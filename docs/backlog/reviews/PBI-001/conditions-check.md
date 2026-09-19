# PBI-001: orchestrator check of the round-2 conditions

**Date:** 2026-09-11.
**Gate:** code review, round 2 of 2 (`findings-r2.json`, GO-WITH-CONDITIONS).
**The reviewer's instruction:** "The orchestrator can check them without another full review round."
**The writer's fixes:** `change-report-r3.json` (DONE), in the uncommitted worktree tree on `d9de491`.

These are independent probes, run with `scratchpad/verify001/probe.py`. Each one imports the worktree's exporters and the `origin/main` copies of `export_sessions.py`, `export_board.py` and `board_config.py` in separate processes.

| Finding | Check | Result |
|---|---|---|
| CR-PBI001-05 (MEDIUM, condition) | `verdict_of(text, "ver")` on the reviewer's 3 probe strings, plus the round-1 fallback headline and the JSON `outcome` case | all 5 give `fallback-declared`; `Outcome: Exercised` and `exercised: ran the two endpoints` give `exercised` |
| CR-PBI001-05, no regression | `verdict_of` on 14 texts × 8 non-verifier lanes (cr, plan, cw, tw, req, orch, human, other), worktree vs `origin/main` | 112 cases, 0 differ |
| CR-PBI001-06 (MEDIUM, condition) | `board_config.manual()` on the real `board.config.json` with its first row's id replaced | refused: `d:x`, `a?b`, `a*b`, `a\|b`, `a"b`, `.x`, `x.`, `x `, `CON`, `con.json`, `LPT1`, `../x`, `a/b`, empty, `..`. Real ids `orch-adrs-spec` and `orch-toolchain` still accepted |
| CR-PBI001-07 (LOW) | `later_items()` on both real specs, worktree vs `origin/main` | identical: dispatch-board 9 ideas (worktree spec) and 10 (main checkout spec); platform-catalogue 0 in both of its spec files |

**Result:** both conditions (05, 06) and the low finding (07) are applied and verified, so the code-review gate is passed as GO-WITH-CONDITIONS with every condition applied.

**Disclosed and accepted as follow-ups:**
- the negation list (the reviewer judged it non-blocking);
- Windows device names with superscript digits;
- the cosmetic tier-1 negation window.
