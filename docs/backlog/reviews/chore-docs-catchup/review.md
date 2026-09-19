# Chore review — docs catch-up after PBI-009, PBI-007 and PBI-027

Reviewer: fresh-context `review-agents:code-reviewer` (Sonnet), 2026-09-19, read-only, against `25156c9`. Saved by the orchestrator from the reviewer's reply (the reviewer does not write report files).

**Verdict: APPROVE.** No findings.

Every claim the diff adds was checked against the code:
- **The `waiting` field.** Its shape, the clearing rule, and `WAITING_CAP` 5 / `WAITING_TEXT` 300 match `exporters/derive.py:86-87,461-486,599-624`.
- **The owner-message exclusions.** `isCompactSummary` and the interrupt marker, in `CLAUDE.md` and in spec §4.1 and T-4, match `exporters/derive.py:476,479` and `tests/test_derive.py:638`.
- **The privacy bullet.** Text goes through `redact()` and is cut at `WAITING_TEXT`, and `showFirstPrompt` does not gate it. This matches `exporters/derive.py:518,528,615`.
- **Age and idleness are judged by the page.** This matches `site/index.html:493-549`.
- **The Overview order** matches `site/index.html:628-639`.
- **The page-test bullet** matches `tests/page.test.mjs` section 23 and the equivalence check at `:1388-1390`.
- **The PBI-027 gap sentence** is rightly removed: `local/collector.py:438` passes `repo_of.get(pid)`.
- **The `server.log` bullet** now says it logs a startup line, a refusal reason line and one line per response. This matches `local/server.py:56-57,385,396,406,411,556-563`.

Nothing unrelated was removed, and the style is consistent with the rest of the file.
