---
id: PBI-036
title: "Retire the hand-kept work-item state for a project: evidence, the owner's switch, and the close-out procedure without `state` (S-39)"
status: Proposed
change_class: standard
depends_on: [PBI-010]
allowed_areas: ["docs/backlog/evidence/**", "CLAUDE.md", "README.md"]
blocked_areas: ["board.config.json", "projects/**", "exporters/**", "site/**", "local/**"]
conflict_group: docs
conflict_risk: Low
requires_spec: false
requires_external_review: true
pr_required: true
merge_allowed_by_agent: true
---

# PBI-036 — Retire the hand-kept work-item state for a project: evidence, the owner's switch, and the close-out procedure without `state` (S-39)

---

## Description

Once trigger T3 shows that a project's derived work-item state is trusted, the owner switches that project to derived mode. This PBI records the evidence and updates the close-out procedure so it no longer edits `buildState.<id>.state` for that project. Only the owner flips the switch. Decomposed from the approved solution spec at the plan gate on 2026-09-19 (track 9, G-10).

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 6, approved 2026-09-19)

**Areas and design notes from the parent spec:**

allowed `docs/backlog/evidence/**`, `CLAUDE.md`, `README.md`. Blocked: `board.config.json` (the owner sets `workItemStatus` themselves, AC-H2), `projects/**` (never deleted, never rewritten by this PBI), `exporters/**`, `site/**`, `local/**`.

**Promotion precondition: trigger T3** (spec, "Revision 6: trigger criteria"). This PBI stays under Proposed until `docs/backlog/evidence/<date>-t3-<projectId>.md` exists, records T3.1 to T3.5, and quotes the owner's decision verbatim. The orchestrator gathers the evidence, and **the owner alone judges** whether it is met. No agent promotes this PBI or flips `workItemStatus`.

- **T3.1** PBI-010 is under Done on the BOARD, and at least 14 days have passed since its merge commit on `main`, during which the project's Backlog tab showed the shadow panel.
- **T3.2** In that time, at least 5 of the project's work items were named by a run (the shadow panel's "Named by a run" figure).
- **T3.3** On the day judged, the shadow panel shows 0 "Runs ahead" and 0 "Hand-kept ahead" items. The only exceptions are an item whose sole difference is a GO-WITH-CONDITIONS the owner has accepted (PBI-035), and an item the owner lists by id as an accepted exception in the evidence file.
- **T3.4** PBI-010 spec row Q-3 is settled by the owner (`docs/backlog/specs/pbi-010-derived-status.md:1111`).
- **T3.5** The owner's decision, "retire the hand-kept state for <projectId>", is quoted verbatim from chat.

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, revision 6, "PBI-036, retiring the hand-kept state"; row 36):

- [ ] **AC-H1** The T3 evidence file exists and records T3.1 to T3.5 before any other change.
- [ ] **AC-H2** For that project only, `workItemStatus` is `"derived"`, set by the owner alone (PBI-010 spec §5.2 and §5.3, `docs/backlog/specs/pbi-010-derived-status.md:486-507`). This PBI's diff leaves `board.config.json` untouched. The evidence file records the owner's edit and its commit.
- [ ] **AC-H3** `CLAUDE.md` and `README.md` say that close-outs no longer edit `buildState.<id>.state` for a project in derived mode. `review`, `open` and `commit` stay overrides (FR-176), and `projects/*.json` is never deleted (C-20).
- [ ] **AC-H4** After the next collector pass, the project's Backlog tab shows derived mode's line of text (PBI-010 spec §5.2), by demonstration.
- [ ] Worker close-out: tier 3 plus AC-H4's demonstration (row 44). The canonical run of the three configured suites is green on a tree holding the owner's switch. The accounted code-review gate has passed.

---

## Evidence

- (written at close-out)

---

## Notes

**Authority.** Decomposed from the parent spec `docs/backlog/specs/dispatch-board.md`, revision 6. The owner approved it at the plan gate on 2026-09-19 with "Approve", answering the approval question that named commit `db14c0b` (spec blob `8fbdd3eba4a1042e2dfdbeb1689369eb015eb390`). The approval is recorded at `main` `e8f3f4e` (Plan-gate record). It accepted row 36's default: T3 as written. These criteria are the spec's own until the PRD re-baseline (row 47).

**Per project.** T3 is judged one project at a time. A second project needs its own evidence file and its own pass through this PBI's procedure. The owner decides whether that is a new PBI. T3's earliest date is PBI-010's merge date plus 14 days. PBI-010 is still In Progress.

**Linked sessions.** T3.2 counts linked sessions. Once PBI-030 has merged, auto-linked sessions count too, and the evidence file says whether PBI-030 was live over its window.

**Merge.** `merge_allowed_by_agent: true`, under the owner's standing merge authorisation of 2026-09-12 (`CLAUDE.md`, "Merge authority"), verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time."

**External review.** `requires_external_review: true`, because it retires the hand-kept state. The owner must explicitly approve ("approve" / "proceed" / "go ahead") before implementation begins.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| Trigger T3 (promotion precondition) | true | pending | `docs/backlog/evidence/<date>-t3-<projectId>.md`; the owner judges |
| External-review gate | true | pending | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
| BOARD-tidy gate | always | pending | |
