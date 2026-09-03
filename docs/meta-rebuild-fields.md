# Exact-Rebuild Field Reference (Meta)

This is the pack's source of truth for capturing an ad account's real settings and rebuilding them faithfully: campaign settings, ad set targeting objects, placements, bidding, attribution, ad tracking, and creative specs including the Advantage+ creative enhancements that are opted in or out. The `account-audit` skill uses it to capture rebuild specs; the `meta-ad-launcher` skill uses it to mirror an existing entity when building net-new ads. Both skills carry a self-contained copy at `references/rebuild-fields.md`.

Everything here was verified on 3 September 2026 against three sources: the official Meta Ads MCP tool schemas plus its live field catalog (`ads_get_field_context`) and live reads; the compiled `meta-ads` 1.1.0 CLI binary (flag strings extracted directly, which surfaced flags the public docs omit); and the Marketing API reference pages (v25.0 and v26.0). Items that could not be confirmed are marked UNVERIFIED. Server versions change: always trust your live tool list, `--help`, and the API's own response over this document.

---

## 1. The three read tiers

An exact rebuild needs the raw API objects, not a summary. Three ways to read them exist, in descending fidelity. The audit uses the best one available and records which tier produced each snapshot.

| Tier | How | Fidelity | Needs |
|---|---|---|---|
| **A: Graph API direct read** | `GET https://graph.facebook.com/<version>/<ENTITY_ID>?fields=<list>` with the system user token (read-only, `curl` from the workspace root where `.env` holds `ACCESS_TOKEN`) | Complete: every field in section 3 | Route B token (SETUP.md Step 4, Route B). Never paste the token anywhere except the command |
| **B: Meta Ads CLI `get --fields`** | `meta ads <resource> get <ID> --fields <list> --output json` (resource = campaign, adset, or ad); creatives via `meta ads creative get <ID> --output json` | Complete for campaigns, ad sets, and ads (`--fields` passes Graph field names through). Creative: `get` returns the creative object; whether it includes `degrees_of_freedom_spec` and `asset_feed_spec` is UNVERIFIED, so fall back to Tier A for creatives | Route B |
| **C: Meta Ads MCP** | `ads_get_ad_entities` with `fields` at `campaign` / `adset` / `ad` level; `ads_get_creatives` with `creative_ids` | Partial. Strong on targeting and delivery settings, blind to attribution, frequency caps, bid constraints, and every creative spec (see section 4). Values come back display-formatted and need normalization (section 5) | Route A (MCP) |

**Practical rule.** If the Route B token is configured, use Tier A (or B) for the rebuild specs even when the MCP is the primary backend for everything else; it is the only way to read creative enhancement enrollment. If only the MCP is available, capture what it exposes, list the rest under "Data Gaps", and tell the user that adding the Route B token upgrades the audit to full fidelity. Never guess a missing field.

---

## 2. Snapshot layout

The audit writes raw objects next to the memory file, one JSON object per line, keyed by `id`:

```
memory/accounts/act_<ACCOUNT_ID>.md
memory/accounts/act_<ACCOUNT_ID>/specs/campaigns.jsonl
memory/accounts/act_<ACCOUNT_ID>/specs/adsets.jsonl
memory/accounts/act_<ACCOUNT_ID>/specs/ads.jsonl
memory/accounts/act_<ACCOUNT_ID>/specs/creatives.jsonl
memory/accounts/act_<ACCOUNT_ID>/specs/index.json
```

Each line carries the entity's fields exactly as returned, plus two pack-added keys: `_captured_via` (`graph`, `cli`, or `mcp`) and `_captured_at` (ISO date). `index.json` maps every id to its name, parent ids, status, and 90-day spend so the launcher can pick a reference entity without reparsing everything. `memory/` is gitignored; these files hold account IDs, audience IDs, pixel IDs, and full ad copy and must never be committed or pasted into chat.

---

## 3. Fields to capture, by entity

Request exactly these on Tier A or B. On Tier C, request the subset the MCP supports (section 4) and record the rest as gaps.

