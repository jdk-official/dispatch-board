---
title: Dispatch board — next iteration (local-first app, features 1–9, answers) and v1 defect fixes
status: draft
spec_version: 6
revision: 1
parent_prd: docs/prd/dispatch-board.md
---

# Solution Spec — Dispatch board: next iteration and v1 defect fixes

<!-- Authored by the planner (pbi-plan) from the PRD at docs/prd/dispatch-board.md, revision 2.
     Must pass the plan gate (independent review + explicit human approval + every ASSUMED row
     confirmed) before any PBI is decomposed from it (SPEC §Gates, plan gate).
     This document becomes the parent authority for every PBI it spawns. -->

**Status: draft, awaiting the plan gate.** The PBI list below is the *proposed* decomposition shown
for review; no PBI file or BOARD entry exists until the owner approves this spec.

**Already delivered, not re-planned here:** v1 (session picker, generated runs, refresher loop) and
project-first navigation (PRD D-18; FR-129, FR-130, FR-135–FR-148), which shipped in commit
`2742ca6` after three review rounds ending in GO. The tab-bar overflow defect (FR-125–FR-128) was
fixed by the same change: the tab bar now wraps (row 2).

---

## Goals

- **G-1** The owner can trust what the board shows: the v1 defects the reviews left open are closed, a carried-over or stale tab is flagged on the page, and config typos fail loudly instead of changing behaviour (PRD O-6, FR-80–FR-85).
- **G-2** The board stays current from log-on onwards with no Claude session open and no Claude usage spent on refreshing, on the owner's PC first and optionally on the Unraid server (PRD O-8, D-16, D-17).
- **G-3** Moving to a host later changes only storage and transport: one set of record shapes and one data adapter in the page (PRD O-9, D-16).
- **G-4** The owner sees at a glance when data is stale and everything that is waiting on them (PRD O-10, features 1–2).
- **G-5** The owner sees each build's progress from its runs alone — findings, work-item state, test trend, cost, run detail, timeline and a usage-limit forecast — with no hand-kept build state (PRD O-11, features 3–9).
- **G-6** The owner can answer plan-gate assumptions from the board, with provenance that keeps agents from ever writing an answer (PRD S-26, C-16, C-17) — only if the owner confirms the answer write path (row 5).

---

## Scope

### In scope

- `exporters/**` — defect fixes FR-80–FR-84, the carried-tab marker and config type checks from review round 4, the last-refresh record (FR-103), and the derivations features 2–7 need (detectors, findings, work-item state, test counts, cost attribution).
- `site/**` — the page defect FR-83 and the design-rule deviations (row 13), the stale-board warning, the "Waiting on you" panel, findings ledger, test trend, cost per work item, usage-limit forecast, run detail, timeline, the data-adapter seam, and the answer UI (conditional on row 5).
- `local/**` — new: record shapes, collector, SQLite local database, local server (page, snapshot, live push, answers endpoint, optional ingest endpoint), Task Scheduler log-on start, and an optional Unraid container definition.
- `projects/**`, `board.config.json` — retiring hand-kept `buildState` once feature 4 derives it, and any new config keys (local server port, database path).
- `docs/adr/**` — one ADR for the answer write path (row 5), and one for the local-first architecture (row 8).
- `CLAUDE.md`, `README.md` — procedures for the local app and the retired pieces.
- One owner-approved store clean-up: delete `tabs/usage` and the five retired `tabs/*` documents (row 4).

### Out of scope

- Re-planning v1 or project-first navigation (delivered, `2742ca6`).
- Hosting on Azure and the hosted API adapter (PRD S-27, S-28); the seam is in scope, the hosted adapter is not.
- Phone notifications (PRD S-29) and an archive older than 7 days (PRD S-30, D-15).
- Continuous integration (PRD S-16) and redacting titles, run labels or agent descriptions (PRD S-17, D-12).
- Using answers to record plan approval or acceptance of review conditions (PRD S-31).
- Hooks in build sessions that report to the board, and hand-written runs (PRD S-11, S-12).
- `C:/Users/jdk/platform-catalogue/**` — the tracked build repo is read, never written.

