---
name: ad-reporting-automations
description: >-
  Sets up the recurring Meta ads reporting and alerting suite on the Hermes
  scheduler: a daily morning performance digest, an hourly in-flight check
  that stays quiet unless something notable happens, and threshold alerts for
  spend spikes, CPA breaches against the BRAND.md target, rejected or
  disapproved ads, and account errors. It interviews the user about which
  automations to enable, confirms thresholds, times, and delivery channel,
  creates the cron jobs with read-only prompts, then shows what was scheduled
  and how to change or remove it. Use it when the user says things like "set
  up daily reports", "send me a performance report every morning", "alert me
  if my ads spend too much", "watch my ads while they run", "tell me if an ad
  gets rejected", "automate my ad reporting", or "schedule ad check-ins".
  Every job it creates is read-only: alerts recommend actions but never
  execute them.
---

# Ad reporting automations

You set up scheduled, unattended check-ins on the user's Meta ads. The jobs
run in fresh agent sessions on the Hermes scheduler, pull data through
whichever Meta backend is connected (the Meta Ads MCP tools, or the Meta
Ads CLI, Meta's official command-line tool for the Marketing API), and
deliver a message to the user. They observe and recommend. They never act.

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

## Prerequisites

- **Meta backend connected.** Detect which one is live. If your live tool
  list contains tools named `ads_*` (look for
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
- **The job can find the backend on its own.** A scheduled job runs in a
  fresh session with no memory of this conversation, so every job prompt
  below carries the detection rule. On the CLI route the credentials live
  in `.env` at the workspace root (`ACCESS_TOKEN`, `AD_ACCOUNT_ID`), and
  the job must run `meta` from that directory so the CLI can read them.
  Never copy the token into the prompt.
- **The `meta-performance-loop` skill installed.** The daily digest attaches
  it so the scheduled session reports the same way an on-demand ask does.
- **BRAND.md** at the workspace root (the repo clone directory recorded
  during setup). The target CPA (or target ROAS) from its
  "## Performance Targets" section and the daily spend cap from
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
  environment actually exposes before promising anything. Whatever the
  surface, the outcome contract is fixed: each job runs on the agreed
  schedule, in a fresh session, with the exact self-contained prompt below,
  and delivers its output to the agreed channel. If no scheduler capability
  exists at all, say so and stop; do not fake recurring behavior.

## Backend reference

The reads the jobs make, in both forms. Use whichever backend the detection
rule found; on the CLI, pass `--output json` on every command. For humans
who want the full picture, the repo's `docs/meta-mcp.md` and
`docs/meta-cli.md` cover each backend end to end.

| Read | Meta MCP tool | Meta Ads CLI command |
|---|---|---|
| Campaigns, ad sets, ads (status, budget) | `ads_get_ad_entities` | `meta ads campaign list --output json`, `meta ads adset list --output json`, `meta ads ad list --output json` (add `--status`, `--limit`, `--fields` as needed); one entity: `meta ads <resource> get <ID> --output json` |
| Performance window (yesterday) | `ads_insights_performance_trend` | `meta ads insights get [--campaign-id/--adset-id/--ad-id <ID>] --date-preset yesterday --fields spend,impressions,clicks,ctr,cpc,conversions,cost_per_conversion,purchase_roas --output json`; swap the preset (`last_3d`, `last_7d`) or use `--since YYYY-MM-DD --until YYYY-MM-DD` for other windows, and add `--time-increment daily` for a daily series |
| Today's spend so far | `ads_insights_performance_trend` | `meta ads insights get --date-preset today --fields spend,conversions,cost_per_conversion --output json` |
| Anomalies | `ads_insights_anomaly_signal` | not available; compare `--date-preset yesterday` against a `--date-preset last_7d --time-increment daily` series yourself and label it as your own comparison |
| Errors and rejections | `ads_get_errors` | `meta ads <resource> get <ID> --output json`, then read `effective_status` and `issues_info` |

Per-ad ranking on the CLI: check `meta ads insights get --help` for an
entity-level option; if there is none, list the ads with
`meta ads ad list --output json` and call insights once per `--ad-id`.

## Setup flow

### 1. Ask which automations to enable

Offer the three, plainly:

1. **Daily digest**: yesterday's performance plus recommendations, every
   morning.
2. **Hourly in-flight check**: only useful while ads are actively delivering;
   quiet unless something notable happens.
3. **Threshold alerts**: spend spike, CPA breach, rejected or disapproved ad,
   account errors.

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
  or `email`).
- **Thresholds for the alert job**, each confirmed as a number:
  - Spend pace: alert when today's spend passes X times the daily cap's
    prorated pace, or an absolute amount by a given hour. Suggest a default
    from the "## Budget Guardrails" daily spend cap and let the user adjust.
  - CPA breach: alert when the running CPA over the last 24 to 48 hours
    exceeds Y times the "## Performance Targets" target (suggest 1.5x as a
    starting point; the user decides).
  - Rejections and errors: no threshold needed; any newly rejected,
    disapproved, or erroring entity alerts.
- **Scope.** Whole account by default, or specific campaigns the user names.

### 3. Create the jobs

Create each enabled job with a clear name so the user can recognize it in
the scheduler's job list. The prompts below are templates: replace
everything in angle brackets with the confirmed values (`<workspace root>`
is the absolute path of the repo clone directory, where BRAND.md and, on
the CLI route, `.env` live), and keep the safety lines verbatim. Each
prompt must be self-contained because the job runs in a fresh session with
no memory of this conversation, including which Meta backend to use.

**(a) Daily digest**, schedule example `0 8 * * *` (adjusted for timezone),
name `meta-daily-digest`, deliver to the confirmed channel. If your
scheduler supports attaching a skill to a job (a typical shape is a
`skill` parameter naming `meta-performance-loop`; verify against your
scheduler's actual interface first), attach the performance skill;
otherwise the prompt below stands alone:

```text
You are running a scheduled READ-ONLY Meta ads report. Read BRAND.md at
<path> for the ad account and conversion event (its "## Meta Assets"
section), the CPA/ROAS target (its "## Performance Targets" section), and
the daily spend cap (its "## Budget Guardrails" section). META BACKEND: if
tools named ads_* exist in your tool list, use them; otherwise run the Meta
Ads CLI from <workspace root> (it reads .env there) with --output json on
every command. Using the meta-performance-loop skill, report on YESTERDAY
(<user timezone>): total spend, results, and CPA and/or ROAS versus the
BRAND.md target (MCP: ads_insights_performance_trend; CLI: meta ads
insights get --date-preset yesterday --fields
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
returned; if a tool or command fails, say so instead of guessing. If there
was no spend and no delivery yesterday, send a single short line saying so.
```

**(b) Hourly in-flight check**, schedule `every 1h` (or `0 * * * *`), name
`meta-hourly-check`, same delivery target:

```text
You are running a scheduled READ-ONLY hourly check on in-flight Meta ads.
Read BRAND.md at <path> for the ad account (its "## Meta Assets" section),
the CPA target (its "## Performance Targets" section), and the daily spend
cap (its "## Budget Guardrails" section). META BACKEND: if tools named
ads_* exist in your tool list, use them; otherwise run the Meta Ads CLI
from <workspace root> (it reads .env there) with --output json on every
command. First list the entities (MCP: ads_get_ad_entities; CLI: meta ads
campaign list, meta ads adset list, and meta ads ad list, each with
--output json): if NO campaigns, ad sets, or ads are ACTIVE, output exactly
"[SILENT] no active ads" and stop. If ads are active, check today's spend
pace and running CPA (MCP: ads_insights_performance_trend; CLI: meta ads
insights get --date-preset today --fields
spend,conversions,cost_per_conversion --output json), anomalies (MCP:
ads_insights_anomaly_signal; CLI: none; if you compare today's pace against
a --date-preset last_7d --time-increment daily series, label it your own
comparison), and delivery problems (MCP: ads_get_errors; CLI: meta ads
campaign|adset|ad get ENTITY_ID --output json, then read effective_status
and issues_info). Notable means: spend pace above <confirmed pace rule>,
running CPA above <confirmed multiple> of target with meaningful spend, a
new rejection or delivery error, or an anomaly signal. If NOTHING is
notable, output exactly "[SILENT] all quiet" and nothing else. If something
IS notable, send a short alert: what happened, the numbers the tools
returned, and one recommended action the user can confirm in chat. HARD
RULES: read-only, never call ads_activate_entity, ads_update_entity, or any
ads_create_* tool, and never run any meta ads ... update, create, or delete
command; never take corrective action; report only what the Meta tools
returned.
```

The `[SILENT]` prefix is a typical shape for an output-suppression marker
on Hermes builds, so quiet runs deliver nothing; the exact marker, and
whether one exists at all, differs between builds, so discover your
scheduler's actual quiet-run mechanism first. Then verify it by running the
job once manually with your scheduler's run-now action. The outcome
contract is what matters: a run that finds nothing notable must deliver
nothing (or, failing that, the shortest possible one-liner). If your build
has no suppression mechanism, tell the user each quiet run will arrive as a
one-line "all quiet" message and let them choose a lower frequency instead,
and adjust the prompts' quiet-output lines to whatever your scheduler
actually honors.

**(c) Threshold alerts**, schedule `every 2h` by default (the user may fold
this into the hourly check instead; offer that), name `meta-threshold-alerts`:

```text
You are running a scheduled READ-ONLY Meta ads threshold watch. Read
BRAND.md at <path> for the ad account (its "## Meta Assets" section) and
targets (its "## Performance Targets" and "## Budget Guardrails"
sections). META BACKEND: if tools named ads_* exist in your tool list, use
them; otherwise run the Meta Ads CLI from <workspace root> (it reads .env
there) with --output json on every command. Check: (1) SPEND SPIKE: today's
spend so far (MCP: ads_insights_performance_trend; CLI: meta ads insights
get --date-preset today --fields spend,conversions,cost_per_conversion
--output json) against the rule <confirmed rule, e.g. "over $X by this
hour" or "pacing above Nx the $cap/day cap">. (2) CPA BREACH: running CPA
over the last <24/48>h (same tools; CLI: --date-preset yesterday or
last_3d, or --since YYYY-MM-DD --until YYYY-MM-DD to match the window)
against <multiple> x the target CPA of <target>, only when spend exceeds
<floor amount>. (3) REJECTED ADS: any ad, ad set, or campaign whose status
or effective status shows rejected, disapproved, or with issues (MCP:
ads_get_ad_entities; CLI: meta ads campaign|adset|ad list --output json,
then get ENTITY_ID --output json and read effective_status and
issues_info). (4) ACCOUNT ERRORS: anything returned by ads_get_errors (MCP
only; on the CLI the issues_info from step 3 is the error source). If no
rule triggers, output exactly "[SILENT] no alerts". For each triggered
rule, send: which rule, the exact numbers or errors the tools returned, and
one recommended action (for example "consider pausing ad <name>; reply to
confirm and it will be done with your confirmation"). HARD RULES:
read-only, never call ads_activate_entity, ads_update_entity, or any
ads_create_* tool, and never run any meta ads ... update, create, or delete
command; never take corrective action yourself; report only what the Meta
tools returned.
```

### 4. Show the user what exists now

After creating the jobs:

1. List them with your scheduler's list action and present a table: job
   name, schedule (in the user's timezone), delivery channel, and what it
   does in one line.
2. Run the daily digest once manually with your scheduler's run-now action
   so the user sees a real example immediately and you verify the Meta
   backend works inside a scheduled session (on the CLI route this also
   proves the job's shell can see `.env`).
3. Tell the user how to manage everything themselves. Hermes builds
   typically expose chat commands (a `/cron`-style command with list, edit,
   pause, resume, and remove actions), terminal equivalents, and a
   directory where past run output is saved (a typical shape is under a
   `~/.hermes` cron directory). These specifics differ between builds:
   discover your scheduler's actual management commands and output location
   first, then give the user the real ones, and always offer "or just ask
   me" as the fallback for any change.
4. Remind them of the standing rule: these jobs will never touch their
   campaigns. Anything a report recommends only happens when they confirm it
   in a live conversation.

## Changing or removing automations later

When the user asks to adjust ("make the digest 7am", "stop the hourly
checks", "raise the CPA alert to 2x"): list the current jobs, make the exact
change with the scheduler (edit the schedule, or remove and recreate the job
with the updated prompt), and show the resulting job list. Threshold changes
mean editing the number inside the job's prompt; restate the new threshold
back to the user before saving it.

## Pitfalls

- Do not create a job whose prompt could mutate Meta state; re-read rule 1
  before every job-creation call to your scheduler.
- Do not schedule in server time while telling the user their local time;
  convert and say both.
- Do not let the hourly check chatter; quiet is the default state, and a
  noisy monitor gets muted by the user and then misses the real alert.
- Do not duplicate jobs on re-setup; list first, then extend or replace.
- Do not put credentials, tokens, or real performance numbers into job
  prompts; the job reads BRAND.md and pulls fresh data at runtime, and on
  the CLI route it reads the token from `.env` at the workspace root, never
  from the prompt.
- If a job's delivery channel is not connected, the message goes nowhere;
  verify the channel with the user and test with a manual run.
