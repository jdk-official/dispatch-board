---
id: PBI-005
title: "Local server: page, data snapshot, live push, 127.0.0.1 binding, Host and Origin checks, network-path guard (FR-92–FR-94, FR-96)"
status: Done
change_class: standard
depends_on: [PBI-003, PBI-004]
allowed_areas: ["local/server*", "local/tests/**", "board.config.json", "exporters/board_config.py"]
blocked_areas: ["exporters/export_*.py", "exporters/derive.py", "exporters/refresh.py", "site/**"]
conflict_group: local-app
conflict_risk: Medium
requires_spec: true
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-005 — Local server: page, data snapshot, live push, 127.0.0.1 binding, Host and Origin checks, network-path guard (FR-92–FR-94, FR-96)

---

## Description

Local server: page, data snapshot, live push, 127.0.0.1 binding, Host and Origin checks, network-path guard (FR-92–FR-94, FR-96). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `local/server*`, `local/tests/**`, `board.config.json`, `exporters/board_config.py` (the port key; it also touches `config` and `exporters`); blocked other `exporters/**` files and `site/**`. Its spec covers:
- 127.0.0.1 binding (NFR-19);
- a Host-header allow-list, an Origin check on every non-GET request, and no CORS (row 24);
- the network-path guard (FR-96, NFR-20);
- a server-level check that a database change reaches connected clients;
- wrapping the content-only page (PRD C-8).

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-92, FR-93, FR-94, FR-96:

- [x] **AC-67** When the local-database path is configured as `\\nas\share\board.db`, the local server shall refuse to start and print that path. *(FR-96.)*
- [x] **AC-68** When a finish is appended to a running agent's transcript while the page served by the local server is open, the page shall show the run's new kind within 10 minutes without a reload. *(FR-94, NFR-18; demonstration.)* — **server-level leg only**, which is this PBI's scope per the approved spec §7 and §10; the in-browser demonstration half is PBI-007's and is *not* claimed here. See Evidence.
- [x] **AC-69** When the page requests the data snapshot, every record returned shall conform to the record shapes. *(FR-93, FR-100.)*
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO). *(The config has three suites; all three are quoted in Evidence.)*

---

## Evidence

