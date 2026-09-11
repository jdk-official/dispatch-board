---
title: PBI-017 — Agent catalogue tab (per-PBI spec)
status: draft
revision: 2
parent_spec: docs/backlog/specs/dispatch-board.md (revision 5, approved)
pbi: docs/backlog/pbi/PBI-017.md
---

# PBI-017 — Agent catalogue tab: per-PBI spec

Refined from the approved parent spec (G-7; rows 19–22; AC-C1 to AC-C7), as its
`requires_spec: true` requires (SPEC §Gates, spec gate). It must pass an independent review
before any code is written. It adds the owner's changes of 2026-09-11, "Include skills too" and
"Show what each agent is for".

- **Revision 2** applies spec-gate review round 1 (`docs/backlog/reviews/PBI-017/spec-review-r1.md`):
  - agent last use now has a source;
  - slash commands are counted only from real typed-command records;
  - plugin purposes are capped to one line;
  - an empty catalogue, or a malformed catalogue file, no longer blanks the tab or stops the refresh;
  - defaults, bare skill names, the "N of M" denominator, test fixtures and documentation are all stated.

---

## 1. What the owner gets

A new **Agent catalogue** tab. It lists every agent and every skill in the agent-catalog
marketplace, grouped by the plugin it comes from. Each plugin group carries a one-line purpose,
with its full text on demand, and each entry shows:
- what it is for (its full description);
- whether its plugin is installed;
- how often it was used, when it was last used, and which projects used it;
- "never used" if it has not been used.

