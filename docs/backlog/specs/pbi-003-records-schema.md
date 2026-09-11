---
id: SPEC-PBI-003
title: "Record shapes and SQLite schema for the local-first app"
pbi: PBI-003
parent: docs/backlog/specs/dispatch-board.md (revision 5, approved)
revision: 4
status: approved — spec gate passed at round 3 (APPROVE-WITH-NOTES; every note applied in revision 4)
date: 2026-09-11
reviews: docs/backlog/reviews/PBI-003/spec-review-r1.md (CHANGES-REQUIRED, applied in revision 2); spec-review-r2.md (CHANGES-REQUIRED, applied in revision 3); spec-review-r3.md (APPROVE-WITH-NOTES, notes applied in revision 4)
---

# PBI-003 — Record shapes and SQLite schema (per-PBI spec)

## 1. Intent

This spec defines the local-first app's records once, in one place:
- **The records:** session, run, project, tab, status, last-refresh and catalogue.
- **The store:** the SQLite schema that holds them.
- **What it does not include:** the answer record, which D-22 defers, and for which no table exists.

**Sources:**
- PRD FR-100 to FR-103, FR-105 and AC-69;
- parent spec §PBI areas, G-3, and rows 8 and 12;
- ADR-0001;
- `CLAUDE.md` "How data gets onto the page";
- the v1 exporters, which are the ground truth for today's shapes.

**The governing constraint** (parent G-3): a later host changes only storage and transport. So each record is **identical** to the store document the v1 exporters publish today, and it maps one-to-one to a store path (§3.3).

**How each consumer uses the one definition** (FR-100):
- **The collector (PBI-019) and the local server (PBI-005)** import `records` and `schema`.
- **The data adapters (PBI-006)** are JavaScript in `site/**` and cannot import Python. They use the definition in two ways:
  - They return store-identical documents (the G-3 identity rule).
  - Every validation rule lives in the declarative `SHAPES` table (§3.1), which is shipped as `local/records.shapes.json` (§3.4). PBI-005's snapshot check (AC-69) validates against `SHAPES`. PBI-006's tests may read that JSON file, read-only.

## 2. Scope

- **In:**
  - `local/records.py`: `SHAPES`, `validate`, `COLLECTION`, `store_path`, `TABLES`, `to_row` and `from_row`.
  - `local/records.shapes.json`: the JSON copy of `SHAPES`.
  - `local/schema.py`: `DDL`, `create_schema` and `SCHEMA_VERSION`.
  - Tests under `local/tests/`.
- **Packages:** no `__init__.py` files are created (A-1). The tests insert `local/` and `exporters/` into `sys.path`.
- **One-way imports:** `schema.py` imports `records` (for `TABLES`), and `records.py` imports nothing local.
- **Out:**
  - WAL mode, busy timeouts, `PRAGMA data_version`, pruning and the collector's writes (PBI-019);
  - the server and the snapshot endpoint (PBI-005);
  - the adapters (PBI-006);
  - filling `run.end` (PBI-020);
  - any change to `exporters/**` or `site/**`, which are blocked. The tests only import `exporters/*`.
- **Handoffs to PBI-001,** recorded in `PBI-001.md` (N-5):
  - validate `runs.manual` lane and kind at config load;
  - reserve `meta/lastRefresh` in `board_config.STATUS_DOC`.

## 3. Record shapes

### 3.1 The `SHAPES` table and its grammar

`SHAPES = {kind: SPEC}`, where `SPEC = {"required": {field: TYPE}, "optional": {field: TYPE}, "enums": {field: [values]}}`. `"enums"` is optional in a `SPEC`. Inside a nested spec (`list_of`/`map_of`), `"optional"` may also be omitted, as the catalogue and `skillUses` rows below do. This is a post-gate clarification from the PBI-003 code review; it aligns the text with the spec's own table and doesn't change behaviour.

A `TYPE` is one of these:
- **A scalar string:** `str`, `int`, `number`, `bool`, `null`, `list`, `object`, or `datetime`.
  - `int` excludes `bool`.
  - `number` is an int or float, not a bool.
  - `datetime` is a **string** that `datetime.fromisoformat` parses and whose result has `tzinfo` set, for example `2026-09-11T12:00:00Z` or `…+01:00` (R3-5). A value that isn't a string is a type error; it never raises.
- **A union** of scalars written with `|`, for example `str|null`.
- **A nested spec:**
  - `{"list_of": SPEC}` is a list whose every item is an object checked against `SPEC`;
  - `{"map_of": SPEC}` is an object whose every value is an object checked against `SPEC`.

