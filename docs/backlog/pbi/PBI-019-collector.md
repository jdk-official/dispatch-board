---
id: PBI-019
title: "Collector: incremental transcript and catalogue reads into SQLite, mass-delete guard, network-path guard (FR-86–FR-88; FR-103 collector half)"
status: Done
change_class: standard
depends_on: [PBI-003, PBI-004]
allowed_areas: ["local/collector*", "local/db*", "local/tests/**", "board.config.json", "exporters/board_config.py"]
blocked_areas: ["site/**"]
conflict_group: local-app
conflict_risk: Medium
requires_spec: true
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-019 — Collector: incremental transcript and catalogue reads into SQLite, mass-delete guard, network-path guard (FR-86–FR-88; FR-103 collector half)

---

## Description

Collector: incremental transcript and catalogue reads into SQLite, mass-delete guard, network-path guard (FR-86–FR-88; FR-103 collector half). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `local/collector*`, `local/db*`, `local/tests/**`, `board.config.json`, `exporters/board_config.py` (the database path key; it also touches `config` and `exporters`); blocked `site/**`. Its spec covers:
- WAL mode;
- change signalling for the server (`PRAGMA data_version` polling);
- a mass-delete guard equivalent to FR-49;
- age-only pruning;
- the network-path guard (FR-96) in the collector;
- the catalogue read (reusing PBI-017's logic through the shared module);
- the collector's half of the last-refresh write (FR-103).

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-86, FR-87, FR-88, FR-103:

*Corrected 2026-09-11, before the build (spec row Q-15; spec-gate review round 1, S-12): the three refresh-plan criteria below quoted PRD wording from before revision 3 (11 sets, test names that no longer exist). They now carry PRD revision 3's wording. Their counts change only when FR-103's refresher half is built, which is PBI-008's, so in this PBI they are regression checks that must stay green. AC-115 and AC-119 to AC-121, which PRD revision 3 assigns to the collector, are added.*

- [x] **AC-34** When the refresh script plans a fresh `out/` holding one project (status document `meta/status`) with its five tabs, two sessions (one linked, one not) and four runs, it shall plan 12 `set` writes and one `update` of `meta/status`. *(`Plan.test_first_plan_sets_everything_and_the_status`. The counts rise by one when FR-103 is built: row 12.)*
- [x] **AC-42** When only an unlinked session's title changes, the refresh script shall plan exactly one `set`, of that session, and no status update. *(`UpdatedAt.test_unlinked_session_change_does_not_bump`. The count rises when FR-103 is built: row 12.)*
- [x] **AC-44** When a linked session's run is deleted, the refresh script shall plan that `delete` plus an `update` of that project's status document. *(`UpdatedAt.test_deleted_linked_run_bumps`. The count rises when FR-103 is built: row 12.)*
- [x] **AC-115** When the collector's database path is configured as `\\nas\share\board.db`, the collector shall refuse to start and print that path. *(FR-180.)*
- [x] **AC-119** When a collector pass would delete more than half of the stored runs and sessions other than by age pruning, the collector shall apply none of that pass's deletions. *(FR-184.)*
- [x] **AC-120** When an unlinked session's last activity is 8 days old, the collector shall delete that session's records from the local database. *(FR-185.)*
- [x] **AC-121** When a linked session's last activity is 30 days old, the collector shall keep that session's records in the local database. *(FR-185.)*
- [x] **AC-63** When one line is appended to a transcript the collector has already read, the collector shall read from that file only the bytes of the appended line. *(FR-86.)*
- [x] **AC-64** When the collector and the session exporter process the same synthetic transcripts used by `tests/`, the collector shall produce session, run and project records equal to the exporter's documents, ignoring `generatedAt`. *(FR-87.)*
- [x] Worker close-out: the three configured suites are green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`, `python -m unittest discover -s local/tests`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

Re-checked fresh at finalize on 2026-09-12, on merged `main` at `f2e58e6`, which holds this PBI (`b23df89`) and PBI-008. Suites: 307 / 96 / 194.
- **AC-63:** `local/tests/test_collector.py` counts every open and read through the collector's `_open` seam: after one appended line, the next pass seeks to the stored offset and reads only that line's bytes.
- **AC-64:** `local/tests/test_collector_equivalence.py` runs the collector and the session exporter over the same synthetic transcripts `tests/` uses and compares the records, ignoring `generatedAt` — in one pass, a few lines at a time, and across a restart.
- **AC-115:** a database path of `\\nas\share\board.db` is refused before anything is opened, and the path is printed (`local/tests/test_db.py`).
- **AC-119:** a pass whose deletions other than age pruning would exceed half the stored runs and sessions applies none of them; the guard is computed before any write.
- **AC-120 and AC-121:** an unlinked session 8 days old has its records deleted; a linked session 30 days old keeps them. Its collector state is kept while the file is still in the window, which is what makes the next pass read nothing.
- **AC-34, AC-42 and AC-44:** the three named `tests/test_refresh.py` tests pass on merged `main`. This PBI did not change them or their counts; PBI-008 has since raised each expectation by the `meta/lastRefresh` write, which is FR-103's refresher half and its work.
- **Close-out:** the canonical run was bound to `d1e9d02` (300 / 89 / 194, PASS) before the merge; on merged `main` the suites are 307 / 96 / 194. Code review round 2 GO (`docs/backlog/reviews/PBI-019/findings.json`).

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_spec: true`: refine a per-PBI spec from the parent spec and have it independently reviewed before any code is written.

---

**Follow-up logged 2026-09-11** from the PBI-003 code review (`docs/backlog/reviews/PBI-003/findings.json`, follow-up 4):
- **The gap:** `to_row` accepts strings holding a lone surrogate, which then fail at INSERT with `UnicodeEncodeError`. The v1 exporters fail the same way, so it isn't a regression.
- **To do:** the collector's per-record error handling should expect `UnicodeEncodeError` as well as `ValueError`.

**Follow-ups logged 2026-09-11** from the PBI-003 code review, round 2 (`docs/backlog/reviews/PBI-003/findings.json`, GO):
- **Deep nesting:** `to_row` and `from_row` raise `RecursionError`, not `ValueError`, on documents nested about 100,000 levels deep, and `to_row` raises `TypeError` for an unhashable `kind`. The exporters can't produce either. If the collector wraps them anyway, catch these too, or narrow the docstrings.
- **Foreign tables:** `create_schema` stamps a file version 1 when a foreign table without indexes has the wrong columns, such as `statuses(x)`; spec §4 accepts this (I-6). When opening a file it didn't create, the collector should check `PRAGMA table_info` against `records.TABLES`.

**Follow-up logged 2026-09-11** from the PBI-019 code review, round 2 (`docs/backlog/reviews/PBI-019/findings.json`, optional, not a finding):
- **The gap:** a stored collector state row whose layout is right but whose inner values have the wrong type still fails every pass instead of resetting that session. Only a hand edit of the database can produce one.
- **To do:** extend the state check to validate inner value types, and reset on a mismatch as the layout check already does.

**Unblocked, 2026-09-11 (push rail).** The owner approved renaming the test constant, verbatim: "ok and approved. Continue building". It answers the question "rename the constant for PBI-019". The push rail's `generic-api-key` rule had matched a test constant named `SECRET` assigned a made-up Windows folder path, a made-up folder path in two collector test files, not a credential. See `docs/backlog/handovers/PBI-019.md`.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | passed 2026-09-11 | docs/backlog/specs/pbi-019-collector.md revision 3, approved in round 3 of 3 (APPROVE-WITH-NOTES, every note disposed: R3-1 and R3-3 applied, R3-2 deferred with rationale and named in Q-9, R3-4 accepted). Reviews: docs/backlog/reviews/PBI-019/spec-review-r1.md (CHANGES-REQUIRED), -r2.md (CHANGES-REQUIRED), -r3.md. Reviewer: pbi-review, same-vendor-subagent tier (a clean-context, read-only Plan agent) |
| External-review gate | false | pending | |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-019/findings.json (round 2 GO, no findings; round 1 NO-GO in findings-r1.json: 1 High, 1 Medium, 3 Low, all fixed test-first). Canonical run 300 / 89 / 194 PASS, bound to `a17d5fa` (run-report.json); cell-report.json CELL-DONE |
| No-self-merge gate | always | passed 2026-09-12 | PR [#15](https://github.com/jdk-official/dispatch-board/pull/15) from `pbi/PBI-019-collector` (commits `a17d5fa` and `d1e9d02`), squash-merged by the owner at 2026-09-11T22:15:23Z as `b23df89`. resolved_method squash (declared) / observed_method squash; level record |
| BOARD-tidy gate | always | passed 2026-09-12 | finalize: done-log entry and BOARD Done row written; close_check not run (`[closeout]` policy unset, so off) |
