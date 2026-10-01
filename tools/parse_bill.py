"""Parse the Senate bill PDF into a section index that keeps page and line cites.

Input:  site/bill.pdf (the PDF as posted by Senate EPW on September 30, 2026)
        (text cached at data/bill/bill_raw.txt, pages split by '===== PAGE N =====')
Output: data/bill/sections.json

Each section carries its printed lines as [page, line_number, text] so that any
quote or search hit can be cited the way Senate staff cite a bill print:
"page 44, line 6". Words the typesetter split across two lines are rejoined on
the line where the word starts; the printed line count is unchanged.

Standard library + pypdf. Re-runnable; overwrites the output.
Exit codes: 0 ok, 1 the table of contents and the body disagree, 2 nothing parsed.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/bill/bill_raw.txt"
PDF = ROOT / "site/bill.pdf"
OUT = ROOT / "data/bill/sections.json"

PAGE_RE = re.compile(r"^===== PAGE (\d+) =====$")
HEADER_RE = re.compile(r"^KAT26642 TWY\s+S\.L\.C\.\s*$")
SEC_RE = re.compile(r"^SEC\. (\d+)\. (.*)$")
TOC_SEC_RE = re.compile(r"^Sec\. (\d+)\. (.*)$")
DIV_RE = re.compile(r"^(DIVISION [A-Z])—(.*)$")
TITLE_RE = re.compile(r"^(TITLE [IVXLC]+)—(.*)$")
SUB_RE = re.compile(r"^(Subtitle [A-Z])—(.*)$")
STRUCT_RE = re.compile(r"^(DIVISION [A-Z]|TITLE [IVXLC]+|Subtitle [A-Z])—")

SOFT = "\u0001"  # typesetter's soft hyphen: join the next fragment with no hyphen
HARD = "\u0002"  # real hyphen at a line break: join the next fragment, keep the hyphen

SMALLCAP_STOP = {"OF", "AND", "OR", "IN", "TO", "ON", "BY", "FOR", "THE", "AS", "AT", "IS", "ARE", "NOT", "ANY", "WITH", "AN"}
TWO_LETTER = {"IN", "OF", "ON", "TO", "OR", "AT", "BY", "NO", "AS", "IF", "AN", "UP", "RE", "US"}


def extract_raw() -> str:
    stamp = "# pdf_sha256=" + hashlib.sha256(PDF.read_bytes()).hexdigest()
    if RAW.exists():
        raw = RAW.read_text(encoding="utf-8")
        if raw.startswith(stamp + "\n"):
            return raw
    from pypdf import PdfReader  # only needed on the first run

    reader = PdfReader(str(PDF))
    parts = [f"\n===== PAGE {i + 1} =====\n{page.extract_text() or ''}" for i, page in enumerate(reader.pages)]
    RAW.write_text(stamp + "\n" + "".join(parts), encoding="utf-8")
    return "".join(parts)


def split_pages(raw: str) -> list[tuple[int, list[str]]]:
    pages: list[tuple[int, list[str]]] = []
    cur: list[str] | None = None
    num = 0
    for line in raw.splitlines():
        m = PAGE_RE.match(line)
        if m:
            if cur is not None:
                pages.append((num, cur))
            num = int(m.group(1))
            cur = []
        elif cur is not None:
            cur.append(line.rstrip())
    if cur is not None:
        pages.append((num, cur))
    return pages


def clean_page(num: int, lines: list[str]) -> list[list]:
    """Return [page, line_number_or_None, text] rows for one page.

    Printed line numbers run 1..N down the page. A trailing integer is stripped
    only when it equals the next expected number, so a real trailing number (a
    year, a section cite) survives. The gap before the number tells a soft
    hyphen ('designa -17', 'Notwith-5') from a real one ('non-  7').
    """
    out: list[list] = []
    expected = 1
    body_started = False
    for line in lines:
        s = line.strip()
        if not s or HEADER_RE.match(s):
            continue
        if not body_started and s == str(num):
            continue  # the page number printed at the top of the page
        body_started = True
        line_no = None
        m = re.match(r"^(.*?)( *)(?<!\d)(\d{1,2})$", s)
        if m and int(m.group(3)) == expected:
            text, gap = m.group(1), m.group(2)
            line_no = expected
            expected += 1
            if text.endswith(" -"):
                s = text[:-2].rstrip() + SOFT
            elif text.endswith("-") and gap == "":
                s = text[:-1] + SOFT
            elif text.endswith("-") and gap:
                s = text + HARD
            else:
                s = text.rstrip()
        elif s.endswith(" -"):
            s = s[:-2].rstrip() + SOFT
        elif s.endswith("-"):
            s = s + HARD
        out.append([num, line_no, s])
    return out


def rejoin_words(rows: list[list]) -> None:
    """Move the tail of a split word up to the line where the word starts."""
    for i in range(len(rows) - 1):
        text = rows[i][2]
        if text.endswith("–") and rows[i + 1][2][:1].isdigit():
            head, _, rest = rows[i + 1][2].partition(" ")
            rows[i][2] += head
            rows[i + 1][2] = rest
            continue
        if not (text.endswith(SOFT) or text.endswith(HARD)):
            continue
        nxt = rows[i + 1][2].lstrip()
        head, _, rest = nxt.partition(" ")
        if "—" in head:
            fragment, body = head.split("—", 1)
            head = fragment + "—"
            rest = (body + " " + rest).strip()
        marker = ""
        if head.endswith(SOFT) or head.endswith(HARD):  # the fragment is itself split again
            marker, head = head[-1], head[:-1]
        rows[i][2] = text[:-1] + head
        rows[i + 1][2] = (marker if not rest else rest) if (marker and not rest) else rest
        if marker and rest == "":
            rows[i + 1][2] = marker
    for row in rows:
        row[2] = row[2].replace(SOFT, "").replace(HARD, "")


def normalize_line(line: str) -> str:
    """pypdf renders small caps as 'D ETERMINATION OF A GENCY'; rejoin the split words."""

    def join_two(m: re.Match) -> str:
        w = m.group(1) + m.group(2)
        return w if w in TWO_LETTER else m.group(0)

    def join_word(m: re.Match) -> str:
        first, rest = m.group(1), m.group(2)
        if first == "A" and rest in SMALLCAP_STOP:
            return m.group(0)
        return first + rest

    line = re.sub(r"(?<![A-Za-z’‘'(])([A-Z]) ([A-Z])(?![A-Za-z])", join_two, line)
    line = re.sub(r"(?<![A-Za-z])([A-Z]) ([A-Z]{2,})(?![a-z])", join_word, line)
    line = re.sub(r"(?<=[A-Z]) -(?=[A-Z])", "-", line)
    line = line.replace(" .—", ".—").replace(" .’’", ".’’").replace(" ;", ";")
    line = line.replace("‘‘", "“").replace("’’", "”")
    line = re.sub(r"[ \t]{2,}", " ", line)
    return line.strip()


def parse_toc(texts: list[str]) -> list[dict]:
    """Ordered outline from the table of contents (it ends where 'DIVISION A—' repeats)."""
    entries: list[dict] = []
    cur: dict | None = None
    started = False
    for line in texts:
        if line.startswith("DIVISION A—"):
            if started:
                break
            started = True
        if not started:
            continue
        kind = None
        m = None
        for k, rx in (("division", DIV_RE), ("title", TITLE_RE), ("subtitle", SUB_RE), ("section", TOC_SEC_RE)):
            m = rx.match(line)
            if m:
                kind = k
                break
        if m:
            cur = {"kind": kind, "label": m.group(1), "heading": m.group(2).strip()}
            entries.append(cur)
        elif cur is not None:
            cur["heading"] = (cur["heading"] + " " + line.strip()).strip()
    for e in entries:
        e["heading"] = e["heading"].replace("non- Federal", "non-Federal").replace("- ", "-") if "- " in e["heading"] else e["heading"]
    return entries


def main() -> int:
    pages = split_pages(extract_raw())
    if not pages:
        print("parse_bill: no pages found", file=sys.stderr)
        return 2

    rows: list[list] = []
    for num, lines in pages:
        rows.extend(clean_page(num, lines))
    rejoin_words(rows)
    for row in rows:
        row[2] = normalize_line(row[2])

    toc = parse_toc([r[2] for r in rows])
    toc_sections = [e for e in toc if e["kind"] == "section"]
    if len(toc_sections) < 50:
        print(f"parse_bill: table of contents yielded only {len(toc_sections)} sections", file=sys.stderr)
        return 2

    div_hits = [i for i, r in enumerate(rows) if r[2].startswith("DIVISION A—")]
    if len(div_hits) < 2:
        print("parse_bill: could not find where the body starts", file=sys.stderr)
        return 2
    body = rows[div_hits[1]:]

    # Locate each section heading in the body; headings may wrap onto all-caps lines.
    found: dict[str, tuple[int, int]] = {}  # number -> (heading index, first text index)
    i = 0
    while i < len(body):
        m = SEC_RE.match(body[i][2])
        if m:
            heading = m.group(2).strip()
            j = i + 1
            while j < len(body) and not heading.endswith(".") and body[j][2] and body[j][2] == body[j][2].upper() and not SEC_RE.match(body[j][2]):
                heading += " " + body[j][2]
                j += 1
            found[m.group(1)] = (i, j)
            i = j
        else:
            i += 1

    toc_nums = [e["label"] for e in toc_sections]
    missing = [n for n in toc_nums if n not in found]
    extra = [n for n in found if n not in set(toc_nums)]
    if missing or extra:
        print(f"parse_bill: table of contents and body disagree: missing={missing} extra={extra}", file=sys.stderr)

    order = sorted((n for n in toc_nums if n in found), key=lambda n: found[n][0])
    sections: list[dict] = []
    division = title = subtitle = None
    by_num: dict[str, dict] = {}
    for e in toc:
        if e["kind"] == "division":
            division, title, subtitle = e, None, None
        elif e["kind"] == "title":
            title, subtitle = e, None
        elif e["kind"] == "subtitle":
            subtitle = e
        elif e["label"] in found:
            by_num[e["label"]] = {
                "number": e["label"],
                "id": f"sec-{e['label']}",
                "heading": e["heading"].rstrip("."),
                "division": division["label"] if division else None,
                "division_heading": division["heading"] if division else None,
                "title": title["label"] if title else None,
                "title_heading": title["heading"] if title else None,
                "subtitle": subtitle["label"] if subtitle else None,
                "subtitle_heading": subtitle["heading"] if subtitle else None,
            }
    for k, n in enumerate(order):
        head_idx, first = found[n]
        end = found[order[k + 1]][0] if k + 1 < len(order) else len(body)
        chunk = [r for r in body[first:end]]
        # Drop the next title's or subtitle's heading block if it trails this section.
        for t in range(max(0, len(chunk) - 8), len(chunk)):
            if STRUCT_RE.match(chunk[t][2]):
                chunk = chunk[:t]
                break
        chunk = [r for r in chunk if r[2]]
        sec = by_num[n]
        sec["page_start"] = body[head_idx][0]
        sec["line_start"] = body[head_idx][1]
        sec["page_end"] = chunk[-1][0] if chunk else sec["page_start"]
        sec["lines"] = chunk
        sec["text"] = "\n".join(r[2] for r in chunk)
        sec["words"] = len(sec["text"].split())
        sections.append(sec)

    unnumbered = sum(1 for s in sections for r in s["lines"] if r[1] is None)
    meta = {
        "pdf_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
        "short_title": "Bipartisan American Affordability and Jobs Act of 2026",
        "draft_id": "KAT26642",
        "congress": "119th Congress, 2d Session",
        "chamber": "Senate",
        "sponsors": ["Shelley Moore Capito (R-W.Va.)", "Mike Lee (R-Utah)", "Sheldon Whitehouse (D-R.I.)", "Martin Heinrich (D-N.M.)"],
        "released": "2026-09-30",
        "pages": len(pages),
        "source_pdf": "https://www.epw.senate.gov/public/_cache/files/5/c/5c5f5935-b224-48e7-abea-e60c30e7a4cf/7935BF3C85967B6F56F6F4858FD3221B7E0AEB02D04BE391CAFBD1B884CE3DC5.bipartisan-american-affordability-and-jobs-act-text.pdf",
        "mirror_pdfs": [
            "https://www.energy.senate.gov/wp-content/uploads/2026/09/KAT26642FINAL.pdf",
            "https://www.energy.senate.gov/wp-content/uploads/2026/09/Bipartisan-American-Affordability-and-Jobs-Act.pdf",
        ],
        "total_words": sum(s["words"] for s in sections),
        "total_lines": sum(len(s["lines"]) for s in sections),
    }
    OUT.write_text(json.dumps({"meta": meta, "outline": toc, "sections": sections}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"parse_bill: {len(pages)} pages, {len(toc_sections)} sections in the table of contents, "
        f"{len(sections)} parsed, {meta['total_lines']} lines ({unnumbered} without a printed number), "
        f"{meta['total_words']} words -> {OUT.relative_to(ROOT)}"
    )
    return 1 if (missing or extra) else 0


if __name__ == "__main__":
    raise SystemExit(main())
