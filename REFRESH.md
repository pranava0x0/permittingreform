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

## Outside readings

`data/takes.json` holds readings of what a section would do, from named industry groups, advocates, law firms, scholars and analysts. Each take quotes its source verbatim, names its sections, and may name the bill `passage` it argues over (a verbatim span the build locates and cites). `claim` is this site's one-sentence paraphrase of their reading, so it goes through the prose lint.

1. Add takes by hand or from a research agent's file. Map sections yourself: agents guess wrong (an ESA definition filed under 1106, a completeness clock under 1106 instead of 1109).
2. Drop pieces written before the text was public (September 30, 2026) and anything known only from a search snippet.
3. `python3 tools/check_quotes.py`. A page that refuses scripts needs a read in a browser, recorded in `data/checks/browser.json` with the exact quotes.

## Claim cites

Every sentence that says what the bill does must carry a passage from the bill: summary sentences and key points (`data/bill/point_cites.json`), and headlines, the comparison tables' BAAJA cells, added provisions and the Communities and Data centers rows (`data/bill/row_cites.json`). `tools/infer_check.py` writes both from verdicts whose evidence span is in the text word for word. The build stops while any claim has no passage or a flagged verdict. A claim that the text is silent ("No export provisions.") counts once the review supports it with no span.

After editing any of that prose, run `python3 tools/infer_check.py`, fix or reword what it flags, and rerun until it exits 0.

## Gates

