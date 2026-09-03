# Claymation animation: Seedance 2.0 image-to-video prompt formulas

Use this file after every storyboard still is approved. Each still becomes one Seedance 2.0 clip; the voiced clips get assembled into the final ad. Read `style-guide.md` for the 8-beat arc and `storyboard-prompts.md` for how the stills were generated.

Tool: `arcads_generate_video_seedance_20`. Check your live tool list; server versions differ, and exact parameter schemas come from the live tool definition.

The worked fragments below continue the neutral fictional example from the storyboard file: the "Everbloom" renewal cream and the characters Diane and Margaret. Swap in the user's real cast sheet.

## Seedance 2.0 platform rules (what matters for claymation)

- **Image input:** pass the approved still's uploaded `filePath` as `referenceImages: [still]`. The first reference image is addressed as `@(img1)` inside the prompt. Max 3 reference images; this pipeline uses exactly 1 per beat.
- **`referenceImages` and `referenceVideos` are mutually exclusive.** This pipeline is pure image-to-video; never pass both.
- **Duration:** integer seconds, 4 to 15. Match each beat target from the style guide, sized to the narrator line at roughly 2.5 words per second plus a small buffer.
- **Aspect ratio:** `"9:16"` (Seedance has no 1:1).
- **Resolution:** `"720p"` default; `"480p"` for cost-sensitive drafts; `"1080p"` if the account supports it.
- **Audio:** `audioEnabled: false`. All voiceover comes from Arcads TTS in post; never put a narrator line in the prompt. In-prompt narration produces inconsistent voice quality across beats and locks pacing to the video model.
- **Prompt length:** 100 to 260 words, structured Subject + Action + Camera + Style + Constraints, one primary action per shot.
- **Forbidden words** (Seedance content checks reject or degrade on these): `cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect`. Substitute "stop-motion claymation film aesthetic", "polished hand-sculpted", "high fidelity", "evenly hand-painted".
- **If a generation comes back `failed`,** never resend the same prompt. Strip flagged or forbidden words and tighten the wording. The corrected retry is a new credit-accounted generation: run it only inside the retry allowance the batch approval named (never more than 2 per beat), otherwise ask first. Seedance bills at submission, so a failed content check may still show a charge; report its actual `creditsCharged`.
- **Always end the prompt with the no-text constraint.** Seedance sometimes invents captions; every prompt must include "no on-screen text, no subtitles, no captions."
- **Critical for this style:** the motion must read as smooth animation that preserves the claymation aesthetic of the still. Do NOT ask for stop-motion judder in the prompt; the model cannot control framerate and the request breaks the look. Judder, if wanted, is a post step (see `SKILL.md`).

## Universal animation prompt structure

```
[BEAT INTRO]            <- what this clip is
[SUBJECT LOCK]          <- reference the @(img1) character and scene exactly
[ACTION]                <- one primary motion plus small secondary motions, with degree adverbs
[CAMERA]                <- framing plus small camera motion (usually locked or breathing)
[STYLE ANCHOR]          <- "stop-motion claymation film aesthetic" plus Aardman tone words
[AMBIENT]               <- room tone and SFX description only; NO narrator or dialogue lines
[CONSTRAINTS]           <- consistency plus negatives, claymation-specific
```

The AMBIENT block describes the sound world of the scene even though `audioEnabled` is false; it helps the model stage physical actions (a pour, a clink) convincingly. Never put spoken lines in it.

## Reusable subject lock fragments

Build these once from the cast sheet, then lift them verbatim into the SUBJECT LOCK block of every relevant beat. Same phrasing every time.

```
DIANE (protagonist):
"Diane, a woman in her late 50s with shoulder-length terracotta-brown wavy
plasticine hair sculpted in distinct ribbon-strands, matte clay skin with
visible thumbprint impressions and deep sculpted laugh lines, warm brown
matte clay eyes set into deep sockets, a sculpted brow furrow. She wears a
cream chunky knit cardigan with visible wool weave over a rust-red blouse,
dark wool trousers, brown leather slippers."

MARGARET (supporting):
"Margaret, a woman in her 60s with silver curly plasticine hair with carved
strand grooves, round wire glasses, a sage-green cable-knit sweater with
visible wool weave, matte clay skin."

PRIMARY SETTING (Diane's kitchen):
"A sunlit miniature claymation kitchen: green-painted wooden cabinets, a
red gingham tablecloth, hand-thrown ceramic cups, a copper kettle on a small
stove, potted herbs on the windowsill, warm tungsten light from a window
on camera-left."
```

