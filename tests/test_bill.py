"""The parsed bill: structure, cites, and the helpers the site and validators share."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import billtext  # noqa: E402
import parse_bill  # noqa: E402

BILL = billtext.load_sections()
BY_NUM = {s["number"]: s for s in BILL["sections"]}


class ParsedBill(unittest.TestCase):
    def test_split_heading_keeps_body_word_on_its_printed_line(self):
        rows = [[71, 19, "“(B) FEDERAL ACTION DURING RE" + parse_bill.SOFT], [71, 20, "MAND.—The activity"]]
        parse_bill.rejoin_words(rows)
        self.assertEqual(rows[1][2], "The activity")
        self.assertEqual(billtext.locate(rows, "The activity")["l1"], 20)

    def test_number_splits_and_quoted_small_caps_are_normalized(self):
        rows = [[8, 16, "Public Law 102–"], [8, 17, "580);"]]
        parse_bill.rejoin_words(rows)
        self.assertEqual(rows[0][2], "Public Law 102–580);")
        self.assertEqual(parse_bill.normalize_line("‘‘P REPARATION’’"), "“PREPARATION”")
        self.assertEqual(parse_bill.normalize_line("HIGH -DENSITY"), "HIGH-DENSITY")

    def test_every_section_in_the_table_of_contents_was_parsed(self):
        toc = [e["label"] for e in BILL["outline"] if e["kind"] == "section"]
        self.assertEqual(toc, [s["number"] for s in BILL["sections"]])
        self.assertEqual(len(toc), 71)

    def test_sections_run_in_page_order_and_cover_the_bill(self):
        pages = [(s["page_start"], s["page_end"]) for s in BILL["sections"]]
        self.assertEqual(pages[0][0], 4)
        self.assertEqual(pages[-1][1], BILL["meta"]["pages"])
        for (a_start, a_end), (b_start, _) in zip(pages, pages[1:]):
            self.assertLessEqual(a_start, a_end)
            self.assertLessEqual(a_end, b_start)

    def test_every_line_sits_inside_its_section_and_has_a_plausible_line_number(self):
        unnumbered = 0
        for s in BILL["sections"]:
            self.assertTrue(s["lines"], s["number"])
            for page, line_no, text in s["lines"]:
                self.assertTrue(s["page_start"] <= page <= s["page_end"], (s["number"], page))
                self.assertTrue(text)
                if line_no is None:
                    unnumbered += 1
                else:
                    self.assertTrue(1 <= line_no <= 30, (s["number"], page, line_no))
        self.assertLessEqual(unnumbered, 3)

    def test_printed_line_numbers_were_stripped_from_the_text(self):
        # A page of bill print carries 25 numbered lines; if the numbers leaked
        # into the text, many lines would end in a bare small integer.
        tails = sum(1 for s in BILL["sections"] for _, _, t in s["lines"] if t.rsplit(" ", 1)[-1].isdigit() and int(t.rsplit(" ", 1)[-1]) <= 25)
        total = sum(len(s["lines"]) for s in BILL["sections"])
        self.assertLess(tails / total, 0.01)

    def test_known_passages_are_where_the_print_puts_them(self):
        loc = billtext.locate(BY_NUM["1106"]["lines"], "shall not travel more than 25 miles from their official duty station")
        self.assertEqual((loc["p1"], loc["l1"], loc["p2"], loc["l2"], loc["count"]), (54, 18, 54, 20, 1))
        self.assertIn("remand, without vacatur", BY_NUM["1110"]["text"].replace("\n", " "))
        self.assertIn("20 megawatts", BY_NUM["2107"]["text"].replace("\n", " "))
        self.assertEqual(BY_NUM["1401"]["heading"], "Maintaining Federal authorizations or permits for projects with non-Federal sponsors")

    def test_words_split_across_lines_were_rejoined(self):
        text = BY_NUM["1106"]["text"]
        self.assertIn("RESPONSIBILITIES", text)
        self.assertNotIn("RE-", text)
        self.assertNotIn("designa ", " ".join(s["text"] for s in BILL["sections"]))


class Locate(unittest.TestCase):
    def test_a_real_quote_is_found_with_its_span(self):
        loc = billtext.locate(BY_NUM["1110"]["lines"], "the only remedy the court may order to redress that violation is to remand, without vacatur")
        self.assertIsNotNone(loc)
        self.assertLessEqual((loc["p1"], loc["l1"]), (loc["p2"], loc["l2"]))

    def test_partial_words_and_numbers_fail(self):
        for quote in ("ederal agency", "not later than 15", "the 150 day", "remand, without vacat"):
            self.assertIsNone(billtext.locate(BY_NUM["1110"]["lines"], quote), quote)
        self.assertIsNone(billtext.locate([[1, 1, "$20,000,000"]], "$20,000"))
        self.assertIsNotNone(billtext.locate([[1, 1, "150 days; 15 days"]], "15 days"))

    def test_an_altered_quote_is_not_found(self):
        self.assertIsNone(billtext.locate(BY_NUM["1110"]["lines"], "the only remedy the court may order is to vacate the authorization"))
        self.assertIsNone(billtext.locate(BY_NUM["1110"]["lines"], ""))

    def test_a_quote_from_another_section_is_not_found(self):
        self.assertIsNone(billtext.locate(BY_NUM["1101"]["lines"], "shall not travel more than 25 miles"))


class Paragraphs(unittest.TestCase):
    def test_enumerators_set_the_indent_level(self):
        paras = billtext.paragraphs(BY_NUM["1106"]["lines"])
        self.assertGreater(len(paras), 100)
        self.assertEqual(paras[0][2], 0)
        by_start = {p[3][:40]: p[2] for p in paras}
        self.assertEqual(by_start["“(a) DETERMINATION OF AGENCY ROLES AND R"], 1)
        self.assertEqual(by_start["“(1) LEAD AGENCY.—"], 2)
        self.assertEqual(by_start["“(A) DESIGNATION.—"], 3)
        self.assertEqual([p[2] for p in paras if p[3].startswith("“(I) the magnitude")], [5])

    def test_a_cross_reference_that_wraps_to_a_new_line_does_not_start_a_paragraph(self):
        paras = billtext.paragraphs(BY_NUM["1106"]["lines"])
        hit = [p for p in paras if "(a)(2)(A) with respect to each agency" in p[3]]
        self.assertEqual(len(hit), 1)
        self.assertTrue(hit[0][3].startswith("“(1) IN GENERAL.—Not later than 30 days"), hit[0][3][:60])

    def test_wrapped_conjunction_does_not_merge_next_item(self):
        p = billtext.paragraphs([[1, 1, "“(I) first;"], [1, 2, "and"], [2, 1, "“(II) second."]])
        self.assertEqual(len(p), 2)
        self.assertEqual(p[1][:3], [2, 1, 5])

    def test_long_roman_and_double_capital_list(self):
        self.assertIsNotNone(billtext.ENUM_RE.match("“(xxxviii) test"))
        p = billtext.paragraphs([[1, j, f"({t}) item;"] for j, t in enumerate(["Z", "AA", "BB"], 1)])
        self.assertEqual([x[2] for x in p], [3, 3, 3])

    def test_paragraphs_keep_every_word(self):
        for n in ("1101", "1402", "2107", "2301"):
            joined = " ".join(p[3] for p in billtext.paragraphs(BY_NUM[n]["lines"]))
            self.assertEqual(billtext.norm(joined), billtext.norm(BY_NUM[n]["text"]), n)


if __name__ == "__main__":
    unittest.main()
