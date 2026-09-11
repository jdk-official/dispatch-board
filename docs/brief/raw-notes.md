# Dispatch board: raw notes (reverse-engineered brief)

Written 2026-09-11 from the working system and the owner's decisions in the session that built it
(sessions 2026-09-10/11). These are notes, not requirements: they record what exists, what the
owner decided, and what is known to be missing. Later docs (PRD, spec, backlog) are derived from them.

## What it is

A live, read-only dashboard of Claude Code agent activity on this computer. It shows, per Claude
Code session, which agents ran, what came back from review, tokens and minutes, and Claude usage.
For a session marked as a build of a tracked project it also shows that project's spec,
assumptions awaiting a human, decisions, backlog and repository state.

Audience: the owner (one person). The page is a claude.ai artifact, private until shared.

## What exists today (repo C:\Users\jdk\dispatch-board, public on GitHub jdk-official/dispatch-board)

- `site/index.html`: the whole page (HTML, CSS, JS in one file). It reads the artifact's document
  store via `window.claude.use('db')` and re-renders on every change. It never writes.
- `exporters/export_board.py`: reads the tracked build repo (spec, PRD, brief, ADRs, review notes,
  git) and writes the project tabs as JSON. Per-work-item build state is hand-maintained in
  `BUILD_STATE` at the top of the file, because the build repo does not record it. That file is
  currently edited by the build session.
- `exporters/export_sessions.py`: discovers Claude Code transcripts under
  `~/.claude/projects`, and for every session active in the last 7 days writes a session document
  (title, folder, activity, usage) and one row per agent run (lane, verdict, tokens, minutes,
  hand-off and feedback links, parallel groups). It has a parse cache and per-agent failure
  isolation.
- `exporters/refresh.py`: runs both exporters, diffs their output against the last push, prints
  the store writes that changed, and records them with `--commit` after the write succeeds. It has
  a mass-delete guard.
- `tests/`: 82 stdlib unittest cases on synthetic transcripts (`python -m unittest discover -s tests`).
- `board.config.json`: artifact URL, tracked build repo, build sessions, session discovery and
  privacy settings, manual orchestrator rows.
- `snapshot/`: the store as of 2026-09-10, before the move to generated rows.
- `CLAUDE.md` / `README.md`: data model, refresh procedure and design rules.

Store collections: `sessions/<id>`, `runs/<agentId>`, `tabs/{spec,assumptions,decisions,backlog,git}`,
`meta/status`. One leftover the page no longer reads: `tabs/usage`. The hand-written `runs/r01`–`r36`
were deleted at the switch to generated rows on 2026-09-10 (`snapshot/runs` keeps r01–r33; r34–r36
were written by the build session after the snapshot and deleted with the rest).

## How it stays live

A separate Claude Code session (the "refresher") runs a 2-minute loop. Each run executes
`refresh.py`, writes the printed changes to the artifact store with the Artifact tool's `write_db`,
then runs `refresh.py --commit`. No session reports to the board itself.

Only a Claude session can write the store: the Artifact tool is the only writer. The artifact
CSP blocks every other network host, so an external database (e.g. Firebase) cannot feed the page
while it stays an artifact.

## Decisions the owner made (with reasons given)

1. **Public GitHub repo** jdk-official/dispatch-board (2026-09-10). The owner chose public over
   private when asked.
2. **Repos stay on the Windows filesystem.** The owner dropped the "repos live in WSL" rule; no WSL
   distro is installed.
3. **Live updates by a refresher loop** (option 1 of 3), chosen as the lowest-cost option that
   actually updates. Rejected for now: hooks in the build session (option 2: relies on the model
   acting), and moving off the artifact to GitHub Pages plus a database (option 3: loses the private
   claude.ai page and means a page rewrite).
4. **Runs are derived from transcripts**, not hand-written. The build session was told to stop
   writing `runs` rows, and to keep writing only `meta/status` title/message/metrics and `BUILD_STATE`.
