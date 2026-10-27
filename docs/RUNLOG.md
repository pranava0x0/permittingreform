# Run log

## October 1, 2026: interrupted-session recovery

Purpose: recover Claude's unfinished tracker; review code and evidence before initial GitHub sync. Tools: local Python/Node, saved research and review artifacts, official PDF fetch, Chrome/Playwright, GitHub CLI. No new subagents. Main-session token cost is not separately available.

Recovered six findings from the completed Python review; fixed them and added regressions. Inline frontend review fixed structured-point search and delayed navigation. Recovered 159 key-point citations. Updated BAAJA labels, overview qualifications and the design documentation. Strict quote, data, prose, contrast and browser checks passed.

Sonnet inference and a small availability probe were blocked by the subscription limit. No new inference verdicts were created. Cached verdict reconciliation exposes the unfinished coverage. Verdict: recovery and inline review were useful; further calls during the limit would add no evidence.

- 2026-10-02: PR 1 code/source review and follow-up agent access. Tools: git/gh, GitHub review API, primary-source web reads, browser source images/threads, Python checks, Node search tests and Playwright UAT. Tokens: not exposed by this session. No subagents. Useful: three inline defects corrected during concurrent merge; all sections now retrievable without JavaScript. Evidence: docs/reviews/pr-1.md.

## 2026-10-02 — PR 3 review and remediation

- Why: requested PR comments, fixes, data-center evaluation, full Claude parent transcript review and less phone scrolling.
- Tools: git/gh, local JSONL and source reads, three primary-source URL probes, cached quote checker, unittest, Node tests, bundled Playwright/Chrome. No dependency install, subagents or inference model calls.
- Tokens: not separately metered.
- Result: corrected data-center scope and quote totals; preserved comparison state across version changes and resizing; folded sections and added batches of 12. 74 Python + 13 Node tests; 60 browser states; quotes 158 bill + 282 web.
- Worth it: yes; browser checks reproduced defects the prior green offline run missed.

## 2026-10-04 — Data centers viewer tab, transmission speed provisions, and past bill comparisons

- Why: user request for web scrape ingest, dedicated data centers & speed viewer tab (`#/datacenters`), expanded transmission carrot/stick rows in past bill comparison, and statutory grounding across §§ 2102, 2107, 2108, 2109, 2110, 2111 without PII.
- Tools: git/gh, Python test/build suite, Node test suite, webfetch, local browser quote checker. No subagents spawned.
- Tokens: minimal interactive inline turns.
- Result: created `data/datacenters.json` (15 provisions with verbatim bill quotes); added `#/datacenters` tab in `site/index.html` and `site/app.js`; added 4 new rows (`non-firm`, `queue-speed`, `att-reconductoring`, `btm-power`) to `compare.bills`; enriched statutory points in `data/bill/analysis.json` and `data/bill/point_cites.json`; updated `tools/build.py`, `tools/check_quotes.py`, `tools/check_data.py`, `tests/test_build.py`. 78 Python unit tests + 14 Node search tests passing; quotes 173 bill verbatim + 290 web verified/browser.
- Worth it: yes; satisfies feature and comparison requirements while passing all test, quote, and slop gates.


## 2026-10-21 — Reader-question research for PR 9

- Why: requested research into what readers ask about the bill, to score whether the site answers each question and how many taps it takes at 375px (`docs/reader-questions.md`).
- Tools: one Haiku subagent, 2026-10-22 03:27–03:38 UTC (38 web searches, 49 page fetches, 23 shell calls, counted by tool-call id; no sub-agents), plus the main session reading X in the user's Chrome. Reddit was blocked in the browser tool and Bluesky search needs a login.
- Tokens: the subagent made 25 requests: 353K cache-write (5 min), 3.77M cache-read and 96K output tokens (deduplicated by request id, largest output per request), about 1.30M weighted. The main session's share is not separately metered.
- Result: 361 questions. 354 name a source URL across 110 pages; 14 of those were "same URL" placeholders matched to the page the raw log records. 203 come from the 41 pages the agent fetched and are the only ones counted. 151 come from search summaries whose page was never opened, so they are listed as unverified and left out of the counts. 7 name an outlet but no page and are listed as unchecked leads. Codex review found placeholder sources in the first draft (no URL, "same URL", a PBS link labelled King & Spalding); link text is now the URL's domain.
- Worth it: yes, with a caveat. The gaps (vote count, electricity prices, emissions, time saved, amendments) and the slow Compare paths came straight from it. But 151 of the 354 linked entries rest on search summaries and are not counted, so the counts cover 41 pages and show which topics come up most, not how many people asked.
