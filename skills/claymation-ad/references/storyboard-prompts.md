# Claymation storyboard: gpt-image-2 prompt formulas

Generate the still-image storyboard before animating anything. Read `style-guide.md` first for the 8-beat arc, the cast sheet, and the aesthetic anchors.

Tool: `arcads_generate_image_gpt` with `model: "gpt-image-2"`, `aspectRatio: "9:16"`, up to 5 `referenceImages`, `nbGenerations` 1 to 10 for variations in a single call. Texture fallback for beats where identity does not matter: `arcads_generate_image_nano_banana` (up to 14 references). Check your live tool list; server versions differ.

The worked examples below use a neutral fictional brand, "Everbloom" (a renewal face cream in a dusty-lavender jar), with fictional characters Diane and Margaret. Swap in the user's real brand, product, and cast sheet.

## Universal prompt structure

Each beat uses the same six-block structure. Paste the blocks in this order:

```
[STYLE LOCK]            <- identical across all beats
[ASPECT + FRAMING]
[CHARACTER(S)]          <- protagonist alone, two-shot, or product/infographic
[SCENE / ACTION]
[MATERIAL DETAIL]       <- clay, fabric, and wood specifics; critical for the look
[NEGATIVE]
```

### STYLE LOCK (paste verbatim into every beat)

```
Aardman-style stop-motion claymation aesthetic. Hand-sculpted plasticine
characters with visible fingerprint impressions and sculpting-tool marks on
clay surfaces, matte clay material with subtle micro-bumps, slightly
asymmetric facial features, painted-on or carefully sculpted eyebrows. Real
knit-fabric clothing with visible weave and stitch lines. Wooden and ceramic
miniature-set props with hand-painted finishes. Warm tungsten interior
lighting, shallow macro depth of field with soft photographic bokeh that
reinforces the miniature-set illusion. Subtle imperfection in every surface,
slightly uneven paint, irregular fabric weave, asymmetric forms.
```

### NEGATIVE (paste into every beat)

```
Not photorealistic, not live-action, not Pixar style, not 3D rendered, not
CGI, not anime, not 2D illustration, not smooth digital render, not glossy,
no ray-traced reflections, no oversized Pixar-style eyes with multiple
highlights. No extra fingers, no merged features, no warped product labels,
no on-screen text unless explicitly requested.
```

### MATERIAL DETAIL (paste the relevant subset into every beat)

Adjust which lines apply to what is in frame:

```
- Skin: matte plasticine, visible thumbprint impressions on cheeks and forehead,
  small sculpting-knife creases at the corners of the eyes, slight asymmetry
  between the left and right side of the face
- Hair: sculpted in distinct ribbon-strands of plasticine, individual strand
  grooves carved with a tool, slightly stiff and not flowing
- Eyes: small matte clay or painted-resin orbs set into sculpted sockets,
  single soft highlight, no wet shine
- Knitwear: real chunky wool yarn, individual stitches visible, slight wear
  at cuffs and hems
- Wood props: hand-painted matte finish, visible grain, small dents and
  scratches that suggest age
- Ceramic and pottery: hand-thrown irregular form, glaze pooling at the bottom
  edges, slight off-roundness
- Product packaging: rendered as a clay-shaded prop with a hand-painted label,
  paint slightly uneven and matte
```

---

## Beat 1: Setup (protagonist in their world)

**Goal:** a wide or medium shot establishing the protagonist in their primary domestic miniature set while the narrator introduces them by name.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, {{WIDE_OR_MEDIUM}} shot of {{PROTAGONIST_FROM_CAST_SHEET}}
standing or sitting in {{PRIMARY_SETTING}}. {{POSTURE_AND_ACTION}}. Warm
morning tungsten light falls across the scene from {{LIGHT_SOURCE}},
casting soft shadows on the wooden floor. Background includes
{{BACKGROUND_PROPS}} in soft macro bokeh, so the miniature-set illusion is
strong.

{MATERIAL DETAIL: skin, hair, knitwear, wood, ceramic}

{NEGATIVE}
```

**Worked example (Diane in her kitchen):**

```
[STYLE LOCK]

Aspect ratio 9:16, medium-wide shot of Diane, a woman in her late 50s with
shoulder-length terracotta-brown wavy plasticine hair sculpted in distinct
ribbon-strands, deep laugh lines and hooded eyelids in matte sculpted clay,
warm brown eyes set into deep sockets. She wears a cream chunky knit
cardigan over a rust-red blouse, dark wool trousers, brown leather slippers.
She stands at her sunlit kitchen counter, pouring tea from a hand-thrown
ceramic kettle into a wide cup. Warm morning tungsten light falls from a
large window on camera-left, casting soft shadows on the wooden floor.
Background includes green-painted cabinets, a red gingham tablecloth, potted
herbs on the windowsill, all in soft macro bokeh.

