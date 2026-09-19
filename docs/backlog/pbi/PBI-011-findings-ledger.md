---
id: PBI-011
title: "Review findings ledger (feature 3, FR-111, FR-112)"
status: Done
change_class: standard
depends_on: [PBI-004]
allowed_areas: ["exporters/**", "tests/test_*.py", "site/**", "tests/page.test.mjs"]
blocked_areas: []
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-011 — Review findings ledger (feature 3, FR-111, FR-112)

---

## Description

Review findings ledger (feature 3, FR-111, FR-112). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`. They also touch `exporters`.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-111, FR-112:

- [x] **AC-77** When round 1 of a PBI-001 review lists findings F1, F2 and F3 and round 2 lists only F2, the findings ledger shall show F1 and F3 resolved, F2 open, and 2 rounds so far. *(FR-111, FR-112; A-31.)*

*Firmed 2026-09-12, before the build started, from PRD FR-111, FR-112 and AC-77, and the owner-confirmed parent-spec row 11 ("the PRD defaults as written"). They add no scope beyond the title.*

- [x] **F-1 Derivation in the shared module.** `exporters/derive.py` reads a review-lane run's result and, when it ends with structured JSON findings, records each finding's id, severity, title, `file:line` and remediation, against that run's project, work item and review round (FR-111). A run whose result holds no such JSON contributes no findings and no error. Work item and round come from what the run already carries; the rules are the PRD's as written.
- [x] **F-2 Published as a project tab document.** The board exporter writes one `projectTabs/<projectId>.findings` document per project: per work item, the open findings, the resolved findings and the number of review rounds. It reuses the `projectTabs` collection the page already subscribes to and `refresh.py` already manages, so no new collection and no change to the mass-delete guard.
- [x] **F-3 AC-77 on the page.** Given round 1 of a PBI-001 review listing F1, F2 and F3 and round 2 listing only F2, the page's findings ledger shows F1 and F3 resolved, F2 open, and 2 rounds so far (FR-112, AC-77). A work item that has reached GO shows its rounds-to-GO. Pinned by page checks, including the empty case (no findings document: the view says so and logs no error).
- [x] **F-4 Nothing else changes.** The other exporter documents are unchanged, the existing suites stay green with no test weakened, and the page's other tabs are untouched.
- [x] **Out of scope:** CLAUDE.md's store-path table, which is outside this work item's areas; the new document is recorded there by a follow-up docs chore.
- [x] Worker close-out: the three configured suites are green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`, `python -m unittest discover -s local/tests`); code-review gate passed (`review-agents:code-reviewer` GO). *(Corrected 2026-09-12: the config has three suites.)*

---

## Evidence

Verified fresh at finalize on merged main `a23afd8` (PR #18, squash), 2026-09-12. Suites on that commit: `tests` **334**, `page.test.mjs` **99**, `local/tests` **194** — all OK.

- **AC-77** — `tests/page.test.mjs`: `findings ledger: AC-77 -- round 1 lists F1, F2, F3 and round 2 lists only F2, so F1 and F3 show resolved, F2 open, 2 rounds so far`, passing among 99. The derivation half is pinned twice more: `test_derive.FindingsDoc.test_ac77_two_rounds_one_finding_still_open` and `test_export_sessions.Findings.test_ac77_two_rounds_open_and_resolved`.
- **F-1** — `exporters/derive.py` reads a review-lane run's result into findings (id, severity, title, `file:line`, remediation) against project, work item and round. Pinned by the 9 `test_derive.FindingsOf` cases, including `test_a_result_with_no_json_yields_none_not_an_error` (no JSON ⇒ no findings, no error), `test_malformed_json_is_skipped_without_a_crash`, `test_an_earlier_decoy_fenced_object_does_not_swallow_the_real_block`, and `test_a_finding_with_no_id_is_dropped_rather_than_collapsed`; plus the 7 `test_derive.FindingsDoc` cases for round/work-item attribution.
- **F-2** — `exporters/export_sessions.py` writes one `projectTabs/<projectId>.findings` per project with a finished round, and deletes its own document when there is none: `test_export_sessions.Findings.test_no_findings_document_without_a_review_round`, `test_findings_document_has_no_generated_at_or_source_missing`, `test_run_documents_carry_no_findings_field`. Reuse of the existing `projectTabs` collection means no new collection and no mass-delete-guard change; ownership between the two exporters is pinned by `test_export_sessions.Ownership.test_export_board_run_alone_does_not_delete_the_findings_document` and `…test_running_the_exporters_in_refresh_order_leaves_exactly_one_findings_document`.
- **F-3** — the three page checks above, including the rounds-to-GO case (`a work item that reached GO shows its rounds-to-GO`) and the empty case (`with no findings document the view says so and logs no console error`). The page suite fails on any unexpected `console.error`, so "logs no error" is enforced, not asserted by eye.
- **F-4** — 334 / 99 / 194 on the merged head, against the pre-merge baseline of 307 / 96 / 194: every suite grew or held, none shrank. The code review confirmed the only removed lines were count constants that had to rise, and `test_export_sessions.Findings.test_a_cache_from_the_previous_parser_version_is_not_reused` pins the parser-version bump that round 1 found missing. `local/tests` is unchanged at 194, as this PBI touched no `local/**` file.
- **Out of scope** — CLAUDE.md's store-path table was added by the separate docs chore, PR #17 (squash-merged `141b3a4`), not by this PBI.
- **Worker close-out** — the three configured suites green on the head commit (above); code-review gate **GO** at round 2 (`docs/backlog/reviews/PBI-011/findings-r1.json`, round 1 NO-GO: 1 High, 5 Medium, 2 Low; all fixed test-first; 3 Lows recorded as follow-ups).

**Two defects the review caught, both of which would have published false information:** the un-bumped parser version meant cached review rows replayed with no findings (43 rows on the live cache), so a cached latest round would have shown never-fixed findings as *Resolved*; and a round whose findings go to a *file* rather than the reply — this project's own review protocol — was treated as the authoritative latest round, again marking everything resolved.

**Follow-up:** PBI-026 (local record shapes accept the `findings` tab) is on the BOARD — `local/records.py:91`'s `TAB_NAMES` does not yet include `findings`, so the local app cannot hold this document. The local suite's green 194 is not evidence of conformance here, because its fixture produces no review round.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

**Owner authority, 2026-09-12:** promoted and started under the standing instruction "This is for dispatch board. Lets keep building the backlog". `merge_allowed_by_agent` is `true` under the owner's standing authorisation, verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time."


---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | `requires_spec: false`; criteria firmed 2026-09-12 from PRD FR-111/FR-112/AC-77 and parent-spec row 11 |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-12 | `review-agents:code-reviewer`, round 2 **GO**; round 1 NO-GO (1 High, 5 Medium, 2 Low), all fixed test-first; 3 Lows recorded as follow-ups. `docs/backlog/reviews/PBI-011/findings-r1.json`, `findings.json`, `cell-report.json` |
| No-self-merge gate | always | passed 2026-09-12 | PR #18 squash-merged `a23afd8` by the orchestrator under the owner's standing merge authorisation (`merge_allowed_by_agent: true`); landing: resolved squash (declared) / observed squash, level `record` |
| BOARD-tidy gate | always | passed 2026-09-12 | two-part Done write: `docs/backlog/done-log.md` entry + BOARD `## Done` index row |
