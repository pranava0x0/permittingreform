"""Bake the tracker's data into the static site.

Reads the source-of-truth files under data/ and writes (site/bill.pdf, the
same-origin copy that makes #page=N links work, is committed as is):
  site/data/core.js   window.PR_DATA  (summaries, comparison, timeline, people, media)
  site/data/bill.js   window.PR_BILL  (full bill text as paragraphs with page and line cites)
  site/llms.txt       compact agent index
  site/llms-full.txt  full text and analysis
  site/sections/*.md  cited analysis and statutory text, one section per file
  site/data/*.json    browser-equivalent JSON
  site/reading.html   section index without JavaScript
  site/sitemap.xml    crawlable HTML entry points

Fails loud (exit 1) on any dangling reference or unverifiable bill quote.
Standard library only. Output is deterministic: running it twice changes nothing.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import billtext  # noqa: E402

ROOT = billtext.ROOT
DATA = ROOT / "data"
SITE = ROOT / "site"
SITE_URL = "https://pranava0x0.github.io/permittingreform/"
REPO_URL = "https://github.com/pranava0x0/permittingreform"
PDF_NAME = "bill.pdf"
# The date the datasets were last captured and checked. Bump on a data refresh, not on a rebuild.
DATA_AS_OF = "2026-10-02"

PRIOR_BILLS = [
    {"label": "SPEED Act (H.R. 4776), engrossed in House", "url": "https://www.govinfo.gov/content/pkg/BILLS-119hr4776eh/html/BILLS-119hr4776eh.htm"},
    {"label": "Energy Permitting Reform Act of 2024 (S. 4753), reported in Senate", "url": "https://www.govinfo.gov/content/pkg/BILLS-118s4753rs/html/BILLS-118s4753rs.htm"},
]

OPTIONAL = {"timeline": "events", "people": "people", "media": "items"}
EFFECTS = {"narrows", "expands", "changes"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_js(var: str, value) -> str:
    body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f"window.{var}={body};\n"


def cite(loc: dict) -> list:
    return [loc["p1"], loc["l1"], loc["p2"], loc["l2"]]


PRIOR_FILES = {"speed": ("speed_act_hr4776_eh.json", 0), "epra": ("epra_2024_s4753_rs.json", 1)}


def cite_url(key: str, cite_text: str, prior: dict) -> str | None:
    """A link for a comparison cite: the section heading in the earlier bill's
    text, or the U.S. Code section at Cornell's Legal Information Institute."""
    if key in prior:
        m = re.search(r"Secs?\. (\d+)", cite_text or "")
        if m and m.group(1) in prior[key]["headings"]:
            heading = prior[key]["headings"][m.group(1)]
            return prior[key]["url"] + "#:~:text=" + quote(f"SEC. {m.group(1)}. {heading}", safe="")
        return prior[key]["url"]
    m = re.search(r"(\d+) U\.S\.C\. (\d+[a-z]*(?:-\d+)?)", cite_text or "")
    if m:
        return f"https://www.law.cornell.edu/uscode/text/{m.group(1)}/{m.group(2)}"
    return None


