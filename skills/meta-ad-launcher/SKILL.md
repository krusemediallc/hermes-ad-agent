---
name: meta-ad-launcher
description: >-
  Launches finished ad creatives to Meta (Facebook and Instagram) through
  whichever Meta backend is connected (Meta's official Ads MCP server or the
  official Meta Ads CLI): resolves the workspace from the setup-state file,
  gets verbatim approval of the whole copy pool bound to a content hash,
  opens a durable run ledger before the first write, picks or creates the
  destination campaign and ad set (always PAUSED), or mirrors an existing
  campaign, ad set, and ad exactly (targeting, placements, bidding,
  attribution, tracking, and the Advantage+ creative enhancement
  enrollment) from the account-audit snapshot or a live read, uploads the
  image or video through whichever backend can take it, builds ONE flexible
  creative per media asset carrying all 5 primary texts, 5 headlines, and 3
  descriptions (routing that creative through the CLI when the MCP cannot
  build it), creates the ad PAUSED, verifies by reading everything back,
  fetches a preview where the backend offers one, reports every created ID,
  retires run-owned ads, creatives, and media cleanly when asked, and holds
  a strict human-confirmation gate before any activation. Use it when the
  user says things like "launch this ad", "push this creative to Meta",
  "publish this as a Facebook ad", "create the campaign and ad set", "build
  it exactly like my winning ad set", "mirror the current campaign for this
  new creative", "put this image live as an ad" (still created paused),
  "deploy these videos to my ad account", "retire the ads from that run",
  or "turn on / activate my paused ad". Do not use it to generate creative
  or write copy; those belong to the Arcads creative skills and
  human-ad-copy.
---

# Meta ad launcher

You turn an approved creative plus approved copy into real Meta ad objects,
in this fixed order:

**checklist → copy approval (verbatim, hashed) → destination plan → run
ledger → media → creative → ad (PAUSED) → verify after create → preview →
report IDs → separate explicit activation (only if asked)**

Nothing you create in this skill is ever ACTIVE. Creation and activation are
two different conversations with two different confirmations.

Two contracts sit under everything below:

- **One flexible creative per media asset.** Each approved image or video
  becomes exactly one creative that carries the whole approved copy pool
  (5 primary texts, 5 headlines, 3 descriptions) as an `asset_feed_spec`,
  and exactly one PAUSED ad. "5 primary texts and 5 headlines" means all
  of them inside one ad unit, never five ads. You never reduce the pool to
  one variant on your own, and you never multiply the ad count to fit a
  backend.
- **Writes go through the Meta MCP or the Meta Ads CLI only.** The Graph
  API is read-only in this pack (Tier A reads and diagnostics). When the
  chosen backend lacks a capability, use the other backend for that
  operation if it is installed; otherwise stop, explain the gap, and let
  the user choose. Never improvise a Graph POST or a Graph upload.

The destination step has three paths: put the ad into existing structure,
mirror an existing campaign / ad set / ad so the new structure carries
exactly the settings the account already runs (the default for new
structure whenever an account memory exists), or build new broad structure
from scratch (the fallback). Mirror mode follows
`references/rebuild-fields.md` in this skill folder: the field lists, the
cloning rules, and the verify-after-create diff all live there.

The same workflow runs over either Meta backend: the Meta Ads MCP server
(server-native tool names `ads_*`) or the Meta Ads CLI (Meta's official
command-line tool for the Marketing API, binary `meta`, run in the terminal
with `--output json`). Detect which one is live (Prerequisites), say once
which one you are using, then make the matching calls from the Backend
reference below. The order, the gates, and the report are identical on both.

**Tool naming on the MCP.** The bare `ads_*` names in this file are the
server-native IDs the Meta server advertises. The Hermes runtime registers
them under a prefixed callable name (observed shape:
`mcp__meta_ads__ads_get_ad_accounts`, where `meta_ads` is the server name
from the Hermes config). Discover the registered name in your live tool
list (`tool_search` or the equivalent in your runtime) and call that; never
assume the bare name is callable. Tool counts drift from day to day, so
readiness is capability-based (the tools this skill needs are present),
never count-based.

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

1. **Resolve the workspace root from the setup-state file.** Setup writes a
   non-secret state file at `$HERMES_HOME/hermes-ad-agent/setup-state.json`
   (fallback `~/.hermes/hermes-ad-agent/setup-state.json` only when
   `HERMES_HOME` is unset; on a managed Hermes host `HERMES_HOME` is set,
   so check the variable first and never hard-code the path). Read
   `workspace_root` (absolute), `meta_backend` (`mcp`, `cli`, or `none`),
   and `arcads_connected` from it. Every path in this skill (`BRAND.md`,
   `memory/`, `ad-runs/`, `outputs/`) is relative to that `workspace_root`;
   a fresh session or a cron job has no conversation history to fall back
   on. If the file is missing or `workspace_root` does not exist on disk,
   stop and ask the user for the workspace root (or to re-run the pack's
   SETUP.md), then continue; do not guess from the current directory. The
   file holds no secrets and no account IDs; never write either into it.
