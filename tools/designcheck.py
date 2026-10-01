#!/usr/bin/env python3
"""designcheck: find the default-AI aesthetic in HTML, CSS, and component files.

The visual counterpart to slopcheck. DESIGN.md 1.1 keeps the inventory of
tells that mark a UI as "a model made this" — the violet-to-indigo gradient,
the gradient-filled headline, glassmorphism on every surface, the same 1rem
radius everywhere, Inter-on-slate as an unconsidered default. This file turns
that inventory into a deterministic gate: no browser, no model, no network.

What it deliberately does NOT do:

  * Accessibility math. Contrast and touch-target checks belong to a real
    engine (axe-core); a hand-rolled checker produced ~70 false positives per
    theme once by skipping alpha compositing (LEDGER 2026-08-24). The one
    exception is the token-contrast test pattern DESIGN.md 3 prescribes,
    which lives beside the site build, not here.
  * Taste. It flags the *unconsidered default*, not any use of purple. Every
    escape is an allowlist entry with a written reason.

Rules it follows, inherited from slopcheck and enforced on itself:

  * It prints how much it examined. Scanning nothing is exit 2, never a pass.
  * Every rule ships a known-bad fixture that must fire and a known-good one
    that must not; --selftest proves the rules can still fail.
  * Every exemption carries a reason with substance, checked at load.

Usage:
  python3 tools/designcheck.py docs/ src/components/
  python3 tools/designcheck.py --selftest
  python3 tools/designcheck.py --list
  python3 tools/designcheck.py --explain ai-gradient-palette
  python3 tools/designcheck.py --only glassmorphism,web-font-import docs/
  python3 tools/designcheck.py --calibrate .
  python3 tools/designcheck.py --fail-on WARN --json findings.json docs/

Config: an optional .designcheck.json beside the scanned root.

  {
    "exclude": ["vendor", "third_party/theme"],
    "disable": {"slate-default-dark": "client brand palette is Tailwind slate by contract"},
    "promote": {"glassmorphism": "FAIL"},
    "demote":  {"hex-outside-root": "INFO"},
    "allow": [{"substring": "linear-gradient(90deg, #4f46e5",
               "reason": "the queue-depth ramp encodes data; indigo end matches the agency's chart key"}],
    "thresholds": {"motion_max_ms": {"value": 400, "reason": "..."}}
  }

Exit codes: 0 clean, 1 findings at or above --fail-on, 2 nothing scanned or a
usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

VERSION = "1.0"

LEVELS = ("FAIL", "WARN", "INFO")
LEVEL_RANK = {"FAIL": 3, "WARN": 2, "INFO": 1, "NEVER": 99}

SUPPORTED_SUFFIXES = {".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".jsx",
                      ".ts", ".tsx", ".vue", ".svelte"}

DEFAULT_EXCLUDE_PARTS = {
    ".git", "node_modules", "dist", "build", ".next", "__pycache__", ".venv",
    "venv", "coverage", "vendor", "third_party", ".cache", "out", ".turbo",
    ".claude", "min",
}

MAX_FILE_BYTES = 2_000_000

# Every threshold stated here, overridable with a reason in .designcheck.json.
DEFAULTS: Dict[str, float] = {
    "motion_max_ms": 300,          # DESIGN.md 5: no motion above 300ms
    "radius_census_min_uses": 5,   # below this, uniformity is coincidence
    "radius_uniform_min_px": 12,   # the tell is everything rounded 2xl-ish
    "shadow_distinct_max": 3,      # DESIGN.md 5 names exactly two shadows
    "hero_min_ctas": 2,            # centered hero + two buttons is the template
}

EMOJI = ("[\U0001F300-\U0001FAFF\U0001F000-\U0001F2FF☀-⛿"
         "✨✅❌❤⭐⚡]")

# The indigo/violet family a generated UI defaults to. Hex values are the
# Tailwind indigo/violet/purple/fuchsia ramps plus the #667eea/#764ba2 pair
# that half the internet's AI heroes ship.
AI_GRADIENT_HEXES = (
    "667eea|764ba2|6366f1|4f46e5|4338ca|3730a3|818cf8|a5b4fc|"
    "8b5cf6|7c3aed|6d28d9|a78bfa|c4b5fd|9333ea|a855f7|c084fc|"
    "d946ef|e879f9|ec4899"
)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Rule:
    id: str
    level: str
    family: str
    why: str
    fix: str
    pattern: Optional[str] = None
    computed: bool = False
    origin: str = ""
    bad: str = ""                 # one fixture file's content that must fire
    good: str = ""                # one that must not
    fixture_suffix: str = ".css"  # what kind of file the fixtures pretend to be

    def compiled(self) -> Optional["re.Pattern[str]"]:
        return re.compile(self.pattern, re.I) if self.pattern else None


RULES: List[Rule] = [
    Rule(
        "ai-gradient-palette", "FAIL", "palette",
        "the violet-to-indigo gradient backdrop, the single most recognizable "
        "mark of an unconsidered model-generated UI",
        "commit to a flat palette derived from the subject; one accent. "
        "Gradients only when they encode data, allowlisted with the reason",
        r"(?:linear|radial|conic)-gradient\([^)]*"
        r"(?:#(?:" + AI_GRADIENT_HEXES + r")\b|\b(?:indigo|violet|purple|fuchsia|blueviolet|mediumpurple)\b)"
        r"[^)]*\)",
        origin="DESIGN.md 1.1 row 1",
        bad=".hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }",
        good=".ramp { background: linear-gradient(90deg, #0b3d2e, #1f7a4d); }",
    ),
    Rule(
        "gradient-text", "FAIL", "palette",
        "a gradient-filled headline; the text version of the same tell",
        "give the headline one color with real contrast",
        r"(?:-webkit-)?background-clip\s*:\s*text|\bbg-clip-text\b",
        origin="DESIGN.md 1.1 row 1 (gradient-filled headline text)",
        bad="h1 { background: linear-gradient(90deg, #111, #333); -webkit-background-clip: text; color: transparent; }",
        good="h1 { color: var(--text); }",
    ),
    Rule(
        "made-with-footer", "FAIL", "copy",
        "the \"Made with love\" footer; decoration standing in for authorship",
        "credit a person, a license, or nothing",
        r"(?:built|made|crafted)\s+with\s+(?:❤️?|♥|&hearts;|love|☕)|powered\s+by\s+AI\b",
        origin="DESIGN.md 1.1 concrete-labels row; the footer variant of pill ceremony",
        bad="<footer>Made with ❤️ by the team</footer>",
        good="<footer>MIT license. Source on GitHub.</footer>",
        fixture_suffix=".html",
    ),
    Rule(
        "sparkle-glyph", "FAIL", "copy",
        "the sparkle emoji doing badge work (✨ New)",
        "say what changed and when, in words and dates",
        "✨",
        origin="DESIGN.md 1.1 row 8 (pill ceremony)",
        bad='<span class="pill">✨ New</span>',
        good='<span class="pill">Added 2026-08-30</span>',
        fixture_suffix=".html",
    ),
    Rule(
        "glassmorphism", "WARN", "surface",
        "backdrop blur as a default surface treatment; it reads generated and "
        "recomposites every frame",
        "choose one structural device (hairline rules, a hard border, a "
        "visible grid) and commit to it",
        r"backdrop-filter\s*:\s*blur|\bbackdrop-blur(?:-(?:sm|md|lg|xl|2xl|3xl|\[[^\]]+\]))?\b",
        origin="DESIGN.md 1.1 row 5; 10 (no backdrop-filter on hot panes)",
        bad=".card { backdrop-filter: blur(12px); background: rgba(255,255,255,0.1); }",
        good=".card { background: var(--surface); border: 1px solid var(--border); }",
    ),
    Rule(
        "slate-default-dark", "WARN", "palette",
        "the framework's slate-900 dark mode shipped as-is",
        "derive the dark surface from the project's own palette",
        r"#0f172a\b|#1e293b\b|rgb\(\s*15\s*[, ]\s*23\s*[, ]\s*42",
        origin="DESIGN.md 1.1 row 7",
        bad="body { background: #0f172a; }",
        good="body { background: #101418; }",
    ),
    Rule(
        "web-font-import", "WARN", "type",
        "a remote font fetch; a render-blocking RTT the system stack avoids",
        "use the system stacks in DESIGN.md 2, or record the sign-off as the "
        "allowlist reason",
        r"fonts\.googleapis\.com|fonts\.gstatic\.com|use\.typekit\.net|fonts\.bunny\.net",
        origin="DESIGN.md 2; 12.5 (no web fonts without sign-off)",
        bad='<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700" rel="stylesheet">',
        good='<link rel="stylesheet" href="./styles.css">',
        fixture_suffix=".html",
    ),
    Rule(
        "default-face", "WARN", "type",
        "Inter/Geist/Poppins as the first family: the unconsidered default, "
        "not a chosen voice",
        "pick a pairing with a point of view, or use the system stack "
        "deliberately",
        r"font-family\s*:\s*['\"]?(?:Inter|Geist|Poppins|Plus Jakarta Sans|Space Grotesk|DM Sans)\b",
        origin="DESIGN.md 1.1 row 2",
        bad="body { font-family: Inter, sans-serif; }",
        good='body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }',
    ),
    Rule(
        "tw-ai-accent", "WARN", "palette",
        "Tailwind's indigo/violet/purple/fuchsia utilities as the accent",
        "derive the accent from the subject and name it as a token",
        r"\b(?:bg|text|border|ring|from|via|to|fill|stroke|shadow|outline|divide|accent|caret|decoration)"
        r"-(?:indigo|violet|purple|fuchsia)-\d{2,3}\b",
        origin="DESIGN.md 1.1 rows 1 and 7, in utility-class form",
        bad='<button class="bg-indigo-600 text-white">Go</button>',
        good='<button class="bg-emerald-700 text-white">Go</button>',
        fixture_suffix=".html",
    ),
    Rule(
        "emoji-icon", "WARN", "iconography",
        "emoji doing an icon system's job in headings or icon slots",
        "real iconography or none; break the three-cards-with-emoji grid",
        r"<h[1-6][^>]*>[^<]*" + EMOJI + r"|class=[\"'][^\"']*\bicon\b[^\"']*[\"'][^>]*>[^<]*" + EMOJI,
        origin="DESIGN.md 1.1 row 4; 11 (emoji is not an icon system)",
        bad="<h3>\U0001F680 Fast setup</h3>",
        good="<h3>Fast setup</h3>",
        fixture_suffix=".html",
    ),
    Rule(
        "beta-pill", "INFO", "copy",
        "\"New\"/\"Beta\" pill ceremony; a claim with no date behind it",
        "a date or a version number carries the same news honestly",
        r"class=[\"'][^\"']*\b(?:pill|badge|chip|tag)\b[^\"']*[\"'][^>]*>\s*(?:New|Beta)\s*<",
        origin="DESIGN.md 1.1 row 8",
        bad='<span class="badge">Beta</span>',
        good='<span class="badge">v2.1</span>',
        fixture_suffix=".html",
    ),
    # --- computed rules -----------------------------------------------------
    Rule(
        "uniform-radius", "WARN", "surface",
        "everything rounded to the same large radius",
        "vary radius with meaning (DESIGN.md 5's ladder), or choose sharp "
        "corners deliberately",
        computed=True,
        origin="DESIGN.md 1.1 row 6; 5",
        bad=(".a { border-radius: 1rem; } .b { border-radius: 1rem; }\n"
             ".c { border-radius: 1rem; } .d { border-radius: 1rem; }\n"
             ".e { border-radius: 1rem; }"),
        good=(".chip { border-radius: 4px; } .input { border-radius: 6px; }\n"
              ".btn { border-radius: 8px; } .modal { border-radius: 12px; }\n"
              ".pill { border-radius: 999px; }"),
    ),
    Rule(
        "hex-outside-root", "WARN", "tokens",
        "a hardcoded hex outside the token blocks; exactly the value that "
        "cannot flip with the theme",
        "move the color to :root as a token and reference var(--name)",
        computed=True,
        origin="DESIGN.md 3 (all colors live as custom properties on :root)",
        bad=".btn { color: #ff2200; }",
        good=":root { --accent: #ff2200; }\n.btn { color: var(--accent); }",
    ),
    Rule(
        "shadow-census", "INFO", "surface",
        "more distinct box-shadows than a two-shadow system allows",
        "collapse to one at-rest and one elevated shadow (DESIGN.md 5)",
        computed=True,
        origin="DESIGN.md 5 (one soft, one elevated)",
        bad=(".a { box-shadow: 0 1px 2px rgba(0,0,0,.06); }\n"
             ".b { box-shadow: 0 2px 6px rgba(0,0,0,.12); }\n"
             ".c { box-shadow: 0 4px 18px rgba(0,0,0,.08); }\n"
             ".d { box-shadow: 0 8px 30px rgba(0,0,0,.25); }"),
        good=(".card { box-shadow: 0 1px 2px rgba(0,0,0,.06); }\n"
              ".toast { box-shadow: 0 4px 18px rgba(0,0,0,.08); }"),
    ),
    Rule(
        "missing-reduced-motion", "WARN", "motion",
        "keyframe animation with no prefers-reduced-motion escape",
        "add the @media (prefers-reduced-motion: reduce) override",
        computed=True,
        origin="DESIGN.md 5 (respect prefers-reduced-motion)",
        bad=("@keyframes spin { to { transform: rotate(360deg); } }\n"
             ".loader { animation: spin 900ms linear infinite; }"),
        good=("@keyframes spin { to { transform: rotate(360deg); } }\n"
              ".loader { animation: spin 900ms linear infinite; }\n"
              "@media (prefers-reduced-motion: reduce) { .loader { animation: none; } }"),
    ),
    Rule(
        "long-motion", "WARN", "motion",
        "a transition or animation running past the motion budget",
        "300ms is the ceiling (DESIGN.md 5); cut the duration or the effect",
        computed=True,
        origin="DESIGN.md 5 (no motion above 300ms)",
        bad=".panel { transition: transform 500ms ease; }",
        good=".panel { transition: transform 200ms ease; }",
    ),
    Rule(
        "centered-hero", "INFO", "layout",
        "the centered hero template: headline, subtitle, two buttons",
        "lead with the tool or the content; the first screen should do "
        "something",
        computed=True,
        origin="DESIGN.md 1.1 row 3",
        bad=('<section class="hero" style="text-align:center"><h1>Tool</h1>'
             '<p>The subtitle.</p><a class="btn">Get started</a>'
             '<a class="btn">See demo</a></section>'),
        good=('<section class="hero"><table><tr><td>49 filings</td></tr>'
              "</table></section>"),
        fixture_suffix=".html",
    ),
]

RULES_BY_ID: Dict[str, Rule] = {r.id: r for r in RULES}
assert len(RULES_BY_ID) == len(RULES), "duplicate rule id"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
VAGUE_REASONS = {"todo", "tbd", "n/a", "na", "because", "x", "temp", "later", "fix"}


def reason_has_substance(reason: object) -> bool:
    return (isinstance(reason, str) and len(reason.strip()) >= 15
            and reason.strip().lower() not in VAGUE_REASONS)


@dataclass
class Config:
    exclude: List[str] = field(default_factory=list)
    disable: Dict[str, str] = field(default_factory=dict)
    levels: Dict[str, str] = field(default_factory=dict)   # rule id -> level
    allow: List[Dict[str, str]] = field(default_factory=list)
    thresholds: Dict[str, float] = field(default_factory=dict)

    def level_of(self, rule: Rule) -> str:
        return self.levels.get(rule.id, rule.level)

    def threshold(self, key: str) -> float:
        return self.thresholds.get(key, DEFAULTS[key])


def load_config(root: Path) -> Config:
    cfg = Config()
    path = root / ".designcheck.json"
    if not path.is_file():
        return cfg
    data = json.loads(path.read_text(encoding="utf-8"))
    cfg.exclude = list(data.get("exclude", []))
    for rid, reason in (data.get("disable") or {}).items():
        if rid not in RULES_BY_ID:
            sys.exit(f"designcheck: config disables unknown rule '{rid}'")
        if not reason_has_substance(reason):
            sys.exit(f"designcheck: disable['{rid}'] needs a reason with substance")
        cfg.disable[rid] = reason
    for key, section in (("promote", data.get("promote") or {}),
                         ("demote", data.get("demote") or {})):
        for rid, level in section.items():
            if rid not in RULES_BY_ID or level not in LEVELS:
                sys.exit(f"designcheck: bad {key} entry {rid}={level}")
            cfg.levels[rid] = level
    for entry in data.get("allow", []):
        if not reason_has_substance(entry.get("reason")):
            sys.exit("designcheck: every allow entry needs a reason with substance")
        if not entry.get("substring"):
            sys.exit("designcheck: allow entries match by 'substring'")
        cfg.allow.append(entry)
    for key, spec in (data.get("thresholds") or {}).items():
        if key not in DEFAULTS:
            sys.exit(f"designcheck: unknown threshold '{key}'")
        if not reason_has_substance((spec or {}).get("reason")):
            sys.exit(f"designcheck: threshold '{key}' needs a reason with substance")
        cfg.thresholds[key] = float(spec["value"])
    return cfg


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
STYLE_BLOCK = re.compile(r"<style[^>]*>(.*?)</style>", re.I | re.S)
STYLE_ATTR = re.compile(r"style\s*=\s*([\"'])(.*?)\1", re.I | re.S)


def css_contexts(text: str, suffix: str) -> List[Tuple[int, str]]:
    """(line offset, css text) runs. CSS-shaped rules only look here, so an
    inline SVG data plot or a JS string does not get miscounted as a style
    system."""
    if suffix == ".css":
        return [(1, text)]
    if suffix in (".html", ".htm", ".vue", ".svelte"):
        out = []
        for m in STYLE_BLOCK.finditer(text):
            out.append((text.count("\n", 0, m.start(1)) + 1, m.group(1)))
        for m in STYLE_ATTR.finditer(text):
            out.append((text.count("\n", 0, m.start(2)) + 1, m.group(2)))
        return out
    return []


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def snippet_at(text: str, pos: int, width: int = 100) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return text[start:end].strip()[:width]


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------
@dataclass
class Finding:
    rule: str
    level: str
    path: str
    line: int
    snippet: str
    why: str


# `.18s` is a duration: the digit before the point is optional in CSS, and
# requiring it read `.18s` as `18s` and flagged a 180ms transition as 18 seconds.
TIME_TOKEN = re.compile(r"(\d*\.?\d+)\s*(ms|s)\b", re.I)
DECL = re.compile(r"\b(transition|animation)\s*:\s*([^;{}]+)", re.I)
RADIUS_DECL = re.compile(r"border-radius\s*:\s*([^;}]+)", re.I)
ROUNDED_CLASS = re.compile(r"\brounded(?:-(sm|md|lg|xl|2xl|3xl|full))?\b")
SHADOW_DECL = re.compile(r"box-shadow\s*:\s*([^;}]+)", re.I)
TOKEN_BLOCK = re.compile(r"(?::root|\[data-theme[^\]]*\])[^{]*\{[^}]*\}", re.S)
HEX_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b")

ROUNDED_PX = {None: 4, "sm": 2, "md": 6, "lg": 8, "xl": 12, "2xl": 16,
              "3xl": 24, "full": 9999}


def radius_px(value: str) -> Optional[float]:
    value = value.strip().split()[0] if value.strip() else ""
    m = re.match(r"(\d+(?:\.\d+)?)(px|rem|em)?$", value)
    if not m:
        return None
    n = float(m.group(1))
    return n * 16 if m.group(2) in ("rem", "em") else n


def run_computed(rule: Rule, text: str, suffix: str, cfg: Config,
                 path: str) -> List[Finding]:
    out: List[Finding] = []
    contexts = css_contexts(text, suffix)

    def add(line: int, snippet: str) -> None:
        out.append(Finding(rule.id, cfg.level_of(rule), path, line,
                           snippet[:100], rule.why))

    if rule.id == "uniform-radius":
        values: List[Tuple[int, float, str]] = []
        for off, css in contexts:
            for m in RADIUS_DECL.finditer(css):
                px = radius_px(m.group(1))
                if px is not None:
                    values.append((off + css.count("\n", 0, m.start()),
                                   px, m.group(0)))
        for m in ROUNDED_CLASS.finditer(text):
            values.append((line_of(text, m.start()),
                           ROUNDED_PX[m.group(1)], m.group(0)))
        if len(values) >= cfg.threshold("radius_census_min_uses"):
            distinct = {v for _, v, _ in values}
            if len(distinct) == 1 and distinct.pop() >= cfg.threshold("radius_uniform_min_px"):
                line, _, snip = values[0]
                add(line, f"{len(values)} radius uses, all '{snip}'")

    elif rule.id == "hex-outside-root":
        for off, css in contexts:
            stripped = TOKEN_BLOCK.sub(lambda m: "\n" * m.group(0).count("\n"), css)
            for m in HEX_LITERAL.finditer(stripped):
                add(off + stripped.count("\n", 0, m.start()),
                    snippet_at(stripped, m.start()))

    elif rule.id == "shadow-census":
        shadows: Dict[str, Tuple[int, str]] = {}
        for off, css in contexts:
            for m in SHADOW_DECL.finditer(css):
                norm = re.sub(r"\s+", " ", m.group(1).strip().lower())
                if norm not in ("none", "unset", "inherit"):
                    shadows.setdefault(norm, (off + css.count("\n", 0, m.start()),
                                              m.group(0)))
        if len(shadows) > cfg.threshold("shadow_distinct_max"):
            line, snip = next(iter(shadows.values()))
            add(line, f"{len(shadows)} distinct box-shadows; first: {snip[:60]}")

    elif rule.id == "missing-reduced-motion":
        for off, css in contexts:
            if re.search(r"@keyframes|animation\s*:", css, re.I) and \
                    "prefers-reduced-motion" not in css:
                m = re.search(r"@keyframes|animation\s*:", css, re.I)
                add(off + css.count("\n", 0, m.start()), snippet_at(css, m.start()))
                break  # once per file is the signal

    elif rule.id == "long-motion":
        for off, css in contexts:
            for decl in DECL.finditer(css):
                # Every duration in the declaration, not the first: a list of
                # transitions is only as fast as its slowest member.
                slowest = max((float(t.group(1)) * (1000 if t.group(2).lower() == "s" else 1)
                               for t in TIME_TOKEN.finditer(decl.group(2))), default=0.0)
                if slowest > cfg.threshold("motion_max_ms"):
                    add(off + css.count("\n", 0, decl.start()),
                        snippet_at(css, decl.start()))

    elif rule.id == "centered-hero":
        if suffix not in (".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte"):
            return out
        hero = re.search(r"class=[\"'][^\"']*\bhero\b[^\"']*[\"']", text, re.I)
        centered = re.search(r"text-align\s*:\s*center|\btext-center\b", text, re.I)
        ctas = re.findall(r"class=[\"'][^\"']*\b(?:btn|button|cta)\b[^\"']*[\"']", text, re.I)
        if hero and centered and len(ctas) >= cfg.threshold("hero_min_ctas"):
            add(line_of(text, hero.start()), snippet_at(text, hero.start()))

    return out


def scan_text(text: str, suffix: str, cfg: Config, path: str,
              only: Optional[set] = None) -> Tuple[List[Finding], int]:
    """Scan one file's content. Returns (findings, exempted count)."""
    findings: List[Finding] = []
    exempted = 0
    for rule in RULES:
        if only and rule.id not in only:
            continue
        if rule.id in cfg.disable:
            continue
        if rule.computed:
            found = run_computed(rule, text, suffix, cfg, path)
        else:
            found = []
            rx = rule.compiled()
            for m in rx.finditer(text):
                found.append(Finding(rule.id, cfg.level_of(rule), path,
                                     line_of(text, m.start()),
                                     snippet_at(text, m.start()), rule.why))
        for f in found:
            if any(a["substring"] in f.snippet for a in cfg.allow):
                exempted += 1
            else:
                findings.append(f)
    return findings, exempted


