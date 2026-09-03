---
name: account-audit
description: >-
  Read-only 90-day deep dive of a connected Meta ad account that writes a
  durable memory file the whole pack reuses: account structure (campaigns,
  ad sets, ads, budgets, bid strategies), exact settings capture (raw
  targeting objects, effective placements, attribution, tracking, and
  creative specs including Advantage+ enhancement enrollment) written as
  rebuild specs the launcher can mirror, settings and pixels, targeting
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
you learn to a memory file at the workspace root (resolved from the setup
state file, see Prerequisites): `memory/accounts/act_<ACCOUNT_ID>.md`, one
file per account. That file is the account's institutional memory: every
creative, copy, and launch skill in this pack consults it before building
net-new ads, so what you write must be accurate, sourced from the backend,
and honest about its gaps. An audit that quietly analyzed nothing is worse
than no audit: coverage is measured and reported before any conclusion is
drawn.

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
   `meta ads ... create`, `update`, or `delete` commands on the CLI. When
   the rebuild-specs step reads the Graph API directly (Tier A), it issues
   GET requests only; never a POST or DELETE. If
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
   token stays in the gitignored `.env`. The Route B token used for Tier A
   reads is read from the workspace-root `.env` inside the command
   (`source .env`, then `$ACCESS_TOKEN`) and must never be echoed, logged,
   or pasted into chat, memory files, snapshot files, or job prompts. The
   `specs/` snapshot files sit under `memory/` and are user data too.
7. **No Meta account, no audit.** In demo mode, or when no backend is
   connected, skip with a note explaining why and what to do next. Never
   fabricate an audit.
8. **Coverage before conclusions.** No copy pattern, hook, angle, or
   creative-format insight is written or spoken until the coverage table
   (Workflow step 5) shows what fraction of the in-scope creatives were
   actually returned. Zero or partial coverage is reported as exactly
   that; "audit complete" is blocked until the coverage thresholds pass or
   the user explicitly accepts the gap in this conversation. A summary
   that implies copy coverage it does not have is a fabrication under rule
   2.
9. **Large responses are handled, never dumped.** Request only the fields
   a step needs, page incrementally, and never print a raw payload over
   about 1 MB into chat, a file, or a job log. Signed media URLs (image
   and video links with query-string signatures) are opaque values: never
   place them in terminal arguments, memory files, or snapshot files;
   store the media ID or hash instead and fetch the URL fresh when needed.

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

  **Tool naming.** The names in this file are the server-native IDs the
  Meta MCP advertises (`ads_get_ad_accounts`, `ads_get_creatives`). The
  Hermes runtime registers them under a prefixed callable name (observed
  shape `mcp__meta_ads__ads_get_ad_accounts`, where the middle segment is
  the server name from your config). Discover the live registered name
  with your tool search and call that; a bare name that is not in your
  tool list is not a missing capability until you have searched for the
  prefixed form. If the server is configured and connected but none of
  its tools are visible in this session, the state is "connected but not
  agent-usable": say so, point to SETUP.md, and stop.
- **A workspace root, from the setup-state file.** Read
  `$HERMES_HOME/hermes-ad-agent/setup-state.json` (fallback
  `~/.hermes/hermes-ad-agent/setup-state.json`) and take `workspace_root`
  from it; it is an absolute path. If the file is missing or the field is
  empty, stop and route the user to SETUP.md; never infer the root from
  the conversation or the current directory. The memory file is written
  under that root at `memory/accounts/act_<ACCOUNT_ID>.md`. Create the
  `memory/accounts/` directories if they do not exist. `memory/` is
  gitignored; keep it that way. The setup-state file also carries
  `meta_backend`; treat it as a hint and still run live detection.
- **The memory template.** The canonical file structure is
  `${HERMES_SKILL_DIR}/references/memory-template.md`. Read it before
  writing; other skills parse the memory file by its exact H2 heading
  names.
- **The rebuild field reference.**
  `${HERMES_SKILL_DIR}/references/rebuild-fields.md` holds the three read
  tiers, the snapshot layout, the exact per-entity field lists, the
  targeting keys and read-only echoes, the creative enhancement feature
  list, the capability matrix, and the MCP normalization rules. Read it
  before the rebuild-specs step and request exactly the fields it lists.
