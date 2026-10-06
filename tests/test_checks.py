"""The validators themselves: each must be able to fail."""
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import billtext  # noqa: E402
import build  # noqa: E402
import check_links  # noqa: E402
import check_quotes  # noqa: E402
import infer_check  # noqa: E402
import webfetch  # noqa: E402

CORE, _, _ = build.build()
PAGE = ("Sen. Example said the bill was needed. \u201cWe are not building the amount of interregional "
        "transmission that we need right now,\u201d she said \u2014 and then left.")


class QuoteMatch(unittest.TestCase):
    def test_a_verbatim_quote_is_verified(self):
        self.assertEqual(check_quotes.match("We are not building the amount of interregional transmission", PAGE)[0], "verified")

    def test_quote_marks_dashes_and_case_do_not_matter(self):
        self.assertEqual(check_quotes.match('"we are not building the amount of interregional transmission that we need right now," she said - and then left', PAGE)[0], "verified")

    def test_a_changed_word_is_not_verified(self):
        result, share = check_quotes.match("We are not building the amount of interstate transmission that we need right now", PAGE)
        self.assertNotEqual(result, "verified")
        self.assertLess(share, 1.0)

    def test_an_invented_quote_is_missing(self):
        self.assertEqual(check_quotes.match("Permitting reform will lower electricity prices by half within a decade", PAGE)[0], "missing")

    def test_an_elided_quote_needs_every_part_on_the_page(self):
        self.assertEqual(check_quotes.match("We are not building ... that we need right now", PAGE)[0], "verified")
        self.assertNotEqual(check_quotes.match("We are not building ... that we will never need", PAGE)[0], "verified")

    def test_a_word_split_by_stray_spacing_still_matches(self):
        split = PAGE.replace("interregional", "inter regional")
        self.assertNotEqual(check_quotes.match("We are not building the amount of interregional transmission", split)[0], "verified")

    def test_elided_passages_must_keep_the_source_order(self):
        self.assertNotEqual(check_quotes.match("third passage ... first passage", "first passage second passage third passage")[0], "verified")

    def test_truncated_numbers_and_words_fail(self):
        self.assertNotEqual(check_quotes.match("spend $20,000", "spend $20,000,000 on it")[0], "verified")
        self.assertNotEqual(check_quotes.match("transmissio", "transmission")[0], "verified")

    def test_a_short_fragment_cannot_ride_on_the_spacing_rule(self):
        self.assertNotEqual(check_quotes.match("the rapist", "She saw a therapist on Monday.")[0], "verified")


class PageText(unittest.TestCase):
    def test_an_inline_tag_inside_a_word_leaves_no_space(self):
        self.assertIn("interregional transmission", webfetch.html_to_text("<p>inter<span class=x>regional</span> <b>transmission</b></p>"))

    def test_a_block_tag_separates_words(self):
        text = webfetch.html_to_text("<div>first</div><div>second</div><p>third<br>fourth</p>")
        self.assertEqual(text.split(), ["first", "second", "third", "fourth"])

    def test_script_and_style_content_is_dropped(self):
        text = webfetch.html_to_text("<style>p{color:red}</style><script>var hidden = 1;</script><p>shown</p>")
        self.assertEqual(text.split(), ["shown"])


class Routes(unittest.TestCase):
    def test_platform_posts_go_to_their_public_endpoints(self):
        kind, target = webfetch.route("https://x.com/SenMikeLee/status/2105333969286037895")
        self.assertEqual(kind, "x")
        self.assertTrue(target.startswith("https://publish.twitter.com/oembed?"))
        kind, target = webfetch.route("https://bsky.app/profile/example.bsky.social/post/3abc")
        self.assertEqual(kind, "bluesky")
        self.assertIn("at%3A%2F%2Fexample.bsky.social%2Fapp.bsky.feed.post%2F3abc", target)
        self.assertEqual(webfetch.route("https://www.youtube.com/watch?v=abc")[0], "youtube")

    def test_an_x_photo_link_is_checked_through_its_post(self):
        post = webfetch.route("https://x.com/hausfath/status/2105398276681785416")
        self.assertEqual(webfetch.route("https://x.com/hausfath/status/2105398276681785416/photo/1"), post)
        self.assertEqual(webfetch.route("https://x.com/hausfath/status/2105398276681785416/video/2"), post)

    def test_an_ordinary_page_and_a_profile_are_fetched_directly(self):
        self.assertEqual(webfetch.route("https://www.epw.senate.gov/public/"), ("page", "https://www.epw.senate.gov/public/"))
        self.assertEqual(webfetch.route("https://x.com/SenCapito")[0], "page")


