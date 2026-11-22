// Measures how far each reader question's answer is from the Overview at 375x812:
// taps from landing, and how far down the page the answer starts (in screen heights).
// Usage: node tools/reader_paths.cjs [base-url] [--write]   (serve site/ first; needs playwright on NODE_PATH)
//
// Gate: tests/reader_paths.json holds each path's taps and screens. A path that takes more taps
// than its baseline, starts more than SLACK screens lower, or disappears fails the run (exit 1),
// so a refresh cannot quietly make an answer harder to reach. --write records the current
// numbers as the new baseline: do that only when a path got shorter, or with a dated reason in
// the commit when a design change makes one longer on purpose.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const args = process.argv.slice(2);
const WRITE = args.includes('--write');
const base = args.find((a) => !a.startsWith('--')) || 'http://127.0.0.1:8766/';
const BASELINE = path.join(__dirname, '..', 'tests', 'reader_paths.json');
const SLACK = 0.25;
const H = 812;

// Each path: id (matches docs/reader-questions.md), steps (each one tap), target (where the answer starts).
// A target must be visible, not just attached: a heading in a closed fold or a cell in a
// closed comparison row is not an answer yet. Fold labels match exactly ("Deadlines" must
// not open "Review deadlines"); a "|" lists labels the same fold has had.
const fold = (name) => ({ summary: name });
const open = (sel) => `details[open]:has(> summary ${sel}) > section`;
// A collapsed row (Positions, Data centers, Communities) is one more tap; the answer is its body.
const row = (sel) => ({ toggle: sel });
const PATHS = [
  ['vote-date', [], '.next-step'],
  ['vote-status', [fold('Where it stands|Status')], open('#h-status')],
  // The heading and the tally line only count; the newest letter names its signers and their stance.
  ['who-for-against', [{ href: '#/positions' }, row('.pos-letter')], '.pos-letter.open .pos-body'],
  ['why-split', [{ href: '#/positions' }, row('.pos-issue')], '.pos-issue .pos-body'],
  ['what-it-does', [], '#h-prov'],
  ['nepa-deadlines', [fold('Review deadlines')], '.provision-detail[open] p'],
  ['lawsuits', [fold('Court challenges')], '.provision-detail[open] p'],
  ['permit-certainty', [fold('Issued permits')], '.provision-detail[open] p'],
  ['dc-costs', [fold('Data center costs')], '.provision-detail[open] p'],
  ['transmission', [fold('Transmission siting')], '.provision-detail[open] p'],
  ['exclusions', [fold('Actions outside NEPA')], '.provision-detail[open] p'],
  ['cwa', [fold('Clean Water Act')], '.provision-detail[open] p'],
  ['esa', [fold('Endangered Species Act')], '.provision-detail[open] p'],
  ['tribes-106', [fold('Historic preservation and tribal consultation')], '.provision-detail[open] p'],
  ['tribes-dispute', [{ href: '#/positions' }, row('#disputes-tribal'), row('#dispute-tribal-consult')], '#dispute-tribal-consult .pos-body'],
  ['vs-current-law', [{ tab: 'bill' }, { href: '#/compare' }, { row: 'row-deadlines' }], '#row-deadlines .col-current'],
  ['vs-earlier-bills', [fold('Changes from earlier bills')], 'details[data-fold="overview:Changes from earlier bills"][open] > section'],
  ['vs-speed-courts', [{ tab: 'bill' }, { href: '#/compare' }, { chipIn: '[data-comparison="main"]', name: 'SPEED Act' }, { row: 'row-sol' }], '#row-sol .col-speed'],
  ['cost-allocation', [{ tab: 'bill' }, { href: '#/compare' }, { row: 'row-cost' }], '#row-cost .col-senate'],
  ['dc-page', [{ tab: 'issues' }, row('.cm-row')], '.cm-row .cm-body'],
  ['counties', [{ tab: 'issues' }, { href: '#/communities' }, { href: '#/communities/courts' }, row('.cm-row')], '.cm-row .cm-body'],
  ['wind-solar', [fold('Where it stands|Status')], open('#h-status')],
  ['agency-deadlines', [fold('Deadlines')], open('#h-clocks')],
  // Amendments: the key changes, one section's change, reactions to the substitute, and the substitute beside other bills.
  ['amend-key-changes', [{ href: '#/amendments' }], '.am-keys li'],
  ['amend-section', [{ href: '#/amendments' }, { sel: 'a.am-key[href="#/amendments/sec/1401"]' }], '#h-am-what'],
  ['amend-reactions', [{ href: '#/amendments/reactions' }, fold('Oppose\\d+')], '.am-stance[open] .am-reaction'],
  ['bill-positions', [{ href: '#/positions' }], '.pos-letter'],
  // Votes and estimates: one tap from the Overview card to the section, one more to open a row.
  ['senate-votes', [{ href: '#/votes' }], '.pos-vote'],
  ['how-each-senator-voted', [{ href: '#/votes' }, row('.pos-vote')], '.pos-vote.open .vote-names'],
  ['stated-vs-vote', [{ href: '#/votes' }, row('#votes-stated')], '#votes-stated .vote-stated'],
  ['estimates-emissions', [{ href: '#/positions/estimates' }, row('#estimates-emissions')], '#estimates-emissions .estimate'],
  ['estimates-prices', [{ href: '#/positions/estimates' }, row('#estimates-electricity_cost')], '#estimates-electricity_cost .estimate'],
  ['estimates-time', [{ href: '#/positions/estimates' }, row('#estimates-time')], '#estimates-time .estimate'],
  ['amend-vs-bills', [{ href: '#/compare' }, { row: 'row-cost' }], '#row-cost .sub-note'],
  ['coverage', [{ tab: 'media' }], '.media-item'],
  ['timeline', [{ tab: 'timeline' }], '.event'],
  // A claim in coverage and the passed-text passages to check it against (data/claims.json).
  ['claim-check', [{ tab: 'media' }, { sel: 'button.chip:has-text("Claims to check")' }], '.claims'],
  // Commentary and statements grouped by position on the bill, each row naming the sections it discusses (data/section_refs.json).
  ['commentary-opposes', [{ tab: 'media' }, { sel: 'button.chip:has-text("Commentary")' }, fold('Opposes the bill\\d+')], 'details.media-fold[open] .secs'],
];

