# Arcads MCP Server Reference

This is the repo-level reference for the **Arcads MCP server**, the creative-generation backend for every image and video skill in this pack. It covers what the server is, how to connect it to a Hermes agent, the tool roster, the two core usage patterns (batching and polling), model availability, credit-cost guidance, and troubleshooting.

The skills themselves are self-contained and do not depend on this file; this doc exists for setup (see [SETUP.md](../SETUP.md), Step 3) and for humans who want the full picture.

> **Tool names vary between server versions.** Every tool name in this document was observed on a real Arcads MCP session, but Arcads ships changes without notice. Always trust the live tool list in your current session over any list written here or in a skill.

---

## What the Arcads MCP is

Arcads ([arcads.ai](https://arcads.ai/?via=hermes)) is an AI ad-creative platform: image generation, video generation, UGC talking-head actors, text-to-speech, and media editing. The **Arcads MCP server** is Arcads' hosted remote MCP endpoint at:

```
https://mcp.arcads.ai
```

Once connected, your agent gets `arcads_*` tools for the whole platform: generate images and videos across a dozen models, create talking-head actor videos, synthesize voiceovers, stitch and subtitle clips, analyze media, and poll generation jobs. The server handles authentication itself. There are no API keys to paste into env files and no REST scripts to maintain; everything goes through MCP tool calls.

**Requirements:** an Arcads account with an **active subscription and credits**. Generations consume credits (see the credit-cost section below). If you do not have an account yet, sign up here: **[https://arcads.ai/?via=hermes](https://arcads.ai/?via=hermes)**

---

## Connecting to Hermes

Hermes configures MCP servers in `~/.hermes/config.yaml` under `mcp_servers`. On a Hostinger Managed App, edit the file from the in-browser terminal (hPanel → Hermes → Manage → CLI) or via the Hermes dashboard's MCP page.

1. Add the server entry:

   ```yaml
   mcp_servers:
     arcads:
       url: "https://mcp.arcads.ai"
       auth: oauth
   ```

2. Attempt the login flow:

   ```bash
   hermes mcp login arcads
   ```

3. Hot-reload MCP servers with `/reload-mcp` in chat (or restart the session).

4. Verify: list your available tools and confirm `arcads_*` tools appear. A cheap read-only smoke test is `arcads_list_products` or `arcads_list_voices`. Do not run a generation tool as a test; generation costs credits.

**UNVERIFIED, be defensive:** Arcads' Help Center documents the MCP as a "add the URL and connect" custom-connector flow tied to your app.arcads.ai login, but does not disclose the exact auth mechanism (OAuth discovery vs. header credentials). Try `auth: oauth` first. If the server does not advertise OAuth discovery and the login command fails:

- Check the Hermes MCP catalog (`hermes mcp` in the terminal, or the dashboard's MCP page) for an Arcads entry with a pre-wired connect flow, and follow whatever your build actually offers.
- Check Arcads' Help Center article "Arcads MCP" for the current connect instructions.
- If the documented connection method fails, check the Arcads Help Center or contact Arcads support.

Expect a browser sign-in to app.arcads.ai at some point in the connect flow; the connection is tied to that account and its subscription.

---

## Tool reference

Grouped by function. All names use the `arcads_` prefix as observed on a live session; verify against your own tool list before calling.

### Image generation

| Tool | Purpose |
|---|---|
| `arcads_generate_image` | Generic text-to-image. `model` selects the engine: `nano-banana`, `nano-banana-2`, `gpt-image`, `gpt-image-2`, `seedream`, `seedream_5_lite`, `grok_image`. |
| `arcads_generate_image_nano_banana` | Nano Banana / Nano Banana 2 images. Up to 14 reference images. The default choice for photoreal, lifestyle, and multi-reference work. |
| `arcads_generate_image_gpt` | gpt-image-2 images. Up to 5 reference images. Best for dense typography and text-heavy layouts (comparison tables, headline cards). |

### Video generation

| Tool | Purpose |
|---|---|
| `arcads_generate_video` | Generic text-to-video or image-to-video. `aspectRatio` (16:9, 9:16, 1:1), `duration` (3 to 15s), `startFrame` / `endFrame`, `nbGenerations`, `enhance`. Use when the user does not name a model. |
| `arcads_generate_video_seedance_20` | Seedance 2.0. The workhorse for UGC-style and multi-shot ad video. |
| `arcads_generate_video_sora2` | Sora 2. Generates speech from the prompt. |
| `arcads_generate_video_veo31` | Veo 3.1. Supports a `startFrame` for a person. |
| `arcads_generate_video_kling_30_pro` | Kling 3.0 Pro. B-roll and motion. |
| `arcads_generate_video_kling_26_pro` | Kling 2.6 Pro. B-roll and motion. |
| `arcads_generate_video_kling_30_4k` | Kling 3.0 at 4K output. |
| `arcads_generate_video_seedance_15` | Seedance 1.5 (older generation). |
| `arcads_generate_video_grok` | Grok video model. |
| `arcads_generate_video_happy_horse` | Happy Horse video model. |
| `arcads_animate_image` | Animate a still image (engines: kling30-animate, wan22). |
| `arcads_audio_driven` | Talking-head actor video: an actor source (situation, source video, or image) combined with a voice source (script or audio). The core UGC tool. |

### Audio

| Tool | Purpose |
|---|---|
| `arcads_text_to_speech` | Text-to-speech from a `script` and `voiceId`. Fast (roughly 5 to 10 seconds). |
| `arcads_list_voices` | Voice catalog; source of valid `voiceId` values. |

### Analysis

| Tool | Purpose |
|---|---|
| `arcads_analyze_media` | Has an AI model watch/read a video, image, audio file, or document and return text about it. Result lands in `data.generatedText`. One call replaces frame extraction plus transcription. Takes about a minute. |

### Media editing

| Tool | Purpose |
|---|---|
| `arcads_stitch_videos` | Concatenate clips (maximum 6 per call). |
| `arcads_trim_video` | Trim a clip. |
| `arcads_extract_scene` | Pull one scene out of a video. |
| `arcads_scene_split` | Split a video into scenes. |
| `arcads_add_subtitles` | Burn subtitles into a video. |
| `arcads_add_text_overlay` | Add a text overlay. |
| `arcads_layer_videos` | Layer/composite videos. |
| `arcads_change_speed_video` | Speed up or slow down a clip. |
| `arcads_extract_frame` | Pull a still frame from a video. |

### Upload and asset registration

| Tool | Purpose |
|---|---|
| `arcads_get_upload_url` | Returns a presigned upload URL plus a `filePath` for a given `mimeType`. Upload your file bytes to the presigned URL with an HTTP PUT, then pass the returned `filePath` (not the URL) into `referenceImages`, `referenceVideos`, `referenceAudios`, `startFrame`, or `endFrame`. |
| `arcads_register_image` / `arcads_register_video` / `arcads_register_audio` | Register a file as a persistent Arcads asset. For long-lived assets only; registered asset IDs are **not** valid as `referenceImages` values (use the upload `filePath` for those). |

Two confirmed gotchas: uploaded temp `filePath`s are **single-use** (consumed by the first tool call that references them, so upload fresh right before the consuming call), and one call with `nbGenerations: N` counts as a single consumer (one upload covers all N variations, while N separate calls would need N fresh uploads).

### Discovery

| Tool | Purpose |
|---|---|
| `arcads_list_products` | List the products configured in the Arcads account. |
| `arcads_get_product` | Fetch one product; `productId` auto-selects when the account has exactly one. |
| `arcads_list_situations` | Catalog of actor situations for `arcads_audio_driven`. |

### Polling and fetching results

| Tool | Purpose |
|---|---|
| `arcads_watch_asset` | Poll a generation job by `assetId`. Returns status **and** a signed `downloadUrl` in one call. This is the tool to poll with. |
| `arcads_get_asset` | Also fetches an asset, but intermittently drops off the server with a `-32602` (tool not found) error. Never build a workflow that blocks on it. |

---

## The batching pattern (`nbGenerations`)

Every generate tool accepts `nbGenerations` (1 to 10): N variations from a **single call**. This is the correct way to produce variations, not N separate calls.

- Ask the user how many variations they want before generating (default 1; keep ad batches modest, around 5).
- Each variation returns its own `assetId`. Poll all of them and present the results as a numbered list.
- One `nbGenerations` call consumes an uploaded reference `filePath` once, so a single upload covers the whole batch.
- Remember that N variations cost roughly N times the credits; fold that into the cost estimate you show the user.

---

## The polling pattern (`arcads_watch_asset`)

Generation is asynchronous. Every generate call returns one or more `assetId`s; poll each with `arcads_watch_asset` until done.

- `status` moves from `pending` to either `generated` or `failed`. While `pending` there is no `downloadUrl`; wait and call again.
- Typical wait times: images roughly 30 seconds to 3 minutes (gpt-image-2 tends toward 1 to 3 minutes); Seedance video around 7 minutes and occasionally up to 15, so poll on a relaxed cadence; text-to-speech about 5 to 10 seconds; media analysis about a minute.
- Text/analysis assets (`arcads_analyze_media`): once generated, read the output from `data.generatedText`.
- On `failed`: do **not** resend the identical prompt. Failures are usually content-moderation or parameter issues; revise the prompt (strip flagged or forbidden words) or fix the enum values first. Note that a content rejection may still charge credits.
- Poll only with `arcads_watch_asset`. If any Arcads tool returns `-32602` (tool not found), refresh your MCP tool catalog (`/reload-mcp`) and retry once.

---

## Model availability

Models available through the Arcads MCP, per the live tool schemas. Exact parameters shift between versions, so refresh the tool schema in your session before relying on specifics.

| Model | Tool | Aspect ratios | Duration | Notes |
|---|---|---|---|---|
| Nano Banana / Nano Banana 2 | `arcads_generate_image_nano_banana` | 1:1, 16:9, 9:16 | n/a | Up to 14 reference images; default image model. |
| gpt-image-2 | `arcads_generate_image_gpt` | 1:1, 16:9, 9:16 only (no 4:5 or 2:3; render 1:1 and crop) | n/a | Up to 5 refs; best text fidelity. For two-column comparison layouts, specify BOTH columns' contents explicitly or the model duplicates one. |
| Seedream / Seedream 5 Lite / Grok Image | `arcads_generate_image` (model enum) | varies | n/a | Alternate image engines. |
| Seedance 2.0 | `arcads_generate_video_seedance_20` | 9:16, 16:9 (no 1:1) | 4 to 15s (integer) | `resolution` 480p/720p/1080p; `audioEnabled` for generated speech/sound; `referenceImages` (max 3) and `referenceVideos` are mutually exclusive; avoid the words `cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect` in prompts (they trigger rejections); prompt sweet spot 100 to 260 words; video-to-video with human faces gets rejected by the content checker. |
| Sora 2 | `arcads_generate_video_sora2` | per tool schema | enum, 4 to 20s | Speech is generated from the prompt text. |
| Veo 3.1 | `arcads_generate_video_veo31` | per tool schema | auto (about 8s) | Use `startFrame` to anchor a person; warns if the spoken script is too long for the clip. |
| Kling 3.0 Pro / 2.6 Pro / 3.0 4K | `arcads_generate_video_kling_30_pro` / `_26_pro` / `_30_4k` | per tool schema | per tool schema | B-roll and motion work. |
| Seedance 1.5, Grok, Happy Horse | `_seedance_15`, `_grok`, `_happy_horse` | per tool schema | per tool schema | Additional engines. |

---

## Credit-cost guidance

Arcads exposes **no billing or pricing endpoint** through the MCP, so costs must be estimated. This pack treats the estimate as a hard gate:

1. Before any generation, build an estimate: prefer actual `creditsCharged` values you have observed from earlier generations with a matching configuration; otherwise ask the user what their plan charges and remember the answer.
2. Present the number **as an estimate**, say where it came from, and add "confirm the exact cost in the Arcads platform".
3. **Wait for explicit confirmation before generating.** No confirmation, no generation. Small QA-fix regenerations after an initial confirmed batch do not need a fresh confirmation, but tell the user they happened.
4. After each generation, note the actual credits charged (visible in the asset's `data.creditsCharged`) so future estimates improve.

One observed datapoint for calibration: a Seedance 2.0 image-to-video clip at 15 seconds / 720p cost roughly **0.9 credits**. Treat that as a ballpark, not a promise.

Per-image credit costs vary by model and plan, so no number is quoted here: when the usage log is empty and the user does not know their rate, run a calibration batch of 1 (generate a single asset with the user's go-ahead, observe the `creditsCharged`, log it) and estimate the full batch from that observed number.

Daily-limit plans report `creditsCharged: 0` with `usedDailyLimit: true`. Still show the user an estimate first; a daily limit is a budget too.

---

## Troubleshooting

**No `arcads_*` tools in your tool list.** The server is not connected or auth failed. Re-check the `config.yaml` entry (`url: "https://mcp.arcads.ai"` exactly), run the connect/login flow again, then `/reload-mcp`. If it still fails, the account's subscription may be inactive or out of credits; have the user log in at app.arcads.ai and check their plan, or create an account at [https://arcads.ai/?via=hermes](https://arcads.ai/?via=hermes).

**Auth worked before but calls now fail.** Sessions and tokens expire. Re-run the login flow for the server and `/reload-mcp`. If your Hermes build cached a token for this server (Hermes stores OAuth tokens under `~/.hermes/mcp-tokens/`), deleting that server's token file forces a completely fresh login.

**A tool that existed earlier returns `-32602` (tool not found).** Known intermittent quirk, seen most often with `arcads_get_asset`. Refresh the MCP tool catalog (`/reload-mcp`) and retry once. Poll with `arcads_watch_asset` instead of `arcads_get_asset` as a standing rule.

**A tool named in this doc or a skill does not exist in your session.** Server versions differ. Use your live tool list as the source of truth and pick the closest equivalent.

**`400 Max 5 reference image(s)`.** You passed more than 5 references to gpt-image-2. Trim the list (Nano Banana takes up to 14 if you need more).

**`422` errors.** Usually an enum or moderation problem: check `aspectRatio` and `duration` against the tool schema, and tighten the prompt.

**Generation status `failed`.** Content moderation or a bad prompt. Never resend the identical prompt; strip flagged and forbidden words (see the Seedance list above) and revise before retrying.

**`File not found` / `REFERENCE_FILE_NOT_FOUND` on a reference file.** The generation tools cannot read the agent's local disk. Use `arcads_get_upload_url`, PUT the file to the presigned URL, and pass the returned `filePath`. Also remember temp `filePath`s are single-use.

**`INVALID_REFERENCE_IMAGES`.** You passed a registered asset ID where the tool wanted an uploaded `filePath`. `referenceImages` takes the `filePath` from `arcads_get_upload_url`, not an `arcads_register_image` result.

**Seedance 500 on audio plus image references.** `audioEnabled: true` combined with `referenceImages` has been intermittently flaky. Fallbacks: drop audio and generate silent image-to-video (add audio downstream with the editing tools), or go text-only.
