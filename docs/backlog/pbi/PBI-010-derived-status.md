---
id: PBI-010
title: "Work-item status derived from runs, shown beside the hand-kept state during a shadow period (feature 4, FR-113)"
status: In Progress
change_class: standard
depends_on: [PBI-004]
allowed_areas: ["exporters/**", "tests/test_*.py", "site/**", "tests/page.test.mjs", "projects/**"]
blocked_areas: []
conflict_group: page
conflict_risk: High
requires_spec: true
requires_external_review: true
pr_required: true
merge_allowed_by_agent: true
---

# PBI-010 — Work-item status derived from runs, shown beside the hand-kept state during a shadow period (feature 4, FR-113)

---

## Description

Work-item status derived from runs, shown beside the hand-kept state during a shadow period (feature 4, FR-113). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`, `projects/**` (read and annotate only; never delete a data file). It also touches `exporters` and `config`. Its spec defines:
- how derived state reaches the Backlog tab, given that `refresh.py` runs `export_board.py` before `export_sessions.py`;
- a shadow period showing derived and hand-kept state side by side, with differences flagged;
- hand-kept `review`, `open` and `commit` staying as overrides (row 15).

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-113:

- [ ] **AC-78** When the latest code-reviewer run naming PBI-001 in a platform-catalogue linked session has verdict `GO` and no hand-kept build state lists PBI-001, the platform-catalogue Backlog shall show PBI-001 as done. *(FR-113; A-32.)*
- [ ] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

- (written at close-out)

---

## Notes

**External-review gate — approved by the owner 2026-09-19**, answering "Approve the build?" with "Approve the build" (spec revision 3; the build ships in shadow mode, and the switch to derived status stays the owner's, row Q-3). **Row Q-2 — the owner chose option (b)**, "Docs chore after merge": the build leaves `CLAUDE.md` alone and a docs chore corrects it straight after the merge. `merge_allowed_by_agent` set true under the owner's standing merge authorisation of 2026-09-12.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_spec: true`: refine a per-PBI spec from the parent spec and have it independently reviewed before any code is written. `requires_external_review: true`: the owner must explicitly approve ("approve" / "proceed" / "go ahead") before implementation begins.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | **passed 2026-09-13** | `docs/backlog/specs/pbi-010-derived-status.md` revision 3. Round 1 **CHANGES-REQUIRED** (1 High, 3 Medium, 4 Low) — all applied; round 2 **APPROVE-WITH-NOTES** (4 Low), applied in revision 3. Reviews: `docs/backlog/reviews/PBI-010/spec-review-r1.md`, `-r2.md`. **The gate found the feature's central defect before any code existed:** the design reported *Agrees* exactly when no run named a work item, so a stale "Not started" read as agreement — the precise failure the feature exists to catch. Revision 2 added a distinct **No evidence** outcome, never counted as agreement, and the panel now states when the linked sessions were last active. Round 1 also confirmed the motivating case on real data: with session `7e0c4f3c` linked, every PBI merged without its build state being updated came out runs-ahead, each mapping to a real merged PR. OWNER rows: Q-1 (non-blocking), Q-2 (`CLAUDE.md` grant), Q-3 (blocks flipping the switch to `derived`, not the build), Q-17 (the AC-64 fixture — default: the orchestrator pre-registers a follow-up at finalize). |
| External-review gate | true | pending | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
| BOARD-tidy gate | always | pending | |
