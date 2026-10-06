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

    def test_agent_exports_match_the_browser_data_and_all_sections(self):
        self.assertEqual(json.loads((ROOT / "site/data/core.json").read_text()), CORE)
        self.assertEqual(json.loads((ROOT / "site/data/bill.json").read_text()), PARAS)
        self.assertEqual((ROOT / "site/llms-full.txt").read_text(), build.llms_full(CORE, PARAS))
        self.assertEqual((ROOT / "site/reading.html").read_text(), build.reading_html(CORE))
        self.assertEqual({p.stem for p in (ROOT / "site/sections").glob("*.md")}, set(PARAS))
        for sec in CORE["sections"]:
            text = (ROOT / f"site/sections/{sec['n']}.md").read_text()
            self.assertEqual(text, build.section_markdown(CORE, PARAS, sec))
            self.assertIn(f"sections/{sec['n']}.md", build.llms_txt(CORE))
            self.assertIn(f"sections/{sec['n']}.md", build.reading_html(CORE))
            for page, line, _, paragraph in PARAS[sec["n"]]:
                self.assertIn(paragraph, text)
                self.assertIn(f"p. {page}, line {line}", text)

    def test_full_export_keeps_every_community_quote_citation(self):
        full = build.llms_full(CORE, PARAS)
        rows = CORE["communities"]["rows"]
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(row["quote"], full)
            self.assertIn(build.pdf_citation(CORE["meta"]["site_url"], row["c"]), full, row["id"])

    def test_agent_exports_disclose_stale_and_incomplete_review(self):
        import copy
        core = copy.deepcopy(CORE)
        core["checks"]["inference"].update(stale=True, flagged=3, unchecked=9)
        for text in (build.llms_txt(core), build.reading_html(core), build.section_markdown(core, PARAS, core["sections"][0])):
            self.assertIn("stale: true", text)
            self.assertIn("3 flagged", text)
            self.assertIn("9 unchecked", text)
            self.assertIn("not enacted law" if text.startswith("# Bipartisan") else "proposed" if text.startswith("# Sec.") else "Proposed", text)

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
        datacenters = sum(1 for r in (CORE.get("datacenters") or {"rows": []})["rows"] if r.get("quote"))
        self.assertEqual(total, CORE["meta"]["quotes"] + len(CORE["overview"]["clocks"]) + len(CORE["overview"]["money"]) + communities + datacenters)

    def test_saved_bill_quote_totals_cover_current_inputs(self):
        total, bad = check_quotes.bill_quotes()
        self.assertEqual(bad, [])
        saved = json.loads((ROOT / "data/checks/quotes.json").read_text())
        summary = json.loads((ROOT / "data/checks.json").read_text())["quotes"]
        self.assertEqual(saved["bill"], {"total": total, "verified": total})
        self.assertEqual(summary["bill_total"], total)
        self.assertEqual(summary["bill_verified"], total)

    def test_every_communities_quote_carries_a_computed_cite(self):
        rows = (CORE.get("communities") or {"rows": []})["rows"]
        self.assertTrue(rows, "data/communities.json produced no rows")
        for r in rows:
            if r.get("quote"):
                self.assertIn("c", r, f"communities {r['id']}: quote has no cite")

    def test_every_datacenters_quote_carries_a_computed_cite(self):
        rows = (CORE.get("datacenters") or {"rows": []})["rows"]
        self.assertTrue(rows, "data/datacenters.json produced no rows")
        for r in rows:
            if r.get("quote"):
                self.assertIn("c", r, f"datacenters {r['id']}: quote has no cite")

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


def build_with(edit):
    """Run the build with one source file altered in memory: edit(path_name, data) -> data."""
    original = build.load

    def sabotaged(path):
        return edit(path.name, original(path))

    with patch.object(build, "load", sabotaged):
        return build.build()


