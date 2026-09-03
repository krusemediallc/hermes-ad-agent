---
name: human-ad-copy
description: Writes and revises specific, natural direct-response ad copy for Meta (Facebook and Instagram) without generic AI-writing habits, then hands the finished set directly to the meta-ad-launcher skill. It builds a claim ledger before drafting, selects from 15 direct-response frameworks, enforces a hard no-em-dash rule, screens for known AI tells, and produces the standard Meta liquidity set of 5 primary texts, 5 headlines, and 3 descriptions. Use it for every request to write Meta primary text, body copy, hooks, headlines, titles, descriptions, or copy variants, and whenever the user says things like "write the ad copy", "give me 5 primary texts", "humanize this", "this sounds like AI", "make it not sound like a robot", "de-slop this", "check this copy for AI tells", or "write this with one of the frameworks". Also run it as the final pass on any copy another skill produced before it goes to meta-ad-launcher.
---

# Human ad copy

Write copy that earns attention through a real observation, useful detail, or
checkable claim. Do not try to "beat" AI detectors. Authorship detectors are
unreliable, and no wording pattern proves who or what wrote a passage. This
skill is an editorial system for removing generic patterns that readers often
associate with low-effort generated copy.

**Hard requirement (operator mandate): never use em dashes (`—`) in ad copy.**
This applies to every primary text, headline, description, hook, and draft,
with no exceptions. Rewrite with a period, comma, colon, or a split sentence.
The bundled validator treats any em dash as a HARD failure that blocks handoff.

## When to use

- Any request for Meta ad copy: primary texts, headlines, descriptions, hooks,
  variants, or a full launch-ready set.
- Revising copy that "sounds like AI", needs humanizing, or needs a de-slop pass.
- The final copy pass before the meta-ad-launcher skill creates ads.

## Required inputs

Before drafting, identify:

- Offer: product, price or terms, mechanism, and destination.
- Audience: situation, awareness level, pain, desired outcome, and objections.
- Creative: what the image or video already communicates.
- Voice: supplied brand guidance or representative approved copy.
- Receipts: verified numbers, dates, names, features, demos, quotes, results,
  constraints, and failures.
- Action: the one thing the reader should do.

**Read the user's BRAND.md first.** It carries the brand voice, offer facts, and
approved claims that feed the ledger below. If BRAND.md is missing, offer to run
the brand-setup skill before drafting. You can draft without it, but say so and
mark every brand-dependent fact as unverified.

Ask only for missing facts that materially change the copy. If a draft can
proceed with placeholders, use explicit brackets such as `[verified result]`.
Never turn an assumption into a claim, and never fabricate a performance number.
Only report metrics that came from the user, BRAND.md, or a Meta tool result (MCP or CLI).

## Workflow

### 1. Build a claim ledger

List each material claim and its source before writing. A receipt can be a
measured result, product specification, named source, customer quote, screenshot,
demo, policy, price, or dated event.

- Keep verified claims.
- Mark claims that still need evidence.
- Cut claims that cannot be checked.
- Preserve testimonials verbatim apart from approved typo fixes. Never invent a
  customer, quote, statistic, deadline, scarcity condition, or endorsement.

Specificity is not decoration. A precise unsupported number is still false.

### 2. Choose genuinely different angles

Read [the 15 direct-response frameworks](references/frameworks.md), then match
frameworks to the available receipts and the creative. One framework is enough
for one ad. A variant set should test different bets, not synonyms.

Change at least two of these between primary-text variants:

- reader problem or awareness level
- opening mechanism
- proof or receipt
- objection
- framework
- call to action

Do not label five paraphrases as five concepts.

### 3. Draft in plain language

Apply these defaults:

1. Lead with the pain, result, observation, or receipt. Skip scene-setting.
2. Prefer plain verbs such as `is`, `has`, `uses`, `built`, `tested`, and `saved`.
3. Give every material benefit a mechanism or proof point.
4. State the positive claim directly. Avoid negative rhetorical seesaws.
5. Never use em dashes. This is a permanent operator mandate, not a style
   preference.
6. Vary sentence and paragraph length naturally. Fragments are allowed when
   they fit the brand voice.
7. Avoid mechanically balanced triads, identical bullet shapes, and repeated
   CTA syntax.
8. Repeat the natural product name instead of inventing elegant synonyms.
9. Admit real constraints when relevant. Do not manufacture flaws to sound human.
10. Replace generic adjectives with facts, not different generic adjectives.

Read [the AI-tell editorial rules](references/ai-tells.md) before the final pass.
These are heuristics and house rules, not evidence of AI authorship.

### 4. Fit the Meta fields

These are creative guidelines, not universal platform limits. Placements and
rendering can vary.

- **Primary text**: put the hook or proof in the opening line. Roughly 125
  characters often appear before expansion, but long primary text is valid.
- **Headline**: aim for about 40 characters or fewer. Make it concrete enough
  to work with any primary text in the set.
- **Description**: aim for roughly 30 to 50 characters. Use a supporting fact,
  term, or mechanism rather than a second headline.
