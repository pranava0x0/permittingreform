/* X (x.com) post collector, run inside a logged-in browser tab.
 *
 * Paste the whole file into the browser's JavaScript tool on any x.com page, then:
 *
 *   __xs.start(targets, { since: "2026-10-20", held: ["2107..."] })   // returns at once
 *   __xs.status()                                                    // poll until done
 *   __xs.dump()                                                      // writes JSON lines into the page body
 *
 * and read the page with a text extractor. targets are paths ("/SenCapito",
 * "/search?q=BAAJA&f=live", "/NATHPO_org/status/123"). The collector moves between
 * them with in-app navigation, so state survives; a full page load clears it, and
 * results are also kept in localStorage under "xs:results" in case of one.
 *
 * Why it works this way (REFRESH.md, 2026-10-05 to 2026-10-20): the JavaScript
 * tool times out at about 45 seconds and filters output containing ? & = ; %,
 * so the run happens in the background and the dump goes through the page text.
 *
 * Only post text, author, time, link cards, quoted posts and image alt text and URLs
 * are kept. Videos are flagged, not fetched. A post is kept when it is on or after
 * `since`, not in `held` (status ids already in the data), and either the target
 * is marked all: true or its text matches TOPIC.
 */
(function () {
  const TOPIC = /permit|BAAJA|affordability and jobs|NEPA|section 106|\b106\b|NHPA|historic preserv|THPO|tribal|tribes|sacred|data cent|transmission|interconnect|capito|whitehouse|heinrich|mike lee|SPEED Act|judicial review|statute of limitations|cloture|H\.?R\.? ?2347|clean energy|wind and solar|offshore wind|grid|ratepayer|endangered species|ESA\b|FERC|pipeline|geothermal|nuclear/i;
  const KEY = "xs:results";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const clean = (s) => (s || "").replace(/\s+/g, " ").trim();
  const bare = (u) => (u || "").split("?")[0];

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; }
  }
  function save(r) {
    try { localStorage.setItem(KEY, JSON.stringify(r)); } catch (e) { /* quota: results still in memory */ }
  }

  function parse(art) {
    const time = art.querySelector("time[datetime]");
    const link = time && time.closest("a[href*='/status/']");
    if (!link) return null;
    const url = "https://x.com" + bare(link.getAttribute("href")).replace(/\/(photo|analytics)\/.*$/, "");
    const names = art.querySelector("[data-testid='User-Name']");
    const texts = art.querySelectorAll("[data-testid='tweetText']");
    const quoteBox = art.querySelector("div[role='link'] [data-testid='tweetText']");
    const main = Array.from(texts).find((t) => t !== quoteBox);
    const card = art.querySelector("[data-testid='card.wrapper']");
    const cardLink = card && card.querySelector("a[href]");
    const imgs = Array.from(art.querySelectorAll("img[src*='pbs.twimg.com/media']"))
      .filter((i) => !(quoteBox && quoteBox.closest("div[role='link']").contains(i)))
      .map((i) => ({ alt: clean(i.alt) === "Image" ? "" : clean(i.alt), src: bare(i.src) + ".jpg" }));
    return {
      url,
      id: url.split("/status/")[1],
      handle: url.split("/")[3],
      name: names ? clean(names.innerText.split("\n")[0]) : "",
      at: time.getAttribute("datetime"),
      text: main ? clean(main.innerText) : "",
      truncated: Boolean(art.querySelector("[data-testid='tweet-text-show-more-link']")),
      links: main ? Array.from(main.querySelectorAll("a[href^='https://t.co']")).map((a) => ({ tco: a.href, shown: clean(a.innerText) })) : [],
      quoted: quoteBox ? clean(quoteBox.innerText) : "",
      card: card ? { title: clean(card.innerText).slice(0, 300), tco: cardLink ? bare(cardLink.href) : "" } : null,
      images: imgs,
      video: Boolean(art.querySelector("[data-testid='videoPlayer'], [data-testid='videoComponent']")),
      repost: clean((art.querySelector("[data-testid='socialContext']") || {}).innerText || ""),
    };
  }

  function go(path) {
    history.pushState({}, "", path);
    window.dispatchEvent(new PopStateEvent("popstate", { state: {} }));
  }

  async function waitArticles(ms) {
    const end = Date.now() + ms;
    while (Date.now() < end) {
      if (document.querySelector("article[data-testid='tweet']")) return true;
      await sleep(300);
    }
    return false;
  }

  const state = { running: false, done: [], current: null, log: [] };

  async function collect(target, opts, results) {
    const t = typeof target === "string" ? { path: target } : target;
    go(t.path);
    await sleep(1500);
    if (!(await waitArticles(12000))) { state.log.push(t.path + ": no posts"); return; }
    const isStatus = /\/status\//.test(t.path);
    let older = 0, kept = 0, seen = 0;
    for (let i = 0; i < (t.scrolls || opts.scrolls || 8); i++) {
      document.querySelectorAll("article[data-testid='tweet']").forEach((art) => {
        const p = parse(art);
        if (!p) return;
        seen++;
        // A repost carries its original date, so an old one still counts as recent
        // activity; a pinned post ("Pinned" in the same slot) does not.
        if (p.at.slice(0, 10) < opts.since) { if (!/repost/i.test(p.repost)) older++; return; }
        if (opts.held.has(p.id) || results[p.id]) return;
        if (!(t.all || isStatus || TOPIC.test(p.text + " " + p.quoted + " " + ((p.card && p.card.title) || "")))) return;
        p.from = t.path;
        results[p.id] = p;
        kept++;
      });
      save(results);
      if (!isStatus && older > 6) break;
      window.scrollBy(0, window.innerHeight * 2.5);
      await sleep(1600);
    }
    state.log.push(t.path + ": kept " + kept + " of " + seen + " seen");
  }

  async function start(targets, opts) {
    if (state.running) return "already running";
    const o = { since: opts.since, scrolls: opts.scrolls, held: new Set(opts.held || []) };
    const results = load();
    state.running = true; state.done = []; state.log = [];
    (async () => {
      for (const t of targets) {
        state.current = typeof t === "string" ? t : t.path;
        try { await collect(t, o, results); } catch (e) { state.log.push(state.current + ": " + e.message); }
        state.done.push(state.current);
        window.scrollTo(0, 0);
      }
      state.running = false; state.current = null;
    })();
    return "started " + targets.length;
  }

  function status() {
    return { running: state.running, current: state.current, done: state.done.length, kept: Object.keys(load()).length, log: state.log };
  }

  /* Writes one JSON object per line, newest first, into the page body. The X app
     stops working afterwards; reload the page to collect again. */
  function dump(filter) {
    const r = Object.values(load()).filter(filter || (() => true)).sort((a, b) => (a.at < b.at ? 1 : -1));
    const pre = document.createElement("pre");
    pre.textContent = r.map((p) => JSON.stringify(p)).join("\n");
    const main = document.createElement("main");
    const art = document.createElement("article");
    art.appendChild(pre); main.appendChild(art);
    document.body.replaceChildren(main);
    return r.length + " posts";
  }

  function reset() { localStorage.removeItem(KEY); return "cleared"; }

  window.__xs = { start, status, dump, reset, parse, TOPIC };
  return "x_collect loaded";
})();
