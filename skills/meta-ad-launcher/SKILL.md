---
name: meta-ad-launcher
description: >-
  Launches finished ad creatives to Meta (Facebook and Instagram) through
  whichever Meta backend is connected (Meta's official Ads MCP server or the
  official Meta Ads CLI): picks or creates the destination campaign and ad
  set (always PAUSED), or mirrors an existing campaign, ad set, and ad
  exactly (targeting, placements, bidding, attribution, tracking, and the
  Advantage+ creative enhancement enrollment) from the account-audit
  snapshot or a live read, uploads the image or video, builds a creative
  from the approved human-ad-copy set (multi-variant text where the backend
  supports it), creates the ad PAUSED, verifies a mirror by reading it
  back and diffing, fetches a preview where the backend offers one,
  reports every created ID back to the user, and holds a strict
  human-confirmation gate before any activation. Use it when the user says
  things like "launch this ad", "push this creative to Meta", "publish this
  as a Facebook ad", "create the campaign and ad set", "build it exactly
  like my winning ad set", "mirror the current campaign for this new
  creative", "put this image live as an ad" (still created paused),
  "deploy these videos to my ad account", or "turn on / activate my paused
  ad". Do not use it to generate creative or write copy; those belong to
  the Arcads creative skills and human-ad-copy.
---

# Meta ad launcher

You turn an approved creative plus approved copy into real Meta ad objects,
in this fixed order:

**checklist → destination → upload media → creative → ad (PAUSED) → verify
after create → preview → report IDs → separate explicit activation (only if
asked)**

Nothing you create in this skill is ever ACTIVE. Creation and activation are
two different conversations with two different confirmations.

The destination step has three paths: put the ad into existing structure,
mirror an existing campaign / ad set / ad so the new structure carries
exactly the settings the account already runs (the default for new
structure whenever an account memory exists), or build new broad structure
from scratch (the fallback). Mirror mode follows
`references/rebuild-fields.md` in this skill folder: the field lists, the
cloning rules, and the verify-after-create diff all live there.

The same workflow runs over either Meta backend: the Meta Ads MCP server
(tools named `ads_*`) or the Meta Ads CLI (Meta's official command-line
tool for the Marketing API, binary `meta`, run in the terminal with
`--output json`). Detect which one is live (Prerequisites), say once which
one you are using, then make the matching calls from the Backend reference
below. The order, the gates, and the report are identical on both.

## Non-negotiable safety rails

1. **Everything is created PAUSED.** Campaigns, ad sets, and ads all get
   `PAUSED` status at creation. There is no exception, even if the user says
   "just make it live". Explain that activation is a separate step.
2. **Activation requires explicit confirmation in the current conversation.**
   Before calling `ads_activate_entity` (MCP) or running
   `meta ads <campaign|adset|ad> update <ID> --status ACTIVE` (CLI), restate
   exactly which entities will go ACTIVE and what the daily budget will be,
   and wait for a clear yes. Approval given earlier in the workflow, or in a
   previous session, does not count.
3. **Budgets and spend settings never change without explicit confirmation.**
   Never call `ads_update_entity` (MCP) or run
   `meta ads <campaign|adset> update <ID> --daily-budget ...` (CLI) to change
   a budget, bid, schedule, or status unless the user confirmed that exact
   change in this conversation.
4. **Never fabricate.** Report only IDs, statuses, and values the Meta tools
   (MCP or CLI) actually returned. If a call failed or a field is missing,
   say so.

## Prerequisites

1. **Confirm a Meta backend is connected.** Detect it in this order:
   - If your live tool list contains tools named `ads_*` (for example
     `ads_get_ad_accounts`, `ads_create_campaign`, `ads_create_ad`), the
     Meta MCP is connected: use the MCP backend.
   - Otherwise, in the terminal, run `meta auth status`; if it reports a
     token, run `meta ads adaccount list --output json`. If that returns
     accounts, the Meta Ads CLI is configured: use the CLI backend.
   - If neither works, stop and tell the user Meta is not connected yet
     (the pack's SETUP.md Step 4 covers both routes).

   If both are available, prefer the MCP (it has the broader surface:
   previews, diagnostics, field help). Say once which backend you are using,
   then proceed, and do not switch backends in the middle of a create
   sequence without telling the user. Names drift between versions: trust
   your live tool list over the MCP tool names written in this file, and
   trust `--help` output over the CLI flags written here.

   On the CLI route, the `AD_ACCOUNT_ID` in the workspace `.env` (the `act_`
   form) must match the ad account in BRAND.md, or pass
   `--ad-account-id <act_ID>` on each command. `meta ads adaccount current`
   shows which account the CLI is pointed at.
2. **Read the user's `BRAND.md`** at the workspace root (the repo clone
   directory recorded during setup). You need the "## Meta Assets" section
   (ad account ID, Page ID, Instagram account ID, pixel ID, default campaign
   objective, default conversion event, default CTA), the landing page URL
   from "## Offer", and the "## Budget Guardrails" section. If `BRAND.md` is
   missing or those sections are empty, offer to run the `brand-setup` skill
   first.
3. **Have the finished creative available.** A local image or video file, or
   an already uploaded Meta image hash / video ID. If the creative only
   exists as a chat attachment, save it to a real file path first.
