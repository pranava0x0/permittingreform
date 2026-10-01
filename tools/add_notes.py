"""Merge section notes (JSON on stdin) into data/bill/analysis.json, keyed by section number.

Usage: python3 tools/add_notes.py < notes.json
Input shape: {"1101": {...}, "1102": {...}} — each value replaces that section's entry.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/bill/analysis.json"


def main() -> int:
    incoming = json.load(sys.stdin)
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"generated": "2026-09-30", "sections": {}}
    for num, note in incoming.items():
        data["sections"][num] = note
    data["sections"] = dict(sorted(data["sections"].items(), key=lambda kv: int(kv[0])))
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"add_notes: {len(incoming)} merged, {len(data['sections'])} sections noted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
