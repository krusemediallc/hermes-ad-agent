# Rebuild Field Reference for the launcher (Meta)

This is the launcher's self-contained copy of the pack's exact-rebuild reference. It tells the mirror mode which fields make up a campaign, an ad set, an ad, and a creative (including the Advantage+ creative enhancements that are opted in or out), how to read them at full fidelity, how to turn a captured reference into a clean write, and how to prove the copy is exact afterwards. Sections 6 (cloning rules) and 7 (verify after create) are the heart of it for this skill; sections 1 to 5 exist so the launcher can do a live read when no audit snapshot exists.

Everything here was verified on 3 September 2026 against three sources: the official Meta Ads MCP tool schemas plus its live field catalog (`ads_get_field_context`) and live reads; the compiled `meta-ads` 1.1.0 CLI binary (flag strings extracted directly, which surfaced flags the public docs omit); and the Marketing API reference pages (v25.0 and v26.0). Items that could not be confirmed are marked UNVERIFIED. Server versions change: always trust your live tool list, `--help`, and the API's own response over this document.

---

## 1. The three read tiers

An exact mirror needs the raw API objects, not a summary. Three ways to read them exist, in descending fidelity. Use the best one available and record which tier produced the reference.

| Tier | How | Fidelity | Needs |
|---|---|---|---|
| **A: Graph API direct read** | `GET https://graph.facebook.com/<version>/<ENTITY_ID>?fields=<list>` with the system user token (read-only, `curl` from the workspace root where `.env` holds `ACCESS_TOKEN`) | Complete: every field in section 3 | Route B token (SETUP.md Step 4, Route B). Never paste the token anywhere except the command |
| **B: Meta Ads CLI `get --fields`** | `meta ads <resource> get <ID> --fields <list> --output json` where `<resource>` is `campaign`, `adset`, or `ad`; creatives via `meta ads creative get <ID> --output json` | Complete for campaigns, ad sets, and ads (`--fields` passes Graph field names through). Creative: `get` returns the creative object; whether it includes `degrees_of_freedom_spec` and `asset_feed_spec` is UNVERIFIED, so fall back to Tier A for creatives | Route B |
| **C: Meta Ads MCP** | `ads_get_ad_entities` with `fields` at `campaign` / `adset` / `ad` level; `ads_get_creatives` with `creative_ids` | Partial. Strong on targeting and delivery settings, blind to attribution, frequency caps, bid constraints, and every creative spec (see section 4). Values come back display-formatted and need normalization (section 5) | Route A (MCP) |

**Practical rule.** If the Route B token is configured, use Tier A (or B) for the reference read even when the MCP is the primary backend for everything else; it is the only way to read creative enhancement enrollment. If only the MCP is available, mirror what it exposes, list the rest as gaps in the plan, and tell the user that adding the Route B token upgrades the mirror to full fidelity. Never guess a missing field.

**Tier A command shape.** Run it from the workspace root so `.env` is in scope, and let the shell substitute the token into the request:

```
source .env && curl -s "https://graph.facebook.com/v25.0/<ENTITY_ID>?fields=<list>&access_token=$ACCESS_TOKEN"
```

The token must never be echoed, logged, or pasted into chat, memory files, or job prompts. Do not `cat .env`, do not `echo $ACCESS_TOKEN`, do not run the shell with `set -x` or any tracing that prints expanded commands, and do not save the raw curl command line anywhere; save only the JSON response. If a response happens to include the token (it should not), strip it before storing.

---

## 2. Snapshot layout

The `account-audit` skill writes raw objects next to the memory file, one JSON object per line, keyed by `id`:

```
memory/accounts/act_<ACCOUNT_ID>.md
memory/accounts/act_<ACCOUNT_ID>/specs/campaigns.jsonl
memory/accounts/act_<ACCOUNT_ID>/specs/adsets.jsonl
memory/accounts/act_<ACCOUNT_ID>/specs/ads.jsonl
memory/accounts/act_<ACCOUNT_ID>/specs/creatives.jsonl
memory/accounts/act_<ACCOUNT_ID>/specs/index.json
```

Each line carries the entity's fields exactly as returned, plus two pack-added keys: `_captured_via` (`graph`, `cli`, or `mcp`) and `_captured_at` (ISO date). `index.json` maps every id to its name, parent ids, status, and 90-day spend so the launcher can pick a reference entity without reparsing everything. `memory/` is gitignored; these files hold account IDs, audience IDs, pixel IDs, and full ad copy and must never be committed or pasted into chat.

