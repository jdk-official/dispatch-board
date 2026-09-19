# BOARD — dispatch-board

<!-- The section a PBI is listed under is the authoritative status (SPEC §State machine).
     PBI files: docs/backlog/pbi/. Parent spec: docs/backlog/specs/dispatch-board.md (revision 5, approved). -->

---

## Proposed

<!-- PBI-016 (Unraid deployment) was moved to Later by the owner on 2026-09-11 ("Move PBI16 to later"). It is now a Future iterations idea in docs/backlog/specs/dispatch-board.md, shown in the Backlog tab's Later group, and is no longer a planned work item. Local convention: a PBI de-scoped this way keeps its file with `status: Later` and sits in no BOARD section. The SPEC has no deferred state; this gap is noted for the backlog-delivery plugin owner. -->

<!-- BOARD-tidy 2026-09-12, PBI-011 close-out: PBI-011 is Done (PR #18, a23afd8), so its dependants PBI-014 and PBI-026 are no longer blocked by it. PBI-014 still waits on PBI-003 (Done), so it is dependency-clear; PBI-026 is dependency-clear. Both remain Proposed — promotion to Ready is the owner's curation act. PBI-026 is local-app (Medium) and touches only `local/records*` and `local/tests/**`, so it collides with neither PBI-005 nor PBI-025. -->

<!-- BOARD-tidy 2026-09-12, PBI-005 close-out: PBI-005 is Done (PR #19, 3e3ec44), so PBI-006 is now dependency-clear — both PBI-003 and PBI-005 are Done. PBI-007 still waits on PBI-006. Nothing is in flight, so no conflict group is occupied: PBI-006 (page), PBI-025 and PBI-026 (local-app, Medium each) could all start. Note PBI-025 shares `board.config.json` and `exporters/board_config.py` with what PBI-005 just landed, so it must branch from main at or after 3e3ec44. PBI-007 also owns AC-68's in-browser demonstration leg, which PBI-005 deliberately did not claim (approved spec §7, §10). All remain Proposed — promotion to Ready is the owner's curation act. -->

| ID | Title | Depends on | Notes |
|----|-------|------------|-------|
| PBI-020 | Timeline view (feature 9; FR-101 filled, FR-122–FR-124) | [PBI-003, PBI-004] | Decomposed from the approved spec, 2026-09-11 |
| PBI-039 | The Backlog tab lists every PBI, not only the plan's | [] | Intake 2026-09-19, owner: "And PBI30 doesn't exist". page group: runs after PBI-010, before PBI-020. |
| PBI-040 | Only one collector runs at a time | [] | Intake 2026-09-19 from PBI-007's log-on demonstration: Task Scheduler started a second collector. Starts after PBI-030 (both edit `local/collector.py`). |
| PBI-031 | Answers endpoint on the local server: the answer record, a server-owned answers database, `POST /api/answers` with its checks, a nonce content-security policy, `local/answers.py list` and `verify`, and the `CLAUDE.md` answer and transcription rules (FR-95, FR-132, NFR-23) | [PBI-007] | Decomposed from spec revision 6 (approved 2026-09-19); batch approved by the owner 2026-09-19. |
| PBI-032 | Answer from the board: Accept and Override on the Assumptions tab (local adapter only), answered and transcribed states (FR-131, AC-87) | [PBI-031] | Decomposed from spec revision 6 (approved 2026-09-19); batch approved by the owner 2026-09-19. |
| PBI-033 | Answer audit: transcript tool calls that could have sent an answer, and the answers they may have made marked on the Assumptions tab | [PBI-032, PBI-030, PBI-034] | Decomposed from spec revision 6 (approved 2026-09-19); batch approved by the owner 2026-09-19. |
| PBI-034 | Approvals as answers: `planApproval` bound to git's blob id of the committed spec, and `conditionsAccepted` bound to one review run, with server checks and `verify` support (S-31) | [PBI-031] | Decomposed from spec revision 6 (approved 2026-09-19); batch approved by the owner 2026-09-19. |
| PBI-035 | Approve from the board: plan approval on the Spec tab, conditions acceptance on the Backlog, and the accepted-conditions overlay | [PBI-032, PBI-034, PBI-010] | Decomposed from spec revision 6 (approved 2026-09-19); batch approved by the owner 2026-09-19. |
| PBI-036 | Retire the hand-kept work-item state for a project: evidence, the owner's switch, and the close-out procedure without `state` (S-39) | [PBI-010] | Decomposed from spec revision 6 (approved 2026-09-19); batch approved by the owner 2026-09-19. |
| PBI-038 | Remove the v1 push path: delete `refresh.py` and its tests, move the three other test modules off it, remove the store adapter, retire the refresher's docs | [PBI-037, PBI-007] | Decomposed from spec revision 6 (approved 2026-09-19); batch approved by the owner 2026-09-19. |

---

<!-- BOARD-tidy 2026-09-19, PBI-014 close-out: PBI-014 is Done (PR #24, 4bbbad8; AC-82 and NFR-22 approved by the owner on rendered screenshots). Its ledger row is gone, so the `page` group's High-risk slot is free. PBI-027 is now dependency-clear (local-app); PBI-007 still waits on PBI-027. PBI-009, PBI-010, PBI-012 and PBI-020 remain serial in the `page` group. -->
## Ready

<!-- Promotion notes:
     - PBI-017 was promoted 2026-09-11, authorised by the owner at the plan gate ("... start PBI-017 via code-writer → code-reviewer"). It is now Done (PR #1, 84fa3ee).
     - PBI-022 and PBI-023 were promoted 2026-09-11 under the owner's standing instruction ("keep building as per their instructions. Don't ask me what to build next"). PBI-023 is the owner's request for pull-request links ("update the artifact with this so I can access it").
     - PBI-018 was promoted 2026-09-11 under the same standing instruction, once its dependency PBI-017 reached Done. It goes before PBI-023: it is next in the approved plan order and unblocks PBI-001, PBI-003 and PBI-013. Both are in the page group at High risk, so they run one at a time.
     - PBI-021 was promoted 2026-09-11. The owner's external-review approval is recorded in its PBI file, verbatim: "approve PBI-021". The delete batch still needs its own approval (AC-S2).
     - PBI-003 was started 2026-09-11 under the standing instruction, once its dependency PBI-018 reached Done. It is local-app work at Low risk, so it runs in parallel with PBI-023 (page).
     - PBI-001 and PBI-013 were started 2026-09-11 under the standing instruction, once their dependency PBI-018 was Done and PBI-023 (page group, High risk) had deregistered. They are in different groups (exporters and page), so they run in parallel.
     - PBI-024 (intake 2026-09-11, a banked follow-up from PBI-001's finalize) and PBI-002 were started 2026-09-11 under the standing instruction, once their dependency PBI-001 reached Done (PR #10, d4023c6). They are in different groups (exporters Medium, page High), so they run in parallel. ~~PBI-004 waits for PBI-024, because both change exporters/export_board.py.~~ PBI-024 Done 2026-09-11 (PR #13, 7bcd2fd), so PBI-004 is no longer held back by it. -->

| ID | Title | Depends on | Conflict group | Conflict risk |
|----|-------|------------|----------------|---------------|

---

## In Progress

| ID | Title | Branch | Worktree | Session tag | Started (UTC) |
|----|-------|--------|----------|-------------|---------------|
<!-- Revision 6 decomposed 2026-09-19 into PBI-031 to PBI-038. The owner approved the batch, asked "Put PBI-031 to PBI-038 on the BOARD as shown, and start PBI-037 (freeze the published artifact) now?", verbatim: "Approve batch, start 037". PBI-037 is docs/Low, so it runs beside PBI-010 (page/High). -->
| PBI-010 | Work-item status derived from runs, shown beside the hand-kept state during a shadow period (feature 4, FR-113) | `pbi/PBI-010-derived-status` | C:/Users/jdk/dispatch-board-worktrees/PBI-010 | 7e0c4f3c | 2026-09-19T13:49:57Z |
| PBI-030 | Sessions link to a project automatically from the files they edit | `pbi/PBI-030-auto-link-sessions` | C:/Users/jdk/dispatch-board-worktrees/PBI-030 | 7e0c4f3c | 2026-09-19T18:30:00Z |
<!-- PBI-030 started 2026-09-19 (exporters, Medium) beside PBI-010: its spec is approved (revision 3), and it rebases onto PBI-010 once that merges, taking PBI-010's follow-up CR-010-1 with it. -->
<!-- PBI-010 started 2026-09-19 the moment PBI-012 closed and freed the page slot. Spec gate passed (revision 3); external review approved by the owner 2026-09-19 ("Approve the build"); ships in shadow mode, the switch to derived status stays the owner's (Q-3). First PBI whose PR the pr-steward raises. -->
<!-- PBI-029 landed by intake and started 2026-09-19 at the owner's request, as a priority: the log-on collector's git children each opened a console window. exporters group, Medium; its areas avoid PBI-012's derive.py and export_sessions.py and PBI-028's records*. -->
<!-- PBI-028 landed by intake 2026-09-19 from two banked follow-ups (PBI-009 spec row 3; PBI-027's review) and started at once under the owner's standing instruction to keep building: local-app Medium, so it runs beside PBI-012 (page High) and PBI-007 (local-app Low, merged, awaiting the owner's log-on demonstration) without collision. -->
<!-- PBI-012 started 2026-09-19 the moment PBI-009 closed and freed the page slot: no spec, no external review and no open owner question, so it runs while the owner decides PBI-010's external-review gate and the CLAUDE.md grant for PBI-010 and PBI-020. merge_allowed_by_agent set true under the owner's standing merge authorisation of 2026-09-12. -->
<!-- PBI-027 and PBI-009 started 2026-09-19 under the owner's standing instruction to keep building the backlog, the moment PBI-014's close-out freed the `page` group's High-risk slot. PBI-027 is local-app (Medium) and touches only `local/collector*`, `local/records*` and `local/tests/**`; PBI-007 (local-app, Low) is idle, waiting on it, so they do not collide. PBI-009 takes the page slot; its spec gate passed 2026-09-12 (revision 3), and it builds on the spec's recommended defaults for the owner rows 1a, 1b and 2 unless the owner says otherwise. Tier resolved `assisted` (earned lift `supervised`). -->
<!-- PBI-007 and PBI-014 started 2026-09-12 under the owner's standing instruction to keep building the backlog, after the owner again asked why nothing was in flight. Only these two can build concurrently: five of the six remaining items (PBI-009, PBI-010, PBI-012, PBI-014, PBI-020) are all `page` group at High risk, and the ledger guard permits one High-risk row per group, so PBI-014 takes that single slot. PBI-007 is local-app at Low risk, a different group, so it runs alongside. Both have `requires_spec: false` and all dependencies Done (PBI-007: PBI-019, PBI-005, PBI-006; PBI-014: PBI-003, PBI-011). `merge_allowed_by_agent` set true on both under the owner's standing merge authorisation of 2026-09-12. Meanwhile the spec gates for PBI-009 and PBI-020 run in parallel — spec authoring writes only under `docs/backlog/specs/`, so it collides with nothing and uses the time while the page slot is held. PBI-007 also owns AC-68's in-browser demonstration leg, which PBI-005 deliberately did not claim. -->
<!-- PBI-025 entered its build 2026-09-12 once its spec gate passed (revision 3, round 2 APPROVE-WITH-NOTES, all notes applied) and PBI-026 landed, which retired the `local/tests/**` overlap the earlier note held it behind. It runs beside PBI-006: different conflict groups (local-app Medium vs page High) and no shared file — PBI-006 touches only `site/**` and `tests/page.test.mjs`. `merge_allowed_by_agent` changed from `false` to `true` under the owner's standing merge authorisation of 2026-09-12. -->
<!-- PBI-006, PBI-025 and PBI-026 promoted and started 2026-09-12 under the owner's standing instruction to keep building the backlog ("This is for dispatch board. Lets keep building the backlog"; "Continue building"), after the owner asked why nothing was in flight. Three run at once because they do not collide: PBI-006 takes the page group's single High-risk slot, freed by PBI-011's close-out; PBI-026 is local-app (Medium) and touches only `local/records*`, `local/records.shapes.json` and `local/tests/**`; PBI-025 is local-app (Medium) but is at its SPEC gate only, which writes solely under `docs/backlog/specs/`, so it cannot collide with PBI-026 despite sharing the group and the `local/tests/**` grant. PBI-025 must not enter its build until PBI-026 lands or its own areas are re-checked. All dependencies are Done: PBI-006 needs PBI-003 and PBI-005; PBI-025 needs PBI-019; PBI-026 needs PBI-011. -->
<!-- PBI-011 promoted and started 2026-09-12 under the owner's standing instruction to keep building. It takes the page group's single High-risk slot, which PBI-008's close-out freed. merge_allowed_by_agent is true under the owner's standing merge authorisation of 2026-09-12. -->
<!-- PBI-019 and PBI-008 resumed 2026-09-11T22:08:17Z from Blocked on the owner's approval, verbatim: "ok and approved. Continue building" (PBI-019: rename the test constant the push rail flagged; PBI-008: add local/tests/test_conformance.py to allowed_areas). -->
<!-- PBI-008 promoted and started 2026-09-11 under the owner's instruction, verbatim: "This is for dispatch board. Lets keep building the backlog". Its dependencies PBI-003 and PBI-004 are Done. It is first of the page PBIs in the plan's order; the page group became free when PBI-002 closed. It runs beside PBI-019 (local-app, Medium): different groups, and FR-103's two halves write the same lastRefresh record shape. -->
<!-- PBI-019 promoted and started 2026-09-11 under the owner's instruction, verbatim: "This is for dispatch board. Lets keep building the backlog". Its dependencies PBI-003 and PBI-004 are Done. PBI-005 (same local-app group, Medium) waits for it: both edit board.config.json and exporters/board_config.py, and PBI-019 is on the critical path. -->
<!-- PBI-004 promoted and started 2026-09-11 on the owner's instruction, verbatim: "This is for dispatch board. Lets keep building the backlog". Its dependency PBI-001 is Done, and PBI-024, which it waited for (both change exporters/export_board.py), is Done. The only active row, PBI-002, is in the page group, so there is no conflict. -->

---

## In Review

| ID | Title | PR | Review verdict | Review note path |
|----|-------|----|----------------|-----------------|

---

## Blocked

| ID | Title | Blocked reason | Unblock condition | Return to |
|----|-------|---------------|-------------------|-----------|

---

## Done

| ID | Title | PR | done-log |
|----|-------|----|----------|
| PBI-017 | Agent catalogue tab: every catalogue agent and skill, grouped by purpose, with usage coverage across sessions and projects | https://github.com/jdk-official/dispatch-board/pull/1 | [↪](done-log.md#pbi-017) |
| PBI-018 | Backlog shows future iterations: a "Later" group of idea cards read from the spec's Future iterations list | https://github.com/jdk-official/dispatch-board/pull/4 | [↪](done-log.md#pbi-018) |
| PBI-022 | PRD re-baseline after project-first navigation and the plan-gate answers, with evidence for AC-84, AC-85 and AC-92 | https://github.com/jdk-official/dispatch-board/pull/3 | [↪](done-log.md#pbi-022) |
| PBI-023 | Pull requests on the board: the GitHub tab lists each project's pull requests as links, and Needs attention flags the ones awaiting the owner's merge | https://github.com/jdk-official/dispatch-board/pull/6 | [↪](done-log.md#pbi-023) |
| PBI-003 | Record shapes and SQLite schema: session, run, project, tab, status, last-refresh and catalogue records (FR-100 except the answer record; FR-101 fields; FR-102) | https://github.com/jdk-official/dispatch-board/pull/7 | [↪](done-log.md#pbi-003) |
| PBI-021 | Store leftovers clean-up: export the six unused documents to snapshot/, then delete them with the owner's explicit approval | https://github.com/jdk-official/dispatch-board/pull/2 | [↪](done-log.md#pbi-021) |
| PBI-013 | Usage limit forecast (feature 6, FR-117, FR-118) | https://github.com/jdk-official/dispatch-board/pull/9 | [↪](done-log.md#pbi-013) |
| PBI-001 | Exporter hardening: FR-80–FR-82, FR-84, carried-tab marker, config type checks, refuse an answers collection (FR-133) | https://github.com/jdk-official/dispatch-board/pull/10 | [↪](done-log.md#pbi-001) |
| PBI-024 | Carried-tab marker: the board exporter writes carriedSince on a tab it keeps from an earlier export (FR-190) | https://github.com/jdk-official/dispatch-board/pull/13 | [↪](done-log.md#pbi-024) |
| PBI-004 | Shared derivation module: extract the exporters' parsing and derivation into an importable module, behaviour unchanged | https://github.com/jdk-official/dispatch-board/pull/14 | [↪](done-log.md#pbi-004) |
| PBI-002 | Page fixes: FR-83 live-state tile, stale-tab callout, token relabel, design-rule deviations, blank-load investigation (FR-85) | https://github.com/jdk-official/dispatch-board/pull/12 | [↪](done-log.md#pbi-002) |
| PBI-019 | Collector: incremental transcript and catalogue reads into SQLite, mass-delete guard, network-path guard (FR-86–FR-88; FR-103 collector half) | https://github.com/jdk-official/dispatch-board/pull/15 | [↪](done-log.md#pbi-019) |
| PBI-008 | Stale-board warning: 'data as of' header (feature 1; FR-103 refresher half, FR-104, FR-105) | https://github.com/jdk-official/dispatch-board/pull/16 | [↪](done-log.md#pbi-008) |
| PBI-011 | Review findings ledger (feature 3, FR-111, FR-112) | https://github.com/jdk-official/dispatch-board/pull/18 | [↪](done-log.md#pbi-011) |
| PBI-005 | Local server: page, data snapshot, live push, 127.0.0.1 binding, Host and Origin checks, network-path guard (FR-92-FR-94, FR-96) | https://github.com/jdk-official/dispatch-board/pull/19 | [↪](done-log.md#pbi-005) |
| PBI-026 | Local record shapes accept the findings tab, so the local app can hold what the findings ledger publishes | https://github.com/jdk-official/dispatch-board/pull/20 | [↪](done-log.md#pbi-026) |
| PBI-006 | Page data-adapter seam: store adapter and local API adapter (FR-97-FR-99) | https://github.com/jdk-official/dispatch-board/pull/21 | [↪](done-log.md#pbi-006) |
| PBI-025 | Local tab and status records: the collector writes each project's tabs and status into the local database | https://github.com/jdk-official/dispatch-board/pull/23 | [↪](done-log.md#pbi-025) |
| PBI-014 | Run detail (feature 8, FR-121) | https://github.com/jdk-official/dispatch-board/pull/24 | [↪](done-log.md#pbi-014) |
| PBI-027 | Local collector publishes a run's files relative to the repository, so the local app matches the board | https://github.com/jdk-official/dispatch-board/pull/27 | [↪](done-log.md#pbi-027) |
| PBI-009 | 'Waiting on you' panel: detectors for pending questions, idle-after-asking and permission refusals (feature 2, FR-106–FR-110) | https://github.com/jdk-official/dispatch-board/pull/29 | [↪](done-log.md#pbi-009) |
| PBI-028 | Local record shapes name the session's waiting list and check a run's files are strings | https://github.com/jdk-official/dispatch-board/pull/31 | [↪](done-log.md#pbi-028) |
| PBI-012 | Test and coverage trend, cost per work item and per agent type (features 5 and 7, FR-114–FR-116, FR-119, FR-120) | https://github.com/jdk-official/dispatch-board/pull/34 | [↪](done-log.md#pbi-012) |
| PBI-029 | No console windows from the scheduled collector | https://github.com/jdk-official/dispatch-board/pull/35 | [↪](done-log.md#pbi-029) |
| PBI-037 | Retire the v1 artifact and its refresher: final store export, final status message, loop stopped, procedures marked retired (S-40) | https://github.com/jdk-official/dispatch-board/pull/42 | [↪](done-log.md#pbi-037) |
| PBI-007 | Log-on start through Task Scheduler and the on-PC deployment end to end (FR-90, FR-91, NFR-17, NFR-18, NFR-21) | https://github.com/jdk-official/dispatch-board/pull/28 | [↪](done-log.md#pbi-007) |
