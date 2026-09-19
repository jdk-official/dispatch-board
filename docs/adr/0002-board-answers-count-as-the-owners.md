---
id: ADR-0002
title: Answers given on the board are recorded by the local server on this PC and count as the owner's, with no login
status: accepted  # the plan gate approved the spec (revision 6) on 2026-09-19
date: 2026-09-19
deciders: [owner, planner]
supersedes: []
superseded-by: null
resolves: spec rows 25, 26, 32, 34, 39 and 50; PRD C-17 (and, for the local page, FR-64 and FR-183)
---

# 0002. Answers given on the board are recorded by the local server on this PC and count as the owner's, with no login

**Date:** 2026-09-19
**Status:** accepted (plan gate, 2026-09-19)

## Context

- **What changed.** On 2026-09-19 the owner pulled "answering assumptions from the board" and "using answers for approvals" out of Future iterations (spec revision 6, G-8 and G-9). Until then answers stayed in chat, and the plan said no agent writes an answer (row 5, PRD C-16).
- **Why an ADR is required.** PRD C-17 requires an accepted ADR before the page may write, since answering reverses FR-64 (the page never writes) and FR-183 (no answers route) (row 39).
- **What no design without a login can do.** Nothing on this PC can tell the owner from an agent acting as the owner (row 26):
  - on the artifact's store, Claude writes with the owner's identity (PRD C-1), and a `{self}` rule binds only a viewer id that Claude shares;
  - on the local server, the Host and Origin checks read header values that any local process can send, and a token in the served page can be read with a GET;
  - an agent can also drive a browser on the page, edit the board database or stop the collector.
- **What the reviews showed.** Rounds 4 and 5 of the plan-gate review tried to make a transcript tripwire into a gate. Round 5 (PG6-r5-1 to PG6-r5-3) showed that the gate could not act in time and could be evaded by routes it cannot see.
- **The owner's answers** (spec, Assumptions & open questions, and the Plan-gate record), verbatim:
  - **Row 32.** Asked "Answering from the board: any agent on this PC can click the board or edit its database as if it were you. How should a board answer be trusted?", the owner answered: "Just procees as if it were me".
  - **Row 25.** Asked "Row 25: board answers only work on the board on this PC, with no answering away from it. Accept?", the owner answered: "Accept, this PC only (Recommended)".
  - **Row 34.** Asked "Row 34: does approving a plan on the board pass the plan gate by itself, or should it also need a one-line chat confirmation naming the answer's id?", the owner answered: "Board approval alone".
- **Sources.** Parent spec: `docs/backlog/specs/dispatch-board.md`, revision 6, approved by the owner on 2026-09-19 (Key decisions; rows 25, 26, 32, 34, 39 and 50; the Plan-gate record). The PBIs that build it are PBI-031 to PBI-035.

## Decision

- **Trust.** An answer given on the board counts as the owner's, whoever gave it. There is no login, account or passphrase. Every answer carries the constant `writer: "page"` and `surface: "local"`, which the server sets.
- **Where.** Answers are given only on the board served by the local server on this PC. The page POSTs to `/api/answers`, and the server stores the answer in its own SQLite file, which only the server writes. The artifact's store is not an answer surface.
- **Approvals.** A plan approval is bound to git's blob id of the committed spec the owner saw (row 50), and a conditions acceptance to one review run. A board plan approval passes the plan gate by itself, with no chat step.
- **Transcription.** No process writes an answer into a repo file. The planner or orchestrator transcribes it, citing `answer:<id>`, and `python local/answers.py verify <spec>` checks that the transcription is faithful. It does not check who gave the answer.
- **The tripwire is an audit mark, not a gate.** Answers that follow a tool call able to send one are marked "Possibly given by an agent" for the owner to read (PBI-033). The marks never decide whether an answer counts, and nobody clears them.
- **What still limits who writes.** Only the server's POST handler builds an answer. The collector never opens the answers file. `CLAUDE.md` still tells agents not to answer for the owner, and keeps build, test and smoke-test work off the owner's server and answers file. The server's cross-site defences stay in place (the Host allow-list, an exact Origin match, a JSON content type, a per-start token, a size limit and a nonce content-security policy). They guard against a malicious web page, not against an agent on this PC.

## Rationale

- **It is the owner's decision.** The owner chose to treat a board answer as theirs, knowing that any agent on this PC can give one (rows 32 and 34).
- **It is honest about what can be enforced.** Without a login, any gate on who answered can be evaded by an agent on this PC. A gate that only looks enforced would be read as a guarantee it cannot give. An audit mark claims only what it shows: what an agent that was not evading did.
- **The local app outlives the artifact.** The artifact is being retired (row 37), so an answer path built on its store would be removed with it. The store also cannot tell the owner from Claude, which writes as the owner (row 25).
- **Answers stay out of the board database.** A separate file keeps the collector as the only writer of the board database. It also keeps answers away from the collector's age pruning and mass-delete guard (row 28).

