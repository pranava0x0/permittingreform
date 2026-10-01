"""Second reading by a model: is each summary claim supported by the text it summarizes?

The quote checker proves that quoted words exist. It cannot tell whether a
paraphrase says what the text says. This script asks a Claude Sonnet model to
read each section of the bill next to the claims made about it and to return,
for every claim, a verdict and a verbatim span of evidence. The script then
checks by string match that each evidence span is really in the text, so a
verdict cannot rest on words the model made up.

Scopes:
  sections  summary sentences and key points, against the bill section they describe
  compare   the comparison table's Senate cells against the cited bill sections,
            and its SPEED Act and EPRA 2024 cells against those bills' texts
  all       both

It calls the Claude Code CLI in print mode (`claude -p --model sonnet`), one
call at a time, with no tools. Answers are cached under data/cache/infer/ by a
hash of the text and claims, so a re-run only re-asks about what changed.

Writes data/checks/inference.json, the "inference" summary in data/checks.json,
and data/bill/point_cites.json: for each key point, the passage the model
cited, kept only when that passage is in the bill text word for word. The site
shows it as the key point's page and line cite.

Usage: python3 tools/infer_check.py [--scope sections|compare|all] [--only 1106,1110]
                                    [--model sonnet] [--dry-run] [--refresh]
Exit codes: 0 every current claim supported, 1 a claim is flagged or unchecked,
            2 nothing examined, or the `claude` command is not installed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import billtext  # noqa: E402
import build  # noqa: E402
import check_links  # noqa: E402

ROOT = build.ROOT
OUT = ROOT / "data/checks/inference.json"
POINT_CITES = ROOT / "data/bill/point_cites.json"
CACHE = ROOT / "data/cache/infer"
PROMPT_VERSION = "3"
MAX_WORDS = 12000
SYSTEM = (
    "You check summaries of United States legislative text. For each numbered claim, decide whether the "
    "source text supports it. Be strict about numbers, deadlines, who must act, conditions and exceptions. "
    "A claim that the source does not address a subject is supported when the source text is silent on it. "
    "Verdicts: \"supported\" (the text says this), \"partly\" (close, but a detail is wrong, overstated or "
    "missing in a way that could mislead a reader), \"unsupported\" (the text does not say this, or says "
    "otherwise). For each claim give \"evidence\": one continuous span of at most 30 words copied exactly, "
    "character for character, from the source text: the span that best supports or contradicts the claim. "
    "Never join two passages, never use an ellipsis, never paraphrase, never add or drop a word. Use an "
    "empty string only when the claim is about silence. Give \"note\" (at most 30 words) only when the verdict "
    "is not \"supported\". Output one JSON object and nothing else: "
    "{\"results\":[{\"id\":\"...\",\"verdict\":\"...\",\"evidence\":\"...\",\"note\":\"...\"}]}"
)


ABBREV = ("No.", "U.S.C.", "Sec.", "Secs.", "v.", "Cir.", "Inc.", "Act.", "e.g.", "i.e.")


def sentences(text: str) -> list[str]:
    """Split a summary into sentence-sized claims; an abbreviation does not end a sentence."""
    parts = re.split(r"(?<=[.;])\s+(?=[A-Z0-9“'(])", text.replace("\n\n", " "))
    merged: list[str] = []
    for part in parts:
        if merged and merged[-1].endswith(ABBREV):
            merged[-1] += " " + part
        else:
            merged.append(part)
    return [p.strip() for p in merged if len(p.split()) >= 4]


def section_units(core: dict, bill: dict, only: set[str] | None) -> list[dict]:
    by_num = {s["number"]: s for s in bill["sections"]}
    units = []
    for s in core["sections"]:
        if only and s["n"] not in only:
            continue
        claims = [(f"{s['n']}.s{i}", c) for i, c in enumerate(sentences(s["plain"]), 1)]
        claims += [(f"{s['n']}.k{i}", p["t"]) for i, p in enumerate(s["points"], 1)]
        units.append({"key": f"section {s['n']}", "label": f"SEC. {s['n']}. {s['h']}", "text": by_num[s["n"]]["text"], "claims": claims})
    return units


def compare_units(core: dict, bill: dict) -> list[dict]:
    by_num = {s["number"]: s for s in bill["sections"]}
    units = []
    # One source for all the Senate cells: the sections they cite, each included once.
    cited: list[str] = []
    claims = []
    for g in core["compare"]["groups"]:
        for r in g["rows"]:
            nums = r["senate"].get("sections", [])
            if nums:
                cited += [n for n in nums if n not in cited]
                claims.append((f"cmp.{r['id']}.senate", f"On the subject of '{r['topic']}', in section(s) {', '.join(nums)}: {r['senate']['text']}"))
    if claims:
        text = "\n\n".join(f"[SEC. {n}. {by_num[n]['heading']}]\n{by_num[n]['text']}" for n in sorted(cited))
        units.append({"key": "compare senate", "label": "Bipartisan American Affordability and Jobs Act of 2026 (sections cited in the comparison)",
                      "text": text, "claims": claims})
    for key, fname, name in (("speed", "speed_act_hr4776_eh.json", "SPEED Act (H.R. 4776) as passed by the House"),
                             ("epra", "epra_2024_s4753_rs.json", "Energy Permitting Reform Act of 2024 (S. 4753) as reported")):
        prior = json.loads((ROOT / "data/prior_bills" / fname).read_text(encoding="utf-8"))
        text = "\n\n".join(f"[SEC. {s['number']}. {s['heading']}]\n{s['text']}" for s in prior["sections"])
        claims = []
        for g in core["compare"]["groups"]:
            for r in g["rows"]:
                cell = r[key]["text"]
                claims.append((f"cmp.{r['id']}.{key}", f"On the subject of '{r['topic']}': {cell}"))
        for i, d in enumerate([d for d in core["compare"]["dropped"] if d["from"] == key], 1):
            claims.append((f"cmp.dropped.{key}{i}", f"This bill contains: {d['text']} ({d['cite']})"))
        units.append({"key": f"compare {key}", "label": name, "text": text, "claims": claims})
    return units


def evidence_is_present(cid: str, claim: str, evidence: str, source: str) -> bool:
    """Require a bounded source span; only explicit comparison absences may be empty."""
    if not evidence:
        return cid.startswith("cmp.") and claim.endswith(("Not addressed.", "No change."))
    return billtext.locate([[1, 1, source]], evidence) is not None


def write_point_cites(results: list[dict], bill: dict) -> int:
    """Keep, for each key point, the passage that backs it: {section: {point text: passage}}.

    A passage from the model is stored only if it is in the section text, word
    for word. Entries added by hand are kept; an entry is replaced only when
    its passage no longer matches the text.
    """
    by_num = {s["number"]: s for s in bill["sections"]}
    cites = json.loads(POINT_CITES.read_text(encoding="utf-8")) if POINT_CITES.exists() else {}
    for r in results:
        m = re.match(r"^(\d{4})\.k\d+$", r["id"])
        if not m or not r["evidence"] or not r["evidence_in_text"] or r["verdict"] != "supported":
            continue
        n = m.group(1)
        if not billtext.locate(by_num[n]["lines"], r["evidence"]):
            continue
        have = cites.get(n, {}).get(r["claim"])
        if have and billtext.locate(by_num[n]["lines"], have):
            continue
        cites.setdefault(n, {})[r["claim"]] = r["evidence"]
    POINT_CITES.write_text(json.dumps(cites, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return sum(len(v) for v in cites.values())


def batches(units: list[dict]) -> list[list[dict]]:
    out: list[list[dict]] = []
    cur: list[dict] = []
    words = 0
    for u in units:
        w = len(u["text"].split()) + sum(len(c.split()) for _, c in u["claims"])
        if cur and words + w > MAX_WORDS:
            out.append(cur)
            cur, words = [], 0
        cur.append(u)
        words += w
    if cur:
        out.append(cur)
    return out


def prompt_for(batch: list[dict]) -> str:
    parts = []
    for u in batch:
        claims = "\n".join(f"{cid}: {text}" for cid, text in u["claims"])
        parts.append(f"=== SOURCE: {u['label']} ===\n{u['text']}\n\n=== CLAIMS ABOUT THIS SOURCE ===\n{claims}")
    return "\n\n\n".join(parts)


def ask(prompt: str, model: str) -> dict:
    proc = subprocess.run(
        ["claude", "-p", "--model", model, "--output-format", "json", "--tools", "", "--no-session-persistence",
         "--strict-mcp-config", "--system-prompt", SYSTEM],
        input=prompt, capture_output=True, text=True, timeout=900, check=False,
        env={k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")})
    if proc.returncode != 0:
        try:
            detail = json.loads(proc.stdout).get("result", "request failed")
        except ValueError:
            detail = proc.stderr.strip() or "request failed without diagnostics"
        raise RuntimeError(f"claude exited {proc.returncode}: {str(detail)[:300]}")
    envelope = json.loads(proc.stdout)
    if envelope.get("is_error"):
        raise RuntimeError(f"claude reported an error: {str(envelope.get('result'))[:300]}")
    body = envelope["result"].strip()
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", body)
    start, end = body.find("{"), body.rfind("}")
    return {"answer": json.loads(body[start:end + 1]), "model": next(iter(envelope.get("modelUsage", {model: 0}))),
            "cost_usd": envelope.get("total_cost_usd", 0)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scope", choices=("sections", "compare", "all"), default="all")
    ap.add_argument("--only", help="comma-separated section numbers (sections scope)")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--dry-run", action="store_true", help="show the batches and stop; no model calls")
    ap.add_argument("--cached-only", action="store_true", help="reconcile saved verdicts with current claims, without calling a model")
    ap.add_argument("--refresh", action="store_true", help="ignore cached answers")
    args = ap.parse_args()

    core, _, errors = build.build()
    if errors:
        print("infer_check: the build has errors; fix those first", file=sys.stderr)
        return 2
    bill = billtext.load_sections()
    only = set(args.only.split(",")) if args.only else None
    units: list[dict] = []
    if args.scope in ("sections", "all"):
        units += section_units(core, bill, only)
    if args.scope in ("compare", "all") and not only:
        units += compare_units(core, bill)
    total_claims = sum(len(u["claims"]) for u in units)
    if not total_claims:
        print("infer_check: no claims to examine", file=sys.stderr)
        return 2
    plan = batches(units)
    print(f"infer_check: {total_claims} claims about {len(units)} sources in {len(plan)} batches")
    if args.dry_run:
        for i, b in enumerate(plan, 1):
            print(f"  batch {i}: {len(b)} sources, {sum(len(u['claims']) for u in b)} claims, ~{sum(len(u['text'].split()) for u in b)} words")
        return 0
    if not args.cached_only and not shutil.which("claude"):
        print("infer_check: the `claude` command is not on PATH; install Claude Code or run with --dry-run", file=sys.stderr)
        return 2

    CACHE.mkdir(parents=True, exist_ok=True)
    text_of = {cid: u["text"] for u in units for cid, _ in u["claims"]}
    claim_of = {cid: c for u in units for cid, c in u["claims"]}
    results: list[dict] = []
    cost = 0.0
    model_used = args.model
    for i, batch in enumerate(plan, 1):
        prompt = prompt_for(batch)
        digest = hashlib.sha256((PROMPT_VERSION + args.model + SYSTEM + prompt).encode("utf-8")).hexdigest()[:24]
        cached = CACHE / f"{digest}.json"
        if cached.exists() and not args.refresh:
            reply = json.loads(cached.read_text(encoding="utf-8"))
            note = "cached"
        elif args.cached_only:
            continue
        else:
            started = time.time()
            reply = ask(prompt, args.model)
            cached.write_text(json.dumps(reply, ensure_ascii=False, indent=1), encoding="utf-8")
            note = f"{time.time() - started:.0f}s"
            cost += reply.get("cost_usd", 0)
        model_used = reply.get("model", model_used)
        answered = {r.get("id"): r for r in reply["answer"].get("results", [])}
        want = [cid for u in batch for cid, _ in u["claims"]]
        missing = [cid for cid in want if cid not in answered]
        print(f"  batch {i}/{len(plan)}: {len(want)} claims, {len(missing)} unanswered ({note})")
        for cid in want:
            r = answered.get(cid, {"verdict": "unanswered", "evidence": "", "note": "the model returned no verdict for this claim"})
            verdict = r.get("verdict", "unanswered")
            evidence = billtext.norm(r.get("evidence", "") or "")
            source = billtext.norm(text_of[cid])
            evidence_ok = evidence_is_present(cid, claim_of[cid], evidence, source)
            results.append({"id": cid, "claim": claim_of[cid], "verdict": verdict, "evidence": evidence,
                            "evidence_in_text": evidence_ok, "note": r.get("note", "")})

    def flagged(r: dict) -> bool:
        return r["verdict"] != "supported" or not r["evidence_in_text"]

    # A verdict stands only while the claim it judged is still the claim on the
    # site. Results for claims that were edited or removed are dropped, and
    # claims with no current verdict are reported as unchecked.
    current: dict[str, str] = {}
    for u in section_units(core, bill, None) + compare_units(core, bill):
        current.update(dict(u["claims"]))
    flags = [r for r in results if flagged(r)]
    checked = time.strftime("%Y-%m-%d", time.gmtime())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prior = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"results": []}
    merged = {r["id"]: r for r in prior.get("results", [])}
    merged.update({r["id"]: r for r in results})
    merged = {k: r for k, r in merged.items() if current.get(k) == r["claim"]}
    # Recheck saved evidence after parser/source edits. A changed claim gets no
    # inherited verdict; a missing span remains flagged.
    all_text = {cid: u["text"] for u in section_units(core, bill, None) + compare_units(core, bill) for cid, _ in u["claims"]}
    for cid, r in merged.items():
        ev = billtext.norm(r.get("evidence", ""))
        r["evidence_in_text"] = evidence_is_present(cid, r["claim"], ev, billtext.norm(all_text[cid]))
    all_results = [merged[k] for k in sorted(merged)]
    unchecked = sorted(set(current) - set(merged))
    OUT.write_text(json.dumps({"checked": checked, "model": model_used, "results": all_results, "unchecked": unchecked, "input_sha256": billtext.review_fingerprint(), "cached_only": args.cached_only}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    all_flags = [r for r in all_results if flagged(r)]
    check_links.merge_summary("inference", {
        "checked": checked, "model": model_used, "total": len(current), "input_sha256": billtext.review_fingerprint(),
        "cached_only": args.cached_only,
        "supported": len(all_results) - len(all_flags), "flagged": len(all_flags), "unchecked": len(unchecked),
    })
    written = write_point_cites(all_results, bill)
    print(f"infer_check: wrote passages for {written} key points -> {POINT_CITES.relative_to(ROOT)}")
    if unchecked:
        print(f"infer_check: {len(unchecked)} current claims have no verdict yet (edited since the last run): {', '.join(unchecked[:12])}{' ...' if len(unchecked) > 12 else ''}")
    print(f"infer_check: {len(results) - len(flags)} of {len(results)} claims supported, {len(flags)} flagged" + (f" (${cost:.2f})" if cost else ""))
    for r in all_flags:
        ev = "" if r["evidence_in_text"] else "  [the model's evidence span is not in the text]"
        print(f"  {r['verdict'].upper():<11} {r['id']}: {r['claim'][:150]}\n      note: {r['note']}{ev}")
    return 1 if (all_flags or unchecked) else 0


if __name__ == "__main__":
    raise SystemExit(main())
