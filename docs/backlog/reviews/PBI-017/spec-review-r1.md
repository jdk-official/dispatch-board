# Spec-gate review, round 1 — PBI-017 per-PBI spec, revision 1

- **Gate:** spec gate (`requires_spec: true`)
- **Reviewer:** same-vendor subagent with a clean context (Claude Code Plan agent following `pbi-review`), read-only
- **Date:** 2026-09-11

**Verdict:** **CHANGES-REQUIRED**

**What was found sound:**
- **Coverage and scope:** it covers the parent's AC-C1 to AC-C7 and stays inside PBI-017's allowed areas.
- **Frontmatter:** all 51 files have single-line names and descriptions.
- **Agent ids:** the namespaced `agentType` values match entry ids exactly.
- **Installed-plugins file:** its shape is as the spec describes.
- **Page subscription:** consistent with how the page already subscribes.
- **Design rules:** respected.

## Findings and dispositions in revision 2

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| H1 | High | An agent's "last use" had no source: run docs carry no time field | Applied: subagent run docs also carry `start`; the latest `start` gives an agent's last use |
| H2 | High | The slash-command rule counted tag text found inside tool results, attachments and `isMeta` duplicates | Applied: only `type == "user"`, non-`isMeta`, string content beginning `<command-message>` or `<command-name>`; tool, attachment and system content is never scanned; a test for each exclusion |
| M1 | Medium | "First sentence" purposes run to 1459 characters | Applied: a defined sentence-end rule with `e.g.`/`i.e.` exceptions, capped at 120 characters on a word boundary; `purposeFull` expandable; tests for the edge cases |
| M2 | Medium | Bare-name skills were handled inconsistently | Applied: bare `Skill` ids match a single catalogue skill name, otherwise they go to "Outside the catalogue"; bare slash commands are not counted, documented as a limitation |
| M3 | Medium | An empty marketplace folder would blank the tab | Applied: no `plugins/` folder, or zero entries, keeps the last export |
| M4 | Medium | A malformed catalogue file could stop the whole refresh | Applied: per-file warnings and fallbacks; only a config type error exits 2 |
| L1 | Low | The config defaults contradicted the parent | Applied: `~` defaults through `expanduser`; exporter maps `ValueError` to exit 2 |
| L2 | Low | The CLI contract and the refresh docstring were not stated | Applied: `[out_dir]`; docstring update; a test for `export()` running three exporters |
| L3 | Low | The CLAUDE.md close-out was incomplete; no privacy line | Applied: the full list, including the privacy line and that `args` are never stored |
| L4 | Low | Empty `agentType`, and unvalidated skill ids | Applied: the key is omitted when empty; ids validated against `^[A-Za-z0-9_.:-]{1,100}$` |
| L5 | Low | The "N of M" denominator and the coverage caption were unstated | Applied: M counts all entries, with "K installed" alongside; caption added |
| L6 | Low | Where fixtures live was unstated | Applied: temporary folders only; every test passes its own `catalogue` config |
| L7 | Low | The one-time cost was understated | Applied: about 94 writes, and each project's "Updated" time moves once |
| I1–I6 | Info | Parsing, id alignment, installed-file shape, subscription, forked sessions, design | I1 (quote and block handling), I4 (tab in the `grp` group, `.empty` block) and I5 (forked sessions, in §7) applied; the rest need no action |
