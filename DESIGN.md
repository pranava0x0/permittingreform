# Permitting Reform design

A committee reading room: dark green masthead, cream paper, compact rows and numbered provisions. The bill and its citations carry the page. This is an independent tracker, not a Senate website.

## Type and color

Self-hosted Raleway for headings and Open Sans for controls and prose. Statutory text uses the system serif stack. Fonts and their licenses live in `site/fonts/`.

Colors live in `site/styles.css`: cream `--bg`, green `--brand` and `--rule`, blue citation links, yellow search marks and selected-tab underline. Dark mode has matching tokens. Contrast tests check text at 4.5:1 and rules/focus at 3:1.

## Layout

The site title dominates the masthead. Five top tabs (Overview, Bill, Effects, News, Method) fit a 375px screen; Bill, Effects and News open a subtab row at the top of the view (Sections and Compare; Data centers and Communities; Timeline, Media and People). Every page keeps its own route. Nine tabs in one scrollable row left five of them off screen on a phone, with nothing to show they existed (2026-10-05). BAAJA is the bill label; its full title and source links expand under Bill details. Search appears on Overview and bill views. Main provisions precede status and sponsors.

Hairline rules divide rows. Avoid cards, shadows, gradients, eyebrow labels and promotional metrics. Comparison tables become labeled rows on phones; the BAAJA column has a pale green background on larger screens. Each statutory paragraph has a page-and-line gutter linked to the PDF.

Use 375×812, 768×800 and 1280×800 for browser checks. Verify DOM counts before screenshots. The mobile masthead title stays on one line. The 18px theme icon keeps a 44px hit area. Controls on touch devices have a 44px minimum height. Preserve keyboard focus and the skip link.

## Editorial rules

Describe proposed changes as proposals. Keep dates, triggers, exceptions and affected parties explicit. Authorization of funding is not appropriation. An agency decision deadline is not a promise of approval.

Use BAAJA for the September 30, 2026 draft; SPEED Act for the House-passed H.R. 4776; EPRA 2024 for reported S. 4753. A numbered list is a reading aid, not a ranking.

AI-assisted summaries are labeled. Verbatim text uses the source's words. A matching quotation proves occurrence, not the accuracy of every nearby claim. Show incomplete review coverage on Method. Do not describe a partial AI check as complete verification.

Dark mode uses brighter secondary text (at least 7:1 against reading surfaces), explicit placeholder colors, visible control borders and pale-green selected controls. Topic badges are omitted from the mobile index and section metadata.

## Phones first

Most readers use a phone. For every UI change, measure page height in screen-heights at 375×812 and the taps needed to reach the key fact, before and after.

- The tabs stay pinned; the title row scrolls away. Clicking the current tab returns to the top.
- Long lists open brief: one line per timeline event, two lines of summary for media and people, a More button for the rest. "Full entries" turns brief mode off.
- Below 1024px, where comparison tables stack (phones and tablets), each comparison row opens on tap and shows BAAJA beside one version picked with the "BAAJA vs." chips. The bill index folds by title at the same width.
- Filter chips sit in one swipeable row on phones.
- Pages with three or more headings get an "On this page" row of jump links.
- The Timeline opens with one horizontal dated line that marks only the milestones (circle Congress, square White House and agencies, diamond courts). A mark opens its event inside its month (`#/timeline/<month>/<id>`); arrows step between milestones. Event rows show a short date and a two-line title. Do not chart every event: a per-month bar chart was tried and rejected on 2026-10-02.

Measured October 2, 2026 at 375×812, in screen-heights: Timeline 2.2 to 1.7 after the milestone line (first screen shows 6 events, was 3); Compare 43 to 9, data center bills 13 to 2, Timeline 14 to 7, People 20 to 6, bill index 16 to 1, Communities 28 to 4 (one line per change).

## PR 3 reading flow

Overview provisions and secondary sections use native disclosures. Communities groups fold by subject. Comparison tables stay open (see 2026-10-20 below). Overview links directly to the data-center table. Long lists start with 12 entries; each load-more adds at most 12 and focuses the first new entry. Filters restart at 12. Milestone jumps reveal events outside the batch. Comparison rows retain their open state when the counterpart changes and stay operable after rotation. Source passages expand within comparison cells.

Communities groups stay open with a count in each heading; the rows themselves are one line each. Folding both the groups and the rows hid all 46 changes behind closed headings (2026-10-02).

Measured October 2, 2026 at 768×1024 after the tablet change: Compare 2.3 screens (was 11.9), data center bills 1.8 (was 11.3), bill index 1.0 (was 9.4). `tests/uat.cjs` enforces scroll budgets at 375 and 768.

## Cites and readings (2026-10-05)

Every sentence that says what the bill does ends in a small "p. N" link. It opens the section's text with the cited lines marked; the line gutter there links to the PDF. Outside readings sit under "What others say it would do" on each section page: brief rows (stance, who, their claim) that open to the verbatim quote, the source and the bill passage. The first rows alternate stances so a reader sees the disagreement without opening More. Readings load with the first section page that needs them.

Measured at 375×812, before and after: the next Senate vote moved from 1.1 screens down the Overview to the first screen; Data centers went from a swipe of the tab row plus a tap to one tap; a provision's critiques are two taps from the Overview (open the provision, then "What others say"); the readings block costs 0.73 screens on a section page with three rows shown.


## Positions (2026-10-18)

