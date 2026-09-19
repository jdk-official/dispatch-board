# Spec-gate review — PBI-009 "Waiting on you" (revision 1, round 1)

Reviewer: `pbi-review`, same-vendor-subagent tier (clean-context, read-only), 2026-09-12. Live tree at `560e296`. Saved verbatim by the orchestrator.

**Verdict: CHANGES-REQUIRED**

Citation integrity is excellent: I re-read and line-counted ~40 cited ranges (`derive.py`, `export_sessions.py`, `refresh.py`, `local/records.py`, `local/collector.py`, `site/index.html`, `tests/page.test.mjs`, `CLAUDE.md`, parent spec, PRD). **Zero drift.** The store design, the two-writer avoidance and the parser-version reasoning are all verified correct. What fails is not implementability — it is two load-bearing empirical claims about what the panel will actually contain.

## Findings

| id | Sev | Finding | Evidence | Required change |
|---|---|---|---|---|
| **F-1** | **High** | **D1 — the "high confidence, structural" detector — fires on 0 of 15 real transcripts.** Every `AskUserQuestion` in the corpus received a `tool_result` (12/15 sessions have asks, 36 asks, **0 unanswered**). §3.3 measures *occurrence* (13 of 15) but never measures the thing D1 detects. So §1.1's framing ("two of three detectors have crisp structured signals, only one is a genuine heuristic") is true of the *signals* and false of the *panel*: on measured data the question half of the panel is produced entirely by D2. This inverts owner-question 2 — disabling D2 makes the panel's question half permanently empty. | spec §3.3:141-146 vs the measurement below | Add the unanswered-rate measurement to §3.3; restate §9 row 2 as "D2 is the only question detector that fires on the measured corpus"; state D1 as a rare-but-high-value detector, not the primary one. |
| **F-2** | **High** | §9 row 1 justifies putting `user-rejected` to the owner on the premise that it "is the most common denial kind". Measured: `user-rejected` **1 of 11** denials; `automode-blocked` **8 of 11**. The premise is false and inverts the question's stakes — the noise risk in D3 sits in `automode-blocked`, which the spec lists without asking. | spec §9 row 1 (`pbi-009-waiting-on-you.md:496`); measurement below | Correct the frequency claim; ask the owner about `automode-blocked` (8/11) as well, or justify listing it unasked. |
| **F-3** | **Med** | **W-a is self-contradictory.** It defines `is_owner_message()` with two rules line 438 does not have (`isMeta` rejection; list-content-with-`text`-block acceptance), then asserts "a refactor with no behaviour change; the existing `first`/`firstPrompt` tests must pass untouched". Line 438 governs `state['first']` → `firstPrompt`. Accepting list content there changes `firstPrompt` for any session opening with a pasted attachment. T-12 and T-4 contradict each other. | `exporters/derive.py:438` (no `isMeta`, `str`-only); spec §4.1 W-a, T-4, T-12 | Either keep line 438's narrower inline test and make `is_owner_message()` a separate new predicate, or drop the "no behaviour change" claim and specify the new `firstPrompt` behaviour. |
| **F-4** | **Med** | **NFR-22 has no criterion and no verifying actor** — the identical gap the sibling review raised as PBI-020 F-5. The string "NFR-22" does not appear in the spec. W-12 covers the regex-checkable half (NFR-9/NFR-14); nothing covers NFR-13 judgement, legibility, dark/light, or NFR-22's own clause that `--human` is used **only** for waiting items and assumptions awaiting a human. W-13 names only test suites and the code-reviewer. | `docs/prd/dispatch-board.md:570`; `docs/backlog/specs/dispatch-board.md:216`; `docs/backlog/reviews/PBI-020/spec-review-r1.md:17` | Add criterion W-14: owner (or a rendered-screenshot evidence artefact under `docs/backlog/evidence/`) confirms the panel against `CLAUDE.md:131-139` and NFR-22, in both themes. Name the actor. |
| **F-5** | **Med** | **The §8.4 probe is vacuous.** `['an item waiting on you', /Waiting on you/]` matches the panel *title*, which §8.3 renders in the empty state too. The probe would pass on two identically empty panels — precisely the failure `tests/page.test.mjs:1461-1462` warns against. | `tests/page.test.mjs:1467-1470`; spec §8.4 step 2 | Probe item content, not the heading — e.g. the fixture's question text and `/Refused/`. |
| **F-6** | **Med** | **No age bound and no panel-level cap; the clearing rule does not clear an abandoned session.** Conditions 1–3 and 5 hold for 13 of 15 sampled sessions (all end on an assistant turn, all are idle past the 10-minute window), so condition 4 is D2's only discriminator. A D2 item on a session the owner silently walked away from persists for the full 7-day window; only typing into that dead session clears it. §7.3's cap is per session only. | `board.config.json:62` window 10 min, `sessions.days` 7; spec §7.2, §7.3 | Add a panel-level cap and/or an age bound, or state explicitly that items persist for the retention window and why that is acceptable. |
| **F-7** | **Low** | FR-108 makes idleness *the collector's* mark; §4.3 moves it to the page. The §4.3 reasoning is sound and I verified both drivers (`export_sessions.py:170-179` signature, `refresh.py:82-85` digest). But the deviation from FR-108's wording is unstated. | `docs/prd/dispatch-board.md:467` | State it as a deliberate, justified deviation in §9 or §12. |
| **F-8** | **Low** | If §8.3's empty state reuses the `.empty` class it lands inside `panel-overview` and trips `emptyPanels` (`tests/page.test.mjs:1463`) in every other test env lacking waiting data. | `tests/page.test.mjs:1463` | Specify: muted style, **not** the `.empty` class. |
| **F-9** | **Low** | Pre-existing NFR-22 conflict the namesake PBI should record: `tile('Architecture decisions', …, 'var(--human)')` is neither a waiting item nor an assumption awaiting a human. | `site/index.html:777` | Note it (fix or bank as follow-up). |

