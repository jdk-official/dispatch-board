---
title: PBI-017 — Agent catalogue tab (per-PBI spec)
status: approved
revision: 3
parent_spec: docs/backlog/specs/dispatch-board.md (revision 5, approved)
pbi: docs/backlog/pbi/PBI-017-agent-catalogue.md
---

# PBI-017 — Agent catalogue tab: per-PBI spec

Refined from the approved parent spec (G-7; rows 19–22; AC-C1 to AC-C7), as its
`requires_spec: true` requires (SPEC §Gates, spec gate). It adds the owner's changes of
2026-09-11, "Include skills too" and "Show what each agent is for".

- **Spec gate: passed 2026-09-11.**
  - Round 1 on revision 1: CHANGES-REQUIRED (`docs/backlog/reviews/PBI-017/spec-review-r1.md`).
  - Round 2 on revision 2: APPROVE-WITH-NOTES (`docs/backlog/reviews/PBI-017/spec-review-r2.md`).
  - Every round-2 note is applied in this revision 3, as the reviewer directed, with no third round.

---

## 1. What the owner gets

A new **Agent catalogue** tab. It lists every agent and every skill in the agent-catalog
marketplace, grouped by the plugin it comes from. Each plugin group carries a one-line purpose,
with its full text on demand, and each entry shows:
- what it is for (its full description);
- whether its plugin is installed;
- how often it was used and when it was last used, in the current view;
- which projects have ever used it;
- "never used" if it has not been used.

The current view is the picker's project, narrowed by its session filter, or the chosen "Other
sessions" session. Each count also shows the all-sessions figure beside it. Agents and skills
seen in use that are not in the catalogue get their own panel.

## 2. Sources (read only, never written)

| What | Where | Evidence |
|---|---|---|
| Agents | `<marketplacePath>/plugins/<plugin>/agents/<name>.md`; frontmatter `name`, `description` | 30 files in 6 plugins; every `name` matches its file; descriptions single-line and double-quoted; all files CRLF (spec review r2 M2) |
| Skills | `<marketplacePath>/plugins/<plugin>/skills/<name>/SKILL.md`; frontmatter `name`, `description` | 21 in 4 plugins; descriptions single-line and unquoted; CRLF |
| Purpose of a plugin | `<marketplacePath>/plugins/<plugin>/.claude-plugin/plugin.json` `description` | Present for all 10 plugins. The §4 rule, re-tested on the real manifests, keeps 4 whole (62–113 characters) and cuts 4 to 120 characters |
| Installed or not | `<installedPath>`: `plugins` object keyed `<plugin>@agent-catalog`, each holding a list of install records | Verified; `workflow-agents@agent-catalog` absent |
| Agent use | each agent's `subagents/agent-<id>.meta.json` `agentType`; namespaced values match entry ids exactly; others are built-in (`Plan`, `general-purpose`) | `exporters/export_sessions.py:442` reads it; the run-doc keys at `:708–713` omit it |
| Skill use | main transcript only: `Skill` tool calls (`input.skill`), and genuine typed-command records (§3) | Session `9562c312`: one `Skill` call each for `backlog-delivery:pbi-plan` and `backlog-delivery:pbi-review`. The only typed plugin command in the real data is `/anthropic-skills:i-have-adhd`, which lands in "Outside the catalogue" |

**Config.** `board.config.json` gains a `catalogue` block with two string keys:
- `marketplacePath`, defaulting to `~/.claude/plugins/marketplaces/agent-catalog`;
- `installedPath`, defaulting to `~/.claude/plugins/installed_plugins.json`.

Defaults, and configured values that start with `~`, go through `os.path.expanduser`. `exporters/board_config.py` raises `ValueError` on a non-string value, and `export_catalogue.py` maps that to exit 2, like `export_sessions.py:622–626`. Every test passes a config with its own `catalogue` block pointing at a temporary folder, so no test ever reads the real `~/.claude`.

## 3. Store shapes and what is counted

