# BOARD — dispatch-board

<!-- The section a PBI is listed under is the authoritative status (SPEC §State machine).
     PBI files: docs/backlog/pbi/. Parent spec: docs/backlog/specs/dispatch-board.md (revision 5, approved). -->

---

## Proposed

<!-- PBI-016 (Unraid deployment) was moved to Later by the owner on 2026-09-11 ("Move PBI16 to later"). It is now a Future iterations idea in docs/backlog/specs/dispatch-board.md, shown in the Backlog tab's Later group, and is no longer a planned work item. Local convention: a PBI de-scoped this way keeps its file with `status: Later` and sits in no BOARD section. The SPEC has no deferred state; this gap is noted for the backlog-delivery plugin owner. -->

| ID | Title | Depends on | Notes |
|----|-------|------------|-------|
| PBI-002 | Page fixes: FR-83 live-state tile, stale-tab callout, token relabel, design-rule deviations, blank-load investigation (FR-85) | [PBI-001] | Decomposed from the approved spec, 2026-09-11 |
| PBI-004 | Shared derivation module: extract the exporters' parsing and derivation into an importable module, behaviour unchanged | [PBI-001] | Decomposed from the approved spec, 2026-09-11 |
| PBI-019 | Collector: incremental transcript and catalogue reads into SQLite, mass-delete guard, network-path guard (FR-86–FR-88; FR-103 collector half) | [PBI-003, PBI-004] | Decomposed from the approved spec, 2026-09-11 |
| PBI-005 | Local server: page, data snapshot, live push, 127.0.0.1 binding, Host and Origin checks, network-path guard (FR-92–FR-94, FR-96) | [PBI-003, PBI-004] | Decomposed from the approved spec, 2026-09-11 |
| PBI-006 | Page data-adapter seam: store adapter and local API adapter (FR-97–FR-99) | [PBI-003, PBI-005] | Decomposed from the approved spec, 2026-09-11 |
| PBI-007 | Log-on start through Task Scheduler and the on-PC deployment end to end (FR-90, FR-91, NFR-17, NFR-18, NFR-21) | [PBI-019, PBI-005, PBI-006] | Decomposed from the approved spec, 2026-09-11 |
| PBI-008 | Stale-board warning: "data as of" header (feature 1; FR-103 refresher half, FR-104, FR-105) | [PBI-003, PBI-004] | Decomposed from the approved spec, 2026-09-11 |
| PBI-009 | "Waiting on you" panel: detectors for pending questions, idle-after-asking and permission refusals (feature 2, FR-106–FR-110) | [PBI-004] | Decomposed from the approved spec, 2026-09-11 |
| PBI-010 | Work-item status derived from runs, shown beside the hand-kept state during a shadow period (feature 4, FR-113) | [PBI-004] | Decomposed from the approved spec, 2026-09-11 |
| PBI-011 | Review findings ledger (feature 3, FR-111, FR-112) | [PBI-004] | Decomposed from the approved spec, 2026-09-11 |
| PBI-012 | Test and coverage trend, cost per work item and per agent type (features 5 and 7, FR-114–FR-116, FR-119, FR-120) | [PBI-004] | Decomposed from the approved spec, 2026-09-11 |
| PBI-014 | Run detail (feature 8, FR-121) | [PBI-003, PBI-011] | Decomposed from the approved spec, 2026-09-11 |
| PBI-020 | Timeline view (feature 9; FR-101 filled, FR-122–FR-124) | [PBI-003, PBI-004] | Decomposed from the approved spec, 2026-09-11 |

---

## Ready

<!-- Promotion notes:
     - PBI-017 was promoted 2026-09-11, authorised by the owner at the plan gate ("... start PBI-017 via code-writer → code-reviewer"). It is now Done (PR #1, 84fa3ee).
     - PBI-022 and PBI-023 were promoted 2026-09-11 under the owner's standing instruction ("keep building as per their instructions. Don't ask me what to build next"). PBI-023 is the owner's request for pull-request links ("update the artifact with this so I can access it").
     - PBI-018 was promoted 2026-09-11 under the same standing instruction, once its dependency PBI-017 reached Done. It goes before PBI-023: it is next in the approved plan order and unblocks PBI-001, PBI-003 and PBI-013. Both are in the page group at High risk, so they run one at a time.
     - PBI-021 was promoted 2026-09-11. The owner's external-review approval is recorded in its PBI file, verbatim: "approve PBI-021". The delete batch still needs its own approval (AC-S2).
     - PBI-003 was started 2026-09-11 under the standing instruction, once its dependency PBI-018 reached Done. It is local-app work at Low risk, so it runs in parallel with PBI-023 (page).
     - PBI-001 and PBI-013 were started 2026-09-11 under the standing instruction, once their dependency PBI-018 was Done and PBI-023 (page group, High risk) had deregistered. They are in different groups (exporters and page), so they run in parallel. -->

| ID | Title | Depends on | Conflict group | Conflict risk |
|----|-------|------------|----------------|---------------|

---

## In Progress

| ID | Title | Branch | Worktree | Session tag | Started (UTC) |
|----|-------|--------|----------|-------------|---------------|

---

## In Review

| ID | Title | PR | Review verdict | Review note path |
|----|-------|----|----------------|-----------------|
| PBI-001 | Exporter hardening: FR-80–FR-82, FR-84, carried-tab marker, config type checks, refuse an answers collection (FR-133) | [#10](https://github.com/jdk-official/dispatch-board/pull/10), branch `pbi/PBI-001-exporter-hardening`, squash; waiting for the owner's merge | GO-WITH-CONDITIONS (round 2; conditions applied and checked; round 1 NO-GO fixed) | docs/backlog/reviews/PBI-001/findings.json |

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
