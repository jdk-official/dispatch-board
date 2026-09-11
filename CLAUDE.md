# Dispatch board

A live dashboard of an agent-built software project. It shows which Claude Code agents ran, what
came back from review, what the spec says, which assumptions are waiting on a human, the backlog,
the repository, and Claude usage. It currently tracks the **platform-catalogue** build at
`C:/Users/jdk/platform-catalogue` (branch `build/logic-core`).

## The published page

- Live page: https://claude.ai/code/artifact/09d7c7e7-26ae-4ed3-9c7f-34ba86925be6 (title "Live Dispatch Board", private to the owner until shared).
- Source: `site/index.html`. It is authored as page content only — no `<html>`, `<head>` or `<body>`; the Artifact tool wraps it.
- **To update it from a new session:** first `Artifact` with `action: "read"` and that `url`, then publish with `file_path: site/index.html` **and the same `url`**. Publishing without `url` creates a separate artifact. Omit `capabilities` and `favicon` on redeploys so the stored ones carry forward.
- Capabilities: `db` only, rule `{ path: "", read: "interact", write: "admin" }` — viewers read, only editors write. The page never writes; the building session does.

## How data gets onto the page

The page holds no data. It subscribes to the artifact's store and re-renders on every change.

| Store path | Written by | Shape |
|---|---|---|
| `sessions/<id>` (one per Claude Code session active in the last `sessions.days` days; id = session id) | `exporters/export_sessions.py`, discovered under `sessions.projectsRoot` | `title`, `project`, `cwd`, `firstPrompt` (only with `sessions.showFirstPrompt`, secrets redacted), `start`, `last`, `build` (listed in `build.sessions`, so the project tabs describe it), `windowDays` (`sessions.days`, for the picker's labels), `windowMinutes` (`runs.runningWindowMinutes`: how long after its last activity the page still shows a session as live), `runs`, `running`, `usage` (the usage tab's data) |
| `runs/<id>` (one per agent run; id = the subagent's agent id) | `exporters/export_sessions.py`, from each session's transcripts; in-line orchestrator work comes from `runs.manual` in `board.config.json` | `session`, `seq` (order within the session), `lane` (`orch`/`req`/`plan`/`cw`/`tw`/`cr`/`ver`/`human`), `label`, `kind` (`running`/`done`/`go`/`changes`/`nogo`/`killed`; a builder that reports NOT-DONE is `changes`), `verdict` (short text), `tok`, `min`, optional `from` / `feeds` (another run id: hand-off / verdict fed back), optional `group` (parallel batch id) |
| `meta/status` | `title`, `message`, `metrics`: the orchestrating session by hand. `live`, `updatedAt`: `exporters/refresh.py`, only when build data changed (a `tabs/*` doc, a build session, or one of its runs) or `live` flipped | `title`, `message`, `live` (bool), `updatedAt` (ISO), `metrics` `{ tests, testFiles, coverage, bundle, measuredAt, measuredOn }` |
| `tabs/spec`, `tabs/assumptions`, `tabs/decisions`, `tabs/backlog`, `tabs/git` | `exporters/export_board.py` | read from the build repo's spec, PRD, brief, ADRs, local review notes and git |

`snapshot/` holds a copy of every store document as of the move (2026-09-10). Restore any of it with `write_db` (`file_path` per document).

## Refresh procedure

No session reports to the board; a refresher session reads what sessions leave on disk. Sessions are
discovered automatically. The page has a session picker: Dispatch, usage and the Overview follow the
selected session; the project tabs (spec, assumptions, decisions, backlog, GitHub) show only for build
sessions. Add a session id to `build.sessions` in `board.config.json` to mark it as a build of the
tracked project.

1. `python exporters/refresh.py` runs both exporters (`export_board.py`, `export_sessions.py`) and prints the store writes that changed since the last push (`nothing to push` if none). Entries point at files under `out/`. If it exits non-zero instead, push nothing:
   - `export_sessions.py` fails when `sessions.projectsRoot` is missing or a `build.sessions` transcript cannot be found, rather than exporting an empty board. A single malformed transcript only costs that session or agent (a warning on stderr).
   - **Mass-delete guard:** if the export has no sessions, or would delete more than half of the pushed `runs` and `sessions`, refresh.py refuses and leaves nothing pending. Check the projects root and transcripts; only if the deletions are really intended, re-run as `python exporters/refresh.py --allow-mass-delete`.
2. `Artifact` `action: "write_db"`, `db_op: "batch"`, `url` = the live page, `writes` = the printed array (it splits into several batches past 50).
3. Only after the write succeeds: `python exporters/refresh.py --commit`. If a write fails, skip this; the next run re-offers the same changes.

To keep the board live, run the refresher on a loop from a session opened in this folder:
`/loop 2m Refresh the dispatch board: follow the Refresh procedure in CLAUDE.md; if refresh.py prints "nothing to push", end the tick without writing.`

`title`, `message` and `metrics` in `meta/status` are still written by hand when the stage changes.
Rows derive from transcripts, so labels are the agents' task descriptions and `tok` is the agent's
reported `subagent_tokens` (context size at finish), falling back to the last transcript response.

Session privacy, in `sessions` in `board.config.json`:

- `exclude` (default `[]`): fnmatch globs matched against each session's working folder (`cwd`, with either slash direction) and against its project folder name under `projectsRoot` (e.g. `C--Users-jdk-private*`). Matching sessions are never read, cached or exported.
- `showFirstPrompt` (default `false`): publish each session's first prompt as `firstPrompt`. Obvious secrets (`sk-…`, `gh[pousr]_…`, `AKIA…`, hex or base64 runs of 32+ characters, `password=` / `token=` values) are replaced with `[redacted]` first. While it is off, a session without a title shows its short id rather than its prompt.
  - Session titles are published whatever this setting says, and Claude Code's AI-generated titles are a summary of the first prompt. Redaction is not applied to titles, run labels (the agents' task descriptions) or the usage tab's agent descriptions, so a secret in any of those is published as written; exclude the session if that matters.

