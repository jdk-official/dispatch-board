---
id: PBI-029
title: "No console windows from the scheduled collector: git runs without a window when the parent has no console"
status: Done
change_class: standard
depends_on: [PBI-007]
allowed_areas: ["exporters/export_board.py", "local/tabs.py", "local/collector.py", "local/server.py", "local/deploy/**", "local/tests/**", "tests/test_export_board.py"]
blocked_areas: ["site/**", "exporters/derive.py", "exporters/export_sessions.py", "local/records*", "local/schema*"]
conflict_group: exporters
conflict_risk: Medium
requires_spec: false
requires_external_review: false
pr_required: true
merge_allowed_by_agent: true
---

# PBI-029 — No console windows from the scheduled collector

---

## Description

A defect in the on-PC deployment (PBI-007), reported by the owner on 2026-09-19: "I think the scheduled task you created runs in the foreground."

The log-on tasks run `pythonw.exe`, so the interpreter opens no console of its own (verified in the registered task XML). But every collector pass runs `git` for each project's tabs (`local/tabs.py`, through `exporters/export_board.py`'s git helpers). A process with no console that starts a console program makes Windows open a new console window for each child, so windows appear and take focus about every 60 seconds. The fix is to launch those children with `CREATE_NO_WINDOW` on Windows.

**Areas:** the git call sites the collector and server reach (`exporters/export_board.py`, `local/tabs.py`, plus `local/collector.py` and `local/server.py` if they launch anything), and `local/deploy/**` and `local/tests/**` for the inspection test's hand-checked launch list. Blocked: `exporters/derive.py` and `exporters/export_sessions.py`, which PBI-012 is changing.

---

## Acceptance criteria

- [x] **N-1 Every child process the collector or server can start is launched without a window on Windows.** One shared helper supplies `creationflags=subprocess.CREATE_NO_WINDOW` on Windows and nothing elsewhere, and every launch site the collector and server reach uses it. The refresher's own launches (`exporters/refresh.py`) are out of scope: they run from an owner's terminal.
- [x] **N-2 Tested, and the tests bite.** A test shows the collector's git launches carry `CREATE_NO_WINDOW` on Windows, and that the flag is absent off Windows (by patching the platform check). It fails before the change.
- [x] **N-3 Exercised for real.** On this Windows machine, a test or evidence run starts the collector's tab pass under `pythonw.exe` and shows that no console window was created. For example, it enumerates top-level console windows (`ConsoleWindowClass`) before and after, or checks the child's `STARTUPINFO`, whichever the builder can make deterministic. The mechanism is stated in Evidence.
- [x] **N-4 Nothing is weakened.** The NFR-17 inspection test (`local/tests/test_deploy_inspection.py`) keeps every guard. If its hand-checked launch list changes, it changes only to name the new helper's site. All suites pass.
- [x] Worker close-out: the three configured suites green on the head commit; accounted code-review gate passed.

---

## Evidence

**Closed out 2026-09-19.** Merged as `8bd2621` (PR #35, squash; landing resolved squash (declared) / observed squash, one parent, level `record`).

- **N-1** — `exporters/export_board.py` `no_window_flags()` returns `{'creationflags': CREATE_NO_WINDOW}` on Windows and `{}` elsewhere; both git launches in `local/tabs.py` pass it.
- **N-2** — `local/tests/test_tabs.py` asserts every git child carries `CREATE_NO_WINDOW` on Windows and none off it (platform check patched); it failed before the change.
- **N-3** — `local/tests/test_no_console_window.py` launches a console-subsystem child (python.exe) from a real `pythonw.exe` parent through `no_window_flags()`; the child reports `GetConsoleWindow()` 0 with the flag and non-zero without it. Mechanism: the child's own console handle, not a mock. Both cases pass on this machine (re-run 2026-09-19).
- **N-4** — `local/tests/test_deploy_inspection.py` keeps every guard; its hand-checked list names the helper's sites only.
- **Close-out** — canonical run bound to `a9985a7`: 826 passed / 0 failed. Re-run on merged main `8bd2621`: backend 410 OK, page 139 passed, local 430 OK. Accounted review: `code-review-r1` GO, `code-review-r2` GO after an out-of-scope PBI file was dropped from the commit, and `code-review-r3` GO under the owner's +1 dispatch extension (`authorisation-ext-1-r1.md`). 0 findings.

---

## Notes

The owner asked for this "as a priority" (2026-09-19). **Owner authority:** `merge_allowed_by_agent` is `true` under the standing merge authorisation of 2026-09-12. The owner re-runs nothing after the merge: the tasks call the checkout's code, so the next start picks the fix up.

---

## Gate tracking

| Gate | Applicable | Status | Artifact / note |
|------|------------|--------|-----------------|
| Spec gate | false | n/a | |
| External-review gate | false | n/a | |
| Code-review gate | true | passed 2026-09-19 | Accounted r1–r3 GO, 0 findings; r3 under the owner's extension |
| No-self-merge gate | always | passed 2026-09-19 | PR #35 squash-merged `8bd2621` under the owner's standing merge authorisation |
| BOARD-tidy gate | always | passed 2026-09-19 | Done write, ledger deregistered |
