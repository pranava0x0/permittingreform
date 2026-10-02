# PR 1 review, October 2, 2026

Reviewed original head ff8b915. PR 1 merged concurrently at dc18e73; the merger integrated the inline fixes. Agent exports continue in a follow-up branch based on that merge. No subagents used.

## Findings and disposition

- Browser user paths retained the old media count. Fixed on the merged branch; combined topic and position filters now have browser coverage.
- The data center comparison transferred the 20 MW threshold to a separate transmission pricing rule and omitted grandfathering. Fixed on the merged branch. Section 2107(a) covers computational transmission loads; new FPA section 228(b)/(c) covers qualifying new connections, including phased buildout, with prior approved arrangements preserved. Draft pages 226–240.
- Current-law pricing omitted separate-facility pricing. Fixed with the primary FERC policy. Exact locator: 59 FR 55037, footnote 34, PDF page 12. [Policy](https://archives.federalregister.gov/issue_slice/1994/11/3/55026-55045.pdf#page=12).
- Vote claims needed sources beyond the engrossed bill. The merged note now has separate sources. [H.R. 9340](https://www.govinfo.gov/content/pkg/BILLS-119hr9340eh/html/BILLS-119hr9340eh.htm) supports the 100 MW definition, financial assurance and consideration deadlines; [Senate roll call 254](https://www.senate.gov/legislative/LIS/roll_call_votes/vote1192/vote_119_2_00254.htm) supports failed cloture on the motion to proceed, not rejection on final passage.

## Accuracy and discourse

The six original additions match the sources reviewed. Read Siegel's three article screenshots, Barnard's email screenshot and Flegal's thread in the browser; oEmbed alone cannot substantiate screenshot or later-thread claims. Tucker's post and Flegal's cost-rule post match their quoted text. CPE's linked PDF supports the transmission summary; its landing page links the document. [CPE brief](https://publicenterprise.org/wp-content/uploads/Analyzing-the-transmission-provisions-of-BAAJA.pdf), pages 1–4 and 6–7.

The strongest additions distinguish advocacy from statutory effects. Flegal's dollar and emissions figures remain attributed estimates. Her EIA point needs the site's qualification: section 2114 revises Form 861 rather than ordering a direct filing by every data center. Section 1401 relief follows a successful court challenge and includes delay costs plus 25–50 percent of specified project costs; it is not blanket reimbursement. Barnard's repost shows a favorable email, but cannot prove that every White House condition is settled. Section 1401 retains a court-order exception. Draft pages 158–166 and 279.

Transmission is a substantive change: section 2101 removes the national-interest-corridor gate and gives qualifying developers a route to FERC, subject to findings and state triggers. A deadline is not universal automatic approval. Section 2104 allows state referrals over local planning. Section 2105 bars federal rights of first refusal for selected regional/interregional facilities; it does not erase every state preference. Draft pages 185–200 and 218–224. The new load floor is binding rather than H.R. 9340's consideration requirement; both eligibility and effective-date triggers matter.

Political reading is conditional. Siegel reports likely utility resistance and House uncertainty, not a settled utility-industry position. Clean-energy supporters value transmission and permit certainty. Environmental groups divide over NEPA remedies, CWA/ESA changes and the unresolved wind/solar side agreement. NRDC and LCV reservations differ from CBD opposition. TPA's concerns distinguish faster project review from burdens on data centers. The media collection is a curated archive, not a poll or a vote forecast. Repeated posts from one person do not add independent coalition members.

## Usefulness and remaining gaps

Topic + position filtering helps readers see cross-cutting disagreements. Source corrections are useful because they identify the operative section and preserve exceptions. Keep modeled savings distinct from enacted obligations and keep the wind/solar side agreement outside the statutory comparison until there is text.

Agent access now includes a compact source-linked llms.txt, per-section Markdown with full statutory paragraphs and page-line cites, a full text/analysis export, plain JSON matching browser data, and a static HTML index linked in a sitemap. Hash routes remain useful browser links but are not independent HTTP documents. Text exports carry the draft version and stale/partial check coverage. Hyphenated data-center searches now match ordinary bill language.

Verification: 73 Python tests, Node search tests, offline data/bill-quote/prose/design gates; 48 browser route states at three widths in both themes; no-JavaScript section index at mobile and desktop; export parity for all 71 sections. Current quote run: 112 bill quotes matched; 137 web quotes matched cached/read source text and three use prior browser records. Current link run: 254 answered, three blocked with prior browser records, zero dead/errors. Those three browser records were not independently reopened here. Saved semantic review remains stale: 401 supported, 12 flagged and 127 unchecked out of 540; current-law comparison cells and some research paraphrases are outside that check. No fresh model sweep was run.
