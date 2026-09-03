---
name: ad-reporting-automations
description: >-
  Sets up the recurring Meta ads reporting and alerting suite on the Hermes
  scheduler: a daily morning performance digest, an hourly in-flight check
  that stays quiet unless something notable happens, threshold alerts for
  spend spikes, CPA breaches against the BRAND.md target, rejected or
  disapproved ads, and account errors, an optional monthly account-memory
  refresh that re-runs the read-only account-audit skill, an optional
  weekly credential-expiry reminder, and, on the Meta MCP bridge transport,
  an optional weekly token maintenance script job (no LLM) that reports
  honestly whether Meta renewed the token. Every agent job resolves the
  workspace root from the setup-state file, checks the Meta connection and
  token expiry before reading data, and alerts loudly and pauses itself on
  an auth failure instead of reporting "no data". It interviews the user
  about which automations to enable, confirms thresholds, times, and
  delivery channel, creates the cron jobs with read-only prompts, then
  shows what was scheduled and how to change or remove it. Use it when the
  user says things like "set up daily reports", "send me a performance
  report every morning", "alert me if my ads spend too much", "watch my
  ads while they run", "tell me if an ad gets rejected", "remind me before
  my Meta token expires", "keep my Meta token renewed", "automate my ad
  reporting", or "schedule ad check-ins". Every job it creates is
  read-only toward Meta ads: alerts recommend actions but never execute
  them.
---

# Ad reporting automations

