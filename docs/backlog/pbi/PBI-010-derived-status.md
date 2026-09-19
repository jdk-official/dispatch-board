---
id: PBI-010
title: "Work-item status derived from runs, shown beside the hand-kept state during a shadow period (feature 4, FR-113)"
status: Done
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

- [x] **AC-78** When the latest code-reviewer run naming PBI-001 in a platform-catalogue linked session has verdict `GO` and no hand-kept build state lists PBI-001, the platform-catalogue Backlog shall show PBI-001 as done. *(FR-113; A-32.)*
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

**Closed out 2026-09-19.** Merged as `f4e92ed` (PR #46, squash; landing resolved squash (declared) / observed squash, level `record`).

- **AC-78** — derivation half met. `exporters/derive.py` derives PBI-001 as done from the latest code-reviewer run's `GO` in a linked session when no hand-kept state lists it (`tests/test_derive.py`, `tests/test_export_sessions.py`), and the exported backlog document carries it. The page half, "the Backlog shall show PBI-001 as done", is **N/A — the owner chose "Hide it entirely" on 2026-09-19 after "Itts very complex and I don't understand it" — accepted by the owner 2026-09-19**. The page shows no derived state, and the switch to derived status stays the owner's (Q-3).
- **Close-out** — canonical run bound to `76030d8`: backend 441/0, page exit 0 (140 checks), local 430/0. Accounted `code-review-r1` (Opus, fresh) GO, 2 Low (CR-010-1, CR-010-2), follow-ups into PBI-030 by the owner's choice "Merge; fix in PBI-030". An earlier accounted review of the same commit (GO) was refused by the push rail because the builder's reports lacked `evidence_binding`; the owner chose "Re-run one review", and that record is kept under `docs/backlog/reviews/PBI-010/superseded-2026-09-19/`.
- **AC-DS22** (spec) — nothing is left to check visually, because the page shows nothing of this PBI (the owner's decision above).
- **Follow-up.** PBI-036's trigger T3.1 and AC-H4 assume a page view of derived state, which no longer exists, so PBI-036 needs re-planning before it can start (the owner is now told about agreement in chat).

---

## Notes

**External-review gate — approved by the owner 2026-09-19**, answering "Approve the build?" with "Approve the build" (spec revision 3; the build ships in shadow mode, and the switch to derived status stays the owner's, row Q-3). **Row Q-2 — the owner chose option (b)**, "Docs chore after merge": the build leaves `CLAUDE.md` alone and a docs chore corrects it straight after the merge. `merge_allowed_by_agent` set true under the owner's standing merge authorisation of 2026-09-12.

**The page view — the owner's decision, 2026-09-19.** Shown the rendered Shadow period panel for the AC-DS22 visual check, the owner said, verbatim: "Itts very complex and I don't understand it". Offered three simpler versions, the owner chose, verbatim: "Hide it entirely". The derivation is built and exported; the page shows none of it. Agreement between derived and hand-kept state is reported to the owner in chat instead. Page criteria that describe the panel are not applicable by this decision (N/A — accepted by the owner 2026-09-19), and AC-DS22's visual check has nothing left to check.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_spec: true`: refine a per-PBI spec from the parent spec and have it independently reviewed before any code is written. `requires_external_review: true`: the owner must explicitly approve ("approve" / "proceed" / "go ahead") before implementation begins.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | passed 2026-09-13 | spec revision 3 (round 2 APPROVE-WITH-NOTES, notes applied) |
| External-review gate | true | passed 2026-09-19 | the owner: "Approve the build" |
| Code-review gate | true | passed 2026-09-19 | Accounted `code-review-r1` GO, 2 Low follow-ups (owner: "Merge; fix in PBI-030") |
| No-self-merge gate | always | passed 2026-09-19 | PR #46 squash-merged `f4e92ed` under the owner's standing merge authorisation |
| BOARD-tidy gate | always | passed 2026-09-19 | Done write, ledger deregistered |