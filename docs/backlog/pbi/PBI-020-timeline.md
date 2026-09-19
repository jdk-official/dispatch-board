---
id: PBI-020
title: "Timeline view (feature 9; FR-101 filled, FR-122–FR-124)"
status: Proposed
change_class: standard
depends_on: [PBI-003, PBI-004]
allowed_areas: ["site/**", "tests/page.test.mjs", "exporters/**", "tests/test_*.py"]
blocked_areas: []
conflict_group: page
conflict_risk: High
requires_spec: true
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-020 — Timeline view (feature 9; FR-101 filled, FR-122–FR-124)

---

## Description

Timeline view (feature 9; FR-101 filled, FR-122–FR-124). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `site/**`, `tests/page.test.mjs`, `exporters/**`, `tests/test_*.py` (run start and end times in the store docs). It also touches `exporters`.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-101, FR-122, FR-123, FR-124:

- [ ] **AC-83** When two runs ran from 10:00 to 10:20 and from 10:05 to 10:30, the timeline shall draw their bars overlapping between 10:05 and 10:20. *(FR-122.)*
- [ ] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

- (written at close-out)

---

## Notes

**Row Q-1 — the owner chose option (b) on 2026-09-19**, "Docs chore after merge": the build leaves `CLAUDE.md` alone and a docs chore corrects the `runs.manual` store-path row straight after the merge. `merge_allowed_by_agent` set true under the owner's standing merge authorisation of 2026-09-12.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_spec: true`: refine a per-PBI spec from the parent spec and have it independently reviewed before any code is written.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | **passed 2026-09-12** | `docs/backlog/specs/pbi-020-timeline.md` revision 2. Round 1 **APPROVE-WITH-NOTES** (5 Medium, 3 Low) — all eight applied, none deferred; AC-T15, AC-T16 and AC-T17 added. Review: `docs/backlog/reviews/PBI-020/spec-review-r1.md`. **What the gate produced:** the spec found FR-123 unmeetable on today's document — `reject()` computes a per-refusal time at `derive.py:287-291` and `usage_doc` discards it, publishing only `firstAt` per window — so the spec adds an `at` list rather than narrowing the requirement, and the reviewer verified the sharing is genuine (both adapters gain the field through `derive.session_result`/`project_doc`). It also settled that runs with no `start` are never placed, never synthesized and never dropped, but listed "off the axis" with the count stated, with AC-T3 requiring 2 of 3 runs unplaced so it cannot pass vacuously. **F-5 is the systemic one:** NFR-22's visual check, which the parent spec makes mandatory for every page PBI, had no criterion and no verifying actor — the same gap PBI-009's gate found independently. Now AC-T17, naming the owner or a screenshot artefact. **Q-1 remains OWNER** and is *not* the PBI-005 defect: `blocked_areas` is empty, and the parent spec's docs grant is conditioned on a declared `docs` touch which PBI-020's row at `:256` does not carry (PBI-017 `:219` and PBI-018 `:220` do). Publishing `end` therefore makes `CLAUDE.md:38` wrong with no in-scope way to fix it — the owner adds `CLAUDE.md` to `allowed_areas` before the build, or pre-registers a docs chore. |
| External-review gate | false | pending | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
| BOARD-tidy gate | always | pending | |