### Campaign

`id, name, status, effective_status, objective, buying_type, bid_strategy, daily_budget, lifetime_budget, spend_cap, budget_remaining, special_ad_categories, special_ad_category_country, promoted_object, is_skadnetwork_attribution, smart_promotion_type, pacing_type, budget_schedule_specs, is_budget_schedule_enabled, start_time, stop_time, source_campaign_id, adlabels, created_time, updated_time`

Budget mode is inferred: a campaign with `daily_budget` or `lifetime_budget` set is CBO; otherwise the ad sets carry budgets (ABO).

### Ad set

`id, name, campaign_id, status, effective_status, targeting, promoted_object, optimization_goal, optimization_sub_event, billing_event, bid_strategy, bid_amount, bid_constraints, attribution_spec, frequency_control_specs, pacing_type, adset_schedule, destination_type, is_dynamic_creative, dsa_beneficiary, dsa_payor, multi_optimization_goal_weight, targeting_optimization_types, daily_budget, lifetime_budget, budget_remaining, daily_min_spend_target, daily_spend_cap, start_time, end_time, learning_stage_info, source_adset_id, budget_schedule_specs, adlabels, created_time, updated_time`

**The targeting object.** These keys are writable and must be captured verbatim when present:

- Location: `geo_locations` (`countries`, `regions`, `cities`, `zips`, `places`, `custom_locations`, `location_types`), `excluded_geo_locations`
- Demographics: `age_min`, `age_max`, `age_range`, `genders`, `locales`, `relationship_statuses`, `education_statuses`, `education_schools`, `education_majors`, `college_years`, `work_employers`, `work_positions`, `life_events`, `industries`, `income`, `family_statuses`
- Audiences: `custom_audiences`, `excluded_custom_audiences`, `connections`, `excluded_connections`, `friends_of_connections`
- Detailed targeting: `flexible_spec` (each entry may hold `interests`, `behaviors`, and demographic keys), `exclusions`, `interests`, `behaviors`, `user_adclusters`
- Placements: `publisher_platforms`, `facebook_positions`, `instagram_positions`, `messenger_positions`, `audience_network_positions`, `threads_positions`, `device_platforms`
- Devices: `user_os`, `user_device`, `excluded_user_device`, `wireless_carrier`, `app_install_state`
- Automation and safety: `targeting_automation` (`advantage_audience`: 1 or 0, plus `individual_setting`), `brand_safety_content_filter_levels`, `excluded_publisher_categories`

Absence of every placement key means Advantage+ placements (all placements). Absence of `targeting_automation` on a new ad set means Advantage+ audience is on by default (the MCP and CLI both apply that default); to hard-cap age, gender, or geo, set `targeting_automation.advantage_audience` to 0 explicitly.

**Read-only echoes inside targeting** (present on read, must be stripped before any write): `effective_publisher_platforms`, `effective_facebook_positions`, `effective_instagram_positions`, `effective_messenger_positions`, `effective_audience_network_positions`, `effective_threads_positions`, `effective_device_platforms`, `effective_brand_safety_content_filter_levels`, `targeting_relaxation_types`, `targeting_optimization`, `dt_consolidation_state`, `page_types` (deprecated), and `location_types` inside `geo_locations` when the API added it.

The `effective_*` arrays are still valuable: they tell you exactly where the ad set actually delivers, which is what "all placements" resolved to. Record them in the memory file's Settings Inventory; do not write them back.

### Ad

`id, name, adset_id, campaign_id, status, effective_status, creative, tracking_specs, conversion_domain, adlabels, bid_amount, source_ad_id, ad_schedule_start_time, ad_schedule_end_time, display_sequence, engagement_audience, preview_shareable_link, created_time, updated_time`

`creative` returns `{ "id": "<CREATIVE_ID>" }`; capture the creative separately by that id.

### Creative

