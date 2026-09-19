---
id: PBI-031
title: "Answers endpoint on the local server: the answer record, a server-owned answers database, POST /api/answers with its checks, a nonce content-security policy, local/answers.py list and verify, and the CLAUDE.md answer and transcription rules"
pbi: PBI-031
status: approved at spec-gate round 2 (APPROVE-WITH-NOTES; notes applied in revision 3 as a text pass)
revision: 3
parent_spec: docs/backlog/specs/dispatch-board.md
parent_revision: 6
date: 2026-09-19
grounded_at: 1cc0716
reviews: docs/backlog/reviews/PBI-031/spec-review-r1.md (round 1, revision 1, CHANGES-REQUIRED); docs/backlog/reviews/PBI-031/spec-review-r2.md (round 2, revision 2, APPROVE-WITH-NOTES). Dispositions for both rounds are in §10
---

# PBI-031: Answers endpoint on the local server (per-PBI spec)

**Citations note.** Every `path:line` below is grounded at `1cc0716` (`main`, 2026-09-19, "PBI-007 Done after
the owner's log-on…"). The working tree had uncommitted changes only under
`docs/backlog/evidence/2026-09-11-page-checks/`, which this spec does not cite.

**`main` has since moved to `270f65d`** (PBI-010 merged). Of the cited paths, only two changed, and neither
change affects this design:

- `exporters/derive.py` gained `workItemStatus` derivation. `clean`, `section`, `table` and `spec_docs` moved
  down by 49 lines: `spec_docs` is now at `:1160` and the revision at `:1212`.
- `exporters/board_config.py` gained `workItemStatus` in `projects()`. `local()` is now at `:77-90`.

PBI-030 also edits
`exporters/board_config.py` (accepted overlap, PBI file Notes), so **the builder re-grounds line numbers
against its own base**, whichever of the two lands second.

**Security path.** `backlog-delivery.config:89` lists `local/server*` and `local/answers*` in
`security_paths`, so the promotion precondition (parent spec, Metadata; row 49) is met. §4 is the threat model
that AC-A8 requires at this gate.

**Revision 2** applies spec review round 1 (`docs/backlog/reviews/PBI-031/spec-review-r1.md`, CHANGES-REQUIRED:
1 High, 4 Medium, 10 Low). All 15 findings are applied; §10 says where. The main changes:

- an Accept is bound to the default it accepts (`resolutionSha`);
- the token is fully specified;
- a Fetch Metadata gate is added;
- line separators and bidi controls are refused;
- `verify`'s cell split is defined;
- `verify` accepts superseded answers in Plan-gate history.

**Revision 3** applies spec review round 2 (`docs/backlog/reviews/PBI-031/spec-review-r2.md`, APPROVE-WITH-NOTES:
1 Medium, 5 Low) as a text pass. All six findings are applied; §10 says where. The main changes:

- `verify` accepts a superseded Plan-gate citation only from an earlier revision (SG31-r2-1);
- a refusal sent before the body is read drains the body first, so the page gets its 403 rather than a
  connection reset;
- the body-read loop and the idle-timeout log line are pinned down;
- the test-isolation scan is closed;
- the log's row field is bounded;
- citation-shaped text and three more directional marks are refused.

## 1. Intent

The local server gets its first write surface. After this PBI:

- `POST /api/answers` stores one answer to an assumption row, but only when every check in §3.4 passes;
- the answer is kept in its own SQLite file, which only the server writes;
- the snapshot and the event stream carry stored answers;
- the served page runs under a nonce content-security policy;
- `python local/answers.py list` and `verify` read the answers file read-only;
- `CLAUDE.md` states the answer and transcription rules.

The page's answer controls are PBI-032's. The two approval types are PBI-034's. The audit is PBI-033's.

**Sources.**

- **The PBI:** `docs/backlog/pbi/PBI-031-answers-endpoint.md`. Allowed areas are at `:7`, blocked areas at `:8`,
  and criteria AC-A1 to AC-A10 at `:41-65`.
- **Parent spec** (`docs/backlog/specs/dispatch-board.md`, revision 6, approved 2026-09-19, Plan-gate record
  `:606`):
  - G-8 (`:49`) and G-6 (`:47`);
  - Key decisions on answers (`:113-117`);
  - "PBI-031, answers endpoint" AC-A1 to AC-A10 (`:395-420`);
  - rows 25 to 32, 41, 46 and 49 (`:548-572`).
- **Owner decisions, not re-opened:**
  - row 32: a board answer counts as the owner's, with no login ("Just procees as if it were me");
  - row 25: answering works on this PC only, at 127.0.0.1 ("Accept, this PC only (Recommended)");
  - row 34: a board approval alone passes ("Board approval alone").
- **ADR-0002** (`docs/adr/0002-board-answers-count-as-the-owners.md`), Decision: a constant `writer: "page"` and
  `surface: "local"`; a separate file only the server writes; no process writes an answer into a repo file.
- **PRD** (`docs/prd/dispatch-board.md`):
  - FR-95 (`:436`), FR-131 (`:510`), FR-132 (`:511`), NFR-23 (`:571`) and AC-87 (`:721`), all still marked
    "Deferred (D-22)". The re-baseline (parent row 47) un-defers them. Until then the parent spec's AC-A
    criteria govern.
  - FR-96 (`:437`), FR-177 to FR-179 (`:438-440`), NFR-19 (`:567`), C-16 (`:590`) and C-17 (`:591`).
  - **G-6 is the parent spec's goal (`dispatch-board.md:47`), not a PRD item.** The PRD has no G-6. Its
    rewording (G-8) happens at approval and is not this PBI's.

## 2. The ground as it is

| Fact | Where |
|---|---|
| The server binds 127.0.0.1 only | `local/server.py:624`, `:653` |
| Every request passes a Host check (`127.0.0.1` or `localhost`, and the bound port if one is named) and an Origin check before routing. The Origin must exactly match either local origin, and is required on every non-GET/HEAD. Both read the **first** header of a name (`headers.get`) | `local/server.py:361-368`, `:382-399`, `:401-414` |
| **A GET with no Origin passes the gate.** Browsers omit Origin on a no-cors GET, such as `<img src>` from any web page | `local/server.py:404-409` |
| No CORS header is ever sent | `local/tests/test_server.py:170` |
| Routing knows three GET paths. Any other method on them is 405, and any other path is 404 | `local/server.py:416-426` |
| A refusal is one `text/plain` line from a fixed table or a fixed constant, sent with `Connection: close`, and never echoes input | `local/server.py:44-53`, `:357-359`, `:435-454` |
| Host and Origin refusal **log lines** quote the header with `%r` (repr-escaped) | `local/server.py:396`, `:411` |
| PATCH (no `do_PATCH`) is refused 501 by the framework, before the gate | `local/tests/test_server.py:182-188` |
| `Handler` sets no `timeout`, so reading the request line and headers can block without limit. `_serve_events` sets its own 10-second timeout | `local/server.py:330-335`, `:531` |
| The board database is opened read-only (`PRAGMA query_only = 1`) and never created. A file with `user_version` 0, or no `sessions` table, reads as "not ready" and is retried | `local/server.py:83-108` |
| The snapshot reads only `records.TABLES`, so another table in the board database is invisible | `local/server.py:127-153` |
| A change is found by polling `PRAGMA data_version`. The hub's watcher diffs whole snapshots and runs only while a stream is open. It sleeps on `stop.wait(poll_interval)`. `unregister()` sets `stop`, and `register()` mints a new watcher when the set was empty. At most 8 streams (`MAX_STREAMS`) | `local/server.py:37`, `:184-208`, `:247-302`; `local/db.py:175-186` |
| The CSP allows `script-src 'self' 'unsafe-inline'` | `local/server.py:40-42` |
| `_wrap_page` injects one marker `<script>` holding `{"snapshot","events","version":1}` | `local/server.py:566-580` |
| The page has one `<script>` (`site/index.html:266`) and no inline event-handler attribute, `javascript:` URL, `eval` or `new Function` (grep of `site/index.html` at `1cc0716`). It reads only `snapshot` and `events` from the marker | `site/index.html:1471-1476` |
| Server messages go to stderr as `server: …`. The log-on wrapper captures stderr into `out/local/logs/server.log`. `log_request` logs the request line only, never headers or body. An unhandled handler exception prints a full traceback | `local/server.py:56-57`, `:375-376`, `:556-563`; `local/deploy/run_local.py:1-20`; `CLAUDE.md:145-149` |
| `serve()` discards the config after reading `databasePath` and `port`. `Server` has no config | `local/server.py:585-626` |
| `SHAPES` has no length rule, and fields a SPEC does not list are allowed and kept | `local/records.py:18-28` |
| `to_row` reads its columns from `TABLES[kind]`. A column copies the doc field of the same name, except where `_DOC_FIELD` maps it (`ord`→`order`) | `local/records.py:139`, `:247-277` |
| `schema.DDL` is built from `records.TABLES` alone, and its names are "fixed lowercase words", unquoted | `local/schema.py:20-27` |
| `local/tests/test_schema.py:88-93` asserts that no board-database table and no `schema.DDL` statement contains "answer" | — |
| `local/tests/test_records.py:187` and `:550` assert that `answer` is an unknown kind. `:69` and `:74` pin the set of kinds and the `SHAPES` literal | — |
| Assumption rows are exported by `derive.spec_docs` as `{n, question, resolution, status, source, impact, level, needsYou}`. `question` and `resolution` are the cleaned second and third cells. `needsYou` comes from the "Rows the human must confirm" line. The spec tab's `revision` is a **string** (`"6"`, or `"—"`) | `exporters/derive.py:1111-1133`, `:1163` |
| `derive.table()` splits the block with `str.splitlines()`, which also splits on U+2028 and U+2029. It splits cells on unescaped `\|`, cleans each cell, and drops the first row as the header | `exporters/derive.py:1008-1031` |
| The page's rule is "awaiting you" = `needsYou`, and ASSUMED = `status === 'ASSUMED'` | `site/index.html:916` |
| `board_config.local()` returns exactly `{databasePath, port}`. The collector calls it at start and on every pass | `exporters/board_config.py:69-86`; `local/collector.py:722`, `:752` |
| The server test harness and the e2e harness both pass a config with no answers path. So do six direct `server.main` calls. With a default of `out/local/answers.db`, all of them would resolve to the **real** file under the repository | `local/tests/server_support.py:270-277`; `local/tests/test_deploy_e2e.py:85-89`; `local/tests/test_server.py:527`, `:540`, `:553`, `:562`, `:570`, `:580` |
| The marker string is pinned by three tests, and a fourth asserts that the page file's bytes are the served body | `local/tests/test_server.py:62`, `:102`, `:104-109`; `local/tests/test_deploy_e2e.py:185-188` |
| The collector deletes only its temporary catalogue folder and board-database rows keyed by `records.TABLES`. None of the collector, `db.py` or `tabs.py` names an answers file or key: a grep for "answer" at `1cc0716` finds only a comment (`collector.py:384`) and a docstring (`tabs.py:59`) | `local/collector.py:447-459`; `local/db.py:165-166` |
| The deploy inspection scans every `local/*.py`. It treats a call to any function named `run`, `call`, `system`, `popen` and the like as a process launch. `socket` may be used only for `AF_INET` and `timeout` | `local/tests/test_deploy_inspection.py:54-63`, `:72-75` |
| `out/` is git-ignored | `.gitignore:2` |

## 3. Decisions

### 3.1 The answer record (`local/records.py`, AC-A1)

- **One new kind, `answer`, in `SHAPES`,** with one flat SPEC. PBI-031 defines one type. PBI-034 may restructure
  the SPEC when it adds its two types.
  - **Required fields:**
    - `id`: `str`;
    - `type`: `str`, enum `['assumption']`;
    - `projectId`: `str`;
    - `note`: `str`;
    - `at`: `datetime` (strict, timezone required);
    - `writer`: `str`, enum `['page']`;
    - `surface`: `str`, enum `['local']`;
    - `specPath`: `str`;
    - `specRevision`: `int`;
    - `row`: `int`;
    - `questionSha`: `str`;
    - `resolutionSha`: `str`;
    - `choice`: `str`, enum `['accept', 'override']`;
    - `answer`: `str`.
  - **Optional field:** `supersedes`: `str`.
  - `resolutionSha` binds an answer to the default the owner saw (SG31-1). It is required on every answer, so no
    stored answer ever lacks it. Answers are append-only and are never migrated.
- **One shape-language addition: `maxLength`.** A SPEC may carry `"maxLength": {field: n}`. `_check_spec` adds
  the error `<field>: longer than n characters` when a present `str` value has `len(value) > n`. Length is
  counted in Python code points (A-6). The answer SPEC sets `{"note": 2000, "answer": 2000}`. This keeps the
  module's rule that "`validate()` reads no rule from anywhere else" (`local/records.py:6`).
- **Registries:**
  - `COLLECTION['answer'] = 'answers'`;
  - `_ID_FORMS['answer'] = re.compile('[0-9a-f]{32}')`;
  - `ANSWER_TABLES = {'answer': ('answers', ('id', 'project_id', 'supersedes', 'at', 'doc'))}`;
  - `_DOC_FIELD` gains `'project_id': 'projectId'`.
  - Column names are lowercase words, like every other table's (`local/schema.py:20-23`), and go unquoted. No
    column is named `row`, which is an SQLite keyword. `project_id` is used by no other table, so the shared
    `_DOC_FIELD` map stays unambiguous.
  - `records.TABLES` is **unchanged**.
- **`to_row` looks a kind up in `TABLES`, then in `ANSWER_TABLES`,** through one private helper, so
  `to_row('answer', …)` works. `from_row` and `store_path` need no other change.
  `store_path('answer', '<32 hex>')` returns `answers/<id>`.
- **`records.shapes.json` is regenerated** with `python local/records.py --write-shapes`. Nothing in the repo
  parses it at run time (grep at `1cc0716`), so the added `answer` kind and `maxLength` key break no reader.
  `tests/test_export_board.py:961` and `:1018` read only its run enums.
- **The module docstring** says that `TABLES` is the board database's registry and `ANSWER_TABLES` the answers
  database's.

### 3.2 The answers database (`local/schema.py`, `exporters/board_config.py`, AC-A2)

- **Location.** `local.answersPath`, default `out/local/answers.db`. It is resolved like `databasePath`:
  relative paths against the repository root (`db.resolve`), with `~` expanded.
  - **A separate reader, `board_config.answers_path(cfg)`,** returns it and validates it as a non-empty string.
    `board_config.local()` is **unchanged**. Only the server and `answers.py` call the new reader, so a
    malformed `answersPath` can never stop the collector, which calls `local()` on every pass (SG31-11). The
    whole-dict assertions in `test_config_local.py:12-42` stay true unedited.
  - `board.config.json` itself is **not edited**: the default applies (A-10).
- **Ownership.** Only `local/server.py` creates or writes the file.
  - The server refuses to start (exit 2 from `main()`, `db.NetworkPath` from `serve()`) when `answersPath` is a
    network path (`db.network_path`, FR-96). Its line names the path, as today's database guard does
    (`local/server.py:649-651`).
  - It also refuses to start when `answersPath` and `databasePath` resolve to the same file (compared with
    `os.path.normcase(os.path.realpath(...))`), so the board database never gets a second writer.
  - The file is created lazily, on the **first answer that passes checks 1 to 16**, never at start, on a GET, or
    on any refused POST (A-2; §3.6 covers the `supersedes` edge case).
- **Schema.** `schema.py` gains:
  - `ANSWERS_SCHEMA_VERSION = 1`;
  - `answers_ddl()`, which returns `CREATE TABLE IF NOT EXISTS answers (...)` built from
    `records.ANSWER_TABLES` with the same `_TYPES` rule, plus:
    - `CREATE INDEX IF NOT EXISTS idx_answers_project ON answers (project_id)`;
    - `CREATE UNIQUE INDEX IF NOT EXISTS idx_answers_supersedes ON answers (supersedes)`. SQLite treats NULLs
      as distinct, so many roots are allowed but an answer can have at most one successor (§3.6).
  - `create_answers_schema(conn)`, which mirrors `create_schema` (one `BEGIN IMMEDIATE` transaction, refusing a
    `user_version` newer than `ANSWERS_SCHEMA_VERSION`).
  - `schema.DDL`, `SCHEMA_VERSION` and `create_schema` are **unchanged**, so `test_schema.py:88-93` stays green
    unedited.
- **Journal and durability.** The rollback journal (SQLite's default, `DELETE` mode) with `synchronous = FULL`,
  set explicitly (A-13). There is no WAL, so a read-only opener needs no `-shm` file.
- **Why the collector never deletes or opens it:**
  1. the collector reads and writes only `databasePath`, through `local()` (`local/collector.py:722`, `:752`),
     and never calls `answers_path()`;
  2. its pruning, deletes and mass-delete guard run over `records.TABLES` rows in that file only
     (`local/db.py:165-172`; `local/collector.py:529-546`), and `answer` is not in `TABLES`;
  3. it removes only its own temporary folder (`local/collector.py:447-459`);
  4. the refresher's exporters delete only under `out/sessions`, `out/runs`, `out/projects` and
     `out/projectTabs` (`exporters/export_sessions.py:276-278`; `exporters/export_board.py:276-295`);
  5. the log wrapper deletes only its own rotated backups under `out/local/logs/` (`CLAUDE.md:135-136`).

  An inspection test pins points 1 and 2 (AE-7).
- **Never pruned (row 46).** No code path issues `DELETE`, `UPDATE`, `DROP` or `REPLACE` on `answers`. An
  inspection test over `local/server.py` and `local/answers.py` pins that (AE-9). The durable copy of an answer
  is its transcription. The file is not backed up.

### 3.3 The route, the token and the gate (`local/server.py`, AC-A3, AC-A4)

- `_route` learns `/api/answers`:
  - `POST` goes to `_post_answer`;
  - `GET`, `HEAD`, `PUT`, `DELETE` and `OPTIONS` get today's `405 method not allowed`;
  - `PATCH` stays `501 method not allowed`, from the framework (A-16).
- **The token (SG31-2):**
  - `secrets.token_urlsafe(32)`: 32 random bytes (256 bits) from the OS CSPRNG, encoded as 43 characters of
    URL-safe base64 (`[A-Za-z0-9_-]{43}`, no padding);
  - created **once, in `Server.__init__`**, as `Server.token`;
  - the same for both origins (`127.0.0.1` and `localhost`) and every page load during one server start;
  - **rotated only by a restart**, never persisted, and never logged;
  - its character set needs no escaping in the marker JSON or in a header, and can never form `</`;
  - it is compared in constant time: the header value, taken as latin-1 bytes, is compared with the token's
    ASCII bytes using `hmac.compare_digest`. A value of a different length or with non-ASCII bytes simply
    compares unequal.
  - This matches AC-A3 and parent row 31 ("the token the server generated at start").
- **The Fetch Metadata gate (SG31-3), new in `_handle`,** runs after the Host and Origin checks and before
  routing, for every method and path.
  - When a `Sec-Fetch-Site` header is present, its value must be `same-origin` or `none`. Otherwise the request
    is refused with 403 `forbidden: the request came from another site`.
  - **One exception:** `GET` or `HEAD` of `/` with `Sec-Fetch-Mode: navigate` and `Sec-Fetch-Dest: document`
    passes whatever the site, so a link or bookmark to the board still opens it.
  - `same-site` is refused on purpose. A page on another `localhost` port is same-site with the board.
  - A request with no `Sec-Fetch-Site`, from a non-browser client or an old browser, passes as today. Such a
    request still meets the Host and Origin checks (A-19).
  - The refusal is logged as `rejected a request with Sec-Fetch-Site %r` (repr-escaped, like the Host and Origin
    lines).
  - This closes the no-cors GET route by which any web page could hold `/api/events` stream slots (`MAX_STREAMS
    = 8`) or fetch the snapshot blind.
- **Exactly one header on the answers route (SG31-12).** On `POST /api/answers`, a request carrying more than
  one `Host`, `Origin`, `Content-Type`, `Content-Length`, `X-Dispatch-Token` or `Sec-Fetch-Site` header (by
  `headers.get_all`) is refused at the first check that reads that header, with that check's line. The rule is
  not widened to the GET routes: their behaviour is unchanged apart from the Fetch Metadata gate.
- **Header-phase timeout (SG31-7).** `Handler.timeout = 30`, so a client that never finishes its request line
  or headers is dropped after 30 seconds. `_serve_events` keeps setting its own 10-second timeout after its
  headers (`:531`).
- **`Server` construction.** `Server` takes the config's `projects` (through `board_config.projects(cfg)` at
  start), the resolved answers path and the token. `serve()` and `main()` gain `answers_path=None`. When it is
  `None`, `board_config.answers_path(cfg)` applies.
- **Projects are read once, at start (A-9).** The server already reads its config only at start.

### 3.4 Checks, in order, with status, line and log reason

The first failing check answers. Nothing is stored, and the body is never echoed. **Checks 1 to 7 run before
any byte of the body is read.** Every refusal on `/api/answers` also carries the header `X-Dispatch-Reason:
<log reason>`, a fixed word from the last column, so PBI-032 can branch without parsing text (SG31-15). It
echoes nothing.

| # | Check | Status and line (exact) | Log reason |
|---|---|---|---|
| 1 | Exactly one Host header, on the allow-list (today's check) | 403 `forbidden: the Host header is not a local address` | `host` (today's line) |
| 2 | Exactly one Origin header, exactly `http://127.0.0.1:<port>` or `http://localhost:<port>` (today's check) | 403, today's two lines | `origin` (today's line) |
| 2a | Fetch Metadata gate (§3.3) | 403 `forbidden: the request came from another site` | `site` |
| 3 | Method is POST | 405 `method not allowed` | `method` |
| 4 | No `Transfer-Encoding` header, and exactly one `Content-Length`, fullmatching `[0-9]{1,5}` (no sign, space or `_`) | 411 `a Content-Length is required; chunked bodies are refused` | `length` |
| 5 | `1 <= Content-Length <= 16384` | 413 `the answer is larger than 16 KiB` (0 gets check 8's line) | `size` |
| 6 | Exactly one `Content-Type`, matching the grammar below | 415 `the answer must be sent as application/json` | `content-type` |
| 7 | Exactly one `X-Dispatch-Token`, equal to `Server.token` (§3.3) | 403 `forbidden: the answer token is missing or stale; reload the page` | `token` |
| 8 | The body is read against a **5-second wall-clock deadline** for the whole body: the loop is `self.connection.settimeout(left)` then `self.rfile.read1(remaining)`, so body bytes already buffered with the headers are kept (SG31-r2-3), and a read past the deadline fails. The body must be exactly Content-Length bytes of strict UTF-8, parse as JSON (§3.5) and be an object | 400 `bad request: the answer is not a JSON object` (short or late read: `bad request: the answer was incomplete`) | `json` / `incomplete` |
| 9 | The body holds none of `id`, `at`, `writer`, `surface` | 400 `bad request: id, at, writer and surface are set by the server` | `server-field` |
| 10 | Body keys ⊆ SHAPES['answer'] required+optional fields, less the four server-set ones. With the server's fields added, `records.validate('answer', …)` returns `[]`. Text rules hold (§3.5) | 400 `bad request: the answer does not match the answer record` | `shape` |
| 11 | `projectId` is the id of a `projects[]` entry, and `specPath` equals that entry's `docs.spec` exactly (string compare; no file is touched) | 400 `bad request: the project or spec is not in board.config.json` | `project` |
| 12 | The board database is ready | 503 with today's `NOT_READY` or `READ_FAILED` line and `Retry-After: 5` | `not-ready` |
| 13 | The snapshot holds `projectTabs/<projectId>.spec` and `.assumptions`. The assumptions tab's `source` equals `docs.spec`. The spec tab's `revision` equals `str(specRevision)` | 409 `conflict: the spec has changed since the page was loaded; reload the page` | `revision` |
| 14 | A row with `n == row` exists and is awaiting: `needsYou is true` or `status == "ASSUMED"` | 409 `conflict: that row is not awaiting an answer; reload the page` | `row` |
| 15 | `sha256(row.question.encode('utf-8')).hexdigest() == questionSha` | 409 `conflict: the question has changed since the page was loaded; reload the page` | `question` |
| 15a | `sha256(row.resolution.encode('utf-8')).hexdigest() == resolutionSha`, for every choice (an Override records what it overrode) | 409 `conflict: the default has changed since the page was loaded; reload the page` | `resolution` |
| 16 | Chain rule (§3.6), checked inside the write transaction. When the file does not exist yet, it is checked **before** anything is created | 409 `conflict: that row already has an answer; reload the page` / `conflict: the answer it replaces is not the row's current answer; reload the page` | `duplicate` / `supersedes` |
| 17 | The answers file can be opened, created or migrated, and the insert commits | 503 `the answers database is not available; see server.log` with `Retry-After: 5` | `unavailable` |

- **Draining before close (SG31-r2-2).** A refusal at check 3, 6 or 7 on `/api/answers` is sent before the
  body is read. Closing a socket with unread bytes in its receive buffer sends a reset, and on Windows the client
  can then lose the response: the page would see a network error instead of 403 "reload the page". So, when
  the request carries exactly one valid `Content-Length` (it meets checks 4 and 5's rules), the handler:
  1. sends the refusal and flushes it;
  2. reads and **discards** up to that many bytes, never parsing them, against a 1-second deadline, stopping
     early when the client closes;
  3. returns, so the framework closes the connection.

  No `shutdown(socket.SHUT_WR)` is used, so `socket`'s use stays within `AF_INET` and `timeout`
  (`local/tests/test_deploy_inspection.py:54-55`). Refusals at checks 4 and 5, where the length is missing or
  invalid, close as now. The drained bytes never reach a check, a log or a response.
- **Content-Type grammar (check 6).** Exactly one `Content-Type` header, whose value, split on the first `;`,
  gives:
  - a media type that, stripped of spaces and tabs, equals `application/json` compared case-insensitively;
  - optionally, one parameter which, stripped, is `charset=utf-8` compared case-insensitively. The value is
    unquoted: `charset="utf-8"` is refused.

  Any other parameter, or a second `;`, is refused. So `application/json`, `Application/JSON` and
  `application/json ; Charset=UTF-8` pass; `application/json; charset=latin-1`, `application/json;
  charset="utf-8"` and `application/json; x=1` do not.
- **Success** returns 201 `application/json; charset=utf-8`, `Cache-Control: no-store`, today's security
  headers, and the body `{"kind": "answer", "id": "<id>", "doc": {…}}`, the snapshot's entry shape
  (`local/server.py:147`).
- The server sets:
  - `id`: `secrets.token_hex(16)`;
  - `at`: `datetime.now(timezone.utc).isoformat(timespec='seconds')`, in `+00:00` form like `generatedAt`;
  - `writer`: `"page"`;
  - `surface`: `"local"`.
- **Why these statuses (A-7).** The parent spec asks only for "the existing one-line 4xx shape". Every line is
  a fixed string built by `_respond_plain`, so the shape is today's. Each reason carries its own status and
  `X-Dispatch-Reason`, so the page (PBI-032) can tell "reload" (403 or 409) from "fix the input" (400, 413, 415)
  without parsing text.

### 3.5 Validation details

- **JSON parsing:** `json.loads(text, object_pairs_hook=…, parse_constant=…)`.
  - A duplicate key is refused (the hook raises).
  - `NaN`, `Infinity` and `-Infinity` are refused.
  - `RecursionError`, `ValueError` (which includes Python's integer-digit limit) and `UnicodeDecodeError` all
    give check 8's line.
- **Every body value is a scalar.** Any list or object value fails check 10 (the shape has no nested field).
- **Text rules** (part of check 10, and in the server rather than the record shape):
  - **Forbidden set** (SG31-4). These characters break a table row or a terminal line:
    - Unicode category `Cc` (C0, DEL, C1, which includes U+0085 NEL and every other `str.splitlines()`
      separator below U+2028);
    - category `Zl` (U+2028) and `Zp` (U+2029);
    - the bidi embedding, override and isolate controls U+202A to U+202E and U+2066 to U+2069;
    - the directional marks U+200E, U+200F and U+061C (SG31-r2-6).
  - `answer` contains no forbidden character. It is one line.
  - `note` contains no forbidden character except `\n`.
  - Neither `answer` nor `note` contains citation-shaped text, `answer:[0-9a-f]{32}`. Both are quoted on
    transcribed lines, and such text would be read by `verify` as a second citation (SG31-r2-6).
  - `projectId`, `specPath`, `questionSha`, `resolutionSha` and `supersedes` contain no forbidden character.
  - For `choice == "accept"`, `answer` is `""` (A-4).
  - For `choice == "override"`, `answer.strip()` is non-empty.
  - Every string encodes as UTF-8. A lone surrogate from a `\ud800` escape is refused rather than failing later
    at the insert.
- **The body limit is 16,384 bytes whatever the fields hold.** An answer and a note both at 2,000 astral
  characters, JSON-escaped, can exceed it and are refused with 413 (A-18).
- **`specRevision` is an `int`,** compared with the spec tab's string revision as `str(specRevision)`. A spec
  whose revision exports as `"—"` cannot be answered (check 13).
- **`questionSha` and `resolutionSha` are defined for PBI-032** as lowercase hex SHA-256 of the UTF-8 bytes of
  the assumptions tab row's `question` and `resolution` strings exactly as exported, with no trimming or
  normalisation. The page can compute them with `crypto.subtle`, since `127.0.0.1` and `localhost` are secure
  contexts.

### 3.6 Write atomicity, idempotency and duplicates (AC-A4)

- **One current answer per row.** The chain key is `(projectId, specPath, row)`.
  - An answer **without** `supersedes` is stored only if no stored answer has that key.
  - An answer **with** `supersedes: S` is stored only if `S` is a stored answer with the same key that nothing
    already supersedes (the head of the chain).
  - Otherwise the answer is refused with 409 (check 16).
  - The unique index on `supersedes` (§3.2) enforces "no forks" in the file itself. The key rule is enforced in
    the transaction.
  - Revisions are not part of the key: a row keeps its number across revisions (parent row 41). A reworded
    question or default is caught by checks 15 and 15a, and the owner then supersedes (A-3).
  - Check 14 requires the row to be awaiting. Once a row is transcribed (`CONFIRMED` and off "Rows the human
    must confirm"), the planner must re-open it before the owner can supersede its answer. PBI-032's page
    text should say so.
- **Idempotency without a key header.** A repeated POST, whether a double click, a client retry or a replayed
  capture, is refused with 409 `duplicate` or `supersedes`, and stores nothing. At most one answer per intent
  is stored, and the page's reload shows the stored one through the snapshot. PBI-032's AC-B2 ("never retry by
  itself") stays correct but is no longer load-bearing.
- **When the lock is taken (SG31-7).** `_post_answer` runs checks 1 to 15a with no lock held, so a slow or
  refused request never blocks another answer. Only then does it take the process-wide answers
  `threading.Lock`.
- **Atomicity.** Under the lock, `_post_answer`:
  1. **if the file does not exist and `supersedes` is given,** answers 409 `supersedes` and creates nothing
     (SG31-8). Nothing can be superseded in an empty store;
  2. otherwise opens a short-lived connection through the module-level seam `_connect_answers(path)`
     (`isolation_level=None`, `timeout=BUSY_TIMEOUT`), creating the parent folder, and runs
     `create_answers_schema`;
  3. runs `BEGIN IMMEDIATE`;
  4. reads the key's chain with `SELECT id, supersedes, doc FROM answers WHERE project_id = ?`, filtering in
     Python;
  5. inserts one row through the module-level seam `_insert_answer(conn, row)`, which runs a parameterised
     `INSERT` (no `OR REPLACE`) from `records.to_row('answer', id, doc)`, then runs `COMMIT`;
  6. closes the connection in `finally`.

  - Any exception rolls back when `conn.in_transaction` (the `create_schema` pattern) and gives check 17's 503.
  - `_insert_answer` is the seam AE-20 patches to raise after the `INSERT` and before the `COMMIT` (SG31-13).
  - `BEGIN IMMEDIATE` also serialises a second process on the same file, which CLAUDE.md forbids anyway.
  - **201 is sent only after `COMMIT` returns.**
- **Append-only.** No `UPDATE` or `DELETE` exists (§3.2). Changing an answer means a new record with
  `supersedes`.

### 3.7 Snapshot and events (AC-A5)

- **`State` gains:**
  - the answers path;
  - an `answers` map (`answers/<id>` → `{"kind": "answer", "id", "doc"}`);
  - a `dirty` flag;
  - a read-only answers connection, opened as `file:<path>?mode=ro` with `uri=True` and
    `PRAGMA query_only = 1`;
  - a `db.Changes` on that connection's `data_version`.
- **Reader states (SG31-8).**
  - **Absent**, or present with `user_version` 0 or no `answers` table: "not created yet". This is silent. The
    reader holds no connection and retries on the next refresh, as `open_read` does (`local/server.py:97-104`).
    It covers the moment between the writer's `connect` and the commit of `create_answers_schema`.
  - **Newer than `ANSWERS_SCHEMA_VERSION`, corrupt or unreadable:** answers are left out of the snapshot, with one
    `warn` per distinct reason (exception type and SQLite error name only; §3.8). The connection is closed.
  - **Every failed open is retried on the next refresh.** Nothing is cached as permanently failed.
- **Re-reading.** `_refresh_locked` re-reads every answer (`SELECT id, doc FROM answers ORDER BY id`,
  `records.from_row`, a bad row skipped with a `warn` as `_stored_fallback` does) when any of these holds:
  - this is the first successful open;
  - `dirty` is set;
  - the answers `data_version` changed.

  The served snapshot is the board records merged with the answers. The version is bumped when either part
  changed. Unavailable answers never block board reads. POSTs then get check 17's 503.
- **The server signals the hub itself (SG31-14).**
  - After a commit, `_post_answer` sets `state.dirty` under the state lock and calls `Hub.notify()`.
  - Each watcher gets **its own** `wake` Event, created with its `stop` Event in `register()`, and waits on
    `wake.wait(poll_interval)`, clearing it after each wake.
  - `notify()` sets the current watcher's `wake` under the hub lock.
  - `unregister()` sets both `stop` and `wake` when it stops a watcher, so the watcher exits at once rather than
    after `poll_interval`.
  - A dying watcher and its replacement never share an Event, so neither can clear a notify meant for the other.
  - A stored answer is therefore pushed at once, not on the next `data_version` poll, which watches only the
    board database.
- **The board database's own `answers` table stays invisible,** because `read_snapshot` still iterates
  `records.TABLES` only and `answer` is not in it. With no stored answers, the snapshot has no `answers/` key.
- **Tests re-keyed:** `test_server.py:302-322` and `test_server_live.py:58-72` assert "no record read from the
  board database's `answers` table":
  - no `answers/` path in the records;
  - the sentinel text absent.

  They no longer assert that the bare substring `answers` is absent, since the page marker and stored answers
  now contain it.

### 3.8 Logging (AC-A7)

- **One line per accepted or refused answer,** through `warn()` (stderr, so `server.log`):
  - `server: answer stored <id> (project <pid>, row <n>)`
  - `server: answer refused: <reason> (project <pid|->, row <n|->)`
- `<reason>` comes from the fixed vocabulary in §3.4.
- `<pid>` is printed only when it is a configured project id. `<n>` is printed only when `row` passes
  `records`' `int` rule (`local/records.py:151`, `bool` excluded) and `1 <= row <= 99999` (SG31-r2-5).
  Otherwise the log prints `-`.
- **Refusals at checks 1, 2 and 2a on `/api/answers`** also write an `answer refused: host|origin|site
  (project -, row -)` line, beside today's repr-escaped Host, Origin or Sec-Fetch-Site line, so every refused
  answer has its line (AC-A7). The body is never read for them.
- **Idle keep-alive timeouts are not logged (SG31-r2-3).** With `Handler.timeout = 30`, the framework calls
  `log_error("Request timed out: %r", e)` for every idle browser connection, which would add a line per page
  load. `Handler.log_error` is overridden to drop exactly that message. Every other `log_error` call still
  reaches `log_message` (A-20).
- **On the answers path, never logged:**
  - the token;
  - `answer`, `note`, `questionSha`, `resolutionSha` and `specPath`;
  - `Content-Type`, `Content-Length` and `X-Dispatch-Token` header values;
  - `validate()`'s and `to_row()`'s error strings, which can quote values through `%r` (`local/records.py:219`,
    `:256`);
  - `str()` of any exception.
- **The 503 (check 17) line** adds the exception's type name and, for `sqlite3.Error`, its `sqlite_errorname`
  only. For example: `server: answer refused: unavailable (project p, row 28): OperationalError SQLITE_BUSY`.
- **An unexpected exception inside `_post_answer`** is caught there. It gets today's 500 line, and one log line
  holding the exception type and the traceback's frames as `file:line in function`, from
  `traceback.extract_tb`, **without the exception message** (SG31-10). The generic `traceback.print_exc` path in
  `_handle` (`:375-376`) stays for the other routes.
- **Exceptions to "nothing a caller chose reaches the log",** all kept:
  - the Host and Origin refusal lines, and the new Sec-Fetch-Site line, which log the header `repr`-escaped
    (`local/server.py:396`, `:411`);
  - `log_request`'s request line, which is also `repr`-escaped (`:556-560`).

  A POST's request line is `POST /api/answers HTTP/1.1`, and **the token never travels in a URL**.

### 3.9 Error shape

- **Every refusal** goes through `_respond_plain`: one line, `text/plain; charset=utf-8`, `Cache-Control:
  no-store`, the three security headers and `Connection: close`. On `/api/answers` it also carries
  `X-Dispatch-Reason`. Closing the connection also discards any body left unread by checks 3 to 7, so a refused
  body cannot be read as a second request.
- The lines are the fixed strings in §3.3 and §3.4. None contains request data.
- A handler exception gives today's `500` line (§3.8).

### 3.10 Nonce content-security policy (AC-A9)

- `CSP` becomes a template whose `script-src` is `'nonce-<N>'` alone: no `'self'` and no `'unsafe-inline'`.
  Every other directive is unchanged. `style-src` keeps `'unsafe-inline'`, since the page uses `style=`
  attributes (`site/index.html:293`, `:300`).
- **`N` is `secrets.token_urlsafe(16)`, fresh for every `GET /` or `HEAD /` response (A-1).** That is stricter
  than the parent's "per-start" and still satisfies its test. `_serve_page` passes `N` to
  `_security_headers(csp=N)` and to `_wrap_page`.
- **`GET /` and `HEAD /` also send `Cross-Origin-Opener-Policy: same-origin`** (SG31-15), so a page that opens
  the board keeps no handle to navigate it.
- `_wrap_page(content, nonce, token)`:
  - writes the marker as `<script nonce="N">window.__DISPATCH_LOCAL__=<json>;</script>`;
  - the JSON comes from `json.dumps({"snapshot": "/api/snapshot", "events": "/api/events", "answers":
    "/api/answers", "token": <Server.token>, "version": 1}, separators=(',', ':'))`;
  - adds ` nonce="N"` to every `<script` start tag in the page body (`re.sub(r'<script(?=[\s>])', …,
    flags=re.IGNORECASE)`).
  - `version` stays 1: the change is additive, and the page ignores unknown keys (`site/index.html:1474-1476`).
- **Why it does not break the page.** The page has one `<script>` and no inline handler, `javascript:` URL,
  `eval` or `new Function` (§2). Scripts inserted with `innerHTML` never run in any case. `connect-src 'self'`
  already covers `fetch('/api/answers')`.
- **Tests that change (SG31-6):**
  - `test_server.py:62` and `:102`, which pinned the exact marker string, become JSON-parsed checks of the
    marker's keys, as `test_deploy_e2e.py:185-188` already does.
  - `test_server.py:104-109` ("the file's own bytes … are the body") becomes: the body equals the source, less
    the hoisted title, with ` nonce="N"` inserted into each `<script` start tag.
  - A guard is added: the number of `<script` start tags in the source equals the number of `nonce="N"` in the
    body, so a `<script` inside a JS string would be caught.
  - `test_deploy_e2e.py` itself is unchanged: it reads `snapshot` and `events` only.
- `tests/page.test.mjs` sets its own marker (`:76`) and is not edited. It must pass unchanged.

### 3.11 `local/answers.py` (AC-A6)

- **Usage:**
  - `python local/answers.py list [--project ID] [--config PATH]`
  - `python local/answers.py verify <spec path> [--config PATH]`
- **Opening the file.** The path comes from `board_config.answers_path(cfg)`. The network-path guard applies
  (exit 2). The file is opened with `file:<path>?mode=ro` and `uri=True`, then `PRAGMA query_only = 1`. A
  `user_version` newer than `ANSWERS_SCHEMA_VERSION` exits 2. `user_version` 0, or no `answers` table, reads as
  empty. The file is never created: when it is missing, `list` prints `no answers recorded (<path> does not
  exist)` and exits 0.
- **Output encoding.** Output is UTF-8: `sys.stdout.reconfigure(encoding='utf-8')`, since the console code page
  on this PC may not be UTF-8 (A-17).
- **Names.** No function in the module is named after a launcher in
  `test_deploy_inspection.py:60-63` (`run`, `call`, `system` and so on). The commands are `cmd_list` and
  `cmd_verify`.
- **`list`:**
  - prints every answer, oldest first (`at`, then `id`);
  - `--project ID` filters to one project, and exits 2 when the id is not in `projects[]`;
  - each answer is one header line and two indented lines, with text printed through
    `json.dumps(..., ensure_ascii=False)` so the quoting is unambiguous:

    ```
    <id>  <at>  <projectId>  assumption  <specPath> rev <n>  row <n>  <choice>[  supersedes <id>][  SUPERSEDED by <id>]
        answer: "<answer>"
        note: "<note>"
    ```
- **`verify <spec path>`:**
  - **Resolving the project.** The spec path is matched to a project whose `join(repoPath, docs.spec)` is the
    same file (`normcase(realpath(...))`). No match exits 2 with `not the spec of a configured project`.
  - **Reading the spec.** It is read with `io.open(..., encoding='utf-8')`, universal newlines, as the exporter
    reads it.
  - **Lines and cells: derive's own rules (SG31-4).**
    - The ledger block is `derive.section(spec, '## Assumptions & open questions')`, and the Plan-gate block is
      `derive.section(spec, '## Plan-gate record')`, which includes its sub-sections.
    - Each block is split into lines with `str.splitlines()`, as `derive.table()` does.
    - A table line is one that starts with `|` and is not a separator row (`^\|\s*-`). Its cells are
      `[derive.clean(c) for c in re.split(r'(?<!\\)\|', line.strip())[1:-1]]`, which is `derive.table()`'s
      per-line rule without its header drop.
    - Substring checks run on the **raw** line.
  - **Citations.** A citation is `answer:<32 lowercase hex>` not followed by another hex digit.
  - **Where a citation may appear.** Each must be either:
    - on a table line of the ledger block: the **ledger form**; or
    - on any line of the Plan-gate block: the **Plan-gate form**.
  - **Checks for every citation,** each failure a mismatch line:
    1. the id exists in the answers file;
    2. `type == "assumption"`;
    3. `projectId` is the resolved project;
    4. `specPath` equals that project's `docs.spec`.
  - **Ledger form, which is current state:**
    - the answer is not superseded. A stale answer in the ledger is unfaithful;
    - the first cell equals `str(row)`;
    - the fourth cell, with `*` removed, is `CONFIRMED`;
    - `sha256(second cell)` equals `questionSha`, so the row's question is still the one answered (A-11);
    - for `choice == "accept"`, `sha256(third cell)` equals `resolutionSha`, so the Resolution is still the
      default the owner accepted (SG31-1). An Override needs no such check, since its Resolution becomes the
      owner's text;
    - the raw line contains `answer:<id> (Accept)` or `answer:<id> (Override)` matching `choice`;
    - for an Override, the raw line contains `answer:<id> (Override) "<answer>"`, with every `|` in the answer
      written `\|`.
  - **Plan-gate form, which is append-only history (SG31-5):**
    - the raw line contains `Row <row>: answer:<id> (Accept)` or `Row <row>: answer:<id> (Override)
      "<answer>"`. On a table line, `|` is written `\|`;
    - **a superseded answer is accepted only from an earlier revision (SG31-r2-1).** The spec's current
      revision is read with `spec_docs`' own rule, `^revision:\s*(\d+)` (multiline, the first match). When
      the cited answer's `specRevision` is **lower** than that, the line prints `ok … (superseded by <id>)`,
      since the Plan-gate record keeps earlier revisions' lines as they were (`dispatch-board.md:598`).
      Otherwise, including a spec with no readable revision, it prints `MISMATCH line <L> answer:<id>:
      superseded`. The current revision's lines must cite each row's current answer.
    - Not adopted: also accepting a superseded citation whose successor is cited later in the same block. The
      current revision's lines are editable, so the planner corrects them in place.
  - A citation anywhere else fails with `cited outside the ledger and the Plan-gate record`.
  - **Output.** The first line is `verify: <spec> (project <pid>): <N> citations, <M> mismatches`. Then comes
    one line per citation, either `ok line <L> answer:<id> row <n>[ (superseded by <id>)]` or `MISMATCH line
    <L> answer:<id>: <field>`. Answer and note text are never printed.
  - **Exit codes:** 0 with no mismatch (including 0 citations), 1 with any mismatch, 2 for usage, config, spec
    or answers-file errors.
  - `verify` checks that a transcription is faithful, not who gave the answer (ADR-0002). PBI-034 extends it for
    `planApproval` and `conditionsAccepted`.
- **Imports.** `answers.py` imports `derive`, `board_config`, `db` (for `resolve` and `network_path`),
  `records` and `schema`, with the `sys.path` set-up that `server.py` uses (`local/server.py:21-25`). All are
  already on `test_deploy_inspection.py`'s exporter list (`:39`).

### 3.12 `CLAUDE.md` and `README.md` (AC-A10)

**`CLAUDE.md` "Answers are the owner's"** (today `:53-55`) is replaced with:

> - **A board answer counts as the owner's, whoever gave it.** The owner decided this on 2026-09-19: "Just
>   procees as if it were me" (spec row 32, ADR-0002). Answers are given only on the board this PC's local
>   server serves (row 25). Each one is stored by `POST /api/answers` in `out/local/answers.db`
>   (`local.answersPath`), which only the server writes.
> - **Agents still do not answer for the owner.** No agent:
>   - POSTs to `/api/answers`;
>   - drives the board's answer controls;
>   - opens the answers file with anything but `python local/answers.py`;
>   - cites an `answer:<id>` it has not read with `python local/answers.py list`.
> - **Build, test, smoke-test and verify work on answers** runs a throwaway server on a port other than 8765,
>   with a temporary answers path: `serve(..., answers_path=<tmp>)`, `main(..., answers_path=<tmp>)`, or a
>   temporary config. It never touches port 8765 or the real `answers.db`. In `local/tests`, every direct
>   `server.serve` or `server.main` call passes `answers_path`, and `test_answers_isolation.py` fails when one
>   does not.
> - **Transcription.** No process writes an answer into a repo file. The planner or orchestrator transcribes it:
>   1. Read the answer with `python local/answers.py list --project <id>`. Only an answer not marked
>      `SUPERSEDED` is transcribed.
>   2. **Ledger row.** Set Status to `CONFIRMED`. In the Source cell, write `Owner, <date>, on the board:
>      answer:<id> (Accept)` or `… answer:<id> (Override) "<answer, with | written \|>"`.
>      - For an Accept, leave the Resolution cell exactly as it was: `verify` checks it is the default the owner
>        accepted.
>      - For an Override, the Resolution becomes the owner's answer.
>      - The note may follow as `note: "…"`, with each newline written as a space (it is not checked).
>      - Take the row off "Rows the human must confirm".
>   3. **Plan-gate record.** Write `Row <n>: answer:<id> (Accept)` or `Row <n>: answer:<id> (Override)
>      "<answer>"`. The current revision's lines cite the row's current answer, and are corrected in place
>      when it is superseded. Never edit an earlier revision's lines: `verify` accepts a superseded answer
>      there only when it was given at an earlier revision.
>   4. Run `python local/answers.py verify <spec>` and quote its whole output in the Plan-gate record or the
>      commit. A non-zero exit means the transcription is not done.
> - `refresh.py`'s answers guard stays until the refresher is removed (see the answers guard below).

**`README.md`**, under "Running the board on this PC" (`README.md:22`), gets one paragraph:

- `local.answersPath` and its default;
- that the file is written only by the server, is git-ignored under `out/`, and is not backed up;
- the two `answers.py` commands.

`CLAUDE.md`'s "The local app on this PC" (`:124-173`) also changes:

- the sentence "The collector is the database's only writer; the server opens it read-only" gains "…and the
  server alone writes `answers.db`";
- the log bullet (`:145-149`) gains the per-answer line and the Sec-Fetch-Site refusal line.

These are the only other doc edits.

### 3.13 `local/server.py` module docstring

The docstring's "It is a reader only: it writes no record, no table and no schema, and creates no file of its
own" (`:1-4`) becomes: "It reads the board database only. Its one write is an answer, into its own answers
file, through `POST /api/answers`." The funnel sentence (`:8-10`) gains the Fetch Metadata gate.

## 4. Threat model (AC-A8)

Method: the `security-agents:threat-modeling` skill's four questions, applied to the change and its blast
radius.

**Scope.** Three attackers are in scope:

- a malicious web page open in the owner's browser (cross-site requests and DNS rebinding);
- a script injected into the board page through rendered data;
- a stale or leaked token.

**Out of scope** (owner's row 32; ADR-0002): any agent or process on this PC answering as the owner, by
driving a browser, sending its own POST with the page's token, or writing the file. The audit for that is
PBI-033's.

### 4.1 What are we building: entry points, boundaries and assets

| Entry point or boundary | Crosses | Asset |
|---|---|---|
| `GET /` (serves the token and the nonce) | browser ↔ 127.0.0.1 server | the token |
| `POST /api/answers` | browser page → server → `answers.db` | the answer record: the owner's decision, which with row 34 can pass a plan gate once PBI-034 ships |
| `GET /api/snapshot`, `GET /api/events` (now carrying answers) | server → browser | the answer text; the stream slots (`MAX_STREAMS = 8`) that carry pushes |
| `answers.db` on disk | server (writer) → `answers.py` (reader) | the stored answers |
| `answers.py verify` | answers file plus spec file → planner's quoted output | faithfulness of the transcription |

### 4.2 Threats and controls

| # | Threat (STRIDE) | Control | Status |
|---|---|---|---|
| T1 | A cross-site HTML form or `no-cors` fetch POSTs an answer (Spoofing) | Its Origin is foreign → 403 (check 2). `Sec-Fetch-Site: cross-site` → 403 (2a). A form cannot send `application/json` → 415. It has no token → 403 | designed |
| T2 | A cross-site `fetch` with a JSON body (Spoofing) | Needs a CORS preflight. `OPTIONS` with a foreign Origin → 403, and no `Access-Control-Allow-*` is ever sent (FR-179), so the browser never sends the POST | designed |
| T3 | DNS rebinding: `evil.example` resolves to 127.0.0.1 and its script reads `GET /` for the token, then POSTs (Spoofing, Information disclosure) | The Host `evil.example:8765` is refused 403 on **every** request, including `GET /`, so the token is never served to it (FR-177, check 1) | designed |
| T4 | Opaque origins: a sandboxed iframe or `file:` page sends `Origin: null` | Not an allowed origin → 403 | designed |
| T5 | A script injected into the page (a rendering bug in `md()` or `esc()`) runs and POSTs with the token | Nonce CSP with no `'unsafe-inline'` and no `'self'` blocks inline handlers (`<img onerror>`) and injected script elements. The nonce is 128 bits and fresh per response. Exfiltration routes are closed: `connect-src 'self'`, `img-src 'self' data:`, `form-action 'none'`, `base-uri 'none'`, `frame-ancestors 'none'` | designed |
| T6 | Injected markup without script: fake text or a fake button that misleads the owner into answering (Tampering) | Nothing can POST without script, and `form-action 'none'` stops forms. Misleading text rendered beside the real controls remains | **residual R1** |
| T7 | A stale token after a server restart | 403 with "reload the page". Nothing stored | designed |
| T8 | A leaked token: copied, cached or logged | Never logged or placed in a URL (§3.8). The page is `Cache-Control: no-store`. A leaked token alone does not pass checks 1, 2 and 2a from any web page. It lives until the server restarts. A local process holding it is row 32's scope | designed; the local part is out of scope |
| T9 | Guessing or timing the token | 256 bits from the OS CSPRNG, compared with `hmac.compare_digest` (§3.3) | designed |
| T10 | Server-set fields or unknown fields forged in the body (Tampering, Elevation) | Checks 9 and 10: closed key set, server sets `id`, `at`, `writer` and `surface` | designed |
| T11 | Path or file probing through `specPath` or `projectId` (Information disclosure) | Both are compared as strings with the config. The server opens no path taken from a body | designed |
| T12 | An answer bound to the wrong question or default (a stale page, a reworded row, an edited default, a new revision) | Checks 13 to 15a: current revision, awaiting row, question hash, default hash. `verify` re-checks both hashes on the transcribed ledger row | designed |
| T13 | Replay or duplicate POSTs (Tampering) | The chain rule (§3.6) → 409. At most one current answer per row | designed |
| T14 | SQL injection | Parameterised statements only. Table and column names are constants from `ANSWER_TABLES` | designed |
| T15 | Oversized or slow bodies, or request smuggling (Denial of service) | `Content-Length` required and ≤ 16 KiB, `Transfer-Encoding` refused, duplicate framing headers refused, a 5-second **wall-clock** body deadline, a 30-second header-phase timeout, `Connection: close` on every refusal. The answers lock is taken only after checks 1 to 15a | designed |
| T16 | A web page holds stream slots or connections with no-cors GETs such as `<img src=".../api/events">`, which carry no Origin (Denial of service; SG31-3) | The Fetch Metadata gate (2a) refuses `cross-site` and `same-site` requests on every route, before a stream is registered. `GET /` navigation stays allowed. It relies on the browser sending `Sec-Fetch-Site`, which every browser the owner uses does (A-19) | designed; the gap in browsers without Fetch Metadata is residual R2 |
| T17 | Echo or log injection of attacker text (Information disclosure, Repudiation) | Fixed refusal lines, a fixed reason vocabulary, project and row logged only in known forms, no exception messages on the answers path, and the kept header lines `repr`-escaped | designed |
| T18 | Repudiation: "I never answered that" | One log line per stored or refused answer. The stored record carries its time. Who clicked is not provable (row 30) | designed; the identity part is accepted by the owner (row 32) |
| T19 | A second writer on the board database, or answers pruned by the collector | Start refused when the two paths are one file. The collector never names the answers path (inspection test) and never calls `answers_path()`. There is no DELETE or UPDATE on answers | designed |
| T20 | An answers file on a network share | Start refused (FR-96) | designed |
| T21 | Clickjacking the answer controls, or an opener navigating the board | `frame-ancestors 'none'` and `X-Frame-Options: DENY` (today's); `Cross-Origin-Opener-Policy: same-origin` (new) | designed |
| T22 | An unfaithful transcription (the wrong row, text or choice, a changed default, or a superseded answer in the ledger) | `verify` (§3.11) | designed |

**Assumed controls: none.** Every control above is specified in §3 and tested in §6.

### 4.3 Residual risks

These go to the owner at the external-review gate, which is the owner's explicit approval of this PBI:

- **R1:** injected markup can mislead without running script. It needs an escaping bug in the page first
  (NFR-22 requires `esc()`), and PBI-032's AC-B5 asserts that answer controls render no data through `md()`.
- **R2 (rewritten per SG31-3).** Two parties can still hold stream slots or connections:
  - **a web page, in a browser that sends no Fetch Metadata headers:** any web page open in the owner's browser,
    not only a local process, can hold the 8 stream slots with no-cors GETs, so a stored answer is not pushed
    until a slot frees. The owner's current browsers send `Sec-Fetch-Site`, so the gate closes this for them;
  - **any process on this PC,** which can already stop the server.
- **Row 32's own residual:** any agent on this PC can answer as the owner. The owner accepted it on 2026-09-19.

### 4.4 Surface for the next diff

Future models of this surface start from this list:

- **Routes:** `GET /`, `/api/snapshot`, `/api/events`; `POST /api/answers`.
- **Gates, in order:** Host, Origin, Sec-Fetch-Site; then, on the answers route, framing, type, token.
- **Marker keys:** `snapshot`, `events`, `answers`, `token`, `version`.
- **Files:** `databasePath` (server reads), `answersPath` (server reads and writes; `answers.py` reads).

PBI-034 adds two answer types and git reads to this surface, and re-opens T10 to T12 for them.

## 5. Files

**Changed (all inside `allowed_areas`):**

- `local/server.py`;
- `local/records.py` and `local/records.shapes.json`;
- `local/schema.py`: the added answers functions only;
- `local/answers.py`: new;
- `exporters/board_config.py`: the new `answers_path()` only;
- `CLAUDE.md` and `README.md`;
- `local/tests/**`:
  - `server_support.py`, `test_deploy_e2e.py`, and the six direct `server.main` calls in `test_server.py` gain a
    temporary answers path;
  - `test_server.py`, `test_server_live.py` and `test_records.py` are edited as §3 names;
  - `test_config_local.py` gains an `AnswersPath` class, and its existing assertions are unedited;
  - new: `test_answers_endpoint.py`, `test_answers_cli.py`, `test_answers_isolation.py` and
    `test_fetch_metadata.py`, plus an inspection class in `test_deploy_inspection.py`.

**Not changed:**

- `board.config.json` (A-10);
- `site/**` and `tests/page.test.mjs` (blocked; they must pass unchanged);
- `local/collector.py`, `local/db.py` (imported, never edited) and `local/deploy/**`;
- every other `exporters/**` file (`derive.py` is imported by `answers.py`, never edited).

**Outside `allowed_areas`, needed: nothing.**

## 6. Acceptance criteria

| # | Maps to | Criterion |
|---|---|---|
| **AE-1** | AC-A1 | `records.SHAPES['answer']` holds exactly §3.1's fields (including `resolutionSha`), enums and `maxLength`. `records.TABLES` is byte-for-byte as at the base. `records.ANSWER_TABLES` and the `_DOC_FIELD` entry are §3.1's. `local/records.shapes.json` equals `--write-shapes` output (the `test_records.py:384-408` checks, kept) |
| **AE-2** | AC-A1 | `store_path('answer', 'a'*32)` returns `'answers/' + 'a'*32`. An id that is not 32 lowercase hex characters raises. `to_row` and `from_row` round-trip a valid answer, and `to_row`'s `project_id` column holds `projectId`. `validate` accepts `note` and `answer` of 0 and 2,000 characters and rejects 2,001, and rejects a missing `resolutionSha`, `choice: "maybe"`, `writer: "agent"`, `surface: "store"` and `type: "other"`. `test_records.py:187` and `:550` use a still-unknown kind (`'nonesuch'`), and `:69` and `:74` include `answer` |
| **AE-3** | AC-A2 | `schema.answers_ddl()` and `create_answers_schema()` create `answers` plus the two indexes, idempotently, and refuse a newer `user_version`. Every name in `answers_ddl()` matches `\A[a-z_]+\Z`. `schema.DDL`, `SCHEMA_VERSION` and `create_schema` are unchanged, and `test_schema.py:88-93` passes **unedited** |
| **AE-4** | AC-A2 | `board_config.answers_path({})` is `'out/local/answers.db'`. A blank or non-string value raises naming `local.answersPath`, and `~` is expanded. `board_config.local()` returns exactly its two keys (the `test_config_local.py:12-42` assertions pass unedited). A collector `--once` pass with `answersPath: 5` in its config commits normally |
| **AE-5** | AC-A2, FR-96 | `main()` exits 2 naming the path, and `serve()` raises `db.NetworkPath`, for `answersPath` `\\nas\share\answers.db`, with no socket bound and no file created. It also exits 2 when `answersPath` and `databasePath` resolve to one file |
| **AE-6** | AC-A2 | Starting a server, `GET /`, `GET /api/snapshot` and every refused POST create no answers file. This includes a POST naming `supersedes` against a missing file, which gets 409 `supersedes`. The first accepted POST creates it. `test_server.py:326`'s board-file-unchanged and `query_only` checks hold with a stored answer in the same test |
| **AE-7** | AC-A2 | An inspection test (AST, in `test_deploy_inspection.py`'s style) shows `local/collector.py`, `local/db.py` and `local/tabs.py` have no string literal containing `answers.db` or `answersPath`, no subscript or attribute named `answersPath`, and no call to `answers_path`. It also shows that `collector.py`'s `board_config.local(...)` results are subscripted only with `'databasePath'`. A collector `--once` pass with `answersPath` pointed at a temporary path leaves that path absent |
| **AE-8** | AC-A2 | `answers.py list` and `verify` leave an existing answers file's bytes and mtime unchanged, create no `-journal` file, and create no file when the path is missing |
| **AE-9** | AC-A2, row 46 | An inspection test finds no SQL literal in `local/server.py` or `local/answers.py` that contains `DELETE`, `UPDATE`, `DROP` or `REPLACE` (case-insensitive) |
| **AE-10** | AC-A3 | A valid POST (a fixture assumptions tab with row 28 ASSUMED, and a spec tab at revision `"6"`) returns 201 with `{"kind": "answer", "id", "doc"}`. `doc.id` is 32 hex characters, `doc.at` is a `+00:00` datetime, `writer` is `"page"` and `surface` is `"local"`. The same record is in the file. A row with `needsYou: true` and status `CONFIRMED` is also accepted. An Override is accepted with the current `resolutionSha` |
| **AE-11** | AC-A3 | POST `/api/answers` with Host `attacker.example`, with two Host headers, with no Origin, with Origin `https://attacker.example`, with two Origin headers, and with Origin `null`: each gets its 403 line, and nothing is stored |
| **AE-12** | AC-A3 | Each of these gets its §3.4 status and line, with no body byte read (asserted with a body sent only after the response, on a raw socket), and nothing stored: no `Content-Length`; `Transfer-Encoding: chunked`; both headers; two `Content-Length` headers; `Content-Length: +5`, ` 5` and `1_0`; 16,385; `text/plain`; `application/json; charset=latin-1`; `application/json; charset="utf-8"`; `application/json; x=1`; two `Content-Type` headers. `Application/JSON` and `application/json ; Charset=UTF-8` pass check 6. A stale token with a 12 KiB body sent in two writes, the second after the response, gets its 403 and `X-Dispatch-Reason: token` with no connection reset, and the drained bytes appear in no log (SG31-r2-2) |
| **AE-13** | AC-A3 | A missing token, a wrong token, a token with a non-ASCII byte, two token headers, and a previous server start's token each get 403 with the "reload the page" line. The comparison goes through `hmac.compare_digest` (asserted with a patch) |
| **AE-14** | AC-A3, AC-A1 | Each of these gets 400 and stores nothing: <ul><li>a body naming `id`, `at`, `writer` or `surface` (its own line);</li><li>an unknown key; a duplicate key; `NaN`; a nested value; a 5,000-digit integer;</li><li>invalid UTF-8; a lone-surrogate escape;</li><li>in `answer`: a C0 or C1 character, `\n`, U+0085, U+2028, U+2029, U+202E, U+2066, U+200E, U+200F or U+061C (`\n` is allowed in `note`, and U+2028 is refused there);</li><li>`answer:` followed by 32 hex characters, in `answer` and in `note`;</li><li>`accept` with a non-empty `answer`; `override` with a blank `answer`; 2,001 characters</li></ul> |
| **AE-15** | AC-A3 | An unknown `projectId`, and a `specPath` differing from `docs.spec` in content or case, each get 400 `project`. No file named in the body is opened (asserted by patching `io.open` and `os.stat` to fail on the posted path) |
| **AE-16** | AC-A3 | Each gets its §3.4 status: no assumptions tab (409 `revision`); a board database not yet written (503); `specRevision` 5 against `"6"` (409); a row number not present, and a `RESOLVED` row with `needsYou: false` (409 `row`); a `questionSha` of other text (409 `question`); a `resolutionSha` of other text, for Accept and for Override (409 `resolution`) |
| **AE-17** | AC-A3 | Across AE-11 to AE-16, AE-18 to AE-20, and a forced 500 (with `_insert_answer` patched to raise `ValueError` carrying the sentinel): a unique sentinel placed in every body field appears in no response body, no response header and no captured stderr. The answers file's row count is unchanged after each refusal. Every refusal on `/api/answers` carries `X-Dispatch-Reason` equal to its §3.4 reason |
| **AE-18** | AC-A4 | `GET`, `HEAD`, `PUT`, `DELETE` and `OPTIONS` on `/api/answers`, with an allowed Origin, give 405. `PATCH` gives 501. Nothing is stored |
| **AE-19** | AC-A4 | A second POST for the same row without `supersedes` gives 409 `duplicate`. One naming the head gives 201. One naming the old head, an unknown id or another row's answer gives 409 `supersedes`. Two concurrent POSTs for one row (two threads released together) store exactly one answer, and get one 201 and one 409 |
| **AE-20** | AC-A4 | With `_insert_answer` patched to run the `INSERT` and then raise, the POST gets 503 `unavailable`, and the file holds no new row. An answers file with `user_version` 2 gives 503 on POST while `GET /api/snapshot` still serves board records. A 503 log line holds the exception type and SQLite error name and nothing else |
| **AE-21** | AC-A5 | After a 201, `GET /api/snapshot` holds `answers/<id>` with kind `answer`. With `poll=30`, an open event stream receives a `change` event whose `set` holds `answers/<id>` within 2 seconds, which shows `Hub.notify`. Closing the last stream stops its watcher within 1 second at `poll=30`, and a stream opened straight after still receives the next answer within 2 seconds. An answers file with `user_version` 0 and no table serves a snapshot with no answers and no warning. The re-keyed `test_server.py:302-322` and `test_server_live.py:58-72` pass, with no `answers/` path and no sentinel read from the board database's own `answers` table |
| **AE-22** | AC-A6 | `list` prints §3.11's format, oldest first, and marks a superseded answer. `--project` filters, and an unknown id exits 2. A missing file prints the no-answers line and exits 0 |
| **AE-23** | AC-A6 | **`verify` exits 0** on a fixture spec holding: <ul><li>a correct Accept ledger row;</li><li>a correct Override row whose answer contains `\|`;</li><li>a ledger row whose question cell contains `\|`;</li><li>a Plan-gate line;</li><li>an earlier revision's Plan-gate line citing a superseded answer, printed `ok … (superseded by <id>)`.</li></ul> **It exits 1, with one `MISMATCH` line each,** for: an unknown id; another project's answer; the wrong row number; a status that is not `CONFIRMED`; `(Accept)` for an override; a changed answer text; a changed question cell; an Accept whose Resolution cell was changed; a superseded answer in the ledger; a superseded answer on a Plan-gate line whose `specRevision` equals the spec's current revision; a citation in Key decisions. **It exits 2** for a spec of no configured project and for a newer-schema answers file. Its output never contains answer or note text |
| **AE-24** | AC-A7 | Captured stderr for one stored and one refused (`question`) POST holds exactly one `answer stored <id> (project p, row 28)` line and one `answer refused: question (project p, row 28)` line. It never holds the token, the answer, the note, `questionSha` or `resolutionSha`. An unknown `projectId` is logged as `project -`, and so are `row: true` and `row: 100000` as `row -`. A POST to `/api/answers` with Origin `https://attacker.example` writes today's Origin line and one `answer refused: origin (project -, row -)` line. An idle keep-alive connection timing out (with `Handler.timeout` patched down) writes nothing |
| **AE-25** | AC-A8 | §4 exists at this spec gate. The PBI's code-review gate runs `review-agents:api-reviewer` beside `review-agents:code-reviewer`, and both reports are in the Evidence |
| **AE-26** | AC-A9 | The `GET /` and `HEAD /` headers' `script-src` is exactly `'nonce-<N>'`, with no `'unsafe-inline'` and no `'self'`, and they carry `Cross-Origin-Opener-Policy: same-origin`. `N` differs between two responses and between two server starts. Every `<script` start tag in the served repository page and in the test page carries `nonce="<N>"` for that response's `N`, and their count equals the source's `<script` count. The marker parses as JSON with `snapshot`, `events`, `answers`, `token` and `version: 1`. `test_server.py:62`, `:102` and `:104-109` are re-keyed as §3.10 says |
| **AE-27** | AC-A9 | `node tests/page.test.mjs` passes unedited. A browser smoke check of a throwaway server (another port, temporary `databasePath` and answers path), per `CLAUDE.md`, loads the board, switches every tab, and shows no CSP violation and no 403 in the console or network log. The evidence names the port and paths |
| **AE-28** | AC-A10 | `CLAUDE.md` holds §3.12's four points (the owner's quote, the agent rule, the throwaway-server rule, and the transcription procedure with `verify`), and `README.md` holds the paragraph |
| **AE-29** | AC-A10 | `server_support.Env.start()`, `test_deploy_e2e.py`'s throwaway config and the six direct `server.main` calls set an answers path inside the test's temporary folder. `test_answers_isolation.py` has two parts: <ul><li>it parses every `local/tests/*.py` (AST) and fails on any `server.serve(...)` or `server.main(...)` call whose `answers_path=` keyword is missing or a literal `None`, unless that call's `config=` is a dict literal with an `answersPath` key (AE-5's calls, whose config carries a network or same-file path);</li><li>it fails if a harness-started server resolves its answers path outside the test's temporary folder.</li></ul> |
| **AE-30** | close-out | Tier 4 (record shapes; parent row 44). The three configured suites are green on the head commit, with numbers quoted, and `records.shapes.json` matches `--write-shapes`. `review-agents:code-reviewer` and `review-agents:api-reviewer` have passed |
| **AE-31** | AC-A3 (SG31-2) | The marker token fullmatches `[A-Za-z0-9_-]{43}`, is the same across two `GET /` calls (at `127.0.0.1` and at `localhost`) on one start, and differs across two starts. With stderr captured for a whole `test_answers_endpoint.py` run, the token never appears in it |
| **AE-32** | SG31-3 | With `Sec-Fetch-Site: cross-site` or `same-site`, each of these gets 403 `forbidden: the request came from another site` and registers no stream: `GET /api/events`, `GET /api/snapshot`, `GET /` with `Sec-Fetch-Mode: no-cors`, and `POST /api/answers`. `same-origin`, `none` and an absent header pass the gate. `GET /` and `HEAD /` with `Sec-Fetch-Site: cross-site`, `Sec-Fetch-Mode: navigate` and `Sec-Fetch-Dest: document` get 200 |
| **AE-33** | SG31-7 | With the body deadline patched to 0.5 s, a client that sends one body byte every 0.2 s gets 400 `incomplete` within 1 s. While that request is pending, a second valid POST for another row gets 201. A client that sends a partial request line and stops is disconnected once `Handler.timeout` (patched down) passes |

## 7. Test plan

TDD per D-9: each AE is written red first. Every server test uses `server_support.Env`, with a temporary board
database, page and answers path. Fixture tabs are written with `Env.write('tab', 'p.assumptions', …)` and
`('tab', 'p.spec', …)`. The config dict carries one project, `p`, with `docs.spec: "docs/spec.md"`. No test
reads `board.config.json`, port 8765 or `out/`.

| File | Class | Covers |
|---|---|---|
| `local/tests/test_records.py` | `Kinds` and the pinned literal (edited, `:69`, `:74`); `Answer` (new); `:187` and `:550` edited | AE-1, AE-2 |
| `local/tests/test_schema.py` | `AnswersSchema` (new); `test_no_answers_table` untouched | AE-3 |
| `local/tests/test_config_local.py` | `AnswersPath` (new); existing assertions untouched | AE-4 |
| `local/tests/test_collector.py` | `--once` with `answersPath: 5`; `--once` with a temporary `answersPath` left absent | AE-4, AE-7 (runtime half) |
| `local/tests/test_server.py` | `Page` (`:44`, `:86`; marker by keys, `:104-109` re-keyed); `IgnoresCollectorState` (`:302`, re-keyed); `NetworkPath` (extended); `NeverWrites` (extended); the six `main` calls given `answers_path` | AE-5, AE-6, AE-21 (half), AE-26 |
| `local/tests/test_server_live.py` | `:58-72` re-keyed; `AnswerPush` (new, `poll=30`, including the watcher-stop case) | AE-21 |
| `local/tests/test_answers_endpoint.py` (new) | `Gate`, `Framing` (raw-socket cases), `ContentType`, `Token`, `Body`, `Binding`, `Chain` (including the two-thread race), `Atomicity` (through the `_insert_answer` and `_connect_answers` seams), `NoEcho`, `Log`, `Methods`, `SlowClient` | AE-10 to AE-20, AE-24, AE-31, AE-33 |
| `local/tests/test_fetch_metadata.py` (new) | the Sec-Fetch-Site gate on every route | AE-32 |
| `local/tests/test_answers_cli.py` (new) | `List`, `Verify`, `ReadOnly`. Answers are created through a throwaway server's POST, never by hand-built SQL, so the file is the server's | AE-8, AE-22, AE-23 |
| `local/tests/test_answers_isolation.py` (new) | the AST scan and the harness guard | AE-29 |
| `local/tests/test_deploy_inspection.py` | `AnswersFile` (new): collector never names it; no DELETE, UPDATE, DROP or REPLACE; `answers.py` passes every existing scan | AE-7, AE-9 |
| `local/tests/test_deploy_e2e.py` | config gains a temporary `answersPath` (`:89`); marker check unchanged | AE-29 |
| `tests/page.test.mjs` (blocked: run, not edited) | unchanged | AE-27 |
| Browser smoke check (evidence, not a suite) | a throwaway server, per `CLAUDE.md` | AE-27 |

## 8. Assumptions and open questions

| Row | Question | Status | Answer, or default, impact and rating |
|---|---|---|---|
| R-1 | Does the gate already cover Host, Origin and CORS for a new POST route? | RESOLVED | Yes. `_handle` runs `_host_ok` and `_origin_ok` before `_route` for every method (`local/server.py:361-368`, `:382-414`), and no CORS header is sent (`local/tests/test_server.py:170`). A no-cors GET without Origin also passes today (`:404-409`), hence §3.3's Fetch Metadata gate |
| R-2 | Is the board database opened read-only, and does the snapshot read only `records.TABLES`? | RESOLVED | Yes (`local/server.py:83-108`, `:127-153`) |
| R-3 | Can the nonce CSP break the page? | RESOLVED | No. One `<script>` (`site/index.html:266`), no inline handler, `javascript:` URL, `eval` or `new Function` (grep at `1cc0716`), and the page reads only `snapshot` and `events` from the marker (`:1474-1476`). One server test pins the page bytes and is re-keyed (`local/tests/test_server.py:104-109`) |
| R-4 | What is the exported assumption row, and what does "awaiting" mean? | RESOLVED | `{n, question, resolution, …, needsYou}` from `exporters/derive.py:1126-1133`. Awaiting means `needsYou` or `status === 'ASSUMED'` (`site/index.html:916`). The spec tab's `revision` is a string (`exporters/derive.py:1163`) |
| R-5 | Would the tests touch the real answers file? | RESOLVED | Yes, as they are. The two harnesses and six direct `main` calls pass a config with no answers path (`local/tests/server_support.py:273`; `local/tests/test_deploy_e2e.py:89`; `local/tests/test_server.py:527-580`). All are changed, and AE-29 guards them |
| R-6 | Where does the server's log go, and does it log headers or bodies? | RESOLVED | stderr, captured by the wrapper into `out/local/logs/server.log` (`local/deploy/run_local.py:1-20`; `CLAUDE.md:145-149`). Only the request line and the Host and Origin lines are logged, all `repr`-escaped (`local/server.py:396`, `:411`, `:556-563`) |
| R-7 | Does anything delete `answers.db`? | RESOLVED | No. The collector deletes only its temporary folder and board rows (`local/collector.py:447-459`; `local/db.py:165-166`). The exporters delete only under `out/sessions`, `out/runs`, `out/projects` and `out/projectTabs` (`exporters/export_sessions.py:276-278`; `exporters/export_board.py:276-295`). The log wrapper deletes only its own rotated backups under `out/local/logs/` (`CLAUDE.md:135-136`) |
| R-8 | Does `to_row` work for a kind outside `TABLES`? | RESOLVED | No, it reads `TABLES[kind]` (`local/records.py:268`), hence §3.1's lookup helper |
| R-9 | Would helper names trip the launch inspection? | RESOLVED | Yes, for `run`, `call`, `system` and the like (`local/tests/test_deploy_inspection.py:60-63`). §3.11 avoids them |
| R-10 | Are the `security_paths` precondition and the owner's decisions (rows 25, 32, 34) in force? | RESOLVED | `backlog-delivery.config:89`; parent spec Plan-gate record (`docs/backlog/specs/dispatch-board.md:606-613`) |
| R-11 | Would validating `answersPath` in `local()` couple the collector to it? | RESOLVED | Yes: the collector calls `local()` at start and every pass (`local/collector.py:722`, `:752`). Hence a separate `answers_path()` that only the server and `answers.py` call (§3.2) |
| A-1 | Nonce per response, or per server start as the parent says? | ASSUMED | Default: per response. That is stronger, and AC-A9's "differs between two starts" still holds. Impact if wrong: low, since a per-start nonce is a one-line change |
| A-2 | When is the answers file created? | ASSUMED | Default: on the first answer that passes checks 1 to 16, never at start or on any refusal. That keeps tests and a bare start from creating it. Impact if wrong: low, since only the first POST's latency and an "unavailable" found at start rather than at first use are affected |
| A-3 | Duplicate policy: one current answer per `(projectId, specPath, row)`, with 409 unless `supersedes` names the head? | ASSUMED | Default: yes (§3.6). This also gives idempotency with no key header. Impact if wrong: **medium**. PBI-032's page must send `supersedes` to change an answer. If free appending were wanted, the page would have to choose "the latest", and `verify`'s ledger superseded check would weaken |
| A-4 | What does an Accept carry? | ASSUMED | Default: `answer: ""`. The accepted default is bound through `resolutionSha` (SG31-1), and the Resolution cell stays as it was at transcription, so `verify` can re-check it. The Source cell ("chosen default" wording) is not bound, since the transcription rewrites it. In this ledger the Resolution cell states the default. Impact if wrong: low. A default kept only in the Source cell and edited between Accept and transcription would not be caught |
| A-5 | Text rules: `answer` is one line with no forbidden character, and `note` allows `\n` | ASSUMED | Default: as §3.5, including Zl, Zp and the bidi controls (SG31-4). A ledger cell cannot hold a line break, and terminal output stays safe. Impact if wrong: low, since the page (PBI-032) uses a single-line answer field |
| A-6 | How is "2,000 characters" counted? | ASSUMED | Default: Python code points. JavaScript's `.length` and HTML `maxlength` count UTF-16 units, which are never fewer than code points, so anything the page accepts passes the server. The page is at most stricter for astral text, which does no harm. Impact if wrong: low |
| A-7 | Status codes 411, 413, 415, 409 and 503 beside 400 and 403, plus `X-Dispatch-Reason` | ASSUMED | Default: §3.4. Every one uses the existing one-line shape. Impact if wrong: low |
| A-8 | `specRevision` type | ASSUMED | Default: `int`, compared as `str()` with the tab's string. Impact if wrong: low |
| A-9 | Projects read at start only | ASSUMED | Default: yes, as today. Impact if wrong: low. A project added to the config needs a server restart before it can be answered |
| A-10 | Edit `board.config.json` to add `answersPath`? | ASSUMED | Default: no, the default applies. Impact if wrong: low |
| A-11 | Does `verify` check the question and default hashes, and supersession? | ASSUMED | Default: both hashes on the ledger row. Supersession fails the ledger form, and fails the Plan-gate form unless the cited answer's `specRevision` is lower than the spec's current revision (SG31-5, SG31-r2-1). Impact if wrong: **medium**. Too strict, and `verify` fails legitimate history, then gets ignored. Too loose, and a stale answer passes as current. An edit to the question or an accepted default after transcription fails `verify`, and the fix is to restore the row or re-answer |
| A-12 | Transcription formats (§3.11, §3.12) | ASSUMED | Default: as written. PBI-032's "awaiting transcription" state (AC-B3) must look for `answer:<id>` in the exported ledger row, which these formats guarantee. Impact if wrong: low |
| A-13 | Journal mode | ASSUMED | Default: rollback journal, `synchronous = FULL`, so read-only opens need no `-shm` file. Impact if wrong: low |
| A-14 | Shape-language addition | ASSUMED | Default: `maxLength` only. PBI-034 adds a pattern rule if it needs one for `specBlob`. Impact if wrong: low |
| A-15 | What happens when the answers file is unusable at run time? | ASSUMED | Default: board reads continue, answers are left out with a warning, and POSTs get 503. A network path still refuses start (FR-96). Impact if wrong: low |
| A-16 | PATCH | ASSUMED | Default: it stays the framework's 501, which already reads "method not allowed" (`local/tests/test_server.py:182-188`). Impact if wrong: low |
| A-17 | `answers.py` output encoding | ASSUMED | Default: UTF-8 on stdout. Impact if wrong: low |
| A-18 | Can a 16 KiB body refuse two maximum-length fields? | ASSUMED | Default: yes, 413. Impact if wrong: low, since it takes about 8,000 bytes of astral characters in both fields |
| A-19 | A request with no `Sec-Fetch-Site` passes the Fetch Metadata gate | ASSUMED | Default: yes, so non-browser clients (the tests, `curl`) and older browsers work as today. Every current Chromium, Firefox and Safari sends the header on every request. Impact if wrong: low. In an old browser, a no-cors GET from a web page can still hold stream slots (residual R2) |
| A-20 | Should idle keep-alive timeouts be logged? | ASSUMED | Default: no. `log_error` drops only the framework's "Request timed out" message (§3.8). They are routine for every browser tab, and a line per page load would bury the lines that matter. Impact if wrong: low, since a timed-out connection had sent no request |

**ASSUMED:** 20 rows. **High impact:** none. **Medium:** A-3 and A-11. A-4 is now low, since SG31-1 was
applied rather than raised to the owner.

**Needs the owner:** nothing blocks the spec gate. The residual risks in §4.3 (R1, R2) are put to the owner with
the external-review go-ahead that `requires_external_review: true` already requires.

## 9. Out of scope

- The page's answer controls and states (PBI-032).
- `planApproval` and `conditionsAccepted` (PBI-034).
- The answer audit (PBI-033).
- Any login or per-person identity (rows 7, 24 and 30).
- Answering off this PC (row 25).
- Backing up `answers.db` (row 46).
- Editing the PRD. Its re-baseline is a chore (parent row 47).

## 10. Spec-gate record

| Round | Revision reviewed | Reviewer | Verdict | Review |
|---|---|---|---|---|
| 1 | 1 | `pbi-review`, same-vendor subagent, clean context | CHANGES-REQUIRED (High 1, Medium 4, Low 10) | `docs/backlog/reviews/PBI-031/spec-review-r1.md` |
| 2 | 2 | `pbi-review`, same-vendor subagent, clean context | **APPROVE-WITH-NOTES** (Medium 1, Low 5; all 15 round-1 findings resolved) | `docs/backlog/reviews/PBI-031/spec-review-r2.md` |

### Round-1 dispositions

Applied: 15 of 15. Deferred: 0. One optional sub-part is declined, with the reason (SG31-12's GET routes).

| Finding | Severity | Disposition | Where / why |
|---|---|---|---|
| SG31-1 | High | Applied (the preferred fix) | Required `resolutionSha` in the record (§3.1). Check 15a, 409 `resolution` (§3.4). `verify`'s ledger form checks the Resolution cell for an Accept (§3.11). The transcription keeps the Resolution cell for an Accept (§3.12). AE-2, AE-10, AE-16, AE-23. T12 and T22. A-4 is re-rated low, because the binding now exists |
| SG31-2 | Medium | Applied | The token is specified in §3.3: `secrets.token_urlsafe(32)`, 256 bits, per server start, both origins, never persisted or logged, 43-character URL-safe alphabet, compared with `hmac.compare_digest` on bytes. The dangling "(§3.5)" is removed. AE-31; T9 |
| SG31-3 | Medium | Applied (the preferred fix) | The Fetch Metadata gate in `_handle`, with the navigation exception for `GET /` (§3.3, check 2a). AE-32. T16 is rewritten with the true premise. R2 is rewritten, and its remaining gap is only browsers without Fetch Metadata. A-19 added |
| SG31-4 | Medium | Applied | Zl, Zp and the bidi controls are refused (with `Cc`) in `answer`, `note` (except `\n`) and the other strings (§3.5). `verify`'s split is derive's own rule (§3.11). AE-14 adds U+0085, U+2028, U+2029, U+202E and U+2066. AE-23 adds a question cell with `\|` |
| SG31-5 | Medium | Applied | Supersession fails the ledger form only. The Plan-gate form prints `ok … (superseded by <id>)` (§3.11). `CLAUDE.md` text: never edit an earlier revision's lines (§3.12). AE-23 case. A-11 re-rated medium |
| SG31-6 | Low | Applied | `test_server.py:104-109` is added to §3.10's list, re-keyed, with a `<script` / `nonce=` count guard. AE-26 |
| SG31-7 | Low | Applied | A 5-second wall-clock body deadline (check 8). The lock is taken only after checks 1 to 15a (§3.6). `Handler.timeout = 30` (§3.3). AE-33; T15 |
| SG31-8 | Low | Applied | An absent file with `supersedes` gives 409 and creates nothing (§3.6 step 1; A-2). The reader's "not created yet" state is `user_version` 0 or no table, silent and retried. Every failed open is retried (§3.7). AE-6, AE-21 |
| SG31-9 | Low | Applied (the first option) | Every direct `serve()` and `main()` call in `local/tests` passes `answers_path`. `test_answers_isolation.py` scans the test sources with the AST (§3.12, §5). AE-29 |
| SG31-10 | Low | Applied | The 503 line logs the exception type and SQLite error name only. The answers route logs its unexpected exceptions without their message (§3.8). The §3.8 wording excepts the repr-escaped header lines. AE-17 extended to AE-18 to AE-20 and a forced 500. AE-20 checks the 503 log line |
| SG31-11 | Low | Applied | A-6's direction is corrected. R-7 is narrowed to `answers.db`, with the log wrapper named. A-4 is re-rated low, because SG31-1 is applied, not left open. A-11 is re-rated medium. The coupling is removed with a separate `board_config.answers_path()` (§3.2; R-11; AE-4) |
| SG31-12 | Low | Applied, with one part declined | The Content-Type grammar is written out (§3.4). Exactly one `Host`, `Origin`, `Content-Type`, `Content-Length`, `X-Dispatch-Token` and `Sec-Fetch-Site` header is required on `/api/answers` (§3.3). AE-11 and AE-12 cases. **Declined:** extending the one-header rule to the GET routes. It is not needed for the write surface, and it would change existing read behaviour outside this PBI's criteria |
| SG31-13 | Low | Applied | Seams `_connect_answers(path)` and `_insert_answer(conn, row)` are named in §3.6. AE-17 and AE-20 use them |
| SG31-14 | Low | Applied | Each watcher gets its own `wake` Event. `unregister()` sets both `stop` and `wake`, and `notify()` sets the current watcher's (§3.7). AE-21 adds the stop-and-reopen case |
| SG31-15 | Low | Applied | `X-Dispatch-Reason` on every answers-route refusal (§3.4). Lowercase `project_id` with a `_DOC_FIELD` mapping, so every schema name stays a lowercase word (§3.1; AE-3). `Cross-Origin-Opener-Policy: same-origin` on `GET /` and `HEAD /` (§3.10; T21; AE-26) |

### Round-2 dispositions

Applied: 6 of 6, in revision 3 as a text pass. Deferred: 0. One optional sub-part is declined, with the reason.
The review needs no round 3: SG31-r2-1 is checked by diff.

| Finding | Severity | Disposition | Where / why |
|---|---|---|---|
| SG31-r2-1 | Medium | Applied | A superseded Plan-gate citation is `ok` only when its `specRevision` is lower than the spec's current revision, read with `^revision:\s*(\d+)`. Otherwise it is `MISMATCH … superseded` (§3.11). §3.12 step 3: the current revision's lines cite the current answer. A-11 reworded. AE-23 gains the exit-1 case. **Declined (optional):** accepting a superseded citation whose successor is cited later in the same block. The current revision's lines are editable, so correcting them in place is simpler and keeps one rule |
| SG31-r2-2 | Low | Applied | Drain before close for refusals at checks 3, 6 and 7 with a valid `Content-Length`: send, then read and discard up to that length under a 1-second deadline, then close (§3.4). No `SHUT_WR`, so the socket inspection is unchanged. AE-12 case |
| SG31-r2-3 | Low | Applied | The body loop is `settimeout(left)` then `self.rfile.read1(remaining)` (check 8). `log_error` drops only the "Request timed out" message (§3.8; A-20). AE-24 case |
| SG31-r2-4 | Low | Applied | The AST scan fails on a missing `answers_path` or a literal `None`, unless `config=` is a dict literal carrying `answersPath` (AE-29) |
| SG31-r2-5 | Low | Applied | `<n>` is logged only under `records`' int rule and `1 <= row <= 99999`. Checks 1, 2 and 2a on the answers route also write an `answer refused` line (§3.8). AE-24 cases |
| SG31-r2-6 | Low | Applied | `answer:[0-9a-f]{32}` is refused in `answer` and `note`, and U+200E, U+200F and U+061C join the forbidden set (§3.5). AE-14 cases |
| SG31-12 (round 1) | — | Reason added | The review gives a stronger reason for declining the one-header rule on the GET routes. `Host`, `Origin` and `Sec-Fetch-*` are forbidden request-header names, so no web page can duplicate them. A duplicate can reach a GET only from a local process, which is row 32's scope |
| Probe: awaiting rule vs superseding | — | Noted | §3.6: once a row is transcribed, the planner re-opens it before the owner can supersede. PBI-032's page text should say so |