# ---------------------------------------------------------------------------
# File walking
# ---------------------------------------------------------------------------
def collect_files(paths: Sequence[str], cfg: Config) -> List[Path]:
    out: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            if p.suffix.lower() in SUPPORTED_SUFFIXES:
                out.append(p)
            continue
        if not p.is_dir():
            sys.exit(f"designcheck: no such path: {raw}")
        for f in sorted(p.rglob("*")):
            if not f.is_file() or f.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            parts = set(f.parts)
            if parts & DEFAULT_EXCLUDE_PARTS:
                continue
            rel = str(f)
            if any(ex in rel for ex in cfg.exclude):
                continue
            if f.stat().st_size > MAX_FILE_BYTES:
                continue
            out.append(f)
    return out


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------
def selftest() -> int:
    """Every rule fires on its bad fixture and stays quiet on its good one."""
    cfg = Config()
    failures = []
    for rule in RULES:
        if not rule.bad or not rule.good:
            failures.append(f"{rule.id}: missing fixture (bad and good are required)")
            continue
        bad_hits, _ = scan_text(rule.bad, rule.fixture_suffix, cfg,
                                "<bad>", only={rule.id})
        good_hits, _ = scan_text(rule.good, rule.fixture_suffix, cfg,
                                 "<good>", only={rule.id})
        if not bad_hits:
            failures.append(f"{rule.id}: known-bad fixture did not fire")
        if good_hits:
            failures.append(f"{rule.id}: known-good fixture fired: "
                            f"{good_hits[0].snippet!r}")
    if failures:
        print("designcheck --selftest: FAIL")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"designcheck --selftest: OK ({len(RULES)} rules, "
          f"{len(RULES) * 2} fixtures)")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="designcheck", add_help=True)
    ap.add_argument("paths", nargs="*", help="files or directories to scan")
    ap.add_argument("--fail-on", default="FAIL", choices=list(LEVELS) + ["NEVER"])
    ap.add_argument("--only", help="comma-separated rule ids")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--explain", metavar="RULE")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--calibrate", action="store_true",
                    help="first-run triage: group findings by rule, no gate")
    ap.add_argument("--json", metavar="OUT", help="also write findings as JSON")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.list:
        for r in RULES:
            kind = "computed" if r.computed else "pattern"
            print(f"{r.level:4} {r.id:24} {kind:8} {r.why}")
        return 0
    if args.explain:
        r = RULES_BY_ID.get(args.explain)
        if not r:
            sys.exit(f"designcheck: unknown rule '{args.explain}'")
        print(f"{r.id} [{r.level}] ({r.family})\nwhy: {r.why}\nfix: {r.fix}\n"
              f"origin: {r.origin}\nbad:  {r.bad}\ngood: {r.good}")
        return 0
    if not args.paths:
        ap.print_usage()
        return 2

    root = Path(args.paths[0])
    cfg = load_config(root if root.is_dir() else root.parent)
    only = set(args.only.split(",")) if args.only else None
    if only:
        unknown = only - set(RULES_BY_ID)
        if unknown:
            sys.exit(f"designcheck: unknown rule(s): {', '.join(sorted(unknown))}")

    files = collect_files(args.paths, cfg)
    findings: List[Finding] = []
    exempted = 0
    total_bytes = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"designcheck: cannot read {f}: {e}", file=sys.stderr)
            continue
        total_bytes += len(text)
        found, ex = scan_text(text, f.suffix.lower(), cfg, str(f), only)
        findings.extend(found)
        exempted += ex

    if not files:
        print("designcheck: nothing scanned (no supported files under the "
              "given paths) — that is an error, not a pass", file=sys.stderr)
        return 2

    findings.sort(key=lambda x: (-LEVEL_RANK[x.level], x.path, x.line))
    if args.calibrate:
        counts = Counter((f.rule, f.level) for f in findings)
        print(f"designcheck --calibrate over {len(files)} files:")
        for (rid, level), n in counts.most_common():
            print(f"  {n:4d}  {level:4} {rid}")
        print("triage each rule: fix now / allow with a reason / disable with "
              "a reason. Never widen the allowlist until the output is empty.")
        return 0

    for f in findings:
        print(f"{f.level:4} {f.rule:24} {f.path}:{f.line}  {f.snippet}")

    by_level = Counter(f.level for f in findings)
    print(f"designcheck: scanned {len(files)} files ({total_bytes:,} bytes); "
          f"{by_level.get('FAIL', 0)} FAIL, {by_level.get('WARN', 0)} WARN, "
          f"{by_level.get('INFO', 0)} INFO; {exempted} exempted by allowlist; "
          f"{len(cfg.disable)} rules disabled")

    if args.json:
        Path(args.json).write_text(json.dumps(
            [f.__dict__ for f in findings], indent=1), encoding="utf-8")

    gate = LEVEL_RANK.get(args.fail_on, 99)
    if any(LEVEL_RANK[f.level] >= gate for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
