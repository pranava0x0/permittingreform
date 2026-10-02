# Permitting Reform

A static site that indexes the Bipartisan American Affordability and Jobs Act of 2026, the 417-page permitting bill four senators released on September 30, 2026.

- **BAAJA.** All 71 substantive sections: a summary, key points, verbatim quotes, and the full text. Each passage carries its page and line in the printed bill and links to that page of the PDF.
- **Compare.** Current law, the 2024 Senate bill (S. 4753), the House-passed SPEED Act (H.R. 4776) and the 2026 Senate text, subject against subject.
- **Data center bills.** BAAJA sections 2107 and 2114 beside current policy, the Ratepayer Protection Act (H.R. 9340), the GRID Savings Act, the Power for the People Act and the GRID Act, on Compare.
- **Communities.** What BAAJA changes about who can comment, be consulted, take part in planning or go to court: the public, tribes, states, local governments, landowners and consulting parties.
- **Timeline, People, Media.** Events since January 2025, the people and groups involved, and coverage, each with a source link.

## Run it

```bash
python3 tools/build.py
python3 -m http.server 8766 --bind 127.0.0.1 --directory site
```

Open http://127.0.0.1:8766. The site has no backend and loads nothing from another origin.

## Layout

| Path | Holds |
|---|---|
| `site/` | The published site. `site/data/*.js` and `site/llms.txt` are generated; do not edit them. |
| `site/bill.pdf` | The bill as posted by Senate EPW. Page cites link into it. |
| `data/bill/sections.json` | The parsed bill: every printed line with its page and line number. |
| `data/bill/analysis.json` | Summaries, key points, quotes and notes on earlier versions, by section. |
| `data/bill/point_cites.json` | The passage that backs each key point. |
| `data/compare.json`, `data/overview.json` | The comparison tables (including `bills`, the data center bills table) and the overview page. |
| `data/communities.json` | The Communities view: one row per change to comment, consultation, planning or court rights, with a quoted passage the build checks. |
| `data/research/` | What the research agents returned, unedited. |
| `data/curation.json` | Edits to the research, each with a reason. |
| `data/timeline.json`, `people.json`, `media.json` | Research after curation. The build reads these. |
| `data/checks/` | Results of the last link, quote and inference checks. |
| `tools/` | Parser, build, validators. Standard library, plus `pypdf` to re-read the PDF. |
| `tests/` | `unittest` and `node --test` suites. |

## Checks

```bash
make check     # tests, data, bill quotes, prose and design gates; no network
make links     # every link on the site
make quotes    # every quote against its source page
make infer     # a second AI reading of each summary against the bill text
```

| Script | Proves |
|---|---|
| `tools/check_quotes.py` | Each bill quote appears word for word in the section it cites. Each web quote appears on the page it cites. |
| `tools/check_links.py` | Each link answers. Sites that refuse scripts are listed as blocked. |
| `tools/check_data.py` | Each record has its required fields, a known vocabulary value and a source. Each key point cites a passage. |
| `tools/infer_check.py` | A Sonnet model judges whether each summary sentence is supported by the section text. The script confirms the model's evidence is in the text. |

The build refuses a changed PDF, an unverifiable bill quote or a stored key-point passage that no longer matches. The data gate also requires a citation for every key point.

## Update it

When the sponsors post a new text, or to bring the timeline and coverage current, follow [REFRESH.md](REFRESH.md).

## Publish

Push to `main`, then run the `pages` workflow by hand. It deploys `site/` to GitHub Pages.

## Review status, October 2, 2026

Offline gates and browser acceptance checks pass. All 159 key points have matched passages; 158 bill quotations match, including Communities. Web checks found 265 quotations in cached source pages and retain 17 browser-verification records. Saved link results: 331 answered a script; 12 refused scripts; none reported dead.

The fresh Sonnet review remains incomplete: 401 saved supported statements, 12 flagged evidence spans and 127 unchecked statements out of 540 current claims. Edited statements do not inherit old verdicts. The subscription limit prevented a fresh call; `make infer` resumes through its batch cache after access returns. Current-law cells, per-section earlier-version notes, data-center bill cells, Communities and research paraphrases are outside that check's coverage.

Run browser checks with an existing Playwright installation and Google Chrome: `node tests/uat.cjs` while `make serve` runs. It checks all views in both themes at three widths, then exercises search, filters, load-more, source passages, comparison switching, viewport transitions, keyboard navigation and a delayed-load regression.

`node tests/clicks.cjs` loads every view and all 71 sections at 375 and 1280 pixels, then clicks every control on the main views from a fresh load, opening folded parents first. It fails on page errors, sideways overflow, controls that do nothing or are covered, a milestone symbol that opens the wrong event, and any load or click over 20 seconds. Results go to `.test-artifacts/clicks.json`.
