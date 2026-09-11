---
title: Dispatch board — next iteration (agent catalogue, local-first app, features) and v1 defect fixes
status: draft
spec_version: 6
revision: 3
parent_prd: docs/prd/dispatch-board.md
---

# Solution Spec — Dispatch board: next iteration and v1 defect fixes

<!-- Authored by the planner (pbi-plan) from the PRD at docs/prd/dispatch-board.md, revision 2.
     Must pass the plan gate (independent review + explicit human approval + every ASSUMED row
     confirmed) before any PBI is decomposed from it (SPEC §Gates, plan gate).
     This document becomes the parent authority for every PBI it spawns. -->

**Status: draft, awaiting the plan gate.** The PBI list below is the *proposed* decomposition shown
for review; no PBI file or BOARD entry exists until the owner approves this spec.

**Revision history.**
- **Revision 2 (2026-09-11):** the owner added PBI-017, the agent catalogue tab, and asked for it to be built first. The owner also asked whether the Backlog shows future iterations; that became PBI-018.
- **Revision 3 (2026-09-11):** applies every finding of plan-gate review round 1 (CHANGES-REQUIRED; `docs/backlog/reviews/dispatch-board/plan-gate-review-r1.md`), and the owner's answers of the same day:
  - answering assumptions from the board is deferred (row 5);
  - the local app goes on the PC first (row 6);
  - the repo is made private (row 3);
  - every other default is accepted.

**Already delivered, not re-planned here:**
- **v1:** the session picker, generated runs and the refresher loop.
- **Project-first navigation** (PRD D-18; FR-129, FR-130, FR-135 to FR-148), shipped in commit `2742ca6`. Its review history: GO-WITH-CONDITIONS, fixes, then GO.
- **The tab-bar overflow fix** (FR-125 to FR-128), in the same change (row 2).

---

## Goals

- **G-1** The owner can trust what the board shows: the v1 defects the reviews left open are closed, a carried-over tab is flagged on the page, and config typos fail loudly instead of changing behaviour (PRD O-6, FR-80–FR-85).
- **G-2** The board stays current from log-on onwards with no Claude session open and no Claude usage spent on refreshing, on the owner's PC first and optionally on the Unraid server (PRD O-8, D-16, D-17).
- **G-3** Moving to a host later changes only storage and transport: one set of record shapes and one data adapter in the page (PRD O-9, D-16).
- **G-4** The owner sees at a glance when data is stale and everything that is waiting on them (PRD O-10, features 1–2).
- **G-5** The owner sees each build's progress from its runs, alongside the hand-kept state until the derived state is trusted: findings, work-item state, test trend, cost, run detail, timeline and a usage-limit forecast (PRD O-11, features 3–9).
- **G-6** No agent, refresher or collector can ever write a plan-gate answer to the board (PRD C-16, FR-133, FR-134). The answer write path itself is deferred (row 5).
- **G-7** The owner can see every agent in the agent catalogue and how much of it the projects use: runs per agent, when it last ran, which projects ran it, and which catalogue agents have never been used (owner request, 2026-09-11; built first).

---

## Scope

### In scope

- `exporters/**` — the defect fixes FR-80 to FR-84, the carried-tab marker and config type checks, the refusal of an `answers` collection (FR-133), the catalogue export (PBI-017), the future-iterations list (PBI-018), and a shared derivation module that the exporters and the collector both use (PBI-004), plus the derivations features 2 to 7 need.
- `site/**` — the page defect FR-83 and the design-rule deviations (row 13), the agent catalogue tab, the Later group on the Backlog, the stale-board warning, the "Waiting on you" panel, findings ledger, test trend, cost per work item, usage-limit forecast, run detail, timeline, and the data-adapter seam.
- `local/**` — new: record shapes and the SQLite schema, collector, local server (page, snapshot, live push; ingest endpoint only for Unraid), Task Scheduler log-on start, and an optional Unraid container definition. There is no answers endpoint (row 5).
- `board.config.json`, `exporters/board_config.py`, `projects/**` — new keys for the local app (port, database path) and the catalogue path; the derived-state shadow period (PBI-010).
- `docs/adr/0001-local-first-architecture.md` — emitted at this plan gate (row 8).
- `docs/**`, `CLAUDE.md`, `README.md` — procedures for the local app, the C-16 rule ("no agent writes answers"), and a PRD re-baseline (PBI-022).
- The agent catalogue, read only: `~/.claude/plugins/marketplaces/agent-catalog/plugins/*/agents/*.md` and `~/.claude/plugins/installed_plugins.json`. It is never written.
- `snapshot/**` — export of the six store leftovers before their owner-approved deletion (PBI-021).

