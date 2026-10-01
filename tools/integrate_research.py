"""Turn the research agents' candidate files into the datasets the site ships.

  data/research/timeline.json -> data/timeline.json
  data/research/people.json   -> data/people.json
  data/research/media.json    -> data/media.json

Agents return candidates; this step is where they become records. It applies
the edits in data/curation.json, enforces the vocabulary (branches, sectors, stances, types, topics), drops rows that
lack a required field or a usable URL, removes duplicates, links timeline
events to bill sections, and reports every drop with its reason.

Exit codes: 0 wrote all three, 1 a file was missing or produced no rows.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/research"
OUT = ROOT / "data"

BRANCHES = {"executive", "agency", "congress_house", "congress_senate", "court", "states", "other"}
SECTORS = {"congress", "white_house", "agency", "court", "industry", "trade_association", "think_tank",
           "environmental_group", "labor", "state_local", "academic", "media"}
STANCES = {"supports", "opposes", "mixed", "neutral", "reporting"}
MEDIA_TYPES = {"gov_press_release", "gov_document", "news", "analysis", "org_statement", "social_x",
               "social_bluesky", "reddit", "youtube", "podcast", "conference", "court_filing"}
TOPIC_MAP = {
    "judicial-review": "courts", "litigation": "courts", "offshore-wind": "offshore",
    "speed-act": "congress", "senate-deal": "congress", "house": "congress",
    "permitting-council": None, "environmental-justice": None,
}
# Timeline events tied to the bill sections that respond to them.
EVENT_SECTIONS = {
    "seven-county": ["1110"],
    "revolution-wind": ["1401"],
    "empire-wind": ["1401"],
    "offshore-wind-stop-work": ["1401"],
    "five-offshore-wind": ["1401"],
    "wind-and-solar-decision": ["1402", "2213"],
    "wind-permitting-freeze": ["1402"],
    "wind-and-solar-permitting": ["1402"],
    "large-load": ["2107"],
    "ratepayer-protection": ["2107"],
    "data-center": ["2107", "2114"],
    "permitting-technology": ["1121"],
    "epermit": ["1121"],
    "ceq-interim-final-rule": ["1103"],
    "ceq-final-rule": ["1103"],
    "categorical-exclusion-guidance": ["1105", "1108"],
    "speed-act": ["1110", "1401"],
    "fiscal-responsibility-act": ["1106"],
    "energy-permitting-reform-act": ["2101", "2201"],
    "senate-leaders-release": ["1101"],
}
TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "zephr_sso_ott", "fbclid", "gclid"}


def log(msg: str) -> None:
    print(f"integrate: {msg}")


def clean_url(url: str) -> str | None:
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        return None
    parts = urlsplit(url)
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def url_key(url: str) -> str:
    parts = urlsplit(url)
    return (parts.netloc.lower().removeprefix("www.") + parts.path.rstrip("/") + ("?" + parts.query if parts.query else "")).lower()


def clean_text(value):
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, list):
        return [clean_text(v) for v in value if v not in (None, "", [], {})]
    if isinstance(value, dict):
        return {k: clean_text(v) for k, v in value.items() if v not in (None, "", [], {})}
    return value


def topics(raw: list[str], known: dict) -> list[str]:
    out: list[str] = []
    for t in raw or []:
        t = TOPIC_MAP.get(t, t)
        if t and t in known and t not in out:
            out.append(t)
    return out


def sources(raw: list[dict]) -> list[dict]:
    out = []
    for s in raw or []:
        url = clean_url(s.get("url", ""))
        if url:
            out.append({**s, "url": url})
    return out


def valid_date(d: str) -> bool:
    return bool(re.match(r"^20(2[3-9])-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$", d or ""))


def load(name: str, key: str) -> list[dict] | None:
    path = SRC / f"{name}.json"
    if not path.exists():
        log(f"{path.relative_to(ROOT)} is missing")
        return None
    rows = clean_text(json.loads(path.read_text(encoding="utf-8")))[key]
    extra = SRC / f"{name}_extra.json"  # rows the main session found after the agent sweep
    if extra.exists():
        rows += clean_text(json.loads(extra.read_text(encoding="utf-8")))[key]
    return curate(name, rows)


def curate(name: str, rows: list[dict]) -> list[dict]:
    """Apply data/curation.json: field overrides and drops, each with a stated reason."""
    path = ROOT / "data/curation.json"
    edits = json.loads(path.read_text(encoding="utf-8")).get(name, {}) if path.exists() else {}
    ids = {r.get("id") for r in rows}
    for rec_id in edits:
        if rec_id not in ids:
            log(f"{name}: curation entry {rec_id!r} matches no record (stale edit?)")
    out = []
    for r in rows:
        edit = edits.get(r.get("id"))
        if edit:
            if not edit.get("reason"):
                raise SystemExit(f"integrate: curation entry {r['id']!r} has no reason")
            if edit.get("drop"):
                log(f"{name}: dropped {r['id']} by curation: {edit['reason']}")
                continue
            r = {**r, **edit.get("set", {})}
            for field in edit.get("unset", []):
                r.pop(field, None)
        out.append(r)
    return out


def write(name: str, key: str, rows: list[dict]) -> None:
    path = OUT / f"{name}.json"
    payload = {"generated": "2026-10-01", key: rows}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"wrote {len(rows)} rows -> {path.relative_to(ROOT)}")


def timeline(known: dict) -> list[dict] | None:
    raw = load("timeline", "events")
    if raw is None:
        return None
    seen: set[str] = set()
    out = []
    for e in raw:
        missing = [k for k in ("id", "date", "title", "branch", "summary") if not e.get(k)]
        e["sources"] = sources(e.get("sources"))
        if missing or not valid_date(e.get("date", "")) or e.get("branch") not in BRANCHES or not e["sources"]:
            log(f"timeline: dropped {e.get('id') or e.get('title')!r}: missing={missing} branch={e.get('branch')!r} sources={len(e['sources'])}")
            continue
        if e["id"] in seen:
            log(f"timeline: dropped duplicate id {e['id']}")
            continue
        seen.add(e["id"])
        e["topics"] = topics(e.get("topics"), known)
        e["milestone"] = bool(e.get("milestone"))
        if e.get("quote"):
            q = e["quote"]
            q_url = clean_url(q.get("source_url", "")) or e["sources"][0]["url"]
            if q.get("text") and q.get("speaker"):
                e["quote"] = {"text": q["text"], "speaker": q["speaker"], "source_url": q_url}
            else:
                del e["quote"]
        secs: list[str] = []
        for needle, nums in EVENT_SECTIONS.items():
            if needle in e["id"]:
                for n in nums:
                    if n not in secs:
                        secs.append(n)
        if secs:
            e["sections"] = secs
        out.append(e)
    out.sort(key=lambda e: (e["date"], e["id"]))
    return out


def people(known: dict) -> list[dict] | None:
    raw = load("people", "people")
    if raw is None:
        return None
    seen: set[str] = set()
    out = []
    for p in raw:
        missing = [k for k in ("id", "name", "role", "sector", "stance", "position") if not p.get(k)]
        p["sources"] = sources(p.get("sources"))
        if missing or p.get("sector") not in SECTORS or p.get("stance") not in STANCES or not p["sources"]:
            log(f"people: dropped {p.get('name')!r}: missing={missing} sector={p.get('sector')!r} stance={p.get('stance')!r} sources={len(p['sources'])}")
            continue
        if p["id"] in seen:
            log(f"people: dropped duplicate id {p['id']}")
            continue
        seen.add(p["id"])
        if p["stance"] == "reporting":
            p["stance"] = "neutral"
        p["inside_government"] = bool(p.get("inside_government", p["sector"] in {"congress", "white_house", "agency", "court"}))
        if p.get("party") not in ("R", "D", "I"):
            p.pop("party", None)
        if p.get("social"):
            social = {k: clean_url(v) for k, v in p["social"].items() if k in ("x", "bluesky")}
            p["social"] = {k: v for k, v in social.items() if v}
            if not p["social"]:
                del p["social"]
        if p.get("quote"):
            q = p["quote"]
            q_url = clean_url(q.get("source_url", ""))
            if q.get("text") and q_url:
                p["quote"] = {"text": q["text"], "source_url": q_url, **({"date": q["date"]} if valid_date(q.get("date", "")) else {})}
            else:
                del p["quote"]
        out.append(p)
    return out


def media(known: dict) -> list[dict] | None:
    raw = load("media", "items")
    if raw is None:
        return None
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    out = []
    for it in raw:
        url = clean_url(it.get("url", ""))
        missing = [k for k in ("id", "date", "type", "outlet", "title") if not it.get(k)]
        if missing or not url or not valid_date(it.get("date", "")) or it.get("type") not in MEDIA_TYPES:
            log(f"media: dropped {it.get('id') or it.get('title')!r}: missing={missing} url={bool(url)} type={it.get('type')!r}")
            continue
        key = url_key(url)
        if it["id"] in seen_ids or key in seen_urls:
            log(f"media: dropped duplicate {it['id']}")
            continue
        seen_ids.add(it["id"])
        seen_urls.add(key)
        it["url"] = url
        it["stance"] = it.get("stance") if it.get("stance") in STANCES else "reporting"
        it["topics"] = topics(it.get("topics"), known)
        it["verified"] = bool(it.get("verified"))
        if it.get("quote") and not (it["quote"].get("text")):
            del it["quote"]
        out.append(it)
    out.sort(key=lambda it: (it["date"], it["id"]), reverse=True)
    return out


def main() -> int:
    known = json.loads((ROOT / "data/topics.json").read_text(encoding="utf-8"))
    rc = 0
    for name, key, fn in (("timeline", "events", timeline), ("people", "people", people), ("media", "items", media)):
        rows = fn(known)
        if not rows:
            log(f"{name}: no rows; nothing written")
            rc = 1
            continue
        write(name, key, rows)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