- **Route B token (optional, upgrades the audit).** If the workspace-root
  `.env` contains `ACCESS_TOKEN` (SETUP.md Step 4, Route B), the
  rebuild-specs step can read the Graph API directly (Tier A), which is the
  only way to read creative enhancement enrollment, ad set attribution, and
  frequency settings. Check for it with a test that does not print the
  value (for example `grep -q '^ACCESS_TOKEN=' .env`). Without it, the
  step runs on the CLI (Tier B) or the MCP (Tier C) and records the gaps.
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
| Rebuild specs: campaigns (raw fields) | `ads_get_ad_entities` at the `campaign` level with `fields` set to the campaign attributes the MCP supports (Tier C, partial: no `special_ad_categories`) | `meta ads campaign get <ID> --fields <campaign field list from references/rebuild-fields.md> --output json` (Tier B) |
| Rebuild specs: ad sets (raw `targeting`, `promoted_object`, delivery) | `ads_get_ad_entities` at the `adset` level with `fields` set to the ad set attributes the MCP supports (Tier C, partial: no `attribution_spec`, `frequency_control_specs`, `bid_constraints`, `adset_schedule`, `is_dynamic_creative`, `dsa_*`) | `meta ads adset get <ID> --fields <ad set field list from references/rebuild-fields.md> --output json` (Tier B) |
| Rebuild specs: ads (creative link, `tracking_specs`, `conversion_domain`) | `ads_get_ad_entities` at the `ad` level with `fields` set to the ad attributes the MCP supports (Tier C, partial: `creative_id` and `conversion_domain` only; no `tracking_specs` or `adlabels`) | `meta ads ad get <ID> --fields <ad field list from references/rebuild-fields.md> --output json` (Tier B) |
| Rebuild specs: creatives (`object_story_spec`, `asset_feed_spec`, `degrees_of_freedom_spec`, `url_tags`) | `ads_get_creatives` with `creative_ids` (Tier C, partial: flattened copy fields only; no enhancement enrollment or multi-variant spec) | `meta ads creative get <ID> --output json` (Tier B; whether it returns `degrees_of_freedom_spec` and `asset_feed_spec` is UNVERIFIED, so prefer Tier A for creatives) |

**Tier A (Graph API direct read)** applies on either backend when the
workspace-root `.env` holds the Route B `ACCESS_TOKEN`, and is the
highest-fidelity read for every entity above. Template, run from the
workspace root, GET only:

```
source .env
curl -s "https://graph.facebook.com/v25.0/<ENTITY_ID>?fields=<field list from references/rebuild-fields.md>&access_token=$ACCESS_TOKEN"
```

Entity IDs come from the list calls in the table; Tier A reads each one by
ID. The token is read from `.env` inside the command and must never be
echoed, logged, or pasted into chat, memory files, or job prompts. Tier A
is GET only; the Graph API is never a write path in this pack.

## Response handling (MCP)

The Meta MCP's responses do not always have the shape a tool description
implies, and a collector that assumes a key silently collects nothing.
Apply these rules to every MCP read in this skill:

- **Read the live key shape before collecting.** Inspect the first
  response of each tool and note the actual top-level keys of
  `structuredContent` (and of the text content when `structuredContent`
  is absent). Observed on one server version: `ads_get_creatives`
  returned its records under `ad_creatives`, not `creatives`, and
  `ads_get_ad_entities` returned `ad_entities`. Keys drift between server
  versions, so read them each session; never hard-code one from this
  file. Record the keys you used in "## Audit Metadata".
- **Normalize stringified JSON.** `structuredContent` values are sometimes
  JSON-encoded strings rather than objects (an `ad_entities` string, or
  an error field holding the text `"[]"`). Before reading a field, if the
  value is a string that starts with `[` or `{`, parse it; treat a parsed
  empty array as zero records, not as success.
- **Paginate and batch by the documented limits.** Use the tool's paging
  parameters (cursor, offset, or page size as its live schema names them)
  and request creatives in batches of IDs sized to the schema's stated
  maximum (verify with the tool's live description; if it states none,
  start at 25 and stay there). Continue until the paging cursor is
  exhausted, and record how many pages you pulled.
- **Retry only the failed batch.** When one batch fails (a transport
  error, an empty error string, a decode error), retry that batch once
  after a short pause, then mark those IDs `inaccessible` and move on.
  Never restart the whole collection and never re-request batches that
  already returned records.
