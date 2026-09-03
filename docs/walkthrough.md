# Hermes Ad Agent: Follow-Along Walkthrough

This guide matches the video chapter by chapter. Each chapter tells you the goal, exactly what to say to Hermes (copy-paste the prompts), and what success looks like before you move on.

A note before you start: Hermes will never spend money without asking you first. Every ad it builds on Meta is created **paused**, and every Arcads generation comes with a cost you approve first: the rate from your Arcads plan, or, if the rate is unknown, a maximum number of credits you set for one calibration run. Retries and quality fixes cost credits too, so Hermes asks before those as well. If it ever seems to skip that, stop and say "do not spend anything without asking me."

---

## Chapter 1: Get Hermes running on Hostinger

**Goal:** a live Hermes Agent you can chat with, hosted for you, no server setup.

1. Grab a Hostinger plan that includes Managed Apps here: **https://www.hostg.xyz/SHJtI** and use code **mrpaidsocial** for an extra 10% off yearly plans.
2. In hPanel, go to **Managed Apps → Hermes** and install it. Hostinger runs it for you (auto-updates, backups, its own dashboard).
3. Open **Hermes → Manage**. From here you can open the web chat interface, the in-browser terminal, and settings.
4. Follow Hermes's onboarding: pick how it accesses an AI model (the bundled option with included credits, or your own provider key), then connect a chat channel if you want Hermes in Telegram, WhatsApp, Discord, Slack, or email. Your install may come with a channel preconnected; if not, the onboarding walks you through it.

**Success looks like:** you send Hermes a message ("hey, are you alive?") from the web UI or your chat app and get a reply.

---

## Chapter 2: Install the Hermes Ad Agent skill pack

**Goal:** Hermes learns the whole ad workflow: brand setup, creative generation, copywriting, launching, reporting.

Say to Hermes (paste the repo link you got with this guide):

> Set up the Hermes Ad Agent skill pack from this repo: https://github.com/krusemediallc/hermes-ad-agent. Read its SETUP.md and follow it step by step. Check in with me at each checkpoint.

Hermes will clone the repo, install every skill, and then move on to connecting Meta (one of two routes) and Arcads (next two chapters are part of the same guided setup). Right after the install, Hermes points its working directory at the pack, so the Project Context panel in the dashboard stops saying "No project context file found" and shows the pack's AGENTS.md instead. After the brand interview in Chapter 4, it also saves a short profile of you and your setup to its own memory, so every new conversation starts already oriented.

**Want to try it before using your real brand?** The repo ships with a demo mode: a sample BRAND.md and a set of parody demo products. Say:

> Set me up in demo mode: copy the demo BRAND.md from assets/demo-brand so I can test the pipeline with the parody products first.

You can run research, creatives, and copy against the demo brand, then run `/brand-setup` later to replace it with your real one. Note the demo brand's landing URL is a placeholder, so you can build everything except an actual launched ad (Meta needs a real URL).

**Success looks like:** Hermes lists the skills it installed and confirms each one is available as a slash command. Ask it:

> List the ad skills you just installed and give me one line on what each does.

---

## Chapter 3: Connect Meta (MCP or CLI)

**Goal:** Hermes can see and manage your ad accounts. There are two routes and you only need one. Route A is Meta's official Ads MCP server, the wider tool surface. Route B is the Meta Ads CLI (Meta's official command-line tool for the Marketing API), authenticated with a system user token, for when the MCP will not connect on your build or when an MCP operation is missing.

Both routes need a token you create once. Neither is "just log in with Facebook": the hosted MCP does not accept a generic OAuth login from a headless server, and it does not accept the CLI's system user token either. That is fine; it is about ten minutes of clicking, and Hermes tells you exactly where.

### Route A: the Meta Ads MCP

If the guided setup hasn't done it already, say:

> Connect Meta's official Ads MCP server. Walk me through creating the user access token it needs, and don't ask me to paste it into this chat.

