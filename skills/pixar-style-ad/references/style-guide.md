# Pixar-style ad: creative style guide

The aesthetic is the Disney-Pixar 3D animated feature film look applied to short-form vertical product ads (TikTok, Reels, Shorts). Format: 9:16 vertical, roughly 30 to 90 seconds total, 4 to 6 beats stitched from 3 to 15 second Seedance clips, voiceover overlaid in post, captions burned on at the end.

## What "Pixar style" means here (and what it does not)

The look is the Disney-Pixar feature film aesthetic specifically. Not generic CGI, not Studio Ghibli (that is 2D), not anime, not stretchy Dreamworks. Anchor every prompt on these traits:

- **3D rendered**, full volumetric lighting, ray-traced reflections
- **Oversized expressive eyes** with multiple specular highlights (the Pixar "wet eye")
- **Stylized but believable proportions**: slightly larger heads, soft features, simplified hands, smooth flowing forms
- **Rich material rendering**: subsurface scattering on skin, detailed fabric weave (waffle robes, knitwear), realistic hair strands, glass and liquid refraction
- **Soft warm golden-hour interior lighting**: sunlight through curtains, window light, lamp glow; almost never harsh top-down or fluorescent
- **Shallow depth of field** with creamy bokeh; the subject always sharply rendered
- **"Appeal"**: characters look like they are about to smile, mid-emotion, never blank-staring
- **Anthropomorphism welcome**: objects with faces, limbs, and eyes are core to the genre

**Do NOT use these words** (they pull away from the Pixar look): `anime`, `Ghibli`, `2D`, `cel-shaded`, `cartoon` (say "Pixar-style 3D animated" instead), `Dreamworks`, `realistic photo`, `live action`, `photorealistic`. When prompting Seedance, also avoid its own forbidden words: `cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect`.

## The story arc (hook / problem / product / payoff / CTA)

Every successful ad in this genre follows roughly the same structure. The hook is anthropomorphism plus a tiny story, not the product. Plan all beats up front so character and setting stay consistent across stills.

| Beat | Story job | Length | What is on screen |
|------|-----------|--------|-------------------|
| **1. Anthropomorphized problem** | HOOK + PROBLEM | 3 to 6s | Close-up macro shot of the problem object given Pixar eyes and a small mouth (a clump of hair in a drain, a cracked fingernail, a tired pillow, a moody pile of laundry). It speaks the user's complaint in first person. |
| **2. Reveal** | PRODUCT | 4 to 8s | A big-eyed Pixar-style protagonist in a sunlit cozy interior (robe, knitwear, soft hair) holding the product, soft window light, plants in the background, surprised or delighted expression. |
| **3. Mechanism of action** | PAYOFF (how it works) | 6 to 10s | A stylized interior (skin layers, hair follicle, joint, gut) with small chibi mascot characters actively doing the mechanism: repairing collagen fibers, stitching keratin, plumping cells. Glowing energy lines connect them. |
| **4. CTA** | CTA | 4 to 6s | The protagonist now smiling and confident, holding one or two product packs facing camera. Lower third clean for the burned-in caption, for example "Try {Brand} {Product} today." |

Variations:

- **Cold-open intercut**: alternate Beat 1 (problem character) with quick cuts of the human protagonist looking distressed before settling into Beat 2. Adds urgency.
- **Multi-pain montage**: 3 or 4 anthropomorphized problem characters in sequence ("I clog your drain", "I weigh down your hair", "I make you self-conscious") before the reveal.
- **Testimonial overlay**: the Beat 2 protagonist speaks the value proposition in first person ("I tried this for 30 days and it changed my mornings") instead of a third-person narrator.

## Cast and continuity sheet (build this BEFORE generating anything)

Pixar ads live or die on character continuity across beats. Build a one-page sheet and reuse it in every image prompt. Save it to `outputs/pixar-ad/<slug>/cast-sheet.md`.

