---
name: human-ad-copy
description: Writes and revises specific, natural direct-response ad copy for Meta (Facebook and Instagram) without generic AI-writing habits, then hands the finished set directly to the meta-ad-launcher skill. It builds a claim ledger before drafting, selects from 15 direct-response frameworks, enforces a hard no-em-dash rule, screens for known AI tells, and produces the standard Meta liquidity set of 5 primary texts, 5 headlines, and 3 descriptions that live inside one flexible ad unit per media asset, presented verbatim for explicit approval before the launcher binds it to a content hash. Use it for every request to write Meta primary text, body copy, hooks, headlines, titles, descriptions, or copy variants, and whenever the user says things like "write the ad copy", "give me 5 primary texts", "humanize this", "this sounds like AI", "make it not sound like a robot", "de-slop this", "check this copy for AI tells", or "write this with one of the frameworks". Also run it as the final pass on any copy another skill produced before it goes to meta-ad-launcher.
---

# Human ad copy

Write copy that earns attention through a real observation, useful detail, or
checkable claim. Do not try to "beat" AI detectors. Authorship detectors are
unreliable, and no wording pattern proves who or what wrote a passage. This
skill is an editorial system for removing generic patterns that readers often
associate with low-effort generated copy.

**Hard requirement (operator mandate): never use em dashes (U+2014) in ad copy.**
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

**Resolve the workspace root, then read the user's BRAND.md.** The workspace
root is recorded in the pack's setup-state file,
`$HERMES_HOME/hermes-ad-agent/setup-state.json` (fallback
`~/.hermes/hermes-ad-agent/setup-state.json`; on Hostinger managed Hermes
`HERMES_HOME` is `/data`). Read its `workspace_root` and open `BRAND.md` there.
Do not assume the current directory is the workspace, and do not rely on a path
mentioned earlier in the conversation. If the file is missing, ask the user for
the workspace root and suggest re-running setup so the next session can find it.
BRAND.md carries the brand voice, offer facts, and approved claims that feed the
ledger below. If BRAND.md is missing, offer to run the brand-setup skill before
drafting. You can draft without it, but say so and mark every brand-dependent
fact as unverified.

**Check the account memory next.** If `memory/accounts/act_<ACCOUNT_ID>.md`
exists at the workspace root for the connected ad account (the
`account-audit` skill writes one per account), read its "## Top Performers"
and "## Creative and Copy Inventory" sections for proven angles, hooks, and
phrasing patterns to draw on. The memory informs style and angle only.
Claims still come only from the claim ledger built from BRAND.md and the
user: a line of winning copy is not a receipt, and nothing from the memory
file enters the copy as a claim.

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
  descriptions when preparing a launch-ready set for meta-ad-launcher. The
  whole pool goes into one flexible ad unit per media asset; it is never
  split into five ads.

All headlines and descriptions should pair truthfully with all primary texts
because Meta may mix them. Do not rely on a description to carry required
context.

### 5. Validate mechanically

Always run the bundled validator when a terminal is available. It is plain
`python3` with the standard library only, no packages, no network, no keys.
The script lives inside this skill folder at `scripts/validate_copy.py`
(absolute path: `${HERMES_SKILL_DIR}/scripts/validate_copy.py`, which resolves
under `$HERMES_HOME/skills/human-ad-copy/`; on Hostinger managed Hermes that is
`/data/skills/human-ad-copy/scripts/validate_copy.py`, on a default install
`~/.hermes/skills/human-ad-copy/scripts/validate_copy.py`). Never hard-code
`~/.hermes`; if `HERMES_SKILL_DIR` is unset, locate the skills directory from
`$HERMES_HOME` or `hermes config path` (verify with `--help` on your build).

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

**Show every REVIEW finding to the user, never swallow it.** An exit code of
`0` is not a clean bill: the validator still prints review findings (near
duplicates, unsupported-claim cues, length guidance), and a set was once
handed off with those warnings hidden behind "validator passed". Copy each
review finding, verbatim or in a one-line paraphrase that keeps the flagged
text, into the Validation section of the handoff block together with what you
did about it (fixed, kept on purpose with a reason, or left for the user to
decide). The user approves the copy with those warnings in view.

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
PAUSED status, with its own human confirmation gates).

Three rules govern the block:

1. **One ad unit, not five ads.** The 5 primary texts and 5 headlines (and 3
   descriptions) live inside ONE ad unit: one flexible creative per media
   asset, built with `asset_feed_spec` (or the Meta Ads CLI's repeated
   `--bodies` / `--titles` / `--descriptions` flags), so Meta rotates the
   variants within that single ad. Never five separate ads, one per primary
   text. The launcher must not silently reduce the set to one variant and must
   not multiply the ad count; if its backend cannot build the flexible unit,
   it blocks before creating anything and gives the user the choice. Write the
   handoff so that intent is unmistakable: the block below describes one ad
   per media asset carrying the whole pool.
2. **Present the block verbatim and get explicit approval.** Show the user the
   complete handoff block exactly as written: every primary text, headline,
   description, the CTA type, the destination, and which media asset each
   pairs with. Do not summarize it, and do not treat "looks good", "get these
   built", or a timed-out approval form as approval of copy the user never saw
   in full. Ask a direct question ("Approve this copy set as shown?") and wait
   for a yes that refers to this exact block.
3. **Approval is bound to a content hash.** The meta-ad-launcher skill
   computes a sha256 of the canonical pool text of the approved block
   (`python3` with `hashlib`, or `shasum -a 256`) and stores only that hash
   plus a short approval note in the run ledger, never the copy itself. Any
   edit to any field afterwards, even fixing one word, produces a new version
   with a new hash that needs its own approval. So finish all edits before
   asking, and after approval hand the block over unchanged. If the user asks
   for a change after approving, produce the revised block in full, present it
   verbatim again, and say plainly that the earlier approval no longer
   applies.

Produce the block in exactly this shape:

```markdown
## Ad copy handoff

**Offer / destination:** [product and landing URL or destination]
**Call to action type:** [for example LEARN_MORE, SHOP_NOW, SIGN_UP]
**Media pairing:** [which image or video file(s) this pool attaches to]
**Ad structure:** one flexible ad unit per media asset carrying all 5 primary
texts, 5 headlines, and 3 descriptions (asset_feed_spec), not separate ads

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
Hard findings: [count, must be 0 at handoff]
Review findings: [count]
- [each review finding, with the flagged text and your disposition]

### Claims to verify
- [only when unverified claims remain; otherwise omit this section]

### Approval
Version: [1, 2, ... incremented on every edit]
Approved as shown: [pending / yes, with the user's words]
```

Keep unverified notes outside the copy itself. Only produce a `copy.json` file
as the deliverable when the user asks for JSON; otherwise JSON exists only as
the temporary validator input. When no launch is planned and the user just
wants copy, use the same labeled structure without the handoff framing.

The hash itself is computed by the launcher at ledger time, not by this skill,
so do not print one here; what this skill guarantees is that the approved
block is complete, verbatim, and unchanged after the user's yes.

## Pitfalls

- Do not hand off a set with any HARD finding outstanding.
- Do not hide REVIEW findings behind "validator passed"; list them in the block.
- Do not hand off copy the user has not seen in full, and do not take a
  general "go ahead" as approval of a block that was never shown verbatim.
- Do not edit approved copy on the way to the launcher; any change is a new
  version that needs a new approval.
- Do not describe the set as five ads. It is one flexible ad unit per media
  asset with the whole pool inside it.
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
