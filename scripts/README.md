# scripts/

Two read-only helper scripts. Both use only the Python standard library (3.9+),
never write files, never call `hermes` with anything but `--version` and
`config path` / `config env-path`, and never print secret values. Run them from
the workspace root (the repo clone directory); quote the path if it has spaces.

## onboarding_doctor.py

Verifies the state of a Hermes install against what the pack expects. It is the
same check SETUP.md Step 8 asks the agent to run, and it is safe to run at any
time, including from a cron job.

```
python3 scripts/onboarding_doctor.py
python3 scripts/onboarding_doctor.py --json
python3 scripts/onboarding_doctor.py --workspace /absolute/path/to/hermes-ad-agent
python3 scripts/onboarding_doctor.py --meta-token-check            # checks META_MCP_TOKEN, falls back to ACCESS_TOKEN
python3 scripts/onboarding_doctor.py --meta-token-check ACCESS_TOKEN
```

What it checks, in order:

1. `hermes` executable (PATH, then `/opt/venv/bin/hermes`, then `$HERMES_HOME/bin`) and `hermes --version`.
2. `HERMES_HOME` (`$HERMES_HOME`, else `hermes config path`, else `~/.hermes`, else `/data`) plus the config, env, skills, and mcp-tokens paths under it.
3. The non-secret setup-state file (`$HERMES_HOME/hermes-ad-agent/setup-state.json`, fallback `~/.hermes/hermes-ad-agent/setup-state.json`): present, `schema_version` 1, absolute `workspace_root` that exists, valid `meta_backend`.
4. `skills-manifest.txt`: every listed skill exists in `<workspace>/skills/<name>/SKILL.md` (BLOCK if not) and in the Hermes skills directory (WARN if not).
5. `config.yaml` literal-secret scan: an `Authorization:` value that is not a `${VAR}` reference, a literal `Bearer EAA...` token, or any long token-like literal. Only line numbers are reported.
6. Env file (from `hermes config env-path`, else `$HERMES_HOME/.env`, plus `<workspace>/.env`): which of `META_MCP_TOKEN`, `ACCESS_TOKEN`, `AD_ACCOUNT_ID` are set (names only) and whether the file mode is 600.
7. Workspace hygiene: `BRAND.md` present, `memory/accounts` present, `.gitignore` covers `memory/`, `ad-runs/`, `research/`, `outputs/`, `.env`.
8. With `--meta-token-check`: calls the Graph API `debug_token` and `/me/permissions` endpoints and reports token type, granted vs missing scopes (all seven the hosted Meta MCP requires), `expires_at` and `data_access_expires_at` as ISO timestamps, and days remaining. WARN under 21 days; BLOCK if expired, if a required scope is missing, or if the token checked as `META_MCP_TOKEN` is not a USER token. A SYSTEM_USER token is fine for the Meta Ads CLI route, so check it under `ACCESS_TOKEN` instead. The token itself is never printed, in any form.
9. `--arcads` is out of scope for this doctor: verify Arcads with `hermes mcp test arcads` and a native read-only call as described in SETUP.md Step 3.

The workspace defaults to the setup-state file's `workspace_root`, then the
current directory. Every non-OK line ends with a pointer to the SETUP.md step
that fixes it.

Exit codes: `0` every check OK (setup COMPLETE), `1` at least one WARN
(PARTIAL), `2` at least one BLOCK. `--json` prints `{exit_code, workspace,
hermes_home, checks[]}` with the same statuses.

Notes: `hermes` is not always on PATH for agent shells (managed containers
put it at `/opt/venv/bin/hermes`), which is why the discovery order above
exists. Where a Hermes subcommand's output shape is not what the script
expects, verify with `hermes config --help` and your live tool list.

## check_docs_consistency.py

Lints the pack's Markdown so retired guidance does not creep back in. It is the
first step of the GitHub Actions workflow (`.github/workflows/verify.yml`) and
runs the same way locally:

```
python3 scripts/check_docs_consistency.py
```

It scans every `*.md` git would publish (skipping `.git/`, `memory/`, `outputs/`,
`ad-runs/`, `research/`, and anything gitignored such as the maintainer's local
notes) and reports `file:line` for:

- an em-dash character (U+2014) anywhere except the two allowed
  `skills/human-ad-copy` lines that document the no-em-dash rule;
- each phrase in the `OBSOLETE` list at the top of the script (retired
  onboarding claims, the old multi-ad default when it is not preceded by
  "never", and the retired improvised write path);
- wording that says a local file is passed to an `ads_creative_upload` tool on
  the same line (the hosted MCP upload tools take public URLs only);
- `--bodies`, `--titles`, or `--descriptions` followed by two quoted values on
  one flag (the CLI wants the flag repeated per value);
- an Arcads credit figure written as an estimate (the retired tilde 0.9 ballpark);
- `skills-manifest.txt` missing, duplicated, or not matching `skills/*/`
  exactly;
- a `SKILL.md` whose frontmatter `name` differs from its folder.

Exit codes: `0` clean, `1` one or more hits (all printed).

## CI

`.github/workflows/verify.yml` runs on every push and pull request: the docs
check, the doctor in `--json` mode (exit 0 or 1 passes because CI has no
Hermes install; exit 2 fails), `py_compile` on every `.py`, a grep for
token-shaped literals (excluding the two scripts that define the patterns),
and `validate_copy.py --help`.
