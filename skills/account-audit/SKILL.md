---
name: account-audit
description: >-
  Read-only 90-day deep dive of a connected Meta ad account that writes a
  durable memory file the whole pack reuses: account structure (campaigns,
  ad sets, ads, budgets, bid strategies), settings and pixels, targeting
  patterns, the creative and copy actually running (verbatim), top and
  bottom performers over the last 90 days, and breakdown analysis (age,
  gender, placement, platform, geo), distilled into learnings the creative
  skills read before building net-new ads. Runs during onboarding
  immediately after the Meta backend is connected and before the
  brand-setup interview, and on demand any time after. Use it when the
  user says things like "audit my ad account", "deep dive my account",
  "build the account memory", "analyze how my account is structured",
  "what's running in my account?", "study my past ads", or "refresh the
  account memory". Strictly read-only on both Meta backends: it never
  creates, edits, pauses, or activates anything.
---

# Account audit

You study one connected Meta ad account for the last 90 days and write what
you learn to a memory file at the workspace root (the repo clone directory
recorded during setup): `memory/accounts/act_<ACCOUNT_ID>.md`, one file per
account. That file is the account's institutional memory: every creative,
copy, and launch skill in this pack consults it before building net-new
ads, so what you write must be accurate, sourced from the backend, and
honest about its gaps.

During onboarding this skill runs as one of the first steps: immediately
after the Meta backend is connected and before the brand-setup interview,
so brand-setup can pre-fill discovered facts (ad account, pixels,
conversion events, observed objectives) from the memory file instead of
asking the user cold. It also runs on demand whenever the user wants a
fresh look or a refresh.

Two Meta backends are supported and the workflow is the same on both: the
Meta Ads MCP server (tools named `ads_*`) or the Meta Ads CLI (Meta's
official command-line tool for the Marketing API, binary `meta`, run in
the terminal with `--output json`). Detect which one is live
(Prerequisites), say once which one you are using, then make the matching
calls from the Backend reference below.

## Hard rules

1. **Read-only, without exception.** This audit never creates, updates,
   pauses, activates, archives, or deletes an ad, ad set, campaign,
   creative, budget, bid, audience, or pixel, on either backend. It makes
   list, get, and insights reads only: no MCP `ads_create_*`,
   `ads_update_entity`, or `ads_activate_entity` calls, and no
   `meta ads ... create`, `update`, or `delete` commands on the CLI. If
   the user asks for a change mid-audit, park the request and hand it to
   the acting skill afterward (`meta-ad-launcher` for launches and status
   changes, the Arcads creative skills for new assets).
2. **Never fabricate a number.** Every metric, name, ID, and line of copy
   in the memory file came from a result the Meta tools (MCP or CLI)
   actually returned in this session. No estimates presented as
   measurements, no filled-in gaps, no invented benchmarks. If a metric is
   missing, a tool failed, or the backend has no tool for it, record
   exactly that in the file's "## Data Gaps" section.
3. **Copy is quoted verbatim.** Primary texts, headlines, descriptions,
   CTAs, and destination URLs go into the file exactly as the backend
   returned them, typos included. Paraphrase kills the point of the
   inventory.
4. **Write incrementally.** Append the memory file section by section as
   each pull completes. Never try to hold the whole account in one
   response; on a large account that loses data.
5. **Cap gracefully, and say so.** All active entities are covered first,
   then top spenders among the rest. If the account exceeds roughly 200
   ads in the 90-day window, cover the top spenders individually,
   summarize the tail in aggregate, and record the cap in "## Data Gaps".
6. **Memory files are user data, never repo data.** `memory/` at the
   workspace root is gitignored. Account IDs, audience names, pixel IDs,
   and verbatim copy live only in the memory file, never in committed
   files. Never paste an access token, or any other secret, into the
   memory file or anywhere else; the MCP handles its own auth and the CLI
   token stays in the gitignored `.env`.
7. **No Meta account, no audit.** In demo mode, or when no backend is
   connected, skip with a note explaining why and what to do next. Never
   fabricate an audit.

## Prerequisites

