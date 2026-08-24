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
run in fresh agent sessions on the Hermes scheduler, pull data through the
Meta Ads MCP, and deliver a message to the user. They observe and recommend.
They never act.

## Non-negotiable rules for every job you create

1. **Read-only, forever.** A scheduled job may call insights, entity-listing,
   and diagnostic tools only. Its prompt must never instruct it to call
   `ads_activate_entity`, `ads_update_entity`, any `ads_create_*` tool, or
   any Arcads generation tool. Never let a monitoring job grow write
   permissions over time.
2. **Alerts ping, humans act.** When a job finds a problem, it delivers the
   finding plus a recommended action and tells the user to reply in chat to
   have it done with their confirmation. No automatic pausing, no automatic
   budget changes, no "corrective" anything.
3. **Never fabricate.** Job prompts must carry the rule that only numbers the
   MCP tools returned get reported, and that a failed tool call is reported
   as a failure, not papered over.
4. **Thresholds are the user's.** Every threshold in an alert job was
   confirmed by the user during setup (or came from BRAND.md and was shown to
   the user during setup). Do not invent trigger levels.

## Prerequisites

- **Meta Ads MCP connected.** Check your live tool list for
  `ads_insights_performance_trend`, `ads_get_ad_entities`, and
  `ads_get_errors`. Tool names differ between server versions; trust the
  live list and adapt the job prompts to the tools that actually exist.
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
everything in angle brackets with the confirmed values, and keep the safety
lines verbatim. Each prompt must be self-contained because the job runs in a
fresh session with no memory of this conversation.

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
the daily spend cap (its "## Budget Guardrails" section). Using the
meta-performance-loop skill and the Meta Ads MCP
insights tools (check your live tool list; ads_insights_performance_trend is
the primary tool), report on YESTERDAY (<user timezone>): total spend,
results, CPA and/or ROAS versus the BRAND.md target, top and bottom ads by
CPA with their numbers, and anything from ads_insights_anomaly_signal or
ads_get_errors. End with 1 to 3 recommendations, each phrased as "reply to
confirm and it will be done with your confirmation"; never execute any
change yourself. HARD RULES: read-only, never call ads_activate_entity,
ads_update_entity, or any ads_create_* tool; report only numbers the MCP
tools returned; if a tool fails, say so instead of guessing. If there was no
spend and no delivery yesterday, send a single short line saying so.
```

**(b) Hourly in-flight check**, schedule `every 1h` (or `0 * * * *`), name
`meta-hourly-check`, same delivery target:

```text
You are running a scheduled READ-ONLY hourly check on in-flight Meta ads.
Read BRAND.md at <path> for the ad account (its "## Meta Assets" section),
the CPA target (its "## Performance Targets" section), and the daily spend
cap (its "## Budget Guardrails" section).
First call ads_get_ad_entities (check your live tool list): if NO campaigns,
ad sets, or ads are ACTIVE, output exactly "[SILENT] no active ads" and
stop. If ads are active, check today's spend pace and running CPA via
ads_insights_performance_trend, anomalies via ads_insights_anomaly_signal,
and delivery problems via ads_get_errors. Notable means: spend pace above
<confirmed pace rule>, running CPA above <confirmed multiple> of target with
meaningful spend, a new rejection or delivery error, or an anomaly signal.
If NOTHING is notable, output exactly "[SILENT] all quiet" and nothing else.
If something IS notable, send a short alert: what happened, the numbers the
tools returned, and one recommended action the user can confirm in chat.
HARD RULES: read-only, never call ads_activate_entity, ads_update_entity, or
any ads_create_* tool; never take corrective action; report only what the
MCP tools returned.
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
sections). Check, using your live
Meta Ads MCP tool list: (1) SPEND SPIKE: today's spend so far via
ads_insights_performance_trend against the rule <confirmed rule, e.g. "over
$X by this hour" or "pacing above Nx the $cap/day cap">. (2) CPA BREACH:
running CPA over the last <24/48>h against <multiple> x the target CPA of
<target>, only when spend exceeds <floor amount>. (3) REJECTED ADS: any ad,
ad set, or campaign whose status or effective status shows rejected,
disapproved, or with issues, via ads_get_ad_entities. (4) ACCOUNT ERRORS:
anything returned by ads_get_errors. If no rule triggers, output exactly
"[SILENT] no alerts". For each triggered rule, send: which rule, the exact
numbers or errors the tools returned, and one recommended action (for
example "consider pausing ad <name>; reply to confirm and it will be done
with your confirmation"). HARD RULES: read-only, never call
ads_activate_entity, ads_update_entity, or any ads_create_* tool; never take
corrective action yourself; report only what the MCP tools returned.
```

### 4. Show the user what exists now

After creating the jobs:

1. List them with your scheduler's list action and present a table: job
   name, schedule (in the user's timezone), delivery channel, and what it
   does in one line.
2. Run the daily digest once manually with your scheduler's run-now action
   so the user sees a real example immediately and you verify the Meta tools
   work inside a scheduled session.
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
  prompts; the job reads BRAND.md and pulls fresh data at runtime.
- If a job's delivery channel is not connected, the message goes nowhere;
  verify the channel with the user and test with a manual run.