[MATERIAL DETAIL: skin shows thumbprint impressions on the cheeks; hair has
individual carved strand grooves; the knit cardigan shows real wool weave with
slight wear at the cuffs; the wooden counter has visible grain and small dents;
the ceramic kettle has a slightly off-round form with glaze pooling at the base.]

[NEGATIVE]
```

---

## Beat 2: Inciting moment (close-up, the protagonist notices the problem)

**Goal:** a tight close-up on the protagonist's face as they see the issue.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, tight close-up of {{PROTAGONIST_FROM_CAST_SHEET}}'s face
as she {{NOTICING_ACTION}}. Her expression is {{CONCERNED_EXPRESSION}},
{{SPECIFIC_FACIAL_CUE}}. {{REFLECTION_OR_FOCAL_OBJECT}} is partially visible
in frame. Soft directional tungsten light wraps her face from
{{LIGHT_DIRECTION}}. Shallow depth of field, miniature-set bokeh behind her.

{MATERIAL DETAIL: emphasize skin texture, eye sockets, sculpted brow}

{NEGATIVE}
```

**Variable examples:**

| Slot | Examples |
|------|----------|
| `NOTICING_ACTION` | "leans toward a small wood-framed bathroom mirror, fingertip lifted to her upper lip" / "looks down at the bathroom scale at her feet" / "studies a clay-rendered chart on the wall" |
| `CONCERNED_EXPRESSION` | "softly furrowed brow, mouth slightly open" / "eyes widening with quiet alarm" / "lips pursed, sculpted eyebrows raised" |
| `SPECIFIC_FACIAL_CUE` | "small carved lines visible above her lip" / "a single sculpted crease deepens between her brows" |
| `REFLECTION_OR_FOCAL_OBJECT` | "her own reflection in the mirror, hair slightly different" / "the scale's clay-painted dial" |

---

## Beat 3: Social validation (two-shot)

**Goal:** the protagonist with a friend, spouse, or coworker in the secondary setting; a small exchange or remark.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, medium two-shot of {{PROTAGONIST_FROM_CAST_SHEET}} on
the {{LEFT_OR_RIGHT}} and {{SUPPORTING_CHARACTER_FROM_CAST_SHEET}} on the
opposite side, both seated at {{SECONDARY_SETTING_PROP}}. {{SHARED_ACTIVITY}}.
The supporting character is mid-remark, mouth slightly open, sculpted
eyebrows raised in curiosity, looking at the protagonist. The protagonist
{{REACTION}}. Background includes {{SECONDARY_SETTING_DETAIL}} in soft macro
bokeh. Warm tungsten light from above.