## Beat 1: animate the setup (HOOK)

**Target duration:** 8 to 10s (narrator intro plus light idle motion)

```
Stop-motion claymation film aesthetic, image-to-video animation of the
scene in @(img1).

Subject: {{PROTAGONIST_FRAGMENT}} in {{PRIMARY_SETTING_FRAGMENT}}.

Action (0-3s): She slowly pours tea from the ceramic kettle into the wide
cup, the stream of tea moving naturally. (3s to midpoint): She gently sets
the kettle down on the counter, her sculpted hand turning slightly.
(midpoint to end): She tilts her head a touch toward the window, expression
calm and unhurried, sculpted eyelids blinking once slowly. Subtle
micro-motion in the steam rising from the cup.

Camera: Locked medium-wide shot, very subtle handheld macro breathing
motion (the miniature-set feel). No zoom or pan.

Style: Stop-motion claymation film aesthetic, Aardman-style hand-sculpted
plasticine characters, matte clay surfaces, real knit-fabric clothing, warm
tungsten interior lighting, shallow macro depth of field with soft
photographic bokeh.

Ambient: faint kettle pour, soft kitchen room tone, distant birdsong outside.

Constraints: The protagonist must remain visually unchanged from @(img1):
same plasticine hair ribbon-strands, same matte clay skin with thumbprint
impressions, same cream knit cardigan with wool weave, same eye sockets.
The kitchen set must remain visually unchanged. No live-action, no
photorealistic transformation, no Pixar smoothing, no 3D ray-traced
materials, no extra fingers, no morphing, no on-screen text, no subtitles,
no captions.
```

## Beat 2: animate the inciting moment (HOOK)

**Target duration:** 6 to 8s (close-up reaction)

```
Stop-motion claymation film aesthetic, image-to-video animation of the
character in @(img1).

Subject: {{PROTAGONIST_FRAGMENT}} in tight close-up at the bathroom mirror.

Action (0-2s): Her sculpted clay fingertip lifts toward her upper lip and
gently touches the area where the small carved lines are visible. Her eyes
follow her own fingertip in the mirror. (2s to end): Her sculpted brow
furrows a touch more, her mouth slightly opens in quiet alarm. A single
slow sculpted blink. She holds the moment, very still.

Camera: Locked tight close-up, very subtle handheld micro-drift, no zoom
or pan. Shallow macro depth of field.

Style: Stop-motion claymation film aesthetic, hand-sculpted plasticine,
matte clay surfaces, soft directional tungsten light from camera-right.

Ambient: very soft bathroom room tone, faint plumbing hum.

Constraints: The protagonist must remain visually unchanged from @(img1):
same plasticine hair strands, same matte clay skin with thumbprint
impressions, same sculpted eye sockets with a single matte highlight. The
sculpted lip lines must remain in the same position. No live-action, no
photorealistic skin smoothing, no Pixar wet-eye sheen, no morphing, no
on-screen text, no subtitles, no captions.
```

## Beat 3: animate the two-character scene (PROBLEM)

**Target duration:** 8 to 10s (one character mouths a short line, the other reacts)

