# Dispatch board

Live dashboard of agent-built software projects: agent runs, review verdicts, spec, assumptions
awaiting a human, decisions, backlog, repository status and Claude usage, per project.

- `site/index.html` — the dashboard page, published as a claude.ai artifact
- `exporters/export_board.py` — spec, assumptions, decisions, backlog and git data from each project's repo
- `exporters/export_sessions.py` — every recent Claude Code session (title, usage), its agent runs, and a summary per project, from the transcripts
- `exporters/export_catalogue.py` — every agent and skill in the agent-catalog marketplace, grouped by plugin, for the Agent catalogue tab
- `exporters/refresh.py` — runs the exporters and lists the store writes that changed since the last push
- `exporters/board_config.py` — the project list and the catalogue paths, read the same way by every exporter
- `projects/<projectId>.json` — hand-kept build state per project (work-item states, the brief's open questions)
- `local/collector.py` — reads the transcripts into the local SQLite database; `local/server.py` — serves the page and its data on 127.0.0.1
- `local/deploy/` — the log-on start: `tasks.py` registers the two Task Scheduler tasks, `run_local.py` runs a target with its output captured to a log
- `tests/` — `python -m unittest discover -s tests` and `node tests/page.test.mjs`
- `local/tests/` — `python -m unittest discover -s local/tests` (the local-first app's record shapes and SQLite schema; Python 3.11 or later)
- `board.config.json` — artifact URL, the projects (repo, branch, build sessions, doc paths), session discovery and privacy settings
- `snapshot/` — copy of the board's store at the time this project was created

**Retired 2026-09-19 (PBI-037).** The published artifact above is frozen: nothing publishes to it, runs the refresher, or hand-edits `meta/status` or `status/*` (including platform-catalogue's hand-written `title`, `message` and `metrics`) — see CLAUDE.md for the no-write rule and the owner-only revert. The live board is the local app below.

## Running the board on this PC

The local-first app needs no open session and no Claude usage: the collector reads the transcripts on disk,
and the local server serves the page from what it wrote.

```
python local/deploy/tasks.py show        # read the two task definitions before registering anything
python local/deploy/tasks.py install     # create or replace them; no administrator needed
python local/deploy/tasks.py start       # run them now, instead of logging off and on
python local/deploy/tasks.py status
python local/deploy/tasks.py uninstall
```

Then open `http://127.0.0.1:8765/` (the port is `local.port` in `board.config.json`). The page updates by
itself; it never needs reloading.

- **`install` is create-or-update.** Re-run it after moving the checkout or changing interpreter, and run
  `uninstall` before deleting the checkout. Task Scheduler keeps the tasks in a `Dispatch board` folder, which
  it leaves behind empty after an uninstall.
- **The tasks run as you, with an interactive token and no elevation**, and carry no password.
- **Both logs are in `out/local/logs/`**, one file per target, each line stamped with the time. They are the
  only place a scheduled process's output goes, so read them first when the board looks stale. Each is capped
  at 1 MB with 5 rotated files beside it — about 6 MB per target at the very most.
- **If a log stops growing, look in `%TEMP%\dispatch-board-<target>-log-failure.txt`.** A log that cannot be
  opened or written, at log-on or later, keeps its target running and sends its lines and the reason there
  instead, and the log is written again once the obstacle is gone. Only if that file cannot be written either
  does the task stop before its target starts, with Last Run Result 73.
- **`uninstall` exits non-zero if a task could not be removed, or its removal could not be confirmed**; a task
  that was never installed is not a failure, whatever language Windows displays.
- **Start order does not matter.** The collector owns the database; the server opens it read-only and answers
  503 until it exists, then serves it with no restart. The server's task waits 15 seconds after log-on so the
  first page load usually has data already.
- Run either one in the foreground to watch it: `python local/collector.py` or `python local/server.py`. Stop
  the scheduled one first (`tasks.py stop`), so two collectors are not writing at once.

See `CLAUDE.md` for the data model and the refresh procedure.
