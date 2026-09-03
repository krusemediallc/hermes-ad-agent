# Meta Authentication for the Ads MCP

This is the authoritative reference for authenticating Meta's official Ads MCP server (`https://mcp.facebook.com/ads`) from a Hermes agent, and in particular from a headless install such as a Hostinger Managed App. It replaces every earlier statement in this repo that the Meta MCP "just works" with an OAuth login and needs no app or token. On a real first-user onboarding (3 September 2026, Hostinger managed Hermes v0.20.x) that was not true, and this document records what was.

Read this before SETUP.md Step 4, Route A. The Meta Ads CLI (Route B) has its own token story in [meta-cli.md](meta-cli.md); the token-class table below explains why the two routes need different tokens.

Everything below was observed on one install and one Meta business. Where a detail is not marked as observed, verify it against `hermes mcp --help`, `hermes config --help`, your live tool list, and Meta's get-started page for the Ads MCP server:
https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-mcp-server/ads-mcp-server-get-started

---

## The two official routes

Meta's get-started page documents exactly two ways to authenticate the hosted Ads MCP:

| Route | How it authenticates | What it needs | Works headless |
|---|---|---|---|
| OAuth | Browser sign-in through a Meta app you own | A pre-registered Meta App ID and a redirect (callback) URL the connecting client can actually serve | Only if the Hermes surface you use supports the exact callback Meta expects |
| Programmatic user token | HTTP header `Authorization: Bearer <USER_ACCESS_TOKEN>` on every request | A USER access token carrying all seven scopes below | Yes |

**Generic OAuth with dynamic client registration is not supported by Meta.** Hermes's `auth: oauth` mode tries discovery plus dynamic registration; Meta first answered with an issuer mismatch and then with `invalid_client_metadata: Dynamic registration is not available for this client.` That is Meta's policy, not a Hermes bug and not a credential problem. Do not retry it, do not invent a callback URL, and do not paste a Hermes session URL as a redirect URI. A Hermes chat or dashboard URL is not a callback.

**The recommended route for a managed or headless Hermes is the user token as a bearer header.** It is what worked end to end, it needs no browser round-trip on the server, and every later step in this document assumes it.

---

## Required scopes (all seven)

The hosted MCP rejects tokens that are missing any of these:

```
ads_mcp_management
ads_read
ads_management
catalog_management
business_management
pages_show_list
instagram_basic
```

`ads_mcp_management` is the one that separates "works with the Marketing API" from "works with the Ads MCP". It is only grantable to a USER token through a Meta app that lists it. If your Graph API Explorer permissions picker does not show it, the app is not eligible for the Ads MCP; verify on Meta's get-started page which app types and access levels can request it.

---

## Token classes: what each can and cannot do

| Token class | Direct Marketing API (Graph reads) | Meta Ads CLI (Route B) | Hosted Ads MCP (Route A) | Notes |
|---|---|---|---|---|
| APP token (`app_id|app_secret` form) | Validate and exchange other tokens only | No | No | Used for `debug_token` and the long-lived exchange call. Never put it in the MCP config. |
| SYSTEM_USER token (Business Suite system user) | Yes | Yes | **No (HTTP 401)** | Cannot carry `ads_mcp_management`, so the hosted MCP rejects it even though every other scope is present. This is the token Route B wants and the token Route A cannot use. |
| USER token, all seven scopes | Yes | Yes (works, but Route B documents the system user token) | **Yes** | The only class that authenticated the hosted MCP on the observed install. Short-lived by default; exchange for long-lived immediately. |

If you already have a Route B system user token, do not try to reuse it for the MCP. Generate a user token for Route A and keep the two separate.

---

## Creating the USER token (Route A, headless)

A human does this once in a browser, on their own machine, never inside the Hermes chat.

