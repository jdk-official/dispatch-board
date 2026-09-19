---
id: PBI-026
title: "Local record shapes accept the findings tab, so the local app can hold what the findings ledger publishes"
status: Done
change_class: standard
depends_on: [PBI-011]
allowed_areas: ["local/records*", "local/records.shapes.json", "local/tests/**"]
blocked_areas: ["site/**", "exporters/**", "local/collector*", "local/db*", "local/server*", "local/schema*"]
conflict_group: local-app
conflict_risk: Medium
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-026 — Local record shapes accept the findings tab

---

## Description

A banked follow-up, landed by intake on 2026-09-12. PBI-011's build surfaced it and recorded it as its own condition.

PBI-011 publishes a new project tab document, `projectTabs/<projectId>.findings`, holding the review findings ledger. The local-first app's record shapes accept only the five original tab names:

```
local/records.py:91   TAB_NAMES = ('spec', 'assumptions', 'decisions', 'backlog', 'git')
```

So a `findings` tab document is not a valid `tab` record locally. Today nothing breaks, because the local test fixture never produces one, but the moment the collector or a local fixture carries a findings document, the conformance check rejects it and that record is skipped. PBI-011 could not fix it: `local/**` is outside its areas.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved), whose derivation rule puts feature derivations in the shared module for both the board and the local app.

**Why these areas:** the tab-name list and the id pattern built from it live in `local/records.py`, mirrored in `local/records.shapes.json`; the conformance and record tests live in `local/tests/`. Nothing else needs to change: `local/schema.py` stores a tab record by kind and id, not by tab name.

---

## Acceptance criteria

