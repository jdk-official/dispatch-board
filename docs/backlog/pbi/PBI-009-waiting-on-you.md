---
id: PBI-009
title: "'Waiting on you' panel: detectors for pending questions, idle-after-asking and permission refusals (feature 2, FR-106–FR-110)"
status: Done
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

- [x] **AC-75** When a session's last assistant turn asks the owner a question and no owner message follows it, the "Waiting on you" panel shall list that session. *(FR-106, FR-107.)*
- [x] **AC-76** When a transcript records an action refused by the permission check, the "Waiting on you" panel shall list that refusal with its session. *(FR-106, FR-109.)*
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

**Closed out 2026-09-19.** Merged as `25156c9` (PR #29, squash; landing resolved squash (declared) / observed squash, level `record`).

- **AC-75** — D1 (an unanswered structured question, listed at once) and D2 (a closing prose question left idle, shipped enabled per the owner) are pinned by `tests/test_derive.py` `Waiting` and the page checks "a question waiting on you"; the accounted reviewers judged both detectors correct against spec revision 3.
- **AC-76** — D3 reads only `toolDenialKind` and lists all three refusal kinds with their session (owner answers 1a/1b); pinned by the derive tests, and checked on real data by the round-2 reviewer: over the owner's 24 local transcripts, all 15 refusals survive until a message the owner actually typed (false owner-presence records fell from 10 to 0 after CR-009-1).
- **Worker close-out** — canonical run via `round_close run`, bound to `0ba49a2`: backend 396, local 413, page suite exit 0 (131 checks). Bounded review accounting, allowance 2, both used: `code-review-r1` GO-WITH-CONDITIONS (CR-009-1 Medium, disposition applied), `code-review-r2` GO with CR-009-1 resolved. Evidence validation PASS at every phase (`docs/backlog/reviews/PBI-009/`).
- **W-14 / NFR-22 visual confirmation — confirmed by the owner 2026-09-19**, verbatim: "W-14 OK". Rendered screenshots, both themes: `docs/backlog/evidence/PBI-009/` (the panel's items there are a disclosed fixture in a scratch database; nothing real was waiting at capture time).

**Follow-ups:** spec §4.1 gains the two owner-message exclusions; `CLAUDE.md` gains the `waiting` field, the known limits and the redaction note; a PBI adds `waiting` to the local record shapes; the marker exclusion depends on Claude Code's exact wording.

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
| Code-review gate | true | passed 2026-09-19 | `code-review-r1` GO-WITH-CONDITIONS (CR-009-1 applied), `code-review-r2` GO |
| No-self-merge gate | always | passed 2026-09-19 | PR #29 squash-merged `25156c9` under the owner's standing merge authorisation |
| BOARD-tidy gate | always | passed 2026-09-19 | W-14 approved by the owner ("W-14 OK"); Done write; ledger deregistered, freeing the page slot |
