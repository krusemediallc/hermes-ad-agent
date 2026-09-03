# Hermes Ad Agent: Install Guide (for the installing agent)

You are a Hermes Agent (Nous Research) and you have been asked to set up the **Hermes Ad Agent** skill pack. This document is written to you. Work through the steps in order. Each step ends with a checkpoint; do not move on until the checkpoint passes. Talk to your user in plain language as you go, and ask before anything that costs money.

Three rules apply to everything below and to every skill you are about to install. They are not optional:

1. **Never spend money without explicit confirmation.** Before any Arcads generation, present a credit-cost estimate and wait for the user to confirm. Before any Meta action that could spend (activating an entity, resuming delivery, changing a budget), get explicit confirmation in the current conversation.
2. **Everything you create on Meta is created PAUSED.** Campaigns, ad sets, and ads. Always.
3. **Never fabricate numbers.** Report only what the Meta tools (MCP or CLI) actually returned.

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

- You can reach the internet (you will clone a repo, connect the Arcads MCP server, and connect Meta through either its MCP server or its command-line tool).

**Optional, only if Meta will be connected through the CLI route (Step 4, Route B).** The Meta Ads CLI is a Python tool that needs Python 3.12 or later, plus one of `uv`, `pipx`, or `pip` to install it. Check what you have:

```bash
python3 --version
uv --version || pipx --version || python3 -m pip --version
```

If the user connects Meta through the MCP route (Route A) instead, none of this is needed; skip it. An old or missing `python3` is not a blocker on its own either: in Step 4, `uv tool install --python 3.12 meta-ads` asks `uv` for a 3.12 interpreter and it can usually fetch one itself.

If any of these fail, tell the user what is missing before continuing. Your environment may differ from the defaults described here (Hermes versions vary); when in doubt, check your own configuration rather than assuming this document is right.

**Checkpoint 0:** terminal works, `~/.hermes/skills/` exists (or you know where your skills directory actually is), `hermes` CLI responds. If the CLI route is planned for Meta, you also know whether `python3` is 3.12 or later and which installer (`uv`, `pipx`, or `pip`) is available.

---

## Step 1: Get this repo into your workspace

You need a local copy of this repository so you can read `skills/`, this file, and `docs/walkthrough.md`.

**This clone directory is the workspace root.** The directory where this repo lands (default `~/hermes-ad-agent`) is the single working directory for everything the skill pack produces: `BRAND.md`, `research/`, `outputs/` (including the shared Arcads usage log at `outputs/arcads-usage-log.jsonl`), and `ad-runs/` all live at the workspace root. Every skill that mentions one of those paths means "relative to the workspace root". You will record its absolute path at the checkpoint below.

If Meta ends up connected through the Meta Ads CLI (Step 4, Route B), the CLI's `.env` file also lives at the workspace root, and `meta` commands are run from there so the file is picked up. This repo's `.gitignore` ignores `.env`, so the token in it is never committed.

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

The creative-generation skills in this pack talk to the **Arcads MCP server** (`https://mcp.arcads.ai`). No Arcads API key in env vars, no REST scripts; the MCP server handles auth itself.

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

## Step 4: Connect Meta (choose one of two routes)

All Meta actions in this pack (research, campaign building, launching, insights) go through one Meta backend. There are two supported backends, and either one gives the same launch and report capabilities in this pack. Pick one:

