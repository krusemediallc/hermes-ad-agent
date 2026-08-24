---
name: claymation-ad
description: Produce a stop-motion claymation story ad in the Aardman and Laika handcrafted look, end to end through the Arcads MCP server. You plan a narrated hook / problem / product / payoff / CTA story across up to 8 beats, lock a consistent clay cast, generate storyboard stills with gpt-image-2 (with a nano-banana fallback for clay texture), animate each beat with Seedance 2.0 image-to-video, voice the narrator with Arcads text-to-speech, then assemble, caption, and deliver. Use this skill when the user asks for a "claymation ad", "clay ad", "stop-motion ad", "Aardman-style ad", "Wallace and Gromit style ad", "animated story ad with clay characters", or shares a reference video with the hand-sculpted plasticine look. Requires the Arcads MCP server to be connected; every generation batch gets a credit-cost estimate and explicit user confirmation before it fires. For the smooth 3D family-movie look use the pixar-style-ad skill instead.
---

# Claymation Ad

You are building a narrative vertical video ad (9:16, roughly 35 to 115 seconds) in the Aardman and Laika stop-motion claymation aesthetic: hand-sculpted plasticine characters, miniature physical sets, a warm third-person narrator telling a small story about a character. The pipeline is: story beats, cast sheet, storyboard stills (gpt-image-2, nano-banana fallback for texture), per-beat animation (Seedance 2.0 image-to-video), narrator voiceover (Arcads TTS), assembly, captions, delivery.

This is the longest and most expensive creative pipeline in this skill pack (a full 8-beat ad means 8 video generations, and video dominates the cost). You must estimate credits and get an explicit "yes" from the user before EVERY generation batch, not just once at the start.

## Before you start

