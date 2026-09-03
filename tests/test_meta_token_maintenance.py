"""Tests for scripts/meta_token_maintenance.py. Standard library unittest, no network.

Run from the repo root:  python3 -m unittest discover -s tests -v

The Graph API, the MCP transport, and the `hermes mcp test` subprocess are replaced
with in-memory fakes. Every run asserts that the fake token strings and the fake app
secret never reach stdout, stderr, or the state file.

Env file layout under test (mirrors the script's docstring):
  META_MCP_LONG_TOKEN   the long-lived USER token the bridge reads (canonical)
  META_MCP_TOKEN        the short-lived handoff token a human pastes after re-authorizing
"""
import contextlib
import fcntl
import io
import json
import os
import stat
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import meta_token_maintenance as mtm  # noqa: E402

# Built by concatenation so the repo's secret-pattern scan does not flag a test fixture.
TOKEN_T = "EAA" + "fakeTOKENvalue1234567890"  # the current long-lived token
TOKEN_C = "EAA" + "fakeTOKENvalue0987654321"  # the candidate Meta hands back
TOKEN_X = "EAA" + "fakeTOKENvalue5555555555"  # a token another writer rotates in
TOKEN_H = "EAA" + "fakeTOKENvalue7777777777"  # a short-lived handoff token a human pasted
APP_ID = "123456789012345"
OTHER_APP_ID = "999999999999999"
APP_SECRET = "fakeappsecret00000000000000"
ALL_SECRETS = (TOKEN_T, TOKEN_C, TOKEN_X, TOKEN_H, APP_SECRET)
NOW = 1_757_000_000
DAY = 86400
T_EXP = NOW + 30 * DAY
C_EXP = T_EXP + 30 * DAY
SCOPES = list(mtm.REQUIRED_SCOPES)

ENV_TEXT = (
    "# Hermes env file\n"
    "export OTHER=\"keep me\"\n"
    "META_APP_ID=%s\n"
    "META_APP_SECRET='%s'\n"
    "META_MCP_LONG_TOKEN='%s'  # live token\n"
    "TRAILING=value # note\n"
) % (APP_ID, APP_SECRET, TOKEN_T)

HANDOFF_LINE = "META_MCP_TOKEN='%s'\n" % TOKEN_H

# A human re-authorized and pasted the short-lived token; no long-token line exists yet.
HANDOFF_ONLY_ENV = (
    "META_APP_ID=%s\n"
    "META_APP_SECRET='%s'\n"
    "%s"
) % (APP_ID, APP_SECRET, HANDOFF_LINE)

CONFIG_BRIDGE = (
    "model:\n"
    "  default: x\n"
    "mcp_servers:\n"
    "  meta_ads:\n"
    "    command: python3\n"
    "    # the bridge reads the token itself\n"
    "\n"
    "    args: [\"/srv/hermes-ad-agent/scripts/meta_mcp_bridge.py\", \"--env-file\", \"/data/.env\"]\n"
    "    trust: untrusted\n"
    "    enabled: true\n"
    "  other_server:\n"
    "    url: https://example.invalid/mcp\n"
    "    headers:\n"
    "      X-Key: abc\n"
)

CONFIG_DIRECT = (
    "mcp_servers:\n"
    "  meta_ads:\n"
    "    url: https://mcp.facebook.com/ads\n"
    "    headers:\n"
    "      Authorization: Bearer ${META_MCP_LONG_TOKEN}\n"
)


def token_info(token_type="USER", expires_at=T_EXP, scopes=None, valid=True, app_id=APP_ID):
    return {"type": token_type, "is_valid": valid, "scopes": SCOPES if scopes is None else scopes,
            "expires_at": expires_at, "data_access_expires_at": expires_at + 30 * DAY, "app_id": app_id}


class FakeGraph:
    """graph_get(url, timeout) stand-in. `tokens` maps token -> debug_token data; `exchange` is a
    (status, json) tuple or a callable returning one (callables may have side effects)."""

    def __init__(self, tokens, exchange):
        self.tokens, self.exchange, self.calls = tokens, exchange, []

    def __call__(self, url, timeout):
        parsed = urllib.parse.urlparse(url)
        query = dict(urllib.parse.parse_qsl(parsed.query))
        self.calls.append((parsed.path, query))
        if parsed.path.endswith("/debug_token"):
            info = self.tokens.get(query.get("input_token"))
            if info is None:
                return 200, {"data": {"is_valid": False, "error": {"message": "Invalid OAuth access token.", "code": 190}}}
            return 200, {"data": info}
        if parsed.path.endswith("/oauth/access_token"):
            return self.exchange() if callable(self.exchange) else self.exchange
        return 404, {"error": {"message": "unknown path", "code": 803}}

    def paths(self):
        return [p.rsplit("/", 1)[-1] for p, _ in self.calls]

    def exchanged(self):
        return [q.get("fb_exchange_token") for p, q in self.calls if p.endswith("/oauth/access_token")]


