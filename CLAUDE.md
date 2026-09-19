# Dispatch board

A live dashboard of an agent-built software project. It shows which Claude Code agents ran, what
came back from review, what the spec says, which assumptions are waiting on a human, the backlog,
the repository, and Claude usage. It tracks the projects listed under `projects` in `board.config.json`:
**platform-catalogue** (`C:/Users/jdk/platform-catalogue`, branch `build/logic-core`) and **dispatch-board**
(this repo, branch `main`).

## The published page

**Retired 2026-09-19 (PBI-037).** The published artifact is frozen: nothing publishes to it, and no PBI republishes it from now on, including PBI-010, which is in flight. This section's text stays until PBI-038 removes the push path. The live board is the local app at http://127.0.0.1:8765. The revert: until PBI-038 merges, restarting `/loop 10m Refresh the dispatch board: follow the Refresh procedure in CLAUDE.md.` restores the artifact, and only the owner asks for that.

- Live page: https://claude.ai/code/artifact/09d7c7e7-26ae-4ed3-9c7f-34ba86925be6 (title "Live Dispatch Board", private to the owner until shared).
- Source: `site/index.html`. It is authored as page content only — no `<html>`, `<head>` or `<body>`; the Artifact tool wraps it.
- **To update it from a new session:** first `Artifact` with `action: "read"` and that `url`, then publish with `file_path: site/index.html` **and the same `url`**. Publishing without `url` creates a separate artifact. Omit `capabilities` and `favicon` on redeploys so the stored ones carry forward.
- Capabilities: `db` only, rule `{ path: "", read: "interact", write: "admin" }` — viewers read, only editors write. The page never writes; the building session does.
- **Switching the published page to project-first navigation** (while the published page is still the version from before projects): do these three steps back to back.
  1. Push the data (the Refresh procedure below).
  2. Publish `site/index.html` straight away.
  3. Reload any open copy of the page, because an open copy keeps running the script it loaded.

  Between steps 1 and 2 the old page still works from the retired `tabs/*` and each session's `build` flag, which marks only platform-catalogue's sessions. A copy of the new page opened before the first project push moves from "Other sessions" to a project once the projects arrive, unless the viewer chose "Other sessions".

## How data gets onto the page

The page holds no data. It reaches its data through a **data adapter chosen at load** (PBI-006), and re-renders on every change:

- **The store adapter** — the published artifact. It subscribes to the artifact's store, exactly as before, and is what the live page runs.
- **The local API adapter** — the page served by the local server (PBI-005). It fetches `/api/snapshot` once, then opens `/api/events?since=<version>`, applying `change` events in place and re-fetching on `reset`.

The adapter is chosen by the **`window.__DISPATCH_LOCAL__` marker** the local server injects, *not* by the absence of `window.claude`: an artifact published without its `db` capability also lacks `window.claude`, and that case must still show the store's out-of-reach board. Both of the marker's URLs are required and must be same-origin; a marker that names only one, or carries a cross-origin, `javascript:` or `data:` URL, falls back to the store adapter.

A local server that refuses, times out, returns 503, returns unreadable JSON, or returns 200 with a body that is not a snapshot all degrade the same honest way: the offline board, "This view cannot reach the local server.", no stream, and a `console.warn` — never a silent blank board. A genuinely empty `records` map is a different case and still draws an ordinary empty board.

Both adapters render the same board; `tests/page.test.mjs` pins that with a ten-panel deep-equal in which no panel is empty on either side.

