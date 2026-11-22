"""Commentary and reports name the sections they discuss; the checks reject a bad pointer.

Each rule has a case that must pass and a case that must fail (CLAUDE.md: a
checker improved into silence passes everything)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import claims as C  # noqa: E402

MEDIA = {r["url"] for r in json.loads((ROOT / "data/media.json").read_text())["items"]}
URL = sorted(MEDIA)[0]
OTHER = sorted(MEDIA)[1]
Q = "the bill would cut the time to sue to 150 days"


def doc(sections=None, url=URL, none=None):
    return {"refs": [{"media_url": url, "sections": sections if sections is not None else [{"n": "1110", "quote": Q}]}],
            "none": none or []}


class ResolveRefs(unittest.TestCase):
    def test_good_ref_resolves_with_heading_link_and_quote(self):
        errors = []
        out = C.resolve_refs(doc(), MEDIA, errors)
        self.assertEqual(errors, [])
        x = out[URL][0]
        self.assertEqual((x["n"], x["h"], x["q"]), ("1110", "Judicial review", Q))
        self.assertTrue(x["href"].startswith("#/"), x["href"])

    def test_sections_sort_by_number(self):
        out = C.resolve_refs(doc([{"n": "2107", "quote": Q}, {"n": "1302", "quote": Q}]), MEDIA, [])
        self.assertEqual([x["n"] for x in out[URL]], ["1302", "2107"])

    def test_unknown_section_fails(self):
        errors = []
        C.resolve_refs(doc([{"n": "9999", "quote": Q}]), MEDIA, errors)
        self.assertTrue(any("9999 is not in the passed text" in e for e in errors), errors)

    def test_missing_quote_fails(self):
        errors = []
        C.resolve_refs(doc([{"n": "1110", "quote": "sue"}]), MEDIA, errors)
        self.assertTrue(any("own words" in e for e in errors), errors)

    def test_not_a_coverage_item_fails(self):
        errors = []
        C.resolve_refs(doc(url="https://example.invalid/x"), MEDIA, errors)
        self.assertTrue(any("not a coverage item" in e for e in errors), errors)

    def test_duplicate_section_and_empty_ref_fail(self):
        errors = []
        C.resolve_refs(doc([{"n": "1110", "quote": Q}, {"n": "1110", "quote": Q}]), MEDIA, errors)
        self.assertTrue(any("listed twice" in e for e in errors), errors)
        errors = []
        C.resolve_refs(doc([]), MEDIA, errors)
        self.assertTrue(any("names no section" in e for e in errors), errors)

    def test_none_needs_a_reason_and_cannot_repeat_a_ref(self):
        errors = []
        C.resolve_refs(doc(none=[{"media_url": OTHER, "why": "Discusses the bill as a whole."}]), MEDIA, errors)
        self.assertEqual(errors, [])
        errors = []
        C.resolve_refs(doc(none=[{"media_url": OTHER, "why": " "}, {"media_url": URL, "why": "x"}]), MEDIA, errors)
        self.assertTrue(any("without a reason" in e for e in errors), errors)
        self.assertTrue(any("listed twice across refs, none and unread" in e for e in errors), errors)


class Committed(unittest.TestCase):
    def test_committed_refs_resolve_clean(self):
        path = ROOT / "data/section_refs.json"
        if not path.exists():
            self.skipTest("no data/section_refs.json")
        errors = []
        C.resolve_refs(json.loads(path.read_text()), MEDIA, errors)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
