---
name: competitor-ad-research
description: Researches competitor ads through the Meta Ads MCP server's ads_library_search tool, pulls each competitor's running ads from the Meta Ad Library (full copy variants, delivery metadata, ad archive links), analyzes angles, hooks, formats, and offers, ranks every ad with a 100-point adaptation-leverage score, and writes a dated research brief (research/BRIEF-<date>.md) containing top competitors, their running ads, scored opportunities, and 3 to 5 concrete creative briefs ready to hand to the Hermes Ad Agent image and video generation skills. Use when the user asks to research competitors, spy on competitor ads, see what ads a brand or niche is running, pull or search the Meta Ad Library, find long-running competitor creative, build a swipe file, or prepare a competitor research brief before making new ads. Research only, it does not generate creatives or publish anything to Meta.
---

# Competitor Ad Research

You are running a research-only competitor workflow for the Hermes Ad Agent. Everything flows through Meta's official Ads MCP server. There are no local scripts, no Python, no Selenium, no browser scraping, no `.env` files, and no `META_ACCESS_TOKEN`. If you catch yourself reaching for curl or a script to hit the Graph API, stop: the only data source in this skill is the `ads_library_search` MCP tool.

The output is one file: `research/BRIEF-<date>.md` at the workspace root (the repo clone directory recorded during setup), for example `research/BRIEF-2026-08-24.md`. It contains the competitor landscape, their running ads with ad archive links, a scored opportunity ranking, and 3 to 5 concrete creative briefs the user can hand directly to this suite's image ad and video ad skills.

Read `references/methodology.md` in this skill folder before your first run. It holds the data contract, the page-resolution policy, the full 100-point score formula, the analysis taxonomy, and the brief template. This file tells you what to do; that file tells you how to judge.

## Requirements

- **Meta Ads MCP connected.** The official server (`https://mcp.facebook.com/ads`) must be configured and logged in. If `ads_library_search` is not in your available tool list, walk the user through connecting the server (see SETUP.md and docs/meta-mcp.md in this repo for the connection steps) and stop until it is connected.
- **An active ad account.** Meta only serves `ads_library_search` to users with at least one active ad account on the connected Business account. If the tool returns an access error, report that requirement plainly; do not retry in a loop.
- **BRAND.md.** Read `BRAND.md` from the workspace root first. It carries the user's offer, audience, tone, markets, and usually a competitor list. If it is missing, offer to run the brand-setup skill before continuing. You can proceed without it if the user insists, but say clearly that adaptation-fit judgments will be weaker.

## Quick reference: ads_library_search

Parameters observed on Meta's official Ads MCP (August 2026 session):

| Parameter | Type | Notes |
|---|---|---|
| `search_terms` | string | Keyword or phrase matched against ad creative text |
| `page_ids` | array of strings | Numeric Page IDs; returns only ads run by these pages |
| `countries` | array of strings | ISO-2 codes (`US`, `GB`, `DE`); filters by reached country |
| `ad_active_status` | string | `ALL`, `ACTIVE`, or `INACTIVE`; defaults to `ALL` |
| `ad_type` | string | `ALL`, `POLITICAL_AND_ISSUE_ADS`, `HOUSING_ADS`, `EMPLOYMENT_ADS`, `CREDIT_ADS` |
| `limit` | integer | Default 25, maximum 50 |

At least one of `search_terms`, `page_ids`, or `countries` is required per call.

