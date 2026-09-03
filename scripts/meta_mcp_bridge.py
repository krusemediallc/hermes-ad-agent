#!/usr/bin/env python3
"""meta_mcp_bridge.py: a local stdio MCP server that proxies to Meta's hosted Ads MCP.

Why this exists
---------------
Hermes talks to this script over stdio exactly as it would to any local MCP server.
The bridge forwards every JSON-RPC message to Meta's Streamable HTTP endpoint
(https://mcp.facebook.com/ads) and does three things the direct connection cannot:

1. Reads the bearer token from the env file on EVERY request, so a rotated token is
   picked up on the next call with no gateway restart and no managed-app redeploy.
2. Removes an empty ``params._meta`` object before forwarding. MCP SDK 2.0 clients add
   ``"_meta": {}`` and Meta answers HTTP 400 / JSON-RPC -32602
   ('"meta" for Request must be an dict or null'). Non-empty ``_meta`` is preserved.
3. Passes Meta's real JSON-RPC error code and message back to the client instead of a
   generic "server returned an error", so credential problems and protocol problems are
   distinguishable.

Security properties
-------------------
- The token is never written to stdout, stderr, or any file. Error text is redacted.
- The upstream must be an https URL on facebook.com unless ``--allow-any-upstream`` is
  passed explicitly (for local test servers only).
- No writes anywhere. Standard library only.

Hermes configuration (typical shape; verify flags with ``hermes mcp add --help``)::

    mcp_servers:
      meta_ads:
        command: python3
        args: ["/absolute/path/to/hermes-ad-agent/scripts/meta_mcp_bridge.py",
               "--env-file", "/data/.env"]
        trust: untrusted
        enabled: true

The env file holds one line ``META_MCP_TOKEN='<fully scoped USER access token>'``.
``scripts/meta_token_maintenance.py`` rewrites that line atomically; this bridge notices.

Usage::

    python3 scripts/meta_mcp_bridge.py [--env-file PATH] [--token-var META_MCP_TOKEN]
                                       [--upstream URL] [--timeout SECONDS]
                                       [--log-level info|debug|warning]
                                       [--allow-any-upstream]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

DEFAULT_UPSTREAM = "https://mcp.facebook.com/ads"
DEFAULT_TOKEN_VAR = "META_MCP_TOKEN"
ALLOWED_HOST_SUFFIX = ".facebook.com"
FALLBACK_PROTOCOL_VERSION = "2025-06-18"
TOKEN_RE = re.compile(r"EAA[A-Za-z0-9]{10,}")
ENV_RECHECK_SECONDS = 15.0

# JSON-RPC error codes used by the bridge itself (server-defined range).
ERR_TRANSPORT = -32000
ERR_NO_TOKEN = -32001
ERR_SESSION_LOST = -32002
ERR_UNAUTHORIZED = -32003
ERR_UPSTREAM_HTTP = -32004


class BridgeTransportError(Exception):
    """Raised when the upstream could not be reached at all."""


# ----------------------------------------------------------------------------
# Small pure helpers (unit-tested)
# ----------------------------------------------------------------------------

def redact(text: str, extra_secrets=()) -> str:
    """Remove anything that looks like a Meta token, plus any known secret values."""
    if not text:
        return text
    out = TOKEN_RE.sub("EAA[redacted]", str(text))
    for secret in extra_secrets:
        if secret and len(secret) >= 8:
            out = out.replace(secret, "[redacted]")
    return out


def parse_dotenv(text: str) -> dict:
    """Parse the dotenv forms Hermes, Meta's CLI, and humans actually write.

    Supports ``KEY=value``, ``export KEY=value``, single or double quotes, blank lines,
    full-line comments, and unquoted trailing comments (``KEY=value # note``).
    """
    result = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value and value[0] in ("'", '"'):
            closing = value.find(value[0], 1)
            if closing != -1:
                value = value[1:closing]
            else:
                value = value[1:]
        else:
            hash_at = value.find(" #")
            if hash_at != -1:
                value = value[:hash_at].rstrip()
        result[key] = value
    return result


def strip_empty_meta(message: dict) -> dict:
    """Drop ``params._meta`` only when it is an empty object. Everything else is untouched."""
    params = message.get("params")
    if isinstance(params, dict) and "_meta" in params and params["_meta"] == {}:
        params = dict(params)
        del params["_meta"]
        message = dict(message)
        message["params"] = params
    return message


def parse_sse(text: str) -> list:
    """Return the JSON-RPC messages carried by a text/event-stream body."""
    messages = []
    for event in re.split(r"\r?\n\r?\n", text):
        data_lines = []
        for line in event.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[len("data:"):].lstrip())
        if not data_lines:
            continue
        payload = "\n".join(data_lines).strip()
        if not payload:
            continue
        try:
            parsed = json.loads(payload)
        except ValueError:
            continue
        if isinstance(parsed, list):
            messages.extend(m for m in parsed if isinstance(m, dict))
        elif isinstance(parsed, dict):
            messages.append(parsed)
    return messages


def check_upstream(url: str, allow_any: bool = False) -> str:
    """Refuse to send a bearer token anywhere but Meta over https."""
    parsed = urllib.parse.urlparse(url)
    if allow_any:
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("upstream must be an http(s) URL")
        return url
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        raise ValueError("upstream must use https")
    if not (host == "mcp.facebook.com" or host.endswith(ALLOWED_HOST_SUFFIX)):
        raise ValueError("upstream host must be on facebook.com (pass --allow-any-upstream only for local tests)")
    return url


def resolve_env_file(explicit: str | None) -> str | None:
    """Pick the env file the same way SETUP.md describes, most specific first."""
    candidates = []
    if explicit:
        candidates.append(explicit)
    if os.environ.get("META_MCP_ENV_FILE"):
        candidates.append(os.environ["META_MCP_ENV_FILE"])
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        candidates.append(os.path.join(hermes_home, ".env"))
    candidates.append("/data/.env")
    candidates.append(os.path.expanduser("~/.hermes/.env"))
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return explicit


def jsonrpc_error(request_id, code: int, message: str, data=None) -> dict:
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": err}


# ----------------------------------------------------------------------------
# Token source: env file first (re-read when it changes), process env as fallback
# ----------------------------------------------------------------------------

class TokenSource:
    def __init__(self, env_file: str | None, var: str):
        self.env_file = env_file
        self.var = var
        self._lock = threading.Lock()
        self._cached = None
        self._mtime = None
        self._checked_at = 0.0

    def get(self) -> str | None:
        with self._lock:
            now = time.monotonic()
            if self.env_file and (now - self._checked_at) >= 0 and (
                self._cached is None or (now - self._checked_at) >= ENV_RECHECK_SECONDS
                or self._mtime != self._safe_mtime()
            ):
                self._reload()
                self._checked_at = now
            if self._cached:
                return self._cached
        value = os.environ.get(self.var)
        return value.strip() if value else None

    def _safe_mtime(self):
        try:
            return os.stat(self.env_file).st_mtime
        except OSError:
            return None

    def _reload(self):
        self._mtime = self._safe_mtime()
        if self._mtime is None:
            self._cached = None
            return
        try:
            with open(self.env_file, "r", encoding="utf-8") as fh:
                values = parse_dotenv(fh.read())
        except OSError:
            self._cached = None
            return
        token = values.get(self.var, "").strip()
        self._cached = token or None


# ----------------------------------------------------------------------------
# HTTP transport (injectable for tests)
# ----------------------------------------------------------------------------

def default_http_post(url: str, headers: dict, body: bytes, timeout: float, want_id=None):
    """POST and return (status, lowercase-header dict, body_text).

    For text/event-stream responses the body is read incrementally and reading stops as
    soon as the JSON-RPC response for ``want_id`` has arrived, so a server that keeps
    the stream open does not stall the bridge.
    """
    req = urllib.request.Request(url, data=body, method="POST")
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        raw = exc.read() if hasattr(exc, "read") else b""
        return exc.code, {k.lower(): v for k, v in exc.headers.items()}, raw.decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as exc:
        raise BridgeTransportError(str(exc)) from exc
    with resp:
        hdrs = {k.lower(): v for k, v in resp.headers.items()}
        ctype = hdrs.get("content-type", "")
        if "text/event-stream" not in ctype:
            return resp.status, hdrs, resp.read().decode("utf-8", "replace")
        chunks = []
        buffered = ""
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            piece = chunk.decode("utf-8", "replace")
            chunks.append(piece)
            buffered += piece
            if want_id is not None and _stream_has_response(buffered, want_id):
                break
        return resp.status, hdrs, "".join(chunks)


def _stream_has_response(buffered: str, want_id) -> bool:
    for msg in parse_sse(buffered):
        if msg.get("id") == want_id and ("result" in msg or "error" in msg):
            return True
    return False


# ----------------------------------------------------------------------------
# The bridge
# ----------------------------------------------------------------------------

class Bridge:
    def __init__(self, upstream: str, token_source: TokenSource, http_post=default_http_post,
                 timeout: float = 120.0, log=None):
        self.upstream = upstream
        self.tokens = token_source
        self.http_post = http_post
        self.timeout = timeout
        self.log = log or (lambda level, msg: None)
        self.session_id = None
        self.protocol_version = FALLBACK_PROTOCOL_VERSION
        self._state_lock = threading.Lock()

    # -- message classification -------------------------------------------------
    @staticmethod
    def kind(message: dict) -> str:
        if "method" in message:
            return "request" if "id" in message else "notification"
        return "response"

    def _headers(self, token: str, include_session: bool = True) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Accept-Encoding": "identity",
            "Authorization": "Bearer " + token,
            "MCP-Protocol-Version": self.protocol_version,
            "User-Agent": "hermes-ad-agent-meta-bridge/1.0",
        }
        if include_session and self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    # -- main entry point ---------------------------------------------------------
    def handle(self, message: dict) -> list:
        """Process one inbound JSON-RPC message; return the messages to emit on stdout."""
        if not isinstance(message, dict):
            return [jsonrpc_error(None, -32600, "invalid request: expected a JSON object")]
        kind = self.kind(message)
        request_id = message.get("id")
        message = strip_empty_meta(message)
        token = self.tokens.get()
        if not token:
            if kind == "request":
                return [jsonrpc_error(request_id, ERR_NO_TOKEN,
                                      "Meta token not found: set %s in the env file the bridge reads "
                                      "(see docs/meta-authentication.md, then re-run the doctor)"
                                      % self.tokens.var)]
            self.log("warning", "dropping %s: no Meta token available" % kind)
            return []

        method = message.get("method", "")
        is_initialize = method == "initialize"
        if is_initialize:
            with self._state_lock:
                self.session_id = None
                requested = (message.get("params") or {}).get("protocolVersion")
                if isinstance(requested, str) and requested:
                    self.protocol_version = requested

        body = json.dumps(message).encode("utf-8")
        try:
            status, headers, text = self.http_post(
                self.upstream, self._headers(token, include_session=not is_initialize),
                body, self.timeout, want_id=request_id if kind == "request" else None)
        except BridgeTransportError as exc:
            if kind == "request":
                return [jsonrpc_error(request_id, ERR_TRANSPORT,
                                      "could not reach Meta MCP: " + redact(str(exc), (token,)))]
            self.log("warning", "transport error on %s: %s" % (kind, redact(str(exc), (token,))))
            return []

        if kind != "request":
            if status not in (200, 202, 204):
                self.log("warning", "upstream answered %s to a %s (%s)"
                         % (status, kind, redact(text[:200], (token,))))
            return []

        return self._handle_request_response(request_id, is_initialize, status, headers, text, token)

    # -- response handling --------------------------------------------------------
    def _handle_request_response(self, request_id, is_initialize, status, headers, text, token):
        if status in (200, 202):
            messages = self._parse_body(headers, text)
            if is_initialize:
                with self._state_lock:
                    sid = headers.get("mcp-session-id")
                    if sid:
                        self.session_id = sid
                    for msg in messages:
                        result = msg.get("result") if isinstance(msg, dict) else None
                        if isinstance(result, dict) and isinstance(result.get("protocolVersion"), str):
                            self.protocol_version = result["protocolVersion"]
            answered = any(m.get("id") == request_id and ("result" in m or "error" in m) for m in messages)
            if not answered:
                messages.append(jsonrpc_error(request_id, ERR_UPSTREAM_HTTP,
                                              "Meta MCP returned HTTP %s without a JSON-RPC response" % status))
            return messages

        upstream_error = self._redact_obj(self._extract_jsonrpc_error(text), (token,))
        if status == 401:
            return [jsonrpc_error(request_id, ERR_UNAUTHORIZED,
                                  "Meta rejected the token (HTTP 401). Check that it is a USER token with all "
                                  "seven scopes and has not expired: python3 scripts/onboarding_doctor.py "
                                  "--meta-token-check",
                                  upstream_error)]
        if status == 404 and self.session_id and not is_initialize:
            with self._state_lock:
                self.session_id = None
            return [jsonrpc_error(request_id, ERR_SESSION_LOST,
                                  "Meta MCP session expired; the client must send initialize again",
                                  upstream_error)]
        if upstream_error:
            code = upstream_error.get("code", ERR_UPSTREAM_HTTP)
            msg = redact(str(upstream_error.get("message", "upstream error")), (token,))
            if "must be an dict or null" in msg:
                msg += (" (empty params._meta rejected upstream; the bridge strips it, so this request "
                        "carried a non-empty or nested _meta)")
            return [jsonrpc_error(request_id, code if isinstance(code, int) else ERR_UPSTREAM_HTTP,
                                  "Meta MCP error (HTTP %s): %s" % (status, msg),
                                  {k: v for k, v in upstream_error.items() if k == "data"} or None)]
        return [jsonrpc_error(request_id, ERR_UPSTREAM_HTTP,
                              "Meta MCP returned HTTP %s: %s" % (status, redact(text[:300], (token,))))]

    @staticmethod
    def _parse_body(headers: dict, text: str) -> list:
        ctype = headers.get("content-type", "")
        if "text/event-stream" in ctype:
            return parse_sse(text)
        text = text.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except ValueError:
            return parse_sse(text)
        if isinstance(parsed, list):
            return [m for m in parsed if isinstance(m, dict)]
        if isinstance(parsed, dict):
            return [parsed]
        return []

    @staticmethod
    def _redact_obj(obj, secrets=()):
        """Redact every string inside a JSON-compatible object (upstream error payloads)."""
        if obj is None:
            return None
        try:
            return json.loads(redact(json.dumps(obj), secrets))
        except (TypeError, ValueError):
            return {"message": redact(str(obj), secrets)}

    @staticmethod
    def _extract_jsonrpc_error(text: str):
        candidates = []
        stripped = (text or "").strip()
        if stripped:
            try:
                parsed = json.loads(stripped)
                candidates = parsed if isinstance(parsed, list) else [parsed]
            except ValueError:
                candidates = parse_sse(stripped)
        for msg in candidates:
            if isinstance(msg, dict) and isinstance(msg.get("error"), dict):
                return msg["error"]
        return None


# ----------------------------------------------------------------------------
# stdio loop
# ----------------------------------------------------------------------------

def make_logger(level: str):
    levels = {"debug": 10, "info": 20, "warning": 30, "error": 40}
    threshold = levels.get(level, 20)

    def log(lvl, msg):
        if levels.get(lvl, 20) >= threshold:
            sys.stderr.write("[meta-bridge] %s: %s\n" % (lvl, redact(msg)))
            sys.stderr.flush()
    return log


def serve(bridge: Bridge, stdin=None, stdout=None, workers: int = 8, log=None):
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    log = log or (lambda level, msg: None)
    out_lock = threading.Lock()

    def emit(messages):
        if not messages:
            return
        with out_lock:
            for msg in messages:
                stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
            stdout.flush()

    def process(raw_line: str):
        line = raw_line.strip()
        if not line:
            return
        try:
            parsed = json.loads(line)
        except ValueError:
            emit([jsonrpc_error(None, -32700, "parse error: stdin line was not JSON")])
            return
        items = parsed if isinstance(parsed, list) else [parsed]
        for item in items:
            try:
                emit(bridge.handle(item))
            except Exception as exc:  # noqa: BLE001 - never let one message kill the bridge
                log("error", "unhandled error: %s" % exc.__class__.__name__)
                if isinstance(item, dict) and "id" in item and "method" in item:
                    emit([jsonrpc_error(item.get("id"), ERR_TRANSPORT,
                                        "bridge internal error: " + exc.__class__.__name__)])

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for raw in stdin:
            pool.submit(process, raw)
    log("info", "stdin closed; bridge exiting")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="stdio MCP bridge to Meta's hosted Ads MCP")
    p.add_argument("--upstream", default=os.environ.get("META_MCP_UPSTREAM", DEFAULT_UPSTREAM))
    p.add_argument("--env-file", default=None, help="dotenv file holding the token (default: auto-detect)")
    p.add_argument("--token-var", default=os.environ.get("META_MCP_TOKEN_VAR", DEFAULT_TOKEN_VAR))
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])
    p.add_argument("--allow-any-upstream", action="store_true", help="local test servers only")
    p.add_argument("--workers", type=int, default=8)
    return p


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    log = make_logger(args.log_level)
    try:
        upstream = check_upstream(args.upstream, args.allow_any_upstream)
    except ValueError as exc:
        log("error", str(exc))
        return 2
    env_file = resolve_env_file(args.env_file)
    if not env_file and not os.environ.get(args.token_var):
        log("warning", "no env file found and %s is not in the environment; requests will fail until "
            "the token exists" % args.token_var)
    tokens = TokenSource(env_file, args.token_var)
    bridge = Bridge(upstream, tokens, timeout=args.timeout, log=log)
    log("info", "bridge ready: upstream=%s env_file=%s var=%s" % (upstream, env_file or "(none)", args.token_var))
    serve(bridge, workers=args.workers, log=log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
