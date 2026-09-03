---
name: image-ad-clone
description: Reverse-engineer an existing image ad into a reusable, parameterizable prompt template that works for any brand and any product, validated by generating it through the Arcads MCP server (gpt-image-2 or nano-banana-2) and saved to the prompt library this skill owns (references/prompt-library.md, 37 seeded templates). Use when the user says "clone this ad as a template", "reverse engineer this ad", "turn this ad into a prompt", "extract a template from this image", "make this ad reusable", "study this ad and make a template", or "add this to my prompt library". The input is an EXISTING ad image the user provides; for generating fresh ads use chatgpt-image-ad or nano-banana-image-ad instead, and this skill's template library is what those two generator skills read.
---

# image-ad-clone

You reverse-engineer an **existing image ad** the user provides into a **reusable, parameterizable template** (with `{placeholders}`), validate it by generating through the Arcads MCP server, then save it to the prompt library that ships in this skill's `references/` folder. This skill is the template-library owner: the chatgpt-image-ad and nano-banana-image-ad generator skills read `references/prompt-library.md` from here.

All generation goes through the Arcads MCP tools: no Arcads API keys, no HTTP scripts. The Arcads MCP server handles its own auth.

## Read order

1. This file: the workflow.
2. `references/prompting-guide.md`: the full teardown and generalization method (visual-analysis checklist, placeholder vocabulary, iteration rules).
3. `references/template-format.md`: the entry skeleton every new template must follow.
4. `references/prompt-library.md`: the destination; study neighboring entries for voice and Model-notes format, and to see which tags are taken.
5. `references/safety-suffixes.md`: the three guards baked into every template round-trip.

## Before you start

1. **Check your tool list.** Tool names below match the Arcads MCP server as documented, but server versions differ. Confirm each tool actually exists in your session before calling it; on `-32602 (tool not found)`, reload the MCP connection and re-check.
2. **BRAND.md**: read the user's BRAND.md if present. The test fill (Phase 4) can use the user's own brand from it, or a plausible fictional brand. If BRAND.md is missing and the user wants to test with their brand, offer to run brand-setup first.
3. If the Arcads MCP tools are not connected, tell the user to connect the Arcads MCP server in their Hermes MCP settings and stop.

## Tools used (Arcads MCP)

| Tool | Role |
|---|---|
| `arcads_analyze_media` | Optional Gemini teardown of the source ad: layout, verbatim text, hierarchy, palette, style. Result text arrives in `data.generatedText`. |
| `arcads_generate_image_gpt` | Validate the template on gpt-image-2 (typography / UI-mimicry ads). Max 5 `referenceImages`. |
| `arcads_generate_image_nano_banana` | Validate the template on nano-banana-2 (photoreal / lifestyle / multi-reference ads). Max 14 `referenceImages`. |
| `arcads_get_upload_url` | Presigned upload URL for the source ad (when analyzing via MCP) and any product reference. |
| `arcads_watch_asset` | Poll status AND fetch the signed `downloadUrl` in one call. The primary poll tool. |

## Hard rules, never relax

1. **Input is an existing ad image.** If the user wants a fresh ad, redirect to chatgpt-image-ad or nano-banana-image-ad.
2. **Parameterize, don't memorize.** The output template must use `{brand.name}`, `{ad.headline}`, `{brand.color_primary}` and friends, reusable across brands and products. Never hard-code the source brand.
3. **Validate before saving.** Always run at least one generation round-trip through the MCP and visually QA it against the source before adding the entry to the library.
4. **Pick the backend in Phase 1** from the ad's nature: typography / UI-mimicry goes to gpt-image-2; photoreal / lifestyle / multi-reference goes to nano-banana-2. Optionally cross-validate against the other backend in Phase 8.
5. **Aspect ratios on this backend are `1:1`, `16:9`, `9:16` only.** If the source is 4:5 or 2:3, validate at the nearest supported ratio and note the intended crop in the template.
6. **Credit cost is an estimate**: present it before each validation round and wait for explicit confirmation (Phase 5). Daily-limit plans show `creditsCharged: 0`; never report numbers the MCP did not return.
7. **Never silently overwrite a library entry.** Append; if a tag collides, ask first.

## Uploading reference files

Needed when (a) analyzing the source ad via `arcads_analyze_media`, or (b) the template uses a real product image as a reference during validation. The remote MCP server usually cannot read local files, so a local path returns `File not found ... Use arcads_get_upload_url`.

1. `arcads_get_upload_url(mimeType)` returns `{presignedUrl, filePath}`.
2. Send the file's raw bytes as an HTTP PUT to the `presignedUrl` with the `Content-Type` header set to the same mime type; expect status 200.
3. Use the returned `filePath` in `referenceImages` (generation) or the analyze call's reference field.

**Gotcha:** temp `filePath` values are single-use, consumed by the first tool call that references them. Upload a fresh copy before each consuming call (analyze once, then re-upload for the validation generate). `nbGenerations` within one call counts as a single consumer.

## Polling

Poll with `arcads_watch_asset(assetId)`: it returns `status` and, once `generated`, the signed `downloadUrl`. While `pending` there is no `downloadUrl`; wait 15-20 seconds and re-call (nano-banana about 30-60s, gpt-image-2 about 1-3 min, analyze about 1 min). For `arcads_analyze_media`, once generated read the text from `data.generatedText`. Never rely on `arcads_get_asset` (intermittent `-32602`). Download validation images to `outputs/image-ad-clone/<tag>/` in the workspace.

