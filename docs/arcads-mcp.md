# Arcads MCP Server Reference

This is the repo-level reference for the **Arcads MCP server**, the creative-generation backend for every image and video skill in this pack. It covers what the server is, how to connect it to a Hermes agent, the tool roster, the two core usage patterns (batching and polling), model availability, the credit-cost contract, and troubleshooting.

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

Hermes configures MCP servers in its config file under `mcp_servers`. Never assume `~/.hermes`: find the file with `hermes config path` (on a Hostinger managed app it lived under `$HERMES_HOME`, which was `/data`), and find the executable with `command -v hermes`, falling back to `/opt/venv/bin/hermes` when `hermes` is not on the agent shell's PATH. Prefer `hermes mcp add` / `hermes mcp configure` and `hermes config check` over hand-editing YAML: a malformed edit can disable the gateway, and edits race an in-progress OAuth login. Verify the exact flags with `--help`; they differ between Hermes versions.

Arcads' server advertises OAuth metadata and dynamic client registration; both worked on the observed deployment. The connect flow is surface-aware, so pick the route that matches where you are:

1. Add the server entry (the config should look like this after `hermes mcp add`; `trust: untrusted` keeps tool output from being treated as instructions):

   ```yaml
   mcp_servers:
     arcads:
       url: "https://mcp.arcads.ai"
       auth: oauth
       trust: untrusted
       enabled: true
   ```

2. Run the OAuth login through the right surface:

   - **Preferred: the Hermes dashboard or Hermes Desktop OAuth relay.** On a headless or managed gateway (Hostinger), the browser cannot reach a callback port inside the container, and the relay handles that for you. Use the dashboard's MCP page or Desktop's connect button if your build offers one.
   - **Otherwise: exactly ONE fresh terminal flow.** Run `hermes mcp login arcads` once, in one terminal, and complete the single authorization URL it prints.
   - **Stop condition.** If you see two authorization URLs, or the message `OAuth callback port <port> is already in use` (`Address already in use`), two login flows have collided. Stop. Do not retry old URLs and do not start another `hermes mcp login` on top; kill the stray login process, then follow the Hermes remote OAuth guide for headless hosts: https://hermes-agent.nousresearch.com/docs/guides/oauth-over-ssh . Observed once on a managed gateway, where a single login command emitted two flows and self-collided.

3. Hot-reload MCP servers with `/reload-mcp` in chat (or restart the session). Tool-schema changes only appear in a fresh agent session.

4. Verify in layers, because `hermes mcp list` shows `enabled` for a failing server (that is config state, not health) and `hermes mcp test` has printed `Connection failed` while exiting 0 (parse the text, not the exit code): configured, enabled, connected (`tools/list` returns), agent-usable (a fresh normal agent session can see and call the registered tool), and verified (a native read-only call returned data). A cheap read-only smoke test is `arcads_list_products` or `arcads_list_voices`. Do not run a generation tool as a test; generation costs credits.

Expect a browser sign-in to app.arcads.ai during the flow; the connection is tied to that account and its subscription. If the documented connection method fails, check the Arcads Help Center article "Arcads MCP" or contact Arcads support.

### Registered tool names

The `arcads_*` names in this document and in the skills are the server-native tool IDs the provider advertises. The Hermes runtime registers each one under a prefixed callable name; the observed shape was `mcp__arcads__arcads_list_products`. An agent must discover the registered name (tool_search or its live tool list) and call that. Tool counts drift between days (80 then 82 on consecutive days), so readiness is capability-based (the tools a skill needs are registered), never count-based.

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
| `arcads_analyze_media` | Has an AI model watch/read a video, image, audio file, or document and return text about it. Result lands in `data.generatedText`. One call replaces frame extraction plus transcription. Takes about a minute. Needs an uploaded or remote path: a local path returned `REFERENCE_FILE_NOT_FOUND` on the hosted deployment, so upload via `arcads_get_upload_url` first. Credit-accounted: it returned `creditsCharged: 0` under a daily limit on one account, which is still a metered operation, never "free". |

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
| `arcads_watch_asset` | Poll a generation job by `assetId`. Returns status, `creditsCharged`, **and** a signed `downloadUrl` in one call. This is the tool to poll with. The signed URL is a temporary credential: pass it between tools as an opaque value, never into a terminal argument, a log, or a durable file. |
| `arcads_get_asset` | Also fetches an asset, but intermittently drops off the server with a `-32602` (tool not found) error. Never build a workflow that blocks on it. |

