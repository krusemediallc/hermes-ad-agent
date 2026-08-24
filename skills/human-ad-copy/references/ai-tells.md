# AI-tell editorial rules for direct-response copy

This is a style and quality catalog, not an authorship test. Humans use every
pattern listed here, and generated text can avoid all of them. A hit means
"inspect this line," not "AI wrote this." The useful signal is usually a cluster
of generic choices replacing facts.

The stable editorial problem is regression toward generic language:

1. A specific fact gets replaced by an abstract benefit.
2. The abstract benefit gets inflated with polished vocabulary.
3. Parallel sentence structures make thin material sound complete.

The reliable fix is a receipt, not a synonym.

## Finding levels

The bundled validator (`scripts/validate_copy.py` in this skill folder) uses
two levels:

- `HARD` means an objective violation of this skill's output contract: em dash,
  malformed `copy.json` payload, empty value, or exact duplicate variant.
- `REVIEW` means a context-dependent cue: generic vocabulary, canned phrase,
  negative parallelism, vague claim cue, lexical similarity, or guidance miss.

Hard does not mean "certainly AI." It means the draft violates a declared rule.
Review-only runs exit successfully so editorial judgment remains with the user.

When no terminal is available to run the validator, this file is the manual
checklist. Work through every section against every variant, and say in the
handoff that the check was done by hand.

## 1. Generic vocabulary

These words often carry tone without information. They are review cues because
many have legitimate literal uses.

| Cue | Better editorial question |
|---|---|
| delve, deep dive | What exact topic or step follows? |
| crucial, pivotal, vital | What changes if the reader ignores it? |
| seamless, effortless, frictionless | Which click, wait, export, or handoff disappeared? |
| unlock, unleash, elevate, empower, supercharge | What does the product actually do? |
| game-changing, revolutionary, groundbreaking, transformative | What changed, for whom, and by how much? |
| cutting-edge, next-level, future-proof | Which capability or version supports this? |
| leverage, utilize, harness | Would `use` name the action more clearly? |
| landscape, realm, ecosystem, space | What market, account, tool, or workflow? |
| tapestry, testament, underscore | Can the sentence state the fact directly? |
| journey | What sequence of events actually happened? |
| robust, comprehensive, holistic | What is included, excluded, or tested? |
| meticulous, intricate | Which detail or quality check matters? |
| foster, garner, bolster | What observable action occurred? |
| streamline, optimize the workflow | Which step got faster, and by how much? |
| showcase, boasts, serves as, stands as | Can the copy use `shows`, `has`, or `is`? |
| actionable insights, valuable insights | What is the takeaway or next action? |

Do not turn `seamless` into `smooth` and leave the sentence unchanged.

Weak:

> Seamlessly streamline your content workflow.

Specific:

> Approve all 12 drafts from one screen. Rejected drafts keep the editor's note.

## 2. Canned phrases

These phrases are common in generated marketing drafts because they supply
familiar shape without product knowledge:

- `In today's fast-paced world`
- `In an ever-evolving landscape`
- `Look no further`
- `We've got you covered`
- `Say goodbye to X`
- `Say hello to Y`
- `The possibilities are endless`
- `Take your X to the next level`
- `Unlock your potential`
- `Designed to empower`
- `Whether you're a beginner or an expert`
- `Imagine a world where`
- `Ready to transform your X?`
- `Here is the truth`
- `The best part?`
- `The result?`

Usually the whole phrase can be deleted. If the remaining sentence says
nothing specific, the missing input is a receipt.

## 3. Sentence-shape cues

### Negative parallelism

Common forms:

- `It is not just X, it is Y.`
- `Not only X, but also Y.`
- `It is not about X. It is about Y.`
- `No X. No Y. Just Z.`
- `More than just X.`
- `This is not another X.`

The contrast can be valid, but repeated rhetorical seesaws are a strong
low-information pattern. State the supported positive claim:

Weak:

> This is not another dashboard. It is your complete growth ecosystem.

Specific:

> The dashboard shows spend, approved assets, and failed imports for each account.

### Rule of three

Exactly three adjectives, benefits, or parallel fragments can be intentional.
Repeated triads make a whole variant set feel mechanically complete. Cut to the
two strongest items, add a real fourth item, or make the structure uneven. Do
not change the number solely to imitate human writing.

### Participle tails

Watch for a comma followed by:

- `ensuring`
- `enabling`
- `allowing you`
- `helping you`
- `showcasing`
- `highlighting`
- `empowering`

These endings often glue an unsupported benefit onto an otherwise factual
sentence.

