# Chore review: chore/docs-last-refresh (PBI-008 documentation catch-up)

Reviewer: fresh-context Plan agent (read-only), 2026-09-12. Two rounds, saved verbatim by the orchestrator. Substantive chore (contract docs), so an explicit verdict, never a recorded skip.

## Round 1 — Verdict: CHANGES-REQUIRED

| id | severity | finding | evidence | required change |
|---|---|---|---|---|
| F1 | High | FR-59 and AC-49 still assert the refresher "ends the tick" / "makes no `write_db` call" when the script "prints `nothing to push`", citing the `/loop` prompt this diff edits — but `refresh.py` can no longer print that string. AC-35 similarly claims the script "shall report nothing to push" after a `generatedAt`-only change, while `test_generated_at_alone_is_not_a_change` now asserts the plan is the last-refresh write. | docs/prd/dispatch-board.md:323 (FR-59), :660 (AC-35), :677 (AC-49); CLAUDE.md:74; tests/test_refresh.py:117-120 | Supersede FR-59 and AC-49 as FR-46 was, and correct AC-35's wording and citation. |
| F2 | Medium | FR-46's superseded line cites `test_nothing_to_push_removes_a_stale_pending_file`, which does not exist; the real name is `test_nothing_to_push_replaces_a_stale_pending_file`. | docs/prd/dispatch-board.md:306; tests/test_refresh.py:108 | Fix the citation. |
| F3 | Low | The new `meta/lastRefresh` row states "UTC seconds with a Z" as a shared fact, but only the refresher writes that form; the collector writes the `+00:00` form. Both are valid. | CLAUDE.md:35; exporters/refresh.py:192; local/collector.py:582-583 | Qualify the claim. |
| F4 | Low | Missing blank line before `## The build it tracks (paused)`. | CLAUDE.md:148-149 | Add it. |

Everything else checked out: `refresh.py` really sets `meta/lastRefresh` on every plan and a refused plan discards the pending file and exits non-zero; `site/index.html`'s header logic matches the store-path row (20-minute rule, `--changes` token, silent when absent or unparsable); the merge-authorisation section is accurately bounded and `merge_allowed_by_agent` is a real, pre-existing field.

## Round 2 — Verdict: CHANGES-REQUIRED

| Finding | Status |
|---|---|
| F1 | Resolved — wording checked against `exporters/refresh.py`; accurate. |
| F2 | Resolved — both cited tests exist. |
| F3 | Resolved — the "never compare as strings" qualifier is accurate. |
| F4 | Resolved. |

| # | Severity | Detail |
|---|---|---|
| N1 | Medium | FR-52 still cites `Plan.test_commit_then_nothing_to_push`, renamed by PBI-008. Same class of staleness as F2. |
| N2 | High (scope/trust) | CLAUDE.md gains a "Merge authority" section asserting an owner authorisation for the building session to self-merge PBI PRs. Unrelated to the last-refresh fixes, unverifiable from the tree, and contrary to the usual no-self-merge practice. Flag for explicit owner confirmation and drop from this change's scope regardless of outcome. |

## Dispositions (orchestrator, 2026-09-12)

- **N1: applied.** FR-52's citation now names `Plan.test_commit_then_a_quiet_tick_prints_only_the_last_refresh_write`. A repo-wide search for the other removed test names returns nothing outside the struck-through text.
- **N2: kept, with the disagreement recorded.** The reviewer is right that the tree cannot prove the authorisation; it is the owner's own message in the session of 2026-09-12, quoted verbatim, and SPEC §Autonomy requires owner authority to be recorded verbatim where it is relied on. The section states the bounds the SPEC keeps: merge stays a human-authorised decision that the agent executes, it does not apply to a NO-GO, an unresolved condition or any circuit-breaker, and it is reversible. The orchestrator surfaced the objection to the owner rather than settling it silently; the owner can move it to its own change or withdraw it.
