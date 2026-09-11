# Code-review gate, round 2 — PBI-017 fix round

- **Gate:** code-review gate
- **Reviewer:** `review-agents:code-reviewer`, clean context, read-only
- **Date:** 2026-09-11
- **Intent source:** rung 1, per-PBI spec `docs/backlog/specs/pbi-017-agent-catalogue.md` revision 3

**Verdict:** **GO-WITH-CONDITIONS**. All round-1 findings are resolved, with one new MEDIUM finding in the tests.

**Round-1 findings:**

| ID | Status | Evidence |
|---|---|---|
| CR-PBI017-01 (High) | Resolved | The name index is a `Map`, and each tab renders on its own. A probe put `__proto__` and `constructor` on both sides (entry names, plugin names, project ids, bare and namespaced skill ids, agent types); every case counted correctly with no errors. |
| CR-PBI017-02 (High) | Resolved | Nested JSON at depths 1,000, 100,000 and 1,000,000 in both files gave exit 0, with the specified fallbacks. An unlistable `plugins/` keeps the last export byte for byte. |
| CR-PBI017-03 (Low) | Resolved | The tab shows "Connecting" or the offline message until the store answers. The other tabs' states are unchanged. |
| CR-PBI017-04 (Low) | Resolved | The page-test header and `CLAUDE.md` name the Agent catalogue tab. |

**Checks:**
- **Suites:** 197 unittest tests and 43 page checks pass.
- **Acceptance criteria:** AC-C3 and AC-C6 are now met; the round-1 assessment of the other criteria holds.
- **Deviations:** the fix's deviations are justified improvements: per-tab isolation, `Map` indexes, `listing()` in place of `glob`, and the `gotCatalogue` flag.

## New findings and dispositions

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| CR-PBI017-R2-01 | Medium | The per-tab try/catch hides a crashing tab from the page suite. A mutated page whose project Overview throws still passed all 43 checks. | Condition: sent to `engineering-agents:code-writer`. The harness is to fail on any unexpected `console.error`, with a project-Overview content assertion, and the mutation probe re-run to confirm the suite goes red. |
| Follow-up | Info | The optional part of CR-03: the usage columns can briefly read "never used" before sessions and runs load | Deferred: cosmetic, and it clears on the next snapshot. Logged in PBI-002 (page fixes). |
| Follow-up | Info | Pre-existing, outside this change: `records()` in `exporters/export_sessions.py` catches only `ValueError`, and a deeply nested transcript line raises `RecursionError` | Deferred: outside PBI-017's change, and contained by the per-session `except Exception`. Logged in PBI-001 (exporter hardening). |
