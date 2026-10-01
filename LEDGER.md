# LEDGER.md: Dated Session Scar Tissue

> Raw chronological archive of per-session learnings. **Not loaded by default.**
> Load when you want the original context behind a rule, or when mining for patterns.
>
> New entries land here. When an entry states a rule that generalizes, fold the rule into the
> right thematic file ([CLAUDE.md](CLAUDE.md), [TESTING.md](TESTING.md), [DATA.md](DATA.md),
> [SECURITY.md](SECURITY.md), [GIT.md](GIT.md), [AGENTS.md](AGENTS.md), [DESIGN.md](DESIGN.md))
> and leave the dated entry here as provenance. Entries are append-only; the thematic files are the
> live source of truth.

---

### 2026-07-17 session additions (a ten-client deliverable marathon)

- **A citation URL is a guessed identifier unless copied verbatim.** Writing
  sources for facts already verified, a plausible slug reconstructed from
  memory of the story is fabrication with extra steps: four caught in one
  session (an industry-press article, a company announcement, and a personal tool's
  Pages URL that does not exist). Copy the URL from the research output or
  the fetch that proved it; when only an outlet+date is held, say so instead
  of minting a slug. Instruct research agents in the same words.
- **For content about an external company, run a verify-or-kill fact pass
  BEFORE authoring, and treat killed assumptions as the pass's main product.**
  Seven consecutive bounded agents (12-20 dated facts, first-party preferred,
  verbatim-URL rule, knowns+gaps fed in, file written by the agent to disk)
  each killed at least one spec assumption — a dead flagship project, a
  headquarters with no hardware in its state, three stale headline numbers on
  the company's own posting. Authoring first would have shipped all of them.
- **Quoting someone else's register does not exempt the banned-word linter.**
  Copy pasted or paraphrased from a company's own posting/marketing smuggled
  "unlock", "harness", "leverage", "elevate" past drafting five times; the
  linter owns every string regardless of who wrote it first, and that is the
  point of making it a test.
- **Shared skin/asset files leak identity across per-recipient builds.** One
  stylesheet carrying every company's motif selector shipped rival names into
  every bundle until the byte-level build guard blocked it. Scope
  per-recipient blocks between strip markers and have the emitter keep only
  the recipient's own. Corollary: alias families in a guard list
  (a client's short name and its full brand name) must be slug-normalized as one family or a
  bundle flags itself as its own rival.
- **Agents deliver their file at the END; a limit-killed agent leaves
  nothing.** Two of nine fact agents, launched nearest a suspected usage
  limit, died with zero output; the seven launched early all landed.
  Frontload delegation in a window, keep two-at-a-time, make the deliverable
  a file the agent writes itself, and save the launch prompt to disk so a
  dead agent is relaunchable verbatim.
- **A machine-checkable copy rule beats a style guide.** "Every hook is seven
  words or fewer; the sentence beside it carries a digit" is grep-able, and
  it caught five real number-free claims that read fine to the eye.

### 2026-08-03 session additions (a dev-tooling dashboard: session-kickoff track)

- **Budget subagent fan-outs against the shared session limit.** The account's
  usage window is one pool shared by the main loop and every subagent — a
  5-agent review batch launched right after a 4-agent research batch killed 4
  of 5 mid-run (`session limit · resets 12pm`). Cap concurrent heavy subagents
  at ~2–3, stagger phases (research → synthesize → then more), use a cheaper
  model tier for miners/researchers when depth allows, and don't launch a
  second heavy batch on the heels of a big one. Corollary: tell research
  agents whether they may sub-spawn — an agent given an N-domain scope will
  sometimes fan out on its own and stall waiting on children.
- **When two subagent reports contradict each other, read the source — and
  read it anyway for any claim that shapes the design.** One explorer
  correctly said a route only re-arms a task; the planning agent said it
  dispatches (which would have put a security guard on the wrong route).
  Thirty seconds of reading the 40-line route settled it. Subagent reports
  are testimony, not evidence: spot-verify every load-bearing claim (what
  guards what, what runs when) in the main loop before it becomes a plan step.
- **A one-off Node script that imports a repo's dependencies must resolve
  from inside the repo.** An ESM `.mjs` dropped in a temp/scratch dir dies
  with `ERR_MODULE_NOT_FOUND` — ESM resolves `node_modules` from the *script
  file's* location, and `NODE_PATH` doesn't apply. Either place the script
  inside the repo, or run `node -e '<CJS source>'` from the repo's cwd (CJS
  `require` in `-e` resolves from the working directory).

### 2026-07-26 session additions (a dev-tooling dashboard: telemetry track: plan → 6 epics → 2 review rounds)

- **"A failure that looks like success" is a bug class worth reviewing for by
  name.** One session shipped six instances, none caught by a passing suite:
  health that described the *incremental slice* rather than the source (so an
  overnight no-op badged a populated card "no data"); a sync that stamped its
  success timestamp after failed writes; a route that returned a `mirror`
  status field the UI never read (green "Synced" over a tick where every
  remote write failed); a bidirectional-reopen rule that re-closed the issue
  in the same pass because the push held a snapshot taken before the pull
  wrote; an importer that overwrote the hand-written body it had just
  imported; and a collector whose caught failure was discarded by its own
  background caller. The shared shape: the *unhappy* path produces output
  indistinguishable from the happy one. Ask of every status, health, and sync
  surface — "what does this render when the underlying thing failed?" — and
  make the answer different from what it renders on success.
- **Validate a hand-rolled binary/format parser against the real corpus
  before trusting it, using records that carry both the parsed field and an
  authoritative one.** Decoding Apple's `attributedBody` typedstream, the
  check was 4,000 messages having BOTH `text` and `attributedBody`: 4,000
  exact matches, 0 mismatches — *then* the decoder was wired in. Same pass
  measured how much of the corpus actually needs it (52% of messages have a
  NULL `text`), which reclassified it from "fragile fallback" to "the main
  path". Both numbers are cheap to get and change the design; guessing either
  would have shipped a channel that silently captured half of everything.