class ClaimCites(unittest.TestCase):
    """Every claim about what the bill does carries a passage from the bill text."""

    def test_every_claim_about_the_bill_carries_a_passage(self):
        self.assertEqual(CORE["checks"]["cites"]["gaps"], [])

    def test_summary_sentences_keep_every_word_of_the_summary(self):
        for sec in CORE["sections"]:
            rebuilt = "\n\n".join(" ".join(t["t"] for t in para) for para in sec["ps"])
            self.assertEqual(" ".join(rebuilt.split()), " ".join(sec["plain"].split()), sec["n"])

    def test_every_cite_falls_inside_the_cited_section(self):
        by_num = {s["n"]: s for s in CORE["sections"]}
        def inside(n, c):
            s = by_num[n]
            return s["p1"] <= c[0] and c[2] <= s["p2"]
        for sec in CORE["sections"]:
            for t in [t for para in sec["ps"] for t in para] + sec["points"]:
                if "c" in t:
                    self.assertTrue(inside(sec["n"], t["c"]), (sec["n"], t["t"][:50]))
        for rc in build.row_claims(CORE["overview"], CORE["compare"], CORE["communities"], CORE["datacenters"]):
            for t in rc["holder"].get("ts", []):
                if "c" in t:
                    self.assertIn(t["n"], rc["sections"])
                    self.assertTrue(inside(t["n"], t["c"]), rc["id"])

    def test_row_claims_cover_every_cell_that_describes_the_bill(self):
        ids = {rc["id"].rsplit(".s", 1)[0] for rc in build.row_claims(CORE["overview"], CORE["compare"], CORE["communities"], CORE["datacenters"])}
        for h in CORE["overview"]["headlines"]:
            self.assertIn(f"hl.{h['id']}", ids)
        for g in CORE["compare"]["groups"]:
            for r in g["rows"]:
                if r["senate"].get("sections"):
                    self.assertIn(f"cmp.{r['id']}.senate", ids)
        for r in CORE["compare"]["bills"]["rows"]:
            if (r.get("senate") or {}).get("sections"):
                self.assertIn(f"dcb.{r['id']}", ids)
        for i, _ in enumerate(CORE["compare"]["added"], 1):
            self.assertIn(f"add.{i}", ids)
        for r in CORE["communities"]["rows"]:
            self.assertIn(f"com.{r['id']}", ids)
        for r in CORE["datacenters"]["rows"]:
            self.assertIn(f"dc.{r['id']}", ids)

    def test_a_summary_sentence_without_a_passage_is_a_gap(self):
        first = billtext.sentences(json.loads((ROOT / "data/bill/analysis.json").read_text(encoding="utf-8"))["sections"]["1101"]["plain"])[0]

        def edit(name, data):
            if name == "point_cites.json":
                data.get("1101", {}).pop(first, None)
            return data

        core, _, errors = build_with(edit)
        self.assertEqual(errors, [])
        self.assertTrue(any(g.startswith("section 1101: no bill passage for summary sentence") for g in core["checks"]["cites"]["gaps"]))

    def test_a_flagged_claim_shows_no_cite_and_is_a_gap(self):
        first = billtext.sentences(json.loads((ROOT / "data/bill/analysis.json").read_text(encoding="utf-8"))["sections"]["1101"]["plain"])[0]

        def edit(name, data):
            if name == "inference.json":
                data["results"].append({"id": "1101.s1", "claim": first, "verdict": "partly", "evidence": "", "evidence_in_text": False, "note": "test"})
            return data

        core, _, _ = build_with(edit)
        sec = next(s for s in core["sections"] if s["n"] == "1101")
        self.assertNotIn("c", sec["ps"][0][0])
        self.assertTrue(any("semantic check flagged" in g for g in core["checks"]["cites"]["gaps"]))

    def test_a_row_passage_from_an_uncited_section_is_an_error(self):
        rc = build.row_claims(CORE["overview"], CORE["compare"], CORE["communities"], CORE["datacenters"])[0]
        other = next(s["n"] for s in CORE["sections"] if s["n"] not in rc["sections"])
        span = next(iter(json.loads((ROOT / "data/bill/point_cites.json").read_text(encoding="utf-8"))[other].values()))

        def edit(name, data):
            if name == "row_cites.json":
                data[rc["id"]] = {"claim": rc["t"], "section": other, "text": span}
            return data

        _, _, errors = build_with(edit)
        self.assertTrue(any(e.startswith(rc["id"]) for e in errors), errors)

    def test_the_build_refuses_to_write_while_gaps_remain(self):
        def edit(name, data):
            if name == "point_cites.json":
                return {}
            return data

        with patch.object(build, "load", lambda p, o=build.load: edit(p.name, o(p))), \
             patch.object(build, "SITE", Path(tempfile.mkdtemp())):
            self.assertEqual(build.main(), 1)


class Takes(unittest.TestCase):
    def test_every_take_names_real_sections_and_a_located_passage(self):
        nums = {s["n"] for s in CORE["sections"]}
        for t in CORE["takes"]["takes"]:
            self.assertTrue(set(t["sections"]) <= nums, t["id"])
            if "passage" in t:
                self.assertIn("c", t["passage"], t["id"])
                self.assertIn(t["passage"]["section"], t["sections"], t["id"])

    def test_every_take_quote_goes_through_the_web_quote_check(self):
        checked = {r["where"] for r in check_quotes.web_quotes(CORE)}
        for t in CORE["takes"]["takes"]:
            self.assertIn(f"takes.{t['id']}", checked)

    def test_a_passage_the_bill_does_not_contain_fails_the_build(self):
        def edit(name, data):
            if name == "takes.json":
                data["takes"][0]["passage"] = {"section": data["takes"][0]["sections"][0], "text": "words this bill never uses anywhere at all"}
            return data

        _, _, errors = build_with(edit)
        self.assertTrue(any("passage not found" in e for e in errors), errors)

    def test_an_unknown_side_or_stance_fails_the_build(self):
        def edit(name, data):
            if name == "takes.json":
                data["takes"][0]["side"] = "astrologers"
                data["takes"][1]["stance"] = "vibes"
            return data

        _, _, errors = build_with(edit)
        self.assertTrue(any("unknown side" in e for e in errors) and any("unknown stance" in e for e in errors), errors)
