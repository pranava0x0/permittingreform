# One entry point for every gate. `make check` needs no network.
PY := python3
PROSE := .test-artifacts/prose.md

.PHONY: check build test data quotes-bill quotes links infer prose design serve

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
	$(PY) tools/slopcheck.py --fail-on WARN site/index.html site/app.js site/search.js README.md REFRESH.md docs $(PROSE)

design:
	$(PY) tools/designcheck.py --fail-on WARN site/styles.css site/index.html

serve:
	$(PY) -m http.server 8766 --bind 127.0.0.1 --directory site
