# Spec-gate review, round 3 — PBI-003 per-PBI spec, revision 3

- **Gate:** spec gate (`requires_spec: true`); this is the last round under `spec_review_max_rounds = 3`
- **Reviewer:** a same-vendor subagent with a clean context (the Claude Code Plan agent, following `pbi-review`), read-only
- **Date:** 2026-09-11

**Verdict:** **APPROVE-WITH-NOTES**. The gate passes, with every note dispositioned below.

**What the reviewer found sound:**
- **Round-2 findings:** N-1 to N-9, I-1 and I-4 are resolved.
- **The grammar:** a validator built from §3.1 alone works, and `json.dumps(SHAPES)` succeeds.
- **Fidelity:** zero errors across every real `out/` document:
  - 16 sessions, 95 runs and 2 projects;
  - 10 tabs and 2 status documents;
  - the catalogue, whose 51 entries all satisfy `id == plugin:name`.
- **Consistency:** §3.2, §3.3 and §4 agree.
- **Transactions:** the transaction mechanism was verified for the default connection under Python 3.14.5 and SQLite 3.50.4.

## Notes and dispositions (all applied in revision 4)

| ID | Severity | Note | Disposition |
|---|---|---|---|
| R3-1 | Medium | `conn.commit()` and `conn.rollback()` do nothing on an `autocommit=True` connection | Applied: explicit `COMMIT`/`ROLLBACK` statements; T3 covers `autocommit=True` |
| R3-2 | Low | `re.match` with `$` accepts a trailing newline | Applied: `re.fullmatch`; the difference from `board_config` is recorded; T4 covers it and the comparison sample excludes such strings |
| R3-3 | Low | Run and session ids could be `.`, `..`, contain `\` or control characters | Applied: rejected; T4 covers it |
| R3-4 | Low | `run.end` untested | Applied: T1 case |
| R3-5 | Low | The `datetime` rule's wording; non-string input | Applied: "parses and `tzinfo` set"; a non-string is a type error; T1 cases |
| R3-6 | Info | `sqlite_autoindex_*` rows | Applied: T3 compares named indexes only |
| R3-7 | Info | The PBI-001 handoff covers only `lane`/`kind`; don't import `local/` from `exporters/` | Applied: the PBI-001 note is widened to the manual-row field types and says to copy the enum values, not import them |
| R3-8 | Info | Parent row 12's keying | Applied: one line in §7 |