- **Never run a production build while a dev server is running on the same
  tree.** `npm run build` rewrites `.next/` under the live server, which then
  500s on every route with `Cannot find module './NNN.js'` — and the error
  points at webpack internals, not at what you did. Cost two debugging
  round-trips before the cause was obvious. Build in a separate checkout, or
  stop the dev server first and restart it after.
- **A test fixture root must mirror the real directory layout whenever the
  code derives a sibling or parent path from it.** A bare
  `mkdtemp()`-created root made a `dirname(root)/archived_sessions` lookup
  resolve to `$TMPDIR/archived_sessions` — shared mutable state across every
  test run on the machine. Build the fixture as `<tmp>/<the-real-parent>/…`
  so derived paths stay inside the sandbox.
- **A default parameter pointing at a real user path will have your tests
  reading the developer's own data.** Two readers defaulted to
  `~/.gemini/antigravity-cli` and `~/Library/Messages/chat.db`; any test that
  didn't override them was silently reading a personal message archive.
  Every test passes an explicit, deliberately non-existent path — and the
  parameter is absolute rather than derived, so a fixture can't accidentally
  resolve onto the real one.
- **A first run that scans everything must not block a page load — background
  it and report that it's running.** A cold usage ledger took 83 seconds to
  build (270 large session logs, none skippable by the mtime pre-filter),
  which is a broken dashboard on a phone. Answering from the store as it
  stands (~140ms) plus a `collecting` flag lets the UI say "still reading"
  instead of rendering a cold store's zeros as fact — which is the same
  looks-like-success trap above.
- **`gh api repos/O/R/pulls/N/reviews` rejects an inline comment on a file
  that isn't in the diff** — 422 `Path could not be resolved`, with no
  indication of which path. Anchor review comments only on changed files;
  when the observation is about an unchanged consumer, comment on the changed
  producer and describe the consumer in the body.

---

### 2026-07-27 session additions (a community-impact site refresh: 3-dimension data refresh, zero agents)

- **A source's own index/listing page, fetched directly, beats keyword search for
  recency.** Three rounds of broad WebSearch ("new facility announcement July
  2026", company-scoped, then domain-scoped to one news site) all came back with
  nothing new — every lead, cross-checked against the already-loaded
  dataset, turned out already-tracked or a stale recap of months-old news
  recirculated by aggregators. WebFetching that news site's own channel-listing
  URL directly (`?term=construction-site-selection`) returned an actual dated
  headline list (27 Jul, 23 Jul, 22 Jul…) and surfaced 3 real new leads plus one
  significant data-quality catch that no keyword query reconstructed. A search
  snippet samples a source; a listing enumerates it — when a keyword-search pass
  for "anything new?" comes back stale or empty, try the source's own
  index/channel page before concluding there's nothing new.
- **A headline's loaded word ("ban", "recall", "moratorium") is not the
  underlying action — check for the entity's own denial before trusting the
  word.** A jurisdiction's zoning-ordinance change (removing by-right approval,
  adding case-by-case review) was seeded as a permanent "ban" twice, both times
  wrong: the jurisdiction's own FAQ stated outright that a blanket moratorium was
  "not legally permissible" and described only the procedural change. The second
  occurrence of an identical failure shape is the signal it's worth a standing
  rule, not just a one-off fix — outlets reach for the strong colloquial word for
  a looser regulatory change than what actually happened.
- **A full 3-dimension data refresh (new records, status re-checks, new-lead
  scouting; ~20 records added/changed across 4 files) ran entirely on direct
  WebSearch/WebFetch/Bash — zero subagents.** ~60 web searches over the session
  made it look fan-out-shaped, but every sub-question was either a targeted
  search or a mechanical check against already-loaded local data (a one-line
  `python3 -c "import json; ..."` against the seed file caught duplicate leads —
  a specific county's site, a "5 new named-project sites" recap — before any research
  time was spent on them). Task *size* doesn't imply agent count; check whether
  the sub-questions are enumerable and answerable inline first, per the existing
  "on an implementation session in a repo you already understand, the default
  agent count is zero" rule above — the same holds for a research-heavy refresh
  in a *dataset* you already control.

### 2026-07-27 session additions (a resource-tracking app: 6-phase plan → 3 review rounds)

- **A module constant used as a DEFAULT ARGUMENT binds at import, so it can
  never be monkeypatched.** `def write(path: Path = QUEUE_PATH)` looks
  configurable and isn't: `monkeypatch.setattr(mod, "QUEUE_PATH", tmp)` changes
  the module attribute while the already-bound default keeps pointing at the
  real file. A test that *believed* it had redirected the write put real rows
  in `data/state/`. Take `path: Path | None = None` and resolve
  `path = path or QUEUE_PATH` inside. The tell: a test asserts on a tmp file
  and passes because the assertion is weak, while the side effect lands
  elsewhere — check `git status` after a test run that writes.
- **A fixture too small to distinguish the right answer from the wrong one
  makes the test a rubber stamp.** An excerpt function was supposed to return
  text around the first difference; it returned `body[0:240]` regardless. The
  test passed for a year of nobody noticing because its fixture page was 20
  characters — so the head of the page *was* the diff. Any test of
  "find/extract the interesting part" needs a fixture where the interesting
  part is NOT at offset zero, and an assertion that the boring part is
  **absent** (`assert "boilerplate" not in out`), not just that the interesting
  part is present.
- **Keyword/phrase classification over prose cannot see negation, and real
  corpora negate constantly.** "No formal NOV or consent order issued" contains
  both "consent order" and "civil penalty", so a rules classifier recorded two
  matters where *nothing happened* as penalised consent decrees. Strip negated
  clauses (sentence-scoped, so a negation can't swallow a real finding
  elsewhere) before matching, and treat tense the same way — an application's
  *proposed* mitigation read as an *imposed* permit condition. Both failure
  modes produce confident, plausible, wrong data rather than an error.
