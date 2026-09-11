---
id: PBI-021
title: "Store leftovers clean-up: export the six unused documents to snapshot/, then delete them with the owner's explicit approval"
status: Done
change_class: standard
depends_on: []
allowed_areas: ["snapshot/**"]
blocked_areas: []
conflict_group: docs
conflict_risk: Low
requires_spec: false
requires_external_review: true
pr_required: true
merge_allowed_by_agent: false
---

# PBI-021 — Store leftovers clean-up: export the six unused documents to snapshot/, then delete them with the owner's explicit approval

---

## Description

Store leftovers clean-up: export the six unused documents to snapshot/, then delete them with the owner's explicit approval. Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `snapshot/**` and the six store deletes named in AC-S1, only after AC-S1 and AC-S2 hold.

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, row 16):

- [x] **AC-S1** Before any delete, the published artifact shall be read and confirmed to be the project-first version, and `tabs/usage`, `tabs/spec`, `tabs/assumptions`, `tabs/decisions`, `tabs/backlog` and `tabs/git` shall be exported to `snapshot/tabs/` and committed.
- [x] **AC-S2** The owner's approval of the named six-document delete batch shall be recorded verbatim in the PBI's evidence before the batch runs.
- [x] **AC-S3** After the batch, the store shall hold none of the six documents, and the published page shall still render every project's tabs.
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

- **AC-S1:** checked again on 2026-09-11, before the delete.
  - The published artifact was read, and it is the project-first version: it has the project picker and reads `projectTabs`.
  - The store's six `tabs/*` documents were read with `read_db`, and each was identical, as parsed JSON, to its committed copy in `snapshot/tabs/` (PR #2, `fd7b926`).
- **AC-S2:** the owner's approval of the delete batch, verbatim, recorded before the batch ran: "approve deleting tabs/usage, tabs/spec, tabs/assumptions, tabs/decisions, tabs/backlog and tabs/git". It was given by jdk-official in the build session on 2026-09-11.
- **The delete batch** ran on 2026-09-11 as one atomic `write_db` batch of six deletes (`tabs/usage`, `tabs/spec`, `tabs/assumptions`, `tabs/decisions`, `tabs/backlog`, `tabs/git`), and it committed.
- **AC-S3:**
  - **Store:** after the batch, `read_db list tabs` returned "No documents matched in collection "tabs"".
  - **Page code:** the published page subscribes only to `sessions`, `projects`, `runs`, `projectTabs`, `catalogue/index` and the status documents (`site/index.html:1040-1051`). The script read back from the artifact is identical to `site/index.html` on `main` `7fd96cb`.
  - **Live page:** after the delete, the page rendered with live data: dispatch-board's Assumptions tab in Chrome, and its Decisions tab in the Browser pane.
  - **Every tab:** the published page's script was then run against the whole live store as read after the delete (projects, projectTabs, sessions, 109 runs, the status documents and `catalogue/index`), with the stub DOM from `tests/page.test.mjs`. All 9 tabs rendered with content for both platform-catalogue and dispatch-board: no "not exported" state and 0 `console.error` calls.
  - **Why the Chrome check was partial:** the Chrome window was hidden, so screenshots timed out, and the Browser pane could not click into the scaled artifact frame. That is why the full tab-by-tab check used the harness.
- **Worker close-out:** verified fresh at finalize on 2026-09-11, on `main` `7fd96cb`, which contains PBI-021's squash commit `fd7b926`:
  - `python -m unittest discover -s tests`: 215 OK;
  - `node tests/page.test.mjs`: 57 checks passed;
  - `python -m unittest discover -s local/tests`: 90 OK.

  The code-review gate passed: `docs/backlog/reviews/PBI-021/findings.json` GO, with no findings. PR #2 was squash-merged by the owner at 2026-09-11T13:40:50Z, and the observed landing is squash (level: record).

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_external_review: true`: the owner must explicitly approve ("approve" / "proceed" / "go ahead") before implementation begins.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | true | passed 2026-09-11 | The owner's explicit approval, verbatim: "approve PBI-021" (in the build session, after the orchestrator explained that the gate needs "approve" / "proceed" / "go ahead", and that the six-document delete needs a separate verbatim approval under AC-S2). This covers starting implementation only; it does not approve the delete batch. |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-021/findings.json (GO, no findings) |
| No-self-merge gate | always | passed 2026-09-11 | PR [#2](https://github.com/jdk-official/dispatch-board/pull/2), opened 2026-09-11 from `pbi/PBI-021-store-cleanup` (commit `c9cc674`), pushed via `git_rail.py`; squash (declared). The first push attempt was refused by the rail, because the worker's `findings.json` was malformed JSON (a path lost its backslash escaping). It was rewritten and validated, then pushed. The review verdict (GO) was unchanged. Squash-merged by the owner (jdk-official) at 2026-09-11T13:40:50Z as `fd7b926`; observed landing squash (level: record). |
| BOARD-tidy gate | always | passed 2026-09-11 | done-log entry appended and BOARD row moved to Done with `board_tidy.py`; ledger row deregistered |