1. **Verify the Arcads MCP server is connected.** List your actually-available tools and confirm you can see the `arcads_*` tools named below. Tool names and parameters can differ between server versions, so always trust your live tool list over the names written here. If no Arcads tools are available, stop and help the user connect the Arcads MCP server first (see the repo's SETUP.md).
2. **Read the user's BRAND.md.** Product, audience, tone, and permissible claims all come from it. If BRAND.md does not exist, offer to run the `brand-setup` skill before continuing.
3. **Read the reference files in this folder, in order.** They are the creative source of truth:
   - `references/style-guide.md` (the aesthetic, the 8-beat arc, the cast sheet template, narration rules, the negative block)
   - `references/storyboard-prompts.md` (per-beat gpt-image-2 prompt formulas with worked examples)
   - `references/animation-prompts.md` (per-beat Seedance 2.0 prompt formulas plus Seedance platform rules)

## Tools used (Arcads MCP)

| Tool | Role |
|---|---|
| `arcads_list_products` | Resolve the `productId` if the account has products configured (auto-selects when there is only one). |
| `arcads_generate_image_gpt` | Storyboard stills. `model: "gpt-image-2"`, `aspectRatio: "9:16"`, up to 5 `referenceImages`, `nbGenerations` 1 to 10. |
| `arcads_generate_image_nano_banana` | Clay-texture fallback for close-ups and the infographic beat when gpt-image-2 smooths the clay (up to 14 `referenceImages`). |
| `arcads_generate_video_seedance_20` | Animate each approved still (image-to-video). `referenceImages: [still]`, `aspectRatio: "9:16"`, `duration` 4 to 15, `resolution: "720p"`, `audioEnabled: false`. |
| `arcads_list_voices` | Pick the narrator voice once. |
| `arcads_text_to_speech` | Narrator (and sparse character) lines per beat, same narrator `voiceId` throughout. |
| `arcads_get_upload_url` | Presigned upload for any local file the generation tools need as a reference. |
| `arcads_stitch_videos` | Concatenate clips, 2 to 6 per call. |
| `arcads_add_subtitles` | Burn captions onto the voiced master (auto-transcribes from the baked-in audio). |
| `arcads_watch_asset` | Poll every asset id until `generated` or `failed`; on success it also returns the download URL. |

Check your live tool list before relying on any of these. Do not build the flow around `arcads_get_asset`; it intermittently disappears from the server with a "-32602 tool not found" error. `arcads_watch_asset` is the reliable poller. On any -32602, refresh your tool catalog and retry once.

## Hard rules (never relax these)

1. **Credit gate before EACH generation batch.** Before the storyboard batch, before the animation batch, before the TTS batch, and before a paid captions pass: present an itemized credit estimate, label it an estimate (Arcads exposes no billing endpoint), tell the user to confirm exact pricing in the Arcads platform, and wait for an explicit yes. QA-fix regenerations inside an approved batch (max 2 retries per beat) do not need a fresh confirmation, but note them when reporting totals.
2. **Script approval gate before any generation.** Present the numbered beat script with every narrator line and every character line, and get an explicit yes. This gate is separate from the credit gate; never treat one approval as covering both.
3. **Aesthetic lock.** Aardman and Laika claymation, not Pixar, not CGI, not 2D. Paste the STYLE LOCK from `references/style-guide.md` verbatim into every still prompt. Honor both banned-word lists: the style guide's (`Pixar`, `3D rendered`, `CGI`, `photorealistic`, `subsurface scattering`, and friends) and Seedance's (`cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect`).
4. **Storyboard first, then animate.** Never one-shot text-to-video the whole ad. Identity drifts across 8 beats, and Seedance's 15 second per-clip ceiling caps a single clip far below ad length anyway. Lock each still with user approval before animating it.
5. **One narrator voice across all beats.** Pick one `voiceId` and reuse it. A second `voiceId` is allowed for a supporting character's single spoken line. Never use an in-prompt narrator line in Seedance; set `audioEnabled: false` and overlay the VO in post.
6. **No dead space.** The voiceover drives clip duration. Each assembled beat should run about `vo_duration + 0.5s`. Never speed up the VO to fit; split the line or regenerate the clip longer instead.
7. **9:16 vertical.** Seedance has no 1:1.
8. **Never fabricate numbers.** Credits, durations, statuses: report only what the MCP actually returned. Log every generation (tool, model, beat, duration, resolution, asset id, and `creditsCharged` once known) to the shared usage log `outputs/arcads-usage-log.jsonl` at the workspace root (the repo clone directory recorded during setup) so future estimates get better.
9. **Meta launch is out of scope here.** When the user wants the finished ad on Meta, hand off to the `meta-ad-launcher` skill, which always creates everything PAUSED.

## Reference file uploads (read this before Phase 2)

The Arcads MCP server is remote. Depending on how your client bridges files, it may not be able to read the local disk. Every reference image or video a generation tool consumes may therefore need to be an Arcads S3 `filePath` rather than a local path. That applies to a user-supplied product photo AND to each generated still you chain forward (the protagonist anchor still reused across Beats 2, 3, 4, 6, 7, 8, plus each approved still into its Seedance call, plus clips into stitch).

Procedure:

1. Try passing the local file path first. Some MCP clients bridge local files automatically, and some editing tools (`arcads_stitch_videos`, `arcads_add_subtitles`, `arcads_trim_video`, `arcads_analyze_media`) upload local paths themselves.
2. If the tool errors with "File not found" or `REFERENCE_FILE_NOT_FOUND`, use the upload flow: call `arcads_get_upload_url(mimeType)` to get `{presignedUrl, filePath}`, then send the file bytes to the `presignedUrl` with a plain HTTP PUT from the terminal (no auth header; set the Content-Type header to the same mimeType; the raw file bytes are the body; a 200 response means it worked). Pass the returned `filePath` in `referenceImages`.
3. **Temp `filePath`s are single-use.** The first tool call that references one consumes it. This skill chains the protagonist anchor into six or more downstream calls, so that means six or more separate uploads of the same PNG. Upload a fresh copy immediately before each consuming call; do not try to cache a `filePath` across calls (it silently works for the first and errors for the rest). A single call with `nbGenerations` greater than 1 counts as one consumer.
4. Never pass an `arcads_register_image` asset id in `referenceImages`; that returns `INVALID_REFERENCE_IMAGES`.

To chain a generated still: after it reaches `generated`, download it from the `arcads_watch_asset` download URL to `outputs/claymation-ad/<slug>/stills/beatN.png`, then upload a fresh temp copy right before each call that uses it.

## Workflow

### Phase 0: Brand, product, cast

1. Read BRAND.md. Ask which product this ad is for; call `arcads_list_products` if the account has products configured.
2. Build the cast and continuity sheet from `references/style-guide.md`: named protagonist, supporting character, narrator persona, primary and secondary miniature settings, the product as a clay prop, and the verbatim STYLE LOCK. Save it to `outputs/claymation-ad/<slug>/cast-sheet.md` and confirm it with the user.

### Phase 1: Story beats and script (approval gate)

Plan the ad around five story jobs mapped onto the 8-beat claymation arc (or the 5-beat short, which drops beats 3, 4, and 5):

| Story job | Claymation beats |
|---|---|
| HOOK | 1 Setup, 2 Inciting moment |
| PROBLEM | 3 Social validation, 4 Quiet despair |
| PRODUCT | 5 Clay infographic (optional), 6 Discovery |
| PAYOFF | 7 Transformation |
| CTA | 8 Resolution and CTA |

Write one narrator sentence per beat plus any sparse character dialogue, then present the numbered script block and wait:

```
Claymation script (confirm before I generate anything)
  1. [SETUP]      narrator: "Diane had used the same kitchen for thirty years."
  2. [INCITING]   narrator: "Until the morning the mirror told a different story."
  ...
  8. [CTA]        narrator: "Everbloom. The age you feel, not the age you are."
Narrator words: ~N total. Estimated runtime: ~Xs. One narrator voice across all beats: yes.
Approve this script? (yes / edit / rewrite)
```

Size each beat's clip duration from its narrator line at roughly 2.5 words per second: 1 to 17 words maps to a 6s clip, 18 to 25 words to 8s, 26 to 32 words to 10s, and 33 or more words means the line splits across beats.

### Phase 2: Storyboard stills (credit gate, then generate sequentially)

Present the credit estimate for the still batch (see Credit estimation below) and wait for yes.

1. Generate the Beat 1 hero still: `arcads_generate_image_gpt` with the Beat 1 prompt from `references/storyboard-prompts.md` plus the verbatim STYLE LOCK, `model: "gpt-image-2"`, `aspectRatio: "9:16"`. Poll with `arcads_watch_asset`, download the result, show the user, and iterate until approved.
2. Generate the other protagonist beats (2, 4, 6, 7, 8) **sequentially**, passing the approved Beat 1 still (and the most recent approved still) as `referenceImages` (max 5) to lock the protagonist. Approve each before the next. Remember the fresh-upload rule for every chained reference.
3. Beat 3 (the two-character scene): pass the approved protagonist still plus the supporting character's cast-sheet description.
4. Beat 5 (the clay infographic) is independent; no character continuity needed. Beat 7 should also reference the approved Beat 6 still so the product prop stays identical.
5. **Texture fallback:** if gpt-image-2 smooths the clay texture or loses fingerprint detail on close-ups, switch those specific beats (typically 5 and 6) to `arcads_generate_image_nano_banana`. Do not switch the whole ad; nano-banana is slightly weaker on cross-beat identity, so use it only where character identity does not matter.
6. QA every still with the claymation checklist in `references/storyboard-prompts.md` (clay texture visible, matte eyes, real knit weave, hand-painted label, identity holds, clean lower third on Beat 8). Max 2 retries per beat; if the third attempt fails, stop and ask the user.

### Phase 3: Animate each beat (credit gate, then fire in parallel)

Present the credit estimate for the animation batch. With 8 beats this is by far the dominant cost of the whole pipeline. Wait for yes.

For each approved still: upload it fresh, read its per-beat prompt in `references/animation-prompts.md`, then call `arcads_generate_video_seedance_20` with `prompt` (no narrator line, ambient sound description is fine, and always include "no on-screen text, no captions, no subtitles"), `referenceImages: [fresh filePath of beatN.png]`, `aspectRatio: "9:16"`, `duration` 4 to 12 chosen per beat, `resolution: "720p"`, `audioEnabled: false`.

Beats are independent, so fire them all, then poll every asset id with `arcads_watch_asset` at a relaxed cadence (a Seedance clip typically takes around 7 minutes, occasionally up to 15). Download each finished clip to `outputs/claymation-ad/<slug>/clips/beatN.mp4`.

QA each clip with the claymation-specific checks: clay flattening into a smooth 3D render, fabric losing its knit weave, label paint going digitally crisp, melted features, mirror reflections misbehaving. Max 2 retries per beat.

### Phase 4: Narrator voiceover (credit gate, then generate)

1. Call `arcads_list_voices` and pick ONE narrator `voiceId` with a warm storyteller tone (the Aardman feel). Known server quirk: the `gender` / `age` / `language` filters have returned errors on some server versions; if a filtered call fails, call unfiltered and filter the returned list yourself. A second `voiceId` is allowed only for a supporting character's single line.
2. Present the TTS credit estimate and wait for yes.
3. Per beat: `arcads_text_to_speech(script=<beat narrator line>, voiceId=<chosen>)`, poll with `arcads_watch_asset` (TTS usually finishes in 5 to 10 seconds), download to `outputs/claymation-ad/<slug>/vo/beatN.mp3`. Character lines render separately with their own voice.

### Phase 5: Assembly (be honest about what the MCP can and cannot do)

**No Arcads MCP tool muxes a standalone audio track onto a video.** That one step needs a local tool. Check whether `ffmpeg` exists on the host by running `ffmpeg -version` in the terminal, then pick a path:

**Path A: ffmpeg available (optional, recommended).** Per beat, trim the clip to the VO and mux:

```bash
VO=outputs/claymation-ad/<slug>/vo/beatN.mp3
CLIP=outputs/claymation-ad/<slug>/clips/beatN.mp4
VO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VO")
CLIP_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$CLIP")
TARGET=$(awk -v a="$CLIP_DUR" -v b="$VO_DUR" 'BEGIN{m=b+0.5; print (a<m)?a:m}')
ffmpeg -y -i "$CLIP" -t "$TARGET" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -an tight_beatN.mp4
ffmpeg -y -i tight_beatN.mp4 -i "$VO" -c:v copy -c:a aac -shortest voiced_beatN.mp4
```

If the VO is longer than the clip, split the line or regenerate the clip longer; never speed up the VO. Then concatenate the voiced beats in story order (local ffmpeg concat with re-encode is simplest; `arcads_stitch_videos` also works but caps at 6 clips per call, so an 8-beat ad means stitching 1 through 6, downloading the part, re-uploading it with beats 7 and 8, and stitching again). Save the master to `outputs/claymation-ad/<slug>/claymation-master.mp4`.

Optional stop-motion judder pass (only if the user explicitly wants the 12 fps stepped feel; the smooth default matches the genre's reference ads): `ffmpeg -i master.mp4 -filter:v "fps=12,fps=24" -c:a copy judder.mp4`. Never ask Seedance for judder in the prompt; it breaks the aesthetic.

**Path B: no ffmpeg.** Be straight with the user. Deliver:
1. The per-beat silent clips and the per-beat VO mp3 files.
2. Optionally a stitched silent visual master via `arcads_stitch_videos` so they can preview the story flow.
3. A short written assembly guide: clip order, and per beat "trim to VO length plus about half a second, VO starts about a quarter second in." Any editor (CapCut, Descript, a desktop NLE) can do this in minutes.

Do not pretend the MCP produced a finished voiced master when it did not.

### Phase 6: Captions

Captions only work automatically on a master that has the VO baked in (the tool transcribes the audio). On Path A: call `arcads_add_subtitles` on the master, `style: "style_1"` for the white-with-black-stroke look (see `references/style-guide.md` for the alternative highlight-block look and how close the preset styles get). If the master was stitched via `arcads_stitch_videos`, pass the stitch result's asset id via `sourceVideoAssetId` instead of re-uploading the file. If a subtitles pass costs credits on this account, gate it like any other batch. On Path B: skip captions, or offer to run this step later once the user sends back their assembled voiced master.

### Phase 7: Music and sound effects (optional, be honest)

The Arcads MCP has text-to-speech but **no music generation tool**. Options, in order of preference:
1. Ship narrator-VO-only. Narrated claymation carries extremely well on voice and captions alone.
2. Baked ambient sound: regenerating a beat with `audioEnabled: true` makes Seedance render ambient SFX into the clip (kettle pours, room tone), but that costs another full video generation and the ambient bed then sits under your VO mix, so only do this deliberately and with a fresh credit gate.
3. If the user supplies a licensed music file and ffmpeg is available, mix it under the VO at low volume as an optional final pass.

### Phase 8: Deliver and log

1. Send the final file (or its download link plus the per-beat assets on Path B) to the user in the chat channel they are using.
2. Report total credits actually charged, summing `creditsCharged` across all asset ids, clearly labeled with anything still estimated. On daily-limit plans Arcads reports `creditsCharged: 0` with `usedDailyLimit: true`; report that honestly.
3. Update `outputs/arcads-usage-log.jsonl` at the workspace root with final statuses and credits.
4. If the user wants it on Meta, hand off to `meta-ad-launcher` (paused, always).

## Credit estimation (how to build the estimate)

Arcads exposes no billing endpoint, so estimates come from, in order:
1. The shared usage log `outputs/arcads-usage-log.jsonl` at the workspace root: past entries with a matching configuration (model, duration, resolution).
2. Example observed rates from one workspace in mid 2026, which you must treat as stale until confirmed: a 5 second 720p Seedance 2.0 image-to-video clip ran about 240 credits (the dominant cost, and billed at submission, so it shows while the asset is still pending), TTS about 8 credits per line, a subtitles pass about 80 credits, stitching 0, and gpt-image-2 stills 0 on a daily-limit image plan. On those rates an 8-beat ad is essentially 8 times the Seedance cost, on the order of 2,000 credits before retries; a validated 2-beat micro ad ran 576 credits total.
3. Ask the user what their plan charges and record the answer in the log for next time.
4. If the log is empty and the user does not know their rates: run a **calibration batch of 1**. With the user's go-ahead, generate one unit of the batch first (one still, one Seedance clip, or one TTS line, whichever batch you are gating), observe the credits actually consumed (`creditsCharged` from the MCP, or have the user check the Arcads dashboard), append that to the usage log, then estimate the rest of the batch from the observed number and confirm before generating the remainder.

Always present the breakdown per batch, label it an estimate, tell the user to confirm exact pricing in the Arcads platform, and wait for yes. A full 8-beat ad is roughly 8 stills + 8 Seedance clips + 8 TTS lines + 1 or 2 stitches + 1 captions pass, plus up to 2 retries per beat. Offer the 5-beat short as the budget option before the user commits.

## Constraints and gotchas (quick reference)

| Item | Note |
|---|---|
| Seedance aspect | 9:16 or 16:9 only, no 1:1. Use 9:16. |
| Seedance image input | `referenceImages: [still]` (max 3; the first is addressed as `@(img1)` in the prompt). |
| `referenceImages` vs `referenceVideos` | Mutually exclusive on Seedance. This pipeline is pure image-to-video; never pass both. |
| gpt-image-2 refs | Max 5; exceeding it returns a 400. nano-banana takes up to 14. |
| Forbidden words | Style guide's banned list plus Seedance's `cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect`. A content-check `failed` means strip flagged words and rewrite; never resend the same prompt. |
| Seedance invents captions | Always include "no on-screen text, no captions, no subtitles" in every animation prompt; burn captions in post. |
| Clay texture flattening | The number one QA risk: video models smooth clay into a 3D render. Tighten the material-detail block and add "preserve all clay texture from @(img1)" on retries; fall back to nano-banana for texture-critical stills. |
| Stop-motion judder | Post-process only (ffmpeg fps filter), never in the Seedance prompt. |
| VO muxing | Not possible via MCP; ffmpeg (optional) or user assembly. |
| Stitch limit | 2 to 6 clips per call; batch and re-stitch for 8 beats. |
| Voice list filters | `arcads_list_voices` filters have errored on some server versions; call unfiltered and filter locally if so. |
| Polling | `arcads_watch_asset` until `generated` or `failed`; the success response includes a time-limited download URL (roughly 12 hours), so download promptly. Avoid `arcads_get_asset`. |
| 422 errors | Usually an enum or moderation issue; check `aspectRatio` and `duration`, tighten the prompt. |

## Related skills

- `pixar-style-ad` for the smooth 3D family-movie look (sibling story-ad pipeline).
- `ugc-video-ad` for live-action-style talking-head ads.
- `human-ad-copy` for the primary text and headlines that go with this creative.
- `meta-ad-launcher` to put the finished ad on Meta, paused.