- **When a parse error hits an append-only file, never fall back to "treat as
  empty" and then write.** `except JSONDecodeError: existing = []` followed by
  a write silently destroys the entire history the file exists to preserve.
  Quarantine the damaged bytes (`path.replace(path + ".corrupt")`), warn, and
  write atomically (temp + rename) so an interrupted run can't produce the
  corrupt file in the first place. The paired test must assert the **prior**
  records survive — asserting only that the new record was written tests around
  the bug.
- **Redact secrets at the throw site, not the log site.** HTTP libraries put
  the full request URL in exception messages, so a key in a query string
  reaches every downstream formatter — and callers can't redact what they don't
  know is sensitive. Catch where the secret is still in scope:
  `raise RuntimeError(str(exc).replace(key, "***")) from None`. Pair it with a
  test that serializes the whole error object and greps for the literal key.
- **One assertion kills the entire dead-link class: every internal `href="#x"`
  has a matching `id="x"` in the generated output.** Referential-integrity
  checks over the *data* prove an id resolves in the registry; they say nothing
  about whether the renderer emitted the anchor. Three record kinds were
  advertising anchors no builder wrote, one already shipping as a dead link,
  and the data-level integrity suite was green throughout.
- **An unverifiable integration should fail loudly, not silently succeed.**
  Without an API key the exact request shape couldn't be tested — but the
  original code sent a human bill number where an internal numeric id was
  required, got an error payload back, and (having never validated response
  status) hashed it into a *stable* fingerprint. The watcher would have
  reported "no change" forever while looking healthy. When you can't verify,
  spend the effort on making failure unmistakable: validate the envelope, match
  identifiers exactly, and raise. Unverified-but-loud beats
  unverified-and-silent.
- **Reviewers concentrate on new machinery, and that's the signal to
  trust.** Across three rounds, 15 defects: 11 in the one new subsystem, ~0 in
  the large data/refactor surface. Two were masked by tests written in the same
  session. If a subsystem's characteristic bug is one where broken and working
  look identical from outside, most of its tests should exist to tell those two
  states apart — not to confirm the happy path.

### 2026-07-27 session additions (a content/news site: X sweep, bookmark/list harvest, dedup against existing data)

- **On a JS-virtualized feed (X/Twitter and similar infinite-scroll SPAs), programmatic `scrollTo`/`scrollBy` moves the scroll position but does not reliably trigger the next-page fetch — and a tight loop of it plus dispatched synthetic events can freeze the tab.** `window.scrollY` updated correctly after `scrollTo`, so the position change looked like it worked, but the article count stayed flat across repeated bottom-of-page checks; a follow-up loop mixing `scrollTo` + dispatched `WheelEvent`s in quick succession caused a 45s `Runtime.evaluate` timeout and left the tab blank. Real input — a `computer`-tool scroll action (actual wheel/touch event) — loaded new content reliably every time. When automating a feed you don't control the source of, prefer simulated real input over programmatic scroll APIs; treat a stalled DOM count as a signal to switch input methods, not to loop harder on the same one.
- **Before treating a manually-sourced find as new data, check whether the automated pipeline already has it.** A curated sweep of a person's X bookmarks + a topic list surfaced ~8 strong-looking candidates; cross-checking by keyword against the existing dataset showed 6 of 8 were already ingested under different record ids by the RSS/search-API scrapers, just not recognized by name. Skipping that check would have produced duplicate records with different ids for the same event — the cheap keyword grep before authoring anything is what caught it.

### 2026-07-28 session additions (a regulatory-filings microsite: news refresh: 4-phase plan → self-review → bot review, zero agents)

- **A section added to a module but not to its explicit export list is silently `undefined`, and tests over it pass vacuously.** A new `tracks` registry went into a `data.js` IIFE but not into its `return {…}` list. Nothing errored: every consumer read `D.tracks || {}`, so the UI rendered zero cards with a clean console, and the new tests iterated the same empty object and passed over nothing. It surfaced only by counting rendered DOM nodes. Two rules follow. **Adding a section to a file with an explicit export/`__all__`/index list is two edits, never one.** And **any test that iterates a collection must first assert the collection is non-empty** — otherwise "no items violated the rule" is indistinguishable from "there were no items," and the suite reports green over a missing feature.
- **Derive cache-busting tokens from content; "keep this in sync by hand" is not a mechanism.** A static site shared one hand-typed `?v=20260715a` across five assets. A PR replaced three of them and nobody bumped it (caught by a bot reviewer, not by me or the 98-test suite). The obvious cost is a stale site; the real one is **skew** — one shared token means a partial cache hit can serve an old `app.js` against a new `data.js`, which renders as a data-shape bug that reproduces for users and never locally, i.e. nearly undiagnosable from a bug report. Fix structurally: generate each token from that file's own content hash and add a sync test (the same generated-output-plus-assert contract already used for derived files). Per-asset hashes also stop an unchanged 491KB bundle from being re-downloaded because a stylesheet moved. Corollary: **a literal can never hold its own file's content hash** — anything needing its own version must read it at runtime (e.g. off its own `<script src>`).
- **When you work around a caching artifact locally, immediately ask whether the deployed artifact has the same bug.** I hit browser-cache staleness three times in one session (a served file was correct while the loaded page was old), diagnosed it each time as local environment noise, and worked around it with a different hostname. The identical failure was sitting in the shipped HTML the whole time and a reviewer found it. A local cache workaround is a *signal about the cache strategy*, not a quirk to route around.
- **One piece of state, one source of truth — especially for URL state.** A "pending" handoff variable existed to carry a deep-linked filter to a not-yet-rendered panel. It was cleared in only one of the two code paths that consume it, so on the other path it went stale and later outvoted the live value when writing the URL. Result: the address bar said one filter while the page showed another, so a copied permalink pointed somewhere wrong. Reproduced in a browser, invisible to the test suite. If a URL is authoritative, nothing may quietly outvote it; a handoff variable must be cleared wherever it is consumed, or it must not be read outside the handoff.
- **A gov/institutional site that bot-blocks its HTML often leaves its JSON API and full-text endpoints wide open.** A federal publication site 302s automated HTML fetches to an unblock page, but its documented JSON API and full-text endpoints return clean data with no auth. That single discovery converted a "snippet-only, unverifiable" claim into a primary-source-confirmed one and settled a date discrepancy. **Before recording a source as unreachable, try its API, its full-text endpoint, and its own listing/index URL** — "the HTML is blocked" is not "the source is blocked."
- **Review your own diff adversarially before anyone else does, and still expect the independent reviewer to find the class you were blind to.** A deliberate self-review found a real correctness bug (the URL/state divergence above) that the suite missed. An independent bot reviewer then found a P1 in a layer I had not been thinking about at all (deploy/caching) — the one place my attention never went, because I had spent the session inside application logic. Both are worth doing: the self-review catches what you can see, and the point of the second reviewer is the blind spot, so weight its findings *higher* when they land outside the area you were working in.

