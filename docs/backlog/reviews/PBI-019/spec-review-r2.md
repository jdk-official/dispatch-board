# Spec-gate review: PBI-019 collector spec, revision 2 (round 2)

Reviewer: `pbi-review`, same-vendor-subagent tier (clean context, read-only), 2026-09-11. Saved verbatim by the orchestrator.

Verdict: CHANGES-REQUIRED

All 13 round-1 findings are resolved. The opening order, copy-then-swap, tagged codec and key-set reset are correct as written. One new Medium remains: the spec text, built literally, breaks FR-86. It needs a small edit, and none of the fixes needs the owner. Round 3 can be a targeted check of R2-1 to R2-6.

## Round-1 resolution

| ID | Status | Note |
|---|---|---|
| S-1 | Resolved | §3.3: read-only pre-check comes before WAL and `create_schema`, and missing tables pass, so fresh files open and foreign files are refused unmodified. Residual gap: R2-6 |
| S-2 | Resolved | §4.3 "Feeding a copy" plus AC-CL13. Residual gap: R2-4 |
| S-3 | Resolved | The generic codec round-trips sets, tuples, non-string keys and the `"$"` escape. `add_record`/`add_agent` add no keys (`derive.py:291-465`), so the key-set check cannot reset on every pass |
| S-4 | Resolved | The marker is content-free and reads no bytes. Two defects remain: R2-2 and R2-3 |
| S-5 | Resolved | §4.2, §4.7, AC-CL7 |
| S-6 | Resolved | Q-21, the §4.7 reading, and a test |
| S-7 | Resolved | §5 and §10 hand off to PBI-007 |
| S-8 | Resolved | §3.5 lock scope and message, AC-CL12 |
| S-9 | Resolved | §3.2 and AC-CL14 |
| S-10 | Resolved | §3.3 step 7, §3.4 |
| S-11 | Resolved | §4.6 step 4, tested with a counted `db.upsert` |
| S-12 | Resolved | `PBI-008.md:39-41` is now corrected. Stale text remains: R2-7 |
| S-13 | Resolved | Deviation recorded in §7 |

## New findings

| ID | Sev | Finding | Evidence | Required change |
|---|---|---|---|---|
| R2-1 | Medium | Some transcripts are re-read in full on every pass. Take an unlinked session whose file time is inside the window but whose `last` is older (the exporter's own case: "a transcript can be touched without new activity"). It is pruned on last activity and its state rows are deleted. The next pass finds no state, reads the file from 0, prunes it again, and so on every 60 s for up to `days`. The spec also doesn't say whether a session whose result is `None` (no answered response) keeps its state. The exporter's cache avoids these re-reads; the collector breaks FR-86 ("read only the lines appended"). Test fixtures, which have fresh mtimes and old timestamps, hit this too. | §4.3 "Age-pruned sessions lose their state"; §4.6 step 6; `export_sessions.py:244,266-268` | Keep state and cursors for every discovered, non-excluded session inside the file-time window, whether or not it enters the results. Discard state only when the session drops out by file time, its transcript vanishes, it is excluded, or it is reset. Add a test: after pruning by last activity, the next pass opens that file 0 times. |
| R2-2 | Low | A marker that fails to match is never removed. A file truncated and rewritten with a cwd that is not excluded falls back to `cwd_of` once. Once it grows back past the old `size`, the stale marker matches again and the session is wrongly purged (reason `other`, which counts toward the guard). Inode reuse causes the same failure. | §4.1 "Exclusion markers" ("Otherwise the marker is ignored") | Delete the marker for that `(dev, ino)` whenever it is consulted and does not match; step 4 re-creates it if the file is still excluded. Test: truncate, rewrite with an included cwd, grow past the old size, and the session is still included. |
| R2-3 | Low | `collector_excluded.ino INTEGER` can overflow. On Windows `st_ino` is an unsigned 64-bit file ID, and from Python 3.12 it can be up to 128-bit on ReFS (Dev Drive). A value above 2^63-1 raises `OverflowError` outside any record savepoint, so every pass rolls back and the collector stalls. | §3.4 DDL; §4.9 "Anything else" | Store `dev` and `ino` as TEXT, or treat an `ino` of 2^63 or more like `ino` 0 (no marker). |
| R2-4 | Low | §4.4 step 4 covers only raises while reading or feeding the main transcript. A raise in `derive.session_result`, or in the post-feed exclusion check, is not covered. If the agents' working copies were then committed, the next pass would see no new bytes and reuse the stale result indefinitely. The exporter instead keeps the old signature and re-reads. | §4.4 steps 3-4; `export_sessions.py:254-260` | Treat any raise after the main feed, up to encoding, as a main-transcript failure: discard all of that session's working copies and cursors. |
| R2-5 | Low | The re-derive triggers leave out a transcript whose mtime changed but whose bytes did not. The exporter's signature includes mtime, and `agent_row`'s `age` depends on it. After a touch, a quiet agent with no finish becomes `running` in the exporter but stays `killed` in the collector, which breaks AC-64. | §4.4 step 3; `export_sessions.py:172-178`; `derive.py:478` | Add "a file's mtime changed" to the re-derive triggers. It costs a `stat` only, no read. |
| R2-6 | Low | A file at the configured path that is not a SQLite database raises `sqlite3.DatabaseError` at step 4. It is not mapped to `db.Refused`, so the exit code (1 or 2) and the loop-mode behaviour are unspecified. | §3.3 step 4; §5 | Map `DatabaseError` in steps 3-8 to `db.Refused` (exit 2, file unmodified) and add that case to AC-CL1. |
| R2-7 | Info | Some text is stale after the PBI-file corrections. §8's intro says AC-115 and AC-119 to AC-121 are "not yet copied". §6 says the PBI files "have" the old wording. Q-15 is still open. | §6, §8 line 440, Q-15; `PBI-019.md:44-52` | Update all three to "done". |
| R2-8 | Info | Three smaller points: (a) `realpath` and `GetDriveTypeW` on a mapped drive contact the file server, which conflicts with §5's "never contacts any network host"; (b) `realpath` opens handles, so "opens no file" is imprecise; (c) step 7's "every transcript is read again" is true only when `collector_sessions` is the table dropped. | §3.2, §3.3 step 7 | Check the string forms and drive type first and stop at the first hit. Consider dropping all three state tables together. |

Owner rows Q-2, Q-3 and Q-21 do not block this gate. Each can be undone, and Q-21 follows A-47's own default.

## Scope check

Every file created or edited is within `allowed_areas`: `local/db.py`, `local/collector.py`, `local/tests/*`, `exporters/board_config.py` and `board.config.json`. Nothing touches `site/**`. `derive`, `export_sessions`, `export_catalogue`, `records`, `schema` and `tests/test_export_sessions.py` are imported only, never edited. The fixes for R2-1 to R2-6 stay in `local/collector*` and `local/db*`. The AC-34, AC-42 and AC-44 counts correctly stay with PBI-008.