4. **Have approved copy.** The standard input is the "Ad copy handoff" block
   from the `human-ad-copy` skill: 5 primary texts, 5 headlines, 3
   descriptions, a CTA type, and a validator result. If the copy has not been
   through that skill, invoke it now rather than launching unvalidated copy.

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
| List Pages | `ads_get_ad_account_pages` / `ads_get_user_pages` | `meta ads page list --output json` |
| List Instagram accounts | `ads_get_ig_accounts` | not available; take the ID from BRAND.md or ask the user (Business Settings → Instagram accounts), or omit `--instagram-actor-id` |
| Read campaigns / ad sets / ads | `ads_get_ad_entities` | `meta ads campaign list --output json`, `meta ads adset list --output json`, `meta ads ad list --output json` (add `--status`, `--limit`, `--fields` as needed); single entity: `meta ads <resource> get <ID> --output json` |
| Create campaign (PAUSED) | `ads_create_campaign` | `meta ads campaign create --name "<name>" --objective <OBJECTIVE> [--daily-budget <minor units>] [--special-ad-categories ...] --status PAUSED --output json` |
| Create ad set (PAUSED) | `ads_create_ad_set` | `meta ads adset create <CAMPAIGN_ID> --name "<name>" --optimization-goal <GOAL> --billing-event IMPRESSIONS --daily-budget <minor units> --targeting-countries <CC> [--age-min --age-max --genders] [--pixel-id <ID> --custom-event-type <EVENT>] --status PAUSED --output json` |
| Upload image / video | `ads_creative_upload_image` / `ads_creative_upload_video` | no separate step; `meta ads creative create --image ./file` or `--video ./file` uploads the local file itself |
| Create creative | `ads_create_creative` | `meta ads creative create --name "<name>" --page-id <PAGE_ID> [--instagram-actor-id <IG_ID>] --image ./file --bodies "..." "..." --titles "..." "..." --descriptions "..." --link-url <URL> --call-to-action <CTA> --output json` (singular `--body/--title/--description` for one variant) |
| Inspect / fix / remove a creative | `ads_get_creatives` / `ads_creative_update` / `ads_creative_delete` | `meta ads creative list`, `get <ID>`, `update <ID>`, `delete <ID>` (each with `--output json`) |
| Create ad (PAUSED) | `ads_create_ad` | `meta ads ad create <AD_SET_ID> --name "<name>" --creative-id <CREATIVE_ID> --status PAUSED --output json` |
| Preview an ad | `ads_get_ad_preview` | not available; the user reviews the paused ad in Ads Manager by name or ID |
| Activate (gated) | `ads_activate_entity` | `meta ads <resource> update <ID> --status ACTIVE --output json` |
| Pause | `ads_update_entity` (status) | `meta ads <resource> update <ID> --status PAUSED --output json` |
| Change budget (gated) | `ads_update_entity` (budget) | `meta ads <resource> update <ID> --daily-budget <minor units> --output json` (campaign or adset only) |
| Delivery / rejection errors | `ads_get_errors` | `meta ads <resource> get <ID> --output json`, read `effective_status` and `issues_info` |
| Field help | `ads_get_field_context` / `ads_get_help_article` | `meta ads <resource> <action> --help` |

Mirror mode adds these calls. The tools, flags, and UNVERIFIED marks match
the capability matrix in `references/rebuild-fields.md` section 4; when a
flag is marked UNVERIFIED, `--help` decides, and a missing flag routes that
field to the Graph POST fallback (same confirmation gate).

| Purpose | Meta MCP tool | Meta Ads CLI command |
|---|---|---|
| Read a reference entity with exact fields (Tier B / C) | `ads_get_ad_entities` with `fields` at campaign / adset / ad level (Tier C, partial: no `attribution_spec`, `frequency_control_specs`, `bid_constraints`, `special_ad_categories`, or creative specs; normalize per the reference doc section 5); `ads_get_creatives` with `creative_ids` (flattened, no `degrees_of_freedom_spec`, `asset_feed_spec`, `url_tags`) | `meta ads <resource> get <ID> --fields <list> --output json` (Tier B, complete for campaign / adset / ad); `meta ads creative get <ID> --output json` (whether it returns `degrees_of_freedom_spec` and `asset_feed_spec` is UNVERIFIED; use Tier A for creatives) |
| Graph direct read (Tier A, both backends) | no MCP tool; `source .env && curl -s "https://graph.facebook.com/v25.0/<ENTITY_ID>?fields=<list>&access_token=$ACCESS_TOKEN"` from the workspace root, Route B token, read-only, token never printed | same command |
| Create campaign copying a reference (PAUSED) | `ads_create_campaign` with `source_campaign_id` plus `name`, `objective`, `buying_type`, `bid_strategy`, `special_ad_categories`, `special_ad_category_country`, `spend_cap`, `pacing_type`, `smart_promotion_type`, `daily_budget` or `lifetime_budget` (CBO only), `status: PAUSED` | `meta ads campaign create --name "<name>" --objective <OBJECTIVE> [--bid-strategy <STRATEGY>] [--daily-budget <minor units>] [--lifetime-budget <minor units>] [--pacing-type <TYPE>] [--special-ad-categories ...] --status PAUSED --output json` (one budget flag at most, CBO only); copy-from (`source_campaign_id`) flag UNVERIFIED on 1.1.0 |
| Create ad set copying a reference (PAUSED) | `ads_create_ad_set` with `source_adset_id`, `campaign_id`, `name`, `targeting` (raw JSON), `promoted_object`, `attribution_spec`, `optimization_goal`, `billing_event`, `bid_strategy`, `bid_amount`, `bid_constraints`, `frequency_control_specs`, `adset_schedule`, `is_dynamic_creative`, `dsa_beneficiary`, `dsa_payor`, `destination_type`, `pacing_type`, budget (ABO only), `status: PAUSED`; placements via `targeting` keys, or `placement` / `placement_soft_opt_out` | `meta ads adset create <CAMPAIGN_ID> --name "<name>" --optimization-goal <GOAL> --billing-event <EVENT> [--bid-strategy <STRATEGY>] [--bid-amount <minor units>] [--daily-budget <minor units>] --targeting @targeting.json --promoted-object @promoted.json (or `--pixel-id <ID> --custom-event-type <EVENT>`) --attribution-spec '<json>' [--dsa-beneficiary <ID> --dsa-payor <ID>] --status PAUSED --output json`; `--targeting '<json>'` inline also works; flags for `frequency_control_specs`, `bid_constraints`, `adset_schedule`, `is_dynamic_creative`, and copy-from (`source_adset_id`) UNVERIFIED on 1.1.0 |
| Create creative with mirrored enhancements | `ads_create_creative` with the identity, media, copy, link, and CTA fields plus `degrees_of_freedom_spec` as a JSON string (shortcuts `advantage_plus_creative`, `advantage_plus_creative_features`) and `instagram_user_id`; no `asset_feed_spec` (single variant only) and no `url_tags` parameter (UNVERIFIED whether inline `creative` JSON on `ads_create_ad` passes `url_tags` through) | `meta ads creative create --name "<name>" --page-id <PAGE_ID> [--instagram-actor-id <IG_ID>] --object-story-spec @spec.json --degrees-of-freedom-spec @dof.json [--url-tags "<tags>"] [--contextual-multi-ads <value>] [--authorization-category <value>] [--applink-treatment <value>] [--asset-feed-spec @feed.json] --output json`; when the media is a local file, replace `--object-story-spec @spec.json` with `--image ./file` or `--video ./file` plus the copy, link, and CTA flags (`--asset-feed-spec` shortcuts: `--bodies`, `--titles`, `--descriptions`, `--images`, `--videos`, `--call-to-actions`) |
| Create ad with mirrored tracking (PAUSED) | `ads_create_ad` with `adset_id`, `name`, `creative` (`creative_id`), `tracking_specs`, `conversion_domain`, `source_ad_id` (draft mode), `status: PAUSED` | `meta ads ad create <AD_SET_ID> --name "<name>" --creative-id <CREATIVE_ID> --tracking-specs '<json>' --conversion-domain <domain> --status PAUSED --output json`; copy-from (`source_ad_id`) flag UNVERIFIED on 1.1.0 |
| Graph POST (last resort, gated) | no MCP tool; `source .env && curl -s -X POST "https://graph.facebook.com/v25.0/act_<ACCOUNT_ID>/<edge>" --data-urlencode "<field>=<value>" ... --data-urlencode "targeting@targeting.json" -d "status=PAUSED" -d "access_token=$ACCESS_TOKEN"` where `<edge>` is `campaigns`, `adsets`, `adcreatives`, or `ads`; only for a field neither backend exposes, token never printed | same command |
| Verify after create (read back) | same read tools as the reference read, Tier A preferred | same |