### 2026-07-28 session additions (same session, SEO + deploy half: audit → per-docket pages → Search Console)

- **Audit what is actually SERVED, not what the head tags claim.** A site's SEO basics all looked correct (canonical, robots, JSON-LD, sitemap, OG description) while the served HTML carried **113 words**: the app shipped six empty panels and JavaScript filled them. Googlebot renders JS on a second, budget-limited pass; Bing, most LLM crawlers and every social unfurler largely do not. **Strip scripts and noscript from the raw HTML and count the words before concluding anything about a site's SEO** — the head tags describe intent, the body is what gets indexed. Baking a real summary from the same data source took it to ~1,700. That is progressive enhancement rather than cloaking as long as the baked text is a strict subset of what the app renders, comes from the same source, and is never hidden from users.
- **A JS app with hash-routed tabs is ONE indexable URL.** A fragment is not a separate URL to a search engine, so every section competes for a single result and nothing can rank for its own identifier. If sections have distinct, substantial content, they need real URLs. Generating them is cheap when the content already exists as data; the thing that makes bulk page generation backfire is duplicate content, so assert that every generated page has a distinct title, description and body.
- **A declared capability with no backing asset fails silently.** `twitter:card=summary_large_image` was set with **no `og:image` at all**, so every share on X, Slack, LinkedIn and iMessage unfurled blank, and nothing in any test or local check would ever surface it. Whenever a tag, manifest or config *declares* something (a card type, an icon, a schema), verify the referenced asset exists and matches the declared dimensions.
- **When two generators write the same file, one must own the whole output or the sync test lies.** A page generator emitted HTML, then a separate asset-stamping pass rewrote it, so "what the generator emits" no longer equalled "what is committed" and the regeneration check failed. Fix: the page generator calls the stamper itself, so its output is final and byte-comparable. Any "regenerate and diff" contract silently breaks the moment a second pass touches the artifact.
- **Generate whole, don't patch, anything that enumerates.** A sitemap patched by regex kept its stale entries when new pages appeared. Regenerating the entire file from the data means a new page cannot be silently omitted, and a test that walks every listed URL and asserts it resolves catches the reverse (a listed page that does not exist).
- **Third-party verification always reads PRODUCTION, so branch work cannot satisfy it.** Search Console ownership verification and sitemap submission both fetch the live site; on GitHub Pages that is the default branch, so an unmerged branch is invisible no matter how correct it is. The same is true of domain verification, webhook callbacks, OAuth redirect URIs and link previews. **Check what is actually deployed before starting any external verification flow** — the deploy is a prerequisite step, not a detail, and discovering it mid-flow means stopping to ask for a merge decision you should have surfaced first.
- **A freshly submitted sitemap reads "Couldn't fetch"; that is the pre-processing state, not an error.** Verify the artifact independently instead of chasing the status: HTTP 200, `application/xml`, valid XML, expected URL count, and a `robots.txt` that does not block (a 404 robots.txt means allow-all). Then re-check in a few days. Related: on a GitHub Pages *project* site, `robots.txt` is served under the project path, but crawlers only read the user-site root, which the project repo does not control — so that file documents intent and little else.
- **Never delete an ownership-verification artifact.** Removing the file or meta tag a service verified with un-verifies the property, and the failure is silent: reporting simply stops. Commit two independent methods so an accidental deletion of one is survivable, and write the "do not delete" note next to the artifact, not in a chat log.

### 2026-07-29 session additions (a content/news site: news front page + priority+ nav + theme rework + X list sweep)

