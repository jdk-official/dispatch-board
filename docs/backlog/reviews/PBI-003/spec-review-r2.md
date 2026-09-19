# Spec-gate review, round 2 — PBI-003 per-PBI spec, revision 2

- **Gate:** spec gate (`requires_spec: true`)
- **Reviewer:** a same-vendor subagent with a clean context (the Claude Code Plan agent, following `pbi-review`), read-only
- **Date:** 2026-09-11

**Verdict:** **CHANGES-REQUIRED**

**Round-1 findings in revision 2:**
- **Resolved:** F-1 to F-4, F-7 to F-11 and F-15.
- **Partly resolved:**
  - F-5 (leaves the `meta/` collision, N-1);
  - F-6 (the nested checks can't be written in the grammar, N-2);
  - F-12 (the handoff isn't recorded in PBI-001, N-5);
  - F-13 (the id forms are under-specified, N-1 and N-4);
  - F-14 (transactions, N-3).

**Fidelity re-check:** revision 2's §3.1 was validated against every real `out/` document, with no errors:
- 16 sessions and 95 runs;
- 2 projects and 10 tabs;
- 2 status documents;
- the catalogue, with 51 entries and 8 plugins.

## Findings and dispositions (all applied in revision 3)

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| N-1 | Medium | The status id form is narrower than v1's `STATUS_DOC`; `meta/lastRefresh` is itself a legal statusDoc | Applied: the status id uses the `STATUS_DOC` regex minus the reserved `meta/lastRefresh`; T4 checks it against `board_config`; follow-up logged in PBI-001 |
| N-2 | Medium | The `SHAPES` grammar can't hold the nested checks | Applied: the grammar gains `list_of`, `map_of` and `datetime`; path-qualified errors; all nested rules live in `SHAPES`; the `id == plugin:name` rule is stated as not checked by `validate` (T2 asserts it) |
| N-3 | Medium | "One transaction" isn't implicit in Python 3.14's sqlite3, and nothing tests it | Applied: §4's mechanism (reject a connection already in a transaction; `BEGIN IMMEDIATE`; version read inside it; `execute()` only; commit or roll back); T3 atomicity case |
| N-4 | Low | Id forms undefined for session, run and project | Applied: §3.2, one segment with no `/`; project ids use `board_config.ID`; T4 bad forms for every kind |
| N-5 | Low | Handoffs exist only in the spec | Applied: both recorded in `PBI-001.md` |
| N-6 | Low | The JSON dump has no producer | Applied: `local/records.shapes.json` plus `--write-shapes`; T1 checks equality |
| N-7 | Low | The row interface is unspecified | Applied: `TABLES`; `to_row` returns a column dict; `from_row` takes a mapping or text; tab columns come from the id |
| N-8 | Low | ISO-8601 UTC not enforced | Applied: a strict `datetime` type for `lastRefresh.at` only |
| N-9 | Low | Test gaps (a) to (d) | Applied: status test reworded; the kept tab comes from the exporter; a null-timestamp linked session; excluded files and the folder-to-kind map named |
| I-1 | Info | The `human` lane citation | Applied: corrected |
| I-2, I-3, I-5, I-6 | Info | Notes | Recorded in revision 3 |
| I-4 | Info | The PBI-003 gate row still says revision 1 | Applied |