Two CLI rules with no MCP counterpart:

- **Budgets are in minor currency units.** `--daily-budget 5000` is 50.00
  in the account currency. Convert before you call, and restate the human
  amount to the user every time a budget appears in a command or a report.
- **The CLI creates everything PAUSED by default.** This skill still passes
  `--status PAUSED` explicitly on every create so the intent is visible in
  the command.

## Pre-launch checklist

Walk this list and show the user the filled-in result before creating
anything. Every line must be a value you verified, not a guess:

- [ ] **Ad account:** confirmed via `ads_get_ad_accounts` (MCP) or
      `meta ads adaccount list --output json` (CLI); match against the
      account in BRAND.md, and if the user has several accounts, ask which
      one. On the CLI, also confirm `AD_ACCOUNT_ID` (or `--ad-account-id`)
      points at that same account.
- [ ] **Facebook Page ID:** from BRAND.md, cross-checked with
      `ads_get_ad_account_pages` or `ads_get_user_pages` (MCP) or
      `meta ads page list --output json` (CLI).
- [ ] **Instagram account:** from BRAND.md, cross-checked with
      `ads_get_ig_accounts` (MCP). The CLI has no listing command: take the
      ID from BRAND.md or ask the user (Business Settings → Instagram
      accounts). Optional but recommended; without it the ad may not run
      with the brand's Instagram identity.
- [ ] **Destination URL:** the landing page from BRAND.md's "## Offer"
      section, or the URL the user gave for this campaign. One offer, one
      link. **It must be a real, live URL.** If the URL is on example.com
      (the demo brand ships with an example.com placeholder), stop: Meta
      rejects example.com links. Ask the user for a real landing page URL
      before creating any ad; do not launch with a placeholder.
- [ ] **Copy validated:** the human-ad-copy handoff block exists, the
      validator passed (or the manual checklist was applied and disclosed),
      and the user approved the exact final copy.
- [ ] **Creative file(s):** file path, format, and aspect ratio noted.
- [ ] **Pixel / conversion event:** from BRAND.md's "## Meta Assets"
      section, if the objective is conversions.
- [ ] **Special Ad Category:** if the offer touches credit, employment,
      housing, or social issues and politics, flag it; the campaign must
      declare it and targeting options narrow. Ask the user rather than
      guessing.

If any line fails, resolve it before continuing.

## Step 1: Choose the destination

Ask the user whether this ad goes into existing structure or new structure.
New structure has two flavors, and the choice between them is yours to
default and the user's to override:

- **Mirror existing structure** is the DEFAULT plan for new structure
  whenever an account memory exists for this account
  (`memory/accounts/act_<ACCOUNT_ID>.md` and its `specs/` folder at the
  workspace root, written by the `account-audit` skill) and it holds a
  suitable reference.
- **New structure (broad)** is the fallback: no memory for this account, no
  suitable reference in it (wrong objective, a special ad category the brief
  does not share, or the user rejects every candidate), or the user asks
  for broad targeting outright.

Say which path you are on and why before drafting the plan.

**Existing structure.** List the account's campaigns and ad sets with
`ads_get_ad_entities` (MCP) or `meta ads campaign list --output json` and
`meta ads adset list --output json` (CLI; add `--status` filters). Filter to
ACTIVE and PAUSED so archived structure does not clutter the choice. Present
name, ID, objective, and status. The user picks the target ad set. Confirm
the pick back: account, campaign, ad set, and destination URL. The wrong
hierarchy spends the wrong budget, so this confirmation is worth ten
seconds.

**Mirror existing structure (default when memory exists).** Build a new
campaign, ad set, and ad that carry exactly the settings of a reference
campaign, ad set, and ad already in the account: objective, budget mode,
targeting object, placements, optimization and billing, bidding,
attribution, tracking specs, conversion domain, and the Advantage+ creative
enhancement enrollment. Read `references/rebuild-fields.md` in this skill
folder before you start; its sections 6 (cloning rules) and 7 (verify after
create) are the contract.

