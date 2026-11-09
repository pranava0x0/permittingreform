"""Bake the tracker's data into the static site.

Reads the source-of-truth files under data/ and writes (site/bill.pdf, the
same-origin copy that makes #page=N links work, is committed as is):
  site/data/core.js   window.PR_DATA  (summaries, comparison, positions issues, recent news)
  site/data/bill.js   window.PR_BILL  (full bill text as paragraphs with page and line cites)
  site/data/takes.js  window.PR_TAKES (outside readings; section pages load it on demand)
  site/data/news.js   window.PR_NEWS  (timeline, people, media; the News pages load it on demand)
  site/data/amend.js  window.PR_AMEND (the November 7 substitute against the September text, and
                      other amendments; the Amendments pages load it on demand)
  site/amendments.html the same, without JavaScript
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
import amendments  # noqa: E402
import billtext  # noqa: E402

ROOT = billtext.ROOT
DATA = ROOT / "data"
SITE = ROOT / "site"
SITE_URL = "https://pranava0x0.github.io/permittingreform/"
REPO_URL = "https://github.com/pranava0x0/permittingreform"
PDF_NAME = "bill.pdf"
# The date the datasets were last captured and checked. Bump on a data refresh, not on a rebuild.
DATA_AS_OF = "2026-11-09"

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


NEWS_KEYS = ("timeline", "people", "media")


def browser_core(core: dict) -> dict:
    """What core.js carries on every page. The outside readings (takes.js) and
    the timeline, people and media (news.js) load on demand; the Overview gets
    its short lists from "recent"."""
    out = {k: v for k, v in core.items() if k not in ("takes", "amend") and k not in NEWS_KEYS}
    out["amend_index"] = amendments.index(core.get("amend"))
    media = sorted(core["media"], key=lambda it: it["date"], reverse=True)[:6]
    marks = sorted((e for e in core["timeline"] if e.get("milestone")), key=lambda e: e["date"], reverse=True)[:6]
    out["recent"] = {
        "media": [{k: it[k] for k in ("url", "title", "outlet", "date")} for it in media],
        "milestones": [{k: e[k] for k in ("id", "date", "title")} for e in marks],
        "counts": {k: len(core[k]) for k in NEWS_KEYS},
        "positions": positions_summary(core),
    }
    return out


def positions_summary(core: dict) -> dict:
    """Counts for the Overview's link to the Positions page. Stances come from
    the people and groups tracked (one per voice; a media item's stance belongs
    to that item, not to a person); letters are media items with a letter."""
    stances = [p["stance"] for p in core["people"]]
    out = {k: stances.count(k) for k in ("supports", "opposes", "mixed")}
    out["letters"] = sum(1 for it in core["media"] if it.get("letter") and it["date"] >= core["meta"]["released"])
    return out


def browser_news(core: dict) -> dict:
    return {k: core[k] for k in NEWS_KEYS}


def cite(loc: dict) -> list:
    return [loc["p1"], loc["l1"], loc["p2"], loc["l2"]]


ROW_CITES = DATA / "bill/row_cites.json"


def row_claims(overview: dict, compare: dict, communities: dict | None, datacenters: dict | None) -> list[dict]:
    """Every sentence outside the section pages that says what the bill does,
    with the sections it rests on. Each must carry a passage from one of
    those sections (data/bill/row_cites.json, written by infer_check.py).

    Returns [{id, t (the sentence), sections, context, holder, key}]: holder[key]
    is the dict the page reads, and the build sets holder["ts"] to the
    sentences with their cites."""
    out: list[dict] = []

    def add(prefix: str, holder: dict, key: str, sections: list[str], context: str) -> None:
        if not sections or not holder.get(key):
            return
        sents = [s for para in billtext.sentence_paragraphs(holder[key]) for s in para]
        for i, s in enumerate(sents, 1):
            out.append({"id": f"{prefix}.s{i}", "t": s, "sections": sections, "context": context, "holder": holder, "key": key})

    for h in overview["headlines"]:
        add(f"hl.{h['id']}", h, "text", h["sections"], h["title"])
    for g in compare["groups"]:
        for r in g["rows"]:
            add(f"cmp.{r['id']}.senate", r["senate"], "text", r["senate"].get("sections", []), r["topic"])
    if compare.get("bills"):
        for r in compare["bills"]["rows"]:
            cell = r.get("senate") or {}
            add(f"dcb.{r['id']}", cell, "text", cell.get("sections", []), r["topic"])
    for group in compare.get("focused", []):
        add("focus." + group["id"], group, "baseline", [group["section"]], group["label"])
    for i, a in enumerate(compare.get("added", []), 1):
        add(f"add.{i}", a, "text", a["sections"], "New in this bill")
    for prefix, doc in (("com", communities), ("dc", datacenters)):
        for r in (doc or {}).get("rows", []):
            add(f"{prefix}.{r['id']}", r, "baaja", r["sections"], r["topic"])
    return out


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
    """Returns (core, paras, errors). Claims that still lack a bill passage are
    listed in core["checks"]["cites"]["gaps"]; main() fails on them, but
    infer_check.py, which fills them, can still run."""
    errors: list[str] = []
    gaps: list[str] = []
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
    # A claim the semantic check did not support shows no cite and blocks the
    # build, whatever passage is stored for it. "unanswered" means the model
    # gave no verdict, so the claim counts as unchecked, not flagged. A supported claim whose evidence
    # span was not word for word needs a passage like any other claim.
    inf_path = DATA / "checks/inference.json"
    flagged = {(r["id"], r["claim"]) for r in (load(inf_path)["results"] if inf_path.exists() else [])
               if r["verdict"] not in ("supported", "unanswered")}
    flagged_sec = {(cid.split(".")[0], claim) for cid, claim in flagged if re.match(r"^\d{4}\.[ks]\d+$", cid)}
    # A claim that the text is silent has no passage; it is covered once the
    # review supports it with no evidence span.
    absent = {(r["id"], r["claim"]) for r in (load(inf_path)["results"] if inf_path.exists() else [])
              if r["verdict"] == "supported" and not r["evidence"] and r["evidence_in_text"] and billtext.is_absence(r["claim"])}
    absent_sec = {(cid.split(".")[0], claim) for cid, claim in absent if re.match(r"^\d{4}\.[ks]\d+$", cid)}
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
        def cited(text: str, what: str) -> dict:
            item = {"t": text}
            if (n, text) in flagged_sec:
                gaps.append(f"section {n}: the semantic check flagged {what}: {text[:70]!r}")
                return item
            span = point_cites.get(n, {}).get(text)
            loc = billtext.locate(s["lines"], span) if span else None
            if loc:
                item["c"] = cite(loc)
            elif span:
                errors.append(f"section {n}: the passage cited for {what} is not in the section text: {span[:60]!r}")
            elif (n, text) in absent_sec:
                item["absent"] = True
            else:
                gaps.append(f"section {n}: no bill passage for {what}: {text[:70]!r}")
            return item

        points = [cited(text, f"key point {i}") for i, text in enumerate(a.get("key_points", []), 1)]
        summary = [[cited(t, "summary sentence") for t in para] for para in billtext.sentence_paragraphs(a.get("plain", ""))]
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
            "ps": summary,
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
    for g in compare.get("focused", []):
        check_refs("focused comparison " + g["id"], [g["section"]])
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

    # Data centers: computing loads, transmission rates and interconnection speed.
    dc_path = DATA / "datacenters.json"
    datacenters = load(dc_path) if dc_path.exists() else None
    if datacenters:
        gids = {g["id"] for g in datacenters["groups"]}
        for r in datacenters["rows"]:
            where = f"datacenters {r['id']}"
            if r["group"] not in gids:
                errors.append(f"{where}: unknown group {r['group']!r}")
            for w in r["who"]:
                if w not in datacenters["who"]:
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

    # Speed: what research found slows projects, the bill passages that reach
    # each cause, and outside readings of whether they help. The rows describe
    # research, not the bill, so the bill appears only as located passages.
    speed_path = DATA / "speed.json"
    speed = load(speed_path) if speed_path.exists() else None
    if speed:
        speed.pop("_about", None)
        for b in speed["blockers"]:
            where = f"speed {b['id']}"
            check_refs(where, b["sections"])
            if not b.get("evidence"):
                errors.append(f"{where}: no research evidence")
            for p in b.get("passages", []):
                sec = by_num.get(p["section"])
                loc = billtext.locate(sec["lines"], p["text"]) if sec else None
                if p["section"] not in b["sections"]:
                    errors.append(f"{where}: passage is from section {p['section']}, which the row does not name")
                elif not loc:
                    errors.append(f"{where}: passage not found in section {p['section']}: {p['text'][:60]!r}")
                elif loc["count"] != 1:
                    errors.append(f"{where}: passage matches more than once in section {p['section']}; include more context")
                else:
                    p["c"] = cite(loc)

    # Every sentence outside the section pages that says what the bill does
    # carries a passage from a section it cites.
    row_cites = load(ROW_CITES) if ROW_CITES.exists() else {}
    rows_cited = rows_absent = 0
    claims = row_claims(overview, compare, communities, datacenters)
    for rc in claims:
        item = {"t": rc["t"]}
        got = row_cites.get(rc["id"])
        if (rc["id"], f"[{rc['context']}] {rc['t']}") in flagged:
            gaps.append(f"{rc['id']}: the semantic check flagged {rc['t'][:70]!r}")
        elif got and got.get("claim") == rc["t"]:
            sec = by_num.get(got["section"])
            loc = billtext.locate(sec["lines"], got["text"]) if sec and got["section"] in rc["sections"] else None
            if loc:
                item["c"] = cite(loc)
                item["n"] = got["section"]
                rows_cited += 1
            else:
                errors.append(f"{rc['id']}: the passage cited is not in section {got['section']} or that section is not cited by the row: {got['text'][:60]!r}")
        elif (rc["id"], f"[{rc['context']}] {rc['t']}") in absent:
            item["absent"] = True
            rows_absent += 1
        else:
            gaps.append(f"{rc['id']}: no bill passage for {rc['t'][:70]!r}")
        rc["holder"].setdefault("ts", []).append(item)

    # Takes: outside readings of what a provision would do, each tied to the
    # bill passage it argues over.
    takes_path = DATA / "takes.json"
    takes = load(takes_path) if takes_path.exists() else {"sides": {}, "stances": {}, "takes": []}
    seen_ids: set[str] = set()
    for t in takes["takes"]:
        where = f"take {t.get('id')}"
        if t["id"] in seen_ids:
            errors.append(f"{where}: duplicate id")
        seen_ids.add(t["id"])
        if t["side"] not in takes["sides"]:
            errors.append(f"{where}: unknown side {t['side']!r}")
        if t["stance"] not in takes["stances"]:
            errors.append(f"{where}: unknown stance {t['stance']!r}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", t.get("date", "")):
            errors.append(f"{where}: date must be YYYY-MM-DD")
        for field in ("who", "url", "claim", "quote"):
            if not t.get(field, "").strip():
                errors.append(f"{where}: empty {field}")
        if not t["sections"]:
            errors.append(f"{where}: names no section")
        check_refs(where, t["sections"])
        p = t.get("passage")
        if p:
            sec = by_num.get(p["section"])
            loc = billtext.locate(sec["lines"], p["text"]) if sec else None
            if p["section"] not in t["sections"]:
                errors.append(f"{where}: passage is from section {p['section']}, which the take does not name")
            elif not loc:
                errors.append(f"{where}: passage not found in section {p['section']}: {p['text'][:60]!r}")
            elif loc["count"] != 1:
                errors.append(f"{where}: passage matches more than once in section {p['section']}; include more context")
            else:
                p["c"] = cite(loc)
    for sec in sections:
        n_takes = sum(1 for t in takes["takes"] if sec["n"] in t["sections"])
        if n_takes:
            sec["takes"] = n_takes

    extra = {}
    for name, key in OPTIONAL.items():
        path = DATA / f"{name}.json"
        extra[name] = load(path)[key] if path.exists() else []
    # Positions: the contested issues the Positions page groups voices under.
    # check_data.py validates its references.
    pos_path = DATA / "positions.json"
    positions = load(pos_path) if pos_path.exists() else {"issues": []}
    positions.pop("_about", None)
    # Disputed readings: the bill passages a question turns on, and the takes
    # that read them each way. A dispute about the bill as a whole (what
    # happens if it fails) has no passage and says why in its note.
    take_by_id = {t["id"]: t for t in takes["takes"]}
    for issue in positions["issues"]:
        for d in issue.get("disputes", []):
            where = f"positions {issue['id']} dispute {d.get('id')}"
            if not d.get("passages") and not d.get("note"):
                errors.append(f"{where}: names no bill passage and no note saying why")
            for p in d.get("passages", []):
                sec = by_num.get(p["section"])
                loc = billtext.locate(sec["lines"], p["text"]) if sec else None
                if not loc:
                    errors.append(f"{where}: passage not found in section {p['section']}: {p['text'][:60]!r}")
                elif loc["count"] != 1:
                    errors.append(f"{where}: passage matches more than once in section {p['section']}; include more context")
                else:
                    p["c"] = cite(loc)
            secs = {p["section"] for p in d.get("passages", [])}
            sides = d.get("readings", {})
            if not (sides.get("against") or sides.get("for")):
                errors.append(f"{where}: names no readings")
            for side, ids in sides.items():
                if side not in ("against", "for"):
                    errors.append(f"{where}: unknown side {side!r}")
                for tid in ids:
                    t = take_by_id.get(tid)
                    if not t:
                        errors.append(f"{where}: no take {tid!r}")
                    elif secs and not secs & set(t["sections"]):
                        errors.append(f"{where}: take {tid} names none of the sections {sorted(secs)}")
                    elif secs and not t.get("passage"):
                        # A reading of a specific clause shows the bill text it argues over (Codex, PR 8).
                        errors.append(f"{where}: take {tid} reads a specific clause but has no bill passage")
                    elif t["stance"] not in ({"supports"} if side == "for" else {"opposes", "concerns"}):
                        errors.append(f"{where}: take {tid} has stance {t['stance']!r}, which does not belong under {side!r}")
    for b in (speed or {}).get("blockers", []):
        for tid in b.get("readings", []):
            if tid not in take_by_id:
                errors.append(f"speed {b['id']}: no take {tid!r}")
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

    for it in extra["media"] + takes["takes"]:
        stamp(it)
    for b in (speed or {}).get("blockers", []):
        for ev in b.get("evidence", []):
            stamp(ev)
    for rec in extra["timeline"] + extra["people"]:
        for src in rec.get("sources", []):
            stamp(src)

    all_points = [p for sec in sections for p in sec["points"]]
    checks["points"] = {"total": len(all_points), "cited": sum(1 for p in all_points if "c" in p)}
    checks["takes"] = {"total": len(takes["takes"]), "sections": len({n for t in takes["takes"] for n in t["sections"]})}
    all_sents = [t for sec in sections for para in sec["ps"] for t in para]
    checks["cites"] = {
        "summary": {"total": len(all_sents), "cited": sum(1 for t in all_sents if "c" in t), "absent": sum(1 for t in all_sents if t.get("absent"))},
        "rows": {"total": len(claims), "cited": rows_cited, "absent": rows_absent},
        "gaps": gaps,
    }

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
        "datacenters": datacenters,
        "speed": speed,
        "positions": positions,
        "takes": takes,
        "timeline": extra["timeline"],
        "people": extra["people"],
        "media": extra["media"],
        "checks": checks,
        "amend": amendments.build(errors),
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
        f"- [{AMEND_TITLE}]({m['site_url']}amendments.html): {AMEND_DESCRIPTION}",
        f"- [Amendments JSON]({m['site_url']}data/amend.json): every section's status in the November 7 substitute, change notes with page-and-line cites in either PDF, word-level redlines, floor amendments and reactions with sources.",
        *[f"- [{title}]({m['site_url']}{page}.html): {description}" for page, (title, description) in READER_PAGES.items()],
        f"- [No-JavaScript section index]({m['site_url']}reading.html)",
        f"- [Full text and analysis]({m['site_url']}llms-full.txt): all sections, comparisons, timeline, people and media with citations.",
        f"- [Tracker JSON]({m['site_url']}data/core.json): the same data the browser renders, including check coverage.",
        f"- [Bill paragraph JSON]({m['site_url']}data/bill.json): section number to [printed page, line, indent level, text] arrays.",
        f"- [Timeline, people and media JSON]({m['site_url']}data/news.json): dated events, positions and coverage, each with its sources.",
        f"- [Outside readings JSON]({m['site_url']}data/takes.json): what named industry groups, advocates, lawyers and analysts say sections would do, each with its verbatim quote, source link and the bill passage it concerns.",
        "- Fetch sections/{number}.md for one section. Each file includes its summary with a page-and-line cite after every sentence, cited key points, quotes, outside readings of what the section would do (quoted from their sources), comparison notes and full statutory text.",
        "- Browser search: #/bill/search/{URL-encoded query}; section: #/bill/sec/{number}; passage: #/bill/sec/{number}/{page}-{line}; cited range: #/bill/sec/{number}/{page}-{line}-{page}-{line}. Fragment routes require JavaScript; use the Markdown or JSON endpoints for HTTP retrieval.",
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
            f"- [Where the two sides disagree]({m['site_url']}issues.html#debate): contested questions, each with the bill passage it turns on and critics' and supporters' readings quoted from their sources.",
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


def pdf_citation(base: str, c: list) -> str:
    """A printed page-and-line range as a Markdown link to that PDF page."""
    p1, l1, p2, l2 = c
    return f"[p. {p1}, line {l1} to p. {p2}, line {l2}]({base}bill.pdf#page={p1})"


def section_markdown(core: dict, paras: dict, sec: dict) -> str:
    base = core["meta"]["site_url"]

    def citation(c: list) -> str:
        return pdf_citation(base, c)

    out = [f"# Sec. {sec['n']}. {sec['h']}", "", "BAAJA draft released September 30, 2026. AI-assisted analysis; proposed changes.",
           "", review_coverage(core), "", f"[Official PDF]({core['meta']['source_pdf']}) · [Browser section]({base}#/bill/sec/{sec['n']})",
           "", "## Summary", ""]
    for para in sec["ps"]:
        out += [" ".join(t["t"] + (f" ({citation(t['c'])})" if t.get("c") else " (the text is silent on this; confirmed by the summary review)" if t.get("absent") else "") for t in para), ""]
    out += ["## Key points", ""]
    for point in sec["points"]:
        cite_md = citation(point["c"]) if point.get("c") else "the text is silent on this; confirmed by the summary review"
        out.append(f"- {point['t']} ({cite_md})")
    takes = [t for t in core["takes"]["takes"] if sec["n"] in t["sections"]]
    if takes:
        out += ["", "## What others say it would do", "",
                "Outside readings, quoted from their sources. These are claims about effects, not findings of this tracker.", ""]
        for t in takes:
            on = f" On the bill text at {citation(t['passage']['c'])}." if t.get("passage", {}).get("c") else ""
            out += [f"- **{t['who']}** ({core['takes']['sides'][t['side']]}; {core['takes']['stances'][t['stance']].lower()}): {t['claim']}",
                    f"  > {t['quote']}", f"  [{t['outlet']}, {t['date']}]({t['url']}).{on}"]
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


def md_cited(core: dict, holder: dict, field: str = "text") -> str:
    """A row's text with each sentence followed by its bill cite, for the agent exports."""
    if not holder.get("ts"):
        return holder[field]
    base = core["meta"]["site_url"]
    return " ".join(t["t"] + (f" (Sec. {t['n']}, {pdf_citation(base, t['c'])})" if t.get("c")
                              else " (the text is silent on this; confirmed by the summary review)" if t.get("absent") else "") for t in holder["ts"])


