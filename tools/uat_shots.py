"""Capture every view at phone, tablet and desktop widths with headless Chrome.

Usage: python3 tools/uat_shots.py [--base http://127.0.0.1:8766] [--only overview,bill]
Writes PNGs to uat-screenshots/ (not committed). Needs Google Chrome and a
running `make serve`. A fresh headless browser has no cache, so each capture
shows the files as served.
Exit codes: 0 captured, 1 a capture failed, 2 Chrome or the server is missing.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "uat-screenshots"
CHROME_PATHS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium", "chromium-browser")
VIEWPORTS = {"phone": (375, 812), "tablet": (768, 1024), "desktop": (1280, 900)}
ROUTES = {
    "overview": "#/overview",
    "bill": "#/bill",
    "section": "#/bill/sec/1106",
    "anchor": "#/bill/sec/1106/54-18/travel%20more%20than%2025%20miles",
    "search": "#/bill/search/data%20center",
    "compare": "#/compare",
    "timeline": "#/timeline",
    "people": "#/people",
    "media": "#/media",
    "method": "#/method",
}


def find_chrome() -> str | None:
    for c in CHROME_PATHS:
        if Path(c).exists() or shutil.which(c):
            return c
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", default="http://127.0.0.1:8766")
    ap.add_argument("--only", help="comma-separated route names")
    ap.add_argument("--tall", type=int, default=2400, help="capture height in CSS pixels")
    ap.add_argument("--dark", action="store_true", help="capture the dark theme")
    args = ap.parse_args()

    chrome = find_chrome()
    if not chrome:
        print("uat_shots: Google Chrome not found", file=sys.stderr)
        return 2
    try:
        urllib.request.urlopen(args.base + "/index.html", timeout=5).read(64)
    except OSError as exc:
        print(f"uat_shots: nothing is serving {args.base} ({exc}); run `make serve`", file=sys.stderr)
        return 2

    names = args.only.split(",") if args.only else list(ROUTES)
    OUT.mkdir(exist_ok=True)
    stamp = time.strftime("%Y-%m-%d")
    failed = 0
    for size, (width, _) in VIEWPORTS.items():
        for name in names:
            dest = OUT / f"{stamp}_{name}_{size}{'_dark' if args.dark else ''}.png"
            cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                   f"--window-size={width},{args.tall}", "--virtual-time-budget=5000", f"--screenshot={dest}"]
            if args.dark:
                cmd.append("--force-dark-mode")
                cmd.append("--blink-settings=preferredColorScheme=0")
            cmd.append(f"{args.base}/{ROUTES[name]}")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=False)
            if proc.returncode != 0 or not dest.exists() or dest.stat().st_size < 5000:
                failed += 1
                print(f"uat_shots: FAILED {dest.name}: {proc.stderr.strip()[-200:]}")
            else:
                print(f"uat_shots: {dest.name} {dest.stat().st_size // 1024} KB")
    print(f"uat_shots: {len(names) * len(VIEWPORTS) - failed} captured, {failed} failed -> {OUT.relative_to(ROOT)}/")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