- **A "not connected" integration is a transient state to retry, not a capability to declare unavailable.** The Chrome extension returned "not connected" twice, so I reported the X list harvest as blocked and shipped the rest — and the user's response was, correctly, to just try again. It connected on the first retry and the harvest ran fine. The tool's own error text said retries usually fix it; I read the second failure as confirmation instead of as a second sample. **Before telling someone a capability is unavailable, retry at least once after doing other work** (time passing is itself the fix for most connection races), and if you still report it blocked, say what you retried. Declaring a blocker is a claim about the world, and it costs the user a round-trip to disprove.
- **Summing `offsetWidth` across flex children silently under-counts by the gaps.** A nav fit calculation summed nine item widths to 718 against a true `scrollWidth` of 733 — `gap: 2px` × 8, plus one more before the trailing control. The result was a layout that declared "it fits" while overflowing by ~18px, visible only in a narrow band of viewport widths. Measure the *container's* `scrollWidth`, which includes gaps, and re-read it after each removal rather than subtracting a cached child width — otherwise the gap that disappears with the child is unaccounted for too, and the gap value gets a second home to drift from the CSS.
- **A JS layout that measures "how much room do I have?" must not let the measured element's own content feed the answer.** A flex item with `flex: 1 1 auto` sizes from its content, so measuring it *while over-full* returns the width it is demanding, not the width it will settle at: `clientWidth` read **317px** with everything inline and **289px** once items moved out and the siblings relaxed. The layout fitted itself to a width that no longer existed. Use a **zero** flex-basis (`flex: 1 1 0`) so the element's width is a pure function of its siblings, pin those siblings with `flex: 0 0 auto`, and give any element whose width you *reserve* `flex: 0 0 auto` as well — an unpinned reserve element is already squeezed at the moment you sample it. Related: `offsetWidth` reads **0** on a `[hidden]` element, so unhide before sampling.
- **When behaviour depends on which element is "current", sweeping one page across many states proves nothing — sweep the pages too.** A priority+ nav restored overflowed items by appending them back onto the list, which only reproduces the authored order when every survivor sits at the front. Because the collapse step pins the *current page's* item, every page whose item wasn't first ended up permanently reordered. The home page's item is index 0, so appending happened to be correct there — and a four-width sweep **on the home page** saw nothing. The dimension I varied was the one that didn't matter. Ask what the code branches on, and vary *that*.
- **An audit is only as good as the set it ran over, so state the set, not just the result.** A theme rework was contrast-checked against `--bg` and `--surface` and shipped claiming "every (token, background) combination". Adding the third surface — the one carrying hover states and a control's caret — exposed four sub-AA pairs, and widening the set turned up a fifth on a background I *had* checked but with a token I hadn't paired against it. A reviewer reproduced my published numbers exactly, which proved the method and said nothing about the coverage. **Write the enumeration into the doc** ("every text token against all three surfaces") so the next person can see what was skipped; a bare "verified" is unfalsifiable.
- **Browser-automation panes don't paint a backgrounded tab, so `requestAnimationFrame` never fires and every geometry read comes back 0.** A probe run straight after `navigate` reported `innerWidth: 0` and an unmoved layout — indistinguishable from "my resize handler is broken." Taking a screenshot first forces the tab to render and the same probe then returns real numbers. **Screenshot before measuring anything layout-dependent, and never debug a rAF-driven feature off a pre-paint read.** The same class of confusion appears the other way round: after a *programmatic* scroll, that pane's screenshots came back blank while the DOM was demonstrably fine — so when the two disagree, trust the DOM query and re-verify, don't redesign against the picture.
- **A defect gets promoted by a redesign long before it gets fixed by one.** 93% of a dataset's records carried a scraper's internal config id where a publication name belonged. It had been wrong for the life of the project and nobody noticed, because it rendered in a dense card footer. Moving that same field under a lead headline made it the first thing you read. **When you promote a field to a more prominent position, audit its actual values across the whole corpus first** — layout changes are a cheap, reliable way to discover which of your data has been quietly wrong.
- **A fallback that preserves the broken behaviour re-arms the bug you just fixed.** The fix wrote `source.publication || source.id`, which keeps a misconfigured feed producing valid records — and silently reproduces the exact defect if anyone adds a feed without the new field. Nothing downstream caught it: the validator had no per-entry schema for that config file, so it would pass CI *and* the deploy gate. A `||` fallback onto the old wrong value is a decision to fail silently; either warn at the seam or validate the field.

### 2026-07-29 session additions (a personal CRM app: six-phase build from a plan, then eight live-feedback rounds, zero agents)

- **A metric that counts absences as successes climbs toward 100% and is worse
  than having none.** A card-recognition accuracy report compared each parsed
  field to what the human confirmed — and counted a field *neither side had* as
  a correct read. Most business cards carry three or four of the five tracked
  fields, so the score would have shown near-perfect recognition while every
  title was being misread. The denominator has to be "cases where either side
  had a value"; absences get their own column, not a free point. Ask of any
  agreement rate: **what fraction of the denominator is two empty strings
  matching?** If it is most of them, the number is measuring sparsity, not
  quality.
- **"Not measured" and "zero" must render differently in a metric, not just in
  a UI.** The existing zero-versus-missing rule (§ Frontend) is usually written
  about a count chip; the same disease in a *score* is worse, because 0% reads
  as "always wrong" and sends someone off rewriting a component that was never
  broken. An unjudged field renders `—`.
- **Killing a script that mutates files in a loop leaves the file mutated.** A
  mutation-testing harness that writes a sabotaged file, runs the suite, then
  restores the original was `TaskStop`ped mid-run; the restore never executed
  and a button silently vanished from the shipped markup. It was only caught by
  a `grep -c` in an unrelated check. Two fixes, both cheap: restore in a
  `finally`, and **verify the tree after killing any long-running task that
  writes** (`git status` plus a grep for a marker you know should be there).
  Backgrounding such a script is itself the risk — prefer running mutations in
  the foreground, or over a scratch copy of the tree.
- **A test that consumes a shared fixture makes its neighbours order-dependent.**
  Four browser tests worked through a queue seeded with one incomplete record;
  the first test to complete it removed it from the queue and the rest found
  nothing. Passing individually, failing together, and the failure reads as a
  timeout rather than as a fixture problem. Any test that *changes the state it
  selects on* should create its own subject.
- **A control that lives inside one view is a control nobody finds.** A camera
  capture button was placed in the Review queue — the view for confirming
  parses — and reported as "no camera control" by someone sitting on the main
  list. The fix was moving it into the persistent chrome. **Where a control
  lives is part of whether it exists**; "it's under X" is a bug report about
  information architecture, not a user error.
- **Edit state keyed by field name alone cannot address one of N rows.** A page
  storing `editing = "title"` works while exactly one record is on screen and
  makes in-place editing impossible *in principle* the moment a view lists
  several. It surfaced as "not clickable" on a review queue. The shape to reach
  for from the start is `{recordId, field}` — retrofitting it touched every
  editor, every commit path, and every keyboard handler.
- **A regex date parser needs a word boundary on its day group or it eats the
  year.** `"March 2025"` parsed as March **20th**, then resolved the year by
  guesswork, producing a confidently wrong date that nothing downstream can
  detect. `(\d{1,2})\b` fails against "2025" (a digit follows) and hands the
  digits to the year alternative; without the boundary it matches "20" happily.
  This is the same family as the existing "native parsers silently succeed with
  a wrong value" rule, in hand-rolled form: **a parser that returns a plausible
  wrong answer is strictly worse than one that fails**, so date extraction gets
  a sanity window and reports how it read each value.
