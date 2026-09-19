---
id: PBI-040
title: "Only one collector runs at a time"
status: Proposed
change_class: standard
depends_on: []
allowed_areas: ["local/collector.py", "local/deploy/run_local.py", "local/tests/**"]
blocked_areas: ["local/server.py", "local/answers*", "exporters/**", "site/**"]
conflict_group: local-app
conflict_risk: Medium
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-040 — Only one collector runs at a time

---

## Description

At the owner's log-on on 2026-09-19, Task Scheduler started the collector at 19:26:35 and a second collector at 19:28:35. Both processes' parent was the Task Scheduler service (PID 4256), even though the task's `MultipleInstancesPolicy` is `IgnoreNew`. Task Scheduler history is disabled on this PC, so the cause is unproven. Two collectors then wrote `out/local/board.db` in interleaved passes. The collector is meant to be the database's only writer (`CLAUDE.md`, "The local app on this PC").

Whatever starts the second process, the collector should refuse to run beside another one. At start-up it takes an exclusive, OS-held lock (for example a lock file next to the database, opened with `msvcrt.locking` on Windows and `fcntl.flock` elsewhere). If the lock is held, it logs one line naming the reason and exits 0, so Task Scheduler's Last Run Result stays clean. The lock is released by the OS when the process dies, so a crash never leaves a stale lock.

---

## Acceptance criteria

- [ ] **S-1** A second collector started while one is running logs "collector: another collector is running (lock <path>); exiting" to its log and exits 0 without writing the database. A test starts two real processes and shows it.
- [ ] **S-2** After the first collector's process is killed, a new collector starts normally: no stale lock survives a crash. The test covers this.
- [ ] **S-3** `--once` runs honour the lock the same way.
- [ ] **S-4** The NFR-17 inspection test (`local/tests/test_deploy_inspection.py`) still passes. If the lock needs `msvcrt` or `fcntl`, the inspection's allow-list names them with the reason, and adds nothing else.
- [ ] Worker close-out: the three configured suites green on the head commit; accounted code-review gate passed.

---

## Evidence

- (written at close-out)

---

## Notes

Landed by intake 2026-09-19 from the owner's log-on demonstration of PBI-007 (AC-65), where the duplicate was observed. `merge_allowed_by_agent` is `true` under the owner's standing merge authorisation of 2026-09-12.

**Sequencing.** It edits `local/collector.py`, which PBI-030 (in progress) also edits, so it starts after PBI-030 merges. It is in the `local-app` group, so a High-risk `local-app` row (PBI-031) in flight also holds it.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | criteria in this PBI |
| External-review gate | false | n/a | |
| Code-review gate | true | pending | |
| No-self-merge gate | always | pending | |
