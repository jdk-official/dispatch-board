---
title: Dispatch board — next iteration (agent catalogue, local-first app, features) and v1 defect fixes
status: approved
spec_version: 6
revision: 6
approved_revision: 6
parent_prd: docs/prd/dispatch-board.md
---

# Solution Spec — Dispatch board: next iteration and v1 defect fixes

<!-- Authored by the planner (pbi-plan) from the PRD at docs/prd/dispatch-board.md, revision 2.
     Approved at the plan gate on 2026-09-11 (see Plan-gate record). This document is the parent
     authority for every PBI it spawns. -->

**Status: revision 6 approved at the plan gate on 2026-09-19** (revision 5 was approved on 2026-09-11).
Revision 6 was approved as committed at `db14c0b` (spec blob `8fbdd3eb`); see the Plan-gate record. Markers
reading **(rev 6, draft)** date from before that approval and now mark what revision 6 added. Revision 6's
PBIs (PBI-031 to PBI-038) are decomposed only after the owner reviews the batch.

**Revision history.**
- **Revision 2:** the owner added PBI-017 (the agent catalogue tab, built first) and PBI-018 (future iterations on the Backlog).
- **Revision 3:** applied plan-gate review round 1 and the owner's answers. Answers from the board are deferred; the local app goes on the PC first; the repo is private; the defaults are accepted.
- **Revision 4:** applied review round 2: acceptance criteria for PBIs the PRD does not cover, dependency edges that enforce order, and a catalogue record.
- **Revision 5 (2026-09-11):** applied the round-3 notes (APPROVE-WITH-NOTES; `docs/backlog/reviews/dispatch-board/plan-gate-review-r3.md`) and the owner's changes to PBI-017: "Include skills too" and "Show what each agent is for". It records the owner's approval.
- **Post-approval amendment (2026-09-11):** the owner moved PBI-016 (Unraid deployment) to Future iterations ("Move PBI16 to later"). Its PBI-list row is removed, and ordering item 5 and rows 5 and 6 are amended. Its areas, its go-ahead entry and the Unraid parts of the scope are kept, marked deferred, so the idea can be revived. There is no other plan change, and no re-review, since this is a de-scope the owner asked for.
- **Revision 6 (2026-09-19, draft):** the owner pulled four ideas out of Future iterations: answering assumptions from the board, using answers for approvals, retiring the hand-kept build state, and retiring the v1 artifact and its refresher. Revision 6 adds goals G-8 to G-11, scope, key decisions, eight proposed PBIs (PBI-031 to PBI-038, under "Revision 6 (draft)" in the decomposition rationale), trigger criteria T3 and T4 for the two retirements, and ledger rows 25 to 47. It needs the independent review, the owner's approval and the owner's confirmation of the ASSUMED rows before anything is decomposed.
- **Revision 6, round 2 after plan-gate-review-r4 (2026-09-19, draft):** applies round 4 (CHANGES-REQUIRED, PG6-1 to PG6-18; dispositions in the Plan-gate record). Alarms become durable records the owner clears on the board, and a board answer is honoured only while no alarm is uncleared. A plan approval binds to the committed text the owner saw and also needs a chat confirmation. The tripwire (PBI-033) now comes before the write surface (PBI-031). PBI-038 covers the three test modules that import `refresh.py`. Rows 48 to 50 are added; rows 40 and 45 become resolved facts, with their choices in rows 48 and 49.
- **Revision 6, round 3 after plan-gate-review-r5 (2026-09-19, draft):** applies round 5 (CHANGES-REQUIRED, PG6-r5-1 to PG6-r5-13) and the owner's answer to the trust question it raised: "Just procees as if it were me" (row 32). A board answer is trusted as the owner's. The tripwire becomes an audit record that marks answers possibly made by an agent, and no longer decides whether an answer counts, so durable alarms, alarm clearance and the honour rule's alarm check are removed. PBI-033 moves off the critical path, behind PBI-032 and PBI-030. A plan approval binds to git's own blob id of the committed spec, computed with git on every side (PG6-r5-4). Dispositions are in the Plan-gate record.
- **Revision 6, round 4 after plan-gate-review-r6 (2026-09-19, draft):** applies round 6 (CHANGES-REQUIRED, PG6-r6-1 to PG6-r6-13) and the owner's answers to rows 25, 34 and 37: "Accept, this PC only (Recommended)", "Board approval alone" and "retire it now". The artifact is frozen now (PBI-037, no longer triggered or held behind PBI-007), and the push path is removed once PBI-007's log-on demonstration is accepted and a 7-day undo window has passed (PBI-038). A board plan approval passes the plan gate by itself: the chat step is removed, the planner picks approvals up from `local/answers.py list`, and an approval accepts every row still ASSUMED in the approved text. The approval path is tightened (exit codes, exact-case paths, the order of the transcription commits, squash merges). Rows 25, 34 and 37 are CONFIRMED; row 50 is raised to High.
- **Revision 6, round 5 after plan-gate-review-r7 (2026-09-19, draft):** applies round 7's notes (APPROVE-WITH-NOTES, PG6-r7-1 to PG6-r7-8) as a text pass: the frozen artifact takes no store writes, the approval's transcription is its own PR, and the approval question is written out. No structural change.

**Already delivered, not re-planned here:**
- **v1:** the session picker, generated runs and the refresher loop.
- **Project-first navigation** (PRD D-18; FR-129, FR-130, FR-135 to FR-148), shipped in commit `2742ca6`. Its review history: GO-WITH-CONDITIONS, fixes, then GO.
- **The tab-bar overflow fix** (FR-125 to FR-128), in the same change (row 2).

---

## Goals

- **G-1** The owner can trust what the board shows: the v1 defects the reviews left open are closed, a carried-over tab is flagged on the page, and config typos fail loudly instead of changing behaviour (PRD O-6, FR-80–FR-85).
- **G-2** The board stays current from log-on onwards with no Claude session open and no Claude usage spent on refreshing, on the owner's PC first and optionally on the Unraid server (PRD O-8, D-16, D-17).
- **G-3** Moving to a host later changes only storage and transport: one set of record shapes, including the catalogue, and one data adapter in the page (PRD O-9, D-16).
- **G-4** The owner sees at a glance when data is stale and everything that is waiting on them (PRD O-10, features 1–2).
- **G-5** The owner sees each build's progress from its runs, alongside the hand-kept state until the derived state is trusted: findings, work-item state, test trend, cost, run detail, timeline and a usage-limit forecast (PRD O-11, features 3–9).
- **G-6** No agent, refresher or collector can ever write a plan-gate answer to the board (PRD C-16, FR-133, FR-134). The answer write path itself is deferred (row 5). *Rev 6 proposes rewording its first sentence (G-8).*
- **G-7** The owner can see every agent and skill in the agent catalogue, grouped by what it is for, and how much of it the projects use: uses per entry, when it was last used, which projects used it, and what has never been used (owner request, 2026-09-11; built first).
- **G-8** (rev 6, draft) The owner can answer an assumption row awaiting them from the board on their PC: Accept its default, or Override it with an answer and a note. Each answer is kept with its provenance (project, spec, revision, row, exact text, time, surface) and reaches the spec's ledger only through a transcription that a check can verify against the stored answer (PRD FR-95, FR-131, FR-132, NFR-23, AC-87; S-37). When approved, this goal replaces G-6's last sentence, and G-6's first sentence becomes "No refresher or collector writes a plan-gate answer, and an answer given on the board counts as the owner's, whoever gave it; answers that look agent-made are marked for the owner to see" (row 32). G-6's guards on the refresher and the collector stay.
- **G-9** (rev 6, draft) The owner can approve a solution-spec revision and accept a review's conditions from the board, bound to the exact committed text or run they approve, so an approval cannot be reused for text or a run the owner never saw (PRD S-31). A board plan approval passes the plan gate by itself (row 34).
- **G-10** (rev 6, draft) The hand-kept work-item state is retired for a project only once trigger T3 shows the derived state is trusted, and the owner decides (PRD S-39, row 15).
- **G-11** (rev 6, draft) The v1 artifact and its refresher are retired now, at the owner's word ("retire it now", row 37): the artifact is frozen, reversibly, as soon as this revision is approved (PBI-037). The dead push path is removed only once PBI-007's log-on demonstration is accepted and a 7-day undo window has passed (PBI-038, T4.4) (PRD S-40, row 8, ADR-0001).

---

## Scope

### In scope

