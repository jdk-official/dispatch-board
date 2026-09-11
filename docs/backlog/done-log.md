# Done log — dispatch-board

<!-- On-demand archive of completed-PBI evidence. NEVER loaded at session start; the BOARD ## Done
     index anchors here by ID. One ## <PBI-ID> section per completed PBI. -->
## PBI-013
- title: Usage limit forecast (feature 6, FR-117, FR-118)
- PR: https://github.com/jdk-official/dispatch-board/pull/9 · merge: `602eab9` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: site/**, tests/page.test.mjs
- evidence: docs/backlog/reviews/PBI-013/findings.json (round 2 GO; round 1 GO-WITH-CONDITIONS, all five applied); run-report bound to c54a119 (215/68/90 PASS); suites 215/68/90 OK on 602eab9; AC-80 checked against the live store's real data
- outcome: The board estimates the next usage-limit hit (mean gap from resumption to each hit, added to the latest reset), labelled an estimate, on the Claude usage tab and the Overview; 'no forecast: no limit hit recorded' when none is recorded. Page republished 2026-09-11. The method still needs the owner's record in PRD A-34.

## PBI-021
- title: Store leftovers clean-up: export the six unused documents to snapshot/, then delete them with the owner's explicit approval
- PR: https://github.com/jdk-official/dispatch-board/pull/2 · merge: `fd7b926` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: snapshot/**
- evidence: docs/backlog/reviews/PBI-021/findings.json (GO, no findings); AC-S1 to AC-S3 in docs/backlog/pbi/PBI-021.md Evidence; owner delete approval recorded verbatim; suites 215 / 57 / 90 OK on 7fd96cb
- outcome: The six retired tabs/* documents were deleted from the store with the owner's verbatim approval on 2026-09-11; copies remain in snapshot/tabs/ (fd7b926); every project's tabs still render.

## PBI-003
- title: Record shapes and SQLite schema: session, run, project, tab, status, last-refresh and catalogue records (FR-100 except the answer record; FR-101 fields; FR-102)
- PR: https://github.com/jdk-official/dispatch-board/pull/7 · merge: `7fd96cb` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: local/records*, local/schema*, local/tests/**
- spec: docs/backlog/specs/pbi-003-records-schema.md
- evidence: docs/backlog/reviews/PBI-003/findings.json (round 2 GO; round 1 NO-GO in findings-r1.json, all five findings fixed); suites 215 / 57 / 90 OK on 7fd96cb; AC-69 N/A for PBI-003, accepted by the owner 2026-09-11 (verified in PBI-005)
- outcome: local/records.py (SHAPES, validate, id forms, store_path, to_row/from_row), local/records.shapes.json and local/schema.py (7 tables, atomic idempotent create_schema), with 90 tests including conformance of every v1 exporter document. Unblocks PBI-019, PBI-005, PBI-006, PBI-008, PBI-014 and PBI-020 (with PBI-004 where needed).

## PBI-023
- title: Pull requests on the board: the GitHub tab lists each project's pull requests as links, and Needs attention flags the ones awaiting the owner's merge
- PR: https://github.com/jdk-official/dispatch-board/pull/6 · merge: `547b635` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: exporters/export_board.py, tests/test_export_board.py, site/**, tests/page.test.mjs, CLAUDE.md, README.md
- evidence: Code review GO-WITH-CONDITIONS, all three applied in e17006b (docs/backlog/reviews/PBI-023/findings.json); real gh run and Browser-pane check passed; unittest 215 OK and page 57/57 on 7fd96cb; handover docs/backlog/handovers/PBI-023.md
- outcome: GitHub tab lists each project's 20 most recently updated PRs as links; open PRs show in Needs attention as awaiting the owner's merge; gh failures never break the refresh. Live 2026-09-11 (pulls pushed, page republished). Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-022
- title: PRD re-baseline after project-first navigation and the plan-gate answers, with evidence for AC-84, AC-85 and AC-92
- PR: https://github.com/jdk-official/dispatch-board/pull/3 · merge: `3c520d6` · class: trivial · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: docs/prd/**, docs/backlog/evidence/**, docs/brief/raw-notes.md
- evidence: Code review GO-WITH-CONDITIONS, all four findings resolved in f3d80de (docs/backlog/reviews/PBI-022/findings.json); evidence docs/backlog/evidence/2026-09-11-prd-demonstrations.md; unittest 205 OK and page 49/49 on fd7b926; handover docs/backlog/handovers/PBI-022.md
- outcome: PRD revision 3 re-baselined to the current board; A-rows settled with ledger rows; D-21 supersedes D-1; D-19..D-26 recorded; brief says private; AC-84/85/92 demonstrated. Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-018
- title: Backlog shows future iterations: a "Later" group of idea cards read from the spec's Future iterations list
- PR: https://github.com/jdk-official/dispatch-board/pull/4 · merge: `25fa9e7` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: exporters/export_board.py, tests/test_export_board.py, site/**, tests/page.test.mjs, CLAUDE.md
- evidence: Code review GO (docs/backlog/reviews/PBI-018/findings.json; CR-018-01 LOW deferred to PBI-001); Browser-pane check: 9 idea cards, neutral --rule-2 bar, no errors; unittest 205 OK and page 49/49 on fd7b926; handover docs/backlog/handovers/PBI-018.md
- outcome: Backlog tab shows the spec's Future iterations as a Later group of 9 neutral idea cards; exporter adds backlog.later; never counted. Live 2026-09-11 (data pushed, page republished). Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-017
- title: Agent catalogue tab: every catalogue agent and skill, grouped by purpose, with usage coverage across sessions and projects
- PR: https://github.com/jdk-official/dispatch-board/pull/1 · merge: `84fa3ee` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: exporters/**, tests/test_*.py, site/**, tests/page.test.mjs, board.config.json, exporters/board_config.py, CLAUDE.md, README.md
- spec: docs/backlog/specs/pbi-017-agent-catalogue.md
- evidence: Code review round 3 GO-WITH-CONDITIONS (docs/backlog/reviews/PBI-017/code-review-r1..r3.md); spec gate passed (pbi-017-agent-catalogue.md rev 3); on 84fa3ee unittest 197 OK and page suite 44/44; live board shipped 2026-09-11 (102 writes, no deletes); handover docs/backlog/handovers/PBI-017.md
- outcome: Agent catalogue tab live on the board. Follow-ups logged in PBI-001, PBI-002 and PBI-023. Landing: resolved_method squash (declared) / observed_method merge. VIOLATION: the landing diverged from the declared contract (the provider's default merge was used against the declared squash); recorded, not reverted; tree identical to the reviewed 942842b. close_check NOT_RUN (policy off; the tool expects PBI-017-*.md file names). No ledger row or worktree (PBI-017 predates both).

