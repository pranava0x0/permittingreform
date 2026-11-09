"""The Amendments view: the November 7 substitute against the September 30 text,
other amendments filed or announced, and who has said what about them.

Inputs:
  data/bill/substitute_diff.json   written by tools/diff_bill.py
  data/bill/substitute_notes.json  one or more factual change notes per changed
                                   section, each carrying a verbatim span from the
                                   text it describes (new or old)
  data/amendments.json             floor amendments, reactions and the vote, each
                                   with a source and a verbatim quote
  site/substitute.pdf              must match the parsed substitute text

build(errors) returns the browser payload; build.py writes it and fails on errors.
Standard library only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import billtext

ROOT = billtext.ROOT
DATA = ROOT / "data"
SUB_PDF = "substitute.pdf"
STATUSES = ("edited", "new", "dropped", "moved", "unchanged")
KINDS = ("substantive", "technical")
STANCES = ("supports", "opposes", "mixed", "undecided", "comments")
# Headings for each stance group; the interactive view uses the same words (AM_STANCE in site/app.js).
STANCE_LABELS = {"supports": "Support", "opposes": "Oppose", "mixed": "Mixed", "undecided": "Undecided", "comments": "Comment on a section"}
FLOOR_STATUS = ("announced", "submitted", "filed", "pending", "adopted", "rejected", "withdrawn", "tabled")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def cite(loc: dict) -> list:
    return [loc["p1"], loc["l1"], loc["p2"], loc["l2"]]


def build(errors: list[str]) -> dict | None:
    diff_path = DATA / "bill/substitute_diff.json"
    if not diff_path.exists():
        return None
    diff = load(diff_path)
    notes = load(DATA / "bill/substitute_notes.json")
    old_by = {s["number"]: s for s in billtext.load_sections()["sections"]}
    sub_doc = load(DATA / "bill/substitute_sections.json")
    new_by = {s["number"]: s for s in sub_doc["sections"]}
    pdf = ROOT / "site" / SUB_PDF
    if not pdf.exists() or hashlib.sha256(pdf.read_bytes()).hexdigest() != sub_doc["meta"]["pdf_sha256"]:
        errors.append("amendments: site/substitute.pdf differs from the parsed substitute; run tools/parse_bill.py --version substitute")
    if diff["new"]["total_words"] != sub_doc["meta"]["total_words"]:
        errors.append("amendments: substitute_diff.json is stale; run tools/diff_bill.py")

    ids = {r["id"] for r in diff["rows"]}
    for key in notes:
        if key not in ids:
            errors.append(f"amendments: note {key} matches no section in the diff")

    rows = []
    for r in diff["rows"]:
        if r["status"] not in STATUSES:
            errors.append(f"amendments: {r['id']} has unknown status {r['status']!r}")
        row = {k: r[k] for k in ("id", "n", "h", "status", "div", "divh", "ti", "tih") if k in r}
        for side in ("old", "new"):
            if side in r:
                row[side] = r[side]
        note = notes.get(r["id"])
        if r["status"] == "unchanged":
            rows.append(row)
            continue
        if not note or not note.get("points"):
            errors.append(f"amendments: {r['id']} ({r['status']}) has no change note")
            note = {"kind": "substantive", "points": []}
        if note.get("kind") not in KINDS:
            errors.append(f"amendments: {r['id']} kind must be one of {KINDS}")
        points = []
        for i, p in enumerate(note["points"], 1):
            side = "new" if "new" in p else "old" if "old" in p else None
            sec = (new_by if side == "new" else old_by).get(r[side]["n"]) if side and side in r else None
            loc = billtext.locate(sec["lines"], p[side]) if sec else None
            if not loc:
                errors.append(f"amendments: {r['id']} point {i}: passage not in the {side or '?'} text: {str(p.get(side))[:60]!r}")
                continue
            if loc["count"] != 1:
                errors.append(f"amendments: {r['id']} point {i}: passage matches {loc['count']} times; lengthen it")
            points.append({"t": p["t"], "side": side, "c": cite(loc)})
        row["kind"] = note.get("kind")
        row["points"] = points
        if r.get("hunks"):
            row["hunks"] = r["hunks"]
            row["struck"], row["inserted"] = r["struck"], r["inserted"]
        # A new or dropped section's redline is its whole text, inserted or struck.
        if r["status"] == "new":
            row["text"] = billtext.paragraphs(new_by[r["n"]]["lines"])
        elif r["status"] == "dropped":
            row["old_text"] = billtext.paragraphs(old_by[r["old"]["n"]]["lines"])
        rows.append(row)

    extra = load(DATA / "amendments.json")
    by_id = {r["id"] for r in rows}
    for where, items in (("floor", extra["floor"]), ("reactions", extra["reactions"])):
        for i, it in enumerate(items):
            label = f"amendments {where} {it.get('id', i)}"
            if not it.get("sources"):
                errors.append(f"{label}: no source")
            for s in it.get("sources", []):
                if not str(s.get("url", "")).startswith("http") or not s.get("quote"):
                    errors.append(f"{label}: each source needs a url and a verbatim quote")
            for n in it.get("sections", []):
                if n not in by_id:
                    errors.append(f"{label}: section {n} is not in the substitute comparison")
    for it in extra["floor"]:
        if it.get("status") not in FLOOR_STATUS:
            errors.append(f"amendments floor {it.get('id')}: unknown status {it.get('status')!r}")
        for st in it.get("positions", []):
            if st.get("stance") not in STANCES or not st.get("url") or not st.get("quote"):
                errors.append(f"amendments floor {it.get('id')}: each position needs a stance, url and quote")
    for it in extra["reactions"]:
        if it.get("stance") not in STANCES:
            errors.append(f"amendments reactions {it.get('id')}: unknown stance {it.get('stance')!r}")

    for key, what in (("origins", "source bill"), ("by_section", "sponsors' summary")):
        held = extra["origins"] if key == "origins" else extra["sponsor_summary"]["by_section"]
        for n in held:
            if n not in by_id:
                errors.append(f"amendments {what} {n}: not a section in the substitute comparison")
    for n, o in extra["origins"].items():
        if not str(o.get("url", "")).startswith("http") or not o.get("sponsor"):
            errors.append(f"amendments source bill {n}: needs a sponsor and a url")
    summary = extra["sponsor_summary"]
    for r in rows:
        if r["id"] in extra["origins"]:
            r["origin"] = extra["origins"][r["id"]]
        if r["id"] in summary["by_section"]:
            r["sponsor_summary"] = summary["by_section"][r["id"]]
        r["reactions"] = [x["id"] for x in extra["reactions"] if r["id"] in x.get("sections", [])]
        if not r["reactions"]:
            del r["reactions"]

    vote = extra.get("vote")
    if vote and not (vote.get("result") or vote.get("when")):
        errors.append("amendments vote: needs a result or a scheduled time ('when')")
    # Key changes: a label over one change note, so each carries that note's text and cite.
    row_by = {r["id"]: r for r in rows}
    highlights = []
    for h in extra.get("highlights", []):
        r = row_by.get(h["id"])
        if not r or h["point"] >= len(r.get("points", [])):
            errors.append(f"amendments highlight {h['id']}#{h['point']}: no such change note")
            continue
        highlights.append({"id": r["id"], "n": r["n"], "label": h["label"], **r["points"][h["point"]]})
    counts = {k: sum(1 for r in rows if r["status"] == k) for k in STATUSES}
    counts["substantive"] = sum(1 for r in rows if r.get("kind") == "substantive")
    counts["technical"] = sum(1 for r in rows if r.get("kind") == "technical")
    return {
        "old": diff["old"],
        "new": dict(diff["new"], pdf=SUB_PDF),
        "substitute": extra["substitute"],
        "counts": counts,
        "rows": rows,
        "highlights": highlights,
        "floor": extra["floor"],
        "floor_note": extra["floor_note"],
        "summary_source": {k: summary[k] for k in ("publisher", "date", "url")},
        "reactions": extra["reactions"],
        "vote": extra.get("vote"),
        "as_of": extra["as_of"],
    }


def index(amend: dict | None) -> dict | None:
    """What every page needs: each September section's fate in the substitute,
    for the banner on its section page, and the counts for the Overview."""
    if not amend:
        return None
    by_old = {}
    for r in amend["rows"]:
        if "old" in r:
            by_old[r["old"]["n"]] = {"id": r["id"], "status": r["status"], "kind": r.get("kind"), "n": r["n"]}
    return {"date": amend["new"]["released"], "counts": amend["counts"], "sections": by_old,
            "floor": len(amend["floor"]), "pages": amend["new"]["pages"],
            "reactions": {k: sum(1 for x in amend["reactions"] if x["stance"] == k) for k in STANCES}}
