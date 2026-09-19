---
id: PBI-028
title: "Local record shapes name the session's waiting list and check a run's files are strings"
status: Done
change_class: standard
depends_on: [PBI-009, PBI-027]
allowed_areas: ["local/records*", "local/records.shapes.json", "local/tests/**"]
blocked_areas: ["site/**", "exporters/**", "local/collector*", "local/server*", "local/schema*", "local/db*"]
conflict_group: local-app
conflict_risk: Medium
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-028 — Local record shapes name `waiting` and type a run's `files`

---

## Description

A banked follow-up landed by intake on 2026-09-19, combining two recorded follow-ups from merged work:

- **PBI-009, spec row 3.** Sessions now carry an optional `waiting` object (from `exporters/derive.py` `waiting_of()`: `questions` [{at, question, source}], `refusals` [{at, kind, tool, detail}], optional `more`). `local/records.py` accepts it only as an unlisted field, so a malformed `waiting` would reach the local database unremarked. PBI-026 did the same job for the `findings` tab.
- **PBI-027, review follow-up.** The run shape types `files` as `list` without checking that its items are strings.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved); the shapes follow PBI-009's spec revision 3 and `waiting_of()` exactly.

---

## Acceptance criteria

- [x] **W-1 The session shape names `waiting`.** `local/records.py` `SHAPES['session']` (and its mirror `local/records.shapes.json`) lists `waiting` as optional, with `questions` and `refusals` typed as lists of objects whose fields match `waiting_of()` exactly, and `more` as an optional integer. The conformance check, which drives the real exporters, still passes with a session that has a question and a refusal.
- [x] **W-2 A malformed `waiting` is rejected, and the test bites.** Tests show `validate('session', …)` rejecting a refusal missing a field, a question that is not an object, and a non-integer `more`, and accepting a `waiting` with empty lists. Each test fails before W-1's change.
- [x] **W-3 A run's `files` holds strings only.** `SHAPES['run']['optional']['files']` rejects a non-string item and accepts `[]`, pinned by a test that fails before the change.
- [x] **W-4 Nothing is weakened.** Every existing local test passes. Where the pinned SHAPES literal in `local/tests/test_records.py` must mirror a shape change, it gains exactly the new fields and loses nothing.
- [x] **Out of scope:** the exporters, the collector, the server, the schema and the page.
- [x] Worker close-out: the three configured suites green on the head commit; accounted code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

**Closed out 2026-09-19.** Merged as `f7b21f9` (PR #31, squash; landing resolved squash (declared) / observed squash, level `record`).

- **W-1** — `SHAPES['session']` names `waiting` as `waiting_of()` writes it; the conformance check carries a question and a refusal through the real exporters; the reviewer validated a copy of the owner's real `board.db` (7 sessions, 223 runs) and 7 real `waiting` objects with no errors.
- **W-2** — `local/tests/test_records.py` `Waiting` rejects a refusal missing a field, a non-object question and a non-integer `more`, and accepts empty lists; with the old `records.py` 10 checks across 8 tests fail (reviewer-confirmed).
- **W-3** — `files` is `{'list_of': 'str'}`: a non-string item is rejected and `[]` accepted.
- **W-4** — all pre-existing local tests pass; the pinned SHAPES literal gains only `waiting` and the typed `files`; the JSON mirror is byte-identical to `--write-shapes`.
- **Out of scope** — only `local/records*` and `local/tests/**` changed.
- **Worker close-out** — canonical run via `round_close run` bound to `7debcf0`: backend 396, local 426, page exit 0 (131); accounted `code-review-r1` GO, 0 findings; evidence PASS at every phase.

---

## Notes

**Owner authority:** `merge_allowed_by_agent` is `true` under the owner's standing merge authorisation of 2026-09-12, verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time." Started under the owner's standing instruction to keep building the backlog.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-19 | Accounted `code-review-r1` GO, 0 findings |
| No-self-merge gate | always | passed 2026-09-19 | PR #31 squash-merged `f7b21f9` under the owner's standing merge authorisation |
| BOARD-tidy gate | always | passed 2026-09-19 | Done write, ledger deregistered |