- **Large payloads.** Field-minimize every request (pass the `fields`
  parameter where the schema offers it). If a response fails to decode
  (Brotli or similar decode errors have been observed on large creative
  reads), shrink the batch and retry that batch; where you control the
  HTTP client (Tier A only), send `Accept-Encoding: identity`. Never print
  a raw payload over about 1 MB anywhere; write records to the snapshot
  files incrementally instead.
- **Redact before printing.** Anything you show in chat is a field-minimized
  excerpt: names, IDs, copy, and numbers, never raw objects with signed
  URLs, tokens, or user identifiers.

## Workflow

### 1. Detect the backend

Run the detection order from Prerequisites. Say once which backend you are
using, and record it later in "## Audit Metadata" as `mcp` or `cli`.

### 2. Pick the account

Enumerate ad accounts over the live backend (`ads_get_ad_accounts` on the
MCP; `meta ads adaccount list --output json` on the CLI, where
`meta ads adaccount current` shows the configured default). Show the user
the list with names AND IDs and confirm which account to audit by both;
never assume, and never select by display name alone. Businesses often
hold several accounts with identical names, so when two rows share a
name, show the IDs side by side and ask the user to pick by ID, then
restate "auditing <name> (<act_ID>)" before the first read. If BRAND.md
exists, compare the pick against its "## Meta Assets" account ID and flag
a mismatch. If the user wants several accounts audited, run this whole
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

"## Settings Inventory" records, beyond the grouped optimization goals and
billing events:

- **Effective placements** per ad set: the `effective_publisher_platforms`,
  `effective_facebook_positions`, `effective_instagram_positions`,
  `effective_messenger_positions`, `effective_audience_network_positions`,
  `effective_threads_positions`, and `effective_device_platforms` echoes
  the read returns, which show where "Advantage+ placements" actually
  resolved to. Record them; they are read-only and never written back.
- **Attribution windows** per ad set: `attribution_spec` on Tier A or B;
  on Tier C only `learning_stage_info.attribution_windows` (for example
  `["7d_click", "1d_view"]`), labeled as an observation.
- **Enhancement enrollment** per top creative: one line per feature key in
  `degrees_of_freedom_spec.creative_features_spec` with its
  `enroll_status` (`OPT_IN` or `OPT_OUT`), and `default` for features the
  read did not return (a missing key is a platform default, never an
  opt-out). On Tier C this summary cannot be produced; write "not readable
  on this tier" and point to Data Gaps.
- **Publishing identities, cross-checked.** Record the Facebook Page and
  the Instagram identity the account actually publishes under, from
  three sources, and say which agreed: (1) the Page list
  (`ads_get_ad_account_pages` / `ads_get_user_pages` on the MCP,
  `meta ads page list --output json` on the CLI); (2) the Instagram
  listing (`ads_get_ig_accounts` on the MCP; none on the CLI); (3) the
  effective Instagram fields on historical creatives
  (`object_story_spec.instagram_actor_id`, `instagram_user_id`,
  `effective_instagram_media_id`, `effective_instagram_story_id`, or
  whichever of these the read returns). An empty `ads_get_ig_accounts`
  result is not proof that no Instagram identity exists: the listing
  depends on the token's scopes and the Page linkage, and accounts have
  run Instagram placements for months with that list empty. When (2) is
  empty but (3) names an identity, record the identity from (3) as
  "observed on creatives, not listed by the IG tool" so the launcher can
  reuse it; when all three are empty, record "no Instagram identity
  observed" and note it in Data Gaps.

### 4. Capture rebuild specs

This step turns the structure map into exact, reusable specs: the raw API
objects behind every campaign, ad set, ad, and creative in scope, stored
next to the memory file so `meta-ad-launcher` can mirror an existing
entity field for field. Read `references/rebuild-fields.md` first; it is
the only source for field names, tiers, and normalization rules here. Do
not add fields it does not list.

1. **Choose the read tier**, in this order, and say once which one you
   are using:
   - **Tier A (Graph direct read)** if the workspace-root `.env` contains
     the Route B `ACCESS_TOKEN` (test its presence without printing it).
     Use the Tier A template from the Backend reference, GET only. Tier A
     is used even when the MCP is the primary backend for everything else;
     it is the only tier that reads creative enhancement enrollment.
   - **Tier B (CLI `get --fields`)** otherwise, if the Meta Ads CLI is live
     (`meta auth status` reports a token). Creatives via
     `meta ads creative get <ID> --output json`; if that response lacks
     `degrees_of_freedom_spec` or `asset_feed_spec`, record the gap (their
     presence on the CLI is UNVERIFIED).
   - **Tier C (MCP)** otherwise: `ads_get_ad_entities` with `fields` at
     the `campaign`, `adset`, and `ad` levels, and `ads_get_creatives`
     with `creative_ids`.
