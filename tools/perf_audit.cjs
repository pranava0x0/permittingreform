/* Cold-load cost of each page at 375x812, the way a phone on a slow link pays it.

   Usage: NODE_PATH=<dir with playwright> node tools/perf_audit.cjs [--json out.json] [--fast]

   Serves site/ itself with gzip (python's http.server sends raw bytes, GitHub Pages does not),
   so the transfer column is close to what the deployed host sends. For every route, in a fresh
   browser context:
     requests     network requests until the page is idle
     transfer     bytes on the wire for those requests (gzip for text)
     dupes        URLs fetched more than once
     ready        ms from navigation until the page's own content is on screen, no throttling
     slow4g       the same with Slow 4G (150 ms round trip, 1.6 Mbps down) and a 4x slower CPU
     screens      page height in screen heights
   --fast skips the throttled pass. Exits 1 if a route never shows its content or fetches a URL twice. */
const http = require('http');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { chromium } = require('playwright');

const SITE = path.join(__dirname, '..', 'site');
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.txt': 'text/plain; charset=utf-8', '.md': 'text/markdown; charset=utf-8',
  '.xml': 'application/xml', '.woff2': 'font/woff2', '.pdf': 'application/pdf', '.png': 'image/png', '.webmanifest': 'application/manifest+json' };
const GZIP = new Set(['.html', '.js', '.css', '.json', '.svg', '.txt', '.md', '.xml', '.webmanifest']);

function serve() {
  const server = http.createServer((req, res) => {
    let rel = decodeURIComponent(req.url.split('?')[0]);
    if (rel.endsWith('/')) rel += 'index.html';
    const file = path.join(SITE, rel);
    if (!file.startsWith(SITE) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end('not found'); return; }
    const ext = path.extname(file);
    let body = fs.readFileSync(file);
    const head = { 'Content-Type': TYPES[ext] || 'application/octet-stream', 'Cache-Control': 'max-age=600' };
    if (GZIP.has(ext) && /gzip/.test(req.headers['accept-encoding'] || '')) { body = zlib.gzipSync(body); head['Content-Encoding'] = 'gzip'; }
    head['Content-Length'] = body.length;
    res.writeHead(200, head); res.end(body);
  });
  return new Promise((ok) => server.listen(0, '127.0.0.1', () => ok(server)));
}

/* route, selector that only exists once that page's own content has rendered */
const ROUTES = [
  ['overview', '#/overview', '.provisions li'],
  ['bill index', '#/bill', '.view-bill h1'],
  ['section 1101', '#/bill/sec/1101', '.view-bill .sec-meta, .view-bill .sec-links'],
  ['compare', '#/compare', '.view-compare h1'],
  ['amendments', '#/amendments', '.view-amendments h1'],
  ['positions', '#/positions', '.view-positions h1'],
  ['people', '#/people', '.view-people h1'],
  ['data centers', '#/datacenters', '.view-datacenters h1'],
  ['communities', '#/communities', '.view-communities h1'],
  ['speed', '#/speed', '.view-speed h1'],
  ['timeline', '#/timeline', '.view-timeline h1'],
  ['coverage', '#/media', '.view-media h1'],
  ['method', '#/method', '.view-method h1'],
];

async function measure(browser, base, hash, sel, throttle) {
  const ctx = await browser.newContext({ viewport: { width: 375, height: 812 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  let bytes = 0; let requests = 0; const seen = {};
  cdp.on('Network.requestWillBeSent', (e) => { if (/^http/.test(e.request.url)) { requests += 1; seen[e.request.url] = (seen[e.request.url] || 0) + 1; } });
  cdp.on('Network.loadingFinished', (e) => { bytes += e.encodedDataLength; });
  if (throttle) {
    await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: 1.6 * 1024 * 1024 / 8, uploadThroughput: 750 * 1024 / 8 });
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  }
  const t0 = Date.now();
  let ready = null;
  await page.goto(base + hash, { waitUntil: 'commit' });
  try { await page.locator(sel).first().waitFor({ state: 'visible', timeout: 60000 }); ready = Date.now() - t0; } catch (e) { ready = null; }
  await page.waitForLoadState('networkidle').catch(() => {});
  const screens = await page.evaluate(() => document.documentElement.scrollHeight / 812);
  const vitals = await page.evaluate(() => new Promise((ok) => {
    const out = { fcp: null, lcp: null, cls: 0 };
    const p = performance.getEntriesByName('first-contentful-paint')[0];
    if (p) out.fcp = Math.round(p.startTime);
    try {
      new PerformanceObserver((l) => { const e = l.getEntries(); if (e.length) out.lcp = Math.round(e[e.length - 1].startTime); }).observe({ type: 'largest-contentful-paint', buffered: true });
      new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) out.cls += e.value; }).observe({ type: 'layout-shift', buffered: true });
    } catch (e) { /* older engine */ }
    setTimeout(() => ok(out), 300);
  }));
  await ctx.close();
  const dupes = Object.keys(seen).filter((u) => seen[u] > 1).map((u) => u.replace(base, ''));
  return { requests, bytes, ready, screens: Math.round(screens * 10) / 10, dupes, fcp: vitals.fcp, lcp: vitals.lcp, cls: Math.round(vitals.cls * 1000) / 1000 };
}

(async () => {
  const args = process.argv.slice(2);
  const fast = args.includes('--fast');
  const jsonAt = args.indexOf('--json');
  const server = await serve();
  const base = `http://127.0.0.1:${server.address().port}/`;
  const browser = await chromium.launch({ channel: 'chrome' });
  const rows = []; let bad = 0;
  for (const [name, hash, sel] of ROUTES) {
    const cold = await measure(browser, base, hash, sel, false);
    const slow = fast ? null : await measure(browser, base, hash, sel, true);
    if (cold.ready === null || cold.dupes.length) bad += 1;
    rows.push({ name, hash, ...cold, slow_ready: slow && slow.ready, slow_fcp: slow && slow.fcp, slow_lcp: slow && slow.lcp });
  }
  await browser.close(); server.close();
  const kb = (n) => (n / 1024).toFixed(0).padStart(5);
  console.log('page            requests  transfer KB  ready ms  slow4G ready ms  slow4G LCP ms    CLS  screens  dupes');
  for (const r of rows) {
    console.log(`${r.name.padEnd(15)} ${String(r.requests).padStart(8)}  ${kb(r.bytes).padStart(11)}  ${String(r.ready).padStart(8)}  ${String(r.slow_ready).padStart(15)}  ${String(r.slow_lcp).padStart(13)}  ${String(r.cls).padStart(5)}  ${String(r.screens).padStart(7)}  ${r.dupes.join(',') || '-'}`);
  }
  if (jsonAt >= 0) fs.writeFileSync(args[jsonAt + 1], JSON.stringify({ measured: new Date().toISOString(), viewport: '375x812', rows }, null, 1) + '\n');
  process.exit(bad ? 1 : 0);
})();
