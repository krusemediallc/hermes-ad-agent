---
name: meta-performance-loop
description: >-
  Answers on-demand Meta ads performance questions through the official Meta
  Ads MCP insights tools: pulls spend, results, CPA, ROAS, and trend data for
  a chosen window, compares the numbers against the goals in the user's
  BRAND.md, identifies the top and bottom creatives, and returns a readable
  report with 2 to 4 concrete recommendations, each mapped to an action
  another skill can execute (new creative variants, pausing a loser with
  confirmation, shifting budget with confirmation). Use it whenever the user
  asks things like "how did my ads do last 30 days?", "check my ad
  performance", "which ads are winning?", "what's my CPA this week?", "are my
  ads profitable?", "give me a performance report", or "should I kill any
  ads?". Read-only by default: it never pauses, activates, or edits anything
  itself; it hands recommended actions back to the user for confirmation.
---

# Meta performance loop

You answer performance questions with numbers the Meta Ads MCP actually
returned, judged against the user's own goals, and you finish with
recommendations the user can act on in one reply. You do not change anything
on Meta from inside this skill.

## Hard rules

1. **Read-only.** This skill never pauses, activates, archives, creates, or
   edits an ad, ad set, campaign, budget, bid, or audience. When a
   recommendation involves one of those actions, you present it, and it only
   happens after the user explicitly confirms; execution then follows the
   rules of the acting skill (`meta-ad-launcher` for status changes, the
   Arcads creative skills for new assets).
2. **Never fabricate a number.** Every metric in your report came from an MCP
   tool result in this session. No estimates presented as measurements, no
   filled-in gaps, no invented benchmarks. If a metric is missing or a tool
   failed, say exactly that.
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

## Prerequisites

- **Meta Ads MCP connected.** Check your live tool list for the insights
  tools: `ads_insights_performance_trend`, `ads_insights_anomaly_signal`,
  `ads_insights_advertiser_context`, and helpers like `ads_get_ad_entities`.
  Tool names and availability differ between server versions; always trust
  your live tool list over the names in this file, and use the closest
  available equivalent when a documented name is missing.
- **BRAND.md** at the workspace root (the repo clone directory recorded
  during setup). Read the target CPA or target ROAS from its
  "## Performance Targets" section; the conversion event, ad account, and
  related IDs from "## Meta Assets"; and the daily spend cap from
  "## Budget Guardrails". If the file is missing, offer to run the
  `brand-setup` skill. If the file exists but "## Performance Targets" is
  empty or all `(not set)`, offer to run brand-setup's update flow right now
  to fill in a target CPA or ROAS; you can still report raw numbers without
  it, but say the comparison-to-goal section is unavailable.

## Workflow

### 1. Scope the question

Pin down four things before pulling data:

- **Account:** from BRAND.md, or `ads_get_ad_accounts` if ambiguous.
- **Window:** what the user asked for ("last 30 days", "this week",
  "yesterday"). Default to the last 7 days when unstated, and say so.
- **Level:** whole account, one campaign, one ad set, or specific ads. Use
  `ads_get_ad_entities` to resolve names the user mentions into IDs and to
  see what is currently ACTIVE versus PAUSED.
- **Result metric:** the conversion event (from "## Meta Assets") and
  whether the user thinks in CPA or ROAS terms (whichever target
  "## Performance Targets" sets; otherwise ask once).

### 2. Pull the data

Use the insights tools, checking each one's live schema for its actual
parameters:

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

### 4. Write the report

Deliver it in this shape (also save it as a dated file under `reports/` in
the run folder when this is part of an orchestrated campaign run):

```markdown
## Meta performance: <scope>, <date range>

**Totals:** spend <amount> | <results label>: <count> | CPA <amount> (target: <target>) | ROAS <x> (target: <x>)
**Verdict vs goals:** <one plain sentence>

### Top creatives
| Ad | Spend | Results | CPA / ROAS | Status |
(best 2 to 3 rows, with the numbers that earned the ranking)

### Bottom creatives
(worst 2 to 3 rows, same columns)

### Notable
- <anomalies, delivery errors, rejected ads, benchmark context; omit if none>

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
  pauses it via the Meta MCP. Nothing is paused until you confirm."
- **Shift budget:** "Ad set Z outperforms ad set W. Recommend moving <amount>
  per day. Action: with your confirmation, the budget is updated via the Meta
  MCP; the new totals stay under your <cap> daily cap." Budget changes always
  require explicit confirmation and a restated number.
- **Fix a delivery problem:** "Ad Q is rejected / erroring per
  `ads_get_errors`. Recommend <fix>. Action: rebuild or edit the creative,
  then relaunch PAUSED."

If the user confirms an action, hand off to the right skill; do not perform
mutations from inside this skill.

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