`id, name, status, object_type, object_story_spec, asset_feed_spec, degrees_of_freedom_spec, url_tags, contextual_multi_ads, instagram_user_id, effective_object_story_id, effective_instagram_media_id, object_story_id, call_to_action_type, image_hash, image_url, video_id, thumbnail_url, product_set_id, template_url, platform_customizations, portrait_customizations, use_page_actor_override, authorization_category, body, title, link_url, link_og_id, image_crops, applink_treatment`

Three sub-objects carry the rebuild:

- `object_story_spec`: `page_id`, `instagram_user_id`, and exactly one of `link_data` (link, message, name, description, caption, call_to_action, image_hash, child_attachments for carousels, multi_share_optimized, multi_share_end_card), `video_data` (video_id, image_hash or image_url thumbnail, title, message, link_description, call_to_action), `photo_data`, or `template_data` (catalog).
- `asset_feed_spec`: the multi-variant creative (`bodies`, `titles`, `descriptions`, `link_urls`, `call_to_action_types`, `images`, `videos`, `ad_formats`, `optimization_type`, `asset_customization_rules` for placement customization). Present on dynamic creative and flexible ads; absent on single-variant creatives.
- `degrees_of_freedom_spec`: `{ "creative_features_spec": { "<feature>": { "enroll_status": "OPT_IN" | "OPT_OUT", "customizations": { ... } } } }`. This is where Advantage+ creative enhancements live. Feature keys documented on the v26.0 Ad Creative Features Spec reference: `adapt_to_placement` (customizations `aspect_ratio_config`, `image_crop_style`), `add_text_overlay`, `ads_with_benefits`, `biz_ai`, `creative_stickers`, `customize_product_recommendation`, `description_automation`, `fb_feed_tag`, `fb_reels_tag`, `fb_story_tag`, `generate_cta`, `hide_price`, `ig_feed_tag`, `ig_reels_tag`, `ig_stream_tag`, `image_animation`, `image_background_gen`, `image_templates`, `image_touchups`, `inline_comment`, `local_store_extension`, `media_order`, `media_type_automation`, `multi_photo_to_video`, `music_generation`, `pac_relaxation`, `product_extensions`, `profile_card`, `profile_extension`, `replace_media_text`, `reveal_details_over_time`, `show_destination_blurbs`, `show_summary`, `site_extensions`, `standard_enhancements`, `standard_enhancements_catalog`, `text_extraction_for_headline`, `text_extraction_for_tap_target`, `text_optimizations`, `text_overlay_translation`, `text_translation`, `translate_voiceover`, `video_highlights`, `video_to_image`, `wa_mm_image_filtering`, `wa_mm_text_truncation_length`. Meta adds features over time; capture whatever keys the read returns and treat a missing key as "platform default", not as opted out.

---

## 4. Capability matrix (verified)

Read = can the route return the field as stored. Write = can the route set it on create. "Graph" means a direct Marketing API call with the Route B token.

