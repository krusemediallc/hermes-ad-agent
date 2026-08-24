---
name: clone-video-ad
description: Clone or adapt an existing video ad for the user's own brand and product using Seedance 2.0 through the Arcads MCP server. Analyzes the real source video with the MCP's media analysis tool, extracts its structure as a beat map (hook, show, demo, verdict, CTA), rewrites the dialogue and visuals for the user's product from BRAND.md, then generates, polls, and delivers the new ad, including multi-clip builds for sources longer than 15 seconds. Use when the user says things like "clone this ad", "remake this video for my brand", "adapt this competitor ad", "make me a version of this video ad", "copy this ad's format with my product", or shares a video ad and asks for their own version. Requires the Arcads MCP server; outputs video files only (Meta launch is a separate skill).
---

# Clone Video Ad (Arcads MCP, Seedance 2.0)

You are cloning an existing video ad onto the user's product: same structure, pacing, camera language, energy, and dialogue pattern, with the product, claims, and brand swapped for theirs. Everything runs through the Arcads MCP server. There is no key setup, no environment files, and no direct API calls in this skill; the MCP server handles auth, uploads, analysis, generation, and polling.

**Tool names note:** the tool names below match the Arcads MCP server as observed in mid 2026. Server versions differ. Before you start, list the tools actually available from the Arcads MCP server in this session and adapt names if they differ. If no Arcads tools are available at all, tell the user the Arcads MCP server is not connected and stop; do not fall back to any other transport.

## When to use

- The user hands you a video ad (file or link) and wants their own version of it.
- The user wants a competitor's winning format rebuilt around their product.

Not for: fresh UGC ads with no source video (use the `ugc-video-ad` skill), static image ads, or turning an ad into a reusable text template without generating video.

## Tools used

| Tool | Role |
|---|---|
| `arcads_analyze_media` | Watch and transcribe the source ad. Returns the blueprint text in `data.generatedText`. |
| `arcads_get_upload_url` | Presigned upload for local reference files when the server cannot read your filesystem. |
| `arcads_generate_video_seedance_20` | Generate the clone. |
| `arcads_watch_asset` | Poll status and fetch the signed download URL in one call. |
| `arcads_stitch_videos` | Join multi-clip builds (caps at 6 clips per call). |
| `arcads_list_products` | Resolve `productId` only if the account has several products; with one product the generate tools auto-select. |

Check each tool's live schema before calling; parameters shift between server versions.

## Prerequisites

1. **Arcads MCP connected** (see tool names note above).
2. **BRAND.md.** Read it before adapting anything: brand voice, product facts, approved and banned claims, compliance rules. If BRAND.md is missing, offer to run the `brand-setup` skill first; if declined, collect product name, one concrete benefit, audience, and claim restrictions in chat.

## Seedance 2.0 constraints (quick reference)

| Constraint | Impact |
|---|---|
| Aspect ratio | `9:16` or `16:9` only. No `1:1`. |
| Duration | 4 to 15 seconds per clip (integer). Longer sources become multi-clip builds. |
| Resolution | `480p`, `720p`, or `1080p`. Default `720p`; `480p` for cheap tests. |
| `referenceImages` (max 3) vs `referenceVideos` | Mutually exclusive in one call. Pick image-to-video or video-to-video, never both. |
| Video-to-video with human faces in the reference | Content checker may reject it and credits are still charged. Keep video-to-video for product-only or hands-only clips. |
| `referenceVideos` count | Only 1 is effective even where the schema allows more. |
| `audioEnabled` | `true` when the clone has speech; the model voices dialogue written in the prompt. |
| `nbGenerations` | 1 to 10 variations in a single call. |
| Prompt length | 100 to 260 words. |
| Forbidden prompt words | cinematic, professional, stunning, 8k, studio, perfect. |

## Workflow

### Phase 0: Gather inputs

| Input | Required | Notes |
|---|---|---|
| Source video ad | yes | A local file (mp4, mov, webm) or a link you can download it from. This is what gets cloned. |
| Product image | recommended | The user's product. Becomes `referenceImages` and `@(img1)`. Without it Seedance invents a product. |
| Product or offer description | if no image | Name, features, audience, key claims; used to rewrite the dialogue. |
| Brand voice | from BRAND.md | Ask only for what BRAND.md does not cover. |