### Out of scope

- Re-planning v1 or project-first navigation (delivered, `2742ca6`).
- Answering assumptions from the board: the page write path, the answers endpoint and FR-95 (deferred by the owner on 2026-09-11, row 5; listed under Future iterations).
- Hosting on Azure and the hosted API adapter (PRD S-27, S-28); the seam is in scope, the hosted adapter is not.
- Phone notifications (PRD S-29) and an archive older than 7 days (PRD S-30, D-15).
- Continuous integration (PRD S-16), and redacting titles, run labels or agent descriptions (PRD S-17, D-12).
- Hooks in build sessions that report to the board, and hand-written runs (PRD S-11, S-12).
- `C:/Users/jdk/platform-catalogue/**`: the tracked build repo is read, never written.

---

## Key decisions

| Decision | Rationale | Made by | Date |
|----------|-----------|---------|------|
| Build the agent catalogue tab (PBI-017) first | Owner request: "Can we add a PBI for a new tab to show all the agents in the catalogue with coverage of what we are using? Make this the first thing we build." | Owner | 2026-09-11 |
| Defer answering assumptions from the board; keep answering in chat | Owner answer at the plan gate (row 5). The guards that stop agents writing answers stay in the plan (G-6) | Owner | 2026-09-11 |
| Make the GitHub repo private | Owner answer at the plan gate (row 3) about the committed `snapshot/` of build data | Owner | 2026-09-11 |
| Local app on the owner's PC first; Unraid last and optional | Owner answer at the plan gate (row 6) | Owner | 2026-09-11 |
| Local first, hosting later: collector → SQLite → local server → page through one data adapter; record shapes defined once — recorded as [ADR-0001](../../adr/0001-local-first-architecture.md) | Owner decision D-16; the stdlib-only technology choice was confirmed at this gate (row 8) | Owner (D-16), planner | 2026-09-11 |
| Unraid is the optional first host; the collector stays on the PC and sends records over the LAN; SQLite never on a network share | Owner decision D-17: transcripts exist only on the PC; SQLite locking over SMB/NFS is unreliable | Owner (D-17) | 2026-09-11 |
| All derivations live in one shared module under `exporters/`; the collector imports it, never re-implements it | Keeps the artifact board and the local app identical (PRD FR-87, AC-64); plan-gate review M-8 | Planner | 2026-09-11 |
| Plan on top of the delivered project-first board; do not re-plan v1 or D-18 | Both are built, reviewed to GO and live (`2742ca6`) | Planner | 2026-09-11 |
| Code changes go through `engineering-agents:code-writer` (TDD) then `review-agents:code-reviewer` until GO | Owner decision D-9 | Owner (D-9) | 2026-09-10 |

---

## Decomposition rationale

The work splits into six tracks. Each PBI names the PRD requirements it delivers. Its acceptance
criteria are the PRD's ACs for those requirements, firmed into the PBI file at decomposition
(row 16).

0. **Agent catalogue and Backlog "Later" group (PBI-017, PBI-018)** come first, at the owner's request. They join data the board already exports with the catalogue's agent files and the spec's Future iterations list.
1. **Hardening (PBI-001, PBI-002, PBI-021, PBI-022)** closes the v1 defects and the answers guard (FR-133), runs the owner-approved store clean-up, and re-baselines the PRD.
2. **Shared derivation (PBI-004)** extracts the exporters' logic into one importable module without changing behaviour, so that the collector and every later feature use the same code (M-8).
3. **Local-first foundation (PBI-003, PBI-019, PBI-005, PBI-006, PBI-007)**, in this order:
   1. record shapes and the SQLite schema;
   2. the collector;
   3. the local server;
   4. the page's data adapter;
   5. the log-on start.
