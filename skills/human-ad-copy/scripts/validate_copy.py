#!/usr/bin/env python3
"""Lint ad copy and validate Meta copy-payload copy.json files.

This is a deterministic style and contract checker, not an AI detector.

Exit codes:
    0: no hard findings (review findings may exist)
    1: one or more hard findings
    2: command-line or input error
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


DISCLAIMER = (
    "Heuristic copy lint only. Findings are style or contract cues, not "
    "evidence of AI authorship."
)
EXPECTED_COUNTS = {"body": 5, "title": 5, "description": 3}
FIELD_TO_JSON_KEY = {
    "body": "bodies",
    "title": "titles",
    "description": "descriptions",
}


@dataclass(frozen=True)
class TextUnit:
    """One independently rendered ad-copy variant."""

    kind: str
    location: str
    text: str


@dataclass(frozen=True)
class Finding:
    """One hard or review-level lint result."""

    severity: str
    code: str
    location: str
    line: int
    column: int
    message: str
    excerpt: str = ""


@dataclass(frozen=True)
class PatternRule:
    """A regex-backed review rule."""

    code: str
    pattern: re.Pattern[str]
    message: str


@dataclass
class Report:
    """Complete result for one input."""

    source: str
    mode: str
    findings: List[Finding] = field(default_factory=list)
    units: List[TextUnit] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def hard_count(self) -> int:
        return sum(item.severity == "HARD" for item in self.findings)

    @property
    def review_count(self) -> int:
        return sum(item.severity == "REVIEW" for item in self.findings)


AI_VOCABULARY = re.compile(
    r"\b(?:"
    r"delv(?:e|es|ed|ing)|deep[- ]dive|crucial|pivotal|vital|"
    r"seamless(?:ly)?|effortless(?:ly)?|frictionless|"
    r"unlock(?:s|ed|ing)?|unleash(?:es|ed|ing)?|elevat(?:e|es|ed|ing)|"
    r"empower(?:s|ed|ing)?|supercharg(?:e|es|ed|ing)|"
    r"game[- ]chang(?:er|ing)|revolutionary|groundbreaking|transformative|"
    r"cutting[- ]edge|next[- ]level|future[- ]proof|"
    r"leverag(?:e|es|ed|ing)|utiliz(?:e|es|ed|ing)|harness(?:es|ed|ing)?|"
    r"landscape|realm|ecosystem|tapestry|testament|journey|"
    r"robust|comprehensive|holistic|meticulous(?:ly)?|intricate|intricacies|"
    r"foster(?:s|ed|ing)?|garner(?:s|ed|ing)?|bolster(?:s|ed|ing)?|"
    r"streamlin(?:e|es|ed|ing)|showcas(?:e|es|ed|ing)|boasts?"
    r")\b",
    re.IGNORECASE,
)

REVIEW_RULES: Sequence[PatternRule] = (
    PatternRule(
        "AI_PHRASE",
        re.compile(
            r"\b(?:"
            r"in today['’]s(?: fast[- ]paced)?(?: world| market| environment)?|"
            r"in (?:an? )?ever[- ]evolving landscape|"
            r"look no further|we['’]ve got you covered|"
            r"say goodbye to|say hello to|the possibilities are endless|"
            r"take (?:your|the) [^.!?\n]{1,50} to the next level|"
            r"unlock your (?:full )?potential|designed to empower|"
            r"whether you['’]re [^.!?\n]{1,50} or [^.!?\n]{1,50}|"
            r"imagine a world where|ready to (?:transform|revolutionize|unlock)|"
            r"actionable insights?|valuable insights?|here['’]s the truth"
            r")\b",
            re.IGNORECASE,
        ),
        "Canned marketing phrase. Replace the shape with a concrete fact or action.",
    ),
    PatternRule(
        "NEGATIVE_PARALLELISM",
        re.compile(
            r"(?:"
            r"\bnot just\b|"
            r"\bnot only\b[^.!?\n]{0,100}\bbut also\b|"
            r"\b(?:it|this|that)['’]?s not about\b[^.!?\n]{0,100}"
            r"\b(?:it|this|that)['’]?s about\b|"
            r"\bmore than just\b|\b(?:isn['’]?t|is not) another\b|"
            r"\bno\b[^.!?\n]{1,60}[.!?]\s*\bno\b[^.!?\n]{1,60}"
            r"[.!?]\s*\bjust\b"
            r")",
            re.IGNORECASE,
        ),
        "Negative parallelism cue. State the supported positive claim directly.",
    ),
    PatternRule(
        "RHETORICAL_PIVOT",
        re.compile(
            r"\b(?:the result|the best part|the catch|the kicker|"
            r"the difference|the problem)\?",
            re.IGNORECASE,
        ),
        "Stock rhetorical pivot. Consider stating the answer directly.",
    ),
    PatternRule(
        "PARTICIPLE_TAIL",
        re.compile(
            r",\s+(?:ensuring|enabling|allowing you|helping you|giving you|"
            r"letting you|highlighting|showcasing|underscoring|reflecting|"
            r"emphasizing|fostering|empowering)\b",
            re.IGNORECASE,
        ),
        "Glued-on benefit clause. Give the benefit its own receipt or remove it.",
    ),
    PatternRule(
        "COPULA_AVOIDANCE",
        re.compile(
            r"\b(?:serves as|stands as|acts as an?|marks an?|represents an?|"
            r"offers a comprehensive|features a robust)\b",
            re.IGNORECASE,
        ),
        "Inflated construction. Check whether plain 'is' or 'has' is clearer.",
    ),
    PatternRule(
        "VAGUE_CLAIM_CUE",
        re.compile(
            r"\b(?:"
            r"(?:experts?|industry leaders?|professionals?|customers?) "
            r"(?:say|agree|recommend|love)|"
            r"(?:studies|research|data|industry reports?) "
            r"(?:shows?|proves?|suggests?|confirms?)|"
            r"trusted by (?:thousands|millions|professionals|teams|brands|businesses)|"
            r"(?:clinically proven|science[- ]backed|proven results?|"
            r"guaranteed (?:results?|success))|"
            r"(?:the (?:best|leading|only)|number one|#\s*1)|"
            r"(?:up to\s+\d+(?:\.\d+)?\s*%?)|"
            r"(?:\d+(?:\.\d+)?\s*[xX]\b)|"
            r"(?:widely regarded|recognized everywhere)"
            r")",
            re.IGNORECASE,
        ),
        (
            "Claim cue needs a source, scope, and qualification. The scanner "
            "cannot determine whether the claim is supported."
        ),
    ),
    PatternRule(
        "BOLD_LABEL_BULLET",
        re.compile(r"^\s*[-*•]\s+\*\*[^*\n]+:\*\*", re.MULTILINE),
        "Repeated bold-label bullets can create mechanical list rhythm.",
    ),
    PatternRule(
        "EMOJI_BULLET",
        re.compile(
            r"^\s*[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\u2600-\u27BF]",
            re.MULTILINE,
        ),
        "Line-leading emoji may be acting as list scaffolding.",
    ),
)

STOPWORDS: Set[str] = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "get",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
    "you",
    "your",
}

TOKEN_ALIASES = {
    "build": "create",
    "built": "create",
    "building": "create",
    "create": "create",
    "created": "create",
    "creating": "create",
    "generate": "create",
    "generated": "create",
    "generating": "create",
    "quick": "fast",
    "quicker": "fast",
    "quickly": "fast",
    "faster": "fast",
    "fastest": "fast",
    "purchase": "buy",
    "purchased": "buy",
    "purchases": "buy",
    "shop": "buy",
}


def contract_finding(
    code: str,
    location: str,
    message: str,
    *,
    line: int = 1,
    column: int = 1,
    excerpt: str = "",
) -> Finding:
    """Create a deterministic hard finding."""

    return Finding("HARD", code, location, line, column, message, excerpt)


def review_finding(
    code: str,
    location: str,
    message: str,
    *,
    line: int = 1,
    column: int = 1,
    excerpt: str = "",
) -> Finding:
    """Create a context-dependent review finding."""

    return Finding("REVIEW", code, location, line, column, message, excerpt)


def line_column(text: str, index: int) -> Tuple[int, int]:
    """Convert a character offset into one-based line and column."""

    line = text.count("\n", 0, index) + 1
    last_break = text.rfind("\n", 0, index)
    column = index + 1 if last_break < 0 else index - last_break
    return line, column


def line_excerpt(text: str, index: int, width: int = 120) -> str:
    """Return a compact source line around a match."""

    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    if end < 0:
        end = len(text)
    value = text[start:end].strip()
    if len(value) <= width:
        return value
    offset = max(0, index - start - width // 2)
    clipped = value[offset : offset + width]
    if offset:
        clipped = "..." + clipped[3:]
    if offset + width < len(value):
        clipped = clipped[:-3] + "..."
    return clipped


def pattern_findings(unit: TextUnit) -> List[Finding]:
    """Run punctuation, vocabulary, phrase, and claim-cue rules."""

    findings: List[Finding] = []
    phrase_spans: List[Tuple[int, int]] = []

    for match in re.finditer("\u2014", unit.text):
        line, column = line_column(unit.text, match.start())
        findings.append(
            contract_finding(
                "EM_DASH",
                unit.location,
                "Em dash violates this skill's no-em-dash output rule.",
                line=line,
                column=column,
                excerpt=line_excerpt(unit.text, match.start()),
            )
        )

    for rule in REVIEW_RULES:
        for match in rule.pattern.finditer(unit.text):
            line, column = line_column(unit.text, match.start())
            findings.append(
                review_finding(
                    rule.code,
                    unit.location,
                    rule.message,
                    line=line,
                    column=column,
                    excerpt=line_excerpt(unit.text, match.start()),
                )
            )
            if rule.code == "AI_PHRASE":
                phrase_spans.append(match.span())

    for match in AI_VOCABULARY.finditer(unit.text):
        if any(start <= match.start() < end for start, end in phrase_spans):
            continue
        line, column = line_column(unit.text, match.start())
        findings.append(
            review_finding(
                "AI_VOCAB",
                unit.location,
                (
                    f"Generic vocabulary cue '{match.group(0)}'. Replace it "
                    "with a concrete fact when it is doing no literal work."
                ),
                line=line,
                column=column,
                excerpt=line_excerpt(unit.text, match.start()),
            )
        )

    return findings


def normalized_text(value: str) -> str:
    """Normalize case, Unicode, punctuation, and whitespace for equality."""

    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def stem_token(token: str) -> str:
    """Apply a deliberately small stemmer for lexical comparison."""

    token = TOKEN_ALIASES.get(token, token)
    if len(token) > 5 and token.endswith("ies"):
        token = token[:-3] + "y"
    elif len(token) > 5 and token.endswith("ing"):
        token = token[:-3]
    elif len(token) > 4 and token.endswith("ed"):
        token = token[:-2]
    elif len(token) > 4 and token.endswith("s"):
        token = token[:-1]
    return TOKEN_ALIASES.get(token, token)


def content_tokens(value: str) -> Set[str]:
    """Return normalized content tokens for near-duplicate review."""

    tokens = re.findall(r"\b[\w']+\b", normalized_text(value))
    return {
        stem_token(token)
        for token in tokens
        if token not in STOPWORDS and len(token) > 1
    }


def lexical_similarity(left: str, right: str) -> Tuple[float, float, float]:
    """Return character ratio, token Jaccard, and token containment."""

    left_normalized = normalized_text(left)
    right_normalized = normalized_text(right)
    character_ratio = difflib.SequenceMatcher(
        None, left_normalized, right_normalized, autojunk=False
    ).ratio()
    left_tokens = content_tokens(left)
    right_tokens = content_tokens(right)
    union = left_tokens | right_tokens
    intersection = left_tokens & right_tokens
    jaccard = len(intersection) / len(union) if union else 0.0
    smallest = min(len(left_tokens), len(right_tokens))
    containment = len(intersection) / smallest if smallest else 0.0
    return character_ratio, jaccard, containment


def duplicate_findings(units: Iterable[TextUnit]) -> List[Finding]:
    """Find exact and lexical near-duplicates within each field type."""

    findings: List[Finding] = []
    grouped: Dict[str, List[TextUnit]] = {}
    for unit in units:
        grouped.setdefault(unit.kind, []).append(unit)

    for kind_units in grouped.values():
        for index, left in enumerate(kind_units):
            for right in kind_units[index + 1 :]:
                left_normalized = normalized_text(left.text)
                right_normalized = normalized_text(right.text)
                if not left_normalized or not right_normalized:
                    continue
                pair_location = f"{left.location} <-> {right.location}"
                if left_normalized == right_normalized:
                    findings.append(
                        contract_finding(
                            "EXACT_DUPLICATE",
                            pair_location,
                            (
                                "Variants are identical after case, punctuation, "
                                "and whitespace normalization."
                            ),
                        )
                    )
                    continue

                if min(len(left_normalized), len(right_normalized)) < 12:
                    continue
                char_ratio, jaccard, containment = lexical_similarity(
                    left.text, right.text
                )
                is_candidate = (
                    char_ratio >= 0.84
                    or (jaccard >= 0.72 and containment >= 0.80)
                    or (char_ratio >= 0.68 and containment >= 0.90)
                )
                if is_candidate:
                    score = max(char_ratio, jaccard)
                    findings.append(
                        review_finding(
                            "PARAPHRASE_CANDIDATE",
                            pair_location,
                            (
                                f"Lexical near-duplicate candidate "
                                f"(similarity {score:.2f}). Test a different "
                                "angle or receipt. This is not a semantic verdict."
                            ),
                        )
                    )
    return findings


def first_nonempty_line(value: str) -> str:
    """Return the first rendered line containing copy."""

    for line in value.splitlines():
        if line.strip():
            return line.strip()
    return ""


def length_findings(units: Iterable[TextUnit]) -> List[Finding]:
    """Apply non-blocking Meta creative-length guidance."""

    findings: List[Finding] = []
    for unit in units:
        if unit.kind == "body":
            opening = first_nonempty_line(unit.text)
            if len(opening) > 125:
                findings.append(
                    review_finding(
                        "PRIMARY_OPENING_LENGTH",
                        unit.location,
                        (
                            f"Opening line is {len(opening)} characters. Roughly "
                            "125 often appear before expansion; long primary "
                            "text itself is allowed."
                        ),
                        excerpt=opening[:120],
                    )
                )
        elif unit.kind == "title" and len(unit.text) > 40:
            findings.append(
                review_finding(
                    "HEADLINE_LENGTH",
                    unit.location,
                    (
                        f"Headline is {len(unit.text)} characters; aim for about "
                        "40 or fewer when the meaning survives."
                    ),
                    excerpt=unit.text[:120],
                )
            )
        elif unit.kind == "description" and len(unit.text) > 50:
            findings.append(
                review_finding(
                    "DESCRIPTION_LENGTH",
                    unit.location,
                    (
                        f"Description is {len(unit.text)} characters; roughly "
                        "30 to 50 is the working guidance."
                    ),
                    excerpt=unit.text[:120],
                )
            )
    return findings


def extract_variant_text(
    item: Any,
    *,
    kind: str,
    location: str,
) -> Tuple[Optional[str], List[Finding]]:
    """Validate and extract one supported copy-payload item."""

    findings: List[Finding] = []
    if kind == "body":
        if not isinstance(item, str):
            return None, [
                contract_finding(
                    "ITEM_TYPE",
                    location,
                    "Body values must be strings in the copy payload.",
                )
            ]
        value = item
    elif isinstance(item, str):
        value = item
    elif isinstance(item, dict):
        if "text" not in item:
            return None, [
                contract_finding(
                    "ITEM_SHAPE",
                    location,
                    "Object value must contain a 'text' field.",
                )
            ]
        if not isinstance(item["text"], str):
            return None, [
                contract_finding(
                    "ITEM_TYPE",
                    f"{location}.text",
                    "The 'text' field must be a string.",
                )
            ]
        value = item["text"]
    else:
        return None, [
            contract_finding(
                "ITEM_TYPE",
                location,
                "Title and description values must be strings or {'text': string}.",
            )
        ]

    if not value.strip():
        findings.append(
            contract_finding(
                "EMPTY_VALUE",
                location,
                "Copy values must contain non-whitespace text.",
            )
        )
        return None, findings
    return value.strip(), findings


def validate_meta_data(data: Any, source: str) -> Report:
    """Validate parsed copy-payload data and scan every copy variant."""

    report = Report(source=source, mode="meta-json")
    if not isinstance(data, dict):
        report.findings.append(
            contract_finding(
                "ROOT_TYPE",
                source,
                "copy.json root must be a JSON object.",
            )
        )
        return report

    expected_keys = set(FIELD_TO_JSON_KEY.values())
    for extra_key in sorted(set(data) - expected_keys):
        report.findings.append(
            review_finding(
                "EXTRA_KEY",
                str(extra_key),
                "The copy payload ignores this extra top-level key.",
            )
        )

    counts: Dict[str, int] = {}
    for kind, json_key in FIELD_TO_JSON_KEY.items():
        if json_key not in data:
            report.findings.append(
                contract_finding(
                    "MISSING_KEY",
                    json_key,
                    f"copy.json requires a '{json_key}' array.",
                )
            )
            continue

        items = data[json_key]
        if not isinstance(items, list):
            report.findings.append(
                contract_finding(
                    "FIELD_TYPE",
                    json_key,
                    f"'{json_key}' must be an array.",
                )
            )
            continue

        counts[json_key] = len(items)
        if not items:
            report.findings.append(
                contract_finding(
                    "EMPTY_ARRAY",
                    json_key,
                    f"'{json_key}' must contain at least one value.",
                )
            )
            continue

        expected_count = EXPECTED_COUNTS[kind]
        if len(items) != expected_count:
            report.findings.append(
                review_finding(
                    "VARIANT_COUNT",
                    json_key,
                    (
                        f"Found {len(items)}; this skill's guidance is "
                        f"{expected_count} {json_key}. This is guidance, not "
                        "an authorship signal."
                    ),
                )
            )

        for index, item in enumerate(items):
            location = f"{json_key}[{index}]"
            value, item_findings = extract_variant_text(
                item, kind=kind, location=location
            )
            report.findings.extend(item_findings)
            if value is not None:
                report.units.append(TextUnit(kind, location, value))

    report.stats["variant_counts"] = counts
    finish_report(report)
    return report


def validate_meta_json(text: str, source: str) -> Report:
    """Parse, validate, and scan a copy-payload JSON document."""

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        excerpt = ""
        lines = text.splitlines()
        if 0 < error.lineno <= len(lines):
            excerpt = lines[error.lineno - 1].strip()[:120]
        report = Report(source=source, mode="meta-json")
        report.findings.append(
            contract_finding(
                "JSON_PARSE",
                source,
                f"Invalid JSON: {error.msg}.",
                line=error.lineno,
                column=error.colno,
                excerpt=excerpt,
            )
        )
        return report
    return validate_meta_data(data, source)


def validate_text(text: str, source: str, field_kind: str = "generic") -> Report:
    """Scan a plain-text draft, optionally with one Meta field type."""

    report = Report(source=source, mode="text")
    if not text.strip():
        report.findings.append(
            contract_finding("EMPTY_INPUT", source, "Draft contains no copy.")
        )
        return report
    unit = TextUnit(field_kind, source, text.strip())
    report.units.append(unit)
    finish_report(report)
    return report


def finish_report(report: Report) -> None:
    """Apply common scans, build stats, and sort findings."""

    for unit in report.units:
        report.findings.extend(pattern_findings(unit))
    report.findings.extend(duplicate_findings(report.units))
    report.findings.extend(length_findings(report.units))

    character_counts: Dict[str, List[int]] = {}
    for unit in report.units:
        key = FIELD_TO_JSON_KEY.get(unit.kind, unit.kind)
        character_counts.setdefault(key, []).append(len(unit.text))
    report.stats["character_counts"] = character_counts
    report.findings.sort(
        key=lambda item: (
            0 if item.severity == "HARD" else 1,
            item.location,
            item.line,
            item.column,
            item.code,
        )
    )


def report_as_json(report: Report) -> str:
    """Serialize a report for automation."""

    payload = {
        "source": report.source,
        "mode": report.mode,
        "disclaimer": DISCLAIMER,
        "hard_count": report.hard_count,
        "review_count": report.review_count,
        "findings": [asdict(item) for item in report.findings],
        "stats": report.stats,
        "exit_code": 1 if report.hard_count else 0,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def report_as_text(report: Report) -> str:
    """Render a compact human-readable report."""

    lines = [
        f"Copy lint: {report.source} ({report.mode})",
        DISCLAIMER,
    ]
    counts = report.stats.get("variant_counts")
    if counts:
        lines.append(
            "Variants: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )

    if not report.findings:
        lines.extend(
            [
                "",
                "Clean mechanical scan. Manual truth, voice, and angle review still required.",
            ]
        )
    else:
        for item in report.findings:
            position = item.location
            if item.line > 1 or item.column > 1:
                position = f"{position}:{item.line}:{item.column}"
            lines.extend(
                [
                    "",
                    f"[{item.severity}] {item.code} at {position}",
                    f"  {item.message}",
                ]
            )
            if item.excerpt:
                lines.append(f"  > {item.excerpt}")

    lines.extend(
        [
            "",
            f"Summary: hard={report.hard_count} review={report.review_count}",
            (
                "Result: FAIL (hard findings must be fixed)."
                if report.hard_count
                else "Result: PASS (review findings remain editorial decisions)."
            ),
        ]
    )
    return "\n".join(lines)


def detect_mode(path: str, text: str, requested: str) -> str:
    """Choose text or meta-json mode."""

    if requested != "auto":
        return requested
    if path != "-" and Path(path).suffix.casefold() == ".json":
        return "meta-json"
    if path == "-" and text.lstrip().startswith("{"):
        return "meta-json"
    return "text"


def read_input(path: str) -> str:
    """Read UTF-8 input from a path or stdin."""

    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8-sig")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Lint ad copy and validate a Meta copy-payload copy.json. "
            "This is not an AI detector."
        )
    )
    parser.add_argument("input", help="Draft text/copy.json path, or - for stdin")
    parser.add_argument(
        "--format",
        choices=("auto", "text", "meta-json"),
        default="auto",
        help="Input format (default: infer .json as meta-json)",
    )
    parser.add_argument(
        "--field",
        choices=("generic", "body", "title", "description"),
        default="generic",
        help="Meta field type for a plain-text input (enables length guidance)",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Report format (default: text)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""

    args = build_parser().parse_args(argv)
    try:
        text = read_input(args.input)
    except (OSError, UnicodeError) as error:
        print(f"Input error: {error}", file=sys.stderr)
        return 2

    mode = detect_mode(args.input, text, args.format)
    if mode == "meta-json":
        report = validate_meta_json(text, args.input)
    else:
        report = validate_text(text, args.input, args.field)

    output = report_as_json(report) if args.output == "json" else report_as_text(report)
    print(output)
    return 1 if report.hard_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
