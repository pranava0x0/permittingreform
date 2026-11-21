"""Claims in coverage, and the passages of the Senate-passed text to check them against.

data/claims.json ties a claim made in a coverage item (an X post, an article, a
statement) to the sections of the passed text (the substitute SA 6883 as
adopted, data/bill/substitute_sections.json) that a reader would compare it
with. The site never says whether a claim is right; it points at the text.

Everything here is deterministic: the same claim and the same bill text give
the same suggestions, the same located passages and the same subsection labels.

Used by tools/build.py (validation and cites) and tools/claim_sections.py (CLI).
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

import billtext

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CLAIMS = DATA / "claims.json"
PASSED = DATA / "bill/substitute_sections.json"
DIFF = DATA / "bill/substitute_diff.json"
SUB_PDF = "substitute.pdf"  # the passed text's print (tools/amendments.py SUB_PDF)

STOP = set("""a an the of and or to in on for by with as at from that this these those it its is are was were be been being
will would shall may can could should not no than then so such any all each every into under over about after before
bill act section sec says say said new also more most other which who whom whose what when where how their they them he she
his her we our you your i us federal government law laws provision provisions would also just only very""".split())

# Words a claim uses for a topic, and the words the bill text uses for it. A claim
# term on the left adds the bill terms on the right to the query. Lowercase.
TOPICS: list[tuple[str, tuple[str, ...]]] = [
    (r"\besa\b|endangered|species|wildlife|habitat", ("endangered species act", "consultation", "biological opinion", "species")),
    (r"lawsuit|sue\b|suing|litigat|court|judicial|statute of limitations|150[- ]day|standing", ("judicial review", "claim", "statute of limitations", "court", "vacatur", "remand")),
    (r"data cent", ("data center",)),
    (r"tribe|tribal|indian|sacred|section 106|\bnhpa\b|historic|preservation|thpo", ("historic preservation", "indian tribe", "tribal", "consultation", "historic property")),
    (r"transmission|power line|grid|interconnect", ("transmission", "interregional", "interconnection", "electric")),
    (r"ratepayer|cost|bill(s)? for|pay for|consumer", ("cost allocation", "costs", "ratepayer", "rates")),
    (r"\bnepa\b|environmental review|environmental impact|\beis\b|\bea\b", ("national environmental policy act", "environmental impact statement", "environmental assessment")),
    (r"deadline|page limit|clock|timeline|years?\b|days?\b", ("deadline", "page limit", "not later than", "days")),
    (r"categorical exclusion|exclusion|exempt", ("categorical exclusion", "exclusion", "exempt")),
    (r"clean water|wetland|section 401|\bcwa\b|water quality", ("clean water act", "water quality certification", "section 401")),
    (r"permit certainty|revok|revoc|rescind|issued permit|certainty", ("revoke", "suspend", "permit", "authorization")),
    (r"wind|solar|renewable|offshore", ("wind", "solar", "renewable", "offshore")),
    (r"pipeline|natural gas|\blng\b|oil", ("pipeline", "natural gas", "oil")),
    (r"mining|mineral|hardrock", ("mining", "mineral")),
    (r"nuclear|reactor", ("nuclear", "reactor")),
    (r"geothermal", ("geothermal",)),
    (r"public land|federal land|\bblm\b|forest", ("public land", "federal land", "national forest", "bureau of land management")),
    (r"ferc|commission", ("commission", "federal energy regulatory commission")),
    (r"state|county|counties|local", ("state", "county", "local", "political subdivision")),
]

SEC_MENTION = re.compile(r"\b(?:sec(?:tion)?\.?|§)\s*(\d{4})\b", re.I)
WORD = re.compile(r"[a-z0-9]+")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def passed_sections() -> dict[str, dict]:
    return {s["number"]: s for s in load(PASSED)["sections"]}


def words(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower()) if w not in STOP and len(w) > 2]


def query_terms(claim: str) -> tuple[list[str], list[str]]:
    """Single words and multi-word phrases for a claim."""
    low = claim.lower()
    singles = words(claim)
    phrases: list[str] = []
    for pat, terms in TOPICS:
        if re.search(pat, low):
            for t in terms:
                (phrases if " " in t else singles).append(t)
    return singles, phrases


def section_label(lines: list[list], loc: dict) -> str:
    """The enumerator path of the paragraph a passage starts in, e.g. "(b)(2)(A)".

    Built from billtext.paragraphs: the paragraph at or before the passage's first
    line, then the nearest earlier paragraph at each shallower level."""
    paras = billtext.paragraphs(lines)
    start = (loc["p1"], loc["l1"])
    at = None
    for i, p in enumerate(paras):
        if (p[0], p[1]) <= start:
            at = i
        else:
            break
    if at is None:
        return ""
    path: list[str] = []
    level = paras[at][2] + 1
    for p in reversed(paras[: at + 1]):
        if p[2] < level and p[2] > 0:
            m = billtext.ENUM_RE.match(billtext.norm(p[3]))
            if m:
                path.append("(" + m.group("tok") + ")")
                level = p[2]
        if level <= 1:
            break
    return "".join(reversed(path))


def locate(sec: dict, text: str) -> dict | None:
    return billtext.locate(sec["lines"], text)


def diff_rows() -> dict[str, dict]:
    """Passed-text section number -> its row in the substitute diff."""
    out = {}
    for r in load(DIFF)["rows"]:
        if r.get("new"):
            out[r["new"]["n"]] = r
    return out


def section_href(n: str, rows: dict[str, dict]) -> str:
    """Where the site shows section n of the passed text: the changes page when the
    substitute changed it, the bill page (same text) when it did not."""
    r = rows.get(n)
    if r and r["status"] != "unchanged":
        return "#/amendments/sec/" + r["id"]
    old = (r or {}).get("old") or {}
    return "#/bill/sec/" + (old.get("n") or n)


def resolve(claims: list[dict], media_urls: set[str], errors: list[str]) -> dict[str, list[dict]]:
    """Validate data/claims.json rows and return them by media URL, each review
    passage located in the passed text with its cite and subsection label."""
    secs = passed_sections()
    rows = diff_rows()
    seen: set[str] = set()
    by_url: dict[str, list[dict]] = {}
    for c in claims:
        where = f"claim {c.get('id')}"
        if c.get("id") in seen:
            errors.append(f"{where}: duplicate id")
        seen.add(c.get("id"))
        for field in ("id", "media_url", "speaker", "quote", "about"):
            if not str(c.get(field, "")).strip():
                errors.append(f"{where}: empty {field}")
        if c.get("media_url") not in media_urls:
            errors.append(f"{where}: media_url is not a coverage item: {c.get('media_url')}")
        if not c.get("review"):
            errors.append(f"{where}: names no passage to review")
        out_review = []
        for r in c.get("review", []):
            sec = secs.get(r.get("section"))
            if not sec:
                errors.append(f"{where}: section {r.get('section')} is not in the passed text")
                continue
            loc = locate(sec, r.get("text", ""))
            if not loc:
                errors.append(f"{where}: passage not found in section {r['section']}: {r.get('text', '')[:60]!r}")
                continue
            if loc["count"] != 1:
                errors.append(f"{where}: passage matches more than once in section {r['section']}; include more context")
                continue
            out_review.append({"n": r["section"], "h": sec["heading"], "at": section_label(sec["lines"], loc),
                               "t": r["text"], "c": [loc["p1"], loc["l1"], loc["p2"], loc["l2"]],
                               "href": section_href(r["section"], rows), "pdf": f"{SUB_PDF}#page={loc['p1']}",
                               **({"look": r["look"]} if r.get("look") else {})})
        by_url.setdefault(c.get("media_url"), []).append(
            {"id": c.get("id"), "speaker": c.get("speaker"), "quote": c.get("quote"), "about": c.get("about"), "review": out_review})
    return by_url


def _score(tokens: Counter, flat: str, singles: list[str], phrases: list[str], idf: dict[str, float]) -> float:
    s = 0.0
    for w in singles:
        if tokens.get(w):
            s += (1 + math.log(tokens[w])) * idf.get(w, 0.0)
    for p in phrases:
        k = flat.count(p)
        if k:
            s += (1 + math.log(k)) * 3.0
    return s


def suggest(claim: str, top: int = 3) -> list[dict]:
    """Rank passed-text sections for a claim; for each, the best paragraph as a
    candidate passage that occurs exactly once in the section."""
    secs = passed_sections()
    singles, phrases = query_terms(claim)
    docs = {n: Counter(words(s["heading"] + " " + s["heading"] + " " + s["text"])) for n, s in secs.items()}
    df = Counter(w for c in docs.values() for w in c)
    idf = {w: math.log(len(docs) / df[w]) for w in df}
    named = SEC_MENTION.findall(claim)
    ranked = []
    for n, s in secs.items():
        flat = (s["heading"] + " " + " ".join(billtext.norm(t) for _, _, t in s["lines"])).lower()
        score = _score(docs[n], flat, singles, phrases, idf) / math.log(10 + sum(docs[n].values()))
        head = Counter(words(s["heading"]))
        score += sum(1.0 for w in singles if head.get(w)) + sum(1.5 for p in phrases if p in s["heading"].lower())
        if n in named:
            score += 100
        ranked.append((round(score, 6), n))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    out = []
    for score, n in ranked[:top]:
        if score <= 0:
            break
        out.append({"section": n, "heading": secs[n]["heading"], "score": score, **best_passage(secs[n], singles, phrases, idf)})
    return out


def best_passage(sec: dict, singles: list[str], phrases: list[str], idf: dict[str, float]) -> dict:
    best = None
    for p in billtext.paragraphs(sec["lines"]):
        text = billtext.norm(p[3])
        sc = _score(Counter(words(text)), text.lower(), singles, phrases, idf)
        if best is None or sc > best[0]:
            best = (sc, text)
    if not best:
        return {}
    text = best[1]
    body = re.sub(r"^“?\([A-Za-z0-9]{1,8}\)\s*", "", text)
    span, loc = body, None
    for limit in range(220, len(body) + 80, 80):
        span = trim(body, limit)
        loc = locate(sec, span)
        if loc and loc["count"] == 1:
            break
    return {"text": span, "at": section_label(sec["lines"], loc) if loc else "", "unique": bool(loc and loc["count"] == 1)}


def trim(text: str, limit: int = 220) -> str:
    """Cut a paragraph to about `limit` characters at a word boundary, dropping a
    leading enumerator so the span reads as text."""
    t = re.sub(r"^“?\([A-Za-z0-9]{1,8}\)\s*", "", text)
    if len(t) <= limit:
        return t
    cut = t[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:—")
