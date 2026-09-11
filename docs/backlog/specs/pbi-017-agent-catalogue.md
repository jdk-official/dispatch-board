---
title: PBI-017 — Agent catalogue tab (per-PBI spec)
status: draft
revision: 1
parent_spec: docs/backlog/specs/dispatch-board.md (revision 5, approved)
pbi: docs/backlog/pbi/PBI-017.md
---

# PBI-017 — Agent catalogue tab: per-PBI spec

Refined from the approved parent spec (G-7; rows 19–22; AC-C1 to AC-C7), as its
`requires_spec: true` requires (SPEC §Gates, spec gate). It must pass an independent review
before any code is written. It adds the owner's changes of 2026-09-11, "Include skills too" and
"Show what each agent is for", and states the exact store shapes, file locations and page
layout the worker builds against.

---

## 1. What the owner gets

A new **Agent catalogue** tab. It lists every agent and every skill in the agent-catalog
marketplace, grouped by the plugin it comes from. Each plugin group carries a one-line purpose,
and each entry shows:
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
| Agents | `<marketplacePath>/plugins/<plugin>/agents/<name>.md`; frontmatter `name`, `description` | 30 files in 6 plugins, each `name` matching its file name (plan-gate review round 3) |
| Skills | `<marketplacePath>/plugins/<plugin>/skills/<name>/SKILL.md`; frontmatter `name`, `description` | 21 in 4 plugins, for example `backlog-delivery/skills/bd-adopt/SKILL.md` |
| Purpose of a plugin | `<marketplacePath>/plugins/<plugin>/.claude-plugin/plugin.json` `description`, first sentence | Present for all 10 plugins, for example review-agents: "Read-only, evidence-first, severity-tagged critique agents …" |
| Installed or not | `<installedPath>` → `plugins` object keyed `<plugin>@agent-catalog` | `installed_plugins.json` (`version`, `plugins`); `workflow-agents@agent-catalog` absent |
| Agent use | each agent's `subagents/agent-<id>.meta.json` `agentType`, for example `review-agents:code-reviewer`, `Plan`, `general-purpose` | `exporters/export_sessions.py` reads it (~line 442) but does not emit it (run-doc keys, line 708) |
| Skill use | the main transcript: `Skill` tool calls, whose `input.skill` is `<plugin>:<name>` or a bare name, and user messages holding `<command-name>/<plugin>:<name></command-name>` | Session `9562c312`: `backlog-delivery:pbi-plan` ×2, `backlog-delivery:pbi-review` ×2; slash commands such as `/model` and `/loop` also appear |

**Config.** `board.config.json` gains a `catalogue` block:
`{"marketplacePath": "C:/Users/jdk/.claude/plugins/marketplaces/agent-catalog", "installedPath": "C:/Users/jdk/.claude/plugins/installed_plugins.json"}`.
- `exporters/board_config.py` reads it, with those values as defaults, and exits 2 on a non-string value, like the other type checks.
- Tests always pass their own paths.

## 3. Store shapes

- **`catalogue/index`** (one document, new collection `catalogue`), written by the new `exporters/export_catalogue.py`:

  ```
  { "generatedAt": ISO,
    "source": { "marketplacePath": str, "installedPath": str },
    "plugins": [ { "plugin": str, "purpose": str, "installed": bool, "agents": int, "skills": int } ],
    "entries": [ { "id": "<plugin>:<name>", "kind": "agent"|"skill", "plugin": str, "name": str,
                   "description": str, "installed": bool } ] }
  ```

  - Plugins with neither agents nor skills (the two grounding plugins) are left out of `plugins`.
  - Entries are sorted by plugin, then kind (agents first), then name.
  - Usage is **not** stored here. The document changes only when the catalogue changes, so most refreshes push nothing for it.
- **`runs/<id>`** gains **`agentType`** (the raw meta value) on every subagent run. `runs.manual` rows carry none.
- **`sessions/<id>`** gains **`skillUses`**: `{ "<skill id>": { "count": int, "last": ISO } }`, taken from that session's main transcript.
  - The skill id is `input.skill` as written.
  - A slash command counts only when its name contains `:` (a plugin skill such as `/backlog-delivery:pbi-plan`), with the leading `/` dropped. Built-in commands such as `/model`, `/compact` and `/loop` are not counted.
- **Coverage is computed in the page** from `runs` (`agentType`) and `sessions` (`skillUses`), which it already subscribes to. So the figures follow the picker and session filter with no extra store documents.

## 4. Exporter, refresh and guards

- **`exporters/export_catalogue.py`:**
  - Its pipeline runs in a testable `main(config=None, out_dir=None)`, matching the other exporters.
  - It reads frontmatter as simple single-line `key: value` pairs between the first two `---` lines, accepting quoted values.
  - It skips, with a stderr warning, an unreadable file or one with no `name`.
  - It writes `out/catalogue/index.json` atomically (the existing `write_json` pattern).
