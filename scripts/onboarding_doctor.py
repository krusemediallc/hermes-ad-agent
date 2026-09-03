#!/usr/bin/env python3
"""Read-only onboarding doctor for the hermes-ad-agent pack.

Checks the Hermes runtime, the setup-state file, the skills manifest, config
and env hygiene, and (optionally) the Meta token. It never writes anything and
never prints secret values. Python 3.9+, standard library only.

Exit codes: 0 all OK, 1 at least one WARN, 2 at least one BLOCK.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REQUIRED_SCOPES = [
    "ads_mcp_management", "ads_read", "ads_management", "catalog_management",
    "business_management", "pages_show_list", "instagram_basic",
]
GRAPH = "https://graph.facebook.com/v25.0"
TOKEN_NAMES = ("META_MCP_TOKEN", "ACCESS_TOKEN", "AD_ACCOUNT_ID")
GITIGNORE_REQUIRED = ("memory/", "ad-runs/", "research/", "outputs/", ".env")
SKIP_SKILL_DIRS = {"__pycache__"}
SECRET_RE = re.compile(r"(EAA[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9_\-]{30,}|sk-[A-Za-z0-9]{20,})")
_SECRETS = set()  # values that must never appear in output


def scrub(text):
    text = str(text)
    for s in _SECRETS:
        if s and s in text:
            text = text.replace(s, "[redacted]")
    return SECRET_RE.sub("[redacted]", text)


class Doctor:
    def __init__(self):
        self.checks = []

    def add(self, status, name, detail, fix=None):
        self.checks.append({"check": name, "status": status,
                            "detail": scrub(detail), "fix": fix})

    def ok(self, name, detail):
        self.add("OK", name, detail)

    def warn(self, name, detail, fix):
        self.add("WARN", name, detail, fix)

    def block(self, name, detail, fix):
        self.add("BLOCK", name, detail, fix)

    def exit_code(self):
        statuses = {c["status"] for c in self.checks}
        return 2 if "BLOCK" in statuses else (1 if "WARN" in statuses else 0)


def run(cmd, timeout=10):
    """Run a command; return (rc, stdout) or (None, '') when it cannot run."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None, ""


def parse_env_file(path):
    """Return {NAME: value} from a KEY=VALUE file. Values stay in memory only."""
    out = {}
    try:
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:]
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip("'\"")
    except OSError:
        pass
    return out


# ---------------------------------------------------------------- checks

def check_hermes(d):
    home = os.environ.get("HERMES_HOME")
    candidates = [shutil.which("hermes"), "/opt/venv/bin/hermes",
                  str(Path(home) / "bin" / "hermes") if home else None]
    exe = next((c for c in candidates if c and os.access(c, os.X_OK)), None)
    if not exe:
        d.warn("hermes executable", "not found on PATH, /opt/venv/bin/hermes, or $HERMES_HOME/bin",
               "SETUP.md Step 0 (preflight): install Hermes or run the doctor inside the Hermes shell")
        return None
    rc, out = run([exe, "--version"])
    version = out.strip().splitlines()[0] if out.strip() else "version unknown"
    if rc == 0:
        d.ok("hermes executable", "%s (%s)" % (exe, version))
    else:
        d.warn("hermes executable", "%s found but 'hermes --version' failed" % exe,
               "SETUP.md Step 0: run 'hermes --version' by hand and check the install")
    return exe


def resolve_hermes_home(d, exe):
    home = os.environ.get("HERMES_HOME")
    source = "$HERMES_HOME"
    if not home and exe:
        rc, out = run([exe, "config", "path"])
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if lines and Path(lines[-1]).exists():  # tolerate non-zero rc; verify with 'hermes config --help'
            home, source = str(Path(lines[-1]).resolve().parent), "hermes config path"
    if not home and Path.home().joinpath(".hermes").is_dir():
        home, source = str(Path.home() / ".hermes"), "~/.hermes"
    if not home and Path("/data").is_dir():
        home, source = "/data", "/data (managed container default)"
    if not home:
        d.warn("HERMES_HOME", "could not resolve (no $HERMES_HOME, 'hermes config path', ~/.hermes, or /data)",
               "SETUP.md Step 0: export HERMES_HOME or run inside the Hermes environment; verify with 'hermes config --help'")
        return None, {}
    paths = {"config": Path(home) / "config.yaml", "env": Path(home) / ".env",
             "skills": Path(home) / "skills", "mcp_tokens": Path(home) / "mcp-tokens"}
    if exe:
        rc, out = run([exe, "config", "env-path"])
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if rc == 0 and lines and "/" in lines[-1]:
            paths["env"] = Path(lines[-1])
    present = ", ".join("%s=%s%s" % (k, p, "" if p.exists() else " (absent)") for k, p in paths.items())
    d.ok("HERMES_HOME", "%s via %s; %s" % (home, source, present))
    return home, paths


