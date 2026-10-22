#!/usr/bin/env python3
"""Model review of what the deterministic slop checkers did not catch.

slop_writing.py and slop_design.py call this after their own pass. It picks
the chunks no rule flagged but that still look suspicious (they score on the
excess-vocabulary lexicon and punctuation fingerprints mined by
slop_patterns.py), asks a Sonnet run to name any tell in them, keeps only spans
that appear verbatim in the input, and appends them to
tells/<kind>-candidates.jsonl with status "proposed". A person promotes a
candidate by moving it into tells/<kind>.jsonl (writing) or turning it into a
rule; until then it never changes a verdict.

Off when: --no-review, SLOP_REVIEW=0, CI is set, or `claude` is not on PATH
(the last one says so on stderr rather than skipping silently). Each chunk is
reviewed once: its hash goes to tells/reviewed-hashes.txt.

Direct use:
    python3 tools/slop_review.py --list writing      # show proposed candidates
    python3 tools/slop_review.py --run queue.json    # review a saved queue
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

TELLS_DIR = Path(os.environ.get("SLOP_TELLS_DIR") or Path(__file__).resolve().parent.parent / "tells")
HASHES = "reviewed-hashes.txt"
LEXICON = "lexicon.json"
MAX_ITEMS = 15
MAX_CHARS = 14_000
TIMEOUT_S = 240

PUNCT_FEATURES = {
    "spaced em dash": re.compile(r"\s—\s"),
    "middle-dot list": re.compile(r"\S\s·\s\S"),
    "arrow": re.compile(r"→|->"),
    "colon label": re.compile(r"^\s*\**[A-Z][\w ]{1,24}\**:\s", re.M),
}

PROMPTS = {
    "writing": """You review prose for AI-writing tells that a deterministic checker missed.
The checker already knows these families: LLM register words, hedges, throat-clearing openers,
antithesis ("not X, but Y"), corrective negation, tricolons, staccato fragments, significance
tails (", highlighting ..."), copula avoidance ("serves as"), aspirational slogans, vague
attribution, self-reference to the page or the work, progress-report vapor.

Report only a span a careful human editor would cut or rewrite because it reads generated:
stock phrasing, a skeleton that fits any subject, empty emphasis, narration of the interface,
commentary on the data instead of the data. Do not report plain technical prose, quotations,
names, or numbers. An empty list is the right answer for clean text.""",
    "design": """You review a UI's markup and CSS census for generated-design tells that a
deterministic checker missed. The checker already knows: violet/indigo gradients, gradient text,
glassmorphism, Inter/Geist/Poppins defaults, uniform radius, centered hero, decorative eyebrows,
sparkle/emoji icons, "Made with love" footers, cream-serif-terracotta, acid accent on near-black,
middle-dot meta strings, arrows on links, 01/02/03 markers on non-sequences.

