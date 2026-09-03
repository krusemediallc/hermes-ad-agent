---
name: nano-banana-image-ad
description: Generate standalone Meta image-ad creatives with the Nano Banana model family (default nano-banana-2, Google's Gemini Flash Image) through the Arcads MCP server. Best for photoreal, lifestyle, material-rich, and multi-reference ads such as handheld signs, sticky-note flatlays, lifestyle photography, and product-in-scene compositions, with up to 14 reference images. Use when the user says "nano banana ad", "photoreal image ad", "lifestyle ad creative", "multi-reference product ad", "make an image ad" with a photographic concept, or wants ad stills for a specific product from reference photos. This skill produces image files only; copy and Meta upload hand off to the human-ad-copy and meta-ad-launcher skills. For typography-heavy or UI-mimicry ads use chatgpt-image-ad instead. To reverse-engineer an existing ad into a reusable template use image-ad-clone.
---

# nano-banana-image-ad

You generate standalone Meta image-ad creatives with the Nano Banana family (default `nano-banana-2`) through the Arcads MCP server. All generation goes through the Arcads MCP tools: no Arcads API keys, no HTTP scripts. The Arcads MCP server handles its own auth. Output is image files saved to the workspace; ad copy and Meta upload are separate skills.

## Before you start

1. **Check your tool list.** The bare `arcads_*` names below are the server-native tool IDs the Arcads MCP advertises; the Hermes runtime registers each one under a prefixed callable name (observed shape: `mcp__arcads__arcads_watch_asset`). Discover the registered name for each tool you need (tool_search or your live tool list) and call that. Server versions differ and tool counts drift day to day, so readiness is "the tools this skill needs are registered", never a count. If a tool is missing or a call returns `-32602 (tool not found)`, reload the MCP connection, re-discover the name, and check again.
2. **Read the user's BRAND.md** (created by the brand-setup skill during install) for brand name, colors, product description, and tagline. You will need these to fill prompt placeholders. If BRAND.md is missing, offer to run brand-setup first; the user can also decline and give you brand details inline.
3. **Arcads account required.** If the Arcads MCP tools are not connected at all, tell the user to connect the Arcads MCP server in their Hermes MCP settings and stop.

## Arcads cost contract (read before the credit gate)

- **Only `creditsCharged` is cost.** Read it back from each asset (`arcads_watch_asset` returns it). Some responses also carry an `mp` field; that is megapixel or usage metadata, never credits. Reading `mp` as credits has understated real cost by hundreds of times on video; treat it the same way on images.
- **No fixed credit figures.** Arcads has no quote or billing endpoint and this file carries no rate. The only historical datapoint in this pack (a 12-second 720p Seedance video charging 432 credits on one account in early September 2026) is a video observation on one account, not a rate and not relevant to image pricing.
- **Every Arcads operation is credit-accounted**, including ones that return `creditsCharged: 0` under a daily limit: generations, retries, QA-fix regenerations, `arcads_analyze_media`, any editing tool. None of them run automatically; they run only when the approval named them with a count-and-cost allowance, otherwise ask again before each one.
- **Signed `downloadUrl` and `presignedUrl` values are temporary credentials.** Pass them between tools as opaque values; never paste one into a terminal command line, a log line, the usage log, or any durable file. Download with a fetch step that reads the URL from a variable or stdin rather than a command argument, and save files under `outputs/nano-banana-image-ad/<slug>/`.

## Model choice: is this the right skill?

| The user wants... | Skill |
|---|---|
| Handheld whiteboard or posterboard signs, handwritten napkin testimonials, sticky-note + product flatlays, letter-board signs, lifestyle scenes, OOH/transit photography, scratch-off tickets, anything photoreal / material-rich / multi-reference | **this skill** (nano-banana-2) |
| Apple Notes lists, fake search results, chat threads, ChatGPT-style conversations, iOS dialogs, Slack snapshots, comparison tables, dating-app cards, iMessage, calendar UI, weather UI, magazine covers, anything typography-heavy or UI-mimicry | **chatgpt-image-ad** (gpt-image-2) |
| Turn an existing ad image into a reusable template | **image-ad-clone** |

If the brief is ambiguous, check the matching template's Model notes in the shared prompt library (see Phase 2); every entry recommends a backend.

## Tools used (Arcads MCP)

| Tool | Role |
|---|---|
| `arcads_generate_image_nano_banana` | Generate the ad. Params: `prompt`, `model`, `aspectRatio`, `referenceImages` (max 14), `nbGenerations` (1-10), optional `productId`. |
| `arcads_get_upload_url` | Presigned upload URL for each local reference image (see Reference images below). |
| `arcads_watch_asset` | Poll status AND fetch the signed `downloadUrl` in one call. The primary poll tool. |
| `arcads_list_products` | Resolve `productId` (optional; auto-selects when the account has one product). |

### `arcads_generate_image_nano_banana` parameters

| Param | Value | Notes |
|---|---|---|
| `prompt` | string (required) | The rewritten ad prompt from Phase 2, with the three safety suffixes appended. |
| `model` | `"nano-banana-2"` (default) or `"nano-banana"` | Only these two on the MCP tool. `nano-banana-2` supports up to 14 refs and is the standard for ad creatives. There is no `-pro` or `-edit` variant here; for an edit, do a full regeneration with the change described in the prompt. |
| `aspectRatio` | `"1:1"`, `"16:9"`, or `"9:16"` | Only these three. No 4:5 or 2:3; render 1:1 or 9:16 and crop downstream. |
| `referenceImages` | array, max 14 | Uploaded `filePath` values (not local paths, not asset ids). Name each reference's role in the prompt. |
| `nbGenerations` | 1-10 | Variants in one call. Default 1; cap 5 for ad batches. |
| `productId` | UUID | Optional; auto-selected when there is only one product. |

## Reference images (max 14)

Reference images are how brand identity stays faithful: pass the product hero, brand wordmark, character portrait, or style board, and name each one's role in the prompt ("the product in image 1", "the lighting mood from image 2"). Strongly recommended whenever the ad features a specific product.

**Upload flow.** The remote Arcads MCP server usually cannot read files on your machine, so passing a local path returns `File not found ... Use arcads_get_upload_url`. When that happens (or by default):

1. Call `arcads_get_upload_url(mimeType)` (for example `image/png`). It returns `{presignedUrl, filePath}`.
2. Send the file's raw bytes as an HTTP PUT to the `presignedUrl` with the `Content-Type` header set to the same mime type. Expect status 200. (The URL carries a checksum query parameter; a plain PUT still succeeds, no extra headers needed.)
3. Pass the returned `filePath` (for example `external-api-temp-uploads/<uuid>.png`) in `referenceImages`.

**Gotchas (confirmed):**
- Temp `filePath` values are **single-use**: consumed by the first tool call that references them. For N separate generation calls, upload a fresh copy before each call. `nbGenerations` inside one call counts as a single consumer, so one upload covers all variants of that call.
- `referenceImages` wants the uploaded `filePath`, **not** an `arcads_register_image` asset id (that returns `INVALID_REFERENCE_IMAGES`).

## Polling and fetching results

Poll each returned assetId with `arcads_watch_asset(assetId)`. It returns `status` (`pending` then `generated` or `failed`) and, once generated, the signed `downloadUrl`, in one call. While `pending` there is no `downloadUrl`: wait 15-20 seconds and call again. Nano Banana images usually finish in 30-60 seconds (allow up to 3 minutes).

Do not use `arcads_get_asset`: it intermittently drops off the server with `-32602 (tool not found)`. `arcads_watch_asset` already returns status, so never block on `arcads_get_asset`.

Download each finished image from its `downloadUrl` and save it into `outputs/nano-banana-image-ad/<slug>/` in the workspace.

## Workflow

### Phase 1: Gather inputs
Collect: the seed prompt or brief; aspect ratio (`1:1`, `16:9`, or `9:16`); reference images (up to 14; recommended); variant count N (default 1, cap 5); model (`nano-banana-2` unless the user asks otherwise). Read BRAND.md for brand details.

### Phase 2: Prompt rewrite
The shared template library (37 validated, parameterizable ad-format templates with per-model notes) **ships with the image-ad-clone skill**: if that skill is installed, read the image-ad-clone skill's `references/prompt-library.md`, wherever your skills are installed, and check whether the brief matches a template. If you cannot find the file, proceed without templates and say so. If a template matches, read its Model notes and proceed only if nano-banana is marked clean, strong, or preferred; if gpt-image-2 is preferred (dense typography, UI mimicry), suggest switching to chatgpt-image-ad. Fill the `{placeholders}` from BRAND.md and the brief.

If image-ad-clone is not installed, or nothing matches, compose a fresh prompt using this skill's `references/prompting-guide.md` (strengths to lean on, prompt anchors, named reference roles, lighting and material language).

Always append the three safety suffixes (no-chrome, edge-safe, glyph-safety; full text in the prompting guide) to the final prompt. Show the rewritten prompt to the user and ask: use it, edit it, or start over. Loop until approved.

### Phase 3: Credit estimate (MANDATORY, never skip)
Arcads exposes no billing or quote endpoint to you. Estimate the credit cost before generating:
1. Ask the user what their plan charges per Nano Banana image; if they know, use that number and save it to the log.
2. Otherwise, if the shared usage log (`outputs/arcads-usage-log.jsonl` at the workspace root, resolved from the setup-state file) has a recorded `creditsCharged` for a matching config, use the most recent one.
3. If neither exists: the first generation is an **unknown-cost calibration of 1**. The user states a maximum acceptable credit exposure for that single image in the approval; you generate one image, read back `creditsCharged`, append it to the usage log, then estimate the full batch from the observed number and confirm again before generating the rest.

Present `~credits x N variants` clearly labeled as an **estimate** with its basis, name any retry allowance (count and cost) or state that there is none, tell the user to confirm the exact cost in the Arcads platform, and **wait for explicit confirmation before generating**. Daily-limit plans report `creditsCharged: 0` with `usedDailyLimit: true`; that is a daily-limit use, not "free", so still show the estimate and still get confirmation. Never invent a number without a source.

### Phase 4: Upload references (if any)
Per Reference images above. Upload fresh immediately before the generation call; collect the `filePath` values.

### Phase 5: Generate
```
arcads_generate_image_nano_banana(
  prompt = "<rewritten prompt + safety suffixes>",
  model = "nano-banana-2",
  aspectRatio = "<1:1|16:9|9:16>",
  referenceImages = ["external-api-temp-uploads/<uuid>.png", ...],   # max 14; omit if none
  nbGenerations = <N>,
)
```
Record each call in `outputs/arcads-usage-log.jsonl` at the workspace root (tool, model, aspectRatio, resolution if any, ref count, count N, date, each assetId; later the final status, `creditsCharged` exactly as the MCP returned it, and the daily-limit indicator). Never log credentials or signed URLs, and never report performance or billing numbers the MCP did not return.

### Phase 6: Poll + visual QA (MANDATORY)
Poll every assetId with `arcads_watch_asset` until `generated`; download the files. Then **view each image** and inspect for: extra fingers or wrong limb count (the classic Gemini-family failure), garbled small text, wordmark drift, character identity drift across variants, melted or warped objects. If a variant is defective, a regeneration with a corrected prompt that names the fix explicitly (see Retry mode in the prompting guide) is a new credit-accounted operation: run it only inside the retry allowance the Phase 3 approval named (never more than 2 per variant), otherwise report the defect and ask first. Never resend the identical prompt. Report each regeneration's actual `creditsCharged`.

### Phase 7: Deliver + hand off
Show the user the saved file paths (send the images through the chat channel where possible), report actual `creditsCharged` per operation plus any daily-limit use, and ask: use all, use these, regenerate (a new gated batch), or cancel. For the selected files, offer the next steps:
- **human-ad-copy** to write the primary text, headlines, and hooks that pair with the creative.
- **meta-ad-launcher** to upload the images and build the campaign, ad set, and ads on Meta. Remind the user those are always created **PAUSED**, and that nothing gets activated and no budget gets changed without their explicit confirmation in that conversation.

## Error recovery

| Symptom | Fix |
|---|---|
| `File not found` on a reference | You passed a local path; run the upload flow first. |
| `REFERENCE_FILE_NOT_FOUND` on generate | The `filePath` was already consumed; re-upload fresh right before the call. |
| `INVALID_REFERENCE_IMAGES` | You passed a register-image asset id; pass the uploaded `filePath` instead. |
| `-32602` on any tool | Refresh the MCP tool list, re-discover the registered name, and re-issue the read call; poll only with `arcads_watch_asset`. A generate call is never re-issued without its allowance. |
| Extra fingers / melted object | Regenerate with explicit anatomy and material constraints (see prompting guide Retry mode), inside the retry allowance or after a fresh yes. |
| `422` validation or moderation | Check `aspectRatio` is in the allowed set; tighten or soften the prompt wording; the re-issue still needs its allowance. |
| `status: failed` | Do not resend the same prompt; strip or reword whatever likely got flagged. Credits may already have been charged; the retry is a new credit-accounted operation under the allowance or a fresh yes. |

## Out of scope

- **gpt-image-2 generation**: use chatgpt-image-ad.
- **Reverse-engineering an existing ad into a template**: use image-ad-clone.
- **Ad copy**: use human-ad-copy.
- **Meta upload, campaigns, activation**: use meta-ad-launcher (paused-only creation; activation requires explicit human confirmation).
- **Video, carousel, DCO**: image only.
