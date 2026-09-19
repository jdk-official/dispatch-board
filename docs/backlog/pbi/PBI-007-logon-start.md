---
id: PBI-007
title: "Log-on start through Task Scheduler and the on-PC deployment end to end (FR-90, FR-91, NFR-17, NFR-18, NFR-21)"
status: In Progress
change_class: standard
depends_on: [PBI-019, PBI-005, PBI-006, PBI-027]
allowed_areas: ["local/deploy/**", "local/tests/**", "README.md", "CLAUDE.md"]
blocked_areas: ["site/**", "exporters/**"]
conflict_group: local-app
conflict_risk: Low
requires_spec: false
requires_external_review: true
pr_required: true
merge_allowed_by_agent: true
---

# PBI-007 — Log-on start through Task Scheduler and the on-PC deployment end to end (FR-90, FR-91, NFR-17, NFR-18, NFR-21)

---

## Description

Log-on start through Task Scheduler and the on-PC deployment end to end (FR-90, FR-91, NFR-17, NFR-18, NFR-21). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `local/deploy/**`, `local/tests/**`, `README.md`, `CLAUDE.md`; blocked `site/**`, `exporters/**`. It registers a Task Scheduler task, a persistent change to the owner's system, so the owner approves it or runs the documented script. It owns the end-to-end checks NFR-17, AC-70, NFR-18 and AC-68.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-90, FR-91, NFR-17, NFR-18, NFR-21:

- [ ] **AC-65** When the owner logs on to Windows with no Claude Code session open, the page at the local server's address shall show the sessions active in the last 7 days within 10 minutes. *(FR-90, FR-91, NFR-17, NFR-21; demonstration.)*
- [x] **AC-68** When a finish is appended to a running agent's transcript while the page served by the local server is open, the page shall show the run's new kind within 10 minutes without a reload. *(FR-94, NFR-18; demonstration.)*
- [x] **AC-70** When the collector and local-server source is searched, it shall contain no invocation of the `claude` command and no request to an Anthropic API host. *(NFR-17; inspection.)*
- [x] **AC-72** When the collector on the PC records a new run in the Unraid deployment, the page served from the Unraid server shall show that run within 10 minutes. *(FR-89, NFR-18; demonstration.)*
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

**Merged 2026-09-19; close-out waits on the owner.** Merged as `7c6bcb6` (PR #28, squash; landing resolved squash (declared) / observed squash, level `record`).

- **AC-70 — met (inspection).** `local/tests/test_deploy_inspection.py` parses every module under `local/` (and the exporter modules the collector imports) for `claude` invocations, network clients and Anthropic hosts; the accounted reviewer re-searched `local/` and `exporters/` independently and found none.
- **Worker close-out — met.** Canonical run via `round_close run`, bound to `3a63f57`: backend 360, local 413 (includes the two-process end-to-end test), page suite exit 0 (121 checks); accounted dispatch `code-review-r1` GO, 0 findings; evidence validation PASS at pre-review, gate-complete and pre-push. Two earlier rounds (NO-GO; GO-WITH-CONDITIONS, applied) predate the accounting and are logged as events.
- **AC-65 — pending the owner.** Needs `python local/deploy/tasks.py install` (a persistent change to the owner's machine, which the orchestrator does not make) and a log-on. The reviewer judged the code would satisfy it and the end-to-end test exercises the mechanism.
- **AC-68 — demonstrated 2026-09-19** on the installed deployment (both tasks registered by the owner and started with `tasks.py start`). The page at `http://127.0.0.1:8765` was loaded once at 11:34:40Z and never reloaded (the browser's navigation count stayed 1). Agent run `a660a214a9e5e02eb` ("Correction review PBI-009 r2") was launched at 11:36Z and finished about 4 minutes later; the open page then showed it as run 154 of 154, outcome Approved / GO, with the header reading "data as of 12:42 PM" local — well within 10 minutes, with no reload. The collector log shows the passes that carried it.
- **AC-72 — deferred to PBI-016 — accepted by the owner 2026-09-19**, verbatim: "defer AC-72". It cannot be met until the Unraid deployment (PBI-016) is built; it is carried there.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_external_review: true`: the owner must explicitly approve ("approve" / "proceed" / "go ahead") before implementation begins.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | true | pending | |
| Code-review gate | true | passed 2026-09-19 | Accounted dispatch `code-review-r1` GO, 0 findings; two pre-accounting rounds logged as events |
| No-self-merge gate | always | passed 2026-09-19 | PR #28 squash-merged `7c6bcb6` under the owner's standing merge authorisation |
| BOARD-tidy gate | always | **waiting on the owner** | AC-65 needs a log-on demonstration (tasks installed 2026-09-19; AC-68 demonstrated); AC-72 deferred to PBI-016 by the owner. Ledger row stays registered (local-app, Low: blocks nothing else) |