1. **Pick the reference.**
   - *With memory:* read
     `memory/accounts/act_<ACCOUNT_ID>/specs/index.json`. It maps every id
     to name, parent ids, status, and 90-day spend. Shortlist ad sets whose
     campaign objective matches the brief (or BRAND.md's default objective
     when the brief does not say), ACTIVE before PAUSED, highest 90-day
     spend first, and show the user the top few with name, ID, campaign,
     status, and spend. The user picks one or names one directly. Then pull
     the raw objects by id from `campaigns.jsonl`, `adsets.jsonl`,
     `ads.jsonl` (one ad in the reference ad set; the user's pick, else
     the highest-spend one), and `creatives.jsonl` (that ad's creative).
     Note each line's `_captured_via`: an `mcp` line carries the read gaps
     listed in the reference doc's section 4 and needs its section 5
     normalization re-checked.
   - *Without memory:* do a live read using the best available tier from
     the reference doc's section 1. Tier A (Graph direct read with the
     Route B token) if the workspace-root `.env` holds `ACCESS_TOKEN`;
     else Tier B (`meta ads <resource> get <ID> --fields <list> --output
     json`, creatives via `meta ads creative get`, with Tier A for the
     creative when the token exists); else Tier C (`ads_get_ad_entities`
     with `fields`, `ads_get_creatives` with `creative_ids`, then normalize
     per section 5). List candidates with the read commands in the Backend
     reference, let the user pick, then read the campaign, the ad set, one
     ad in it, and that ad's creative with the exact field lists from
     section 3. Tier A commands take the token from `.env` through the
     shell, for example
     `source .env && curl -s "https://graph.facebook.com/v25.0/<ID>?fields=<list>&access_token=$ACCESS_TOKEN"`;
     the token must never be echoed, logged, or pasted into chat, memory
     files, or job prompts, and the raw command line is never saved. Keep
     the raw JSON in the run folder (not in git, not in chat) for the
     cloning and verify steps. A live read does not create the `specs/`
     snapshot files; offer to run `account-audit` for that.
   - *No usable reference:* fall back to new structure (broad) and say so.