- **Restart the server before believing a bug report about a missing feature.**
  Three separate "the control isn't there" reports in one session were a dev
  server left running across a code change, serving the previous bundle. The
  existing content-hash cache-busting rule is the structural fix and was
  applied; the operational half is that **a long-lived local server is a stale
  artifact in exactly the same way a CDN is**, and checking it costs one
  restart.
- **A "verify or it's a guess" pass is worth running against your own parser
  output, not just against external data.** Seven sentences run through a
  freshly written NL parser exposed four bugs in one pass — a year read as a
  day, a title swallowing its employer, a pronoun captured as a venue, a
  clause boundary off by one preposition. None were visible from reading the
  code; all were obvious in the output table. **Print the parse of a dozen real
  inputs before writing a single test**, then write the tests against what you
  learned.
- **Agent/token retrospective: zero subagents, zero workflows, correctly.** A
  session spanning ~15 commits, six planned phases, five late feature requests
  and ~710 tests used no delegation at all. Every question was about code being
  written in the same session (answered by `grep`, by reading the file, or by
  running it), and the single external unknown — three job-board API contracts
  — was four `curl` probes, not a research harness. That probe was also the
  session's highest-value 60 seconds: it refuted a documented assumption
  (empty-list versus 404 semantics) and caught a third vendor encoding dates as
  epoch milliseconds where the others send ISO. **A fan-out would have returned
  summaries of the same four responses at 30× the cost and with the contract
  details flattened out.**

### 2026-08-03 session additions (a regulatory-filings microsite: news refresh + commissioner-quote audit + regional-entity comment views)

- **A fuzzy/normalized text matcher must be fed identically-preprocessed input on both sides — reusing one blindly, without checking its exact calling convention, can silently invert its correctness.** Diffing five commissioners' statements across six near-identical regulatory orders, a naive substring check flagged seven sentences as "tailored" that were actually the same text, just interrupted differently by a footnote citation each order's own OCR page-break splices in. Reusing the project's own LCS-tolerant matcher fixed most of that — except I passed it a raw, un-normalized source string on one side where every existing caller passed pre-normalized text, which reintroduced near-universal false positives (a "verified identical" quote came back "not found"). Caught only by manually re-checking a sentence I already knew, by eye, was identical. **Before trusting a shared matcher/diff utility, read one existing call site and match its exact preprocessing, not just its function signature.**
- **A citation field that points at ONE representative location inside a block is not the same as a field marking the block's boundary — verify a field's semantics against the raw source before using it as a structural delimiter.** `commishPages[key]` looked like "where this commissioner's statement starts" (used that way for months) and is actually "the page of the one pull-quote chosen to represent them," which can sit mid-statement — a 5-page statement's headline quote sat on page 3 of 5. An extraction script built on the wrong assumption cross-contaminated one commissioner's text with the next one's. Fixed by locating the real boundary independently (searching the source for the section's own header text) rather than trusting the citation field.
- **A correction that hedges an overclaim can itself be a smaller, still-wrong overclaim — re-verify the walk-back with a repeatable check, don't trust that "hedged" means "now safe."** A prior fix had changed a site's claim from "identical across all six orders" to "largely common, with some per-order tailoring" after an ad hoc check found mismatches — but that check had the same false-positive bug above, so the hedge itself overstated how much tailoring actually existed (true answer: 4 of 5 commissioners fully verbatim; the 5th with exactly one footnote, on one order). The fix: promote the one-time manual finding into a permanent, reusable regression tool instead of trusting corrected prose to stay correct.
- **In a live, human-owned browser (not an isolated automation instance), tab focus can drift between calls for reasons outside your control — pin every call to an explicit tab_id once more than one tab might be open.** A JS-execution call meant for a government docket-sheet tab landed on the user's Gmail inbox instead — focus had shifted between an `open_url` call and the next command. No further action was taken on it and nothing beyond inbox summary text was read, but it could as easily have been a banking or health tab, and reading it at all was already outside the task's scope. `list_tabs` → match the target by URL → pass that literal tab_id on every subsequent call; never rely on an implicit "current tab."
- **An idempotent generator's "insert this block if missing" needs a matching "replace it if present," or the block goes stale forever after the first successful run — and the replacement must consume the block's own leading whitespace, or a second run compounds the indent.** A page generator's `if (!html.includes(MARKER)) insert` had no else-branch, so a dated field baked into that block silently froze at its first-ever value on every later regeneration — a staleness bug hiding behind a script that exits 0 every time. (Distinct from the already-logged "two generators write one file" bug below: this was one generator, incomplete on its own re-run branch.) First fix attempt replaced only the inner content, leaving the OLD indent in front of the new block's own indent, so a second run visibly doubled it — caught by explicitly testing the generator against its own just-generated output before trusting it fixed.
- **A "find differences" check that only looks in one direction passes vacuously on an empty or truncated comparison — the same failure mode as an untested collection, one level up.** The commissioner-statement diff tool above compared each other order's text against the baseline order for anything NEW, but never checked the reverse (does every baseline-order sentence still appear over there?) — an independent PR review caught that a failed extraction (an empty or truncated statement) would produce zero "novel" entries and report success, unguarded against exactly the failure the tool existed to catch. Fixing it surfaced real value beyond the fix itself: the reverse pass found a genuine extraction-boundary bug (a footnote continuing past a commissioner's signature line was truncated along with the real signature) that the one-directional version could never have found no matter how long it ran. Any "compare A against B for differences" check needs both directions, plus a sanity floor on each side's size — the same rule as "assert the collection is non-empty" before trusting a loop found nothing wrong with it.

### 2026-08-08 fleet telemetry audit (14-day window: 2026-07-25 → 2026-08-08, 163 sessions, 13,093 deduped requests)

Full-window measurement of every `~/.claude/projects/**/*.jsonl` (deduped by
`requestId`), run because 5-hour-window budget exhaustion and error'd-session
resumes had become chronic. Numbers below are weighted tokens
(input ×1, 5m-TTL cache writes ×1.25, 1h-TTL writes ×2.0, reads ×0.1, output ×5).

