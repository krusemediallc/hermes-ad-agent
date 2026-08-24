---
name: meta-ad-launcher
description: >-
  Launches finished ad creatives to Meta (Facebook and Instagram) through the
  official Meta Ads MCP server: picks or creates the destination campaign and
  ad set (always PAUSED), uploads the image or video, builds a creative from
  the approved human-ad-copy set (multi-variant text where the server supports
  it), creates the ad PAUSED, fetches a preview, reports every created ID back
  to the user, and holds a strict human-confirmation gate before any
  activation. Use it when the user says things like "launch this ad", "push
  this creative to Meta", "publish this as a Facebook ad", "create the
  campaign and ad set", "put this image live as an ad" (still created paused),
  "deploy these videos to my ad account", or "turn on / activate my paused
  ad". Do not use it to generate creative or write copy; those belong to the
  Arcads creative skills and human-ad-copy.
---

# Meta ad launcher

You turn an approved creative plus approved copy into real Meta ad objects,
in this fixed order:

**checklist → destination → upload media → creative → ad (PAUSED) → preview →
report IDs → separate explicit activation (only if asked)**

Nothing you create in this skill is ever ACTIVE. Creation and activation are
two different conversations with two different confirmations.

## Non-negotiable safety rails

1. **Everything is created PAUSED.** Campaigns, ad sets, and ads all get
   `PAUSED` status at creation. There is no exception, even if the user says
   "just make it live". Explain that activation is a separate step.
2. **Activation requires explicit confirmation in the current conversation.**
   Before calling `ads_activate_entity`, restate exactly which entities will
   go ACTIVE and what the daily budget will be, and wait for a clear yes.
   Approval given earlier in the workflow, or in a previous session, does not
   count.
3. **Budgets and spend settings never change without explicit confirmation.**
   Never call `ads_update_entity` to change a budget, bid, schedule, or
   status unless the user confirmed that exact change in this conversation.
4. **Never fabricate.** Report only IDs, statuses, and values the MCP tools
   actually returned. If a call failed or a field is missing, say so.

## Prerequisites

1. **Confirm the Meta Ads MCP server is connected.** Look at your actually
   available tool list for tools named like `ads_get_ad_accounts`,
   `ads_create_campaign`, `ads_create_ad`. Tool names and availability differ
   between server versions, so always trust your live tool list over the
   names written in this file. If no `ads_*` tools exist, stop and tell the
   user the Meta Ads MCP server needs to be connected first (see the pack's
   SETUP.md).
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

## Pre-launch checklist

Walk this list and show the user the filled-in result before creating
anything. Every line must be a value you verified, not a guess:

- [ ] **Ad account:** confirmed via `ads_get_ad_accounts` (match against the
      account in BRAND.md; if the user has several accounts, ask which one).
- [ ] **Facebook Page ID:** from BRAND.md, cross-checked with
      `ads_get_ad_account_pages` or `ads_get_user_pages`.
- [ ] **Instagram account:** from BRAND.md, cross-checked with
      `ads_get_ig_accounts`. Optional but recommended; without it the ad may
      not run with the brand's Instagram identity.
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

**Existing structure.** Use `ads_get_ad_entities` to list the account's
campaigns and ad sets (filter to ACTIVE and PAUSED so archived structure does
not clutter the choice). Present name, ID, objective, and status. The user
picks the target ad set. Confirm the pick back: account, campaign, ad set,
and destination URL. The wrong hierarchy spends the wrong budget, so this
confirmation is worth ten seconds.

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

Then call `ads_create_campaign` and `ads_create_ad_set` with **PAUSED**
status. Check each tool's live schema for exact parameter names before
calling; server versions differ. A paused ad set with a budget spends
nothing, but the budget number still needs the user's approval because it is
what activation will unleash later.

## Step 2: Upload the media

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

## Step 3: Build the creative

Call `ads_create_creative`. Check its live parameter schema first, then map
the approved inputs onto it:

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

Never edit the approved copy while mapping it into fields. If a field limit
forces a cut, go back to the user with the exact problem.

`ads_get_creatives` and `ads_creative_update` exist for inspecting and fixing
a creative; `ads_creative_delete` removes one created in error. Use
`ads_get_field_context` when a parameter's meaning is unclear and
`ads_get_help_article` for Meta's own documentation.

## Step 4: Create the ad, PAUSED

Call `ads_create_ad` with the target ad set ID, the creative ID, a clear ad
name (a good default: `<creative-slug> | <angle> | <date>`), and **PAUSED**
status. One creative per ad. If the user approved multiple creatives, repeat
steps 2 to 4 per creative in the same ad set unless the plan said otherwise.

If creation fails, read the error carefully, check `ads_get_errors` for
account-level problems, and fix the actual cause. Do not blind-retry a
mutation; a retry after an ambiguous failure can create duplicates. List the
ad set's ads first to see whether the ad actually got created.

## Step 5: Preview and report

1. Fetch a preview with `ads_get_ad_preview` (ask the user which placement
   format they want to see if the tool offers options; feed and story/reel
   are the useful defaults).
2. Report the launch in one block the user can keep:

```markdown
## Launch report: <campaign or ad name>
Everything below is PAUSED. Nothing spends until you activate it.

| Entity | Name | ID | Status |
|---|---|---|---|
| Campaign | ... | ... | PAUSED (or "existing") |
| Ad set | ... | ... | PAUSED (or "existing") |
| Creative | ... | ... | created |
| Ad | ... | ... | PAUSED |

- Copy variants attached: <5/5/3, or what the server allowed>
- Destination: <URL> | CTA: <type>
- Daily budget on activation: <amount> (BRAND.md cap: <cap>)
- Preview: <link or "attached above">
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
3. Only then call `ads_activate_entity` for each confirmed entity, bottom-up
   or top-down as the user chose.
4. Verify with `ads_get_ad_entities` and report the new statuses. Offer to
   set up monitoring with the `meta-performance-loop` skill and alerts with
   `ad-reporting-automations`.

Pausing an ACTIVE entity at the user's request also goes through
confirmation (state what will stop delivering), then `ads_update_entity`.

## Pitfalls

- **Wrong account or ad set.** Always confirm the hierarchy before mutating.
- **Video not processed.** The most common video-ad failure; wait and verify
  before creating the ad.
- **Tool name drift.** Server versions differ. If a tool named here is not in
  your live list, find the closest equivalent in your actual roster and say
  which one you used.
- **Silent copy edits.** The launcher launches; it does not rewrite. Copy
  changes go back through `human-ad-copy` and user approval.
- **Duplicate ads from retries.** After any ambiguous failure, list before
  re-creating.
- **Treating enthusiasm as approval.** The activation gate needs the restated
  entities and budget, then a yes.
