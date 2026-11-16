# One entry point for every gate. `make check` needs no network.
PY := python3
PROSE := .test-artifacts/prose.md

.PHONY: check build test data quotes-bill quotes links infer prose design serve final progress browser-quotes

check: build test data quotes-bill prose design
	@echo "make check: all gates green"

build:
	$(PY) tools/build.py

test:
	$(PY) -m unittest discover -s tests -q
	node --test tests/search.test.cjs

data:
	$(PY) tools/check_data.py

quotes-bill:
	$(PY) tools/check_quotes.py --bill-only

# Network: fetches every cited page (cached under data/cache/).
quotes:
	$(PY) tools/check_quotes.py

links:
	$(PY) tools/check_links.py

# Calls Claude Sonnet through the `claude` CLI, one request at a time.
infer:
	$(PY) tools/infer_check.py

prose:
	@mkdir -p .test-artifacts
	$(PY) tools/check_data.py --dump-prose $(PROSE) > /dev/null
	$(PY) tools/slop_writing.py --no-review --fail-on WARN site/index.html site/app.js site/search.js README.md REFRESH.md docs $(PROSE)

design:
	$(PY) tools/slop_design.py --no-review --fail-on WARN site/styles.css site/index.html

serve:
	$(PY) -m http.server 8766 --bind 127.0.0.1 --directory site

# Browser checks in order (perf, reader paths, UAT, click crawl), each logged under .test-artifacts/final/.
# Needs NODE_PATH pointing at a node_modules with playwright. The click crawl takes about 34 minutes;
# `make final SKIP=clicks` runs the three short ones.
final:
	$(PY) tools/final_checks.py $(if $(SKIP),--skip $(SKIP),)

# Is a `make final` run moving? Prints each step's state; exits 2 if it stalled or died.
progress:
	$(PY) tools/final_checks.py --status

# Reads every page `make quotes` could not reach in a scripted Chrome and tests its quotes.
# `make browser-quotes WRITE=1` records each quote it found in data/checks/browser.json.
browser-quotes:
	$(PY) tools/browser_quotes.py $(if $(WRITE),--write,)
