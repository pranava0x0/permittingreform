# Contract: sweep for November 16 (evening) to November 18, 2026

The bill: the Bipartisan American Affordability and Jobs Act of 2026 (BAAJA), S. 5653, released September 30, 2026 by Sens. Capito, Lee, Whitehouse and Heinrich. The Senate is using H.R. 2347 as the vehicle. The sponsors' substitute, SA 6883, was released November 7. Senate votes so far: 73-25 on November 9 (cloture on the motion to proceed), 62-21 on November 10 (motion to proceed), 70-27 on November 16 (cloture on SA 6883, roll call 264). On November 18 at about 11:45 a.m. the Senate is scheduled to vote on a motion to waive a Merkley budget point of order against SA 6883 (if raised), adoption of SA 6883, and cloture on H.R. 2347 as amended.

Window: items dated 2026-11-16 or later that react to the bill, the substitute, the November 16 vote, the amendments filed to SA 6883, or the November 18 votes. Skip anything dated before 2026-11-16.

Rules:
1. Fetch the page and copy every quote and title character for character from the fetched text. Never quote from a search-result snippet. If a page refuses scripts, try `https://r.jina.ai/<url>` and say so in `route`.
2. Skip any URL in `held-urls.txt` (already in the data) and any X status id in `x-held-ids.txt`.
3. Never invent or paraphrase a quote, date, URL or headline. A page you could not read goes in `not_found` with the reason.
4. Write your output file after every item (read it, append, write it back), so nothing is lost if you stop.
5. Vocabulary is in `x-vocab.txt`. `stance` is the item's stance on this bill (use `reporting` for straight news). Sector is the speaker's sector.
6. Plain UTF-8, no HTML entities. Omit keys you have no value for rather than writing empty strings.

Media item shape (see `x-example-item.json`):
{"date": "YYYY-MM-DD", "type": "...", "outlet": "...", "author": "...", "title": "verbatim headline or first sentence of the post", "url": "...", "summary": "one plain sentence on what it says, naming who", "stance": "...", "quote": {"text": "verbatim", "speaker": "who said it"}, "topics": ["..."], "sector": "...", "route": "direct" | "r.jina.ai" | "chrome"}

Output file: `{"items": [...], "not_found": [{"what": "...", "why": "..."}]}`.
