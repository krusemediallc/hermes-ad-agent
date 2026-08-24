---
name: chatgpt-image-ad
description: Generate standalone Meta image-ad creatives with ChatGPT Image 2 (gpt-image-2) through the Arcads MCP server. Best for typography-heavy and UI-mimicry ads such as fake iMessage or Slack threads, ChatGPT-style conversations, iOS dialogs, comparison tables, Apple Notes lists, fake search results, calendar and weather UI, magazine mastheads, and big-type hero statements, with dense text rendered legibly. Use when the user says "gpt image ad", "ChatGPT image ad", "typography ad", "comparison table ad", "fake iMessage ad", "UI-style ad", or wants any fresh Meta image creative whose success depends on readable text or faithful app UI. This skill produces image files only; copy and Meta upload hand off to the human-ad-copy and meta-ad-launcher skills. For photoreal, lifestyle, or multi-reference ads use nano-banana-image-ad instead. To reverse-engineer an existing ad into a reusable template use image-ad-clone.
---

# chatgpt-image-ad

You generate standalone Meta image-ad creatives with **gpt-image-2** through the Arcads MCP server. Everything goes through MCP tools: no API keys, no environment files, no HTTP scripts. The MCP server handles auth. Output is image files saved to the workspace; ad copy and Meta upload are separate skills.

## Before you start

1. **Check your tool list.** The tool names below match the Arcads MCP server as documented, but server versions differ. Confirm each tool actually exists in your current session's tool list before calling it. If a tool is missing or a call returns `-32602 (tool not found)`, reload the MCP connection and check again.
2. **Read the user's BRAND.md** (created by the brand-setup skill during install) for brand name, colors, product description, and tagline. You will need these to fill prompt placeholders. If BRAND.md is missing, offer to run brand-setup first; the user can also decline and give you brand details inline.
3. **Arcads account required.** If the Arcads MCP tools are not connected at all, tell the user to connect the Arcads MCP server in their Hermes MCP settings and stop.

## Model choice: is this the right skill?

| The user wants... | Skill |
|---|---|
| Apple Notes lists, fake search results, chat threads, ChatGPT-style conversations, iOS dialogs, Slack snapshots, comparison tables, dating-app cards, iMessage, calendar UI, weather UI, magazine covers, anything typography-heavy or UI-mimicry | **this skill** (gpt-image-2) |
| Handheld whiteboard signs, napkin handwritten testimonials, sticky-note + product flatlays, letter-board signs, lifestyle scenes, OOH/transit photography, scratch-off tickets, anything photoreal / material-rich / multi-reference | **nano-banana-image-ad** (nano-banana-2) |
| Turn an existing ad image into a reusable template | **image-ad-clone** |

If the brief is ambiguous, check the matching template's Model notes in the shared prompt library (see Phase 2); every entry recommends a backend.

## Tools used (Arcads MCP)

| Tool | Role |
|---|---|
| `arcads_generate_image_gpt` | Generate the ad. Params: `prompt`, `model: "gpt-image-2"`, `aspectRatio`, `referenceImages` (max 5), `nbGenerations` (1-10), optional `productId`. |
| `arcads_get_upload_url` | Presigned upload URL for each local reference image (see Reference images below). |
| `arcads_watch_asset` | Poll status AND fetch the signed `downloadUrl` in one call. The primary poll tool. |
| `arcads_list_products` | Resolve `productId` (optional; auto-selects when the account has one product). |

### `arcads_generate_image_gpt` parameters

| Param | Value | Notes |
|---|---|---|
| `prompt` | string (required) | The rewritten ad prompt from Phase 2, with the three safety suffixes appended. |
| `model` | `"gpt-image-2"` | Locked. `gpt-image-2` beats `gpt-image` for text fidelity. |
| `aspectRatio` | `"1:1"`, `"16:9"`, or `"9:16"` | Only these three. No 4:5 or 2:3 on this backend; render 1:1 and crop downstream. |
| `referenceImages` | array, max 5 | Uploaded `filePath` values (not local paths, not asset ids). More than 5 returns `400 Max 5 reference image(s) allowed`. |
| `nbGenerations` | 1-10 | Variants in one call. Default 1; cap 5 for ad batches. |
| `productId` | UUID | Optional; auto-selected when there is only one product. |