## The reviewer's own re-measurement

15 most recently modified mains under `C:/Users/jdk/.claude/projects` (25 total, 8 project folders, 18–8564 lines).

| Claim | Author | **Reviewer** | |
|---|---|---|---|
| Ends on an assistant conversation record | 15/15 | **15/15** | ✅ |
| Final text block ends `"?"` | 1/15 | **1/15** | ✅ |
| Solicit input without `?` | "6+" | **6** (a89ae64e, 25b6fa1f, 496ae460, cfb52509, 423734c4, 94a05a09) | ✅ |
| `"permission to use"` present | 15/15, all boilerplate | **15/15**, all boilerplate | ✅ |
| `is_error: true` tool results | 146 | **146** | ✅ exact |
| Last raw line not a conversation record | "two ended on attachment" | **11/15** non-conversation (`last-prompt` ×6, `attachment` ×2, `mode`, `bridge-session`, `artifact-comment-monitor`) | ✅ (understated — strengthens §3.1 fact 2) |
| `stop_reason: "tool_use"` at the end | 2 | **2** | ✅ |
| `toolDenialKind` top-level, `type: "user"`, `isMeta` absent, `toolUseResult` a **plain string**, `sourceToolAssistantUUID` + `content[0].tool_use_id` present | claimed | **confirmed on all 11 denial records** | ✅ |
| Denial kind distribution | "`user-rejected` is most common" | `automode-blocked` **8**, `user-rejected` **1**, `permission-rule` **1**, `automode-unavailable` **1** | ❌ **F-2** |
| `AskUserQuestion` sessions | 13/15 | **12/15** (36 calls) | ~ |
| **Unanswered asks (what D1 detects)** | not measured | **0/15 sessions, 0 items** | ❌ **F-1** |
| D2 condition 4 as specified (anchored final paragraph, `?` or the 8-phrase list) | "~1 in 7" | **4/15 fire; 0 false positives; recall ≈4/7 of genuine solicitations** | better than claimed |

`toolDenialKind` fail-safe: absence yields zero refusal items, never a false "nothing waiting" — verified. But denials appear only in CLI versions **2.1.205–2.1.260**; the 11 transcripts on 2.1.138–2.1.202 have none, and I cannot distinguish "no denial occurred" from "field did not exist". §9 row 4 and §12 record the limit honestly; that is adequate.

## Should D2 ship?

**Yes — and the spec undersells it.** Measured, D2's condition 4 fires on 4/15 with zero false positives and catches ~57% of genuine solicitations, not the ~14% §3.3 implies. Given F-1 (D1 fires on nothing in the corpus), shipping D2 disabled would leave FR-107/FR-108 producing an empty panel indefinitely — the failure §1.1 itself calls worse than nothing. `Inferred` is honest enough *as a word*, but only if F-6 is fixed: an item that can never be cleared except by typing into a dead session is the stale-lingering case, and the "later owner message clears it" rule does **not** prevent it. Ship D2 enabled, with an age bound.

## Owner questions

**The 2-of-10 split is right in count, wrong in content.** Row 2 (D2 ships enabled) is genuinely the owner's — but must be re-put with the corrected recall and with F-1's consequence stated, because "disable it" is a materially worse option than the spec implies. Row 1 is the owner's, but on a false premise (F-2) and aimed at the wrong kind: ask about `automode-blocked` (8/11), not primarily `user-rejected` (1/11). Rows 3–10 are correctly settled without the owner. I would add one: F-4's NFR-22 visual check needs a named human actor at close-out.

## Scope check

Clean. Every file §2 lists is inside `allowed_areas` (`docs/backlog/pbi/PBI-009.md:7`); `local/**` is correctly excluded and §6 proves no edit is needed there rather than assuming it. The four store claims all verified: `local/records.py:194-200` allows unlisted fields; `refresh.py:44` `MANAGED` and `:47` `TABS` untouched; the mass-delete guard (`refresh.py:132-143`) counts deletes, and a dropped field is a `set`. The `PARSER_VERSION` 6→7 claim is **correct and necessary** — `local/collector.py:157-161` key-set-checks `derive.new_session()`, and `export_sessions.py:170-179` folds the version into the cache signature, so no stale cache can serve rows without `waiting`. The PBI-011 round-1 defect class is closed here.