- **`catalogue/index`** (one document, new collection `catalogue`), written by the new `exporters/export_catalogue.py`:

  ```
  { "generatedAt": ISO,
    "source": { "marketplacePath": str, "installedPath": str },
    "plugins": [ { "plugin": str, "purpose": str, "purposeFull": str, "installed": bool,
                   "agents": int, "skills": int } ],
    "entries": [ { "id": "<plugin>:<name>", "kind": "agent"|"skill", "plugin": str, "name": str,
                   "description": str, "installed": bool } ] }
  ```

  - **Name.** An entry's `name` is its frontmatter `name`, falling back to the file name (agents) or the folder name (skills).
  - **Id check.** An entry whose `<plugin>:<name>` does not match `^[A-Za-z0-9_.:-]{1,100}$` is skipped, with a warning.
  - **Empty plugins.** Plugins with neither agents nor skills are left out of `plugins`.
  - **Order.** Entries are sorted by plugin, then kind (agents first), then name.
  - **No usage here.** Usage is not stored in this document, so it changes only when the catalogue changes.
- **`runs/<id>`** gains two keys on subagent runs:
  - **`agentType`**, the raw meta value, omitted when the meta is missing or empty;
  - **`start`**, the ISO launch time already in the row (`export_sessions.py:451`, `:688`), omitted when null.

  `runs.manual` rows carry neither.
- **`sessions/<id>`** always carries **`skillUses`**, `{}` when there are none: `{ "<skill id>": { "count": int, "last": ISO } }`, from that session's main transcript only.
  - A use with no readable timestamp is counted, but leaves `last` unchanged; `last` is omitted if no use has a time.
  - The page treats a missing `skillUses` as `{}`, for sessions cached under the old parser.
- **What counts as a skill use.** Exactly two cases:
  1. **`Skill` tool calls.** An assistant `tool_use` block with `name == "Skill"`. The id is its `input.skill`. The call's `args` are never read or stored.
  2. **Typed commands.** A record where all of these hold:
     - `type == "user"`;
     - `isMeta` is not true;
     - `message.content` is a string;
     - that string starts with `<command-message>` or `<command-name>`;
     - the name inside `<command-name>` contains `:`.

     The id is the name without its leading `/`. `tool_use`, `tool_result`, attachment and system content is never scanned.
- **Skill ids are validated.** A skill id must match `^[A-Za-z0-9_.:-]{1,100}$`. Anything else is dropped with a warning.
- **Matching uses to catalogue entries**, in the page:
  - a namespaced id counts toward the entry with that id;
  - a bare `Skill` id counts toward the one catalogue skill with that `name`, if exactly one exists;
  - any other id goes to "Outside the catalogue".
- **Known limitation:** bare slash commands the owner types, such as `/loop`, are not counted (§7).
- **The current view's scope:**
  - **Runs:** the page's existing run scope (`site/index.html:858`).
  - **Sessions:** `p ? sessions.filter(s => s.project === p.id && (!sel || s.id === sel)) : [cur()]`. This matches the run scope, with the session filter applied the same way.
- **All-sessions figures** use every exported run and session.
- **Last use:** for an agent, the latest `start` among its runs in scope; for a skill, the latest `last` in scope.
- **Projects** are computed over all exported sessions, not the view:
  - they are the distinct project names from run `project` (agents) and session `project` (skills), in `projects` order;
  - "Other sessions" is added when an unlinked session used the entry.

## 4. Exporter, refresh and failure handling

- **`exporters/export_catalogue.py`:**
  - it runs as `python exporters/export_catalogue.py [out_dir]`, the same contract as the other exporters, with a testable `main(config=None, out_dir=None)`;
  - it writes `out/catalogue/index.json` atomically, with the existing `write_json` pattern;
  - its module docstring states what it reads and writes.
- **Frontmatter.**
  - Read files in text mode with `encoding='utf-8-sig'`, so universal newlines apply and a BOM is tolerated.
  - Frontmatter is the single-line `key: value` pairs between the first two lines that are `---` after `strip()`.
  - Strip each key and value, then remove only a matching pair of surrounding quotes.
  - A block value (`>` or `|`) is ignored with a warning, rather than published.
- **Purpose line:**
  - A missing, empty or non-string `description` counts as "no usable manifest", and the purpose is then the plugin name.
  - Otherwise, take the text up to and including the first `.`, `!` or `?` that is followed by whitespace or the end of the text. An `e.g.` or `i.e.`, matched case-insensitively, is not a sentence end.
  - If that is longer than 120 characters, cut it at the last word boundary that leaves room, remove trailing spaces and commas, and append `…`. The result, including `…`, is at most 120 characters.
  - `purposeFull` keeps the whole description.
