---
id: PBI-008
title: "Stale-board warning: 'data as of' header (feature 1; FR-103 refresher half, FR-104, FR-105)"
status: Done
change_class: standard
depends_on: [PBI-003, PBI-004]
allowed_areas: ["exporters/refresh.py", "tests/test_refresh.py", "site/**", "tests/page.test.mjs", "local/tests/test_conformance.py"]
blocked_areas: ["local/records*", "local/schema*", "local/records.shapes.json", "local/collector*", "local/db*", "local/server*", "local/tests/test_records.py", "local/tests/test_schema.py", "local/tests/test_collector*", "local/tests/test_db.py", "local/tests/test_config_local.py", "local/tests/collector_support.py"]
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-008 — Stale-board warning: "data as of" header (feature 1; FR-103 refresher half, FR-104, FR-105)

---

## Description

Stale-board warning: "data as of" header (feature 1; FR-103 refresher half, FR-104, FR-105). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `exporters/refresh.py`, `tests/test_refresh.py`, `site/**`, `tests/page.test.mjs`; blocked `local/**` (the collector's half is PBI-019's). It also touches `exporters`.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-103, FR-104, FR-105:

*Corrected 2026-09-11 (PBI-019 spec-gate review round 1, S-12, and spec row Q-15): the three refresh-plan criteria below quoted PRD wording from before revision 3 (11 sets, test names that no longer exist). They now carry PRD revision 3's wording. This PBI builds FR-103's refresher half, so it is the one whose counts rise by one, as each criterion notes.*

- [x] **AC-34** When the refresh script plans a fresh `out/` holding one project (status document `meta/status`) with its five tabs, two sessions (one linked, one not) and four runs, it shall plan 12 `set` writes and one `update` of `meta/status`. *(`Plan.test_first_plan_sets_everything_and_the_status`. The counts rise by one when FR-103 is built: row 12.)*
- [x] **AC-42** When only an unlinked session's title changes, the refresh script shall plan exactly one `set`, of that session, and no status update. *(`UpdatedAt.test_unlinked_session_change_does_not_bump`. The count rises when FR-103 is built: row 12.)*
- [x] **AC-44** When a linked session's run is deleted, the refresh script shall plan that `delete` plus an `update` of that project's status document. *(`UpdatedAt.test_deleted_linked_run_bumps`. The count rises when FR-103 is built: row 12.)*
- [x] **AC-74** When the last-refresh time is 25 minutes old, the page shall show the "data as of" text in the `--changes` amber token with the word "stale"; when it is 5 minutes old, the page shall show it without that styling. *(FR-104, FR-105.)*

*Firmed 2026-09-11, before the build started, from the owner-confirmed parent spec row 12 ("The last-refresh record adds one write per tick, and the affected tests are updated"), PRD FR-103 to FR-105, and the `lastRefresh` record shape in `local/records.py`. The criteria add no scope beyond the title.*