class Links(unittest.TestCase):
    def test_the_checker_sees_every_kind_of_link_the_site_renders(self):
        found = check_links.collect(CORE)
        places = {where.split(".")[0] for wheres in found.values() for where in wheres}
        self.assertEqual(places, {"meta", "overview", "compare", "timeline", "people", "media", "takes"})
        self.assertIn(CORE["meta"]["source_pdf"], found)
        for item in CORE["media"]:
            self.assertIn(item["url"].split("#", 1)[0], found)

    def test_a_non_http_value_is_not_collected(self):
        for url in check_links.collect(CORE):
            self.assertRegex(url, r"^https?://")


class BrowserRecord(unittest.TestCase):
    def test_every_recorded_page_is_one_the_site_links_to(self):
        linked = set(check_links.collect(CORE))
        for url in check_links.browser_pages():
            self.assertIn(url, linked, "a browser record for a page the site no longer cites")

    def test_every_recorded_quote_is_one_the_site_prints_from_that_page(self):
        printed = {(r["url"], check_quotes.canon(r["text"])) for r in check_quotes.web_quotes(CORE)}
        for url, rec in check_links.browser_pages().items():
            for quote in rec.get("quotes", []):
                self.assertIn((url, check_quotes.canon(quote)), printed, quote[:60])


