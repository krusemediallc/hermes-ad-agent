---
name: meta-performance-loop
description: >-
  Answers on-demand Meta ads performance questions through whichever Meta
  backend is connected (the Meta Ads MCP insights tools or the Meta Ads
  CLI's `meta ads insights get`): pulls spend, results, CPA, ROAS, and trend
  data for a chosen window, compares the numbers against the goals in the
  user's BRAND.md, identifies the top and bottom creatives, and returns a
  readable report with 2 to 4 concrete recommendations, each mapped to an
  action another skill can execute (new creative variants, pausing a loser
  with confirmation, shifting budget with confirmation). Use it whenever the
  user asks things like "how did my ads do last 30 days?", "check my ad
  performance", "which ads are winning?", "what's my CPA this week?", "are
  my ads profitable?", "give me a performance report", or "should I kill
  any ads?". Read-only by default: it never pauses, activates, or edits
  anything itself; it hands recommended actions back to the user for
  confirmation.
---

# Meta performance loop

You answer performance questions with numbers the Meta tools (MCP or CLI)
actually returned, judged against the user's own goals, and you finish with
recommendations the user can act on in one reply. You do not change anything
on Meta from inside this skill.

Two Meta backends are supported and the workflow is the same on both: the
Meta Ads MCP server (insights tools named `ads_insights_*`) or the Meta Ads
CLI (Meta's official command-line tool for the Marketing API, binary
`meta`, run in the terminal with `--output json`). Detect which one is live
(Prerequisites), say once which one you are using, then make the matching
calls from the Backend reference below.

## Hard rules

1. **Read-only.** This skill never pauses, activates, archives, creates, or
   edits an ad, ad set, campaign, budget, bid, or audience. When a
   recommendation involves one of those actions, you present it, and it only
   happens after the user explicitly confirms; execution then follows the
   rules of the acting skill (`meta-ad-launcher` for status changes, the
   Arcads creative skills for new assets).
2. **Never fabricate a number.** Every metric in your report came from a
   result the Meta tools (MCP or CLI) actually returned in this session. No
   estimates presented as measurements, no filled-in gaps, no invented
   benchmarks. If a metric is missing, a tool failed, or the backend has no
   tool for it, say exactly that.
3. **Goals come from the user, not from you.** Judge performance against the
   targets in BRAND.md's "## Performance Targets" section (target CPA or
   target ROAS, plus the "## Budget Guardrails" daily spend cap) or
   thresholds the user states in this conversation. If neither exists,
   present the raw numbers, say you have no target to judge against, and ask
   for one. Do not silently infer a profitability goal.
4. **Name the conversion.** "Results" is ambiguous. Confirm which event
   counts as the result (purchase, lead, registration; the default
   conversion event in BRAND.md's "## Meta Assets" section is the starting
   point) and label it in the report.
   Different purchase-type events are distinct; do not merge them silently.
5. **No implied causality.** Aggregate performance ranks an ad; it does not
   prove which creative element caused the result. Phrase recommendations as
   tests, not verdicts.
6. **State the window and currency.** Every reported number carries its date
   range. Meta reports in the ad account's currency and timezone.
7. **Auth before data, and empty is not healthy.** The first call of every
   report is a connection check (the account listing must return the
   BRAND.md account by ID), and the token expiry date from BRAND.md is
   read alongside it. A zero-row insights result is "no delivery in the
   window" only after that check passed in this session; before it, the
   honest reading is "could not verify the connection". On an auth
   failure, say so, give the renewal steps, and stop; never present an
   empty table as a quiet week.

## Prerequisites