- **Total: 624.6M weighted.** Cost structure: **65% cache reads** (4.03B raw ×0.1),
  **26% cache writes** (85M raw, of which **86% were 1h-TTL writes billed at 2×**),
  **10% output**, ~0% fresh input. The bill is almost entirely
  `round-trips × context size` — output is a rounding error.
- **The legacy measurement method (flat ×1.25 on `cache_creation_input_tokens`)
  now understates spend ~10%** (570M vs 625M) because writes moved to 1h TTL at 2×.
  Correct method: split `usage.cache_creation.ephemeral_5m_input_tokens` ×1.25
  from `ephemeral_1h_input_tokens` ×2.0. Caveat: transcripts log usage only for
  *successful* requests, so failed/interrupted attempts' streaming cost is
  invisible — every retry number here is a floor.
- **Context concentration: 72 of 163 sessions crossed 200K max context and
  carried 91% of all spend (570.7M).** ≥400K: 25 sessions, 75%. ≥600K: 13
  sessions, 54%. ≥800K: 5 sessions, 29%. Peaks: 926K / 923K / 916K — worse than
  the 880K peak that motivated the "~200K then /clear" rule on 2026-08-04.
  The rule is correct and almost never followed.
- **Autonomous sessions ran 100–287 round trips per human prompt** (e.g. 437
  requests over 3 prompts at 865K ctx; 343 over 2 at 537K). At 600K context each
  round trip costs ~60K weighted in cache reads alone, so one "go do the thing"
  prompt late in a big session costs 6–17M weighted. The same run in a fresh
  small session is ~8× cheaper. The `round-trips × context` rule generalizes
  from commit turns to *every* autonomous run.
- **Limit-hit economics, measured across 45 session-limit hits on 6 of 14 days**
  (2026-08-03 alone: 15 hits; 2026-07-25: 12):
  - Resumed **<1h** after the hit: median re-pay **2K** tokens (n=11) — the 1h
    prompt cache was still alive; resume was nearly free.
  - Resumed **>1h** after: median re-pay **150K**, total **7.96M raw re-written**
    (≈16M weighted at 2×) across n=32 resumes.
  - The limit error message contains the decision input: `resets 12:10am`.
    **If reset − now < ~1h, park and resume at reset (cache survives). If
    longer, the cache dies before the window reopens — start fresh sessions
    except the single one holding irreplaceable state.**
  - Repeated window slams also compounded upward: one **weekly** limit hit
    ("You've hit your weekly limit · resets 10pm") and one "Credit balance is
    too low" (extra usage exhausted). No window-timing trick fixes those.
- **The wall-slam pattern:** on limit days, 10–20 sessions were live in the
  final hours (2026-07-25 13:00: 36.4M across **17 sessions** in one hour;
  2026-08-03 18:00: 18.4M across **18**). A fleet that wide guarantees the wall
  lands mid-flight for everything at once; each stranded session then pays the
  >1h resume tax above. 56 of 94 active hours had 2+ concurrent sessions.
- **Network/API errors are rare and cheap in the moment, expensive overnight.**
  9 network events (ENOTFOUND / connection-closed / timeout) in 14 days.
  Auto-retry seconds later: re-pay ≈0 (cache alive). But sessions left error'd
  and resumed 1.6–16h later re-paid 62K–402K each — a full context re-write at
  2×, same economics as a limit-hit resume. An error'd session >1h old should
  be treated exactly like a rate-limited one: fresh session unless its state is
  irreplaceable. Also seen: 3 OAuth-revoked auth failures mid-fleet (re-login,
  ~1M re-paid across the interruptions).
- **Model mix: Opus-5 carried 53% of weighted spend (330M), Sonnet-5 31%
  (192.6M), Fable-5 14% (88M), Opus-4.8 2%, Haiku 0.3% (2M).** Subagents were
  9.1% of spend (consistent with the 8.1% measured 2026-08-04) — so per-subagent
  model selection barely moves the bill; the **main-loop model** is the lever.
  Bulk autonomous/mechanical work on Sonnet, Opus/Fable reserved for
  design/judgment turns, is the largest budget lever after context size.
