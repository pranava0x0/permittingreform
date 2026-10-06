/* Real browser acceptance checks. Requires Playwright and a local server. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.UAT_BASE || 'http://127.0.0.1:8766/';
(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const results = [], errors = [];
  fs.mkdirSync("uat-screenshots", {recursive:true});
  try {
    for (const width of [375, 768, 1280]) {
      const page = await browser.newPage({ viewport: { width, height: width === 375 ? 812 : 800 }, hasTouch: width === 375 });
      page.on('pageerror', e => errors.push(e.message));
      for (const theme of ['light', 'dark']) {
        await page.goto(base);
        await page.evaluate(t => {sessionStorage.setItem('pr-theme',t);document.documentElement.dataset.theme=t;},theme);
        // Timeline, people and media load with the News pages; load them once so counts can be read.
        await page.goto(base+'#/timeline');
        await page.waitForFunction(() => Boolean(window.PR_DATA.timeline));
        const n = await page.evaluate(() => ({
          compare: window.PR_DATA.compare.groups.reduce((a, g) => a + g.rows.length, 0) + (window.PR_DATA.compare.bills ? window.PR_DATA.compare.bills.rows.length : 0),
          media: Math.min(12,window.PR_DATA.media.length), timeline: Math.min(12,window.PR_DATA.timeline.length),
          communities: window.PR_DATA.communities.rows.length, bills: window.PR_DATA.compare.bills.rows.length,
          datacenters: window.PR_DATA.datacenters.rows.length,
          people: Math.min(12,window.PR_DATA.people.filter(p=>p.inside_government).length) }));
        const routes = [
          ['overview','.provisions li',10], ['bill','.index li',71],
          ['bill/sec/1106','.para',null], ['compare','.compare tbody tr:not(.row-note)',n.compare],
          ['communities','.cm-row',n.communities], ['datacenters','.cm-row',n.datacenters], ['compare/data-center-bills','.compare tbody tr',n.bills],
          ['timeline','.event',n.timeline], ['people','.person',n.people], ['media','.media-item',n.media], ['method','.versus dd',null]
        ];
        for (const [route, selector, expected] of routes) {
          await page.goto(base+'#/'+route);
          await page.waitForSelector(selector,{state:'attached'});
          await page.evaluate(() => document.fonts.ready);
          const count = await page.locator(selector).count();
          assert.ok(count > 0,route+' empty');
          if (expected) assert.equal(count,expected,route);
          if (route === 'overview') {
            assert.equal(await page.locator('.brand-name').innerText(), 'Permitting Reform');
            assert.ok(await page.locator('.brand-name').evaluate(el => el.getBoundingClientRect().height < parseFloat(getComputedStyle(el).lineHeight) * 1.5));
            if (width === 375) assert.ok((await page.locator('.provisions li').first().boundingBox()).y < page.viewportSize().height / 2, 'first provision appears early on mobile: '+JSON.stringify(await page.locator('.provisions li').first().boundingBox()));
            await page.locator('.bill-details summary').click();
            assert.ok(await page.locator('.bill-details a[href="bill.pdf#page=1"]').isVisible());
            await page.locator('.bill-details summary').click();
            await page.locator('.provision-detail summary').first().click();
            assert.ok(await page.locator('.provision-detail .where a').first().isVisible());
            await page.locator('.provision-detail summary').first().click();
            assert.equal(await page.locator('a[href="#/compare/data-center-bills"]').count(),1);
          }
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),route+' overflows at '+width);
          assert.ok(!(await page.locator('#view').innerText()).includes('[object Object]'),route+' object rendered');
          const height = await page.evaluate(()=>document.documentElement.scrollHeight);
          const budget = {overview:2.5,bill:2.5,compare:4,'compare/data-center-bills':4,communities:5,datacenters:5,timeline:2,people:4.5,media:5};
          if (width < 1024 && budget[route]) assert.ok(height <= page.viewportSize().height * budget[route], route+' scroll budget at '+width+': '+height);
          results.push({width,theme,route,count,height});
          if (theme === 'light' && [375,1280].includes(width) && route === 'compare/data-center-bills')
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
      assert.equal(await page.locator('.media-item').count(), await page.evaluate(()=>Math.min(12,PR_DATA.media.length)));
      await page.getByRole('group',{name:'Source type',exact:true}).getByRole('button').nth(1).click();
      assert.ok(await page.locator('.media-item').count() < await page.evaluate(()=>PR_DATA.media.length));
      await page.goto(base+'#/media');
      await page.getByRole('group',{name:'Source type',exact:true}).getByRole('button').first().click();
      await page.evaluate(()=>document.querySelectorAll('details.filter-wrap').forEach(d=>{d.open=true;}));
      await page.getByRole('group',{name:'Topic',exact:true}).getByRole('button',{name:/^Data centers/}).click();
      await page.getByRole('group',{name:'Position',exact:true}).getByRole('button',{name:'Mixed',exact:true}).click();
      assert.equal(await page.locator('.media-item').count(), await page.evaluate(()=>Math.min(12,PR_DATA.media.filter(x=>x.stance==='mixed'&&x.topics.includes('data-centers')).length)));
      await page.getByRole('group',{name:'Topic',exact:true}).getByRole('button',{name:'All topics'}).click();
      await page.getByRole('group',{name:'Position',exact:true}).getByRole('button',{name:'All positions'}).click();
      await page.goto(base+'#/media');
      const mediaCount = await page.evaluate(()=>PR_DATA.media.length);
      await page.locator('.show-rest').click();
      assert.equal(await page.locator('.media-item').count(),Math.min(24,mediaCount));
      assert.equal(await page.evaluate(()=>document.activeElement.className),'media-item');
      while (await page.locator('.show-rest').count()) await page.locator('.show-rest').click();
      assert.equal(await page.locator('.media-item').count(),mediaCount);
      await page.locator('#media-filter').fill('zzzznoresult');
      await page.locator('#media-filter').fill('');
      assert.equal(await page.locator('.media-item').count(),Math.min(12,mediaCount));
      await page.goto(base+'#/communities');
      await page.getByRole('group',{name:'Who',exact:true}).getByRole('button',{name:/^States/}).click();
      assert.equal(await page.locator('.cm-row').count(),await page.evaluate(()=>PR_DATA.communities.rows.filter(r=>r.who.includes('states')).length));
      assert.ok(await page.locator('.cm-row').first().isVisible(), 'Communities rows are visible without opening a fold');
      await page.locator('.cm-row .event-toggle').first().click();
      assert.ok(await page.locator('.cm-row.open .cm-body').first().isVisible());
      assert.ok(await page.locator('.cm-row.open a[href*="bill.pdf#page="]').first().isVisible());
      await page.getByRole('group',{name:'Who',exact:true}).getByRole('button',{name:/^Everyone/}).click();
      // A filter that empties a whole group must still render (regression: null group passed to foldBlock).
      for (const who of await page.evaluate(()=>Object.keys(PR_DATA.communities.who))) {
        await page.goto(base+'#/communities');
        await page.getByRole('group',{name:'Who',exact:true}).getByRole('button',{name:new RegExp('^'+(await page.evaluate(w=>PR_DATA.communities.who[w],who)))}).click();
        const want=await page.evaluate(w=>PR_DATA.communities.rows.filter(r=>r.who.includes(w)).length,who);
        assert.equal(await page.locator('.cm-row').count(),want,'communities filter '+who);
      }
      await page.goto(base+'#/datacenters');
      await page.getByRole('group',{name:'Affected party',exact:true}).getByRole('button',{name:/^Data center operators/}).click();
      assert.equal(await page.locator('.cm-row').count(),await page.evaluate(()=>PR_DATA.datacenters.rows.filter(r=>r.who.includes('data_centers')).length));
      assert.ok(await page.locator('.cm-row').first().isVisible(), 'Datacenters rows are visible without opening a fold');
      await page.locator('.cm-row .event-toggle').first().click();
      assert.ok(await page.locator('.cm-row.open .cm-body').first().isVisible());
      assert.ok(await page.locator('.cm-row.open a[href*="bill.pdf#page="]').first().isVisible());
      await page.getByRole('group',{name:'Affected party',exact:true}).getByRole('button',{name:/^All entities/}).click();
      for (const who of await page.evaluate(()=>Object.keys(PR_DATA.datacenters.who))) {
        await page.goto(base+'#/datacenters');
        await page.getByRole('group',{name:'Affected party',exact:true}).getByRole('button',{name:new RegExp('^'+(await page.evaluate(w=>PR_DATA.datacenters.who[w],who)))}).click();
        const want=await page.evaluate(w=>PR_DATA.datacenters.rows.filter(r=>r.who.includes(w)).length,who);
        assert.equal(await page.locator('.cm-row').count(),want,'datacenters filter '+who);
      }
      await page.goto(base+'#/compare/data-center-bills');
      assert.equal(await page.locator('.compare tbody tr').count(), await page.evaluate(()=>PR_DATA.compare.bills.rows.length));
      // Tables stack below 1024px, so phones and tablets get tap-to-open rows and one counterpart.
      if (width < 1024) {
        const row = page.locator('#row-bills-existing');
        await row.locator('.row-toggle').click();
        assert.equal(await row.locator('td:visible').count(),2);
        await page.getByRole('group',{name:'Compare BAAJA with'}).getByRole('button',{name:'Current policy',exact:true}).click();
        assert.equal(await row.locator('.row-toggle').getAttribute('aria-expanded'),'true');
        assert.ok(await row.locator('.col-policy').isVisible());
        assert.equal(await row.locator('td:visible').count(),2);
        assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Current policy');
        await page.setViewportSize({width:1280,height:800});
        await page.waitForFunction(()=>Boolean(document.querySelector(".row-toggle")) === matchMedia("(max-width: 1023px)").matches);
        assert.equal(await row.locator('td:visible').count(),6);
        assert.ok(await page.locator('.versions').isVisible());
        await page.setViewportSize({width:375,height:812});
        await page.waitForFunction(()=>Boolean(document.querySelector(".row-toggle")) === matchMedia("(max-width: 1023px)").matches);
        assert.equal(await row.locator('td:visible').count(),2);
        await row.locator('.row-toggle').click();
        assert.equal(await row.locator('td:visible').count(),0);
        await row.locator('.row-toggle').focus(); await page.keyboard.press('Enter');
        assert.equal(await row.locator('td:visible').count(),2);
      } else {
        await page.setViewportSize({width:375,height:812});
        await page.waitForFunction(()=>Boolean(document.querySelector(".row-toggle")) === matchMedia("(max-width: 1023px)").matches);
        assert.equal(await page.locator('.row-toggle').count(), await page.evaluate(()=>PR_DATA.compare.bills.rows.length));
        await page.locator('.row-toggle').first().click();
        assert.equal(await page.locator('.compare tbody tr').first().locator('td:visible').count(),2);
        await page.setViewportSize({width,height:800});
        await page.waitForFunction(()=>Boolean(document.querySelector(".row-toggle")) === matchMedia("(max-width: 1023px)").matches);
        assert.equal(await page.locator('.compare tbody tr').first().locator('td:visible').count(),6);
      }
      await page.locator('.cell-source summary:visible').first().click();
      assert.ok(await page.locator('.cell-source[open] blockquote').first().isVisible());
      if (width < 1024) {
        await page.goto(base+'#/compare');
        await page.locator('.section-fold summary').first().click();
        const first = page.locator('.section-fold').first();
        await first.locator('.row-toggle').first().click();
        await page.locator('[data-comparison="main"]').getByRole('button',{name:'SPEED Act',exact:true}).click();
        assert.ok(await first.evaluate(d=>d.open));
        assert.ok(await first.locator('.compare tbody tr').first().locator('.col-speed').isVisible());
      }
      await page.goto(base+'#/people');
      await page.getByRole('button',{name:/Outside government/}).click();
      assert.equal(await page.locator('.person').count(), await page.evaluate(()=>Math.min(12,PR_DATA.people.filter(x=>!x.inside_government).length)));
      await page.locator('.show-rest').click();
      assert.equal(await page.locator('.person').count(),await page.evaluate(()=>Math.min(24,PR_DATA.people.filter(x=>!x.inside_government).length)));
      assert.ok((await page.evaluate(()=>document.activeElement.id)).startsWith('person-'));
      await page.goto(base+'#/timeline');
      await page.getByRole('button',{name:/Milestones/}).click();
      assert.equal(await page.locator('.event').count(), await page.evaluate(()=>Math.min(12,PR_DATA.timeline.filter(x=>x.milestone).length)));
      await page.getByRole('button',{name:/Milestones/}).click();
      await page.locator('.show-rest').click();
      assert.equal(await page.locator('.event').count(),24);
      // Milestone line: only milestones are marked; a mark opens its event in that month; arrows step; All events clears.
      await page.goto(base+'#/timeline');
      const ms = await page.evaluate(()=>PR_DATA.timeline.filter(e=>e.milestone).sort((a,b)=>a.date<b.date?-1:a.date>b.date?1:0).map(e=>({id:e.id,month:e.date.slice(0,7)})));
      assert.equal(await page.locator('.tl-mark').count(), ms.length);
      assert.ok(ms.length < await page.evaluate(()=>PR_DATA.timeline.length), 'the line marks some events, not all');
      const lastMs = ms[ms.length-1];
      // Every symbol, clustered or not, opens its own milestone when tapped anywhere it is drawn.
      for (const m of ms) {
        await page.locator('.tl-line').scrollIntoViewIfNeeded();
        const sym = await page.locator('.tl-mark[data-id="'+m.id+'"] .tl-sym').boundingBox();
        // Tap near the bottom edge of the drawn symbol: half of a bottom-row symbol hangs below the line.
        await page.mouse.click(sym.x+sym.width/2, sym.y+sym.height-1);
        await page.waitForSelector('.tl-mark.sel[data-id="'+m.id+'"]');
      }
      await page.getByRole('button',{name:'All events'}).click();
      await page.waitForSelector('.tl-mark.sel',{state:'detached'});
      await page.locator('.tl-line').scrollIntoViewIfNeeded();
      const lastSym = await page.locator('.tl-mark[data-id="'+lastMs.id+'"] .tl-sym').boundingBox();
      await page.mouse.click(lastSym.x+lastSym.width/2, lastSym.y+lastSym.height/2);
      await page.waitForURL(u=>u.hash==='#/timeline/'+lastMs.month+'/'+lastMs.id);
      await page.waitForSelector('#ev-'+lastMs.id+'.open');
      assert.ok(await page.locator('#ev-'+lastMs.id+' .event-body').isVisible());
      assert.equal(await page.evaluate(()=>document.activeElement.dataset.id), lastMs.id);
      assert.equal(await page.evaluate(m=>[...document.querySelectorAll('.event')].every(n=>n.querySelector('.event-body p').textContent.length>0)&&document.querySelectorAll('.event').length<=PR_DATA.timeline.filter(e=>e.date.slice(0,7)===m).length, lastMs.month), true);
      if (width === 375) assert.ok((await page.locator('.tl-caption').boundingBox()).height <= 48, 'milestone caption stays within two lines');
      // Filters still work while a milestone is picked.
      await page.locator('.filters[aria-label="Branch"] .chip').nth(1).click();
      await page.waitForSelector('.filters[aria-label="Branch"] .chip[aria-pressed="true"]:not(:first-child)');
      await page.locator('.filters[aria-label="Branch"] .chip').first().click();
      await page.waitForSelector('.filters[aria-label="Branch"] .chip:first-child[aria-pressed="true"]');
      await page.getByRole('button',{name:'Earlier milestone'}).click();
      await page.waitForSelector('.tl-mark.sel[data-id="'+ms[ms.length-2].id+'"]');
      assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('aria-label')),'Earlier milestone');
      await page.getByRole('button',{name:'All events'}).click();
      await page.waitForSelector('.tl-mark.sel',{state:'detached'});
      assert.equal(await page.evaluate(()=>location.hash),'#/timeline');
      // A milestone link on Overview opens its month with the event expanded and on screen.
      await page.goto(base+'#/overview');
      const link = page.locator('a.feed-title[href^="#/timeline/"]').first();
      await link.evaluate(a=>{const d=a.closest('details'); if (d) d.open=true;});
      await link.click();
      await page.waitForSelector('.event.open');
      const box = await page.locator('.event.open').boundingBox();
      assert.ok(box.y >= 0 && box.y < page.viewportSize().height, 'linked event on screen: '+box.y);
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
    const textContext = await browser.newContext({javaScriptEnabled:false, viewport:{width:375,height:812}});
    const textPage = await textContext.newPage();
    await textPage.goto(base+'reading.html');
    const textSections = await textPage.locator('main section').count();
    assert.equal(textSections, JSON.parse(fs.readFileSync('site/data/core.json','utf8')).sections.length);
    assert.ok(await textPage.locator('#sec-2107').innerText().then(t=>t.includes('Ratepayer')));
    assert.ok(await textPage.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await textPage.screenshot({path:'uat-screenshots/375-text-index.png'});
    await textPage.setViewportSize({width:1280,height:800});
    await textPage.goto(base+'reading.html');
    await textPage.evaluate(() => document.fonts.ready);
    await textPage.screenshot({path:'uat-screenshots/1280-text-index.png'});
    await textContext.close();
    const race = await browser.newPage();
    await race.route('**/data/bill.js*', async route => {
      await new Promise(resolve => setTimeout(resolve, 250));
      await route.continue();
    });
    await race.goto(base+'#/bill/search/page%2054', {waitUntil:'domcontentloaded'});
    await race.locator('[data-tab="news"]').click();
    await race.waitForFunction(() => Boolean(window.PR_BILL));
    assert.ok(race.url().endsWith('#/timeline'), 'late search must not redirect away from the selected tab');
    await race.close();
    assert.deepEqual(errors,[]);
    fs.mkdirSync('.test-artifacts',{recursive:true});
    fs.writeFileSync('.test-artifacts/uat.json',JSON.stringify({views:results,errors},null,2));
    console.log(`${results.length} rendered states; search, filters, citations, theme and keyboard checks passed at all three widths.`);
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