- [x] **R-1 The shapes accept it.** `findings` is a valid tab name in `local/records.py` ~~and in `local/records.shapes.json`~~, so `projectTabs/<projectId>.findings` validates as a `tab` record and round-trips through `to_row`/`from_row` with its store path preserved. *(**Wording corrected at close-out, 2026-09-12.** `local/records.shapes.json` mirrors only `SHAPES` — the `tab` kind's field spec — and contains zero occurrences of any tab name, so it neither can nor should carry one. The criterion was authored on the assumption that it did. Verified independently by the orchestrator and confirmed by the reviewer; the struck clause was satisfied vacuously and is corrected rather than ticked as though the file had changed.)*
- [x] **R-2 Nothing else widens.** A tab name that is not in the list is still rejected, and no other record kind's id pattern changes. Tested with a name that must still fail.
- [x] **R-3 Conformance covers it.** `local/tests/test_conformance.py` exercises a findings document among the documents the exporters write, so the gap PBI-011 found cannot reappear unnoticed.
- [x] **R-4 The local suite grows, nothing is weakened.** Every existing local test still passes unchanged, and the new cases are added rather than substituted.
- [x] **Out of scope:** the collector, the server, the schema, the page, and the exporters. The document's shape and content are PBI-011's.
- [x] Worker close-out: the three configured suites are green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`, `python -m unittest discover -s local/tests`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

Verified fresh at finalize on merged main `5baa922` (PR #20, squash), 2026-09-12. Suites on that commit: `tests` **334**, `page.test.mjs` **99**, `local/tests` **265** — all OK, 0 skipped, against the 334 / 99 / 261 baseline (+4).

- **R-1** — `local/records.py:91` is now `TAB_NAMES = ('spec', 'assumptions', 'decisions', 'backlog', 'git', 'findings')`. Pinned by `local/tests/test_records.py::Paths::test_findings_is_a_valid_tab_name` (round-trips with the store path preserved) and by the conformance test below. `local/records.shapes.json` was correctly left untouched — see the corrected wording above — and `test_the_committed_json_copy_equals_shapes` still guards the mirror unmodified.
- **R-2** — `test_tab_names_widened_by_exactly_one` (the tuple grew by exactly one entry) and `test_an_unlisted_tab_name_is_still_rejected` (`alpha.notes`, `alpha.usage` and `alpha.findings.git` all still raise `ValueError`). Every existing id-form test for the other six kinds passes unchanged, and `TAB_NAMES` has one consumer repo-wide, so no other record kind's pattern moved.
- **R-3** — `local/tests/test_conformance.py::ConformanceFindings::test_a_findings_tab_was_written_and_conforms`. It drives the **real** `export_sessions.main` / `export_board.main` and walks the real `out/`, so `projectTabs/alpha.findings.json` is produced by `exporters/export_sessions.py:290-309` rather than hand-built. The fixture carries a *completed* review round, which is what makes `derive.findings_doc` non-empty — the base fixture's reviewer is still running, and that is exactly why the gap was invisible until PBI-011's build hit it.
- **R-4** — 4 tests added, 0 removed, 0 modified; no existing assertion touched. The shared `ConformanceV1` fixture and its tests are untouched, and `FindingsFixture` is a separate subclass used only by the new class.
- **Out of scope** — honoured: the change touches only `local/records.py` and two local test files. The collector, server, schema, page and exporters are unchanged.
- **Worker close-out** — the three configured suites green on the head commit (above); code-review gate **GO** at round 1.

**This was a widening of an input validator, and was reviewed as one.** `TAB_NAMES` feeds a regex alternation at `local/records.py:103`. The reviewer verified `form.fullmatch(record_id)` at the call site (`local/records.py:207`) rather than assuming the pattern was anchored, then probed adversarially: it accepted only `alpha.findings`, `Xalpha.findings`, `alpha.git` and a 100-character id, and rejected `alpha.findings.git`, `alpha.findingsX`, `alpha.spec|findings`, `al.pha.findings`, `alpha..findings`, trailing newline/space/NUL, `alpha.FINDINGS`, 101 characters and `al+pha.findings`. `_PROJECT_ID` is `[A-Za-z0-9_-]{1,100}` with no dot, the separator dot is escaped, and the alternation sits in a non-capturing group. Exactly one new id form.

**Mutation-verified:** stashing only `records.py` fails 3 of the 4 new tests — `test_findings_is_a_valid_tab_name`, `test_tab_names_widened_by_exactly_one`, and `ConformanceFindings::test_a_findings_tab_was_written_and_conforms` (error). R-3 was genuinely red before the fix.

**Follow-ups** (2 Low, in `docs/backlog/reviews/PBI-026/findings.json`): `local/records.py:103` joins `TAB_NAMES` into the regex with no `re.escape` — inert today, since every name is alphabetic, but a fail-open trap for any future name carrying a metacharacter; and `FindingsFixture.transcripts()` copy-pastes ~25 of 32 lines of the base fixture instead of extending it, so later edits to the base fixture will silently stop reaching the findings test.

**A cross-PBI hazard this created, caught at PBI-025's spec gate:** widening `TAB_NAMES` makes it unsafe for any other component to compute a "tabs this pass owns" set from it. `projectTabs` has two writers — `export_board` owns the five suffixes, `export_sessions` owns `findings` — and PBI-025's revision-1 spec would have derived its local deletion set from `records.TAB_NAMES`, deleting the findings record on every 60-second pass. That is fixed in PBI-025's revision 2 (finding F-2) before either built.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

**Owner authority:** `merge_allowed_by_agent` is `true` under the owner's standing authorisation of 2026-09-12, verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time." Promotion from Proposed to Ready remains a curation step.

**Ordering:** it depends on PBI-011, which introduces the document. It shares the `local-app` group with PBI-005 and PBI-025 at Medium risk, and touches none of their files.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI; the parent spec's derivation rule covers the design |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-12 (round 1 GO) | `review-agents:code-reviewer` (Opus): **GO**, 0 Critical, 0 High, 0 Medium, 2 Low as follow-ups. Re-measured rather than trusting the report: `fullmatch` verified at the call site, an adversarial id sweep over the widened alternation, and a mutation run (stashing `records.py` fails 3 of 4 new tests). Suites run by the reviewer: 334 / 99 / 265, matching the builder exactly. `docs/backlog/reviews/PBI-026/findings.json` |
| No-self-merge gate | always | passed 2026-09-12 | PR #20 squash-merged `5baa922` by the orchestrator under the owner's standing merge authorisation (`merge_allowed_by_agent: true`), on a round-1 GO. Landing: resolved squash (declared) / observed squash, level `record`. PR `MERGEABLE` / `CLEAN`. |
| BOARD-tidy gate | always | passed 2026-09-12 | two-part Done write: `docs/backlog/done-log.md` entry + BOARD `## Done` index row |