- **Correction-shaped user messages in 14 days: 3.** Process friction is not the
  problem; economics are. (One of the 3 was the recurring "don't look like
  Claude slop" aesthetic note already codified in DESIGN.md.)
- Audit script kept as [tools/audit_sessions.py](tools/audit_sessions.py)
  (edit the `CUTOFF`/`NOW` dates at the top, run
  `python3 tools/audit_sessions.py out.json`; writes per-session, retry-cost,
  and error-event JSON dumps beside the output path). Re-run it before the next
  economics claim rather than reasoning from these frozen numbers.

### 2026-09-24 sweep: Sep 7-24, 254 Claude sessions, 5 Codex sessions, 18 days

Context behind the 2026-09-24 additions to CLAUDE.md, AGENTS.md, DESIGN.md (§ 11.1.3), DATA.md, TESTING.md, GIT.md and SECURITY.md, and behind the slopcheck registry.

- **Scale.** 747 Claude transcript files opened; 566M weighted tokens and 14.2M output tokens in the 18-day digest; 22 usage-limit hits, 86 sessions past 200K context. Top projects by weighted tokens: a job-search site (123M), an MCP server (84M), a second MCP server (48M), a tariff tracker (46M), a brownfield tracker (41M).
- **Typed messages: 176, not 1,535.** Hook-spawned security reviews (150), diff-cap notices (250), about 40 scheduled-task prompts, and skill bodies were counted as typed. `mine_sessions.py` filters them now; the digest's own count had been 405.
- **Twenty-one messages complained about the writing**, most of them quoting the tells. The registry now holds 153 entries: 80 typed by the user, 73 from review tables, sibling checkers and slop-fixing commits. The Aug 30 checker caught 17 of the 153 (11%; 11 of the 80 the user typed); the new rules alone catch 107 (69%; 56 of the 80), and the rest are held by the registry only. That 69% is in-sample, since the rules were written from these phrases; the out-of-sample check is the 22 held-out variants in `HELD_OUT`, all caught by their rule alone.
- **Sibling checkers held rules the base checker lacked.** A documentation project's `check_writing.py` had `maxim-voice`, `inanimate-protagonist`, `definition-by-negation`, `welded-crossref`, `antithesis-parallel`, `vague-virtue-word` and two idiom rules, each added after a real miss on 2026-08-28..30. All are now in the base checker. Its default run had also scanned a `research/raw` tree of forum threads and reported hundreds of FAILs written by strangers.
- **The checker is still finding the flagged phrases.** Run over the sibling projects' published docs after the registry landed, it found "organized by data domain, not by laboratory" and "provenance envelope" still on an MCP site the user flagged on Sep 11. It found "this pitch" three times in a pitch-deck data file. It also found "Terms every town can see" and "From pilots to a public fleet" in decks the Sep 16 review had not reached.
- **The second half of the loop was empty.** The registry was filled from the transcripts; running `harvest_tells.py` over the same window afterwards found three uncaught user phrases, two of them typos of entries already registered, which is the closed-loop check that the harvest sees what a person sees.
- **Unrelated to prose, worth keeping:** a hand-typed `$22,000 per kW` from the wrong reactor archetype; five fabricated moratorium records with real bill numbers; a 29-PR pile from two scheduled scrapers; a pasted API key in a transcript; ten review agents lost to the usage limit with zero findings.

### 2026-09-24 second pass: the Codex archive, and Aug 21 to Sep 7

Context behind the second set of 2026-09-24 entries in AGENTS.md, DESIGN.md (§ 8.14, § 12.36), GIT.md, SECURITY.md and TESTING.md, and behind the two dated corrections in CLAUDE.md.

- **Why a second pass.** The morning sweep's digest could not see Codex. `mine_sessions.py` read `~/.codex/sessions/`, which held 4 files from July, while every later session sat in `archived_sessions/` (148 files). With the archive, Sep 7-24 had 36 Codex sessions and 96 of the window's 271 typed messages. The Claude sessions of Aug 21 to Sep 7 also fell between the Aug 21 and Sep 24 sweeps.
- **What was read.** The main session read every typed message since Aug 21 (684: 481 Claude, 203 Codex). Two Sonnet agents read redacted per-turn extracts, one of 43 Codex sessions (182 KB, 268K tokens) and one of 83 Claude sessions from Aug 21 to Sep 7 (443 KB, 349K tokens). Every quote the new entries cite was grepped back to its extract. One agent's date was wrong (the heartbeat loop ran on Sep 2, not Sep 21) and one count was high (four same-prompt Codex sessions on Sep 12, not five); both were corrected, and the same-prompt sessions were left out because they match Codex's run-several-attempts feature as well as a mistake.
- **Measured along the way.** Codex cut `AGENTS.md` at 32,886 bytes in 7 projects. `claude.coauthor` is absent from the Claude Code 2.1.281 binary, and the `attribution` setting it does read is unset in `~/.claude/settings.json`. `find -newermt` and `timeout` both work on this machine.
- **Movement since July.** Continuation nudges: about 95 per 30 days in the 2026-07-07 count, 12 in the 34 days since Aug 21. Sessions past 200K context: 43% all-time, 34% for Sep 7-24, 25% this week. Usage-limit hits: 22 in Sep 7-24, 15 of them in the last seven days.
- **The new top repeated ask** is syncing with work from other sessions (branches, PRs, uncommitted changes, "I made edits in another session"): 68 of 684 typed messages, split about evenly between Claude and Codex. No skill covers it; see backlog.
- **Considered and not added:** a second accessor that skipped a state gate (one instance, close to TESTING.md's roster-trap rule); a validator reusing the code-under-test's spatial index (one instance); `httpx` treating `params={}` as "replace the query" on a redirect (a library quirk that belongs in the `government-data` skill); text extraction over screenshots (one instance, already in the harness prompt); agent turns ending in an offer and drawing a bare "yes" (38 of 337 turns ended in an offer, 5 drew a bare yes, all at real permission boundaries).

### 2026-09-24 evening: can a repo carry only AGENTS.md?

- **Method.** Headless Claude Code 2.1.281 runs in throwaway git repos holding one `AGENTS.md` with marker words, file tools disabled (`--disallowedTools Read,Bash,Glob,Grep,...`), `--output-format json` for usage. A run with no loaded file and a run with a loaded file differ by the file's tokens; a skipped file differs by the prompt text only.
- **Results.** Outside `~/Projects`: loaded (both markers returned). Inside `~/Projects`, with identical flags: not loaded, at 4K, 39K, 41K and 115K characters and for filler text alike; the parent `~/Projects/CLAUDE.md` is the only difference. The first probe of the evening allowed tools and returned the right word by reading the file; that result was reported to the user as confirmation and then withdrawn.
- **Tokenizer.** The 115 KB base `CLAUDE.md` loaded outside `~/Projects` added 38,763 prompt tokens on `claude-opus-5-5[1m]`: 2.97 bytes per token.
- **Other tools, from their own binaries.** Codex: `project_doc_max_bytes = 32768`, `.agents/skills` known. Antigravity's bundled docs: `GEMINI.md` / `AGENTS.md` / `.agents/rules/*.md` walked up to the repo root, skills under `.agents/`, machine-wide customizations in `~/.gemini/config/`. Claude Code's `.agents/skills` strings belong to its Cursor-config importer, not its skill loader.
- **Trailers.** `git log --all` over 22 repos in `~/Projects`: 502 AI `Co-authored-by` values, every one `noreply@anthropic.com`; the rest were the user's own addresses (13) and one dependabot.
- **Probe residue.** Six headless sessions left small transcripts under `~/.claude/projects/` (folders named for `.agents-md-probe`, `.tok-probe-*` and the scratchpad); they will appear in the next digest as one-message sessions.