{MATERIAL DETAIL: both characters' skin, hair, and knitwear; secondary setting props}

{NEGATIVE}
```

**Worked example (Diane and Margaret at a cafe):**

```
[STYLE LOCK]

Aspect ratio 9:16, medium two-shot of Diane on the right and her friend
Margaret on the left, both seated at a small wooden cafe table holding
hand-thrown ceramic teacups. Margaret has silver curly plasticine hair,
round wire glasses, and a sage-green cable-knit sweater. They are sharing
afternoon tea over a small clay teapot. Margaret is mid-remark, mouth
slightly open, sculpted eyebrows raised in curiosity, looking at Diane.
Diane holds her teacup partway to her mouth, expression softly
self-conscious, eyes glancing down. Background includes a wall of potted
plants on wooden shelves and hanging brass pendant lights, all in soft
macro bokeh. Warm tungsten light from above.

[MATERIAL DETAIL: Diane's terracotta plasticine hair and Margaret's silver
sculpted curls both show carved strand grooves; both knit garments show real
wool weave; the ceramic teacups are hand-thrown with slight off-roundness;
the wooden table has visible grain.]

[NEGATIVE]
```

---

## Beat 4: Quiet despair (solo reflection)

**Goal:** the protagonist alone, looking at her reflection or out a window. The narrator carries the emotional beat; no dialogue.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, {{MEDIUM_OR_WIDE}} shot of {{PROTAGONIST_FROM_CAST_SHEET}}
standing alone in {{INTROSPECTIVE_LOCATION}}, {{REFLECTIVE_POSE}}. Her
expression is {{SUBDUED_EMOTION}}. Soft dim tungsten light enters from
{{LIGHT_SOURCE}}, casting long sculpted shadows. The background is sparse,
quiet, and slightly shadowed compared to the other beats, emphasizing
solitude.

{MATERIAL DETAIL: skin, hair, and knitwear emphasized in the dimmer light}

{NEGATIVE}
```

---

## Beat 5: Clay infographic (no characters needed)

**Goal:** a hand-sculpted clay chart or diagram explaining the mechanism, static or with one subtle indicator. Only visualize claims BRAND.md supports. This beat can generate independently (no continuity references) and is the first candidate for the nano-banana texture fallback.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, head-on shot of a {{CHART_TYPE}} sculpted entirely from
clay and plasticine on a {{FRAME_DESCRIPTION}}. The title at the top reads
"{{TITLE_TEXT}}" in chunky hand-sculpted clay letters with slight asymmetry,
each letter looking individually shaped by hand. The chart shows
{{CHART_CONTENT}}. {{INDICATOR_OR_ANNOTATION}}. Soft tungsten light falls
across the chart from camera-left, casting subtle sculpted shadows that
reveal the depth of each clay element. The wall behind the frame is plain
cream-painted clay with a slight texture.

{MATERIAL DETAIL: emphasize the clay letters and lines, hand-shaped imperfection}

{NEGATIVE}
```

**Worked example (skin-moisture chart for Everbloom):**

```
[STYLE LOCK]

Aspect ratio 9:16, head-on shot of a line graph sculpted entirely from clay
and plasticine on a hand-carved wooden frame. The title at the top reads
"SKIN MOISTURE" in chunky hand-sculpted clay letters with slight asymmetry,
each letter looking individually shaped by hand. The chart shows a high
horizontal line on the left labeled "HIGH" that drops steadily down to "LOW"
near the right side, with x-axis tick marks labeled "30 40 50 60" in clay
buttons. A small clay arrow points to the drop, labeled "OVER TIME" in a
sculpted rounded tag. Soft tungsten light falls across the chart from
camera-left, casting subtle sculpted shadows that reveal the depth of each
clay element. The wall behind the frame is plain cream-painted clay with a
slight texture.

[MATERIAL DETAIL: clay letters show fingerprint impressions and slightly
uneven edges; the line graph is a single carved plasticine ribbon; the arrow
and tags are individually pressed clay; the wooden frame has hand-carved
grain and a hand-painted finish.]

[NEGATIVE]
```

---

## Beat 6: Discovery (product close-up plus protagonist reach)

**Goal:** a close to medium shot of the product rendered as a clay prop, with the protagonist's hand reaching toward it. Second candidate for the nano-banana texture fallback.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, {{CLOSE_OR_MEDIUM}} shot of {{PRODUCT_DESCRIPTION_AS_CLAY_PROP}}
sitting on {{SURFACE}}. {{PROTAGONIST_FROM_CAST_SHEET}}'s hand enters frame
from {{HAND_DIRECTION}}, sculpted fingers reaching toward the product.
Surrounding props include {{SUPPORTING_PROPS}} in soft macro bokeh. Warm
tungsten light from {{LIGHT_SOURCE}} catches the product label, making the
hand-painted text readable.

{MATERIAL DETAIL: the product prop, the surrounding wood, ceramic, and cloth}

{NEGATIVE}
```

**Worked example (Everbloom jar on the kitchen table):**

```
[STYLE LOCK]

Aspect ratio 9:16, medium shot of a small dusty-lavender jar labeled
"everbloom" in hand-painted cream lettering, with smaller hand-painted text
underneath that reads "RENEWAL CREAM" in matte plum, sitting on a wooden
kitchen table. The jar is rendered as a clay prop: a slightly imperfect
cylinder, hand-applied matte paint with subtle brush texture. Diane's hand
enters frame from camera-right, terracotta-clay fingers reaching toward the
jar. Surrounding props include a cream hand-thrown ceramic cup, a red
gingham tablecloth corner, and a tin kettle in the background, all in soft
macro bokeh. Warm tungsten light from a window on camera-left catches the
jar label.

[MATERIAL DETAIL: the jar paint is slightly uneven and matte; the ceramic cup
has glaze pooling at the base; the wooden table has visible grain and small
dents; the hand shows sculpted knuckle creases and slight asymmetry.]

[NEGATIVE]
```

---

## Beat 7: Transformation (weeks later)

**Goal:** time passes, the protagonist uses the product, and a "weeks later" reveal shows subtle visual improvement. Reference the approved Beat 6 still so the product prop stays identical.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, {{FRAMING}} of {{PROTAGONIST_FROM_CAST_SHEET}}
{{USING_OR_AFTER_USING_PRODUCT}}. {{SUBTLE_TRANSFORMATION_CUE}}. Her
expression is {{POSITIVE_EMOTION}}, {{SPECIFIC_FACIAL_CUE}}. Soft natural
tungsten light, slightly brighter and warmer than the earlier beats to
signal positive change. The background is the {{PRIMARY_SETTING}} from
Beat 1, lit a touch more openly.

{MATERIAL DETAIL: note the subtle improvement, e.g. slightly smoother clay
skin in one specific area only, slightly more open eyes, upright posture}

{NEGATIVE}
```

Keep the improvement localized and subtle: same character, same identity, one specific area of the clay a touch smoother. A full-face smoothing reads as a different character and usually means the model dropped the clay aesthetic.

---

## Beat 8: Resolution + CTA

**Goal:** the confident protagonist with the product, lower third clean for the burned-in CTA caption.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, medium shot of {{PROTAGONIST_FROM_CAST_SHEET}} in
{{PRIMARY_SETTING}}, facing camera directly with a {{CONFIDENT_SMILE}}.
She holds {{PRODUCT_DESCRIPTION}} at chest height with sculpted clay hands,
the hand-painted label rotated cleanly toward camera. Warm tungsten light
from camera-left wraps her face, with a soft rim light from camera-right.
{{BACKGROUND_PROPS}} are in soft macro bokeh. The lower third of the frame
remains visually clean and uncluttered, leaving room for a post-production
caption overlay.

{MATERIAL DETAIL: clay skin, hair, knitwear, the product, surrounding props}

{NEGATIVE}
```

---

## Cross-beat continuity rules

1. **Always pass the prior approved protagonist still as a reference image** when generating the next beat that includes the protagonist. Beats 1, 2, 4, 6, 7, 8 chain in order. Beat 3 attaches Beat 1 (or Beat 2) as the protagonist reference; the supporting character is generated fresh from the cast sheet. (Remember: on this MCP a temp uploaded `filePath` is single-use; upload a fresh copy of the still right before each call that references it.)
2. **Keep the STYLE LOCK and MATERIAL DETAIL blocks consistent.** Do not paraphrase them.
3. **Reuse exact phrasing** for hair color, eye color, clothing, and skin texture across every protagonist beat. "Terracotta-brown wavy plasticine hair sculpted in distinct ribbon-strands" must appear identically in every prompt; do not shorten it to "brown clay hair" in later beats.
4. **Generate sequentially, not in parallel.** Identity drift compounds otherwise.
5. **Beat 5 is independent** and can generate at any time.
6. **Beat 7 references Beat 6's product prop**: pass the approved Beat 6 still as a reference to keep the packaging identical.

## Image QA checklist (claymation-specific)

Before sending a still to Seedance, verify:

- [ ] Clay texture preserved: thumbprint and tool marks visible on faces and hands, no smooth Pixar-style render leaking in
- [ ] Knit fabric reads as real wool weave, not painted-on stripes
- [ ] Eyes are matte, a single soft highlight at most, no wet-eye multi-catchlight
- [ ] Hair shows individual carved strand grooves
- [ ] Wooden and ceramic props show a hand-painted finish and slight irregularity
- [ ] Character identity holds across all protagonist beats: same face proportions, same hair color and style, same outfit
- [ ] Product label paint looks hand-applied: slight unevenness, matte finish
- [ ] No burned-in text except the sculpted lettering Beat 5 explicitly asks for
- [ ] 9:16 aspect ratio
- [ ] Beat 8 has clean negative space in the lower third

A corrected-prompt retry is a new credit-accounted generation: run it only inside the retry allowance the still batch approval named (never more than 2 per beat), otherwise stop and ask the user, and report each retry's actual `creditsCharged`. If the allowed retries still lose clay texture or identity, propose `arcads_generate_image_nano_banana` for that specific beat (it tends to hold texture better on close-ups and product props) as a new gated generation. Beat-by-beat fallback only; never switch the entire ad.

## When the user already has a clay character

If they provide an existing claymation-style hero image, skip the cast-sheet protagonist build: pass that hero as the reference image for every protagonist beat. Beat 5 does not need it.