def disputes_markdown(core: dict) -> list[str]:
    """The Positions page's disputes as text: the question, the bill passages it
    turns on, then each side's readings in the sources' words."""
    take_by_id = {t["id"]: t for t in core["takes"]["takes"]}
    issues = [i for i in core["positions"]["issues"] if i.get("disputes")]
    if not issues:
        return []
    out = ["", "## Where the two sides disagree", "",
           "Each question quotes the bill, then what critics and supporters say it means, quoted from their sources. The tracker does not say which reading is right.", ""]
    for issue in issues:
        for d in issue["disputes"]:
            out += [f"### {issue['title']}: {d['question']}", ""]
            for ps in d.get("passages", []):
                cite_md = f", {pdf_citation(core['meta']['site_url'], ps['c'])}" if ps.get("c") else ""
                out.append(f"- Bill, [Sec. {ps['section']}]({core['meta']['site_url']}sections/{ps['section']}.md): \"{ps['text']}\"{cite_md}")
            if not d.get("passages") and d.get("note"):
                out.append(f"- {d['note']}")
            for key, label in (("against", "Critics"), ("for", "Supporters")):
                takes = [take_by_id[i] for i in d.get("readings", {}).get(key, []) if i in take_by_id]
                if not takes:
                    out.append(f"- {label}: none found yet.")
                for t in takes:
                    out.append(f"- {label}: **{t['who']}** ({core['takes']['stances'][t['stance']].lower()}), [{t['outlet']}, {t['date']}]({t['url']}): \"{t['quote']}\"")
            out.append("")
    return out


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
                out.append(f"- {key}: {md_cited(core, cell)}")
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
                out.append(f"- {v['label']}: {md_cited(core, cell)}")
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
                    f"- BAAJA: {md_cited(core, row, 'baaja')}",
                    "- Bill: " + ", ".join(f"[{n}]({core['meta']['site_url']}sections/{n}.md)" for n in row.get("sections", []))]
            if row.get("quote"):
                where = f" (Sec. {row['quote_section']})" if row.get("quote_section") else ""
                cite = f", {pdf_citation(core['meta']['site_url'], row['c'])}" if row.get("c") else ""
                out.append(f"- Quote{where}: \"{row['quote']}\"{cite}")
            out.append("")
    dc = core.get("datacenters")
    if dc:
        out += ["", "## Data centers: computing loads, transmission rates and speed", "", dc["intro"], ""]
        for row in dc["rows"]:
            who = ", ".join(dc["who"].get(w, w) for w in row["who"])
            out += [f"### {row['topic']}", "", f"- Effect: {row['effect']}; affects: {who}",
                    f"- Now: {row['now']}" + (f" Source: [{row['now_cite']}]({row['now_url']})" if row.get("now_url") else ""),
                    f"- BAAJA: {md_cited(core, row, 'baaja')}",
                    "- Bill: " + ", ".join(f"[{n}]({core['meta']['site_url']}sections/{n}.md)" for n in row.get("sections", []))]
            if row.get("quote"):
                where = f" (Sec. {row['quote_section']})" if row.get("quote_section") else ""
                cite = f", {pdf_citation(core['meta']['site_url'], row['c'])}" if row.get("c") else ""
                out.append(f"- Quote{where}: \"{row['quote']}\"{cite}")
            out.append("")
    sp = core.get("speed")
    if sp:
        out += ["", "## What slows projects: research on causes of delay", "", sp["intro"], ""]
        takes = {t["id"]: t for t in core["takes"]["takes"]}
        for b in sp["blockers"]:
            out += [f"### {b['title']}", "", f"- Headline: {b['headline']}"]
            for ev in b["evidence"]:
                out.append(f"- {ev['finding']} \"{ev['quote']}\" Source: [{ev['org']}, {ev['title']}]({ev['url']}) ({ev['date']}; data: {ev.get('period', 'n/a')})")
            if b.get("disagreement"):
                out.append(f"- Where studies differ: {b['disagreement']}")
            for ps in b.get("passages", []):
                cite = f", {pdf_citation(core['meta']['site_url'], ps['c'])}" if ps.get("c") else ""
                out.append(f"- Bill text (Sec. {ps['section']}{cite}): \"{ps['text']}\"")
            out.append("- Bill: " + (", ".join(f"[{n}]({core['meta']['site_url']}sections/{n}.md)" for n in b["sections"]) or "no section mapped"))
            for tid in b.get("readings", []):
                t = takes[tid]
                out.append(f"- Reading, {t['who']} ({core['takes']['stances'][t['stance']].lower()}): {t['claim']} [{t['outlet']}]({t['url']})")
            out.append("")
    for g in core["compare"].get("focused", []):
        out += ["", "## " + g["label"], "", g["question"], "",
                f"BAAJA §{g['section']}: {md_cited(core, g, 'baseline')}"]
        out += [f"- {e['label']}: {e['text']} [{e['cite']}]({e['url']})" for e in g["entries"]]
    out += disputes_markdown(core)
    out += ["", "## Added and dropped provisions", "", "```json", json.dumps({k: core["compare"][k] for k in ("added", "dropped")}, ensure_ascii=False), "```", ""]
    for label, rows in (("Timeline", core["timeline"]), ("People", core["people"]), ("Media", core["media"])):
        out += ["", f"## {label}", ""]
        for row in rows:
            # JSON preserves all provenance, position tags and conditional fields.
            out += ["```json", json.dumps(row, ensure_ascii=False), "```", ""]
    return "\n".join(out) + "\n"


