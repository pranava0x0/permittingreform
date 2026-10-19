# Handoff: website news refresh, 2026-10-18 (branch jam/website-news-refresh-385939)

State at ~261K context. Research outputs in this directory: letters.json (done), congress.json (done), walled.json (orchestrator, Chrome), press.json (haiku agent running), x.json (haiku X/Chrome agent running).
Already edited: data/curation.json (letter metadata for the 222-group Oct 5 letter and the 73-group WELC letter).
Coder brief (Positions page spec) and agent contract live in the session scratchpad:
/private/tmp/claude-501/-Users-pranava-Projects-Permitting-Reform--claude-worktrees-congress-datacenters-lawsuits-media-c5a659/1a336e69-0e18-4027-a631-fb6f8ce37de7/scratchpad/{coder_brief.md,agent_contract.md}

Remaining steps:
1. When press.json and x.json land: sonnet synthesis -> data/research/{media,timeline,people}_extra.json + curation entries (letter objects for: governors 22, 200+ ESA letter, NARF+8 tribal Oct 9, 185 groups Oct 13, NAM 100+ Oct 14, Chamber Oct 15); update data/overview.json status.points only (never headlines; make infer is unavailable, OAuth expired).
2. python3 tools/integrate_research.py && python3 tools/build.py; set DATA_AS_OF="2026-10-18" in tools/build.py; make quotes; make links.
3. Opus coder with coder_brief.md (Positions page, #/positions, D.recent.positions counts on Overview). Coder owns site/, tests/, tools/check_data.py, data/positions.json only.
4. make check; serve with python3 -m http.server 8771 -d site; sonnet UAT in built-in browser at 375x812 (scroll/tap counts), 768, 1280, dark.
5. Docs: REFRESH.md learned, docs/agent-runs.md (letters 129K/66 calls/11 min; congress 130K/86 calls/12 min), DESIGN.md Positions page, README, backlog.md, issues.md.
6. Commit (no AI attribution), push, gh pr create against main; two codex review rounds (poll gh api repos/O/R/pulls/N/comments and gh pr view N --json reviews, several minutes each); fix; push; stop. Do not merge.
Facts to carry: governors count is 22 (EPW says 21); NGA CEO is Brandon Tatum; Capito says vote returns Nov 8 while floor log says Nov 9 cloture on H.R. 2347; Oct 23 NARF input deadline has no official source.