```
PROTAGONIST (human hero)
- Age range: 20s / 30s / 40s
- Build: petite / average / curvy
- Hair: color, length, style (e.g. "ash-brown low bun with face-framing strands")
- Eyes: color, large Pixar irises, multiple catchlights
- Skin: warm undertone with light freckles across the nose bridge
- Outfit: cream waffle-knit robe over a fitted tank, thin gold necklace
- Personality cue: gentle smile, slightly tilted head

ANTHROPOMORPHIC PROBLEM CHARACTER (beat 1)
- What object: <e.g. clump of dark hair in a shower drain>
- Face placement: <e.g. two big sad eyes and a small downturned mouth embedded in the hair>
- Voice and personality: <e.g. defeated, weary, mumbling>

MASCOT CHARACTERS (beat 3)
- Form: chibi blob, 2 to 3 inches "tall", smooth matte rubbery material
- Color: ivory white with soft pink cheeks
- Eyes: tiny black dot pupils, single highlight, oversized
- Behavior: cooperative team, gently working on the mechanism

SETTING
- Beats 2 and 4: sunlit bedroom or kitchen, sheer curtains, plant in a clay pot, soft warm color grade
- Beat 3: stylized cross-section interior of <skin / hair follicle / joint / etc.>

PRODUCT
- Packaging colors, shape, label text (paste from BRAND.md or read off the product photo)
- Held at chest height with one or both hands, facing camera

STYLE LOCK (paste verbatim into every image prompt)
"Disney-Pixar 3D animated feature film aesthetic, soft volumetric golden-hour lighting,
subsurface scattering on skin, large expressive eyes with multiple catchlights, stylized
but believable proportions, rich material rendering, shallow depth of field, warm cozy
color palette, painterly background."
```

If the same brand runs another ad later, reuse this sheet so the campaign stays visually coherent.

## Why storyboard first, then animate

1. **gpt-image-2 for storyboard stills**: it produces the most consistent stylized 3D-animated stills, especially when you re-feed prior outputs as reference images for the next frame. It holds character identity across beats far better than text-only text-to-video.
2. **Seedance 2.0 image-to-video**: animates each still while preserving the rendered character. It takes the approved still in `referenceImages` and produces 3 to 15 seconds of motion driven by a text prompt.
3. **Assembly**: the per-beat voiced clips get concatenated into one continuous vertical video, then captions are burned on.

One-shot text-to-video is the wrong choice: you get character drift between beats, and the 15 second per-clip ceiling caps you far below ad length anyway. The image-first pipeline is mandatory for this style.

## Voiceover rules

- Generate the voiceover with Arcads text-to-speech (`arcads_text_to_speech`) and overlay it in post. Never use an in-prompt narrator line in the Seedance prompt; set `audioEnabled: false`.
- One `voiceId` across all beats. A second characterful voice is allowed for the anthropomorphized problem character's line only.
- **No dead space.** The voiceover must fill the clip it plays over. Dead air kills retention; viewers swipe on the first half second of silence. Per beat, either trim the clip to `vo_duration + 0.5s` (default), or extend the VO by a few words when the visual needs the full time to land (a camera move, the mascot mechanism, the CTA hold). An allowed micro-buffer is about a quarter second of lead and a quarter second of tail.
- If the VO runs longer than the clip, never speed it up. Split the line across two beats or regenerate the clip at a longer duration.
- Pace planning: assume roughly 2.5 spoken words per second when choosing each beat's `duration`.

## Negative prompt block (paste into every video prompt)

```
no live-action footage, no photorealistic faces, no anime style, no 2D cel-shaded
look, no Studio Ghibli style, no flat illustration, no harsh fluorescent lighting,
no extra fingers, no melted features, no morphing between frames, no warped product
labels, no on-screen text unless specified, no subtitles, no captions
```

For Seedance specifically, also strip the model's forbidden words from your prompt: no `cinematic`, `professional`, `stunning`, `8k`, `studio`, `perfect`. Substitute "3D animated film aesthetic" for cinematic, "polished" for stunning, "high fidelity" for 8k, "ivory white matte material" where you would have said perfect.

## Captioning (the burned-in short-form look)

Default: `arcads_add_subtitles` with `style: "style_1"` gives the white-text-with-black-stroke look on a master that has the VO baked in (it auto-transcribes the audio). Try other styles from the tool's catalog for variants.

If a human editor finishes the ad instead, describe the target look for them:

- White bold sans-serif (Montserrat Bold or similar), around 7 percent of video height
- 4 to 6 px solid black stroke, no drop shadow
- Lower third, centered, about 25 percent from the bottom (above the platform UI overlay)
- Caption changes per spoken phrase, not per word

**Important: let Seedance render the scene WITHOUT captions.** Tell it "no on-screen text, no captions, no subtitles" in every prompt; Seedance occasionally invents captions when you do not ask for them. Burn captions on after assembly, with control.
