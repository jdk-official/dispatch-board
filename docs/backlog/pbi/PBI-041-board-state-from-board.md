---
id: PBI-041
title: "The board note and the pipeline's Board box come from the BOARD, not from hand-kept text"
status: In Progress
change_class: standard
depends_on: []
allowed_areas: ["exporters/derive.py", "exporters/export_board.py", "tests/test_derive.py", "tests/test_export_board.py", "site/index.html", "tests/page.test.mjs", "projects/**"]
blocked_areas: ["local/**", "exporters/export_sessions.py", "exporters/refresh.py"]
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-041 — The board note and the pipeline's Board box come from the BOARD, not from hand-kept text

---

## Description

Two things the owner reads go out of date between hand edits:
- **The Backlog tab's note** comes from `boardNote` in `projects/<id>.json`, which the building session writes by hand. On 2026-09-19 it was hours stale.
- **The Overview pipeline's "Board" box** says "Proposed column · 0 items until approved", hardcoded in `site/index.html`. It has never read any data.

The exporter reads the project's BOARD (`docs.board` in `board.config.json`; `docs/backlog/BOARD.md` for dispatch-board) and exports, per section (Proposed, Ready, In Progress, Done), the PBI ids and titles listed in its tables. The page then shows:
- **In the Board box:** the real counts, in plain words (for example "3 in progress · 12 proposed"). Nothing else changes in the pipeline.
- **On the Backlog tab:** one plain line in place of the hand-kept note: "In progress: PBI-031 Answers endpoint, …".
- **The hand-kept note:** if one exists, it is shown beneath that line only while it is non-empty. The owner can retire it by emptying it.

Keep it minimal: the owner found a previous panel "very complex". One line and one box, no new panel.

---

## Acceptance criteria

- [ ] **N-1** With a BOARD listing PBI-031 under In Progress and PBI-032 and PBI-033 under Proposed, the exported backlog tab carries those ids per section, and the page's Board box reads "1 in progress · 2 proposed".
- [ ] **N-2** The Backlog tab's first line lists the In Progress PBIs by id and title, from the BOARD.
- [ ] **N-3** A project whose `docs.board` is missing or unreadable exports as today (warning on stderr), and the Board box shows no counts rather than a wrong zero.
- [ ] **N-4** The hardcoded "0 items until approved" is gone; a page check fails if the Board box shows a count the data does not support.
- [ ] Worker close-out: the three configured suites green on the head commit; accounted code-review gate passed.

---

## Evidence

- (written at close-out)

---

## Notes

Landed by intake 2026-09-19. The owner asked, verbatim: "What do we need to change to ensure the board stays upto date?", after "I feel like we aren't updating the backlog with new PBIs. Or any of the associated views". It was also found that the pipeline's Board box is hardcoded. `merge_allowed_by_agent` is `true` under the owner's standing merge authorisation of 2026-09-12.

**Sequencing.** `page` group, High: it runs in the page slot, before PBI-020 because it fixes what the owner sees now.

**Every change to `exporters/` or `site/` needs the local tasks restarted** until PBI-040's self-restart lands.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| External-review gate | false | n/a | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