def build() -> tuple[dict, dict, list[str]]:
    errors: list[str] = []
    bill = billtext.load_sections()
    pdf = SITE / PDF_NAME
    if not pdf.exists() or hashlib.sha256(pdf.read_bytes()).hexdigest() != bill["meta"].get("pdf_sha256"):
        errors.append("PDF differs from indexed text; run tools/parse_bill.py")
    analysis = load(DATA / "bill/analysis.json")["sections"]
    topics = load(DATA / "topics.json")
    overview = load(DATA / "overview.json")
    compare = load(DATA / "compare.json")
    by_num = {s["number"]: s for s in bill["sections"]}
    cites_path = DATA / "bill/point_cites.json"
    point_cites = load(cites_path) if cites_path.exists() else {}
    prior = {}
    for key, (fname, idx) in PRIOR_FILES.items():
        doc = load(DATA / "prior_bills" / fname)
        prior[key] = {"url": PRIOR_BILLS[idx]["url"], "headings": {x["number"]: x["heading"] for x in doc["sections"]}}

    for n in by_num:
        if n not in analysis:
            errors.append(f"section {n} has no analysis entry")
    for n in analysis:
        if n not in by_num:
            errors.append(f"analysis entry {n} matches no section in the bill")

    sections = []
    paras: dict[str, list] = {}
    for s in bill["sections"]:
        n = s["number"]
        a = analysis.get(n, {})
        quotes = []
        for q in a.get("quotes", []):
            loc = billtext.locate(s["lines"], q["text"])
            if not loc:
                errors.append(f"section {n}: quote not found verbatim: {q['text'][:70]!r}")
                continue
            if loc["count"] != 1:
                errors.append(f"section {n}: ambiguous quote; include more context")
            quotes.append({"t": billtext.norm(q["text"]), "why": q.get("why", ""), "c": cite(loc)})
        points = []
        for i, text in enumerate(a.get("key_points", []), 1):
            point = {"t": text}
            span = point_cites.get(n, {}).get(text)
            if span:
                loc = billtext.locate(s["lines"], span)
                if loc:
                    point["c"] = cite(loc)
                else:
                    errors.append(f"section {n}: the passage cited for key point {i} is not in the section text: {span[:60]!r}")
            points.append(point)
        for t in a.get("topics", []):
            if t not in topics:
                errors.append(f"section {n}: unknown topic {t!r}")
        sections.append({
            "n": n,
            "h": s["heading"],
            "div": s["division"], "divh": s["division_heading"],
            "ti": s["title"], "tih": s["title_heading"],
            "su": s["subtitle"], "suh": s["subtitle_heading"],
            "p1": s["page_start"], "l1": s["line_start"], "p2": s["page_end"],
            "words": s["words"],
            "imp": a.get("importance", 1),
            "topics": a.get("topics", []),
            "plain": a.get("plain", ""),
            "points": points,
            "quotes": quotes,
            "vs": {"current": a.get("vs_current_law", ""), "speed": a.get("vs_speed_act", ""), "epra": a.get("vs_epra_2024", "")},
        })
        paras[n] = billtext.paragraphs(s["lines"])

    def check_refs(where: str, refs: list[str]) -> None:
        for r in refs:
            if r not in by_num:
                errors.append(f"{where}: section {r} does not exist")

    for h in overview["headlines"]:
        check_refs(f"overview headline {h['id']}", h["sections"])
    for kind in ("clocks", "money"):
        for row in overview[kind]:
            check_refs(f"overview {kind}", [row["section"]])
            sec = by_num.get(row["section"])
            loc = billtext.locate(sec["lines"], row["quote"]) if sec else None
            if not loc:
                errors.append(f"overview {kind} {row.get('what')!r}: quote not found in section {row['section']}")
            else:
                row["c"] = cite(loc)
    for g in compare["groups"]:
        for r in g["rows"]:
            check_refs(f"compare row {r['id']}", r["senate"].get("sections", []))
            for key in ("current", "epra", "speed"):
                if r[key].get("cite"):
                    url = cite_url(key, r[key]["cite"], prior)
                    if url:
                        r[key]["url"] = url
    bills = compare.get("bills")
    if bills:
        keys = [v["key"] for v in bills["versions"]]
        for r in bills["rows"]:
            for k in keys:
                cell = r.get(k) or {}
                if not cell.get("text"):
                    errors.append(f"compare bills {r['id']}: empty cell {k}")
                check_refs(f"compare bills {r['id']}", cell.get("sections", []))
    for a in compare["added"]:
        check_refs("compare added", a["sections"])
    for item in compare["dropped"]:
        item["url"] = cite_url(item["from"], item["cite"], prior)

    # Communities: how the bill changes who can comment, consult, take part or sue.
    comm_path = DATA / "communities.json"
    communities = load(comm_path) if comm_path.exists() else None
    if communities:
        gids = {g["id"] for g in communities["groups"]}
        for r in communities["rows"]:
            where = f"communities {r['id']}"
            if r["group"] not in gids:
                errors.append(f"{where}: unknown group {r['group']!r}")
            for w in r["who"]:
                if w not in communities["who"]:
                    errors.append(f"{where}: unknown party {w!r}")
            if r["effect"] not in EFFECTS:
                errors.append(f"{where}: effect {r['effect']!r} is not one of {sorted(EFFECTS)}")
            check_refs(where, r["sections"])
            if r.get("quote"):
                sec = by_num.get(r.get("quote_section", r["sections"][0]))
                loc = billtext.locate(sec["lines"], r["quote"]) if sec else None
                if not loc:
                    errors.append(f"{where}: quote not found in section {r.get('quote_section', r['sections'][0])}")
                else:
                    r["c"] = cite(loc)

    extra = {}
    for name, key in OPTIONAL.items():
        path = DATA / f"{name}.json"
        extra[name] = load(path)[key] if path.exists() else []
    checks_path = DATA / "checks.json"
    checks = load(checks_path) if checks_path.exists() else {}
    if checks.get("inference"):
        checks["inference"]["stale"] = checks["inference"].get("input_sha256") != billtext.review_fingerprint()

    # Stamp each outbound link with what the link checker last saw, so the
    # site can say which ones no script was able to open.
    links_path = DATA / "checks/links.json"
    link_cls = ({u: r["cls"] for u, r in load(links_path)["results"].items() if "browser" not in r}
                if links_path.exists() else {})

    def stamp(row: dict, key: str = "url") -> None:
        cls = link_cls.get(row.get(key))
        if cls and cls != "ok":
            row["lk"] = cls
        row.pop("verified", None)

    for it in extra["media"]:
        stamp(it)
    for rec in extra["timeline"] + extra["people"]:
        for src in rec.get("sources", []):
            stamp(src)

    all_points = [p for sec in sections for p in sec["points"]]
    checks["points"] = {"total": len(all_points), "cited": sum(1 for p in all_points if "c" in p)}

    meta = dict(bill["meta"])
    meta.update({
        "sections": len(sections),
        "quotes": sum(len(s["quotes"]) for s in sections),
        "paragraphs": sum(len(p) for p in paras.values()),
        "pdf": PDF_NAME,
        "prior_bills": PRIOR_BILLS,
        "site_url": SITE_URL,
        "repo_url": REPO_URL,
        "as_of": DATA_AS_OF,
    })
    core = {
        "meta": meta,
        "topics": topics,
        "sections": sections,
        "overview": overview,
        "compare": compare,
        "communities": communities,
        "timeline": extra["timeline"],
        "people": extra["people"],
        "media": extra["media"],
        "checks": checks,
    }
    return core, paras, errors


