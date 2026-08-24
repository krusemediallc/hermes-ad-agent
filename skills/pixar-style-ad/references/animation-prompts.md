# Animate the storyboard: Seedance 2.0 image-to-video prompt formulas

Use this file after every storyboard still is approved. Each still becomes one Seedance 2.0 clip; the voiced clips get assembled into the final ad. Read `style-guide.md` for the story arc and `storyboard-prompts.md` for how the stills were generated.

Tool: `arcads_generate_video_seedance_20`. Check your live tool list; server versions differ, and exact parameter schemas come from the live tool definition.

## Seedance 2.0 platform rules (the parts that matter here)

- **Image input:** pass the approved still's uploaded `filePath` as `referenceImages: [still]`. The first reference image is addressed as `@(img1)` inside the prompt. Max 3 reference images; this pipeline uses exactly 1 per beat.
- **`referenceImages` and `referenceVideos` are mutually exclusive.** This pipeline is pure image-to-video; never pass both.
- **Duration:** integer seconds, 4 to 15 (a 3 second target rounds up to 4). Match the beat target, sized to the VO line at roughly 2.5 words per second plus a small buffer.
- **Aspect ratio:** `"9:16"` (Seedance has no 1:1).
- **Resolution:** `"720p"` default; `"480p"` for cost-sensitive drafts; `"1080p"` if the account supports it.
- **Audio:** `audioEnabled: false`. Voiceover comes from Arcads TTS in post, never from an in-prompt narrator line.
- **Prompt length:** 100 to 260 words, structured Subject + Action + Camera + Style + Constraints, with one primary action per shot and optional `[00:00]`-style timestamps.
- **Forbidden words** (Seedance content checks reject or degrade on these): `cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect`. Substitute "3D animated film aesthetic", "polished", "high fidelity", "ivory white matte material".
- **If a generation comes back `failed`,** never resend the same prompt. Strip flagged or forbidden words, tighten the wording, and retry (max 2 retries per beat). Note: Seedance bills at submission, so a failed content check may still show a charge.
- **Always end the prompt with the no-text constraint.** Seedance sometimes invents captions; every prompt must include "no on-screen text, no subtitles, no captions."

## Universal animation prompt structure

```
[BEAT INTRO]            <- what this clip is
[SUBJECT LOCK]          <- reference the @(img1) character and scene exactly
[ACTION]                <- one primary motion, with degree adverbs and rough timestamps
[CAMERA]                <- framing plus camera movement
[STYLE ANCHOR]          <- "3D animated film aesthetic" plus Pixar tone words
[CONSTRAINTS]           <- consistency plus negatives
```

No dialogue or narrator block: the clips are silent and the VO is overlaid in post. Describing the character mouthing a line is fine and helps rough lip sync, but do not ask Seedance to generate speech audio.

## Beat 1: animate the anthropomorphized problem (HOOK + PROBLEM)

**Target duration:** 4 to 6s (one short line of VO plus a small reaction beat)

```
3D animated film aesthetic, image-to-video animation of the character in @(img1).

Subject: {{PAIN_POINT_CHARACTER}}, fully described, matching the still exactly.

Action (0-2s): The character {{SUBTLE_IDLE_MOTION}}: eyes blink once slowly, the mouth
trembles slightly, the body sags a touch more. (2s to end): The character looks up at
camera and mouths a short complaint, small mouth shapes matching the syllables,
eyebrows rising mid-line, a single tear sliding down at the end.

Camera: Locked extreme close-up macro, slight handheld micro-drift, no zoom or pan.

Style: Disney-Pixar 3D animated feature film aesthetic, soft volumetric lighting,
subsurface scattering, painterly background, shallow depth of field, warm cozy
color grade.

Constraints: The character must remain visually unchanged from @(img1): same
proportions, same eye color, same surface texture. No live-action footage, no
photorealistic transformation, no extra eyes, no morphing limbs, no on-screen text,
no subtitles, no captions.
```

**Worked example (drain hair, 5s):**

```
3D animated film aesthetic, image-to-video animation of the character in @(img1).

Subject: A dark tangled clump of hair sitting in a stainless steel shower drain,
with two oversized Pixar eyes embedded in it, an exhausted half-lidded expression, a
small downturned mouth, soap bubbles around the drain.

Action (0-2s): The hair clump's eyes blink once slowly. Its small mouth quivers,
and the whole clump sags a touch lower over the drain edge. (2-5s): The eyes lift
to look up at the camera. Its mouth opens and moves as if speaking a short line. A
single tear gently slides down the side of the hair clump as the moment finishes,
catching the warm light.

Camera: Locked extreme close-up macro, very subtle handheld micro-drift, no zoom or
pan. Shallow depth of field, drain rim slightly out of focus.

Style: Disney-Pixar 3D animated feature film aesthetic, soft warm ambient lighting
from above the drain, subsurface scattering on the wet hair strands, painterly
soft-focus tile background, slightly desaturated warm color grade.

Constraints: The hair clump must remain visually unchanged from @(img1): same shape,
same eye placement, same drain. No live-action footage, no photorealistic hair, no
extra eyes, no morphing limbs, no on-screen text, no subtitles, no captions.
```

## Beat 2: animate the protagonist reveal (PRODUCT)

**Target duration:** 6 to 8s (one or two short VO lines plus the product hold gesture)

