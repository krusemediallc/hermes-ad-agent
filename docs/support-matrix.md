# Support Matrix

What this pack has been tested on, where the paths live, which OAuth surface works where, and the capability each integration must provide before a skill treats it as ready. Read this when an install does not match `SETUP.md`, or when a tool count changes and you want to know whether that matters (it does not; capability does).

Facts here come from real installs. Where a version, flag, or path is not listed, verify it in your environment with `--help` and your live tool list rather than assuming.

---

## Tested Hermes versions

| Item | Tested | Notes |
|---|---|---|
| Hermes Agent | v0.20.4 and v0.20.6 | Hostinger managed image, September 2026 |
| Python (Hermes runtime) | 3.13 | packaged in the managed image |
| MCP Python SDK | 2.0.0 | carries the Meta interop blocker below |
| Hermes source layout | `/opt/hermes-agent` (packaged, not a git checkout) | never patched by this pack |
| Meta Ads CLI (`meta-ads`) | 1.1.0 | requires Python 3.12 or later |

Other Hermes versions and self-hosted installs are expected to work but have not been exercised end to end. The pack never depends on Hermes internals, only on the `hermes` CLI, the skills directory, the MCP config, and the memory files.

---

## Deployment: Hostinger is recommended, not required

The recommended deployment is a Hostinger managed Hermes app: it comes with the dashboard, the in-browser terminal, an environment-variables UI, and a stable home directory, and it is the environment this pack was onboarded on. It is not a prerequisite. Any Hermes install with a terminal, a skills directory, and MCP support can run the pack. The only Hostinger-specific facts are the paths and the restart rule below.

### Paths: Hostinger managed image versus a default install

| What | Default install | Hostinger managed image | How to discover |
|---|---|---|---|
| `hermes` executable | on PATH | `/opt/venv/bin/hermes` (often not on PATH for agent shells) | `command -v hermes \|\| ls -l /opt/venv/bin/hermes` |
| Hermes home | `~/.hermes` | `/data` | `echo "${HERMES_HOME:-$HOME/.hermes}"` |
| Config file | `~/.hermes/config.yaml` | `/data/config.yaml` | `hermes config path` |
| Env file | `~/.hermes/.env` | `/data/.env` | `hermes config env-path` |
| Skills | `~/.hermes/skills` | `/data/skills` | `$HERMES_HOME/skills` |
| MCP tokens | `~/.hermes/mcp-tokens` | `/data/mcp-tokens` | `$HERMES_HOME/mcp-tokens` |
| Memories | `~/.hermes/memories` | `/data/memories` | `$HERMES_HOME/memories` |
| Cron jobs | `~/.hermes/cron` | `/data/cron` | `$HERMES_HOME/cron` |
| Pack setup state | `~/.hermes/hermes-ad-agent/setup-state.json` | `/data/hermes-ad-agent/setup-state.json` | `$HERMES_HOME/hermes-ad-agent/setup-state.json` |

Rule: never hard-code `~/.hermes`. Discover the home once (SETUP.md Step 0) and derive everything from it.

### Restart and reload rules

| Change | Takes effect |
|---|---|
| Config file edit (`hermes config set`, `hermes mcp add`, including the bridge entry) | may hot-reload; verify with `hermes mcp list` and `hermes mcp test` |
| Process environment variable (Hostinger env UI, shell profile) | only after the managed app restarts or redeploys |
| The `META_MCP_LONG_TOKEN` line in the env file, Meta MCP bridge transport (a maintenance-script write, on its weekly run or from the `META_MCP_TOKEN` handoff line) | the next request; the bridge re-reads the file per call, so nothing restarts |
| MCP server added or its tool list changed | a fresh agent session (tool schemas load at session start) |
| Memory file entries | next session (frozen snapshot at session start) |

---

## Surfaces and what works for OAuth on each

