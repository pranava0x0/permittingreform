// Search and cite formatting, run against the built data: node --test tests/search.test.cjs
const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");

const S = require(path.join(__dirname, "..", "site", "search.js"));
global.window = {};
require(path.join(__dirname, "..", "site", "data", "core.js"));
require(path.join(__dirname, "..", "site", "data", "bill.js"));
const D = global.window.PR_DATA;
const B = global.window.PR_BILL;

function search(q) {
  return S.searchBill(D.sections, B, S.parseQuery(q));
}

test("a section number, a page and a phrase parse to different query types", () => {
  assert.deepStrictEqual(S.parseQuery("1106").type, "section");
  assert.deepStrictEqual(S.parseQuery("Sec. 2107").n, "2107");
  assert.deepStrictEqual(S.parseQuery("§ 1401").n, "1401");
  assert.deepStrictEqual(S.parseQuery("p. 50").page, 50);
  assert.deepStrictEqual(S.parseQuery("page 417").page, 417);
  assert.strictEqual(S.parseQuery("150 days").type, "text");
  assert.strictEqual(S.parseQuery("   ").type, "empty");
  assert.strictEqual(S.parseQuery('"remand, without vacatur"').exact, true);
});

test("stop words are dropped from token matching but kept in the phrase", () => {
  const q = S.parseQuery("right of first refusal");
  assert.deepStrictEqual(q.tokens, ["right", "first", "refusal"]);
  assert.strictEqual(q.phrase, "right of first refusal");
});

test("data center finds the ratepayer protection section first", () => {
  const r = search("data center");
  assert.strictEqual(r.sections[0].n, "2107");
  assert.ok(r.passages >= 5);
});

test("a plural query finds the singular in the text", () => {
  assert.ok(search("data centers").sections.some((s) => s.n === "2107" && s.hits.length > 0));
});

test("the travel sanction is found on page 54 of section 1106", () => {
  const r = search("travel more than 25 miles");
  assert.strictEqual(r.sections.length, 1);
  assert.strictEqual(r.sections[0].n, "1106");
  const hit = r.sections[0].hits[0];
  const para = B["1106"][hit.i];
  assert.ok(para[3].includes("travel more than 25 miles"));
  assert.ok(para[0] <= 54 && hit.page === para[0]);
});

test("an exact phrase in quotes does not fall back to scattered words", () => {
  const exact = search('"vacatur without remand"');
  assert.strictEqual(exact.sections.length, 0);
  const loose = search("vacatur without remand");
  assert.ok(loose.sections.length > 0);
});

test("a word that is not in the bill returns nothing", () => {
  assert.strictEqual(search("zeppelin").sections.length, 0);
});

test("highlight ranges are ordered, non-overlapping and inside the text", () => {
  const q = S.parseQuery("environmental review");
  const text = B["1106"].map((p) => p[3]).find((t) => t.toLowerCase().includes("environmental review"));
  const rs = S.ranges(text, q);
  assert.ok(rs.length > 0);
  let last = 0;
  for (const [a, b] of rs) {
    assert.ok(a >= last && b > a && b <= text.length);
    assert.strictEqual(text.slice(a, b).toLowerCase(), "environmental review");
    last = b;
  }
});

test("a snippet keeps its highlight inside the window", () => {
  const q = S.parseQuery("25 miles");
  const text = B["1106"].map((p) => p[3]).find((t) => t.includes("25 miles"));
  const sn = S.snippet(text, S.ranges(text, q), 160);
  assert.ok(sn.text.length <= 160);
  for (const [a, b] of sn.ranges) assert.strictEqual(sn.text.slice(a, b), "25 miles");
});

test("every section can be found by its own heading", () => {
  for (const s of D.sections) {
    const r = S.searchBill(D.sections, B, S.parseQuery('"' + s.h + '"'));
    assert.ok(r.sections.some((x) => x.n === s.n), s.n + " " + s.h);
  }
});

test("page lookup returns the section that contains the page", () => {
  assert.strictEqual(S.sectionForPage(D.sections, 55).n, "1106");
  assert.strictEqual(S.sectionForPage(D.sections, 417).n, "2302");
  assert.strictEqual(S.sectionForPage(D.sections, 2), null);
});

test("cites and dates are written out in the house style", () => {
  assert.strictEqual(S.formatCite([44, 6, 44, 11]), "p. 44, lines 6 to 11");
  assert.strictEqual(S.formatCite([44, 6, 44, 6]), "p. 44, line 6");
  assert.strictEqual(S.formatCite([54, 22, 55, 4]), "p. 54, line 22 to p. 55, line 4");
  assert.strictEqual(S.formatPages(31, 61), "pp. 31 to 61");
  assert.strictEqual(S.formatPages(123, 123), "p. 123");
  assert.strictEqual(S.formatDate("2026-09-30"), "September 30, 2026");
  assert.strictEqual(S.formatDate(""), "Date not available");
});


test("search finds a phrase present only in a structured key point", () => {
  const sections = [{n:"1", h:"Title", plain:"Summary", points:[{t:"special key point"}], imp:1}];
  const r = S.searchBill(sections, {"1":[]}, S.parseQuery("special key point"));
  assert.equal(r.sections.length, 1);
  assert.equal(r.sections[0].inSummary, true);
});

 test("hyphenated data-center queries find the ratepayer provision", () => {
  assert.ok(search("data-center").sections.some(s => s.n === "2107"));
});
