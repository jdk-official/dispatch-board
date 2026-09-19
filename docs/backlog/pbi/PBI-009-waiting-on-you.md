---
id: PBI-009
title: "'Waiting on you' panel: detectors for pending questions, idle-after-asking and permission refusals (feature 2, FR-106–FR-110)"
status: In Progress
change_class: standard
depends_on: [PBI-004]
allowed_areas: ["exporters/**", "tests/test_*.py", "site/**", "tests/page.test.mjs"]
blocked_areas: []
conflict_group: page
conflict_risk: High
requires_spec: true
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-009 — "Waiting on you" panel: detectors for pending questions, idle-after-asking and permission refusals (feature 2, FR-106–FR-110)

---

## Description

"Waiting on you" panel: detectors for pending questions, idle-after-asking and permission refusals (feature 2, FR-106–FR-110). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `exporters/**`, `tests/test_*.py`, `site/**`, `tests/page.test.mjs`. Its spec confirms the transcript record types against real transcripts before any detector is built (row 10). It also touches `exporters`.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-106, FR-107, FR-108, FR-109, FR-110:

- [ ] **AC-75** When a session's last assistant turn asks the owner a question and no owner message follows it, the "Waiting on you" panel shall list that session. *(FR-106, FR-107.)*
- [ ] **AC-76** When a transcript records an action refused by the permission check, the "Waiting on you" panel shall list that refusal with its session. *(FR-106, FR-109.)*
- [ ] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

- (written at close-out)

---

## Notes

**Owner answers to the spec's §9 rows, 2026-09-19** (asked in chat; the owner's selections, verbatim):
- Row 1a (auto-mode-blocked refusals): "List them (Recommended)" — listed, tagged `Refused`, cleared by a later owner message or the 48-hour bound.
- Row 1b (user-rejected refusals): "List them (Recommended)" — listed the same way.
- Row 2 (prose detector D2): "Ship enabled (Recommended)" — enabled, tagged `Inferred`, gated on idleness and the 48-hour bound (§7.6).
These settle every row marked "Needs OWNER before building"; the build proceeds on the spec's revision 3 exactly.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_spec: true`: refine a per-PBI spec from the parent spec and have it independently reviewed before any code is written.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | **passed 2026-09-12** | `docs/backlog/specs/pbi-009-waiting-on-you.md` revision 3. Round 1 **CHANGES-REQUIRED** (2 High, 4 Medium, 3 Low) — all nine applied; round 2 **APPROVE-WITH-NOTES** (N-1..N-4, all applied in revision 3). Reviews: `docs/backlog/reviews/PBI-009/spec-review-r1.md`, `-r2.md`. **The gate reversed the design's story on measured data:** the "structural" detector D1 (unanswered `AskUserQuestion`) fires on **0 of 15** real transcripts (36 asks, all answered), while the prose detector D2 fires on 4/15 with **0 false positives, recall ≈4/7** — so D2 ships enabled with a 48-hour age bound, since disabling it would leave the panel permanently empty. The denial split is `automode-blocked` 8/11 vs `user-rejected` 1/11, reversing revision 1's premise. Zero new store documents: `waiting` is an optional field on `sessions/<id>` (one writer), and `PARSER_VERSION` 6→7 is confirmed necessary. **OWNER rows 1a (`automode-blocked` on the panel?), 1b (`user-rejected`?) and 2 (D2 enabled — recommended yes) remain open.** The `--human` misuse at `site/index.html:777`/`:784` is an NFR-10 matter with no live home (PBI-002 closed without it) and goes to a new intake item. |
| External-review gate | false | pending | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
| BOARD-tidy gate | always | pending | |
