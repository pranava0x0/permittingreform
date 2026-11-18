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

## November 15, 2026: Senate votes, published estimates, coverage through November 15

`tests/uat.cjs` passed 96 rendered states at 375, 768 and 1280 pixels. Cold load by `tools/perf_audit.cjs` at 375×812 on Slow 4G with a 4x slower CPU. Before is `main` on November 15 before any change (`.test-artifacts/perf-before.json`); after is this branch (`perf-final.json`). Transfer is gzip bytes from the audit's own server.

| Page | Requests | Transfer KB | Slow 4G ready ms | Layout shift (CLS) | Screens |
|---|---|---|---|---|---|
| overview | 8 → 8 | 226 → 233 | 1540 → 1603 | 0.134 → 0 | 2.3 → 2.4 |
| bill index | 8 → 8 | 226 → 233 | 1538 → 1524 | 0.277 → 0 | 1.2 → 1.3 |
| section 1101 | 9 → 9 | 328 → 335 | 1554 → 1548 | 0.885 → 0 | 4 → 4 |
| compare | 8 → 8 | 226 → 233 | 1548 → 1540 | 0.885 → 0 | 10.1 → 10.1 |
| amendments | 9 → 9 | 304 → 311 | 2094 → 2095 | 0.328 → 0 | 3.8 → 4.1 |
| positions | 10 → 10 | 393 → 425 | 2520 → 2617 | 0.373 → 0 | 3.6 → 4.3 |
| people | 9 → 9 | 363 → 395 | 2522 → 2539 | 0.331 → 0 | 3.7 → 3.7 |
| data centers | 8 → 8 | 226 → 233 | 1517 → 1520 | 0.885 → 0 | 2.6 → 2.5 |
| communities | 8 → 8 | 226 → 233 | 1527 → 1543 | 0.885 → 0 | 4.4 → 4.3 |
| speed | 9 → 9 | 255 → 262 | 1510 → 1509 | 0.778 → 0 | 1.7 → 1.7 |
| timeline | 9 → 9 | 363 → 395 | 2524 → 2527 | 0.137 → 0 | 1.6 → 1.6 |
| coverage | 9 → 9 | 363 → 395 | 2557 → 2530 | 0.176 → 0 | 3 → 3.3 |
| method | 8 → 8 | 226 → 233 | 1510 → 1517 | 0.134 → 0 | 2.6 → 2.6 |

Layout shift is 0 on all 13 pages. Before, a sub-page first drew the Overview shell and then replaced it, so its largest paint came at about 750 ms and the page then jumped. The largest paint is now the page's own content and lands with the ready time (1.5 to 2.6 s on Slow 4G). Positions, People, Timeline and Coverage grew about 32 KB: the news bundle carries two roll calls of 100 names each, 18 estimates and 70 more coverage items (333 to 403).

Reader paths from the Overview at 375×812 (`tools/reader_paths.cjs`, taps · screens down the page). The first column is `main` after PR 20; 24 other paths did not move.

| Question | Path id | After PR 20 | Now |
|---|---|---|---|
| Who is for it and who is against it? | `who-for-against` | 2 · 1.09 | 2 · 1.48 |
| Why do the groups split? | `why-split` | 2 · 2.04 | 2 · 2.74 |
| Is the tribal consultation claim right? | `tribes-dispute` | 3 · 0.91 | 3 · 1.27 |
| Positions on one section | `bill-positions` | 1 · 1.01 | 1 · 1.37 |
| How it differs from earlier bills | `vs-earlier-bills` | 1 · 1.93 | 1 · 2.04 |
| Agency deadlines | `agency-deadlines` | 1 · 1.81 | 1 · 1.92 |
| How did the Senate vote? | `senate-votes` | new | 1 · 0.61 |
| How did each senator vote? | `how-each-senator-voted` | new | 2 · 1 |
| Did a senator vote the way they said? | `stated-vs-vote` | new | 2 · 0.9 |
| Published emissions estimates | `estimates-emissions` | new | 2 · 2.18 |
| Published electricity cost estimates | `estimates-prices` | new | 2 · 2.24 |
| Published estimates of time saved | `estimates-time` | new | 2 · 2.51 |

