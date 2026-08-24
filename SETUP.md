# Hermes Ad Agent: Install Guide (for the installing agent)

You are a Hermes Agent (Nous Research) and you have been asked to set up the **Hermes Ad Agent** skill pack. This document is written to you. Work through the steps in order. Each step ends with a checkpoint; do not move on until the checkpoint passes. Talk to your user in plain language as you go, and ask before anything that costs money.

Three rules apply to everything below and to every skill you are about to install. They are not optional:

1. **Never spend money without explicit confirmation.** Before any Arcads generation, present a credit-cost estimate and wait for the user to confirm. Before any Meta action that could spend (activating an entity, resuming delivery, changing a budget), get explicit confirmation in the current conversation.
2. **Everything you create on Meta is created PAUSED.** Campaigns, ad sets, and ads. Always.
3. **Never fabricate numbers.** Report only what the MCP tools actually returned.

---

## Step 0: Preflight

Confirm the following about your own environment before touching anything:

- You are a Hermes Agent with access to a terminal (shell/exec tool). On a Hostinger Managed App you also have the in-browser terminal in hPanel (Hermes → Manage → CLI); commands below work the same there.
- Your skills directory exists. The default is `~/.hermes/skills/`. Verify:

  ```bash
  ls -la ~/.hermes/skills/
  ```

- The `hermes` CLI responds:

  ```bash
  hermes --version
  ```

- You can reach the internet (you will clone a repo and connect two remote MCP servers).

If any of these fail, tell the user what is missing before continuing. Your environment may differ from the defaults described here (Hermes versions vary); when in doubt, check your own configuration rather than assuming this document is right.

**Checkpoint 0:** terminal works, `~/.hermes/skills/` exists (or you know where your skills directory actually is), `hermes` CLI responds.

---

## Step 1: Get this repo into your workspace

You need a local copy of this repository so you can read `skills/`, this file, and `docs/walkthrough.md`.

**This clone directory is the workspace root.** The directory where this repo lands (default `~/hermes-ad-agent`) is the single working directory for everything the skill pack produces: `BRAND.md`, `research/`, `outputs/` (including the shared Arcads usage log at `outputs/arcads-usage-log.jsonl`), and `ad-runs/` all live at the workspace root. Every skill that mentions one of those paths means "relative to the workspace root". You will record its absolute path at the checkpoint below.

If you were given a GitHub URL for this repo:

```bash
cd ~
git clone https://github.com/krusemediallc/hermes-ad-agent.git hermes-ad-agent
cd hermes-ad-agent
ls skills/
```

If `git` is unavailable, download and unpack the archive instead. Note that GitHub's zip extracts to a folder named `hermes-ad-agent-main/`, so rename it to match the default workspace root:

```bash
cd ~
curl -L -o hermes-ad-agent.zip https://github.com/krusemediallc/hermes-ad-agent/archive/refs/heads/main.zip
unzip hermes-ad-agent.zip
mv hermes-ad-agent-main hermes-ad-agent
cd hermes-ad-agent
ls skills/
```

If the user handed you the files some other way (an upload, a shared folder), just confirm you can see a `skills/` directory containing one folder per skill, each with a `SKILL.md` inside.

**Checkpoint 1:** `ls skills/` shows the skill folders, each folder contains a `SKILL.md`, and you have recorded the absolute path of the workspace root (run `pwd` from inside it). Later steps and every skill in this pack refer back to that path.

---

## Step 2: Install the skills

Every folder under `skills/` is one skill in the agentskills.io format. Install all of them.

The two install routes below leave the skills in different-looking places, and that is fine. A Skills Hub or tap install registers each skill in Hermes's managed skills store under a `<owner>/<repo>/<skill-name>` identity, with Hermes handling placement and updates. A direct folder copy puts each skill folder itself straight into your skills directory (for example `~/.hermes/skills/<skill-name>/`). Either shape is correct as long as every skill shows up in your installed-skills list; do not "fix" one shape into the other.

**Preferred: the native Skills Hub install.** If this repo lives on GitHub, Hermes can install directly from it, which also runs Hermes's security scan on each skill:

```bash
# one skill at a time, path maps repo path -> skill:
hermes skills install krusemediallc/hermes-ad-agent/skills/<skill-name>
```

Or register the whole repo as a tap and install from it:

```bash
hermes skills tap add krusemediallc/hermes-ad-agent
hermes skills search ad
hermes skills install krusemediallc/hermes-ad-agent/<skill-name>
```

Repeat `hermes skills install` for every folder you saw in `skills/` in Step 1. You can preview any skill first with `hermes skills inspect krusemediallc/hermes-ad-agent/<skill-name>`. Community installs show a third-party warning panel on first install; that is expected, show it to the user rather than suppressing it.

**Fallback: copy the folders.** If the hub install is unavailable in your build, or you only have a local copy of the repo, copy each skill folder into your skills directory:

