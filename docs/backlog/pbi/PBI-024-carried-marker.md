---
id: PBI-024
title: "Carried-tab marker: the board exporter writes carriedSince on a tab it keeps from an earlier export (FR-190)"
status: In Review
change_class: standard
depends_on: [PBI-001]
allowed_areas: ["exporters/export_board.py", "tests/test_export_board.py", "CLAUDE.md", "local/tests/test_conformance.py"]
blocked_areas: ["site/**", "local/records*", "local/schema*", "local/records.shapes.json", "exporters/export_sessions.py", "exporters/export_catalogue.py"]
conflict_group: exporters
conflict_risk: Medium
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-024 — Carried-tab marker: the board exporter writes carriedSince on a tab it keeps from an earlier export (FR-190)

---

## Description

A banked follow-up, landed by intake on 2026-09-11. PBI-001's title named the "carried-tab marker", but its criteria (decomposed before PRD revision 3 added FR-190 and AC-125) did not include it, and it was not built. This was found at PBI-001's finalize.

When `exporters/export_board.py` keeps a project tab's last export because its source went missing (FR-153: the repo is missing or moved, the spec renamed, or git unavailable), it shall mark that tab document with `carriedSince`, the time the carry began. The page's warning that reads it is PBI-002's (FR-191 / AC-126).

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved), row 13: "a `carriedSince` marker shown as a warning".

**Why these areas:**
- The keep-last logic is in `export_board.py`, around lines 394-414: kept tabs are held as exact bytes and written back unchanged.
- The keep-last tests live in `tests/test_export_board.py` (`MissingSources`).
- `CLAUDE.md` documents the `projectTabs` shape.
- `local/**` is not needed: the local record shapes accept extra fields (`local/tests/test_records.py:149`), so the conformance tests stay green without a `local/` change.

---

## Acceptance criteria

- [x] **AC-125** When the board exporter keeps a project tab from an earlier export, it shall write `carriedSince` on that tab document. *(FR-190.)*
- [x] **Stable while carried:** on later runs while the source is still missing, `carriedSince` keeps its first value, the time the carry began, and the kept document stays byte-identical run to run. So `refresh.py` plans no write for it after the first carry. The existing `MissingSources.test_kept_tabs_are_byte_identical` is updated to say this, not weakened.
- [x] **Clears on recovery:** when the tab's source comes back, the next export rebuilds the tab without `carriedSince`.
- [x] **Scope:** only tabs kept under FR-153 get the marker. A tab that exports normally never carries `carriedSince`, and no other store document changes shape.
- [x] **Docs:** `CLAUDE.md`'s `projectTabs` description names `carriedSince` and when it is set and cleared.
- [x] **Out of scope:** the page's warning (FR-191 / AC-126, PBI-002), and any change to `export_sessions.py`, `export_catalogue.py` or `local/**`, apart from the one approved test below.
- [x] **Local conformance test updated, not weakened:** `local/tests/test_conformance.py`'s `test_alpha_tabs_are_the_ones_export_board_kept` asserts that each carried tab equals its first export plus `carriedSince`. The local suite stays at 90 tests, all passing. *(Scope approved by the owner, 2026-09-11.)*
- [x] Worker close-out: the three configured suites are green on the head commit. That is `python -m unittest discover -s tests` (267 before, plus the new tests), `node tests/page.test.mjs` (68) and `python -m unittest discover -s local/tests` (90, which must not change). The code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

Re-checked fresh at finalize on 2026-09-11, on merged `main` at `049f27e`, which holds this PBI (`7bcd2fd`) and PBI-002.
- **AC-125:** `tests/test_export_board.py`'s `MissingSources` tests pass. They assert that a kept tab equals its earlier export plus `carriedSince` (lines 395–420), including a readable tab kept beside a corrupt one (line 516).
- **Stable while carried:** the byte-identity test (lines 423–440) asserts the first carry adds only `carriedSince`, and later runs write the same bytes, keeping the first value (line 486). So `refresh.py` plans no further write.
- **Clears on recovery:** asserted at lines 459 and 476–477. A tab whose source returns is rebuilt without `carriedSince`.
- **Scope:** asserted at lines 491–501 and 539. Tabs that export normally, and a healthy tab beside a carried one, never carry the marker.
- **Docs:** `CLAUDE.md` names `carriedSince` in its `projectTabs` description (lines 32 and 57).
- **Out of scope:** PR #13's diff touches only `exporters/export_board.py`, `tests/test_export_board.py`, `CLAUDE.md` and `local/tests/test_conformance.py` (the `git pull` of `049f27e` lists no other file for the two merges besides PBI-002's `site/index.html` and `tests/page.test.mjs`).
- **Local conformance test:** the local suite ran 90 tests, all passing, on `049f27e`.
- **Close-out:** 274 / 89 / 90 passing on `049f27e`; the worker's canonical run bound to `749b4ae` was 274 / 68 / 90, PASS (`docs/backlog/reviews/PBI-024/run-report.json`). Code review round 2 GO (`docs/backlog/reviews/PBI-024/findings.json`).

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

**Blocked, 2026-09-11:** code-writer built the change and its tests pass, but `local/tests/test_conformance.py:403` asserts the first carried export is byte-identical to the original. That was FR-153's old contract, and AC-125 changes it. The intake premise, that `local/**` isn't needed because the shapes accept extra fields, held for the shape checks but missed this byte assertion. Unblocking needs the owner's approval to add `local/tests/test_conformance.py` to `allowed_areas` (SPEC: a blocked-area edit needs a PBI update with the user's approval). See `docs/backlog/handovers/PBI-024.md`.

**Unblocked, 2026-09-11.** The owner approved the scope change, verbatim: "approve adding local/tests/test_conformance.py to PBI-024".
- **Now allowed:** `local/tests/test_conformance.py` was added to `allowed_areas`.
- **Still blocked:** the rest of `local/` stays out of scope, so `local/records*`, `local/schema*` and `local/records.shapes.json` are now named in `blocked_areas`.
- **What the test update must do:** update only `ConformanceV1.test_alpha_tabs_are_the_ones_export_board_kept` to the FR-190 contract. Each carried tab equals its first export plus `carriedSince`, and the local suite stays at 90 tests.

**Ordering:** it lands before PBI-004, whose extraction moves `export_board.py`'s logic, so the two don't collide. It can run beside PBI-002, which is in the page group and never touches `exporters/**`.

**Owner authority:** the standing instruction of 2026-09-11, verbatim: "Start from the beginning. I want you to use the agents and keep building as per their instructions. Don't ask me what to build next".

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI; the parent spec's row 13 covers the design |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-024/findings.json (round 2 GO; round 1 GO-WITH-CONDITIONS in findings-r1.json, all three applied) |
| No-self-merge gate | always | passed 2026-09-11 | PR [#13](https://github.com/jdk-official/dispatch-board/pull/13) from `pbi/PBI-024-carried-marker` (commit `749b4ae`), squash-merged by the owner at 2026-09-11T17:45:02Z as `7bcd2fd`. resolved_method squash (declared) / observed_method squash; level record |
| BOARD-tidy gate | always | passed 2026-09-11 | finalize: done-log entry and BOARD Done row written; close_check not run (`[closeout]` policy unset, so off) |
