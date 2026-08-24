# BRAND.md: Mr. Paid Social Hydration Labs (Demo)

<!--
  DEMO MODE. This is a complete SAMPLE brand file for a fictional parody brand,
  so you can test every Hermes Ad Agent skill end to end without touching a real
  business. To use it, copy this file to the workspace root (the repo clone
  directory recorded during setup) as BRAND.md. When you are ready to run for a
  real brand, run the brand-setup skill instead; it creates your own BRAND.md at
  the workspace root (that file is gitignored).
-->

## Business Basics

- **Brand name:** Mr. Paid Social Hydration Labs
- **Website:** https://example.com (demo placeholder; not a real site)
- **What you sell:** A parody performance-hydration brand for media buyers. Every
  product pretends that ad-account skills are a nutrient you can drink. One-line
  positioning: electrolytes formulated for people who check ROAS before they
  check their pulse. Satire / novelty consumer product; it is a joke, the ads
  should be in on the joke, and it is NOT a real dietary supplement company.
- **Price point:** $29 one-time / $24 subscription. Free shipping over $50.

## Offer

- **Main offer:** The Campaign Stack, a 3-flavor variety pack (24 sticks), $29.
  Hero product: Mr. Paid Social Electrolyte Drink Mix ("Scale Sticks"),
  single-serve powder sticks, 0.21 oz (6g) each. Flavors: Re-Targeting Rush
  (lime), Prospecting Punch (fruit punch), Scale-Up Watermelon. Upsell:
  Always-On Subscription, ships monthly, $24/month (save 17%, cancel anytime,
  "pause delivery" jokes encouraged).
- **Current promo:** 30-day "No Wasted Spend" money-back guarantee.
- **Landing page URL:** https://example.com/scale-sticks
  <!-- DEMO PLACEHOLDER: Meta rejects example.com URLs. Swap this for a real,
       live URL before launching any ad; meta-ad-launcher will refuse to create
       an ad while this is an example.com URL. -->

## Audience

- **Who they are:** Primary: media buyers, performance marketers, and growth
  hackers, roughly 22 to 45, extremely online, fluent in Meta Ads Manager
  jargon. Secondary: founders and marketing generalists who run their own ads
  and get the joke. They hang out on Instagram Reels, marketing Twitter/X
  screenshots reposted to IG, and meme accounts about agency life.
- **Pains:** Checking dashboards at 2 AM, ads stuck in the learning phase,
  attribution they do not trust, agency-life burnout.
- **Desires:** Inside jokes about CPMs, learning phase, and attribution. They
  buy the joke first and the electrolytes second.

## Voice and Tone

- **Voice description:** Deadpan parody of premium supplement advertising. Say
  absurd things with a straight face. Media-buyer jargon used as if it were
  nutrition science ("clinically meaningless dose of Machine Learning").
  Confident direct-response structure (hook, problem, product, offer, CTA) with
  satirical content. Short sentences. Emojis sparingly, one per ad maximum.
  Example on-voice lines:
  - "Your ads are in the learning phase. You don't have to be."
  - "1000 mg of Scale per stick. That is not a real unit, but neither is your attribution window."
  - "Hydration for people who say 'let it cook' about a $50 ad set."
- **Words to use:** The parody label claims verbatim in creative: 1000 mg Scale,
  200 mg Performance, 60 mg Machine Learning. AI-Powered Formulation. For
  Growth Hackers.
- **Words to avoid:** No hashtags in primary text. No em-dashes anywhere in ad
  copy; use commas, periods, or parentheses instead. No zaniness; the humor
  comes from sincerity.

## Claims and Compliance

- **Approved claims ledger:**
  - The fictional label claims (Scale, Performance, Machine Learning in mg) may
    appear only in clearly absurd, joke-forward context, never in a list of
    real benefits. Backed by: they are visibly parody packaging text.
  - "High ROAS" is package parody text, not a performance claim, and may only
    appear as such.
  - 30-day "No Wasted Spend" money-back guarantee. Backed by: the demo offer
    terms above.
