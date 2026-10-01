"""Shared bill-text helpers: locating a quote and splitting a section into paragraphs.

The build and the quote checker both import these, so a cite shown on the site
and a cite checked by the validator come from the same code.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECTIONS = ROOT / "data/bill/sections.json"

WS_RE = re.compile(r"\s+")


def norm(text: str) -> str:
    """Collapse whitespace. Quote marks and dashes are compared exactly."""
    return WS_RE.sub(" ", text).strip()


def load_sections() -> dict:
    return json.loads(SECTIONS.read_text(encoding="utf-8"))


def flat_index(lines: list[list]) -> tuple[str, list[int]]:
    """Join printed lines with single spaces; return the string and each line's start offset."""
    parts: list[str] = []
    starts: list[int] = []
    pos = 0
    for _, _, text in lines:
        t = norm(text)
        starts.append(pos)
        parts.append(t)
        pos += len(t) + 1
    return " ".join(parts), starts


def locate(lines: list[list], quote: str) -> dict | None:
    """Find a verbatim quote in a section. Returns its page and line span, or None."""
    flat, starts = flat_index(lines)
    q = norm(quote)
    if not q:
        return None
    hits = [m.start() for m in re.finditer(re.escape(q), flat)
            if not (m.start() and (flat[m.start()-1].isalnum() or
                    re.search(r"[0-9][,.]$", flat[:m.start()])))
            and not (m.end() < len(flat) and (flat[m.end()].isalnum() or
                     re.match(r"[,.][0-9]", flat[m.end():])))]
    if not hits:
        return None
    at = hits[0]
    end = at + len(q) - 1

    def line_at(offset: int) -> int:
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo

    a, b = line_at(at), line_at(end)
    return {"p1": lines[a][0], "l1": lines[a][1], "p2": lines[b][0], "l2": lines[b][1], "count": len(hits)}


ENUM_RE = re.compile(r"^“?\((?P<tok>[a-z]{1,2}|[A-Z]{1,2}|\d{1,2}|[ivxl]{2,8}|[IVXL]{2,8})\)")
SEC_START_RE = re.compile(r"^“?(SEC\.|SECTION|§)\s")
TERMINAL_RE = re.compile(r"([.;:—”]|[;,] and|[;,] or)$")


def enum_level(tok: str, last: dict) -> int:
    """Indent level for a bill enumerator: (a) 1, (1) 2, (A) 3, (i) 4, (I) 5, (aa) 6, (AA) 7."""
    if tok.isdigit():
        return 2
    if tok.islower():
        if len(tok) == 1:
            if tok in "ivx" and last.get(1) != chr(ord(tok) - 1):
                return 4
            return 1
        if len(set(tok)) == 1 and tok[0] not in "ivx":
            return 6
        if len(set(tok)) == 1 and last.get(6) == chr(ord(tok[0]) - 1) * 2:
            return 6
        return 4
    if len(tok) == 2 and len(set(tok)) == 1 and (last.get(3) == "Z" or last.get(3) == chr(ord(tok[0]) - 1) * 2):
        return 3
    if len(tok) == 1:
        if tok in "IVX" and last.get(3) != chr(ord(tok) - 1):
            return 5
        return 3
    if len(set(tok)) == 1 and tok[0] not in "IVX":
        return 7
    return 5


def paragraphs(lines: list[list]) -> list[list]:
    """Group printed lines into paragraphs: [page, line, level, text].

    A paragraph starts at a line that opens with an enumerator or a section
    heading, when the line before it ended a clause. A cross-reference that
    merely wraps to the start of a line ('subsection' / '(a)(2)...') does not
    start one, because the line before it does not end a clause.
    """
    out: list[list] = []
    last: dict = {}
    prev_text = ""
    level = 0
    for page, line_no, text in lines:
        t = norm(text)
        if not t:
            continue
        m = ENUM_RE.match(t)
        sec = SEC_START_RE.match(t)
        opens_quote = t.startswith("“")
        prev_ends = (not out) or bool(TERMINAL_RE.search(out[-1][3])) or bool(SEC_START_RE.match(out[-1][3]))
        if (not out) or (prev_ends and (m or sec or opens_quote)):
            if sec:
                level = 0
            elif m:
                if prev_text.endswith((":", "—")):
                    last.pop(1, None)
                    last.pop(3, None)
                level = enum_level(m.group("tok"), last)
                tok = m.group("tok")
                last[level] = tok
                for deeper in [k for k in last if k > level]:
                    del last[deeper]
            elif out:
                level = max(1, min(level, 2))
            out.append([page, line_no, level, t])
        else:
            out[-1][3] += " " + t
        prev_text = t
    return out


def review_fingerprint() -> str:
    """Bind summary-check coverage to its complete set of input documents."""
    paths = ["bill/sections.json", "bill/analysis.json", "compare.json",
             "prior_bills/speed_act_hr4776_eh.json", "prior_bills/epra_2024_s4753_rs.json"]
    h = hashlib.sha256()
    for name in paths:
        h.update(name.encode())
        h.update((ROOT / "data" / name).read_bytes())
    return h.hexdigest()
