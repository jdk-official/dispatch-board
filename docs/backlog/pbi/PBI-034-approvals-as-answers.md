---
id: PBI-034
title: "Approvals as answers: `planApproval` bound to git's blob id of the committed spec, and `conditionsAccepted` bound to one review run, with server checks and `verify` support (S-31)"
status: Proposed
change_class: standard
depends_on: [PBI-031]
allowed_areas: ["local/server*", "local/records*", "local/answers*", "local/tests/**", "CLAUDE.md"]
blocked_areas: ["site/**", "exporters/**", "local/collector*"]
conflict_group: local-app
conflict_risk: Medium
requires_spec: true
requires_external_review: true
pr_required: true
merge_allowed_by_agent: false
---

# PBI-034 — Approvals as answers: `planApproval` bound to git's blob id of the committed spec, and `conditionsAccepted` bound to one review run, with server checks and `verify` support (S-31)

---

## Description

Two more answer types on PBI-031's endpoint. `planApproval` is bound to git's own blob id of the committed spec the owner saw. `conditionsAccepted` is bound to one GO-WITH-CONDITIONS review run. The server checks each binding against git or the snapshot. `local/answers.py verify` checks each transcription, and `CLAUDE.md` gains the procedure by which a board approval reaches the Plan-gate record. A board plan approval passes the plan gate by itself (row 34). Decomposed from the approved solution spec at the plan gate on 2026-09-19 (track 8, G-9).

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 6, approved 2026-09-19)

**Areas and design notes from the parent spec:**

allowed `local/server*`, `local/records*`, `local/answers*`, `local/tests/**` (including the reviewed git launches in `test_deploy_inspection.py`), `CLAUDE.md`. Blocked: `site/**`, `exporters/**`, `local/collector*`. It also touches `docs`. A security path through `security_paths`.

**Decision record:** [ADR-0002](../../adr/0002-board-answers-count-as-the-owners.md). A board plan approval passes the plan gate by itself.

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, revision 6, "PBI-034, approvals as answers"; rows 33, 34, 50):

- [ ] **AC-P1** Two more answer types, with the common fields of AC-A1 and the checks of AC-A3:
  - **`planApproval`** carries `specPath`, `specRevision`, `decision` (`approve` or `changes`) and `specBlob` (40 lowercase hex characters, `^[0-9a-f]{40}$` in the record shape), taken from the spec tab record the page rendered (AC-Q1).
    - `specBlob` is git's own blob id of the committed spec, `git rev-parse HEAD:<specPath>`. It is offered only while the spec is committed: `git ls-files --error-unmatch -- <specPath>` succeeds (tracked, exact case), and `git --no-optional-locks status --porcelain -- <specPath>` prints nothing.
    - The server resolves the spec's path from `board.config.json` (the project's `repoPath` plus `docs.spec`) and applies the network-path guard to it. It runs the same commands in that repository, plus `git cat-file -p <blob>` for the committed text's `revision:` and `status:`.
    - Every git call, on every side, has a timeout and `no_window_flags()`, and checks its exit code. A non-zero exit or a timeout leaves `specBlob` absent and `specCommitted` false, and the server refuses.
    - The server refuses the POST when HEAD's blob differs from the posted `specBlob`, when the file is untracked or not clean, when the committed text's `revision:` differs from the posted revision, or when its `status:` is not `draft`.
    - Tests cover a CRLF working copy of an LF-committed spec (`core.autocrlf = true`), which gives the same id on the page, on the server and in `verify`. They also cover a wrong-case `docs.spec` over a dirty file, an untracked spec and an ignored spec: none of the three offers *Approve*, and the server refuses each of them.
    - The server's and `local/answers.py`'s git launches are added to the reviewed list in `local/tests/test_deploy_inspection.py`.
  - **`conditionsAccepted`** carries `pbiId` and `runId`. The run must exist in the snapshot as a code-reviewer run of the posted project, with a GO-WITH-CONDITIONS verdict that names the PBI.
