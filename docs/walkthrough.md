# Hermes Ad Agent: Follow-Along Walkthrough

This guide matches the video chapter by chapter. Each chapter tells you the goal, exactly what to say to Hermes (copy-paste the prompts), and what success looks like before you move on.

A note before you start: Hermes will never spend money without asking you first. Every ad it builds on Meta is created **paused**, and every Arcads generation comes with a credit estimate you have to approve. If it ever seems to skip that, stop and say "do not spend anything without asking me."

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

Hermes will clone the repo, install every skill, and then move on to connecting Meta (one of two routes) and Arcads (next two chapters are part of the same guided setup).

**Want to try it before using your real brand?** The repo ships with a demo mode: a sample BRAND.md and a set of parody demo products. Say:

> Set me up in demo mode: copy the demo BRAND.md from assets/demo-brand so I can test the pipeline with the parody products first.

You can run research, creatives, and copy against the demo brand, then run `/brand-setup` later to replace it with your real one. Note the demo brand's landing URL is a placeholder, so you can build everything except an actual launched ad (Meta needs a real URL).

**Success looks like:** Hermes lists the skills it installed and confirms each one is available as a slash command. Ask it:

> List the ad skills you just installed and give me one line on what each does.

---

## Chapter 3: Connect Meta (MCP or CLI)

**Goal:** Hermes can see and manage your ad accounts. There are two routes and you only need one. Route A is Meta's official Ads MCP server: no developer app, no tokens, just a Meta Business login. Route B is the Meta Ads CLI (Meta's official command-line tool for the Marketing API), authenticated with a system user token, for Hermes builds where the MCP will not connect.

### Route A: the Meta Ads MCP

If the guided setup hasn't done it already, say:

> Connect Meta's official Ads MCP server and walk me through the login.

Hermes adds `https://mcp.facebook.com/ads` to its MCP config and starts an OAuth login. You'll get a browser link: sign in with your **Meta Business account** and approve which ad accounts Hermes may access. Only approve the accounts you actually want it working in.

**Success looks like:** Hermes lists your ad accounts by name. Verify with:

> List the ad accounts you can see and tell me which pages are connected to the first one.

### Route B: the Meta Ads CLI

If the MCP will not connect on your Hermes build (or you would rather use a plain CLI), say:

> The Meta MCP won't connect on my build. Set up the Meta Ads CLI instead and walk me through creating the system user token.

Hermes installs the `meta-ads` package (it needs Python 3.12 or later), then tells you exactly where to click in Meta Business Suite to create a system user, assign it your ad account and Facebook Page, and generate a token with the scopes it lists (generating the token needs a Meta developer app of your own; creating one is a few clicks and Hermes points you to it). You paste the token into the in-browser terminal from Chapter 1, never into chat. It is saved to a gitignored `.env` at the workspace root, and then Hermes lists your ad accounts.

**Success looks like:** Hermes lists your ad accounts by name. Verify with:

> List the ad accounts and pages the Meta Ads CLI can see.

One note on the two routes: competitor research (the Meta Ad Library) needs Route A; everything else in this guide works on both.

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

Hermes proposes concepts, estimates credits, and waits for your go-ahead. Reply with which concepts you want (for example "run 1 and 3"), and it generates, quality-checks the images, and shows you the results.

**Success looks like:** you have ad images saved in your workspace, you approved a credit estimate before anything was generated, and any weird generations (garbled text, extra fingers) got caught and regenerated automatically.

---

## Chapter 6: Build video ads

**Goal:** a scroll-stopping video ad, either product b-roll or a UGC-style talking person.

For a UGC-style ad, say:

> Make me a UGC-style video ad for my main offer. Show me the actor options, the script, and the credit estimate before generating.

For product b-roll, say:

> Make me a 10 second product video ad for [your product]. Vertical, for Instagram Reels. Show me the plan and credit estimate first.

Two approval gates here, and that's by design: you approve the **spoken script word for word** (if anyone talks in the video) and you approve the **credit estimate**, both before generation starts. Video takes a few minutes to render; Hermes polls until it's done.

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

Hermes uploads the creatives, builds the campaign, ad set, and ads through Meta (MCP or CLI). On the MCP route it hands you preview links; on the CLI route there are no previews, so you review the paused ads in Ads Manager by name. Everything sits **paused**. One requirement: the ads need a real destination URL. If you've been testing in demo mode, the demo BRAND.md's placeholder (example.com) landing page won't fly; the launcher checks for placeholder URLs and will ask you for a real one before it creates anything, because Meta rejects example.com links. When you've reviewed the previews (or the paused ads in Ads Manager) and you're ready to spend:

> The previews look good. Activate the campaign.

Hermes will confirm the spend implication once more, then activate.

**Success looks like:** the campaign appears in your Ads Manager exactly as described, paused until the moment you explicitly said go. Nothing was activated and no budget moved without your say-so.

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
