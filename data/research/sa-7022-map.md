# SA 7022 map: what the managers' amendment changes in the SA 6883 substitute

Source of SA 7022 text: Congressional Record, Nov. 17, 2026, vol. 172, no. 174, pp. S5725-S5726 (govinfo CREC-2026-11-17-pt1-PgS5725-4.htm; the -3 file prints the same SA 7022 text followed by SA 7023). Page:line references below are to the SA 6883 print in `data/bill/substitute_raw.txt` (KAT26764, 494 pages, with line numbers in the PDF text layer). Old-bill references are to `data/bill/bill_raw.txt` (KAT26642, Sept. 30 draft, 417 pages). Sections and headings come from `substitute_sections.json`; SA 6883 vs Sept. 30 status comes from `substitute_diff.json`.

## 1. Form

SA 7022 is a list of edit instructions, not full text. The Record prints 14 instructions (all listed in section 2): 8 single-word or single-reference edits, 1 insert between two lines, and 5 strike-and-insert blocks, three of which carry several paragraphs of new text. It was submitted by Mr. Lee (for himself, Mr. Heinrich, Mrs. Capito, and Mr. Whitehouse) as an amendment intended to be proposed to SA 6883, ordered to lie on the table. Six instructions are technical (typo or cross-reference). Eight add or rewrite text.

Placement caveat that affects three instructions: instructions 1 to 11 match the SA 6883 print in the repo at the cited page and line (the quoted words are on the cited lines). Instructions 12, 13 and 14 cite pages 459, 461 and 491. In the repo's print the same text sits three pages earlier (456, 458, 488) and, for 12 and 13, at slightly different line numbers. Where that happens the table gives the page:line in our print that the quoted words match, and marks the placement "by text". Nothing in this file is guessed beyond that.

## 2. Instructions

Key: T = technical (typo or cross-reference). S = substantive. "Cited" is the page:line in the Record; where the quoted words sit elsewhere in `substitute_raw.txt`, the actual page:line is given in parentheses.