The launcher reads these files; it does not write them. When the launcher does a live read because no snapshot exists, it keeps the raw JSON in the run folder (or in memory only) for the verify step and does not create the snapshot files itself; that stays the audit's job.

---

## 3. Fields to capture, by entity

Request exactly these on Tier A or B. On Tier C, request the subset the MCP supports (section 4) and record the rest as gaps.

### Campaign

`id, name, status, effective_status, objective, buying_type, bid_strategy, daily_budget, lifetime_budget, spend_cap, budget_remaining, special_ad_categories, special_ad_category_country, promoted_object, is_skadnetwork_attribution, smart_promotion_type, pacing_type, budget_schedule_specs, is_budget_schedule_enabled, start_time, stop_time, source_campaign_id, adlabels, created_time, updated_time`

Budget mode is inferred: a campaign with `daily_budget` or `lifetime_budget` set is CBO; otherwise the ad sets carry budgets (ABO).

### Ad set

`id, name, campaign_id, status, effective_status, targeting, promoted_object, optimization_goal, optimization_sub_event, billing_event, bid_strategy, bid_amount, bid_constraints, attribution_spec, frequency_control_specs, pacing_type, adset_schedule, destination_type, is_dynamic_creative, dsa_beneficiary, dsa_payor, multi_optimization_goal_weight, targeting_optimization_types, daily_budget, lifetime_budget, budget_remaining, daily_min_spend_target, daily_spend_cap, start_time, end_time, learning_stage_info, source_adset_id, budget_schedule_specs, adlabels, created_time, updated_time`

**The targeting object.** These keys are writable and must be carried verbatim when present:

- Location: `geo_locations` (`countries`, `regions`, `cities`, `zips`, `places`, `custom_locations`, `location_types`), `excluded_geo_locations`
- Demographics: `age_min`, `age_max`, `age_range`, `genders`, `locales`, `relationship_statuses`, `education_statuses`, `education_schools`, `education_majors`, `college_years`, `work_employers`, `work_positions`, `life_events`, `industries`, `income`, `family_statuses`
- Audiences: `custom_audiences`, `excluded_custom_audiences`, `connections`, `excluded_connections`, `friends_of_connections`
- Detailed targeting: `flexible_spec` (each entry may hold `interests`, `behaviors`, and demographic keys), `exclusions`, `interests`, `behaviors`, `user_adclusters`
- Placements: `publisher_platforms`, `facebook_positions`, `instagram_positions`, `messenger_positions`, `audience_network_positions`, `threads_positions`, `device_platforms`
- Devices: `user_os`, `user_device`, `excluded_user_device`, `wireless_carrier`, `app_install_state`
- Automation and safety: `targeting_automation` (`advantage_audience`: 1 or 0, plus `individual_setting`), `brand_safety_content_filter_levels`, `excluded_publisher_categories`

Absence of every placement key means Advantage+ placements (all placements). Absence of `targeting_automation` on a new ad set means Advantage+ audience is on by default (the MCP and CLI both apply that default); to hard-cap age, gender, or geo, set `targeting_automation.advantage_audience` to 0 explicitly. When the reference carries `targeting_automation`, write it exactly as read so the new ad set lands on the same setting.

**Read-only echoes inside targeting** (present on read, must be stripped before any write): `effective_publisher_platforms`, `effective_facebook_positions`, `effective_instagram_positions`, `effective_messenger_positions`, `effective_audience_network_positions`, `effective_threads_positions`, `effective_device_platforms`, `effective_brand_safety_content_filter_levels`, `targeting_relaxation_types`, `targeting_optimization`, `dt_consolidation_state`, `page_types` (deprecated), and `location_types` inside `geo_locations` when the API added it.

The `effective_*` arrays are still valuable: they tell you exactly where the reference ad set actually delivers, which is what "all placements" resolved to. Use them in the plan's placements summary; do not write them back.

### Ad

`id, name, adset_id, campaign_id, status, effective_status, creative, tracking_specs, conversion_domain, adlabels, bid_amount, source_ad_id, ad_schedule_start_time, ad_schedule_end_time, display_sequence, engagement_audience, preview_shareable_link, created_time, updated_time`

