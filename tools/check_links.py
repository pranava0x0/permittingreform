"""Check every link the site renders.

Walks the same data the build bakes into the site (so a link the reader can
click is a link this checked), fetches each unique URL once, and sorts the
answers into four classes:

  ok       the server answered with content
  blocked  the site refuses automated readers (401/403/429, a wall page);
           the link may be fine and needs a browser to confirm
  dead     404 or 410: the page is gone
  error    timeout, DNS, TLS or a 5xx; re-run before believing it

A blocked page that someone opened in a browser is recorded by hand in
data/checks/browser.json. It stays "blocked" here (no script read it) and
carries the date it was opened.

Writes data/checks/links.json (per URL) and the "links" summary in
data/checks.json, which the Method page shows.

Usage: python3 tools/check_links.py [--refresh] [--only SUBSTRING] [--workers N]
Exit codes: 0 no dead links, 1 dead links found, 2 nothing to check,
            3 more than half the fetches errored (network down; nothing written).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import webfetch  # noqa: E402

ROOT = build.ROOT
OUT = ROOT / "data/checks/links.json"
SUMMARY = ROOT / "data/checks.json"


def collect(core: dict) -> dict[str, list[str]]:
    """Every outbound URL the site renders, mapped to where it appears."""
    found: dict[str, list[str]] = defaultdict(list)

    def add(url, where: str) -> None:
        if isinstance(url, str) and url.lower().startswith(("http://", "https://")):
            found[url.split("#", 1)[0]].append(where)  # a fragment is the same document

    meta = core["meta"]
    add(meta["source_pdf"], "meta.source_pdf")
    for u in meta["mirror_pdfs"]:
        add(u, "meta.mirror_pdfs")
    for p in meta.get("prior_bills", []):
        add(p["url"], "meta.prior_bills")
    for p in core["overview"]["status"]["points"]:
        add(p["source"]["url"], "overview.status")
    if core["overview"].get("next"):
        add(core["overview"]["next"]["source"]["url"], "overview.next")
    for v in core["compare"]["versions"]:
        add(v.get("url"), f"compare.versions.{v['key']}")
    for g in core["compare"]["groups"]:
        for r in g["rows"]:
            for key in ("current", "epra", "speed"):
                add(r[key].get("url"), f"compare.{r['id']}.{key}")
            for src in (r.get("note") or {}).get("sources", []):
                add(src.get("url"), f"compare.{r['id']}.note")
    for item in core["compare"]["dropped"]:
        add(item.get("url"), "compare.dropped")
    for t in (core.get("takes") or {}).get("takes", []):
        add(t["url"], f"takes.{t['id']}")
    for e in core["timeline"]:
        for s in e.get("sources", []):
            add(s["url"], f"timeline.{e['id']}.source")
        add((e.get("quote") or {}).get("source_url"), f"timeline.{e['id']}.quote")
    for p in core["people"]:
        for s in p.get("sources", []):
            add(s["url"], f"people.{p['id']}.source")
        add((p.get("quote") or {}).get("source_url"), f"people.{p['id']}.quote")
        for k, u in (p.get("social") or {}).items():
            add(u, f"people.{p['id']}.social.{k}")
    for it in core["media"]:
        add(it["url"], f"media.{it['id']}")
        for v in it.get("visuals", []):
            add(v.get("url"), f"media.{it['id']}.visual")
    return found


BROWSER = ROOT / "data/checks/browser.json"


def browser_pages() -> dict:
    """Pages opened by hand in a browser: {url: {"opened": date, "title": str, "quotes": [str]}}."""
    if not BROWSER.exists():
        return {}
    pages = json.loads(BROWSER.read_text(encoding="utf-8"))["pages"]
    for url, rec in pages.items():
        if not rec.get("opened"):
            raise SystemExit(f"check_links: {BROWSER.name} entry {url!r} has no 'opened' date")
    return pages


def merge_summary(key: str, value: dict) -> None:
    data = json.loads(SUMMARY.read_text(encoding="utf-8")) if SUMMARY.exists() else {}
    data[key] = value
    SUMMARY.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--refresh", action="store_true", help="ignore cached answers and fetch again")
    ap.add_argument("--only", help="check only URLs containing this text")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    core, _, errors = build.build()
    if errors:
        print("check_links: the build has errors; fix those first", file=sys.stderr)
        return 2
    urls = collect(core)
    if args.only:
        urls = {u: w for u, w in urls.items() if args.only in u}
    if not urls:
        print("check_links: no URLs to check", file=sys.stderr)
        return 2

    print(f"check_links: {len(urls)} unique URLs from {sum(len(w) for w in urls.values())} places")
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pages = list(pool.map(lambda u: webfetch.read(u, refresh=args.refresh), sorted(urls)))

    counts = Counter(p.cls for p in pages)
    if counts["error"] > len(pages) / 2:
        print(f"check_links: {counts['error']} of {len(pages)} fetches errored; the network looks down. Nothing written.", file=sys.stderr)
        return 3

    results = {p.url: {"cls": p.cls, "status": p.status, "kind": p.kind, "note": p.note, "where": urls[p.url]} for p in pages}
    opened = browser_pages()
    for url, row in results.items():
        if row["cls"] == "blocked" and url in opened:
            row["browser"] = opened[url]["opened"]
    in_browser = sum(1 for row in results.values() if "browser" in row)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    checked = time.strftime("%Y-%m-%d", time.gmtime())
    saved, stamp = results, checked
    if args.only and OUT.exists():  # a partial run updates its URLs; it must not erase the rest or re-date them
        prior = json.loads(OUT.read_text(encoding="utf-8"))
        saved, stamp = prior["results"], prior.get("checked", checked)
        saved.update(results)
    OUT.write_text(json.dumps({"checked": stamp, "results": saved}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    summary = {"checked": checked, "total": len(pages), **{c: counts[c] for c in ("ok", "blocked", "dead", "error")},
               "browser": in_browser}
    if not args.only:
        merge_summary("links", summary)

    by_set: dict[str, Counter] = defaultdict(Counter)
    for p in pages:
        for where in urls[p.url]:
            by_set[where.split(".")[0]][p.cls] += 1
    print(f"check_links: finished in {time.time() - started:.0f}s")
    print(f"{'dataset':<10} {'ok':>4} {'blocked':>8} {'dead':>5} {'error':>6}")
    for name in sorted(by_set):
        c = by_set[name]
        print(f"{name:<10} {c['ok']:>4} {c['blocked']:>8} {c['dead']:>5} {c['error']:>6}")
    print(f"{'unique':<10} {counts['ok']:>4} {counts['blocked']:>8} {counts['dead']:>5} {counts['error']:>6}")
    for cls in ("dead", "error", "blocked"):
        rows = [p for p in pages if p.cls == cls]
        if rows:
            print(f"\n{cls} ({len(rows)}):")
            for p in rows:
                seen = f"  opened in a browser {results[p.url]['browser']}" if "browser" in results[p.url] else ""
                print(f"  {p.status or '-':>4} {p.url}  [{p.note}]{seen}  <- {urls[p.url][0]}")
    return 1 if counts["dead"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
