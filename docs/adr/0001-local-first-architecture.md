---
id: ADR-0001
title: A local-first app, Python stdlib only, feeds the board without a Claude session
status: accepted  # the plan gate approved the spec (revision 5) on 2026-09-11
date: 2026-09-11
deciders: [owner, planner]
supersedes: []
superseded-by: null
resolves: spec row 8; PRD D-16, D-17, A-29
---

# 0001. A local-first app, Python stdlib only, feeds the board without a Claude session

**Date:** 2026-09-11
**Status:** accepted (plan gate, 2026-09-11)

## Context

- **How v1 stays live.** The board stays current only while a Claude Code session runs a refresher loop. That loop writes the artifact store through the Artifact tool, the only writer the store accepts (PRD C-1). It stops when that session closes and expires after 7 days (C-6), and every tick spends Claude usage.
- **What the owner decided.** Build a local version that needs no Claude session (D-16), which may later run on their Unraid server (D-17).
- **What the host can and can't reach.** Transcripts exist only on the PC running Claude Code (C-7, C-15). The artifact's content security policy blocks every external connection, so an artifact cannot read a local server (C-2, C-18).
- **Sources.** Parent spec: `docs/backlog/specs/dispatch-board.md` (revision 5, approved), Key decisions and row 8.

## Decision

- **The pipeline.** A collector on the PC reads transcripts incrementally and writes records to a SQLite database. A local web server serves the page, a data snapshot and a Server-Sent Events live-push stream.
- **The page.** It reads through one data-adapter interface: the store adapter when it runs as the artifact, the local API adapter when the local server serves it.
- **One definition of the records.** The record shapes and the SQLite schema are defined once, and the collector, the server and both adapters use them.
- **Derivation.** It lives in one shared module under `exporters/`, which the collector imports.
- **Technology.** The local app under `local/` is Python standard library only (`sqlite3` in WAL mode, `http.server`), and so is the shared derivation under `exporters/` that it imports.
- **Deployment.** It runs on the owner's PC first, started at log-on by Task Scheduler and bound to 127.0.0.1. Unraid is an optional later deployment of the server and database as a container, fed by the collector over the LAN. The database never sits on a network share.
- **Switch-over.** The v1 artifact and its refresher keep running until the owner retires them.

## Rationale

- **No Claude session.** It removes the dependency on an open Claude session and on Claude usage for refreshing (NFR-17).
- **Hosting later is a swap.** Defining the record shapes and the adapter seam now means a later host changes only storage and transport, not the page (D-16).
- **Unraid-ready.** SQLite runs unchanged in a container on Unraid (D-17).
- **No new dependencies.** Standard-library-only matches the existing exporters and tests (C-13), so there is nothing to install or audit. Server-Sent Events are one-way, which is all live push needs.

## Consequences

- **Easier:**
  - the board stays live across restarts, and with no session open;
  - freshness is no longer bound to a 10-minute loop;
  - a later host (Unraid, or Azure as a future iteration) reuses the records and the page.
- **Harder:**
  - there are two data paths until the owner retires the artifact refresher;
  - a long-lived local process needs its own guards: a mass-delete guard in the collector, and Host and Origin checks in the server (spec rows 24 and 7);
  - the standard library's HTTP server is basic, so throughput and features are limited to what one owner needs.
- **Reversal cost:** moving to a framework or another database later means reworking the collector, the server and the adapter (PBI-003, PBI-019, PBI-005, PBI-006). The record shapes and the page would largely survive.

## Alternatives considered

- **Keep only the artifact and its Claude refresher**: rejected, because the board dies with the session and costs Claude usage (D-16).
- **GitHub Pages plus an external database fed by hooks**: rejected for now, because it loses the private claude.ai page and means a page rewrite (D-3, C-2).
- **A web framework (FastAPI, Flask) or a JavaScript runtime server**: rejected, because it adds dependencies to install and audit when the standard library covers one user's needs (C-13).
- **SQLite on a network share, read by a server elsewhere**: rejected, because SQLite locking over SMB and NFS is unreliable (D-17, C-14).