`creative` returns `{ "id": "<CREATIVE_ID>" }`; read the creative separately by that id.

### Creative

`id, name, status, object_type, object_story_spec, asset_feed_spec, degrees_of_freedom_spec, url_tags, contextual_multi_ads, instagram_user_id, effective_object_story_id, effective_instagram_media_id, object_story_id, call_to_action_type, image_hash, image_url, video_id, thumbnail_url, product_set_id, template_url, platform_customizations, portrait_customizations, use_page_actor_override, authorization_category, body, title, link_url, link_og_id, image_crops, applink_treatment`

Three sub-objects carry the rebuild:

- `object_story_spec`: `page_id`, `instagram_user_id`, and exactly one of `link_data` (link, message, name, description, caption, call_to_action, image_hash, child_attachments for carousels, multi_share_optimized, multi_share_end_card), `video_data` (video_id, image_hash or image_url thumbnail, title, message, link_description, call_to_action), `photo_data`, or `template_data` (catalog).
- `asset_feed_spec`: the multi-variant creative (`bodies`, `titles`, `descriptions`, `link_urls`, `call_to_action_types`, `images`, `videos`, `ad_formats`, `optimization_type`, `asset_customization_rules` for placement customization). Present on dynamic creative and flexible ads; absent on single-variant creatives.
- `degrees_of_freedom_spec`: `{ "creative_features_spec": { "<feature>": { "enroll_status": "OPT_IN" | "OPT_OUT", "customizations": { ... } } } }`. This is where Advantage+ creative enhancements live. Feature keys documented on the v26.0 Ad Creative Features Spec reference: `adapt_to_placement` (customizations `aspect_ratio_config`, `image_crop_style`), `add_text_overlay`, `ads_with_benefits`, `biz_ai`, `creative_stickers`, `customize_product_recommendation`, `description_automation`, `fb_feed_tag`, `fb_reels_tag`, `fb_story_tag`, `generate_cta`, `hide_price`, `ig_feed_tag`, `ig_reels_tag`, `ig_stream_tag`, `image_animation`, `image_background_gen`, `image_templates`, `image_touchups`, `inline_comment`, `local_store_extension`, `media_order`, `media_type_automation`, `multi_photo_to_video`, `music_generation`, `pac_relaxation`, `product_extensions`, `profile_card`, `profile_extension`, `replace_media_text`, `reveal_details_over_time`, `show_destination_blurbs`, `show_summary`, `site_extensions`, `standard_enhancements`, `standard_enhancements_catalog`, `text_extraction_for_headline`, `text_extraction_for_tap_target`, `text_optimizations`, `text_overlay_translation`, `text_translation`, `translate_voiceover`, `video_highlights`, `video_to_image`, `wa_mm_image_filtering`, `wa_mm_text_truncation_length`. Meta adds features over time; carry whatever keys the read returns and treat a missing key as "platform default", not as opted out.

---

## 4. Capability matrix (verified)

Read = can the route return the field as stored. Write = can the route set it on create. "Graph" means a direct Marketing API call with the Route B token; in this pack that call is GET only (Tier A capture and diagnostics), so the "Graph write" column reads "not supported" on every row: writes go through the Meta MCP or the Meta Ads CLI, never through an improvised Graph POST.

