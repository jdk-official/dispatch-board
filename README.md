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
- `tests/` — `python -m unittest discover -s tests` and `node tests/page.test.mjs`
- `local/tests/` — `python -m unittest discover -s local/tests` (the local-first app's record shapes and SQLite schema; Python 3.11 or later)
- `board.config.json` — artifact URL, the projects (repo, branch, build sessions, doc paths), session discovery and privacy settings
- `snapshot/` — copy of the board's store at the time this project was created

See `CLAUDE.md` for the data model and the refresh procedure.
