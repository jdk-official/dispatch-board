---
id: PBI-004
title: "Shared derivation module: extract the exporters' parsing and derivation into an importable module, behaviour unchanged"
status: Done
change_class: standard
depends_on: [PBI-001]
allowed_areas: ["exporters/**", "tests/test_*.py"]
blocked_areas: ["site/**", "local/**"]
conflict_group: exporters
conflict_risk: Medium
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-004 — Shared derivation module: extract the exporters' parsing and derivation into an importable module, behaviour unchanged

---

## Description

Shared derivation module: extract the exporters' parsing and derivation into an importable module, behaviour unchanged. Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `exporters/**`, `tests/test_*.py`; blocked `site/**`, `local/**`. There is no behaviour change: the existing suites stay green unchanged.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to the ACs this PBI names:

- [x] The PRD requirements named in the title are met, as firmed in this PBI's per-PBI spec (no PRD AC cites them directly). *Firmed below (2026-09-11, before the build started): this PBI has no per-PBI spec (`requires_spec: false`), so the worker firmed the criteria from the title, the parent spec (Key decisions: "All derivations live in one shared module under `exporters/`; the collector imports it, never re-implements it"; plan order item 2) and PRD FR-87 / C-21. They add no scope beyond the title.*
- [x] **D-1 One shared module.** A module (or package) named `derive` under `exporters/` holds the exporters' parsing and derivation:
  - from the session exporter: transcript record parsing, token and usage arithmetic, lane, verdict and kind classification, run linking, redaction, usage aggregation and skill-use counting;
  - from the board exporter: the spec, table, bullet and Later-list parsing, and build state;
  - from the catalogue exporter: the frontmatter and purpose parsing.

  It uses the Python standard library only (C-21).
- [x] **D-2 Importable by the collector.** `import derive`, with `exporters/` on `sys.path`, performs no I/O. It reads no config, prints nothing and never exits. Its derivation functions take parsed data (transcript records as dicts, file text as strings), not file paths, so PBI-019's incremental reader (FR-86, FR-87) can feed them records. File reading, config, git and gh calls, and writing `out/` stay in the exporters.
- [x] **D-3 Behaviour unchanged, suites unchanged.** The exporters import from `derive`. Every `main()` signature and every name the suites import or patch still exists on its exporter module, and a patch still takes effect: `export_sessions.parse_session`, `export_sessions.read_subagent`, `export_sessions.os.path`, `export_sessions.write_json` (imported by `export_catalogue`), `refresh.plan` and `board_config`. No existing test is edited; new tests may be added.
- [x] **D-4 Byte-identical output.** The three exporters' output is byte-identical before and after, run on the same frozen copy of the owner's real transcripts, config and repos, with the same `now` and the same stubbed `gh`.
- [x] **D-5 Direct tests.** A new `tests/test_derive.py` imports `derive` directly, not through an exporter. It tests its public functions on small inputs, and asserts that importing it touches no files.
- [x] Worker close-out: the three configured suites are green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`, `python -m unittest discover -s local/tests`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

Re-checked fresh at finalize on 2026-09-11, on merged `main` at `d10d9e6` (PR #14, squash).
- **Title / firmed criteria:** met through D-1 to D-5 below. The firming note above records how the criteria were set before the build.
- **D-1:** `exporters/derive.py` holds the session, board and catalogue parsing and derivation, standard library only. The round 1 and round 2 reviews (`docs/backlog/reviews/PBI-004/findings-r1.json`, `findings.json`) verified every moved function against the base code.
- **D-2:** `tests/test_derive.py` asserts that `import derive` opens no files, lists no folders, prints nothing and imports only the standard library. Its functions take parsed records and text, and the incremental-feed test shows earlier documents stay unchanged as records are added.
- **D-3:** no pre-existing test was edited (both reviews checked this), and the suites that patch `export_sessions.parse_session`, `read_subagent` and `os.path` pass.
- **D-4:** code-writer's before/after harness on a frozen copy of the owner's real data: 155 files in round 1 and 157 in round 2, 0 differences. Code review round 1 independently compared 155 files, 0 differences. At finalize, a real-data `refresh.py` with the new exporters planned no change to any session, run, project, catalogue or tab against the board pushed by the old exporters, apart from the git tab (the new commit) and the refresher session's own document.
- **D-5:** `tests/test_derive.py`, 26 tests, imports `derive` directly.
- **Close-out:** 300 / 89 / 90 passing on `d10d9e6`. The canonical run was bound to `333361b` (`run-report.json`, PASS). Code review round 2 GO.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | false | pending | |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-004/findings.json (round 2 GO; round 1 GO-WITH-CONDITIONS in findings-r1.json: one Medium, returned documents shared live state, fixed test-first; two Lows applied). Round 2's one Low, a stale comment, was reworded by the orchestrator before the canonical run. Canonical run 300 / 89 / 90 PASS, bound to `333361b` (run-report.json); cell-report.json CELL-DONE |
| No-self-merge gate | always | passed 2026-09-11 | PR [#14](https://github.com/jdk-official/dispatch-board/pull/14) from `pbi/PBI-004-shared-derivation` (commit `333361b`), squash-merged by the owner at 2026-09-11T19:35:50Z as `d10d9e6`. resolved_method squash (declared) / observed_method squash; level record |
| BOARD-tidy gate | always | passed 2026-09-11 | finalize: done-log entry and BOARD Done row written; close_check not run (`[closeout]` policy unset, so off) |
