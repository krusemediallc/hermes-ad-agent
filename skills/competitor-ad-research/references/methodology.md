# Competitor Research Methodology

Condensed reference for the competitor-ad-research skill. The SKILL.md procedure tells you when to do each step; this file defines the judgments: how to pick competitors, how to trust a page match, what to record per ad, how the 100-point score works, how to classify ads, and the exact output contract for the brief.

## 1. Competitor selection

A good competitor set for ad research is 3 to 7 pages that meet at least one of:

- **Direct competitors:** sell a substitutable product to the same audience.
- **Audience competitors:** sell something different to the same buyer (useful for hooks and angles even when the product differs).
- **Aspirational operators:** brands the user admires for their creative volume or style, in or near the niche.

Prefer named competitors from BRAND.md or the user. When proposing candidates yourself, favor pages with meaningful active ad volume (a page running 1 or 2 ads teaches little) and always get the user's sign-off before pulling.

## 2. Page-resolution confidence policy

Never guess a page. Accepted resolutions:

| Input | Method | Confidence |
|---|---|---|
| `123456789` | Explicit numeric Page ID | Explicit |
| Ad Library or Facebook URL containing a numeric page ID | Parsed from URL | Explicit |
| Brand name where exactly one returned page is an exact normalized name match | Keyword search via `ads_library_search`, then exact match on `page_name` | High |
| User picks a page ID from candidates you presented | User-confirmed | Explicit |

Normalization means case, punctuation, and spacing only. Refuse: substring or starts-with matches, "closest" or "most ads" heuristics, multiple pages sharing the exact normalized name (ask the user), and any candidate that requires a judgment call. When unresolved, keep up to ten candidate pages (name, ID, sample ad count) as evidence for the user and move on.

## 3. Data contract per ad

Record whatever the server returns from this set; leave missing fields empty and never manufacture values:

- **Identity and timing:** Ad Library ID, page ID, page name, creation time, delivery start time, delivery stop time (absence of a stop time is what "active or not stopped" means).
- **Full copy arrays:** every body, headline (link title), description, and caption variant, untruncated. Multiple variants on one ad usually indicate Dynamic Creative or an active copy test; that is a signal, keep all of them.
- **Context:** publisher platforms, languages, snapshot URL, and any reach or audience fields the server includes.
- **Derived:** the public archive link `https://www.facebook.com/ads/library/?id=<ad-library-id>`, and your resolution method for the page.

Deduplicate strictly by Ad Library ID across every query in the run. Duplicate copy under distinct IDs stays as distinct records.

## 4. The 100-point adaptation-leverage score

This is an adaptation-readiness ordering, not a performance model. Compute it per deduplicated ad from returned fields only:

| Component | Points | Calculation |
|---|---:|---|
| Longevity proxy | 45 | Linear over observed running days, capped at 365. Stopped ads: start to stop. Unstopped ads: start to today. Missing or invalid dates score 0 |
| Active or not stopped | 15 | 15 when no stop date was returned, otherwise 0 |
| Publisher-platform breadth | 15 | 3.75 per unique platform, capped at 4 platforms |
| Copy completeness | 15 | 3.75 for each non-empty array among bodies, headlines, descriptions, captions |
| Creative inspectability | 10 | 10 when a snapshot URL or viewable archive creative is available, 5 when only copy and metadata exist, 0 when neither |

When a component's input field was simply not returned by this server version, score that component 0 and tag the ad "partial data" so a low score is not mistaken for a weak ad. Round the total to one decimal and always show the component breakdown in the brief.

**Why longevity is only a proxy.** Ad Library data does not expose spend, conversions, ROAS, or profitability. "Not stopped" can mean active, or just no stop date returned. Long duration can reflect evergreen low-spend delivery, duplication, or plain inertia. Platform breadth and copy completeness measure how reusable the material is, not how well it performed. The brief must label the metric "commercial-library longevity proxy" and carry this disclaimer verbatim in spirit: sustained spend suggests the advertiser found the ad worth running, and nothing more.

