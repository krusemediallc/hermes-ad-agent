# Hermes Ad Agent

**A media buyer brain for your Hermes agent.**

Install this skill pack and your [Hermes agent](https://hermes-agent.nousresearch.com) (by Nous Research) becomes a full-stack Meta media buyer: it researches competitor ads, generates image and video creatives with Arcads, writes ad copy that actually sounds human, launches everything to Meta (always paused, never spending without you), then monitors performance and reports back on a schedule. And it does none of it blind: Hermes studies your last 90 days first and remembers what works before it builds anything.

You talk to it in plain English, from Telegram, WhatsApp, Discord, or the web chat. It does the media buying.

> This repo is the companion to a YouTube collab between Mr. Paid Social and Hostinger. Watch the full walkthrough here: **[YouTube video link coming soon]**

## What you need

1. **A Hermes agent on a Hostinger Managed App.** Easiest way to run Hermes 24/7 with the built-in scheduler. Get it here: [hostg.xyz/SHJtI](https://www.hostg.xyz/SHJtI) and use code **mrpaidsocial** for an extra 10% off yearly plans.
2. **An Arcads account** with credits, for image and video generation: [arcads.ai](https://arcads.ai/?via=hermes)
3. **A Meta ad account** (plus a Facebook Page), connected either through Meta Business login (the Meta Ads MCP server) or through a system user token (the Meta Ads CLI, Meta's official command-line tool for the Marketing API). Pick the MCP if your Hermes build connects to it, the CLI otherwise.

**Model recommendation:** any model Hermes supports will work, but media buying involves judgment calls, long tool chains, and copywriting. A strong model pays for itself. We recommend Claude Sonnet or better, via your own Anthropic or OpenRouter key (`hermes model` walks you through it).

### Two ways to connect Meta

| Route | Auth | Needs | Best when |
|---|---|---|---|
| Meta Ads MCP server | Meta Business OAuth login, no token | A Hermes build that connects to remote MCP servers | You want the widest tool surface (Ad Library search, previews, anomaly signals) |
| Meta Ads CLI | System user token from Business Suite | Python 3.12+ and a terminal | The MCP will not connect on your build, or you prefer a plain CLI |

Both routes create everything paused and follow the same confirmation rules. SETUP.md Step 4 covers both (Route A and Route B); the long-form references are [docs/meta-mcp.md](docs/meta-mcp.md) and [docs/meta-cli.md](docs/meta-cli.md).

## Install

Open a chat with your Hermes agent and paste this:

```
Set up this repo: https://github.com/krusemediallc/hermes-ad-agent. Read SETUP.md and follow it.
```

That's it. The agent installs the skills, walks you through connecting Arcads (MCP) and Meta (MCP or CLI, your choice), audits your ad account's last 90 days into a per-account memory file, then runs a short brand interview so every skill knows who it's writing for. When it finishes, say something like "research my competitors and pitch me three ad concepts" and watch it go.

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

Arcads is connected through its official MCP server, and Meta through either Meta's official Ads MCP server or Meta's official Ads CLI, whichever you connect. The only credential the pack can ever ask for is the Meta system user token on the CLI route, and it lives in a gitignored `.env`.

## Safety rails

These are baked into the skills, not left to chance:

- **PAUSED only.** Every campaign, ad set, and ad is created paused. Nothing goes live until you review it in Ads Manager (or explicitly tell the agent to activate it).
- **Cost confirmation.** Before any Arcads generation, the agent shows you an estimated credit cost and waits for your yes.
- **No silent spend.** The agent never activates ads, resumes delivery, or touches budgets without explicit confirmation from you in that conversation.
- **No made-up numbers.** Performance reports only contain what the Meta tools (MCP or CLI) actually returned.

## Demo assets

The repo comes with parody demo products and a sample BRAND.md so you can run the whole pipeline before touching your real brand: see Demo mode in [SETUP.md](SETUP.md). Great for testing your setup on day one without risking anything.

---

## For the agent installing this

If you are a Hermes agent (or any AI agent) that has been asked to set up this repo: **read [SETUP.md](SETUP.md) and follow it step by step.** It covers installing the skills into `~/.hermes/skills/`, configuring the Arcads MCP server in `~/.hermes/config.yaml`, connecting Meta by one of two routes (the Meta Ads MCP server or the Meta Ads CLI, SETUP.md Step 4), verifying your available tools, and running `brand-setup` to create the user's BRAND.md. Do not improvise an install path; SETUP.md is the source of truth.

---

## License and credits

MIT License. Built by **Mr. Paid Social** (Caleb Kruse).

**YouTube walkthrough:** [link coming soon]

**Disclaimer:** Arcads generations cost credits and Meta ads cost real money. This repo is designed to never spend either without your explicit confirmation, but you are responsible for reviewing everything before it goes live. Nothing here is a guarantee of ad performance.
