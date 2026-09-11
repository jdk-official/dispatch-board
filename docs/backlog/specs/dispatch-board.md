---
title: Dispatch board — next iteration (agent catalogue, local-first app, features) and v1 defect fixes
status: approved
spec_version: 6
revision: 5
parent_prd: docs/prd/dispatch-board.md
---

# Solution Spec — Dispatch board: next iteration and v1 defect fixes

<!-- Authored by the planner (pbi-plan) from the PRD at docs/prd/dispatch-board.md, revision 2.
     Approved at the plan gate on 2026-09-11 (see Plan-gate record). This document is the parent
     authority for every PBI it spawns. -->

**Status: approved at the plan gate on 2026-09-11.** The PBIs below are decomposed into
`docs/backlog/pbi/` and listed under **Proposed** on `docs/backlog/BOARD.md`.

**Revision history.**
- **Revision 2:** the owner added PBI-017 (the agent catalogue tab, built first) and PBI-018 (future iterations on the Backlog).
- **Revision 3:** applied plan-gate review round 1 and the owner's answers. Answers from the board are deferred; the local app goes on the PC first; the repo is private; the defaults are accepted.
- **Revision 4:** applied review round 2: acceptance criteria for PBIs the PRD does not cover, dependency edges that enforce order, and a catalogue record.
- **Revision 5 (2026-09-11):** applied the round-3 notes (APPROVE-WITH-NOTES; `docs/backlog/reviews/dispatch-board/plan-gate-review-r3.md`) and the owner's changes to PBI-017: "Include skills too" and "Show what each agent is for". It records the owner's approval.

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
- **G-6** No agent, refresher or collector can ever write a plan-gate answer to the board (PRD C-16, FR-133, FR-134). The answer write path itself is deferred (row 5).
- **G-7** The owner can see every agent and skill in the agent catalogue, grouped by what it is for, and how much of it the projects use: uses per entry, when it was last used, which projects used it, and what has never been used (owner request, 2026-09-11; built first).

---

## Scope

### In scope

- `exporters/**` — the defect fixes FR-80 to FR-84, the carried-tab marker and config type checks, the refusal of an `answers` collection (FR-133), the catalogue export (PBI-017, a new `exporters/export_catalogue.py` run by `refresh.py`), the future-iterations list (PBI-018), and a shared derivation module that the exporters and the collector both use (PBI-004), plus the derivations features 2 to 7 need.
- `site/**` — the page defect FR-83 and the design-rule deviations (row 13), the agent catalogue tab, the Later group on the Backlog, the stale-board warning, the "Waiting on you" panel, findings ledger, test trend, cost per work item, usage-limit forecast, run detail, timeline, and the data-adapter seam.
- `local/**` — new: record shapes and the SQLite schema (including the catalogue), collector, local server (page, snapshot, live push; ingest endpoint only for Unraid), Task Scheduler log-on start, and an optional Unraid container definition. There is no answers endpoint (row 5).
- `board.config.json`, `exporters/board_config.py`, `projects/**` — new keys for the catalogue paths, the local server port and the database path; the derived-state shadow period (PBI-010).
- `docs/adr/0001-local-first-architecture.md` — accepted at this plan gate (row 8).
- `docs/prd/**`, `docs/backlog/evidence/**`, `CLAUDE.md`, `README.md` — procedures for the local app, the C-16 rule ("no agent writes answers") and the PRD re-baseline (PBI-022).
- The agent catalogue, read only: `~/.claude/plugins/marketplaces/agent-catalog/plugins/*/agents/*.md`, `~/.claude/plugins/marketplaces/agent-catalog/plugins/*/skills/*/SKILL.md` and `~/.claude/plugins/installed_plugins.json`. It is never written.
- `snapshot/**` — export of the six store leftovers before their owner-approved deletion (PBI-021).

### Out of scope