---

## Key decisions

| Decision | Rationale | Made by | Date |
|----------|-----------|---------|------|
| Plan the next iteration on top of the delivered project-first board; do not re-plan v1 or D-18 | Both are built, reviewed to GO and live (`2742ca6`); the PRD marks D-18 "being built" only because it was written mid-build (PRD A-38) | Planner | 2026-09-11 |
| Local first, hosting later: collector → SQLite → local server → page through one data adapter; record shapes defined once | Owner decision D-16: the board must not depend on a Claude session, and hosting later should only swap storage and transport | Owner (D-16) | 2026-09-11 |
| Unraid is the optional first host; the collector stays on the PC and sends records over the LAN; SQLite never on a network share | Owner decision D-17: transcripts exist only on the PC; SQLite locking over SMB/NFS is unreliable | Owner (D-17) | 2026-09-11 |
| The local app uses the Python standard library only (`sqlite3`, `http.server`, Server-Sent Events for live push) under `local/` | Matches the existing stdlib-only exporters and tests (PRD C-13); no new dependency to audit or install; SSE is one-way, which is all live push needs — confirm at the gate (row 8) | Planner | 2026-09-11 |
| The v1 artifact and its refresher keep running until the owner retires them | Running both is the safe switch-over; retirement is an owner call once the local app has run for a while (row 8) | Planner | 2026-09-11 |
| Code changes go through `engineering-agents:code-writer` (TDD) then `review-agents:code-reviewer` until GO | Owner decision D-9 | Owner (D-9) | 2026-09-10 |
| The answer write path is adopted only through an ADR, with provenance guards that apply whether or not it is adopted | It reverses "the page never writes" (PRD C-17); plan-gate answers must be human (PRD C-16) — confirm at the gate (row 5) | Planner (recommendation) | 2026-09-11 |

---

## Decomposition rationale

The work splits into five tracks. Each PBI names the PRD requirements it delivers; its acceptance
criteria are the PRD's ACs for those requirements, firmed into the PBI file at decomposition.

1. **Hardening (PBI-001, PBI-002)** closes the v1 defects first, because the collector (PBI-004) reuses the exporter logic and would otherwise inherit them (PRD A-12, FR-87).
2. **Local-first foundation (PBI-003 to PBI-007)**: record shapes first (the contract every later piece shares), then the collector and the local server, then the page's data adapter, then the log-on start.
3. **Features on the current board (PBI-008 to PBI-014)**: each works on the artifact today through the store adapter, and in the local app once PBI-006 lands, because both read the same record shapes. Most depend only on PBI-001 or PBI-003.
4. **Answers (PBI-015)** comes after the local server and adapter, and only if row 5 is confirmed.
5. **Unraid (PBI-016)** is last and optional (row 6).

### PBI list (proposed)