READER_PAGES = {
    "comparisons": ("Data center and digital permitting bills compared", "Compare BAAJA with data center siting and disclosure proposals, current E-NEPA law and the House and Senate ePermit bills."),
    "issues": ("Key issues in permitting reform", "What S. 5653 would change, the bill sections behind each provision, and how supporters and critics read them."),
    "timeline": ("Permitting reform timeline", "Dated legislative, legal and agency events, with source records for each event."),
    "coverage": ("Permitting reform news and coverage", "Reporting, analysis and statements about the permitting bill, with publication dates and links to the originals."),
}


def reader_html(core: dict, page: str) -> str:
    esc = html.escape

    def link(url, label):
        return f'<a href="{esc(url)}">{esc(label)}</a>'

    title, description = READER_PAGES[page]
    route = {"coverage": "media", "comparisons": "compare"}.get(page, page)
    nav = [link("index.html", "Overview"), link("reading.html", "Bill")]
    nav.extend(link(key + ".html", name) for key, name in (("issues", "Key issues"), ("timeline", "Timeline"), ("coverage", "Coverage")))
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           f'<title>{esc(title)} · BAAJA (S. 5653)</title><meta name="description" content="{esc(description)}">',
           f'<link rel="canonical" href="{SITE_URL}{page}.html"><link rel="stylesheet" href="styles.css">',
           '</head><body><main><nav aria-label="Tracker pages">' + ' · '.join(nav) + '</nav>',
           f'<h1>{esc(title)}</h1><p>{esc(description)}</p>',
           f'<p>{esc(core["meta"]["short_title"])} · Updated {esc(core["meta"]["as_of"])} · ' +
           link("index.html#/" + route, "Open interactive view") + '</p>']
    if page == "comparisons":
        for group in core["compare"]["focused"]:
            out.append(f'<section id="{esc(group["id"])}"><h2>{esc(group["label"])}</h2><p>{esc(group["question"])}</p>')
            out.append(f'<h3>BAAJA · Sec. {esc(group["section"])}</h3>')
            for sentence in group["ts"]:
                c = sentence["c"]
                out.append('<p>' + esc(sentence["t"]) + ' ' + link(f'bill.pdf#page={c[0]}', f'p. {c[0]}, line {c[1]} to p. {c[2]}, line {c[3]}') + '</p>')
            for entry in group["entries"]:
                out.append(f'<h3>{esc(entry["label"])}</h3><p>{esc(entry["text"])} ' + link(entry["url"], entry["cite"]) + '</p>')
            out.append('</section>')
    elif page == "issues":
        out.append('<p>Jump to: ' + ' · '.join(link("#" + key, name) for key, name in
                   (("datacenters", "Data centers"), ("speed", "Project delays"), ("communities", "Communities"), ("debate", "Debate"))) + '</p>')
        out.append('<h2>What would the bill change?</h2>')
        for h in core["overview"]["headlines"]:
            out.append(f'<h3>{esc(h["title"])}</h3>')
            for sentence in h["ts"]:
                start, line, end, last = sentence["c"]
                cite = link(f'bill.pdf#page={start}', f'Bill p. {start}, line {line} to p. {end}, line {last}')
                out.append(f'<p>{esc(sentence["t"])} {cite}</p>')
        for key, label in (("datacenters", "Data centers"), ("speed", "Project delays"), ("communities", "Communities")):
            guide = core[key]
            out.append(f'<h2 id="{key}">{label}</h2><p>{esc(guide["intro"])}</p>')
            if key == "speed":
                for blocker in guide["blockers"]:
                    out.append(f'<h3>{esc(blocker["title"])}</h3>')
                    for evidence in blocker["evidence"]:
                        out.append('<p>' + esc(evidence["finding"]) + ' ' + link(evidence["url"], evidence["org"]) + '</p>')
            else:
                for row in guide["rows"]:
                    refs = " · ".join(link(f'sections/{n}.md', f'Sec. {n}') for n in row["sections"])
                    out.append(f'<h3>{esc(row["topic"])}</h3><p>{esc(row["baaja"])} {refs}</p>')
        out.append('<h2 id="debate">Where do supporters and critics disagree?</h2>')
        takes = {t["id"]: t for t in core["takes"]["takes"]}
        for issue in core["positions"]["issues"]:
            for dispute in issue.get("disputes", []):
                out.append(f'<section><h3>{esc(dispute["question"])}</h3>')
                for passage in dispute.get("passages", []):
                    sec = passage["section"]
                    out.append('<p>' + link(f'sections/{sec}.md', f'Bill section {sec}') + ': “' + esc(passage["text"]) + '”</p>')
                if dispute.get("note"):
                    out.append('<p>' + esc(dispute["note"]) + '</p>')
                for side, label in (("against", "Critics"), ("for", "Supporters")):
                    readings = dispute.get("readings", {}).get(side, [])
                    if not readings:
                        out.append(f"<p>{label}: no reading recorded for this question.</p>")
                    for take_id in readings:
                        take = takes[take_id]
                        out.append('<p>' + label + ' · ' + link(take["url"], take["who"]) + ' (' + esc(take["date"]) + '): “' + esc(take["quote"]) + '”</p>')
                out.append('</section>')
    else:
        items = core["media" if page == "coverage" else "timeline"]
        for row in sorted(items, key=lambda r: r["date"], reverse=True):
            refs = [link(row["url"], row["outlet"])] if page == "coverage" else [link(s["url"], s.get("title") or s.get("publisher") or s["url"]) for s in row["sources"]]
            out.append(f'<article id="{esc(row["id"])}"><h2>{esc(row["title"])}</h2><time datetime="{esc(row["date"])}">{esc(row["date"])}</time>'
                       f'<p>{esc(row["summary"])}</p><p>{" · ".join(refs)}</p></article>')
    return '\n'.join(out + ['</main></body></html>']) + '\n'