def llms_txt(core: dict) -> str:
    m = core["meta"]
    out = [
        f"# {m['short_title']}: permitting reform tracker",
        "",
        f"> Section index, plain-language summaries, verbatim quotes with page and line cites, and a comparison with the SPEED Act and the Energy Permitting Reform Act of 2024. Bill text released {m['released']}; {m['pages']} pages, {m['sections']} sections. Data as of {m['as_of']}.",
        "",
        f"- Site: {m['site_url']}",
        f"- Bill PDF (official): {m['source_pdf']}",
        f"- Source data: {m['repo_url']}",
        "",
        "## Reading and retrieval",
        "",
        "Independent tracker. BAAJA is the September 30, 2026 draft, not enacted law. Summaries are AI-assisted. Verify legal claims against the official PDF and compare the specified versions, not later amendments.",
        "PDF citations use printed bill pages and lines. A matching quote proves occurrence; it does not validate nearby interpretations. Source positions describe the cited item, not every position held by its author.",
        f"- [No-JavaScript section index]({m['site_url']}reading.html)",
        f"- [Full text and analysis]({m['site_url']}llms-full.txt): all sections, comparisons, timeline, people and media with citations.",
        f"- [Tracker JSON]({m['site_url']}data/core.json): the same data the browser renders, including check coverage.",
        f"- [Bill paragraph JSON]({m['site_url']}data/bill.json): section number to [printed page, line, indent level, text] arrays.",
        "- Fetch sections/{number}.md for one section. Each file includes its summary, cited key points, quotes, comparison notes and full statutory text.",
        "- Browser search: #/bill/search/{URL-encoded query}; section: #/bill/sec/{number}; passage: #/bill/sec/{number}/{page}-{line}. Fragment routes require JavaScript; use the Markdown or JSON endpoints for HTTP retrieval.",
        "",
        "## Check coverage",
        "",
        review_coverage(core),
        "",
        "## Sections",
        "",
    ]
    for s in core["sections"]:
        topics = ", ".join(core["topics"].get(t, t) for t in s["topics"])
        out.append(f"- [Sec. {s['n']}. {s['h']}]({m['site_url']}sections/{s['n']}.md) (pp. {s['p1']} to {s['p2']}; {topics})")
    out += ["", "## Research", "",
            f"- [Data center bills and Communities]({m['site_url']}llms-full.txt): BAAJA beside the Ratepayer Protection Act, GRID Savings Act, Power for the People Act, GRID Act and current policy; and who can comment, consult, plan or sue.",
            f"- [Timeline, people and media]({m['site_url']}llms-full.txt): dated records with source links and attributed positions.",
            f"- [Method and check status]({m['site_url']}#/method): browser view; equivalent checks are in data/core.json.",
            f"- [Subject comparisons]({m['site_url']}#/compare): browser view; retrieve the compare object in data/core.json without JavaScript."]
    return "\n".join(out) + "\n"


