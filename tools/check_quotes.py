"""Check every quotation the site prints against its source.

Two kinds of quote, two kinds of check:

1. Bill quotes (section key text, the deadline and money tables). Each must
   appear verbatim in the parsed bill text of the section it cites. This uses
   the same locate() the build uses, so the page and line shown on the site
   are the ones verified here.

2. Web quotes (timeline, people, media). The cited page is fetched (cached)
   and its readable text searched for the quote. Results:
     verified      found, allowing only for quote-mark, dash and spacing differences
     near          at least 85% of the quote's 6-word runs are on the page
     missing       the page was read and the quote is not on it
     browser       the site refuses scripts, and the quote was read on the page in a
                   browser by hand (recorded in data/checks/browser.json)
     unreachable   the site refused or failed the fetch; needs a browser
     unverifiable  audio or video; only a title is machine-readable

Writes data/checks/quotes.json (per quote) and the "quotes" summary in
data/checks.json.

Usage: python3 tools/check_quotes.py [--refresh] [--bill-only]
Exit codes: 0 clean, 1 a quote is missing from its source, 2 nothing examined.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import billtext  # noqa: E402
import build  # noqa: E402
import check_links  # noqa: E402
import webfetch  # noqa: E402

ROOT = build.ROOT
OUT = ROOT / "data/checks/quotes.json"
PUNCT = str.maketrans({
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "‘": "'", "’": "'", "‚": "'", "′": "'",
    "—": "-", "–": "-", "‑": "-", "‐": "-", "−": "-", " ": " ", "​": "", "‌": "", "﻿": "",
})


def canon(text: str) -> str:
    """Fold the differences a copy-paste introduces, and nothing else."""
    text = unicodedata.normalize("NFKC", text).translate(PUNCT).lower()
    text = re.sub(r"\s+([,.;:!?%)])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def match(quote: str, page_text: str) -> tuple[str, float]:
    """Return (result, share of the quote's 6-word runs found on the page)."""
    hay = canon(page_text)
    needle = canon(quote).strip('"\' ')
    parts = [p.strip() for p in re.split(r"\s*(?:\.\.\.|…|\[\.\.\.\])\s*", needle) if p.strip()]
    cursor = 0
    exact = bool(parts)
    for part in parts:
        found = re.search(r"(?<!\w)" + re.escape(part) + r"(?!\w|[.,]\d)", hay[cursor:])
        if not found:
            exact = False
            break
        cursor += found.end()
    if exact:
        return "verified", 1.0
    # Whitespace changes can change meaning ("therapist" / "the rapist").
    # A close match needs review even if removing spaces makes it identical.
    words = needle.split()
    size = 6 if len(words) >= 6 else max(1, len(words))
    runs = [" ".join(words[i:i + size]) for i in range(0, max(1, len(words) - size + 1))]
    share = sum(1 for r in runs if r in hay) / len(runs)
    return ("near" if share >= 0.85 else "missing"), share


def bill_quotes() -> tuple[int, list[str]]:
    bill = billtext.load_sections()
    by_num = {s["number"]: s for s in bill["sections"]}
    analysis = json.loads((ROOT / "data/bill/analysis.json").read_text(encoding="utf-8"))["sections"]
    overview = json.loads((ROOT / "data/overview.json").read_text(encoding="utf-8"))
    total, bad = 0, []
    for n, a in analysis.items():
        for q in a.get("quotes", []):
            total += 1
            if n not in by_num or not billtext.locate(by_num[n]["lines"], q["text"]):
                bad.append(f"section {n}: {q['text'][:80]!r}")
    cpath = ROOT / "data/communities.json"
    for r in (json.loads(cpath.read_text(encoding="utf-8"))["rows"] if cpath.exists() else []):
        if r.get("quote"):
            total += 1
            n = r.get("quote_section", r["sections"][0])
            if n not in by_num or not billtext.locate(by_num[n]["lines"], r["quote"]):
                bad.append(f"communities {r['id']}, section {n}: {r['quote'][:80]!r}")
    for kind in ("clocks", "money"):
        for row in overview[kind]:
            total += 1
            sec = by_num.get(row["section"])
            if not sec or not billtext.locate(sec["lines"], row["quote"]):
                bad.append(f"overview {kind}, section {row['section']}: {row['quote'][:80]!r}")
    return total, bad


def web_quotes(core: dict) -> list[dict]:
    rows = []
    for e in core["timeline"]:
        q = e.get("quote")
        if q:
            rows.append({"where": f"timeline.{e['id']}", "text": q["text"], "speaker": q.get("speaker", ""), "url": q["source_url"]})
    for p in core["people"]:
        q = p.get("quote")
        if q:
            rows.append({"where": f"people.{p['id']}", "text": q["text"], "speaker": p["name"], "url": q["source_url"]})
    for it in core["media"]:
        q = it.get("quote")
        if q:
            rows.append({"where": f"media.{it['id']}", "text": q["text"], "speaker": q.get("speaker", ""), "url": it["url"]})
    bills = core["compare"].get("bills") or {"rows": []}
    for r in bills["rows"]:
        for k, cell in r.items():
            if isinstance(cell, dict) and cell.get("quote"):
                rows.append({"where": f"compare.bills.{r['id']}.{k}", "text": cell["quote"], "speaker": "", "url": cell["url"]})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--refresh", action="store_true", help="ignore cached pages and fetch again")
    ap.add_argument("--bill-only", action="store_true", help="skip the web quotes (no network)")
    args = ap.parse_args()

    total, bad = bill_quotes()
    if not total:
        print("check_quotes: no bill quotes found to check", file=sys.stderr)
        return 2
    print(f"check_quotes: bill quotes: {total - len(bad)} of {total} found verbatim")
    for b in bad:
        print(f"  NOT IN BILL TEXT: {b}")
    if args.bill_only:
        return 1 if bad else 0

    core, _, errors = build.build()
    if errors:
        print("check_quotes: the build has errors; fix those first", file=sys.stderr)
        return 1
    rows = web_quotes(core)
    print(f"check_quotes: web quotes: {len(rows)} to check against {len({r['url'] for r in rows})} pages")
    with ThreadPoolExecutor(max_workers=6) as pool:
        pages = dict(zip(sorted({r["url"] for r in rows}), pool.map(lambda u: webfetch.read(u, refresh=args.refresh), sorted({r["url"] for r in rows}))))

    opened = check_links.browser_pages()
    for r in rows:
        page = pages[r["url"]]
        if page.cls != "ok":
            r["result"], r["share"], r["note"] = "unreachable", 0.0, f"{page.cls}: {page.note}"
            seen = opened.get(r["url"])
            if page.cls == "blocked" and seen and canon(r["text"]) in {canon(q) for q in seen.get("quotes", [])}:
                r["result"], r["share"], r["note"] = "browser", 1.0, f"read in a browser on {seen['opened']}"
        elif page.kind == "youtube":
            r["result"], r["share"], r["note"] = "unverifiable", 0.0, "video: only the title is machine-readable"
        else:
            r["result"], r["share"] = match(r["text"], page.text)
            r["note"] = page.note
            if r["result"] == "missing" and len(page.text) < 1500:
                r["result"], r["note"] = "unreachable", "page returned too little text to search (script-rendered)"

    counts = Counter(r["result"] for r in rows)
    checked = time.strftime("%Y-%m-%d", time.gmtime())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"checked": checked, "bill": {"total": total, "verified": total - len(bad)}, "web": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    check_links.merge_summary("quotes", {
        "checked": checked, "bill_total": total, "bill_verified": total - len(bad),
        "total": len(rows), "verified": counts["verified"], "near": counts["near"], "missing": counts["missing"],
        "browser": counts["browser"], "unreachable": counts["unreachable"], "unverifiable": counts["unverifiable"],
    })
    print("check_quotes: " + ", ".join(f"{k} {counts[k]}" for k in ("verified", "browser", "near", "missing", "unreachable", "unverifiable")))
    for result in ("missing", "near"):
        for r in rows:
            if r["result"] == result:
                print(f"  {result.upper()} ({r['share']:.0%}) {r['where']}\n      quote: {r['text'][:110]!r}\n      page:  {r['url']}")
    return 1 if (bad or counts["missing"] or counts["near"] or counts["unreachable"] or counts["unverifiable"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
