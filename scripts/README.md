# scripts/

Four helper scripts, all Python standard library only (3.9+), none of which
ever prints a secret value. Two are read-only (`onboarding_doctor.py`,
`check_docs_consistency.py`). `meta_mcp_bridge.py` is a long-running local MCP
server that writes nothing. `meta_token_maintenance.py` is the one script that
writes: it rewrites the long-lived token line of the env file (and, on the
reauthorization path, clears the short-lived handoff line), and only under a
lock, a compare-and-swap, and a smoke test. None of them calls `hermes` with
anything but `--version` and `config path` / `config env-path`, except
`meta_token_maintenance.py --hermes-test`, which also runs
`hermes mcp test meta_ads`. Run them from the workspace root (the repo clone
directory); quote the path if it has spaces.

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
python3 scripts/onboarding_doctor.py --meta-token-check                       # META_MCP_LONG_TOKEN, then META_MCP_TOKEN, then ACCESS_TOKEN
python3 scripts/onboarding_doctor.py --meta-token-check ACCESS_TOKEN          # the CLI route's system user token
```

`--meta-token-check` defaults to `META_MCP_LONG_TOKEN`, the long-lived token
the Meta MCP bridge reads, and falls back to `META_MCP_TOKEN` (the short-lived
handoff line, normally empty) and then `ACCESS_TOKEN`; pass a name to check one
variable only.

What it checks, in order:

1. `hermes` executable (PATH, then `/opt/venv/bin/hermes`, then `$HERMES_HOME/bin`) and `hermes --version`.
2. `HERMES_HOME` (`$HERMES_HOME`, else `hermes config path`, else `~/.hermes`, else `/data`) plus the config, env, skills, and mcp-tokens paths under it.
3. The non-secret setup-state file (`$HERMES_HOME/hermes-ad-agent/setup-state.json`, fallback `~/.hermes/hermes-ad-agent/setup-state.json`): present, `schema_version` 1, absolute `workspace_root` that exists, valid `meta_backend`.
4. `skills-manifest.txt`: every listed skill exists in `<workspace>/skills/<name>/SKILL.md` (BLOCK if not) and in the Hermes skills directory (WARN if not).
5. `config.yaml` literal-secret scan: an `Authorization:` value that is not a `${VAR}` reference, a literal `Bearer EAA...` token, or any long token-like literal. Only line numbers are reported.
6. Env file (from `hermes config env-path`, else `$HERMES_HOME/.env`, plus `<workspace>/.env`): which of `META_MCP_LONG_TOKEN`, `META_MCP_TOKEN`, `META_APP_ID`, `ACCESS_TOKEN`, `AD_ACCOUNT_ID` are set (names only) and whether the file mode is 600.
7. Workspace hygiene: `BRAND.md` present, `memory/accounts` present, `.gitignore` covers `memory/`, `ad-runs/`, `research/`, `outputs/`, `.env`.
8. With `--meta-token-check <NAME>`: calls the Graph API `debug_token` and `/me/permissions` endpoints and reports token type, granted vs missing scopes (all seven the hosted Meta MCP requires), `expires_at` and `data_access_expires_at` as ISO timestamps, and days remaining. WARN under 21 days; BLOCK if expired, if a required scope is missing, or if the token checked under the MCP name is not a USER token. A SYSTEM_USER token is fine for the Meta Ads CLI route, so check it under `ACCESS_TOKEN` instead. The token itself is never printed, in any form.
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
`_meta` blocker. SETUP.md Step 4, Route A2 is the install guide. The config
entry is written with `hermes config set` / `hermes config unset` (verify the
key syntax, and whether `args` takes a JSON list, with `hermes config --help`),
never by pasting YAML:

```bash
hermes config set mcp_servers.meta_ads.command /opt/venv/bin/python
hermes config set mcp_servers.meta_ads.args '["/absolute/path/to/hermes-ad-agent/scripts/meta_mcp_bridge.py"]'
hermes config set mcp_servers.meta_ads.enabled true
hermes config set mcp_servers.meta_ads.trust untrusted
hermes config set mcp_servers.meta_ads.connect_timeout 120
hermes config unset mcp_servers.meta_ads.url
hermes config unset mcp_servers.meta_ads.headers
hermes config check
hermes mcp test meta_ads
```

Resulting shape (reference only; do not paste secrets here):

```yaml
mcp_servers:
  meta_ads:
    command: /opt/venv/bin/python
    args: ["/absolute/path/to/hermes-ad-agent/scripts/meta_mcp_bridge.py"]
    enabled: true
    trust: untrusted
    connect_timeout: 120
    # no url, no headers
