"""Tests for scripts/meta_token_maintenance.py. Standard library unittest, no network.

Run from the repo root:  python3 -m unittest discover -s tests -v

Both Graph API and MCP transports are replaced with in-memory fakes. Every run
asserts that the fake token strings and the fake app secret never reach stdout
or the state file.
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
TOKEN_T = "EAA" + "fakeTOKENvalue1234567890"
TOKEN_C = "EAA" + "fakeTOKENvalue0987654321"
TOKEN_X = "EAA" + "fakeTOKENvalue5555555555"
APP_ID = "123456789012345"
APP_SECRET = "fakeappsecret00000000000000"
NOW = 1_757_000_000
DAY = 86400
T_EXP = NOW + 30 * DAY
SCOPES = list(mtm.REQUIRED_SCOPES)

ENV_TEXT = (
    "# Hermes env file\n"
    "export OTHER=\"keep me\"\n"
    "META_APP_ID=%s\n"
    "META_APP_SECRET='%s'\n"
    "META_MCP_TOKEN='%s'  # live token\n"
    "TRAILING=value # note\n"
) % (APP_ID, APP_SECRET, TOKEN_T)


def token_info(token_type="USER", expires_at=T_EXP, scopes=None, valid=True):
    return {"type": token_type, "is_valid": valid, "scopes": SCOPES if scopes is None else scopes,
            "expires_at": expires_at, "data_access_expires_at": expires_at + 30 * DAY, "app_id": APP_ID}


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


class FakeMcp:
    """mcp_post(url, headers, body, timeout) stand-in. initialize answers JSON with a session id;
    tools/list answers as an SSE stream so both body parsers are exercised."""

    def __init__(self, fail=False, tools=None):
        self.fail, self.tools, self.calls = fail, tools, []

    def __call__(self, url, headers, body, timeout):
        msg = json.loads(body.decode("utf-8"))
        self.calls.append((msg.get("method"), dict(headers)))
        if self.fail:
            err = {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32001, "message": "unauthorized"}}
            return 401, {"content-type": "application/json"}, json.dumps(err)
        if msg.get("method") == "initialize":
            reply = {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": mtm.PROTOCOL_VERSION}}
            return 200, {"content-type": "application/json", "mcp-session-id": "sess-1"}, json.dumps(reply)
        if msg.get("method") == "tools/list":
            tools = [{"name": "ads_get_ad_accounts"}, {"name": "ads_create_campaign"}] if self.tools is None else self.tools
            payload = json.dumps({"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}})
            return 200, {"content-type": "text/event-stream"}, "event: message\ndata: %s\n\n" % payload
        return 202, {}, ""


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
        for key in ("META_MCP_ENV_FILE", "META_APP_ID", "META_APP_SECRET", "META_MCP_TOKEN"):
            os.environ.pop(key, None)
        mtm._SECRETS.clear()

    # -- helpers ------------------------------------------------------------------
    def write_env(self, text):
        with open(self.env_file, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    def read_env(self):
        with open(self.env_file, "r", encoding="utf-8", newline="") as fh:
            return fh.read()

    def assert_no_secrets(self, text):
        for secret in (TOKEN_T, TOKEN_C, TOKEN_X, APP_SECRET):
            self.assertNotIn(secret, text)

    def run_main(self, graph, mcp=None, extra=()):
        argv = ["--env-file", self.env_file, "--state-file", self.state_file] + list(extra)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mtm.main(argv, graph_get_fn=graph, mcp_post_fn=mcp or FakeMcp(), now=lambda: NOW)
        text = out.getvalue()
        self.assert_no_secrets(text)
        self.assertRegex(text.rstrip().splitlines()[-1], r"^Outcome: [A-Z_]+$")
        return code, text

    def state(self):
        with open(self.state_file, "r", encoding="utf-8") as fh:
            raw = fh.read()
        self.assert_no_secrets(raw)
        return json.loads(raw)

    def renew_graph(self, c_exp=T_EXP + 30 * DAY, c_scopes=None, c_type="USER", exchange=None):
        tokens = {TOKEN_T: token_info(), TOKEN_C: token_info(token_type=c_type, expires_at=c_exp, scopes=c_scopes)}
        return FakeGraph(tokens, exchange or (200, {"access_token": TOKEN_C, "token_type": "bearer", "expires_in": 5184000}))

    # -- dotenv handling ----------------------------------------------------------
    def test_rewrite_preserves_every_other_byte(self):
        text = "export A=\"old\"\r\nA=old # c\n# A=commented\nAB=old\nA = 'old' # q\nB=x\nA=old"
        new, hits = mtm.rewrite_token_lines(text, "A", "new")
        self.assertEqual(hits, 4)
        self.assertEqual(new, "export A=\"new\"\r\nA=new # c\n# A=commented\nAB=old\nA = 'new' # q\nB=x\nA=new")
        self.assertEqual(mtm.parse_dotenv(new)["A"], "new")
        parsed = mtm.parse_dotenv("K='v' # note\nJ=\"q\"\nL=w # z\nexport M=m\n# comment\nbare\n")
        self.assertEqual(parsed, {"K": "v", "J": "q", "L": "w", "M": "m"})

    def test_renewed_writes_atomically_and_preserves_file(self):
        mcp = FakeMcp()
        graph = self.renew_graph()
        code, out = self.run_main(graph, mcp)
        self.assertEqual(code, 0)
        self.assertIn("Outcome: RENEWED", out)
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_C))
        self.assertIn("META_MCP_TOKEN='%s'  # live token\n" % TOKEN_C, self.read_env())
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
        self.assertIn("live gateway uses the new token on its next call", out)
        st = self.state()
        self.assertEqual(st["schema_version"], 1)
        self.assertEqual(st["last_outcome"], "RENEWED")
        self.assertEqual(st["consecutive_non_advancing_runs"], 0)
        self.assertEqual(st["last_advancing_expiry_at"], mtm.iso(NOW))
        self.assertEqual(st["expires_at"], mtm.iso(T_EXP + 30 * DAY))
        self.assertEqual(st["days_remaining"], 60.0)

    # -- classification -----------------------------------------------------------
    def test_replaced_same_expiry_is_not_written_by_default(self):
        mcp = FakeMcp()
        code, out = self.run_main(self.renew_graph(c_exp=T_EXP), mcp)
        self.assertEqual(code, 1)
        self.assertIn("Outcome: REPLACED_SAME_EXPIRY", out)
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(mcp.calls, [])
        self.assertEqual(self.state()["consecutive_non_advancing_runs"], 1)

    def test_one_day_advance_is_still_same_expiry(self):
        code, out = self.run_main(self.renew_graph(c_exp=T_EXP + DAY))
        self.assertEqual(code, 1)
        self.assertIn("Outcome: REPLACED_SAME_EXPIRY", out)
        self.assertEqual(self.read_env(), ENV_TEXT)

    def test_replaced_same_expiry_written_with_flag(self):
        code, out = self.run_main(self.renew_graph(c_exp=T_EXP + 3600), FakeMcp(), ["--replace-same-expiry", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_C))
        first = json.loads(out.splitlines()[0])
        self.assertEqual(first["outcome"], "REPLACED_SAME_EXPIRY")
        self.assertTrue(first["written"])
        self.assertEqual(self.state()["consecutive_non_advancing_runs"], 1)

    def test_no_change_when_meta_returns_same_token(self):
        graph = FakeGraph({TOKEN_T: token_info()}, (200, {"access_token": TOKEN_T, "expires_in": 100}))
        mcp = FakeMcp()
        code, out = self.run_main(graph, mcp)
        self.assertEqual(code, 0)
        self.assertIn("Outcome: NO_CHANGE", out)
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(stat.S_IMODE(os.stat(self.env_file).st_mode), 0o644)  # untouched
        self.assertEqual(mcp.calls, [])

    def test_no_change_under_min_days_exits_1(self):
        graph = FakeGraph({TOKEN_T: token_info(expires_at=NOW + 5 * DAY)}, (200, {"access_token": TOKEN_T}))
        code, out = self.run_main(graph)
        self.assertEqual(code, 1)
        self.assertIn("Outcome: NO_CHANGE", out)
        self.assertIn("plan a manual re-auth", out)
        code, out = self.run_main(graph, extra=["--min-days", "3"])
        self.assertEqual(code, 0)

    def test_exchange_skipped_without_app_credentials(self):
        self.write_env("META_MCP_TOKEN=%s\n" % TOKEN_T)
        graph = FakeGraph({TOKEN_T: token_info()}, (500, None))
        code, out = self.run_main(graph)
        self.assertEqual(code, 0)
        self.assertIn("Outcome: NO_CHANGE", out)
        self.assertIn("exchange skipped: META_APP_ID/META_APP_SECRET not set", out)
        self.assertEqual([p for p, _ in graph.calls], ["/v25.0/debug_token"])
        self.assertEqual(graph.calls[0][1]["access_token"], TOKEN_T)  # fallback: token inspects itself

    def test_reauth_required_on_oauth_error_190(self):
        oauth = {"message": "Error validating access token: Session has expired", "type": "OAuthException", "code": 190}
        code, out = self.run_main(self.renew_graph(exchange=(400, {"error": oauth})))
        self.assertEqual(code, 2)
        self.assertIn("Outcome: REAUTH_REQUIRED", out)
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(self.state()["last_outcome"], "REAUTH_REQUIRED")

    def test_reauth_required_when_token_missing(self):
        self.write_env("OTHER=1\n")
        code, out = self.run_main(FakeGraph({}, (500, None)))
        self.assertEqual(code, 2)
        self.assertIn("Outcome: REAUTH_REQUIRED", out)
        self.assertIn("no token in env file", out)

    def test_reauth_required_when_current_token_invalid_or_expired(self):
        code, out = self.run_main(FakeGraph({}, (500, None)))  # debug_token: is_valid false
        self.assertEqual(code, 2)
        self.assertIn("Outcome: REAUTH_REQUIRED", out)
        code, out = self.run_main(FakeGraph({TOKEN_T: token_info(expires_at=NOW - 10)}, (500, None)))
        self.assertEqual(code, 2)
        self.assertIn("Outcome: REAUTH_REQUIRED", out)
        self.assertIn("expired", out)

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
        self.assertEqual(self.read_env(), ENV_TEXT)

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

    # -- write safety -------------------------------------------------------------
    def test_dry_run_writes_nothing(self):
        mcp = FakeMcp()
        code, out = self.run_main(self.renew_graph(), mcp, ["--dry-run", "--json"])
        self.assertEqual(code, 0)
        first = json.loads(out.splitlines()[0])
        self.assertEqual(first["outcome"], "RENEWED")
        self.assertTrue(first["would_write"])
        self.assertFalse(first["written"])
        self.assertTrue(first["dry_run"])
        self.assertEqual(self.read_env(), ENV_TEXT)
        self.assertEqual(stat.S_IMODE(os.stat(self.env_file).st_mode), 0o644)
        self.assertEqual(os.listdir(self.tmp.name), [".env"])  # no state dir, no lock, no temp file
        self.assertEqual(mcp.calls, [])

    def test_cas_mismatch_aborts_without_writing(self):
        def exchange():
            self.write_env(ENV_TEXT.replace(TOKEN_T, TOKEN_X))  # another writer rotates the token mid-run
            return 200, {"access_token": TOKEN_C, "expires_in": 5184000}
        tokens = {TOKEN_T: token_info(), TOKEN_C: token_info(expires_at=T_EXP + 30 * DAY)}
        code, out = self.run_main(FakeGraph(tokens, exchange))
        self.assertEqual(code, 2)
        self.assertIn("Outcome: FAILED", out)
        self.assertIn("token changed underneath, not writing", out)
        self.assertEqual(self.read_env(), ENV_TEXT.replace(TOKEN_T, TOKEN_X))

    def test_smoke_test_failure_rolls_back(self):
        code, out = self.run_main(self.renew_graph(), FakeMcp(fail=True))
        self.assertEqual(code, 2)
        self.assertIn("Outcome: FAILED", out)
        self.assertIn("rolled back to the previous token", out)
        self.assertEqual(self.read_env(), ENV_TEXT)
        st = self.state()
        self.assertEqual(st["last_outcome"], "FAILED")
        self.assertEqual(st["expires_at"], mtm.iso(T_EXP))
        self.assertIn("rolled back", " ".join(st["notes"]))

    def test_smoke_test_requires_an_ads_tool(self):
        code, out = self.run_main(self.renew_graph(), FakeMcp(tools=[{"name": "other_tool"}]))
        self.assertEqual(code, 2)
        self.assertIn("none with ads_ in the name", out)
        self.assertEqual(self.read_env(), ENV_TEXT)

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

    # -- state and output ---------------------------------------------------------
    def test_state_counter_increments_and_resets(self):
        same = FakeGraph({TOKEN_T: token_info()}, (200, {"access_token": TOKEN_T}))
        self.run_main(same)
        self.run_main(same)
        st = self.state()
        self.assertEqual(st["consecutive_non_advancing_runs"], 2)
        self.assertIsNone(st["last_advancing_expiry_at"])
        self.assertEqual(st["last_run"], mtm.iso(NOW))
        self.run_main(self.renew_graph())
        st = self.state()
        self.assertEqual(st["consecutive_non_advancing_runs"], 0)
        self.assertEqual(st["last_advancing_expiry_at"], mtm.iso(NOW))
        self.assertEqual(st["last_outcome"], "RENEWED")
        self.assertTrue(all(isinstance(n, str) and len(n) <= 200 for n in st["notes"]))

    def test_json_output_shape(self):
        code, out = self.run_main(self.renew_graph(), FakeMcp(), ["--json"])
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 2)
        data = json.loads(lines[0])
        for key in ("outcome", "token_type", "scopes_ok", "expires_at", "data_access_expires_at", "days_remaining",
                    "written", "smoke_test", "next_renewal_deadline", "next_steps", "exit_code", "notes"):
            self.assertIn(key, data)
        self.assertEqual(lines[1], "Outcome: RENEWED")
        self.assertEqual(data["exit_code"], 0)
        self.assertEqual(data["token_type"], "USER")
        self.assertTrue(data["scopes_ok"])
        self.assertEqual(data["next_renewal_deadline"], mtm.iso(T_EXP + 30 * DAY - 21 * DAY))

    def test_human_output_lists_every_field(self):
        code, out = self.run_main(self.renew_graph())
        for label in ("outcome:", "token type:", "scopes ok:", "expires_at:", "data_access_expires_at:",
                      "days remaining:", "written:", "smoke test:", "next renewal deadline:", "next steps:"):
            self.assertIn(label, out)
        self.assertIn("written:                yes", out)

    def test_redact_covers_pattern_and_known_secrets(self):
        self.assertEqual(mtm.redact("x " + "EAA" + "abcdefghijklmnop" + " y"), "x EAA[redacted] y")
        mtm._SECRETS.add(APP_SECRET)
        self.assertEqual(mtm.redact("secret=" + APP_SECRET), "secret=[redacted]")
        self.assertNotIn(TOKEN_C, mtm.redact("leak " + TOKEN_C + " end"))


if __name__ == "__main__":
    unittest.main()