| Surface | Terminal | Arcads OAuth | Meta MCP auth | Notes |
|---|---|---|---|---|
| Hermes dashboard (web) | via hPanel terminal on Hostinger | works: the dashboard MCP page runs the OAuth relay | user-token header only | preferred surface for Arcads login on a managed gateway |
| Hermes Desktop | local | works: same relay | user-token header only | good alternative when the user runs Desktop against the gateway |
| Local CLI / TUI (`hermes` on a machine with a browser) | yes | works as ONE fresh `hermes mcp login arcads` | user-token header only | working directory is the launch directory, not `terminal.cwd` |
| Managed gateway, headless (Hostinger, SSH only) | yes | fragile: a terminal login on a headless box can emit two flows and collide on the callback port; stop and use the dashboard relay or the Hermes remote OAuth guide (https://hermes-agent.nousresearch.com/docs/guides/oauth-over-ssh) | user-token header only | most cron and messaging sessions run here |

Meta's hosted MCP does not support Hermes's generic OAuth (issuer mismatch, then `invalid_client_metadata: Dynamic registration is not available for this client`). Meta's own documentation offers OAuth only against a pre-registered Meta app with an exact callback the client supports, and a programmatic bearer route with a user access token. The bearer route is the documented Route A in this pack, carried either as a header in the config (direct transport) or by the local bridge (below), which reads the same user token from the env file. Users who own a Meta app and a supported callback may try OAuth; it is untested here.

---

## Meta MCP transports (Route A)

Both transports use the same fully scoped USER token and the same server name (`meta_ads`), so registered tool names and every skill's backend detection are identical. Pick one; never keep both entries.

| Transport | Config entry type | Token lives in | Token change applies | Handles the empty `_meta` blocker | Requirements |
|---|---|---|---|---|---|
| Direct URL | `url: "https://mcp.facebook.com/ads"` with `headers: Authorization: "Bearer ${META_MCP_LONG_TOKEN}"` | managed env UI or the env file | after a managed-app restart or redeploy | no (blocked on MCP SDK 2.0) | a Hermes build that connects to remote MCP servers |
| Bridge (`scripts/meta_mcp_bridge.py`), recommended on Hostinger | `command: /opt/venv/bin/python` (or `python3`) with `args: ["/absolute/path/to/scripts/meta_mcp_bridge.py"]`, `connect_timeout: 120`, no `url`, no `headers`; written with `hermes config set` / `unset` (SETUP.md Step 4, Route A2) | the env file only (the bridge reads a file, not the process environment) | on the next request, no restart | yes (strips an empty `params._meta`, preserves a non-empty one) | any Python 3 (standard library only); a Hermes build that runs command-type MCP servers; the env file holding the long-lived token as `META_MCP_LONG_TOKEN`, once, mode `0600`; absolute paths in `args`; `trust: untrusted`; upstream `https` on `facebook.com` (anything else is refused unless `--allow-any-upstream`, which is for local tests only) |

Bridge flags, all optional: `--env-file` (default `$META_MCP_ENV_FILE` or `$META_MCP_DOTENV_PATH`, else `$HERMES_HOME/.env`, else `/data/.env`, else `~/.hermes/.env`, so on a standard install it is not needed in `args`), `--token-var META_MCP_LONG_TOKEN`, `--upstream https://mcp.facebook.com/ads` (env `META_MCP_UPSTREAM` or `META_MCP_UPSTREAM_URL`), `--timeout 120`, `--log-level info`, `--allow-any-upstream`. It never writes the token anywhere, redacts error text, and forwards Meta's real JSON-RPC error code and message instead of a generic error. Variable names: `META_MCP_LONG_TOKEN` is the long-lived token the bridge reads; `META_MCP_TOKEN` is the short-lived handoff line a person fills for reauthorization and the maintenance script clears. Existing installs that already used `META_MCP_LONG_TOKEN` need no rename; an install that stored the long-lived token as `META_MCP_TOKEN` renames that line to `META_MCP_LONG_TOKEN` once. Install steps: SETUP.md Step 4, Route A2; operator runbook: `docs/meta-ads-mcp-renewal.md`.

---

## Meta MCP: MCP SDK 2.0 interop blocker (known)

| Field | Value |
|---|---|
| Surfaces as | `Server returned an error response` from Hermes; `Connection failed` from `hermes mcp test` (which still exits 0) |
| Underlying | HTTP `400`, JSON-RPC `-32602`, message `"meta" for Request must be an dict or null` |
| Cause | MCP Python SDK 2.0 sends `params._meta: {}`; Meta's server rejects an empty object where it expects a dict or null |
| Is it credentials? | No. A raw read-only `tools/list` with the same bearer and no `_meta` succeeds |
| What to do | Detect the signature, stop, record it. Switch Route A to the bridge transport above, which strips the empty object before it reaches Meta. If the bridge cannot run, use the Meta Ads CLI (Route B) for Meta until the upstream fix lands, and retest the direct transport after the next Hermes update |
| What not to do | Regenerate tokens, re-add the server as a URL, patch `/opt/hermes-agent`, site-packages, or the SDK from this repo |

Status semantics that matter when diagnosing: `hermes mcp list` reports `enabled` for a failing server (config state, not health); `hermes mcp test` must be read as text; and a tool visible to `hermes mcp test` is not usable by an agent session that started before the registration.

---

## Scheduled jobs: agent jobs and one script job

| Job | Kind | Schedule (typical) | Touches the token? | Delivery |
|---|---|---|---|---|
| Daily digest, hourly check, threshold alerts, monthly memory refresh, credential-expiry reminder (`ad-reporting-automations`) | agent jobs with read-only prompts | per the skill | never; they read the expiry date from BRAND.md and check the connection | the user's channel |
| `meta-token-maintenance` (`scripts/meta_token_maintenance.py --markdown --hermes-test`) | **script job, no agent, no LLM** (`--no-agent`; verify the flag with `hermes cron --help`) | weekly, `0 9 * * 1` | yes: re-exchanges it and rewrites the `META_MCP_LONG_TOKEN` line only when the expiry advanced (`RENEWED`) or `--replace-same-expiry` is set, under a lock, a compare-and-swap, and a smoke test; the previous token is restored only when Meta rejected the new one (`401`/`403`) | the user's channel; delivery of the Markdown report is part of success |

The maintenance job requires the bridge transport (so the new token is used without a restart) and `META_APP_ID` plus `META_APP_SECRET` in the same env file. Its report opens with a headline (`SUCCESS` when the token was renewed or a same-expiry candidate was deliberately written; otherwise the outcome name) and a detail (`RENEWED`, `REPLACED_SAME_EXPIRY`, `NO_CHANGE`, `REAUTH_REQUIRED`, `FAILED`); exit `0` healthy, `1` warning, `2` action needed. The same script is the reauthorization path: a person puts a fresh short-lived user token on the `META_MCP_TOKEN` handoff line and runs it. It does not replace the expiry reminder: `REAUTH_REQUIRED` still needs a human, and whether re-exchange ever advances expiry is unverified (the one observed re-exchange returned an equal-expiry token). Details: `docs/meta-ads-mcp-renewal.md` and `docs/meta-authentication.md`, "Automatic renewal".

---

## Readiness is capability-based, never count-based

Tool rosters drift daily (Meta went from 106 to 97 tools between two days; Arcads from 80 to 82). Server-native names (`ads_get_ad_accounts`, `arcads_list_products`) are what the providers advertise; the Hermes runtime registers them under a longer callable name, typically `mcp__meta_ads__ads_get_ad_accounts` and `mcp__arcads__arcads_list_products`. A skill therefore:

1. discovers the live registered name with `tool_search` (substring match on the native name),
2. checks that every capability in the manifest below has at least one matching registered tool,
3. reports readiness per capability, and never says "N tools present, so ready".

### Required capability manifest

**Meta (via MCP, or via the Meta Ads CLI where marked):**

| Capability | MCP native tool (typical) | Meta Ads CLI | Required for |
|---|---|---|---|
| List ad accounts with names and IDs | `ads_get_ad_accounts` | `meta ads adaccount list --output json` | Checkpoint 4, every skill's backend detection |
| Read entities with targeting, placements, bidding | `ads_get_ad_entities` | `meta ads <campaign\|adset\|ad> list\|get --fields ...` | account-audit, launcher mirror mode |
| Read creatives and copy (paginated, coverage-counted) | `ads_get_creatives` (live key observed: `ad_creatives`) | `meta ads creative list\|get` | account-audit copy analysis |
| Insights | `ads_insights_*` | `meta ads insights get` | reporting, performance loop |
| Create campaign, ad set, creative, ad, all PAUSED | `ads_create_campaign`, `ads_create_ad_set`, `ads_create_creative`, `ads_create_ad` | `meta ads <resource> create --status PAUSED` | meta-ad-launcher |
| Upload a local image or video file | not available on the MCP (upload tools take public URLs only and were still rolling out) | `meta ads creative create --image ./file` / `--video ./file` | launcher, any run with local media |
| One flexible creative carrying multiple primary texts, headlines, descriptions | not available on the MCP (`ads_create_creative` is scalar, no `asset_feed_spec`) | `--bodies` / `--titles` / `--descriptions` repeated per value, or `--asset-feed-spec @feed.json` | launcher, the 5/5/3 pool |
| Activate (only on explicit user confirmation) | `ads_activate_entity` / `ads_update_entity` | `meta ads <resource> update --status ACTIVE` | meta-ad-launcher after review |
| Ad preview (for thumbnail and copy verification) | `ads_get_ad_preview` | not available | launcher video-cover check |
| Retire (ads, creatives, media) and read back DELETED | `ads_update_entity`, `ads_creative_delete` | `meta ads <resource> update\|delete` | launcher cleanup |

Write policy: writes go only through the Meta MCP or the Meta Ads CLI. When the MCP lacks a capability, use the CLI for that operation if installed; otherwise stop and explain the gap and let the user choose. The Graph API is read-only in this pack (the audit's exact-settings capture and diagnostics), never an improvised write path.

**Arcads (MCP only):**

| Capability | Native tool (typical) | Cost | Required for |
|---|---|---|---|
| List products | `arcads_list_products` | none | Checkpoint 3, every generator's readiness check |
| Generate image | `arcads_generate_image` | credits, reported as `creditsCharged` | image ad skills |
| Generate video | `arcads_generate_video` (and actor/UGC variants) | credits, reported as `creditsCharged` | video ad skills |
| Watch an asset to completion | `arcads_watch_asset` | none, but see below | every generator |

Cost rules that follow from the first real run: only `creditsCharged` in the response is cost (`mp` is usage metadata, not credits, and treating it as credits was wrong by roughly 480x); Arcads has no quote endpoint, so a first paid generation is an explicit unknown-cost calibration under a user-defined maximum exposure; transcription, analysis, subtitling, and editing operations are credit-accounted even when a daily allowance returns 0 charged, so they are never run automatically. No fixed credit figures appear in this pack as estimates; any number that does is labelled an account-specific historical observation.

---

## Token classes for Meta

| Token | Direct Marketing API | Meta Ads CLI | Hosted Meta MCP |
|---|---|---|---|
| App token | validate and exchange other tokens only | no | no |
| System user token | yes | yes | rejected (`401`; cannot carry `ads_mcp_management`) |
| User token with all seven scopes | yes | yes (but the CLI route documents a system user token) | yes |

Seven scopes for the MCP: `ads_mcp_management`, `ads_read`, `ads_management`, `catalog_management`, `business_management`, `pages_show_list`, `instagram_basic`. Long-lived user tokens last about 60 days; Meta returns no refresh token, so renewal is manual and the expiry date is recorded in `BRAND.md` (Meta Assets) and checked by every reporting job. On the bridge transport the weekly maintenance script re-exchanges the token and reports honestly whether the expiry advanced (`RENEWED`) or not (`REPLACED_SAME_EXPIRY`); the manual path stays in place because the advancing case is unverified, and it runs through the same script via the `META_MCP_TOKEN` handoff line (`docs/meta-ads-mcp-renewal.md`).

---

## Completion vocabulary (shared with SETUP.md Step 8)

configured, enabled, connected, agent-usable, verified, durable. Setup is COMPLETE only when all six hold for every integration at the same time; otherwise it is PARTIAL (something missing) or FRAGILE (working today, known to break soon). A report always says which.
