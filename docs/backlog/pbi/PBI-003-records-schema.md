---
id: PBI-003
title: "Record shapes and SQLite schema: session, run, project, tab, status, last-refresh and catalogue records (FR-100 except the answer record; FR-101 fields; FR-102)"
status: Done
change_class: standard
depends_on: [PBI-018]
allowed_areas: ["local/records*", "local/schema*", "local/tests/**"]
blocked_areas: ["site/**", "exporters/**"]
conflict_group: local-app
conflict_risk: Low
requires_spec: true
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-003 — Record shapes and SQLite schema: session, run, project, tab, status, last-refresh and catalogue records (FR-100 except the answer record; FR-101 fields; FR-102)

---

## Description

Record shapes and SQLite schema: session, run, project, tab, status, last-refresh and catalogue records (FR-100 except the answer record; FR-101 fields; FR-102). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `local/records*`, `local/schema*`, `local/tests/**`; blocked `site/**`, `exporters/**`. It defines:
- the run record's start and end fields (FR-101), which PBI-020 fills;
- the run record's `agentType`;
- per-session skill use;
- the catalogue record.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-100, FR-101, FR-102:

- [x] **AC-69** *(N/A for PBI-003, accepted by the owner 2026-09-11: see Evidence.)* When the page requests the data snapshot, every record returned shall conform to the record shapes. *(FR-93, FR-100.)*
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

The criteria were verified fresh at finalize on 2026-09-11, on merged `main` `7fd96cb`, which contains PBI-003's squash commit:
- `python -m unittest discover -s tests`: 215 tests, OK;
- `node tests/page.test.mjs`: 57 checks passed;
- `python -m unittest discover -s local/tests`: 90 tests, OK.

**AC-D1 to AC-D7 (the spec-owned criteria in `docs/backlog/specs/pbi-003-records-schema.md`) are all met:**
- T1 and T4 (`local/tests/test_records.py`), including a literal pin of `SHAPES` to spec §3.1;
- T2 (`test_conformance.py`): every document the real exporters and `refresh.plan` write validates;
- T3 (`test_schema.py`): atomicity in three connection modes.

**Line endings:** the suite also passed on a real clone with `core.autocrlf=true`, done by the orchestrator and by the reviewer.

- **AC-69: N/A — verified in PBI-005 (the snapshot endpoint is PBI-005's, and `PBI-005.md` carries AC-69); PBI-003 contributed through AC-D2, which shows the definition fits every v1 document — accepted by jdk-official (owner) 2026-09-11.** The owner's reply, verbatim: "accept AC-69 as N/A for PBI-00". The reply's last character was cut off; it answered the one open AC-69 disposition, which was PBI-003's.
- **Worker close-out:**
  - all three suites pass on `7fd96cb`;
  - the spec gate passed at round 3 (revision 4);
  - the code-review gate passed: `docs/backlog/reviews/PBI-003/findings.json` round 2 GO (round 1 NO-GO in `findings-r1.json`, all five findings fixed);
  - PR #7 was squash-merged by the owner at 2026-09-11T15:03:45Z; the observed landing is squash (level: record).

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_spec: true`: refine a per-PBI spec from the parent spec and have it independently reviewed before any code is written.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | passed 2026-09-11 | docs/backlog/specs/pbi-003-records-schema.md revision 4 (approved); reviews spec-review-r1.md, spec-review-r2.md (CHANGES-REQUIRED, applied), spec-review-r3.md (APPROVE-WITH-NOTES, all notes applied) |
| External-review gate | false | pending | |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-003/findings.json (round 2 GO; round 1 NO-GO in findings-r1.json, all five findings fixed) |
| No-self-merge gate | always | passed 2026-09-11 | PR [#7](https://github.com/jdk-official/dispatch-board/pull/7), opened 2026-09-11 from `pbi/PBI-003-records-schema` (commit `508d768`), pushed via `git_rail.py`; squash-merged by the owner (jdk-official) at 2026-09-11T15:03:45Z as `7fd96cb`; observed landing squash (level: record) |
| BOARD-tidy gate | always | passed 2026-09-11 | done-log entry appended and BOARD row moved to Done with `board_tidy.py`; ledger row deregistered |