- [x] **L-1 The refresher's write (FR-103).** Every `refresh.py` plan includes exactly one `set` of `meta/lastRefresh`. Its file under `out/` holds `{"at": <UTC time, seconds, with Z>, "writer": "refresher"}`, which fits the `lastRefresh` shape. `--commit` records it as pushed like any other write. A refused plan (the mass-delete or answers guard) writes and plans nothing, as now.
- [x] **L-2 The counts rise by one, and the tests say so.** AC-34's plan is 13 `set` writes (12 plus `meta/lastRefresh`) and one `update` of `meta/status`. AC-42's is two `set` writes (that session and `meta/lastRefresh`) and no status update. AC-44's is that `delete`, the status `update`, and the `meta/lastRefresh` `set`. The three named tests, and every other test in `tests/test_refresh.py` whose expected plan changes only because of the added `meta/lastRefresh` write, are updated to the new counts, as row 12 allows ("the affected tests are updated"). No test is weakened: each keeps what it checks, and only the extra write is added to its expectation. *(Widened 2026-09-11 after the first build found 21 more affected tests; the file was always in this PBI's areas.)*
- [x] **L-3 It is not project data.** Writing `meta/lastRefresh` never bumps any project's status `updatedAt` or `live`. It is never deleted by a plan, and it never counts toward the mass-delete guard.
- [x] **L-4 The page (FR-104, FR-105, AC-74).** The page subscribes to `meta/lastRefresh` and shows "data as of <time>" in the header. The time comes from `at`, rendered through `esc()`. When `at` is more than 20 minutes old, the text uses the `--changes` token and says "stale" (never `--human`). The minute timer re-evaluates staleness with no store change. With no `meta/lastRefresh` document, or an unreadable `at`, the header shows no "data as of" text and logs no error. Each case is pinned by a page check.
- [x] **Out of scope:** the collector's half of FR-103 (PBI-019), anything under `local/**`, and CLAUDE.md's refresh procedure. Every tick now has at least one write, so "nothing to push" no longer occurs; the procedure text is updated by a follow-up docs chore after merge. If `local/tests/test_conformance.py` fails because `refresh.plan` now writes a `lastRefresh` document, the worker stops and reports: `local/**` is blocked.
- [x] Worker close-out: the three configured suites are green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`, `python -m unittest discover -s local/tests`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

Re-checked fresh at finalize on 2026-09-12, on merged `main` at `f2e58e6` (this PBI's squash merge). Suites: 307 / 96 / 194.
- **L-1 and AC-34, AC-42, AC-44:** `tests/test_refresh.py` proves every plan carries exactly one `set` of `meta/lastRefresh` (`{"at": …, "writer": "refresher"}`), and the three named tests now expect the raised counts: 13 sets plus the status update; two sets for a changed unlinked session; the delete, the status update and the last-refresh set.
- **L-3:** tested directly — the record never bumps a project's status `updatedAt` or `live`, is never deleted by a plan, and never counts toward the mass-delete guard. A refused plan still writes and plans nothing.
- **L-4 and AC-74:** seven page checks. The header shows "data as of <time>" taken from `at` (an exact-match check that fails if the time is not derived from the record), amber with "stale" past 20 minutes and plain at 5, re-evaluated by the existing minute timer, and silent with no console error when the record is absent or `at` is not a readable string (null, 0, true, a number, an object, a bad string). A hostile value is escaped.
- **L-2:** `local/tests/test_conformance.py` maps `meta/lastRefresh` to the `lastRefresh` kind and expects it among the documents the plan writes; the local suite's count is unchanged. No test was weakened: the round-2 review read all 24 changed expectations hunk by hunk and confirmed every original assertion is kept.
- **Close-out:** the canonical run was bound to `bd280d5` (307 / 96 / 90, PASS) before the merge; on merged `main` the suites are 307 / 96 / 194, the local count now including PBI-019's collector tests. Code review round 2 GO (`docs/backlog/reviews/PBI-008/findings.json`).
- **Live effect:** from this merge on, every refresher tick has at least one write, so `refresh.py` no longer prints "nothing to push". CLAUDE.md's refresh procedure, its store-path table and PRD FR-46 still describe the old behaviour; the docs chore below corrects them.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

**Blocked, 2026-09-11 (hard stop, blocked area):** code-writer built L-1 to L-3, but `local/tests/test_conformance.py` (`ConformanceV1.setUpClass`) fails once `refresh.plan` writes `meta/lastRefresh`: its path map knows only `meta/status`. The file is under `local/**`, which this PBI blocks, and it was not changed. Unblocking needs the owner's approval to add `local/tests/test_conformance.py` to `allowed_areas` for a one-test update that maps `meta/lastRefresh` to the `lastRefresh` kind (SPEC: a blocked-area edit needs a PBI update with the user's approval). See `docs/backlog/handovers/PBI-008.md`.

**Unblocked, 2026-09-11.** The owner approved the scope change, verbatim: "ok and approved. Continue building". It answers the question "approve adding local/tests/test_conformance.py to PBI-008".
- **Now allowed:** `local/tests/test_conformance.py` was added to `allowed_areas`.
- **Still blocked:** the rest of `local/` stays out of scope, named file by file in `blocked_areas` (as for PBI-024), because a blanket `local/**` block would override the new allowance.
- **What the test update must do:** update only the conformance test so its path map knows `meta/lastRefresh` (the `lastRefresh` kind PBI-003 already defines) and expects that kind among the documents `refresh.plan` writes. The local suite's test count does not change.


**Follow-ups logged 2026-09-11** from this PBI's code reviews (recorded, not findings):
- **CR-5 (Low):** the hostile-`at` page check pins the outcome (no markup reaches the DOM) but never reaches `esc()`, because `when()` returns `toLocaleString` output. The check's label claims more than it proves. No behaviour risk.
- **CR-6 (Low):** PRD FR-46 (`docs/prd/dispatch-board.md`) still requires the deleted `nothing to push` output and cites three renamed tests. It is outside this PBI's areas and belongs to the docs chore below.

**Docs chore after merge (outside this PBI's areas):** CLAUDE.md's refresh procedure and `/loop` prompt still guard on `nothing to push`, which can no longer occur, and its store-path table has no `meta/lastRefresh` row; PRD FR-46 needs the same correction.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | false | pending | |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-008/findings.json (round 2 GO, 2 Low recorded as follow-ups; round 1 GO-WITH-CONDITIONS in findings-r1.json: 1 Medium, 3 Low, all fixed test-first). Canonical run 307 / 96 / 90 PASS, bound to `bd280d5` (run-report.json); cell-report.json CELL-DONE |
| No-self-merge gate | always | passed 2026-09-12 | PR [#16](https://github.com/jdk-official/dispatch-board/pull/16) from `pbi/PBI-008-stale-board` (commit `bd280d5`), squash-merged by the owner at 2026-09-12T07:13:46Z as `f2e58e6`. resolved_method squash (declared) / observed_method squash; level record |
| BOARD-tidy gate | always | passed 2026-09-12 | finalize: done-log entry and BOARD Done row written; close_check not run (`[closeout]` policy unset, so off) |