**Check your live tool list first.** Server versions differ. Before your first call, confirm `ads_library_search` exists in this session and read its live schema; trust the live schema over this table. Some builds expose page-name search or pagination parameters this table does not show; the August 2026 build did not, so treat 50 results per query as the working ceiling and narrow with keywords instead of paging. The server may also require housekeeping fields on every call (a stable `client_conversation_id` and an `advertiser_request` string quoting the user's ask); fill those exactly as the live tool description instructs.

## Procedure

### Step 1: Load brand context

Read `BRAND.md`. Pull out: what the user sells, who they sell to, their primary market countries, their tone, and any listed competitors. Default the research market to the brand's primary country, or `US` if none is stated. Confirm the market with the user if BRAND.md is ambiguous.

### Step 2: Build the competitor list

Combine BRAND.md's competitor section with whatever the user names in the conversation. Aim for 3 to 7 competitors. Accept any of: a brand name, an exact Facebook Page name, a numeric Page ID, or an Ad Library URL (the numeric `id` or `view_all_page_id` in the URL is usable directly). If the user has no competitors in mind, propose candidates from the niche and get their sign-off before pulling.

### Step 3: Resolve pages, never guess

`page_ids` wants numeric Page IDs, so names must be resolved first:

1. If the input is already a numeric ID, or contains one (Ad Library URL, Facebook page URL with a numeric ID), use it as explicit.
2. Otherwise run `ads_library_search` with `search_terms` set to the brand name plus the market country, and read the `page_name` / page ID pairs on the returned ads.
3. Accept a resolution only when exactly one page's name is an exact match after normalizing case, punctuation, and spacing. Substring matches, similar names, or "the biggest page in the results" are not matches.
4. When zero or multiple exact matches appear, show the user the candidate pages you found (name, ID, sample ad count) and ask them to pick or supply the numeric ID. Do not pick for them.

Record how each page was resolved (explicit ID, exact name match, or user-confirmed) so the brief can disclose it.

### Step 4: Pull the ads

For each resolved competitor, call `ads_library_search` with `page_ids` set to that page, `countries` set to the confirmed market, `ad_active_status: "ACTIVE"` (ask the user if they also want stopped ads; `ALL` is useful for spotting recently killed creative), and `limit: 50`.

Then run 1 to 3 keyword sweeps with `search_terms` on the niche's core phrases (product category, problem language, offer language) to catch competitors the user did not name. Flag interesting pages from these sweeps as "discovered" rather than silently merging them into the competitor set.

While collecting:

- **Deduplicate strictly by Ad Library ID.** Never dedupe by copy text, page, date, or creative URL. Identical copy under different IDs means the competitor is running duplicates, and that is itself a signal worth keeping.
- **Preserve full copy.** Keep every returned body, headline, description, and caption variant without truncation. Multiple bodies on one ad usually means Dynamic Creative or an active copy test.
- **Keep the metadata.** Page name and ID, creation and delivery start dates, stop date if present, publisher platforms, languages, and the ad snapshot URL, whatever the server returns. Fields vary by server version, country, and ad category; record what you get and never invent values for missing fields.
- **Build the archive link.** For every ad, construct `https://www.facebook.com/ads/library/?id=<ad-library-id>`. These public links go in the brief so the user can view any creative in their own browser.

### Step 5: Analyze angles, hooks, formats, and offers

Classify every ad using the taxonomy in `references/methodology.md`: marketing angle, hook type, format, and offer structure. Work from what you can actually observe. Ad copy and metadata are always observable. Visual format is observable only if you have genuinely viewed the creative (for example by opening the snapshot or archive link with a browser or fetch toolset available in this session). If you have not seen the pixels, classify visuals as "unverified, inferred from copy" and say so in the brief. Never write a visual description of a creative you did not view.

### Step 6: Score adaptation leverage

Score every deduplicated ad with the 100-point formula in `references/methodology.md`: longevity proxy (45), active status (15), platform breadth (15), copy completeness (15), creative inspectability (10). The score is computed only from returned fields. When a component's input is missing (for example the server returned no platform list), score that component zero and note "partial data" on the ad. Show the component breakdown, not just the total.

Two non-negotiable framings, repeat both in the brief:

- Longevity is a proxy for advertiser commitment, never proof of performance. The Ad Library does not expose spend, conversions, or ROAS, so you cannot know an ad "works", only that someone kept paying for it.
- Never fabricate performance numbers. Report only what the MCP returned.

### Step 7: Judge brand fit

The objective score orders the raw opportunities; brand fit decides which become briefs. For each of the top 10 to 15 scored ads, note in one or two lines how the angle maps onto the user's actual offer and audience from BRAND.md, what transfers, and what must be replaced. Keep this layer visibly separate from the objective score; it never changes the number.

### Step 8: Write the brief

Create the `research/` directory at the workspace root if needed and write `research/BRIEF-<date>.md` using today's date and the exact output contract in `references/methodology.md`. Required sections: run summary and coverage, competitor landscape table, ranked opportunities with score breakdowns and archive links, full copy detail for the top ads, and 3 to 5 creative briefs.

Each creative brief must be concrete enough to hand to a generation skill without re-reading the research: working title, source ad archive link(s), angle and hook, target format (static image, UGC talking head, or short video), a drafted hook line and copy direction in the brand's voice, visual direction, an explicit "replace" list (competitor branding, people, claims, product shots), and which skill in this suite should produce it (the image ad skill for statics, the video ad skill for motion). Write all suggested ad copy without em-dashes. Never carry a competitor's outcome claim into a brief unless the user can substantiate their own equivalent.

### Step 9: Hand off, do not generate

Present the brief to the user, restate the longevity disclaimer once, and ask which briefs they want produced. Then stop. Creative generation belongs to the image and video skills, which run their own credit-cost estimate and confirmation gates through the Arcads MCP. Do not invoke them yourself without the user choosing a brief, and do not create, modify, or activate anything in the user's ad account from this skill.

## Pitfalls

- **Access error on the first call.** Usually means the connected Meta login has no active ad account, or the OAuth session lapsed. Explain, suggest re-running the Meta MCP login (see SETUP.md / docs/meta-mcp.md for the reconnect steps), stop.
- **The 50-result ceiling.** Big advertisers run hundreds of ads. Say openly that the pull is a sample, prioritize `ACTIVE` ads, and slice further with `search_terms` per product line if the user wants depth.
- **Prolific lookalike pages.** Dropshippers clone brand names constantly. This is exactly why Step 3 refuses fuzzy matches.
- **Snapshot URLs are not deliverables.** They can expire or require login. The durable public reference is the `facebook.com/ads/library/?id=` archive link; always include it.
- **Copy-only records.** Some ads come back with metadata but empty copy arrays. Keep them, score them honestly (they lose copy-completeness and inspectability points), and never pad them with invented text.
- **Scope creep into generation or account management.** Requests like "now make me that ad" or "pause my campaign" leave this skill. Route generation to the image/video skills and account actions to the launch/insights skills.

## Verification

Before telling the user you are done, confirm all of these against the written file:

1. `research/BRIEF-<date>.md` exists at the workspace root and today's date is in the filename.
2. Every listed ad has an Ad Library archive link and a score with visible components.
3. No performance numbers appear anywhere except fields the MCP actually returned, and the longevity disclaimer appears in the brief.
4. Every visual claim is either backed by a creative you viewed or labeled unverified.
5. There are 3 to 5 creative briefs, each naming a target format and the generation skill that should receive it, with no em-dashes in the suggested copy.
6. No campaigns, ads, creatives, or audiences were created, changed, or activated during the run.