```bash
cp -R skills/* ~/.hermes/skills/
```

One caveat on self-containment: each skill folder carries its own instructions and references, but the image and video generator skills may also read the shared prompt-template library that lives in the `image-ad-clone` skill's folder. Install all the skills together and this just works in either install shape; if a generator cannot find the template library (for example because only some skills were installed), it degrades gracefully and builds prompts from scratch instead. Also note that a manual copy skips the hub's security scanning, so prefer the hub route when you can.

**Verify discovery.** List your installed skills (use whichever surface your build has: the `skills_list()` tool, `/skills list` in chat, or `hermes skills list` in the terminal) and confirm every folder from `skills/` appears. Each installed skill is also available as a slash command matching its folder name (for example `/brand-setup`).

**Checkpoint 2:** every skill from this repo appears in your installed-skills list and is invokable as a slash command.

---

## Step 3: Verify the Arcads MCP connection

The creative-generation skills in this pack talk to the **Arcads MCP server** (`https://mcp.arcads.ai`). No API keys in env vars, no REST scripts; the MCP server handles auth itself.

**First, check whether it is already connected.** List your currently available tools and look for tools whose names start with `arcads_` (for example `arcads_list_products`, `arcads_generate_image`, `arcads_watch_asset`). Tool rosters differ between server versions, so always trust your live tool list over any list written in a skill.

**If the Arcads tools are missing, walk the user through connecting:**

1. The user needs an Arcads account with an active subscription and credits. If they do not have one, send them here to sign up: **https://arcads.ai/?via=hermes**
2. Add the server to your MCP config. In `~/.hermes/config.yaml` under `mcp_servers`:

   ```yaml
   mcp_servers:
     arcads:
       url: "https://mcp.arcads.ai"
       auth: oauth
   ```

   The exact auth mechanism Arcads uses is not publicly documented, so be defensive: try `auth: oauth` first and run `hermes mcp login arcads`. If the server does not advertise OAuth discovery, check Arcads' Help Center article "Arcads MCP" and your Hermes MCP catalog (`hermes mcp` or the dashboard's MCP page) for the current connect flow, and follow what your environment actually offers. The connect flow is tied to the user's app.arcads.ai login, so they may need to complete a browser sign-in.
3. Hot-reload MCP servers with `/reload-mcp` (or restart the session), then re-check the tool list.

**Checkpoint 3:** your tool list contains `arcads_` tools, and calling `arcads_list_products` (or another cheap read-only Arcads tool) returns a real response. Do not run any generation tool yet; generation costs credits.

---

## Step 4: Verify the Meta Ads MCP connection

All Meta actions (research, campaign building, launching, insights) go through **Meta's official Ads MCP server** at `https://mcp.facebook.com/ads`. Auth is Meta Business OAuth: no developer app, no App Review, no API token.

**First, check whether it is already connected.** Look in your tool list for tools whose names start with `ads_` (for example `ads_get_ad_accounts`, `ads_create_campaign`, `ads_insights_performance_trend`). Again, trust your live tool list; Meta ships new tools and renames things between versions.

**If the Meta tools are missing, walk the user through connecting:**

1. Add the server to `~/.hermes/config.yaml`:

   ```yaml
   mcp_servers:
     meta_ads:
       url: "https://mcp.facebook.com/ads"
       auth: oauth
   ```

2. Run the OAuth flow:

   ```bash
   hermes mcp login meta_ads
   ```

   The user signs in with their **Meta Business account** in the browser and approves which ad accounts the connector can access. Tokens are cached under `~/.hermes/mcp-tokens/`.
3. `/reload-mcp`, then re-check the tool list.

**Important warning to pass on to the user:** Meta's write tools have no confirmation screen of their own. That is exactly why the skills in this pack enforce the paused-by-default and confirm-before-spend rules; do not bypass them.

**Checkpoint 4:** calling `ads_get_ad_accounts` returns the user's ad account list. Show the user which accounts you can see and confirm they are the intended ones.

---

## Step 5: Run the brand setup interview

Run the **brand-setup** skill (`/brand-setup`). It interviews the user about their business and writes `BRAND.md` at the workspace root (the repo clone directory recorded in Checkpoint 1). Every other skill in this pack reads that file for brand voice, offer, audience, compliance notes, Meta assets, budget guardrails, and performance targets (a target CPA or target ROAS, which the reporting and performance skills use as their thresholds).

Every downstream skill checks for `BRAND.md` and offers to run brand-setup if it is missing, but doing it now means the user's first ad build just works.

### Demo mode (optional)

If the user wants to try the pipeline before committing a real brand, they can skip the interview for now and use the bundled demo brand instead. Copy the demo file from the repo to the workspace root:

```bash
cp assets/demo-brand/BRAND.md BRAND.md
```

