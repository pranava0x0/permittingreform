/* Bill search and cite formatting. Pure functions: no DOM, so Node can test them. */
(function (root) {
  "use strict";

  var STOP = { the: 1, of: 1, a: 1, an: 1, and: 1, or: 1, to: 1, "in": 1, "for": 1, on: 1, by: 1, is: 1, be: 1 };

  function parseQuery(raw) {
    var q = String(raw || "").replace(/\s+/g, " ").trim();
    if (!q) return { type: "empty", raw: "" };
    var m = /^(?:sec(?:tion)?\.?|§)?\s*(\d{4})$/i.exec(q);
    if (m) return { type: "section", n: m[1], raw: q };
    m = /^(?:p\.?|pp\.?|page)\s*(\d{1,3})$/i.exec(q);
    if (m) return { type: "page", page: Number(m[1]), raw: q };
    var quoted = /^["“](.+)["”]$/.exec(q);
    var phrase = (quoted ? quoted[1] : q).toLowerCase();
    var tokens = [];
    if (!quoted) {
      phrase.split(" ").forEach(function (t) {
        t = t.replace(/^[^a-z0-9$]+|[^a-z0-9%]+$/g, "");
        if (t && !STOP[t] && tokens.indexOf(t) < 0) tokens.push(t);
      });
      if (!tokens.length) tokens = [phrase];
    }
    return { type: "text", raw: q, phrase: phrase, tokens: tokens, exact: Boolean(quoted) };
  }

  /* A token also matches its singular: "centers" finds "center". */
  function variants(tok) {
    return tok.length > 3 && tok.charAt(tok.length - 1) === "s" ? [tok, tok.slice(0, -1)] : [tok];
  }

  function hasToken(lower, tok) {
    var v = variants(tok);
    for (var i = 0; i < v.length; i++) if (lower.indexOf(v[i]) >= 0) return true;
    return false;
  }

  function hasAll(lower, tokens) {
    for (var i = 0; i < tokens.length; i++) if (!hasToken(lower, tokens[i])) return false;
    return tokens.length > 0;
  }

  function occurrences(lower, needle, out) {
    if (!needle) return;
    var at = lower.indexOf(needle);
    while (at >= 0) {
      out.push([at, at + needle.length]);
      at = lower.indexOf(needle, at + needle.length);
    }
  }

  /* Highlight ranges for a query in a text: the phrase where it occurs, else each token. */
  function ranges(text, query) {
    var lower = text.toLowerCase();
    var out = [];
    occurrences(lower, query.phrase, out);
    if (!out.length && !query.exact) {
      query.tokens.forEach(function (tok) {
        var before = out.length;
        occurrences(lower, tok, out);
        if (out.length === before) occurrences(lower, variants(tok)[variants(tok).length - 1], out);
      });
    }
    out.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
    var merged = [];
    out.forEach(function (r) {
      var last = merged[merged.length - 1];
      if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]);
      else merged.push([r[0], r[1]]);
    });
    return merged;
  }

  /* A window of text around the first highlight, with ranges shifted to match. */
  function snippet(text, rs, width) {
    width = width || 240;
    if (text.length <= width) return { text: text, ranges: rs, lead: false, trail: false };
    var first = rs.length ? rs[0][0] : 0;
    var start = Math.max(0, first - Math.floor(width / 3));
    if (start > 0) {
      var sp = text.indexOf(" ", start);
      if (sp >= 0 && sp < first) start = sp + 1;
    }
    var end = Math.min(text.length, start + width);
    if (end < text.length) {
      var back = text.lastIndexOf(" ", end);
      if (back > start + width / 2) end = back;
    }
    var shifted = [];
    rs.forEach(function (r) {
      if (r[1] > start && r[0] < end) shifted.push([Math.max(r[0], start) - start, Math.min(r[1], end) - start]);
    });
    return { text: text.slice(start, end), ranges: shifted, lead: start > 0, trail: end < text.length };
  }

  var lowerCache = null;
  function lowered(paras) {
    if (lowerCache && lowerCache.src === paras) return lowerCache.map;
    var map = {};
    Object.keys(paras).forEach(function (n) {
      map[n] = paras[n].map(function (p) { return p[3].toLowerCase(); });
    });
    lowerCache = { src: paras, map: map };
    return map;
  }

  /* Search every section: heading, summary, key points, and each paragraph of text. */
  function searchBill(sections, paras, query) {
    var low = paras ? lowered(paras) : {};
    var results = [];
    var passages = 0;
    sections.forEach(function (s, order) {
      var score = 0;
      var head = s.h.toLowerCase();
      var summary = (s.plain + " " + s.points.map(function (p) { return typeof p === "string" ? p : p.t; }).join(" ")).toLowerCase();
      var inHeading = head.indexOf(query.phrase) >= 0 || (!query.exact && hasAll(head, query.tokens));
      var inSummary = summary.indexOf(query.phrase) >= 0 || (!query.exact && hasAll(summary, query.tokens));
      if (inHeading) score += head.indexOf(query.phrase) >= 0 ? 50 : 30;
      if (inSummary) score += summary.indexOf(query.phrase) >= 0 ? 12 : 6;
      var hits = [];
      var plist = low[s.n] || [];
      var phraseHits = 0;
      var tokenHits = 0;
      for (var i = 0; i < plist.length; i++) {
        var lower = plist[i];
        var kind = lower.indexOf(query.phrase) >= 0 ? 2 : (!query.exact && hasAll(lower, query.tokens) ? 1 : 0);
        if (!kind) continue;
        if (kind === 2) phraseHits++; else tokenHits++;
        hits.push({ i: i, kind: kind, page: paras[s.n][i][0], line: paras[s.n][i][1] });
      }
      score += Math.min(30, phraseHits * 3) + Math.min(15, tokenHits);
      if (!score) return;
      hits.sort(function (a, b) { return b.kind - a.kind || a.i - b.i; });
      passages += hits.length;
      results.push({ n: s.n, order: order, score: score + s.imp, inHeading: inHeading, inSummary: inSummary, hits: hits });
    });
    results.sort(function (a, b) { return b.score - a.score || a.order - b.order; });
    return { query: query, passages: passages, sections: results };
  }

  function sectionForPage(sections, page) {
    for (var i = 0; i < sections.length; i++) {
      if (page >= sections[i].p1 && page <= sections[i].p2) return sections[i];
    }
    return null;
  }

  /* [p1, l1, p2, l2] -> "p. 44, lines 6 to 11" */
  function formatCite(c) {
    var p1 = c[0], l1 = c[1], p2 = c[2], l2 = c[3];
    if (p1 === p2) {
      if (l1 == null) return "p. " + p1;
      return l1 === l2 || l2 == null ? "p. " + p1 + ", line " + l1 : "p. " + p1 + ", lines " + l1 + " to " + l2;
    }
    return "p. " + p1 + (l1 == null ? "" : ", line " + l1) + " to p. " + p2 + (l2 == null ? "" : ", line " + l2);
  }

  function formatPages(p1, p2) {
    return p1 === p2 ? "p. " + p1 : "pp. " + p1 + " to " + p2;
  }

  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  function formatDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    if (!m) return iso || "Date not available";
    return MONTHS[Number(m[2]) - 1] + " " + Number(m[3]) + ", " + m[1];
  }

  var api = {
    parseQuery: parseQuery, ranges: ranges, snippet: snippet, searchBill: searchBill,
    sectionForPage: sectionForPage, formatCite: formatCite, formatPages: formatPages, formatDate: formatDate, months: MONTHS
  };
  root.PRSearch = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
