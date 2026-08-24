# gpt-image-2 prompting guide (chatgpt-image-ad)

Model-specific brain for generating standalone Meta ad creatives with **ChatGPT Image 2** (`gpt-image-2`) through the Arcads MCP server.

The shared template library (37 validated ad-format templates with per-model notes) ships with the **image-ad-clone** skill; when installed it lives at `~/.hermes/skills/image-ad-clone/references/prompt-library.md`. Check it before composing a fresh prompt.

## What gpt-image-2 is good at

Pick this skill (over nano-banana-image-ad) when the ad's success depends on any of these:

- **Dense text fidelity**: table rows, chat bubbles, ChatGPT-response panels, comment threads, Slack messages, comparison tables, Apple Notes lists, weather and forecast UI, fake search results pages.
- **UI mimicry**: iOS dialogs, iMessage threads, AirDrop modals, Google search pages, Slack conversations, Apple Notes / Calendar / Weather, dating-app cards. gpt-image-2 reproduces these patterns faithfully.
- **Logo and wordmark legibility**: publication wordmarks, brand wordmarks, small-caps subheads, monospace numbers.
- **Typography-led layouts**: brutalist big-statement hero quotes, magazine mastheads, editorial article heroes, condensed-sans hero stats.
- **Diagrammatic layouts**: flowcharts, stacked-bar comparisons, calendar timelines, annotated callouts with arrows.

## What gpt-image-2 struggles with

If any of these are core to the ad, prefer **nano-banana-image-ad** instead:

- **Photoreal handheld objects**: held-up whiteboard signs, handwritten napkin testimonials, flatlay product photography with rich material rendering (leather + metal + fabric textures side by side).
- **Aspirational lifestyle photography**: full-bleed scenic backgrounds with naturalistic lighting.
- **Stop-motion / claymation / Pixar / clay textures**: anything needing material-based realism.
- **Subject continuity across many references**: nano-banana takes up to 14 reference images; gpt-image-2 caps at 5 and blends them less smoothly.

## Hard limits (Arcads MCP)

1. **Model is `gpt-image-2`.** Locked; it beats `gpt-image` for text fidelity.
2. **Max 5 reference images** per call (more returns `400 Max 5 reference image(s) allowed`), passed as uploaded `filePath` values.
3. **Aspect ratios: `1:1`, `16:9`, `9:16` only.** Templates designed for `4:5`, `2:3`, or `3:2` render at `1:1` (or `9:16` for tall content) and get cropped downstream before upload.
4. **No platform/screenshot chrome** in output (the no-chrome suffix is always on unless the concept genuinely requires simulated chrome and the user agrees).
5. **Edge-safe rule always on**: text and focal subjects inside the central 84% of the canvas.
6. **Glyph-safety rule always on**: plain words inside body-text blocks; emoji OK in headlines.
7. **Two-column comparison prompts must state BOTH columns' values explicitly** or the model duplicates one set into both columns.

## Composing the prompt

When writing or completing a prompt, anchor on:

- **Subject and pose**
- **Lighting and time of day**
- **Lens / framing**
- **Color palette / mood**: pull from BRAND.md.
- **Composition**: rule of thirds, leading lines, regions described in vertical order (top X%, middle, bottom).
- **Negative space for text overlay** if the ad carries headline or body copy.
- **Reference roles**: if references are passed, name each one's role explicitly ("the product in image 1", "the brand wordmark from image 2"). Multi-reference quality improves when each reference is labeled.
- **Standalone-creative scope**: never describe iOS chrome, Sponsored badges, engagement counts, or platform UI. The no-chrome guard catches violations, but write the prompt as if the rule is on you.
- **gpt-image-2 strengths to lean on**: explicit typography (font weight and size feel), UI proportions ("iOS dialog with rounded corners, about 24px radius"), small-text body content treated as exact strings, exact element counts ("EXACTLY THREE message rows").

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

Common gpt-image-2 defects and their fixes:
- **Garbled small text**: "Render <specific text block> at LARGE size, occupying at least 25% of the canvas height. Plain English words only, no glyph artifacts." Fewer words beats more rules.
- **Wrong element count** (asked for 3 Slack messages, got 4): explicit count, for example "EXACTLY THREE message rows, no fourth row, no scroll cutoff at the bottom."
- **Wordmark drift**: pass the actual wordmark file as a reference image AND name it in the prompt ("the brand wordmark from image 1").
- **UI proportion drift** (iOS dialog too small): "The iOS dialog occupies the central 70% of the canvas width."
- **Duplicated comparison columns**: restate both columns' values explicitly, item by item.

**Retry cap:** 2 regeneration attempts per variant (3 total including the first). If defects remain, stop, show the best attempt, and ask the user how to proceed.

## Out of scope, fail clearly

- Meta upload: meta-ad-launcher (creates everything paused; activation needs explicit human confirmation).
- Ad copy: human-ad-copy.
- Video, carousel, DCO: image only.
- Nano Banana generation: nano-banana-image-ad.
- Adding templates to the library: image-ad-clone.