**How `validate(kind, doc)` works:**
- It is driven **only** by `SHAPES`: no rule is hard-coded outside it.
- It returns a list of error strings, each with a path. For example: `entries[3].kind: 'tool' is not one of ['agent', 'skill']`, or `skillUses['x'].count: expected int`.
- Fields not listed are allowed and kept, at every level.
- `json.dumps(SHAPES)` must succeed.

"Always written" means the v1 exporter writes the field on every document. Those fields are required; the rest are optional.

| Kind | Required | Optional |
|---|---|---|
| `session` | `title` str, `folder` str, `cwd` str, `start` str\|null, `last` str\|null, `project` str\|null, `build` bool, `windowDays` int, `windowMinutes` int, `runs` int, `running` int, `usage` object, `skillUses` `{"map_of": {"required": {"count": "int"}, "optional": {"last": "str"}}}` | `firstPrompt` str |
| `run` | `session` str, `project` str\|null, `seq` int, `lane` str, `label` str, `kind` str, `verdict` str, `tok` int, `min` int | `from` str, `feeds` str, `group` str, `agent` str, `agentType` str, `start` str, `end` str |
| `project` | `name` str, `repoPath` str, `branch` str, `sessions` list, `statusDoc` str, `order` int, `runs` int, `running` int, `last` str\|null, `usage` object\|null | — |
| `tab` | `generatedAt` str | `source` str |
| `status` | — | `title` str, `message` str, `live` bool, `updatedAt` str, `metrics` object |
| `lastRefresh` | `at` datetime, `writer` str | — |
| `catalogue` | `generatedAt` str, `plugins` `{"list_of": {"required": {"plugin": "str", "purpose": "str", "purposeFull": "str", "installed": "bool", "agents": "int", "skills": "int"}}}`, `entries` `{"list_of": {"required": {"id": "str", "kind": "str", "plugin": "str", "name": "str", "description": "str", "installed": "bool"}, "enums": {"kind": ["agent", "skill"]}}}` | `source` object |

**Enums:**
- **`run.kind`:** `running`, `done`, `go`, `changes`, `nogo`, `killed`.
- **`run.lane`:** `orch`, `req`, `plan`, `cw`, `tw`, `cr`, `ver`, `other` (the exporter's `LANE` map and its `other` fallback), plus `human`, the lane the page defines for manual owner rows (`site/index.html`'s lane list). This corrects revision 2's citation (I-1).
- **`lastRefresh.writer`:** `collector`, `refresher`.

**Rules and notes:**
- **Timestamps:** only `lastRefresh.at` is a strict `datetime`, because FR-105 computes staleness from it. Run and session times come from `stamp()`, which also accepts times with no timezone, so they stay `str` (N-8).
- **Catalogue ids:** the rule that `catalogue.entries[].id` equals `plugin:name` is an exporter invariant. **`validate` does not check it.** T2 asserts it on exporter output.
- **`run.agent`** is written only when `lane` is `other`. **`run.end`** is defined here (FR-101) and filled by PBI-020.
- **Manual rows:** `runs.manual` lane and kind values are free text in the config. The enums stay strict, so `to_row` rejects a bad manual row. How the collector reports that is PBI-019's decision, and validating those values at config load is logged for PBI-001.
- **Integer types:** `windowDays`, `windowMinutes` and `tok` are ints as long as the config and transcripts hold ints. PBI-001's config type checks guard this (I-2).

### 3.2 Id forms

Every id is one non-empty string. Each kind's form is:

