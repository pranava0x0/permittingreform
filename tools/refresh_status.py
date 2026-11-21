"""What changed on the floor since the last refresh: one deterministic read of every source.

  python3 tools/refresh_status.py            # report; exit 10 if anything touches the bill, 0 if not, 2 on fetch failure
  python3 tools/refresh_status.py --write    # also record the newest roll calls seen in data/research/floor_state.json
  python3 tools/refresh_status.py --json     # the report as JSON

Reads, in order (all answer scripts; REFRESH.md has the history of each route):
  Senate roll calls  senate.gov roll-call XML, numbers after floor_state.senate_last (a page with
                     no <vote_result> is "not posted yet", not a vote)
  House roll calls   clerk.house.gov roll XML, numbers after floor_state.house_last
  Congressional Record  govinfo CREC mods.xml for each day from floor_state.checked to today;
                     granule titles naming the bill (BILL_TITLES)
  House floor        docs.house.gov/floor week page for this week and next; lines naming H.R. 2347
  Senate floor log   dailypress.senate.gov home page with a cache-busting query; lines naming the
                     bill that are not in floor_state.floor_log_seen count as new

It reports; it never edits site data. A person records votes with tools/roll_call.py and
writes the overview, timeline and votes rows from the primary pages it lists.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data/research/floor_state.json"
UA = {"User-Agent": "Mozilla/5.0 (permitting-tracker refresh probe)"}
BILL = re.compile(r"H\.?\s?R\.?\s?2347|\bS\.?\s?5653\b|permitting|affordability and jobs|BAAJA", re.I)
BILL_TITLES = re.compile(r"2347|PERMITTING|AFFORDABILITY AND JOBS|SURVIVOR JUSTICE TAX PREVENTION", re.I)
SENATE_XML = "https://www.senate.gov/legislative/LIS/roll_call_votes/vote1192/vote_119_2_{n:05d}.xml"
HOUSE_XML = "https://clerk.house.gov/evs/2026/roll{n:03d}.xml"
CREC_MODS = "https://www.govinfo.gov/metadata/pkg/CREC-{d}/mods.xml"
HOUSE_FLOOR = "https://docs.house.gov/floor/Default.aspx?date={d}"
DAILYPRESS = "https://www.dailypress.senate.gov/?nc={t}"


def fetch(url: str, timeout: int = 30) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, f"{type(e).__name__}: {e}"


def unpublished(status: int) -> bool:
    """A roll number with no vote yet: 404, or the Senate's 200 'Roll Call Vote
    Unavailable' page. Anything else (429, 5xx, a network error) is a failed check."""
    return status in (200, 404)


def tag(xml: str, name: str) -> str:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", xml, re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else ""


def senate(after: int, errors: list[str]) -> list[dict]:
    out = []
    n = after + 1
    misses = 0
    while misses < 2 and n < after + 60:
        status, xml = fetch(SENATE_XML.format(n=n))
        if status != 200 or "<vote_result>" not in xml:
            if not unpublished(status):
                errors.append(f"{SENATE_XML.format(n=n)}: HTTP {status} {xml[:80]}".strip())
                break  # stop here so --write cannot advance past a roll that was never read
            misses += 1
            n += 1
            continue
        misses = 0
        doc = " ".join(tag(xml, t) for t in ("document_name", "document_title", "amendment_number", "vote_question_text"))
        out.append({"number": n, "date": tag(xml, "vote_date"), "question": tag(xml, "vote_question_text"),
                    "result": tag(xml, "vote_result"), "count": f'{tag(xml, "yeas")}-{tag(xml, "nays")}',
                    "bill": bool(BILL.search(doc)), "url": SENATE_XML.format(n=n)})
        n += 1
    return out


def house(after: int, errors: list[str]) -> list[dict]:
    out = []
    n = after + 1
    misses = 0
    while misses < 2 and n < after + 120:
        status, xml = fetch(HOUSE_XML.format(n=n))
        if status != 200 or "<vote-result>" not in xml:
            if not unpublished(status):
                errors.append(f"{HOUSE_XML.format(n=n)}: HTTP {status} {xml[:80]}".strip())
                break  # stop here so --write cannot advance past a roll that was never read
            misses += 1
            n += 1
            continue
        misses = 0
        legis = tag(xml, "legis-num")
        q = tag(xml, "vote-question")
        desc = tag(xml, "vote-desc")
        out.append({"number": n, "date": tag(xml, "action-date"), "legis": legis, "question": q, "desc": desc,
                    "result": tag(xml, "vote-result"),
                    "count": f'{tag(xml, "yea-total")}-{tag(xml, "nay-total")}',
                    "bill": bool(re.search(r"H R 2347", legis) or BILL.search(desc)), "url": HOUSE_XML.format(n=n)})
        n += 1
    return out