You set up scheduled, unattended check-ins on the user's Meta ads. The jobs
run in fresh agent sessions on the Hermes scheduler, pull data through
whichever Meta backend is connected (the Meta Ads MCP tools, or the Meta
Ads CLI, Meta's official command-line tool for the Marketing API), and
deliver a message to the user. They observe and recommend. They never act.

A scheduled job has no conversation to lean on, so it must find its own
footing every run: the workspace root from the setup-state file, an
explicit working directory, and a working, unexpired Meta connection
checked before the first data read. A job that cannot prove its
connection says so loudly; it never sends an empty report that looks like
a quiet day.

## Non-negotiable rules for every job you create

1. **Read-only, forever.** A scheduled job may call insights, entity-listing,
   and diagnostic reads only, on either backend. Its prompt must never
   instruct it to call the MCP tools `ads_activate_entity`,
   `ads_update_entity`, or any `ads_create_*`; never to run any
   `meta ads ... update` (status or budget), `create`, or `delete` command
   on the CLI; and never to call any Arcads generation tool. Never let a
   monitoring job grow write permissions over time.
2. **Alerts ping, humans act.** When a job finds a problem, it delivers the
   finding plus a recommended action and tells the user to reply in chat to
   have it done with their confirmation. No automatic pausing, no automatic
   budget changes, no "corrective" anything.
3. **Never fabricate.** Job prompts must carry the rule that only numbers the
   Meta tools (MCP or CLI) returned get reported, and that a failed tool
   call or command is reported as a failure, not papered over.
4. **Thresholds are the user's.** Every threshold in an alert job was
   confirmed by the user during setup (or came from BRAND.md and was shown to
   the user during setup). Do not invent trigger levels.
5. **Auth first, and an empty result is not "healthy".** Every job checks
   the Meta connection and the token expiry date before it reads any
   data. On an auth failure it sends a loud alert with the renewal steps
   and pauses itself; it never returns "no spend" or "no data" when the
   real answer is "could not authenticate". A zero-row result counts as a
   quiet day only after the auth check passed in that same run.
6. **Explicit workdir, resolved root.** Every job prompt names the
   absolute workspace root taken from the setup-state file at setup time
   and instructs the job to re-resolve it at run time and change into it
   before any file read or CLI command. No job depends on the scheduler's
   default directory.

## Prerequisites

- **The workspace root, from the setup-state file.** Read
  `$HERMES_HOME/hermes-ad-agent/setup-state.json` (fallback
  `~/.hermes/hermes-ad-agent/setup-state.json`) and take `workspace_root`
  (absolute). If the file is missing or the field is empty, stop and route
  the user to SETUP.md; a job created with a guessed path fails silently
  at 3 am. The file's `meta_backend` is a hint; jobs still detect live.
- **Meta backend connected.** Detect which one is live. If your live tool
  list contains tools whose names contain `ads_` (look for
  `ads_insights_performance_trend`, `ads_get_ad_entities`, and
  `ads_get_errors`), the Meta MCP is connected. Otherwise run
  `meta auth status` in the terminal; if it reports a token, run
  `meta ads adaccount list --output json`, and if that returns accounts the
  Meta Ads CLI is configured. If neither works, stop and tell the user Meta
  is not connected yet (SETUP.md Step 4 covers both routes). If both work,
  prefer the MCP. The CLI reads the jobs use are `meta ads insights get`,
  `meta ads campaign|adset|ad list`, and `meta ads <resource> get <ID>`,
  always with `--output json`. Tool names differ between MCP server
  versions and flags differ between CLI versions; trust the live tool list
  and `--help` output over what is written here, and adapt the job prompts
  to what actually exists.
- **Tool naming.** The names in this file and in the prompts are
  server-native IDs (`ads_insights_performance_trend`). The Hermes runtime
  registers them under prefixed callable names (observed shape
  `mcp__meta_ads__ads_insights_performance_trend`, where the middle
  segment is the server name in the Hermes config). Every job prompt
  therefore tells the job to discover the registered name in its own
  live tool list at run time and call that; a bare name written in a
  prompt is a label, not an address. If the server is configured but no
  such tools are visible in the job's session, the state is "connected but
  not agent-usable" and the job reports exactly that.
- **The token expiry date.** BRAND.md's "## Meta Assets" section carries
  the line `Meta token expires: YYYY-MM-DD` (written by brand-setup; on
  the CLI route with a system user token it reads `none (...)`). The
  hosted Meta MCP takes a long-lived user token that lasts about 60 days
  and comes with no refresh token, so renewal is manual and the jobs are
  the early warning. If the line is `(not set)` or missing, say so, offer
  brand-setup's update flow to record it, and create the jobs anyway with
  the expiry check reporting "expiry date unknown". The pack's read-only
  doctor, `python3 scripts/onboarding_doctor.py --meta-token-check` run
  from the workspace root, reports the token's `expires_at`, days
  remaining, and scopes without printing the token (verify its flags with
  `--help`); the jobs may use it as the second source when it is present,
  otherwise the BRAND.md date is the source. On the bridge transport the
  maintenance job's non-secret state file,
  `$HERMES_HOME/hermes-ad-agent/token-maintenance-state.json` (last
  outcome, `expires_at`, days remaining), is a third source the jobs may
  read; it holds dates and counters only, never a token.
- **The `meta-performance-loop` skill installed.** The daily digest attaches
  it so the scheduled session reports the same way an on-demand ask does.
  The optional monthly memory refresh needs the `account-audit` skill
  installed the same way.
- **BRAND.md** at the workspace root. The target CPA (or target ROAS) from
  its "## Performance Targets" section and the daily spend cap from
  "## Budget Guardrails" feed the threshold alerts, and the default
  conversion event from "## Meta Assets" defines "results". If BRAND.md is
  missing, offer to run `brand-setup` first. If it exists but
  "## Performance Targets" is empty or all `(not set)`, offer to run
  brand-setup's update flow to fill in a target before creating alert jobs,
  or ask for the numbers directly and suggest saving them to BRAND.md.
- **A scheduler.** Hermes builds typically have a built-in cron system,
  reachable as a scheduling tool in your tool list (a typical shape is a
  `cronjob` tool taking a schedule, a prompt, a name, and a delivery target;
  verify against your actual tool list first, because names and signatures
  differ between builds). Discover what scheduler capability this
  environment actually exposes before promising anything, including
  whether a job can pause itself or another job (a pause or disable action
  on the scheduler tool, or a chat command the job can invoke). Whatever
  the surface, the outcome contract is fixed: each job runs on the agreed
  schedule, in a fresh session, with the exact self-contained prompt below,
  from an explicit working directory, and delivers its output to the agreed
  channel. If no scheduler capability exists at all, say so and stop; do
  not fake recurring behavior.

## Backend reference

The reads the jobs make, in both forms. Use whichever backend the detection
rule found; on the CLI, pass `--output json` on every command. For humans
who want the full picture, the repo's `docs/meta-mcp.md` and
`docs/meta-cli.md` cover each backend end to end.

| Read | Meta MCP tool | Meta Ads CLI command |
|---|---|---|
| Connection check | `ads_get_ad_accounts` (the account named in BRAND.md must appear, by ID) | `meta auth status`, then `meta ads adaccount list --output json` |
| Campaigns, ad sets, ads (status, budget) | `ads_get_ad_entities` | `meta ads campaign list --output json`, `meta ads adset list --output json`, `meta ads ad list --output json` (add `--status`, `--limit`, `--fields` as needed); one entity: `meta ads <resource> get <ID> --output json` |
| Performance window (yesterday) | `ads_insights_performance_trend` | `meta ads insights get [--campaign-id/--adset-id/--ad-id <ID>] --date-preset yesterday --fields spend,impressions,clicks,ctr,cpc,conversions,cost_per_conversion,purchase_roas --output json`; swap the preset (`last_3d`, `last_7d`) or use `--since YYYY-MM-DD --until YYYY-MM-DD` for other windows, and add `--time-increment daily` for a daily series |
| Today's spend so far | `ads_insights_performance_trend` | `meta ads insights get --date-preset today --fields spend,conversions,cost_per_conversion --output json` |
| Anomalies | `ads_insights_anomaly_signal` | not available; compare `--date-preset yesterday` against a `--date-preset last_7d --time-increment daily` series yourself and label it as your own comparison |
| Errors and rejections | `ads_get_errors` | `meta ads <resource> get <ID> --output json`, then read `effective_status` and `issues_info` |

Per-ad ranking on the CLI: check `meta ads insights get --help` for an
entity-level option; if there is none, list the ads with
`meta ads ad list --output json` and call insights once per `--ad-id`.

## The common preamble (top of every job prompt, verbatim)

Every prompt below starts with this block. Paste it in full at the top of
each job's prompt, replacing `<workspace root>` with the absolute path from
the setup-state file and `<user timezone>` with the confirmed timezone; the
job runs in a fresh session with no memory of this conversation, so nothing
may be left implicit.

```text
PREAMBLE. (1) WORKDIR: read the setup-state file at
$HERMES_HOME/hermes-ad-agent/setup-state.json (fallback
~/.hermes/hermes-ad-agent/setup-state.json) and take workspace_root; it
should equal <workspace root>. If the file is missing or the two differ,
send an alert saying setup-state is missing or moved and stop. Change into
that directory before any file read or command; every path below is
relative to it. (2) META CONNECTION: the tool names in this prompt are
server-native IDs; search your live tool list for the registered name
(shape like mcp__<server>__ads_get_ad_accounts) and call that. If such
tools exist, call the ad-accounts listing and confirm the account from
BRAND.md "## Meta Assets" appears by ID. If none exist, run the Meta Ads
CLI from this directory (it reads .env here) with --output json on every
command: meta auth status, then meta ads adaccount list --output json. If
the MCP server is configured but its tools are not visible, report
"connected but not agent-usable" and do not attempt the CLI for that
reason unless the CLI is independently configured. (3) TOKEN EXPIRY: read
the line "Meta token expires:" under "## Meta Assets" in BRAND.md. If the
date is within 7 days or already past, include a warning at the top of
whatever you send. (4) AUTH FAILURE: if step 2 fails (auth error, 401,
"Server returned an error response" on the account listing, no accounts,
or the expected account missing), send this alert and STOP; do not
proceed to any data read and do not send "no spend" or "no data":
"AUTH FAILURE in <job name>: Meta connection failed (<exact error>). Token
expiry on record: <date or unknown>. Renewal: generate a new Meta user
token with the seven scopes (ads_mcp_management, ads_read,
ads_management, catalog_management, business_management,
pages_show_list, instagram_basic), exchange it for a long-lived token,
store it in the managed app environment or the file hermes config
env-path names, restart the managed app, run hermes mcp test for the
Meta server, then update the date in BRAND.md via brand-setup (SETUP.md
Step 4). This job is pausing itself until you reply." Then pause this
job with the scheduler's pause or disable action if one is available to
you; if none is, say in the alert that it could not pause itself and
will repeat this alert every run until fixed. (5) A response with zero
rows counts as a quiet day only after step 2 succeeded in this run.
```

## Setup flow

### 1. Ask which automations to enable

Offer the six, plainly:

1. **Daily digest**: yesterday's performance plus recommendations, every
   morning.
2. **Hourly in-flight check**: only useful while ads are actively delivering;
   quiet unless something notable happens.
3. **Threshold alerts**: spend spike, CPA breach, rejected or disapproved ad,
   account errors.
4. **Monthly account-memory refresh** (optional): re-runs the read-only
   `account-audit` skill so `memory/accounts/act_<ACCOUNT_ID>.md` at the
   workspace root stays current for the creative and copy skills.
5. **Credential expiry reminder** (optional, recommended on the MCP
   route): a weekly read-only check of the token expiry date that warns at
   21, 14, and 7 days out and every week after expiry.
6. **Token maintenance job** (optional, only when Meta is connected
   through the pack's bridge, SETUP.md Step 4 Route A2, and the env file
   holds `META_APP_ID` and `META_APP_SECRET`): a weekly **script job with
   no LLM** that runs `scripts/meta_token_maintenance.py`, re-exchanges the
   token with Meta, rewrites the env-file line only when the expiry
   actually advanced, and delivers one outcome line to the user's channel.
   It sits alongside the reminder, never instead of it: `REAUTH_REQUIRED`
   still needs a human.

The user can pick any subset. If they already have jobs from a previous
setup, list them first with your scheduler's list action so you extend
rather than duplicate.

### 2. Confirm the parameters

Collect and repeat back before creating anything:

- **Timezone and times.** Ask the user's timezone. Cron schedules evaluate on
  the server's clock, so check the server time (run `date` in the terminal)
  and convert: if the user wants 8:00 in their timezone and the server runs
  in another, shift the cron hour accordingly, and say what you did. Default
  digest time: 8:00 am user's local time.
- **Delivery channel.** Default `deliver` target: `origin`, which sends the
  result to the chat channel where the job was created (Telegram, Discord,
  Slack, email, and so on). Confirm that is where the user wants reports; a
  different connected channel can be named instead (for example `telegram`
  or `email`). Auth-failure alerts go to the same channel; ask whether a
  second channel should receive them too when the scheduler supports it.
- **Thresholds for the alert job**, each confirmed as a number:
  - Spend pace: alert when today's spend passes X times the daily cap's
    prorated pace, or an absolute amount by a given hour. Suggest a default
    from the "## Budget Guardrails" daily spend cap and let the user adjust.
  - CPA breach: alert when the running CPA over the last 24 to 48 hours
    exceeds Y times the "## Performance Targets" target (suggest 1.5x as a
    starting point; the user decides).
  - Rejections and errors: no threshold needed; any newly rejected,
    disapproved, or erroring entity alerts.
- **Scope.** Whole account by default, or specific campaigns the user names,
  always by name and ID.
- **Workdir.** Show the absolute workspace root you resolved and confirm it
  is the directory that holds BRAND.md (and `.env` on the CLI route).

### 3. Create the jobs

Create each enabled job with a clear name so the user can recognize it in
the scheduler's job list. The prompts below are templates: paste the
common preamble first, replace everything in angle brackets with the
confirmed values, and keep the safety lines verbatim. Each prompt must be
self-contained because the job runs in a fresh session with no memory of
this conversation.

**(a) Daily digest**, schedule example `0 8 * * *` (adjusted for timezone),
name `meta-daily-digest`, deliver to the confirmed channel. If your
scheduler supports attaching a skill to a job (a typical shape is a
`skill` parameter naming `meta-performance-loop`; verify against your
scheduler's actual interface first), attach the performance skill;
otherwise the prompt below stands alone:

```text
<PREAMBLE>
You are running the scheduled READ-ONLY Meta ads daily digest. Read
BRAND.md for the ad account (its "## Meta Assets" section, name and ID),
the conversion event, the CPA/ROAS target (its "## Performance Targets"
section), and the daily spend cap (its "## Budget Guardrails" section).
Using the meta-performance-loop skill, report on YESTERDAY (<user
timezone>): total spend, results, and CPA and/or ROAS versus the BRAND.md
target (MCP: ads_insights_performance_trend; CLI: meta ads insights get
--date-preset yesterday --fields
spend,impressions,clicks,ctr,cpc,conversions,cost_per_conversion,purchase_roas
--output json); top and bottom ads by CPA with their numbers (CLI: meta ads
ad list --output json, then insights once per --ad-id); anomalies (MCP:
ads_insights_anomaly_signal; CLI: none, so compare yesterday against a
--date-preset last_7d --time-increment daily series and label it your own
comparison); and delivery errors (MCP: ads_get_errors; CLI: meta ads
campaign|adset|ad get ENTITY_ID --output json, then read effective_status
and issues_info). End with 1 to 3 recommendations, each phrased as "reply
to confirm and it will be done with your confirmation"; never execute any
change yourself. HARD RULES: read-only, never call ads_activate_entity,
ads_update_entity, or any ads_create_* tool, and never run any meta ads ...
update, create, or delete command; report only what the Meta tools
returned; if a tool or command fails, say so instead of guessing. If the
connection check passed and there was no spend and no delivery yesterday,
send a single short line saying so, with the date the check passed.
```

**(b) Hourly in-flight check**, schedule `every 1h` (or `0 * * * *`), name
`meta-hourly-check`, same delivery target:

```text
<PREAMBLE>
You are running the scheduled READ-ONLY hourly check on in-flight Meta
ads. Read BRAND.md for the ad account (its "## Meta Assets" section), the
CPA target (its "## Performance Targets" section), and the daily spend
cap (its "## Budget Guardrails" section). First list the entities (MCP:
ads_get_ad_entities; CLI: meta ads campaign list, meta ads adset list, and
meta ads ad list, each with --output json): if the connection check passed
and NO campaigns, ad sets, or ads are ACTIVE, output exactly "[SILENT] no
active ads" and stop. If ads are active, check today's spend pace and
running CPA (MCP: ads_insights_performance_trend; CLI: meta ads insights
get --date-preset today --fields spend,conversions,cost_per_conversion
--output json), anomalies (MCP: ads_insights_anomaly_signal; CLI: none; if
you compare today's pace against a --date-preset last_7d --time-increment
daily series, label it your own comparison), and delivery problems (MCP:
ads_get_errors; CLI: meta ads campaign|adset|ad get ENTITY_ID --output
json, then read effective_status and issues_info). Notable means: spend
pace above <confirmed pace rule>, running CPA above <confirmed multiple>
of target with meaningful spend, a new rejection or delivery error, or an
anomaly signal. If NOTHING is notable, output exactly "[SILENT] all quiet"
and nothing else. If something IS notable, send a short alert: what
happened, the numbers the tools returned, and one recommended action the
user can confirm in chat. HARD RULES: read-only, never call
ads_activate_entity, ads_update_entity, or any ads_create_* tool, and
never run any meta ads ... update, create, or delete command; never take
corrective action; report only what the Meta tools returned. An auth
failure is never silent.
```

The `[SILENT]` prefix is a typical shape for an output-suppression marker
on Hermes builds, so quiet runs deliver nothing; the exact marker, and
whether one exists at all, differs between builds, so discover your
scheduler's actual quiet-run mechanism first. Then verify it by running the
job once manually with your scheduler's run-now action. The outcome
contract is what matters: a run that finds nothing notable must deliver
nothing (or, failing that, the shortest possible one-liner), and a run
that could not authenticate must deliver the loud alert. If your build
has no suppression mechanism, tell the user each quiet run will arrive as
a one-line "all quiet" message and let them choose a lower frequency
instead, and adjust the prompts' quiet-output lines to whatever your
scheduler actually honors.

**(c) Threshold alerts**, schedule `every 2h` by default (the user may fold
this into the hourly check instead; offer that), name `meta-threshold-alerts`:

```text
<PREAMBLE>
You are running the scheduled READ-ONLY Meta ads threshold watch. Read
BRAND.md for the ad account (its "## Meta Assets" section) and targets
(its "## Performance Targets" and "## Budget Guardrails" sections). Check:
(1) SPEND SPIKE: today's spend so far (MCP: ads_insights_performance_trend;
CLI: meta ads insights get --date-preset today --fields
spend,conversions,cost_per_conversion --output json) against the rule
<confirmed rule, e.g. "over $X by this hour" or "pacing above Nx the
$cap/day cap">. (2) CPA BREACH: running CPA over the last <24/48>h (same
tools; CLI: --date-preset yesterday or last_3d, or --since YYYY-MM-DD
--until YYYY-MM-DD to match the window) against <multiple> x the target
CPA of <target>, only when spend exceeds <floor amount>. (3) REJECTED ADS:
any ad, ad set, or campaign whose status or effective status shows
rejected, disapproved, or with issues (MCP: ads_get_ad_entities; CLI: meta
ads campaign|adset|ad list --output json, then get ENTITY_ID --output json
and read effective_status and issues_info). (4) ACCOUNT ERRORS: anything
returned by ads_get_errors (MCP only; on the CLI the issues_info from step
3 is the error source). If the connection check passed and no rule
triggers, output exactly "[SILENT] no alerts". For each triggered rule,
send: which rule, the exact numbers or errors the tools returned, and one
recommended action (for example "consider pausing ad <name>; reply to
confirm and it will be done with your confirmation"). HARD RULES:
read-only, never call ads_activate_entity, ads_update_entity, or any
ads_create_* tool, and never run any meta ads ... update, create, or
delete command; never take corrective action yourself; report only what
the Meta tools returned.
```

**(d) Monthly account-memory refresh** (optional), schedule example
`0 6 1 * *` (the 1st of each month, adjusted for timezone), name
`meta-account-memory-refresh`, same delivery target. If your scheduler
supports attaching a skill to a job (verify against your scheduler's
actual interface first, as with the digest), attach `account-audit`;
otherwise the prompt below stands alone. The one file this job writes is
the local memory file; toward Meta it is as read-only as the others:

```text
<PREAMBLE>
You are running the scheduled Meta account-memory refresh. Using the
account-audit skill, re-run the READ-ONLY 90-day account audit for the ad
account named in BRAND.md (its "## Meta Assets" section, by name and ID)
and update memory/accounts/act_<ACCOUNT_ID>.md under the workspace root.
The audit reads Meta and rewrites only that local memory file; it changes
nothing on Meta. Follow the audit's coverage rule: report its creative
coverage line (returned/requested) and label the result "audit PARTIAL"
when coverage fell below the threshold. When it finishes, send a short
summary: the audit date, the backend used, the coverage line, and the 2
or 3 biggest changes since the previous audit (the file's "## Changelog"
section lists them). HARD RULES: read-only on Meta, never call
ads_activate_entity, ads_update_entity, or any ads_create_* tool, never
run any meta ads ... update, create, or delete command, and never call
any Arcads generation tool; report only what the Meta tools returned; if
a tool or command fails, say so instead of guessing.
```

**(e) Credential expiry reminder** (optional), schedule example
`0 9 * * 1` (Mondays, adjusted for timezone), name
`meta-token-expiry-reminder`, same delivery target. This job reads one
line of BRAND.md and makes one read-only connection check; it holds no
token and never renews anything:

```text
<PREAMBLE>
You are running the scheduled READ-ONLY Meta credential expiry reminder.
Read the line "Meta token expires:" under "## Meta Assets" in BRAND.md.
If it reads "none (system user token; ...)", output exactly "[SILENT]
system user token, no scheduled expiry" and stop. If it is "(not set)" or
missing, send: "Meta token expiry date is not recorded in BRAND.md; run
brand-setup's update flow to record it (SETUP.md Step 4 explains where
the date comes from)." Otherwise compute the days until that date from
today's date. If the connection check in the preamble passed and more
than 21 days remain, output exactly "[SILENT] token ok, <n> days left". At
21, 14, and 7 days or fewer, and every run after the date has passed,
send: "Meta token expires in <n> days (<date>)" or "Meta token expired on
<date>", plus the renewal steps: generate a new Meta user token with the
seven scopes (ads_mcp_management, ads_read, ads_management,
catalog_management, business_management, pages_show_list,
instagram_basic), exchange it for a long-lived token, store it in the
managed app environment or the file hermes config env-path names, restart
the managed app, run hermes mcp test for the Meta server, then update the
date in BRAND.md via brand-setup. If scripts/onboarding_doctor.py exists
under the workspace root, run python3 scripts/onboarding_doctor.py
--meta-token-check (read-only; check --help first) and include its
token-expiry line, which never contains the token. HARD RULES: read-only;
never print, log, or request
a token value; never call ads_activate_entity, ads_update_entity, or any
ads_create_* tool; never run any meta ads ... update, create, or delete
command.
```

**(f) Token maintenance job** (optional, bridge transport only), schedule
example `0 9 * * 1` (Mondays, adjusted for timezone), name
`meta-token-maintenance`, same delivery target. This is the one job in the
suite that is **not an agent job**: it runs a deterministic script with no
LLM and no prompt, and it needs no preamble. It requires the Meta MCP
bridge (`scripts/meta_mcp_bridge.py` as the `meta_ads` command-type
server, so a rotated token is used on the next request without a restart)
and `META_APP_ID` plus `META_APP_SECRET` in the same env file as
`META_MCP_TOKEN`. Create it as a script job with a delivery target; typical
shape, verify every flag with `hermes cron --help`:

```bash
hermes cron add --name meta-token-maintenance --schedule "0 9 * * 1" \
  --script "cd <workspace root> && python3 scripts/meta_token_maintenance.py --json" \
  --no-agent --deliver <confirmed channel>
```

Before scheduling it, run the script once by hand from the workspace root
with `--dry-run --json` (writes nothing), then once live with `--json`, and
read the outcome line each time. The outcomes, exactly: `RENEWED` (new
token, expiry advanced by more than a day, written and smoke-tested),
`REPLACED_SAME_EXPIRY` (new token string, expiry not advanced; not written
unless `--replace-same-expiry`; not a renewal, the old token stays valid),
`NO_CHANGE` (same token, or exchange skipped because the app credentials
are absent), `REAUTH_REQUIRED` (token invalid or expired, or Meta refused
the exchange; a human generates a new token, SETUP.md Step 4 Route A (a)),
`FAILED` (lock held, missing scopes, compare-and-swap mismatch, write or
smoke-test failure, rolled back). Exit `0` healthy, `1` warning (unwritten
`REPLACED_SAME_EXPIRY`, or fewer than `--min-days` remaining, default 21),
`2` action needed. Its writes are atomic and guarded (lock file,
compare-and-swap on the token line, MCP `initialize` plus `tools/list`
smoke test with the new token, rollback on failure), and it never prints a
token or the app secret. Honesty note to pass on to the user: on the one
observed re-exchange Meta returned an equal-expiry token, so whether
re-exchange ever advances expiry is unverified; the script reports what
happened, and the reminder in (e) stays because the manual path still
exists. Full reference: `scripts/README.md` and
`docs/meta-authentication.md`, "Automatic renewal".

### 4. Show the user what exists now

After creating the jobs:

1. List them with your scheduler's list action and present a table: job
   name, schedule (in the user's timezone), delivery channel, workdir, and
   what it does in one line.
2. Run the daily digest once manually with your scheduler's run-now action
   so the user sees a real example immediately and you verify, inside a
   scheduled session, that the setup-state file resolves, the workdir is
   right, the registered tool names were found (or the CLI ran from the
   workdir and could see `.env`), and the connection check passed before
   any data read. A first run that reports "no data" without showing the
   connection check passed is a failed verification; fix the prompt before
   leaving. If the token maintenance job was created, run it once through
   the scheduler too and confirm the user actually received its outcome
   line on the channel; delivery is part of that job's success, because an
   undelivered `REAUTH_REQUIRED` is silent until the token dies. If it did
   not arrive, fix delivery before trusting the job.
3. Tell the user how to manage everything themselves. Hermes builds
   typically expose chat commands (a `/cron`-style command with list, edit,
   pause, resume, and remove actions), terminal equivalents, and a
   directory where past run output is saved (a typical shape is under the
   `$HERMES_HOME` cron directory). These specifics differ between builds:
   discover your scheduler's actual management commands and output location
   first, then give the user the real ones, and always offer "or just ask
   me" as the fallback for any change. Explain that after an auth-failure
   alert the job stays paused until they renew the token and resume it (or
   ask you to).
4. Remind them of the standing rule: these jobs will never touch their
   campaigns. Anything a report recommends only happens when they confirm it
   in a live conversation.

## Changing or removing automations later

When the user asks to adjust ("make the digest 7am", "stop the hourly
checks", "raise the CPA alert to 2x", "resume the digest, I renewed the
token"): list the current jobs, make the exact change with the scheduler
(edit the schedule, resume the paused job, or remove and recreate the job
with the updated prompt), and show the resulting job list. Threshold
changes mean editing the number inside the job's prompt; restate the new
threshold back to the user before saving it. Before resuming a job paused
by an auth failure, run it once manually and confirm the connection check
passes; if BRAND.md's expiry date was not updated, send the user to
brand-setup's update flow first.

## Pitfalls

- Do not create a job whose prompt could mutate Meta state; re-read rule 1
  before every job-creation call to your scheduler.
- Do not schedule in server time while telling the user their local time;
  convert and say both.
- Do not let the hourly check chatter; quiet is the default state, and a
  noisy monitor gets muted by the user and then misses the real alert.
- Do not let an auth failure be quiet either: "[SILENT]" is for verified
  quiet days, never for a failed connection check.
- Do not duplicate jobs on re-setup; list first, then extend or replace.
- Do not put credentials, tokens, or real performance numbers into job
  prompts; the job reads BRAND.md and pulls fresh data at runtime, and on
  the CLI route it reads the token from `.env` at the workspace root, never
  from the prompt. The expiry date is the only token fact a prompt may
  mention, and only by reference to BRAND.md.
- Do not write a workspace root into a prompt that you did not read from
  the setup-state file, and do not omit the workdir instruction.
- Do not hard-code registered tool names into prompts as if they were
  stable; the prompt says how to discover them.
- If a job's delivery channel is not connected, the message goes nowhere;
  verify the channel with the user and test with a manual run.
- Do not turn the token maintenance job into an agent job or give it a
  prompt; it is a script job with no LLM, and its only deliverable is the
  script's outcome line. Never edit the `META_MCP_TOKEN` line by hand while
  that job exists (it rewrites the line under a lock and a compare-and-swap),
  and never let a `REPLACED_SAME_EXPIRY` be described to the user as a
  renewal.
- Do not remove the credential expiry reminder because the maintenance job
  exists; `REAUTH_REQUIRED` still needs a human, and the reminder is the
  path that reaches them.
