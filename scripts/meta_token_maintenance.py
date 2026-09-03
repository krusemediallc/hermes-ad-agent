#!/usr/bin/env python3
"""Deterministic maintenance for the Meta USER token behind the hosted Ads MCP.

scripts/meta_mcp_bridge.py reads META_MCP_LONG_TOKEN from the env file on every request.
This script keeps that value fresh without an LLM in the loop: inspect the current
token, ask Meta for a long-lived exchange, classify the answer honestly, and only then
rewrite the one env line under a lock, with compare-and-swap, an MCP smoke test, and a
narrowly scoped rollback. Python 3.9+, standard library only. Never prints a token or
the app secret.

Variables in the env file ($HERMES_HOME/.env, /data/.env on Hostinger):
  META_MCP_LONG_TOKEN   the long-lived USER token the bridge sends to Meta (canonical)
  META_MCP_TOKEN        the HANDOFF variable: a human pastes a fresh short-lived USER token
                        here after re-authorizing; this script exchanges it, writes the
                        long-lived result to META_MCP_LONG_TOKEN, and clears the handoff line
  META_APP_ID / META_APP_SECRET   the Meta app used for debug_token and the exchange

Outcome vocabulary (the last stdout line is always "Outcome: <NAME>"):
  RENEWED               A different token whose expiry is more than one day later than
                        the current one (or a long-lived token produced from the handoff
                        variable); written and smoke-tested.
  REPLACED_SAME_EXPIRY  A different token string with the same expiry. Left unwritten
                        unless --replace-same-expiry is passed. Not a renewal: the
                        deadline did not move and the old token stays valid at Meta.
  NO_CHANGE             Meta returned the same token, the candidate would expire earlier
                        than the current one (retained), or the exchange was skipped
                        because the app credentials are not set. Nothing written.
  REAUTH_REQUIRED       Current token missing, invalid, or expired with no usable handoff
                        token, or Meta answered the exchange with an OAuth error (code
                        190). A human must mint a new USER token (docs/meta-ads-mcp-renewal.md).
  FAILED                Anything else: lock held, network or JSON error, candidate not a
                        USER token, missing a scope, or belonging to another app, env
                        file changed underneath (compare-and-swap), key line missing or
                        duplicated, or a post-write check failed.

Headline status for cron reports (status_compat, four values): SUCCESS when RENEWED or
when a REPLACED_SAME_EXPIRY candidate was actually written; NO_CHANGE when a same-expiry
candidate was left unwritten (the detail line still says REPLACED_SAME_EXPIRY);
otherwise REAUTH_REQUIRED or FAILED.

Post-write checks: a direct MCP initialize + tools/list with the new token, and with
--hermes-test also "hermes mcp test <server>" through the bridge. If Meta rejects the
new token (HTTP 401/403) the previous token is restored. Any other failure keeps the
candidate (debug_token already proved it valid and scoped) and reports FAILED so the
operator looks at the transport or the bridge configuration, not the credential.

Exit codes: 0 RENEWED, NO_CHANGE, or a written REPLACED_SAME_EXPIRY with at least
--min-days left; 1 REPLACED_SAME_EXPIRY left unwritten, or a healthy outcome with fewer
than --min-days left; 2 REAUTH_REQUIRED or FAILED. With --json, stdout is one JSON line
followed by the Outcome line; with --markdown, the report below followed by the Outcome
line. --dry-run inspects and exchanges, reports what a live run would do, and writes
nothing at all (no env, state, or lock file).
"""
import argparse
import datetime as dt
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

GRAPH_HOST = "https://graph.facebook.com"
DEFAULT_UPSTREAM = "https://mcp.facebook.com/ads"
DEFAULT_TOKEN_VAR = "META_MCP_LONG_TOKEN"
DEFAULT_HANDOFF_VAR = "META_MCP_TOKEN"
PROTOCOL_VERSION = "2025-06-18"
CLIENT_NAME = "hermes-ad-agent-token-maintenance"
NET_TIMEOUT = 30.0
HERMES_TEST_TIMEOUT = 90
ADVANCE_SECONDS = 86400
REQUIRED_SCOPES = ["ads_mcp_management", "ads_read", "ads_management", "catalog_management",
                   "business_management", "pages_show_list", "instagram_basic"]
HEALTHY = ("RENEWED", "NO_CHANGE", "REPLACED_SAME_EXPIRY")
TOKEN_RE = re.compile(r"EAA[A-Za-z0-9]{10,}")
_SECRETS = set()  # values that must never reach stdout or the state file


