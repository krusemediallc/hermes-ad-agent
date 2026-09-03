#!/usr/bin/env python3
"""Deterministic maintenance for the Meta USER token behind the hosted Ads MCP.

scripts/meta_mcp_bridge.py reads META_MCP_TOKEN from the env file on every
request. This script keeps that value fresh without an LLM in the loop: it
inspects the current token, asks Meta for a long-lived exchange, classifies
the answer honestly, and only then rewrites the one env line, under a lock,
with compare-and-swap, an MCP smoke test, and rollback. Python 3.9+, standard
library only. It never prints or logs a token or the app secret.

Outcome vocabulary (the last stdout line is always "Outcome: <NAME>"):

  RENEWED               Meta returned a different token whose expiry is more
                        than one day later than the current one. It was written
                        to the env file and passed the smoke test.
  NO_CHANGE             Meta returned the same token string, or the exchange
                        was skipped because the app credentials are not set.
                        Nothing was written; the expiry did not move.
  REPLACED_SAME_EXPIRY  Meta returned a different token string with the same
                        or an earlier expiry. Left unwritten unless
                        --replace-same-expiry is passed.
  REAUTH_REQUIRED       The current token is missing, invalid, or expired, or
                        Meta answered the exchange with an OAuth error (code
                        190). A human must mint a new user token; see
                        docs/meta-authentication.md.
  FAILED                Everything else: the lock is held, a network or JSON
                        error, the candidate is not a USER token or misses a
                        scope, the env file changed underneath (compare-and-
                        swap), or the smoke test failed after the write (the
                        previous token was restored).

Why an equal-expiry replacement is not a renewal: Meta's fb_exchange_token
call on a long-lived token often hands back a fresh token string that expires
at the same instant as the old one. The deadline the operator cares about has
not moved, so calling that a renewal hides the manual re-auth that is still
coming. Rotating the secret for no gain also touches the live gateway (the
bridge picks the new value up on its next call). The old cron job labelled
these runs as renewals; this script reports REPLACED_SAME_EXPIRY, counts them
in consecutive_non_advancing_runs in the state file, and leaves the env file
alone unless told otherwise.

Exit codes: 0 RENEWED or NO_CHANGE (or a written REPLACED_SAME_EXPIRY) with at
least --min-days of validity left; 1 REPLACED_SAME_EXPIRY left unwritten, or a
healthy outcome with fewer than --min-days left; 2 REAUTH_REQUIRED or FAILED.
With --json, stdout is one JSON line followed by the "Outcome:" line.
--dry-run runs the inspections and the exchange, reports what a live run would
do, and writes nothing at all (no env, state, or lock file).
"""
import argparse
import datetime as dt
import fcntl
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

GRAPH_HOST = "https://graph.facebook.com"
DEFAULT_UPSTREAM = "https://mcp.facebook.com/ads"
DEFAULT_GRAPH_VERSION = "v25.0"
PROTOCOL_VERSION = "2025-06-18"
CLIENT_NAME = "hermes-ad-agent-token-maintenance"
NET_TIMEOUT = 30.0
ADVANCE_SECONDS = 86400
REQUIRED_SCOPES = ["ads_mcp_management", "ads_read", "ads_management", "catalog_management",
                   "business_management", "pages_show_list", "instagram_basic"]
HEALTHY = ("RENEWED", "NO_CHANGE", "REPLACED_SAME_EXPIRY")
TOKEN_RE = re.compile(r"EAA[A-Za-z0-9]{10,}")
_SECRETS = set()  # values that must never reach stdout, stderr, or the state file


class Stop(Exception):
    """Unwinds the run with a final outcome and a message (redacted before printing)."""

    def __init__(self, outcome, message):
        Exception.__init__(self, message)
        self.outcome, self.message = outcome, message


def redact(text):
    text = str(text)
    for secret in sorted(_SECRETS, key=len, reverse=True):
        if secret and len(secret) >= 8:
            text = text.replace(secret, "[redacted]")
    return TOKEN_RE.sub("EAA[redacted]", text)