AMEND_TITLE = "Amendments to the permitting bill"
AMEND_DESCRIPTION = ("What the November 7 substitute changes in each section of the September 30 text, with page and line cites "
                     "in both PDFs, other amendments filed or announced, and who has said they support or oppose them.")
AMEND_STATUS = {"edited": "Edited", "new": "New", "dropped": "Dropped", "moved": "Renumbered", "unchanged": "Unchanged"}


def amendments_html(core: dict) -> str:
    """The Amendments view as plain HTML for readers without JavaScript and for crawlers."""
    esc = html.escape
    a = core["amend"]
    old_pdf, new_pdf = PDF_NAME, a["new"]["pdf"]

    def link(url, label):
        return f'<a href="{esc(url)}">{esc(label)}</a>'

    def pcite(p):
        pdf, label = (new_pdf, "Nov. 7") if p["side"] == "new" else (old_pdf, "Sept. 30")
        c = p["c"]
        return link(f"{pdf}#page={c[0]}", f"{label} p. {c[0]}, line {c[1]}")

    sub = a["substitute"]
    nav = [link("index.html", "Overview"), link("reading.html", "Bill"), link("issues.html", "Key issues"),
           link("timeline.html", "Timeline"), link("coverage.html", "Coverage")]
    c = a["counts"]
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           f'<title>{esc(AMEND_TITLE)} · BAAJA (S. 5653)</title><meta name="description" content="{esc(AMEND_DESCRIPTION)}">',
           f'<link rel="canonical" href="{SITE_URL}amendments.html"><link rel="stylesheet" href="styles.css">',
           '</head><body><main><nav aria-label="Tracker pages">' + ' · '.join(nav) + '</nav>',
           f'<h1>{esc(AMEND_TITLE)}</h1><p>{esc(AMEND_DESCRIPTION)}</p>',
           f'<p>Updated {esc(a["as_of"])} · ' + link("index.html#/amendments", "Open interactive view") + '</p>',
           '<p>Jump to: ' + ' · '.join(link("#" + k, v) for k, v in (("substitute", "Substitute"), ("floor", "Other amendments"), ("reactions", "Reactions"))) + '</p>',
           f'<h2 id="substitute">{esc(sub["title"])}</h2>',
           f'<p>{esc(sub["summary"])} ' + ' · '.join(link(s["url"], s["label"]) for s in sub["links"]) + '</p>',
           f'<p>{a["old"]["pages"]} pages and {a["old"]["sections"]} sections on September 30; {a["new"]["pages"]} pages and {a["new"]["sections"]} sections on November 7. '
           f'{c["edited"]} sections edited, {c["new"]} added, {c["dropped"]} dropped, {c["moved"]} renumbered, {c["unchanged"]} unchanged.</p>']
    group = None
    for r in a["rows"]:
        if r["status"] == "unchanged":
            continue
        g = (r["div"], r["ti"])
        if g != group:
            group = g
            label = f'{r["div"]}, {r["ti"]}: {r["tih"]}' if r["ti"] else f'{r["div"]}: {r["divh"]}'
            out.append(f'<h3>{esc(label.title())}</h3>')
        was = ""
        if "old" in r and "new" in r and (r["old"]["n"] != r["new"]["n"] or r["old"]["h"] != r["new"]["h"]):
            was = f' (September 30: Sec. {esc(r["old"]["n"])}. {esc(r["old"]["h"])})'
        out.append(f'<section id="sec-{esc(r["id"])}"><h4>Sec. {esc(r["n"])}. {esc(r["h"])} · {AMEND_STATUS[r["status"]]}{was}</h4><ul>')
        for p in r["points"]:
            out.append(f'<li>{esc(p["t"])} {pcite(p)}</li>')
        out.append('</ul></section>')
    unchanged = [r for r in a["rows"] if r["status"] == "unchanged"]
    out.append(f'<p>Unchanged ({len(unchanged)}): ' + ', '.join(link(f'sections/{r["n"]}.md', "Sec. " + r["n"]) for r in unchanged) + '</p>')
    out.append('<h2 id="floor">Other amendments</h2>')
    if not a["floor"]:
        out.append('<p>None filed or announced in the sources checked.</p>')
    for f in a["floor"]:
        out.append(f'<section><h3>{esc(f.get("number") or "Unnumbered")} · {esc(f["sponsor"])}</h3>'
                   f'<p>{esc(f["summary"])} Status: {esc(f["status"])}, {esc(f["date"])}.</p>')
        for s in f["sources"]:
            out.append(f'<p>“{esc(s["quote"])}” {link(s["url"], s["publisher"])}</p>')
        for st in f.get("positions", []):
            out.append(f'<p>{esc(st["who"])} ({esc(st["stance"])}): “{esc(st["quote"])}” {link(st["url"], st["publisher"])}</p>')
        out.append('</section>')
    out.append('<h2 id="reactions">Reactions to the substitute</h2>')
    for st in ("supports", "opposes", "mixed", "undecided"):
        rows = [x for x in a["reactions"] if x["stance"] == st]
        if not rows:
            continue
        out.append(f'<h3>{st.capitalize()}</h3>')
        for x in rows:
            src = x["sources"][0]
            out.append(f'<p><strong>{esc(x["who"])}</strong>, {esc(x["role"])}, {esc(x["date"])}: “{esc(src["quote"])}” {link(src["url"], src["publisher"])}</p>')
    return "\n".join(out + ['</main></body></html>']) + "\n"


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
           '<p><a href="index.html">Interactive tracker</a> · <a href="amendments.html">November 7 substitute and amendments</a> · <a href="llms.txt">Agent index</a> · <a href="llms-full.txt">Full text and analysis</a> · <a href="data/core.json">Tracker JSON</a></p>']
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
    gaps = core["checks"]["cites"]["gaps"]
    if gaps:
        for g in gaps[:40]:
            print(f"build: {g}", file=sys.stderr)
        print(f"build: {len(gaps)} claim(s) about the bill carry no bill passage; run tools/infer_check.py, "
              "then fix or reword any claim it flags. Nothing written.", file=sys.stderr)
        return 1
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    (SITE / "data/core.js").write_text(dump_js("PR_DATA", browser_core(core)), encoding="utf-8")
    (SITE / "data/bill.js").write_text(dump_js("PR_BILL", paras), encoding="utf-8")
    (SITE / "data/takes.js").write_text(dump_js("PR_TAKES", core["takes"]), encoding="utf-8")
    (SITE / "data/news.js").write_text(dump_js("PR_NEWS", browser_news(core)), encoding="utf-8")
    (SITE / "data/amend.js").write_text(dump_js("PR_AMEND", core["amend"]), encoding="utf-8")
    (SITE / "amendments.html").write_text(amendments_html(core), encoding="utf-8")
    (SITE / "llms.txt").write_text(llms_txt(core), encoding="utf-8")
    (SITE / "llms-full.txt").write_text(llms_full(core, paras), encoding="utf-8")
    (SITE / "reading.html").write_text(reading_html(core), encoding="utf-8")
    for page in READER_PAGES:
        (SITE / f"{page}.html").write_text(reader_html(core, page), encoding="utf-8")
    # The home page's JSON-LD dateModified follows the data, not a hand edit (it sat at Oct 2 after
    # an Oct 20 refresh). A pattern that stops matching is an error, never a silent no-op.
    index = SITE / "index.html"
    page = index.read_text(encoding="utf-8")
    stamped, n = re.subn(r'("dateModified":")\d{4}-\d{2}-\d{2}(")', r"\g<1>" + DATA_AS_OF + r"\g<2>", page)
    if n != 1:
        raise SystemExit(f"build: expected one JSON-LD dateModified in site/index.html, found {n}")
    summary, upcoming = core["overview"]["summary"], core["overview"].get("next")
    content = [f'<h1>{html.escape(core["meta"]["short_title"])}</h1>']
    for record in (summary, upcoming):
        if not record:
            continue
        source = record["source"]
        date = (html.escape(record["date"]) + ": ") if record.get("date") else ""
        content.append(f'<p>{date}{html.escape(record["text"])} <a href="{html.escape(source["url"])}">{html.escape(source["label"])}</a></p>')
    stamped, count = re.subn(r'(<!-- static overview -->).*?(<!-- /static overview -->)',
                             lambda m: m[1] + "\n".join(content) + m[2], stamped, flags=re.S)
    if count != 1:
        raise SystemExit("build: missing static overview markers")
    if stamped != page:
        index.write_text(stamped, encoding="utf-8")
    for name, data in (("core", browser_core(core)), ("bill", paras), ("takes", core["takes"]), ("news", browser_news(core)), ("amend", core["amend"])):
        (SITE / f"data/{name}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (SITE / "sections").mkdir(exist_ok=True)
    for sec in core["sections"]:
        (SITE / f"sections/{sec['n']}.md").write_text(section_markdown(core, paras, sec), encoding="utf-8")
    (SITE / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
                                    "\n".join(f"<url><loc>{SITE_URL}{path}</loc></url>" for path in
                                              ("", "reading.html", "amendments.html", *(page + ".html" for page in READER_PAGES), "llms.txt", "llms-full.txt", *(f"sections/{s['n']}.md" for s in core["sections"]))) + "\n</urlset>\n", encoding="utf-8")
    if not (SITE / PDF_NAME).exists():
        print(f"build: site/{PDF_NAME} is missing; download it from {core['meta']['source_pdf']}", file=sys.stderr)
        return 1
    m = core["meta"]
    print(
        f"build: {m['sections']} sections, {m['paragraphs']} paragraphs, {m['quotes']} quotes, "
        f"{sum(len(g['rows']) for g in core['compare']['groups'])} comparison rows, "
        f"{len(core['timeline'])} events, {len(core['people'])} people, {len(core['media'])} media items -> site/data/"
    )
    for name in ("core.js", "bill.js", "takes.js", "news.js", "amend.js"):
        print(f"build:   site/data/{name} {(SITE / 'data' / name).stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
