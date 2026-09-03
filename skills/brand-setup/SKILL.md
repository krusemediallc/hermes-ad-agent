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
  acknowledgment. It records the Meta token's expiry date (a date, never
  the token) with a renewal reminder, writes BRAND.md to the workspace
  root resolved from the setup-state file, updates that file's backend
  fields, reads BRAND.md back for confirmation, then saves a short profile
  to Hermes memory (one User Profile entry and one Notes entry, no secrets
  or account IDs) so later sessions start with the essentials. Use it
  on first install, whenever BRAND.md is missing, when another skill routes
  the user here, or when the user says "set up my brand", "brand setup",
  "create my brand file", "onboard my business", "update my brand file",
  "change my brand voice", "we have a new offer", or "my spend cap changed".
---

# Brand setup

You are building `BRAND.md`, the single file every other Hermes Ad Agent
skill reads for brand context. It lives at the workspace root, which you
resolve from the setup-state file before anything else:
`$HERMES_HOME/hermes-ad-agent/setup-state.json` (fallback
`~/.hermes/hermes-ad-agent/setup-state.json`), field `workspace_root`, an
absolute path written by SETUP.md. If the file is missing or the field is
empty, stop and route the user to SETUP.md; do not guess a directory or
take one from the conversation. The structure to follow is the
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
- Never store secrets. The MCP servers handle their own auth (the Meta MCP
  token lives in the managed app's environment or the file
  `hermes config env-path` names), and the Meta Ads CLI (Meta's official
  command-line tool for the Marketing API) keeps its token in a gitignored
  `.env`; BRAND.md holds business facts, the user's own account
  identifiers, and the token's expiry DATE only, never a token value, and
  only after the user confirms them.
- Tool names in this file are server-native IDs (`ads_get_ad_accounts`);
  the Hermes runtime registers them under prefixed callable names
  (observed shape `mcp__meta_ads__ads_get_ad_accounts`). Discover the
  registered name in your live tool list and call that.
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
   use. If there are several, show them by name AND ID and ask which is
   the default for ad work; the user picks by ID when two share a name
   (identical display names across a business are common). Restate
   "<name> (<act_ID>)" before recording it.
2. For the chosen account, `ads_get_ad_account_pages` to find the Facebook
   Pages it can publish under (fall back to `ads_get_user_pages` if needed).
   Ask which Page is the default identity.
3. `ads_get_ig_accounts` to find linked Instagram accounts. Ask which one, if
   any, ads should publish under.

On the CLI route:

1. `meta ads adaccount list --output json` to list the ad accounts the system
   user can use. If there are several, show them by name AND ID and ask
   which is the default for ad work, picking by ID when names repeat. The
   CLI's `AD_ACCOUNT_ID` (in the workspace `.env`,
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

**Meta token expiry (a date, never the token).** On the MCP route the
hosted Meta MCP accepts a user access token, and the long-lived form Meta
issues lasts about 60 days with no refresh token, so renewal is manual
and every reporting job needs to know the date. Ask the user for the
expiry date recorded at SETUP.md Step 4 (the token exchange response
reports it; the pack's read-only doctor,
`python3 scripts/onboarding_doctor.py --meta-token-check` run from the
workspace root, reports `expires_at` and days remaining without printing
the token; verify its flags with `--help`). Write it under
"## Meta Assets" as its own line, exactly:
`Meta token expires: YYYY-MM-DD`, followed by the renewal reminder line:
`Renewal: generate a new user token with all seven scopes, exchange it
for a long-lived token, update the environment variable, restart the
managed app, then update this date (SETUP.md Step 4).` On the CLI route
with a system user token, which has no scheduled expiry, write
`Meta token expires: none (system user token; can still be invalidated)`.
If the user does not know the date, write `Meta token expires: (not set)`
and add a Setup Gaps line saying reporting jobs will warn about it until
it is filled in. Never write the token value, its prefix, or its length.

**Update the setup-state file.** If
`$HERMES_HOME/hermes-ad-agent/setup-state.json` (fallback
`~/.hermes/hermes-ad-agent/setup-state.json`) exists, update the fields
this discovery learned and leave the rest untouched: `meta_backend`
(`mcp`, `cli`, or `none`) and `arcads_connected` (`true` or `false`).
Read the file, change only those keys, write it back as valid JSON, and
read it back to confirm. Do not create the file if it is missing (SETUP.md
owns creation; note the gap instead), and never write a token, an account
ID, or any other identifier into it.