2. **Pull the exact field lists** from `references/rebuild-fields.md`
   section 3 for campaigns, ad sets, ads, and creatives (on Tier C, the
   subset the capability matrix in section 4 marks as readable). Scope:
   all ACTIVE entities first, then the top 90-day spenders among the rest,
   under the same roughly 200-ad cap as the structure map. Read each ad's
   `creative.id` (or `creative_id` on the MCP) and capture that creative
   separately by id.
3. **Write the snapshot files** under the workspace root, one JSON object
   per line, fields exactly as returned, plus `_captured_via` (`graph`,
   `cli`, or `mcp`) and `_captured_at` (ISO date):
   - `memory/accounts/act_<ACCOUNT_ID>/specs/campaigns.jsonl`
   - `memory/accounts/act_<ACCOUNT_ID>/specs/adsets.jsonl`
   - `memory/accounts/act_<ACCOUNT_ID>/specs/ads.jsonl`
   - `memory/accounts/act_<ACCOUNT_ID>/specs/creatives.jsonl`
   Write incrementally, one line as each entity's read completes. On a
   refresh, replace the files rather than appending duplicates.
4. **Build `specs/index.json`**: a map from every captured id to its
   name, entity type, parent ids (`campaign_id`, `adset_id`), status,
   `effective_status`, and 90-day spend (from step 6 once pulled; write
   the index after the performance pull, or write it now and update the
   spend values then).
5. **Normalize Tier C reads** per `references/rebuild-fields.md` section
   5 before storing: index-keyed objects back to arrays, currency strings
   kept alongside their integer minor-unit values, bid strategy labels
   mapped to enums (unknown labels kept and marked UNVERIFIED), and
   `learning_stage_info.attribution_windows` recorded as an observation.
   Note in the memory file which normalizations were applied. Tier A and
   B snapshots are stored as returned.
6. **Record per-tier gaps** in "## Data Gaps" and in "## Rebuild Specs":
   - Tier A: none expected; name any field the API omitted.
   - Tier B: creative `degrees_of_freedom_spec` and `asset_feed_spec` if
     the CLI did not return them.
   - Tier C (MCP-only setups): creative enhancement enrollment
     (`degrees_of_freedom_spec`), `asset_feed_spec`, `object_story_spec`
     as a raw object, `url_tags`, ad set `attribution_spec`,
     `frequency_control_specs`, `bid_constraints`, `adset_schedule`,
     `is_dynamic_creative`, `dsa_beneficiary`, `dsa_payor`, ad
     `tracking_specs`, and campaign `special_ad_categories` cannot be
     read. State plainly that adding the Route B token (SETUP.md Step 4,
     Route B) upgrades the audit to full fidelity, and never guess a
     missing field.

Write "## Rebuild Specs" in the memory file: tier used, snapshot paths,
entity counts per file, normalizations applied, the per-creative
enhancement enrollment summary for the top creatives, and the fields
unavailable on this tier.

### 5. Inventory the creative and copy (coverage first)

This step is fail-closed. It has three parts in a fixed order: collect,
measure coverage, and only then analyze.

**5a. Collect.** Build the list of creative IDs referenced by the ads in
scope (each ad's `creative.id`, or `creative_id` on the MCP), de-duplicate
it, and record the count as `requested`. Pull those creatives
(`ads_get_creatives` with the ID batches, `ads_get_creative_ads` where you
need the reverse mapping, plus `ads_get_ad_images` and `ads_get_ad_videos`
for the media mix on the MCP; `meta ads creative list` and
`meta ads creative get <ID>` on the CLI), following every rule in
"Response handling": read the live key shape first (observed:
`ad_creatives`), normalize stringified JSON, batch by the documented
limit, retry only failed batches. Write each record to
`specs/creatives.jsonl` as it arrives.

**5b. Measure coverage.** Before reading a single line of copy, produce
this table in chat and write it into "## Creative and Copy Inventory" as
its first block:

| Count | Meaning |
|---|---|
| requested | distinct creative IDs referenced by in-scope ads |
| returned | records actually received with a matching ID |
| missing | requested IDs absent from every response with no error |
| inaccessible | IDs whose batch errored after the retry, or that the backend reported as unreadable |
| duplicate | IDs returned more than once (paging overlap), counted once in `returned` |

`requested` must equal `returned + missing + inaccessible`; if it does
not, your collector is reading the wrong key, so go back to 5a. Then
apply the thresholds:

- **Returned is zero:** write "coverage: 0 of <requested>; no copy or
  creative analysis possible" in the section, list the likely cause (a
  key-shape mismatch is the first suspect, then scopes, then the tier),
  and skip 5c entirely. The section contains the table and nothing else.
