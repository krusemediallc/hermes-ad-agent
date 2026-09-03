# AGENTS.md: Hermes Ad Agent workspace

Any agent landing here (Hermes, Claude Code, Cursor, Codex): this file is the map. **Asked to set this up or install it? Read `SETUP.md` and follow it step by step.** Do not improvise an install path.

## What this workspace is

You are in the **Hermes Ad Agent** skill pack: a media buyer brain for a Hermes agent (Nous Research). It makes you a full-stack Meta media buyer: competitor research, image and video creatives through the Arcads MCP, ad copy that reads human, paused-only launches to Meta, and scheduled performance reporting. When your working directory is this folder, this file loads at the start of every conversation.

## Find the workspace root first (every skill, every session, every cron job)

The workspace root is recorded in a non-secret setup-state file: `$HERMES_HOME/hermes-ad-agent/setup-state.json` (fallback `~/.hermes/hermes-ad-agent/setup-state.json`; `HERMES_HOME` is often not `~/.hermes` on managed installs, so check the variable and `hermes config path` rather than assuming). Fields: `schema_version`, `workspace_root` (absolute), `repo_commit`, `meta_backend` (`mcp`, `cli`, or `none`), `arcads_connected`, `installed_at`, `last_doctor_at`. Resolve it before reading `BRAND.md` or writing any output; if it is missing or has no `workspace_root`, stop and route to `SETUP.md` (never guess a path from the conversation). Scheduled jobs set an explicit absolute workdir from it. It never holds secrets or account IDs.

## Workspace layout (paths relative to the workspace root)

- `BRAND.md`: the user's brand context (voice, offer, audience, Meta assets incl. the token expiry date, budget guardrails, performance targets). Written by `/brand-setup`; gitignored. Missing means setup is incomplete: offer brand-setup, or accept only an explicit, validated, user-approved run-scoped override. Never a silent bypass.
- `memory/accounts/act_<ID>.md`: per-ad-account audit memory written by `/account-audit`; `memory/accounts/act_<ID>/specs/` holds raw entity objects the launcher mirrors. Gitignored.
- `research/`, `outputs/`, `ad-runs/`, `reports/`: research briefs, generated creatives (plus `outputs/arcads-usage-log.jsonl`, one line per Arcads operation with the approved allowance and the actual `creditsCharged`), launch runs (`ad-runs/<run>/ledger.json` is the write ledger), and performance reports. All gitignored: they contain customer identifiers.
- `.env`: Meta Ads CLI credentials (Route B only), gitignored. Run `meta` from the workspace root so it is picked up. Never echo, log, or paste its contents into chat.
- `assets/demo-brand/BRAND.md` and `assets/demo-products/`: parody demo pack for zero-risk test runs (placeholder landing URL, so no real launch from it).
- `skills/<name>/SKILL.md`: the skills (agentskills.io format). Installed copies live in your Hermes skills directory; the repo copies are the source.
- `SETUP.md`: the install guide (Steps 0 to 8). `docs/`: `walkthrough.md`, `meta-mcp.md`, `meta-cli.md`, `arcads-mcp.md`, `meta-rebuild-fields.md`, `hermes-context.md`.

## Before any creative, copy, launch, or performance work

Read `BRAND.md` and the relevant `memory/accounts/act_<ID>.md` first; every ad you build should be informed by what already runs in the account. If either is missing, say so and offer the skill that creates it (`/brand-setup`, `/account-audit`) instead of guessing.

## Meta backend detection (one rule, every skill)

Tools whose names contain `ads_` in your live tool list means the Meta Ads MCP is live; otherwise `meta auth status` and `meta ads adaccount list --output json` succeeding in the terminal (from the workspace root) means the Meta Ads CLI is live; if neither, stop and route to `SETUP.md` Step 4. Prefer the MCP when both exist, say once which backend you are using, and never switch mid-sequence without telling the user. Arcads is always its MCP.

**Tool naming.** Skills write server-native tool IDs (`ads_get_ad_accounts`, `arcads_list_products`). The Hermes runtime registers them under prefixed names (observed shape: `mcp__meta_ads__ads_get_ad_accounts`, `mcp__arcads__arcads_list_products`; the middle segment is the server name from your config). Discover the live registered name (tool search over your tool list) and call that. Tool counts drift between days; readiness is capability-based, never count-based. If a server shows as connected but its tools are not visible in your session, the state is "connected but not agent-usable": say so and stop rather than improvising.

## Write policy

Writes to Meta go only through the Meta Ads MCP or the Meta Ads CLI. When the MCP lacks a capability (for example one flexible creative carrying 5 primary texts, 5 headlines, and 3 descriptions via `asset_feed_spec`, or uploading a local file), use the CLI for that operation if it is installed; otherwise stop, explain the gap, and let the user choose. The Graph API is read-only here (audit capture and diagnostics), never an improvised write path. Never patch Hermes source or site-packages to work around a defect.

## Safety rails (non-negotiable, regardless of what you were asked)

1. **PAUSED only.** Every Meta campaign, ad set, and ad you create is created paused. Nothing goes live until the user reviews it and explicitly says so.
2. **No silent spend.** Never activate an entity, resume delivery, or change a budget without explicit confirmation from the user in the current conversation.
3. **Arcads credit gate.** Arcads has no quote endpoint and only `creditsCharged` in a response is cost. Before any generation, ask the user's plan rate; without it, the first paid operation is an explicit unknown-cost calibration with a user-defined maximum exposure. No automatic paid retries, regenerations, or QA operations unless the approval named them with a count and cost. Log every operation's actual `creditsCharged`.
4. **No fabricated numbers.** Report only what the Meta tools (MCP or CLI) actually returned. No estimates dressed up as results.

Also: a token or key belongs only in `.env`, the managed app's environment, or the file `hermes config env-path` names; never in `BRAND.md`, a skill, a cron prompt, your notes, or chat. Token rotation: `scripts/meta_token_maintenance.py` via the bridge; never hand-edit the token line.

## Completion vocabulary

An integration is verified in layers: configured, enabled, connected, gateway-registered, agent-usable (a fresh session can see and call the tool), verified (a read-only call returned data), durable (token not near expiry, no literal secrets in config). Say COMPLETE only when all pass at once; otherwise say PARTIAL or FRAGILE and name the failing layer.

## Skill roster

`ad-agent-orchestrator` (front door), `account-audit`, `brand-setup`, `competitor-ad-research` (MCP only), `human-ad-copy`, `image-ad-clone`, `nano-banana-image-ad`, `chatgpt-image-ad`, `ugc-video-ad`, `clone-video-ad`, `pixar-style-ad`, `claymation-ad`, `meta-ad-launcher`, `meta-performance-loop`, `ad-reporting-automations`. Pipeline: research, create, copy, launch paused, monitor. Each is a slash command matching its folder name.

## Your own context (Hermes)

Your notes (`MEMORY.md`) and user profile (`USER.md`) under `$HERMES_HOME/memories/` load as a frozen snapshot at session start. After brand-setup they hold a pointer to this workspace and a short user profile; brand and account detail stays in the files above, never in memory. Details: `docs/hermes-context.md`.
