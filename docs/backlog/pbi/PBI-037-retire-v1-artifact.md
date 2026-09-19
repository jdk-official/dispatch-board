---
id: PBI-037
title: "Retire the v1 artifact and its refresher: final store export, final status message, loop stopped, procedures marked retired (S-40)"
status: Done
change_class: standard
depends_on: []
allowed_areas: ["docs/backlog/evidence/**", "snapshot/**", "CLAUDE.md", "README.md"]
blocked_areas: ["site/**", "exporters/**", "local/**", "board.config.json"]
conflict_group: docs
conflict_risk: Low
requires_spec: false
requires_external_review: true
pr_required: true
merge_allowed_by_agent: true
---

# PBI-037 — Retire the v1 artifact and its refresher: final store export, final status message, loop stopped, procedures marked retired (S-40)

---

## Description

This PBI freezes the published claude.ai artifact and stops its refresher, at the owner's word "retire it now" (row 37). Every `meta/*` and `status/*` document is exported to `snapshot/`. One final owner-approved store write sets a retirement message and turns off every live flag. The refresher loop stops, and the Refresh and publish procedures are marked retired. The artifact is neither deleted nor republished. The freeze stays reversible until PBI-038 removes the push path. Decomposed from the approved solution spec at the plan gate on 2026-09-19 (track 10, G-11).

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 6, approved 2026-09-19)

**Areas and design notes from the parent spec:**

allowed `docs/backlog/evidence/**`, `snapshot/**`, `CLAUDE.md`, `README.md`, and one owner-approved store write. Blocked: `site/**`, `exporters/**`, `local/**`, `board.config.json`. There is no artifact publish and no deletion.

**Trigger T4, a same-day check** (spec, "Revision 6: trigger criteria"; evidence in `docs/backlog/evidence/<date>-t4-retire-artifact.md`). All of these must hold on the day, before any store write:

- **T4.1** PBI-007 is merged, and both tasks are installed and serving. The evidence quotes AC-68's demonstration of 2026-09-19 (`docs/backlog/pbi/PBI-007-logon-start.md`, Evidence) and that day's committed-pass lines in `out/local/logs/collector.log`. PBI-007 need not be Done.
- **T4.2** No feature the owner uses exists only on the artifact: the page suite's adapter deep-equal passes on `main`.
- **T4.3** The owner's acceptance of the loss is quoted verbatim: row 37's answer, "retire it now", given to a question that stated the loss. It is also this PBI's external-review go-ahead.

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, revision 6, "PBI-037, freezing the artifact and stopping the refresher"; rows 37, 38):

- [x] **AC-V1** The T4 evidence file exists and records T4.1 to T4.3 before any store write or loop change.
- [x] **AC-V2** Before the final write, every `meta/*` and `status/*` document in the store is exported to `snapshot/` and committed.
- [x] **AC-V3** The last refresher push is taken when no run in the export is `running`, linked or not. The orchestrator dispatches no agent between that push and the final write, so no run is frozen as `running`. Then one final write, approved by the owner, sets the `meta/status` message to "Retired <date>: the board now runs on this PC at http://127.0.0.1:8765", and sets `live: false` on `meta/status` and every `status/*` document.
- [x] **AC-V4** The refresher loop is stopped. `CLAUDE.md` and `README.md` mark the Refresh and publish procedures retired, keep their text until PBI-038, and state the revert: until PBI-038 merges, restarting `/loop 10m Refresh the dispatch board: …` restores the artifact. `CLAUDE.md` also says that no PBI republishes the artifact from now on, including PBI-010, which is in flight.
- [x] **AC-V5** The artifact is neither deleted nor republished, and its capabilities are unchanged.
- [x] **AC-V6** From the freeze on, nothing republishes the artifact, runs the refresher or writes its store: no `write_db` call and no hand edit of `meta/status` or `status/*`. That includes the paused platform-catalogue build's hand-written `title`, `message` and `metrics`. The only exception is the documented revert, which the owner asks for. `CLAUDE.md` and `README.md` state this rule, and that any such write restarts T4.4's window.
- [x] **AC-V7** The close-out includes one orchestrator step outside the repository. The orchestrator's session memory note for the dispatch board is updated to say that the artifact is frozen, that the refresher loop is not restarted when the frozen page shows "stale", that nothing is published to the artifact, and that the board lives at http://127.0.0.1:8765. This PBI does not change that note as a file.
- [x] Worker close-out: tier 1 plus demonstration (row 44). The diff holds no executable file, shown by its diff stat. The three configured suites are green on the head commit. The accounted code-review gate has passed.

