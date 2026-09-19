---
pbi: PBI-009
title: "\"Waiting on you\" panel: detectors for pending questions, idle-after-asking and permission refusals"
parent_spec: docs/backlog/specs/dispatch-board.md (revision 5, approved)
prd: docs/prd/dispatch-board.md (FR-106 to FR-110, AC-75, AC-76)
revision: 3
status: round 2 returned APPROVE-WITH-NOTES on revision 2; N-1 to N-4 and the two round-2 adjudications applied in this revision (`requires_spec: true`)
reviews: docs/backlog/reviews/PBI-009/spec-review-r1.md (round 1, revision 1, CHANGES-REQUIRED); docs/backlog/reviews/PBI-009/spec-review-r2.md (round 2, revision 2, APPROVE-WITH-NOTES)
grounded_at: 560e296
---

# PBI-009: "Waiting on you" panel (per-PBI spec)

<!-- Every citation below was verified by reading the named file at commit 560e296 and counting lines.
     No line reference in this document was produced by a sed offset. -->

---

## 1. Intent

The board already shows what agents did. It does not show **what is stuck because nobody told the
owner**. A session that asked a question at 23:10 and went quiet looks exactly like a session that
finished its work; a tool call the permission rail refused looks like nothing at all.

This PBI adds one **"Waiting on you"** panel, rendered in the `--human` violet that
`CLAUDE.md` reserves for things awaiting a human, listing four kinds of item:

| Kind | Requirement | Signal class | Fires on the measured corpus (§3.5) |
|---|---|---|---|
| A question put to the owner and not yet answered (D1) | FR-107, AC-75 | **structured** — a tool call with no result | **0 of 15.** Rare but exact; see §7.1 |
| A session that went quiet after asking something in prose (D2) | FR-108 | **inferred** — text heuristic, lower confidence | **4 of 15**, 0 false positives; see §7.2 |
| An action refused by the permission check (D3) | FR-109, AC-76 | **structured** — a dedicated transcript field | **11 denial records**, all in the transcripts on CLI 2.1.205–2.1.260 |
| An assumption row the board exporter marks `needsYou` (D4) | FR-110 | **already exported** — no new derivation at all | exact, by construction |

### 1.1 The design constraint that shapes everything below

The parent spec's row 10 (`docs/backlog/specs/dispatch-board.md:294`) makes this spec responsible for
confirming the transcript record types **against real transcripts before any detector is built**. That
confirmation is §3.

**Revision 2 corrects what revision 1 concluded from it (round-1 F-1).** Revision 1 said "two of the
three detectors have crisp structured signals, and only one is a genuine text heuristic". That is true
of the **signals** and false of the **panel**. Measured, every one of the 36 `AskUserQuestion` calls in
the corpus received a `tool_result`, so **D1 — the crisp one — fires on 0 of 15 transcripts**, while D2
fires on 4. The honest statement is therefore:

> Two of the three question-and-refusal signals are structured and exact when they occur. But on
> measured data the panel's **question half is produced entirely by D2, the inferred detector**. D1 is a
> rare-but-high-value detector, not the primary one, and the spec must not be read as though the crisp
> detector carries the feature.

This is not an argument for dropping D1: an unanswered `AskUserQuestion` is the single most
unambiguous "waiting on you" state the transcript can hold, it costs nothing to detect, and its
measured absence is a property of this corpus rather than of the format (§3.3.1). It is an argument
against letting §9 present "disable D2" as the conservative option — with D1 silent, disabling D2
ships FR-107 and FR-108 as a **permanently empty panel**, which is the failure this section calls worse
than nothing.

The governing risk is asymmetric and must be stated plainly:

- A detector that fires too readily turns the panel into noise the owner learns to ignore — and once
  ignored, the panel is worse than absent, because it consumes the `--human` colour that the rest of
  the board uses to mean "this really is yours".
- A detector that fires too rarely is **worse still**, because an empty panel asserts "nothing is
  waiting", which is a claim the data cannot support.

The resolution is not to pick a cleverer threshold. It is to **separate the structured detectors from
the inferred one, label them differently on the page, and never let the panel's empty state claim more
than it knows** (§7.4). This is the same family of honesty as the two limits `CLAUDE.md` already
records: inferred `feeds` links are heuristics (`CLAUDE.md:145`) and the usage tab is not a plan meter
(`CLAUDE.md:146`). §9 adds this feature's limits to that list.

---

## 2. Scope

### In scope