2. **Show the user what will be mirrored.** Before any create, present the
   plan summary drawn from the cleaned reference (reference doc section 6,
   last paragraph):
   - campaign: objective, buying type, special ad categories, bid strategy,
     spend cap, pacing, budget mode (CBO or ABO)
   - ad set: optimization goal, billing event, bid strategy and bid amount
     or constraints, attribution windows, destination type, promoted object
     (pixel and event), frequency caps and schedule when present,
     `targeting_automation` state
   - targeting summary: geo (included and excluded), age range, genders,
     custom audiences included and excluded (by name from the memory file
     when it has them, else by id count), detailed targeting, connections
   - placements: the explicit placement keys, or "Advantage+ placements
     (all)" when none are set, with the reference's `effective_*` arrays
     as "observed delivery" for context
   - ad: tracking specs, conversion domain
   - creative: enhancement enrollment as a per-feature `OPT_IN` / `OPT_OUT`
     list from `degrees_of_freedom_spec`, or "platform defaults" when the
     reference has none; `url_tags`, `contextual_multi_ads`,
     `instagram_user_id`, CTA type; whether the reference was multi-variant
     (`asset_feed_spec` present)
   - budget amount: from the user's brief, compared line by line to the
     BRAND.md daily spend cap (the reference's amount is shown for context
     only and is never copied)

   Label every line with where the value came from: "from reference
   <name / ID>" for mirrored values, "from brief" or "from BRAND.md" for
   the new name, budget amount, media, copy, destination URL, and any CTA
   change. Mark any field the read tier could not see as a gap (for
   example "attribution: not readable on the MCP; add the Route B token to
   mirror it") rather than guessing a value; on a Tier C reference,
   express attribution from `learning_stage_info.attribution_windows` only
   after the user confirms it. Never treat a missing key as a setting.
3. **The user approves the plan**, including the budget versus the cap and
   the reference choice. Then create per the Cloning rules below and
   continue to Step 2. The user can override any mirrored value in the
   plan; an override is a "from brief" value and is verified as such.

**New structure (broad, fallback).** Create it explicitly, and only after
the user approves a plan containing:

- campaign name and objective (default campaign objective from BRAND.md's
  "## Meta Assets" section, for example `OUTCOME_SALES` or `OUTCOME_LEADS`)
- special ad categories (usually an empty list, but always stated)
- budget location: campaign-level budget (CBO) or ad-set-level budget (ABO),
  and the daily amount, explicitly compared to the BRAND.md daily spend cap
- ad set name, targeting (keep it broad: countries, age range, optional
  gender; do not invent interests or custom audiences the user never asked
  for), and the conversion event plus pixel if optimizing for conversions

If `memory/accounts/act_<ACCOUNT_ID>.md` exists at the workspace root for
this account but you are on this path (no suitable reference, or the user
asked for broad), still read its "## Structure Map" section before drafting
the plan and follow the account's observed conventions: the naming
pattern, CBO versus ABO, and the attribution setting. Say in the plan
which choices came from the memory file; the user can override any of
them. The default conversion event, objective, pixel, and CTA still come
from BRAND.md's "## Meta Assets" as above.

Then create both with **PAUSED** status:

- **MCP:** call `ads_create_campaign`, then `ads_create_ad_set`. Check each
  tool's live schema for exact parameter names before calling; server
  versions differ.
- **CLI:** run the campaign create, take the campaign ID from the JSON, then
  run the ad set create against it:

  ```
  meta ads campaign create --name "<name>" --objective <OBJECTIVE> \
    [--daily-budget <minor units>] [--special-ad-categories ...] \
    --status PAUSED --output json
  meta ads adset create <CAMPAIGN_ID> --name "<name>" \
    --optimization-goal <GOAL> --billing-event IMPRESSIONS \
    --daily-budget <minor units> --targeting-countries <CC> \
    [--age-min <N> --age-max <N> --genders <...>] \
    [--pixel-id <ID> --custom-event-type <EVENT>] \
    --status PAUSED --output json
  ```

  `--optimization-goal` and `--billing-event` are required on the ad set.
  Put `--daily-budget` on the campaign for CBO or on the ad set for ABO, as
  the plan said, and never on both. Targeting goes through
  `--targeting-countries` plus the optional `--age-min`, `--age-max`, and
  `--genders` flags. When optimizing for conversions, add `--pixel-id` and
  `--custom-event-type` from BRAND.md's "## Meta Assets". Pass
  `--status PAUSED` explicitly even though it is the default. Budgets are
  minor units (5000 is 50.00): convert, then restate the amount to the user
  in the account currency before running the command. Check `--help` for
  the flags your installed version accepts.

A paused ad set with a budget spends nothing, but the budget number still
needs the user's approval because it is what activation will unleash later.

### Cloning rules (mirror mode)

Apply `references/rebuild-fields.md` section 6 to each reference object, in
order, before you write anything:

1. Strip identity and state (`id`, `account_id`, `created_time`,
   `updated_time`, `status`, `effective_status`, `budget_remaining`,
   `learning_stage_info`, `preview_shareable_link`,
   `effective_object_story_id`, `effective_instagram_media_id`,
   `_captured_via`, `_captured_at`).
2. Strip the read-only echoes (every `effective_*` key,
   `targeting_relaxation_types`, `targeting_optimization`,
   `dt_consolidation_state`, `page_types`, `multi_optimization_goal_weight`,
   `targeting_optimization_types`, `is_budget_schedule_enabled`,
   `campaign_group_active_time`).
3. Re-parent: the new `campaign_id` on the ad set, the new `adset_id` on the
   ad. Never reuse the reference's parent on this path.
4. Record provenance: `source_campaign_id`, `source_adset_id`,
   `source_ad_id` set to the reference ids.
5. Rename per the naming convention in the memory file's Structure Map (or
   the reference's own pattern when there is no memory), with the user's
   approved name.
6. Budgets and schedule: carry the budget mode (CBO or ABO) exactly; the
   amount comes from the user's brief and the BRAND.md cap check, never from
   the reference; drop `start_time` and `end_time` unless the user asked for
   a schedule.
7. Status: `PAUSED` on every entity.
8. Creative: reuse the `object_story_spec` shape with the new media and the
   approved copy; carry `degrees_of_freedom_spec` verbatim (the enhancement
   enrollment is the point of mirroring); carry `url_tags`,
   `contextual_multi_ads`, `instagram_user_id`, and the call to action
   unless the brief changes them; carry the `asset_feed_spec` structure
   when the reference was multi-variant (CLI or Graph only).
9. Special ad categories carry over exactly.

The result is the **cleaned reference**: one JSON object per entity with
only writable fields, kept in the run folder (never in git, never in chat)
so the verify step can diff against it.

Three things the mirror never copies, whatever the reference says: the
status (always `PAUSED`; rails 1 and 2 stand), the budget amount (mode yes,
amount from the brief against the BRAND.md cap; rail 3 stands), and any
activation (Step 7 is a separate conversation). The pre-launch checklist,
the plan approval, and the per-create confirmation all still apply.

**Write mapping, MCP backend.** Check each tool's live schema first.

- Campaign: `ads_create_campaign` with `source_campaign_id` set to the
  reference campaign id, plus the new `name`, `status: PAUSED`, and the
  cleaned campaign fields (`objective`, `buying_type`, `bid_strategy`,
  `special_ad_categories`, `special_ad_category_country`, `spend_cap`,
  `pacing_type`, `smart_promotion_type`, and `daily_budget` or
  `lifetime_budget` only when the mode is CBO).
- Ad set: `ads_create_ad_set` with `source_adset_id`, the new
  `campaign_id`, the new `name`, `status: PAUSED`, the full cleaned
  `targeting` JSON (belt and braces even with the copy-from id),
  `promoted_object`, `attribution_spec`, `optimization_goal`,
  `billing_event`, `bid_strategy`, `bid_amount`, and, when the reference
  carries them, `bid_constraints`, `frequency_control_specs`,
  `adset_schedule`, `destination_type`, `pacing_type`,
  `is_dynamic_creative`, `dsa_beneficiary`, `dsa_payor`; the budget only
  when the mode is ABO. Placement controls travel inside `targeting`; use
  `placement` / `placement_soft_opt_out` only if the live schema offers
  them and the targeting keys cannot express the reference.
- Creative: `ads_create_creative` with the Page and `instagram_user_id`,
  the new media, the approved copy, link, and CTA, and the mirrored
  `degrees_of_freedom_spec` passed as a JSON string (the shortcuts
  `advantage_plus_creative` and `advantage_plus_creative_features` exist,
  but the full spec is the exact mirror; use it).
  **MCP limitation:** `ads_create_creative` takes no `asset_feed_spec`
  (single variant only) and no `url_tags`; whether inline `creative` JSON
  on `ads_create_ad` passes `url_tags` through is UNVERIFIED.
  **Workaround:** for a multi-variant reference, create several
  single-variant creatives (one per approved copy variant) and one PAUSED
  ad per creative in the same ad set, and tell the user the variants are
  split across ads rather than pooled in one creative; or, when the CLI is
  also configured, build that one creative on the CLI with
  `--asset-feed-spec @feed.json` and say you switched backends for it. For
  `url_tags`, use the CLI or the Graph POST fallback for that creative, or
  tell the user the tags were not mirrored and list them as a delta in the
  verify report. Never drop them silently.
- Ad: `ads_create_ad` with the new `adset_id`, `name`, `creative` holding
  `creative_id`, the mirrored `tracking_specs` and `conversion_domain`,
  `source_ad_id` when the live schema takes it (draft mode), and
  `status: PAUSED`.

**Write mapping, CLI backend.** `--help` wins over every flag here. Write
`targeting.json`, `promoted.json`, `dof.json`, and (when needed)
`spec.json` / `feed.json` from the cleaned reference into the run folder
and pass them with `@file`.

- Campaign:
  `meta ads campaign create --name "<name>" --objective <OBJECTIVE>
  [--bid-strategy <STRATEGY>] [--daily-budget <minor units> |
  --lifetime-budget <minor units>] [--pacing-type <TYPE>]
  [--special-ad-categories ...] --status PAUSED --output json`.
  The copy-from flag (`source_campaign_id`) is UNVERIFIED on 1.1.0: check
  `--help`; if it is missing, either set provenance through the Graph POST
  fallback or report the unset `source_campaign_id` as a known delta.
- Ad set:
  `meta ads adset create <CAMPAIGN_ID> --name "<name>"
  --optimization-goal <GOAL> --billing-event <EVENT>
  [--bid-strategy <STRATEGY>] [--bid-amount <minor units>]
  [--daily-budget <minor units>] --targeting @targeting.json
  --promoted-object @promoted.json --attribution-spec '<json>'
  [--dsa-beneficiary <ID> --dsa-payor <ID>] --status PAUSED --output json`.
  `--targeting @targeting.json` (or `--targeting '<json>'`) replaces the
  broad-path `--targeting-countries` / `--age-min` / `--age-max` /
  `--genders` flags; do not mix them. `--promoted-object` replaces
  `--pixel-id` + `--custom-event-type` (either form is verified; use the
  JSON one to carry every key). Flags for `frequency_control_specs`,
  `bid_constraints`, `adset_schedule`, `is_dynamic_creative`, and the
  copy-from `source_adset_id` are UNVERIFIED on 1.1.0: check `--help`, and
  route any field with no flag to the Graph POST fallback.
- Creative:
  `meta ads creative create --name "<name>" --page-id <PAGE_ID>
  [--instagram-actor-id <IG_ID>] --object-story-spec @spec.json
  --degrees-of-freedom-spec @dof.json [--url-tags "<tags>"]
  [--contextual-multi-ads <value>] [--authorization-category <value>]
  [--applink-treatment <value>] --output json`, where `spec.json` is the
  reference's `object_story_spec` shape with the new media reference and
  the approved copy. When the media is a local file that still needs
  uploading, use the media flags instead of `--object-story-spec`
  (`--image ./file` or `--video ./file` plus `--body` / `--title` /
  `--description` or their plural forms, `--link-url`,
  `--call-to-action`) together with `--degrees-of-freedom-spec @dof.json`
  and the same optional flags. For a multi-variant reference, add
  `--asset-feed-spec @feed.json` carrying the reference's structure with
  the approved copy and new media (the plural shortcuts `--bodies`,
  `--titles`, `--descriptions`, `--images`, `--videos`,
  `--call-to-actions` are the same field).
- Ad:
  `meta ads ad create <AD_SET_ID> --name "<name>" --creative-id
  <CREATIVE_ID> --tracking-specs '<json>' --conversion-domain <domain>
  --status PAUSED --output json`. The copy-from flag (`source_ad_id`) is
  UNVERIFIED on 1.1.0; same handling as the campaign.

**Graph POST, last resort only.** For a field that neither the live MCP
schema nor the installed CLI exposes (examples: `frequency_control_specs`
or `source_*` on a CLI whose `--help` lacks the flag; `url_tags` or
`asset_feed_spec` on an MCP-only setup with no CLI), POST the cleaned
reference object directly with the Route B token, still `PAUSED`, and only
after the same explicit confirmation every create in this skill requires:
`source .env && curl -s -X POST
"https://graph.facebook.com/v25.0/act_<ACCOUNT_ID>/<edge>"
--data-urlencode "name=<name>" --data-urlencode "campaign_id=<ID>"
--data-urlencode "targeting@targeting.json" ... -d "status=PAUSED"
-d "access_token=$ACCESS_TOKEN"`, where `<edge>` is `campaigns`, `adsets`,
`adcreatives`, or `ads` (JSON-valued fields URL-encoded from the
run-folder files). The token comes from `.env` through the shell and is
never echoed, logged, or pasted into chat, memory files, or job prompts;
do not save the command line. Say in the report which fields went through
the Graph fallback. If no Route B token exists, the field cannot be
mirrored: say so and list it as a delta.

## Step 2: Upload the media

**MCP:**

- **Image:** `ads_creative_upload_image` with the file. Keep the returned
  image hash or ID for the creative.
- **Video:** `ads_creative_upload_video` with the file. Keep the returned
  video ID. **Video processing is asynchronous on Meta's side.** Do not
  create the ad the same second the upload returns; verify the video shows as
  ready (check it with `ads_get_ad_videos`, or retry the creative step after
  a short wait if creation fails with a video-processing error). A video
  creative also needs a thumbnail image; if the tool schema asks for one and
  Meta has not auto-generated it yet, wait for processing to finish.

You can list what already exists in the account with `ads_get_ad_images` and
`ads_get_ad_videos` when the user wants to reuse previously uploaded media.

**CLI:** there is no separate upload step. `meta ads creative create
--image ./file` or `--video ./file` uploads the local file itself as part of
creating the creative (images: .jpg .jpeg .png .gif .bmp .webp; videos:
.mp4 .mov .avi .mkv .wmv). The video-processing caution still applies: if
`meta ads ad create` fails with a video-processing error, wait, list the ad
set's ads (`meta ads ad list --output json`) to confirm nothing was
created, then retry the ad create only. Do not re-run the creative create;
that would upload the video again and leave a duplicate creative.

## Step 3: Build the creative

**MCP:** call `ads_create_creative`. Check its live parameter schema first,
then map the approved inputs onto it:

- **Identity:** the Page ID, plus the Instagram account when available.
- **Asset:** the image hash (image ad) or video ID plus thumbnail (video ad).
- **Link and CTA:** the destination URL and the CTA type from the copy
  handoff (for example `LEARN_MORE`, `SHOP_NOW`, `SIGN_UP`).
- **Text, multi-variant where supported.** Meta creatives can carry a pool of
  copy that the delivery system mixes per impression (the concept Meta calls
  text liquidity or flexible ads: multiple bodies, titles, and descriptions
  in one creative). If the tool schema accepts arrays of bodies, titles, and
  descriptions, supply the full approved set: 5 primary texts, 5 headlines,
  3 descriptions. If the schema only accepts a single body, title, and
  description, use variant 1 of each, tell the user the server version
  limited you to one variant, and offer to create additional ads for the
  other variants instead.

**CLI:** run `meta ads creative create` with the same inputs mapped onto
its flags:

```
meta ads creative create --name "<name>" --page-id <PAGE_ID> \
  [--instagram-actor-id <IG_ID>] \
  --image ./file \
  --bodies "<primary 1>" "<primary 2>" "<primary 3>" "<primary 4>" "<primary 5>" \
  --titles "<headline 1>" "<headline 2>" "<headline 3>" "<headline 4>" "<headline 5>" \
  --descriptions "<description 1>" "<description 2>" "<description 3>" \
  --link-url <URL> --call-to-action <CTA> --output json
```

- **Identity:** `--page-id <PAGE_ID>` is required; add
  `--instagram-actor-id <IG_ID>` when the ID is known.
- **Asset:** `--image ./file` or `--video ./file` (the upload happens here,
  see Step 2).
- **Link and CTA:** `--link-url <URL>` and `--call-to-action <CTA>`.
- **Text, multi-variant:** the plural flags `--bodies` (max 5), `--titles`
  (max 5), and `--descriptions` (max 5) each take several quoted values, so
  the 5/5/3 handoff set fits in one creative. If the installed version
  rejects the plural flags (check `meta ads creative create --help`), fall
  back to the singular `--body`, `--title`, and `--description` with
  variant 1 of each, tell the user the CLI version limited you to one
  variant, and offer to create additional ads for the other variants.

**Mirror mode:** the creative also carries the reference's
`degrees_of_freedom_spec` verbatim (`degrees_of_freedom_spec` as a JSON
string on `ads_create_creative`; `--degrees-of-freedom-spec @dof.json` on
the CLI), plus `url_tags`, `contextual_multi_ads`, `instagram_user_id`, and
the CTA type unless the brief changed them; see the Cloning rules in
Step 1 for the exact mapping and the MCP limitation on `asset_feed_spec`
and `url_tags`. Do not "improve" the enrollment: an `OPT_OUT` in the
reference stays `OPT_OUT`, and an absent spec stays absent (platform
defaults), because matching the reference is the point.

Never edit the approved copy while mapping it into fields. If a field limit
forces a cut, go back to the user with the exact problem.

`ads_get_creatives` and `ads_creative_update` exist for inspecting and fixing
a creative; `ads_creative_delete` removes one created in error (on the CLI:
`meta ads creative list`, `get`, `update`, `delete`). When a parameter's
meaning is unclear, use `ads_get_field_context` on the MCP and
`ads_get_help_article` for Meta's own documentation; on the CLI,
`meta ads creative create --help` is the reference.

## Step 4: Create the ad, PAUSED

Create the ad with the target ad set ID, the creative ID, a clear ad name
(a good default: `<creative-slug> | <angle> | <date>`), and **PAUSED**
status: `ads_create_ad` (MCP) or
`meta ads ad create <AD_SET_ID> --name "<name>" --creative-id <CREATIVE_ID>
--status PAUSED --output json` (CLI). In mirror mode add the reference's
`tracking_specs` and `conversion_domain` (and `source_ad_id` where the
backend takes it) as the Cloning rules describe. One creative per ad. If
the user approved multiple creatives, repeat steps 2 to 4 per creative in
the same ad set unless the plan said otherwise.

If creation fails, read the error carefully and fix the actual cause. On
the MCP, check `ads_get_errors` for account-level problems. On the CLI, the
command prints the API error itself (exit code 4 is an API error, 3 is an
authentication error); for an ad that was created but is flagged, read
`effective_status` and `issues_info` from
`meta ads ad get <ID> --output json` (the same `get` works on the ad set
and campaign). Do not blind-retry a mutation; a retry after an ambiguous
failure can create duplicates. List the ad set's ads first
(`ads_get_ad_entities` or `meta ads ad list --output json`) to see whether
the ad actually got created.

## Step 5: Verify after create

A mirror is only exact if you check it, so this step runs before any
preview or report. On the existing-structure and broad paths it is short:
read each created entity back (`ads_get_ad_entities` / `ads_get_creatives`
on the MCP, `meta ads <resource> get <ID> --output json` on the CLI),
confirm `status` is `PAUSED`, the parent ids are the ones in the plan, and
the ad points at the creative you built, and report anything that differs.

In mirror mode, follow `references/rebuild-fields.md` section 7 in full:

1. Read the new campaign, ad set, ad, and creative back with the same tier
   used for the reference read, Tier A or B preferred (Tier A for the
   creative whenever the Route B token exists, because only it is
   guaranteed to return `degrees_of_freedom_spec`). Use the exact field
   lists from the reference doc's section 3.
2. Diff against the cleaned reference, field by field:
   - campaign: `objective`, `buying_type`, `bid_strategy`,
     `special_ad_categories`, `special_ad_category_country`, `spend_cap`,
     `pacing_type`, `smart_promotion_type`, budget mode
   - ad set: `targeting` (deep compare after stripping the read-only
     echoes from the read-back and, on a Tier C read-back, after section 5
     normalization; element order inside `flexible_spec`,
     `custom_audiences`, and placement lists is not a delta, a missing or
     extra element is), `promoted_object`, `optimization_goal`,
     `billing_event`, `bid_strategy`, `bid_amount`, `attribution_spec`,
     `frequency_control_specs`, `destination_type`, `pacing_type`,
     `is_dynamic_creative`, budget mode
   - ad: `creative.id` set to the new creative, `tracking_specs`,
     `conversion_domain`
   - creative: `degrees_of_freedom_spec.creative_features_spec` per
     feature (`enroll_status` must match, feature by feature), `url_tags`,
     `instagram_user_id`, `call_to_action_type`, media ids
3. Report every delta as a row with the field name, the expected value
   (from the cleaned reference), and the actual value (from the
   read-back). A key present in the cleaned reference but absent in the
   read-back is a delta (`actual: absent`); a key in the read-back that
   the reference never carried is a delta unless it is on the harmless
   list or is a platform default (say which). Never silently accept a
   difference, and never round a near-match into a match.
4. Expected, harmless deltas, listed under their own heading so the user
   can skip them: new ids, `PAUSED` status, the new name, new parent ids,
   new media hashes or video ids, `source_*` provenance fields, and any
   `effective_*` echoes the platform recomputes.
5. A field the read-back tier cannot see (Tier C cannot read
   `attribution_spec` or any creative spec) is reported as
   `unverifiable on this tier`, never as matched; name the Route B token
   as the fix. A read-back that fails is not a pass: say the read failed,
   keep the created IDs, and mark the mirror unverified.

If a delta is a real mismatch (the wrong optimization goal, an enhancement
enrolled the other way, a targeting key dropped), do not fix it by
re-creating on your own. Show the delta, propose the exact update or the
delete-and-recreate, and wait for the user's confirmation; a paused entity
with a wrong setting is safe to leave paused while they decide.

## Step 6: Preview and report

1. **MCP:** fetch a preview with `ads_get_ad_preview` (ask the user which
   placement format they want to see if the tool offers options; feed and
   story/reel are the useful defaults). **CLI:** there is no preview
   command, so the report line reads "Preview: review in Ads Manager
   (search the ad name or ID)".
2. Report the launch in one block the user can keep:

```markdown
## Launch report: <campaign or ad name>
Backend: MCP | CLI
Destination path: existing | mirror of <reference campaign / ad set / ad, names and IDs> | new (broad)
Everything below is PAUSED. Nothing spends until you activate it.

| Entity | Name | ID | Status |
|---|---|---|---|
| Campaign | ... | ... | PAUSED (or "existing") |
| Ad set | ... | ... | PAUSED (or "existing") |
| Creative | ... | ... | created |
| Ad | ... | ... | PAUSED |

- Copy variants attached: <5/5/3, or what the backend allowed>
- Destination: <URL> | CTA: <type>
- Daily budget on activation: <amount> (BRAND.md cap: <cap>)
- Preview: <link, or "review in Ads Manager" on the CLI route>
- Verify after create: exact match | <N> deltas (table below) | unverified (<reason>)
- Mirror gaps (read tier limits) and Graph POST fields, if any: <list>

| Field | Expected (reference) | Actual (read-back) |
|---|---|---|
| ... | ... | ... |

Harmless deltas: <ids, PAUSED, name, parents, media, source_* , effective_*>
```

The delta table and the mirror lines appear only in mirror mode; on the
other paths the verify line reads "read back: PAUSED, parents and creative
link confirmed" or names what was off.

3. Tell the user how to review it in Ads Manager and that they can activate
   either there or by asking you.

If this launch is part of an orchestrated campaign run (see the
`ad-agent-orchestrator` skill), also save this block as `launch.md` in the
run folder.

## Step 7: Activation (separate, gated, only on request)

When the user asks to turn the ads on:

1. Restate exactly what will happen: which entities go ACTIVE (by name and
   ID), and the daily budget that starts spending, compared to the BRAND.md
   cap. Remind them that an ACTIVE ad still does not deliver while its ad set
   or campaign stays PAUSED, so list every level that needs flipping.
2. Wait for an explicit confirmation in this conversation. "Looks great" about
   the preview is not activation approval; ask plainly: "Confirm and I will
   activate <entities> at <budget>/day."
3. Only then activate each confirmed entity, bottom-up or top-down as the
   user chose: `ads_activate_entity` (MCP) or
   `meta ads <campaign|adset|ad> update <ID> --status ACTIVE --output json`
   (CLI), one call per entity.
4. Verify with `ads_get_ad_entities` (MCP) or
   `meta ads ad get <ID> --output json` (CLI; the same `get` on the ad set
   and campaign) and report the new statuses. Offer to set up monitoring
   with the `meta-performance-loop` skill and alerts with
   `ad-reporting-automations`.

Pausing an ACTIVE entity at the user's request also goes through
confirmation (state what will stop delivering), then `ads_update_entity`
(MCP) or `meta ads <campaign|adset|ad> update <ID> --status PAUSED` (CLI).

## Pitfalls

- **Wrong account or ad set.** Always confirm the hierarchy before mutating.
  On the CLI, that includes the `AD_ACCOUNT_ID` the commands run against.
- **Video not processed.** The most common video-ad failure; wait and verify
  before creating the ad.
- **Tool name drift.** Server versions differ. If a tool named here is not in
  your live list, find the closest equivalent in your actual roster and say
  which one you used.
- **Flag drift.** CLI versions differ; trust `--help` over the flags written
  here, and say which flag you used if it differs.
- **Budget units on the CLI are minor units.** `--daily-budget 5000` is
  50.00, not 5,000. Convert, then restate the human amount.
- **Silent copy edits.** The launcher launches; it does not rewrite. Copy
  changes go back through `human-ad-copy` and user approval.
- **Duplicate ads from retries.** After any ambiguous failure, list before
  re-creating.
- **Treating enthusiasm as approval.** The activation gate needs the restated
  entities and budget, then a yes.
- **Mirroring the wrong things.** The mirror copies settings, never status,
  never the budget amount, never the reference's media or copy. A reference
  that was ACTIVE still yields a PAUSED copy.
- **Writing read-only echoes back.** `effective_*` keys,
  `targeting_relaxation_types`, and the rest of the strip list make the
  create fail or silently change targeting. Clean first, then write.
- **Trusting a partial read as complete.** An `mcp`-captured reference
  cannot show attribution, frequency caps, or enhancement enrollment. Show
  those as gaps in the plan and as `unverifiable` in the verify report;
  never fill them in from memory.
- **Skipping the read-back.** A create that returned an id is not proof the
  settings landed. Step 5 is part of the launch, not an optional extra.
- **Leaking the Route B token.** Tier A reads and Graph POSTs take the token
  from `.env` through the shell; the token is never echoed, logged, or
  pasted into chat, memory files, or job prompts, and the expanded command
  line is never saved.
