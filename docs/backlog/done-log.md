# Done log — dispatch-board

<!-- On-demand archive of completed-PBI evidence. NEVER loaded at session start; the BOARD ## Done
     index anchors here by ID. One ## <PBI-ID> section per completed PBI. -->
## PBI-030
- title: Sessions link to a project automatically from the files they edit
- PR: https://github.com/jdk-official/dispatch-board/pull/48 · merge: `fc1ad09` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: exporters/export_sessions.py, exporters/board_config.py, exporters/derive.py, tests/test_export_sessions.py, tests/test_derive.py, local/collector.py, local/tests/**
- evidence: Canonical run bound to e2b8776: 483/140/439. Accounted code-review-r1 GO, 1 Low follow-up. Real-transcript comparison: 260 runs match. Handover docs/backlog/handovers/PBI-030.md
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Sessions link to a project from the files they edit; not sticky.

## PBI-010
- title: Work-item status derived from runs, shown beside the hand-kept state during a shadow period (feature 4, FR-113)
- PR: https://github.com/jdk-official/dispatch-board/pull/46 · merge: `f4e92ed` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: exporters/**, tests/test_*.py, site/**, tests/page.test.mjs, projects/**
- evidence: Canonical run bound to 76030d8: 441/140/430. Accounted code-review-r1 GO, 2 Low follow-ups into PBI-030 (owner). Page view hidden at the owner's choice. Handover docs/backlog/handovers/PBI-010.md
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Derived work-item state exported; no page view; switch stays the owner's.

## PBI-007
- title: Log-on start through Task Scheduler and the on-PC deployment end to end (FR-90, FR-91, NFR-17, NFR-18, NFR-21)
- PR: https://github.com/jdk-official/dispatch-board/pull/28 · merge: `7c6bcb6` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: local/deploy/**, local/tests/**, README.md, CLAUDE.md
- evidence: AC-65 demonstrated by the owner's log-on 2026-09-19 19:26 local: Task Scheduler started collector and server, first pass 27 s later, 6 sessions served. AC-68 demonstrated 2026-09-19; AC-70 by inspection test; AC-72 deferred to PBI-016 by the owner. Handover docs/backlog/handovers/PBI-007.md
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. The board starts at log-on with no Claude session. Follow-up PBI-040: a duplicate collector instance at log-on.

## PBI-037
- title: Retire the v1 artifact and its refresher: final store export, final status message, loop stopped, procedures marked retired (S-40)
- PR: https://github.com/jdk-official/dispatch-board/pull/42 · merge: `85654f8` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: docs/backlog/evidence/**, snapshot/**, CLAUDE.md, README.md
- evidence: T4 evidence and final snapshot committed before the owner-approved final write (meta/status v56, status/dispatch-board v104). Canonical run bound to 13e23ce: 412/139/430. Accounted code-review-r1 GO, 0 findings. Handover docs/backlog/handovers/PBI-037.md
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. The v1 artifact is frozen; its refresh and publish procedures are retired.

