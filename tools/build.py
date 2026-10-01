"""Bake the tracker's data into the static site.

Reads the source-of-truth files under data/ and writes (site/bill.pdf, the
same-origin copy that makes #page=N links work, is committed as is):
  site/data/core.js   window.PR_DATA  (summaries, comparison, timeline, people, media)
  site/data/bill.js   window.PR_BILL  (full bill text as paragraphs with page and line cites)
  site/llms.txt       plain-text digest for agent readers

Fails loud (exit 1) on any dangling reference or unverifiable bill quote.
Standard library only. Output is deterministic: running it twice changes nothing.
"""
from __future__ import annotations

import hashlib
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
DATA_AS_OF = "2026-10-01"

PRIOR_BILLS = [
    {"label": "SPEED Act (H.R. 4776), engrossed in House", "url": "https://www.govinfo.gov/content/pkg/BILLS-119hr4776eh/html/BILLS-119hr4776eh.htm"},
    {"label": "Energy Permitting Reform Act of 2024 (S. 4753), reported in Senate", "url": "https://www.govinfo.gov/content/pkg/BILLS-118s4753rs/html/BILLS-118s4753rs.htm"},
]

OPTIONAL = {"timeline": "events", "people": "people", "media": "items"}


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
    for a in compare["added"]:
        check_refs("compare added", a["sections"])
    for item in compare["dropped"]:
        item["url"] = cite_url(item["from"], item["cite"], prior)

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
        "## Sections",
        "",
    ]
    for s in core["sections"]:
        out.append(f"- Sec. {s['n']}. {s['h']} (pp. {s['p1']} to {s['p2']}): {s['plain']}")
    out += ["", "## Timeline", ""]
    for e in core["timeline"]:
        out.append(f"- {e['date']}: {e['title']}")
    return "\n".join(out) + "\n"


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
