"""The static site's contract: tokens, contrast, assets, and no unsafe HTML sinks."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402

CSS = (ROOT / "site/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "site/index.html").read_text(encoding="utf-8")
JS = (ROOT / "site/app.js").read_text(encoding="utf-8")
HEX = re.compile(r"#[0-9A-Fa-f]{3,8}\b")


def block(selector: str) -> str:
    start = CSS.index(selector + " {")
    return CSS[start:CSS.index("}", start)]


def tokens(selector: str) -> dict:
    return {m.group(1): m.group(2) for m in re.finditer(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})\s*;", block(selector))}


def luminance(hex_color: str) -> float:
    chans = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in chans]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg: str, bg: str) -> float:
    a, b = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


# Every text-on-background pair the stylesheet renders.
PAIRS = [
    ("text", "bg"), ("text-muted", "bg"), ("accent", "bg"),
    ("text", "surface"), ("text-muted", "surface"), ("accent", "surface"),
    ("text", "accent-weak"), ("text-muted", "accent-weak"), ("accent", "accent-weak"),
    ("bg", "rule"), ("on-brand", "brand"), ("on-brand-muted", "brand"), ("on-mark", "mark"),
    ("stance-supports", "bg"), ("stance-opposes", "bg"), ("stance-mixed", "bg"), ("stance-neutral", "bg"),
    ("stance-supports", "surface"), ("stance-opposes", "surface"), ("stance-mixed", "surface"),
    ("stance-neutral", "surface"),
]
# Rules, focus rings and the current-tab underline: WCAG 1.4.11 asks 3:1 for these.
NON_TEXT = [("rule", "bg"), ("rule", "surface"), ("rule", "accent-weak"), ("mark", "brand"), ("on-brand-muted", "brand")]


class Tokens(unittest.TestCase):
    def test_both_themes_define_the_same_color_tokens(self):
        light, dark = tokens(":root"), tokens('[data-theme="dark"]')
        self.assertEqual(set(light), set(dark))
        self.assertGreaterEqual(len(light), 14)

    def test_every_rendered_pair_meets_wcag_aa_in_both_themes(self):
        for name, theme in (("light", tokens(":root")), ("dark", tokens('[data-theme="dark"]'))):
            for fg, bg in PAIRS:
                ratio = contrast(theme[fg], theme[bg])
                self.assertGreaterEqual(ratio, 4.5, f"{name}: --{fg} on --{bg} is {ratio:.2f}:1")

    def test_rules_and_focus_marks_meet_three_to_one_in_both_themes(self):
        for name, theme in (("light", tokens(":root")), ("dark", tokens('[data-theme="dark"]'))):
            for fg, bg in NON_TEXT:
                ratio = contrast(theme[fg], theme[bg])
                self.assertGreaterEqual(ratio, 3.0, f"{name}: --{fg} on --{bg} is {ratio:.2f}:1")

    def test_dark_secondary_text_and_controls_have_clear_contrast(self):
        dark = tokens('[data-theme="dark"]')
        for bg in ("bg", "surface", "accent-weak"):
            self.assertGreaterEqual(contrast(dark["text-muted"], dark[bg]), 7)
        self.assertGreaterEqual(contrast(dark["border"], dark["surface"]), 3)

    def test_every_color_token_is_used(self):
        for name in tokens(":root"):
            self.assertIn(f"var(--{name})", CSS, name)

    def test_the_contrast_function_knows_black_on_white(self):
        self.assertAlmostEqual(contrast("#000000", "#FFFFFF"), 21.0, places=1)
        self.assertLess(contrast("#777777", "#888888"), 1.5)

    def test_no_color_is_named_outside_the_token_blocks(self):
        rest = CSS.replace(block(":root"), "").replace(block('[data-theme="dark"]'), "")
        self.assertEqual(HEX.findall(rest), [])
        self.assertNotRegex(rest, r"\brgba?\(|\bhsla?\(")

    def test_every_custom_property_in_use_is_defined(self):
        defined = set(re.findall(r"--([a-z0-9-]+)\s*:", block(":root")))
        used = set(re.findall(r"var\(--([a-z0-9-]+)\)", CSS))
        self.assertEqual(used - defined, set())


class Page(unittest.TestCase):
    def test_local_assets_exist(self):
        refs = re.findall(r'(?:src|href)="([^"#]+?)(?:\?v=\d+)?"', HTML)
        local = [r for r in refs if not r.startswith(("http", "#"))]
        self.assertIn("styles.css", local)
        for ref in local:
            self.assertTrue((ROOT / "site" / ref).exists(), ref)

    def test_nothing_loads_from_another_origin(self):
        self.assertEqual(re.findall(r'<(?:script|link|img)[^>]+(?:src|href)="https?://[^"]+"[^>]*(?:rel="stylesheet"|\.js|\.css)', HTML), [])
        self.assertNotIn("fonts.googleapis", HTML + CSS)
        self.assertNotIn("@import", CSS)

    def test_canonical_url_matches_the_build_setting(self):
        self.assertIn(f'<link rel="canonical" href="{build.SITE_URL}">', HTML)

    def test_data_never_reaches_an_html_sink(self):
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
            self.assertNotIn(sink, JS, sink)

    def test_outbound_links_are_restricted_to_http(self):
        self.assertIn(r"/^https?:\/\//i.test", JS)

    def test_interface_text_has_no_em_dash(self):
        self.assertNotIn("—", JS)
        self.assertNotIn("—", HTML)

    def test_the_json_ld_date_follows_the_data(self):
        # It sat at 2026-10-02 after an Oct 20 data refresh (Codex, PR 8); build.py now writes it.
        self.assertIn('"dateModified":"' + build.DATA_AS_OF + '"', HTML)

    def test_a_failed_readings_or_news_load_names_that_resource(self):
        # The bill-text failure message once covered every lazy load, so a takes.js failure on the
        # Positions page said "The bill text did not load" and offered the PDF (Codex, PR 8).
        self.assertIn('failure(err, "The outside readings")', JS)
        self.assertIn('failure(err, "The timeline, people and media")', JS)
        self.assertNotIn("fill(host, failure(err)));\n    return el(\"section\", { class: \"block\", \"aria-labelledby\": \"h-disputes\" }", JS)

    def test_a_concerned_reading_is_not_counted_as_opposition(self):
        # NRDC's "concerns" take sat in "Opponents read it as" and counted as "against" (Codex, PR 8).
        self.assertIn('"Opponents and critics read it as"', JS)
        self.assertIn('x === "concerns"', JS)
        self.assertIn('el("span", { class: "stance stance-" + t.stance }, T.stances[t.stance])', JS)

    def test_the_positions_page_leads_with_disputed_readings(self):
        self.assertIn("disputesBlock(),\n      el(\"section\", { class: \"block\", \"aria-labelledby\": \"h-letters\" },", JS)
        self.assertIn('"No reading on this side found yet."', JS)

    def test_the_positions_page_is_routed_in_the_news_group(self):
        self.assertIn('const NEWS_TABS = ["timeline", "positions", "people", "media"];', JS)
        self.assertIn('[["timeline", "Timeline"], ["positions", "Positions"], ["media", "Media"], ["people", "People"]]', JS)
        self.assertIn('positions: "Positions"', JS)
        self.assertIn('else if (tab === "positions") nodes = renderPositions();', JS)
        self.assertIn('href: "#/positions"', JS)

    def test_the_sector_table_links_to_people_routes_the_router_reads(self):
        self.assertIn('"#/people/" + (rows[k].inside ? "inside" : "outside") + "/" + c[0] + "/" + k', JS)
        self.assertIn('pplSide = parts[1] === "outside" ? "outside" : "inside";', JS)
        self.assertIn('pplSector = SECTORS[parts[3]] ? parts[3] : "all";', JS)
        self.assertIn('(pplSector === "all" || sectorKey(p) === pplSector)', JS)

    def test_letters_and_stance_chips_follow_their_filters(self):
        self.assertIn('it.letter && it.date >= D.meta.released', JS)
        self.assertIn('pool.filter((p) => pplSector === "all" || sectorKey(p) === pplSector)', JS)
        self.assertIn('l.at_least ? num(l.signer_count) + "+ signers"', JS)

    def test_issue_voices_start_at_the_bill_release(self):
        """A statement about an earlier bill shares topics with the current one; the Positions page must not count it."""
        self.assertIn('it.date >= D.meta.released && POSITION_SIDES.some', JS)

    def test_the_bill_text_loader_caches_its_promise(self):
        self.assertIn("if (!billPromise)", JS)


if __name__ == "__main__":
    unittest.main()
