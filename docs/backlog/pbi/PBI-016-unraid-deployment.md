---
id: PBI-016
title: "Unraid deployment: collector upload and ingest endpoint with a secret from the environment, rejecting answers, and a container definition (FR-89, FR-134, AC-71, AC-72)"
status: Later
change_class: standard
depends_on: [PBI-005, PBI-007]
allowed_areas: ["local/server*", "local/collector*", "local/deploy/**", "local/tests/**", "README.md"]
blocked_areas: ["site/**"]
conflict_group: local-app
conflict_risk: Low
requires_spec: false
requires_external_review: true
pr_required: true
merge_allowed_by_agent: false
---

# PBI-016 — Unraid deployment: collector upload and ingest endpoint with a secret from the environment, rejecting answers, and a container definition (FR-89, FR-134, AC-71, AC-72)

---

> **Moved to Later on 2026-09-11 by the owner** ("Move PBI16 to later"). This is no longer a planned work item: it is listed under the spec's Future iterations and shown in the Backlog tab's Later group. Revive it with a fresh promotion, and check rows 6, 7 and 24 of the parent spec when you do.

## Description

Unraid deployment: collector upload and ingest endpoint with a secret from the environment, rejecting answers, and a container definition (FR-89, FR-134, AC-71, AC-72). Decomposed from the approved solution spec at the plan gate on 2026-09-11.

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 5, approved)

**Areas and design notes from the parent spec:**

allowed `local/server*`, `local/collector*` (the upload half of FR-89), `local/deploy/**`, `local/tests/**`, `README.md`; blocked `site/**`.
- The shared secret is read from an environment variable or a git-ignored file, on both the collector and the server, never from `board.config.json`.
- The ingest endpoint rejects answer records (FR-134, AC-88).
- The Host allow-list is extended to the Unraid server's configured LAN hostname and address (row 7).
- No answers endpoint exists on the LAN.

---

## Acceptance criteria

**From the PRD** (`docs/prd/dispatch-board.md` section 7), matched to FR-89, FR-134:

- [ ] **AC-71** When the Unraid container's volume mapping is inspected, the local database shall be mapped to a path on the Unraid server's own storage, not to a mounted SMB or NFS share. *(NFR-20, C-14; inspection.)*
- [ ] **AC-72** When the collector on the PC records a new run in the Unraid deployment, the page served from the Unraid server shall show that run within 10 minutes. *(FR-89, NFR-18; demonstration.)*
- [ ] **AC-88** When an ingest request carries an answer record, the local server shall reject it, and the data snapshot shall contain no answer from that request. *(FR-134.)*
- [ ] Worker close-out: both suites green on the head commit (`python -m unittest discover -s tests`, `node tests/page.test.mjs`); code-review gate passed (`review-agents:code-reviewer` GO).

---

## Evidence

- (written at close-out)

---

## Notes

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO. `requires_external_review: true`: the owner must explicitly approve ("approve" / "proceed" / "go ahead") before implementation begins.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | pending | |
| External-review gate | true | pending | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
| BOARD-tidy gate | always | pending | |
