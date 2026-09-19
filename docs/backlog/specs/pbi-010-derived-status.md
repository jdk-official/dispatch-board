---
id: SPEC-PBI-010
title: "Work-item status derived from runs, shown beside the hand-kept state during a shadow period"
pbi: PBI-010
parent: docs/backlog/specs/dispatch-board.md (revision 5, approved)
revision: 3
status: approved at spec-gate round 2 (APPROVE-WITH-NOTES; N-1 through N-4 applied in revision 3 as a text pass needing no re-review). Q-17's gap is recorded with a default: option (b), a pre-registered follow-up at finalize, replaced by option (a) if the owner grants the one file before the build.
date: 2026-09-13
grounded_at: 560e296
reviews: docs/backlog/reviews/PBI-010/spec-review-r1.md (round 1, revision 1, CHANGES-REQUIRED); docs/backlog/reviews/PBI-010/spec-review-r2.md (round 2, revision 2, APPROVE-WITH-NOTES)
---

# PBI-010: Work-item status derived from runs, beside the hand-kept state (per-PBI spec)

**Citations note (revision 3, N-4).** Every citation below is grounded at `560e296`. `main` has since
moved to `4bbbad8` (PBI-014, PR #24), which touched `exporters/derive.py` (+104 lines), `site/index.html`
(+79) and `tests/page.test.mjs` (+149). The citations are correct at `560e296`; they have shifted on
`main` — for example `when()` is now `site/index.html:282` and `EQ_PROJECT_TABS` is
`tests/page.test.mjs:1400` (both verified by direct read against `4bbbad8`). **The builder must re-ground
each citation against its own base before relying on the line number.** This spec is not re-cited line
by line for the moved base.

## 1. Intent

Today each work item's state on the Backlog tab comes only from hand-kept `buildState` in
`projects/<projectId>.json`, which the build session edits by hand (`CLAUDE.md:123-129`;
`exporters/derive.py:843-846`, read into the backlog rows at `:907-915`). When that edit is forgotten
the board is wrong and nothing on it says so.

**The concrete failure this PBI exists for.** On 2026-09-12 PBI-005, PBI-006, PBI-011, PBI-025 and
PBI-026 were merged and fully reviewed while `buildState` did not list them. The Backlog showed each
as "Not started" for hours. `projects/dispatch-board.json` as committed at `560e296` still lists only
eight PBIs (017, 018, 021, 022, 023, 003, 001, 013), with PBI-001 as `conditions` although PR #10 had
merged. The close-out edits are in the uncommitted working tree, not at that commit.

After this PBI:

- **Derived status.** Every project document `projects/<projectId>` carries a derived state for every
  work item that a code-writer, test-writer or code-reviewer run in that project's linked sessions names
  (FR-113). It uses the same shared derivation for the published board and the local app.
- **Shadow period.** While a project's shadow period is on (the default), the Backlog tab shows the
  derived state beside the hand-kept state and flags every work item where they differ (FR-175,
  AC-110). Each difference is grouped by direction, so a stale hand-kept file (the 2026-09-12 case)
  reads differently from something the runs cannot prove. A work item that no run names and that is
  hand-kept "Not started" is **no evidence**, its own outcome: not flagged, and **never counted as
  agreement** (§6.1). The panel also states when the linked sessions were last active, so the owner can
  see how old the evidence itself is.
- **Overrides.** Hand-kept `review`, `open` and `commit` keep overriding derived values (FR-176,
  AC-111; parent row 15).
- **The switch.** A per-project config key sets the shadow period (A-48 assigns it to this spec).
  Setting it to `derived` retires the hand-kept `state` for that project. Flipping it is the owner's
  decision (S-39). This spec defines the mechanism, not the date.

**Sources.**

- **PRD, revision 3:**
  - FR-113 (`docs/prd/dispatch-board.md:478`), FR-175 (`:479`), FR-176 (`:480`);
  - AC-78 (`:712`), AC-110 (`:750`), AC-111 (`:751`);
  - A-23 (`:833`, heuristic links), A-32 (`:799`, "the PRD defaults as written"), A-48 (`:837`);
  - S-39 (`:158`), C-20 (`:594`, `projects/*.json` is never deleted);
  - NFR-9, NFR-10, NFR-13, NFR-14 (`:548-553`) and NFR-22 (`:570`).
- **Brief** candidate feature 4: "Review verdicts on runs naming a PBI give done / conditions open /
  partly built" (`docs/brief/raw-notes.md:188-189`).
- **Parent spec, revision 5:**
  - the shared-derivation decision (`docs/backlog/specs/dispatch-board.md:87`) and the derivation rule
    (`:270`);
  - row 15 (`:299`);
  - PBI-010's areas and the three things its spec must define (`:249-252`);
  - the owner go-ahead requirement (`:274`);
  - NFR-22 for every page PBI (`:216`).
- **The PBI file:** `docs/backlog/pbi/PBI-010-derived-status.md`. Allowed areas are `exporters/**`,
  `tests/test_*.py`, `site/**`, `tests/page.test.mjs` and `projects/**` (`:7`). Its criteria are AC-78
  (`:40`) and the close-out (`:41`). It has `requires_spec` and `requires_external_review` (`:11-12`).
- **Live code at `560e296`:**
  - `exporters/derive.py`, `exporters/export_sessions.py`, `exporters/export_board.py`,
    `exporters/refresh.py`, `exporters/board_config.py`;
  - `site/index.html`, `tests/page.test.mjs`;
  - `local/records.py`, `local/collector.py`, `local/tabs.py`.
- **Format precedent:** `pbi-025-local-tabs.md` (revision 4) and `pbi-020-timeline.md` (revision 2).

**Four rules govern the design.**

1. **Prove, don't infer.** A state is published only when a signal the exporter can read supports it.
   Where no signal exists (a merge, conditions applied, a commit), §2.3 says so, and the page says so
   too.
2. **One derivation.** The evidence-to-state mapping lives in `exporters/derive.py`. It is called from
   `derive.project_doc`, which the session exporter and the collector both already call
   (`exporters/export_sessions.py:287-289`; `local/collector.py:440`). The local app therefore gets
   it with no `local/**` edit.
3. **No new store document and no new writer.** The derived state rides on `projects/<projectId>`,
   whose single writer is `export_sessions.py` (`CLAUDE.md:40`). `projectTabs` and its two-writer
   split are untouched (§4).
4. **A difference is information, not a defect.** A difference is shown as a comparison with its
   direction and its evidence, in neutral tones. Agreement is stated in real text, so neither case is
   hidden (§6). **Agreement means a run backs it:** the absence of evidence is reported as no evidence,
   never as agreement (revision 2, H-1).

---

## 2. The evidence as it actually is

### 2.1 What a run row carries

`derive.agent_row` builds one row per subagent (`exporters/derive.py:475-500`). The fields this spec
reads are all set at `:488-489`:

- `id`, `start`;
- `lane`: `cw`, `tw`, `cr`, `plan`, `ver`, `req` or `other`, from the agent type (`:23-24`, `:481-482`);
- `kind` and `verdict`, from `classify` (`:220-245`);
- `pbis`: the PBI ids in the label (`:262-268`).

For the `cr` lane, `kind_of` (`:206-217`) gives three results:

- `nogo` for NO-GO and REJECT;
- `changes` for CHANGES-REQUIRED;
- `go` for every other review token, including GO-WITH-CONDITIONS, GO-WITH-NOTES and
  APPROVE-WITH-CONDITIONS (`:28-29`).

The distinguishing token survives in `verdict`, so `kind` alone cannot tell conditions from done, but
`verdict` can.

`pbis` is **not** published on the run document: `run_doc` copies an explicit key list
(`:727-739`). So the page cannot attribute a run to a work item. The attribution must happen in
`derive`, and that is rule 2.

### 2.2 Attribution: how a run is tied to a work item

The only link from a run to a work item is its label. A task description naming `PBI-nnn`, or the
`PBI-003/004/005` shorthand, is read by `derive.pbis` (`exporters/derive.py:262-268`). `CLAUDE.md:145`
and PRD A-23 (`:833`) already record that inferred links are heuristics that need a PBI id in the task
description.

`findings_doc` sets the precedent this spec follows exactly:

- **A round** is a `cr` run with `kind` in `go`, `changes` or `nogo` and a non-empty `pbis`
  (`exporters/derive.py:687`).
- **A run naming two PBIs is credited to both** (`:689-690`). The real label "Code-review gate
  PBI-003/004/005" (platform-catalogue, 2026-09-09, NO-GO) is one round for each of the three.
- **A run naming none is dropped** (`:687`).

This spec keeps that rule, so features 3 and 4 attribute runs identically. It adds one thing: a
finished review round that names no PBI is **counted** as `unattributedRounds` rather than silently
dropped. The count is shown, so the owner sees how much review activity the derivation cannot place.
On today's linked data that is 7 of dispatch-board's 24 finished review rounds (§2.6).

**The known risk.** A label that mentions a second PBI in passing, such as "Review PBI-025 (the
PBI-019 follow-up)", credits both. That could move the second PBI's derived state. The page therefore
shows the evidence behind every flagged item (§6.2): its latest review run's label and verdict. A
mis-credit is visible rather than silent (row Q-8).

### 2.3 What the runs cannot show

Each point was checked against the code rather than assumed.

- **A merge.** `add_record` records Agent launches, TaskStops, Skill calls, inline results and task
  notifications (`exporters/derive.py:448-472`). It never records a `Bash` or `PowerShell` command's
  text. A `gh pr merge` in a transcript is therefore not in any row. Merges done outside Claude
  (the owner in the browser) are in no transcript at all. **"Merged" is unprovable from runs.**
- **Conditions applied.** After GO-WITH-CONDITIONS, the builder that applies the conditions is a `cw`
  run whose verdict is DONE. Nothing in its row says the conditions were met; only a later review round
  could. **"Conditions applied" is unprovable** unless a later round says GO.
- **A commit.** No row carries a commit hash. **Unprovable.**
- **"Not started".** The absence of a run naming a PBI does not prove nothing was done. The work may
  have run in a session not linked to the project (§2.5), or under a label without a PBI id.
  **`todo` is unprovable.** It is published as "no run names it", never as a positive finding. On the
  page, a hand-kept `todo` with no evidence is the **no evidence** outcome, never agreement (§6.1).

### 2.4 Why pull requests are not used as merge evidence

