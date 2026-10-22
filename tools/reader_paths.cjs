// Measures how far each reader question's answer is from the Overview at 375x812:
// taps from landing, and how far down the page the answer starts (in screen heights).
// Usage: node tools/reader_paths.cjs [base-url]   (serve site/ first; needs playwright on NODE_PATH)
const { chromium } = require('playwright');
const base = process.argv[2] || 'http://127.0.0.1:8766/';
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
  ['who-for-against', [{ href: '#/positions' }], '#view h1'],
  ['why-split', [{ href: '#/positions' }, row('.pos-issue')], '.pos-issue .pos-body'],
  ['what-it-does', [], '#h-prov'],
  ['nepa-deadlines', [fold('Review deadlines')], '.provision-detail[open] p'],
  ['lawsuits', [fold('Lawsuit limits')], '.provision-detail[open] p'],
  ['permit-certainty', [fold('Permit certainty')], '.provision-detail[open] p'],
  ['dc-costs', [fold('Data center costs')], '.provision-detail[open] p'],
  ['transmission', [fold('Transmission siting')], '.provision-detail[open] p'],
  ['exclusions', [fold('Actions outside NEPA')], '.provision-detail[open] p'],
  ['cwa', [fold('Clean Water Act')], '.provision-detail[open] p'],
  ['esa', [fold('Endangered Species Act')], '.provision-detail[open] p'],
  ['tribes-106', [fold('Historic preservation')], '.provision-detail[open] p'],
  ['tribes-dispute', [{ href: '#/positions' }, row('#dispute-tribal-consult')], '#dispute-tribal-consult .pos-body'],
  ['vs-current-law', [{ tab: 'bill' }, { href: '#/compare' }, { row: 'row-deadlines' }], '#row-deadlines .col-current'],
  ['vs-earlier-bills', [fold('Changes from earlier bills')], 'details[data-fold="overview:Changes from earlier bills"][open] > section'],
  ['vs-speed-courts', [{ tab: 'bill' }, { href: '#/compare' }, { chipIn: '[data-comparison="main"]', name: 'SPEED Act' }, { row: 'row-sol' }], '#row-sol .col-speed'],
  ['cost-allocation', [{ tab: 'bill' }, { href: '#/compare' }, { row: 'row-cost' }], '#row-cost .col-senate'],
  ['dc-page', [{ tab: 'effects' }, row('.cm-row')], '.cm-row .cm-body'],
  ['counties', [{ tab: 'effects' }, { href: '#/communities' }, row('.cm-row')], '.cm-row .cm-body'],
  ['wind-solar', [fold('Where it stands|Status')], open('#h-status')],
  ['agency-deadlines', [fold('Deadlines')], open('#h-clocks')],
  ['coverage', [{ tab: 'news' }], '.event'], // the headlines are the answer
];

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 375, height: H } });
  const rows = [];
  for (const [id, steps, target] of PATHS) {
    await p.goto(base + '#/overview'); await p.reload(); await p.waitForSelector('.provisions li');
    for (const s of steps) {
      if (s.summary) await p.locator('summary').filter({ hasText: new RegExp(`^\\s*(${s.summary})\\s*$`) }).click();
      else if (s.row) await p.locator(`#${s.row} .row-toggle`).click();
      else if (s.toggle) await p.locator(`${s.toggle} .event-toggle`).first().click();
      else if (s.tab) await p.locator(`.tabs a[data-tab="${s.tab}"]`).click();
      else if (s.href) await p.locator(`#view a[href="${s.href}"]`).first().click();
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
})();