| Kind | Id form |
|---|---|
| session, run | a non-empty string with no `/` or `\`, no control characters, and not `.` or `..` (R3-3). Manual run ids come from the config. |
| project | `^[A-Za-z0-9_-]{1,100}$` (`board_config.ID`) |
| tab | `<projectId>.<tab>`: the project part matches the project form; the tab is `spec`, `assumptions`, `decisions`, `backlog` or `git` |
| status | `^(meta\|status)/[A-Za-z0-9_-]{1,100}$` (the same form as `board_config.STATUS_DOC`), **except `meta/lastRefresh`**, which is reserved |
| lastRefresh | `lastRefresh` |
| catalogue | `index` |

Every id and path pattern is applied with `re.fullmatch` (R3-2). `re.match` with `$` would also accept a trailing newline. This deliberately differs from `board_config.ID` and `STATUS_DOC`, which use `re.match`, but only for strings that end in a newline.

A tab document does not carry its own name, so `validate` does not check id forms. `store_path` and `to_row` do, and they raise `ValueError` for a bad one.

### 3.3 Store paths (the G-3 mapping)

`store_path(kind, id)` checks the id form (§3.2) and returns the store path:

| Kind | Store path |
|---|---|
| session | `sessions/<id>` |
| run | `runs/<id>` |
| project | `projects/<id>` |
| tab | `projectTabs/<id>` |
| status | `<id>` (`meta/<x>` or `status/<x>`) |
| lastRefresh | `meta/lastRefresh` |
| catalogue | `catalogue/index` |

Reserving `meta/lastRefresh` keeps the mapping one-to-one. A per-project last-refresh record would need a new store path; that is a low-impact future change (A-4).

### 3.4 The shipped JSON copy

`local/records.shapes.json` is `json.dumps(SHAPES, indent=2, sort_keys=True)` plus a trailing newline. `python local/records.py --write-shapes` regenerates it. T1 asserts the committed file equals `SHAPES`, so the two can't drift.

## 4. SQLite schema

The schema is Python standard library `sqlite3`, and the file is created by the collector (PBI-019).

**`TABLES`** is defined in `records.py` as `{kind: (table, columns)}`:

| Kind | Table | Columns |
|---|---|---|
| session | `sessions` | `id`, `project`, `last`, `doc` |
| run | `runs` | `id`, `session`, `project`, `seq`, `start`, `doc` |
| project | `projects` | `id`, `ord`, `doc` |
| tab | `project_tabs` | `id`, `project`, `tab`, `doc` |
| status | `statuses` | `id`, `doc` |
| lastRefresh | `last_refresh` | `id`, `doc` |
| catalogue | `catalogue` | `id`, `doc` |

**Columns:**
- `id TEXT PRIMARY KEY`.
- `doc TEXT NOT NULL`, holding the record as canonical JSON: `json.dumps(sort_keys=True, ensure_ascii=False, allow_nan=False)`. `doc` is the source of truth. Sorted keys differ from the exporters' insertion order, but dict equality and G-3 are unaffected (I-3).
- **Key columns:**
  - most come from `doc`: `sessions.project`/`last`, `runs.session`/`project`/`seq`/`start`, and `projects.ord`, which is `doc.order`;
  - `project_tabs.project` and `tab` come from the **id**;
  - a missing optional value is `NULL`.

**Indexes:** `sessions(project)`, `sessions(last)`, `runs(session)`, `runs(project)`, `project_tabs(project)`. There is no `answers` table.

**Rows:**
- **`to_row(kind, id, doc)`** checks the id form, then `validate`. It returns a **dict mapping each column to its value**, including `id` and `doc`, and raises `ValueError` listing the errors.
- **`from_row(kind, row)`** accepts either a mapping that has `doc` (such as a `sqlite3.Row` or a dict) or the `doc` text, and returns the document dict.

**`create_schema(conn)`: the mechanism** (N-3, verified against Python 3.14 and SQLite 3.50):
1. If `conn.in_transaction` is true, raise `ValueError`. This also rejects `autocommit=False` connections, which are always inside a transaction. The collector passes a default connection.
2. Run `conn.execute("BEGIN IMMEDIATE")`. This also stops two processes both upgrading.
3. Read `PRAGMA user_version` inside the transaction. If it is greater than `SCHEMA_VERSION` (1), run `conn.execute("ROLLBACK")` and raise `RuntimeError`.
4. Run each statement in the module-level `DDL` list with `conn.execute()`, never `executescript()`, which would commit any open transaction. The statements are all `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`, so a partial version-1 file heals. This runs whenever `user_version` is 0 or 1.
5. Run `conn.execute("PRAGMA user_version = 1")`, then `conn.execute("COMMIT")`.
6. On any exception, run `conn.execute("ROLLBACK")` and re-raise. The file is then left exactly as it was.

The steps use explicit `COMMIT` and `ROLLBACK` statements, not `conn.commit()` and `conn.rollback()`. On an `autocommit=True` connection those two methods do nothing, whereas the explicit statements work in the default, `isolation_level=None` and `autocommit=True` modes. This was verified at spec-gate round 3 (R3-1).

**Healing limits:** healing cannot repair a table whose columns are wrong. That is acceptable at version 1 (I-6). Any schema change after version 1 needs a PBI whose `allowed_areas` include `local/schema*`, and none is planned. PBI-019 prunes by age, using the `sessions(last)` index.

## 5. Tests (`local/tests/`, standard library `unittest` only)

The fixtures are built inside `local/tests/`; nothing is imported from `tests/test_*.py`. The run command is `python -m unittest discover -s local/tests`.

**T1. Shapes and grammar:**
- For each kind that has required fields, a missing required field.
- For each kind: a minimal valid document, a wrong type, and an unknown field (kept).
- `status`, which has no required fields: a wrong-typed `live` and a valid empty `{}` (N-9a).
- The enums (`run.kind`, `run.lane`, `lastRefresh.writer`).
- Nested rules, all coming from `SHAPES`, with error paths:
  - `entries[i].kind` not in the enum;
  - `entries[i]` missing `installed`;
  - `plugins[i].agents` not an int;
  - `skillUses[k].count` not an int, and a `skillUses` value that is not an object.
- `int` rejecting `bool`.
- `datetime`:
  - valid: `2026-09-11T12:00:00Z`, `2026-09-11T12:00:00+01:00`;
  - also valid: `2026-09-11T12:00:00+0100`;
  - invalid: a string with no timezone, `not a time`, and a non-string such as `5`, which is a type error and does not raise (R3-5).
- A run carrying `start`, `end`, `agentType` and `agent` as strings passes, and one with `end: 5` fails (AC-D3, R3-4).
- Nullable fields: session `start`/`last` and project `usage`/`last`.
- `json.dumps(SHAPES)` succeeds.
- The committed `local/records.shapes.json` equals `SHAPES`.

**T2. Conformance with v1** (AC-D2). Run the exporters in-process on synthetic input in a temporary folder, using their real signatures:
- `export_sessions.main(config, out_dir, projects_root, now)`;
- `export_board.main(config, out_dir, data_dir, now)`, with the git tab skipped when git is unavailable;
- `export_catalogue.main(config, out_dir, now)`;
- then `refresh.plan(out)`. The config has one project on `meta/status` and one on `status/<pid>`, so both forms are written.

**Which documents are validated:**
- **Every document written,** mapped by folder: `sessions/` is session, `runs/` is run, `projects/` is project, `projectTabs/` is tab, `catalogue/index.json` is catalogue, and `meta/status.json` and `status/*.json` are status.
- **Excluded:** `.cache/`, `.pending.json` and `.pushed.json` (N-9d).
- **Also asserted:** each document's `store_path` equals its relative path, and every `entries[].id` equals `plugin:name`.

**Required cases:**
- a running run, which needs a recent file time, and a killed run;
- a lane-`other` run, which carries `agent`;
- a `runs.manual` row, with no `agentType` or `start`;
- a session with a skill use that has no readable time;
- `showFirstPrompt` on;
- a project with an empty `sessions` list, so `usage` and `last` are null;
- a linked session with no readable timestamps, so `start` and `last` are null (N-9c);
- a linked session and an unlinked one;
- a **kept tab produced by the exporter itself**: run `export_board` twice, moving `repoPath` away before the second run (N-9b);
- the catalogue.

Nothing is read from the real `out/`, `~/.claude` or the store.

**T3. Schema:**
- `create_schema` twice, which is idempotent;
- `user_version == 1`;
- the tables and the **named** indexes, read from `sqlite_master` and ignoring `sqlite_autoindex_*` (R3-6);
- no `answers` table;
- `user_version` 2 raises and leaves the file unchanged;
- a partial file, with one table dropped at version 1, heals;
- a connection already in a transaction raises `ValueError`;
- a connection opened with `autocommit=True` commits the schema, and on a forced failure leaves no tables, `user_version` 0 and no open transaction (R3-1);
- **atomicity:** patch `schema.DDL` to append a failing statement, then assert no tables and `user_version` 0 (N-3).

**T4. Rows and paths:**
- `to_row` returns a dict with exactly `TABLES[kind]` columns;
- `to_row` then `from_row` returns an equal document for every kind;
- `from_row` accepts a mapping or `doc` text;
- the key columns match, with the tab columns coming from the id;
- an invalid document raises;
- NaN raises;
- `store_path` for every kind;
- a bad id form raises for every kind, including an id containing `/` and a bad project part in a tab id;
- `store_path('status', 'meta/lastRefresh')` raises;
- run and session ids `.`, `..`, or containing `\` or a control character raise, and so does any id ending in a newline (R3-2, R3-3);
- the status id form accepts every value `board_config.STATUS_DOC` accepts except `meta/lastRefresh`, checked by importing `board_config` and comparing on a sample set that excludes strings ending in a newline (N-1, R3-2).

## 6. Acceptance criteria

- [ ] **AC-D1** `local/records.py` defines the seven kinds in a declarative `SHAPES` table whose grammar (§3.1) includes nested `list_of`/`map_of` specs and a strict `datetime` type. `validate(kind, doc)` is driven only by `SHAPES` and returns path-qualified errors, empty when valid. Unknown fields are kept. `SHAPES` is JSON-serialisable, and `local/records.shapes.json` equals it.
- [ ] **AC-D2** Every document the v1 exporters and `refresh.plan` write validates against its kind, across all the T2 cases, and its `store_path` equals its path.
- [ ] **AC-D3** The run shape carries the optional `start`, `end`, `agentType` and `agent`. The session shape carries `skillUses` (FR-101; parent §PBI-003).
- [ ] **AC-D4** A `lastRefresh` record, with id `lastRefresh` and store path `meta/lastRefresh` (reserved, so no status document can take it), carries a strict `datetime` `at` and a `writer` (FR-102, FR-105).
- [ ] **AC-D5** `create_schema(conn)` follows §4's mechanism:
  - it creates the tables and indexes in one `BEGIN IMMEDIATE` transaction at `user_version` 1, and is idempotent;
  - it heals a partial file;
  - it refuses a newer version, or a connection already in a transaction;
  - it leaves the file untouched on any failure;
  - it creates no `answers` table.
- [ ] **AC-D6** `to_row` returns the column dict for `TABLES[kind]`, and `from_row` inverts it for every kind. Both reject invalid records and bad id forms (§3.2). `store_path` implements §3.3.
- [ ] **AC-D7** The code is standard library only. `python -m unittest discover -s local/tests` passes, and so do the two configured suites.
- **AC-69 (PRD):** PBI-003 **contributes** through AC-D2. AC-69 itself is verified by PBI-005. At close-out it is recorded as "contributed via AC-D2; verified in PBI-005", not ticked.

## 7. Assumptions and open questions (all resolved)

| # | Question | Resolution |
|---|---|---|
| A-1 | Are packages needed? | **RESOLVED:** no. `sys.path` insertion, as in `tests/test_export_board.py:11`; imports are one-way. |
| A-2 | `local/tests/` isn't in the canonical suite. | **Default accepted:** a chore PR adds `local = "python -m unittest discover -s local/tests"` to `[test_commands]` before PBI-019 or PBI-005 starts. Until then, PBI-003's run-report names all three commands. |
| A-3 | Is `min` a number or a string? | **RESOLVED:** an int, as is `tok` (`export_sessions.py:252`, `:485`, `:729`). |
| A-4 | Should last-refresh be one global record? | **RESOLVED:** yes, one global record (FR-103, row 12). `meta/lastRefresh` is reserved (§3.2), and PBI-001 reserves it in `STATUS_DOC`. |
| A-5 | Is `doc` the source of truth? | **RESOLVED:** yes (G-3). |

**Informational, no change:**
- **I-5:** the hand-written `snapshot/runs/r01`–`r33` lack `session` and `project`. They are unmanaged and never served locally.
- **I-4:** the PBI-003 gate-tracking row is updated to revision 3.
- **R3-8:** parent row 12 / PRD A-39's "keyed by project id plus row or PBI id" applies to per-row records, such as the deferred answer record. None of the seven kinds here is per-row.

## 8. Spec-gate record

| Round | Revision reviewed | Verdict | Review note |
|---|---|---|---|
| 1 | 1 | CHANGES-REQUIRED (1 High, 8 Medium, 5 Low, 1 Info) | `docs/backlog/reviews/PBI-003/spec-review-r1.md` |
| 2 | 2 | CHANGES-REQUIRED (3 Medium, 6 Low) | `docs/backlog/reviews/PBI-003/spec-review-r2.md` |
| 3 | 3 | APPROVE-WITH-NOTES (1 Medium, 4 Low, 3 Info), all applied in revision 4 | `docs/backlog/reviews/PBI-003/spec-review-r3.md` |

- **Reviewer:** same-vendor, a clean-context Claude Code Plan subagent following `pbi-review`. The resolved gate is `spec: agent` (tier assisted).
- **The gate passed** on 2026-09-11, within `spec_review_max_rounds = 3`.