The git tab's `pulls` (`CLAUDE.md:42`) carries `state: MERGED` and a head `branch`. In the refresher's
export on 2026-09-13, all 20 dispatch-board PRs are `MERGED`. Every PBI PR uses `pbi/PBI-0nn-<slug>`
(#2 to #23), and the chores use `chore/…`. For this repository the join is accurate in practice. It is
still **not a reliable basis for a derived state**:

1. `pulls` holds only the **20 most recently updated** PRs (`CLAUDE.md:42`). PR #1 (PBI-017), #3
   (PBI-022) and #4 (PBI-018) have already dropped out, so older work items would lose their merge
   evidence as the list moves.
2. The branch name is a build-session habit, not an enforced rule.
3. **platform-catalogue has no remote**, so it has no `pulls` at all (`CLAUDE.md:162`).
4. `pulls` is left out whenever `gh` fails (`CLAUDE.md:69`). It is **never collected locally**
   (PBI-025 §4.5), so a state that depended on it would differ between the board and the local app.
   That breaks rule 2.
5. `pulls` lives on the git tab, owned by `export_board.py`. Joining it with runs, owned by
   `export_sessions.py`, would make one exporter read the other's source (§4.1).

A merge-corroboration tag is recorded as a possible follow-up (row Q-4). It is not in this PBI.

### 2.5 Linked sessions only — and what that hides today

FR-113 derives "from … runs in that project's linked sessions" (`docs/prd/dispatch-board.md:478`).
PBI ids are per-project (platform-catalogue also has a PBI-004, PBI-005, PBI-006, PBI-010 and PBI-011),
so an unlinked session's runs cannot be placed in a project at all.

**The real data makes this the most important limit of the design.**

- **At `560e296` and at revision 1 (2026-09-13),** `board.config.json` linked one session to
  dispatch-board, `9562c312`, whose last activity was 2026-09-11 17:45.
- Every run naming PBI-004, PBI-005, PBI-006, PBI-008, PBI-011, PBI-019, PBI-025 or PBI-026 is in
  session `7e0c4f3c`, which was then linked to **no** project (its session document had
  `project: null`). The round-1 reviewer confirmed this, and found PBI-007 and PBI-014 there too.
- With that config, the derivation saw none of the 2026-09-12 work. Revision 1's comparison then
  reported a work item hand-kept `todo` and named by no linked run as **agreeing**. That was the
  round-1 High finding (H-1), and revision 2 removes it (§6.1).
- **Linkage, 2026-09-13.** After the round-1 review, the orchestrator linked `7e0c4f3c` to
  dispatch-board in `board.config.json`, which now lists `9562c312` and `7e0c4f3c`
  (`board.config.json:33`). It is a working-tree change, not yet committed. That resolves today's
  real-data case **operationally only**.

**The 2026-09-12 staleness is exactly the case an unlinked build session hides, and linking one session
does not fix the design.** The next build session that nobody links fails the same way. So the design
does not rely on linkage:

- **No evidence is its own outcome.** A hand-kept `todo` with no evidence is shown as "No evidence",
  with its own tile and tag. It is never counted as agreement (§6.1, AC-DS24).
- **The panel says how many linked sessions the derivation read, and when they were last active.**
  The time comes from `project.last` (`exporters/derive.py:749`), in real text (§6.2).
- Keeping every build session linked stays the owner's (row Q-1).

The fixture tests (§7) prove detection works once the evidence is in a linked session. They also prove
that a work item without evidence is never reported as agreeing.

### 2.6 What the rules show on today's data

This is a throwaway check, not a test.

- **Evidence:** the refresher's `out/runs/*.json`. `out/` is local, not committed, and is rewritten on
  every refresh, so **each row carries its own measurement time**.
- **Comparison:** each project's `buildState` as committed at `560e296`, using §3's rules and §6.1's
  comparison.

| Project, sessions read | Measured | Named by a run | Agree | Runs ahead | Hand-kept ahead | No evidence | Unattributed rounds |
|---|---|---|---|---|---|---|---|
| dispatch-board, linked (`9562c312`) | 2026-09-13, revision 1; the round-1 reviewer re-measured it the same day and matched exactly | 10 | 4 (003, 013, 018, 021) | 3 (001, 002, 024) | 3 (017, 022, 023) | not re-measured | 7 |
| dispatch-board, with `7e0c4f3c` also linked | 2026-09-13, revision 1, when `7e0c4f3c` held 51 runs | 18 | 4 | **11** (001, 002, 004, 005, 006, 008, 011, 019, 024, 025, 026) | 3 | not re-measured | 7 |
| the same | 2026-09-13, round-1 review, when `7e0c4f3c` held 73 runs | **20** | 4 | **13** (the 11, plus the in-flight PBI-007 and PBI-014) | 3 | not re-measured | not restated |
| platform-catalogue, linked (`7f71729a`) | 2026-09-13, revision 1; **corrected in revision 2** | 12 | 2 (009, 010) | 1 (011) | 9 (000, 001, 002, 008 `conditions`; 003, 004, 005, 006, 007 `partial`) | 1 (012) | 1 |

**Correction (revision 2, H-1).** Revision 1 counted platform-catalogue's PBI-012 as named and agreeing.
No label in `7f71729a` names 012, and it is hand-kept `todo` at `560e296`. Under revision 2's §6.1 it is
**no evidence**. Revision 1 also had no-evidence items on dispatch-board that it counted nowhere; those
counts were not re-measured for revision 2.

**These figures will keep moving.** `7e0c4f3c` was linked to dispatch-board on 2026-09-13 and is still
the active build session. Every refresh re-reads it, so every figure above is a snapshot, not a
baseline.

What the table establishes:

- **At revision 1's measurement, every "runs ahead" item on dispatch-board was genuinely stale at
  `560e296`.** The git tab lists a `MERGED` PR for each of the 11: #10, #12, #13, #14, #15, #16, #18,
  #19, #20, #21, #23. The round-1 reviewer confirmed each one against `git log` and the exported `pulls`.
  **That held only at that measurement.** Derived `done` means *the latest review passed*; hand-kept
  `done` means *merged and closed out* (M-1). So "runs ahead" also collects **work in flight and reviews
  awaiting merge**. By the review's re-measurement it already held PBI-007 (`partial`, no round) and
  PBI-014 (NO-GO, then GO-WITH-CONDITIONS, still in review). The page says so wherever the group is
  shown (§6.2, §6.4).
- **Two causes make up "hand-kept ahead".** On dispatch-board all 3 are GO-WITH-CONDITIONS. On
  platform-catalogue **4 of 9** are; the other five are `partial`. For a GO-WITH-CONDITIONS item, the
  final round said GO-WITH-CONDITIONS, the build applied the conditions and merged under the owner's
  authorisation (`CLAUDE.md:153-156`), and no later round said GO. §2.3 says the runs cannot show that.
  Direction grouping is what stops these burying the staleness signal. In derived mode these items stay
  `conditions` for good (§5.3, §6.3; row Q-3, **OWNER**, blocking before the switch flips).

---

## 3. The derivation

### 3.1 The evidence set

For one project, the evidence is the agent rows of its **linked, exported** sessions: the same
`linked` list `project_doc` already computes (`exporters/derive.py:745`), taken from
`results[sid]['rows']`. This is the same row population `findings_doc` reads
(`exporters/export_sessions.py:299`), apart from `runs.manual` rows, which name no PBI
(`exporters/derive.py:721`).

- **Order.** Rows are ordered by `(start or '', id)`. The id tie-break is required: the exporter builds
  `results` in glob order and the collector in its own order, and both must derive the same "latest".
- **Evidence runs.** A row is evidence for `PBI-nnn` when its `lane` is `cw`, `tw` or `cr` and `nnn`
  is in its `pbis`.
- **Not evidence.**
  - `plan` (spec and plan gates): an approved spec is not built work.
  - `ver`: its outcome word is not a review verdict (`:174-186`).
  - `req`, `orch` and `other`: this covers the "Draft/Revise PBI-0nn spec" runs, which are `other`.
- **A round** is an evidence run with `lane == 'cr'` and `kind` in `go`, `changes` or `nogo`. That is
  `findings_doc`'s predicate (`:687`). A running, killed or stopped review is evidence of activity but
  is not a round.

### 3.2 State to evidence

These are FR-113's four states, applied in order. The first match wins.

| State | Evidence required | Can the runs prove it? |
|---|---|---|
| `done` | The **latest round** has `kind == 'go'` and a `verdict` that is not a conditions token: GO, GO-WITH-NOTES, APPROVE, APPROVED or APPROVE-WITH-NOTES | **Proves "the latest code review passed"**, which is AC-78's wording. It does **not** prove the change merged (§2.3). The page labels the derived column "From runs", never "Merged". It shows derived `done` as **"Review passed"**, never the hand-kept "Built and reviewed" (`site/index.html:289`), because hand-kept `done` means merged and closed out (revision 2, M-1) |
| `conditions` | The latest round's `verdict` is GO-WITH-CONDITIONS or APPROVE-WITH-CONDITIONS | Proves the latest review **set** conditions. It cannot prove they are still open, because "applied" is unprovable (§2.3) |
| `partial` | Either the latest round is `changes` or `nogo`, or there is at least one evidence run and no round at all (a build of any kind, or an unfinished review) | Proves work was started and has not passed review |
| `todo` | **Never published.** A PBI with no evidence run has no entry | **Unprovable** (§2.3). Absence is shown as "No run names it" |

**What does not change a state.**

- **Build runs after the latest round.** A GO followed by a `cw` "apply conditions" run stays `done`.
  A NO-GO followed by a fix run stays `partial` until a new round.
- **A running or killed review after a finished round.** Only finished rounds decide.

`STATES` (`exporters/derive.py:755`) stays the vocabulary. `derive` adds one constant,
`CONDITIONS_TOKENS = ('GO-WITH-CONDITIONS', 'APPROVE-WITH-CONDITIONS')`.

### 3.3 The published shape

A new pure function, `derive.work_items(rows)`, returns
`{'items': {PBI id: item}, 'unattributedRounds': int}`. Its output is lists, dicts, strings, ints and
null only, so it round-trips through JSON unchanged, as `records.to_row` requires
(`local/records.py:229-237`).

| Field | Type | Meaning |
|---|---|---|
| `state` | `done` \| `conditions` \| `partial` | §3.2 |
| `rounds` | int | Finished review rounds naming the PBI. It equals `findings_doc`'s `rounds` for the same rows (AC-DS4) |
| `verdict` | string \| null | The latest round's `verdict` token; null with no round |
| `latestRound` | string \| null | That round's run id, so the page can show its label (`runs/<id>` is published) |
| `builds` | int | `cw`/`tw` evidence runs of any kind |
| `runs` | [string] | Every evidence run id, in §3.1 order |

`unattributedRounds` counts rounds with an empty `pbis`.

`derive.project_doc` (`exporters/derive.py:742-750`) gains three keys, written on **every** project
document, so their presence means "derived by this version":

- `workItems`: `work_items(linked rows)['items']`, `{}` when nothing names a PBI;
- `unattributedRounds`: an int, 0 when none;
- `workItemStatus`: `p.get('workItemStatus') or 'shadow'` (§5). The `.get` keeps hand-built project
  dicts in existing tests valid (`tests/test_derive.py:192`; `local/tests/test_tabs.py:67`).

Its signature does not change.

### 3.4 Worked example: the 2026-09-12 scenario

These are the real verdict sequences from session `7e0c4f3c`, taken as if it were linked to
dispatch-board. The `plan` and `other` runs are dropped per §3.1.

| PBI | Evidence in order | Derived |
|---|---|---|
| PBI-005 | cw DONE · cr NO-GO · cw DONE-WITH-CONDITIONS · cr GO | `done`, rounds 2, verdict GO |
| PBI-006 | cw DONE · cr GO-WITH-CONDITIONS · cw DONE · cr GO | `done`, rounds 2 |
| PBI-011 | cw DONE-WITH-CONDITIONS · cr NO-GO · cw DONE · cr GO | `done`, rounds 2 |
| PBI-025 | cw DONE · cr GO-WITH-CONDITIONS · cw DONE · cr GO | `done`, rounds 2 |
| PBI-026 | cw DONE · cr GO | `done`, rounds 1 |

At `560e296` none of the five is in `buildState`, so each is hand-kept `todo`, and `done` outranks
`todo`. All five fall in "Runs are ahead of the hand-kept state" (§6.1). §7 turns this table into the
fixture for AC-DS5.

---

## 4. How derived state reaches the page: ownership, store, cache and the local app

### 4.1 On the project document, not the backlog tab

The parent spec asks how derived state reaches the Backlog "given that `refresh.py` runs
`export_board.py` before `export_sessions.py`" (`docs/backlog/specs/dispatch-board.md:250`;
`exporters/refresh.py:43`).

**The answer: it does not go through `export_board.py`.**

- `export_sessions.py` writes it onto `projects/<projectId>` in the same tick. `refresh.py` runs every
  exporter (`:95-101`) before it plans (`:228`), so both documents come from one plan.
- The page already subscribes to `projects` and `projectTabs` (`site/index.html:1300-1307`). It joins
  `projectTabs/<pid>.backlog` (hand-kept) with `projects/<pid>` (derived) by PBI id.
- Exporter order does not matter.

**Alternatives considered and rejected.**

| Alternative | Why not |
|---|---|
| `export_board.py` reads `out/runs/*.json` and adds derived state to `backlog` | With today's order it reads the **previous** tick's runs. The collector builds `backlog` through `local/tabs.py`, which is blocked, so the local app would lack the field. PBI-025's AC-TB1 equivalence (`local/tests/test_tabs_equivalence.py`) would then fail in a blocked suite. `run_doc` does not publish `pbis` anyway (§2.1) |
| Swap `EXPORTERS` so sessions run first | `export_board.py` run alone, as its tests do, would read stale runs. It changes `CLAUDE.md:65` and `refresh.py:7` for no gain |
| A new `projectTabs/<pid>.<suffix>` written by `export_sessions.py` | The local tab id form is built from `records.TAB_NAMES` (`local/records.py:91`, `:103`), so a new suffix fails `store_path`. `test_every_store_path_equals_the_path_it_was_written_to` (`local/tests/test_conformance.py:403-406`) drives the real exporters and would go red, in a blocked suite. It would need a prerequisite local PBI, as PBI-011 needed PBI-026, plus changes to `refresh.py`'s `TABS` (`:47`) and both writers' ownership sets |
| Add it to `projectTabs/<pid>.findings` | That document is deleted when a project has no finished round (`exporters/export_sessions.py:300-309`), so derived `partial` would vanish with it. It would also make "findings" mean two things |

**The one join on the page, and why it is not a second derivation.** The page compares two exported
values per PBI using a four-step rank (§6.1). Doing that in an exporter would force one exporter to read
the other's source, which is exactly what the table above rejects. The page is the same code under both
data adapters, so the board and the local app still cannot diverge, which is the purpose of the parent's
rule (`docs/backlog/specs/dispatch-board.md:87`). Every evidence judgement (attribution, rounds,
latest, state) stays in `derive` (row Q-5).

### 4.2 Single writer, and the two-writer rule