def record(since: dt.date, today: dt.date, errors: list[str]) -> list[dict]:
    out = []
    d = since
    while d <= today:
        status, xml = fetch(CREC_MODS.format(d=d.isoformat()), timeout=60)
        if status == 200 and xml:
            for m in re.finditer(r"<relatedItem[^>]*ID=\"id-(CREC-[^\"]+)\"[^>]*>(.*?)</relatedItem>", xml, re.S):
                title = tag(m.group(2), "title")
                if BILL_TITLES.search(title):
                    gid = m.group(1)
                    out.append({"date": d.isoformat(), "granule": gid, "title": title,
                                "url": f"https://www.govinfo.gov/content/pkg/CREC-{d.isoformat()}/html/{gid}.htm"})
        elif status not in (404, 200):
            errors.append(f"Record {d}: HTTP {status}")
        d += dt.timedelta(days=1)
    return out


def house_floor(today: dt.date, errors: list[str]) -> list[dict]:
    out = []
    monday = today - dt.timedelta(days=today.weekday())
    for wk in (monday, monday + dt.timedelta(days=7)):
        url = HOUSE_FLOOR.format(d=wk.strftime("%Y%m%d"))
        status, page = fetch(url)
        if status != 200:
            errors.append(f"House floor {wk}: HTTP {status}")
            continue
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
        hits = sorted({text[max(0, m.start() - 160): m.end() + 200].strip() for m in re.finditer(r"H\.R\. 2347", text)})
        out.append({"week_of": wk.isoformat(), "url": url, "mentions": hits,
                    "suspension": "Suspension" in text, "rule": bool(re.search(r"pursuant to a rule|Rule", text))})
    return out


def floor_log(errors: list[str]) -> dict:
    url = DAILYPRESS.format(t=int(time.time()))
    status, page = fetch(url)
    if status != 200:
        errors.append(f"Senate floor log: HTTP {status}")
        return {"url": url, "lines": []}
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
    # One entry per timestamp ("2:25 p.m. Senator Lankford spoke on permitting reform."), so an
    # entry reads the same on every run and floor_log_seen can tell new ones from old.
    entries = re.split(r"(?=\b\d{1,2}:\d{2} [ap]\.m\. )", text)
    lines = sorted({e.strip()[:400] for e in entries if re.match(r"\d{1,2}:\d{2} [ap]\.m\. ", e) and BILL.search(e)})
    convene = re.search(r"(?:convene|adjourned until)[^<]{0,120}?(?:a\.m\.|p\.m\.|noon)", text, re.I)
    return {"url": url, "lines": lines, "next": convene.group(0) if convene else ""}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--today", help="YYYY-MM-DD, for tests")
    a = ap.parse_args()
    state = json.loads(STATE.read_text()) if STATE.exists() else {"senate_last": 270, "house_last": 327, "checked": "2026-11-19"}
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    errors: list[str] = []
    rep = {
        "state": state,
        "senate": senate(state["senate_last"], errors),
        "house": house(state["house_last"], errors),
        "record": record(dt.date.fromisoformat(state["checked"]), today, errors),
        "house_floor": house_floor(today, errors),
        "senate_floor": floor_log(errors),
        "errors": errors,
    }
    seen_log = set(state.get("floor_log_seen", []))
    rep["senate_floor"]["new"] = [x for x in rep["senate_floor"]["lines"] if x not in seen_log]
    touches = (any(r["bill"] for r in rep["senate"] + rep["house"]) or rep["record"]
               or any(w["mentions"] for w in rep["house_floor"]) or rep["senate_floor"]["new"])
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    else:
        print(f"since: Senate roll {state['senate_last']}, House roll {state['house_last']}, Record {state['checked']}")
        for r in rep["senate"]:
            print(f"  Senate {r['number']} {r['date']}: {r['question']} | {r['result']} {r['count']}{'  << BILL' if r['bill'] else ''}")
        for r in rep["house"]:
            print(f"  House {r['number']} {r['date']}: {r['legis']} {r['question']} | {r['result']} {r['count']}{'  << BILL' if r['bill'] else ''}")
        for g in rep["record"]:
            print(f"  Record {g['date']} {g['granule']}: {g['title']}")
        for w in rep["house_floor"]:
            print(f"  House floor week of {w['week_of']}: {len(w['mentions'])} mention(s) of H.R. 2347 {w['url']}")
            for m in w["mentions"]:
                print(f"    ... {m}")
        sf = rep["senate_floor"]
        print(f"  Senate floor log: {len(sf['lines'])} line(s) on the bill, {len(sf['new'])} new since the last --write; {sf.get('next', '')}")
        for x in sf["new"]:
            print(f"    ... {x}")
        for e in errors:
            print(f"  FETCH ERROR: {e}")
        print("touches the bill: " + ("yes" if touches else "no"))
    if a.write and not errors:
        new = {"senate_last": max([state["senate_last"]] + [r["number"] for r in rep["senate"]]),
               "house_last": max([state["house_last"]] + [r["number"] for r in rep["house"]]),
               "checked": today.isoformat(),
               "floor_log_seen": sorted(set(state.get("floor_log_seen", [])) | set(rep["senate_floor"]["lines"]))}
        STATE.write_text(json.dumps(new, indent=1) + "\n")
    if errors:
        return 2
    return 10 if touches else 0


if __name__ == "__main__":
    sys.exit(main())
