---
id: PBI-033
title: "Answer audit: transcript tool calls that could have sent an answer, and the answers they may have made marked on the Assumptions tab"
status: Proposed
change_class: standard
depends_on: [PBI-032, PBI-030, PBI-034]
allowed_areas: ["exporters/derive.py", "exporters/export_sessions.py", "tests/test_*.py", "local/records*", "local/collector*", "local/tests/**", "site/**", "tests/page.test.mjs", "CLAUDE.md"]
blocked_areas: ["local/server*", "local/answers*", "local/schema*"]
conflict_group: page
conflict_risk: High
requires_spec: true
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-033 — Answer audit: transcript tool calls that could have sent an answer, and the answers they may have made marked on the Assumptions tab

---

## Description

The shared derivation records every transcript tool call that could have sent an answer, as `answerSuspects` on the session document. On the local adapter, the Assumptions tab marks each answer given within 5 minutes after such a call and lists the pairings in an "Answer audit" panel. The audit is a record for the owner to read, not a gate: it never decides whether an answer counts (row 32). Decomposed from the approved solution spec at the plan gate on 2026-09-19 (track 7, G-8).

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 6, approved 2026-09-19)

**Areas and design notes from the parent spec:**

allowed `exporters/derive.py`, `exporters/export_sessions.py`, `tests/test_*.py`, `local/records*` (with `local/records.shapes.json`; the session's `answerSuspects`), `local/collector*` (only if carrying the field needs it), `local/tests/**`, `site/**`, `tests/page.test.mjs`, `CLAUDE.md`. Blocked: `local/server*`, `local/answers*`, `local/schema*`. It also touches `exporters`, `local-app` and `docs`. Tier 4 (record shapes).

**Decision record:** [ADR-0002](../../adr/0002-board-answers-count-as-the-owners.md). The tripwire is an audit mark, not a gate.

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, revision 6, "PBI-033, answer audit"; rows 26, 32):

- [ ] **AC-G1** The shared derivation records, as `answerSuspects` `[{at, tool, detail}]` on the session document (detail redacted and cut to 300 characters), every tool call in a main or subagent transcript that could have **sent** an answer:
  - a Bash or PowerShell call whose input names `/api/answers` together with a sending command (`curl`, `wget`, `Invoke-WebRequest`, `Invoke-RestMethod`, `urllib`, `requests`, `fetch`);
  - a WebFetch call naming `/api/answers`;
  - a browser-automation call (`mcp__*Browser*__*`, `mcp__claude-in-chrome__*`, the preview tools) whose input names the local server's origin, or that acts on a tab whose last-seen URL is on that origin; and a `javascript_*` call naming `/api/answers`;
  - an Artifact or ArtifactData write naming an `answers/` path.

  Calls that only **mention** the endpoint (`grep`, `rg`, `Select-String`, `git log -S`, Read, Edit, Write) are not recorded. The exporters and the collector produce identical `answerSuspects`, with the equivalence fixture extended to prove it.
- [ ] **AC-G2** The PBI's spec confirms the tool-call shapes against real transcripts before the detector is built, as PBI-009 did. That includes browser calls on `127.0.0.1:8765` (session `7e0c4f3c`) and the revision-6 planning and review transcripts. The spec also measures how many harmless calls the rule marks.
- [ ] **AC-G3** On the local adapter, the Assumptions tab marks each answer given within 5 minutes after a suspect call as "Possibly given by an agent: <session>, <tool>", in the `--changes` tone, and lists every such pairing in an "Answer audit" panel. Nobody clears the marks, and they change neither whether an answer counts nor how it is transcribed. They last as long as their session document: an unlinked session's is pruned after 7 days (FR-185), and its marks go with it. The store adapter shows no audit.
- [ ] **AC-G4** The rendering meets NFR-22 and renders audit data through `esc()` only. `tests/page.test.mjs` covers a marked answer, an unmarked one, the panel, and the store adapter's absence of both.
- [ ] **AC-G5** `CLAUDE.md` states what the audit cannot see. That is an agent that avoids the recorded shapes (a URL built at run time, a script file written first, editing a transcript or the board database, a session under `sessions.exclude`, a stopped collector), a script injected into the page, and a browser tab the tool call never identifies. The marks show what a non-evading agent did, never that nothing happened.
- [ ] Worker close-out: tier 4 (record shapes; row 44). The canonical run of the three configured suites is green on the head commit, with `records.shapes.json` regenerated. The accounted code-review gate has passed.

---

## Evidence

- (written at close-out)

---

## Notes

**Authority.** Decomposed from the parent spec `docs/backlog/specs/dispatch-board.md`, revision 6. The owner approved it at the plan gate on 2026-09-19 with "Approve", answering the approval question that named commit `db14c0b` (spec blob `8fbdd3eba4a1042e2dfdbeb1689369eb015eb390`). The approval is recorded at `main` `e8f3f4e` (Plan-gate record). These criteria are the spec's own until the PRD re-baseline (row 47).

**Merge.** `merge_allowed_by_agent: true`. It is an audit that decides nothing, so it follows the owner's standing merge authorisation of 2026-09-12 (`CLAUDE.md`, "Merge authority"), verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time."

**Sequencing.** It is off the critical path. It waits behind PBI-030, which edits the same exporter files, rather than rebasing a tier-4 change onto it. It also waits behind PBI-034, because both change `local/records*` and regenerate `local/records.shapes.json`, and their groups differ. Once PBI-030 has merged, auto-linked sessions are read too.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | pending | per-PBI spec, with AC-G2's measurement on real transcripts |
| External-review gate | false | n/a | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
| BOARD-tidy gate | always | pending | |