| Store path | Writer before | Writer after | Change |
|---|---|---|---|
| `projects/<projectId>` | `export_sessions.py` (`CLAUDE.md:40`), via `derive.project_doc` | Unchanged; the collector writes the same record via the same function (`local/collector.py:440`) | Three added keys (§3.3) |
| `projectTabs/<projectId>.{spec,assumptions,decisions,backlog,git}` | `export_board.py` (`exporters/export_board.py:40`) | Unchanged | **None.** `export_board.py` is not edited |
| `projectTabs/<projectId>.findings` | `export_sessions.py` (`exporters/export_sessions.py:290-309`) | Unchanged | None |

- **No "tabs I own" set is computed, changed or added** anywhere: not `export_board.TABS`, not
  `refresh.TABS` (`exporters/refresh.py:47`), not `local/tabs.OWNED` (`local/tabs.py:32`), and
  `records.TAB_NAMES` is never read.
- **`export_board.py` does not write `projects/`**, and `export_sessions.py` does not write the five
  board tabs. AC-DS12 checks both.

### 4.3 `refresh.py`: `TABS`, `MANAGED` and the mass-delete guard

- **`MANAGED`** already includes `projects` (`exporters/refresh.py:44`), so a changed project document
  is pushed as a `set`.
- **Status documents.** `projects/<pid>` is in each project's "mine" set (`:167-172`), so a derived-state
  change moves that project's `updatedAt`. That is the desired behaviour.
- **The mass-delete guard.** Its `projects/*` clause (`:143-145`) and emptied-tabs clause (`:146-152`)
  are untouched: no document is added to or removed from any managed collection.
- **`refresh.py` is not edited.** `tests/test_refresh.py` stays green unchanged.

**Operational note.** The first refresh after merge rewrites both `projects/*` documents once.

### 4.4 The cache: no `PARSER_VERSION` bump

- **What the cache holds.** `export_sessions.py` caches each session's parse, including its agent
  `rows` (`:249-253`, written at `:271`). It reuses a parse only when the signature matches, and the
  signature leads with `PARSER_VERSION` (`:60`, `:179`, `:245`). It is 6 at `560e296`, but it will have
  moved before this PBI builds: PBI-014 bumps it from 6 to 7, and PBI-009's spec also requires a bump
  (`docs/backlog/specs/pbi-009-waiting-on-you.md:795`). **This spec pins no literal value.** It requires
  `PARSER_VERSION` to be **unchanged from the build base** (revision 2, M-2).
- **What `work_items` reads.** Only `id`, `start`, `lane`, `kind`, `verdict` and `pbis`. Every one is set
  by `agent_row` today (`exporters/derive.py:488-489`), so every row cached under the build base's
  version already has them.
- **Nothing derived is cached.** `project_doc` is recomputed from `results` on every run
  (`exporters/export_sessions.py:287-289`).
- **PBI-011's round-1 NO-GO does not apply.** It added a **new row field** (`findings`), which rows
  cached under version 5 lacked (`tests/test_export_sessions.py:1024-1034`). This PBI adds none.
- **The collector** derives its rows through the same `derive.agent_row` (`local/collector.py:379`).

**No bump is needed, on one condition, stated as AC-DS13.** This PBI changes none of `agent_row`,
`pbis`, `classify`, `verdict_of` or `kind_of`. If the build finds it must, that is a stop: it bumps
`PARSER_VERSION`, adds a cached-rerun test in the style of `:1024-1034`, and reports the collector
impact rather than editing `local/**`.

### 4.5 The local app: the record shapes already accept this

- **The shape.** The `project` shape requires `name`, `repoPath`, `branch`, `sessions`, `statusDoc`,
  `order`, `runs`, `running`, `last` and `usage`, and lists no optionals (`local/records.py:50-56`).
  "Fields a SPEC does not list are allowed, and kept, at every level" (`:21`).
- **Validation.** `workItems`, `unattributedRounds` and `workItemStatus` therefore validate, and
  round-trip through `to_row` / `from_row` when §3.3's types hold (`:229-237`).
- **No edit anywhere local.** No change is needed to `local/records*`, `local/records.shapes.json` or
  `local/schema*`, and **no follow-up PBI is needed**.

Two existing local tests exercise this with no edit:

- `test_one_pass_equals_the_exporter` (`local/tests/test_collector_equivalence.py:84-91`) compares the
  collector's project records with the exporter's. Both come from `derive.project_doc`.
- `test_every_document_validates_against_its_kind` and `test_every_document_round_trips_through_its_row`
  (`local/tests/test_conformance.py:397-411`) drive the real exporters.

**If either fails, that is a stop and an owner question, never a licence to edit `local/**`** (row
Q-13).

---

## 5. The shadow period's switch (A-48)

### 5.1 Where it lives

The switch is a per-project key in `board.config.json`, read by `exporters/board_config.py`:

```json
"projects": [ { "id": "dispatch-board", "…": "…", "workItemStatus": "shadow" } ]
```

**Why the config and not `projects/<projectId>.json`.**

1. **The hand-kept file is what retirement retires**, and the build session edits it routinely
   (`CLAUDE.md:123-125`). The owner's retirement switch should not live in the file an agent edits by
   hand on every close-out.
2. **Per-project settings already live in `projects[]`** (`CLAUDE.md:114-119`). `board_config.projects()`
   is the one reader every exporter and the collector share (`exporters/board_config.py:103-133`;
   `local/collector.py:440` receives its output).
3. **The switch reaches the page on the same document as the derived state**
   (`project_doc` → `workItemStatus`), so the mode and the data it governs can never come from
   different exports.

**This PBI does not edit `board.config.json`**, which is outside its `allowed_areas`
(`docs/backlog/pbi/PBI-010-derived-status.md:7`). The default, `shadow`, applies with no config change. So:

- **the shadow period starts** at the first refresh after this PBI merges;
- **it ends for a project** when the owner writes `"workItemStatus": "derived"` into that project's
  entry.

### 5.2 Values, and what each does

| Value | Set by | Backlog tab | Overview | `projects/<id>.json` |
|---|---|---|---|---|
| absent, or `"shadow"` | the default | Hand-kept state as today, **plus** the derived state beside it, the three-way comparison and the "where they differ" panel (§6.2) | Cells, tiles and "Needs attention" keep the **hand-kept** state; one added item counts "runs ahead" (§6.4) | Read as today; `review`, `open` and `commit` override |
| `"derived"` | **the owner only** | **Derived** state drives the tiles, the state column, the dependency graph's tones and the badge. No hand-kept state column and no comparison. A line of real text says the hand-kept state is retired for this project | Cells, tiles and "Needs attention" use the derived state; a PBI named by no run counts as Not started | **Still read, never deleted** (C-20). `review`, `open` and `commit` still override (FR-176). Only its `state` stops being shown |

- **Reversible.** Removing the key or setting `"shadow"` restores the shadow view on the next refresh.
- **The data file is never written or deleted by this PBI**, nor by the switch.
- **No third value** (for example one that hides derived state without retiring anything) is added
  (row Q-7).

### 5.3 Who flips it

Retiring the hand-kept state is the owner's decision (S-39, `docs/prd/dispatch-board.md:158`; parent
row 15, `docs/backlog/specs/dispatch-board.md:299`).

- **The mechanism has no agent path.** No exporter, test or page writes `workItemStatus`; the page
  never writes anything (`CLAUDE.md:14`).
- **This PBI's diff leaves `board.config.json` and `projects/*.json` untouched** (AC-DS11).
- **The rule should be documented.** "Only the owner sets `workItemStatus`" belongs in `CLAUDE.md`
  beside the C-16 rule. `CLAUDE.md` is not in this PBI's areas, so that is row Q-2 (**OWNER**).

A flip to `derived` is only sensible once the shadow panel's "runs ahead", "not named by any run" and
"no evidence" groups are understood. The page shows the counts that decision needs; it does not make the
decision.

**What a flip does to GO-WITH-CONDITIONS items (revision 2, M-3).** A work item closed on
GO-WITH-CONDITIONS, with no later review round, stays derived `conditions` **for good**. §2.3 explains
why: "conditions applied" is unprovable from runs.

- **Which items.** At `560e296`, measured 2026-09-13 on the linked sessions: dispatch-board PBI-017,
  PBI-022 and PBI-023, and platform-catalogue PBI-000, PBI-001, PBI-002 and PBI-008.
- **What derived mode would show.** Each of those items would read "Conditions open".
- **Needs attention.** Each would also add a "<id> review conditions" item to the Overview's "Needs
  attention" (`site/index.html:524`). The seven items would be permanent: a later review round saying GO
  is the only thing that removes one.

**Row Q-3 is therefore blocking before the switch is flipped to `derived` for any project.** It does
not block the build.

### 5.4 Validation

`board_config.projects()` raises `ValueError`, naming the project and `workItemStatus`, for any
present value other than the strings `"shadow"` and `"derived"`. That includes `null`, `true`, `""`,
`"Derived"` and `["shadow"]`.

- **Both exporters already turn that into exit 2 with nothing exported**
  (`exporters/export_board.py:233-259`; `exporters/export_sessions.py:201-205`), per G-1's "config typos
  fail loudly" (`docs/backlog/specs/dispatch-board.md:34`).
- **The legacy config shape** (`build.*`) gets the default through the same loop
  (`exporters/board_config.py:112-132`).

---

## 6. The page

### 6.1 The comparison

For each PBI in the spec's list (`docs.backlog.pbis`), the inputs are:

- `hk`: the hand-kept `state`, where an unlisted PBI is `todo` (`exporters/derive.py:912`);
- `item`: `project.workItems[id]`, possibly undefined.

With `rank = { todo: 0, partial: 1, conditions: 2, done: 3 }`, read through `own()`
(`site/index.html:293`):

| Outcome | Condition | Flagged? | `data-shadow` |
|---|---|---|---|
| **Agrees** | `item` present and `item.state === hk`. **A run must back it** | No | `agrees` |
| **No evidence** | `item` absent and `hk === 'todo'`. No run names it, and the hand-kept state is Not started | No, and **never counted as agreement** | `no-evidence` |
| **Runs ahead** | `item` present, both ranks known, `rank[item.state] > rank[hk]` | **Yes** | `runs-ahead` |
| **Hand-kept ahead** | `item` present, both ranks known, `rank[item.state] < rank[hk]` | **Yes** | `handkept-ahead` |
| **Not named by any run** | `item` absent and `hk !== 'todo'` | **Yes** (FR-175: the runs give no state, while the hand-kept state claims progress, so the two differ) | `unnamed` |
| **Cannot compare** | `hk` or `item.state` not a key of `rank` (for example `"constructor"`) | No; counted separately; nothing logged | `unknown` |

**Evaluation order (revision 3, N-3).** The six outcomes are checked in this order; the first match
wins:

1. **Cannot compare** — `hk` is not a key of `rank`, or `item` is present and `item.state` is not a key
   of `rank`. Checked first, so an unrecognised state (hand-kept or derived) never falls through and
   reads as Agrees, No evidence or Not named. This is what stops two equal unrecognised states (for
   example `hk` and `item.state` both `"constructor"`) from satisfying "Agrees", and stops an
   unrecognised `hk` with no `item` from satisfying "Not named by any run".
2. **No evidence** — `item` absent and `hk === 'todo'`.
3. **Not named by any run** — `item` absent and `hk !== 'todo'` (by this point `hk` is a known rank key).
4. **Agrees** — `item` present and `item.state === hk`.
5. **Runs ahead** — `item` present, `rank[item.state] > rank[hk]`.
6. **Hand-kept ahead** — `item` present, `rank[item.state] < rank[hk]`.

The flagged set is the union of the three flagged outcomes. That is "every work item where the two
differ" (FR-175, `docs/prd/dispatch-board.md:479`).

**Why "no evidence" is neither agreement nor a difference (revision 2, H-1).** Revision 1 called a
hand-kept `todo` with no derived item "Agrees". That made a stale "Not started" for work done in an
unlinked session, which is exactly the 2026-09-12 failure, read as agreement. A staleness detector that
reports agreement exactly when it has no data defeats itself.

- **Not flagged.** Absence of a run is not a finding (§2.3). Most not-started work genuinely has no runs.
- **Never agreement.** It has its own tag, its own tile and its own list. It is excluded from the
  "Agree" count and from the all-agree sentence (§6.2).
- **The reader can judge how old the evidence is.** The panel states when the linked sessions were last
  active.

### 6.2 Backlog tab, shadow mode

**Rendering rule.** This applies when `project.workItems` is an object and `workItemStatus` is not
`derived`. The lookup uses `projects.find(p => p.id === proj().id)`, which is the whole project,
**not narrowed by the session filter** (§6.8).

The panel is drawn in this order, inside the existing `renderBacklog` (`site/index.html:792-843`):

1. **The existing header, source, carried marker and four state tiles.** These keep counting hand-kept
   state (`:828-834`).