- **Meta backend connected.** Detect it in this order:
  1. If your live tool list contains tools named `ads_*` (for this skill:
     `ads_get_ad_accounts`, `ads_get_ad_entities`, `ads_get_creatives`,
     and `ads_insights_performance_trend`), the Meta MCP is connected: use
     the MCP backend.
  2. Otherwise, in the terminal, run `meta auth status`; if it reports a
     token, run `meta ads adaccount list --output json`. If that returns
     accounts, the Meta Ads CLI is configured: use the CLI backend. Its
     calls for this skill are `meta ads campaign|adset|ad list`,
     `meta ads <resource> get`, `meta ads creative list|get`, and
     `meta ads insights get`, always with `--output json`.
  3. If neither works, stop and tell the user Meta is not connected yet
     (the pack's SETUP.md Step 4 covers both routes).

  If both are available, prefer the MCP (creative reads, previews,
  breakdown-capable insights, custom audience listings, and activity logs
  exist only there). Say once which backend you are using. Tool names and
  availability differ between server versions; always trust your live tool
  list over the names in this file, use the closest available equivalent
  when a documented name is missing, and on the CLI trust `--help` output
  over the flags written here.
- **A workspace root.** The memory file is written under the workspace
  root (the repo clone directory recorded during setup), at
  `memory/accounts/act_<ACCOUNT_ID>.md`. Create the `memory/accounts/`
  directories if they do not exist. `memory/` is gitignored; keep it that
  way.
- **The memory template.** The canonical file structure is
  `${HERMES_SKILL_DIR}/references/memory-template.md`. Read it before
  writing; other skills parse the memory file by its exact H2 heading
  names.
- **BRAND.md is optional here.** During onboarding this skill runs before
  brand-setup, so BRAND.md usually does not exist yet; that is fine. When
  it does exist, read "## Performance Targets" for the goal metric and
  "## Meta Assets" for the expected account ID. If BRAND.md is the demo
  file (or the user is in demo mode with no real Meta connection), skip
  the audit with a note; there is no real account to study.

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
| Read campaigns / ad sets / ads | `ads_get_ad_entities` | `meta ads campaign list --output json`, `meta ads adset list --output json`, `meta ads ad list --output json` (add `--status`, `--limit`, `--fields` as needed) |
| Read one entity's full settings | `ads_get_ad_entities` (single-entity parameters) | `meta ads <resource> get <ID> --output json` (returns the entity fields plus `effective_status` and `issues_info`) |
| Read creatives and copy | `ads_get_creatives` / `ads_get_creative_ads` | `meta ads creative list --output json`, `meta ads creative get <ID> --output json` |
| Creative media inventory | `ads_get_ad_images` / `ads_get_ad_videos` | not available; describe formats from the creative fields `meta ads creative get` returns, and record the gap in Data Gaps |
| Ad preview | `ads_get_ad_preview` | not available; record in Data Gaps |
| 90-day performance | `ads_insights_performance_trend` | `meta ads insights get --date-preset last_90d --fields spend,impressions,clicks,ctr,cpc,cpm,reach,frequency,conversions,cost_per_conversion,purchase_roas --time-increment all_days --output json` (account level by default) |
| Scope to one entity | the entity parameters of `ads_insights_performance_trend` | add `--campaign-id <ID>`, `--adset-id <ID>`, or `--ad-id <ID>` to the command above |
| Per-ad ranking | the per-ad breakdown from `ads_insights_performance_trend` | check `meta ads insights get --help` for an entity-level option; if there is none, list the ads (`meta ads ad list --output json`) and call insights once per `--ad-id`, ordered with `--sort spend_descending` and capped with `--limit` |
| Breakdowns (age, gender, placement, platform, geo) | the breakdown parameters of `ads_insights_performance_trend` | add `--breakdown age`, `--breakdown gender`, `--breakdown publisher_platform`, `--breakdown platform_position`, `--breakdown device_platform`, or `--breakdown country` (repeatable) to the insights command |
| Custom audiences by name | `ads_get_ad_account_custom_audiences` / `ads_get_custom_audience` | not available; record the audience IDs the ad set targeting references and note the missing names in Data Gaps |
| Pixels and conversion events | `ads_get_datasets` / `ads_get_dataset_details` (when present in the live list) | not available as a listing; read the pixel and event each ad set promotes from `meta ads adset get <ID> --output json` |
| Account activity logs | `ads_account_get_activity_logs` | not available; record in Data Gaps |
| Delivery / rejection errors | `ads_get_errors` | `meta ads <resource> get <ID> --output json`, read `effective_status` and `issues_info` |

## Workflow

### 1. Detect the backend

Run the detection order from Prerequisites. Say once which backend you are
using, and record it later in "## Audit Metadata" as `mcp` or `cli`.

### 2. Pick the account

Enumerate ad accounts over the live backend (`ads_get_ad_accounts` on the
MCP; `meta ads adaccount list --output json` on the CLI, where
`meta ads adaccount current` shows the configured default). Show the user
the list with names and IDs and confirm which account to audit; never
assume. If the user wants several accounts audited, run this whole
workflow once per account, one file each. Then create
`memory/accounts/act_<ACCOUNT_ID>.md` from the template and write
"## Audit Metadata" and the start of "## Account Snapshot" (name, ID,
currency, timezone) immediately.

### 3. Map the structure

Pull campaigns, then ad sets, then ads, with their settings and targeting:
objective, buying type, CBO versus ABO, budgets (state amounts in the
account currency; CLI budget fields arrive in minor units, 5000 is 50.00),
bid strategies, statuses, schedules, optimization goals, billing events,
attribution settings, placements (Advantage+ or manual), special ad
categories, promoted pixel and conversion event, and the targeting spec
(geos, ages, genders, custom audiences, exclusions, detailed targeting).
Paginate with `--limit` and repeated calls (CLI) or the tools' paging
parameters (MCP). Cover all ACTIVE entities first, then the highest
90-day spenders among PAUSED and archived ones, applying the roughly 200
ad cap from the Hard rules. Also note naming conventions you observe in
campaign, ad set, and ad names. Write "## Structure Map",
"## Settings Inventory", and "## Targeting Playbook" as you go, each
section appended when its data is complete.

### 4. Inventory the creative and copy

Pull the creatives behind the ads in scope (`ads_get_creatives` /
`ads_get_creative_ads` on the MCP, plus `ads_get_ad_images` and
`ads_get_ad_videos` for the media mix; `meta ads creative list` and
`meta ads creative get <ID>` on the CLI). Record the format mix (image,
video, carousel, dynamic), the hooks and angles in use, and for the
running ads the primary texts, headlines, descriptions, CTAs, and
destination URLs, verbatim. Write "## Creative and Copy Inventory".

### 5. Pull 90 days of performance

Use the last 90 days (`--date-preset last_90d` on the CLI; the equivalent
window parameters on the MCP). Pull:

- Account-level totals and trend (spend, impressions, clicks, CTR, CPC,
  CPM, reach, frequency, conversions, cost per conversion, purchase ROAS).
- Per-campaign totals.
- Per-ad rows for the top spenders, ranked by spend and by the goal
  metric (step 6). On the CLI, if there is no entity-level option in
  `meta ads insights get --help`, call insights once per `--ad-id` for the
  capped ad list only.
- Breakdowns at account level, and for the top campaigns where volume
  justifies it: age/gender, placement (`publisher_platform` and
  `platform_position`), device platform, and geo (`country`). Where the
  backend does not support a breakdown, record that in "## Data Gaps"
  instead of skipping silently.

Write "## Top Performers" (top ads by spend AND by the goal metric, with
their winning copy verbatim and a short note on what the winners share),
"## Underperformers and Fatigue" (high-spend ads far off the account's
typical efficiency, high-frequency flags; numbers only from the backend,
never invented), and "## Breakdown Analysis" (where results over- and
under-index) as each pull completes.

### 6. Determine the goal metric

The ranking metric for winners and losers, chosen honestly:

1. If BRAND.md exists and "## Performance Targets" names a target CPA or
   target ROAS, that target's metric is the goal metric.
2. Otherwise, use the account's dominant objective over the window (the
   objective carrying the most 90-day spend) and its natural metric: cost
   per result for lead or conversion objectives, purchase ROAS where
   purchase values exist, CPC or CTR for traffic objectives.

