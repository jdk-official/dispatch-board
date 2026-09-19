---
id: PBI-039
title: "The Backlog tab lists every PBI, not only the plan's"
status: Done
change_class: standard
depends_on: []
allowed_areas: ["exporters/derive.py", "exporters/export_board.py", "tests/test_derive.py", "tests/test_export_board.py", "site/index.html", "tests/page.test.mjs"]
blocked_areas: ["local/**", "exporters/export_sessions.py", "exporters/refresh.py"]
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-039 — The Backlog tab lists every PBI, not only the plan's

---

## Description

The Backlog tab's work items come only from the spec's `### PBI list (proposed)` table (`exporters/derive.py`, the `# --- backlog` block). A PBI that enters through intake after the plan gate (PBI-023 to PBI-030 here) has a file under `docs/backlog/pbi/` and a BOARD row, but never appears on the board. The owner noticed on 2026-09-19 that PBI-030 "doesn't exist" on the dashboard.

The exporter also reads the project's PBI files (`<repoPath>/docs/backlog/pbi/PBI-*.md`, frontmatter `id`, `title`, `depends_on`, `conflict_group`, `conflict_risk`, `requires_spec`) and appends every PBI the spec's table does not name, in id order, marked as not in the plan. A file whose `status:` is `Later` is left out: the Later group already shows it. The spec table stays first and authoritative for the PBIs it names. Build state is looked up exactly as for plan PBIs.

---

## Acceptance criteria

- [x] **B-1** With a PBI file `PBI-030-…md` that the spec table does not list, the exported backlog tab carries a PBI-030 item with the file's title, dependencies, conflict group and risk, and a field marking it as added after the plan.
- [x] **B-2** A PBI the spec table lists is exported once, from the table, even when its file also exists; the table's order is kept and added items follow in id order.
- [x] **B-3** A PBI file with `status: Later` is not exported as a work item; a file with unreadable frontmatter is skipped with a warning on stderr, never a failure.
- [x] **B-4** A project without a `docs/backlog/pbi/` folder exports exactly what it does today (platform-catalogue's tab is unchanged byte for byte in a test fixture).
- [x] **B-5** The page shows added items in the backlog list and the Overview's backlog cells, counted in the PBI totals, with a small "after plan" tag; a page check proves it.
- [x] Worker close-out: the three configured suites green on the head commit; accounted code-review gate passed.

---

## Evidence

**Closed out 2026-09-19.** Merged as `c58dfd2` (PR #50, squash; landing resolved squash (declared) / observed squash, level `record`).

- **B-1 to B-5** — each met, with its proving tests listed in `docs/backlog/reviews/PBI-039/change-r1.json` and `change-r2.json`. The reviewer ran the exporter on the real repos: dispatch-board's Backlog goes from 20 to 38 items, with PBI-023 to PBI-040 tagged "after plan", and platform-catalogue's is byte-identical (13 items, no PBI files).
- **Close-out** — canonical run bound to `7d35846`: backend 498/0, page exit 0 (142 checks), local 439/0. Accounted review: round 1 GO with 2 Lows (CR-039-1 BOM, CR-039-2 dependency cycle), both applied in round 2; round 2 GO, 0 findings.

---

## Notes

Landed by intake 2026-09-19 after the owner reported, verbatim: "And PBI30 doesn't exist" (and "It says not started on the dashboard", about PBI-020, which is correct: PBI-020 has not started). `merge_allowed_by_agent` is `true` under the owner's standing merge authorisation of 2026-09-12.

**Sequencing.** `page` group, High: it edits `exporters/derive.py` and `site/index.html` like PBI-010 and PBI-020, so it runs after PBI-010 in the page slot. It is small and fixes what the owner sees, so it goes before PBI-020.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-19 | Accounted r1 GO (2 Lows applied), r2 GO |
| No-self-merge gate | always | passed 2026-09-19 | PR #50 squash-merged `c58dfd2` under the owner's standing merge authorisation |
| BOARD-tidy gate | always | passed 2026-09-19 | Done write, ledger deregistered |