- **Missing marketplace folder (AC-C6):** it keeps the previous `out/catalogue/index.json` untouched, warns on stderr, and exits 0.
- **Missing or unreadable installed-plugins file:** every entry is marked `installed: false`, with a warning.
- **`exporters/refresh.py`:**
  - it runs `export_catalogue.py` in `export()` (line 78);
  - it adds `catalogue` to `MANAGED` (line 34);
  - it refuses, without `--allow-mass-delete`, any plan that deletes `catalogue/index`, in the same way as the project-document guard.
- **`exporters/export_sessions.py`:**
  - it emits `agentType` on run docs;
  - it collects `skillUses` while parsing the main transcript;
  - it bumps `PARSER_VERSION`, so cached sessions are re-read once.

  The first push after this change re-sets every run and session document once. Those are sets, not deletes, so the guards are not tripped.

## 5. Page

- **Tab.** A new tab button, `data-tab="catalogue"`, "Agent catalogue", placed straight after Dispatch (`site/index.html:216`). It is visible in every view, projects and "Other sessions" alike, and the keyboard arrow and Home/End keys cover it. It subscribes to `db.doc('catalogue/index')` next to the existing subscriptions (`:895–905`).
- **Summary tiles**, in the existing status-tile language:
  - "Agents used": N of M, for the current view, with the all-sessions N beside it;
  - "Skills used", the same way;
  - "Outside the catalogue": the count of agent types and skills seen but not listed.
- **Groups.** One panel per plugin in `plugins` order. The header shows the plugin name, the purpose line, and a muted "not installed" tag when `installed` is false.
- **Rows.** One per entry:
  - a kind tag (agent or skill);
  - the name, with the id in the mono face (ids only, per the design rules);
  - the description, clamped to two lines with an expandable `<details>` for the rest;
  - uses in the view;
  - last use;
  - the projects whose sessions used it;
  - all-sessions uses;
  - a neutral "never used" tag when there are none.

  Within a group, rows sort by uses in the view, then by name.
- **Outside the catalogue.** A final panel lists the agent types (`Plan`, `general-purpose`) and skills (`artifact-design`, `loop`, …) seen in use but not in `entries`, with the same use columns.
- **Empty and missing states.** With no `catalogue/index`, the tab shows the page's existing "not exported yet" empty state. With no uses in the view, the counts read 0 and every entry reads "never used".
- **Design rules.** Colours only from tokens; `--human` never used here; all store text passed through `esc()`; no motion.

## 6. Acceptance criteria (refined from the parent's AC-C1–AC-C7)

- **AC-C1** `export_catalogue.py`, run against a synthetic marketplace, writes `catalogue/index` in the §3 shape:
  - every agent and skill file becomes one entry with kind, plugin, name, full description and installed flag;
  - plugins get their purpose from the manifest's first sentence, or the plugin name if the manifest is missing;
  - the two paths come from the `catalogue` config block, and the tests pass their own.
- **AC-C2** The tab groups entries by plugin, with the purpose line, and shows each entry's full description through its expandable detail.
- **AC-C3** Usage is taken from the transcripts:
  - `runs/<id>.agentType` is set on subagent runs and absent on manual rows;
  - `sessions/<id>.skillUses` counts `Skill` tool calls and namespaced slash commands, not built-in slash commands;
  - uses outside the catalogue appear only in the "Outside the catalogue" panel.
- **AC-C4** Each entry shows its uses, last use and projects in the current view and its all-sessions uses, or "never used".
- **AC-C5** The tab sits after Dispatch in every view. The "Agents used" and "Skills used" tiles give N of M for the current view, with the all-sessions figure beside.
- **AC-C6** `refresh.py` manages `catalogue` and refuses a plan that deletes `catalogue/index` unless `--allow-mass-delete` is given. A missing marketplace folder keeps the last export, with a warning and exit 0. A missing installed-plugins file marks entries not installed, with a warning.
- **AC-C7** Tests:
  - `tests/test_export_catalogue.py` for the export and its failure paths;
  - additions to `tests/test_export_sessions.py` for `agentType` and `skillUses`;
  - additions to `tests/test_refresh.py` for the managed collection and the guard;
  - additions to `tests/page.test.mjs` for the tab in a project view and in "Other sessions", covering the tiles, grouping, "never used" and the outside panel.

  `python -m unittest discover -s tests` and `node tests/page.test.mjs` are green. No test reads the real `~/.claude`.
- **Close-out:** `CLAUDE.md` documents `catalogue/index`, `agentType`, `skillUses` and the `catalogue` config block, and `review-agents:code-reviewer` returns GO.

## 7. Out of scope

- Other marketplaces.
- Skill use inside subagent transcripts (the main transcript only, per the parent's AC-C3).
- Plugin versions and drift between the marketplace clone and the installed cache.
- The local app's catalogue record (PBI-003 and PBI-019).