- **Banned claims:**
  - This is satire. Never present the product as delivering real cognitive,
    medical, or performance benefits. No health claims, no disease claims, no
    "boosts focus" stated as fact.
  - No income or results claims, and no ROAS promises presented as real
    outcomes.
  - Never fabricate performance numbers in reporting. Only report what the Meta
    tools return.
- **Regulated-category notes:** Not a real supplement company, but ads read as
  supplement-adjacent, so stay clear of health-claim territory entirely.
  Follow Meta personal-attributes policy: never call out the viewer's health,
  finances, or job status directly ("Are you a broke media buyer?" is not
  allowed; "Made for media buyers" is fine). No before/after imagery, no
  medical imagery, no fake certifications beyond what is visibly parody on the
  packaging, no real celebrity likenesses, no competitor brand names.

## Meta Assets

<!-- Placeholders. Replace with real values only in a private workspace-root
     BRAND.md, never in this committed demo file. -->

- **Ad account ID:** YOUR_AD_ACCOUNT_ID
- **Page ID:** YOUR_PAGE_ID
- **Instagram account ID:** YOUR_IG_ACCOUNT_ID
- **Pixel ID:** YOUR_PIXEL_ID
- **Default campaign objective:** OUTCOME_SALES
- **Default conversion event:** Purchase
- **Default CTA:** SHOP_NOW

## Arcads Assets

- **Product IDs:** (not set) <!-- register the demo product in your own Arcads workspace, or leave unset -->
- **Preferred actors:** No preference; deadpan, sincere delivery matters more
  than the specific actor.
- **Preferred voices:** No preference; dry, straight-faced reads.

## Performance Targets

<!-- Demo values, chosen to exercise the reporting and alerting skills. Set your
     own real targets in your workspace-root BRAND.md. -->

- **Target CPA:** $25 per Purchase (demo value)
- **Target ROAS:** (not set)
- **Target CTR (optional):** (not set)
- **Attribution notes:** Default Meta attribution settings; demo brand, so treat
  all numbers as test data.

## Budget Guardrails

- **Arcads credit budget per batch:** 5 credits maximum per generation batch.
  Estimate the cost first and get explicit confirmation before generating. Stop
  and re-confirm if a batch would exceed 5 credits.
- **Meta daily spend cap:** $50/day total across all ad sets for this brand.
  Never create an ad set whose daily budget would push the account past this
  cap. Per-ad-set default budget: $10/day unless the user says otherwise.
- **PAUSED-only acknowledgment:** Acknowledged (demo file): "All campaigns, ad
  sets, and ads are created PAUSED. Nothing spends until you explicitly approve
  activation in a live conversation." No budget increases, no activating paused
  entities, and no resuming delivery without explicit human confirmation in the
  current conversation.

## Creative Preferences

- **Formats:** Static image ads and short UGC-style video (8 to 15s). Deadpan
  talking-head UGC or product b-roll with dry voiceover.
- **Aspect ratios:** 1:1 and 9:16 for statics; 9:16 for video.
- **Styles:** Clean studio product shots on white or bold solid color, packaging
  text legible, supplement-aisle lighting played completely straight. Hook in
  the first line, offer and CTA in the last line. Headlines under 40
  characters. Avoid: medical settings, before/after, zany humor.
- **Reference images:** `<workspace root>/assets/demo-products/` (the product
  shot is `electrolyte-drink-mix-sticks.jpg`; use it as the product reference
  in every generation so packaging stays consistent).

## Setup Gaps

- Meta Assets IDs are placeholders; replace with real IDs in a private
  workspace-root BRAND.md before launching.
- Landing page URL is an example.com placeholder and must be swapped for a real
  URL before any launch.
- Arcads product ID not set; register or pick a product in your Arcads
  workspace if you want to run the Arcads creative skills against this demo.

## Changelog

- 2026-08-24: Rewritten to the canonical BRAND.md schema; added Performance
  Targets (demo values), Arcads Assets, Setup Gaps, and Changelog sections.
