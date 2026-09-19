---
id: PBI-014
title: "Run detail (feature 8, FR-121)"
status: Done
change_class: standard
depends_on: [PBI-003, PBI-011]
allowed_areas: ["site/**", "tests/page.test.mjs", "exporters/**", "tests/test_*.py"]
blocked_areas: []
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-014 — Run detail (feature 8, FR-121)

---

## Description

Run detail (feature 8, FR-121). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `site/**`, `tests/page.test.mjs`, `exporters/**`, `tests/test_*.py`. It also touches `exporters`.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-121:

- [x] **AC-82** When the owner selects a code-reviewer run, the page shall show that run's verdict summary, findings, files touched and duration. *(FR-121; demonstration.)*
- [x] **NFR-22 visual confirmation, by a named actor** *(added 2026-09-13 from code-review finding CR-014-2)*. The regex-checkable half is automated — the page check "NFR-22: the run detail uses status tiles, colours only through tokens, and never --human" fails when a hex colour is injected into the page. The judgement half cannot be automated: before close-out **the owner** confirms the run-detail panel in **both themes** (dark on bare `:root`; light under `prefers-color-scheme: light` and `[data-theme="light"]`) against `CLAUDE.md`'s design rules and NFR-22 (`docs/prd/dispatch-board.md:570`). The owner may delegate this to a rendered-screenshot artefact under `docs/backlog/evidence/`, but that directory is outside this PBI's `allowed_areas`, so the artefact route is orchestrator close-out bookkeeping, not worker output.
- [x] Worker close-out: the three configured suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`, `python -m unittest discover -s local/tests`); code-review gate passed (`review-agents:code-reviewer` GO). *(Corrected 2026-09-13: the config has three suites.)*

---

## Evidence

**Close-out completed 2026-09-19.** (Stopped at step 3 on 2026-09-13 while two criteria waited on the owner; both were dispositioned by the owner on 2026-09-19 against the rendered-screenshot artefact.) Merged as `4bbbad8` (PR #24, squash). Suites on the merged head: `tests` **360**, `page.test.mjs` **121**, `local/tests` **304** — all OK.

- **Worker close-out — met.** The three configured suites are green on the head commit; the canonical run was bound to `123a61c` on a base confirmed equal to `origin/main`, with the commit following the run in the same step. The code-review gate passed: round 1 NO-GO (1 High, 2 Medium, 3 Low), fixed; round 2 (final) GO-WITH-CONDITIONS (3 Medium, 1 Low), every merge condition applied.
- **AC-82 — demonstrated, approved by the owner 2026-09-19.** Demonstration: `docs/backlog/evidence/PBI-014/` (README + four PNGs) — the Dispatch tab driven in headless Edge on the page at `47f8c13` via the local server, picking code-reviewer run `a7f2ff8c431f28b3c` (verdict summary, 5 findings, duration 11 min, files its findings name) and code-writer run `aed41112a65c82b5a` (files it edited, duration 9 min). The owner, verbatim: "ok, approved". Earlier history of this criterion: The page checks "AC-82: a picked code-reviewer run shows its verdict summary…" and "AC-82: a picked run names the files it edited", with the `derive` tests for `findings` and `files`, pin the behaviour. AC-82 is a *demonstration* criterion, and the orchestrator has not demonstrated it: it cannot drive clicks inside the artifact iframe, so ticking it on test evidence would claim a demonstration that did not happen. The page was republished and the store re-pushed with the new fields on 2026-09-13, so the panel is viewable. **What the demonstration will honestly show**, measured on real transcripts by the final reviewer: a code-reviewer run makes no edits (0 of 37), so its panel shows the files its *findings* name; and 65 of dispatch-board's 140 recorded edits were made in git worktrees outside `repoPath`, so those show by file name only. The criterion passes honestly on a review round with readable findings plus a builder run.
- **NFR-22 visual confirmation — confirmed by the owner (its named verifier) 2026-09-19**, via the rendered-screenshot route this criterion permits: the same four PNGs, dark (bare `:root`) and light (`prefers-color-scheme: light`), with `[data-theme="light"]` measured to resolve the same semantic tokens as the media query. The owner, verbatim: "ok, approved". Three observations recorded in the evidence README and accepted with it as not PBI-014 defects (the PBI-027 `…/` paths in local data; reviewer-authored `&gt;` entities; the web font's punctuation spacing, page-wide). The automated half passes: the page check "NFR-22: the run detail uses status tiles, colours only through tokens, and never --human" fails when a hex colour, a CSS literal or `--human` is injected into a scratch copy of the page. The judgement half — the panel in both themes against `CLAUDE.md`'s design rules — is the owner's.

**What the gates caught, which the suites alone would not have.** A requirement declared undeliverable ("files touched") that round 1 proved deliverable at source. A version-bump test, written by a fix run cut off by a usage limit, that would have passed with no bump. A page claim that worktree edits were "outside the project's repository". And a board/local divergence — `local/collector.py:436` omits the repository `exporters/export_sessions.py:286` passes — now follow-up **PBI-027**, on which **PBI-007 depends**.

**A defect in the orchestrator's merge step:** the pre-merge mergeable guard matched the lowercase JSON *key* `"mergeable"` case-insensitively instead of its value, and so passed on `UNKNOWN`. The merge was safe (base equal to `origin/main`; GitHub reports UNKNOWN right after creation) and landed cleanly, but the guard checked nothing; it is replaced by JSON parsing.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | false | pending | |
| Code-review gate | true | passed 2026-09-13 | Round 1 **NO-GO** (1 High, 2 Medium, 3 Low), fixed test-first; round 2 (final) **GO-WITH-CONDITIONS** (3 Medium, 1 Low), conditions applied (`change-report-r3.json`). `docs/backlog/reviews/PBI-014/findings-r1.json`, `findings.json`, `cell-report.json` |
| No-self-merge gate | always | passed 2026-09-13 | PR #24 squash-merged `4bbbad8` by the orchestrator under the owner's standing merge authorisation, conditions applied. Landing: resolved squash (declared) / observed squash, level `record`. |
| BOARD-tidy gate | always | passed 2026-09-19 | AC-82 and NFR-22 dispositioned by the owner ("ok, approved") against `docs/backlog/evidence/PBI-014/`; two-part Done write, ledger row deregistered, releasing the `page` group's High-risk slot. |
