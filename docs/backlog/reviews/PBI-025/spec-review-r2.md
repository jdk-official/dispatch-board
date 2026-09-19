# Spec-gate review — PBI-025 (revision 2, round 2)

Reviewer: `pbi-review`, same-vendor-subagent tier (clean-context, read-only), 2026-09-12. Live tree at `5baa922` (PBI-026 merged). Saved verbatim by the orchestrator.

**Verdict: APPROVE-WITH-NOTES**

All nine round-1 findings are genuinely resolved in the spec text, not just in §11's table. The notes below are stale facts created by PBI-026 landing mid-gate; none changes a rule, and none can produce a wrong build.

## Round-1 resolution table

| id | status | what I personally checked |
|---|---|---|
| F-1 | **Resolved** | §7.3 and AC-TB10 (`:754-761`, `:919-923`) assert `set(records.TAB_NAMES) >= set(tabs.OWNED)`. Green against the live six-name tuple (`local/records.py:91`). Exact-equality half still bites: `SHAPES['tab']` (`local/records.py:57-60`), `SHAPES['status']` (`:61-64`), `TABLES['tab']`/`['status']` (`:116-117`) and `SCHEMA_VERSION` are all untouched by PBI-026 (its diff is one line, `git show 5baa922 -- local/records.py`), so a real shape, column or schema change still fails the canary, and removing a name from `TAB_NAMES` still fails containment. |
| F-2 | **Resolved** | I grepped every `TAB_NAMES` occurrence in the spec (16 hits). Every intended, carry, deletion and guard-grouping set is scoped to `tabs.OWNED` — §4.3 `:336-337`, §4.4 `:353-354`, §6.1 `:548-556`, §6.2 `:595-598`, §6.3 `:636-645`. The surviving `TAB_NAMES` references are narrative, the read-only canary, the test monkey-patch, and explicit negatives. **No deletion or guard path reads it.** The deletion trigger of revision 1 is removed (`:585-591`). §2.1's evidence checks out verbatim: `exporters/export_board.py:7-9`, `:39`, `:277-285` (suffix filter `rsplit('.', 1)[-1] in TABS`), `exporters/export_sessions.py:292-293`, `exporters/refresh.py:45-47`, `local/records.py:103`. §6.1 partitions on the suffix after the first `.` and §6.3 groups on the part before it — consistent with `records.py:238` and `refresh.py:149`. |
| F-3 | **Resolved** | §7.2/AC-TB11 replace the fixture with the in-run `_reference_git_tab` comparison including key order. Non-reproducibility confirmed at `exporters/export_board.py:143-144` (`repoPath`, `head`, `commits[].sha/.date`). |
| F-4 | **Resolved** | §7.3 `:780-790` and AC-TB5 now assert row counts and full `id, doc` text from a **second** connection, plus zero `upsert`/`delete`. `local/db.py:175-186` is exactly `class Changes` with "Tells a reader when another connection has committed" — the claim is accurate, and round 1's `:175-184` was the short cite. |
| F-5 | **Resolved** | `derive.git_default` added; `git_doc` takes `ahead_out`/`shortstat_out` and applies the emptiness rule itself (§3.2 `:186-204`), matching `export_board.py:129` and `:141-142`. §7.1 `:688-692` now exercises the rule through the signature — it can. |
| F-6 | **Resolved** | §4.2.1's blast-radius argument is exact: `local/collector.py:643-648` logs one line and returns 1, and the loop at `:696-708` ignores that return and sleeps. The confinement covers both modes round 1 named: the ADR folder is read by `os.listdir`/`read` (`export_board.py:106-108` → `PermissionError`) and a non-UTF-8 spec by `read` (`:47-49` → `UnicodeDecodeError`). The `load_data` carve-out is justified on `export_board.py:22-25` and `:273-275`, read verbatim. AC-TB14 is verifiable (four cases, observable commit/no-commit). |
| F-7 | **Resolved** | AC-TB4 asserts a non-empty deletion set; AC-TB8 starts from a stored status record and asserts it readable with `doc` unchanged; AC-TB9 requires a github.com `origin` (so `github_origin`, `export_board.py:159-164`, is true) and a non-empty argv list. |
| F-8 | **Resolved** | T-3's first clause marked satisfied-at-gate (`:858-863`). §4.7 `:426-434` correctly states `board_config.ID` is `^…$` with `.match` (`exporters/board_config.py:17`, `:118`) versus `fullmatch` (`local/records.py:207`). §7.4 `:813-817` makes editing `test_conformance.py` a stop-and-report. |
| F-9 | **Resolved, finding corrected** | See below. |

## Adjudication of F-9 — the author is right, round 1 was wrong

I read both sites directly. `exporters/board_config.py:118` is `if not isinstance(pid, str) or not ID.match(pid):` and **:119 is the raise** — round 1 said 120. `:130-132` is **exactly** the project dict (`out.append({'id'…` at 130, `'statusDoc': status, 'docs': …}` at 132) — round 1 said 131-133. **Neither drift reproduces. Round 1's F-9 was incorrect and should be read as withdrawn.**

