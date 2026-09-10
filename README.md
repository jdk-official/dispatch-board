# Dispatch board

Live dashboard of an agent-built software project: agent runs, review verdicts, spec, assumptions
awaiting a human, decisions, backlog, repository status and Claude usage.

- `site/index.html` — the dashboard page, published as a claude.ai artifact
- `exporters/export_board.py` — spec, assumptions, decisions, backlog and git data from the build repo
- `exporters/export_usage.py` — Claude usage from Claude Code transcripts
- `board.config.json` — artifact URL, build repo path, sessions to include in usage
- `snapshot/` — copy of the board's store at the time this project was created

See `CLAUDE.md` for the data model and the refresh procedure.