- Re-planning v1 or project-first navigation (delivered, `2742ca6`).
- Answering assumptions from the board, deferred by the owner on 2026-09-11 (row 5; listed under Future iterations). This defers:
  - FR-95, FR-131 and FR-132;
  - NFR-23 and AC-87;
  - the answer record of FR-100;
  - the answers endpoint.

  The guards FR-133 and FR-134 stay in the plan.
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
5. **Unraid (PBI-016)** is last and optional (row 6).

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
| PBI-016 | Unraid deployment: collector upload and ingest endpoint with a secret from the environment, rejecting answers, and a container definition (FR-89, FR-134, AC-71, AC-72) | [PBI-005, PBI-007] | local-app | Low | false | true |

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
metadata. PBI-018 shows them on the Backlog tab as a separate "Later" group.

- **Answering assumptions from the board**: Accept / Override plus a note, recorded with provenance. This is the former PBI-015, deferred by the owner on 2026-09-11 (row 5), covering FR-95, FR-131, FR-132, NFR-23, AC-87 and the answer record. The guards that stop agents writing answers are already in this plan (G-6).
- **Phone notifications**: a review returns NO-GO, a run is cut off, the build goes idle, a session is waiting on the owner (brief "Future iteration"; PRD S-29).
- **Hosting on Azure**: Static Web Apps, Functions, a database and Entra ID, plus the hosted API adapter (PRD S-27, S-28, D-17).
- **Archive beyond 7 days**: keep sessions and runs older than the 7-day window (PRD S-30, D-15).
- **Continuous integration**: run both test suites on every push (PRD S-16).
- **Using answers for approvals**: record plan approval and the acceptance of review conditions through the answer mechanism (PRD S-31).
- **Other marketplaces in the catalogue tab**: agents and skills from marketplaces other than agent-catalog (row 19).
- **Retiring the hand-kept build state**: once the shadow period shows derived state is trusted (row 15).
- **Retiring the v1 artifact and its refresher**: once the local app has run for a while (row 8, ADR-0001).

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
- **PBI-016**: allowed `local/server*`, `local/collector*` (the upload half of FR-89), `local/deploy/**`, `local/tests/**`, `README.md`; blocked `site/**`.
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
  - PBI-016 (LAN exposure; optional, row 6).

---

## Assumptions & open questions

**Rows the human must confirm or correct at the plan gate:** none (the owner confirmed or corrected every row on 2026-09-11; row 16 with changes to PBI-017).

| # | Question / ambiguity | Resolution | Status | Source / chosen default | Impact if wrong |
|---|----------------------|-----------|--------|-------------------------|-----------------|
| 1 | Idle refresh cadence and the two token figures (PRD A-5, A-6) | Keep the 10-minute every-tick loop until the local app replaces the refresher. Dispatch keeps `subagent_tokens`, relabelled "reported tokens" in PBI-002, and cost per work item uses effective usage | CONFIRMED | Owner, 2026-09-11 (accepted the defaults) | Low — up to 144 small writes a day until PBI-007 |
| 2 | Is the tab-bar overflow defect (PRD FR-125–FR-128, A-24) still open? | No: the tab bar wraps, so no tab is clipped | RESOLVED | `site/index.html:58` (`.tabs` flex-wrap); commit `2742ca6` message | Low |
| 3 | Snapshot of build data in the public repo (PRD A-8) | The repo is made private on GitHub; `snapshot/` stays | CONFIRMED | Owner, 2026-09-11: "Make the repo private" (done the same day) | Medium — git history before the switch was public |
| 4 | Deleting the store leftovers (PRD A-9, D-11) | A separate owner-run PBI-021, gated by owner approval, with preconditions: the page confirmed project-first, and the six documents exported to `snapshot/` first (AC-S1–AC-S3) | CONFIRMED | Owner, 2026-09-11 (accepted); mechanism tightened by review H-2 | Low — six unused documents stay until then |
| 5 | Adopt the answer write path (PRD A-25, C-17) | Not now. The former PBI-015 moves to Future iterations; answers stay in chat. The guards stay: FR-133 in PBI-001, FR-134 in PBI-016, and the C-16 rule in `CLAUDE.md` | CONFIRMED | Owner, 2026-09-11: "Not now" | **High** — reversing later needs an ADR and the deferred PBI |
| 6 | Deployment target (PRD A-26) | On-PC first (PBI-007). Unraid (PBI-016) is last and optional, built only when the owner says so | CONFIRMED | Owner, 2026-09-11 | Medium |
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