The four errors the author found instead are all real, and all now fixed in revision 2:

- `exporters/refresh.py:27-29` is about `meta/lastRefresh`, not a status document. The claim now rests on `MANAGED` at `:44` — correct, `status` is not in it.
- `refresh.py:43` is the `EXPORTERS` tuple; the unconditional run is `run_export(out)` at `:223`. Confirmed.
- `derive.spec_docs` ends at `:938`; `:943` is `PURPOSE_MAX`. Confirmed.
- `local/collector.py:585-588` is the rollback, `:589-591` the cache-invalidate-and-re-raise. Confirmed.

## New findings

| id | sev | finding | required change |
|---|---|---|---|
| N-1 | Low | §2's evidence row (`:72`) still asserts `TAB_NAMES` is the five, citing `local/records.py:91` — now the **six**. §2's bullets (`:84`, `:91`), Q-3 ("PBI-026 is in code review") and §11 narrate PBI-026 as unlanded; it merged at `5baa922`, status `Done` (`docs/backlog/pbi/PBI-026.md:4`). No rule depends on any of it — §2.1 supersedes and every set is `OWNED`-scoped — but the build must not meet a false statement in its own contract. | Refresh §2's row and tense to the merged reality; leave §2.1's rules exactly as they are. |
| N-2 | Low | §7.3 (`:763-764`) and AC-TB13 (`:936`) monkey-patch `records.TAB_NAMES` "so the record is storable". That is now unnecessary (`findings` is already a valid id) and was always inert: `_ID_FORMS['tab']` is compiled **at import** from `TAB_NAMES` (`local/records.py:103`), so rebinding the tuple changes no validation. | Drop the patch; store the `findings` record directly. The criterion is unchanged and still non-vacuous. |
| N-3 | Info | Citation drift from the same merge (+73 lines in that file): §2 cites `local/tests/test_conformance.py:342`, `:344-347`, `:401-413`; the live lines are `:353` (`('tab', 'alpha.findings')`) and `:415` (the kinds set). `:82` and `:269-270` are still exact. | Refresh. |
| N-4 | Low | `UnicodeDecodeError` **is a subclass of `ValueError`**. §4.2.1's rows 2 and 4 therefore cannot both be met by a block-level `except ValueError` around §4.3 step 2; the handlers must be scoped per call, with `load_data` outside the confined block. AC-TB14's fourth case catches a build that gets it wrong, but one sentence removes the trap. | State it in §4.2.1. |
| N-5 | Info | §1 cites the PBI-019 and PBI-005 specs as "approved"; their front matter still reads "awaiting round 3" / "awaiting round 2" (`pbi-019-collector.md:7`, `pbi-005-local-server.md:7`) although both PBIs merged (`b23df89`, `3e3ec44`). Not this spec's to fix. | Flag to the owner as close-out bookkeeping on those two files. |

## Owner questions

14 rows, Q-1…Q-14. Q-3 alone is OWNER, correctly, and is non-blocking (backlog curation). Q-1's settlement is forced by the equivalence rule, not chosen: `refresh.py:184-185` writes exactly `live` and `updatedAt` and merges with `op: update`. Its rejected seed source is real — `snapshot/meta/status.json` exists and holds `title`, `message`, `metrics` — and the rejection (dated backup, one project, not re-readable) is sound. Q-2 keeps the exclusion, drops "permanently", carries an FYI. Q-14 is recorded in §11 as an explicit restatement. **No settled row smuggles a design decision, and nothing that needs the owner is marked settled.** F-6's operational choice, round 1's one complaint here, is now a stated rule with evidence rather than a footnote.

## The 21 criteria

6 + 14 + close-out = 21, as claimed. AC-TB13 and AC-TB14 are both mechanically verifiable with no human demonstration (stored-record identity, `db.delete` counts, commit/no-commit, exit code). No criterion is now vacuously satisfiable: F-7's three each carry an asserted non-empty precondition, and AC-TB5's "wrote nothing" is observed on table contents rather than a pragma that cannot move.

## Scope check — passes

Every file in §4.1 is inside `allowed_areas` (`docs/backlog/pbi/PBI-025.md:7`): `local/tabs*`, `local/collector*`, `exporters/derive.py`, `exporters/export_board.py`, `tests/test_derive.py`, `tests/test_export_board.py`, `local/tests/**`. No edit is specified or implied to `local/records*`, `local/schema*`, `local/records.shapes.json`, `local/server*` or `site/**` (`:8`). `board.config.json` and `exporters/board_config.py` remain deliberately unused — legitimate. PBI-026 being `Done` retires the `local/tests/**` overlap; §7.4's unmodified-`Fixture` rule is now belt-and-braces rather than load-bearing, and should stay.

Apply N-1 through N-4 as a revision-3 text pass; they need no re-review.
