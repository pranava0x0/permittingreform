"""Validate the datasets the site ships: shape, references, vocabulary and house style.

Runs the build in memory (so it checks what the site renders), then checks:
  - every section has a summary, key points, at least one verified quote and
    notes on all three earlier versions
  - every comparison row has four filled cells
  - timeline, people and media records have their required fields, valid
    dates, known vocabulary values, unique ids and at least one http(s) source
  - machine-written prose follows the house style: no em or en dashes, no
    exclamation marks, none of the register words DESIGN.md bans

Verbatim quotes and source titles are exempt from the style checks.

Usage: python3 tools/check_data.py [--dump-prose PATH]
  --dump-prose writes every machine-written string as a paragraph, for
  tools that lint prose (for example slopcheck).
Exit codes: 0 clean, 1 findings, 2 nothing examined.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import integrate_research as vocab  # noqa: E402

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BANNED = re.compile(
    r"\b(delve|leverag\w*|robust|seamless\w*|elevate[sd]?|unlock\w*|empower\w*|harness\w*|tapestry|testament|"
    r"underscore[sd]?|pivotal|crucial|comprehensive|cutting-edge|game-chang\w*|ever-evolving|realm|landmark|"
    r"groundbreaking|sweeping|unprecedented|notably|importantly|it is worth noting|in today's)\b", re.I)
DASH = re.compile(r"[—–]")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")


def prose_fields(core: dict) -> list[tuple[str, str]]:
    """(where, text) for every string a machine wrote and the site displays."""
    out: list[tuple[str, str]] = []
    for s in core["sections"]:
        out.append((f"section {s['n']} summary", s["plain"]))
        out += [(f"section {s['n']} key point", p["t"]) for p in s["points"]]
        out += [(f"section {s['n']} quote note", q["why"]) for q in s["quotes"] if q["why"]]
        out += [(f"section {s['n']} vs {k}", v) for k, v in s["vs"].items() if v]
    o = core["overview"]
    out.append(("overview money note", o["money_note"]))
    out += [("overview status", p["text"]) for p in o["status"]["points"]]
    out += [(f"overview headline {h['id']}", h["title"] + ". " + h["text"]) for h in o["headlines"]]
    out += [("overview clock", c["what"]) for c in o["clocks"]] + [("overview money", c["what"]) for c in o["money"]]
    for g in core["compare"]["groups"]:
        for r in g["rows"]:
            out += [(f"compare {r['id']} {k}", r[k]["text"]) for k in ("current", "epra", "speed", "senate")]
    out += [("compare added", a["text"]) for a in core["compare"]["added"]]
    out += [("compare dropped", a["text"]) for a in core["compare"]["dropped"]]
    for e in core["timeline"]:
        out += [(f"timeline {e['id']} title", e["title"]), (f"timeline {e['id']} summary", e["summary"])]
        if e.get("significance"):
            out.append((f"timeline {e['id']} significance", e["significance"]))
    for p in core["people"]:
        out += [(f"people {p['id']} role", p["role"]), (f"people {p['id']} position", p["position"])]
        out += [(f"people {p['id']} action", a) for a in p.get("key_actions", [])]
    out += [(f"media {it['id']} summary", it["summary"]) for it in core["media"] if it.get("summary")]
    return out


def check(core: dict) -> tuple[list[str], dict]:
    errs: list[str] = []
    counts = {"sections": len(core["sections"]), "compare rows": 0, "timeline": len(core["timeline"]),
              "people": len(core["people"]), "media": len(core["media"]), "prose strings": 0}

    for s in core["sections"]:
        if not s["plain"]:
            errs.append(f"section {s['n']}: no summary")
        if not s["points"]:
            errs.append(f"section {s['n']}: no key points")
        if not s["quotes"]:
            errs.append(f"section {s['n']}: no key quote")
        for i, p in enumerate(s["points"], 1):
            if "c" not in p:
                errs.append(f"section {s['n']}: key point {i} cites no passage: {p['t'][:60]!r}")
        if not s["topics"]:
            errs.append(f"section {s['n']}: no topic")
        if s["imp"] not in (1, 2, 3):
            errs.append(f"section {s['n']}: importance {s['imp']!r} is not 1, 2 or 3")
        for k, v in s["vs"].items():
            if not v:
                errs.append(f"section {s['n']}: no note on {k}")

    for g in core["compare"]["groups"]:
        for r in g["rows"]:
            counts["compare rows"] += 1
            for k in ("current", "epra", "speed", "senate"):
                if not (r.get(k) or {}).get("text"):
                    errs.append(f"compare {r['id']}: empty cell {k}")

    def http(url) -> bool:
        return isinstance(url, str) and url.lower().startswith(("http://", "https://"))

    def dated(where: str, d: str) -> None:
        if not DATE_RE.match(d or "") or d > core["meta"]["as_of"]:
            errs.append(f"{where}: date {d!r} is malformed or after the data date {core['meta']['as_of']}")

    seen: set[str] = set()
    for e in core["timeline"]:
        w = f"timeline {e.get('id')}"
        if e["id"] in seen:
            errs.append(f"{w}: duplicate id")
        seen.add(e["id"])
        dated(w, e["date"])
        if not e["id"].startswith(e["date"]):
            errs.append(f"{w}: id does not start with its date")
        if e["branch"] not in vocab.BRANCHES:
            errs.append(f"{w}: unknown branch {e['branch']!r}")
        if not e.get("sources") or not all(http(s["url"]) for s in e["sources"]):
            errs.append(f"{w}: needs at least one http(s) source")
        if len(e["title"]) > 120:
            errs.append(f"{w}: title is {len(e['title'])} characters (limit 120)")
        q = e.get("quote")
        if q and (not q.get("speaker") or len(q["text"].split()) > 70):
            errs.append(f"{w}: quote needs a speaker and at most 70 words")

    seen = set()
    for p in core["people"]:
        w = f"people {p.get('id')}"
        if p["id"] in seen:
            errs.append(f"{w}: duplicate id")
        seen.add(p["id"])
        if p["sector"] not in vocab.SECTORS:
            errs.append(f"{w}: unknown sector {p['sector']!r}")
        if p["stance"] not in vocab.STANCES:
            errs.append(f"{w}: unknown stance {p['stance']!r}")
        # A former official keeps a government sector but sits outside government.
        if p["inside_government"] and p["sector"] not in {"congress", "white_house", "agency", "court"}:
            errs.append(f"{w}: marked inside government but sector is {p['sector']}")
        if not p.get("sources") or not all(http(s["url"]) for s in p["sources"]):
            errs.append(f"{w}: needs at least one http(s) source")

    seen = set()
    urls: set[str] = set()
    for it in core["media"]:
        w = f"media {it.get('id')}"
        if it["id"] in seen:
            errs.append(f"{w}: duplicate id")
        seen.add(it["id"])
        dated(w, it["date"])
        if it["type"] not in vocab.MEDIA_TYPES:
            errs.append(f"{w}: unknown type {it['type']!r}")
        if it["stance"] not in vocab.STANCES:
            errs.append(f"{w}: unknown stance {it['stance']!r}")
        if not http(it["url"]):
            errs.append(f"{w}: url is not http(s)")
        key = vocab.url_key(it["url"])
        if key in urls:
            errs.append(f"{w}: duplicate url")
        urls.add(key)
        if not it.get("outlet") or not it.get("title"):
            errs.append(f"{w}: needs an outlet and a title")

    for where, text in prose_fields(core):
        counts["prose strings"] += 1
        if DASH.search(text):
            errs.append(f"{where}: em or en dash in displayed prose: {text[:70]!r}")
        m = BANNED.search(text)
        if m:
            errs.append(f"{where}: register word {m.group(0)!r}: {text[:70]!r}")
        if "!" in text:
            errs.append(f"{where}: exclamation mark: {text[:70]!r}")
        if EMOJI.search(text):
            errs.append(f"{where}: emoji: {text[:70]!r}")
    return errs, counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dump-prose", metavar="PATH", help="write machine-written prose to PATH, one paragraph per string")
    args = ap.parse_args()

    core, _, build_errors = build.build()
    errs, counts = check(core)
    errs = [f"build: {e}" for e in build_errors] + errs
    if args.dump_prose:
        Path(args.dump_prose).write_text("\n\n".join(t for _, t in prose_fields(core)) + "\n", encoding="utf-8")
    examined = ", ".join(f"{v} {k}" for k, v in counts.items())
    if not sum(counts.values()):
        print("check_data: nothing to examine", file=sys.stderr)
        return 2
    for e in errs:
        print(f"check_data: {e}")
    print(f"check_data: examined {examined}; {len(errs)} finding(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
