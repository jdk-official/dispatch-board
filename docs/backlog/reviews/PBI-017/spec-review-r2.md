# Spec-gate review, round 2 — PBI-017 per-PBI spec, revision 2

- **Gate:** spec gate (`requires_spec: true`)
- **Reviewer:** same-vendor subagent with a clean context (Claude Code Plan agent following `pbi-review`), read-only
- **Date:** 2026-09-11

**Verdict:** **APPROVE-WITH-NOTES**

**Checked:**
- Round-1 findings H1, H2, M1–M4 and L1–L7 are resolved.
- H2 was re-tested on the real transcripts: the one real typed plugin command counted, and every tool, attachment, system and `isMeta` occurrence excluded.
- M1 was re-tested on the real manifests: 4 purposes kept whole and 4 cut at 120 characters.
- Every cited code line is accurate.
- The spec is buildable once the notes are applied, and the reviewer judged that no third round is needed.

## Notes and dispositions (all applied in revision 3)

| ID | Note | Disposition |
|---|---|---|
| M1 | A projects column scoped to the view shows nothing useful | Applied: projects are computed over all exported sessions, including "Other sessions"; AC-C4 and the page tests updated |
| M2 | The frontmatter rule ignores CRLF, which every real file uses | Applied: text mode with `utf-8-sig`, `strip()` before the quote rule; CRLF+BOM fixture in AC-C1 |
| L1 | The `export()` test would run the real exporters | Applied: module-level `EXPORTERS`; the test patches `refresh.subprocess.run` |
| L2 | Purpose-rule details open | Applied: punctuation kept; 120 characters includes `…`; empty description means no manifest; `e.g.`/`i.e.` case-insensitive |
| L3 | Omission rules for missing values unstated | Applied: `start` omitted when null; `skillUses` always emitted (`{}`); a use with no time is counted; the page treats a missing `skillUses` as `{}` |
| L4 | View scope of the counts | Applied: the session scope matches the run scope; the Outside tile shows the view and all-sessions figures |
| L5 | Entry names and ids not validated | Applied: name fallbacks; ids checked against the regex |
| L6 | Page tests left parts of AC-C2 and AC-C4 untested | Applied: last use, projects, filter narrowing, `<details>`, caption, hostile-text `esc()` |
| L7 | Docstrings | Applied: the `refresh.py` guard paragraph and the `export_sessions.py` module docstring |
| I1 | Evidence miscount | Applied: one `Skill` call each |
| I2 | `skillUses` keys under a field-path update | No action (sessions use `set`); noted in §7 |
| I3 | Design-rule compliance | No action (compliant) |
