---
id: PBI-001
title: "Exporter hardening: FR-80–FR-82, FR-84, carried-tab marker, config type checks, refuse an answers collection (FR-133)"
status: Done
change_class: standard
depends_on: [PBI-018]
allowed_areas: ["exporters/**", "tests/test_*.py", "CLAUDE.md"]
blocked_areas: ["site/**", "local/**"]
conflict_group: exporters
conflict_risk: Medium
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-001 — Exporter hardening: FR-80–FR-82, FR-84, carried-tab marker, config type checks, refuse an answers collection (FR-133)

---

## Description

Exporter hardening: FR-80–FR-82, FR-84, carried-tab marker, config type checks, refuse an answers collection (FR-133). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `exporters/**`, `tests/test_*.py`, `CLAUDE.md`; blocked `site/**`, `local/**`. It also adds the C-16 rule to `CLAUDE.md`: no agent writes answers or calls an answers endpoint.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-80, FR-81, FR-82, FR-84, FR-133:

- [x] **AC-57** When a carried-over row of kind `running` belongs to an agent that cannot be re-read, and the running window has elapsed since the row's `end` time, the session exporter shall export that row with kind `killed` and verdict `no result`. *(FR-80.)*
- [x] **AC-58** When one agent transcript holds a response whose `usage.output_tokens` is a string, the session exporter shall still export that session and every one of its runs. *(FR-81.)*
- [x] **AC-59** When `sessions.showFirstPrompt` is the string `"false"`, or `sessions.exclude` is a string rather than a list, the session exporter shall exit non-zero with an error naming that key. *(FR-82.)*
- [x] **AC-61** When a verifier run completes with a result stating `exercised`, the session exporter shall record verdict `exercised`. *(FR-84.)*
- [x] **AC-86** When the refresh script is given an export that includes an `answers` document, it shall exit non-zero, name the `answers` collection on stderr, and leave no pending plan. *(FR-133.)*
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

