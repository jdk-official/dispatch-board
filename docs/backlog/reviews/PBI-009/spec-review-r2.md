# Spec-gate review — PBI-009 "Waiting on you" (revision 2, round 2)

Reviewer: `pbi-review`, same-vendor-subagent tier, clean context, read-only. Live tree `560e296`. Every citation re-read and line-counted; no `sed`. Saved by the orchestrator.

> **Note on the transport.** The harness flagged this reply as containing instruction-shaped text and neutralised the control tags. That was not an injection attempt: finding N-3 is *about* the product mis-parsing framing text as owner input, so the reviewer had to quote a `<system-reminder>`-shaped record to describe the defect. Quoted tags below are escaped.

**Verdict: APPROVE-WITH-NOTES**

## Round-1 resolution

| F | Resolved | What was checked |
|---|---|---|
| **F-1** | **Yes** | New §3.3.1 carries the table (12/15 sessions, 36 calls, 36 answered, **0 unanswered**, D1 fires 0/15). §1.1 separates *signals* from *panel* and names D2 as producing the question half. §7.1 reads "rare-but-high-value… **It is not what makes the panel non-empty**". §1's intent table gained a measured-rate column. |
| **F-2** | **Yes** | §3.2's table carries the measured column (8/1/1/1 of 11) and states revision 1 had it backwards. §9 row 1 split: **1a `automode-blocked` (8/11), marked the one that matters**; 1b `user-rejected` (1/11) beside it. |
| **F-3** | **Yes — the strongest fix in the revision** | `derive.py:438` re-read: the §4.1 quote is verbatim, character for character. It tests `str` only, ignores `isMeta`, and is left untouched — so a session opening with pasted-attachment (list) content still sets `first` from the later plain-string record exactly as today. `is_owner_message()` is a separate predicate used only by the new folds; the "no behaviour change" claim is gone. T-4 and T-12 no longer overlap, and T-25 pins the divergence. |
| **F-4** | **Yes** | W-14 names **the owner** (artefact route as delegation), both themes, `CLAUDE.md:131-139`, NFR-9/10/13/14 individually — all four PRD lines verified — plus NFR-22's reservation clause verbatim. A close-out step, not build output. |
| **F-5** | **Partly — see N-1** | §8.4 probes the fixture's question text and `/Refused/`, states why the title fails, and T-29 is a real negative control. |
| **F-6** | **Yes** | §7.6 adds the 48-h bound (D2 condition 6) and the 20-item cap, both render-time; W-15, T-27, T-28. It **does** clear an abandoned session: the item's `at` is fixed, so suppression fires without owner action. The document does not grow unboundedly — the per-session cap of 5 (§7.3/W-6) bounds `waiting` in the store independently, which matters because project-linked sessions outlive the 7-day window. |
| **F-7** | **Yes** | §9 row 12 + §12 state the FR-108 deviation; both drivers re-verified (`export_sessions.py:170-179`, `refresh.py:82-85`). |
| **F-8** | **Yes** | §8.3 + W-10 require muted style and no `empty` class; T-26 asserts with the same `/class="empty"/` as `page.test.mjs:1463`. |
| **F-9** | **Yes, banked correctly** | Both instances verified: `site/index.html:777` (`tile(… 'var(--human)')`) and `:784` (`--tone:var(--human)` on the ADR cards). **Round 1's framing was wrong and is withdrawn:** NFR-22 (`prd:570`) governs *next-iteration views and the catalogue tab* — it does not reach the Decisions tab. The page-wide rule is **NFR-10** (`prd:549`), already marked *Partly met* with its remedy **planned in PBI-002**. Route the follow-up into PBI-002's existing NFR-10 remedy rather than a fresh PBI. Not this PBI's to fix. |

## The two challenges

**§7.6's values (48 h / 20) — the author is right; non-OWNER stands.** Render-time view constants that delete nothing, reversible in one line, and not what F-6 demanded (F-6 required *a* bound, stated). They differ in kind from row 2, which decides what the feature is. The one product edge — a genuinely unanswered question stops being shown at 48 h — is mitigated by the footer stating the suppression and by §12. FYI is the right weight.

**12 vs 13 — settled at 12, and reconciled rather than adopted.** Re-measured: 25 mains, 15 newest, **12 sessions with an `AskUserQuestion` `tool_use` block, 36 calls, 36 answered, 0 unanswered** — exact reproduction. The 13 is reproducible too: 13 transcripts contain the *literal string* `AskUserQuestion` anywhere; session `233bec8e` carries the string with zero actual calls. So 13 was a string match, 12 the structural count. Immaterial to D1 (0 either way) — but it is the same string-vs-structure error §3.2 warns against, so worth closing. §3.5's "not reconciled" line can go.

## New findings

- **N-1 (Med) — `/Refused/` is still a weak probe.** `site/index.html:1070` renders `<th class="num">Refused</th>` unconditionally in the usage panel, and `page.test.mjs:1467-1470` tests `Object.values(seen).some(...)` across **all** panels. So `/Refused/` matches with the waiting panel absent. Same hazard for the question text if it collides with the assumptions fixture's `Which port?`. T-29 catches this, so it cannot ship wrong — but it costs a build round. Anchor both probes to `seen['panel-overview']`, or use a string unique to the panel.
- **N-2 (Med) — W-14's cited authority does not cover its artefact route.** `specs/dispatch-board.md:216-217` permits `CLAUDE.md` and `README.md` touches; it does not name `docs/backlog/evidence/**`, which is outside `PBI-009.md:7`'s `allowed_areas`. Precedent exists but is not authority. The primary route (owner confirms directly) is scope-clean; if delegated, the worker needs an explicit scope extension. State that, or a scope-breach stop is possible at close-out.
- **N-3 (Low) — `is_owner_message()`'s list branch omits the `<` test.** As specified it accepts any list with a `text` block and no `tool_result`, so a list-form `<\system-reminder>` would read as an owner message and over-clear items — the direction §1.1 calls worse. Measured: **0 such records in 15 transcripts**, so theoretical, and T-4 demands the rejection. Apply the same `<`-prefix test to list text blocks.
- **N-4 (Low) — §7.6's cap has two orderings.** "newest first" and the kind-based drop order coexist; within a kind, nothing says which goes. T-28 pins only the kind part.

## Positions

**D2 ships enabled.** Unchanged from round 1 and better supported: 4/15, 0 false positives, ≈4/7 recall, D1 silent, and §7.6 supplies the age bound made a precondition. Disabling it ships an empty panel.

**Three OWNER rows: 1a, 1b, 2 — correct and correctly weighted.** 1a is the right aim. Rows 3–13 are genuinely settled; none is settleable by code, and none the code settles is marked OWNER. Row 12 (FR-108 deviation) is a PRD-wording departure decided without the owner — defensible since the observable outcome is identical, but it deserves the same FYI as rows 11 and 13.

## Scope check

Clean. `local/**` untouched (§2, §6; `records.py:194-200` allows unlisted fields, `TAB_NAMES` at `:91` never consulted). No new store document — `waiting` is an optional field on `sessions/<id>`, one writer, `refresh.py:44` `MANAGED` and `:47` `TABS` unchanged, mass-delete guard unaffected (a dropped field is a `set`). **`PARSER_VERSION` 6→7 is still correct and necessary**: `export_sessions.py:60` reads 6, and `local/collector.py:157-161` key-set-checks `derive.new_session()`, which W-b changes.
