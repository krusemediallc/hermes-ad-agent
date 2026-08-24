# image-ad-clone method guide: reverse-engineer an existing ad into a reusable template

This is the full teardown-and-generalization method behind the image-ad-clone skill. The workflow is model-agnostic through the generalization step; the backend choice (gpt-image-2 vs nano-banana-2) happens up front and only affects which Arcads MCP generation tool validates the template.

Companion files in this folder:
- `prompt-library.md`: destination for new entries (37 seeded templates, T1-T39 with intentional gaps at T16/T22).
- `template-format.md`: the entry skeleton.
- `safety-suffixes.md`: the three always-on prompt guards.

## Hard rules, never relax

1. **Strip platform and screenshot chrome from the analysis.** Describe the actual ad creative, not the screenshot wrapper. Ignore iOS status bars, "Sponsored" or "Saved" badges, surrounding post text, link-card footers, engagement rows, and tab bars. If the reference is an ad-in-feed screenshot, mentally crop the wrapper. The template must produce a standalone image that would be uploaded as a Meta creative.
2. **Always validate by generating.** A template that has not been round-tripped through the chosen model against the original is not validated. Run at least one generation with the original as a reference image and compare. Refine until the structure matches.
3. **Always test the generalized version.** Before saving, fill the placeholders with a **different** brand and generate again. If the structure breaks, the placeholder set is wrong; fix it.
4. **Never write brand-specific text into the final template.** Wordmarks, product names, slogans, specific photographs, source-brand hex colors: all become `{placeholders}`. Only structural content (layout descriptions, photography style, typography family feel, composition rules) stays literal.
5. **Append, never silently overwrite.** If a new tag collides with an existing library entry, ask the user before replacing.
6. **Document Model notes for both backends when possible.** Even if the user only cares about one backend today, a "gpt-image-2: clean / nano-banana: weak on small text" note saves the next run from picking the wrong backend. If only one backend was validated, say so explicitly.

## Inputs the user must provide

| Input | Notes |
|---|---|
| Reference ad image | A local file (PNG/JPG/WEBP) or an image shared in chat. The thing being reverse-engineered. |
| Test brand (optional) | Which brand the Phase 4 test fill should use. Default: the user's own brand from BRAND.md, otherwise a plausible fictional brand. |
| Template tag (optional) | Short identifier like `T40`; propose one from the analysis if not given. |

## Phase 2 in depth: visual analysis checklist

This is the most important phase. View the reference image (or run `arcads_analyze_media` on it) and document each of these, structurally separating brand-specific content from format and structure:

- **Aspect ratio.** Measure or estimate W:H. Map to the nearest ratio the Arcads MCP accepts (`1:1`, `16:9`, `9:16`) and note the crop if the native ratio differs.
- **Format type.** What the ad pretends to be: editorial article, product flatlay, comparison table, fake search results, story composite, native UI mimic, and so on.
- **Layout structure.** Header / hero / footer / grid; how regions are arranged, in vertical order.
- **Typography.** Family feel (geometric sans, condensed sans, serif, handwritten marker, monospace), weight, hierarchy. Do not name specific fonts unless iconic and necessary; describe the feel.
- **Color palette.** 3-6 hex guesses. Mark which are brand-specific (become `{brand.color_*}` variables) vs neutral or structural (white/black/grey backgrounds stay literal).
- **Photography style.** Studio flatlay, lifestyle UGC, editorial portrait, stock-photo grid. Describe lighting and lens.
- **Text content, verbatim.** Every visible string. Mark which strings are brand-specific vs structural (labels like "AS SEEN ON" or "VS" are structural).
- **Decorative and non-text elements.** Icons, divider lines, badges, emoji, hand-lettering, props.
- **Branded vs structural.** The key column: mark every piece `[BRAND]` (becomes a variable) or `[STRUCTURE]` (stays literal).
- **Chrome to strip.** Anything that is a screenshot or platform artifact; note it for explicit exclusion in the prompt.

State this analysis to the user as a compact summary before moving on.

## Drafting the faithful v1 prompt

Write a prompt that, paired with the original as a reference image, would reproduce the ad faithfully. Leave brand-specific content **literal** at this stage; do not placeholder-ize yet.