Weak:

> It syncs the file nightly, ensuring your team always has accurate insights.

Specific:

> It syncs the file at 2 a.m. Failed rows appear in an error report with the
> source ID.

### Rhetorical question pivots

`The result?`, `The best part?`, `The catch?`, and `The difference?` imitate
punchy social copy. State the answer unless the brand genuinely uses this
rhythm.

### Copula avoidance

`Serves as`, `stands as`, `acts as`, `represents`, `offers a`, and `features a`
often replace simpler language. `Is` and `has` are useful words.

### Uniform rhythm

Five sentences with similar length and syntax feel generated even when each is
clean alone. Mix lengths when the thought calls for it. A fragment can help.
Do not add typos, slang, or random punctuation to simulate a person.

### Elegant variation

Calling one product `the platform`, `the ecosystem`, `the solution`, and `the
digital companion` creates distance. Repeat the product's natural name.

## 4. Unsupported-claim cues

A mechanical scanner cannot know whether a claim is supported. It can flag
language that needs a source or narrower wording:

- `Experts say` or `industry leaders agree`
- `Studies show`, `research proves`, or `data suggests` without a named source
- `Trusted by thousands` without a defensible count
- `Proven results`, `guaranteed success`, or `clinically proven`
- `The best`, `leading`, `number one`, `the only`, or similar superlatives
- `Up to 70%`, `3x`, or another performance figure without scope and baseline
- `Customers love` or `professionals recommend` without attributable evidence
- `Widely regarded`, `recognized everywhere`, or other vague consensus

Treat the flag as a request for a claim record:

1. Exact wording of the claim.
2. Source or artifact.
3. Timeframe and population.
4. Baseline and denominator where relevant.
5. Required qualification or disclosure.

If the evidence is absent, cut or narrow the claim. Do not hide it behind
`may`, `can help`, or `designed to`. Performance figures must come from the
user, BRAND.md, or an MCP tool result. Never invent them.

## 5. Formatting cues

### Em dash

This skill uses a no-em-dash house rule. The validator marks `—` as hard.
Use a period, comma, colon, or parentheses according to the sentence.

### Repeated bold-label bullets

This pattern becomes conspicuous when every line follows the same template:

```markdown
- **Speed:** Generate drafts faster.
- **Scale:** Produce more content.
- **Quality:** Improve every result.
```

Use ordinary sentences, or make each bullet carry a different kind of detail.

### Emoji scaffolding

An emoji can fit a real brand voice. An emoji at the start of every line often
acts as artificial structure. Remove the scaffolding before deciding whether
one meaningful emoji belongs.

### Mechanical emphasis

Review:

- boldface on every takeaway
- title case on every heading
- identical line lengths
- repeated arrows or checkmarks
- all-caps urgency without a real deadline

Formatting should reveal hierarchy, not compensate for vague content.

## 6. Variant-set cues

Each line can pass alone while the set still looks machine-made.

### Exact duplicates

Case, punctuation, or whitespace changes do not create a variant. The validator
marks normalized exact duplicates as hard.

### Lexical near-duplicates

The validator compares normalized characters and content-word overlap. It can
surface pairs such as:

> Build reports in half the time.
>
> Create your reports in half the time.

This is a review heuristic. It cannot determine semantic equivalence, and it
will miss paraphrases that use different vocabulary.

### Strategic paraphrases

These require human review:

> Stop wasting hours on weekly reports.
>
> Get your Friday afternoon back.
>
> Reporting should not take all day.

The wording changes, but all three may test the same time-saving claim. A useful
set changes the bet:

- operator story with a timestamped failure
- before-and-after step count
- objection about data access, answered with the architecture
- customer quote with permission
- offer-led description of what is included

## 7. What to write toward

- Plain `is` and `has` constructions.
- Verbs that name the action.
- Numbers with definitions and sources.
- Product names, dates, file types, steps, and visible artifacts.
- Honest constraints and failed attempts when relevant.
- A hook that matches the creative.
- Uneven but intentional rhythm.
- One clear next action.

Do not optimize for "human-looking randomness." Optimize for truth, specificity,
voice fidelity, and a real reason to care.

## Final manual sweep

The scanner cannot answer these:

- Is the claim true and properly qualified?
- Does the copy sound like this brand rather than a generic person?
- Is a flagged word literal and useful in context?
- Do two variants make the same strategic argument?
- Does the opening depend on context hidden after the first line?
- Can every headline pair accurately with every primary text?
- Does the destination fulfill the CTA?

A clean mechanical scan is the beginning of review, not certification.
