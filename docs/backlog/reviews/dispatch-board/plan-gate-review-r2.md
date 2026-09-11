# Plan-gate review, round 2 — `docs/backlog/specs/dispatch-board.md` revision 3

- **Gate:** plan gate
- **Reviewer:** same-vendor subagent with a clean context (Claude Code Plan agent following `pbi-review`), read-only
- **Date:** 2026-09-11
- **Verdict:** **CHANGES-REQUIRED**
- **Human approval:** still required.
- **Result of round 1:**
  - fixed: H-1, H-2, H-4 (on the PC), M-2, M-4, M-5, M-6, L-1, L-2, L-3, S-1, S-2 and S-3;
  - partly fixed: H-3, M-1, M-3, M-7 and M-8.

  The partial fixes led to the findings below.
- **Parser:** `spec_tabs` still reads the spec: 21 PBIs, `humanList` `[7, 15, 24]`, 7 goals, 9 decisions, ADR-0001.
- **Checks:** the dependency graph is acyclic, and the PBI-017 join is feasible from the files named.

## Findings and dispositions in revision 4

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| R2-H1 | High | PBI-017, PBI-018, PBI-021 and PBI-022 had no source of acceptance criteria (the PRD has none for them); PBI-017's store location and `agentType` gap were undecided | Applied: a new spec section with AC-C1–AC-C6, AC-L1–AC-L3, AC-S1–AC-S3 and AC-R1–AC-R3. The catalogue goes in a `catalogue/agents` document, managed and guarded. Run docs gain `agentType`. Row 16 changed and needs re-confirmation |
| R2-M1 | Medium | "Built first" existed only in prose, and the second-group convention cannot be enforced | Applied: PBI-001, PBI-003 and PBI-013 depend on PBI-018. Every `site/**` PBI is registered in `page` at High. Page PBIs that also edit exporters depend on PBI-001 or PBI-004. PBI-021 and PBI-022 are declared exempt. The second group is now a note for readers only |
| R2-M2 | Medium | The cross-group rule was applied inconsistently (PBI-010, PBI-005, PBI-019, PBI-017) | Applied through the R2-M1 scheme; the `config` and `exporters` touches are declared |
| R2-M3 | Medium | The catalogue had no local-app record | Applied: a catalogue record in PBI-003, and the catalogue read in PBI-019 |
| R2-M4 | Medium | PBI-009 to PBI-012 did not depend on PBI-004 | Applied |
| R2-M5 | Medium | PBI-016 lacked the collector's upload half, and row 24 blocked LAN hostnames | Applied: `local/collector*` added; the Host allow-list extended on Unraid; row 7 clarified |
| R2-M6 | Medium | AC-68 and NFR-18 were in PBI-005, which cannot demonstrate them | Applied: moved to PBI-007; PBI-005 keeps a server-level push check |
| R2-L1 | Low | Row 19 said 7 plugins; the agents are in 6 | Applied |
| R2-L2 | Low | The deferred answer requirements were not named | Applied: listed in Out of scope and Future iterations; PBI-003 retitled |
| R2-L3 | Low | FR-101 and FR-103 appeared in two titles each | Applied: the titles now mark each half |
| R2-L4 | Low | PBI-022's area was too broad and its scope too narrow | Applied: narrowed to `docs/prd/**`, `docs/backlog/evidence/**` and one brief line; the plan-gate answers added to AC-R2 |
| R2-L5 | Low | ADR-0001 was `accepted` before the gate, and had a wording slip | Applied: `proposed` until the spec is approved; wording fixed |
| Info | — | Add the retirement ideas to Future iterations; PBI-018 must handle a spec with no such section | Applied (AC-L3) |