```
Stop-motion claymation film aesthetic, image-to-video animation of the
two-shot in @(img1).

Subject: {{PROTAGONIST_FRAGMENT}} on the right and {{SUPPORTING_CHARACTER_FRAGMENT}}
on the left, both seated at a wooden cafe table holding hand-thrown ceramic
teacups.

Action (0-3s): Margaret tilts her head a touch, her sculpted clay mouth
opening and moving as if speaking a short remark, her painted lips forming
clear shapes (a rough match is fine), her sculpted eyebrows rising on the
emphasized words. (3s to midpoint): Diane's sculpted eyes glance down at
her teacup, expression softly self-conscious, her mouth closing.
(midpoint to end): Diane lifts her teacup partway to her mouth, hesitates,
then sets it back down. Slight steam rises from both cups throughout.

Camera: Locked medium two-shot, very subtle handheld breathing motion. No
zoom or pan.

Style: Stop-motion claymation film aesthetic, Aardman-style hand-sculpted
plasticine, matte clay surfaces, real knit-fabric clothing, warm tungsten
overhead light, shallow macro depth of field, soft cafe-bokeh background.

Ambient: soft cafe room tone, faint clink of cup against saucer, distant
muffled conversation.

Constraints: Both characters must remain visually unchanged from @(img1):
same plasticine hair colors and carved strand grooves, same matte clay
skin, same knit garments with visible wool weave, same eye sockets. The
cafe set must remain unchanged. No live-action, no photorealistic skin
smoothing, no Pixar wet-eye sheen, no extra fingers on the teacups, no
morphing, no on-screen text, no subtitles, no captions.
```

## Beat 4: animate the quiet despair (PROBLEM)

**Target duration:** 5 to 7s (slow, sparse motion; the narrator carries it)

```
Stop-motion claymation film aesthetic, image-to-video animation of the
scene in @(img1).

Subject: {{PROTAGONIST_FRAGMENT}} standing alone in her dimly lit living
room in front of a full-length wood-framed standing mirror.

Action (0-2s): She slowly lifts her sculpted clay hand to her cheek,
fingers resting lightly against the skin. (2s to midpoint): Her sculpted
eyes lower a fraction, expression subdued. A very slow sculpted blink.
(midpoint to end): She lets her hand fall slowly back to her side, her gaze
still on her own reflection. The mirror reflection mirrors her motion
exactly.

Camera: Locked medium-wide shot, very subtle handheld macro breathing
motion. No zoom or pan.

Style: Stop-motion claymation film aesthetic, hand-sculpted plasticine,
matte clay, soft dim tungsten light from a single side lamp casting long
sculpted shadows.

Ambient: very soft room tone, the faintest distant clock tick.

Constraints: The protagonist must remain visually unchanged from @(img1):
same plasticine hair strands, same matte clay skin with thumbprint
impressions, same cream knit cardigan with wool weave. The dim living room
set must remain unchanged. The mirror reflection must match the
protagonist's pose accurately throughout. No live-action, no photorealistic
smoothing, no Pixar sheen, no morphing, no on-screen text, no subtitles,
no captions.
```

## Beat 5: animate the clay infographic (PRODUCT mechanism)

**Target duration:** 8 to 10s (a chart reveal with one small animated indicator)

```
Stop-motion claymation film aesthetic, image-to-video animation of the
hand-sculpted chart in @(img1).

Subject: A line graph sculpted entirely from clay and plasticine on a
hand-carved wooden frame, mounted on a cream-painted clay wall, exactly as
in the still, including its sculpted title lettering and axis labels.

Action (0-2s): The chart sits still, soft tungsten light gently shifting
across its surface as if a curtain moved nearby. (2s to midpoint): A small
sculpted clay arrow indicator slowly traces along the line graph from left
to right, moving in measured even motion, drawing the eye to the drop.
(midpoint to end): The arrow comes to rest at the bottom-right end of the
line, and the small label tag visibly settles into place with a final
gentle motion.

Camera: Locked head-on shot, very subtle handheld macro breathing motion,
plus a slight slow zoom-in of about five percent over the full duration
toward the drop in the line.

Style: Stop-motion claymation film aesthetic, hand-sculpted plasticine
letters and graph elements, a hand-carved wooden frame, a matte
cream-painted clay wall background, soft tungsten light from camera-left.

Ambient: a quiet low room hum, the stillness of a research beat.

Constraints: The chart and frame must remain visually unchanged from
@(img1): same chunky sculpted letters with slight asymmetry, same
plasticine line ribbon, same hand-carved frame. No live-action, no
digital text overlay, no smooth animated graphics, no Pixar render, no
morphing, no extra labels, no on-screen text beyond what is already
sculpted into the still, no subtitles, no captions.
```