5. **One dashboard per session**, through a session picker. Sessions are **auto-discovered: every
   session active in the last 7 days** (the owner chose this over "only sessions with agents" and "a
   hand-kept list").
6. **Project tabs only for build sessions**, i.e. those listed in `build.sessions`.
7. **The refresher's own session stays on the board**: the owner wants to see it.
8. **Privacy defaults.** First prompts are not published unless `showFirstPrompt` is on, and obvious
   secrets are redacted when it is. `exclude` globs hide sessions. (This came from a code-review
   finding; the owner accepted the default.)
9. **Process: code changes go through the catalogue agents.** `engineering-agents:code-writer` builds
   under TDD, then `review-agents:code-reviewer` gives GO/NO-GO, looping until GO. The owner asked
   "why aren't we using agents for this?" after a solo build. That solo build's first review was
   NO-GO (one HIGH finding: a single bad file froze the board).
10. **Design preferences** (stated earlier, recorded in CLAUDE.md): a professional dashboard, not an
    editorial page. Status tiles (bordered, 3px coloured top bar, label, figure, one-line context).
    One sans (Schibsted Grotesk) with tabular figures; monospace only for ids and hashes, and no wide
    monospace text. Dark-first tokens. Violet (`--human`) only for things waiting on a human. Motion
    only when true (an agent is actually running).
11. **Deleting store documents needs the owner's go-ahead.** An automated permission check blocked
    a batch that deleted `tabs/usage`, so leftovers stay until the owner approves.

## Review history of the current code

Three rounds by `review-agents:code-reviewer`: NO-GO (1 HIGH, 6 MEDIUM, 5 LOW), then
GO-WITH-CONDITIONS (1 MEDIUM regression, 4 LOW), then GO with 4 LOW notes, still open:

- A carried-over row can stay "running" while its agent file is unreadable, which keeps the build
  "live".
- One malformed usage line in an agent transcript can drop the whole session.
- Config values are not type-checked. A quoted `"false"` turns first-prompt publishing on, and a
  quoted `exclude` glob hides every session.
- For non-build sessions, the session tiles say "active" after the header shows Idle, until the next
  data change.

## Known gaps and issues (observed, not yet decided)

- **Verifier runs show no outcome.** `review-agents:verifier` reports `exercised` or
  `fallback-declared`, not GO or NO-GO, so its runs show "finished".
- **The loop writes every tick.** The refresher's own session changes every run, so there is always
  one write even when nothing else happened. The owner was offered a slower idle cadence; no
  decision yet.
- **The loop is not durable.** It dies when the refresher session closes, and the session-only cron
  expires after 7 days. A cloud routine cannot read local transcripts.
- **Two token figures disagree.** Dispatch shows agents' self-reported `subagent_tokens`; the usage
  tab shows transcript-derived effective usage.
- **Single tracked project.** `export_board.py` hard-codes the platform-catalogue paths (spec, PRD,
  brief) and `BUILD_STATE`. The same build repo now also holds `docs/prd/architect-tool.md` and
  more briefs, so a second project in the same session is not representable.
- **BUILD_STATE is hand-edited** and drifts from reality unless the build session updates it.
- **No CI.** Tests run only by hand. The page has no automated tests: its changes were checked by
  `node --check`, by reading, and by one local harness render.
- **The published page sometimes loads blank** in Chrome until reloaded. Not reproduced locally;
  cause unknown.
- **Sharing exposes every session's title and folder.** AI-generated titles summarise first prompts,
  and redaction does not cover titles, run labels or agent descriptions.
- **Store leftovers** await deletion: `tabs/usage`, plus the five retired single-project `tabs/*` once project-first navigation ships. `runs/r01`–`r36` are already gone.
- **No backlog-delivery rails in this repo**: no config, BOARD, ADRs or PRD. The build it tracks
  (C:\Users\jdk\platform-catalogue) uses `docs/brief`, `docs/prd`, `docs/adr`, `docs/backlog/`
  (BOARD.md, specs/, done-log.md) and `backlog-delivery.config`.

## Owner's answers (2026-09-11)

12. **Only the owner views the board.** It is not shared, so privacy work beyond the current
    defaults is not a priority.
13. **One tracked project.** Multi-project support is out of scope.
14. **Freshness: 10 minutes is enough.** The refresher loop moved from every 2 minutes to every 10
    (at minute 3, 13, 23 and so on).
15. **Show sessions from the last 7 days, for now.** No archive of older sessions or runs.

## Direction for the next iteration (owner, 2026-09-11)

16. **Local first, hosting later.** Build a local version that no longer depends on a Claude session:
    - A collector (the existing exporter logic, reading new transcript lines incrementally) writes
      to **SQLite**.
    - A small local web server serves the page, a data snapshot, a live push stream, and an answers
      endpoint.
    - The page gets one data adapter (artifact store today, local API next, hosted API later).
    - It starts at log-on via Task Scheduler. It uses no Claude usage to refresh.
    - Define one set of record shapes (sessions, runs, tabs, status, answers) now, so hosting later
      only swaps the storage and the transport.
17. **The owner may host it on their Unraid server.** SQLite was chosen partly for this: the server
    and its database can run as a container on Unraid. Transcripts exist only on the PC running
    Claude Code, so the collector stays on the PC and sends records to the server over the LAN
    (the same ingest-API shape as a cloud host). The server must not read SQLite over a network
    share, because SQLite locking over SMB/NFS is unreliable. The cloud option (Azure Static Web
    Apps, Functions, a database, Entra ID) remains a later alternative.

18. **Project-first navigation (owner, 2026-09-11; supersedes decision 13 "one project" and the
    tab-visibility recommendation). This is the build priority.**
    - Each project has a spec, a backlog and build sessions.
    - The owner picks a **project** from the dropdown and sees its spec, requirements, assumptions,
      decisions, backlog and repo.
    - Dispatch and usage for a project combine the runs of every session building it, with a filter
      to narrow to one session.
    - Sessions linked to no project stay viewable on their own.
    - Projects and their build sessions are listed in `board.config.json`, because build sessions run
      from `C:\Users\jdk`, not the repo folder.
    - The first two projects are **platform-catalogue** and **dispatch-board** (this repo), so the dispatch
      board's own PBIs appear on the board once they exist.
    - The owner chose to build this now, before the PRD revision and pbi-plan are finished.

## Candidate features for the next iteration (owner-approved for the PRD, 2026-09-11; not built)

The owner asked for all of these to go into the plan. None has been built.

1. **Stale-board warning.** Show "data as of <time>" in the header, and flag it (amber) when the last
   push is older than about 2 refresh intervals (20 minutes at the 10-minute cadence). The loop can
   die silently when its session closes or the cron expires after 7 days.
2. **"Waiting on you" panel.** One list across all sessions of everything blocked on the owner:
   - sessions paused on a question to the owner, with no answer yet in the transcript;
   - sessions idle after asking the owner something;
   - actions refused by the permission check;
   - plan-gate assumptions awaiting confirmation.
3. **Review findings ledger.** Reviewers end their result with structured JSON findings (id, severity,
   title, file:line, remediation). Collect them per work item and per review round: open vs
   resolved, and rounds to GO.
4. **Work-item status derived from runs**, replacing the hand-edited `BUILD_STATE` in
   `export_board.py`. Review verdicts on runs naming a PBI give done / conditions open / partly built.
5. **Test and coverage trend.** Code-writer and test-writer reports state counts (e.g. "664 tests
   green"); plot them per run.
6. **Usage limit forecast.** From the current rate of use and past limit hits (which are recorded
   with reset times), estimate when the next limit will be hit.
7. **Cost per work item.** Total effective usage by the PBI ids in run labels, and by agent type.
8. **Run detail.** Select a run to see the agent's result: verdict summary, findings, files
   touched, duration. Today only a one-line verdict shows.
9. **Timeline view.** Runs on a real clock: parallel batches, idle gaps, and where usage limits cut
   work off.

## Future iteration (recorded idea, not in this plan)

- **Phone notifications** from the refresher (a review returns NO-GO, a run is cut off, the build
  goes idle, a session is waiting on the owner). The owner deferred this on 2026-09-11.

## Raised by the owner, 2026-09-11 (not yet decided)

- **"The dashboard doesn't display all tabs. Should it?"** This covers two different things:
  - **By design:** Spec, Assumptions, Decisions, Backlog and GitHub show only when a build session
    is picked. With one tracked project (decision 13), those tabs describe the project, not a
    session, so hiding them when another session is picked only removes information.
    Recommendation: always show the project tabs, and split the navigation into a **Project** group
    (Overview, Spec, Assumptions, Decisions, Backlog, GitHub) and a **Sessions** group (picker,
    Dispatch, Usage). That way the picker visibly scopes only the session tabs.
  - **A bug:** the tab bar scrolls sideways with its scrollbar hidden. At narrower widths (about
    1050px) the last tab is cut off ("Claude u…") with no sign that more tabs exist. It needs a
    visible overflow cue, or tabs that wrap or fit.
- **"What about input into assumptions?"** The owner wants to answer plan-gate assumptions from the
  board. Today the page never writes (design rule), and answers travel through chat to the build
  session (the build's recent "PRD rev 3 with owner answers" run). Considerations for the plan:
  - The page can write to its own store if it is given write capability. Each assumption would get
    **Accept the chosen default** or **Override** with the owner's answer and a note, saved as
    e.g. `answers/<row>`, with a time and the writer's identity.
  - The answers must reach the build repo, where the plan gate records them. Either the build
    session reads `answers/*` at each gate and writes them into the PRD/spec ledger, or an importer
    does it on the refresher's loop.
  - **Provenance.** Claude writes the store with the owner's identity (Artifact `write_db`), so the
    store alone cannot prove a human gave an answer. Plan-gate answers must be human. So the
    refresher and every agent must never write `answers/*`; `refresh.py` should refuse that
    collection. Only the page records answers, stamped with the viewer's identity.
  - This reverses a design rule ("the page never writes"), so it needs an ADR.
  - The same mechanism could later record plan approval, and acceptance of review conditions.

## Open questions still unanswered

- Should the refresher survive the session closing (a local scheduled task)?
- Is the snapshot of build data in a public repo acceptable long term?