`make check` before every commit. `make links`, `make quotes` and `make infer` after any data change. `make check` fails while a claim lacks a bill passage, so run `make infer` first.

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
- 2026-10-02. Paywalled POLITICO and Pro stories: read the free part through `https://r.jina.ai/<url>` and record the item as read from a preview; use facts only from the readable part. Wayback holds no readable 2026 capture. Find URLs through the Wayback CDX index or `rss.politico.com`.
- 2026-10-02. A research agent's `stance` field drifts toward "position on reform" unless the brief says "stance on the September 30 bill". Re-check stances for new people before integrating.
- 2026-10-02. New rows the main session selects from an agent file go in `data/research/<name>_extra.json`; edits to held rows go in `data/curation.json` with a reason. Run the duplicate check (URL, title, same-day events) after integrating.
- 2026-10-02. Agent exports come from tools/build.py. Rebuild Markdown, HTML, JSON and sitemap together; do not edit generated files. Each section Markdown file includes the saved review limits. Run the export parity tests before publishing.
- 2026-10-05. Every sentence is a claim. A 4-word floor had exempted "10 years.", "150 days." and "ERCOT is excluded." from both the review and the cite. The sentence splitter also broke "D.C. Circuit." into two claims; it now knows "D.C." and "U.S.".
- 2026-10-05. Changing the splitter changes claim ids. Stop a running `infer_check.py` and restart it rather than reconcile two runs; unchanged batches come back from the cache.
- 2026-10-05. X bookmarks and the Following feed: the Following timeline loads a few posts per scroll and stalls the page; `filter:follows since:YYYY-MM-DD` search returns the same accounts by keyword. Store results in `localStorage` between navigations and save every scroll, because a long script times out at 45 seconds and loses unsaved results.
- 2026-10-05. Reddit refuses both the search tool and the Chrome extension. Leave it out of a sweep rather than retry.
- 2026-10-05. Punchbowl's document links (`punchbowl.news/<name>/`) are attachment pages that serve scripts an empty shell. Cite the PDF under `punchbowl.news/wp-content/uploads/`, which the quote check can read.
- 2026-10-05. The Senate Press Gallery floor log (`dailypress.senate.gov/<weekday-month-day-year>/`) states the next scheduled vote and the legislative vehicle.
- 2026-10-05. `infer_check.py` now asks only about claims with no usable supported verdict for their current wording; `--all` re-asks everything. After rewording 40 claims it asked 61 of 807 in 8 batches, against a full run of 25 batches (about two hours and $2 to $3, most of it re-confirming unchanged claims).
- 2026-10-05. The model sometimes joins two passages with "..." in its evidence. `usable_span` keeps the longest piece that is in the text word for word; a supported claim with no usable piece is a gap, not a flag, and needs a passage found by hand.
- 2026-10-18. Haiku research agents on a 12-day window: one agent per source family (letters, Congress, press, X) with the held-URL, held-title and held-people lists in the brief. The not_found list is as valuable as the items; keep it. Each ran 130K to 190K tokens.
- 2026-10-18. X keyword search returned almost nothing useful (2 items from 10 queries). Read account timelines instead: navigate to x.com/<handle> and pull `article` nodes with their `time[datetime]` and `/status/` hrefs in one javascript call. Give the agent a tab it created itself.
- 2026-10-18. Bluesky keyword search is blocked for unauthenticated clients (403 public API, 401 bsky.social); getAuthorFeed on known handles works.
- 2026-10-18. Paywalled Punchbowl stories sometimes render in full in Chrome (Oct 13 tribal story) and sometimes only as a preview (Oct 5 letter story). Washington Times renders in full. Chamber letters are PDFs under uschamber.com/assets/documents and fetch with tools/webfetch; NAM posts its coalition letters as pages under nam.org with the signer list on a separate link.
- 2026-10-18. Sign-on letters carry a `letter` object on the media row: to, signer_count, signers_sample, ask. Count what the document says; if it gives no count, count the signature block and say so in the curation reason.
- 2026-10-20. X search returned useful results this time when queries paired the bill's name or "permitting bill" with the specific fight (Section 106, NHPA, THPO, sacred sites, NCAI, NATHPO). Strip `? & = ; %` from collected text before returning it from a javascript call, or the extension's filter blocks the whole result; for long results, write them into the page and read with get_page_text.
- 2026-10-20. Disputed readings live in `data/positions.json` under an issue's `disputes`. Each reading is a take in `data/takes.json`; the build locates every passage and rejects a supporting take filed under "against" (or the reverse). A side with no reading renders as none found, which is the honest state, not a gap to fill.
- 2026-10-26. X collection is a script now: paste `tools/x_collect.js` into the browser's javascript tool on any x.com page, run `__xs.start([...paths], {since, held})`, poll `__xs.status()`, then `__xs.dump()` and read the page with get_page_text. It moves between timelines and searches with in-app navigation and saves to localStorage on every scroll, so a reload loses nothing. Pass held status ids so posts already in the data are skipped. 235 posts in one run; 37 became media items.
- 2026-10-26. A pinned post carries its old date and sits at the top of a timeline, so a collector that stops after a few older posts quit on accounts whose pinned post was months old. Reposts also carry the original date but count as recent activity. The collector now tells them apart by the social-context line ("Pinned" versus "reposted").
- 2026-10-26. To pull selected posts after a dump, read `localStorage["xs:results"]` by id in a javascript call rather than searching the dumped text; the dump breaks the X app until reload.
- 2026-10-26. `data/speed.json` holds the Speed page. A blocker's passages must come from sections the row names, each found exactly once; its readings are take ids. Studies cited there go through `make quotes` like takes. A cause the bill does not address keeps an empty `sections` list, and the page says no section is aimed at it.
- 2026-10-26. A web research agent returns media types, sectors and stances outside the vocabulary (letter, statement, preservation, legal_analyst) and takes without ids. Map them in a merge script before integrating; `integrate_research.py` rejects the rest with a clear error.
- 2026-10-26. `tests/uat.cjs` and `tests/clicks.cjs` need Playwright, which is not installed globally. Install it in a scratch directory (`npm i --ignore-scripts playwright` there) and run `NODE_PATH=<dir>/node_modules node tests/uat.cjs` while the site is served. Run both after any data refresh: more events in a month or more disputes on an issue change page heights and batch boundaries.