class FakeMcp:
    """mcp_post(url, headers, body, timeout) stand-in. initialize answers JSON with a session id;
    tools/list answers as an SSE stream so both body parsers are exercised.

    fail=True          HTTP 401 with a JSON-RPC error on every call (Meta rejects the token)
    init_status        HTTP status for initialize (plain-text body)
    init_error         JSON-RPC error object returned with HTTP 200 on initialize
    tools_status       HTTP status for tools/list (plain-text body)
    raise_on           method name on which the transport raises OSError
    tools              the tools/list payload (default: two ads_ tools)
    """

    def __init__(self, fail=False, tools=None, init_status=None, init_error=None, tools_status=None, raise_on=None):
        self.fail, self.tools, self.calls = fail, tools, []
        self.init_status, self.init_error, self.tools_status, self.raise_on = init_status, init_error, tools_status, raise_on

    def __call__(self, url, headers, body, timeout):
        msg = json.loads(body.decode("utf-8"))
        method = msg.get("method")
        self.calls.append((method, dict(headers)))
        if self.raise_on == method:
            raise OSError("socket closed while sending " + headers.get("Authorization", ""))
        if self.fail:
            err = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32001, "message": "unauthorized"}}
            return 401, {"content-type": "application/json"}, json.dumps(err)
        if method == "initialize":
            if self.init_status is not None:
                return self.init_status, {"content-type": "text/plain"}, "nope"
            if self.init_error is not None:
                reply = {"jsonrpc": "2.0", "id": 1, "error": self.init_error}
            else:
                reply = {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": mtm.PROTOCOL_VERSION}}
            return 200, {"content-type": "application/json", "mcp-session-id": "sess-1"}, json.dumps(reply)
        if method == "tools/list":
            if self.tools_status is not None:
                return self.tools_status, {"content-type": "text/plain"}, "nope"
            tools = [{"name": "ads_get_ad_accounts"}, {"name": "ads_create_campaign"}] if self.tools is None else self.tools
            payload = json.dumps({"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}})
            return 200, {"content-type": "text/event-stream"}, "event: message\ndata: %s\n\n" % payload
        return 202, {}, ""


class FakeProc:
    def __init__(self, stdout="", stderr=""):
        self.stdout, self.stderr = stdout, stderr


class FakeHermes:
    """hermes_run_fn(cmd) stand-in: records the argv and returns an object with .stdout/.stderr."""

    def __init__(self, stdout="", stderr="", exc=None):
        self.stdout, self.stderr, self.exc, self.calls = stdout, stderr, exc, []

    def __call__(self, cmd):
        self.calls.append(list(cmd))
        if self.exc is not None:
            raise self.exc
        return FakeProc(self.stdout, self.stderr)


HERMES_OK = "Testing MCP server 'meta_ads'...\nConnected. 47 tools available.\n"
HERMES_BAD = "Testing MCP server 'meta_ads'...\nConnection failed: HTTP 401 Unauthorized\n"


def row(key, value):
    """One line of the human report, exactly as print_report pads it."""
    return "%-23s %s" % (key + ":", value)


class MaintenanceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env_file = os.path.join(self.tmp.name, ".env")
        self.state_file = os.path.join(self.tmp.name, "state", "token-maintenance-state.json")
        self.write_env(ENV_TEXT)
        os.chmod(self.env_file, 0o644)
        patcher = mock.patch.dict(os.environ, {"HERMES_HOME": self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in ("META_MCP_ENV_FILE", "META_MCP_DOTENV_PATH", "META_APP_ID", "META_APP_SECRET",
                    "META_MCP_TOKEN", "META_MCP_LONG_TOKEN"):
            os.environ.pop(key, None)
        mtm._SECRETS.clear()

    # -- helpers ------------------------------------------------------------------
    def write_env(self, text):
        with open(self.env_file, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    def read_env(self):
        with open(self.env_file, "r", encoding="utf-8", newline="") as fh:
            return fh.read()

    def env_values(self):
        return mtm.parse_dotenv(self.read_env())

    def assert_no_secrets(self, text):
        for secret in ALL_SECRETS:
            self.assertNotIn(secret, text)

    def run_main(self, graph, mcp=None, extra=(), hermes=None):
        argv = ["--env-file", self.env_file, "--state-file", self.state_file] + list(extra)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mtm.main(argv, graph_get_fn=graph, mcp_post_fn=mcp or FakeMcp(), now=lambda: NOW,
                            hermes_run_fn=hermes)
        text = out.getvalue()
        self.assert_no_secrets(text)
        self.assert_no_secrets(err.getvalue())
        self.assertRegex(text.rstrip().splitlines()[-1], r"^Outcome: [A-Z_]+$")
        return code, text

    def run_json(self, graph, mcp=None, extra=(), hermes=None):
        code, text = self.run_main(graph, mcp, ["--json"] + list(extra), hermes)
        lines = text.strip().splitlines()
        self.assertEqual(len(lines), 2)
        return code, json.loads(lines[0]), text

    def state(self):
        with open(self.state_file, "r", encoding="utf-8") as fh:
            raw = fh.read()
        self.assert_no_secrets(raw)
        return json.loads(raw)

    def renew_graph(self, c_exp=C_EXP, c_scopes=None, c_type="USER", exchange=None, c_app_id=APP_ID):
        tokens = {TOKEN_T: token_info(),
                  TOKEN_C: token_info(token_type=c_type, expires_at=c_exp, scopes=c_scopes, app_id=c_app_id)}
        return FakeGraph(tokens, exchange or (200, {"access_token": TOKEN_C, "token_type": "bearer", "expires_in": 5184000}))

    def handoff_graph(self, current_info=None, handoff_info=None):
        """Handoff scenario: the current token (if any) is described by current_info, the pasted
        short-lived token is valid, and exchanging it yields TOKEN_C with a 60-day expiry."""
        tokens = {TOKEN_H: handoff_info or token_info(expires_at=NOW + 2 * 3600), TOKEN_C: token_info(expires_at=C_EXP)}
        if current_info is not None:
            tokens[TOKEN_T] = current_info
        return FakeGraph(tokens, (200, {"access_token": TOKEN_C, "token_type": "bearer", "expires_in": 5184000}))

    def install_fake_hermes(self):
        """Put an executable `hermes` on PATH (find_hermes checks shutil.which first). Returns its path."""
        bin_dir = os.path.join(self.tmp.name, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        exe = os.path.join(bin_dir, "hermes")
        with open(exe, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        os.chmod(exe, 0o755)
        patcher = mock.patch.dict(os.environ, {"PATH": bin_dir})
        patcher.start()
        self.addCleanup(patcher.stop)
        return exe

    def maintainer(self, extra=(), mcp=None, hermes=None):
        args = mtm.build_arg_parser().parse_args(["--env-file", self.env_file, "--state-file", self.state_file] + list(extra))
        return mtm.Maintainer(args, graph_get_fn=FakeGraph({}, (500, None)), mcp_post_fn=mcp or FakeMcp(),
                              now=lambda: NOW, hermes_run_fn=hermes)

    # -- defaults -----------------------------------------------------------------
    def test_defaults_name_the_long_and_handoff_variables(self):
        self.assertEqual(mtm.DEFAULT_TOKEN_VAR, "META_MCP_LONG_TOKEN")
        self.assertEqual(mtm.DEFAULT_HANDOFF_VAR, "META_MCP_TOKEN")
        args = mtm.build_arg_parser().parse_args([])
        self.assertEqual(args.token_var, "META_MCP_LONG_TOKEN")
        self.assertEqual(args.handoff_var, "META_MCP_TOKEN")
        self.assertEqual(args.hermes_server, "meta_ads")
        self.assertFalse(args.hermes_test)
        self.assertIsNone(args.config_file)
        self.assertEqual(args.min_days, 21)
        self.assertEqual(mtm.build_arg_parser().parse_args(["--handoff-var", ""]).handoff_var, "")

    def test_legacy_layout_with_custom_token_var_and_no_handoff(self):
        self.write_env("META_APP_ID=%s\nMETA_APP_SECRET=%s\nMETA_MCP_TOKEN='%s'\n" % (APP_ID, APP_SECRET, TOKEN_T))
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(), ["--token-var", "META_MCP_TOKEN", "--handoff-var", ""])
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertFalse(data["via_handoff"])
        self.assertEqual(self.env_values()["META_MCP_TOKEN"], TOKEN_C)
        self.assertNotIn("META_MCP_LONG_TOKEN", self.read_env())

    # -- dotenv handling ----------------------------------------------------------
    def test_rewrite_preserves_every_other_byte(self):
        text = "export A=\"old\"\r\nA=old # c\n# A=commented\nAB=old\nA = 'old' # q\nB=x\nA=old"
        new, hits = mtm.rewrite_token_lines(text, "A", "new")
        self.assertEqual(hits, 4)
        self.assertEqual(new, "export A=\"new\"\r\nA=new # c\n# A=commented\nAB=old\nA = 'new' # q\nB=x\nA=new")
        self.assertEqual(mtm.parse_dotenv(new)["A"], "new")
        parsed = mtm.parse_dotenv("K='v' # note\nJ=\"q\"\nL=w # z\nexport M=m\n# comment\nbare\n")
        self.assertEqual(parsed, {"K": "v", "J": "q", "L": "w", "M": "m"})

    def test_rewrite_to_empty_keeps_quotes_and_clears_the_value(self):
        new, hits = mtm.rewrite_token_lines("K='old'  # c\nJ=\"old\"\nL=old\nM=''\n", "K", "")
        self.assertEqual((new, hits), ("K=''  # c\nJ=\"old\"\nL=old\nM=''\n", 1))
        new, _ = mtm.rewrite_token_lines(new, "L", "")
        self.assertEqual(mtm.parse_dotenv(new), {"K": "", "J": "old", "L": "", "M": ""})
        new, hits = mtm.rewrite_token_lines(new, "M", "v")
        self.assertIn("M='v'\n", new)
        self.assertEqual(hits, 1)

    def test_renewed_writes_atomically_and_preserves_file(self):
        mcp = FakeMcp()
        graph = self.renew_graph()
        code, out = self.run_main(graph, mcp)
        self.assertEqual(code, 0)
        self.assertIn("Outcome: RENEWED", out)
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_C))
        self.assertIn("META_MCP_LONG_TOKEN='%s'  # live token\n" % TOKEN_C, self.read_env())
        self.assertEqual(stat.S_IMODE(os.stat(self.env_file).st_mode), 0o600)
        self.assertEqual(sorted(os.listdir(self.tmp.name)), [".env", "state"])  # no temp files left behind
        # the smoke test used the candidate, carried the session id, and asked for tools
        self.assertEqual([m for m, _ in mcp.calls], ["initialize", "notifications/initialized", "tools/list"])
        self.assertEqual(mcp.calls[-1][1]["Authorization"], "Bearer " + TOKEN_C)
        self.assertEqual(mcp.calls[-1][1]["Mcp-Session-Id"], "sess-1")
        self.assertEqual(mcp.calls[0][1]["Accept"], "application/json, text/event-stream")
        # both inspections used the app token, never the user token, as access_token
        debug_calls = [q for p, q in graph.calls if p.endswith("/debug_token")]
        self.assertEqual({q["access_token"] for q in debug_calls}, {APP_ID + "|" + APP_SECRET})
        self.assertEqual(graph.exchanged(), [TOKEN_T])
        self.assertIn("live gateway uses the new token on its next call", out)
        self.assertIn(row("status", "SUCCESS"), out)
        st = self.state()
        self.assertEqual(st["schema_version"], 1)
        self.assertEqual(st["last_outcome"], "RENEWED")
        self.assertEqual(st["status_compat"], "SUCCESS")
        self.assertEqual(st["bridge_config_valid"], "unknown")
        self.assertEqual(st["consecutive_non_advancing_runs"], 0)
        self.assertEqual(st["last_advancing_expiry_at"], mtm.iso(NOW))
        self.assertEqual(st["expires_at"], mtm.iso(C_EXP))
        self.assertEqual(st["days_remaining"], 60.0)

    # -- classification -----------------------------------------------------------
    def test_replaced_same_expiry_is_not_written_by_default(self):
        mcp = FakeMcp()
        code, out = self.run_main(self.renew_graph(c_exp=T_EXP), mcp)
        self.assertEqual(code, 1)
        self.assertIn("Outcome: REPLACED_SAME_EXPIRY", out)
        self.assertIn(row("status", "NO_CHANGE"), out)  # headline: nothing was written
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(mcp.calls, [])
        st = self.state()
        self.assertEqual(st["consecutive_non_advancing_runs"], 1)
        self.assertEqual(st["status_compat"], "NO_CHANGE")

    def test_one_day_advance_is_still_same_expiry(self):
        code, out = self.run_main(self.renew_graph(c_exp=T_EXP + DAY))
        self.assertEqual(code, 1)
        self.assertIn("Outcome: REPLACED_SAME_EXPIRY", out)
        self.assertEqual(self.read_env(), ENV_TEXT)

    def test_replaced_same_expiry_written_with_flag(self):
        code, data, out = self.run_json(self.renew_graph(c_exp=T_EXP + 3600), FakeMcp(), ["--replace-same-expiry"])
        self.assertEqual(code, 0)
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_C))
        self.assertEqual(data["outcome"], "REPLACED_SAME_EXPIRY")
        self.assertEqual(data["status_compat"], "SUCCESS")
        self.assertTrue(data["written"])
        self.assertTrue(data["candidate_differed"])
        self.assertFalse(data["expiry_advanced"])
        self.assertIn("(same expiry, forced)", data["message"])
        st = self.state()
        self.assertEqual(st["consecutive_non_advancing_runs"], 1)
        self.assertEqual(st["status_compat"], "SUCCESS")

    def test_shorter_expiry_candidate_is_retained_even_when_forced(self):
        mcp = FakeMcp()
        code, data, out = self.run_json(self.renew_graph(c_exp=T_EXP - 2 * DAY), mcp, ["--replace-same-expiry"])
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "NO_CHANGE")
        self.assertEqual(data["status_compat"], "NO_CHANGE")
        self.assertIn("would expire earlier", data["message"])
        self.assertIn("retained", data["message"])
        self.assertFalse(data["written"])
        self.assertTrue(data["candidate_differed"])
        self.assertEqual(data["candidate_expires_at"], mtm.iso(T_EXP - 2 * DAY))
        self.assertEqual(data["expires_at"], mtm.iso(T_EXP))  # the report still describes the retained token
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(mcp.calls, [])
        self.assertEqual(self.state()["consecutive_non_advancing_runs"], 1)

    def test_exactly_one_day_earlier_is_same_expiry_not_retained(self):
        code, out = self.run_main(self.renew_graph(c_exp=T_EXP - DAY))
        self.assertEqual(code, 1)
        self.assertIn("Outcome: REPLACED_SAME_EXPIRY", out)
        self.assertEqual(self.read_env(), ENV_TEXT)

    def test_no_change_when_meta_returns_same_token(self):
        graph = FakeGraph({TOKEN_T: token_info()}, (200, {"access_token": TOKEN_T, "expires_in": 100}))
        mcp = FakeMcp()
        code, data, out = self.run_json(graph, mcp)
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "NO_CHANGE")
        self.assertFalse(data["candidate_differed"])
        self.assertEqual(data["required_action"], "none")
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(stat.S_IMODE(os.stat(self.env_file).st_mode), 0o644)  # untouched
        self.assertEqual(mcp.calls, [])

    def test_no_change_under_min_days_exits_1(self):
        graph = FakeGraph({TOKEN_T: token_info(expires_at=NOW + 5 * DAY)}, (200, {"access_token": TOKEN_T}))
        code, data, out = self.run_json(graph)
        self.assertEqual(code, 1)
        self.assertEqual(data["outcome"], "NO_CHANGE")
        self.assertIn("plan a manual re-auth", data["next_steps"])
        self.assertEqual(data["required_action"],
                         "re-authorize before %s (fewer than 21 days remain)" % mtm.iso(NOW + 5 * DAY))
        code, out = self.run_main(graph, extra=["--min-days", "3"])
        self.assertEqual(code, 0)

    def test_exchange_skipped_without_app_credentials(self):
        self.write_env("META_MCP_LONG_TOKEN=%s\n" % TOKEN_T)
        graph = FakeGraph({TOKEN_T: token_info()}, (500, None))
        code, out = self.run_main(graph)
        self.assertEqual(code, 0)
        self.assertIn("Outcome: NO_CHANGE", out)
        self.assertIn("exchange skipped: META_APP_ID/META_APP_SECRET not set", out)
        self.assertEqual([p for p, _ in graph.calls], ["/v25.0/debug_token"])
        self.assertEqual(graph.calls[0][1]["access_token"], TOKEN_T)  # fallback: token inspects itself

    def test_reauth_required_on_oauth_error_190(self):
        oauth = {"message": "Error validating access token: Session has expired", "type": "OAuthException", "code": 190}
        code, data, out = self.run_json(self.renew_graph(exchange=(400, {"error": oauth})))
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "REAUTH_REQUIRED")
        self.assertEqual(data["status_compat"], "REAUTH_REQUIRED")
        self.assertEqual(data["required_action"], data["next_steps"])
        self.assertIn("store it as META_MCP_TOKEN in %s" % self.env_file, data["required_action"])
        self.assertIn("writes META_MCP_LONG_TOKEN", data["required_action"])
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(self.state()["last_outcome"], "REAUTH_REQUIRED")

    def test_reauth_required_when_token_missing(self):
        self.write_env("OTHER=1\n")
        code, out = self.run_main(FakeGraph({}, (500, None)))
        self.assertEqual(code, 2)
        self.assertIn("Outcome: REAUTH_REQUIRED", out)
        self.assertIn("no token in env file (META_MCP_LONG_TOKEN in", out)

    def test_reauth_required_when_current_token_invalid_or_expired(self):
        code, out = self.run_main(FakeGraph({}, (500, None)))  # debug_token: is_valid false
        self.assertEqual(code, 2)
        self.assertIn("Outcome: REAUTH_REQUIRED", out)
        self.assertIn("current token is not valid", out)
        code, out = self.run_main(FakeGraph({TOKEN_T: token_info(expires_at=NOW - 10)}, (500, None)))
        self.assertEqual(code, 2)
        self.assertIn("Outcome: REAUTH_REQUIRED", out)
        self.assertIn("current token expired at", out)

    def test_failed_when_candidate_misses_scope(self):
        graph = self.renew_graph(c_scopes=[s for s in SCOPES if s != "instagram_basic"])
        code, out = self.run_main(graph)
        self.assertEqual(code, 2)
        self.assertIn("Outcome: FAILED", out)
        self.assertIn("missing scopes: instagram_basic", out)
        self.assertEqual(self.read_env(), ENV_TEXT)

    def test_failed_when_candidate_is_not_a_user_token(self):
        code, out = self.run_main(self.renew_graph(c_type="SYSTEM_USER"))
        self.assertEqual(code, 2)
        self.assertIn("Outcome: FAILED", out)
        self.assertIn("candidate is a SYSTEM_USER token", out)
        self.assertEqual(self.read_env(), ENV_TEXT)

    def test_failed_when_candidate_belongs_to_another_app(self):
        mcp = FakeMcp()
        code, data, out = self.run_json(self.renew_graph(c_app_id=OTHER_APP_ID), mcp)
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "FAILED")
        self.assertIn("candidate belongs to a different Meta app than META_APP_ID", data["message"])
        self.assertEqual(data["required_action"], data["message"])
        self.assertFalse(data["written"])
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(mcp.calls, [])

    def test_app_check_needs_both_sides(self):
        # debug_token without an app_id cannot contradict META_APP_ID; the candidate is accepted
        code, out = self.run_main(self.renew_graph(c_app_id=""))
        self.assertEqual(code, 0)
        self.assertIn("Outcome: RENEWED", out)
        self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)

    def test_non_oauth_exchange_error_is_failed_and_redacted(self):
        leaky = {"message": "bad request for %s with %s" % (TOKEN_T, APP_SECRET), "code": 100}
        code, out = self.run_main(self.renew_graph(exchange=(400, {"error": leaky})))
        self.assertEqual(code, 2)
        self.assertIn("Outcome: FAILED", out)
        self.assertIn("[redacted]", out)

    def test_graph_transport_error_is_failed(self):
        def boom(url, timeout):
            raise OSError("connection refused while sending " + TOKEN_T)
        code, out = self.run_main(boom)
        self.assertEqual(code, 2)
        self.assertIn("Outcome: FAILED", out)
        self.assertIn("graph request failed: OSError", out)

    # -- handoff path -------------------------------------------------------------
    def test_handoff_creates_long_token_line_and_clears_handoff(self):
        self.write_env(HANDOFF_ONLY_ENV)
        graph, mcp = self.handoff_graph(), FakeMcp()
        code, data, out = self.run_json(graph, mcp)
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertEqual(data["status_compat"], "SUCCESS")
        self.assertTrue(data["via_handoff"])
        self.assertTrue(data["written"])
        self.assertTrue(data["expiry_advanced"])
        self.assertTrue(data["candidate_differed"])
        self.assertIn("(from the handoff token)", data["message"])
        self.assertIn("exchanging the handoff token from META_MCP_TOKEN", " ".join(data["notes"]))
        self.assertIn("cleared the handoff line META_MCP_TOKEN", " ".join(data["notes"]))
        # the long-token line was appended with single quotes; the handoff line was emptied in place
        expected = HANDOFF_ONLY_ENV.replace(HANDOFF_LINE, "META_MCP_TOKEN=''\n") + "META_MCP_LONG_TOKEN='%s'\n" % TOKEN_C
        self.assertEqual(self.read_env(), expected)
        self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)
        self.assertEqual(self.env_values()["META_MCP_TOKEN"], "")
        self.assertEqual(stat.S_IMODE(os.stat(self.env_file).st_mode), 0o600)
        # the handoff token was inspected, then exchanged, then the candidate was inspected
        self.assertEqual(graph.paths(), ["debug_token", "access_token", "debug_token"])
        self.assertEqual(graph.calls[0][1]["input_token"], TOKEN_H)
        self.assertEqual(graph.exchanged(), [TOKEN_H])
        self.assertEqual(graph.calls[2][1]["input_token"], TOKEN_C)
        self.assertEqual([m for m, _ in mcp.calls], ["initialize", "notifications/initialized", "tools/list"])
        self.assertEqual(mcp.calls[-1][1]["Authorization"], "Bearer " + TOKEN_C)
        self.assertEqual(data["expires_at"], mtm.iso(C_EXP))
        self.assertEqual(data["token_type"], "USER")
        st = self.state()
        self.assertEqual(st["last_outcome"], "RENEWED")
        self.assertEqual(st["status_compat"], "SUCCESS")

    def test_handoff_append_adds_newline_and_clears_unquoted_line(self):
        self.write_env("META_APP_ID=%s\nMETA_APP_SECRET=%s\nMETA_MCP_TOKEN=%s" % (APP_ID, APP_SECRET, TOKEN_H))
        code, out = self.run_main(self.handoff_graph())
        self.assertEqual(code, 0)
        self.assertIn("Outcome: RENEWED", out)
        self.assertEqual(self.read_env(), "META_APP_ID=%s\nMETA_APP_SECRET=%s\nMETA_MCP_TOKEN=\nMETA_MCP_LONG_TOKEN='%s'\n"
                         % (APP_ID, APP_SECRET, TOKEN_C))

    def test_handoff_fills_an_existing_empty_long_token_line(self):
        self.write_env(ENV_TEXT.replace(TOKEN_T, "") + "META_MCP_TOKEN=\"%s\"\n" % TOKEN_H)
        code, data, out = self.run_json(self.handoff_graph())
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertTrue(data["via_handoff"])
        # rewritten in place (comment kept), not appended; double quotes on the handoff line survive
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_C) + "META_MCP_TOKEN=\"\"\n")

    def test_handoff_used_when_current_token_is_invalid(self):
        self.write_env(ENV_TEXT + HANDOFF_LINE)
        graph = self.handoff_graph(current_info=None)  # TOKEN_T unknown to debug_token: invalid
        code, data, out = self.run_json(graph)
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertTrue(data["via_handoff"])
        self.assertIn("current token unusable (current token is not valid", " ".join(data["notes"]))
        self.assertEqual(graph.paths(), ["debug_token", "debug_token", "access_token", "debug_token"])
        self.assertEqual([q["input_token"] for p, q in graph.calls if p.endswith("/debug_token")], [TOKEN_T, TOKEN_H, TOKEN_C])
        self.assertEqual(graph.exchanged(), [TOKEN_H])
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_C) + "META_MCP_TOKEN=''\n")

    def test_handoff_used_when_current_token_is_expired(self):
        self.write_env(ENV_TEXT + HANDOFF_LINE)
        graph = self.handoff_graph(current_info=token_info(expires_at=NOW - 10))
        code, data, out = self.run_json(graph)
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertTrue(data["via_handoff"])
        self.assertIn("current token expired at", " ".join(data["notes"]))
        self.assertEqual(graph.exchanged(), [TOKEN_H])
        self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)
        self.assertEqual(self.env_values()["META_MCP_TOKEN"], "")

    def test_unusable_handoff_is_noted_and_current_token_is_used(self):
        # the handoff line holds a token debug_token does not know: note it, carry on with the current token
        self.write_env(ENV_TEXT + HANDOFF_LINE)
        graph = self.renew_graph()
        code, data, out = self.run_json(graph)
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertFalse(data["via_handoff"])
        self.assertEqual(graph.exchanged(), [TOKEN_T])
        self.assertTrue(any("unusable" in n for n in data["notes"]))
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_C) + HANDOFF_LINE)  # handoff line untouched

    def test_valid_handoff_is_preferred_even_when_current_token_is_valid(self):
        # a human deliberately placed a fresh token: exchange that one, write the long line, clear the handoff
        self.write_env(ENV_TEXT + HANDOFF_LINE)
        graph = self.handoff_graph(current_info=token_info())
        code, data, out = self.run_json(graph)
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertTrue(data["via_handoff"])
        self.assertEqual(graph.exchanged(), [TOKEN_H])
        self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)
        self.assertEqual(self.env_values()["META_MCP_TOKEN"], "")

    def test_bad_handoff_token_is_reauth_required(self):
        self.write_env(HANDOFF_ONLY_ENV)
        graph = FakeGraph({}, (200, {"access_token": TOKEN_C}))
        code, data, out = self.run_json(graph)
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "REAUTH_REQUIRED")
        self.assertIn("handoff token is not valid", data["message"])
        self.assertEqual(graph.paths(), ["debug_token"])
        self.assertEqual(self.read_env(), HANDOFF_ONLY_ENV)
        # an expired handoff token is the same story
        graph = FakeGraph({TOKEN_H: token_info(expires_at=NOW - 1)}, (200, {"access_token": TOKEN_C}))
        code, out = self.run_main(graph)
        self.assertEqual(code, 2)
        self.assertIn("Outcome: REAUTH_REQUIRED", out)
        self.assertIn("handoff token expired at", out)
        self.assertEqual(self.read_env(), HANDOFF_ONLY_ENV)

    def test_handoff_without_app_credentials_is_reauth_required(self):
        self.write_env(HANDOFF_LINE)
        graph = self.handoff_graph()
        code, data, out = self.run_json(graph)
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "REAUTH_REQUIRED")
        self.assertIn("META_APP_ID/META_APP_SECRET are not set, so it cannot be exchanged", data["message"])
        self.assertEqual(graph.calls, [])
        self.assertEqual(self.read_env(), HANDOFF_LINE)
        # same when the current token is invalid and only the handoff is left
        self.write_env("META_MCP_LONG_TOKEN='%s'\n%s" % (TOKEN_T, HANDOFF_LINE))
        graph = self.handoff_graph()
        code, out = self.run_main(graph)
        self.assertEqual(code, 2)
        self.assertIn("Outcome: REAUTH_REQUIRED", out)
        self.assertIn("cannot be exchanged", out)
        self.assertEqual(graph.paths(), ["debug_token"])

    def test_handoff_disabled_with_empty_var(self):
        self.write_env(HANDOFF_ONLY_ENV)
        graph = self.handoff_graph()
        code, out = self.run_main(graph, extra=["--handoff-var", ""])
        self.assertEqual(code, 2)
        self.assertIn("Outcome: REAUTH_REQUIRED", out)
        self.assertIn("no token in env file", out)
        self.assertEqual(graph.calls, [])
        self.assertEqual(self.read_env(), HANDOFF_ONLY_ENV)

    def test_custom_handoff_var(self):
        self.write_env(HANDOFF_ONLY_ENV.replace("META_MCP_TOKEN=", "PASTE_HERE="))
        code, data, out = self.run_json(self.handoff_graph(), extra=["--handoff-var", "PASTE_HERE"])
        self.assertEqual(code, 0)
        self.assertTrue(data["via_handoff"])
        self.assertEqual(self.env_values()["PASTE_HERE"], "")
        self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)
        self.assertIn("cleared the handoff line PASTE_HERE", " ".join(data["notes"]))

    def test_handoff_candidate_rejected_by_meta_rolls_back_and_keeps_the_paste(self):
        self.write_env(HANDOFF_ONLY_ENV)
        code, data, out = self.run_json(self.handoff_graph(), FakeMcp(fail=True))
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "FAILED")
        self.assertTrue(data["rolled_back"])
        self.assertFalse(data["written"])
        self.assertIn("rolled back to the previous token", data["message"])
        # the created line is emptied, the human's handoff token is still there for the next attempt
        self.assertEqual(self.read_env(), HANDOFF_ONLY_ENV + "META_MCP_LONG_TOKEN=''\n")

    def test_handoff_kept_when_post_write_check_is_not_an_auth_failure(self):
        self.write_env(HANDOFF_ONLY_ENV)
        code, data, out = self.run_json(self.handoff_graph(), FakeMcp(raise_on="tools/list"))
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "FAILED")
        self.assertTrue(data["written"])
        self.assertTrue(data["candidate_kept"])
        self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)
        self.assertEqual(self.env_values()["META_MCP_TOKEN"], TOKEN_H)  # not cleared: the run did not finish

    def test_handoff_clear_failure_is_a_note_not_a_failure(self):
        self.write_env("META_APP_ID=%s\nMETA_APP_SECRET=%s\n%s%s" % (APP_ID, APP_SECRET, HANDOFF_LINE, HANDOFF_LINE))
        code, data, out = self.run_json(self.handoff_graph())
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertIn("could not clear META_MCP_TOKEN: META_MCP_TOKEN appears 2 times", " ".join(data["notes"]))
        self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)
        self.assertEqual(self.read_env().count(HANDOFF_LINE), 2)

    # -- write safety -------------------------------------------------------------
    def test_dry_run_writes_nothing(self):
        mcp = FakeMcp()
        hermes = FakeHermes(HERMES_OK)
        code, data, out = self.run_json(self.renew_graph(), mcp, ["--dry-run", "--hermes-test"], hermes)
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertEqual(data["status_compat"], "SUCCESS")
        self.assertTrue(data["would_write"])
        self.assertFalse(data["written"])
        self.assertTrue(data["dry_run"])
        self.assertEqual(data["hermes_test"], "not run")
        self.assertEqual(data["smoke_test"], "not run")
        self.assertIn("dry run: a live run would write the candidate", data["message"])
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(stat.S_IMODE(os.stat(self.env_file).st_mode), 0o644)
        self.assertEqual(os.listdir(self.tmp.name), [".env"])  # no state dir, no lock, no temp file
        self.assertEqual(mcp.calls, [])
        self.assertEqual(hermes.calls, [])

    def test_dry_run_handoff_writes_nothing(self):
        self.write_env(HANDOFF_ONLY_ENV)
        code, data, out = self.run_json(self.handoff_graph(), extra=["--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertTrue(data["via_handoff"])
        self.assertTrue(data["would_write"])
        self.assertFalse(data["written"])
        self.assertEqual(self.read_env(), HANDOFF_ONLY_ENV)
        self.assertEqual(os.listdir(self.tmp.name), [".env"])

    def test_cas_mismatch_aborts_without_writing(self):
        def exchange():
            self.write_env(ENV_TEXT.replace(TOKEN_T, TOKEN_X))  # another writer rotates the token mid-run
            return 200, {"access_token": TOKEN_C, "expires_in": 5184000}
        tokens = {TOKEN_T: token_info(), TOKEN_C: token_info(expires_at=C_EXP)}
        code, out = self.run_main(FakeGraph(tokens, exchange))
        self.assertEqual(code, 2)
        self.assertIn("Outcome: FAILED", out)
        self.assertIn("META_MCP_LONG_TOKEN changed underneath, not writing", out)
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_X))

    def test_duplicate_token_lines_fail_closed(self):
        self.write_env(ENV_TEXT + "META_MCP_LONG_TOKEN='%s'\n" % TOKEN_T)
        mcp = FakeMcp()
        code, data, out = self.run_json(self.renew_graph(), mcp)
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "FAILED")
        self.assertIn("META_MCP_LONG_TOKEN appears 2 times in %s; keep exactly one line" % self.env_file, data["message"])
        self.assertFalse(data["written"])
        self.assertEqual(self.read_env(), ENV_TEXT + "META_MCP_LONG_TOKEN='%s'\n" % TOKEN_T)
        self.assertEqual(mcp.calls, [])

    def test_write_value_missing_key_fails_unless_allow_create(self):
        m = self.maintainer()
        with self.assertRaises(mtm.Stop) as ctx:
            m.write_value(self.env_file, "NEW_KEY", "", "v1")
        self.assertEqual(ctx.exception.outcome, "FAILED")
        self.assertEqual(ctx.exception.message, "no NEW_KEY line found to rewrite")
        self.assertEqual(self.read_env(), ENV_TEXT)
        m.write_value(self.env_file, "NEW_KEY", "", "v1", allow_create=True)
        self.assertEqual(self.read_env(), ENV_TEXT + "NEW_KEY='v1'\n")
        # allow_create rewrites an existing line in place instead of appending a second one
        m.write_value(self.env_file, "NEW_KEY", "v1", "v2", allow_create=True)
        self.assertEqual(self.read_env(), ENV_TEXT + "NEW_KEY='v2'\n")
        # compare-and-swap still applies
        with self.assertRaises(mtm.Stop) as ctx:
            m.write_value(self.env_file, "NEW_KEY", "stale", "v3", allow_create=True)
        self.assertEqual(ctx.exception.message, "NEW_KEY changed underneath, not writing")
        # a duplicated key fails closed even with allow_create
        self.write_env(ENV_TEXT + "NEW_KEY='v2'\nNEW_KEY='v2'\n")
        with self.assertRaises(mtm.Stop) as ctx:
            m.write_value(self.env_file, "NEW_KEY", "v2", "v3", allow_create=True)
        self.assertIn("NEW_KEY appears 2 times", ctx.exception.message)
        self.assertEqual(self.read_env(), ENV_TEXT + "NEW_KEY='v2'\nNEW_KEY='v2'\n")

    def test_write_value_os_error_is_failed(self):
        m = self.maintainer()
        with self.assertRaises(mtm.Stop) as ctx:
            m.write_value(os.path.join(self.tmp.name, "missing", ".env"), "K", "", "v", allow_create=True)
        self.assertEqual(ctx.exception.outcome, "FAILED")
        self.assertEqual(ctx.exception.message, "env file read/write failed: FileNotFoundError")

    # -- post-write checks --------------------------------------------------------
    def test_smoke_test_auth_rejection_rolls_back(self):
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(fail=True))
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "FAILED")
        self.assertEqual(data["status_compat"], "FAILED")
        self.assertTrue(data["rolled_back"])
        self.assertFalse(data["written"])
        self.assertFalse(data["candidate_kept"])
        self.assertEqual(data["smoke_test"], "initialize rejected: HTTP 401")
        self.assertIn("Meta rejected the new token", data["message"])
        self.assertIn("rolled back to the previous token", data["message"])
        self.assertIn("(the previous token was restored)", data["next_steps"])
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(data["expires_at"], mtm.iso(T_EXP))  # the report describes the restored token
        st = self.state()
        self.assertEqual(st["last_outcome"], "FAILED")
        self.assertEqual(st["status_compat"], "FAILED")
        self.assertEqual(st["expires_at"], mtm.iso(T_EXP))
        self.assertIn("rolled back", " ".join(st["notes"]))

    def test_smoke_test_auth_rejection_on_tools_list_or_403_rolls_back(self):
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(tools_status=401))
        self.assertEqual(code, 2)
        self.assertTrue(data["rolled_back"])
        self.assertEqual(data["smoke_test"], "tools/list rejected: HTTP 401")
        self.assertEqual(self.read_env(), ENV_TEXT)
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(init_status=403))
        self.assertEqual(code, 2)
        self.assertTrue(data["rolled_back"])
        self.assertEqual(data["smoke_test"], "initialize rejected: HTTP 403")
        self.assertEqual(self.read_env(), ENV_TEXT)

    def test_smoke_test_transport_error_keeps_candidate(self):
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(raise_on="initialize"))
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "FAILED")
        self.assertTrue(data["written"])
        self.assertTrue(data["candidate_kept"])
        self.assertFalse(data["rolled_back"])
        self.assertTrue(data["expiry_advanced"])
        # the candidate is a known secret by then, so it is replaced as a value, not just by pattern
        self.assertEqual(data["smoke_test"], "transport error: OSError: socket closed while sending Bearer [redacted]")
        self.assertIn("the new token was kept because debug_token validated it", data["message"])
        self.assertIn("(the validated new token is in place)", data["next_steps"])
        self.assertEqual(data["required_action"], data["message"])
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_C))
        self.assertEqual(data["expires_at"], mtm.iso(C_EXP))
        st = self.state()
        self.assertEqual(st["last_outcome"], "FAILED")
        self.assertEqual(st["expires_at"], mtm.iso(C_EXP))

    def test_smoke_test_requires_an_ads_tool_but_keeps_candidate(self):
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(tools=[{"name": "other_tool"}]))
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "FAILED")
        self.assertEqual(data["smoke_test"], "tools/list returned 1 tools, none with ads_ in the name")
        self.assertTrue(data["written"])
        self.assertTrue(data["candidate_kept"])
        self.assertFalse(data["rolled_back"])
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_C))
        self.write_env(ENV_TEXT)
        code, out = self.run_main(self.renew_graph(), FakeMcp(tools=[]))  # the human report also says written
        self.assertEqual(code, 2)
        self.assertIn("Outcome: FAILED", out)
        self.assertIn(row("written", "yes"), out)
        self.assertIn(row("smoke test", "tools/list returned 0 tools, none with ads_ in the name"), out)

    def test_smoke_test_other_http_failures_keep_candidate(self):
        for mcp, detail in ((FakeMcp(init_status=500), "initialize failed: HTTP 500"),
                            (FakeMcp(tools_status=500), "tools/list failed: HTTP 500"),
                            (FakeMcp(init_error={"code": -32600, "message": "bad init " + TOKEN_C}),
                             "initialize failed: HTTP 200, bad init [redacted]")):
            with self.subTest(detail=detail):
                self.write_env(ENV_TEXT)
                code, data, out = self.run_json(self.renew_graph(), mcp)
                self.assertEqual(code, 2)
                self.assertEqual(data["outcome"], "FAILED")
                self.assertEqual(data["smoke_test"], detail)
                self.assertTrue(data["written"])
                self.assertTrue(data["candidate_kept"])
                self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)

    def test_smoke_test_returns_ok_detail_and_kind(self):
        self.assertEqual(self.maintainer(mcp=FakeMcp()).smoke_test(TOKEN_C),
                         (True, "passed: 2 tools listed, 2 with ads_ in the name", "ok"))
        self.assertEqual(self.maintainer(mcp=FakeMcp(fail=True)).smoke_test(TOKEN_C),
                         (False, "initialize rejected: HTTP 401", "auth"))
        self.assertEqual(self.maintainer(mcp=FakeMcp(tools_status=403)).smoke_test(TOKEN_C),
                         (False, "tools/list rejected: HTTP 403", "auth"))
        self.assertEqual(self.maintainer(mcp=FakeMcp(raise_on="tools/list")).smoke_test(TOKEN_C)[::2], (False, "transport"))
        self.assertEqual(self.maintainer(mcp=FakeMcp(tools=[{"name": "x"}, {"name": "ads_y"}])).smoke_test(TOKEN_C),
                         (True, "passed: 2 tools listed, 1 with ads_ in the name", "ok"))
        self.assertEqual(self.maintainer(mcp=FakeMcp(tools=[])).smoke_test(TOKEN_C)[::2], (False, "other"))

    def test_no_smoke_test_flag_skips_mcp(self):
        mcp = FakeMcp(fail=True)
        code, out = self.run_main(self.renew_graph(), mcp, ["--no-smoke-test"])
        self.assertEqual(code, 0)
        self.assertEqual(mcp.calls, [])
        self.assertIn(TOKEN_C, self.read_env())
        self.assertIn("skipped (--no-smoke-test)", out)

    def test_lock_held_fails_before_touching_anything(self):
        os.makedirs(os.path.dirname(self.state_file))
        fd = os.open(self.state_file + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        graph = self.renew_graph()
        code, out = self.run_main(graph)
        self.assertEqual(code, 2)
        self.assertIn("Outcome: FAILED", out)
        self.assertIn("another maintenance run holds the lock", out)
        self.assertEqual(graph.calls, [])
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertFalse(os.path.exists(self.state_file))

    def test_non_https_upstream_is_refused(self):
        graph = self.renew_graph()
        code, out = self.run_main(graph, extra=["--upstream", "http://127.0.0.1:8000/mcp"])
        self.assertEqual(code, 2)
        self.assertIn("--upstream must be an https URL", out)
        self.assertEqual(graph.calls, [])
        self.assertEqual(self.read_env(), ENV_TEXT)

    # -- hermes mcp test ----------------------------------------------------------
    def test_hermes_test_runs_after_smoke_test_and_passes(self):
        exe = self.install_fake_hermes()
        hermes = FakeHermes(HERMES_OK)
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(), ["--hermes-test"], hermes)
        self.assertEqual(code, 0)
        self.assertEqual(data["outcome"], "RENEWED")
        self.assertEqual(hermes.calls, [[exe, "mcp", "test", "meta_ads"]])
        self.assertTrue(data["hermes_test"].startswith("passed: "))
        self.assertIn("47 tools available", data["hermes_test"])
        self.assertFalse(data["candidate_kept"])
        self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)
        self.write_env(ENV_TEXT)
        code, out = self.run_main(self.renew_graph(), FakeMcp(), ["--hermes-test"], hermes)
        self.assertEqual(code, 0)
        self.assertIn(row("hermes mcp test", "passed:"), out)

    def test_hermes_test_server_name_flag(self):
        exe = self.install_fake_hermes()
        hermes = FakeHermes(HERMES_OK)
        code, out = self.run_main(self.renew_graph(), FakeMcp(), ["--hermes-test", "--hermes-server", "meta_ads_staging"], hermes)
        self.assertEqual(code, 0)
        self.assertEqual(hermes.calls, [[exe, "mcp", "test", "meta_ads_staging"]])

    def test_hermes_test_failure_keeps_token_and_fails(self):
        self.install_fake_hermes()
        for text in (HERMES_BAD + TOKEN_C + "\n", "✗ meta_ads: unreachable (tools: 0)\n"):
            with self.subTest(text=text[:12]):
                self.write_env(ENV_TEXT)
                hermes = FakeHermes(stdout="", stderr=text)
                code, data, out = self.run_json(self.renew_graph(), FakeMcp(), ["--hermes-test"], hermes)
                self.assertEqual(code, 2)
                self.assertEqual(data["outcome"], "FAILED")
                self.assertTrue(data["written"])
                self.assertTrue(data["candidate_kept"])
                self.assertFalse(data["rolled_back"])
                self.assertTrue(data["hermes_test"].startswith("failed: "))
                self.assertTrue(data["smoke_test"].startswith("passed: "))
                self.assertIn("hermes mcp test failed", data["message"])
                self.assertIn("hermes config check", data["message"])
                self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)
                self.assertEqual(data["required_action"], data["message"])
                if TOKEN_C in text:
                    self.assertIn("[redacted]", data["hermes_test"])

    def test_hermes_test_not_run_without_flag_and_skipped_on_failed_smoke_test(self):
        self.install_fake_hermes()
        hermes = FakeHermes(HERMES_OK)
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(), [], hermes)
        self.assertEqual(data["hermes_test"], "not run")
        self.assertEqual(hermes.calls, [])
        self.write_env(ENV_TEXT)
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(fail=True), ["--hermes-test"], hermes)
        self.assertEqual(data["outcome"], "FAILED")
        self.assertEqual(data["hermes_test"], "not run")
        self.assertEqual(hermes.calls, [])
        self.write_env(ENV_TEXT)
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(tools=[]), ["--hermes-test"], hermes)
        self.assertEqual(data["hermes_test"], "not run")
        self.assertEqual(hermes.calls, [])

    def test_hermes_test_runs_when_smoke_test_is_skipped(self):
        exe = self.install_fake_hermes()
        hermes = FakeHermes(HERMES_OK)
        code, data, out = self.run_json(self.renew_graph(), FakeMcp(fail=True), ["--no-smoke-test", "--hermes-test"], hermes)
        self.assertEqual(code, 0)
        self.assertEqual(data["smoke_test"], "skipped (--no-smoke-test)")
        self.assertEqual(hermes.calls, [[exe, "mcp", "test", "meta_ads"]])

    def test_hermes_executable_missing_keeps_token_and_fails(self):
        hermes = FakeHermes(HERMES_OK)
        with mock.patch.object(mtm, "find_hermes", return_value=None):
            code, data, out = self.run_json(self.renew_graph(), FakeMcp(), ["--hermes-test"], hermes)
        self.assertEqual(code, 2)
        self.assertEqual(data["outcome"], "FAILED")
        self.assertEqual(hermes.calls, [])
        self.assertEqual(data["hermes_test"], "hermes executable not found (PATH, /opt/venv/bin/hermes, $HERMES_HOME/bin/hermes)")
        self.assertTrue(data["candidate_kept"])
        self.assertEqual(self.env_values()["META_MCP_LONG_TOKEN"], TOKEN_C)

    def test_run_hermes_test_judges_text_not_exit_code(self):
        with mock.patch.object(mtm, "find_hermes", return_value="/fake/hermes"):
            ok, detail = mtm.run_hermes_test("meta_ads", FakeHermes(stdout="Connected. 3 tools.\n"))
            self.assertTrue(ok)
            self.assertEqual(detail, "passed: Connected. 3 tools.")
            ok, detail = mtm.run_hermes_test("meta_ads", FakeHermes(stdout="✗ meta_ads: Connection failed"))
            self.assertFalse(ok)
            self.assertTrue(detail.startswith("failed: "))
            ok, detail = mtm.run_hermes_test("meta_ads", FakeHermes(stdout="12 tools, 1 test failed"))
            self.assertFalse(ok)
            ok, detail = mtm.run_hermes_test("meta_ads", FakeHermes(stdout="Connected.\n"))
            self.assertFalse(ok)  # no tool listing means no proof
            ok, detail = mtm.run_hermes_test("meta_ads", FakeHermes(exc=RuntimeError("boom " + TOKEN_C)))
            self.assertEqual((ok, detail), (False, "could not run hermes mcp test: RuntimeError"))
            fake = FakeHermes(stdout="tools:  " + TOKEN_C + "\n" + "x" * 500)
            ok, detail = mtm.run_hermes_test("meta_ads", fake)
            self.assertEqual(fake.calls, [["/fake/hermes", "mcp", "test", "meta_ads"]])
            self.assertTrue(ok)
            self.assertIn("EAA[redacted]", detail)
            self.assertNotIn(TOKEN_C, detail)
            self.assertLessEqual(len(detail), len("passed: ") + 160)
        with mock.patch.object(mtm, "find_hermes", return_value=None):
            self.assertEqual(mtm.run_hermes_test("meta_ads", FakeHermes(HERMES_OK)),
                             (False, "hermes executable not found (PATH, /opt/venv/bin/hermes, $HERMES_HOME/bin/hermes)"))

    def test_find_hermes_checks_path_then_hermes_home(self):
        exe = self.install_fake_hermes()
        self.assertEqual(mtm.find_hermes(), exe)
        os.chmod(exe, 0o644)  # not executable: skipped by shutil.which
        with mock.patch.object(mtm.shutil, "which", return_value=None):
            found = mtm.find_hermes()
            self.assertIn(found, (None, "/opt/venv/bin/hermes"))
            os.chmod(exe, 0o755)  # $HERMES_HOME/bin/hermes is the last candidate
            if not os.path.isfile("/opt/venv/bin/hermes"):
                self.assertEqual(mtm.find_hermes(), exe)

    # -- bridge config ------------------------------------------------------------
    def write_config(self, text, path=None):
        path = path or os.path.join(self.tmp.name, "config.yaml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_check_bridge_config_yes_no_unknown(self):
        self.assertEqual(mtm.check_bridge_config(), "unknown")  # no $HERMES_HOME/config.yaml
        self.write_config(CONFIG_BRIDGE)
        self.assertEqual(mtm.check_bridge_config(), "yes")
        self.write_config(CONFIG_DIRECT)
        self.assertEqual(mtm.check_bridge_config(), "no")
        self.write_config("mcp_servers:\n  arcads:\n    command: npx\n")
        self.assertEqual(mtm.check_bridge_config(), "no")  # no meta_ads entry at all
        self.write_config("mcp_servers:\n  meta_ads:\n    command: python3\n    headers:\n      X: y\n")
        self.assertEqual(mtm.check_bridge_config(), "no")  # command plus headers is not the bridge shape
        self.write_config("mcp_servers:\n  meta_ads:   # bridge\n    command: python3\n")
        self.assertEqual(mtm.check_bridge_config(), "yes")
        other = self.write_config(CONFIG_BRIDGE, os.path.join(self.tmp.name, "elsewhere.yaml"))
        self.write_config(CONFIG_DIRECT)
        self.assertEqual(mtm.check_bridge_config(other), "yes")  # explicit path wins
        self.assertEqual(mtm.check_bridge_config(os.path.join(self.tmp.name, "nope.yaml")), "unknown")

    def test_bridge_config_valid_reaches_report_state_and_markdown(self):
        self.write_config(CONFIG_BRIDGE)
        code, data, out = self.run_json(self.renew_graph())
        self.assertEqual(data["bridge_config_valid"], "yes")
        self.assertEqual(self.state()["bridge_config_valid"], "yes")
        self.write_env(ENV_TEXT)
        self.write_config(CONFIG_DIRECT)
        code, out = self.run_main(self.renew_graph(), extra=["--markdown"])
        self.assertIn("- Bridge config valid: no", out)
        self.assertIn(row("bridge config valid", "no"), self.run_main(FakeGraph({}, (500, None)))[1])
        self.assertEqual(self.state()["bridge_config_valid"], "no")
        other = self.write_config(CONFIG_BRIDGE, os.path.join(self.tmp.name, "elsewhere.yaml"))
        code, data, out = self.run_json(FakeGraph({}, (500, None)), extra=["--config-file", other])
        self.assertEqual(data["bridge_config_valid"], "yes")
        os.remove(os.path.join(self.tmp.name, "config.yaml"))
        code, data, out = self.run_json(FakeGraph({}, (500, None)))
        self.assertEqual(data["bridge_config_valid"], "unknown")
        self.assertEqual(self.state()["bridge_config_valid"], "unknown")

    # -- env file resolution ------------------------------------------------------
    def test_resolve_env_file_order(self):
        other = os.path.join(self.tmp.name, "other.env")
        with mock.patch.dict(os.environ, {"META_MCP_DOTENV_PATH": other}):
            self.assertEqual(mtm.resolve_env_file(None), other)
            self.assertEqual(mtm.resolve_env_file("/explicit/.env"), "/explicit/.env")
            with mock.patch.dict(os.environ, {"META_MCP_ENV_FILE": "/env-file/.env"}):
                self.assertEqual(mtm.resolve_env_file(None), "/env-file/.env")
        self.assertEqual(mtm.resolve_env_file(None), os.path.join(self.tmp.name, ".env"))  # $HERMES_HOME/.env
        with mock.patch.dict(os.environ, {"HERMES_HOME": ""}):
            with mock.patch.object(mtm.os.path, "isfile", side_effect=lambda p: p == "/data/.env"):
                self.assertEqual(mtm.resolve_env_file(None), "/data/.env")
            with mock.patch.object(mtm.os.path, "isfile", return_value=False):
                self.assertEqual(mtm.resolve_env_file(None), os.path.expanduser("~/.hermes/.env"))

    def test_dotenv_path_alias_drives_a_run(self):
        alias = os.path.join(self.tmp.name, "alias.env")
        with open(alias, "w", encoding="utf-8") as fh:
            fh.write(ENV_TEXT)
        with mock.patch.dict(os.environ, {"META_MCP_DOTENV_PATH": alias}):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = mtm.main(["--state-file", self.state_file, "--json"], graph_get_fn=self.renew_graph(),
                                mcp_post_fn=FakeMcp(), now=lambda: NOW)
        self.assert_no_secrets(out.getvalue())
        data = json.loads(out.getvalue().splitlines()[0])
        self.assertEqual(code, 0)
        self.assertEqual(data["env_file"], alias)
        self.assertEqual(data["outcome"], "RENEWED")
        with open(alias, "r", encoding="utf-8") as fh:
            self.assertEqual(fh.read(), ENV_TEXT.replace(TOKEN_T, TOKEN_C))
        self.assertEqual(self.read_env(), ENV_TEXT)  # $HERMES_HOME/.env untouched
        self.assertEqual(self.state()["last_outcome"], "RENEWED")

    # -- state and output ---------------------------------------------------------
    def test_state_counter_increments_and_resets(self):
        same = FakeGraph({TOKEN_T: token_info()}, (200, {"access_token": TOKEN_T}))
        self.run_main(same)
        self.run_main(same)
        st = self.state()
        self.assertEqual(st["consecutive_non_advancing_runs"], 2)
        self.assertIsNone(st["last_advancing_expiry_at"])
        self.assertEqual(st["last_run"], mtm.iso(NOW))
        self.assertEqual(st["status_compat"], "NO_CHANGE")
        self.run_main(self.renew_graph())
        st = self.state()
        self.assertEqual(st["consecutive_non_advancing_runs"], 0)
        self.assertEqual(st["last_advancing_expiry_at"], mtm.iso(NOW))
        self.assertEqual(st["last_outcome"], "RENEWED")
        self.assertEqual(sorted(st), ["bridge_config_valid", "consecutive_non_advancing_runs", "data_access_expires_at",
                                      "days_remaining", "expires_at", "last_advancing_expiry_at", "last_outcome",
                                      "last_run", "notes", "schema_version", "status_compat"])
        self.assertTrue(all(isinstance(n, str) and len(n) <= 200 for n in st["notes"]))

    def test_json_output_shape(self):
        code, data, out = self.run_json(self.renew_graph())
        for key in ("outcome", "message", "token_type", "scopes_ok", "missing_scopes", "expires_at",
                    "data_access_expires_at", "days_remaining", "next_renewal_deadline", "next_steps",
                    "candidate_expires_at", "candidate_differed", "would_write", "env_file", "state_file",
                    "required_action", "status_compat", "written", "rolled_back", "candidate_kept",
                    "expiry_advanced", "via_handoff", "smoke_test", "hermes_test", "bridge_config_valid",
                    "notes", "dry_run", "min_days", "exit_code", "consecutive_non_advancing_runs"):
            self.assertIn(key, data)
        self.assertEqual(out.strip().splitlines()[1], "Outcome: RENEWED")
        self.assertEqual(data["exit_code"], 0)
        self.assertEqual(data["token_type"], "USER")
        self.assertTrue(data["scopes_ok"])
        self.assertEqual(data["status_compat"], "SUCCESS")
        self.assertTrue(data["candidate_differed"])
        self.assertTrue(data["expiry_advanced"])
        self.assertTrue(data["written"])
        self.assertFalse(data["via_handoff"])
        self.assertFalse(data["candidate_kept"])
        self.assertEqual(data["bridge_config_valid"], "unknown")
        self.assertEqual(data["hermes_test"], "not run")
        self.assertEqual(data["required_action"], "none")
        self.assertEqual(data["candidate_expires_at"], mtm.iso(C_EXP))
        self.assertEqual(data["next_renewal_deadline"], mtm.iso(C_EXP - 21 * DAY))
        self.assertEqual(data["env_file"], self.env_file)
        self.assertEqual(data["state_file"], self.state_file)

    def test_human_output_lists_every_field(self):
        code, out = self.run_main(self.renew_graph())
        for label in ("outcome:", "status:", "message:", "token type:", "scopes ok:", "expires_at:",
                      "data_access_expires_at:", "days remaining:", "candidate expires_at:", "written:",
                      "expiry advanced:", "bridge config valid:", "smoke test:", "hermes mcp test:",
                      "next renewal deadline:", "required action:", "notes:", "next steps:"):
            self.assertIn(label, out)
        self.assertIn(row("written", "yes"), out)
        self.assertIn(row("expiry advanced", "yes"), out)
        self.assertIn(row("hermes mcp test", "not run"), out)
        self.assertIn(row("required action", "none"), out)
        self.assertIn(row("bridge config valid", "unknown"), out)
        self.write_env(ENV_TEXT)
        code, out = self.run_main(self.renew_graph(), FakeMcp(fail=True))
        self.assertIn(row("written", "rolled back"), out)
        self.assertIn(row("expiry advanced", "no"), out)
        self.assertIn(row("status", "FAILED"), out)

    def test_markdown_report_block(self):
        code, out = self.run_main(self.renew_graph(), extra=["--markdown"])
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "# SUCCESS",
            "",
            "- Outcome detail: RENEWED",
            "- Current expiry (UTC): %s" % mtm.iso(C_EXP),
            "- Candidate expiry (UTC): %s" % mtm.iso(C_EXP),
            "- Candidate differed: yes",
            "- Credential replaced: yes",
            "- Expiry advanced: yes",
            "- Bridge config valid: unknown",
            "- MCP smoke test: passed",
            "- Hermes mcp test: not run",
            "- Required action: none",
            "Outcome: RENEWED",
        ])

    def test_markdown_report_for_other_outcomes(self):
        code, out = self.run_main(self.renew_graph(c_exp=T_EXP), extra=["--markdown"])
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertEqual(lines[0], "# NO_CHANGE")  # four-value headline: nothing was written
        self.assertIn("- Outcome detail: REPLACED_SAME_EXPIRY", lines)
        self.assertIn("- Current expiry (UTC): %s" % mtm.iso(T_EXP), lines)
        self.assertIn("- Candidate expiry (UTC): %s" % mtm.iso(T_EXP), lines)
        self.assertIn("- Candidate differed: yes", lines)
        self.assertIn("- Credential replaced: no", lines)
        self.assertIn("- Expiry advanced: no", lines)
        self.assertIn("- MCP smoke test: not run", lines)
        self.assertEqual(lines[-1], "Outcome: REPLACED_SAME_EXPIRY")

        code, out = self.run_main(self.renew_graph(c_exp=T_EXP), extra=["--markdown", "--replace-same-expiry"])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], "# SUCCESS")
        self.assertIn("- Outcome detail: REPLACED_SAME_EXPIRY", lines)
        self.assertIn("- Credential replaced: yes", lines)
        self.assertIn("- Expiry advanced: no", lines)

        self.write_env(ENV_TEXT)
        code, out = self.run_main(self.renew_graph(), FakeMcp(fail=True), ["--markdown"])
        lines = out.splitlines()
        self.assertEqual(lines[0], "# FAILED")
        self.assertIn("- Credential replaced: no", lines)
        self.assertIn("- MCP smoke test: failed", lines)
        self.assertTrue(any(l.startswith("- Required action: Meta rejected the new token") for l in lines), lines)

        self.write_env("OTHER=1\n")
        code, out = self.run_main(FakeGraph({}, (500, None)), extra=["--markdown"])
        lines = out.splitlines()
        self.assertEqual(lines[0], "# REAUTH_REQUIRED")
        self.assertIn("- Current expiry (UTC): unavailable", lines)
        self.assertIn("- Candidate expiry (UTC): unavailable", lines)
        self.assertIn("- Candidate differed: unavailable", lines)
        self.assertTrue(any(l.startswith("- Required action: a human must mint a new short-lived USER token") for l in lines), lines)
        self.assertEqual(lines[-1], "Outcome: REAUTH_REQUIRED")

        self.write_env(ENV_TEXT)
        graph = FakeGraph({TOKEN_T: token_info(expires_at=NOW + 5 * DAY)}, (200, {"access_token": TOKEN_T}))
        code, out = self.run_main(graph, extra=["--markdown"])
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertEqual(lines[0], "# NO_CHANGE")
        self.assertIn("- Candidate differed: no", lines)
        self.assertIn("- Required action: re-authorize before %s (fewer than 21 days remain)" % mtm.iso(NOW + 5 * DAY), lines)

    def test_redact_covers_pattern_and_known_secrets(self):
        self.assertEqual(mtm.redact("x " + "EAA" + "abcdefghijklmnop" + " y"), "x EAA[redacted] y")
        mtm._SECRETS.add(APP_SECRET)
        self.assertEqual(mtm.redact("secret=" + APP_SECRET), "secret=[redacted]")
        self.assertNotIn(TOKEN_C, mtm.redact("leak " + TOKEN_C + " end"))
        self.assertIsNone(mtm.iso(None))
        self.assertEqual(mtm.iso(0), "never")
        self.assertEqual(mtm.iso(NOW), "2025-09-04T15:33:20Z")

    def test_handoff_secret_never_reaches_output_or_state(self):
        self.write_env(ENV_TEXT + HANDOFF_LINE)
        leaky = {"message": "cannot exchange %s (app %s)" % (TOKEN_H, APP_SECRET), "code": 100}
        graph = FakeGraph({TOKEN_H: token_info()}, (400, {"error": leaky}))
        code, data, out = self.run_json(graph)  # run_json asserts TOKEN_H and APP_SECRET are absent
        self.assertEqual(data["outcome"], "FAILED")
        self.assertIn("[redacted]", data["message"])
        self.assert_no_secrets(json.dumps(self.state()))


if __name__ == "__main__":
    unittest.main()