## Beat 6: animate the discovery (PRODUCT)

**Target duration:** 6 to 8s (the hand reaches and picks up the product)

```
Stop-motion claymation film aesthetic, image-to-video animation of the
scene in @(img1).

Subject: A small dusty-lavender jar labeled "{{PRODUCT_LABEL}}" in
hand-painted cream lettering, rendered as a clay prop, sitting on a wooden
kitchen table. {{PROTAGONIST_FRAGMENT}}'s sculpted clay hand enters frame
from camera-right.

Action (0-2s): Her sculpted fingers move slowly toward the jar, hovering
briefly above it. (2s to midpoint): Her hand gently picks up the jar,
sculpted fingers curling around it as it lifts from the table.
(midpoint to end): She slowly rotates the jar in her hand, the hand-painted
label turning to face the camera more cleanly, the light catching the matte
paint.

Camera: Locked medium shot, very subtle handheld macro breathing motion,
plus a slight slow dolly-in of about three percent over the duration toward
the jar.

Style: Stop-motion claymation film aesthetic, a hand-sculpted plasticine
hand, a matte clay-painted jar prop, a wooden table with visible grain,
warm tungsten light from a window on camera-left catching the label.

Ambient: soft kitchen room tone, a faint kettle whistle in the distance.

Constraints: The product jar must remain visually unchanged from @(img1):
same paint with subtle brush texture, same hand-painted label text legible
and readable, same matte finish. The protagonist's hand must remain
visually unchanged: same matte clay texture, sculpted knuckle creases,
slight asymmetry. No live-action, no photorealistic product render, no
smooth digital plastic look, no warped or shifting label text, no extra
fingers, no morphing, no on-screen text, no subtitles, no captions.
```

## Beat 7: animate the transformation (PAYOFF)

**Target duration:** 10 to 12s (apply the product plus a subtle reveal)

```
Stop-motion claymation film aesthetic, image-to-video animation of the
scene in @(img1).

Subject: {{PROTAGONIST_FRAGMENT}} in her bathroom, the mirror visible
behind her, holding the "{{PRODUCT_LABEL}}" jar.

Action (0-3s): She opens the jar and takes a small amount of cream onto
her sculpted clay fingertip, slow deliberate motion. (3s to midpoint): She
gently applies the cream to her upper lip with measured strokes, her
sculpted eyes watching her own reflection in the mirror. (midpoint to end):
She lowers her hand and looks at her reflection, her expression slowly
warming into a small pleased smile. The carved lines above her lip appear
subtly softer than at the start of the clip, while everything else about
her identity remains exactly the same.

Camera: Locked medium close-up, very subtle handheld macro breathing
motion, plus a slight slow dolly-in of about three percent on her face for
the final moment.

Style: Stop-motion claymation film aesthetic, hand-sculpted plasticine,
matte clay surfaces, warm tungsten light slightly brighter and warmer than
the earlier beats to signal positive change.

Ambient: soft bathroom room tone, the gentle sound of a small lid turning.

Constraints: The protagonist must remain visually unchanged from @(img1):
same terracotta plasticine hair with carved strand grooves, same matte
clay skin with thumbprint impressions across the cheeks and forehead, same
cream knit cardigan with visible wool weave, same sculpted eye sockets.
The jar prop must remain visually identical to Beat 6. Only the specific
upper-lip area may appear subtly smoother by the end; no other part of the
face changes. No live-action, no photorealistic skin smoothing across the
whole face, no Pixar render, no morphing, no on-screen text, no subtitles,
no captions.
```

## Beat 8: animate the resolution + CTA

**Target duration:** 6 to 8s (smile, product hold, hold for the caption)

