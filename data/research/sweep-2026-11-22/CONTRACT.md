# Contract: deep sweep, November 20 to 22, 2026, with claims about what the bill does

The bill: the Bipartisan American Affordability and Jobs Act of 2026 (BAAJA), S. 5653 (Capito, Lee, Whitehouse, Heinrich), carried on H.R. 2347. The Senate adopted the sponsors' substitute SA 6883 on November 18 and passed H.R. 2347 as amended 62 to 33 on November 19 (roll call 270). Merkley objected to votes on the managers' amendment (SA 7022, refiled as SA 7030) and on 19 other amendments, so neither came up. The House returns November 30 and must act on the Senate amendment.

Window: commentary and reports only (op-eds, analyses, explainers, law-firm alerts, think-tank reports, CRS or CBO products, organizations' statements and letters) dated 2026-11-07 or later that are not already held. No X posts and no straight news this time. Each item also carries `sections`: [{"n": "1110", "quote": "verbatim from the page where it discusses that provision"}] for every specific provision it discusses, using numbers from `sections.txt` (see REFS-CONTRACT.md step 2 for how to map). Stance is the piece's position on this bill: supports, opposes, mixed, neutral.

What we want most: items that make a CLAIM about what the bill (as passed) would do or not do — e.g. "it guts the Endangered Species Act", "it lets data centers skip NEPA", "it caps lawsuits at 150 days", "it protects tribal consultation", "it raises ratepayer costs". For each such claim copy the exact sentence from the fetched page into `claims` (see shape). Do not judge whether a claim is true. Also keep straight news and statements of position, as before.

Rules:
1. Fetch the page and copy every quote, claim and title character for character from the fetched text. Never quote from a search-result snippet. If a page refuses scripts, try `https://r.jina.ai/<url>` and say so in `route`.
2. Skip any URL in `held-urls.txt` (already in the data) and any X status id in `x-held-ids.txt`.
3. Never invent or paraphrase a quote, claim, date, URL or headline. A page you could not read goes in `not_found` with the reason.
4. Write your output file after every item (read it, append, write it back), so nothing is lost if you stop.
5. Vocabulary is in `x-vocab.txt`. `stance` is the item's stance on this bill (use `reporting` for straight news). Sector is the speaker's sector.
6. Plain UTF-8, no HTML entities. Omit keys you have no value for rather than writing empty strings.
7. Dates: X post dates come from the status id in America/New_York: ms = (id >> 22) + 1288834974657.

Media item shape (see `x-example-item.json`):
{"date": "YYYY-MM-DD", "type": "...", "outlet": "...", "author": "...", "title": "verbatim headline or first sentence of the post", "url": "...", "summary": "one plain sentence on what it says, naming who", "stance": "...", "quote": {"text": "verbatim", "speaker": "who said it"}, "topics": ["..."], "sector": "...", "route": "direct" | "r.jina.ai" | "chrome",
 "claims": [{"text": "verbatim sentence or clause from the page asserting what the bill does", "speaker": "who asserts it", "about": "3-6 word topic, e.g. 'ESA consultation deadlines'", "sections_hint": ["1106"] }]}
`sections_hint` is optional: give it only if the page itself names a section or provision; never guess.

Output file: `{"items": [...], "not_found": [{"what": "...", "why": "..."}]}`.
