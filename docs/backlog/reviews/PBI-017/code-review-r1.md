# Code-review gate, round 1 — PBI-017 working-tree change

- **Gate:** code-review gate
- **Reviewer:** `review-agents:code-reviewer`, clean context, read-only
- **Date:** 2026-09-11
- **Intent source:** rung 1, per-PBI spec `docs/backlog/specs/pbi-017-agent-catalogue.md` revision 3

**Verdict:** **NO-GO** (2 HIGH unresolved)

**Checked and sound:**
- **Suites:** 193 unittest tests and 35 page checks pass.
- **First push simulated in scratch folders:** 96 writes in 2 batches, no deletes, no guard tripped.
- **Real data:** 30 agents and 21 skills in 8 plugins.
- **Page:** `esc()` on all store text, tokens only, no motion, keyboard access to the new tab.
- **Scope:** only the allowed areas were touched.
- **Deviation assessment:** the code-writer's nine interpretation choices and the `Skill` tool-use dedupe are justified improvements. There is no plan defect.

**Acceptance criteria:**
- AC-C1, C2, C4, C5 and C7 are met.
- AC-C3 is met except for CR-PBI017-01.
- AC-C6 is not met, because of CR-PBI017-02.

The tab was rendered in a real browser (the Browser pane), with the real exported data and a stub store, on the same day. There were no errors; the clamped descriptions expand, and the table scrolls inside its own box.

## Findings and dispositions

The code-writer fixed all four findings under TDD. Its verdict was DONE: 197 unittest tests and 43 page checks pass. The fix is being re-reviewed in round 2 (`code-review-r2.md`).

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| CR-PBI017-01 | High | A skill id such as `constructor` resolves through `Object.prototype` in `catalogueUses` and throws inside `renderAll`, blanking every later tab | Sent to `engineering-agents:code-writer`: prototype-free indexes, a try/catch around each tab's render, page checks |
| CR-PBI017-02 | High | Deeply nested JSON in a manifest or the installed-plugins file raises `RecursionError`: exit 1, and `refresh.py` pushes nothing | Sent to the code-writer: wider handlers, guarded folder listings, tests |
| CR-PBI017-03 | Low | The tab says "not exported yet" while the store is still connecting or offline | Sent to the code-writer |
| CR-PBI017-04 | Low | The page-test descriptions omit the catalogue tab | Sent to the code-writer |
| Follow-up | Info | Choice 6: an installed-plugins key with an empty install list counts as installed | No change: the real installed-plugins file (version 2) has exactly one install record under each of the 9 `@agent-catalog` keys, and no empty lists. Kept as the code-writer chose it |
| Follow-up | Info | Earlier round ids CR-01..12, CR2-*, CR3-* are not recorded in the repo | Noted: those rounds were run in-session before review notes were kept; regressions were covered by the full suites and the unchanged guard code |