A fourth News subtab answers "who is for and against" on one page. Three blocks, in the order a reader asks: the letters and joint statements (date, stance, signer count, title; each opens to recipients, the ask, sample signers, the quote and the source), the voices on each issue (For, Against and Mixed under the issue's cited headline, four shown and the rest behind one chip), and a by-sector table whose counts link into the People page with the sector carried in the route. Only statements dated on or after the bill text's release count as voices on an issue; earlier statements were about prior bills or reform in general. The Overview carries one line, "Who's for and against: N support, N oppose", on its first screen; the letters count was left off because the line wraps at 375px with it.

Measured at 375×812: the page is 3.1 screens with every row closed (the budget is 4), the first letter row sits on the first screen, and the first letter's signers are two taps from the Overview (the link, then the row), with the signers at 0.93 screens. No horizontal scroll at 375, 768 or 1280; the sector table is 640px wide at 768. Light and dark both render; the only sub-44px targets are inline text links and the masthead, which are exempt.

## Overview first screen and Positions budget (2026-10-20)

The Overview's first phone screen carries, in order: the bill name, the next vote, the for-and-against line, the review status, search, the data center bills link and the "On this page" row. The next vote (2026-10-05) and the for-and-against line (2026-10-18) were put there on purpose, so the first provision can no longer start in the top half of a 375×812 screen; that UAT rule, from 2026-10-01, had been failing since the next vote was added. The rule is now that five of the ten provisions fit the first screen. To make room, the next-vote line drops the clause about the November 3 election and the data center link reads "Compare data center bills" on one line.

Disputed readings on Positions show four questions per issue and the rest behind one chip, as the voices on each issue do. Eight tribal consultation questions had taken the page past its 4-screen budget, and each issue the backlog adds would have added about half a screen.

Measured at 375×812, before and after: the first provision moved from y 600 to 528, with the fifth provision's bottom at 825 (below the fold) to 753; the Overview went from 1.85 to 1.76 screens; Positions went from 4.05 to 3.77 screens, and every dispute question past the fourth costs one tap. An Overview link to an event outside its month's first 12 (October has 22) now opens that event on screen in one tap; it opened nothing before.

## Compare tables open; subtabs and jump links read as controls (2026-10-20)

The reader preferred the earlier Compare page, where every subject table was open beside the other bills. Folding the six groups behind closed headings hid the table view this page exists for, so the groups render open again at every width; only the rows still open on tap below 1024px. Cost at 375×812: Compare grows from 3.7 to 9.8 screens (budget raised from 4 to 11 in `tests/uat.cjs`); the subject chips stay pinned, so any group is one tap away. Long column headers in the data center bills table now wrap instead of running into the next column.

Subtabs sit in a tinted track with the current page filled, so they read as a second row of tabs rather than a line of bold text. "On this page" jump links carry a label and render as outlined pills with a down arrow, distinct from the grey filter chips. Section-page cross links (`.sec-links`) are semibold with a thicker underline. Page height cost: +0.02 screens at 375×812.

## Subtabs as folder tabs (2026-10-21)

The tinted track from 2026-10-20 still read as links, and its filled current page looked like a pressed filter chip. Subtabs are now folder tabs on a 2px rule: the other pages sit behind in the tint with muted text, and the current page has a thick top edge, bold text and the page background, so it joins the content below. On phones the tabs split the full width equally (News: four tabs of about 85px; "Compare with earlier bills" wraps to two lines inside its tab), so all of them show without sideways scrolling. Every subtab is at least 44px tall at every width. Filter chips stay small rectangles with gaps between them, and jump links stay outlined pills with a down arrow; none of the three uses the others' shape. `tests/uat.cjs` checks that the subtab row fits one line without clipping, that every subtab is at least 44px tall and that exactly one is current.

## One filter row per page; the rest behind More filters (2026-10-21)

Reader research (`docs/reader-questions.md`: 361 questions from 111 pages and X threads) found the Overview already answered most common questions in one tap. The clutter readers ran into was on the inner pages: Media showed three chip rows and a topic box before its first item, and Data centers and Communities each opened on two chip rows plus a jump row. Three approaches were weighed:

1. Fewer controls on the same pages (chosen). Each page keeps one filter row in view; the other filters sit in a closed More filters control that says how many are on ("More filters (1 on)") and opens by itself when any is on. Pages under three screens lose their jump row. The status fold moves above the provisions and is renamed "Where it stands". Routes and records are unchanged.
2. Merge the News pages: Timeline and Media in one feed, People inside Positions, nine pages down to seven. Rejected for now: the feeds have different shapes, and deep links would need redirects.
3. Open the Overview with reader questions. Rejected: the provisions list already answers them in one tap, so the questions would repeat cited text and break the five-provisions rule.

Measured at 375×812 (`.test-artifacts/clutter-*.txt`, controls visible on the first screen and in total): Overview 17 and 25 to 10 and 18; Data centers 19 and 31 to 11 and 22; Communities 21 and 62 to 17 and 58; Timeline 35 and 42 to 33 and 40 (the rest are chart markers); Media 38 and 49 to 4 and 15. Page heights did not grow. "Will it pass" and the wind and solar question moved from 1.28 screens down to 0.58 (`tools/reader_paths.cjs`); every other reader path kept its tap count and moved by at most 0.07 screens. `tests/uat.cjs` checks that More filters starts closed on Media, counts filters that are on, and stays open after a filter is set.
