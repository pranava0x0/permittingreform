# Permitting Reform design

A committee reading room: dark green masthead, cream paper, compact rows and numbered provisions. The bill and its citations carry the page. This is an independent tracker, not a Senate website.

## Type and color

Self-hosted Raleway for headings and Open Sans for controls and prose. Statutory text uses the system serif stack. Fonts and their licenses live in `site/fonts/`.

Colors live in `site/styles.css`: cream `--bg`, green `--brand` and `--rule`, blue citation links, yellow search marks and selected-tab underline. Dark mode has matching tokens. Contrast tests check text at 4.5:1 and rules/focus at 3:1.

## Layout

The site title dominates the masthead. Seven plain navigation links use one horizontally scrollable row on phones. BAAJA is the bill label; its full title and source links expand under Bill details. Search appears on Overview and bill views. Main provisions precede status and sponsors.

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
- On phones, each comparison row opens on tap and shows BAAJA beside one version picked with the "BAAJA vs." chips.
- Filter chips sit in one swipeable row on phones.
- Pages with three or more headings get an "On this page" row of jump links.
- The Timeline opens with a swipeable milestone strip, scrolled to the newest milestone.

Measured October 2, 2026 at 375×812, in screen-heights: Compare 43 to 9, data center bills 13 to 2, Timeline 14 to 7, People 20 to 6, bill index 16 to 1, Communities 28 to 4 (one line per change).

## PR 3 reading flow

Overview provisions and secondary sections use native disclosures. Communities and general comparison groups fold by subject. Overview links directly to the data-center table. Long lists start with 12 entries; each load-more adds at most 12 and focuses the first new entry. Filters restart at 12. Milestone jumps reveal events outside the batch. Comparison rows retain their open state when the counterpart changes and stay operable after rotation. Source passages expand within comparison cells.
