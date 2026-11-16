#!/usr/bin/env python3
"""Run the browser checks in a fixed order, with a status file another terminal can read.

  NODE_PATH=<dir with playwright> python3 tools/final_checks.py          # perf, paths, uat, clicks
  NODE_PATH=... python3 tools/final_checks.py --skip clicks              # the three short ones
  python3 tools/final_checks.py --status                                 # is a run moving? (make progress)

Steps, each against a server this script starts on a free port:
  perf    tools/perf_audit.cjs   cold load of every page at 375x812, plain and Slow 4G
  paths   tools/reader_paths.cjs taps and screens from the Overview to each answer
  uat     tests/uat.cjs          every view, both themes, three widths
  clicks  tests/clicks.cjs       every control from a fresh load (about 34 minutes)

Each step's output goes to .test-artifacts/final/<step>.log and its state to
.test-artifacts/final/status.json as it starts and ends. The run refuses to start while
another one is alive, and it does not rebuild site/. Exit code: 0 if every step passed.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".test-artifacts" / "final"
STATUS = OUT / "status.json"
CLICKS_PROGRESS = OUT / "clicks-progress.json"
STANDALONE_PROGRESS = ROOT / ".test-artifacts" / "clicks-progress.json"
# Seconds each full step took on 2026-11-15 (Apple M-series laptop, headless Chrome). Only used by
# --status to say when a step has run more than three times as long.
USUAL = {"perf": 60, "paths": 90, "uat": 150, "clicks": 2040}
# A step is called stalled when nothing it writes has changed for this long.
QUIET_S = 180



SERVE = """
import functools, http.server, sys
class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 128
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=sys.argv[2])
Server(("127.0.0.1", int(sys.argv[1])), handler).serve_forever()
"""

def steps(base: str) -> dict[str, tuple[list[str], dict[str, str]]]:
    return {
        "perf": (["node", "tools/perf_audit.cjs", "--json", str(OUT / "perf.json")], {}),
        "paths": (["node", "tools/reader_paths.cjs", base], {}),
        "uat": (["node", "tests/uat.cjs"], {"UAT_BASE": base}),
        "clicks": (["node", "tests/clicks.cjs"], {"UAT_BASE": base, "CLICKS_PROGRESS": str(CLICKS_PROGRESS), "CLICKS_OUT": str(OUT / "clicks.json")}),
    }


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, TypeError):
        return False
    return True


def read_status() -> dict | None:
    return json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else None


def write_status(doc: dict) -> None:
    doc["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    STATUS.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")


def clock() -> str:
    return time.strftime("%H:%M:%S")


def crawl(path: Path) -> tuple[str, int, bool] | None:
    """Where a click crawl is, the seconds since it last wrote, and whether its process is alive."""
    if not path.exists():
        return None
    p = json.loads(path.read_text(encoding="utf-8"))
    text = (f"{p.get('width')}px {p.get('phase')}, route {p.get('route')} ({p.get('route_n')} of {p.get('routes')})"
            f", {p['controls_done']} controls done, {p['page_loads']} page loads, {p['problems']} problems")
    return text, int(time.time() - path.stat().st_mtime), p.get("state") == "running" and alive(p.get("pid"))


def show_status() -> int:
    doc = read_status()
    # A crawl started by hand (node tests/clicks.cjs) writes its own progress file.
    alone = crawl(STANDALONE_PROGRESS)
    if alone and alone[2]:
        print(f"a crawl started by hand is running: {alone[0]}; last output {alone[1]}s ago" + (" -- STALLED" if alone[1] > QUIET_S else ""))
        if alone[1] > QUIET_S:
            return 2
    if not doc:
        print("final_checks: no `make final` run recorded (.test-artifacts/final/status.json is missing)")
        return 0 if alone and alone[2] else 1
    running = doc["state"] == "running" and alive(doc.get("pid"))
    state = doc["state"] if doc["state"] != "running" or running else "died (the process is gone and the run never finished)"
    print(f"run started {doc['started']}, state: {state}")
    stalled = False
    for s in doc["steps"]:
        line = f"  {s['name']:<7} {s['state']:<8}"
        if s["state"] == "running" and running:
            log = OUT / f"{s['name']}.log"
            marks = [f.stat().st_mtime for f in (log, CLICKS_PROGRESS if s["name"] == "clicks" else log) if f.exists()]
            quiet = int(time.time() - max(marks)) if marks else None
            took = int(time.time() - s["began"])
            line += f" {took}s so far (usually about {s['usual']}s)"
            here = crawl(CLICKS_PROGRESS) if s["name"] == "clicks" else None
            if here:
                line += f"; {here[0]}"
            if quiet is not None:
                line += f"; last output {quiet}s ago"
                if quiet > QUIET_S and s["name"] == "clicks":
                    stalled = True
                    line += " -- STALLED"
            if took > 3 * s["usual"]:
                stalled = True
                line += " -- more than three times the usual time"
        elif "seconds" in s:
            line += f" {s['seconds']}s, exit {s['exit']}, log {s['log']}"
        print(line)
    return 2 if stalled or state.startswith("died") else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true", help="print the state of the current or last run and exit")
    ap.add_argument("--skip", default="", help="comma-separated steps to leave out")
    ap.add_argument("--only", default="", help="comma-separated steps to run")
    args = ap.parse_args()
    if args.status:
        return show_status()

    names = [n for n in steps("") if n not in args.skip.split(",") and (not args.only or n in args.only.split(","))]
    unknown = [n for n in (args.skip + "," + args.only).split(",") if n and n not in steps("")]
    if unknown or not names:
        sys.exit(f"final_checks: unknown or empty step list {unknown or names}; steps are {', '.join(steps(''))}")
    if not os.environ.get("NODE_PATH"):
        sys.exit("final_checks: set NODE_PATH to a node_modules directory that holds playwright (see REFRESH.md)")
    last = read_status()
    if last and last["state"] == "running" and alive(last.get("pid")):
        sys.exit(f"final_checks: a run started {last['started']} is still alive (pid {last['pid']}); see --status")
    OUT.mkdir(parents=True, exist_ok=True)

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}/"
    # `python -m http.server` queues only 5 pending connections; Chrome opens more at once and the
    # overflow comes back as ERR_CONNECTION_RESET on a script, which left the UAT waiting on data
    # that never loaded (2026-11-16). SERVE raises the queue to 128.
    server = subprocess.Popen([sys.executable, "-c", SERVE, str(port), str(ROOT / "site")],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    doc = {"started": time.strftime("%Y-%m-%dT%H:%M:%S"), "pid": os.getpid(), "state": "running", "base": base,
           "steps": [{"name": n, "state": "pending", "usual": USUAL[n]} for n in names]}
    write_status(doc)
    failed = []
    try:
        for _ in range(50):  # the server needs a moment before the first step asks it for a page
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.1)
        else:
            sys.exit(f"final_checks: the local server never answered on port {port}")
        for s in doc["steps"]:
            cmd, env = steps(base)[s["name"]]
            log = OUT / f"{s['name']}.log"
            s.update(state="running", began=time.time(), log=str(log.relative_to(ROOT)))
            write_status(doc)
            print(f"[{clock()}] {s['name']}: started (usually about {s['usual']}s); log {s['log']}", flush=True)
            with log.open("w", encoding="utf-8") as fh:
                code = subprocess.run(cmd, cwd=ROOT, env={**os.environ, **env}, stdout=fh, stderr=subprocess.STDOUT).returncode
            s.update(state="passed" if code == 0 else "failed", seconds=int(time.time() - s.pop("began")), exit=code)
            write_status(doc)
            print(f"[{clock()}] {s['name']}: {s['state']} in {s['seconds']}s (exit {code})", flush=True)
            if code:
                failed.append(s["name"])
                print("    " + "\n    ".join(log.read_text(encoding="utf-8").strip().splitlines()[-12:]), flush=True)
    finally:
        server.terminate()
        doc["state"] = "failed" if failed or any(s["state"] != "passed" for s in doc["steps"]) else "passed"
        write_status(doc)
    print(f"final_checks: {len(names) - len(failed)} of {len(names)} steps passed" + (f"; failed: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
