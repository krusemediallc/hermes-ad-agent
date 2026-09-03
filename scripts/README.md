# scripts/

Four helper scripts, all Python standard library only (3.9+), none of which
ever prints a secret value. Two are read-only (`onboarding_doctor.py`,
`check_docs_consistency.py`). `meta_mcp_bridge.py` is a long-running local MCP
server that writes nothing. `meta_token_maintenance.py` is the one script that
writes: it rewrites a single line of the env file, and only under a lock, a
compare-and-swap, and a smoke test. None of them calls `hermes` with anything
but `--version` and `config path` / `config env-path`. Run them from the
workspace root (the repo clone directory); quote the path if it has spaces.

Tests (offline, no Hermes and no Meta needed):

```
python3 -m unittest discover -s tests
```

## onboarding_doctor.py

Verifies the state of a Hermes install against what the pack expects. It is the
same check SETUP.md Step 8 asks the agent to run, and it is safe to run at any
time, including from a cron job.

```
python3 scripts/onboarding_doctor.py
python3 scripts/onboarding_doctor.py --json
python3 scripts/onboarding_doctor.py --workspace /absolute/path/to/hermes-ad-agent
python3 scripts/onboarding_doctor.py --meta-token-check            # checks META_MCP_TOKEN, falls back to ACCESS_TOKEN
python3 scripts/onboarding_doctor.py --meta-token-check ACCESS_TOKEN
```

What it checks, in order:

1. `hermes` executable (PATH, then `/opt/venv/bin/hermes`, then `$HERMES_HOME/bin`) and `hermes --version`.
2. `HERMES_HOME` (`$HERMES_HOME`, else `hermes config path`, else `~/.hermes`, else `/data`) plus the config, env, skills, and mcp-tokens paths under it.
3. The non-secret setup-state file (`$HERMES_HOME/hermes-ad-agent/setup-state.json`, fallback `~/.hermes/hermes-ad-agent/setup-state.json`): present, `schema_version` 1, absolute `workspace_root` that exists, valid `meta_backend`.
4. `skills-manifest.txt`: every listed skill exists in `<workspace>/skills/<name>/SKILL.md` (BLOCK if not) and in the Hermes skills directory (WARN if not).
5. `config.yaml` literal-secret scan: an `Authorization:` value that is not a `${VAR}` reference, a literal `Bearer EAA...` token, or any long token-like literal. Only line numbers are reported.
6. Env file (from `hermes config env-path`, else `$HERMES_HOME/.env`, plus `<workspace>/.env`): which of `META_MCP_TOKEN`, `ACCESS_TOKEN`, `AD_ACCOUNT_ID` are set (names only) and whether the file mode is 600.
7. Workspace hygiene: `BRAND.md` present, `memory/accounts` present, `.gitignore` covers `memory/`, `ad-runs/`, `research/`, `outputs/`, `.env`.
8. With `--meta-token-check`: calls the Graph API `debug_token` and `/me/permissions` endpoints and reports token type, granted vs missing scopes (all seven the hosted Meta MCP requires), `expires_at` and `data_access_expires_at` as ISO timestamps, and days remaining. WARN under 21 days; BLOCK if expired, if a required scope is missing, or if the token checked as `META_MCP_TOKEN` is not a USER token. A SYSTEM_USER token is fine for the Meta Ads CLI route, so check it under `ACCESS_TOKEN` instead. The token itself is never printed, in any form.
9. `--arcads` is out of scope for this doctor: verify Arcads with `hermes mcp test arcads` and a native read-only call as described in SETUP.md Step 3.

The workspace defaults to the setup-state file's `workspace_root`, then the
current directory. Every non-OK line ends with a pointer to the SETUP.md step
that fixes it.

Exit codes: `0` every check OK (setup COMPLETE), `1` at least one WARN
(PARTIAL), `2` at least one BLOCK. `--json` prints `{exit_code, workspace,
hermes_home, checks[]}` with the same statuses.