The counts follow the picker (a project's sessions, or the chosen "Other sessions" session) and
show the all-sessions figure beside them. Agents and skills seen in use that are not in the
catalogue get their own panel.

## 2. Sources (read only, never written)

| What | Where | Evidence |
|---|---|---|
| Agents | `<marketplacePath>/plugins/<plugin>/agents/<name>.md`; frontmatter `name`, `description` | 30 files in 6 plugins; every `name` matches its file; descriptions single-line and double-quoted (spec review I1) |
| Skills | `<marketplacePath>/plugins/<plugin>/skills/<name>/SKILL.md`; frontmatter `name`, `description` | 21 in 4 plugins; descriptions single-line and unquoted (I1) |
| Purpose of a plugin | `<marketplacePath>/plugins/<plugin>/.claude-plugin/plugin.json` `description` | Present for all 10 plugins; first sentences run from 1 to 1459 characters (spec review M1), so it is capped (§4) |
| Installed or not | `<installedPath>`: `plugins` object keyed `<plugin>@agent-catalog`, each holding a list of install records | Verified (I3); `workflow-agents@agent-catalog` absent |
| Agent use | each agent's `subagents/agent-<id>.meta.json` `agentType`; namespaced values match entry ids exactly (`engineering-agents:code-writer`, …); others are built-in (`Plan`, `general-purpose`) | Verified (I2); `exporters/export_sessions.py:442` reads it, but the run-doc keys at `:708–713` omit it |
| Skill use | main transcript only: `Skill` tool calls (`input.skill`), and genuine typed-command records (§3) | Session `9562c312`: `backlog-delivery:pbi-plan` ×2 and `backlog-delivery:pbi-review` ×2 as `Skill` calls |

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

  - Plugins with neither agents nor skills are left out of `plugins`.
  - Entries are sorted by plugin, then kind (agents first), then name.
  - Usage is not stored here, so the document changes only when the catalogue changes.
- **`runs/<id>`** gains two keys on subagent runs:
  - **`agentType`**, the raw meta value, omitted when the meta is missing or empty;
  - **`start`**, the ISO launch time, already held in the row as `r['start']` at `export_sessions.py:451` and `:688`.

  `runs.manual` rows carry neither.
- **`sessions/<id>`** gains **`skillUses`**, `{ "<skill id>": { "count": int, "last": ISO } }`, from that session's main transcript only. A use is counted in exactly two cases:
  1. **`Skill` tool calls.** An assistant `tool_use` block with `name == "Skill"`. The id is its `input.skill`. The call's `args` are never read or stored.
  2. **Typed commands.** A record where all of these hold:
     - `type == "user"`;
     - `isMeta` is not true;
     - `message.content` is a string;
     - that string starts with `<command-message>` or `<command-name>`;
     - the name inside `<command-name>` contains `:` (a plugin command, such as `/backlog-delivery:pbi-plan`).

     The id is the name without its leading `/`. `tool_use`, `tool_result`, attachment and system content is never scanned, which excludes tag text that merely appears inside tool output (spec review H2).
- **Skill ids are validated.** A skill id must match `^[A-Za-z0-9_.:-]{1,100}$`. Anything else is dropped with a warning.
- **Matching uses to catalogue entries**, in the page:
  - a namespaced id counts toward the entry with that id;
  - a bare `Skill` id, such as `pbi-review`, counts toward the one catalogue skill with that `name`, if exactly one exists;
  - any other id goes to "Outside the catalogue". That includes bare built-in skills such as `loop`, and plugin commands that are not skills.
- **Known limitation (§7):** bare slash commands the owner types, such as `/loop`, are not counted.
- **Coverage is computed in the page** from `runs` (`agentType`, `start`) and `sessions` (`skillUses`):
  - an agent's last use is the latest `start` among its runs;
  - a skill's is the latest `last`.

## 4. Exporter, refresh and failure handling

- **`exporters/export_catalogue.py`:**
  - it runs as `python exporters/export_catalogue.py [out_dir]`, the same contract as the other exporters, with a testable `main(config=None, out_dir=None)`;
  - it writes `out/catalogue/index.json` atomically, with the existing `write_json` pattern.
- **Frontmatter.** Single-line `key: value` pairs between the first two `---` lines. Only a matching pair of surrounding quotes is stripped. A block value (`>` or `|`) is ignored with a warning, rather than published as the description.
- **Purpose line.**
  - Take the manifest `description` up to the first `.`, `!` or `?` that is followed by whitespace or the end of the text, and not part of `e.g.` or `i.e.`.
  - Cap it at 120 characters, cutting on a word boundary and adding `…`.
  - `purposeFull` keeps the whole text.
  - With no usable manifest, the purpose is the plugin name.
- **Only a config type error exits non-zero** (exit 2). Every other problem is warned on stderr and falls back, with exit 0:
  - an unreadable, non-UTF-8 or malformed agent or skill file: that entry is skipped;
  - a malformed or non-UTF-8 `plugin.json`: the purpose falls back to the plugin name;
  - an `installed_plugins.json` that is missing, unreadable or the wrong shape (`plugins` not an object, or entries not lists): every entry is marked `installed: false`;
  - a missing marketplace folder, a missing `plugins/` folder, or zero agents and zero skills found: the previous `out/catalogue/index.json` is kept untouched. This covers a half-finished `git pull`, a failed clone and a repointed path (spec review M3).
- **`exporters/refresh.py`:**
  - `export()` runs `export_catalogue.py` (line 78);
  - `catalogue` is added to `MANAGED` (line 34);
  - without `--allow-mass-delete`, the planner refuses any plan that deletes `catalogue/index`, like the project-document guard;
  - its docstring is updated (lines 9–10: the exporters and managed collections);
  - a test covers `export()` running all three exporters.
- **`exporters/export_sessions.py`:**
  - it emits `agentType` and `start` on subagent run docs;
  - it collects `skillUses` while parsing the main transcript;
  - it bumps `PARSER_VERSION`, so cached sessions are re-read once.
- **One-time cost (spec review L7).** The first push after this change is about 94 writes in 2 batches: every run and session, plus `catalogue/index` and both projects' status documents. Every linked run and session changes, so each project's "Updated" time moves once. The writes are sets, not deletes, so no guard trips.

## 5. Page

- **Tab.** A new tab button, `data-tab="catalogue"`, "Agent catalogue", placed straight after Dispatch and before Claude usage, inside the session group (`grp`) that begins at Dispatch (`site/index.html:216`).
  - It is not in `PROJECT_TABS` (`:805`), so it shows in every view.
  - The keyboard arrow and Home/End keys cover it through `tabs`.
  - It subscribes to `db.doc('catalogue/index')` next to the existing subscriptions (`:895`).
- **Summary tiles**, in the existing status-tile language:
  - **"Agents used":** N of M for the current view, where M counts every agent entry, installed or not, plus a line "K installed". The all-sessions N appears beside it.
  - **"Skills used":** the same, for skills.
  - **"Outside the catalogue":** the count of ids seen in use but not in `entries`.
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
  - last use;
  - the projects whose sessions used it;
  - all-sessions uses;
  - a neutral "never used" tag when there are none.

  Within a group, rows sort by uses in the view, then by name.
- **Outside the catalogue.** A final panel lists the ids seen in use but not in `entries`, with the same use columns. Examples: `Plan` and `general-purpose` among agents, `artifact-design` and `loop` among skills.
- **Empty states.**
  - With no `catalogue/index`, the panel shows the page's existing `.empty` block: "The agent catalogue has not been exported yet."
  - With no uses in the view, the counts read 0 and every entry reads "never used".
- **Design rules.** Colours only from tokens; `--human` never used here; all store text passed through `esc()`; descriptions never through `md()`; no motion.

## 6. Acceptance criteria (refined from the parent's AC-C1–AC-C7)

- **AC-C1** `export_catalogue.py`, run against a synthetic marketplace built in a temporary folder, writes `catalogue/index` in the §3 shape:
  - every agent and skill file becomes one entry with kind, plugin, name, full description and installed flag;
  - `purpose` follows the §4 rule, tested with a manifest that has no full stop, one containing "e.g.", and one over 120 characters;
  - `purposeFull` is the whole text;
  - the two paths come from the test's own `catalogue` config.
- **AC-C2** The tab groups entries by plugin, showing the purpose line with `purposeFull` expandable, and each entry's full description expandable.
- **AC-C3** Usage is taken from the transcripts:
  - `runs/<id>` carries `agentType` and `start` on subagent runs, and neither on manual rows or where the meta is missing;
  - `sessions/<id>.skillUses` counts `Skill` tool calls and genuine typed plugin commands only;
  - synthetic tests show that none of these are counted: command text inside a `tool_result`, a `tool_use` or an attachment; an `isMeta` duplicate; a bare slash command; an invalid id;
  - a bare `Skill` id counts toward a catalogue skill only when exactly one skill has that name;
  - everything else lands only in "Outside the catalogue".
- **AC-C4** Each entry shows its uses, last use (agents: the latest run `start`; skills: `last`) and projects in the current view, plus its all-sessions uses, or "never used". The coverage caption is shown.
- **AC-C5** The tab sits after Dispatch, in the session group, in every view. The "Agents used" and "Skills used" tiles give N of M (M = all entries) for the current view, with "K installed" and the all-sessions figure beside.
- **AC-C6** The refresh script and the exporter handle failures as specified:
  - `refresh.py` manages `catalogue`, runs the new exporter, and refuses a plan that deletes `catalogue/index` without `--allow-mass-delete`;
  - a missing marketplace, a missing `plugins/` folder, or zero entries keeps the last export, with a warning and exit 0;
  - a malformed manifest falls back to the plugin name, with exit 0;
  - a malformed or missing installed-plugins file marks entries not installed, with exit 0;
  - only a config type error exits 2.
- **AC-C7** Tests:
  - `tests/test_export_catalogue.py` for the export and every failure path above;
  - additions to `tests/test_export_sessions.py` for `agentType`, `start` and `skillUses`, including the exclusions;
  - additions to `tests/test_refresh.py` for the managed collection, the guard and `export()` running three exporters;
  - additions to `tests/page.test.mjs` for the tab in a project view and in "Other sessions": tiles, grouping, bare-name matching, "never used", the outside panel and the empty state.

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
- **Forked sessions** that repeat an earlier session's history (for example `ccb0c1af` containing `55051457`'s lines) count those uses twice in all-sessions figures, as usage already does (spec review I5).
