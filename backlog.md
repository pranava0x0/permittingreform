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
| medium | Timeline: FERC accepted PJM's 6.8 GW reliability backstop on 2026-09-29 but suspended it to 2027-02-28 over cost allocation, collateral and exit rules. Trump's March 2026 Ratepayer Protection Pledge, once a primary source is found. |
| medium | People leads: Rob Gramlich (Grid Strategies), Ari Peskoe (Harvard Electricity Law Initiative), Devin Hartman (Lighthouse Energy Institute), Nathaniel Keohane (C2ES). |
| medium | Section 2107 notes: say that section 228 covers only loads that connect after enactment (several outlets leave this out). |
| low | Per-section pages for search engines; the site is one page with hash routes. |
| low | Split `site/data/core.js` so the timeline, people and media load on demand. |
| low | Split the research schema's stance into "on this bill" and "on reform"; curation does this by hand now. |

## Release follow-up

- Finish `make infer` after the Sonnet session limit resets. At handoff: 401 supported, 12 flagged and 127 unchecked out of 540 statements. Review flags against sources; do not relabel them to make the gate pass.
- Extend semantic checking to current-law comparison cells, per-section prior-version notes and overview/research paraphrases. These are outside the current model check.
