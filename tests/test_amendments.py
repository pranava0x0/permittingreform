"""The November 7 substitute: parse, diff and the Amendments payload."""
import copy
import html
import json
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import amendments  # noqa: E402
import build  # noqa: E402
import diff_bill  # noqa: E402

CORE, _, ERRORS = build.build()
AMEND = CORE["amend"]
OLD = json.loads((ROOT / "data/bill/sections.json").read_text(encoding="utf-8"))["sections"]
NEW = json.loads((ROOT / "data/bill/substitute_sections.json").read_text(encoding="utf-8"))["sections"]


class Substitute(unittest.TestCase):
    def test_every_section_of_both_texts_appears_once(self):
        olds = [r["old"]["n"] for r in AMEND["rows"] if "old" in r]
        news = [r["new"]["n"] for r in AMEND["rows"] if "new" in r]
        self.assertEqual(sorted(olds), sorted(s["number"] for s in OLD))
        self.assertEqual(sorted(news), sorted(s["number"] for s in NEW))

    def test_the_committed_diff_matches_the_parsed_texts(self):
        self.assertEqual(json.loads((ROOT / "data/bill/substitute_diff.json").read_text(encoding="utf-8")), diff_bill.build())

    def test_a_reused_number_keeps_two_rows(self):
        # Sept 2242 (Northwest Power Council) is dropped; Sept 2243 becomes the new 2242.
        rows = {r["id"]: r for r in AMEND["rows"]}
        self.assertEqual(rows["2242-dropped"]["status"], "dropped")
        self.assertEqual(rows["2242"]["old"]["n"], "2243")
        # The dropped section sits where it was, after 2241, not at the top of the list.
        order = [r["id"] for r in AMEND["rows"]]
        self.assertEqual(order[order.index("2242-dropped") - 1], "2241")

    def test_every_changed_section_has_cited_points(self):
        for r in AMEND["rows"]:
            if r["status"] == "unchanged":
                continue
            self.assertTrue(r["points"], r["id"])
            for p in r["points"]:
                self.assertIn(p["side"], ("old", "new"))
                self.assertEqual(len(p["c"]), 4)

    def test_each_hunk_reads_in_both_texts(self):
        # Context plus struck words is a run of the old text; inserted words are a run of the new.
        old = {s["number"]: " ".join(s["text"].split()) for s in OLD}
        new = {s["number"]: " ".join(s["text"].split()) for s in NEW}
        checked = 0
        for r in AMEND["rows"]:
            for h in r.get("hunks", []):
                before = " ".join(x for x in (h["before"], h["del"], h["after"]) if x)
                after_ = " ".join(x for x in (h["before"], h["ins"], h["after"]) if x)
                self.assertIn(before, old[r["old"]["n"]], f"{r['id']} hunk at {h['a']}")
                # Context is quoted from the old text, which a neighboring hunk may edit; the inserted words stand alone.
                if h["ins"]:
                    self.assertIn(h["ins"], new[r["new"]["n"]], f"{r['id']} hunk at {h['b']}")
                checked += 1
        self.assertGreater(checked, 400)

    def test_a_span_that_is_not_in_the_text_fails_the_build(self):
        notes = json.loads((ROOT / "data/bill/substitute_notes.json").read_text(encoding="utf-8"))
        bad = copy.deepcopy(notes)
        bad["1401"]["points"][0]["new"] = "words that the substitute never prints"
        real = amendments.load

        def fake(path):
            return bad if path.name == "substitute_notes.json" else real(path)
        with patch.object(amendments, "load", side_effect=fake):
            errors = []
            amendments.build(errors)
        self.assertTrue(any("1401 point 1" in e for e in errors), errors)

    def test_a_changed_section_without_a_note_fails_the_build(self):
        real = amendments.load

        def fake(path):
            if path.name == "substitute_notes.json":
                notes = real(path)
                notes.pop("2107")
                return notes
            return real(path)
        with patch.object(amendments, "load", side_effect=fake):
            errors = []
            amendments.build(errors)
        self.assertTrue(any("2107 (edited) has no change note" in e for e in errors), errors)

    def test_section_pages_know_each_sections_fate(self):
        ix = build.browser_core(CORE)["amend_index"]
        self.assertEqual(set(ix["sections"]), {s["number"] for s in OLD})

    def test_reactions_and_source_bills_are_sourced(self):
        for x in AMEND["reactions"]:
            self.assertIn(x["stance"], amendments.STANCES)
            self.assertTrue(x["sources"][0]["quote"] and x["sources"][0]["url"].startswith("http"))
        # A section the sponsors describe as adding another bill names that bill's sponsors.
        for r in AMEND["rows"]:
            if any(b.startswith(("Adds H.R.", "Adds S.")) for b in r.get("sponsor_summary", [])):
                self.assertIn("origin", r, f"section {r['id']} names no source bill")

    def test_status_labels_match_in_every_render_path(self):
        js = (ROOT / "site/app.js").read_text(encoding="utf-8")
        m = re.search(r"const AM_STATUS = \{([^}]*)\}", js)
        js_keys = set(re.findall(r'"?(\w+)"?:', m.group(1)))
        self.assertEqual(js_keys, set(amendments.STATUSES))
        self.assertEqual(set(build.AMEND_STATUS), set(amendments.STATUSES))

    def test_the_timeline_states_the_diff_counts(self):
        ev = next(e for e in CORE["timeline"] if e["id"] == "2026-11-07-substitute-amendment")
        c = AMEND["counts"]
        self.assertIn(f"edits {c['edited']} sections", ev["summary"])
        self.assertIn(f"adds {c['new']}", ev["summary"])
        self.assertEqual(c["dropped"], 1)
        self.assertIn("drops one", ev["summary"])

    def test_context_never_overlaps_a_neighboring_hunk(self):
        old = {s["number"]: " ".join(s["text"].split()) for s in OLD}
        for r in AMEND["rows"]:
            text = old.get(r.get("old", {}).get("n"), "")
            for h in r.get("hunks", []):
                for words in (h["before"], h["after"]):
                    self.assertIn(words, text, r["id"])

    def test_the_static_edition_prints_every_reaction(self):
        page = build.amendments_html(CORE)
        for x in AMEND["reactions"]:
            self.assertIn(html.escape(x["who"]), page, x["id"])
        js = (ROOT / "site/app.js").read_text(encoding="utf-8")
        for k, label in amendments.STANCE_LABELS.items():
            self.assertIn(f'["{k}", "{label}"]', js)

    def test_payload_and_static_page_are_in_sync(self):
        self.assertEqual((ROOT / "site/data/amend.js").read_text(encoding="utf-8"), build.dump_js("PR_AMEND", AMEND))
        self.assertEqual((ROOT / "site/amendments.html").read_text(encoding="utf-8"), build.amendments_html(CORE))


if __name__ == "__main__":
    unittest.main()