**Brand fit is a separate layer.** Qualitative fit notes (how an angle maps to the user's offer, what transfers, what must change) inform which opportunities become creative briefs, but they never move the objective score. Keep the two visibly separate.

## 5. Analysis taxonomy

Classify each ad on four axes. Work only from observables; if you have not viewed the creative itself, mark format and visual notes as "unverified, inferred from copy".

**Angle** (the persuasive frame):

- Problem/agitation: leads with the pain, product arrives as relief
- Benefit-direct: leads with the outcome or transformation
- Social proof: testimonial, review count, "join 40,000 others"
- Us-vs-them: against the old way, the incumbent, or the category
- Founder/story: first-person origin or behind-the-scenes narrative
- Offer-led: discount, bundle, free trial, guarantee does the selling
- Curiosity/pattern-interrupt: withholds the payoff to earn the click
- Education/how-to: teaches something and sells inside the lesson

**Hook** (the first line or first visual beat):

- Question, bold claim, callout ("If you run Facebook ads..."), statistic, confession, negative hook ("Stop doing X"), news/trend jack, or demonstration-first

**Format** (only assert when observed):

- Static image (product shot, lifestyle, text-heavy graphic, meme style, comparison layout)
- Carousel
- Video: UGC talking head, demo, b-roll montage, animation, screen recording, cinematic spot
- Copy-led (long primary text carrying the ad regardless of creative)

**Offer** (the deal structure):

- Price-off or sale, bundle, free trial or freemium, lead magnet, quiz or diagnostic funnel, subscription, guarantee-forward, waitlist or launch, or no explicit offer (pure brand)

Patterns to surface across the set: which angles dominate each competitor, which hooks repeat across competitors (crowded), which angles nobody in the set is running (open lanes), copy-test intensity (many variants on one ad), and duplication (same copy under many IDs, a signal of scaling behavior).

## 6. Adaptation boundaries

For every opportunity that becomes a brief:

- Reuse structure: layout, pacing, proof architecture, hook mechanics, offer framing.
- Replace entirely: competitor branding, logos, people, product imagery, proprietary UI, verbatim copy, and every claim.
- Never carry over an outcome claim ("lost 20 lbs", "saved $400/mo") unless the user can substantiate their own replacement.
- Fit notes are judgment, and must never be presented as performance evidence.

## 7. BRIEF.md output contract

Write to `research/BRIEF-<YYYY-MM-DD>.md` in the workspace. Required sections, in order:

```markdown
# Competitor Research Brief: <brand> (<date>)

## 1. Run summary
Market, active/all filter, competitors pulled, discovery keyword sweeps,
total ads collected, dedupe count, server fields that were unavailable,
and this disclaimer: longevity is a commercial-library proxy for advertiser
commitment; it does not prove spend, conversions, or profitability.

## 2. Competitor landscape
| Competitor | Page ID | Resolution | Ads sampled | Active | Dominant angle | Dominant format |
One row per competitor, plus a short paragraph each on their apparent strategy.
Include discovered pages (from keyword sweeps) in a separate labeled table.

## 3. Ranked opportunities
| Rank | Score | Ad Library link | Page | Running since | Angle | Hook | Format |
Top 15 to 20 by adaptation-leverage score. Every row links to
https://www.facebook.com/ads/library/?id=<id>. Below the table, show the
five-component score breakdown for at least the top 10, flagging any
"partial data" ads.

## 4. Top ad detail
For the top 5 to 8 ads: every copy variant in full (bodies, headlines,
descriptions, captions), the metadata, the observed-vs-inferred visual note,
and a two-line brand-fit judgment (clearly labeled as judgment).

## 5. Creative briefs
3 to 5 briefs, each self-contained (see template below).

## 6. Next steps
Which skill produces each brief, and a reminder that generation runs its own
credit-cost confirmation before anything is created.
```

Creative brief template (one per brief):

```markdown
### Brief N: <working title>
- Source: <archive link(s)> from <competitor> (<score>, running <n> days)
- Angle / Hook: <angle> / <hook type>
- Target format: static image | UGC talking-head video | short video
- Hand to: <image ad skill | video ad skill in this suite>
- Aspect ratio: 1:1 | 4:5 | 9:16
- Hook line (draft, brand voice): "..."
- Copy direction: 2 to 4 sentences on message, proof, and CTA
- Visual direction: what the frame or beats should show, built for the
  user's product (never the competitor's assets)
- Replace list: competitor branding, people, product shots, and all claims;
  note which user-substantiable proof goes in instead
```

Style rules for briefs: write drafted hooks and copy in the brand's voice from BRAND.md, keep claims to what the user can substantiate, and use no em-dashes in any suggested ad copy (commas, periods, or parentheses instead).

Example of a well-formed brief entry (fictional competitor, fictional brand):

```markdown
### Brief 2: The 14-Day Desk Reset
- Source: https://www.facebook.com/ads/library/?id=1234567890123456
  from Peak Posture Co (score 87.5, running 212 days)
- Angle / Hook: problem/agitation / callout
- Target format: UGC talking-head video
- Hand to: video ad skill
- Aspect ratio: 9:16
- Hook line: "If your lower back hates your desk job, this is for you."
- Copy direction: Open on the callout, agitate with one specific desk-day
  moment (the 3 pm slump, the stand-up wince), introduce the product as a
  two-minute daily reset, close with the trial offer. One proof point only,
  and it must be the user's own.
- Visual direction: Selfie-style talking head at a real desk, one cutaway
  to the product in use, end card with offer text.
- Replace list: All Peak Posture branding, their spokesperson, their
  "9 out of 10 users" claim (swap in the user's verified review stat or
  drop the stat entirely).
```

## 8. Interpretation guardrails (repeat in every brief)

1. Longevity is commitment, not performance. No spend, conversion, or ROAS data exists in the Ad Library.
2. Scores order adaptation readiness of the sample pulled this run; they are not a market census (queries cap at 50 results each).
3. Visual claims marked "unverified" came from copy and metadata, not from viewing the creative.
4. Nothing in this brief was generated or published; production happens only through the generation skills after the user picks a brief.