| # | Cited (SA 6883 page:line) | Section | Instruction (Record text) | What it does | T/S |
|---|---|---|---|---|---|
| 1 | 73:9 | 1110 Judicial review | On page 73, line 9, strike ``9(b)'' and insert ``19(b)''. | Fixes the Natural Gas Act cross-reference in the new "Except as provided in section 9(b) of the Natural Gas Act (15 U.S.C. 717r(b))" clause so it reads 19(b). The U.S.C. cite 717r(b) is the section 19(b) citation. | T |
| 2 | 120:12-13 | 1202 Clean Water Act permitting and State certification | On page 120, lines 12 and 13, strike ``subclause'' and insert ``clause''. | In the petition-to-court consideration text, "a petition under this sub-/clause" becomes "this clause" (the word is split across lines 12-13). | T |
| 3 | 120:20 | 1202 Clean Water Act permitting and State certification | On page 120, line 20, insert ``the'' before ``certifying''. | "identified by certifying authority" becomes "identified by the certifying authority". | T |
| 4 | 160:14 | 1304 State assumption of consultation responsibilities | On page 160, line 14, strike ``(B)(i)'' and insert ``(B)''. | The cross-reference "the notification and period provided under subparagraph (B)(i)" becomes "(B)". The notification and the 120-day period sit in (B)(i) and (B)(ii), so the pointer now covers both. | T |
| 5 | 170:1 | 1401 Maintaining Federal authorizations or permits for projects with non-Federal sponsors | On page 170, line 1, insert ``and final'' after ``necessary''. | Definition of "covered project or action": a project that has secured "all necessary and final Federal authorizations or permits". Narrows the protected set to projects whose authorizations are final. | S |
| 6 | 182:22 | 1402 Ensuring fairness for specific types of covered projects | On page 182, line 22, strike ``(d)'' and insert ``(c)''. | "described in subsection (d)(1)(A)(ii)" becomes "(c)(1)(A)(ii)". In SA 6883 this section has subsections (a) to (c) only; judicial review is (c), and the timeline text that the old (c) held now sits in section 1403(b). | T |
| 7 | 202:15 | 1403 Avoiding unreasonable delays in permitting | On page 202, line 15, strike ``(b)'' and insert ``(c)''. | The 120-day expedited-decision clause says the petition "is filed under subsection (b)". SA 6883 made (b) the timeline and (c) the right to petition, so the pointer moves to (c). | T |
| 8 | 202, between 19 and 20 | 1403 Avoiding unreasonable delays in permitting | On page 202, between lines 19 and 20, insert the following: (h) Requirement to Make Federal Authorizations or Permits Public.--Any action that is a Federal authorization or permit shall be made public (as defined in section 3 of the National Environmental Policy Act of 1969) unless otherwise provided for by applicable law. | Adds a new subsection (h) at the end of section 1403 requiring Federal authorizations and permits to be made public, unless other law provides otherwise. | S |
| 9 | 237:17 through 238:2 | 2101 Transmission permitting | Beginning on page 237, strike line 17 and all that follows through page 238, line 2, and insert the following: ``(5) Landowner input.-- ``(A) In general.--The term `landowner input' means input received-- ``(i) by the Commission; ``(ii) from affected landowners, … ``(iii) pursuant to notification … ``(B) Notification.--For purposes of subparagraph (A)(iii), the term `notification' means a written notice that includes-- … ``(ii) information on-- ``(I) the general process of Commission proceedings; and ``(II) the rights that affected landowners retain in Commission proceedings. | Restructures the FPA section 216(a)(5) "landowner input" definition into (A)(i)-(iii) and adds (B), defining the required notice (description of facilities with a map or map reference; information on the Commission process and landowner rights). | S |
| 10 | 242:2 | 2101 Transmission permitting | On page 242, strike line 2 and insert the following: the siting of the applicable facility. ``(6) Land restoration.-- … ``(7) Standard of conduct for communicating with affected landowners.-- … | Adds two paragraphs after the pre-filing paragraph (5) of new FPA section 216(d): (6) Commission may attach land-restoration conditions to a permit and must require corrective action at the permit holder's cost, with a savings clause; (7) applicant must adopt a landowner-communications standard (contact log, accurate communications, no coercion, public meetings in each county). | S |
| 11 | 284:6-12 | 2107 Ratepayer protection | On page 284, strike lines 6 through 12 and insert the following: (ii) Exclusion.--The term ``computational load site'' does not include-- (I) computing or data storage equipment that is ancillary … (II) a facility or any equipment that is primarily used to provide-- (aa) Internet access … or (bb) cable service … or telecommunications service, … | Keeps the existing exclusion for ancillary computing equipment (as new subclause (I)) and adds subclause (II): facilities or equipment primarily used to provide Internet access, cable service, telecommunications, information, VoIP or other wire communications are not a "computational load site". | S |
| 12 | 459:13-19 (our print: 456:9-15, by text) | 2301 Historic preservation | On page 459, strike lines 13 through 19 and insert the following: other form of financial assistance with respect to which a Federal agency does not exercise predominant control and responsibility over the subsequent use of such financial assistance or any adverse effect of the project, activity, or program on a historic property; | Rewrites the "undertaking" exclusion for federally assisted projects (clause (ii) of the new "undertaking" definition). The exclusion now turns on whether the agency exercises "predominant control and responsibility" over use of the assistance or any adverse effect on a historic property, replacing "not for the primary purpose of historic preservation, subject to the condition that this clause shall not apply to a project that receives more than $10,000,000 … from the Department of Transportation". | S |
| 13 | 461:17 (our print: 458:13-14, by text) | 2301 Historic preservation | On page 461, strike line 17 and insert the following: section. ``(C) Rule of construction with respect to federal financial assistance.-- ``(i) Transportation projects.-- … more than $10,000,000 … ``(ii) Other federally assisted projects.-- … | Adds subparagraph (C) after the "undertaking" exclusion list: the Department of Transportation is treated as having predominant control over assistance above $10,000,000, and clause (i) does not stop other agencies from being found to have predominant control at any dollar amount. | S |
| 14 | 491:21 (our print: 488:21, by text) | 2302 Funding for the Historic Preservation Fund; grants for Tribal Historic Preservation officers; additional funding | On page 491, line 21, strike ``$200,000,000'' and insert ``$300,000,000''. | Raises the Historic Preservation Fund authorization in new 54 U.S.C. 303102 from $200,000,000 to $300,000,000 (the SA 6883 sentence reads "For each of fiscal years 2027 through 2036, there is authorized to be appropriated … $200,000,000 for deposit in the Historic Preservation Fund."). | S |

