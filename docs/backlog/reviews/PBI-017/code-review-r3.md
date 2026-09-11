# Code-review gate, round 3 — PBI-017 condition round

- **Gate:** code-review gate
- **Reviewer:** `review-agents:code-reviewer`, clean context, read-only
- **Date:** 2026-09-11
- **Scope:** the round-3 change to `tests/page.test.mjs` (error recorder, `expectErrors()`, `PAGE_HTML`, block 8) and the Tests line in `CLAUDE.md`

**Verdict:** **GO-WITH-CONDITIONS**. CR-PBI017-R2-01 is closed, and the two new findings are LOW, in test code only.

**Checked:**
- **Mutation probes, through `PAGE_HTML`:**
  - an Overview that throws: exit 1, "unexpected console.error";
  - a "Work items built" tile showing `—`: exit 1 at block 8.
- **The recorder is sound:** it is installed before the page script runs; the only `console.error` in the page is in `renderAll`, and nothing fails spuriously.
- **The default path is unchanged**, and the `CLAUDE.md` text is accurate.
- **Suites:** 44 page checks and 197 unittest tests pass.

## Findings and dispositions

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| CR-PBI017-R3-01 | Low | Block 7's `expectErrors()` accepts any `console.error` from any tab, so a second renderer crash caused by the malformed catalogue passes | Logged as a follow-up in PBI-002 (page fixes, whose allowed areas include `tests/page.test.mjs`). Rationale below. |
| CR-PBI017-R3-02 | Low | A check that fails before `ok()` runs never prints the page's recorded error, and the vm filename is hardcoded to `site/index.html` under `PAGE_HTML` | Logged as a follow-up in PBI-002. Diagnostics only: the suite still goes red. |

**Why the follow-ups don't block:**
- Both findings are test-harness diagnostics; no page or exporter behaviour changes.
- R3-01 needs a future change that has another tab read `catalogue/index`, and no tab does today.
- The PBI-017 code-review gate passes on this verdict, with both notes resolved as logged follow-ups (`pbi-review` verdict rules: every note applied, logged as a follow-up, or deferred with rationale).