---

## The batching pattern (`nbGenerations`)

Every generate tool accepts `nbGenerations` (1 to 10): N variations from a **single call**. This is the correct way to produce variations, not N separate calls.

- Ask the user how many variations they want before generating (default 1; keep ad batches modest, around 5).
- Each variation returns its own `assetId`. Poll all of them and present the results as a numbered list.
- One `nbGenerations` call consumes an uploaded reference `filePath` once, so a single upload covers the whole batch.
- Remember that N variations cost roughly N times the credits; fold that into the cost estimate you show the user, and read back each variation's own `creditsCharged` afterwards.

---

## The polling pattern (`arcads_watch_asset`)

Generation is asynchronous. Every generate call returns one or more `assetId`s; poll each with `arcads_watch_asset` until done.

- `status` moves from `pending` to either `generated` or `failed`. While `pending` there is no `downloadUrl`; wait and call again.
- Typical wait times: images roughly 30 seconds to 3 minutes (gpt-image-2 tends toward 1 to 3 minutes); Seedance video around 7 minutes and occasionally up to 15, so poll on a relaxed cadence; text-to-speech about 5 to 10 seconds; media analysis about a minute.
- Text/analysis assets (`arcads_analyze_media`): once generated, read the output from `data.generatedText`.
- On `failed`: do **not** resend the identical prompt. Failures are usually content-moderation or parameter issues; revise the prompt (strip flagged or forbidden words) or fix the enum values first. A content rejection may still charge credits, and the corrected retry is a new credit-accounted operation that needs its own allowance (see the credit contract below).
- Poll only with `arcads_watch_asset`. If any Arcads tool returns `-32602` (tool not found), refresh your MCP tool catalog (`/reload-mcp`), re-discover the registered name, and re-issue the read call. Never re-issue a generate call on a transport error without reading back first; ambiguity means read back, not re-create.
- Download promptly from the signed `downloadUrl` (it expires) into `outputs/<skill>/<slug>/` at the workspace root, and keep the URL opaque.

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

## Credit-cost contract

Arcads exposes **no billing, pricing, or quote endpoint** through the MCP. This pack treats cost as a hard gate built on one contract:

**`creditsCharged` is the only cost figure.** Read it back from the asset after the call (`arcads_watch_asset` returns it; it also appears as `data.creditsCharged`). Nothing else is cost. Assets also carry an `mp` field; that is megapixel or usage metadata, **never credits**. An earlier version of this doc quoted "about 0.9 credits" for a Seedance clip because it read `mp`; the real charge on that kind of clip was hundreds of times higher. One account-specific historical observation, not a rate and not an estimate: a 12-second 720p Seedance 2.0 video charged `creditsCharged: 432` on one account in early September 2026 while its `mp` field read 0.9216. No other fixed figures are quoted here; anything a skill file once listed (per-line TTS, per-pass subtitles, per-clip Seedance numbers) was an account-specific observation and is not an estimate.

The gate, in order:

1. **Ask the user's plan rate first** for the model, duration, and resolution in question. Record the answer in the usage log.
2. **Otherwise use the usage log** (`outputs/arcads-usage-log.jsonl` at the workspace root): a recorded `creditsCharged` from a matching configuration.
3. **Otherwise the first paid generation is an explicit unknown-cost calibration.** The approval must state a user-defined maximum acceptable credit exposure for that single operation. Generate exactly one unit, read back `creditsCharged`, log it, then re-gate the rest against the observed number.
4. **Present every figure as an estimate**, say where it came from, name any follow-up allowance (retries, regenerations) with a count and a per-operation cost, add "confirm the exact cost in the Arcads platform", and **wait for explicit confirmation before generating**. No confirmation, no generation.
5. **No automatic paid or credit-accounted operations.** Retries, regenerations, QA-fix regenerations, transcription, analysis (`arcads_analyze_media`), subtitles, enhancement, stitching, trimming, and editing are all credit-accounted, including when they return `creditsCharged: 0` under a daily limit. They run only when the approval named them with a count-and-cost allowance; otherwise ask again before each one.
6. **Log every operation** with tool, model, duration, resolution, count, date, asset ids, final status, `creditsCharged` exactly as returned, and the daily-limit indicator (`usedDailyLimit`). Report actual `creditsCharged` per operation and daily-limit use to the user. Never log or print signed URLs.

