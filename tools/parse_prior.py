"""Parse GPO bill HTML (govinfo BILLS-*.htm) into a section list for comparison.

Standard library only. Input files live in data/prior_bills/; output JSON beside them.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data/prior_bills"

PRIOR = {
    "speed_act_hr4776_eh": {
        "file": "BILLS-119hr4776eh.htm",
        "name": "SPEED Act (H.R. 4776), as passed the House",
        "short": "SPEED Act (House-passed, Dec 18 2025)",
        "congress": "119th",
        "status": "Passed House 221-196 on 2025-12-18",
        "url": "https://www.congress.gov/bill/119th-congress/house-bill/4776/text/eh",
        "govinfo": "https://www.govinfo.gov/content/pkg/BILLS-119hr4776eh/html/BILLS-119hr4776eh.htm",
    },
    "epra_2024_s4753_rs": {
        "file": "BILLS-118s4753rs.htm",
        "name": "Energy Permitting Reform Act of 2024 (S. 4753), as reported by Senate ENR",
        "short": "EPRA 2024 (Manchin-Barrasso, reported)",
        "congress": "118th",
        "status": "Reported by Senate Energy and Natural Resources 15-4 on 2024-07-31; no floor vote",
        "url": "https://www.congress.gov/bill/118th-congress/senate-bill/4753/text/rs",
        "govinfo": "https://www.govinfo.gov/content/pkg/BILLS-118s4753rs/html/BILLS-118s4753rs.htm",
    },
}

SEC_RE = re.compile(r"^\s*SEC(?:TION)?\.?\s+(\d+[A-Z]?)\.\s+(.*)$")
HEAD_RE = re.compile(r"^\s*(DIVISION [A-Z]|TITLE [IVXLC]+|Subtitle [A-Z]|PART [IVXLC0-9]+)(?:--|—)(.*)$")


def to_text(raw: str) -> str:
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html.unescape(raw)
    return raw


def parse(key: str, spec: dict) -> dict:
    src = DIR / spec["file"]
    text = to_text(src.read_text(encoding="utf-8", errors="replace"))
    lines = text.splitlines()
    # Skip the GPO banner and the bill's own table of contents: body starts at
    # the first 'SEC.' heading that follows the last TOC line ('Sec. N.').
    sections: list[dict] = []
    cur: dict | None = None
    title = subtitle = None
    seen_body = False
    for line in lines:
        s = line.rstrip()
        m = SEC_RE.match(s)
        if m and s.strip().startswith("SEC"):
            seen_body = True
            cur = {"number": m.group(1), "heading": m.group(2).strip().rstrip("."), "title": title, "subtitle": subtitle, "lines": []}
            sections.append(cur)
            continue
        h = HEAD_RE.match(s)
        if h and seen_body and s.strip().upper() == s.strip():
            label = h.group(1)
            if label.startswith("TITLE") or label.startswith("DIVISION"):
                title = f"{label}—{h.group(2).strip()}"
                subtitle = None
            else:
                subtitle = f"{label}—{h.group(2).strip()}"
            continue
        if h and seen_body and label_is_subtitle(h.group(1)):
            subtitle = f"{h.group(1)}—{h.group(2).strip()}"
            continue
        if cur is not None:
            cur["lines"].append(s.strip())
    out = []
    for sec in sections:
        body = " ".join(l for l in sec["lines"] if l)
        body = re.sub(r"\s{2,}", " ", body).strip()
        out.append({
            "number": sec["number"],
            "id": f"{key}-sec-{sec['number']}",
            "heading": sec["heading"],
            "title": sec["title"],
            "subtitle": sec["subtitle"],
            "words": len(body.split()),
            "text": body,
        })
    return {"meta": {k: v for k, v in spec.items() if k != "file"} | {"key": key, "sections": len(out)}, "sections": out}


def label_is_subtitle(label: str) -> bool:
    return label.startswith("Subtitle") or label.startswith("PART")


def main() -> int:
    rc = 0
    for key, spec in PRIOR.items():
        data = parse(key, spec)
        outp = DIR / f"{key}.json"
        outp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        n = data["meta"]["sections"]
        print(f"parse_prior: {key}: {n} sections, {sum(s['words'] for s in data['sections'])} words -> {outp.relative_to(ROOT)}")
        if n < 3:
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
