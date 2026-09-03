# Meta Ads MCP: token renewal and reauthorization runbook

Operator runbook for the credential behind Meta's hosted Ads MCP when Hermes reaches it through the pack's bridge (SETUP.md Step 4, Route A2). It covers what the weekly maintenance job does, how to read its report, what a week with no change means, and the exact steps a person takes when the token has to be reissued. The long-form authentication reference is [meta-authentication.md](meta-authentication.md); the flag-by-flag script reference is `scripts/README.md`.

Two variable names live in the profile env file (the file `hermes config env-path` prints: `/data/.env` on Hostinger, `$HERMES_HOME/.env` elsewhere):

| Variable | Holds | Written by |
|---|---|---|
| `META_MCP_LONG_TOKEN` | the long-lived USER token the bridge sends to Meta on every request | the maintenance script (or a person, once, at first install) |
| `META_MCP_TOKEN` | a short-lived handoff token, present only between a person generating it and the maintenance script exchanging it | a person; cleared by the script after the exchange |

Neither value ever appears in `config.yaml`, in chat, in a cron prompt, in `BRAND.md`, or in any tracked file. Presence is checked with counts (`grep -c '^META_MCP_LONG_TOKEN=' <env-file>`), never by printing.

---

## How it works

- Hermes runs `scripts/meta_mcp_bridge.py` as a command-type MCP server named `meta_ads`. The bridge reads `META_MCP_LONG_TOKEN` from the env file **on every request** and forwards the call to `https://mcp.facebook.com/ads` with that bearer. A value that changes on disk is used on the next call: no gateway restart, no managed-app redeploy, no `/reload-mcp`. Only a change to the `meta_ads` config entry itself (the command, the args) needs a reload.
- `scripts/meta_token_maintenance.py` keeps that value fresh with no LLM anywhere in the loop. It inspects the current token with `debug_token`, asks Meta for a long-lived exchange (`fb_exchange_token`, using `META_APP_ID` and `META_APP_SECRET` from the same env file), inspects the candidate (USER type, all seven scopes, issued by the configured app), classifies the answer honestly, and only then rewrites the one line under a lock, a compare-and-swap, an atomic `0600` write, and an MCP smoke test.
- The same script is the reauthorization path: a person places a fresh short-lived token in `META_MCP_TOKEN`, and the script exchanges it, writes `META_MCP_LONG_TOKEN`, empties the handoff value, and tests the result. The handoff line is consulted only when the long-lived token is missing, invalid, or expired; while `META_MCP_LONG_TOKEN` still validates, the script exchanges that token and leaves the handoff line untouched. Nobody edits the long-lived line by hand, with one documented exception below (early replacement of a still-valid token).
- Both scripts are project-owned files in the workspace clone and use only the Python standard library.

---

## Renewal cadence

Weekly and preemptive: the exchange is attempted while the current token is still valid, not after it lapses. SETUP.md Step 7 schedules it as a script job (no agent, no prompt) with a delivery target; the typical shape, verified with `hermes cron --help`:

```bash
hermes cron add --name meta-token-maintenance --schedule "0 9 * * 1" \
  --script "cd /absolute/path/to/hermes-ad-agent && python3 scripts/meta_token_maintenance.py --markdown --hermes-test" \
  --no-agent --deliver <the channel the user chats on>
```

A long-lived user token lasts about 60 days and Meta issues no refresh token, so the weekly attempt is what gives the operator time. `--min-days` (default 21) turns an otherwise healthy run into exit code `1` once fewer than that many days remain, which is the cue to plan the human step below. Run order on a new install: `--dry-run --markdown` once by hand (writes nothing), then one live run by hand, then one run through the scheduler, and confirm the report reached the channel. Delivery is part of success; an undelivered `REAUTH_REQUIRED` is silent until the token dies.