## Consequences

- **Easier:**
  - the owner answers assumption rows, approves a spec revision and accepts a review's conditions from the board, without typing into chat;
  - a plan gate no longer waits on a chat turn: the planner picks approvals up with `local/answers.py list`;
  - each approval is bound to the exact committed text or run it approves, so it cannot be reused for text the owner never saw;
  - PRD C-17 is met, so the local page may write answers.
- **Harder, and the honest costs:**
  - **Any agent on this PC can answer as the owner**, by clicking the board, by sending its own POST with the page's token, or by other routes. Its answer counts. Because a board plan approval passes the plan gate by itself, an agent that clicks *Approve* passes the gate that everything downstream builds on (row 34, **High**).
  - The audit sees only an agent that is not evading. It cannot see a URL built at run time, a script file written first, an edited transcript or board database, a session under `sessions.exclude`, a stopped collector, a script injected into the page, or a browser tab the tool call does not identify (AC-G5). An empty audit panel never means no agent answered.
  - `writer: "page"` satisfies NFR-23 to the letter but proves nothing about who clicked (row 30). There is no per-person identity.
  - The owner cannot answer away from this PC (row 25, **High**). The server listens on 127.0.0.1 only, and the artifact cannot reach it.
  - An untranscribed answer lives only in `out/local/answers.db`, which is not backed up. Its durable copy is its transcription in the repo (row 46).
- **Reversal cost:**
  - Going back to chat-only answers means removing the endpoint, the answers file and the page controls (PBI-031, PBI-032, PBI-034, PBI-035). The transcriptions already in specs stay valid.
  - Moving to authenticated answers needs a login on the local server, which rows 7 and 24 chose against. That change would supersede this ADR.
  - Remote answering would need a new host (the Unraid deployment or Azure, both in Future iterations), since the artifact's store is being retired.
- **Revisit when:**
  - the board becomes reachable from anywhere but this PC;
  - someone other than the owner uses this PC;
  - the answer audit marks an answer the owner did not give.

## Alternatives considered

The first four options were put to the owner with the row 32 question. The owner took none of them and answered "Just procees as if it were me"; each entry adds the planner's reason it would not have served. The fifth is the design that rounds 4 and 5 of the plan-gate review had in the draft. The last is row 25's choice of surface.

- **Board drafts, confirmed in chat.** A board answer would be a draft until the owner confirmed it in chat. Rejected: row 32 chose trust, and row 34 then removed the chat step for plan approvals too ("Board approval alone"). It would also leave chat as the only real gate, and a chat quote is transcribed by the planner, so it proves no more than a board answer does (round 5, PG6-r5-10).
- **A passphrase.** The owner would type a secret with each answer. Rejected: it is a login under another name, which rows 7 and 24 chose against and revision 6 keeps out of scope. It also protects nothing from an agent that can drive the browser while the owner types, or read the secret where it is stored.
- **Detection-only gating.** An answer would count only while the transcript tripwire had flagged nothing. Rejected: the detector runs on the collector's passes, so a forged answer can be honoured before the pass that would flag it. It can also be evaded by routes it never sees (round 5, PG6-r5-1 and PG6-r5-3).
- **Drop board answering.** Keep answers in chat, as row 5 had it. Rejected: the owner pulled answering from the board into revision 6 on 2026-09-19. It would also leave the plan gate waiting on a chat turn.
- **Durable alarms and an honour gate** (the draft in rounds 4 and 5). The tripwire's alarms would be durable records the collector never deletes. The owner would clear each alarm from the board. A board answer would be honoured only while no alarm was uncleared, and a plan approval would also need a chat confirmation. Rejected after round 5:
  - the honour rule had no freshness condition, so a plain `curl` forgery was honoured if it was checked before the collector's next pass (PG6-r5-1);
  - the tripwire could not see browser automation, which posts through the page itself (PG6-r5-2);
  - alarms could be deleted, or never raised, through calls it did not flag: editing `board.db`, excluding the session, rebuilding the database (PG6-r5-3).

  Hardening it would only make the gate harder to evade; without a login it cannot be closed. The owner's row 32 answer superseded it (Round-5 dispositions).
- **Answers on the artifact's store, or on both surfaces** (row 25). Rejected:
  - the store would need the `user` capability and an `answers/{self}` write rule, which binds only a viewer id that Claude shares;
  - the artifact is being retired (row 37);
  - "both" would double the surface for no gain.
