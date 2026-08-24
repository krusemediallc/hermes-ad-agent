# Library entry format

Markdown skeleton for an entry in `prompt-library.md`. Load this before composing a new entry. The library already contains T1-T39 in this format; match its style when appending so the file stays consistent for both consuming generator skills (chatgpt-image-ad and nano-banana-image-ad).

## Skeleton

```markdown
## {tag} - {one-line title}

**When to use:** {1-2 sentence positioning fit. What kind of ad is this? Who or what is it good for?}

**Aspect ratio:** `{ratio}` ({1-line why, for example "Meta feed-portrait friendly", "Stories / Reels"; if the design ratio is not natively supported on the backend, note the generate-then-crop path})

**Reference image:** {what kind of reference image to pass. Examples: "clean product hero (white background, all SKUs visible)", "lifestyle portrait of subject mid-action", "logo + product flatlay"}

**Variables:**
- `{variable_name}` - {description; what kind of value goes in it; format hint if any}
- `{variable_name}` - ...

**Template prompt:**
\`\`\`
{The full prompt text, with {placeholders} embedded. Should produce a standalone ad creative when filled and paired with the reference image. No screenshot or platform chrome.}
\`\`\`

**Example fill** ({brand_name}):
- `{variable_name}` = `{example value}`
- `{variable_name}` = `{example value}`
- ...

**Model notes:**
- **gpt-image-2:** {known strengths or limits with this template, for example "renders dense table text cleanly", "tends to add a 3rd Slack message; keep the prompt explicit about exactly N"}
- **nano-banana:** {known strengths or limits, for example "weaker on dense small text; keep body to 3 lines max", "excellent multi-reference blending; pass logo + product + style as three refs"}

Validated example: `{path/to/outputs/dir/}`

---
```

(End every entry with a horizontal rule on its own line so the next entry has visual separation.)

## Field-by-field guidance

### `{tag}`
Format `T<n> - <short noun phrase>`. Continue numbering from the existing library: T1-T39 are seeded, so the next is T40. The noun phrase is searchable; pick something describing the format, not the content ("T40 - Lifestyle hero with overlay text", not "T40 - AcmeCo morning shaker ad").

### `{one-line title}` (after the hyphen)
A short noun phrase distilling the format, 4-8 words. Examples: "Apple Notes listicle aesthetic", "Editorial article hero", "Comparison table (dark, hooky)".

### When to use
Two ideas: who or what brand fits (product category, target-audience temperament), and which positioning angle (credibility, social proof, comparison, sentimental, and so on). Describe the gut fit, not a list of rules.

### Aspect ratio
The design intent. The Arcads MCP image tools accept `1:1`, `16:9`, `9:16` natively; a template designed for `2:3` or `4:5` should say so and note that it generates at the nearest supported ratio and gets cropped downstream. Record any per-backend rendering mismatch in Model notes so the consuming skill can route correctly.

### Reference image
Tell the future agent what kind of image to ground the generation on; the more specific the better:
- "Clean product hero shot, white background, all SKUs visible"
- "Lifestyle portrait, subject mid-action, soft daylight"
- "Logo wordmark on neutral background"
- "Existing ad in the same format" (rare, usually sub-optimal)

Reference images are how the brand identity stays faithful. Bad guidance here causes wrong-looking outputs no matter how good the prompt is.

### Variables
List every `{placeholder}` in the template prompt. For each, describe in one line: what the value represents, the expected type or format (string? hex code? list? short headline?), and any constraints (max chars, enum).

Use the standard variable names where they fit:

| Variable | Use for |
|---|---|
| `{brand.name}` | Wordmark text (the literal word or letters that appear on the packaging) |
| `{brand.color_primary}` | Primary brand color hex (`#RRGGBB`) |
| `{brand.color_accent}` | Secondary accent color hex |
| `{brand.product_image_description}` | One-line description of the product visible in the ad |
| `{brand.tagline}` | Short brand promise (6 words or fewer) |
| `{brand.competitor_category}` | What the brand is being compared against |
| `{ad.headline}` | Top-line headline |
| `{ad.subcopy}` | Sub-headline / supporting copy |
| `{ad.body}` | Primary text block |
| `{ad.cta_phrase}` | CTA button text |

For template-specific variables, name them clearly. Examples from existing entries: `{notes_title}`, `{checklist_items[]}` (T1); `{publication}`, `{photo_subject_description}`, `{tagline}`, `{band_color}` (T2); `{hook_line_1}`, `{hook_line_2}`, `{competitor_label}`, `{table_columns}`, `{table_rows[]}` (T6); `{handwritten_text_lines}`, `{sticky_note_color}` (T7).

### Template prompt
The actual prompt body, in a fenced code block, plug-and-play after substitution. Remember:
1. **Specify the aspect ratio at the top** as part of the prompt ("1:1 static ad creative, 1080x1080, edge-to-edge").
2. **Describe the canvas as standalone**: phrases like "edge-to-edge", "static ad creative", "the standalone image that would be uploaded as a Meta creative". This pairs with the appended no-chrome suffix so the output is the actual upload, not a screenshot.
3. **Explicitly exclude chrome** in a closing paragraph: "No surrounding social platform UI: no brand row, no body copy, no engagement counts, no app navigation, no iOS device chrome." The auto-suffix is a safety net; the prompt should also be explicit.
4. **Describe regions in vertical order**: top X%, middle, bottom. Helps the model lay out predictably.
5. **Name reference roles when multiple refs are expected.** "The product visible in image 1 should appear at center." Most models do better when references are addressed by index.

### Example fill
Pick a consistent test-case brand (the seeded library uses the fictional VerdantOne Daily Greens throughout) and show every variable substituted. It should be the version actually validated in the test-fill phase.

### Model notes
For each model the template was validated against (gpt-image-2 and/or nano-banana), give a one-line known-issue or known-strength note. If a template only works with one model, say so explicitly. If both render cleanly, write `both: clean`. If one backend was not tested, write "untested, validate before using on this backend."

### Validated example path
Pointer to `outputs/image-ad-clone/<tag>/`, the directory holding the locked-in prompt text, the round-1 generation against the original reference, and the final generation against the test-fill brand, so a future agent or human can audit the template's provenance.

## Style notes for matching the existing library

- Use `*italic*` for terse asides, `**bold**` only for section labels (`**When to use:**` and so on) and key callouts.
- Hex codes go in backticks: `#1A4731`.
- Do not use em-dashes; use commas, colons, parentheses, or a plain hyphen for asides.
- Wrap variables in single backticks: `{brand.name}`.
- Code-block fences use triple backticks with no language tag (prompts are not code).
- The horizontal rule between entries is `---` on its own line, separated by blank lines from neighboring content.

## Hard rules

- **Never silently overwrite an existing entry.** If the new tag collides, ask the user before replacing.
- **Append, don't reorder.** New templates go at the bottom of the library, before any "Adding new templates" or footer sections. Do not reshuffle existing entries.
- **Keep entries self-contained.** Do not reference other library entries by tag inside a template prompt. Each entry should be readable and usable on its own.
- **Validate against the model you intend to ship on.** An entry that only renders cleanly on gpt-image-2 should say so in its Model notes; do not claim portability you have not checked.
