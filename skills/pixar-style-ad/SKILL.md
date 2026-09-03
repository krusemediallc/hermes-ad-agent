---
name: pixar-style-ad
description: Produce a 3D animated character story ad in the Disney-Pixar feature film look, end to end through the Arcads MCP server. You plan a hook / problem / product / payoff / CTA story, lock a consistent cast, generate storyboard stills with gpt-image-2, animate each beat with Seedance 2.0 image-to-video, voice it with Arcads text-to-speech, then assemble, caption, and deliver. Use this skill when the user asks for a "Pixar-style ad", "Pixar cartoon ad", "3D animated ad", "animated story ad", "give my product a cute character or mascot ad", or shares a reference video with the 3D family-movie look. Requires the Arcads MCP server to be connected; every generation batch gets a credit-cost estimate and explicit user confirmation before it fires. For the clay stop-motion look use the claymation-ad skill instead.
---

# Pixar-Style Ad

You are building a short vertical video ad (9:16, roughly 30 to 90 seconds) in the Disney-Pixar 3D animated feature film aesthetic. The hook of this genre is anthropomorphism plus a tiny story, not the product itself. The pipeline is: story beats, cast sheet, storyboard stills (gpt-image-2), per-beat animation (Seedance 2.0 image-to-video), voiceover (Arcads TTS), assembly, captions, delivery.

This is one of the most expensive creative pipelines in this skill pack. Video generation dominates the cost. You must estimate credits and get an explicit "yes" from the user before EVERY generation batch, not just once at the start.

## Before you start

