// Measures how far each reader question's answer is from the Overview at 375x812:
// taps from landing, and how far down the page the answer starts (in screen heights).
// Usage: node tools/reader_paths.cjs [base-url]   (serve site/ first; needs playwright on NODE_PATH)
const { chromium } = require('playwright');
const base = process.argv[2] || 'http://127.0.0.1:8766/';
const H = 812;

// Each path: id (matches docs/reader-questions.md), steps (each one tap), target (where the answer starts).
const fold = (name) => ({ summary: name });
const PATHS = [
  ['vote-date', [], '.next-step'],
  ['vote-status', [fold('Where it stands')], '#h-status'],
  ['who-for-against', [{ href: '#/positions' }], '#view h1'],
  ['why-split', [{ href: '#/positions' }], 'h2:text-is("By issue")'],
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
  ['tribes-dispute', [{ href: '#/positions' }], 'h2:text-is("Disputed readings")'],
  ['vs-current-law', [{ tab: 'bill' }, { href: '#/compare' }], '.view-compare .compare'],
  ['vs-earlier-bills', [fold('Changes from earlier bills')], 'h2:text-is("Changes from earlier bills")'],
  ['vs-speed-courts', [{ tab: 'bill' }, { href: '#/compare' }, { chipIn: '[data-comparison="main"]', name: 'SPEED Act' }], 'h2:text-is("Lawsuits")'],
  ['cost-allocation', [{ tab: 'bill' }, { href: '#/compare' }], 'h2:text-is("Transmission and the grid")'],
  ['dc-page', [{ tab: 'effects' }], '.cm-row'],
  ['counties', [{ tab: 'effects' }, { href: '#/communities' }], '.cm-row'],
  ['wind-solar', [fold('Where it stands')], '#h-status'],
  ['agency-deadlines', [fold('Deadlines')], '#h-clocks'],
  ['coverage', [{ tab: 'news' }], '.event'],
];

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 375, height: H } });
  const rows = [];
  for (const [id, steps, target] of PATHS) {
    await p.goto(base + '#/overview'); await p.reload(); await p.waitForSelector('.provisions li');
    for (const s of steps) {
      if (s.summary) await p.locator('summary', { hasText: s.summary }).first().click();
      else if (s.tab) await p.locator(`.tabs a[data-tab="${s.tab}"]`).click();
      else if (s.href) await p.locator(`#view a[href="${s.href}"]`).first().click();
      else if (s.chipIn) await p.locator(s.chipIn).getByRole('button', { name: s.name, exact: true }).click();
      await p.waitForTimeout(250);
    }
    const t = p.locator(target).first();
    await t.waitFor({ state: 'attached', timeout: 5000 });
    const y = await t.evaluate((e) => e.getBoundingClientRect().top + scrollY);
    rows.push({ id, taps: steps.length, screens: +(y / H).toFixed(2) });
  }
  console.log(JSON.stringify(rows));
  await b.close();
})();
