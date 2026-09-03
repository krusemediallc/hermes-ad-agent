---
name: meta-ad-launcher
description: >-
  Launches finished ad creatives to Meta (Facebook and Instagram) through
  whichever Meta backend is connected (Meta's official Ads MCP server or the
  official Meta Ads CLI): picks or creates the destination campaign and ad
  set (always PAUSED), uploads the image or video, builds a creative from
  the approved human-ad-copy set (multi-variant text where the backend
  supports it), creates the ad PAUSED, fetches a preview where the backend
  offers one, reports every created ID back to the user, and holds a strict
  human-confirmation gate before any activation. Use it when the user says
  things like "launch this ad", "push this creative to Meta", "publish this
  as a Facebook ad", "create the campaign and ad set", "put this image live
  as an ad" (still created paused), "deploy these videos to my ad account",
  or "turn on / activate my paused ad". Do not use it to generate creative
  or write copy; those belong to the Arcads creative skills and
  human-ad-copy.
---

# Meta ad launcher

You turn an approved creative plus approved copy into real Meta ad objects,
in this fixed order:

**checklist → destination → upload media → creative → ad (PAUSED) → preview →
report IDs → separate explicit activation (only if asked)**

Nothing you create in this skill is ever ACTIVE. Creation and activation are
two different conversations with two different confirmations.

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

**Existing structure.** List the account's campaigns and ad sets with
`ads_get_ad_entities` (MCP) or `meta ads campaign list --output json` and
`meta ads adset list --output json` (CLI; add `--status` filters). Filter to
ACTIVE and PAUSED so archived structure does not clutter the choice. Present
name, ID, objective, and status. The user picks the target ad set. Confirm
the pick back: account, campaign, ad set, and destination URL. The wrong
hierarchy spends the wrong budget, so this confirmation is worth ten
seconds.

**New structure.** Create it explicitly, and only after the user approves a
plan containing:

- campaign name and objective (default campaign objective from BRAND.md's
  "## Meta Assets" section, for example `OUTCOME_SALES` or `OUTCOME_LEADS`)
- special ad categories (usually an empty list, but always stated)
- budget location: campaign-level budget (CBO) or ad-set-level budget (ABO),
  and the daily amount, explicitly compared to the BRAND.md daily spend cap
- ad set name, targeting (keep it broad: countries, age range, optional
  gender; do not invent interests or custom audiences the user never asked
  for), and the conversion event plus pixel if optimizing for conversions

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
--status PAUSED --output json` (CLI). One creative per ad. If the user
approved multiple creatives, repeat steps 2 to 4 per creative in the same
ad set unless the plan said otherwise.

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

## Step 5: Preview and report

1. **MCP:** fetch a preview with `ads_get_ad_preview` (ask the user which
   placement format they want to see if the tool offers options; feed and
   story/reel are the useful defaults). **CLI:** there is no preview
   command, so the report line reads "Preview: review in Ads Manager
   (search the ad name or ID)".
2. Report the launch in one block the user can keep:

```markdown
## Launch report: <campaign or ad name>
Backend: MCP | CLI
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
```

3. Tell the user how to review it in Ads Manager and that they can activate
   either there or by asking you.

If this launch is part of an orchestrated campaign run (see the
`ad-agent-orchestrator` skill), also save this block as `launch.md` in the
run folder.

## Step 6: Activation (separate, gated, only on request)

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
