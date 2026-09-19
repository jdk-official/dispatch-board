---
id: PBI-032
title: "Answer from the board: Accept and Override on the Assumptions tab (local adapter only), answered and transcribed states (FR-131, AC-87)"
status: Proposed
change_class: standard
depends_on: [PBI-031]
allowed_areas: ["site/**", "tests/page.test.mjs"]
blocked_areas: ["exporters/**", "local/**"]
conflict_group: page
conflict_risk: High
requires_spec: true
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-032 — Answer from the board: Accept and Override on the Assumptions tab (local adapter only), answered and transcribed states (FR-131, AC-87)

---

## Description

The Assumptions tab gets *Accept* and *Override* on each row awaiting the owner, shown only when the page runs on the local adapter. A submission posts one answer to PBI-031's endpoint. The row then shows that it has been answered, and that it is awaiting transcription until the spec's ledger cites the answer id. Decomposed from the approved solution spec at the plan gate on 2026-09-19 (track 7, G-8).

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 6, approved 2026-09-19)

**Areas and design notes from the parent spec:**

allowed `site/**`, `tests/page.test.mjs`. Blocked: `exporters/**`, `local/**`. Its smoke test runs against a throwaway server (AC-B4).

**Decision record:** [ADR-0002](../../adr/0002-board-answers-count-as-the-owners.md).

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, revision 6, "PBI-032, answering on the page"; rows 30, 40):

- [ ] **AC-B1** On the Assumptions tab, each row awaiting the owner offers *Accept* (showing the row's chosen default) and *Override* (answer and note fields). They appear only when the local adapter is active and its marker carries a token. The store adapter shows no controls, only a line saying answers are given on the board on the PC, and has no write method (FR-64 holds on the artifact).
- [ ] **AC-B2** A submission sends one POST, disables the row's controls while it is pending, shows the server's refusal line on failure, and never retries by itself.
- [ ] **AC-B3** An answered row shows "Answered <time>: Accept/Override" and "awaiting transcription" until the spec ledger cites that answer id. Once answered, it leaves the "Awaiting your decision" counts.
- [ ] **AC-B4** The UI smoke test runs against a throwaway server on another port with a temporary `local.answersPath` (AC-A10), never the owner's server. Its evidence names the port and path used.
- [ ] **AC-B5** The rendering meets NFR-22. `tests/page.test.mjs` covers the controls on the local adapter, their absence on the store adapter, the token header and each failure path. It also asserts that the answer controls render no data through `md()`, only through `esc()`.
- [ ] Worker close-out: tier 3 (row 44). The canonical run of the three configured suites is green on the head commit. The accounted code-review gate has passed.

---

## Evidence

- (written at close-out)

---

## Notes

**Authority.** Decomposed from the parent spec `docs/backlog/specs/dispatch-board.md`, revision 6. The owner approved it at the plan gate on 2026-09-19 with "Approve", answering the approval question that named commit `db14c0b` (spec blob `8fbdd3eba4a1042e2dfdbeb1689369eb015eb390`). The approval is recorded at `main` `e8f3f4e` (Plan-gate record). These criteria are the spec's own until the PRD re-baseline (row 47). PRD AC-87 is still marked deferred there, and the re-baseline amends it to the answer record's fields.

**Merge.** `merge_allowed_by_agent: true`, under the owner's standing merge authorisation of 2026-09-12 (`CLAUDE.md`, "Merge authority"), verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time."

**Sequencing.** It runs after PBI-031, and can run in parallel with PBI-034, since they share no file. It waits for the `page` slot, which PBI-010 holds now. PBI-020 and PBI-039 are in the same group.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | pending | per-PBI spec |
| External-review gate | false | n/a | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
| BOARD-tidy gate | always | pending | |