Either way, state in the file which rule applied. A goal metric inferred
from the dominant objective is labeled as inferred, not user-confirmed,
and brand-setup should confirm it later.

### 7. Distill the learnings

Write "## Learnings for New Ads": a short do/don't list grounded in the
sections above (angles and formats that won, placements or demographics
that over-index, targeting patterns the account relies on, copy patterns
of the winners, what fatigued). Every line must trace back to data already
in the file; this section is the one the creative skills act on, so keep
it concrete. Finish the file with "## Data Gaps" (everything this backend
could not provide, plus any caps applied) and a dated "## Changelog"
entry, and complete "## Audit Metadata" and the spend and count figures in
"## Account Snapshot".

### 8. Read the summary back

Give the user a short plain-language summary: account, window, backend,
90-day spend, what is running, the top 2 to 3 performers with their
numbers, the biggest learnings, and the file path where the full memory
now lives. Do not paste the whole file into chat.

### 9. Offer a refresh

One line: the `ad-reporting-automations` skill can schedule a read-only
refresh of this audit on a cadence (monthly is a sensible default) if the
user wants it; otherwise skip. Manual refresh: the user says "refresh the
account memory" any time, which reruns this workflow and updates the same
file, replacing stale sections and appending a dated "## Changelog" entry
rather than creating a second file.

## How the pack consumes the memory file

- **brand-setup** (which runs next during onboarding) reads the file to
  pre-fill discovered facts: the ad account, pixels and conversion events
  in use, the dominant objective, and observed budget levels. The user
  still confirms everything; the audit informs the interview, it does not
  replace it.
- **The creative and copy skills** (the Arcads image and video skills,
  `human-ad-copy`, and the other ad-generation skills) read
  "## Learnings for New Ads", "## Top Performers", and
  "## Creative and Copy Inventory" before building net-new ads, so new
  creative extends what already works instead of repeating what already
  fatigued.
- **meta-ad-launcher** reads "## Structure Map" and
  "## Settings Inventory" to match the account's existing conventions
  (naming, CBO versus ABO, placements) when building new campaigns.
- Skills treat the memory file as a hint from a past session and still
  verify live state at runtime; an audit is a snapshot, not a feed.

## Pitfalls

- Do not run this audit as a pretext to change things; there is no
  mutation path in this skill at all.
- Do not summarize copy. Verbatim or absent, with absence noted.
- Do not let a big account blow the session: caps and incremental writes
  are the mechanism, and both get recorded in the file.
- Do not put account IDs, audience names, or copy into README, SETUP, a
  skill file, or any other committed file; the memory file under the
  gitignored `memory/` directory is their only home.
- Do not audit the demo brand or a disconnected setup; skip with a note.
- Do not carry numbers from memory of past sessions or from an old memory
  file into a refresh; pull fresh data every time and update the file.
- On the CLI, a section that depends on an MCP-only tool (previews, media
  inventory, custom audience names, activity logs) is recorded as a data
  gap, not silently skipped.
