"""tools/refresh_status.py: a failed roll-call fetch stops the scan, and new floor-log lines count."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import refresh_status as R  # noqa: E402

VOTE = "<vote_result>Passed</vote_result><vote_date>x</vote_date><vote_question_text>On Passage</vote_question_text><yeas>1</yeas><nays>0</nays>"


def fake(pages):
    def f(url, timeout=30):
        return pages.get(url, (404, ""))
    return f


class Rolls(unittest.TestCase):
    def test_server_error_is_reported_and_stops_the_scan(self):
        pages = {R.SENATE_XML.format(n=280): (503, ""), R.SENATE_XML.format(n=281): (200, VOTE)}
        errors = []
        with patch.object(R, "fetch", fake(pages)):
            out = R.senate(279, errors)
        self.assertEqual(out, [])
        self.assertTrue(errors and "503" in errors[0], errors)

    def test_unpublished_rolls_are_not_errors(self):
        pages = {R.SENATE_XML.format(n=280): (200, VOTE), R.SENATE_XML.format(n=281): (200, "Roll Call Vote Unavailable")}
        errors = []
        with patch.object(R, "fetch", fake(pages)):
            out = R.senate(279, errors)
        self.assertEqual([r["number"] for r in out], [280])
        self.assertEqual(errors, [])

    def test_house_network_error_is_reported(self):
        errors = []
        with patch.object(R, "fetch", fake({R.HOUSE_XML.format(n=328): (0, "URLError: timed out")})):
            R.house(327, errors)
        self.assertTrue(errors, errors)


class FloorLog(unittest.TestCase):
    def run_main(self, lines, seen):
        state = {"senate_last": 279, "house_last": 327, "checked": "2026-11-21", "floor_log_seen": seen}
        tmp = Path(tempfile.mkdtemp()) / "floor_state.json"
        tmp.write_text(json.dumps(state))
        with patch.object(R, "senate", lambda a, e: []), patch.object(R, "house", lambda a, e: []), \
             patch.object(R, "record", lambda a, b, e: []), patch.object(R, "house_floor", lambda t, e: []), \
             patch.object(R, "floor_log", lambda e: {"url": "u", "lines": lines, "next": ""}), \
             patch.object(R, "STATE", tmp), patch.object(sys, "argv", ["x", "--today", "2026-11-21"]), \
             patch("builtins.print"):
            return R.main()

    def test_new_floor_log_line_touches_the_bill(self):
        self.assertEqual(self.run_main(["H.R. 2347 passed"], []), 10)

    def test_seen_floor_log_line_does_not(self):
        self.assertEqual(self.run_main(["H.R. 2347 passed"], ["H.R. 2347 passed"]), 0)


if __name__ == "__main__":
    unittest.main()