---

## Evidence

**Closed out 2026-09-19.** Merged as `85654f8` (PR #42, squash; landing resolved squash (declared) / observed squash, one parent, level `record`).

- **AC-V1** — `docs/backlog/evidence/2026-09-19-t4-retire-artifact.md` records T4.1 to T4.3 (both tasks running, 258 committed collector passes that day, page adapter deep-equal passing on `daeb0b0`, the owner's "retire it now"), committed in `58c4752` before any store write.
- **AC-V2** — `snapshot/final-2026-09-19/` holds `meta/lastRefresh` v16, `meta/status` v55 and `status/dispatch-board` v103, exported after the last push and committed in `58c4752` before the final write.
- **AC-V3** — last push: 102 writes in 3 atomic, version-pinned batches, no run `running`; no agent dispatched before the final write. Final write, the owner's verbatim approval "Approve the final write": `meta/status` v56 (retirement message, `live` false) and `status/dispatch-board` v104 (`live` false).
- **AC-V4** — no refresher loop runs; `CLAUDE.md` ("The published page", "Refresh procedure") and `README.md` mark both retired, keep their text until PBI-038 and state the owner-only revert.
- **AC-V5** — only the two store updates above; no publish call, no deletion, capabilities untouched.
- **AC-V6** — the no-write rule, including the paused build's hand-written fields and the T4.4 restart, is stated in `CLAUDE.md` and `README.md`; the two store-cleanup open items are marked moot.
- **AC-V7** — the orchestrator's memory note for the dispatch board says the artifact is frozen, the loop is not restarted for "stale", nothing is published, and the board is at http://127.0.0.1:8765 (updated 2026-09-19, outside the repository).
- **Close-out** — tier 1 plus demonstration: the diff holds only `CLAUDE.md`, `README.md`, `docs/backlog/evidence/**` and `snapshot/**`. Canonical run bound to `13e23ce`: backend 412/0, page exit 0 (139 checks), local 430/0. Accounted `code-review-r1` (Sonnet) GO, 0 findings; the reviewer reproduced the three suites.

---

## Notes

**Authority.** Decomposed from the parent spec `docs/backlog/specs/dispatch-board.md`, revision 6. The owner approved it at the plan gate on 2026-09-19 with "Approve", answering the approval question that named commit `db14c0b` (spec blob `8fbdd3eba4a1042e2dfdbeb1689369eb015eb390`). That question said approving "freezes the published claude.ai page today (PBI-037)". The approval is recorded at `main` `e8f3f4e` (Plan-gate record). It accepted row 38's default: freeze now, remove the code later. These criteria are the spec's own until the PRD re-baseline (row 47).

**Batch approved and started 2026-09-19.** Asked "Put PBI-031 to PBI-038 on the BOARD as shown, and start PBI-037 (freeze the published artifact) now?", the owner answered, verbatim: "Approve batch, start 037".

**Promotion.** The spec makes the owner's approval of revision 6 this PBI's promotion (Metadata: "PBI-037 is the exception"; sequencing: "At this revision's approval: PBI-037 … is promoted and can start at once"). It is landed here as Proposed only because the owner reviews this decomposition batch before anything goes on the BOARD. It can move to Ready as soon as the batch is accepted. Its T4 evidence file is its own first act (AC-V1).

**What the owner loses** (accepted 2026-09-19, row 37): viewing the board away from this PC, a board held off this machine, and any replacement in this plan. See the spec, "What the owner loses at T4".

**Merge.** `merge_allowed_by_agent: true`, under the owner's standing merge authorisation of 2026-09-12 (`CLAUDE.md`, "Merge authority"), verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time." The final store write in AC-V3 still needs the owner's own approval.

**External review.** `requires_external_review: true`. The go-ahead is row 37's answer, "retire it now" (T4.3).

**Sequencing.** `docs`, Low: it collides with no code, so it can run beside PBI-010. PBI-038 depends on it.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| Trigger T4 (same day) | true | passed 2026-09-19 | `docs/backlog/evidence/2026-09-19-t4-retire-artifact.md` |
| External-review gate | true | passed 2026-09-19 | the owner: "retire it now" (row 37); "Approve batch, start 037"; "Approve the final write" |
| Code-review gate | true | passed 2026-09-19 | Accounted `code-review-r1` GO, 0 findings |
| No-self-merge gate | always | passed 2026-09-19 | PR #42 squash-merged `85654f8` under the owner's standing merge authorisation |
| BOARD-tidy gate | always | passed 2026-09-19 | Done write, ledger deregistered |