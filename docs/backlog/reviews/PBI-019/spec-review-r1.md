# Spec-gate review: PBI-019 collector spec, revision 1

Reviewer: `pbi-review`, same-vendor-subagent tier (built-in Plan agent, clean context, read-only), 2026-09-11. Saved verbatim by the orchestrator.

Verdict: CHANGES-REQUIRED

The design is sound. The state design is complete: it persists per-session and per-agent derive state, cursors, meta and the last result, and recomputes all cross-session glue every pass. It matches the exporter's tail and cache rules (`export_sessions.py:227-288`), so incremental reads plus `derive` can reach AC-64 equivalence. Three Medium defects in the text would produce wrong behaviour if built literally. All three are small edits and none needs the owner.

## Findings

| ID | Sev | Finding | Evidence | Required change |
|---|---|---|---|---|
| S-1 | Medium | The opening order is wrong. Step 6 checks the `collector_*` columns before step 7 creates those tables, so every fresh file is refused. Separately, WAL mode (which persists in the file) and `create_schema` change a foreign file before the check refuses it: the tables are added and it is stamped version 1. | spec §3.3 steps 4-7; `schema.py:4-6`; PBI-019.md "Foreign tables" follow-up | First run a read-only `table_info` check on the tables that already exist, and refuse on a mismatch. Missing tables are fine. Only then set WAL, run `create_schema`, create the state tables, and re-check. |
| S-2 | Medium | A failed feed can count records twice. `add_record` and `add_agent` change state in place. If a raise comes part-way through the new lines, the cached state keeps the records fed so far. The next pass feeds them again, so skill uses and rejects are counted twice. The spec says the main state "stays where it was" but gives no way to achieve that, and says nothing about the agent's cursor or state. AC-64 fixtures never raise mid-feed, so no test would catch it. | §4.4 steps 2 and 4; `derive.py:417-465`, `296-305` | Feed a copy (decoded from the stored text, or deep-copied) and swap it in only on success, for both main and agent files. Add a test: raise on line k with the cache warm, then check the next pass counts it once. |
| S-3 | Medium | The codec and the reset rule depend on today's field list. Feature PBIs will add fields to `new_session` and `new_agent` (the derivation rule). A new set field raises `TypeError` and freezes the session. A new dict with `None` keys is silently written with the key `"null"`. A key missing from old stored state raises `KeyError`. The only reset trigger is a `PARSER_VERSION` bump. | §4.3 codec and versioning; parent spec line 270 | Use a generic recursive tagged codec (any set, any dict with non-string keys). Also reset when the decoded key set differs from `derive.new_session(sid)` or `new_agent()`. Add a handoff line for feature PBIs. |
| S-4 | Low | An excluded session's opening lines are read again on every pass through `cwd_of`, and the whole file is read if it has no `cwd` line. This conflicts with FR-86 and with CLAUDE.md's "never read". The exporter does the same, so this is parity. | §4.1 step 5 | Either accept it as a documented parity exception, or store a marker with no content, keyed by `(dev, ino)`. |
| S-5 | Low | A vanished transcript of an unlinked session whose stored `last` is already past the window is given reason `other`. After a long absence, Claude Code's own transcript cleanup can then trip the guard and stall the board. | §4.7 reasons | Treat it as `age` when the session is unlinked and its stored `last` is past the window. |
| S-6 | Low | A-47 is still an open PRD row, but the spec treats it as settled. The spec also reads FR-184's "finds no sessions" clause as not blocking passes whose deletions are all by age, and does not say so. | PRD summary (A-45 to A-48 open); spec §4.7, AC-CL7 | Add owner row Q-21, state the interpretation, and test "no sessions, only age deletions → commit". |
| S-7 | Low | A refusal in loop mode shows only on the stderr of a Task Scheduler process. The board stalls with no visible reason. | §5 loop mode | Add a handoff so PBI-007 captures stderr to a log file. |
| S-8 | Low | `BEGIN IMMEDIATE` holds the write lock across every file read and the catalogue export. On a first full read, a concurrent `--once` run can exceed its 10 s busy timeout, fail with "database is locked" and exit 1. | §3.3 step 3, §3.5 | Document this, or print a clear "another collector holds the lock" message. |
| S-9 | Low | "Resolved absolute form" is ambiguous. A symlink or junction into a share is caught only by `realpath`. Local `\\?\C:\` paths are refused as network paths. That fails safe and follows FR-180 literally. | §3.2 | Name `os.path.realpath`, and record that `\\?\` paths are refused on purpose. |
| S-10 | Low | The state tables are a disposable cache, but a column mismatch in them makes the collector refuse to start. | §3.3 step 6 | Drop and recreate `collector_*` (a full re-read) instead of refusing. |
| S-11 | Info | The guard is checked after the upserts have run. The rollback makes this safe, but the order is unclear. | §4.6 steps 3-5 | Compute the guard before any write. |
| S-12 | Info | I checked the AC-34 claim and it holds. `tests/test_refresh.py:86` asserts `1+5+2+4+1` (12 sets plus 1 update), and PRD line 659 says 12. FR-103 (PRD line 456) gives the refresher half to PBI-008. `PBI-008.md:37-39` has the same out-of-date wording. | as cited | Q-15's correction must cover `PBI-008.md` too. |
| S-13 | Info (standards) | The tests import `tests/test_export_sessions.py`, which breaks the PBI-003 §5 convention ("nothing is imported from `tests/test_*.py`"). It is justified by AC-64's wording ("the synthetic transcripts used by `tests/`"). | §7; pbi-003 spec §5 | Record the deviation. |

## Owner questions

| Q | Needs owner | Blocks building | Recommended default |
|---|---|---|---|
| Q-1 state tables | **No.** The reviewer settles it: this is not a PBI-003 schema change. The tables sit outside `records.TABLES`, `schema.py` and `user_version`, and PBI-003 §4 governs the records schema's healing limits. `ATTACH` is correctly rejected, because commits across attached files are not atomic in WAL mode. | No | Keep the tables, with S-10. PBI-005's spec must ignore `collector_*`. |
| Q-2 tab and status records | **Yes. This is a genuine plan gap.** FR-100 defines tab and status records "used by the collector". Parent line 269 aims at "no Claude session needed". No PBI in the table writes these records locally. | Not PBI-019. It does block PBI-007's end-to-end claim and retiring v1. | A new PBI through pbi-intake. Do not widen PBI-019: `export_board` calls `gh`, which breaks §5's "never contacts any network host", and its `carriedSince` logic needs the `out/` folder to persist. |
| Q-3 FR-185 "only" | Confirmation only, as a PRD wording fix | No | Keep the spec's reading. The literal reading contradicts the `exclude` privacy rule and AC-64. Amend FR-185 to say "prunes by age only …; other deletions go through FR-184". |
| Q-21 (new) A-47 is open | Yes | No | A-47's own default. Wrong pruning can be undone: widening `days` re-reads the transcripts. |
| Q-15 | Orchestrator | No | Correct both `PBI-019.md` and `PBI-008.md`. |

None of the ASSUMED defaults is high-impact enough to block building. Every record can be rebuilt from the transcripts and the config.

## Scope check

Every file created or edited is within `allowed_areas`. The spec only reads `exporters/derive.py`, `export_sessions.py`, `export_catalogue.py`, `local/records.py`, `local/schema.py` and `tests/test_export_sessions.py`. It needs no edit to `refresh.py`, `local/records*`, `local/schema*` or `derive.py`. The fixes for S-1 to S-10 all stay in `local/db*` and `local/collector*`. Q-12's follow-up (moving the glue into `derive`) needs `exporters/**` and is correctly deferred.