- `exporters/derive.py` — every new derivation (the parent spec's rule, §4).
- `exporters/export_sessions.py` — the parser-version bump only (§4.4). No detector logic.
- `site/index.html` — the panel, in both Overview renderers.
- `tests/test_derive.py`, `tests/test_export_sessions.py`, `tests/page.test.mjs`.

### Out of scope

- **`local/**` entirely.** It is outside PBI-009's `allowed_areas`
  (`docs/backlog/pbi/PBI-009-waiting-on-you.md:7`: `exporters/**`, `tests/test_*.py`, `site/**`,
  `tests/page.test.mjs`). §6 shows the design needs no edit there, and §9 row 3 records the one
  follow-up it recommends.
- Any new store document or store collection (§5 — the design deliberately adds none).
- Notifying the owner off the board. Phone notifications are a Future iteration
  (`docs/backlog/specs/dispatch-board.md:205`).
- Answering from the board. Deferred by the owner (parent spec row 5); `refresh.py` refuses any
  export holding an `answers` document (`exporters/refresh.py:115-120`), and nothing here writes one.

---

## 3. The signals, confirmed against real transcripts (parent spec row 10)

Evidence was gathered read-only over the 15 most recently modified main transcripts under
`sessions.projectsRoot` (`board.config.json`), spanning 8 project folders, 18 to 8564 lines each.
Findings that decided the design:

### 3.1 Record-type facts that constrain every detector

1. **`timestamp`** is top-level, uniformly `YYYY-MM-DDTHH:MM:SS.sssZ`, and present on every
   `user`, `assistant`, `system` and `attachment` record — but **absent entirely** from bookkeeping
   record types (`mode`, `custom-title`, `ai-title`, `last-prompt`, `file-history-snapshot`,
   `bridge-session`, and others). `derive.stamp()` (`exporters/derive.py:150-157`) already returns
   `None` for an unreadable one, so the detectors must tolerate `None`, never assume a time.
2. **A transcript's last line is frequently not a conversation record.** Revision 1 reported two
   transcripts ending on a `type: "attachment"` record; the round-1 reviewer's independent count found
   **11 of 15** ending on a non-conversation record (`last-prompt` ×6, `attachment` ×2, `mode`,
   `bridge-session`, `artifact-comment-monitor`). Revision 1 understated this, and the correction
   strengthens the rule rather than weakening it: **every detector that reasons about "the last turn"
   must first filter to `type in ("user", "assistant")`**, or it will read a bookkeeping row as the
   conversation's end in the majority of sessions, not a minority of them.
3. **A `type: "user"` record is very often not the owner.** It may be a tool result, an `isMeta`
   duplicate of a typed command, or an injected `<command-message>` / `<system-reminder>` block.
   `derive.add_record()` already encodes the discriminator at `exporters/derive.py:438`: a genuine
   typed message is a `user` record whose `message.content` is a **plain string that does not start
   with `<`**. `isMeta` is used separately at `exporters/derive.py:441` to reject the synthetic
   duplicate Claude Code writes beside a real typed slash command.

### 3.2 Permission refusals — a dedicated field exists (FR-109)

The sample contained 146 `is_error: true` tool results, **most of which are ordinary command
failures** (non-zero exits, bad syntax) and not refusals. String-matching would have been badly
wrong in both directions: the phrase `"permission to use"` matched in **all 15 transcripts**, every
one of them from unrelated boilerplate skill-description text, never from a refusal.

The authoritative signal is a **top-level `toolDenialKind`** field, a sibling of `message` and
`timestamp`, on a `type: "user"` record with `isMeta` absent. Four values were observed, across
**11 denial records in total**:

| `toolDenialKind` | What it means | **Measured count** | Listed? |
|---|---|---|---|
| `automode-blocked` | The auto-mode classifier denied the action | **8 of 11** | **Yes** — see §9 row 1a (OWNER) |
| `user-rejected` | The owner clicked reject on the tool call | **1 of 11** | Yes — see §9 row 1b |
| `permission-rule` | A hard rail refused it (e.g. a protected path) | **1 of 11** | **Yes** |
| `automode-unavailable` | The classifier model was temporarily unavailable | **1 of 11** | **No** — §3.2.2 |

**Revision 2 corrects a frequency claim (round-1 F-2).** Revision 1's §9 row 1 asserted that
`user-rejected` "is the most common denial kind" and put *only* that kind to the owner. The
measurement says the opposite: `user-rejected` is **1 of 11** and `automode-blocked` is **8 of 11**.
The noise risk in D3 therefore sits almost entirely in `automode-blocked`, which revision 1 listed
without asking. §9 splits the question into rows 1a (`automode-blocked`, the volume kind) and 1b
(`user-rejected`, the already-known kind).

**3.2.1 The refused tool's name is recoverable.** The denial record carries
`message.content[0].tool_use_id`; the preceding `assistant` record (also named by the denial's
top-level `sourceToolAssistantUUID`) holds a `tool_use` block whose `id` equals it, and that block's
`name` is the refused tool. The detector therefore keeps a rolling map of `tool_use id -> name` as it
folds assistant records, exactly as `add_record()` already keeps `state['launched']`
(`exporters/derive.py:453`).

**3.2.2 `automode-unavailable` is deliberately excluded.** It is a transient model outage, not a
decision about the action. Listing it would put an item on the owner's panel that no owner action can
clear, which is the precise definition of noise.

**3.2.3 A landmine worth naming.** On these records the top-level `toolUseResult` is a **plain
string** (`"User rejected tool use"`, or an `"Error: …"`-prefixed string), *not* the dict every other
path assumes. The existing code is safe only by luck of an explicit guard —
`isinstance(tur, dict) and tur.get('status') == 'completed'` at `exporters/derive.py:462`. Any new
code reading `toolUseResult` must repeat that guard. A test pins it (§8, T-9).

### 3.3 Questions to the owner — structured, and prose

**Structured (FR-107).** `AskUserQuestion` tool calls appear as
`message.content[].type == "tool_use"`, `name == "AskUserQuestion"`, with
`input.questions[].question`. They occurred in **12 of the 15** sampled transcripts, **36 calls in
total**. Because a question is a *tool call*, the owner's answer arrives as a `tool_result` carrying
the same `tool_use_id`. **"Unanswered" is therefore a structural fact, not a guess**: a tool call with
no matching result.

#### 3.3.1 The measurement revision 1 did not take (round-1 F-1)

Revision 1 measured how often an ask **occurs** and stopped there. D1 does not detect an ask; it
detects an ask that is **unanswered**, and that rate was never measured. It has now been:

| Measurement | Value |
|---|---|
| Sessions containing an `AskUserQuestion` | **12 of 15** |
| `AskUserQuestion` calls | **36** |
| Calls with a matching `tool_result` | **36** |
| **Calls with no matching result — what D1 detects** | **0** |
| **Sessions on which D1 fires** | **0 of 15** |

So FR-107's structural signal is real, exact and, in this corpus, **silent**. Three things follow, and
the rest of the spec is written to them:

1. **The framing in §1.1 changes**, not the mechanism. D1's precision is still 100% by construction —
   an unanswered tool call cannot be a false positive. Its measured *recall of the panel's content* is
   nil.
2. **D1 still ships.** The zero is a property of how these 15 sessions ended (each ask was answered
   before the session stopped), not of the record format, which §3.2-style structural evidence confirms
   is present and well-formed on all 36 calls. An interrupted or abandoned ask is exactly the state the
   panel exists for, is unambiguous when it happens, and costs one set-difference to detect. §7.1
   therefore presents D1 as **rare but high-value**, and §12 records that it may show nothing for long
   stretches.
3. **D2 is load-bearing, not supplementary.** With D1 at zero, disabling D2 leaves FR-107 and FR-108
   rendering an empty panel indefinitely. §9 row 2 is re-put on that basis.

**Prose (FR-108).** This is where the ground truth is uncomfortable, and the spec must not paper over
it:

- All 15 sampled transcripts ended on an `assistant` record. **Not one ended on a user record.** So
  "the session ended with the assistant talking" is true of essentially every session and carries no
  information whatsoever.
- **Only 1 of 15** ended its final text block with a literal `"?"`.
- Yet **exactly 6 more** plainly solicited the owner's input without a question mark — closing with
  phrasings such as "let me know the scope and I'll run it", "say the word if you'd rather I delete
  the directory", or an offer of alternatives ending in a full stop. **7 genuine solicitations in
  total**, then: 1 with a `?`, 6 without.

**A trailing-`?`-only test would find one seventh of the real cases. D2's condition 4 is not that
test, and revision 1 conflated the two (round-1 F-1's recall correction).** Condition 4 is an anchored
final-paragraph match against `?` **or** a short closed solicitation list (§7.2). Measured as
specified:

| D2 condition 4, as written in §7.2 | Value |
|---|---|
| Sessions it fires on | **4 of 15** |
| False positives among those | **0** |
| Genuine solicitations in the corpus | 7 |
| **Recall** | **≈4/7, about 57%** |

Not "roughly one seventh". The detector is materially better than revision 1 claimed, and §7.2, §9
row 2 and §12 are corrected to this figure.

That said, the honest limit stands in its true form: **there is no test over prose that is both
precise and complete.** D2 misses about three in seven — the polite closes its phrase list does not
know — and a looser list would start matching rhetorical and self-answered questions. What has
changed is the size of the trade, not its existence. §9 row 2 still puts it to the owner, now with the
measured number and with §3.3.1's consequence stated beside it.

`message.stop_reason` is usable as a *negative* filter: a final assistant record with
`stop_reason == "tool_use"` was cut off mid-call (two such in the sample, each followed only by an
`attachment` record and never by a tool result). That session is broken, not asking.

### 3.4 What has no signal

`ExitPlanMode` and a `Plan` tool call appear **nowhere** in the sample. No detector may depend on
them.

### 3.5 The corpus, and what a second measurement confirmed

Every figure in §3 comes from the same corpus: the **15 most recently modified main transcripts** under
`sessions.projectsRoot` (`board.config.json:57`, `C:/Users/jdk/.claude/projects`), 25 mains in total
across 8 project folders, 18 to 8564 lines each. The round-1 reviewer re-measured the corpus
independently. The consolidated result, which is what §7 and §9 are written to:

| Measurement | Revision 1 | Independent re-measurement | Status in revision 2 |
|---|---|---|---|
| Ends on an assistant conversation record | 15/15 | 15/15 | confirmed |
| Final text block ends `"?"` | 1/15 | 1/15 | confirmed |
| Solicits input without a `?` | "6+" | 6 | confirmed, stated exactly (§3.3) |
| `"permission to use"` present, all boilerplate | 15/15 | 15/15 | confirmed |
| `is_error: true` tool results | 146 | 146 | confirmed exactly |
| `stop_reason: "tool_use"` at the end | 2 | 2 | confirmed |
| `toolDenialKind` record shape (top-level, `type: "user"`, `isMeta` absent, `toolUseResult` a plain string, `sourceToolAssistantUUID` and `content[0].tool_use_id` present) | claimed | confirmed on **all 11** denial records | confirmed |
| Last raw line not a conversation record | "two ended on attachment" | 11/15 | **corrected** (§3.1 fact 2) — revision 1 understated it |
| Denial-kind distribution | "`user-rejected` most common" | `automode-blocked` 8, `user-rejected` 1, `permission-rule` 1, `automode-unavailable` 1 | **corrected** (§3.2) |
| Sessions containing an `AskUserQuestion` | 13/15 | 12/15 (36 calls) | **corrected to 12/15** |
| **Unanswered asks — what D1 detects** | not measured | **0/15 sessions, 0 of 36 calls** | **added** (§3.3.1) |
| D2 condition 4 as specified | "~1 in 7" | **4/15 fire, 0 false positives, recall ≈4/7** | **corrected** (§3.3) |

Two notes on the three corrected rows. **The 12 vs 13 ask-session difference is now reconciled
(round-2 review).** 12 is the count of sessions with an actual `AskUserQuestion` `tool_use` block — 36
calls, 36 answered, 0 unanswered. 13 is the count of transcripts containing the literal string
`AskUserQuestion` anywhere, which is one wider because session `233bec8e` carries the string with zero
actual calls. 13 was a string match, 12 the structural count — the same string-vs-structure error this
section warns against, closed rather than left open. The spec adopts **12**, the structural figure;
nothing turns on the choice, since D1's unanswered count is 0 under either. The **`toolDenialKind`
availability window** is a real limit worth stating: denial
records appear only in transcripts written by CLI versions **2.1.205 to 2.1.260**; the 11 transcripts on
2.1.138 to 2.1.202 carry none, and "no denial occurred" cannot be distinguished from "the field did not
exist then". That does not affect the design — absence yields zero refusal items, never a false
"nothing waiting" (§9 row 4) — and §12 records it.

---

## 4. Where the derivation lives

The parent spec's rule (`docs/backlog/specs/dispatch-board.md:87`) is that **all derivations live in
one shared module under `exporters/`, and the collector imports it, never re-implements it**. The PRD
writes FR-107 to FR-109 as duties of "the collector"; implementing them in `derive.py` is what
discharges that for both the board and the local app from one implementation.

### 4.1 Everything goes in `exporters/derive.py`

**W-a. A new predicate, beside the existing inline test — not an extraction of it.**

**Revision 2 rewrites this item (round-1 F-3).** Revision 1 called `is_owner_message()` an extraction
of the inline discriminator at `exporters/derive.py:438`, then gave it two rules that line does not
have, then claimed "a refactor with no behaviour change" and asked for the existing
`first`/`firstPrompt` tests to pass untouched. That is self-contradictory, and T-4 and T-12
contradicted each other as a result. Line 438 reads, verbatim at `560e296`:

```python
if t == 'user' and state['first'] is None and isinstance(m.get('content'), str) and not m['content'].lstrip().startswith('<'):
    state['first'] = ' '.join(m['content'].split())
```

It tests `str` content only and **does not consult `isMeta`**. It governs `state['first']`, which
becomes the published `firstPrompt`. Widening it to accept list content would change `firstPrompt` for
any session that opens with a pasted attachment — a behaviour change to a published field, in a PBI
that claims none.

**The resolution: leave line 438 exactly as it is.** `is_owner_message()` is a **new, separate
predicate** used only by the new detectors:

```python
def is_owner_message(o):
    """True for a record the owner actually typed, for the waiting detectors' 'the owner was present'
    test. Wider than the inline firstPrompt test at add_record's line 438, which this does not change:
      - a `user` record, with `isMeta` not True (Claude Code's synthetic duplicate of a typed command);
      - whose message.content is either a plain string not beginning with `<`,
      - or a list carrying at least one `type == "text"` block whose text does not begin with `<`,
        and no `tool_result` block (what a pasted image or attachment reply produces).
    """
```

**The `<`-prefix rejection applies to both content shapes, not just the string one (round-2 N-3).** A
list-form record whose text block begins with `<` — a list-carrying `<system-reminder>` or similar
framing text — is a record the harness injected, not one the owner typed, and must be rejected the same
way the string branch already rejects it. Measured: no such record occurs in the 15-transcript sample,
so the case is theoretical, but `is_owner_message()` is the boolean that decides whether every pending
item in a session clears at once — the direction §1.1 calls worse — so the two branches must agree
rather than one being narrower by omission.

Why the predicate must be wider than line 438, even though line 438 stays narrow: the detectors use it
for the **clearing rule** (§7.1, §7.2, §7.3) — "did the owner speak after this item?". A reply the
owner typed alongside a pasted attachment arrives as list content. Treating that as *not* an owner
message would leave an answered question listed as pending, which is a false positive in the noisiest
possible direction. `firstPrompt`, by contrast, wants the narrow test it already has, and gets it.

**Consequences, stated so no later reader re-merges the two.** `add_record()` does not call
`is_owner_message()` for `state['first']`; line 438 is untouched and the existing `first`/`firstPrompt`
tests pass unchanged (T-12). `is_owner_message()` is called only from the new folds in W-c. The two
tests no longer conflict: **T-4** pins the new predicate's wider behaviour, **T-12** pins that
`firstPrompt` did not move, and **T-25** pins the difference itself.

**W-b. New state keys** in `new_session()` (`exporters/derive.py:419-422`), all additive:

| Key | Holds |
|---|---|
| `tools` | `{tool_use id: name}`, for §3.2.1 |
| `asks` | `{tool_use id: {"at", "question"}}` for each `AskUserQuestion` |
| `answered` | the set of `tool_use_id`s that received any `tool_result` |
| `denials` | `[{"at", "kind", "tool", "detail"}]`, filtered per §3.2 |
| `lastOwnerAt` | timestamp of the most recent owner message |
| `lastTurn` | `{"at", "role", "stop", "text"}` for the most recent `user`/`assistant` record only |

**W-c. `add_record()` folds them** (`exporters/derive.py:425-472`), purely by addition. No existing
branch changes. `lastTurn` is overwritten on each qualifying record, so it naturally ends holding the
last conversation record and ignores bookkeeping types (§3.1 fact 2).

**W-d. `waiting_of(state)`** returns the session's `waiting` object (§5.1), or `None`.

**W-e. `session_result()`** (`exporters/derive.py:503-517`) puts `waiting_of(state)` into the
document, under the same "copy, so later records leave it as it is" rule the function already
documents.

### 4.2 What stays in the exporter

**No detector logic whatsoever.** `export_sessions.py` already delegates parsing entirely —
`derive.new_session`, `derive.add_record`, `derive.session_result`
(`exporters/export_sessions.py:147-167`). It gains exactly one change, §4.4.

### 4.3 What the page computes, and why it is not in the exporter

`waiting` carries **only facts read out of the transcript** — what was asked, when, what was refused.
It carries **no idle flag and no elapsed duration**.

This is deliberate and load-bearing. `parse_session` caches a session's parse against its transcript
files alone (`exporters/export_sessions.py:143-146`, and the signature at
`exporters/export_sessions.py:170-179`). A field whose value depends on *now* would either defeat that
cache or go stale inside it. Worse, a changing duration would change the document's digest on every
tick (`exporters/refresh.py:82-85`), pushing a store write for every session every 10 minutes forever.

The page already has both inputs it needs on the session document: `last` and `windowMinutes`
(`CLAUDE.md:37`). It derives idleness at render time exactly as it already decides liveness. The
exporter states facts; the page states elapsed time.

### 4.4 The one exporter change: `PARSER_VERSION`

> **Relative to the build base (amended 2026-09-13).** The figures in this section cite the tree at `560e296`, where `PARSER_VERSION` is 6. They are not the target. PBI-014 (run detail, in review at the time of this amendment) bumps `PARSER_VERSION` from 6 to 7 for its new `files` field, and page-group PBIs merge one at a time, so this PBI will build on a base where the value is already 7 or higher. **The build must bump it by exactly one from whatever the base holds**, not set it to 7: a literal 7 would change nothing, and every session row cached before this PBI — which lacks `waiting` — would be replayed, leaving the panel silently empty. That is the defect class behind PBI-011's round-1 NO-GO (43 cached rows replayed with no findings). T-16 is amended to match.

`export_sessions.py:60` declares `PARSER_VERSION = 6  # bump when parsing changes, to drop cached
results`. Parsing changes here, so it becomes **7**.

This bump does more than clear `out/.cache/sessions.json`. The local collector's stored resume state
is validated by `_session_ok()` at `local/collector.py:157-161`, which checks **both**
`entry['parser'] == export_sessions.PARSER_VERSION` **and**
`set(entry['state']) == set(derive.new_session(sid))`. Adding keys in W-b changes that second set, so
without the bump the collector would silently reject its own stored state. With it, both checks agree,
and `local/collector.py:155-156` documents the outcome: the session "resets … and reads its files from
0 once, rather than failing every pass". One full re-read, then normal operation, and **no edit to
`local/**` is required**. This is the reason the bump belongs in this PBI rather than being left to
whoever notices later.

---

## 5. The store document — and its ownership

### 5.1 No new document. A new optional field.

`waiting` is an **optional field on the existing `sessions/<id>` document**:

```jsonc
"waiting": {
  "questions": [ { "at": "…Z", "question": "…", "source": "ask" | "prose" } ],
  "refusals":  [ { "at": "…Z", "kind": "permission-rule", "tool": "Bash", "detail": "…" } ],
  "more": 0          // items beyond the per-session cap (§7.3); omitted when 0
}
```

The field is omitted entirely when a session has nothing waiting, so an unaffected session's document
is byte-for-byte what it is today and `refresh.py` pushes no write for it.

FR-110 needs **no new data at all**. The `needsYou` rows already exist in
`projectTabs/<id>.assumptions` (`exporters/derive.py:889`) and in the `notWorkedOut` rows of
`projectTabs/<id>.decisions` (`exporters/derive.py:899`), and the page already reads both
(`site/index.html:747`, `site/index.html:776`). The panel composes them client-side.

### 5.2 Ownership — the hazard this design avoids

`CLAUDE.md:41` records the trap: `projectTabs` has **two writers**. `export_board.py` owns five tab
suffixes (`exporters/export_board.py:40`) and `export_sessions.py` owns `findings`
(`exporters/export_sessions.py:295-309`), and *neither may touch the other's*. Anything computing an
"I own these" set must use its own constant and **never `records.TAB_NAMES`**, which lists all six
(`local/records.py:91`). Getting that wrong is how a design deletes another writer's document every
60 seconds.

**This design does not enter that collection at all.**

- `sessions/*` has exactly one writer, `export_sessions.py`, which already replaces the whole folder
  each run (`exporters/export_sessions.py:276-278`). Adding a field to a document it already owns
  introduces no second writer and no new lifecycle.
- `exporters/refresh.py:44` `MANAGED` is unchanged — no new collection.
- `exporters/refresh.py:47` `TABS` is unchanged — **no new tab suffix**. Had `waiting` been a seventh
  `projectTabs` suffix, it would have required edits to `refresh.py`'s `TABS`, to `export_board.py`'s
  or `export_sessions.py`'s owned set, **and** to `local/records.py:91` and its id form at
  `local/records.py:103`, the last two being outside this PBI's areas. Avoiding that is the main
  reason the field sits on the session document.
- The **mass-delete guard** (`exporters/refresh.py:132-143`) needs no change. It counts deletes of
  pushed `runs` and `sessions` documents and refuses when a project would lose every pushed
  `projectTabs` document. The number of session documents is unchanged by this PBI; a session that
  stops having anything waiting loses a *field*, which is an ordinary `set`, never a delete.

---

## 6. The local app

The record shapes in `local/records.py` are outside this PBI's areas. The design was checked against
them rather than assuming:

**It validates as written.** `records.validate()` states its own contract at
`local/records.py:194-200`: "fields SHAPES does not list are allowed", and `_check_spec()`
(`local/records.py:174-191`) iterates only the declared `required` and `optional` keys. An extra
`waiting` field on a session document therefore passes the conformance check that
`local/tests/` runs over the real exporters (`CLAUDE.md:110`) — **the check that PBI-026 was raised to
satisfy for the findings tab does not need a sibling here.**

**The collector inherits it with no edit.** `local/collector.py:336-338, 386` builds session state and
results through `derive.new_session`, `derive.add_record` and `derive.session_result`. Because every
derivation is in `derive.py` (§4.1), the collector produces `waiting` without a line changing. §4.4
covers its stored-state reset.

**What is genuinely imperfect, stated as an owner question and not fixed here** (§9 row 3): `waiting`
will be *allowed* but not *validated* — it is absent from `local/records.shapes.json`, so a
malformed `waiting` would reach the local database unremarked. The recommended fix is a **follow-up
PBI adding `waiting` to the session shape's `optional` block**, exactly as PBI-026 followed the
findings tab. This spec does not specify an edit to a file outside its areas.

---

## 7. The detectors

Each subsection states: the exact signal, what matches, **what deliberately does not**, and how an
item is cleared.

### 7.1 D1 — Pending question (FR-107, AC-75) · confidence: **exact** · measured rate: **0 of 15**

**Read this detector as rare-but-high-value, not primary (§3.3.1).** When it fires it is certainly
right — an `AskUserQuestion` with no `tool_result` cannot be a false positive. It fired on nothing in
the measured corpus, because every ask there was answered before its session stopped. It earns its
place because the state it catches (a session interrupted or abandoned mid-ask) is precisely the state
the panel exists for, and it costs one set-difference. **It is not what makes the panel non-empty; D2
is** (§7.2).

**Signal.** An `AskUserQuestion` `tool_use` block whose `id` is in `state['asks']` and **not** in
`state['answered']`.

**Matches.** Any such call, whether or not the session is idle. A question put to the owner is waiting
on the owner from the moment it is asked; that is the panel's whole subject.

**Does not match.** A question that received a `tool_result` (the owner answered). A question asked
inside a **subagent** transcript — only the main transcript is read, matching the existing rule for
`skillUses` (`exporters/export_sessions.py:22-28`); an agent's question goes to its orchestrator, not
to the owner.

**Clearing / no double-counting.** Three independent mechanisms, in order:
1. A `tool_result` with the same `tool_use_id` removes it — the structural answer.
2. **Any owner message later than the ask clears every pending question in that session.** If the
   owner typed anything afterwards, they were present and the question is not silently blocking them.
   This is what stops a question that was answered *conversationally* rather than through the tool
   from being listed forever.
3. Only the transcript is consulted, so an item cannot be counted twice across a re-export; a
   re-parse of the same transcript yields the same set.

### 7.2 D2 — Idle after asking (FR-108) · confidence: **inferred, and labelled as such** · measured rate: **4 of 15, 0 false positives**

**This is the detector that makes the panel's question half non-empty** (§3.3.1). Measured, condition 4
as specified below fires on 4 of 15 transcripts with zero false positives, recalling about 4 of the 7
genuine solicitations in the corpus — **not the ~1-in-7 revision 1 implied** (§3.3).

**Signal.** All of the following, conjunctively:
1. `state['lastTurn'].role == "assistant"` (after filtering to conversation records, §3.1 fact 2);
2. `stop_reason != "tool_use"` — excludes a session cut off mid-call (§3.3);
3. no owner message after `lastTurn.at`;
4. the **final paragraph** of the last text block either ends in `?`, or matches a short, closed,
   second-person solicitation list (`let me know`, `want me to`, `shall I`, `should I`, `which would
   you`, `your call`, `say the word`, `confirm`);
5. the session is **quiet longer than `runs.runningWindowMinutes`** — judged on the page from `last`
   and `windowMinutes` (§4.3);
6. **the item is younger than the age bound** (§7.6) — added in revision 2 per round-1 F-6, and
   judged on the page for the same reason as condition 5.

**Does not match.** A live session (condition 5) — the owner is in it. A question mark anywhere but
the closing paragraph (condition 4 is anchored, so a rhetorical aside mid-answer does not count). A
session whose last turn was a tool call (condition 2). A session idle so long it has been abandoned
(condition 6).

**Clearing.** Two rules, and revision 1 had only the first. **Condition 3** is the owner's own
clearing rule: one owner message ends the item, which also prevents double-counting against D1 (§7.5).
**Condition 6** is the bound that clears an item nobody ever comes back to.

**Why an age bound is required, not optional.** Conditions 1, 2, 3 and 5 hold for **13 of the 15**
sampled sessions — every session ends on an assistant turn (§3.5), and every session older than the
10-minute `runs.runningWindowMinutes` (`board.config.json:62`) is idle. **Condition 4 is D2's only
real discriminator.** Combine that with a clearing rule that fires only on a *later owner message*,
and a session the owner silently walked away from can never be cleared except by typing into a dead
session: the item persists for the whole `sessions.days` retention window (`board.config.json:56`,
**7 days**). That is the stale-lingering failure mode, and the word `Inferred` does not excuse it.
§7.6 bounds it.

**Honest limit.** From §3.3: this detector finds the trailing-`?` case plus whatever the closed
solicitation list catches — measured, about 4 in 7 of genuine solicitations. It will miss polite
closes it does not know, and it may occasionally fire on a session that ended on a rhetorical
flourish (it did not in the corpus). It cannot be made both precise and complete, which is why §9
row 2 puts the enable/disable call to the owner — with the measured recall and with §3.3.1's
consequence stated, so "disable it" is not mistaken for the safe option.

### 7.3 D3 — Permission refusal (FR-109, AC-76) · confidence: **high**

**Signal.** A `type: "user"` record with a top-level `toolDenialKind` in the listed set (§3.2), `isMeta`
absent. The refused tool's name comes from `state['tools']` via
`message.content[0].tool_use_id` (§3.2.1); when it cannot be resolved the item still lists, with the
tool shown as `—`, because the refusal is the fact that matters.

**Does not match.** `automode-unavailable` (§3.2.2). Any `is_error: true` tool result **without**
`toolDenialKind` — that is an ordinary command failure, and §3.2 shows those outnumber refusals. No
string matching is used anywhere in this detector.

**Clearing.** An owner message later than the refusal clears it, on the same reasoning as §7.1 — and
this is the rule that keeps a seven-day window from accumulating every refusal the owner already dealt
with. Refusals are also capped (below).

**Cap.** At most **5** items per session across D1–D3, with the remainder counted in `more`. A session
that refused forty calls in a loop is one problem, not forty. A **panel-level** cap and an age bound
also apply — §7.6.

### 7.4 D4 — Assumptions awaiting a human (FR-110) · confidence: **exact**

Not a detector: the rows are already marked by the board exporter under FR-44
(`docs/prd/dispatch-board.md:301`). The panel lists every `rows[].needsYou` from the project's
`assumptions` tab and every `notWorkedOut[].needsYou` from its `decisions` tab, for every project in
view.

### 7.5 No item is counted twice

- **D1 against D2.** A session contributes **at most one question item**. D1 wins where both could
  match: a structured `AskUserQuestion` is preferred over inferring from prose, and the prose branch is
  skipped whenever D1 produced an item for that session. This also resolves FR-107 and FR-108, which
  otherwise describe overlapping states of the same question — the item is one, and its `source`
  (`ask` or `prose`) plus its elapsed time say which requirement it satisfies.
- **D4 against the existing Overview.** `site/index.html:520` already pushes a "Plan gate approval"
  line into "Needs attention" from `docs.assumptions.humanList.length`. The panel supersedes it, and
  that line is removed so one fact is not stated twice on one screen (§9 row 8).

### 7.6 Age bound and panel-level cap (revision 2, round-1 F-6)

Revision 1 had a per-session cap and a single clearing rule, and neither bounds an **abandoned**
session: a session nobody returns to is never cleared, and one such session yields at most 5 items
rather than none. Over the 7-day retention window that is how the panel silently fills with the dead.
Two bounds are added, both derived from configuration the board already has, neither introducing a
new setting:

| Bound | Rule | Why this value |
|---|---|---|
| **Age bound** | A **D1 or D2 question item is not listed once it is older than 48 hours**, measured from the item's `at` to render time. A **D3 refusal item** is not listed once it is older than 48 hours either. The item is not deleted from `waiting` — it is **derived out at render time**, on the page, for the same reason idleness is (§4.3): an age is a function of *now*, and the exporter states no time-dependent value. | The board's own retention is 7 days (`board.config.json:56`) and its liveness window is 10 minutes (`:62`). 48 hours sits between them: long enough that a question asked on a Friday evening survives until Monday morning with the weekend inside it, short enough that a session abandoned last week is gone. It is one constant on the page, reversible in one line. |
| **Panel-level cap** | At most **20 items** across all sessions and all kinds, newest first, with the remainder shown as a single **"+N more waiting"** line. The per-session cap of 5 (§7.3) still applies first. | A panel that cannot be read in one screen is not a panel the owner reads. 20 is 4 sessions at their per-session cap. D4 rows are counted in the 20, but are **never** the items dropped — an assumption awaiting a human is an exact fact, so the drop order is D2 items first (inferred), then D3, then D1, then never D4. **The full ordering, stated in one place (round-2 N-4):** the panel displays all surviving items newest-first by `at`; when the cap must drop items, it drops by kind in the stated order, and **within a kind it drops the oldest items of that kind first** — the same direction as the newest-first display, so what remains after a drop is always the most recent items of whichever kinds survive. |

**The panel states its own bounds rather than hiding them.** When either bound removes anything, the
panel's footer reads "Older than 48 hours, or beyond the first 20, is not shown." — so a suppressed
item is a stated absence, never a silent one, on the same principle as §8.3.

**What this deliberately does not do.** It does not clear the item in the store, does not write a
dismissal, and does not add an `answers`-like record — all of which would need a writer the design
does not have (§5.2) and the owner has deferred (§2). Suppression is a render-time view rule, and a
re-export of the same transcript still produces the same `waiting` object (§7.1 rule 3).

---

## 8. The page

### 8.1 Placement and language

A panel titled **"Waiting on you"**, placed in the Overview **above** "Needs attention"
(`site/index.html:545-548`), spanning the row rather than sitting in the `g-3` grid when it has items.

It must render from **both** Overview renderers — `renderOverview()` for a project and
`renderSessionOverview()` for "Other sessions" (`site/index.html:494-496`). A blocked session linked to
no project is exactly the session most likely to be forgotten.

Design rules (`CLAUDE.md:131-139`), all binding:

- One summary tile in the existing status-tile language, `--human`, matching
  `tile('Awaiting your decision', …, 'var(--human)', true)` at `site/index.html:506`.
- Colours only through tokens; `--human` (`site/index.html:9`) for every item, since the whole panel
  is by definition awaiting a human. Severity hues are not used — this is not a severity list.
- One sans face. IBM Plex Mono only for a session id. **No wide monospace**: a quoted question renders
  in the sans face, clamped to two lines.
- Everything through `esc()`. Transcript text is data, never markup — `md()` is for repo text only
  (`CLAUDE.md:138`), so it is **not** used here.
- No new motion.

### 8.2 Showing confidence honestly

Confidence is shown as a **word on each item**, not a score:

| Item | Tag | Reads as |
|---|---|---|
| D1 | `Asked you` | the question is quoted verbatim |
| D2 | `Inferred` | "last message looks like a question · quiet 4h" |
| D3 | `Refused` | "Bash refused by a permission rule" |
| D4 | `Needs you` | reuses the existing `tag human` class (`site/index.html:114`) |

`Inferred` is the load-bearing word. It tells the owner that an item may be wrong **without**
demoting it out of sight, which a numeric score would do. Numeric confidence is rejected: the
detectors are boolean, and a percentage would be invented.

### 8.3 The empty state — the sentence that must not overclaim

When nothing is detected the panel shows:

> **Nothing detected as waiting on you.** These are heuristics over transcripts; a question asked in
> prose may not be spotted.

Not "Nothing is waiting on you." The panel may not assert an absence it cannot verify (§1.1). This
sentence is an acceptance criterion (W-10), not a stylistic preference.

**It must not use the `.empty` class** (revision 2, round-1 F-8). The panel lives inside
`panel-overview`, and `tests/page.test.mjs:1463` computes `emptyPanels` by testing each panel's
`innerHTML` for `/class="empty"/`. An empty state rendered with `.empty` would therefore mark
`panel-overview` as empty in **every** test environment whose fixture has no waiting data, failing
`tests/page.test.mjs:1464-1465` — including the two assertions this PBI must keep green (§8.4) — even
though the Overview is full of content. The sentence renders in the **muted style** instead: the
existing muted token treatment used for secondary text, with no `empty` class anywhere in the panel's
markup. W-10 states this, and T-26 pins it.

### 8.4 Keeping the ten-panel equivalence check meaningful

`tests/page.test.mjs:1431-1473` deep-equals every panel across the store adapter and the local API
adapter, and asserts `emptyPanels` is `[]` on **both** sides — with the comment at
`tests/page.test.mjs:1461-1462` explaining why: an empty state is what both sides would show if a
renderer were never reached at all.

The new panel lives inside `panel-overview`, which is already compared, so it is covered **only if the
fixture exercises it**. This PBI must therefore:

1. add a `waiting` block to at least one `EQ_SESSIONS` fixture session, carrying **both** a question
   and a refusal; a `needsYou` row is already present (`tests/page.test.mjs:1394`,
   `tests/page.test.mjs:1397`);
2. add probes to the content list at `tests/page.test.mjs:1467-1470`, in its existing
   `[what, regexp]` form;
3. leave `emptyPanels` empty on both sides.

**Revision 2 corrects the probe (round-1 F-5).** Revision 1 proposed
`['an item waiting on you', /Waiting on you/]`. That matches the **panel title**, which §8.3 renders in
the empty state too — so the probe would have passed on two identically empty panels, which is exactly
the failure `tests/page.test.mjs:1461-1462` warns against and exactly what step 2 exists to prevent. A
title is not content.

**The probes must match item content**, and there are two so that neither detector class can be
silently absent:

```js
['a question waiting on you', /<the fixture's verbatim question text>/],
['a refused action', /Refused/],
```

The first is the fixture session's own question string, which appears only when an item is rendered;
the second is the D3 item tag from §8.2, which appears only when a refusal is rendered. Neither string
occurs in the §8.3 empty state, so a panel that rendered nothing fails the probe — which is the point.

**Both probes must be anchored to the panel itself, not run across the whole rendered board (round-2
N-1).** The general equivalence check's `seen` map (`tests/page.test.mjs:1466`), tested by
`Object.values(seen).some(...)` at `:1467-1470`, matches against **every** panel's markup together. Run
that way, `/Refused/` is vacuous: `site/index.html:1070` renders `<th class="num">Refused</th>`
unconditionally in the Usage tab's "Usage limits" table, so the probe would pass whether or not the
waiting panel drew a refusal. The fixture's question text carries the same hazard if it collides with
the assumptions fixture's own `Which port?` string, already asserted at `tests/page.test.mjs:1469` for a
different panel. T-23 and T-29 must therefore test `seen['panel-overview']` specifically — or, failing
that, use fixture strings verified unique to the waiting panel — never the whole-board `seen` object.

---

## 9. Assumptions and open questions

| # | Question | Default chosen | Impact if wrong | Needs OWNER before building? |
|---|---|---|---|---|
| 1a | **Does an `automode-blocked` refusal belong on the panel?** The auto-mode classifier denied the action; the owner may never have seen it. It is **8 of the 11** denial records measured (§3.2) — by volume, D3 *is* this kind. | **List it**, tagged `Refused`, cleared by any later owner message and by the 48-hour age bound (§7.3, §7.6). | **This is where D3's noise actually lives.** If the owner does not want auto-mode denials surfaced, they are the single largest noise source the panel has and will be the majority of D3's items. Excluding them wrongly makes D3 near-silent — the other three kinds together were 3 of 11. | **YES.** Revision 1 did not ask this, resting on a frequency claim that was wrong (round-1 F-2). It is the kind whose volume decides whether D3 helps or annoys. |
| 1b | **Does a `user-rejected` refusal belong on the panel?** The owner clicked reject themselves, so they already know — but in a long autonomous session they may not recall it, and the run is still blocked. | **List it**, tagged `Refused`, cleared the same way. | Low volume: **1 of 11** measured, not "the most common kind" as revision 1 claimed. Listing it when unwanted is a minor irritant; excluding it wrongly loses real blocks in autonomous runs. | **Asked alongside 1a, but not a blocker on its own.** If the owner answers only one, 1a is the one that matters. |
| 2 | **Does the prose detector D2 ship enabled?** Corrected figures: condition 4 fires on **4 of 15 with zero false positives**, recall **≈4/7 (~57%)** of genuine solicitations — **not** the ~1-in-7 revision 1 implied (§3.3). And **D1 fires on 0 of 15** (§3.3.1). | **Ship enabled**, tagged `Inferred`, gated on idleness and on the 48-hour age bound (§7.6). | **The two options are not symmetric, and revision 1 presented them as though they were.** Enabled and too loose: the panel gains items the owner dismisses and `--human` loses meaning board-wide — bounded by the measured 0 false positives and by §7.6. **Disabled: because D1 is silent on measured data, FR-107 and FR-108 together render a permanently empty panel** — not a reduced feature but the failure §1.1 calls worse than nothing, shipped deliberately. | **YES**, re-put on the corrected evidence. The trade is still the owner's; what changed is that "disable it" is visibly the **worse** option, not the safe one. The spec recommends **enable**, contingent on §7.6 shipping with it. |
| 3 | `waiting` is allowed but not validated by the local record shapes (§6). | Ship as an unlisted-but-allowed field; **recommend a follow-up PBI** adding it to the session shape's `optional` block, as PBI-026 did for `findings`. | A malformed `waiting` reaches the local database unremarked. Low: only `derive.py` writes it, and §8 tests pin its shape. | No — `local/records.py` is outside this PBI's areas, and `validate()` accepts the document today (`local/records.py:194-200`). |
| 4 | Is `toolDenialKind` a stable field? It is an undocumented internal of a vendor log format. | Read it as the sole signal for D3; degrade to **zero refusal items** if it disappears, never to string matching (§3.2 shows string matching is actively wrong). | If the field is renamed, D3 silently under-reports until someone notices. Fixture tests pin the shape so the failure is visible in CI-less review at close-out. | No — a risk to record, not a decision. |
| 5 | Per-session cap on listed items. | **5**, remainder in `more` (§7.3). | Too low hides a genuinely multi-blocked session; too high lets one looping session fill the panel. Reversible in one line. | No. |
| 6 | The clearing rule "any later owner message clears the item". | Adopt for D1, D2 and D3 (§7.1). | A refusal the owner typed past without resolving is dropped, so the panel under-reports. The alternative — never clearing — makes a 7-day window accumulate every historical refusal, which is worse. | No. |
| 7 | Does the panel obey the session filter, or show every session in view? | **Every session in the current view**, ignoring the session filter. | A blocker hidden by a filter the owner forgot they set is exactly the failure this feature exists to prevent. | No — settled by the feature's own intent. |
| 8 | The existing "Plan gate approval" line in "Needs attention" (`site/index.html:520`) duplicates D4. | **Remove it**; the panel carries it (§7.5). | One fact stated twice on one screen; trivially reversible. | No. |
| 9 | Is a question inside a subagent transcript a question to the owner? | **No** — main transcript only, matching `skillUses` (`exporters/export_sessions.py:22-28`). | An agent blocked on its orchestrator would be mislabelled as blocking the owner. | No — settled by how agents actually run. |
| 10 | Does D1 fire immediately, or only once idle? | **Immediately** for D1 (structured); D2 requires idleness. This is what lets AC-75 hold without an idle gate, since AC-75 states no time condition. | Firing immediately lists a session the owner is actively working in. Mitigated: an owner message clears it at once (§7.1). | No — AC-75's wording settles it. |
| 11 | **The age bound and panel cap's values** (revision 2, round-1 F-6): 48 hours, 20 items. | **48 h / 20**, derived from the board's own 7-day retention and 10-minute liveness window (§7.6); suppression is a render-time rule, so nothing is deleted. | Too short hides a real question over a long weekend; too long lets abandoned sessions accumulate for the full 7 days, which is the failure F-6 identified. Both are one constant on the page, reversible in one line. | No — a tuning value, and F-6 required only that *some* bound exist and be stated. **FYI to the owner:** if 48 h feels wrong in use, it is a one-line change, not a redesign. **Reaffirmed in round 2** (`spec-review-r2.md`, "The two challenges"): "the author is right; non-OWNER stands" — a render-time view constant that deletes nothing and is reversible in one line differs in kind from a row that decides what the feature is, so it stays FYI rather than becoming a fourth owner row. |
| 12 | **FR-108 says "the collector shall mark that session as idle after asking"; §4.3 computes idleness on the page instead** (revision 2, round-1 F-7). | **Deliberate, justified deviation.** The requirement's *observable outcome* — an idle-after-asking session appears marked on the panel — is met exactly. Only the computation site moves. | Stated in full at §4.3 and verified: `parse_session` caches a session's parse against its transcript files alone (`exporters/export_sessions.py:143-146`, signature `:170-179`), and `refresh.py`'s digest (`exporters/refresh.py:82-85`) would change on every tick. A `now`-dependent field in the exporter would either defeat the cache or go stale in it, and would push a store write for every session every 10 minutes forever. The page already holds `last` and `windowMinutes` and derives liveness this way today. | No — a design decision with verified drivers, recorded here (and in §12) so the deviation is explicit rather than silent. |
| 13 | **`--human` on the Decisions tab's ADR tile and cards (`site/index.html:777`, `:784`) — raised at the spec gate as a misuse; on re-grounding (2026-09-13) a taste question, not a defect** | **Not a defect under the governing rule; no intake item.** NFR-10 (`docs/prd/dispatch-board.md:549`), which governs this tab, reserves `--human` for "something awaiting a human". A *proposed* ADR ("all proposed, none in force") is awaiting a human's accept-or-reject, and the page already maps the `proposed` state to `--human` by design (`.tag.proposed`, `site/index.html:114`). The test used earlier — "neither a waiting item nor an assumption awaiting a human" — is NFR-22's stricter wording (`:570`), which reaches only next-iteration views and the Agent catalogue tab. Both instances therefore conform to NFR-10 as written. Whether a proposed ADR *should* read as "awaiting you" is an owner taste call, recorded as an FYI and outside this PBI either way. Separately, NFR-10's own status note ("Partly met: the brand dot… planned in PBI-002") is stale: PBI-002 shipped that remedy (`docs/backlog/pbi/PBI-002-page-fixes.md:40`, `:59`; the brand mark now uses `currentColor`) — a PRD bookkeeping fix, not this PBI's. |

**Owner rows after revision 2: three to answer, of which one is blocking — 1a, 1b and 2.**

- **Row 2 is the blocking one**, and it is re-put rather than repeated: the recall figure was wrong in
  revision 1 (≈57%, not ~14%), and the alternative's true cost — a permanently empty panel, because
  D1 fires on nothing measured — was not stated. Both are now on the row.
- **Rows 1a and 1b replace revision 1's single row 1**, which asked about the wrong denial kind on a
  false premise. 1a (`automode-blocked`, 8 of 11) is the one that carries D3's noise; 1b
  (`user-rejected`, 1 of 11) is asked beside it for completeness.
- **Rows 3 to 13 are settled without the owner**, with two FYIs attached: row 11's tuning values and
  row 13's pre-existing `--human` conflict, which the owner may want raised as a follow-up PBI.
- **One close-out actor is named, not asked:** W-14 requires the owner, or a rendered-screenshot
  evidence artefact, to confirm the panel against NFR-22 in both themes (§11, round-1 F-4). That is a
  step in the close-out, not a question blocking the build.

None of the blocking rows can be settled by reading the code, and none was settled by the parent spec,
whose row 10 delegated exactly this question here.

---

## 10. Test plan

Named files and cases. Both suites must be green
(`python -m unittest discover -s tests`, `node tests/page.test.mjs`). All Python tests build synthetic
transcripts in temporary directories and never read the real `~/.claude` (`CLAUDE.md:108`).

### 10.1 `tests/test_derive.py`

| id | Case |
|---|---|
| T-1 | An `AskUserQuestion` with no `tool_result` yields one `questions` item with `source: "ask"` and the question text. |
| T-2 | The same call **with** a matching `tool_result` yields nothing. (No double-count of an answered question.) |
| T-3 | An unanswered call **followed by an owner message** yields nothing (§7.1 rule 2). |
| T-4 | **The new predicate.** `is_owner_message()` accepts a plain-string user record; rejects an `isMeta` duplicate, a `<command-message>` block, a `<system-reminder>`, and a `tool_result`-bearing list; **accepts** a list carrying a `text` block and no `tool_result` (§4.1, the pasted-attachment reply); **rejects** the same list shape when its `text` block begins with `<` (round-2 N-3), the same prefix rule the string branch already applies. |
| T-5 | A final assistant turn ending `"…which would you prefer?"` with no owner reply yields one `prose` question; the same text **followed by** an owner message yields nothing. |
| T-6 | A final assistant turn with `stop_reason: "tool_use"` yields nothing (§3.3). |
| T-7 | A transcript whose last line is a `type: "attachment"` record is judged on the last **conversation** record, not the attachment (§3.1 fact 2). |
| T-8 | Each of `permission-rule`, `automode-blocked`, `user-rejected` yields a refusal with the tool name resolved from the preceding assistant `tool_use` block; `automode-unavailable` yields none. |
| T-9 | A denial record whose top-level `toolUseResult` is a **plain string** is handled without raising (§3.2.3). |
| T-10 | Six qualifying items in one session produce 5 items and `more: 1`. |
| T-11 | A session with none of the above has **no `waiting` key at all** in its document. |
| T-12 | `new_session()` gains only the W-b keys, and the existing `first`/`firstPrompt` behaviour is unchanged — including that a session opening with a **list-content** record still yields the same `firstPrompt` it does today (guards that line 438 was not widened; §4.1 W-a). |
| **T-25** | **The two tests are different, and deliberately so** (revision 2, round-1 F-3). One transcript opening with a list-content owner reply: `is_owner_message()` returns **True** for that record, while `state['first']` is **unchanged by it**, exactly as at `exporters/derive.py:438`. This is the case in which T-4 and T-12 would have contradicted each other under revision 1's wording. |

**False positives most feared, each with a negative test:** T-2 and T-3 (a question already answered),
T-5's second half (the owner replied in prose), T-6 (a crashed session read as a question), T-8's last
clause (a transient classifier outage read as a refusal), and — the one §3.2 shows would have been
catastrophic — **T-13: a transcript containing 20 ordinary `is_error: true` tool failures and the
boilerplate phrase "permission to use" produces zero refusals.**

### 10.2 `tests/test_export_sessions.py`

| id | Case |
|---|---|
| T-14 | A synthetic session with a pending question and a refusal exports a `sessions/<id>.json` carrying `waiting`; an unaffected session's document is unchanged from today's output. |
| T-15 | `waiting` holds **no** idle flag and no duration (§4.3), so re-exporting the same transcript at a later clock time produces a byte-identical document. |
| T-16 | `PARSER_VERSION` is **exactly one greater than its value at the build base**, and a cache written under the build base's version is not reused. *(Amended 2026-09-13: this row previously pinned "7" and "6". PBI-014 moves `PARSER_VERSION` from 6 to 7 before this PBI builds, so a literal 7 would pass with no bump at all.)* |
| T-17 | No document is written to `projectTabs` beyond the existing `findings` lifecycle, and `refresh.py`'s plan over the export contains no new collection (guards §5.2). |

### 10.3 `tests/page.test.mjs`

| id | Case |
|---|---|
| T-18 | The panel lists a `waiting` question, a refusal and a `needsYou` row, with the four tags of §8.2, in a project view. |
| T-19 | The panel renders in "Other sessions" (`renderSessionOverview`). |
| T-20 | **The empty case:** no session has `waiting` and no row is `needsYou` → the panel shows the §8.3 sentence verbatim, and does **not** say "nothing is waiting on you". |
| T-21 | A question idle longer than `windowMinutes` shows the idle wording; the same item inside the window does not (§4.3 — page-side derivation). |
| T-22 | A question containing `<script>` and backticks is escaped and **not** rendered through `md()`. |
| T-23 | The store and local adapters render the panel identically, with **both** §8.4 probes added (the fixture's question text and `/Refused/`) and `emptyPanels` empty on both sides. |
| T-24 | "Needs attention" no longer carries the duplicate "Plan gate approval" line (§7.5). |
| **T-26** | **The empty state is not `.empty`** (§8.3, round-1 F-8). With no waiting data at all, the panel renders the §8.3 sentence and `panel-overview`'s `innerHTML` contains **no** `class="empty"` — asserted with the same `/class="empty"/` test `tests/page.test.mjs:1463` uses, so the criterion and the suite's own check cannot drift apart. |
| **T-27** | **The age bound** (§7.6). A question item stamped 47 hours ago renders; the same item stamped 49 hours ago does not, and the footer's suppression line appears. A refusal behaves the same way. Time is injected, not read from the wall clock, so the case is deterministic. |
| **T-28** | **The panel-level cap** (§7.6). 25 items across 6 sessions render 20 items and one "+5 more waiting" line; D4 `needsYou` rows survive the cap while D2 items are dropped first, oldest D2 items before newer ones (round-2 N-4). |
| **T-29** | **The probe is not vacuous** (round-1 F-5). A negative control: rendering the equivalence fixture with its `waiting` block removed makes the §8.4 probes **fail** — proving they test item content and not the panel title, which is present in both states. |

---

## 11. Acceptance criteria

| id | Criterion | Source |
|---|---|---|
| **AC-75** | When a session's last assistant turn asks the owner a question and no owner message follows it, the "Waiting on you" panel lists that session. | PRD (FR-106, FR-107) |
| **AC-76** | When a transcript records an action refused by the permission check, the panel lists that refusal with its session. | PRD (FR-106, FR-109) |
| **W-1** | One panel titled "Waiting on you" appears in the Overview, in `--human`, in both `renderOverview()` and `renderSessionOverview()`. | FR-106 |
| **W-2** | An unanswered `AskUserQuestion` is listed with its question text, tagged `Asked you`; the same call with a matching `tool_result` is not listed. | FR-107 |
| **W-3** | A session whose last conversation turn is an assistant question, quiet longer than `runs.runningWindowMinutes`, is listed tagged `Inferred`; a live one is not. | FR-108 |
| **W-4** | A `toolDenialKind` of `permission-rule` or `automode-blocked` is listed with its refused tool; `automode-unavailable` is not, and no `is_error` tool result without `toolDenialKind` is. | FR-109 |
| **W-5** | Every `needsYou` assumption row and `notWorkedOut` row, for every project in view, appears in the panel. | FR-110 |
| **W-6** | Any owner message later than an item clears it, and a session contributes at most one question item and at most 5 items in total. | §7.3, §7.5 |
| **W-7** | Every derivation is in `exporters/derive.py`; `export_sessions.py` changes only `PARSER_VERSION`. | Parent spec `:87` |
| **W-8** | No new store collection, no new `projectTabs` suffix, and no change to `refresh.py`'s `MANAGED`, `TABS` or the mass-delete guard. | §5.2 |
| **W-9** | A session document with nothing waiting carries no `waiting` key and is unchanged from today's export; the document holds no time-dependent value. | §4.3 |
| **W-10** | The empty panel states that nothing was **detected**, and names the heuristic limit; it never asserts that nothing is waiting. **It uses the muted style and carries no `empty` class**, so `panel-overview` is never counted in `emptyPanels` (`tests/page.test.mjs:1463`). | §8.3 |
| **W-11** | Both adapters render the panel identically; the equivalence fixture exercises it through **two item-content probes** (the fixture's question text and `/Refused/`, never the panel title), evaluated against `seen['panel-overview']` alone and not the whole-board `seen` map (round-2 N-1); no panel is empty on either side. | §8.4 |
| **W-12** | Transcript text renders through `esc()` only, in the sans face; no wide monospace, no colour outside the tokens. | `CLAUDE.md:131-139`, NFR-9, NFR-14 |
| **W-13** | Worker close-out: both suites green on the head commit; `review-agents:code-reviewer` GO. | PBI-009 |
| **W-14** | **Close-out visual confirmation, by a named actor.** Before the PBI is closed, **the owner** — or, where the owner delegates it, a **rendered-screenshot evidence artefact written under `docs/backlog/evidence/`** and linked from the PBI file's Evidence section — confirms the "Waiting on you" panel **in both themes** (dark on bare `:root`, and light under both `prefers-color-scheme: light` and `[data-theme="light"]`) against: (a) the design rules at `CLAUDE.md:131-139`; (b) the four NFRs NFR-22 incorporates — **NFR-9** (`docs/prd/dispatch-board.md:548`, no colour literal outside the `:root` token blocks), **NFR-10** (`:549`, `--human` only for something awaiting a human; the semantic tokens for run and review states), **NFR-13** (`:552`, the status-tile language: bordered tile, 3 px coloured top bar, label, figure, one line of context) and **NFR-14** (`:553`, store text through `esc()`), of which only NFR-9 and NFR-14 are regex-checkable and so only those are covered by W-12; and (c) **NFR-22's reservation clause** — that `--human` is used **only** for "Waiting on you" items and assumptions awaiting a human, with no other new use introduced by this PBI. The confirmation is recorded as a close-out step with its actor named, not assumed. | `docs/prd/dispatch-board.md:570` (NFR-22), `docs/backlog/specs/dispatch-board.md:216`, `docs/prd/dispatch-board.md:548`, `:549`, `:552`, `:553`; round-1 F-4 |
| **W-15** | **The panel is bounded.** No item older than 48 hours is listed, no more than 20 items are listed across all sessions, and whenever either bound suppresses anything the panel says so. `waiting` in the store still carries no time-dependent value (W-9), because both bounds are applied at render time. | §7.6, round-1 F-6 |

**A note on W-14's evidence route and this PBI's areas (corrected, round-2 N-2).**
`docs/backlog/pbi/PBI-009-waiting-on-you.md:7` lists `exporters/**`, `tests/test_*.py`, `site/**` and
`tests/page.test.mjs` as `allowed_areas`; `docs/**` is not among them and nothing in W-14 changes that.
Revision 2 cited `docs/backlog/specs/dispatch-board.md:216-217` as authority for a screenshot artefact
under `docs/backlog/evidence/`, but that line names only `CLAUDE.md` and `README.md` as the
declared-docs-touch class — it does not reach `docs/backlog/evidence/**`. The two existing artefacts at
`docs/backlog/evidence/2026-09-11-page-checks` and
`docs/backlog/evidence/2026-09-11-prd-demonstrations.md` are precedent that the practice is tolerated,
not authority that this spec's parent grants it.

So the two routes are not equally scope-clean. **The owner confirming the panel directly needs no
artefact at all, is the primary route, and stays scope-clean as written.** The **delegated** route — a
rendered-screenshot evidence artefact written under `docs/backlog/evidence/` — needs an **explicit scope
extension** to `docs/backlog/pbi/PBI-009-waiting-on-you.md`'s `allowed_areas` before a worker writes it; without one, a
worker who delegates the confirmation and writes the artefact risks a scope-breach stop at close-out.
This spec does not grant that extension itself (`docs/**` stays outside its areas); it is recorded here
so a worker who reaches W-14 obtains the extension first rather than assuming the citation already
covers it.

---

## 12. Known limits, to be recorded in `CLAUDE.md`

To sit beside the two limits already recorded at `CLAUDE.md:145-146`:

- **The "Waiting on you" panel is detectors, not a guarantee.** A question asked in prose is found
  only when its closing paragraph looks like a question; measured, that catches about **4 of every 7**
  real solicitations, and sessions that closed with a polite offer the phrase list does not know are
  missed. An empty panel means nothing was detected, never that nothing is waiting.
- **On measured data the panel's question half comes from the prose detector, not the structured one.**
  Every `AskUserQuestion` in the 15-transcript corpus was answered, so the exact detector (an ask with
  no result) found nothing. It stays because the state it catches is unambiguous when it occurs, but
  the panel should be read as mostly inferred, and it may show no structured question item for long
  stretches.
- **Only main transcripts are read.** A question a subagent asked its orchestrator is not listed.
- **Refusals rest on one undocumented transcript field** (`toolDenialKind`). If it is renamed
  upstream, refusals stop being listed rather than being guessed from message text. Denial records
  were also only observed in transcripts written by CLI **2.1.205 to 2.1.260**; on older transcripts
  "no refusal happened" and "the field did not exist yet" are indistinguishable (§3.5).
- **An item is cleared by any later owner message**, so a refusal the owner typed past without
  resolving disappears from the panel.
- **An item is also dropped after 48 hours, and the panel shows at most 20** (§7.6). A question on a
  session nobody returns to stops being listed even though nobody answered it — the alternative was
  letting abandoned sessions accumulate for the full 7-day retention window. When either bound hides
  something the panel says so, but it cannot say what it hid.
- **Idleness is computed on the page, not by the collector**, a deliberate deviation from FR-108's
  wording (§4.3, §9 row 12). The observable outcome is identical; a `now`-dependent field in the
  exporter would defeat its own parse cache and push a store write for every session every tick.

---

## 13. Spec-gate record

| Field | Value |
|---|---|
| Author | building session, 2026-09-12 |
| Grounded at | `560e296`, every citation read and line-counted; every citation revision 2 touches re-read and re-counted |
| Independent review | **required before any code** (`requires_spec: true`) |
| Round 1 | **CHANGES-REQUIRED** (2 High, 5 Med, 3 Low) — `docs/backlog/reviews/PBI-009/spec-review-r1.md`. All nine findings applied in revision 2; see §14 |
| Round 2 | **APPROVE-WITH-NOTES**, on revision 2 (2 Med, 2 Low new findings; two challenges resolved in the author's favour) — `docs/backlog/reviews/PBI-009/spec-review-r2.md`. N-1 to N-4 and both adjudications applied in revision 3, plus a correction to row 13's NFR citation and follow-up route; see §14 |
| Owner rows outstanding | §9 rows **1a**, **1b** and **2**, unchanged by round 2 (`spec-review-r2.md`: "Three OWNER rows: 1a, 1b, 2 — correct and correctly weighted") |

---

## 14. Spec-review resolution

| Round | Revision reviewed | Verdict | Review note |
|---|---|---|---|
| 1 | 1 | CHANGES-REQUIRED | `docs/backlog/reviews/PBI-009/spec-review-r1.md` |
| 2 | 2 | APPROVE-WITH-NOTES | `docs/backlog/reviews/PBI-009/spec-review-r2.md` |

Round 1 (2026-09-12): CHANGES-REQUIRED — 2 High, 5 Medium, 3 Low; **all nine applied in revision 2,
none deferred.** The reviewer re-read and line-counted ~40 cited ranges across `derive.py`,
`export_sessions.py`, `refresh.py`, `local/records.py`, `local/collector.py`, `site/index.html`,
`tests/page.test.mjs`, `CLAUDE.md`, the parent spec and the PRD, and reported **zero citation drift**.
The scope check was clean, the store design and two-writer avoidance verified, and the
`PARSER_VERSION` 6→7 reasoning confirmed **correct and necessary**. Neither High finding was a figure
the spec got wrong; both were measurements the spec **did not take**.

### What the reviewer's independent re-measurement confirmed

Re-measured on the same corpus and **confirmed**: ends-on-assistant **15/15**; final block ends `"?"`
**1/15**; solicits without `?` **6**; `"permission to use"` present and boilerplate **15/15**;
`is_error: true` **146 exactly**; `stop_reason: "tool_use"` at the end **2**; and the whole
`toolDenialKind` record shape — top-level, `type: "user"`, `isMeta` absent, `toolUseResult` a plain
string, `sourceToolAssistantUUID` and `content[0].tool_use_id` present — **on all 11 denial records**.
The `toolDenialKind` fail-safe (absence yields zero refusal items, never a false "nothing waiting") was
verified. §3.5 records the full comparison, including the three rows that changed.

### Disposition of each finding

| Finding | Sev | Disposition in revision 2 |
|---|---|---|
| **F-1** | **High** | **Applied, and it changed the design's story rather than its mechanism.** New **§3.3.1** adds the measurement revision 1 never took: 36 `AskUserQuestion` calls, **36 answered, 0 unanswered, D1 fires on 0 of 15**. §1.1 is rewritten — the old "two of three detectors are crisp, only one is a heuristic" is kept only as a statement about *signals*, and explicitly corrected as a statement about the *panel*: **on measured data the question half is produced entirely by D2**. §7.1's heading and opening now present D1 as **rare-but-high-value, not primary**, with the reason it still ships (precision 100% by construction; the state it catches is exactly the panel's subject; the zero is a property of this corpus, not the format). §1's intent table gains a measured-rate column. §9 row 2 is re-put with F-1's consequence — disabling D2 leaves FR-107/FR-108 rendering a permanently empty panel — and §12 records the limit in the owner's language. The ask-session count is also corrected **13/15 → 12/15** on the reviewer's independent count; **the one-session difference is reconciled in round 2** (§3.5): 13 counts the literal string `AskUserQuestion` anywhere, including session `233bec8e`, which carries the string with zero actual calls, while 12 counts only sessions with a real `tool_use` block — nothing turns on it, since the unanswered count is 0 either way |
| **F-2** | **High** | **Applied.** The false premise is corrected at source: §3.2's table gains a measured-count column — `automode-blocked` **8 of 11**, `user-rejected` **1 of 11**, `permission-rule` **1**, `automode-unavailable` **1** — and states plainly that revision 1 had it backwards. §9 row 1 is **split into 1a and 1b** and re-aimed: **1a asks about `automode-blocked`**, the kind that carries D3's volume and that revision 1 listed without asking, and is marked the one that matters if the owner answers only one; **1b** keeps the `user-rejected` question at its true weight. The noise risk is now put to the owner in the kind where it actually sits |
| **F-3** | **Med** | **Applied, by the first of the two routes the finding offered.** W-a no longer claims an extraction. `exporters/derive.py:438` was re-read at `560e296` and is quoted verbatim in §4.1: it tests `str` content only and does not consult `isMeta`. **Line 438 is left exactly as it is**, so `firstPrompt` does not move, and `is_owner_message()` becomes a **separate new predicate** used only by the new detectors — where it must be wider, because it backs the clearing rule and a reply typed beside a pasted attachment arrives as list content. The "no behaviour change" claim is gone, the contradiction between T-4 and T-12 with it; T-12 now explicitly pins that a list-content opener leaves `firstPrompt` unchanged, and **new T-25** pins the difference between the two tests directly — the exact case in which revision 1's two criteria disagreed |
| **F-4** | **Med** | **Applied.** New criterion **W-14** names the actor: **the owner**, or a rendered-screenshot evidence artefact under `docs/backlog/evidence/` linked from the PBI file's Evidence section, confirms the panel **in both themes** at close-out. It cites `CLAUDE.md:131-139` and, individually, the four NFRs NFR-22 incorporates — NFR-9 (`docs/prd/dispatch-board.md:548`), NFR-10 (`:549`), NFR-13 (`:552`), NFR-14 (`:553`) — noting that only NFR-9 and NFR-14 are regex-checkable and therefore that W-12 covered only half the requirement. It carries **NFR-22's own reservation clause** (`docs/prd/dispatch-board.md:570`): `--human` only for waiting items and assumptions awaiting a human. A note after §11's table records that the artefact is close-out bookkeeping of the declared-docs-touch class (`docs/backlog/specs/dispatch-board.md:216-217`), not a source-area change, with the two existing artefacts under `docs/backlog/evidence/` as precedent. The string "NFR-22" now appears in this spec eleven times |
| **F-5** | **Med** | **Applied.** The vacuous probe is replaced. §8.4 states why `/Waiting on you/` fails as a probe — it matches the panel **title**, which §8.3 renders in the empty state too, so it would pass on two identically empty panels, the precise failure `tests/page.test.mjs:1461-1462` warns against — and specifies **two item-content probes** instead: the fixture's verbatim question text, and `/Refused/` (the §8.2 D3 tag), so neither detector class can be silently absent. The fixture requirement is tightened to carry both a question and a refusal. **New T-29** is a negative control: with the fixture's `waiting` block removed, the probes must **fail**. W-11 is restated to match |
| **F-6** | **Med** | **Applied, as the finding required, and treated as a precondition of shipping D2.** New **§7.6** adds both bounds. The reasoning the finding supplies is stated in §7.2: conditions 1, 2, 3 and 5 hold for **13 of 15** sampled sessions, so **condition 4 is D2's only real discriminator**, and a clearing rule that fires only on a later owner message can never clear a session the owner walked away from — the item would persist the full 7-day retention window (`board.config.json:56`; liveness window `:62`). The bounds: a **48-hour age bound** on D1, D2 and D3 items, and a **20-item panel-level cap** with a "+N more waiting" line and a drop order that never drops an exact D4 row. Both are **render-time** rules, so W-9 still holds — `waiting` carries no time-dependent value and a re-export is byte-identical. The panel states when a bound has hidden something. New criterion **W-15**, new cases **T-27** and **T-28**, and §9 row 11 records the two values as tunable with an FYI to the owner |
| **F-7** | **Low** | **Applied.** The deviation is now explicit in both places the finding allowed. **§9 row 12** records it as a deliberate, justified deviation: FR-108 (`docs/prd/dispatch-board.md:467`) makes idleness the collector's mark, §4.3 computes it on the page, the observable outcome is identical and only the computation site moves — with the two drivers the reviewer independently verified (`exporters/export_sessions.py:143-146` and the signature at `:170-179`; the digest at `exporters/refresh.py:82-85`). **§12** carries it as a recorded limit. It is no longer a silent departure from a requirement's wording |
| **F-8** | **Low** | **Applied.** §8.3 now states that the empty state uses the **muted style and carries no `empty` class**, with the mechanism named: the panel sits inside `panel-overview`, and `tests/page.test.mjs:1463` computes `emptyPanels` with `/class="empty"/`, so an `.empty` empty state would fail `:1464-1465` in every environment whose fixture lacks waiting data — including this PBI's own §8.4 criterion. W-10 carries the rule and **new T-26** asserts it with the same regular expression the suite uses, so criterion and check cannot drift apart |
| **F-9** | **Low** | **Applied as recorded-and-banked, per the finding's own "fix or bank"; NFR citation corrected in round 2.** **§9 row 13** records the pre-existing conflict, re-read and confirmed at `site/index.html:777` and `:784` (the ADR cards, `--tone:var(--human)`, the adjacent instance the finding did not name). Revision 2 cited **NFR-22** as the reservation being diluted; **round 2 withdrew that framing** — NFR-22 (`docs/prd/dispatch-board.md:570`) governs only next-iteration views and the Agent catalogue tab and does not reach the Decisions tab, so the correct citation is **NFR-10** (`:549`), the page-wide `--human` reservation, already *Partly met*. Revision 3 also corrects the review's own suggested route: the review proposed folding the follow-up into "PBI-002's existing NFR-10 remedy", but PBI-002 is **`Done`** (squash-merged `049f27e`, PR #12; `docs/backlog/pbi/PBI-002-page-fixes.md`) and its remedy already shipped, fixing only the brand dot — a closed PBI has no live remedy for this instance to join. Row 13 now directs the follow-up to a **new item through `pbi-intake`**. Still **out of scope for PBI-009 unless the owner says otherwise**: pre-existing, on the Decisions tab rather than this panel, and outside what W-14 covers |

### Round 2 (2026-09-12): APPROVE-WITH-NOTES, applied in revision 3

`docs/backlog/reviews/PBI-009/spec-review-r2.md` — same-vendor-subagent tier, clean context, read-only,
live tree `560e296`, every citation re-read and line-counted, no `sed`. Verdict **APPROVE-WITH-NOTES**:
4 new findings (2 Medium, 2 Low), two author challenges resolved in the author's favour, and one
correction to round 1's own F-9 disposition. The reviewer re-verified round 1's resolution held, re-ran
the corpus measurements a second time and confirmed them again (§3.5), found the scope check clean, and
judged the three OWNER rows (1a, 1b, 2) "correct and correctly weighted" and D2-ships-enabled unchanged.

| Finding | Sev | Disposition in revision 3 |
|---|---|---|
| **N-1** | Med | **Applied.** §8.4 now states that both equivalence probes must be evaluated against `seen['panel-overview']` alone, not the whole-board `seen` map the general `Object.values(seen).some(...)` check at `tests/page.test.mjs:1467-1470` uses — `/Refused/` is otherwise vacuous, since `site/index.html:1070` renders `<th class="num">Refused</th>` unconditionally in the Usage tab. W-11, T-23 and T-29 restated to match |
| **N-2** | Med | **Applied.** The W-14 evidence-route note is corrected: `docs/backlog/specs/dispatch-board.md:216-217` authorises only `CLAUDE.md`/`README.md` touches, not `docs/backlog/evidence/**`, which sits outside `docs/backlog/pbi/PBI-009-waiting-on-you.md:7`'s `allowed_areas`. The note now states the owner-confirms-directly route is scope-clean and primary, and the delegated-artefact route needs an explicit scope extension obtained first, rather than assuming the parent-spec citation already covers it |
| **N-3** | Low | **Applied.** `is_owner_message()`'s docstring (§4.1) now rejects a list-form `text` block beginning with `<`, the same rule the string branch already applies, with the reasoning stated inline. T-4 gains the matching negative case. Measured 0 such records in the 15-transcript sample; the fix closes a theoretical gap T-4's own framing already implied |
| **N-4** | Low | **Applied.** §7.6's panel-level cap row now states the full ordering in one place: the panel displays surviving items newest-first, drops by kind in the stated order when the cap binds, and **within a kind drops the oldest items of that kind first**. T-28 restated to name the within-kind order |

**The two challenges, adjudicated:**

- **12 vs 13, reconciled.** §3.5 and F-1's disposition above now state the reconciliation directly: 12
  counts sessions with an actual `AskUserQuestion` `tool_use` block (36 calls, 36 answered, 0
  unanswered); 13 counts transcripts containing the literal string anywhere, one wider because session
  `233bec8e` carries the string with zero calls. The spec keeps **12**, the structural figure; immaterial
  to D1, but closed rather than left as "not reconciled".
- **§7.6's 48 h / 20 values stay non-OWNER.** The reviewer's own challenge concluded "the author is right;
  non-OWNER stands": both are render-time view constants that delete nothing and are reversible in one
  line, differing in kind from a row that decides what the feature is. §9 row 11 now records this
  adjudication explicitly, alongside its existing FYI.

**Correction to round 1's F-9, carried into row 13.** The round-2 reviewer flagged that round 1's own
disposition of F-9 cited the wrong requirement — **NFR-10** (`docs/prd/dispatch-board.md:549`), not
NFR-22 (`:570`), governs the `--human` misuse at `site/index.html:777`/`:784`, since NFR-22 reaches only
next-iteration views and the Agent catalogue tab. Separately, the reviewer's own suggested follow-up
route — fold it into "PBI-002's existing NFR-10 remedy" — does not hold up: PBI-002 is **`Done`**
(squash-merged `049f27e`, PR #12), its NFR-10 remedy already shipped (the brand dot only), and a closed
PBI has no live item for a new instance to join. §9 row 13 is corrected on both points: the citation is
NFR-10, and the recommended route is a **new item through `pbi-intake`**, not PBI-002.

**Correction, 2026-09-13 (orchestrator, re-grounded against the source).** The routing above — "a new item through `pbi-intake`" — is **withdrawn**. Read against NFR-10's actual text, `site/index.html:777` and `:784` are not a violation: NFR-10 reserves `--human` for "something awaiting a human", a proposed ADR awaits the owner's accept-or-reject, and the page maps `proposed` to `--human` deliberately at `:114`. Round 1 (F-9) and round 2 both judged these lines against NFR-22's stricter reservation, which does not govern the Decisions tab. No intake item is raised; row 13 now records it as an owner FYI. NFR-10's "Partly met … planned in PBI-002" status note in the PRD is stale, because PBI-002 shipped the brand-dot remedy, and is left for a PRD bookkeeping chore. No design decision or acceptance criterion changes.

### Where revision 3 leaves the owner

Revision 1 put two rows to the owner and the reviewer judged "the 2-of-10 split is right in count,
wrong in content". Revision 2 put **three owner rows, one blocking**, and round 2 confirmed all three
unchanged: row **2** (does D2 ship enabled) re-put with the corrected recall of ≈4/7 and with the true
cost of the alternative; rows **1a** and **1b**, replacing revision 1's row 1, aimed at
`automode-blocked` first. Rows 3 to 13 are settled without the owner, two of them carrying an FYI
(row 11's bound values, reaffirmed non-OWNER in round 2; row 13's banked `--human` conflict, now routed
to a new `pbi-intake` item rather than PBI-002). The reviewer's added item — a named human actor for the
NFR-22 visual check — is **W-14**, a close-out step rather than a question, so it does not block the
build.

**The spec's recommendation on the one blocking row is to enable D2**, contingent on §7.6 shipping
with it. That is the reviewer's conclusion too, and the evidence for it is the measurement revision 1
did not take.