These were verified fresh at finalize on 2026-09-11, on merged `main` `d4023c6` (PR #10's squash commit). `python -m unittest discover -s tests` gave 267 OK; `node tests/page.test.mjs` 68 checks passed; `python -m unittest discover -s local/tests` 90 OK.
- **AC-57:** `Malformed.test_a_running_agent_that_cannot_be_reread_is_killed_once_the_window_has_passed` (and `..._stays_running_within_the_window`), plus the session-level case `test_a_running_row_in_a_session_that_cannot_be_parsed_is_killed_once_the_window_has_passed` and the `Carried` unit tests.
- **AC-58:** `Malformed.test_a_string_token_count_skips_only_that_response`: both runs are exported, requests = 3.
- **AC-59:** the `ConfigTypes` tests. `sessions.showFirstPrompt` `"false"` and a string `sessions.exclude` exit 2 with the key named on stderr, and nothing is written.
- **AC-61:** `Pipeline.test_verifier_that_exercised_its_checks` gives verdict `exercised` with kind `done`. A fallback is also recorded honestly: the `VerdictOf` fallback, JSON-outcome, case and negation tests, and the orchestrator's probe in `docs/backlog/reviews/PBI-001/conditions-check.md`.
- **AC-86:** the `Answers` tests and `Cli.test_an_answers_document_exits_non_zero_naming_the_collection`: exit 2, `answers` on stderr, nothing on stdout, no pending plan, and not lifted by `--allow-mass-delete`.
- **Real data:** `python exporters/refresh.py` ran the merged exporters (parser version 5, so a full re-parse) against the real transcripts and both projects on 2026-09-11. It exited 0 with no stderr warnings and planned 6 routine store writes, and no deletes.
- **Worker close-out:**
  - The code-review gate passed: round 2 GO-WITH-CONDITIONS (`docs/backlog/reviews/PBI-001/findings.json`), with the conditions applied (`change-report-r3.json`) and checked (`conditions-check.md`).
  - PR #10 was squash-merged by the owner at 2026-09-11T16:30:15Z, and the observed landing is squash (level: record).
- **Not delivered, although the title names it:** the "carried-tab marker", which is PRD FR-190 / AC-125 (`carriedSince` on a kept tab document). It is not among this PBI's listed criteria, which were decomposed before PRD revision 3 added it, and it was not built. It is carried to a follow-up; see Notes.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

**Follow-up logged 2026-09-11** from the PBI-017 code review, round 2 (`docs/backlog/reviews/PBI-017/code-review-r2.md`):
- **The problem:** `records()` in `exporters/export_sessions.py` catches only `ValueError`. A deeply nested JSON line in a transcript raises `RecursionError`. The per-session and per-agent `except Exception` handlers contain it today, but not every caller was traced (for example the one near line 299).
- **To do:** catch `RecursionError` in `records()`, as `export_catalogue.py` now does, and add a test with a nested transcript line. This is in scope as FR-81-style hardening.

**Follow-up logged 2026-09-11** from the PBI-022 code review (`docs/backlog/reviews/PBI-022/findings.json`, follow-up 2; PRD revision 3, row A-45):
- **The gap:** FR-137 and AC-90 have no named test. `tests/test_export_sessions.py` has none for a session that is linked to a project but falls outside the session window.
- **To do:** add that test here, since this PBI's areas include `exporters/**` and `tests/test_*.py`. Then close A-45 in the PRD.

**Follow-up logged 2026-09-11** from the PBI-021 code review (`docs/backlog/reviews/PBI-021/findings.json`, follow-up 5):
- **The gap:** `CLAUDE.md` says `snapshot/` holds the store "as of the move (2026-09-10)". Since PBI-021, `snapshot/tabs/` holds the 2026-09-10 and 2026-09-11 copies of the retired documents.
- **To do:** correct that sentence. `CLAUDE.md` is in this PBI's areas.

**Follow-ups logged 2026-09-11** from the PBI-018 code review (`docs/backlog/reviews/PBI-018/findings.json`; verdict GO):
- **CR-018-01 (LOW):**
  - **The problem:** `later_items()` in `exporters/export_board.py` recognises only `- ` bullets at column 0. `* `, `+ `, numbered or indented bullets are dropped, or merged into the previous idea.
  - **To do:** recognise any Markdown list marker, with up to 3 leading spaces, and treat deeper-indented lines as nested items. Or keep `- ` as the only style and warn on stderr about other markers. Add a test for each case.
  - **Why it was deferred:** the real spec uses only `- ` bullets, `CLAUDE.md` documents that limit, and nothing crashes.
- **Optional:** build a bullet that has words before its bold span from the text around the span, so the title is not shown twice.
- **Optional:** decide whether nested sub-bullets under a Later idea should render as a list.

**Follow-ups logged 2026-09-11** from the PBI-023 code review (`docs/backlog/reviews/PBI-023/findings.json`):
- **The published `remotes` field:** `git_tab` publishes raw `git remote -v` lines as `remotes` (`exporters/export_board.py`, about line 275). A remote like `https://user:TOKEN@github.com/...` would publish its token.
  - **To do:** strip userinfo from `remotes` before export, and add a test. Today's origin has no credentials in its URL. This is an existing gap, not introduced by PBI-023.
- **Base repository:** `gh` picks the base repository by its own rules, not necessarily `origin`.
  - **To do:** consider passing `--repo`, derived from the origin URL, to the pull-request list.
- **Draft PRs:** `gh` reports them as `OPEN`, so they show as "awaiting your merge".
  - **To do:** consider adding `isDraft` to `--json` and leaving drafts out of Needs attention (a page change: coordinate with PBI-002).
- **Open PRs outside the 20-row window:** an open PR left untouched while 20 others are updated drops out of Needs attention.
  - **To do:** consider a separate `gh pr list --state open` call for the attention list.

**Follow-ups logged 2026-09-11** from the PBI-003 spec gate (`docs/backlog/specs/pbi-003-records-schema.md` revision 3; `docs/backlog/reviews/PBI-003/spec-review-r2.md`, N-5):
- **Manual rows:** at config load, validate each `runs.manual` row in `board.config.json`:
  - `lane` and `kind` must be among the run enums in PBI-003's `SHAPES`;
  - `id`, `label`, `verdict` and `from` must be strings (spec-gate round 3, R3-7).

  Copy the enum values into `board_config`; don't import `local/records`, which would reverse ADR-0001's dependency direction. Today a typo or a non-string is accepted by v1 but would be rejected by the local app's `to_row`.
- **Reserved path:** reserve `meta/lastRefresh` in `board_config.STATUS_DOC`, so no project's `statusDoc` can take the last-refresh record's store path (FR-102/FR-103).

**Follow-up logged 2026-09-11** by the orchestrator (found while shipping PBI-023):
- **The gap:** the Backlog tab lists work items only from the approved spec's "PBI list (proposed)" table. A PBI added later, such as PBI-023 (entered directly as a standard change), never appears there, even with a `buildState` entry.
- **To do:** have `export_board` also read PBI files from the configured `pbi_dir`, or `docs.board`, and list any PBI that isn't in the spec's table, marked as added after the plan.
- **Not done in PBI-001** (optional 9): it needs `pbi_dir` config, PBI frontmatter parsing and a `site/**` change, so it is carried to PBI-002.

**Follow-ups logged 2026-09-11 from PBI-001's own Build cell** (`docs/backlog/reviews/PBI-001/findings-r1.json`, `findings-r2.json`, `conditions-check.md`):
- **Verifier negations:** the list of words that negate a verifier's outcome covers not, never, no, cannot, without, n't, unable to, rather than and instead of. Widen it only if real verifier transcripts show other phrasings. Reviewer: non-blocking.
- **Windows device names:** device names with superscript digits (COM¹…LPT³), `CONIN$` and `CONOUT$` are not refused as `runs.manual` ids. None is a plausible hand-written id.
- **Later-list nesting rule (plan defect):** the rule "up to 3 leading spaces starts a new idea" differs from CommonMark's parent-content-column nesting. Update the spec rule in the next spec revision; the code needs no change.
- **Minor, optional:**
  - a git tab exported before this change is kept byte-for-byte if its repo becomes unreadable;
  - `github_repo()` duplicates `github_origin()`;
  - the tier-1 negation window.
- **After merge:** close A-45, and mark FR-80, FR-81, FR-82, FR-84 and FR-133 met in `docs/prd/dispatch-board.md`, in the next PRD revision.
- **Carried-tab marker (found at finalize):** FR-190 / AC-125 was not built. When `export_board` keeps a tab's last export (FR-153), it should write `carriedSince`. It is an exporter change, so it can't go in PBI-002 (which blocks `exporters/**`). It becomes a small follow-up PBI in the `exporters` group, to land before PBI-002's stale-tab callout (FR-191 / AC-126) and before PBI-004's extraction starts, so the two don't collide in `export_board.py`.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | false | pending | |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-001/findings.json (round 2 GO-WITH-CONDITIONS; round 1 NO-GO in findings-r1.json, all four fixed). The round-2 conditions CR-PBI001-05 and -06, and the Low -07, were applied (change-report-r3.json) and checked by the orchestrator (conditions-check.md), as the reviewer allowed |
| No-self-merge gate | always | passed 2026-09-11 | Squash-merged by the owner (jdk-official) at 2026-09-11T16:30:15Z as `d4023c6`; observed landing squash (level: record). PR [#10](https://github.com/jdk-official/dispatch-board/pull/10), opened 2026-09-11 from `pbi/PBI-001-exporter-hardening` (commit `9aeff32`, on main `d9de491`), pushed via `git_rail.py`; squash (declared). Canonical run bound to `9aeff32`: 267 / 57 / 90, PASS. Waiting for the owner's merge, then `pbi-lifecycle finalize PBI-001` |
| BOARD-tidy gate | always | passed 2026-09-11 | done-log entry appended and BOARD row moved to Done with `board_tidy.py`; ledger row deregistered |
