# Dispatch board (v1 as built, plus next iteration): Product Requirements

**Status:** plan-ready draft, revision 2. It records the working v1 as built and adds the owner's next iteration (not built) and the project-first navigation now being built (D-18). Self-graded only; the quality verdict belongs to the caller's gate, not to this document.
**Sources, in priority order:** `docs/brief/raw-notes.md` (the brief, re-read in full for this revision, including the owner's answers of 2026-09-11, the next-iteration direction, decision 18 on project-first navigation, candidate features 1–9 and the two undecided items), `CLAUDE.md` (as it stands after the project-first changes), `README.md`, `board.config.json`, then the code as ground truth: `site/index.html`, `exporters/export_sessions.py`, `exporters/refresh.py`, `exporters/export_board.py`, the `tests/` files, and `.gitignore`. Also used: the commissioning task context (audience, the NFR figures "about 0.2 s", "5000 documents", "about 86 used") and the **revision instructions of 2026-09-11**, which correct two statements of the first draft: the store leftovers (A-9) and the artifact's font policy (C-2, formerly A-14). Every listed input was readable.
**Moving baseline:** the brief gained decision 18 while this revision was being written, and the working tree is part-way through building it (A-38). Part A of section 4 describes v1 as built **before** that work. Nothing was run to produce this document.
**Date:** 2026-09-11

### Glossary (each term is used in exactly one sense throughout this document)

- **Page**: `site/index.html`. In v1 it is published as the claude.ai artifact "Live Dispatch Board", private to the owner. In the next iteration the same page is also served by the local server.
- **Store**: the artifact's document store. In the v1 baseline its collections are `sessions/<id>`, `runs/<agentId>`, `tabs/{spec,assumptions,decisions,backlog,git}` and `meta/status`. D-18 adds `projects/<projectId>`, `projectTabs/<projectId>.<tab>` and `status/<projectId>`.
- **Session exporter**: `exporters/export_sessions.py`. **Board exporter**: `exporters/export_board.py`. **Refresh script**: `exporters/refresh.py`.
- **Refresher**: the separate Claude Code session that runs the v1 refresh loop. **Tick**: one pass of that loop.
- **Session**: one Claude Code conversation, identified by its session id and recorded as a **main transcript** (`<projectsRoot>/<folder>/<id>.jsonl`) plus one **agent transcript** per subagent (`<id>/subagents/agent-<agentId>.jsonl`, with a `.meta.json`).
- **Project** (D-18): an entry under `projects` in `board.config.json`, with `id`, `name`, `repoPath`, `branch`, `sessions`, `statusDoc` and `docs`. The first two are platform-catalogue and dispatch-board. **Linked session**: a session listed in a project's `sessions`.
- **Build session**: in the v1 baseline, a session listed in `build.sessions` in `board.config.json`; under D-18, a linked session. **Tracked build repo**: in the v1 baseline, `build.repoPath` (`C:/Users/jdk/platform-catalogue`, branch `build/logic-core`); under D-18, each project's `repoPath`. **Project tabs**: Spec, Assumptions, Decisions, Backlog and GitHub details.
- **Run**: one agent dispatched by a session. In v1 it is stored as one `runs/<agentId>` document.
- **Lane**: a run's agent role. The **review lanes** are `plan`, `cr` (code-reviewer) and `ver` (verifier). The **build lanes** are `req` (requirements-author), `cw` (code-writer) and `tw` (test-writer). The others are `orch`, `human` and `other`.
- **Kind**: a run's state. It is one of `running`, `done`, `go`, `changes`, `nogo` or `killed`. **Verdict**: the short text shown with a run, usually the agent's own **verdict token** (for example `GO-WITH-NOTES`, `NOT-DONE`).
- **Finish**: the record that a run ended. It is either a `<task-notification>` in the main transcript or an inline foreground result.
- **Session window**: `sessions.days` (7 days, D-5 and D-15). **Running window**: `runs.runningWindowMinutes` (10 minutes).
- **Effective usage**: tokens weighted by relative cost: input × 1, cache read × 0.1, cache write × 2, output × 5. It is a comparison figure, not a price.
- **Pushed state**: `out/.pushed.json`, which records what the store holds. **Pending plan**: `out/.pending.json`, which records the last printed set of writes.
- **Mass-delete guard**: the refresh script's refusal of an export that has no sessions, or that would delete more than half of the pushed runs and sessions.
- **`write_db`**: the Artifact tool operation that writes store documents, used with `db_op: "batch"`.
- **Work item**: a backlog item of a tracked build, identified by a PBI id (for example `PBI-001`).

Next-iteration terms (none of these is built):

- **Collector**: a program on the owner's PC that reuses the session exporter's logic, reads transcripts incrementally and produces records. It needs no Claude session.
- **Local database**: the SQLite database that holds the records.
- **Local server**: a small web server that serves the page, a **data snapshot** (all current records in one response), a **live-push stream** (record changes sent to open pages without a reload) and an **answers endpoint**. In the Unraid deployment it also has an **ingest endpoint** that accepts records from the collector.
- **On-PC deployment**: collector, local server and local database all run on the owner's PC; the local server listens on 127.0.0.1 only. **Unraid deployment**: the local server and local database run as a container on the owner's Unraid server; the collector stays on the PC and sends records over the LAN.
- **Record shapes**: the one set of definitions for session, run, project, tab, status and answer records, shared by the collector, the local server and every data adapter.
- **Data adapter**: the one interface through which the page obtains data. The **store adapter** reads the Store; the **local API adapter** reads the local server; a **hosted API adapter** is a later option.
- **Last-refresh time**: the time of the last successful refresh (a collector write, or a refresher tick that wrote to the Store). It is held in a status record separate from `meta/status` and `status/<projectId>`.
- **Answer**: the owner's response to one assumption row awaiting a human: *Accept* the chosen default, or *Override* with an answer, plus an optional note.

---

## 1. Intended outcomes

**v1 (as built):**

- **O-1** The owner can see, for any Claude Code session active on this computer in the last 7 days, which agents ran, what each returned, and the tokens and minutes each used, without opening a transcript.
- **O-2** For a build of a tracked project, the owner sees the project's spec, the assumptions awaiting a human, decisions, backlog and repository state next to the agent activity.
- **O-3** The owner sees each session's Claude usage: effective usage, where it went, how it was spread over time and models, and when a usage limit refused work.
- **O-4** The board stays current without any session having to report to it. Everything is derived from what sessions leave on disk.
- **O-5** Nothing the owner has not chosen to publish is published by default. First prompts are withheld, excluded sessions are never read, and obvious secrets are redacted when prompts are published.
- **O-6** One bad file or a broken discovery cannot freeze or wipe the board. Failures are isolated per agent and per session, and mass deletes are refused.
- **O-7** The page reads as a professional dashboard that follows the owner's stated design preferences.

**Project-first navigation (D-18, being built):**

- **O-12** The owner picks a project and sees its spec, assumptions, decisions, backlog and repository, with Dispatch and usage combined over every session building it. Sessions linked to no project stay viewable on their own. The dispatch board's own work items appear once they exist.

**Next iteration (not built):**

- **O-8** The board stays current from log-on onwards with no Claude session open and no Claude usage spent on refreshing (D-16).
- **O-9** Moving the board to a host later changes only storage and transport, not the page or the record shapes (D-16, D-17).
- **O-10** The owner sees at a glance when the board's data is stale and everything, across all sessions, that is waiting on them (features 1–2).
- **O-11** The owner sees each build's progress from its runs alone: review findings, work-item state, test trend, cost per work item, run details, a timeline and a usage-limit forecast (features 3–9). No hand-kept build state is needed.

## 2. Scope

### In scope

v1 as built:

- **S-1** The page: a read-only, live-subscribed dashboard with a session picker, Overview, Dispatch, Claude usage and the project tabs.
- **S-2** The session exporter: session discovery, session documents, run rows, usage, privacy settings, a parse cache and failure isolation.
- **S-3** The board exporter.
- **S-4** The refresh script: diffing against the last push, batching, the mass-delete guard, the status live flag, and commit.
- **S-5** The refresher loop procedure in `CLAUDE.md`, at the 10-minute cadence (D-14).
- **S-6** The settings in `board.config.json` that the above read.
- **S-7** The automated test suite (`tests/`).
- **S-8** Six requirements v1 does not yet meet (FR-80 to FR-85), recorded as open defects of v1. Whether and when to close them is not decided (A-12, A-13).

Being built now:

- **S-14** Project-first navigation for every project listed in `board.config.json`, starting with platform-catalogue and dispatch-board (D-18). This supersedes D-13, which had put more than one project out of scope. The owner made it the build priority and chose to build it before this revision was finished (FR-129, FR-130, FR-135 to FR-148).

Next iteration (not built):

- **S-20** The local-first app (D-16): collector, local database, local server, and a log-on start through Task Scheduler.
- **S-21** The data-adapter seam in the page, with the store adapter and the local API adapter built (D-16).
- **S-22** One set of record shapes for sessions, runs, projects, tabs, status and answers (D-16; projects added for D-18, A-39).
- **S-23** An optional Unraid deployment of the local server and local database as a container, fed by the collector over the LAN (D-17). Whether the owner uses it is open (A-26).
- **S-24** Candidate features 1–9, which the owner approved for this plan on 2026-09-11 (brief lines 165–190): stale-board warning, "Waiting on you" panel, review findings ledger, work-item status derived from runs, test and coverage trend, usage limit forecast, cost per work item, run detail, timeline view.
- **S-25** The tab-bar overflow fix (a v1 defect, FR-125 to FR-128). Which tabs show is settled by D-18 (FR-129).
- **S-26** Answering assumptions from the board, including its provenance guards. The page's write path is included only if the owner adopts it through an ADR (A-25). The provenance guards (FR-133, FR-134) apply regardless.

### Out of scope

- **S-9** Any write from the v1 page. The only page write proposed for the next iteration is the answer path (S-26), conditional on its ADR.
- **S-10** Moving off the artifact to GitHub Pages plus an external database. This was rejected for now (D-3) and cannot be done while the page is an artifact (C-2).
- **S-11** Hooks in the build session that report to the board (rejected for now, D-3).
- **S-12** Hand-written `runs` rows (D-4).
- **S-13** Deleting store leftovers (`tabs/usage`, and the retired `tabs/*` documents once D-18 ships) without the owner's go-ahead (D-11, A-9).
- **S-15** Making the v1 refresher durable, for example as a scheduled Claude task. Durability comes instead from the next iteration's log-on start (D-16, S-20).
- **S-16** Continuous integration and automated tests of the page. They are absent in v1 (A-17).
- **S-17** Redaction of session titles, run labels and agent descriptions. It is absent in v1 and is not a priority, because only the owner views the board (D-12, A-2).
- **S-18** A plan usage meter. Transcripts record only the moments a limit refused a request (`CLAUDE.md`, Open items). The usage limit forecast (feature 6) is an estimate, not a meter.
- **S-19** Decomposing this document into backlog items, and any code or tests. Those are downstream of this document.
- **S-27** Hosting on Azure (Static Web Apps, Functions, a database, Entra ID). It remains a later alternative (D-17).
- **S-28** Building the hosted API adapter. The seam is in scope (S-21); the hosted adapter is later (D-16).
- **S-29** Phone notifications (a review returns NO-GO, a run is cut off, the build goes idle, a session is waiting). The owner deferred them to a future iteration on 2026-09-11 (brief lines 192–195).
- **S-30** An archive of sessions or runs older than 7 days (D-15).
- **S-31** Using the answer mechanism to record plan approval or the acceptance of review conditions. The brief names this only as a possible later use (brief line 223).

## 3. Decisions already made

Only the owner's recorded decisions are listed. D-1 to D-11 sit under the brief's heading "Decisions the owner made (with reasons given)". D-12 to D-15 sit under "Owner's answers (2026-09-11)", and D-16 to D-18 under "Direction for the next iteration (owner, 2026-09-11)"; the brief numbers them 12 to 18 in the same sequence. The reason is kept where the brief records one. Decision-adjacent lines without such a marker are in section 8.

| ID | Decision | Reason recorded | Source |
|---|---|---|---|
| **D-1** | The code lives in a **public** GitHub repository, `jdk-official/dispatch-board` (2026-09-10). | The owner chose public over private when asked. | Brief lines 55–56 |
| **D-2** | Repositories stay on the **Windows filesystem**. The earlier "repos live in WSL" rule is dropped. | No WSL distro is installed. | Brief lines 57–58 |
| **D-3** | The board is kept live by a **refresher loop** (option 1 of 3). Rejected for now: hooks in the build session (option 2) and moving to GitHub Pages plus a database (option 3). | The refresher loop is the lowest-cost option that actually updates. Option 2 relies on the model acting. Option 3 loses the private claude.ai page and means a page rewrite. | Brief lines 59–62 |
| **D-4** | Runs are **derived from transcripts**, not hand-written. The build session writes only `meta/status` `title`/`message`/`metrics` and the hand-kept build state. | No reason recorded beyond the instruction to the build session. | Brief lines 63–64 |
| **D-5** | There is **one dashboard per session**, reached through a session picker. Sessions are **auto-discovered: every session active in the last 7 days**. | Chosen over "only sessions with agents" and "a hand-kept list". No further reason recorded. D-18 changes the picker to projects first; auto-discovery stays. | Brief lines 65–67 |
| **D-6** | Project tabs appear **only for build sessions** (those in `build.sessions`). | No reason recorded. Superseded in effect by D-18: a project always shows all its tabs. | Brief line 68 |
| **D-7** | The **refresher's own session stays on the board**. | The owner wants to see it. | Brief line 69 |
| **D-8** | **Privacy defaults:** first prompts are not published unless `showFirstPrompt` is on. When it is on, obvious secrets are redacted. `exclude` globs hide sessions. | This came from a code-review finding, and the owner accepted the default. | Brief lines 70–72 |
| **D-9** | **Code changes go through the catalogue agents.** `engineering-agents:code-writer` builds under TDD, then `review-agents:code-reviewer` gives GO/NO-GO, looping until GO. | The owner asked "why aren't we using agents for this?" after a solo build. That build's first review was NO-GO, with one HIGH finding: a single bad file froze the board. | Brief lines 73–76 |
| **D-10** | **Design preferences:** a professional dashboard, not an editorial page. Status tiles: bordered, 3 px coloured top bar, label, figure, one-line context. One sans (Schibsted Grotesk) with tabular figures, and monospace only for ids and hashes (no wide monospace text). Dark-first tokens. Violet `--human` only for things waiting on a human. Motion only when true. | These are the owner's stated preferences, recorded in `CLAUDE.md`. | Brief lines 77–81; `CLAUDE.md` "Design rules" |
| **D-11** | **Deleting store documents needs the owner's go-ahead.** The leftovers stay until the owner approves. | An automated permission check blocked a batch that deleted `tabs/usage`. | Brief lines 82–83 |
| **D-12** | **Only the owner views the board.** It is not shared. | Privacy work beyond the current defaults is therefore not a priority. | Brief lines 126–127 |
| **D-13** | **One tracked project.** Multi-project support is out of scope. **Superseded by D-18 the same day.** | No reason recorded. | Brief line 128 |
| **D-14** | **Freshness: 10 minutes is enough.** The refresher loop moved from every 2 minutes to every 10 (at minute 3, 13, 23 and so on). | No reason recorded beyond "10 minutes is enough". | Brief lines 129–130; `CLAUDE.md` (`/loop 10m`) |
| **D-15** | **Show sessions from the last 7 days, for now. No archive** of older sessions or runs. | No reason recorded. | Brief line 131 |
| **D-16** | **Local first, hosting later.** A collector (the existing exporter logic, reading new transcript lines incrementally) writes to SQLite. A small local web server serves the page, a data snapshot, a live-push stream and an answers endpoint. The page gets one data adapter (artifact store today, local API next, hosted API later). It starts at log-on via Task Scheduler and uses no Claude usage to refresh. One set of record shapes (sessions, runs, tabs, status, answers) is defined now. | Build a local version that no longer depends on a Claude session; defining the record shapes now means hosting later only swaps the storage and the transport. | Brief lines 135–143 |
| **D-17** | **Unraid is the owner's possible host.** The server and its SQLite database can run as a container on the owner's Unraid server. The collector stays on the PC and sends records to the server over the LAN, in the same ingest-API shape as a cloud host. The server must not read SQLite over a network share. Azure (Static Web Apps, Functions, a database, Entra ID) remains a later alternative. | SQLite was chosen partly so that the server and database can run on Unraid. Transcripts exist only on the PC running Claude Code. SQLite locking over SMB/NFS is unreliable. | Brief lines 144–149 |
| **D-18** | **Project-first navigation, the build priority.** It supersedes D-13 and the tab-visibility recommendation. Each project has a spec, a backlog and build sessions. The owner picks a project from the dropdown and sees its spec, requirements, assumptions, decisions, backlog and repo. Dispatch and usage for a project combine the runs of every session building it, with a filter to narrow to one session. Sessions linked to no project stay viewable on their own. Projects and their build sessions are listed in `board.config.json`. The first two projects are platform-catalogue and dispatch-board. | Build sessions run from `C:\Users\jdk`, not the repo folder, so they must be listed. Listing dispatch-board makes the board's own PBIs appear once they exist. The owner chose to build this before the PRD revision and pbi-plan are finished. | Brief lines 151–163 |

*Not promoted to a decision:*
- `CLAUDE.md`'s open item "Switch Dispatch to transcript figures so there is one number" is an unowned imperative in an open-items list, and the brief lists the same point as "not yet decided" (A-6).
- The "slower idle cadence" was offered to the owner and not decided (A-5).
- Whether the owner will actually host on Unraid: D-17 says the owner *may* (A-26).
- Answering assumptions from the board: the brief lists it under "Raised by the owner, 2026-09-11 (not yet decided)" (A-25).
- The binding of the local server to 127.0.0.1 comes from the revision instructions, not from a recorded decision. It is stated as a requirement for the on-PC deployment only (NFR-19), because the Unraid deployment must accept LAN connections (A-27).
- `CLAUDE.md`'s data model for projects (`projects/<projectId>`, `projectTabs`, `status/<projectId>`, `projects/<projectId>.json`) is the build session's implementation of D-18, not an owner decision. FR-135 to FR-148 draw on it as the current description of that work (A-38).

## 4. Functional requirements

**Status tags:**
- *Met* means v1 meets the requirement. The evidence is a named test in `tests/`, or inspection of the named code where no test exists.
- *v1 procedure* means the behaviour is performed by the refresher session following `CLAUDE.md`, and is checked by demonstration.
- **Not met in v1** marks a known gap or an open review finding.
- **D-18: being built, not verified** marks FR-129, FR-130 and FR-135 to FR-148.
- **Next iteration: not built** marks the rest of FR-86 to FR-134.

**Supersession.** These pairs are not contradictions. Each v1 requirement describes v1 as built before the D-18 work, and is replaced when the named requirement is built.

| v1 requirement | Replaced by | Condition |
|---|---|---|
| FR-2 (build sessions exported beyond the window) | FR-137 (linked sessions) | When D-18 ships. |
| FR-42 (five singleton `tabs/*` documents) | FR-140 (`projectTabs/<projectId>.<tab>`) | When D-18 ships. |
| FR-43 (work-item state from `BUILD_STATE`) | FR-141 (`buildState` in the project data file), then FR-113 (derived from runs) | FR-141 when D-18 ships; FR-113 when feature 4 is built. |
| FR-54 to FR-56 (`meta/status` for the one build) | FR-144 (each project's status document) | When D-18 ships. |
| FR-66, FR-67 (session picker) | FR-130 (projects first, then "Other sessions") | When D-18 ships. |
| FR-68 and AC-51 (project tabs hidden for non-build sessions) | FR-129, AC-85 (a project always shows all its tabs) | When D-18 ships. |
| FR-69 (views limited to one session) | FR-145 to FR-147 | When D-18 ships. |
| NFR-16 and AC-47 (82 tests) | A new count | Already stale for the current tree (A-38). |
| FR-63 (page reads only through `window.claude.use('db')`) | FR-97 to FR-99 (data adapter) | When the adapter seam is built. |
| FR-64 and AC-50 (the page never writes) | FR-131, FR-132 | Only if the ADR for answers is accepted (A-25, C-17). |
| AC-34, AC-42, AC-44 (exact plan contents) | Counts rise by one last-refresh write | When FR-103 is built (A-37). |

### Part A: v1 as built, before the D-18 work (FR-1 to FR-85)

#### Session discovery and session documents (session exporter)

- **FR-1** When the session exporter runs, it shall write one `sessions/<id>` document for every main transcript under `sessions.projectsRoot` whose last recorded timestamp lies within the session window of the run. *(Met: `Pipeline.test_basic_export`; D-5, D-15.)*
- **FR-2** The session exporter shall export every build session whether or not its last activity lies within the session window. *(Met: inspection of `main()`.)*
- **FR-3** The session exporter shall set `build` to true on the document of every build session and to false on every other session document. *(Met: `Cache.test_build_sessions_change_applies_without_a_transcript_change`. Under D-18, `build` is true when `project` is set, per `CLAUDE.md`.)*
- **FR-4** The session exporter shall write in every session document the fields `title`, `project`, `cwd`, `start`, `last`, `build`, `windowDays`, `windowMinutes`, `runs`, `running` and `usage`. *(Met: `Pipeline.test_window_days_on_the_session_doc`, `test_window_minutes_on_the_session_doc`; `CLAUDE.md` data model. Under D-18, `project` holds the linked project's id and the folder name moves to `folder`: FR-138.)*
- **FR-5** If a main transcript records no assistant response, then the session exporter shall leave that session out of the export. *(Met: inspection of `parse_session()`.)*

#### Agent runs (session exporter)

- **FR-6** When the session exporter exports a session, it shall write one `runs/<agentId>` document per agent transcript in that session, carrying `session`, `seq`, `lane`, `label`, `kind`, `verdict`, `tok` and `min`. *(Met: `Pipeline.test_basic_export`.)*
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
- **FR-17** The session exporter shall set a run's `tok` to the `subagent_tokens` its finish reports. When that value is missing or unreadable, it shall use the context size of the agent's last transcript response. *(Met: `Pipeline.test_basic_export`, `Malformed.test_malformed_numeric_tags`. Which token figure the board should show is open: A-6.)*
- **FR-18** The session exporter shall set a run's `min` to its reported duration in whole minutes, rounded. When that value is missing or unreadable, it shall use the whole minutes between the run's launch and its finish. *(Met: `Classify.test_minutes`, `test_minutes_survive_malformed_numbers_and_timestamps`.)*
- **FR-19** When a code-writer or test-writer run whose label marks it as a fix (it contains `review`, `LOW`, `LOWs`, `notes`, `fix`, `fixes` or `CR-<n>`) starts after a review-lane run with a verdict, the session exporter shall set its `feeds` to one of two runs. If the fix run names a PBI id, it is the latest earlier such review run that shares a PBI id. If the fix run names none, it is the latest earlier such review run. *(Met: `Link.test_fix_is_fed_by_the_review`; heuristic limits, A-23.)*
- **FR-20** When a code-reviewer run starts after a code-writer or test-writer run of kind `done`, the session exporter shall set its `from` to the latest such run, restricted to runs sharing a PBI id when the review names one. *(Met: `Link.test_review_comes_from_the_last_finished_build`, `Pipeline.test_not_done_builder_is_changes_and_does_not_hand_off`.)*
- **FR-21** When a code-writer or test-writer run naming a PBI id starts after a plan-lane run of kind `go` that shares that id, the session exporter shall set its `from` to that plan-lane run. *(Met: `Link.test_builder_comes_from_the_plan_gate`.)*
- **FR-22** When two or more consecutive non-fix runs in the same build lane (`cw` or `tw`) each launch within 120 seconds of the previous one, the session exporter shall give them one shared `group` letter. *(Met: `Link.test_parallel_group`.)*
- **FR-23** Where `runs.manual` lists a row whose `after` run is exported, the session exporter shall insert that row immediately after its anchor run, in the anchor run's session. *(Met: inspection of `main()`.)*

#### Usage (session exporter)

- **FR-24** The session exporter shall compute each session's effective usage over the responses in its main transcript and in every agent transcript, counting each response once by message id. *(Met: inspection of `tokens()` and `response()`.)*
- **FR-25** When a transcript records a request refused by a usage limit (an API error status 429 or a quota-limit record), the session exporter shall count that refusal in the session's `usage.limits`, grouped by the reset time the platform reported. *(Met: inspection of `reject()` and `usage_doc()`.)*
- **FR-26** The session exporter shall publish, per session, an hourly effective-usage series split into main session and agents, covering at most the last 168 hours of that session's activity. *(Met: inspection of `usage_doc()`.)*

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
- **FR-38** If a build session's main transcript cannot be found under the projects root, then the session exporter shall exit non-zero, naming that session id. *(Met: `Discovery.test_missing_build_transcript_fails`. Under D-18 this applies to every linked session, per `CLAUDE.md`.)*

#### Parse cache and file writes

- **FR-39** When the parser version, the running window, and every one of a session's transcript files' modification time and size are unchanged since the previous run, the session exporter shall reuse the cached parse, unless one of the session's runs is `running` or an agent was skipped. *(Met: `Cache.test_reused_when_nothing_changed`, `test_invalidated_by_a_transcript_change`.)*
- **FR-40** When `build.sessions`, `sessions.showFirstPrompt` or `runs.runningWindowMinutes` changes, the session exporter shall apply the new value on its next run without any transcript change. *(Met: `Cache.test_build_sessions_change_applies_without_a_transcript_change`, `test_running_window_change_applies_without_a_transcript_change`, `Privacy.test_toggling_first_prompt_applies_without_a_transcript_change`.)*
- **FR-41** The session exporter and the refresh script shall write each output and state file through a temporary file in the same folder that is then swapped into place. *(Met: `WriteJson.test_a_failed_write_keeps_the_previous_file`, `Save.*`.)*

#### Project tabs (board exporter)

- **FR-42** When the board exporter runs, it shall write the five project-tab documents `spec`, `assumptions`, `decisions`, `backlog` and `git`. Their sources are the tracked build repo's solution spec, PRD, brief, ADRs and local review notes, and its git state. *(Met in the v1 baseline: inspection; no automated test, A-17. Replaced by FR-140.)*
- **FR-43** The board exporter shall take each work item's state, review summary, open items and commit from `BUILD_STATE`, defaulting any work item absent from `BUILD_STATE` to state `todo`. *(Met in the v1 baseline: inspection; D-4; drift risk, A-20. Replaced by FR-141, then FR-113.)*
- **FR-44** The board exporter shall mark as awaiting a human (`needsYou`) exactly the assumption rows that the tracked spec lists as rows the human must confirm at the plan gate. *(Met: inspection.)*

#### Refresh script

- **FR-45** When the refresh script runs, it shall run the board exporter and the session exporter. It shall then print a JSON plan holding a `set` write for every runs, sessions or tabs document whose content, ignoring `generatedAt`, differs from the pushed state. *(Met: `Plan.test_first_plan_sets_everything_and_the_status`, `test_generated_at_alone_is_not_a_change`. Under D-18 the managed collections are `runs`, `sessions`, `projects` and `projectTabs`, per `CLAUDE.md`.)*
- **FR-46** If no document differs from the pushed state and no status update is due, then the refresh script shall print `nothing to push` and leave no pending plan. *(Met: `Plan.test_commit_then_nothing_to_push`, `test_nothing_to_push_removes_a_stale_pending_file`, `Cli.test_nothing_to_push`.)*
- **FR-47** When a document of a managed collection recorded in the pushed state is no longer exported, the refresh script shall include a `delete` write for it. *(Met: `Plan.test_vanished_run_is_deleted`; scope of D-11, A-10.)*
- **FR-48** The refresh script shall emit no `delete` write for any document that is not recorded in the pushed state. *(Met: inspection of `plan()`. This is why `tabs/usage` stays, A-9.)*
- **FR-49** If the export contains no sessions, or would delete more than half of the pushed runs and sessions, then the refresh script shall refuse the plan: it exits with status 2 and leaves no pending plan. *(Met: `MassDelete.test_more_than_half_is_refused`, `test_refusal_removes_a_stale_pending_file`, `test_zero_sessions_is_refused`, `test_zero_sessions_refused_even_for_a_small_delete`.)*
- **FR-50** Where `--allow-mass-delete` is given, the refresh script shall plan the deletes that FR-49 would otherwise refuse. *(Met: `MassDelete.test_allowed_with_the_flag`, `Cli.test_mass_delete_exits_non_zero_without_the_flag`.)*
- **FR-51** If either exporter exits non-zero, then the refresh script shall exit non-zero without planning. *(Met: `Cli.test_export_failure_stops_before_planning`.)*
- **FR-52** When `refresh.py --commit` is run with a pending plan, the refresh script shall record that plan's state as the pushed state. *(Met: `Plan.test_commit_then_nothing_to_push`, `Cli.test_commit`.)*
- **FR-53** If `refresh.py --commit` is run with no pending plan, then the refresh script shall exit with status 1 and report `nothing pending`. *(Met: `Cli.test_commit_without_pending`.)*
- **FR-54** When a tabs document, a build session's document or a build session's run is changed or deleted, or the live flag flips, the refresh script shall add an `update` of `meta/status` carrying `live` and `updatedAt`. *(Met in the v1 baseline: `UpdatedAt.test_build_session_change_bumps`, `test_build_run_change_bumps`, `test_deleted_build_run_bumps`, `test_tab_change_bumps`, `test_live_flip_bumps`. Replaced by FR-144.)*
- **FR-55** If only non-build session documents or their runs change, then the refresh script shall leave `meta/status` out of the plan. *(Met: `UpdatedAt.test_non_build_session_change_does_not_bump`, `test_non_build_run_change_does_not_bump`, `test_running_non_build_run_does_not_bump`.)*
- **FR-56** The refresh script shall set `live` to true exactly when a build session has a run of kind `running`. *(Met: `UpdatedAt.test_running_non_build_run_does_not_bump`, `test_live_flip_bumps`. Under D-18, per project: FR-144.)*
- **FR-57** When a plan holds more than 50 writes, the refresh script shall split it into consecutive batches of at most 50 writes. *(Met: `Plan.test_batches_past_the_limit`; C-3.)*

#### Refresher

- **FR-58** While the refresher loop is active, the refresher shall, on each tick, run the refresh script and write the printed plan to the store with `write_db` batch operations. *(v1 procedure: `CLAUDE.md` Refresh procedure, steps 1–2; D-3.)*
- **FR-59** When the refresh script prints `nothing to push`, the refresher shall end the tick without writing to the store. *(v1 procedure: the `/loop` prompt in `CLAUDE.md`.)*
- **FR-60** When a tick's `write_db` writes succeed, the refresher shall run `refresh.py --commit`. *(v1 procedure: `CLAUDE.md` step 3.)*
- **FR-61** If a tick's `write_db` write fails, then the refresher shall not run `refresh.py --commit`. *(v1 procedure: `CLAUDE.md` step 3.)*
- **FR-62** If the refresh script exits non-zero, then the refresher shall write nothing to the store in that tick. *(v1 procedure: `CLAUDE.md` step 1.)*

#### Page

- **FR-63** The page shall obtain all its data from store subscriptions opened through `window.claude.use('db')`. *(Met: inspection of `site/index.html`. Replaced by FR-97 to FR-99 when built.)*
- **FR-64** The page shall issue no write to the store. *(Met: inspection; brief line 19. Replaced only if the answers ADR is accepted: A-25.)*
- **FR-65** When a subscribed store document changes, the page shall re-render the views that show it. *(Met: inspection of the `onSnapshot` handlers.)*
- **FR-66** The page shall list sessions in a session picker, with build sessions in a "Builds" group and all others in an "Other sessions · last <N> days" group, most recent activity first. *(Met: inspection of `fillPicker()`; D-5. Replaced by FR-130.)*
- **FR-67** When sessions first load and no session is selected, the page shall select the first session available in this order: the session saved from the previous visit, the first live build session, the first build session, the most recently active session. *(Met: inspection of `pickSession()`. Replaced by FR-130; the D-18 default selection is not stated, A-38.)*
- **FR-68** While the selected session is not a build session, the page shall hide the project tabs. *(Met: inspection of `applySession()`; D-6. Replaced by FR-129.)*
- **FR-69** When a session is selected, the page shall limit the Overview, Dispatch and Claude-usage tabs to that session's runs and usage. *(Met: inspection of `applySession()`; D-5. Replaced by FR-145 to FR-147.)*
- **FR-70** While a build session is selected and any of its runs is `running` or `meta/status.live` is true, the page shall show the header status `Building`. *(Met: inspection of `renderHeader()`.)*
- **FR-71** While a non-build session is selected and it has a `running` run or its last activity lies within its `windowMinutes`, the page shall show the header status `Active`. *(Met: inspection of `renderHeader()`; otherwise `Idle`.)*
- **FR-72** When the Dispatch tab is shown, the page shall draw the selected session's runs as a swimlane in `seq` order, with `from` hand-off arrows, `feeds` arrows and one bracket per parallel `group`. The swimlane has one column per lane used, and every pipeline lane for a build session. *(Met: inspection of `renderDispatch()`.)*
- **FR-73** When the Dispatch tab is shown, the page shall list the selected session's runs newest first, each with its agent, label, outcome, verdict, tokens and minutes. *(Met: inspection of `renderDispatch()`.)*
- **FR-74** While a build session is selected, the page shall show in the Overview the summary tiles, backlog cells, pipeline, needs-attention list, usage panel, review outcomes and recent agent activity. *(Met: inspection of `renderOverview()`.)*
- **FR-75** The page shall derive the needs-attention list from store data. It lists assumptions awaiting a human, work items with open conditions, partly built work items, a tracked build repo with no git remote, a session with runs but no verifier run, and runs cut off. *(Met: inspection of `renderOverview()`.)*
- **FR-76** When the Claude-usage tab is shown, the page shall show the selected session's effective usage by activity, by hour, by model and by agent run, its usage-limit hits, and a notice that the figures are not a plan usage meter. *(Met: inspection of `renderUsage()`.)*
- **FR-77** If `window.claude.use('db')` is unavailable, then the page shall show only a notice that it cannot reach the live store. *(Met: inspection.)*
- **FR-78** If a live store subscription ends with an error, then the page shall show a footer message giving the error code and asking for a reload. *(Met: inspection.)*
- **FR-79** The page shall restore the last selected tab and session from browser local storage when it is reloaded. *(Met: inspection.)*

#### Requirements not met in v1

- **FR-80** **Not met in v1 (open review LOW 1).** If an agent transcript cannot be re-read and its carried-over row has kind `running`, then the session exporter shall reclassify that row as kind `killed` with verdict `no result` once the running window has elapsed since the row's `end` time. *(Today such a row stays `running` and keeps the build "live". The remedy was chosen by the author of this document: A-12.)*
- **FR-81** **Not met in v1 (open review LOW 2).** If a usage record in an agent transcript is malformed, then the session exporter shall skip that record and export the session with its other records. *(Today one malformed usage line can drop the whole session: A-12.)*
- **FR-82** **Not met in v1 (open review LOW 3).** If a value under `sessions` or `runs` in `board.config.json` does not have its documented JSON type, then the session exporter shall exit non-zero with an error naming the key. The documented types are: `days` and `runningWindowMinutes` numbers, `projectsRoot` a string, `exclude` a list of strings, `showFirstPrompt` a boolean, `manual` a list. *(Today a quoted `"false"` turns first-prompt publishing on, and a quoted `exclude` glob hides every session. The remedy was chosen by the author of this document: A-12.)*
- **FR-83** **Not met in v1 (open review LOW 4).** While a non-build session is selected, the page shall show the same active-or-idle state in the Overview's "Running now" tile as in the header status. *(Today the tile says "session active" after the header shows Idle, until the next data change: A-12.)*
- **FR-84** **Not met in v1 (known gap).** When a verifier run completes with a result stating `exercised` or `fallback-declared`, the session exporter shall record that word as the run's verdict. *(Today such runs show `finished`. Kind mapping: A-11.)*
- **FR-85** **Not met in v1 (known gap, cause unknown).** When the published page is opened in Chrome, the page shall render its app bar and Overview panel without a manual reload. *(It sometimes loads blank until reloaded; not reproduced locally: A-13.)*

### Part B: next iteration and D-18 (FR-86 to FR-148)

Every requirement in Part B is **next iteration: not built**, except FR-129, FR-130 and FR-135 to FR-148, which are **D-18: being built, not verified**. Sources: D-16, D-17, D-18, the candidate features (brief lines 165–190), the two undecided items (brief lines 197–223), and `CLAUDE.md` for the D-18 data model.

#### Collector (D-16)

- **FR-86** When the collector reads a transcript it has read before, it shall read only the lines appended since its previous read of that file. *(D-16 "reading new transcript lines incrementally".)*
- **FR-87** The collector shall derive session, run, project and usage records by the same rules as the session exporter (FR-1 to FR-38 as replaced by FR-137 to FR-139, and FR-80 to FR-84 once those are met). *(D-16 "the existing exporter logic"; D-18.)*
- **FR-88** Where the on-PC deployment is used, the collector shall write its records to the local database. *(D-16.)*
- **FR-89** Where the Unraid deployment is used, the collector shall send its records to the local server's ingest endpoint over the LAN. *(D-17.)*
- **FR-90** When the owner logs on to Windows, Task Scheduler shall start the collector. *(D-16.)*
- **FR-91** Where the on-PC deployment is used, when the owner logs on to Windows, Task Scheduler shall start the local server. *(D-16. In the Unraid deployment the container runs independently of log-on.)*

#### Local server (D-16, D-17)

- **FR-92** When a browser requests the local server's root address, the local server shall return the page. *(D-16.)*
- **FR-93** When the page requests the data snapshot, the local server shall return every current record in the record shapes. *(D-16.)*
- **FR-94** When a record in the local database changes, the local server shall send that change on the live-push stream to every open page. *(D-16.)*
- **FR-95** When the answers endpoint receives an answer record from the page, the local server shall store it in the local database. *(D-16 names the endpoint. Its use by the page depends on A-25.)*
- **FR-96** If the configured local-database path is a network path (a UNC path beginning `\\` or `//`), then the local server shall refuse to start and name the path. *(D-17; C-14. This check was chosen by the author of this document and cannot detect every network mount: A-29.)*

#### Data adapter (D-16)

- **FR-97** The page shall obtain all its data through one data-adapter interface. *(D-16.)*
- **FR-98** When the page is served by the local server, the page shall use the local API adapter. *(Selection rule chosen by the author of this document: A-29.)*
- **FR-99** When the page runs as the claude.ai artifact, the page shall use the store adapter. *(C-2 blocks the local API from the artifact: C-18.)*

#### Record shapes (D-16)

- **FR-100** The record shapes shall define session, run, project, tab, status and answer records in one definition used by the collector, the local server and both built data adapters. *(D-16 lists sessions, runs, tabs, status and answers; the project record is added for D-18: A-39. Location and format of the definition: A-29.)*
- **FR-101** The run record shape shall carry each run's start time and end time. *(Needed by the timeline view, FR-122.)*
- **FR-102** The status record shapes shall carry the last-refresh time in a record separate from `meta/status` and `status/<projectId>`. *(Feature 1. Separate so that FR-54, FR-55 and FR-144 keep their meaning.)*
- **FR-103** When the collector writes records successfully, or a refresher tick's `write_db` writes succeed, the writer shall set the last-refresh time to the time of that write. *(Feature 1. Effect on v1 plan counts: A-37.)*

#### Feature 1: stale-board warning

- **FR-104** The page shall show "data as of <last-refresh time>" in the header. *(Brief lines 169–171.)*
- **FR-105** While the last-refresh time is more than 20 minutes old, the page shall show the header's "data as of" text in the `--changes` amber token with the word "stale". *(Brief line 170: "about 2 refresh intervals (20 minutes at the 10-minute cadence)". The threshold is taken as exactly 20 minutes: A-35.)*

#### Feature 2: "Waiting on you" panel

- **FR-106** The page shall show one "Waiting on you" panel listing, across all listed sessions, every item that FR-107 to FR-110 detect, marked with the `--human` violet. *(Brief lines 172–176; D-10.)*
- **FR-107** When a session's transcript shows a question to the owner with no owner answer after it, the collector shall mark that session as paused on a question. *(Detection signal: A-30.)*
- **FR-108** When a session's last assistant message asked the owner something and the session has had no activity for longer than the running window, the collector shall mark that session as idle after asking. *(Detection signal: A-30.)*
- **FR-109** When a transcript records an action refused by the permission check, the collector shall record that refusal against its session. *(Detection signal: A-30.)*
- **FR-110** The "Waiting on you" panel shall include every assumption row the board exporter marks `needsYou` (FR-44), for every project. *(Brief line 176; D-18.)*

#### Feature 3: review findings ledger

- **FR-111** When a review-lane run's result ends with structured JSON findings, the collector shall record each finding's id, severity, title, file:line and remediation against the run's project, work item and review round. *(Brief lines 177–179. Round numbering and resolution rule: A-31; project key: A-39.)*
- **FR-112** When the findings ledger is shown, the page shall show per work item the open and resolved findings and the number of review rounds to GO. *(Brief line 179; A-31.)*

#### Feature 4: work-item status derived from runs

- **FR-113** The collector shall derive each work item's state (done, conditions open, partly built, todo) from the review verdicts of runs in that project's linked sessions whose labels name the work item's PBI id, without reading any hand-kept build state. *(Brief lines 180–181. Mapping: A-32. Replaces FR-141, and FR-43 before it.)*

#### Feature 5: test and coverage trend

- **FR-114** When a code-writer or test-writer run's result states a test count (for example "664 tests green"), the collector shall record that count on the run. *(Brief lines 182–183. Parsing rule: A-33.)*
- **FR-115** When a code-writer or test-writer run's result states a coverage percentage, the collector shall record that percentage on the run. *(Brief line 182 "test and coverage trend"; A-33.)*
- **FR-116** When the test trend is shown, the page shall plot the recorded test counts and coverage percentages per run in `seq` order. *(Brief line 183.)*

#### Feature 6: usage limit forecast

- **FR-117** While at least one usage-limit hit is recorded, the page shall show an estimated time of the next limit hit, labelled as an estimate. *(Brief lines 184–185. Method: A-34.)*
- **FR-118** If no usage-limit hit is recorded, then the page shall show "no forecast: no limit hit recorded" in place of the estimate. *(Chosen by the author of this document: A-34.)*

#### Feature 7: cost per work item

- **FR-119** The page shall show the effective usage totalled per PBI id named in the labels of a project's runs. *(Brief line 186; D-18 scopes PBI ids by project, A-39. Runs naming several ids: A-33.)*
- **FR-120** The page shall show the effective usage totalled per agent type. *(Brief line 186.)*

#### Feature 8: run detail

- **FR-121** When the owner selects a run, the page shall show that run's verdict summary, findings, files touched and duration. *(Brief lines 187–188. "Files touched" source: A-33.)*

#### Feature 9: timeline view

- **FR-122** When the timeline view is shown, the page shall draw the selected runs as bars on a real-clock time axis from each run's start time to its end time. *(Brief lines 189–190; FR-101.)*
- **FR-123** When the timeline view is shown, the page shall mark each recorded usage-limit refusal at its time on the axis. *(Brief line 190.)*
- **FR-124** When the timeline view is shown, the page shall shade every interval longer than the running window in which no shown run is active, as an idle gap. *(Brief line 189 "idle gaps". Threshold chosen by the author of this document: A-33.)*

#### Tab bar and navigation

- **FR-125** **Also a v1 defect.** While the tab bar is narrower than the total width of its tabs, the page shall show a visible cue that further tabs exist. *(Brief lines 206–208. Today `.tabs` scrolls sideways with its scrollbar hidden (`site/index.html` lines 57–58), so at about 1050 px the last tab is clipped to "Claude u…". Wrapping or fitting the tabs so that none is clipped also satisfies this FR, because no tab is then hidden. D-18's eight always-shown tabs make the overflow more likely.)*
- **FR-126** When the tab bar has overflowed, the page shall let the owner reach every tab by pointer and by the Left/Right arrow keys. *(Keeps NFR-15.)*
- **FR-127** When the owner selects a tab that lies partly outside the visible tab bar, the page shall scroll the tab bar until that tab is fully visible. *(Derived from brief lines 206–208: a clipped tab gives "no sign that more tabs exist".)*
- **FR-128** When the page is shown at a viewport width of 1050 px, the page shall show the "Claude usage" tab label in full or show the overflow cue of FR-125. *(Brief line 207.)*
- **FR-129** **D-18.** When a project is selected, the page shall show all its tabs: Overview, Spec, Assumptions, Decisions, Backlog, GitHub, Dispatch and Claude usage. *(Brief lines 154–155; `CLAUDE.md` Refresh procedure. Replaces FR-68; settles the tab-visibility question formerly in A-24.)*
- **FR-130** **D-18.** The page shall list the projects in its picker in their `board.config.json` order, followed by an "Other sessions" group. *(Brief line 154; `CLAUDE.md`. Replaces FR-66.)*

#### Answering assumptions from the board

- **FR-131** Where the answer write path is adopted by an accepted ADR (A-25), the page shall offer on each assumption row awaiting a human an *Accept* action and an *Override* action with an answer field and a note field.
- **FR-132** Where the answer write path is adopted by an accepted ADR (A-25), when the owner submits an answer, the page shall save one answer record carrying the project id, the row id, the choice, the answer, the note, the time and the writer's identity. *(Brief lines 213–214; project id added for D-18, A-39. Identity on the local server: A-28.)*
- **FR-133** If a plan would contain a write to the `answers` collection, then the refresh script shall refuse the plan: exit non-zero, name the collection on stderr, and leave no pending plan. *(Brief lines 218–221; C-16. Exit behaviour modelled on FR-49 by the author of this document.)*
- **FR-134** If a request to the ingest endpoint carries an answer record, then the local server shall reject that record and store nothing from it. *(C-16: the collector never writes answers.)*

#### Project-first navigation (D-18: being built, not verified)

Sources: brief lines 151–163 for the behaviour; `CLAUDE.md` (Projects, the data-model table and the Refresh procedure) for the document names and failure rules. None of these has been checked against the code or tests by this document (A-38).

- **FR-135** The exporters shall read the tracked projects from `projects` in `board.config.json`, each with `id`, `name`, `repoPath`, `branch`, `sessions`, `statusDoc` and `docs`. *(Brief line 159; `board.config.json` already lists platform-catalogue and dispatch-board.)*
- **FR-136** If `board.config.json` has no `projects`, then the exporters shall read the older `build.*` shape as one project whose status document is `meta/status`. *(`CLAUDE.md` Projects.)*
- **FR-137** The session exporter shall export every linked session whether or not its last activity lies within the session window. *(`CLAUDE.md` data model. Replaces FR-2.)*
- **FR-138** The session exporter shall set `project` on every session and run document to the id of the project that lists the session, or to null when no project lists it. *(`CLAUDE.md` data model.)*
- **FR-139** When the session exporter runs, it shall write one `projects/<projectId>` document per project, carrying its `name`, `repoPath`, `branch`, exported linked `sessions`, `statusDoc`, `order`, and the `runs`, `running`, `last` and `usage` combined over its linked sessions. *(Brief line 156; `CLAUDE.md` data model.)*
- **FR-140** When the board exporter runs, it shall write one `projectTabs/<projectId>.<tab>` document for each project tab whose source exists in that project's repository, and no document for a tab whose source is missing. *(`CLAUDE.md` data model. Replaces FR-42.)*
- **FR-141** The board exporter shall take each work item's state, review summary, open items and commit from `buildState` in `projects/<projectId>.json`, treating an unlisted work item as `todo`. *(`CLAUDE.md` Projects. Replaces FR-43 until FR-113 is built.)*
- **FR-142** If a project data file is not valid JSON, then the board exporter shall exit non-zero, so that the refresh script pushes nothing. *(`CLAUDE.md` Refresh procedure step 1.)*
- **FR-143** If a project's `repoPath` does not exist, then the board exporter shall skip that project with a warning on stderr. *(`CLAUDE.md` Refresh procedure step 1.)*
- **FR-144** When a project's `projects` or `projectTabs` documents, one of its linked sessions or one of their runs changes, or its live flag flips, the refresh script shall update that project's status document (`meta/status` for platform-catalogue, `status/<projectId>` otherwise) with `live` and `updatedAt`. *(`CLAUDE.md` data model. Replaces FR-54 to FR-56 for projects.)*
- **FR-145** When a project is selected, the page shall combine Dispatch, Claude usage and the Overview's agent tiles over every session linked to that project. *(Brief lines 156–157.)*
- **FR-146** When the session filter names one linked session, the page shall narrow Dispatch, Claude usage and the Overview's agent tiles to that session. *(Brief lines 156–157.)*
- **FR-147** When "Other sessions" is selected, the page shall show Overview, Dispatch and Claude usage for the chosen session linked to no project. *(Brief line 158.)*
- **FR-148** When a selected project's tab has no exported document, the page shall show that tab's "not exported yet" state. *(`CLAUDE.md` data model; dispatch-board has no spec yet, A-21.)*

## 5. Non-functional requirements

### v1 as built

- **NFR-1** While the refresher loop is active, the refresher shall start a tick every 10 minutes (the `/loop 10m` cadence, at minutes 3, 13, 23 and so on). *(v1 as built since 2026-09-11; D-14; `CLAUDE.md`.)*
- **NFR-2** The session exporter shall classify a run with no finish as `running` for at most 10 minutes after its agent transcript was last written (`runs.runningWindowMinutes` = 10). *(Met: `board.config.json`, FR-14, FR-15.)*
- **NFR-3** A session-exporter run with a warm parse cache and no transcript change shall complete within 0.2 s, as measured by the elapsed time the exporter prints. *(Target from the commissioning task's "about 0.2 s with the cache": A-19.)*
- **NFR-4** The store shall hold no more than 5000 documents. The commissioning context gave about 86 in use. The one known unused leftover is `tabs/usage`; the five `tabs/*` documents join it once D-18 ships (A-9). *(C-4.)*
- **NFR-5** Every batch the refresh script prints shall contain at most 50 writes. *(Met: `Plan.test_batches_past_the_limit`; C-3.)*
- **NFR-6** With the default privacy settings (`showFirstPrompt` false, `exclude` empty), 0 session documents shall carry a `firstPrompt` field and 0 titles shall be derived from prompt text. *(Met: `Privacy.test_first_prompt_is_off_by_default`; D-8.)*
- **NFR-7** With `showFirstPrompt` on, a published `firstPrompt` shall be at most 200 characters long. It shall contain 0 matches of these redaction patterns:
  - `sk-` followed by 16 or more key characters;
  - `gh[pousr]_` followed by 20 or more letters or digits;
  - `AKIA` or `ASIA` followed by 16 upper-case letters or digits;
  - a run of 32 or more hexadecimal characters;
  - a run of 32 or more base64-style characters containing a digit, an upper-case and a lower-case letter;
  - the value after `password`, `passwd`, `pwd`, `token`, `secret` or `api key`/`api_key`/`api-key` followed by `=` or `:`.

  *(Met: `Privacy.test_first_prompt_when_on_is_redacted`, `Redact.test_patterns`. Titles, run labels and agent descriptions are not covered: A-2.)*
- **NFR-8** Redaction shall leave text that matches no pattern in NFR-7 unchanged. Examples are prose, file paths, PBI ids and commit hashes shorter than 32 characters. *(Met: `Redact.test_ordinary_text_is_untouched`.)*
- **NFR-9** The page shall contain 0 hex, `rgb()` or `hsl()` colour literals outside its `:root` token blocks. The dark tokens sit on bare `:root`, and a light override applies under both `prefers-color-scheme: light` and `[data-theme="light"]`. *(Met: a search finds every colour literal on lines 8–24, the token blocks; D-10.)*
- **NFR-10** The page shall use the `--human` violet only for elements that represent something awaiting a human. It shall use the semantic tokens `--live`, `--go`, `--changes` and `--nogo` for run and review states. *(Partly met: the brand mark's dot is also `--human`, A-16; D-10.)*
- **NFR-11** The page shall set all text in one sans family (Schibsted Grotesk, falling back to the system sans) with tabular figures, and shall use IBM Plex Mono only for ids and commit hashes. *(Partly met: monospace is also used for paths, branch names, directory names and code spans, A-15. The fonts load from Google Fonts, which the artifact CSP permits: C-2; D-10.)*
- **NFR-12** The page shall declare every animation inside `@media (prefers-reduced-motion: no-preference)`, and shall animate pipeline arrows and run glows only while an agent is running. *(Met for arrows and run glows. The header status dot is discussed in A-16; D-10.)*
- **NFR-13** The page shall render every summary figure in the status-tile language: a bordered tile with a 3 px coloured top bar, a label, a figure and one line of context (`.tile`, `.cell`). *(Met: inspection; D-10.)*
- **NFR-14** The page shall pass 100% of store-derived text through `esc()` before inserting it into markup. Text lifted from repo documents goes through `md()` instead, which also renders only code spans and bold. *(Met: inspection; `CLAUDE.md` design rules.)*
- **NFR-15** The page shall provide:
  - a keyboard-operable tab list (`role="tab"` and `role="tabpanel"`, Left/Right arrow, Home and End keys);
  - a visible focus outline on every button and on the session picker;
  - `role="img"` with an `aria-label` on every chart SVG.

  *(Met: inspection. No conformance level is stated: A-22.)*
- **NFR-16** The automated suite shall hold 82 `unittest` cases that use only the Python standard library, pass with `python -m unittest discover -s tests`, and never touch the real `out/`, the real projects root or the live store. *(Met for the v1 baseline; brief line 32. The current tree holds 127 `def test_` methods across three files, counted by search, not run: A-38.)*

### Next iteration: not built

- **NFR-17** Refreshing the board in the next iteration shall consume 0 Claude usage and require 0 open Claude Code sessions. *(D-16 "It uses no Claude usage to refresh".)*
- **NFR-18** A change written to a transcript on the PC shall appear on an open page served by the local server within 10 minutes, without a reload. *(D-14 is the only freshness figure in the inputs; no tighter target for the local push is stated: A-35.)*
- **NFR-19** In the on-PC deployment, the local server shall listen on 127.0.0.1 only: 0 listening sockets on any other address. *(Revision instructions. Not applicable to the Unraid deployment: A-27.)*
- **NFR-20** 0 deployments shall place the local database file on a network share (SMB or NFS). The local server shall open the database only on storage local to the host it runs on. *(D-17; C-14.)*
- **NFR-21** Within 10 minutes of the owner logging on to Windows, with no Claude Code session open, the page served by the local server shall show sessions active in the last 7 days. *(D-14, D-15, D-16.)*
- **NFR-22** Every next-iteration and D-18 view shall meet NFR-9, NFR-10, NFR-13 and NFR-14, and shall use the `--human` violet only for "Waiting on you" items and assumptions awaiting a human. *(D-10.)*
- **NFR-23** 0 answer records shall carry the identity of the refresher, the collector or any agent as their writer. *(C-16.)*

## 6. Constraints

- **C-1** In v1, only a Claude session writes the store, through the Artifact tool's `write_db`. The artifact's capability rule grants write to editors (`admin`) and read to viewers (`interact`). The page could write its own store only if given write capability, and Claude writes with the owner's identity, so the store alone cannot prove that a human wrote a document. *(Brief lines 49–50 and 211–220; `CLAUDE.md`; `board.config.json`.)*
- **C-2** The artifact's content security policy permits stylesheets from `https://fonts.googleapis.com` and font files from `https://fonts.gstatic.com`. It blocks every other network host, and it blocks fetch, XHR and WebSocket connections to any external host. No external database or service (for example Firebase, or the local server) can feed the page while it remains a claude.ai artifact. *(Brief lines 50–51; corrected by the revision instructions of 2026-09-11. The page loads its fonts from `fonts.googleapis.com`, `site/index.html` lines 2–3.)*
- **C-3** A `write_db` batch accepts at most 50 writes. *(`refresh.py` `BATCH`; `CLAUDE.md` Refresh procedure step 2.)*
- **C-4** An artifact's store holds at most 5000 documents. *(Commissioning task context.)*
- **C-5** All repositories and data live on the Windows filesystem under Windows paths (for example `C:/Users/jdk/...`, `C:/Users/jdk/.claude/projects`). No WSL distro is installed, and globs must match either slash direction. *(D-2; `board.config.json`; `CLAUDE.md` privacy settings.)*
- **C-6** The v1 refresher's loop is a session-only cron. It stops when the refresher session closes, and it expires 7 days after it is created. *(Brief lines 105–106.)*
- **C-7** A cloud routine cannot read the local transcripts, so the refresher, and in the next iteration the collector, must run on this computer. *(Brief line 106; D-17.)*
- **C-8** The page is authored as page content only, with no `<html>`, `<head>` or `<body>`. A redeploy must first read the artifact, then publish with the same `url`, omitting `capabilities` and `favicon`. *(`CLAUDE.md`.)*
- **C-9** A tracked build repo does not record per-work-item build state, so until feature 4 that state comes only from a hand-kept file: `BUILD_STATE` in the v1 baseline, `projects/<projectId>.json` under D-18. *(Brief lines 21–23; D-4; `CLAUDE.md` Projects.)*
- **C-10** No session reports to the board. Transcripts that Claude Code writes under the projects root are the only source of sessions and runs. *(Brief lines 45–47; D-4.)*
- **C-11** Code changes are built by `engineering-agents:code-writer` under TDD and reviewed by `review-agents:code-reviewer` until GO. *(D-9.)*
- **C-12** Deleting store documents needs the owner's go-ahead. An automated permission check has already blocked one delete batch. *(D-11; scope against routine deletes: A-10.)*
- **C-13** The automated tests use only the Python standard library. *(`CLAUDE.md`.)*
- **C-14** The local server must not read or write the local database over a network share, because SQLite locking over SMB/NFS is unreliable. *(D-17.)*
- **C-15** Transcripts exist only on the PC running Claude Code. In the Unraid deployment the collector sends records to the server over the LAN, in the same ingest-API shape as a cloud host. *(D-17.)*
- **C-16** Plan-gate answers must be human. The refresher, the collector and every agent must never write answer records; the refresh script refuses the `answers` collection; only the page records answers, stamped with the viewer's identity. *(Brief lines 218–221; revision instructions.)*
- **C-17** The answer write path reverses the rule "the page never writes" (FR-64, brief line 19), so it needs an accepted ADR before FR-131 and FR-132 are built. No ADR exists in this repo. *(Brief line 222; A-21, A-25.)*
- **C-18** The store adapter is the only adapter usable from the artifact, because C-2 blocks connections to the local server. The local API adapter is usable only from the page as served by the local server. *(Derived from C-2 and D-16.)*
- **C-19** Build sessions run from `C:\Users\jdk`, not from a project's repository folder, so a session can be tied to a project only by listing it in `board.config.json`. *(D-18; brief lines 159–160.)*

## 7. Acceptance criteria

The inputs contain tests but no stated acceptance criteria (A-18). AC-1 to AC-47 restate the behaviour an existing named test already checks, so the v1 baseline satisfies them. AC-48 to AC-56 were derived by the author of this document and are checked by demonstration or inspection (A-17). AC-57 to AC-62 gate the requirements v1 does not yet meet. AC-63 to AC-93 gate the next iteration and D-18, and were derived by the author of this document (A-18).

### Session export and classification

- **AC-1** When the session exporter runs over one session whose code-writer finished by notification with `subagent_tokens` 5000 and `duration_ms` 1740000, it shall write exactly one session document and a run of kind `done` with `tok` 5000 and `min` 29. *(`Pipeline.test_basic_export`.)*
- **AC-2** When the session exporter runs with `sessions.days` 3, it shall write `windowDays` 3 on the session document. When it runs with `runs.runningWindowMinutes` 25, it shall write `windowMinutes` 25. *(`Pipeline.test_window_days_on_the_session_doc`, `test_window_minutes_on_the_session_doc`.)*
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
- **AC-29** When `build.sessions` names a session id with no main transcript, the session exporter shall exit non-zero and print that id on stderr. *(`Discovery.test_missing_build_transcript_fails`.)*

### Cache and file writes

- **AC-30** When the session exporter runs twice with no transcript change, it shall parse the session on the first run and parse nothing on the second. *(`Cache.test_reused_when_nothing_changed`.)*
- **AC-31** When a line is appended to a session's main transcript between runs, the session exporter shall parse that session again. *(`Cache.test_invalidated_by_a_transcript_change`.)*
- **AC-32** When `runs.runningWindowMinutes` changes from 10 to 60 for an unfinished agent whose transcript was last written 30 minutes ago, the session exporter shall change that run's kind from `killed` to `running` without any transcript change. *(`Cache.test_running_window_change_applies_without_a_transcript_change`.)*
- **AC-33** When writing a non-serialisable object fails, the file writers of the session exporter and the refresh script shall leave the previous file content intact and no temporary file behind. *(`WriteJson.test_a_failed_write_keeps_the_previous_file`, `Save.test_a_failed_write_keeps_the_previous_file`.)*

### Refresh script

- **AC-34** When the refresh script plans a fresh `out/` holding five tabs, two sessions (one a build session) and four runs, it shall plan 11 `set` writes and one `update` of `meta/status`. *(`Plan.test_first_plan_sets_everything_and_the_status`. Counts change under D-18 and when FR-103 is built: A-37, A-38.)*
- **AC-35** When a plan has been committed and only `generatedAt` then changes in `tabs/spec`, the refresh script shall report nothing to push. *(`Plan.test_generated_at_alone_is_not_a_change`.)*
- **AC-36** When one pushed run is no longer exported, the refresh script shall plan exactly one `delete`, for that run. *(`Plan.test_vanished_run_is_deleted`.)*
- **AC-37** When all four pushed runs vanish from the export, the refresh script shall exit non-zero, name `--allow-mass-delete` on stderr, print nothing on stdout, and leave no pending plan. *(`Cli.test_mass_delete_exits_non_zero_without_the_flag`, `MassDelete.test_more_than_half_is_refused`.)*
- **AC-38** When both sessions vanish from an export whose pushed state holds 16 runs and sessions, the refresh script shall refuse the plan even though only 2 documents would be deleted. *(`MassDelete.test_zero_sessions_refused_even_for_a_small_delete`.)*
- **AC-39** When the same four runs vanish and `--allow-mass-delete` is given, the refresh script shall plan their deletes and leave a pending plan. *(`MassDelete.test_allowed_with_the_flag`.)*
- **AC-40** When an exporter reports a failure, the refresh script shall exit 1, echo the failure on stderr, and leave no pending plan. *(`Cli.test_export_failure_stops_before_planning`.)*
- **AC-41** When `refresh.py --commit` is run with no pending plan, the refresh script shall exit 1 and print `nothing pending` on stderr. *(`Cli.test_commit_without_pending`.)*
- **AC-42** When only a non-build session's title changes, the refresh script shall plan exactly one `set`, of that session, and no `meta/status` update. *(`UpdatedAt.test_non_build_session_change_does_not_bump`. Count changes when FR-103 is built: A-37.)*
- **AC-43** When a non-build session's run becomes `running`, the refresh script shall plan `live` false and no `meta/status` update. *(`UpdatedAt.test_running_non_build_run_does_not_bump`.)*
- **AC-44** When a build session's run is deleted, the refresh script shall plan that `delete` plus an `update` of `meta/status`. *(`UpdatedAt.test_deleted_build_run_bumps`. Count changes when FR-103 is built: A-37.)*
- **AC-45** When a build session's run becomes `running`, the refresh script shall write `live` true and an `updatedAt` into `out/meta/status.json`. *(`UpdatedAt.test_live_flip_bumps`.)*
- **AC-46** When 60 new runs are added to the AC-34 fixture, the refresh script shall print 2 batches, the first holding exactly 50 writes. *(`Plan.test_batches_past_the_limit`.)*
- **AC-47** When `python -m unittest discover -s tests` is run from the repository root on the v1 baseline, the suite shall report 82 tests run with no failures and no errors. *(NFR-16; stale for the current tree, A-38.)*

### Refresher and page (demonstration and inspection)

- **AC-48** When a tick's `write_db` call fails, the refresher shall leave `out/.pending.json` in place and `out/.pushed.json` unchanged, so that the next tick offers the same writes again. *(FR-61; demonstration.)*
- **AC-49** When a tick's refresh script prints `nothing to push`, the refresher shall make no `write_db` call in that tick. *(FR-59; demonstration against the refresher's transcript.)*
- **AC-50** When `site/index.html` is inspected, it shall contain no call that sets, updates, adds or deletes a store document. *(FR-64; inspection. Replaced only if the answers ADR is accepted.)*
- **AC-51** When a non-build session is selected on the published page, the page shall hide the Spec, Assumptions, Decisions, Backlog and GitHub-details tabs. *(FR-68; demonstration on the v1 baseline. Replaced by AC-85 under D-18.)*
- **AC-52** When the page runs where `window.claude.use` is undefined, such as a local file preview, the page shall show "This view cannot reach the live store" and no session data. *(FR-77; demonstration.)*
- **AC-53** When a session document changes in the store while the page is open, the page shall show the change without a reload. *(FR-65; demonstration.)*
- **AC-54** When `site/index.html` is searched for hex, `rgb()` and `hsl()` colour literals, the search shall find matches only inside the `:root` token blocks. *(NFR-9; inspection. Met: lines 8–24.)*
- **AC-55** When `site/index.html` is inspected, every `@keyframes` and `animation` declaration shall sit inside `@media (prefers-reduced-motion: no-preference)`. *(NFR-12; inspection.)*
- **AC-56** When the session exporter runs a second time with no transcript change on the owner's machine, it shall print an elapsed time of 0.2 s or less. *(NFR-3; demonstration.)*

### Requirements not met in v1

- **AC-57** When a carried-over row of kind `running` belongs to an agent that cannot be re-read, and the running window has elapsed since the row's `end` time, the session exporter shall export that row with kind `killed` and verdict `no result`. *(FR-80.)*
- **AC-58** When one agent transcript holds a response whose `usage.output_tokens` is a string, the session exporter shall still export that session and every one of its runs. *(FR-81.)*
- **AC-59** When `sessions.showFirstPrompt` is the string `"false"`, or `sessions.exclude` is a string rather than a list, the session exporter shall exit non-zero with an error naming that key. *(FR-82.)*
- **AC-60** When a non-build session's running window elapses with no store change, the page shall show "session idle" in the Overview's "Running now" tile within 60 s of the header showing `Idle`. *(FR-83.)*
- **AC-61** When a verifier run completes with a result stating `exercised`, the session exporter shall record verdict `exercised`. *(FR-84.)*
- **AC-62** When the published page is opened in Chrome 20 times in a row, each time in a fresh tab, the page shall render its app bar and Overview panel on every load without a reload. *(FR-85; the load count was chosen by the author of this document, A-13.)*

### Next iteration and D-18

- **AC-63** When one line is appended to a transcript the collector has already read, the collector shall read from that file only the bytes of the appended line. *(FR-86.)*
- **AC-64** When the collector and the session exporter process the same synthetic transcripts used by `tests/`, the collector shall produce session, run and project records equal to the exporter's documents, ignoring `generatedAt`. *(FR-87.)*
- **AC-65** When the owner logs on to Windows with no Claude Code session open, the page at the local server's address shall show the sessions active in the last 7 days within 10 minutes. *(FR-90, FR-91, NFR-17, NFR-21; demonstration.)*
- **AC-66** When the listening sockets of the on-PC local server are listed (for example with `netstat -ano`), the list shall show the server bound to 127.0.0.1 only. *(NFR-19; inspection.)*
- **AC-67** When the local-database path is configured as `\\nas\share\board.db`, the local server shall refuse to start and print that path. *(FR-96.)*
- **AC-68** When a finish is appended to a running agent's transcript while the page served by the local server is open, the page shall show the run's new kind within 10 minutes without a reload. *(FR-94, NFR-18; demonstration.)*
- **AC-69** When the page requests the data snapshot, every record returned shall conform to the record shapes. *(FR-93, FR-100.)*
- **AC-70** When the collector and local-server source is searched, it shall contain no invocation of the `claude` command and no request to an Anthropic API host. *(NFR-17; inspection.)*
- **AC-71** When the Unraid container's volume mapping is inspected, the local database shall be mapped to a path on the Unraid server's own storage, not to a mounted SMB or NFS share. *(NFR-20, C-14; inspection.)*
- **AC-72** When the collector on the PC records a new run in the Unraid deployment, the page served from the Unraid server shall show that run within 10 minutes. *(FR-89, NFR-18; demonstration.)*
- **AC-73** When the page is loaded from the local server, it shall request the data snapshot from the local server; when it is loaded as the artifact, it shall open store subscriptions. *(FR-98, FR-99.)*
- **AC-74** When the last-refresh time is 25 minutes old, the page shall show the "data as of" text in the `--changes` amber token with the word "stale"; when it is 5 minutes old, the page shall show it without that styling. *(FR-104, FR-105.)*
- **AC-75** When a session's last assistant turn asks the owner a question and no owner message follows it, the "Waiting on you" panel shall list that session. *(FR-106, FR-107.)*
- **AC-76** When a transcript records an action refused by the permission check, the "Waiting on you" panel shall list that refusal with its session. *(FR-106, FR-109.)*
- **AC-77** When round 1 of a PBI-001 review lists findings F1, F2 and F3 and round 2 lists only F2, the findings ledger shall show F1 and F3 resolved, F2 open, and 2 rounds so far. *(FR-111, FR-112; A-31.)*
- **AC-78** When the latest code-reviewer run naming PBI-001 in a platform-catalogue linked session has verdict `GO` and no hand-kept build state lists PBI-001, the platform-catalogue Backlog shall show PBI-001 as done. *(FR-113; A-32.)*
- **AC-79** When a code-writer run's result contains "664 tests green", the collector shall record test count 664 on that run. *(FR-114.)*
- **AC-80** When no usage-limit hit is recorded, the page shall show "no forecast: no limit hit recorded"; when at least one is recorded, the page shall show a time labelled as an estimate. *(FR-117, FR-118.)*
- **AC-81** When two runs of one project naming PBI-001 have effective usage 100 and 50, the page shall show 150 for that project's PBI-001. *(FR-119.)*
- **AC-82** When the owner selects a code-reviewer run, the page shall show that run's verdict summary, findings, files touched and duration. *(FR-121; demonstration.)*
- **AC-83** When two runs ran from 10:00 to 10:20 and from 10:05 to 10:30, the timeline shall draw their bars overlapping between 10:05 and 10:20. *(FR-122.)*
- **AC-84** When the page is shown at a viewport width of 1050 px, the page shall show the "Claude usage" tab label in full or show a visible overflow cue. *(FR-125, FR-128; demonstration.)*
- **AC-85** When the dispatch-board project is selected, the page shall show the Overview, Spec, Assumptions, Decisions, Backlog, GitHub, Dispatch and Claude usage tabs. *(FR-129; demonstration.)*
- **AC-86** When the refresh script is given an export that includes an `answers` document, it shall exit non-zero, name the `answers` collection on stderr, and leave no pending plan. *(FR-133.)*
- **AC-87** Where the answer write path is adopted, when the owner accepts the default of an assumption row, the page shall save one answer record with that project id, row id, choice *Accept*, a time and the writer's identity. *(FR-132.)*
- **AC-88** When an ingest request carries an answer record, the local server shall reject it, and the data snapshot shall contain no answer from that request. *(FR-134.)*
- **AC-89** When `board.config.json` lists the platform-catalogue and dispatch-board projects, the session exporter shall write `projects/platform-catalogue` and `projects/dispatch-board` documents with `order` 0 and 1. *(FR-135, FR-139.)*
- **AC-90** When a linked session was last active 30 days ago, the session exporter shall still export it, with `project` set to its project's id. *(FR-137, FR-138.)*
- **AC-91** When `projects/platform-catalogue.json` is not valid JSON, the board exporter shall exit non-zero and the refresh script shall print no plan. *(FR-142.)*
- **AC-92** When a project with two linked sessions is selected and the session filter names one of them, the page shall list in Dispatch only that session's runs. *(FR-145, FR-146; demonstration.)*
- **AC-93** When the dispatch-board project is selected while `docs/backlog/specs/dispatch-board.md` does not exist, the page shall show the Spec tab's "not exported yet" state. *(FR-140, FR-148; demonstration.)*

## 8. Assumptions and open questions

Each row records a gap the inputs left, the default chosen and the impact if that default is wrong. Where a row's default reads *none — decision pending*, the inputs explicitly left the choice open between named alternatives, and no default has been invented. Where the owner asked for a recommendation on an undecided item (A-25), the recommendation is recorded beside the pending default, not as the default.

**Rows resolved by this revision** (kept for traceability; not counted as open rows): **A-1** audience → settled by D-12 (owner only). **A-3** more than one project → settled by D-13 (out of scope), then reversed by D-18 the same day: projects listed in `board.config.json` are in scope (S-14). **A-4** refresher durability and freshness → freshness settled by D-14 (10 minutes; NFR-1 updated), durability addressed by D-16 (log-on start of the next iteration). **A-7** session window and archive → settled by D-15 (7 days, no archive); the retention consequence moves to A-36. **A-14** fonts under the artifact CSP → resolved by the corrected C-2: the CSP permits Google Fonts stylesheets and font files. **A-24** tab visibility → settled by D-18: a project always shows all its tabs (FR-129), which replaces the recommended Project / Sessions split. The tab-overflow defect is not an assumption and stays as FR-125 to FR-128.

| ID | Gap | Default chosen | Impact if wrong |
|---|---|---|---|
| **A-2** | **Unredacted fields.** Session titles and folders, run labels and the usage tab's agent descriptions are published as written. AI-generated titles summarise first prompts. Priority lowered by D-12 (owner only). | Keep v1 behaviour: no redaction beyond the first prompt, and `exclude` (FR-27) is the only mitigation (S-17). | If the board is ever shared, or the Unraid deployment exposes the page to other LAN users (A-27), those fields are visible to them, partly bypassing D-8's intent. |
| **A-5** | **The v1 loop writes every tick.** The refresher's own session changes on every run, so there is always at least one write. A slower idle cadence was offered and not decided. | **None — decision pending** (owner): current every-tick cadence or a slower idle cadence. | At 10 minutes, up to 144 `write_db` batches a day while the loop runs. D-7 keeps the refresher's session on the board, so excluding it is not an available remedy. |
| **A-6** | **Two token figures disagree.** Dispatch shows `subagent_tokens` (about 2.4M); the usage tab shows effective usage (agents about 8.3M). | **None — decision pending** (owner). `CLAUDE.md`'s proposal to switch Dispatch to transcript figures is not a decision. FR-17 describes v1 as built. Cost per work item (FR-119) uses effective usage. | Two numbers keep differing about 3.5-fold. If Dispatch switches, FR-17, the swimlane box widths and the "Agent tokens" tile change. |
| **A-8** | **A snapshot of build data in a public repo.** `snapshot/` is committed to the public repository (D-1). | **None — decision pending** (owner). | The build's runs, assumptions, decisions and spec summaries are publicly readable; deleting the folder later does not remove it from git history. |
| **A-9** | **Store leftovers.** `runs/r01`–`r36` were deleted on 2026-09-10 at the switch to generated rows (brief lines 39–41; revision instructions). The only current leftover is `tabs/usage`, which the page no longer reads and the refresh script never deletes (FR-48). Once D-18 ships, `tabs/spec`, `tabs/assumptions`, `tabs/decisions`, `tabs/backlog` and `tabs/git` become leftovers too (`CLAUDE.md` Open items). `snapshot/runs` keeps `r01`–`r33`, because `r34`–`r36` were written after the snapshot. The brief's line 119 and `CLAUDE.md`'s open items still describe `r01`–`r36` as present; this document treats those lines as out of date. | **None — decision pending** the owner's go-ahead to delete the leftovers (D-11). They stay. | One unused document now, six after D-18. Whether the commissioning figure "about 86 used" (NFR-4) was counted before or after the 36 deletions is not known, so the store's current count may be about 50. The 5000 limit is far off either way. |
| **A-10** | **The scope of D-11 against the refresh script's routine deletes** (FR-47) of previously pushed documents that are no longer exported. | D-11 applies to documents the refresh script never pushed and to deletes outside the refresh procedure. Routine deletes continue, bounded by the mass-delete guard (FR-49). This includes a skipped project's `projectTabs` (FR-143, per `CLAUDE.md`). | If D-11 covers routine deletes too, every deleting tick needs the owner's approval, and sessions leaving the window stay listed until approved. FR-47 and FR-58 would change. |
| **A-11** | **How a verifier outcome maps to kind.** The verifier reports `exercised` or `fallback-declared`. | FR-84 records the word as the verdict; the kind stays `done`. | A `fallback-declared` verification looks as healthy as an `exercised` one, and the "App not verified" item clears after any verifier run. |
| **A-12** | **Remedies for the four open review LOW findings** (FR-80 to FR-83). Whether to fix them is not decided. | Record them as not met, with remedies chosen by the author of this document. No fix is scheduled and the cost is not estimated. | If the owner prefers other remedies, FR-80 to FR-83 and AC-57 to AC-60 change. Implementation cost is unknown. The collector inherits these defects through FR-87 until they are fixed. |
| **A-13** | **The published page sometimes loads blank in Chrome.** Not reproduced locally; cause unknown. | FR-85 is not met. AC-62's 20-load check was chosen by the author of this document. | Neither fix nor cost can be estimated. A fault rarer than one in 20 loads passes AC-62. |
| **A-15** | **Monospace beyond ids and hashes** (branch crumb, session folder, repo path, branch names, remotes, working-tree entries, directory names, code spans). | Read D-10 literally. NFR-11 is partly met. | If short paths and branch names count as ids, nothing changes; otherwise about eight places need restyling. |
| **A-16** | **Violet and motion outside the written rules.** The brand dot is `--human`; the header status dot pulses for "active" non-build sessions with no agent running. | NFR-10 partly met; NFR-12 met for arrows and run glows, the header dot flagged here. | Under a strict reading of D-10, two small page changes follow. |
| **A-17** | **No CI and no automated page tests.** | Keep v1 as it is. Page requirements (FR-63 to FR-79, FR-83, FR-85, and the Part B page FRs) and the demonstration ACs (AC-48 to AC-56, AC-60 to AC-62, AC-65, AC-68, AC-72, AC-82, AC-84, AC-85, AC-92, AC-93) are checked by demonstration or inspection. | Page regressions go undetected until seen. Demonstrations depend on live data, and FR-85 cannot be reproduced on demand. |
| **A-18** | **No stated acceptance criteria in the inputs.** | AC-1 to AC-47 are anchored to named tests. AC-48 to AC-93 were derived by the author of this document. | Derived ACs may gate the wrong behaviour. Owner confirmation is advisable for AC-57 to AC-62 and for AC-63 to AC-93, whose fixtures and figures the inputs do not state. |
| **A-19** | **Source and scope of the 0.2 s figure.** From the commissioning task, not measured by this document. | NFR-3 applies it to the exporter's printed elapsed time, warm cache, no transcript change. | If it meant the whole refresh-script run, NFR-3 measures the wrong span. |
| **A-20** | **Hand-kept build state drifts.** In the v1 baseline it is `BUILD_STATE` in `export_board.py`; under D-18 it moves to `projects/<projectId>.json`, still edited by hand (C-9). The v1 backlog tab also names its source as `scripts/export-board.py`, a path that does not exist. | Keep the D-4 arrangement, in whichever file D-18 puts it, until feature 4 (FR-113) replaces it. | Backlog cells misreport work-item state whenever the file lags; the wrong source path misleads anyone tracing data. |
| **A-21** | **No backlog-delivery rails in this repo** (no `backlog-delivery.config`, `docs/backlog`, ADRs). `board.config.json` already points the dispatch-board project at `docs/backlog/specs/dispatch-board.md`, `docs/backlog/BOARD.md` and `docs/adr`, none of which exists. | This PRD is the first rail; no other is created by this document. Until the planner creates the spec, the dispatch-board project's spec-derived tabs show "not exported yet" (FR-148). | The planner may need the config and `docs/backlog/` first, and C-17's ADR needs a `docs/adr/` home. The board cannot show this project's assumptions until a spec exists. |
| **A-22** | **Accessibility standard.** No conformance level is stated. | No WCAG level is claimed; NFR-15 records v1's features, and FR-126 keeps the tab list keyboard-reachable. | If a level such as WCAG 2.2 AA applies, tokens, charts and the new timeline need auditing. |
| **A-23** | **Heuristic links between runs.** `feeds` needs a PBI id or a fix word in the task description. | Accept the v1 heuristics (FR-19 to FR-21). | Some hand-offs are missing from the swimlane. Features 3, 4 and 7 also rely on PBI ids in run labels, so runs without one fall outside them. |
| **A-25** | **Answering assumptions from the board (raised 2026-09-11, not decided).** Give the page a write path (Accept / Override plus a note), or keep answers travelling through chat to the build session. Also open: how answers reach the build repo — the build session reads `answers/*` at each gate, or an importer does it on a loop. | **None — decision pending** (owner; needs an ADR, C-17). Recommended by this document: adopt the write path (FR-131, FR-132) with the provenance guards C-16, FR-133, FR-134 and NFR-23, which are specified unconditionally because they cost nothing if the path is not adopted. Transport to the build repo: none — decision pending between the two named options. | If not adopted, FR-131, FR-132, AC-87 and FR-95's use by the page drop, and answers stay in chat. If adopted without an ADR, the design rule is broken silently. Until the transport is chosen, answers recorded on the board do not reach the plan-gate ledger. |
| **A-26** | **Deployment target.** D-17 says the owner *may* host on Unraid; on-PC or Unraid is not chosen. | **None — decision pending** (owner). Requirements cover both deployments (FR-88 to FR-91, NFR-19, NFR-20). | Building both deployments costs more than building one. If Unraid is never used, FR-89, FR-134, AC-71 and AC-72 are unused work. |
| **A-27** | **Unraid network exposure and authentication.** In the Unraid deployment the server must accept the collector's records and serve the page over the LAN, so NFR-19's 127.0.0.1 binding cannot apply. The inputs state no authentication. | The Unraid server listens on the LAN; the ingest endpoint requires a shared secret configured on the collector and the server; the page is served without login on the owner's home LAN. | Any LAN device can read the board (A-2 applies) and, without the secret, could not inject records; if the owner wants login, an identity layer is needed, which also affects A-28. |
| **A-28** | **Answer provenance on the local server.** The page served locally has no claude.ai viewer identity, and agents on the same PC can reach 127.0.0.1, so the server cannot prove a human submitted an answer (C-16). | The local server stamps answers from its own page as the owner; agents are forbidden by instruction (`CLAUDE.md`) from calling the answers endpoint; FR-133 and FR-134 block the refresher and collector. Proof of human authorship is not claimed. | An agent that ignores its instructions could record a plan-gate answer indistinguishable from the owner's. Closing this needs an interactive confirmation or login, at an unestimated cost. |
| **A-29** | **Local server interface details** the inputs leave open: port, endpoint paths, live-push transport, where the record-shape definition lives and in what format, the adapter selection rule (FR-98, FR-99), the UNC-path check (FR-96), and whether the v1 refresher and artifact keep running once the local app ships. | Chosen at solution-spec time. The adapter follows where the page is loaded; FR-96 rejects UNC paths only; the v1 refresher and artifact keep running until the owner retires them. | FR-96 cannot detect a network drive mapped to a letter or a share mounted into a container, so NFR-20 rests on AC-71's inspection. Running both paths doubles the moving parts until one is retired. |
| **A-30** | **"Waiting on you" detection signals.** The inputs do not say how a transcript shows a pending question, an idle-after-asking session or a permission refusal. | FR-107 uses a question tool call with no later owner message; FR-108 uses a last assistant message ending in a question mark plus the running window; FR-109 uses the transcript's record of a permission denial. The exact record types are to be confirmed against real transcripts. | If the transcripts do not record these reliably, the panel misses items or lists false ones; the cost of the detectors is unestimated until the record types are confirmed. |
| **A-31** | **Findings ledger rules.** The inputs give the finding fields but not how rounds are numbered or when a finding counts as resolved. | A round is each successive review-lane run naming the same PBI id within one project. A finding is resolved when a later round for that work item does not list its id. A result with malformed findings JSON is recorded with no findings and keeps its verdict. | If reviewers renumber ids between rounds, findings show resolved wrongly; if resolution requires explicit confirmation, FR-112 and AC-77 change. |
| **A-32** | **Work-item status mapping.** The brief says verdicts give done / conditions open / partly built, without a mapping. | Latest code-reviewer verdict for the PBI id within the project's linked sessions: `GO` → done; `GO-WITH-NOTES` or `GO-WITH-CONDITIONS` → conditions open; `CHANGES-REQUIRED`, `NO-GO`, or a finished build run with no review → partly built; no runs → todo. Linked sessions stay exported beyond the 7-day window (FR-137). | A mapping the owner reads differently misreports the Backlog. Work done in a session that is not linked to the project ages out after 7 days (D-15) and is lost to the derivation. |
| **A-33** | **Parsing and attribution rules for features 5, 7, 8 and 9.** The inputs give one example ("664 tests green") and no rules. | Test count: the first integer followed by "tests". Coverage: the first percentage next to "coverage". A run naming several PBI ids has its usage split equally among them. "Files touched" are the paths in the agent's file-editing tool calls. An idle gap is an interval longer than the running window with no active run. | Reports worded differently yield no or wrong figures; a different attribution changes per-work-item costs; the timeline's gaps shift with the threshold. |
| **A-34** | **Usage limit forecast method.** The inputs name the inputs (rate of use, past limit hits with reset times) but no method, and no plan meter exists (S-18). | Estimate the capacity as the effective usage spent between the previous reset and the last recorded hit, and project the current hourly rate forward to that capacity. No forecast is shown without a recorded hit (FR-118). | Accuracy is unknown and may be poor; the plan's actual limit may not track effective usage. The owner could act on a misleading estimate. |
| **A-35** | **Freshness target for the local push and the stale threshold.** D-14 says 10 minutes is enough; the inputs give no tighter target for the local push. The stale threshold is "about" 20 minutes. | NFR-18 uses 10 minutes; FR-105 uses exactly 20 minutes. | If the owner expects near-real-time updates from the local push, NFR-18 tightens and the collector's read interval becomes a design driver. |
| **A-36** | **Retention with no archive (D-15).** The inputs do not say whether the local database deletes records older than 7 days or merely stops showing them. v1's store drops them (FR-47), and a quiet week can trip the mass-delete guard (FR-49). | The local database keeps only what the page shows: records of sessions active in the last 7 days plus all linked sessions (FR-137); older records are deleted. The v1 guard behaviour is unchanged. | Features 3, 4, 5 and 7 lose history for sessions not linked to a project. After a quiet week, the v1 guard refuses every tick until someone re-runs with `--allow-mass-delete`. |
| **A-37** | **The last-refresh write changes v1 plan contents.** FR-103 adds one write to every successful refresher tick, so the exact counts in AC-34, AC-42 and AC-44 and their tests rise by one. | Accept the change: those ACs and tests are updated when FR-103 is built. Status-document semantics (FR-54, FR-55, FR-144) stay unchanged because the last-refresh time lives in a separate record. | If the owner prefers no v1 change, the stale-board warning works only in the local app, and the artifact keeps having no stale indicator (the original gap behind feature 1). |
| **A-38** | **Moving baseline.** Decision 18 was added to the brief while this revision was being written, and the owner chose to build it before the revision finished. The working tree is part-way through: `board.config.json` already uses `projects`; the exporters and tests reference `projectTabs`; `CLAUDE.md` describes the new data model; `tests/` holds 127 `def test_` methods (a search count, not a run); `site/index.html` does not yet read `projects` or `projectTabs`. The D-18 default session or project selection on first load is not stated. | Part A describes v1 as built before the D-18 work, which is the state the first draft read and the evidence its named tests cite. FR-129, FR-130 and FR-135 to FR-148 take their detail from `CLAUDE.md` and are marked "being built, not verified". This document ran nothing. | Once D-18 ships, the Part A requirements in the supersession table no longer describe the tree, and NFR-16 and AC-47 (82 tests) are already stale. If the build diverges from `CLAUDE.md`, FR-135 to FR-148 are wrong. A re-baseline of Part A is needed after D-18 lands. |
| **A-39** | **D-18's effect on the next iteration.** D-16's record shapes list sessions, runs, tabs, status and answers, with no project record. Row ids such as `A-1` and PBI ids such as `PBI-001` repeat across projects' ledgers and backlogs. | Add a project record to the record shapes (FR-100), and key answers, findings, derived work-item state and cost per work item by project id plus row or PBI id (FR-111, FR-113, FR-119, FR-132). | Without the project key, one project's answer, finding or cost is attributed to another. If the owner prefers D-16's record list unchanged, FR-100 and AC-64 change. |

## 9. Requirements report

```json
{
  "schema_version": "1",
  "report": {
    "agent": "requirements-author",
    "as_of_date": "2026-09-11",
    "scope": "Revision 2 of the plan-ready PRD for the dispatch board: v1 as built (before the D-18 work), project-first navigation being built (D-18), and the next iteration (not built), from docs/brief/raw-notes.md (re-read in full, including decision 18 added during this revision), the revision instructions of 2026-09-11, CLAUDE.md, README.md, board.config.json, site/index.html, the exporters and tests; written to docs/prd/dispatch-board.md",
    "summary": "12 intended outcomes (O-1..O-7 v1, O-12 D-18, O-8..O-11 next iteration); 16 in-scope and 15 out-of-scope items; 18 owner decisions (D-1..D-18; D-12..D-18 added, D-13 superseded by D-18); 148 EARS functional requirements (FR-1..FR-79 v1 as built, FR-80..FR-85 not met in v1, FR-129, FR-130 and FR-135..FR-148 D-18 being built and not verified, the rest of FR-86..FR-134 next iteration not built); 23 measurable NFRs (NFR-17..NFR-23 next iteration); 19 constraints; 93 EARS acceptance criteria (AC-1..AC-47 anchored to existing tests on the v1 baseline, AC-48..AC-93 derived); 33 open assumption rows, 6 of which carry 'none - decision pending' (A-5, A-6, A-8, A-9, A-25, A-26), A-25 with a recommendation recorded beside the pending default; rows A-1, A-3, A-4, A-7, A-14 and A-24 resolved by D-12..D-18 and the corrected C-2. Conditions: feasible is weak, evidenced by row A-12 (remedies and cost of FR-80..FR-83 unestimated), row A-28 (answer provenance cannot be proven on the local server), row A-30 (waiting-on-you detection signals unconfirmed against real transcripts) and row A-34 (forecast method of unknown accuracy); able_to_be_validated is weak, evidenced by row A-17 (no CI and no page tests; page FRs and demonstration ACs rest on demonstration or inspection), row A-18 (AC-48..AC-93 author-derived and need owner confirmation) and row A-38 (the D-18 requirements are unverified against a tree still being changed, and NFR-16/AC-47 are stale for it). Every input was readable; none was missing.",
    "verdict": "DONE-WITH-CONDITIONS",
    "sensitivity": "sensitive"
  },
  "grades": {
    "complete": "pass",
    "consistent": "pass",
    "feasible": "weak",
    "comprehensible": "pass",
    "able_to_be_validated": "weak"
  },
  "ears_conformant_count": 241,
  "assumptions_open_questions_count": 33
}
```
