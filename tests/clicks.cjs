/* Click crawler: loads every view (all 71 sections included) at phone and desktop widths,
   then clicks every control on the main views from a fresh load and times it.
   Fails on page errors, horizontal overflow, dead controls, or any load or click over 20s.
   Usage: NODE_PATH=<dir with playwright> UAT_BASE=http://127.0.0.1:8766/ node tests/clicks.cjs */
const { chromium } = require('playwright');
const fs = require('node:fs');
const base = process.env.UAT_BASE || 'http://127.0.0.1:8766/';
const RED_MS = 20000;   /* the hard limit: anything slower is a ship blocker */
const SLOW_MS = 1000;   /* reported, not failed */
const out = process.env.CLICKS_OUT || '.test-artifacts/clicks.json';

const WIDTHS = [{ w: 375, h: 812, touch: true }, { w: 1280, h: 800, touch: false }];
const CLICK_ROUTES = ['overview', 'bill', 'bill/sec/1106', 'bill/sec/2107', 'bill/search/transmission', 'compare',
  'compare/data-center-bills', 'communities', 'datacenters', 'timeline', 'people', 'media', 'method'];
const CONTROLS = '#view button, #view summary, #view select, #view a[href^="#"], .tabs a, #theme-toggle';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const report = { loads: [], clicks: [], problems: [], slow: [] };
  let n = 0;
  const problem = (p) => { report.problems.push(p); console.log('PROBLEM', JSON.stringify(p)); };

  for (const vp of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, hasTouch: vp.touch, isMobile: vp.touch });
    const page = await ctx.newPage();
    let errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

    const open = async (route) => {
      errors = [];
      const t0 = Date.now();
      await page.goto(base + '?n=' + (n++) + '#/' + route, { waitUntil: 'load', timeout: RED_MS + 5000 });
      await page.waitForFunction(() => {
        const v = document.getElementById('view');
        return v && v.children.length && !v.querySelector('.loading');
      }, null, { timeout: RED_MS });
      return Date.now() - t0;
    };
    const settle = () => page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
    const state = () => page.evaluate(() => ({
      hash: location.hash, html: document.getElementById('view').innerHTML.length + ':' + document.querySelectorAll('[open], .open, [aria-expanded="true"], [aria-pressed="true"]').length,
      theme: document.documentElement.dataset.theme || '', y: Math.round(scrollY),
      /* Clicking a control focuses it; focus on the page body or on the clicked control is not a change. */
      focus: (() => { const a = document.activeElement; return !a || a === document.body || a.dataset.crawled === '1' ? 'none' : a.outerHTML.slice(0, 80); })(),
      overflow: document.documentElement.scrollWidth > innerWidth + 1,
    }));

    /* 1. Every view, every section: load time, errors, overflow, length. */
    const sections = await (async () => { await open('overview'); return page.evaluate(() => PR_DATA.sections.map((s) => s.n)); })();
    const all = CLICK_ROUTES.concat(sections.map((s) => 'bill/sec/' + s)).filter((r, i, a) => a.indexOf(r) === i);
    for (const route of all) {
      const ms = await open(route);
      const s = await page.evaluate(() => ({ h: document.documentElement.scrollHeight, overflow: document.documentElement.scrollWidth > innerWidth + 1, text: document.getElementById('view').innerText }));
      const rec = { width: vp.w, route, ms, screens: +(s.h / vp.h).toFixed(1) };
      report.loads.push(rec);
      if (ms > RED_MS) problem({ ...rec, kind: 'load over 20s' });
      else if (ms > SLOW_MS) report.slow.push({ ...rec, kind: 'load' });
      if (errors.length) problem({ ...rec, kind: 'page error', errors });
      if (s.overflow) problem({ ...rec, kind: 'horizontal overflow' });
      if (/\[object Object\]|undefined|NaN/.test(s.text)) problem({ ...rec, kind: 'bad text', sample: (s.text.match(/.{0,40}(\[object Object\]|undefined|NaN).{0,40}/) || [])[0] });
      /* Scroll the whole page top to bottom; it must reach the footer without errors. */
      await page.evaluate(async () => { for (let y = 0; y < document.documentElement.scrollHeight; y += innerHeight * 0.9) { scrollTo(0, y); await new Promise((r) => requestAnimationFrame(r)); } });
      if (errors.length) problem({ ...rec, kind: 'error while scrolling', errors });
    }

    /* 2. Every control on the main views, each from a fresh load. */
    for (const route of CLICK_ROUTES) {
      await open(route);
      const total = await page.locator(CONTROLS).count();
      for (let i = 0; i < total; i++) {
        await open(route);
        const loc = page.locator(CONTROLS).nth(i);
        if (!(await loc.count())) continue;
        const info = await loc.evaluate((el) => ({ tag: el.tagName.toLowerCase(), label: (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60), disabled: el.disabled === true }));
        const rec = { width: vp.w, route, i, ...info };
        if (info.disabled) { report.clicks.push({ ...rec, result: 'disabled' }); continue; }
        /* A control inside a folded row or disclosure: open its parents the way a reader would first. */
        if (!(await loc.isVisible())) {
          await loc.evaluate((el) => {
            for (let n = el.parentElement; n; n = n.parentElement) {
              if (n.tagName === 'DETAILS') n.open = true;
              if (n.matches('.event, .cm-row, .person, .media-item, .compare tbody tr')) n.classList.add('open');
            }
          });
          if (!(await loc.isVisible())) { report.clicks.push({ ...rec, result: 'hidden' }); continue; }
          rec.revealed = true;
        }
        /* Symbols on the milestone line take pointer input through the line: tap the symbol itself. */
        const viaLine = await loc.evaluate((el) => getComputedStyle(el).pointerEvents === 'none');
        const markId = viaLine ? await loc.getAttribute('data-id') : null;
        await loc.scrollIntoViewIfNeeded();
        if (!viaLine) {
          try { await loc.click({ trial: true, timeout: 3000 }); }
          catch (e) { problem({ ...rec, kind: 'obscured: cannot be tapped', error: e.message.split('\n').find((l) => /intercepts|not visible|outside/.test(l)) || e.message.split('\n')[0] }); continue; }
        }
        /* A control that is already current (this tab, this section, the pressed filter) may rightly do nothing. */
        const current = await loc.evaluate((el) => el.matches('[aria-pressed="true"], [aria-current]:not([aria-current="false"])') ||
          (el.tagName === 'A' && el.getAttribute('href') === location.hash));
        await loc.evaluate((el) => { el.dataset.crawled = '1'; });
        const before = await state();
        errors = [];
        const t0 = Date.now();
        try {
          if (viaLine) {
            const box = await loc.locator('.tl-sym').boundingBox();
            await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
          } else if (info.tag === 'select') {
            const vals = await loc.evaluate((el) => Array.from(el.options).map((o) => o.value));
            await loc.selectOption(vals[vals.length - 1], { timeout: RED_MS });
          } else {
            await loc.click({ timeout: RED_MS });
          }
          await settle();
          await page.waitForFunction(() => !document.querySelector('#view .loading'), null, { timeout: RED_MS });
          if (viaLine && !(await page.evaluate((id) => location.hash.endsWith('/' + id), markId))) {
            problem({ ...rec, kind: 'tap on symbol opened another milestone', got: await page.evaluate(() => location.hash) });
          }
        } catch (e) {
          problem({ ...rec, kind: 'click failed', error: e.message.split('\n')[0] });
          continue;
        }
        const ms = Date.now() - t0;
        const after = await state();
        const changed = ['hash', 'html', 'theme', 'y', 'focus'].filter((k) => before[k] !== after[k]);
        const r = { ...rec, ms, changed: changed.join(',') };
        report.clicks.push(r);
        if (ms > RED_MS) problem({ ...r, kind: 'click over 20s' });
        else if (ms > SLOW_MS) report.slow.push({ ...r, kind: 'click' });
        if (errors.length) problem({ ...r, kind: 'page error after click', errors });
        if (after.overflow) problem({ ...r, kind: 'overflow after click' });
        if (!changed.length && current) r.result = 'current: no-op by design';
        else if (!changed.length) problem({ ...r, kind: 'dead click' });
      }
    }

    /* 3. Load-more lists: count taps to reach the last entry. */
    for (const route of ['timeline', 'people', 'media']) {
      await open(route);
      let taps = 0;
      const t0 = Date.now();
      while (await page.locator('.show-rest').count()) { await page.locator('.show-rest').click(); await settle(); taps++; if (taps > 50) break; }
      report.loads.push({ width: vp.w, route: route + ' (all loaded)', ms: Date.now() - t0, taps, screens: +((await page.evaluate(() => document.documentElement.scrollHeight)) / vp.h).toFixed(1) });
      if (errors.length) problem({ width: vp.w, route, kind: 'error loading more', errors });
    }
    await ctx.close();
  }
  await browser.close();
  fs.mkdirSync('.test-artifacts', { recursive: true });
  fs.writeFileSync(out, JSON.stringify(report, null, 1));
  const clicked = report.clicks.filter((c) => c.ms != null);
  const max = (xs) => xs.reduce((m, x) => (x.ms > m.ms ? x : m), { ms: 0 });
  console.log(`views loaded: ${report.loads.length}; controls clicked: ${clicked.length} (hidden ${report.clicks.filter((c) => c.result === 'hidden').length}, disabled ${report.clicks.filter((c) => c.result === 'disabled').length})`);
  console.log('slowest load:', JSON.stringify(max(report.loads)));
  console.log('slowest click:', JSON.stringify(max(clicked)));
  console.log(`over ${SLOW_MS}ms: ${report.slow.length}; problems: ${report.problems.length}`);
  process.exit(report.problems.length ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