- **Route A: Meta Ads MCP (OAuth login, no token).** Meta's official Ads MCP server at `https://mcp.facebook.com/ads`. Auth is a Meta Business OAuth login in the browser: no developer app, no App Review, no API token. It has the broader tool surface (Ad Library search, ad previews, anomaly signals, diagnostics).
- **Route B: Meta Ads CLI (system user token).** The Meta Ads CLI (Meta's official command-line tool for the Marketing API) is a small Python tool, binary `meta`, that authenticates with a Meta system user access token. It works on any Hermes build that has a terminal, so it is the fallback whenever the MCP will not connect.

**Recommendation:** try Route A first. If it cannot be connected within a few minutes (Hermes builds differ in MCP support), go to Route B rather than stalling; the user loses nothing they need for this pack. If both end up available, prefer the MCP for its broader surface. Say once which backend you are using, and do not switch backends in the middle of a create sequence without telling the user.

**First, detect what is already there.**

1. Look in your tool list for tools whose names start with `ads_` (for example `ads_get_ad_accounts`, `ads_create_campaign`, `ads_insights_performance_trend`). If they are present, the Meta MCP is already connected: Route A is live, go straight to Checkpoint 4. Trust your live tool list; Meta ships new tools and renames things between versions.
2. Otherwise, in the terminal, from the workspace root:

   ```bash
   meta auth status
   ```

   If it prints a (masked) token, run `meta ads adaccount list --output json`. If that returns accounts, the Meta Ads CLI is already configured: Route B is live, go straight to Checkpoint 4.
3. If neither works, Meta is not connected yet. Ask the user which route they want (or apply the recommendation above) and walk them through it below.

### Route A: Meta Ads MCP (OAuth login, no token)

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

Route A is connected when `ads_` tools appear in your tool list and `ads_get_ad_accounts` returns the user's ad accounts. If your build has no MCP support, the login never completes, or the tools still do not appear after a reload and a session restart, stop spending time on it and switch to Route B.

### Route B: Meta Ads CLI (system user token)

Four parts: install the CLI, get a token, configure, verify.

**(a) Install the CLI.** The PyPI package is `meta-ads` (publisher Meta Platforms, Inc.) and it requires Python 3.12 or later. Prefer an isolated install so it does not touch the system Python:

```bash
uv tool install --python 3.12 meta-ads
```

If `uv` is not available:

```bash
pipx install meta-ads
```

If neither is available, use a virtual environment plus pip, then call the binary from the venv (or put its `bin/` directory on PATH):

```bash
python3 -m venv ~/.venvs/meta-ads
~/.venvs/meta-ads/bin/pip install meta-ads
```

Verify the install:

```bash
meta --version
```

Command shape is `meta ads <resource> <action> [options]` (noun then verb). Global options include `--output json|table|plain`, `--limit N`, `--debug`, `--no-color`, `--no-input`, `--help`. Always pass `--output json` when you run it yourself. Exit codes: 0 success, 3 authentication error, 4 API error. Trust `--help` output over any flag written in a skill or in this guide; CLI versions differ.

**(b) Get a system user access token.** You cannot click through Business Suite yourself; the user does this part in the browser. Relay these steps to them:

1. In Meta Business Suite, open Settings → Users → System Users → Add. Role: **Admin**.
2. Assign assets to that system user: the ad account(s), the Facebook Page(s), and any datasets/pixels or catalogs the pack should be able to use. An asset that is not assigned here will be invisible to the CLI.
3. In Meta for Developers (developers.facebook.com), add the system user as an **App Admin** on an app. The user needs an app of their own there; if they have none, creating one is a few clicks. Then choose **Generate New Token**, select that app, and grant these scopes: `business_management`, `ads_management`, `pages_show_list`, `pages_read_engagement`, `pages_manage_ads`, `catalog_management`, `read_insights`.
4. Copy the token once; Meta does not show it again.

Handling the token: have the user paste it directly into the terminal (into the `.env` file or the `meta auth` prompt below), not into chat with you, wherever that is avoidable. If it does land in chat, tell them to treat it as exposed and to generate a new token once setup is done. Never write it into `BRAND.md`, job prompts, or any committed file.

Two notes to pass on to the user:

- System user tokens have no scheduled expiry, but Meta can invalidate one (a password change, a role removal, a security event). The fix is to generate a new token the same way and update `.env`.
- This guide cannot promise that App Review is never needed. Marketing API "Development access" normally covers ad accounts the business itself administers, which is the case here. If reads work but a call fails with a permissions error, have the user check the app's Marketing API access level in the app dashboard on Meta for Developers.

**(c) Configure.** The CLI reads `ACCESS_TOKEN` (required) and `AD_ACCOUNT_ID` (required for most commands, in the `act_` form, for example `act_123456`); `BUSINESS_ID` is optional and only matters for catalog and dataset commands, which this pack does not use. Precedence, highest first: command-line flags (for example `--ad-account-id`), then shell environment variables, then a `.env` file in the current working directory, then user-level config under `~/.config/meta/`.

The placement this pack expects is a `.env` at the workspace root (the path recorded in Checkpoint 1), with `meta` always run from that directory. Have the user create it in the terminal (any editor works; `nano .env` is fine), with this exact format:

```
ACCESS_TOKEN='<ACCESS_TOKEN>'
AD_ACCOUNT_ID='<AD_ACCOUNT_ID>'
```

Then tighten permissions:

```bash
cd <workspace root>
chmod 600 .env
```

Alternatively, run `meta auth` from the workspace root and follow its prompts; it saves the token for you (to `.env` or the environment; check `meta auth --help` for where your version writes). If the user does not know the ad account ID yet, try `ACCESS_TOKEN` alone first and run `meta ads adaccount list --output json` to see the accounts the system user was assigned, then add `AD_ACCOUNT_ID` from that output. If your CLI version refuses to run that command without `AD_ACCOUNT_ID`, the user can read the ID in Ads Manager (the `act=` number in the URL) and add it first.

**(d) Verify.** From the workspace root:

```bash
meta auth status
meta ads adaccount list --output json
meta ads page list --output json
```

`meta auth status` prints the masked token. The second command lists the ad accounts the system user can see; the third lists the Facebook Pages. Show the user which accounts and Pages are visible and confirm they are the intended ones (`meta ads adaccount current` shows which single account the configuration points at). If an expected account or Page is missing, it was not assigned to the system user in step (b) 2. One gap to note now: the CLI has no Instagram account listing, so if the user wants ads to run under an Instagram identity, ask them for the Instagram account ID (Business Settings → Instagram accounts) so brand-setup can record it in Step 5.

**Important warning to pass on to the user, on either route:** Meta's write operations, MCP tools and CLI commands alike, have no confirmation screen of their own. That is exactly why the skills in this pack enforce the paused-by-default and confirm-before-spend rules; do not bypass them.

**Checkpoint 4:** EITHER `ads_get_ad_accounts` (Route A) OR `meta ads adaccount list --output json` (Route B) returns the user's ad accounts, and the user has confirmed they are the intended ones. Record which route is live (`mcp` or `cli`); you will hand that to brand-setup in Step 5, which writes it as the "Meta connection" line under `## Meta Assets` in `BRAND.md`.

---

## Step 5: Run the brand setup interview

Run the **brand-setup** skill (`/brand-setup`). It interviews the user about their business and writes `BRAND.md` at the workspace root (the repo clone directory recorded in Checkpoint 1). Every other skill in this pack reads that file for brand voice, offer, audience, compliance notes, Meta assets, budget guardrails, and performance targets (a target CPA or target ROAS, which the reporting and performance skills use as their thresholds).

Tell brand-setup which Meta route is live from Checkpoint 4. It records that under `## Meta Assets` as a "Meta connection" line (`mcp` or `cli`). Skills treat that line as a hint and still verify the live backend at runtime, so it never has to be perfect, but it saves a round of detection. On the CLI route it also needs the ad account ID, Page ID, and (if any) Instagram account ID you found in Step 4, since the CLI cannot look up Instagram accounts on its own.

Every downstream skill checks for `BRAND.md` and offers to run brand-setup if it is missing, but doing it now means the user's first ad build just works.

### Demo mode (optional)

If the user wants to try the pipeline before committing a real brand, they can skip the interview for now and use the bundled demo brand instead. Copy the demo file from the repo to the workspace root:

```bash
cp assets/demo-brand/BRAND.md BRAND.md
```

The demo BRAND.md points at the parody products in `<workspace root>/assets/demo-products/`, so image and video skills resolve reference images without any extra setup. One hard limit: the demo landing URL is a placeholder on example.com, and `meta-ad-launcher` checks for example.com URLs and refuses to create any ad until a real URL is supplied (Meta rejects example.com). So demo mode exercises research, creative, and copy end to end, but a launch still needs a real destination URL. When the user is ready for their real brand, run `/brand-setup`; it replaces the demo file.

**Checkpoint 5:** `BRAND.md` exists at the workspace root (from the interview, or the demo copy), it includes Performance Targets (at least a target CPA or target ROAS), and the user has confirmed its contents look right. If it came from the interview, its `## Meta Assets` section names the Meta connection (`mcp` or `cli`) that matches Checkpoint 4.

---

## Step 6: Offer reporting automations (optional but recommended)

Ask the user whether they want scheduled performance reports and alerts. If yes, run the **ad-reporting-automations** skill (`/ad-reporting-automations`). It uses Hermes's built-in scheduler (cron jobs stored under `~/.hermes/cron/`) to run recurring insight pulls through the Meta backend (the MCP's `ads_insights_*` tools on Route A, or `meta ads insights get` on Route B) and deliver them wherever the user chats with you (Telegram, Discord, Slack, email, and so on, via the job's `deliver` target).

Reporting jobs are read-only by design: they call insights and entity reads only. On the MCP that means `ads_insights_*` and `ads_get_*` tools; on the CLI it means `meta ads insights get` and `meta ads <resource> list|get`. They never call `ads_activate_entity`, `ads_update_entity`, or any `ads_create_*` tool, and never run `meta ads ... update --status ACTIVE`, `--daily-budget`, `create`, or `delete`. If the user declines, just note that they can run it later.

**Checkpoint 6:** either a reporting job exists (verify with `/cron list` or `hermes cron list`) or the user has explicitly declined for now.

---

## Step 7: Final self-test and report

Run this checklist and record the result of each item:

1. **Meta backend live:** EITHER `ads_get_ad_accounts` (MCP) OR `meta ads adaccount list --output json` (CLI) returns accounts; note which one.
2. **Arcads MCP live:** confirm `arcads_` tools are present in your tool list and one read-only call (such as `arcads_list_products` or `arcads_list_voices`) succeeds.
3. **Skills discoverable:** list installed skills and confirm every folder from this repo's `skills/` directory is present and triggerable as a slash command.
4. **BRAND.md exists at the workspace root** (from Step 5, real or demo).
5. **Scheduler state:** note whether a reporting job was created (Step 6).

Then **report to your user** in plain language:

- Which skills you installed and what each one is for (one line each).
- Which Meta route is connected (MCP or CLI) and which ad accounts it can see, and which Arcads account the Arcads MCP maps to.
- The standing safety rules: everything is created paused, nothing is activated and no money is spent without their explicit confirmation, and Arcads generations always come with a credit estimate first.
- Suggested first commands to try (for example: "research my competitors' ads", "make me 3 image ad concepts", "build and launch a paused campaign").

**Checkpoint 7:** the user has seen and acknowledged that report. Setup is complete.

---

## Troubleshooting

### General

**`hermes: command not found`**: You may not be on a standard Hermes install, or the CLI is not on PATH. On Hostinger Managed Apps, use the in-browser terminal in hPanel (Hermes → Manage). Otherwise check how Hermes was installed in your environment.

**Skills installed but not triggering in conversation**: Confirm the skill folders are directly under your skills directory (each folder containing its own `SKILL.md`, not nested an extra level deep such as `skills/skills/<name>/`). Then re-list skills. Triggering matches on the `description` field in each SKILL.md.

**`hermes skills install` fails or rejects the repo**: Fall back to the copy method in Step 2. If the hub's security scan returns a warning verdict, show it to the user and let them decide; do not use `--force` without telling them.

**Cron job created but nothing is delivered**: Check `hermes cron list` for the job's status and look at run output under `~/.hermes/cron/output/<job_id>/`. Confirm the `deliver` target is a channel the user has actually connected (Telegram, Discord, Slack, email, etc.).

### Arcads MCP

**No `arcads_` tools after connecting**: Run `/reload-mcp` or restart the session. Confirm the entry in `config.yaml` is exactly `url: "https://mcp.arcads.ai"`. If auth fails, the user's Arcads subscription may be inactive or out of credits; have them log in at app.arcads.ai and check, or create an account at https://arcads.ai/?via=hermes. If your build's MCP page shows a different connect flow for Arcads, follow that flow.

**An Arcads tool that existed earlier returns `-32602` (tool not found)**: Known intermittent quirk on the Arcads server. Refresh your MCP tool catalog (`/reload-mcp`) and retry once. For asset polling, always use `arcads_watch_asset` rather than `arcads_get_asset`.

### Meta, Route A (Meta Ads MCP)

**Route A: the Meta MCP will not connect at all**: Your Hermes build may not support remote MCP servers, or the OAuth callback may not work in your environment. Do not stall on it. Go to Route B in Step 4; the pack works the same way on the CLI.

**Route A: Meta OAuth loop or `ads_get_ad_accounts` returns nothing**: The user must sign in with a Meta **Business** account that actually has ad-account access, and must approve the specific ad accounts during the consent screen. Re-run `hermes mcp login meta_ads` and have them re-approve. Cached tokens live in `~/.hermes/mcp-tokens/`; deleting the server's token file forces a fresh login.

**Route A: a Meta tool named in a skill does not exist in your session**: Server versions differ. Use your live tool list as the source of truth and pick the closest equivalent; the skills tell you to do this too.

### Meta, Route B (Meta Ads CLI)

**Route B: `meta: command not found`**: The binary installed somewhere that is not on PATH. `uv tool` installs shims into its own bin directory (`uv tool dir --bin` prints it; `uv tool update-shell` adds it to PATH), `pipx` uses `~/.local/bin` (`pipx ensurepath`), and a venv keeps it under `<venv>/bin/`. Add the right directory to PATH, then re-open the shell (or start a new terminal session) and try `meta --version` again.

**Route B: `meta auth status` shows no token**: The CLI looks, in order, at command-line flags, shell environment variables, a `.env` in the current working directory, and user-level config under `~/.config/meta/`. The most common cause is running `meta` from a different directory than the one holding `.env`. Run it from the workspace root, or confirm the file is there with `ls -la .env` and that it contains `ACCESS_TOKEN='...'`.

**Route B: a command exits with code 3**: Authentication error. The token is invalid, was invalidated (password change, role removal, security event), or is missing one of the required scopes. Have the user generate a new token from the system user with the full scope list in Step 4 (b) and update `.env`.

**Route B: a command exits with code 4**: API error. Read the message the CLI prints; re-run with `--debug` for the full request and response. If a flag was rejected, run the same command with `--help` to see the flag names your version actually supports. If Meta says the account, Page, or object is not accessible, check that the system user has that ad account and Page assigned in Business Settings.

**Route B: `meta ads adaccount list` returns an empty list**: The token works but the system user has no ad accounts assigned. In Business Settings, assign the ad account(s) (and the Page(s)) to the system user, then re-run the command. No new token is needed for an asset assignment.

**Route B: Python version too old**: The CLI needs Python 3.12 or later. Install it with `uv tool install --python 3.12 meta-ads`, which pins the tool to a 3.12 interpreter (and can fetch one), instead of relying on the system `python3`.

**Route B: a flag named in a skill does not exist**: CLI versions differ. Run the command with `--help` and use the flag names it prints; trust `--help` over anything written in a skill or in this guide.

### Keys and secrets

**Something asks you for an API key or a `.env` file**: Arcads never needs a key; all Arcads calls go through the Arcads MCP, which handles auth through its own connect flow. Meta needs a token ONLY on Route B (the system user token), and the only places it belongs are the workspace `.env` (gitignored) or the shell environment. Anything that asks for a key anywhere else (a skill file, `BRAND.md`, a job prompt, chat), or asks for an Arcads key at all, is off the documented path. Stop and check with the user.
