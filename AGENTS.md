# For any agent working in this repo

This is the **Hermes Ad Agent** skill pack: Meta ads research, a read-only account audit that writes per-account memory files to `memory/accounts/` right after Meta is connected (before brand-setup), creative generation (Arcads MCP), copywriting, launching and reporting (Meta Ads MCP server or Meta Ads CLI, either one), packaged as agent skills.

- **Asked to set this up / install it?** Read `SETUP.md` and follow it step by step. It is written to you.
- **Skills** live in `skills/`, one self-contained folder per skill, each with a `SKILL.md` (agentskills.io format).
- **Human walkthrough** (for your user to follow along): `docs/walkthrough.md`.
- **Two Meta backends.** Skills detect which one is live: `ads_*` tools in the tool list means the MCP; otherwise `meta auth status` and `meta ads adaccount list --output json` in the terminal means the CLI (the Meta Ads CLI is Meta's official command-line tool for the Marketing API). Reference docs: `docs/meta-mcp.md` and `docs/meta-cli.md`.

Non-negotiable rules, regardless of what you were asked:

1. Never spend money without explicit confirmation from your user in the current conversation. That covers Arcads credit generation (estimate first, confirm, then generate) and any Meta action that spends: activating entities, resuming delivery, changing budgets.
2. Create every Meta campaign, ad set, and ad **paused**.
3. Report only numbers the Meta tools (MCP or CLI) actually returned. Never fabricate performance data.
