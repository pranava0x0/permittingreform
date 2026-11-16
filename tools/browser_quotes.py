#!/usr/bin/env python3
"""Read in a scripted Chrome the pages `make quotes` could not fetch, and test their quotes.

  NODE_PATH=<dir with playwright> python3 tools/browser_quotes.py            # pages marked unreachable
  NODE_PATH=... python3 tools/browser_quotes.py --write                      # ...and record what was found
  NODE_PATH=... python3 tools/browser_quotes.py --recheck                    # re-read every recorded page
  NODE_PATH=... python3 tools/browser_quotes.py --url URL --quote "words"    # one page, one quote

The list comes from data/checks/quotes.json, so run `make quotes` first. A quote counts as found
only when check_quotes.match calls it verified, the same test the gate applies to a fetched page.
--write records each found quote in data/checks/browser.json with today's date; run `make quotes`
again afterwards. A page behind a sign-in, a paywall or a "verify you are human" screen comes
back without the quote and is listed for a hand read: this script does not try to get past one.

Exit code: 0 when every quote was found or none needed a browser, 1 when any was not found,
2 when --url or --recheck matched nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_links  # noqa: E402
import check_quotes  # noqa: E402

ROOT = check_quotes.ROOT
BROWSER = ROOT / "data/checks/browser.json"


def wanted(args: argparse.Namespace) -> dict[str, list[str]]:
    """{url: [quotes to look for]}, in a stable order."""
    if args.quote is not None:
        if not args.url or not args.quote.strip():
            sys.exit("browser_quotes: --quote needs --url and some text")
        return {args.url: [args.quote]}
    pages: dict[str, list[str]] = {}
    if args.recheck:
        for url, rec in check_links.browser_pages().items():
            if rec.get("quotes"):
                pages[url] = list(rec["quotes"])
    else:
        if not check_quotes.OUT.exists():
            sys.exit("browser_quotes: data/checks/quotes.json is missing; run `make quotes` first")
        doc = json.loads(check_quotes.OUT.read_text(encoding="utf-8"))
        print(f"browser_quotes: reading the list from {check_quotes.OUT.name}, checked {doc.get('checked', 'on an unknown date')}")
        for row in doc["web"]:
            if row["result"] == "unreachable" and row["text"] not in pages.setdefault(row["url"], []):
                pages[row["url"]].append(row["text"])
    if args.url:
        pages = {u: q for u, q in pages.items() if u == args.url}
    return dict(sorted(pages.items()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="record found quotes in data/checks/browser.json")
    ap.add_argument("--recheck", action="store_true", help="re-read every page already recorded, instead of the unreachable ones")
    ap.add_argument("--url", help="only this page")
    ap.add_argument("--quote", help="look for this text on --url instead of the quotes on file")
    ap.add_argument("--headed", action="store_true", help="show the browser window (some sites refuse a headless one)")
    args = ap.parse_args()
    if args.write and (args.recheck or args.quote is not None):
        sys.exit("browser_quotes: --write records new reads; it does not combine with --recheck or --quote")
    if not os.environ.get("NODE_PATH"):
        sys.exit("browser_quotes: set NODE_PATH to a node_modules directory that holds playwright (see REFRESH.md)")

    pages = wanted(args)
    total = sum(len(q) for q in pages.values())
    print(f"browser_quotes: {total} quotes on {len(pages)} pages to read", flush=True)
    if not pages:
        if args.url or args.recheck:
            print("browser_quotes: nothing matched; check --url against the file it is read from", file=sys.stderr)
            return 2
        print(f"browser_quotes: no quote is marked unreachable in {check_quotes.OUT.relative_to(ROOT)}")
        return 0

    began = time.time()
    proc = subprocess.Popen(["node", str(ROOT / "tools/browser_text.cjs")] + (["--headed"] if args.headed else []),
                            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    proc.stdin.write("\n".join(pages) + "\n")
    proc.stdin.close()
    found: dict[str, dict] = {}
    lost: list[tuple[str, str, str]] = []
    seen = 0
    for line in proc.stdout:
        row = json.loads(line)
        seen += 1
        url = row["url"]
        text = row.get("text", "")
        hits = [q for q in pages[url] if check_quotes.match(q, text)[0] == "verified"]
        why = row.get("error") or f"HTTP {row.get('status')}, {len(text)} characters, title {row.get('title', '')[:60]!r}"
        for q in pages[url]:
            if q not in hits:
                lost.append((url, q, why))
        if hits:
            found[url] = {"title": row.get("title", "").strip(), "quotes": hits}
        took = int(time.time() - began)
        print(f"[{took // 60:02d}:{took % 60:02d}] {seen} of {len(pages)} {urlsplit(url).netloc}: {len(hits)} of {len(pages[url])} quotes found", flush=True)
    code = proc.wait()
    if code or seen != len(pages):
        print(f"browser_quotes: the browser stopped early (exit {code}) after {seen} of {len(pages)} pages", file=sys.stderr)
        return 1

    if args.write and found:
        doc = json.loads(BROWSER.read_text(encoding="utf-8"))
        today = time.strftime("%Y-%m-%d")
        for url, rec in found.items():
            old = doc["pages"].get(url, {})
            quotes = list(old.get("quotes", [])) + [q for q in rec["quotes"] if q not in old.get("quotes", [])]
            doc["pages"][url] = {"opened": today, "title": rec["title"] or old.get("title", ""), "quotes": quotes}
        BROWSER.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"browser_quotes: recorded {sum(len(r['quotes']) for r in found.values())} quotes on {len(found)} pages in {BROWSER.relative_to(ROOT)}; run `make quotes` again")
    for url, quote, why in lost:
        print(f"  NOT FOUND {url}\n      quote: {quote[:110]!r}\n      page:  {why}")
    print(f"browser_quotes: found {total - len(lost)} of {total} quotes" + (f"; {len(lost)} need a hand read" if lost else ""))
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
