# Contract: which bill sections a commentary or report discusses, November 22, 2026

The bill: the Bipartisan American Affordability and Jobs Act of 2026 (BAAJA), S. 5653, carried on H.R. 2347. Text public September 30, 2026; the sponsors' substitute SA 6883 was released November 7 and adopted November 18; the Senate passed H.R. 2347 as amended 62 to 33 on November 19. Section numbers are almost the same in both texts. `sections.txt` lists every section of the passed text (number, tab, heading).

Your work list is one file (`refs-todo-a.json` or `refs-todo-b.json`): commentary, organizations' statements, reports and government releases already on the site. For each item:

1. Fetch the page (`url`). If it refuses scripts, try `https://r.jina.ai/<url>` and say so in `route`. A page you cannot read goes in `not_read` with the reason. Never work from a search snippet or from the `summary` field.
2. Find the provisions of the bill the piece discusses. A provision counts when the piece names its section ("Section 1106") or describes it so specifically that only one section fits (a 150-day lawsuit deadline is 1110; transmission cost allocation and the ratepayer protection language are 2107; ESA Section 7 consultation timelines are 1302; Clean Water Act 401 certification is 1202; the data center community program is 2117). Map each to a number in `sections.txt`. When two sections could fit, read their headings and pick the one the piece describes; if you cannot tell, leave it out. Most pieces discuss 1 to 5 sections. Do not list a section the piece only mentions in passing as part of a list of the bill's titles.
3. For each section, copy a `quote` from the page, character for character: the sentence or clause (8 to 45 words) where the piece talks about that provision. It must be on the fetched page exactly.
4. Read the piece's position on this bill (not on permitting reform in general): `supports`, `opposes`, `mixed` (backs parts and fights parts, or backs it with named conditions), `neutral` (explains without taking a side) or `reporting` (straight news). Copy the sentence that shows it into `stance_quote`. If the item's current `stance` is wrong, say so in `stance_note`.
5. A piece that discusses the bill only as a whole, with no specific provision, goes in `none` with one plain sentence saying why.
6. Write your output file after every item (read it, append, write it back), so nothing is lost if you stop.

Output file (`refs-proposed-a.json` or `-b.json`):
{"refs": [{"id": "...", "url": "...", "route": "direct|jina", "stance": "...", "stance_quote": "verbatim", "stance_note": "only if the current stance is wrong", "sections": [{"n": "1110", "quote": "verbatim from the page"}]}],
 "none": [{"id": "...", "url": "...", "why": "..."}],
 "not_read": [{"id": "...", "url": "...", "why": "..."}]}

Plain UTF-8, no HTML entities. Never invent or paraphrase a quote. Report at the end: counts of refs, none and not_read, and any page whose text did not match the item's title.
