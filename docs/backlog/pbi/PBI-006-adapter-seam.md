---
id: PBI-006
title: "Page data-adapter seam: store adapter and local API adapter (FR-97–FR-99)"
status: Done
change_class: standard
depends_on: [PBI-003, PBI-005]
allowed_areas: ["site/**", "tests/page.test.mjs"]
blocked_areas: ["exporters/**", "local/**"]
conflict_group: page
conflict_risk: High
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-006 — Page data-adapter seam: store adapter and local API adapter (FR-97–FR-99)

---

## Description

Page data-adapter seam: store adapter and local API adapter (FR-97–FR-99). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `site/**`, `tests/page.test.mjs`; blocked `exporters/**`, `local/**`.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-97, FR-98, FR-99:

- [x] **AC-73** When the page is loaded from the local server, it shall request the data snapshot from the local server; when it is loaded as the artifact, it shall open store subscriptions. *(FR-98, FR-99.)*
- [x] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO). *(The config has three suites; all three are quoted in Evidence.)*

---

## Evidence

Verified fresh at finalize on merged main `10e6659` (PR #21, squash), 2026-09-12. Suites on that commit: `tests` **334**, `page.test.mjs` **111**, `local/tests` **265** — all OK, 0 skipped. The page suite grew 99 → 111 across two review rounds.

- **AC-73, the local half** — served locally, the page fetches `/api/snapshot` and opens `/api/events?since=<version>`, and `Object.keys(subs)` is empty: pinned by the page check `AC-73, the local half`.
- **AC-73, the artifact half** — with no marker, the eight store subscriptions open, and `env()` installs throwing `fetch`/`EventSource` so any HTTP reach fails the run: pinned by `AC-73, the artifact half`. A mutant routed down the local path fails rather than passes, so this is measured, not assumed.
- **FR-97, one interface / same board** — all ten panels, both pickers, and `statusText` / `crumb` / `asOf` / `foot` deep-equal between the adapters, pinned by `FR-97: the store adapter and the local API adapter render the same board`. Reversing the local comparator kills it.
- **FR-98/FR-99, detection** — the marker decides even with `window.claude` present; a marker naming no snapshot URL, missing its events URL, or carrying a non-same-origin URL falls back to the store adapter.
- **Worker close-out** — the three configured suites green on the head commit; code-review gate **GO** at round 2.

**The design decision this PBI owned.** The parent spec's row Q-11 left the detection *signal* open. It is the `window.__DISPATCH_LOCAL__` marker rather than the absence of `window.claude`, because an artifact published without its `db` capability also lacks `window.claude` and must still render the store's out-of-reach board instead of silently reaching for a local server that is not there.

**The two halves of the local-first system were exercised together for the first time.** The builder started the real `local/server.py` over a real SQLite database and drove the page's inline script with its actual `/api/snapshot`; the round-2 reviewer repeated it headlessly and confirmed PBI-005's spec-gate finding S-4 holds *across the seam* — `reset` carries `id: <version>`, change events carry ids, and the server takes the larger of `since`/`Last-Event-ID`, so the reconnect loop that finding warned about cannot occur. That had been an argued guarantee until now.

**Round 1's Medium was about evidence, not code.** The FR-97 equivalence check compared rendered `innerHTML` across all ten panels and genuinely bit — but the fixture left five panels empty on both sides, so the PBI's strongest claim rested partly on comparing emptiness to emptiness. Replaying the round-1 fixture confirms six of ten panels came up empty. The fixture now carries a spec tab, an assumptions row awaiting a human, a decisions tab with `carriedSince`, a backlog in all four states plus a Later idea, a findings tab with open and resolved entries, and a git tab with an OPEN and a MERGED pull request, and the check asserts `emptyPanels()` is `[]` on both sides before the deep-equal.

**The five Lows, all applied:** a 200 carrying a non-snapshot body now takes the honest degrade path instead of silently drawing an empty board (a genuinely empty `records` map still draws an ordinary empty board — a different case, kept different); a marker missing its events URL no longer opens `undefined?since=N`; both marker URLs must be same-origin; one change event causes one render pass rather than eight; and the write-only `version` was removed.

**Adversarial verification at round 2.** 19 hostile URLs against the new same-origin check — refused include the userinfo trick, `https://127.0.0.1:8765.evil.test/` (a prefix lookalike that defeats a naive `startsWith`), all three backslash-to-another-host forms, other-scheme, other-port, `file:`, `about:`, `vbscript:`, `data:`, `javascript:`, ipv6 and a foreign-origin `blob:`. URLs are validated, not rewritten, and there is no `<base>` element in the page or in `_wrap_page()`, so the validation base and the fetch base are the same. The reviewer also forced a reader to throw inside the render hold and confirmed the `finally` released it and the next event still drew — a hold that leaked would have frozen the board.

**No leak and no new XSS surface:** `answers/` and `collector_state/` records are inert and unknown collections are never read, so PBI-005's AC-SV7 holds on the page side; no renderer was touched and `md()` was not widened; an `img onerror` payload in a findings-tab title arrives entity-escaped on **both** adapters. The page contains exactly one `console.error`, the pre-existing one at `site/index.html:1107`.

**Test integrity:** the test diff has exactly two deleted lines (a header comment and the `env()` signature); nothing was weakened. The reviewer's own 18-mutant sweep kills the builder's 8/8 plus 5 more.

**Follow-ups:** five mutants survive that sweep, all unpinned correct guards — the notable one being that the render hold's own `finally` is untested. And `CLAUDE.md` is outside this PBI's `allowed_areas`, so its store-path table and page-test bullet still describe a store-only page; a docs chore covers that along with the `findings` tab row PBI-011 left.

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

**Owner authority, 2026-09-12:** promoted and started under the owner's standing instruction to keep building the backlog, verbatim: "This is for dispatch board. Lets keep building the backlog". `merge_allowed_by_agent` was changed from `false` to `true` under the owner's standing merge authorisation of 2026-09-12, verbatim: "Standing authorisation: merge any PBI PR yourself, squash, once its code review is GO or its conditions are all applied. Don't ask me each time." The no-self-merge floor is unchanged: the merge still requires a GO or fully-applied conditions, and a NO-GO or a circuit-breaker still stops.

**Why it can run now:** its dependencies PBI-003 and PBI-005 are both Done, and it takes the `page` group's single High-risk slot, which PBI-011's close-out freed. It builds against the `window.__DISPATCH_LOCAL__` seam and the snapshot/event shapes PBI-005's spec (revision 2, §6.1) defined; that spec deliberately deferred the *detection signal* to this PBI.

---

**Follow-up logged 2026-09-11** from the PBI-003 code review (`docs/backlog/reviews/PBI-003/findings.json`, follow-up 2):
- **The gap:** the `datetime` type in PBI-003's `SHAPES` is defined by Python's `datetime.fromisoformat`, which accepts forms a JavaScript reader of `local/records.shapes.json` cannot reproduce.
- **To do:** before PBI-006 validates against the JSON copy, pin a portable definition, such as a regex in `SHAPES`. That change needs `local/records*` in the areas of whichever PBI makes it.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | `requires_spec: false`; the approved parent spec (revision 5) is the design authority, and its row Q-11 left only the detection signal to this PBI |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-12 (round 2 GO) | Round 1 **GO-WITH-CONDITIONS** (0 Critical, 0 High, 1 Medium, 5 Low) — all six applied; round 2 **GO with zero findings**. The Medium was that the FR-97 equivalence fixture left five of ten panels empty on both sides; replaying it confirms six came up empty, so the finding was real. Round 2 re-measured rather than trusting the report: 19 hostile URLs against the new same-origin check, a forced throw inside the render hold to prove the `finally` releases, and an 18-mutant sweep killing the builder's 8/8 plus 5 more. `docs/backlog/reviews/PBI-006/findings-r1.json`, `findings.json`, `cell-report.json` |
| No-self-merge gate | always | passed 2026-09-12 | PR #21 squash-merged `10e6659` by the orchestrator under the owner's standing merge authorisation (`merge_allowed_by_agent` set `true` from `false` under that authority), on a round-2 GO. Landing: resolved squash (declared) / observed squash, level `record`. PR `MERGEABLE` / `CLEAN`. |
| BOARD-tidy gate | always | passed 2026-09-12 | two-part Done write: `docs/backlog/done-log.md` entry + BOARD `## Done` index row |