class Inference(unittest.TestCase):
    def test_positive_claims_require_complete_evidence(self):
        self.assertFalse(infer_check.evidence_is_present("1106.k1", "Requires 15 days", "15", "150 days"))
        self.assertFalse(infer_check.evidence_is_present("cmp.x.senate", "Same as EPRA 2024.", "", "text"))
        self.assertFalse(infer_check.evidence_is_present("1106.s1", "A rule applies.", "", "text"))
        self.assertTrue(infer_check.evidence_is_present("cmp.x.speed", "Not addressed.", "", "text"))
        self.assertTrue(infer_check.evidence_is_present("1106.k1", "Requires 150 days", "150 days", "within 150 days of receipt"))

    def test_an_abbreviation_does_not_end_a_sentence(self):
        got = infer_check.sentences("Amends 16 U.S.C. 824p to add a deadline. Order No. 1920 still counts for planning.")
        self.assertEqual(got, ["Amends 16 U.S.C. 824p to add a deadline.", "Order No. 1920 still counts for planning."])

    def test_paragraphs_split_into_separate_claims(self):
        got = infer_check.sentences("The agency has 30 days to respond.\n\nCourts must rule within 120 days.")
        self.assertEqual(len(got), 2)

    def test_every_summary_sentence_and_key_point_becomes_a_claim(self):
        bill = billtext.load_sections()
        units = infer_check.section_units(CORE, bill, None)
        self.assertEqual(len(units), len(CORE["sections"]))
        ids = [cid for u in units for cid, _ in u["claims"]]
        self.assertEqual(len(ids), len(set(ids)))
        points = sum(len(s["points"]) for s in CORE["sections"])
        self.assertEqual(sum(1 for cid in ids if ".k" in cid), points)

    def test_every_comparison_cell_for_a_bill_becomes_a_claim(self):
        bill = billtext.load_sections()
        ids = {cid for u in infer_check.compare_units(CORE, bill) + infer_check.row_units(CORE, bill) for cid, _ in u["claims"]}
        for g in CORE["compare"]["groups"]:
            for r in g["rows"]:
                self.assertIn(f"cmp.{r['id']}.speed", ids)
                self.assertIn(f"cmp.{r['id']}.epra", ids)
                if r["senate"].get("sections"):
                    self.assertTrue(any(i.startswith(f"cmp.{r['id']}.senate.s") for i in ids), r["id"])

    def test_row_claims_are_checked_against_only_the_sections_they_cite(self):
        bill = billtext.load_sections()
        rows = {rc["id"]: rc for rc in build.row_claims(CORE["overview"], CORE["compare"], CORE["communities"], CORE["datacenters"])}
        for u in infer_check.row_units(CORE, bill):
            nums = u["key"].split(" ", 1)[1].split(",")
            for cid, _ in u["claims"]:
                self.assertEqual(sorted(set(rows[cid]["sections"])), nums, cid)

    def test_a_new_bill_text_re_asks_every_claim(self):
        import contextlib, io
        saved = json.loads((ROOT / "data/checks/inference.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            for sha, expect_all in ((saved["bill_sha256"], False), ("a-different-draft", True)):
                path = Path(tmp) / "inference.json"
                path.write_text(json.dumps(dict(saved, bill_sha256=sha)), encoding="utf-8")
                out = io.StringIO()
                with patch.object(infer_check, "OUT", path), patch.object(sys, "argv", ["infer_check", "--dry-run"]), \
                        contextlib.redirect_stdout(out):
                    infer_check.main()
                self.assertEqual("asking about every claim" in out.getvalue(), expect_all, out.getvalue()[:200])

    def test_a_reconcile_does_not_stamp_a_new_bill_onto_old_verdicts(self):
        import contextlib, io
        saved = json.loads((ROOT / "data/checks/inference.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            out_path, pc, rc = Path(tmp) / "inference.json", Path(tmp) / "pc.json", Path(tmp) / "rc.json"
            out_path.write_text(json.dumps(dict(saved, bill_sha256="an-older-draft", input_sha256="old-inputs")), encoding="utf-8")
            pc.write_text((ROOT / "data/bill/point_cites.json").read_text(encoding="utf-8"), encoding="utf-8")
            rc.write_text((ROOT / "data/bill/row_cites.json").read_text(encoding="utf-8"), encoding="utf-8")
            with patch.object(infer_check, "OUT", out_path), patch.object(infer_check, "POINT_CITES", pc), \
                    patch.object(build, "ROW_CITES", rc), patch.object(check_links, "merge_summary", lambda *a, **k: None), \
                    patch.object(sys, "argv", ["infer_check", "--cached-only"]), contextlib.redirect_stdout(io.StringIO()):
                infer_check.main()
            written = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(written["bill_sha256"], "an-older-draft")
        self.assertEqual(written["input_sha256"], "old-inputs")

    def test_a_joined_evidence_span_yields_only_a_verbatim_piece(self):
        lines = next(x for x in billtext.load_sections()["sections"] if x["number"] == "1304")["lines"]
        joined = "with the written agreement of the Secretary and a State... the Secretary may assign, and the State may assume, the consultation responsibilities"
        piece = infer_check.usable_span(joined, lines)
        self.assertEqual(piece, "the Secretary may assign, and the State may assume, the consultation responsibilities")
        self.assertIsNone(infer_check.usable_span("words this bill never uses ... nor these other words either", lines))
        self.assertIsNone(infer_check.usable_span("", lines))

    def test_absence_claims_are_recognized_and_positive_claims_are_not(self):
        for claim in ("No export provisions.", "[Coal] No leasing provisions.", "Royalties are unchanged;",
                      "The text does not say what notice the earlier review must have had."):
            self.assertTrue(billtext.is_absence(claim), claim)
        for claim in ("Indian lands are excluded.", "FERC may permit lines of 230 kilovolts and up.", "Same as EPRA 2024."):
            self.assertFalse(billtext.is_absence(claim), claim)

    def test_a_stale_passage_is_pruned_and_a_current_one_kept(self):
        bill = billtext.load_sections()
        sec = next(s for s in bill["sections"] if s["number"] == "1101")
        span = "Nothing in this Act mandates a particular outcome"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "point_cites.json"
            path.write_text(json.dumps({"1101": {"An edited-away claim": span, "Kept claim": span}}), encoding="utf-8")
            with patch.object(infer_check, "POINT_CITES", path):
                infer_check.write_point_cites([], bill, {"1101.k1": "Kept claim"})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"1101": {"Kept claim": span}})
        self.assertIsNotNone(billtext.locate(sec["lines"], span))

    def test_no_batch_is_larger_than_the_word_limit_unless_one_source_is(self):
        bill = billtext.load_sections()
        units = infer_check.section_units(CORE, bill, None) + infer_check.compare_units(CORE, bill)
        plan = infer_check.batches(units)
        self.assertEqual(sum(len(b) for b in plan), len(units))
        for batch in plan:
            words = sum(len(u["text"].split()) + sum(len(c.split()) for _, c in u["claims"]) for u in batch)
            self.assertTrue(words <= infer_check.MAX_WORDS or len(batch) == 1, words)

    def test_a_stored_passage_is_in_the_bill_and_belongs_to_a_current_key_point(self):
        path = ROOT / "data/bill/point_cites.json"
        if not path.exists():
            self.skipTest("no key-point passages yet")
        cites = json.loads(path.read_text(encoding="utf-8"))
        by_num = {s["number"]: s for s in billtext.load_sections()["sections"]}
        for n, entries in cites.items():
            for point, passage in entries.items():
                self.assertIsNotNone(billtext.locate(by_num[n]["lines"], passage), f"{n}: {passage[:60]}")


if __name__ == "__main__":
    unittest.main()


class BrowserRecords(unittest.TestCase):
    def test_a_browser_record_counts_only_for_its_own_text(self):
        import check_quotes
        opened = {"https://example.org/a": {"opened": "2026-10-02", "quotes": ["The exact words"]}}
        hit = {"url": "https://example.org/a", "text": "the exact  words", "result": "unreachable"}
        miss = {"url": "https://example.org/a", "text": "other words", "result": "unreachable"}
        other = {"url": "https://example.org/b", "text": "The exact words", "result": "unreachable"}
        for row in (hit, miss, other):
            check_quotes.from_browser(row, opened)
        self.assertEqual([hit["result"], miss["result"], other["result"]], ["browser", "unreachable", "unreachable"])

