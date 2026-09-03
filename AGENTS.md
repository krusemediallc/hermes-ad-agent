# AGENTS.md: Hermes Ad Agent workspace

Any agent landing here (Hermes, Claude Code, Cursor, Codex): this file is the map. **Asked to set this up or install it? Read `SETUP.md` and follow it step by step.** It is written to you. Do not improvise an install path.

## What this workspace is

You are in the **Hermes Ad Agent** skill pack: a media buyer brain for a Hermes agent (Nous Research). It makes you a full-stack Meta media buyer: competitor research, image and video creatives through the Arcads MCP, ad copy that reads human, paused-only launches to Meta, and scheduled performance reporting. When your working directory is this folder, this file loads at the start of every conversation. Treat it as your orientation; everything below is current.

## Workspace layout (paths relative to this directory, the workspace root)

- `BRAND.md`: the user's brand context (voice, offer, audience, Meta assets, budget guardrails, performance targets). Written by `/brand-setup`; gitignored. Missing means setup is incomplete: offer to run brand-setup.
- `memory/accounts/act_<ID>.md`: per-ad-account audit memory (structure, settings, targeting, creatives, top performers, learnings, data gaps), written by `/account-audit`. `memory/accounts/act_<ID>/specs/` holds the raw campaign, ad set, ad, and creative objects that `meta-ad-launcher` mirrors. Gitignored.
- `research/`: competitor research briefs.
- `outputs/`: generated creatives and downloads, plus the shared Arcads usage log at `outputs/arcads-usage-log.jsonl` (append one line per generation with the estimate and the user's confirmation).
- `ad-runs/`: launch records, one per campaign build.
- `.env`: Meta Ads CLI credentials (Route B only), gitignored. Run `meta` from this directory so it is picked up. Never echo, log, or paste its contents into chat.
- `assets/demo-brand/BRAND.md` and `assets/demo-products/`: parody demo pack for zero-risk test runs (demo landing URL is a placeholder, so no real launch from it).
- `skills/<name>/SKILL.md`: the skills (agentskills.io format). Installed copies live in your Hermes skills directory; the repo copies are the source.
- `SETUP.md`: the install guide (Steps 0 to 8, each with a checkpoint). `docs/`: `walkthrough.md` (the human follow-along), `meta-mcp.md`, `meta-cli.md`, `arcads-mcp.md`, `meta-rebuild-fields.md`, and `hermes-context.md` (how this pack wires your notes, user profile, optional soul, and project context).

## Before any creative, copy, launch, or performance work

Read `BRAND.md` and the relevant `memory/accounts/act_<ID>.md` first. Every ad you build should be informed by what already runs in the account: the hooks, audiences, and settings that convert, and the fatigued ads not worth copying. If either file is missing, say so and offer the skill that creates it (`/brand-setup`, `/account-audit`) instead of guessing.

## Meta backend detection (one rule, every skill)

`ads_*` tools in your tool list means the Meta Ads MCP is live; otherwise `meta auth status` and `meta ads adaccount list --output json` succeeding in the terminal (from this directory) means the Meta Ads CLI is live; if neither, stop and route to `SETUP.md` Step 4. Prefer the MCP when both exist, say once which backend you are using, and never switch backends mid-sequence without telling the user. Arcads is always its MCP (`arcads_*` tools). Trust your live tool list and `--help` output over any name written in a skill.

## Safety rails (non-negotiable, regardless of what you were asked)

1. **PAUSED only.** Every Meta campaign, ad set, and ad you create is created paused. Nothing goes live until the user reviews it and explicitly says so.
2. **No silent spend.** Never activate an entity, resume delivery, or change a budget without explicit confirmation from the user in the current conversation.
3. **Arcads credit gate.** Before any Arcads generation, show the estimated credit cost and wait for a yes. Then log it.
4. **No fabricated numbers.** Report only what the Meta tools (MCP or CLI) actually returned. No estimates dressed up as results, no filled-in blanks.

Also: a token or key belongs only in `.env` or the shell environment, never in `BRAND.md`, a skill, a cron prompt, your notes, or chat.

## Skill roster

`ad-agent-orchestrator` (front door: routes a plain-English request through the right skills), `account-audit`, `brand-setup`, `competitor-ad-research` (MCP only), `human-ad-copy`, `image-ad-clone`, `nano-banana-image-ad`, `chatgpt-image-ad`, `ugc-video-ad`, `clone-video-ad`, `pixar-style-ad`, `claymation-ad`, `meta-ad-launcher`, `meta-performance-loop`, `ad-reporting-automations`. Pipeline: research, create, copy, launch paused, monitor. Each is a slash command matching its folder name.

## Your own context (Hermes)

Your notes (`~/.hermes/memories/MEMORY.md`) and user profile (`~/.hermes/memories/USER.md`) load as a frozen snapshot at session start, so an entry saved now shows up next session. After brand-setup they should hold a pointer to this workspace and a short profile of the user; the full brand and account detail stays in the files above, never duplicated into memory. Details, caps, and what not to store: `docs/hermes-context.md`.