Equal-expiry candidates are not written by default. For the first weeks on a new install, add `--replace-same-expiry` to the scheduled command so the write, smoke test, Hermes test, and delivery are exercised end to end at least once (a written `REPLACED_SAME_EXPIRY` reports as `SUCCESS`); then take the flag off, because rotating the string without moving the deadline buys nothing.

---

## Status meanings

The `--markdown` report opens with a headline, then a detail line. The headline has four values: `SUCCESS` when the detail is `RENEWED` or a written `REPLACED_SAME_EXPIRY`; `NO_CHANGE` when nothing was written, which includes an equal-expiry candidate left unwritten (the default, with `REPLACED_SAME_EXPIRY` on the detail line); otherwise `REAUTH_REQUIRED` or `FAILED`:

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

| Headline | Detail | What happened | Long token written? | Exit |
|---|---|---|---|---|
| `SUCCESS` | `RENEWED` | Meta returned a different token whose expiry is more than a day later; written and smoke-tested | yes | `0` |
| `SUCCESS` | `REPLACED_SAME_EXPIRY` | a different token string with the same expiry, written because `--replace-same-expiry` was passed | yes | `0` |
| `REPLACED_SAME_EXPIRY` | `REPLACED_SAME_EXPIRY` | a different token string with the same expiry, left unwritten (the default); the old token stays valid | no | `1` |
| `NO_CHANGE` | `NO_CHANGE` | Meta returned the same token, or a candidate with a shorter expiry (retained, never written), or the exchange was skipped because `META_APP_ID` / `META_APP_SECRET` are absent | no | `0`, or `1` under `--min-days` |
| `REAUTH_REQUIRED` | `REAUTH_REQUIRED` | the current token is missing, invalid, or expired, or Meta refused the exchange | no | `2` |
| `FAILED` | `FAILED` | the lock was held; the candidate is not a USER token, is missing a scope, or was issued by an app other than `META_APP_ID`; the `META_MCP_LONG_TOKEN` line is missing or appears twice; the compare-and-swap found the line changed underneath; or the write, smoke test, or Hermes test failed | see the rollback rule | `2` |

Exit codes: `0` healthy (`SUCCESS`, or `NO_CHANGE` with at least `--min-days` remaining); `1` warning (an equal-expiry candidate left unwritten, or any healthy outcome with fewer than `--min-days` remaining); `2` `REAUTH_REQUIRED` or `FAILED`. A monitoring channel can treat non-zero as "look at this".

**Rollback rule.** After a write, the smoke test sends a direct MCP `initialize` and `tools/list` to Meta with the new token. If Meta rejected it (HTTP `401` or `403`), the previous token is restored and the run is `FAILED`. If the failure was a transport problem or anything else, the validated candidate is kept, the run is still `FAILED`, and the report says so in the notes: a network fault is not evidence against a token Meta just issued and validated. Read the "Credential replaced" line to know which state the file is in.

**Bridge config valid** reports whether the `meta_ads` entry in the Hermes config has the command-type bridge shape (`command` and `args`, no `url`, no `headers`); `unknown` means the config could not be read from where the script ran. **Hermes mcp test** is `not run` unless `--hermes-test` was passed and a write happened; the script parses the printed text because that command's exit code is unreliable.

---

## Expected no-change behavior

A `NO_CHANGE` headline (with `NO_CHANGE` or `REPLACED_SAME_EXPIRY` on the detail line and "Credential replaced: no") is the normal weekly result and is not a skipped attempt. The script always inspects the current token and, when the app credentials are present, always asks Meta for an exchange. Meta decides what comes back: the same token, a new string with the same expiry, or a new string with a later expiry. On the one observed re-exchange Meta returned an equal-expiry token, and whether a re-exchange ever advances a long-lived user token's expiry is unverified; this pack does not claim it does.

So, week by week:

