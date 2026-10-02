/* Real browser acceptance checks. Requires Playwright and a local server. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.UAT_BASE || 'http://127.0.0.1:8766/';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const results = [], errors = [];
  try {
    for (const width of [375, 768, 1280]) {
      const page = await browser.newPage({ viewport: { width, height: width === 375 ? 812 : 800 }, hasTouch: width === 375 });
      page.on('pageerror', e => errors.push(e.message));
      for (const theme of ['light', 'dark']) {
        await page.goto(base);
        await page.evaluate(t => {sessionStorage.setItem('pr-theme',t);document.documentElement.dataset.theme=t;},theme);
        const n = await page.evaluate(() => ({
          compare: window.PR_DATA.compare.groups.reduce((a, g) => a + g.rows.length, 0) + (window.PR_DATA.compare.bills ? window.PR_DATA.compare.bills.rows.length : 0),
          media: window.PR_DATA.media.length, timeline: window.PR_DATA.timeline.length }));
        const routes = [
          ['overview','.provisions li',10], ['bill','.index li',71],
          ['bill/sec/1106','.para',null], ['compare','.compare tbody tr:not(.row-note)',n.compare],
          ['timeline','.event',n.timeline], ['people','.person',null], ['media','.media-item',n.media], ['method','.versus dd',null]
        ];
        for (const [route, selector, expected] of routes) {
          await page.goto(base+'#/'+route);
          await page.waitForSelector(selector);
          await page.evaluate(() => document.fonts.ready);
          const count = await page.locator(selector).count();
          assert.ok(count > 0,route+' empty');
          if (expected) assert.equal(count,expected,route);
          if (route === 'overview') {
            assert.equal(await page.locator('.brand-name').innerText(), 'Permitting Reform');
            assert.ok(await page.locator('.brand-name').evaluate(el => el.getBoundingClientRect().height < parseFloat(getComputedStyle(el).lineHeight) * 1.5));
            if (width === 375) assert.ok((await page.locator('.provisions li').first().boundingBox()).y < 400, 'first provision appears early on mobile');
            await page.locator('.bill-details summary').click();
            assert.ok(await page.locator('.bill-details a[href="bill.pdf#page=1"]').isVisible());
            await page.locator('.bill-details summary').click();
          }
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),route+' overflows at '+width);
          assert.ok(!(await page.locator('#view').innerText()).includes('[object Object]'),route+' object rendered');
          results.push({width,theme,route,count});
          if (['overview','bill/sec/1106','compare'].includes(route))
            await page.screenshot({path:`uat-screenshots/${width}-${theme}-${route.replaceAll('/','-')}.png`,fullPage:false});
        }
      }
      // User paths: submit search, follow a passage, filters, theme, keyboard skip.
      await page.goto(base+'#/overview');
      await page.locator('#search-input').fill('travel more than 25 miles');
      await page.locator('.search button').click();
      await page.waitForSelector('.results mark');
      const passage = page.locator('.results a[href*="/54-"]').first();
      assert.ok(await passage.count(), 'search result links to page 54');
      await passage.click();
      await page.waitForSelector('.para.target');
      assert.ok((await page.locator('.para.target').innerText()).includes('25 miles'));
      await page.goto(base+'#/media');
      await page.locator('#media-filter').fill('zzzznoresult');
      assert.equal(await page.locator('.media-item').count(),0);
      await page.locator('#media-filter').fill('');
      assert.equal(await page.locator('.media-item').count(), await page.evaluate(()=>PR_DATA.media.length));
      await page.getByRole('group',{name:'Source type',exact:true}).getByRole('button').nth(1).click();
      assert.ok(await page.locator('.media-item').count() < await page.evaluate(()=>PR_DATA.media.length));
      await page.goto(base+'#/media');
      await page.getByRole('group',{name:'Source type',exact:true}).getByRole('button').first().click();
      await page.evaluate(()=>document.querySelectorAll('details.filter-wrap').forEach(d=>{d.open=true;}));
      await page.getByRole('group',{name:'Topic',exact:true}).getByRole('button',{name:/^Data centers/}).click();
      await page.getByRole('group',{name:'Position',exact:true}).getByRole('button',{name:'Mixed',exact:true}).click();
      assert.equal(await page.locator('.media-item').count(), await page.evaluate(()=>PR_DATA.media.filter(x=>x.stance==='mixed'&&x.topics.includes('data-centers')).length));
      await page.getByRole('group',{name:'Topic',exact:true}).getByRole('button',{name:'All topics'}).click();
      await page.getByRole('group',{name:'Position',exact:true}).getByRole('button',{name:'All positions'}).click();
      await page.goto(base+'#/people');
      await page.getByRole('button',{name:/Outside government/}).click();
      assert.equal(await page.locator('.person').count(), await page.evaluate(()=>PR_DATA.people.filter(x=>!x.inside_government).length));
      await page.goto(base+'#/timeline');
      await page.getByRole('button',{name:/Milestones/}).click();
      assert.equal(await page.locator('.event').count(), await page.evaluate(()=>PR_DATA.timeline.filter(x=>x.milestone).length));
      const before = await page.locator('html').getAttribute('data-theme');
      await page.locator('#theme-toggle').click();
      assert.notEqual(await page.locator('html').getAttribute('data-theme'),before);
      await page.goto(base);
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(()=>document.activeElement.className),'skip');
      await page.keyboard.press('Enter');
      assert.equal(await page.evaluate(()=>document.activeElement.id),'main');
      await page.close();
    }
    const race = await browser.newPage();
    await race.route('**/data/bill.js*', async route => {
      await new Promise(resolve => setTimeout(resolve, 250));
      await route.continue();
    });
    await race.goto(base+'#/bill/search/page%2054', {waitUntil:'domcontentloaded'});
    await race.locator('[data-tab="media"]').click();
    await race.waitForFunction(() => Boolean(window.PR_BILL));
    assert.ok(race.url().endsWith('#/media'), 'late search must not redirect away from the selected tab');
    await race.close();
    assert.deepEqual(errors,[]);
    fs.mkdirSync('.test-artifacts',{recursive:true});
    fs.writeFileSync('.test-artifacts/uat.json',JSON.stringify({views:results,errors},null,2));
    console.log(`${results.length} rendered states; search, filters, citations, theme and keyboard checks passed at all three widths.`);
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
