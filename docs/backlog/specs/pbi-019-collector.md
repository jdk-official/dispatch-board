---
id: SPEC-PBI-019
title: "Collector: incremental transcript and catalogue reads into SQLite, with the mass-delete and network-path guards"
pbi: PBI-019
parent: docs/backlog/specs/dispatch-board.md (revision 5, approved)
revision: 3
status: approved at spec-gate round 3; built and merged (PBI-019, PR #15, squash b23df89, 2026-09-12)
date: 2026-09-11
reviews: docs/backlog/reviews/PBI-019/spec-review-r1.md (round 1, revision 1, CHANGES-REQUIRED); docs/backlog/reviews/PBI-019/spec-review-r2.md (round 2, revision 2, CHANGES-REQUIRED); round 3 approved revision 3
closeout_note: "Front matter corrected 2026-09-12. It read 'awaiting round 3' after the spec had passed and the PBI had merged — stale status carried past close-out. Raised as N-5 at PBI-025's spec-gate round 2."
---

# PBI-019: Collector (per-PBI spec)

## 1. Intent

The collector is the local-first app's only writer. It follows the Claude Code transcripts as they grow and writes session, run, project, catalogue and last-refresh records into the local SQLite database. The local server (PBI-005) reads that database and pushes changes to the page.

**Sources:**
- PRD revision 3: FR-86, FR-87, FR-88, FR-96, FR-100 to FR-103, FR-180, FR-184, FR-185, NFR-17 to NFR-21, C-14, C-16, C-21, AC-34, AC-42, AC-44, AC-63, AC-64, AC-115, AC-119 to AC-121, A-37 and A-47;
- parent spec: Key decisions ("all derivations live in one shared module… the collector imports it, never re-implements it"), the local-first order, the derivation rule, PBI-019's areas, and rows 8, 12 and 24;
- ADR-0001;
- the PBI-003 spec (`pbi-003-records-schema.md`), the PBI-004 review follow-ups (`docs/backlog/reviews/PBI-004/findings.json`) and the PBI-003 review follow-ups copied into `PBI-019.md`;
- the spec-gate reviews, round 1 (`docs/backlog/reviews/PBI-019/spec-review-r1.md`), applied in revision 2, and round 2 (`docs/backlog/reviews/PBI-019/spec-review-r2.md`), applied in this revision (§11).

**Three rules govern the design:**
- **Equivalence (FR-87, AC-64).** For the same transcripts, config and `now`, the database holds exactly the documents `export_sessions.py` writes. Where this spec has to pick between a cleaner design and matching the exporter, it matches the exporter.
- **Read only what was appended (FR-86, AC-63).** A transcript already read is reopened only to read its new bytes, never from the start. Derivation state therefore persists between passes and across restarts (§4.3).
- **Reuse, never re-implement.** The collector calls `derive`, `records`, `schema`, `board_config`, and the helper functions of `export_sessions` and `export_catalogue`. The one exception, a few lines of glue, is named in §4.4 and row Q-12.

## 2. Scope and module layout

**Files it creates or changes (all within its allowed areas):**

| File | Contents |
|---|---|
| `local/db.py` | Opening the database: the network-path guard, the read-only pre-check, WAL mode, `schema.create_schema`, the collector's state tables, the column re-check, the write helpers and the `Changes` watcher (§3) |
| `local/collector.py` | One pass (§4), the state codec (§4.3), the guards (§4.7) and the command line (§5) |
| `local/tests/test_db.py`, `test_collector.py`, `test_collector_equivalence.py`, `test_config_local.py` | Tests (§7) |
| `exporters/board_config.py` | New `local(cfg)` reader for the database-path key (§3.1) |
| `board.config.json` | New `"local": {"databasePath": "out/local/board.db"}` block |

**Imports.** There are no packages (PBI-003 A-1). `local/collector.py` inserts the repository's `exporters/` folder into `sys.path`, found from `__file__`, and runs from any working folder; `local/` is already on `sys.path` when it runs as a script. Imports only ever go from `local` to `exporters`:
- `derive`: every derivation (§4.4), and `new_session` / `new_agent` for the state key check (§4.3);
- `board_config`: `projects`, `manual`, `catalogue`, and the new `local`;
- `export_sessions`: `settings` (config typing and defaults, identical to the exporter's), `load_meta`, `cwd_of` and `PARSER_VERSION`. None of them does I/O at import;
- `export_catalogue`: `main`, for the catalogue read (§4.5);
- `records` and `schema`, through `db`.

The collector does not import `export_board`, so the `carried` name clash in the PBI-004 follow-up does not arise.

**Records it writes:** `session`, `run`, `project`, `catalogue` and `lastRefresh`. "Usage" and "skill-use" (FR-87) are fields of those records (`session.usage`, `session.skillUses` and `project.usage`), not kinds of their own. It writes **no** `tab` and **no** `status` record (row Q-2), and never an answer (C-16).

## 3. Database (FR-88, FR-96, FR-180, C-14, C-21)

### 3.1 The path key

- **Config:** `board.config.json` gains `"local": {"databasePath": "out/local/board.db"}`. PBI-005 adds its port to the same `local` block (parent: "the second to land merges").
- **`board_config.local(cfg)`** returns `{"databasePath": <str>}`, with the default filled in and a leading `~` expanded. It follows the style of `catalogue()`:
  - a `local` block that is not an object raises `ValueError('"local" must be an object, not <type>')`;
  - a `databasePath` that is not a string, or is empty or blank, raises `ValueError('local.databasePath must be a non-empty string, not <repr>')`.
- **Resolution.** The collector resolves a relative path against the **repository root**, never the working folder, because Task Scheduler may start it in `System32` (PBI-007).
- **Default:** `out/local/board.db`. `out/` is already git-ignored, so the file, its `-wal` and its `-shm` are never committed, and no v1 exporter or `refresh.py` touches `out/local/` (row Q-6).

### 3.2 The network-path guard (FR-96, FR-180, AC-115)

`db.network_path(path)` runs these checks **in this order and stops at the first one that is true** (review R2-8):
1. the path exactly as configured starts with `\\` or `//`;
2. its absolute form, `os.path.abspath` (after resolution against the repository root, §3.1), starts with `\\` or `//`;
3. on Windows only, the drive letter of the absolute form is a mapped network drive: `GetDriveTypeW` returns `DRIVE_REMOTE`, through `ctypes`, behind a seam the tests patch (row Q-16);
4. its real path, `os.path.realpath`, which follows symbolic links and junctions, starts with `\\` or `//`, or (on Windows) has a drive letter for which `GetDriveTypeW` returns `DRIVE_REMOTE`. A link on a local disk that points into a share is caught only this way.

That covers `\\server\share\…`, `//server/share/…`, `\\?\UNC\…`, a relative path resolved from a UNC working folder, a mapped network drive, and a link into a share.

**What the checks touch.** Checks 1 and 2 work on strings only. Check 3 asks Windows about a drive letter. Check 4 runs only for a path that checks 1 to 3 found local. None of them reads or writes the contents of any file, and none creates anything. Two of them are not purely local, and this spec says so plainly:
- `GetDriveTypeW` on a mapped drive letter may make Windows contact the file server behind it;
- `os.path.realpath` may open a handle to an existing path, or to the links along it, to read its final name. It asks for no access to the contents. When a link leads into a share, resolving it may contact that file server.

In both cases the path is then refused, and nothing else happens. Stopping at the first hit means a path already refused by its string form never reaches either call, and a mapped drive is refused by check 3 before `realpath` would resolve through it.

**`\\?\` paths are refused on purpose.** A local extended-length path such as `\\?\C:\data\board.db` also starts with `\\`, so it is refused as a network path. That is deliberate: it fails safe, and it follows FR-180 literally ("starts with `\\` or `//`"). The owner writes the path without the prefix.

`db.open_db(path)` checks the guard **before anything else touches the path**: before it, nothing creates a folder or a file, and nothing opens the path for reading or writing. The only access is what the guard's own checks make, as listed above. On a network path it raises `db.NetworkPath`, whose message holds the path **exactly as configured**. The collector prints `collector: refusing to start: the database path <configured path> is a network path; SQLite over SMB or NFS is unsafe (C-14)` to stderr and exits 2.

PBI-005 imports the same helper for its own FR-96 check.

### 3.3 Opening sequence (`db.open_db`)

The order guarantees two things: a fresh file is never refused, and a foreign file is never modified before it is refused.

1. **Network-path guard** (§3.2).
2. **Parent folder:** create it if it is missing.
3. **Connect:** `sqlite3.connect(path, isolation_level=None, timeout=10)`. With `isolation_level=None` every transaction is explicit (`BEGIN IMMEDIATE` … `COMMIT`/`ROLLBACK`, as in `schema.py`), and `create_schema` finds no open transaction. The timeout sets a busy wait of 10 s (lock scope: §3.5).
4. **Read-only pre-check** (PBI-003 follow-up, "foreign tables"). This step runs only `PRAGMA` reads and a `SELECT` on `sqlite_master`; it writes nothing.
   - `PRAGMA user_version` greater than `schema.SCHEMA_VERSION` raises `db.Refused` naming the path and both versions.
   - For every table in `records.TABLES` **that already exists**, `PRAGMA table_info(<table>)` must list exactly the expected column names, in order. Otherwise raise `db.Refused` naming the table, its columns and the expected ones, for example `statuses(x)`.
   - **Missing tables are fine**: `create_schema` adds them in step 6. A fresh file has none and passes.
   - `collector_*` tables are not refused here; step 7 deals with them.

   A file refused here keeps its journal mode, its tables and its `user_version`. The collector exits 2.
5. **WAL:** `PRAGMA journal_mode=WAL`. If the returned mode is not `wal`, raise `db.Refused` naming the path and the mode; the collector exits 2. Then `PRAGMA synchronous=NORMAL`, which is durable in WAL mode: a power cut can lose the last pass but never corrupts, and the cursors roll back with the records (§3.5).
6. **Records schema:** `schema.create_schema(conn)`. Its `RuntimeError` (a newer `user_version`, which step 4 already catches unless another process changed the file in between) becomes `db.Refused`; exit 2.
7. **State tables** (§3.4), in one `BEGIN IMMEDIATE` transaction:
   - if **any** `collector_*` table exists with columns other than the expected ones, **all three** state tables are dropped together (review R2-8), with the warning `collector: state table <table> had columns (<columns>); all three state tables dropped and recreated, so every transcript is read again from the start`. Dropping all three is what makes that warning true: no cursor, state or marker survives to skip a read. The state is a disposable cache, so this costs one full re-read and never a refusal;
   - then `CREATE TABLE IF NOT EXISTS` for each state table.
8. **Re-check:** `PRAGMA table_info` for every table in `records.TABLES` and every state table must now list exactly the expected columns, in order. Otherwise raise `db.Refused` as in step 4; exit 2. This catches a race with another writer or a defect in steps 6 and 7.

The pre-check and the re-check run on **every** open, not only on files the collector did not create.

**A file that is not a database** (review R2-6). Any `sqlite3.DatabaseError` raised in steps 3 to 8, for example "file is not a database", becomes `db.Refused` naming the path and the error; the collector exits 2. The one exception is `sqlite3.OperationalError` "database is locked" (a subclass of `DatabaseError`), which stays the lock case of §3.5. A file at the path that is not a SQLite database fails at the first statement of step 4, which only reads, so it is refused **unmodified**: the same bytes as before, and no `-wal` or `-shm` file is left beside it.

### 3.4 The collector's state tables

The derivation state (§4.3) has to commit **in the same transaction** as the records it produced. Otherwise a crash between the two either reads bytes twice (counting skill uses twice) or loses them. `ATTACH` is not atomic across files in WAL mode, so the state lives in the same file, in three tables that `db.py` owns:

```sql
CREATE TABLE IF NOT EXISTS collector_sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)
CREATE TABLE IF NOT EXISTS collector_agents (session TEXT NOT NULL, agent TEXT NOT NULL, data TEXT NOT NULL,
                                             PRIMARY KEY (session, agent))
CREATE TABLE IF NOT EXISTS collector_excluded (dev TEXT NOT NULL, ino TEXT NOT NULL, size INTEGER NOT NULL,
                                               rule TEXT NOT NULL, PRIMARY KEY (dev, ino))
```

- `collector_excluded` holds the content-free exclusion markers of §4.1: no session id, no path, no `cwd`, no title.
- **`dev` and `ino` are `TEXT`** (review R2-3): each is `str(st_dev)` and `str(st_ino)`, the decimal digits of the value `os.stat` returns. On Windows `st_ino` is an unsigned 64-bit file ID, and from Python 3.12 it can be 128-bit on ReFS (Dev Drive), so it can exceed SQLite's signed 64-bit `INTEGER`. As text it never binds as an integer, so no `OverflowError` is possible. `size` stays `INTEGER`: `st_size` fits in 63 bits. The cursors (§4.2) hold `dev` and `ino` inside the JSON state, where `json` writes and reads integers of any size, so they never bind as SQLite integers either.
- They are not records: they are outside `records.TABLES` and `SHAPES`, leave `user_version` alone, and are never served.
- They are a **disposable cache**. Dropping them costs one full re-read and loses nothing that the transcripts and the config cannot rebuild; so a column mismatch in any one of them drops and recreates all three together (§3.3 step 7).
- **Not a PBI-003 schema change** (row Q-1, settled by the spec-gate reviewer): PBI-003 §4 governs the records schema, and these tables sit outside `records.TABLES`, `schema.py` and `user_version`.
- **Handoff to PBI-005:** the server must ignore every `collector_*` table.

### 3.5 Transactions

- **One transaction per pass.** Each pass runs entirely inside `BEGIN IMMEDIATE`: it reads the stored records and state, reads the files, derives, computes the deletions and the guard, then writes records, deletes, state and last-refresh, and ends with `COMMIT` (§4.6).
- **Readers.** In WAL mode readers never block this, so the server keeps serving the last committed state during a pass.
- **Failure.** Any exception that §4.9 does not handle ends in `ROLLBACK`, and the in-memory cache is dropped (§4.3). A refused pass (§4.7) also ends in `ROLLBACK`.
- **Write helpers:**
  - `db.upsert(conn, kind, row)` runs `INSERT INTO <table> (<cols>) VALUES (…) ON CONFLICT(id) DO UPDATE SET <col>=excluded.<col>, …`, taking a row from `records.to_row`;
  - `db.delete(conn, kind, id)`;
  - `db.stored(conn, kind)` returns `{id: doc}` through `records.from_row`.
- **Lock scope.** A pass holds the database's write lock from its `BEGIN IMMEDIATE` to its `COMMIT` or `ROLLBACK`: across every file read, the catalogue export (§4.5), derivation and the writes. `open_db` holds it briefly in steps 6 and 7. A first full read of many transcripts can hold it for longer than another collector's 10 s busy wait.
- **Two collectors at once** (a manual run beside the Task Scheduler one) are safe:
  - `BEGIN IMMEDIATE` serialises the passes;
  - each pass reads cursors and state inside its own transaction;
  - a pass whose connection sees a `PRAGMA data_version` different from the value recorded after its own last commit reloads its cache from the database before reading any file;
  - a collector whose `BEGIN IMMEDIATE`, or any of whose `open_db` steps 3 to 8 (in practice steps 6 and 7), fails with `sqlite3.OperationalError` "database is locked" prints `collector: another collector holds the database lock on <path>; this pass did not run` to stderr. With `--once` it exits 1; in loop mode it tries again at the next interval (§5).

### 3.6 Change signalling for the server (`PRAGMA data_version`)

`db.Changes(conn)` is a small watcher for PBI-005:
- `poll()` runs `PRAGMA data_version` on the **server's own** connection. It returns `True` when the value differs from the previous poll, and `False` otherwise; the first poll returns `False`.
- `data_version` changes only for commits made by **other** connections, so the server must not share the collector's connection.
- A pass that commits changes it. A refused or failed pass rolls back and does not.
- A successful pass always commits at least the last-refresh record (§4.8), so the server sees one change per successful pass. PBI-005 decides what to push, for example by diffing records.
- **Handoff to PBI-005:** poll outside any open read transaction. A long-held read transaction stops WAL checkpoints and makes the `-wal` file grow.

## 4. One pass

`collector.run_pass(conn, config, projects_root=None, now=None, allow_mass_delete=False, clock=None) -> PassReport`. The signature mirrors `export_sessions.main(config, out_dir, projects_root, now)` so the tests can run both on the same input. `now` is epoch seconds and defaults to `time.time()`. `clock` returns the last-refresh time and defaults to `datetime.now(timezone.utc)`.

### 4.1 Settings and discovery, as the exporter does them

1. `st = export_sessions.settings(config, projects_root)`. A `ValueError` fails the pass with exit 2 and writes nothing, as the exporter does.
2. If `st['root']` is not a folder, the pass fails (exit 2), naming the path.
3. `mains = glob.glob(os.path.join(st['root'], '*', '*.jsonl'))`: **the same call, iterated in the order it returns, not sorted.** Sorting rows by `start` is stable, so on ties (for example runs with no start) the order in which sessions are visited decides `seq`, the `runs.manual` anchors and `link`. Matching the exporter needs the same order (row Q-12).
4. A linked session (`st['build']`) with no main transcript fails the pass (exit 2), naming the ids, as the exporter does.
5. Per main transcript, in order, with `t0 = now`:
   - **Window by file time.** An unlinked session whose file time is more than `days` old is skipped **without being opened**. Its stored records, if any, become deletions for reason `age` (§4.7), and its state rows are deleted (§4.3, "Which sessions keep state").
   - **Exclusion.** When `st['exclude']` is non-empty, `derive.excluded(patterns, folder, cwd)` decides. It matches the folder or the `cwd`, so the collector asks in this order and stops at the first answer:
     1. the folder alone, `derive.excluded(patterns, folder, '')`: no file is read;
     2. for a session already in state, the `cwd` held in its derive state: no file is read;
     3. an **exclusion marker** (below) that matches this file: excluded, and no file is read;
     4. otherwise `export_sessions.cwd_of(path)`, which reads the start of the file, as the exporter does.

     An excluded session has **no state and no records**: nothing is read incrementally, cached or stored. A session that becomes excluded, because the config changed or because its first `cwd` arrives in newly appended lines, has its state rows and records removed, with deletions for reason `other` (§4.7).
   - **Exclusion markers** (review S-4; choice: the marker, not a parity exception). When step 4 finds a **non-empty** `cwd` that the patterns exclude, the pass stores a `collector_excluded` row `(dev, ino, size, rule)`: the file's `st_dev`, `st_ino` and `st_size`, and `rule`, the SHA-256 hex digest of `json.dumps(st['exclude'])`. It holds no session id, path, `cwd` or title. A marker matches a file when its `(dev, ino)` equals the file's, the file's size is at least the marker's `size`, and `rule` equals the current digest; the pass then updates `size`.
     - **A marker that does not match is deleted** (review R2-2). When step 3 finds a marker with the file's `(dev, ino)` but a smaller file size or a different `rule`, the pass deletes that marker and step 4 decides again. If step 4 finds the file still excluded, it stores a new marker in its place (same `(dev, ino)`, current size and digest); otherwise none remains. So a file truncated and rewritten with a `cwd` that is not excluded can never be matched again by the old marker once it grows back past the old size.
     - A marker whose `(dev, ino)` belongs to no main transcript this pass is deleted.
     - **Why this keeps equivalence:** the exporter decides from the file's first `cwd`, and in a file that is only appended to, the first `cwd` never changes. A replaced file (new `ino`), a truncated one (smaller size) or a changed `exclude` list (new digest) all fall back to step 4. The folder cannot undo a `cwd` match, because `derive.excluded` is true when either matches.
     - **No marker** is stored when `cwd_of` returns `''` (the file has no `cwd` line yet, so a later line can still decide), or when `st_ino` is 0 (a file system with no `ino`). Those files are checked through `cwd_of` on every pass, as the exporter does (row Q-9).
   - **Window by last activity.** After derivation, a session enters the results only if it is linked, or its `doc.last` is within `days` of `t0`, exactly as the exporter judges it. A stored session that fails this test becomes a deletion for reason `age`. **Its records go, but its state and cursors stay** (review R2-1; §4.3, "Which sessions keep state"), as the exporter keeps it in its cache (`export_sessions.py:244, 266-268`). The same holds for a session whose result is `None` (nothing answered yet): it keeps its state and cursors and has no records.

### 4.2 Incremental reads (FR-86, AC-63)

**A cursor** is stored per transcript file, the main transcript and each `subagents/agent-*.jsonl`, inside that file's state (§4.3). It holds `{path, dev, ino, offset, size, mtime}`. `offset` is the byte position just after the last complete line consumed.

**The read procedure** is `collector.read_new(cursor, path) -> (lines, new_cursor, reset)`:
1. `os.stat(path)` (not a read).
2. **Replaced:** if the cursor has a non-zero `ino` and `(st_dev, st_ino)` differs, the file was replaced (for example by `os.replace`). Reset: offset 0, and this file's derive state is discarded.
3. **Truncated:** if `st_size < offset`, reset the same way.
4. **Unchanged:** if `st_size == offset`, return no lines **without opening the file**. The new cursor still takes the `mtime` from step 1, so a changed file time is seen without a read (§4.4 step 3).
5. Otherwise open in binary through the module seam `collector._open`, `seek(offset)`, and `read(st_size - offset)`: exactly the new bytes, no more.
6. **Partial trailing line:** keep the bytes up to and including the last `b'\n'`. Any bytes after it are held back, and `new_cursor.offset` advances only past the last `b'\n'`. The next pass reads the held-back fragment again together with its completion, because they are bytes of the same appended line.
7. **Decoding as the exporter does:** decode the kept bytes by iterating `io.TextIOWrapper(io.BytesIO(chunk), encoding='utf-8', errors='replace')`. That is the same decoder and the same universal-newline splitting as the exporter's `io.open(path, encoding='utf-8', errors='replace')`. Cutting at `b'\n'` never splits a UTF-8 sequence or a `\r\n` pair. Each line goes through `derive.parse_line` / `record_pairs`.

`read_new` returns a new cursor and never changes the one it was given; the caller keeps the new cursor only if feeding succeeds (§4.3, "Feeding a copy").

**Files that appear or disappear:**
- **New files** start with an empty cursor (offset 0).
- **A deleted agent file** loses its state row, and its run becomes a deletion for reason `other`.
- **A deleted main transcript** takes its session, and every one of that session's agent states, with it. The deletion has reason `age` when the session is unlinked and its stored session record's `last` is more than `days` before `t0` (Claude Code's own clean-up of old transcripts); otherwise reason `other` (§4.7). A linked one fails the pass instead (§4.1).

**Consequences:**
- A session skipped by the window, or excluded by the folder, its stored `cwd` or a marker, is never opened (FR-86). Only a session with no marker and no state is opened for `cwd_of` (§4.1).
- A session pruned on last activity, or whose result is `None`, keeps its state and cursors (§4.3), so on the next pass it is opened only if it gained bytes, and then only for those bytes.
- An agent's `.meta.json` is small and is not a transcript. It is re-read with `export_sessions.load_meta` only when its `(mtime, size)` changes; the stored meta is used otherwise.
- The **accepted blind spots** are row Q-8 (a final line that never gets its `\n`) and row Q-9 (a same-size rewrite in place, and file systems with no `ino`).

### 4.3 State that persists between reads, and how it is stored

`derive` is built to be fed record by record (its docstring; the PBI-004 import contract). Incremental reads give the same result as a full read only if that running state survives from one pass to the next, restarts included. What persists:

| Per | State | Why |
|---|---|---|
| session (`collector_sessions.data`) | `v` (`STATE_VERSION`), `parser` (`export_sessions.PARSER_VERSION`), `window` (seconds), `main` cursor, `state`: the encoded `derive.new_session` dict (today `sid`, `title`, `aiTitle`, `cwd`, `first`, `start`, `last`, `by`, `rejects`, `launched`, `stopped`, `notes`, `sync`, `uses`, `skillCalls`), `result`: the last `derive.session_result` output or `null` | `add_record` folds each record into this state; `agent_row` reads `launched`, `notes`, `sync` and `stopped` from it; `result` is reused for unchanged sessions and supplies the kept rows of agents that could not be read |
| agent (`collector_agents.data`) | its cursor, `state`: the encoded `derive.new_agent` dict (today `by`, `rejects`, `first`, `last`, `text`), `meta` and `metaSig` `[mtime, size]` | `add_agent` folds each record; `agent_row` needs the meta |

What is **not** persisted: row order, `seq`, `from`/`feeds`/`group` links, run counts, project documents, or anything the config decides. All of these are recomputed every pass from the results, as the exporter recomputes them on every run (§4.4).

**The codec** (PBI-004 follow-up; review S-3). The state is not valid JSON as it stands: `skillCalls` is a set, and `by`, `launched`, `stopped` and `sync` can have `None` as a key. Feature PBIs will add fields (the derivation rule), so the codec depends on no field list. `collector.encode(value)` and `collector.decode(text)` are one **generic recursive tagged codec**, used for session state, agent state and `result` alike:
- `None`, `bool`, `int`, `float` and `str` are written as they are;
- a `list` is written as a JSON array of encoded items;
- a `dict` whose keys are all strings, none of them `"$"`, is written as a JSON object of encoded values, **keeping insertion order**;
- **any other dict** (a `None`, `int`, `bool` or other non-string key, or a `"$"` key) is written as `{"$": "map", "v": [[<encoded key>, <encoded value>], …]}`, keeping insertion order. The order of `by` decides the "last response" (`ctx`) and the order of the usage sums;
- **any `set`** is written as `{"$": "set", "v": [<encoded items>]}` and a `frozenset` as `{"$": "frozenset", …}`; a `tuple` as `{"$": "tuple", "v": […]}`;
- any other type raises `TypeError`, which §4.9 treats as state that cannot be encoded.
- The text is `json.dumps(…, ensure_ascii=True)`, so a lone surrogate from a transcript's `\ud800` escape is stored as an escape and never raises at INSERT. NaN is allowed, since the state is private and only ever read by `json.loads`.
- **Round-trip property:** for any value built from those types, at any depth, `decode(encode(s)) == s`, every container keeps its type (set, tuple, list, dict), and every dict keeps its key order.

**Versioning and resets.** That session's state is discarded, and its files re-read from offset 0 once, when any of these holds:
- the stored `v` or `parser` differs from the running code (row Q-11);
- the decoded session state's **key set** differs from `derive.new_session(sid)`'s, or an agent state's key set differs from `derive.new_agent()`'s. This catches a field a feature PBI added or removed, so no stored state can raise `KeyError` in `derive`;
- the stored text cannot be decoded.

These are deliberate resets, not incremental reads. A changed `window` re-derives the rows from the state without reading any file.

**Handoff to feature PBIs that add a field to `derive.new_session` or `derive.new_agent`:** the collector resets the affected states by itself (one full re-read per session, on the first pass after the change). The new field's values must be built from the codec's types above; any other type makes the session unencodable (§4.9). A change of meaning that keeps the key set, such as a field now counted differently, still needs a `PARSER_VERSION` bump.

**Feeding a copy** (review S-2). `add_record` and `add_agent` change the state in place, so a raise part-way through the new lines would leave the records fed so far in the state, and the next pass would feed them again (skill uses and rejects counted twice). So:
- a pass never feeds the cached or stored state itself. It feeds a **working copy**: `copy.deepcopy` of the cached decoded state, or a fresh `decode` of the stored text when there is no cache;
- the working copy, and the new cursor from `read_new`, replace the old ones **only when every new line of that file was fed without a raise**. This applies to the main transcript and to each agent file separately;
- **a raise while feeding an agent file** discards that agent's working copy and new cursor; its stored state and cursor stay, and its row is carried (§4.4 step 2);
- **a main-transcript failure** discards the working copies and new cursors of the main transcript **and of all that session's agents** fed in this pass; the whole session keeps its stored state, cursors and result (§4.4 step 4). A main-transcript failure is a raise while reading or feeding the main transcript, **or any raise after the main feed up to and including encoding** (review R2-4): in `derive.session_result`, in the post-feed exclusion check, in `derive.carried` on a skipped agent's kept row, or in `collector.encode`. Only a raise tied to one agent file in §4.4 step 2 stays that agent's own failure. Because the cursors are discarded too, the next pass sees the same new bytes again and re-derives, rather than reusing a stale result;
- the replaced states are written to `collector_sessions` and `collector_agents` in the pass's transaction, and promoted into the in-memory cache only after `COMMIT`.

The next pass therefore feeds the failed file from its old cursor onto its old state, and every record is counted once.

**The in-memory cache.** A long-running collector keeps the decoded states in memory between passes. The cache is dropped, and reloaded from the database, after a refused or failed pass, or when `data_version` shows another writer (§3.5). A new process always loads from the database, so a restart continues from the stored cursors (AC-CL4).

**Which sessions keep state** (review R2-1). State and cursors are kept for **every discovered, non-excluded session inside the file-time window**, whether or not it enters the results. That includes a session pruned on last activity (§4.1) and a session whose result is `None`. It matches the exporter, whose cache keeps every such session (`export_sessions.py:244, 266-268`). A session's state rows are deleted only when:
- the session drops out of the window **by file time** (§4.1);
- its main transcript vanishes (§4.2), which takes all its agent states with it; a vanished agent file takes only that agent's state;
- it is excluded (§4.1);
- it is reset (above, and §4.2 steps 2 and 3); a reset replaces the state rather than leaving none.

Deleting a session's **records** never deletes its **state** by itself. So under AC-120, an unlinked session whose last activity is 8 days old has its records deleted from the database (reason `age`), while its collector state stays for as long as its file time is inside the window. The next pass opens that file only if it gained bytes. The state goes once the file drops out by file time, and a session resumed after that is read in full once (row Q-10).

### 4.4 Derivation and assembly (FR-87, AC-64)

Per session in discovery order:
1. **Main transcript:** feed each new `(raw, record)` pair into the working copy (§4.3) with `derive.add_record(state, o, raw, warn)`.
2. **Agents:** for each path in `sorted(glob.glob(os.path.join(base, sid, 'subagents', 'agent-*.jsonl')))`, the exporter's order, which fixes the order of `usage.subagents`:
   - feed new records into the agent's working copy with `derive.add_agent`;
   - `sub = derive.agent_summary(astate)`;
   - `row = derive.agent_row(state, aid, meta, sub, age=now - mtime(path), window=st['window'])`.
   - An agent whose read or derivation raises is `skipped`, with a warning; its working copy and new cursor are discarded (§4.3). Its previous row, taken from the stored `result`, is appended **after** the others through `derive.carried(row, window, now)`, as `export_sessions.main` does.
3. **Re-derive or reuse.** The session is re-derived (`derive.session_result(state, subs, rows, skipped)`, or `None` when `state['by']` is empty) when any of these holds:
   - a file of the session gained or lost bytes, appeared, disappeared or was reset;
   - a file's `mtime` changed (review R2-5): the main transcript's or an agent's, seen by the `stat` of §4.2 step 1 against the cursor's `mtime`, with no read. The exporter's signature holds every file's mtime (`export_sessions.py:172-178`), and `agent_row`'s `age` depends on it (`derive.py:478`). For example (AC-64), a quiet agent with no finish, already `killed` because its running window has passed, whose file is touched without new bytes becomes `running` again in the exporter, so it must in the collector too;
   - a meta changed, or the window changed;
   - the stored result has a `running` row;
   - the stored result has a skipped agent.

   Otherwise the stored `result` is reused. Re-deriving touches no file beyond step 1 and step 2's new bytes.
4. **Main transcript fails.** A main-transcript failure (§4.3, "Feeding a copy") is a raise while reading or feeding the main transcript, or any raise after the main feed up to and including encoding: `derive.session_result` in step 3, the post-feed exclusion check of §4.1, `derive.carried` on a skipped agent's kept row, or `collector.encode`. A raise tied to a single agent file in step 2 is not one. On a main-transcript failure the session keeps its stored `result`, with its rows passed through `carried`, and its state and cursors, main and agents, stay as stored: **every** working copy and new cursor of that session is discarded. That matches the exporter's "keeping its last export" path, which keeps the old signature so the session is re-read next run (`export_sessions.py:254-260`). A session with no stored result is left out.

**Assembly across sessions** repeats the tail of `export_sessions.main` line for line:
- `rows = sorted((dict(r, session=sid) for sid, res in results.items() for r in res['rows']), key=lambda r: r['start'] or '')`;
- `derive.place_manual(rows, st['manual'])`;
- per session: `derive.link(mine)`, then `derive.run_doc(r, i, project)` for each row in `seq` order, then `derive.session_doc(result, sid, st, runs, running)`;
- per configured project, in order: `derive.project_doc(p, order, results, counts, running, st['project_of'])`.

That glue is about 15 lines, and `derive` does not hold it. Moving it into `derive` needs `exporters/**`, which this PBI may not edit. So the collector repeats it, and AC-64 plus AC-CL5 catch any drift (row Q-12).

### 4.5 The catalogue read

The collector reuses PBI-017's logic whole:
- **The call:** it runs `export_catalogue.main(config, out_dir=<temporary folder>, now=<now as ISO>)` with stdout captured, then reads `catalogue/index.json` from that folder. `export_catalogue` does its parsing through `derive.frontmatter` and `derive.purpose`.
- **Exit code 2** (a `catalogue` value of the wrong type) fails the pass.
- **No file written** (missing marketplace, no plugins folder, no entries) leaves the stored catalogue record as it is. The catalogue is never deleted, matching AC-C6's "keep the last export".
- **No rewrite for a timestamp.** The record is written only when it differs from the stored one **ignoring `generatedAt`**, as `refresh.digest` judges. This keeps the catalogue row from being rewritten on every pass.

### 4.6 Diff and write

The guard is decided **before any write** (review S-11):
1. **Intended set:** every session, run, project and catalogue record from §4.4 and §4.5.
2. **Stored set:** `db.stored(conn, kind)` for the same kinds.
3. **Deletions:** each stored id not in the intended set, tagged with a reason: `age` or `other` (§4.7).
4. **Guard** (§4.7), computed from the stored set and the deletions of step 3. If it refuses, `ROLLBACK`, report, and stop. Nothing has been written.
5. **Upserts:** each intended record that is new, or whose document differs from the stored one, ignoring `generatedAt`, is passed to `records.to_row`, then `db.upsert`, one savepoint per record (§4.9). A skipped upsert keeps its stored version and adds no deletion, so the guard's decision still holds.
6. **Deletions applied** to the records. Deleting a record deletes no state row: a session pruned on last activity keeps its state and cursors (§4.3, "Which sessions keep state").
7. **State:** write the changed `collector_sessions`, `collector_agents` and `collector_excluded` rows. Delete the state rows of sessions that dropped out by file time, whose main transcript vanished, or that are excluded, and of vanished agent files (§4.3). Delete the stale markers: those that did not match when consulted and were not re-created, and those whose `(dev, ino)` belongs to no main transcript (§4.1).
8. **Last refresh** (§4.8), then `COMMIT`.

### 4.7 The mass-delete guard and age pruning (FR-184, FR-185, AC-119 to AC-121, A-47)

**Age pruning (FR-185, row 12).** A deletion has reason `age` only when the session is linked to no project in the current config and either:
- the pass dropped it for the window, by file time or by last activity (§4.1); or
- its main transcript vanished and its stored session record's `last` is more than `days` before `t0` (review S-5). Claude Code's own clean-up of old transcripts then counts as pruning and cannot trip the guard.

That session's runs share its reason. Age pruning deletes **records**. Whether the session's collector state goes too is decided by §4.3 ("Which sessions keep state"): it goes when the session drops out by file time or its transcript vanished, and stays when the session was pruned on last activity.

Every other deletion has reason `other`:
- an agent file that vanished;
- a main transcript that vanished, of a session whose stored `last` is within the window, missing, or unreadable;
- an exclusion;
- a project removed from the config;
- a session that stopped parsing and has no stored result;
- anything else.

Linked sessions are never pruned (AC-121), because the exporter always exports them.

**The guard**, equivalent to FR-49 and ignoring `age` deletions as A-47's default says (row Q-21). Let `held` be the number of stored `runs` plus `sessions`, and `gone` the `other` deletions among runs and sessions. The pass is **refused** when any of these holds:
- `gone` is non-empty and (the pass found no sessions, or `2 * len(gone) > held`);
- the pass would delete any `project` record;
- the pass would delete the `catalogue` record. That cannot happen through §4.5, but it is guarded anyway, as FR-49 guards it.

**How FR-184's "finds no sessions" clause is read** (review S-6). "Finds no sessions" means that no session enters the results (§4.1). Such a pass is refused only when it also has an `other` deletion. A pass that finds no sessions and whose deletions are **all** by age commits, because A-47's default puts age pruning outside the guard, and FR-184's remedy ("apply none of that pass's deletions") has nothing to hold back once age deletions are exempt. A pass that finds no sessions and deletes nothing also commits. If the owner settles A-47 otherwise, this reading changes with it (row Q-21).

**A refused pass writes nothing:** no record, no deletion, no cursor or state, no marker, no last-refresh. It rolls back and drops the cache, so the next pass meets the same condition again. It prints to stderr what `refresh.py` would print: the counts and ids, what to check (`sessions.projectsRoot`, the transcripts, `projects`, `catalogue`), and `--allow-mass-delete`. This is stricter than FR-184's "apply none of that pass's deletions", and it meets it (row Q-4).

**The override.** `--allow-mass-delete` lifts the guard for **one** pass, and only with `--once` (§5). Age pruning never needs it: after a quiet week, a pass that prunes more than half of the stored records by age alone is committed (A-47's default, row Q-21).

### 4.8 The collector's half of the last-refresh write (FR-103)

- **What it writes.** Every pass that commits writes the record `lastRefresh` (store path `meta/lastRefresh`) as `{"at": clock().isoformat(timespec='seconds'), "writer": "collector"}`, in the same transaction and just before `COMMIT`. `at` is a timezone-aware UTC time, as the PBI-003 shape's strict `datetime` requires.
- **Quiet passes count too.** A pass with no record changes still writes it, so the page's "data as of" means "the collector last confirmed the data" and goes stale only when the collector stops (FR-105; row Q-5).
- **When it does not change.** A refused or failed pass leaves it as it was.

### 4.9 Error handling

**Per record, in the write phase** (the PBI-003 follow-ups). Each upsert runs inside `SAVEPOINT rec` … `RELEASE rec`. When `records.to_row` or the INSERT raises one of these:
- `ValueError`, including an invalid document or a bad id;
- `UnicodeEncodeError`, a subclass of `ValueError` but named explicitly: a lone surrogate reaching SQLite;
- `RecursionError`, from deep nesting;
- `TypeError`;
- `OverflowError`, an int that cannot bind;
- `sqlite3.DataError`;

then:
- the collector runs `ROLLBACK TO rec; RELEASE rec` and warns `collector: <kind> <id> not stored (<ExceptionName>: <message>)`;
- the stored version of that record, if any, is **kept**: it is removed from the deletion set;
- the pass goes on.

This covers derived records that break the shapes, for example a non-string `customTitle`, or a float `sessions.days` that makes `windowDays` a float. They are skipped rather than failing the pass.

**Per session (feeding).** As §4.3 ("Feeding a copy") and §4.4 steps 2 and 4 say, a failing agent costs that agent and a failing main transcript costs that session's update, and neither leaves a partly fed state behind. This matches the exporter, which isolates failure per agent and per session, not per record: `derive.parse_line` already skips lines that are not JSON objects or are nested too deeply.

**State that cannot be encoded.** A session whose state or result cannot be encoded (for example `RecursionError` from a deeply nested usage object, or `TypeError` from a type the codec does not know) is a main-transcript failure (§4.4 step 4): every working copy and new cursor of that session, main and agents, is discarded, and its stored state, cursors and result stay as they were, with a warning.

**Anything else** (a SQLite error outside a record's savepoint, `OSError` on the database, a bug) rolls back the whole pass and reports it; §5 says what happens next. A lock timeout gets its own message (§3.5).

## 5. Running it

```
python local/collector.py [--once] [--allow-mass-delete] [--interval SECONDS] [--config PATH]
```

**The arguments:**
- **`--config`** defaults to the repository's `board.config.json`. The config is re-read at the start of every pass, so a change to `projects` needs no restart. A changed `local.databasePath` is ignored until restart, with a warning.
- **`--once`** runs one pass and exits:
  - **0** after a committed pass, including one with nothing to change;
  - **2** after any refusal: a network path, a bad `local` key, a file at the path that is not a SQLite database (§3.3), WAL unavailable, a newer schema, wrong columns in a records table, a config type error, a missing `projectsRoot`, a missing linked transcript, or the mass-delete guard;
  - **1** after any other failure, including another collector holding the lock (§3.5).
- **`--allow-mass-delete`** is accepted only with `--once`. Without it, the collector exits 2 with a usage message.
- **Loop mode**, without `--once`, is the default for Task Scheduler (PBI-007):
  - startup refusals, meaning the path, database and schema checks of §3, exit 2 straight away;
  - after that, each pass runs every `--interval` seconds (default 60; row Q-17);
  - a failed, refused or locked-out pass is reported on stderr with a timestamp, and the loop goes on;
  - Ctrl+C exits 0.
- **Handoff to PBI-007** (review S-7): in loop mode a refusal or failure shows only on the collector's stderr, which a Task Scheduler process otherwise discards, so the board would stall with no visible reason. PBI-007's scheduled start must capture the collector's stderr (and stdout) to a log file in a known local folder.

**Output.** One stdout line per committed pass, for example `collector: 4 sessions (1 re-derived, 812 bytes read), 23 runs, 2 projects; 3 written, 1 deleted (1 by age) | 0.2s`. Warnings go to stderr, prefixed `collector: `.

**What it never does:** invoke `claude`, contact any network host, or write outside the database and a temporary folder for the catalogue read. PBI-007 inspects that (NFR-17, AC-70). **One qualification** (review R2-8): when the configured database path is on a mapped drive or leads through a link into a share, the network-path guard's own checks (`GetDriveTypeW`, `os.path.realpath`) may make Windows contact that file server before the path is refused (§3.2). The collector itself sends nothing, and it exits 2 straight after.

**Callable in-process** for the tests: `collector.main(argv, config=None, db_path=None, projects_root=None, now=None)` returns the exit code.

## 6. FR-103, and the refresh-plan counts (AC-34, AC-42, AC-44)

- **This PBI does not change those counts.** They belong to `refresh.py`'s plan for the artifact store. The collector's half of FR-103 (§4.8) writes to SQLite and adds nothing to any plan.
- **The counts rise by one when the refresher half of FR-103 is built.** The PRD calls it the refresher's half and gives it to PBI-008, whose areas are `exporters/refresh.py` and `tests/test_refresh.py`. PBI-019's areas include neither, so it **cannot** change those counts or tests.
- **So PBI-019 meets AC-34, AC-42 and AC-44 as unchanged regressions:** on its head commit, the three named tests pass as they stand.
- **The PBI files are corrected (done 2026-09-11; review S-12, R2-7).** `PBI-019.md` and `PBI-008.md` used to quote wording from before PRD revision 3: 11 `set` writes and "one a build session", `test_non_build_session_change_does_not_bump` and `test_deleted_build_run_bumps`. Both now carry PRD revision 3's wording (`PBI-019.md` lines 44 to 48, `PBI-008.md` lines 39 to 41), which is what the current tests say:
  - **AC-34:** 12 `set` writes plus one `update`, in `Plan.test_first_plan_sets_everything_and_the_status`, which asserts `1 + 5 + 2 + 4 + 1`;
  - **AC-42:** in `UpdatedAt.test_unlinked_session_change_does_not_bump`;
  - **AC-44:** in `UpdatedAt.test_deleted_linked_run_bumps`.

  §8 states all three in that wording, and row Q-15 is closed.

## 7. Tests (`local/tests/`, standard library `unittest` only)

**What the tests never touch:** the real `~/.claude`, `out/`, `board.config.json` or database. Everything lives in temporary folders.

**How they import:** they insert `local/` and `exporters/` into `sys.path`, as `test_conformance.py` does. To use the synthetic transcripts of `tests/`, they import `tests/test_export_sessions.py` **as a module**, `import test_export_sessions as tes`, with `tests/` inserted into `sys.path`, and use its record builders (`user`, `reply`, `launch`, `stop`, `notify`, `inline`, `skill_call`, `typed`) and `Tree`. A module attribute is not collected as a test, so none of its test cases run twice. They also reuse `test_conformance.Fixture`.

**A recorded deviation from PBI-003 §5** (review S-13). PBI-003's convention is that `local/tests/` builds its own fixtures and "nothing is imported from `tests/test_*.py`". These tests break it on purpose: AC-64 requires equivalence on "the same synthetic transcripts used by `tests/`", and importing the builders is the only way to use exactly those transcripts rather than a copy that can drift (row Q-14). The import is limited to the builders and `Tree`; no test case of `tests/` is collected or run from `local/tests/`.

**`test_config_local.py`** (`board_config.local`): the default; `~` expanded; a non-object block, a non-string value and an empty value each raise, naming the key; the committed `board.config.json` holds the key.

**`test_db.py`:**
- **WAL:** `journal_mode` is `wal` after `open_db`.
- **Fresh file:** `open_db` on a path that does not exist succeeds, with every records table, the three state tables and `user_version` 1.
- **Network path:** `\\nas\share\board.db`, `//nas/share/board.db`, `\\?\UNC\nas\share\board.db` and the local extended-length `\\?\C:\x\board.db` each raise `NetworkPath` with the configured text, and no folder or file is created; a local path whose `os.path.realpath` (patched) is `\\nas\share\board.db` is refused; a mapped network drive is refused (with the seam patched); a plain local path is accepted.
- **Check order** (R2-8): with `os.path.realpath` and the drive-type seam wrapped by counters, a UNC path is refused with both called 0 times, and a mapped drive is refused with `realpath` called 0 times.
- **Not a database** (R2-6): a file of plain text bytes at the path makes `open_db` raise `Refused` naming the path, `main(['--once', …])` exits 2, and afterwards the file's bytes are unchanged and no `-wal` or `-shm` file exists.
- **Relative paths** resolve against the repository root, not the working folder.
- **Refusals leave a foreign file unmodified:** a file at a newer `user_version`, and a file holding `statuses(x)` in rollback-journal mode, are each refused (naming the version, or `statuses`), and afterwards the file's bytes, its `journal_mode`, its table list and its `user_version` are all unchanged.
- **Healing:** a missing records table is added, through `create_schema`.
- **State tables:** with rows in all three state tables, a `collector_excluded` table with the wrong columns makes `open_db` drop and recreate **all three** (R2-8), with a warning naming it; `open_db` succeeds and the three tables are empty, so the next pass reads every transcript from offset 0; the re-check refuses when a records table is wrong after step 6 (with `create_schema` patched).
- **Write helpers:** `upsert`, then `stored`, round-trips each kind; a lone surrogate inside a savepoint raises `UnicodeEncodeError` and leaves the transaction usable.
- **`Changes.poll`:** `False` first; `True` after another connection commits; `False` after a rolled-back `BEGIN IMMEDIATE`.

**`test_collector.py`:**
- **AC-63.** Read, append one line, then pass again with `collector._open` wrapped by a counter. For that file: one `seek` to the previous size, and bytes returned equal to the appended line's bytes. An unchanged file is not opened at all.
- **Partial line.** A line written without `\n` is not consumed, and the offset stays put. After it is completed, the record is folded exactly once: its skill use is counted once.
- **Truncation and replacement.** A truncated file (`size < offset`), and a file swapped in with `os.replace`, are each re-read from 0, and the result equals a fresh read.
- **New and deleted files.** A new agent file adds a run; a deleted agent file removes its run and state row; a deleted main transcript removes the session.
- **Restart.** A second process-equivalent (a fresh call with no cache) continues from the stored cursors, reading only the appended bytes, and the result equals the exporter's.
- **Failed feed, counted once** (S-2). With the cache warm from a first pass, append lines holding skill uses, then patch `derive.add_record` to raise on the k-th new line; the pass keeps the session's stored result, state and cursor. Remove the patch and pass again: each skill use and reject of the appended lines is counted once, and the records equal the exporter's on the final files. The same with `derive.add_agent` raising on an agent file's k-th new line: that agent's state and cursor stay, and the next pass counts its records once.
- **Failure after the main feed** (R2-4). With new bytes in the main transcript and in an agent file, patch in turn `derive.session_result`, the post-feed exclusion check and `collector.encode` to raise once. After each such pass, the session's stored result, its main and agent states and all its cursors are unchanged. The next pass, without the raise, reads the same new bytes again (counted through `collector._open`), counts each record once, and the records equal the exporter's.
- **Codec.** Round trips on states holding a `None` key in `by`, `launched`, `stopped` and `sync`, a `None` in `skillCalls`, and a lone surrogate; and on a generic value with a set, a frozenset and a tuple nested inside lists and dicts, a dict with `int` and `bool` keys, and a dict with a `"$"` key. Each is equal, with the same container types and key order. An unknown type raises `TypeError`.
- **Key-set reset.** A stored session state with a key missing, or an extra key, compared with `derive.new_session(sid)` (and the same for an agent against `derive.new_agent()`), is discarded and re-read from 0, with no `KeyError`, and the result equals a fresh read.
- **Running rows.** A session with a running row is re-derived on a later pass with no new bytes, and becomes `killed` / `no result` once the window passes (the `now` moved).
- **Touched file** (R2-5). An agent with no finish, `killed` because its running window has passed, has its file's mtime set to `now` with `os.utime` and no new bytes. The next pass re-derives the session, the run is `running` as in the exporter's output on the same files and `now`, and `collector._open` is called 0 times.
- **Guard:**
  - more than half deleted for reason `other` is refused, writing nothing: records, state, markers, last-refresh and `data_version` all unchanged;
  - the guard is decided before any write: with `db.upsert` wrapped by a counter, a refused pass calls it zero times;
  - a pass that finds no sessions and has an `other` deletion is refused;
  - a pass that finds no sessions and whose deletions are all by age commits (S-6);
  - deleting a project record (the project removed from the config) is refused;
  - `--allow-mass-delete --once` applies these deletions;
  - a quiet-week scenario, where more than half the records are pruned by age, commits (A-47).
- **Pruning.** AC-120 and AC-121 as written.
  - **Pruned on last activity keeps state** (R2-1): an unlinked session whose file time is inside the window but whose records' timestamps are more than `days` old has no records after a pass, while its `collector_sessions` and `collector_agents` rows remain. A second pass, with `collector._open` and `cwd_of` wrapped by counters, opens its files 0 times and still stores no records for it. The same for a session whose result is `None` (no answered response).
  - **Pruned by file time loses state:** once that file's mtime is set more than `days` in the past, the next pass deletes its state rows.
  - A vanished main transcript of an unlinked session whose stored `last` is past the window is deleted for reason `age`, so removing more than half the transcripts this way commits; the same with `last` inside the window is reason `other` (S-5).
- **Exclusion.** An excluded session stores no state and no records; a session that becomes excluded is purged. With a marker stored, a second pass does not open the excluded file (counted through `collector._open` and a patched `cwd_of`); the marker row holds only `dev`, `ino`, `size` and `rule`; changing `exclude`, replacing the file or truncating it makes the next pass decide through `cwd_of` again; a file with no `cwd` line gets no marker. **Stale marker** (R2-2): truncate an excluded file, rewrite it with a `cwd` the patterns do not exclude, pass, then append until it is larger than the old marker's `size` and pass again: the session is still included, its records equal the exporter's, and no `collector_excluded` row holds its `(dev, ino)`.
- **Lock.** With another connection holding `BEGIN IMMEDIATE` and the busy timeout patched short, `main(['--once', …])` exits 1 and stderr holds "another collector holds the database lock".
- **Last refresh.** A committed pass writes `at` from the injected clock and `writer: collector`; a refused pass and a failed pass (missing `projectsRoot`) leave it unchanged.
- **Per-record errors.** With `records.to_row` patched to raise each of `ValueError`, `UnicodeEncodeError`, `RecursionError` and `TypeError` for one run id, that run is not stored, a warning names it, its previous version is kept, and every other record is written. A real lone-surrogate session title takes the same path end to end.
- **Catalogue.** It equals the exporter's document ignoring `generatedAt`; a missing marketplace keeps the stored record; a pass with only a new `generatedAt` does not rewrite the catalogue row.
- **Command line.**
  - `--once` exit codes 0, 1 and 2 (patching `run_pass` to raise for 1);
  - `--allow-mass-delete` without `--once` exits 2;
  - the loop, with `time.sleep` patched and two iterations, carries on after a failed pass;
  - AC-115 through `main([...])` with a UNC path: exit 2, and the path on stderr.
- **No answers.** After every scenario, `sqlite_master` holds no `answers` table, and the collector writes only the five kinds of §2.

**`test_collector_equivalence.py`** (AC-64, and AC-CL5 for incremental reading):
- **One-shot.** On `test_conformance.Fixture` (running, killed, stopped, lane `other`, a `runs.manual` row, skill uses with and without a time, `showFirstPrompt` on, a project with no sessions, a linked session with no readable time, linked and unlinked sessions) and on `tes.Tree` scenarios (a finish by notification, an inline foreground finish, a rate-limit kill, a stop then a completed finish, a `Skill` call and a typed `/<plugin>:<skill>` command, malformed and too-deeply-nested lines, token counts that are not numbers):
  - run `export_sessions.main(cfg, out, root, now)`;
  - run `collector.run_pass(conn, cfg, projects_root=root, now=now)` with the same `now`;
  - for `session`, `run` and `project`, the `{id: doc}` maps from `out/` and from the database (`from_row`) are equal.
- **Incremental.** The same fixtures written a few lines at a time, split at every line boundary of the main transcripts and the agent transcripts, with a pass after each step. After the final write, the database equals the exporter's one run on the final files.
- **After a restart.** The incremental case again, with a new connection and no cache halfway through.
- **With exclusion.** A fixture with `sessions.exclude` matching one session by `cwd`: the one-shot and incremental cases equal the exporter's output with markers in use.

## 8. Acceptance criteria

**From the PRD (revision 3 wording).** `PBI-019.md` carries all nine in this wording (corrected 2026-09-11; row Q-15, done).
- [ ] **AC-34** When the refresh script plans a fresh `out/` holding one project (status document `meta/status`) with its five tabs, two sessions (one linked, one not) and four runs, it shall plan 12 `set` writes and one `update` of `meta/status`. **PBI-019 leaves this unchanged:** `Plan.test_first_plan_sets_everything_and_the_status` passes as it stands. The count change for FR-103 is PBI-008's (§6).
- [ ] **AC-42** When only an unlinked session's title changes, the refresh script shall plan exactly one `set`, of that session, and no status update. Unchanged by this PBI (`UpdatedAt.test_unlinked_session_change_does_not_bump`).
- [ ] **AC-44** When a linked session's run is deleted, the refresh script shall plan that `delete` plus an `update` of that project's status document. Unchanged by this PBI (`UpdatedAt.test_deleted_linked_run_bumps`).
- [ ] **AC-63** When one line is appended to a transcript the collector has already read, the collector shall read from that file only the bytes of the appended line. *(FR-86; §4.2; counted through `collector._open`.)*
- [ ] **AC-64** When the collector and the session exporter process the same synthetic transcripts used by `tests/`, the collector shall produce session, run and project records equal to the exporter's documents, ignoring `generatedAt`. *(FR-87; §7 one-shot case.)*
- [ ] **AC-115** When the collector's database path is configured as `\\nas\share\board.db`, the collector shall refuse to start and print that path. *(FR-180, FR-96; exit 2; nothing created.)*
- [ ] **AC-119** When a collector pass would delete more than half of the stored runs and sessions other than by age pruning, the collector shall apply none of that pass's deletions. *(FR-184; this spec also writes nothing else, §4.7.)*
- [ ] **AC-120** When an unlinked session's last activity is 8 days old, the collector shall delete that session's records from the local database. *(FR-185. This criterion is about records. The session's collector state is not a record, and it stays while the file's time is inside the window (§4.3; AC-CL15).)*
- [ ] **AC-121** When a linked session's last activity is 30 days old, the collector shall keep that session's records in the local database. *(FR-185.)*

**Added by this spec.** Each is testable and covered in §7.
- [ ] **AC-CL1** *(FR-88, C-21; §3.3.)* `db.open_db` on a path that does not exist returns a connection in WAL mode with the PBI-003 schema at `user_version` 1 and the three `collector_*` tables. It refuses, with exit 2 and a message naming the cause, a newer `user_version`, a records table whose `PRAGMA table_info` columns differ from the expected ones (for example `statuses(x)`), a file that is not a SQLite database (`sqlite3.DatabaseError` in steps 3 to 8 becomes `db.Refused`), and a journal mode other than `wal`. A file refused for its version or its columns is left unmodified: the same bytes, journal mode, tables and `user_version` as before. A file that fails the step-4 read (not a database) keeps the same bytes, with no `-wal` or `-shm` file beside it (review R3-3: a file with a valid header that fails later, in steps 5 to 8, may already be in WAL mode). A wrong column set in any `collector_*` table drops and recreates all three.
- [ ] **AC-CL2** `board_config.local(cfg)` returns `databasePath`, defaulting to `out/local/board.db` with `~` expanded. It raises `ValueError`, naming `local` or `local.databasePath`, for a non-object block or a non-string or empty value. The collector resolves a relative path against the repository root, and `board.config.json` holds the key.
- [ ] **AC-CL3** *(FR-86.)*
  - a trailing line without `\n` is not consumed until completed, and is then folded exactly once;
  - a truncated or replaced file is re-read from offset 0 and gives the result of a fresh read;
  - an unchanged file is not opened;
  - a file whose mtime changed with no new bytes makes its session re-derive without being opened, and the result equals the exporter's (§4.4 step 3);
  - a new agent file adds its run, and a deleted one removes its run and state.
- [ ] **AC-CL4** After a restart (a new connection and no in-memory cache), a pass that follows one appended line reads only that line's bytes, and the records equal the exporter's. The generic codec round-trips `None` and other non-string keys, a `"$"` key, sets, frozensets and tuples at any depth, a lone surrogate and key order, keeping every container's type. A stored state whose key set differs from `derive.new_session(sid)`'s or `derive.new_agent()`'s is re-read from offset 0, and the result equals a fresh read.
- [ ] **AC-CL5** *(FR-87.)* When the AC-64 fixtures are written a few lines at a time, with a pass after each step, the final session, run and project records equal the exporter's one run on the final files.
- [ ] **AC-CL6** The catalogue record equals `export_catalogue.py`'s document, ignoring `generatedAt`. A missing marketplace keeps the stored record. A pass in which only `generatedAt` would change does not rewrite it.
- [ ] **AC-CL7** *(FR-184, FR-185, FR-49 equivalence, A-47.)* A pass is refused when it would delete a project record, or when it finds no sessions and has a non-age deletion; the refusal is decided before any record is upserted. A refused pass leaves the records, state, cursors, markers, last-refresh and `PRAGMA data_version` unchanged. `--allow-mass-delete --once` applies the deletions. A pass that removes more than half the records by age pruning alone commits, and so does a pass that finds no sessions and whose deletions are all by age. A vanished main transcript of an unlinked session whose stored `last` is more than `days` old is deleted for reason `age`.
- [ ] **AC-CL8** *(FR-103, collector half.)* Every committed pass writes the `lastRefresh` record with `writer: "collector"` and `at` equal to the injected clock's time (timezone-aware; valid under `records.validate`). Refused and failed passes leave it unchanged.
- [ ] **AC-CL9** `db.Changes.poll()` on a second connection returns `True` after a committed pass and `False` after a refused one.
- [ ] **AC-CL10** When storing one record raises `ValueError`, `UnicodeEncodeError`, `RecursionError` or `TypeError`, that record is skipped, with a warning naming its kind and id, its stored version is kept, and every other record of the pass is written.
- [ ] **AC-CL11** A session matched by `sessions.exclude` never has a state row or a record in the database, and a session that becomes excluded has both removed. The only trace of an excluded session is a `collector_excluded` row holding `dev`, `ino`, `size` and `rule` and nothing else; while it matches, the file is not opened; after the `exclude` list changes, or the file is replaced or truncated, the pass decides again through `cwd_of`. Output with exclusion equals the exporter's.
- [ ] **AC-CL12** `--once` exits 0, 1 or 2 as §5 says, and `--allow-mass-delete` without `--once` exits 2. The loop continues after a failed pass. While another connection holds the write lock, `--once` exits 1 and prints "another collector holds the database lock". The database holds no `answers` table, and the collector writes only `session`, `run`, `project`, `catalogue` and `lastRefresh` records (C-16).
- [ ] **AC-CL13** *(FR-86, FR-87; §4.3 "Feeding a copy".)* When feeding a main transcript or an agent file raises on its k-th new line with the cache warm, that file's stored state and cursor are unchanged after the pass, and the next pass, without the raise, counts every record of the appended lines (skill uses and rejects included) exactly once; the records then equal the exporter's on the final files. The same holds when `derive.session_result`, the post-feed exclusion check or `collector.encode` raises after the main feed: every working copy and new cursor of that session, main and agents, is discarded, its stored state, cursors and result are unchanged, and the next pass reads the same new bytes again (§4.4 step 4).
- [ ] **AC-CL14** *(FR-96, FR-180; §3.2.)* `db.network_path` is true for `\\nas\share\board.db`, `//nas/share/board.db`, `\\?\UNC\nas\share\board.db`, the local extended-length `\\?\C:\x\board.db`, a path whose `os.path.realpath` starts with `\\`, and a mapped network drive; `open_db` refuses each before creating any folder or file. A plain local path is accepted. The checks stop at the first hit: a path refused by its string form never reaches `GetDriveTypeW` or `os.path.realpath`, and a mapped drive never reaches `os.path.realpath`.
- [ ] **AC-CL15** *(FR-86, FR-185; §4.3 "Which sessions keep state".)* An unlinked session whose file time is inside the window but whose last activity is more than `days` old has its records deleted and keeps its state rows and cursors; on the next pass its files are opened 0 times. The same holds for a session whose result is `None`. Its state rows are deleted once its file time leaves the window. An exclusion marker that is consulted and does not match is deleted, so a file truncated and rewritten with a `cwd` that is not excluded stays included after it grows past the old size. `collector_excluded.dev` and `.ino` are `TEXT`, so an `st_ino` above 2^63 - 1 is stored without error.

**Close-out** (replacing the PBI file's line):
- [ ] All three configured suites are green on the head commit: `python -m unittest discover -s tests`, `node tests/page.test.mjs` and `python -m unittest discover -s local/tests`. The code-review gate has passed (`review-agents:code-reviewer` GO).

**That is 25 criteria in all:** 9 from the PRD, 15 added, and the close-out.

## 9. Assumptions and open questions

**Owner** marks a row that needs the owner. The other rows are settled at the spec gate, or can be.

| # | Question | Default chosen | Impact if wrong | Needs |
|---|---|---|---|---|
| Q-1 | Where does the derivation state live? PBI-003 §4 says any schema change after version 1 needs a PBI with `local/schema*` | Three `collector_*` tables in the same file, owned by `local/db.py`, outside `records.TABLES` and `user_version`, and ignored by the server. The same file is needed for atomic commits (WAL makes `ATTACH` non-atomic). **Settled by the spec-gate reviewer (round 1): not a PBI-003 schema change**, because PBI-003 §4 governs the records schema and these tables sit outside `records.TABLES`, `schema.py` and `user_version`. PBI-005 must ignore `collector_*`. A column mismatch in any of them drops and recreates all three (§3.3 step 7) | — | Settled (spec-gate reviewer) |
| Q-2 | Who writes `tab` (`projectTabs`) and `status` records into the local database? FR-100 defines them as records "used by the collector", the parent aims at "no Claude session needed", and no PBI writes them locally. `meta/status`'s title, message and metrics are written by hand in the artifact store | **Not PBI-019.** The reviewer confirms a genuine plan gap and recommends a **new PBI through pbi-intake**, not a widening of PBI-019, because: `export_board` calls `gh`, which breaks §5's "never contacts any network host"; and its `carriedSince` logic needs a persistent `out/` folder, which the collector does not keep. Until then the local page shows project tabs as "not exported yet" and no status | The local app is incomplete for the Spec, Assumptions, Decisions, Backlog and GitHub tabs, and for status tiles; this blocks PBI-007's end-to-end claim and retiring v1, not PBI-019 | **CONFIRMED.** The owner approved the new PBI on 2026-09-11, verbatim: "Q-2: yes." Landed by intake as **PBI-025** (Proposed, depends on PBI-019) |
| Q-3 | FR-185 says the collector "shall delete … **only**" age-pruned unlinked sessions, but equivalence (AC-64) and FR-184 need other deletions (a vanished transcript, an exclusion, a removed project) | Read FR-185 as the retention rule. The database mirrors the exporter's set, and every other deletion goes through the guard (§4.7). The reviewer agrees: the literal reading contradicts the `exclude` privacy rule and AC-64. **Recommended PRD amendment:** FR-185 to say the collector "prunes by age only unlinked sessions …; other deletions go through FR-184" | If the owner meant literally "only", vanished and excluded sessions stay stored for good, AC-64 fails after any deletion, and exclusion cannot remove data | **CONFIRMED.** Confirmed by the owner 2026-09-11, verbatim: "Q-3 and A-47: yes." The PRD's FR-185 is amended to this reading |
| Q-4 | Does the guard hold back only the deletions (FR-184) or the whole pass? | The whole pass writes nothing, as FR-49 does and as the brief asks ("refuse, write nothing"). FR-184 is met | Upserts wait until the override, so the board stalls, as v1 does | — |
| Q-5 | Is last-refresh written on a pass that changes no record? | Yes, on every committed pass | If "only when records change" is wanted, the page reads "stale" in quiet spells while the collector is healthy | — |
| Q-6 | Default database path | `out/local/board.db` (git-ignored through `out/`; untouched by the v1 exporters and `refresh.py`) | A retirement of `out/` with v1 would need a new default; a low-cost config change | — |
| Q-7 | Key name and shape | A `local` block, `local.databasePath`; PBI-005 adds `local.port` | A rename touches two PBIs' small config changes | — |
| Q-8 | A final line that never gets its `\n` | Held back until one arrives | The exporter would parse a complete, unterminated last line and the collector would not. Claude Code terminates every line | — |
| Q-9 | How replacement is detected without reading extra bytes (AC-63 forbids reading more) | `(st_dev, st_ino)` change, or `size < offset`. The exclusion markers use the same test (§4.1) | A rewrite in place at the same or a larger size, or a file system reporting `ino` 0, goes unnoticed until the next reset; with `ino` 0 no marker is stored, so excluded files are checked through `cwd_of` every pass, as the exporter does. A marker that is consulted and does not match is deleted (§4.1, R2-2). One case remains: on a file system that reuses an `ino` at once (NTFS does not, because its file ID carries a sequence number), an excluded file deleted and replaced between two passes by a new main transcript with the same `(dev, ino)`, at least the old size and the same `rule` is treated as excluded until it is truncated or the `exclude` list changes. Likewise (review R3-2, deferred): an excluded file truncated and grown back past the marker's `size` between two passes still matches its old marker and stays excluded, where the exporter would include it. That fails safe for privacy, and Claude Code only ever appends to transcripts | — |
| Q-10 | State of age-pruned sessions | Kept while the transcript's file time is inside the window, including a session pruned on last activity or whose result is `None` (review R2-1, §4.3), as the exporter's cache keeps it. Removed when the session drops out by file time, its transcript vanishes, it is excluded, or it is reset | A session resumed after its file time left the window is read in full once. While kept, a pruned session's state costs its rows in the database, and no reads | — |
| Q-11 | A parser or state-format change | Stored `parser` or `v` differs, or the state's key set differs from `derive`'s (§4.3): that session's state is discarded and re-read from 0 once | One slow pass after a `derive` change | — |
| Q-12 | The assembly glue (row sort, `place_manual`, `link`, `seq`, counts, `project_doc`) is in `export_sessions.main`, not in `derive` | The collector repeats those ~15 lines; AC-64 and AC-CL5 catch drift; the order `glob` returns is kept for ties. **Follow-up:** move the glue into `derive` in a PBI with `exporters/**` | A change to the exporter's tail without the collector's shows up only as an AC-64 failure | — |
| Q-13 | The catalogue read | `export_catalogue.main` into a temporary folder on every pass | A few dozen small file reads a minute. If that is too much, read it every Nth pass | — |
| Q-14 | Where the AC-64 transcripts come from | `tests/test_export_sessions.py`'s builders, imported as a module, plus `test_conformance.Fixture`. A recorded deviation from PBI-003 §5 (§7) | A later edit to those builders changes the fixture. That is intended, and it is the derivation rule's extension point | — |
| Q-15 | `PBI-019.md` quotes AC-34, AC-42 and AC-44 from before PRD revision 3 (11 sets; test names that no longer exist), and omits AC-115 and AC-119 to AC-121. `PBI-008.md` (lines 37 to 39) has the same out-of-date wording | This spec restates them to revision 3 (§6, §8). The orchestrator corrects **both** `PBI-019.md` and `PBI-008.md`. **Done 2026-09-11:** both files now carry revision 3's wording, and `PBI-019.md` holds AC-115 and AC-119 to AC-121 | — | Done (orchestrator) |
| Q-16 | Mapped network drives (FR-96 only names `\\` and `//`) | Refuse a drive letter whose `GetDriveTypeW` is `DRIVE_REMOTE` | A false refusal only if Windows misreports; the owner can point the path at a local disk | — |
| Q-17 | Loop interval | 60 s, as a command-line flag. The parent allows one config key | NFR-18's 10 minutes has plenty of margin; a config key would need another PBI's area | — |
| Q-18 | Derived records that break the shapes (for example a float `sessions.days`) | Skipped per record with a warning (§4.9), not fatal | The local board shows fewer sessions than the artifact until the config is fixed | — |
| Q-19 | Write volume | One state row per session and one per agent, rewritten only when that file changed | A very long, active main transcript rewrites a large row every pass. If measured to be a problem, split `by` out in a later PBI | — |
| Q-20 | Transcript lines that `derive` itself cannot handle | The session keeps its last result, state and cursors (§4.3, §4.4 step 4), as the exporter does; it is not isolated per line | A poison record stalls that session's updates until fixed, as in v1 | — |
| Q-21 | PRD A-47 (how the mass-delete guard and age pruning interact) is still an open PRD row | Build to **A-47's own default**: FR-49's thresholds apply to deletions other than age pruning, and age pruning of unlinked sessions is not blocked by the guard. So a pass whose deletions are all by age commits, even one that finds no sessions (§4.7) | Pruning that the owner would have blocked goes through. It can be undone: widening `sessions.days` re-reads the transcripts and restores the records | **CONFIRMED.** Confirmed by the owner 2026-09-11, verbatim: "Q-3 and A-47: yes." A-47's default stands |

## 10. Out of scope

- **The local server** (PBI-005): the page, the snapshot, SSE live push, Host and Origin checks, its own FR-96 check (AC-67, which reuses `db.network_path`), polling `db.Changes`, and ignoring the `collector_*` tables.
- **The page's data adapters** (PBI-006).
- **Task Scheduler start at log-on**, capturing the collector's stderr to a log file (§5 handoff), and the end-to-end checks NFR-17, NFR-18, NFR-21, AC-65, AC-68 and AC-70 (PBI-007). This PBI only makes the loop mode suitable for it.
- **The refresher's half of FR-103**, and any change to `refresh.py`, `tests/test_refresh.py` or the AC-34, AC-42 and AC-44 counts (PBI-008).
- **Writing `tab` and `status` records locally** (row Q-2; a new PBI through pbi-intake).
- **The Unraid upload and ingest** (FR-89, FR-181, FR-182; the former PBI-016, now a future iteration).
- **Answers, of any kind** (D-22, C-16).
- **Editing** `exporters/**` other than `board_config.py`, `local/records*`, `local/schema*`, `site/**` or `tests/**`.
- **Filling `run.end`** beyond what `derive.agent_row` already sets (PBI-020).

## 11. Spec-gate record

| Round | Revision reviewed | Verdict | Review note |
|---|---|---|---|
| 1 | 1 | CHANGES-REQUIRED | `docs/backlog/reviews/PBI-019/spec-review-r1.md` |
| 2 | 2 | CHANGES-REQUIRED | `docs/backlog/reviews/PBI-019/spec-review-r2.md` |
| 3 | 3 | pending | — |

Round 1 (2026-09-11): CHANGES-REQUIRED, 3 Medium, 7 Low, 3 Info; all applied in revision 2 — see docs/backlog/reviews/PBI-019/spec-review-r1.md

- **S-1 (Medium):** §3.3 reordered: a read-only version and `table_info` pre-check of existing tables first (missing tables fine), then WAL, `create_schema`, the state tables and a full re-check. AC-CL1 now requires that a fresh file opens and a refused foreign file is left unmodified.
- **S-2 (Medium):** §4.3 "Feeding a copy": main and agent files are fed on a deep copy or fresh decode, swapped in with their cursors only on success; a main failure keeps the whole session as stored. New AC-CL13 and its test (raise on line k with a warm cache, next pass counts once).
- **S-3 (Medium):** §4.3 codec replaced by a generic recursive tagged codec (sets, frozensets, tuples, any dict with non-string or `"$"` keys); reset when the decoded key set differs from `derive.new_session(sid)` / `derive.new_agent()`; handoff for feature PBIs added. AC-CL4 updated.
- **S-4 (Low):** chose the content-free marker (`collector_excluded`, keyed by `(dev, ino)`, with size and a digest of `exclude`), which keeps equivalence (§4.1); no marker when `cwd_of` finds no `cwd` or `ino` is 0. AC-CL11 updated.
- **S-5 (Low):** a vanished main transcript of an unlinked session whose stored `last` is past the window is an `age` deletion (§4.2, §4.7). AC-CL7 updated.
- **S-6 (Low):** owner row Q-21 added (A-47 open, its own default used); §4.7 states how "finds no sessions" is read; test and AC-CL7 cover "no sessions, only age deletions → commit".
- **S-7 (Low):** §5 and §10 hand off to PBI-007 to capture the collector's stderr to a log file.
- **S-8 (Low):** §3.5 documents the lock scope and adds the "another collector holds the database lock" message (exit 1 with `--once`). AC-CL12 updated.
- **S-9 (Low):** §3.2 names `os.path.abspath` and `os.path.realpath`, and records that `\\?\` paths are refused on purpose (fails safe, FR-180 literal). New AC-CL14.
- **S-10 (Low):** a `collector_*` column mismatch drops and recreates the table with a warning (full re-read) instead of refusing (§3.3 step 7, §3.4).
- **S-11 (Info):** §4.6 reordered so the guard is decided before any write; tested with a counted `db.upsert`.
- **S-12 (Info):** §6 and row Q-15 now cover `PBI-008.md` as well as `PBI-019.md`.
- **S-13 (Info, standards):** §7 records the deviation from PBI-003 §5 and its justification (AC-64 names the synthetic transcripts used by `tests/`).

Round 2 (2026-09-11): CHANGES-REQUIRED, 1 Medium, 5 Low, 2 Info; all applied in revision 3 — see docs/backlog/reviews/PBI-019/spec-review-r2.md

- **R2-1 (Medium):** §4.3 "Age-pruned sessions lose their state" replaced by "Which sessions keep state": every discovered, non-excluded session inside the file-time window keeps its state and cursors, including one pruned on last activity or with a `None` result; state goes only on a file-time drop-out, a vanished transcript, an exclusion or a reset. §4.1, §4.2, §4.6 steps 6 and 7, §4.7 and Q-10 match; AC-120 is marked as about records only. New AC-CL15 and tests (next pass opens the pruned file 0 times).
- **R2-2 (Low):** a marker that is consulted and does not match is deleted, and step 4 re-creates it if the file is still excluded (§4.1, §4.6 step 7). Test: truncate, rewrite with an included `cwd`, grow past the old size, still included (AC-CL15). Q-9 names the one remaining inode-reuse case.
- **R2-3 (Low):** `collector_excluded.dev` and `ino` are `TEXT` (decimal digits), so no integer overflow is possible (§3.4 DDL; AC-CL15).
- **R2-4 (Low):** any raise after the main feed up to and including encoding (`session_result`, the post-feed exclusion check, `carried`, `encode`) is a main-transcript failure that discards every working copy and cursor of the session (§4.3, §4.4 step 4, §4.9). AC-CL13 extended, with a test.
- **R2-5 (Low):** "a file's mtime changed" (a `stat` only) added to the re-derive triggers, with the touched quiet agent example (§4.4 step 3; cursor `mtime` updated in §4.2 step 4). AC-CL3 extended, with a test.
- **R2-6 (Low):** `sqlite3.DatabaseError` in opening steps 3 to 8 becomes `db.Refused` (exit 2), except "database is locked"; a non-database file is refused unmodified (§3.3, §3.5, §5). AC-CL1 extended, with a test.
- **R2-7 (Info):** §6, §8's intro and Q-15 now say the PBI files are corrected (done 2026-09-11).
- **R2-8 (Info):** §3.2 checks string forms and drive type first and stops at the first hit, says plainly that `GetDriveTypeW` and `realpath` may contact the file server, and makes "opens no file" precise; §5's "never contacts any network host" is qualified; §3.3 step 7 drops all three state tables together. AC-CL1 and AC-CL14 extended, with tests.

Round 3 (2026-09-11), the final round: APPROVE-WITH-NOTES, 1 Low, 3 Info; every note disposed — see docs/backlog/reviews/PBI-019/spec-review-r3.md. **The spec gate is passed with revision 3.**

- **R3-1 (Low), apply in build:** a §7 test patches `os.stat` to return `st_ino = 2**64 - 1` and checks that the marker is stored and matches on the next pass (AC-CL15).
- **R3-2 (Info), deferred with rationale:** the truncate-and-grow-back marker case is named in Q-9. It fails safe for privacy, and Claude Code only appends to transcripts.
- **R3-3 (Info), applied:** AC-CL1 now says "a file that fails the step-4 read" keeps the same bytes.
- **R3-4 (Info), accepted:** a refused pass keeps vanished or newly excluded sessions until `--allow-mass-delete`, as the whole-pass refusal (Q-4) and v1's `refresh.py` do. No change.