1. **Have a Meta app.** In Meta for Developers, use an existing app or create one (a few clicks). The app must be able to request `ads_mcp_management`; check Meta's get-started page for the current app requirements.
2. **Open the Graph API Explorer** (Meta for Developers, Tools). Select that app, choose **User Token**, and in the permissions picker add every one of the seven scopes above. Generate the token and complete the Facebook login and consent screens as the Meta Business user who holds admin or advertiser access on the ad accounts the agent should manage.
3. **Do not paste that token anywhere yet.** Graph API Explorer tokens are short-lived (roughly an hour). On the observed onboarding one expired in the middle of setup.
4. **Exchange it immediately for a long-lived token.** Meta documents the exchange as a GET on `oauth/access_token` with `grant_type=fb_exchange_token`, your app ID, your app secret, and the short-lived token. Run it from your own terminal, never in chat, and read the token from the response without echoing it into a log. The long-lived token is valid for about 60 days.
5. **Record the expiry.** Meta returned **no refresh token** on the observed install, so renewal is manual. Call `debug_token` with the app token (or read `expires_in` from the exchange response) and write the expiry date, and only the date, somewhere the operator will see it: a calendar reminder about a week ahead, and the non-secret setup-state file described in SETUP.md. When it expires, repeat steps 2 to 5 and update the stored secret. (The bridge transport plus the weekly maintenance script, described under "Automatic renewal" below, can re-exchange the token without a restart, but whether a re-exchange ever advances the expiry is unverified, so keep treating renewal as manual until the script reports `RENEWED`.)
6. **Check the scopes on the long-lived token** with `debug_token` before storing it. If any of the seven is missing, the MCP will return 401 later and the fix is a new token, not a config change.

Reporting and cron jobs that depend on this token must check the recorded expiry, alert loudly when authentication fails, and pause rather than return an empty report that looks like "no data".

---

## Storing the token

- **Where.** Either the managed app's environment settings (on Hostinger, the environment variables UI for the Hermes managed app) or the file that `hermes config env-path` prints (on the observed install, `/data/.env`; on a self-hosted Hermes typically `~/.hermes/.env`). Never hard-code either path in a skill; discover it with `hermes config env-path`. On the bridge transport (below) the env file is the only home: the bridge reads a file, not the process environment.
- **Name.** This pack uses `META_MCP_TOKEN`, and only that name (see the single-alias rule under "Automatic renewal"). On the direct transport the MCP config references it as `${META_MCP_TOKEN}` and nothing else; on the bridge transport the config carries no header and the bridge reads the variable from the env file itself.
- **File mode.** If the env file route is used, set it to `0600` (`chmod 600 "$(hermes config env-path)"`).
- **Never** in chat, in BRAND.md, in `memory/`, in a cron job prompt, in `ad-runs/`, in any file this repo tracks, or as a literal string in `config.yaml`. After configuring, grep the config for `EAA` and for `Bearer ` followed by anything other than `${` to confirm no literal token landed there.
- **Rotation.** When the token expires or leaks, generate a new one, replace the secret at the same place, restart the managed app (direct transport only; on the bridge transport the next request picks the new value up), and re-run the verification layers below. Do not keep the old value anywhere. On the bridge transport the weekly maintenance script handles the routine re-exchange; a leak or an expiry still means a human generates a new token.

---

## Configuring Hermes

Prefer the Hermes CLI over hand-editing YAML. A malformed edit can disable the gateway, and an edit that races an in-progress `hermes mcp login` can leave the config half-written.

Typical shape (verify flag names with `hermes mcp add --help` and `hermes mcp configure --help` on your version):

```bash
hermes config check                     # before: confirm the config parses today
hermes mcp add meta_ads --url https://mcp.facebook.com/ads \
  --header 'Authorization: Bearer ${META_MCP_TOKEN}' \
  --trust untrusted
hermes config check                     # after: confirm it still parses
```

If `hermes mcp add` does not accept a header or trust flag on your version, `hermes config set` on the `mcp_servers.meta_ads.*` keys is the next choice; hand-editing `config.yaml` is the last. The resulting entry should look like this:

```yaml
mcp_servers:
  meta_ads:
    url: "https://mcp.facebook.com/ads"
    headers:
      Authorization: "Bearer ${META_MCP_TOKEN}"
    trust: untrusted
    enabled: true
```

- The config file lives where `hermes config path` says (on the observed install `/data/config.yaml`, with `HERMES_HOME=/data`).
- `trust: untrusted` is deliberate. Meta's tool descriptions and results are remote content; untrusted keeps Hermes from treating them as instructions.
- `hermes` may not be on `PATH` in agent shells. Discover it with `command -v hermes`, then try `/opt/venv/bin/hermes` on a Hostinger container, then `$HERMES_HOME`. Never assume `~/.hermes`.
- Never patch `/opt/hermes-agent` or site-packages from this repo, whatever error you are chasing.

### The bridge transport (recommended on Hostinger)

The entry above is the **direct transport**: Hermes connects to the URL itself. The alternative, and the recommended one on Hostinger, is to run the pack's local bridge as a **command-type MCP server** and let it talk to Meta. Same server name, same token, no header in the config:

```yaml
mcp_servers:
  meta_ads:
    command: python3
    args: ["/absolute/path/to/hermes-ad-agent/scripts/meta_mcp_bridge.py", "--env-file", "/data/.env"]
    trust: untrusted
    enabled: true
```