If the user gives only a video and "clone this for my product", ask for a product image or a text description before continuing.

### Phase 1: Upload and analyze the source (one analysis call)

Get the source video to the server. Try passing the local path directly first; some deployments bridge files automatically (`arcads_analyze_media` often accepts local paths). If it fails with `File not found` or `REFERENCE_FILE_NOT_FOUND`:

1. `arcads_get_upload_url(mimeType)` (for example `video/mp4`) returns `{presignedUrl, filePath}`.
2. Upload the raw file bytes to `presignedUrl` with an HTTP PUT and a matching Content-Type header. Expect status 200.
3. Use the returned `filePath`.

Then call `arcads_analyze_media` with `referenceVideos: ["<filePath>"]` and this analysis prompt:

> "You are reverse-engineering a video ad so it can be recreated for a different product. Analyze this video and return: (1) total duration in seconds and aspect ratio (9:16 or 16:9); (2) a beat map: for each beat, the timestamp range, a label (HOOK / SHOW / DEMO / VERDICT / CTA etc.), what is on screen, camera framing and movement, and whether anyone speaks; (3) the FULL spoken transcript, verbatim, with per-beat line breaks (or SILENT if no speech); (4) speaker tone, energy arc, and relationship to the viewer; (5) lighting and capture style (phone or handheld, tripod, polished); (6) how the product is physically shown and which claims or features are called out; (7) the 2 or 3 defining traits that make this ad recognizable and MUST transfer to a clone. Be precise and concise."

Poll the returned assetId with `arcads_watch_asset` until `generated` (analysis takes about a minute), then read the blueprint from `data.generatedText`. Never write the clone from a thumbnail or the user's memory of the ad; always analyze the real video first. If the source is silent, note it; you will skip the dialogue gate.

Uploaded `filePath` values are single use: the analysis call consumes the one you just used. Any later call needs a fresh upload.

### Phase 2: Present the analysis and confirm

Show a tight summary and the swap plan, then wait:

```
Source ad analysis
Duration: 14s | Aspect: 9:16 | Beats: 4 | Dialogue: ~30 words | Style: handheld selfie review

Beat map:
  [00:00-00:03] HOOK    close-up to camera, excited: opening line
  [00:03-00:07] SHOW    tilts product to the lens: feature call-out
  [00:07-00:10] DEMO    (silent) uses the product, tight shot on the result
  [00:10-00:14] VERDICT back to camera: closing line and CTA

Defining traits: 1) ... 2) ... 3) ...

Transfers: structure, pacing, camera, edit style, tone, energy, dialogue pattern
Swaps:     product -> yours | claims -> your approved claims | brand -> yours

Proceed with the adaptation? (yes / adjust)
```

### Phase 3: Decide the generation mode

Walk this tree and tell the user which mode you picked and why:

- **Source 15s or shorter:** single clip. **Longer:** multi-clip, split at natural beat boundaries with each clip 15s or less (see Multi-clip builds).
- **Product image provided:** image-to-video with `referenceImages` and `@(img1)` in the prompt. **No image:** text-only (describe the product precisely in the prompt), or video-to-video only if the source is product-only or hands-only with no human faces.
- **Source has speech:** `audioEnabled: true` and the Phase 5 dialogue gate is required. **Silent:** `audioEnabled: false` (or ask if they want added voice) and skip the gate.

### Phase 4: Adapt for the user's brand

**Dialogue (if the source speaks):** keep the same conversational pattern, the same number of spoken lines, the same silent-beat placement, and the same energy arc. Swap product references for the user's product and match each line's word count within about 3 words to preserve pacing. Apply human ad-copy discipline (invoke the `human-ad-copy` skill for the rewrite if installed): plain spoken language, contractions, no AI-sounding phrasing, and no em-dashes in ad copy, ever.

**Claims gate (BRAND.md):** every claim carried over from the source must survive contact with BRAND.md. Anything banned there is rewritten around. Health, earnings, and before/after claims need an approved claim in BRAND.md or explicit user sign-off in this conversation. Claims the source made that the user's product cannot support get flagged in the Phase 5 block, never silently kept.

