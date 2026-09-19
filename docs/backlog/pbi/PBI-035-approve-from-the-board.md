---
id: PBI-035
title: "Approve from the board: plan approval on the Spec tab, conditions acceptance on the Backlog, and the accepted-conditions overlay"
status: Proposed
change_class: standard
depends_on: [PBI-032, PBI-034, PBI-010]
allowed_areas: ["site/**", "tests/page.test.mjs", "exporters/derive.py", "exporters/export_board.py", "local/tabs.py", "tests/test_*.py", "local/records*", "local/tests/**"]
blocked_areas: ["local/server*", "local/answers*"]
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-035 — Approve from the board: plan approval on the Spec tab, conditions acceptance on the Backlog, and the accepted-conditions overlay

---

## Description

The Spec tab offers *Approve* and *Request changes* for a draft spec that is committed and clean, on the local adapter only. The spec tab record gains `status`, `specBlob` and `specCommitted`, read with git. The Backlog offers *Accept conditions* on an item whose derived state is `conditions`, and shows accepted conditions as a page overlay. Decomposed from the approved solution spec at the plan gate on 2026-09-19 (track 8, G-9).

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 6, approved 2026-09-19)

**Areas and design notes from the parent spec:**

allowed `site/**`, `tests/page.test.mjs`, `exporters/derive.py` and `exporters/export_board.py` (the spec tab's `status`, `specBlob` and `specCommitted`), `local/tabs.py` (the same two git values), `tests/test_*.py`, `local/records*` (the tab shape), `local/tests/**`. Blocked: `local/server*`, `local/answers*`. It also touches `exporters` and `local-app`.

**Decision record:** [ADR-0002](../../adr/0002-board-answers-count-as-the-owners.md).

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, revision 6, "PBI-035, approving on the page"; rows 34, 35, 50):

- [ ] **AC-Q1** When a project's spec `status:` is `draft` and its spec tab record says `specCommitted: true`, the Spec tab offers *Approve* and *Request changes*, with a note, on the local adapter only.
  - Beside them it shows the spec's path, revision and short blob id, and says the approval is of the committed text at that id (`git show <id>` prints it).
  - The spec tab record gains `status` (from the frontmatter), `specBlob` (`git rev-parse HEAD:<specPath>`) and `specCommitted` (both of AC-P1's checks pass). The git values are read beside the git tab's commands in `exporters/export_board.py` and `local/tabs.py`, under AC-P1's exit-code rule.
  - Beside *Approve* the tab lists every row still ASSUMED in the spec, High-impact ones first, since approving accepts their defaults (AC-P3).
  - While a spec is draft and committed, the Overview's "Needs attention" shows "<spec> revision <n> awaiting your approval".
  - The page posts the `specBlob` it rendered. After a submission it shows the first 8 characters of the answer id.
- [ ] **AC-Q2** A Backlog item whose derived state is `conditions` offers *Accept conditions*. Once accepted, it shows "Conditions accepted by you <time>", its "<id> review conditions" item leaves "Needs attention", and the shadow comparison counts it as done with accepted conditions. This is a page overlay: the derived state itself is unchanged.
- [ ] **AC-Q3** The design rules, page-test coverage and smoke-test rule of AC-B4 and AC-B5 apply. The smoke test runs on a throwaway server on another port with a temporary `local.answersPath`, and its evidence names both. `tests/page.test.mjs` covers the controls on the local adapter, their absence on the store adapter, and each failure path, and asserts they render no data through `md()`.
- [ ] Worker close-out: tier 4 (the tab record shape; row 44). The canonical run of the three configured suites is green on the head commit. The accounted code-review gate has passed.

---

## Evidence

- (written at close-out)

---

## Notes

**Authority.** Decomposed from the parent spec `docs/backlog/specs/dispatch-board.md`, revision 6. The owner approved it at the plan gate on 2026-09-19 with "Approve", answering the approval question that named commit `db14c0b` (spec blob `8fbdd3eba4a1042e2dfdbeb1689369eb015eb390`). The approval is recorded at `main` `e8f3f4e` (Plan-gate record). These criteria are the spec's own until the PRD re-baseline (row 47).

**Merge.** `merge_allowed_by_agent: true`, under the owner's standing merge authorisation of 2026-09-12 (`CLAUDE.md`, "Merge authority"), verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time."

**Sequencing.** It runs after PBI-032, PBI-034 and PBI-010, because the conditions half needs PBI-010's derived `conditions` state. Two overlaps are accepted by name, and whichever PBI lands second rebases: PBI-030 on `exporters/derive.py`, and PBI-039 on `exporters/derive.py` and `exporters/export_board.py`.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| External-review gate | false | n/a | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
| BOARD-tidy gate | always | pending | |
