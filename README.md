# Dispatch board

Live dashboard of an agent-built software project: agent runs, review verdicts, spec, assumptions
awaiting a human, decisions, backlog, repository status and Claude usage.

- `site/index.html` — the dashboard page, published as a claude.ai artifact
- `exporters/export_board.py` — spec, assumptions, decisions, backlog and git data from the build repo
- `exporters/export_sessions.py` — every recent Claude Code session (title, usage) and its agent runs, from the transcripts
- `exporters/refresh.py` — runs the exporters and lists the store writes that changed since the last push
- `tests/` — `python -m unittest discover -s tests`
- `board.config.json` — artifact URL, build repo and build sessions, session discovery and privacy settings
- `snapshot/` — copy of the board's store at the time this project was created

See `CLAUDE.md` for the data model and the refresh procedure.