```

```
python3 scripts/meta_mcp_bridge.py [--env-file PATH] [--token-var META_MCP_LONG_TOKEN]
                                   [--upstream https://mcp.facebook.com/ads]
                                   [--timeout 120] [--log-level info]
                                   [--allow-any-upstream]
```

What it does on every request:

1. Reads the bearer token from the env file **each time**, so a rotated
   token (written by `meta_token_maintenance.py`, on its weekly run or from
   the handoff line) is used on the next call with no gateway restart and no
   managed-app redeploy.
2. Strips an empty `params._meta` object, which MCP SDK 2.0 clients add and
   Meta rejects with JSON-RPC `-32602` `"meta" for Request must be an dict or
   null`. A non-empty `_meta` is preserved.
3. Passes Meta's real JSON-RPC error code and message back to Hermes instead
   of a generic error, so the next failure is diagnosable.

Env-file resolution when `--env-file` is omitted: `$META_MCP_ENV_FILE` (alias
`$META_MCP_DOTENV_PATH`), else `$HERMES_HOME/.env`, else `/data/.env`, else
`~/.hermes/.env`. On a standard Hermes install that lands on the profile env
file (`hermes config env-path`), so `--env-file` in the config `args` is
optional; add it only for a non-standard layout where the gateway's
environment does not carry `HERMES_HOME`. The upstream can likewise come from
`$META_MCP_UPSTREAM` (alias `$META_MCP_UPSTREAM_URL`) instead of `--upstream`,
and the variable name from `$META_MCP_TOKEN_VAR` instead of `--token-var`.

Variable names in the env file: the long-lived token lives on one line,
`META_MCP_LONG_TOKEN='<fully scoped USER token>'`, mode `0600`; that is the
name the bridge reads (`--token-var` overrides it for tests only).
`META_MCP_TOKEN` in the same file is the short-lived handoff line a person
fills for reauthorization and `meta_token_maintenance.py` clears; the bridge
never reads it. Existing installs that already used `META_MCP_LONG_TOKEN`
need no rename; an install that stored the long-lived token under
`META_MCP_TOKEN` renames that line to `META_MCP_LONG_TOKEN` once, and never
keeps a long-lived token under both names.

Safety properties: never writes the token anywhere (no log, no file, no
error text); redacts error text before forwarding it; refuses any upstream
that is not `https` on `facebook.com` unless started with
`--allow-any-upstream`, which is for local test servers only and never
belongs in a real config. It has no exit-code contract of its own: it runs
until Hermes closes its stdin. After configuring it, run `hermes config check`,
then `hermes mcp test meta_ads` (read the text), then confirm a fresh normal
session can find `mcp__meta_ads__ads_get_ad_accounts` with `tool_search` and
call it read-only. Because it is a project-owned file referenced by absolute
path, it survives Hermes and container updates; nothing under `/opt` is
patched.

## meta_token_maintenance.py

Deterministic token upkeep for the bridge transport, and the one sanctioned
way to reauthorize by hand. No LLM anywhere in it. Meant to run weekly as a
**script job** (no agent) on the Hermes scheduler, with the Markdown report
delivered to the user's channel; SETUP.md Step 7 covers the job and its
dry-run-first order, and `docs/meta-ads-mcp-renewal.md` is the operator
runbook (cadence, status meanings, expected no-change weeks, the human
reauthorization steps).

```
python3 scripts/meta_token_maintenance.py [--env-file PATH]
                                          [--token-var META_MCP_LONG_TOKEN] [--handoff-var META_MCP_TOKEN]
                                          [--app-id-var META_APP_ID] [--app-secret-var META_APP_SECRET]
                                          [--dry-run] [--json | --markdown] [--replace-same-expiry]
                                          [--min-days 21] [--state-file PATH] [--config-file PATH]
                                          [--no-smoke-test] [--hermes-test] [--hermes-server meta_ads]
                                          [--upstream https://mcp.facebook.com/ads] [--graph-version vNN.N]
```

Flags: `--token-var` names the long-lived line the bridge reads (default
`META_MCP_LONG_TOKEN`); `--handoff-var` names the short-lived line a person
fills for reauthorization (default `META_MCP_TOKEN`); `--upstream` is the MCP
endpoint the smoke test talks to (https only); `--graph-version` is the Graph
API version used for `debug_token` and the exchange; `--hermes-test` runs
`hermes mcp test <server>` through the bridge after a write, with
`--hermes-server` naming the server (default `meta_ads`); `--config-file`
names the Hermes config to inspect for the bridge entry (default
`$HERMES_HOME/config.yaml`), which feeds the "Bridge config valid" line;
`--markdown` and `--json` choose the report format; `--dry-run` writes nothing;
`--replace-same-expiry` also writes an equal-expiry candidate; `--min-days`
sets the warning threshold; `--state-file` overrides the state path;
`--no-smoke-test` exists for offline tests only. Env-file resolution matches
the bridge (`--env-file`, else `$META_MCP_ENV_FILE` or `$META_MCP_DOTENV_PATH`,
else `$HERMES_HOME/.env`, else `/data/.env`, else `~/.hermes/.env`).

What it does, in order:

1. Reads the env file and inspects the current long-lived token
   (`META_MCP_LONG_TOKEN`) with `debug_token` (type, scopes, expiry,
   data-access expiry). If it validates, it is the exchange input and the
   handoff line is ignored. If it is missing, invalid, or expired and the
   handoff line (`META_MCP_TOKEN`) holds a value, that short-lived USER token
   is the candidate source instead: a person put it there
   (`docs/meta-ads-mcp-renewal.md`, "Human reauthorization runbook"). Missing
   with no handoff token is `REAUTH_REQUIRED`.
2. Exchanges it with `grant_type=fb_exchange_token`, using `META_APP_ID` and
   `META_APP_SECRET` from the same env file. Without those two values the
   exchange is skipped and the run reports `NO_CHANGE` with days remaining;
   the handoff path cannot run without them.
3. Inspects the candidate: it must be a USER token carrying all seven scopes
   the hosted MCP requires, and it must belong to the configured app
   (`META_APP_ID`). A token minted by another app is `FAILED` and never
   written.
4. Classifies the result. A candidate whose expiry advanced by more than a
   day is `RENEWED` and written; an equal-expiry candidate is
   `REPLACED_SAME_EXPIRY`, written only with `--replace-same-expiry`; a
   candidate with a shorter expiry than the current token is retained and
   reported as `NO_CHANGE`; the same token back is `NO_CHANGE`.
5. On a write: atomic (temp file, fsync, rename, mode `0600`), guarded by a
   lock file and a compare-and-swap on the token line. The rewrite fails
   closed if the `META_MCP_LONG_TOKEN` line is missing or appears more than
   once; the handoff path is the one exception and may create the long-token
   line on a first install. On the handoff path the `META_MCP_TOKEN` value is
   emptied (the line stays) in a second write, after the post-write checks
   pass.
6. Smoke test: a direct MCP `initialize` plus `tools/list` against
   `--upstream` with the new token. If Meta rejected the token (HTTP `401` or
   `403`) the previous token is restored and the run is `FAILED`. On a
   transport or any other failure the validated candidate is kept, the run is
   still `FAILED`, and the report carries a note saying so: a network fault is
   not evidence against a token Meta just issued and validated. Because the
   bridge re-reads the env file per request, a passing smoke test means the
   live gateway uses the new token on its next call.
7. With `--hermes-test`, after a write: runs `hermes mcp test meta_ads`
   through the bridge (binary discovered as `command -v hermes`, then
   `/opt/venv/bin/hermes`, then `$HERMES_HOME/bin/hermes`) and parses the
   printed text, because that command's exit code is unreliable.

Outcomes, exactly. Every report has a headline and a detail. The headline is
`SUCCESS` when the detail is `RENEWED` or a written `REPLACED_SAME_EXPIRY`;
otherwise it repeats the detail:

| Headline | Detail | Meaning | Long token written? |
|---|---|---|---|
| `SUCCESS` | `RENEWED` | different token **and** expiry advanced by more than a day | yes |
| `SUCCESS` | `REPLACED_SAME_EXPIRY` | different token, expiry not advanced, written because `--replace-same-expiry` was passed | yes |
| `REPLACED_SAME_EXPIRY` | `REPLACED_SAME_EXPIRY` | different token, expiry not advanced; **not a renewal**, the old token stays valid | no (the default) |
| `NO_CHANGE` | `NO_CHANGE` | same token back, a shorter-expiry candidate (retained), or exchange skipped because the app credentials are absent | no |
| `REAUTH_REQUIRED` | `REAUTH_REQUIRED` | token missing, invalid, or expired, or Meta refused the exchange; a human fills the handoff line and re-runs | no |
| `FAILED` | `FAILED` | lock held; candidate not USER, missing a scope, or from another app; long-token line missing or duplicated; compare-and-swap mismatch; write, smoke-test, Hermes-test, or transport failure | rolled back only on a Meta `401`/`403`; otherwise the validated candidate stays |

Exit codes: `0` healthy (`SUCCESS`, or `NO_CHANGE` with days remaining at or
above `--min-days`); `1` warning (an equal-expiry candidate left unwritten, or
fewer than `--min-days` remaining); `2` `REAUTH_REQUIRED` or `FAILED`.

`--markdown` renders exactly this report, which is what the cron job
delivers (the first line is the headline described above):

```
# SUCCESS | NO_CHANGE | REAUTH_REQUIRED | FAILED
- Outcome detail: RENEWED | REPLACED_SAME_EXPIRY | NO_CHANGE | REAUTH_REQUIRED | FAILED
- Current expiry (UTC): <timestamp or unavailable>
- Candidate expiry (UTC): <timestamp or unavailable>
- Candidate differed: yes/no/unavailable
- Credential replaced: yes/no
- Expiry advanced: yes/no
- Bridge config valid: yes/no/unknown
- MCP smoke test: passed/failed/not run
- Hermes mcp test: passed/failed/not run
- Required action: <none or precise reauthorization instruction>
```

`--json` prints one JSON line carrying the same fields (plus `status_compat`,
for anything that consumed the earlier output shape) followed by the
`Outcome:` line. Without either flag the script prints a human-readable table
and then the `Outcome:` line. `--dry-run` writes nothing and is the first run
you make.

Recommended job shape (verify the flags with `hermes cron --help`):

```bash
hermes cron add --name meta-token-maintenance --schedule "0 9 * * 1" \
  --script "cd /absolute/path/to/hermes-ad-agent && python3 scripts/meta_token_maintenance.py --markdown --hermes-test" \
  --no-agent --deliver <the channel the user chats on>
```

For the first weeks on a new install add `--replace-same-expiry` to that
command so the write, smoke test, Hermes test, and delivery are proven end to
end at least once; then remove it, because rotating the string without moving
the deadline buys nothing.

State file, non-secret: `$HERMES_HOME/hermes-ad-agent/token-maintenance-state.json`
(override with `--state-file`) holding last outcome, `expires_at`,
`data_access_expires_at`, the last advancing expiry, consecutive
non-advancing runs, and days remaining.

Safety properties: never prints the token, the handoff token, or the app
secret, in any output mode or error; never writes without the lock, the
compare-and-swap, and the smoke test (`--no-smoke-test` exists for offline
tests, not for production); restores the previous token only when Meta
rejected the new one, and otherwise keeps the validated candidate and says
so; never writes under `--dry-run`; never generates a token from nothing
(`REAUTH_REQUIRED` is a human step, done through the handoff line, never in
chat). Honesty rule: Meta returned an equal-expiry token on the one observed
re-exchange, so whether re-exchange ever advances expiry is unverified. The
script reports what actually happened, a `NO_CHANGE` week is Meta's decision
rather than a skipped attempt, and the credential-expiry reminder plus the
auth-failure alert path still cover manual reauthorization.

## CI

`.github/workflows/verify.yml` runs on every push and pull request: the docs
check, the doctor in `--json` mode (exit 0 or 1 passes because CI has no
Hermes install; exit 2 fails), `py_compile` on every `.py`, the unit tests
(`python3 -m unittest discover -s tests -v`, which exercise the bridge and the
maintenance script offline), a grep for token-shaped literals (excluding the
two scripts that define the patterns), and `validate_copy.py --help`.
