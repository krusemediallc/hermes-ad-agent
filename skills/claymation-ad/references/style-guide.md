# Claymation ad: creative style guide

The aesthetic is the Aardman and Laika stop-motion claymation feature film look applied to short-form vertical product ads (TikTok, Reels, Shorts). Format: 9:16 vertical, roughly 35 to 115 seconds total, 5 to 8 beats stitched from 4 to 12 second Seedance clips, a third-person narrator voiceover overlaid in post, captions burned on at the end.

## What "claymation" means here (and what it does not)

This look anchors on the Aardman Animations lineage (Wallace and Gromit, Chicken Run) and Laika (Coraline, Kubo): hand-sculpted clay and plasticine, visible tool marks, slightly imperfect armatures, miniature physical sets. Not generic CGI cartoon.

Anchor every prompt on these traits:

- **Hand-sculpted clay and plasticine surfaces**: visible fingerprint impressions, sculpting-tool marks, slight asymmetry, subtle pinch lines around facial features
- **Matte clay material**: no Pixar wet-eye sheen, no glossy refraction; clay reads as opaque, slightly waxy, with soft micro-bumps
- **Exaggerated, character-driven faces**: oversized noses, deep wrinkles when called for, asymmetric eye placement, painted-on or sculpted eyebrows; characters can be quirky rather than conventionally appealing
- **Real-looking knit and felt fabric**: chunky wool sweaters, knit cardigans, felt curtains, separately constructed and stitched, not painted on
- **Wooden and ceramic props**: the miniature-set vibe of real-wood tables, hand-thrown ceramic mugs, tin kettles, fabric tablecloths
- **Warm tungsten interior lighting** for domestic scenes; cool fluorescent for office or dystopian scenes
- **Shallow depth of field** with creamy bokeh; a soft macro-photography feel that reinforces the miniature-set illusion
- **Subtle imperfection everywhere**: slightly uneven paint on labels, irregular fabric weave, clay surfaces never perfectly smooth

**Do NOT use these words** (they pull away from the claymation look): `Pixar`, `3D rendered`, `digital`, `CGI`, `anime`, `cel-shaded`, `2D`, `painted illustration`, `realistic photo`, `live action`, `photorealistic`, `smooth render`, `subsurface scattering`, `ray-traced`. When prompting Seedance, also avoid its own forbidden words: `cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect`.

## Smooth motion vs stop-motion judder: pick one

Real stop-motion has 12 to 15 fps judder. AI video generators output smooth 24 or 30 fps. The winning reference ads in this genre are all smooth: the AI keeps the handcrafted visual aesthetic but plays motion smoothly. That is the default.

If the user explicitly wants the judder feel, it is a post step (an ffmpeg fps filter after assembly, covered in `SKILL.md`). Do not bake judder into the Seedance prompt; the model cannot reliably control framerate and asking for judder tends to break the aesthetic.

## The claymation story arc (8 beats, longer-form than the Pixar genre)

Claymation ads in this genre are narrative: a quirky third-person narrator tells a story about a character. The protagonist drives the entire arc. Plan all beats up front so character and miniature set stay consistent.

| Beat | Story job | Length | What is on screen |
|------|-----------|--------|-------------------|
| **1. Setup** | HOOK | 6 to 10s | Wide or medium shot of the protagonist in their domestic miniature set (kitchen, bedroom, bathroom). The narrator says their name and a single defining trait. |
| **2. Inciting moment** | HOOK | 6 to 8s | Close-up of the protagonist's face as they spot the issue (lines in a mirror, a number on a scale, a sound). Surprised or concerned expression. |
| **3. Social validation** | PROBLEM | 6 to 10s | Two-character scene: the protagonist with a friend, spouse, or coworker in a cafe, living room, or office. A small exchange or remark. |
| **4. Quiet despair** | PROBLEM | 5 to 8s | A solo reflection beat. The protagonist alone at a window, mirror, or sink. No dialogue; the narrator carries it. |
| **5. Clay infographic** | PRODUCT (mechanism) | 6 to 10s | A hand-sculpted clay chart or diagram on a wall (clay letters, a plasticine line graph) explaining the mechanism. Optional: drop it if the product needs no explanation. |
| **6. Discovery** | PRODUCT | 6 to 8s | Close to medium shot of the product rendered as a slightly imperfect clay prop on a wooden table or shelf. The protagonist reaches for it. |
| **7. Transformation** | PAYOFF | 8 to 12s | Time passes, the protagonist uses the product, and a "weeks later" reveal shows subtle visible improvement. |
| **8. Resolution + CTA** | CTA | 6 to 8s | The confident protagonist holds the product, smiling at camera. Lower third clean for the burned-in CTA caption. |