def review_coverage(core: dict) -> str:
    checks = core["checks"]
    inf = checks.get("inference", {})
    return (f"Saved AI review: {inf.get('supported', 0)} supported, {inf.get('flagged', 0)} flagged, "
            f"{inf.get('unchecked', 0)} unchecked of {inf.get('total', 0)} statements; "
            f"checked {inf.get('checked', 'unknown')}; stale: {str(inf.get('stale', True)).lower()}. "
            "Coverage excludes current-law comparison cells and some research paraphrases. "
            "Read data/core.json checks for link and quote results and their dates. A stale review does not verify the current wording.")


def section_markdown(core: dict, paras: dict, sec: dict) -> str:
    base = core["meta"]["site_url"]

    def citation(c: list) -> str:
        p1, l1, p2, l2 = c
        return f"[p. {p1}, line {l1} to p. {p2}, line {l2}]({base}bill.pdf#page={p1})"

    out = [f"# Sec. {sec['n']}. {sec['h']}", "", "BAAJA draft released September 30, 2026. AI-assisted analysis; proposed changes.",
           "", review_coverage(core), "", f"[Official PDF]({core['meta']['source_pdf']}) · [Browser section]({base}#/bill/sec/{sec['n']})",
           "", "## Summary", "", sec["plain"], "", "## Key points", ""]
    for point in sec["points"]:
        out.append(f"- {point['t']} ({citation(point['c'])})")
    out += ["", "## Selected statutory quotes", ""]
    for q in sec["quotes"]:
        out += [f"> {q['t']}", "", citation(q["c"]), "", q.get("why", ""), ""]
    out += ["## Comparison notes", ""]
    out += [f"- [{p['label']}]({p['url']})" for p in core["meta"]["prior_bills"]]
    out += [""]
    for key, label in (("current", "Current law"), ("epra", "EPRA 2024 (reported S. 4753)"), ("speed", "SPEED Act (House-passed H.R. 4776)")):
        out += [f"### {label}", "", sec["vs"].get(key) or "No note recorded.", ""]
    out += ["## Full statutory text", "", "Extracted from the official PDF; line cites mark paragraph starts. Consult the PDF for exact layout.", ""]
    for page, line, level, text in paras[sec["n"]]:
        out += [f"[p. {page}, line {line}]({base}bill.pdf#page={page}) (indent level {level})", "", text, ""]
    return "\n".join(out) + "\n"


def llms_full(core: dict, paras: dict) -> str:
    out = [llms_txt(core)]
    out += [section_markdown(core, paras, sec) for sec in core["sections"]]
    out += ["## Subject comparisons", ""]
    for group in core["compare"]["groups"]:
        for row in group["rows"]:
            out += [f"### {row['topic']}", ""]
            for key in ("current", "epra", "speed", "senate", "note"):
                if key not in row:
                    continue
                cell = row[key]
                out.append(f"- {key}: {cell['text']}")
                if cell.get("url"):
                    out.append(f"  Source: [{cell.get('cite', 'Source')}]({cell['url']})")
                for source in cell.get("sources", []):
                    out.append(f"  Source: [{source.get('cite', 'Source')}]({source['url']})")
                for n in cell.get("sections", []):
                    out.append(f"  Bill: [{n}]({core['meta']['site_url']}sections/{n}.md)")
    bills = core["compare"].get("bills")
    if bills:
        out += ["", f"## {bills['label']}", "", bills.get("intro", ""), ""]
        out += [f"- {v['label']}: {v['sub']} [{v['label']}]({v['url']})" for v in bills["versions"]]
        for row in bills["rows"]:
            out += ["", f"### {row['topic']}", ""]
            for v in bills["versions"]:
                cell = row.get(v["key"])
                if not cell:
                    continue
                out.append(f"- {v['label']}: {cell['text']}")
                if cell.get("url"):
                    out.append(f"  Source: [{cell.get('cite', 'Source')}]({cell['url']})")
                if cell.get("quote"):
                    out.append(f"  Quote: \"{cell['quote']}\"")
                for n in cell.get("sections", []):
                    out.append(f"  Bill: [{n}]({core['meta']['site_url']}sections/{n}.md)")
        if bills.get("others"):
            out += ["", f"### {bills.get('others_label', 'Other bills')}", "", "```json", json.dumps(bills["others"], ensure_ascii=False), "```"]
    comm = core.get("communities")
    if comm:
        out += ["", "## Communities: who can comment, consult, plan or sue", "", comm["intro"], ""]
        for row in comm["rows"]:
            who = ", ".join(comm["who"].get(w, w) for w in row["who"])
            out += [f"### {row['topic']}", "", f"- Effect: {row['effect']}; affects: {who}",
                    f"- Now: {row['now']}" + (f" Source: [{row['now_cite']}]({row['now_url']})" if row.get("now_url") else ""),
                    f"- BAAJA: {row['baaja']}",
                    "- Bill: " + ", ".join(f"[{n}]({core['meta']['site_url']}sections/{n}.md)" for n in row.get("sections", []))]
            if row.get("quote"):
                out.append(f"- Quote: \"{row['quote']}\"")
            out.append("")
    out += ["", "## Added and dropped provisions", "", "```json", json.dumps({k: core["compare"][k] for k in ("added", "dropped")}, ensure_ascii=False), "```", ""]
    for label, rows in (("Timeline", core["timeline"]), ("People", core["people"]), ("Media", core["media"])):
        out += ["", f"## {label}", ""]
        for row in rows:
            # JSON preserves all provenance, position tags and conditional fields.
            out += ["```json", json.dumps(row, ensure_ascii=False), "```", ""]
    return "\n".join(out) + "\n"


