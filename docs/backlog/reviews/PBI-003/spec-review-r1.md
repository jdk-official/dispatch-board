# Spec-gate review, round 1 — PBI-003 per-PBI spec, revision 1

- **Gate:** spec gate (`requires_spec: true`)
- **Reviewer:** a same-vendor subagent with a clean context (the Claude Code Plan agent, following `pbi-review`), read-only
- **Date:** 2026-09-11

**Verdict:** **CHANGES-REQUIRED**

**What the reviewer checked:**
- the exporter code;
- every real `out/` document: 16 sessions, 95 runs, 2 projects, 10 tabs, the catalogue and both status documents;
- the 40 `snapshot/` files;
- the existing test fixtures;
- the PBI files for PBI-005, 006, 008, 019 and 020.

The design, with the `doc` column as the source of truth, holds. The scope stays within PBI-003's areas, and PBI-019's concerns are excluded.

## Findings and dispositions (all applied in revision 2)

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| F-1 | High | `project.usage` is null for a project with no exported sessions (`export_sessions.py:524-527, 762`) | Applied: `object\|null`, required; empty-project case in T1 and T2 |
| F-2 | Medium | The run shape omits `agent`, written for lane `other` and read by the page | Applied: `agent` optional |
| F-3 | Medium | `min` (and `tok`) are always ints | Applied: typed `int`; A-3 resolved |
| F-4 | Medium | The required/optional split is looser than what the exporter writes; session `start`/`last` can be null | Applied: always-written fields are required; session `start`/`last` are `str\|null` |
| F-5 | Medium | The last-refresh id doesn't match its store path; there is no record-to-store-path mapping; the `tabs` table name collides | Applied: `COLLECTION` and `store_path` (§3.3); id `lastRefresh`; table `project_tabs` |
| F-6 | Medium | FR-100's "both adapters" had no mechanism | Applied: declarative, JSON-serialisable `SHAPES`; §1 states how the adapters use it |
| F-7 | Medium | AC-69 overstated; no disposition for PBI-003's AC-69 | Applied: "contributes via AC-D2; verified in PBI-005" |
| F-8 | Medium | Migrations handed to PBI-019, which cannot edit `local/schema*` | Applied: later changes need a PBI with `local/schema*`; `sessions(last)` index added |
| F-9 | Medium | T2 cases unnamed; status documents not covered | Applied: required T2 cases listed; `refresh.plan` covers status; `data_dir` injection; `HAS_GIT` skip |
| F-10 | Low | `__init__.py` wrongly said to match `local/records*` | Applied: no packages |
| F-11 | Low | Circular import risk | Applied: one-way imports |
| F-12 | Low | `runs.manual` enums are free text in the config | Applied: enums strict; decision handed to PBI-019; PBI-001 note |
| F-13 | Low | The tab-name enum can't be checked by `validate` | Applied: id forms checked in `store_path`/`to_row` (T4) |
| F-14 | Low | `create_schema` hardening | Applied: heal on version 0 or 1; one transaction; `allow_nan=False` |
| F-15 | Info | No `answers` table | Applied: T3 asserts its absence |

## Assumption dispositions

- **A-1:** RESOLVED (no packages).
- **A-2:** default accepted (a chore PR adds `local` to `[test_commands]` before PBI-019 or PBI-005 starts).
- **A-3:** RESOLVED (ints).
- **A-4:** RESOLVED (one global record).
- **A-5:** RESOLVED (`doc` is the source of truth).

None of these needs a human decision.
