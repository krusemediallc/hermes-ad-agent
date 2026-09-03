# Storyboard stills: gpt-image-2 prompt formulas

Generate the still-image storyboard before animating anything. Read `style-guide.md` first for the story arc, cast sheet, and aesthetic anchors.

Tool: `arcads_generate_image_gpt` with `model: "gpt-image-2"`, `aspectRatio: "9:16"`, up to 5 `referenceImages`, `nbGenerations` 1 to 10 for variations in a single call. Check your live tool list; server versions differ.

## Why gpt-image-2 for the storyboard

1. **Strong stylized 3D rendering**: a convincing Pixar lookalike without photoreal artifacts leaking in.
2. **Reference-image fidelity**: passing prior outputs as references holds protagonist identity across beats.
3. **Editable**: you can iterate on a frame by passing the same image back with a refinement instruction.

## Universal prompt structure

Every beat prompt has the same five-block structure. Paste the blocks in this order:

```
[STYLE LOCK]      <- identical across all beats
[ASPECT + FRAMING]
[CHARACTER]       <- protagonist OR anthropomorphic problem OR mascots
[SCENE / ACTION]
[NEGATIVE]
```

### STYLE LOCK (paste verbatim into every beat)

```
Disney-Pixar 3D animated feature film aesthetic, rendered in a stylized 3D animation
style. Soft volumetric golden-hour lighting from a large window, warm cozy color
palette of cream, butter yellow, dusty pink, and soft sage. Subsurface scattering
on skin, painterly background, shallow depth of field with creamy bokeh. Characters
have large expressive eyes with multiple specular catchlights, stylized but
believable proportions, smooth simplified hands, soft hair strands with subsurface
glow. Rich material detail: waffle-knit fabric weave, ceramic glaze, glass
refraction. Slightly desaturated film color grade. Vertical 9:16 composition.
```

### NEGATIVE (paste into every beat; gpt-image-2 accepts these as inline constraints)

```
Not photorealistic, not live-action, not anime, not 2D, not cel-shaded, not Studio
Ghibli, not flat illustration. No extra fingers, no merged features, no warped
product labels, no on-screen text unless explicitly requested.
```

## Beat 1: anthropomorphized problem character (HOOK + PROBLEM)

**Goal:** a close-up macro of the user's pain point, given Pixar eyes and a small mouth, about to speak the complaint in first person.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, extreme close-up macro shot of {{PAIN_POINT_OBJECT}} resting on
{{SURFACE_OR_LOCATION}}. Embedded in the {{OBJECT}} are two oversized Pixar-style eyes
with thick lower lashes and a {{EYE_EXPRESSION}} expression, pupils oversized, two or
three specular catchlights, slight tears welling at the corners. A small downturned
mouth sits below the eyes. The {{OBJECT}} has a slight slump or {{POSTURE}} posture
that reinforces its sadness. Background is soft-focus {{SETTING}} with warm ambient
bokeh. The character looks directly at camera.

{NEGATIVE}
```

**Variable examples:**

| Pain point object | Surface / location | Eye expression | Posture |
|-------------------|--------------------|----------------|---------|
| clump of dark tangled hair | stainless steel shower drain with soap bubbles | exhausted, half-lidded | drooping over the drain edge |
| cracked, flaking fingernail | a pale fingertip with subtle skin texture | tearful, brows pinched inward | slightly bent and chipped |
| a worn, dingy pillow | rumpled white linen sheets with morning light | grumpy, brows furrowed | sagging in the middle |
| a tired plant leaf | terracotta pot on a kitchen counter | weary, eyes half-closed | wilted, drooping downward |
| a heap of laundry | overflowing wicker basket | overwhelmed, eyes wide and frazzled | precariously stacked |

**Worked example (drain hair):**

```
[STYLE LOCK]

Aspect ratio 9:16, extreme close-up macro shot of a dark tangled clump of long brown
hair resting in a stainless steel shower drain with small soap bubbles around it.
Embedded in the hair clump are two oversized Pixar-style eyes with thick lower
lashes, pupils oversized, three specular catchlights, slight tears welling at the
corners, an exhausted half-lidded expression. A small downturned mouth sits below
the eyes. The hair clump droops over the drain edge, slumped and defeated. Background
is soft-focus white shower tile with warm ambient bokeh. The character looks directly
at camera.

[NEGATIVE]
```

## Beat 2: protagonist reveal (PRODUCT)

**Goal:** cut to the Pixar-style human hero in a sunlit interior, holding the product with a delighted or curious expression.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, medium head-and-shoulders shot of {{PROTAGONIST}} standing in
{{INTERIOR_SETTING}}. Soft window light from camera-left wraps across her face,
backlight rim through {{LIGHT_SOURCE}}. She holds {{PRODUCT}} at chest height with
{{HAND_POSITION}}, looking down at it with {{EXPRESSION}}, lips slightly parted. Her
hair is {{HAIR_DESCRIPTION}}, eyes are {{EYE_COLOR}} with oversized Pixar irises and
multiple highlights. She wears {{OUTFIT}}. Background includes {{BACKGROUND_PROPS}}
in soft focus.

{NEGATIVE}
```

**Variable examples:**

