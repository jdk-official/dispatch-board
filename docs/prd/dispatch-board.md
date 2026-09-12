# Dispatch board (current tree as baseline, plus next iteration): Product Requirements

**Status:** plan-ready draft, **revision 3**. Self-graded only. The quality verdict belongs to the caller's gate, not to this document.
**Date:** 2026-09-11
**Baseline:** Part A of section 4 describes the **current tree**: v1, plus project-first navigation (D-18, shipped in commit `2742ca6`), plus the Agent catalogue tab (PBI-017, D-19: built, reviewed and live on the board, with PR #1 awaiting the owner's merge). Part B is the approved next iteration, which is not built. Nothing was run to produce this document. Test names were found by searching `tests/`, and the page behaviour by reading `site/index.html`.
**Sources, in priority order:**
- `docs/backlog/specs/dispatch-board.md` (the approved solution spec, revision 5): its Assumptions & open questions ledger (rows 1–24, all confirmed or resolved), Key decisions, Plan-gate record, Future iterations and criteria AC-C1–AC-C7, AC-L1–AC-L3, AC-S1–AC-S3 and AC-R1–AC-R3. "Row *n*" in this document always means row *n* of that ledger.
- `docs/brief/raw-notes.md` (the brief, including decisions 19 and 20). Brief citations name a stable anchor: a numbered decision ("brief decision *n*"), a numbered item under the brief's heading "Candidate features for the next iteration" ("brief candidate feature *n*"), or a section heading and item. Line numbers in parentheses locate the anchor in the current brief; where they disagree, the anchor governs.
- `docs/backlog/pbi/PBI-022.md` (this work item).
- The orchestrator's facts, verified on 2026-09-11.
- `docs/adr/0001-local-first-architecture.md` (accepted).
- `CLAUDE.md`, `README.md`, `docs/backlog/BOARD.md` and `board.config.json`.
- The code, searched or read in part: `site/index.html`, the `tests/` files (`test_export_sessions.py`, `test_export_board.py`, `test_export_catalogue.py`, `test_refresh.py`, `page.test.mjs`).

Every listed input was readable.

### Change log from revision 2

- **Re-baselined (AC-R1).** Part A now describes the current tree.
  - The project-first requirements (FR-129, FR-130, FR-135 to FR-148) and the tab-bar requirements (FR-125 to FR-128, met by row 2) moved into Part A. Every id is kept.
  - Part A requirements that D-18 replaced are marked **Superseded**, kept in place, and point to their replacement. The supersession table is resolved.
  - Test citations were renamed to the current tests. The counts in AC-34, NFR-16 and AC-47 were updated.
- **Decisions recorded (AC-R2).**
  - D-19 and D-20 are brief decisions 19 and 20.
  - D-21 makes the repository private and **supersedes D-1**.
  - D-22 is row 5 (answers from the board deferred), D-23 is row 6 (on-PC first, Unraid last and optional) and D-24 is row 8 (the local-app technology, ADR-0001).
  - D-25 is the plan approval: all defaults accepted, and rows 7, 15 and 24 as recommended.
  - D-26 is the owner's standing build instruction.
- **Settled by the ledger:** 28 A-rows in the section 8 table, each citing the ledger row that settles it. The ledger names 27 of them; A-20 is named by no row, and this document maps it to row 15. A-24, which row 2 names, is listed with the rows resolved earlier instead.
- **Closed by this revision:** A-38, the moving baseline.
- **Added:**
  - FR-149 to FR-192;
  - NFR-24;
  - C-20 to C-23;
  - AC-94 to AC-128;
  - A-40 to A-48;
  - O-13 and O-14;
  - S-32 to S-40.
- **Deferred by D-22** (kept, not in force): FR-95, FR-131, FR-132, NFR-23, AC-87, and the answer record of FR-100.
- **Amended in place, ids unchanged:**
  - Part A: FR-3, FR-4, FR-6, FR-38, FR-40, FR-44, FR-45, FR-47 to FR-51, FR-70 to FR-76, FR-79, FR-82, FR-83 and FR-85;
  - Part B: FR-100, FR-113, FR-129, FR-140, FR-143 and FR-147;
  - NFR-4, NFR-10 to NFR-12, NFR-16, NFR-19 and NFR-22;
  - C-9, C-12, C-16 and C-17;
  - AC-29, AC-34, AC-35, AC-42 to AC-45, AC-47, AC-59, AC-60, AC-85 and AC-93.

### Glossary (each term is used in exactly one sense throughout this document)

- **Page**: `site/index.html`, published as the claude.ai artifact "Live Dispatch Board" and private to the owner. In the next iteration the local server also serves it.
- **Store**: the artifact's document store. Its current collections are `sessions/<id>`, `runs/<agentId>`, `projects/<projectId>`, `projectTabs/<projectId>.<tab>`, `catalogue/index`, `meta/status` (platform-catalogue's status document) and `status/<projectId>` (every other project's). **Retired leftovers**: `tabs/usage`, and `tabs/{spec,assumptions,decisions,backlog,git}` from before D-18 (six documents in all).
- **Session exporter**: `exporters/export_sessions.py`. **Board exporter**: `exporters/export_board.py`. **Catalogue exporter**: `exporters/export_catalogue.py`. **Refresh script**: `exporters/refresh.py`.
- **Refresher**: the separate Claude Code session that runs the v1 refresh loop. **Tick**: one pass of that loop.
- **Session**: one Claude Code conversation, identified by its session id and recorded as a **main transcript** (`<projectsRoot>/<folder>/<id>.jsonl`) plus one **agent transcript** per subagent (`<id>/subagents/agent-<agentId>.jsonl`, with a `.meta.json`).
- **Project**: an entry under `projects` in `board.config.json`, with `id`, `name`, `repoPath`, `branch`, `sessions`, `statusDoc` and `docs`. The two projects are platform-catalogue and dispatch-board. **Linked session**: a session listed in a project's `sessions`. **Unlinked session**: any other exported session. **Tracked build repo**: a project's `repoPath`.
- **Project tabs**: Spec, Assumptions, Decisions, Backlog and GitHub details.
- **View**: what the project picker selects, either one project or **"Other sessions"** (the unlinked sessions). **Session filter**: the second picker. In a project view it offers "All sessions" or one linked session. In "Other sessions" it chooses one unlinked session. **Current view**: the selected view, narrowed by the session filter.
- **Run**: one agent dispatched by a session, stored as one `runs/<agentId>` document.
- **Lane**: a run's agent role. The **review lanes** are `plan`, `cr` (code-reviewer) and `ver` (verifier). The **build lanes** are `req` (requirements-author), `cw` (code-writer) and `tw` (test-writer). The others are `orch`, `human` and `other`.
- **Kind**: a run's state, one of `running`, `done`, `go`, `changes`, `nogo` or `killed`. **Verdict**: the short text shown with a run, usually the agent's own **verdict token** (for example `GO-WITH-NOTES`, `NOT-DONE`).
- **Finish**: the record that a run ended, either a `<task-notification>` in the main transcript or an inline foreground result.
- **Session window**: `sessions.days` (7 days, D-5 and D-15). **Running window**: `runs.runningWindowMinutes` (10 minutes).
- **Effective usage**: tokens weighted by relative cost: input × 1, cache read × 0.1, cache write × 2, output × 5. It is a comparison figure, not a price.
- **Pushed state**: `out/.pushed.json`, which records what the store holds. **Pending plan**: `out/.pending.json`, which records the last printed set of writes.
- **Managed collections**: the collections the refresh script writes and deletes in: `runs`, `sessions`, `projects`, `projectTabs` and `catalogue`.
- **Mass-delete guard**: the refresh script's refusal of a plan that would delete too much (FR-49).
- **`write_db`**: the Artifact tool operation that writes store documents, used with `db_op: "batch"`.
- **Work item**: a backlog item of a project, identified by a PBI id (for example `PBI-001`). **Hand-kept build state**: `buildState` in `projects/<projectId>.json`, edited by hand.
- **Catalogue**: the agents (`plugins/<plugin>/agents/<name>.md`) and skills (`plugins/<plugin>/skills/<name>/SKILL.md`) in the agent-catalog marketplace clone. **Entry**: one agent or skill, identified as `<plugin>:<name>`. **Skill use**: a `Skill` tool call or a typed `/<plugin>:<skill>` command in a main transcript.
- **Ledger row *n***: row *n* of the approved spec's Assumptions & open questions ledger.

Next-iteration terms (none of these is built):

- **Collector**: a program on the owner's PC that reuses the exporters' logic through a shared derivation module, reads transcripts incrementally and produces records. It needs no Claude session.
- **Local database**: the SQLite database that holds the records (WAL mode, D-24).
- **Local server**: a small web server (Python `http.server`, D-24) that serves the page, a **data snapshot** (all current records in one response) and a **live-push stream** (Server-Sent Events). In the Unraid deployment it also has an **ingest endpoint** that accepts records from the collector. It has no answers endpoint while D-22 stands.
- **On-PC deployment**: the collector, local server and local database all run on the owner's PC, and the local server listens on 127.0.0.1 only. **Unraid deployment**: the local server and local database run as a container on the owner's Unraid server, and the collector stays on the PC and sends records over the LAN.
- **Record shapes**: the one set of definitions for session, run, project, tab, status, last-refresh and catalogue records, shared by the collector, the local server and every data adapter.
- **Data adapter**: the one interface through which the page obtains data. The **store adapter** reads the Store. The **local API adapter** reads the local server. A **hosted API adapter** is a later option.
- **Last-refresh time**: the time of the last successful refresh (a collector write, or a refresher tick that wrote to the Store), held in a status record separate from `meta/status` and `status/<projectId>`.
- **Shadow period**: the time during which derived work-item state is shown beside the hand-kept build state (row 15).
- **Later item**: an idea card read from a spec's "Future iterations (not planned)" list (D-20).
- **Answer** (deferred by D-22): the owner's response to one assumption row, *Accept* or *Override* plus a note.

---

## 1. Intended outcomes

**Current tree (baseline):**

- **O-1** The owner can see, for any Claude Code session active on this computer in the last 7 days, which agents ran, what each returned, and the tokens and minutes each used, without opening a transcript.
- **O-2** For each tracked project, the owner sees the project's spec, the assumptions awaiting a human, decisions, backlog and repository state next to the agent activity.
- **O-3** The owner sees Claude usage per project or per session: effective usage, where it went, how it was spread over time and models, and when a usage limit refused work.
- **O-4** The board stays current without any session having to report to it. Everything is derived from what sessions leave on disk.
- **O-5** Nothing the owner has not chosen to publish is published by default. First prompts are withheld, excluded sessions are never read, and obvious secrets are redacted when prompts are published.
- **O-6** One bad file or a broken discovery cannot freeze or wipe the board. Failures are isolated per agent, per session and per project, and mass deletes are refused.
- **O-7** The page reads as a professional dashboard that follows the owner's stated design preferences.
- **O-12** The owner picks a project and sees its spec, assumptions, decisions, backlog and repository, with Dispatch and usage combined over every session building it. Sessions linked to no project stay viewable under "Other sessions". *(D-18, shipped.)*
- **O-13** The owner sees every agent and skill in the agent catalogue, grouped by what it is for, and how much of it the projects use: uses per entry, when it was last used, which projects used it, and what has never been used. *(D-19; spec G-7. Built, PR #1 awaiting merge.)*

**Next iteration (not built):**

- **O-8** The board stays current from log-on onwards with no Claude session open and no Claude usage spent on refreshing, on the owner's PC first (D-16, D-23).
- **O-9** Moving the board to a host later changes only storage and transport, not the page or the record shapes (D-16, D-17, D-24).
- **O-10** The owner sees at a glance when the board's data is stale and everything, across all sessions, that is waiting on them (features 1–2).
- **O-11** The owner sees each build's progress from its runs: review findings, work-item state, test trend, cost per work item, run details, a timeline and a usage-limit forecast (features 3–9). During the shadow period the derived state is shown beside the hand-kept state (row 15).
- **O-14** The owner sees the ideas recorded for later iterations on the Backlog, apart from the planned work items (D-20).

## 2. Scope

### In scope

Current tree (baseline):

- **S-1** The page: a read-only, live-subscribed dashboard with a project picker, a session filter and "Other sessions". It has nine tabs: Overview, Spec, Assumptions, Decisions, Backlog, GitHub, Dispatch, Agent catalogue and Claude usage.
- **S-2** The session exporter: session discovery, session and project documents, run rows (with `agentType` and `start`), usage, skill use, privacy settings, a parse cache and failure isolation.
- **S-3** The board exporter, per project.
- **S-4** The refresh script: running the three exporters, diffing against the last push over the managed collections, batching, the mass-delete guard, per-project status documents, and commit.
- **S-5** The refresher loop procedure in `CLAUDE.md`, at the 10-minute cadence (D-14; kept until the local app replaces it, row 1).
- **S-6** The settings in `board.config.json` that the above read.
- **S-7** The automated test suites: `python -m unittest discover -s tests` and `node tests/page.test.mjs`.
- **S-8** Six requirements the current tree does not yet meet (FR-80 to FR-85), recorded as open defects. Their remedies are settled by row 13 and planned in PBI-001 and PBI-002.
- **S-14** Project-first navigation for every project listed in `board.config.json` (D-18). **Shipped** in commit `2742ca6`, and now part of the baseline.
- **S-25** The tab-bar overflow fix (FR-125 to FR-128). **Met**: the tab bar wraps (row 2).
- **S-32** The Agent catalogue tab and the catalogue exporter (PBI-017, D-19). Built and reviewed, live on the board, with PR #1 awaiting the owner's merge.

Next iteration (not built; approved plan):

- **S-20** The local-first app (D-16, D-24): collector, local database, local server, and a log-on start through Task Scheduler, on the owner's PC first (D-23). It includes the server hardening of rows 7 and 24.
- **S-21** The data-adapter seam in the page, with the store adapter and the local API adapter built (D-16).
- **S-22** One set of record shapes for sessions, runs, projects, tabs, status, last-refresh and catalogue records (D-16; projects for D-18, row 12; the catalogue for D-19). The answer record is deferred (D-22).
- **S-23** An optional Unraid deployment of the local server and local database as a container, fed by the collector over the LAN (D-17). It is built last, and only when the owner says so (D-23).
- **S-24** Candidate features 1–9 (the brief's "Candidate features for the next iteration", lines 173–198): stale-board warning, "Waiting on you" panel, review findings ledger, work-item status derived from runs, test and coverage trend, usage limit forecast, cost per work item, run detail, timeline view.
- **S-26** The provenance guards only: C-16, FR-133 and FR-134. The answer write path is out of scope (S-37, D-22).
- **S-33** The Backlog "Later" group of idea cards, read from a spec's Future iterations list (PBI-018, D-20).
- **S-34** The store leftovers clean-up (PBI-021, row 4). The six retired documents are exported to `snapshot/tabs/` first, and then deleted only with the owner's explicit approval (AC-S1 to AC-S3).
- **S-35** The derived-state shadow period (PBI-010, row 15).
- **S-36** Hardening follow-ups settled by rows 1 and 13: the carried-tab marker, the "reported tokens" relabel, the config type checks, and the design-rule fixes (PBI-001, PBI-002).

### Out of scope

- **S-9** Any write from the page. The answer path that would have introduced one is deferred (D-22).
- **S-10** Moving off the artifact to GitHub Pages plus an external database. This was rejected for now (D-3) and cannot be done while the page is an artifact (C-2).
- **S-11** Hooks in the build session that report to the board (rejected for now, D-3).
- **S-12** Hand-written `runs` rows (D-4).
- **S-13** Deleting store leftovers other than through PBI-021's owner-approved batch (D-11, row 4).
- **S-15** Making the v1 refresher durable, for example as a scheduled Claude task. Durability comes instead from the log-on start of the next iteration (D-16, S-20).
- **S-16** Continuous integration (a future iteration in the spec).
- **S-17** Redaction of session titles, run labels, agent descriptions and skill ids. It is not a priority, because only the owner views the board (D-12, row 18).
- **S-18** A plan usage meter. Transcripts record only the moments a limit refused a request. The usage limit forecast (feature 6) is an estimate, not a meter.
- **S-19** Decomposing this document into backlog items, and any code or tests. Those are downstream of this document.
- **S-27** Hosting on Azure (Static Web Apps, Functions, a database, Entra ID). It is a future iteration (D-17).
- **S-28** Building the hosted API adapter. The seam is in scope (S-21); the hosted adapter is a future iteration.
- **S-29** Phone notifications (a future iteration, deferred by the owner on 2026-09-11).
- **S-30** An archive of sessions or runs older than 7 days (D-15; a future iteration).
- **S-31** Using the answer mechanism to record plan approval or the acceptance of review conditions (a future iteration).
- **S-37** Answering assumptions from the board, including the answers endpoint, FR-95, FR-131, FR-132, NFR-23, AC-87 and the answer record. The owner deferred it: "Not now" (D-22, row 5). It is a future iteration.
- **S-38** Agents and skills from marketplaces other than agent-catalog in the catalogue tab (a future iteration; row 19).
- **S-39** Retiring the hand-kept build state (a later owner decision; row 15).
- **S-40** Retiring the v1 artifact and its refresher (a later owner decision; row 8, ADR-0001).

## 3. Decisions already made

Only the owner's recorded decisions are listed, each with its source.
- **D-1 to D-11** sit under the brief's heading "Decisions the owner made (with reasons given)".
- **D-12 to D-15** sit under "Owner's answers (2026-09-11)".
- **D-16 to D-20** sit under "Direction for the next iteration" and the numbered decisions after it. The brief numbers D-12 to D-20 as 12 to 20.
- **D-21 to D-25** are the owner's answers and approval recorded in the approved spec's Key decisions and Plan-gate record.
- **D-26** is the owner's standing instruction, as verified by the orchestrator on 2026-09-11.

Lines that are decision-adjacent but carry no such marker are listed after the table.

| ID | Decision | Reason recorded | Source |
|---|---|---|---|
| **D-1** | The code lives in a **public** GitHub repository, `jdk-official/dispatch-board` (2026-09-10). **Superseded by D-21 (2026-09-11): the repository is now private.** | The owner chose public over private when asked. | Brief decision 1 (lines 55–57, including its "Superseded 2026-09-11" note); the brief's "What exists today" heading (line 16) now says "private" (A-40) |
| **D-2** | Repositories stay on the **Windows filesystem**. The earlier "repos live in WSL" rule is dropped. | No WSL distro is installed. | Brief decision 2 (lines 58–59) |
| **D-3** | The board is kept live by a **refresher loop** (option 1 of 3). Rejected for now: hooks in the build session (option 2) and moving to GitHub Pages plus a database (option 3). | The refresher loop is the lowest-cost option that actually updates. Option 2 relies on the model acting. Option 3 loses the private claude.ai page and means a page rewrite. | Brief decision 3 (lines 60–63) |
| **D-4** | Runs are **derived from transcripts**, not hand-written. A build session writes only its status document's `title`/`message`/`metrics` and the hand-kept build state (now `projects/<projectId>.json`). | No reason recorded beyond the instruction to the build session. | Brief decision 4 (lines 64–65); `CLAUDE.md` Projects |
| **D-5** | **Sessions are auto-discovered: every session active in the last 7 days.** Originally there was one dashboard per session, reached through a session picker. D-18 changed the picker to projects first, and auto-discovery stays. | Chosen over "only sessions with agents" and "a hand-kept list". | Brief decision 5 (lines 66–68) |
| **D-6** | Project tabs appear **only for build sessions**. **Superseded by D-18**: a project always shows all its tabs (FR-129). | No reason recorded. | Brief decision 6 (line 69) |
| **D-7** | The **refresher's own session stays on the board**. | The owner wants to see it. | Brief decision 7 (line 70) |
| **D-8** | **Privacy defaults:** first prompts are not published unless `showFirstPrompt` is on. When it is on, obvious secrets are redacted. `exclude` globs hide sessions. | This came from a code-review finding, and the owner accepted the default. | Brief decision 8 (lines 71–73) |
| **D-9** | **Code changes go through the catalogue agents.** `engineering-agents:code-writer` builds under TDD, then `review-agents:code-reviewer` gives GO/NO-GO, looping until GO. | The owner asked "why aren't we using agents for this?" after a solo build whose first review was NO-GO. | Brief decision 9 (lines 74–77) |
| **D-10** | **Design preferences:** a professional dashboard with status tiles. It uses one sans (Schibsted Grotesk) with tabular figures, and monospace only for ids and hashes. Tokens are dark-first. The violet `--human` is only for things waiting on a human. Motion appears only when true. | These are the owner's stated preferences. | Brief decision 10 (lines 78–82); `CLAUDE.md` "Design rules" |
| **D-11** | **Deleting store documents needs the owner's go-ahead.** | An automated permission check blocked a batch that deleted `tabs/usage`. Scope against routine deletes: row 14. | Brief decision 11 (lines 83–84) |
| **D-12** | **Only the owner views the board.** It is not shared. | Privacy work beyond the current defaults is therefore not a priority. Reaffirmed in `CLAUDE.md` (2026-09-11). | Brief decision 12 (lines 127–128) |
| **D-13** | **One tracked project.** **Superseded by D-18 the same day.** | No reason recorded. | Brief decision 13 (line 129) |
| **D-14** | **Freshness: 10 minutes is enough.** The refresher loop runs every 10 minutes. | The owner set the target at 10 minutes (reaffirmed 2026-09-11). | Brief decision 14 (lines 130–131); `CLAUDE.md` (`/loop 10m`) |
| **D-15** | **Show sessions from the last 7 days, for now. No archive.** | No reason recorded. | Brief decision 15 (line 132) |
| **D-16** | **Local first, hosting later.** A collector writes to SQLite, and a small local web server serves the page, a data snapshot and a live-push stream. The page gets one data adapter. The app starts at log-on via Task Scheduler and uses no Claude usage to refresh. One set of record shapes is defined now. The answers endpoint D-16 also named is deferred by D-22. | Hosting later then only swaps the storage and the transport. | Brief decision 16 (lines 140–148); ADR-0001 (accepted) |
| **D-17** | **Unraid is the owner's possible host.** The server and SQLite database can run as a container on Unraid, and the collector stays on the PC and sends records over the LAN. SQLite is never on a network share. Azure remains a later alternative. | Transcripts exist only on the PC. SQLite locking over SMB/NFS is unreliable. | Brief decision 17 (lines 149–154) |
| **D-18** | **Project-first navigation, the build priority.** It supersedes D-13 and D-6. Projects and their build sessions are listed in `board.config.json`. Dispatch and usage combine every session building a project, with a filter to one session. Unlinked sessions stay viewable. **Shipped in commit `2742ca6`.** | Build sessions run from `C:\Users\jdk`, not the repo folder, so they must be listed. | Brief decision 18 (lines 156–168); spec "Already delivered" |
| **D-19** | **Agent catalogue tab, built first (PBI-017).** The owner's words: "Can we add a PBI for a new tab to show all the agents in the catalogue with coverage of what we are using? Make this the first thing we build." At the plan gate the owner widened it with "Include skills too" and "Show what each agent is for". The tab therefore lists the catalogue's agents and skills, grouped by purpose, with full descriptions. | Owner request. | Brief decision 19 (line 170); spec Key decisions rows 1–2; row 16 |
| **D-20** | **Future iterations on the Backlog (PBI-018).** A "Later" group of idea cards, read from the spec's "Future iterations (not planned)" list. | The owner asked: "In the backlog, do we show future iterations?", and the Backlog did not show them. | Brief decision 20 (line 171); row 23 |
| **D-21** | **The GitHub repository `jdk-official/dispatch-board` is private.** It supersedes D-1. `snapshot/` stays in the repository. | Owner answer at the plan gate on row 3 ("Make the repo private"), about the committed snapshot of build data; done the same day. | Spec Key decisions; row 3; Plan-gate record |
| **D-22** | **Answering assumptions from the board is deferred.** Answers stay in chat. The former PBI-015 moves to Future iterations. The guards that stop agents writing answers stay in the plan (FR-133, FR-134, C-16). | Owner answer at the plan gate on row 5: "Not now". | Spec Key decisions; row 5; Plan-gate record |
| **D-23** | **The local app goes on the owner's PC first. Unraid is last and optional**, built only when the owner says so. | Owner answer at the plan gate on row 6: "On this PC first". | Spec Key decisions; row 6; Plan-gate record |
| **D-24** | **Local-app technology and switch-over:** Python standard library only under `local/`: `sqlite3` in WAL mode, a threaded `http.server`, Server-Sent Events for live push, default port 8765. On the PC the server binds to 127.0.0.1. The v1 artifact and refresher keep running until the owner retires them. | The owner accepted the default at the plan gate (row 8). Recorded as ADR-0001, status accepted. | Row 8; ADR-0001; spec Key decisions |
| **D-25** | **Plan approved (2026-09-11).** "Approve (Recommended)" was given for spec revision 4, conditional on a clean round-3 review. The condition was met: round 3 returned APPROVE-WITH-NOTES, disposed in revision 5. The owner answered "Accept all defaults" for rows 1, 4, 8, 10–14, 19–21 and 23. Rows 7 ("Yes, that's fine"), 15 ("Yes, side by side first") and 24 ("Yes, harden it") were accepted as recommended. Row 16 was changed with the PBI-017 changes of D-19. | Owner approval at the plan gate. | Spec Plan-gate record |
| **D-26** | **Standing instruction (2026-09-11):** build continuously through the backlog-delivery workflow with the catalogue agents. Merges stay the owner's. | Owner instruction. | Orchestrator's verified facts, 2026-09-11; spec metadata `merge_allowed_by_agent: false` |

*Not promoted to a decision:*
- `CLAUDE.md`'s open item "Switch Dispatch to transcript figures so there is one number" is an unowned imperative. The owner-confirmed row 1 settles the matter the other way: Dispatch keeps `subagent_tokens`, relabelled "reported tokens" (A-6, FR-192).
- The spec's planner decisions are recorded in the approved spec and are not owner decisions: all derivations in one shared module under `exporters/`, and ordering enforced by `depends_on` edges and the `page` conflict group. The first is reflected in FR-87.
- `CLAUDE.md`'s data model is the build's implementation, not an owner decision. Part A draws on it as the description of the current tree.

## 4. Functional requirements

**Status tags:**
- *Met* means the current tree meets the requirement. The evidence is a named test in `tests/` (Python `Class.test_name`, or a quoted check of `page.test.mjs`), or inspection of the named code where no test exists. This document ran nothing itself; both suites were run on 2026-09-11 and passed (A-44). Gaps in the evidence mapping remain (A-45).
- *v1 procedure* means the behaviour is performed by the refresher session following `CLAUDE.md`, and is checked by demonstration.
- *Built (PBI-017)* means built, reviewed and live on the board, with PR #1 awaiting the owner's merge.
- **Not met** marks a known gap or an open review finding.
- **Superseded by …** marks a requirement kept for traceability that is no longer in force.
- **Next iteration: not built** marks Part B.
- **Deferred (D-22)** marks the answer path, which is not in the plan.

**Supersession table (resolved in revision 3).**

| Requirement | Replaced by | Status |
|---|---|---|
| FR-2 (build sessions exported beyond the window) | FR-137 (linked sessions) | **Superseded**: D-18 shipped (`2742ca6`). |
| FR-42 (five singleton `tabs/*` documents) | FR-140, FR-153 | **Superseded**. The five old documents are store leftovers until PBI-021 (row 4). |
| FR-43 (work-item state from `BUILD_STATE`) | FR-141 (`buildState` in the project data file) | **Superseded**. FR-113 will run *beside* FR-141 during the shadow period (FR-175, FR-176, row 15), not replace it. |
| FR-54 (`meta/status` update for the one build) | FR-144 | **Superseded**. |
| FR-55 (non-build changes leave `meta/status` alone) | FR-149 | **Superseded**. |
| FR-56 (`live` for the one build) | FR-150 | **Superseded**. |
| FR-66 (session picker) | FR-130 | **Superseded**. |
| FR-67 (default session selection) | FR-156, FR-157 | **Superseded**. |
| FR-68 and AC-51 (project tabs hidden for non-build sessions) | FR-129, FR-158 and AC-85, AC-107 | **Superseded**. |
| FR-69 (views limited to one session) | FR-145 to FR-147 | **Superseded**. |
| NFR-16 and AC-47 (82 tests) | Restated in place (197, confirmed by the 2026-09-11 run, A-44) | **Resolved**: amended, not superseded. |
| FR-63 (page reads only through `window.claude.use('db')`) | FR-97 to FR-99 (data adapter) | **In force** until PBI-006 builds the adapter seam. |
| FR-64 and AC-50 (the page never writes) | FR-131, FR-132 | **In force**. The replacement is deferred by D-22. |
| AC-34, AC-42, AC-44 (exact plan contents) | The counts rise by one last-refresh write | Re-baselined to the current fixtures. They are updated when FR-103 is built (row 12). |

### Part A: current tree (the baseline)

#### Session discovery and session documents (session exporter)

- **FR-1** When the session exporter runs, it shall write one `sessions/<id>` document for every main transcript under `sessions.projectsRoot` whose last recorded timestamp lies within the session window of the run. *(Met: `Pipeline.test_basic_export`; D-5, D-15.)*
- **FR-2** **Superseded by FR-137.** The session exporter shall export every build session whether or not its last activity lies within the session window.
- **FR-3** The session exporter shall set `build` to true on the documents of sessions linked to the project whose status document is `meta/status` (platform-catalogue), and to false on every other session document. *(Met: `Projects.test_build_flag_marks_only_the_meta_status_project`. Only copies of the page from before D-18 read `build`.)*
- **FR-4** The session exporter shall write in every session document the fields `title`, `folder`, `cwd`, `start`, `last`, `project`, `build`, `windowDays`, `windowMinutes`, `runs`, `running`, `usage` and `skillUses`. *(Met: `Pipeline.test_window_days_on_the_session_doc`, `test_window_minutes_on_the_session_doc`, `Projects.test_session_keeps_its_folder_name`, `CatalogueUsage.test_sessions_without_skill_use_carry_an_empty_map`; `CLAUDE.md` data model.)*
- **FR-5** If a main transcript records no assistant response, then the session exporter shall leave that session out of the export. *(Met: inspection of `parse_session()`.)*

#### Agent runs (session exporter)

- **FR-6** When the session exporter exports a session, it shall write one `runs/<agentId>` document per agent transcript in that session, carrying `session`, `project`, `seq`, `lane`, `label`, `kind`, `verdict`, `tok` and `min`. *(Met: `Pipeline.test_basic_export`, `Projects.test_sessions_and_runs_carry_their_project`. `agentType` and `start`: FR-167.)*
- **FR-7** The session exporter shall assign each run's lane from its agent type as follows: `requirements-author` → `req`, `Plan` → `plan`, `code-writer` → `cw`, `test-writer` → `tw`, `code-reviewer` → `cr`, `verifier` → `ver`, and any other, missing or unreadable agent type → `other`. *(Met: `Malformed.test_truncated_meta_falls_back_to_empty`.)*
- **FR-8** If a TaskStop names a run that has no completed finish, then the session exporter shall classify that run as kind `killed` with verdict `stopped`. *(Met: `Classify.test_stopped`, `test_stop_echo_notification_keeps_stopped`, `test_stopped_then_resumed_and_completed`, `test_completion_before_an_ineffective_stop_keeps_its_verdict`.)*
- **FR-9** If a run's last reply or finish result reports that a session, weekly or usage limit was hit, then the session exporter shall classify that run as kind `killed` with verdict `killed · rate limit`. *(Met: `Classify.test_rate_limit`.)*
- **FR-10** When a review-lane run completes, the session exporter shall record as its verdict the last review token in its finish result, or in its last reply when the result holds none. *(Met: `VerdictOf.test_rereview_quoting_an_earlier_verdict_takes_the_last_label`, `test_lane_decides_the_vocabulary`.)*
- **FR-11** When a build-lane run completes, the session exporter shall record as its verdict the first build token (`NOT-DONE`, `DONE-WITH-CONDITIONS`, `DONE`) in its finish result, or in its last reply when the result holds none. *(Met: `VerdictOf.test_builders_keep_the_leading_token`.)*
- **FR-12** The session exporter shall derive a completed run's kind from its verdict token as follows. On review lanes: `NO-GO`, `REJECT` or `REJECTED` → `nogo`; `CHANGES-REQUIRED` → `changes`; any other review token → `go`. On build lanes: `NOT-DONE` → `changes`; any other build token → `done`. With no token on any lane: `done`, with verdict `finished`. *(Met: `KindOf.*`, `Classify.test_completed`.)*
- **FR-13** If a run's finish reports a status other than completed, then the session exporter shall classify the run as kind `killed` with that status as its verdict, or `failed` when the status is blank. *(Met: `Classify.test_failed_finish`.)*
- **FR-14** While a run has no finish and its agent transcript was last written within the running window, the session exporter shall classify the run as kind `running`. *(Met: `Classify.test_running_window`.)*
- **FR-15** If a run has no finish and its agent transcript was last written longer ago than the running window, then the session exporter shall classify the run as kind `killed` with verdict `no result`. *(Met: `Classify.test_running_window`.)*
- **FR-16** When a foreground agent returns its result inline rather than by notification, the session exporter shall treat that inline result as the run's finish. *(Met: `Pipeline.test_inline_result`.)*
- **FR-17** The session exporter shall set a run's `tok` to the `subagent_tokens` its finish reports. When that value is missing or unreadable, it shall use the context size of the agent's last transcript response. *(Met: `Pipeline.test_basic_export`, `Malformed.test_malformed_numeric_tags`. Dispatch keeps this figure, relabelled "reported tokens": row 1, FR-192.)*
- **FR-18** The session exporter shall set a run's `min` to its reported duration in whole minutes, rounded. When that value is missing or unreadable, it shall use the whole minutes between the run's launch and its finish. *(Met: `Classify.test_minutes`, `test_minutes_survive_malformed_numbers_and_timestamps`.)*
- **FR-19** When a code-writer or test-writer run whose label marks it as a fix (it contains `review`, `LOW`, `LOWs`, `notes`, `fix`, `fixes` or `CR-<n>`) starts after a review-lane run with a verdict, the session exporter shall set its `feeds` to one of two runs. If the fix run names a PBI id, it is the latest earlier such review run that shares a PBI id. If the fix run names none, it is the latest earlier such review run. *(Met: `Link.test_fix_is_fed_by_the_review`; heuristic limits, A-23.)*
- **FR-20** When a code-reviewer run starts after a code-writer or test-writer run of kind `done`, the session exporter shall set its `from` to the latest such run, restricted to runs sharing a PBI id when the review names one. *(Met: `Link.test_review_comes_from_the_last_finished_build`, `Pipeline.test_not_done_builder_is_changes_and_does_not_hand_off`.)*
- **FR-21** When a code-writer or test-writer run naming a PBI id starts after a plan-lane run of kind `go` that shares that id, the session exporter shall set its `from` to that plan-lane run. *(Met: `Link.test_builder_comes_from_the_plan_gate`.)*
- **FR-22** When two or more consecutive non-fix runs in the same build lane (`cw` or `tw`) each launch within 120 seconds of the previous one, the session exporter shall give them one shared `group` letter. *(Met: `Link.test_parallel_group`.)*
- **FR-23** Where `runs.manual` lists a row whose `after` run is exported, the session exporter shall insert that row immediately after its anchor run, in the anchor run's session. *(Met: inspection of `main()`.)*

#### Usage (session exporter)

- **FR-24** The session exporter shall compute each session's effective usage over the responses in its main transcript and in every agent transcript, counting each response once by message id. *(Met: inspection of `tokens()` and `response()`.)*
- **FR-25** When a transcript records a request refused by a usage limit (an API error status 429 or a quota-limit record), the session exporter shall count that refusal in the session's `usage.limits`, grouped by the reset time the platform reported. *(Met: inspection of `reject()` and `usage_doc()`; `AggregateUsage.test_limits_sharing_a_reset_are_one_limit`.)*
- **FR-26** The session exporter shall publish, per session, an hourly effective-usage series split into main session and agents, covering at most the last 168 hours of that session's activity. *(Met: inspection of `usage_doc()`; `AggregateUsage.test_hourly_series_is_capped_to_the_last_week`.)*

#### Privacy (session exporter)

- **FR-27** Where a `sessions.exclude` glob matches a session's working folder (with either slash direction) or its project folder name under the projects root, the session exporter shall not read, cache or export that session. *(Met: `Privacy.test_exclude_by_cwd`, `test_exclude_by_project_folder`, `test_excluded_sessions_are_not_cached`; D-8.)*
- **FR-28** While `sessions.showFirstPrompt` is off, the session exporter shall omit `firstPrompt` from every session document. *(Met: `Privacy.test_first_prompt_is_off_by_default`, `test_toggling_first_prompt_applies_without_a_transcript_change`; D-8.)*
- **FR-29** If a session has no title while `sessions.showFirstPrompt` is off, then the session exporter shall use the first 8 characters of the session id as its title. *(Met: `Privacy.test_first_prompt_is_off_by_default`; inspection of `session_doc()`.)*
- **FR-30** Where `sessions.showFirstPrompt` is on, the session exporter shall replace every match of the redaction patterns in NFR-7 with `[redacted]` before publishing the first prompt as `firstPrompt`. *(Met: `Privacy.test_first_prompt_when_on_is_redacted`, `Redact.test_patterns`; D-8.)*

#### Failure isolation (session exporter)

- **FR-31** If an agent transcript cannot be read and no earlier row for that agent is cached, then the session exporter shall export the rest of that session without the agent. *(Met: `Malformed.test_unreadable_subagent_is_skipped_with_a_warning`, `test_subagent_file_that_vanishes_is_skipped`.)*
- **FR-32** If an agent that was exported on an earlier run cannot be re-read, then the session exporter shall keep that agent's last cached row. *(Met: `Malformed.test_agent_that_cannot_be_reread_keeps_its_last_row`. See also FR-80.)*
- **FR-33** When a session's cached parse skipped an unreadable agent, the session exporter shall re-read that session on its next run. *(Met: `Malformed.test_transient_agent_read_error_does_not_drop_the_run_for_good`.)*
- **FR-34** If a session's main transcript cannot be parsed and an earlier parse is cached, then the session exporter shall keep the session's last export until a later run parses it. *(Met: `Malformed.test_failed_parse_keeps_the_previous_result`.)*
- **FR-35** If a session's main transcript cannot be parsed and no earlier parse is cached, then the session exporter shall leave that session out of the export. *(Met: `Malformed.test_failed_parse_without_a_cached_result_omits_the_session`, `test_main_transcript_that_vanishes_is_skipped`.)*
- **FR-36** The session exporter shall skip every transcript line that is not a JSON object. *(Met: `Records.test_only_dict_records`, `Malformed.test_non_object_lines_are_skipped`, `test_meta_that_is_not_an_object`.)*
- **FR-37** If `sessions.projectsRoot` does not exist, then the session exporter shall exit non-zero and leave the previous contents of `out/` unchanged. *(Met: `Discovery.test_missing_projects_root_fails_and_keeps_the_last_export`.)*
- **FR-38** If a linked session's main transcript cannot be found under the projects root, then the session exporter shall exit non-zero, naming that session id. *(Met: `Projects.test_linked_session_without_a_transcript_fails`; `Discovery.test_missing_build_transcript_fails` for the older config shape of FR-136.)*

#### Parse cache and file writes

- **FR-39** When the parser version, the running window, and every one of a session's transcript files' modification time and size are unchanged since the previous run, the session exporter shall reuse the cached parse, unless one of the session's runs is `running` or an agent was skipped. *(Met: `Cache.test_reused_when_nothing_changed`, `test_invalidated_by_a_transcript_change`.)*
- **FR-40** When a project's `sessions` list, `sessions.showFirstPrompt` or `runs.runningWindowMinutes` changes, the session exporter shall apply the new value on its next run without any transcript change. *(Met: `Cache.test_running_window_change_applies_without_a_transcript_change`, `Privacy.test_toggling_first_prompt_applies_without_a_transcript_change`. `Cache.test_build_sessions_change_applies_without_a_transcript_change` covers the linked-session list through the older `build.sessions` shape, which FR-136 reads as one project.)*
- **FR-41** The session exporter and the refresh script shall write each output and state file through a temporary file in the same folder that is then swapped into place. *(Met: `WriteJson.test_a_failed_write_keeps_the_previous_file`, `Save.*`.)*

#### Project tabs (board exporter)

- **FR-42** **Superseded by FR-140 and FR-153.** When the board exporter runs, it shall write the five project-tab documents `spec`, `assumptions`, `decisions`, `backlog` and `git`.
- **FR-43** **Superseded by FR-141.** The board exporter shall take each work item's state, review summary, open items and commit from `BUILD_STATE`, defaulting any work item absent from `BUILD_STATE` to state `todo`.
- **FR-44** The board exporter shall mark as awaiting a human (`needsYou`), for each project, exactly the assumption rows that the project's spec lists as rows the human must confirm at the plan gate. *(Met: inspection; `ExportProject.test_spec_without_the_human_rows_line`.)*

#### Refresh script

- **FR-45** When the refresh script runs, it shall run the exporters and then print a JSON plan holding a `set` write for every document of the managed collections whose content, ignoring `generatedAt`, differs from the pushed state. *(Met: `Plan.test_first_plan_sets_everything_and_the_status`, `test_generated_at_alone_is_not_a_change`, `Catalogue.test_catalogue_is_a_managed_collection`, `test_a_new_generated_at_alone_is_not_a_change`.)*
- **FR-46** ~~If no document differs from the pushed state and no status update is due, then the refresh script shall print `nothing to push` and leave no pending plan.~~ **Superseded 2026-09-12 by FR-103 (PBI-008).** Every plan now carries one `set` of `meta/lastRefresh`, so a tick always has at least one write and that output can no longer occur. What remains true: a quiet tick plans only the last-refresh write, and a stale pending file is still removed. *(Met: `Plan.test_commit_then_a_quiet_tick_prints_only_the_last_refresh_write`, `test_nothing_to_push_replaces_a_stale_pending_file`, `Cli.test_a_quiet_tick_prints_only_the_last_refresh_write`.)*
- **FR-47** When a document of a managed collection recorded in the pushed state is no longer exported, the refresh script shall include a `delete` write for it. *(Met: `Plan.test_vanished_run_is_deleted`, `test_vanished_project_tab_is_deleted`; D-11 scope, row 14.)*
- **FR-48** The refresh script shall emit no `delete` write for any document outside the managed collections or not recorded in the pushed state. *(Met: `Plan.test_retired_tabs_are_never_deleted`, `test_unmanaged_collections_are_never_deleted`. This is why the six leftovers stay until PBI-021.)*
- **FR-49** If the export contains no sessions, would delete more than half of the pushed runs and sessions, would delete any `projects/*` document, would delete every pushed `projectTabs` document of a project, or would delete `catalogue/index`, then the refresh script shall refuse the plan: it exits non-zero, names `--allow-mass-delete` on stderr, and leaves no pending plan. *(Met: `MassDelete.test_more_than_half_is_refused`, `test_refusal_removes_a_stale_pending_file`, `test_zero_sessions_is_refused`, `test_zero_sessions_refused_even_for_a_small_delete`, `test_losing_every_tab_of_a_project_is_refused`, `test_losing_the_only_tab_of_a_second_project_is_refused`, `test_deleting_a_project_document_is_refused`, `Catalogue.test_deleting_the_catalogue_is_refused`, `Cli.test_mass_delete_exits_non_zero_without_the_flag`.)*
- **FR-50** Where `--allow-mass-delete` is given, the refresh script shall plan the deletes that FR-49 would otherwise refuse. *(Met: `MassDelete.test_allowed_with_the_flag`, `Plan.test_vanished_project_is_deleted_with_the_flag`, `Cli.test_project_delete_exits_non_zero_without_the_flag`.)*
- **FR-51** If any exporter exits non-zero, then the refresh script shall run no later exporter and exit non-zero without planning. *(Met: `Export.test_a_failing_exporter_stops_the_rest`, `Cli.test_export_failure_stops_before_planning`.)*
- **FR-52** When `refresh.py --commit` is run with a pending plan, the refresh script shall record that plan's state as the pushed state. *(Met: `Plan.test_commit_then_a_quiet_tick_prints_only_the_last_refresh_write`, `Cli.test_commit`.)*
- **FR-53** If `refresh.py --commit` is run with no pending plan, then the refresh script shall exit with status 1 and report `nothing pending`. *(Met: `Cli.test_commit_without_pending`.)*
- **FR-54** **Superseded by FR-144.** When a tabs document, a build session's document or a build session's run is changed or deleted, or the live flag flips, the refresh script shall add an `update` of `meta/status` carrying `live` and `updatedAt`.
- **FR-55** **Superseded by FR-149.** If only non-build session documents or their runs change, then the refresh script shall leave `meta/status` out of the plan.
- **FR-56** **Superseded by FR-150.** The refresh script shall set `live` to true exactly when a build session has a run of kind `running`.
- **FR-57** When a plan holds more than 50 writes, the refresh script shall split it into consecutive batches of at most 50 writes. *(Met: `Plan.test_batches_past_the_limit`; C-3.)*

#### Refresher

These requirements stay in force until the local app replaces the refresher (row 1, D-24).

- **FR-58** While the refresher loop is active, the refresher shall, on each tick, run the refresh script and write the printed plan to the store with `write_db` batch operations. *(v1 procedure: `CLAUDE.md` Refresh procedure, steps 1–2; D-3.)*
- **FR-59** ~~When the refresh script prints `nothing to push`, the refresher shall end the tick without writing to the store. *(v1 procedure: the `/loop` prompt in `CLAUDE.md`.)*~~ **Superseded 2026-09-12 by FR-103 (PBI-008), with FR-46.** Every plan now carries one `set` of `meta/lastRefresh`, so a tick always has at least one write and the script can no longer print `nothing to push`. A tick still writes nothing when the plan is refused by a guard, which exits non-zero.
- **FR-60** When a tick's `write_db` writes succeed, the refresher shall run `refresh.py --commit`. *(v1 procedure: `CLAUDE.md` step 3.)*
- **FR-61** If a tick's `write_db` write fails, then the refresher shall not run `refresh.py --commit`. *(v1 procedure: `CLAUDE.md` step 3.)*
- **FR-62** If the refresh script exits non-zero, then the refresher shall write nothing to the store in that tick. *(v1 procedure: `CLAUDE.md` step 1.)*

#### Page

- **FR-63** The page shall obtain all its data from store subscriptions opened through `window.claude.use('db')`. *(Met: inspection of `site/index.html`. In force until FR-97 to FR-99 are built.)*
- **FR-64** The page shall issue no write to the store. *(Met: inspection; the brief's "What exists today", `site/index.html` item (line 19). In force: D-22 defers the only proposed page write.)*
- **FR-65** When a subscribed store document changes, the page shall re-render the views that show it. *(Met: inspection of the `onSnapshot` handlers.)*
- **FR-66** **Superseded by FR-130.** The page shall list sessions in a session picker, with build sessions in a "Builds" group and all others in an "Other sessions · last <N> days" group, most recent activity first.
- **FR-67** **Superseded by FR-156 and FR-157.** When sessions first load and no session is selected, the page shall select the first session available in this order: the saved session, the first live build session, the first build session, the most recently active session.
- **FR-68** **Superseded by FR-129 and FR-158.** While the selected session is not a build session, the page shall hide the project tabs.
- **FR-69** **Superseded by FR-145 to FR-147.** When a session is selected, the page shall limit the Overview, Dispatch and Claude-usage tabs to that session's runs and usage.
- **FR-70** While a project is selected and any of its runs is `running` or its status document's `live` is true, the page shall show the header status `Building`. *(Met: page check "dispatch-board: only its runs, Building while its run runs…"; inspection of `renderHeader()`. Otherwise the page shows the status document's `title`, or `Idle`.)*
- **FR-71** While "Other sessions" is selected and the chosen session has a `running` run or its last activity lies within its `windowMinutes`, the page shall show the header status `Active`. *(Met: inspection of `renderHeader()`; otherwise `Idle`.)*
- **FR-72** When the Dispatch tab is shown, the page shall draw the current view's runs as a swimlane. Runs are drawn in `seq` order within each session, and sessions in the order they started. The swimlane shows `from` hand-off arrows, `feeds` arrows and one bracket per parallel `group`. It has one column per lane used, and every pipeline lane in a project view. *(Met: inspection of `renderDispatch()`, `sorted()` and `laneList()`.)*
- **FR-73** When the Dispatch tab is shown, the page shall list the current view's runs newest first, each with its agent, label, outcome, verdict, tokens and minutes. *(Met: inspection of `renderDispatch()`.)*
- **FR-74** While a project is selected, the page shall show in the Overview the summary tiles, backlog cells, pipeline, needs-attention list, usage panel, review outcomes and recent agent activity. *(Met: page check "project Overview: the summary tiles and backlog cells come from the project's backlog and runs"; inspection of `renderOverview()`.)*
- **FR-75** The page shall derive the needs-attention list from store data. It lists assumptions awaiting a human, work items with open conditions, partly built work items, a tracked build repo with no git remote, a session with runs but no verifier run, and runs cut off. *(Met: inspection of `renderOverview()`.)*
- **FR-76** When the Claude-usage tab is shown, the page shall show the current view's effective usage by activity, by hour, by model and by agent run, its usage-limit hits, and a notice that the figures are not a plan usage meter. *(Met: inspection of `renderUsage()`. With no session filter, a project view uses the project's combined `usage`.)*
- **FR-77** If `window.claude.use('db')` is unavailable, then the page shall show only a notice that it cannot reach the live store. *(Met: inspection.)*
- **FR-78** If a live store subscription ends with an error, then the page shall show a footer message giving the error code and asking for a reload. *(Met: inspection.)*
- **FR-79** The page shall restore the last selected tab, view and session filter from browser local storage when it is reloaded. *(Met: page checks "saved project and saved session filter are restored…" and "project view shows every project tab; the saved Spec tab survives the load".)*

#### Requirements not met in the current tree

The remedies below are settled by row 13 and planned in PBI-001 (exporter fixes) and PBI-002 (page fixes).

- **FR-80** **Not met (open review LOW 1).** If an agent transcript cannot be re-read and its carried-over row has kind `running`, then the session exporter shall reclassify that row as kind `killed` with verdict `no result` once the running window has elapsed since the row's `end` time. *(Row 13; PBI-001.)*
- **FR-81** **Not met (open review LOW 2).** If a usage record in an agent transcript is malformed, then the session exporter shall skip that record and export the session with its other records. *(Row 13; PBI-001.)*
- **FR-82** **Not met (open review LOW 3).** If a value under `sessions` or `runs` in `board.config.json` does not have its documented JSON type, then the session exporter shall exit with status 2 and an error naming the key. The documented types are: `days` and `runningWindowMinutes` numbers, `projectsRoot` a string, `exclude` a list of strings, `showFirstPrompt` a boolean, `manual` a list. *(Row 13: "config type checks with exit 2"; PBI-001.)*
- **FR-83** **Not met (open review LOW 4).** While a session under "Other sessions" is selected, the page shall show the same active-or-idle state in the Overview's "Running now" tile as in the header status. *(The tile is computed only when data changes (`site/index.html` line 420). The header is redrawn every 60 s (line 991). Row 13; PBI-002.)*
- **FR-84** **Not met (known gap).** When a verifier run completes with a result stating `exercised` or `fallback-declared`, the session exporter shall record that word as the run's verdict. *(The kind stays `done`: row 13 confirms the A-11 default; PBI-001.)*
- **FR-85** **Not met (known gap, cause unknown).** When the published page is opened in Chrome, the page shall render its app bar and Overview panel without a manual reload. *(Row 13: a time-boxed investigation in PBI-002.)*

#### Project-first navigation (as built: D-18, commit `2742ca6`)

- **FR-129** When a project is selected, the page shall show all its tabs: Overview, Spec, Assumptions, Decisions, Backlog, GitHub, Dispatch, Agent catalogue and Claude usage. *(Met: page check "project view shows every project tab…"; `site/index.html` lines 219–227. Replaces FR-68. Nine tabs: A-43.)*
- **FR-130** The page shall list the projects in its picker in their `board.config.json` order, followed by an "Other sessions" entry while any unlinked session is exported. *(Met: page checks "picker lists projects in order, then Other sessions…" and "with no unlinked sessions left, Other sessions disappears…". Replaces FR-66.)*
- **FR-135** The exporters shall read the tracked projects from `projects` in `board.config.json`, each with `id`, `name`, `repoPath`, `branch`, `sessions`, `statusDoc` and `docs`. *(Met: `ProjectList.test_projects_list_wins_over_the_legacy_block`, `test_defaults`, `CommittedFiles.test_repo_config_lists_both_projects`.)*
- **FR-136** If `board.config.json` has no `projects`, then the exporters shall read the older `build.*` shape as one project whose status document is `meta/status`. *(Met: `ProjectList.test_legacy_build_block_is_one_project`, `LegacyProjects.test_build_block_is_one_project`, `test_usage_sessions_are_linked_too`.)*
- **FR-137** The session exporter shall export every linked session whether or not its last activity lies within the session window. *(Shipped; `CLAUDE.md` data model. No named test was identified: A-45. Replaces FR-2.)*
- **FR-138** The session exporter shall set `project` on every session and run document to the id of the project that lists the session, or to null when no project lists it. *(Met: `Projects.test_sessions_and_runs_carry_their_project`.)*
- **FR-139** When the session exporter runs, it shall write one `projects/<projectId>` document per project. The document carries `name`, `repoPath`, `branch`, the exported linked `sessions`, `statusDoc` and `order`, plus `runs`, `running`, `last` and `usage` combined over the linked sessions. *(Met: `Projects.test_project_document`, `test_project_usage_combines_its_sessions`, `test_session_listed_twice_counts_once`, `AggregateUsage.*`.)*
- **FR-140** When the board exporter runs, it shall write one `projectTabs/<projectId>.<tab>` document for each project tab whose source has existed in that project's repository. No document is written for a tab whose source has never existed. *(Met: `ExportProject.test_every_tab_is_written_under_the_project_id`, `MissingSources.test_missing_spec_board_and_adrs_write_no_spec_tabs`, `test_folder_that_is_not_a_git_repo_has_no_git_tab`. Replaces FR-42; keep-last behaviour: FR-153.)*
- **FR-141** The board exporter shall take each work item's state, review summary, open items and commit from `buildState` in `projects/<projectId>.json`, treating an unlisted work item as `todo`. *(Met: `ExportProject.test_build_state_and_open_questions_come_from_the_data_file`, `test_missing_data_file_means_no_build_state`. Replaces FR-43. FR-113 runs beside it in the shadow period: FR-175.)*
- **FR-142** If a project data file is not valid JSON, then the board exporter shall exit non-zero, so that the refresh script pushes nothing. *(Met: `ExportProject.test_malformed_data_file_stops_the_export_and_keeps_the_last_one`.)*
- **FR-143** If a project's `repoPath` does not exist, then the board exporter shall skip that project with a warning on stderr and refresh the other projects. *(Met: `MissingSources.test_missing_repo_is_skipped_with_a_warning`, `test_missing_repo_keeps_its_last_tabs_while_others_refresh`.)*
- **FR-144** When a project's `projects` or `projectTabs` documents, one of its linked sessions or one of their runs changes, or its live flag flips, the refresh script shall update that project's status document with `live` and `updatedAt`. The status document is `meta/status` for platform-catalogue and `status/<projectId>` otherwise. *(Met: `UpdatedAt.test_linked_session_change_bumps`, `test_linked_run_change_bumps`, `test_deleted_linked_run_bumps`, `test_project_tab_change_bumps`, `test_project_document_change_bumps`, `test_live_flip_bumps`, `ProjectStatus.test_a_change_bumps_only_its_own_project`. Replaces FR-54.)*
- **FR-145** When a project is selected, the page shall combine Dispatch, Claude usage and the Overview's agent tiles over every session linked to that project. *(Met: page check "dispatch-board: only its runs, … project-wide usage".)*
- **FR-146** When the session filter names one linked session, the page shall narrow Dispatch, Claude usage and the Overview's agent tiles to that session. *(Met: page check "session filter narrows Dispatch and usage to one session; project tabs stay".)*
- **FR-147** When "Other sessions" is selected, the page shall show Overview, Dispatch, Agent catalogue and Claude usage for the chosen session linked to no project. *(Met: page checks "Other sessions: project tabs hidden, … session-scoped view" and "catalogue, Other sessions: the tab stays…".)*
- **FR-148** When a selected project's tab has no exported document, the page shall show that tab's "not exported yet" state. *(Met: page check "dispatch-board without spec/backlog shows the existing empty states".)*
- **FR-149** If only sessions linked to no project, or their runs, change, then the refresh script shall update no status document. *(Met: `UpdatedAt.test_unlinked_session_change_does_not_bump`, `test_unlinked_run_change_does_not_bump`, `test_running_unlinked_run_does_not_bump`. Replaces FR-55.)*
- **FR-150** The refresh script shall set a project's `live` to true exactly when a session linked to that project has a run of kind `running`. *(Met: `ProjectStatus.test_live_is_per_project`, `UpdatedAt.test_live_flip_bumps`. Replaces FR-56.)*
- **FR-151** When the refresh script first writes a project's `status/<projectId>` document, it shall write that document with a `set`. *(Met: `ProjectStatus.test_first_write_of_a_new_status_document_is_a_set`.)*
- **FR-152** When the refresh script writes a status document that is already recorded in the pushed state, it shall write it with an `update`. *(Met: `ProjectStatus.test_later_writes_merge`. `meta/status` is only ever updated, because it holds hand-written fields.)*
- **FR-153** If a project tab's source goes missing after the tab was exported (the repository is missing or moved, the spec is renamed, or git is unavailable), then the board exporter shall keep that tab's last export unchanged and print a warning on stderr. *(Met: `MissingSources.test_missing_repo_keeps_its_last_tabs_while_others_refresh`, `test_renamed_spec_keeps_the_tabs_built_from_it`, `test_kept_tabs_are_byte_identical`.)*
- **FR-154** When a project is removed from `projects` in `board.config.json`, the exporters shall write no `projects` or `projectTabs` document for it. *(Met: `MissingSources.test_project_dropped_from_the_config_loses_its_tabs`, `Projects.test_projects_dropped_from_the_config_are_removed`. The store deletes then need `--allow-mass-delete`: FR-49.)*
- **FR-155** If `projects` in `board.config.json` is not a list of objects, or a project's `id` or `statusDoc` is unusable, then the exporters shall exit non-zero. *(Met: `ProjectList.test_unusable_ids_and_status_docs_are_refused`, `test_projects_that_is_not_a_list_is_refused`, `test_entry_that_is_not_an_object_is_refused`, `MissingSources.test_project_list_that_is_not_a_list_stops_the_export`.)*
- **FR-156** When the projects and sessions have first loaded, the page shall select a view by this rule: the view saved from the previous visit if the picker still lists it, otherwise the first project with a live session, otherwise the first entry in the picker. *(Met: `pickView()`; page checks "…default is the project with a live session", "saved project and saved session filter are restored…" and "no saved view and no live project: the first project". Replaces FR-67.)*
- **FR-157** When a project view is chosen, the page shall set the session filter to the saved filter if that session is linked to the project, and otherwise to "All sessions". *(Met: `pickSession()`; page check "session filter: All sessions (default) plus the project's sessions".)*
- **FR-158** While "Other sessions" is selected, the page shall hide the Spec, Assumptions, Decisions, Backlog and GitHub tabs. *(Met: `apply()`; page check "Other sessions: project tabs hidden…". With FR-129, this replaces FR-68.)*
- **FR-159** If a view change hides the selected tab, then the page shall select the Overview tab. *(Met: `apply()`; page check "Other sessions: … Spec falls back to Overview…".)*

#### Tab bar (as built; met by row 2)

- **FR-125** While the tab bar is narrower than the total width of its tabs, the page shall show a visible cue that further tabs exist. *(Met: the tab bar wraps (`site/index.html` line 58, `.tabs { flex-wrap: wrap }`), so no tab is ever hidden. Row 2.)*
- **FR-126** When the tab bar has overflowed, the page shall let the owner reach every tab by pointer and by the Left/Right arrow keys. *(Met: wrapping means the bar never overflows, and the arrow keys move between visible tabs (lines 315–323). Keeps NFR-15.)*
- **FR-127** When the owner selects a tab that lies partly outside the visible tab bar, the page shall scroll the tab bar until that tab is fully visible. *(Met: no tab lies outside a wrapping tab bar. Row 2.)*
- **FR-128** When the page is shown at a viewport width of 1050 px, the page shall show the "Claude usage" tab label in full or show the overflow cue of FR-125. *(Met by inspection: row 2. The demonstration (AC-84) found it met on 2026-09-11: A-41.)*

#### Agent catalogue (as built: PBI-017, D-19)

- **FR-160** When the refresh script runs, it shall run the catalogue exporter after the board exporter and the session exporter. *(Built (PBI-017): `Export.test_the_three_exporters_run_in_order`.)*
- **FR-161** When the catalogue exporter runs, it shall write one `catalogue/index` document. The document lists one entry per agent file (`plugins/*/agents/*.md`) and per skill file (`plugins/*/skills/*/SKILL.md`) under the configured `catalogue.marketplacePath`. Each entry carries `id` (`<plugin>:<name>`), `kind`, `plugin`, `name`, `description` and `installed`. Entries are sorted by plugin, then agents first, then name. *(Built (PBI-017): `Export.test_every_agent_and_skill_is_one_entry`, `test_the_file_is_written_whole`, `test_entries_sort_by_plugin_then_agents_first_then_name`, `test_plugins_without_agents_or_skills_are_left_out`; AC-C1.)*
- **FR-162** The catalogue exporter shall mark an entry `installed` exactly when the file at `catalogue.installedPath` holds a `<plugin>@agent-catalog` key for the entry's plugin. *(Built (PBI-017): `Export.test_installed_comes_from_the_agent_catalog_keys`, `Failures.test_missing_installed_file_marks_nothing_installed`, `test_malformed_installed_file_marks_nothing_installed`.)*
- **FR-163** The catalogue exporter shall give each plugin a purpose line, taken as the first sentence of its manifest's `description` cut to 120 characters at a word boundary. Where the manifest has no usable description, the purpose line is the plugin name. *(Built (PBI-017): `Purpose.*`, `PurposeInTheExport.test_manifest_cases`, `Failures.test_malformed_manifest_falls_back_to_the_plugin_name`; AC-C2.)*
- **FR-164** If the marketplace folder or its `plugins/` folder is missing or cannot be listed, or no agent and no skill is found, then the catalogue exporter shall keep the last `catalogue/index` export unchanged and print a warning. *(Built (PBI-017): `Failures.test_missing_marketplace_keeps_the_last_export`, `test_missing_plugins_folder_keeps_the_last_export`, `test_zero_entries_keeps_the_last_export`, `test_unlistable_plugins_folder_keeps_the_last_export`; AC-C6.)*
- **FR-165** If an agent or skill file is unreadable or malformed, or its `<plugin>:<name>` is not a safe id, then the catalogue exporter shall leave that entry out and print a warning. *(Built (PBI-017): `Failures.test_unreadable_or_malformed_entry_files_are_skipped`, `Export.test_an_entry_with_an_unusable_id_is_skipped_with_a_warning`.)*
- **FR-166** If a `catalogue` value in `board.config.json` is not a string, then the catalogue exporter shall exit with status 2. *(Built (PBI-017): `Failures.test_a_config_type_error_exits_2`, `Config.test_non_string_values_raise`.)*
- **FR-167** The session exporter shall write on every subagent run document its `agentType` from the agent's meta file and its `start` launch time. Either field is left out when unknown, and `runs.manual` rows carry neither. *(Built (PBI-017): `CatalogueUsage.test_subagent_runs_carry_agent_type_and_start`, `test_no_agent_type_when_the_meta_is_missing_or_empty`, `test_no_start_when_the_launch_time_is_unknown`, `test_manual_rows_carry_neither`; AC-C3.)*
- **FR-168** The session exporter shall write on every session document a `skillUses` map with a count and a last-use time per skill id, counted from the `Skill` tool calls and the typed `/<plugin>:<skill>` commands in the main transcript. *(Built (PBI-017): `CatalogueUsage.test_skill_calls_and_typed_plugin_commands_are_counted`, `test_a_streamed_skill_call_seen_twice_counts_once`, `test_skill_calls_inside_agent_transcripts_are_not_counted`. Known limits, per `CLAUDE.md`: bare slash commands and skill use inside agent transcripts are not counted.)*
- **FR-169** The page shall show an "Agent catalogue" tab directly after Dispatch, in every project view and in "Other sessions". *(Built (PBI-017): page checks "catalogue: the Agent catalogue tab sits straight after Dispatch, before Claude usage" and "catalogue, Other sessions: the tab stays…"; AC-C5.)*
- **FR-170** When the Agent catalogue tab is shown, the page shall show one group per plugin, in catalogue order, each headed by its purpose line and listing each entry with its full description. *(Built (PBI-017): page check "catalogue: one group per plugin in order, purpose with purposeFull expandable, not-installed tag, descriptions expandable"; AC-C2.)*
- **FR-171** When the Agent catalogue tab is shown, the page shall show for each entry its use count and last use in the current view, and the projects whose sessions used it over all exported sessions. An entry with no use in the current view reads "never used". *(Built (PBI-017): page checks "catalogue: uses and last use (latest run start) in the view; projects and uses over all sessions" and "catalogue: never used in the view…"; AC-C4.)*
- **FR-172** When the Agent catalogue tab is shown, the page shall show an agents tile and a skills tile. Each gives the number of entries of that kind used in the current view, out of the catalogue total, with the all-sessions figure beside it. *(Built (PBI-017): page check "catalogue, project view: tiles give the view figure, the all-sessions figure beside it, and K installed"; AC-C5.)*
- **FR-173** When the Agent catalogue tab is shown, the page shall list agent types and skill ids seen in use but absent from the catalogue in a separate "Outside the catalogue" panel. *(Built (PBI-017): page check "catalogue: ids outside the catalogue get their own final panel with the same columns"; AC-C3.)*
- **FR-174** When the session filter names one session, the page shall narrow the Agent catalogue's current-view figures to that session. *(Built (PBI-017): page check "catalogue: the session filter narrows both runs and sessions".)*

### Part B: next iteration (FR-86 to FR-124, FR-131 to FR-134, FR-175 to FR-192)

Every requirement in Part B is **next iteration: not built**, except FR-95, FR-131 and FR-132, which are **deferred (D-22)**. Sources: D-16, D-17, D-22 to D-24, the candidate features (the brief's "Candidate features for the next iteration", lines 173–198), ledger rows 1, 5–8, 10–13, 15, 23 and 24, and spec criteria AC-L1 to AC-L3. The owning PBI is named where the spec assigns one.

#### Collector (D-16; PBI-019)

- **FR-86** When the collector reads a transcript it has read before, it shall read only the lines appended since its previous read of that file. *(D-16.)*
- **FR-87** The collector shall derive session, run, project, usage and skill-use records by the same rules as the session exporter (FR-1 to FR-41 as amended, FR-137 to FR-139, FR-167, FR-168, and FR-80 to FR-84 once those are met), by importing the shared derivation module (PBI-004). *(D-16; spec Key decisions.)*
- **FR-88** Where the on-PC deployment is used, the collector shall write its records to the local database. *(D-16, D-23.)*
- **FR-89** Where the Unraid deployment is used, the collector shall send its records to the local server's ingest endpoint over the LAN. *(D-17; last and optional, D-23; PBI-016.)*
- **FR-90** When the owner logs on to Windows, Task Scheduler shall start the collector. *(D-16; PBI-007, with the owner's approval of the task.)*
- **FR-91** Where the on-PC deployment is used, when the owner logs on to Windows, Task Scheduler shall start the local server. *(D-16; PBI-007.)*
- **FR-180** If the configured local-database path is a network path (a UNC path beginning `\\` or `//`), then the collector shall refuse to start and name the path. *(Row 24: "the network-path guard runs in both the collector and the server".)*
- **FR-184** If a collector pass finds no sessions, or would delete more than half of the stored runs and sessions other than by age pruning, then the collector shall apply none of that pass's deletions. *(Spec, PBI-019: "a mass-delete guard equivalent to FR-49". Interaction with pruning: A-47.)*
- **FR-185** The collector shall delete from the local database only the records of sessions linked to no project whose last activity is older than the session window. *(Row 12: "the last 7 days plus linked sessions, pruned by age only".)*

#### Local server (D-16, D-17, D-24; PBI-005)

- **FR-92** When a browser requests the local server's root address, the local server shall return the page. *(D-16.)*
- **FR-93** When the page requests the data snapshot, the local server shall return every current record in the record shapes. *(D-16.)*
- **FR-94** When a record in the local database changes, the local server shall send that change on the Server-Sent Events live-push stream to every open page. *(D-16, D-24.)*
- **FR-95** **Deferred (D-22).** When the answers endpoint receives an answer record from the page, the local server shall store it in the local database.
- **FR-96** If the configured local-database path is a network path (a UNC path beginning `\\` or `//`), then the local server shall refuse to start and name the path. *(D-17; C-14. It cannot detect every network mount; NFR-20 rests on AC-71's inspection. Row 24.)*
- **FR-177** If a request to the local server carries a Host header outside the allow-list, then the local server shall reject the request. The allow-list is `localhost` and `127.0.0.1`, plus the Unraid server's configured LAN hostname and address in the Unraid deployment. *(Rows 24 and 7. Response detail: A-46.)*
- **FR-178** If a non-GET request to the local server carries an Origin header that does not match the local server's own origin, then the local server shall reject the request. *(Row 24. Match rule: A-46.)*
- **FR-179** The local server shall send no `Access-Control-Allow-*` (CORS) header on any response. *(Row 24.)*
- **FR-181** Where the Unraid deployment is used, the collector and the local server shall read the ingest shared secret from an environment variable or a git-ignored file, and never from `board.config.json`. *(Row 7; PBI-016.)*
- **FR-182** Where the Unraid deployment is used, if an ingest request does not carry the shared secret, then the local server shall reject the request and store nothing from it. *(Row 7, confirming the former A-27 default; PBI-016.)*
- **FR-183** While the answer write path is deferred (D-22), the local server shall expose no answers endpoint. *(Rows 5 and 7; spec scope `local/**`.)*

#### Data adapter (D-16; PBI-006)

- **FR-97** The page shall obtain all its data through one data-adapter interface. *(D-16.)*
- **FR-98** When the page is served by the local server, the page shall use the local API adapter. *(Row 8: the adapter follows where the page is loaded.)*
- **FR-99** When the page runs as the claude.ai artifact, the page shall use the store adapter. *(C-2 blocks the local API from the artifact: C-18.)*

#### Record shapes (D-16; PBI-003)

- **FR-100** The record shapes shall define session, run, project, tab, status, last-refresh and catalogue records in one definition used by the collector, the local server and both built data adapters. *(D-16; the project record for D-18 (row 12); the catalogue record, the run record's `agentType` and per-session skill use for D-19 (spec, PBI-003). The answer record is deferred by D-22.)*
- **FR-101** The run record shape shall carry each run's start time and end time. *(Needed by the timeline view, FR-122; PBI-003 defines, PBI-020 fills.)*
- **FR-102** The status record shapes shall carry the last-refresh time in a record separate from `meta/status` and `status/<projectId>`. *(Feature 1.)*
- **FR-103** When the collector writes records successfully, or a refresher tick's `write_db` writes succeed, the writer shall set the last-refresh time to the time of that write. *(Feature 1; row 12 accepts the one extra write per tick. The collector's half is in PBI-019, the refresher's in PBI-008.)*

#### Feature 1: stale-board warning (PBI-008)

- **FR-104** The page shall show "data as of <last-refresh time>" in the header. *(Brief candidate feature 1, lines 177–179.)*
- **FR-105** While the last-refresh time is more than 20 minutes old, the page shall show the header's "data as of" text in the `--changes` amber token with the word "stale". *(Brief candidate feature 1, line 178; row 11 accepts exactly 20 minutes.)*

#### Feature 2: "Waiting on you" panel (PBI-009)

- **FR-106** The page shall show one "Waiting on you" panel listing, across all listed sessions, every item that FR-107 to FR-110 detect, marked with the `--human` violet. *(Brief candidate feature 2, lines 180–184; D-10.)*
- **FR-107** When a session's transcript shows a question to the owner with no owner answer after it, the collector shall mark that session as paused on a question. *(Row 10: the record types are confirmed against real transcripts before any detector is built.)*
- **FR-108** When a session's last assistant message asked the owner something and the session has had no activity for longer than the running window, the collector shall mark that session as idle after asking. *(Row 10.)*
- **FR-109** When a transcript records an action refused by the permission check, the collector shall record that refusal against its session. *(Row 10.)*
- **FR-110** The "Waiting on you" panel shall include every assumption row the board exporter marks `needsYou` (FR-44), for every project. *(Brief candidate feature 2, line 184; D-18.)*

#### Feature 3: review findings ledger (PBI-011)

- **FR-111** When a review-lane run's result ends with structured JSON findings, the collector shall record each finding's id, severity, title, file:line and remediation against the run's project, work item and review round. *(Brief candidate feature 3, lines 185–187; rules accepted by row 11; project key by row 12.)*
- **FR-112** When the findings ledger is shown, the page shall show per work item the open and resolved findings and the number of review rounds to GO. *(Row 11.)*

#### Feature 4: work-item status derived from runs (PBI-010)

- **FR-113** The collector shall derive each work item's state (done, conditions open, partly built, todo) from the review verdicts of runs in that project's linked sessions whose labels name the work item's PBI id, without reading any hand-kept build state. *(Brief candidate feature 4, lines 188–189; mapping accepted by row 11. It is shown beside FR-141 during the shadow period (row 15). Retiring FR-141 is a later owner decision: S-39.)*
- **FR-175** While the shadow period is active, the page shall show each work item's derived state beside its hand-kept state and flag every work item where the two differ. *(Row 15: "Yes, side by side first". Switch and length: A-48.)*
- **FR-176** Where a work item has hand-kept `review`, `open` or `commit` values, the Backlog tab shall show those values in place of derived ones. *(Row 15: "Hand-kept `review`, `open` and `commit` stay as overrides".)*

#### Feature 5: test and coverage trend (PBI-012)

- **FR-114** When a code-writer or test-writer run's result states a test count (for example "664 tests green"), the collector shall record that count on the run. *(Brief candidate feature 5, lines 190–191; parsing rule accepted by row 11.)*
- **FR-115** When a code-writer or test-writer run's result states a coverage percentage, the collector shall record that percentage on the run. *(Row 11.)*
- **FR-116** When the test trend is shown, the page shall plot the recorded test counts and coverage percentages per run in `seq` order. *(Brief candidate feature 5, line 191.)*

#### Feature 6: usage limit forecast (PBI-013)

- **FR-117** While at least one usage-limit hit is recorded, the page shall show an estimated time of the next limit hit, labelled as an estimate. *(Brief candidate feature 6, lines 192–193; method accepted by row 11.)*
- **FR-118** If no usage-limit hit is recorded, then the page shall show "no forecast: no limit hit recorded" in place of the estimate. *(Row 11.)*

#### Feature 7: cost per work item (PBI-012)

- **FR-119** The page shall show the effective usage totalled per PBI id named in the labels of a project's runs. *(Brief candidate feature 7, line 194; row 1: cost uses effective usage; row 11: split rule; row 12: project key.)*
- **FR-120** The page shall show the effective usage totalled per agent type. *(Brief candidate feature 7, line 194.)*

#### Feature 8: run detail (PBI-014)

- **FR-121** When the owner selects a run, the page shall show that run's verdict summary, findings, files touched and duration. *(Brief candidate feature 8, lines 195–196; "files touched" source accepted by row 11.)*

#### Feature 9: timeline view (PBI-020)

- **FR-122** When the timeline view is shown, the page shall draw the selected runs as bars on a real-clock time axis from each run's start time to its end time. *(Brief candidate feature 9, lines 197–198; FR-101.)*
- **FR-123** When the timeline view is shown, the page shall mark each recorded usage-limit refusal at its time on the axis. *(Brief candidate feature 9, lines 197–198.)*
- **FR-124** When the timeline view is shown, the page shall shade every interval longer than the running window in which no shown run is active, as an idle gap. *(Row 11.)*

#### Answering assumptions from the board (deferred by D-22; the guards stay)

- **FR-131** **Deferred (D-22).** Where the answer write path is adopted by an accepted ADR, the page shall offer on each assumption row awaiting a human an *Accept* action and an *Override* action with an answer field and a note field.
- **FR-132** **Deferred (D-22).** Where the answer write path is adopted by an accepted ADR, when the owner submits an answer, the page shall save one answer record carrying the project id, the row id, the choice, the answer, the note, the time and the writer's identity.
- **FR-133** If a plan would contain a write to the `answers` collection, then the refresh script shall refuse the plan: exit non-zero, name the collection on stderr, and leave no pending plan. *(C-16; row 5 keeps it in PBI-001. Today `answers` is only an unmanaged collection that is never deleted (`Plan.test_unmanaged_collections_are_never_deleted`); the refusal is not built.)*
- **FR-134** If a request to the ingest endpoint carries an answer record, then the local server shall reject that record and store nothing from it. *(C-16; row 5 keeps it in PBI-016.)*

#### Backlog "Later" group (D-20; PBI-018)

- **FR-186** When the board exporter reads a spec with a `### Future iterations (not planned)` heading, it shall add each bullet under that heading to the backlog document as a `later` item. The item's title is the bullet's first bold span, and its description is the rest of the bullet with any leading colon removed. *(AC-L1.)*
- **FR-187** The Backlog tab shall show `later` items as a separate "Later" group of neutral idea cards below the work items. *(AC-L2.)*
- **FR-188** The page shall exclude `later` items from the work-item totals and from "Needs attention". *(AC-L2.)*
- **FR-189** If a project's spec has no Future iterations heading, then the board exporter shall add no `later` item and report no error. *(AC-L3.)*

#### Hardening follow-ups (rows 1 and 13; PBI-001, PBI-002)

- **FR-190** When the board exporter keeps a tab's last export (FR-153), it shall mark that tab document with `carriedSince`, the time the carry began. *(Row 13: "a `carriedSince` marker shown as a warning"; PBI-001.)*
- **FR-191** While a shown project tab carries `carriedSince`, the page shall show a warning on that tab stating that time. *(Row 13; PBI-002 "stale-tab callout".)*
- **FR-192** The page shall label the Dispatch token figure "reported tokens". *(Row 1; PBI-002 "token relabel".)*

## 5. Non-functional requirements

### Current tree (baseline)

- **NFR-1** While the refresher loop is active, the refresher shall start a tick every 10 minutes (the `/loop 10m` cadence). *(D-14; kept until the local app replaces the refresher, row 1.)*
- **NFR-2** The session exporter shall classify a run with no finish as `running` for at most 10 minutes after its agent transcript was last written (`runs.runningWindowMinutes` = 10). *(Met: `board.config.json`, FR-14, FR-15.)*
- **NFR-3** A session-exporter run with a warm parse cache and no transcript change shall complete within 0.2 s, as measured by the elapsed time the exporter prints. *(Commissioning figure: A-19.)*
- **NFR-4** The store shall hold no more than 5000 documents. The current contents are the sessions, runs, project and project-tab documents, the status documents, `catalogue/index` and the six retired leftovers, and PBI-021 removes the leftovers (row 4). *(C-4.)*
- **NFR-5** Every batch the refresh script prints shall contain at most 50 writes. *(Met: `Plan.test_batches_past_the_limit`; C-3.)*
- **NFR-6** With the default privacy settings (`showFirstPrompt` false, `exclude` empty), 0 session documents shall carry a `firstPrompt` field and 0 titles shall be derived from prompt text. *(Met: `Privacy.test_first_prompt_is_off_by_default`; D-8.)*
- **NFR-7** With `showFirstPrompt` on, a published `firstPrompt` shall be at most 200 characters long. It shall contain 0 matches of these redaction patterns:
  - `sk-` followed by 16 or more key characters;
  - `gh[pousr]_` followed by 20 or more letters or digits;
  - `AKIA` or `ASIA` followed by 16 upper-case letters or digits;
  - a run of 32 or more hexadecimal characters;
  - a run of 32 or more base64-style characters containing a digit, an upper-case and a lower-case letter;
  - the value after `password`, `passwd`, `pwd`, `token`, `secret` or `api key`/`api_key`/`api-key` followed by `=` or `:`.

  *(Met: `Privacy.test_first_prompt_when_on_is_redacted`, `Redact.test_patterns`. Titles, run labels, agent descriptions and skill ids are not covered: row 18.)*
- **NFR-8** Redaction shall leave text that matches no pattern in NFR-7 unchanged. *(Met: `Redact.test_ordinary_text_is_untouched`.)*
- **NFR-9** The page shall contain 0 hex, `rgb()` or `hsl()` colour literals outside its `:root` token blocks. The dark tokens sit on bare `:root`, and a light override applies under both `prefers-color-scheme: light` and `[data-theme="light"]`. *(Met: a search of `site/index.html` on 2026-09-11, after the catalogue tab, found hex colour literals only on lines 8–10, 15–17 and 22–24, all inside the `:root` token blocks (lines 6–25), and no `rgb()` or `hsl()` literal (AC-54). D-10.)*
- **NFR-10** The page shall use the `--human` violet only for elements that represent something awaiting a human. It shall use the semantic tokens `--live`, `--go`, `--changes` and `--nogo` for run and review states. *(Partly met: the brand dot is also `--human`. Row 13 settles the remedy (the brand dot stops using `--human`), which is planned in PBI-002.)*
- **NFR-11** The page shall set all text in one sans family (Schibsted Grotesk, falling back to the system sans) with tabular figures, and shall use IBM Plex Mono only for ids and commit hashes. *(Partly met. Row 13 settles the remedy (paths and branch names move to the sans face), which is planned in PBI-002. The fonts load from Google Fonts, which C-2 permits.)*
- **NFR-12** The page shall declare every animation inside `@media (prefers-reduced-motion: no-preference)`, and shall animate pipeline arrows, run glows and the header status dot only while an agent is running. *(Partly met: the arrows and run glows are met. Row 13 settles that the header dot pulses only while an agent runs; PBI-002.)*
- **NFR-13** The page shall render every summary figure in the status-tile language: a bordered tile with a 3 px coloured top bar, a label, a figure and one line of context (`.tile`, `.cell`). *(Met: inspection; the catalogue tiles use `tile()`; D-10.)*
- **NFR-14** The page shall pass 100% of store-derived text through `esc()` before inserting it into markup. Text lifted from repo documents goes through `md()` instead, which renders only code spans and bold. *(Met: inspection; page check "catalogue: descriptions are escaped and never rendered as markdown".)*
- **NFR-15** The page shall provide:
  - a keyboard-operable tab list (`role="tab"` and `role="tabpanel"`, Left/Right arrow, Home and End keys);
  - a visible focus outline on every button and on both pickers;
  - `role="img"` with an `aria-label` on every chart SVG.

  *(Met: inspection. No conformance level is stated: A-22.)*
- **NFR-16** The Python suite shall hold 197 `unittest` cases that use only the Python standard library. It shall pass with `python -m unittest discover -s tests`, and never touch the real `out/`, the real projects root, the real `~/.claude` or the live store. *(197 was first a search count of `def test_` methods across the four `test_*.py` files; the 2026-09-11 run reported "Ran 197 tests … OK": A-44. It was 82 on the v1 baseline.)*
- **NFR-24** The page suite `node tests/page.test.mjs` shall use 0 npm packages (node built-ins only) and exit 0 on the current `site/index.html`. *(`CLAUDE.md` Tests; the 2026-09-11 run reported "all 44 page checks passed" and exited 0, A-44.)*

### Next iteration: not built

- **NFR-17** Refreshing the board in the next iteration shall consume 0 Claude usage and require 0 open Claude Code sessions. *(D-16; PBI-007.)*
- **NFR-18** A change written to a transcript on the PC shall appear on an open page served by the local server within 10 minutes, without a reload. *(D-14; row 11 accepts 10 minutes.)*
- **NFR-19** In the on-PC deployment, the local server shall listen on 127.0.0.1 only: 0 listening sockets on any other address. *(D-24; ADR-0001 "bound to 127.0.0.1". Not applicable to the Unraid deployment: row 7.)*
- **NFR-20** 0 deployments shall place the local database file on a network share (SMB or NFS). The local server shall open the database only on storage local to the host it runs on. *(D-17; C-14.)*
- **NFR-21** Within 10 minutes of the owner logging on to Windows, with no Claude Code session open, the page served by the local server shall show sessions active in the last 7 days. *(D-14, D-15, D-16.)*
- **NFR-22** Every next-iteration view, and the Agent catalogue tab, shall meet NFR-9, NFR-10, NFR-13 and NFR-14, and shall use the `--human` violet only for "Waiting on you" items and assumptions awaiting a human. *(D-10; spec "every page PBI must meet the design rules".)*
- **NFR-23** **Deferred (D-22).** 0 answer records shall carry the identity of the refresher, the collector or any agent as their writer.

## 6. Constraints

- **C-1** In v1, only a Claude session writes the store, through the Artifact tool's `write_db`. The artifact's capability rule grants write to editors (`admin`) and read to viewers (`interact`). Claude writes with the owner's identity, so the store alone cannot prove that a human wrote a document. *(The brief's "How it stays live", lines 49–50, and its "Provenance" consideration under "Raised by the owner, 2026-09-11", lines 226–229; `board.config.json`.)*
- **C-2** The artifact's content security policy permits stylesheets from `https://fonts.googleapis.com` and font files from `https://fonts.gstatic.com`. It blocks every other network host, and fetch, XHR and WebSocket connections to any external host. No external database or service (for example the local server) can feed the page while it remains a claude.ai artifact. *(The brief's "How it stays live", lines 50–51.)*
- **C-3** A `write_db` batch accepts at most 50 writes. *(`refresh.py` `BATCH`.)*
- **C-4** An artifact's store holds at most 5000 documents. *(Commissioning task context.)*
- **C-5** All repositories and data live on the Windows filesystem under Windows paths. No WSL distro is installed, and globs must match either slash direction. *(D-2.)*
- **C-6** The v1 refresher's loop is a session-only cron. It stops when the refresher session closes, and it expires 7 days after it is created. *(The brief's known gap "The loop is not durable", lines 106–107.)*
- **C-7** A cloud routine cannot read the local transcripts, so the refresher, and in the next iteration the collector, must run on this computer. *(The brief's known gap "The loop is not durable", line 107; D-17.)*
- **C-8** The page is authored as page content only, with no `<html>`, `<head>` or `<body>`. A redeploy must first read the artifact, then publish with the same `url`, omitting `capabilities` and `favicon`. The local server must wrap the page (spec, PBI-005). *(`CLAUDE.md`.)*
- **C-9** A tracked build repo does not record per-work-item build state, so that state comes from the hand-kept `projects/<projectId>.json`. Until feature 4 it comes only from there, and during the shadow period that file sits beside the derived state (row 15). *(D-4; `CLAUDE.md` Projects.)*
- **C-10** No session reports to the board. Transcripts that Claude Code writes under the projects root are the only source of sessions and runs. *(D-4.)*
- **C-11** Code changes are built by `engineering-agents:code-writer` under TDD and reviewed by `review-agents:code-reviewer` until GO. *(D-9, D-26.)*
- **C-12** Deleting store documents needs the owner's go-ahead. Routine refresh deletes of previously pushed documents continue under the mass-delete guard. *(D-11; scope settled by row 14.)*
- **C-13** The automated tests use only the Python standard library and node built-ins. *(`CLAUDE.md`.)*
- **C-14** The local server and the collector must not read or write the local database over a network share, because SQLite locking over SMB/NFS is unreliable. *(D-17; row 24.)*
- **C-15** Transcripts exist only on the PC running Claude Code. In the Unraid deployment the collector sends records to the server over the LAN, in the same ingest-API shape as a cloud host. *(D-17.)*
- **C-16** Plan-gate answers must be human. The refresher, the collector and every agent must never write answer records, and the refresh script refuses the `answers` collection (FR-133). `CLAUDE.md` gains the rule "no agent writes answers or calls an answers endpoint" (PBI-001). If the answer path is ever revived, only the page records answers, stamped with the viewer's identity. *(The brief's "Provenance" consideration under "Raised by the owner, 2026-09-11", lines 226–229; row 5.)*
- **C-17** The answer write path would reverse the rule "the page never writes" (FR-64). D-22 defers it. Reviving it needs an accepted ADR and the deferred former PBI-015. *(The brief's ADR consideration under "Raised by the owner, 2026-09-11", line 230; row 5.)*
- **C-18** The store adapter is the only adapter usable from the artifact, because C-2 blocks connections to the local server. The local API adapter is usable only from the page as served by the local server. *(Derived from C-2 and D-16.)*
- **C-19** Build sessions run from `C:\Users\jdk`, not from a project's repository folder, so a session can be tied to a project only by listing it in `board.config.json`. *(D-18.)*
- **C-20** `projects/*.json` is never deleted. Retiring the hand-kept build state is a later owner decision. *(Row 15; spec, PBI-010 "never delete a data file".)*
- **C-21** The local app under `local/`, and the shared derivation under `exporters/` that it imports, use the Python standard library only: `sqlite3` in WAL mode, a threaded `http.server`, and Server-Sent Events for live push. The default port is 8765. *(D-24; row 8; ADR-0001.)*
- **C-22** The agent catalogue under `~/.claude/plugins` is read and never written. Only the agent-catalog marketplace and the installed-plugins file are read. *(Spec scope; `CLAUDE.md`; row 19.)*
- **C-23** Every PBI needs a pull request, and no agent merges one; merges are the owner's. *(D-26; spec metadata `pr_required: true`, `merge_allowed_by_agent: false`.)*

## 7. Acceptance criteria

The inputs gave no acceptance criteria when this PRD was first drafted. Row 16 has since confirmed that each PBI's criteria are this PRD's ACs for its requirements (formerly A-18).
- **AC-1 to AC-47** restate behaviour an existing named test checks, and are re-baselined here to the current tests.
- **AC-48 to AC-56** are checked by demonstration or inspection.
- **AC-57 to AC-62** gate the requirements not yet met.
- **AC-63 to AC-93** gate the next iteration and the project-first work. Of these, AC-84, AC-85 and AC-89 to AC-93 now gate shipped behaviour.
- **AC-94 to AC-109** gate the as-built Agent catalogue and project-first detail, anchored to named tests.
- **AC-110 to AC-128** gate the next-iteration additions of revision 3. They are derived from ledger rows and spec criteria.

### Session export and classification

- **AC-1** When the session exporter runs over one session whose code-writer finished by notification with `subagent_tokens` 5000 and `duration_ms` 1740000, it shall write exactly one session document and a run of kind `done` with `tok` 5000 and `min` 29. *(`Pipeline.test_basic_export`.)*
- **AC-2** When the session exporter runs with `sessions.days` 3, it shall write `windowDays` 3 on the session document, and when it runs with `runs.runningWindowMinutes` 25, it shall write `windowMinutes` 25. *(`Pipeline.test_window_days_on_the_session_doc`, `test_window_minutes_on_the_session_doc`.)*
- **AC-3** When one agent's meta file is truncated, the session exporter shall export that agent's run with lane `other` and export the session's code-writer run with lane `cw`. *(`Malformed.test_truncated_meta_falls_back_to_empty`.)*
- **AC-4** When a run named by a TaskStop is followed by the platform's `killed` notification, the session exporter shall classify it as kind `killed` with verdict `stopped`. *(`Classify.test_stop_echo_notification_keeps_stopped`.)*
- **AC-5** When a run named by a TaskStop later completes with the result `Verdict: GO`, the session exporter shall classify it as kind `go` with verdict `GO`. *(`Classify.test_stopped_then_resumed_and_completed`.)*
- **AC-6** When a run's last reply contains "You've hit your session limit", the session exporter shall classify it as kind `killed` with verdict `killed · rate limit`. *(`Classify.test_rate_limit`.)*
- **AC-7** When a code-reviewer's result reads "Round 1 Verdict: NO-GO. … Verdict: GO-WITH-NOTES", the session exporter shall record verdict `GO-WITH-NOTES` and kind `go`. *(`VerdictOf.test_rereview_quoting_an_earlier_verdict_takes_the_last_label`, `KindOf.test_review_lanes`.)*
- **AC-8** When a code-writer's result reads "Verdict: NOT-DONE … once fixed it will be Verdict: DONE", the session exporter shall record verdict `NOT-DONE` and kind `changes`. *(`VerdictOf.test_builders_keep_the_leading_token`, `KindOf.test_not_done_is_changes_on_build_lanes`.)*
- **AC-9** When a code-reviewer run completes with a result containing no verdict token, the session exporter shall record kind `done` and verdict `finished`. *(`Classify.test_completed`.)*
- **AC-10** When a run has no finish and its agent transcript was last written 60 s ago under a 600 s running window, the session exporter shall classify it as kind `running`. *(`Classify.test_running_window`.)*
- **AC-11** When a run has no finish and its agent transcript was last written 900 s ago under a 600 s running window, the session exporter shall classify it as kind `killed` with verdict `no result`. *(`Classify.test_running_window`.)*
- **AC-12** When a foreground code-writer returns `DONE` inline with 77 total tokens and 240000 ms, the session exporter shall write a run with kind `done`, verdict `DONE`, `tok` 77 and `min` 4. *(`Pipeline.test_inline_result`.)*
- **AC-13** When a finish reports `subagent_tokens` "12k" and `duration_ms` "soon", the session exporter shall write `tok` 1160 (the last response's context size) and `min` 19 (launch to finish). *(`Malformed.test_malformed_numeric_tags`.)*

### Links between runs

- **AC-14** When a code-writer finishes `NOT-DONE` and a code-reviewer run follows it, the session exporter shall write no `from` on the review run. *(`Pipeline.test_not_done_builder_is_changes_and_does_not_hand_off`.)*
- **AC-15** When a code-writer fix run for PBI-001 starts after a PBI-001 code-reviewer run of kind `changes`, the session exporter shall set the fix run's `feeds` to that review run. *(`Link.test_fix_is_fed_by_the_review`.)*
- **AC-16** When code-writer runs launch at minutes 0, 1 and 10, the session exporter shall give the first two runs group `A` and the third run no group. *(`Link.test_parallel_group`.)*
- **AC-17** When a PBI-001 plan-lane run of kind `go` ends before a PBI-001 code-writer run starts, the session exporter shall set the code-writer run's `from` to that plan-lane run. *(`Link.test_builder_comes_from_the_plan_gate`.)*

### Privacy

- **AC-18** When one of two sessions has working folder `C:\work\secret-app` and `sessions.exclude` is `["C:/work/secret*"]`, the session exporter shall export only the other session and only its run. *(`Privacy.test_exclude_by_cwd`.)*
- **AC-19** When a session's project folder matches an `exclude` glob, the session exporter shall leave that session's id out of `out/.cache/sessions.json`. *(`Privacy.test_excluded_sessions_are_not_cached`.)*
- **AC-20** When the session exporter runs with default privacy settings over a session whose first prompt is "Please build the widget", it shall write no `firstPrompt` field and a title that does not contain "widget". *(`Privacy.test_first_prompt_is_off_by_default`.)*
- **AC-21** When `sessions.showFirstPrompt` is on and the first prompt holds seven secrets, the session exporter shall publish a `firstPrompt` and a title that contain none of the seven values. The seven are an `sk-` key, a `ghp_` token, an `AKIA` key, a 34-character hex run, a 44-character base64 run, a `password=` value and a `token=` value. *(`Privacy.test_first_prompt_when_on_is_redacted`.)*
- **AC-22** When the text "Refactor the session picker so the 7-day window is configurable; see PBI-010 and commit 2a8ce40." is redacted, the session exporter shall return it unchanged. *(`Redact.test_ordinary_text_is_untouched`.)*

### Failure isolation

- **AC-23** When one agent transcript path is unreadable, the session exporter shall exit 0, export the session's other run, and name the unreadable agent on stderr. *(`Malformed.test_unreadable_subagent_is_skipped_with_a_warning`.)*
- **AC-24** When a previously exported, finished agent's file raises a permission error on re-read, the session exporter shall keep that run with kind `done` and `tok` 5000. *(`Malformed.test_agent_that_cannot_be_reread_keeps_its_last_row`.)*
- **AC-25** When one agent read fails once and nothing on disk then changes, the session exporter shall export that agent's run on the following run, giving the session `runs` 2. *(`Malformed.test_transient_agent_read_error_does_not_drop_the_run_for_good`.)*
- **AC-26** When a session's parse raises an error and an earlier parse is cached, the session exporter shall keep that session and its run in the export, and shall export the new activity on the following run. *(`Malformed.test_failed_parse_keeps_the_previous_result`.)*
- **AC-27** When one of two sessions' parse raises an error and no parse of it is cached, the session exporter shall export only the other session. *(`Malformed.test_failed_parse_without_a_cached_result_omits_the_session`.)*
- **AC-28** When the projects root is missing after a successful export, the session exporter shall exit non-zero and leave the earlier session documents in `out/`. *(`Discovery.test_missing_projects_root_fails_and_keeps_the_last_export`.)*
- **AC-29** When a project's `sessions` names a session id with no main transcript, the session exporter shall exit non-zero and print that id on stderr. *(`Projects.test_linked_session_without_a_transcript_fails`; `Discovery.test_missing_build_transcript_fails` for the older shape.)*

### Cache and file writes

- **AC-30** When the session exporter runs twice with no transcript change, it shall parse the session on the first run and parse nothing on the second. *(`Cache.test_reused_when_nothing_changed`.)*
- **AC-31** When a line is appended to a session's main transcript between runs, the session exporter shall parse that session again. *(`Cache.test_invalidated_by_a_transcript_change`.)*
- **AC-32** When `runs.runningWindowMinutes` changes from 10 to 60 for an unfinished agent whose transcript was last written 30 minutes ago, the session exporter shall change that run's kind from `killed` to `running` without any transcript change. *(`Cache.test_running_window_change_applies_without_a_transcript_change`.)*
- **AC-33** When writing a non-serialisable object fails, the file writers of the session exporter and the refresh script shall leave the previous file content intact and no temporary file behind. *(`WriteJson.test_a_failed_write_keeps_the_previous_file`, `Save.test_a_failed_write_keeps_the_previous_file`.)*

### Refresh script

- **AC-34** When the refresh script plans a fresh `out/` holding one project (status document `meta/status`) with its five tabs, two sessions (one linked, one not) and four runs, it shall plan 12 `set` writes and one `update` of `meta/status`. *(`Plan.test_first_plan_sets_everything_and_the_status`. The counts rise by one when FR-103 is built: row 12.)*
- **AC-35** When a plan has been committed and only `generatedAt` then changes in `projectTabs/p.spec`, the refresh script shall plan only the `meta/lastRefresh` write. *(`Plan.test_generated_at_alone_is_not_a_change`. Reworded 2026-09-12: before PBI-008 built FR-103's refresher half, this read "shall report nothing to push"; the test now asserts the quiet-tick plan.)*
- **AC-36** When one pushed run is no longer exported, the refresh script shall plan exactly one `delete`, for that run. *(`Plan.test_vanished_run_is_deleted`.)*
- **AC-37** When all four pushed runs vanish from the export, the refresh script shall exit non-zero, name `--allow-mass-delete` on stderr, print nothing on stdout, and leave no pending plan. *(`Cli.test_mass_delete_exits_non_zero_without_the_flag`, `MassDelete.test_more_than_half_is_refused`.)*
- **AC-38** When both sessions vanish from an export whose pushed state holds 16 runs and sessions, the refresh script shall refuse the plan even though only 2 documents would be deleted. *(`MassDelete.test_zero_sessions_refused_even_for_a_small_delete`.)*
- **AC-39** When the same four runs vanish and `--allow-mass-delete` is given, the refresh script shall plan their deletes and leave a pending plan. *(`MassDelete.test_allowed_with_the_flag`.)*
- **AC-40** When an exporter reports a failure, the refresh script shall exit 1, echo the failure on stderr, and leave no pending plan. *(`Cli.test_export_failure_stops_before_planning`.)*
- **AC-41** When `refresh.py --commit` is run with no pending plan, the refresh script shall exit 1 and print `nothing pending` on stderr. *(`Cli.test_commit_without_pending`.)*
- **AC-42** When only an unlinked session's title changes, the refresh script shall plan exactly one `set`, of that session, and no status update. *(`UpdatedAt.test_unlinked_session_change_does_not_bump`. The count rises when FR-103 is built: row 12.)*
- **AC-43** When an unlinked session's run becomes `running`, the refresh script shall plan `live` false and no status update. *(`UpdatedAt.test_running_unlinked_run_does_not_bump`.)*
- **AC-44** When a linked session's run is deleted, the refresh script shall plan that `delete` plus an `update` of that project's status document. *(`UpdatedAt.test_deleted_linked_run_bumps`. The count rises when FR-103 is built: row 12.)*
- **AC-45** When a linked session's run becomes `running`, the refresh script shall write `live` true and an `updatedAt` into the project's status document under `out/`. *(`UpdatedAt.test_live_flip_bumps`, `ProjectStatus.test_live_is_per_project`.)*
- **AC-46** When 60 new runs are added to the AC-34 fixture, the refresh script shall print 2 batches, the first holding exactly 50 writes. *(`Plan.test_batches_past_the_limit`.)*
- **AC-47** When `python -m unittest discover -s tests` is run from the repository root on the current tree, the suite shall report 197 tests run with no failures and no errors. *(NFR-16; the 2026-09-11 run reported "Ran 197 tests … OK": A-44.)*

### Refresher and page (demonstration and inspection)

- **AC-48** When a tick's `write_db` call fails, the refresher shall leave `out/.pending.json` in place and `out/.pushed.json` unchanged, so that the next tick offers the same writes again. *(FR-61; demonstration.)*
- **AC-49** ~~When a tick's refresh script prints `nothing to push`, the refresher shall make no `write_db` call in that tick. *(FR-59; demonstration against the refresher's transcript.)*~~ **Superseded 2026-09-12 with FR-59.** That output no longer occurs; the equivalent check is that a tick whose plan a guard refuses makes no `write_db` call.
- **AC-50** When `site/index.html` is inspected, it shall contain no call that sets, updates, adds or deletes a store document. *(FR-64; inspection. In force: D-22.)*
- **AC-51** **Superseded by AC-85 and AC-107.** When a non-build session is selected on the published page, the page shall hide the Spec, Assumptions, Decisions, Backlog and GitHub-details tabs.
- **AC-52** When the page runs where `window.claude.use` is undefined, such as a local file preview, the page shall show "This view cannot reach the live store" and no session data. *(FR-77; demonstration.)*
- **AC-53** When a session document changes in the store while the page is open, the page shall show the change without a reload. *(FR-65; demonstration.)*
- **AC-54** When `site/index.html` is searched for hex, `rgb()` and `hsl()` colour literals, the search shall find matches only inside the `:root` token blocks. *(NFR-9; inspection.)*
- **AC-55** When `site/index.html` is inspected, every `@keyframes` and `animation` declaration shall sit inside `@media (prefers-reduced-motion: no-preference)`. *(NFR-12; inspection.)*
- **AC-56** When the session exporter runs a second time with no transcript change on the owner's machine, it shall print an elapsed time of 0.2 s or less. *(NFR-3; demonstration.)*

### Requirements not yet met

- **AC-57** When a carried-over row of kind `running` belongs to an agent that cannot be re-read, and the running window has elapsed since the row's `end` time, the session exporter shall export that row with kind `killed` and verdict `no result`. *(FR-80.)*
- **AC-58** When one agent transcript holds a response whose `usage.output_tokens` is a string, the session exporter shall still export that session and every one of its runs. *(FR-81.)*
- **AC-59** When `sessions.showFirstPrompt` is the string `"false"`, or `sessions.exclude` is a string rather than a list, the session exporter shall exit with status 2 and an error naming that key. *(FR-82; row 13.)*
- **AC-60** When the running window of a session selected under "Other sessions" elapses with no store change, the page shall show "session idle" in the Overview's "Running now" tile within 60 s of the header showing `Idle`. *(FR-83.)*
- **AC-61** When a verifier run completes with a result stating `exercised`, the session exporter shall record verdict `exercised`. *(FR-84.)*
- **AC-62** When the published page is opened in Chrome 20 times in a row, each time in a fresh tab, the page shall render its app bar and Overview panel on every load without a reload. *(FR-85; row 13.)*

### Next iteration and project-first navigation

- **AC-63** When one line is appended to a transcript the collector has already read, the collector shall read from that file only the bytes of the appended line. *(FR-86.)*
- **AC-64** When the collector and the session exporter process the same synthetic transcripts used by `tests/`, the collector shall produce session, run and project records equal to the exporter's documents, ignoring `generatedAt`. *(FR-87. Whichever of PBI-019 and a feature PBI lands second extends this fixture.)*
- **AC-65** When the owner logs on to Windows with no Claude Code session open, the page at the local server's address shall show the sessions active in the last 7 days within 10 minutes. *(FR-90, FR-91, NFR-17, NFR-21; demonstration.)*
- **AC-66** When the listening sockets of the on-PC local server are listed (for example with `netstat -ano`), the list shall show the server bound to 127.0.0.1 only. *(NFR-19; inspection.)*
- **AC-67** When the local-database path is configured as `\\nas\share\board.db`, the local server shall refuse to start and print that path. *(FR-96.)*
- **AC-68** When a finish is appended to a running agent's transcript while the page served by the local server is open, the page shall show the run's new kind within 10 minutes without a reload. *(FR-94, NFR-18; demonstration.)*
- **AC-69** When the page requests the data snapshot, every record returned shall conform to the record shapes. *(FR-93, FR-100.)*
- **AC-70** When the collector and local-server source is searched, it shall contain no invocation of the `claude` command and no request to an Anthropic API host. *(NFR-17; inspection.)*
- **AC-71** When the Unraid container's volume mapping is inspected, the local database shall be mapped to a path on the Unraid server's own storage, not to a mounted SMB or NFS share. *(NFR-20, C-14; inspection.)*
- **AC-72** When the collector on the PC records a new run in the Unraid deployment, the page served from the Unraid server shall show that run within 10 minutes. *(FR-89, NFR-18; demonstration.)*
- **AC-73** When the page is loaded from the local server, it shall request the data snapshot from the local server, and when it is loaded as the artifact, it shall open store subscriptions. *(FR-98, FR-99.)*
- **AC-74** When the last-refresh time is 25 minutes old, the page shall show the "data as of" text in the `--changes` amber token with the word "stale", and when it is 5 minutes old, the page shall show it without that styling. *(FR-104, FR-105.)*
- **AC-75** When a session's last assistant turn asks the owner a question and no owner message follows it, the "Waiting on you" panel shall list that session. *(FR-106, FR-107.)*
- **AC-76** When a transcript records an action refused by the permission check, the "Waiting on you" panel shall list that refusal with its session. *(FR-106, FR-109.)*
- **AC-77** When round 1 of a PBI-001 review lists findings F1, F2 and F3 and round 2 lists only F2, the findings ledger shall show F1 and F3 resolved, F2 open, and 2 rounds so far. *(FR-111, FR-112.)*
- **AC-78** When the latest code-reviewer run naming PBI-001 in a platform-catalogue linked session has verdict `GO` and no hand-kept build state lists PBI-001, the platform-catalogue Backlog shall show PBI-001 as done. *(FR-113.)*
- **AC-79** When a code-writer run's result contains "664 tests green", the collector shall record test count 664 on that run. *(FR-114.)*
- **AC-80** When no usage-limit hit is recorded, the page shall show "no forecast: no limit hit recorded", and when at least one is recorded, the page shall show a time labelled as an estimate. *(FR-117, FR-118.)*
- **AC-81** When two runs of one project naming PBI-001 have effective usage 100 and 50, the page shall show 150 for that project's PBI-001. *(FR-119.)*
- **AC-82** When the owner selects a code-reviewer run, the page shall show that run's verdict summary, findings, files touched and duration. *(FR-121; demonstration.)*
- **AC-83** When two runs ran from 10:00 to 10:20 and from 10:05 to 10:30, the timeline shall draw their bars overlapping between 10:05 and 10:20. *(FR-122.)*
- **AC-84** When the page is shown at a viewport width of 1050 px, the page shall show the "Claude usage" tab label in full or show a visible overflow cue. *(FR-125, FR-128; demonstration. Demonstrated as met under AC-R3 on 2026-09-11: A-41.)*
- **AC-85** When the dispatch-board project is selected, the page shall show the Overview, Spec, Assumptions, Decisions, Backlog, GitHub, Dispatch, Agent catalogue and Claude usage tabs. *(FR-129; page check "project view shows every project tab…"; demonstrated as met under AC-R3 on 2026-09-11: A-41. Replaces AC-51.)*
- **AC-86** When the refresh script is given an export that includes an `answers` document, it shall exit non-zero, name the `answers` collection on stderr, and leave no pending plan. *(FR-133.)*
- **AC-87** **Deferred (D-22).** Where the answer write path is adopted, when the owner accepts the default of an assumption row, the page shall save one answer record with that project id, row id, choice *Accept*, a time and the writer's identity.
- **AC-88** When an ingest request carries an answer record, the local server shall reject it, and the data snapshot shall contain no answer from that request. *(FR-134.)*
- **AC-89** When `board.config.json` lists two projects, the session exporter shall write their `projects` documents with `order` 0 and 1. *(FR-135, FR-139; `Projects.test_project_usage_combines_its_sessions`.)*
- **AC-90** When a linked session was last active 30 days ago, the session exporter shall still export it, with `project` set to its project's id. *(FR-137, FR-138; no named test identified: A-45.)*
- **AC-91** When `projects/platform-catalogue.json` is not valid JSON, the board exporter shall exit non-zero and the refresh script shall print no plan. *(FR-142; `ExportProject.test_malformed_data_file_stops_the_export_and_keeps_the_last_one`, FR-51.)*
- **AC-92** When a project with two linked sessions is selected and the session filter names one of them, the page shall list in Dispatch only that session's runs. *(FR-145, FR-146; page check "session filter narrows Dispatch and usage to one session…"; demonstrated as met under AC-R3 on 2026-09-11: A-41.)*
- **AC-93** When a selected project's spec file does not exist, the page shall show the Spec tab's "not exported yet" state. *(FR-140, FR-148; page check "dispatch-board without spec/backlog shows the existing empty states". Restated because dispatch-board now has a spec.)*

### Current tree: Agent catalogue and project-first detail

- **AC-94** When the catalogue exporter runs against a synthetic marketplace holding agent and skill files, it shall write one `catalogue/index` entry per file, each carrying `kind`, `plugin`, `name`, `description` and `installed`. *(FR-161; `Export.test_every_agent_and_skill_is_one_entry`.)*
- **AC-95** When the marketplace folder is missing and an earlier export exists, the catalogue exporter shall leave `out/catalogue/index.json` unchanged. *(FR-164; `Failures.test_missing_marketplace_keeps_the_last_export`.)*
- **AC-96** When a `catalogue` value in the config is not a string, the catalogue exporter shall exit with status 2. *(FR-166; `Failures.test_a_config_type_error_exits_2`.)*
- **AC-97** When a plan would delete `catalogue/index`, the refresh script shall refuse it unless `--allow-mass-delete` is given. *(FR-49; `Catalogue.test_deleting_the_catalogue_is_refused`.)*
- **AC-98** When the refresh script runs, it shall run the board, session and catalogue exporters in that order. *(FR-160; `Export.test_the_three_exporters_run_in_order`.)*
- **AC-99** When a main transcript holds a `Skill` tool call and a typed `/<plugin>:<skill>` command, the session exporter shall count both in that session's `skillUses`. *(FR-168; `CatalogueUsage.test_skill_calls_and_typed_plugin_commands_are_counted`.)*
- **AC-100** When a project is selected, the page shall show the Agent catalogue tab directly after Dispatch and before Claude usage. *(FR-169; page check "catalogue: the Agent catalogue tab sits straight after Dispatch, before Claude usage".)*
- **AC-101** When "Other sessions" is selected, the page shall keep the Agent catalogue tab and base its current-view figures on the chosen session. *(FR-169, FR-174; page check "catalogue, Other sessions: the tab stays, and follows the chosen session".)*
- **AC-102** When a catalogue entry has no use in the current view, the page shall show "never used" for it. *(FR-171; page check "catalogue: never used in the view…".)*
- **AC-103** When an agent type seen in use is not in the catalogue, the page shall list it in the "Outside the catalogue" panel. *(FR-173; page check "catalogue: ids outside the catalogue get their own final panel…".)*
- **AC-104** When the Agent catalogue tab is shown in a project view, each summary tile shall show the view's count out of the catalogue total, with the all-sessions count beside it. *(FR-172; page check "catalogue, project view: tiles give the view figure, the all-sessions figure beside it…".)*
- **AC-105** When no view is saved and no project is live, the page shall select the first project. *(FR-156; page check "no saved view and no live project: the first project".)*
- **AC-106** When a saved project and a saved session filter exist, the page shall restore both on load. *(FR-156, FR-157, FR-79; page check "saved project and saved session filter are restored…".)*
- **AC-107** When "Other sessions" is selected while the Spec tab is selected, the page shall hide the five project tabs and select Overview. *(FR-158, FR-159; page check "Other sessions: project tabs hidden, Spec falls back to Overview…". Replaces AC-51 with AC-85.)*
- **AC-108** When a project's `repoPath` goes missing after a successful export, the board exporter shall keep that project's tabs unchanged while the other projects refresh. *(FR-143, FR-153; `MissingSources.test_missing_repo_keeps_its_last_tabs_while_others_refresh`.)*
- **AC-109** When `node tests/page.test.mjs` is run from the repository root on the current tree, it shall exit 0. *(NFR-24; met by the 2026-09-11 run, which exited 0: A-44.)*

### Next iteration: additions in revision 3

- **AC-110** While the shadow period is active, when PBI-001's derived state is done and its hand-kept state is `partial`, the Backlog shall show both states and flag PBI-001. *(FR-175.)*
- **AC-111** When a work item has a hand-kept `review` value, the Backlog tab shall show that value in place of the derived review summary. *(FR-176.)*
- **AC-112** When a request reaches the on-PC local server with Host header `attacker.example`, the local server shall reject it and return no board data. *(FR-177.)*
- **AC-113** When a POST request reaches the local server with Origin `https://attacker.example`, the local server shall reject it. *(FR-178.)*
- **AC-114** When the local server's responses are inspected, none shall carry an `Access-Control-Allow-Origin` header. *(FR-179; inspection.)*
- **AC-115** When the collector's database path is configured as `\\nas\share\board.db`, the collector shall refuse to start and print that path. *(FR-180.)*
- **AC-116** When `board.config.json` is searched after the Unraid deployment is configured, the search shall find no ingest secret. *(FR-181; inspection.)*
- **AC-117** Where the Unraid deployment is used, when an ingest request carries no shared secret, the local server shall reject it, and the data snapshot shall contain nothing from that request. *(FR-182.)*
- **AC-118** When the local server's routes are listed, the list shall contain no route that accepts answer records. *(FR-183; inspection.)*
- **AC-119** When a collector pass would delete more than half of the stored runs and sessions other than by age pruning, the collector shall apply none of that pass's deletions. *(FR-184.)*
- **AC-120** When an unlinked session's last activity is 8 days old, the collector shall delete that session's records from the local database. *(FR-185.)*
- **AC-121** When a linked session's last activity is 30 days old, the collector shall keep that session's records in the local database. *(FR-185.)*
- **AC-122** When a spec's Future iterations heading holds the bullet "**Phone notifications**: a review returns NO-GO", the board exporter shall add a `later` item titled "Phone notifications" with the description "a review returns NO-GO". *(FR-186; AC-L1.)*
- **AC-123** When a project's backlog holds three work items and two `later` items, the Backlog tab shall show the two `later` items in a "Later" group below the work items. *(FR-187; AC-L2.)*
- **AC-124** When platform-catalogue's spec has no Future iterations heading, the board exporter shall add no `later` item and exit 0. *(FR-189; AC-L3.)*
- **AC-125** When the board exporter keeps a project tab from an earlier export, it shall write `carriedSince` on that tab document. *(FR-190.)*
- **AC-126** When a shown project tab carries `carriedSince`, the page shall show a warning on that tab stating that time. *(FR-191.)*
- **AC-127** When the Dispatch tab is shown, the page shall label the token figure "reported tokens". *(FR-192.)*
- **AC-128** When a project's backlog holds three work items and two `later` items, the page shall count 3 work items in the Backlog totals. *(FR-188; AC-L2.)*

## 8. Assumptions and open questions

Each open row records a gap the inputs left, the default chosen, and the impact if that default is wrong. No open row carries *none — decision pending* in revision 3, because every explicitly undecided choice in revision 2 was settled by the owner at the plan gate (D-21 to D-25).

**Rows settled by the approved spec's ledger in revision 3.** These are kept for traceability and not counted as open rows. Each one cites the ledger row that settles it.

| ID | Former gap | Settled by | Settlement |
|---|---|---|---|
| **A-2** | Unredacted titles, folders, run labels and agent descriptions | **Row 18** | Only the owner views the board; redaction beyond first prompts stays out of scope (S-17). |
| **A-5** | The v1 loop writes every tick; slower idle cadence undecided | **Row 1** | Keep the 10-minute every-tick loop until the local app replaces the refresher (up to 144 small writes a day until PBI-007). |
| **A-6** | Two token figures disagree | **Row 1** | Dispatch keeps `subagent_tokens`, relabelled "reported tokens" (FR-192); cost per work item uses effective usage (FR-119). |
| **A-8** | A snapshot of build data in a public repo | **Row 3** | The repo is private (D-21); `snapshot/` stays. Git history from before the switch was public. |
| **A-9** | Store leftovers | **Row 4** | PBI-021: confirm the published page is project-first, export the six documents to `snapshot/tabs/`, then delete them only with the owner's recorded approval (AC-S1 to AC-S3; S-34). |
| **A-10** | Scope of D-11 against routine refresh deletes | **Row 14** | D-11 covers leftovers and deletes outside the refresh procedure; routine deletes continue under the mass-delete guard (C-12). |
| **A-11** | Verifier outcome and kind | **Row 13** | The PRD remedy stands: FR-84 records the word, and the kind stays `done`. |
| **A-12** | Remedies for the four open review LOWs | **Row 13** | The PRD remedies for FR-80 to FR-83, planned in PBI-001 and PBI-002. |
| **A-13** | Blank load in Chrome | **Row 13** | A time-boxed investigation (PBI-002); AC-62 stays the check. |
| **A-15** | Monospace beyond ids and hashes | **Row 13** | Paths and branch names move to the sans face (NFR-11; PBI-002). |
| **A-16** | Violet and motion outside the written rules | **Row 13** | The brand dot stops using `--human`; the header dot pulses only while an agent runs (NFR-10, NFR-12; PBI-002). |
| **A-18** | No stated acceptance criteria | **Row 16** | Each PBI's criteria are this PRD's ACs for its requirements; the spec's own criteria cover PBI-017, PBI-018, PBI-021 and PBI-022. |
| **A-20** | Hand-kept build state drifts | **Row 15** | Derived state is shown beside the hand-kept state in a shadow period; `review`, `open` and `commit` stay as overrides; `projects/*.json` is never deleted; retirement is a later owner decision (FR-175, FR-176, C-20, S-39). Row 15 does not name A-20; this document maps it. The `scripts/export-board.py` path noted in revision 2 no longer appears in `site/`, `exporters/` or `projects/` (search). |
| **A-21** | No backlog-delivery rails in this repo | **Row 17** | `backlog-delivery.config` in the repo root; the BOARD, PBI files and done-log under `docs/backlog/`; `docs/adr/` holds ADR-0001. |
| **A-25** | Answering assumptions from the board | **Row 5** | "Not now" (D-22). Deferred to Future iterations; the guards FR-133, FR-134 and C-16 stay. |
| **A-26** | Deployment target | **Row 6** | On-PC first (PBI-007); Unraid (PBI-016) last and optional (D-23). |
| **A-27** | Unraid network exposure and authentication | **Row 7** | The page is served on the LAN without login; the Host allow-list is extended to the Unraid LAN name and address; the ingest secret comes from an environment variable or a git-ignored file; there is no answers endpoint (FR-177, FR-181 to FR-183). |
| **A-28** | Answer provenance on the local server | **Row 9** | Not applicable: no answers endpoint is built (row 5). |
| **A-29** | Local server interface details | **Row 8** | Python stdlib, `sqlite3` WAL, threaded `http.server`, SSE, port 8765, the record shapes in PBI-003, the v1 artifact and refresher kept until the owner retires them; ADR-0001 accepted (D-24, C-21). |
| **A-30** | "Waiting on you" detection signals | **Row 10** | PBI-009's spec confirms the transcript record types against real transcripts before any detector is built. |
| **A-31** | Findings ledger rules | **Row 11** | The PRD defaults as written. |
| **A-32** | Work-item status mapping | **Row 11** | The PRD defaults as written. |
| **A-33** | Parsing and attribution rules for features 5, 7, 8, 9 | **Row 11** | The PRD defaults as written. |
| **A-34** | Usage limit forecast method | **Row 11** | The PRD default as written; the forecast is labelled an estimate. |
| **A-35** | Freshness of the local push; stale threshold | **Row 11** | NFR-18 at 10 minutes; FR-105 at exactly 20 minutes. |
| **A-36** | Retention with no archive | **Row 12** | The local database keeps the last 7 days plus linked sessions, pruned by age only (FR-185); history of unlinked sessions is lost by design (D-15). |
| **A-37** | The last-refresh write changes v1 plan counts | **Row 12** | One extra write per tick; the affected ACs and tests are updated when FR-103 is built. |
| **A-39** | D-18's effect on the next iteration | **Row 12** | Records are keyed by project id plus row or PBI id; the project record is in the record shapes. |

**Rows resolved earlier or closed by this revision** (not counted as open):
- **A-1** was settled by D-12 in revision 2.
- **A-3** was settled by D-13, then D-18, in revision 2.
- **A-4** was settled by D-14 and D-16 in revision 2.
- **A-7** was settled by D-15 in revision 2.
- **A-14** was resolved by the corrected C-2 in revision 2.
- **A-24** (tab visibility) was settled by D-18 in revision 2. Its defect half, the tab-bar overflow, is resolved by **row 2** (FR-125 to FR-128 met).
- **A-38** (moving baseline) is **closed by this revision**. D-18 shipped (`2742ca6`), Part A now describes the current tree, and the D-18 default selection is stated (FR-156, FR-157). No ledger row covers it; the evidence limits it left behind were carried by A-44, since settled by the 2026-09-11 suite runs, and A-45.

**Rows resolved by other PBI-022 work (2026-09-11).** These were open when revision 3 was written. They are kept for traceability and not counted as open rows. Each keeps its original gap text and cites the evidence that resolves it.

| ID | Former gap | Settled by | Settlement |
|---|---|---|---|
| **A-40** | **Brief line 16 still reads "public on GitHub", and brief decision 1 still reads public.** The spec's and PBI-022's AC-R2 include correcting that line, but this revision was restricted to writing the PRD only. | **`docs/brief/raw-notes.md`** (PBI-022) | The brief's "What exists today" heading (line 16) now reads "private on GitHub jdk-official/dispatch-board since 2026-09-11". Decision 1 is marked "Superseded 2026-09-11" (the owner's answer "Make the repo private"). The question "Is the snapshot of build data in a public repo acceptable long term?" has moved from "Open questions still unanswered" to "Owner's answers (2026-09-11)", citing row 3 (CONFIRMED). The brief now agrees with D-21. Evidence: `git diff -- docs/brief/raw-notes.md`. |
| **A-41** | **AC-R3 evidence.** Demonstration evidence for AC-84, AC-85 and AC-92 under `docs/backlog/evidence/` was not written by this revision, because it lies outside the one-file write. | **`docs/backlog/evidence/2026-09-11-prd-demonstrations.md`** | All three are demonstrated as met. The page's own source (`site/index.html`, base commit `942842b`) was run in the in-app browser against the board's real exported data, with only the store connection stubbed, and no run logged a page error. **AC-84:** at 1050 × 800 the tab row wraps, and "Claude usage" shows in full (x 28–136 px, not clipped, and no sideways scroll). **AC-85:** with dispatch-board selected, the visible tabs are the nine AC-85 names, Agent catalogue included. **AC-92:** a local copy links a second session to dispatch-board, with no change to `board.config.json` or the store. There, the filter `7f71729a` lists 56 of the 79 runs and `9562c312` lists 23, with none from the other session. |
| **A-42** | **PBI-017's status differs between inputs.** `docs/backlog/BOARD.md` lists it In Review with "none yet: committed locally on `main`; the push and PR wait for the owner" and review GO-WITH-CONDITIONS, round 3. The orchestrator's facts of 2026-09-11 say it is live on the board and PR #1 awaits the owner's merge. | **PR #1; the shared BOARD** | PR #1 exists and is open: https://github.com/jdk-official/dispatch-board/pull/1 (branch `pbi/PBI-017-agent-catalogue`). The shared `docs/backlog/BOARD.md` in the main checkout lists PBI-017 under In Review with that PR, "waiting for the owner's merge". The BOARD in this branch is the older copy from the branch base, which is why it read "none yet". S-32 and the *Built (PBI-017)* tags stand. |
| **A-43** | **Tab count.** The orchestrator calls the Agent catalogue "a tenth tab", but its own list of tabs, and `site/index.html` lines 219–227, give nine. | **Orchestrator correction (2026-09-11)** | Nine tabs. The "tenth tab" wording was wrong, and FR-129 and AC-85 stand as written. `site/index.html` lines 219–227 hold nine `role="tab"` buttons, and the AC-85 demonstration (A-41) saw the same nine. |
| **A-44** | **Nothing was run, and the test count is a search count.** NFR-16 and AC-47 say 197, counted as `def test_` methods across the four Python test files. The page suite's check count is not stated. | **Suite runs, 2026-09-11** | The orchestrator ran both suites on commit `942842b`, and they were run again in the PBI-022 worktree with the same result. `python -m unittest discover -s tests` reported "Ran 197 tests … OK". `node tests/page.test.mjs` reported "all 44 page checks passed" and exited 0. The runs confirm the 197 in NFR-16 and AC-47, which are not restated, and meet AC-109. The ISO 29148 self-grades in section 9 are the author's and are unchanged. |

**Open rows:**

| ID | Gap | Default chosen | Impact if wrong |
|---|---|---|---|
| **A-17** | **No continuous integration.** The page now has an automated suite (`node tests/page.test.mjs`), but neither suite runs on push (CI is a future iteration, S-16). Several page requirements and the demonstration ACs (AC-48 to AC-56, AC-60 to AC-62, AC-65, AC-68, AC-72, AC-82, AC-84, AC-85, AC-92) still rest on demonstration or inspection. | Keep both suites run by hand at each PBI close-out, and the demonstration ACs as written. | Regressions between close-outs go unnoticed until seen. Demonstrations depend on live data, and FR-85 cannot be reproduced on demand. |
| **A-19** | **Source and scope of the 0.2 s figure.** It comes from the commissioning task and was not measured by this document. | NFR-3 applies it to the exporter's printed elapsed time, with a warm cache and no transcript change. | If it meant the whole refresh-script run, which now includes three exporters, NFR-3 measures the wrong span. |
| **A-22** | **Accessibility standard.** No conformance level is stated. | No WCAG level is claimed; NFR-15 records the page's features. | If a level such as WCAG 2.2 AA applies, the tokens, charts, catalogue tables and the future timeline need auditing. |
| **A-23** | **Heuristic links between runs.** `feeds` needs a PBI id or a fix word in the task description. | Accept the heuristics (FR-19 to FR-21). | Some hand-offs are missing from the swimlane. Features 3, 4 and 7 also rely on PBI ids in run labels, so runs without one fall outside them. |
| **A-45** | **Evidence mapping for shipped behaviour.** FR-137 and AC-90 (linked sessions beyond the window) have no named test identified. The page-check citations are quoted check names; the suite that holds them passed all 44 checks on 2026-09-11 (A-44). NFR-9's half of this row is closed: a search of `site/index.html` on 2026-09-11, after the catalogue tab, found colour literals only on lines 8–24, inside the `:root` token blocks. | These are marked shipped on the orchestrator's verification and `CLAUDE.md`, with named tests cited wherever a name matches. | A divergence between `CLAUDE.md` and the code in those requirements stays unnoticed until a demonstration or a new test. |
| **A-46** | **Server hardening details that rows 7 and 24 leave open:** what counts as the server's own origin (FR-178), what a rejection returns (FR-177, FR-178, FR-182), and where the Unraid LAN hostname and address are configured. | Own origin: the scheme, host and port the page was served from. A rejection returns an HTTP 4xx status with no board data. The Unraid name and address come from a config key defined in PBI-016. | A stricter or looser rule changes FR-177, FR-178, AC-112 and AC-113. The cost is low. |
| **A-47** | **Collector mass-delete guard against age pruning.** The spec asks for a guard "equivalent to FR-49" (PBI-019) and for age-only pruning (row 12), but gives no rule for how the two interact. After a quiet week, age pruning alone can remove more than half of the records. | FR-49's thresholds apply to deletions other than age pruning. Age pruning of unlinked sessions (FR-185) is not blocked by the guard. | If the owner wants age pruning guarded too, the local board stalls after a quiet week until an override, as v1 does. FR-184, FR-185 and AC-119 change. |
| **A-48** | **The shadow period's switch and length.** Row 15 sets a shadow period, and makes retirement a later owner decision, but does not say how the period starts or ends. | PBI-010's spec defines the switch. The period lasts until the owner decides to retire the hand-kept state (S-39). | FR-175, FR-176 and AC-110 stay in force longer or shorter than the owner expects. The two states can disagree on the Backlog for that time. |

## 9. Requirements report

```json
{
  "schema_version": "1",
  "report": {
    "agent": "requirements-author",
    "as_of_date": "2026-09-11",
    "scope": "Revision 3 of the plan-ready PRD for the dispatch board (PBI-022 re-baseline): Part A re-baselined to the current tree (v1, plus project-first navigation shipped in 2742ca6, plus the PBI-017 Agent catalogue tab, live with PR #1 awaiting merge) and Part B the approved next iteration. Sources: the approved spec docs/backlog/specs/dispatch-board.md revision 5 (ledger rows 1-24, Key decisions, Plan-gate record, Future iterations, AC-C/AC-L/AC-S/AC-R), docs/brief/raw-notes.md (decisions 19 and 20), docs/backlog/pbi/PBI-022.md, the orchestrator's facts of 2026-09-11, ADR-0001, CLAUDE.md, README.md, docs/backlog/BOARD.md, board.config.json, site/index.html and the tests (searched at authoring; run 2026-09-11 (A-44)). Written to docs/prd/dispatch-board.md",
    "summary": "14 intended outcomes (O-1..O-7, O-12, O-13 current tree; O-8..O-11, O-14 next iteration; O-13, O-14 added). Scope: 21 in-scope and 19 out-of-scope items (S-32..S-40 added). 26 owner decisions: D-19 and D-20 are brief decisions 19 and 20; D-21 (repo private) supersedes D-1; D-22 (row 5), D-23 (row 6) and D-24 (row 8) record ledger rows as decisions; D-25 is the plan approval; D-26 is the standing build instruction; D-6 and D-13 remain superseded by D-18. 192 EARS functional requirements: FR-149..FR-192 added; Part A holds FR-1..FR-85, FR-125..FR-130 and FR-135..FR-174; FR-2, FR-42, FR-43, FR-54..FR-56 and FR-66..FR-69 are superseded; FR-95, FR-131 and FR-132 are deferred by D-22; FR-80..FR-85 are not met. 24 measurable NFRs (NFR-24 added; NFR-23 deferred). 23 constraints (C-20..C-23 added). 128 EARS acceptance criteria (AC-94..AC-128 added; AC-51 superseded; AC-87 deferred). The supersession table is resolved. 28 A-rows are marked settled, each citing its spec ledger row (A-2, A-5, A-6, A-8..A-13, A-15, A-16, A-18, A-20, A-21, A-25..A-37, A-39); the ledger names 27 of them, and this document maps A-20 to row 15 (A-24, which row 2 names, is listed as resolved earlier); A-38 is closed by the re-baseline; 13 rows were open as written (A-17, A-19, A-22, A-23, A-40..A-48). A-40..A-44 were then resolved by other PBI-022 work on 2026-09-11 (the brief correction, the AC-R3 evidence file, PR #1, the nine-tab count and the suite runs), leaving 8 open rows (A-17, A-19, A-22, A-23, A-45..A-48), none with 'none - decision pending'. Condition: able_to_be_validated is weak, evidenced by row A-44 (nothing run; the 197-test figure in NFR-16/AC-47 is a search count that may need restating), row A-45 (FR-137/AC-90 have no named test and NFR-9 was not re-checked) and row A-17 (no CI; the demonstration ACs rest on demonstration). Since this grading, A-44 is closed: both suites were run on 2026-09-11 (unittest: Ran 197 tests, OK; page suite: all 44 page checks passed), confirming the 197; the grade is the author's and is unchanged. NFR-9's half of A-45 is also closed (colour literals only on site/index.html lines 8-24, inside the :root token blocks); its FR-137/AC-90 half stays open. Not delivered by this file, and flagged: the brief line-16 correction (A-40) and the AC-R3 evidence (A-41); both have since been delivered elsewhere in PBI-022 (docs/brief/raw-notes.md; docs/backlog/evidence/2026-09-11-prd-demonstrations.md). Every input was readable; none was missing.",
    "verdict": "DONE-WITH-CONDITIONS",
    "sensitivity": "sensitive"
  },
  "grades": {
    "complete": "pass",
    "consistent": "pass",
    "feasible": "pass",
    "comprehensible": "pass",
    "able_to_be_validated": "weak"
  },
  "ears_conformant_count": 320,
  "assumptions_open_questions_count": 8
}
```
