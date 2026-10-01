# Front-end review

October 1, 2026. Inline review of app.js, search.js, styles.css, generated data and browser behavior. No subagent used.

## Fixed

- Search joined structured key-point objects as strings, making their text unsearchable. It now reads the text field. A regression test searches a phrase present only in a key point.
- A delayed page-number search could navigate away after the reader selected another tab. Async rendering now checks that its destination remains connected. Browser regression delays bill.js, switches to Media and verifies the selected route survives.
- Method displayed a stale supported-claim total after summaries changed. Input fingerprints now invalidate stale coverage. Saved verdict reconciliation drops changed statements and exposes flagged and unchecked counts.
- Overview overstated travel sanctions, remedy scope, cost recovery and NEPA exclusions. It now states conditions and links to the relevant sections. Existing data-center service arrangements are identified.

## Browser evidence

See ../../uat.md and tests/uat.cjs. Data is inserted as text nodes; external links require HTTP(S). No HTML interpolation of source prose was found.

## Open

Fresh Sonnet summary review is unfinished because the subscription limit blocked calls. The saved review covers only selected fields. Neither link checks nor quote matching establish that every paraphrase is accurate.
