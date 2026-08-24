# Hermes Ad Agent

**A media buyer brain for your Hermes agent.**

Install this skill pack and your [Hermes agent](https://hermes-agent.nousresearch.com) (by Nous Research) becomes a full-stack Meta media buyer: it researches competitor ads, generates image and video creatives with Arcads, writes ad copy that actually sounds human, launches everything to Meta (always paused, never spending without you), then monitors performance and reports back on a schedule.

You talk to it in plain English, from Telegram, WhatsApp, Discord, or the web chat. It does the media buying.

> This repo is the companion to a YouTube collab between Mr. Paid Social and Hostinger. Watch the full walkthrough here: **[YouTube video link coming soon]**

## What you need

1. **A Hermes agent on a Hostinger Managed App.** Easiest way to run Hermes 24/7 with the built-in scheduler. Get it here: [hostg.xyz/SHJtI](https://www.hostg.xyz/SHJtI) and use code **mrpaidsocial** for an extra 10% off yearly plans.
2. **An Arcads account** with credits, for image and video generation: [arcads.ai](https://arcads.ai/?via=hermes)
3. **A Meta ad account** (plus a Facebook Page) you can connect through Meta Business login.

**Model recommendation:** any model Hermes supports will work, but media buying involves judgment calls, long tool chains, and copywriting. A strong model pays for itself. We recommend Claude Sonnet or better, via your own Anthropic or OpenRouter key (`hermes model` walks you through it).

## Install

Open a chat with your Hermes agent and paste this:

```
Set up this repo: https://github.com/krusemediallc/hermes-ad-agent. Read SETUP.md and follow it.
```

That's it. The agent installs the skills, walks you through connecting the Arcads and Meta MCP servers, then runs a short brand interview so every skill knows who it's writing for. When it finishes, say something like "research my competitors and pitch me three ad concepts" and watch it go.

## The skills

Fourteen skills, one pipeline: research → create → launch → monitor.

| Skill | What it does |
|---|---|
| `ad-agent-orchestrator` | The front door. Takes a plain-English request ("make me new ads for the spring sale") and routes it through the right skills, end to end. |
| `brand-setup` | Interviews you about your brand and product, then writes BRAND.md, the context file every other skill reads. |
| `competitor-ad-research` | Searches the Meta Ad Library for competitor ads and distills them into hooks, angles, and a creative brief. |
| `human-ad-copy` | Writes primary text, headlines, and hooks, then strips every known AI-writing tell so the copy reads like a person wrote it. |
| `image-ad-clone` | Reverse-engineers a winning image ad into a reusable template, then rebuilds it for your brand. |
| `nano-banana-image-ad` | Photoreal and lifestyle image ads with Arcads' Nano Banana models, the default for most image work. |
| `chatgpt-image-ad` | Text-heavy image ads (comparison tables, headlines, "us vs them" layouts) with gpt-image-2, the model that gets typography right. |
| `ugc-video-ad` | Talking-head UGC videos: AI actor plus AI voice reading a script you approve line by line. |
| `clone-video-ad` | Recreates a reference video ad beat by beat with Seedance, restyled for your product. |
| `pixar-style-ad` | 3D-animated character story ads in a family-movie look. |
| `claymation-ad` | Stop-motion claymation story ads with consistent characters across shots. |
| `meta-ad-launcher` | Builds the campaign, ad set, and ad on Meta with your creative and copy. Everything lands PAUSED for your review. |
| `meta-performance-loop` | A scheduled loop that reads real Meta insights, flags winners and losers, and suggests what to scale or kill. |
| `ad-reporting-automations` | Recurring performance reports on Hermes cron, delivered wherever you chat (Telegram, WhatsApp, Discord, email). |

Everything talks to Arcads and Meta through their official MCP servers. No API keys in env files, no scripts to babysit.

## Safety rails

These are baked into the skills, not left to chance:

- **PAUSED only.** Every campaign, ad set, and ad is created paused. Nothing goes live until you review it in Ads Manager (or explicitly tell the agent to activate it).
- **Cost confirmation.** Before any Arcads generation, the agent shows you an estimated credit cost and waits for your yes.
- **No silent spend.** The agent never activates ads, resumes delivery, or touches budgets without explicit confirmation from you in that conversation.
- **No made-up numbers.** Performance reports only contain what the Meta MCP actually returned.

## Demo assets

The repo comes with parody demo products and a sample BRAND.md so you can run the whole pipeline before touching your real brand: see Demo mode in [SETUP.md](SETUP.md). Great for testing your setup on day one without risking anything.

---

## For the agent installing this

If you are a Hermes agent (or any AI agent) that has been asked to set up this repo: **read [SETUP.md](SETUP.md) and follow it step by step.** It covers installing the skills into `~/.hermes/skills/`, configuring the Arcads and Meta Ads MCP servers in `~/.hermes/config.yaml`, verifying your available tools, and running `brand-setup` to create the user's BRAND.md. Do not improvise an install path; SETUP.md is the source of truth.

---

## License and credits

MIT License. Built by **Mr. Paid Social** (Caleb Kruse).

**YouTube walkthrough:** [link coming soon]

**Disclaimer:** Arcads generations cost credits and Meta ads cost real money. This repo is designed to never spend either without your explicit confirmation, but you are responsible for reviewing everything before it goes live. Nothing here is a guarantee of ad performance.
