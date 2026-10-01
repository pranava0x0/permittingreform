# User acceptance tests

October 1, 2026. Local Google Chrome, headless Playwright. Served `site/` at port 8766. Runner: `tests/uat.cjs`.

| Coverage | Result |
|---|---|
| 375×812, 768×800, 1280×800; light and dark | 48 rendered states passed |
| Overview, index, section, comparison, timeline, people, media, method | Nonempty DOM and expected record counts |
| Horizontal overflow | None at tested widths |
| Search | Travel-sanction search opens and highlights its cited passage |
| Media | Empty search, reset and source-type filter work |
| People and timeline | Outside-government and milestone counts match the data |
| Theme and keyboard | Toggle changes theme; skip link reaches main content |
| Delayed bill download | Switching to Media prevents stale search redirection |
| Console | No page errors in the view matrix |
| Visual inspection | Phone overview and section; desktop comparison; restrained typography, readable tables and citations |

Captures are local under `uat-screenshots/`; machine results are in `.test-artifacts/uat.json`. The runner repeats the checks without those artifacts. This pass does not assert full screen-reader compatibility or independently verify every research claim.

October 1 mobile refinement: one-line title, compact theme icon, collapsible bill details and first provision above 400px at 375px width verified in both themes. Dark secondary text reaches 7:1; control borders reach 3:1.