## Workflow

### Phase 1: Receive ad + pick backend
Take the source ad image. Classify it: typography / UI-mimicry / dense text validates on **gpt-image-2**; photoreal / lifestyle / multi-reference / product-in-scene validates on **nano-banana-2**. State your pick and why; ask whether the user wants the other backend cross-validated in Phase 8. Read `references/prompt-library.md` to see which template tags are taken (new entries continue after the seeded T1-T39, so the next is T40).

### Phase 2: Teardown
Describe the source precisely, using your own image vision (view the file) or, for a richer structured teardown, upload it and call `arcads_analyze_media` with a request like: "Describe this ad's layout, every text element verbatim, visual hierarchy, color palette with hex guesses, typography, photographic vs graphic style, and the 3 traits that make it recognizable." Capture: layout grid, each text block, hierarchy, palette, type treatment, imagery style, defining traits, and mark every element `[BRAND]` (becomes a variable) or `[STRUCTURE]` (stays literal). Mentally crop away any screenshot or platform chrome; the template must produce a standalone creative. Full checklist in `references/prompting-guide.md`.

### Phase 3: Parameterize
Convert the teardown into a template with `{placeholders}` for everything brand or product specific (brand name, product, headline, subhead, palette, imagery subject). Keep structural and compositional language literal. Use the standard placeholder vocabulary in `references/prompting-guide.md`. Append the three standard safety guards (`references/safety-suffixes.md`).

### Phase 4: Fill with a test brand
Pick a plausible **different** brand or product than the source's (the user's own brand from BRAND.md works well, or a fictional one) to prove reusability. Fill every placeholder.

### Phase 5: Credit estimate (MANDATORY, never skip)
Estimate `~credits x variants` for the validation round: use the shared usage log (`outputs/arcads-usage-log.jsonl` at the workspace root, the repo clone directory recorded during setup) if it has a matching config; otherwise ask the user their plan's rate. If the log is empty and the user does not know the rate, run a **calibration batch of 1**: with the user's go-ahead, generate a single validation image first, observe the credits actually consumed (`creditsCharged` from the MCP, or have the user check the Arcads dashboard), append that to the usage log, then estimate the remaining validation variants from the observed number. Present every figure as an estimate, point them to the Arcads platform for the exact cost, and **wait for explicit confirmation before generating**.

### Phase 6: Upload refs (if the template uses a product image)
Per Uploading reference files above; upload fresh.

### Phase 7: Validate (round-trip)
Generate with the Phase 1 backend:
```
# typography / UI ad:
arcads_generate_image_gpt(prompt="<filled template + suffixes>", model="gpt-image-2", aspectRatio="<r>", nbGenerations=2)
# photoreal / lifestyle ad:
arcads_generate_image_nano_banana(prompt="<filled template + suffixes>", model="nano-banana-2", aspectRatio="<r>", referenceImages=[...], nbGenerations=2)
```
2-3 variants in one call is enough to judge template stability. Poll with `arcads_watch_asset`, download, **view the outputs**, and compare to the source: does it reproduce the layout, hierarchy, and feel? Is the text legible (gpt-image-2)? Are hands and materials clean (nano-banana)? If it drifts, refine the template wording and re-validate; cap 2 refine loops. Log each call to `outputs/arcads-usage-log.jsonl` at the workspace root.

### Phase 8: Cross-validate (optional)
If requested, fire the same filled template through the other backend and record in the entry's Model notes which backend renders it best and any caveats. If you only validated one backend, say so explicitly in the Model notes ("untested, validate before using").

### Phase 9: Save to the library
Append the finished template to `references/prompt-library.md` using the skeleton in `references/template-format.md`: tag and title, when-to-use, aspect ratio (plus crop note if the native ratio is unsupported), reference-image guidance, variable schema, the parameterized template prompt, example fill, Model notes for both backends, and the validated-example path under `outputs/image-ad-clone/<tag>/`. Show the user the new entry and the validation image(s). The template is now available to chatgpt-image-ad and nano-banana-image-ad.

## Error recovery

| Symptom | Fix |
|---|---|
| Template renders inconsistently across `nbGenerations` | Tighten compositional language; add explicit placement and anchoring; pick the more stable backend. |
| `File not found` / `REFERENCE_FILE_NOT_FOUND` | Upload first / re-upload fresh before the call (single-use paths). |
| `-32602 arcads_get_asset not found` | Poll with `arcads_watch_asset`. |
| Text garbled on a typography template | Move it to gpt-image-2; enlarge the text; note "gpt-image-2 only" in Model notes. |
| `422` validation or moderation | Check the aspect ratio is in the allowed set; tighten or soften the wording; never resend a failed prompt unchanged. |

## Out of scope

- **Fresh ad generation**: chatgpt-image-ad / nano-banana-image-ad.
- **Video ad cloning**: image only.
- **Ad copy**: human-ad-copy.
- **Meta upload, campaigns, activation**: meta-ad-launcher (creates everything paused; activation needs explicit human confirmation).
- **Multi-template extraction in one run**: one reference produces one template per run; batch sequentially.
