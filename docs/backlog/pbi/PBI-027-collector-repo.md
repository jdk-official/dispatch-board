---
id: PBI-027
title: "Local collector publishes a run's files relative to the repository, so the local app matches the board"
status: In Progress
change_class: standard
depends_on: [PBI-014]
allowed_areas: ["local/collector*", "local/tests/**", "local/records*", "local/records.shapes.json"]
blocked_areas: ["site/**", "exporters/**", "local/server*", "local/schema*", "local/db*"]
conflict_group: local-app
conflict_risk: Medium
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-027 — Local collector publishes run files relative to the repository

---

## Description

A banked follow-up, landed by intake on 2026-09-13. PBI-014's final code review (finding **CR-014-7**, `docs/backlog/reviews/PBI-014/findings.json`) made it a condition of PBI-014's merge.

PBI-014 adds a `files` field to each run document: the files the run edited, relative to the project's `repoPath`. `derive.run_doc(r, seq, project, repo=None)` publishes a path relative to `repo` when one is passed, and as `…/<file name>` (folders withheld) when none is. The two callers disagree:

```
exporters/export_sessions.py:286   derive.run_doc(r, i, pid, repo_of.get(pid))      # board: passes the repo
local/collector.py:436             derive.run_doc(r, i, st['project_of'].get(sid))   # local: passes none
```

So for the same run the board publishes `site/index.html` while the local database stores `…/index.html`. That breaks the parent spec's rule that the board and the local app derive **identical documents** from one shared implementation. `local/tests` stays green only because its fixtures contain no edit tool calls at all, so the equivalence coverage is vacuous for this field. PBI-014 could not fix it: `local/**` is outside its areas.

**Why this must land before deployment:** the divergence withholds only — the local side shows less, never more — and nobody observes it until the local app runs. PBI-007 (the log-on deployment) therefore now **depends on this item**, so the deployment cannot ship with the mismatch.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved).

---

## Acceptance criteria

- [ ] **L-1 The collector passes the repository.** `local/collector.py`'s call to `derive.run_doc` passes the run's project `repoPath`, exactly as `exporters/export_sessions.py` does, so a run's `files` in the local database equals the board's for the same run.
- [ ] **L-2 Equivalence covers `files`, and bites.** A local test drives a fixture containing an edit tool call **inside** the repository and one **outside** it, and asserts the collector's run document `files` equals the exporter's for the same input. It fails before L-1's fix is applied.
- [ ] **L-3 The shapes name the new run fields.** `local/records.py`'s `SHAPES['run']` (and its mirror `local/records.shapes.json`) name the optional `files` and `findings` fields PBI-014 publishes; the conformance check still passes; no other record kind's shape changes.
- [ ] **L-4 Nothing is weakened.** Every existing local test passes unchanged, and new cases are added rather than substituted.
- [ ] **Out of scope:** the page, the exporters, the server, the schema, and the worktree limitation (edits made in a git worktree sit outside `repoPath` on the board too — that is PBI-014's to describe, not this item's to fix).
- [ ] Worker close-out: the three configured suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`, `python -m unittest discover -s local/tests`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

- (written at close-out)

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

**Owner authority:** `merge_allowed_by_agent` is `true` under the owner's standing merge authorisation of 2026-09-12, verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time." Promotion from Proposed to Ready remains a curation step.

**Dependency recorded on PBI-007, 2026-09-13.** PBI-014's final reviewer made this enforceable as a condition: PBI-007's `depends_on` now includes PBI-027, so the deployment cannot land before the local app matches the board. Adding the dependency only tightens PBI-007's gate; it widens no scope.

**Planning gap noted by the reviewer:** the PRD's AC-64 assigns the local fixture to whichever feature PBI lands second, yet PBI-014's areas excluded `local/**`, so the feature PBI could not satisfy it. Not the builder's fault; worth a note for the next decomposition.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI; the parent spec's shared-derivation rule covers the design |
| External-review gate | false | n/a | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
| BOARD-tidy gate | always | pending | |
