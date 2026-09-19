# Chore review — docs: PBI-014's run fields (`findings`, `files`)

Reviewer: fresh-context read-only agent, 2026-09-13, against the merged tree at `4bbbad8`. Saved by the orchestrator. Substantive chore (contract doc), so no review skip is recorded. The chore discharges PBI-014's close-out condition CR-014-3.

**Verdict: APPROVE-WITH-NOTES. Both notes applied.**

## The seven claims, each verified against the code

| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | `findings` appears only on a code-review round with a readable findings block; `[]` when the round listed none; the key is left out when nothing readable was found | **Confirmed** | `exporters/derive.py:533-539` sets `findings`/`hasFindingsBlock` only when `lane == 'cr'`; `findings_of()` returns `None` when unreadable; `run_doc()` (`:818-819`) copies `findings` only when `hasFindingsBlock` is truthy, otherwise omitting the key |
| 2 | `files` comes from successful edit tool calls only | **Confirmed** | `response()` records every edit call by tool id (`:290-297`); `failed_edit()` marks ids whose result was `is_error` (`:300-308`); `agent_summary()` (`:346`) drops files whose id is in `failed` |
| 3 | Paths are published relative to the project's `repoPath` | **Confirmed** | `publishable_files()` (`:767-795`) strips the normalized `repo` prefix |
| 4 | Unplaceable paths publish as `…/<file name>`: worktree, genuinely outside, `~/`, drive-relative, and a session linked to no project | **Confirmed for (a)–(d); confirmed in practice for (e)** | A worktree path is outside `root` in string terms and takes the `ABSOLUTE` branch (`:789-790`), matching the docstring (`:774`). For (e), `export_sessions.py:284-286` passes `repo_of.get(pid)`, which is `None` for an unlinked session; with no root, only `ABSOLUTE`/`UNPLACEABLE` paths get `…/name` (`:781-792`) — a bare relative path would keep its folders. Holds because edit tool inputs are always absolute (enforced upstream); see N1 |
| 5 | A code-reviewer run's panel shows the files its findings name | **Confirmed** | `site/index.html:588-599` falls back to files parsed from finding locations when `edited` is empty, rendering "Files its findings name: …"; exercised in `tests/page.test.mjs` section 22 |
| 6 | The PBI-027 gap: the local collector omits the repository | **Confirmed** | `local/collector.py:436` calls `derive.run_doc` with no fourth argument, so every path collapses to `…/<file name>` |
| 7 | Both fields are published unredacted; `exclude` applies | **Confirmed, both parts** | Text is rendered via `esc()`/`md()` only, never redacted (`site/index.html:596-605`). `export_sessions.py:233-234` `continue`s before `parse_session()` for an excluded session, so its runs are never parsed or exported — not merely blanked at document assembly |

## Findings and dispositions

| id | sev | finding | disposition |
|---|---|---|---|
| N1 | Low | Claim 4(e)'s "any path from a session linked to no project" is true only because edit tool inputs are always absolute; the code would pass a bare relative path through with folders intact (`derive.py:781-792`), and no test covers that combination (`tests/test_derive.py:311-318` exercises only absolute inputs). | **Applied.** The row now says such a session has no `repoPath` to place a path against, that edit tool inputs are always absolute and so always unplaceable, and that the rule itself would pass a bare relative path through with its folders. |
| N2 | Low | The tests section's description of `tests/page.test.mjs` omits the run-detail checks PBI-014 added (section 22, ~130 lines, `:1644-1780`) — a stale statement this chore did not originally fix. | **Applied.** The bullet now also names the findings ledger, the run detail (verdict, findings, files edited, duration) and the data-adapter seam, all of which the suite checks. |

## Voice and confidence

The additions match the document's dense, cross-referencing style. Nothing is asserted more confidently than the code supports, apart from N1's over-generalisation, now corrected.

## Other stale statements swept for

Beyond N2, none. The Dispatch tab description, `PARSER_VERSION`, the session cache and the page-adapter equivalence passages name no fixed field list or panel count that PBI-014 changed.

## Gate

Docs class. The three configured suites were run anyway and quoted on `4bbbad8`: `tests` **360**, `page.test.mjs` **121**, `local/tests` **304** — all passing.
