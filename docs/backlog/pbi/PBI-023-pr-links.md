---
id: PBI-023
title: "Pull requests on the board: the GitHub tab lists each project's pull requests as links, and Needs attention flags the ones awaiting the owner's merge"
status: Done
change_class: standard
depends_on: [PBI-017]
allowed_areas: ["exporters/export_board.py", "tests/test_export_board.py", "site/**", "tests/page.test.mjs", "CLAUDE.md", "README.md"]
blocked_areas: ["local/**", "exporters/refresh.py"]
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: false
---

# PBI-023 — Pull requests on the board

---

## Description

The owner asked on 2026-09-11 to get to pull requests from the dashboard: "could you also update the artifact with this so I can access it?". This came up when PBI-017's pull request (#1) was opened.

Today the GitHub tab records only the repository's remotes. A PR link can appear only as plain text in the Backlog note, because the page renders code spans and bold but no links.

This PBI entered directly as a `standard` change (SPEC §Change classes). It does not go through the planner front.

**Depends on PBI-017**, because it builds on that change's page code: the per-tab render isolation and the page-test error rule.

---

## Acceptance criteria

- [x] **AC-P1** For a project whose `origin` remote is on `github.com`, the board exporter shall add a `pulls` list to that project's `git` tab document.
  - **Contents:** the 20 most recently updated pull requests, in any state. Each carries `number`, `title`, `state` (`OPEN` / `MERGED` / `CLOSED`), `url`, `branch` (the head ref) and `updatedAt`.
  - **Source:** `gh pr list --state all --limit 20 --json …`, run in the project's `repoPath` with a timeout of at most 15 s.
- [x] **AC-P2** When `gh` is missing, exits non-zero, times out or prints malformed JSON, the exporter shall do three things:
  - print a warning on stderr;
  - leave `pulls` out;
  - export the rest of the `git` tab as before.

  It shall never fail the refresh. A project without a GitHub remote gets no `pulls` and no warning.
- [x] **AC-P3** The GitHub tab shall show a "Pull requests" panel.
  - **Each row:** the number, the title, a state tag (open / merged / closed, using the existing semantic tag colours), the branch in mono and the updated time.
  - **Links:** the number and title link to the PR's URL, opening in a new tab with `rel="noopener noreferrer"`. Only URLs beginning `https://github.com/` are rendered as links; any other URL is shown as escaped text.
  - **No data:** without `pulls`, the panel says pull requests are not available, rather than showing an empty table.
- [x] **AC-P4** The Overview's "Needs attention" list shall show each open pull request as "PR #n awaiting your merge", with the `--human` tone (a merge is an owner decision) and a link to the PR. It shall not show merged or closed pull requests.
- [x] **AC-P5** Everything in the new panel and the attention item shall go through `esc()`. Titles are never passed through `md()`.
- [x] **AC-P6** Tests:
  - **Exporter:** with an injected command runner, never the real `gh`. Cover success, `gh` missing, a non-zero exit, a timeout, malformed JSON and a non-GitHub remote.
  - **Page test:** the panel, the attention item, a hostile title escaped, a `javascript:` URL not linked, and the no-`pulls` state.
  - Both suites shall pass.
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

Each criterion was verified fresh at finalize on 2026-09-11, on merged `main` `7fd96cb`, which contains PBI-023's squash commit `547b635`: `python -m unittest discover -s tests` ran 215 tests, OK; `node tests/page.test.mjs` passed all 57 checks.
- **AC-P1:** the `PullRequests` tests pass, and they assert the exact `gh` argv, including `--search sort:updated-desc`. The post-merge refresh published `pulls` for dispatch-board with 7 PRs (#1 to #7), from the real `gh`.
- **AC-P2:** the failure-mode tests pass (`gh` missing, a non-zero exit, a timeout, malformed JSON, a non-GitHub origin), each exiting 0. Platform-catalogue, which has no GitHub remote, gets no `pulls`.
- **AC-P3:** the page suite's section 10 checks pass. In the Browser pane, with the real data, the GitHub tab listed the PRs with github.com links (`target=_blank`, `rel=noopener noreferrer`), and the Repository box read "Pull requests: 1 open".
- **AC-P4:** the Browser-pane check showed "PR #5 awaiting your merge" in `--human`, with a link. The page checks confirm merged and closed PRs are excluded.
- **AC-P5:** the escaping checks pass, including a hostile title and inherited-key states. Lookalike hosts render as text, and a mutation check proves the guard is covered.
- **AC-P6:** 10 exporter tests use an injected `gh` runner (the real one is refused), and there are 8 page checks. Both suites pass.
- **Worker close-out:**
  - both suites pass on `7fd96cb`;
  - the code-review gate passed: `docs/backlog/reviews/PBI-023/findings.json` GO-WITH-CONDITIONS, with all three conditions applied in `e17006b`;
  - PR #6 was squash-merged by the owner at 2026-09-11T15:03:35Z; the observed landing is squash (level: record);
  - the page was republished and the `pulls` data pushed on 2026-09-11.

---

## Notes

- **Build process:** per owner decision D-9 and the owner's 2026-09-11 instruction to build continuously through the backlog-delivery workflow. That means `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.
- **Privacy:** PR titles are published to the board, like session titles. Only the owner views it (PRD D-12).
- **Open question, default chosen, low impact:** if the artifact's sandbox refuses to open a new tab, the link still shows its URL, which the owner can copy. The worker checks this in the real browser at close-out.
- **Scope:** `exporters/refresh.py` is blocked. The `git` tab document is already managed, so the refresh planner needs no change.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-11 | docs/backlog/reviews/PBI-023/findings.json (GO-WITH-CONDITIONS; CR-PBI023-01..03 applied in e17006b) |
| No-self-merge gate | always | passed 2026-09-11 | PR [#6](https://github.com/jdk-official/dispatch-board/pull/6), opened 2026-09-11 from `pbi/PBI-023-pr-links` (commit `e17006b`), pushed via `git_rail.py`; squash (declared). Squash-merged by the owner (jdk-official) at 2026-09-11T15:03:35Z as `547b635`; observed landing squash (level: record) |
| BOARD-tidy gate | always | passed 2026-09-11 | done-log entry appended and BOARD row moved to Done with `board_tidy.py`; ledger row deregistered |