| Field or object | MCP read | CLI read | Graph read | MCP write | CLI write | Graph write (this pack) |
|---|---|---|---|---|---|---|
| Campaign objective, buying_type, bid_strategy, budgets, spend_cap, pacing, smart_promotion_type, special_ad_category_country | yes | yes (`--fields`) | yes | yes | yes (`--objective`, `--bid-strategy`, `--daily-budget`, `--lifetime-budget`, `--pacing-type`) | not supported |
| Campaign `special_ad_categories` | no (only the country list) | yes | yes | yes | yes (`--special-ad-categories`) | not supported |
| Campaign copy-from | n/a | n/a | n/a | yes (`source_campaign_id`) | UNVERIFIED | not supported |
| Ad set `targeting` (full object) | yes (normalize, section 5) | yes | yes | yes (`targeting` raw JSON) | yes (`--targeting '<json>'` or `--targeting @file.json`) | not supported |
| Ad set `promoted_object` | yes | yes | yes | yes | yes (`--promoted-object` JSON or `@file`, or `--pixel-id` + `--custom-event-type`) | not supported |
| Ad set optimization_goal, billing_event, destination_type, bid_strategy, bid_amount, budgets, pacing, start/end | yes (bid_strategy as a display label) | yes | yes | yes | yes | not supported |
| Ad set `attribution_spec` | no (windows only via `learning_stage_info.attribution_windows`) | yes | yes | yes | yes (`--attribution-spec`) | not supported |
| Ad set `frequency_control_specs`, `bid_constraints`, `adset_schedule`, `is_dynamic_creative`, `dsa_beneficiary`, `dsa_payor` | no | yes | yes | yes | dsa yes (`--dsa-beneficiary`, `--dsa-payor`); the others UNVERIFIED on 1.1.0 | not supported |
| Ad set placement controls | via `targeting` | via `targeting` | via `targeting` | yes (`targeting` keys, or `placement` / `placement_soft_opt_out`) | via `--targeting` JSON | not supported |
| Ad set copy-from | n/a | n/a | n/a | yes (`source_adset_id`) | UNVERIFIED | not supported |
| Ad `creative_id` link | yes (`creative_id`) | yes (`creative`) | yes | yes (`creative` with `creative_id`) | yes (`--creative-id`) | not supported |
| Ad `tracking_specs`, `conversion_domain`, `adlabels` | conversion_domain yes; others no | yes | yes | yes | yes (`--tracking-specs`, `--conversion-domain`) | not supported |
| Ad copy-from | n/a | n/a | n/a | yes (`source_ad_id`, draft mode) | UNVERIFIED | not supported |
| Creative `object_story_spec` | no (flattened: body, title, link_url, image_hash, video_id, call_to_action_type, child_attachments) | UNVERIFIED (`creative get`) | yes | yes (`ads_create_creative` fields, or inline `object_story_spec` on `ads_create_ad`) | yes (`--object-story-spec` JSON or `@file`) | not supported |
| Creative `asset_feed_spec` (multi-variant text and media) | no | UNVERIFIED | yes | no (scalar `message` / `headline` / `description` only; the one flexible 5 / 5 / 3 creative this pack requires is built on the CLI) | yes (`--asset-feed-spec` JSON or `@file`; shortcuts `--bodies`, `--titles`, `--descriptions`, `--images`, `--videos`, `--call-to-actions`) | not supported |
| Creative `degrees_of_freedom_spec` (enhancements on or off) | no | UNVERIFIED | yes | yes (`degrees_of_freedom_spec` as a JSON string; shortcuts `advantage_plus_creative`, `advantage_plus_creative_features`) | yes (`--degrees-of-freedom-spec` JSON or `@dof.json`) | not supported |
| Creative `url_tags`, `contextual_multi_ads`, `authorization_category`, `applink_treatment` | no | UNVERIFIED | yes | no parameter exposed (UNVERIFIED whether inline `creative` JSON on `ads_create_ad` passes them through) | yes (`--url-tags`, `--contextual-multi-ads`, `--authorization-category`, `--applink-treatment`) | not supported |
| Creative `instagram_user_id` | effective media id only | UNVERIFIED | yes | yes (`instagram_user_id`) | yes (`--instagram-actor-id`) | not supported |
| Creative media upload (the image or video file itself) | n/a | n/a | n/a | `ads_creative_upload_image` / `ads_creative_upload_video` take a public URL only, never a local path; a "this tool is new and is being gradually rolled out" reply means unavailable for the account, not bad credentials | yes (`--image ./file` / `--video ./file` upload a local file inside `creative create`) | not supported |

Bottom line: **full fidelity capture needs Tier A or B (the Route B token)**; **full fidelity rebuild needs the CLI for the creative**, because the CLI covers every creative-level field natively (including `asset_feed_spec` and local media upload) while the MCP covers everything except multi-variant `asset_feed_spec`, `url_tags`, and local files. The pack's rule is one flexible creative per media asset carrying the whole copy pool (5 primary texts, 5 headlines, 3 descriptions), so on an MCP-only setup the launcher stops before the creative and lets the user choose (install the CLI route, or explicitly accept a single variant); it never splits the pool across several ads and never writes through the Graph API.

---

## 5. Normalizing MCP reads