| Field or object | MCP read | CLI read | Graph read | MCP write | CLI write | Graph write |
|---|---|---|---|---|---|---|
| Campaign objective, buying_type, bid_strategy, budgets, spend_cap, pacing, smart_promotion_type, special_ad_category_country | yes | yes (`--fields`) | yes | yes | yes (`--objective`, `--bid-strategy`, `--daily-budget`, `--lifetime-budget`, `--pacing-type`) | yes |
| Campaign `special_ad_categories` | no (only the country list) | yes | yes | yes | yes (`--special-ad-categories`) | yes |
| Campaign copy-from | n/a | n/a | n/a | yes (`source_campaign_id`) | UNVERIFIED | yes |
| Ad set `targeting` (full object) | yes (normalize, section 5) | yes | yes | yes (`targeting` raw JSON) | yes (`--targeting '<json>'` or `--targeting @file.json`) | yes |
| Ad set `promoted_object` | yes | yes | yes | yes | yes (`--promoted-object` JSON or `@file`, or `--pixel-id` + `--custom-event-type`) | yes |
| Ad set optimization_goal, billing_event, destination_type, bid_strategy, bid_amount, budgets, pacing, start/end | yes (bid_strategy as a display label) | yes | yes | yes | yes | yes |
| Ad set `attribution_spec` | no (windows only via `learning_stage_info.attribution_windows`) | yes | yes | yes | yes (`--attribution-spec`) | yes |
| Ad set `frequency_control_specs`, `bid_constraints`, `adset_schedule`, `is_dynamic_creative`, `dsa_beneficiary`, `dsa_payor` | no | yes | yes | yes | dsa yes (`--dsa-beneficiary`, `--dsa-payor`); the others UNVERIFIED on 1.1.0 | yes |
| Ad set placement controls | via `targeting` | via `targeting` | via `targeting` | yes (`targeting` keys, or `placement` / `placement_soft_opt_out`) | via `--targeting` JSON | yes |
| Ad set copy-from | n/a | n/a | n/a | yes (`source_adset_id`) | UNVERIFIED | yes |
| Ad `creative_id` link | yes (`creative_id`) | yes (`creative`) | yes | yes (`creative` with `creative_id`) | yes (`--creative-id`) | yes |
| Ad `tracking_specs`, `conversion_domain`, `adlabels` | conversion_domain yes; others no | yes | yes | yes | yes (`--tracking-specs`, `--conversion-domain`) | yes |
| Ad copy-from | n/a | n/a | n/a | yes (`source_ad_id`, draft mode) | UNVERIFIED | yes |
| Creative `object_story_spec` | no (flattened: body, title, link_url, image_hash, video_id, call_to_action_type, child_attachments) | UNVERIFIED (`creative get`) | yes | yes (`ads_create_creative` fields, or inline `object_story_spec` on `ads_create_ad`) | yes (`--object-story-spec` JSON or `@file`) | yes |
| Creative `asset_feed_spec` (multi-variant text and media) | no | UNVERIFIED | yes | no (single variant only; create several creatives instead) | yes (`--asset-feed-spec` JSON or `@file`; shortcuts `--bodies`, `--titles`, `--descriptions`, `--images`, `--videos`, `--call-to-actions`) | yes |
| Creative `degrees_of_freedom_spec` (enhancements on or off) | no | UNVERIFIED | yes | yes (`degrees_of_freedom_spec` as a JSON string; shortcuts `advantage_plus_creative`, `advantage_plus_creative_features`) | yes (`--degrees-of-freedom-spec` JSON or `@dof.json`) | yes |
| Creative `url_tags`, `contextual_multi_ads`, `authorization_category`, `applink_treatment` | no | UNVERIFIED | yes | no parameter exposed (UNVERIFIED whether inline `creative` JSON on `ads_create_ad` passes them through) | yes (`--url-tags`, `--contextual-multi-ads`, `--authorization-category`, `--applink-treatment`) | yes |
| Creative `instagram_user_id` | effective media id only | UNVERIFIED | yes | yes (`instagram_user_id`) | yes (`--instagram-actor-id`) | yes |

Bottom line: **full fidelity capture needs Tier A or B (the Route B token)**; **full fidelity rebuild is possible on both routes**, with the CLI covering every creative-level field natively and the MCP covering everything except multi-variant `asset_feed_spec` and `url_tags` (work around with several single-variant creatives, or use the CLI for that creative).

---

## 5. Normalizing MCP reads

The MCP returns display-formatted values in places. Before a snapshot from Tier C is reused, apply these transformations and note them in the memory file:

- **Index-keyed arrays.** Lists inside `targeting` and `promoted_object` can arrive as objects with string indexes, for example `{"0": "US", "1": "CA"}`. Convert them back to arrays (`["US", "CA"]`) before storing or writing.
- **Currency strings.** `daily_budget`, `lifetime_budget`, `spend_cap`, `bid_amount` arrive like `"$50.00 USD"`. Store both the display string and the integer minor-unit value (`5000`); every write takes minor units.
- **Bid strategy labels.** `bid_strategy` arrives as a label. Map: `Highest volume` or `Lowest cost` to `LOWEST_COST_WITHOUT_CAP`; `Cost per result goal` or `Cost cap` to `COST_CAP`; `Bid cap` to `LOWEST_COST_WITH_BID_CAP`; `ROAS goal` or `Minimum ROAS` to `LOWEST_COST_WITH_MIN_ROAS`. If a label is not in this list, keep the label and mark the enum UNVERIFIED rather than guessing.
- **Attribution.** The MCP does not return `attribution_spec`. `learning_stage_info.attribution_windows` (for example `["7d_click", "1d_view"]`) reveals the windows in use; record it as an observation and, on rebuild, express it as `attribution_spec` (`[{"event_type":"CLICK_THROUGH","window_days":7},{"event_type":"VIEW_THROUGH","window_days":1}]`) only after the user confirms.
- **Times.** ISO strings with offsets; keep as returned.

Tier A and B return the raw API shapes and need none of this.

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
8. **Creative**: reuse `object_story_spec` shape with the new media (`image_hash` or `video_id`) and the new copy; carry `degrees_of_freedom_spec` verbatim (the enhancement enrollment is the point of mirroring), carry `url_tags`, `contextual_multi_ads`, `instagram_user_id`, `call_to_action` unless the brief changes them; carry `asset_feed_spec` structure when the reference was multi-variant (CLI or Graph only).
9. **Special ad categories** carry over exactly; they change what targeting is legal.
10. **Fastest exact copy on the MCP**: `ads_create_campaign` with `source_campaign_id`, then `ads_create_ad_set` with `source_adset_id` plus the new name and parent (and the full `targeting` JSON as a belt-and-braces override), then `ads_create_creative` with the mirrored `degrees_of_freedom_spec`, then `ads_create_ad` with `creative_id` and the mirrored `tracking_specs` and `conversion_domain`.

---

## 7. Verify after create

A mirror is only exact if you check it. After creating, read the new entity back with the same tier used for the reference (Tier A or B preferred) and compare field by field against the cleaned reference spec:

- Ad set: `targeting` (deep compare after normalization), `promoted_object`, `optimization_goal`, `billing_event`, `bid_strategy`, `bid_amount`, `attribution_spec`, `frequency_control_specs`, `destination_type`, `pacing_type`, `is_dynamic_creative`, budget mode.
- Ad: `creative.id` set, `tracking_specs`, `conversion_domain`.
- Creative: `degrees_of_freedom_spec.creative_features_spec` per feature (`enroll_status` must match), `url_tags`, `instagram_user_id`, `call_to_action_type`, media ids.

Report every delta to the user with the field name, expected value, and actual value, and never silently accept a difference. Expected, harmless deltas: new ids, `PAUSED` status, the new name, new parent ids, new media hashes, and any `effective_*` echoes the platform recomputes.

---

## 8. Known limits and open items

- **MCP-only setups cannot read creative enhancement enrollment or ad set attribution / frequency settings.** The audit says so in Data Gaps and recommends the Route B token. This is a limit of the MCP's read surface as of September 2026, not of the Marketing API.
- **Whether `meta ads creative get` returns `degrees_of_freedom_spec` and `asset_feed_spec` is UNVERIFIED** on 1.1.0; the Tier A read is the guaranteed path for creatives.
- **CLI flags for `frequency_control_specs`, `bid_constraints`, `adset_schedule`, `is_dynamic_creative`, and the `source_*` copy-from fields are UNVERIFIED** on 1.1.0 (`meta ads adset create --help` is authoritative). Use Tier A (Graph POST with the same token) when a native flag is missing, still PAUSED and still confirm-gated.
- **Direct Graph writes are last resort**, only for fields no native MCP tool or CLI flag exposes, and only after the same explicit confirmation the launcher requires for every create.
- **Never treat a missing key as a setting.** Absent placement keys mean Advantage+ placements; an absent `degrees_of_freedom_spec` means platform defaults; record these as observed defaults, not as opt-outs.
