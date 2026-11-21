"""Claims in coverage point at passed-text passages; the checks reject a bad pointer.

Each validation rule has a case that must pass and a case that must fail, so a
check that silently stopped firing would show here (CLAUDE.md: a checker improved
into silence passes everything)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import claims as C  # noqa: E402
import claim_sections  # noqa: E402

SECS = C.passed_sections()
MEDIA = {r["url"] for r in json.loads((ROOT / "data/media.json").read_text())["items"]}
URL = sorted(MEDIA)[0]
GOOD = "the deadline for filing a claim for judicial review"  # in Sec. 1110 of the passed text


def row(**kw):
    r = {"id": "t1", "media_url": URL, "speaker": "Someone", "quote": "a claim", "about": "Lawsuit deadlines",
         "review": [{"section": "1110", "text": GOOD}]}
    r.update(kw)
    return r


class Resolve(unittest.TestCase):
    def test_good_row_resolves_with_cite_label_and_link(self):
        errors = []
        out = C.resolve([row()], MEDIA, errors)
        self.assertEqual(errors, [])
        r = out[URL][0]["review"][0]
        self.assertEqual(r["n"], "1110")
        self.assertEqual(len(r["c"]), 4)
        self.assertTrue(r["at"].startswith("("), r["at"])
        self.assertTrue(r["href"].startswith("#/"), r["href"])
        self.assertTrue(r["pdf"].startswith("substitute.pdf#page="), r["pdf"])

    def test_passage_not_in_section_fails(self):
        errors = []
        C.resolve([row(review=[{"section": "1101", "text": GOOD}])], MEDIA, errors)
        self.assertTrue(any("not found in section 1101" in e for e in errors), errors)

    def test_ambiguous_passage_fails(self):
        errors = []
        C.resolve([row(review=[{"section": "1110", "text": "judicial review"}])], MEDIA, errors)
        self.assertTrue(any("more than once" in e for e in errors), errors)

    def test_unknown_section_and_media_fail(self):
        errors = []
        C.resolve([row(media_url="https://example.invalid/x", review=[{"section": "9999", "text": GOOD}])], MEDIA, errors)
        self.assertTrue(any("not a coverage item" in e for e in errors), errors)
        self.assertTrue(any("9999 is not in the passed text" in e for e in errors), errors)

    def test_row_with_no_passage_fails(self):
        errors = []
        C.resolve([row(review=[])], MEDIA, errors)
        self.assertTrue(any("names no passage" in e for e in errors), errors)

    def test_committed_claims_resolve(self):
        doc = json.loads(C.CLAIMS.read_text())
        errors = []
        C.resolve(doc["claims"], MEDIA, errors)
        self.assertEqual(errors, [])
        for s in doc.get("skipped", []):
            self.assertTrue(s.get("why", "").strip(), s)


class Suggest(unittest.TestCase):
    def test_deterministic(self):
        q = "It caps lawsuits against permits at 150 days"
        self.assertEqual(C.suggest(q), C.suggest(q))

    def test_ranks_the_topic_section_first(self):
        self.assertEqual(C.suggest("lawsuits must be filed within 150 days of judicial review")[0]["section"], "1110")
        top = [s["section"] for s in C.suggest("ratepayers pay for interregional transmission cost allocation")]
        self.assertIn("2107", top)

    def test_named_section_wins(self):
        self.assertEqual(C.suggest("Section 2301 rewrites tribal consultation")[0]["section"], "2301")

    def test_candidate_passage_is_in_the_section(self):
        for s in C.suggest("data centers and the community assistance program"):
            if s["unique"]:
                loc = C.locate(SECS[s["section"]], s["text"])
                self.assertEqual(loc["count"], 1)


class Pending(unittest.TestCase):
    def test_pending_lists_only_integrated_unmapped_claims(self):
        doc = json.loads(C.CLAIMS.read_text())
        held = {(c["media_url"], claim_sections.norm(c["quote"])) for c in doc["claims"] + doc.get("skipped", [])}
        for p in claim_sections.pending():
            self.assertIn(p["media_url"], MEDIA)
            self.assertNotIn((p["media_url"], claim_sections.norm(p["quote"])), held)


if __name__ == "__main__":
    unittest.main()
