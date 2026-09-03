# Hostinger WebUI: false "Session expired, reload the page" errors

If the Hermes dashboard on a Hostinger managed app shows **"Session expired, reload the page"** in the middle of a conversation, the conversation has almost certainly not expired. This page explains the cause, the symptom, the safe procedure, and why a resubmitted launch cannot create a duplicate campaign.

## Cause

The dashboard authenticates with a session cookie plus a CSRF token. After a managed-app restart or redeploy (which is exactly what a Step 4 environment change requires), the app mints fresh session and CSRF material, and open browser tabs keep sending the old pair until they reload. The server rejects the stale CSRF token and the UI renders that rejection as an expired session. On the first real install, the server had 176 valid sessions and had minted 71 of them within ten minutes of one restart, each one a tab or client re-handshaking. None of those were conversation expiries.

Other triggers that look the same: several dashboard tabs open on the same instance (each rotation invalidates the others), a browser that cleared cookies mid-session, or a reverse proxy that changed the cookie path.

## Symptom

- The banner appears right after a restart, a redeploy, or an env change, or when a second tab was opened.
- The gateway itself is up: `hermes mcp list` and `hermes cron list` work from the terminal, and the previous message may already have been processed.
- The conversation history is intact after one reload.

If the banner appears repeatedly after a single reload with only one tab open, that is a different problem (check the app logs in hPanel); the rest of this page assumes the common case.

## Safe procedure

1. **Refresh once.** Reload the page exactly one time and sign in again if asked. Do not click "retry" or "send" on the previous message.
2. **Do not resend a write request.** If the last message was a launch, an activation, a budget change, or a generation, assume it may have been received and processed. Resending it is how duplicates happen on systems without a run key. This pack has one (see below), but the rule still stands: read before you write.
3. **Check for an in-flight run before doing anything else.** From the workspace root:

   ```bash
   ls -lt ad-runs/ | head
   cat ad-runs/<newest-run>/ledger.json
   ```

   The ledger shows the approved plan, the run key, and every Meta object the run has created so far with its status and timestamp. If a run is in progress, tell the agent to **resume from the ledger** (it reads remote state and the ledger first, then continues), not to start over.
4. **Close duplicate tabs.** Keep one dashboard tab per instance. Extra tabs rotate each other's sessions and reproduce the banner.
5. **Then continue the conversation.** Ask the agent to summarize what it already did in that run before you approve the next step.

## Why a duplicate submission cannot create a duplicate hierarchy

`meta-ad-launcher` writes `ad-runs/<run>/ledger.json` with the approved plan and a **run key** before its first mutation on Meta, and it records every returned ID (media, campaign, ad set, creative, ad) with a status and timestamp as it goes. On any retry, including a resubmitted message after a false session-expiry banner, the launcher:

- reads the ledger and the remote state first,
- treats a transport ambiguity ("did that create call land?") as a read-back, never as a re-create,
- reuses the run key to find the objects it already owns and continues from the first missing step,
- and, when a run is retired, cleans up the ads, their creatives, and their uploaded media together, confirming each as `DELETED` on read-back.

So the worst case of a resubmitted launch is a second conversation turn that finds the existing ledger and reports "already created, here is where it stopped". A second campaign, ad set, or ad is not possible while the ledger for that run key exists. The same holds for the ad-copy approval: the approval is bound to a content hash of the exact pool, so a resend cannot approve different text by accident.

What the run key does not protect: a brand-new run started from scratch after deleting or ignoring the ledger. Never delete a ledger for a run that has any live objects; retire the run first.

## Related

- `SETUP.md`, Step 4 (d): the restart boundary that most often triggers this banner.
- `docs/support-matrix.md`: restart and reload rules per kind of change.
