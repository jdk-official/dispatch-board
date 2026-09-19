# Spec-gate review: PBI-019 collector spec, revision 3 (round 3, final)

Reviewer: `pbi-review`, same-vendor-subagent tier (clean context, read-only), 2026-09-11. Saved verbatim by the orchestrator.

Verdict: APPROVE-WITH-NOTES

All eight round-2 findings are resolved. The R2-1 fix is correct, and I checked it against `export_sessions.py:227-270`. Revision 3 keeps state and cursors for every session the exporter's cache keeps, including a session pruned on last activity (`fresh[sid]` is kept whether line 267 prunes it or not) and a session whose result is `None`. It drops state exactly when the exporter would lose its cache entry: the file time leaves the window, the transcript vanishes, the session is excluded, or it is reset. That gives:
- **FR-86:** a pruned session is reopened only when it gains bytes.
- **AC-64:** a kept `result` is re-judged on last activity every pass, as line 267 does.
- **AC-120 and AC-121:** these govern records, and §4.3, §4.6 steps 6 and 7, §4.7, AC-120's note and Q-10 all say the same.

**Nothing keeps state forever.** Only linked sessions keep state with no time limit, as the exporter does. Markers are content-free and last only as long as their file.

**No excluded content leaks.** The step-2 shortcut (the `cwd` held in state) matches `cwd_of`, because `derive.add_record` keeps the first non-empty string `cwd` (`derive.py:428`), the same rule as `export_sessions.py:135`.

## Round-2 resolution

| ID | Status | Note |
|---|---|---|
| R2-1 | Resolved | §4.3 "Which sessions keep state", §4.1, §4.2, §4.6, §4.7, Q-10; AC-CL15 and its §7 test (0 opens, 0 `cwd_of` calls) |
| R2-2 | Resolved | §4.1: a marker that does not match is deleted and re-created only if the file is still excluded. The test is in §7, and Q-9 names the one remaining case |
| R2-3 | Resolved | `dev` and `ino` are `TEXT`; the cursors keep them in JSON. See R3-1 |
| R2-4 | Resolved | §4.3, §4.4 step 4, §4.9; AC-CL13 extended, with a test |
| R2-5 | Resolved | §4.2 step 4 records `mtime` without a read; §4.4 step 3 adds the trigger; AC-CL3 and the touched-agent test |
| R2-6 | Resolved | §3.3 maps `DatabaseError` to `Refused` (the lock error excepted), exit 2; AC-CL1 and its test. See R3-3 |
| R2-7 | Resolved | §6, §8 and Q-15 say "done"; `PBI-019.md:44-52` confirms it |
| R2-8 | Resolved | §3.2 checks in order and stops at the first hit; §5's claim about network contact is qualified; §3.3 step 7 drops all three tables; AC-CL14 and a counter test |

## New findings

| ID | Sev | Finding | Evidence | Disposition |
|---|---|---|---|---|
| R3-1 | Low | AC-CL15 says an `st_ino` above 2^63 - 1 "is stored without error", but no §7 test covers it, although §8 says every criterion is covered in §7. It can be tested only through a patched `os.stat`. | §8 AC-CL15; §7 "Exclusion" | **Apply in build:** add a test that patches `os.stat` to return `st_ino = 2**64 - 1`, then checks that the marker is stored and matches on the next pass. |
| R3-2 | Info | If an excluded file is truncated and grows back past the marker's `size` between two passes, the old marker still matches, so the session stays excluded while the exporter would include it. This fails safe for privacy. Q-9 covers in-place rewrites only in general terms. | §4.1 markers; Q-9 | **Defer:** Claude Code only appends to transcripts. Name the case in Q-9 when convenient. |
| R3-3 | Info | AC-CL1's "keeps the same bytes" holds for a file that fails at step 4, which is the plain-text test case. A file with a valid header that is corrupt further in, and fails in steps 5 to 8, may already have been switched to WAL. | §3.3 "A file that is not a database"; AC-CL1 | **Apply in build (wording only):** say "a file that fails the step-4 read". |
| R3-4 | Info | A refused pass keeps a vanished or newly excluded session's records and state until `--allow-mass-delete` is used. | §4.7, Q-4 | **Accept:** this follows from the whole-pass refusal the owner asked for, and v1's `refresh.py` behaves the same. No change. |

No contradictions between the sections, the criteria, the assumptions table and §11. The count of 25 criteria is correct (9 from the PRD, 15 added, the close-out). Every criterion can be tested with the named seams (`collector._open`, `cwd_of`, the drive-type seam, `os.utime`, the injected `now` and clock).

Owner rows Q-2, Q-3 and Q-21 do not block this gate.

## Scope check

Every file the spec creates or edits is within `allowed_areas`: `local/db.py`, `local/collector.py`, `local/tests/*`, `exporters/board_config.py` and `board.config.json`. Nothing touches `site/**`. `derive`, `export_sessions`, `export_catalogue`, `records`, `schema` and `tests/test_export_sessions.py` are imported only, never edited. The revision-3 edits stay within `local/collector*` and `local/db*`. The AC-34, AC-42 and AC-44 counts correctly stay with PBI-008.