Senate votes sits first on Positions, so letters, the issue rows and a section's positions start 0.4 to 0.7 screens lower than before. The Positions scroll budget in `tests/uat.cjs` moved from 4 to 4.75 screens.75 screens for the two new folded sections; letters show the newest six, with the rest behind one control.

`tests/clicks.cjs` passed: 184 views loaded and 5,023 controls clicked at 375 and 1280 pixels (163 hidden, 2 disabled), 0 problems, about 34 minutes. Slowest click 7,575 ms (Compare, a bill-text link); 7 clicks took over a second.

**Tab separators (same day).** A short vertical rule now sits between neighbouring tabs and between neighbouring subtabs. It is drawn over each link's left edge and takes no room: at 375 pixels the five tabs and five subtabs keep the same boxes, the header still ends at 138 pixels and the page heading starts at 154, so taps and screens to every answer are unchanged.

## November 18, 2026: managers' amendment and filed amendments

`make final`: perf, reader paths and UAT (102 rendered states) pass; the click crawl loaded 186 views and clicked 4,845 controls with 0 problems (none over 1 s). The first UAT run failed: two new status lines and a longer next-step line pushed the fourth provision 20 px below the first phone screen. The next-step line is shorter now. Before is `main` at 78772f9, cold load at 375x812, Slow 4G.

| Page | Requests | Transfer KB | Slow 4G ready ms | CLS |
|---|---|---|---|---|
| overview | 8.0 → 8.0 | 235.0 → 236.0 | 1506.0 → 1509.0 | 0.0 → 0.0 |
| bill index | 8.0 → 8.0 | 235.0 → 236.0 | 1492.0 → 1495.0 | 0.0 → 0.0 |
| section 1101 | 9.0 → 9.0 | 338.0 → 339.0 | 1507.0 → 1522.0 | 0.0 → 0.0 |
| compare | 8.0 → 8.0 | 235.0 → 236.0 | 1511.0 → 1510.0 | 0.0 → 0.0 |
| amendments | 9.0 → 9.0 | 314.0 → 325.0 | 2493.0 → 2499.0 | 0.0 → 0.0 |
| positions | 10.0 → 10.0 | 426.0 → 433.0 | 2497.0 → 2512.0 | 0.0 → 0.0 |
| people | 9.0 → 9.0 | 396.0 → 404.0 | 2493.0 → 2495.0 | 0.0 → 0.0 |
| data centers | 8.0 → 8.0 | 235.0 → 236.0 | 1484.0 → 1505.0 | 0.0 → 0.0 |
| communities | 8.0 → 8.0 | 235.0 → 236.0 | 1486.0 → 1491.0 | 0.0 → 0.0 |
| speed | 9.0 → 9.0 | 265.0 → 266.0 | 1484.0 → 1495.0 | 0.0 → 0.0 |
| timeline | 9.0 → 9.0 | 396.0 → 404.0 | 2487.0 → 2501.0 | 0.0 → 0.0 |
| coverage | 9.0 → 9.0 | 396.0 → 404.0 | 2489.0 → 2502.0 | 0.0 → 0.0 |
| method | 8.0 → 8.0 | 235.0 → 236.0 | 1481.0 → 1487.0 | 0.0 → 0.0 |

The Amendments page grew 11 KB for the 172 filed amendments; its ready time did not move.

## November 18, 2026 (afternoon): roll calls 266 to 268 and the Votes page

Roll calls moved off Debate to their own page, Bill → Votes (`#/votes`). Findings on the way:

- The first UAT run failed the Positions scroll budget at 375 px (3,972 px against 3,857): each roll call added a row.
- The stated-position table would have shown three columns headed "Nov 18 vote"; headers now name the roll call.
- Moving the votes off Positions put Disputed readings near the top, and its late-loading list shifted the letters below it (Slow 4G CLS 0 → 0.039). The folded rows now draw at once and only their bodies wait for the readings; CLS is 0 again.
- A misplaced edit broke the bill section "What others say" block; `make check`, perf and reader paths all passed, and UAT caught it by timing out on `#/bill/sec/1106`.

Perf against `main` at 2c2e667 (cold load, 375x812, Slow 4G): Positions 433 → 435 KB, 2,512 → 2,513 ms ready, CLS 0 → 0; the new Votes page is 9 requests, 405 KB, 2,494 ms ready, CLS 0, 1.3 screens. Other pages within 25 ms.