The MCP returns display-formatted values in places. Before a Tier C read is used as a reference, apply these transformations and note them in the plan:

- **Index-keyed arrays.** Lists inside `targeting` and `promoted_object` can arrive as objects with string indexes, for example `{"0": "US", "1": "CA"}`. Convert them back to arrays (`["US", "CA"]`) before storing or writing.
- **Currency strings.** `daily_budget`, `lifetime_budget`, `spend_cap`, `bid_amount` arrive like `"$50.00 USD"`. Keep both the display string and the integer minor-unit value (`5000`); every write takes minor units.
- **Bid strategy labels.** `bid_strategy` arrives as a label. Map: `Highest volume` or `Lowest cost` to `LOWEST_COST_WITHOUT_CAP`; `Cost per result goal` or `Cost cap` to `COST_CAP`; `Bid cap` to `LOWEST_COST_WITH_BID_CAP`; `ROAS goal` or `Minimum ROAS` to `LOWEST_COST_WITH_MIN_ROAS`. If a label is not in this list, keep the label and mark the enum UNVERIFIED rather than guessing.
- **Attribution.** The MCP does not return `attribution_spec`. `learning_stage_info.attribution_windows` (for example `["7d_click", "1d_view"]`) reveals the windows in use; record it as an observation and, on rebuild, express it as `attribution_spec` (`[{"event_type":"CLICK_THROUGH","window_days":7},{"event_type":"VIEW_THROUGH","window_days":1}]`) only after the user confirms.
- **Times.** ISO strings with offsets; keep as returned.

Tier A and B return the raw API shapes and need none of this. Snapshot lines with `_captured_via: "mcp"` were normalized by the audit already, but re-check the four points above before writing, because a normalized snapshot still carries the gaps (no `attribution_spec`, no creative specs).

---

## 6. Cloning rules (mirror mode)

When rebuilding from a captured spec, start from the raw object and apply, in order:

1. **Strip identity and state**: `id`, `account_id`, `created_time`, `updated_time`, `status`, `effective_status`, `budget_remaining`, `learning_stage_info`, `preview_shareable_link`, `effective_object_story_id`, `effective_instagram_media_id`, `_captured_via`, `_captured_at`.
2. **Strip read-only echoes** listed in section 3 (all `effective_*` keys, `targeting_relaxation_types`, `targeting_optimization`, `dt_consolidation_state`, `page_types`, `multi_optimization_goal_weight`, `targeting_optimization_types`, `is_budget_schedule_enabled`, `campaign_group_active_time`).
3. **Re-parent**: set the new `campaign_id` (ad set) or `adset_id` (ad); never reuse the source parent unless the user chose "existing structure".
4. **Record provenance**: set `source_campaign_id`, `source_adset_id`, or `source_ad_id` to the reference id so Meta's own lineage shows the copy.
5. **Rename** per the account's naming convention from the memory file's Structure Map.
6. **Budgets and schedule**: carry the budget mode (CBO or ABO) exactly; set amounts from the user's brief, compared against the BRAND.md daily spend cap; drop `start_time` and `end_time` unless the user asked for a schedule.
7. **Status**: always `PAUSED` on every entity.
8. **Creative**: reuse `object_story_spec` shape with the new media (`image_hash` or `video_id`) and the new copy; carry `degrees_of_freedom_spec` verbatim (the enhancement enrollment is the point of mirroring), carry `url_tags`, `contextual_multi_ads`, `instagram_user_id`, `call_to_action` unless the brief changes them; carry `asset_feed_spec` structure with the approved copy pool inside it (CLI only; `ads_create_creative` cannot write it, and the pack's one-flexible-creative-per-asset rule applies whether or not the reference was multi-variant).
9. **Special ad categories** carry over exactly; they change what targeting is legal.
10. **Fastest exact copy on the MCP**: `ads_create_campaign` with `source_campaign_id`, then `ads_create_ad_set` with `source_adset_id` plus the new name and parent (and the full `targeting` JSON as a belt-and-braces override), then `ads_create_creative` with the mirrored `degrees_of_freedom_spec`, then `ads_create_ad` with `creative_id` and the mirrored `tracking_specs` and `conversion_domain`.

The output of steps 1 to 9 is the **cleaned reference**: one JSON object per entity that contains only writable fields, the new name, the new parent, the provenance field, the user-approved budget, and `PAUSED`. Keep it in the run folder (never in git, never in chat): the write step sends it, and the verify step diffs against it.

What the cleaned reference must still show the user before any create (the plan summary): objective and buying type, special ad categories, budget mode and the amount versus the BRAND.md cap, optimization goal and billing event, bid strategy (and bid amount or constraints if present), attribution windows, targeting summary (geo, ages, genders, audiences included and excluded, detailed targeting, `targeting_automation`), placements (explicit keys, or "Advantage+ placements" when absent, with the reference's `effective_*` arrays as the observed resolution), destination type and promoted object, tracking specs and conversion domain, and the enhancement enrollment per feature (`OPT_IN` / `OPT_OUT` list, or "platform defaults" when the reference has no `degrees_of_freedom_spec`).

---

## 7. Verify after create

A mirror is only exact if you check it. After creating, read the new entity back with the same tier used for the reference (Tier A or B preferred) and compare field by field against the cleaned reference spec:

- Ad set: `targeting` (deep compare after normalization), `promoted_object`, `optimization_goal`, `billing_event`, `bid_strategy`, `bid_amount`, `attribution_spec`, `frequency_control_specs`, `destination_type`, `pacing_type`, `is_dynamic_creative`, budget mode.
- Ad: `creative.id` set, `tracking_specs`, `conversion_domain`.
- Creative: `degrees_of_freedom_spec.creative_features_spec` per feature (`enroll_status` must match), `url_tags`, `instagram_user_id`, `call_to_action_type`, media ids.

Campaign fields are cheap to include in the same pass: `objective`, `buying_type`, `bid_strategy`, `special_ad_categories`, `special_ad_category_country`, `spend_cap`, `pacing_type`, `smart_promotion_type`, and budget mode.

Report every delta to the user with the field name, expected value, and actual value, and never silently accept a difference. Expected, harmless deltas: new ids, `PAUSED` status, the new name, new parent ids, new media hashes, and any `effective_*` echoes the platform recomputes.

Rules for the comparison itself:

- Deep-compare `targeting` after stripping the read-only echoes from the read-back and after applying section 5 normalization if the read-back came from the MCP. Array order inside `flexible_spec`, `custom_audiences`, and placement lists is not a delta; a missing or extra element is.
- A key present in the cleaned reference but absent in the read-back is a delta (report `actual: absent`). A key absent from the reference but present in the read-back is a delta unless it is on the harmless list or is a platform default the reference never carried (say which).
- When the read-back tier cannot see a field (Tier C cannot read `attribution_spec` or any creative spec), report that field as `unverifiable on this tier`, not as matched. Offer the Route B token as the fix.
- A verify read that fails is not a pass. Say the read failed, keep the created IDs in the report, and mark the mirror unverified.

---

## 8. Known limits and open items

- **MCP-only setups cannot read creative enhancement enrollment or ad set attribution / frequency settings.** The plan says so under gaps and recommends the Route B token. This is a limit of the MCP's read surface as of September 2026, not of the Marketing API.
- **Whether `meta ads creative get` returns `degrees_of_freedom_spec` and `asset_feed_spec` is UNVERIFIED** on 1.1.0; the Tier A read is the guaranteed path for creatives.
- **CLI flags for `frequency_control_specs`, `bid_constraints`, `adset_schedule`, `is_dynamic_creative`, and the `source_*` copy-from fields are UNVERIFIED** on 1.1.0 (`meta ads adset create --help` is authoritative). When a native flag is missing on the backend in use, check whether the other backend's live schema takes the field; if neither does, the field cannot be set on this setup: say so in the plan and list it as a delta in the verify report.
- **Direct Graph writes are not supported by this pack.** The Route B token is used for Tier A reads (capture and diagnostics) only. Every write goes through the Meta MCP or the Meta Ads CLI; multi-variant `asset_feed_spec` and local media upload live on the CLI route (`meta ads creative create` with the repeated plural flags or `--asset-feed-spec @feed.json`, and `--image ./file` / `--video ./file`). If neither backend can write a field, stop and say so; never improvise a Graph POST or a Graph upload.
- **Never treat a missing key as a setting.** Absent placement keys mean Advantage+ placements; an absent `degrees_of_freedom_spec` means platform defaults; carry these as observed defaults, not as opt-outs.