## PBI-029
- title: No console windows from the scheduled collector
- PR: https://github.com/jdk-official/dispatch-board/pull/35 · merge: `8bd2621` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: local/tabs.py, exporters/export_board.py, local/tests/**, tests/test_export_board.py
- evidence: Canonical run bound to a9985a7: 826/0. Re-run on 8bd2621: backend 410 OK, page 139, local 430 OK. Accounted r1-r3 GO, 0 findings (r3 under the owner's extension). Handover docs/backlog/handovers/PBI-029.md
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Git children launch with CREATE_NO_WINDOW on Windows; proved under a real pythonw.exe parent.

## PBI-012
- title: Test and coverage trend, cost per work item and per agent type (features 5 and 7, FR-114–FR-116, FR-119, FR-120)
- PR: https://github.com/jdk-official/dispatch-board/pull/34 · merge: `312e2f5` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: exporters/**, tests/test_*.py, site/**, tests/page.test.mjs
- evidence: Canonical run bound to 51acfa5: 823/0. Re-run on 8bd2621: backend 410 OK, page 139 passed. Accounted code-review-r1 GO, 1 Low (CR-012-1, follow-up chore). Handover docs/backlog/handovers/PBI-012.md
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Runs carry stated tests and coverage; Dispatch charts both; usage shows cost per work item and per agent type.

## PBI-028
- title: Local record shapes name the session's waiting list and check a run's files are strings
- PR: https://github.com/jdk-official/dispatch-board/pull/31 · merge: `f7b21f9` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: local/records*, local/records.shapes.json, local/tests/**
- evidence: Canonical run via round_close bound to 7debcf0: backend 396, local 426, page exit 0 (131). Accounted code-review-r1 GO, 0 findings; reviewer validated the owner's real board.db and 7 real waiting objects. Handover docs/backlog/handovers/PBI-028.md
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Session shape names waiting; run files typed as strings; grammar gains scalar list_of and an object form. Closes PBI-009 spec row 3 and PBI-027's review follow-up.

## PBI-009
- title: 'Waiting on you' panel: detectors for pending questions, idle-after-asking and permission refusals (feature 2, FR-106–FR-110)
- PR: https://github.com/jdk-official/dispatch-board/pull/29 · merge: `25156c9` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: exporters/**, tests/test_*.py, site/**, tests/page.test.mjs
- spec: docs/backlog/specs/pbi-009-waiting-on-you.md revision 3
- evidence: Canonical run via round_close bound to 0ba49a2: backend 396, local 413, page exit 0 (131). Accounted review, allowance 2 used: r1 GO-WITH-CONDITIONS (CR-009-1 applied), r2 GO. W-14 approved by the owner on docs/backlog/evidence/PBI-009/. Handover docs/backlog/handovers/PBI-009.md
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Waiting-on-you panel: D1 structured question, D2 idle prose question (on), D3 refusals from toolDenialKind (all three kinds), D4 plan gate; 48-hour bound, cap 5 with overflow. CR-009-1 caught Claude Code's own compaction summaries and interrupt marker counting as the owner, which erased user-rejected refusals; fixed and checked on 24 real transcripts. PARSER_VERSION 7 to 8.

## PBI-027
- title: Local collector publishes a run's files relative to the repository, so the local app matches the board
- PR: https://github.com/jdk-official/dispatch-board/pull/27 · merge: `941ac4b` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: local/collector*, local/tests/**, local/records*, local/records.shapes.json
- evidence: Canonical run via round_close bound to 5ad02c8: backend 360, local 306, page exit 0 (121). Accounted dispatch code-review-r1 GO, 0 findings; evidence validation PASS at pre-review, gate-complete, pre-push (docs/backlog/reviews/PBI-027/). Handover docs/backlog/handovers/PBI-027.md
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. The collector passes each run's repoPath, so local files equal the board's; the run shape names files and findings. First PBI under bounded review accounting: an earlier pre-accounting review is logged as an event, and the owner chose a live re-review. Unblocks PBI-007.

## PBI-014
- title: Run detail (feature 8, FR-121)
- PR: https://github.com/jdk-official/dispatch-board/pull/24 · merge: `4bbbad8` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: site/**, tests/page.test.mjs, exporters/**, tests/test_*.py
- evidence: Suites on merged head 4bbbad8: tests 360, page.test.mjs 121, local/tests 304, all OK; canonical run bound to 123a61c. Code review round 1 NO-GO (1 High, 2 Medium, 3 Low), fixed test-first; round 2 GO-WITH-CONDITIONS (3 Medium, 1 Low), all applied (docs/backlog/reviews/PBI-014/). AC-82 demonstration and NFR-22 visual confirmation: docs/backlog/evidence/PBI-014/ (four PNGs, both themes), approved by the owner 2026-09-19 ("ok, approved"). Handover docs/backlog/handovers/PBI-014.md
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Picking a run on the Dispatch tab opens its detail: verdict summary, the round's own findings, files edited (repo-relative; unplaceable paths as …/name), duration. PARSER_VERSION 6 to 7. Round 1 disproved a builder claim that files touched was undeliverable. Follow-ups: PBI-027 (local collector omits the repo; PBI-007 depends on it), CLAUDE.md docs chore merged 47f8c13 (#25). Close-out waited six days on the owner-verified criteria; the rendered-screenshot route cleared it in one approval.

## PBI-025
- title: Local tab and status records: the collector writes each project's tabs and status into the local database
- PR: https://github.com/jdk-official/dispatch-board/pull/23 · merge: `560e296` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: local/tabs*, local/collector*, local/tests/**, exporters/derive.py, exporters/export_board.py, tests/test_derive.py, tests/test_export_board.py, board.config.json, exporters/board_config.py
- spec: docs/backlog/specs/pbi-025-local-tabs.md revision 4
- evidence: Suites on merged head 560e296: tests 345, page.test.mjs 111, local/tests 304, all OK, 0 skipped (baseline 334/111/265). Canonical run bound to 3345bca after rebasing onto 860144d. T-1 by test_tabs_equivalence.TabEquivalence; T-2 by test_tabs.Carry.test_the_full_carry_cycle; T-3 by test_tabs.Status (8) and StatusEquivalence (3); T-4 by test_tabs.Shapes; T-5 by test_tabs.NoNetwork, re-probed by the reviewer as 12 subprocesses all git, no gh or curl; T-6 by GitTabUnchanged and SpecTabBytes, with the byte fixture confirmed genuinely pre-move by running it green against a clean git archive of the base tree.
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Spec gate 2 rounds; code review round 1 GO-WITH-CONDITIONS (1 Medium, 1 Low, both applied) then round 2 GO with zero findings. The spec gate caught a data-loss bug before any code existed (F-2): projectTabs has two writers, so deriving the local owned-tabs set from records.TAB_NAMES would have deleted the findings ledger every 60-second pass. The code review found the spec itself wrong on tabs.carry - the literal wording deletes a carried record on the third pass - so the spec was amended to revision 4 to match the correct build. It also found the spec gate's UnicodeDecodeError-subclasses-ValueError hole repeated on the git path, where one project's non-UTF-8 output would have failed every pass indefinitely. Completes the local-first path: collector to SQLite to server to page. Known gap by design: pulls is excluded locally, so the local GitHub tab carries no pull requests.

## PBI-006
- title: Page data-adapter seam: store adapter and local API adapter (FR-97-FR-99)
- PR: https://github.com/jdk-official/dispatch-board/pull/21 · merge: `10e6659` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: site/**, tests/page.test.mjs
- evidence: Suites on merged head 10e6659: tests 334, page.test.mjs 111, local/tests 265, all OK, 0 skipped (page checks 99 to 111 across two rounds). Canonical run bound to 4d0db2d, re-run after rebasing onto 5baa922 so it attests the tree that merged. AC-73 pinned on both halves; FR-97 by a ten-panel deep-equal between the adapters whose fixture now leaves no panel empty on either side; FR-98/FR-99 by the marker-selection checks. First end-to-end exercise of the local-first system: a real local/server.py over a real SQLite database driven by the page, with PBI-005's spec-gate S-4 finding confirmed to hold across the seam (reset carries id, server takes the larger of since/Last-Event-ID, no reconnect loop).
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Code review round 1 GO-WITH-CONDITIONS (1 Medium, 5 Low), all six applied; round 2 GO with zero findings. The Medium was about evidence rather than code: the equivalence fixture left five of ten panels empty on both sides, so the PBI's strongest claim partly compared emptiness to emptiness; replaying it confirms six came up empty. Two of the Lows were quiet-wrongness bugs: a 200 with a non-snapshot body silently drew an empty board, and a marker missing its events URL opened undefined?since=N. Round 2 verified adversarially: 19 hostile URLs against the new same-origin check (refusing the userinfo trick, the 8765.evil.test prefix lookalike and all three backslash-to-another-host forms), a forced throw inside the render hold proving the finally releases, and an 18-mutant sweep killing the builder's 8/8 plus 5 more. The published artifact still runs the pre-PBI-006 page; republishing is a separate step.

## PBI-026
- title: Local record shapes accept the findings tab, so the local app can hold what the findings ledger publishes
- PR: https://github.com/jdk-official/dispatch-board/pull/20 · merge: `5baa922` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: local/records*, local/records.shapes.json, local/tests/**
- evidence: Suites on merged head 5baa922: tests 334, page.test.mjs 99, local/tests 265, all OK, 0 skipped (baseline 334/99/261, +4). Canonical run bound to b185574, validated. R-3 pinned by ConformanceFindings.test_a_findings_tab_was_written_and_conforms, which drives the real export_sessions.main so projectTabs/alpha.findings.json is produced by the exporter, not hand-built; mutation-verified red before the fix (stashing records.py fails 3 of 4 new tests). Validator widening reviewed as such: fullmatch verified at the call site, adversarial id sweep accepted only the one new form and rejected alpha.findings.git, alpha.findingsX, alpha.spec|findings, al.pha.findings, alpha..findings, trailing newline/space/NUL, alpha.FINDINGS, 101 chars.
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Code review GO at round 1 (0 Critical, 0 High, 0 Medium, 2 Low as follow-ups). Criterion R-1 named local/records.shapes.json as a file that must change; it encodes no tab names at all, so that half was satisfiable only vacuously and the criterion was corrected at close-out rather than ticked. This widening created a cross-PBI hazard caught at PBI-025's spec gate before either built: projectTabs has two writers (export_board owns the five suffixes, export_sessions owns findings), so deriving a tabs-this-pass-owns set from records.TAB_NAMES would have deleted the local findings record every 60-second collector pass. Fixed in PBI-025 revision 2, finding F-2.

## PBI-005
- title: Local server: page, data snapshot, live push, 127.0.0.1 binding, Host and Origin checks, network-path guard (FR-92-FR-94, FR-96)
- PR: https://github.com/jdk-official/dispatch-board/pull/19 · merge: `3e3ec44` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: local/server*, local/tests/**, board.config.json, exporters/board_config.py
- spec: docs/backlog/specs/pbi-005-local-server.md revision 2
- evidence: Suites on merged head 3e3ec44: tests 334, page.test.mjs 99, local/tests 261, all OK, 0 skipped (local suite grew 194 to 261). Canonical run bound to 270f2de, re-run after rebasing onto main a23afd8 so it attests the tree that merged. AC-67 pinned by NetworkGuard.test_unc_path_refuses_at_start_exits_2_no_socket_no_file_created (assertions made concrete after round 1 found them absent and vacuous); AC-68 server-level leg by Live.test_change_delivered_within_three_poll_intervals (the in-browser demonstration half is PBI-007's per spec sections 7 and 10 and is NOT claimed here); AC-69 by the snapshot tests plus a by-hand run returning HTTP 200, 3 records, skipped 0. Security surface pinned: 127.0.0.1/AF_INET with allow_reuse_address=False, the six-method funnel, one plain shape over all eight refusals with no echo of Host/Origin/method/request line, query_only=1 with file bytes/mtime/data_version/sqlite_master unchanged, AC-SV7 clean on snapshot and stream, no reset loop.
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. Code review round 1 NO-GO (1 High, 3 Medium, 7 Low, 1 Info), round 2 GO. The High was a test that proved nothing: test_no_client_can_stall_another read as proof of AC-SV10 but the stalled client kept draining into the socket send buffer, so instrumenting queue.Queue.put_nowait recorded 0 queue.Full events and the whole drop path was untested. Fixed by forcing overflow, not by softening the criterion; round 2 re-measured 2 events and an unbounded queue fails both tests. A real race was also fixed (Hub.register reused a watcher whose stop Event was already set, leaving live push silently dead for a client connecting in that window), and the repaired AC-SV2 test surfaced a defect neither round had found (CPython leaves request_version at HTTP/0.9 during send_error, suppressing the status line and every header on the 505). A blocked-area breaker fired mid-build: the PBI granted exporters/board_config.py in allowed_areas while blocked_areas held exporters/**, and blocked wins; the owner chose to narrow the block, widening no surface.

## PBI-011
- title: Review findings ledger (feature 3, FR-111, FR-112)
- PR: https://github.com/jdk-official/dispatch-board/pull/18 · merge: `a23afd8` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: exporters/**, tests/test_*.py, site/**, tests/page.test.mjs
- evidence: Suites on merged head a23afd8: tests 334, page.test.mjs 99, local/tests 194, all OK (baseline 307/96/194); canonical run bound to 3538b12, run-report validated. AC-77 pinned by a named page check plus test_derive.FindingsDoc.test_ac77_two_rounds_one_finding_still_open and test_export_sessions.Findings.test_ac77_two_rounds_open_and_resolved. Code review round 1 NO-GO (1 High, 5 Medium, 2 Low), all fixed test-first; round 2 GO with 3 Lows as follow-ups.
- outcome: resolved_method=squash (declared) / observed_method=squash, level record. The review caught two defects that would have published false information: an un-bumped parser version replayed 43 cached review rows with no findings, and a round whose findings live in a file rather than the reply was treated as authoritative -- both would have shown never-fixed findings as Resolved. Follow-up PBI-026 is on the BOARD: local/records.py TAB_NAMES does not yet accept a findings tab, so the local app cannot hold this document.

## PBI-008
- title: Stale-board warning: 'data as of' header (feature 1; FR-103 refresher half, FR-104, FR-105)
- PR: https://github.com/jdk-official/dispatch-board/pull/16 · merge: `f2e58e6` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: exporters/refresh.py, tests/test_refresh.py, site/**, tests/page.test.mjs, local/tests/test_conformance.py (added with the owner's approval)
- evidence: Code review round 2 GO, 2 Low recorded (findings.json; round 1 GO-WITH-CONDITIONS in findings-r1.json, all four fixed test-first, the strengthened page check confirmed to fail against the defect it pins); run-report bound to bd280d5 (307/96/90 PASS); cell-report CELL-DONE; suites 307/96/194 on merged main f2e58e6; handover docs/backlog/handovers/PBI-008.md
- outcome: Every refresh plan carries one set of meta/lastRefresh (writer 'refresher'), never bumping a project's status, never deleted, never counted by the mass-delete guard; the page header shows 'data as of <time>', amber with 'stale' past 20 minutes, silent when the record is absent or unreadable. A tick now always has at least one write, so refresh.py never prints 'nothing to push' again: CLAUDE.md's procedure, its store-path table and PRD FR-46 need a docs chore. Round 1 stopped at a blocked-area breaker, cleared by the owner widening the scope to local/tests/test_conformance.py. Unblocks the page group. Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-019
- title: Collector: incremental transcript and catalogue reads into SQLite, mass-delete guard, network-path guard (FR-86–FR-88; FR-103 collector half)
- PR: https://github.com/jdk-official/dispatch-board/pull/15 · merge: `b23df89` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: local/collector*, local/db*, local/tests/**, board.config.json, exporters/board_config.py
- spec: docs/backlog/specs/pbi-019-collector.md (revision 3)
- evidence: Spec gate 3 rounds (spec-review-r1..r3.md); code review round 2 GO (findings.json; round 1 NO-GO in findings-r1.json, all five fixed test-first); run-report bound to d1e9d02 (300/89/194 PASS); cell-report CELL-DONE; suites 307/96/194 on merged main f2e58e6; handover docs/backlog/handovers/PBI-019.md
- outcome: The collector reads each transcript from where it stopped (AC-63) and derives records equal to the session exporter's through the shared derive module (AC-64); local/db.py opens the database in WAL mode, refuses network paths (AC-115) and foreign files, and signals changes; the mass-delete guard is decided before any write (AC-119) and unlinked sessions are pruned by age (AC-120, AC-121). The first push was refused by the secret scan on a made-up folder path in a test constant; renamed with the owner's approval. Unblocks PBI-005, PBI-006 and PBI-025. Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-002
- title: Page fixes: FR-83 live-state tile, stale-tab callout, token relabel, design-rule deviations, blank-load investigation (FR-85)
- PR: https://github.com/jdk-official/dispatch-board/pull/12 · merge: `049f27e` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: site/**, tests/page.test.mjs
- evidence: Code review round 2 GO (docs/backlog/reviews/PBI-002/findings.json; round 1 GO-WITH-CONDITIONS in findings-r1.json, both Lows applied); run-report bound to d10aa68 (267/89/90 PASS); page suite 89/89 on merged main; page republished 2026-09-11; AC-62 live check stopped at 5 loads in Edge (4 drew, 1 empty at 5 s, undetermined) and was accepted by the owner, verbatim: 'accept but keep the test active'; handover docs/backlog/handovers/PBI-002.md
- outcome: Page fixes live: FR-83 idle tile, FR-191 carried-tab warning, row 13 design fixes, 'reported tokens' relabel, earlier reviews' page follow-ups, and the likely FR-85 blank-load cause (render-blocking font stylesheet). The AC-62 20-load live check stays active as a standing re-run; a load still blank at 12 s reopens FR-85. Unblocks the page group (PBI-008 to PBI-012, PBI-020). Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-004
- title: Shared derivation module: extract the exporters' parsing and derivation into an importable module, behaviour unchanged
- PR: https://github.com/jdk-official/dispatch-board/pull/14 · merge: `d10d9e6` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: exporters/**, tests/test_*.py
- evidence: Code review round 2 GO (docs/backlog/reviews/PBI-004/findings.json; round 1 GO-WITH-CONDITIONS in findings-r1.json: one Medium, returned documents shared live state, fixed test-first, two Lows applied); byte-identical before/after on frozen real data (157 files, 0 differences); run-report bound to 333361b (300/89/90 PASS); cell-report CELL-DONE; suites 300/89/90 OK on merged main d10d9e6; real-data refresh with the new exporters changed no session, run, project, catalogue or tab; handover docs/backlog/handovers/PBI-004.md
- outcome: exporters/derive.py holds the exporters' parsing and derivation: stdlib only, no I/O at import, functions take parsed records and text, returned documents are snapshots, so the collector (PBI-019) can import it; exporters' output unchanged. Unblocks PBI-019, PBI-005, PBI-008 to PBI-012 and PBI-020. Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-024
- title: Carried-tab marker: the board exporter writes carriedSince on a tab it keeps from an earlier export (FR-190)
- PR: https://github.com/jdk-official/dispatch-board/pull/13 · merge: `7bcd2fd` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: exporters/export_board.py, tests/test_export_board.py, CLAUDE.md, local/tests/test_conformance.py
- evidence: Code review round 2 GO (docs/backlog/reviews/PBI-024/findings.json; round 1 GO-WITH-CONDITIONS in findings-r1.json, all three applied); run-report bound to 749b4ae (274/68/90 PASS); suites 274/89/90 OK on merged main 049f27e; handover docs/backlog/handovers/PBI-024.md
- outcome: The board exporter stamps carriedSince on a project tab it keeps from an earlier export (FR-190 / AC-125); stable while carried, cleared on recovery, and a corrupt kept file no longer stops the export. The page's warning (FR-191) shipped in PBI-002. Unblocks PBI-004. Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-001
- title: Exporter hardening: FR-80–FR-82, FR-84, carried-tab marker, config type checks, refuse an answers collection (FR-133)
- PR: https://github.com/jdk-official/dispatch-board/pull/10 · merge: `d4023c6` · class: standard · tier: assisted · cell-verdict: GO-WITH-CONDITIONS
- allowed_areas: exporters/**, tests/test_*.py, CLAUDE.md
- evidence: docs/backlog/reviews/PBI-001/findings.json (round 2 GO-WITH-CONDITIONS; round 1 NO-GO fixed); conditions applied (change-report-r3.json) and checked (conditions-check.md); run-report bound to 9aeff32 (267/57/90 PASS); suites 267/68/90 OK on d4023c6; real-data refresh clean
- outcome: Exporters hardened: stuck running rows become killed, bad token counts skipped, config type errors exit 2, verifier outcomes recorded honestly, answers documents refused (C-16), credentials stripped from remotes, manual rows validated, Later lists take any marker. Not delivered: the carried-tab marker (FR-190 / AC-125), carried to a follow-up.

## PBI-013
- title: Usage limit forecast (feature 6, FR-117, FR-118)
- PR: https://github.com/jdk-official/dispatch-board/pull/9 · merge: `602eab9` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: site/**, tests/page.test.mjs
- evidence: docs/backlog/reviews/PBI-013/findings.json (round 2 GO; round 1 GO-WITH-CONDITIONS, all five applied); run-report bound to c54a119 (215/68/90 PASS); suites 215/68/90 OK on 602eab9; AC-80 checked against the live store's real data
- outcome: The board estimates the next usage-limit hit (mean gap from resumption to each hit, added to the latest reset), labelled an estimate, on the Claude usage tab and the Overview; 'no forecast: no limit hit recorded' when none is recorded. Page republished 2026-09-11. The method still needs the owner's record in PRD A-34.

## PBI-021
- title: Store leftovers clean-up: export the six unused documents to snapshot/, then delete them with the owner's explicit approval
- PR: https://github.com/jdk-official/dispatch-board/pull/2 · merge: `fd7b926` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: snapshot/**
- evidence: docs/backlog/reviews/PBI-021/findings.json (GO, no findings); AC-S1 to AC-S3 in docs/backlog/pbi/PBI-021-store-cleanup.md Evidence; owner delete approval recorded verbatim; suites 215 / 57 / 90 OK on 7fd96cb
- outcome: The six retired tabs/* documents were deleted from the store with the owner's verbatim approval on 2026-09-11; copies remain in snapshot/tabs/ (fd7b926); every project's tabs still render.

## PBI-003
- title: Record shapes and SQLite schema: session, run, project, tab, status, last-refresh and catalogue records (FR-100 except the answer record; FR-101 fields; FR-102)
- PR: https://github.com/jdk-official/dispatch-board/pull/7 · merge: `7fd96cb` · class: standard · tier: assisted · cell-verdict: GO
- allowed_areas: local/records*, local/schema*, local/tests/**
- spec: docs/backlog/specs/pbi-003-records-schema.md
- evidence: docs/backlog/reviews/PBI-003/findings.json (round 2 GO; round 1 NO-GO in findings-r1.json, all five findings fixed); suites 215 / 57 / 90 OK on 7fd96cb; AC-69 N/A for PBI-003, accepted by the owner 2026-09-11 (verified in PBI-005)
- outcome: local/records.py (SHAPES, validate, id forms, store_path, to_row/from_row), local/records.shapes.json and local/schema.py (7 tables, atomic idempotent create_schema), with 90 tests including conformance of every v1 exporter document. Unblocks PBI-019, PBI-005, PBI-006, PBI-008, PBI-014 and PBI-020 (with PBI-004 where needed).

## PBI-023
- title: Pull requests on the board: the GitHub tab lists each project's pull requests as links, and Needs attention flags the ones awaiting the owner's merge
- PR: https://github.com/jdk-official/dispatch-board/pull/6 · merge: `547b635` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: exporters/export_board.py, tests/test_export_board.py, site/**, tests/page.test.mjs, CLAUDE.md, README.md
- evidence: Code review GO-WITH-CONDITIONS, all three applied in e17006b (docs/backlog/reviews/PBI-023/findings.json); real gh run and Browser-pane check passed; unittest 215 OK and page 57/57 on 7fd96cb; handover docs/backlog/handovers/PBI-023.md
- outcome: GitHub tab lists each project's 20 most recently updated PRs as links; open PRs show in Needs attention as awaiting the owner's merge; gh failures never break the refresh. Live 2026-09-11 (pulls pushed, page republished). Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-022
- title: PRD re-baseline after project-first navigation and the plan-gate answers, with evidence for AC-84, AC-85 and AC-92
- PR: https://github.com/jdk-official/dispatch-board/pull/3 · merge: `3c520d6` · class: trivial · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: docs/prd/**, docs/backlog/evidence/**, docs/brief/raw-notes.md
- evidence: Code review GO-WITH-CONDITIONS, all four findings resolved in f3d80de (docs/backlog/reviews/PBI-022/findings.json); evidence docs/backlog/evidence/2026-09-11-prd-demonstrations.md; unittest 205 OK and page 49/49 on fd7b926; handover docs/backlog/handovers/PBI-022.md
- outcome: PRD revision 3 re-baselined to the current board; A-rows settled with ledger rows; D-21 supersedes D-1; D-19..D-26 recorded; brief says private; AC-84/85/92 demonstrated. Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-018
- title: Backlog shows future iterations: a "Later" group of idea cards read from the spec's Future iterations list
- PR: https://github.com/jdk-official/dispatch-board/pull/4 · merge: `25fa9e7` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: exporters/export_board.py, tests/test_export_board.py, site/**, tests/page.test.mjs, CLAUDE.md
- evidence: Code review GO (docs/backlog/reviews/PBI-018/findings.json; CR-018-01 LOW deferred to PBI-001); Browser-pane check: 9 idea cards, neutral --rule-2 bar, no errors; unittest 205 OK and page 49/49 on fd7b926; handover docs/backlog/handovers/PBI-018.md
- outcome: Backlog tab shows the spec's Future iterations as a Later group of 9 neutral idea cards; exporter adds backlog.later; never counted. Live 2026-09-11 (data pushed, page republished). Landing: resolved_method squash (declared) / observed_method squash; level record.

## PBI-017
- title: Agent catalogue tab: every catalogue agent and skill, grouped by purpose, with usage coverage across sessions and projects
- PR: https://github.com/jdk-official/dispatch-board/pull/1 · merge: `84fa3ee` · class: standard · tier: assisted · cell-verdict: CELL-DONE
- allowed_areas: exporters/**, tests/test_*.py, site/**, tests/page.test.mjs, board.config.json, exporters/board_config.py, CLAUDE.md, README.md
- spec: docs/backlog/specs/pbi-017-agent-catalogue.md
- evidence: Code review round 3 GO-WITH-CONDITIONS (docs/backlog/reviews/PBI-017/code-review-r1..r3.md); spec gate passed (pbi-017-agent-catalogue.md rev 3); on 84fa3ee unittest 197 OK and page suite 44/44; live board shipped 2026-09-11 (102 writes, no deletes); handover docs/backlog/handovers/PBI-017.md
- outcome: Agent catalogue tab live on the board. Follow-ups logged in PBI-001, PBI-002 and PBI-023. Landing: resolved_method squash (declared) / observed_method merge. VIOLATION: the landing diverged from the declared contract (the provider's default merge was used against the declared squash); recorded, not reverted; tree identical to the reviewed 942842b. close_check NOT_RUN (policy off; the tool expects PBI-017-*.md file names). No ledger row or worktree (PBI-017 predates both).