```
3D animated film aesthetic, image-to-video animation of the protagonist in @(img1).

Subject: {{PROTAGONIST_DESCRIPTION exactly as in the still}} holding {{PRODUCT
exactly as in the still}}.

Action (0-2s): She looks down at the product in her hands with delighted curiosity,
lips parting slightly. (2s to midpoint): She slowly raises her eyes from the product
up to the camera, lips curving into a gentle smile, eyebrows lifting in surprise.
(midpoint to end): She tilts her head slightly, leans the product a touch closer to
camera, and mouths a short line with natural lip movement, small head nods on the
emphasized words.

Camera: Locked medium head-and-shoulders, vertical 9:16, very subtle handheld
breathing motion. No dolly, no pan.

Style: Disney-Pixar 3D animated feature film aesthetic, soft golden-hour window
light wrapping camera-left to camera-right, painterly soft-focus interior
background, shallow depth of field, warm cozy palette of cream, butter yellow, and
dusty pink.

Constraints: The protagonist must remain visually unchanged from @(img1): same hair,
same eye color, same outfit, same freckles. The product label must remain visually
unchanged. No live-action, no photorealistic face, no extra fingers, no morphing
features, no on-screen text, no subtitles, no captions.
```

## Beat 3: animate the mascot mechanism scene (PAYOFF)

**Target duration:** 8 to 12s (the mascots do the work; VO narrates over it)

```
3D animated film aesthetic, image-to-video animation of the scene in @(img1).

Subject: A stylized cross-section of {{INTERIOR_STRUCTURE}} populated by {{N}} small
chibi ivory-white mascot characters with tiny black-dot eyes, soft pink cheeks, and
simple rounded limbs. {{ENERGY_VISUAL}} traces through the structure.

Action (0-3s): The mascots begin {{PRIMARY_MECHANISM}} in coordinated motion; each
mascot pulls, smooths, weaves, or stitches in the same rhythm. (3s to midpoint): The
{{ENERGY_VISUAL}} brightens and pulses outward from their work, lighting up the
surrounding {{STRUCTURE_DETAIL}}. (midpoint to end): The mascots pause, look around
at their finished section, give each other tiny celebratory glances, and the entire
structure now glows softly and evenly.

Camera: Slow gentle dolly-in toward the center of the action, 9:16 vertical framing,
focus held on the mascots throughout.

Style: Disney-Pixar 3D animated feature film aesthetic, soft warm interior glow,
painterly ivory-and-gold palette, subsurface scattering on the mascot bodies,
shallow depth of field with creamy bokeh.

Constraints: The mascots must remain visually consistent throughout: same ivory
color, same proportions, same eye style. The structure cross-section must remain
unchanged in geometry. No live-action, no photorealistic anatomy, no horror-style
organs, no extra mascot limbs, no morphing, no on-screen text, no subtitles, no
captions.
```

## Beat 4: animate the CTA

**Target duration:** 4 to 6s (final smile plus product hold)

```
3D animated film aesthetic, image-to-video animation of the protagonist in @(img1).

Subject: {{PROTAGONIST_DESCRIPTION exactly as in Beat 2}} now facing the camera
directly, holding {{ONE_OR_TWO_PRODUCT_PACKAGES}} at chest height with the labels
toward camera.

Action (0-2s): She gives a warm confident smile, eyes brightening, a small happy
head tilt. (2s to end): She raises the packages a touch closer to the camera, the
labels rotating slightly so they read cleanly. Her smile widens into a small
satisfied grin at the very end.

Camera: Locked medium shot, vertical 9:16, gentle handheld breathing motion. No
dolly or zoom.

Style: Disney-Pixar 3D animated feature film aesthetic, soft golden-hour window
light from camera-left, painterly soft-focus background, warm cozy color palette.

Constraints: The protagonist must remain visually identical to Beat 2: same hair,
same eye color, same outfit, same freckles, same skin tone. The product label must
remain visually identical to the still. The lower third of the frame must remain
visually clean for a post-production caption overlay. No live-action, no
photorealistic face, no extra fingers, no morphing, no on-screen text, no
subtitles, no captions.
```

## Cross-clip continuity rules

1. **Each clip's reference image is the approved still for that beat.** Do not chain by feeding a frame from a prior animation as the next beat's anchor; animated frames drift.
2. **Lift the protagonist description verbatim** from the cast sheet into Beats 2 and 4. Do not paraphrase.
3. **Keep the style block consistent** across all beats: "3D animated film aesthetic" everywhere, never Seedance's forbidden words.
4. **Fire beats in parallel** once all stills are approved, then poll every asset id with `arcads_watch_asset` at a relaxed cadence (a clip typically takes around 7 minutes, occasionally up to 15).
5. **Log each call** (model, duration, resolution, aspect ratio, reference count, asset id, and `creditsCharged` when known) to the run's `log.jsonl`.

## Per-clip QA

Watch each finished clip end to end (or have the user do it) and check:

- [ ] Character identity holds from the input still to the last frame
- [ ] No finger or limb morphing; count fingers on every visible hand throughout
- [ ] No product-label drift; the label text and colors stay legible and identical
- [ ] Mouth movement is plausible where the character "speaks" (rough match is fine; frame-exact lip sync is not Seedance's strength)
- [ ] No burned-in text or subtitles appeared
- [ ] The motion follows the prompt: the primary action happens and nothing random intrudes

If any check fails, regenerate that beat with a tightened constraint block (for example "the protagonist's hands have exactly five fingers each, no morphing"). Max 2 retries per beat, then stop and ask the user.

## After animation

Assembly (trim each clip to its VO, mux, concatenate) and captioning are covered in the Workflow section of `SKILL.md`, including what to do when no local ffmpeg is available.
