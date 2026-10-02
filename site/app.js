/* Permitting Reform: views and routing. Data comes from data/core.js (window.PR_DATA)
   and, on demand, data/bill.js (window.PR_BILL). Every data string is set as text, never as HTML. */
(function () {
  "use strict";

  const D = window.PR_DATA;
  const S = window.PRSearch;
  const view = document.getElementById("view");
  if (!D || !S || !view) return;

  const byNum = {};
  D.sections.forEach((s, i) => { byNum[s.n] = s; s.order = i; });

  /* ---------- small helpers ---------- */

  function append(node, child) {
    if (child == null || child === false) return;
    if (Array.isArray(child)) child.forEach((c) => append(node, c));
    else node.appendChild(typeof child === "object" ? child : document.createTextNode(String(child)));
  }

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach((k) => {
        const v = attrs[k];
        if (v == null || v === false) return;
        if (k === "class") node.className = v;
        else if (k.slice(0, 2) === "on") node.addEventListener(k.slice(2), v);
        else node.setAttribute(k, v === true ? "" : v);
      });
    }
    append(node, children);
    return node;
  }

  /* Replace a node's children; unlike replaceChildren, accepts nested arrays. */
  function fill(node, ...children) {
    node.replaceChildren();
    append(node, children);
    return node;
  }

  function safeUrl(u) {
    return /^https?:\/\//i.test(String(u || "")) ? u : null;
  }

  function ext(url, label, cls) {
    const href = safeUrl(url);
    if (!href) return el("span", { class: cls }, label);
    return el("a", { href: href, target: "_blank", rel: "noopener noreferrer", class: cls }, label);
  }

  function pdfHref(page) {
    return D.meta.pdf + "#page=" + page;
  }

  function pdfLink(page, label, cls) {
    return el("a", { href: pdfHref(page), target: "_blank", rel: "noopener", class: cls || "cite" }, label);
  }

  function secHref(n, anchor) {
    return "#/bill/sec/" + n + (anchor ? "/" + anchor : "");
  }

  function secLink(n) {
    const s = byNum[n];
    if (!s) return el("span", null, "Sec. " + n);
    return el("a", { href: secHref(n), class: "sec-link", title: s.h }, "Sec. " + n);
  }

  function secLinks(nums) {
    const out = [];
    nums.forEach((n, i) => { if (i) out.push(", "); out.push(secLink(n)); });
    return out;
  }

  function num(n) {
    return Number(n).toLocaleString("en-US");
  }

  function marked(text, rs) {
    if (!rs || !rs.length) return [text];
    const out = [];
    let at = 0;
    rs.forEach((r) => {
      if (r[0] > at) out.push(text.slice(at, r[0]));
      out.push(el("mark", null, text.slice(r[0], r[1])));
      at = r[1];
    });
    if (at < text.length) out.push(text.slice(at));
    return out;
  }

  function chip(label, pressed, onclick, count) {
    return el("button", { type: "button", class: "chip", "aria-pressed": pressed ? "true" : "false", onclick: onclick },
      label, count == null ? null : el("span", { class: "chip-count" }, count));
  }

  /* Machine-written text may hold several paragraphs, separated by a blank line. */
  function paras(text, cls) {
    return String(text || "").split(/\n\s*\n/).map((t) => el("p", { class: cls }, t));
  }

  function firstSentence(text) {
    const m = /^(.*?[.!?])\s/.exec(text + " ");
    return m ? m[1] : text;
  }

  const STANCE = { supports: "Supports", opposes: "Opposes", mixed: "Mixed", neutral: "No position stated", reporting: "Reporting" };
  function stanceTag(stance) {
    if (!STANCE[stance]) return null;
    return el("span", { class: "stance stance-" + stance }, STANCE[stance]);
  }

  function topicTags(topics) {
    const known = (topics || []).filter((t) => D.topics[t]);
    if (!known.length) return null;
    return el("span", { class: "topics" }, known.map((t) => el("span", { class: "topic" }, D.topics[t])));
  }

  const LINK_NOTE = { blocked: "site blocks automated checks", error: "no answer when checked", dead: "dead when checked" };

  function sourceList(sources) {
    const list = (sources || []).filter((s) => safeUrl(s.url));
    if (!list.length) return null;
    const items = [];
    list.forEach((s, i) => {
      if (i) items.push("; ");
      items.push(ext(s.url, s.publisher || s.title || "Source"));
      if (s.lk) items.push(el("span", { class: "unchecked" }, " (" + LINK_NOTE[s.lk] + ")"));
    });
    return el("p", { class: "sources" }, "Source: ", items);
  }

  function searchBox(value) {
    const input = el("input", { type: "search", name: "q", id: "search-input", placeholder: "Search the bill text", enterkeyhint: "search", spellcheck: "false", value: value || "" });
    return el("form", { class: "search", role: "search", autocomplete: "off", onsubmit: (ev) => {
      ev.preventDefault();
      const q = input.value.trim();
      location.hash = q ? "#/bill/search/" + encodeURIComponent(q) : "#/bill";
    } },
      el("label", { class: "sr-only", "for": "search-input" }, "Search the bill text"),
      input,
      el("button", { type: "submit" }, "Search"));
  }

  /* ---------- lazy bill text ---------- */

  let billPromise = null;
  function ensureBill() {
    if (window.PR_BILL) return Promise.resolve(window.PR_BILL);
    if (!billPromise) {
      billPromise = new Promise((resolve, reject) => {
        const tag = document.createElement("script");
        tag.src = "data/bill.js?v=4";
        tag.onload = () => (window.PR_BILL ? resolve(window.PR_BILL) : reject(new Error("bill text did not load")));
        tag.onerror = () => { billPromise = null; reject(new Error("bill text could not be fetched")); };
        document.head.appendChild(tag);
      });
    }
    return billPromise;
  }

  function loading(text) {
    return el("p", { class: "loading", role: "status" }, text);
  }

  function failure(err) {
    return el("div", { class: "notice", role: "alert" },
      el("p", null, "The bill text did not load (" + err.message + ")."),
      el("p", null, el("a", { href: D.meta.pdf }, "Open the PDF")));
  }

  /* ---------- overview ---------- */

  function renderOverview() {
    const o = D.overview;
    const m = D.meta;
    const head = el("div", { class: "lede overview-lede" },
      el("div", { class: "bill-heading" }, el("h1", null, "BAAJA"),
        el("details", { class: "bill-details" },
          el("summary", null, "Bill details"),
          el("p", null, m.short_title),
          el("p", { class: "facts" }, num(m.pages) + " pages · " + m.sections + " sections · released " + S.formatDate(m.released)),
          el("p", null, pdfLink(1, "Bill PDF", "plain"), " · ", ext(o.status.points[0].source.url, "Senate EPW release")))),
      el("p", { class: "note" }, "Proposed law", " · ",
        el("a", { href: "#/method" }, D.checks.inference && (D.checks.inference.stale || D.checks.inference.flagged || D.checks.inference.unchecked) ? "Review incomplete" : "Review status")),
      searchBox(""));

    const status = el("section", { class: "block", "aria-labelledby": "h-status" },
      el("h2", { id: "h-status" }, "Status"),
      el("ul", { class: "status-list" }, o.status.points.map((p) =>
        el("li", null, p.text + " ", el("span", { class: "sources-inline" }, ext(p.source.url, p.source.label))))));

    const provisions = el("section", { class: "block", "aria-labelledby": "h-prov" },
      el("h2", { id: "h-prov" }, "Main provisions"),
      el("ol", { class: "provisions" }, o.headlines.map((h) =>
        el("li", null,
          el("h3", null, el("a", { href: secHref(h.sections[0]) }, h.title)),
          el("p", null, h.text),
          el("p", { class: "where" }, secLinks(h.sections))))));

    const clocks = el("section", { class: "block", "aria-labelledby": "h-clocks" },
      el("h2", { id: "h-clocks" }, "Deadlines"),
      el("div", { class: "table-wrap" }, el("table", { class: "data" },
        el("thead", null, el("tr", null, el("th", { scope: "col" }, "Time"), el("th", { scope: "col" }, "For"), el("th", { scope: "col" }, "Text"))),
        el("tbody", null, o.clocks.map((c) => el("tr", null,
          el("td", { class: "figure" }, c.clock),
          el("td", null, c.what),
          el("td", { class: "nowrap" }, secLink(c.section), ", ", pdfLink(c.c[0], S.formatCite(c.c)))))))));

    const money = el("section", { class: "block", "aria-labelledby": "h-money" },
      el("h2", { id: "h-money" }, "Money authorized"),
      el("div", { class: "table-wrap" }, el("table", { class: "data" },
        el("thead", null, el("tr", null, el("th", { scope: "col" }, "Amount"), el("th", { scope: "col" }, "For"), el("th", { scope: "col" }, "Fiscal years"), el("th", { scope: "col" }, "Text"))),
        el("tbody", null, o.money.map((c) => el("tr", null,
          el("td", { class: "figure" }, c.amount),
          el("td", null, c.what),
          el("td", { class: "nowrap", "data-label": "Fiscal years" }, c.years),
          el("td", { class: "nowrap" }, secLink(c.section), ", ", pdfLink(c.c[0], S.formatCite(c.c))))))),
      el("p", { class: "note" }, o.money_note)));

    const cmp = D.compare;
    const changes = el("section", { class: "block", "aria-labelledby": "h-changes" },
      el("h2", { id: "h-changes" }, "Changes from earlier bills"),
      el("div", { class: "two-col" },
        el("div", null,
          el("h3", null, "Added"),
          el("ul", { class: "plain-list" }, cmp.added.slice(0, 5).map((a) => el("li", null, a.text + " ", el("span", { class: "where" }, secLinks(a.sections)))))),
        el("div", null,
          el("h3", null, "Left out"),
          el("ul", { class: "plain-list" }, cmp.dropped.slice(0, 5).map((a) =>
            el("li", null, a.text + " ", el("span", { class: "where" }, versionLabel(a.from) + ", ", citeNode(a))))))),
      el("p", null, el("a", { href: "#/compare" }, "Full comparison")));

    const recentMedia = D.media.slice().sort((a, b) => (a.date < b.date ? 1 : -1)).slice(0, 6);
    const milestones = D.timeline.filter((e) => e.milestone).slice().sort((a, b) => (a.date < b.date ? 1 : -1)).slice(0, 6);
    const latest = el("section", { class: "block", "aria-labelledby": "h-latest" },
      el("div", { class: "two-col" },
        el("div", null,
          el("h2", { id: "h-latest" }, "Recent coverage"),
          el("ul", { class: "feed" }, recentMedia.map((it) => el("li", null,
            ext(it.url, it.title, "feed-title"),
            el("span", { class: "feed-meta" }, it.outlet + " · " + S.formatDate(it.date))))),
          el("p", null, el("a", { href: "#/media" }, "All " + D.media.length + " items"))),
        el("div", null,
          el("h2", null, "Milestones"),
          el("ul", { class: "feed" }, milestones.map((e) => el("li", null,
            el("a", { href: "#/timeline", class: "feed-title" }, e.title),
            el("span", { class: "feed-meta" }, S.formatDate(e.date))))),
          el("p", null, el("a", { href: "#/timeline" }, "All " + D.timeline.length + " events")))));

    return [head, provisions, status, el("div", { class: "two-col wide-left" }, clocks, money), changes, latest];
  }

  /* ---------- bill: index, section, search ---------- */

  let billTopic = "all";
  let billMajor = false;

  function structureGroups(list) {
    const groups = [];
    let cur = null;
    list.forEach((s) => {
      const key = s.div + "|" + s.ti;
      if (!cur || cur.key !== key) {
        cur = { key: key, div: s.div, divh: s.divh, ti: s.ti, tih: s.tih, sections: [] };
        groups.push(cur);
      }
      cur.sections.push(s);
    });
    return groups;
  }

  function titleCase(caps) {
    const small = { of: 1, and: 1, the: 1, on: 1, "for": 1, to: 1, "in": 1 };
    return caps.toLowerCase().split(" ").map((w, i) => (i && small[w] ? w : w.charAt(0).toUpperCase() + w.slice(1))).join(" ");
  }

  function groupLabel(g) {
    return titleCase(g.div) + ", " + titleCase(g.ti) + ": " + titleCase(g.tih);
  }

  function renderBillIndex() {
    const counts = {};
    D.sections.forEach((s) => s.topics.forEach((t) => { counts[t] = (counts[t] || 0) + 1; }));
    const topics = Object.keys(D.topics).filter((t) => counts[t]);
    const majors = D.sections.filter((s) => s.imp === 3).length;
    const list = D.sections.filter((s) => (billTopic === "all" || s.topics.indexOf(billTopic) >= 0) && (!billMajor || s.imp === 3));

    const filters = el("div", { class: "filters", role: "group", "aria-label": "Topic" },
      chip("All", billTopic === "all", () => { billTopic = "all"; route(); }, D.sections.length),
      topics.map((t) => chip(D.topics[t], billTopic === t, () => { billTopic = t; route(); }, counts[t])),
      el("span", { class: "filter-gap" }),
      chip("Major provisions", billMajor, () => { billMajor = !billMajor; route(); }, majors));

    const body = list.length ? structureGroups(list).map((g) => el("section", { class: "index-group" },
      el("h2", null, groupLabel(g)),
      el("ul", { class: "index" }, g.sections.map((s) => el("li", { class: s.imp === 3 ? "major" : null },
        el("a", { href: secHref(s.n), class: "index-head" },
          el("span", { class: "index-num" }, s.n),
          el("span", { class: "index-title" }, s.h)),
        el("span", { class: "index-pages" }, S.formatPages(s.p1, s.p2)),
        el("p", { class: "index-sum" }, firstSentence(s.plain)),
        el("p", { class: "index-tags" }, s.imp === 3 ? el("span", { class: "tag-major" }, "Major") : null, topicTags(s.topics)))))))
      : el("p", { class: "empty" }, "No sections match.");

    const active = billTopic !== "all" || billMajor;
    const filterBox = el("details", { class: "filter-wrap", open: active || window.matchMedia("(min-width: 640px)").matches },
      el("summary", null, "Topics"), filters);
    return [el("div", { class: "lede" }, el("h1", null, "BAAJA sections"), searchBox("")), filterBox, body];
  }

  function outline(current) {
    const groups = structureGroups(D.sections);
    const nav = el("nav", { class: "outline", "aria-label": "Bill sections" },
      groups.map((g) => {
        const open = g.sections.some((s) => s.n === current);
        return el("details", { open: open },
          el("summary", null, titleCase(g.div).replace("Division ", "Div. ") + ", " + titleCase(g.ti) + ": " + titleCase(g.tih)),
          el("ul", null, g.sections.map((s) => el("li", null,
            el("a", { href: secHref(s.n), "aria-current": s.n === current ? "true" : null, class: s.imp === 3 ? "major" : null },
              s.n + " " + s.h)))));
      }));
    return el("details", { class: "outline-wrap", open: window.matchMedia("(min-width: 1024px)").matches },
      el("summary", { class: "outline-toggle" }, "Sections"), nav);
  }

  function quoteBlock(q) {
    return el("figure", { class: "quote" },
      el("blockquote", null, q.t),
      el("figcaption", null, pdfLink(q.c[0], S.formatCite(q.c)), q.why ? " · " + q.why : null));
  }

  function versusBlock(s) {
    const rows = [["Current law", s.vs.current], ["SPEED Act", s.vs.speed], ["EPRA 2024", s.vs.epra]].filter((r) => r[1]);
    if (!rows.length) return null;
    return el("section", { class: "sec-part machine", "aria-labelledby": "h-vs" },
      el("h2", { id: "h-vs" }, "Earlier versions", el("span", { class: "credit-inline" }, "AI-written")),
      el("dl", { class: "versus" }, rows.map((r) => [el("dt", null, r[0]), el("dd", null, paras(r[1]))])));
  }

  function renderSection(n, anchor, query) {
    const s = byNum[n];
    if (!s) return [el("div", { class: "notice" }, el("p", null, "No section " + n + "."), el("p", null, el("a", { href: "#/bill" }, "All sections")))];
    const prev = D.sections[s.order - 1];
    const next = D.sections[s.order + 1];
    const place = [titleCase(s.div), titleCase(s.ti)];
    if (s.su) place.push(s.su);

    const textHost = el("div", { class: "fulltext", id: "fulltext" }, loading("Loading"));
    const article = el("article", { class: "section" },
      el("h1", null, "Sec. " + s.n + ". " + s.h),
      el("p", { class: "sec-meta" },
        el("span", null, place.join(", ")), "·",
        pdfLink(s.p1, S.formatPages(s.p1, s.p2)), "·", el("span", null, num(s.words) + " words"),
        s.imp === 3 ? ["·", el("span", { class: "tag-major" }, "Major")] : null,
        topicTags(s.topics)),
      el("section", { class: "sec-part machine", "aria-labelledby": "h-sum" },
        el("h2", { id: "h-sum" }, "Summary", el("span", { class: "credit-inline" }, "AI-written")),
        paras(s.plain, "summary"),
        s.points.length ? el("ul", { class: "points" }, s.points.map((p) => el("li", null, p.t, p.c ? [" ", pdfLink(p.c[0], S.formatCite(p.c))] : null))) : null),
      s.quotes.length ? el("section", { class: "sec-part", "aria-labelledby": "h-key" },
        el("h2", { id: "h-key" }, "Key text"),
        s.quotes.map(quoteBlock)) : null,
      versusBlock(s),
      el("section", { class: "sec-part", "aria-labelledby": "h-full" },
        el("h2", { id: "h-full" }, "Full text"),
        textHost),
      el("nav", { class: "pager", "aria-label": "Neighboring sections" },
        prev ? el("a", { href: secHref(prev.n), rel: "prev" }, "Previous: Sec. " + prev.n + ". " + prev.h) : el("span"),
        next ? el("a", { href: secHref(next.n), rel: "next" }, "Next: Sec. " + next.n + ". " + next.h) : el("span")));

    ensureBill().then((bill) => {
      if (!textHost.isConnected) return;
      const list = bill[n] || [];
      const q = query ? S.parseQuery(query) : null;
      fill(textHost, list.map((p) => {
        const id = "p-" + p[0] + "-" + (p[1] == null ? "x" : p[1]);
        const rs = q && q.type === "text" ? S.ranges(p[3], q) : null;
        return el("div", { class: "para lvl" + Math.min(p[2], 6), id: id },
          el("a", { class: "gutter", href: pdfHref(p[0]), target: "_blank", rel: "noopener", "aria-label": "Page " + p[0] + (p[1] == null ? "" : ", line " + p[1]) },
            p[0] + (p[1] == null ? "" : ":" + p[1])),
          el("p", null, marked(p[3], rs)));
      }));
      if (anchor) {
        const target = document.getElementById("p-" + anchor);
        if (target) {
          target.classList.add("target");
          target.scrollIntoView({ block: "center" });
        }
      }
    }).catch((err) => fill(textHost, failure(err)));

    return [searchBox(query || ""), el("div", { class: "bill-layout" }, outline(n), article)];
  }

  function renderSearch(raw) {
    const q = S.parseQuery(raw);
    if (q.type === "empty") return renderBillIndex();
    if (q.type === "section") {
      if (byNum[q.n]) { location.replace(secHref(q.n)); return [loading("Opening section " + q.n)]; }
      return [searchBox(q.raw), el("div", { class: "notice" }, el("p", null, "No section " + q.n + ". Sections run from 1101 to 2302."))];
    }
    const host = el("div", { class: "results" }, loading("Searching"));
    ensureBill().then((bill) => {
      if (!host.isConnected) return;
      if (q.type === "page") {
        const s = S.sectionForPage(D.sections, q.page);
        if (!s) { fill(host, el("div", { class: "notice" }, el("p", null, "The bill has " + D.meta.pages + " pages. Sections start on page 4."))); return; }
        const p = (bill[s.n] || []).find((x) => x[0] >= q.page) || bill[s.n][0];
        location.replace(secHref(s.n, p[0] + "-" + (p[1] == null ? "x" : p[1])));
        return;
      }
      const res = S.searchBill(D.sections, bill, q);
      document.title = "“" + q.raw + "” · Permitting Reform";
      if (!res.sections.length) {
        fill(host,
          el("h1", null, "No matches for “" + q.raw + "”"),
          el("p", null, "The bill says “computational load” for data centers, “claim” for a lawsuit, and “authorization” for a permit."));
        return;
      }
      const enc = encodeURIComponent(q.raw);
      const blocks = res.sections.map((r) => {
        const s = byNum[r.n];
        const shown = r.hits.slice(0, 3);
        const anchorOf = (hit) => hit.page + "-" + (hit.line == null ? "x" : hit.line) + "/" + enc;
        return el("section", { class: "result" },
          el("h2", null, el("a", { href: shown.length ? secHref(s.n, anchorOf(shown[0])) : secHref(s.n) }, "Sec. " + s.n + ". " + s.h)),
          el("p", { class: "result-meta" }, S.formatPages(s.p1, s.p2),
            r.hits.length ? " · " + r.hits.length + (r.hits.length === 1 ? " passage" : " passages") : " · in the summary"),
          !shown.length ? el("p", { class: "result-sum" }, marked(firstSentence(s.plain), S.ranges(firstSentence(s.plain), q))) : null,
          el("ul", { class: "passages" }, shown.map((hit) => {
            const p = bill[s.n][hit.i];
            const sn = S.snippet(p[3], S.ranges(p[3], q), 260);
            return el("li", null,
              el("a", { class: "gutter", href: secHref(s.n, anchorOf(hit)), "aria-label": "Page " + p[0] + ", line " + p[1] }, p[0] + ":" + p[1]),
              el("p", null, sn.lead ? "… " : null, marked(sn.text, sn.ranges), sn.trail ? " …" : null));
          })),
          r.hits.length > shown.length ? el("p", { class: "more" }, el("a", { href: secHref(s.n, anchorOf(shown[0])) }, "All " + r.hits.length + " passages")) : null);
      });
      fill(host,
        el("h1", null, "“" + q.raw + "”"),
        el("p", { class: "facts", role: "status" }, num(res.passages) + (res.passages === 1 ? " passage in " : " passages in ") + res.sections.length + (res.sections.length === 1 ? " section" : " sections")),
        blocks);
    }).catch((err) => fill(host, failure(err)));
    return [searchBox(q.raw), host];
  }

  /* ---------- compare ---------- */

  function versionLabel(key) {
    const v = D.compare.versions.find((x) => x.key === key);
    return v ? v.label : key;
  }

  function citeNode(cell) {
    if (!cell.cite) return null;
    return safeUrl(cell.url) ? ext(cell.url, cell.cite) : cell.cite;
  }

  function compareCell(cell) {
    const kids = [el("span", { class: "cell-text" }, cell.text)];
    if (cell.sections && cell.sections.length) kids.push(el("span", { class: "cell-cite" }, secLinks(cell.sections)));
    else if (cell.cite) kids.push(el("span", { class: "cell-cite" }, citeNode(cell)));
    return kids;
  }

  function renderCompare(groupId) {
    const c = D.compare;
    const groups = groupId && c.groups.some((g) => g.id === groupId) ? c.groups.filter((g) => g.id === groupId) : c.groups;
    const keys = c.versions.map((v) => v.key);
    const filters = el("div", { class: "filters", role: "group", "aria-label": "Subject" },
      el("a", { class: "chip", href: "#/compare", "aria-current": groups.length === c.groups.length ? "true" : null }, "All"),
      c.groups.map((g) => el("a", { class: "chip", href: "#/compare/" + g.id, "aria-current": groups.length === 1 && groups[0].id === g.id ? "true" : null }, g.label)));

    const versions = el("dl", { class: "versions" }, c.versions.map((v) => el("div", null,
      el("dt", null, safeUrl(v.url) ? ext(v.url, v.label) : v.label),
      el("dd", null, v.sub))));

    const tables = groups.map((g) => el("section", { class: "block" },
      el("h2", null, g.label),
      el("div", { class: "table-wrap" }, el("table", { class: "compare" },
        el("thead", null, el("tr", null, el("th", { scope: "col" }, "Subject"), c.versions.map((v) => el("th", { scope: "col", class: "col-" + v.key }, v.label)))),
        el("tbody", null, g.rows.map((r) => [el("tr", null,
          el("th", { scope: "row" }, r.topic),
          keys.map((k) => el("td", { class: "col-" + k, "data-label": versionLabel(k) }, compareCell(r[k])))),
          r.note ? el("tr", { class: "row-note" },
            el("td", { colspan: keys.length + 1 }, el("strong", null, r.note.label + ". "), el("span", { class: "cell-text" }, r.note.text),
              el("span", { class: "cell-cite" }, r.note.sources.map((src, i) => [i ? " · " : null, citeNode(src)])))) : null]))))));

    const lists = el("section", { class: "block" },
      el("div", { class: "two-col" },
        el("div", null,
          el("h2", null, "Added in BAAJA"),
          el("ul", { class: "plain-list" }, c.added.map((a) => el("li", null, a.text + " ", el("span", { class: "where" }, secLinks(a.sections)))))),
        el("div", null,
          el("h2", null, "Left out of BAAJA"),
          ["speed", "epra"].map((k) => [
            el("h3", null, versionLabel(k)),
            el("ul", { class: "plain-list" }, c.dropped.filter((d) => d.from === k).map((d) => el("li", null, d.text + " ", el("span", { class: "where" }, citeNode(d)))))]))));

    return [
      el("div", { class: "lede" }, el("h1", null, "Comparison", el("span", { class: "credit-inline" }, "AI-written"))),
      versions, filters, tables, groupId ? null : lists];
  }

  /* ---------- timeline ---------- */

  const BRANCHES = [["all", "All"], ["executive", "White House"], ["agency", "Agencies"], ["congress_house", "House"], ["congress_senate", "Senate"], ["court", "Courts"], ["states", "States"], ["other", "Other"]];
  let tlBranch = "all";
  let tlMilestones = false;

  function branchLabel(key) {
    const b = BRANCHES.find((x) => x[0] === key);
    return b ? b[1] : "Other";
  }

  function renderTimeline() {
    const all = D.timeline.slice().sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
    const counts = {};
    all.forEach((e) => { counts[e.branch] = (counts[e.branch] || 0) + 1; });
    const list = all.filter((e) => (tlBranch === "all" || e.branch === tlBranch) && (!tlMilestones || e.milestone));
    const filters = el("div", { class: "filters", role: "group", "aria-label": "Branch" },
      BRANCHES.filter((b) => b[0] === "all" || counts[b[0]]).map((b) =>
        chip(b[1], tlBranch === b[0], () => { tlBranch = b[0]; route(); }, b[0] === "all" ? all.length : counts[b[0]])),
      el("span", { class: "filter-gap" }),
      chip("Milestones", tlMilestones, () => { tlMilestones = !tlMilestones; route(); }, all.filter((e) => e.milestone).length));
    const out = [];
    let year = null;
    list.forEach((e) => {
      const y = e.date.slice(0, 4);
      if (y !== year) { year = y; out.push(el("h2", { class: "year" }, y)); }
      out.push(el("article", { class: "event" + (e.milestone ? " milestone" : "") },
        el("h3", null, e.title),
        el("p", { class: "event-meta" }, S.formatDate(e.date) + " · " + branchLabel(e.branch) + (e.background ? " · before 2025" : "")),
        el("p", null, e.summary),
        e.significance ? el("p", { class: "signif" }, e.significance) : null,
        e.quote && e.quote.text ? el("figure", { class: "quote small" },
          el("blockquote", null, e.quote.text),
          el("figcaption", null, safeUrl(e.quote.source_url) ? ext(e.quote.source_url, e.quote.speaker || "Source") : e.quote.speaker)) : null,
        e.sections && e.sections.length ? el("p", { class: "where" }, "In the bill: ", secLinks(e.sections)) : null,
        sourceList(e.sources)));
    });
    return [
      el("div", { class: "lede" }, el("h1", null, "Timeline")),
      filters,
      list.length ? el("div", { class: "timeline" }, out) : el("p", { class: "empty" }, "No events match.")];
  }

  /* ---------- people ---------- */

  const SECTORS = {
    congress: "Congress", white_house: "White House", agency: "Agencies", court: "Courts", industry: "Industry",
    trade_association: "Trade associations", think_tank: "Think tanks", environmental_group: "Environmental groups",
    labor: "Labor", state_local: "States and localities", academic: "Academics", media: "Reporters",
    former: "Former officials"
  };
  let pplSide = "inside";
  let pplStance = "all";

  /* "2026-01-28: Chaired the hearing" -> "January 28, 2026: Chaired the hearing" */
  function datedAction(text) {
    const m = /^(\d{4}-\d{2}-\d{2}):\s*(.*)$/.exec(text);
    return m ? S.formatDate(m[1]) + ": " + m[2] : text;
  }

  function renderPeople() {
    const all = D.people;
    const inside = all.filter((p) => p.inside_government);
    const outside = all.filter((p) => !p.inside_government);
    const pool = pplSide === "inside" ? inside : outside;
    const list = pool.filter((p) => pplStance === "all" || p.stance === pplStance);
    const stanceCounts = {};
    pool.forEach((p) => { stanceCounts[p.stance] = (stanceCounts[p.stance] || 0) + 1; });
    const filters = el("div", { class: "filters", role: "group", "aria-label": "Group and position" },
      chip("In government", pplSide === "inside", () => { pplSide = "inside"; pplStance = "all"; route(); }, inside.length),
      chip("Outside government", pplSide === "outside", () => { pplSide = "outside"; pplStance = "all"; route(); }, outside.length),
      el("span", { class: "filter-gap" }),
      chip("All positions", pplStance === "all", () => { pplStance = "all"; route(); }),
      ["supports", "mixed", "opposes", "neutral"].filter((k) => stanceCounts[k]).map((k) =>
        chip(STANCE[k], pplStance === k, () => { pplStance = k; route(); }, stanceCounts[k])));
    const GOV = { congress: 1, white_house: 1, agency: 1, court: 1 };
    const groups = {};
    list.forEach((p) => {
      const key = !p.inside_government && GOV[p.sector] ? "former" : p.sector;
      (groups[key] = groups[key] || []).push(p);
    });
    const order = Object.keys(SECTORS).filter((k) => groups[k]);
    const body = order.map((k) => el("section", { class: "block" },
      el("h2", null, SECTORS[k]),
      el("div", { class: "people" }, groups[k].map((p) => el("article", { class: "person" },
        el("h3", null, p.name, p.party ? el("span", { class: "party" }, " (" + p.party + ")") : null),
        el("p", { class: "role" }, [p.role, p.affiliation].filter(Boolean).join(", ")),
        el("p", { class: "person-stance" }, stanceTag(p.stance)),
        el("p", null, p.position),
        p.key_actions && p.key_actions.length ? el("ul", { class: "actions" }, p.key_actions.map((a) => el("li", null, datedAction(a)))) : null,
        p.quote && p.quote.text ? el("figure", { class: "quote small" },
          el("blockquote", null, p.quote.text),
          el("figcaption", null, safeUrl(p.quote.source_url) ? ext(p.quote.source_url, p.quote.date ? S.formatDate(p.quote.date) : "Source") : null)) : null,
        p.social && (safeUrl(p.social.x) || safeUrl(p.social.bluesky)) ? el("p", { class: "social" },
          safeUrl(p.social.x) ? ext(p.social.x, "X") : null,
          safeUrl(p.social.x) && safeUrl(p.social.bluesky) ? " · " : null,
          safeUrl(p.social.bluesky) ? ext(p.social.bluesky, "Bluesky") : null) : null,
        sourceList(p.sources))))));
    return [
      el("div", { class: "lede" }, el("h1", null, "People"), el("p", { class: "facts" }, "Positions as of " + S.formatDate(D.meta.as_of))),
      filters,
      list.length ? body : el("p", { class: "empty" }, "No entries match.")];
  }

  /* ---------- media ---------- */

  const MEDIA_TYPES = [
    ["all", "All", null],
    ["gov", "Government", ["gov_press_release", "gov_document", "court_filing"]],
    ["news", "News", ["news"]],
    ["analysis", "Analysis", ["analysis"]],
    ["statement", "Statements", ["org_statement"]],
    ["x", "X", ["social_x"]],
    ["bluesky", "Bluesky", ["social_bluesky"]],
    ["reddit", "Reddit", ["reddit"]],
    ["av", "Video and audio", ["youtube", "podcast", "conference"]]
  ];
  let mediaType = "all";
  let mediaStance = "all";
  let mediaTopic = "all";
  let mediaVisual = false;
  let mediaText = "";

  function mediaGroup(type) {
    const g = MEDIA_TYPES.find((t) => t[2] && t[2].indexOf(type) >= 0);
    return g ? g[0] : "news";
  }

  function mediaList() {
    const needle = mediaText.trim().toLowerCase();
    return D.media.filter((it) =>
      (mediaType === "all" || mediaGroup(it.type) === mediaType) &&
      (mediaStance === "all" || it.stance === mediaStance) &&
      (mediaTopic === "all" || (it.topics || []).indexOf(mediaTopic) >= 0) &&
      (!mediaVisual || (it.visuals && it.visuals.length)) &&
      (!needle || (it.title + " " + it.outlet + " " + (it.summary || "") + " " + (it.author || "")).toLowerCase().indexOf(needle) >= 0))
      .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  }

  function mediaItems(list) {
    if (!list.length) return el("p", { class: "empty" }, "No items match.");
    return el("ul", { class: "media-list" }, list.map((it) => {
      const g = MEDIA_TYPES.find((t) => t[0] === mediaGroup(it.type));
      return el("li", { class: "media-item" },
        el("h3", null, ext(it.url, it.title)),
        el("p", { class: "feed-meta" }, it.outlet + (it.author ? " · " + it.author : "") + " · " + S.formatDate(it.date) + " · " + g[1]),
        el("p", { class: "media-tags" }, stanceTag(it.stance), topicTags(it.topics),
          it.lk ? el("span", { class: "unchecked" }, LINK_NOTE[it.lk]) : null),
        it.summary ? el("p", null, it.summary) : null,
        it.visuals && it.visuals.length ? el("ul", { class: "visuals" }, it.visuals.map((v) => el("li", null,
          el("strong", null, "Cheat sheet: " + v.title + ". "), v.text + " ", ext(v.url, "View image")))) : null,
        it.quote && it.quote.text ? el("figure", { class: "quote small" },
          el("blockquote", null, it.quote.text),
          it.quote.speaker ? el("figcaption", null, it.quote.speaker) : null) : null);
    }));
  }

  function renderMedia() {
    const counts = { all: D.media.length };
    D.media.forEach((it) => { const g = mediaGroup(it.type); counts[g] = (counts[g] || 0) + 1; });
    const listHost = el("div", { id: "media-host" });
    const countHost = el("p", { class: "facts", role: "status" });
    const refresh = () => {
      const list = mediaList();
      fill(listHost, mediaItems(list));
      countHost.textContent = list.length + " of " + D.media.length + " items";
    };
    const visualCount = D.media.filter((it) => it.visuals && it.visuals.length).length;
    const typeChips = el("div", { class: "filters", role: "group", "aria-label": "Source type" },
      MEDIA_TYPES.filter((t) => counts[t[0]]).map((t) => chip(t[1], mediaType === t[0], () => { mediaType = t[0]; route(); }, counts[t[0]])),
      visualCount ? [el("span", { class: "filter-gap" }),
        chip("Cheat sheets", mediaVisual, () => { mediaVisual = !mediaVisual; route(); }, visualCount)] : null);
    const stanceChips = el("div", { class: "filters", role: "group", "aria-label": "Position" },
      chip("All positions", mediaStance === "all", () => { mediaStance = "all"; route(); }),
      ["supports", "mixed", "opposes", "reporting", "neutral"].filter((k) => D.media.some((it) => it.stance === k)).map((k) =>
        chip(STANCE[k], mediaStance === k, () => { mediaStance = k; route(); })),
      el("span", { class: "filter-gap" }),
      el("label", { class: "sr-only", "for": "media-filter" }, "Filter by word"),
      el("input", { id: "media-filter", type: "search", class: "inline-filter", placeholder: "Filter by word", value: mediaText,
        oninput: (ev) => { mediaText = ev.target.value; refresh(); } }));
    const topicCounts = {};
    D.media.forEach((it) => (it.topics || []).forEach((t) => { topicCounts[t] = (topicCounts[t] || 0) + 1; }));
    const topicChips = el("div", { class: "filters", role: "group", "aria-label": "Topic" },
      chip("All topics", mediaTopic === "all", () => { mediaTopic = "all"; route(); }),
      Object.keys(D.topics).filter((t) => topicCounts[t]).map((t) =>
        chip(D.topics[t], mediaTopic === t, () => { mediaTopic = t; route(); }, topicCounts[t])));
    const topicBox = el("details", { class: "filter-wrap", open: mediaTopic !== "all" || window.matchMedia("(min-width: 640px)").matches },
      el("summary", null, "Topics"), topicChips);
    refresh();
    return [el("div", { class: "lede" }, el("h1", null, "Media"), countHost), typeChips, stanceChips, topicBox, listHost];
  }

  /* ---------- method ---------- */

  function renderMethod() {
    const m = D.meta;
    const ck = D.checks || {};
    const rows = [["Bill quotes", m.quotes + " of " + m.quotes + " match the PDF text word for word."]];
    if (ck.points) rows.push(["Key points", ck.points.cited + " of " + ck.points.total + " carry a passage from the bill, matched the same way."]);
    if (ck.inference) {
      const i = ck.inference;
      rows.push(["Summary review", i.stale ? "The saved review predates changes to its inputs. Re-check pending." :
        i.supported + " of " + i.total + " statements have a saved supported verdict; " + i.flagged + " remain flagged and " + (i.unchecked || 0) + " are unchecked. " +
        (i.cached_only ? "Saved results were reconciled with the current wording; the fresh Sonnet review is unfinished. " : "") +
        "This check covers section summaries, key points and selected comparison cells. It does not verify all site prose or establish legal accuracy."]);
    }
    if (ck.quotes) {
      const q = ck.quotes;
      const parts = [q.verified + " of " + q.total + " found on the cited page by script."];
      if (q.browser) parts.push(q.browser + " more read on the page in a browser, where the site refuses scripts.");
      if (q.near) parts.push(q.near + " found with small differences in wording.");
      if (q.unreachable) parts.push(q.unreachable + " on pages that could not be opened.");
      if (q.unverifiable) parts.push(q.unverifiable + " from video, where only the title can be read.");
      parts.push("Checked " + S.formatDate(q.checked) + ".");
      rows.push(["Quotes from the web", parts.join(" ")]);
    }
    if (ck.links) {
      const l = ck.links;
      const parts = [l.ok + " of " + l.total + " answered a script."];
      if (l.blocked) parts.push(l.blocked + " refuse scripts" + (l.browser ? "; " + l.browser + " of those opened in a browser." : "."));
      if (l.error) parts.push(l.error + " gave no answer.");
      parts.push(l.dead + " dead. Checked " + S.formatDate(l.checked) + ".");
      rows.push(["Links", parts.join(" ")]);
    }
    return [
      el("div", { class: "lede" }, el("h1", null, "Method"), el("p", { class: "facts" }, "Data as of " + S.formatDate(m.as_of))),
      el("section", { class: "block prose" },
        el("h2", null, "Bill text"),
        el("p", null, "Draft " + m.draft_id + ", " + m.pages + " pages, posted by Senate EPW on " + S.formatDate(m.released) + ": ",
          ext(m.source_pdf, "EPW copy"), ", ", ext(m.mirror_pdfs[0], "Energy Committee copy"), "."),
        el("p", null, "A cite such as 44:6 is page 44, line 6 of that PDF. A word split across printed lines is indexed on the line where it begins; the final word of a cited passage may continue onto the next line. The draft has no bill number, and its page numbers will change when the sponsors post a new text.")),
      el("section", { class: "block prose" },
        el("h2", null, "Summaries"),
        el("p", null, "Drafted with Claude and reviewed with AI assistance against the bill and from the two earlier bills: ",
          m.prior_bills.map((b, i) => [i ? "; " : "", ext(b.url, b.label)]), ". A green rule marks AI-written text. It is not legal advice.")),
      el("section", { class: "block prose" },
        el("h2", null, "Timeline, people, media"),
        el("p", null, "Collected by web search on " + S.formatDate(m.as_of) + ". A person's or group's position is taken from its own statements."),
        el("p", null, "Reddit could not be searched by script or by browser; it has no entries.")),
      el("section", { class: "block" },
        el("h2", null, "Checks"),
        el("dl", { class: "versus" }, rows.map((r) => [el("dt", null, r[0]), el("dd", null, r[1])]))),
      el("section", { class: "block prose" },
        el("h2", null, "Data"),
        el("p", null, ext(m.repo_url, "Data and scripts on GitHub"), " · ", el("a", { href: "llms.txt" }, "Plain-text digest")))];
  }

  /* ---------- router ---------- */

  const TITLES = { overview: "Overview", bill: "BAAJA", compare: "Compare", timeline: "Timeline", people: "People", media: "Media", method: "Method" };
  let lastPath = null;

  function route() {
    const hash = location.hash.replace(/^#\/?/, "");
    const parts = hash.split("/").map((p) => { try { return decodeURIComponent(p); } catch (e) { return p; } });
    const tab = TITLES[parts[0]] ? parts[0] : "overview";
    let nodes;
    let keepScroll = false;
    if (tab === "bill" && parts[1] === "sec") { nodes = renderSection(parts[2], parts[3], parts[4]); keepScroll = Boolean(parts[3]); }
    else if (tab === "bill" && parts[1] === "search") nodes = renderSearch(parts.slice(2).join("/"));
    else if (tab === "bill") nodes = renderBillIndex();
    else if (tab === "compare") nodes = renderCompare(parts[1]);
    else if (tab === "timeline") nodes = renderTimeline();
    else if (tab === "people") nodes = renderPeople();
    else if (tab === "media") nodes = renderMedia();
    else if (tab === "method") nodes = renderMethod();
    else nodes = renderOverview();
    fill(view, nodes);
    view.className = "view view-" + tab;
    document.querySelectorAll(".tabs a").forEach((a) => {
      if (a.getAttribute("data-tab") === tab) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
    const h1 = view.querySelector("h1");
    document.title = (h1 && tab !== "overview" ? h1.firstChild.textContent + " · " : "") + "Permitting Reform";
    const path = location.hash;
    if (path !== lastPath && !keepScroll) window.scrollTo(0, 0);
    lastPath = path;
  }

  document.addEventListener("keydown", (ev) => {
    const tag = (ev.target.tagName || "").toLowerCase();
    const input = document.getElementById("search-input");
    if (ev.key === "/" && input && tag !== "input" && tag !== "textarea" && !ev.metaKey && !ev.ctrlKey) {
      ev.preventDefault();
      input.focus();
    }
  });

  /* Theme: the system's unless the reader picks one; the choice lasts for the session. */
  const toggle = document.getElementById("theme-toggle");
  function paintToggle() {
    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    toggle.setAttribute("title", dark ? "Light theme" : "Dark theme");
    toggle.setAttribute("aria-pressed", dark ? "true" : "false");
    toggle.setAttribute("aria-label", dark ? "Light theme" : "Dark theme");
  }
  toggle.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { sessionStorage.setItem("pr-theme", next); } catch (e) { /* not persisted */ }
    paintToggle();
  });
  paintToggle();

  const asof = document.getElementById("footer-asof");
  if (asof) asof.textContent = "Data as of " + S.formatDate(D.meta.as_of);

  window.addEventListener("hashchange", route);
  route();
})();
