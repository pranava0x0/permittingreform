#!/usr/bin/env python3
"""Read a Senate roll-call vote from the Senate's XML, and fetch a new one.

  python3 tools/roll_call.py 259            # fetch vote 259 into data/votes/ and print its record
  python3 tools/roll_call.py 257 --offline  # re-read the committed file; no network

The XML for every roll call in data/votes.json is committed under data/votes/. The build re-reads
each file and fails if the tally, the result or any senator's vote in votes.json differs from it,
so the member lists cannot drift from the Senate's record. The printed record carries every field
votes.json copies from the XML; `question` (plain words) and `measure` are written by hand.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/votes"
BASE = "https://www.senate.gov/legislative/LIS/roll_call_votes/vote{congress}{session}/vote_{congress}_{session}_{number:05d}"
# Fields of a votes.json roll call that are copied from the XML and must equal it.
COPIED = ("number", "date", "official_question", "required", "result", "quote", "yeas", "nays", "not_voting")


def read(path: Path) -> dict:
    """The fields votes.json copies from one roll-call XML file."""
    root = ElementTree.parse(path).getroot()

    def text(node, tag: str) -> str:
        return " ".join((node.findtext(tag) or "").split())

    count = root.find("count")
    day = ",".join(text(root, "vote_date").split(",")[:2])  # "November 9, 2026,  05:31 PM"
    return {
        "number": int(text(root, "vote_number")),
        "date": datetime.strptime(day, "%B %d, %Y").strftime("%Y-%m-%d"),
        "official_question": text(root, "vote_question_text"),
        "required": text(root, "majority_requirement"),
        "result": text(root, "vote_result"),
        "quote": text(root, "vote_result_text"),
        "yeas": int(text(count, "yeas") or 0),
        "nays": int(text(count, "nays") or 0),
        "not_voting": int(text(count, "absent") or 0),
        "present": int(text(count, "present") or 0),
        "members": [[f"{text(m, 'first_name')} {text(m, 'last_name')}", text(m, "party"), text(m, "state"), text(m, "vote_cast")]
                    for m in root.iter("member")],
    }


def differences(rc: dict, raw: dict) -> list[str]:
    """What a votes.json roll call says that the Senate's XML does not."""
    out = [f"{key} is {rc.get(key)!r}, the Senate file says {raw[key]!r}" for key in COPIED if rc.get(key) != raw[key]]
    if raw["present"]:
        out.append(f"the Senate file counts {raw['present']} voting present, which votes.json has no place for")
    ours = {(m[0], m[2]): m[1:4] for m in rc["members"]}
    theirs = {(m[0], m[2]): m[1:4] for m in raw["members"]}
    for who in sorted(set(ours) | set(theirs)):
        if who not in theirs:
            out.append(f"{who[0]} ({who[1]}) is not in the Senate file")
        elif who not in ours:
            out.append(f"{who[0]} ({who[1]}) is in the Senate file and missing here")
        elif ours[who] != theirs[who]:
            out.append(f"{who[0]} ({who[1]}) is {'-'.join(ours[who][::2])} here and {'-'.join(theirs[who][::2])} in the Senate file")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("number", type=int, help="the roll-call vote number")
    ap.add_argument("--congress", type=int, default=119)
    ap.add_argument("--session", type=int, default=2)
    ap.add_argument("--offline", action="store_true", help="re-read the committed XML instead of fetching it")
    args = ap.parse_args()
    base = BASE.format(congress=args.congress, session=args.session, number=args.number)
    path = RAW / (base.rsplit("/", 1)[1] + ".xml")
    if not args.offline:
        req = urllib.request.Request(base + ".xml", headers={"User-Agent": "Mozilla/5.0 (roll-call reader)"})
        with urllib.request.urlopen(req, timeout=40) as res:
            body = res.read()
        if b"<roll_call_vote>" not in body:
            sys.exit(f"roll_call: {base}.xml did not return a roll-call vote ({len(body)} bytes)")
        RAW.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        print(f"roll_call: wrote {path.relative_to(ROOT)} ({len(body)} bytes)", file=sys.stderr)
    if not path.exists():
        sys.exit(f"roll_call: {path.relative_to(ROOT)} is not committed; run without --offline to fetch it")
    raw = read(path)
    raw.pop("present")
    record = {**{k: raw[k] for k in COPIED}, "url": base + ".htm", "xml_url": base + ".xml", "members": raw["members"]}
    if not args.offline:
        record["xml_fetched"] = time.strftime("%Y-%m-%d")
    cast = [m[3] for m in record["members"]]
    print(f"roll_call: vote {raw['number']}, {raw['date']}: {raw['quote']}; {len(cast)} senators "
          f"({cast.count('Yea')} yea, {cast.count('Nay')} nay, {cast.count('Not Voting')} not voting)", file=sys.stderr)
    print(json.dumps(record, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
