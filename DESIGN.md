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

Overview provisions and secondary sections use native disclosures. Communities and general comparison groups fold by subject. Overview links directly to the data-center table. Long lists start with 12 entries; each load-more adds at most 12 and focuses the first new entry. Filters restart at 12. Milestone jumps reveal events outside the batch. Comparison rows retain their open state when the counterpart changes and stay operable after rotation. Source passages expand within comparison cells.

Communities groups stay open with a count in each heading; the rows themselves are one line each. Folding both the groups and the rows hid all 46 changes behind closed headings (2026-10-02).

Measured October 2, 2026 at 768×1024 after the tablet change: Compare 2.3 screens (was 11.9), data center bills 1.8 (was 11.3), bill index 1.0 (was 9.4). `tests/uat.cjs` enforces scroll budgets at 375 and 768.

## Cites and readings (2026-10-05)

Every sentence that says what the bill does ends in a small "p. N" link. It opens the section's text with the cited lines marked; the line gutter there links to the PDF. Outside readings sit under "What others say it would do" on each section page: brief rows (stance, who, their claim) that open to the verbatim quote, the source and the bill passage. The first rows alternate stances so a reader sees the disagreement without opening More. Readings load with the first section page that needs them.

Measured at 375×812, before and after: the next Senate vote moved from 1.1 screens down the Overview to the first screen; Data centers went from a swipe of the tab row plus a tap to one tap; a provision's critiques are two taps from the Overview (open the provision, then "What others say"); the readings block costs 0.73 screens on a section page with three rows shown.


## Positions (2026-10-18)

A fourth News subtab answers "who is for and against" on one page. Three blocks, in the order a reader asks: the letters and joint statements (date, stance, signer count, title; each opens to recipients, the ask, sample signers, the quote and the source), the voices on each issue (For, Against and Mixed under the issue's cited headline, four shown and the rest behind one chip), and a by-sector table whose counts link into the People page with the sector carried in the route. Only statements dated on or after the bill text's release count as voices on an issue; earlier statements were about prior bills or reform in general. The Overview carries one line, "Who's for and against: N support, N oppose", on its first screen; the letters count was left off because the line wraps at 375px with it.

Measured at 375×812: the page is 3.1 screens with every row closed (the budget is 4), the first letter row sits on the first screen, and the first letter's signers are two taps from the Overview (the link, then the row), with the signers at 0.93 screens. No horizontal scroll at 375, 768 or 1280; the sector table is 640px wide at 768. Light and dark both render; the only sub-44px targets are inline text links and the masthead, which are exempt.