Notes: `hermes` is not always on PATH for agent shells (managed containers
put it at `/opt/venv/bin/hermes`), which is why the discovery order above
exists. Where a Hermes subcommand's output shape is not what the script
expects, verify with `hermes config --help` and your live tool list.

## check_docs_consistency.py

Lints the pack's Markdown so retired guidance does not creep back in. It is the
first step of the GitHub Actions workflow (`.github/workflows/verify.yml`) and
runs the same way locally:

```
python3 scripts/check_docs_consistency.py
```

It scans every `*.md` git would publish (skipping `.git/`, `memory/`, `outputs/`,
`ad-runs/`, `research/`, and anything gitignored such as the maintainer's local
notes) and reports `file:line` for:

- an em-dash character (U+2014) anywhere except the two allowed
  `skills/human-ad-copy` lines that document the no-em-dash rule;
- each phrase in the `OBSOLETE` list at the top of the script (retired
  onboarding claims, the old multi-ad default when it is not preceded by
  "never", and the retired improvised write path);
- wording that says a local file is passed to an `ads_creative_upload` tool on
  the same line (the hosted MCP upload tools take public URLs only);
- `--bodies`, `--titles`, or `--descriptions` followed by two quoted values on
  one flag (the CLI wants the flag repeated per value);
- an Arcads credit figure written as an estimate (the retired tilde 0.9 ballpark);
- `skills-manifest.txt` missing, duplicated, or not matching `skills/*/`
  exactly;
- a `SKILL.md` whose frontmatter `name` differs from its folder.

Exit codes: `0` clean, `1` one or more hits (all printed).

## meta_mcp_bridge.py

A local stdio MCP server that Hermes runs as a **command-type** MCP server and
that proxies every request to Meta's hosted Ads MCP
(`https://mcp.facebook.com/ads`) over Streamable HTTP. It exists for two
reasons: token rotation without a gateway restart, and the MCP SDK 2.0 empty
`_meta` blocker. SETUP.md Step 4, Route A2 is the install guide; the config
entry it expects is:

```yaml
mcp_servers:
  meta_ads:
    command: python3
    args: ["/absolute/path/to/hermes-ad-agent/scripts/meta_mcp_bridge.py", "--env-file", "/data/.env"]
    trust: untrusted
    enabled: true
```

```
python3 scripts/meta_mcp_bridge.py [--env-file PATH] [--token-var META_MCP_TOKEN]
                                   [--upstream https://mcp.facebook.com/ads]
                                   [--timeout 120] [--log-level info]
                                   [--allow-any-upstream]
```

What it does on every request:

1. Reads the bearer token from the env file **each time**, so a rotated
   token (a manual replacement, or `meta_token_maintenance.py`) is used on
   the next call with no gateway restart and no managed-app redeploy.
2. Strips an empty `params._meta` object, which MCP SDK 2.0 clients add and
   Meta rejects with JSON-RPC `-32602` `"meta" for Request must be an dict or
   null`. A non-empty `_meta` is preserved.
3. Passes Meta's real JSON-RPC error code and message back to Hermes instead
   of a generic error, so the next failure is diagnosable.

Env-file resolution when `--env-file` is omitted: `$META_MCP_ENV_FILE`, else
`$HERMES_HOME/.env`, else `/data/.env`, else `~/.hermes/.env`. Pass it
explicitly in the config `args` anyway; a gateway session's environment can
differ from your terminal's. The file holds one line,
`META_MCP_TOKEN='<fully scoped USER token>'`, mode `0600`. That is the single
canonical name; if a prototype used `META_MCP_LONG_TOKEN`, rename the line.

Safety properties: never writes the token anywhere (no log, no file, no
error text); redacts error text before forwarding it; refuses any upstream
that is not `https` on `facebook.com` unless started with
`--allow-any-upstream`, which is for local test servers only and never
belongs in a real config. It has no exit-code contract of its own: it runs
until Hermes closes its stdin. After adding it, run `hermes config check`,
then `hermes mcp test meta_ads` (read the text), then confirm a fresh normal
session can find `mcp__meta_ads__ads_get_ad_accounts` with `tool_search` and
call it read-only.