## Hard rules, never relax

1. **Model is `gpt-image-2`.** If the user wants Nano Banana, switch to nano-banana-image-ad.
2. **No platform or screenshot chrome** in the output unless the concept requires it (rare, needs user agreement). Append the no-chrome guard to every prompt.
3. **Edge-safe + glyph-safety guards always on.** Keep all text inside the safe central margin.
4. **Max 5 reference images.**
5. **Comparison-table and two-column prompts must specify BOTH columns' values.** If you only give one set, gpt-image-2 duplicates it into both columns (confirmed failure). State the competitor values AND the brand values explicitly.
6. **Credit estimate + confirmation before every generation** (Phase 3). Never report numbers the MCP did not return.
7. **No Meta upload here.** Hand off to meta-ad-launcher.

## Reference images (max 5)

Optional but strongly recommended when the ad features a specific product or an exact brand wordmark (wordmark drift is a known failure; passing the wordmark as a reference fixes it). Name each reference's role in the prompt.

**Upload flow.** The remote Arcads MCP server usually cannot read files on your machine, so passing a local path returns `File not found ... Use arcads_get_upload_url`. When that happens (or by default):

1. Call `arcads_get_upload_url(mimeType)` (for example `image/png`). It returns `{presignedUrl, filePath}`.
2. Send the file's raw bytes as an HTTP PUT to the `presignedUrl` with the `Content-Type` header set to the same mime type. Expect status 200. (The URL carries a checksum query parameter; a plain PUT still succeeds, no extra headers needed.)
3. Pass the returned `filePath` (for example `external-api-temp-uploads/<uuid>.png`) in `referenceImages`.

**Gotchas (confirmed):**
- Temp `filePath` values are **single-use**: consumed by the first tool call that references them. For N separate generation calls, upload a fresh copy before each call. `nbGenerations` inside one call counts as a single consumer, so one upload covers all variants of that call.
- `referenceImages` wants the uploaded `filePath`, **not** an `arcads_register_image` asset id.

## Polling and fetching results

Poll each returned assetId with `arcads_watch_asset(assetId)`. It returns `status` (`pending` then `generated` or `failed`) and, once generated, the signed `downloadUrl`, in one call. While `pending` there is no `downloadUrl`: wait 15-20 seconds and call again. gpt-image-2 usually takes 1-3 minutes.

Do not use `arcads_get_asset`: it intermittently drops off the server with `-32602 (tool not found)`. `arcads_watch_asset` already returns status, so never block on `arcads_get_asset`.

Download each finished image from its `downloadUrl` and save it into `outputs/chatgpt-image-ad/<slug>/` in the workspace.

## Workflow

### Phase 1: Gather inputs
Collect: the seed prompt or brief; aspect ratio (`1:1`, `16:9`, or `9:16`); reference images (up to 5, optional); variant count N (default 1, cap 5). Read BRAND.md for brand details.

### Phase 2: Prompt rewrite
The shared template library (37 validated, parameterizable ad-format templates with per-model notes) **ships with the image-ad-clone skill**: if that skill is installed, read the image-ad-clone skill's `references/prompt-library.md`, wherever your skills are installed, and check whether the brief matches a template. If you cannot find the file, proceed without templates and say so. If a template matches, read its Model notes and proceed only if gpt-image-2 is marked clean or preferred; if nano-banana is preferred (photoreal, handheld, lifestyle), suggest switching to nano-banana-image-ad. Fill the `{placeholders}` from BRAND.md and the brief.

If image-ad-clone is not installed, or nothing matches, compose a fresh prompt using this skill's `references/prompting-guide.md` (strengths to lean on, prompt anchors, typography and UI-proportion language).

Always append the three safety suffixes (no-chrome, edge-safe, glyph-safety; full text in the prompting guide) to the final prompt. Show the rewritten prompt to the user and ask: use it, edit it, or start over. Loop until approved.