| Store path | Written by | Shape |
|---|---|---|
| `sessions/<id>` (one per Claude Code session active in the last `sessions.days` days, plus every session linked to a project; id = session id) | `exporters/export_sessions.py`, discovered under `sessions.projectsRoot` | `title`, `folder` (the working folder's name), `cwd`, `firstPrompt` (only with `sessions.showFirstPrompt`, secrets redacted), `start`, `last`, `project` (the id of the project whose `sessions` list it, or null), `build` (true only for sessions of the project whose `statusDoc` is `meta/status`, platform-catalogue: what copies of the page from before projects call the build, shown with the retired `tabs/*`; nothing else reads it), `windowDays` (`sessions.days`, for the picker's labels), `windowMinutes` (`runs.runningWindowMinutes`: how long after its last activity the page still shows a session as live), `runs`, `running`, `usage` (the usage tab's data; since PBI-012 each of its `subagents` entries also carries `pbis`, the PBI ids named in its task description, which feed the usage tab's cost-per-work-item table), `skillUses` (`{ "<skill id>": { count, last } }` from the main transcript only, `{}` when unused; `last` is left out when no use had a readable time), optional `waiting` (PBI-009, `waiting_of()`'s result verbatim: `questions` `[{at, question, source: 'ask'|'prose'}]` — at most one, the unanswered `AskUserQuestion` or else the closing prose question; `refusals` `[{at, kind: 'permission-rule'|'automode-blocked'|'user-rejected', tool, detail}]`; optional `more`, the count left out past `WAITING_CAP` (5) items total, question first then the newest refusals, each `question`/`detail` cut to `WAITING_TEXT` (300) characters. Left out entirely when nothing is waiting. An item clears once a later record `is_owner_message()` accepts follows it — a message the owner actually typed; a compaction summary (`isCompactSummary: true`) and the literal interrupt marker text `[Request interrupted by user for tool use]` are Claude Code's own writes, not the owner, and clear nothing. Carries no elapsed time: age (48 hours) and D2's idleness (against `windowMinutes`) are judged by the page, not the exporter, so the document is byte-identical between exports of one transcript) |
| `runs/<id>` (one per agent run; id = the subagent's agent id) | `exporters/export_sessions.py`, from each session's transcripts; in-line orchestrator work comes from `runs.manual` in `board.config.json` | `session`, `project` (its session's project, or null), `seq` (order within the session), `lane` (`orch`/`req`/`plan`/`cw`/`tw`/`cr`/`ver`/`human`/`other`; `other` is an agent type the exporter does not map to a lane), `label`, `kind` (`running`/`done`/`go`/`changes`/`nogo`/`killed`; a builder that reports NOT-DONE is `changes`; a verifier whose result states `exercised` or `fallback-declared` has that word as its `verdict` and stays `done`. The word is read in any case. An outcome label (the JSON `outcome` key or `Outcome:`) decides when there is one; without it, every other mention counts together, whether `Verdict:`-labelled, bold, code-quoted or bare. A word after a negation such as "not exercised", "could not be exercised", "unable to be exercised", "rather than exercised" or "instead of being exercised" is skipped, and wherever both words are found, `fallback-declared` wins), `verdict` (short text), `tok`, `min`, optional `from` / `feeds` (another run id: hand-off / verdict fed back), optional `group` (parallel batch id), and on subagent runs only `agentType` (the raw meta value, e.g. `review-agents:code-reviewer`; left out when the meta has none) and `start` (its launch time; left out when unknown). `runs.manual` rows carry neither. Since PBI-012, a code-writer or test-writer run (lane `cw` or `tw`) may also carry **`tests`** and **`coverage`**: the run's own stated test count and coverage, never a reviewer's quoted figure, which would otherwise put the same point on the trend twice. Each is parsed from the result: a count, plain or comma-grouped, followed by the word "tests", or a percentage straight before or after the word "coverage" (a `:` or `=` may also sit between "coverage" and a number after it), with only spaces or tabs between the number and the word and both on the same line; "tests" immediately followed by `/` is a path rather than a count and is skipped, and a coverage figure over 100 is dropped as not a percentage. Since PBI-014, two more optional fields. **`findings`**: on a code-review round whose result carries a readable findings block, that round's own findings (id, severity, title, `file:line`, remediation) — `[]` when the round listed none, and the key left out when nothing readable was found; the project's findings ledger (`projectTabs/<projectId>.findings`) keys the same findings by round, not by run. **`files`**: the files the run edited, taken from the inputs of its successful edit tool calls (a refused or failed edit is not counted), each published **relative to the project's `repoPath`**; a path the board cannot place inside the repository — one edited in a git worktree of it, one genuinely outside it, a `~/` or drive-relative path, or a path from a session linked to no project (which has no `repoPath` to place it against; edit tool inputs are always absolute, so such a path is always unplaceable — the rule itself would pass a bare relative path through with its folders) — is published as `…/<file name>` with its folders withheld. A code-reviewer run makes no edits, so its detail shows the files its findings name instead |
| `catalogue/index` (one document) | `exporters/export_catalogue.py`, from the agent-catalog marketplace clone and the installed-plugins file named in `catalogue` in `board.config.json` (read only, never written) | `generatedAt`, `source` `{ marketplacePath, installedPath }`, `plugins` `[{ plugin, purpose, purposeFull, installed, agents, skills }]` (plugins with neither agents nor skills are left out), `entries` `[{ id: "<plugin>:<name>", kind: "agent"/"skill", plugin, name, description, installed }]`, sorted by plugin, then agents first, then name. It holds no usage: the Agent catalogue tab derives that from runs' `agentType` and sessions' `skillUses`, so the document changes only when the catalogue does |
| `projects/<projectId>` (one per entry in `projects` in `board.config.json`) | `exporters/export_sessions.py` | `name`, `repoPath`, `branch`, `sessions` (its linked sessions that were exported), `statusDoc`, `order` (position in the config: the picker's order), `runs`, `running`, `last` (latest activity across its sessions), `usage` (all its sessions combined, in the same shape as a session's `usage`) |
| `projectTabs/<projectId>.findings` (one per project with a finished review round) | `exporters/export_sessions.py` | The review findings ledger (PBI-011). Per work item: the open findings, the resolved findings, the rounds so far and the rounds to GO. A finding listed in one round and absent from the next is resolved; one still listed is open (AC-77). Each finding carries the round it was first and last seen, its severity, title, `file:line` and remediation. A round whose result carries no parseable findings block still counts toward `rounds`, but only a round that carries one decides which findings are **open** — which is why this project's own reviews, whose findings go to a file rather than the reply, rarely resolve anything in the ledger. `source` is optional in the shared `tab` shape; `generatedAt` is required, and the exporter writes both. The document is deleted when a project has no finished round. **Ownership:** `projectTabs` has two writers — `export_board.py` owns the five tabs below, `export_sessions.py` owns this one, and neither touches the other's. Anything computing a "tabs I own" set must use its own constant, never `records.TAB_NAMES`, which lists all six. |
| `projectTabs/<projectId>.<tab>` (tab = `spec`, `assumptions`, `decisions`, `backlog`, `git`) | `exporters/export_board.py` | read from the project's repo: the files named in its `docs`, its local review notes and git, plus its data file (see Projects). `backlog` holds `source`, `generatedAt`, `pbis` (the spec's PBI list with each item's build state), `board` (the data file's `boardNote`) and `later` (`[{ title, description }]`, one per list item (a `-`, `*`, `+` or `1.` marker indented by at most three spaces) under the spec's `### Future iterations (not planned)` heading, up to the next heading of that level or higher; `[]` without the heading). A list line indented further (four spaces or a tab) is a nested item: not an idea of its own; it and the lines that continue it are appended to its idea's description as text, marker included. An indented line after a blank line (a loose list's nested item or paragraph) is appended too, so nothing written under an idea is lost; a blank line followed by an unindented line that starts no idea, or a horizontal rule, ends the idea. A `later` title is the bullet's first bold span, less a trailing colon, and its description the text after it, less a leading colon; a bullet with words before its bold span keeps the whole bullet as its description, and one without a bold span is all title. The Backlog tab shows `later` as a "Later" group of neutral idea cards below the work items, never counted in the PBI totals, the backlog cells or "Needs attention". `git` holds the repository facts (`branch`, `defaultBranch`, `head`, `remotes` (the `git remote -v` lines, with any `user:token@` removed from their URLs so no credential is published), `ahead`, `shortstat`, `dirty`, `tracked`, `byDir`, `commits`) and, only for a project whose `origin` remote is on github.com, `pulls`: `[{ number, title, state, url, branch, updatedAt }]`, the 20 most recently updated pull requests (any state) that `gh pr list --state all --search sort:updated-desc --limit 20 --json number,title,state,url,headRefName,updatedAt --repo <owner>/<name>` prints when run in the repo (owner and name from the origin URL, so gh cannot pick another base repository; `--repo` is left out when the origin's path is not just an owner and a name) with a 15 s timeout, most recently updated first (without the sort qualifier gh would pick the 20 most recently created). `state` is `OPEN`, `MERGED` or `CLOSED` and `branch` is the head ref; any other value shows as a neutral tag with the raw text. When gh is missing, not signed in, exits non-zero, times out or prints malformed JSON, `pulls` is left out (a warning on stderr) and the rest of the tab exports as usual; a project without a GitHub origin has no `pulls` and no warning. The GitHub tab shows `pulls` as a "Pull requests" panel (it says they are not available when `pulls` is absent), linking only `https://github.com/` URLs; each OPEN one is also "PR #n awaiting your merge" in the Overview's "Needs attention". A tab whose source has never existed is not written (spec, assumptions, decisions and backlog need the spec; git needs a git repository), and the page shows its "not exported yet" state. Once exported, a tab whose source goes missing keeps its last export (a warning on stderr), marked with `carriedSince`: the time the carry began, in UTC with a `Z` (e.g. `2026-09-11T08:30:00Z`). It is set on the first run that keeps the tab, left as it is (and the file byte for byte) on later runs while the source is still missing, and gone once the source comes back and the tab is rebuilt; a tab that exports normally never has it. A kept file that is not a readable JSON object (truncated, not UTF-8, nested too deeply to parse, or holding a lone surrogate escape such as `\ud800`) is kept unmarked, exactly as it was, with a warning on stderr naming the file, so the page shows no carried warning for it |
| `meta/status` (platform-catalogue's `statusDoc`) | `title`, `message`, `metrics`: its build session by hand. `live`, `updatedAt`: `exporters/refresh.py`, only when that project's data changed (its `projects`/`projectTabs` docs, a linked session, or one of that session's runs) or `live` flipped | `title`, `message`, `live` (bool), `updatedAt` (ISO), `metrics` `{ tests, testFiles, coverage, bundle, measuredAt, measuredOn }` |
| `status/<projectId>` (every other project's `statusDoc`) | `live`, `updatedAt`: `exporters/refresh.py`, under the same rule; created with `set` on its first write, merged into after. `title`, `message`, `metrics` are optional, by hand | same shape as `meta/status` |
| `meta/lastRefresh` (one document) | `exporters/refresh.py`, on every plan (FR-103's refresher half, PBI-008); the collector writes the same record locally (PBI-019) | `at` (the time of the write, to the second: the refresher writes UTC with a `Z`, the collector the equivalent ISO offset form `+00:00`; both are valid, so never compare them as strings) and `writer` (`refresher` or `collector`). The page's header reads it as "data as of <time>", shown in the `--changes` amber token with the word "stale" once it is more than 20 minutes old, and shown not at all when the document is absent or its `at` is not a readable time. The path is reserved: no `statusDoc` may take it |

Retired: `tabs/spec`, `tabs/assumptions`, `tabs/decisions`, `tabs/backlog`, `tabs/git` (the single-project tabs, replaced by `projectTabs`). The page no longer reads them, and `refresh.py` never deletes them: it deletes only in the collections it manages (`runs`, `sessions`, `projects`, `projectTabs`, `catalogue`). They stay in the store until the owner approves deleting them.

`snapshot/` holds copies of the store's documents: `meta/` and `runs/` as of the move (2026-09-10), and `tabs/` the six retired `tabs/*` documents as the store held them on 2026-09-11, so its copies date from their last writes on 2026-09-10 and 2026-09-11. Restore any of it with `write_db` (`file_path` per document).

## Answers are the owner's

No agent writes answers or calls an answers endpoint. Answers to the plan gate's questions come from the owner and stay in chat; if answering from the board is ever built, only the page records an answer, stamped with the viewer's identity. `refresh.py` refuses any export that holds an `answers` document (see the answers guard below).

## Refresh procedure

**Retired 2026-09-19 (PBI-037).** This procedure stays below until PBI-038 removes the push path, but nothing runs it. From the freeze on, nothing republishes the artifact, runs the refresher or writes its store: no `write_db` call and no hand edit of `meta/status` or `status/*`, including the paused platform-catalogue build's hand-written `title`, `message` and `metrics` further down this section. The documented revert (the loop below, owner-only) is the only exception; any other such write restarts PBI-038's T4.4 undo window. A frozen board looking stale is expected and is not a reason to restart the loop.

No session reports to the board; a refresher session reads what sessions leave on disk. Sessions are
discovered automatically. The page's picker lists the projects, then "Other sessions". A project always
shows all its tabs (Overview, Spec, Assumptions, Decisions, Backlog, GitHub, Findings ledger, Dispatch,
Agent catalogue, Claude usage). Dispatch, the Agent catalogue's usage figures, usage and the Overview's agent tiles combine
every session linked to the project, and a session filter narrows them to one. "Other sessions" is the
session-scoped view (Overview, Dispatch, Agent catalogue, usage) for sessions linked to no project. Add a
session id to a project's `sessions` in `board.config.json` to link it.

Since PBI-012, the Dispatch tab plots a Test count and a Coverage chart below the swimlane, one point per run
that stated a readable figure, in run order; the Claude usage tab gains a Cost per work item table (project
view only, effective usage split evenly across the PBI ids a run names) and a Cost per agent type table.

1. `python exporters/refresh.py` runs the three exporters, in this order: `export_board.py`, `export_sessions.py`, `export_catalogue.py`. It prints the store writes that changed since the last push. Since PBI-008 built FR-103's refresher half, every plan also carries one `set` of `meta/lastRefresh`, so a tick always has at least one write and the script no longer prints `nothing to push`; a plan the guards refuse exits non-zero and leaves nothing pending. Entries point at files under `out/`. If it exits non-zero instead, push nothing:
   - `export_sessions.py` fails when `sessions.projectsRoot` is missing or a linked session's transcript (`projects[].sessions`) cannot be found, rather than exporting an empty board. A single malformed transcript only costs that session or agent (a warning on stderr); a response whose token counts are not numbers, or a line nested too deeply to parse, costs only that record. An agent that cannot be re-read keeps its last row, and a session that cannot be parsed keeps its last export; either way, a row kept as `running` is exported as `killed` with verdict `no result` once `runs.runningWindowMinutes` has passed since its end (the session is still re-read next run).
   - `export_sessions.py` also fails (exit 2, with an error naming the key) when a value under `sessions` or `runs` does not have its documented type: `days` and `runningWindowMinutes` numbers, `projectsRoot` a string, `exclude` a list of strings, `showFirstPrompt` `true` or `false` (the string `"false"` is refused), `manual` a list. Each `runs.manual` row needs a string `id` and `label`, and its `id` becomes the file name `out/runs/<id>.json` on the Windows refresher, so it must be both the local app's run-id form (one path segment: not empty, no `/` or `\`, no control characters, not `.` or `..`) and a safe Windows file name (no `:`, `*`, `?`, `<`, `>`, `|` or `"`; no leading dot; no trailing dot or space; not a device name `CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9` or `LPT1`-`LPT9`, in any case, with or without an extension); `verdict` and `from`, when given, are strings; `lane` (default `orch`) is one of `orch`, `req`, `plan`, `cw`, `tw`, `cr`, `ver`, `human`, `other`, and `kind` (default `done`) one of `running`, `done`, `go`, `changes`, `nogo`, `killed`. A bad row fails with an error naming it.
   - `export_board.py` fails when a project data file (`projects/<projectId>.json`) is not valid JSON, rather than resetting that project's build state. A tab that was exported before but cannot be rebuilt (the project's `repoPath` is missing or moved, its spec was renamed, git is unavailable) keeps its last export, with a warning on stderr, while the other projects refresh as usual. The kept tab gets `carriedSince` (the time the carry began) on the first such run, so that run pushes it once; later runs leave it unchanged, and the next export after the source comes back drops it. Fix the source; a project's tabs go only when it is removed from `projects`.
   - `export_board.py` lists a GitHub project's pull requests with the GitHub CLI, so the refresher needs `gh` installed and signed in (`gh auth status`). Without it the git tab is exported without `pulls`, with a warning on stderr; that is never a failure.
   - Both exporters fail when `projects` in `board.config.json` is not a list of objects, or a project's `id` or `statusDoc` is unusable (`meta/lastRefresh` is reserved for the local app's last-refresh record, so it cannot be a `statusDoc`).
   - `export_catalogue.py` fails (exit 2) only when a `catalogue` value in `board.config.json` is not a string (or the block is not an object). Everything else is a warning on stderr, and the export goes on:
     - a missing marketplace folder, a missing `plugins/` folder or one that cannot be listed, or no agents and no skills at all: the last `out/catalogue/index.json` is kept untouched, so the tab is never blanked;
     - an unreadable, non-UTF-8 or malformed agent or skill file, or one whose `<plugin>:<name>` is not a safe id: that entry is left out;
     - a plugin's `agents/` or `skills/` folder that cannot be listed: its entries are left out;
     - a missing or malformed plugin manifest: that plugin's purpose is its name;
     - a missing, unreadable or wrongly shaped installed-plugins file: every entry is marked not installed.
   - **Mass-delete guard:** refresh.py refuses, and leaves nothing pending, if the export has no sessions, would delete more than half of the pushed `runs` and `sessions`, would delete any `projects/*` document, would delete every pushed `projectTabs` document of a project, or would delete `catalogue/index`. Check the projects root, the transcripts, `projects` and `catalogue` in `board.config.json`; only if the deletions are really intended (for example, a project was removed from the config), re-run as `python exporters/refresh.py --allow-mass-delete`.
   - **Answers guard:** refresh.py refuses any export that holds a document in the `answers` collection (a file under `out/answers/`). It names the collection on stderr, exits non-zero and leaves nothing pending, and `--allow-mass-delete` does not lift it. No exporter writes answers, so find what put the file there and remove it.
2. `Artifact` `action: "write_db"`, `db_op: "batch"`, `url` = the live page, `writes` = the printed array (it splits into several batches past 50).
3. Only after the write succeeds: `python exporters/refresh.py --commit`. If a write fails, skip this; the next run re-offers the same changes.

Retired 2026-09-19 (PBI-037): the loop below is not run day to day; it is the documented revert, run only when the owner asks for it, until PBI-038 merges.

To keep the board live, run the refresher on a loop from a session opened in this folder. The
owner's freshness target is 10 minutes (2026-09-11); only the owner views the board:
`/loop 10m Refresh the dispatch board: follow the Refresh procedure in CLAUDE.md.`

`title`, `message` and `metrics` in `meta/status` are still written by hand when the stage changes.
Rows derive from transcripts, so labels are the agents' task descriptions and `tok` is the agent's
reported `subagent_tokens` (context size at finish), falling back to the last transcript response.

Session privacy, in `sessions` in `board.config.json`:

- `exclude` (default `[]`): fnmatch globs matched against each session's working folder (`cwd`, with either slash direction) and against its project folder name under `projectsRoot` (e.g. `C--Users-jdk-private*`). Matching sessions are never read, cached or exported.
- `showFirstPrompt` (default `false`): publish each session's first prompt as `firstPrompt`. Obvious secrets (`sk-…`, `gh[pousr]_…`, `AKIA…`, hex or base64 runs of 32+ characters, `password=` / `token=` values) are replaced with `[redacted]` first. While it is off, a session without a title shows its short id rather than its prompt.
  - Session titles are published whatever this setting says, and Claude Code's AI-generated titles are a summary of the first prompt. Redaction is not applied to titles, run labels (the agents' task descriptions) or the usage tab's agent descriptions, so a secret in any of those is published as written; exclude the session if that matters.
  - Skill ids taken from transcripts (`skillUses` keys) are published unredacted, like titles; that is acceptable because only the owner views the board (PRD D-12). A `Skill` call's arguments are never read or stored.
  - Pull request titles and branch names (the git tab's `pulls`) are published as GitHub has them, unredacted, like session titles; that is acceptable for the same reason, since only the owner views the board. The `exclude` setting does not apply to them.
  - A run's `findings` and `files` (PBI-014) are published unredacted, like run labels. Finding titles and remediations are the reviewer's own words, and `files` names the files a run edited. A path inside the project's repository is published relative to it, so a sensitive file or folder name inside the repository appears as written; folders are withheld only for a path the board cannot place inside the repository, which is published as `…/<file name>`. Neither field is redacted, which is acceptable for the same reason, since only the owner views the board. The `exclude` setting does apply: an excluded session's runs are never read or exported, so neither field is published for them.
  - A session's `waiting` question text and refusal `detail` (PBI-009) are published through `redact()` and cut to `WAITING_TEXT`, unlike a redacted `firstPrompt`: `waiting` is published whatever `showFirstPrompt` says, since `session_doc()` does not gate it. The `exclude` setting does apply: an excluded session is never parsed, so it never has a `waiting` field.

The Agent catalogue, in `catalogue` in `board.config.json`:

- `marketplacePath` (default `~/.claude/plugins/marketplaces/agent-catalog`): the marketplace clone. Agents are `plugins/<plugin>/agents/<name>.md`, skills `plugins/<plugin>/skills/<name>/SKILL.md` (frontmatter `name` and `description`), and each plugin's purpose line is the first sentence of `.claude-plugin/plugin.json`'s `description`, cut to 120 characters.
- `installedPath` (default `~/.claude/plugins/installed_plugins.json`): its `<plugin>@agent-catalog` keys mark plugins installed.
- Both are strings; a leading `~` is expanded. Other marketplaces are not read.
- Usage comes from the transcripts. An agent use is a run's `agentType`. A skill use is a `Skill` tool call (`input.skill`) or a plugin command the owner typed (`/<plugin>:<skill>`) in a session's main transcript. On the page, a namespaced id counts toward the entry with that id, and a bare `Skill` id toward the one catalogue skill with that name. Anything else, such as `Plan`, `general-purpose` or `artifact-design`, is listed under "Outside the catalogue".
- **Known limitation:** bare slash commands the owner types, such as `/loop`, are not counted (a bare `Skill` call is). Skill use inside agent transcripts is not counted either. A forked session that repeats an earlier session's history counts those uses twice in the all-sessions figures.

Tests, run all three (they are the `[test_commands]` in `backlog-delivery.config`):

- `python -m unittest discover -s tests` (stdlib only). They build synthetic transcripts, marketplaces and `out/` folders in temporary directories, pass their own config (including a `catalogue` block), and never touch the real `out/`, `~/.claude` or the live board.
- `node tests/page.test.mjs` (node built-ins only, no `npm install`). It runs the inline script of `site/index.html` against a stub DOM and a fake store, and checks the project picker, the session filter, the project Overview, the Agent catalogue tab, the Backlog's Later group, the pull requests (the GitHub tab's panel and the Overview's awaiting-merge items), the findings ledger (PBI-011), the run detail (a picked run's verdict summary, findings, files edited and duration, PBI-014), the test count and coverage trend charts and the cost per work item and per agent type tables (PBI-012), the "Waiting on you" panel (PBI-009), and the data-adapter seam (PBI-006: the store adapter and the local API adapter render the same board); it exits non-zero on the first failed check. Because each tab renders in its own try/catch, any `console.error` the page logs that a check does not expect also fails the suite. `PAGE_HTML=<path>` points it at another copy of the page (default `site/index.html`).
- `python -m unittest discover -s local/tests` (stdlib only; needs Python 3.11 or later). It tests the local-first app: its record shapes and SQLite schema (`local/records.py`, `local/schema.py`), the collector (`local/collector.py`), and the local server (`local/server.py`, PBI-005) — including its 127.0.0.1 binding, the Host allow-list and Origin check, the read-only database opener, the network-path guard and the live event stream. It also runs a conformance check that every document the exporters write fits the shapes; that check drives the real exporters rather than hand-building documents, which is how PBI-026 proved the `findings` tab is accepted. `test_deploy_e2e.py` then starts the collector and the server as two real processes, through the same wrapper Task Scheduler launches, and measures the deployed pair: the snapshot, `netstat` showing 127.0.0.1 only, and a finish appended to a transcript arriving on an already-open event stream; one case runs the tasks' exact command line, with no arguments for the target, in a copy of the checkout, so the default config, database, page and log folder are exercised too. It costs about 15 seconds and needs no network.

## The local app on this PC

The collector and the local server start at log-on through Task Scheduler. `python local/deploy/tasks.py`
takes `show`, `install`, `uninstall`, `start`, `stop` and `status`; `install` is create-or-update (it registers
by XML with `schtasks /F`), so re-running it after moving the checkout is the way to fix the paths. README.md
has the operator's version of this.

- **Each task launches `local/deploy/run_local.py --target collector|server`, never the target directly.**
  Task Scheduler discards a process's stdout and stderr, and without them a refused collector pass or a server
  that would not bind leaves the board stale with no visible reason. The wrapper calls the target's `main()` in
  this process with both streams pointed at a rotating log in `out/local/logs/`, stamps every line with the
  time, catches a crash with its traceback, and exits with the code the target returned, so Task Scheduler's
  Last Run Result is the real one. Growth is capped: 1 MB live plus 5 rotated files per target.
- **A failure of the log never stops the board unless the fallback file fails too, and is never silent.** A log
  that cannot be opened, written or rotated, at log-on or later (a file or an ACL where `out/local/logs` should
  be, a full disk, an antivirus or sync handle on a rotated file, a second wrapper on the same log), leaves the
  target running: its lines and the reason go to `%TEMP%\dispatch-board-<target>-log-failure.txt` (capped at
  1 MB) and to stderr when there is one. The log is opened at its first line and retried on every line, and the
  first line it takes again says how many went to the fallback file. Only when that fallback file cannot take the
  start line either, so that no file can hold the reason, does the wrapper not start the target: it exits
  **73**, which Task Scheduler shows as the Last Run Result.
- **Read the logs first when the board looks stale.** `out/local/logs/collector.log` holds one line per
  committed pass and every refusal; `out/local/logs/server.log` holds the `server: serving …` startup line, a
  reason line for every Host/Origin refusal, and one line per HTTP request handled (`log_request`, called for
  every response the handler sends) — address, request line and status code/size — successes and refusals alike,
  not rejections only.
- **The generated task XML never enters the repository.** It carries this machine's interpreter path, checkout
  path and user name, so `install` writes it to a temporary folder and deletes it once `schtasks` has read it.
- **Order does not matter, and the two never fight.** The collector is the database's only writer; the server
  opens it read-only (`query_only=1`) and answers 503 while it does not exist, then serves it without a
  restart. The server's task is delayed 15 seconds after log-on so the first page load usually has data.
- **Git children open no console window.** `local/tabs.py`'s git launches pass `export_board.no_window_flags()`,
  which adds `CREATE_NO_WINDOW` on Windows, so the log-on tasks, which run under the console-less `pythonw.exe`,
  never flash one up. `local/tests/test_no_console_window.py` proves it from a real `pythonw.exe` parent: a
  console-subsystem child (`python.exe`, the same kind of program as `git.exe`) reports no console window with
  the flag and one without it.
- **Nothing here invokes `claude` or reaches an Anthropic host** (NFR-17). `local/tests/test_deploy_inspection.py`
  parses every module under `local/` and checks it: no claude executable in any literal, no bare `claude` token
  in the text, every process launch it can read names `git` or `schtasks`, and every launch it cannot read and
  every import by a built name is on a hand-checked list that counts the sites in each function. It also checks
  that no network-client module is imported, `ssl`, `_socket`, `imaplib`, `poplib`, `socketserver` and
  `multiprocessing.connection` included, whether by name or as a submodule read off an imported package
  (`http.client` off `import http.server`), and that no literal `__import__` or `import_module` names one of
  them, `socket` or `ctypes`. `socket` may take only what the listener needs and `ctypes` only the drive-type
  call, whether imported plainly, under an alias, as a submodule or name by name (attributes read off a name
  imported from them count), and no Anthropic host may appear anywhere — in the exporter modules the collector
  imports as well, a list the check keeps in step with the real imports. It is a tripwire, not a proof: a
  launcher, module or attribute kept under another name (`go = subprocess.run`, `k = ctypes.windll`),
  `getattr`, `sys.modules`, `exec`, a module an exporter re-exports, a reviewed site swapped for a different one
  in the same function, or a program or host built at run time, would pass it.

## Projects

Projects are listed under `projects` in `board.config.json`, in picker order. Each entry has:

- `id` (letters, digits, `-` and `_`; used in store ids and file names), `name`, `repoPath`, `branch`.
- `sessions`: the Claude Code session ids that build it. Build sessions run from `C:\Users\jdk`, not the repo folder, so they are listed rather than found.
- `statusDoc`: `meta/status` for platform-catalogue; `status/<id>` otherwise (the default).
- `docs`: paths relative to `repoPath`: `spec`, `prd`, `brief`, `adrDir`, `board`, optionally `design` (a design spec whose revision the Spec tab shows) and `reviews` (`[{ "gate", "path" }]`; `{round}` in the path stands for rounds 1 to 3). `board` is recorded but not read yet: the Backlog tab's note about the BOARD comes from the data file.

A config without `projects` (the older `build.*` / `usage.sessions` shape) is still read, as one project whose `statusDoc` is `meta/status`.

**Hand-kept build state lives in `projects/<projectId>.json`** in this repo (not in the build repo, not in `out/`); platform-catalogue's is `projects/platform-catalogue.json`. It records what the build repo does not, and the build session edits it by hand as work items move:

- `buildState`: per PBI, `{ "state", "review", "open", "commit" }`. `state` is `done`, `conditions`, `partial` or `todo`; a PBI that is not listed is `todo`.
- `notWorkedOut`: `[{ "item", "row", "adr" }]`, the brief's "Things I haven't worked out" mapped to spec ledger rows (`adr` may be `null`).
- `boardNote`: the text the Backlog tab shows about the BOARD.

A project without a data file has no build state. A data file that is not valid JSON stops `export_board.py`, so `refresh.py` pushes nothing until it is fixed. `tests/test_export_board.py` checks every data file's shape.

## Design rules (the owner's stated preferences)

- **Professional dashboard, not an editorial page.** No poster hero, no oversized display type. Overview first: summary tiles, backlog cells, pipeline, the "Waiting on you" panel, needs-attention list, usage, recent activity.
- The owner **liked the status-tile language**: bordered tile, 3px coloured top bar, small label, figure, one-line context. Reuse it everywhere (`.tile`, `.cell`).
- The owner **disliked wide monospace text**. One sans (Schibsted Grotesk) for everything, tabular figures; IBM Plex Mono only for ids and commit hashes.
- Dark-first tokens on bare `:root`, light override under `prefers-color-scheme: light` and `[data-theme="light"]`. Colours only through tokens. One bold colour, `--human` violet, reserved for things awaiting a human; semantic colours `--live` / `--go` / `--changes` / `--nogo` are separate.
- Motion only when it is true: pipeline arrows animate only while an agent is running; `prefers-reduced-motion` respected.
- All data rendered through `esc()`; repo text may carry `code` spans and bold via `md()` — nothing else.

## Open items

- **Two token figures disagree.** Dispatch shows agents' self-reported tokens (~2.4M); the usage tab shows transcript-derived effective usage (agents ~8.3M). Switch Dispatch to transcript figures so there is one number.
- **Retired tabs.** Since project-first navigation, the store's `tabs/spec`, `tabs/assumptions`, `tabs/decisions`, `tabs/backlog` and `tabs/git` are leftovers too. Nothing reads or deletes them; remove them by hand with `write_db` delete ops once the owner agrees. Moot since the artifact was frozen on 2026-09-19 (PBI-037): its store is no longer written, so they stay.
- **Leftover documents.** Besides the retired `tabs/*`, the store holds a stale `tabs/usage`. `refresh.py` never deletes it, because it deletes only documents recorded in `out/.pushed.json`. Remove it by hand with a `write_db` delete once the owner agrees. Moot since the artifact was frozen on 2026-09-19 (PBI-037): its store is no longer written, so they stay. The hand-written `runs/r01`…`r36` were deleted at the switch to generated rows on 2026-09-10.
- Inferred links are heuristics: `feeds` needs a PBI id or the word review/notes/LOWs/fix in the task description; runs without one (e.g. "Align types.ts…") get no link.
- The usage tab is not a plan meter: transcripts record only the moments a limit refused a request.
- **The "Waiting on you" panel is detectors, not a guarantee** (PBI-009). A closing prose question is caught only when it looks like one — about 4 of every 7 real solicitations on measured data — so an empty panel means nothing was detected, never that nothing is waiting. On the same data the question half comes entirely from the prose detector: every structured `AskUserQuestion` in the corpus was answered, so the exact detector caught nothing there. Only main transcripts are read; a question a subagent asks its orchestrator is never listed. Refusals rest on the undocumented `toolDenialKind` field, observed only on CLI 2.1.205–2.1.260 — an older transcript can't distinguish "no refusal happened" from "the field didn't exist yet".
- **What clears or bounds a waiting item** (PBI-009). Any later message `is_owner_message()` accepts clears it, so a refusal the owner typed past unresolved just disappears; a compaction summary and the literal interrupt marker text are excluded from that predicate, but the marker match is a fixed string and would silently stop matching if Claude Code changed its exact wording. An item older than 48 hours is dropped and the panel shows at most 20 across all sessions; whenever either bound hides something the panel says so, but not what it hid. Idleness (D2) is computed on the page, not the exporter — a deliberate deviation from FR-108's wording, so the stored document never changes with the clock alone.
- The Browser pane cannot open files outside an open project folder; preview `site/index.html` from this project instead.

## Merge authority (the owner's standing authorisation, 2026-09-12)

The owner authorised the building session to merge its own work items' pull requests, verbatim:

> "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time."

- It applies on a code review of GO, or GO-WITH-CONDITIONS with every condition applied. The merge is squash, and the close-out follows in the same pass.
- It does not apply to a NO-GO, an unresolved condition, or any circuit-breaker: a scope breach, a rail refusal, a blocked-area stop, a high-impact assumption. Those still stop and wait for the owner.
- Each work item carries `merge_allowed_by_agent: true` with this authorisation quoted as its authority, so the metadata matches what is done.
- Merge stays a human-authorised decision that the agent executes; this is the human half, and it is reversible at any time.

## The build it tracks (paused)

platform-catalogue, branch `build/logic-core`, not merged to `master`, no remote. Its work-item state is recorded in `projects/platform-catalogue.json`, which is the source of truth (the Backlog tab shows it). What the plan gate still needs from the owner is in the spec (the Assumptions tab). This file does not restate either, so it cannot fall out of step with them. Nothing is pushed or deployed without the owner saying so.