def iso(ts):
    if ts is None:
        return None
    if not ts:
        return "never"
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- dotenv

def parse_dotenv(text):
    """KEY=value, export KEY=value, single or double quotes, comments. Values stay in memory."""
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key:
            continue
        if value[:1] in ("'", '"'):
            close = value.find(value[0], 1)
            value = value[1:close] if close != -1 else value[1:]
        elif " #" in value:
            value = value[:value.index(" #")].rstrip()
        out[key] = value
    return out


def rewrite_token_lines(text, var, new_value):
    """Replace the value on every VAR= line; keep prefix, spacing, quotes, trailing comments
    and line endings byte for byte. Returns (new_text, lines_changed)."""
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
        if old[:1] in ("'", '"') and old.find(old[0], 1) != -1:
            close = old.find(old[0], 1)
            new = old[0] + new_value + old[0] + old[close + 1:]
        else:
            idx = old.find(" #")
            new = new_value + (old[idx:] if idx != -1 else "")
        out.append(prefix + var + eq + new + line[len(body):])
        hits += 1
    return "".join(out), hits


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def atomic_write(path, text):
    """Temp file in the same directory, fsync, mode 0600, os.replace, directory fsync."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".maint-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    try:
        dfd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass


# ---------------------------------------------------------------- paths, lock, state

def resolve_env_file(explicit):
    """--env-file, else $META_MCP_ENV_FILE, else $HERMES_HOME/.env, else /data/.env if it
    exists, else ~/.hermes/.env. The first three are authoritative when set: a missing file
    there is reported, never silently replaced by the next candidate (this script writes)."""
    for candidate in (explicit, os.environ.get("META_MCP_ENV_FILE")):
        if candidate:
            return candidate
    if os.environ.get("HERMES_HOME"):
        return os.path.join(os.environ["HERMES_HOME"], ".env")
    if os.path.isfile("/data/.env"):
        return "/data/.env"
    return os.path.expanduser("~/.hermes/.env")


def resolve_state_file(explicit):
    if explicit:
        return explicit
    base = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.hermes")
    return os.path.join(base, "hermes-ad-agent", "token-maintenance-state.json")


def acquire_lock(path):
    """flock the lock file for the whole run; return the fd, or None when another run holds it."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