- **Only a config type error exits non-zero** (exit 2). Every other problem is warned on stderr and falls back, with exit 0:
  - an unreadable, non-UTF-8 or malformed agent or skill file: that entry is skipped;
  - a malformed or non-UTF-8 `plugin.json`: the purpose falls back to the plugin name;
  - an `installed_plugins.json` that is missing, unreadable or the wrong shape: every entry is marked `installed: false`;
  - a missing marketplace folder, a missing `plugins/` folder, or zero agents and zero skills found: the previous `out/catalogue/index.json` is kept untouched.
- **`exporters/refresh.py`:**
  - the exporters it runs become a module-level `EXPORTERS` tuple, `('export_board.py', 'export_sessions.py', 'export_catalogue.py')`, used by `export()`;
  - `catalogue` is added to `MANAGED` (line 34);
  - without `--allow-mass-delete`, the planner refuses any plan that deletes `catalogue/index`;
  - the module docstring is updated: lines 9–10 (exporters and managed collections) and lines 21–24 (the guard paragraph, adding `catalogue/index`);
  - the `export()` test patches `refresh.subprocess.run` and asserts that the three scripts are called in that order. It never runs the real exporters.
- **`exporters/export_sessions.py`:**
  - it emits `agentType` and `start` on subagent run docs;
  - it always emits `skillUses` on session docs;
  - it bumps `PARSER_VERSION`, so cached sessions are re-read once;
  - its module docstring (lines 1–32) lists the new fields.
- **One-time cost.** The first push after this change is about 94 writes in 2 batches: every run and session, plus `catalogue/index` and both projects' status documents. Each project's "Updated" time moves once. The writes are sets, not deletes, so no guard trips.

## 5. Page

- **Tab.** A new tab button, `data-tab="catalogue"`, "Agent catalogue", placed straight after Dispatch and before Claude usage, inside the session group (`grp`) that begins at Dispatch (`site/index.html:216`).
  - It is not in `PROJECT_TABS` (`:805`), so it shows in every view.
  - The keyboard arrow and Home/End keys cover it through `tabs`.
  - It subscribes to `db.doc('catalogue/index')` next to the existing subscriptions (`:895`).
- **Summary tiles**, in the existing status-tile language. Each shows the current view's figure with the all-sessions figure beside it:
  - **"Agents used":** N of M, where M counts every agent entry, installed or not, plus a line "K installed";
  - **"Skills used":** the same, for skills;
  - **"Outside the catalogue":** the number of distinct ids seen in use but not in `entries`.
- **Coverage caption.** Beneath the tiles, in the existing `src()` style (`:247`): "Usage covers the sessions the board exports: the last 7 days plus every linked session."
- **Groups.**
  - One panel per plugin, in `plugins` order.
  - The header shows the plugin name and its one-line purpose, with `purposeFull` in an expandable `<details>`.
  - A muted "not installed" tag appears when `installed` is false.
- **Rows.** One per entry:
  - a kind tag (agent or skill);
  - the name, with the id in the mono face (ids only);
  - the description, clamped to two lines, with an expandable `<details>` for the rest;
  - uses in the view;
  - last use in the view;
  - projects (all sessions, §3);
  - all-sessions uses;
  - a neutral "never used" tag when there are no uses in the view.

  Within a group, rows sort by uses in the view, then by name.
- **Outside the catalogue.** A final panel lists the ids seen in use but not in `entries`, with the same columns.
- **Empty states.**
  - With no `catalogue/index`, the panel shows the page's existing `.empty` block: "The agent catalogue has not been exported yet."
  - With no uses in the view, the view counts read 0 and every entry reads "never used".
- **Design rules.** Colours only from tokens; `--human` never used here; all store text passed through `esc()`; descriptions never through `md()`; no motion.

## 6. Acceptance criteria (refined from the parent's AC-C1–AC-C7)

- **AC-C1** `export_catalogue.py`, run against a synthetic marketplace built in a temporary folder, writes `catalogue/index` in the §3 shape:
  - every agent and skill file becomes one entry with kind, plugin, name, full description and installed flag;
  - the name fallbacks and the id check behave as in §3;
  - `purpose` follows the §4 rule exactly, tested with: a manifest with no full stop; one containing "E.g."; one over 120 characters, whose expected result ends in `…` and is at most 120 characters; and an empty `description`;
  - one agent file and one manifest are written with CRLF line endings and a UTF-8 BOM, and parse identically;
  - the two paths come from the test's own `catalogue` config.
