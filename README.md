# Hermes Ad Agent

**A media buyer brain for your Hermes agent.**

Install this skill pack and your [Hermes agent](https://hermes-agent.nousresearch.com) (by Nous Research) becomes a full-stack Meta media buyer: it researches competitor ads, generates image and video creatives with Arcads, writes ad copy that actually sounds human, launches everything to Meta (always paused, never spending without you), then monitors performance and reports back on a schedule. And it does none of it blind: Hermes studies your last 90 days first and remembers what works before it builds anything.

You talk to it in plain English, from Telegram, WhatsApp, Discord, or the web chat. It does the media buying.

> This repo is the companion to a YouTube collab between Mr. Paid Social and Hostinger. Watch the full walkthrough here: **[YouTube video link coming soon]**

## What you need

1. **A Hermes agent on a Hostinger Managed App.** Easiest way to run Hermes 24/7 with the built-in scheduler. Get it here: [hostg.xyz/SHJtI](https://www.hostg.xyz/SHJtI) and use code **mrpaidsocial** for an extra 10% off yearly plans.
2. **An Arcads account** with credits, for image and video generation: [arcads.ai](https://arcads.ai/?via=hermes)
3. **A Meta ad account** (plus a Facebook Page), connected through Meta's official Ads MCP server, Meta's official Ads CLI, or both. Each needs a token you create once in Meta's developer tools: a scoped user access token for the MCP on a headless install, a system user token for the CLI. Details in [docs/meta-authentication.md](docs/meta-authentication.md).

**Model recommendation:** any model Hermes supports will work, but media buying involves judgment calls, long tool chains, and copywriting. A strong model pays for itself. We recommend Claude Sonnet or better, via your own Anthropic or OpenRouter key (`hermes model` walks you through it).

### Two ways to connect Meta

| Route | Auth | Needs | Best when |
|---|---|---|---|
| Meta Ads MCP server | A Meta **user** access token with seven scopes, stored as a managed secret and referenced by the MCP config (OAuth only if you own a pre-registered Meta app with a supported callback) | A Hermes build that connects to remote MCP servers, or one that runs the pack's local bridge as a command-type MCP server, plus a Meta app of your own to mint the token | You want the widest tool surface (Ad Library search, previews, anomaly signals) |
| Meta Ads CLI | System user token from Business Suite | Python 3.12+ and a terminal | The MCP will not connect on your build, an MCP operation is missing (local file upload, one flexible ad with the full copy pool), or you prefer a plain CLI |

Both routes create everything paused and follow the same confirmation rules. Neither token is ever pasted into chat or written literally into a config file. SETUP.md Step 4 covers both (Route A and Route B); the long-form references are [docs/meta-authentication.md](docs/meta-authentication.md) (start here), [docs/meta-mcp.md](docs/meta-mcp.md), [docs/meta-cli.md](docs/meta-cli.md), and [docs/support-matrix.md](docs/support-matrix.md) for which operation runs on which backend.

### What is verified

Everything below happened on a real Hostinger managed Hermes (v0.20.x) against a real ad account in September 2026, not in a mock:

- Paused image and video ads were built end to end, each carrying 5 primary texts, 5 headlines, and 3 descriptions inside one flexible ad unit.
- The Meta MCP route works with a fully scoped user token as a bearer header. A generic OAuth login and a system user token both fail against the hosted MCP.
- On Hostinger the MCP route runs through the pack's local bridge (`scripts/meta_mcp_bridge.py`), so a rotated token takes effect on the next call with no restart, and a deterministic weekly maintenance job (`scripts/meta_token_maintenance.py`, no LLM) reports honestly whether Meta advanced the expiry (`RENEWED`) or only handed back a same-expiry token (`REPLACED_SAME_EXPIRY`, which is what the one observed re-exchange returned).
- Some MCP operations were not available on the account (media upload tools still rolling out, no flexible copy on `ads_create_creative`); those steps ran through the Meta Ads CLI instead. The pack blocks and tells you when the route you connected cannot do the step, rather than quietly building something smaller.
- The Arcads MCP connected and generated creatives; actual credit charges were reported per operation.

Tool rosters drift between days, so readiness is checked by capability, not by counting tools. Run the doctor after setup and after any Hermes update:

```bash
python3 scripts/onboarding_doctor.py
```

It is read-only and redacts secrets; it reports which layers (configured, connected, agent-usable, verified, durable) pass and which do not.

## Install

Open a chat with your Hermes agent and paste this:

```
Set up this repo: https://github.com/krusemediallc/hermes-ad-agent. Read SETUP.md and follow it.
```

That's it. The agent installs the skills, walks you through connecting Arcads (MCP) and Meta (MCP or CLI, your choice), audits your ad account's last 90 days into a per-account memory file, then runs a short brand interview so every skill knows who it's writing for. Setup also wires Hermes's own context and memory (project context, notes, user profile, and an optional soul) so every conversation starts oriented instead of cold; see [docs/hermes-context.md](docs/hermes-context.md). When it finishes, say something like "research my competitors and pitch me three ad concepts" and watch it go.

## The skills

Fifteen skills, one pipeline: research → create → launch → monitor.

| Skill | What it does |
|---|---|
| `ad-agent-orchestrator` | The front door. Takes a plain-English request ("make me new ads for the spring sale") and routes it through the right skills, end to end. |
| `account-audit` | A read-only 90-day deep dive of each connected ad account, over either Meta backend (MCP or CLI), written to a per-account memory file the creative, copy, and launch skills consult before building anything new. It also captures the exact API objects (targeting, placements, bidding, attribution, creative enhancement settings) so new ads can mirror what already runs. |
| `brand-setup` | Interviews you about your brand and product, then writes BRAND.md, the context file every other skill reads. |
| `competitor-ad-research` | Searches the Meta Ad Library for competitor ads and distills them into hooks, angles, and a creative brief. Needs the Meta MCP; the Ad Library is not in the CLI. |
| `human-ad-copy` | Writes primary text, headlines, and hooks, then strips every known AI-writing tell so the copy reads like a person wrote it. |
| `image-ad-clone` | Reverse-engineers a winning image ad into a reusable template, then rebuilds it for your brand. |
| `nano-banana-image-ad` | Photoreal and lifestyle image ads with Arcads' Nano Banana models, the default for most image work. |
| `chatgpt-image-ad` | Text-heavy image ads (comparison tables, headlines, "us vs them" layouts) with gpt-image-2, the model that gets typography right. |
| `ugc-video-ad` | Talking-head UGC videos: AI actor plus AI voice reading a script you approve line by line. |
| `clone-video-ad` | Recreates a reference video ad beat by beat with Seedance, restyled for your product. |
| `pixar-style-ad` | 3D-animated character story ads in a family-movie look. |
| `claymation-ad` | Stop-motion claymation story ads with consistent characters across shots. |
| `meta-ad-launcher` | Builds the campaign, ad set, and ad on Meta with your creative and copy, over either Meta backend (MCP or CLI). Everything lands PAUSED for your review. |
| `meta-performance-loop` | A scheduled loop that reads real Meta insights (MCP or CLI), flags winners and losers, and suggests what to scale or kill. |
| `ad-reporting-automations` | Recurring performance reports on Hermes cron, over either Meta backend, delivered wherever you chat (Telegram, WhatsApp, Discord, email). |

Arcads is connected through its official MCP server, and Meta through either Meta's official Ads MCP server or Meta's official Ads CLI, whichever you connect. There is no REST integration to write and no code to deploy: the pack is skills plus configuration. The credentials it can ask you to create are Meta's own tokens (a scoped user token for the MCP route, a system user token for the CLI route), and they live only as managed secrets or in gitignored env files, referenced by name from the config. Nothing in this repo ever asks you to paste a token into chat.

## Safety rails

These are baked into the skills, not left to chance:

- **PAUSED only.** Every campaign, ad set, and ad is created paused. Nothing goes live until you review it in Ads Manager (or explicitly tell the agent to activate it).
- **Cost confirmation.** Before any Arcads generation, the agent asks for your plan's rate or, if you do not know it, a maximum credit exposure you are willing to spend, and waits for your yes. It reports the actual credits charged after each operation and never retries or re-generates on your credits without a fresh approval.
- **No silent spend.** The agent never activates ads, resumes delivery, or touches budgets without explicit confirmation from you in that conversation.
- **No made-up numbers.** Performance reports only contain what the Meta tools (MCP or CLI) actually returned.

## Demo assets

The repo comes with parody demo products and a sample BRAND.md so you can run the whole pipeline before touching your real brand: see Demo mode in [SETUP.md](SETUP.md). Great for testing your setup on day one without risking anything.

---

## For the agent installing this

If you are a Hermes agent (or any AI agent) that has been asked to set up this repo: **read [SETUP.md](SETUP.md) and follow it step by step.** It covers installing the skills into the Hermes skills directory (discover it from `$HERMES_HOME` and `hermes config path`; on Hostinger it is under `/data`, never assume `~/.hermes`), configuring the Arcads MCP server, connecting Meta by one of two routes (the Meta Ads MCP server or the Meta Ads CLI, SETUP.md Step 4, with the token rules in [docs/meta-authentication.md](docs/meta-authentication.md)), verifying your available tools by capability, and running `brand-setup` to create the user's BRAND.md. Finish with `python3 scripts/onboarding_doctor.py` and report the result as COMPLETE, PARTIAL, or FRAGILE. Do not improvise an install path; SETUP.md is the source of truth.

---

## License and credits

MIT License. Built by **Mr. Paid Social** (Caleb Kruse).

**YouTube walkthrough:** [link coming soon]

**Disclaimer:** Arcads generations cost credits and Meta ads cost real money. This repo is designed to never spend either without your explicit confirmation, but you are responsible for reviewing everything before it goes live. Nothing here is a guarantee of ad performance.
