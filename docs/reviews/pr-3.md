# PR 3 review and acceptance spec

Reviewed head: `120b3902f62b955fb0695e835771a2c463e61376`. Inline review; no subagents.

## Trigger and success criteria

A phone reader needs data-center rules without scrolling through the whole tracker. Keep all records and citations, fold overview provisions and secondary sections, fold Communities and general comparison groups, and show long lists in batches of 12. Each load-more action adds 12, filters start at 12, and milestone jumps reveal their event even outside the initial batch. Desktop uses the same controls. Comparison rows stay open when the counterpart changes and remain operable across 640px. Preserve keyboard focus after rerenders.

Separate section 2107(a) transmission pricing from section 228(b)/(c) prospective protection and section 2114 reporting. Existing-arrangement language must not imply a blanket exemption from all three. Every changed claim keeps a bill or primary-source citation. Quote artifacts must reflect all 158 bill quotations.

## Claude transcript audit

Read all parent JSONL records from session `689a36a5-9bc7-45e7-84be-509e9fd3d08e`, extracting user and assistant prose; inspected tool calls and research handoffs. No raw background-agent transcripts were loaded. Also checked the originating session's user brief. Private transcript contents stay out of shipped assets.

Delivered: 13 data-center comparison dimensions; other federal bills; Heatmap/POLITICO additions; Communities; citations and incomplete-review notices. Free Pro previews were distinguished from full articles; two unsupported podcast records were removed. These are useful additions.

Missed: the browser suite never ran, comparison resizing breaks controls, comparator changes erase open rows, persisted totals exclude Communities, long lists still require many screens. Section 228 grandfathering was generalized beyond its text. Form 861 scope and deadline were underspecified. General comparison content precedes the specialized table; add a direct Overview link.

Research scope grew to Communities beyond the explicit data-center request. Three logged research runs cost about 1.07M tokens (296K + 443K + 334K); the last two greatly exceeded the project's 40K useful-result guideline. Quote occurrence checks do not establish every paraphrase or negative claim. The prior 12 flagged and 127 unchecked inference statements remain unresolved; this review does not relabel them.

## Evidence

BAAJA: stored section 2107(a), proposed FPA 228(f)(1)-(2), and section 2114(b). H.R. 9340 House-passed text was opened live: its 100 MW threshold remains, scoped to data-center facilities. S. 3852 was opened live: section 4(a)(2) excepts existing facilities during a 10-year certificate transition. Other bill quotations were rechecked against cached source text; this is not a fresh legal audit of all paraphrases. One attempted FERC news URL did not resolve; no fresh validation of the June orders is claimed.

## Baseline at 375 × 812

Overview 8,076px; Compare 7,372px; Communities 3,505px; Timeline 8,806px; People 7,843px; Media 6,145px. Browser reproduced zero row toggles and zero visible comparison cells after desktop-to-phone resize. Existing UAT failed the first-provision positioning assertion.

## Coverage limits and excluded work

No new article sweep, dependency install, second-model inference calls or PR merge. Existing preview-only and blocked-source records were retained with their limits. The 10 section-context suggestions in the Heatmap handoff were checked as candidates; they were not blindly added to statutory summaries. This pass adds navigation to 2102 and 2108, displays source passages already verified by the quote gate, and keeps legal paraphrase coverage explicitly incomplete on Method.

## Final validation

`make check`: 74 Python tests and 13 Node tests pass; data, bill quotes, prose and design gates pass. Full quote check: 158/158 bill passages; 265 web quotes matched by script and 17 retained browser records; no missing, near or unreachable quotes. No inference verdict was changed.

Browser: 60 rendered states at 375×812, 768×800 and 1280×800, in light and dark. No page errors or document overflow. Search-to-PDF passage, delayed bill-load navigation, every list batch, empty filters, Communities filters and source links, comparison counterpart changes, keyboard expansion, desktop/phone transitions and folded-parent preservation pass. Initial phone scroll budgets are enforced in UAT. Two data-center screenshots were inspected.

| Initial phone view | Before px | After px | After screens |
|---|---:|---:|---:|
| Overview | 8,076 | 1,301 | 1.6 |
| Compare | 7,372 | 2,521 | 3.1 |
| Communities | 3,505 | 844 | 1.0 |
| Timeline | 8,806 | 1,769 | 2.2 |
| People | 7,843 | 2,945 | 3.6 |
| Media | 6,145 | 3,394 | 4.2 |

Measurements describe initial views; expanding or loading more grows them. Full statutory text remains available in the bill view. All 179 media items are reachable through the batches. General Compare keeps all 58 substantive rows in the DOM; folded groups and mobile counterpart selection control visibility.

Review dimensions: security: text-only DOM construction and existing safe-URL checks retained; performance: smaller initial lists, no added dependencies; correctness: scope, counts and breakpoint defects fixed; maintainability: shared disclosures and executable browser gates. Residual risk: broad legal paraphrases and earlier inference flags remain only partially reviewed.