def reading_html(core: dict) -> str:
    esc = html.escape
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<title>Section index · Permitting Reform</title>',
           f'<link rel="canonical" href="{SITE_URL}reading.html">',
           '<link rel="stylesheet" href="styles.css"></head><body>',
           '<main id="main"><h1>Permitting Reform: section index</h1>',
           '<p>September 30, 2026 BAAJA draft. Proposed changes; AI-assisted summaries.</p>',
           f'<p>{esc(review_coverage(core))}</p>',
           '<p><a href="index.html">Interactive tracker</a> · <a href="llms.txt">Agent index</a> · <a href="llms-full.txt">Full text and analysis</a> · <a href="data/core.json">Tracker JSON</a></p>']
    for sec in core["sections"]:
        out += [f'<section id="sec-{sec["n"]}"><h2>Sec. {sec["n"]}. {esc(sec["h"])}</h2>',
                f'<p>{esc(sec["plain"])}</p>',
                f'<p><a href="sections/{sec["n"]}.md">Text and cited analysis</a> · <a href="bill.pdf#page={sec["p1"]}">PDF page {sec["p1"]}</a></p></section>']
    return "\n".join(out + ['</main></body></html>']) + "\n"


def main() -> int:
    core, paras, errors = build()
    if errors:
        for e in errors:
            print(f"build: {e}", file=sys.stderr)
        print(f"build: {len(errors)} error(s); nothing written", file=sys.stderr)
        return 1
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    (SITE / "data/core.js").write_text(dump_js("PR_DATA", core), encoding="utf-8")
    (SITE / "data/bill.js").write_text(dump_js("PR_BILL", paras), encoding="utf-8")
    (SITE / "llms.txt").write_text(llms_txt(core), encoding="utf-8")
    (SITE / "llms-full.txt").write_text(llms_full(core, paras), encoding="utf-8")
    (SITE / "reading.html").write_text(reading_html(core), encoding="utf-8")
    for name, data in (("core", core), ("bill", paras)):
        (SITE / f"data/{name}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (SITE / "sections").mkdir(exist_ok=True)
    for sec in core["sections"]:
        (SITE / f"sections/{sec['n']}.md").write_text(section_markdown(core, paras, sec), encoding="utf-8")
    (SITE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
                                    "\n".join(f"<url><loc>{SITE_URL}{path}</loc></url>" for path in ("", "reading.html")) + "\n</urlset>\n", encoding="utf-8")
    if not (SITE / PDF_NAME).exists():
        print(f"build: site/{PDF_NAME} is missing; download it from {core['meta']['source_pdf']}", file=sys.stderr)
        return 1
    m = core["meta"]
    print(
        f"build: {m['sections']} sections, {m['paragraphs']} paragraphs, {m['quotes']} quotes, "
        f"{sum(len(g['rows']) for g in core['compare']['groups'])} comparison rows, "
        f"{len(core['timeline'])} events, {len(core['people'])} people, {len(core['media'])} media items -> site/data/"
    )
    for name in ("core.js", "bill.js"):
        print(f"build:   site/data/{name} {(SITE / 'data' / name).stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