2. **Confirm a Meta backend is connected.** Detect it in this order:
   - If your live tool list contains tools named `ads_*` (for example
     `ads_get_ad_accounts`, `ads_create_campaign`, `ads_create_ad`, under
     the runtime's registered prefix; see Tool naming above), the Meta MCP
     is connected: use the MCP backend.
   - Otherwise, in the terminal, run `meta auth status`; if it reports a
     token, run `meta ads adaccount list --output json`. If that returns
     accounts, the Meta Ads CLI is configured: use the CLI backend.
   - If neither works, stop and tell the user Meta is not connected yet
     (the pack's SETUP.md Step 4 covers both routes).

   `meta_backend` in the setup-state file records what setup found; the
   live check above wins when they disagree, and you say so.

   If both are available, the MCP is the primary backend (broader surface:
   previews, diagnostics, field help, `ads_get_errors`), and the CLI
   carries the two operations the MCP cannot do today: uploading a local
   file and building one flexible creative that holds the whole copy pool
   (Steps 2 and 3). Say once which backend you are using and which
   operations the CLI will carry, then proceed; do not switch backends in
   the middle of a create sequence without telling the user. Names drift
   between versions: trust your live tool list over the MCP tool names
   written in this file, and trust `--help` output over the CLI flags
   written here.

   **Known MCP blocker (not a credential problem).** If every Meta MCP call
   fails with a bare "Server returned an error response" and a lower-level
   log shows HTTP 400 / JSON-RPC `-32602` with a message like
   `"meta" for Request must be an dict or null`, the MCP client is sending
   `params._meta: {}` and Meta's server rejects it. That is an interop
   defect between the Hermes MCP client and Meta's server, not a token
   problem: detect the signature, stop calling the MCP, do not regenerate
   tokens, do not patch Hermes or its packages, and use the CLI route for
   this run (or wait for the upstream fix). Say which you did.

   On the CLI route, the `AD_ACCOUNT_ID` in the workspace `.env` (the `act_`
   form) must match the ad account in BRAND.md, or pass
   `--ad-account-id <act_ID>` on each command. `meta ads adaccount current`
   shows which account the CLI is pointed at.
3. **Read the user's `BRAND.md`** at the workspace root. You need the
   "## Meta Assets" section (ad account name and ID, Page ID, Instagram
   account ID, pixel ID, default campaign objective, default conversion
   event, default CTA), the landing page URL from "## Offer", and the
   "## Budget Guardrails" section. **This is a strict gate.** If `BRAND.md`
   is missing or any of those sections is empty, do not proceed on
   run-local files or values pulled from chat. Offer two ways forward: run
   the `brand-setup` skill first (the default), or an **explicit, validated
   run-scoped override**: the user supplies every required field (ad
   account name and ID, Page ID, destination URL, objective, conversion
   event and pixel when optimizing for conversions, CTA, daily spend cap),
   you show the full set back, the user approves it in so many words, you
   record it in the run ledger as `brand_override` with the approval
   wording, and you offer to merge it into `BRAND.md` at the end of the
   run. A silent bypass is never an option; a launch that ran without
   `BRAND.md` and without a recorded override is a defect.
4. **Have the finished creative available.** A local image or video file, or
   an already uploaded Meta image hash / video ID. If the creative only
   exists as a chat attachment, save it to a real file path first. Note for
   each asset whether it is a local file or a public URL; that decides
   which backend can upload it (Step 2).
5. **Have the copy pool.** The standard input is the "Ad copy handoff" block
   from the `human-ad-copy` skill: 5 primary texts, 5 headlines, 3
   descriptions, a CTA type, and a validator result. If the copy has not been
   through that skill, invoke it now rather than launching unvalidated copy.
   Having the block is not approval: the Copy approval gate below still
   runs.

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
| Upload image / video | `ads_creative_upload_image` / `ads_creative_upload_video` (public URLs only, never a local path; check your live tool list, and treat a "this tool is new and is being gradually rolled out" reply as unavailable for this account, not as bad credentials) | no separate step; `meta ads creative create --image ./file` or `--video ./file` uploads the local file itself |
| Create creative | `ads_create_creative` (scalar `message` / `headline` / `description`; no `asset_feed_spec`, so it cannot build the one flexible 5 / 5 / 3 creative this pack requires; route that creative to the CLI, or the user explicitly accepts a single variant) | `meta ads creative create --name "<name>" --page-id <PAGE_ID> [--instagram-actor-id <IG_ID>] --image ./file --bodies "<primary 1>" --bodies "<primary 2>" ... --titles "<headline 1>" --titles "<headline 2>" ... --descriptions "<description 1>" ... --link-url <URL> --call-to-action <CTA> --output json` (repeat each plural flag once per value, or `--asset-feed-spec @feed.json`; singular `--body/--title/--description` only for a user-accepted single variant; for video, `--video ./file` with no `--image`, the cover is auto-generated) |
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
flag is marked UNVERIFIED, `--help` decides. A field that neither the live
MCP schema nor the installed CLI can write cannot be mirrored on this
setup: say so in the plan and list it as a delta in the verify report. The
Graph API is read-only in this pack; there is no Graph write fallback.

| Purpose | Meta MCP tool | Meta Ads CLI command |
|---|---|---|
| Read a reference entity with exact fields (Tier B / C) | `ads_get_ad_entities` with `fields` at campaign / adset / ad level (Tier C, partial: no `attribution_spec`, `frequency_control_specs`, `bid_constraints`, `special_ad_categories`, or creative specs; normalize per the reference doc section 5); `ads_get_creatives` with `creative_ids` (flattened, no `degrees_of_freedom_spec`, `asset_feed_spec`, `url_tags`) | `meta ads <resource> get <ID> --fields <list> --output json` (Tier B, complete for campaign / adset / ad); `meta ads creative get <ID> --output json` (whether it returns `degrees_of_freedom_spec` and `asset_feed_spec` is UNVERIFIED; use Tier A for creatives) |
| Graph direct read (Tier A, both backends) | no MCP tool; `source .env && curl -s "https://graph.facebook.com/v25.0/<ENTITY_ID>?fields=<list>&access_token=$ACCESS_TOKEN"` from the workspace root, Route B token, GET only (reads and diagnostics; never a write or an upload), token never printed | same command |
| Create campaign copying a reference (PAUSED) | `ads_create_campaign` with `source_campaign_id` plus `name`, `objective`, `buying_type`, `bid_strategy`, `special_ad_categories`, `special_ad_category_country`, `spend_cap`, `pacing_type`, `smart_promotion_type`, `daily_budget` or `lifetime_budget` (CBO only), `status: PAUSED` | `meta ads campaign create --name "<name>" --objective <OBJECTIVE> [--bid-strategy <STRATEGY>] [--daily-budget <minor units>] [--lifetime-budget <minor units>] [--pacing-type <TYPE>] [--special-ad-categories ...] --status PAUSED --output json` (one budget flag at most, CBO only); copy-from (`source_campaign_id`) flag UNVERIFIED on 1.1.0 |
| Create ad set copying a reference (PAUSED) | `ads_create_ad_set` with `source_adset_id`, `campaign_id`, `name`, `targeting` (raw JSON), `promoted_object`, `attribution_spec`, `optimization_goal`, `billing_event`, `bid_strategy`, `bid_amount`, `bid_constraints`, `frequency_control_specs`, `adset_schedule`, `is_dynamic_creative`, `dsa_beneficiary`, `dsa_payor`, `destination_type`, `pacing_type`, budget (ABO only), `status: PAUSED`; placements via `targeting` keys, or `placement` / `placement_soft_opt_out` | `meta ads adset create <CAMPAIGN_ID> --name "<name>" --optimization-goal <GOAL> --billing-event <EVENT> [--bid-strategy <STRATEGY>] [--bid-amount <minor units>] [--daily-budget <minor units>] --targeting @targeting.json --promoted-object @promoted.json (or `--pixel-id <ID> --custom-event-type <EVENT>`) --attribution-spec '<json>' [--dsa-beneficiary <ID> --dsa-payor <ID>] --status PAUSED --output json`; `--targeting '<json>'` inline also works; flags for `frequency_control_specs`, `bid_constraints`, `adset_schedule`, `is_dynamic_creative`, and copy-from (`source_adset_id`) UNVERIFIED on 1.1.0 |
| Create creative with mirrored enhancements | `ads_create_creative` with the identity, media, copy, link, and CTA fields plus `degrees_of_freedom_spec` as a JSON string (shortcuts `advantage_plus_creative`, `advantage_plus_creative_features`) and `instagram_user_id`; no `asset_feed_spec` (single variant only) and no `url_tags` parameter (UNVERIFIED whether inline `creative` JSON on `ads_create_ad` passes `url_tags` through) | `meta ads creative create --name "<name>" --page-id <PAGE_ID> [--instagram-actor-id <IG_ID>] --object-story-spec @spec.json --degrees-of-freedom-spec @dof.json [--url-tags "<tags>"] [--contextual-multi-ads <value>] [--authorization-category <value>] [--applink-treatment <value>] [--asset-feed-spec @feed.json] --output json`; when the media is a local file, replace `--object-story-spec @spec.json` with `--image ./file` or `--video ./file` plus the copy, link, and CTA flags (`--asset-feed-spec` shortcuts: `--bodies`, `--titles`, `--descriptions`, `--images`, `--videos`, `--call-to-actions`) |
| Create ad with mirrored tracking (PAUSED) | `ads_create_ad` with `adset_id`, `name`, `creative` (`creative_id`), `tracking_specs`, `conversion_domain`, `source_ad_id` (draft mode), `status: PAUSED` | `meta ads ad create <AD_SET_ID> --name "<name>" --creative-id <CREATIVE_ID> --tracking-specs '<json>' --conversion-domain <domain> --status PAUSED --output json`; copy-from (`source_ad_id`) flag UNVERIFIED on 1.1.0 |
| Verify after create (read back) | same read tools as the reference read, Tier A preferred | same |
| Retire run-owned objects (gated, read back `DELETED`) | `ads_update_entity` (status `DELETED`, if the live schema offers it) for ads; `ads_creative_delete` for creatives; media delete only if a tool exists in the live list | `meta ads ad delete <ID> --output json`; `meta ads creative delete <ID> --output json`; media delete per `--help` |

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

- [ ] **Workspace root:** resolved from the setup-state file (Prerequisites
      1); `BRAND.md` read from it (or a recorded run-scoped override), and
      `ad-runs/` writable there.
- [ ] **Ad account, by name AND ID:** confirmed via `ads_get_ad_accounts`
      (MCP) or `meta ads adaccount list --output json` (CLI); match both
      the display name and the `act_` ID against BRAND.md. Accounts with
      identical display names exist in real businesses, so a name match
      alone is never a selection; if the user has several accounts, show
      name and ID side by side and ask which one. On the CLI, also confirm
      `AD_ACCOUNT_ID` (or `--ad-account-id`) points at that same ID.
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
- [ ] **Copy approved verbatim:** the human-ad-copy handoff block exists,
      the validator passed (or the manual checklist was applied and
      disclosed), and the Copy approval gate below has passed:
      `copy_pool_hash` and the user's approval wording are in the run
      ledger.
- [ ] **Creative file(s):** file path (or public URL), format, and aspect
      ratio noted; per asset, which backend uploads it (Step 2 capability
      gate) and which backend builds its creative (Step 3).
- [ ] **Pixel / conversion event:** from BRAND.md's "## Meta Assets"
      section, if the objective is conversions.
- [ ] **Special Ad Category:** if the offer touches credit, employment,
      housing, or social issues and politics, flag it; the campaign must
      declare it and targeting options narrow. Ask the user rather than
      guessing.

If any line fails, resolve it before continuing.

## Copy approval gate (before any create)

Media approval, plan approval, and "go build it" do not approve copy. A
real launch once built a 5 / 5 / 3 pool on the strength of "Get these
built" after an approval form timed out; that is the failure this gate
exists to prevent. Nothing is created (no campaign, no ad set, no upload,
no creative) until this gate has passed in the current conversation.

1. **Show the whole pool verbatim.** One message, plain text, nothing
   paraphrased or truncated: every primary text (numbered 1 to 5), every
   headline (1 to 5), every description (1 to 3), the CTA type, the
   destination URL, and the media pairing (which file or asset ID gets this
   pool; with several media assets, the same pool on each unless the plan
   says otherwise). Surface every validator warning from the human-ad-copy
   handoff next to the line it concerns, plus any field-length problem you
   can already see (Meta truncates or rejects over-length text).
2. **Write the canonical pool file** to the run folder as
   `ad-runs/<run>/copy-pool.txt` (UTF-8, LF line endings, no trailing
   whitespace), in this fixed order so the hash is reproducible:

   ```
   PRIMARY 1: <text>
   ...
   PRIMARY 5: <text>
   HEADLINE 1: <text>
   ...
   HEADLINE 5: <text>
   DESCRIPTION 1: <text>
   ...
   DESCRIPTION 3: <text>
   CTA: <TYPE>
   DESTINATION: <URL>
   MEDIA: <file name or asset id>   (one MEDIA line per asset)
   ```
3. **Compute the content hash** of that file and show it:

   ```
   shasum -a 256 ad-runs/<run>/copy-pool.txt
   # or
   python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' ad-runs/<run>/copy-pool.txt
   ```
4. **Ask for approval of exactly that text**, naming the hash: "Approve
   this copy pool as shown (sha256 <first 12 characters>)?" Wait for an
   explicit yes about the copy. "Looks good", "go", "build it", "get these
   built", a thumbs-up on the media, or approval of the plan summary are
   not copy approval; ask again in plain words. A form or button that
   timed out is not approval either.
5. **Record it in the ledger** (Run ledger below): `copy_pool_hash`
   (`sha256:<hex>`), `copy_approval.wording` (the user's approval message,
   verbatim), and `copy_approval.at`. The ledger stores the hash and the
   approval note only, never the pool text itself.
6. **Any change invalidates the approval.** If a single character of any
   line changes later (a validator fix, a field-length cut, a new CTA, a
   different URL, another media pairing), rewrite `copy-pool.txt`,
   recompute the hash, and run the gate again. Before every creative
   create, recompute the hash of the file you are about to map into fields
   and compare it to `copy_pool_hash` in the ledger; a mismatch stops the
   build.

## Run ledger (before the first mutation)

Every launch owns a run folder `ad-runs/<YYYY-MM-DD>-<slug>/` at the
workspace root, and inside it `ledger.json`. `ad-runs/` holds real entity
IDs and is gitignored; it is never committed and never pasted into chat in
full. The ledger is the only durable record of what this run created. A
real build once created media, a campaign, an ad set, and an image
creative before a video creative failed, and a later cleanup missed the
creative objects because nothing had written them down. So:

1. **Write the ledger before the first mutation**, right after the plan
   (Step 1) and the copy pool are approved and before any upload or
   create:

   ```json
   {
     "schema_version": 1,
     "run_key": "<YYYY-MM-DD>-<slug>",
     "created_at": "<ISO timestamp>",
     "workspace_root": "<absolute path>",
     "backend": "mcp | cli",
     "creative_backend": "mcp | cli",
     "ad_account": { "name": "<name>", "id": "act_<id>" },
     "plan": {
       "destination_path": "existing | mirror | new",
       "campaign": { "name": "...", "id": "<existing id or null>", "objective": "..." },
       "ad_set": { "name": "...", "id": "<existing id or null>", "daily_budget_minor_units": 0 },
       "media_assets": [ { "label": "<file name or asset id>", "kind": "image | video", "source": "local | url | existing" } ],
       "variants_per_creative": { "bodies": 5, "titles": 5, "descriptions": 3 },
       "expected_creatives": 0,
       "expected_ads": 0,
       "reference": { "campaign_id": null, "adset_id": null, "ad_id": null }
     },
     "plan_approval": { "wording": "<verbatim>", "at": "<ISO timestamp>" },
     "copy_pool_hash": "sha256:<hex>",
     "copy_approval": { "wording": "<verbatim>", "at": "<ISO timestamp>" },
     "brand_override": null,
     "objects": [],
     "events": []
   }
   ```

   `expected_creatives` and `expected_ads` both equal the number of media
   assets (one flexible creative and one ad per asset). If the user
   explicitly accepted a single-variant creative for an asset (Step 3),
   record that asset's override and the user's wording in `events`.
2. **Append every returned ID immediately**, in the same turn the tool
   returns it and before the next call, as an entry in `objects`:
   `{ "type": "image | video | campaign | adset | creative | ad", "id":
   "...", "name": "...", "status": "PAUSED | created | processing | ACTIVE
   | DELETED", "backend": "mcp | cli", "created_at": "<ISO>", "verified":
   false }`. A failed call is an event (`{ "at", "event": "create_failed",
   "type", "error" }`), never a silent retry. Update `status` and
   `verified` after the read-back in Step 5.
3. **On any retry or resumed session, read first, create second.** Read
   the ledger, then read the remote state (the ad set's ads and the
   account's creatives and media by name: `ads_get_ad_entities`,
   `ads_get_creatives`, `ads_get_ad_images`, `ads_get_ad_videos` on the
   MCP; `meta ads ad list`, `meta ads creative list` on the CLI), and
   reconcile: an object in the ledger that exists remotely is reused; an
   object that exists remotely under this run's name but is missing from
   the ledger is appended, not re-created. Transport ambiguity (a timeout,
   a bare "Server returned an error response", a WebUI "Session expired,
   reload the page" during a write) means read back, never re-create.
4. **Duplicate identical build requests resume the existing run.** Before
   opening a new ledger, scan `ad-runs/*/ledger.json` for a run with the
   same `ad_account.id`, the same `copy_pool_hash`, the same media labels,
   and the same destination that is not marked `completed` or `retired`.
   If one exists, tell the user and continue that run from its ledger
   (step 3 above) instead of starting another. A resent form on the
   Hostinger WebUI after a "Session expired" notice, a re-run cron job, or
   the user repeating "build it" after a page reload therefore cannot
   create a second set of ads.
5. **Close the run** by writing `completed_at` and the final assertion
   from Step 5 (`"final_assertion": { "non_deleted_ads": N,
   "run_owned_creatives": N, "asserted_at": "<ISO>" }`) once everything
   has been read back.

Every cron job that touches a run (reporting, retirement) sets an explicit
absolute working directory (the `workspace_root` from the setup-state
file) and opens the ledger by path; nothing about the run lives only in a
conversation.

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
the pick back: account (name and ID), campaign, ad set, and destination
URL. The wrong hierarchy spends the wrong budget, so this confirmation is
worth ten seconds.

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
     the raw JSON in the run folder (`ad-runs/<run>/`, not in git, not in
     chat) for the cloning and verify steps. A live read does not create
     the `specs/` snapshot files; offer to run `account-audit` for that.
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

Then, with the run ledger already written (Run ledger, step 1), create
both with **PAUSED** status and append each returned ID to the ledger as
it arrives:

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
   with the approved pool inside it (CLI only; `ads_create_creative`
   cannot write it, and the pack's flexible-creative contract applies
   whether or not the reference was multi-variant).
9. Special ad categories carry over exactly.

The result is the **cleaned reference**: one JSON object per entity with
only writable fields, kept in the run folder (`ad-runs/<run>/`, never in
git, never in chat) so the verify step can diff against it.

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
- Creative: on a mirror the creative still follows the Step 3 contract
  (one flexible creative per media asset carrying the whole approved
  pool), so it is built on the CLI: `meta ads creative create` with the
  media, `--asset-feed-spec @feed.json` (the reference's structure with
  the approved copy, or the plural shortcut flags), and
  `--degrees-of-freedom-spec @dof.json` carrying the mirrored enrollment
  verbatim, plus `--url-tags`, `--contextual-multi-ads`, and
  `--instagram-actor-id` as the reference had them. **MCP limitation:**
  `ads_create_creative` takes no `asset_feed_spec` (scalar text fields
  only) and no `url_tags`; whether inline `creative` JSON on
  `ads_create_ad` passes `url_tags` through is UNVERIFIED. It does take the
  mirrored `degrees_of_freedom_spec` as a JSON string (the shortcuts
  `advantage_plus_creative` and `advantage_plus_creative_features` exist,
  but the full spec is the exact mirror), so it is only the right tool
  for a creative the user has explicitly accepted as single-variant
  (Step 3). Never split the pool across several ads to fit the MCP. If
  the CLI is not installed, stop before the creative and give the user
  the two Step 3 choices; if `url_tags` cannot be written on the backend
  in use, tell the user the tags were not mirrored and list them as a
  delta in the verify report. Never drop them silently.
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
  `--help`; if it is missing, report the unset `source_campaign_id` as a
  known delta (provenance is a nice-to-have; the mirrored settings are
  what the verify step proves).
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
  copy-from `source_adset_id` are UNVERIFIED on 1.1.0: check `--help`. A
  field with no flag cannot be written on the CLI route; if the MCP is
  also connected and its live schema takes the field, create that entity
  there and say so; otherwise the field is not mirrored: list it in the
  plan as a gap and in the verify report as a delta.
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
  `--description` or their plural forms, each plural flag repeated once
  per value, `--link-url`, `--call-to-action`) together with
  `--degrees-of-freedom-spec @dof.json` and the same optional flags. With
  `--video`, no `--image` unless the user supplied a custom thumbnail. The
  whole approved pool goes in as one flexible creative: `--asset-feed-spec
  @feed.json` carrying the reference's structure (when it had one) with
  the approved copy and new media, or the plural shortcuts `--bodies`,
  `--titles`, `--descriptions`, `--images`, `--videos`,
  `--call-to-actions`, repeated once per value (the same field).
- Ad:
  `meta ads ad create <AD_SET_ID> --name "<name>" --creative-id
  <CREATIVE_ID> --tracking-specs '<json>' --conversion-domain <domain>
  --status PAUSED --output json`. The copy-from flag (`source_ad_id`) is
  UNVERIFIED on 1.1.0; same handling as the campaign.

**No Graph writes.** For a field that neither the live MCP schema nor the
installed CLI exposes (examples: `frequency_control_specs` or `source_*`
on a CLI whose `--help` lacks the flag; `url_tags` on an MCP-only setup),
the field cannot be mirrored on this setup. Do not POST it to the Graph
API with the Route B token: in this pack that token reads (Tier A) and
never writes. Say so in the plan before creating, list the field as a
delta in the verify report, and offer the fix (install the other backend,
or set the field by hand in Ads Manager after the paused entity exists).
For `asset_feed_spec` on an MCP-only setup the Step 3 contract applies:
stop before the creative and let the user choose.

## Step 2: Upload the media

**Media capability gate (run it before the first upload).** Decide, per
asset, which backend can carry it, and say so:

1. **Check the live tool list** for the upload tools
   (`ads_creative_upload_image`, `ads_creative_upload_video`, sometimes a
   combined `ads_creative_upload_media`, under the runtime's registered
   prefix). Absence means the MCP cannot upload in this session.
2. **A reply such as "This tool is new and is being gradually rolled out"**
   means the upload tool is unavailable for this ad account, not that the
   credentials are bad. Do not regenerate tokens, do not retry, do not
   reconnect the server; record the message in the ledger `events` and
   route the upload to the CLI.
3. **The MCP upload tools take public URLs only.** A local file path never
   works: the server downloads the bytes itself, and Google Drive,
   Dropbox, and similar share links fail because they return a sign-in
   page. Arcads asset URLs from the Arcads MCP result are public and work.
4. **A local file goes through the CLI**: `meta ads creative create
   --image ./file` or `--video ./file` uploads it as part of creating the
   creative (Step 3), so on the CLI there is no separate upload step.
5. **If the MCP cannot upload the asset and the CLI is not installed,
   stop.** Offer exactly two choices: install and configure the CLI route
   for creatives (the pack's SETUP.md Step 4, Route B; the CLI takes a
   system user token), or provide a direct, publicly reachable URL for
   the file. Never improvise a Graph API upload with the Route B token,
   never guess a URL, and never substitute a different file or an asset
   from another ad.

**MCP upload (public URLs).** Pass the URL to `ads_creative_upload_image`
(`image_url`) or `ads_creative_upload_video` (`video_url`). Keep the
returned image hash or video ID and append it to the ledger at once. Video
processing is asynchronous on Meta's side: after the video upload, poll
`ads_get_ad_videos` with `video_ids` and `fields: ["status", "picture"]`
until `status.video_status` is `ready` before creating the creative. Do
not create the ad the same second the upload returns.

**CLI upload (local files).** No separate step; the upload happens inside
`meta ads creative create` (images: .jpg .jpeg .png .gif .bmp .webp;
videos: .mp4 .mov .avi .mkv .wmv). The video-processing caution still
applies: if `meta ads ad create` fails with a video-processing error,
wait, read the ledger and list the ad set's ads (`meta ads ad list
--output json`) to confirm nothing was created, then retry the ad create
only. Do not re-run the creative create; that would upload the video
again and leave a duplicate creative.

**Video cover rule (both backends).** The cover is the video's own frame:
Meta's preferred thumbnail (the `picture` that `ads_get_ad_videos` returns
once the video is `ready`, or the auto-generated thumbnail on the CLI) or
a frame the user chose and supplied as a file. Never an unrelated image,
never the image from another ad, never an image ad's hash.

- MCP: prefer creating the ad through `ads_create_ad` with an inline
  `object_story_spec` whose `video_data` carries `video_id`, the copy, the
  link, and the CTA and **no** `image_hash` or `image_url`; the tool
  auto-generates the thumbnail from the video. If `ads_create_creative`
  requires a thumbnail for a video ad, pass the video's own `picture` URL
  from `ads_get_ad_videos` as `image_url`. (On this pack a video creative
  that carries the full copy pool is built on the CLI anyway; see Step 3.)
- CLI: `--video ./file` alone; the thumbnail is auto-generated. Add
  `--image` next to `--video` only when the user supplied a custom
  thumbnail file, and then that file, and only that file, is the cover.
- **Verify the processed thumbnail before reporting success.** After the
  ad exists, fetch a preview (`ads_get_ad_preview` on the MCP, feed
  format) and look at the rendered cover: it must be a frame of this
  video. If you can view images, say what you saw; if you cannot, ask the
  user to open the preview and confirm the cover before you call the
  launch done. On the CLI route (no preview tool), ask the user to confirm
  the thumbnail in Ads Manager and record their answer in the ledger. A
  cover you did not verify is reported as "cover: unverified", never as
  done.
- If the user provided a thumbnail, use it. If not, say in the report that
  the cover was auto-generated from the video and offer to swap in a
  user-chosen frame.

You can list what already exists in the account with `ads_get_ad_images`
and `ads_get_ad_videos` (MCP) when the user wants to reuse previously
uploaded media; a reused asset is still recorded in the ledger with
`"source": "existing"` so retirement knows not to delete it.

## Step 3: Build the creative

**The contract: one flexible creative per media asset.** Each approved
image or video becomes exactly one creative whose `asset_feed_spec`
carries all 5 primary texts (`bodies`), 5 headlines (`titles`), and 3
descriptions (`descriptions`) from the approved pool, plus the link and
the CTA. Meta then tests the combinations inside that one ad unit. Never
reduce the pool to one variant on your own, and never build one ad per
variant: five ads with one text each is not what "5 primary texts and 5
headlines" means, and it multiplies the ad count the user approved.

**Which backend builds it.** Check the live schema first:

- `ads_create_creative` on the MCP takes scalar `message`, `headline`, and
  `description` fields and has no `asset_feed_spec` parameter (verified on
  the current server; re-check your live schema, because a later server
  version may add it). Unless your live schema shows an `asset_feed_spec`
  (or an equivalent multi-value) input, the MCP cannot build the flexible
  creative.
- The CLI can: `meta ads creative create` with each plural flag repeated
  once per value, or `--asset-feed-spec @feed.json`.

So, **before creating anything for this asset**:

1. If the MCP route is primary and the CLI is installed (`meta auth
   status` reports a token and `meta ads adaccount list --output json`
   returns the same account, by ID), build this creative on the CLI and
   say so once ("creatives go through the Meta Ads CLI because the MCP
   cannot carry the copy pool"). Record `creative_backend: cli` in the
   ledger. The campaign, ad set, ad, preview, and verification can stay on
   the MCP.
2. If the CLI is not installed, **stop before creating anything** and
   offer exactly two choices:
   - install and configure the Meta Ads CLI route for creatives (the
     pack's SETUP.md Step 4, Route B: a system user token, which the CLI
     accepts even though the hosted MCP rejects it), then continue; or
   - explicitly accept a **single-variant creative** for this asset
     (primary text 1, headline 1, description 1, or the three the user
     names), recorded in the ledger `events` with the user's wording and
     shown as "1 / 1 / 1 at the user's explicit choice" in the report.

   "Just do what you can" is not a choice of the second option; ask
   plainly. Do not offer a third option that changes the ad count.
3. Recompute the hash of `copy-pool.txt` and compare it to
   `copy_pool_hash` in the ledger before mapping any text into a flag or a
   parameter. A mismatch stops the build (Copy approval gate, step 6).

**CLI:** run `meta ads creative create` with the approved inputs mapped
onto its flags:

```
meta ads creative create --name "<name>" --page-id <PAGE_ID> \
  [--instagram-actor-id <IG_ID>] \
  --image ./file \
  --bodies "<primary 1>" --bodies "<primary 2>" --bodies "<primary 3>" \
  --bodies "<primary 4>" --bodies "<primary 5>" \
  --titles "<headline 1>" --titles "<headline 2>" --titles "<headline 3>" \
  --titles "<headline 4>" --titles "<headline 5>" \
  --descriptions "<description 1>" --descriptions "<description 2>" \
  --descriptions "<description 3>" \
  --link-url <URL> --call-to-action <CTA> --output json
```

- **Identity:** `--page-id <PAGE_ID>` is required; add
  `--instagram-actor-id <IG_ID>` when the ID is known.
- **Asset:** `--image ./file` or `--video ./file` (the upload happens here,
  see Step 2). With `--video`, no `--image` unless the user supplied a custom
  thumbnail (Step 2 cover rule).
- **Link and CTA:** `--link-url <URL>` and `--call-to-action <CTA>`.
- **Text: repeat each plural flag once per value.** `--bodies` (max 5),
  `--titles` (max 5), and `--descriptions` (max 5) are repeated flags,
  exactly as Meta's CLI docs show them: `--titles "A" --titles "B"`.
  Putting several values after a single flag (one `--titles` followed by
  both quoted values) is wrong: the CLI keeps only the first value and
  rejects the rest as unexpected arguments. Written correctly, the 5 / 5 / 3 pool fits in one creative.
  The equivalent long form is `--asset-feed-spec @feed.json`, where
  `feed.json` in the run folder holds `bodies`, `titles`, `descriptions`,
  `link_urls`, `call_to_action_types`, and the media reference; use it
  when a mirror carries the reference's full `asset_feed_spec` structure
  (Step 1 cloning rules). Flag spellings come from `--help` in the
  installed version.
- **If the command fails, stop and show the user the exact error and the
  exact command** before doing anything else. Check `--help` for the flag
  spelling in the installed version and fix that if it is the cause. Do
  not fall back to a single variant on your own and do not split the pool
  across several ads: the only alternatives are the ones in the contract
  above (fix the CLI call, or the user explicitly accepts a single-variant
  creative), and the report says exactly how many variants were attached.

**MCP (a user-accepted single-variant creative, or a server whose live
schema exposes `asset_feed_spec`):** call `ads_create_creative` after
checking its live parameter schema, mapping:

- **Identity:** the Page ID, plus the Instagram account when available.
- **Asset:** the image hash (image ad), or the video ID with the cover
  sourced per the video cover rule in Step 2 (the inline
  `object_story_spec` path that auto-generates it, or the video's own
  `picture`).
- **Link and CTA:** the destination URL and the CTA type from the copy
  handoff (for example `LEARN_MORE`, `SHOP_NOW`, `SIGN_UP`).
- **Text:** the single `message`, `headline`, and `description` the user
  chose, recorded in the ledger. If the live schema does expose an
  `asset_feed_spec` (or a multi-value) parameter, pass the full pool
  through it instead and treat the read-back assertion in Step 5 as the
  proof that it landed.

**Mirror mode:** the creative also carries the reference's
`degrees_of_freedom_spec` verbatim (`--degrees-of-freedom-spec @dof.json`
on the CLI; `degrees_of_freedom_spec` as a JSON string on
`ads_create_creative`), plus `url_tags`, `contextual_multi_ads`,
`instagram_user_id`, and the CTA type unless the brief changed them; see
the Cloning rules in Step 1 for the exact mapping and the MCP limitation
on `asset_feed_spec` and `url_tags`. Do not "improve" the enrollment: an
`OPT_OUT` in the reference stays `OPT_OUT`, and an absent spec stays
absent (platform defaults), because matching the reference is the point.

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
backend takes it) as the Cloning rules describe. One creative per ad, one
ad per media asset: the number of ads equals `expected_ads` in the ledger,
never more. If the user approved multiple media assets, repeat Steps 2 to
4 per asset in the same ad set unless the plan said otherwise. Append the
ad ID to the ledger the moment it returns.

If creation fails, read the error carefully and fix the actual cause. On
the MCP, check `ads_get_errors` for account-level problems. On the CLI, the
command prints the API error itself (exit code 4 is an API error, 3 is an
authentication error); for an ad that was created but is flagged, read
`effective_status` and `issues_info` from
`meta ads ad get <ID> --output json` (the same `get` works on the ad set
and campaign). Do not blind-retry a mutation; a retry after an ambiguous
failure can create duplicates. Read the ledger, then list the ad set's
ads (`ads_get_ad_entities` or `meta ads ad list --output json`) to see
whether the ad actually got created (Run ledger, step 3); a transport
error is read back, never re-sent.

## Step 5: Verify after create

A mirror is only exact if you check it, so this step runs before any
preview or report. On the existing-structure and broad paths it is short:
read each created entity back (`ads_get_ad_entities` / `ads_get_creatives`
on the MCP, `meta ads <resource> get <ID> --output json` on the CLI),
confirm `status` is `PAUSED`, the parent ids are the ones in the plan, and
the ad points at the creative you built, and report anything that differs.

**Flexible creative assertion (every path).** For each run-owned creative,
read `asset_feed_spec` back and assert it holds exactly 5 `bodies`, 5
`titles`, and 3 `descriptions` (or the single variant the user explicitly
accepted). The read must come from a tier that returns the spec: Tier A
(Graph read with the Route B token, GET only) or `meta ads creative get
<ID> --output json` on the CLI (whether it returns `asset_feed_spec` is
UNVERIFIED on 1.1.0; if the key is absent from its output, use Tier A).
`ads_get_creatives` on the MCP flattens the creative and cannot show the
spec, so on an MCP-only setup with no Route B token the assertion is
reported as `unverifiable on this tier`, never as passed, and the user is
asked to confirm in Ads Manager that the ad's text options list all five
primary texts and five headlines.

**Count assertion (every path).** List the ad set's ads and the account's
creatives by name, count the non-deleted ads and the run-owned creatives,
compare both to `expected_ads` and `expected_creatives` in the ledger, and
write the result into the ledger as `final_assertion`. A count that is
off (a duplicate from a retry, a creative created before a failed ad) is
reported with the extra IDs and handed to the Retirement flow below; it is
never quietly accepted. Mark each verified object `"verified": true` in
the ledger.

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
Backend: MCP | CLI | MCP with creatives on the CLI
Run ledger: ad-runs/<run>/ledger.json (run key <run>)
Ad account: <name> (<act_ID>)
Destination path: existing | mirror of <reference campaign / ad set / ad, names and IDs> | new (broad)
Everything below is PAUSED. Nothing spends until you activate it.

| Entity | Name | ID | Status |
|---|---|---|---|
| Campaign | ... | ... | PAUSED (or "existing") |
| Ad set | ... | ... | PAUSED (or "existing") |
| Media | ... | <hash or video id> | uploaded (or "existing") |
| Creative | ... | ... | created |
| Ad | ... | ... | PAUSED |

- Copy pool: sha256 <first 12 characters>, approved "<approval wording>"
- Copy variants attached: 5 / 5 / 3 in one flexible creative per media asset (read back: confirmed | unverifiable on this tier, user to confirm in Ads Manager) | 1 / 1 / 1 at the user's explicit choice
- Ads: <N> non-deleted (expected <N>); creatives: <N> run-owned (expected <N>)
- Video cover: verified from preview | confirmed by user in Ads Manager | unverified
- Destination: <URL> | CTA: <type>
- Daily budget on activation: <amount> (BRAND.md cap: <cap>)
- Preview: <link, or "review in Ads Manager" on the CLI route>
- Verify after create: exact match | <N> deltas (table below) | unverified (<reason>)
- Mirror gaps (read tier limits) and fields no backend could write, if any: <list>

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
   and campaign), report the new statuses, and record the activation in
   the ledger (`status: ACTIVE` on each object, plus an `activated` event
   with the confirmation wording). Offer to set up monitoring with the
   `meta-performance-loop` skill and alerts with
   `ad-reporting-automations`.

Pausing an ACTIVE entity at the user's request also goes through
confirmation (state what will stop delivering), then `ads_update_entity`
(MCP) or `meta ads <campaign|adset|ad> update <ID> --status PAUSED` (CLI),
and the ledger records it.

## Retirement and cleanup (run-owned objects)

When the user asks to retire, undo, or clean up a run, or when the Step 5
count assertion finds extras, retire everything the run owns, not just
the ads. A real correction once retired three wrong paused ads and left
their creative objects ACTIVE in the account; this flow exists so that
does not happen again.

1. **Build the cleanup plan from the ledger plus a fresh remote read**:
   every run-owned ad, creative, and uploaded image or video (never an
   object recorded with `"source": "existing"`, and never a campaign or ad
   set that existed before the run unless the user names it by ID). List
   each with type, name, ID, and current remote status.
2. **Confirm the plan** with the user in this conversation, by ID. A
   cleanup is a mutation and gets the same explicit confirmation as a
   create.
3. **Delete bottom-up**: ads first (`ads_update_entity` with status
   `DELETED` if the live schema offers it, or `meta ads ad delete <ID>
   --output json` on the CLI), then creatives (`ads_creative_delete` or
   `meta ads creative delete <ID> --output json`), then media where the
   backend offers a delete (check the live tool list and `--help`; if no
   delete exists for media, say so and leave the asset, recorded as
   `retained`). On the CLI never pair `--no-input` with `--force` unless
   the user asked for that exact deletion by ID.
4. **Read back each object** and require the remote state to show
   `DELETED` (or "not found" where the API removes the object entirely)
   before marking it `DELETED` in the ledger with a timestamp. A delete
   call that returned without an error is not proof; the read-back is.
5. **Final assertion**: the exact count of non-deleted run-owned ads and
   creatives (target: 0 for a full retirement, or the number the user
   asked to keep), written to the ledger as `final_assertion` with
   `retired_at`, and reported to the user with the IDs that were removed
   and any that were retained.

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
  changes go back through `human-ad-copy`, then through the Copy approval
  gate again (new hash, new approval).
- **"Build it" taken as copy approval.** Plan approval, media approval, or
  a timed-out approval form never approve the copy pool. The gate needs
  the verbatim pool shown and a yes bound to its hash.
- **Splitting the pool into five ads, or quietly shipping variant 1.** One
  flexible creative per media asset carries the whole pool. If the backend
  cannot build it, stop and offer the two Step 3 choices; never change the
  ad count and never reduce the pool on your own.
- **Duplicate ads from retries.** After any ambiguous failure (a timeout,
  "Server returned an error response", a WebUI "Session expired" during a
  write), read the ledger and the remote state before re-creating. A
  repeated identical build request resumes the existing run.
- **Retiring ads but leaving their creatives.** Cleanup covers ads,
  creatives, and uploaded media, and each one is read back as `DELETED`.
- **Reading the MCP interop error as a token problem.** A bare "Server
  returned an error response" on every call, with `-32602` and `"meta"
  for Request must be an dict or null` underneath, is the client SDK's
  `params._meta` defect. Switch to the CLI; do not regenerate tokens.
- **"Gradually rolled out" read as bad credentials.** That reply from an
  upload tool means the tool is unavailable for the account. Route the
  upload to the CLI.
- **Losing the workspace between sessions.** Paths come from the
  setup-state file, never from conversation memory or the current
  directory; a cron job sets an explicit absolute workdir.
- **Picking an account by name alone.** Two accounts can share a display
  name; select and confirm by name and ID.
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
- **Improvising a Graph write.** The Route B token reads (Tier A) and
  never writes or uploads in this pack. A field or an upload that neither
  the MCP nor the CLI can carry is a stop-and-explain, not a curl POST.
- **Leaking the Route B token.** Tier A reads take the token from `.env`
  through the shell; the token is never echoed, logged, or pasted into
  chat, memory files, ledgers, or job prompts, and the expanded command
  line is never saved.
