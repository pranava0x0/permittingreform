/* Opens each URL in Chrome and prints what a reader would see, one JSON line per page.

   Usage: NODE_PATH=<dir with playwright> node tools/browser_text.cjs [--headed] < urls.txt
   Output per URL: {"url", "status", "title", "text"} or {"url", "error"}.

   tools/browser_quotes.py drives this. It does nothing to get past a sign-in, a paywall or a
   "verify you are human" page: such a page comes back as whatever text it showed. */
const { chromium } = require('playwright');

(async () => {
  const urls = require('fs').readFileSync(0, 'utf8').split('\n').map((s) => s.trim()).filter(Boolean);
  const browser = await chromium.launch({ channel: 'chrome', headless: !process.argv.includes('--headed') });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  for (const url of urls) {
    const page = await ctx.newPage();
    let row;
    try {
      const res = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});
      row = { url, status: res ? res.status() : null, title: await page.title(), text: await page.evaluate(() => document.body.innerText) };
    } catch (e) {
      row = { url, error: String(e.message || e).split('\n')[0] };
    }
    console.log(JSON.stringify(row));
    await page.close().catch(() => {});
  }
  await browser.close();
})();
