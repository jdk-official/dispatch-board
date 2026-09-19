---
id: PBI-030
title: "Sessions link to a project automatically from the files they edit"
status: Proposed
change_class: standard
depends_on: []
allowed_areas: ["exporters/export_sessions.py", "exporters/board_config.py", "exporters/derive.py", "tests/test_export_sessions.py", "tests/test_derive.py", "local/collector.py", "local/tests/**", "docs/backlog/specs/pbi-030-*.md"]
blocked_areas: ["site/**", "exporters/refresh.py", "local/server.py"]
conflict_group: exporters
conflict_risk: Medium
requires_spec: true
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-030 — Sessions link to a project automatically from the files they edit

---

## Description

Today a session belongs to a project only when its id is listed in that project's `sessions` in `board.config.json` (PRD glossary, "Linked session"; `exporters/export_sessions.py` `settings()` builds `project_of` from those lists). Every new session lands in "Other sessions" until the owner copies its id into the config by hand.

This PBI links a session to a project when the session's own transcript shows it editing files inside that project's `repoPath` (or a worktree of it). The hand-kept `sessions` list stays, and wins: a session listed there keeps that project whatever it edited.

The spec (`requires_spec: true`) must settle, with the PRD requirements it amends:
- **The evidence.** Which tool calls count (Edit, Write, NotebookEdit; not Read, not Bash), how worktree paths map to a project (`git worktree list` from `repoPath`, or a path prefix), and what happens when one session edits two projects' files.
- **Stickiness.** Whether a session keeps its link once its editing ages out of the transcript window, and whether an auto-linked session is exempt from age pruning the way a listed one is (FR-185).
- **The fatal-missing-transcript rule.** FR-38 fails the run when a *listed* session's transcript is missing; it must not start failing for an auto-linked one.
- **Where the link is shown.** A session document's `project` already carries the id; the spec decides whether it also records *why* (`linkedBy: config | edits`).

---

## Acceptance criteria

- [ ] **L-1** When a session within the window edits (Edit or Write) a file under dispatch-board's `repoPath` and is listed in no project, the session exporter and the local collector both set its `project` to `dispatch-board`, and the project document's `sessions` includes it.
- [ ] **L-2** When a session edits files only under a worktree of a project's repository, it is linked to that project.
- [ ] **L-3** A session listed in a project's `sessions` keeps that project even when it edited another project's files.
- [ ] **L-4** A session that only read or searched a project's files (Read, Grep, Glob, Bash) is not linked.
- [ ] **L-5** An auto-linked session whose transcript has gone never fails the run (FR-38 still applies to listed sessions only).
- [ ] **L-6** Out of scope, checked: the page (`site/**`) is unchanged; "Other sessions" shrinks only because fewer sessions are unlinked.
- [ ] Worker close-out: the three configured suites green on the head commit; accounted code-review gate passed.

---

## Evidence

- (written at close-out)

---

## Notes

**Owner authority (verbatim, 2026-09-19):** "want the auto-linking". Landed by intake the same day. `merge_allowed_by_agent` is `true` under the owner's standing merge authorisation of 2026-09-12.

**Q-1 answered by the owner 2026-09-19** (asked whether an auto-linked session should stay with its project after it leaves the 7-day window), verbatim: "No, 7-day window (Recommended)". Auto-links are not sticky; to keep a session, list it.

**Sequencing.** PBI-010 (page group, High) also edits `exporters/**`. PBI-030's spec gate runs while PBI-010 builds; its build starts only once PBI-010 has merged, so the two never edit `derive.py` or `export_sessions.py` at once.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | pending | |
| External-review gate | false | n/a | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
