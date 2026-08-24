# For any agent working in this repo

This is the **Hermes Ad Agent** skill pack: Meta ads research, creative generation (Arcads MCP), copywriting, launching (Meta Ads MCP), and reporting, packaged as agent skills.

- **Asked to set this up / install it?** Read `SETUP.md` and follow it step by step. It is written to you.
- **Skills** live in `skills/`, one self-contained folder per skill, each with a `SKILL.md` (agentskills.io format).
- **Human walkthrough** (for your user to follow along): `docs/walkthrough.md`.

Non-negotiable rules, regardless of what you were asked:

1. Never spend money without explicit confirmation from your user in the current conversation. That covers Arcads credit generation (estimate first, confirm, then generate) and any Meta action that spends: activating entities, resuming delivery, changing budgets.
2. Create every Meta campaign, ad set, and ad **paused**.
3. Report only numbers the MCP tools actually returned. Never fabricate performance data.