Record text for the long instructions is quoted in full in section 4. Short instructions above are verbatim; "…" marks shortening.

## 3. Sections SA 7022 changes, and SA 6883's prior changes

Status is the `status` field in `substitute_diff.json` (SA 6883 vs the Sept. 30 bill). All ten sections SA 7022 touches were already "edited" by SA 6883. The last column asks the narrower question: did SA 6883 change the words at the exact spot SA 7022 edits?

| Section | Heading | SA 6883 vs Sept. 30 | SA 7022 instructions (#) | SA 6883 changed the exact passage? |
|---|---|---|---|---|
| 1110 | Judicial review | edited (3 hunks) | 1 (T) | Yes. The "Except as provided in section 9(b) of the Natural Gas Act" clause is new in SA 6883. |
| 1202 | Clean Water Act permitting and State certification | edited (11 hunks) | 2, 3 (T) | No. The two lines read the same as the Sept. 30 text (old 112:14-24). |
| 1304 | State assumption of consultation responsibilities | edited (4 hunks) | 4 (T) | No. Same words as old 152:17-18. |
| 1401 | Maintaining Federal authorizations or permits for projects with non-Federal sponsors | edited (61 hunks) | 5 (S) | Yes. The "covered project or action" definition is new in SA 6883. |
| 1402 | Ensuring fairness for specific types of covered projects | edited | 6 (T) | Words unchanged (old 167:25 has the same "(d)(1)(A)(ii)"), but SA 6883 reorganised the section, which is what made the pointer stale. |
| 1403 | Avoiding unreasonable delays in permitting | edited | 7 (T), 8 (S) | #7: words unchanged (old 184:25), pointer made stale by SA 6883's new (b). #8: insert follows subsection (g), which SA 6883 re-lettered from old (f). |
| 2101 | Transmission permitting | edited | 9 (S), 10 (S) | #9: No (definition text is word for word the Sept. 30 text). #10: Yes in effect. SA 6883 deleted old paragraphs (6) and (7) at exactly this spot. |
| 2107 | Ratepayer protection | edited | 11 (S) | Yes. The "(ii) Exclusion" text is new in SA 6883 (Sept. 30 had none). |
| 2301 | Historic preservation | edited | 12 (S), 13 (S) | #12: Yes. SA 6883 added the Transportation $10,000,000 condition to this clause. #13: No change by SA 6883 at the end of the exclusion list; the new (C) is placed after it. |
| 2302 | Funding for the Historic Preservation Fund; grants for Tribal Historic Preservation officers; additional funding | edited | 14 (S) | Yes, reworded. SA 6883 moved the fiscal-year language to the front of the sentence; the $200,000,000 figure itself is unchanged from Sept. 30. |

Totals: 14 instructions, 10 sections, 10 of 10 sections already edited by SA 6883. Substantive instructions fall in 6 sections (1401, 1403, 2101, 2107, 2301, 2302), all of which SA 6883 had edited. Of the 8 substantive instructions, 6 sit on a passage SA 6883 itself rewrote or deleted (#5, #8 by adjacency, #10, #11, #12, #14) and 2 sit on text SA 6883 left alone (#9, #13).

Section 3001 (Division C, new in SA 6883): no SA 7022 instruction lands in it by text. Instruction 14's cited page 491 line 21 falls inside section 3001 in our print, but the quoted figure "$200,000,000" is not in 3001 (see unresolved list).

## 4. Three readings of each substantive passage in an already-changed section

For each: Sept. 30 bill (S. 5653, `bill_raw.txt`), SA 6883 (`substitute_raw.txt`), then the SA 7022 edit as printed in the Record. Lines are verbatim from the text layer with the printed line number kept at the left (hyphenation at line ends is as printed).

### 4.1 Section 1401, definition of "covered project or action" (instruction 5)

Sept. 30 bill (old 158:22-159:8). No such definition; only the Federal authorization or permit definition:

> 158:22 (a) D EFINITION OF FEDERAL AUTHORIZATION OR
> 158:23 PERMIT.—The term ‘‘Federal authorization or permit’’
> 158:24 means an authorization, permit, record of decision, right-
> 158:25 of-way, finding of no significant impact, verification, ex -
> 159:1 tension, construction and operations plan, biological opin -
> 159:2 ion, incidental take statement, concurrence, or any other
> 159:3 approval or order that is necessary, including any deter -
> 159:4 mination by a Federal department or agency that addi -
> 159:5 tional authorizations or permits are not necessary, for the
> 159:6 construction or operation at full capacity of a project.
> 159:7 (b) M AINTENANCE OF AUTHORIZATIONS AND PER-
> 159:8 MITS.—


SA 6883 (169:21-170:3):

> 169:21 (a) DEFINITIONS.—In this section:
> 169:22 (1) C OVERED PROJECT OR ACTION .—The term
> 169:23 ‘‘covered project or action’’ means a project or ac -
> 169:24 tion with a non-Federal project sponsor that has se -
> 170:1 cured all necessary Federal authorizations or per -
> 170:2 mits for construction or operation.
> 170:3 (2) F EDERAL AUTHORIZATION OR PERMIT .—


SA 7022 (cited 170:1):

> On page 170, line 1, insert ``and final'' after
> ``necessary''.


Result: "…has secured all necessary and final Federal authorizations or permits for construction or operation." The Sept. 30 bill had no separate definition; its operative paragraph (old 159:17-19) said "a project that has secured all necessary Federal authorizations and permits". SA 6883 keeps that wording in the maintenance paragraph (170:17-171:2: "a project that has secured all necessary Federal authorizations and permits"). SA 7022 edits only the definition at 170:1, so the two phrases would differ ("necessary and final" in the definition, "necessary" in 1401(b)(1)).

### 4.2 Section 1403, new subsection (h) (instruction 8)

Sept. 30 bill (old 184:18-185:5). The section ended at subsection (f), "ORDER":

> 184:22 (2) issue a decision under this section as expe -
> 184:23 ditiously as practicable, but not later than 120 days,
> 184:24 after the date on which the petition is filed under
> 184:25 subsection (b), absent extraordinary circumstances.
> 185:1 (f) ORDER.—A court awarding injunctive relief under
> 185:2 subsection (d)(1) shall issue an order requiring a decision
> 185:3 on the covered application not later than 60 days after
> 185:4 the date on which the order is issued.


SA 6883 (202:15-202:20). Subsections re-lettered (e) to (f) and (f) to (g); section ends at (g):

> 202:8 (f) E XPEDITED PROCEDURES; T IME TO DECIDE.—
> 202:9 A reviewing court shall—
> 202:10 (1) establish an expedited schedule for briefing
> 202:11 and disposition under this section; and
> 202:12 (2) issue a decision under this section as expe -
> 202:13 ditiously as practicable, but not later than 120 days,
> 202:14 after the date on which the petition is filed under
> 202:15 subsection (b), absent extraordinary circumstances.
> 202:16 (g) O RDER.—A court awarding injunctive relief
> 202:17 under subsection (e)(1) shall issue an order requiring a
> 202:18 decision on the covered application not later than 60 days
> 202:19 after the date on which the order is issued.


SA 7022 (cited between 202:19 and 202:20):

> On page 202, between lines 19 and 20, insert the following:
> (h) Requirement to Make Federal Authorizations or Permits
> Public.--Any action that is a Federal authorization or permit
> shall be made public (as defined in section 3 of the National
> Environmental Policy Act of 1969) unless otherwise provided
> for by applicable law.


### 4.3 Section 2101, landowner input definition (instruction 9)

Sept. 30 bill (old 187:16-188:3):

> 187:16 section 225(a).
> 187:17 ‘‘(5) L ANDOWNER INPUT .—The term ‘land -
> 187:18 owner input’ means input received—
> 187:19 ‘‘(A) by the Commission;
> 187:20 ‘‘(B) from affected landowners, such as
> 187:21 farmers and ranchers, in the path of the pro -
> 187:22 posed construction or modification of an electric
> 187:23 transmission facility; and
> 187:24 ‘‘(C) pursuant to notification provided to,
> 187:25 and consultation with, those affected land -
> 188:1 owners, farmers, and ranchers by the Commis -
> 188:2 sion.
> 188:3 ‘‘(6) S ECRETARY.—The term ‘Secretary’ means


SA 6883 (237:16-238:3). Word for word the same as Sept. 30:

> 237:16 section 225(a).
> 237:17 ‘‘(5) L ANDOWNER INPUT .—The term ‘land -
> 237:18 owner input’ means input received—
> 237:19 ‘‘(A) by the Commission;
> 237:20 ‘‘(B) from affected landowners, such as
> 237:21 farmers and ranchers, in the path of the pro -
> 237:22 posed construction or modification of an electric
> 237:23 transmission facility; and
> 237:24 ‘‘(C) pursuant to notification provided to,
> 237:25 and consultation with, those affected land -
> 238:1 owners, farmers, and ranchers by the Commis -
> 238:2 sion.
> 238:3 ‘‘(6) SECRETARY.—The term ‘Secretary’ means


SA 7022 (cited 237:17 through 238:2):

> Beginning on page 237, strike line 17 and all that follows
> through page 238, line 2, and insert the following:
> ``(5) Landowner input.--
> ``(A) In general.--The term `landowner input' means input
> received--
> ``(i) by the Commission;
> ``(ii) from affected landowners, such as farmers and
> ranchers, in the path of the proposed construction or
> modification of an electric transmission facility; and
> ``(iii) pursuant to notification provided to, and
> consultation with, those affected landowners, farmers, and
> ranchers by the Commission.
> ``(B) Notification.--For purposes of subparagraph (A)(iii),
> the term `notification' means a written notice that
> includes--
> ``(i) a general description of the proposed facilities,
> including the purpose and general location of the facilities,
> accompanied by a map or a reference to an easily accessible
> map; and
> ``(ii) information on--
> ``(I) the general process of Commission proceedings; and
> ``(II) the rights that affected landowners retain in
> Commission proceedings.


### 4.4 Section 2101, end of paragraph (5) of new FPA section 216(d) (instruction 10)

Sept. 30 bill (old 191:10-192:9). Paragraphs (6) Simultaneous processing and (7) Limitations follow:

> 191:10 ‘‘(5) P RE-FILING PROCESSES .—Any Commis -
> 191:11 sion-related pre-filing processes relating to an appli -
> 191:12 cation submitted under subsection (c) may com -
> 191:13 mence before, but shall commence no later than, an
> 191:14 application is submitted to the applicable State com -
> 191:15 mission or other entity that has authority to approve
> 191:16 the siting of the applicable facility.
> 191:17 ‘‘(6) S IMULTANEOUS PROCESSING .—In the case
> 191:18 of transmission facilities that are capable of trans -
> 191:19 mitting electric energy at a voltage of not less than
> 191:20 345 kilovolts, an application under subsection (c)
> 191:21 shall be submitted to the Commission simultaneously
> 191:22 with, or any time after, the submission of an appli -
> 191:23 cation to the applicable State commission or other
> 191:24 entity that has authority to approve the siting of the
> 192:1 applicable facility, and the Commission shall com -
> 192:2 mence a proceeding under subsection (b).
> 192:3 ‘‘(7) L IMITATIONS.—Simultaneous processing
> 192:4 under paragraph (6) is subject to the condition that
> 192:5 the Commission shall not issue a permit under sub -
> 192:6 section (b) unless the Commission first makes a
> 192:7 finding described in subparagraph (A), (B), or (C)
> 192:8 of subsection (b)(1) with respect to the applicable
> 192:9 electric transmission facility.’’.


SA 6883 (241:21-242:2). Paragraphs (6) and (7) are gone; paragraph (5) closes the subsection:

> 241:21 ‘‘(5) P RE-FILING PROCESSES .—Any Commis -
> 241:22 sion-related pre-filing processes relating to an appli -
> 241:23 cation submitted under subsection (c) may com -
> 241:24 mence before, but shall commence no later than, an
> 241:25 application is submitted to the applicable State com -
> 242:1 mission or other entity that has authority to approve
> 242:2 the siting of the applicable facility.’’.


SA 7022 (cited 242:2). The first line of the insert re-prints the last line of (5), then new (6) and (7) follow:

> On page 242, strike line 2 and insert the following:
> the siting of the applicable facility.
> ``(6) Land restoration.--
> ``(A) In general.--The Commission shall have the power to
> attach to the issuance of a permit under subsection (b) such
> reasonable terms and conditions as the Commission may find
> necessary to appropriately restore the applicable land
> following construction.
> ``(B) Corrective action.--If the holder of a permit issued
> under subsection (b) fails to comply with any requirement or
> condition imposed by the Commission that is related to the
> preservation or restoration of, or mitigation of impacts to,
> affected property, the Commission shall require corrective
> action, including through an order requiring corrective
> action, the costs of which shall be borne by the permit
> holder.
> ``(C) Savings provision.--Nothing in this paragraph
> precludes measures or requirements that differ from those
> prescribed in this paragraph to protect or restore affected
> property or to mitigate impacts on such property.
> ``(7) Standard of conduct for communicating with affected
> landowners.--
> ``(A) In general.--An applicant for a permit under
> subsection (b) shall adopt and implement a standard of
> conduct for communicating with affected landowners,
> including, at a minimum, requirements--
> ``(i) to maintain a log accounting for each instance of
> applicant communications with each affected landowner;
> ``(ii) to ensure that all communications with each affected
> landowner are transparent and accurate to the maximum extent
> possible;
> ``(iii) to refrain from any coercive or threatening
> communications with an affected landowner; and
> ``(iv) to hold, in each county in which the proposed
> facilities would be located, a reasonable number of public
> meetings accessible to affected landowners.
> ``(B) Preservation of other protections.--The requirements
> of subparagraph (A) shall not be construed to limit or
> supersede any additional or more stringent requirement
> established by the Commission.''.


### 4.5 Section 2107, computational load site exclusion (instruction 11)

Sept. 30 bill (old 229:1-229:6). The definition ends at the bulk-power-system clause and goes straight to "(F) Public utility"; there is no exclusion:

> 229:1 (ii) are supplied through electrical
> 229:2 equipment that is connected to the bulk-
> 229:3 power system (as defined in section 215(a)
> 229:4 of the Federal Power Act (16 U.S.C.
> 229:5 824o(a))).
> 229:6 (F) P UBLIC UTILITY .—The term ‘‘public


SA 6883 (284:1-284:13):

> 284:1 (II) are supplied through elec -
> 284:2 trical equipment that is connected to
> 284:3 the bulk-power system (as defined in
> 284:4 section 215(a) of the Federal Power
> 284:5 Act (16 U.S.C. 824o(a))).
> 284:6 (ii) E XCLUSION.—The term ‘‘com -
> 284:7 putational load site’’ does not include com -
> 284:8 puting or data storage equipment that is
> 284:9 ancillary to a facility the primary purpose
> 284:10 of which is a commercial or industrial ac -
> 284:11 tivity other than an activity described in
> 284:12 subparagraph (A).
> 284:13 (F) ELIGIBLE COMPUTATIONAL LOAD CUS -


SA 7022 (cited 284:6-12):

> On page 284, strike lines 6 through 12 and insert the
> following:
> (ii) Exclusion.--The term ``computational load site'' does
> not include--
> (I) computing or data storage equipment that is ancillary
> to a facility the primary purpose of which is a commercial or
> industrial activity other than an activity described in
> clause (i); or
> (II) a facility or any equipment that is primarily used to
> provide--
> (aa) Internet access (as defined in section 1105(a) of the
> Internet Tax Freedom Act (47 U.S.C. 151 note; Public Law 105-
> 277)); or
> (bb) cable service (as defined in section 602 of the
> Communications Act of 1934 (47 U.S.C. 522)) or
> telecommunications service, information service,
> interconnected VoIP service, non-interconnected VoIP service,
> or other wire communications (as those terms are defined in
> section 3 of that Act (47 U.S.C. 153)).


Other "ancillary" exclusions elsewhere in section 2107 (the later FPA "data center" and "computational load site" definitions) are not named by any SA 7022 instruction.

### 4.6 Section 2301, "undertaking" exclusion for federal financial assistance (instructions 12 and 13)

Sept. 30 bill, clause (ii) (old 383:22-384:3):

> 383:22 ‘‘(ii) a project, activity, or program
> 383:23 for which the only Federal involvement is
> 383:24 a loan, loan guarantee, grant (including a
> 383:25 capitalization grant), cost-share award, or
> 384:1 other form of financial assistance that is
> 384:2 not for the primary purpose of historic
> 384:3 preservation;


SA 6883, clause (ii) (456:5-456:15). SA 6883 added the Department of Transportation condition:

> 456:5 ‘‘(ii) a project, activity, or program
> 456:6 for which the only Federal involvement is
> 456:7 a loan, loan guarantee, grant (including a
> 456:8 capitalization grant), cost-share award, or
> 456:9 other form of financial assistance that is
> 456:10 not for the primary purpose of historic
> 456:11 preservation, subject to the condition that
> 456:12 this clause shall not apply to a project that
> 456:13 receives more than $10,000,000 of finan -
> 456:14 cial assistance from the Department of
> 456:15 Transportation;


SA 7022 instruction 12 (cited 459:13-19; matches our 456:9-15 by text, the replacement starts at "other form of financial assistance"):

> On page 459, strike lines 13 through 19 and insert the
> following:
> other form of financial assistance with respect to which a
> Federal agency does not exercise predominant control and
> responsibility over the subsequent use of such financial
> assistance or any adverse effect of the project, activity, or
> program on a historic property;


Sept. 30 bill, end of the exclusion list (old 385:17-385:25), where instruction 13 lands. No subparagraph (C) follows:

> 385:17 maintenance, or post-approval implementa -
> 385:18 tion of a project, activity, or program after
> 385:19 the determination has been made under
> 385:20 subsection (c), except that a subsequent
> 385:21 discrete decision of a Federal agency to
> 385:22 amend or materially modify a determina -
> 385:23 tion made under subsection (c) is itself an
> 385:24 undertaking, to the extent provided in this
> 385:25 section.’’; and
> 386:1 (4) by adding at the end the following:


SA 6883, end of the exclusion list (458:5-458:15). Same words as Sept. 30; no subparagraph (C):

> 458:5 ‘‘(ix) the continuation, operation,
> 458:6 maintenance, or post-approval implementa -
> 458:7 tion of a project, activity, or program after
> 458:8 the determination has been made under
> 458:9 subsection (c), except that a subsequent
> 458:10 discrete decision of a Federal agency to
> 458:11 amend or materially modify a determina -
> 458:12 tion made under subsection (c) is itself an
> 458:13 undertaking, to the extent provided in this
> 458:14 section.’’; and
> 458:15 (4) by adding at the end the following:


SA 7022 instruction 13 (cited 461:17; matches our 458:13-14 by text, the replacement starts at "section."):

> On page 461, strike line 17 and insert the following:
> section.
> ``(C) Rule of construction with respect to federal
> financial assistance.--
> ``(i) Transportation projects.--For purposes of clause (ii)
> of subparagraph (B), the Department of Transportation shall
> be considered to have predominant control and responsibility
> over the subsequent use of financial assistance described in
> that clause for any project, activity, or program that
> receives more than $10,000,000 of financial assistance from
> the Department of Transportation.
> ``(ii) Other federally assisted projects.--Nothing in
> clause (i) precludes a determination that a Federal agency
> exercises predominant control and responsibility over the
> subsequent use of financial assistance described in
> subparagraph (B)(ii) with respect to a project, activity, or
> program that receives financial assistance from any other
> Federal agency, without regard to the amount of such
> assistance.''; and


The new (C)(i) refers to "clause (ii) of subparagraph (B)", which is the clause instruction 12 rewrites. Instruction 12 drops the SA 6883 Department of Transportation $10,000,000 condition from clause (ii) itself and instruction 13 restates it in (C)(i) as a presumption of predominant control.

### 4.7 Section 2302, Historic Preservation Fund authorization (instruction 14)

Sept. 30 bill (old 414:7-414:11):

> 414:7 is amended to read as follows:
> 414:8 ‘‘§ 303102. Funding
> 414:9 ‘‘There is authorized to be appropriated for deposit
> 414:10 in the Historic Preservation Fund $200,000,000 for each
> 414:11 of fiscal years 2027 through 2036.’’.


SA 6883 (488:15-488:22):

> 488:15 is amended to read as follows:
> 488:16 ‘‘§ 303102. Funding
> 488:17 ‘‘For each of fiscal years 2027 through 2036, there
> 488:18 is authorized to be appropriated, from the unappropriated
> 488:19 balance of the Historic Preservation Fund on September
> 488:20 30, 2026, or the general fund of the Treasury,
> 488:21 $200,000,000 for deposit in the Historic Preservation
> 488:22 Fund.’’.


SA 7022 (cited 491:21):

> On page 491, line 21, strike ``$200,000,000'' and insert
> ``$300,000,000''.


The quoted figure is on 488:21 in our print. Placement is by text; see section 5.


### 4.8 Technical-only sections

Instructions 1, 2, 3, 4, 6 and 7 are typo or pointer fixes and get no three-way reading. For 1110, the Sept. 30 text at old 68:22-69:2 is "(1) ORIGINAL JURISDICTION.—The court of appeals of the United States for the circuit in which a project subject to an authorization will be constructed, expanded, or operated shall have original and exclusive jurisdiction over a claim." SA 6883 replaced it with (A) and (B) (73:7-74:3), and the clause SA 7022 corrects is at 73:8-73:11. For 1202 the Sept. 30 text (old 112:14-16) and SA 6883 (120:11-13) both read "In re-/viewing a petition under this sub-/clause, a reviewing court shall con-/sider—". For 1304 the Sept. 30 text is old 152:17-18, "the State, after the notification and / period provided under subparagraph (B)(i),", unchanged in SA 6883 at 160:13-14.

## 5. Unresolved

1. Instruction 12 (cited 459:13-19): our SA 6883 print has no matching text on page 459 lines 13-19 (those lines belong to the "(iii) Applicability of other provisions" clause). The replacement begins "other form of financial assistance", which matches clause (ii) of the "undertaking" exclusion at 456:9-15. Placement is by text, not by cited line; the cited line numbers also differ from ours.
2. Instruction 13 (cited 461:17): our page 461 line 17 is "clause (ii) or (iii) of subparagraph", inside the consultation clause. The insert starts with "section." and ends with a closing quote and "; and", which matches the end of the exclusion list at 458:13-14 ("to the extent provided in this / section.''; and"). Placement by text; confidence moderate to high.
3. Instruction 14 (cited 491:21): our page 491 line 21 is in section 3001 (survivor justice tax exclusion) and has no dollar figure. The "$200,000,000" on a line 21 is at 488:21 in section 2302, a three-page offset, the same offset as instructions 12 and 13. The only other "$200,000,000" in the print is at 227:9 (an authorization "for each of fiscal years 2027 through 2031"). Placement at 488:21 is by text and offset, not by the cited page.
4. Pages 459, 461 and 491 in the Record are each three pages after the text they appear to edit, while the cites for pages 73 to 284 match our print exactly. The Record may cite a different print of SA 6883 than `substitute_raw.txt` for the Division B tail. This file does not establish which; check against the printed SA 6883 before relying on page cites for instructions 12 to 14.
5. Instruction 10 (cited 242:2): the Record gives no paragraph heading for the insert. "New FPA section 216(d)" is inferred from position (it follows paragraph (5) PRE-FILING PROCESSES at 241:21-242:2). The inserted text refers to "a permit under subsection (b)", consistent with that.
6. Instruction 1 (73:9): "9(b)" is on that line as cited. Treating 19(b) as the Natural Gas Act section matching 15 U.S.C. 717r(b) is outside knowledge, not from the files; SA 6883 at 486:6 (section 2301) already cites "section 19(b) of the Natural Gas Act".