2. **A "Shadow period" panel**, a `.panel` with the `.tile` language (NFR-13):
   - **A sentence of real text, pinned by AC-DS6 and AC-DS24:** "Shadow period: each work item's state
     is derived from the code-writer, test-writer and code-reviewer runs in this project's N linked
     session(s) whose task names it, and shown beside the hand-kept state. Those sessions were last
     active <time>. A difference is shown for you to look at before deciding whether to retire the
     hand-kept state; it is not an error in either. Review passed means the latest code review passed,
     not that the change merged. Work done in sessions not linked to this project is not seen, so a
     work item no run names is shown as no evidence, never as agreement."
   - **The time.** `<time>` is `when(project.last)` (`site/index.html:273`; `project.last` is set at
     `exporters/derive.py:749`), escaped. When `when()` returns `''` (`last` is null or not a readable
     time), the second sentence reads "Those sessions have no recorded activity." instead. It uses
     `when()`, not `ago()` (`:274-279`), because `ago()` reads `Date.now()`, and the two-adapter
     deep-equal (§6.8) must not depend on how much time passes between rendering its two sides.
   - **Six tiles:**
     - "Agree", with the sub-line "backed by a run";
     - "Runs ahead of the hand-kept state";
     - "Hand-kept state ahead of the runs";
     - "Not named by any run";
     - "No evidence", with the sub-line "no run names it; hand-kept Not started";
     - "Review rounds naming no work item" (`unattributedRounds`).

     A seventh, "Cannot compare", appears only when its count is above zero.
   - **Tile tones:** `var(--ink)` for runs ahead, `var(--ink-2)` for hand-kept ahead, and `var(--ink-3)`
     or `var(--rule-2)` for the rest, no evidence included.
3. **"Where hand-kept and derived state differ"**, three groups, each drawn only when non-empty. Every
   flagged item appears in exactly one group:
   - **"Runs are ahead of the hand-kept state: out-of-date entries, work in flight, or reviews awaiting
     merge".** Under the heading, one fixed line: "Review passed means the latest code review passed. It
     is not proof of merge, so this group can include work still being built or a passed review whose
     pull request has not merged, as well as a hand-kept entry that is out of date." Each row reads
     "PBI-nnn · <title> — hand-kept: <label>; from runs: <label>", then the evidence line: "latest
     review: <run label> · <verdict> · <time>". The run is looked up by `latestRound` in `allRuns`. When
     the id is not found, it reads "latest review: round N, <verdict>". With no round, it reads "N build
     run(s), no finished review".
   - **The hand-kept state is ahead of the runs.** The same rows, under one fixed line: "Runs show
     review verdicts only. They cannot show that conditions were applied, that a pull request was
     merged, or work done in a session not linked to this project."
   - **Not named by any run.** Id, title and hand-kept label, under: "No code-writer, test-writer or
     code-reviewer run in the linked sessions names these work items."
   - **"No evidence either way".** Not a difference, so it is drawn **after** the difference groups and
     outside them, only when non-empty. It lists id and title under the line: "No code-writer,
     test-writer or code-reviewer run in the linked sessions names these work items, and the hand-kept
     state says Not started. There is nothing to compare, so they are not counted as agreeing."
   - **When no item is flagged**, the panel shows real text instead, pinned by AC-DS6. **It counts only
     run-backed agreement** (A = the `agrees` count, E = the `no-evidence` count):
     - A > 0: "Hand-kept and derived state agree for all A work items that a run names." When E > 0,
       followed by: "E work item(s) named by no run and hand-kept Not started have no evidence and are
       not counted as agreeing."
     - A = 0: "No run in the linked sessions names any of these N work items, so there is nothing to
       compare. None is counted as agreeing."
   - **Run-named ids missing from the PBI list** (for example a run naming platform-catalogue's
     `PBI-013`, one past that project's actual list of PBI-000 to PBI-012
     (`out/projectTabs/platform-catalogue.backlog.json`), revision 3, N-1) are listed after the groups
     as plain text: "Named by runs but not in the PBI list: …". They are never added to the table or any
     count.
4. **The dependency graph**, unchanged, drawn from hand-kept state.
5. **The work-items table.** Its single "State" column (`:838-839`) becomes three columns:
   - "Hand-kept" (the existing tag);
   - "From runs": a `.tag <state>` with the text from a new
     `derivedLabel = { done: 'Review passed', conditions: 'Conditions open', partial: 'Partly built' }`,
     read through `own()`, or "No run names it" in `.tag.todo`. `stateLabel` (`:289`) stays the
     hand-kept vocabulary, and derived `done` never reads "Built and reviewed" (revision 2, M-1);
   - "Shadow": a tag reading Agrees, Runs ahead, Hand-kept ahead, Not named by any run, No evidence or
     Cannot compare, on a `<tr data-shadow="…">`.

**What makes a difference unmistakable and not alarming.** NFR-10 reserves `--human` for things awaiting
a human and uses `--nogo` and `--changes` for review states (`docs/prd/dispatch-board.md:549`), so a
difference uses **none of `--human`, `--nogo` or `--changes`**, and never `.callout.warn` or the warning
icon.

- Two new tag classes join the existing tag rules (`site/index.html:112-115`):
  - `.tag.agrees`, `.tag.no-evidence` and `.tag.unknown`: `--t: var(--ink-3)`;
  - `.tag.differs`: `--t: var(--ink)`, used for all three flagged outcomes, which the tag text tells
    apart.
- The emphasis comes from the words, the grouping and the counts, not from an alarm colour. A
  default `.callout`, which is `--human` (`:154`), is not used.

### 6.3 Backlog tab, derived mode

**Rendering rule:** `workItemStatus === 'derived'` and `workItems` is an object. The page computes
`effective(pbi) = item ? item.state : 'todo'` and uses it everywhere the tab used `x.state`:

- the four tiles. The `done` tile reads "Review passed", not "Built and reviewed" (`:830`). The `todo`
  tile reads "No run names it", not "Not started", because derived state never proves `todo` (§2.3);
- the dependency graph's top bars and dashed `partial` border (`:818-825`), with `derivedLabel` in
  each node's title;
- the table's single "State" column, with `derivedLabel` text, where a PBI no run names reads "No run
  names it".

Changes from shadow mode:

- **No shadow panel, no "Hand-kept" or "Shadow" column**, and no `data-shadow` attribute.
- **One line of real text below the source line:** "The hand-kept state is retired for this project
  (the owner set `workItemStatus` to derived). State comes from runs in this project's N linked
  session(s), last active <time>. Review passed means the latest code review passed; it is not proof
  the change merged. Review, open items and commit still come from projects/<id>.json where recorded."
  `<time>` and its no-activity fallback are as in §6.2.
- **The "Review rounds naming no work item" tile stays.**
- **GO-WITH-CONDITIONS items stay "Conditions open" for good (revision 2, M-3; §5.3).** An item closed
  on GO-WITH-CONDITIONS with no later round counts in the "Conditions open" tile and shows that state
  indefinitely. At `560e296` that is dispatch-board PBI-017, PBI-022 and PBI-023, and platform-catalogue
  PBI-000, PBI-001, PBI-002 and PBI-008. This is the consequence row Q-3 must settle before any flip.

### 6.4 Overview

`renderOverview` (`site/index.html:494-549`) and the tab badge (`:394-395`) change as follows.

- **Shadow mode.**
  - The tiles, cells (`:514-516`), badge and the existing "Needs attention" items (`:524-525`) keep the
    hand-kept state, byte-identically when nothing is flagged.
  - A cell whose PBI is flagged gains `data-shadow="<outcome>"`, and its `title` gains
    "; hand-kept and derived state differ".
  - When the "runs ahead" count is above zero, one item is added to "Needs attention": "N work items:
    runs are ahead of the hand-kept state", with the message "Out-of-date entries, work in flight, or
    reviews awaiting merge: a passed review is not proof of merge." It uses tone `var(--ink-3)` and
    `data-go="backlog"`.
  - "Hand-kept ahead", "not named" and "no evidence" add no attention item: they are expected limits
    of the evidence (§2.3), not action.
- **Derived mode.** `effective()` replaces `x.state` in the tiles, cells, badge and the
  conditions/partial attention items. An attention item's message is the hand-kept `open` when
  non-empty, else the derived review summary (§6.5).
  - **The GO-WITH-CONDITIONS consequence (M-3).** Every item that stays derived `conditions` (§5.3,
    §6.3) adds a permanent "<id> review conditions" item through the existing rule
    (`site/index.html:524`). That is seven items across the two projects at `560e296`. This PBI does not
    suppress them: hiding a real review state would break rule 1, and Q-3 decides the remedy before any
    flip.

### 6.5 FR-176 overrides

For both modes, per PBI:

- **Review column.** The hand-kept `review` when it is a non-empty string other than `—`, which is
  `build_state`'s default for an absent key (`exporters/derive.py:845`). Otherwise the derived summary:
  "Round N: <verdict>" when `rounds > 0`, "N build run(s), no review yet" when `builds > 0`, else `—`.
  An explicit hand-kept `"—"` cannot be told from an absent one and shows the derived summary
  (row Q-10).
- **Still open.** The hand-kept `open` only. This PBI derives no "open" value; the Findings ledger
  already shows open findings.
- **Commit.** The hand-kept `commit` only. It is unprovable from runs (§2.3).

### 6.6 When derived state is absent

A project document **without** a `workItems` object comes from a store not yet re-exported, or from an
older local database. For it, the Backlog and Overview render **exactly as before this PBI**, in either
mode: no shadow panel, no extra columns, no `data-shadow`, and no retirement line. AC-DS18 pins this on
a fixture copied from the existing backlog tests.

### 6.7 Escaping, `md()` and design rules

- **`esc()` for store text.** Every store-derived string goes through `esc()` (`site/index.html:270`;
  NFR-14). That covers run labels, verdicts, PBI ids, hand-kept `review` and `open`, and the
  "not in the PBI list" ids.
- **`md()` only for repo text.** `md()` (`:272`) stays for PBI titles only, which is repo text as today
  (`:839`). It is **not** widened, and never applied to a run label or verdict.
- **Colours** only through existing tokens (NFR-9). There is no motion.
- **Status tiles** use `tile()` (NFR-13).

### 6.8 Both adapters and the session filter

- **Both adapters.** `projects` arrives through both adapters' `collection('projects', 'order', …)`
  (`site/index.html:1300-1305`, `:1257-1260`), so the shadow view reads nothing adapter-specific.
- **The session filter.** Derived state is project-wide, like the Backlog tab itself. The session
  filter narrows `runs` (`:1168`) but not `projects`, and evidence labels are looked up in `allRuns`.
  Selecting one session changes nothing on the Backlog tab (AC-DS20).
- **The ten-panel equivalence check** (`tests/page.test.mjs:1461-1473`) stays meaningful. The compared
  board must show every shadow outcome on both sides (§7.4, AC-DS21).

---

## 7. Test plan

All three suites are stdlib-only or node built-ins (`CLAUDE.md:106-110`). Tests come first (D-9).

Two constraints on where fixtures can live:

- **Only named test files are allowed.** The PBI's areas grant `tests/test_*.py` and
  `tests/page.test.mjs`, not `tests/**` (`docs/backlog/pbi/PBI-010-derived-status.md:7`). So the 2026-09-12 fixture
  is written inline in each test file that needs it: a Python constant in `tests/test_derive.py`,
  reused by import from `tests/test_export_sessions.py`, and a JS constant in `tests/page.test.mjs`.
  It is never a shared file under `tests/fixtures/`.
- **No existing test case is changed.** Cases are only added. The project-document tests already
  compare chosen keys, so adding keys breaks none of them:
  - `tests/test_derive.py:200-201`;
  - `tests/test_export_sessions.py:917`;
  - `tests/test_export_board.py:906`.
- **The one allowed fixture edit (revision 3, N-2).** §7.4's Equivalence case adds PBI-005 to the shared
  `EQ_PROJECT_TABS`, and renames `PROJECTS` to `EQ_PROJECTS` where it feeds `EQ_RECORDS` and `overStore`.
  Both are fixture edits, not test-case edits: `EQ_PROJECT_TABS` is used only at `:1418` (on `main`), and
  the existing `seen` checks it feeds only test that something is present, so the added item breaks
  none of them. This is the one fixture edit this spec allows; every other addition in §7.1–§7.4 is a
  new case, not an edit to an existing one, and "no existing test case is changed" stays true.

**The shared fixture, `STALE_2026_09_12`.** Rows for one linked session, labelled as the real runs were:

- **The five PBIs.** "Build PBI-005 local server", "Code-review PBI-005", "Fix PBI-005 review
  findings", "Code-review PBI-005 round 2", and so on, with §3.4's lanes, kinds and verdicts.
- **Distractor runs.** The `plan` spec-gate runs ("Spec gate review PBI-005", CHANGES-REQUIRED then
  APPROVE-WITH-NOTES) and the `other` spec-author runs ("Author PBI-025 spec").
