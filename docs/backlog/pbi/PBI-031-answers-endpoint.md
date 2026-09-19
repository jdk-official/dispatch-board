---
id: PBI-031
title: "Answers endpoint on the local server: the answer record, a server-owned answers database, `POST /api/answers` with its checks, a nonce content-security policy, `local/answers.py list` and `verify`, and the `CLAUDE.md` answer and transcription rules (FR-95, FR-132, NFR-23)"
status: Proposed
change_class: standard
depends_on: [PBI-007]
allowed_areas: ["local/server*", "local/records*", "local/schema*", "local/answers*", "local/tests/**", "board.config.json", "exporters/board_config.py", "CLAUDE.md", "README.md"]
blocked_areas: ["site/**", "local/collector*", "local/db*", "exporters/derive.py", "exporters/export_*.py", "exporters/refresh.py"]
conflict_group: local-app
conflict_risk: High
requires_spec: true
requires_external_review: true
pr_required: true
merge_allowed_by_agent: false
---

# PBI-031 — Answers endpoint on the local server: the answer record, a server-owned answers database, `POST /api/answers` with its checks, a nonce content-security policy, `local/answers.py list` and `verify`, and the `CLAUDE.md` answer and transcription rules (FR-95, FR-132, NFR-23)

---

## Description

The local server gets its first write surface. An answer record is defined in its own registry, stored in a separate SQLite file that only the server writes, and accepted through `POST /api/answers` only when every check passes. The served page moves to a nonce content-security policy. `local/answers.py` lists the stored answers and verifies transcriptions. `CLAUDE.md` gains the answer and transcription rules. Decomposed from the approved solution spec at the plan gate on 2026-09-19 (track 7, G-8).

**Parent spec:** docs/backlog/specs/dispatch-board.md (revision 6, approved 2026-09-19)

**Areas and design notes from the parent spec:**