class Stop(Exception):
    """Unwinds the run with a final outcome and a message (redacted before printing)."""

    def __init__(self, outcome, message):
        Exception.__init__(self, message)
        self.outcome, self.message = outcome, message


def redact(text):
    text = str(text)
    for secret in sorted(_SECRETS, key=len, reverse=True):
        if len(secret) >= 8:
            text = text.replace(secret, "[redacted]")
    return TOKEN_RE.sub("EAA[redacted]", text)


def iso(ts):
    if not ts:
        return None if ts is None else "never"
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- env file

def parse_dotenv(text):
    """KEY=value, export KEY=value, single or double quotes, full-line and trailing comments."""
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("export "):
            line = line[7:].strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if value[:1] in ("'", '"'):
            close = value.find(value[0], 1)
            value = value[1:close] if close != -1 else value[1:]
        elif " #" in value:
            value = value[:value.index(" #")].rstrip()
        if key:
            out[key] = value
    return out


def rewrite_token_lines(text, var, new_value):
    """Replace the value on every VAR= line, keeping prefix, spacing, quotes, trailing comments and
    line endings byte for byte. Returns (new_text, lines_changed)."""
    pattern = re.compile(r"^(\s*(?:export\s+)?)" + re.escape(var) + r"(\s*=\s*)(.*)$")
    out, hits = [], 0
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        match = pattern.match(body)
        if not match:
            out.append(line)
            continue
        prefix, eq, old = match.groups()
        old = old.strip()
        quote = old[0] if old[:1] in ("'", '"') and old.find(old[0], 1) > 0 else ""
        tail = old[old.find(quote, 1) + 1:] if quote else (old[old.find(" #"):] if " #" in old else "")
        out.append(prefix + var + eq + quote + new_value + quote + tail + line[len(body):])
        hits += 1
    return "".join(out), hits


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def atomic_write(path, text):
    """Temp file in the same directory, fsync, mode 0600, os.replace. The temp file never outlives a failure."""
    fd, tmp = tempfile.mkstemp(prefix=".maint-", dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def resolve_env_file(explicit):
    """--env-file, else $META_MCP_ENV_FILE / $META_MCP_DOTENV_PATH, else $HERMES_HOME/.env, else /data/.env
    if it exists, else ~/.hermes/.env. The first three are authoritative when set: this script writes, so a
    missing file there is reported rather than silently replaced by the next candidate."""
    explicit = explicit or os.environ.get("META_MCP_ENV_FILE") or os.environ.get("META_MCP_DOTENV_PATH")
    if explicit:
        return explicit
    if os.environ.get("HERMES_HOME"):
        return os.path.join(os.environ["HERMES_HOME"], ".env")
    return "/data/.env" if os.path.isfile("/data/.env") else os.path.expanduser("~/.hermes/.env")


def acquire_lock(path):
    """flock the lock file for the whole run; return the fd, or None when another run holds it."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except OSError:
        os.close(fd)
        return None


# ---------------------------------------------------------------- Hermes-side checks

def check_bridge_config(config_path=None):
    """'yes' when mcp_servers.meta_ads is a command-type (bridge) entry with no url and no headers,
    'no' when it is not, 'unknown' when the config cannot be read. Line-based; no YAML library needed."""
    path = config_path or os.path.join(os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes"), "config.yaml")
    try:
        lines = read_text(path).splitlines()
    except OSError:
        return "unknown"
    start = next((i for i, line in enumerate(lines) if re.match(r"^\s*meta_ads:\s*(#.*)?$", line)), None)
    if start is None:
        return "no"
    indent = len(lines[start]) - len(lines[start].lstrip())
    keys = set()
    for line in lines[start + 1:]:
        if line.strip() and not line.strip().startswith("#") and (len(line) - len(line.lstrip())) <= indent:
            break
        stripped = line.strip()
        if ":" in stripped and not stripped.startswith(("-", "#")):
            keys.add(stripped.split(":", 1)[0].strip())
    return "yes" if "command" in keys and "url" not in keys and "headers" not in keys else "no"


def find_hermes():
    home = os.environ.get("HERMES_HOME") or ""
    for cand in (shutil.which("hermes"), "/opt/venv/bin/hermes", os.path.join(home, "bin", "hermes") if home else None):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def run_hermes_test(server, run_fn=None, timeout=HERMES_TEST_TIMEOUT):
    """Run `hermes mcp test <server>` and judge its TEXT (the exit code is unreliable). Returns (ok, detail)."""
    exe = find_hermes()
    if not exe:
        return False, "hermes executable not found (PATH, /opt/venv/bin/hermes, $HERMES_HOME/bin/hermes)"
    runner = run_fn or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=timeout))
    try:
        proc = runner([exe, "mcp", "test", server])
    except Exception as exc:
        return False, "could not run hermes mcp test: %s" % type(exc).__name__
    text = redact("%s\n%s" % (getattr(proc, "stdout", "") or "", getattr(proc, "stderr", "") or ""))
    low = text.lower()
    failed = "connection failed" in low or "✗" in text or " failed" in low
    ok = not failed and "tool" in low
    return ok, ("passed" if ok else "failed") + ": " + " ".join(text.split())[:160]


# ---------------------------------------------------------------- network layer (injectable for tests)

def _json_or_none(raw):
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return None


def graph_get(url, timeout):
    """GET a Graph API URL; return (status, parsed JSON or None). Transport errors raise."""
    req = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, _json_or_none(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, _json_or_none(exc.read())


def mcp_post(url, headers, body, timeout):
    """POST one JSON-RPC message; return (status, lowercase headers, body text). An SSE body is read
    only until the response to the request id has arrived (Meta may keep the stream open)."""
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read().decode("utf-8", "replace")
    with resp:
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        if "text/event-stream" not in hdrs.get("content-type", ""):
            return resp.status, hdrs, resp.read().decode("utf-8", "replace")
        sent, text = _json_or_none(body), ""
        want = sent.get("id") if isinstance(sent, dict) else None
        for chunk in iter(lambda: resp.read(4096), b""):
            text += chunk.decode("utf-8", "replace")
            if want is not None and any(m.get("id") == want and ("result" in m or "error" in m) for m in parse_sse(text)):
                break
        return resp.status, hdrs, text


def parse_sse(text):
    out = []
    for event in re.split(r"\r?\n\r?\n", text):
        data = "\n".join(l[5:].lstrip() for l in event.splitlines() if l.startswith("data:")).strip()
        parsed = _json_or_none(data.encode("utf-8")) if data else None
        out.extend(parsed if isinstance(parsed, list) else [parsed])
    return [m for m in out if isinstance(m, dict)]


def parse_body(headers, text):
    parsed = None if "text/event-stream" in headers.get("content-type", "") else _json_or_none(text.encode("utf-8"))
    if parsed is None:
        return parse_sse(text)
    return [m for m in (parsed if isinstance(parsed, list) else [parsed]) if isinstance(m, dict)]


# ---------------------------------------------------------------- the run

REPORT_KEYS = ("outcome", "message", "token_type", "scopes_ok", "missing_scopes", "expires_at",
               "data_access_expires_at", "days_remaining", "next_renewal_deadline", "next_steps",
               "candidate_expires_at", "candidate_differed", "would_write", "env_file", "state_file",
               "required_action", "status_compat")


class Maintainer:
    def __init__(self, args, graph_get_fn=None, mcp_post_fn=None, now=None, hermes_run_fn=None):
        self.a, self.graph_get, self.mcp_post = args, graph_get_fn or graph_get, mcp_post_fn or mcp_post
        self.hermes_run_fn = hermes_run_fn
        self.now = now or (lambda: dt.datetime.now(dt.timezone.utc).timestamp())
        self.report = dict.fromkeys(REPORT_KEYS)
        self.report.update(written=False, rolled_back=False, candidate_kept=False, expiry_advanced=False,
                           via_handoff=False, smoke_test="not run", hermes_test="not run",
                           bridge_config_valid="unknown", notes=[], dry_run=bool(args.dry_run),
                           min_days=args.min_days)

    def note(self, text):
        self.report["notes"].append(redact(text)[:200])

    # -- Graph API ----------------------------------------------------------------
    def graph(self, path, params, oauth_outcome):
        """GET <version>/<path>; return (status, json). A Graph error raises Stop: OAuth errors (code 190 or
        'Error validating access token') get `oauth_outcome`, everything else FAILED."""
        url = "%s/%s/%s?%s" % (GRAPH_HOST, self.a.graph_version, path, urllib.parse.urlencode(params))
        try:
            status, data = self.graph_get(url, NET_TIMEOUT)
        except Exception as exc:  # network, timeout, decode; text is redacted
            raise Stop("FAILED", "graph request failed: %s" % redact("%s: %s" % (type(exc).__name__, exc)))
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict):
            oauth = err.get("code") == 190 or "Error validating access token" in str(err.get("message", ""))
            raise Stop(oauth_outcome if oauth else "FAILED", "%s: %s (code %s, HTTP %s)" % (
                path, redact(err.get("message", "unknown error")), err.get("code"), status))
        return status, data

    def inspect(self, token, app_id, app_secret, who):
        """debug_token; returns {type, app_id, expires_at, data_access_expires_at, scopes} or raises Stop.
        A bad current or handoff token means a human must re-authorize; a bad candidate is a FAILED run."""
        bad = "FAILED" if who == "candidate" else "REAUTH_REQUIRED"
        access = "%s|%s" % (app_id, app_secret) if app_id and app_secret else token
        status, data = self.graph("debug_token", {"input_token": token, "access_token": access}, bad)
        d = data.get("data") if isinstance(data, dict) else None
        if not isinstance(d, dict):
            raise Stop("FAILED", "debug_token(%s): unexpected response (HTTP %s)" % (who, status))
        if d.get("is_valid") is not True or d.get("error"):
            raise Stop(bad, "%s token is not valid: %s" % (
                who, redact((d.get("error") or {}).get("message", "is_valid is not true"))))
        exp = int(d.get("expires_at") or 0)
        if exp and exp <= self.now():
            raise Stop(bad, "%s token expired at %s" % (who, iso(exp)))
        return {"type": d.get("type"), "app_id": str(d.get("app_id") or ""), "expires_at": exp,
                "scopes": [str(s) for s in (d.get("scopes") or [])],
                "data_access_expires_at": int(d.get("data_access_expires_at") or 0)}

    def describe(self, info):
        """Record the token the env file holds right now."""
        r, exp = self.report, info["expires_at"]
        r["token_type"], r["missing_scopes"] = info["type"], [s for s in REQUIRED_SCOPES if s not in info["scopes"]]
        r["scopes_ok"] = not r["missing_scopes"]
        r["expires_at"], r["data_access_expires_at"] = iso(exp), iso(info["data_access_expires_at"])
        r["days_remaining"] = round((exp - self.now()) / 86400.0, 1) if exp else None
        r["next_renewal_deadline"] = iso(exp - self.a.min_days * 86400) if exp else None

    # -- env file -----------------------------------------------------------------
    def write_value(self, env_file, var, expect, new, allow_create=False):
        """Compare-and-swap: re-read, require the stored value to equal `expect`, rewrite exactly one line.
        Fails closed when the key is duplicated, or missing unless allow_create (handoff path)."""
        try:
            text = read_text(env_file)
            if parse_dotenv(text).get(var, "").strip() != expect:
                raise Stop("FAILED", "%s changed underneath, not writing" % var)
            new_text, hits = rewrite_token_lines(text, var, new)
            if hits > 1:
                raise Stop("FAILED", "%s appears %d times in %s; keep exactly one line" % (var, hits, env_file))
            if hits == 0:
                if not allow_create:
                    raise Stop("FAILED", "no %s line found to rewrite" % var)
                sep = "" if not text or text.endswith(("\n", "\r")) else "\n"
                new_text = "%s%s%s='%s'\n" % (text, sep, var, new)
            atomic_write(env_file, new_text)
        except OSError as exc:
            raise Stop("FAILED", "env file read/write failed: %s" % type(exc).__name__)

    # -- post-write checks --------------------------------------------------------
    def smoke_test(self, token):
        """initialize, notifications/initialized, tools/list against --upstream with the candidate token.
        Returns (ok, detail, kind) where kind is 'auth' (Meta rejected the token), 'transport', or 'other'."""
        headers = {"Authorization": "Bearer " + token, "Accept": "application/json, text/event-stream",
                   "Accept-Encoding": "identity", "Content-Type": "application/json",
                   "MCP-Protocol-Version": PROTOCOL_VERSION, "User-Agent": CLIENT_NAME + "/1.0"}

        def post(message):
            status, hdrs, text = self.mcp_post(self.a.upstream, headers, json.dumps(message).encode("utf-8"), NET_TIMEOUT)
            return status, hdrs, parse_body(hdrs, text)

        try:
            status, hdrs, msgs = post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": PROTOCOL_VERSION, "capabilities": {},
                "clientInfo": {"name": CLIENT_NAME, "version": "1.0"}}})
            err = next((m["error"] for m in msgs if m.get("id") == 1 and isinstance(m.get("error"), dict)), None)
            if status in (401, 403):
                return False, "initialize rejected: HTTP %s" % status, "auth"
            if status not in (200, 202) or err:
                return False, "initialize failed: HTTP %s%s" % (status, ", " + redact(err.get("message", "")) if err else ""), "other"
            if hdrs.get("mcp-session-id"):
                headers["Mcp-Session-Id"] = hdrs["mcp-session-id"]
            post({"jsonrpc": "2.0", "method": "notifications/initialized"})
            status, hdrs, msgs = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        except Exception as exc:
            return False, "transport error: " + redact("%s: %s" % (type(exc).__name__, exc)), "transport"
        if status in (401, 403):
            return False, "tools/list rejected: HTTP %s" % status, "auth"
        reply = next((m for m in msgs if m.get("id") == 2), None)
        if status not in (200, 202) or not reply or not isinstance(reply.get("result"), dict):
            return False, "tools/list failed: HTTP %s" % status, "other"
        names = [str(t.get("name", "")) for t in reply["result"].get("tools", []) if isinstance(t, dict)]
        ads = [n for n in names if "ads_" in n]
        if not ads:
            return False, "tools/list returned %d tools, none with ads_ in the name" % len(names), "other"
        return True, "passed: %d tools listed, %d with ads_ in the name" % (len(names), len(ads)), "ok"

    # -- the algorithm ------------------------------------------------------------
    def maintain(self, env_file):
        a, r = self.a, self.report
        try:
            values = parse_dotenv(read_text(env_file))
        except OSError:
            values = {}
        current = values.get(a.token_var, "").strip()
        handoff = values.get(a.handoff_var, "").strip() if a.handoff_var else ""
        app_id = (values.get(a.app_id_var) or os.environ.get(a.app_id_var) or "").strip()
        app_secret = (values.get(a.app_secret_var) or os.environ.get(a.app_secret_var) or "").strip()
        _SECRETS.update(s for s in (current, handoff, app_id, app_secret) if s)
        have_app = bool(app_id and app_secret)
        if not have_app:
            self.note("app credentials not set: debug_token used the token as its own access_token")

        # 1. Which token do we exchange? A valid handoff token a human left wins (that is what the line is
        #    for); otherwise the current long-lived token. Describe the current token whenever it is usable.
        info_t, source, use_handoff = None, current, False
        if current:
            try:
                info_t = self.inspect(current, app_id, app_secret, "current")
                self.describe(info_t)
            except Stop as stop:
                if stop.outcome != "REAUTH_REQUIRED" or not handoff:
                    raise
                self.note("current token unusable (%s); trying the handoff token in %s" % (stop.message, a.handoff_var))
        elif not handoff:
            raise Stop("REAUTH_REQUIRED", "no token in env file (%s in %s)" % (a.token_var, env_file))
        if handoff:
            if not have_app:
                if info_t is None:
                    raise Stop("REAUTH_REQUIRED", "a handoff token is present but %s/%s are not set, so it cannot "
                                                  "be exchanged" % (a.app_id_var, a.app_secret_var))
                self.note("handoff token present but %s/%s are not set; it cannot be exchanged" % (a.app_id_var, a.app_secret_var))
            else:
                try:
                    self.inspect(handoff, app_id, app_secret, "handoff")
                    use_handoff = True
                except Stop as stop:
                    if info_t is None:
                        raise
                    self.note("handoff token in %s is unusable (%s); continuing with the current token"
                              % (a.handoff_var, stop.message))
        if use_handoff:
            r["via_handoff"], source = True, handoff
            self.note("exchanging the handoff token from %s" % a.handoff_var)
        elif info_t is None:
            raise Stop("REAUTH_REQUIRED", "no usable token: %s is missing or invalid and no handoff token is usable"
                       % a.token_var)
        elif not have_app:
            raise Stop("NO_CHANGE", "exchange skipped: %s/%s not set" % (a.app_id_var, a.app_secret_var))

        # 2. Exchange, then validate the candidate as strictly as Meta's MCP will.
        status, data = self.graph("oauth/access_token", {
            "grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": app_secret,
            "fb_exchange_token": source}, "REAUTH_REQUIRED")
        candidate = str(data.get("access_token") or "").strip() if isinstance(data, dict) else ""
        if status != 200 or not candidate:
            raise Stop("FAILED", "exchange: no access_token in the response (HTTP %s)" % status)
        if data.get("expires_in") is not None:
            self.note("exchange reported expires_in=%s s" % data.get("expires_in"))
        r["candidate_differed"] = candidate != current
        if candidate == current:
            raise Stop("NO_CHANGE", "Meta returned the same token; expiry unchanged")
        _SECRETS.add(candidate)
        info_c = self.inspect(candidate, app_id, app_secret, "candidate")
        r["candidate_expires_at"] = iso(info_c["expires_at"])
        if info_c["type"] != "USER":
            raise Stop("FAILED", "candidate is a %s token; the hosted MCP needs USER" % info_c["type"])
        missing = [s for s in REQUIRED_SCOPES if s not in info_c["scopes"]]
        if missing:
            raise Stop("FAILED", "candidate is missing scopes: %s" % ", ".join(missing))
        if app_id and info_c["app_id"] and info_c["app_id"] != str(app_id):
            raise Stop("FAILED", "candidate belongs to a different Meta app than %s" % a.app_id_var)

        # 3. Classify.
        if info_t is not None:
            cur_exp, cand_exp = info_t["expires_at"], info_c["expires_at"]
            if cur_exp and cand_exp and cand_exp < cur_exp - ADVANCE_SECONDS:
                raise Stop("NO_CHANGE", "candidate would expire earlier (%s) than the current token (%s); retained"
                           % (iso(cand_exp), iso(cur_exp)))
            advancing = bool(cur_exp) and (cand_exp == 0 or cand_exp > cur_exp + ADVANCE_SECONDS)
            outcome = "RENEWED" if advancing else "REPLACED_SAME_EXPIRY"
        else:
            advancing, outcome = True, "RENEWED"
        r["expiry_advanced"] = advancing
        r["would_write"] = advancing or bool(a.replace_same_expiry)
        if a.dry_run:
            raise Stop(outcome, "dry run: a live run would %s the candidate (expires %s)" % (
                "write" if r["would_write"] else "not write", r["candidate_expires_at"]))
        if not r["would_write"]:
            raise Stop(outcome, "candidate expiry did not advance (%s); not written. Pass --replace-same-expiry "
                                "to rotate anyway" % r["candidate_expires_at"])

        # 4. Write, then prove the new token works before calling it done.
        self.write_value(env_file, a.token_var, current, candidate, allow_create=info_t is None)
        r["written"] = True
        self.describe(info_c)
        if a.no_smoke_test:
            r["smoke_test"] = "skipped (--no-smoke-test)"
        else:
            ok, detail, kind = self.smoke_test(candidate)
            r["smoke_test"] = detail
            if not ok and kind == "auth":
                self.rollback(env_file, candidate, current, info_t)
            if not ok:
                r["candidate_kept"] = True
                raise Stop("FAILED", "smoke test failed (%s); the new token was kept because debug_token validated "
                                     "it, so check the endpoint or the network, not the credential" % detail)
            self.note("the bridge re-reads the env file per request; the live gateway uses the new token on its next call")
        if a.hermes_test:
            ok, detail = run_hermes_test(a.hermes_server, self.hermes_run_fn)
            r["hermes_test"] = detail
            if not ok:
                r["candidate_kept"] = True
                raise Stop("FAILED", "hermes mcp test failed (%s); the new token was kept, check the bridge "
                                     "configuration (hermes config check)" % detail)
        if r["via_handoff"]:
            try:
                self.write_value(env_file, a.handoff_var, handoff, "")
                self.note("cleared the handoff line %s" % a.handoff_var)
            except Stop as exc:
                self.note("could not clear %s: %s" % (a.handoff_var, exc.message))
        raise Stop(outcome, "new token written to %s%s%s" % (
            env_file, " (from the handoff token)" if r["via_handoff"] else "",
            "" if advancing else " (same expiry, forced)"))

    def rollback(self, env_file, candidate, current, info_t):
        """Meta rejected the new token outright: restore the previous line. Raises FAILED either way."""
        detail = self.report["smoke_test"]
        try:
            self.write_value(env_file, self.a.token_var, candidate, current)
        except Stop as exc:
            raise Stop("FAILED", "smoke test failed (%s) and rollback failed: %s; the env file may hold the untested "
                                 "token" % (detail, exc.message))
        self.report["written"], self.report["rolled_back"] = False, True
        if info_t is not None:
            self.describe(info_t)
        raise Stop("FAILED", "Meta rejected the new token (%s); rolled back to the previous token" % detail)

    # -- wrap-up ------------------------------------------------------------------
    def finish(self):
        """Derive exit_code, status_compat, required_action, and next_steps from the final report."""
        r, a, outcome = self.report, self.a, self.report["outcome"]
        low = r["days_remaining"] is not None and r["days_remaining"] < a.min_days
        unwritten_same = outcome == "REPLACED_SAME_EXPIRY" and not r["written"]
        r["exit_code"] = 2 if outcome not in HEALTHY else (1 if unwritten_same or low else 0)
        if outcome == "RENEWED" or (outcome == "REPLACED_SAME_EXPIRY" and r["written"]):
            r["status_compat"] = "SUCCESS"
        elif outcome == "REPLACED_SAME_EXPIRY":
            r["status_compat"] = "NO_CHANGE"  # nothing was written; the detail line keeps the precise reason
        else:
            r["status_compat"] = outcome
        if outcome == "REAUTH_REQUIRED":
            r["next_steps"] = ("a human must mint a new short-lived USER token with all seven scopes for the configured "
                               "app, store it as %s in %s, and re-run this script; it exchanges it and writes %s "
                               "(docs/meta-ads-mcp-renewal.md)" % (a.handoff_var or a.token_var, r["env_file"], a.token_var))
            r["required_action"] = r["next_steps"]
        elif outcome == "FAILED":
            r["next_steps"] = "fix the reported error and re-run" + (
                " (the previous token was restored)" if r["rolled_back"] else
                (" (the validated new token is in place)" if r["candidate_kept"] else ""))
            r["required_action"] = r["message"] or r["next_steps"]
        else:
            r["next_steps"] = ("no action needed for the same-expiry candidate; re-run with --replace-same-expiry only "
                               "to rotate the string" if unwritten_same else "nothing to do")
            r["required_action"] = "none"
            if low:
                r["next_steps"] += ("; fewer than %g days remain and Meta did not advance the expiry: plan a manual "
                                    "re-auth before %s" % (a.min_days, r["expires_at"]))
                r["required_action"] = "re-authorize before %s (fewer than %g days remain)" % (r["expires_at"], a.min_days)
        return r["exit_code"]

    def save_state(self, path):
        """Bounded JSON state (overwritten, never appended); notes are short redacted strings."""
        r, outcome, now_iso = self.report, self.report["outcome"], iso(self.now())
        try:
            with open(path, "r", encoding="utf-8") as fh:
                prev = json.load(fh)
        except (OSError, ValueError):
            prev = {}
        runs, last_adv = int(prev.get("consecutive_non_advancing_runs") or 0), prev.get("last_advancing_expiry_at")
        if outcome == "RENEWED":
            runs, last_adv = 0, now_iso
        elif outcome in ("NO_CHANGE", "REPLACED_SAME_EXPIRY"):
            runs += 1
        state = {"schema_version": 1, "last_run": now_iso, "last_outcome": outcome, "status_compat": r["status_compat"],
                 "expires_at": r["expires_at"], "data_access_expires_at": r["data_access_expires_at"],
                 "last_advancing_expiry_at": last_adv, "consecutive_non_advancing_runs": runs,
                 "days_remaining": r["days_remaining"], "bridge_config_valid": r["bridge_config_valid"],
                 "notes": [redact(n)[:200] for n in [r["message"]] + r["notes"] if n][:10]}
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            atomic_write(path, json.dumps(state, indent=2, sort_keys=True) + "\n")
        except OSError as exc:
            self.note("state file not written: %s" % type(exc).__name__)
        r["consecutive_non_advancing_runs"] = runs

    def run(self):
        a, r = self.a, self.report
        base = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
        r["env_file"] = resolve_env_file(a.env_file)
        r["state_file"] = a.state_file or os.path.join(base, "hermes-ad-agent", "token-maintenance-state.json")
        r["bridge_config_valid"] = check_bridge_config(a.config_file)
        lock_fd, write_state = None, not a.dry_run
        try:
            if not a.upstream.startswith("https://"):
                raise Stop("FAILED", "--upstream must be an https URL")
            if not a.dry_run:
                lock_fd = acquire_lock(r["state_file"] + ".lock")
                if lock_fd is None:
                    write_state = False
                    raise Stop("FAILED", "another maintenance run holds the lock (%s.lock)" % r["state_file"])
            self.maintain(r["env_file"])
            raise Stop("FAILED", "maintain() ended without an outcome")
        except Stop as stop:
            r["outcome"], r["message"] = stop.outcome, redact(stop.message)
        except Exception as exc:  # never exit without an Outcome line
            r["outcome"], r["message"] = "FAILED", redact("unexpected %s: %s" % (type(exc).__name__, exc))
        code = self.finish()
        if write_state:
            self.save_state(r["state_file"])
        if lock_fd is not None:
            os.close(lock_fd)
        return code


# ---------------------------------------------------------------- output and CLI

def _check_state(detail):
    if not detail or detail.startswith(("not run", "skipped")):
        return "not run"
    return "passed" if detail.startswith("passed") else "failed"


def render_markdown(r):
    yn = lambda v: "unavailable" if v is None else ("yes" if v else "no")  # noqa: E731
    return "\n".join([
        "# " + str(r["status_compat"] or r["outcome"]),
        "",
        "- Outcome detail: %s" % r["outcome"],
        "- Current expiry (UTC): %s" % (r["expires_at"] or "unavailable"),
        "- Candidate expiry (UTC): %s" % (r["candidate_expires_at"] or "unavailable"),
        "- Candidate differed: %s" % yn(r["candidate_differed"]),
        "- Credential replaced: %s" % ("yes" if r["written"] else "no"),
        "- Expiry advanced: %s" % ("yes" if r["expiry_advanced"] and r["written"] else "no"),
        "- Bridge config valid: %s" % r["bridge_config_valid"],
        "- MCP smoke test: %s" % _check_state(r["smoke_test"]),
        "- Hermes mcp test: %s" % _check_state(r["hermes_test"]),
        "- Required action: %s" % (r["required_action"] or "none"),
    ])


def print_report(r, as_json=False, as_markdown=False):
    if as_json:
        print(redact(json.dumps(r, sort_keys=True)))
    elif as_markdown:
        print(redact(render_markdown(r)))
    else:
        scopes = None if r["scopes_ok"] is None else ("yes" if r["scopes_ok"] else "missing " + ", ".join(r["missing_scopes"]))
        deadline = r["next_renewal_deadline"] and "%s (expiry minus %g days)" % (r["next_renewal_deadline"], r["min_days"])
        rows = [("outcome", r["outcome"]), ("status", r["status_compat"]), ("message", r["message"]),
                ("token type", r["token_type"]), ("scopes ok", scopes), ("expires_at", r["expires_at"]),
                ("data_access_expires_at", r["data_access_expires_at"]), ("days remaining", r["days_remaining"]),
                ("candidate expires_at", r["candidate_expires_at"]),
                ("written", "rolled back" if r["rolled_back"] else ("yes" if r["written"] else "no")),
                ("expiry advanced", "yes" if r["expiry_advanced"] and r["written"] else "no"),
                ("bridge config valid", r["bridge_config_valid"]), ("smoke test", r["smoke_test"]),
                ("hermes mcp test", r["hermes_test"]), ("next renewal deadline", deadline),
                ("required action", r["required_action"]), ("notes", "; ".join(r["notes"]) or "none"),
                ("next steps", r["next_steps"])]
        print("Meta token maintenance%s: env=%s state=%s" % (" (dry run)" if r["dry_run"] else "", r["env_file"], r["state_file"]))
        for key, value in rows:
            print(redact("  %-23s %s" % (key + ":", "unknown" if value is None else value)))
    print("Outcome: %s" % r["outcome"])


def build_arg_parser():
    p = argparse.ArgumentParser(description="Keep the Meta user token for the hosted Ads MCP fresh (deterministic).")
    p.add_argument("--env-file", help="dotenv file holding the token (default: auto-detect, see resolve_env_file)")
    p.add_argument("--token-var", default=DEFAULT_TOKEN_VAR, help="long-lived token variable (default %s)" % DEFAULT_TOKEN_VAR)
    p.add_argument("--handoff-var", default=DEFAULT_HANDOFF_VAR,
                   help="short-lived handoff variable a human fills after re-authorizing (default %s); pass '' to disable"
                        % DEFAULT_HANDOFF_VAR)
    p.add_argument("--app-id-var", default="META_APP_ID")
    p.add_argument("--app-secret-var", default="META_APP_SECRET")
    p.add_argument("--dry-run", action="store_true", help="inspect and exchange, report, write nothing")
    p.add_argument("--json", action="store_true", help="one JSON line, then the Outcome line")
    p.add_argument("--markdown", action="store_true", help="the cron report block, then the Outcome line")
    p.add_argument("--replace-same-expiry", action="store_true", help="also write a candidate whose expiry did not advance")
    p.add_argument("--min-days", type=float, default=21, help="exit 1 when fewer days remain (default 21)")
    p.add_argument("--state-file", help="default $HERMES_HOME/hermes-ad-agent/token-maintenance-state.json")
    p.add_argument("--config-file", help="Hermes config.yaml to inspect for the bridge entry (default $HERMES_HOME/config.yaml)")
    p.add_argument("--no-smoke-test", action="store_true")
    p.add_argument("--hermes-test", action="store_true", help="after a write, also run 'hermes mcp test <server>' through the bridge")
    p.add_argument("--hermes-server", default="meta_ads", help="MCP server name for --hermes-test (default meta_ads)")
    p.add_argument("--upstream", default=DEFAULT_UPSTREAM)
    p.add_argument("--graph-version", default="v25.0")
    return p


def main(argv=None, graph_get_fn=None, mcp_post_fn=None, now=None, hermes_run_fn=None):
    maintainer = Maintainer(build_arg_parser().parse_args(argv), graph_get_fn, mcp_post_fn, now, hermes_run_fn)
    code = maintainer.run()
    print_report(maintainer.report, maintainer.a.json, maintainer.a.markdown)
    return code


if __name__ == "__main__":
    sys.exit(main())