- **Liquidity set**: default to 5 primary texts, 5 headlines, and 3
  descriptions when preparing a launch-ready set for meta-ad-launcher.

All headlines and descriptions should pair truthfully with all primary texts
because Meta may mix them. Do not rely on a description to carry required
context.

### 5. Validate mechanically

Always run the bundled validator when a terminal is available. It is plain
`python3` with the standard library only, no packages, no network, no keys.
The script lives inside this skill folder at `scripts/validate_copy.py`
(absolute path: `${HERMES_SKILL_DIR}/scripts/validate_copy.py`, typically
`~/.hermes/skills/human-ad-copy/scripts/validate_copy.py`).

The validator accepts plain text for a single draft, or JSON for a full set.
For the full-set check, write the set to a temporary `copy.json` in exactly
this shape, because that is the structure the validator parses:

```json
{
  "bodies": ["primary text 1", "primary text 2"],
  "titles": ["headline 1", "headline 2"],
  "descriptions": ["supporting line 1"]
}
```

`bodies` holds the primary texts, `titles` the headlines. Titles and
descriptions may also use the supported `{"text": "..."}` form, while bodies
must be strings. For a launch set, use 5/5/3. This JSON file is a validation
artifact only; the user-facing deliverable is the markdown handoff block below,
unless the user explicitly asks for JSON.

Run:

```bash
python3 "${HERMES_SKILL_DIR}/scripts/validate_copy.py" draft.txt
python3 "${HERMES_SKILL_DIR}/scripts/validate_copy.py" copy.json
python3 "${HERMES_SKILL_DIR}/scripts/validate_copy.py" copy.json --output json
```

Finding levels:

- `HARD`: deterministic contract failure, including an em dash, invalid JSON
  shape, empty value, or exact duplicate variant. Fix before handoff.
- `REVIEW`: heuristic editorial cue, lexical near-duplicate, unsupported-claim
  cue, or count/length guidance. Inspect in context.

Exit code `1` means hard findings exist. Review-only findings return `0`.
CLI or unreadable-input errors return `2`. A clean scan does not certify human
authorship or guarantee performance.

**If no terminal is available in your session**, apply the full checklist in
[references/ai-tells.md](references/ai-tells.md) manually: scan every variant
for em dashes, exact duplicates, canned phrases, generic vocabulary, negative
parallelism, unsupported-claim cues, and length guidance. Then state plainly in
your handoff that the mechanical validator was not run and the checklist was
applied by hand.

### 6. Make the judgment pass

The scanner cannot reliably judge truth, voice, rhythm, semantic paraphrase, or
strategic fit. Read the set aloud and ask:

- Does the first line earn the second?
- Could this sentence describe ten unrelated offers?
- Is each claim traceable to a receipt?
- Would a real customer or operator use these exact words?
- Does each variant test a different reason to act?
- Does the CTA match the destination and creative?

## Output contract: handoff to meta-ad-launcher

The deliverable of this skill is a structured markdown block that the
meta-ad-launcher skill consumes directly when it builds the ad (always in
PAUSED status, with its own human confirmation gates). Produce it in exactly
this shape:

```markdown
## Ad copy handoff

**Offer / destination:** [product and landing URL or destination]
**Call to action type:** [for example LEARN_MORE, SHOP_NOW, SIGN_UP]

### Primary texts
1. [primary text 1]
2. [primary text 2]
3. [primary text 3]
4. [primary text 4]
5. [primary text 5]

### Headlines
1. [headline 1]
2. [headline 2]
3. [headline 3]
4. [headline 4]
5. [headline 5]

### Descriptions
1. [description 1]
2. [description 2]
3. [description 3]

### Validation
Validator: [PASS / FAIL / not run, checklist applied manually]
Hard findings: [count] | Review findings: [count and one-line disposition]

### Claims to verify
- [only when unverified claims remain; otherwise omit this section]
```

Keep unverified notes outside the copy itself. Only produce a `copy.json` file
as the deliverable when the user asks for JSON; otherwise JSON exists only as
the temporary validator input. When no launch is planned and the user just
wants copy, use the same labeled structure without the handoff framing.

## Pitfalls

- Do not hand off a set with any HARD finding outstanding.
- Do not "fix" a flagged generic word by swapping in a synonym; add a receipt.
- Do not invent testimonials, statistics, deadlines, or scarcity.
- Do not report or imply performance numbers that no MCP tool or user provided.
- Do not let five variants make the same argument in different words.

## Rewrite examples

Illustrative facts below are placeholders, not claims to reuse.

Generic:

> Unlock a seamless way to transform your workflow and achieve powerful results.

Specific:

> Thursday's report took 47 minutes because three CSV exports broke. This tool
> pulls the same fields into one sheet, then flags the rows that failed.

Paraphrase set:

> Build reports faster.
>
> Create reports in less time.
>
> Speed up every report.

Angle set:

> The 47-minute export failure, told as an operator story.
>
> A side-by-side count of the old and new steps.
>
> The security reviewer's objection, answered with the actual data flow.