Total: about 50 to 75 seconds of clip time. The **5-beat short** (Setup, Inciting, Discovery, Transformation, CTA) drops beats 3, 4, and 5 and lands around 35 to 45 seconds. Offer it as the budget option.

Variations by category:

- **Health and supplements**: the full 8-beat works well; the chart beat sells the mechanism.
- **Beauty and skincare**: emphasize beats 2 (mirror) and 4 (self-reflection); the chart beat is optional.
- **Office and B2B**: the protagonist sits in a fluorescent-lit office; a cool-light palette for beats 1 through 4, warm light only after the discovery.
- **Food and kitchen products**: beats 1, 6, and 7 dominate; the social beat becomes a family dinner.

## Cast and continuity sheet (build this BEFORE generating anything)

Claymation ads usually feature two or three named characters. Lock all of them up front and save the sheet to `outputs/claymation-ad/<slug>/cast-sheet.md`.

The examples below use a neutral fictional brand, "Everbloom" (a renewal face cream in a dusty-lavender jar), and fictional characters Diane and Margaret. Swap in the user's real brand and invent characters that fit their audience.

```
PROTAGONIST
- Name (used by the narrator): <e.g. Diane>
- Age range: <30s to 60s; claymation favors middle-aged and older characters>
- Distinctive feature: <e.g. shoulder-length terracotta-brown wavy hair, deep laugh lines, hooded eyelids>
- Build: <average / petite / sturdy>
- Eye color: <e.g. warm brown, sculpted lower lids visible>
- Outfit: <e.g. cream chunky knit cardigan over a rust-red blouse, dark wool trousers, brown leather slippers>
- Posture cue: <e.g. slight forward lean, soft rounded shoulders>

SUPPORTING CHARACTER (beat 3)
- Relationship: <best friend / spouse / coworker>
- Distinctive feature: <e.g. silver curly hair, round wire glasses, sage-green cable-knit sweater>
- Age range: <similar to or older than the protagonist>

NARRATOR (voiceover, never visible)
- Voice persona: <warm storytelling, mid-pace> OR <wry, dry humor>
- Tone: <gentle observational / wry / matter-of-fact>

SETTING, primary location
- Domestic: <e.g. small sunlit kitchen with green-painted cabinets, red gingham tablecloth, wooden table, copper kettle on the stove, potted herbs on the windowsill>
- Reuse this setting for beats 1, 6, and 8 to anchor continuity

SETTING, secondary location (beat 3)
- <e.g. a neighborhood cafe with potted plants, wooden tables, hanging brass pendant lights>

PRODUCT
- Render as a clay-stylized prop: matte hand-painted label, slightly imperfect jar or cylinder shape, paint that looks hand-applied
- Copy the exact label text from BRAND.md or the product photo
- Position: on the wooden table, bathroom shelf, or kitchen counter

STYLE LOCK (paste verbatim into every image prompt)
"Aardman-style stop-motion claymation aesthetic. Hand-sculpted plasticine
characters with visible fingerprint impressions and sculpting-tool marks,
matte clay surfaces, slightly asymmetric features. Real knit-fabric clothing
with visible weave, wooden and ceramic miniature-set props. Warm tungsten
interior lighting, shallow macro depth of field, soft photographic bokeh.
Subtle imperfection in every surface. 9:16 vertical."
```

If the same brand runs another ad later, reuse this sheet so the campaign stays coherent.

## Why storyboard first (gpt-image-2, with a nano-banana fallback)

