"""Compare the September 30 bill with the November 7 substitute, section by section.

Input:  data/bill/sections.json              (introduced text, site/bill.pdf)
        data/bill/substitute_sections.json   (substitute, site/substitute.pdf)
Output: data/bill/substitute_diff.json

Sections are matched by number and heading in three passes: same number and
heading, then same heading under a new number (moved), then same number under
a new heading (renamed). What is left over is new or dropped.

Each edited section carries word-level hunks. A hunk keeps the struck and
inserted words, a few words of context on either side, and the page and line
where it sits in each PDF, so every change on the site cites both texts.

Standard library only. Deterministic. `--dump` prints the hunks as plain text
for reading.
"""
from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLD = ROOT / "data/bill/sections.json"
NEW = ROOT / "data/bill/substitute_sections.json"
OUT = ROOT / "data/bill/substitute_diff.json"

CONTEXT = 8  # words of unchanged text shown on each side of a hunk
BRIDGE = 4   # unchanged runs this short join the hunks on either side


def words(lines: list[list]) -> list[tuple[str, int, int]]:
    """Every word of a section with the page and printed line it sits on."""
    out = []
    for page, line, text in lines:
        for w in text.split():
            out.append((w, page, line or 0))
    return out


def match_sections(old: list[dict], new: list[dict]) -> list[tuple[dict | None, dict | None]]:
    key = lambda s: s["heading"].lower()
    pairs: dict[str, str] = {}
    free_new = {s["number"]: s for s in new}
    left = []
    for s in old:
        t = free_new.get(s["number"])
        if t and key(t) == key(s):
            pairs[s["number"]] = t["number"]
            del free_new[t["number"]]
        else:
            left.append(s)
    still = []
    for s in left:
        hits = [t for t in free_new.values() if key(t) == key(s)]
        if len(hits) == 1:
            pairs[s["number"]] = hits[0]["number"]
            del free_new[hits[0]["number"]]
        else:
            still.append(s)
    for s in still:
        t = free_new.get(s["number"])
        if t:
            pairs[s["number"]] = t["number"]
            del free_new[t["number"]]
    new_by = {s["number"]: s for s in new}
    out: list[tuple[dict | None, dict | None]] = []
    for s in old:
        out.append((s, new_by.get(pairs[s["number"]]) if s["number"] in pairs else None))
    for s in new:
        if s["number"] in free_new:
            out.append((None, s))
    return out


def hunks(a: list[tuple[str, int, int]], b: list[tuple[str, int, int]]) -> list[dict]:
    sm = difflib.SequenceMatcher(None, [w for w, _, _ in a], [w for w, _, _ in b], autojunk=False)
    ops = [op for op in sm.get_opcodes()]
    # Join changes separated by a short unchanged run, so one edit reads as one hunk.
    groups: list[list[tuple]] = []
    for op in ops:
        if op[0] == "equal":
            continue
        if groups:
            prev = groups[-1][-1]
            gap = op[1] - prev[2]
            if gap <= BRIDGE:
                groups[-1].append(op)
                continue
        groups.append([op])
    out = []
    for k, g in enumerate(groups):
        i1, i2 = g[0][1], g[-1][2]
        # Context stops at a neighboring hunk, so it never quotes words that hunk strikes.
        lo = max(i1 - CONTEXT, groups[k - 1][-1][2] if k else 0)
        hi = min(i2 + CONTEXT, groups[k + 1][0][1] if k + 1 < len(groups) else len(a))
        j1, j2 = g[0][3], g[-1][4]
        old_words = [w for w, _, _ in a[i1:i2]]
        new_words = [w for w, _, _ in b[j1:j2]]
        at_a = a[i1] if i1 < len(a) else a[-1]
        at_b = b[j1] if j1 < len(b) else b[-1]
        out.append({
            "before": " ".join(w for w, _, _ in a[lo:i1]),
            "del": " ".join(old_words),
            "ins": " ".join(new_words),
            "after": " ".join(w for w, _, _ in a[i2:hi]),
            "a": [at_a[1], at_a[2]],
            "b": [at_b[1], at_b[2]],
        })
    return out


