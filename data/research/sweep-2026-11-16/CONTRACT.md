# Contract: newer quotes for people with no clear position (2026-11-16)

Goal: for each person assigned to you, find their most recent public statement on the Senate permitting bill and record it verbatim with its source, or record that none was found.

The bill: the Bipartisan American Affordability and Jobs Act of 2026 (BAAJA), S. 5653, released September 30, 2026 by Sens. Capito, Lee, Whitehouse and Heinrich; the Senate is using H.R. 2347 as the vehicle; the sponsors' substitute amendment SA 6883 was released November 7; the Senate voted 73-25 on November 9 to end debate on taking it up and 62-21 on November 10 to take it up. Also called "the Senate permitting deal" or "the bipartisan permitting bill".

Rules:
1. Prefer statements dated on or after 2026-09-30 about this bill. If the person has none, record their most recent statement on permitting reform generally and mark `about: "permitting reform generally"`.
2. Acceptable sources only: a .gov page (senate.gov, house.gov, whitehouse.gov, agency sites, congress.gov, the Congressional Record), the person's own official social account, or a news article or press release that quotes the person directly in quotation marks.
3. Fetch the page and copy the quote character for character from the fetched text. Never quote from a search-result snippet. If a page refuses scripts, try `https://r.jina.ai/<url>`; say which route you used.
4. Never invent or paraphrase a quote, a date or a URL. If you cannot find one, say so: that is a valid result.
5. Write your output file after every person (append), so nothing is lost if you stop.

Output: a JSON array, one object per person:
{"id": "...", "found": true, "quote": "...", "url": "...", "date": "YYYY-MM-DD", "speaker_context": "where and how they said it", "about": "the bill" | "permitting reform generally", "reading": "supports" | "opposes" | "mixed" | "none", "reading_reason": "one sentence tying the reading to the quote's words", "route": "direct" | "r.jina.ai"}
or {"id": "...", "found": false, "searched": ["query 1", "query 2"]}