**Account audit memory** (`memory/accounts/act_<ACCOUNT_ID>.md` at the
workspace root, one file per ad account, written by the `account-audit`
skill), once the default ad account is chosen:

1. Check `memory/accounts/` for an audit file matching that account.
   Running `account-audit` right after the Meta backend is connected,
   before this interview, is the preferred order; if the file is missing
   and a Meta backend is live, offer to run it now (it is strictly
   read-only) and come back. If the user declines, continue without it.
2. If the file exists, read its "## Account Snapshot" and
   "## Settings Inventory" sections and pre-fill the "## Meta Assets"
   answers from them: the pixel and conversion events actually in use and
   the observed default campaign objective. Present each pre-fill as an
   observed value from the audit for the user to confirm or correct, never
   as already decided.
3. From its "## Top Performers" and "## Account Snapshot" sections, propose
   baseline Performance Targets (for example the account's 90-day CPA or
   ROAS), labeled explicitly as observed numbers from the audit, not
   goals. The user confirms, adjusts, or replaces them in Step 2 before
   anything is written to BRAND.md.

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
   discovery (`mcp` or `cli`), not asked, and the
   `Meta token expires: YYYY-MM-DD` line plus its renewal reminder go
   under the same heading even when the template you copied does not
   list them (the reporting skills parse that exact line). Anything left
   `(not set)` also gets a line under "## Setup Gaps" so a later session
   knows what to revisit.
