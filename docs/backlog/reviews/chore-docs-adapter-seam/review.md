# Chore review — docs: the adapter seam, the findings tab, and the local suite

Reviewer: fresh-context read-only agent, 2026-09-12, against the live tree at `10e6659`. Saved by the orchestrator. Substantive chore (contract doc), so no review skip is recorded.

**Round 1 verdict: CHANGES-REQUIRED. All three actionable findings applied; re-verified below.**

## Findings and dispositions

| id | sev | finding | disposition |
|---|---|---|---|
| **F7** | **High** | The Refresh-procedure paragraph's tab list is stale: "A project always shows all its tabs (Overview, Spec, Assumptions, Decisions, Backlog, GitHub, Dispatch, Agent catalogue, Claude usage)" names nine and omits the **Findings ledger** tab PBI-011 added. The page has ten (`site/index.html:236`, `tab-findings`). | **Applied.** "Findings ledger" inserted after GitHub. This was a pre-existing staleness the chore's own edits did not touch — the reviewer was asked specifically to look for exactly this, and found it. |
| **F1** | Medium | "Only a round whose result actually carries a structured findings block counts" overstates `hasFindingsBlock`. A round without a parseable block **still counts toward `rounds`** (and can still set `roundsToGo`); it simply is not authoritative for deciding which findings are *open*. Evidence: `exporters/derive.py:674-708`, docstring at `:678-680` ("still counts as a round but is never authoritative"), and `item['rounds'] = len(runs)` at `:704` including blockless rounds. | **Applied,** reworded to the reviewer's own phrasing. The orchestrator had also repeated this inaccuracy to the owner in conversation and corrected it there. |
| **F2** | Low | "`generatedAt` and `source` are omitted when missing" implies the exporter sometimes leaves them out. It always writes both (`exporters/export_sessions.py:302-305`), and `generatedAt` is `required` in the shared `tab` shape (`local/records.py:57-59`). | **Applied.** Replaced with a statement true of the schema: `source` is optional, `generatedAt` is required, and the exporter writes both. |

## Verified correct, no action

| id | what was confirmed |
|---|---|
| F3 | The findings writer is `exporters/export_sessions.py`, **not** `export_board.py`; the document is deleted when a project has no finished round; the **two-writer ownership** statement and the warning that `records.TAB_NAMES` lists all six names are accurate and load-bearing. `exporters/export_sessions.py:290-309`, `exporters/export_board.py:39`, `:265-284`, `local/records.py:91`. |
| F4 | The adapter-seam section verified line for line: the `window.__DISPATCH_LOCAL__` marker name; both URLs required and same-origin; `javascript:` / `data:` / cross-origin falling back to the store adapter; the `window.claude`-absence rationale; and the degrade list (refuse / timeout / 503 / bad JSON / **200 with a non-snapshot body** → offline board, the exact quoted message, no stream, `console.warn`), with an empty `records` map still drawing an ordinary empty board. `site/index.html:1265-1291`, `:1225-1233`. |
| F5 | The ten-panel deep-equal claim: exactly ten tabs exist, and `rendered()` compares all ten with `emptyPanels` asserted `[]` on both sides before the `deepEqual`. `tests/page.test.mjs:1421-1473`. |
| F6 | The tests-section rewrite: `local/tests` now covers the collector and the server (127.0.0.1 bind, Host/Origin gate, read-only opener, UNC refusal, the live stream), and `test_conformance.py` really runs the real exporters in-process rather than hand-building documents. `local/tests/test_server.py:20-33`, `:517-533`; `local/tests/test_conformance.py:1-19`. |

## Other staleness swept for and not found

The reviewer read the whole document against the merged tree. Beyond F7, it found nothing stale in "Open items", the local-app description, or the rest of the store-path table, and judged nothing overstated relative to the code.

## Gate

Docs class. The three configured suites were run anyway and quoted: `tests` **334**, `page.test.mjs` **111**, `local/tests` **265** — all passing on `10e6659`.