## meta_token_maintenance.py

Deterministic token upkeep for the bridge transport. No LLM anywhere in it.
Meant to run weekly as a **script job** (no agent) on the Hermes scheduler,
with the outcome line delivered to the user's channel; SETUP.md Step 7 covers
the job and its dry-run-first order.

```
python3 scripts/meta_token_maintenance.py [--env-file PATH] [--token-var META_MCP_TOKEN]
                                          [--app-id-var META_APP_ID] [--app-secret-var META_APP_SECRET]
                                          [--dry-run] [--json] [--replace-same-expiry]
                                          [--min-days 21] [--state-file PATH] [--no-smoke-test]
```

What it does, in order:

1. Reads the current token from the env file and inspects it with
   `debug_token` (type, scopes, expiry, data-access expiry).
2. Exchanges it with `grant_type=fb_exchange_token`, using `META_APP_ID` and
   `META_APP_SECRET` from the same env file. Without those two values the
   exchange is skipped and the run reports `NO_CHANGE` with days remaining.
3. Inspects the candidate: it must be a USER token carrying all seven scopes
   the hosted MCP requires.
4. Classifies the result, and writes only when the outcome is `RENEWED`.
5. On a write: atomic (temp file, fsync, rename, mode `0600`), guarded by a
   lock file and a compare-and-swap on the token line, then a direct MCP
   `initialize` plus `tools/list` smoke test with the new token. Any failure
   rolls the line back. Because the bridge re-reads the env file per request,
   a passing smoke test means the live gateway uses the new token on its next
   call.

Outcomes, exactly:

| Outcome | Meaning | Written? |
|---|---|---|
| `RENEWED` | different token **and** expiry advanced by more than a day | yes |
| `REPLACED_SAME_EXPIRY` | different token, expiry not advanced; **not a renewal**, the old token stays valid | no, unless `--replace-same-expiry` |
| `NO_CHANGE` | same token back, or exchange skipped because app credentials are absent | no |
| `REAUTH_REQUIRED` | token invalid or expired, or Meta refused the exchange; a human must generate a new token | no |
| `FAILED` | lock held, missing scopes on the candidate, compare-and-swap mismatch, or a write or smoke-test failure (rolled back) | no |

Exit codes: `0` healthy (`RENEWED`, or `NO_CHANGE` with days remaining at or
above `--min-days`); `1` warning (`REPLACED_SAME_EXPIRY` left unwritten, or
fewer than `--min-days` remaining); `2` `REAUTH_REQUIRED` or `FAILED`.
`--json` prints the same outcome as a JSON object for the scheduler's
delivery; `--dry-run` writes nothing and is the first run you make.

State file, non-secret: `$HERMES_HOME/hermes-ad-agent/token-maintenance-state.json`
(override with `--state-file`) holding last outcome, `expires_at`,
`data_access_expires_at`, the last advancing expiry, consecutive
non-advancing runs, and days remaining.

Safety properties: never prints the token or the app secret, in any output
mode or error; never writes without the lock, the compare-and-swap, and the
smoke test (`--no-smoke-test` exists for offline tests, not for production);
never writes under `--dry-run`; never generates a token from nothing.
Honesty rule: Meta returned an equal-expiry token on the one observed
re-exchange, so whether re-exchange ever advances expiry is unverified. The
script reports what actually happened, and the credential-expiry reminder
plus the auth-failure alert path still cover manual reauthorization.

## CI

`.github/workflows/verify.yml` runs on every push and pull request: the docs
check, the doctor in `--json` mode (exit 0 or 1 passes because CI has no
Hermes install; exit 2 fails), `py_compile` on every `.py`, the unit tests
(`python3 -m unittest discover -s tests -v`, which exercise the bridge and the
maintenance script offline), a grep for token-shaped literals (excluding the
two scripts that define the patterns), and `validate_copy.py --help`.