| Slot | Examples |
|------|----------|
| `PROTAGONIST` | "a young woman in her late 20s, warm undertone skin with light freckles across the nose bridge" |
| `INTERIOR_SETTING` | "a sunlit bedroom with sheer linen curtains and an exposed beam ceiling" / "a bright kitchen with pale oak cabinets" |
| `LIGHT_SOURCE` | "sheer curtains" / "a south-facing window" / "a morning kitchen window" |
| `PRODUCT` | full description of the user's product packaging: color, shape, label text (from BRAND.md or the product photo) |
| `HAND_POSITION` | "both hands cradling it gently" / "one hand around the pouch, the other thumb on the label" |
| `EXPRESSION` | "delighted curiosity, eyes wide" / "gentle surprise, eyebrows raised" |
| `HAIR_DESCRIPTION` | "ash-brown low bun with face-framing strands" / "honey blonde messy bun" |
| `OUTFIT` | "a cream waffle-knit robe over a fitted tank, thin gold necklace" |
| `BACKGROUND_PROPS` | "a leafy potted monstera, an unmade linen bed, soft morning light" |

**Reference-image input:** when generating Beat 2, attach the approved hero portrait (if one exists) as a reference image to lock identity. If the user supplies a real product photo, attach it too so the packaging renders accurately.

## Beat 3: mascot mechanism of action (PAYOFF)

**Goal:** a stylized cross-section of the relevant body interior with chibi blob mascots actively doing the mechanism the product claims. Only make mechanism claims that BRAND.md supports.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, stylized cross-section view of {{INTERIOR_STRUCTURE}}, rendered as
a soft painterly landscape of {{TEXTURES}}. Three to five small chibi mascot
characters populate the scene. Each is a 2 to 3 inch tall ivory-white matte blob with
a smooth rounded body, tiny black-dot eyes with one highlight each, soft pink cheeks,
and small simple limbs. They are {{MASCOT_ACTION}}. Glowing golden energy lines and
{{ENERGY_VISUAL}} connect the mascots and trace through the structure, indicating
the active mechanism. Soft warm interior lighting with a golden ambient glow.

{NEGATIVE}
```

**Variable examples (by mechanism):**

| Product claim | Interior structure | Mascot action | Energy visual |
|---------------|--------------------|----------------|---------------|
| Builds collagen | cross-section of skin layers with hair follicles and collagen fibers | mascots pulling and weaving glowing golden collagen strands taut | golden energy lines linking strand nodes |
| Strengthens nails | inside a nail bed with keratin layers | mascots stacking and stitching keratin scales into a smooth shield | sparkling crystalline keratin layers forming |
| Supports gut health | cross-section of intestinal villi with a friendly microbiome | mascots high-fiving and tending tiny gardens between the villi | soft pink-green energy waves rolling through |
| Soothes joints | inside a knee joint with cartilage and synovial fluid | mascots gently smoothing cartilage with tiny tools, applying a glowing gel | swirling teal cushioning halo around the joint |
| Hydrates hair | cross-section of a single hair shaft with cuticle scales | mascots smoothing lifted cuticle scales down like roof shingles | iridescent moisture droplets soaking in |
| Sharpens focus | a softly glowing stylized brain landscape with winding neural paths | mascots relinking glowing pathway segments and flipping tiny switches on | warm amber signal pulses traveling the paths |

## Beat 4: CTA frame

**Goal:** the protagonist (same identity as Beat 2) holds one or two product packages facing camera, confident smile, lower third left clean for the caption overlay.

**Formula:**

```
{STYLE LOCK}

Aspect ratio 9:16, medium shot of {{PROTAGONIST}} (same character as previous frames)
standing in {{SAME_INTERIOR_SETTING}}, now facing camera directly with a warm
confident smile, eyes bright. She holds {{ONE_OR_TWO_PRODUCT_PACKAGES}} at chest
height, labels turned cleanly toward camera. Soft window light from camera-left,
gentle backlight rim. Background includes {{BACKGROUND_PROPS}} in soft focus. The
lower third of the frame has empty negative space for a caption overlay.

{NEGATIVE}
```

The "empty negative space in the lower third" hint helps the model leave room for the burned-in caption you add in post.

## Cross-beat continuity rules

1. **Always pass the prior approved frame as a reference image** when generating the next beat featuring the same character. gpt-image-2 honors references strongly for style and identity. (Remember: on this MCP a temp uploaded `filePath` is single-use; upload a fresh copy of the still right before each call that references it.)
2. **Keep the STYLE LOCK block byte-identical** across all beats. Do not paraphrase it; it is a style anchor.
3. **Reuse exact phrasing** for hair, outfit, eye color, freckles, and skin tone in every beat that includes the protagonist. "Ash-brown low bun" in Beat 2 and "brown hair tied back" in Beat 4 produce two different characters.
4. **Lock the product packaging description once** in the cast sheet and copy-paste it identically into Beats 2 and 4.
5. **Generate beats sequentially, not in parallel.** You need to approve each still before passing it as the reference to the next.
6. **Typography warning:** if a still needs a two-column comparison or any dense text layout, specify BOTH columns' values explicitly or gpt-image-2 tends to duplicate one column.

## Image QA checklist (per beat)

Before sending a still to Seedance for animation, verify:

- [ ] The character has the right number of fingers on each visible hand (five each, thumb included)
- [ ] Both eyes aligned, pupils centered, no drift
- [ ] The product label reads correctly and matches the brand reference
- [ ] Same protagonist across beats: same hair, eye color, freckles, outfit
- [ ] No burned-in text unless requested
- [ ] Aspect ratio is 9:16
- [ ] The lower third has clean negative space if this frame will carry a caption

A corrected-prompt retry is a new credit-accounted generation: run it only inside the retry allowance the still batch approval named (never more than 2 per beat), otherwise stop and ask the user. Report each retry's actual `creditsCharged`.

## When the user already has a brand character

If they provide an existing Pixar-style hero image, skip the protagonist-generation step: pass that hero as the reference image into Beats 2 and 4 directly. Beats 1 and 3 do not need the hero reference (different subjects).