def check_setup_state(d, home):
    candidates = []
    if home:
        candidates.append(Path(home) / "hermes-ad-agent" / "setup-state.json")
    candidates.append(Path.home() / ".hermes" / "hermes-ad-agent" / "setup-state.json")
    path = next((p for p in candidates if p.is_file()), None)
    if not path:
        d.warn("setup-state", "no setup-state.json at " + " or ".join(str(c) for c in candidates),
               "SETUP.md Step 1: write the non-secret setup-state file so fresh sessions and cron jobs can find the workspace")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        d.block("setup-state", "%s is not valid JSON (%s)" % (path, type(e).__name__),
                "SETUP.md Step 1: rewrite setup-state.json")
        return None
    root = data.get("workspace_root")
    problems = []
    if data.get("schema_version") != 1:
        problems.append("schema_version != 1")
    if not root or not Path(str(root)).is_absolute():
        problems.append("workspace_root missing or not absolute")
    elif not Path(root).is_dir():
        problems.append("workspace_root does not exist")
    if data.get("meta_backend") not in ("mcp", "cli", "none"):
        problems.append("meta_backend not one of mcp|cli|none")
    if problems:
        d.block("setup-state", "%s: %s" % (path, "; ".join(problems)),
                "SETUP.md Step 1: fix the setup-state file (schema_version 1, absolute workspace_root, meta_backend)")
        return root if root and Path(str(root)).is_dir() else None
    d.ok("setup-state", "%s (meta_backend=%s, arcads_connected=%s, last_doctor_at=%s)" % (
        path, data.get("meta_backend"), data.get("arcads_connected"), data.get("last_doctor_at")))
    return root