def entry(old: dict | None, new: dict | None) -> dict:
    if old and new:
        hs = hunks(words(old["lines"]), words(new["lines"]))
        if old["number"] != new["number"]:
            status = "moved"
        elif not hs and old["heading"] == new["heading"]:
            status = "unchanged"
        else:
            status = "edited"
    else:
        hs = []
        status = "new" if new else "dropped"
    base = new or old
    rec = {
        # A dropped section's number can be reused in the substitute (2242), so its id says so.
        "id": base["number"] if new else base["number"] + "-dropped",
        "n": base["number"],
        "h": base["heading"],
        "status": status,
        "div": base["division"], "divh": base["division_heading"],
        "ti": base["title"], "tih": base["title_heading"],
        "su": base["subtitle"], "suh": base["subtitle_heading"],
    }
    if old:
        rec["old"] = {"n": old["number"], "h": old["heading"], "p1": old["page_start"], "l1": old["line_start"], "p2": old["page_end"], "words": old["words"]}
    if new:
        rec["new"] = {"n": new["number"], "h": new["heading"], "p1": new["page_start"], "l1": new["line_start"], "p2": new["page_end"], "words": new["words"]}
    if hs:
        rec["hunks"] = hs
        rec["struck"] = sum(len(h["del"].split()) for h in hs)
        rec["inserted"] = sum(len(h["ins"].split()) for h in hs)
    return rec


def build() -> dict:
    old_doc = json.loads(OLD.read_text(encoding="utf-8"))
    new_doc = json.loads(NEW.read_text(encoding="utf-8"))
    rows = [entry(o, n) for o, n in match_sections(old_doc["sections"], new_doc["sections"])]
    # Order rows the way the substitute prints them; a dropped section sits where it was.
    order = {s["number"]: i for i, s in enumerate(new_doc["sections"])}
    old_order = {s["number"]: i for i, s in enumerate(old_doc["sections"])}

    def pos(r: dict) -> float:
        if "new" in r:
            return order[r["new"]["n"]]
        # Place a dropped section right after the new position of the section before it.
        prev = [o for o in old_doc["sections"] if old_order[o["number"]] < old_order[r["old"]["n"]]]
        for o in reversed(prev):
            m = next((x for x in rows if x.get("old", {}).get("n") == o["number"] and "new" in x), None)
            if m:
                return order[m["new"]["n"]] + 0.5
        return -1
    # Keys first: list.sort empties the list while it runs, so pos() could not see the rows.
    keys = {id(r): pos(r) for r in rows}
    rows.sort(key=lambda r: keys[id(r)])
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {
        "old": {k: old_doc["meta"][k] for k in ("draft_id", "released", "pages", "source_pdf", "total_words")} | {"sections": len(old_doc["sections"])},
        "new": {k: new_doc["meta"][k] for k in ("draft_id", "released", "pages", "source_pdf", "total_words", "kind", "press_release")} | {"sections": len(new_doc["sections"])},
        "counts": counts,
        "rows": rows,
    }


def dump(doc: dict, only: set[str] | None = None) -> str:
    out = []
    for r in doc["rows"]:
        if only and r["n"] not in only and r["id"] not in only:
            continue
        o, n = r.get("old"), r.get("new")
        out.append(f"### {r['status'].upper()} Sec. {r['n']} {r['h']}" + (f" (was Sec. {o['n']} {o['h']})" if o and (o['n'] != r['n'] or o['h'] != r['h']) else ""))
        for h in r.get("hunks", []):
            out.append(f"- [old p{h['a'][0]}:{h['a'][1]} / new p{h['b'][0]}:{h['b'][1]}] …{h['before']} [-{h['del']}-] {{+{h['ins']}+}} {h['after']}…")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    doc = build()
    if "--dump" in argv:
        only = set(argv[argv.index("--dump") + 1:]) or None
        sys.stdout.write(dump(doc, only))
        return 0
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("diff_bill: " + ", ".join(f"{v} {k}" for k, v in sorted(doc["counts"].items())) + f" -> {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
