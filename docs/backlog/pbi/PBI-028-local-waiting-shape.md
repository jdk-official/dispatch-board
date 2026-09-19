---
id: PBI-028
title: "Local record shapes name the session's waiting list and check a run's files are strings"
status: In Progress
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

- [ ] **W-1 The session shape names `waiting`.** `local/records.py` `SHAPES['session']` (and its mirror `local/records.shapes.json`) lists `waiting` as optional, with `questions` and `refusals` typed as lists of objects whose fields match `waiting_of()` exactly, and `more` as an optional integer. The conformance check, which drives the real exporters, still passes with a session that has a question and a refusal.
- [ ] **W-2 A malformed `waiting` is rejected, and the test bites.** Tests show `validate('session', …)` rejecting a refusal missing a field, a question that is not an object, and a non-integer `more`, and accepting a `waiting` with empty lists. Each test fails before W-1's change.
- [ ] **W-3 A run's `files` holds strings only.** `SHAPES['run']['optional']['files']` rejects a non-string item and accepts `[]`, pinned by a test that fails before the change.
- [ ] **W-4 Nothing is weakened.** Every existing local test passes. Where the pinned SHAPES literal in `local/tests/test_records.py` must mirror a shape change, it gains exactly the new fields and loses nothing.
- [ ] **Out of scope:** the exporters, the collector, the server, the schema and the page.
- [ ] Worker close-out: the three configured suites green on the head commit; accounted code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

- (written at close-out)

---

## Notes

**Owner authority:** `merge_allowed_by_agent` is `true` under the owner's standing merge authorisation of 2026-09-12, verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time." Started under the owner's standing instruction to keep building the backlog.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| External-review gate | false | n/a | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
| BOARD-tidy gate | always | pending | |
