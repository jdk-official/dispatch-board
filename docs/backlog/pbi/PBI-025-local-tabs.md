---
id: PBI-025
title: "Local tab and status records: the collector writes each project's Spec, Assumptions, Decisions, Backlog and GitHub tabs and its status into the local database"
status: Done
change_class: standard
depends_on: [PBI-019]
allowed_areas: ["local/tabs*", "local/collector*", "local/tests/**", "exporters/derive.py", "exporters/export_board.py", "tests/test_derive.py", "tests/test_export_board.py", "board.config.json", "exporters/board_config.py"]
blocked_areas: ["site/**", "local/records*", "local/schema*", "local/records.shapes.json", "local/server*"]
conflict_group: local-app
conflict_risk: Medium
requires_spec: true
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-025 — Local tab and status records

---

## Description

A singleton PBI, landed by intake on 2026-09-11. It closes a gap in the plan that the PBI-019 spec gate found (row Q-2 of `docs/backlog/specs/pbi-019-collector.md`; review note `docs/backlog/reviews/PBI-019/spec-review-r1.md`):
- FR-100 defines `tab` and `status` records for the local database, and PBI-003 built their shapes (`local/records.py`).
- No planned PBI writes them. PBI-019's collector writes sessions, runs, projects, the catalogue and last-refresh only.
- So once PBI-006 and PBI-007 land, the local app would show the Spec, Assumptions, Decisions, Backlog and GitHub tabs as "not exported yet", with no status tiles. That breaks the parent spec's aim of a board that needs no Claude session (parent spec, critical path).

This PBI makes the collector also write, for every project in `board.config.json`, the five `projectTabs` records and the project's status record, by the same rules as `export_board.py` and `refresh.py`.

**Why a spec is required (`requires_spec: true`).** The design has open choices the per-PBI spec must settle before code:
- **Network:** `export_board` lists pull requests with `gh`, which contacts GitHub, while PBI-019's collector is designed never to contact a network host. Options: leave `pulls` out locally, allow `gh` on a slower cycle as an explicit exception, or another source.
- **`carriedSince` (FR-190):** `carriedSince` and keep-last (FR-153) rely on the last exported tab persisting. Locally, the database record is the persistent copy.
- **Status fields:** where the status record's `title`, `message` and `metrics` come from locally. In the artifact store they are written by hand; `live` and `updatedAt` follow `refresh.py`'s rules.
- **Cadence:** tab reads (repo files and git) are heavier than transcript reads, so they may run less often than every pass.
- **Shared code:** tab assembly (`spec_tabs`, `git_tab`) lives in `export_board.py`, not `derive`. Moving it into `derive` keeps the collector from re-implementing it (parent spec Key decision: all derivations live in one shared module under `exporters/`).

**Why these areas:**
- `local/tabs*` is a new module for the tab and status pass.
- `local/collector*` is the hook into PBI-019's pass.
- `exporters/derive.py` and `exporters/export_board.py` are for moving tab assembly into the shared module, behaviour unchanged, with their tests.
- The config files are for any cadence or `gh` key the spec settles on.
- `local/records*` and `local/schema*` are blocked because the tab and status shapes already exist (PBI-003). `local/server*` is PBI-005's.

---

## Acceptance criteria