- `NO_CHANGE`, or an unwritten `REPLACED_SAME_EXPIRY`, with days remaining at or above `--min-days`: nothing to do (the unwritten case exits `1` only so a monitor can see that Meta handed back a string it chose not to keep).
- Either of those with fewer days than `--min-days`: Meta is not moving the deadline; plan the human reauthorization below before the date.
- A candidate with a shorter expiry than the current token is never written; the current token is retained and the run reports `NO_CHANGE`.
- The state file `$HERMES_HOME/hermes-ad-agent/token-maintenance-state.json` counts consecutive non-advancing runs. A climbing counter is expected, not an alarm.

The credential-expiry reminder job from `ad-reporting-automations` stays in place next to the maintenance job for exactly this reason: the reminder is the path that reaches a person when Meta never advances the expiry.

---

## Human reauthorization runbook

The script takes the handoff path whenever `META_MCP_LONG_TOKEN` is missing, invalid, or expired: that is the `REAUTH_REQUIRED` report, and a first install where the person prefers the script to do the exchange. When the old token is still valid but has to go early (the reminder says the date is close and the maintenance job has not advanced it, or the token leaked), do the one extra step under "Early replacement of a still-valid token" first, then the same five steps. Steps 1 to 3 are done by a person in a browser and a terminal; nothing goes through chat.

1. **Generate a short-lived USER token.** In the Graph API Explorer (Meta for Developers, Tools), select the **same Meta app** whose ID is in `META_APP_ID`; a token minted by any other app is rejected by the script as `FAILED`. Choose User Token and add all seven scopes: `ads_mcp_management`, `ads_read`, `ads_management`, `catalog_management`, `business_management`, `pages_show_list`, `instagram_basic`. Complete the login and consent as the Business user who holds admin or advertiser access on the ad accounts the agent manages. Do not extend or exchange it yourself; the script does that.
2. **Put it on the handoff line, within the hour.** Explorer tokens are short-lived. Open the env file in the terminal (`nano "$(hermes config env-path)"` or `vi`) and set the value of the `META_MCP_TOKEN=` line; edit the existing line if one is there (it may be empty from a previous run), otherwise add one. Never leave two `META_MCP_TOKEN` lines. Keep the file at mode `0600` (`chmod 600 "$(hermes config env-path)"`). Confirm without printing: `grep -c '^META_MCP_TOKEN=' "$(hermes config env-path)"` prints `1`.
3. **Run the maintenance script** from the workspace root:

   ```bash
   python3 scripts/meta_token_maintenance.py --markdown --hermes-test
   ```

   It exchanges the handoff token for a long-lived one, verifies the result (USER, seven scopes, same app), writes `META_MCP_LONG_TOKEN` (creating the line on a first install), clears the handoff line, smoke-tests the new token against Meta's MCP, and runs `hermes mcp test meta_ads` through the bridge. Expect `# SUCCESS` with detail `RENEWED`. No restart is needed: the bridge uses the new value on its next request. Anything else: read the "Required action" line and fix that before repeating. Two specific cases: if `META_APP_ID` / `META_APP_SECRET` are missing, the report is `REAUTH_REQUIRED` with a note that the handoff token cannot be exchanged; add them and re-run. If the run ends `FAILED` after the write because a post-write check hit a transport or bridge-configuration problem, the new long-lived token is in place and the handoff value is left as is; fix the reported problem, re-run (the script now exchanges the valid long-lived token and ignores the handoff line), and empty the handoff value in the terminal when convenient.
4. **Verify from the agent's side.** `hermes mcp test meta_ads` (read the text; the exit code is not a signal), then from a **fresh normal session** discover `mcp__meta_ads__ads_get_ad_accounts` with the tool search and call it read-only. It must return the ad accounts with names and IDs.
5. **Record and resume.** Put the new expiry date (the "Current expiry" line, date only) into `BRAND.md` through brand-setup's update flow, resume any reporting job that paused itself on the auth failure, and confirm the handoff line is empty or gone (`grep -c "^META_MCP_TOKEN='EAA" <env-file>` prints `0`).

### Early replacement of a still-valid token