- **AC-C2** The tab groups entries by plugin, showing the purpose line with `purposeFull` expandable, and each entry's full description expandable.
- **AC-C3** Usage is taken from the transcripts:
  - `runs/<id>` carries `agentType` and `start` on subagent runs, and neither on manual rows, where the meta is missing, or where `start` is null;
  - every session document carries `skillUses`, `{}` when unused;
  - `skillUses` counts `Skill` tool calls and genuine typed plugin commands only;
  - synthetic tests show that none of these are counted: command text inside a `tool_result`, a `tool_use` or an attachment; an `isMeta` duplicate; a bare slash command; an invalid id;
  - a use with no timestamp is counted, and leaves `last` unchanged;
  - a bare `Skill` id counts toward a catalogue skill only when exactly one skill has that name;
  - everything else lands only in "Outside the catalogue".
- **AC-C4** Each entry shows:
  - its uses and last use in the current view (agents: the latest run `start`; skills: `last`);
  - the projects that have ever used it, computed over all exported sessions, including "Other sessions" for unlinked ones;
  - its all-sessions uses;
  - "never used" when it has no uses in the view.

  The coverage caption is shown.
- **AC-C5** The tab sits after Dispatch, in the session group, in every view. The "Agents used", "Skills used" and "Outside the catalogue" tiles each give the current view's figure, with the all-sessions figure beside. The first two give N of M (M = all entries) and "K installed". The session filter narrows both runs and sessions.
- **AC-C6** The refresh script and the exporter handle failures as specified:
  - `refresh.py` manages `catalogue`, runs the three `EXPORTERS` in order, and refuses a plan that deletes `catalogue/index` without `--allow-mass-delete`;
  - a missing marketplace, a missing `plugins/` folder, or zero entries keeps the last export, with a warning and exit 0;
  - a malformed manifest falls back to the plugin name, with exit 0;
  - a malformed or missing installed-plugins file marks entries not installed, with exit 0;
  - only a config type error exits 2.
- **AC-C7** Tests:
  - `tests/test_export_catalogue.py` for the export and every failure path above, including the CRLF-and-BOM fixture;
  - additions to `tests/test_export_sessions.py` for `agentType`, `start` and `skillUses`, including the exclusions and the missing-timestamp case;
  - additions to `tests/test_refresh.py` for the managed collection, the guard, and `export()` calling the three scripts in order with `subprocess.run` patched;
  - additions to `tests/page.test.mjs`, in a project view and in "Other sessions", covering:
    - the tiles and their all-sessions figures;
    - grouping, with `purposeFull` and the descriptions expandable;
    - last use from the latest run `start`;
    - the projects column, including "Other sessions";
    - session-filter narrowing in a project view;
    - bare-name matching;
    - "never used" and the outside panel;
    - the coverage caption and the empty state;
    - `esc()` of a hostile description (compare the existing `Legacy <img src=x>` title check).

  All fixtures are built in temporary folders inside the tests (nothing under `tests/fixtures/`). `python -m unittest discover -s tests` and `node tests/page.test.mjs` are green.
- **Close-out.** `CLAUDE.md` documents all of the following:
  - the `catalogue/index` document;
  - `agentType` and `start` on runs, and `skillUses` on sessions;
  - the `catalogue` config block;
  - `catalogue` in the list of managed collections and in the mass-delete guard paragraph;
  - the catalogue exporter's failure behaviour in the Refresh-procedure list;
  - a privacy line: skill ids from transcripts are published unredacted, like titles (acceptable under D-12), and `Skill` arguments are never stored;
  - the bare-slash-command limitation.

  `review-agents:code-reviewer` returns GO.

## 7. Out of scope and known limitations

- Other marketplaces.
- Skill use inside subagent transcripts (the main transcript only, per the parent's AC-C3).
- Plugin versions, and drift between the marketplace clone and the installed cache.
- The local app's catalogue record (PBI-003 and PBI-019).
- **Bare slash commands** the owner types (for example `/loop`) are not counted. A bare `Skill` call is.
- **Forked sessions** that repeat an earlier session's history (for example `ccb0c1af` containing `55051457`'s lines) count those uses twice in all-sessions figures, as usage already does.
- **`skillUses` keys** contain `:` and `.`. They are safe under `set`, which the refresh uses for sessions; a future field-path `update` would need an array shape instead.
