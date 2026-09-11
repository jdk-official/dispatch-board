# Plan-gate review, round 1 — `docs/backlog/specs/dispatch-board.md` revision 1

- **Gate:** plan gate (SPEC §Gates, plan gate)
- **Reviewer:** same-vendor subagent with a clean context (Claude Code Plan agent following `pbi-review`), read-only. Reviewer tier per `backlog-delivery.config` `[reviewer] mode = "same-vendor-subagent"`.
- **Date:** 2026-09-11
- **Verdict:** **CHANGES-REQUIRED**
- **Human approval:** still required (`plan_gate_requires_human = true`).
- **Scope note:** the review covered revision 1. Revision 2 (PBI-017 and PBI-018, added at the owner's request while it ran) was not reviewed. Revision 3 applies every finding below and goes to round 2.

## What checked out
- **D-18 delivered** in `2742ca6`, with 141 tests and the page test in the repo.
- **Tab bar wraps:** `site/index.html:58`.
- **Human-confirm list:** it names exactly the ASSUMED rows.
- **Graph and groups:** the graph is acyclic and every conflict group is in the registry.
- **Decisions and constraints:** the key decisions match D-9, D-16 and D-17, and the design is consistent with C-2, C-7, C-13, C-15, C-17 and C-18.
- **Dashboard parser:** the parser's inputs (PBI table, confirm line, goal bullets, ledger and decisions tables) parse correctly.

## Findings and dispositions in revision 3

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| H-1 | High | The provenance guards (FR-133, FR-134, NFR-23) lived only in conditional PBI-015, and FR-134 was double-claimed by PBI-016 | Applied: FR-133 and the C-16 `CLAUDE.md` rule go to PBI-001, and FR-134 goes to PBI-016 alone. PBI-015 is deferred by the owner (row 5) |
| H-2 | High | An owner-gated, irreversible store delete was buried in code PBI-001, with no approval gate | Applied: a separate owner-run PBI-021 (`requires_external_review: true`), with preconditions: the published page confirmed project-first, the six documents exported to `snapshot/`, and the owner approving the named batch in chat |
| H-3 | High | PBI-010 retires `buildState` lossily: exporter order, lost `review`/`open`/`commit`, unlinked sessions, an undeclared `config` touch | Applied: `requires_spec: true`; the spec defines the data flow, a shadow period, and overrides for `review`/`open`/`commit`; the data file is never deleted; the `config` touch is declared (row 15 changed and needs re-confirmation) |
| H-4 | High | Local server exposure: DNS rebinding and CSRF on 127.0.0.1, a trivially readable key, LAN answers, and no location for the secret | Applied: PBI-005 `requires_spec: true`, with a Host allow-list, Origin checks and no CORS; there is no answers endpoint (row 5); the secret comes from an environment variable or a git-ignored file (rows 7 and 24 need re-confirmation; row 9 is not applicable) |
| M-1 | Medium | Coverage gaps: FR-95, FR-101 double-claimed, NFR-17, NFR-18, NFR-22, the token relabel | Applied: FR-95 deferred with PBI-015; PBI-003 defines the FR-101 fields and PBI-020 fills them; NFR-17 and AC-70 go to PBI-007, NFR-18 and AC-68 to PBI-005; NFR-22 is stated for every page PBI; the relabel goes to PBI-002 |
| M-2 | Medium | Missing edges: PBI-005→schema, PBI-008→collector, PBI-014→PBI-003, PBI-009's edge | Applied: the SQLite schema moves into PBI-003; the collector's last-refresh write moves into PBI-019; PBI-014 and PBI-020 depend on PBI-003; PBI-009 depends on PBI-001 |
| M-3 | Medium | The conflict metadata did not enforce "runs alone"; PBI-013's exporter area was unnecessary; cross-group touches were undeclared | Applied: cross-group PBIs set to `conflict_risk: High` with both groups declared; PBI-013 is page-only; the docs and config touches are declared |
| M-4 | Medium | PBI-004 and PBI-014 were oversized | Applied: PBI-004 split into PBI-004 (shared derivation, no behaviour change) and PBI-019 (collector); PBI-014 split into PBI-014 (run detail) and PBI-020 (timeline) |
| M-5 | Medium | Local-app design gaps: cross-process change detection, no guard in the local store, UNC check in the server only | Applied: PBI-019 is `requires_spec`, covering WAL, `PRAGMA data_version` polling, a mass-delete guard and age-only pruning; the network-path guard goes in both the collector and the server |
| M-6 | Medium | PBI-007 registers a Task Scheduler task with no approval gate | Applied: `requires_external_review: true` |
| M-7 | Medium | New config keys had no owner | Applied: PBI-005 owns the port and PBI-019 the database path; both may edit `board.config.json` and `exporters/board_config.py` |
| M-8 | Medium | Where the shared derivation lives was ambiguous | Applied: a stated rule. Derivations live in the shared module under `exporters/`, the collector imports them, and whichever PBI lands second extends the AC-64 fixture |
| L-1 | Low | Round-4 review citations had no repo record, and "three rounds ending in GO" was inaccurate | Applied: cited as the code-reviewer report of 2026-09-11 in session `9562c312` (not stored in the repo); the round wording corrected |
| L-2 | Low | Row 2 cited `CLAUDE.md` for "tab bar wraps" | Applied: now cites `site/index.html:58` and the `2742ca6` commit message |
| L-3 | Low | D-18's demonstration ACs have no evidence, and the PRD needs a re-baseline | Applied: PBI-022 |
| I-1 | Info | The exporter reads six PBI columns, so the ext.-review column is not shown | Noted; out of scope for this plan |
| I-2 | Info | Retention drops the history of unlinked sessions | The owner confirmed row 12 knowingly |
| S-1 | Medium | ADRs belong at the plan gate, not in PBIs | Applied: ADR-0001 (local-first architecture) emitted at the gate; no answers ADR, because it is deferred; `docs/adr/**` removed from PBI-003 |
| S-2 | Low | `change_class`, `pr_required` and `merge_allowed_by_agent` not proposed | Applied: stated in the decomposition rationale |
| S-3 | Low | The config names a missing `scripts/create-pbi-worktree.py` | Applied: the key was removed, with a note |
| S-4 | Info | Dashboard parser: no breakage | Kept the formats |