(async () => {
  const b = await chromium.launch({channel:"chrome"});
  const p = await b.newPage({ viewport: { width: 375, height: H } });
  const rows = [];
  for (const [id, steps, target] of PATHS) {
    await p.goto(base + '#/overview'); await p.reload(); await p.waitForSelector('.provisions li');
    for (const s of steps) {
      if (s.summary) await p.locator('summary').filter({ hasText: new RegExp(`^\\s*(${s.summary})\\s*$`) }).click();
      else if (s.row) await p.locator(`#${s.row} .row-toggle`).click();
      else if (s.toggle) await p.locator(`${s.toggle} .event-toggle`).first().click();
      else if (s.tab) await p.locator(`.tabs a[data-tab="${s.tab}"]`).click();
      else if (s.href) await p.locator(`.subtabs:not([hidden]) a[href="${s.href}"], #view a[href="${s.href}"]`).first().click();
      else if (s.sel) await p.locator(s.sel).first().click();
      else if (s.jump) await p.locator('.jumps button').filter({ hasText: s.jump }).first().click();
      else if (s.chipIn) await p.locator(s.chipIn).getByRole('button', { name: s.name, exact: true }).click();
      await p.waitForTimeout(250);
    }
    const t = p.locator(target).first();
    await t.waitFor({ state: 'visible', timeout: 5000 });
    const y = await t.evaluate((e) => e.getBoundingClientRect().top + scrollY);
    rows.push({ id, taps: steps.length, screens: +(y / H).toFixed(2) });
  }
  console.log(JSON.stringify(rows));
  await b.close();
  if (WRITE) {
    fs.writeFileSync(BASELINE, JSON.stringify(Object.fromEntries(rows.map((r) => [r.id, { taps: r.taps, screens: r.screens }])), null, 1) + '\n');
    console.log('reader_paths: baseline written to tests/reader_paths.json');
    return;
  }
  if (!fs.existsSync(BASELINE)) { console.log('reader_paths: no baseline at tests/reader_paths.json; run with --write once'); process.exit(1); }
  const was = JSON.parse(fs.readFileSync(BASELINE, 'utf8'));
  const now = Object.fromEntries(rows.map((r) => [r.id, r]));
  const bad = [];
  for (const [id, w] of Object.entries(was)) {
    const n = now[id];
    if (!n) { bad.push(id + ': path missing'); continue; }
    if (n.taps > w.taps) bad.push(`${id}: ${n.taps} taps, baseline ${w.taps}`);
    if (n.screens > w.screens + SLACK) bad.push(`${id}: starts ${n.screens} screens down, baseline ${w.screens} (+${SLACK} allowed)`);
  }
  const fresh = rows.filter((r) => !was[r.id]).map((r) => r.id);
  const shorter = rows.filter((r) => was[r.id] && (r.taps < was[r.id].taps || r.screens < was[r.id].screens - SLACK)).map((r) => r.id);
  const taps = rows.reduce((a, r) => a + r.taps, 0);
  console.log(`reader_paths: ${rows.length} paths, ${taps} taps in all (baseline ${Object.values(was).reduce((a, w) => a + w.taps, 0)})` +
    (shorter.length ? `; shorter: ${shorter.join(', ')} (run with --write to lock in)` : '') +
    (fresh.length ? `; not in baseline: ${fresh.join(', ')} (run with --write)` : ''));
  for (const x of bad) console.log('  LONGER: ' + x);
  if (bad.length || fresh.length) process.exit(1);
})();
