# REFRESH.md: how to bring this tracker current

Project playbook for the `data-refresh` skill. Two things go stale: the bill text and the research.

## A new bill text

The sponsors expect a manager's amendment before the Senate votes. Page and section numbers will move.

1. Download the new PDF to `site/bill.pdf`. Update `source_pdf`, `mirror_pdfs`, `draft_id` and `released` in `tools/parse_bill.py`.
2. Run `python3 tools/parse_bill.py` using an environment with pypdf. The parser automatically re-extracts when the PDF hash changes; do not install dependencies without the advisory check required by AGENTS.md. It must report as many parsed sections as the table of contents lists and exit 0.
3. Run `python3 tools/build.py`. Each quote that changed or moved fails with its section number. Fix the quote in `data/bill/analysis.json`, the passage in `data/bill/point_cites.json`, or the row in `data/overview.json`.
4. Re-read each section whose text changed and update its summary. `git diff data/bill/sections.json` shows which.
5. Run `make infer`, then `make check`.
6. Keep the old text: add it to `data/prior_bills/` and to the comparison if the changes matter.

`HEADER_RE` in `parse_bill.py` matches the running header of the September 30 draft (`KAT26642 TWY S.L.C.`). A new draft has a new header.

## Research

1. Add events, people and coverage to `data/research/*_extra.json`, or rerun a research agent and replace `data/research/*.json`.
2. Put corrections in `data/curation.json` with a reason. Do not edit the agent files.
3. `python3 tools/integrate_research.py && python3 tools/build.py`
4. `make links && make quotes`, then set `DATA_AS_OF` in `tools/build.py` and rebuild.

## Gates

`make check` before every commit. `make links`, `make quotes` and `make infer` after any data change.

## Known limits

See [docs/data-sources.md](docs/data-sources.md) for sources that refuse scripts and the routes that work.

## Learned

- 2026-10-01. Page numbers typed by hand were wrong for the travel sanction (page 54, not 55). Cites are computed from the parsed text; never type one.
- 2026-10-01. A summary can borrow a fact the bill does not state (a case name, who asked for a provision). The inference check flags these; delete them or move them to a note with its own source.

- 2026-10-01. `python3 tools/infer_check.py --cached-only` reconciles saved verdicts without model calls. It exits nonzero while claims remain flagged or unchecked; this is not a fresh semantic review. Input fingerprints make stale results visible after source edits.
- 2026-10-01. After research integration, inspect duplicate URLs and names as well as quotes. After rebuilding, rerun `tests/uat.cjs` against the served output.
- 2026-10-02. X: `webfetch.read` (oEmbed) returns only the first post of a thread and cuts long posts at about 280 characters. Read threads, long posts and attached screenshots in a browser; numbering can skip (Flegal's 15-post thread has no post 9). Expand t.co links with `curl -sI` to find the article a post cites.
- 2026-10-02. X search: `since:` plus `min_faves:` on the Top tab returns about 10 to 20 posts per query, so run several narrow queries (data centers, transmission, Ratepayer Protection Act, utilities, opponents) instead of one broad one. Bookmarks now sit under History at `/i/history`.
- 2026-10-02. Port 8766 may already be serving the main checkout. From a worktree, check `lsof -a -p <pid> -d cwd` before trusting a page on that port, and preview on another port.
- 2026-10-02. Cheat sheets: a media item may carry `visuals: [{title, text, url}]` for a summary image. The site links to the image on X and describes what it sorts; it does not copy the image. Read the image in a browser and check its claims against the bill before writing the description.


- 2026-10-02. Agent exports come from tools/build.py. Rebuild Markdown, HTML, JSON and sitemap together; do not edit generated files. Each section Markdown file includes the saved review limits. Run the export parity tests before publishing.