```
Stop-motion claymation film aesthetic, image-to-video animation of the
character in @(img1).

Subject: {{PROTAGONIST_FRAGMENT}} in {{PRIMARY_SETTING_FRAGMENT}}, holding
the "{{PRODUCT_LABEL}}" jar at chest height, facing camera.

Action (0-2s): She gives a small warm gentle smile, her sculpted laugh
lines working with the smile. Her sculpted eyes meet the camera and
brighten softly. (2s to midpoint): She raises the jar a touch closer to
camera, her hand turning slightly so the hand-painted label reads cleanly.
(midpoint to end): Her smile widens into a small satisfied grin. She holds
the pose, still and warm, ready for a caption to land on the lower third
of the frame.

Camera: Locked medium shot, very subtle handheld macro breathing motion.
No zoom or pan.

Style: Stop-motion claymation film aesthetic, Aardman-style hand-sculpted
plasticine, matte clay surfaces, a real knit-fabric cardigan, warm tungsten
light from camera-left with a soft rim from camera-right catching her hair.

Ambient: warm kitchen room tone, faint birdsong outside.

Constraints: The protagonist must remain visually identical to Beat 7:
same plasticine hair, same matte clay skin, same cream knit cardigan with
wool weave, same eye sockets. The jar prop must remain visually identical
to Beats 6 and 7. The lower third of the frame must remain visually clean
and uncluttered for a post-production caption overlay. No live-action, no
photorealistic smoothing, no Pixar sheen, no morphing, no extra fingers,
no on-screen text, no subtitles, no captions.
```

## Cross-clip continuity rules

1. **Each clip's reference image is the approved still for that beat.** Do not chain by feeding an animated end-frame as the next beat's anchor; drift compounds.
2. **Lift the SUBJECT LOCK fragments verbatim** into every beat. Do not paraphrase the protagonist description.
3. **Keep the style block consistent** across all beats: "stop-motion claymation film aesthetic" everywhere, never `cinematic`, never `Pixar`, never `3D rendered`.
4. **Fire all beats in parallel** once their stills are approved, then poll every asset id with `arcads_watch_asset` at a relaxed cadence (a clip typically takes around 7 minutes, occasionally up to 15).
5. **Log each call** (tool, model, beat, duration, resolution, aspect ratio, reference count, count, date, asset id, final status, `creditsCharged` exactly as returned, and the daily-limit indicator) to the shared usage log `outputs/arcads-usage-log.jsonl` at the workspace root. Only `creditsCharged` is cost; the `mp` field is megapixel or usage metadata, never credits. Never log the signed download URL.

## Per-clip QA (claymation-specific)

Watch each finished clip end to end (or have the user do it) and verify:

- [ ] Clay texture preserved end to end; the smoothing tendency of video models is the number one risk, and fingerprint impressions plus tool marks should stay visible in close-ups
- [ ] Knit fabric stays woven wool, not painted-on stripes
- [ ] Eyes stay matte; no wet-eye sheen developing mid-clip
- [ ] Character identity holds from the input still to the last frame: same face proportions, same hair color and strand grooves, same outfit
- [ ] Product label paint keeps its hand-applied look; no digital crispness leaking in
- [ ] The Beat 7 improvement stays localized (one specific area, not the whole face)
- [ ] No burned-in text or subtitles appeared
- [ ] Mirror reflections move correctly on Beats 2, 4, and 7
- [ ] The Beat 3 mouth movement is plausible (a rough match is fine for Seedance)

Report the QA states separately, never as one "QA passed": metadata-pass (duration, resolution, aspect, silent), sampled-frames-pass (the texture, fabric, eye, and label checks above on sampled frames), transcript-pass (voiced master only; Arcads transcription is credit-accounted and needs an allowance), motion/lip-sync review required (texture drift over time, mirror behavior, and Beat 3 mouth plausibility need the clip watched end to end; frames never clear it), claims/branding check (prop and label match the cast sheet; the Beat 7 improvement stays localized), and human approval.

If clay texture flattens or identity drifts, a regeneration with a tightened material-detail block and an explicit "preserve all clay texture from @(img1)" constraint is a new credit-accounted generation: run it only inside the retry allowance the batch approval named (never more than 2 per beat), otherwise stop and ask the user.

## After animation

Assembly (trim each clip to its VO, mux, concatenate, optional judder pass) and captioning are covered in the Workflow section of `SKILL.md`, including what to do when no local ffmpeg is available.