**Visuals:** keep camera work, framing per beat, edit style, setting, lighting, and technical-flaw cues from the blueprint. Swap only the product (appearance, colors, materials, label wording).

**Prompt composition (Seedance rules):**

- Order: Subject + Action + Camera + Style + Constraints.
- 100 to 260 words. One primary action per shot; use degree adverbs (slowly, casually).
- Timestamps `[00:00]`, `[00:04]` and so on for multi-beat pacing inside a clip.
- With a product image: include `@(img1)` and the line "the product from @(img1) must remain visually unchanged in every shot".
- At least one style anchor (documentary, photorealistic, handheld).
- No forbidden words (see constraints table).

### Phase 5: Dialogue confirmation gate (mandatory if speech)

Separate from the credit gate. Approval of the analysis or the plan never substitutes for dialogue approval.

```
Dialogue script (confirm before I generate)

  1. [HOOK]    "Okay, whoever designed this actually thought about people like me."
  2. [SHOW]    "It's the compact blender everyone's posting. Fits in one hand."
  3. [DEMO]    (silent beat, drops in fruit, presses the lid, it just runs)
  4. [VERDICT] "Smoothie in forty seconds. I'm done going back. Link below."

Spoken words: ~35 | Target: 15s | Fits at a natural pace: yes
Claim flags: none carried over from the source
Approve this dialogue? (yes / edit / rewrite)
```

Loop on edits until approved. Skip only if the clone is silent.

### Phase 6: Credit estimate gate (mandatory)

1. Ask how many variations they want (default 1); variations go through `nbGenerations` in one call.
2. Estimate credits. Arcads exposes no billing endpoint, so: read the shared usage log `outputs/arcads-usage-log.jsonl` at the workspace root (the repo clone directory recorded during setup) for a past Seedance run with a similar config and cite its `creditsCharged`; else use a credit rates note in BRAND.md; else ask the user. If the log is empty and the user does not know, run a **calibration batch of 1**: with the user's go-ahead, generate a single clip or variation first, observe the credits actually consumed (`creditsCharged` from the MCP, or have the user check the Arcads dashboard), append that to the usage log, then estimate the rest of the build from the observed number and confirm before generating it. One dated reference point you may cite as possibly stale: a 15s, 720p, image-referenced Seedance clip has cost about 0.9 credits. Multi-clip builds multiply per clip.
3. Present and wait:

```
Estimated credit cost:
  Seedance 2.0 (15s, 720p, image-to-video) x 1 variation = ~0.9 credits (from generation log)
  Estimate only. Confirm exact pricing in the Arcads platform.
  Proceed? (yes / no)
```

Never generate before the confirmation. QA-fix regenerations after it need no re-ask but their extra credits get reported. A later variant round always gets a fresh estimate and confirmation.

### Phase 7: Generate

**Single clip.** Upload the product image fresh right before this call (single-use rule), then:

```
arcads_generate_video_seedance_20(
  prompt          = "<adapted prompt>",
  aspectRatio     = "9:16",              # match the source
  duration        = 14,                  # from the beat map
  resolution      = "720p",
  audioEnabled    = true,                # from Phase 3 and 5
  referenceImages = ["<fresh filePath>"],  # image-to-video; omit for text-only or video-to-video
  nbGenerations   = <N>,
)
```

Right after the call succeeds, append a line to the shared usage log `outputs/arcads-usage-log.jsonl` at the workspace root (create it if missing) with model, duration, resolution, aspectRatio, audioEnabled, reference counts, prompt word count, and every returned assetId; update it later with final status and `creditsCharged`. Never log secrets.

**Multi-clip builds (source longer than 15s), pick by source type:**

**Pattern A, multi-scene explainer (default for most long ads).** The source is a sequence of distinct scenes with no visual continuity to carry between beats. Fire per-beat image-to-video generations in parallel:

1. Map each beat to one clip of 15s or less; embed that beat's approved line in its prompt.
2. Lock identity across beats by repeating an identical character description verbatim in every prompt (for example "a warm woman in her early forties with shoulder-length dark hair"), and repeat the style anchor verbatim too. For tighter control, generate one hero still first and pass it as `referenceImages` on each beat, with a fresh upload per beat.
3. Beats where the product appears get image-to-video with a fresh upload of the product image and `@(img1)`; lifestyle beats with no product on screen go text-only.
4. Fire all beats at once (they are independent), poll them all, and download each as `beat_N` in order.