Typical Hostinger values are a workspace at `/data/workspace/hermes-ad-agent` and an env file at `/data/.env`; `python3` is enough (the bridge is standard library only) and `/opt/venv/bin/python3` also works. Verify the flags for adding a command-type server with `hermes mcp add --help`. Why and how it changes the operating rules is in "Automatic renewal" below; the step-by-step install, including the `META_MCP_LONG_TOKEN` migration note, is SETUP.md Step 4, Route A2.

### Restart boundaries

| What changed | What it takes to apply |
|---|---|
| A process environment variable (the token, on the managed env UI; direct transport) | Restart or redeploy the managed app. A running process does not see the new value. |
| The token line in the env file (bridge transport; a manual replacement or the maintenance script) | Nothing. The bridge reads the file on the next request. |
| `config.yaml` (including adding or changing the bridge entry) | May hot-reload (`/reload-mcp` in chat or the dashboard's MCP page). Confirm rather than assume. |
| The set of tools a server advertises (tool schema) | A fresh agent session. An existing session keeps its old tool list. |

---

## Automatic renewal with the bridge and the maintenance script

Two scripts in `scripts/` turn the "replace the secret and restart" cycle into something a weekly job can do safely. Both are standard-library Python; both are documented flag by flag in `scripts/README.md`. This section is about what they do to the operating rules.

### The mechanism

- **`scripts/meta_mcp_bridge.py`** is a local stdio MCP server that Hermes runs as a command-type entry (the YAML above) in place of connecting to the URL. It proxies every request to Meta's hosted Ads MCP over Streamable HTTP and reads `META_MCP_TOKEN` from the env file **on every request**. A token that changes on disk is used on the next call, with no gateway restart and no managed-app redeploy. On the way it also strips the empty `params._meta` object that MCP SDK 2.0 clients add and Meta rejects (the blocker below), preserves a non-empty `_meta`, and forwards Meta's real JSON-RPC error code and message instead of a generic error. It never writes the token anywhere, redacts error text, and refuses any upstream that is not `https` on `facebook.com` unless started with `--allow-any-upstream` (local tests only).
- **`scripts/meta_token_maintenance.py`** is deterministic, with no LLM anywhere in it. It reads the current token, inspects it with `debug_token` (type, scopes, expiry, data-access expiry), exchanges it with `grant_type=fb_exchange_token` using `META_APP_ID` and `META_APP_SECRET` from the same env file, inspects the candidate (it must be a USER token carrying all seven scopes), and classifies the result with the vocabulary below. A write is atomic (temp file, fsync, rename, mode `0600`), guarded by a lock file and a compare-and-swap on the token line, and followed by a direct MCP `initialize` plus `tools/list` smoke test with the new token; on any failure it rolls back. Because the bridge re-reads the file per request, a passing smoke test means the live gateway uses the new token on its next call. `--dry-run` writes nothing.
- The job runs weekly as a **script job** (no agent, no prompt) with a delivery target, so the outcome line reaches the person who has to act on it. Typical shape, verify with `hermes cron --help`:

  ```bash
  hermes cron add --name meta-token-maintenance --schedule "0 9 * * 1" \
    --script "cd /absolute/path/to/hermes-ad-agent && python3 scripts/meta_token_maintenance.py --json" \
    --no-agent --deliver <the channel the user chats on>
  ```

  Run it once with `--dry-run` first, then once live, then once through the scheduler, and confirm the user received the message. Delivery is part of success.

### The outcome vocabulary

| Outcome | What happened | What the operator does | Exit code |
|---|---|---|---|
| `RENEWED` | Meta returned a different token **and** the expiry advanced by more than a day; the new token was written and smoke-tested | Nothing. Read the new expiry from the outcome line or the state file and update the date in BRAND.md at the next brand-setup update | `0` |
| `REPLACED_SAME_EXPIRY` | Meta returned a different token string but the expiry did not advance; **not written** unless `--replace-same-expiry`; the old token stays valid | Nothing now. This is not a renewal and buys no time. Watch days remaining and plan the manual renewal before the date | `1` |
| `NO_CHANGE` | The same token came back, or the exchange was skipped because `META_APP_ID` / `META_APP_SECRET` are absent | Nothing while days remaining is at or above `--min-days` (default 21) | `0` (`1` under `--min-days`) |
| `REAUTH_REQUIRED` | The token is invalid or expired, or Meta refused the exchange | Generate a new USER token with the seven scopes, exchange it for a long-lived one, and replace the env-file line in the terminal. No restart on the bridge transport | `2` |
| `FAILED` | The lock was held, the candidate was missing a scope, the compare-and-swap found the token line changed underneath, or the write or smoke test failed (rolled back) | Read the redacted reason, re-run once; if it persists, check the env file by hand: presence, mode `0600`, single alias | `2` |

Exit code `1` also covers any otherwise healthy outcome with fewer than `--min-days` remaining, so a monitoring channel can treat non-zero as "look at this".

### The honesty note

Meta returned an equal-expiry token on the one observed re-exchange. Whether re-exchanging a long-lived user token ever advances its expiry is therefore **unverified**, and this pack does not claim it does. The script reports what actually happened: `REPLACED_SAME_EXPIRY` is deliberately not called a renewal, and a run of them is expected rather than alarming. The credential-expiry reminder and the auth-failure alert path in the reporting suite still cover manual reauthorization and stay in place alongside the maintenance job.

### What the maintenance script never does

- Never calls an LLM or reads a prompt. It is plain Python on the standard library and is scheduled as a script job, not an agent job.
- Never prints, logs, or delivers the token or the app secret, in any form, including in `--json` output and in error text.
- Never writes the env file without the lock, the compare-and-swap on the token line, and the smoke test; never leaves a partial file (atomic rename) and never keeps a token the smoke test rejected (rollback).
- Never writes anything under `--dry-run`.
- Never generates a token from nothing. `REAUTH_REQUIRED` is a human's job, done in the browser and the terminal, never in chat.

### The single-alias rule

The env file holds the token under one name, `META_MCP_TOKEN`, and the bridge, the maintenance script, the doctor, and the direct-transport config all read that one name. If a prototype stored it as `META_MCP_LONG_TOKEN`, rename that line and delete the old one. Two aliases are how a rotation updates one line while the bridge keeps reading the other, stale one. `--token-var` on both scripts exists for tests, not for a second production name.

### The state file

`$HERMES_HOME/hermes-ad-agent/token-maintenance-state.json` records the last outcome, `expires_at`, `data_access_expires_at`, the last advancing expiry, the count of consecutive non-advancing runs, and days remaining. It is non-secret (dates and counters only), and reporting jobs may read it as a second source for days remaining beside the date in BRAND.md.

---

## Verification layers

"It connected once" is not a state. Verify each layer separately, in this order, and report each one.

1. **Token doctor.** `python3 scripts/onboarding_doctor.py --meta-token-check` (read-only, redacted; it never prints the token). It confirms the secret is present, that the config references `${META_MCP_TOKEN}` and holds no literal bearer, and, when it can reach Meta, the token's scopes and expiry.
2. **Provider `tools/list`.** A direct MCP `tools/list` against `https://mcp.facebook.com/ads` with the bearer header returns a tool roster. A 401 here means the token class or scopes are wrong (see the table above); nothing in Hermes will fix it.
3. **`hermes mcp test meta_ads`.** Read the printed text. On the observed install it printed `Connection failed` and still exited 0, so the exit code is not a signal. `hermes mcp list` showing `enabled` is config state, not health.
4. **Agent-usable.** Start a **fresh, normal** agent session (not the one that edited the config). Ask it to discover the registered Meta tool with its tool search and to call it read-only. The provider advertises `ads_get_ad_accounts`; the Hermes runtime registers it under a name like `mcp__meta_ads__ads_get_ad_accounts`. The agent must find and call the live registered name, not the bare one.
5. **Verified.** That read-only call returned real data: a list of ad accounts with names and IDs. Show it to the user and have them confirm by **name and ID** which account the agent will work in. Two accounts can share a display name; a selection by name alone is not a selection.
6. **Durable.** The token expiry is recorded and not within a week; no literal secret exists in config, chat, or any tracked file; the env file (if used) is mode 0600.

### Completion vocabulary

Use these words exactly when reporting status; they are not interchangeable.

| State | Meaning |
|---|---|
| configured | The `meta_ads` entry exists in the config and parses |
| enabled | `enabled: true` (what `hermes mcp list` shows; says nothing about health) |
| connected | Provider `tools/list` succeeded with the configured header |
| agent-usable | A fresh normal session can discover and call the registered tool |
| verified | The read-only call returned account data the user confirmed |
| durable | Expiry recorded and not imminent; no literal secrets; correct file modes |

- **COMPLETE** means all six pass at the same time.
- **PARTIAL** means at least one of configured, enabled, connected, agent-usable, or verified is not yet true. Say which.
- **FRAGILE** means everything works today but durable fails (token expiring soon, a literal secret somewhere, a config edited by hand and not checked).

Never report Meta as "connected" when the true state is PARTIAL or FRAGILE.

---

## Known blockers and their exact signatures

### Issuer mismatch, then dynamic registration refused

Seen when Hermes was configured with `auth: oauth` and asked to log in:

```
issuer mismatch
invalid_client_metadata: Dynamic registration is not available for this client.
```

Meaning: Meta does not allow generic OAuth clients to self-register. Switch to the user-token route above. The only OAuth that can work is one with your own pre-registered App ID and a callback the Hermes surface actually serves; if you do not have both, do not attempt it.

### Empty `_meta` rejected (Hermes / MCP SDK interop defect)

Hermes on MCP Python SDK 2.0.0 sends `params._meta: {}` on tool calls. Meta answers:

```
HTTP 400
JSON-RPC -32602: "meta" for Request must be an dict or null
```

Hermes surfaces it only as `Server returned an error response`. If you see that message, check the raw response for the `-32602` / `"meta" for Request` text before doing anything else.

Meaning: the token and config are fine; this is an interop defect between the Hermes runtime's SDK version and Meta's server. What to do:

- Stop. Do not regenerate tokens, do not re-run login, do not re-add the server as a URL.
- Do not patch Hermes source, `/opt/hermes-agent`, or site-packages.
- Switch the transport to the bridge (SETUP.md Step 4, Route A2): `scripts/meta_mcp_bridge.py` strips the empty `_meta` before the request reaches Meta, which is a configuration change, not a patch.
- Only if the bridge cannot run, use the Meta Ads CLI route for the operations you need (SETUP.md Step 4, Route B), and re-verify the direct transport after the next Hermes update.

### 401 from the provider with a token that works elsewhere

The token is a SYSTEM_USER or APP token, or a user token missing `ads_mcp_management`. See the token-class table. Generate a fully scoped USER token.

### Expired token

Reads that worked start failing with an auth error. Check the recorded expiry. Graph API Explorer tokens expire in about an hour; long-lived tokens in about 60 days. Repeat the creation steps, replace the secret, restart the managed app (direct transport; on the bridge transport nothing restarts), re-run the verification layers. On the bridge transport the maintenance script will have reported `REAUTH_REQUIRED` for this state; that outcome is the signal, not a fix.

### `hermes mcp login` self-collides on a headless gateway

Relevant to any OAuth-based MCP (observed with Arcads, and it would apply to a Meta OAuth attempt too). The CLI can emit two authorization flows at once and fail with `OAuth callback port <port> is already in use ([Errno 98] Address already in use)`. If two authorization URLs or a busy callback port appear: stop, do not retry the old URLs, and follow the Hermes remote OAuth guide instead:
https://hermes-agent.nousresearch.com/docs/guides/oauth-over-ssh

---

## Account selection

After verification, the agent shows every account the token can see and the user picks one by **name and ID**. Record the chosen ID only in run-scoped files this repo ignores (`ad-runs/`, `memory/`), never in the setup-state file, chat transcripts that get pasted elsewhere, or anything tracked in git. If two accounts share a display name, the agent must ask which ID, and must not proceed on a name alone.

---

## Quick checklist

- [ ] Meta app exists and can request `ads_mcp_management`
- [ ] USER token generated with all seven scopes
- [ ] Exchanged for a long-lived token immediately; expiry recorded; renewal reminder set
- [ ] Stored as `META_MCP_TOKEN` in the managed env UI or the `hermes config env-path` file (mode 0600)
- [ ] `hermes config check` passed before and after the `meta_ads` entry was added
- [ ] Config references `${META_MCP_TOKEN}` only (direct transport) or names the bridge script by absolute path with `--env-file` and carries no header (bridge transport); `trust: untrusted` either way
- [ ] Managed app restarted after the env change (direct transport only; the bridge needs no restart for a token change)
- [ ] On the bridge transport: one token alias in the env file (`META_MCP_TOKEN`, no leftover `META_MCP_LONG_TOKEN`), and if the maintenance job is wanted, `META_APP_ID` and `META_APP_SECRET` in the same file
- [ ] Doctor, `tools/list`, `hermes mcp test` text, fresh-session tool call, account list by name and ID
- [ ] Maintenance job (bridge transport, optional): `--dry-run` once, live once, scheduled as a script job, and the user received the delivered outcome line
- [ ] Status reported as COMPLETE, PARTIAL, or FRAGILE, with the failing layer named