- **One agreeing item.** PBI-003 with a cr GO.
- **One no-evidence item.** PBI-010 is in the backlog list, hand-kept `todo`, and no row names it. It
  must come out `no-evidence`, never `agrees`, so AC-DS5 cannot pass vacuously on it.
- **One hand-kept-ahead item.** PBI-017 with a final GO-WITH-CONDITIONS.
- **One unattributed round.** A cr GO labelled "Code review round 2".

The paired hand-kept state is `560e296`'s eight `buildState` entries, verbatim in state:
017 done, 018 done, 021 done, 022 done, 023 done, 003 done, 001 conditions and 013 done.

### 7.1 `tests/test_derive.py` (added cases)

- **The four rules:**
  - `test_work_items_latest_round_go_is_done`: a NO-GO then a GO naming PBI-001 gives `done`, rounds 2,
    verdict `GO`, and `latestRound` is the GO run's id (AC-78's shape).
  - `test_work_items_conditions_tokens_are_conditions`: GO-WITH-CONDITIONS and APPROVE-WITH-CONDITIONS
    each give `conditions`.
  - `test_work_items_go_with_notes_and_approve_are_done`
  - `test_work_items_latest_nogo_or_changes_is_partial`
  - `test_work_items_activity_without_a_round_is_partial`: each of these alone gives `partial` with
    rounds 0 and verdict null: a cw DONE, a cw killed, a tw DONE, a cr `running`, and a cr killed.
- **What does not downgrade:**
  - `test_work_items_a_build_after_a_go_does_not_downgrade_it`
  - `test_work_items_an_unfinished_review_after_a_go_does_not_downgrade_it`
- **Attribution:**
  - `test_work_items_a_run_naming_three_pbis_credits_all_three`: the real label "Code-review gate
    PBI-003/004/005" (NO-GO) gives three items, each rounds 1 and `partial`.
  - `test_work_items_a_round_naming_no_pbi_credits_none_and_is_counted`: a cr GO labelled "Code review
    round 2" gives `items == {}` and `unattributedRounds == 1`. A cw with no id changes neither.
  - `test_work_items_plan_ver_req_other_and_orch_lanes_are_never_evidence`: an APPROVE `plan` run, an
    `exercised` `ver` run, and `other`/`req`/`orch` runs, each naming PBI-009, give no item.
- **Order and consistency:**
  - `test_work_items_order_is_start_then_id`: two rounds for one PBI in either input order give the
    same result; with identical `start`, the larger id is latest; the output is equal for every
    permutation of a six-row input.
  - `test_work_items_rounds_equal_findings_doc_rounds`: over `STALE_2026_09_12` plus a findings-bearing
    round, for every PBI in both, `items[p]['rounds'] == findings_doc(rows)[p]['rounds']`.
  - `test_work_items_output_round_trips_through_json`: `json.loads(json.dumps(x)) == x`, with no tuples.
- **The project document:**
  - `test_project_doc_carries_work_items_from_its_linked_sessions_only`:
    - a session linked to another project contributes nothing;
    - an exported but unlinked session contributes nothing;
    - a session listed under two projects counts only for its first (`project_of`);
    - a linked session missing from `results` contributes nothing.
  - `test_project_doc_always_writes_the_three_keys`: `workItems == {}`, `unattributedRounds == 0` and
    `workItemStatus == 'shadow'` for a project with no runs, and for a hand-built `p` with no
    `workItemStatus` key.
  - `test_project_doc_passes_work_item_status_through`: `derived` stays `derived`.
  - `test_a_project_doc_with_work_items_is_a_valid_local_record` (**non-vacuous**): a `project_doc`
    built from `STALE_2026_09_12` with non-empty `workItems` passes `records.validate('project', doc)
    == []`, and `records.from_row('project', records.to_row('project', 'dispatch-board', doc)) == doc`.
    It reads `local/records.py` by path, which imports nothing local (`local/records.py:12`), so there
    is no `local/**` edit.
- **The fixture:**
  - `test_the_2026_09_12_fixture_derives_done_for_the_five`: `items[p]['state'] == 'done'` for PBI-005,
    PBI-006, PBI-011, PBI-025 and PBI-026, with rounds 2, 2, 2, 2, 1. PBI-003 is `done`, PBI-017 is
    `conditions`, and `unattributedRounds == 1`.

### 7.2 `tests/test_export_sessions.py` (added cases)

End to end against synthetic transcripts, with the record builders the file already has:

- `test_project_document_carries_work_items`: a linked session with a cw DONE and a cr GO naming
  PBI-001 writes `out/projects/<pid>.json` with `workItems['PBI-001']['state'] == 'done'`.
- `test_rounds_in_an_unlinked_session_reach_no_project`: the same runs in an unlinked session leave
  every project's `workItems` empty.
- `test_work_items_are_identical_when_the_parse_is_reused_from_the_cache`: export twice. The second run
  reports 0 re-read, and the project document's `workItems` is byte-identical. This proves §4.4's
  no-bump claim on the cache path.
- `test_the_2026_09_12_scenario_end_to_end`: `STALE_2026_09_12` as transcripts gives the five PBIs
  `done` in `out/projects/dispatch-board.json`.
- `test_export_sessions_writes_no_board_tab_and_export_board_writes_no_project_document`: runs
  `export_board.main` then `main` into one `out/`, in refresh order (precedent `:1108`). It asserts:
  - the five board tab files are byte-identical to `export_board.main` alone;
  - the set of files under `out/projectTabs/` is unchanged by `main`, apart from `findings`;
  - `export_board.main` alone writes nothing under `out/projects/`.
- `test_an_unusable_work_item_status_exits_2_and_exports_nothing`

### 7.3 `tests/test_export_board.py` (added cases, `ProjectList` and `ExportProject`)

- `test_work_item_status_defaults_to_shadow`: covers the `projects` list and the legacy `build` block.
- `test_work_item_status_derived_is_kept`
- `test_unusable_work_item_status_is_refused`: for each of `null`, `true`, `1`, `""`, `"Derived"`,
  `"retired"` and `["shadow"]`, `ValueError` names the project and `workItemStatus`.
- `test_export_board_exits_2_on_an_unusable_work_item_status_and_leaves_out_as_it_was`
- `test_the_switch_does_not_reach_the_board_tabs`: `export_board.main`'s written bytes for all four
  spec tabs are identical under `shadow` and `derived`.

### 7.4 `tests/page.test.mjs` (added block, "shadow period")

Each case is a distinct fixture fed through the store adapter unless stated.

| Case | Fixture | Assertion |
|---|---|---|
| **AC-78** | platform-catalogue backlog with PBI-001 `todo` (unlisted); project `workItems` PBI-001 `{state:'done', rounds:1, verdict:'GO'}` | PBI-001's "From runs" cell reads "Review passed" and does not contain "Built and reviewed"; its row is `data-shadow="runs-ahead"` |
| **AC-110** | dispatch-board backlog with PBI-001 `partial`; `workItems` PBI-001 `done` | "Hand-kept" reads "Partly built", "From runs" reads "Review passed", and the row is flagged `runs-ahead` and listed under the group whose heading starts "Runs are ahead of the hand-kept state" |
| **AC-111** | hand-kept review `"GO-WITH-CONDITIONS (round 2)"`, derived rounds 3 verdict GO; then the same with hand-kept review `"—"` | The Review cell shows the hand-kept text and not "Round 3"; then it shows "Round 3: GO" |
| **2026-09-12 staleness** | The JS `STALE_2026_09_12`: backlog pbis PBI-003 `done`, PBI-005, 006, 010, 011, 025, 026 `todo`, PBI-017 `done`; `workItems` from §7.1's expected output; `unattributedRounds: 1`; the runs published with their labels | The set of `data-shadow="runs-ahead"` rows is **exactly** {PBI-005, PBI-006, PBI-011, PBI-025, PBI-026}; `handkept-ahead` is exactly {PBI-017}; `agrees` is **exactly {PBI-003}**; `no-evidence` is **exactly {PBI-010}**. Tiles read Agree 1, runs ahead 5, hand-kept ahead 1, not named 0, no evidence 1, and "Review rounds naming no work item" 1. PBI-010 is listed under "No evidence either way" and in no difference group. PBI-025's evidence line contains "Code-review PBI-025 round 2" and "GO". "Needs attention" contains "5 work items: runs are ahead of the hand-kept state" and "not proof of merge". The project's `last` is `'2026-09-12T18:40:00Z'`, and the panel contains "were last active " followed by that value formatted with the page's `when()` options |
| **All agree** | done/done, conditions/conditions, partial/partial, **plus** one todo with no item | No `runs-ahead`, `handkept-ahead` or `unnamed` anywhere; no "Where hand-kept and derived state differ" group; the text "agree for all 3 work items that a run names" and "1 work item(s) named by no run" are present, and "agree for all 4" is **absent**; the todo row is `data-shadow="no-evidence"`, not `agrees`; "Agree" tile 3, "No evidence" tile 1, the flagged tiles 0; no shadow attention item |
| **Run naming no PBI, nothing to compare** | `unattributedRounds: 2`, `workItems: {}`, all four hand-kept `todo` | Tile "Review rounds naming no work item" reads 2; no table row gains a derived state from it; every row is `data-shadow="no-evidence"` and none is `agrees`; "Agree" tile 0, "No evidence" tile 4; "nothing to compare. None is counted as agreeing" is present |
| **Last activity unknown** | the 2026-09-12 fixture with the project's `last: null` | "Those sessions have no recorded activity." is present, and "were last active" is absent; no error |
| **Not named by any run** | hand-kept `done`, `workItems: {}` | Row `data-shadow="unnamed"`, listed under "Not named by any run" |
| **Not in the PBI list** | `workItems` holds `PBI-000`, absent from `pbis` | "Named by runs but not in the PBI list: PBI-000" is present; the table and tile totals are unchanged |
| **Derived mode** | `workItemStatus:'derived'`, hand-kept PBI-001 `todo` and PBI-002 `done`, derived PBI-001 `conditions`, no item for PBI-002 | Tiles count conditions 1 and "No run names it" 1, and no tile reads "Built and reviewed" or "Not started"; no "Hand-kept" column, no `data-shadow`, no shadow panel; the retirement line is present and contains "not proof the change merged"; the badge is 1; Overview cells show `cell conditions` for PBI-001 and `cell todo` for PBI-002; "Needs attention" has "PBI-001 review conditions", which is the M-3 consequence pinned |
| **Derived mode keeps overrides** | as above, with hand-kept PBI-002 `review:"GO (round 2)"`, `commit:"abc1234"` | Review "GO (round 2)" and commit "abc1234" are shown |
| **Absent** | a project document with no `workItems` (the existing backlog fixtures at `tests/page.test.mjs:109`, `:1400-1404`) | No "Shadow period" text, no `data-shadow`, one "State" column; the Backlog and Overview markup equals that fixture rendered with `workItemStatus:'derived'` and no `workItems` (the mode alone changes nothing without data) |
| **Cannot compare** | hand-kept state `"constructor"`, derived `"__proto__"` | Tag "Cannot compare"; counted in neither agree nor differ; no `console.error` (the harness fails on one, `CLAUDE.md:109`) |
| **Escaping** | latest-round run label `<img src=x onerror=alert(1)>`, verdict `` `x` **y** ``, hand-kept `open` `<b>z</b>` | No raw `<img` and no `<b>`/`<code>` produced from the label, verdict or `open`; the characters appear escaped |
| **Evidence not found** | `latestRound: 'gone'` | Evidence reads "latest review: round 2, GO"; no error |
| **Session filter** | a project with two sessions; select one | The Backlog markup is identical before and after selecting |
| **Tones** | the 2026-09-12 fixture | The shadow panel's markup and every `data-shadow` row, `no-evidence` included, contain none of `var(--human)`, `var(--nogo)`, `var(--changes)`, `class="tag nogo"`, `class="tag changes"`, `class="tag human"` or `callout warn` |
| **Equivalence (FR-97)** | `EQ_PROJECTS`: `PROJECTS` with dispatch-board given `workItems` over the existing `EQ_PROJECT_TABS` backlog (`:1400-1404`): PBI-001 `done` (agrees), PBI-002 `partial` (hand-kept `conditions`, so hand-kept ahead), PBI-003 absent (hand-kept `partial`, so not named), PBI-004 `done` (hand-kept `todo`, so runs ahead). **Revision 2 adds a fifth backlog item** to `EQ_PROJECT_TABS`' dispatch-board backlog (`:1400-1404`; the constant is used only at `:1418`): `PBI-005`, `todo`, with no derived item, so it is **no evidence**. Dispatch-board's `last` is a fixed ISO time. Used on **both** sides: `overStore` (`:1442`) and `EQ_RECORDS` (`:1430`) | `emptyPanels` is still `[]` on both sides (`:1463-1465`); the `seen` list (`:1467-1471`) gains `['each shadow outcome', …]` rows for `data-shadow="agrees"`, `"runs-ahead"`, `"handkept-ahead"`, `"unnamed"` and `"no-evidence"`, and one for `/were last active/`; `rendered(l)` deep-equals `rendered(s)` (`:1472`). The existing `seen` rows are presence checks that one more `todo` item cannot break |