- [ ] **AC-P2** For each cited `planApproval`, `verify` checks, in the project's repository with read-only git commands:
  1. the approved text was committed at `specPath`: `git log --find-object=<specBlob> -- <specPath>` lists a commit;
  2. that text's `revision:` (from `git show <specBlob>`) equals `specRevision`;
  3. at the transcription commit (the earliest commit that `git log --reverse -S 'answer:<id>' --format=%H -- <specPath>` lists), `git show <commit>:<specPath>` equals `git show <specBlob>` once both are normalised. Normalising removes only the frontmatter lines `status:` and `approved_revision:` and the `## Plan-gate record` section. An uncommitted transcription fails with "commit the transcription first".

  Later commits do not fail `verify`; it prints, as information, how many lines outside the Plan-gate record have changed since the transcription commit. For each cited `conditionsAccepted`, `verify` confirms that the run exists.
- [ ] **AC-P3** `CLAUDE.md` says how a board approval reaches the Plan-gate record:
  - **Pickup.** The planner ends its gate turn with the gate pending and does not wait on chat. `python local/answers.py list --project <id>` runs at the start of each orchestrator session and on any loop that session runs. Only the latest `planApproval` for the spec's current `specBlob` that no later answer supersedes counts. With `approve` it is transcribed; with `changes` the spec returns to the planner with the owner's note. The transcribed answer id and note are the runbook's "exact human approval message".
  - **What an approval accepts.** A `planApproval` with `approve` accepts the chosen default of every row still ASSUMED in the approved text that has no answer of its own. The transcription lists those rows as confirmed by that approval.
  - **Commits, in order.** Assumption answers are transcribed into the ledger before the approved text is committed, or after the transcription commit, never with it. The transcription commit holds only the answer id, the owner's note, `status:` and `approved_revision:`. `verify`'s output goes in the next commit, which touches only the Plan-gate record. The status banner, a revision-history line, G-6's rewording and the row move come after that.
  - **Squash merges.** The commit holding the approved text is in the branch's history before the transcription is committed, and the two are never squashed together. Recording the approval is its own PR, holding the transcription commit and `verify`'s output commit. The banner, the revision-history line, G-6's rewording, the row move and the decomposition follow in a later PR. Tests squash a draft with its transcription, and a transcription with a banner edit, and show `verify` naming the cause each time. The binding reads `HEAD` of `repoPath`, whatever branch that checkout is on, so `verify` runs on that branch.
  - **Honouring.** A `planApproval` or `conditionsAccepted` is honoured once transcribed with a clean `verify`. A board plan approval passes the plan gate by itself; there is no chat step.
  - **Revision 6 itself** is approved in chat, since the board path does not exist until PBI-034 and PBI-035 ship.
- [ ] Worker close-out: tier 4 (record shapes; row 44). The canonical run of the three configured suites is green on the head commit, with `records.shapes.json` regenerated. The accounted code-review gate has passed.

---

## Evidence

- (written at close-out)

---

## Notes

**Authority.** Decomposed from the parent spec `docs/backlog/specs/dispatch-board.md`, revision 6. The owner approved it at the plan gate on 2026-09-19 with "Approve", answering the approval question that named commit `db14c0b` (spec blob `8fbdd3eba4a1042e2dfdbeb1689369eb015eb390`). The approval is recorded at `main` `e8f3f4e` (Plan-gate record). It accepted row 50's default (git's blob id on every side; the check made at the transcription commit), which is high impact. The owner answered row 34 "Board approval alone". These criteria are the spec's own until the PRD re-baseline (row 47).

**Merge.** `merge_allowed_by_agent: false`. The spec reserves this merge for the owner, because this PBI decides what a board approval binds to (rows 34, 50; Metadata).

**External review.** `requires_external_review: true`: it changes how approvals reach the workflow. The owner must explicitly approve ("approve" / "proceed" / "go ahead") before implementation begins.

**Security path.** `local/server*` and `local/answers*` are in `security_paths` once PBI-031's promotion chore has merged (row 49).

**Sequencing.** It runs after PBI-031, and can run in parallel with PBI-032, since they share no file. PBI-033 and PBI-035 wait for it.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | pending | per-PBI spec |
| External-review gate | true | pending | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | the owner merges |
| BOARD-tidy gate | always | pending | |