- **Returned is below 90 percent of requested** (default threshold; the
  user may set another and you record it): 5c may proceed on the returned
  records only, every finding in the section is prefixed "partial
  coverage (<returned>/<requested>)", and "audit complete" is blocked
  (step 9) until the user explicitly accepts the gap or a rerun raises
  coverage.
- **Returned is at or above the threshold:** proceed to 5c; still list
  the missing and inaccessible IDs in "## Data Gaps".

Write the same figures into "## Audit Metadata" (`creative coverage:
<returned>/<requested>, missing <n>, inaccessible <n>, duplicate <n>,
threshold <pct>, accepted-by-user: yes|no`).

**5c. Analyze.** Only now record the format mix (image, video, carousel,
dynamic), the hooks and angles in use, and for the running ads the
primary texts, headlines, descriptions, CTAs, and destination URLs,
verbatim, each tied to its creative ID. Multi-variant creatives
(`asset_feed_spec` with several `bodies`, `titles`, or `descriptions`)
are one creative with every variant listed under it, never split into
several ads. Every sentence of pattern analysis ("winners open with a
question", "the account leans on UGC video") must be traceable to
specific returned creative IDs; a claim with no traceable records is
removed, not softened.

### 6. Pull 90 days of performance

Use the last 90 days (`--date-preset last_90d` on the CLI; the equivalent
window parameters on the MCP). Pull:

- Account-level totals and trend (spend, impressions, clicks, CTR, CPC,
  CPM, reach, frequency, conversions, cost per conversion, purchase ROAS).
- Per-campaign totals.
- Per-ad rows for the top spenders, ranked by spend and by the goal
  metric (step 7). On the CLI, if there is no entity-level option in
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
under-index) as each pull completes. Fill the 90-day spend values in
`specs/index.json` from the per-entity rows now.

### 7. Determine the goal metric

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

### 8. Distill the learnings

Write "## Learnings for New Ads": a short do/don't list grounded in the
sections above (angles and formats that won, placements or demographics
that over-index, targeting patterns the account relies on, copy patterns
of the winners, what fatigued). Every line must trace back to data already
in the file; this section is the one the creative skills act on, so keep
it concrete. Finish the file with "## Data Gaps" (everything this backend
could not provide, the rebuild-spec fields the chosen tier could not read,
plus any caps applied) and a dated "## Changelog" entry, and complete
"## Audit Metadata" and the spend and count figures in
"## Account Snapshot".

### 9. Read the summary back

Give the user a short plain-language summary: account (name and ID),
window, backend, 90-day spend, what is running, the creative coverage
line from step 5b (`<returned>/<requested>` creatives read, with missing
and inaccessible counts), the top 2 to 3 performers with their numbers,
the biggest learnings, the rebuild-spec tier used (and, on Tier C, that
the Route B token would upgrade it), and the file path where the full
memory now lives. Do not paste the whole file or the snapshot files into
chat.

**Completion label.** Say "audit complete" only when the coverage
threshold passed and every section was written from returned data. When
coverage failed the threshold and the user has not accepted the gap, or
when a whole section is a data gap, label the result "audit PARTIAL" and
name the gap in one line. A partial audit still writes its file and is
still useful; it is the label that must be honest, because
`brand-setup` and the creative skills read this file trusting it.

### 10. Note it in Hermes memory

Hermes keeps a small personal notes file, `$HERMES_HOME/memories/MEMORY.md`
(`~/.hermes/memories/MEMORY.md` when `HERMES_HOME` is unset; "My Notes"
in the dashboard, cap 2,200 characters), that is injected into
every session's system prompt. Leave one pointer there so the next session
knows the account memory exists without opening the workspace. Use the
built-in `memory` tool, notes target, one entry under 250 characters that
starts with the stable prefix `Hermes Ad Agent audit:` and records only:
how many account memory files exist under `memory/accounts/` at the
workspace root (a count, never the IDs), the capture tier used (`graph`,
`cli`, or `mcp`), and the audit date. Example shape:
`Hermes Ad Agent audit: <N> account memory file(s) at
<root>/memory/accounts/, captured via <graph|cli|mcp> on <date>. Read the
matching act_ file before building ads.`

