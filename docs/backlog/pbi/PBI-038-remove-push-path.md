---
id: PBI-038
title: "Remove the v1 push path: delete `refresh.py` and its tests, move the three other test modules off it, remove the store adapter, retire the refresher's docs"
status: Proposed
change_class: standard
depends_on: [PBI-037, PBI-007]
allowed_areas: ["exporters/refresh.py", "tests/test_refresh.py", "local/tests/test_conformance.py", "local/tests/test_tabs_equivalence.py", "local/tests/fixtures/**", "tests/test_export_sessions.py", "site/**", "tests/page.test.mjs", "CLAUDE.md", "README.md", "docs/prd/**"]
blocked_areas: ["exporters/derive.py", "exporters/export_*.py", "exporters/board_config.py", "local/*.py", "local/records.shapes.json", "local/deploy/**"]
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: true
pr_required: true
merge_allowed_by_agent: false
---

# PBI-038 — Remove the v1 push path: delete `refresh.py` and its tests, move the three other test modules off it, remove the store adapter, retire the refresher's docs

---

## Description

Once the artifact has been frozen (PBI-037), PBI-007's log-on demonstration has been accepted, and a 7-day undo window has passed, this PBI removes the dead push path. It deletes `exporters/refresh.py` and `tests/test_refresh.py`, and moves the three other test modules that import `refresh` off it without losing their checks. It removes the store adapter from the page, and retires the refresher's documentation. After this merge the freeze can no longer be undone by restarting the loop. Decomposed from the approved solution spec at the plan gate on 2026-09-19 (track 10, G-11).

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 6, approved 2026-09-19)

**Areas and design notes from the parent spec:**

allowed `exporters/refresh.py` and `tests/test_refresh.py` (deletion only), `local/tests/test_conformance.py`, `local/tests/test_tabs_equivalence.py` and their fixtures under `local/tests/`, `tests/test_export_sessions.py` (AC-X6), `site/**`, `tests/page.test.mjs`, `CLAUDE.md`, `README.md`, `docs/prd/**` (the C-1 and FR-99 notes). Blocked: every other `local/**` path and every other `exporters/**` file. It also touches `exporters`, `local-app` and `docs`.

**Promotion precondition: trigger T4.4** (spec, "Revision 6: trigger criteria"; recorded in the same T4 evidence file as PBI-037). This PBI stays under Proposed until that evidence exists and the owner judges that it is met:

- PBI-007 is under Done: the owner has accepted its log-on demonstration (AC-65).
- At least 7 days have passed since PBI-037 closed (`revert_window_days = 7`). In that time no session's transcript runs `exporters/refresh.py --commit` or writes the artifact's store (a `write_db` call); a dry run of `refresh.py` does not count. The owner may shorten the 7 days, and the evidence file quotes them if so.
- The owner gives this PBI its external-review go-ahead.

The earliest date is 2026-09-26, PBI-007's Done date, or PBI-037's close date plus 7 days, whichever is latest. T4.4 counts every session, auto-linked or not.

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, revision 6, "PBI-038, removing the push path"; rows 38, 43):

- [ ] **AC-X1** T4.4 is recorded before any change.
- [ ] **AC-X2** `exporters/refresh.py` and `tests/test_refresh.py` are deleted. FR-133 and AC-86 retire with them. The exporter modules stay, because `local/tabs.py` and the collector import them.
- [ ] **AC-X3** The store adapter is removed from `site/index.html`. A page without the local marker shows the offline board, with a line naming the local app.
- [ ] **AC-X4** `CLAUDE.md`, `README.md` and the PRD's C-1 and FR-99 notes no longer describe a live store path.
- [ ] **AC-X5** Tier 4 (module deletion): the canonical run of all three suites is green on the head commit.
- [ ] **AC-X6** No module imports `refresh` afterwards. Its three other importers are moved off it, not deleted:
  - `local/tests/test_conformance.py` (`:19`, `refresh.plan()` at `:253`) keeps driving the real exporters, and checks the status documents through the collector's status records instead of `refresh.plan`, so AC-69's conformance proof still covers every document kind;
  - `local/tests/test_tabs_equivalence.py` (`:18`; `:67-72`, `:163-175`) re-pins the status rule of `local/tabs.py` to fixed expected documents, captured from `refresh.plan` before the deletion and committed as fixtures, rather than deleting the comparison;
  - `tests/test_export_sessions.py` (`:1282`) checks the collections from the exporters' `out/` folders directly.
- [ ] Worker close-out: tier 4 (row 44). The canonical run of the three configured suites is green on the head commit, and a search shows no remaining `refresh` import. The accounted code-review gate has passed.

---

## Evidence

- (written at close-out)

---

## Notes

**Authority.** Decomposed from the parent spec `docs/backlog/specs/dispatch-board.md`, revision 6. The owner approved it at the plan gate on 2026-09-19 with "Approve", answering the approval question that named commit `db14c0b` (spec blob `8fbdd3eba4a1042e2dfdbeb1689369eb015eb390`). The approval is recorded at `main` `e8f3f4e` (Plan-gate record). These criteria are the spec's own until the PRD re-baseline (row 47).

**Areas, as written for globs.** The spec's "their fixtures under `local/tests/`" is written here as `local/tests/fixtures/**`, a folder this PBI creates. The spec blocks "every other `local/**` path": the globs cover the `local/` modules, `local/records.shapes.json` and `local/deploy/**`. Test modules under `local/tests/` other than the two named are blocked too, although no glob lists them. The T4.4 evidence is written before promotion, not by this PBI's diff.

**Merge.** `merge_allowed_by_agent: false`. The spec reserves this merge for the owner, because this PBI deletes a module (Metadata; row 49).

**External review.** `requires_external_review: true`, for a deletion. The owner's go-ahead is part of T4.4.

**Sequencing.** `page`, High: it never runs beside PBI-032, PBI-033, PBI-035 or PBI-039.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| Trigger T4.4 (promotion precondition) | true | pending | the T4 evidence file; the owner judges |
| External-review gate | true | pending | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | the owner merges |
| BOARD-tidy gate | always | pending | |
