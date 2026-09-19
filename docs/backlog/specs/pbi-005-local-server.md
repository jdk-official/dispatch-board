---
id: SPEC-PBI-005
title: "Local server: the page, the data snapshot, live push, 127.0.0.1 binding, Host and Origin checks, and the network-path guard"
pbi: PBI-005
parent: docs/backlog/specs/dispatch-board.md (revision 5, approved)
revision: 2
status: approved at spec-gate round 2 (APPROVE-WITH-NOTES, both notes applied); built and merged (PBI-005, PR #19, squash 3e3ec44, 2026-09-12)
date: 2026-09-12
reviews: docs/backlog/reviews/PBI-005/spec-review-r1.md (round 1, revision 1, CHANGES-REQUIRED); docs/backlog/reviews/PBI-005/spec-review-r2.md (round 2, revision 2, APPROVE-WITH-NOTES)
closeout_note: "Front matter corrected 2026-09-12. It read 'awaiting round 2' after the spec had passed and the PBI had merged — stale status carried past close-out. Raised as N-5 at PBI-025's spec-gate round 2."
---

# PBI-005: Local server (per-PBI spec)

## 1. Intent

The local server is the read side of the local-first app. The collector (PBI-019) writes the SQLite
database; this server reads it, serves the page and a data snapshot over HTTP on 127.0.0.1, and pushes
every database change to the pages that are open. It writes no record, no table and no schema, and it
creates no file of its own; the one mark it can leave on disk is the `-wal` and `-shm` pair SQLite
itself creates beside a WAL database when it opens one and no writer is connected (§5.1).

**Sources:**
- PRD revision 3: FR-92, FR-93, FR-94, FR-96, FR-180; NFR-17 to NFR-21; C-8, C-14, C-16, C-18, C-21;
  AC-66 to AC-70, AC-73; A-29, A-35;
- parent spec (revision 5, approved): the Key decisions, the local-first order (PBI-003 → PBI-019 →
  PBI-005 → PBI-006 → PBI-007), PBI-005's areas, and rows 7, 8 and 24;
- ADR-0001 (accepted);
- what is already built and must be reused: `local/records.py`, `local/schema.py`, `local/db.py` and
  `local/collector.py` (PBI-019, merged), and `exporters/board_config.py`;
- the PBI-019 spec (`pbi-019-collector.md`, revision 3) for the handoffs it names: ignore the
  `collector_*` tables (§3.4), poll `PRAGMA data_version` outside any open read transaction (§3.6),
  and reuse `db.network_path` for FR-96 (§3.2).

**Three rules govern the design:**
- **The server never writes the database's content.** Not a record, not a state table, not a schema.
  The collector owns every write. This is what makes the concurrency story trivial (§5) and it is
  asserted, not assumed — AC-SV6, scoped to the database file's own bytes, mtime and `data_version`,
  because SQLite's WAL sidecar files are outside our control (§5.1).
- **Reuse, never re-implement.** The server imports `records` (shapes, `TABLES`, `store_path`,
  `from_row`), `schema` (`SCHEMA_VERSION` only), `db` (`stored`, `network_path`, `resolve`, `Changes`) and
  `board_config` (`local`). Its one piece of new plumbing is a read-only connection, and §2 says why
  it cannot live in `db.py`.
- **Fail closed at the edge.** A request that is not plainly from a browser on this machine gets a
  one-line plain-text refusal and no board data (§4).

## 2. Scope and module layout

**Files it creates or changes (all within its allowed areas):**

| File | Contents |
|---|---|
| `local/server.py` | Everything: the config read, the network-path guard, the read-only opener, the snapshot state, the event hub, the request handler, the page wrapper and the command line |
| `local/tests/test_server.py` | Routes, hardening, the page wrapper, snapshot conformance, the command line (§9) |
| `local/tests/test_server_live.py` | Live push, reconnection, and running beside a real collector pass (§9) |
| `local/tests/test_config_local.py` | Extended for `local.port` (the file is PBI-019's, in an allowed area) |
| `exporters/board_config.py` | `local(cfg)` gains `port` (§3) |
| `board.config.json` | `"local"` gains `"port": 8765` |

**One module, on purpose.** The allowed area is `local/server*`, so the glob permits `local/server_x.py`
if the file grows past comfort. It is written as one module because the parts are small and share one
lock (§5.3).

**Why the read-only opener is not in `db.py`.** `local/db*` is **not** in this PBI's allowed areas, so
this PBI may import `db.py` but may not edit it. `db.open_db` is also the wrong function: it creates
the parent folder, creates the file, runs `schema.create_schema` and creates the three `collector_*`
tables — all writes, and it takes the write lock (PBI-019 §3.3, steps 6 and 7). The server therefore
defines its own `server.open_read(path, root=None)` (§5.1). It reuses `db.network_path` and
`db.resolve` unchanged, so the FR-96 guard is one implementation in both processes.

**Imports.** There are no packages (PBI-003 A-1). `local/server.py` inserts the repository's
`exporters/` folder into `sys.path`, found from `__file__`, exactly as `local/collector.py` does;
`local/` is already on `sys.path` when it runs as a script. Imports only ever go from `local` to
`exporters`. The standard library only (C-21): `http.server`, `socketserver`, `socket`, `sqlite3`,
`threading`, `queue` (one bounded queue per stream, §7.1), `json`, `io`, `os`, `re`, `argparse`, `sys`,
`time`. No third-party package, and no network client of any kind.

**Records it serves:** every kind in `records.TABLES` — `session`, `run`, `project`, `tab`, `status`,
`lastRefresh`, `catalogue`. The collector writes only five of them today (PBI-019 §2); `tab` and
`status` arrive when PBI-025 lands, and the server needs no change for that, because it enumerates
kinds from `records.TABLES` and never from `sqlite_master`.

## 3. Configuration: the port key

- **`board.config.json`** gains `"port": 8765` inside the existing `"local"` block, which PBI-019
  created for `databasePath`. The parent spec anticipated this ("the second to land merges"); PBI-019
  is merged, so this PBI only adds the key.
- **`board_config.local(cfg)`** returns `{"databasePath": <str>, "port": <int>}`. The existing
  `databasePath` behaviour is unchanged, including its `ValueError` messages, so the collector and
  `local/tests/test_config_local.py` keep working.
- **Validation**, in the style of `catalogue()` and the existing `databasePath` check:
  - a `local` block that is not an object already raises `ValueError('"local" must be an object, not
    <type>')`;
  - a `port` that is not an integer, or is a `bool` (because `True` is an `int` in Python), or is
    outside 1 to 65535, raises `ValueError('local.port must be a whole number from 1 to 65535, not
    <repr>')`.
- **Default:** 8765 (C-21, row 8).
- **Port 0 is refused in the config** and accepted only through `--port` and the in-process entry
  point, where it means "bind a free port". That is how the tests get an ephemeral port without
  writing a config (§9). Row Q-3.

The collector reads `local(cfg)['databasePath']` and ignores the new key; nothing else in the
repository reads the `local` block.

## 4. Binding and hardening (NFR-19, NFR-20, FR-96, row 24)

### 4.1 Start-up order

Nothing is opened, created or bound until the checks pass, in this order:

1. **Read the config** (`server.read_config`, the same shape as `collector.read_config`: an unreadable
   file, text that is not JSON, and a top-level value that is not an object are all refusals, never a
   crash). A `ValueError` or `OSError` prints one line and exits 2.
2. **Read `local.databasePath` and `local.port`** (§3). A `ValueError` exits 2.
3. **The network-path guard** (§4.4). A network path prints the path and exits 2, **before any socket
   is bound and before the database path is touched** (AC-67).
4. **Bind** 127.0.0.1 on the configured port (§4.2). A port already in use exits 2, naming the port.
5. **Serve.** The database is opened lazily on the first read (§5.1), so a server started before the
   collector's first pass still serves the page.

### 4.2 Binding (NFR-19)

- `ThreadingHTTPServer` with `address_family = socket.AF_INET` and `server_address = ('127.0.0.1',
  port)`. The literal address, never the name `localhost`, which can resolve to `::1` as well and
  would bind a second socket.
- **`allow_reuse_address = False`.** `http.server.HTTPServer` sets it to 1. On Windows `SO_REUSEADDR`
  lets a second process bind the same address and port and take over the listener, so it is turned off;
  the cost is that a restart within the TIME_WAIT window may have to wait, and it exits 2 with a clear
  message when it cannot bind.
- `daemon_threads = True`, so a stuck stream thread cannot keep the process alive after `stop()`.
- `protocol_version = 'HTTP/1.1'`, so keep-alive works. Every ordinary response therefore **must**
  carry a `Content-Length`; the event stream is the one exception and closes the connection instead
  (§7.1).
- AC-66 (the `netstat -ano` inspection) is the owner's, under PBI-007. The server-level check is
  AC-SV1.

### 4.3 The request path: how the gate really runs first

`http.server` does not give the gate for free, and the design must say how it is obtained. In CPython's
`BaseHTTPRequestHandler.handle_one_request` the dispatch is `mname = 'do_' + self.command`, and

```python
if not hasattr(self, mname):
    self.send_error(HTTPStatus.NOT_IMPLEMENTED, "Unsupported method (%r)" % self.command)
    return
```

so a method with no `do_` attribute is answered **501 before any handler code of ours runs** — it would
never reach the Host and Origin checks, and never reach a 405. `parse_request` refuses earlier still:
400 for a malformed request line (echoing it), 505 for an unsupported version, and 431 when the header
count passes `http.client._MAXHEADERS` (100) or a header line passes `_MAXLINE` (65536);
`handle_one_request` itself answers 414 for a request line over 65536 bytes. Every one of those paths
goes through `send_error`, which by default renders `DEFAULT_ERROR_MESSAGE` — an HTML page, at
`text/html;charset=utf-8`, carrying the offending method token or request line HTML-escaped into the
body. That is the opposite of this spec's "one line of `text/plain`" and "the offending value is never
echoed" (§4.3.1). Two overrides fix both halves.

**One funnel.** The handler defines exactly six methods — `do_GET`, `do_HEAD`, `do_POST`, `do_PUT`,
`do_DELETE`, `do_OPTIONS` — and each is one line that calls the same `_handle()`. `_handle()` runs the
Host check, then the Origin check, and only then routes on the path (§6). No route is reachable without
the gate, and a route added later gets it by construction because routing happens inside `_handle()`.

**A method outside those six** (`PATCH`, `TRACE`, `CONNECT`, or any other token) has no `do_` attribute
and is answered **501** by `handle_one_request`, before the gate. That is accepted, not worked around:
the six cover every method the browser can aim at this server, the 501 reaches no route and no board
data, and the overridden `send_error` makes its body identical in shape to every other refusal. The
alternative, overriding `handle_one_request` itself, would re-implement request parsing for no gain.

**One refusal shape.** `send_error(code, message=None, explain=None)` is overridden and **ignores the
`message` and `explain` it is handed**. It sends the status, then `Content-Type: text/plain;
charset=utf-8`, `Cache-Control: no-store`, a `Content-Length`, the standard headers below and
`Connection: close`, then one fixed line and nothing else:

**Which line, and who chooses it (review R2-1).** A refusal the server raises itself — the Host and Origin gate of §4.3.1, the route and stream refusals of §6.3, and §7.1's `too many open streams` — goes through an internal helper that names its own line and sets the headers that line needs, including `Retry-After: 5` on 503. The `send_error` override governs only the statuses the framework raises (400, 414, 431, 501, 505 and a 500 from an unhandled error), where the status code alone does determine the line. Either path emits the same shape: one line of `text/plain`, no HTML, and never an echo of the offending value.

The lines are:

| Status | Reached by | Body |
|---|---|---|
| 400 | a malformed request line (`parse_request`) | `bad request` |
| 403 | the Host or Origin check (§4.3.1) | the three lines of §4.3.1 |
| 404 | an unknown path, after the gate | `not found` |
| 405 | a routed method no route takes, after the gate | `method not allowed` |
| 414 | a request line over 65536 bytes | `bad request` |
| 431 | over 100 headers, or a header line over 65536 bytes | `bad request` |
| 500, 503 | §6.3 | the lines in §6.3 |
| 501 | a method outside the six | `method not allowed` |
| 505 | an unsupported HTTP version (`parse_request`) | `bad request` |

`error_message_format = '%(code)d\n'` and `error_content_type = 'text/plain; charset=utf-8'` are set as
well, so even a path that somehow reached the base implementation could not emit HTML or an echo.
`log_error` still writes the framework's own message, including the offending token, to **stderr** only
— that is the owner's diagnostic, and the no-echo rule is about the response body.

### 4.3.1 Host, Origin and CORS (row 24)

Every request that reaches a `do_` method passes through the gate before it is routed.

- **Host allow-list.** The `Host` header is split into host and port. The host, lower-cased, must be
  `127.0.0.1` or `localhost`. The port, when present, must equal the port the server is listening on.
  A missing `Host` header is rejected. Everything else — a name that resolves to 127.0.0.1 through DNS
  rebinding, a LAN name, a wrong port — is rejected with **403**. Row 7's Unraid extension of this
  list is deferred with the Unraid idea and is not built here (§12).
- **Origin.** Any request carrying an `Origin` header whose value is not exactly
  `http://127.0.0.1:<port>` or `http://localhost:<port>` is rejected with **403**. On a request whose
  method is **not** `GET` or `HEAD`, an `Origin` header is **required**; a non-GET request without one
  is rejected with 403. The server has no non-GET route today, so a well-formed `POST`, `PUT`,
  `DELETE` or `OPTIONS` that passes the gate reaches a **405** from `_handle()`'s routing — which is
  only true because those four have their own `do_` methods (§4.3); the check exists so that a later
  route (the deferred Unraid ingest) cannot be added without it, and it is tested against all four.
- **No CORS, ever.** No response carries any `Access-Control-Allow-*` header, and `OPTIONS` is not
  answered as a preflight: it goes through the same gate and then gets 405. Without those headers a
  browser will not hand a cross-origin page the snapshot or the stream, and the Host allow-list closes
  DNS rebinding, which is the attack row 24 names.
- **What a rejection returns.** Status 403 through the overridden `send_error` of §4.3, so:
  `Content-Type: text/plain; charset=utf-8`, `Cache-Control: no-store`, a `Content-Length`, the other
  headers below, and one line of body: `forbidden: the Host header is not a local address` or
  `forbidden: the Origin header is not a local address` or `forbidden: this request needs an Origin
  header`. **The offending value is never echoed** into the body, so the response cannot be used to
  reflect attacker-chosen text, and no board data appears in it. The rejection is logged once on
  stderr, with the value, for the owner. Every other refusal the server or the framework can emit —
  400, 404, 405, 414, 431, 501 — comes out of that same override with the same headers and the same
  one-line shape (§4.3's table).
- **Other headers on every response:** `X-Content-Type-Options: nosniff`, `Referrer-Policy:
  no-referrer`, `X-Frame-Options: DENY`, and on the page a `Content-Security-Policy` of
  `default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
  https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src
  'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'`. `'unsafe-inline'` is
  unavoidable: the page is one file of inline style and inline script (C-8). The value of the policy
  here is `connect-src 'self'`, `frame-ancestors 'none'` and `default-src 'none'`. Row Q-13 records
  the font hosts.
- **`version_string()`** returns the fixed string `dispatch-board`, so no response advertises the
  Python or `BaseHTTPServer` version.
- **Request-line limits.** `http.server` already caps the request line at 65536 bytes and the header
  count at 100, and refuses past either with a 414 or a 431 raised inside the framework — which lands
  in the overridden `send_error` and therefore comes back as the same one line of `text/plain`, with
  the request line not echoed (§4.3). A request body is never read, because no route takes one; a
  non-GET request is refused or 405'd before any body is read, and the connection is then closed
  rather than left with an unread body on it.

### 4.4 The network-path guard (FR-96, FR-180, NFR-20, AC-67)

The server calls `db.network_path(path)` — the same function, with the same four checks in the same
order, that PBI-019 §3.2 specifies and `local/db.py` implements. On a true result the server prints to
stderr:

```
server: refusing to start: the database path \\nas\share\board.db is a network path; SQLite over SMB or NFS is unsafe (C-14)
```

with the path **exactly as configured**, and exits 2. Nothing is bound, no folder or file is created,
and the database path is not opened. That is AC-67 in full.

Two qualifications carry over from PBI-019 §3.2 and §5, and are repeated here rather than assumed:
`GetDriveTypeW` on a mapped drive letter and `os.path.realpath` on a link into a share may make Windows
contact that file server before the path is refused. The server itself sends nothing and exits at once.

**Who owns NFR-20** ("0 deployments shall place the local database file on a network share; the local
server shall open the database only on storage local to the host it runs on"). Its **on-PC half is
asserted here**, not deferred: the committed `local.databasePath` is `out/local/board.db`, a repository-
relative path resolved against the repository root (§5.1 step 1), so the default deployment is local
storage by construction; and the guard above runs at **every** start, before any socket is bound and
before the path is opened, so a path that is a network path can never be served from. AC-67 and AC-SV8
test exactly that. The Unraid half — AC-71's volume-mapping inspection — went to Future iterations with
the Unraid idea (§12) and is **not** what this spec rests on; the on-PC deployment's own end-to-end
inspection, if the owner wants one on top of the guard, belongs with PBI-007, which owns the on-PC
deployment (parent spec, PBI-007's row). Nothing here points at deferred work.

## 5. Reading the database (C-14, C-21, and PBI-019's handoffs)

### 5.1 Opening, read-only

`server.open_read(path, root=None) -> sqlite3.Connection | None`:

1. `full = db.resolve(path, root)` — a relative path is resolved against the **repository root**, never
   the working folder, exactly as the collector does (PBI-019 §3.1), because PBI-007 may start this
   process from `System32`.
2. If `full` does not exist, return `None`. The server is then "not ready" (§6.3) and tries again on
   the next read. **It never creates the database**: that is the collector's job, and a file the server
   created would have no schema.
3. `sqlite3.connect(full, isolation_level=None, timeout=5, check_same_thread=False)`, then
   `PRAGMA query_only = 1`. Any write statement on that connection now raises
   `sqlite3.OperationalError`, which is the mechanical guarantee behind "the server never writes"
   (AC-SV6).
4. `PRAGMA user_version`. A version of 0, or a `sessions` table that does not exist, means the
   collector has not finished its first pass: close and return `None` (not ready). A version greater
   than `schema.SCHEMA_VERSION` is refused, and the server reports it as "not ready", naming both
   versions, rather than exiting — the collector may be mid-upgrade and the owner should still get the
   page.

**What "never writes" means precisely.** `query_only = 1` stops every statement that would change the
database's content; it does not stop SQLite from creating the `-wal` and `-shm` files beside the
database when it opens a WAL file and no writer is currently connected, and it cannot, because that is
how WAL is read at all (it is also why a `mode=ro` URI will not do, below). So the claim this spec makes
and AC-SV6 tests is scoped to **the database file itself** — its bytes, its mtime and its
`PRAGMA data_version` are unchanged, and `sqlite_master` gains nothing — not to the folder's listing.
The server still creates no file of its own: no log, no state file, and never the database (step 2).

**Why not a `mode=ro` URI.** A read-only connection cannot create the `-shm` file a WAL database needs,
so opening `file:…?mode=ro` fails outright when no writer is currently connected. `query_only=1` on an
ordinary connection gives the same protection against writing our own data while letting SQLite manage
the WAL index. Row Q-2.

**One race, and why it is harmless.** Between step 2's existence check and step 3's connect, the file
could vanish; SQLite would then create an empty one. Step 4 sees `user_version` 0 and reports "not
ready", and the collector's `open_db` heals an empty file (PBI-019 §3.3: missing tables are fine). No
data is lost and nothing is refused for good.

### 5.2 Concurrency with the collector

- **WAL.** The collector puts the file in WAL mode. Readers never block the writer and the writer never
  blocks readers, so a snapshot taken during a collector pass returns the last committed state and the
  pass is not delayed (PBI-019 §3.5).
- **Busy timeout** of 5 seconds (the `timeout=5` on connect). A reader still waits briefly for a
  checkpoint or the schema lock. On expiry the read raises `sqlite3.OperationalError`, which becomes a
  503 (§6.3), never a crash and never a partial snapshot.
- **Never `BEGIN IMMEDIATE`,** never a write, never `create_schema`, never `db.upsert` / `db.delete`.
- **A consistent snapshot** reads all seven tables inside one short `BEGIN DEFERRED` … `COMMIT` read
  transaction, so the page never sees a run whose session is missing. It is milliseconds long. This
  respects PBI-019 §3.6's handoff ("a long-held read transaction stops WAL checkpoints and makes the
  `-wal` file grow") because the transaction never spans a poll, a sleep or a socket write.
- **`PRAGMA data_version`** is polled through `db.Changes` on the **server's own** connection and
  **outside** any read transaction, as §3.6 requires. It changes only for commits by other connections,
  so it is exactly "the collector committed something".

### 5.3 One reader, one lock

The server holds one `State` object with one connection, one `db.Changes` watcher, the current
snapshot, and an integer `version`. Every use of the connection happens while the state's
`threading.Lock` is held, so the connection is never touched by two threads at once even though it is
opened with `check_same_thread=False`. Request threads and the watcher thread (§7.2) all go through
the same two methods:

- `State.refresh() -> (version, records, changed_paths, removed_paths)`: if `Changes.poll()` is true,
  or there is no snapshot yet, re-read (§5.4), diff against the previous snapshot by store path, bump
  `version` when anything differs, and return the delta; otherwise return the current snapshot and an
  empty delta.
- `State.current()`: the snapshot as it stands, refreshing first.

`version` starts at 1 and is **not** persisted: a restarted server re-baselines and its first event to
a returning client is a `reset` (§7.3). Row Q-14.

### 5.4 Reading the records (FR-93, AC-69)

For each `kind` in `records.TABLES`, in a fixed order, the server calls **`db.stored(conn, kind)`** —
the function PBI-019 already ships (`local/db.py:169`), which runs
`SELECT id, doc FROM <table> ORDER BY id` over `records.TABLES[kind][0]` and returns `{id: document}`.
It is a plain `SELECT`: read-only, safe on the `query_only` connection, and it removes the duplicated
loop this spec's revision 1 described.

**Why the naive loop would not have worked.** `records.from_row(kind, row)` accepts a `str` or a
`Mapping`/`sqlite3.Row` and raises `ValueError` for anything else, a tuple included
(`local/records.py:264-286`). A default `sqlite3` cursor yields **tuples**, so
`from_row(kind, row)` over `conn.execute(...)` would have raised on every row: an empty snapshot with
`skipped` equal to the record count, which AC-69 would have passed vacuously. `db.stored` avoids it by
unpacking each row into `rid, doc` and handing `from_row` the **doc text**, which is one of the two
shapes it takes. Should the fallback below ever need row objects instead, it sets
`conn.row_factory = sqlite3.Row` on its own cursor and never on the shared connection.

**The id check is explicit.** Because `db.stored` passes text rather than a mapping, `from_row` does
not run `_check_id`; the server gets that check from `records.store_path(kind, rid)`, which calls
`_check_id` itself (`local/records.py:211-216`) and raises `ValueError` for an id not in the kind's
form. Every key in the snapshot is therefore a validated store path, and an ill-formed id is skipped by
the same rule as an invalid document.

Each record becomes one entry keyed by `records.store_path(kind, record_id)`:

```json
"runs/f3a1": {"kind": "run", "id": "f3a1", "doc": { … }}
```

- **`from_row` validates.** It raises `ValueError` for text that is not JSON, for `NaN`/`Infinity`, for
  an id not in the kind's form, and for a document that fails `records.validate`. So every record the
  server returns conforms to the shapes by construction, which is AC-69.
- **A row that raises is left out**, counted in the response's `skipped` figure, and warned about once
  on stderr naming its kind and id. One bad row must not blank the board; this mirrors the collector's
  per-record handling (PBI-019 §4.9). Row Q-7.
- **How the skip works with `db.stored`.** `db.stored` is a dict comprehension, so a single bad row
  raises for the whole kind. The server therefore calls it first and, **only when it raises
  `ValueError`**, falls back for that one kind to the same `SELECT` run row by row on a cursor with
  `row_factory = sqlite3.Row`, calling `records.from_row(kind, row)` per row and skipping the rows that
  raise. The happy path is `db.stored` unchanged; the fallback exists solely to isolate the bad rows,
  and the kinds that read cleanly are never re-read. Both paths produce the same `{id: document}`
  mapping, so the code after them is one branch.
- **Only `records.TABLES` is read.** `sqlite_master` is never enumerated, so the three `collector_*`
  state tables (PBI-019 §3.4) are invisible to the server, along with any other table in the file.
- **No answers, ever** (C-16). There is no `answers` kind in `records.SHAPES`, no `answers` table in
  the schema, and no route that accepts a body. If an `answers` table were somehow present in the file,
  the server would not read it. AC-SV7 asserts this against a file that has one.

**The store-path key, and the missing inverse.** The PBI-003 review's follow-up 3 notes that
`local/records` has no inverse of `store_path` (path back to kind and id), that
`local/tests/test_conformance.py` reimplements one, and that `COLLECTION` maps `meta` to both
`lastRefresh` and `status`. **This PBI does not need the inverse**, and therefore does **not** need
`local/records*` added to its allowed areas:

- the server always goes the forward way, from a kind it already has to a path;
- every entry carries its own `kind` and `id`, so no consumer has to parse the key back;
- no route takes a store path as input; the snapshot is whole, and the stream names paths only as
  keys of a delta.

If a later review decides the snapshot should instead be addressable per path (`GET
/api/record/meta/status`), that route would need the inverse and the areas would have to be widened —
a scope question for the owner at that point, not an assumption made here. Row Q-10.

## 6. Routes

**Three routes** — `/`, `/api/snapshot` and `/api/events` — on `GET` and `HEAD` only. (§6.3 is not a
route; it is the error table those three share.) Routing happens inside `_handle()`, after the gate of
§4.3: an unknown path is 404, and a known path asked for with a routed method no route takes is 405.

### 6.1 `GET /` — the page (FR-92, C-8)

`site/**` is **blocked for this PBI**, so the page is not copied, embedded or edited. The server
**reads** `site/index.html` at request time — reading a file is not editing it — resolves it with
`db.resolve('site/index.html')` from the repository root, and wraps it, because the file is authored
as page content only, with no `<html>`, `<head>` or `<body>` (C-8).

**The wrapper** reproduces what the Artifact tool puts around the same file, so the local page and the
published artifact render alike:

```html
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>:root{color-scheme:light}body{margin:0;background:#faf9f7;font:14px system-ui,-apple-system,"Segoe UI",sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>
<title>…</title>
<script>window.__DISPATCH_LOCAL__={"snapshot":"/api/snapshot","events":"/api/events","version":1};</script>
</head><body>
…site/index.html, byte for byte, minus the hoisted title…
</body></html>
```

- **The title is hoisted, and nothing else is parsed.** One regular expression takes a
  `<title>…</title>` from the first 8 KB of the file — the same window the Artifact tool scans — and
  moves it into the head; the remainder of the file goes into the body unchanged. If there is no
  title, `Dispatch board` is used. No other element is moved, and the file is never otherwise rewritten.
  A `<link rel="preconnect">` or `<style>` left in the body is valid and behaves identically; browsers
  hoist neither, and neither does this wrapper. Row Q-8.
- **`window.__DISPATCH_LOCAL__` is the adapter seam** for PBI-006 (FR-98, AC-73). Its presence is the
  signal "you are being served by the local server, use the local API adapter"; its absence, in the
  artifact, means the store adapter. PBI-006 may instead detect the absence of `window.claude`; the
  marker is additive and harmless either way, and it carries the two URLs so the adapter hard-codes
  none. This is a seam this spec fixes, for PBI-006 to consume (row Q-11).
- **What the page does before PBI-006, and why an empty board is correct here.** `site/index.html`
  opens its data with `db = await window.claude?.use?.('db')` (`site/index.html:1139`). Served locally
  there is no `window.claude`, so the optional chain yields `undefined` without throwing, the page sets
  `offline = true`, renders every tab empty and puts "This view cannot reach the live store, so it
  shows no data." in the footer. (The `console.warn` on that path fires only if opening a store
  *raises*, which cannot happen when the object is absent — so expect no console error either.) That
  is the expected observable for this PBI: the server's job is the page, the snapshot and the stream;
  wiring the page to them is PBI-006's (FR-97 to FR-99, §12). A build reviewer should read an empty
  local board with that footer as **pass**, not as a defect, and should check `/api/snapshot` for the
  data instead.
- **Headers:** 200, `Content-Type: text/html; charset=utf-8`, `Cache-Control: no-store`, a
  `Content-Length`, the CSP of §4.3. `HEAD` returns the same headers and no body.
- **A missing or unreadable `site/index.html`** returns 500 with a one-line plain-text message naming
  the path. The server still starts and the API routes still work, so the failure is diagnosable.

### 6.2 `GET /api/snapshot` — the data snapshot (FR-93, AC-69)

```json
{
  "version": 12,
  "generatedAt": "2026-09-12T09:14:02+00:00",
  "skipped": 0,
  "records": {
    "sessions/9562c312-…": {"kind": "session", "id": "9562c312-…", "doc": {…}},
    "runs/f3a1":           {"kind": "run",     "id": "f3a1",       "doc": {…}},
    "meta/lastRefresh":    {"kind": "lastRefresh", "id": "lastRefresh", "doc": {…}}
  }
}
```

- 200, `Content-Type: application/json; charset=utf-8`, `Cache-Control: no-store`, a `Content-Length`.
- **Serialised with `json.dumps(…, ensure_ascii=True)`** and sent as ASCII bytes. A session title can
  hold a lone surrogate (the exporters and the shapes both allow it); `ensure_ascii=True` writes it as
  a `\udXXX` escape, so no response can fail with `UnicodeEncodeError` part-way through a body. The
  same rule holds for the event stream (§7.1).
- `version` is the value a client passes back as `?since=` when it opens the stream (§7.3).
- `generatedAt` is the server's own clock and is for the owner's eyes only. The page's staleness
  (FR-104, FR-105, PBI-008) reads `meta/lastRefresh`, which is a record like any other.

### 6.3 Not-ready and error responses

| Condition | Status | Body (one line, `text/plain`, except where noted) |
|---|---|---|
| The database file does not exist, or has no schema yet | 503 | `the local database is not ready yet; the collector has not written it` |
| `user_version` newer than `schema.SCHEMA_VERSION` | 503 | `the local database is at schema version N, newer than this server (version M)` |
| A read times out on the busy timeout, or any `sqlite3.Error` | 503 | `the local database could not be read; try again` |
| Any unexpected exception in a handler | 500 | `the server failed to handle this request` |

- A 503 carries `Retry-After: 5`. The page is served in every one of these states, so the owner sees a
  board that says it has no data rather than a browser error.
- A traceback goes to stderr only, never into a response. PBI-007 captures that stderr to a log file;
  this PBI writes no log file of its own (§8).

### 6.4 `GET /api/events`

§7.

Every other path, including `/favicon.ico`, returns 404 with a one-line plain-text body.

## 7. Live push (FR-94, AC-68, NFR-18)

### 7.1 The stream

`GET /api/events` responds 200 with `Content-Type: text/event-stream; charset=utf-8`,
`Cache-Control: no-store`, `X-Accel-Buffering: no` and **`Connection: close`** — with
`protocol_version = 'HTTP/1.1'` and no `Content-Length`, the handler must either chunk the body itself
or close the connection; closing is simpler and costs nothing, because Server-Sent Events keep one
connection open for their lifetime anyway.

The handler then writes ASCII bytes and flushes after every write:

```
retry: 3000

event: change
id: 13
data: {"version":13,"set":{"runs/f3a1":{"kind":"run","id":"f3a1","doc":{…}}},"deleted":["sessions/ab"]}

: ping
```

- one `data:` line per event, one line of `json.dumps(…, ensure_ascii=True)` with no newlines in it;
- `id:` is the snapshot version, so a reconnecting browser sends it back as `Last-Event-ID`;
- `retry: 3000` is sent once, at the start;
- a `: ping` comment every 15 seconds. It keeps idle intermediaries from closing the stream and, more
  usefully, is how the server discovers a browser that has gone away: the write raises and that client
  is dropped.
- **At most 8 concurrent streams.** A ninth gets 503 with `too many open streams`. One owner with a few
  tabs never reaches it, and it bounds the thread count.

**Every byte of a stream is written by that stream's own request thread.** The watcher thread (§7.2)
never touches a socket. `ThreadingHTTPServer` already gives each connection its own thread; the
`/api/events` handler keeps that thread for the life of the stream and runs one loop:

- it owns a **bounded `queue.Queue(maxsize=32)`**, registered in the hub when the stream opens and
  removed in a `finally` when it ends;
- it blocks on `queue.get(timeout=15)`; an item is an event to write, a timeout is the heartbeat;
- it writes and flushes. A `BrokenPipeError`, `ConnectionResetError`, `OSError` or `socket.timeout`
  ends the loop, removes the queue from the hub and closes the connection — the client is gone.

**The watcher only enqueues.** For each registered queue it calls `put_nowait`. On `queue.Full` — the
client is not draining, so its send buffer is full or the tab is suspended — that client is **dropped**:
its queue is marked overflowed and removed, and its own thread sees the mark, writes nothing more and
closes. The watcher never blocks, never waits on a socket, and never holds the state lock across a
write. A suspended tab therefore costs at most 32 buffered events and itself; it cannot delay the
watcher, another client, or the change budget of §7.2, which is the failure NFR-18 exists to exclude.

**A belt as well as braces:** the connection socket is given `settimeout(10)` for the stream's
lifetime, so even a write that begins into a full buffer cannot block that thread for ever. A timeout
is treated as a dead client, exactly like a broken pipe. (A dropped client loses nothing it needed: it
reconnects on `retry: 3000` and the version comparison of §7.3 hands it a `reset`.)

### 7.2 Detecting a change

One **watcher thread** exists while at least one stream is open. Every `--poll` seconds (default 2) it
calls `State.refresh()` (§5.3), which polls `PRAGMA data_version` through `db.Changes` and, when that
says another connection committed, re-reads the records and diffs them by store path. A non-empty
delta is **enqueued** to every open stream as one `change` event, whose `set` holds the full document
of every added or changed record and whose `deleted` holds the paths that went. Enqueuing is all the
watcher does with a client (§7.1): one `put_nowait` per queue, a drop on `queue.Full`, and no socket
write of its own, so no client can stall it or another client.

Sending whole documents rather than field-level patches keeps the client simple and matches the store
adapter's model, where a subscription hands the page a whole document per path. The data is small: a
few hundred records at most.

**The budget (NFR-18: 10 minutes).** A transcript append is picked up by the collector's next pass
(default interval 60 s, PBI-019 §5), committed, seen by the next poll (≤ 2 s), and written to the open
stream at once. The worst case is about 62 seconds plus delivery, against a budget of 600. AC-68's
in-browser leg is a demonstration and belongs to PBI-007; the server-level leg is AC-68 as restated in
§10 and is tested without a browser.

**With no clients** the watcher thread is not running: the database is not polled at all, nothing is
buffered, and no thread is alive for the stream. The first client to connect starts it; the last to
disconnect stops it within one poll interval. The version and the cached snapshot survive in the
`State`, so nothing is re-read needlessly. Row Q-6.

### 7.3 Joining and reconnecting

A page fetches `/api/snapshot`, reads its `version`, then opens `/api/events?since=<version>`. On
connect the server reads **both** `?since=` and the `Last-Event-ID` header, takes each one that parses
as a non-negative integer, and uses **the larger of the two** — the client's newest knowledge — as the
version it holds. Neither wins unconditionally. Then, after a `State.refresh()`, against the current
version:

- **equal:** send nothing but the `retry:` line and the heartbeats. The client is already current.
- **different, or both absent, or neither parses:** send `event: reset`, **with `id: <current
  version>`** and `data: {"version": N}`. The client re-fetches `/api/snapshot` and reopens the stream.
  This closes the race between the snapshot fetch and the stream opening, and covers a browser that was
  asleep, a server restart, and any missed event, without the server keeping a history of deltas.

**Why both halves of that matter.** `EventSource` resends the last `id:` it saw as `Last-Event-ID` on
every automatic reconnect, and the page cannot clear it. Under revision 1 — no `id:` on `reset`, and
`Last-Event-ID` winning unconditionally — a client that had just obeyed a `reset` and re-fetched a
newer snapshot would reconnect still carrying the **old** id, be judged stale again, and be reset
again, on a 3-second loop. Putting `id: <version>` on the `reset` moves the browser's stored id forward
as soon as it is told to reset, and taking the larger of the two values means a fresh `?since=` from a
just-fetched snapshot is never overridden by a stale header. Both are needed: the `id:` fixes the
browser's own retry, the max fixes the first reconnect after a manual re-open.

Reconnection itself is the browser's: `EventSource` retries on its own, after `retry: 3000`.

## 8. Running it

```
python local/server.py [--port N] [--config PATH] [--poll SECONDS]
```

- **`--config`** defaults to the repository's `board.config.json`. Unlike the collector, the config is
  read **once**, at start: a changed port or database path means a restart, and the server says so in
  its start-up line.
- **`--port`** overrides `local.port` and accepts 0, which binds a free port and prints the one it got.
- **`--poll`** overrides the 2-second `data_version` poll.
- **Exit codes:** 0 on Ctrl+C or `stop()`; **2** for every start-up refusal — a network path, a config
  that cannot be read or is not an object, a bad `local.databasePath` or `local.port`, a port already
  in use; **1** for any other failure.
- **One line on stdout at start:** `server: serving http://127.0.0.1:8765 from out/local/board.db`.
  Warnings and rejections go to stderr, prefixed `server: `.
- **Callable in-process for the tests:** `server.serve(config=None, db_path=None, port=None,
  page=None, poll=None) -> Server`, which is already bound and serving in a background thread and
  offers `.port`, `.url` and `.stop()`; and `server.main(argv=None, …) -> int`, which returns the exit
  code.
- **What it never does:** write to the database, invoke `claude`, or contact any network host
  (NFR-17, AC-70; the PBI-019 §3.2 qualification about the guard's own checks applies here too, §4.4).
  It reads exactly two files: the config and `site/index.html`.
- **Start at log-on, and the log file, are PBI-007's.** This PBI adds no Task Scheduler task and writes
  no log file; capturing this process's stdout and stderr to a log in a known local folder is PBI-007's
  job, exactly as it is for the collector (PBI-019 §5's handoff). Without that capture a scheduled
  server's refusals are invisible, so it matters.

## 9. Tests (`local/tests/`, standard library `unittest` only)

**What the tests never touch:** the real `~/.claude`, `out/`, `board.config.json` or database, and the
real port 8765. Every server is started with `port=0` in a temporary folder, and stopped in
`tearDown`. Databases are built by running the real `db.open_db` and `db.upsert` in a temporary folder,
or by running `collector.run_pass` over the synthetic transcripts, so the tests exercise the real
schema rather than a hand-made one.

**How they import:** they insert `local/` and `exporters/` into `sys.path`, as `test_conformance.py`
does, and reuse `local/tests/collector_support.py` and `test_conformance.Fixture` for fixtures.

**A small HTTP client, not a browser.** `http.client.HTTPConnection` for the ordinary routes; for the
stream, the same connection with the response read incrementally in a thread, with a timeout. No
browser is needed for any criterion except AC-68's in-page leg, which is a demonstration (§10).

**`test_config_local.py`** (extended): `port` defaults to 8765; a string, a float, `True` and 0, and
70000 each raise `ValueError` naming `local.port`; `databasePath`'s existing behaviour is unchanged;
the committed `board.config.json` holds both keys.

**`test_server.py`:**
- **Binding:** `server_address == ('127.0.0.1', port)`, `address_family` is `AF_INET`,
  `allow_reuse_address` is false; a connection to the machine's own LAN address on that port is
  refused (skipped when that address is 127.0.0.1 or unavailable).
- **The page:** 200 and `text/html; charset=utf-8`; the body starts `<!doctype html>`, holds exactly
  one `<html>`, one `<head>` and one `<body>`, carries the charset and viewport metas, the reset and
  the CSP header; the file's bytes appear in the body unchanged apart from the hoisted title; the title
  is in the head; `window.__DISPATCH_LOCAL__` carries both URLs; `HEAD` gives the same headers and no
  body; a missing `site/index.html` gives 500 naming the path while `/api/snapshot` still answers.
- **Host allow-list:** `127.0.0.1:<port>` and `localhost:<port>` pass; `evil.test:<port>`,
  `board.example.com`, `127.0.0.1:1` and a request with no `Host` each give 403, `text/plain`, one
  line, with neither the offending value nor any record in the body.
- **Origin:** `POST`, `PUT`, `DELETE` and `OPTIONS` with no `Origin`, or with a foreign one, give 403;
  with the allowed `Origin` they give 405; a `GET` carrying a foreign `Origin` gives 403. No response
  of any route carries a header beginning `Access-Control-Allow-`.
- **The gate really runs first (§4.3):** the handler class has a `do_` method for each of `GET`, `HEAD`,
  `POST`, `PUT`, `DELETE` and `OPTIONS` (asserted by `hasattr`, so the funnel cannot be removed
  silently); a raw `PATCH` request gives 501; a request line of 70000 bytes gives 414; 120 header lines
  give 431; a malformed request line gives 400. **Every one of those responses** — and the 403s, 404s
  and 405s above — is `text/plain; charset=utf-8`, one line, ends in a single `\n`, carries
  `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` and a `Content-Length`, contains no `<`
  and does not contain the offending token (`PATCH`, the bad request line, the rejected `Host` or
  `Origin` value) anywhere in the body.
- **Snapshot conformance (AC-69, non-vacuous):** the fixture's records are read back and the snapshot
  must hold **an entry for every record written**, with `skipped == 0` — so a build in which every row
  raised and the snapshot came back empty **fails**, rather than passing on an empty `records` map.
  Then every entry's key equals `records.store_path(kind, id)` and every `doc` gives
  `records.validate(kind, doc) == []`. A separate case adds one deliberately corrupt row (written
  directly with the collector's connection): that row is left out, `skipped` is exactly 1, a warning
  names its kind and id, **and every other record of that same kind is still served** — which is the
  per-kind fallback of §5.4 working rather than `db.stored` losing the whole kind.
- **Ignores the collector's state and answers:** with rows in all three `collector_*` tables and an
  `answers` table created in the file, no response body contains their contents or the substring
  `collector_`; **the API routes** (`/api/snapshot` and the stream's events) additionally contain no
  `answers` substring — the page route is exempt, because its body is `site/index.html`, whose wording
  this PBI neither owns nor may edit. The snapshot's kinds are a subset of `records.TABLES` for every
  route.
- **Never writes:** the **database file's** bytes, its mtime and its `PRAGMA data_version` are
  unchanged after every route has been exercised, and `sqlite_master` gains nothing; the assertion is
  on the database file, not on the folder's listing, because SQLite may create `-wal`/`-shm` beside it
  (§5.1). `PRAGMA query_only` is 1 on the server's connection; with `db.open_db`,
  `schema.create_schema`, `db.upsert` and `db.delete` patched to raise, every route still answers.
- **Not ready:** with no database file, `/` is 200 and `/api/snapshot` is 503 with `Retry-After`, and
  **no file is created** at the path; with `user_version` set past `SCHEMA_VERSION`, 503 names both
  versions; after the collector then creates the database, the next request serves records with no
  restart.
- **The network-path guard (AC-67):** `main([])` with `local.databasePath` set to
  `\\nas\share\board.db` exits 2, stderr holds that exact path, no socket is listening on the
  configured port, and nothing is created on disk. The same for `//nas/share/board.db` and for a local
  path whose `os.path.realpath` is patched to a UNC path.
- **The command line:** a bad `local.port` exits 2; a port already in use exits 2 naming the port; a
  start-up line names the URL and the database; `stop()` exits 0; `--port 0` binds and reports a free
  port.
- **Errors:** a handler forced to raise gives 500, one plain line, no traceback in the body and a
  traceback on stderr; no response carries a `Server` header naming Python.

**`test_server_live.py`:**
- **AC-68 at the server level:** with a stream open, another connection commits a change to a run's
  `kind` (`running` → `done`); within three poll intervals the stream yields one `change` event whose
  `set` holds `runs/<id>` with the new `kind`, and whose `version` is greater than the snapshot's. The
  same with a deleted record, which arrives in `deleted`.
- **Joining:** `?since=<current version>` yields no `reset`; `?since=1` on a later version yields
  `reset`; a reconnect carrying `Last-Event-ID` behaves the same. **The larger value wins, either
  way:** a stale `Last-Event-ID` with a current `?since=` yields no `reset`, and a current
  `Last-Event-ID` with a stale `?since=` yields none either. **No reset loop:** the `reset` event
  carries `id: <current version>`; re-opening the stream with that id as `Last-Event-ID`, after
  re-fetching the snapshot, yields no second `reset`.
- **Heartbeat and disconnect:** a `: ping` arrives within twice the heartbeat; a client that closes its
  socket is dropped, and with `db.Changes.poll` wrapped by a counter the poll count stops rising once
  the last client has gone (measured with the tolerance AC-SV10 states), and rises again on the next
  connection.
- **No client can stall another (§7.1):** two streams are opened; one stops reading entirely while its
  socket buffer fills (the test reads nothing on it and pushes more than 32 changes). The other stream
  keeps receiving every change within one poll interval throughout, the poll counter keeps rising, and
  the stalled client is dropped rather than the watcher blocking. The same case with the reader's queue
  patched to a `maxsize` of 2, so the overflow is reached in a couple of events rather than 32.
- **Cap:** the ninth concurrent stream gets 503.
- **Beside a real collector:** `collector.run_pass` is run on the same file while a stream is open and
  a snapshot request is in flight. The pass commits (its report is a committed one), the snapshot
  returns a consistent set, and the stream delivers the change. Then, with another connection holding
  `BEGIN IMMEDIATE`, a snapshot request still returns the last committed state.

## 10. Acceptance criteria

**From the PRD**, restated so each is testable. AC-66 and AC-70 to AC-73 are not this PBI's (§12).

- [ ] **AC-67** When `local.databasePath` is `\\nas\share\board.db`, the local server shall refuse to
      start: exit code 2, that path printed on stderr exactly as configured, no socket listening on the
      configured port, and no file or folder created. *(FR-96, FR-180; §4.4; testable, no browser.)*
- [ ] **AC-68** When a record in the local database changes while a client is connected to
      `/api/events`, the server shall deliver a `change` event naming that record's store path and
      carrying its new document, within three poll intervals — well inside NFR-18's 10 minutes.
      *(FR-94, NFR-18; §7; testable at the server level with an HTTP client. The in-page leg — the page
      open in a browser shows the run's new kind without a reload — is a **demonstration** and belongs
      to PBI-007, which owns AC-68's end-to-end form.)*
- [ ] **AC-69** When `/api/snapshot` is requested over a database holding a known set of conforming
      records, it shall return **an entry for every one of them, with `skipped` 0** — an empty or
      short `records` map fails this criterion, so it cannot be met vacuously — and every entry it
      returns shall satisfy `records.validate(kind, doc) == []` with a key equal to
      `records.store_path(kind, id)`. A stored row that does not conform is omitted and counted in
      `skipped`, never returned, and the other rows of its kind are still returned.
      *(FR-93, FR-100; §5.4; testable, no browser.)*

**Added by this spec.** Each is testable without a browser and is covered in §9.

- [ ] **AC-SV1** *(NFR-19; §4.2.)* The server binds `127.0.0.1` only: `server_address[0]` is
      `127.0.0.1`, the address family is `AF_INET`, `allow_reuse_address` is false, and a connection to
      the machine's LAN address on that port is refused. AC-66's `netstat` inspection stays PBI-007's.
- [ ] **AC-SV2** *(Row 24; §4.3, §4.3.1.)* `GET /` succeeds with `Host` of `127.0.0.1:<port>` or
      `localhost:<port>`, and returns 403 for a foreign name, a name with the wrong port, and a request
      with no `Host` header. **Every refusal the server can emit — 400, 403, 404, 405, 414, 431, 501
      and 505 — has the same shape:** `text/plain; charset=utf-8`, one line, `Cache-Control: no-store`,
      `nosniff`, a `Content-Length`, no `<` in the body, no record data, and no echo of the rejected
      value (the `Host`, the `Origin`, the method token or the request line).
- [ ] **AC-SV3** *(Row 24; §4.3, §4.3.1.)* The handler defines `do_GET`, `do_HEAD`, `do_POST`,
      `do_PUT`, `do_DELETE` and `do_OPTIONS`, and every one funnels through the gate before routing:
      `POST`, `PUT`, `DELETE` and `OPTIONS` give 403 without an `Origin` or with a foreign one, and 405
      with the allowed one. A `GET` carrying a foreign `Origin` gives 403. A method outside those six,
      such as `PATCH`, returns **501** — answered by `handle_one_request` before the gate, reaching no
      route and no board data, in the one-line plain shape of AC-SV2. No response from any route
      carries an `Access-Control-Allow-*` header.
- [ ] **AC-SV4** *(C-21; §3.)* `board_config.local(cfg)` returns `port`, defaulting to 8765. A value
      that is not a whole number, is a boolean, or falls outside 1 to 65535 raises `ValueError` naming
      `local.port`; `databasePath`'s existing behaviour and messages are unchanged; the committed
      `board.config.json` holds both keys; `--port 0` binds a free port.
- [ ] **AC-SV5** *(FR-92, C-8; §6.1.)* `GET /` returns 200 `text/html; charset=utf-8` whose body is one
      well-formed document — `<!doctype html>`, one `<html>`, one `<head>`, one `<body>` — carrying the
      charset and viewport metas and the reset, with `site/index.html`'s content in the body byte for
      byte apart from a `<title>` hoisted into the head, and with `window.__DISPATCH_LOCAL__` naming
      `/api/snapshot` and `/api/events`. `HEAD /` returns the same headers and no body. An unknown path
      returns 404; a missing `site/index.html` returns 500 naming the path while the API still answers.
      `site/**` is not edited.
- [ ] **AC-SV6** *(NFR-20, C-14; §5.1, §5.2.)* The server never writes **the database's content**: its
      connection reports `PRAGMA query_only` 1; after every route has been exercised **the database
      file's** bytes, its mtime and its `PRAGMA data_version` are unchanged and `sqlite_master` has
      gained nothing; and every route still answers with `db.open_db`, `schema.create_schema`,
      `db.upsert` and `db.delete` patched to raise. The criterion is scoped to that file: SQLite may
      create a `-wal`/`-shm` pair beside it when it opens a WAL database, which is outside the server's
      control (§5.1), so the folder's listing is not asserted. The server itself creates no file.
- [ ] **AC-SV7** *(PBI-019 §3.4's handoff; C-16; §5.4.)* With rows in all three `collector_*` tables
      and an `answers` table present in the file, no response body holds any of their contents or the
      substring `collector_`, and **the API routes' bodies** (`/api/snapshot` and the stream's events)
      hold no `answers` substring either — that substring check is scoped to the API routes, because
      the page route's body is `site/index.html`, whose wording this PBI neither owns nor may edit.
      The kinds in the snapshot are a subset of `records.TABLES`, on every route. The server has no
      route that accepts a request body.
- [ ] **AC-SV8** *(FR-93; §5.1, §6.3.)* With no database file, `/` still returns the page and
      `/api/snapshot` returns 503 with `Retry-After` and a one-line reason, and **no file is created at
      the configured path**. A `user_version` newer than `schema.SCHEMA_VERSION` returns 503 naming both
      versions. Once the collector creates the database, the next request serves records with no
      restart.
- [ ] **AC-SV9** *(FR-94; §7.1, §7.3.)* The stream sets `text/event-stream`, `no-store` and
      `Connection: close`, and opens with a `retry:` line. `?since=<current version>` produces no
      `reset`; a stale, absent or unparsable position produces one, and that `reset` carries
      `id: <current version>`, so re-opening with it as `Last-Event-ID` after a fresh snapshot produces
      **no second `reset`** (no reset loop). Where both `?since=` and `Last-Event-ID` are present, the
      **larger** parseable value is used, whichever header it came from. A `: ping` comment arrives
      within twice the heartbeat. The ninth concurrent stream is refused with 503.
- [ ] **AC-SV10** *(FR-94; §7.1, §7.2.)* While no client is connected, the server does not poll the
      database: with `db.Changes.poll` wrapped by a counter, the count stops rising after the last
      client disconnects and rises again once a client connects. **The stated tolerance**, so the test
      cannot be flaky: after the last client's socket is closed, the server is allowed one heartbeat
      plus one poll interval (15 s + 2 s at the defaults, and the test drives both down through
      `--poll` and the heartbeat constant) to discover the loss; the count is sampled **after** that
      window and must then be unchanged over a further two poll intervals. Nothing is buffered for
      absent clients, and a client that connects later is brought up to date by a `reset` plus a fresh
      snapshot. A client that stops reading is dropped on its queue's overflow and stalls neither the
      watcher nor any other stream (§7.1).
- [ ] **AC-SV11** *(C-14, C-21; §5.2.)* The server and a real collector pass run against the same file
      without either blocking the other: with a stream open, `collector.run_pass` commits, the change is
      delivered, and a snapshot taken during the pass returns a consistent, last-committed set. While
      another connection holds `BEGIN IMMEDIATE`, a snapshot still answers; a read that exceeds the
      5-second busy timeout returns 503, not a crash and not a partial body.
- [ ] **AC-SV12** *(§4.1, §8.)* `main([])` starts, prints one line naming the URL and the database, and
      returns 0 when stopped. It returns 2 for a network path, a config that cannot be read or is not an
      object, a bad `local.databasePath` or `local.port`, and a port already in use, each with a message
      naming the cause; 1 for any other failure. A handler that raises returns 500 with one plain line,
      the traceback on stderr only, and no response advertises the Python version.

**Close-out expectation.** This spec does not edit `docs/backlog/pbi/PBI-005-local-server.md`, which is outside this
PBI's allowed areas; it states what close-out is expected to show, and the worker's close-out is read
against this line:

- [ ] All three configured suites are green on the head commit: `python -m unittest discover -s tests`,
      `node tests/page.test.mjs` and `python -m unittest discover -s local/tests`. The code-review gate
      has passed (`review-agents:code-reviewer` GO).

`PBI-005.md`'s own close-out line names only the first two suites; all three are the configured
`[test_commands]` in `backlog-delivery.config`, and `local/tests` is where this PBI's tests live, so
running all three is the expectation either way. Amending that line in the PBI file is the owner's, not
this PBI's.

**That is 15 criteria in all:** 3 from the PRD and 12 added, plus the close-out expectation. One of
them, AC-68, has a demonstration half that is PBI-007's; every other criterion is testable without a
browser.

## 11. Assumptions and open questions

**Owner** marks a row that genuinely needs the owner. The other rows are settled at the spec gate, or
can be.

| # | Question | Default chosen | Impact if wrong | Needs |
|---|---|---|---|---|
| Q-1 | Where the port lives | `local.port` in the existing `local` block, default 8765 (C-21, row 8); `board_config.local` returns it beside `databasePath` | A rename touches one config file and one function | — |
| Q-2 | How to open a WAL database without writing to it | An ordinary connection with `PRAGMA query_only = 1`, not a `mode=ro` URI, because a read-only connection cannot create the `-shm` file a WAL database needs and fails outright when no writer is connected | If `query_only` were somehow not honoured, an accidental write would reach the file. AC-SV6 checks the pragma and the file's bytes, so a regression is caught | — |
| Q-3 | Port 0 | Refused in `board.config.json`; accepted through `--port` and the in-process entry point, where it means an ephemeral port for the tests | A test that hard-codes a port collides with a running server; that is the reason for the exception | — |
| Q-4 | The snapshot's shape | One object keyed by store path, each entry carrying `kind`, `id` and `doc`, plus `version`, `generatedAt` and `skipped` | PBI-006's local API adapter is written against this. A change after PBI-006 lands costs both | **Settled at spec-gate round 1** (reviewer: "settled at this gate"). PBI-006 builds against it |
| Q-5 | What the stream carries | Whole documents in a `set` map plus a `deleted` list, not field-level patches, with a `reset` event as the catch-all | Slightly larger events. Patches would need a merge rule the store adapter does not have | — |
| Q-6 | Polling with no clients | No watcher thread and no polling at all; the first client starts it, the last to leave stops it within one poll interval | A page opened long after a change gets its data from the snapshot anyway, so nothing is lost | — |
| Q-7 | A stored row that does not conform | Left out of the snapshot, counted in `skipped`, warned once on stderr; never fatal | The board shows fewer records than the database holds until the collector is fixed. Failing instead would blank the board over one bad row (AC-69 requires that what *is* returned conforms, which this meets) | — |
| Q-8 | How the content-only page is wrapped, given `site/**` is blocked | Read `site/index.html` at request time and wrap it in a fixed skeleton, hoisting only a `<title>` found in the first 8 KB, mirroring what the Artifact tool does | If the Artifact harness's skeleton changes, the local page drifts from the published one. The drift is visual, and the fix is one string in `server.py` | — |
| Q-9 | Where the page file is found | `site/index.html`, resolved from the repository root like the database path; re-read on every request, so an edit shows on reload | A packaged deployment later would need a `--page` flag; one argument | — |
| Q-10 | Does this PBI need `local/records*` in its areas, given the missing inverse of `store_path` (PBI-003 review follow-up 3)? | **No.** The server only ever goes forward, from a kind it already holds to a path, and every entry carries its own `kind` and `id`. No route takes a store path as input, so the ambiguity of `meta/*` (both `lastRefresh` and `status`) is never met | If a later review wants per-path addressing (`GET /api/record/<path>`), the inverse is needed and the areas must be widened. That would be a scope question for the owner, not a decision this spec should make on its own | — (flagged; would become an owner question only if per-path addressing is wanted) |
| Q-11 | How the page knows it is local (FR-98, AC-73) | The wrapper injects `window.__DISPATCH_LOCAL__` with the two URLs. PBI-006 may instead detect the absence of `window.claude`; the marker is additive and harmless | If PBI-006 picks a different signal, this one is dead weight, three lines long | **Settled at spec-gate round 1**: the seam (marker plus the snapshot and event shapes) is fixed here, with S-4 applied; only the *detection signal* is PBI-006's to choose |
| Q-12 | The Host allow-list | `127.0.0.1` and `localhost` only, with the port checked when present. No IPv6 literal, because the server binds IPv4 only. Row 7's Unraid extension is deferred with the Unraid idea | A future IPv6 binding would need `[::1]` adding. One line | — |
| Q-13 | The page fetches its fonts from `fonts.googleapis.com` and `fonts.gstatic.com`, as the artifact does | Keep it, and allow exactly those two hosts in the CSP, so the local page looks like the published one | Offline, or on a locked-down machine, the local board falls back to the system sans face. It still works. If the owner wants a board that never touches the internet, the fonts must be embedded or dropped — a change to `site/index.html`, which this PBI may not edit, so it would be PBI-006's or a new PBI's | **Owner** — low urgency, does not block building. Reviewer's recommended default (round 1): build as specified, since the CSP already confines the fetch to those two hosts, and log an offline-fonts follow-up against `site/**` for PBI-006 or a new PBI |
| Q-14 | What `version` means | A per-process counter, starting at 1, bumped when the snapshot differs. It is not persisted, so a restart re-baselines and a returning client gets a `reset` | A client that reconnects across a restart re-fetches the snapshot once. That is the intended, cheap behaviour | — |
| Q-15 | Poll interval and heartbeat | 2 seconds and 15 seconds, as `--poll` and a constant, not config keys — the same choice PBI-019 made for its interval (its row Q-17), and the parent allows this PBI one config key | NFR-18's 10 minutes has enormous margin at a 60-second collector interval; a slower poll would still meet it | — |
| Q-16 | Anyone signed in to this PC can read the board, because there is no login on 127.0.0.1 | Accepted: row 24 says "No login on the PC", and the board holds no secret the owner does not already have on disk. Worth saying plainly rather than leaving implicit | On a shared machine another signed-in user could read session titles, first prompts (when `showFirstPrompt` is on) and run labels | **Settled at spec-gate round 1**: settled by parent row 24, correctly surfaced; no owner action and no build impact |
| Q-17 | `PBI-005.md`'s areas do not list `CLAUDE.md` or `README.md`, although the parent spec grants every PBI that touch ("Every PBI may update `CLAUDE.md` and `README.md` for its own procedures") | This spec keeps the run instructions in §8 and in the module docstring, and changes neither file | The owner has no note in `CLAUDE.md` saying how to start the local server. PBI-007 documents the deployment anyway, so the gap is short-lived | **Owner** — does not block building. Reviewer's recommended default (round 1): the parent spec already grants the touch and `PBI-005.md` simply omits it, so the owner either adds `CLAUDE.md` to `allowed_areas` for a one-paragraph note, or accepts §8 plus the docstring and leaves the note to PBI-007 |

## 12. Out of scope

- **The page's data adapter** (PBI-006, FR-97 to FR-99, AC-73). This PBI fixes the seam
  (`window.__DISPATCH_LOCAL__`, the snapshot shape, the event shape) and edits no page file.
- **Task Scheduler start at log-on, capturing this server's stdout and stderr to a log file, and the
  end-to-end criteria** NFR-17, NFR-21, AC-65, AC-66, AC-70 and AC-68's in-browser leg (PBI-007).
- **The Unraid upload, the ingest endpoint, the shared secret, the LAN Host allow-list and AC-71,
  AC-72** (moved to Future iterations by the owner on 2026-09-11; rows 6, 7 and 24 describe them if
  revived).
- **Answers of any kind**, including any endpoint that would accept one (D-22, C-16, FR-95, FR-134).
- **Any change to the record shapes or the SQLite schema** (`local/records*`, `local/schema*` are
  PBI-003's) — and any change to `local/db*` or `local/collector*`, which are PBI-019's and outside
  this PBI's allowed areas.
- **Writing `tab` and `status` records locally** (PBI-019 row Q-2; PBI-025). The server already serves
  those kinds, so PBI-025 needs no server change.
- **Every file under `exporters/` other than `board_config.py`, and everything under `site/`** — both
  blocked by the PBI.
- **The staleness banner** (FR-104, FR-105, PBI-008). The server serves `meta/lastRefresh` as a record;
  the page decides what to say about it.

## 13. Spec-gate record

| Round | Revision reviewed | Verdict | Review note |
|---|---|---|---|
| 1 | 1 | CHANGES-REQUIRED | `docs/backlog/reviews/PBI-005/spec-review-r1.md` |

Round 1 (2026-09-12): CHANGES-REQUIRED, 2 High, 3 Medium, 5 Low; all applied in revision 2 — see
docs/backlog/reviews/PBI-005/spec-review-r1.md.

| Finding | Sev | Disposition in revision 2 |
|---|---|---|
| S-1 | High | Applied. New §4.3 quotes CPython's `handle_one_request` dispatch, specifies six explicit `do_*` methods funnelling through one `_handle()`, an overridden `send_error` that ignores the message it is handed and emits one fixed plain line per status (plus `error_message_format` / `error_content_type` as a backstop), and states that a method outside the six returns 501 before the gate; §4.3.1, §6, AC-SV2, AC-SV3 and §9 follow it |
| S-2 | High | Applied. §5.4 now reads each kind through `db.stored(conn, kind)` (`local/db.py:169`), explains that a default cursor's tuples would have made `records.from_row` raise on every row (`local/records.py:264-286`), gets the id check from `records.store_path` (`local/records.py:211-216`), and adds a per-kind row-by-row fallback on `sqlite3.Row` so Q-7's skipping survives `db.stored`'s all-or-nothing comprehension. AC-69 is now non-vacuous: it requires an entry per stored record and `skipped` 0 |
| S-3 | Med | Applied. §7.1 gives each stream its own bounded `queue.Queue(maxsize=32)` written only by its own request thread, with the watcher doing `put_nowait` and dropping a client on `queue.Full`, plus a 10-second socket timeout as a second line; §7.2 says the watcher only enqueues; §9 adds a stalled-client test and AC-SV10 carries the assertion |
| S-4 | Med | Applied. §7.3 puts `id: <version>` on the `reset` event and takes the **larger** of `?since=` and `Last-Event-ID` rather than an unconditional precedence, with the loop it prevents spelled out; AC-SV9 and §9 test both halves, including "no second reset" |
| S-5 | Med | Applied. §4.4 asserts NFR-20's on-PC half here — the committed path `out/local/board.db` is repository-relative and the guard runs at every start, tested by AC-67 and AC-SV8 — and names PBI-007 for any deployment-level inspection. The reference to the deferred AC-71 is gone |
| S-6 | Low | Applied. §1 and §5.1 say plainly that opening a WAL database can create `-wal`/`-shm` beside it and that `query_only` protects the database's content, not the folder; AC-SV6 is scoped to the database file's bytes, mtime, `data_version` and `sqlite_master` |
| S-7 | Low | Applied. §6 now reads "Three routes", naming them, and notes that §6.3 is the shared error table, not a route |
| S-8 | Low | Applied. The `answers` substring assertion is scoped to the API routes in AC-SV7 and §9, because the page route's body is `site/index.html`; the kinds-subset assertion stays global |
| S-9 | Low | Applied. §6.1 states the observable: with no `window.claude`, `site/index.html:1139` yields `undefined` without throwing, the page sets `offline`, renders empty and shows its "cannot reach the live store" footer — and, contrary to the review note's wording, logs **no** console warning on that path, because `console.warn` there fires only if opening a store raises. A build reviewer should read that as pass, not defect |
| S-10 | Low | Applied. AC-SV10 states the tolerance: one heartbeat plus one poll interval after the socket closes before the counter is sampled, then unchanged over two further poll intervals, with both intervals driven down in the test |
| Scope slip | — | Applied. §10's close-out no longer claims to replace a line in `PBI-005.md` (outside `allowed_areas`); it is worded as the close-out expectation, noting that all three suites are the configured `[test_commands]` and that amending the PBI file is the owner's |
| Owner rows | — | Q-13 and Q-17 stay **Owner** rows, each carrying the reviewer's recommended default; Q-16, Q-4 and Q-11 are marked settled at this gate |

Round 2 (2026-09-12): APPROVE-WITH-NOTES, 2 Low; both applied in this revision without a further round, as the reviewer recommended — see docs/backlog/reviews/PBI-005/spec-review-r2.md. **The spec gate is passed.**

- **R2-1 (Low), applied:** §4.3 now says which refusals name their own line (the gate, §6.3 and §7.1, with `Retry-After` on 503) and which the `send_error` override governs (framework-raised statuses).
- **R2-2 (Low), applied:** the `from_row` citation in §5.4 is now `local/records.py:264-286`.
- The reviewer accepted both deliberate deviations from its round-1 wording (the per-kind `sqlite3.Row` fallback, and that the locally served page shows an empty board with the "cannot reach the live store" footer and no console warning).
