---
name: ad-agent-orchestrator
description: >-
  The end-to-end media buyer workflow for Hermes Ad Agent. It walks a complete
  Meta ad campaign through six stages, Brief, optional Research, Create (the
  Arcads image and video skills), Copy (human-ad-copy), Launch
  (meta-ad-launcher, always PAUSED), and Monitor (meta-performance-loop and
  scheduled check-ins), telling you which skill to invoke at each stage, what
  artifact it must produce, and which safety gate applies before moving on. Use
  it when the user wants a whole campaign rather than one isolated task, for
  example "build me a campaign", "take this product from idea to ads", "make
  and launch ads for X", "run the full ad workflow", "new campaign start to
  finish", "let's test some new creative on Meta", or "pick up where we left
  off on the campaign". If the user only wants a single phase (just an image,
  just copy, just a performance report), invoke that one skill directly
  instead.
---

# Ad agent orchestrator

You are running a full ad campaign for the user. Component skills do the work
of each phase; this skill tells you the order, the artifact each stage leaves
behind, and the approval gate that must pass before the next stage starts.

Keep the process light. Sub-skills write their artifacts to their own
documented locations at the workspace root (resolved from the setup-state
file, see Stage 0); the run folder does not relocate any of them. The run
folder holds a `run-log.md` that links or paths to every artifact, the
`copy.md` you save from human-ad-copy's output, and, once the launch stage
starts, the `ledger.json` that `meta-ad-launcher` owns (the approved plan,
the copy approval hash, and every Meta ID it created). The run folder plus
the ledger is the record; the conversation is not, because it does not
survive a restart.

## The three rails

These are non-negotiable and apply at every stage. Repeat them to yourself
before any tool call or CLI command that generates media or touches Meta.

1. **Money is confirmed before it is spent.** Arcads has no quote endpoint
   and only the `creditsCharged` field in a response is cost. Before any
   Arcads generation, state the batch (model, count, duration or
   resolution), the user's plan rate if they have given one, and otherwise
   a user-defined maximum exposure for a first, explicitly unknown-cost
   calibration; wait for an explicit yes that names the count and the cap.
   No paid retry, regeneration, or QA operation (transcription, analysis,
   subtitles, editing) runs unless that approval named it. Before
   proposing any Meta budget, state the number and how it compares to the
   daily spend cap in BRAND.md, and wait for an explicit yes.
2. **Nothing delivers without a human.** Every campaign, ad set, and ad is
   created in PAUSED status, no exceptions. Never activate an entity, resume
   delivery, or change a budget or spend setting without explicit confirmation
   given in the current conversation. Approval of one action never carries
   over to another action, and never carries over from a previous session.
3. **Never invent a number.** Report only what the Meta or Arcads tools
   actually returned. No estimated results presented as measured, no
   filled-in gaps, no invented benchmarks. If a metric is missing, say it is
   missing.

## Before you start (Stage 0)

1. **Resolve the workspace root from the setup-state file.** Read
   `$HERMES_HOME/hermes-ad-agent/setup-state.json` (fallback
   `~/.hermes/hermes-ad-agent/setup-state.json`) and take `workspace_root`
   (an absolute path), plus `meta_backend` and `arcads_connected` as hints.
   If the file is missing or `workspace_root` is empty, refuse to run:
   tell the user setup is incomplete and route them to SETUP.md. Never
   take the root from the conversation, the current directory, or a guess;
   a root that lives only in chat is lost to the next session and to every
   cron job. Record the resolved root in `run-log.md`.
2. **Read `BRAND.md` at that root.** Every stage depends on it (offer,
   audience, voice, claims rules, budget guardrails, Meta assets). The gate
   is strict: if the file is missing or a required section is `(not set)`,
   offer to run the `brand-setup` skill and pause the campaign until it
   exists. The only alternative is an explicit, run-scoped override the
   user asks for by name: you list every required field (offer, destination
   URL, audience, claims allowed and banned, ad account with name and ID,
   Page, daily spend cap, PAUSED acknowledgment), the user supplies each
   one in this conversation, you write them to `brief.md` under a heading
   "BRAND.md override (run-scoped, user-approved <date>)", and you offer to
   merge them into BRAND.md when the run ends. A run-local file that
   quietly stands in for BRAND.md is a bypass, not an override; do not do
   it.
