---
name: brand-setup
description: >-
  Guided brand interview that creates or updates BRAND.md, the brand profile
  every Hermes Ad Agent skill reads before doing research, creative, copy, or
  launches. It auto-discovers what it can first (ad accounts, Facebook Pages,
  and Instagram accounts through whichever Meta backend is connected, the Meta
  Ads MCP or the Meta Ads CLI, and records which Meta connection is live;
  products, actors, and voices through the Arcads MCP; brand voice drafted
  from the user's website when a web tool is available), then interviews the
  user for the rest: offer, audience, tone, claims and compliance rules,
  performance targets (target CPA or target ROAS plus the conversion event and
  default campaign objective), and budget guardrails including the Arcads
  credit budget per batch, the Meta daily spend cap, and the PAUSED-only
  acknowledgment. It writes BRAND.md to the workspace root (the repo clone
  directory recorded during setup) and reads it back for confirmation. Use it
  on first install, whenever BRAND.md is missing, when another skill routes
  the user here, or when the user says "set up my brand", "brand setup",
  "create my brand file", "onboard my business", "update my brand file",
  "change my brand voice", "we have a new offer", or "my spend cap changed".
---

# Brand setup

You are building `BRAND.md`, the single file every other Hermes Ad Agent
skill reads for brand context. It lives at the workspace root: the repo clone
directory recorded during setup (SETUP.md Checkpoint 1 records its absolute
path; the default is `~/hermes-ad-agent`). The structure to follow is the
canonical template, available from two equivalent sources: the skill-local
copy at `${HERMES_SKILL_DIR}/BRAND.template.md` and the repo-root copy at
`<workspace root>/BRAND.template.md`. Read whichever you find first; they are
identical. If neither file exists, write the schema yourself: an H1
`# BRAND.md: <Brand Name>` followed by exactly these H2 sections, in this
order: Business Basics, Offer, Audience, Voice and Tone, Claims and
Compliance, Meta Assets, Arcads Assets, Performance Targets, Budget
Guardrails, Creative Preferences, Setup Gaps, Changelog. Other skills parse
BRAND.md by these exact heading names.

**Demo mode.** To try the whole pack without a real brand, copy
`assets/demo-brand/BRAND.md` from the repo to the workspace root as
`BRAND.md` and skip the interview. The demo's reference images resolve at
`<workspace root>/assets/demo-products/`. Its landing URL is an example.com
placeholder; meta-ad-launcher requires a real URL before creating any ad
(Meta rejects example.com).

Two modes:

- **Create** when `BRAND.md` does not exist yet (first install, or a skill
  sent the user here). Run the full flow below.
- **Update** when `BRAND.md` exists and the user wants changes. Jump to
  "Update flow" at the bottom.

Ground rules for the whole flow:

- Never invent a value. A field you cannot discover or the user does not
  answer is written as `(not set)`, not guessed.
- Never store secrets. The MCP servers handle their own auth, and the Meta Ads
  CLI (Meta's official command-line tool for the Marketing API) keeps its
  token in a gitignored `.env`; BRAND.md holds business facts and the user's
  own account identifiers only, never a token, and only after the user
  confirms them.
- Keep the interview conversational: two or three questions per message, not
  a wall of twenty.

## Step 1: Discover before you ask

Do the automatic work first so the interview is short. Check your actually
available tool list before each block; tool names and availability differ
between MCP server versions, so verify against the live list rather than
assuming a documented name exists.

**Meta backend** (the Meta Ads MCP server or the Meta Ads CLI):

Detect which one is live before calling anything. If your live tool list
contains tools named `ads_*` (for example `ads_get_ad_accounts`), the Meta
MCP is connected: use it. Otherwise run `meta auth status` in the terminal;
if it reports a token, run `meta ads adaccount list --output json`, and if
that returns accounts the Meta Ads CLI is configured: use it. If both are
available, prefer the MCP. Say once which backend you are using. Trust the
live tool schema over the tool names written here, and trust `--help` output
over the CLI flags written here; server and CLI versions differ.

On the MCP route:

1. `ads_get_ad_accounts` to list the ad accounts the connected Meta login can
   use. If there are several, show them by name and ask which is the default
   for ad work.
2. For the chosen account, `ads_get_ad_account_pages` to find the Facebook
   Pages it can publish under (fall back to `ads_get_user_pages` if needed).
   Ask which Page is the default identity.
3. `ads_get_ig_accounts` to find linked Instagram accounts. Ask which one, if
   any, ads should publish under.

On the CLI route:

1. `meta ads adaccount list --output json` to list the ad accounts the system
   user can use. If there are several, show them by name and ask which is the
   default for ad work. The CLI's `AD_ACCOUNT_ID` (in the workspace `.env`,
   `act_` form) should be that default; if the user picks a different
   account, tell them to update `.env`, or that skills will pass
   `--ad-account-id` on each call.
2. `meta ads page list --output json` to find the Facebook Pages the system
   user was assigned. Ask which Page is the default identity.
3. The CLI has no Instagram account listing. Ask the user for the Instagram
   account ID (Meta Business Settings, Instagram accounts) or leave it
   `(not set)`.

Record the chosen names and IDs exactly as the tools returned them, only
after the user confirms each pick. Record the live backend as the "Meta
connection" field under "## Meta Assets": `mcp` or `cli`. If neither
backend is connected, write `(not set)` there, note it in the file's
"## Setup Gaps" section, and continue; the interview still works without
it.

**Arcads MCP** (tools named `arcads_*`), if its tools exist in this session:

1. `arcads_list_products` to see the products registered in the user's Arcads
   workspace. If there is exactly one, propose it as the default; if several,
   ask. `arcads_get_product` fills in the detail for the chosen one.
2. Note that actor and voice catalogs exist via `arcads_list_situations` and
   `arcads_list_voices`. Do not dump the whole catalogs into the interview;
   just ask whether the user already has preferred actors or voices, and
   record any they name. Creative skills browse the catalogs at generation
   time.

If the Arcads MCP is not connected, note it under "## Setup Gaps" and
continue.

**Website**, if the user has one and you have a web fetch or browser tool
available:

1. Ask for the URL, then offer to read the homepage and one or two key pages
   (pricing, about) to draft brand voice.
2. From what you read, draft: a one-line description, three to five tone
   adjectives, phrases the brand actually uses, and candidate claims you saw
   on the site.
3. Present the draft as a proposal. Everything drafted from the website must
   be confirmed or corrected by the user before it goes into BRAND.md.

## Step 2: Interview for the rest

Work through these seven areas, pre-filling anything discovery already
answered and asking only for what is missing.

1. **Offer.** What is being sold, price point, any current promo or
   guarantee, the primary call to action, and the default destination URL for
   ads.
2. **Audience.** Who buys, the main pain the offer solves, the outcome they
   want, how aware they already are of this kind of product, and anyone the
   ads should not target or speak to.
3. **Voice and tone.** Three to five adjectives, words and phrases to use,
   words and phrases to avoid, one or two example lines the user likes, and
   the emoji policy. If the website draft exists, refine it here.
4. **Claims and compliance.** Which claims may be made and what backs each
   one up, which claims are banned outright, whether the business falls into
   a regulated or Meta special ad category (credit, employment, housing,
   health, financial products, or similar), and any disclaimer that must
   appear. Be direct with the user: copy skills will refuse claims that are
   not on this list.
5. **Performance targets and Meta defaults.** At least one of target CPA or
   target ROAS is required; it is what the reporting and monitoring skills
   judge performance against. Also collect the default conversion event
   (Purchase, Lead, CompleteRegistration, or similar) and the default
   campaign objective (for example OUTCOME_SALES or OUTCOME_LEADS), plus an
   optional target CTR and any attribution notes. Write the targets under
   "## Performance Targets" and the conversion event, objective, and default
   CTA under "## Meta Assets".
6. **Budget guardrails.** All three are required and written into BRAND.md:
   - **Arcads credit budget per batch:** the maximum estimated credits a
     single creative batch may cost before the agent must stop and check in,
     over and above the normal per-generation confirmation.
   - **Meta daily spend cap:** the maximum daily budget the agent may
     propose for any ad set. Anything above it requires an explicit
     conversation, not just a routine approval.
   - **PAUSED-only acknowledgment:** read this sentence to the user and
     record their acknowledgment verbatim in the file: "All campaigns, ad
     sets, and ads are created PAUSED. Nothing spends until you explicitly
     approve activation in a live conversation." Do not skip this even if
     the user waves it off; a short "acknowledged" from them is enough.
7. **Creative preferences.** Preferred formats (static, UGC video,
   cinematic), aspect ratios, styles or cliches to avoid, and where the
   brand's reference images live on disk.

## Step 3: Write BRAND.md

1. Copy the canonical template structure exactly (from
   `${HERMES_SKILL_DIR}/BRAND.template.md` or
   `<workspace root>/BRAND.template.md`, whichever you find; they are
   identical; if neither exists, use the schema listed at the top of this
   skill): same H2 sections, same order, same heading names. Other skills
   parse this file by its headings.
2. Fill every field with the confirmed value or `(not set)`. The "Meta
   connection" field under "## Meta Assets" is written from Step 1
   discovery (`mcp` or `cli`), not asked. Anything left `(not set)` also
   gets a line under "## Setup Gaps" so a later session knows what to
   revisit.
3. Add the first Changelog entry under "## Changelog" ("<date>: Initial
   setup via brand-setup").
4. Write the file to the workspace root (the repo clone directory recorded
   during setup) as `BRAND.md`.

## Step 4: Read it back

Present the finished file to the user section by section and ask them to
confirm or correct it. Apply corrections, then confirm once more that the
final version is right. Do not end the flow on an unconfirmed file; if the
user disappears mid-review, say clearly which sections are confirmed and
which are still drafts the next session should revisit.

Close by telling the user what unlocks now: the ad-agent-orchestrator skill
can run full campaigns, and the creative, copy, and launcher skills will all
read this file automatically.

## Update flow

When the user says "update my brand file" or names a specific change:

1. Read the current `BRAND.md`. If it does not exist, switch to the create
   flow instead.
2. Ask what changed, or apply the change they already named. Touch only the
   relevant sections; do not re-run the whole interview.
3. Re-run the matching discovery step only when the change involves connected
   assets (a new ad account, Page, Instagram account, or Arcads product) or
   the Meta connection changed (for example the user moved from the CLI to
   the MCP); update the "Meta connection" field to match.
4. If the change touches budget guardrails, re-read the new numbers back
   explicitly before saving; these fields gate real spending. The PAUSED-only
   acknowledgment never gets removed, only re-affirmed.
5. Add a dated Changelog line describing the change, and read back the
   changed sections (not the whole file) for confirmation. Other skills
   route users here to fill "## Performance Targets" when it is empty; in
   that case touch just that section (and the conversion event under
   "## Meta Assets" if it is also unset).

## Pitfalls

- Do not write discovered accounts, Pages, or products into the file before
  the user picks and confirms them; the connected login may have access to
  accounts that are not theirs to advertise for.
- Do not let the website draft masquerade as the user's voice; it is a
  starting point they must edit or bless.
- Do not leave the three budget guardrails as `(not set)` without flagging
  it: tell the user that creative and launch skills will fall back to asking
  every single time until these are filled in.
- Do not paste actor or voice catalog dumps into BRAND.md; record only the
  user's stated preferences.

## Verification

Before you call the flow done: `BRAND.md` exists at the workspace root (the
repo clone directory recorded during setup), its headings match the
canonical template exactly, every field is either a confirmed value or an
explicit `(not set)`, the Meta connection field is `mcp`, `cli`, or
`(not set)` with a Setup Gaps line, at least one performance target (CPA or
ROAS) plus the default conversion event and campaign objective are present,
the three budget guardrails and the PAUSED-only acknowledgment are present,
and the user confirmed the read-back.
