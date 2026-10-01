# Agent runs

One row per agent or model run: what it did, whether it worked, cost, and what to do differently.

| Date | Run | Model | Result | Cost | In hindsight |
|---|---|---|---|---|---|
| 2026-09-30 | Timeline and people research (web) | Sonnet | 50 events, 45 people, every URL fetched. Stalled once at its first batch when the machine slept; resumed from the file it had written and finished. | 756K tokens, 188 tool calls | The incremental-write rule paid for itself: the stall lost nothing. Ask for the stance on the bill and the stance on reform as two fields; one field forced 25 hand edits in `data/curation.json`. |
| 2026-09-30 | Media sweep (web) | Sonnet | 90 items across press, government, groups, X, Bluesky, video. Found the keyless routes for X (oEmbed) and Bluesky (public API). Zero Reddit. | 563K tokens, 179 tool calls | Reddit was refused by every route (script, both browsers, search). Record a walled source after the first refusal and move on. |
| 2026-10-01 | Extra coverage search (main session) | Fable | 3 searches found 10 candidates; 6 were already held, 4 added after fetching each page. | about 15K tokens | Inline search was the right size for a gap check. |
| 2026-10-01 | Summary check, `tools/infer_check.py` | Sonnet via `claude -p` | See `data/checks/inference.json`. Evidence spans became the key-point cites. | 9 calls | One call per 12,000 words. The first plan of 30 calls sent the same long sections 18 times. |
| 2026-10-01 | Code review: Python tools | Sonnet | See `docs/reviews/review-tools.md`. | | |
| 2026-10-01 | Code review: front end | Inline Codex review | See `docs/reviews/review-site.md`; prior Sonnet review had not run. | Not separately metered | Direct code reads and browser tests found the defects. |
| 2026-10-01 | Resume summary check and minimal availability probe | Sonnet CLI | Both calls refused by session limit; no new verdicts. Saved results reconciled without model calls. | Token usage unavailable; no successful response | Preserve the batch cache and finish other checks; no polling loop. |