def load_state(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- network layer (injectable)

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
    """POST one JSON-RPC message; return (status, lowercase headers, body text). For an SSE
    body, stop reading as soon as the response to the request id has arrived."""
    req = urllib.request.Request(url, data=body, method="POST")
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read().decode("utf-8", "replace")
    with resp:
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        if "text/event-stream" not in hdrs.get("content-type", ""):
            return resp.status, hdrs, resp.read().decode("utf-8", "replace")
        sent = _json_or_none(body)
        want = sent.get("id") if isinstance(sent, dict) else None
        text = ""
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            text += chunk.decode("utf-8", "replace")
            if want is not None and any(m.get("id") == want and ("result" in m or "error" in m)
                                        for m in parse_sse(text)):
                break
        return resp.status, hdrs, text


def parse_sse(text):
    out = []
    for event in re.split(r"\r?\n\r?\n", text):
        data = "\n".join(l[5:].lstrip() for l in event.splitlines() if l.startswith("data:")).strip()
        if not data:
            continue
        try:
            parsed = json.loads(data)
        except ValueError:
            continue
        out.extend(parsed if isinstance(parsed, list) else [parsed])
    return [m for m in out if isinstance(m, dict)]


def parse_body(headers, text):
    if "text/event-stream" in headers.get("content-type", ""):
        return parse_sse(text)
    parsed = _json_or_none(text.encode("utf-8"))
    if parsed is None:
        return parse_sse(text)
    return [m for m in (parsed if isinstance(parsed, list) else [parsed]) if isinstance(m, dict)]


# ---------------------------------------------------------------- the run

class Maintainer:
    def __init__(self, args, graph_get_fn=None, mcp_post_fn=None, now=None):
        self.a = args
        self.graph_get = graph_get_fn or graph_get
        self.mcp_post = mcp_post_fn or mcp_post
        self.now = now or (lambda: dt.datetime.now(dt.timezone.utc).timestamp())
        self.report = {"outcome": None, "message": None, "token_type": None, "scopes_ok": None,
                       "missing_scopes": None, "expires_at": None, "data_access_expires_at": None,
                       "days_remaining": None, "written": False, "rolled_back": False,
                       "smoke_test": "skipped", "next_renewal_deadline": None, "next_steps": None,
                       "notes": [], "candidate_expires_at": None, "would_write": None,
                       "dry_run": bool(args.dry_run), "env_file": None, "state_file": None}

    def note(self, text):
        self.report["notes"].append(redact(text)[:200])

    # -- Graph API ----------------------------------------------------------------
    def graph_url(self, path, params):
        return "%s/%s/%s?%s" % (GRAPH_HOST, self.a.graph_version, path, urllib.parse.urlencode(params))

    def call_graph(self, url):
        try:
            return self.graph_get(url, NET_TIMEOUT)
        except Exception as exc:  # network, timeout, decode; text is redacted
            raise Stop("FAILED", "graph request failed: %s" % redact("%s: %s" % (type(exc).__name__, exc)))

    @staticmethod
    def graph_error(data):
        return data.get("error") if isinstance(data, dict) and isinstance(data.get("error"), dict) else None

    @staticmethod
    def is_oauth(err):
        return err.get("code") == 190 or "Error validating access token" in str(err.get("message", ""))

    @staticmethod
    def err_text(err, status):
        return "%s (code %s, HTTP %s)" % (redact(err.get("message", "unknown error")), err.get("code"), status)

    def inspect(self, token, app_id, app_secret, who):
        """debug_token; returns {type, expires_at, data_access_expires_at, scopes} or raises Stop."""
        access = "%s|%s" % (app_id, app_secret) if app_id and app_secret else token
        status, data = self.call_graph(self.graph_url("debug_token", {"input_token": token, "access_token": access}))
        bad = "REAUTH_REQUIRED" if who == "current" else "FAILED"
        err = self.graph_error(data)
        if err:
            raise Stop(bad if self.is_oauth(err) else "FAILED", "debug_token(%s): %s" % (who, self.err_text(err, status)))
        d = data.get("data") if isinstance(data, dict) else None
        if not isinstance(d, dict):
            raise Stop("FAILED", "debug_token(%s): unexpected response (HTTP %s)" % (who, status))
        if d.get("is_valid") is not True or d.get("error"):
            raise Stop(bad, "%s token is not valid: %s" % (
                who, redact((d.get("error") or {}).get("message", "is_valid is not true"))))
        exp = int(d.get("expires_at") or 0)
        if exp and exp <= self.now():
            raise Stop(bad, "%s token expired at %s" % (who, iso(exp)))
        return {"type": d.get("type"), "expires_at": exp, "scopes": [str(s) for s in (d.get("scopes") or [])],
                "data_access_expires_at": int(d.get("data_access_expires_at") or 0)}

    def describe(self, info):
        """Record the token the env file holds right now."""
        r, exp = self.report, info["expires_at"]
        r["token_type"] = info["type"]
        r["missing_scopes"] = [s for s in REQUIRED_SCOPES if s not in info["scopes"]]
        r["scopes_ok"] = not r["missing_scopes"]
        r["expires_at"], r["data_access_expires_at"] = iso(exp), iso(info["data_access_expires_at"])
        r["days_remaining"] = round((exp - self.now()) / 86400.0, 1) if exp else None
        r["next_renewal_deadline"] = iso(exp - self.a.min_days * 86400) if exp else None

    def exchange(self, current, app_id, app_secret):
        url = self.graph_url("oauth/access_token", {"grant_type": "fb_exchange_token", "client_id": app_id,
                                                     "client_secret": app_secret, "fb_exchange_token": current})
        status, data = self.call_graph(url)
        err = self.graph_error(data)
        if err:
            raise Stop("REAUTH_REQUIRED" if self.is_oauth(err) else "FAILED", "exchange: " + self.err_text(err, status))
        token = data.get("access_token") if isinstance(data, dict) else None
        if status != 200 or not token:
            raise Stop("FAILED", "exchange: no access_token in the response (HTTP %s)" % status)
        if data.get("expires_in") is not None:
            self.note("exchange reported expires_in=%s s" % data.get("expires_in"))
        return str(token).strip()

    # -- env file -----------------------------------------------------------------
    def write_token(self, env_file, expect, new):
        """Compare-and-swap: re-read, require the stored token to equal `expect`, rewrite that line only."""
        try:
            text = read_text(env_file)
        except OSError as exc:
            raise Stop("FAILED", "cannot read env file: %s" % type(exc).__name__)
        if parse_dotenv(text).get(self.a.token_var, "").strip() != expect:
            raise Stop("FAILED", "token changed underneath, not writing")
        new_text, hits = rewrite_token_lines(text, self.a.token_var, new)
        if not hits:
            raise Stop("FAILED", "no %s line found to rewrite" % self.a.token_var)
        try:
            atomic_write(env_file, new_text)
        except OSError as exc:
            raise Stop("FAILED", "env file write failed: %s" % type(exc).__name__)

    # -- MCP smoke test -----------------------------------------------------------
    def smoke_test(self, token):
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
            if status not in (200, 202) or err:
                return False, "initialize failed: HTTP %s%s" % (status, "" if not err else ", " + redact(err.get("message", "")))
            if hdrs.get("mcp-session-id"):
                headers["Mcp-Session-Id"] = hdrs["mcp-session-id"]
            post({"jsonrpc": "2.0", "method": "notifications/initialized"})
            status, hdrs, msgs = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        except Exception as exc:
            return False, "transport error: " + redact("%s: %s" % (type(exc).__name__, exc))
        reply = next((m for m in msgs if m.get("id") == 2), None)
        if status not in (200, 202) or not reply or not isinstance(reply.get("result"), dict):
            return False, "tools/list failed: HTTP %s" % status
        names = [str(t.get("name", "")) for t in reply["result"].get("tools", []) if isinstance(t, dict)]
        ads = [n for n in names if "ads_" in n]
        if not ads:
            return False, "tools/list returned %d tools, none with ads_ in the name" % len(names)
        return True, "passed: %d tools listed, %d with ads_ in the name" % (len(names), len(ads))

    # -- the algorithm ------------------------------------------------------------
    def maintain(self, env_file):
        a, r = self.a, self.report
        try:
            values = parse_dotenv(read_text(env_file))
        except OSError:
            values = {}
        current = values.get(a.token_var, "").strip()
        if not current:
            raise Stop("REAUTH_REQUIRED", "no token in env file (%s in %s)" % (a.token_var, env_file))
        _SECRETS.add(current)
        app_id = (values.get(a.app_id_var) or os.environ.get(a.app_id_var) or "").strip()
        app_secret = (values.get(a.app_secret_var) or os.environ.get(a.app_secret_var) or "").strip()
        _SECRETS.update(s for s in (app_id, app_secret) if s)
        have_app = bool(app_id and app_secret)
        if not have_app:
            self.note("app credentials not set: debug_token used the token as its own access_token")
        info_t = self.inspect(current, app_id, app_secret, "current")
        self.describe(info_t)
        if not have_app:
            self.note("exchange skipped: %s/%s not set" % (a.app_id_var, a.app_secret_var))
            raise Stop("NO_CHANGE", "exchange skipped: %s/%s not set" % (a.app_id_var, a.app_secret_var))
        candidate = self.exchange(current, app_id, app_secret)
        if candidate == current:
            raise Stop("NO_CHANGE", "Meta returned the same token; expiry unchanged")
        _SECRETS.add(candidate)
        info_c = self.inspect(candidate, app_id, app_secret, "candidate")
        if info_c["type"] != "USER":
            raise Stop("FAILED", "candidate is a %s token; the hosted MCP needs USER" % info_c["type"])
        missing = [s for s in REQUIRED_SCOPES if s not in info_c["scopes"]]
        if missing:
            raise Stop("FAILED", "candidate is missing scopes: %s" % ", ".join(missing))
        r["candidate_expires_at"] = iso(info_c["expires_at"])
        advancing = info_t["expires_at"] > 0 and info_c["expires_at"] > info_t["expires_at"] + ADVANCE_SECONDS
        outcome = "RENEWED" if advancing else "REPLACED_SAME_EXPIRY"
        r["would_write"] = advancing or bool(a.replace_same_expiry)
        if a.dry_run:
            raise Stop(outcome, "dry run: a live run would %s the candidate (expires %s)" % (
                "write" if r["would_write"] else "not write", r["candidate_expires_at"]))
        if not r["would_write"]:
            raise Stop(outcome, "candidate expiry did not advance (%s); not written. Pass --replace-same-expiry "
                                "to rotate anyway" % r["candidate_expires_at"])
        self.write_token(env_file, current, candidate)
        r["written"] = True
        self.describe(info_c)
        if a.no_smoke_test:
            r["smoke_test"] = "skipped (--no-smoke-test)"
        else:
            ok, detail = self.smoke_test(candidate)
            r["smoke_test"] = detail
            if not ok:
                self.rollback(env_file, candidate, current, info_t, detail)
            self.note("the bridge re-reads the env file per request; the live gateway uses the new token on its next call")
        raise Stop(outcome, "new token written to %s%s" % (env_file, "" if advancing else " (same expiry, forced)"))

    def rollback(self, env_file, candidate, current, info_t, detail):
        try:
            self.write_token(env_file, candidate, current)
        except Stop as exc:
            raise Stop("FAILED", "smoke test failed (%s) and rollback failed: %s; the env file may hold the "
                                 "untested token" % (detail, exc.message))
        self.report["written"], self.report["rolled_back"] = False, True
        self.describe(info_t)
        raise Stop("FAILED", "smoke test failed (%s); rolled back to the previous token" % detail)

    # -- wrap-up ------------------------------------------------------------------
    def exit_code(self):
        r, outcome = self.report, self.report["outcome"]
        if outcome not in HEALTHY:
            return 2
        if outcome == "REPLACED_SAME_EXPIRY" and not r["written"]:
            return 1
        return 1 if r["days_remaining"] is not None and r["days_remaining"] < self.a.min_days else 0

    def next_steps(self):
        r, a, outcome = self.report, self.a, self.report["outcome"]
        if outcome == "REAUTH_REQUIRED":
            return ("a human must mint a new USER token with all seven scopes, exchange it for a long-lived one, "
                    "and store it as %s in %s (docs/meta-authentication.md); then re-run" % (a.token_var, r["env_file"]))
        if outcome == "FAILED":
            return "fix the reported error and re-run" + (" (the previous token was restored)" if r["rolled_back"] else "")
        if outcome == "REPLACED_SAME_EXPIRY" and not r["written"]:
            steps = "no action needed for the same-expiry candidate; re-run with --replace-same-expiry only to rotate the string"
        else:
            steps = "nothing to do"
        if r["days_remaining"] is not None and r["days_remaining"] < a.min_days:
            steps += "; fewer than %g days remain and Meta did not advance the expiry: plan a manual re-auth before %s" % (
                a.min_days, r["expires_at"])
        return steps

    def save_state(self, path):
        r, outcome, now_iso = self.report, self.report["outcome"], iso(self.now())
        prev = load_state(path)
        runs, last_adv = int(prev.get("consecutive_non_advancing_runs") or 0), prev.get("last_advancing_expiry_at")
        if outcome == "RENEWED":
            runs, last_adv = 0, now_iso
        elif outcome in ("NO_CHANGE", "REPLACED_SAME_EXPIRY"):
            runs += 1
        state = {"schema_version": 1, "last_run": now_iso, "last_outcome": outcome, "expires_at": r["expires_at"],
                 "data_access_expires_at": r["data_access_expires_at"], "last_advancing_expiry_at": last_adv,
                 "consecutive_non_advancing_runs": runs, "days_remaining": r["days_remaining"],
                 "notes": [redact(n)[:200] for n in [r["message"]] + r["notes"] if n][:10]}
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            atomic_write(path, json.dumps(state, indent=2, sort_keys=True) + "\n")
        except OSError as exc:
            self.note("state file not written: %s" % type(exc).__name__)
        r["consecutive_non_advancing_runs"] = runs

    def run(self):
        a, r = self.a, self.report
        r["env_file"], r["state_file"] = resolve_env_file(a.env_file), resolve_state_file(a.state_file)
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
        r["exit_code"], r["next_steps"] = self.exit_code(), self.next_steps()
        if write_state:
            self.save_state(r["state_file"])
        if lock_fd is not None:
            os.close(lock_fd)
        return r["exit_code"]


# ---------------------------------------------------------------- output and CLI

def print_report(r, as_json):
    if as_json:
        print(redact(json.dumps(r, sort_keys=True)))
    else:
        scopes = None if r["scopes_ok"] is None else ("yes" if r["scopes_ok"] else "missing " + ", ".join(r["missing_scopes"]))
        deadline = r["next_renewal_deadline"] and "%s (expiry minus %g days)" % (r["next_renewal_deadline"], r["min_days"])
        rows = [("outcome", r["outcome"]), ("message", r["message"]), ("token type", r["token_type"]),
                ("scopes ok", scopes), ("expires_at", r["expires_at"]),
                ("data_access_expires_at", r["data_access_expires_at"]), ("days remaining", r["days_remaining"]),
                ("written", "rolled back" if r["rolled_back"] else ("yes" if r["written"] else "no")),
                ("smoke test", r["smoke_test"]), ("next renewal deadline", deadline),
                ("notes", "; ".join(r["notes"]) or "none"), ("next steps", r["next_steps"])]
        print("Meta token maintenance%s: env=%s state=%s" % (" (dry run)" if r["dry_run"] else "", r["env_file"], r["state_file"]))
        for key, value in rows:
            print(redact("  %-23s %s" % (key + ":", "unknown" if value is None else value)))
    print("Outcome: %s" % r["outcome"])


def build_arg_parser():
    p = argparse.ArgumentParser(description="Keep the Meta user token for the hosted Ads MCP fresh (deterministic).")
    p.add_argument("--env-file", help="dotenv file holding the token (default: auto-detect, see resolve_env_file)")
    p.add_argument("--token-var", default="META_MCP_TOKEN")
    p.add_argument("--app-id-var", default="META_APP_ID")
    p.add_argument("--app-secret-var", default="META_APP_SECRET")
    p.add_argument("--dry-run", action="store_true", help="inspect and exchange, report, write nothing")
    p.add_argument("--json", action="store_true", help="one JSON line, then the Outcome line")
    p.add_argument("--replace-same-expiry", action="store_true", help="also write a candidate whose expiry did not advance")
    p.add_argument("--min-days", type=float, default=21, help="exit 1 when fewer days remain (default 21)")
    p.add_argument("--state-file", help="default $HERMES_HOME/hermes-ad-agent/token-maintenance-state.json")
    p.add_argument("--no-smoke-test", action="store_true")
    p.add_argument("--upstream", default=DEFAULT_UPSTREAM)
    p.add_argument("--graph-version", default=DEFAULT_GRAPH_VERSION)
    return p


def main(argv=None, graph_get_fn=None, mcp_post_fn=None, now=None):
    args = build_arg_parser().parse_args(argv)
    maintainer = Maintainer(args, graph_get_fn, mcp_post_fn, now)
    code = maintainer.run()
    maintainer.report["min_days"] = args.min_days
    print_report(maintainer.report, args.json)
    return code


if __name__ == "__main__":
    sys.exit(main())
