# Spec-gate review — PBI-025 local tab and status records (revision 1, round 1)

Reviewer: `pbi-review`, same-vendor-subagent tier (clean-context, read-only Plan agent), 2026-09-12. Saved verbatim by the orchestrator.

**Verdict: CHANGES-REQUIRED**

The blocked-areas verdict is sound and I could not break it. The findings below are in the criteria and the deletion/carry rules, not in the record shapes.

## Findings

| id | sev | finding | evidence | required change |
|---|---|---|---|---|
| F-1 | **High** | AC-TB10 pins `records.TAB_NAMES` to "its value at the start of this PBI". PBI-026 is **In Progress** and exists solely to widen `TAB_NAMES` to accept `findings`. Once both land on main, this canary fails the `local/tests` suite — the spec's own close-out criterion. The spec asserts the two are parallel-safe (§2) while adding a test that is not. | `local/records.py:91`; `docs/backlog/pbi/PBI-026.md:2-8` (`status: In Progress`, allowed `local/records*`) | Re-express the canary as containment, not equality: assert `set(TAB_NAMES) >= {'spec','assumptions','decisions','backlog','git'}`, plus exact equality for `SHAPES['tab']`, `SHAPES['status']`, `TABLES['tab']`, `TABLES['status']`, `SCHEMA_VERSION`. |
| F-2 | **High** | §6.2 deletes a tab record "when its tab name is no longer one of the five". `projectTabs` is a **two-writer collection**: `export_board` owns five suffixes, `export_sessions` owns `findings`, and each is explicitly forbidden to touch the other's. After PBI-026 the local tab pass, computing its intended set over `records.TAB_NAMES`, would delete a `findings` record every pass — and in the guard's per-project grouping, a `findings`-only project would also trip the emptied-tabs clause. | `exporters/export_board.py:7-10`, `:277-284`; `exporters/refresh.py:45-47` | State that the intended/deletion set is scoped to the **five suffixes this pass owns**, read from a local constant, never from `records.TAB_NAMES`; a tab id with any other suffix is left untouched and excluded from the guard's grouping. |
| F-3 | **Medium** | AC-TB11/§7.2 require `export_board.main`'s written bytes to equal "a fixture captured from the pre-move implementation… generated once during the build, from the current code, and committed". Not achievable: the git tab carries `repoPath` (a temp dir), `head`, and `commits[].sha`/`.date` from a freshly built synthetic repo — none reproducible across runs. And a fixture captured *after* the move proves nothing. | `exporters/export_board.py:143-146`; `local/tests/test_conformance.py` `HAS_GIT` guard | Replace with an in-run equivalence: keep a reference copy of the pre-move `git_tab` body in the test and assert `git_tab(...) == reference(...)` on identical captured stdout, plus byte-identical `main` output for the four deterministic spec tabs. |
| F-4 | **Medium** | AC-TB5 and §7.3 assert "`PRAGMA data_version` unchanged" to prove a refused pass wrote nothing. SQLite does not bump `data_version` for changes on the *same* connection — that is precisely what `db.Changes` documents. On the collector's own connection the assertion is vacuous. | `local/db.py:175-184`; `local/collector.py:186` | Observe from a second connection, or assert on the tables directly (row counts and `doc` text unchanged). |
| F-5 | **Medium** | §3.2's signature `git_doc(root, branch, default, log, files, status, remotes_raw, head, ahead, shortstat, now)` leaves two *derivations* in the caller and therefore duplicated in `local/tabs.py`: the `master`/`main`/`''` selection, and the "empty when there is no default or current branch" rule. §7.1 then tests `git_doc` for exactly that emptiness rule, which its signature cannot exercise — an internal inconsistency, and drift the equivalence suite would not catch until the documents already differ. | `exporters/export_board.py:129`, `:141-142` | Add `derive.git_default(master_out, main_out)` and have `git_doc` take the raw `ahead`/`shortstat` stdout plus `branch`/`default`, applying the emptiness rule itself; fix §7.1 accordingly. |
| F-6 | **Medium** | §4.2: "A raise inside `tabs.build` is not caught: it fails the pass before any transaction opens, so nothing is written." Blast radius is larger locally than on the board. A `PermissionError` on one project's ADR folder, or a non-UTF-8 spec file, kills **every** record of that pass — sessions, runs, projects, catalogue, and `lastRefresh` — every 60 s, indefinitely. `_one` logs one line and loops. The board's equivalent is a human-watched tick. | `local/collector.py:638-648`, `:582-583`; `exporters/export_board.py:47-49` | Confine a per-project read/git failure to that project (warn, build no tabs, carry per §4.4). Keep the whole-pass failure only for `load_data`'s `ValueError`, where matching the exporter protects build state — and say so explicitly. |
| F-7 | **Low** | Vacuously satisfiable criteria: AC-TB4 ("every tab deletion carries `other`; none `age`"), AC-TB8 ("no pass deletes a status record"), AC-TB9/T-5 ("invokes `git` and nothing else"). Each is true of an empty result. | — | Add a non-empty precondition to each: ≥1 actual tab deletion; a pass that removes a configured project while a status row exists; ≥1 project with a github.com origin remote. |
| F-8 | **Low** | T-3 as restated ("the spec states the local source… ") is a spec-authoring condition, not close-out-verifiable; only its AC-TB7 half is. §4.7's claim that `board_config`'s id check "is exactly `records._PROJECT_ID`" overstates: `board_config.ID` uses `match`, `records` uses `fullmatch` (a trailing newline diverges — already documented at `local/records.py:93-94`). §7.4 reuses `test_conformance.Fixture`; if it must be modified, the §2 parallel-safety claim with PBI-026 breaks. | `exporters/board_config.py:17`, `local/records.py:93-98`, `:207` | Mark T-3's first clause satisfied-at-gate; soften §4.7's wording; state that `Fixture` is consumed unmodified. |
| F-9 | **Info** | Citation drift, all ±1 line and none load-bearing: `exporters/board_config.py:118-119` (the raise is at 120), `:130-132` (the dict is 131-133). | — | Refresh at revision 2. |

