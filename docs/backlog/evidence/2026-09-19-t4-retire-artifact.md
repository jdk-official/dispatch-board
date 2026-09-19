# T4 — retiring the v1 artifact: same-day check, 2026-09-19

Recorded before any store write or loop change (PBI-037, AC-V1). The checks were run at about 18:00 local time.

## T4.1 — the local app is installed and serving

- PBI-007 is merged: PR #28, squash `7c6bcb6`.
- `python local/deploy/tasks.py status` shows both tasks registered and running:
  - `\Dispatch board\Collector`: Running.
  - `\Dispatch board\Local server`: Running.
- `out/local/logs/collector.log` holds 258 committed-pass lines dated 2026-09-19. The last one before this check:
  `2026-09-19T17:57:49 collector: 7 sessions (1 re-derived, 30259 bytes read), 247 runs, 2 projects, 10 tabs; 4 written, 0 deleted (0 by age) | 1.4s`
- AC-68 was demonstrated on 2026-09-19 on the installed deployment (docs/backlog/pbi/PBI-007-logon-start.md, Evidence). The page at http://127.0.0.1:8765 was loaded once and never reloaded, and it showed a run's new kind after a finish was appended to its transcript.

## T4.2 — nothing the owner uses exists only on the artifact

`node tests/page.test.mjs` on `main` at `daeb0b0` exited 0 with all 139 page checks passed. That includes the adapter deep-equal check "FR-97: the store adapter and the local API adapter render the same board from the same data, on a board where every panel has content".

## T4.3 — the owner accepts the loss

Row 37 asked: "retire the published claude.ai artifact after 30 days of reliable local running (no earlier than 2026-10-19), accepting there's then no board away from this PC?" The owner answered, verbatim: **"retire it now"** (2026-09-19).

The plan-gate approval of revision 6 ("Approve", commit `db14c0b`) stated that approving "freezes the published claude.ai page today (PBI-037)". The batch approval was "Approve batch, start 037". This is also PBI-037's external-review go-ahead.

All three hold, so the freeze may proceed today.
