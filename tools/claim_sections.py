"""Point claims in coverage at the passed text's sections. Never rates a claim.

  python3 tools/claim_sections.py suggest "it caps lawsuits at 150 days"   # ranked sections + candidate passages
  python3 tools/claim_sections.py pending [--json]   # sweep claims on integrated items with no row in data/claims.json
  python3 tools/claim_sections.py draft              # writes data/research/claims_draft.json for every pending claim
  python3 tools/claim_sections.py check              # validates data/claims.json; prints what it covered

`pending` exits 1 while a claim collected in a sweep (data/research/sweep-*/*-proposed.json,
key `claims`) sits on a coverage item but has no row in data/claims.json and no entry in
data/claims.json `skipped` (with a reason). That keeps a refresh from dropping claims.

`draft` is deterministic: the top suggested sections and passages for each pending claim,
for a person to confirm, cut to the clause that matters, or replace, then move into
data/claims.json. Suggestions are a keyword ranking, not a reading: check every one.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import claims as C

ROOT = C.ROOT
DATA = C.DATA


def media_urls() -> set[str]:
    return {r["url"] for r in C.load(DATA / "media.json")["items"]}


def claims_doc() -> dict:
    return C.load(C.CLAIMS) if C.CLAIMS.exists() else {"claims": [], "skipped": []}


def norm(s: str) -> str:
    return " ".join(s.split()).strip().lower()


def pending() -> list[dict]:
    doc = claims_doc()
    held = {(c["media_url"], norm(c["quote"])) for c in doc["claims"]}
    held |= {(s["media_url"], norm(s["quote"])) for s in doc.get("skipped", [])}
    urls = media_urls()
    out, seen = [], set()
    for f in sorted((DATA / "research").glob("sweep-*/*-proposed.json")):
        try:
            doc = C.load(f)
            items = doc if isinstance(doc, list) else doc.get("items", [])
        except json.JSONDecodeError as e:
            print(f"warning: {f}: {e}", file=sys.stderr)
            continue
        for it in items:
            for cl in it.get("claims", []) or []:
                key = (it.get("url"), norm(cl.get("text", "")))
                if not key[1] or key in held or key in seen or it.get("url") not in urls:
                    continue
                seen.add(key)
                out.append({"media_url": it["url"], "date": it.get("date", ""), "outlet": it.get("outlet", ""),
                            "speaker": cl.get("speaker", ""), "quote": cl["text"], "about": cl.get("about", ""),
                            "hint": cl.get("sections_hint", []), "from": str(f.relative_to(ROOT))})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("suggest")
    s.add_argument("claim")
    s.add_argument("--top", type=int, default=3)
    p = sub.add_parser("pending")
    p.add_argument("--json", action="store_true")
    sub.add_parser("draft")
    sub.add_parser("check")
    a = ap.parse_args()

    if a.cmd == "suggest":
        print(json.dumps(C.suggest(a.claim, a.top), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "pending":
        rows = pending()
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        else:
            for r in rows:
                print(f"{r['date']} {r['outlet']}: {r['quote'][:100]!r}  ({r['media_url']})")
            print(f"{len(rows)} pending claim(s)")
        return 1 if rows else 0
    if a.cmd == "draft":
        rows = pending()
        drafts = []
        for i, r in enumerate(rows):
            hint = " ".join(f"section {n}" for n in r["hint"])
            sug = C.suggest((r["about"] + ". " + r["quote"] + " " + hint).strip(), 3)
            drafts.append({"id": f"draft-{i + 1}", "media_url": r["media_url"], "speaker": r["speaker"], "quote": r["quote"],
                           "about": r["about"], "review": [{"section": x["section"], "text": x["text"], "_heading": x["heading"],
                                                            "_at": x["at"], "_unique": x["unique"]} for x in sug]})
        out = DATA / "research/claims_draft.json"
        out.write_text(json.dumps({"drafts": drafts}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{len(drafts)} draft(s) written to {out.relative_to(ROOT)}")
        return 0
    # check
    errors: list[str] = []
    doc = claims_doc()
    by_url = C.resolve(doc["claims"], media_urls(), errors)
    for s_ in doc.get("skipped", []):
        if not str(s_.get("why", "")).strip():
            errors.append(f"skipped claim on {s_.get('media_url')}: no reason")
    for e in errors:
        print("error:", e)
    n_pass = sum(len(c["review"]) for v in by_url.values() for c in v)
    secs = {r["n"] for v in by_url.values() for c in v for r in c["review"]}
    print(f"claims: {len(doc['claims'])} on {len(by_url)} coverage items; {n_pass} passages in {len(secs)} sections; "
          f"{len(doc.get('skipped', []))} skipped; {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