3. Add the first Changelog entry under "## Changelog" ("<date>: Initial
   setup via brand-setup").
4. Write the file to the workspace root (resolved from the setup-state
   file) as `BRAND.md`.

## Step 4: Read it back

Present the finished file to the user section by section and ask them to
confirm or correct it. Apply corrections, then confirm once more that the
final version is right. Do not end the flow on an unconfirmed file; if the
user disappears mid-review, say clearly which sections are confirmed and
which are still drafts the next session should revisit. Once the file is
confirmed, do Step 5 before closing.

## Step 5: Save the essentials to Hermes memory

BRAND.md is the full profile, but Hermes only reads it when a skill opens
it. Hermes also keeps two small personal memory files that are injected
into the system prompt of every session, under `$HERMES_HOME/memories/`
(`~/.hermes/memories/` when `HERMES_HOME` is unset): `USER.md` ("User
Profile" in the dashboard, who the user is and how they want to be
worked with, cap 1,375 characters) and `MEMORY.md` ("My Notes", the
agent's own notes about the environment, cap 2,200 characters). Use the
built-in `memory` tool to write one entry in each so the next session
knows where the brand lives and how to behave before it opens a single
file. The setup-state file, not these notes, is the machine-readable
source of the workspace root; the note is a human-readable pointer.

1. **User Profile entry** (the `memory` tool, user-profile target), under
   400 characters, starting with the stable prefix `Hermes Ad Agent:`.
   Contents: brand name and the one-line offer, the user's role (owner,
   marketer, agency, or whatever they told you), the preferred reporting
   channel and cadence (ask now if the interview did not cover it; it is
   one question), and the sentence "Always confirm before any spend."
   Example shape:
   `Hermes Ad Agent: <Brand> sells <one-line offer>. User is the <role>.
   Reports go to <channel> <cadence>. Always confirm before any spend.`
2. **Notes entry** (the `memory` tool, notes target), under 500 characters,
   also starting with `Hermes Ad Agent:`. Contents: the workspace root as
   an absolute path, the Meta backend (`mcp` or `cli`, from the "Meta
   connection" field), whether the Arcads MCP is connected, where BRAND.md
   and `memory/accounts/` live under that root, and the sentence
   "Everything launches PAUSED." Example shape:
   `Hermes Ad Agent: workspace root <absolute path>. Meta backend: <mcp or
   cli>. Arcads MCP: <connected or not connected>. Brand profile at
   <root>/BRAND.md; account memory at <root>/memory/accounts/. Everything
   launches PAUSED.`
3. **Add or replace, never duplicate.** On the first run use the tool's
   `add` action. On any later run (an update, a re-run, a moved workspace)
   use `replace`, matching the existing entry by its `Hermes Ad Agent:`
   prefix as the old text, so each file keeps exactly one entry for this
   pack. Before writing, check whether an entry with that prefix already
   exists; if it does, replace it even when the user only said "set up my
   brand".
4. **Respect the caps.** Both files hold everything else the agent has
   remembered too, so stay well under your own limits (400 and 500
   characters) and never push a file past its cap (1,375 characters for
   USER.md, 2,200 for MEMORY.md, the `memory.user_char_limit` and
   `memory.memory_char_limit` config keys). If a write is rejected for
   size, shorten the entry rather than trimming someone else's.
5. **Tell the user what just happened.** Both files are loaded as a frozen
   snapshot at session start, so these entries take effect from the next
   session, not this one. If `memory.write_approval` is true in the
   Hermes config (`hermes config path` prints where it lives), the writes
   sit in `/memory` as pending until
   the user runs `/memory approve` (or `/memory reject`); say so and ask
   them to approve. If `memory.memory_enabled` or
   `memory.user_profile_enabled` is false, skip the matching entry, say
   which one was skipped, and note it under "## Setup Gaps".
6. **What never goes in these files:** tokens or any secret, ad account
   IDs, Page or Instagram IDs, pixel IDs, audience names, verbatim ad copy,
   performance numbers, or budget figures. Those belong in BRAND.md and the
   gitignored `memory/accounts/` files at the workspace root. The Hermes
   memory files carry pointers and behavior rules only. If the user asks
   you to "remember" one of those values anyway, put it in BRAND.md and
   explain why.

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
   the MCP); update the "Meta connection" field to match, and update
   `meta_backend` and `arcads_connected` in the setup-state file if it
   exists. When the user says the Meta token was renewed ("I got a new
   token", "renewed my Meta token", or a reporting job's expiry alert sent
   them here), update only the `Meta token expires: YYYY-MM-DD` line with
   the new date and add a Changelog entry; never ask for or record the
   token itself.
4. If the change touches budget guardrails, re-read the new numbers back
   explicitly before saving; these fields gate real spending. The PAUSED-only
   acknowledgment never gets removed, only re-affirmed.
5. Add a dated Changelog line describing the change, and read back the
   changed sections (not the whole file) for confirmation. Other skills
   route users here to fill "## Performance Targets" when it is empty; in
   that case touch just that section (and the conversion event under
   "## Meta Assets" if it is also unset).
6. Refresh the two Hermes memory entries with the `memory` tool's
   `replace` action (Step 5), matching the existing text by its
   `Hermes Ad Agent:` prefix so nothing is duplicated. Do this whenever the
   change touches anything those entries carry: brand name, offer, the
   user's role, reporting channel or cadence, workspace root, Meta backend,
   or the Arcads connection. If no entry with that prefix exists yet, `add`
   it instead. The same caps, the frozen-snapshot note, the
   `memory.write_approval` case, and the no-IDs-no-secrets rule apply.

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
- Do not put account IDs, audience names, copy, numbers, or any token into
  the Hermes memory files (USER.md, MEMORY.md); they are pointers and
  rules only, and they are read into every session's prompt.
- Do not `add` a second `Hermes Ad Agent:` entry on a re-run; `replace`
  the existing one.
- Do not record the Meta token, any fragment of it, or its length; the
  expiry date is the only token fact BRAND.md carries.
- Do not create or rewrite the setup-state file wholesale; change only
  `meta_backend` and `arcads_connected`, and only when the file exists.
- Do not choose an ad account by display name alone.

## Verification

Before you call the flow done: `BRAND.md` exists at the workspace root
resolved from the setup-state file, its headings match the canonical
template exactly, every field is either a confirmed value or an explicit
`(not set)`, the Meta connection field is `mcp`, `cli`, or `(not set)`
with a Setup Gaps line, the `Meta token expires:` line is present under
"## Meta Assets" with a date, `none (system user token; ...)`, or
`(not set)` plus a Setup Gaps line, the ad account is recorded by name and
ID, at least one performance target (CPA or ROAS) plus the default
conversion event and campaign objective are present, the three budget
guardrails and the PAUSED-only acknowledgment are present, the user
confirmed the read-back, the setup-state file (when it exists) reads back
with the `meta_backend` and `arcads_connected` values you observed, and
Hermes memory holds exactly one `Hermes Ad Agent:` entry in the User
Profile and one in Notes (or the user was told the writes are pending
approval, or that memory is disabled). Nothing in any of those files is
a token value.