**Pattern B, one continuous scene, chained.** Only when the whole ad is one person or setting and the hands, surface, and lighting must carry between beats:

1. Clip 1: image-to-video with the product image. Generate, poll, download.
2. Clip 2: video-to-video with clip 1's downloaded file as `referenceVideos` (upload it fresh first; no `referenceImages`, they are mutually exclusive).
3. Chain each next clip from the most recent one, sequentially. Only chain product-only or hands-only clips; faces in a reference video risk rejection with credits still charged.

**Stitching:** upload the clips (fresh `filePath` each) and join them with `arcads_stitch_videos`, which caps at 6 clips per call; for more, stitch in batches and then stitch the batch outputs. If a local ffmpeg happens to be installed in your environment, concatenating locally with a re-encode is a fine alternative for the final master, but the MCP stitch is the default path.

### Phase 8: Poll, deliver, QA

1. Poll every assetId with `arcads_watch_asset` until `generated` or `failed`. Video runs about 7 minutes, occasionally up to 15; use a relaxed cadence. No `downloadUrl` while `pending`. If `arcads_get_asset` exists in your tool list, do not rely on it; it drops off intermittently with `-32602 tool not found`. On any `-32602`, refresh the MCP tool list and retry once.
2. Download each finished clip from its signed `downloadUrl` into `outputs/clone-video-ad/<slug>/` (signed URLs expire, download promptly). Update the log with final status and `creditsCharged`.
3. Spot-check frames: melted or drifted product, wrong hands, label text that changed between shots, garbled speech. Clearly broken output gets one corrected-prompt regeneration (cap 2 retries per clip); note the extra credits.
4. Send the finished video to the user in the current chat if the channel supports media attachments; otherwise share the download URLs and saved file paths. For multi-clip builds present each clip plus the stitched master. Number multiple variations.
5. Report actual `creditsCharged` totals from the MCP. Never invent numbers.
6. Offer a variant round: a new hook beat on the same body, a different setting, or more `nbGenerations` of the winner. Changed dialogue re-runs the dialogue and claims gates; every round re-runs the credit gate.

## Error recovery

| Symptom | Fix |
|---|---|
| Analysis returns a thin or empty blueprint | Re-call with a shorter, sharper analysis prompt, or trim the source clip. Confirm the file actually uploaded. |
| `File not found` / `REFERENCE_FILE_NOT_FOUND` | Local path did not bridge, or a `filePath` was already consumed. Upload fresh immediately before the consuming call. |
| `INVALID_REFERENCE_IMAGES` | A registered asset id was passed. Reference fields want the uploaded `filePath`. |
| `-32602 tool not found` | Refresh the MCP tool list and retry once. Poll with `arcads_watch_asset` only. |
| `status: failed` (content) | Never resend the same prompt. Strip flagged and forbidden words, tighten the motion, regenerate. |
| Server error on audio plus image | Historically intermittent. Retry once; if it persists, drop audio, or generate silent image-to-video and add voice downstream. |
| Video-to-video face rejection | Switch to image-to-video with the product image. |
| Prompt over 260 words | Trim tone and setting detail; keep the beat structure and dialogue. |
| Product drifts between shots | Add "the product from @(img1) must remain visually unchanged in every shot" and lock label details in words. |
| 422 validation | Check enums: aspect ratio (no 1:1), duration 4 to 15, resolution. |

## Hard rules, never relax

1. Analyze the real source video before adapting. Never clone from a description or thumbnail.
2. Dialogue confirmation gate before generating any speaking clone. Separate from the credit gate.
3. Credit estimate presented and explicitly confirmed before any generation. Always labeled an estimate.
4. Claims audited against BRAND.md; unsupported claims from the source get flagged, never carried silently.
5. `referenceImages` and `referenceVideos` never in the same call. No 1:1 aspect. No forbidden words.
6. Log every generation; report only numbers the MCP returned.
7. This skill outputs video files only. Launching to Meta belongs to the Meta launch skill, and anything created there is always paused until a human explicitly activates it.