1. **Verify the Arcads MCP server is connected.** List your actually-available tools and confirm you can see the `arcads_*` tools named below. Tool names and parameters can differ between server versions, so always trust your live tool list over the names written here. If no Arcads tools are available, stop and help the user connect the Arcads MCP server first (see the repo's SETUP.md).
2. **Read the user's BRAND.md.** Every creative decision (product, audience, tone, claims you may and may not make) comes from it. If BRAND.md does not exist, offer to run the `brand-setup` skill before continuing.
3. **Read the reference files in this folder, in order.** They are the creative source of truth:
   - `references/style-guide.md` (the aesthetic, the story arc, the cast sheet template, the negative block)
   - `references/storyboard-prompts.md` (per-beat gpt-image-2 prompt formulas)
   - `references/animation-prompts.md` (per-beat Seedance 2.0 prompt formulas plus Seedance platform rules)

## Tools used (Arcads MCP)

| Tool | Role |
|---|---|
| `arcads_list_products` | Resolve the `productId` if the account has products configured (auto-selects when there is only one). |
| `arcads_generate_image_gpt` | Storyboard stills. `model: "gpt-image-2"`, `aspectRatio: "9:16"`, up to 5 `referenceImages`, `nbGenerations` 1 to 10. |
| `arcads_generate_video_seedance_20` | Animate each approved still (image-to-video). `referenceImages: [still]`, `aspectRatio: "9:16"`, `duration` 3 to 15, `resolution: "720p"`, `audioEnabled: false`. |
| `arcads_list_voices` | Pick the voiceover voice once. |
| `arcads_text_to_speech` | One voiceover line per beat, same `voiceId` throughout. |
| `arcads_get_upload_url` | Presigned upload for any local file the generation tools need as a reference. |
| `arcads_stitch_videos` | Concatenate clips, 2 to 6 per call. |
| `arcads_add_subtitles` | Burn captions onto the voiced master (auto-transcribes from the baked-in audio). |
| `arcads_watch_asset` | Poll every asset id until `generated` or `failed`; on success it also returns the download URL. |

The bare `arcads_*` names above are the server-native tool IDs the Arcads MCP advertises. The Hermes runtime registers each one under a prefixed callable name (observed shape: `mcp__arcads__arcads_watch_asset`). Discover the registered name for each tool you need (tool_search or your live tool list) and call that; never assume the bare name is callable, and never use a tool count as a readiness check (counts drift day to day). Do not build the flow around `arcads_get_asset`; it intermittently disappears from the server with a "-32602 tool not found" error. `arcads_watch_asset` is the reliable poller. On any -32602, refresh your tool catalog, re-discover the registered name, and re-issue the read call (never re-issue a generate call without its allowance).

## Arcads cost contract (read before any credit gate)

- **Only `creditsCharged` is cost.** Read it back from each asset (`arcads_watch_asset` returns it). Nothing else is cost. Some responses also carry an `mp` field; that is megapixel or usage metadata, never credits. Reading `mp` as credits has understated real cost by hundreds of times.
- **One account-specific historical observation, not a rate and not an estimate:** a 12-second 720p Seedance 2.0 video charged `creditsCharged: 432` on one account in early September 2026 while its `mp` field read 0.9216. Your account, plan, and model will differ.
- **Arcads has no quote or billing endpoint.** Ask the user for their plan's rate first. If they do not know it, the first paid generation of each batch type is an explicit unknown-cost calibration: the approval must state a user-defined maximum acceptable credit exposure for that one operation, you generate exactly one unit, read back `creditsCharged`, log it, and re-gate the rest of the batch against the observed number.
- **Every Arcads operation is credit-accounted**, including ones that return `creditsCharged: 0` under a daily limit: stills, clips, TTS lines, retries, regenerations, QA-fix regenerations, transcription, `arcads_analyze_media`, `arcads_add_subtitles`, enhancement, stitching, trimming, editing. None of them run automatically. They run only when the batch approval named them with a count-and-cost allowance (for example "up to 1 retry per beat at or under N credits each"); otherwise ask again before each one.
- **Log every operation** to `outputs/arcads-usage-log.jsonl` at the workspace root (resolve the root from the setup-state file, never from memory of the conversation): tool, model, beat, duration, resolution, aspectRatio, count (`nbGenerations`), date, every assetId, final status, `creditsCharged` exactly as returned, and a daily-limit indicator (`usedDailyLimit` when the server returns it). Report actual `creditsCharged` per operation to the user, plus any daily-limit use.
- **Signed `downloadUrl` and `presignedUrl` values are temporary credentials.** Pass them between tools as opaque values. Never paste one into a terminal command line, a log line, the usage log, the cast sheet, or any durable file. Download with a fetch step that reads the URL from a variable or stdin rather than a command argument, and save files under `outputs/pixar-ad/<slug>/`.

## Hard rules (never relax these)

1. **Credit gate before EACH generation batch.** Before the storyboard batch, before the animation batch, before the TTS batch, before any stitch, and before a captions pass: present an itemized credit estimate, label it an estimate (Arcads exposes no billing endpoint), state its basis (the user's plan rate, the usage log, or unknown with a user-stated maximum exposure for a calibration of 1), name any retry allowance with a count and cost, tell the user to confirm exact pricing in the Arcads platform, and wait for an explicit yes. QA-fix regenerations are separate credit-accounted operations: they run only inside a named allowance, otherwise ask before each one, and always report their actual `creditsCharged`.
2. **Script approval gate before any generation.** Present the numbered beat script (every spoken line included) and get an explicit yes. This gate is separate from the credit gate; never treat one approval as covering both.
3. **Aesthetic lock.** Disney-Pixar 3D feature film, not anime, not Ghibli, not 2D, not claymation. Paste the STYLE LOCK from `references/style-guide.md` verbatim into every still prompt. Honor both banned-word lists: the style guide's (`anime`, `Ghibli`, `2D`, `cel-shaded`, `cartoon`, `photorealistic`, and friends) and Seedance's (`cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect`).
4. **Storyboard first, then animate.** Never one-shot text-to-video the whole ad. Character identity drifts, and Seedance's 15 second ceiling caps a single clip far below ad length anyway. Lock each still with user approval before animating it.
5. **One voiceover voice across all beats.** Pick one `voiceId` and reuse it (a second characterful voice is allowed for the anthropomorphized problem character's line only). Never use an in-prompt narrator line in Seedance; set `audioEnabled: false` and overlay the VO in post.
6. **No dead space.** The voiceover drives clip duration. Each assembled beat should run about `vo_duration + 0.5s`. Never speed up the VO to fit; split the line or regenerate the clip longer instead.
7. **9:16 vertical.** Seedance has no 1:1, and the close-up macro framings in this genre do not translate to 16:9.
8. **Never fabricate numbers.** Credits, durations, statuses: report only what the MCP actually returned, and only `creditsCharged` is cost (never `mp`). Log every operation with the fields in the cost contract above to the shared usage log `outputs/arcads-usage-log.jsonl` at the workspace root so future estimates get better.
9. **Meta launch is out of scope here.** When the user wants the finished ad on Meta, hand off to the `meta-ad-launcher` skill, which always creates everything PAUSED.
10. **QA states stay separate.** Report metadata-pass, sampled-frames-pass, transcript-pass, motion/lip-sync review required, claims/branding check, and human approval per clip; never an overall "QA passed" from sampled frames plus a transcript.

## Reference file uploads (read this before Phase 2)

The Arcads MCP server is remote. Depending on how your client bridges files, it may not be able to read the local disk. Every reference image or video a generation tool consumes may therefore need to be an Arcads S3 `filePath` rather than a local path. That applies to a user-supplied product photo AND to each generated still you chain forward (Beat 1 still as Beat 2's identity reference, approved still into the Seedance image-to-video call, clips into stitch).

Procedure:

1. Try passing the local file path first. Some MCP clients bridge local files automatically, and some editing tools (`arcads_stitch_videos`, `arcads_add_subtitles`, `arcads_trim_video`) have accepted local paths on some deployments. `arcads_analyze_media` (transcription and analysis) needs an uploaded or remote path on the hosted deployment: a local path returned `REFERENCE_FILE_NOT_FOUND`.
2. If the tool errors with "File not found" or `REFERENCE_FILE_NOT_FOUND`, use the upload flow: call `arcads_get_upload_url(mimeType)` to get `{presignedUrl, filePath}`, then send the file bytes to the `presignedUrl` with a plain HTTP PUT (no auth header; set the Content-Type header to the same mimeType; the raw file bytes are the body; a 200 response means it worked). Read the presigned URL from a variable rather than pasting it into a saved command; it is a temporary credential. Pass the returned `filePath` in `referenceImages`.
3. **Temp `filePath`s are single-use.** The first tool call that references one consumes it. Using the same still as Beat 2's reference and again for its Seedance call means two separate uploads. Upload a fresh copy immediately before each consuming call. A single call with `nbGenerations` greater than 1 counts as one consumer, so one upload covers it.
4. Never pass an `arcads_register_image` asset id in `referenceImages`; that returns `INVALID_REFERENCE_IMAGES`. The register tools are for persistent assets, not generation references.

To chain a generated still: after it reaches `generated`, download it from the `arcads_watch_asset` download URL to `outputs/pixar-ad/<slug>/stills/beatN.png`, then upload a fresh temp copy right before each call that uses it.

## Workflow

### Phase 0: Brand, product, cast

1. Read BRAND.md. Ask which product this ad is for; call `arcads_list_products` if the account has products configured.
2. Build the cast and continuity sheet from `references/style-guide.md`: protagonist, the anthropomorphized problem character, mascot characters, setting, product packaging description, and the verbatim STYLE LOCK. Save it to `outputs/pixar-ad/<slug>/cast-sheet.md` and confirm it with the user.

### Phase 1: Story beats and script (approval gate)

Plan the ad around five story jobs, then map them onto 4 to 6 beats:

| Story job | What it does | Typical beat |
|---|---|---|
| HOOK | The anthropomorphized problem character grabs attention in the first seconds | Beat 1 |
| PROBLEM | The pain point lands emotionally (often the same beat as the hook, or a quick montage) | Beat 1 to 2 |
| PRODUCT | The protagonist meets the product in a sunlit cozy interior | Beat 2 to 3 |
| PAYOFF | The mascot mechanism scene shows how it works, plus the visible result | Beat 3 to 4 |
| CTA | Protagonist with packaging, clean lower third for the caption | Final beat |

Write one sentence of voiceover per beat. Then present the numbered script block and wait:

```
Pixar script (confirm before I generate anything)
  1. [HOOK]    drain-hair character: "I clog your shower every single morning."
  2. [PRODUCT] protagonist: "Then I found this."
  3. [PAYOFF]  narrator: "Tiny helpers rebuild each strand from the root."
  4. [CTA]     narrator: "Try {Brand} {Product} today."
VO words: ~N total. Estimated runtime: ~Xs. One voice across all beats: yes.
Approve this script? (yes / edit / rewrite)
```

### Phase 2: Storyboard stills (credit gate, then generate sequentially)

Present the credit estimate for the still batch (see Credit estimation below) and wait for yes.

1. Generate the Beat 1 hero still: `arcads_generate_image_gpt` with the Beat 1 prompt from `references/storyboard-prompts.md` plus the verbatim STYLE LOCK, `model: "gpt-image-2"`, `aspectRatio: "9:16"`. Poll with `arcads_watch_asset`, download the result, and show it to the user. Iterate until approved.
2. Generate Beats 2 through N **sequentially**, passing the prior approved still(s) as `referenceImages` (max 5) to lock the protagonist's face, outfit, and the product packaging. Get approval on each before the next. Remember the fresh-upload rule for every chained reference.
3. The mascot mechanism beat only needs the protagonist reference if the protagonist appears in frame; otherwise generate it independently from the cast sheet's mascot description.
4. QA every still before approving it forward: correct finger counts, aligned eyes, readable and accurate product label, identical protagonist across beats, no burned-in text, clean lower third where captions will land. Inspect the image yourself if you can view images; otherwise walk the user through the checklist. A corrected-prompt retry is a new credit-accounted generation: run it only inside the retry allowance the batch approval named (never more than 2 per beat), otherwise stop and ask the user.

If the user asks for variations of a still, use `nbGenerations` (1 to 10) in a single call rather than repeated calls; each variation returns its own asset id.

### Phase 3: Animate each beat (credit gate, then fire in parallel)

Present the credit estimate for the animation batch. Video is the dominant cost of the whole pipeline. Wait for yes.

For each approved still: upload it fresh, read its per-beat prompt in `references/animation-prompts.md`, then call `arcads_generate_video_seedance_20` with `prompt` (no narrator line, ambient sound description is fine, and always include "no on-screen text, no captions, no subtitles"), `referenceImages: [fresh filePath of beatN.png]`, `aspectRatio: "9:16"`, `duration` 3 to 10 chosen per beat, `resolution: "720p"`, `audioEnabled: false`.

Beats are independent, so fire them all, then poll every asset id with `arcads_watch_asset` at a relaxed cadence (a Seedance clip typically takes around 7 minutes, occasionally up to 15). Download each finished clip to `outputs/pixar-ad/<slug>/clips/beatN.mp4`.

QA each clip and report every state separately; never collapse them into one "QA passed":

| State | What clears it |
|---|---|
| metadata-pass | Duration, resolution, aspect ratio match the approved plan, and the clip is silent as requested. |
| sampled-frames-pass | Sampled frames show no character morphing, hand artifacts, eye misalignment, product-label drift, or invented captions. |
| transcript-pass | Not applicable to silent clips; applies to the voiced master (the VO matches the approved script verbatim). Transcription through Arcads is credit-accounted; run it only if allowed, otherwise the user listens. |
| motion/lip-sync review required | Morphing over time and plausibility of any mouth movement can only be judged by watching the clip end to end. Frames never clear this state. |
| claims/branding check | On-screen product and packaging match the cast sheet; nothing implies a claim BRAND.md does not allow. |
| human approval | The user has watched the clip and said yes. |

A retry with a tightened constraint block is a new credit-accounted generation: run it only inside the retry allowance the batch approval named (never more than 2 per beat), otherwise stop and ask.

### Phase 4: Voiceover (credit gate, then generate)

1. Call `arcads_list_voices` and pick ONE `voiceId` matching the brand persona (optionally a second characterful voice for the problem character's single line). If the tool rejects `gender` / `age` / `language` filters with an error, call it unfiltered and filter the returned list yourself.
2. Present the TTS credit estimate and wait for yes.
3. Per beat: `arcads_text_to_speech(script=<beat line>, voiceId=<chosen>)`, poll with `arcads_watch_asset` (TTS is fast, usually 5 to 10 seconds), download to `outputs/pixar-ad/<slug>/vo/beatN.mp3`.

### Phase 5: Assembly (be honest about what the MCP can and cannot do)

**No Arcads MCP tool muxes a standalone audio track onto a video.** That one step needs a local tool. Check whether `ffmpeg` exists on the host by running `ffmpeg -version` in the terminal, then pick a path:

**Path A: ffmpeg available (optional, recommended).** Per beat, trim the clip to the VO and mux:

```bash
VO=outputs/pixar-ad/<slug>/vo/beatN.mp3
CLIP=outputs/pixar-ad/<slug>/clips/beatN.mp4
VO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VO")
CLIP_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$CLIP")
TARGET=$(awk -v a="$CLIP_DUR" -v b="$VO_DUR" 'BEGIN{m=b+0.5; print (a<m)?a:m}')
ffmpeg -y -i "$CLIP" -t "$TARGET" -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -an tight_beatN.mp4
ffmpeg -y -i tight_beatN.mp4 -i "$VO" -c:v copy -c:a aac -shortest voiced_beatN.mp4
```

If the VO is longer than the clip, split the line or regenerate the clip longer (a new credit-accounted generation that needs its own gate); never speed up the VO. Then concatenate the voiced beats (local ffmpeg concat with re-encode is simplest and costs no credits, or upload each voiced clip fresh and use `arcads_stitch_videos`, max 6 per call, batching for more, each call gated). Save the master to `outputs/pixar-ad/<slug>/pixar-master.mp4`.

**Path B: no ffmpeg.** Be straight with the user. Deliver:
1. The per-beat silent clips and the per-beat VO mp3 files.
2. Optionally a stitched silent visual master via `arcads_stitch_videos` so they can preview the flow.
3. A short written assembly guide: clip order, and per beat "trim to VO length plus about half a second, VO starts about a quarter second in." Any editor (CapCut, Descript, a desktop NLE) can do this in minutes.

Do not pretend the MCP produced a finished voiced master when it did not.

### Phase 6: Captions

Captions only work automatically on a master that has the VO baked in (the tool transcribes the audio). On Path A: call `arcads_add_subtitles` on the master (try the local path first; it may auto-upload, otherwise presign-upload it), `style: "style_1"` for the white-with-black-stroke look, and poll. A subtitles pass is a credit-accounted operation on every account (a `creditsCharged: 0` under a daily limit is still metered), so gate it like any other batch and report its actual `creditsCharged`. On Path B: skip captions, or offer to run this step later once the user sends back their assembled voiced master.

### Phase 7: Music and sound effects (optional, be honest)

The Arcads MCP has text-to-speech but **no music generation tool**. Options, in order of preference:
1. Ship VO-only. This genre carries well on voiceover and captions alone.
2. Baked ambient sound: regenerating a beat with `audioEnabled: true` makes Seedance render ambient SFX into the clip, but that costs another full video generation and the ambient bed then sits under your VO mix, so only do this deliberately and with a fresh credit gate.
3. If the user supplies a licensed music file and ffmpeg is available, mix it under the VO at low volume as an optional final pass.

### Phase 8: Deliver and log

1. Send the final file (or its download link plus the per-beat assets on Path B) to the user in the chat channel they are using.
2. Report actual `creditsCharged` per operation and the total, summing `creditsCharged` across all asset ids, clearly labeled with anything still pending. On daily-limit plans Arcads reports `creditsCharged: 0` with `usedDailyLimit: true`; report that per operation rather than claiming it was free forever.
3. Update `outputs/arcads-usage-log.jsonl` at the workspace root with final statuses, credits, and daily-limit indicators.
4. If the user wants it on Meta, hand off to `meta-ad-launcher` (paused, always).

## Credit estimation (how to build the estimate)

Arcads exposes no billing or quote endpoint, so estimates come from, in order:
1. Ask the user what their plan charges per still, per Seedance second or clip at the chosen resolution, per TTS line, per stitch, and per subtitles pass. Record the answers in the usage log for next time.
2. The shared usage log `outputs/arcads-usage-log.jsonl` at the workspace root: past entries with a matching configuration (model, duration, resolution), using their recorded `creditsCharged`.
3. If neither exists for a batch type: run an **unknown-cost calibration of 1**. The approval must state a user-defined maximum acceptable credit exposure for that single operation. Generate one unit of the batch first (one still, one Seedance clip, or one TTS line, whichever batch you are gating), read back `creditsCharged` (only that field; `mp` is never credits), append it to the usage log, then estimate the rest of the batch from the observed number and confirm before generating the remainder.

Do not use fixed credit figures from this file or memory as estimates. The only historical datapoint carried here, a 12-second 720p Seedance 2.0 video charging 432 credits on one account in early September 2026, is an account-specific observation, not a rate. Seedance bills at submission, so a charge can show while the asset is still pending. Stitching, TTS, and subtitles have returned `creditsCharged: 0` under a daily limit on some accounts; that is a daily-limit use, not "free", and the real rate on the user's plan is unknown until observed.

Always present the breakdown per batch, state its basis, name the retry allowance (count and cost) or state that there is none, label it an estimate, tell the user to confirm exact pricing in the Arcads platform, and wait for yes. A typical 5-beat ad is roughly 5 stills + 5 Seedance clips + 5 TTS lines + 1 stitch + 1 captions pass, plus whatever retries the user allows.

## Constraints and gotchas (quick reference)

| Item | Note |
|---|---|
| Seedance aspect | 9:16 or 16:9 only, no 1:1. Use 9:16 for this genre. |
| Seedance image input | `referenceImages: [still]` (max 3; the first is addressed as `@(img1)` in the prompt). |
| `referenceImages` vs `referenceVideos` | Mutually exclusive on Seedance. This pipeline is pure image-to-video; never pass both. |
| gpt-image-2 refs | Max 5. Each beat only chains 1 or 2 prior stills, so this never binds. Exceeding it returns a 400. |
| gpt-image-2 aspect | 1:1, 16:9, 9:16 only. |
| Forbidden words | Style guide's banned list plus Seedance's `cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect`. A content-check `failed` means strip flagged words and rewrite; never resend the same prompt. |
| Seedance invents captions | Always include "no on-screen text, no captions, no subtitles" in every animation prompt; burn captions in post. |
| VO muxing | Not possible via MCP; ffmpeg (optional) or user assembly. |
| Stitch limit | 2 to 6 clips per call; batch and re-stitch for more. |
| Polling | `arcads_watch_asset` until `generated` or `failed`; the success response includes a time-limited signed download URL (roughly 12 hours), so download promptly, and treat the URL as a credential (never in a command argument, log, or durable file). Avoid `arcads_get_asset`. |
| 422 errors | Usually an enum or moderation issue; check `aspectRatio` and `duration`, tighten the prompt. |

## Related skills

- `claymation-ad` for the stop-motion clay look (sibling story-ad pipeline).
- `ugc-video-ad` for live-action-style talking-head ads.
- `human-ad-copy` for the primary text and headlines that go with this creative.
- `meta-ad-launcher` to put the finished ad on Meta, paused.
