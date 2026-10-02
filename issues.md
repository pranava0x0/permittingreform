# Issues

| Date | Area | Problem | Cause | Status |
|---|---|---|---|---|
| 2026-09-30 | parser | Printed line numbers stayed in the text after the first line of some pages. | Code bug: a number glued to a hyphen (`RE-15`) did not match, and the counter desynced for the rest of the page. | Fixed: the number may follow any non-digit; it is stripped only when it equals the expected line. |
| 2026-09-30 | parser | Wrapped section headings (`... LEVEL OF` / `REVIEW.`) leaked into the section text. | Code bug: the text began one line after the heading, not after its last wrapped line. | Fixed; `test_bill` covers heading text. |
| 2026-09-30 | parser | Each section ended with the next title's heading. | Code bug: the chunk ran to the next `SEC.` line. | Fixed: a trailing DIVISION, TITLE or Subtitle block is cut. |
| 2026-10-01 | site | Search results and full text rendered as `[object HTMLElement]`. | Code bug: `replaceChildren` was handed an array. | Fixed with a `fill()` helper. |
| 2026-10-01 | data | A hand-typed page cite was wrong (travel sanction: page 55 for 54). | Process: cites were typed. | Fixed: every cite is computed by `billtext.locate`; hand-typed pages removed. |
| 2026-10-01 | data | Notes on earlier versions misdescribed the SPEED Act (said it had no permit-certainty rule and kept ordinary remedies). | Written from memory before the text was read. | Fixed after reading H.R. 4776 (eh) and S. 4753 (rs) in full; `infer_check --scope compare` now checks those cells against the texts. |
| 2026-10-01 | data | "47 project types" in section 1402. The list has 46 named types and one catch-all. | Miscount. | Fixed in the summary and the comparison. |
| 2026-10-01 | data | The limitation periods for FAST-41 projects and highways were swapped. | Written from memory. | Fixed: 2 years for FAST-41, 150 days for highways. |
| 2026-10-01 | link check | A 308 redirect was reported as an error. | Python 3.9's urllib does not follow 308. | Fixed in `webfetch.read`. |
| 2026-10-01 | site | Overview tables scrolled sideways on a phone and hid the cite column. | CSS. | Fixed: rows stack under 640px. |
| 2026-10-01 | design | Small-caps labels above headings, a site title smaller than the page heading, a bill search box on pages with no bill text. | Design choices the owner rejected. | Fixed: labels removed, title enlarged, search moved to Overview and Bill. |
| 2026-10-01 | parser and citations | Six saved review findings: merged clauses, indentation, partial-word matches, split-heading cite offsets, extraction artifacts and stale PDF cache. | Parser and validator gaps. | Fixed; see docs/reviews/resolution.md and regression tests. |
| 2026-10-01 | search | Key-point objects were joined as strings; delayed page searches could redirect after a tab change. | Data shape and async lifecycle bugs. | Fixed; search regression and browser delayed-load test. |
| 2026-10-01 | verification | Fresh summary review blocked by Sonnet subscription limit. | External quota. | Open; 401 supported, 12 flagged, 127 unchecked. Visible on Overview and Method. |
| 2026-10-02 | link check | `check_links.py --only X` replaced `data/checks/links.json` with the one matching URL, dropping 240 saved results. | Code bug: a partial run wrote its subset as the whole file. | Fixed: a partial run merges into the saved results. |
| 2026-10-02 | data | Compare, data centers: the current-law cell said there was no federal rule. FERC's 1994 pricing policy already charges a new load the higher of embedded or incremental transmission cost, and the BAAJA cell left out the charge for both. | Written before the 1994 policy was checked. | Fixed in both cells, with a source. |
| 2026-10-02 | data | People listed Josh Siegel at E&E News; he moved to Punchbowl News in late September 2026. | Stale affiliation. | Fixed in curation with the Talking Biz News source. |
| 2026-10-02 | tests | `tests/uat.cjs` hard-coded 45 comparison rows and 94 media items. | Literal mirroring the data. | Fixed: counts come from `window.PR_DATA`. |

