"""The build: no dangling references, and the committed site data matches its sources."""
import json
import sys
import tempfile
from unittest.mock import patch
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import billtext  # noqa: E402
import build  # noqa: E402
import check_data  # noqa: E402
import check_quotes  # noqa: E402
import integrate_research as vocab  # noqa: E402

CORE, PARAS, ERRORS = build.build()


class Build(unittest.TestCase):
    def test_pdf_replacement_invalidates_the_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "bill.pdf").write_bytes(b"%PDF-unrelated")
            with patch.object(build, "SITE", Path(tmp)):
                _, _, errors = build.build()
            self.assertTrue(any("PDF differs" in e for e in errors))

    def test_changed_review_inputs_mark_saved_coverage_stale(self):
        with patch.object(billtext, "review_fingerprint", return_value="different-inputs"):
            core, _, _ = build.build()
        self.assertTrue(core["checks"]["inference"]["stale"])

    def test_the_build_reports_no_errors(self):
        self.assertEqual(ERRORS, [])

    def test_committed_site_data_is_in_sync_with_the_sources(self):
        self.assertEqual((ROOT / "site/data/core.js").read_text(encoding="utf-8"), build.dump_js("PR_DATA", CORE))
        self.assertEqual((ROOT / "site/data/bill.js").read_text(encoding="utf-8"), build.dump_js("PR_BILL", PARAS))
        self.assertEqual((ROOT / "site/llms.txt").read_text(encoding="utf-8"), build.llms_txt(CORE))

    def test_every_section_is_summarized_and_every_summary_has_a_section(self):
        bill = {s["number"] for s in billtext.load_sections()["sections"]}
        self.assertEqual({s["n"] for s in CORE["sections"]}, bill)
        self.assertEqual(set(PARAS), bill)

    def test_every_quote_cite_falls_inside_its_section(self):
        checked = 0
        for s in CORE["sections"]:
            for q in s["quotes"]:
                p1, l1, p2, l2 = q["c"]
                self.assertTrue(s["p1"] <= p1 <= p2 <= s["p2"], (s["n"], q["c"]))
                checked += 1
        self.assertGreaterEqual(checked, len(CORE["sections"]))

    def test_a_missing_quote_fails_the_build(self):
        analysis = json.loads((ROOT / "data/bill/analysis.json").read_text(encoding="utf-8"))
        original = build.load

        def sabotaged(path):
            data = original(path)
            if path.name == "analysis.json":
                data["sections"]["1101"]["quotes"][0]["text"] += " and other words the bill does not say"
            return data

        self.assertTrue(analysis["sections"]["1101"]["quotes"])
        build.load = sabotaged
        try:
            _, _, errors = build.build()
        finally:
            build.load = original
        self.assertTrue(any("section 1101: quote not found" in e for e in errors), errors)

    def test_bill_quote_checker_agrees_with_the_build(self):
        total, bad = check_quotes.bill_quotes()
        self.assertEqual(bad, [])
        communities = sum(1 for r in (CORE.get("communities") or {"rows": []})["rows"] if r.get("quote"))
        self.assertEqual(total, CORE["meta"]["quotes"] + len(CORE["overview"]["clocks"]) + len(CORE["overview"]["money"]) + communities)

    def test_every_communities_quote_carries_a_computed_cite(self):
        rows = (CORE.get("communities") or {"rows": []})["rows"]
        self.assertTrue(rows, "data/communities.json produced no rows")
        for r in rows:
            if r.get("quote"):
                self.assertIn("c", r, f"communities {r['id']}: quote has no cite")

    def test_the_pdf_the_cites_point_to_is_present(self):
        pdf = ROOT / "site" / CORE["meta"]["pdf"]
        self.assertTrue(pdf.exists())
        self.assertEqual(pdf.read_bytes()[:5], b"%PDF-")


class Data(unittest.TestCase):
    def test_the_data_validator_passes(self):
        errs, counts = check_data.check(CORE)
        self.assertEqual(errs, [])
        self.assertGreater(counts["prose strings"], 500)

    def test_the_data_validator_catches_a_dash_and_a_bad_reference(self):
        broken = json.loads(json.dumps(CORE))
        broken["sections"][0]["plain"] = "A summary — with a dash."
        broken["media"][0]["type"] = "telegram"
        errs, _ = check_data.check(broken)
        self.assertTrue(any("em or en dash" in e for e in errs))
        self.assertTrue(any("unknown type 'telegram'" in e for e in errs))

    def test_every_vocabulary_value_has_a_label_in_the_interface(self):
        js = (ROOT / "site/app.js").read_text(encoding="utf-8")
        sectors = js[js.index("const SECTORS = {"):js.index("};", js.index("const SECTORS = {"))]
        for key in vocab.SECTORS:
            self.assertIn(f"{key}:", sectors, key)
        types = js[js.index("const MEDIA_TYPES = ["):js.index("];", js.index("const MEDIA_TYPES = ["))]
        for key in vocab.MEDIA_TYPES:
            self.assertIn(f'"{key}"', types, key)
        stances = js[js.index("const STANCE = {"):js.index("};", js.index("const STANCE = {"))]
        for key in vocab.STANCES:
            self.assertIn(f"{key}:", stances, key)
        css = (ROOT / "site/styles.css").read_text(encoding="utf-8")
        for key in vocab.STANCES:
            self.assertIn(f".stance-{key}", css, key)

    def test_every_topic_in_use_is_registered(self):
        used = {t for s in CORE["sections"] for t in s["topics"]}
        used |= {t for e in CORE["timeline"] for t in e.get("topics", [])}
        used |= {t for it in CORE["media"] for t in it.get("topics", [])}
        self.assertLessEqual(used, set(CORE["topics"]))


if __name__ == "__main__":
    unittest.main()