def check_skills(d, workspace, paths):
    manifest = workspace / "skills-manifest.txt"
    if not manifest.is_file():
        d.warn("skills manifest", "%s not found" % manifest,
               "SETUP.md Step 2: the manifest is checked in; re-fetch the repo")
        return
    names = [l.strip() for l in manifest.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    missing_repo = [n for n in names if not (workspace / "skills" / n / "SKILL.md").is_file()]
    on_disk = sorted(p.name for p in (workspace / "skills").iterdir()
                     if p.is_dir() and p.name not in SKIP_SKILL_DIRS) if (workspace / "skills").is_dir() else []
    unlisted = [n for n in on_disk if n not in names]
    if missing_repo or unlisted:
        d.block("skills manifest", "manifest/skills mismatch: missing in repo=%s, unlisted=%s" % (missing_repo, unlisted),
                "SETUP.md Step 2: regenerate skills-manifest.txt from skills/*/")
    else:
        d.ok("skills manifest", "%d skills listed and present in the workspace" % len(names))
    hermes_skills = paths.get("skills") if paths else None
    if not hermes_skills or not hermes_skills.is_dir():
        d.warn("skills installed", "Hermes skills dir not found (%s)" % hermes_skills,
               "SETUP.md Step 2: install the skills (hub/tap first, local copy fallback)")
        return
    missing = [n for n in names if not (hermes_skills / n / "SKILL.md").is_file()]
    if missing:
        d.warn("skills installed", "missing in %s: %s" % (hermes_skills, missing),
               "SETUP.md Step 2: copy the missing skills from the workspace (local-copy fallback), then re-run")
    else:
        d.ok("skills installed", "all %d manifest skills present in %s" % (len(names), hermes_skills))


def check_config_secrets(d, paths):
    cfg = paths.get("config") if paths else None
    if not cfg or not cfg.is_file():
        d.warn("config secrets", "config.yaml not found; nothing scanned",
               "SETUP.md Step 4: connect Meta with 'hermes mcp add' so config.yaml exists")
        return
    hits = []
    for n, line in enumerate(cfg.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        s = line.strip()
        if re.match(r"(?i)authorization\s*:", s):
            value = s.split(":", 1)[1].strip().strip("'\"")
            if value and "${" not in value:
                hits.append("line %d: literal Authorization value" % n)
        if re.search(r"Bearer\s+EAA", s):
            hits.append("line %d: literal Bearer EAA token" % n)
        if re.search(r"(?i)(token|secret|api_key|apikey|password)\s*:\s*['\"]?[A-Za-z0-9_\-]{40,}", s):
            hits.append("line %d: long token-like literal" % n)
    if hits:
        d.block("config secrets", "%s: %s" % (cfg, "; ".join(hits)),
                "SETUP.md Step 4: move the token to the env file / managed-app environment and reference ${META_MCP_TOKEN}")
    else:
        d.ok("config secrets", "%s has no literal bearer tokens" % cfg)


def check_env_file(d, paths, workspace):
    files = []
    if paths and paths.get("env"):
        files.append(paths["env"])
    files.append(workspace / ".env")
    found_any = False
    for f in files:
        if not f.is_file():
            continue
        found_any = True
        keys = parse_env_file(f)
        for v in keys.values():
            if len(v) >= 20:
                _SECRETS.add(v)
        present = [k for k in TOKEN_NAMES if keys.get(k)]
        mode = stat.S_IMODE(f.stat().st_mode)
        detail = "%s: keys present=%s, mode=%o" % (f, present or "none", mode)
        if mode & 0o077:
            d.warn("env file", detail + " (group/other readable)",
                   "SETUP.md Step 4: chmod 600 the env file")
        else:
            d.ok("env file", detail)
    env_names = [k for k in TOKEN_NAMES if os.environ.get(k)]
    if env_names:
        d.ok("process env", "set in the process environment: %s" % env_names)
    if not found_any and not env_names:
        d.warn("env file", "no env file and no META_MCP_TOKEN/ACCESS_TOKEN in the environment",
               "SETUP.md Step 4: fine only if Meta is connected via the dashboard/OAuth relay; otherwise store the token in the managed app environment or 'hermes config env-path'")


def check_workspace(d, workspace):
    if (workspace / "BRAND.md").is_file():
        d.ok("BRAND.md", "present at %s" % workspace)
    else:
        d.warn("BRAND.md", "missing at %s" % workspace,
               "SETUP.md Step 6: run the brand-setup interview (skills refuse to launch without it or an approved run-scoped override)")
    if (workspace / "memory" / "accounts").is_dir():
        d.ok("memory/accounts", "present")
    else:
        d.warn("memory/accounts", "missing (no account audit has been run)",
               "SETUP.md Step 5: run the account deep dive")
    gi = workspace / ".gitignore"
    if not gi.is_file():
        d.warn(".gitignore", "missing", "SETUP.md Step 1: restore .gitignore from the repo")
        return
    lines = [l.strip() for l in gi.read_text(encoding="utf-8").splitlines()]
    missing = [p for p in GITIGNORE_REQUIRED if not any(l == p or l == "/" + p for l in lines)]
    if missing:
        d.warn(".gitignore", "missing entries: %s" % missing,
               "SETUP.md Step 1: add them; run state and research contain customer identifiers")
    else:
        d.ok(".gitignore", "ignores %s" % ", ".join(GITIGNORE_REQUIRED))


def graph_get(path, params):
    url = "%s%s?%s" % (GRAPH, path, urllib.parse.urlencode(params))
    req = urllib.request.Request(url, headers={"Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
            msg = body.get("error", {}).get("message", "HTTP %d" % e.code)
        except Exception:
            msg = "HTTP %d" % e.code
        return None, msg
    except Exception as e:  # network, timeout, decode
        return None, type(e).__name__


def iso(ts):
    if not ts:
        return "never"
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_meta_token(d, env_name, paths, workspace):
    names = [env_name] if env_name != "META_MCP_TOKEN" else ["META_MCP_TOKEN", "ACCESS_TOKEN"]
    token, used = None, None
    sources = [paths.get("env")] if paths and paths.get("env") else []
    sources.append(workspace / ".env")
    for n in names:
        token = os.environ.get(n)
        if not token:
            for f in sources:
                if f and f.is_file():
                    token = parse_env_file(f).get(n)
                    if token:
                        break
        if token:
            used = n
            break
    if not token:
        d.block("meta token", "none of %s set in the environment or env files" % names,
                "SETUP.md Step 4: store the Meta user token and reference it as ${META_MCP_TOKEN}")
        return
    _SECRETS.add(token)
    dbg, err = graph_get("/debug_token", {"input_token": token, "access_token": token})
    if err or not dbg or "data" not in dbg:
        d.block("meta token", "%s: debug_token failed (%s)" % (used, err or "no data"),
                "SETUP.md Step 4: the token is invalid or expired; issue a new user token and exchange it for a long-lived one")
        return
    data = dbg["data"]
    ttype = data.get("type", "UNKNOWN")
    perms, perr = graph_get("/me/permissions", {"access_token": token})
    granted = set(data.get("scopes") or [])
    if perms and isinstance(perms.get("data"), list):
        granted |= {p.get("permission") for p in perms["data"] if p.get("status") == "granted"}
    missing = [s for s in REQUIRED_SCOPES if s not in granted]
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    exp, dexp = data.get("expires_at") or 0, data.get("data_access_expires_at") or 0
    days = None if not exp else (exp - now) / 86400.0
    summary = "%s: type=%s, valid=%s, expires_at=%s, data_access_expires_at=%s, days_remaining=%s, missing_scopes=%s" % (
        used, ttype, data.get("is_valid"), iso(exp), iso(dexp),
        "n/a" if days is None else "%.1f" % days, missing or "none")
    if perr:
        summary += ", /me/permissions error=%s" % perr
    fix = "SETUP.md Step 4 (Route A token): "
    if data.get("is_valid") is False or (days is not None and days <= 0):
        d.block("meta token", summary + " (EXPIRED or invalid)", fix + "issue a new user token; Meta gave no refresh token, renewal is manual")
    elif used == "META_MCP_TOKEN" and ttype != "USER":
        d.block("meta token", summary + " (the hosted Meta MCP requires a USER token with ads_mcp_management; a SYSTEM_USER token is fine for the Meta Ads CLI route only)",
                fix + "generate a user token with all seven scopes")
    elif missing:
        d.block("meta token", summary, fix + "re-issue the token with all seven required scopes")
    elif days is not None and days < 21:
        d.warn("meta token", summary + " (renew soon)", fix + "exchange for a fresh long-lived token before expiry and update the env")
    else:
        d.ok("meta token", summary)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Read-only onboarding doctor for hermes-ad-agent.")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--workspace", help="workspace root (default: setup-state workspace_root, else cwd)")
    ap.add_argument("--meta-token-check", nargs="?", const="META_MCP_TOKEN", metavar="ENV_NAME",
                    help="validate the Meta token named ENV_NAME (default META_MCP_TOKEN, fallback ACCESS_TOKEN) against the Graph API")
    ap.add_argument("--arcads", action="store_true", help="out of scope; see the note it prints")
    args = ap.parse_args()

    d = Doctor()
    exe = check_hermes(d)
    home, paths = resolve_hermes_home(d, exe)
    state_root = check_setup_state(d, home)
    workspace = Path(args.workspace or state_root or os.getcwd()).resolve()
    if not workspace.is_dir():
        d.block("workspace", "%s does not exist" % workspace, "SETUP.md Step 1: pass --workspace <repo clone>")
    else:
        d.ok("workspace", str(workspace))
        check_skills(d, workspace, paths)
        check_workspace(d, workspace)
    check_config_secrets(d, paths)
    check_env_file(d, paths, workspace)
    if args.meta_token_check:
        check_meta_token(d, args.meta_token_check, paths, workspace)
    if args.arcads:
        d.ok("arcads", "out of scope for this doctor: verify with 'hermes mcp test arcads' plus a native read-only call (see SETUP.md Step 3)")

    code = d.exit_code()
    if args.json:
        print(json.dumps({"exit_code": code, "workspace": str(workspace),
                          "hermes_home": home, "checks": d.checks}, indent=2))
    else:
        for c in d.checks:
            line = "[%-5s] %s: %s" % (c["status"], c["check"], c["detail"])
            if c["fix"]:
                line += "\n        -> " + c["fix"]
            print(line)
        label = {0: "COMPLETE (all checks OK)", 1: "PARTIAL (warnings)", 2: "BLOCKED"}[code]
        print("\nResult: %s. Exit code %d. Read-only; nothing was changed." % (label, code))
    sys.exit(code)


if __name__ == "__main__":
    main()