### Phase 3: Credit estimate (MANDATORY, never skip)
Arcads exposes no billing endpoint to you. Estimate the credit cost before generating:
1. If the shared usage log (`outputs/arcads-usage-log.jsonl` at the workspace root, the repo clone directory recorded during setup) has a charge for a matching config, use the most recent one.
2. Otherwise ask the user what their plan charges per gpt-image-2 image; if they know, use that number and save it to the log.
3. If the log is empty and the user does not know: run a **calibration batch of 1**. With the user's go-ahead, generate a single image first, observe the credits actually consumed (`creditsCharged` from the MCP, or have the user check the Arcads dashboard), append that to the usage log, then estimate the full batch from the observed number and confirm before generating the rest.

Present `~credits x N variants` clearly labeled as an **estimate**, tell the user to confirm the exact cost in the Arcads platform, and **wait for explicit confirmation before generating**. Daily-limit plans report `creditsCharged: 0` with `usedDailyLimit: true`; still show the estimate and still get confirmation. Never invent a number without a source.

### Phase 4: Upload references (if any)
Per Reference images above. Upload fresh immediately before the generation call; collect the `filePath` values.

### Phase 5: Generate
```
arcads_generate_image_gpt(
  prompt = "<rewritten prompt + safety suffixes>",
  model = "gpt-image-2",
  aspectRatio = "<1:1|16:9|9:16>",
  referenceImages = ["external-api-temp-uploads/<uuid>.png"],   # max 5; omit if none
  nbGenerations = <N>,
)
```
Record each call in `outputs/arcads-usage-log.jsonl` at the workspace root (model, aspectRatio, ref count, N, each assetId; later the final status and `creditsCharged` exactly as the MCP returned it). Never log credentials, and never report performance or billing numbers the MCP did not return.

### Phase 6: Poll + visual QA (MANDATORY)
Poll every assetId with `arcads_watch_asset` until `generated`; download the files. Then **view each image** and inspect for: garbled small text (the main gpt-image-2 failure on dense body text); wordmark drift; wrong element count (4 chat bubbles instead of 3); UI proportion drift (an iOS dialog too small or misshapen); duplicated column values in comparison tables. If a variant is defective, regenerate with a corrected prompt that names the fix explicitly (see Retry mode in the prompting guide); never resend the identical prompt. Cap 2 retries per variant. QA-fix regenerations after the Phase 3 confirmation do not need a fresh credit confirmation, but tell the user they happened.

### Phase 7: Deliver + hand off
Show the user the saved file paths (send the images through the chat channel where possible) and ask: use all, use these, regenerate, or cancel. For the selected files, offer the next steps:
- **human-ad-copy** to write the primary text, headlines, and hooks that pair with the creative.
- **meta-ad-launcher** to upload the images and build the campaign, ad set, and ads on Meta. Remind the user those are always created **PAUSED**, and that nothing gets activated and no budget gets changed without their explicit confirmation in that conversation.

## Error recovery

| Symptom | Fix |
|---|---|
| `400 Max 5 reference image(s)` | Reduce to 5 or fewer; if the concept needs more refs, switch to nano-banana-image-ad. |
| `File not found` on a reference | You passed a local path; run the upload flow first. |
| `REFERENCE_FILE_NOT_FOUND` on generate | The `filePath` was already consumed; re-upload fresh right before the call. |
| `-32602` on any tool | Refresh the MCP tool list and retry once; poll only with `arcads_watch_asset`. |
| Garbled small text | Regenerate: enlarge the text, use fewer words, add "all text large and legible", keep it inside the safe margin. |
| Both comparison columns identical | Restate BOTH columns' values explicitly in the prompt and regenerate. |
| `422` validation or moderation | Check `aspectRatio` is in the allowed set; tighten or soften the prompt wording. |
| `status: failed` | Do not resend the same prompt; strip or reword whatever likely got flagged, then retry once. |

## Out of scope

- **Nano Banana / Gemini generation**: use nano-banana-image-ad.
- **Reverse-engineering an existing ad into a template**: use image-ad-clone.
- **Ad copy**: use human-ad-copy.
- **Meta upload, campaigns, activation**: use meta-ad-launcher (paused-only creation; activation requires explicit human confirmation).
- **Video, carousel, DCO**: image only.