The script prefers a long-lived token that still validates, so a fresh handoff token is ignored while `META_MCP_LONG_TOKEN` works. To replace a valid token early (a leak, or a deadline Meta keeps returning unchanged), the person empties the long-lived value in the terminal immediately before step 3, keeping the line: `META_MCP_LONG_TOKEN=''`. That is the one documented exception to the no-hand-edit rule, and it opens a short window in which the bridge has no token, so do it right before running the script, not the night before. The script then takes the handoff path, writes the new value onto the existing line, and reports `SUCCESS` with detail `RENEWED`. For a leak, also invalidate the old token at Meta once the new one is verified (the Access Token Debugger offers this; verify the current options on Meta's page); the old value must not survive anywhere.

If Meta is connected on the direct transport instead (Route A1, `url` plus `headers` in the config), there is no bridge to pick the change up: the person exchanges the token for a long-lived one themselves, stores it as `META_MCP_LONG_TOKEN` where the config reads it from (the managed app's environment UI or the env file), and restarts the managed app. Then steps 4 and 5.

---

## Security notes

- Only a USER token with the seven scopes authenticates the hosted MCP. Never substitute an app token (`app_id|app_secret`) or a system-user token for the MCP user token: the hosted MCP answers `401` to both, and the script refuses a non-USER candidate. The system-user token belongs to the Meta Ads CLI route and stays in the workspace `.env`.
- No secrets in `config.yaml`. The bridge entry has `command` and `args` only: no `url`, no `headers`, no token, no `${...}` placeholder. `grep -c 'Bearer EAA' "$(hermes config path)"` prints `0`.
- Keep `trust: untrusted` on the `meta_ads` entry. Meta's tool descriptions and results are remote content and must not be treated as instructions.
- Never paste a token into chat, in either direction, and never into a cron prompt, `BRAND.md`, `memory/`, the setup-state file, `ad-runs/`, or anything git tracks. If one lands in chat or a log, treat it as exposed and reauthorize.
- The env file is mode `0600`; the script writes atomically and keeps that mode; the state file holds dates and counters only. The script never prints, logs, or delivers a token or the app secret, in any output mode, including the Markdown and JSON reports.
- Never hand-edit `META_MCP_LONG_TOKEN` while the job exists. Reauthorization goes through the handoff line so the script can validate, exchange, write, and test in one guarded pass; a hand edit can race the compare-and-swap.

---

## Deployment and update note

- The bridge and the maintenance script are project-owned files under the workspace clone (`scripts/`), referenced from the Hermes config by absolute path. They survive Hermes updates and container rebuilds that replace `/opt/hermes-agent` or the virtualenv, because nothing under `/opt` is patched. After a Hermes update, run `hermes config check`, `hermes mcp test meta_ads`, and one `--dry-run --markdown` to confirm the transport and the credential are both still healthy.
- Pulling the repo updates both scripts in place. The config entry does not change unless the clone path did; if the workspace moves, update `mcp_servers.meta_ads.args` and the cron job's `--script` path, then `hermes config check` and `hermes mcp test meta_ads`.
- The interpreter named in the config (`/opt/venv/bin/python` on Hostinger; `python3` works too) only needs the standard library, Python 3.9 or later.
- The bridge resolves the env file as `--env-file`, else `$META_MCP_ENV_FILE` (alias `$META_MCP_DOTENV_PATH`), else `$HERMES_HOME/.env`, else `/data/.env`, else `~/.hermes/.env`, the upstream as `--upstream`, else `$META_MCP_UPSTREAM` (alias `$META_MCP_UPSTREAM_URL`), else `https://mcp.facebook.com/ads`, and the variable name as `--token-var`, else `$META_MCP_TOKEN_VAR`, else `META_MCP_LONG_TOKEN`. On a standard install nothing needs passing; `--env-file` in `args` is only for a layout where the gateway's environment does not carry `HERMES_HOME`.