- [x] **T-1 Tab records match the exporter.** After a collector pass over a project whose repo holds a spec, the local database holds that project's `spec`, `assumptions`, `decisions`, `backlog` and `git` tab records. Each equals `export_board.py`'s document for the same repo, config and data file, ignoring `generatedAt` and any field the spec explicitly excludes locally (for example `pulls`). Tested on the synthetic repos used by `tests/test_export_board.py`.
- [x] **T-2 Keep-last and `carriedSince`.** When a tab's source goes missing after a pass wrote it, the next pass keeps the stored record and marks it with `carriedSince`, the time the carry began. The value holds on later passes while the source stays missing, and it is gone once the source returns, as FR-153 and FR-190 describe for the exporter.
- [x] **T-3 Status records.** The collector writes each project's status record (at its `statusDoc` path). `live` and `updatedAt` follow `refresh.py`'s rule, and the spec states the local source of `title`, `message` and `metrics`, each tested.
- [x] **T-4 Shapes.** Every tab and status record the collector writes validates against `local/records.py`'s shapes, with no change to those shapes.
- [x] **T-5 Network boundary.** A test with a patched `subprocess` proves the collector runs no network command, unless the spec approves `gh` as a named exception. If it does, the exception has its own criterion: cadence, timeout, and behaviour when `gh` is missing, which leaves `pulls` out with a warning, as v1 does.
- [x] **T-6 Behaviour unchanged for v1.** If tab assembly moves into `derive`, `export_board.py`'s output is byte-identical before and after on the same inputs, and no existing test is edited.
- [x] **Out of scope:** the page and its data adapter (PBI-006), the local server (PBI-005), log-on start (PBI-007), answers (C-16), and any change to record shapes or the schema.
- [x] **Worker close-out:** the three configured suites are green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`, `python -m unittest discover -s local/tests`), and the code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

Verified fresh at finalize on merged main `560e296` (PR #23, squash), 2026-09-12. Suites on that commit: `tests` **345**, `page.test.mjs` **111**, `local/tests` **304** — all OK, 0 skipped, against the 334 / 111 / 265 baseline (+11 backend, +39 local).

- **T-1** — `test_tabs_equivalence.TabEquivalence.test_one_pass_holds_the_documents_the_exporter_wrote`: after a pass, the local database holds each project's five tab records, each equal to `export_board.py`'s document for the same repo, config and data file. Non-vacuous on the `pulls` exclusion via `test_the_exporter_listed_pull_requests_and_the_collector_did_not`.
- **T-2** — `test_tabs.Carry.test_the_full_carry_cycle` and `test_the_local_carried_since_equals_the_exporters`: the carry begins, holds across passes while the source stays missing, and is gone once the source returns.
- **T-3** — first clause satisfied at the spec gate (a spec-authoring condition, not close-out-verifiable); the close-out half by `test_tabs.Status` (8 cases) and `StatusEquivalence` (3). `live` and `updatedAt` follow `refresh.py`'s rule; the local status record carries only those two, which the spec settled as forced rather than chosen — `exporters/refresh.py:184-185` writes exactly those and merges with `op: update`.
- **T-4** — `test_tabs.Shapes.test_every_record_written_validates_and_round_trips`, with `local/records*` and `local/schema*` untouched (both blocked).
- **T-5** — `test_tabs.NoNetwork.test_a_full_pass_runs_git_and_nothing_else`. The reviewer re-probed with its own patched `subprocess` over real repos: 12 subprocesses, all `git`, no `gh` or `curl`, and `FakeRun` never reaches a real subprocess.
- **T-6** — `test_export_board.GitTabUnchanged.test_git_tab_equals_the_pre_move_implementation` and `SpecTabBytes.test_the_four_spec_tabs_are_byte_identical_to_the_committed_fixture`, plus `test_derive.Git.test_derive_still_runs_no_subprocess`.
- **Worker close-out** — the three configured suites green on the head commit; code-review gate **GO** at round 2.

**The rule this PBI most needed to get right.** `projectTabs` has two writers — `export_board` owns the five tabs, `export_sessions` owns `findings` (PBI-011) — and neither may touch the other's. The owned-tabs set therefore comes from a local `tabs.OWNED` constant and **never** from `records.TAB_NAMES`, which has listed all six since PBI-026. Deriving it from `TAB_NAMES` puts the findings record outside the intended set, and deletion is *stored minus intended*, so the collector would have deleted the findings ledger on **every 60-second pass**. Round 1 of the spec gate (finding F-2) caught this before any code existed; reverting `tabs.owns` to `records.TAB_NAMES` still fails both `ForeignSuffixes` cases.

**The build was right and the spec was wrong.** `tabs.carry` deviated from §4.4 row 4's "Store nothing" for an already-carried record. Returning nothing drops the record from the intended set, so §6.2 would delete it on the **third** pass — losing the carry the rule exists to preserve. The code reviewer reproduced that from the literal wording and adjudicated the deviation correct; the spec is amended to **revision 4** to match the code, with the mechanism recorded. No acceptance criterion moved, and AC-TB3 still asserts zero `db.upsert` on a later carrying pass.

**The same bug class, found twice on different paths.** The spec gate's round 2 (N-4) caught that `UnicodeDecodeError` subclasses `ValueError`, so a confined per-project failure and the `load_data` whole-pass carve-out cannot both sit behind one block-level handler. Round 1 of the code review then found the identical hole where nobody had looked: `GIT_ERRORS` omitted `UnicodeDecodeError`, so one project's non-UTF-8 git output — an unlimited `git log %s`, or a branch name — escaped the confined region and failed **every pass indefinitely, writing nothing at all**, taking the healthy projects with it. Reproduced by the reviewer, fixed test-first with the error raised from git's own output (`FakeRun.raw` decodes real bytes with the call's own encoding, as `subprocess.run` does under `text=True`) rather than from a synthetic exception. Round 2 applied the same lens further: twelve pathological document shapes all degrade inside `READ_ERRORS`, and the one residual — `derive.git_doc`'s pipe unpack — was probed and found unreachable, because git folds a multi-line subject to one line.

**No regression to the board**, which four merged PBIs depend on: `_reference_git_tab` is the verbatim pre-move body, compared on keys, values **and key order** through one shared fake git over four input sets, plus byte-identity for the four deterministic spec tabs. The reviewer confirmed that fixture is genuinely pre-move by running it green against a clean `git archive` of the base tree, rather than accepting that the existing tests still pass.

**Restored guard, verified non-vacuous:** round 1's Low was that a `statuses`-zero tearDown guard had been removed rather than re-expressed, and the change report said "none removed". It is restored as an assertion of the rows a pass *should* write; under mutation (an extra status row for an unconfigured project) it fails **57 of 70 scenarios**. The change report now reads "two re-expressed, one removed".

**A tooling gap found along the way.** `tools/change_report_schema.py` and `tools/cell_report_schema.py` have no `__main__`, so `python <tool>.py <file>` exits 0 on any input, including garbage — a green light that checks nothing, which the orchestrator had been citing all session. All 46 change- and cell-reports in this repo were then validated properly by importing the modules and calling `validate()`, with a prior assertion that the validators reject garbage; every one is genuinely valid. `run_report_schema.py` and `handover_schema.py` do validate from the CLI. Worth raising with the backlog-delivery plugin owner.

**Known limitation, by design:** `pulls` is excluded locally (spec Q-2), so the local app's GitHub tab carries no pull requests. Fetching them needs a process outside the collector, which is deliberately network-free.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_spec: true`: refine a per-PBI spec from the parent spec and the PBI-019 spec, and have it independently reviewed before any code is written.

