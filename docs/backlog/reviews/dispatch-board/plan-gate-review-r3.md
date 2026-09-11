# Plan-gate review, round 3 — `docs/backlog/specs/dispatch-board.md` revision 4

- **Gate:** plan gate
- **Reviewer:** same-vendor subagent with a clean context (Claude Code Plan agent following `pbi-review`), read-only
- **Date:** 2026-09-11

**Verdict:** **APPROVE-WITH-NOTES**

- **Human approval:** required, and given (see the spec's Plan-gate record).
- **Round-2 findings:** all 12 resolved; three had small remainders (M1, L4, L6).
- **Ordering trace:** PBI-017 and PBI-018 run alone, and page PBIs run one at a time.
- **Graph and groups:** the graph is acyclic and every group is registered.
- **PRD coverage:** exactly once, or explicitly deferred.
- **Parser:** reads revision 4: `humanList` `[16]`, 21 PBIs, 7 goals, 9 decisions, ADR-0001 `proposed`, rounds r1 and r2.

## Notes and dispositions (applied in revision 5)

| ID | Note | Disposition |
|---|---|---|
| M1 | PBI-008 could run beside PBI-004 on `refresh.py` | Applied: PBI-008 depends on `[PBI-003, PBI-004]` |
| L1 | AC-C1 did not name the installed-plugins path or the script | Applied: a new `exporters/export_catalogue.py` run by `refresh.py`; `catalogue.marketplacePath` and `catalogue.installedPath` keys; tests pass their own paths |
| L2 | AC-C2 said "each run document"; the guard was undefined for one document | Applied: subagent run docs only (manual rows carry none); the refresh script refuses deleting `catalogue/index` without `--allow-mass-delete` |
| L3 | The AC-L1 title rule did not fit the spec's own bullets | Applied: title is the first bold span, description is the rest; the list's bullets reworded to `**Title**: description` |
| L4 | AC-R2 listed only some settled A-rows | Applied: every PRD A-row settled by a ledger row, citing the row |
| L5 | AC-C4's tile scope was unstated | Applied: current view, with the all-sessions figure beside |
| L6 | Rows 7 and 24 were reworded after confirmation | Applied: the approval names the revision-4 wording; row 24's impact text restored |
| L7 | PBI-003's run record lacked `agentType` | Applied now in PBI-003's area text (it defines `agentType` and per-session skill use); also covered by its per-PBI spec |
| L8 | PBI-019 and PBI-005 both add a config key | Applied: a sentence accepting that small merge |
| L9 | PBI-021 was `trivial` though its core act is an irreversible delete | Applied: `standard` |
| F1 | ADR-0001 cited spec revision 3 | Applied: ADR-0001 accepted, citing revision 5 |
| F2, Info | FR-96 split; CLAUDE.md/README prose merges; `snapshot/**` has no group | No action, for the reasons given in the review |
| F3 | The round-3 note must use the `**Verdict:**` form | Applied (this file) |

## Change after this review

The owner changed PBI-017's criteria at approval: "Include skills too" and "Show what each agent is for". To keep that change reviewed without a fourth plan-gate round, PBI-017 is set to `requires_spec: true`. Its refined per-PBI spec, covering skills and purpose groups (AC-C1–AC-C7), gets an independent spec-gate review before any code is written (SPEC §Gates, spec gate).