Tests: `python -m unittest discover -s tests` (stdlib only). They build synthetic transcripts and `out/` folders in temporary directories, pass their own config, and never touch the real `out/` or the live board.

Per-PBI build state is not recorded anywhere in the build repo, so it lives in `BUILD_STATE` at the top of `exporters/export_board.py` and must be edited by hand as work items move. `NOT_WORKED_OUT` there maps the brief's open questions to ledger rows.

## Design rules (the owner's stated preferences)

- **Professional dashboard, not an editorial page.** No poster hero, no oversized display type. Overview first: summary tiles, backlog cells, pipeline, needs-attention list, usage, recent activity.
- The owner **liked the status-tile language**: bordered tile, 3px coloured top bar, small label, figure, one-line context. Reuse it everywhere (`.tile`, `.cell`).
- The owner **disliked wide monospace text**. One sans (Schibsted Grotesk) for everything, tabular figures; IBM Plex Mono only for ids and commit hashes.
- Dark-first tokens on bare `:root`, light override under `prefers-color-scheme: light` and `[data-theme="light"]`. Colours only through tokens. One bold colour, `--human` violet, reserved for things awaiting a human; semantic colours `--live` / `--go` / `--changes` / `--nogo` are separate.
- Motion only when it is true: pipeline arrows animate only while an agent is running; `prefers-reduced-motion` respected.
- All data rendered through `esc()`; repo text may carry `code` spans and bold via `md()` — nothing else.

## Open items

- **Two token figures disagree.** Dispatch shows agents' self-reported tokens (~2.4M); the usage tab shows transcript-derived effective usage (agents ~8.3M). Switch Dispatch to transcript figures so there is one number.
- **Leftover documents.** The store still holds the hand-written `runs/r01`…`r36` and a stale `tabs/usage`. The page never shows those runs, because they have no `session` field and it lists only the selected session's runs. `refresh.py` never deletes them either: it deletes only documents recorded in `out/.pushed.json`, and these never were. Remove them by hand with `write_db` delete ops if wanted, and tell the build session to stop writing `runs` rows by hand.
- Inferred links are heuristics: `feeds` needs a PBI id or the word review/notes/LOWs/fix in the task description; runs without one (e.g. "Align types.ts…") get no link.
- The usage tab is not a plan meter: transcripts record only the moments a limit refused a request.
- The Browser pane cannot open files outside an open project folder; preview `site/index.html` from this project instead.

## The build it tracks (paused)

platform-catalogue, branch `build/logic-core`, 12 commits, not merged to `master`, no remote. Remaining: fix PBI-009's two review items; finish PBI-010 (profile picker, onboarding-plan view); PBI-011 delivery checks and a verifier pass; PBI-012 Pages workflow file; local merge; handover. The plan gate still needs the owner's confirmation of 20 assumptions. Nothing is pushed or deployed without the owner saying so.
