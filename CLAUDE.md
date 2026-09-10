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
| `runs/<id>` (one per agent run) | the orchestrating session, by hand, as it dispatches and receives agents | `seq` (order), `lane` (`orch`/`req`/`plan`/`cw`/`tw`/`cr`/`ver`/`human`), `label`, `kind` (`running`/`done`/`go`/`changes`/`nogo`/`killed`), `verdict` (short text), `tok`, `min`, optional `from` / `feeds` (another run id: hand-off / verdict fed back), optional `group` (parallel batch id) |
| `meta/status` | the orchestrating session | `title`, `message`, `live` (bool), `updatedAt` (ISO), `metrics` `{ tests, testFiles, coverage, bundle, measuredAt, measuredOn }` |
| `tabs/spec`, `tabs/assumptions`, `tabs/decisions`, `tabs/backlog`, `tabs/git` | `exporters/export_board.py` | read from the build repo's spec, PRD, brief, ADRs, local review notes and git |
| `tabs/usage` | `exporters/export_usage.py` | read from Claude Code transcripts for the sessions in `board.config.json` |

`snapshot/` holds a copy of every store document as of the move (2026-09-10). Restore any of it with `write_db` (`file_path` per document).

## Refresh procedure

1. `python exporters/export_board.py` → `out/{spec,assumptions,decisions,backlog,git}.json`
2. `python exporters/export_usage.py` → `out/usage.json` (add new session ids to `board.config.json` first)
3. `Artifact` `action: "write_db"`, `db_op: "batch"`, one `set` per file into collection `tabs` with `doc_id` = file stem and `file_path` pointing at it.
4. Update `meta/status` (`update`) with the current stage and `updatedAt`.
5. Write or update `runs/<id>` rows as agents start (`kind: "running"`) and finish (verdict, `tok`, `min`).

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
- `runs` rows have no generator — they were seeded by hand from the overnight build. A generator could derive them from the session transcripts (`subagents/*.meta.json` gives agent type and task).
- The usage tab is not a plan meter: transcripts record only the moments a limit refused a request.
- The Browser pane cannot open files outside an open project folder; preview `site/index.html` from this project instead.

## The build it tracks (paused)

platform-catalogue, branch `build/logic-core`, 12 commits, not merged to `master`, no remote. Remaining: fix PBI-009's two review items; finish PBI-010 (profile picker, onboarding-plan view); PBI-011 delivery checks and a verifier pass; PBI-012 Pages workflow file; local merge; handover. The plan gate still needs the owner's confirmation of 20 assumptions. Nothing is pushed or deployed without the owner saying so.