Daily-limit plans report `creditsCharged: 0` with `usedDailyLimit: true`. That is a daily-limit use, not "free": still show the user an estimate first and still count the operation.

Seedance bills at submission, so a charge can appear while the asset is still pending, and a content-check failure can still charge.

### Video QA is several states, not one

For video assets, report each state separately and never collapse them into "QA passed": metadata-pass (duration, resolution, aspect, audio track match the plan), sampled-frames-pass, transcript-pass (transcription through Arcads is itself credit-accounted), motion/lip-sync review required (only watching the clip end to end clears it), claims/branding check, and human approval.

---

## Troubleshooting

**No `arcads_*` tools in your tool list.** The server is not connected, auth failed, or you are looking for the bare name instead of the registered one (`mcp__arcads__...`). Re-check the config entry (`url: "https://mcp.arcads.ai"` exactly, via `hermes mcp list` and `hermes config check`), run the connect/login flow again through the right surface (see Connecting), then `/reload-mcp` and open a fresh agent session. If it still fails, the account's subscription may be inactive or out of credits; have the user log in at app.arcads.ai and check their plan, or create an account at [https://arcads.ai/?via=hermes](https://arcads.ai/?via=hermes).

**`hermes mcp list` says enabled but calls fail.** `enabled` is config state, not health, and `hermes mcp test` can print `Connection failed` while exiting 0. Read the test output text and verify the layers separately (configured, enabled, connected, agent-usable, verified).

**Two authorization URLs or `OAuth callback port ... already in use` during login.** Two login flows collided. Stop, do not retry old URLs, end the stray login process, and use the dashboard/Desktop relay or the remote OAuth guide: https://hermes-agent.nousresearch.com/docs/guides/oauth-over-ssh .

**Auth worked before but calls now fail.** Sessions and tokens expire. Re-run the login flow for the server (one fresh flow) and `/reload-mcp`. Hermes stores OAuth tokens under the `mcp-tokens` directory inside `$HERMES_HOME` (find it with `hermes config path`; never assume `~/.hermes`); deleting that server's token file forces a completely fresh login.

**A tool that existed earlier returns `-32602` (tool not found).** Known intermittent quirk, seen most often with `arcads_get_asset`. Refresh the MCP tool catalog (`/reload-mcp`), re-discover the registered name, and re-issue the read call. Poll with `arcads_watch_asset` instead of `arcads_get_asset` as a standing rule.

**A tool named in this doc or a skill does not exist in your session.** Server versions differ and tool counts drift. Use your live tool list as the source of truth and pick the closest equivalent.

**`400 Max 5 reference image(s)`.** You passed more than 5 references to gpt-image-2. Trim the list (Nano Banana takes up to 14 if you need more).

**`422` errors.** Usually an enum or moderation problem: check `aspectRatio` and `duration` against the tool schema, and tighten the prompt.

**Generation status `failed`.** Content moderation or a bad prompt. Never resend the identical prompt; strip flagged and forbidden words (see the Seedance list above) and revise before retrying.

**`File not found` / `REFERENCE_FILE_NOT_FOUND` on a reference file.** The generation and analysis tools (including `arcads_analyze_media` for transcription) cannot read the agent's local disk on the hosted deployment. Use `arcads_get_upload_url`, PUT the file to the presigned URL (treat that URL as a temporary credential: read it from a variable, do not paste it into a saved command), and pass the returned `filePath`. Also remember temp `filePath`s are single-use.

**`INVALID_REFERENCE_IMAGES`.** You passed a registered asset ID where the tool wanted an uploaded `filePath`. `referenceImages` takes the `filePath` from `arcads_get_upload_url`, not an `arcads_register_image` result.

**Seedance 500 on audio plus image references.** `audioEnabled: true` combined with `referenceImages` has been intermittently flaky. Report it; a re-issue is a new credit-accounted operation that needs the approval's retry allowance or a fresh yes. Fallbacks, each gated the same way: drop audio and generate silent image-to-video (add audio downstream with the editing tools), or go text-only.