4. **Features on the current board (PBI-008 to PBI-014, PBI-020)** work on the artifact today through the store adapter, and in the local app once PBI-006 lands.
5. **Unraid (PBI-016)** is last and optional (row 6).

**Metadata proposed for every PBI:**
- `pr_required: true` and `merge_allowed_by_agent: false` (the owner merges).
- `change_class: standard`, except PBI-021 and PBI-022, which are `trivial`.
- A PBI that touches two conflict groups is registered in the one that owns most of its work, set to `conflict_risk: High` so that no other PBI in that group starts beside it, and declares the second group in its areas. The coordinator treats it as occupying both groups (review M-3).

### PBI list (proposed)

| ID | Title | Depends on | Conflict group | Conflict risk | Requires spec | Requires ext. review |
|----|-------|------------|----------------|---------------|---------------|----------------------|
| PBI-017 | Agent catalogue tab: every catalogue agent, installed or not, with usage coverage across sessions and projects | [] | exporters | High | false | false |
| PBI-018 | Backlog shows future iterations: a "Later" group of idea cards read from the spec's Future iterations list | [PBI-017] | exporters | High | false | false |
| PBI-001 | Exporter hardening: FR-80–FR-82, FR-84, carried-tab marker, config type checks, refuse an answers collection (FR-133) | [] | exporters | Medium | false | false |
| PBI-002 | Page fixes: FR-83 live-state tile, stale-tab callout, token relabel, design-rule deviations, blank-load investigation (FR-85) | [PBI-001] | page | Low | false | false |
| PBI-021 | Store leftovers clean-up: export the six unused documents to snapshot/, then delete them with the owner's explicit approval | [] | docs | Low | false | true |
| PBI-022 | PRD re-baseline after project-first navigation, with evidence for its demonstration ACs (AC-84, AC-85, AC-92) | [] | docs | Low | false | false |
| PBI-004 | Shared derivation module: extract the exporters' parsing and derivation into an importable module, behaviour unchanged | [PBI-001] | exporters | Medium | false | false |
| PBI-003 | Record shapes and SQLite schema: session, run, project, tab, status and last-refresh records (FR-100–FR-102) | [] | local-app | Low | true | false |
| PBI-019 | Collector: incremental transcript reads into SQLite, mass-delete guard, network-path guard, last-refresh write (FR-86–FR-88, FR-103) | [PBI-003, PBI-004] | local-app | Medium | true | false |
| PBI-005 | Local server: page, data snapshot, live push, 127.0.0.1 binding, Host and Origin checks, network-path guard (FR-92–FR-94, FR-96) | [PBI-003] | local-app | Medium | true | false |
| PBI-006 | Page data-adapter seam: store adapter and local API adapter (FR-97–FR-99) | [PBI-003, PBI-005] | page | Medium | false | false |
| PBI-007 | Log-on start through Task Scheduler and the on-PC deployment end to end (FR-90, FR-91, NFR-17, NFR-21) | [PBI-019, PBI-005, PBI-006] | local-app | Low | false | true |
| PBI-008 | Stale-board warning: refresher last-refresh record and "data as of" header (feature 1, FR-103–FR-105) | [PBI-003] | page | High | false | false |
| PBI-009 | "Waiting on you" panel: detectors for pending questions, idle-after-asking and permission refusals (feature 2, FR-106–FR-110) | [PBI-001] | exporters | High | true | false |
| PBI-010 | Work-item status derived from runs, shown beside the hand-kept state during a shadow period (feature 4, FR-113) | [PBI-001] | exporters | Medium | true | true |
| PBI-011 | Review findings ledger (feature 3, FR-111, FR-112) | [PBI-001] | exporters | High | false | false |
| PBI-012 | Test and coverage trend, cost per work item and per agent type (features 5 and 7, FR-114–FR-116, FR-119, FR-120) | [PBI-001] | exporters | High | false | false |
| PBI-013 | Usage limit forecast (feature 6, FR-117, FR-118) | [] | page | Low | false | false |
| PBI-014 | Run detail (feature 8, FR-121) | [PBI-003, PBI-011] | page | High | false | false |
| PBI-020 | Timeline view (feature 9, FR-101, FR-122–FR-124) | [PBI-003] | page | High | true | false |
| PBI-016 | Unraid deployment: ingest endpoint with a secret from the environment, rejecting answers, and a container definition (FR-89, FR-134, AC-71, AC-72) | [PBI-005, PBI-007] | local-app | Low | false | true |