On Hostinger, the working path is a **Meta user access token** carrying seven scopes (`ads_mcp_management`, `ads_read`, `ads_management`, `catalog_management`, `business_management`, `pages_show_list`, `instagram_basic`). Hermes points you to Meta for Developers: you generate the token in the Graph API Explorer with your own Meta app, exchange it right away for a long-lived token (about 60 days), and store it as a managed secret (Hostinger's environment settings for the Hermes app, or the env file Hermes names). The MCP config only ever references the variable name, never the token itself. Then you restart the app so it picks up the secret.

Two things to know up front:

- Meta gives no refresh token for this route, so the token expires in roughly 60 days and renewal is manual. Hermes records the expiry date and you should set a calendar reminder a week ahead. Reporting jobs check it and will shout, not go quiet, if it lapses.
- The browser OAuth route only works if you own a pre-registered Meta app and the surface you use supports its exact callback. Most Hostinger installs will not; that is why the token route is the default here.

**Success looks like:** Hermes lists your ad accounts **with their IDs** and tells you the token's expiry date, and it does that from a fresh conversation, not just the one where you set it up. A browser login screen is not success. Verify with:

> Start fresh: list the ad accounts you can see, with IDs, tell me which pages are connected to the first one, and tell me when the Meta token expires.

Pick the account you want Hermes working in by name **and** ID (two accounts can share a name).

### Route B: the Meta Ads CLI

If the MCP will not connect on your Hermes build (or you would rather use a plain CLI), say:

> The Meta MCP won't connect on my build. Set up the Meta Ads CLI instead and walk me through creating the system user token.

Hermes installs the `meta-ads` package (it needs Python 3.12 or later), then tells you exactly where to click in Meta Business Suite to create a system user, assign it your ad account and Facebook Page, and generate a token with the scopes it lists (generating the token needs a Meta developer app of your own; creating one is a few clicks and Hermes points you to it). You paste the token into the in-browser terminal from Chapter 1, never into chat. It is saved to a gitignored `.env` at the workspace root, and then Hermes lists your ad accounts.

**Success looks like:** Hermes lists your ad accounts by name. Verify with:

> List the ad accounts and pages the Meta Ads CLI can see.

One note on the two routes: competitor research (the Meta Ad Library) needs Route A; everything else in this guide works on both. A few build operations go the other way: uploading a local file and building one ad that carries all five primary texts and five headlines currently need Route B, so if you can, set up both. Hermes tells you before it builds anything if the route you connected cannot do what you asked.

### Teach Hermes your account history

Once Meta is connected (either route), have Hermes study what your account has already done before it builds anything. Say:

> Audit my ad account and build the account memory.

Hermes runs a read-only deep dive of your last 90 days (structure, targeting, creatives, copy, winners, losers) and writes it to a memory file, one per ad account. It only reads; nothing in your account changes. This is the step that makes everything after it smarter: every new ad Hermes builds is informed by what already works in your account, from the hooks and audiences that convert to the fatigued ads not worth copying. The audit also feeds the brand interview in the next chapter, so brand-setup can confirm real defaults from your account instead of asking cold. It captures your exact settings too (targeting, placements, bidding, attribution, and the Advantage+ creative enhancements you have on or off), so new ads can mirror what already runs; the Meta MCP cannot read all of those on its own, so setting up the Route B system user token as well, even if you connected through the MCP, gets you the complete picture.

If you're testing in demo mode, or your ad account is brand new with nothing in it, skip this for now; Hermes notes the skip and you can run the audit any time later.

**Success looks like:** Hermes shows you a summary of the audit (top ads, spend, what's working and what's not) and confirms a memory file exists for each account you want it managing.

---

## Chapter 4: Connect the Arcads MCP

**Goal:** Hermes can generate images, videos, UGC-style actor videos, and voiceovers through Arcads.

You need an Arcads account with an active subscription and credits. Sign up here if you don't have one: **https://arcads.ai/?via=hermes**

Then say:

> Connect the Arcads MCP server and walk me through signing in.

Hermes adds `https://mcp.arcads.ai` to its MCP config and walks you through the connect flow tied to your app.arcads.ai login.

**Success looks like:** Hermes confirms the Arcads tools are available, without generating anything yet. Verify with:

> List the Arcads tools you have available, and show me my Arcads products if any exist. Don't generate anything.

Before moving on, also run the brand interview if setup hasn't already:

> Run brand-setup so you know my business.

Answer its questions; Hermes writes a BRAND.md it will reuse for every ad from now on.

---

## Chapter 5: Build image ads

**Goal:** finished static ad images for your brand, made from a plain-English request.

Say:

> Make me 3 image ad concepts for my brand. Use my BRAND.md. Show me the concepts and the estimated Arcads credit cost before you generate anything.

Hermes proposes concepts, tells you the cost (your plan rate, or asks you for a maximum if the rate is unknown), and waits for your go-ahead. Reply with which concepts you want (for example "run 1 and 3"), and it generates, quality-checks the images, and shows you the results.

**Success looks like:** you have ad images saved in your workspace, you approved the cost before anything was generated, and any weird generations (garbled text, extra fingers) got flagged in QA, with Hermes asking you before regenerating anything, since a regeneration costs credits too.

---

## Chapter 6: Build video ads

**Goal:** a scroll-stopping video ad, either product b-roll or a UGC-style talking person.

For a UGC-style ad, say:

> Make me a UGC-style video ad for my main offer. Show me the actor options, the script, and the credit estimate before generating.

For product b-roll, say:

> Make me a 10 second product video ad for [your product]. Vertical, for Instagram Reels. Show me the plan and credit estimate first.

Two approval gates here, and that's by design: you approve the **spoken script word for word** (if anyone talks in the video) and you approve the **cost** (your plan rate, or a maximum you set when the rate is unknown), both before generation starts. Video takes a few minutes to render; Hermes polls until it's done.

**Success looks like:** a finished vertical video in your workspace that matches the script you approved.

---

## Chapter 7: Let Hermes write your ad copy

**Goal:** primary text, headlines, and hooks that sound like a person wrote them, matched to your brand voice.

Say:

> Write me 5 variations of primary text and headlines for the image ads from earlier. Match my brand voice from BRAND.md, and make it sound human, not like AI wrote it.

Push back like you would with a copywriter:

> Variation 2 is close. Make it punchier and cut the first sentence.

**Success looks like:** copy you'd actually run, in your voice, with hooks/headlines/primary text clearly laid out so you can mix and match.

---

## Chapter 8: Launch ads without opening Ads Manager

**Goal:** a real campaign, ad set, and ads live in your Meta account, built entirely from chat, created paused so nothing spends yet.

Say:

> Launch these: create a new campaign with one ad set and the 3 ads we made (image ads plus the copy from earlier). [Your objective, audience, and daily budget here.] Create everything paused and show me previews before I turn anything on.

Before anything is created, Hermes shows you the whole plan and waits:

- **The copy pool, verbatim.** Every primary text, headline, description, the call to action, the destination URL, and which media each one pairs with, printed in full, with any validator warnings (length, placeholder URL, missing field). You approve that exact text. Hermes fingerprints what you approved, so if a single word changes afterward it has to ask again. "Get these built" before you have seen the pool is not an approval, and Hermes will not treat it as one.
- **One ad unit per creative, not one ad per line.** The five primary texts, five headlines, and three descriptions all go inside a single flexible ad on each image or video. Hermes never fans them out into five ads and never quietly drops to one variant. If the Meta route you connected cannot build that unit (the MCP currently cannot), it stops before creating anything and asks whether to build that creative through the Meta Ads CLI or to explicitly accept a single variant.
- **The video cover is a frame from the video.** Meta's preferred thumbnail, or a frame you pick. Never another ad's image. Hermes reads it back after processing and looks at the preview before it tells you the ad is done.

Then Hermes uploads the creatives, builds the campaign, ad set, and ads through Meta (MCP or CLI), writing every returned ID to a run ledger as it goes. On the MCP route it hands you preview links; on the CLI route there are no previews, so you review the paused ads in Ads Manager by name. Everything is read back and confirmed **PAUSED** before Hermes reports success. One requirement: the ads need a real destination URL. If you've been testing in demo mode, the demo BRAND.md's placeholder (example.com) landing page won't fly; the launcher checks for placeholder URLs and will ask you for a real one before it creates anything, because Meta rejects example.com links. When you've reviewed the previews (or the paused ads in Ads Manager) and you're ready to spend:

> The previews look good. Activate the campaign.

Hermes will confirm the spend implication once more, then activate.

**If the Hostinger web chat says "Session expired, reload the page":** that message comes from the web UI's cookie rotation, not from your conversation ending. Refresh the page once. Do not resend the build request; the run ledger and its run key mean a repeated request is caught rather than built twice, but the safest move is still to ask "where did the launch get to?" and let Hermes read its ledger back.

**Success looks like:** the campaign appears in your Ads Manager exactly as described, each ad carrying the full copy pool you approved, paused until the moment you explicitly said go. Nothing was activated and no budget moved without your say-so.

---

## Chapter 9: Automated reporting and alerts

**Goal:** Hermes checks your account on a schedule and messages you the numbers, so you never have to remember to look.

Say:

> Set up my ad reporting automations. I want a daily performance summary every morning at 8, and alert me if anything looks off. Send it to this chat.

Hermes uses its built-in scheduler to create the recurring jobs and delivers reports to whatever channel you're chatting in (Telegram, Discord, Slack, email, and more). The jobs are read-only: they pull insights (and anomaly signals on the MCP route), they never touch your budgets or campaigns. The "anything looks off" thresholds aren't guessed, either: alerts compare your numbers against the Performance Targets (target CPA or target ROAS) you set in BRAND.md during brand-setup, so if the alerts feel too tight or too loose, update those targets.

Try an on-demand pull too:

> How did my ads do in the last 7 days? Only give me numbers the Meta tools actually returned.

**Success looks like:** a scheduled report lands in your chat on time with real numbers from your account, and asking "how are my ads doing?" any time gets you a straight answer.

---

## That's the whole loop

Brand in BRAND.md, creatives from Arcads, copy in your voice, launched paused through Meta (MCP or CLI), and reporting on a schedule. From here, everything is just talking to Hermes. Two links if you skipped ahead:

- Hostinger (host Hermes): https://www.hostg.xyz/SHJtI with code **mrpaidsocial**
- Arcads (creative generation): https://arcads.ai/?via=hermes