### 7.5 Suites that stay green unedited

- **`python -m unittest discover -s local/tests`**, which is outside the areas. It must pass with no
  edit, in particular `local/tests/test_collector_equivalence.py:84-91` and
  `local/tests/test_conformance.py:397-411`. A failure is a **stop and report** (row Q-13).
- **`tests/test_refresh.py`**: unchanged, because `refresh.py` is untouched (§4.3).
- **Every existing case** in `tests/test_derive.py`, `tests/test_export_sessions.py`,
  `tests/test_export_board.py` and `tests/page.test.mjs`.

---

## 8. Acceptance criteria

**From the PBI file** (`docs/backlog/pbi/PBI-010-derived-status.md:40-41`):

- [ ] **AC-78** When the latest code-reviewer run naming PBI-001 in a platform-catalogue linked session
      has verdict `GO` and no hand-kept build state lists PBI-001, the platform-catalogue Backlog shall
      show PBI-001 as done. **Read here as:** in shadow mode the "From runs" column shows "Review
      passed" beside the hand-kept "Not started"; in derived mode the state column does. "Review
      passed" is this spec's wording for derived `done`, because a passed review is not proof of merge
      (revision 2, M-1).
      *(§3.2, §6.2, §6.3; §7.1 first case, §7.4 AC-78 case and derived-mode case.)*
- [ ] **Close-out:** see AC-DS23.

**From the PRD**, for the requirements this PBI implements (FR-175, FR-176):

- [ ] **AC-110** While the shadow period is active, when PBI-001's derived state is done and its
      hand-kept state is `partial`, the Backlog shall show both states and flag PBI-001.
      *(§6.1, §6.2; §7.4 AC-110 case.)*
- [ ] **AC-111** When a work item has a hand-kept `review` value, the Backlog tab shall show that value
      in place of the derived review summary. *(§6.5; §7.4 AC-111 and derived-mode-override cases.)*

**Added by this spec.** Each names a fixture that contains the awkward case.

- [ ] **AC-DS1 The mapping.** `derive.work_items` returns the §3.2 state for each §7.1 rule fixture, and
      **no entry** for a PBI named by no `cw`/`tw`/`cr` run. No `todo` value is ever emitted.
- [ ] **AC-DS2 Attribution.** A round labelled "Code-review gate PBI-003/004/005" is one round for each
      of the three. A finished round naming no PBI adds to `unattributedRounds` and to no item. Runs on
      the `plan`, `ver`, `req`, `other` and `orch` lanes are never evidence, shown on a fixture where
      each names a PBI.
- [ ] **AC-DS3 Determinism.** `work_items` output is identical for every permutation of a six-row input,
      and "latest" is decided by `(start or '', id)`.
- [ ] **AC-DS4 Linked sessions only, consistent with the ledger.**
  - `project_doc`'s `workItems` counts only rows from its linked, exported sessions, shown on a fixture
    holding each excluded kind (another project's, unlinked, listed-twice, missing from `results`).
  - For every PBI with rounds, `rounds` equals `findings_doc`'s `rounds` over the same rows.
- [ ] **AC-DS5 The 2026-09-12 staleness is detected, and only it.**
  - `STALE_2026_09_12` exported end to end derives `done` for PBI-005, PBI-006, PBI-011, PBI-025 and
    PBI-026.
  - On the page, with `560e296`'s hand-kept states, the `runs-ahead` set is **exactly** those five,
    `handkept-ahead` exactly {PBI-017}, `agrees` **exactly {PBI-003}** and `no-evidence` **exactly
    {PBI-010}**. PBI-010, which no run names, is never `agrees`. *(Amended in revision 2, H-1.)*
  - The "Agree" tile reads 1 and the "No evidence" tile reads 1.
  - "Needs attention" says "5 work items: runs are ahead of the hand-kept state", with a message
    containing "not proof of merge".
- [ ] **AC-DS6 All agree is stated, not blank, and counts only run-backed agreement.** *(Amended in
      revision 2, H-1.)* On the all-agree fixture, which also holds one hand-kept `todo` that no run
      names:
  - no row carries a flagged `data-shadow` value, and the `todo` row is `no-evidence`, not `agrees`;
  - the agreement sentence counts 3, the run-backed items: "agree for all 3 work items that a run
    names". "agree for all 4" is absent, and the no-evidence sentence counts 1;
  - the "Shadow period" explanation sentence is present;
  - the flagged tiles read 0, "Agree" reads 3, "No evidence" reads 1, and no shadow attention item
    exists.

  On the nothing-to-compare fixture (all `todo`, `workItems: {}`), "Agree" reads 0, no row is `agrees`,
  and the "nothing to compare. None is counted as agreeing" sentence is present.
- [ ] **AC-DS7 A run naming no PBI.** With `unattributedRounds: 2` the tile reads 2 and no work item's
      derived state changes.
- [ ] **AC-DS8 Not named by any run.** A hand-kept `done` with no derived entry is flagged `unnamed` and
      listed in its group. A run-named id absent from the PBI list is listed as text and counted
      nowhere.
- [ ] **AC-DS9 The switch is read and validated.**
  - `board_config.projects` gives `workItemStatus` `shadow` when absent (both config shapes) and keeps
    `derived`.
  - Every other value in §7.3's list raises `ValueError` naming the project and key.
  - `export_board.main` and `export_sessions.main` each return 2 with `out/` unchanged.
  - `project_doc` publishes the value.
- [ ] **AC-DS10 Derived mode.** With `workItemStatus: 'derived'`:
  - tiles, graph tones, state column, badge, Overview cells and the conditions/partial attention items
    use the derived state, with absence as `todo`;
  - the `done` tile reads "Review passed" and the `todo` tile reads "No run names it" *(revision 2)*;
  - no hand-kept column, shadow column, shadow panel or `data-shadow` is drawn;
  - the retirement line is present and states that a passed review is not proof of merge *(revision 2,
    M-1)*;
  - a derived `conditions` item adds "<id> review conditions" to "Needs attention", which is the M-3
    consequence, pinned so a flip's effect is known;
  - hand-kept `review`, `open` and `commit` still override.
- [ ] **AC-DS11 The switch is the owner's.** `git diff --name-only main...HEAD` on the PBI branch lists
      neither `board.config.json` nor any `projects/*.json`. No exporter, test or page code writes
      `workItemStatus` to a file or the store; a search of the diff finds it only as a read and as test
      input. **Actor *(revision 2, L-4)*:** the `review-agents:code-reviewer` run of the code-review gate
      performs both checks on the PR diff and states the result in its findings. A GO without that
      statement does not close this criterion.
- [ ] **AC-DS12 Ownership and store.**
  - `export_board.py`, `exporters/refresh.py` and every `local/**` file are unchanged on the branch.
  - §7.2's refresh-order test shows the five board tabs byte-identical and no new file under
    `out/projectTabs/`.
  - `export_board.main` writes nothing under `out/projects/`.
  - `workItems` appears only on `projects/<id>` documents.
- [ ] **AC-DS13 Cache.**
  - `PARSER_VERSION` is **unchanged from the build base**: the diff against the base leaves its line in
    `exporters/export_sessions.py` untouched. No literal value is pinned, because PBI-014 and PBI-009
    each move it before this builds *(revision 2, M-2)*.
  - `derive.agent_row`, `pbis`, `classify`, `verdict_of` and `kind_of` are unchanged (their existing
    test cases pass unedited).
  - A second export reusing every cached parse writes a byte-identical `workItems`.
- [ ] **AC-DS14 Local records.**
  - A `project_doc` with non-empty `workItems` validates against `local/records.py`'s `project` shape
    and round-trips through `to_row` / `from_row`.
  - `python -m unittest discover -s local/tests` passes with no file under `local/` edited.
- [ ] **AC-DS15 Tone and wording.** The shadow panel and flagged rows contain no `--human`, `--nogo` or
      `--changes` token, no `nogo`/`changes`/`human` tag class and no `callout warn`. The three group
      headings and the hand-kept-ahead explanation line are present as §6.2 words them.
- [ ] **AC-DS16 Escaping.** A run label `<img src=x onerror=alert(1)>`, a verdict with backticks and
      `**bold**`, and a hand-kept `open` of `<b>z</b>` render as literal text. No tag and no
      `<code>`/`<b>` is produced from any of them, proving `md()` was not applied.
- [ ] **AC-DS17 Review summary.** With hand-kept review `—` or absent, the Review column shows
      "Round N: <verdict>" (rounds > 0), "N build run(s), no review yet" (builds only) or `—`.
- [ ] **AC-DS18 Absent derived state.** A project document without `workItems` renders the Backlog and
      Overview with no shadow markup and a single State column, identically under both switch values.
- [ ] **AC-DS19 Cannot compare.** A hand-kept state `"constructor"` against a derived `"__proto__"` shows
      "Cannot compare", is counted in no agree or differ tile, and logs nothing.
- [ ] **AC-DS20 Session filter.** Selecting one session of a two-session project leaves the Backlog
      markup identical.
- [ ] **AC-DS21 Both adapters (FR-97, PBI-006).** *(Amended in revision 2, H-1.)*
  - The equivalence board carries `data-shadow` rows of all five outcomes (`agrees`, `runs-ahead`,
    `handkept-ahead`, `unnamed`, `no-evidence`) and the last-active sentence, asserted by name on the
    local side.
  - `emptyPanels` is `[]` on both sides.
  - `rendered(l)` deep-equals `rendered(s)`.
- [ ] **AC-DS22 NFR-22: a visual check with a named actor, at close-out, not build output.** No regex can
      judge "professional dashboard", legibility, or dark and light. Before the PR is marked ready, the
      PBI's Evidence section must record **one** of these.

      **Who writes it, and where *(revision 2, L-3)*.** The Evidence section of
      `docs/backlog/pbi/PBI-010-derived-status.md` (`:45-47`) is outside `allowed_areas` (`:7`). The build branch
      therefore never edits that file. **The orchestrator writes it, at finalize (`pbi-lifecycle
      finalize`), on `main`**, as close-out bookkeeping. The builder only reports the owner's words or
      the artefact path in its change report.
  - **Primary: the owner looked.** The owner viewed the rendered Backlog tab in shadow mode (with at
    least one flagged item) and the Overview, in dark and light, and confirmed them against the design
    rules (`CLAUDE.md:131-138`; NFR-9, NFR-10, NFR-13, NFR-14 at `docs/prd/dispatch-board.md:548-553`).
    The owner's words are recorded verbatim. The local server serves the page, so the owner can look
    without publishing anything.
  - **Fallback, only with the owner's permission to write it:** a rendered-screenshot artefact under
    `docs/backlog/evidence/<date>-pbi-010-shadow/`, following `docs/backlog/evidence/2026-09-11-page-checks/`,
    at 1050 px in both themes, with a written check against each design rule. The owner's confirmation
    is then outstanding, not assumed. `docs/backlog/evidence/**` is **not** in this PBI's areas
    (`docs/backlog/pbi/PBI-010-derived-status.md:7`), which is why the owner route is primary.

  A close-out with neither is incomplete.
- [ ] **AC-DS23 Close-out.**
  - `python -m unittest discover -s tests` and `node tests/page.test.mjs` are green on the head commit.
  - `python -m unittest discover -s local/tests` is green with `local/` unedited.
  - The code-review gate passed (`review-agents:code-reviewer` GO).
  - The owner's go-ahead was recorded before implementation began (`requires_external_review`,
    `docs/backlog/pbi/PBI-010-derived-status.md:12`, `:53`).
  - **Recorded by the orchestrator at finalize, on `main`** *(revision 2, L-3)*. It ticks the PBI file's
    criteria and fills its Evidence section (`docs/backlog/pbi/PBI-010-derived-status.md:36-47`), both outside
    `allowed_areas`, so neither is edited on the build branch.
- [ ] **AC-DS24 No evidence is never agreement, and the evidence's age is stated.** *(New in revision 2,
      H-1.)*
  - `data-shadow="no-evidence"` is drawn for every hand-kept `todo` with no derived item, and
    `agrees` only where `workItems[id]` exists and its `state` equals the hand-kept state.
  - The "No evidence" tile counts exactly the `no-evidence` rows, and the "Agree" tile never includes
    one.
  - The shadow sentence states "were last active " followed by `when(project.last)`, or "Those sessions
    have no recorded activity." when `last` is null or unreadable. Both branches are shown on fixtures:
    the 2026-09-12 fixture and the last-activity-unknown case.