Report only a concrete snippet (a class, a declaration, a short run of markup or text) that
reads like a template default rather than a choice. An empty list is the right answer.""",
}

SCHEMA = """Return JSON only, no prose, in this shape:
{"findings": [{"id": "<item id>", "span": "<exact substring of that item>",
  "family": "<short family name>", "why": "<20 words or fewer>",
  "rule_idea": "<a regex or a one-line test that would catch this and its siblings>"}]}"""


def disabled_reason(no_review: bool = False) -> Optional[str]:
    if no_review:
        return "--no-review"
    if os.environ.get("SLOP_REVIEW", "1").strip().lower() in {"0", "off", "false", "no"}:
        return "SLOP_REVIEW=0"
    if os.environ.get("CI"):
        return "CI"
    if not shutil.which("claude"):
        return "claude CLI not on PATH"
    return None


def chunk_hash(text: str) -> str:
    return hashlib.sha1(re.sub(r"\s+", " ", text).strip().lower().encode()).hexdigest()[:16]


def _read_hashes(tells_dir: Path) -> set:
    p = tells_dir / HASHES
    return set(p.read_text().split()) if p.exists() else set()


def load_lexicon(tells_dir: Path, kind: str) -> Dict[str, float]:
    p = tells_dir / LEXICON
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {w: float(s) for w, s in (data.get(kind) or {}).items()}


def score(text: str, lexicon: Dict[str, float]) -> float:
    words = re.findall(r"[a-z][a-z'-]+", text.lower())
    s = sum(lexicon.get(w, 0.0) for w in words)
    s += sum(1.0 for rx in PUNCT_FEATURES.values() if rx.search(text))
    # A small floor so prose still gets sampled before slop_patterns has mined a lexicon.
    return 0.05 + s / max(1.0, len(words) ** 0.5)


def select(items: Sequence[dict], kind: str, tells_dir: Path = TELLS_DIR,
           limit: int = MAX_ITEMS) -> List[dict]:
    """Highest-scoring unreviewed items, inside the character budget."""
    seen = _read_hashes(tells_dir)
    lex = load_lexicon(tells_dir, kind)
    scored = []
    for it in items:
        h = chunk_hash(it["text"])
        if h in seen or len(it["text"]) < 40:
            continue
        sc = score(it["text"], lex)
        if sc > 0:
            scored.append((sc, h, it))
    scored.sort(key=lambda t: -t[0])
    out, budget, hashes = [], MAX_CHARS, set()
    for sc, h, it in scored:
        if h in hashes or len(out) >= limit or len(it["text"]) > budget:
            continue
        hashes.add(h)
        budget -= len(it["text"])
        out.append(dict(it, hash=h, score=round(sc, 3)))
    return out


def build_prompt(kind: str, items: Sequence[dict], census: str = "") -> str:
    body = "\n\n".join("[{}] ({}:{})\n{}".format(i, it["source"], it["loc"], it["text"])
                       for i, it in enumerate(items))
    extra = "\n\nCSS census:\n" + census if census else ""
    return "{}\n\n{}{}\n\nItems:\n\n{}".format(PROMPTS[kind], SCHEMA, extra, body)


def call_model(prompt: str, model: str = "sonnet") -> str:
    # Run from an empty directory so no project CLAUDE.md rides along on every call.
    with tempfile.TemporaryDirectory() as d:
        proc = subprocess.run(
            ["claude", "-p", "--model", model, "--output-format", "json",
             "--no-session-persistence", "--tools", "", "--strict-mcp-config"],
            input=prompt, capture_output=True, text=True, cwd=d, timeout=TIMEOUT_S)
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        out = {"is_error": True, "result": (proc.stdout + proc.stderr).strip()[:300]}
    if proc.returncode != 0 or out.get("is_error"):
        raise RuntimeError("claude exited {}: {}".format(proc.returncode, out.get("result", "")))
    return out.get("result", "")


def parse_findings(raw: str, items: Sequence[dict]) -> List[dict]:
    """Keep only findings whose span is verbatim in the item it names."""
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("model reply held no JSON object: {!r}".format(raw[:200]))
    found = json.loads(m.group()).get("findings") or []
    kept = []
    for f in found:
        try:
            it = items[int(f.get("id"))]
        except (TypeError, ValueError, IndexError):
            continue
        span = (f.get("span") or "").strip()
        if span and span in it["text"]:
            kept.append({"span": span, "family": f.get("family", ""), "why": f.get("why", ""),
                         "rule_idea": f.get("rule_idea", ""), "source": it["source"],
                         "loc": it["loc"], "hash": it["hash"]})
    return kept


def record(kind: str, findings: Sequence[dict], items: Sequence[dict],
           tells_dir: Path = TELLS_DIR, model: str = "sonnet") -> Path:
    tells_dir.mkdir(parents=True, exist_ok=True)
    out = tells_dir / "{}-candidates.jsonl".format(kind)
    today = time.strftime("%Y-%m-%d")
    with out.open("a") as fh:
        for f in findings:
            fh.write(json.dumps(dict(f, kind=kind, by="review:" + model, date=today,
                                     status="proposed"), ensure_ascii=False) + "\n")
    with (tells_dir / HASHES).open("a") as fh:
        fh.write("".join(it["hash"] + "\n" for it in items))
    return out


def save_queue(kind: str, items: Sequence[dict], census: str, model: str,
               tells_dir: Path = TELLS_DIR) -> Path:
    qdir = tells_dir / "review-queue"
    qdir.mkdir(parents=True, exist_ok=True)
    q = qdir / "{}-{}.json".format(kind, time.strftime("%Y%m%d-%H%M%S"))
    q.write_text(json.dumps({"kind": kind, "items": list(items), "census": census, "model": model}))
    return q


def review(kind: str, items: Sequence[dict], census: str = "", no_review: bool = False,
           mode: str = "on", tells_dir: Path = TELLS_DIR, model: str = "sonnet") -> int:
    """Entry point for the checkers. Returns the number of new candidates (0 in
    background mode). Never changes the checker's exit code."""
    why_off = disabled_reason(no_review)
    if why_off:
        if why_off.startswith("claude"):
            print("review: skipped ({})".format(why_off), file=sys.stderr)
        return 0
    picked = select(items, kind, tells_dir)
    if not picked:
        print("review: 0 unflagged chunks scored as suspicious; nothing sent")
        return 0
    if mode == "background":
        q = save_queue(kind, picked, census, model, tells_dir)
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--run", str(q)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print("review: {} chunk(s) sent to {} in the background; results land in "
              "tells/{}-candidates.jsonl".format(len(picked), model, kind))
        return 0
    print("review: sending {} unflagged chunk(s) to {} ...".format(len(picked), model))
    try:
        findings = parse_findings(call_model(build_prompt(kind, picked, census), model), picked)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        q = save_queue(kind, picked, census, model, tells_dir)
        print("review: FAILED ({}).\n  {} chunk(s) saved to {}; rerun with: python3 {} --run {}"
              .format(exc, len(picked), q, Path(__file__).resolve(), q), file=sys.stderr)
        return 0
    out = record(kind, findings, picked, tells_dir, model)
    print("review: {} new candidate tell(s) from {} chunk(s) -> {}".format(
        len(findings), len(picked), out))
    for f in findings:
        print("  NEW  {:<14} {}:{}  {!r}\n       {}".format(
            f["family"][:14], f["source"], f["loc"], f["span"][:90], f["why"]))
    return len(findings)


def list_candidates(kind: str, tells_dir: Path = TELLS_DIR) -> int:
    p = tells_dir / "{}-candidates.jsonl".format(kind)
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []
    rows = [r for r in rows if r.get("status") == "proposed"]
    for r in rows:
        print("{}  {:<14} {!r}  ({}:{})".format(r["date"], r["family"][:14], r["span"][:80],
                                                r["source"], r["loc"]))
    print("{} proposed {} candidate(s) in {}".format(len(rows), kind, p))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", metavar="KIND", choices=sorted(PROMPTS))
    ap.add_argument("--run", metavar="QUEUE", help="review a queue file written in background mode")
    args = ap.parse_args(argv)
    if args.list:
        return list_candidates(args.list)
    if args.run:
        q = Path(args.run)
        data = json.loads(q.read_text())
        items, kind, model = data["items"], data["kind"], data.get("model", "sonnet")
        try:
            findings = parse_findings(call_model(build_prompt(kind, items, data.get("census", "")),
                                                 model), items)
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            print("review: FAILED ({}); queue kept at {}".format(exc, q), file=sys.stderr)
            return 1
        record(kind, findings, items, q.parent.parent, model)
        q.unlink()
        print("review: {} new candidate(s) from {}".format(len(findings), q.name))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