- **Meta backend connected.** Detect it in this order:
  1. If your live tool list contains tools named `ads_*` (for this skill:
     `ads_insights_performance_trend`, `ads_insights_anomaly_signal`,
     `ads_insights_advertiser_context`, and helpers like
     `ads_get_ad_entities`), the Meta MCP is connected: use the MCP backend.
  2. Otherwise, in the terminal, run `meta auth status`; if it reports a
     token, run `meta ads adaccount list --output json`. If that returns
     accounts, the Meta Ads CLI is configured: use the CLI backend. Its
     calls for this skill are `meta ads insights get`,
     `meta ads campaign|adset|ad list`, and `meta ads <resource> get`,
     always with `--output json`.
  3. If neither works, stop and tell the user Meta is not connected yet
     (the pack's SETUP.md Step 4 covers both routes).

  If both are available, prefer the MCP (anomaly signals, advertiser
  context, and benchmarks exist only there). Say once which backend you are
  using. Tool names and availability differ between server versions; always
  trust your live tool list over the names in this file, use the closest
  available equivalent when a documented name is missing, and on the CLI
  trust `--help` output over the flags written here.

  **Tool naming.** The names in this file are server-native IDs
  (`ads_insights_performance_trend`). The Hermes runtime registers them
  under prefixed callable names (observed shape
  `mcp__meta_ads__ads_insights_performance_trend`, where the middle
  segment is the server name in the Hermes config). Search your live tool
  list for the registered name and call that; do not conclude a tool is
  missing until you have looked for the prefixed form.

  **Connected but not agent-usable.** If the Meta MCP server is configured
  and reports connected (for example in `hermes mcp list`) but none of its
  tools are visible in this session, say exactly that, point the user to
  SETUP.md's verification step (a fresh session, or a tool-schema reload),
  and stop. Do not improvise a terminal workaround for anything that would
  write to Meta. Reads are a different matter: if the Meta Ads CLI is
  independently configured (Route B, detection step 2 passes), reporting
  through it is fine; say you switched and why.
- **The workspace root, from the setup-state file.** Read
  `$HERMES_HOME/hermes-ad-agent/setup-state.json` (fallback
  `~/.hermes/hermes-ad-agent/setup-state.json`) and take `workspace_root`
  (absolute). If it is missing, stop and route the user to SETUP.md rather
  than guessing where BRAND.md lives. Run every CLI command from that
  directory so `.env` is picked up.
- **Auth check and token expiry.** Before the first insights read, run the
  connection check (`ads_get_ad_accounts` on the MCP, or
  `meta auth status` plus `meta ads adaccount list --output json` on the
  CLI) and confirm the BRAND.md account appears by ID. Read the line
  `Meta token expires: YYYY-MM-DD` under "## Meta Assets" (the pack's
  read-only doctor, `python3 scripts/onboarding_doctor.py
  --meta-token-check` from the workspace root, is the second source; it
  never prints the token); if the date is within 7 days or past, open the
  report with that warning. If the check
  fails (an auth error, a 401, "Server returned an error response" on the
  listing, or the account absent), stop and report: the exact error, the
  expiry date on record, and the renewal steps (a new user token with the
  seven scopes, exchanged for a long-lived token, stored in the managed
  app environment or the file `hermes config env-path` names, app
  restarted, `hermes mcp test` for the Meta server, then the date updated
  in BRAND.md via brand-setup; SETUP.md Step 4). Never regenerate a token
  yourself and never present an empty result as a report.
- **BRAND.md** at the workspace root. Read the target CPA or target ROAS
  from its "## Performance Targets" section; the conversion event, ad
  account (name and ID), and related IDs from "## Meta Assets"; and the
  daily spend cap from "## Budget Guardrails". If the file is missing,
  offer to run the `brand-setup` skill. If the file exists but
  "## Performance Targets" is empty or all `(not set)`, offer to run
  brand-setup's update flow right now to fill in a target CPA or ROAS; you
  can still report raw numbers without it, but say the comparison-to-goal
  section is unavailable.
- **Account memory (optional).** If `memory/accounts/act_<ACCOUNT_ID>.md`
  exists at the workspace root for the account (the `account-audit` skill
  writes it), read it for the account's audited 90-day baselines and note
  the audit date; the report can then say how the current window compares
  to them. No file means no baseline comparison; do not reconstruct one
  from memory.

## Backend reference

Every Meta call this skill makes, in both forms. MCP tool names come from
your live tool list; CLI flags come from `--help` (versions differ, and when
this table and `--help` disagree, `--help` wins). Always pass
`--output json` on the CLI. In the CLI column, `<resource>` is `campaign`,
`adset`, or `ad`. For humans who want the full picture, the repo's
docs/meta-mcp.md and docs/meta-cli.md cover each backend.

| Purpose | Meta MCP tool | Meta Ads CLI command |
|---|---|---|
| List ad accounts | `ads_get_ad_accounts` | `meta ads adaccount list --output json` (configured account: `meta ads adaccount current`) |
| Read campaigns / ad sets / ads | `ads_get_ad_entities` | `meta ads campaign list --output json`, `meta ads adset list --output json`, `meta ads ad list --output json` (add `--status`, `--limit`, `--fields` as needed); single entity: `meta ads <resource> get <ID> --output json` |
| Performance over a window | `ads_insights_performance_trend` | `meta ads insights get --date-preset last_7d --fields spend,impressions,clicks,ctr,cpc,conversions,cost_per_conversion,purchase_roas --time-increment daily --output json` (account level by default) |
| Scope to one entity | the entity parameters of `ads_insights_performance_trend` | add `--campaign-id <ID>`, `--adset-id <ID>`, or `--ad-id <ID>` to the command above |
| Per-ad ranking | the per-ad breakdown from `ads_insights_performance_trend` | check `meta ads insights get --help` for an entity-level option; if there is none, list the ads (`meta ads ad list --output json`) and call insights once per `--ad-id` |
| Anomalies | `ads_insights_anomaly_signal` | not available; compare `--date-preset yesterday` against a `last_7d` daily series yourself and label it as your own comparison |
| Advertiser context | `ads_insights_advertiser_context` | not available; report the section as unavailable |
| Benchmarks | `ads_insights_industry_benchmark` / `ads_insights_auction_ranking_benchmarks` | not available; report the section as unavailable |
| Opportunity score | `ads_get_opportunity_score` | not available; report the section as unavailable |
| Delivery / rejection errors | `ads_get_errors` | `meta ads <resource> get <ID> --output json`, read `effective_status` and `issues_info` |

More `meta ads insights get` options, all from `--help`: `--date-preset`
takes `today`, `yesterday`, `last_3d`, `last_7d`, `last_14d`, `last_30d`,
`last_90d`, `this_month`, or `last_month`; `--since YYYY-MM-DD --until
YYYY-MM-DD` (always together) replaces the preset for a custom range;
`--time-increment` takes `all_days`, `daily`, `weekly`, or `monthly`;
`--fields` also accepts `reach`, `frequency`, and `cpm`; `--breakdown`
(repeatable) takes `age`, `gender`, `country`, `publisher_platform`,
`device_platform`, `platform_position`, or `impression_device`;
`--sort spend_descending` orders rows; `--limit` defaults to 50.

## Workflow

### 1. Scope the question

Run the auth check from Prerequisites first (connection, account by ID,
expiry date); nothing below happens until it passes. Then pin down four
things before pulling data:

- **Account:** from BRAND.md, by name and ID, confirmed against the
  listing the auth check returned (`ads_get_ad_accounts` on the MCP,
  `meta ads adaccount list --output json` on the CLI). When two accounts
  share a name, the ID decides. On the CLI, the `AD_ACCOUNT_ID` in the
  workspace `.env` must be that account, or pass `--ad-account-id` on each
  command.
- **Window:** what the user asked for ("last 30 days", "this week",
  "yesterday"). Default to the last 7 days when unstated, and say so. On the
  CLI, map the window to a `--date-preset` (`yesterday`, `last_7d`,
  `last_30d`, `this_month`, and so on) or to `--since YYYY-MM-DD --until
  YYYY-MM-DD` for anything the presets do not cover.
- **Level:** whole account, one campaign, one ad set, or specific ads. Use
  `ads_get_ad_entities` (MCP) or `meta ads campaign list --output json`,
  `meta ads adset list --output json`, and `meta ads ad list --output json`
  (CLI) to resolve names the user mentions into IDs and to see what is
  currently ACTIVE versus PAUSED.
- **Result metric:** the conversion event (from "## Meta Assets") and
  whether the user thinks in CPA or ROAS terms (whichever target
  "## Performance Targets" sets; otherwise ask once).

### 2. Pull the data

**MCP.** Use the insights tools, checking each one's live schema for its
actual parameters:

- `ads_insights_performance_trend`: the workhorse. Pull spend, impressions,
  clicks, results, and cost metrics over the window, at the level you scoped.
  Pull a per-ad (or per-creative) breakdown as well as the aggregate so you
  can rank top and bottom performers.
- `ads_insights_advertiser_context`: account-level context (structure,
  delivery state, recent changes). Useful for the "what changed" part of a
  report.
- `ads_insights_anomaly_signal`: unusual movements worth flagging (spend or
  cost swings). Include anything it returns that overlaps the window.
- Optional context when useful and available:
  `ads_insights_industry_benchmark` and
  `ads_insights_auction_ranking_benchmarks` for how the account compares to
  its industry, `ads_get_opportunity_score` for Meta's own suggestions
  (present these as Meta's suggestions, not your endorsement), and
  `ads_get_errors` for delivery or rejection problems that would explain a
  performance gap.

**CLI.** `meta ads insights get` is the one insights command, so the pull
looks like this:

- **Aggregate over the window:** `meta ads insights get --date-preset
  last_7d --fields spend,impressions,clicks,ctr,cpc,conversions,cost_per_conversion,purchase_roas
  --time-increment daily --output json`. It runs at account level by
  default; add `--campaign-id <ID>`, `--adset-id <ID>`, or `--ad-id <ID>` to
  scope it. `--time-increment daily` gives the day-by-day series;
  `all_days` gives one total row. Swap the preset for `--since` and
  `--until` when the user's window is not a preset.
- **Per-ad ranking:** check `meta ads insights get --help` for an
  entity-level option that returns one row per ad. If there is none, list
  the ads (`meta ads ad list --output json`) and call insights once per
  `--ad-id`, then rank the rows yourself. `--sort spend_descending` and
  `--limit` help when the account is large.
- **Anomalies:** not available on the CLI. Compare `--date-preset
  yesterday` against the `last_7d` daily series yourself, and label any
  swing you flag as your own comparison, not a Meta signal.
- **Advertiser context, benchmarks, opportunity score:** MCP only. On the
  CLI, say those sections are unavailable rather than skipping them.
- **Delivery or rejection problems:** `meta ads <resource> get <ID>
  --output json`, then read `effective_status` and `issues_info`.

Spend comes back in the ad account's currency on both backends. Keep that
separate from budgets: any budget change you later recommend is set on the
CLI in minor units (5000 is 50.00), so state the human amount in the report.

An insights call that returns no rows, an empty error string, or "Server
returned an error response" is not a quiet window until you have
distinguished the cases: re-run the connection check; if it now fails, this
is an auth failure (Prerequisites); if it passes and the entity listing
shows ACTIVE ads in the window, report the insights failure as a tool
failure; only when the check passes and no ads delivered is "no spend in
the window" the honest line. Note the MCP interop defect observed with
some SDK versions (a request rejected over its `_meta` field, surfaced only
as "Server returned an error response"): it is not a credential problem,
so do not regenerate tokens or patch Hermes; use the CLI for reads if it
is configured, or wait for the upstream fix, and say which.

When comparing two windows (for example this week versus last week), compare
efficiency metrics (CPA, ROAS, CTR), and never present volume totals from
unequal-length windows as if they were comparable.

### 3. Judge against goals

For each judged entity, compare measured CPA or ROAS against the target
from BRAND.md's "## Performance Targets" section and classify:

- **Winner:** meaningfully better than target with enough spend and results
  to matter.
- **Loser:** meaningfully worse than target with enough spend that the
  verdict is not noise.
- **Watch:** in between, or conflicting signals.
- **Insufficient data:** too little spend or too few results to judge. Say
  what "enough" means: as a default, treat spend below roughly one target
  CPA, or fewer than a handful of results, as insufficient, and tell the
  user that is the rule you applied so they can change it.

When the account memory file exists, also compare the window against its
audited baselines, labeled with the audit's date range. The baseline is
context, not a target: BRAND.md's targets stay the pass/fail bar, and the
baseline numbers came from the memory file rather than a live tool call in
this session, so label them as the audit's numbers when you cite them.

### 4. Write the report

Deliver it in this shape (also save it as a dated file under `reports/` in
the run folder when this is part of an orchestrated campaign run):

```markdown
## Meta performance: <scope>, <date range>
Backend: MCP | CLI

**Totals:** spend <amount> | <results label>: <count> | CPA <amount> (target: <target>) | ROAS <x> (target: <x>)
**Verdict vs goals:** <one plain sentence>

### Top creatives
| Ad | Spend | Results | CPA / ROAS | Status |
(best 2 to 3 rows, with the numbers that earned the ranking)

### Bottom creatives
(worst 2 to 3 rows, same columns)

### Notable
- <anomalies, delivery errors, rejected ads, benchmark context; omit if none;
  on the CLI, name the MCP-only sections as unavailable>

### Recommendations
1. ...
2. ...
```

### 5. Recommend, mapped to actions

Give 2 to 4 recommendations. Each one names the data that motivates it, and
the exact action another skill can execute so the user can just say "do
number 2":

- **Iterate on a winner:** "Ad X is your best at <CPA> over <window>.
  Recommend 3 new variants of its angle. Action: the installed Arcads image
  or video skill for the creative, then `human-ad-copy` for the copy, then
  `meta-ad-launcher` to launch them PAUSED. Generating costs Arcads credits,
  so that flow will show you a credit estimate first."
- **Pause a loser:** "Ad Y spent <amount> at <CPA>, <n>x your target.
  Recommend pausing it. Action: with your confirmation, `meta-ad-launcher`
  pauses it via the Meta backend (MCP `ads_update_entity` or CLI
  `meta ads ad update <ID> --status PAUSED`). Nothing is paused until you
  confirm."
- **Shift budget:** "Ad set Z outperforms ad set W. Recommend moving <amount>
  per day. Action: with your confirmation, the budget is updated via the
  Meta backend (MCP `ads_update_entity` or CLI
  `meta ads adset update <ID> --daily-budget <minor units>`, where 5000 is
  50.00); the new totals stay under your <cap> daily cap." Budget changes
  always require explicit confirmation and a restated number.
- **Fix a delivery problem:** "Ad Q is rejected / erroring per
  `ads_get_errors` (MCP) or its `effective_status` and `issues_info` from
  `meta ads ad get <ID> --output json` (CLI). Recommend <fix>. Action:
  rebuild or edit the creative, then relaunch PAUSED."

If the user confirms an action, hand off to the right skill; do not perform
mutations from inside this skill. The acting skill writes only through the
Meta MCP or the Meta Ads CLI; if neither can perform the action in this
session (the MCP tools not agent-usable, the CLI not configured), the
answer is "blocked until the backend is usable", never an improvised
Graph API call or a hand-built request.

After delivering the report, when the account memory file exists and the
window's results have shifted materially from its baselines (or the audit
date is months old), offer to refresh the file by running the
`account-audit` skill; it is read-only on Meta and rewrites only the memory
file. Never edit the memory file from inside this skill.

## Pitfalls

- Do not run this loop as a pretext to change things; the mutation always
  goes through a confirmation and the acting skill.
- Do not average CPAs across ads (divide total spend by total results
  instead).
- Do not judge a day-old ad as a loser; call it insufficient data and say
  when it will be worth judging.
- Do not paste raw tool JSON as the report; the user wants the readable
  version, with the raw numbers preserved accurately inside it.
- Do not carry numbers from memory of past sessions; pull fresh data every
  time.
- On the CLI, a section that depends on an MCP-only tool (anomalies,
  advertiser context, benchmarks, opportunity score) is reported as
  unavailable, not silently skipped.
- Do not report before the connection check; a report that opens with
  zeros and no auth line is the failure mode this skill exists to avoid.
- Do not read `hermes mcp list` saying "enabled" as health; it is config
  state. Agent-usable means the registered tool is in your list and a
  read-only call returned data.
- Do not pick an account by display name; identical names are common.
