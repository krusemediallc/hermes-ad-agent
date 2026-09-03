"""Unit tests for scripts/meta_mcp_bridge.py (standard library unittest only).

Run from the repo root:

    python3 -m unittest tests.test_meta_mcp_bridge -v

The bridge is imported by path so the tests work without installing anything. Every
HTTP call goes through a fake ``http_post`` that records what the bridge sent and
returns scripted ``(status, headers, text)`` tuples; nothing touches the network.
"""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
BRIDGE_PATH = os.path.join(SCRIPTS_DIR, "meta_mcp_bridge.py")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


def _load_bridge_module():
    spec = importlib.util.spec_from_file_location("meta_mcp_bridge", BRIDGE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["meta_mcp_bridge"] = module
    spec.loader.exec_module(module)
    return module


bridge_mod = _load_bridge_module()

# The fake tokens are assembled at runtime so the literal never appears in the repo:
# .github/workflows/verify.yml greps every file for EAA[A-Za-z0-9]{20,} and fails the
# build on a match. At runtime both values match the bridge's TOKEN_RE (EAA + 25 chars).
TOKEN_A = "EAA" + "fakeBridgeToken1234567890"
TOKEN_B = "EAA" + "fakeBridgeToken0987654321"
ALL_TOKENS = (TOKEN_A, TOKEN_B)

UPSTREAM = "https://mcp.facebook.com/ads"
TOKEN_VAR = "META_MCP_TOKEN"
BASE_MTIME = 1_700_000_000
JSON_HEADERS = {"content-type": "application/json"}
SSE_HEADERS = {"content-type": "text/event-stream; charset=utf-8"}

# Environment variables the bridge consults. Every test scrubs them so a developer's
# real shell environment cannot change the outcome.
BRIDGE_ENV_VARS = ("META_MCP_TOKEN", "META_MCP_ENV_FILE", "HERMES_HOME",
                   "META_MCP_UPSTREAM", "META_MCP_TOKEN_VAR")


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def assert_no_tokens(test: unittest.TestCase, text: str, where: str = "output"):
    for token in ALL_TOKENS:
        test.assertNotIn(token, text, "fake token leaked into %s" % where)


def write_env_file(path: str, token=None, mtime=BASE_MTIME, extra_lines=()):
    lines = list(extra_lines)
    if token is not None:
        lines.append("%s='%s'" % (TOKEN_VAR, token))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.utime(path, (mtime, mtime))


def request(request_id, method, params=None):
    msg = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def notification(method, params=None):
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    return msg


def result_msg(request_id, payload):
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def error_msg(request_id, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": err}


def json_response(status, message=None, session=None, text=None):
    headers = dict(JSON_HEADERS)
    if session:
        headers["mcp-session-id"] = session
    body = text if text is not None else (json.dumps(message) if message is not None else "")
    return status, headers, body


def sse_body(*messages):
    return "".join("event: message\ndata: %s\n\n" % json.dumps(m) for m in messages)


def sse_response(*messages, status=200, session=None):
    headers = dict(SSE_HEADERS)
    if session:
        headers["mcp-session-id"] = session
    return status, headers, sse_body(*messages)


class FakeHttp:
    """Stand-in for default_http_post: records calls, replays scripted outcomes.

    ``responses`` is consumed in order; an item that is an exception instance is raised.
    ``router`` (a callable taking the recorded call dict) overrides the script when given,
    which keeps multi-threaded tests order-independent.
    """

    def __init__(self, responses=(), router=None):
        self.responses = list(responses)
        self.router = router
        self.calls = []
        self._lock = threading.Lock()

    def __call__(self, url, headers, body, timeout, want_id=None):
        if not isinstance(body, (bytes, bytearray)):
            raise AssertionError("bridge must POST bytes, got %r" % type(body))
        call = {
            "url": url,
            "headers": dict(headers),
            "body": json.loads(body.decode("utf-8")),
            "timeout": timeout,
            "want_id": want_id,
        }
        with self._lock:
            self.calls.append(call)
            if self.router is not None:
                outcome = self.router(call)
            elif self.responses:
                outcome = self.responses.pop(0)
            else:
                raise AssertionError("fake http_post called more often than scripted: %r" % call["body"])
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class RecordingLog:
    def __init__(self):
        self.lines = []
        self._lock = threading.Lock()

    def __call__(self, level, msg):
        with self._lock:
            self.lines.append((level, msg))

    def text(self):
        return "\n".join("%s: %s" % pair for pair in self.lines)

    def messages(self, level=None):
        return [msg for lvl, msg in self.lines if level is None or lvl == level]


class ScrubbedEnvMixin:
    """Snapshot os.environ, remove every bridge-related variable, restore on exit."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        for var in BRIDGE_ENV_VARS:
            os.environ.pop(var, None)

    def make_temp_dir(self) -> str:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return tmp.name

    def make_env_file(self, token=None, mtime=BASE_MTIME, extra_lines=()) -> str:
        path = os.path.join(self.make_temp_dir(), ".env")
        write_env_file(path, token, mtime, extra_lines)
        return path


# ----------------------------------------------------------------------------
# 1. parse_dotenv
# ----------------------------------------------------------------------------

class ParseDotenvTests(unittest.TestCase):
    def parse(self, *lines):
        return bridge_mod.parse_dotenv("\n".join(lines) + "\n")

    def test_plain_and_export_prefix(self):
        self.assertEqual(self.parse("PLAIN=value", "export EXPORTED=exported-value"),
                         {"PLAIN": "value", "EXPORTED": "exported-value"})

    def test_single_and_double_quotes_are_stripped(self):
        self.assertEqual(self.parse("SINGLE='single quoted'", 'DOUBLE="double quoted"',
                                    "export QUOTED_EXPORT='%s'" % TOKEN_A),
                         {"SINGLE": "single quoted", "DOUBLE": "double quoted",
                          "QUOTED_EXPORT": TOKEN_A})

    def test_comment_lines_and_blank_lines_are_skipped(self):
        parsed = self.parse("# a full-line comment", "", "   ", "KEY=value", "  # indented comment")
        self.assertEqual(parsed, {"KEY": "value"})

    def test_unquoted_trailing_comment_is_removed(self):
        self.assertEqual(self.parse("KEY=value # trailing note"), {"KEY": "value"})
        self.assertEqual(self.parse("KEY=value   #   spaced note"), {"KEY": "value"})

    def test_hash_without_leading_space_is_part_of_the_value(self):
        self.assertEqual(self.parse("KEY=abc#def"), {"KEY": "abc#def"})

    def test_equals_and_hash_inside_quotes_are_preserved(self):
        parsed = self.parse("EQ_HASH='a=b#c # still the value'", 'DQ="x=y=z # not a comment"')
        self.assertEqual(parsed, {"EQ_HASH": "a=b#c # still the value",
                                  "DQ": "x=y=z # not a comment"})

    def test_unquoted_value_splits_on_first_equals_only(self):
        self.assertEqual(self.parse("KEY=a=b=c"), {"KEY": "a=b=c"})

    def test_whitespace_around_key_and_value_is_trimmed(self):
        self.assertEqual(self.parse("  SPACED  =  padded  "), {"SPACED": "padded"})

    def test_lines_without_equals_or_key_are_ignored(self):
        self.assertEqual(self.parse("NOEQUALS", "=no-key", "OK=1"), {"OK": "1"})

    def test_later_assignment_wins_and_crlf_is_accepted(self):
        self.assertEqual(bridge_mod.parse_dotenv("A=1\r\nA=2\r\nB=3\r\n"), {"A": "2", "B": "3"})

    def test_empty_text(self):
        self.assertEqual(bridge_mod.parse_dotenv(""), {})


# ----------------------------------------------------------------------------
# 2. strip_empty_meta
# ----------------------------------------------------------------------------

class StripEmptyMetaTests(unittest.TestCase):
    def test_removes_empty_meta_and_keeps_other_params(self):
        msg = request(1, "initialize", {"protocolVersion": "2025-06-18", "_meta": {}})
        out = bridge_mod.strip_empty_meta(msg)
        self.assertEqual(out, request(1, "initialize", {"protocolVersion": "2025-06-18"}))
        self.assertNotIn("_meta", out["params"])

    def test_preserves_non_empty_meta(self):
        msg = request(1, "tools/call", {"name": "x", "_meta": {"progressToken": "p1"}})
        self.assertEqual(bridge_mod.strip_empty_meta(msg), msg)

    def test_preserves_null_meta(self):
        msg = request(1, "tools/call", {"_meta": None})
        self.assertEqual(bridge_mod.strip_empty_meta(msg), msg)

    def test_message_without_params_is_unchanged(self):
        msg = request(1, "ping")
        self.assertEqual(bridge_mod.strip_empty_meta(msg), msg)

    def test_params_without_meta_is_unchanged(self):
        msg = request(1, "tools/list", {"cursor": "abc"})
        self.assertEqual(bridge_mod.strip_empty_meta(msg), msg)

    def test_non_dict_params_is_unchanged(self):
        msg = request(1, "weird", ["positional"])
        self.assertEqual(bridge_mod.strip_empty_meta(msg), msg)

    def test_does_not_mutate_the_input(self):
        msg = request(1, "initialize", {"capabilities": {}, "_meta": {}})
        snapshot = copy.deepcopy(msg)
        out = bridge_mod.strip_empty_meta(msg)
        self.assertEqual(msg, snapshot)
        self.assertIn("_meta", msg["params"])
        self.assertIsNot(out, msg)
        self.assertIsNot(out["params"], msg["params"])


# ----------------------------------------------------------------------------
# 3. parse_sse
# ----------------------------------------------------------------------------

class ParseSseTests(unittest.TestCase):
    def test_multi_event_stream_with_comments_and_junk(self):
        stream = (
            "event: message\n"
            "id: 1\n"
            'data: {"jsonrpc":"2.0","method":"notifications/message","params":{"level":"info"}}\n'
            "\n"
            ": keepalive comment inside an event\n"
            'data: {"jsonrpc":"2.0","id":5,"result":{"ok":true}}\n'
            "\n"
            "data: this is not json\n"
            "\n"
            ": a comment-only event\n"
            "\n"
            "data: 42\n"
            "\n"
            'data:{"jsonrpc":"2.0","id":6,"result":{}}\n'
            "\n"
        )
        self.assertEqual(bridge_mod.parse_sse(stream), [
            {"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info"}},
            {"jsonrpc": "2.0", "id": 5, "result": {"ok": True}},
            {"jsonrpc": "2.0", "id": 6, "result": {}},
        ])

    def test_data_spanning_two_lines_is_joined(self):
        stream = 'data: {"jsonrpc":"2.0",\ndata: "id":1,"result":{"joined":true}}\n\n'
        self.assertEqual(bridge_mod.parse_sse(stream),
                         [{"jsonrpc": "2.0", "id": 1, "result": {"joined": True}}])

    def test_json_array_payload_expands_and_drops_non_objects(self):
        stream = 'data: [{"jsonrpc":"2.0","id":2,"result":{}},{"jsonrpc":"2.0","id":3,"result":{}},"junk",7]\n\n'
        self.assertEqual(bridge_mod.parse_sse(stream),
                         [{"jsonrpc": "2.0", "id": 2, "result": {}},
                          {"jsonrpc": "2.0", "id": 3, "result": {}}])

    def test_crlf_event_separators(self):
        stream = 'data: {"id":1,"result":{}}\r\n\r\ndata: {"id":2,"result":{}}\r\n\r\n'
        self.assertEqual(bridge_mod.parse_sse(stream),
                         [{"id": 1, "result": {}}, {"id": 2, "result": {}}])

    def test_empty_and_dataless_streams(self):
        self.assertEqual(bridge_mod.parse_sse(""), [])
        self.assertEqual(bridge_mod.parse_sse("event: ping\nid: 9\n\n"), [])
        self.assertEqual(bridge_mod.parse_sse("data:\n\n"), [])

    def test_stream_has_response_detects_the_wanted_id(self):
        stream = sse_body(notification("notifications/message"), result_msg(3, {}))
        self.assertTrue(bridge_mod._stream_has_response(stream, 3))
        self.assertFalse(bridge_mod._stream_has_response(stream, 4))
        self.assertFalse(bridge_mod._stream_has_response(sse_body(request(3, "sampling/createMessage")), 3))


# ----------------------------------------------------------------------------
# 4. check_upstream
# ----------------------------------------------------------------------------

class CheckUpstreamTests(unittest.TestCase):
    def test_accepts_meta_hosts_over_https(self):
        self.assertEqual(bridge_mod.check_upstream("https://mcp.facebook.com/ads"), "https://mcp.facebook.com/ads")
        self.assertEqual(bridge_mod.check_upstream("https://x.facebook.com/y"), "https://x.facebook.com/y")
        self.assertEqual(bridge_mod.check_upstream("https://MCP.FACEBOOK.COM/ads"), "https://MCP.FACEBOOK.COM/ads")

    def test_rejects_plain_http_to_meta(self):
        with self.assertRaises(ValueError) as ctx:
            bridge_mod.check_upstream("http://mcp.facebook.com/ads")
        self.assertIn("https", str(ctx.exception))

    def test_rejects_other_hosts(self):
        for url in ("https://evil.example.com/ads", "https://facebook.com.evil.example/ads",
                    "https://notfacebook.com/ads", "https://mcp.facebook.com.attacker.net/ads"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError) as ctx:
                    bridge_mod.check_upstream(url)
                self.assertIn("facebook.com", str(ctx.exception))

    def test_allow_any_upstream_accepts_local_http(self):
        self.assertEqual(bridge_mod.check_upstream("http://127.0.0.1:8000/mcp", allow_any=True),
                         "http://127.0.0.1:8000/mcp")
        self.assertEqual(bridge_mod.check_upstream("https://evil.example.com/ads", allow_any=True),
                         "https://evil.example.com/ads")

    def test_allow_any_upstream_still_requires_an_http_url(self):
        for url in ("ftp://127.0.0.1/mcp", "not a url", "https://", ""):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    bridge_mod.check_upstream(url, allow_any=True)

    def test_main_exits_2_on_bad_upstream(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = bridge_mod.main(["--upstream", "https://evil.example.com/ads"])
        self.assertEqual(rc, 2)
        self.assertIn("facebook.com", buf.getvalue())


# ----------------------------------------------------------------------------
# resolve_env_file, jsonrpc_error, build_arg_parser
# ----------------------------------------------------------------------------

class ResolveEnvFileTests(ScrubbedEnvMixin, unittest.TestCase):
    HOME = "/fake-home"

    def resolve(self, explicit, existing, env=None):
        existing = set(existing)
        with mock.patch.dict(os.environ, env or {}), \
                mock.patch("os.path.isfile", side_effect=lambda p: p in existing), \
                mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", self.HOME, 1)):
            return bridge_mod.resolve_env_file(explicit)

    def test_explicit_path_wins_when_it_exists(self):
        self.assertEqual(self.resolve("/x/.env", {"/x/.env", "/env-var/.env", "/data/.env"},
                                      {"META_MCP_ENV_FILE": "/env-var/.env"}), "/x/.env")

    def test_env_var_path_is_next(self):
        self.assertEqual(self.resolve("/missing/.env", {"/env-var/.env", "/hh/.env", "/data/.env"},
                                      {"META_MCP_ENV_FILE": "/env-var/.env", "HERMES_HOME": "/hh"}),
                         "/env-var/.env")

    def test_hermes_home_env_is_next(self):
        self.assertEqual(self.resolve(None, {"/hh/.env", "/data/.env"}, {"HERMES_HOME": "/hh"}), "/hh/.env")

    def test_data_env_then_home_hermes_env(self):
        self.assertEqual(self.resolve(None, {"/data/.env", self.HOME + "/.hermes/.env"}), "/data/.env")
        self.assertEqual(self.resolve(None, {self.HOME + "/.hermes/.env"}), self.HOME + "/.hermes/.env")

    def test_returns_explicit_even_if_missing_when_nothing_exists(self):
        self.assertEqual(self.resolve("/nowhere/.env", set()), "/nowhere/.env")
        self.assertIsNone(self.resolve(None, set()))


class JsonrpcErrorTests(unittest.TestCase):
    def test_shape_without_data(self):
        self.assertEqual(bridge_mod.jsonrpc_error(7, -32000, "boom"),
                         {"jsonrpc": "2.0", "id": 7, "error": {"code": -32000, "message": "boom"}})

    def test_shape_with_data_and_null_id(self):
        self.assertEqual(bridge_mod.jsonrpc_error(None, -32700, "parse", {"line": 3}),
                         {"jsonrpc": "2.0", "id": None,
                          "error": {"code": -32700, "message": "parse", "data": {"line": 3}}})

    def test_error_code_constants(self):
        self.assertEqual(bridge_mod.ERR_TRANSPORT, -32000)
        self.assertEqual(bridge_mod.ERR_NO_TOKEN, -32001)
        self.assertEqual(bridge_mod.ERR_SESSION_LOST, -32002)
        self.assertEqual(bridge_mod.ERR_UNAUTHORIZED, -32003)
        self.assertEqual(bridge_mod.ERR_UPSTREAM_HTTP, -32004)


class ArgParserTests(ScrubbedEnvMixin, unittest.TestCase):
    def test_defaults(self):
        args = bridge_mod.build_arg_parser().parse_args([])
        self.assertEqual(args.upstream, bridge_mod.DEFAULT_UPSTREAM)
        self.assertEqual(args.token_var, bridge_mod.DEFAULT_TOKEN_VAR)
        self.assertIsNone(args.env_file)
        self.assertEqual(args.timeout, 120.0)
        self.assertEqual(args.log_level, "info")
        self.assertFalse(args.allow_any_upstream)
        self.assertEqual(args.workers, 8)

    def test_env_overrides_for_upstream_and_token_var(self):
        with mock.patch.dict(os.environ, {"META_MCP_UPSTREAM": "https://alt.facebook.com/ads",
                                          "META_MCP_TOKEN_VAR": "OTHER_TOKEN"}):
            args = bridge_mod.build_arg_parser().parse_args([])
        self.assertEqual(args.upstream, "https://alt.facebook.com/ads")
        self.assertEqual(args.token_var, "OTHER_TOKEN")

    def test_main_runs_to_stdin_eof(self):
        env_path = self.make_env_file(TOKEN_A)
        err = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO("")), contextlib.redirect_stderr(err):
            rc = bridge_mod.main(["--upstream", "http://127.0.0.1:8000/mcp", "--allow-any-upstream",
                                  "--env-file", env_path, "--workers", "1"])
        self.assertEqual(rc, 0)
        self.assertIn("bridge ready: upstream=http://127.0.0.1:8000/mcp env_file=%s var=%s" % (env_path, TOKEN_VAR),
                      err.getvalue())
        self.assertIn("stdin closed; bridge exiting", err.getvalue())
        assert_no_tokens(self, err.getvalue(), "stderr")


# ----------------------------------------------------------------------------
# 12. redact and make_logger
# ----------------------------------------------------------------------------

class RedactionTests(unittest.TestCase):
    def test_masks_meta_tokens(self):
        out = bridge_mod.redact("Bearer %s and again %s." % (TOKEN_A, TOKEN_B))
        self.assertEqual(out, "Bearer EAA[redacted] and again EAA[redacted].")
        assert_no_tokens(self, out)

    def test_masks_extra_secrets_of_eight_or_more_chars(self):
        out = bridge_mod.redact("pw=hunter2hunter2 short=abc", ("hunter2hunter2", "abc", "", None))
        self.assertEqual(out, "pw=[redacted] short=abc")

    def test_short_eaa_prefix_is_not_a_token(self):
        self.assertEqual(bridge_mod.redact("EAAshort"), "EAAshort")

    def test_empty_and_none_pass_through(self):
        self.assertEqual(bridge_mod.redact(""), "")
        self.assertIsNone(bridge_mod.redact(None))

    def test_non_string_input_is_stringified(self):
        self.assertEqual(bridge_mod.redact(12345), "12345")

    def test_make_logger_writes_redacted_lines_to_stderr(self):
        log = bridge_mod.make_logger("info")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            log("info", "token is %s here" % TOKEN_A)
            log("warning", "second %s" % TOKEN_B)
            log("debug", "debug-hidden")
        out = buf.getvalue()
        self.assertIn("[meta-bridge] info: token is EAA[redacted] here\n", out)
        self.assertIn("[meta-bridge] warning: second EAA[redacted]\n", out)
        self.assertNotIn("debug-hidden", out)
        assert_no_tokens(self, out, "stderr")

    def test_make_logger_threshold_and_unknown_levels(self):
        log = bridge_mod.make_logger("warning")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            log("info", "info-hidden")
            log("error", "error-shown")
            log("mystery", "unknown-level-treated-as-info")
        out = buf.getvalue()
        self.assertNotIn("info-hidden", out)
        self.assertIn("[meta-bridge] error: error-shown\n", out)
        self.assertNotIn("unknown-level", out)

        debug_log = bridge_mod.make_logger("debug")
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            debug_log("debug", "debug-shown")
        self.assertIn("[meta-bridge] debug: debug-shown\n", buf.getvalue())


# ----------------------------------------------------------------------------
# 5. TokenSource
# ----------------------------------------------------------------------------

class TokenSourceTests(ScrubbedEnvMixin, unittest.TestCase):
    def test_reads_token_from_env_file(self):
        path = self.make_env_file(TOKEN_A, extra_lines=("# comment", "OTHER=1"))
        self.assertEqual(bridge_mod.TokenSource(path, TOKEN_VAR).get(), TOKEN_A)

    def test_picks_up_rewritten_file_by_mtime(self):
        path = self.make_env_file(TOKEN_A, mtime=BASE_MTIME)
        source = bridge_mod.TokenSource(path, TOKEN_VAR)
        self.assertEqual(source.get(), TOKEN_A)
        self.assertEqual(source.get(), TOKEN_A)
        write_env_file(path, TOKEN_B, mtime=BASE_MTIME + 60)
        self.assertEqual(source.get(), TOKEN_B)
        self.assertEqual(source.get(), TOKEN_B)

    def test_rereads_after_recheck_interval_even_without_mtime_change(self):
        path = self.make_env_file(TOKEN_A, mtime=BASE_MTIME)
        source = bridge_mod.TokenSource(path, TOKEN_VAR)
        self.assertEqual(source.get(), TOKEN_A)
        write_env_file(path, TOKEN_B, mtime=BASE_MTIME)  # same mtime: only the timer can notice
        self.assertEqual(source.get(), TOKEN_A)
        with mock.patch.object(bridge_mod.time, "monotonic",
                               return_value=source._checked_at + bridge_mod.ENV_RECHECK_SECONDS + 1):
            self.assertEqual(source.get(), TOKEN_B)

    def test_falls_back_to_process_env_when_file_lacks_var(self):
        path = self.make_env_file(None, extra_lines=("OTHER=1",))
        with mock.patch.dict(os.environ, {TOKEN_VAR: "  " + TOKEN_B + "  "}):
            self.assertEqual(bridge_mod.TokenSource(path, TOKEN_VAR).get(), TOKEN_B)

    def test_file_value_beats_process_env(self):
        path = self.make_env_file(TOKEN_A)
        with mock.patch.dict(os.environ, {TOKEN_VAR: TOKEN_B}):
            self.assertEqual(bridge_mod.TokenSource(path, TOKEN_VAR).get(), TOKEN_A)

    def test_returns_none_when_neither_exists(self):
        path = self.make_env_file(None, extra_lines=("OTHER=1",))
        self.assertIsNone(bridge_mod.TokenSource(path, TOKEN_VAR).get())
        self.assertIsNone(bridge_mod.TokenSource(None, TOKEN_VAR).get())
        self.assertIsNone(bridge_mod.TokenSource(os.path.join(self.make_temp_dir(), "missing.env"), TOKEN_VAR).get())

    def test_empty_value_in_file_counts_as_missing(self):
        path = self.make_env_file(None, extra_lines=("%s=''" % TOKEN_VAR, "%s=" % TOKEN_VAR))
        self.assertIsNone(bridge_mod.TokenSource(path, TOKEN_VAR).get())
        with mock.patch.dict(os.environ, {TOKEN_VAR: TOKEN_B}):
            self.assertEqual(bridge_mod.TokenSource(path, TOKEN_VAR).get(), TOKEN_B)

    def test_no_env_file_uses_process_env(self):
        with mock.patch.dict(os.environ, {TOKEN_VAR: TOKEN_A}):
            self.assertEqual(bridge_mod.TokenSource(None, TOKEN_VAR).get(), TOKEN_A)

    def test_deleted_file_falls_back_to_process_env(self):
        path = self.make_env_file(TOKEN_A)
        source = bridge_mod.TokenSource(path, TOKEN_VAR)
        self.assertEqual(source.get(), TOKEN_A)
        os.remove(path)
        with mock.patch.dict(os.environ, {TOKEN_VAR: TOKEN_B}):
            self.assertEqual(source.get(), TOKEN_B)
        self.assertIsNone(source.get())

    def test_custom_var_name(self):
        path = self.make_env_file(None, extra_lines=("ACCESS_TOKEN='%s'" % TOKEN_A,))
        self.assertEqual(bridge_mod.TokenSource(path, "ACCESS_TOKEN").get(), TOKEN_A)
        self.assertIsNone(bridge_mod.TokenSource(path, TOKEN_VAR).get())


# ----------------------------------------------------------------------------
# Bridge fixtures
# ----------------------------------------------------------------------------

class BridgeTestCase(ScrubbedEnvMixin, unittest.TestCase):
    TIMEOUT = 33.5

    def setUp(self):
        super().setUp()
        self.env_path = self.make_env_file(TOKEN_A)
        self.tokens = bridge_mod.TokenSource(self.env_path, TOKEN_VAR)
        self.log = RecordingLog()
        self.http = None
        self.emitted = []

    def tearDown(self):
        assert_no_tokens(self, self.log.text(), "the bridge log")
        assert_no_tokens(self, json.dumps(self.emitted), "messages emitted to stdout")
        super().tearDown()

    def make_bridge(self, responses=(), router=None, upstream=UPSTREAM):
        self.http = FakeHttp(responses, router)
        self.bridge = bridge_mod.Bridge(upstream, self.tokens, http_post=self.http,
                                        timeout=self.TIMEOUT, log=self.log)
        return self.bridge

    def handle(self, message):
        out = self.bridge.handle(message)
        self.assertIsInstance(out, list)
        self.emitted.extend(out)
        return out

    def rotate_token(self, token, mtime):
        write_env_file(self.env_path, token, mtime=mtime)

    def initialize(self, request_id=1, client_version="2025-06-18"):
        init = request(request_id, "initialize", {"protocolVersion": client_version, "capabilities": {},
                                                   "clientInfo": {"name": "t", "version": "0"}, "_meta": {}})
        return self.handle(init)

    def initialize_response(self, request_id=1, session="sess-1", server_version="2025-03-26"):
        return json_response(200, result_msg(request_id, {"protocolVersion": server_version, "capabilities": {},
                                                           "serverInfo": {"name": "meta", "version": "1"}}),
                             session=session)


# ----------------------------------------------------------------------------
# 6 + 7. Request path: headers, _meta stripping, session, protocol, token rotation
# ----------------------------------------------------------------------------

class BridgeRequestTests(BridgeTestCase):
    def test_initialize_forwarded_without_empty_meta_and_with_expected_headers(self):
        self.make_bridge([self.initialize_response(session="sess-1", server_version="2025-03-26")])
        out = self.initialize(client_version="2025-06-18")

        self.assertEqual(len(self.http.calls), 1)
        call = self.http.calls[0]
        self.assertEqual(call["url"], UPSTREAM)
        self.assertEqual(call["timeout"], self.TIMEOUT)
        self.assertEqual(call["want_id"], 1)
        self.assertEqual(call["body"]["method"], "initialize")
        self.assertNotIn("_meta", call["body"]["params"])
        self.assertEqual(call["body"]["params"]["protocolVersion"], "2025-06-18")
        self.assertEqual(call["body"]["id"], 1)

        headers = call["headers"]
        self.assertEqual(headers["Authorization"], "Bearer " + TOKEN_A)
        self.assertIn("text/event-stream", headers["Accept"])
        self.assertIn("application/json", headers["Accept"])
        self.assertEqual(headers["Accept-Encoding"], "identity")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["MCP-Protocol-Version"], "2025-06-18")
        self.assertNotIn("Mcp-Session-Id", headers)
        self.assertTrue(headers.get("User-Agent"))

        self.assertEqual(out, [result_msg(1, {"protocolVersion": "2025-03-26", "capabilities": {},
                                              "serverInfo": {"name": "meta", "version": "1"}})])
        self.assertEqual(self.bridge.session_id, "sess-1")
        self.assertEqual(self.bridge.protocol_version, "2025-03-26")

    def test_later_requests_carry_session_and_negotiated_protocol_version(self):
        self.make_bridge([
            self.initialize_response(session="sess-1", server_version="2025-03-26"),
            json_response(200, result_msg(2, {"tools": []})),
            json_response(200, result_msg("str-id", {"content": []})),
        ])
        self.initialize()
        out = self.handle(request(2, "tools/list", {"_meta": {}}))
        self.assertEqual(out, [result_msg(2, {"tools": []})])
        call = self.http.calls[1]
        self.assertEqual(call["headers"]["Mcp-Session-Id"], "sess-1")
        self.assertEqual(call["headers"]["MCP-Protocol-Version"], "2025-03-26")
        self.assertEqual(call["headers"]["Authorization"], "Bearer " + TOKEN_A)
        self.assertNotIn("_meta", call["body"]["params"])
        self.assertEqual(call["want_id"], 2)

        out = self.handle(request("str-id", "tools/call", {"name": "x", "_meta": {"progressToken": 9}}))
        self.assertEqual(out, [result_msg("str-id", {"content": []})])
        call = self.http.calls[2]
        self.assertEqual(call["headers"]["Mcp-Session-Id"], "sess-1")
        self.assertEqual(call["body"]["params"]["_meta"], {"progressToken": 9})
        self.assertEqual(call["want_id"], "str-id")

    def test_no_session_header_before_initialize_and_missing_session_header_leaves_none(self):
        self.make_bridge([json_response(200, result_msg(1, {"protocolVersion": "2025-03-26"}))])
        self.initialize()
        self.assertIsNone(self.bridge.session_id)
        self.assertNotIn("Mcp-Session-Id", self.http.calls[0]["headers"])

    def test_reinitialize_drops_stale_session_and_adopts_the_new_one(self):
        self.make_bridge([
            self.initialize_response(session="sess-1"),
            self.initialize_response(request_id=9, session="sess-2"),
        ])
        self.initialize()
        self.assertEqual(self.bridge.session_id, "sess-1")
        self.initialize(request_id=9)
        self.assertNotIn("Mcp-Session-Id", self.http.calls[1]["headers"])
        self.assertEqual(self.bridge.session_id, "sess-2")

    def test_protocol_version_falls_back_when_client_and_server_omit_it(self):
        self.make_bridge([json_response(200, result_msg(1, {"capabilities": {}}), session="s")])
        self.handle(request(1, "initialize", {"capabilities": {}}))
        self.assertEqual(self.http.calls[0]["headers"]["MCP-Protocol-Version"], bridge_mod.FALLBACK_PROTOCOL_VERSION)
        self.assertEqual(self.bridge.protocol_version, bridge_mod.FALLBACK_PROTOCOL_VERSION)

    def test_token_rotation_between_requests(self):
        self.make_bridge([
            json_response(200, result_msg(1, {"a": 1})),
            json_response(200, result_msg(2, {"b": 2})),
        ])
        self.handle(request(1, "tools/list"))
        self.rotate_token(TOKEN_B, mtime=BASE_MTIME + 120)
        self.handle(request(2, "tools/list"))
        self.assertEqual(self.http.calls[0]["headers"]["Authorization"], "Bearer " + TOKEN_A)
        self.assertEqual(self.http.calls[1]["headers"]["Authorization"], "Bearer " + TOKEN_B)

    def test_non_dict_message_is_an_invalid_request(self):
        self.make_bridge()
        out = self.handle("not an object")
        self.assertEqual(out, [bridge_mod.jsonrpc_error(None, -32600, "invalid request: expected a JSON object")])
        self.assertEqual(self.http.calls, [])

    def test_kind_classification(self):
        kind = bridge_mod.Bridge.kind
        self.assertEqual(kind(request(1, "ping")), "request")
        self.assertEqual(kind(request(None, "ping")), "request")
        self.assertEqual(kind(notification("notifications/initialized")), "notification")
        self.assertEqual(kind(result_msg("srv-1", {})), "response")
        self.assertEqual(kind(error_msg("srv-1", -1, "x")), "response")

    def test_default_log_is_a_noop_and_default_transport_is_wired(self):
        bridge = bridge_mod.Bridge(UPSTREAM, self.tokens)
        self.assertIs(bridge.http_post, bridge_mod.default_http_post)
        self.assertIsNone(bridge.log("info", "ignored"))
        self.assertEqual(bridge.timeout, 120.0)


# ----------------------------------------------------------------------------
# 8. Error mapping
# ----------------------------------------------------------------------------

class BridgeErrorMappingTests(BridgeTestCase):
    def single_error(self, out, expected_id):
        self.assertEqual(len(out), 1, out)
        msg = out[0]
        self.assertEqual(msg["jsonrpc"], "2.0")
        self.assertEqual(msg["id"], expected_id)
        self.assertIn("error", msg)
        self.assertNotIn("result", msg)
        return msg["error"]

    def test_401_maps_to_unauthorized_and_points_at_the_doctor(self):
        self.make_bridge([(401, {"content-type": "text/plain", "www-authenticate": "Bearer"}, "Unauthorized")])
        err = self.single_error(self.handle(request(3, "tools/list")), 3)
        self.assertEqual(err["code"], bridge_mod.ERR_UNAUTHORIZED)
        self.assertEqual(err["code"], -32003)
        self.assertIn("401", err["message"])
        self.assertIn("doctor", err["message"])
        self.assertNotIn("data", err)

    def test_404_with_session_clears_it_and_maps_to_session_lost(self):
        self.make_bridge([
            self.initialize_response(session="sess-1"),
            (404, {"content-type": "text/plain"}, "Session not found"),
            json_response(200, result_msg(3, {})),
        ])
        self.initialize()
        self.assertEqual(self.bridge.session_id, "sess-1")
        err = self.single_error(self.handle(request(2, "tools/list")), 2)
        self.assertEqual(err["code"], bridge_mod.ERR_SESSION_LOST)
        self.assertEqual(err["code"], -32002)
        self.assertIn("initialize", err["message"])
        self.assertIsNone(self.bridge.session_id)
        self.handle(request(3, "tools/list"))
        self.assertNotIn("Mcp-Session-Id", self.http.calls[2]["headers"])

    def test_404_without_session_is_a_generic_upstream_http_error(self):
        self.make_bridge([(404, {"content-type": "text/plain"}, "Not Found")])
        err = self.single_error(self.handle(request(2, "tools/list")), 2)
        self.assertEqual(err["code"], bridge_mod.ERR_UPSTREAM_HTTP)
        self.assertIn("404", err["message"])

    def test_404_on_initialize_is_not_session_lost(self):
        self.make_bridge([(404, {"content-type": "text/plain"}, "Not Found")])
        self.bridge.session_id = "stale"
        err = self.single_error(self.initialize(), 1)
        self.assertEqual(err["code"], bridge_mod.ERR_UPSTREAM_HTTP)

    def test_400_jsonrpc_error_passes_code_through_and_redacts_message(self):
        upstream_message = '"meta" for Request must be an dict or null (seen %s)' % TOKEN_A
        self.make_bridge([json_response(400, error_msg(4, -32602, upstream_message))])
        err = self.single_error(self.handle(request(4, "tools/call", {"name": "x", "_meta": {"k": {}}})), 4)
        self.assertEqual(err["code"], -32602)
        self.assertIn("HTTP 400", err["message"])
        self.assertIn('"meta" for Request must be an dict or null', err["message"])
        self.assertIn("EAA[redacted]", err["message"])
        self.assertIn("empty params._meta rejected upstream", err["message"])
        self.assertNotIn(TOKEN_A, json.dumps(err))
        self.assertNotIn("data", err)

    def test_400_jsonrpc_error_without_meta_hint_and_with_data(self):
        self.make_bridge([json_response(400, error_msg(4, -32602, "Invalid params", {"detail": "cursor"}))])
        err = self.single_error(self.handle(request(4, "tools/list")), 4)
        self.assertEqual(err["code"], -32602)
        self.assertEqual(err["message"], "Meta MCP error (HTTP 400): Invalid params")
        self.assertEqual(err["data"], {"data": {"detail": "cursor"}})

    def test_400_jsonrpc_error_with_non_integer_code_falls_back(self):
        self.make_bridge([json_response(400, error_msg(4, "E_BAD", "bad"))])
        err = self.single_error(self.handle(request(4, "tools/list")), 4)
        self.assertEqual(err["code"], bridge_mod.ERR_UPSTREAM_HTTP)
        self.assertEqual(err["message"], "Meta MCP error (HTTP 400): bad")

    def test_400_jsonrpc_error_delivered_as_sse_is_still_extracted(self):
        self.make_bridge([sse_response(error_msg(4, -32601, "Method not found"), status=400)])
        err = self.single_error(self.handle(request(4, "nope")), 4)
        self.assertEqual(err["code"], -32601)
        self.assertIn("Method not found", err["message"])

    def test_500_plain_text_maps_to_upstream_http_error_and_is_redacted(self):
        self.make_bridge([(500, {"content-type": "text/html"}, "<h1>Internal Server Error</h1> token=%s" % TOKEN_A)])
        err = self.single_error(self.handle(request(5, "tools/list")), 5)
        self.assertEqual(err["code"], bridge_mod.ERR_UPSTREAM_HTTP)
        self.assertEqual(err["code"], -32004)
        self.assertIn("HTTP 500", err["message"])
        self.assertIn("Internal Server Error", err["message"])
        self.assertIn("EAA[redacted]", err["message"])

    def test_500_body_is_truncated_to_300_chars(self):
        self.make_bridge([(503, {"content-type": "text/plain"}, "x" * 1000)])
        err = self.single_error(self.handle(request(5, "tools/list")), 5)
        self.assertLess(len(err["message"]), 400)

    def test_transport_error_maps_to_minus_32000(self):
        self.make_bridge([bridge_mod.BridgeTransportError("<urlopen error [Errno 61] refused> bearer " + TOKEN_A)])
        err = self.single_error(self.handle(request(6, "tools/list")), 6)
        self.assertEqual(err["code"], bridge_mod.ERR_TRANSPORT)
        self.assertEqual(err["code"], -32000)
        self.assertIn("could not reach Meta MCP", err["message"])
        self.assertIn("refused", err["message"])
        self.assertNotIn(TOKEN_A, err["message"])

    def test_missing_token_maps_to_minus_32001_without_calling_upstream(self):
        write_env_file(self.env_path, None, mtime=BASE_MTIME + 5, extra_lines=("OTHER=1",))
        self.make_bridge()
        err = self.single_error(self.handle(request(7, "tools/list")), 7)
        self.assertEqual(err["code"], bridge_mod.ERR_NO_TOKEN)
        self.assertEqual(err["code"], -32001)
        self.assertIn(TOKEN_VAR, err["message"])
        self.assertIn("doctor", err["message"])
        self.assertEqual(self.http.calls, [])

    def test_missing_token_drops_notification_with_a_warning(self):
        write_env_file(self.env_path, None, mtime=BASE_MTIME + 5, extra_lines=("OTHER=1",))
        self.make_bridge()
        self.assertEqual(self.handle(notification("notifications/initialized")), [])
        self.assertEqual(self.http.calls, [])
        self.assertTrue(any("no Meta token" in m for m in self.log.messages("warning")), self.log.lines)

    def test_200_without_matching_response_id_synthesizes_an_error(self):
        stray = notification("notifications/message", {"level": "info", "data": "hi"})
        self.make_bridge([json_response(200, stray)])
        out = self.handle(request(8, "tools/list"))
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0], stray)
        self.assertEqual(out[1]["id"], 8)
        self.assertEqual(out[1]["error"]["code"], bridge_mod.ERR_UPSTREAM_HTTP)
        self.assertIn("HTTP 200 without a JSON-RPC response", out[1]["error"]["message"])

    def test_200_with_a_response_for_a_different_id_synthesizes_an_error(self):
        self.make_bridge([json_response(200, result_msg(99, {}))])
        out = self.handle(request(8, "tools/list"))
        self.assertEqual([m.get("id") for m in out], [99, 8])
        self.assertEqual(out[1]["error"]["code"], -32004)

    def test_200_empty_body_and_202_to_a_request_synthesize_an_error(self):
        self.make_bridge([json_response(200, text=""), (202, {}, "")])
        for expected_status in ("200", "202"):
            err = self.single_error(self.handle(request(8, "tools/list")), 8)
            self.assertEqual(err["code"], -32004)
            self.assertIn("HTTP %s without a JSON-RPC response" % expected_status, err["message"])

    def test_200_with_non_json_body_that_is_not_sse_synthesizes_an_error(self):
        self.make_bridge([(200, {"content-type": "text/html"}, "<html>login page</html>")])
        err = self.single_error(self.handle(request(8, "tools/list")), 8)
        self.assertEqual(err["code"], -32004)

    def test_error_response_from_upstream_counts_as_answered(self):
        self.make_bridge([json_response(200, error_msg(8, -32601, "Method not found"))])
        out = self.handle(request(8, "nope"))
        self.assertEqual(out, [error_msg(8, -32601, "Method not found")])

    # -- Known defect, documented here so the fix has a ready regression test. -------------
    # The bridge passes the upstream JSON-RPC error object through unredacted: as error.data
    # on the 401 and 404 paths, and as error.data.data on the generic path. Only error.message
    # is redacted (the bridge redacts the whole upstream error object, data included).

    def test_401_upstream_error_data_is_redacted(self):
        self.make_bridge([json_response(401, error_msg(1, -32001, "bad token " + TOKEN_A, {"echo": TOKEN_A}))])
        out = self.bridge.handle(request(1, "tools/list"))
        self.assertNotIn(TOKEN_A, json.dumps(out))

    def test_generic_upstream_error_data_is_redacted(self):
        self.make_bridge([json_response(400, error_msg(1, -32602, "bad params", {"echo": TOKEN_A}))])
        out = self.bridge.handle(request(1, "tools/list"))
        self.assertNotIn(TOKEN_A, json.dumps(out))


# ----------------------------------------------------------------------------
# 9. SSE response path
# ----------------------------------------------------------------------------

class BridgeSseTests(BridgeTestCase):
    def test_sse_notification_plus_response_are_both_returned(self):
        progress = notification("notifications/progress", {"progressToken": 1, "progress": 50})
        self.make_bridge([sse_response(progress, result_msg(2, {"tools": [{"name": "ads_get_ad_accounts"}]}))])
        out = self.handle(request(2, "tools/list"))
        self.assertEqual(out, [progress, result_msg(2, {"tools": [{"name": "ads_get_ad_accounts"}]})])
        self.assertEqual(out[-1]["id"], 2)

    def test_sse_initialize_captures_session_and_protocol_version(self):
        init_result = result_msg(1, {"protocolVersion": "2025-03-26", "capabilities": {}})
        self.make_bridge([sse_response(notification("notifications/message"), init_result, session="sse-sess"),
                          json_response(200, result_msg(2, {}))])
        out = self.initialize()
        self.assertEqual(out[-1], init_result)
        self.assertEqual(self.bridge.session_id, "sse-sess")
        self.assertEqual(self.bridge.protocol_version, "2025-03-26")
        self.handle(request(2, "ping"))
        self.assertEqual(self.http.calls[1]["headers"]["Mcp-Session-Id"], "sse-sess")
        self.assertEqual(self.http.calls[1]["headers"]["MCP-Protocol-Version"], "2025-03-26")

    def test_sse_shaped_body_under_json_content_type_is_still_parsed(self):
        self.make_bridge([(200, JSON_HEADERS, sse_body(result_msg(2, {"fallback": True})))])
        self.assertEqual(self.handle(request(2, "ping")), [result_msg(2, {"fallback": True})])

    def test_json_array_body_is_expanded(self):
        body = [notification("notifications/message"), result_msg(2, {}), "junk"]
        self.make_bridge([json_response(200, body)])
        self.assertEqual(self.handle(request(2, "ping")), [notification("notifications/message"), result_msg(2, {})])

    def test_sse_body_with_non_lowercase_content_type_key_still_parses(self):
        # The bridge expects the transport to lowercase header names; a non-lowercase key is
        # ignored for content-type, but the SSE fallback in _parse_body still finds the message.
        self.make_bridge([(200, {"Content-Type": "text/event-stream"}, sse_body(result_msg(2, {})))])
        self.assertEqual(self.handle(request(2, "ping")), [result_msg(2, {})])


# ----------------------------------------------------------------------------
# 10. Notifications and client responses
# ----------------------------------------------------------------------------

class BridgeNotificationTests(BridgeTestCase):
    def test_notification_is_forwarded_with_strip_and_202_returns_nothing(self):
        self.make_bridge([(202, {}, "")])
        out = self.handle(notification("notifications/initialized", {"_meta": {}}))
        self.assertEqual(out, [])
        call = self.http.calls[0]
        self.assertEqual(call["body"], {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        self.assertNotIn("_meta", call["body"]["params"])
        self.assertIsNone(call["want_id"])
        self.assertEqual(call["headers"]["Authorization"], "Bearer " + TOKEN_A)
        self.assertEqual(self.log.messages("warning"), [])

    def test_notification_carries_session_after_initialize(self):
        self.make_bridge([self.initialize_response(session="sess-1"), (202, {}, "")])
        self.initialize()
        self.handle(notification("notifications/initialized"))
        self.assertEqual(self.http.calls[1]["headers"]["Mcp-Session-Id"], "sess-1")

    def test_notification_200_and_204_return_nothing_quietly(self):
        self.make_bridge([json_response(200, text=""), (204, {}, "")])
        self.assertEqual(self.handle(notification("notifications/cancelled")), [])
        self.assertEqual(self.handle(notification("notifications/cancelled")), [])
        self.assertEqual(self.log.messages("warning"), [])

    def test_notification_non_2xx_is_only_logged_and_redacted(self):
        self.make_bridge([(400, JSON_HEADERS, json.dumps(error_msg(None, -32600, "bad %s" % TOKEN_A)))])
        self.assertEqual(self.handle(notification("notifications/initialized")), [])
        warnings = self.log.messages("warning")
        self.assertEqual(len(warnings), 1, self.log.lines)
        self.assertIn("upstream answered 400 to a notification", warnings[0])
        self.assertIn("EAA[redacted]", warnings[0])

    def test_notification_transport_error_is_only_logged(self):
        self.make_bridge([bridge_mod.BridgeTransportError("timed out " + TOKEN_A)])
        self.assertEqual(self.handle(notification("notifications/initialized")), [])
        warnings = self.log.messages("warning")
        self.assertEqual(len(warnings), 1)
        self.assertIn("transport error on notification", warnings[0])
        self.assertNotIn(TOKEN_A, warnings[0])

    def test_client_response_to_server_request_is_forwarded(self):
        self.make_bridge([(202, {}, "")])
        reply = result_msg("srv-1", {"role": "assistant"})
        self.assertEqual(self.handle(reply), [])
        self.assertEqual(self.http.calls[0]["body"], reply)
        self.assertIsNone(self.http.calls[0]["want_id"])


# ----------------------------------------------------------------------------
# 11. serve()
# ----------------------------------------------------------------------------

def echo_router(call):
    """Answer every request with a result carrying its id; accept notifications with 202."""
    body = call["body"]
    if "method" in body and "id" in body:
        return json_response(200, result_msg(body["id"], {"echo": body["method"]}))
    return 202, {}, ""


class ServeTests(BridgeTestCase):
    STDIN = "".join([
        json.dumps(request(1, "tools/list", {"_meta": {}})) + "\n",
        "\n",
        "this is not json\n",
        json.dumps([request(2, "ping"), notification("notifications/initialized")]) + "\n",
        "   \n",
    ])

    def run_serve(self, stdin_text, workers):
        stdout = io.StringIO()
        bridge_mod.serve(self.bridge, stdin=io.StringIO(stdin_text), stdout=stdout, workers=workers, log=self.log)
        text = stdout.getvalue()
        assert_no_tokens(self, text, "serve() stdout")
        lines = text.splitlines()
        self.assertTrue(all(line.strip() for line in lines), "no blank stdout lines")
        parsed = [json.loads(line) for line in lines]
        self.emitted.extend(parsed)
        self.assertEqual(text.count("\n"), len(lines), "every message ends with exactly one newline")
        return parsed

    def test_single_worker_emits_one_line_per_message_in_order(self):
        self.make_bridge(router=echo_router)
        out = self.run_serve(self.STDIN, workers=1)
        self.assertEqual(out, [
            result_msg(1, {"echo": "tools/list"}),
            bridge_mod.jsonrpc_error(None, -32700, "parse error: stdin line was not JSON"),
            result_msg(2, {"echo": "ping"}),
        ])
        self.assertEqual(out[1]["id"], None)
        self.assertEqual(out[1]["error"]["code"], -32700)
        self.assertNotIn("_meta", self.http.calls[0]["body"]["params"])
        self.assertEqual([c["body"].get("method") for c in self.http.calls],
                         ["tools/list", "ping", "notifications/initialized"])
        self.assertEqual(self.log.messages("info"), ["stdin closed; bridge exiting"])

    def test_multiple_workers_emit_the_same_set_of_messages(self):
        self.make_bridge(router=echo_router)
        out = self.run_serve(self.STDIN, workers=4)
        self.assertEqual(len(out), 3)
        keyed = sorted(json.dumps(m, sort_keys=True) for m in out)
        expected = sorted(json.dumps(m, sort_keys=True) for m in [
            result_msg(1, {"echo": "tools/list"}),
            bridge_mod.jsonrpc_error(None, -32700, "parse error: stdin line was not JSON"),
            result_msg(2, {"echo": "ping"}),
        ])
        self.assertEqual(keyed, expected)
        self.assertEqual(len(self.http.calls), 3)

    def test_each_stdout_line_is_compact_json(self):
        self.make_bridge(router=echo_router)
        stdout = io.StringIO()
        bridge_mod.serve(self.bridge, stdin=io.StringIO(json.dumps(request(1, "ping")) + "\n"),
                         stdout=stdout, workers=1, log=self.log)
        line = stdout.getvalue()
        self.assertEqual(line, '{"jsonrpc":"2.0","id":1,"result":{"echo":"ping"}}\n')

    def test_empty_stdin_emits_nothing(self):
        self.make_bridge()
        self.assertEqual(self.run_serve("", workers=2), [])
        self.assertEqual(self.http.calls, [])

    def test_internal_error_in_handle_yields_a_bridge_error_and_keeps_serving(self):
        def exploding_router(call):
            if call["body"].get("method") == "boom":
                return RuntimeError("unexpected " + TOKEN_A)
            return echo_router(call)

        self.make_bridge(router=exploding_router)
        stdin_text = "".join([
            json.dumps(request(1, "boom")) + "\n",
            json.dumps(notification("boom")) + "\n",
            json.dumps(request(2, "ping")) + "\n",
        ])
        out = self.run_serve(stdin_text, workers=1)
        self.assertEqual(out, [
            bridge_mod.jsonrpc_error(1, bridge_mod.ERR_TRANSPORT, "bridge internal error: RuntimeError"),
            result_msg(2, {"echo": "ping"}),
        ])
        errors = self.log.messages("error")
        self.assertEqual(errors, ["unhandled error: RuntimeError", "unhandled error: RuntimeError"])

    def test_no_token_flows_through_serve(self):
        write_env_file(self.env_path, None, mtime=BASE_MTIME + 5, extra_lines=("OTHER=1",))
        self.make_bridge()
        out = self.run_serve(json.dumps(request(1, "ping")) + "\n", workers=1)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["error"]["code"], -32001)
        self.assertEqual(self.http.calls, [])


if __name__ == "__main__":
    unittest.main()