allowed `local/server*`, `local/records*` (with `local/records.shapes.json`), `local/schema*` (the answers database's DDL function only; `schema.DDL` unchanged), `local/answers*`, `local/tests/**`, `board.config.json` and `exporters/board_config.py` (the `local.answersPath` key only), `CLAUDE.md`, `README.md`. Blocked: `site/**`, `local/collector*`, `local/db*`, and every other `exporters/**` file. It also touches `config`, `exporters` and `docs`. It is a **security path**, a new write surface, registered in `security_paths` before promotion; tier 4 (record shapes).

**Promotion precondition.** A `chore-work` change adding `local/server*` and `local/answers*` to `security_paths` in `backlog-delivery.config` is merged before this PBI is promoted (spec Metadata; row 49).

**Decision record:** [ADR-0002](../../adr/0002-board-answers-count-as-the-owners.md): a board answer counts as the owner's, whoever gave it; answers are recorded by the local server on this PC only.

---

## Acceptance criteria

**Spec-owned criteria** (`docs/backlog/specs/dispatch-board.md`, revision 6, "PBI-031, answers endpoint"; rows 25–32, 41, 46, 49):

- [ ] **AC-A1** `local/records.py` defines the answer record in its own registry, `records.ANSWER_TABLES`, beside `records.TABLES`, so the board database gains no answers table. Every answer carries `id`, `type`, `projectId`, `note` (at most 2,000 characters, may be empty), `at`, `writer` (always `page`), `surface` (always `local`) and an optional `supersedes` (an earlier answer id). The one type defined here, `assumption`, carries `specPath`, `specRevision`, `row` (the ledger row number), `questionSha` (the SHA-256 of the row's question text as exported), `choice` (`accept` or `override`) and `answer` (at most 2,000 characters). `records.shapes.json` is regenerated. `records.store_path('answer', id)` returns `answers/<id>`, and `local/tests/test_records.py:187` and `:550`, which asserted the kind is unknown, are rewritten to test the new registry.
- [ ] **AC-A2** Answers are stored in their own SQLite file at `local.answersPath` (default `out/local/answers.db`). A new function in `local/schema.py` builds its DDL from `records.ANSWER_TABLES`. `schema.DDL` stays the board database's, so `local/tests/test_schema.py:88-93` (`test_no_answers_table`) passes unchanged. Only `local/server.py` creates or writes the answers file, and the network-path guard (FR-96) applies to it. The server still opens the board database read-only (`query_only=1`). An inspection test, in the style of `test_deploy_inspection.py`, shows the collector never opens the answers file. `local/answers.py` opens it read-only. Answers are never pruned.
- [ ] **AC-A3** `POST /api/answers` stores one answer only when every check passes:
  - Host is on the allow-list, and Origin is one of the two local origins, both as today;
  - `Content-Type` is `application/json`, and `Content-Length` is present and at most 16 KiB; a chunked body is refused before anything is read;
  - an `X-Dispatch-Token` header equals, compared in constant time, the token the server generated at start and injected into `__DISPATCH_LOCAL__`; a stale token's refusal line says to reload the page;
  - the body conforms to AC-A1;
  - `projectId` is the id of an entry in `projects[]` of `board.config.json`, and `specPath` equals that entry's `docs.spec`; the server takes paths from the config only, never from the body;
  - for `assumption`: the row exists in the project's current assumptions tab record, is awaiting the owner or ASSUMED, and its question hash matches.

  The server sets `id`, `at`, `writer` and `surface`, and refuses a body that supplies any of them. Success returns 201 with the record. Every failure returns the existing one-line 4xx shape, stores nothing and echoes nothing. A test covers each check.
- [ ] **AC-A4** Answers are append-only. The endpoint accepts no PUT, PATCH or DELETE, and a changed answer is a new record with `supersedes`.
- [ ] **AC-A5** The snapshot and the event stream carry answers under `answers/<id>`, and the server signals the event hub itself when it stores one. An `answers` table found in the *board* database stays invisible. With no stored answers the snapshot holds no `answers` key, so `local/tests/test_server.py:302-322` still holds; that test and `local/tests/test_server_live.py:58-72` are re-keyed to "no record read from the board database's `answers` table".
- [ ] **AC-A6** `local/answers.py` has two commands:
  - `list [--project ID]` prints the stored answers;
  - `verify <spec path>` checks every `answer:<id>` citation in the spec: the id exists, and its type, project, spec path, row, choice and answer text match the ledger row or Plan-gate line that cites it. It exits non-zero and names each mismatch. It checks that a transcription is faithful, not who gave the answer.
- [ ] **AC-A7** `server.log` carries one line for each accepted or refused answer: the id or the reason, and the row, never the text.
- [ ] **AC-A8** This PBI's spec gate includes a threat model of the endpoint (the `security-agents:threat-modeling` skill). It covers a malicious web page (cross-site requests and DNS rebinding), a script injected into the page, and a stale or leaked token. An agent on this PC answering as the owner is out of its scope (row 32). The code review includes `review-agents:api-reviewer`.
- [ ] **AC-A9** The served page runs under a content-security policy whose `script-src` is a per-start nonce, without `'unsafe-inline'`. `_wrap_page` adds the nonce to the marker script and to the page's one `<script>`. A test asserts that the header's `script-src` carries a `'nonce-…'` source and no `'unsafe-inline'`, that the nonce differs between two server starts, and that every `<script>` in the served page carries it.
- [ ] **AC-A10** `CLAUDE.md` "Answers are the owner's" says:
  - an answer given on the board counts as the owner's, whoever gave it (the owner, 2026-09-19: "Just procees as if it were me"; row 32);
  - agents still do not answer for the owner: no agent POSTs to `/api/answers`, drives the answer controls, opens the answers file, or cites an answer id it has not read with `local/answers.py`;
  - build, test, smoke-test and verify work on the answer controls runs a throwaway server on another port with a temporary `local.answersPath`, never port 8765 or the real `answers.db`;
  - the transcription procedure: cite `answer:<id>`, then run `verify` and quote its output.
- [ ] Worker close-out: tier 4 (record shapes; row 44). The canonical run of the three configured suites is green on the head commit, with `records.shapes.json` regenerated. The accounted code-review gate (`review-agents:code-reviewer` plus `review-agents:api-reviewer`) has passed.

---

## Evidence

- (written at close-out)

---

## Notes

**Authority.** Decomposed from the parent spec `docs/backlog/specs/dispatch-board.md`, revision 6. The owner approved it at the plan gate on 2026-09-19 with "Approve", answering the approval question that named commit `db14c0b` (spec blob `8fbdd3eba4a1042e2dfdbeb1689369eb015eb390`). The approval is recorded at `main` `e8f3f4e` (Plan-gate record). These criteria are the spec's own until the PRD re-baseline (row 47), which un-defers FR-95, FR-132, NFR-23 and AC-87 as amended.

**Merge.** `merge_allowed_by_agent: false`. The spec reserves this merge for the owner, because this PBI opens the local server's first write surface (Metadata; row 49).

**External review.** `requires_external_review: true`, for a new write surface. The owner must explicitly approve ("approve" / "proceed" / "go ahead") before implementation begins.

**Sequencing.** This is the only revision-6 PBI that can start once PBI-007 is Done and the `security_paths` chore has merged. It holds `local-app` at High, so no other local-app PBI runs beside it. Its overlap with PBI-030 on `exporters/board_config.py` is accepted by name: whichever of the two lands second rebases. Critical path to answering from the board: PBI-007 → PBI-031 → PBI-032.

Build per owner decision D-9: `engineering-agents:code-writer` under TDD, then `review-agents:code-reviewer` until GO.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | true | pending | per-PBI spec, with the threat model of AC-A8 |
| External-review gate | true | pending | |
| Code-review gate | true | pending | `review-agents:code-reviewer` and `review-agents:api-reviewer` |
| No-self-merge gate | always | pending | the owner merges |
| BOARD-tidy gate | always | pending | |