Verified fresh at finalize on merged main `3e3ec44` (PR #19, squash), 2026-09-12. Suites on that commit: `tests` **334**, `page.test.mjs` **99**, `local/tests` **261** — all OK, 0 skipped, against the 334 / 99 / 194 baseline (the local suite grew by 67).

- **AC-67** — `test_server.NetworkGuard.test_unc_path_refuses_at_start_exits_2_no_socket_no_file_created`: a UNC database path exits 2, names the path, leaves **no socket listening on the configured port** and **creates no file or folder**. The round-1 review found these two assertions absent and vacuous respectively; they are now concrete (a real port, a recursive folder listing, the real `db_path`), and stubbing `db.network_path` to `False` makes the test fail. `test_realpath_pointing_at_a_unc_path_refuses` covers the symlink-resolution case. The guard runs before any bind in both `serve` and `main`.
- **AC-68 (server-level leg)** — `test_server_live.Live.test_change_delivered_within_three_poll_intervals`: with a stream open, another connection commits a `running` → `done` change and the stream yields one `change` event carrying `runs/<id>` with the new kind and a higher `version`, within three poll intervals — well inside NFR-18's 10 minutes. `test_deleted_record_arrives_in_deleted` covers the deletion half, and `BesideACollector.test_snapshot_and_stream_survive_a_real_collector_pass` proves it holds beside a real collector pass. **What is not claimed:** the in-browser demonstration (the page open in a browser showing the new kind without a reload) is explicitly PBI-007's under the approved spec §7 ("AC-68's in-browser leg is a demonstration and belongs to PBI-007") and §10, and the reviewer recorded it under `not_audited`. It is not ticked here by inference.
- **AC-69** — `/api/snapshot` returns an entry for every stored record with `skipped == 0`, and every entry conforms to the record shapes. The spec made this non-vacuous on purpose after round-1 spec finding S-2: an empty or short `records` map fails. Proven by the snapshot tests plus a by-hand run over a temporary database that returned HTTP 200 with 3 records and `skipped: 0`.
- **Worker close-out** — all three configured suites green on the head commit, quoted above; code-review gate **GO** at round 2.

**The security surface**, verified independently by the reviewer in both rounds and pinned by tests:

- 127.0.0.1/AF_INET binding with `allow_reuse_address=False` — `Binding.test_binds_127_0_0_1_only_and_refuses_reuse`, `Binding.test_a_connection_to_the_lan_address_is_refused`.
- The Host allow-list and the Origin check on every non-GET, with no CORS — `HostAndOrigin.test_bad_hosts_are_403_one_line_no_echo`, `test_get_with_foreign_origin_is_403`, `test_non_get_needs_origin_or_403`, `test_no_response_carries_a_cors_header`.
- All six methods funnelled through the gate before routing, with every framework-raised status sharing one plain shape — `GateFramework.test_the_six_do_methods_exist`, `test_every_refusal_has_the_same_plain_shape` (one property list over all eight refusals: 403 ×3, 404, 405, 400, 414, 431, 501, 505), `test_a_method_outside_the_six_is_501`. No response echoes a Host, Origin, method token or request line in body or headers — the reviewer swept a marker token through all six positions across eight responses and found it in none.
- The database is never written — `NeverWrites.test_query_only_and_file_unchanged_even_with_writers_patched_to_raise`: `query_only=1`, with the file's bytes, mtime, `data_version` and `sqlite_master` unchanged.
- AC-SV7 — `IgnoresCollectorState.test_no_response_holds_collector_state_or_answers` and `Live.test_stream_events_hold_no_collector_state_or_answers`: neither the snapshot nor the stream leaks `answers` or `collector_` state.
- No reconnect loop — `Live.test_no_reset_loop_after_obeying_a_reset`, `test_larger_of_since_and_last_event_id_wins_either_way`, `test_current_since_no_reset_stale_gives_reset_with_id`.

**The round-1 High was a test that proved nothing.** `test_no_client_can_stall_another` read as proof of AC-SV10 and of spec-gate finding S-3, but the stalled client kept draining into the OS socket send buffer, so the queue never overflowed: instrumenting `queue.Queue.put_nowait` recorded **0 `queue.Full` events**, leaving the whole drop path untested while the test asserted nothing about the stalled client. It was fixed by making the test force overflow — not by softening the criterion. Round 2 re-measured **2 `queue.Full` events**, and swapping the bounded queue for an unbounded one fails both `HubDirect.test_a_client_that_never_drains_overflows_and_is_dropped` and the repaired `Live.test_no_client_can_stall_another`.

**A real race was fixed:** `Hub.register` reused a watcher whose `stop` Event was already set, so a client connecting between the last unregister and the thread exiting got no watcher — live push silently dead, no error, self-healing only on a later connection. Round-1 probe: clients=1, watcher alive=False, 0 refreshes. After the fix: alive=True, 11 refreshes, change delivered. Pinned by `HubDirect.test_a_stream_registering_while_the_watcher_exits_gets_its_own_watcher`.

**A defect the repaired test then surfaced, which neither review round had found:** CPython sets `request_version` only after its 505 and bad-version-400 checks, so it is still `HTTP/0.9` when `send_error` runs and the base class suppresses the status line and every header — the 505 returned a bare `bad request` with no `Content-Type`, `Content-Length`, `Cache-Control` or `nosniff`. `_respond_plain` now forces HTTP/1.1 in that state. Round 2 confirmed all six framework paths return a proper status line and 9 headers with `Connection: close` still honoured, and that the builder's worry about HTTP/0.9 clients does not bite: CPython 3.14 gives such a request `headers = {}`, so it cannot pass the Host gate — it gets 403 and never any board data.

**Follow-ups** (3 Low + 1 Informational, in `docs/backlog/reviews/PBI-005/findings.json`): spec §4.3's `log_error` sentence describes behaviour the override it also mandates makes impossible (a plan defect, cheapest as a spec edit); the `except OSError` clause swallows any routing `OSError` with no response, against §6.3's 500 rule, and the new test pins that as the contract; the HTTP/0.9 version forcing lives only in `_respond_plain`, not the three success writers (unreachable on 3.14, a bounded risk on the 3.11 floor); and an unused `_orig_poll` in `Live.setUp`.

**Owner questions still parked** from the spec gate: Q-13 (the page fetches Google fonts, so it is not offline-capable) and Q-17 (`CLAUDE.md`/`README.md` are not in this PBI's `allowed_areas`, though the parent spec grants every PBI that touch).

**A note on the review record:** the orchestrator's review prompt wrongly asked the reviewer for a bare array, overriding `code-reviewer`'s own schema, and the push rail refused the file twice. The reviewer's literal output is preserved unaltered at `docs/backlog/reviews/PBI-005/findings-r2-array.json`; the envelope in `findings.json` was assembled by the orchestrator with the reviewer's prose carried byte for byte and `impact` quoted verbatim from it. This is recorded in that file's own `audit.provenance`. No verdict, severity, count or measurement was changed.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_spec: true`: refine a per-PBI spec from the parent spec and have it independently reviewed before any code is written.

**Owner authority, 2026-09-12:** started under the standing instruction to keep building. `merge_allowed_by_agent` is `true` under the owner's standing authorisation, verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time." Spec gate passed: docs/backlog/specs/pbi-005-local-server.md revision 2 (round 1 CHANGES-REQUIRED, round 2 APPROVE-WITH-NOTES, both notes applied); reviews in docs/backlog/reviews/PBI-005/.

**Blocked-area breaker, 2026-09-12 — metadata corrected by owner decision.** The scope rail refused the build's `exporters/board_config.py` edit: `allowed_areas` named that file while `blocked_areas` held `exporters/**`, and a blocked-area match wins over an allowed one (`scope_guard.py:177-185`), so the PBI granted and forbade the same path. Both spec-gate rounds read the grant and called scope clean without noticing the collision. Put to the owner as a three-way choice (narrow the block / defer the config change / override once); the owner chose **narrow the block**. `blocked_areas` is now `["exporters/export_*.py", "exporters/derive.py", "exporters/refresh.py", "site/**"]`, which blocks every exporter except the one file `allowed_areas` already names — the reading the Description above states in words ("blocked other `exporters/**` files"). No surface is widened: a new file under `exporters/` is still refused, because `allowed_areas` does not name it. No acceptance criterion and no design decision changed.


---

**Follow-up logged 2026-09-11** from the PBI-003 code review (`docs/backlog/reviews/PBI-003/findings.json`, follow-up 3):
- **The gap:** `local/records` has no inverse of `store_path` (store path to kind and id). `local/tests/test_conformance.py` reimplements it, and `COLLECTION` maps `meta` to both `lastRefresh` and `status`.
- **To do:** if the snapshot check (AC-69) needs the inverse, the PBI that adds it needs `local/records*` in its allowed areas.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | passed 2026-09-12 | docs/backlog/specs/pbi-005-local-server.md revision 2, APPROVE-WITH-NOTES in round 2 of 3 (both Low notes applied without a further round, as the reviewer recommended); round 1 CHANGES-REQUIRED (2 High, 3 Medium, 5 Low), all applied. Reviews: docs/backlog/reviews/PBI-005/spec-review-r1.md, -r2.md |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-12 (round 2 GO) | **Round 2: GO** — 3 Low, 1 Informational, all recorded as follow-ups, none blocking. The reviewer re-measured rather than trusting the change-report: 2 `queue.Full` events where round 1 recorded 0; an unbounded queue fails both drop-path tests; the watcher probe went from alive=False/0 refreshes to alive=True/11 refreshes; each of the eight named fixes was mutated back and its test failed without it. Suites run by the reviewer: 307 / 96 / 261, 0 skipped, matching the builder exactly; all 14 new local tests assert something real and none weakens a prior assertion. Findings at `docs/backlog/reviews/PBI-005/findings.json` (envelope assembled by the orchestrator — see Evidence; reviewer's literal output at `findings-r2-array.json`). Round 1 (`review-agents:code-reviewer`, Opus, 2026-09-12): **NO-GO** — 1 High, 3 Medium, 7 Low, 1 Informational, at `docs/backlog/reviews/PBI-005/findings-r1.json`. The High (CR-005-01) is test-adequacy: `test_no_client_can_stall_another` claims AC-SV10 and spec finding S-3 but never overflows the queue (instrumented: 2 clients registered, 0 `queue.Full` events), leaving the whole drop path untested. CR-005-02 is a real race — `Hub.register` reuses a watcher whose `stop` is already set, so a client connecting in that window gets no watcher and live push is silently dead. CR-005-04: the AC-67 assertions are absent or vacuous, though the guard code itself is correctly ordered. **Security surface verified clean:** 127.0.0.1/AF_INET bind with `allow_reuse_address=False`; the six-method funnel with every framework-raised status (400/414/431/501/505) landing in the overridden `send_error` as one fixed plain line, with no construction that echoes a Host, Origin, method token or request line; no `Access-Control-Allow-*`; `query_only=1` with file bytes, mtime, `data_version` and `sqlite_master` unchanged; AC-SV7 holds on both snapshot and stream; no reset loop; no spec-review finding re-opened. `code_review_max_rounds = 2`, so round 2 must reach GO. |
| No-self-merge gate | always | passed 2026-09-12 | PR #19 squash-merged `3e3ec44` by the orchestrator under the owner's standing merge authorisation (`merge_allowed_by_agent: true`), on a round-2 GO with every condition applied or dispositioned. Landing: resolved squash (declared) / observed squash, level `record`. CI: provider `none`, status `absent`; PR `MERGEABLE` / `CLEAN`. |
| BOARD-tidy gate | always | passed 2026-09-12 | two-part Done write: `docs/backlog/done-log.md` entry + BOARD `## Done` index row |