**Owner authority:** on 2026-09-11 the owner approved creating this item, verbatim: "Q-2: yes." That answered the PBI-019 spec's question: "Who writes `tab` (`projectTabs`) and `status` records into the local database? … a new PBI through pbi-intake is recommended". This records the item's existence and scope. Promotion from Proposed to Ready is still a curation step.

**Ordering:** it depends on PBI-019, the collector it extends, and it shares the `local-app` group. It must land before PBI-007's end-to-end check claims a board that needs no Claude session.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | **passed 2026-09-12** | `docs/backlog/specs/pbi-025-local-tabs.md` revision 3. Round 1 **CHANGES-REQUIRED** (2 High, 4 Medium, 2 Low, 1 Info) — all nine applied, none deferred; round 2 **APPROVE-WITH-NOTES**, with N-1..N-4 applied as a revision-3 text pass the reviewer stated needs no re-review, and N-5 (stale front matter on the PBI-019 and PBI-005 spec files) fixed separately at source. Reviews: `docs/backlog/reviews/PBI-025/spec-review-r1.md`, `-r2.md`. **The gate earned its keep:** round 1's F-2 found that deriving the local deletion set from `records.TAB_NAMES` would delete the `findings` record on every 60-second collector pass once PBI-026 landed — `projectTabs` has two writers (`export_board` owns the five suffixes, `export_sessions` owns `findings`), so the set is now scoped to a local `tabs.OWNED` constant. Round 2 also caught N-4: `UnicodeDecodeError` is a subclass of `ValueError`, so the confined-failure rule and the `load_data` carve-out cannot both be met by a block-level `except ValueError`. Round 2 further **withdrew round 1's F-9** as incorrect (the cited citation drift did not reproduce) and confirmed four real citation errors the author found in its place. |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-12 (round 2 GO) | Round 1 **GO-WITH-CONDITIONS** (0 Critical, 0 High, 1 Medium, 1 Low), both applied; round 2 **GO with zero findings**. The Medium was a real bug the reviewer reproduced: `GIT_ERRORS` omitted `UnicodeDecodeError`, so one project's non-UTF-8 git output failed every 60-second pass indefinitely, writing nothing. Round 2 re-measured rather than read — rebinding `GIT_ERRORS` to the round-1 tuple reproduces the original failure exactly; the restored tearDown guard fails 57 of 70 scenarios under mutation; the `tabs.owns` mutation still fails both `ForeignSuffixes` cases; and the network probe saw 12 subprocesses, all `git`. `docs/backlog/reviews/PBI-025/findings-r1.json`, `findings.json`, `cell-report.json` |
| No-self-merge gate | always | passed 2026-09-12 | PR #23 squash-merged `560e296` by the orchestrator under the owner's standing merge authorisation (`merge_allowed_by_agent` set `true` from `false` under that authority), on a round-2 GO. Landing: resolved squash (declared) / observed squash, level `record`. |
| BOARD-tidy gate | always | passed 2026-09-12 | two-part Done write: `docs/backlog/done-log.md` entry + BOARD `## Done` index row |
