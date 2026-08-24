# Nano Banana prompting guide (nano-banana-image-ad)

Model-specific brain for generating standalone Meta ad creatives with the Nano Banana family (`nano-banana-2`, Google's Gemini Flash Image) through the Arcads MCP server.

The shared template library (37 validated ad-format templates with per-model notes) ships with the **image-ad-clone** skill; when installed it lives at `~/.hermes/skills/image-ad-clone/references/prompt-library.md`. Check it before composing a fresh prompt.

## What nano-banana is good at

Pick this skill (over chatgpt-image-ad) when the ad's success depends on any of these:

- **Photoreal handheld objects**: held-up whiteboard signs, hand-lettered cardboard, handwritten napkin notes, sticky-note + product flatlays, letter-board signs. Nano Banana renders held-paper texture, marker bleed, and hand-shadow naturalism better than gpt-image-2.
- **Aspirational lifestyle photography**: full-bleed scenic backgrounds (sunset coastline, mountain trail, kitchen at golden hour) with naturalistic lighting and shallow depth of field.
- **Multi-image reference blending**: up to 14 reference images, blended smoothly (logo + product + style board + character + setting in one composition).
- **Subject continuity across runs**: pass the same hero portrait as a reference in every run and the character stays consistent.
- **Rich material rendering**: leather, metal, fabric, foil, glass, liquid, plasticine. Anywhere the brief says "photoreal" or "tactile".
- **Stop-motion / claymation / Pixar-adjacent aesthetics**: material-based realism that gpt-image-2 flattens.

## What nano-banana struggles with

If any of these are core to the ad, prefer **chatgpt-image-ad** (gpt-image-2) instead:

- **Dense small body text**: chat bubbles, ChatGPT-response panels, table rows, calendar blocks, Slack messages, comment threads, search results pages. Letters blur or rearrange at small size.
- **UI mimicry of specific platforms**: iOS Messages chrome, Slack window proportions, Google search layout. The aesthetic is close but not pixel-faithful.
- **Brand wordmark fidelity**: text wordmarks can drift if not passed as a reference image.
- **Condensed-sans / brutalist typography hero quotes**: letter-spacing and condensed letterforms shift run to run.
- **Crossword grids, AirDrop dialogs, fake comment threads**: anything where small-text fidelity inside a rectangular UI element is the whole gag.

## Hard limits (Arcads MCP)

1. **Model enum is `nano-banana-2` (default) or `nano-banana`.** The MCP tool does not expose `-pro` or `-edit` variants. For an inpaint-style edit, do a full regeneration with the change described in the prompt.
2. **Max 14 reference images** per call, passed as uploaded `filePath` values.
3. **Aspect ratios: `1:1`, `16:9`, `9:16` only.** Templates designed for `4:5` or `2:3` render at the nearest supported ratio and get cropped downstream before upload.
4. **No platform/screenshot chrome** in output (the no-chrome suffix is always on unless the concept genuinely requires simulated chrome and the user agrees).
5. **Edge-safe rule always on**: text and focal subjects inside the central 84% of the canvas.
6. **Glyph-safety rule always on**: plain words inside body-text blocks; emoji OK in headlines.

## Composing the prompt

When writing or completing a prompt, anchor on:

- **Subject and pose**
- **Lighting and time of day**: Nano Banana renders natural light beautifully. Specify "golden hour through east-facing window", "diffuse overhead studio softbox", "harsh midday sun with crisp shadows".
- **Lens / framing**: "35mm shallow depth of field", "macro extreme close-up", "wide environmental".
- **Color palette / mood**: pull from BRAND.md.
- **Composition**: rule of thirds, leading lines, region-by-region layout in vertical order (top X%, middle, bottom).
- **Negative space for text overlay** if the ad carries headline or body copy.
- **Reference roles**: name each reference explicitly. "The product in image 1", "the lighting and mood from image 2", "the character from image 3". Multi-reference blending improves dramatically with named roles.
- **Material specifics**: "subsurface scattering on skin", "satin foil reflectivity", "knit fabric weave", "marker bleed at stroke edges". Nano Banana renders material distinctions; lean into them.
- **Standalone-creative scope**: never describe iOS chrome, Sponsored badges, engagement counts, or platform UI.
- **Avoid keyword-soup prompts**: Nano Banana responds better to one well-written paragraph than to a comma-separated keyword list.

Show the rewritten prompt to the user as one block, say which template (if any) it is based on, and loop on "use / edit / start over" until approved.

## Always-on safety suffixes (append all three to every prompt)

There is no script auto-appending these anymore: **you** append them to the end of every image-ad prompt before generating. They fix recurring rendering failures across every modern image model and total about 1,575 characters, well under prompt caps. Do not silently drop them; skip the no-chrome guard only when the ad's concept genuinely requires simulated platform chrome and the user has agreed.

### 1. NO_CHROME_SUFFIX

```
[NO PLATFORM CHROME] Render only the standalone ad creative (the static image uploaded to Meta),
not a screenshot of how it displays in-feed. Exclude: iOS device chrome (status bar, home indicator);
platform brand-row above the ad (avatar + handle + Sponsored / Saved label); post body / caption text;
link-card footer (URL + headline + button); engagement rows (likes / comments / shares counts,
Followed-by, View comments); action buttons (Like / Comment / Share / Save); comment input boxes;
platform tab/nav bars (Instagram, Facebook, Twitter); Story chrome (progress bars, story header,
swipe-up arrows). Just the standalone image.
```

### 2. SAFE_ZONE_SUFFIX

```
[EDGE-SAFE] All text, headlines, CTAs, table headers, sign/board content, product wordmarks, and
key focal subjects must fit within the central 84% of the canvas (~8% padding from every edge).
Backgrounds and divider lines may bleed; text and focal elements may NOT touch or extend off any edge.
If a tall focal subject doesn't fit at the requested aspect ratio, scale it DOWN. Never crop a
headline, never let text run off-frame, never cut off the top/bottom of a sign, board, or product.
```

### 3. GLYPH_SAFETY_SUFFIX

```
[TEXT FIDELITY] Inside body-text blocks (chat bubbles, message threads, comment text, ChatGPT
responses, dense paragraphs): plain words only. NO emoji, NO unicode glyphs, NO special characters
mid-sentence. Emoji OK in headlines and short large-text positions where the prompt explicitly calls
for them. Render the EXACT count of conversation elements the prompt specifies. Do not invent
additional comments, messages, replies, or responses.
```

## Retry mode (when a variant fails visual QA)

Regenerate with a **revised** prompt that explicitly corrects the defect. Never resend the same payload expecting a different outcome.

Common nano-banana defects and their fixes:
- **Garbled small text**: if the text is essential, switch to chatgpt-image-ad. Otherwise scale the text block up to occupy at least 30% of the canvas and re-render.
- **Wordmark drift**: pass the wordmark as a reference image AND name it in the prompt ("the brand wordmark from image 1").
- **Wrong character identity across runs**: pass the hero portrait as a reference in every run.
- **Extra fingers / wrong limb count**: add an explicit anatomy clause: "exactly two hands, five fingers each, anatomically correct arms, no extra limbs."
- **Melted or warped objects**: name the object's material and rigidity explicitly ("rigid aluminum bottle with crisp edges").

**Retry cap:** 2 regeneration attempts per variant (3 total including the first). If defects remain, stop, show the best attempt, and ask the user how to proceed.

## Out of scope, fail clearly

- Meta upload: meta-ad-launcher (creates everything paused; activation needs explicit human confirmation).
- Ad copy: human-ad-copy.
- Video, carousel, DCO: image only.
- gpt-image-2 generation: chatgpt-image-ad.
- Adding templates to the library: image-ad-clone.
