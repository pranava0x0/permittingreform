# Backlog

| Priority | Idea |
|---|---|
| medium | Disputed readings for other contested issues on the Positions page, using the same shape (`data/positions.json` disputes: question, bill passages, takes on each side): lawsuit limits (section 1110 remand without vacatur), data center costs (section 2107 20 MW floor), and transmission backstop siting. Tribal consultation shipped first on 2026-10-20. |
| high | Re-run the parser and re-read changed sections when the manager's amendment is posted (see REFRESH.md). |
| high | Enable GitHub Pages by running the `pages` workflow, then submit the sitemap. |
| medium | Add Reddit threads by hand; no tool could reach the site. |
| medium | A third comparison column for the amended Senate text, once it exists. |
| medium | An implementation calendar: every rulemaking and report the bill orders, with its deadline. |
| medium | Promote the six phrases flagged on 2026-10-01 from `tools/slopcheck.py` here to the registry in coding-best-practices. |
| medium | Choose a license for the repository. |
| high | Media candidates still open from the 2026-10-02 X sweep: Canary Media and Utility Dive on transmission, the C2ES/Greenline modeling release, Grayson Flood's thread (his data-center image did not render in the browser), Siegel posts (Cramer "significant improvement"; White House support), Regunberg, Huffman, Pomerantz, Christian Fong's RMI chart on local transmission spending, Alex Mechanick's Artificial Weights explainer, and the Sierra Club reaction (needs a browser read). Heatmap, Green Tape, Mackenzie, Mathew and Hausfather were added. |
| low | Timeline: FERC's September 29 PJM backstop order is cited through trade press; add the eLibrary order once readable. |
| medium | People leads: Rob Gramlich (Grid Strategies), Devin Hartman (Lighthouse Energy Institute), Nathaniel Keohane (C2ES). |
| low | Per-section pages for search engines; the site is one page with hash routes. |
| low | Split `site/data/core.js` so the timeline, people and media load on demand. |
| low | Split the research schema's stance into "on this bill" and "on reform"; curation does this by hand now. |

## Release follow-up

- Finish `make infer` after the Sonnet session limit resets. At handoff: 401 supported, 12 flagged and 127 unchecked out of 540 statements. Review flags against sources; do not relabel them to make the gate pass.
- Extend semantic checking to current-law comparison cells, per-section prior-version notes and overview/research paraphrases. These are outside the current model check.
| medium | Read the Heatmap pieces the sweep skipped for budget: trump-wind-energy-prices (6/17), pjm-interconnection-reforms (7/28), trump-gas-plant-permits (8/21), the transmission costs Q&A (9/4). |
| medium | Senate Data Center Transparency Act (Blunt Rochester, Curtis, October 1): add to the data center bills list once it has a number and text. |
| low | Restore `tests/uat.cjs` coverage: install Playwright after the advisory check, add checks for brief lists, phone comparison rows and the Communities view. |

| medium | Asset URLs carry a hand-bumped `?v=N`; a CSS or JS change without a bump serves stale files to returning readers (found 2026-10-02 at v=4). Stamp a content hash in `tools/build.py` instead. |
| medium | Outside readings still missing for specific provisions as of 2026-10-05: utilities (EEI, NRECA and APPA posted holding statements only), hyperscalers and data-center groups, tribal governments (Section 106 and ESA), labor, and anything on section 1121 (eNEPA) or the offshore sections. |
| medium | Media candidates from the 2026-10-05 sweep: the WSJ editorial "Permitting Reform at Last, Really?" (CAPTCHA wall), Forbes (Broughel, October 5), Inside Climate News (October 2), CleanTechnica (October 2), Washington Examiner's Daily on Energy on data centers, mgrid.org, EPIC's AI analysis of the bill, Third Way's interview with Josh Freed, and the Central Air podcast with Jane Flegal. David Roberts records a Volts episode with Daniel Palken on October 7. |
| low | Beveridge & Diamond's reading that Section 106 consultation could end without an agreement has no bill passage attached; find the clause in section 2301. |
| low | `infer_check.py --all` packs units into batches in order, so one early edit shifts every later batch and misses the cache. Pack by a stable key (one batch per bill title). The default incremental run avoids most of the cost. |
| high | Run `python3 tools/infer_check.py` once the `claude` CLI is logged in again (its OAuth session expired on 2026-10-06). 18 claims carry verified passages but no review verdict: 16 reworded or newly split sentences and 2 the model skipped (2241.s1, 2251 as renumbered). The Method page reports them as unchecked. |
- Walled items from the 2026-10-18 sweep still unread: Punchbowl Oct 5 letter story (premium preview only), Punchbowl "Key House boost" Westerman story (404 at the guessed URL), Axios Oct 1, 5 and 8 Future of Energy items (403), Law.com Oct 14, National Review shot-clock piece. Priority: low.
- Null results worth re-checking after the Nov 9 vote: CPC, CHC, CBC, Problem Solvers, New Dems (Sept 30 only), Schumer and Jeffries statements, Statement of Administration Policy on S. 5653, IBEW endorsement (Heatmap Oct 7 says still pending), Data Center Coalition position (Axios Oct 8 says reviewing), EEI/NRECA/APPA on the transmission backstop. Priority: medium.
- USET tribal joint letter PDF (Oct 9) 404s at the guessed URL; NARF's summary page is the only copy. Find the letter on usetinc.org or narf.org and quote it. Priority: medium.
| high | Reader gap (docs/reader-questions.md, 2026-10-21): will it pass. Count declared senators against the 60 needed for cloture and say what the House would do with a Senate bill; cite whip counts and statements, not predictions. |
| medium | Reader gap: electricity prices. Readers ask whether the bill lowers household bills; cite published modeling (for example the C2ES/Greenline release) with its assumptions, beyond the data center cost section. |
| medium | Reader gap: emissions. Cite the published emissions modeling and the arguments on each side (Flegal, Roberts threads in the X notes). |
| medium | Reader gap: time saved. Link Columbia CGEP's time-saved tool (posted October 21) and the transmission-vs-gas permitting durations it reports, once the numbers are read from the tool itself. |
| low | Reader paths into Compare are long at 375px: the SPEED Act lawsuit deadline takes 4 taps (Bill, Compare, SPEED Act chip, the row) and who pays for transmission takes 3 taps and 3.1 screens. Links from the Lawsuit limits and Transmission siting provisions to their open comparison rows would make each 2. |