1. **Identity continuity across 8 beats**: gpt-image-2 holds the same sculpted character face when you re-feed prior frames as references. Critical when the protagonist appears in beats 1, 2, 3, 4, 6, 7, and 8.
2. **Strong stylized stop-motion output**: gpt-image-2 renders clay textures cleanly when the STYLE LOCK is pasted verbatim.
3. **Fallback**: if gpt-image-2 smooths out the clay texture or loses fingerprint detail on close-ups, switch to `arcads_generate_image_nano_banana` for those specific beats only (product close-ups and the infographic, where character identity does not matter). Nano-banana holds texture better but is slightly weaker on cross-beat identity, so never switch the whole ad.
4. **Seedance 2.0 image-to-video** then animates each approved still while preserving the clay aesthetic. The 15 second per-clip ceiling is per beat; 8 beats at about 8 seconds average gives roughly 64 seconds of final ad after assembly.

One-shot text-to-video is the wrong choice for this style: identity drifts and the clip ceiling caps you far below ad length.

## Narration and dialogue rules

- Generate all voiceover with Arcads text-to-speech (`arcads_text_to_speech`) and overlay it in post. Never use an in-prompt narrator line in the Seedance prompt; set `audioEnabled: false`. In-prompt narration produces inconsistent voice quality across beats and locks pacing to the video model's delivery. External TTS gives one consistent voice, predictable per-line durations, and clean audio for the caption pass.
- One narrator `voiceId` across the whole ad. Warm storyteller tone by default (the Aardman feel); wry and dry also works. Browse `arcads_list_voices` and confirm the pick with the user.
- The narrator refers to the character by name ("Diane noticed her reflection had opinions").
- Character dialogue is sparse: at most one short casual line per character, never marketing copy. Often the supporting character makes the observation, for example: "You look different. What is that?" Render character lines as separate TTS calls with their own `voiceId` and place them at the right beat during assembly.
- **No dead space.** The voiceover must fill the clip it plays over; dead air kills retention. Per beat, either trim the clip to `vo_duration + 0.5s` (default) or extend the VO by a few words when the visual needs the time (a camera move, the transformation montage, the CTA hold). About a quarter second of lead and a quarter second of tail is the allowed micro-buffer.
- If the VO runs longer than the clip, never speed it up. Split the line across two beats or regenerate the clip at a longer duration.

### Per-beat duration from the narrator line (roughly 2.5 words per second)

| Narrator words | Spoken duration | Beat clip duration |
|----------------|-----------------|--------------------|
| 1 to 10 | about 2 to 3s | 6s |
| 11 to 17 | about 4 to 5s | 6s |
| 18 to 25 | about 6 to 7s | 8s |
| 26 to 32 | about 8 to 9s | 10s |
| 33 or more | split across beats | n/a |

TTS pace varies per voice, so treat these as planning numbers and measure the real audio durations during assembly.

## Negative prompt block (paste into every video prompt)

```
no live-action footage, no photorealistic faces, no Pixar style, no 3D rendered
look, no CGI, no anime, no 2D illustration, no smooth digital render, no ray-traced
materials, no extra fingers, no melted features, no morphing between frames, no
warped product labels, no on-screen text unless specified, no subtitles, no captions
```

For Seedance specifically, also strip the model's forbidden words: no `cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect`. Substitute "stop-motion claymation film aesthetic", "polished hand-sculpted", "high fidelity", "evenly hand-painted".

## Captioning

Two looks work for this genre:

**A. White with black stroke** (the classic short-form look): white bold sans-serif around 7 percent of video height, 4 to 6 px solid black stroke, lower third, centered, per-phrase timing. `arcads_add_subtitles` with `style: "style_1"` is the closest preset.

**B. Highlight block**: white bold text on a solid orange-red rounded rectangle with a slight 2 to 3 degree tilt for a handmade feel, one word or short phrase per block. No preset matches exactly; try the tool's other catalog styles for the closest fit, or describe this spec to a human editor.

Burn captions after assembly, never in the Seedance prompt. The negative block tells Seedance "no captions"; you add them in post, with control. `arcads_add_subtitles` transcribes from the master's baked-in audio, so it only works after the VO has been muxed in.