### Future iterations (not planned)

These are ideas the owner has recorded for after this iteration. They are not PBIs and carry no
metadata. PBI-018 shows them on the Backlog tab as a separate "Later" group.

- **Answering assumptions from the board** (Accept / Override plus a note, recorded with provenance): the former PBI-015, deferred by the owner on 2026-09-11 (row 5). The guards that stop agents writing answers are already in this plan (G-6).
- **Phone notifications**: a review returns NO-GO, a run is cut off, the build goes idle, a session is waiting on the owner (brief "Future iteration"; PRD S-29).
- **Hosting on Azure** (Static Web Apps, Functions, a database, Entra ID) and the **hosted API adapter** (PRD S-27, S-28, D-17).
- **An archive** of sessions and runs older than 7 days (PRD S-30, D-15).
- **Continuous integration** running both test suites (PRD S-16).
- **Using answers for plan approval** and the acceptance of review conditions (PRD S-31).
- **Skills and other marketplaces** in the agent catalogue tab (row 19).

### Allowed and blocked areas (per PBI)

Every page PBI must meet the design rules for new views (PRD NFR-22). Every PBI may update
`CLAUDE.md` and `README.md` for its own procedures (a declared `docs` touch).

- **PBI-017**: allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`, `board.config.json`, `exporters/board_config.py`, `CLAUDE.md`, `README.md`; blocked `local/**`. Reads the catalogue under `~/.claude/plugins` and never writes it. Second group: `page`.
- **PBI-018**: allowed `exporters/export_board.py`, `tests/test_export_board.py`, `site/**`, `tests/page.test.mjs`, `CLAUDE.md`; blocked `local/**`. Second group: `page`.
- **PBI-001**: allowed `exporters/**`, `tests/test_*.py`, `CLAUDE.md`; blocked `site/**`, `local/**`. Also adds the C-16 rule to `CLAUDE.md`: no agent writes answers or calls an answers endpoint.
- **PBI-002**: allowed `site/**`, `tests/page.test.mjs`; blocked `exporters/**`, `local/**`.
- **PBI-021**: allowed `snapshot/**` and the store operations named in its PBI file. Preconditions:
  1. the published artifact has been read and confirmed to be the project-first version;
  2. `tabs/usage` and the five retired `tabs/*` are exported to `snapshot/` first;
  3. the owner approves the named delete batch in chat.
- **PBI-022**: allowed `docs/prd/**`, `docs/backlog/**`.
- **PBI-004**: allowed `exporters/**`, `tests/test_*.py`; blocked `site/**`, `local/**`. No behaviour change: the existing suites stay green unchanged.
- **PBI-003**: allowed `local/records*`, `local/schema*`, `local/tests/**`; blocked `site/**`, `exporters/**`. Defines the run record's start and end fields (FR-101), which PBI-020 fills.
- **PBI-019**: allowed `local/collector*`, `local/db*`, `local/tests/**`, `board.config.json`, `exporters/board_config.py` (the database path key); blocked `site/**`. Its spec covers:
  - WAL mode;
  - change signalling for the server (`PRAGMA data_version` polling);
  - a mass-delete guard equivalent to FR-49;
  - age-only pruning;
  - the network-path guard (FR-96) applied in the collector too;
  - the collector's half of the last-refresh write (FR-103).
- **PBI-005**: allowed `local/server*`, `local/tests/**`, `board.config.json`, `exporters/board_config.py` (the port key); blocked `exporters/**` (other files), `site/**`. Its spec covers:
  - 127.0.0.1 binding (NFR-19);
  - a Host-header allow-list, an Origin check on every non-GET request, and no CORS (row 24);
  - the network-path guard (FR-96, NFR-20);
  - live push within the freshness target (NFR-18, AC-68);
  - wrapping the content-only page (PRD C-8).
- **PBI-006**: allowed `site/**`, `tests/page.test.mjs`; blocked `exporters/**`, `local/**`.
- **PBI-007**: allowed `local/deploy/**`, `local/tests/**`, `README.md`, `CLAUDE.md`; blocked `site/**`, `exporters/**`. It registers a Task Scheduler task, a persistent change to the owner's system, so the owner approves it or runs the documented script. Owns NFR-17 and AC-70.
- **PBI-008**: allowed `exporters/refresh.py`, `tests/test_refresh.py`, `site/**`, `tests/page.test.mjs`; blocked `local/**` (the collector's write is PBI-019's). Second group: `exporters`.
- **PBI-009**: allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`. Its spec confirms the transcript record types against real transcripts before any detector is built (row 10). Second group: `page`.
- **PBI-010**: allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`, `projects/**` (read and annotate only; never delete a data file). Second groups: `config`, `page`. Its spec defines:
  - how derived state reaches the Backlog tab, given that `refresh.py` runs `export_board.py` before `export_sessions.py`;
  - a shadow period showing derived and hand-kept state side by side, with differences flagged;
  - hand-kept `review`, `open` and `commit` staying as overrides (row 15).
- **PBI-011, PBI-012**: allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`. Second group: `page`.
- **PBI-013**: allowed `site/**`, `tests/page.test.mjs` only. It reads the limit reset times the session docs already carry (`usage.limits[].resetsAt`).
- **PBI-014**: allowed `site/**`, `tests/page.test.mjs`, `exporters/**`, `tests/test_*.py`. Second group: `exporters`.
- **PBI-020**: allowed `site/**`, `tests/page.test.mjs`, `exporters/**`, `tests/test_*.py` (run start and end times in the store docs). Second group: `exporters`.
- **PBI-016**: allowed `local/server*`, `local/deploy/**`, `local/tests/**`, `README.md`; blocked `site/**`.
  - The ingest secret is read from an environment variable or a git-ignored file, never from `board.config.json`.
  - The ingest endpoint rejects answer records (FR-134, AC-88).
  - No answers endpoint exists on the LAN.

### Sequencing notes

- **First, alone:** PBI-017, at the owner's request; nothing else runs beside it. **Second, alone:** PBI-018.
- **Any time, owner-driven:** PBI-021 (the store clean-up, when the owner approves the batch) and PBI-022 (docs). Neither shares an area with the code PBIs.
- **Then in parallel:** PBI-001 (`exporters`), PBI-003 (`local-app`) and PBI-013 (`page`) share no area.
- **After PBI-001:**
  - PBI-002 and PBI-004 become eligible.
  - Then PBI-009 to PBI-012 become eligible. Each is High in its group, so they run one at a time.
- **After PBI-003:** PBI-005, PBI-008 and PBI-020.
- **Critical path to "no Claude session needed":** PBI-001 → PBI-004 → PBI-019, and PBI-003 → PBI-005 → PBI-006, joining at PBI-007.
- **The derivation rule (M-8).** Features 2 to 7 are built in the shared module under `exporters/`. The collector imports them. Whichever of PBI-019 and a feature PBI lands second extends the AC-64 equivalence fixture to the new fields.
- **Owner go-ahead before implementation** (`requires_external_review: true`):
  - PBI-021 (a store delete);
  - PBI-007 (a Task Scheduler task);
  - PBI-010 (changes the build session's workflow);
  - PBI-016 (LAN exposure; optional, row 6).

---

## Assumptions & open questions

**Rows the human must confirm or correct at the plan gate:** none (the owner confirmed every row on 2026-09-11; rows 7, 15 and 24 after the review).

| # | Question / ambiguity | Resolution | Status | Source / chosen default | Impact if wrong |
|---|----------------------|-----------|--------|-------------------------|-----------------|
| 1 | Idle refresh cadence and the two token figures (PRD A-5, A-6) | Keep the 10-minute every-tick loop until the local app replaces the refresher. Dispatch keeps `subagent_tokens`, relabelled "reported tokens" in PBI-002, and cost per work item uses effective usage | CONFIRMED | Owner, 2026-09-11 (accepted the defaults) | Low — up to 144 small writes a day until PBI-007 |
| 2 | Is the tab-bar overflow defect (PRD FR-125–FR-128, A-24) still open? | No: the tab bar wraps, so no tab is clipped | RESOLVED | `site/index.html:58` (`.tabs` flex-wrap); commit `2742ca6` message | Low |
| 3 | Snapshot of build data in the public repo (PRD A-8) | The repo is made private on GitHub; `snapshot/` stays | CONFIRMED | Owner, 2026-09-11: "Make the repo private" (done the same day) | Medium — git history before the switch was public |
| 4 | Deleting the store leftovers (PRD A-9, D-11) | A separate owner-run PBI-021, gated by owner approval, with preconditions: the page confirmed project-first, and the six documents exported to `snapshot/` first | CONFIRMED | Owner, 2026-09-11 (accepted); mechanism tightened by review H-2 | Low — six unused documents stay until then |
| 5 | Adopt the answer write path (PRD A-25, C-17) | Not now. The former PBI-015 moves to Future iterations; answers stay in chat. The guards stay: FR-133 in PBI-001, FR-134 in PBI-016, and the C-16 rule in `CLAUDE.md` | CONFIRMED | Owner, 2026-09-11: "Not now" | **High** — reversing later needs an ADR and the deferred PBI |
| 6 | Deployment target (PRD A-26) | On-PC first (PBI-007). Unraid (PBI-016) is last and optional, built only when the owner says so | CONFIRMED | Owner, 2026-09-11 | Medium |
| 7 | Unraid network exposure and authentication (PRD A-27) | Serve the page on the LAN without login. The ingest endpoint requires a shared secret, read from an environment variable or a git-ignored file, never from `board.config.json`. There is no answers endpoint | CONFIRMED | Owner, 2026-09-11 (after the review): "Yes, that's fine" | Medium — any LAN device can read the board |
| 8 | Local app technology and switch-over (PRD A-29) | Python stdlib only under `local/`: `sqlite3` (WAL mode), `http.server` (threaded), Server-Sent Events for live push, default port 8765. Record shapes and the schema are in PBI-003. The v1 artifact and refresher keep running until the owner retires them. Recorded as ADR-0001 | CONFIRMED | Owner, 2026-09-11 (accepted); ADR-0001 | Medium |
| 9 | Answer provenance on the local server (PRD A-28) | Not applicable in this plan: no answers endpoint is built (row 5) | RESOLVED | Row 5 | Low |
| 10 | "Waiting on you" detection signals (PRD A-30) | PBI-009's spec confirms the transcript record types against real transcripts before any detector is built | CONFIRMED | Owner, 2026-09-11 (accepted) | Medium |
| 11 | Derivation rules for features 3–7 and 9 (PRD A-31–A-35) | The PRD defaults as written | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 12 | Retention, record keys and plan counts (PRD A-36, A-37, A-39) | The local database keeps the last 7 days plus linked sessions, pruned by age only. Records are keyed by project id plus row or PBI id. The last-refresh record adds one write per tick, and the affected tests are updated | CONFIRMED | Owner, 2026-09-11 (accepted); history of unlinked sessions is lost by design (D-15) | Low |
| 13 | Remedies for open review findings and design deviations (PRD A-11–A-13, A-15, A-16) | The PRD remedies for FR-80–FR-84. Other remedies, from the code-reviewer report of 2026-09-11 on the project-first change (session `9562c312`; not stored in the repo): a `carriedSince` marker shown as a warning; config type checks with exit 2; the refresher's session stays linked to dispatch-board, which is documented. Design fixes: paths and branch names move to the sans face; the brand dot stops using `--human`; the header dot pulses only while an agent runs. FR-85: a time-boxed investigation | CONFIRMED | Owner, 2026-09-11 (accepted); citation fixed after review L-1 | Low |
| 14 | Scope of D-11 against routine refresh deletes (PRD A-10) | D-11 covers leftovers and deletes outside the refresh procedure; routine deletes continue under the mass-delete guard | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 15 | PBI-010 and hand-kept build state | PBI-010 is `requires_spec`. Derived state is shown beside the hand-kept state during a shadow period, with differences flagged. Hand-kept `review`, `open` and `commit` stay as overrides. `projects/*.json` is never deleted. Retiring the hand-kept state is a later owner decision, after the shadow period | CONFIRMED | Owner, 2026-09-11 (after the review): "Yes, side by side first" | Medium — derived state may disagree with the build session's hand-kept view |
| 16 | Acceptance criteria source | Each PBI's criteria are the PRD's ACs for its requirements (AC-57–AC-93, A-18); approving this spec confirms them | CONFIRMED | Owner, 2026-09-11 (accepted) | Medium |
| 17 | Where the backlog-delivery rails go (PRD A-21) | `backlog-delivery.config` in the repo root (hooks off; `worktree_script` unset until a helper exists). BOARD, PBI files and done-log go under `docs/backlog/` at decomposition | RESOLVED | `backlog-delivery.config` | Low |
| 18 | Does only the owner view the board (PRD A-2)? | Yes; redaction beyond first prompts stays out of scope | RESOLVED | Brief decision 12; PRD D-12 | Low |
| 19 | What counts as "the catalogue" for PBI-017 | Every agent in the agent-catalog marketplace: 30 agents in 7 plugins, each marked installed or not (`workflow-agents`, 12 agents, is not installed). Built-in agent types listed separately. Skills out of scope | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 20 | What "coverage" means | Per agent: run count, last run and the projects whose sessions ran it, over the sessions the board exports. A summary of catalogue agents used at least once. The tab follows the picker and adds an all-sessions total | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 21 | Where the tab sits | A new "Agent catalogue" tab after Dispatch, in every view | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 22 | Where the catalogue's agents are defined, and how runs name them | `~/.claude/plugins/marketplaces/agent-catalog/plugins/<plugin>/agents/<name>.md` with `name`/`description` frontmatter; runs record `<plugin>:<name>` | RESOLVED | `…/plugins/engineering-agents/agents/code-writer.md`; `agentType` in `subagents/*.meta.json` | Low |
| 23 | How future iterations appear on the Backlog (PBI-018) | A separate "Later" group of idea cards, below the PBIs, read from this spec's Future iterations list; never counted as work items | CONFIRMED | Owner, 2026-09-11 (accepted) | Low |
| 24 | Local server hardening | Host-header allow-list (`localhost`, `127.0.0.1`). An Origin check on every non-GET request. No CORS headers. The network-path guard runs in both the collector and the server. The server and page need no login on the PC | CONFIRMED | Owner, 2026-09-11 (after the review): "Yes, harden it" | Medium — a malicious web page could otherwise read the board through DNS rebinding |

---

## Plan-gate record

<!-- Filled in after the plan gate passes. Do not proceed to PBI decomposition
     until this section is complete (SPEC §Plan gate). -->

**Reviewed by:** same-vendor subagent with a clean context (Claude Code Plan agent following `pbi-review`)
**Review date:** 2026-09-11 (round 1 on revision 1: CHANGES-REQUIRED, applied in revision 3; round 2 pending)
**Review note path:** docs/backlog/reviews/dispatch-board/plan-gate-review-r1.md

**Human approval:**
> pending

**Approved by:** —
**Approval date:** pending

**Assumptions resolved:**
- Owner, 2026-09-11, via the plan-gate decision prompt:
  - rows 5 ("Not now"), 6 ("On this PC first") and 3 ("Make the repo private");
  - "Accept all defaults" for rows 1, 4, 8, 10, 11, 12, 13, 14, 16, 19, 20, 21, 23.
- Owner, 2026-09-11, after revision 3:
  - row 7: "Yes, that's fine" (LAN read without login; the upload secret outside the repo);
  - row 15: "Yes, side by side first";
  - row 24: "Yes, harden it".
