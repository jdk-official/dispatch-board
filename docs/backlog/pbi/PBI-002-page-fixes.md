---
id: PBI-002
title: "Page fixes: FR-83 live-state tile, stale-tab callout, token relabel, design-rule deviations, blank-load investigation (FR-85)"
status: Done
change_class: standard
depends_on: [PBI-001]
allowed_areas: ["site/**", "tests/page.test.mjs"]
blocked_areas: ["exporters/**", "local/**"]
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-002 — Page fixes: FR-83 live-state tile, stale-tab callout, token relabel, design-rule deviations, blank-load investigation (FR-85)

---

## Description

Page fixes: FR-83 live-state tile, stale-tab callout, token relabel, design-rule deviations, blank-load investigation (FR-85). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `site/**`, `tests/page.test.mjs`; blocked `exporters/**`, `local/**`.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-83, FR-85:

- [x] **AC-60** When a non-build session's running window elapses with no store change, the page shall show "session idle" in the Overview's "Running now" tile within 60 s of the header showing `Idle`. *(FR-83.)*
- [x] **AC-62** When the published page is opened in Chrome 20 times in a row, each time in a fresh tab, the page shall render its app bar and Overview panel on every load without a reload. *(FR-85; the load count was chosen by the author of this document, A-13.)*
- [x] **AC-126** When a shown project tab carries `carriedSince`, the page shall show a warning on that tab stating that time. *(FR-191; the "stale-tab callout" in this PBI's title. Added 2026-09-11 before the build started: PRD revision 3 added it after decomposition. The exporter half, FR-190 / AC-125, is PBI-024; the page is tested against a fake store, so it doesn't wait for PBI-024.)*
- [x] **Row 13 design fixes:** paths and branch names move to the sans face (IBM Plex Mono stays only for ids and commit hashes); the brand dot stops using `--human`; the header status dot pulses only while an agent runs. Each is pinned by a page check.
- [x] **Token relabel (spec row 1):** Dispatch's `subagent_tokens` figure is labelled "reported tokens" wherever it is shown.
- [x] Worker close-out: the three configured suites are green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`, `python -m unittest discover -s local/tests`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

Re-checked fresh at finalize on 2026-09-11, on merged `main` at `049f27e` (this PBI's squash merge, PR #12), with `node tests/page.test.mjs` passing all 89 checks.
- **AC-60:** the two "running window" page checks (`tests/page.test.mjs` block around lines 933–966). "Running now" shows "session idle" on the same minute tick that the header turns `Idle`, including a render that straddles the end of the window.
- **AC-62: accepted by the owner, check kept active.** The page was republished to the live artifact on 2026-09-11 after the merge. The 20-load check could not be completed at finalize:
  - Claude in Chrome connected only after the owner signed in, and it was running in Microsoft Edge, not Chrome.
  - Loads 1, 3, 4 and 5 drew the header and a full panel within 5 s. Load 2 showed an empty page area at 5 s; whether it would have drawn later is unknown, because the next load replaced it.
  - An earlier empty frame, after a click, drew fully later without a reload.
  - Edge would not capture background tabs, and later screenshots timed out (the window stopped drawing), so the check stopped at 5 loads, not 20.
  - The page opened on the saved Assumptions tab, not Overview.
  - Disposition: accepted by the owner on 2026-09-11, verbatim: "PBI-002's 20-load check: accept but keep the test active".
  - **The check stays active:** it is re-run whenever a visible Chrome or Edge window is available, with two screenshots per load (5 s and 12 s). A load that is still blank at 12 s reopens FR-85 as a defect.
- **AC-126:** page block 13 (lines 996–1023). Each shown project tab carrying `carriedSince` warns in the `--changes` callout, stating the time, escaped; a tab without it shows no warning.
- **Row 13 design fixes:** page block 14 (lines 1026–1050). The brand dot does not use `--human`; the pulse is keyed to `.status.run`, never to `.on`; paths and branch names use the sans face.
- **Token relabel:** lines 1104–1111. The Overview tile, both run tables, the Dispatch tile and the swimlane caption all say "reported tokens".
- **Close-out:** suites 274 / 89 / 90 passing on `049f27e`. The worker's canonical run was bound to `d10aa68`: 267 / 89 / 90, PASS. Code review round 2 GO (`docs/backlog/reviews/PBI-002/findings.json`).

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

**Follow-up logged 2026-09-11** from the PBI-017 code review, round 2 (`docs/backlog/reviews/PBI-017/code-review-r2.md`):
- **The problem:** if `catalogue/index` arrives before sessions and runs, the Agent catalogue tab briefly shows 0 uses and "never used" for every entry. It clears on the next snapshot.
- **To do:** add a runs-loaded flag, and show the tab's usage columns as pending until sessions and runs have loaded.

**Follow-ups logged 2026-09-11** from the PBI-017 code review, round 3 (`docs/backlog/reviews/PBI-017/code-review-r3.md`), both in `tests/page.test.mjs`:
- **CR-PBI017-R3-01:**
  - **The problem:** block 7's `expectErrors()` wraps every fire, so an error from any tab counts as expected.
  - **To do:**
    1. Fire projects, sessions, runs and projectTabs outside it, and wrap only the `catalogue/index` fire.
    2. Assert exactly one error, "Board: the catalogue could not be drawn".
    3. Check the Overview panel shows no error state.
    4. Re-run the reviewer's probe C: an Overview that throws only when `catalogue.entries` includes `null` must fail the suite.
- **CR-PBI017-R3-02:**
  - **The problem:** a check that fails before `ok()` runs doesn't print the page's recorded error, and the reported file name is hardcoded.
  - **To do:**
    1. Print the recorded page errors to stderr on a non-zero exit.
    2. Use the loaded path (`PAGE_HTML` or `site/index.html`) as the vm filename and in the tab-button message.

**Follow-up logged 2026-09-11** from the PBI-021 code review (`docs/backlog/reviews/PBI-021/findings.json`, follow-up 4; optional):
- **The gap:** nothing in `tests/page.test.mjs` stops the page from subscribing to a retired `tabs/*` document again.
- **To do:** add a guard that the fake store's subscriptions never receive a `c:tabs` or `d:tabs/` key.

**Follow-up logged 2026-09-11** from the PBI-023 fix round (code-writer report, `docs/backlog/reviews/PBI-023/change-report-r2.json`):
- **The gap:** other label lookups in `site/index.html` read plain objects by a data key, such as `stateLabel[x.state] || x.state` on the Backlog tab. They don't crash, because `esc()` stringifies the result, but an inherited name such as `constructor` would show function text.
- **To do:** guard them with `Object.hasOwn`, or use `Map`s, as PBI-017 and PBI-023 did, and add a page check.

**Follow-ups logged 2026-09-11** from the PBI-013 Build cell (`docs/backlog/reviews/PBI-013/findings-r2.json`, `change-report-r2.json`):
- **CR-PBI013-06 (Low):** `forecastIsPast()`, in `renderAll` and the minute timer, runs outside the per-tab try/catch. Make it return false on any exception, and compute `Date.now()` once per render for both the tiles and the check.
- **Malformed `usage.hourly`:** a non-list `usage.hourly`, or null entries in it, makes `usageChart` throw (`hours.map`). Add an `Array.isArray` guard and an entry check, with a page check.

**Not in this PBI:** listing PBIs added after the plan (PBI-001's optional 9). It needs `exporters/**`, which this PBI blocks, so it stays a follow-up for an exporter PBI.

**Owner authority for starting:** the standing instruction of 2026-09-11, verbatim: "Start from the beginning. I want you to use the agents and keep building as per their instructions. Don't ask me what to build next".

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | false | pending | |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-002/findings.json (round 2 GO; round 1 GO-WITH-CONDITIONS in findings-r1.json, both Lows applied) |
| No-self-merge gate | always | passed 2026-09-11 | PR [#12](https://github.com/jdk-official/dispatch-board/pull/12) from `pbi/PBI-002-page-fixes` (commit `d10aa68`), squash-merged by the owner at 2026-09-11T17:45:06Z as `049f27e`. resolved_method squash (declared) / observed_method squash; level record |
| BOARD-tidy gate | always | passed 2026-09-11 | finalize: done-log entry and BOARD Done row written; close_check not run (`[closeout]` policy unset, so off). AC-62 accepted by the owner, with its live check kept active |