## The COHERENT-AS-WRITTEN claim — verified, and it holds

I re-checked every cited line in the live tree.

- `local/records.py:57-60` — `'tab': {'required': {'generatedAt': 'str'}, 'optional': {'source': 'str'}}` ✓. The "extra fields allowed and kept at every level" rule is at `:18-21` and is enforced by `_check_spec` (`:174-191`), which iterates only listed fields ✓. So `carriedSince`, `repoPath`, `commits`, `byDir`, `pbis`, `later` all pass.
- `:61-64` — `status` has `'required': {}` and five optional fields ✓; a first-write `{live, updatedAt}` validates.
- `:88-89` COLLECTION, `:91` TAB_NAMES (equals `export_board.TABS` at `exporters/export_board.py:39`), `:103-104` id forms, `:206-208` the `meta/lastRefresh` refusal, `:112-119` TABLES, `:238` the split-on-first-dot — **all accurate as cited**.
- I went further than the spec: `local/schema.py:24-27` builds the DDL from `records.TABLES.values()`, so `project_tabs` and `statuses` already exist at `SCHEMA_VERSION = 1`, with `idx_project_tabs_project` (`:17`). `db.open_db` column check (`local/db.py:145-147`) therefore passes untouched.
- Every document the pass must write carries `generatedAt` as a `str`: `derive.spec_docs` at `exporters/derive.py:918, 933, 934, 937`, and `git_tab` at `:143`. Both `statusDoc` forms match `_ID_FORMS['status']`.
- `local/tests/test_conformance.py:342` already asserts `'tab'` and `'status'` among the kinds round-tripped, and `:344-347` both status forms — so this is proven behaviour, not inference.

**Judgement: no tab or status document this spec requires would fail the existing shapes, and no schema change is implied.** The PBI-005-style circuit-breaker risk is not present here. The blocked-area risk that *does* exist is the opposite one — F-1, a test that hard-codes a blocked file's current value that a concurrent PBI is changing.

## Owner questions

| row | author | my call | recommended default |
|---|---|---|---|
| Q-1 status `title`/`message`/`metrics` | OWNER, "blocks a complete build" | **Settle at this gate.** Not a blocker, and the spec contradicts itself by calling its own default "safe to build against and reversible". Writing only `live`/`updatedAt` and merging is *exactly* what `refresh.py` does (`exporters/refresh.py:184-185`), so the equivalence rule already mandates it. | Build the default. Re-mark "settled; a config-sourced status block is a follow-up PBI." Note for the owner (non-blocking): `snapshot/meta/status.json` exists and is an on-disk copy — worth naming as a rejected seed source. |
| Q-3 `findings` tab | OWNER (curation) | **Correctly OWNER, correctly non-blocking.** | Raise the follow-up PBI now, gated on PBI-026. Tighten §6.2 per F-2 either way. |
| Q-2 `pulls` excluded **permanently** | unmarked | **Settle at gate, but surface.** The exclusion is forced by FR-96/NFR-17 and pre-authorised by T-1 ("any field the spec explicitly excludes locally, for example `pulls`"). The word *permanently*, and "it needs a separate process outside the collector", is a product-scope reduction the owner should see. | Keep the exclusion; drop "permanently"; record as an FYI, not a gate blocker. |
| Q-14 T-6 wording | unmarked | **Settle at gate.** The literal reading is genuinely unprovable — `tests/**` is not an allowed area, only the two named files are. The reinterpretation is forced, not smuggled. | Accept, and record it as an explicit restatement of a PBI-file criterion in §11. |
| Q-4, Q-5, Q-6, Q-7, Q-8, Q-9, Q-10, Q-11, Q-12, Q-13 | unmarked | Agreed — all settled, all well-argued. Q-4 needs the F-5 correction; Q-10's before-the-lock placement is right and its citation (`local/collector.py:556-566`) is accurate. | — |

No "default chosen" is smuggling a design decision past the gate other than §4.2's whole-pass failure mode (F-6), which is a real operational choice presented as a footnote rather than a question.

## Scope check — passes

Every file in §4.1 is inside `allowed_areas`: `local/tabs.py`, `local/collector.py`, `exporters/derive.py`, `exporters/export_board.py`, `tests/test_derive.py`, `tests/test_export_board.py`, `local/tests/test_tabs*.py`. No edit to `local/records*`, `local/records.shapes.json`, `local/schema*`, `local/server*` or `site/**` is specified, and none is implied by anything I verified. `board_config.json` and `exporters/board_config.py` are left unused, which is legitimate.

Two scope caveats for the build, both covered above: `local/tests/test_conformance.py` must be consumed, not modified (F-8), and AC-TB10's canary must not pin a value PBI-026 owns (F-1).

Re-run the gate on revision 2 once F-1 through F-6 are applied or explicitly deferred with rationale.
