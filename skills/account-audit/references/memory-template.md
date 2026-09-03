# Account memory: act_<ACCOUNT_ID>

<!-- Written by the account-audit skill to memory/accounts/act_<ACCOUNT_ID>.md
     at the workspace root. memory/ is gitignored: this file is user data and
     never gets committed. Other skills parse it by the exact H2 heading names
     below, so keep every heading verbatim and in this order. Every number and
     every line of copy in this file came from the Meta backend; nothing here
     is estimated or invented. -->

## Audit Metadata

<!-- Generated date (YYYY-MM-DD) and the backend used: mcp or cli. -->
<!-- Date range audited, e.g. the 90 days ending on the generated date. -->
<!-- Refresh instructions: say "refresh the account memory" to rerun the
     account-audit skill against this account; it updates this same file and
     adds a Changelog entry. -->

## Account Snapshot

<!-- Account name, account ID (act_...), currency, timezone. -->
<!-- Total spend over the 90-day window, in the account currency. -->
<!-- Counts of active campaigns, active ad sets, and active ads at audit
     time (plus paused counts if pulled). -->

## Structure Map

<!-- The campaign tree: each campaign with its objective, buying type, CBO
     versus ABO, budget (human currency amounts), bid strategy, and status,
     then its ad sets and ads with their statuses. -->
<!-- Naming conventions observed in campaign, ad set, and ad names, and what
     the parts appear to encode. -->
<!-- If the ad list was capped, say which entities are mapped individually
     and that the tail is summarized (details in Data Gaps). -->

## Settings Inventory

<!-- Attribution settings, optimization goals, and billing events by ad set
     (grouped where they repeat). -->
<!-- Placements: Advantage+ versus manual, and which manual placements when
     manual. -->
<!-- Special ad categories declared, if any. -->
<!-- Pixels / datasets and the conversion events actually promoted by the ad
     sets. -->

## Rebuild Specs

<!-- Capture tier used: graph (Tier A, Route B token in the workspace .env),
     cli (Tier B, meta ads <resource> get --fields), or mcp (Tier C). -->
<!-- Snapshot file paths relative to the workspace root:
     memory/accounts/act_<ACCOUNT_ID>/specs/campaigns.jsonl, adsets.jsonl,
     ads.jsonl, creatives.jsonl, and index.json. -->
<!-- Entity counts per snapshot file (campaigns, ad sets, ads, creatives),
     and whether the ~200-ad cap trimmed the set. -->
<!-- Normalization applied (Tier C only): index-keyed arrays converted,
     currency strings paired with minor-unit integers, bid strategy labels
     mapped to enums (any left UNVERIFIED), attribution windows recorded as
     an observation. Write "none (raw API shapes)" on Tier A or B. -->
<!-- Per-creative enhancement enrollment summary for the top creatives:
     creative id, then each creative_features_spec key with OPT_IN, OPT_OUT,
     or default (key absent). On Tier C write "not readable on this tier". -->
<!-- Fields unavailable on this tier, named plainly (for example on mcp:
     degrees_of_freedom_spec, asset_feed_spec, attribution_spec,
     frequency_control_specs, tracking_specs, special_ad_categories), and
     the note that adding the Route B token upgrades the audit. -->

## Targeting Playbook

<!-- Geos, age ranges, and gender settings in use, and which ad sets use
     which. -->
<!-- Advantage+ audience usage versus original audiences. -->
<!-- Custom audiences and lookalikes referenced, by name where the backend
     provides names (IDs only on the CLI; note that in Data Gaps), plus
     exclusions. -->
<!-- Detailed-targeting themes: the interest and behavior clusters that
     recur. -->

## Creative and Copy Inventory

<!-- Format mix across running ads: image, video, carousel, dynamic, with
     rough counts. -->
<!-- Hooks and angles in use, each tied to the ads that carry it. -->
<!-- For each running ad (or each of the capped top spenders): primary text,
     headline, description, CTA, and destination URL, quoted verbatim. -->

## Top Performers

<!-- Top ads over the 90-day window by spend AND by the goal metric; name
     the goal metric and whether it came from BRAND.md Performance Targets
     or was inferred from the dominant objective. -->
<!-- Each top ad's numbers: spend, results, CPA or ROAS, CTR, frequency. -->
<!-- The winning copy, quoted verbatim. -->
<!-- What the winners share: format, angle, hook, audience, placement. -->

## Underperformers and Fatigue

<!-- High-spend ads whose efficiency sits far off the account's typical or
     target level, with their numbers. -->
<!-- Frequency or fatigue flags: high frequency, declining CTR across the
     window, rising CPA on a once-strong ad. -->
<!-- Numbers only from the backend; if a fatigue signal cannot be measured
     on this backend, it belongs in Data Gaps, not here. -->

## Breakdown Analysis

<!-- Age and gender: where spend goes and where results over- and
     under-index. -->
<!-- Placement and platform/device: same treatment (publisher platform,
     platform position, device platform). -->
<!-- Geo: countries or regions that over- and under-index. -->
<!-- Note the level each breakdown was pulled at (account, or a named
     campaign) and any breakdowns this backend could not provide. -->

## Learnings for New Ads

<!-- The distilled do/don't list the creative and copy skills must read
     before building net-new ads for this account. -->
<!-- Do lines: angles, formats, hooks, audiences, and placements the data
     supports doubling down on, each traceable to a section above. -->
<!-- Don't lines: what fatigued, what underperformed, what is already
     saturated and should not be repeated as-is. -->
<!-- Keep it short and concrete; this is the section that gets acted on. -->

## Data Gaps

<!-- What this backend could not provide (for example on the CLI: previews,
     media inventory, custom audience names, activity logs, anomaly
     signals). -->
<!-- Caps applied: how many ads were covered individually, how the tail was
     summarized, and any pagination limits hit. -->
<!-- Tool calls that failed or returned partial data, named plainly. -->

## Changelog

<!-- One dated entry per audit or refresh: date, backend used, window, and
     a one-line note of what changed in this file. -->
<!-- Newest entry first. Refreshes update the sections above in place and
     add an entry here; they never create a second file. -->