| ID | Title | Depends on | Conflict group | Conflict risk | Requires spec | Requires ext. review |
|----|-------|------------|----------------|---------------|---------------|----------------------|
| PBI-001 | Exporter hardening: FR-80–FR-82 and FR-84, carried-tab marker, config type checks, verifier outcome | [] | exporters | Medium | false | false |
| PBI-002 | Page fixes: FR-83 live-state tile, stale-tab callout, design-rule deviations, blank-load investigation (FR-85) | [PBI-001] | page | Low | false | false |
| PBI-003 | Record shapes: session, run, project, tab, status, answer and last-refresh records (FR-100–FR-102) | [] | local-app | Low | true | false |
| PBI-004 | Collector: incremental transcript reads, shared derivation, SQLite local database (FR-86–FR-88) | [PBI-001, PBI-003] | local-app | Medium | true | false |
| PBI-005 | Local server: page, data snapshot, live-push stream, 127.0.0.1 binding, network-path guard (FR-92–FR-94, FR-96) | [PBI-003] | local-app | Medium | false | false |
| PBI-006 | Page data-adapter seam: store adapter and local API adapter (FR-97–FR-99) | [PBI-003, PBI-005] | page | Medium | false | false |
| PBI-007 | Log-on start through Task Scheduler, on-PC deployment end to end (FR-90, FR-91, NFR-21) | [PBI-004, PBI-005, PBI-006] | local-app | Low | false | false |
| PBI-008 | Stale-board warning: last-refresh record and "data as of" header (feature 1, FR-103–FR-105) | [PBI-003] | page | Low | false | false |
| PBI-009 | "Waiting on you" panel: detectors for pending questions, idle-after-asking and permission refusals (feature 2, FR-106–FR-110) | [PBI-003] | exporters | Medium | true | false |
| PBI-010 | Work-item status derived from runs, retiring hand-kept buildState (feature 4, FR-113) | [PBI-001] | exporters | Medium | false | true |
| PBI-011 | Review findings ledger (feature 3, FR-111, FR-112) | [PBI-001] | exporters | Medium | false | false |
| PBI-012 | Test and coverage trend, cost per work item and per agent type (features 5 and 7, FR-114–FR-116, FR-119, FR-120) | [PBI-001] | exporters | Low | false | false |
| PBI-013 | Usage limit forecast (feature 6, FR-117, FR-118) | [] | page | Low | false | false |
| PBI-014 | Run detail and timeline view (features 8 and 9, FR-101, FR-121–FR-124) | [PBI-011] | page | Medium | true | false |
| PBI-015 | Answering assumptions from the board, with the ADR and provenance guards (FR-131–FR-134, NFR-23) | [PBI-005, PBI-006] | page | Medium | true | true |
| PBI-016 | Unraid deployment: ingest endpoint with shared secret and container definition (FR-89, FR-134, AC-71, AC-72) | [PBI-005, PBI-007] | local-app | Low | false | true |

### Allowed and blocked areas (per PBI)

