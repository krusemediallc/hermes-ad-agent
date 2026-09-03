# How Hermes stays oriented: the four context panels

Hermes carries four pieces of standing context into every conversation. The dashboard shows them as four panels: **My Notes**, **User Profile**, **Agent Soul**, and **Project Context**. This page explains what each one is, who writes it, when it loads, and how this skill pack uses it during setup. Read it if a conversation starts cold, if the dashboard says "No project context file found", or if you are deciding what belongs where.

The facts here match the Hermes docs as of September 2026. Hermes versions differ; when your instance disagrees with this page, trust your instance.

The paths below are written with the default `~/.hermes` home. The real home is `$HERMES_HOME`, and it is not always `~/.hermes`: on Hostinger managed Hermes it is `/data`, so the files are `/data/memories/MEMORY.md`, `/data/memories/USER.md`, `/data/SOUL.md`, `/data/config.yaml`, and `/data/hermes-ad-agent/setup-state.json`. Discover the paths instead of assuming them: `echo $HERMES_HOME`, `hermes config path` (the config file), and `hermes config env-path` (the env file); if `hermes` is not on PATH in an agent shell, try `/opt/venv/bin/hermes` and verify with `--help`. Never hard-code `~/.hermes` in a skill, cron job, or doc you write for the pack.

## The four panels at a glance

| Panel | File | Cap | Who writes it | When it loads |
|---|---|---|---|---|
| My Notes | `~/.hermes/memories/MEMORY.md` | 2,200 characters (about 800 tokens) | The agent, with its built-in `memory` tool (`add`, `replace`, `remove`), or when the user says "remember that ..." | Frozen snapshot at session start |
| User Profile | `~/.hermes/memories/USER.md` | 1,375 characters (about 500 tokens) | Same as above | Frozen snapshot at session start |
| Agent Soul | `~/.hermes/SOUL.md` (or `$HERMES_HOME/SOUL.md`) | Truncated if large, scanned for prompt-injection patterns | A human, by hand (this pack only installs one on an explicit yes) | Every session, slot 1 of the system prompt; a built-in default applies if missing or empty |
| Project Context | The first match in the working directory: `.hermes.md` / `HERMES.md`, then `AGENTS.override.md`, then `AGENTS.md`, then `CLAUDE.md`, then `.cursorrules` / `.cursor/rules/*.mdc` | Dynamic at startup (floor 20,000 characters); 8,000 characters per file discovered later | The project maintainer (this repo ships `AGENTS.md`) | Session start from the working directory, plus progressive discovery as the agent moves into subdirectories |

"Frozen snapshot" matters: the two memory files are read once when the session begins and injected into the system prompt. An entry saved mid-conversation shows up from the next session on, not in the current one. Config keys: `memory.memory_enabled`, `memory.user_profile_enabled`, `memory.memory_char_limit` (2200), `memory.user_char_limit` (1375), and `memory.write_approval` (false by default; when true, writes wait in `/memory pending` until `/memory approve` or `/memory reject`).

## My Notes (MEMORY.md)

The agent's own notebook: environment facts, conventions, things it learned about how to work here. It is small on purpose. Good entries are one line each: where the workspace is, which Meta backend is live, that everything launches paused. Bad entries are anything that already lives in a file the agent can read (the brand voice, the account audit, the skill list).

## User Profile (USER.md)

Who the user is and how they like to work: communication style, expectations, how much detail they want, what annoys them. Even smaller than the notes. This is not the brand file. "Prefers short replies, wants the credit estimate before every generation" belongs here; "the offer is a 30-day supply at $49" belongs in `BRAND.md`.

## Agent Soul (SOUL.md)

Identity and tone: how direct the agent is, how it handles uncertainty, whether it asks before acting. It is global to the whole Hermes instance, not to a project, so it must never carry project paths, workflows, or account details. Hermes's own guidance is the rule of thumb: if it should follow the agent everywhere, it belongs in SOUL.md; if it belongs to a project, it belongs in AGENTS.md. Session-level overlays exist too (`/personality <name>`, twelve built in, custom ones under `agent.personalities` in `config.yaml`) and do not touch the file.

## Project Context (AGENTS.md and friends)

Loaded from Hermes's **working directory** at session start. Inside a git repository, Hermes merges the chain of `AGENTS.md` files from the git root down to the working directory (each with a provenance header, duplicates removed). Outside a git repo it checks the working directory only, never parents. As the agent navigates into subdirectories during a session it discovers their `AGENTS.md` files progressively, capped at 8,000 characters per file, which is why this repo's `AGENTS.md` stays under that limit.

Which directory counts as "working directory" depends on how the session started:

- **Dashboard, messaging channels, cron:** the `terminal.cwd` key in the config file (`hermes config path`; `~/.hermes/config.yaml` on a default install, `/data/config.yaml` on Hostinger; default value `'.'`). The `TERMINAL_CWD` environment variable overrides it per invocation.
- **CLI (TUI) sessions:** always the directory you launched from.