- [ ] **AC-DS25 Derived `done` is "Review passed", and runs-ahead is not called stale.** *(New in
      revision 2, M-1.)*
  - Derived `done` renders "Review passed" in the "From runs" column, the derived-mode state column and
    the derived-mode tile, and never "Built and reviewed".
  - Three texts are present exactly as §6.2 and §6.4 word them: the runs-ahead group heading ("…
    out-of-date entries, work in flight, or reviews awaiting merge"), its fixed line, and the runs-ahead
    attention item's message ("… not proof of merge").
  - The derived-mode line states that a passed review is not proof of merge.

**Why none of these can be met vacuously.**

- **AC-DS5** names exact sets, not "at least one", and its fixture holds a no-evidence item (PBI-010),
  so a design that still called it agreeing fails.
- **AC-DS6's** all-agree fixture holds a no-evidence item too, so a count of 4 fails.
- **AC-DS14 and AC-DS21** require non-empty `workItems` in the checked documents. AC-DS21's board
  carries all five outcomes.
- **AC-DS22** is the one criterion a machine cannot close, which is why it names its actor.

**That is 28 criteria:** AC-78 and the close-out from the PBI file, AC-110 and AC-111 from the PRD, and
24 added (AC-DS1 to AC-DS22, AC-DS24 and AC-DS25; AC-DS23 is the close-out restated).

---

## 9. Assumptions and open questions

**OWNER** marks a row that genuinely needs the owner. The rest are settled here, subject to the spec gate.

| # | Question | Default chosen (what the build does absent an answer) | Impact if wrong | Needs |
|---|---|---|---|---|
| Q-1 | **The 2026-09-12 work was invisible on real data.** Every run naming PBI-004, 005, 006, 008, 011, 019, 025 and 026 is in session `7e0c4f3c`, which at `560e296` was linked to no project; dispatch-board linked only `9562c312` (§2.5). The round-1 reviewer confirmed it. **Linked on 2026-09-13:** after the round-1 review the orchestrator added `7e0c4f3c` to dispatch-board's `sessions` (`board.config.json:33`). It is a working-tree change, not yet committed. It moves that session's runs (73 at the round-1 re-measurement) and its usage into dispatch-board's Dispatch, catalogue and usage views | The build proceeds. **Operationally resolved for today's data by the 2026-09-13 link.** The design no longer depends on it (revision 2, H-1): a future unlinked build session's stale `todo` now reads as **no evidence**, never agreement, and the panel says when the linked sessions were last active (AC-DS24). **Recommendation:** the owner commits the config change and links each future build session | A future build session left unlinked hides its work from the derivation. After H-1 the page shows that as "no evidence" beside an old last-active time, not as agreement | **OWNER** (non-blocking; operationally resolved 2026-09-13) |
| Q-2 | `CLAUDE.md` becomes incomplete: the `projects/<projectId>` store row (`CLAUDE.md:40`), the hand-kept section (`:123-129`), the new `workItemStatus` key and the "only the owner sets it" rule. `CLAUDE.md` is not in this PBI's `allowed_areas` (`docs/backlog/pbi/PBI-010-derived-status.md:7`), and the parent's permission is conditioned on a declared `docs` touch that PBI-010's row does not declare (`docs/backlog/specs/dispatch-board.md:216-217`, `:249`); PBI-020 Q-1 is the precedent | **Ask before editing.** The build leaves `CLAUDE.md` alone and reports the gap at close-out. The owner chooses: (a) add `CLAUDE.md` to `allowed_areas` before the build, or (b) pre-register a `chore-work` sweep after merge | A documented contract lags the code until (a) or (b); the owner-only rule for the switch exists only in this spec until then | **OWNER** |
| Q-3 | **GO-WITH-CONDITIONS stays `conditions` even after the conditions were applied and the PR merged.** This workflow merges on GO-WITH-CONDITIONS with conditions applied (`CLAUDE.md:153-156`). Such items land in "hand-kept ahead": platform-catalogue **4 of its 9** hand-kept-ahead items (the other five are `partial`) and dispatch-board 3 of 3, at revision 1's 2026-09-13 measurement (§2.6). **In derived mode** (revision 2, M-3) they stay `conditions` for good, each adding a permanent "<id> review conditions" attention item (`site/index.html:524`). Today that is dispatch-board 017, 022 and 023, and platform-catalogue 000, 001, 002 and 008 (§5.3, §6.3) | Keep FR-113's literal mapping; separate the difference by direction so it does not bury the staleness signal (§6.1). **Refused:** inferring "conditions applied" from a later `cw` fix run (rule 1) | A flip taken without settling this leaves seven permanent "Conditions open" states and attention items. Remedies: the owner accepts that, **or** the build process adds a short confirming review round after conditions are applied, **or** the owner accepts an inference rule in a follow-up | **OWNER — blocking before the switch is flipped to `derived` for any project**; not blocking the build |
| Q-4 | Use the git tab's `pulls` (`MERGED` plus a `pbi/PBI-0nn-…` branch) as merge evidence? | **No** (§2.4): only the 20 most recent PRs, a naming habit, no remote for platform-catalogue, absent locally, and it belongs to the other exporter | A "merged" corroboration tag on the page is a reasonable follow-up PBI (page-only, store adapter only, marked as such). Recorded, not built | settled, FYI |
| Q-5 | Is the page's rank comparison a derivation that the parent rule (`docs/backlog/specs/dispatch-board.md:87`) puts in `derive`? | **No** (§4.1): it joins two exporters' documents and is identical code under both adapters. Every evidence judgement stays in `derive` | If the reviewer disagrees, the only placement that avoids cross-exporter reads is a third document built from both. That is a larger change needing a local shape follow-up | settled at gate |
| Q-6 | The switch in `board.config.json` rather than `projects/<id>.json` | **Config** (§5.1): the owner's decision stays out of the file the build session edits; the mode travels with the derived data | Moving it later is a small change in `board_config` and `project_doc` | settled |
| Q-7 | A third switch value that hides derived state without retiring anything? | **No.** Two values; removing the key restores shadow | If derived state proves noisy, the owner has no "off" short of a code change | settled |
| Q-8 | A label mentioning a second PBI in passing credits both (§2.2) | Keep `findings_doc`'s rule, so features 3 and 4 attribute identically; show the evidence run label on every flagged item | A mis-credit is visible rather than silent; a label convention ("one PBI id per task description") would remove it | settled |
| Q-9 | Spec-gate (`plan`) approvals and spec-author (`other`) runs are not evidence | Correct by definition: an approved spec is not built work (§3.1) | A PBI mid-spec-gate shows "No run names it", which is accurate for "built" | settled |
| Q-10 | A hand-kept `review` of exactly `"—"` cannot be told from an absent one (`exporters/derive.py:845`) | Treated as absent; the derived summary shows | Only an explicit `"—"` is affected. Low | settled |
| Q-11 | Should derived `todo` be published? | **No** (§2.3, §3.2): absence is unprovable, so it is shown as "No run names it". Against a hand-kept `todo` it is **no evidence**, never agreement (revision 2, H-1) | None: FR-175's comparison still flags a hand-kept non-`todo` with no evidence (`unnamed`) | settled |
| Q-12 | `projects/<pid>` and `projectTabs/<pid>.backlog` can briefly come from different pushes when a plan splits into several batches (`CLAUDE.md:79`) | Accepted: the page re-renders on the next document | A shadow outcome may be wrong for seconds during a push | settled, Low |
| Q-13 | Do the three added keys really pass `local/tests` untouched? §4.5 argues yes from `local/records.py:21` and `:50-56` | Run the suite; **a failure is a stop and an owner question, never a `local/**` edit.** Were it to fire, the recommended follow-up is a local-shapes PBI in the style of PBI-026 | Low if it passes as argued; a hard stop if not | settled (contingent) |
| Q-14 | `PARSER_VERSION` | **No bump:** unchanged from the build base, whatever value PBI-014 and PBI-009 have left it at (§4.4); conditional on AC-DS13 | A missed bump would replay rows without the fields read, but none are new | settled |
| Q-15 | `projects/**` is in the PBI's areas "read and annotate only", and this design writes nothing there | **Unused.** An unused allowed area is not a defect; C-20 holds trivially | None | settled |
| Q-16 | How long does the shadow period last? | Until the owner sets `derived` for a project (A-48, S-39). No date, timer or automatic end | As A-48 records: the two states disagree on the Backlog for as long as the owner leaves it | settled (the mechanism); the end is the owner's |
| Q-17 | **The AC-64 equivalence fixture (revision 2, L-1).** The parent rule says whichever of PBI-019 and a feature PBI lands second "extends the AC-64 equivalence fixture to the new fields" (`docs/backlog/specs/dispatch-board.md:270`). PBI-019 has landed, so that is this PBI. **The rule is not met as written, and the spec does not argue that it is.** The comparison is whole-record (`local/tests/test_collector_equivalence.py:91`), so the three new keys are compared on every project record with no edit. But the only PBI-naming run in a linked session of that fixture is a code-writer run labelled "PBI-002 fix review notes" (`:32`, linked by `build=[S[0], S[3]]` at `:67`). It yields only PBI-002 `partial` with no round, so `done`, `conditions`, `rounds > 0`, `latestRound` and a non-zero `unattributedRounds` never reach the comparison. `local/**` is not in this PBI's areas. **A sibling hit this exact gap:** PBI-014's areas excluded `local/**`, and PBI-027 was raised as its follow-up (`docs/backlog/pbi/PBI-027-collector-repo.md:65`) | The build proceeds **with no `local/**` edit**. The collector reaches the new keys only through the same `derive.project_doc`, called with identical arguments (`exporters/export_sessions.py:289`, `local/collector.py:440`; upheld at round 1). Every state path is tested in `tests/` (§7.1). **Recorded default (revision 3, round-2 gate): option (b).** The orchestrator pre-registers the follow-up at this PBI's finalize, either as a local-tests PBI raised through `pbi-intake`, or folded into **PBI-027** (`docs/backlog/pbi/PBI-027-collector-repo.md`, which already files the equivalent gap for PBI-014 and has not yet built), so the gap is never left noted with nothing on the backlog. **If the owner grants the one file, `local/tests/test_collector_equivalence.py`, before the build**, option (a) replaces it: one added linked scenario with a cr GO, a cr GO-WITH-CONDITIONS and a cr GO naming no PBI; AC-DS12's and AC-DS14's "no `local/` file edited" then exempt that one file | Low: a collector-to-exporter divergence in the new fields could only come from the shared function's callers, which are identical today. It would go unseen by `local/tests` until the local app is used | **OWNER** (non-blocking for the build; default is (b), pre-registered at finalize) |

**Four rows need the owner: Q-1, Q-2, Q-3 and Q-17.** Only Q-3 blocks anything, and not the build:

- **Q-1** is non-blocking and operationally resolved by the 2026-09-13 link. After H-1 the design no
  longer depends on it.
- **Q-2** is a documentation grant, and the same class of question as PBI-020's Q-1.
- **Q-3** is a process choice about GO-WITH-CONDITIONS. **It is blocking before the switch is flipped
  to `derived` for any project.**
- **Q-17** is the AC-64 fixture. **Recorded default: option (b)** — the orchestrator pre-registers the
  follow-up at finalize (a local-tests PBI via `pbi-intake`, or folded into PBI-027). A grant of the one
  file before the build replaces it with option (a). PBI-010 does not close out with the gap merely
  noted and no follow-up on the backlog.

Q-4 carries an FYI. Every other row is settled here.

---

## 10. Out of scope

- **Retiring the hand-kept state** (S-39). This PBI builds the switch; the owner flips it.
- **Deleting or rewriting `projects/*.json`** (C-20).
- **Merge evidence from pull requests** (§2.4, Q-4). No join between `pulls` and runs.
- **A derived "open" or "commit"** (§6.5). Neither is provable from runs.
- **Editing `board.config.json`.** Session `7e0c4f3c` was linked by the orchestrator on 2026-09-13,
  outside this PBI (Q-1); the build never edits the file.
- **Extending the AC-64 fixture under `local/tests/**`** (Q-17), unless the owner grants that one file
  before the build. Absent that grant, the follow-up is pre-registered by the orchestrator at PBI-010's
  finalize (Q-17's recorded default, revision 3), not built here.
- **The PBI file's criteria and Evidence section**: written by the orchestrator at finalize, on `main`
  (AC-DS22, AC-DS23).
- **`CLAUDE.md` and `README.md`** (Q-2).
- **`exporters/export_board.py`, `exporters/refresh.py`, and every file under `local/`** (§4).
- **Any change to run parsing:** `agent_row`, `pbis`, `classify`, `verdict_of`, `kind_of`,
  `PARSER_VERSION` (§4.4).
- **The Findings ledger tab** and `findings_doc`'s behaviour (reused as a reference only).
- **Answers, of any kind** (C-16).

---

## 11. Spec-gate record

| Round | Revision reviewed | Verdict | Review note |
|---|---|---|---|
| 1 | 1 | CHANGES-REQUIRED | `docs/backlog/reviews/PBI-010/spec-review-r1.md` |
| 2 | 2 | APPROVE-WITH-NOTES | `docs/backlog/reviews/PBI-010/spec-review-r2.md` |

Round 1 (2026-09-13): CHANGES-REQUIRED, 1 High, 3 Medium, 4 Low. **All eight are applied in revision
2, and none is deferred.** L-1 is applied by raising an OWNER row (Q-17) rather than by argument. See
`docs/backlog/reviews/PBI-010/spec-review-r1.md`.

**What the reviewer upheld is unchanged in revision 2**, and no part of the design was weakened to meet a
finding:

- about 60 citations checked with no drift;
- Q-1's premise: the 2026-09-12 work lived in unlinked session `7e0c4f3c`;
- the validation claim: with that session linked, every merged-but-unrecorded PBI comes out
  runs-ahead, each with a real merged PR (11 at revision 1's snapshot, 13 on live data);
- `board.config.json` is not a scope risk: the default and validation live in `board_config.projects()`
  (`exporters/board_config.py:130-132`);
- `project_doc` is called identically by `exporters/export_sessions.py:289` and `local/collector.py:440`;
- no `PARSER_VERSION` bump is needed, even against a moved base;
- attribution, and the rejection of pull requests as merge evidence.

**Context change after the review.** On 2026-09-13 the orchestrator linked `7e0c4f3c` to dispatch-board
(`board.config.json:33`, a working-tree change, not yet committed). That resolves Q-1's real-data case
operationally. It does not resolve H-1, and revision 2 does not treat it as doing so.

| Finding | Sev | Disposition in revision 2 |
|---|---|---|
| H-1 | **High** | **Applied: the design no longer reports agreement without evidence.** §6.1 adds a fifth outcome, **No evidence** (`item` absent, hand-kept `todo`, `data-shadow="no-evidence"`, `.tag.no-evidence`). It is not flagged, and never counted as agreement. "Agrees" now requires a derived item. §6.2 gives it its own tile ("No evidence") and its own list ("No evidence either way", outside the difference groups). The all-agree sentence counts **only run-backed agreement**, and states "nothing to compare" when no run names any item. The shadow sentence states when the linked sessions were last active, from `project.last` (`exporters/derive.py:749`) through `when()` (`site/index.html:273`), with a no-activity fallback. It uses `when()` rather than `ago()` so the two-adapter deep-equal stays deterministic. **AC-DS5** now pins `agrees` exactly {PBI-003} and `no-evidence` exactly {PBI-010}. **AC-DS6's** fixture holds a no-evidence item, so a count of 4 fails, and it adds a nothing-to-compare case. **AC-DS21's** equivalence board gains a fifth backlog item so all five outcomes and the last-active sentence are compared. **AC-DS24** is new. §2.5, §2.6 (platform-catalogue's PBI-012 is now no evidence, named 12 not 13, agree 2 not 3), §1, rule 4, §2.3, Q-1 and Q-11 are corrected to match. The fixture tests keep a no-evidence item in every agreement-bearing case, so none passes vacuously |
| M-1 | Med | **Applied.** Derived `done` is labelled **"Review passed"** through a new `derivedLabel`, in the same tone as `stateLabel`'s "Built and reviewed" (`site/index.html:289`). `stateLabel` stays the hand-kept vocabulary (§3.2, §6.2, §6.3). The runs-ahead group heading now reads "… out-of-date entries, work in flight, or reviews awaiting merge", with a fixed line saying a passed review is not proof of merge. The runs-ahead attention item's message says the same (§6.4). The derived-mode line says `done` is not proof of merge (§6.3). §2.6's claim is corrected: every runs-ahead item was stale **only at revision 1's measurement**, and by the review's re-measurement the group held the in-flight PBI-007 and PBI-014. AC-78's reading and §7.4's AC-78, AC-110 and derived-mode cases are updated. **AC-DS10** is amended and **AC-DS25** is new |
| M-2 | Med | **Applied.** §4.4 and AC-DS13 no longer pin a literal 6. Both require `PARSER_VERSION` **unchanged from the build base**. PBI-014 moves it from 6 to 7, and PBI-009's spec requires its own bump (`docs/backlog/specs/pbi-009-waiting-on-you.md:795`). Q-14 matches |
| M-3 | Med | **Applied.** §5.3 and §6.3 state the derived-mode consequence. Items closed on GO-WITH-CONDITIONS with no later round stay `conditions` for good: today dispatch-board 017, 022 and 023, and platform-catalogue 000, 001, 002 and 008. Each adds a permanent "review conditions" item to Needs attention (`site/index.html:524`); §6.4 says so, and AC-DS10 pins it. §2.6's "dominated" is corrected: GO-WITH-CONDITIONS accounts for **4 of 9** on platform-catalogue, and the other five are `partial`. **Q-3 is now marked blocking before the switch is flipped to `derived`**, not blocking the build |
| L-1 | Low | **Raised as OWNER (Q-17), not argued.** The whole-record comparison (`local/tests/test_collector_equivalence.py:91`) does compare the new keys. But that fixture's only linked PBI evidence (`:32`, `:67`) yields PBI-002 `partial` with no round, so the rule "extends … to the new fields" is not met as written. The spec says so plainly and notes that PBI-014 hit the same planning gap and needed PBI-027 (`docs/backlog/pbi/PBI-027-collector-repo.md:65`). The default is that the build proceeds with no `local/**` edit; the owner picks a one-file grant before the build or a follow-up PBI. §10 records it |
| L-2 | Low | **Applied.** Every §2.6 row carries its measurement time. A live row is added: 20 named and 13 runs-ahead, because `7e0c4f3c` grew from 51 to 73 runs. The text states that the figures will keep moving now that the session is linked. No-evidence counts not re-measured for revision 2 are marked so, not invented |
| L-3 | Low | **Applied.** AC-DS22 and AC-DS23 name the actor and branch. The Evidence section and the criteria ticks of `docs/backlog/pbi/PBI-010-derived-status.md` are written **by the orchestrator, at finalize, on `main`**, never on the build branch, because the file is outside `allowed_areas` (`:7`). §10 records it |
| L-4 | Low | **Applied.** AC-DS11's diff checks are assigned to the `review-agents:code-reviewer` run of the code-review gate, which states the result in its findings. A GO without that statement does not close the criterion |

**Owner rows after revision 2:**

- **Q-1:** OWNER, non-blocking; operationally resolved by the 2026-09-13 link, and no longer
  load-bearing after H-1.
- **Q-2:** OWNER, the `CLAUDE.md` grant.
- **Q-3:** OWNER, **blocking before the switch is flipped to `derived`**, not blocking the build.
- **Q-17:** OWNER, new (L-1): the AC-64 fixture, as a grant before the build or a follow-up PBI.

Implementation also needs the owner's explicit go-ahead (`requires_external_review: true`,
`docs/backlog/pbi/PBI-010-derived-status.md:12`), recorded verbatim here or in the PBI file before any code is written.

**For the round-2 reviewer, the load-bearing changes to re-verify independently:**

1. **§6.1 and §6.2:** no path counts a work item without a derived item as agreement: not the tag, the
   tile, nor the all-agree sentence.
2. **§7.4 and §8:** AC-DS5, AC-DS6, AC-DS21 and AC-DS24 each hold a no-evidence item in their fixture.
3. **§6.2:** `when()` (`site/index.html:273`) rather than `ago()` (`:274-279`) keeps the two-adapter
   deep-equal deterministic.
4. **Q-17:** the reading of `local/tests/test_collector_equivalence.py:32`, `:67` and `:91`.

**On citations.** Line citations were taken by reading each file directly and counting lines, at
`560e296`. The PRD's staged edits at lines 429 and 836 replace lines one for one, so no cited PRD line
number moves. **Every citation added or touched in revision 2 was re-read the same way, with no `sed`.**
That covers:

- `exporters/derive.py:749`;
- `site/index.html:273`, `:274-279`, `:289`, `:524` and `:830`;
- `board.config.json:13` and `:33`;
- `docs/backlog/specs/dispatch-board.md:270`;
- `local/tests/test_collector_equivalence.py:32`, `:67` and `:91`;
- `docs/backlog/pbi/PBI-027-collector-repo.md:65`;
- `docs/backlog/pbi/PBI-010-derived-status.md:7`, `:36-47`;
- `docs/backlog/specs/pbi-009-waiting-on-you.md:795`;
- `tests/page.test.mjs:1388`, `:1400-1404` and `:1418`;
- `exporters/board_config.py:130-132`.

The §2.6 platform-catalogue correction was checked against `git show 560e296:projects/platform-catalogue.json`,
where PBI-012 is `todo`.

### Round 2

Round 2 (2026-09-13): APPROVE-WITH-NOTES — every round-1 resolution and the fixed-time-formatter claim
were independently re-verified and upheld; the four new findings are all Low, and none would have
produced a wrong build — see `docs/backlog/reviews/PBI-010/spec-review-r2.md`.

| Finding | Sev | Disposition in revision 3 |
|---|---|---|
| N-1 | Low | **Applied.** §6.2's "not in the PBI list" example was wrong: platform-catalogue's PBI list runs PBI-000 to PBI-012 (`out/projectTabs/platform-catalogue.backlog.json`), so PBI-000 is in it, not an example of an absent id. The example is now platform-catalogue's `PBI-013`, one past the list's actual range. §2.6, §5.3 and §6.3, which already counted PBI-000 correctly, are unchanged |
| N-2 | Low | **Applied.** §7 now names the one allowed fixture edit: §7.4's Equivalence case adds PBI-005 to the shared `EQ_PROJECT_TABS`, and renames `PROJECTS` to `EQ_PROJECTS` where it feeds `EQ_RECORDS` and `overStore`. Both are harmless — the constant is used once, and the existing `seen` checks only test presence — and are now called out so a strict builder or reviewer does not refuse them. "No existing test case is changed" stays true: no case is edited, only the shared fixture two cases already read |
| N-3 | Low | **Applied.** §6.1 now states the evaluation order, first match wins: Cannot compare, then No evidence, then Not named by any run, then Agrees, then Runs ahead, then Hand-kept ahead. Checking Cannot compare first closes both ambiguities the note raised: an unrecognised hand-kept state with no derived item no longer reads as Not named, and two equal unrecognised states no longer read as Agrees |
| N-4 | Low | **Applied.** A note under the front matter records that `main` has moved to `4bbbad8` (PBI-014, #24 — `derive.py` +104, `index.html` +79, `page.test.mjs` +149) while every citation in this spec is grounded at `560e296`; the builder must re-ground before relying on a line number, e.g. `when()` is now `site/index.html:282` and `EQ_PROJECT_TABS` is `tests/page.test.mjs:1400` (both verified by direct read against `4bbbad8`). No citation in the body is rewritten, per the note's own instruction |

**Q-17's default, recorded as the round-2 gate asked.** Q-17 stays **OWNER** — it is an `allowed_areas`
grant that code cannot settle — but the gap is no longer left unowned. **Option (b) is the recorded
default:** the orchestrator pre-registers the follow-up at PBI-010's finalize, either as a local-tests
PBI raised through `pbi-intake`, or folded into **PBI-027** (`docs/backlog/pbi/PBI-027-collector-repo.md`, which already
files the equivalent gap for PBI-014 and has not yet built). **If the owner grants the one file,
`local/tests/test_collector_equivalence.py`, before the build**, option (a) replaces it: one added linked
scenario with a cr GO, a cr GO-WITH-CONDITIONS and a cr GO naming no PBI. §9's Q-17 row and §10 are
updated to match. PBI-010 does not close out with the AC-64 fixture gap merely noted and no follow-up on
the backlog.

**Owner rows after revision 3:**

- **Q-1:** unchanged — OWNER, non-blocking; operationally resolved by the 2026-09-13 link.
- **Q-2:** unchanged — OWNER, the `CLAUDE.md` grant.
- **Q-3:** unchanged — OWNER, blocking before the switch is flipped to `derived`, not blocking the build.
- **Q-17:** OWNER, with a recorded default — option (b), the pre-registered follow-up, unless the owner
  grants the one file before the build.

**On citations, revision 3.** Verified by direct read, no `sed`:

- `out/projectTabs/platform-catalogue.backlog.json` — the `pbis` list runs PBI-000 to PBI-012 (N-1);
- `site/index.html:282` (`when()`) and `tests/page.test.mjs:1400` (`EQ_PROJECT_TABS`), both on `main` at
  `4bbbad8` (N-4);
- `git log --oneline` on `main` confirms `4bbbad8` (PBI-014, #24) as the current head, four commits after
  `560e296`.
