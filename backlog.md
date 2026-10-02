# Backlog

| Priority | Idea |
|---|---|
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
