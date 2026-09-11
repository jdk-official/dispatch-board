# Done log — dispatch-board

<!-- On-demand archive of completed-PBI evidence. NEVER loaded at session start; the BOARD ## Done
     index anchors here by ID. One ## <PBI-ID> section per completed PBI. -->
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