The demo BRAND.md points at the parody products in `<workspace root>/assets/demo-products/`, so image and video skills resolve reference images without any extra setup. One hard limit: the demo landing URL is a placeholder on example.com, and `meta-ad-launcher` checks for example.com URLs and refuses to create any ad until a real URL is supplied (Meta rejects example.com). So demo mode exercises research, creative, and copy end to end, but a launch still needs a real destination URL. When the user is ready for their real brand, run `/brand-setup`; it replaces the demo file.

**Checkpoint 5:** `BRAND.md` exists at the workspace root (from the interview, or the demo copy), it includes Performance Targets (at least a target CPA or target ROAS), and the user has confirmed its contents look right.

---

## Step 6: Offer reporting automations (optional but recommended)

Ask the user whether they want scheduled performance reports and alerts. If yes, run the **ad-reporting-automations** skill (`/ad-reporting-automations`). It uses Hermes's built-in scheduler (cron jobs stored under `~/.hermes/cron/`) to run recurring insight pulls through the Meta MCP and deliver them wherever the user chats with you (Telegram, Discord, Slack, email, and so on, via the job's `deliver` target).

Reporting jobs are read-only by design: they call `ads_insights_*` and diagnostic tools and never modify campaigns, budgets, or delivery. If the user declines, just note that they can run it later.

**Checkpoint 6:** either a reporting job exists (verify with `/cron list` or `hermes cron list`) or the user has explicitly declined for now.

---

## Step 7: Final self-test and report

Run this checklist and record the result of each item:

1. **Meta MCP live:** call `ads_get_ad_accounts` and confirm it returns accounts.
2. **Arcads MCP live:** confirm `arcads_` tools are present in your tool list and one read-only call (such as `arcads_list_products` or `arcads_list_voices`) succeeds.
3. **Skills discoverable:** list installed skills and confirm every folder from this repo's `skills/` directory is present and triggerable as a slash command.
4. **BRAND.md exists at the workspace root** (from Step 5, real or demo).
5. **Scheduler state:** note whether a reporting job was created (Step 6).

Then **report to your user** in plain language:

- Which skills you installed and what each one is for (one line each).
- Which MCP servers are connected and which ad accounts / Arcads account they map to.
- The standing safety rules: everything is created paused, nothing is activated and no money is spent without their explicit confirmation, and Arcads generations always come with a credit estimate first.
- Suggested first commands to try (for example: "research my competitors' ads", "make me 3 image ad concepts", "build and launch a paused campaign").

Setup is complete when the user has seen and acknowledged that report.

---

## Troubleshooting

**`hermes: command not found`**: You may not be on a standard Hermes install, or the CLI is not on PATH. On Hostinger Managed Apps, use the in-browser terminal in hPanel (Hermes → Manage). Otherwise check how Hermes was installed in your environment.

**Skills installed but not triggering in conversation**: Confirm the skill folders are directly under your skills directory (each folder containing its own `SKILL.md`, not nested an extra level deep such as `skills/skills/<name>/`). Then re-list skills. Triggering matches on the `description` field in each SKILL.md.

**`hermes skills install` fails or rejects the repo**: Fall back to the copy method in Step 2. If the hub's security scan returns a warning verdict, show it to the user and let them decide; do not use `--force` without telling them.

**No `arcads_` tools after connecting**: Run `/reload-mcp` or restart the session. Confirm the entry in `config.yaml` is exactly `url: "https://mcp.arcads.ai"`. If auth fails, the user's Arcads subscription may be inactive or out of credits; have them log in at app.arcads.ai and check, or create an account at https://arcads.ai/?via=hermes. If your build's MCP page shows a different connect flow for Arcads, follow that flow.

**An Arcads tool that existed earlier returns `-32602` (tool not found)**: Known intermittent quirk on the Arcads server. Refresh your MCP tool catalog (`/reload-mcp`) and retry once. For asset polling, always use `arcads_watch_asset` rather than `arcads_get_asset`.

**Meta OAuth loop or `ads_get_ad_accounts` returns nothing**: The user must sign in with a Meta **Business** account that actually has ad-account access, and must approve the specific ad accounts during the consent screen. Re-run `hermes mcp login meta_ads` and have them re-approve. Cached tokens live in `~/.hermes/mcp-tokens/`; deleting the server's token file forces a fresh login.

**A Meta tool named in a skill does not exist in your session**: Server versions differ. Use your live tool list as the source of truth and pick the closest equivalent; the skills tell you to do this too.

**Cron job created but nothing is delivered**: Check `hermes cron list` for the job's status and look at run output under `~/.hermes/cron/output/<job_id>/`. Confirm the `deliver` target is a channel the user has actually connected (Telegram, Discord, Slack, email, etc.).

**Anything asks you for an API key or .env file**: Stop. Nothing in this pack uses raw API keys or REST endpoints. All Arcads calls go through the Arcads MCP and all Meta calls go through Meta's Ads MCP, and both handle auth through their own connect flows. If a request for a key appears, you are off the documented path.
