---
id: PBI-012
title: "Test and coverage trend, cost per work item and per agent type (features 5 and 7, FR-114–FR-116, FR-119, FR-120)"
status: Done
change_class: standard
depends_on: [PBI-004]
allowed_areas: ["exporters/**", "tests/test_*.py", "site/**", "tests/page.test.mjs"]
blocked_areas: []
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-012 — Test and coverage trend, cost per work item and per agent type (features 5 and 7, FR-114–FR-116, FR-119, FR-120)

---

## Description

Test and coverage trend, cost per work item and per agent type (features 5 and 7, FR-114–FR-116, FR-119, FR-120). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`. They also touch `exporters`.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-114, FR-115, FR-116, FR-119, FR-120:

- [x] **AC-79** When a code-writer run's result contains "664 tests green", the collector shall record test count 664 on that run. *(FR-114.)*
- [x] **AC-81** When two runs of one project naming PBI-001 have effective usage 100 and 50, the page shall show 150 for that project's PBI-001. *(FR-119.)*
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

**Closed out 2026-09-19.** Merged as `312e2f5` (PR #34, squash; landing resolved squash (declared) / observed squash, one parent, level `record`).

- **AC-79** — `tests/test_derive.py` `StatedFigures` reads 664 from 'DONE. 664 tests green; …'; `tests/test_export_sessions.py` records `tests: 664` on a code-writer run's document. Re-run on merged main `8bd2621`: backend 410 OK.
- **AC-81** — page check "AC-81: two runs of one project naming PBI-001 with effective usage 100 and 50 show 150 for that project's PBI-001" (`tests/page.test.mjs:1924`). Re-run on `8bd2621`: all 139 page checks passed.
- **Close-out** — canonical run bound to `51acfa5`: 823 passed / 0 failed (run-report PASS). Accounted `code-review-r1` GO with one Low follow-up, CR-012-1 (stated-figure parsing crossing a line break), dispositioned follow-up and fixed as chore `chore/cr-012-1-stated-counts`.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-19 | Accounted `code-review-r1` GO, 1 Low (CR-012-1, follow-up) |
| No-self-merge gate | always | passed 2026-09-19 | PR #34 squash-merged `312e2f5` under the owner's standing merge authorisation |
| BOARD-tidy gate | always | passed 2026-09-19 | Done write, ledger deregistered |