Structure the prompt with these sections (omit any that do not apply):
- Aspect ratio + canvas (for example "1:1 static ad creative, 1080x1080, edge-to-edge")
- Background description
- Header section (top X% of the image)
- Main content / hero section
- Decorative elements (badges, dividers)
- Bottom section / footer band
- Typography note (weight, family feel, hierarchy)
- Composition and spacing rules
- **Explicit chrome exclusion**: name what NOT to render. The appended no-chrome suffix is a safety net; the prompt itself should also exclude chrome explicitly.

Show the v1 prompt to the user.

## Compare and iterate

After each validation generation, compare against the original and identify deltas: layout regions misplaced or missing, typography weight wrong, aspect-ratio misread, brand color drifted, decorative elements wrong or missing. Refine the prompt from the deltas and regenerate. **Cap at 4 iterations**; beyond that the prompt has a structural problem and needs dramatic editing, not tweaking.

## Generalizing into placeholders

Walk back through the faithful prompt and replace every `[BRAND]`-marked element with a `{placeholder}`.

**Standard variables** (use these names where they fit):
- `{brand.name}`: wordmark text
- `{brand.color_primary}`: primary brand color hex (for example `#1A4731`)
- `{brand.color_accent}`: secondary accent color hex
- `{brand.product_image_description}`: one-line description of the product visible in the ad
- `{brand.tagline}`: short brand promise
- `{brand.competitor_category}`: for comparison templates, what is being compared against
- `{ad.headline}`: top-line headline copy
- `{ad.subcopy}`: sub-headline / supporting copy
- `{ad.body}`: primary text block
- `{ad.cta_phrase}`: CTA button text

**Template-specific variables**, named clearly when needed: `{checklist_items[]}` (Notes-style), `{tweet_body}` (story templates), `{rows[]}` (comparison templates), `{publication}` (editorial templates), `{ugc_subject}` (UGC composites).

For each variable, write a one-line description of what it represents and what kind of value goes in it.

## Testing the generalized template

Fill every placeholder with the test brand's values and generate again, with the reference image set to the test brand's product photo (NOT the original ad). The output should:
1. Keep the same layout and composition as the original.
2. Show the test brand instead of the source brand.
3. Read as a coherent ad, not a frankenstein.

If the test fails, the structure breaks under different brand assumptions: return to the generalization step and refine the placeholder set. Often the fix is adding a placeholder that was missed (for example a hardcoded font feel that was actually brand-specific).

## Cross-model validation

When time and credits permit, run the same filled template through the other backend and record the deltas in the Model notes block:

```markdown
**Model notes:**
- **gpt-image-2:** clean, strong on the table text
- **nano-banana:** table text blurs at small row height; reduce rows or use gpt-image-2
```

If only one backend was validated:

```markdown
**Model notes:**
- **gpt-image-2:** validated clean (see example path)
- **nano-banana:** untested, validate before using on this backend
```

## Documenting and saving

Compose the library entry per `template-format.md`: tag + one-line title, when-to-use, aspect ratio (with crop note if the design ratio is not natively supported), reference-image guidance, variable schema, the template prompt in a fenced block, the example fill from the test run, Model notes, and the validated-example path. Append it to `prompt-library.md` (ask before overwriting any collision), save the validated images under `outputs/image-ad-clone/<tag>/` in the workspace, and tell the user the template is now available to both generator skills, subject to the Model notes recommendation.

## Naming convention

The seeded library holds T1-T39 (with intentional gaps at T16/T22); new templates continue at T40, T41, and so on. Add a semantic suffix: `T40 - Lifestyle hero`. Keep the `T<n>` part for cross-skill referencing. Pick a noun phrase that describes the format, not the source brand's content.

## Out of scope

- Generating real ads or uploading to Meta: the generator skills and meta-ad-launcher handle that (Meta entities are always created paused; activation needs explicit human confirmation).
- Reverse-engineering video ads: image only.
- Multi-template extraction in one run: one reference, one template.
- Revising an existing entry: treat it as a new run pointed at the same entry; show the diff and ask before overwriting.
