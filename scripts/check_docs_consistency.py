#!/usr/bin/env python3
"""Docs consistency check for the hermes-ad-agent pack (read-only, stdlib).

Scans every *.md git would publish (skipping .git, memory/, outputs/, ad-runs/,
research/, and anything gitignored) and fails on:
  - em-dash characters (U+2014) outside the two allowed human-ad-copy lines
  - obsolete phrases that the onboarding review retired
  - the one-flag-many-values CLI pattern (--bodies "A" "B")
  - stale Arcads credit rates written as estimates
  - skills-manifest.txt not matching skills/*/ exactly
  - SKILL.md frontmatter whose name differs from its folder

Prints file:line for every hit. Exit 0 clean, 1 on any hit.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "memory", "outputs", "ad-runs", "research", "node_modules", "__pycache__"}
EM_DASH = "\u2014"
# (relative path, substring that identifies the one allowed line)
ALLOWED_EM_DASH = (
    ("skills/human-ad-copy/SKILL.md", "never use em dashes"),
    ("skills/human-ad-copy/references/ai-tells.md", "no-em-dash house rule"),
)
# Case-insensitive obsolete phrases. The third field is an optional
# exemption: skip the hit when this word appears earlier on the same line.
OBSOLETE = (
    ("no developer app", None),
    ("no App Review, no API token", None),
    ("Anything asks you for an API key", None),
    ("one ad per variant", "never"),
    ("Graph POST, last resort", None),
)
UPLOAD_RE = re.compile(r"ads_creative_upload")
WITH_FILE_RE = re.compile(r"(?i)with the file")
MULTI_VALUE_RE = re.compile(r"""--(?:bodies|titles|descriptions)\s+(?:"[^"]*"|'[^']*')\s+(?:"|')""")
STALE_CREDIT_RE = re.compile(r"(?i)(~\s*0\.9\s*credits?|0\.9\s*credits?\s+per)")
NAME_RE = re.compile(r"^name:\s*['\"]?([^'\"\s]+)['\"]?\s*$")


def git_visible():
    """Files git would publish (tracked or untracked-not-ignored), or None."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others",
                              "--exclude-standard", "-z"], capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return {f for f in out.stdout.decode("utf-8", "replace").split("\0") if f}


def md_files():
    visible = git_visible()
    for p in sorted(ROOT.rglob("*.md")):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if visible is not None and rel.as_posix() not in visible:
            continue  # gitignored local file, not part of the public pack
        yield p, rel.as_posix()


def scan_markdown():
    hits = []
    for path, rel in md_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            hits.append("%s:0: not valid UTF-8" % rel)
            continue
        for n, line in enumerate(lines, 1):
            low = line.lower()
            if EM_DASH in line and not any(rel == a and marker in line for a, marker in ALLOWED_EM_DASH):
                hits.append("%s:%d: em-dash (U+2014)" % (rel, n))
            for phrase, exempt in OBSOLETE:
                idx = low.find(phrase.lower())
                if idx == -1:
                    continue
                if exempt and exempt in low[:idx]:
                    continue
                hits.append("%s:%d: obsolete phrase %r" % (rel, n, phrase))
            if UPLOAD_RE.search(line) and WITH_FILE_RE.search(line):
                hits.append("%s:%d: 'with the file' next to ads_creative_upload (MCP uploads take public URLs only)" % (rel, n))
            if MULTI_VALUE_RE.search(line):
                hits.append("%s:%d: one-flag-many-values CLI pattern (repeat the flag per value)" % (rel, n))
            if STALE_CREDIT_RE.search(line):
                hits.append("%s:%d: stale credit rate written as an estimate (only creditsCharged is cost)" % (rel, n))
    return hits


def scan_skills():
    hits = []
    skills_dir = ROOT / "skills"
    folders = sorted(p.name for p in skills_dir.iterdir()
                     if p.is_dir() and p.name not in SKIP_DIRS) if skills_dir.is_dir() else []
    manifest = ROOT / "skills-manifest.txt"
    if not manifest.is_file():
        hits.append("skills-manifest.txt:0: missing (expected one skill folder name per line)")
    else:
        listed = [l.strip() for l in manifest.read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.lstrip().startswith("#")]
        seen = set()
        for i, name in enumerate(listed, 1):
            if name in seen:
                hits.append("skills-manifest.txt:%d: duplicate entry %r" % (i, name))
            seen.add(name)
            if name not in folders:
                hits.append("skills-manifest.txt:%d: %r has no skills/%s/ folder" % (i, name, name))
        for name in folders:
            if name not in seen:
                hits.append("skills-manifest.txt:0: skills/%s/ is not listed" % name)
    for name in folders:
        skill = skills_dir / name / "SKILL.md"
        if not skill.is_file():
            hits.append("skills/%s/SKILL.md:0: missing" % name)
            continue
        lines = skill.read_text(encoding="utf-8").splitlines()
        if not lines or lines[0].strip() != "---":
            hits.append("skills/%s/SKILL.md:1: no frontmatter block" % name)
            continue
        fm_name = None
        for n, line in enumerate(lines[1:], 2):
            if line.strip() == "---":
                break
            m = NAME_RE.match(line)
            if m:
                fm_name = (m.group(1), n)
        if not fm_name:
            hits.append("skills/%s/SKILL.md:1: frontmatter has no name field" % name)
        elif fm_name[0] != name:
            hits.append("skills/%s/SKILL.md:%d: frontmatter name %r != folder %r" % (name, fm_name[1], fm_name[0], name))
    return hits


def main():
    hits = scan_markdown() + scan_skills()
    for h in hits:
        print(h)
    if hits:
        print("\n%d issue(s) found." % len(hits))
        sys.exit(1)
    print("Docs consistency: clean.")
    sys.exit(0)


if __name__ == "__main__":
    main()
