---
id: PBI-013
title: "Usage limit forecast (feature 6, FR-117, FR-118)"
status: Done
change_class: standard
depends_on: [PBI-018]
allowed_areas: ["site/**", "tests/page.test.mjs"]
blocked_areas: []
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-013 — Usage limit forecast (feature 6, FR-117, FR-118)

---

## Description

Usage limit forecast (feature 6, FR-117, FR-118). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `site/**`, `tests/page.test.mjs` only. It reads the limit reset times the session docs already carry (`usage.limits[].resetsAt`).

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-117, FR-118:

- [x] **AC-80** When no usage-limit hit is recorded, the page shall show "no forecast: no limit hit recorded"; when at least one is recorded, the page shall show a time labelled as an estimate. *(FR-117, FR-118.)*
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

These were verified fresh at finalize on 2026-09-11, on merged `main` `602eab9` (PR #9's squash commit):
- **Suites:** `python -m unittest discover -s tests` 215 OK; `node tests/page.test.mjs` 68 checks passed (section 11 covers AC-80's two outcomes, the session filter, Other sessions and malformed data); `python -m unittest discover -s local/tests` 90 OK.
- **AC-80 against real data:** `site/index.html` from `602eab9` was run with the stub DOM from `tests/page.test.mjs` against the live store as read on 2026-09-11 (`docs/backlog/evidence/2026-09-11-page-checks/forecast-check.mjs`, run as `node forecast-check.mjs site/index.html <store dump folder>`), with 0 `console.error` calls:
  - platform-catalogue: "Next limit hit Sep 11, 12:36 AM · estimate from 3 limit hits · passed with no hit since" on the Overview and the Claude usage tab;
  - dispatch-board: "Sep 10, 11:56 PM · estimate from 1 limit hit · passed with no hit since";
  - Other sessions, where no hit is recorded: exactly "no forecast: no limit hit recorded".

  Times show in the viewer's local time.
- **Published:** the page was republished from `602eab9` to the same artifact URL on 2026-09-11.
- **Worker close-out:** the code-review gate passed with round 2 GO (`docs/backlog/reviews/PBI-013/findings.json`). PR #9 was squash-merged by the owner at 2026-09-11T16:13:06Z, and the observed landing is squash (level: record).

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

**Follow-ups logged from the Build cell (2026-09-11):**
- **Forecast method, a plan defect for the owner.** Spec ledger row 11 and PRD A-34 defer to "the PRD default as written", but the PRD writes no method.
  - **Implemented:** the mean of the gaps from resumption to each hit, where resumption is the later of the reset before the hit and the first hour with usage. The mean is added to the latest reset.
  - **When the latest hit's reset time is unrecorded:** the tile shows a duration after the reset rather than a clock time.
  - **What the owner's record should cover:** these choices, whether a usage-rate model (brief feature 6, "current rate of use") is wanted, and how a `seven_day` limit should weigh in.
  - **Where the record goes:** PRD A-34 / spec row 11, in the next PRD revision.
- **CR-PBI013-06 (Low), deferred with rationale.** `forecastIsPast()` at `site/index.html` (in `renderAll` and the minute timer) runs outside the per-tab try/catch. The only trigger found is a contrived store value (an hourly `main` that cannot become a number); the store is admin-written and the exporter writes integers. Fix it by returning false on any exception, and computing `Date.now()` once per render. PBI-002 (page fixes) is the natural home.
- **A non-list `usage.hourly`, or null entries in it,** still makes the existing `usageChart` throw (inside the tab guard). An `Array.isArray` and entry check would fix it; PBI-002.
- **When a forecast passes on an idle board,** the minute timer's one redraw resets scroll positions inside panels, the same as any store change.
- **CLAUDE.md does not describe the forecast tile,** its states or its method: the next docs chore.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | false | pending | |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-013/findings.json (round 2 GO; round 1 GO-WITH-CONDITIONS in findings-r1.json, all five conditions applied; CR-PBI013-06 Low deferred, see Notes) |
| No-self-merge gate | always | passed 2026-09-11 | PR [#9](https://github.com/jdk-official/dispatch-board/pull/9), opened 2026-09-11 from `pbi/PBI-013-usage-forecast` (commit `c54a119`, on main `d9de491`), pushed via `git_rail.py`; squash (declared). Canonical run bound to `c54a119`: 215 / 68 / 90, PASS. Squash-merged by the owner (jdk-official) at 2026-09-11T16:13:06Z as `602eab9`; observed landing squash (level: record) |
| BOARD-tidy gate | always | passed 2026-09-11 | done-log entry appended and BOARD row moved to Done with `board_tidy.py`; ledger row deregistered |