3. **Confirm both backends are live** by checking what is actually
   available. Arcads: your live tool list must contain the Arcads MCP tools
   (server-native names like `arcads_generate_image_nano_banana`,
   `arcads_watch_asset`). Meta: if the tool list contains tools whose
   names contain `ads_` (for example `ads_get_ad_accounts`,
   `ads_create_campaign`), the Meta Ads MCP server is connected; otherwise
   run `meta auth status` in the terminal and, if it reports a token,
   `meta ads adaccount list --output json`. If that returns accounts, the
   Meta Ads CLI (Meta's official command-line tool for the Marketing API)
   is configured. If both work, prefer the MCP. Note the naming rule: the
   Hermes runtime registers MCP tools under prefixed names (observed shape
   `mcp__meta_ads__ads_get_ad_accounts`, `mcp__arcads__arcads_list_products`);
   search your live tool list for the registered name and call that, and
   trust the live list and `--help` over any name written in a skill. If a
   server is configured but none of its tools are visible in this session,
   say "connected but not agent-usable" and stop rather than improvising.
   Say once which Meta backend is in use and record it in `run-log.md`. If
   Meta is missing, Research, Launch, and Monitor are blocked but Create
   and Copy still work; if Arcads is missing, Create is blocked but the
   other stages still work with creative files the user supplies. Tell the
   user either way.
4. **Create the run folder** at the workspace root:
   `ad-runs/<YYYY-MM-DD>-<campaign-slug>/`. Start a `run-log.md` inside it.
   The run folder holds what this skill writes (`brief.md`, `copy.md` saved
   from human-ad-copy's output, `run-log.md`) plus the launcher's
   `ledger.json`. `run-log.md` records links or relative paths to every
   other artifact where its sub-skill wrote it (the research brief under
   `research/`, creative files under `outputs/`, report paths). Never move
   or copy sub-skill outputs into the run folder. `ad-runs/` is gitignored
   because it holds real entity IDs.

## The campaign lifecycle

| Stage | Invoke | Artifact (and where it lives) | Gate before the next stage |
|---|---|---|---|
| 0. Account audit (onboarding, then refresh on request) | `account-audit` | `memory/accounts/act_<ACCOUNT_ID>.md` at the workspace root; link it from `run-log.md` | None to approve (the audit is read-only); Create and Copy read its learnings before generating |
| 1. Brief | this skill (you) | `brief.md` in the run folder | User confirms the brief |
| 2. Research (optional) | `competitor-ad-research` | `research/BRIEF-<date>.md` at the workspace root; link it from `run-log.md` | User selects which angles or references to carry forward |
| 3. Create | `nano-banana-image-ad`, `chatgpt-image-ad`, `image-ad-clone`, `ugc-video-ad`, `clone-video-ad`, `pixar-style-ad`, or `claymation-ad` | creative files under each skill's own `outputs/<skill>/<slug>/` folder; paths and Arcads asset IDs recorded in `run-log.md` | Credit estimate confirmed before generation; user selects the final assets |
| 4. Copy | `human-ad-copy` | `copy.md` saved into the run folder (5/5/3 pools grouped per media asset, one flexible ad unit each) | User approves the verbatim copy block, bound to its sha256 content hash |
| 5. Launch | `meta-ad-launcher` | `ledger.json` in the run folder (approved plan, run key, copy hash, every created ID with status and timestamp), summarized in `run-log.md` | User approves the exact launch plan; everything is created PAUSED and read back |
| 6. Monitor | `meta-performance-loop`, plus optional scheduled check-ins | dated performance reports where that skill writes them, linked from `run-log.md` | Any activation, pause, or budget change needs fresh explicit confirmation |

Skill names can vary by install. If a named skill is not in your installed
skills list, check `skills_list()` for the closest match (for the Create
stage, look for the skills that call the Arcads MCP generation tools) and
tell the user what you found.

### Stage 1: Brief

You own this stage directly. Pull defaults from `BRAND.md`, then confirm with
the user:

- product or offer for this campaign, and the destination URL
- objective (what a success looks like: leads, purchases, traffic)
- audience for this campaign, if it differs from the BRAND.md default
- creative direction: format (static image, UGC video, cinematic), how many
  ads, any references to imitate or avoid
- rough budget intent, checked against the BRAND.md daily spend cap

Also load the account memory: if `memory/accounts/act_<ACCOUNT_ID>.md`
exists at the workspace root for the chosen ad account (the `account-audit`
skill writes one per account at onboarding), read it now and note its path
in `run-log.md`. If it is missing and a Meta backend is live, offer to run
`account-audit` first (it is read-only); the campaign can proceed without
it, but the Create and Copy stages lose the account's learnings.

Write `brief.md` capturing the answers. **Gate:** the user confirms the brief.
Do not generate anything before this.

### Stage 2: Research (optional)

Skip when the user already knows what they want. Otherwise invoke
`competitor-ad-research`, which uses `ads_library_search` on the Meta Ads MCP
to pull competitor and category ads and summarizes hooks, angles, formats,
and offers into `research/BRIEF-<date>.md` at the workspace root. That file
stays where the research skill wrote it; add its path to `run-log.md`.

The Ad Library is not exposed by the Meta Ads CLI. On a CLI-only install this
stage is skipped, or done from reference ads the user supplies; the research
skill explains its fallbacks. Note which in `run-log.md`.

Two honesty rules: Ad Library presence and longevity suggest an advertiser
keeps running an ad, but they are not evidence of spend, conversions, or
profitability, so present findings as inspiration, not proof. And copy
nothing verbatim; research feeds angles, not plagiarism.

**Gate:** the user picks which angles or reference ads carry into the Create
stage. Record the picks in `run-log.md` alongside the brief link.

### Stage 3: Create

Invoke the installed Arcads creative skill that matches the brief:

- `nano-banana-image-ad` for photoreal or lifestyle statics
- `chatgpt-image-ad` for typography-heavy or UI-style statics
- `image-ad-clone` to adapt a specific reference image ad the user selected
- `ugc-video-ad` for talking-head or UGC video
- `clone-video-ad` to recreate a specific reference video ad the user
  selected, beat by beat, restyled for their product
- `pixar-style-ad` for 3D-animated character story ads in a family-movie look
- `claymation-ad` for stop-motion clay story ads with consistent characters

Those skills own prompt craft, generation, polling, QA, and saving files;
your job is to hand them the brief and enforce the gates.

Before any generation, read the "## Learnings for New Ads" and
"## Top Performers" sections of the account memory file loaded in Stage 1
and pass what they say along with the brief: net-new creative should build
on what the account already proved and avoid what it disproved. Skip this
only when no memory file exists.

**Gates (both live inside the creative skills; verify they happened):**

- **Credit gate:** the exact batch (model, count, duration, resolution) and
  its cost basis were shown and the user explicitly confirmed before the
  first generation call. The cost basis is the user's plan rate, or, when
  none is known, a user-defined maximum exposure for a calibration run
  whose cost is stated as unknown. Past `creditsCharged` values in the
  shared Arcads usage log at `outputs/arcads-usage-log.jsonl` (relative to
  the workspace root) are account-specific historical observations, never
  estimates; the `mp` field in responses is usage metadata, not credits.
  If the creative skill did not surface the gate, stop and do it yourself,
  and verify afterward that the log line records the actual
  `creditsCharged` and any daily-limit use per operation.
- **Dialogue gate:** for any video where a person speaks, the exact spoken
  lines were shown and approved separately before generation.
- **Selection:** after QA, the user picks which finished assets move forward.
  QA is reported by state (metadata pass, sampled-frames pass, transcript
  pass, motion or lip-sync review required, claims and branding check,
  human approval), never collapsed into "QA passed". Rejected assets stay
  in the folder but go no further; a rejection never auto-triggers a
  regeneration, and a paid QA operation runs only if the credit approval
  named it.

Artifacts: finished media files stay in each creative skill's own output
folder (`outputs/<skill>/<slug>/` at the workspace root). In `run-log.md`,
list each file's path, its Arcads asset ID, the model used, and whether the
user selected it.

### Stage 4: Copy

Invoke `human-ad-copy` with the brief, the selected creatives, and the voice
and claims sections of `BRAND.md`. Also point it at the account memory file
loaded in Stage 1; its "## Top Performers" and "## Creative and Copy
Inventory" sections inform angle and phrasing, never claims. It produces
primary text, headlines, and descriptions that sound human and stay inside
the approved claims.

Every factual claim in the copy must trace to the claims section of
`BRAND.md` or to something the user stated in this conversation. Anything
unverifiable gets a placeholder and a question, never a guess.

**The flexible-unit contract.** When the brief asks for several primary
texts and headlines (the pack's default pool is 5 primary texts, 5
headlines, and 3 descriptions), all of them belong inside ONE ad unit per
media asset: one flexible creative built with `asset_feed_spec`, from
which Meta assembles combinations. It never means five separate ads, and
it never means quietly keeping one variant. Write the pool in `copy.md`
grouped per media asset with that intent stated in the heading.

Artifact: `copy.md` in the run folder, saved by you from human-ad-copy's
output, with each pool marked with the creative it pairs with.

**Gate: verbatim approval bound to a content hash.** The approval is
demonstrated, not inferred. Show the user every primary text, headline,
description, CTA, destination URL, and media pairing verbatim in one
block, together with any validator warnings (length, banned claims,
placeholders). Then compute the pool's content hash (sha256 of the
canonical pool text, for example `python3 -c 'import hashlib,sys;
print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())' < copy.md` or
`shasum -a 256 copy.md`), show the short hash, and ask for an explicit
approval of that block. Only a clear yes to that block counts; "get these
built", "looks good", an expired approval form, or enthusiasm about the
creative is not copy approval. `meta-ad-launcher` owns the record: it
stores only the hash and a one-line approval note (who, when) in
`ledger.json`, never the copy itself, and it refuses to build if the hash
of `copy.md` at build time differs from the approved one. Any edit after
approval changes the hash and requires re-approval of the shown block.

### Stage 5: Launch

Invoke `meta-ad-launcher` with the selected creatives, approved copy, and the
brief. Before it creates anything, present the full launch plan in one block:

- ad account, Facebook Page, and Instagram identity to publish under
- campaign objective and structure (campaigns, ad sets, ads, and which
  creative and copy pair goes where)
- targeting and placements per ad set
- daily budget per ad set, explicitly compared to the BRAND.md spend cap
- destination URLs and CTA

When an account memory exists (`memory/accounts/act_<ACCOUNT_ID>.md` with
its `specs/` snapshots), `meta-ad-launcher` defaults to mirroring the
best-matching reference structure from it: exact targeting, placements,
bidding, attribution, tracking, and creative enhancement settings, with the
brief's changes layered on top and every difference from the reference
shown in the plan above. After creating, it reads each new entity back and
verifies the copy field by field, reporting any delta rather than accepting
it silently.

The plan also names, per creative, which backend will build it and why.
The Meta MCP's `ads_create_creative` takes scalar copy fields and no
`asset_feed_spec`, so it cannot build the flexible unit from Stage 4; the
Meta Ads CLI can (`meta ads creative create` with repeated `--bodies`,
`--titles`, `--descriptions` flags or `--asset-feed-spec @feed.json`, and
it uploads local files). When the chosen backend cannot build the unit the
copy pool calls for, the launcher blocks before creating anything and
gives the user the choice: switch that creative to the CLI, or explicitly
accept a single named variant for it. Neither reducing to one variant nor
multiplying the ad count happens silently. Writes go through the MCP or
the CLI only; the Graph API is never an improvised write path.

**Gate:** the user approves this exact plan. The launcher then persists
the approved plan, the copy hash, and a run key in
`ad-runs/<run>/ledger.json` BEFORE its first mutation, and creates
everything with `status: PAUSED` at every level, campaign, ad set, and ad,
recording each returned ID with status and timestamp as it goes. It must
never create anything ACTIVE, and you must never call
`ads_activate_entity` or change a status or budget through
`ads_update_entity`, or run `meta ads ... update --status ACTIVE` or
`--daily-budget` on the CLI, as part of a launch.

**Read-back assertions.** After creating, the launcher reads each entity
back and verifies field by field: copy, CTA, destination, targeting,
budget, and, for video ads, that the processed thumbnail is the video's
own frame (fetched via a preview and looked at, never another ad's
image). It then asserts the exact count of non-deleted ads and run-owned
creatives against the plan and reports any delta rather than accepting
it silently. If a call's outcome is ambiguous (timeout, "Server returned
an error response" with no ID), it reads remote state and the ledger
before doing anything else; it never re-creates on ambiguity.

Artifact: a launch section in `run-log.md` pointing at `ledger.json` and
listing every created entity ID, its status (PAUSED), and the ad preview
links if available (the MCP can fetch previews; the CLI cannot, so on
that route the user reviews the paused ads in Ads Manager by name or ID).
Tell the user everything is paused and how to review it in Ads Manager.

If anything must be retired (a wrong ad, a failed half-build), the
launcher's cleanup covers the ads AND their creatives AND uploaded media:
it shows the cleanup plan, gets a confirmation, deletes, and reads back
DELETED for each. Retiring an ad while its creative stays ACTIVE is an
incomplete cleanup; the final count assertion catches it.

If the user later asks to turn the ads on: restate exactly which entities
will go ACTIVE and what the daily budget will be, get an explicit
confirmation in that conversation, and only then activate. This is rail 2;
it never gets softened.

### Stage 6: Monitor

Invoke `meta-performance-loop` for on-demand performance reads. It uses the
Meta insights tools (MCP) or `meta ads insights get` (CLI) and writes dated
reports to its own documented location; link each report's path from
`run-log.md`.

For recurring check-ins, offer to schedule a Hermes cron job (for example a
daily read delivered back to the chat where it was created). A scheduled job
may only read and report. It must never activate, pause, scale, or change
budgets on its own; any action it recommends comes back to the user as a
proposal requiring fresh confirmation.

Rail 3 rules this stage: every number in a report is one a Meta tool
returned, cited with its date range. Recommendations are proposals only.

## Resume an interrupted run

When the user says something like "continue the campaign", "where were we",
or "pick up the launch":

1. Run Stage 0 again (setup-state file, BRAND.md, backends), then list
   `ad-runs/` at the resolved root and open the most recent run folder (or
   ask which one if several are active).
2. Read `run-log.md` and `ledger.json` and inspect which artifacts exist:
   `brief.md` and `copy.md` in the run folder, plus the linked
   `research/BRIEF-<date>.md`, creative files under `outputs/`, the
   ledger's entity IDs with their statuses, and report paths. The furthest
   complete artifact tells you roughly where the run stopped.
3. Before redoing anything with a cost or a side effect, reconcile with the
   live systems: check pending Arcads assets with `arcads_watch_asset` using
   the asset IDs in `run-log.md`, and check what already exists on Meta
   against every ID in `ledger.json` (MCP: `ads_get_ad_entities`; CLI:
   `meta ads campaign|adset|ad list --output json`, or
   `meta ads <resource> get <ID> --output json` for one entity). The
   ledger's run key makes a repeated submission safe: the launcher reads
   remote state and the ledger first and continues from the last recorded
   ID. Never regenerate or re-launch just because the conversation was cut
   off, and never re-create an entity because a transport error hid its
   ID.
4. Summarize what is done and what is next, then ask the user where to pick
   up. Approvals do not survive the interruption, except the copy approval
   whose hash is in the ledger and still matches `copy.md`: any other gate
   whose action has not happened yet must be re-confirmed in the current
   conversation before you act on it.

## Pitfalls

- Do not run stages in parallel to save time; each gate depends on the
  artifact before it.
- Do not invoke more than one creative skill "to explore options" without a
  credit-confirmed plan for each.
- Do not let a scheduled monitor job grow write permissions over time.
- Do not treat a user's enthusiasm ("looks great, ship it!") about creative
  as launch approval; the launch gate needs the full plan with budgets shown,
  and the copy gate needs the verbatim block and its hash approved.
- Do not split a copy pool into separate ads to fit a backend, and do not
  collapse it to a single variant; block and let the user choose.
- Do not start a run from a workspace root that exists only in the
  conversation; if the setup-state file is missing, the run does not start.