Rules for this entry:

- First audit: `add`. Any refresh, or an audit of another account: check
  for an existing `Hermes Ad Agent audit:` entry and `replace` it (matching
  on that prefix as the old text), updating the count, tier, and date. One
  entry per Hermes instance, never one per account.
- Nothing from the account goes in: no account IDs, account names, pixel
  or audience names, copy, spend, or any other number from the audit.
  Those live only in the gitignored memory file. The Hermes memory file is
  a pointer.
- Stay far under the file cap (2,200 characters shared with everything
  else the agent has remembered); if a write is rejected for size, shorten
  this entry rather than trimming someone else's.
- The file is loaded as a frozen snapshot at session start, so the entry
  is visible from the next session on. If `memory.write_approval` is true
  in the Hermes config (`hermes config path` prints its location), the
  write waits in `/memory` as pending until the user runs
  `/memory approve`; tell them. If `memory.memory_enabled` is false, skip
  the write and say so in one line.

### 11. Offer a refresh

One line: the `ad-reporting-automations` skill can schedule a read-only
refresh of this audit on a cadence (monthly is a sensible default) if the
user wants it; otherwise skip. Manual refresh: the user says "refresh the
account memory" any time, which reruns this workflow and updates the same
file, replacing stale sections and appending a dated "## Changelog" entry
rather than creating a second file, and replaces the Hermes memory entry
from step 10 with the new tier and date.

## How the pack consumes the memory file

- **brand-setup** (which runs next during onboarding) reads the file to
  pre-fill discovered facts: the ad account, pixels and conversion events
  in use, the publishing identities from the cross-check, the dominant
  objective, and observed budget levels. The user still confirms
  everything; the audit informs the interview, it does not replace it.
- **Every consumer reads the coverage line first.** A section written
  under partial coverage carries its prefix, and a consumer that finds
  "coverage: 0 of N" treats the copy inventory as absent, not as "the
  account runs no copy".
- **The creative and copy skills** (the Arcads image and video skills,
  `human-ad-copy`, and the other ad-generation skills) read
  "## Learnings for New Ads", "## Top Performers", and
  "## Creative and Copy Inventory" before building net-new ads, so new
  creative extends what already works instead of repeating what already
  fatigued.
- **meta-ad-launcher** reads "## Structure Map" and
  "## Settings Inventory" to match the account's existing conventions
  (naming, CBO versus ABO, placements) when building new campaigns, and
  reads "## Rebuild Specs" plus the `specs/*.jsonl` and `specs/index.json`
  snapshots to mirror a reference entity exactly (targeting, attribution,
  tracking, and creative enhancement enrollment).
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
- Do not put account IDs, names, or numbers into the Hermes memory entry
  (step 10) either; it is a pointer with a file count, a tier, and a date,
  and it is replaced on refresh, never duplicated.
- Do not audit the demo brand or a disconnected setup; skip with a note.
- Do not carry numbers from memory of past sessions or from an old memory
  file into a refresh; pull fresh data every time and update the file.
- On the CLI, a section that depends on an MCP-only tool (previews, media
  inventory, custom audience names, activity logs) is recorded as a data
  gap, not silently skipped.
- Do not treat a missing key in a snapshot as a setting: absent placement
  keys mean Advantage+ placements, an absent `degrees_of_freedom_spec`
  means platform defaults. Record observed defaults, never opt-outs.
- Do not print, echo, or log the Route B token while checking for it or
  using it in a Tier A command, and never issue anything but GET on that
  tier.
- Do not assume the response key. A collector that reads
  `structuredContent.creatives` when the server returns `ad_creatives`
  collects zero records while the summary implies coverage; the coverage
  table in step 5b exists to catch exactly that.
- Do not write copy or creative-pattern findings on zero or partial
  coverage without the prefix and the blocked completion label.
- Do not treat an empty `ads_get_ig_accounts` result as "no Instagram";
  check Pages and the creatives' effective Instagram fields first.
- Do not pick an ad account by display name; identical names are common.
  Name and ID, confirmed by the user.
- Do not put signed media URLs into snapshot files, memory files, or
  terminal arguments; keep the media ID and fetch the URL when needed.
