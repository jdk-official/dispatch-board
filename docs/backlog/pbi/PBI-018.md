---
id: PBI-018
title: "Backlog shows future iterations: a 'Later' group of idea cards read from the spec's Future iterations list"
status: In Review
change_class: standard
depends_on: [PBI-017]
allowed_areas: ["exporters/export_board.py", "tests/test_export_board.py", "site/**", "tests/page.test.mjs", "CLAUDE.md"]
blocked_areas: ["local/**"]
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-018 — Backlog shows future iterations: a "Later" group of idea cards read from the spec's Future iterations list

---

## Description

Backlog shows future iterations: a "Later" group of idea cards read from the spec's Future iterations list. Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `exporters/export_board.py`, `tests/test_export_board.py`, `site/**`, `tests/page.test.mjs`, `CLAUDE.md`; blocked `local/**`. It also touches `exporters`.

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, row 16):

- [x] **AC-L1** The board exporter shall read each bullet under a spec's `### Future iterations (not planned)` heading into the backlog document as a `later` item. The item's title is the bullet's first bold span, and its description is the rest of the bullet with any leading colon removed.
- [x] **AC-L2** The Backlog tab shall show `later` items as a separate "Later" group of neutral idea cards below the PBIs. They shall never be counted in the PBI totals or in "Needs attention".
- [x] **AC-L3** A spec without that heading, such as platform-catalogue's, shall produce no Later group and no error.
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

Each criterion was verified fresh at finalize on 2026-09-11, on merged `main` `fd7b926`, which contains PBI-018's squash commit `25fa9e7`: `python -m unittest discover -s tests` ran 205 tests, OK; `node tests/page.test.mjs` passed all 49 checks.
- **AC-L1:** `tests/test_export_board.py` `FutureIterations` (8 tests) pass. The post-merge export of the real spec (`out/projectTabs/dispatch-board.backlog.json`) holds 9 `later` items, with titles from each bullet's bold span.
- **AC-L2:**
  - the page suite's section 9 (5 checks) passes: placement, escaping, neutrality, and exclusion from every count;
  - in the Browser pane, the page from this branch with the real data showed 9 idea cards below Work items;
  - the cards' tone bar resolves to `--rule-2`, not `--human`, and the page logged no errors.
- **AC-L3:** `test_spec_without_the_heading_has_no_later_items_and_no_error` passes, and the post-merge export of platform-catalogue's spec has `later: []` with nothing on stderr.
- **Worker close-out:**
  - both suites pass on `fd7b926`;
  - the code-review gate passed: `docs/backlog/reviews/PBI-018/findings.json` GO, with CR-018-01 (LOW) deferred to PBI-001 with its rationale;
  - PR #4 was squash-merged by the owner at 2026-09-11T13:40:23Z, and the observed landing is squash, as declared (level: record).

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | false | pending | |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-018/findings.json (GO; CR-018-01 LOW deferred to PBI-001 with rationale) |
| No-self-merge gate | always | pending | PR [#4](https://github.com/jdk-official/dispatch-board/pull/4), opened 2026-09-11 from `pbi/PBI-018-later-group` (commit `e4cec5c`), pushed via `git_rail.py`; squash (declared); waiting for the owner's merge, then `pbi-lifecycle finalize PBI-018` |
| BOARD-tidy gate | always | pending | |
