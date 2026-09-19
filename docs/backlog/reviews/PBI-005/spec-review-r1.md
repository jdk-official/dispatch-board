# Spec-gate review — PBI-005 local server (revision 1, round 1)

Reviewer: `pbi-review`, same-vendor-subagent tier (clean-context, read-only Plan agent), 2026-09-12. Saved verbatim by the orchestrator.

**Verdict: CHANGES-REQUIRED**

A strong, well-grounded spec: the start-up order, the network-path guard, the no-write argument, the `collector_*`/`answers` exclusions and the test plan are all sound and testable. Three defects would produce a build that cannot meet its own criteria, two of them on the hardening path.

## Findings

| ID | Sev | Finding | Evidence | Required change |
|---|---|---|---|---|
| S-1 | High | The "one gate before routing" invariant does not hold on `http.server`. `BaseHTTPRequestHandler.handle_one_request` answers an unknown method with 501 *before* any handler code runs (`if not hasattr(self, 'do_'+command)`), so `POST/PUT/DELETE/OPTIONS` never reach the Host/Origin gate and never reach 405. AC-SV3 as written is unachievable. `send_error` also emits an HTML page and echoes the method token, contradicting "one line of `text/plain`" and "the offending value is never echoed". | §4.3, §6, AC-SV3, AC-SV2 | State explicit `do_GET/do_HEAD/do_POST/do_PUT/do_DELETE/do_OPTIONS` (or an override of `handle_one_request`) that all funnel through the gate, and override `send_error`/`error_message_format` so 400, 404, 501 and header/line-limit refusals return the same one-line plain body with the standard headers and echo nothing. Say what a method outside that list returns. |
| S-2 | High | §5.4's read cannot work. `records.from_row(kind, row)` accepts only a `str` or a `Mapping`/`sqlite3.Row`; a default cursor yields a **tuple**, so every row raises `ValueError` and the snapshot would be empty with `skipped` = every record — while still passing AC-69 vacuously. | `local/records.py:264-286`; spec §5.4 | Specify `conn.row_factory = sqlite3.Row` (which also gets the id-form check the spec claims), or reuse `db.stored(conn, kind)`, which already does this loop. Prefer `db.stored` — it removes one duplication and keeps the id check explicit via `store_path`. |
| S-3 | Med | Broadcast blocking. §7.2 has the single watcher thread write each event to every open stream, and §7.1 has the heartbeat discover dead clients by a raising write. On a blocking socket, one suspended browser tab whose send buffer is full blocks that write indefinitely, stalling the watcher and therefore every other client — the failure NFR-18 is meant to exclude. | §7.1, §7.2, AC-SV9/AC-SV10 | Give each stream its own bounded queue and let its own request thread write and heartbeat; the watcher only enqueues (dropping a client whose queue overflows). Alternatively set a socket write timeout and drop on timeout. |
| S-4 | Med | `Last-Event-ID` "wins over `since`" can loop. A browser auto-reconnect carries the last `id:` it saw; the spec puts no `id:` on `reset`, so a client that has just re-fetched a newer snapshot is told to reset again. | §7.3, AC-SV9 | Emit `id: <version>` on `reset` too, and take the **newer** of `Last-Event-ID` and `since` rather than an unconditional precedence. |
| S-5 | Med | NFR-20 now has no owner. §4.4 hands its deployment half to AC-71, which §12 lists under the deferred Unraid work; PBI-007's criteria do not include it. | §4.4, §12; parent spec post-approval amendment | Either assert the on-PC half here (default path is repo-local; the guard runs at every start) or name PBI-007 as its owner. Do not leave it pointing at a deferred PBI. |
| S-6 | Low | "It writes nothing, anywhere" is slightly stronger than the design. Opening a WAL database creates `-shm`/`-wal` beside it when absent; `query_only=1` protects the database's content, not the directory. | §1, §5.1, AC-SV6 | Say so in §5.1 and scope AC-SV6 to the database file's bytes/mtime/`data_version` (which is what it already tests). |
| S-7 | Low | Internal inconsistency: "Four routes" precedes three (`/`, `/api/snapshot`, `/api/events`); §6.3 is an error table. | §6 | Correct the count. |
| S-8 | Low | AC-SV7's "no response body holds the substring `answers`" applied to *every* route couples PBI-005's suite to `site/index.html`'s wording (today it happens not to contain it). | AC-SV7, §9 | Scope the substring assertion to the API routes; keep the kinds-subset assertion global. |
| S-9 | Low | §6.1/AC-SV5 do not state the observable: served locally before PBI-006, the page reaches `window.claude?.use?.('db')`, gets nothing and renders an empty board with a console warning. | `site/index.html:1139` | One sentence in §6.1 so the reviewer of the build does not read an empty board as a defect. |
| S-10 | Low | AC-SV10's "the count stops rising" is timing-dependent: a vanished client is only discovered on the next write, up to one heartbeat later. | §7.2, AC-SV10 | State the tolerance (close the socket and allow one heartbeat plus one poll) so the test is not flaky. |

**On the two questions put to me directly.** The read-only opener in `local/server.py` is sound: `db.open_db` genuinely writes and takes the write lock, `local/db*` is outside the areas, and `network_path`/`resolve`/`Changes` are pure and correctly reused. The only real duplication is the `user_version > SCHEMA_VERSION` check (two places, cheap, both fail closed) — acceptable, and S-2's `db.stored` reuse removes the other. The page-wrapping approach is correct: reading is not editing, the file's `<title>` is on line 1 within the 8 KB window, and no traversal is possible because no route takes a path. The `window.__DISPATCH_LOCAL__` seam plus the snapshot/event shapes are specified well enough for PBI-006 to build against once S-4 lands; deferring only the *detection signal* to PBI-006 is right, since the marker is additive either way.

## Owner questions

| Row | Needs owner | Blocks building | Recommended default |
|---|---|---|---|
| Q-13 (page fetches Google fonts) | Yes, but low urgency | No | Build as specified; the CSP already confines it to the two hosts. Log an offline-fonts follow-up against `site/**` (PBI-006 or a new PBI). |
| Q-17 (`CLAUDE.md`/`README.md` not in `allowed_areas`) | Yes | No | The parent spec already grants every PBI that touch ("Every PBI may update `CLAUDE.md` and `README.md` for its own procedures"); `PBI-005.md` simply omits it. Owner to add `CLAUDE.md` to `allowed_areas`, or accept §8 + docstring and leave the note to PBI-007. |
| Q-16 (any signed-in user can read the board) | No | No | Settled by parent row 24; correctly surfaced. |
| Q-4/Q-11 (snapshot and seam shapes) | No | No | Settled at this gate, with S-4 applied. |

## Scope check

Every file the spec creates or edits — `local/server.py`, `local/tests/test_server*.py`, `local/tests/test_config_local.py`, `exporters/board_config.py`, `board.config.json` — is inside `allowed_areas`; `site/index.html` and `local/db.py` are read only. One item sits outside: §10's close-out says it **replaces the line in `PBI-005.md`**, and `docs/backlog/pbi/PBI-005.md` is not in `allowed_areas`. Reword it as a close-out expectation (the three suites are already the configured `[test_commands]`), or have the owner amend the PBI file.
