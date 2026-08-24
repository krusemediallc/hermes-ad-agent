---
name: ugc-video-ad
description: Create UGC style talking-head video ads (a believable person speaking about the user's product to camera) through the Arcads MCP server, end to end. Lists real actor situations and voices via MCP and presents options, writes the spoken script with human ad-copy discipline, runs a mandatory dialogue and claims gate against BRAND.md, estimates credit cost and waits for confirmation, generates in batches, polls to completion, delivers the finished clips, and offers a variant round. Use when the user says things like "make a UGC ad", "talking head ad for my product", "actor video", "testimonial video ad", "creator style ad", "make someone talk about my product", "spokesperson video", or "selfie style review video". Requires the Arcads MCP server to be connected; outputs video files only (Meta launch is a separate skill).
---

# UGC Video Ad (Arcads MCP)

You are producing a UGC style video ad: a believable, casual person speaking about the user's product straight to camera, like a real creator filmed it on their phone. Everything runs through the Arcads MCP server. There is no key setup, no environment files, and no direct API calls in this skill; the MCP server handles auth, uploads, generation, and polling.

**Tool names note:** the tool names below match the Arcads MCP server as observed in mid 2026. Server versions differ. Before you start, list the tools actually available from the Arcads MCP server in this session and adapt names if they differ. If no Arcads tools are available at all, tell the user the Arcads MCP server is not connected and stop; do not fall back to any other transport.

## When to use

- The user wants a person on camera talking about their product (review, testimonial, unboxing, routine, first impression).
- The user wants "an actor" or "a creator" to read a script for their brand.

Not for: cloning a specific existing video ad (use the `clone-video-ad` skill), silent b-roll or product-only clips (generate directly with a video tool, no actor needed), or static image ads.

## Prerequisites

1. **Arcads MCP connected.** Confirm at least `arcads_watch_asset` and one `arcads_generate_*` tool appear in your available tool list.
2. **BRAND.md.** Read the user's BRAND.md before writing anything. It carries brand voice, audience, product facts, approved and banned claims, and compliance rules. If BRAND.md is missing, offer to run the `brand-setup` skill first; if the user declines, gather product name, one concrete benefit, audience, and any claim restrictions in chat before continuing.

## Two production routes

Pick one route per ad and tell the user which you chose and why.

**Route A: Arcads actor (default for talking-head).** Use `arcads_audio_driven`. It combines an actor source with a voice source:

| Actor source | Where it comes from |
|---|---|
| `situation` | Pick from the Arcads actor catalog via `arcads_list_situations` |
| `image` | A photo the user supplies (uploaded first, see Uploads) |
| `sourceVideo` | A video of a person the user supplies (uploaded first) |

| Voice source | Where it comes from |
|---|---|
| `script` | Text; the platform voices it (pick a voice via `arcads_list_voices`) |
| `audio` | An audio file: either `arcads_text_to_speech(script, voiceId)` output or an uploaded recording |

Route A gives you real, consistent actors and clean lip-sync. It is the best match when the user says "actor" or "spokesperson".

**Route B: Generated person (Seedance 2.0 speaking prompt).** Use `arcads_generate_video_seedance_20` with the dialogue embedded in the prompt and `audioEnabled: true`. Route B gives you full control of the scene (setting, camera, jump cuts, product in hand via a reference image) at the cost of a synthetic person. Best when the user wants a specific scene, a product physically shown, or a full jump-cut UGC edit. The prompt formula for Route B is at the bottom of this file.

## Video model choice (Route B and general video)

| Model | Tool | Aspect | Duration | Use it for |
|---|---|---|---|---|
| Seedance 2.0 | `arcads_generate_video_seedance_20` | 9:16 or 16:9, no 1:1 | 4 to 15s (integer) | Default UGC model. Speech from prompt with `audioEnabled: true`. `resolution` 480p, 720p, or 1080p. Up to 3 `referenceImages` (product in frame, `@(img1)` refers to the first). Forbidden words in prompts: cinematic, professional, stunning, 8k, studio, perfect. Prompt 100 to 260 words. |
| Sora 2 | `arcads_generate_video_sora2` | per tool schema | enum 4, 8, 12, 16, 20s | Longest single-clip dialogue. Speech generated from the prompt. |
| Veo 3.1 | `arcads_generate_video_veo31` | per tool schema | auto, about 8s | Animate a supplied person photo via `startFrame`. Warns or truncates if the script runs past roughly 20 words. |
| Kling 3.0 / 2.6 | `arcads_generate_video_kling_30_pro`, `_kling_26_pro`, `_kling_30_4k` | per tool schema | per tool schema | Silent b-roll and motion shots only. No speech. Redirect speaking requests to Seedance, Sora, or Veo. |

If the user does not name a model: Route A for pure talking-head, Seedance 2.0 for scene-driven UGC. Check each tool's live schema for exact parameters before calling.

## Workflow

### Step 1: Capture the brief

Ask for whatever BRAND.md does not already answer:

- Audience (one sentence) and the feeling or action the ad should drive.
- Product name plus one concrete benefit and any proof point.
- Hook idea for the first two seconds (pattern interrupt, curiosity, relatable moment).
- CTA wording.
- Aspect ratio (default 9:16) and target length.
- Anything banned: words, claims, competitor mentions.

### Step 2: Pick the actor and voice (Route A) or design the person (Route B)

**Route A:** call `arcads_list_situations` and present a short numbered list of 4 to 8 fitting actor situations (name or id plus a one-line description of who they are and the vibe). Ask the user to pick one, or to supply their own photo or video instead. If the script will be voiced from text, call `arcads_list_voices` and present 3 to 5 matching voices the same way. Wait for the pick.

**Route B:** describe the person in the prompt yourself using the formula at the bottom of this file (age range, casual hair, 2 or 3 skin reality cues, comfort clothing). Show the user your one-line person description before generating.

### Step 3: Write the script with human ad-copy discipline

If the `human-ad-copy` skill is installed, invoke it to draft or final-pass the script; it is the house standard for copy in Hermes Ad Agent. Whether or not it is installed, hold these rules:

- Write like a person talking, not a brand writing. Contractions, plain words, short lines.
- Filler is allowed and often good: "okay so", "honestly", "I'm not even kidding".
- No AI tells: no "game-changer", "elevate", "unleash", "seamless", no rule-of-three stacking, no tidy summary sign-off. End mid-thought or with a laugh, not a polished outro.
- No em-dashes in ad copy, ever. Use periods and commas.
- One idea per line. Hook first, proof in the middle, CTA last.
- Read every line out loud in your head at a relaxed pace with natural pauses. If it feels rushed for the target duration, cut words. Plan at least one silent beat (inspecting the product, sipping, reacting) in any clip over 8 seconds.

**Script length picks the duration** at roughly 2.5 spoken words per second, rounded up:

| Spoken words | Seedance 2.0 | Sora 2 |
|---|---|---|
| 1 to 8 | 4 to 5s | 4s |
| 9 to 15 | 6 to 8s | 8s |
| 16 to 25 | 9 to 12s | 12s |
| 26 to 35 | 13 to 15s | 16s |
| 36 to 48 | too long, split | 20s |
| 49+ | too long, split | too long, split |

If the script is too long for one clip, offer to trim it, split it into multiple clips, or switch models.

### Step 4: Claims and compliance gate (BRAND.md)

Before showing the script, audit every factual claim in it against BRAND.md:

- Anything in BRAND.md's banned claims, banned words, or compliance section is out. Rewrite around it.
- Health, medical, financial, earnings, weight, and before/after claims need an explicit approved claim in BRAND.md or explicit user sign-off in this conversation. Never soften this by burying the claim in filler.
- Claims you cannot trace to BRAND.md or the user get flagged, not silently included.

Carry any flags into the dialogue gate block so the user rules on them.

### Step 5: Dialogue confirmation gate (mandatory, separate from credits)

Every video where a person speaks gets this gate. Present the exact lines, timed, and wait for an explicit yes. Approval of tone, actor, or cost never substitutes for dialogue approval.

```
Dialogue script (confirm before I generate)

  1. [HOOK]    "Okay so this showed up today and I need to talk about it."
  2. [SHOW]    "It's the insulated bottle everyone kept recommending. The lid actually seals."
  3. [DEMO]    (silent beat, flips it upside down over the counter, nothing leaks)
  4. [VERDICT] "That's it. That's the review. Link's below if you want one."

Spoken words: ~34 | Target duration: 15s | Fits at a natural pace: yes
Claim flags: none
Approve this dialogue? (yes / edit / rewrite)
```

Loop on edits until approved. Skip this gate only for fully silent clips.

### Step 6: Variation count and credit estimate gate (mandatory)

1. Ask how many variations the user wants (default 1, sensible cap 5). Variations go into a single generate call via `nbGenerations` (1 to 10), not repeated calls.
2. Estimate credits. Arcads exposes no billing endpoint, so: read the shared usage log `outputs/arcads-usage-log.jsonl` at the workspace root (the repo clone directory recorded during setup) for a past run with a matching model and config and use its recorded `creditsCharged`; else use a credit rates note in BRAND.md if one exists; else ask the user what a comparable generation costs them. If the log is empty and the user does not know, run a **calibration batch of 1**: with the user's go-ahead, generate a single variation first, observe the credits actually consumed (`creditsCharged` from the MCP, or have the user check the Arcads dashboard), append that to the usage log, then estimate the remaining variations from the observed number and confirm before generating them. One dated reference point you may cite as possibly stale: a 15s, 720p, image-referenced Seedance 2.0 clip has cost about 0.9 credits.
3. Present it as an estimate, cite the source, and wait:

```
Estimated credit cost:
  Seedance 2.0 (15s, 720p, 1 reference image) x 2 variations = ~1.8 credits (from generation log)
  Estimate only. Confirm exact pricing in the Arcads platform.
  Proceed? (yes / no)
```

Do not generate until the user confirms. QA-fix regenerations after this confirmation do not need a new confirmation, but report their extra credits at the end. A fresh variant round later always gets a fresh estimate and confirmation.

### Step 7: Upload reference files (only if the user supplied media)

A user-supplied actor photo, source video, or voice recording must reach the Arcads server. Try passing the local file path directly first; some deployments bridge files automatically. If the tool returns `File not found` or `REFERENCE_FILE_NOT_FOUND`:

1. Call `arcads_get_upload_url(mimeType)` (for example `image/jpeg`, `video/mp4`, `audio/mpeg`). It returns `{presignedUrl, filePath}`.
2. Upload the raw file bytes to `presignedUrl` with an HTTP PUT and a Content-Type header matching the mimeType. Expect status 200.
3. Pass the returned `filePath` (not the local path, not a registered asset id) in the tool's reference field.

Uploaded `filePath` values are single use: the first tool call that references one consumes it. Upload fresh immediately before the consuming call. A single call with `nbGenerations` greater than 1 counts as one consumer, so one upload covers the whole batch.

### Step 8: Generate

**Route A:**

```
arcads_audio_driven(
  situation = "<picked situation id>",   # or image / sourceVideo filePath
  script    = "<approved dialogue>",     # or audio = <TTS or uploaded filePath>
  ...                                    # remaining params per the live tool schema
)
```

If voicing from text with a specific voice, either pass the script with the chosen `voiceId` (if the schema supports it) or run `arcads_text_to_speech(script, voiceId)` first, poll it (TTS finishes in about 5 to 10 seconds), and feed the audio in.

**Route B:**

```
arcads_generate_video_seedance_20(
  prompt          = "<UGC prompt with approved dialogue embedded>",
  aspectRatio     = "9:16",
  duration        = <from Step 3>,
  resolution      = "720p",              # 480p for cheap tests, 1080p for finals
  audioEnabled    = true,
  referenceImages = ["<fresh filePath>"],  # only if a product image is in frame
  nbGenerations   = <N>,
)
```

Immediately after each generate call succeeds, append one line to the shared usage log `outputs/arcads-usage-log.jsonl` at the workspace root (create the folder and file if missing) with model, duration, resolution, aspectRatio, audioEnabled, reference counts, prompt word count, and every returned assetId. Update the entry later with final status and `creditsCharged`. Never log secrets.

### Step 9: Poll

Poll each assetId with `arcads_watch_asset(assetId)` until `status` is `generated` or `failed`. It returns the signed `downloadUrl` in the same call once done. While `pending` there is no URL; wait and re-call on a relaxed cadence (video runs about 7 minutes, occasionally up to 15; TTS about 5 to 10 seconds). If `arcads_get_asset` exists in your tool list, do not rely on it; it is known to drop off intermittently with a `-32602 tool not found` error. On any `-32602`, refresh your MCP tool list and retry once.

### Step 10: Deliver and QA

1. Download each finished video from its signed `downloadUrl` into `outputs/ugc-video-ad/<slug>/` (signed URLs expire, so download promptly).
2. Watch or spot-check each clip: garbled speech, lip-sync drift, warped hands, a product label that changed between shots. If a clip is clearly broken, regenerate once with a corrected prompt (cap 2 retries per clip) and note the extra credits.
3. Send the finished files to the user in the current chat if the channel supports media attachments; otherwise share the download URLs and the saved file paths. Number the variations so the user can pick favorites.
4. Report actual `creditsCharged` totals from the log. Never state numbers the MCP did not return.

### Step 11: Variant loop

Offer one concrete next round, for example: 3 new hooks on the winning body (change only the first line), the same script on a different actor or voice, or a different setting. Each round with changed dialogue re-runs the dialogue and claims gates, and every round re-runs the credit gate. Batch each round with `nbGenerations`.

## Route B prompt formula (Seedance 2.0 UGC, condensed)

Stack these 9 layers into one 100-to-260-word prompt, in order. Skipping layers is what makes AI video look fake.

1. **Format header:** duration, "UGC style <content type> video, filmed on smartphone", a specific lighting source (natural bedroom window light, bathroom vanity light), a filming posture (casual handheld selfie angle, phone propped on counter).
2. **Person:** natural age range, casual hair, 2 or 3 skin reality cues (visible texture, slight undereye shadows, a hint of forehead shine), comfort clothing. Never dermatological terms.
3. **Setting:** a lived-in space with 3 specific clutter details (mug on the counter, clothes on a chair, plants on the windowsill).
4. **Product intro:** how the product physically enters frame ("holds the @(img1) up to the camera"). With a reference image, add "the product from @(img1) must remain visually unchanged in every shot".
5. **Script beats:** one jump cut per beat, framing change plus action, dialogue in quotes, silent beats written as actions with no quotes.
6. **Tone direction:** 2 or 3 emotion words plus behavior, and always an explicit pacing cue ("speaks at a relaxed, unhurried pace, leaves a beat of silence after each sentence"). Models default to rushed speech; this line counters it.
7. **Edit style:** "each jump cut is slightly closer or at a different angle, as if she filmed multiple takes and edited the best bits together."
8. **Technical flaws:** natural phone quality, not color graded, slight motion blur, soft focus, sound direct from the phone mic with room ambience.
9. **Vibe statement:** one anchor sentence ("trustworthy and real, a friend telling you about something she genuinely likes").

Remember the forbidden words for Seedance prompts: cinematic, professional, stunning, 8k, studio, perfect.

## Error recovery

| Symptom | Fix |
|---|---|
| `File not found` / `REFERENCE_FILE_NOT_FOUND` | Local path did not bridge. Upload via `arcads_get_upload_url` and pass the fresh `filePath` (Step 7). |
| `INVALID_REFERENCE_IMAGES` | A registered asset id was passed. Reference fields want the uploaded `filePath`. |
| `-32602 tool not found` | Refresh the MCP tool list and retry once. Poll with `arcads_watch_asset` only. |
| `status: failed` (content) | Never resend the same prompt. Remove flagged or forbidden words, tighten the action, regenerate. |
| 422 validation | Check enums: aspect ratio, duration, resolution. Seedance takes no 1:1. |
| Server error on audio plus image (Seedance) | Historically intermittent. Retry once; if it persists, generate silent image-to-video and add voice via `arcads_audio_driven` or TTS downstream. |
| Speech sounds rushed | Add or strengthen the pacing cue in the tone layer and add a silent beat; or extend the duration. |

## Hard rules, never relax

1. Dialogue confirmation gate before generating any speaking video. Separate from the credit gate.
2. Credit estimate presented and explicitly confirmed before any generation. Always labeled an estimate.
3. Claims audited against BRAND.md; unsupported claims flagged, never slipped in.
4. No em-dashes in ad copy.
5. Log every generation; report only real numbers the MCP returned.
6. This skill outputs video files only. Launching to Meta belongs to the Meta launch skill, and anything created there is always paused until a human explicitly activates it.