- **PBI-001**: allowed `exporters/**`, `tests/test_*.py`, `CLAUDE.md`; blocked `site/**`, `local/**`.
- **PBI-002**: allowed `site/**`, `tests/page.test.mjs`; blocked `exporters/**`, `local/**`.
- **PBI-003**: allowed `local/records*`, `local/tests/**`, `docs/adr/**`; blocked `site/**`.
- **PBI-004**: allowed `local/collector*`, `local/db*`, `local/tests/**`, `exporters/**` (only to extract shared derivation into an importable module; behaviour unchanged, existing tests green); blocked `site/**`.
- **PBI-005**: allowed `local/server*`, `local/tests/**`; blocked `exporters/**`, `site/**`.
- **PBI-006**: allowed `site/**`, `tests/page.test.mjs`; blocked `exporters/**`, `local/**`.
- **PBI-007**: allowed `local/deploy/**`, `local/tests/**`, `README.md`, `CLAUDE.md`; blocked `site/**`, `exporters/**`.
- **PBI-008**: allowed `exporters/refresh.py`, `tests/test_refresh.py`, `site/**`, `tests/page.test.mjs`, `local/collector*` (declared cross-group touch; runs alone in page and exporters).
- **PBI-009**: allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs` (cross-group touch).
- **PBI-010**: allowed `exporters/**`, `tests/test_*.py`, `projects/**`, `CLAUDE.md`; blocked `site/**`.
- **PBI-011, PBI-012**: allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs` (cross-group touch).
- **PBI-013**: allowed `site/**`, `tests/page.test.mjs`, `exporters/export_sessions.py` (only to expose limit reset times already parsed).
- **PBI-014**: allowed `site/**`, `tests/page.test.mjs`, `exporters/**`, `tests/test_*.py` (run start/end times).
- **PBI-015**: allowed `site/**`, `tests/page.test.mjs`, `local/server*`, `local/tests/**`, `exporters/refresh.py`, `tests/test_refresh.py`, `docs/adr/**`, `CLAUDE.md`.
- **PBI-016**: allowed `local/server*`, `local/deploy/**`, `local/tests/**`, `README.md`; blocked `site/**`.

### Sequencing notes

- **Start in parallel:** PBI-001 (exporters), PBI-003 (local-app) and PBI-013 (page) share no area.
- **After PBI-001:** PBI-002, PBI-010, PBI-011 and PBI-012 become eligible. PBI-010, PBI-011 and PBI-012 share the `exporters` group at Medium or Low risk, so they may run in parallel only if the worker keeps their areas apart; otherwise run them in that order.
- **After PBI-003:** PBI-005, PBI-008 and PBI-009. PBI-004 also needs PBI-001, so the collector reuses the hardened logic.
- **Critical path to "no Claude session needed":** PBI-003 → PBI-005 → PBI-006 → PBI-007, with PBI-004 joining before PBI-007.
- **Late and conditional:** PBI-015 (row 5) and PBI-016 (row 6). Both require the owner's explicit go-ahead before implementation (`requires_external_review: true`).
- **Cross-group PBIs** (PBI-008, PBI-009, PBI-011, PBI-012, PBI-014) touch both `exporters` and `page`; each runs while no other PBI in either group is active.
- **PBI-010 requires external review** because it changes the build session's workflow: the hand-kept `buildState` it retires is edited by another Claude session today.

---

## Assumptions & open questions

**Rows the human must confirm or correct at the plan gate:** 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 (every ASSUMED row). Each row is also listed with its default in the Plan-gate record once confirmed.

| # | Question / ambiguity | Resolution | Status | Source / chosen default | Impact if wrong |
|---|----------------------|-----------|--------|-------------------------|-----------------|
| 1 | Idle refresh cadence and the two token figures (PRD A-5, A-6) | Keep the 10-minute every-tick loop until the local app replaces the refresher; Dispatch keeps `subagent_tokens` but labels them "reported tokens", while cost per work item uses effective usage | ASSUMED | Default chosen by the planner; both PRD rows are "decision pending" | Low — up to 144 small writes a day until PBI-007; two differently labelled token figures remain |
| 2 | Is the tab-bar overflow defect (PRD FR-125–FR-128, A-24) still open? | No: the tab bar now wraps, so no tab is clipped | RESOLVED | `site/index.html` `.tabs` rule (commit `2742ca6`); `CLAUDE.md` "tab bar wraps" | Low |
| 3 | Snapshot of build data in the public repo (PRD A-8) | Keep `snapshot/` as is; only the owner views the board, and the pre-publish secret scan found nothing | ASSUMED | Default chosen by the planner | Medium — build runs, assumptions and decisions stay publicly readable in git history |
| 4 | Deleting the store leftovers (PRD A-9, D-11) | Delete `tabs/usage` and the five retired `tabs/*` in one batch inside PBI-001, only after the owner approves that batch explicitly | ASSUMED | Default chosen by the planner; the permission check blocked an earlier delete | Low — six unused documents otherwise stay in the store |
| 5 | Adopt the answer write path, and how answers reach the build repo (PRD A-25, C-17) | Adopt it through an ADR, with the provenance guards (refresh.py refuses `answers`; the ingest endpoint rejects them; no agent writes answers). The build session reads `answers/*` at each plan gate; no importer | ASSUMED | Recommended by the PRD (A-25); transport chosen by the planner | **High** — it reverses a design rule and touches plan-gate provenance; if not adopted, PBI-015 is dropped |
| 6 | Deployment target (PRD A-26) | On-PC first (PBI-007). Unraid (PBI-016) stays last and optional, built only when the owner says so | ASSUMED | Default chosen by the planner | Medium — building Unraid unused wastes one PBI; skipping it delays the hosted path |
| 7 | Unraid network exposure and authentication (PRD A-27) | Serve on the LAN without login; the ingest endpoint requires a shared secret held by the collector and the server | ASSUMED | PRD A-27 default | Medium — any LAN device can read the board |
| 8 | Local app technology and switch-over (PRD A-29) | Python stdlib only under `local/`: `sqlite3`, `http.server` (threaded), Server-Sent Events for live push, default port 8765. The record shapes live in one module plus a JSON description the page reads. An ADR records the local-first architecture. The v1 artifact and refresher keep running until the owner retires them | ASSUMED | Default chosen by the planner (Key decisions) | Medium — a framework choice later means reworking PBI-004 to PBI-006 |
| 9 | Answer provenance on the local server (PRD A-28) | The page served locally holds a per-install key issued by the server at first visit; agents are forbidden by `CLAUDE.md` from calling the answers endpoint. Proof of human authorship is not claimed | ASSUMED | Planner default, strengthening PRD A-28 | Medium — an agent that ignores its instructions and reads the key could forge an answer |
| 10 | "Waiting on you" detection signals (PRD A-30) | PBI-009 is `requires_spec: true`: its spec confirms the transcript record types (question tool call with no later owner message, a permission-denied record) against real transcripts before any detector is built | ASSUMED | Planner default | Medium — the panel misses items or lists false ones |
| 11 | Derivation rules for features 3–7 and 9 (PRD A-31–A-35) | Take the PRD defaults as written: rounds per PBI id per project; latest code-reviewer verdict mapping; first "N tests" and "coverage N%"; equal cost split across PBI ids; forecast from last reset to last hit; stale at 20 minutes; idle gap longer than the running window | ASSUMED | PRD A-31–A-35 defaults | Low — reworded agent reports give missing or wrong figures; each rule is one function to change |
| 12 | Retention, record keys and plan counts (PRD A-36, A-37, A-39) | The local database keeps what the page shows (last 7 days plus linked sessions); records are keyed by project id plus row or PBI id; the last-refresh record adds one write per tick, and the affected tests are updated | ASSUMED | PRD A-36, A-37, A-39 defaults | Low — history for unlinked sessions is lost after 7 days |
| 13 | Remedies for the open review LOW findings and design deviations (PRD A-11–A-13, A-15, A-16; review round 4) | The PRD remedies for FR-80–FR-84. Carried tabs get a `carriedSince` marker, shown as a warning callout. Config values are type-checked, with exit 2. The refresher's own session stays linked to dispatch-board, and the docs say so. Paths and branch names move to the sans face. The brand dot stops using `--human`. The header dot pulses only while an agent runs. FR-85 gets a time-boxed investigation: if it isn't reproducible, it closes with that evidence | ASSUMED | Planner defaults over PRD A-11–A-16 and review CR4-01–CR4-03 | Low — each is a small, reversible change |
| 14 | Scope of D-11 against routine refresh deletes (PRD A-10) | D-11 covers leftovers and deletes outside the refresh procedure; routine deletes of previously pushed documents continue under the mass-delete guard | ASSUMED | PRD A-10 default | Low — otherwise every deleting tick waits for the owner |
| 15 | PBI-010 retires hand-kept build state | When derived state ships, `projects/platform-catalogue.json` `buildState` is no longer read. The build session is told, and its `boardNote` and `notWorkedOut` stay | ASSUMED | Planner default | Medium — derived state may read differently from what the build session wrote by hand (PRD A-32) |
| 16 | Acceptance criteria source | Each PBI's criteria are the PRD's ACs for its requirements (AC-57–AC-93, including those the PRD's author derived, A-18); the owner confirming this spec confirms them | ASSUMED | Planner default | Medium — an AC the owner reads differently gates the wrong behaviour |
| 17 | Where does the planner put the backlog-delivery rails (PRD A-21)? | `backlog-delivery.config` in the repo root, written for this plan (hooks off); BOARD, PBI files and done-log under `docs/backlog/` at decomposition | RESOLVED | `backlog-delivery.config` (this planning pass) | Low |
| 18 | Does only the owner view the board (PRD A-2)? | Yes; redaction beyond first prompts stays out of scope | RESOLVED | Brief decision 12; PRD D-12 | Low |

---

## Plan-gate record

<!-- Filled in after the plan gate passes. Do not proceed to PBI decomposition
     until this section is complete (SPEC §Plan gate). -->

**Reviewed by:** pending
**Review date:** pending
**Review note path:** pending

**Human approval:**
> pending

**Approved by:** —
**Approval date:** pending

**Assumptions resolved:**
- pending