- `exporters/**` — the defect fixes FR-80 to FR-84, the carried-tab marker and config type checks, the refusal of an `answers` collection (FR-133), the catalogue export (PBI-017, a new `exporters/export_catalogue.py` run by `refresh.py`), the future-iterations list (PBI-018), and a shared derivation module that the exporters and the collector both use (PBI-004), plus the derivations features 2 to 7 need.
- `site/**` — the page defect FR-83 and the design-rule deviations (row 13), the agent catalogue tab, the Later group on the Backlog, the stale-board warning, the "Waiting on you" panel, findings ledger, test trend, cost per work item, usage-limit forecast, run detail, timeline, and the data-adapter seam.
- `local/**` — new: record shapes and the SQLite schema (including the catalogue), collector, local server (page, snapshot, live push), and Task Scheduler log-on start. There is no answers endpoint (row 5). *Deferred to Future iterations (2026-09-11, the owner's "Move PBI16 to later"):* the Unraid ingest endpoint and the optional Unraid container definition.
- `board.config.json`, `exporters/board_config.py`, `projects/**` — new keys for the catalogue paths, the local server port and the database path; the derived-state shadow period (PBI-010).
- `docs/adr/0001-local-first-architecture.md` — accepted at this plan gate (row 8).
- `docs/prd/**`, `docs/backlog/evidence/**`, `CLAUDE.md`, `README.md` — procedures for the local app, the C-16 rule ("no agent writes answers") and the PRD re-baseline (PBI-022).
- The agent catalogue, read only: `~/.claude/plugins/marketplaces/agent-catalog/plugins/*/agents/*.md`, `~/.claude/plugins/marketplaces/agent-catalog/plugins/*/skills/*/SKILL.md` and `~/.claude/plugins/installed_plugins.json`. It is never written.
- `snapshot/**` — export of the six store leftovers before their owner-approved deletion (PBI-021).
- (rev 6, draft) `local/server*`, `local/records*`, `local/schema*`, `local/answers*`, `local/tests/**`, `board.config.json`, `exporters/board_config.py` — the answer record, a separate answers database written only by the local server, the `POST /api/answers` endpoint and its checks, a nonce content-security policy for the served page, and the `local/answers.py` list and verify tool (PBI-031, PBI-034).
- (rev 6, draft) `exporters/derive.py`, `exporters/export_sessions.py`, `local/records*`, `tests/test_*.py`, `site/**` — an answer audit: transcript tool calls that could have sent an answer, shown beside the answers they may have made (PBI-033).
- (rev 6, draft) `site/**`, `tests/page.test.mjs` — Accept and Override on the Assumptions tab, plan approval on the Spec tab and conditions acceptance on the Backlog, on the local adapter only (PBI-032, PBI-035); and, after trigger T4.4, removal of the store adapter (PBI-038).
- (rev 6, draft) `CLAUDE.md`, `README.md`, `docs/adr/0002-*`, `docs/backlog/evidence/**`, `snapshot/**` — the answer rules and the transcription procedure, ADR-0002, the trigger evidence for T3 and T4, and the final store export (PBI-033, PBI-036, PBI-037).
- (rev 6, draft) Deleting `exporters/refresh.py` and `tests/test_refresh.py` once the refresher is retired, and moving the three other test modules that import it off it (PBI-038).

### Out of scope

- Re-planning v1 or project-first navigation (delivered, `2742ca6`).
- Answering assumptions from the board, deferred by the owner on 2026-09-11 (row 5; listed under Future iterations). This defers:
  - FR-95, FR-131 and FR-132;
  - NFR-23 and AC-87;
  - the answer record of FR-100;
  - the answers endpoint.

  The guards FR-133 and FR-134 stay in the plan. *Rev 6 proposes moving this into scope (G-8, PBI-031 to PBI-033), on the local app only.*
- (rev 6, draft) Answering, or approving, from the published artifact or from anywhere but the owner's PC. The artifact's store is not an answer surface (row 25).
- (rev 6, draft) Any process writing answers, approvals or ledger rows into repo files. The collector, the server and the refresher never write a spec; the planner or orchestrator transcribes, and `local/answers.py verify` checks the transcription (row 29).
- (rev 6, draft) Approvals other than a solution-spec plan approval and the acceptance of a review's conditions: `requires_external_review` go-aheads, merges, store deletes (C-12), Task Scheduler changes and per-PBI spec-gate rows stay in chat (row 33).
- (rev 6, draft) Changing the backlog-delivery plugin (`~/.claude/plugins/**`). The workflow honours a board approval through this repo's documented procedure, not a plugin change (row 34).
- (rev 6, draft) A login, account or authentication on the local server; a remote replacement for the artifact (Unraid stays deferred, Azure stays a future iteration); deleting the artifact or its store (row 38).
- Hosting on Azure and the hosted API adapter (PRD S-27, S-28); the seam is in scope, the hosted adapter is not.
- Phone notifications (PRD S-29) and an archive older than 7 days (PRD S-30, D-15).
- Continuous integration (PRD S-16), and redacting titles, run labels or agent descriptions (PRD S-17, D-12).
- Hooks in build sessions that report to the board, and hand-written runs (PRD S-11, S-12).
- Marketplaces other than agent-catalog in the catalogue tab (Future iterations).
- `C:/Users/jdk/platform-catalogue/**`: the tracked build repo is read, never written.

---

## Key decisions

| Decision | Rationale | Made by | Date |
|----------|-----------|---------|------|
| Build the agent catalogue tab (PBI-017) first | Owner request: "Can we add a PBI for a new tab to show all the agents in the catalogue with coverage of what we are using? Make this the first thing we build." | Owner | 2026-09-11 |
| The catalogue tab covers skills as well as agents, grouped by what each is for | Owner's changes to PBI-017's criteria at the plan gate: "Include skills too", "Show what each agent is for" | Owner | 2026-09-11 |
| Defer answering assumptions from the board; keep answering in chat | Owner answer at the plan gate (row 5). The guards that stop agents writing answers stay in the plan (G-6) | Owner | 2026-09-11 |
| Make the GitHub repo private | Owner answer at the plan gate (row 3) about the committed `snapshot/` of build data | Owner | 2026-09-11 |
| Local app on the owner's PC first; Unraid last and optional | Owner answer at the plan gate (row 6) | Owner | 2026-09-11 |
| Local first, hosting later: collector → SQLite → local server → page through one data adapter; record shapes defined once — [ADR-0001](../../adr/0001-local-first-architecture.md) (accepted) | Owner decision D-16; the stdlib-only technology choice was confirmed at this gate (row 8) | Owner (D-16), planner | 2026-09-11 |
| Unraid is the optional first host; the collector stays on the PC and sends records over the LAN; SQLite never on a network share | Owner decision D-17: transcripts exist only on the PC; SQLite locking over SMB/NFS is unreliable | Owner (D-17) | 2026-09-11 |
| All derivations live in one shared module under `exporters/`; the collector imports it, never re-implements it | Keeps the artifact board and the local app identical (PRD FR-87, AC-64); plan-gate review M-8 | Planner | 2026-09-11 |
| Ordering is enforced by `depends_on` edges and by registering every PBI that edits `site/**` in the `page` group at High risk | The coordinator's eligibility check reads only `depends_on` and `conflict_group`; plan-gate review R2-M1 | Planner | 2026-09-11 |
| Code changes go through `engineering-agents:code-writer` (TDD) then `review-agents:code-reviewer` until GO | Owner decision D-9 | Owner (D-9) | 2026-09-10 |
| (rev 6, draft) Plan the four pulled ideas now. Retire the hand-kept state only when trigger T3 is met; freeze the artifact now, and remove the push path once T4.4 is met | Owner pulled them from Future iterations on 2026-09-19, and answered "retire it now" for the artifact (row 37). A trigger is checked at promotion from Proposed to Ready. Freezing is reversible while `exporters/refresh.py` exists, so the irreversible step (PBI-038) waits for PBI-007's log-on demonstration, the only proof the board returns after a reboot with no Claude session | Owner (pull; row 37); planner (T3, T4.4) | 2026-09-19 |
| (rev 6, draft) Answers are recorded on the local app only, through `POST /api/answers`, into a separate answers database the local server alone writes. The artifact store is not an answer surface — [ADR-0002](../../adr/0002-board-answers-count-as-the-owners.md) (accepted) | The artifact is what item 4 retires, so an answer path built there would be removed with it. The store also can't tell the owner from Claude writing as the owner (C-1). The local app outlives the artifact (row 25) | Owner (row 25); planner | 2026-09-19 |
| (rev 6, draft) The board database stays read-only in the server and written only by the collector; answers live in their own file | Keeps the invariant that the two processes never fight (`CLAUDE.md` "The local app on this PC"), keeps the collector's age pruning and mass-delete guard away from answers, and keeps the existing no-answers-table tests true for the board database (row 28) | Planner (proposed; row 28) | 2026-09-19 |
| (rev 6, draft) No process writes an answer into a repo file. The planner or orchestrator transcribes it into the ledger or the Plan-gate record, citing `answer:<id>`, and `python local/answers.py verify <spec>` checks every citation against the stored answer | Nothing writes repo files today (row 29). Automatic spec edits would give the server write access to the project repos, including platform-catalogue, which is read, never written | Planner (proposed; row 29) | 2026-09-19 |
| (rev 6, draft) A board answer is trusted as the owner's, whoever gave it. The transcript tripwire is an audit record, not a gate — [ADR-0002](../../adr/0002-board-answers-count-as-the-owners.md) (accepted) | No login-free design can stop an agent on this PC answering as the owner: it can drive a browser, edit the board database or stop the collector (round 5, PG6-r5-1 to PG6-r5-3; row 26). Asked how a board answer should be trusted, the owner answered "Just procees as if it were me". Only the server's POST handler builds an answer, `CLAUDE.md` tells agents not to answer, and answers that look agent-made are marked for the owner to see (row 32) | Owner | 2026-09-19 |
| (rev 6, draft) Two approvals go through answers: a plan approval, bound to git's blob id of the committed spec the owner saw, and a conditions acceptance, bound to one review run. Each is honoured once transcribed with a clean `verify`; a board plan approval passes the plan gate by itself — [ADR-0002](../../adr/0002-board-answers-count-as-the-owners.md) (accepted) | Binding stops an approval being reused for text or a run the owner never saw. `verify` checks the transcription is faithful. The owner chose board approval alone (row 34). Everything else stays in chat (rows 33, 34, 50) | Owner (row 34); planner (rows 33, 50) | 2026-09-19 |
| (rev 6, draft) Retiring the artifact freezes it rather than deleting it: a final store export and status message, the refresher stopped now, and the push-path code removed after PBI-007's log-on demonstration and a 7-day undo window | Keeps the step reversible until the code goes. Deletion is the owner's own act and is not planned (rows 37, 38) | Planner (proposed; rows 37 **High**, 38) | 2026-09-19 |
| (rev 6, draft) ADR-0002, "The page records answers through the local server", is written at this revision's plan gate, row 25 now being confirmed — [ADR-0002](../../adr/0002-board-answers-count-as-the-owners.md) (accepted) | PRD C-17 requires an accepted ADR before the page may write (FR-64, FR-183). It meets the ADR bar: hard to reverse, not evident from the code, and the store route was rejected (row 39) | Planner | 2026-09-19 |

---

## Decomposition rationale

The work splits into six tracks. Each PBI's acceptance criteria are the PRD's ACs for the
requirements it names. PBI-017, PBI-018, PBI-021 and PBI-022 have no PRD requirements, so they take
the criteria listed in this spec, under "Acceptance criteria for PBIs the PRD does not cover" (row 16).

0. **Agent catalogue and the Backlog "Later" group (PBI-017, PBI-018)** come first, at the owner's request. Every other code PBI depends on PBI-018 directly or through its own dependencies. PBI-017 is `requires_spec: true`: its refined spec, which adds skills and purpose groups, gets an independent spec-gate review before any code is written.
1. **Hardening (PBI-001, PBI-002)** closes the v1 defects and adds the answers guard (FR-133). Two owner-driven chores run whenever the owner chooses: the store clean-up (PBI-021) and the PRD re-baseline (PBI-022).
2. **Shared derivation (PBI-004)** extracts the exporters' logic into one importable module without changing behaviour. Every feature derivation, and the collector, then builds on it.
3. **Local-first foundation (PBI-003, PBI-019, PBI-005, PBI-006, PBI-007)**, in this order:
   1. record shapes and the SQLite schema;
   2. the collector;
   3. the local server;
   4. the page's data adapter;
   5. the log-on start and end-to-end check.
4. **Features on the current board (PBI-008 to PBI-014, PBI-020)** work on the artifact today through the store adapter, and in the local app once PBI-006 lands.
5. **Unraid (PBI-016)** is last and optional (row 6). **Moved to Future iterations by the owner on 2026-09-11** ("Move PBI16 to later"); it is no longer a planned work item.

**How ordering is enforced.** The coordinator reads only `depends_on` and `conflict_group`, so:
- **Page PBIs run one at a time.** Every PBI that edits `site/**` is registered in the `page` group at `conflict_risk: High`, so no two start together.
- **Exporter work is ordered by edges.** A page PBI that also edits `exporters/**` depends on PBI-001, or on PBI-004 for feature derivations and for `refresh.py`. That puts it after the exporter-only PBIs.
- **Other areas.** Touches of `config` and `docs` are listed in each PBI's areas, for people reading the plan.
- **Exempt:** the two owner-driven chores, PBI-021 and PBI-022, share no code area.
- **One accepted overlap.** PBI-019 and PBI-005 may run in parallel, and each adds one key to `board.config.json` and `exporters/board_config.py` (the database path and the port). The second to land merges that small change; the owner merges both.

**Metadata proposed for every PBI:**
- `pr_required: true` and `merge_allowed_by_agent: false` (the owner merges).
- `change_class: standard`, except PBI-022, which is `trivial`. PBI-021 is `standard`, because its core act is an irreversible store delete (review L9).

### PBI list (proposed)

| ID | Title | Depends on | Conflict group | Conflict risk | Requires spec | Requires ext. review |
|----|-------|------------|----------------|---------------|---------------|----------------------|
| PBI-017 | Agent catalogue tab: every catalogue agent and skill, grouped by purpose, with usage coverage across sessions and projects | [] | page | High | true | false |
| PBI-018 | Backlog shows future iterations: a "Later" group of idea cards read from the spec's Future iterations list | [PBI-017] | page | High | false | false |
| PBI-001 | Exporter hardening: FR-80–FR-82, FR-84, carried-tab marker, config type checks, refuse an answers collection (FR-133) | [PBI-018] | exporters | Medium | false | false |
| PBI-002 | Page fixes: FR-83 live-state tile, stale-tab callout, token relabel, design-rule deviations, blank-load investigation (FR-85) | [PBI-001] | page | High | false | false |
| PBI-021 | Store leftovers clean-up: export the six unused documents to snapshot/, then delete them with the owner's explicit approval | [] | docs | Low | false | true |
| PBI-022 | PRD re-baseline after project-first navigation and the plan-gate answers, with evidence for AC-84, AC-85 and AC-92 | [] | docs | Low | false | false |
| PBI-004 | Shared derivation module: extract the exporters' parsing and derivation into an importable module, behaviour unchanged | [PBI-001] | exporters | Medium | false | false |
| PBI-003 | Record shapes and SQLite schema: session, run, project, tab, status, last-refresh and catalogue records (FR-100 except the answer record; FR-101 fields; FR-102) | [PBI-018] | local-app | Low | true | false |
| PBI-019 | Collector: incremental transcript and catalogue reads into SQLite, mass-delete guard, network-path guard (FR-86–FR-88; FR-103 collector half) | [PBI-003, PBI-004] | local-app | Medium | true | false |
| PBI-005 | Local server: page, data snapshot, live push, 127.0.0.1 binding, Host and Origin checks, network-path guard (FR-92–FR-94, FR-96) | [PBI-003, PBI-004] | local-app | Medium | true | false |
| PBI-006 | Page data-adapter seam: store adapter and local API adapter (FR-97–FR-99) | [PBI-003, PBI-005] | page | High | false | false |
| PBI-007 | Log-on start through Task Scheduler and the on-PC deployment end to end (FR-90, FR-91, NFR-17, NFR-18, NFR-21) | [PBI-019, PBI-005, PBI-006] | local-app | Low | false | true |
| PBI-008 | Stale-board warning: "data as of" header (feature 1; FR-103 refresher half, FR-104, FR-105) | [PBI-003, PBI-004] | page | High | false | false |
| PBI-009 | "Waiting on you" panel: detectors for pending questions, idle-after-asking and permission refusals (feature 2, FR-106–FR-110) | [PBI-004] | page | High | true | false |
| PBI-010 | Work-item status derived from runs, shown beside the hand-kept state during a shadow period (feature 4, FR-113) | [PBI-004] | page | High | true | true |
| PBI-011 | Review findings ledger (feature 3, FR-111, FR-112) | [PBI-004] | page | High | false | false |
| PBI-012 | Test and coverage trend, cost per work item and per agent type (features 5 and 7, FR-114–FR-116, FR-119, FR-120) | [PBI-004] | page | High | false | false |
| PBI-013 | Usage limit forecast (feature 6, FR-117, FR-118) | [PBI-018] | page | High | false | false |
| PBI-014 | Run detail (feature 8, FR-121) | [PBI-003, PBI-011] | page | High | false | false |
| PBI-020 | Timeline view (feature 9; FR-101 filled, FR-122–FR-124) | [PBI-003, PBI-004] | page | High | true | false |

### Acceptance criteria for PBIs the PRD does not cover

These criteria are this spec's own (row 16). Each PBI file copies them at decomposition.

**PBI-017, agent catalogue tab** (G-7; rows 19–22). Its per-PBI spec refines these criteria and is reviewed before code:
- **AC-C1** A new exporter, `exporters/export_catalogue.py`, which `refresh.py` runs alongside the other exporters, shall write one document, `catalogue/index`. It lists every entry found in the marketplace:
  - agents: `<marketplacePath>/plugins/*/agents/*.md`;
  - skills: `<marketplacePath>/plugins/*/skills/*/SKILL.md`.

  Each entry carries its kind (agent or skill), plugin, name, full description from its frontmatter, and whether its plugin is installed (from the `<plugin>@agent-catalog` keys in the installed-plugins file). Two new `catalogue` keys in `board.config.json` hold `marketplacePath`, defaulting to `~/.claude/plugins/marketplaces/agent-catalog`, and `installedPath`, defaulting to `~/.claude/plugins/installed_plugins.json`. Tests pass their own paths and never read the real `~/.claude`.
- **AC-C2** The tab shall group entries by purpose. Each group is one plugin (for example engineering, review, security, expert, platform, workflow, backlog delivery, governance), with a one-line purpose from the plugin's manifest where it has one, and otherwise the plugin name. Each entry shows its full description, so the owner can see what each agent or skill is for.
- **AC-C3** Usage shall be derived from the transcripts:
  - **agent use:** each subagent run document carries its `agentType`, for example `review-agents:code-reviewer`; `runs.manual` rows carry none;
  - **skill use:** each session document records, from its main transcript, a count and a last-use time per skill, counting `Skill` tool calls (`input.skill`, for example `backlog-delivery:pbi-plan`) and `/<plugin>:<skill>` slash commands;
  - **outside the catalogue:** agent types and skills seen but not in the catalogue, such as `Plan`, `general-purpose` and `artifact-design`, are listed separately.
- **AC-C4** For each entry, the tab shall show:
  - its use count;
  - its last use;
  - the projects whose sessions used it;
  - "never used" when there are none.

  These figures cover the sessions the board exports: the last 7 days plus every linked session.
- **AC-C5** A new "Agent catalogue" tab shall appear after Dispatch in every view. It follows the picker and session filter, and shows the all-sessions figure beside each count. Two summary tiles, "N of M agents used" and "N of M skills used", count usage in the current view and show the all-sessions figure beside it.
- **AC-C6** The refresh script shall manage the `catalogue` collection. It shall refuse, without `--allow-mass-delete`, any plan that deletes `catalogue/index`. If the marketplace folder is missing, the exporter shall keep the last catalogue export and print a warning, rather than blank the tab.
- **AC-C7** The tests shall cover:
  - the catalogue export, against a synthetic marketplace folder and installed-plugins file;
  - skill-use counting, against synthetic transcripts with `Skill` tool calls and slash commands;
  - the tab in a project view and in "Other sessions" (the page test).

  Both suites shall be green.

**PBI-018, future iterations on the Backlog** (row 23):
- **AC-L1** The board exporter shall read each bullet under a spec's `### Future iterations (not planned)` heading into the backlog document as a `later` item. The item's title is the bullet's first bold span, and its description is the rest of the bullet with any leading colon removed.
- **AC-L2** The Backlog tab shall show `later` items as a separate "Later" group of neutral idea cards below the PBIs. They shall never be counted in the PBI totals or in "Needs attention".
- **AC-L3** A spec without that heading, such as platform-catalogue's, shall produce no Later group and no error.

**PBI-021, store leftovers clean-up** (row 4):
- **AC-S1** Before any delete, the published artifact shall be read and confirmed to be the project-first version, and `tabs/usage`, `tabs/spec`, `tabs/assumptions`, `tabs/decisions`, `tabs/backlog` and `tabs/git` shall be exported to `snapshot/tabs/` and committed.
- **AC-S2** The owner's approval of the named six-document delete batch shall be recorded verbatim in the PBI's evidence before the batch runs.
- **AC-S3** After the batch, the store shall hold none of the six documents, and the published page shall still render every project's tabs.

**PBI-022, PRD re-baseline** (review L-3, R2-L4, round-3 L4):
- **AC-R1** PRD revision 3 shall describe the tree after project-first navigation as its baseline: Part A re-baselined and the supersession table resolved.
- **AC-R2** The re-baseline shall record every decision made since PRD revision 2:
  - every PRD A-row that a ledger row of this spec settles is marked settled, citing the row;
  - D-1 is superseded, because the repo is now private;
  - rows 5, 6 and 8 and PBI-017 with the owner's changes are recorded as decisions;
  - brief decisions 19 and 20 are recorded;
  - the brief's line "public on GitHub" is corrected.
- **AC-R3** Evidence for AC-84, AC-85 and AC-92 shall be recorded under `docs/backlog/evidence/`, as demonstration notes or screenshots.

### Future iterations (not planned)

These are ideas the owner has recorded for after this iteration. They are not PBIs and carry no
metadata. PBI-018 shows them on the Backlog tab as a separate "Later" group. On 2026-09-19 the owner
pulled four ideas from this list into revision 6 (draft): answering assumptions from the board, using
answers for approvals, retiring the hand-kept build state, and retiring the v1 artifact and its
refresher. They are planned under "Revision 6 (draft)" below and are no longer listed here.

- **Unraid deployment (formerly PBI-016)**: the collector uploads records over the LAN to an ingest endpoint on the Unraid server, which reads its shared secret from the environment, rejects answers, and ships as a container definition (FR-89, FR-134, AC-71, AC-72). The owner moved it here on 2026-09-11 ("Move PBI16 to later"). Rows 6, 7 and 24 still describe how it would be exposed and hardened when it is revived.
- **Phone notifications**: a review returns NO-GO, a run is cut off, the build goes idle, a session is waiting on the owner (brief "Future iteration"; PRD S-29).
- **Hosting on Azure**: Static Web Apps, Functions, a database and Entra ID, plus the hosted API adapter (PRD S-27, S-28, D-17).
- **Archive beyond 7 days**: keep sessions and runs older than the 7-day window (PRD S-30, D-15).
- **Continuous integration**: run both test suites on every push (PRD S-16).
- **Other marketplaces in the catalogue tab**: agents and skills from marketplaces other than agent-catalog (row 19).

### Allowed and blocked areas (per PBI)

Every page PBI must meet the design rules for new views (PRD NFR-22). Every PBI may update
`CLAUDE.md` and `README.md` for its own procedures (a declared `docs` touch).

- **PBI-017**: allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`, `board.config.json`, `exporters/board_config.py`, `CLAUDE.md`, `README.md`; blocked `local/**`. It also touches the `exporters` and `config` groups. It reads the catalogue under `~/.claude/plugins` and never writes it.
- **PBI-018**: allowed `exporters/export_board.py`, `tests/test_export_board.py`, `site/**`, `tests/page.test.mjs`, `CLAUDE.md`; blocked `local/**`. It also touches `exporters`.
- **PBI-001**: allowed `exporters/**`, `tests/test_*.py`, `CLAUDE.md`; blocked `site/**`, `local/**`. It also adds the C-16 rule to `CLAUDE.md`: no agent writes answers or calls an answers endpoint.
- **PBI-002**: allowed `site/**`, `tests/page.test.mjs`; blocked `exporters/**`, `local/**`.
- **PBI-021**: allowed `snapshot/**` and the six store deletes named in AC-S1, only after AC-S1 and AC-S2 hold.
- **PBI-022**: allowed `docs/prd/**`, `docs/backlog/evidence/**`, `docs/brief/raw-notes.md` (the one "public on GitHub" line); blocked `docs/backlog/specs/**`, `docs/backlog/BOARD.md`, `docs/backlog/reviews/**`.
- **PBI-004**: allowed `exporters/**`, `tests/test_*.py`; blocked `site/**`, `local/**`. There is no behaviour change: the existing suites stay green unchanged.
- **PBI-003**: allowed `local/records*`, `local/schema*`, `local/tests/**`; blocked `site/**`, `exporters/**`. It defines:
  - the run record's start and end fields (FR-101), which PBI-020 fills;
  - the run record's `agentType`;
  - per-session skill use;
  - the catalogue record.
- **PBI-019**: allowed `local/collector*`, `local/db*`, `local/tests/**`, `board.config.json`, `exporters/board_config.py` (the database path key; it also touches `config` and `exporters`); blocked `site/**`. Its spec covers:
  - WAL mode;
  - change signalling for the server (`PRAGMA data_version` polling);
  - a mass-delete guard equivalent to FR-49;
  - age-only pruning;
  - the network-path guard (FR-96) in the collector;
  - the catalogue read (reusing PBI-017's logic through the shared module);
  - the collector's half of the last-refresh write (FR-103).
- **PBI-005**: allowed `local/server*`, `local/tests/**`, `board.config.json`, `exporters/board_config.py` (the port key; it also touches `config` and `exporters`); blocked other `exporters/**` files and `site/**`. Its spec covers:
  - 127.0.0.1 binding (NFR-19);
  - a Host-header allow-list, an Origin check on every non-GET request, and no CORS (row 24);
  - the network-path guard (FR-96, NFR-20);
  - a server-level check that a database change reaches connected clients;
  - wrapping the content-only page (PRD C-8).
- **PBI-006**: allowed `site/**`, `tests/page.test.mjs`; blocked `exporters/**`, `local/**`.
- **PBI-007**: allowed `local/deploy/**`, `local/tests/**`, `README.md`, `CLAUDE.md`; blocked `site/**`, `exporters/**`. It registers a Task Scheduler task, a persistent change to the owner's system, so the owner approves it or runs the documented script. It owns the end-to-end checks NFR-17, AC-70, NFR-18 and AC-68.
- **PBI-008**: allowed `exporters/refresh.py`, `tests/test_refresh.py`, `site/**`, `tests/page.test.mjs`; blocked `local/**` (the collector's half is PBI-019's). It also touches `exporters`.
- **PBI-009**: allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`. Its spec confirms the transcript record types against real transcripts before any detector is built (row 10). It also touches `exporters`.
- **PBI-010**: allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`, `projects/**` (read and annotate only; never delete a data file). It also touches `exporters` and `config`. Its spec defines:
  - how derived state reaches the Backlog tab, given that `refresh.py` runs `export_board.py` before `export_sessions.py`;
  - a shadow period showing derived and hand-kept state side by side, with differences flagged;
  - hand-kept `review`, `open` and `commit` staying as overrides (row 15).
- **PBI-011, PBI-012**: allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`. They also touch `exporters`.
- **PBI-013**: allowed `site/**`, `tests/page.test.mjs` only. It reads the limit reset times the session docs already carry (`usage.limits[].resetsAt`).
- **PBI-014**: allowed `site/**`, `tests/page.test.mjs`, `exporters/**`, `tests/test_*.py`. It also touches `exporters`.
- **PBI-020**: allowed `site/**`, `tests/page.test.mjs`, `exporters/**`, `tests/test_*.py` (run start and end times in the store docs). It also touches `exporters`.
- **PBI-016** *(deferred to Future iterations, 2026-09-11; kept for revival, not planned work)*: allowed `local/server*`, `local/collector*` (the upload half of FR-89), `local/deploy/**`, `local/tests/**`, `README.md`; blocked `site/**`.
  - The shared secret is read from an environment variable or a git-ignored file, on both the collector and the server, never from `board.config.json`.
  - The ingest endpoint rejects answer records (FR-134, AC-88).
  - The Host allow-list is extended to the Unraid server's configured LAN hostname and address (row 7).
  - No answers endpoint exists on the LAN.

### Sequencing notes

- **First:** PBI-017. **Second:** PBI-018 (it depends on PBI-017). Every other code PBI depends on PBI-018 directly or through its own dependencies, and every page PBI is High in `page`, so nothing runs beside them.
- **Any time, owner-driven:** PBI-021 (when the owner approves the delete batch) and PBI-022. Both are exempt from the ordering above and share no code area.
- **After PBI-018:** PBI-001 (`exporters`), PBI-003 (`local-app`) and PBI-013 (`page`) can run in parallel.
- **After PBI-001:** PBI-002 and PBI-004. **After PBI-004:** PBI-008 to PBI-012 and PBI-020 (page PBIs, one at a time), and PBI-019 and PBI-005 (once PBI-003 is done).
- **Critical path to "no Claude session needed":** PBI-017 → PBI-018 → PBI-001 → PBI-004 → PBI-019 and PBI-005 → PBI-006 → PBI-007.
- **The derivation rule.** Features 2 to 7 are built in the shared module under `exporters/`, and the collector imports them. Whichever of PBI-019 and a feature PBI lands second extends the AC-64 equivalence fixture to the new fields.
- **Owner go-ahead before implementation** (`requires_external_review: true`):
  - PBI-021 (a store delete);
  - PBI-007 (a Task Scheduler task);
  - PBI-010 (changes the build session's workflow);
  - ~~PBI-016 (LAN exposure; optional, row 6)~~: deferred to Future iterations on 2026-09-11. It needs the owner's go-ahead again if revived.

### Revision 6 (draft): tracks

Nothing in this section is approved. It is kept out of the `### PBI list (proposed)` table on purpose,
so the Backlog tab does not show these PBIs as planned work before the plan gate. At approval the rows
move into that table, and the PBI files are written.

7. **Answering from the board (PBI-031, PBI-032, then PBI-033).** First the write surface, its record and
   the answer rules (PBI-031), then the page controls (PBI-032). The answer audit (PBI-033) follows. It is
   not a gate, since a board answer is trusted as the owner's (row 32), so it waits behind PBI-030, which
   edits the same exporter files, rather than holding up answering.
8. **Approvals through answers (PBI-034, PBI-035).** Two further answer types, each bound to what it
   approves (PBI-034), then their controls on the Spec and Backlog tabs (PBI-035). The conditions half
   needs PBI-010's derived `conditions` state.
9. **Retiring the hand-kept state (PBI-036).** Documentation and the owner's own switch
   (`workItemStatus: "derived"`, PBI-010 spec §5). Promoted only when trigger T3 is met.
10. **Retiring the v1 artifact (PBI-037, then PBI-038).** Freeze the artifact and stop the refresher now
    (PBI-037, a same-day check T4), then remove the dead push path once PBI-007 is Done and 7 days have
    passed without the refresher (PBI-038, trigger T4.4).

**Metadata proposed for every revision-6 PBI:**
- `pr_required: true`.
- `merge_allowed_by_agent: true`, under the owner's standing merge authorisation of 2026-09-12 (`CLAUDE.md` "Merge authority"), except PBI-031, PBI-034 and PBI-038, which are `false`. PBI-031 opens the first write surface; PBI-034 decides what a board approval binds to (rows 34, 50); PBI-038 deletes a module. The owner merges all three. PBI-033 is an audit that decides nothing, so it follows the standing authorisation.
- `change_class: standard` for all eight.
- **How a trigger is enforced.** `depends_on` cannot express a date or an owner's judgement. PBI-036 and PBI-038 therefore carry their trigger in the PBI file as a promotion precondition. Each stays under Proposed until its evidence file exists and records the owner's decision verbatim. Promotion to Ready is already the owner's act (BOARD, Ready notes). **PBI-037 is the exception:** the owner's approval of this revision is its promotion, since the approval question says approving freezes the published page today; its T4 evidence file is its own first act (AC-V1), and T4's same-day check must pass before any store write.
- **PBI-031's promotion precondition.** A `chore-work` change adding `local/server*` and `local/answers*` to `security_paths` in `backlog-delivery.config` (empty today, line 87) is merged before PBI-031 is promoted, so its own and PBI-034's `pbi-work` resolver sees a security path without anyone remembering a flag (row 49). The page's answer controls are not added: `site/index.html` is one file, so the entry would flag every page PBI.

### Revision 6 (draft): PBI list (proposed)

| ID | Title | Depends on | Conflict group | Conflict risk | Requires spec | Requires ext. review | Trigger |
|----|-------|------------|----------------|---------------|---------------|----------------------|---------|
| PBI-031 | Answers endpoint on the local server: the answer record, a server-owned answers database, `POST /api/answers` with its checks, a nonce content-security policy, `local/answers.py list` and `verify`, and the `CLAUDE.md` answer and transcription rules (FR-95, FR-132, NFR-23) | [PBI-007] | local-app | High | true | true | — |
| PBI-032 | Answer from the board: Accept and Override on the Assumptions tab (local adapter only), answered and transcribed states (FR-131, AC-87) | [PBI-031] | page | High | true | false | — |
| PBI-033 | Answer audit: transcript tool calls that could have sent an answer, and the answers they may have made marked on the Assumptions tab | [PBI-032, PBI-030, PBI-034] | page | High | true | false | — |
| PBI-034 | Approvals as answers: `planApproval` bound to git's blob id of the committed spec, and `conditionsAccepted` bound to one review run, with server checks and `verify` support (S-31) | [PBI-031] | local-app | Medium | true | true | — |
| PBI-035 | Approve from the board: plan approval on the Spec tab, conditions acceptance on the Backlog, and the accepted-conditions overlay | [PBI-032, PBI-034, PBI-010] | page | High | false | false | — |
| PBI-036 | Retire the hand-kept work-item state for a project: evidence, the owner's switch, and the close-out procedure without `state` (S-39) | [PBI-010] | docs | Low | false | true | T3 |
| PBI-037 | Retire the v1 artifact and its refresher: final store export, final status message, loop stopped, procedures marked retired (S-40) | [] | docs | Low | false | true | T4 (same day) |
| PBI-038 | Remove the v1 push path: delete `refresh.py` and its tests, move the three other test modules off it, remove the store adapter, retire the refresher's docs | [PBI-037, PBI-007] | page | High | false | true | T4.4 |

**Dependency graph (rev 6).** PBI-007 → PBI-031 → {PBI-032, PBI-034}. {PBI-032, PBI-030, PBI-034} → PBI-033. {PBI-032, PBI-034, PBI-010} → PBI-035. PBI-010 → PBI-036 (+T3). PBI-037 (+T4, same day). {PBI-037, PBI-007} → PBI-038 (+T4.4). PBI-031 also carries the `security_paths` precondition above.

### Revision 6 (draft): trigger criteria

A trigger is **checkable**: each part is a count, a date or a quoted statement, and all of it is written
into an evidence file before the PBI is promoted. The orchestrator gathers the evidence; **the owner
alone judges** whether it is met. No agent promotes a triggered PBI, flips `workItemStatus`, or stops the
refresher on its own reading of the evidence.

**T3: retiring the hand-kept state for one project** (PBI-036; evidence in
`docs/backlog/evidence/<date>-t3-<projectId>.md`). All of these hold:
- **T3.1** PBI-010 is under Done on the BOARD, and at least 14 days have passed since its merge commit on `main`, during which that project's Backlog tab showed the shadow panel. The earliest possible date is PBI-010's merge date plus 14 days; PBI-010 is still In Progress.
- **T3.2** In that time, at least 5 of the project's work items were named by a run (the shadow panel's "Named by a run" figure). A project with no build activity cannot meet T3: no evidence means no trust.
- **T3.3** On the day judged, the shadow panel shows 0 "Runs ahead" and 0 "Hand-kept ahead" items. Two exceptions are allowed: an item whose only difference is a GO-WITH-CONDITIONS that the owner has accepted (PBI-035), and an item the owner lists by id as an accepted exception in the evidence file.
- **T3.4** PBI-010 spec row Q-3 (GO-WITH-CONDITIONS stays `conditions`) is settled by the owner (`docs/backlog/specs/pbi-010-derived-status.md:1111`).
- **T3.5** The owner's decision, "retire the hand-kept state for <projectId>", is quoted verbatim from chat. No answer type carries this decision (row 33).

**T4: freezing the v1 artifact and stopping the refresher** (PBI-037; evidence in
`docs/backlog/evidence/<date>-t4-retire-artifact.md`). A same-day check, not a wait: the owner answered
"retire it now" (row 37), which drops the earlier 30 days of evidence. All of these hold on the day:
- **T4.1** PBI-007 is merged, and both tasks are installed and serving: AC-68's demonstration of 2026-09-19 (`docs/backlog/pbi/PBI-007-logon-start.md`, Evidence) and that day's committed-pass lines in `out/local/logs/collector.log` are quoted. PBI-007 need not be Done: its log-on demonstration (AC-65) gates PBI-038, not this.
- **T4.2** No feature the owner uses exists only on the artifact: the page suite's adapter deep-equal passes on `main`.
- **T4.3** The owner's acceptance of the loss is quoted verbatim: row 37's answer, "retire it now", given to a question that stated the loss. It is also PBI-037's external-review go-ahead.

**T4.4: removing the push path** (PBI-038; recorded in the same T4 evidence file). All of these hold:
- PBI-007 is under Done: the owner has accepted its log-on demonstration (AC-65), so the board is proven to come back after a reboot with no Claude session.
- At least 7 days have passed since PBI-037 closed (the repository's `revert_window_days = 7`, `backlog-delivery.config:62`), and in that time no session's transcript runs `exporters/refresh.py --commit` or writes the artifact's store (a `write_db` call); a dry run of `refresh.py` does not count. Seven days is the default; the owner may shorten it, and the evidence file quotes them if so.
- The owner gives PBI-038 its external-review go-ahead.

The earliest date is 2026-09-26, or PBI-007's Done date, or PBI-037's close date plus 7 days, whichever is latest.

**Linked sessions and PBI-030.** T3.2 is counted over linked sessions; T4.4 over every session, since any session could write the store. PBI-030 (intake,
`docs/backlog/pbi/PBI-030-auto-link-sessions.md`) links sessions by the files they edit as well as by the
config list. Once it has merged, the triggers count auto-linked sessions too, and each evidence file says
whether PBI-030 was live over its window. Auto-linking only widens the set.

**What the owner loses at T4, accepted on 2026-09-19 (row 37).**
- **Viewing the board away from the PC.** This covers the phone, another computer and claude.ai on the web. The local app listens on 127.0.0.1 only (PRD NFR-19), and the artifact cannot read the local server (PRD C-2, C-18).
- **A board held off this machine.** The local database is rebuilt from transcripts. Answers survive only through their transcriptions into the repo.
- **What replaces it: nothing in this plan.** The frozen artifact stays readable, with its last data, a "stale" header (PBI-008) and a final status message. Wider access would come back only if the Unraid deployment (formerly PBI-016: LAN only, no login) or Azure hosting (PRD S-27) is revived. Both stay in Future iterations.
- **What the owner gains.** The refresher's Claude usage stops (up to 144 writes a day, row 1), and there is one data path instead of two (ADR-0001, Consequences).

**Why answering does not depend on the artifact.** Answers live on the local app (row 25), so PBI-037 and
PBI-038 remove no answer path. Had answers been built on the artifact's store, T4 would have deleted them.

### Revision 6 (draft): acceptance criteria

These criteria are this spec's own until the PRD is re-baselined (row 47). Each PBI file copies them at
decomposition, and any PBI with `requires_spec: true` refines them in its own spec.

**PBI-031, answers endpoint** (G-8; rows 25–32, 41, 46, 49):
- **AC-A1** `local/records.py` shall define the answer record in a registry of its own, `records.ANSWER_TABLES`, beside `records.TABLES`, so the record shapes stay defined once (ADR-0001) and the board database gains no answers table. Every answer carries `id`, `type`, `projectId`, `note` (at most 2,000 characters, may be empty), `at`, `writer` (always `page`) and `surface` (always `local`), plus an optional `supersedes` (an earlier answer id). This PBI defines one type, **`assumption`**: `specPath`, `specRevision`, `row` (the ledger row number), `questionSha` (the SHA-256 of the row's question text as exported), `choice` (`accept` or `override`) and `answer` (at most 2,000 characters). PBI-034 adds two more.

  `records.shapes.json` shall be regenerated. `records.store_path('answer', id)` now succeeds (`answers/<id>`), so `local/tests/test_records.py:187` and `:550`, which assert the kind is unknown, are rewritten to test the new registry.
- **AC-A2** Answers shall be stored in their own SQLite file at `local.answersPath` (default `out/local/answers.db`), whose DDL `local/schema.py` builds from `records.ANSWER_TABLES` with its own function. `schema.DDL` stays the board database's, so `local/tests/test_schema.py:88-93` (`test_no_answers_table`) stays true unchanged. Only `local/server.py` creates or writes the answers file, and the network-path guard (FR-96) applies to it. The server keeps opening the board database read-only (`query_only=1`); the collector never opens the answers file (an inspection test in the style of `test_deploy_inspection.py`); `local/answers.py` opens it read-only. Answers are never pruned.
- **AC-A3** `POST /api/answers` shall store one answer only when every check passes:
  - Host is on the allow-list, and Origin is one of the two local origins (`local/server.py:410`), both as today;
  - `Content-Type` is `application/json`, and `Content-Length` is present and at most 16 KiB; a chunked body is refused before anything is read;
  - an `X-Dispatch-Token` header equals, compared in constant time, the token the server generated at start and injected into `__DISPATCH_LOCAL__`. A stale token's refusal line says to reload the page;
  - the body conforms to AC-A1;
  - `projectId` is the id of an entry in `projects[]` of `board.config.json`, and `specPath` equals that entry's `docs.spec`. The server takes paths from the config only, never from the body (row 31);
  - for `assumption`: the row exists in that project's current assumptions tab record, is awaiting the owner or ASSUMED, and its question hash matches.

  The server sets `id`, `at`, `writer` and `surface`, and refuses a body that supplies any of them. Success returns 201 with the record. Every failure returns the existing one-line 4xx shape, stores nothing and echoes nothing.
- **AC-A4** Answers shall be append-only. The endpoint accepts no PUT, PATCH or DELETE, and a changed answer is a new record with `supersedes`.
- **AC-A5** The snapshot and the event stream shall carry answers under `answers/<id>`, and the server shall signal the event hub itself when it stores one, since `data_version` polling watches only the board database. An `answers` table found in the *board* database shall stay invisible. With no stored answers the snapshot holds no `answers` key, so `local/tests/test_server.py:302-322` stays true; that test and `local/tests/test_server_live.py:58-72` are re-keyed to "no record read from the board database's `answers` table", since a stored answer or an audit entry's detail may contain the word.
- **AC-A6** `local/answers.py` shall have two commands:
  - `list [--project ID]` prints the stored answers;
  - `verify <spec path>` checks every `answer:<id>` citation in the spec: the id exists, and its type, project, spec path, row, choice and answer text match the ledger row or Plan-gate line that cites it (plan approvals: AC-P2). It exits non-zero naming each mismatch. It checks that a transcription is faithful, not who gave the answer.
- **AC-A7** `server.log` shall carry one line for each accepted or refused answer: the id or the reason, and the row, never the text.
- **AC-A8** The PBI's spec gate shall include a threat model of the endpoint (the `security-agents:threat-modeling` skill), covering a malicious web page (cross-site requests and DNS rebinding), a script injected into the page, and a stale or leaked token. An agent on this PC answering as the owner, by any route, is outside its scope: the owner has decided such an answer counts as theirs (row 32). Its code review shall include `review-agents:api-reviewer`.
- **AC-A9** The served page shall run under a content-security policy whose `script-src` is a per-start nonce, without `'unsafe-inline'`. `_wrap_page` adds the nonce to the marker script and to the page's one `<script>` (`local/server.py:40-42`, `:566-581`). A test shall assert that the header's `script-src` carries a `'nonce-…'` source and no `'unsafe-inline'`, that the nonce differs between two server starts, and that every `<script>` in the served page carries it.
- **AC-A10** `CLAUDE.md` "Answers are the owner's" shall say:
  - an answer given on the board counts as the owner's, whoever gave it (the owner, 2026-09-19: "Just procees as if it were me"; row 32);
  - agents still do not answer for the owner: no agent POSTs to `/api/answers`, drives the answer controls, opens the answers file, or cites an answer id it has not read with `local/answers.py`;
  - build, test, smoke-test and verify work on the answer controls runs a throwaway server on another port with a temporary `local.answersPath`, never port 8765 or the real `answers.db`;
  - the transcription procedure: cite `answer:<id>`, then run `verify` and quote its output.

**PBI-033, answer audit** (G-8; rows 26, 32):
- **AC-G1** The shared derivation shall record, as `answerSuspects` `[{at, tool, detail}]` on the session document (detail redacted and cut to 300 characters), every tool call in a main or subagent transcript that could have **sent** an answer:
  - a Bash or PowerShell call whose input names `/api/answers` together with a sending command (`curl`, `wget`, `Invoke-WebRequest`, `Invoke-RestMethod`, `urllib`, `requests`, `fetch`);
  - a WebFetch call naming `/api/answers`;
  - a browser-automation call (`mcp__*Browser*__*`, `mcp__claude-in-chrome__*`, the preview tools) whose input names the local server's origin, or that acts on a tab whose last-seen URL is on that origin (so a board tab the owner already has open counts), and a `javascript_*` call naming `/api/answers`;
  - an Artifact or ArtifactData write naming an `answers/` path.

  Calls that only **mention** the endpoint (`grep`, `rg`, `Select-String`, `git log -S`, Read, Edit, Write) are not recorded. The exporters and the collector shall produce identical `answerSuspects` (the equivalence fixture is extended).
- **AC-G2** The PBI's spec shall confirm the tool-call shapes against real transcripts before the detector is built, as PBI-009 did, including browser calls on `127.0.0.1:8765` (session `7e0c4f3c`) and the revision-6 planning and review transcripts, and measure how many harmless calls the rule marks.
- **AC-G3** On the local adapter, the Assumptions tab shall mark each answer given within 5 minutes after a suspect call as "Possibly given by an agent: <session>, <tool>", in the `--changes` tone, and list every such pairing in an "Answer audit" panel. The marks are a record for the owner to read: nobody clears them, and they change neither whether an answer counts nor how it is transcribed. They last as long as their session document: an unlinked session's is pruned after 7 days (FR-185), and its marks go with it. The store adapter shows no audit, since it holds no answers.
- **AC-G4** The rendering shall meet NFR-22 and render audit data through `esc()` only. `tests/page.test.mjs` shall cover a marked answer, an unmarked one, the panel, and the store adapter's absence of both.
- **AC-G5** `CLAUDE.md` shall state what the audit cannot see: an agent that avoids the recorded shapes (a URL built at run time, a script file written first, editing a transcript or the board database, a session under `sessions.exclude`, a stopped collector), a script injected into the page, and a browser tab the tool call never identifies. Its marks show what a non-evading agent did, never that nothing happened.

**PBI-032, answering on the page** (G-8; rows 30, 40):
- **AC-B1** On the Assumptions tab, each row awaiting the owner shall offer *Accept* (showing the row's chosen default) and *Override* (answer and note fields). They appear only when the local adapter is active and its marker carries a token. The store adapter shows no controls, only a line saying answers are given on the board on the PC, and has no write method (FR-64 holds on the artifact).
- **AC-B2** A submission shall send one POST, disable the row's controls while it is pending, show the server's refusal line on failure, and never retry by itself.
- **AC-B3** An answered row shall show "Answered <time>: Accept/Override" and "awaiting transcription" until the spec ledger cites that answer id. It shall leave the "Awaiting your decision" counts once answered.
- **AC-B4** The PBI's UI smoke test shall run against a throwaway server on another port with a temporary `local.answersPath` (AC-A10), never the owner's server, and its evidence shall name the port and path used.
- **AC-B5** The rendering shall meet NFR-22, and `tests/page.test.mjs` shall cover the controls on the local adapter, their absence on the store adapter, the token header and each failure path. It shall also assert that the answer controls render no data through `md()`, only through `esc()`.

**PBI-034, approvals as answers** (G-9; rows 33, 34, 50):
- **AC-P1** Two more answer types, with the common fields of AC-A1 and the checks of AC-A3:
  - **`planApproval`** carries `specPath`, `specRevision`, `decision` (`approve` or `changes`) and `specBlob` (40 lowercase hex characters, `^[0-9a-f]{40}$` in the record shape), taken from the spec tab record the page rendered (AC-Q1). `specBlob` is **git's own blob id of the committed spec**, `git rev-parse HEAD:<specPath>`, and is offered only while the spec is committed: `git ls-files --error-unmatch -- <specPath>` succeeds (tracked, exact case) and `git --no-optional-locks status --porcelain -- <specPath>` prints nothing. The server resolves the spec's path from `board.config.json` (the project's `repoPath` plus `docs.spec`), applies the network-path guard to it, and runs the same commands in that repository, plus a third read, `git cat-file -p <blob>`, for the committed text's `revision:` and `status:`. Every git call, on every side, has a timeout and `no_window_flags()` (as `local/tabs.py:50-53`) and checks its exit code: a non-zero exit or a timeout leaves `specBlob` absent and `specCommitted` false, and the server refuses. The server refuses the POST when HEAD's blob differs from the posted `specBlob`, when the file is untracked or not clean, when the committed text's `revision:` differs from the posted revision, or when its `status:` is not `draft`. `--no-optional-locks` keeps `status` from writing `.git/index` in a repository the board only reads. Every side takes the id from git, which hashes the committed content after its line-ending conversion, so a CRLF working copy of an LF-committed spec (`core.autocrlf = true`) gives the same id on the page, on the server and in `verify`. Tests shall cover that case, a wrong-case `docs.spec` over a dirty file, an untracked spec and an ignored spec: none offers *Approve*, and the server refuses all three. The server's and `local/answers.py`'s git launches are added to the reviewed list in `local/tests/test_deploy_inspection.py`.
  - **`conditionsAccepted`** carries `pbiId` and `runId`. The run must exist in the snapshot as a code-reviewer run of the posted project with a GO-WITH-CONDITIONS verdict that names the PBI.
- **AC-P2** For each cited `planApproval`, `verify` shall check, in the project's repository with read-only git commands:
  1. the approved text was committed at `specPath`: `git log --find-object=<specBlob> -- <specPath>` lists a commit;
  2. that text's `revision:` (from `git show <specBlob>`) equals `specRevision`;
  3. at the **transcription commit** (the earliest commit that `git log --reverse -S 'answer:<id>' --format=%H -- <specPath>` lists), `git show <commit>:<specPath>` equals `git show <specBlob>` once both are normalised. Normalising removes only the frontmatter lines `status:` and `approved_revision:` and the `## Plan-gate record` section. Both texts come from git's objects, so their line endings agree. An uncommitted transcription fails with "commit the transcription first".

  Later commits are decomposition and do not fail `verify`; it prints, as information, how many lines outside the Plan-gate record changed since the transcription commit. For each cited `conditionsAccepted`, `verify` confirms that the run exists.
- **AC-P3** `CLAUDE.md` shall say how a board approval reaches the Plan-gate record:
  - **Pickup.** The planner ends its gate turn with the gate pending and does not wait on chat. At the start of each orchestrator session, and on any loop that session runs, `python local/answers.py list --project <id>` is run; after PBI-037 there is no standing loop, so the session start is the usual pickup. Only the latest `planApproval` for the spec's current `specBlob` that no later answer supersedes (AC-A4) counts. With `approve` it is transcribed; with `changes` the spec returns to the planner with the owner's note. The transcribed answer id and note are the runbook's "exact human approval message".
  - **What an approval accepts.** A `planApproval` with `approve` accepts the chosen default of every row still ASSUMED in the approved text that has no answer of its own. The transcription lists those rows as confirmed by that approval.
  - **Commits, in order.** Any assumption answers are transcribed into the ledger before the approved text is committed (the owner then approves text that holds them) or after the transcription commit, never with it. The transcription commit holds only the answer id, the owner's note, `status:` and `approved_revision:`. `verify`'s output goes in the next commit, which touches only the Plan-gate record. The status banner, a revision-history line, G-6's rewording and moving rows into `### PBI list (proposed)` come after that.
  - **Squash merges.** The commit holding the approved text is in the history of the branch the transcription lands on before the transcription is committed, and the two are never squashed together: the draft's PR merges first, or the transcription is its own commit or PR. The transcription also reaches the branch `verify` runs on without being squashed together with any later edit: **recording the approval is its own PR**, holding the transcription commit and `verify`'s output commit (squashing those two is safe, since the output sits in the normalised-away Plan-gate record), and the status banner, the revision-history line, G-6's rewording, the row move and the decomposition follow in a later PR. Tests squash a draft with its transcription, and a transcription with a banner edit, and show `verify` naming the cause each time. The binding reads `HEAD` of `repoPath`, whatever branch that checkout is on (for platform-catalogue, `build/logic-core`), so `verify` runs on that branch.
  - **Honouring.** A `planApproval` or `conditionsAccepted` is honoured once transcribed with a clean `verify`. A board plan approval passes the plan gate by itself (row 34); there is no chat step.
  - **Revision 6 itself** is approved in chat, since the board path does not exist until PBI-034 and PBI-035 ship.

**PBI-035, approving on the page** (G-9; rows 34, 35, 50):
- **AC-Q1** When a project's spec `status:` is `draft` and its spec tab record says `specCommitted: true`, the Spec tab shall offer *Approve* and *Request changes*, with a note, on the local adapter only. Beside them it shows the spec's path, revision and short blob id, and says the approval is of the committed text at that id (`git show <id>` prints it). The spec tab record gains `status` (the frontmatter), `specBlob` (`git rev-parse HEAD:<specPath>`) and `specCommitted` (AC-P1's two checks both pass); the git values are read beside the git tab's commands in `exporters/export_board.py` and `local/tabs.py`, with AC-P1's exit-code rule. Beside *Approve* the tab lists every row still ASSUMED in the spec, High-impact ones first, since approving accepts their defaults (AC-P3). While a spec is draft and committed, the Overview's "Needs attention" shows "<spec> revision <n> awaiting your approval". The page posts the `specBlob` it rendered, and after a submission shows the answer id's first 8 characters.
- **AC-Q2** A Backlog item whose derived state is `conditions` shall offer *Accept conditions*. Once accepted, it shows "Conditions accepted by you <time>". Its "<id> review conditions" item leaves "Needs attention", and in the shadow comparison it counts as done with accepted conditions. This is a page overlay: the derived state itself is unchanged.
- **AC-Q3** The same design rules, page-test coverage and smoke-test rule as AC-B4 and AC-B5 shall apply.

**PBI-036, retiring the hand-kept state** (G-10; row 36):
- **AC-H1** The T3 evidence file shall exist, and record T3.1–T3.5, before any other change.
- **AC-H2** For that project only, `workItemStatus` shall be `"derived"`, set by the owner alone (PBI-010 spec §5.2 and §5.3, `docs/backlog/specs/pbi-010-derived-status.md:486-507`: "the owner only"; "The mechanism has no agent path"). The PBI's diff leaves `board.config.json` untouched; the evidence file records the owner's edit and its commit.
- **AC-H3** `CLAUDE.md` and `README.md` shall say that close-outs no longer edit `buildState.<id>.state` for a project in derived mode. `review`, `open` and `commit` stay overrides (FR-176), and `projects/*.json` is never deleted (C-20).
- **AC-H4** After the next collector pass, the project's Backlog tab shall show derived mode's line of text (PBI-010 spec §5.2), by demonstration.

**PBI-037, freezing the artifact and stopping the refresher** (G-11; rows 37, 38):
- **AC-V1** The T4 evidence file shall exist, and record T4.1–T4.3, before any store write or loop change. PBI-037 is promoted at this revision's approval.
- **AC-V2** Before the final write, every `meta/*` and `status/*` document in the store shall be exported to `snapshot/` and committed.
- **AC-V3** The last refresher push shall be taken when no run in the export is `running`, linked or not, and the orchestrator shall dispatch no agent between that push and the final write, so no run is frozen as `running`. Then one final write, approved by the owner, shall set the `meta/status` message to "Retired <date>: the board now runs on this PC at http://127.0.0.1:8765", and `live: false` on `meta/status` and every `status/*` document, so the frozen page shows no live activity.
- **AC-V4** The refresher loop shall be stopped. `CLAUDE.md` and `README.md` shall mark the Refresh and publish procedures retired, keeping their text until PBI-038, and state the revert: until PBI-038 merges, restarting `/loop 10m Refresh the dispatch board: …` restores the artifact. `CLAUDE.md` shall also say that no PBI republishes the artifact from now on, including PBI-010, which is in flight.
- **AC-V5** The artifact shall be neither deleted nor republished, and its capabilities shall be unchanged.
- **AC-V6** From the freeze on, nothing shall republish the artifact, run the refresher, or write its store: no `write_db` call and no hand edit of `meta/status` or `status/*`. This includes the paused platform-catalogue build's hand-written `title`, `message` and `metrics` in `meta/status` (`CLAUDE.md`, "Refresh procedure"); a stage message stops at the freeze, and the build's state is read from its data file on the local board. The only exception is the documented revert (AC-V4), which the owner asks for. `CLAUDE.md` and `README.md` state this rule. Any such write restarts T4.4's window.
- **AC-V7** PBI-037's close-out includes an orchestrator step outside the repository: the orchestrator's session memory note for the dispatch board is updated to say the artifact is frozen, the refresher loop is not restarted when the frozen page shows "stale", nothing is published to the artifact, and the board lives at http://127.0.0.1:8765. That note is updated separately; it is not a file this PBI changes.

**PBI-038, removing the push path** (G-11; rows 38, 43):
- **AC-X1** T4.4 shall be recorded before any change.
- **AC-X2** `exporters/refresh.py` and `tests/test_refresh.py` shall be deleted. FR-133 and AC-86 retire with them, since nothing writes the store any more. The exporter modules stay, because `local/tabs.py` and the collector import them.
- **AC-X3** The store adapter shall be removed from `site/index.html`. A page without the local marker shows the offline board, with a line naming the local app.
- **AC-X4** `CLAUDE.md`, `README.md` and the PRD's C-1 and FR-99 notes shall no longer describe a live store path.
- **AC-X5** This is tier 4 (module deletion): the canonical run of all three suites.
- **AC-X6** No module shall import `refresh` afterwards. Its three other importers are moved off it, not deleted:
  - `local/tests/test_conformance.py` (`:19`, `refresh.plan()` at `:253`) keeps driving the real exporters and checks the status documents through the collector's status records instead of `refresh.plan`, so AC-69's conformance proof still covers every document kind;
  - `local/tests/test_tabs_equivalence.py` (`:18`; `:67-72`, `:163-175`) re-pins the status rule of `local/tabs.py` to fixed expected documents, captured from `refresh.plan` before the deletion and committed as fixtures, rather than deleting the comparison;
  - `tests/test_export_sessions.py` (`:1282`) checks the collections from the exporters' `out/` folders directly.

### Revision 6 (draft): allowed and blocked areas

- **PBI-031**: allowed `local/server*`, `local/records*` (with `local/records.shapes.json`), `local/schema*` (the answers database's DDL function only; `schema.DDL` unchanged), `local/answers*`, `local/tests/**`, `board.config.json` and `exporters/board_config.py` (the `local.answersPath` key only), `CLAUDE.md`, `README.md`. Blocked: `site/**`, `local/collector*`, `local/db*`, and every other `exporters/**` file. It also touches `config`, `exporters` and `docs`. It is a **security path**, a new write surface, registered in `security_paths` before promotion; tier 4 (record shapes).
- **PBI-032**: allowed `site/**`, `tests/page.test.mjs`. Blocked: `exporters/**`, `local/**`. Its smoke test runs against a throwaway server (AC-B4).
- **PBI-033**: allowed `exporters/derive.py`, `exporters/export_sessions.py`, `tests/test_*.py`, `local/records*` (with `local/records.shapes.json`; the session's `answerSuspects`), `local/collector*` (only if carrying the field needs it), `local/tests/**`, `site/**`, `tests/page.test.mjs`, `CLAUDE.md`. Blocked: `local/server*`, `local/answers*`, `local/schema*`. It also touches `exporters`, `local-app` and `docs`. Tier 4 (record shapes).
- **PBI-034**: allowed `local/server*`, `local/records*`, `local/answers*`, `local/tests/**` (including the reviewed git launches in `test_deploy_inspection.py`), `CLAUDE.md`. Blocked: `site/**`, `exporters/**`, `local/collector*`. It also touches `docs`. A security path through `security_paths`.
- **PBI-035**: allowed `site/**`, `tests/page.test.mjs`, `exporters/derive.py` and `exporters/export_board.py` (the spec tab's `status`, `specBlob` and `specCommitted`), `local/tabs.py` (the same two git values), `tests/test_*.py`, `local/records*` (the tab shape), `local/tests/**`. Blocked: `local/server*`, `local/answers*`. It also touches `exporters` and `local-app`.
- **PBI-036**: allowed `docs/backlog/evidence/**`, `CLAUDE.md`, `README.md`. Blocked: `board.config.json` (the owner sets `workItemStatus` themselves, AC-H2), `projects/**` (never deleted, never rewritten by this PBI), `exporters/**`, `site/**`, `local/**`.
- **PBI-037**: allowed `docs/backlog/evidence/**`, `snapshot/**`, `CLAUDE.md`, `README.md`, and one owner-approved store write. Blocked: `site/**`, `exporters/**`, `local/**`, `board.config.json`. There is no artifact publish and no deletion.
- **PBI-038**: allowed `exporters/refresh.py` and `tests/test_refresh.py` (deletion only), `local/tests/test_conformance.py`, `local/tests/test_tabs_equivalence.py` and their fixtures under `local/tests/`, `tests/test_export_sessions.py` (AC-X6), `site/**`, `tests/page.test.mjs`, `CLAUDE.md`, `README.md`, `docs/prd/**` (the C-1 and FR-99 notes). Blocked: every other `local/**` path and every other `exporters/**` file. It also touches `exporters`, `local-app` and `docs`.

### Revision 6 (draft): sequencing

- **At this revision's approval:** PBI-037 (`docs`, Low) is promoted and can start at once, beside PBI-010, since it collides with no code. It needs only T4's same-day check, not PBI-007 being Done.
- **After PBI-007 is Done:** PBI-031 is the only revision-6 PBI that can start, once the `security_paths` chore has merged. PBI-007 is still In Progress, awaiting the owner's log-on demonstration (`docs/backlog/BOARD.md`, In Progress). PBI-031 holds `local-app` at High, so no other local-app PBI runs beside it; PBI-028 is Done (PR #31, `f7b21f9`).
- **After PBI-031:** PBI-032 (`page`) and PBI-034 (`local-app`) can run in parallel; they share no file. PBI-032 waits for the `page` slot: PBI-010 holds it now (In Progress since 2026-09-19, HEAD `5e4f97c`), and PBI-020 and PBI-039 are Proposed in the same group. PBI-012 has merged (PR #34, `312e2f5`).
- **After PBI-032, PBI-030 and PBI-034:** PBI-033, the answer audit. It is not a gate (row 32), so it waits behind PBI-030 rather than rebasing a tier-4 change onto it, and behind PBI-034, since both change `local/records*` and regenerate `local/records.shapes.json` and their groups differ.
- **After PBI-032, PBI-034 and PBI-010:** PBI-035.
- **Triggered, any time the trigger is met:** PBI-036 (T3, per project, no earlier than PBI-010's merge date plus 14 days) and PBI-038 (T4.4: PBI-007 Done and 7 days after PBI-037 closed, no earlier than 2026-09-26). PBI-036 is `docs` Low and collides with nothing in code; PBI-038 is `page` High.
- **PBI-030 (intake, not planned here).** PBI-030 links sessions to a project from the files they edit (`docs/backlog/pbi/PBI-030-auto-link-sessions.md`; `exporters`, Medium; builds after PBI-010 merges). It edits `exporters/derive.py`, `exporters/export_sessions.py`, `exporters/board_config.py`, `local/collector.py` and `local/tests/**`. PBI-033 now depends on it, so they never run together. Its overlaps with PBI-031 (`exporters/board_config.py`) and PBI-035 (`exporters/derive.py`) are **accepted by name**: whichever lands second rebases, as PBI-019 and PBI-005 did with the config keys. The triggers count auto-linked sessions once PBI-030 has merged (T4.4).
- **PBI-039 (intake, not planned here).** PBI-039 makes the Backlog tab list every PBI, not only the plan's (`docs/backlog/pbi/PBI-039-backlog-lists-every-pbi.md`; `page`, High). It edits `exporters/derive.py`, `exporters/export_board.py` and `site/index.html`. Being `page` High, it never runs beside PBI-032, PBI-033, PBI-035 or PBI-038; the group serialises them. Its `derive.py` and `export_board.py` changes overlap PBI-035's spec tab fields, so whichever of the two lands second rebases. It reads PBI files, and revision-6 PBI files are written only at approval, so it cannot show these PBIs early; once their rows move into `### PBI list (proposed)` they come from the table (its B-2).
- **Critical path to answering from the board:** PBI-007 → PBI-031 → PBI-032.
- **Owner go-ahead before implementation** (`requires_external_review: true`): PBI-031 (a new write surface), PBI-034 (changes how approvals reach the workflow), PBI-036, PBI-037 and PBI-038 (retirements and a deletion). PBI-037's go-ahead is row 37's answer (T4.3).

---

## Assumptions & open questions

**Rows the human must confirm or correct at the plan gate:** 28, 29, 30, 31, 33, 35, 36, 38, 41, 46, 47, 48, 49, 50 (revision 6, draft; row 50 is high impact, and approving the revision accepts every row still ASSUMED). Rows 1 to 24 were confirmed or corrected by the owner on 2026-09-11 (row 16 with changes to PBI-017) and stand; rows 25, 32, 34 and 37 were answered by the owner on 2026-09-19; rows 26, 27, 39, 40, 42, 43, 44 and 45 are resolved from the code and docs.

| # | Question / ambiguity | Resolution | Status | Source / chosen default | Impact if wrong |
|---|----------------------|-----------|--------|-------------------------|-----------------|
| 1 | Idle refresh cadence and the two token figures (PRD A-5, A-6) | Keep the 10-minute every-tick loop until the local app replaces the refresher. Dispatch keeps `subagent_tokens`, relabelled "reported tokens" in PBI-002, and cost per work item uses effective usage | CONFIRMED | Owner, 2026-09-11 (accepted the defaults) | Low — up to 144 small writes a day until PBI-007 |
| 2 | Is the tab-bar overflow defect (PRD FR-125–FR-128, A-24) still open? | No: the tab bar wraps, so no tab is clipped | RESOLVED | `site/index.html:58` (`.tabs` flex-wrap); commit `2742ca6` message | Low |
| 3 | Snapshot of build data in the public repo (PRD A-8) | The repo is made private on GitHub; `snapshot/` stays | CONFIRMED | Owner, 2026-09-11: "Make the repo private" (done the same day) | Medium — git history before the switch was public |
| 4 | Deleting the store leftovers (PRD A-9, D-11) | A separate owner-run PBI-021, gated by owner approval, with preconditions: the page confirmed project-first, and the six documents exported to `snapshot/` first (AC-S1–AC-S3) | CONFIRMED | Owner, 2026-09-11 (accepted); mechanism tightened by review H-2 | Low — six unused documents stay until then |
| 5 | Adopt the answer write path (PRD A-25, C-17) | Not now. The former PBI-015 moves to Future iterations; answers stay in chat. The guards stay: FR-133 in PBI-001 and the C-16 rule in `CLAUDE.md`. FR-134 (the ingest endpoint rejects answer records) travels with the Unraid idea, deferred to Future iterations on 2026-09-11, since without Unraid there is no ingest endpoint | CONFIRMED | Owner, 2026-09-11: "Not now" | **High** — reversing later needs an ADR and the deferred PBI |
| 6 | Deployment target (PRD A-26) | On-PC first (PBI-007). Unraid (PBI-016) is last and optional, built only when the owner says so. On 2026-09-11 the owner moved it to Future iterations ("Move PBI16 to later") | CONFIRMED | Owner, 2026-09-11 | Medium |
| 7 | Unraid network exposure and authentication (PRD A-27) | Serve the page on the LAN without login, with the Host allow-list extended to the Unraid server's LAN name and address. The shared secret for the collector's uploads is read from an environment variable or a git-ignored file, never from `board.config.json`. There is no answers endpoint | CONFIRMED | Owner, 2026-09-11: "Yes, that's fine"; approved in this wording (revision 4, review L6) | Medium — any LAN device can read the board |
| 8 | Local app technology and switch-over (PRD A-29) | Python stdlib only under `local/`: `sqlite3` (WAL mode), `http.server` (threaded), Server-Sent Events for live push, default port 8765. Record shapes and the schema are in PBI-003. The v1 artifact and refresher keep running until the owner retires them. Recorded as ADR-0001 | CONFIRMED | Owner, 2026-09-11 (accepted); ADR-0001 accepted | Medium |
| 9 | Answer provenance on the local server (PRD A-28) | Not applicable in this plan: no answers endpoint is built (row 5) | RESOLVED | Row 5 | Low |
| 10 | "Waiting on you" detection signals (PRD A-30) | PBI-009's spec confirms the transcript record types against real transcripts before any detector is built | CONFIRMED | Owner, 2026-09-11 (accepted) | Medium |
| 11 | Derivation rules for features 3–7 and 9 (PRD A-31–A-35) | The PRD defaults as written | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 12 | Retention, record keys and plan counts (PRD A-36, A-37, A-39) | The local database keeps the last 7 days plus linked sessions, pruned by age only. Records are keyed by project id plus row or PBI id. The last-refresh record adds one write per tick, and the affected tests are updated | CONFIRMED | Owner, 2026-09-11 (accepted); history of unlinked sessions is lost by design (D-15) | Low |
| 13 | Remedies for open review findings and design deviations (PRD A-11–A-13, A-15, A-16) | The PRD remedies for FR-80–FR-84. Other remedies, from the code-reviewer report of 2026-09-11 on the project-first change (session `9562c312`; not stored in the repo): a `carriedSince` marker shown as a warning; config type checks with exit 2; the refresher's session stays linked to dispatch-board, which is documented. Design fixes: paths and branch names move to the sans face; the brand dot stops using `--human`; the header dot pulses only while an agent runs. FR-85: a time-boxed investigation | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 14 | Scope of D-11 against routine refresh deletes (PRD A-10) | D-11 covers leftovers and deletes outside the refresh procedure; routine deletes continue under the mass-delete guard | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 15 | PBI-010 and hand-kept build state | PBI-010 is `requires_spec`. Derived state is shown beside the hand-kept state during a shadow period, with differences flagged. Hand-kept `review`, `open` and `commit` stay as overrides. `projects/*.json` is never deleted. Retiring the hand-kept state is a later owner decision (Future iterations) | CONFIRMED | Owner, 2026-09-11: "Yes, side by side first" | Medium |
| 16 | Acceptance criteria source | Each PBI's criteria are the PRD's ACs for its requirements (AC-57–AC-93, A-18). PBI-017, PBI-018, PBI-021 and PBI-022 take this spec's criteria (AC-C1–AC-C7, AC-L1–AC-L3, AC-S1–AC-S3, AC-R1–AC-R3). PBI-017's criteria include the owner's changes, and its refined spec is reviewed before code (`requires_spec: true`) | CONFIRMED | Owner, 2026-09-11: "Change PBI-017's criteria", choosing "Include skills too" and "Show what each agent is for"; applied in revision 5 | Medium |
| 17 | Where the backlog-delivery rails go (PRD A-21) | `backlog-delivery.config` in the repo root (hooks off; `worktree_script` unset until a helper exists). BOARD, PBI files and done-log go under `docs/backlog/` at decomposition | RESOLVED | `backlog-delivery.config` | Low |
| 18 | Does only the owner view the board (PRD A-2)? | Yes; redaction beyond first prompts stays out of scope | RESOLVED | Brief decision 12; PRD D-12 | Low |
| 19 | What counts as "the catalogue" for PBI-017 | Every agent and every skill in the agent-catalog marketplace, grouped by plugin (purpose):<br>• agents: 30 in 6 plugins (engineering 3, expert 2, platform 1, review 3, security 9, workflow 12);<br>• skills: 21 in 4 plugins (backlog-delivery 12, governance 7, security 1, workflow 1).<br>Each entry is marked installed or not; workflow-agents is not installed. Entries seen in use but outside the catalogue are listed separately | CONFIRMED | Owner, 2026-09-11 (accepted, then widened: "Include skills too", "Show what each agent is for") | Low |
| 20 | What "coverage" means | Per entry: use count, last use and the projects whose sessions used it, over the sessions the board exports. Summary tiles count agents and skills used in the current view, with the all-sessions figure beside | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 21 | Where the tab sits | A new "Agent catalogue" tab after Dispatch, in every view | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 22 | Where the catalogue's entries are defined, and how their use is recorded | Agents are at `…/agent-catalog/plugins/<plugin>/agents/<name>.md`; skills at `…/plugins/<plugin>/skills/<name>/SKILL.md`; both have `name`/`description` frontmatter. Agent runs record `<plugin>:<name>` as `agentType` in `subagents/*.meta.json` (run docs do not carry it yet; AC-C3 adds it). Skill use is recorded as `Skill` tool calls naming `<plugin>:<name>`, and as `/<plugin>:<skill>` slash commands | RESOLVED | `…/plugins/engineering-agents/agents/code-writer.md`; `…/plugins/backlog-delivery/skills/bd-adopt/SKILL.md`; `Skill` calls `backlog-delivery:pbi-plan` and `backlog-delivery:pbi-review` in session `9562c312` | Low |
| 23 | How future iterations appear on the Backlog (PBI-018) | A separate "Later" group of idea cards, below the PBIs, read from this spec's Future iterations list; never counted as work items (AC-L1–AC-L3) | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 24 | Local server hardening | Host-header allow-list (`localhost`, `127.0.0.1`; extended on Unraid, row 7). An Origin check on every non-GET request. No CORS headers. The network-path guard runs in both the collector and the server. No login on the PC | CONFIRMED | Owner, 2026-09-11: "Yes, harden it"; approved in this wording (revision 4, review L6) | Medium — without these checks, a malicious web page could read the board through DNS rebinding |
| 25 | (rev 6) Where is an answer recorded, and by whom: the artifact's store, the local app, or both? Asked: "Row 25: board answers only work on the board on this PC, with no answering away from it. Accept?" | **The local app only.** The page, when served by the local server, POSTs to `/api/answers`, and the server stores the answer. The store route is rejected: it needs the `user` capability and a `{self}` write rule in place of today's `{path:"", read:"interact", write:"admin"}` (`CLAUDE.md`, "The published page"); Claude writes the store as the owner, so it proves nothing more (C-1, `docs/prd/dispatch-board.md:575`); and item 4 retires it. "Both" doubles the surface for no gain | CONFIRMED | Owner, 2026-09-19, verbatim: "Accept, this PC only (Recommended)" | **High** — the owner cannot answer away from the PC. If remote answering is wanted later, the design moves to the store (a `user` capability and an `answers/{self}` rule), which the artifact's retirement rules out |
| 26 | (rev 6) Can either surface tell the owner from an agent acting as the owner? | **No.** On the store, Claude writes with the owner's identity (C-1, `docs/prd/dispatch-board.md:575`), and a `{self}` rule binds only the viewer id, which Claude shares (Artifact runtime contract 0.2.45, `db.d.ts`, "ACCESS RULES"). On the local server, the Host and Origin gate checks header values that any local process can send (`local/server.py:382-414`), and a token in the served page can be read with a GET. An agent can also drive a browser on the page, edit the board database or stop the collector (round 5, PG6-r5-1 to PG6-r5-3). So no login-free design can tell them apart; row 32 records the owner's decision on how a board answer is trusted | RESOLVED | `docs/prd/dispatch-board.md:575`; `local/server.py:382-414`; `db.d.ts` (contract 0.2.45); `docs/backlog/reviews/dispatch-board/plan-gate-review-r5.md` | **High** — frames rows 32 and 34 |
| 27 | (rev 6) Does an answer record shape exist today, and what must change to add one? | No. `records.TABLES` has no answer kind (`local/records.py:130-138`), and `local/schema.py:24-27` builds the board database's DDL from `records.TABLES`, so adding the kind there would create an answers table in the board database and fail `local/tests/test_schema.py:88-93`. The answer record therefore goes in its own registry, `records.ANSWER_TABLES`, with the answers database's DDL built from it by its own function in `local/schema.py` (AC-A1, AC-A2). Tests that change: `local/tests/test_records.py:187` and `:550` (the kind becomes known; `store_path('answer', …)` succeeds), and `local/tests/test_server.py:302-322` and `local/tests/test_server_live.py:58-72` (re-keyed from the substring "answers", AC-A5). Tests that stay true unchanged: `local/tests/test_schema.py:88-93`, `local/tests/test_collector.py:35-41` | RESOLVED | Files cited | Low |
| 28 | (rev 6) The server is a reader and the collector the board database's only writer (`local/server.py:1-4`, `:83-92`; `CLAUDE.md`, "The local app on this PC"). Where do answers go? | A separate SQLite file, `local.answersPath` (default `out/local/answers.db`), created and written only by the server, with its shape in `records.ANSWER_TABLES` (row 27). The board database stays read-only in the server. The collector never opens the answers file | ASSUMED | Default: a separate file | Medium — putting answers in the board database would make two writers of one file, and bring answers into reach of the collector's pruning and mass-delete guard |
| 29 | (rev 6) How does an answer reach the repo's spec ledger? | Nothing writes repo files today. The collector writes SQLite and logs; the refresher writes `out/` and the store (`CLAUDE.md`, "Refresh procedure" and "The local app on this PC"). So no process writes an answer into a spec. The planner or orchestrator transcribes it, into the ledger row or the Plan-gate record, citing `answer:<id>`, and `local/answers.py verify` checks the citation (AC-A6). Until then the page shows the row as "awaiting transcription" (AC-B3) | ASSUMED | Default: transcription by hand, plus `verify` | Medium — automatic write-back would give a long-lived process write access to the project repos, including platform-catalogue, which is read, never written |
| 30 | (rev 6) Whose identity does a local answer carry (FR-132 "the writer's identity"; C-16 "the viewer's identity")? | `writer: "page"` and `surface: "local"`. The server alone sets them. There is no login on the PC (row 24), so the writer is whoever uses the browser at the PC: the owner, since only the owner uses the board (row 18). NFR-23 holds by construction: only the POST handler builds an answer. That meets NFR-23 to the letter but proves nothing about provenance, since a forged answer carries `writer: "page"` too; provenance rests on row 32 | ASSUMED | Default: a constant writer, no login | Medium — if a per-person identity is required, it needs a login, which rows 7 and 24 chose against |
| 31 | (rev 6) How is the write endpoint hardened against cross-site requests? | Today's gate stays: the Host allow-list, an exact Origin match on every non-GET request, no CORS headers, and the 127.0.0.1 binding (`local/server.py:382-426`; FR-177 to FR-179). Added: a JSON content type (a cross-origin form cannot send one without a preflight, which fails with no CORS headers), a per-start token in `__DISPATCH_LOCAL__` sent as `X-Dispatch-Token` and compared in constant time, a required `Content-Length` of at most 16 KiB, a project and spec path taken from `board.config.json` and never from the body (so the server reads no file a caller names), validation against the current tab record, append-only storage, one log line per attempt, and a nonce content-security policy without `'unsafe-inline'` for the served page's scripts (AC-A3 to AC-A9; today `script-src 'self' 'unsafe-inline'`, `local/server.py:40-42`) | ASSUMED | Default: the list above, refined under a threat model at PBI-031's spec gate (AC-A8) | Medium — a weaker list reopens the DNS-rebinding and CSRF risks that row 24 closed for reads |
| 32 | (rev 6) "Answering from the board: any agent on this PC can click the board or edit its database as if it were you. How should a board answer be trusted?" | **As the owner's, whoever gave it.** Construction still limits who writes: only the server's POST handler builds an answer, the collector never opens the answers file (AC-A2), and the refresher's answers guard stays until the refresher goes (`exporters/refresh.py:115-120`). Rule: `CLAUDE.md` still tells agents not to answer, and keeps build and smoke-test work off the owner's server (AC-A10; today `CLAUDE.md:51-53`). The transcript tripwire becomes an **audit record**: answers that follow a tool call able to send one are marked for the owner to read (PBI-033), and the marks never decide whether an answer counts. What the audit cannot see is stated, not closed: a URL built at run time, a script file written first, editing a transcript or the board database, a session under `sessions.exclude` (`local/collector.py:177-179`, `:233-236`), a stopped collector, and a script injected into the page (AC-G5; the nonce policy, AC-A9, guards the last) | CONFIRMED | Owner, 2026-09-19, verbatim: "Just procees as if it were me" | **High** — any agent on this PC can give an answer that counts as the owner's; the audit shows only one that is not evading |
| 33 | (rev 6) Which approvals go through answers (S-31)? | Two: a plan approval of a solution-spec revision (the plan gate), and the acceptance of a review's conditions (a GO-WITH-CONDITIONS round). External-review go-aheads, merges, store deletes (C-12), Task Scheduler changes and per-PBI spec-gate rows stay in chat | ASSUMED | Default: those two only, as S-31 names | Medium — widening this adds surfaces that row 34's binding must cover |
| 34 | (rev 6) Does a board approval replace the chat approval at the plan gate? Asked: "Row 34: does approving a plan on the board pass the plan gate by itself, or should it also need a one-line chat confirmation naming the answer's id?" | **Board approval alone.** A `planApproval` is bound to git's blob id of the committed spec the owner saw (row 50), and a `conditionsAccepted` to one review run (AC-P1). The backlog-delivery runbook records "the exact human approval message" in the Plan-gate record and is not in this repo (`~/.claude/plugins/cache/agent-catalog/backlog-delivery/0.2.0/skills/pbi-plan/SKILL.md`, step 3), so it is not changed: the transcribed answer id and note are that message. The planner picks approvals up from `local/answers.py list` rather than waiting on chat, and an `approve` accepts the default of every row still ASSUMED in the approved text (AC-P3). No chat step remains. Other approvals stay in chat (row 33) | CONFIRMED | Owner, 2026-09-19, verbatim: "Board approval alone" | **High** — an agent that clicks *Approve* passes the plan gate, which everything downstream builds on; the owner accepted this with row 32 |
| 35 | (rev 6) What does an accepted-conditions answer change? | A page overlay: a derived `conditions` item with a matching `conditionsAccepted` shows as accepted and leaves "Needs attention" (AC-Q2). The derivation and the collector stay unaware of answers. This gives PBI-010 row Q-3 an owner-chosen remedy, one item at a time (`docs/backlog/specs/pbi-010-derived-status.md:1111`, `:524`) | ASSUMED | Default: an overlay on the page | Low — putting it in the derivation instead would make the collector read the answers file (row 28) |
| 36 | (rev 6) When is "the shadow period shows derived state is trusted" (row 15)? | Trigger T3: at least 14 days of shadow panel since PBI-010 merged; at least 5 work items named by a run; 0 unexplained "Runs ahead" or "Hand-kept ahead"; Q-3 settled; the owner's verbatim decision. Judged per project by the owner. The switch is reversible (`docs/backlog/specs/pbi-010-derived-status.md:493`), and only the owner flips it (`:498-507`) | ASSUMED | Default: T3 as written | Medium — too loose, and the Backlog shows stale derived state; too strict, and the hand-kept file lingers. Either is reversible |
| 37 | (rev 6) When is the artifact retired, and what does it cost? Asked: "Row 37: retire the published claude.ai artifact after 30 days of reliable local running (no earlier than 2026-10-19), accepting there's then no board away from this PC?" | **Now.** PBI-037 freezes the artifact and stops the refresher at this revision's approval, after T4's same-day check: PBI-007 merged and serving, adapter parity, and this answer quoted as the acceptance of the loss. It stays reversible: until PBI-038 merges, restarting the refresher loop restores the artifact (AC-V4). PBI-038 removes the push path only once PBI-007's log-on demonstration (AC-65) is accepted and 7 days have passed (T4.4). The loss: no board away from the PC (NFR-19, `docs/prd/dispatch-board.md:567`; C-2 and C-18, `:576`, `:592`), no copy off this machine, and no replacement in this plan, since Unraid and Azure stay in Future iterations | CONFIRMED | Owner, 2026-09-19, verbatim: "retire it now" | **High** — the owner loses remote viewing until the Unraid deployment or Azure hosting is revived |
| 38 | (rev 6) What does "retiring the artifact" do to the artifact itself? | It freezes it. The `meta/*` and `status/*` documents are exported to `snapshot/`, one final status message is written, and the refresher stops (PBI-037). The artifact is not deleted or republished. The push-path code is removed only after PBI-007's log-on demonstration and a 7-day undo window (PBI-038, T4.4). Deleting the artifact is the owner's own act and is not planned; "retire it now" (row 37) does not say "delete" | ASSUMED | Default: freeze, then remove the code later | Medium — deleting at once would destroy the store with no way back |
| 39 | (rev 6) Does reviving the answer path need an ADR? | Yes. C-17 requires an accepted ADR before the page may write (`docs/prd/dispatch-board.md:591`), since it reverses FR-64 (`:332`) and FR-183 (`:443`). ADR-0002 is written at this revision's plan gate once row 25 is confirmed. Retiring the artifact follows ADR-0001's switch-over clause ("keep running until the owner retires them"), so it needs no new ADR | RESOLVED | `docs/prd/dispatch-board.md:591`, `:332`, `:443`; `docs/adr/0001-local-first-architecture.md` (Decision, Switch-over) | Low |
| 40 | (rev 6) Can answers reach the artifact? | No. The refresher refuses an `answers` collection (`exporters/refresh.py:115-120`), and the artifact cannot reach the local server (C-18, `docs/prd/dispatch-board.md:592`). What the artifact's Assumptions tab shows instead is row 48 | RESOLVED | `exporters/refresh.py:115-120`; `docs/prd/dispatch-board.md:592` | Low |
| 41 | (rev 6) What identifies the row an answer is for? | Ledger rows are integers parsed from the spec (`exporters/derive.py:1119-1133`), and revisions append rows rather than renumbering them. An answer binds to the project, spec path, revision, row number and a hash of the question text, so a renumbered or reworded row cannot silently take an old answer (AC-A1, AC-A3) | ASSUMED | Default: bind to row number plus question hash | Low |
| 42 | (rev 6) Is PBI-010 built? | No. It is In Progress, started 2026-09-19 (`docs/backlog/BOARD.md`, In Progress; HEAD `5e4f97c`, "PBI-010 started"), and holds the `page` slot. It has not merged, so the shadow period has not started, PBI-035 and PBI-036 depend on it, and T3 cannot start before it merges | RESOLVED | `docs/backlog/BOARD.md` (In Progress); commit `5e4f97c` | Medium — T3's earliest date moves with PBI-010 |
| 43 | (rev 6) What survives when the refresher is removed, and what else must change? | `local/tabs.py` imports `derive` and `export_board` (`local/tabs.py:27-30`), and the collector imports the shared module, so the exporters stay. Three test modules besides `tests/test_refresh.py` import `refresh`: `local/tests/test_conformance.py:19` (AC-69's conformance check plans through `refresh.plan()` at `:253`), `local/tests/test_tabs_equivalence.py:18` (the status rule of `local/tabs.py` is pinned against `refresh.plan` and `refresh.commit`, `:67-72`, `:163-175`) and `tests/test_export_sessions.py:1282`. PBI-038 moves all three off it (AC-X6) and has them in its allowed areas. FR-133 and AC-86 retire with `refresh.py`, since nothing writes the store any more | RESOLVED | `local/tabs.py:27-30`; the three import sites cited; `CLAUDE.md`, "Refresh procedure" | Low |
| 44 | (rev 6) What verification tier applies? | Tier 4 for PBI-031, PBI-033, PBI-034 and PBI-035 (the shared record shapes and `records.shapes.json`) and for PBI-038 (a module deletion). Tier 3 for PBI-032, and for PBI-036, whose owner-made `workItemStatus` switch changes behaviour (the tiles, the state column and "Needs attention" change source): the three suites on a tree holding the switch, plus AC-H4's demonstration. Tier 1 plus demonstration for PBI-037, whose diff holds no executable file (shown by its diff stat). Each runs the three `[test_commands]` suites | RESOLVED | `backlog-delivery.config` `[test_commands]`; the verification-gate-tiers rule | Low |
| 45 | (rev 6) Will the autonomy resolver flag the answer write surface by itself? | No. `backlog-delivery.config:87` sets `security_paths = []`, so a PBI touching `local/server*` is not a security path unless someone passes `--security-path`. How that is closed is row 49 | RESOLVED | `backlog-delivery.config:87` | Medium — PBI-031 and PBI-034 edit the write surface |
| 46 | (rev 6) How long are answers kept, and backed up? | Kept forever: they are exempt from row 12's 7-day window and from the mass-delete guard, since the collector never opens the file. The durable copy is each answer's transcription in the repo. The answers file itself is not backed up | ASSUMED | Default: kept forever, file not backed up | Low — a lost file loses only untranscribed answers, and `verify` would then fail loudly on the missing ids. The audit marks live on session documents, not in the answers file, and last as long as those (AC-G3) |
| 47 | (rev 6) How does the PRD catch up? | After approval, a `chore-work` change re-baselines the PRD to revision 4. It:<br>• un-defers FR-95, FR-131, FR-132, NFR-23 and AC-87 as amended by rows 25 and 30, with FR-95's "store it in the local database" amended to the separate answers file (row 28);<br>• supersedes FR-183 and its AC-118 (no answers route), and FR-64 for the local page;<br>• supersedes D-22 (answers deferred) and amends C-16: "stamped with the viewer's identity" becomes the constant writer of row 30, and "every agent must never write answer records" becomes the owner's decision that a board answer counts as theirs (row 32), with the agent rule kept in `CLAUDE.md`;<br>• adds the answer record to FR-100's list, and the session's `answerSuspects` to the session shape (PBI-033);<br>• restates NFR-23 as a checkable limit: 0 answer records carry a `writer` other than `page` or a `surface` other than `local`, by inspection and test, which does not establish who clicked (row 30);<br>• names the answer record's fields in FR-132 and AC-87 (`specPath`, `specRevision`, the row number, `questionSha`, `surface`, optional `supersedes`) in place of "row id" and "the writer's identity", and adds "on the local adapter only" to FR-131 (row 25);<br>• marks C-17 met by ADR-0002;<br>• retires, with PBI-037 and PBI-038, every requirement whose subject is the refresh script, the refresher or the store, FR-133 and AC-86 included (row 43). Round 6 names the candidates (FR-45, FR-47–FR-53, FR-57, FR-58, FR-60–FR-62, FR-99, FR-103's refresher half, FR-144, FR-149–FR-152, FR-160, NFR-1, NFR-5, AC-33–AC-38), and the re-baseline checks each against that rule;<br>• moves S-31, S-37, S-39 and S-40 into scope, and turns this spec's criteria AC-A1 to AC-A10, AC-G1 to AC-G5, AC-B1 to AC-B5, AC-P1 to AC-P3 and AC-Q1 to AC-Q3 into PRD requirements and ACs, so S-31 and the audit carry requirements of their own;<br>• records the owner's revision-6 answers as decisions D-27 onwards.<br>Until then, the revision-6 criteria are this spec's own (AC-A to AC-X) | ASSUMED | Default: a chore after approval, not a PBI | Low |
| 48 | (rev 6) What does the artifact's Assumptions tab show once answering exists? | The rows read-only, with one line saying answers are given on the board on the PC, and no controls or write method (AC-B1). Answers themselves never reach it (row 40) | ASSUMED | Default: read-only rows and a pointer line | Low — the artifact is retired at T4 anyway |
| 49 | (rev 6) How is the answer write surface registered as a security path (row 45)? | A `chore-work` change adds `local/server*` and `local/answers*` to `security_paths`, merged before PBI-031 is promoted: a promotion precondition, not a recommendation. PBI-031, PBI-034 and PBI-038 are `merge_allowed_by_agent: false`; PBI-033, now an audit, is not. For this plan gate the planner passes `--security-path` by hand. `site/index.html` is not added, since it would flag every page PBI | ASSUMED | Default: the chore as a precondition of PBI-031, and owner merges for those three | Medium — without it, PBI-034's `pbi-work` would not see a security path and could be agent-merged under the standing authorisation |
| 50 | (rev 6) How is a plan approval bound to the text the owner saw, and how does `verify` survive the edits made at approval? | `specBlob` is git's own blob id of the committed spec, `git rev-parse HEAD:<specPath>`, offered only when `git ls-files --error-unmatch` finds the path in its exact case and `git --no-optional-locks status --porcelain` prints nothing for it; every git call checks its exit code (AC-P1). The exporter and collector read it with git for the spec tab; the page posts what it rendered; the server runs the same checks (`git ls-files`, `git status`, `git rev-parse`, and `git cat-file` for the committed text) and refuses a mismatch or an uncommitted file (AC-P1, AC-Q1). Git hashes the committed content after its line-ending conversion, so a CRLF working copy (`core.autocrlf = true` on this PC) gives the same id everywhere. `verify` reads both texts with `git show`, checks the blob was committed, and checks the transcription commit changes only `status:`, `approved_revision:` and the Plan-gate record (normalising drops that whole section, design notes in it included, since it is a record); later decomposition commits do not fail it, and the approved commit must reach the transcription's branch unsquashed (AC-P2, AC-P3). Rejected: hashing the bytes on disk, which gives a different id from git on every CRLF working copy (round 5, PG6-r5-4); hashing LF-normalised text, which works but needs a second definition kept in step on three sides; failing `verify` on any later change, which the approval edits themselves trigger | ASSUMED | Default: git's blob id on every side; check at the transcription commit | **High** — with board approval alone (row 34) the binding is the plan approval's only check: a looser one lets an edit ride on the owner's approval, and a stricter `verify` fails after every legitimate approval and gets ignored. The owner's approval of this revision accepts this default (AC-P3) |

---

## Plan-gate record

**Reviewed by:** same-vendor subagent with a clean context (Claude Code Plan agent following `pbi-review`)
**Review date:** 2026-09-11. Round 1 on revision 1 was CHANGES-REQUIRED. Round 2 on revision 3 was CHANGES-REQUIRED. Round 3 on revision 4 was APPROVE-WITH-NOTES, with its notes applied in revision 5 (dispositions in the round-3 note).
**Review note path:** docs/backlog/reviews/dispatch-board/plan-gate-review-r3.md (rounds 1 and 2: plan-gate-review-r1.md, plan-gate-review-r2.md)

**Human approval:**
> **Approve (Recommended)** — the owner's answer, on 2026-09-11, to: "Approve the plan (spec revision 4: 21 PBIs, agent catalogue tab first)? Approval only takes effect if the round-3 independent review comes back clean; if it asks for changes I'll apply them and come back to you."

**Approved by:** the owner (jdk)
**Approval date:** 2026-09-11. The condition was met: round 3 returned APPROVE-WITH-NOTES and every note is disposed of in revision 5. The owner's changes to PBI-017 are applied, and PBI-017's refined spec gets its own review before code.

**Assumptions resolved:**
- Owner, 2026-09-11, via the plan-gate decision prompt:
  - rows 5 ("Not now"), 6 ("On this PC first") and 3 ("Make the repo private");
  - "Accept all defaults" for rows 1, 4, 8, 10, 11, 12, 13, 14, 19, 20, 21, 23.
- Owner, 2026-09-11, after revision 3: row 7 ("Yes, that's fine"), row 15 ("Yes, side by side first"), row 24 ("Yes, harden it"). Rows 7 and 24 are approved in their revision-4 wording.
- Owner, 2026-09-11, after revision 4: row 16, "Change PBI-017's criteria", choosing "Include skills too" and "Show what each agent is for" (applied in revision 5, with rows 19, 20 and 22 widened to match).

### Revision 6 plan-gate record (pending)

Not filled until revision 6 passes its own plan gate. The record above is revision 5's and stays as it is.

- **Revision 6, round 2 after plan-gate-review-r4.** It applied round 4's findings; the Round-4 table says where.
- **Revision 6, round 3 after plan-gate-review-r5.** This text applies round 5's findings and the owner's answer to row 32; the Round-5 table says where. Where the two tables disagree, round 5's governs: the owner's trust decision supersedes round 4's PG6-1 design (durable alarms, alarm clearance and the honour rule's alarm check), PG6-4's `tripwire_alarms` table, PG6-6's alarm controls and PG6-8's `merge_allowed_by_agent: false` for PBI-033.
- **Revision 6, round 4 after plan-gate-review-r6.** This text applies round 6's findings and the owner's answers to rows 25, 34 and 37; the Round-6 table says where. Round 6 governs over rounds 4 and 5 where they disagree. T4 was renumbered: T4.1 to T4.3 in the older tables mean the retired 30-day criteria, T4.5 and T4.6 no longer exist (T4.4 is now the push-path removal), and PG6-r5-10's chat step is gone.
- **Revision 6, round 5 after plan-gate-review-r7.** Round 7 (`docs/backlog/reviews/dispatch-board/plan-gate-review-r7.md`) returned APPROVE-WITH-NOTES, with no further round needed; its notes are applied here, and the Round-7 table says where.
- **Resolver signals to declare:** `--change-class epic`, `--security-path` (PBI-031 opens the local server's first write surface, and `security_paths` is empty, rows 45 and 49), and `--high-impact-assumed` (row 50). The plan gate therefore resolves to the owner, whatever tier applies.
- **Independent review (rev 6):** round 4 (`docs/backlog/reviews/dispatch-board/plan-gate-review-r4.md`) and round 5 (`docs/backlog/reviews/dispatch-board/plan-gate-review-r5.md`) returned CHANGES-REQUIRED, and so did round 6 (`docs/backlog/reviews/dispatch-board/plan-gate-review-r6.md`). Round 7 (`docs/backlog/reviews/dispatch-board/plan-gate-review-r7.md`) returned APPROVE-WITH-NOTES; its notes are applied, and no further round is needed.
- **Owner's approval (rev 6):** **"Approve"**, the owner's answer on 2026-09-19 to the approval question below, which named commit `db14c0b` (the spec's git blob there is `8fbdd3eba4a1042e2dfdbeb1689369eb015eb390`). Approved by the owner (jdk). The approval accepts the 14 rows still ASSUMED at that commit, rows 28–31, 33, 35, 36, 38, 41 and 46–50, including row 50 (high impact). Resolver: `--change-class epic --security-path --high-impact-assumed` gave `gates.plan = human` (overrides `high_impact_assumed`, `security_path`), so the owner's approval was required and is the approval. This record is its own pull request, never squashed with later edits (PG6-r7-2).
- **Approval question (rev 6):** "Approve the dispatch-board plan, spec revision 6 at commit `db14c0b`? Approving accepts the 14 default answers still open (rows 28–31, 33, 35, 36, 38, 41 and 46–50) and freezes the published claude.ai page today (PBI-037). The one high-impact default is row 50: when you approve a plan on the board, your approval is tied to the exact saved version of the spec you were looking at. If the text was changed before your approval was recorded, the check fails. Edits made afterwards, such as splitting the plan into work items, are allowed, and the check only reports them."
- **Assumptions resolved (rev 6):** rows 25, 32, 34 and 37, by the owner on 2026-09-19.
  - Row 25, asked "Row 25: board answers only work on the board on this PC, with no answering away from it. Accept?": "Accept, this PC only (Recommended)".
  - Row 34, asked "Row 34: does approving a plan on the board pass the plan gate by itself, or should it also need a one-line chat confirmation naming the answer's id?": "Board approval alone".
  - Row 37, asked "Row 37: retire the published claude.ai artifact after 30 days of reliable local running (no earlier than 2026-10-19), accepting there's then no board away from this PC?": "retire it now".
  - Row 32: Asked "Answering from the board: any agent on this PC can click the board or edit its database as if it were you. How should a board answer be trusted?", the owner answered, verbatim: "Just procees as if it were me".
- **ASSUMED rows confirmed (rev 6):** _pending_ for rows 28–31, 33, 35, 36, 38, 41, 46–50. The owner's approval of this revision accepts all of them at their defaults (AC-P3's rule, applied here in chat).
- **Outstanding:** only the owner's explicit plan approval of this revision, given in chat to the question above (AC-P3). No question row remains. Row 50 is the one high-impact row still ASSUMED, and the question names it in plain words so the owner accepts it knowingly.
- **ADR at approval:** ADR-0002 (row 39).

#### Round-4 dispositions

| Finding | Disposition | Where / why |
|---------|-------------|-------------|
| PG6-1 | Applied | Honour rule counts every uncleared alarm, whatever its time (AC-G3, row 32). Alarms are durable `alarm` records the collector never deletes (AC-G4). Clearing is an `alarmCleared` answer from the board (AC-A1, AC-A3, AC-B4); a forged clearance raises a new alarm. Excluded sessions stated as a residual (AC-G5, row 32). A plan approval also needs a chat confirmation (AC-P3, row 34). PBI-033 now precedes PBI-031 so the clearance can name real alarms |
| PG6-2 | Applied | Bound to the committed blob the page rendered; the server refuses a mismatch with the file on disk (AC-P1, AC-Q1). `verify` checks at the transcription commit, so the approval edits and later decomposition do not fail it (AC-P2, row 50). The git-blob alternative was taken over a normalised hash of the working file |
| PG6-3 | Applied | Row 43 cites the three import sites. PBI-038's allowed areas include them, and AC-X6 moves them off `refresh` without dropping the conformance or status-rule checks |
| PG6-4 | Applied | Option (a): `records.ANSWER_TABLES`, with the answers DDL from its own `local/schema.py` function; PBI-031 may touch `local/schema*` (AC-A1, AC-A2). Row 27 corrected, naming the tests that change and those that stay true. The alarm table is named `tripwire_alarms` so `test_no_answers_table` holds (AC-G4) |
| PG6-5 | Applied | Project checked against `projects[]`; spec path from the config only, never the body; network-path guard on it; a conditions run must belong to the posted project (AC-A3, AC-P1, row 31) |
| PG6-6 | Applied | Page-script forgery added to row 32's residuals and AC-A8's threat model. Nonce content-security policy without `'unsafe-inline'` (AC-A9). AC-B5 asserts answer and alarm controls render nothing through `md()` |
| PG6-7 | Applied | T4.3 takes active days from transcript timestamps, captures pass days weekly before the log rotates, and defines a stop from the log-on line |
| PG6-8 | Applied | The `security_paths` chore is a promotion precondition of PBI-031 (Metadata; row 49). Row 45 is Medium. PBI-034, and PBI-033, are `merge_allowed_by_agent: false` |
| PG6-9 | Applied | Kept owner-only, as the PBI-010 spec says: AC-H2 has no agent path, and PBI-036's areas block `board.config.json` |
| PG6-10 | Applied | Row 41 cites `exporters/derive.py:1119-1133`; row 45 cites line 87; the sequencing records PBI-028 Done (`f7b21f9`, #31) and PBI-012 merged (`312e2f5`, #34) |
| PG6-11 | Applied | Acknowledged in the revision-6 sequencing (overlap with PBI-033, PBI-031 and PBI-035 accepted by name) and under T4.6 (the triggers count auto-linked sessions once PBI-030 merges). PBI-030 is not planned here |
| PG6-12 | Applied | Row 47 adds AC-118, C-16's identity wording, FR-95's storage wording, D-22, FR-100, FR-185, and FR-133 and AC-86 retiring at PBI-038 |
| PG6-13 | Applied | Row 44: PBI-036 is tier 3 plus AC-H4's demonstration |
| PG6-14 | Applied | G-8 gives G-6's new first sentence; G-6 is marked "rev 6 proposes". The rewording is made at approval |
| PG6-15 | Applied | AC-V3 takes the last push with no linked run `running`, and sets `live: false` on every status document |
| PG6-16 | Applied | Rows 40 and 45 are now RESOLVED facts; their choices are rows 48 and 49 |
| PG6-17 | Applied | AC-A2 (read-only open in `answers.py`), AC-A3 (constant-time token, `Content-Length`, no chunked bodies, reload hint, both local origins), AC-A5 (hub signalled on store; no `answers` key when empty) |
| PG6-18 | Applied (no change beyond PG6-1) | Row 30 says `writer: "page"` meets NFR-23 to the letter but proves nothing about provenance |

#### Round-5 dispositions

| Finding | Disposition | Where / why |
|---------|-------------|-------------|
| PG6-r5-1 | Superseded by the owner's decision | The finding shows the alarm check could not gate in time. The owner decided a board answer counts as theirs (row 32), so no alarm check gates an answer and freshness no longer matters. The `alarms` command and the honour rule's alarm clause are removed (AC-A6, AC-P3) |
| PG6-r5-2 | Applied, as audit | Browser-automation and `javascript_*` calls on the local origin are recorded (AC-G1). Smoke tests of the answer controls run on a throwaway server and answers file, never port 8765 (AC-A10, AC-B4, AC-Q3). An agent driving the page is covered by the owner's decision, so AC-A8's threat model scopes it out by name |
| PG6-r5-3 | Applied in part; hardening not taken | Row 32 no longer claims a count that cannot reach zero, and AC-G5 lists the routes the audit cannot see. Re-deriving alarms, flagging `board.db` and `tasks.py stop`, and alarming on a growing `exclude` list are not taken: they only made a gate harder to evade, and there is no gate now. PBI-033 needs no evasion threat model for the same reason. The choice this finding put to the owner was put and answered (row 32) |
| PG6-r5-4 | Applied | `specBlob` is git's blob id, `git rev-parse HEAD:<specPath>` with a clean `git status --porcelain`, computed with git by the exporter, the collector and the server alike; `verify` reads both texts with `git show`. A test covers a CRLF working copy of an LF-committed spec (AC-P1, AC-P2, AC-Q1, row 50) |
| PG6-r5-5 | Applied | Only calls that could send are recorded; mentions are not (AC-G1). The shapes are measured on the revision-6 planning and review transcripts too (AC-G2). Build and verify work never targets port 8765 or the real `answers.db` (AC-A10). Batch clearing is gone with the clearing itself |
| PG6-r5-6 | Applied | T3.5 is chat only, like T4.5 |
| PG6-r5-7 | Applied | Row 42 and the sequencing say PBI-010 is In Progress and holds the `page` slot (`5e4f97c`) |
| PG6-r5-8 | Applied | The spec tab record carries `specCommitted` from `git status --porcelain -- <specPath>`, so the page parses no `dirty` lines, and the server repeats the check (AC-P1, AC-Q1) |
| PG6-r5-9 | Applied | AC-P3 puts the status banner, a revision-history line, G-6's rewording and the row move in a later commit; the `-S` search is limited with `-- <specPath>` (AC-P2) |
| PG6-r5-10 | Applied | The chat confirmation is now row 34's stricter option, and AC-P3 and row 34 say it relies on the owner reading the Plan-gate record, never on parsing transcripts. The page shows the answer id's first 8 characters after a submission (AC-Q1) |
| PG6-r5-11 | Applied | T3.1 and the sequencing give T3's earliest date as PBI-010's merge date plus 14 days; T4.6 and the sequencing give 2026-11-18 |
| PG6-r5-12 | Applied | PBI-033 depends on PBI-030, so they never run side by side; it is off the critical path now it gates nothing |
| PG6-r5-13 | Moot | No clearances exist any more. Row 46 notes that the audit marks are rebuilt from transcripts, so losing `answers.db` loses only untranscribed answers |

**PBI-033's place.** It stays a PBI of its own rather than merging. Its work is in the shared derivation, the session shape and the page (`exporters/derive.py`, `exporters/export_sessions.py`, `local/records*`, `site/**`); merging it into PBI-031 would put a tier-4 exporter change inside the security-path PBI, and merging it into PBI-032 would put exporter and record-shape work into a page-only PBI that is on the critical path. As an audit it gates nothing, so it moves behind PBI-032 and PBI-030 and joins the `page` group at High, since it now edits `site/**`.

#### Round-6 dispositions

| Finding | Disposition | Where / why |
|---------|-------------|-------------|
| PG6-r6-1 | Applied as proposed | PBI-037 is untriggered with `depends_on: []`, promoted at approval behind T4's same-day check (T4.1 to T4.3), and states its revert (AC-V4). PBI-038 depends on [PBI-037, PBI-007] and waits for T4.4: PBI-007 Done (AC-65) and a 7-day undo window, the owner able to shorten it. The 30-day conditions are dropped. G-11, the key decisions, track 10, the graph, the sequencing and rows 37 and 38 follow |
| PG6-r6-2 | Applied | AC-P3 defines the pickup (`local/answers.py list` at each orchestrator session and on its loop), names the transcription as the runbook's approval message, says an `approve` accepts every row still ASSUMED in the approved text, and says revision 6 itself is approved in chat. The chat step is gone from AC-P3, G-9, the key decisions and row 34. Row 33 is unchanged: the answer concerned the plan gate only |
| PG6-r6-3 | Applied | Row 50 is High, and `--high-impact-assumed` names it. It stays ASSUMED: the owner's approval of this revision accepts it, and the Plan-gate record says the approval question names it |
| PG6-r6-4 | Applied | AC-P3: the transcription commit holds the answer id, note, `status:` and `approved_revision:`; `verify`'s output follows in its own commit; assumption answers are committed before the approved text or after the transcription, never with it |
| PG6-r6-5 | Applied | AC-P1: `git ls-files --error-unmatch` for tracked, exact-case paths; every git call checks its exit code; `specBlob` must match `^[0-9a-f]{40}$`; tests for a wrong-case, an untracked and an ignored spec |
| PG6-r6-6 | Applied | AC-P3: the approved commit reaches the transcription's branch before the transcription, never squashed with it, with a test showing `verify` name the cause; the binding follows `HEAD` of `repoPath` |
| PG6-r6-7 | Applied | PBI-033 depends on PBI-034 as well |
| PG6-r6-8 | Applied | Row 47 restates NFR-23, names FR-132's and AC-87's fields, adds FR-131's local-only limit, marks C-17 met by ADR-0002, states the rule that retires the refresher-only requirements with round 6's candidate list to check, and turns the spec's revision-6 criteria into PRD requirements |
| PG6-r6-9 | Applied | The Round-4 precedence line now also names PG6-4's alarm table, PG6-6's alarm controls and PG6-8's PBI-033 flag; the table itself is left as history |
| PG6-r6-10 | Applied | AC-G1 counts a call acting on a tab last seen on the local origin; AC-G5 adds the injected script and an unidentified tab; AC-G3 and row 46 say the marks last as long as their session document (7 days for an unlinked one) |
| PG6-r6-11 | Applied | AC-P1 names the third read (`git cat-file -p`), runs `status` with `--no-optional-locks`, a timeout and `no_window_flags()`, and adds `local/answers.py`'s launches to the reviewed list |
| PG6-r6-12 | Applied | AC-A9 cites `local/server.py:40-42`; rows 25, 28, 29 and 43 cite `CLAUDE.md` by heading |
| PG6-r6-13 | Applied | Rows 25, 34 and 37 CONFIRMED and quoted above; the question list, the resolver signal and the pending list updated; row 25 no longer awaited in the key decisions; ADR-0002 is due at approval |

#### Round-7 dispositions

| Finding | Disposition | Where / why |
|---------|-------------|-------------|
| PG6-r7-1 | Applied | AC-V6: after the freeze nothing republishes, refreshes or writes the store, including the paused build's hand-written `meta/status` message, except the owner's revert; any such write restarts T4.4's window. AC-V7: the orchestrator's session memory note is updated separately, as a close-out step outside the repository |
| PG6-r7-2 | Applied | AC-P3: recording the approval is its own PR, never squashed with later edits; the banner, history line, G-6, row move and decomposition follow in a later PR; a second squash test covers a banner edit |
| PG6-r7-3 | Applied | AC-V3: the last push waits until no run in the export is `running`, and no agent is dispatched between it and the final write |
| PG6-r7-4 | Applied, order B | The plan approval is PBI-037's promotion (Metadata); its evidence file is its first act (AC-V1); the approval question says it freezes the page today |
| PG6-r7-5 | Applied | AC-P3 Pickup: session start and any loop that session runs; only the latest unsuperseded `planApproval` counts; `changes` returns the spec to the planner with the owner's note |
| PG6-r7-6 | Applied | The approval question is written out in plain words, names the commit (placeholder `<commit id>` until revision 6 is committed), the 14 defaults it accepts, row 50 and the freeze today |
| PG6-r7-7 | Applied | The round-6 precedence line says round 6 governs, explains the T4 renumbering and retires PG6-r5-10's chat step; the older tables are left as history |
| PG6-r7-8 | Applied | Scope line says T4.4; row 50 names the four git reads and that normalising drops the whole Plan-gate record; T4.4 counts `refresh.py --commit` or a store write, not a dry run, and its earliest date includes PBI-037's close date plus 7 days |