Whichever route you use, set it with the discovered paths, not a guessed `~/.hermes`: `hermes config set terminal.cwd <absolute workspace root>` edits whatever file `hermes config path` reports, and a cron job should carry an explicit absolute workdir of its own rather than inherit whatever the gateway happened to have. A malformed hand edit to `config.yaml` can take the gateway down, so prefer `hermes config set` and check with `hermes config check` (verify both against `--help` on your build).

**Why the panel can say "No project context file found for this workspace":** none of the recognized files exist in the current working directory. Almost always that means the working directory is still Hermes's default rather than the pack's workspace root. It is not an error in the pack; it means the pointer has not been set yet.

## How this pack wires each panel during setup

[SETUP.md](../SETUP.md) does this as part of the guided install; this is the summary.

1. **Project Context.** Point Hermes's working directory at the workspace root (the repo clone directory recorded in SETUP.md Checkpoint 1, default `~/hermes-ad-agent`) by setting `terminal.cwd` in the config file that `hermes config path` reports (`hermes config set terminal.cwd <absolute path>`; hand-editing the file also works but is riskier, see above). Confirm in the dashboard's Project Context panel: it should show the contents of `AGENTS.md` instead of the "No project context file found" message. If the gateway needs a restart to pick up the change, restart it and check again. If the user wants Hermes to keep a different working directory, the fallback is a pointer file: a short `AGENTS.md` in that directory that names the workspace root and says "read its AGENTS.md first".
2. **My Notes.** After brand-setup, the agent saves a few one-line entries with its `memory` tool: the workspace root path, the live Meta backend (`mcp` or `cli`), the brand name, and the standing rule that everything launches paused and nothing spends without confirmation. That is all. Expect to see them from the next session on. The note is a convenience for the model; the authoritative copy of the workspace root and backend is the setup-state file in item 5, which skills read even when the memory snapshot is stale or the session has none.
3. **User Profile.** After brand-setup, one or two lines on how the user wants to be worked with (reply length, approval habits, preferred channel). Nothing about the business.
4. **Agent Soul (optional).** `hermes/SOUL.md` in this repo is a short media-buyer persona: direct, numbers-first, says what it did not verify, asks before spending. It is installed only if the user explicitly says yes, and it is appended to an existing `SOUL.md` rather than replacing it, because the soul is global to the instance and the user may already have one.
5. **Setup state (the fifth thing, not a panel).** The four panels are prose for the model. The pack also persists one small machine-readable file that every skill and cron job reads before doing anything: `$HERMES_HOME/hermes-ad-agent/setup-state.json` (fallback `~/.hermes/hermes-ad-agent/setup-state.json`; `/data/hermes-ad-agent/setup-state.json` on Hostinger). It exists because the workspace root used to live only in the conversation, and a fresh session or a cron job could not find `BRAND.md` or write `outputs/` without asking. Setup writes it at the end of the install; the doctor step refreshes it. Schema, version 1:

   ```json
   {
     "schema_version": 1,
     "workspace_root": "/absolute/path/to/hermes-ad-agent",
     "repo_commit": "<git short sha of the installed pack>",
     "meta_backend": "mcp",
     "arcads_connected": true,
     "installed_at": "2026-09-03T00:00:00Z",
     "last_doctor_at": "2026-09-03T00:00:00Z"
   }
   ```

   `meta_backend` is one of `mcp`, `cli`, or `none`; `arcads_connected` is a boolean; the timestamps are ISO 8601. Every skill resolves `workspace_root` from this file before reading `BRAND.md` or writing to `research/`, `outputs/`, `ad-runs/`, `reports/`, or `memory/`, and every cron job still sets its own explicit absolute workdir (the file is a lookup, not a substitute for the cron's cwd). If it is missing, the skill asks the user for the workspace root and suggests re-running setup rather than guessing. The no-secrets rule is strict: no tokens, no keys, no ad account IDs, no page IDs, no business IDs, nothing that identifies a customer. It holds a path, a commit, two connection flags, and two timestamps, and it is safe to print in full.

## What not to put in each

- **Anywhere:** secrets. No tokens, no keys, no `.env` contents. A Meta token belongs only in the managed app's environment (the hosting provider's env UI) or the env file that `hermes config env-path` reports; `config.yaml` references it as `${META_MCP_TOKEN}`, never as a literal.
- **Setup state:** anything beyond the seven fields above. No account IDs, no secrets, no brand facts; those have their own homes.
- **My Notes:** long text, the brand voice, audit findings, lists of ads. Those live in `BRAND.md` and `memory/accounts/`. Duplicating them into a 2,200-character file guarantees they go stale.
- **User Profile:** business facts, offers, prices, targets. Those are `BRAND.md`.
- **Agent Soul:** project paths, workflows, account IDs, brand names, safety rules that already live in `AGENTS.md`. The soul is identity and tone only, and it follows the agent into every project on the instance.
- **Project Context:** personal data, account IDs, or anything user-specific. `AGENTS.md` is committed to a public repo; the user's data stays in the gitignored files it points to.
