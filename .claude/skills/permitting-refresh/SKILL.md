---
name: permitting-refresh
description: Refresh the permitting-bill tracker (BAAJA / H.R. 2347) end to end — floor status and votes, the Congressional Record, X posts, articles, claims mapped to the sections of the passed text a reader should check, every gate including the reader-path tap budget, then PR, review rounds and merge. Use for "refresh", "run it back", "update the site", "check for votes", "sweep X/news", or a scheduled floor-watch run in this repo.
---

# Permitting tracker refresh

Neutral site: report what happened and what was said, quote it verbatim, and point at the bill text. Never rate a claim, never say who is right. REFRESH.md is the playbook and holds the dated learnings; read it (all of "Learned") and the latest entry in docs/RUNLOG.md before starting. This skill is the order of operations and the commands.

Work in a new branch from `origin/main` (`git fetch`, `git switch --detach origin/main`, `git checkout -B refresh/<date>`). Never commit to main.

## 1. Floor status (deterministic, 2–5 minutes)

```
python3 tools/refresh_status.py          # exit 10: something touches the bill; 0: nothing; 2: a source failed
```

It reads Senate and House roll-call XML after the numbers in `data/research/floor_state.json`, govinfo CREC `mods.xml` for each day since the last check (granule titles naming the bill, including the House title "SURVIVOR JUSTICE TAX PREVENTION ACT"), the House floor schedule for this week and next, and the Senate floor log. Open every listed primary page before writing anything from it.

- A roll call on the bill: `python3 tools/roll_call.py <n>` (Senate) and add the record to `data/votes.json`; add a timeline event; update `data/overview.json` `latest` (date, one short sentence with the result, roll-call link) and `next` (only a scheduled step with a date). Keep the Overview opening line within four lines at 375px.
- A Record speech or statement on the bill is a coverage item (`type: gov_document`, `sector: congress`), quoted from the granule.
- When done: `python3 tools/refresh_status.py --write` records the newest roll numbers and today's date.

## 2. X posts

Follow REFRESH.md's X notes. Use `tools/x_collect.js` in the logged-in Chrome tab you created (never another tab; never post or like): `__xs.start(targets, {since, held})`, poll `__xs.status()`, read `localStorage["xs:results"]` in chunks. Targets: the handles in the newest `data/research/sweep-*/x-handles.txt` plus searches pairing the bill's name with the current fight. Date each post from its status id in America/New_York. Write `data/research/sweep-<date>/x-proposed.json`.

## 3. Articles

Web search plus fetch, never a search snippet. Wire, major outlets, trade press, law-firm alerts, think tanks, advocates, members' and committees' releases. Skip URLs in `held-urls.txt` (build it from data/media.json, media_extra.json and takes.json). Write `data/research/sweep-<date>/web-proposed.json`.

A research agent may do steps 2 and 3; give it `data/research/sweep-<date>/CONTRACT.md` (copy the newest one and change the window). Every item that asserts what the bill does carries `claims: [{text, speaker, about, sections_hint?}]` with the claim copied verbatim.

## 4. Integrate

Add chosen items to `data/research/media_extra.json` (map vocabulary; `press` → `media`), then `python3 tools/integrate_research.py`. Summaries come from the roll call or the Record, not an outlet's framing.

## 5. Claims to check (deterministic suggestions, human choice)

```
python3 tools/claim_sections.py pending      # claims on integrated items with no row in data/claims.json
python3 tools/claim_sections.py draft        # writes data/research/claims_draft.json with ranked sections + candidate spans
python3 tools/claim_sections.py suggest "<claim>"   # one claim
```

For each pending claim, read the suggested sections in the passed text (`data/bill/substitute_sections.json`, or `python3 tools/diff_bill.py --dump <n>`), pick the passage(s) a reader would compare the claim with, and add a row to `data/claims.json`: `media_url`, `speaker`, `quote` (the claim, verbatim from the page), `about` (a short neutral topic label), `review: [{section, text (verbatim span from the passed text), look?}]`. `look` names what to compare ("the deadline length", "which agencies are covered"), never whether it holds. The suggestions are a keyword ranking: confirm each by reading. A claim with no passage to point at (a forecast, a motive, a process complaint) goes in `skipped` with `why`. Then `make claims` must pass with 0 pending.

## 6. Gates (fix failures; never loosen a gate to get green)

```
make check                       # build, unit tests, data, claims, prose, design
make quotes                      # 0 missing; unreachable pages → make browser-quotes, then WRITE=1
make links
NODE_PATH=<scratch>/node_modules make final     # perf, reader paths, UAT, click crawl (~17–34 min)
```

Playwright: `npm i --ignore-scripts playwright@1.60.0` in a scratch directory. The reader-path step fails when any answer takes more taps than `tests/reader_paths.json` records, starts more than 0.25 screens lower, or disappears: the interaction budget. If a change shortens a path, `make paths WRITE=1` locks in the new numbers. Never raise a baseline to pass; if a design change must lengthen a path, say why in the commit. UAT scroll budgets in `tests/uat.cjs` work the same way: a raise needs a dated note.

## 7. Record and ship

Bump `DATA_AS_OF` in `tools/build.py` and `as_of` in touched data files; rerun integrate and build. Append dated learnings to REFRESH.md and an entry to docs/RUNLOG.md. Commit (plain-text model/agent disclosure, no AI co-author trailers or tool footers), push, open a PR. Review the diff yourself for at least two rounds (data accuracy against the primary pages, neutrality of every new sentence, code), wait for CI and the Codex review, fix findings, and squash-merge only when CI is green and no finding is unresolved. Nothing changed since main's data: no PR; say so in one line.

Finish with: each chamber's action (tallies, roll numbers), the next scheduled step, items and claims added, gate results, and the PR link or "no change".
