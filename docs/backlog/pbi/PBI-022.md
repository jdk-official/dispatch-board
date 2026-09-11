---
id: PBI-022
title: "PRD re-baseline after project-first navigation and the plan-gate answers, with evidence for AC-84, AC-85 and AC-92"
status: In Review
change_class: trivial
depends_on: []
allowed_areas: ["docs/prd/**", "docs/backlog/evidence/**", "docs/brief/raw-notes.md"]
blocked_areas: ["docs/backlog/specs/**", "docs/backlog/BOARD.md", "docs/backlog/reviews/**"]
conflict_group: docs
conflict_risk: Low
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-022 — PRD re-baseline after project-first navigation and the plan-gate answers, with evidence for AC-84, AC-85 and AC-92

---

## Description

PRD re-baseline after project-first navigation and the plan-gate answers, with evidence for AC-84, AC-85 and AC-92. Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `docs/prd/**`, `docs/backlog/evidence/**`, `docs/brief/raw-notes.md` (the one "public on GitHub" line); blocked `docs/backlog/specs/**`, `docs/backlog/BOARD.md`, `docs/backlog/reviews/**`.

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, row 16):

- [x] **AC-R1** PRD revision 3 shall describe the tree after project-first navigation as its baseline: Part A re-baselined and the supersession table resolved.
- [x] **AC-R2** The re-baseline shall record every decision made since PRD revision 2:
  - every PRD A-row that a ledger row of this spec settles is marked settled, citing the row;
  - D-1 is superseded, because the repo is now private;
  - rows 5, 6 and 8 and PBI-017 with the owner's changes are recorded as decisions;
  - brief decisions 19 and 20 are recorded;
  - the brief's line "public on GitHub" is corrected.
- [x] **AC-R3** Evidence for AC-84, AC-85 and AC-92 shall be recorded under `docs/backlog/evidence/`, as demonstration notes or screenshots.
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

Each criterion was verified fresh at finalize on 2026-09-11, on merged `main` `fd7b926`, which contains PBI-022's squash commit `3c520d6`: `python -m unittest discover -s tests` ran 205 tests, OK; `node tests/page.test.mjs` passed all 44+5 = 49 checks.
- **AC-R1:** `docs/prd/dispatch-board.md` is revision 3. Part A describes the tree after project-first navigation and the Agent catalogue tab. The code review confirmed that every supersession-table row has a resolved status, and that no id from revision 2 was lost.
- **AC-R2:**
  - the settled A-rows cite their spec ledger rows (the reviewer checked all 28);
  - D-21 supersedes D-1;
  - D-19 to D-26 record the decisions made since revision 2, including brief decisions 19 and 20, rows 5, 6 and 8, and PBI-017 with the owner's changes;
  - brief line 16 now says the repo is private;
  - 48 of 48 brief citations were checked by script against the current brief.
- **AC-R3:** `docs/backlog/evidence/2026-09-11-prd-demonstrations.md` records AC-84, AC-85 and AC-92, each met, with its method.
- **Worker close-out:**
  - both suites pass on `fd7b926`;
  - the code-review gate passed: `docs/backlog/reviews/PBI-022/findings.json` GO-WITH-CONDITIONS, with all four findings resolved in `f3d80de`;
  - PR #3 was squash-merged by the owner at 2026-09-11T13:40:35Z, and the observed landing is squash, as declared (level: record).

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | false | pending | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | PR [#3](https://github.com/jdk-official/dispatch-board/pull/3), opened 2026-09-11 from `pbi/PBI-022-prd-rebaseline` (commit `f3d80de`), pushed via `git_rail.py`; squash (declared); waiting for the owner's merge, then `pbi-lifecycle finalize PBI-022` |
| BOARD-tidy gate | always | pending | |
