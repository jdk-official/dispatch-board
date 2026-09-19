# Spec-gate review — PBI-005 local server (revision 2, round 2)

Reviewer: `pbi-review`, same-vendor-subagent tier (clean-context, read-only Plan agent), 2026-09-12. Saved verbatim by the orchestrator.

**Verdict: APPROVE-WITH-NOTES**

Every round-1 finding is resolved, and resolved against the code rather than the prose. The two deliberate deviations are both correct on the facts and both better than my round-1 wording. Two Low notes remain; neither blocks the build.

## Round-1 resolution

| ID | Resolved | How, verified |
|---|---|---|
| S-1 | Yes | §4.3's quote of `handle_one_request` matches CPython 3.14.5 exactly (`mname = 'do_' + self.command`; `hasattr` → 501; 414 at >65536 bytes). `http.client._MAXLINE` is 65536 and `_MAXHEADERS` 100; `parse_request` emits 400/505/431 as tabulated; `DEFAULT_ERROR_MESSAGE` is HTML carrying `%(message)s`. Six `do_*` funnelling through `_handle()`, plus the `send_error` override and the `error_message_format`/`error_content_type` backstop, close both halves. The 501 concession is argued, not hidden. |
| S-2 | Yes | `db.stored` (`local/db.py:169`) does `SELECT id, doc … ORDER BY id` and hands `from_row` the doc **text**, so the tuple failure is gone. `from_row` (`local/records.py:264-286`) accepts `str` or `Mapping`/`sqlite3.Row` only, confirming the original defect. The id check via `records.store_path` → `_check_id` (`:211-216`) is real. AC-69 is now non-vacuous (entry per record, `skipped == 0`). |
| S-3 | Yes | Per-stream bounded `queue.Queue(maxsize=32)`, watcher `put_nowait`-only, drop on `Full`, plus `settimeout(10)`. §7.2, AC-SV10 and the §9 stalled-client case (including the `maxsize=2` variant) all agree. |
| S-4 | Yes | `id: <current version>` on `reset` and max-of-the-two. I traced the three loop cases — post-reset auto-reconnect, manual re-open with a stale header, and a server restart that re-baselines `version` to 1 (covered because the rule is "different", not "older"). No loop in any. |
| S-5 | Yes | §4.4 asserts the on-PC half here; `LOCAL_DATABASE = 'out/local/board.db'` and the committed `board.config.json` `local` block confirm the repo-relative default, and `db.resolve` takes it from `REPO`. The AC-71 pointer is gone. |
| S-6 | Yes | §1, §5.1 and AC-SV6 are scoped to the database file's bytes, mtime, `data_version` and `sqlite_master`. |
| S-7 | Yes | "Three routes", with §6.3 named as the shared error table. |
| S-8 | Yes | The `answers` substring assertion is API-routes-only; the kinds-subset assertion stays global. |
| S-9 | Yes | See deviations. |
| S-10 | Yes | AC-SV10 states one heartbeat plus one poll before sampling, then unchanged over two further polls; both intervals are driven down in the test. Coherent with the new per-stream design, where a dead client is found on the heartbeat write. |
| Scope slip | Yes | §10 is worded as a close-out expectation; `PBI-005.md` is untouched, and the amendment is left to the owner. |

## New findings

| ID | Sev | Finding | Evidence | Required change |
|---|---|---|---|---|
| R2-1 | Low | "One fixed line chosen by status code" is not true for three statuses: 403 has the three lines of §4.3.1, 503 has §6.3's three plus §7.1's `too many open streams`, and the `Retry-After: 5` of §6.3 is not in §4.3's header list. As written, `send_error` both ignores the text it is handed and must choose among several lines for one code. | §4.3 table vs §4.3.1, §6.3, §7.1 | One sentence: the gate and §6.3/§7.1 refuse through an internal helper that names its own line (and adds `Retry-After` on 503); the `send_error` override governs only framework-raised statuses, where the code does determine the line. |
| R2-2 | Low | Citation drift: §5.4 cites `local/records.py:262-283` for `from_row`; it is 264-286. `db.py:169`, `records.py:211-216` and `site/index.html:1139` are exact. | `local/records.py` | Correct the range. |

**Recommended disposition for both:** apply during the build, in the spec file, without a further review round — neither changes a design decision or an acceptance criterion.

## The two deviations

- **Per-kind `sqlite3.Row` fallback instead of skipping inside `db.stored`.** Correct and better. `db.stored` is a dict comprehension, so one bad row does lose the whole kind; my round-1 "reuse `db.stored`" would have silently cost Q-7's per-record skipping. Keeping the happy path on `db.stored` and isolating bad rows per kind preserves both reuse and Q-7, and §9 tests exactly that ("every other record of that same kind is still served").
- **No console warning on the local page.** Correct, and my round-1 wording was wrong. `site/index.html:1139` is `try { db = await window.claude?.use?.('db'); } catch (e) { console.warn(…) }`; with `window.claude` absent the optional chain yields `undefined` without throwing, and line 1140 sets `offline` and the "cannot reach the live store, so it shows no data" footer. The revised §6.1 states the true observable, which is what S-9 was for.

## Scope check

Clean. `PBI-005.md` grants `local/server*`, `local/tests/**`, `board.config.json`, `exporters/board_config.py`; every file in §2 is inside it, `site/index.html` and `local/db.py` are read-only, and no edit to `docs/backlog/pbi/**` is claimed. Internally consistent after the edits: 3 PRD + 12 added criteria matches the §10 count, all seven `records.TABLES` kinds are served, `schema.create_schema` does set `user_version`, so §5.1 step 4's readiness test works. Owner rows Q-13 and Q-17 remain correctly parked; neither is a high-impact assumption and neither blocks this gate.
