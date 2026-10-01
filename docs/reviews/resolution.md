# Review resolution

October 1, 2026. The saved Python review was recovered before edits.

| Finding | Resolution |
|---|---|
| F1: clauses merged after wrapped conjunctions | Test the accumulated paragraph; recognize inserted section headings. Separate statutory paragraphs now render independently. |
| F2: enumeration indentation | Accept longer Roman numerals, continue doubled-capital lists, clear ambiguous letter state at sub-list openers. |
| F3: truncated quotes accepted | Reject partial words and partial numbers. Reject ambiguous bill quotations during build. |
| F4: citation begins on wrong line | Keep body text following a split run-in heading on its printed line. Document the split-word end convention on Method. |
| F5: extraction artifacts | Join en-dash number splits and quoted small caps; repair spaces inside capitalized hyphenated terms. |
| F6: PDF and index could diverge | Bind raw extraction and parsed metadata to the PDF SHA-256; reject a replaced PDF during build. Fresh official download matched the local hash. |

Additional review hardened web quotes: elided passages must appear in order, with complete word and number boundaries. Removing all spaces no longer turns a near match into a verified quote. Near and inaccessible quotes fail the check.

All 159 key points now have passages found in their section. 141 were recovered from unchanged, supported saved claims; 18 were resolved against the source text. This is citation coverage, not a completed second semantic review.

Positive inference verdicts also require a complete evidence span. Empty evidence is accepted only for explicit comparison claims of no change or non-coverage; a claim that two bills are identical cannot pass without evidence.
