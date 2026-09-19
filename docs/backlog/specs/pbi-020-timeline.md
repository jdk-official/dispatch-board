---
title: "Timeline view: runs as bars on a real-clock axis, with usage-limit refusals and idle gaps"
pbi: PBI-020
parent: docs/backlog/specs/dispatch-board.md (revision 5, approved)
revision: 2
status: round 1 returned **APPROVE-WITH-NOTES** (`docs/backlog/reviews/PBI-020/spec-review-r1.md`); every note F-1..F-8 is applied in this revision, none deferred (§10). The gate passes on this revision; Q-1 still needs the owner before the build starts (§8).
grounded_at: 560e296 ("PBI-025: local tab and status records from the collector (#23)")
---

# PBI-020: Timeline view (per-PBI spec)

Every file and line cited below was read in the working tree at `560e296` and the line numbers counted
by reading, not by offset arithmetic.

---

## 1. Intent

PBI-020 fills **FR-101** (the run record carries each run's start time and end time — PBI-003 defined
the fields, this PBI writes them) and builds **feature 9**, the timeline view: **FR-122** (runs drawn
as bars on a real-clock axis from start to end), **FR-123** (each recorded usage-limit refusal marked
at its time on the axis) and **FR-124** (every interval longer than the running window with no shown
run active shaded as an idle gap). Its one PRD criterion is **AC-83**: two runs from 10:00–10:20 and
10:05–10:30 draw bars that overlap between 10:05 and 10:20.

The PBI is deliberately small at the exporter end and mostly a page change. Its areas
(`docs/backlog/pbi/PBI-020-timeline.md:7`) are `site/**`, `tests/page.test.mjs`, `exporters/**`,
`tests/test_*.py`. Nothing else is touched; §9 lists what that excludes and why.

**What this spec refuses to do.** A timeline is the view that most tempts a page into inventing data:
a run with no start gets a guessed one, a bar with no end is stretched to "now", an axis is quietly
broken so that minute-long bars look big. This spec forbids all three (§4.4, §4.3, §4.5) and pins
each refusal with a test whose fixture actually contains the awkward case.

---

## 2. The data as it actually is

### 2.1 Run times today

`derive.agent_row()` (`exporters/derive.py:475–500`) builds every run row with both times:

- `begin = state['launched'].get(tuid) or sub['first']` (line 483) — the Agent tool-use time from the
  main transcript, else the agent transcript's first timestamp. **`None` when neither exists.**
- `end = (fin or {}).get('at') or sub['last'] or begin` (line 485) — the finish notification's time,
  else the agent transcript's last timestamp, else `begin`.
- `min` (line 489) comes from `classify()` (`exporters/derive.py:240–245`): the reported
  `duration_ms` rounded to minutes, else `round((epoch(end) - epoch(begin)) / 60)`, else `0`.

`derive.run_doc()` (`exporters/derive.py:727–739`) then publishes a fixed key list and **drops `end`
entirely**; it copies `start` only inside `if 'agentType' in r:` (line 735). Every subagent row has an
`agentType` key (set unconditionally at line 490, possibly `''`), so in practice: subagent rows publish
`start` when it is truthy, `runs.manual` rows publish neither. `CLAUDE.md:38` states this as the
contract ("`start` (its launch time; left out when unknown) … `runs.manual` rows carry neither").

### 2.2 The three populations — confirmed by existing tests

| Population | Store document today | Pinned by |
|---|---|---|
| Subagent run with a known launch or first timestamp | `start` present, no `end` | `tests/test_export_sessions.py:756–760`, `:770` |
| Subagent run whose launch time is unknown (no Agent tool-use record and no timestamped line) | **no `start`**, no `end` | `tests/test_export_sessions.py:772–780` (`test_no_start_when_the_launch_time_is_unknown`) |
| `runs.manual` row (in-line orchestrator work) | **no `start`**, no `end`, no `agentType` | `tests/test_export_sessions.py:782–789` (`test_manual_rows_carry_neither`) |

A `runs.manual` row *does* carry a start internally — `place_manual()` sets
`'start': a['end'], 'end': a['end']` from its anchor run (`exporters/derive.py:720`) — but that is a
**placement heuristic for the swimlane's ordering, not an observed time**. §3.2 keeps it unpublished.

`min` is required on every run document (`local/records.py:38`), including manual rows, where
`place_manual` sets it to `0` (line 721).

### 2.3 Usage-limit refusals today

`derive.reject()` (`exporters/derive.py:287–291`) records one entry per refusal —
`{at, resetsAt, type, overage}` — for any record with `apiErrorStatus == 429` or a `quotaLimits` key.
`usage_doc()` (`:370–381`) then **groups them by reset time and throws the individual times away**:
the published `usage.limits[]` entry is `{firstAt, refused, type, resetsAt}` (line 379). A window in
which the platform refused five requests publishes one time, `firstAt`, and the count `5`.

FR-123 says "each recorded usage-limit refusal at its time". With today's document that criterion can
only be met vacuously — one mark per group, whatever `refused` says. §3.3 publishes the times.

`aggregate_usage()` merges limits across a project's sessions by `resetsAt`
(`exporters/derive.py:571–582`), summing `refused` and keeping the earliest `firstAt`.

### 2.4 The running window (FR-124's threshold)

`runs.runningWindowMinutes` (default 10) is published on every session document as `windowMinutes`
(`CLAUDE.md:37`; `exporters/export_sessions.py:107`). The page already reads it with the same default:
`Number(s.windowMinutes) || 10` (`site/index.html:335`). The timeline reuses that value; it does not
introduce a second idle threshold.

### 2.5 The page it is being added to

`site/index.html` is content-only, one file, no external script (`CLAUDE.md:12`). The Dispatch
swimlane (`site/index.html:562–619`) is hand-built SVG string concatenation inside `renderDispatch()`:
a `viewBox="0 0 1180 H"`, `role="img"` with a sentence-long `aria-label` (line 570), lane bands, and
`fill`/`stroke` values taken only from tokens and from `toneOf` (line 288). The timeline is built the
same way, in the same function's panel, by the same means. No chart library is added — none can be:
the artifact's CSP allows scripts only from the named CDNs, and the page loads none today.

Escaping: `esc()` (`site/index.html:270`) escapes `& < > "` — not `'`. `md()` (line 272) allows code
spans and bold and is for repo-authored text. Run labels and verdicts are agent-written.

---

## 3. The exporter half — FR-101, filled

### 3.1 `run_doc()` publishes `end` beside `start`

In `exporters/derive.py:735–738`, extend the copied key list from `('agentType', 'start')` to
`('agentType', 'start', 'end')`, under the same `if 'agentType' in r:` guard and the same `if r.get(k)`
truthiness test. That is the whole change: two words and a comment.

Consequences, each of which a test pins (§6.1, §6.2):

- A subagent run with both times publishes `start` and `end`.
- A subagent run with no launch time and an undated transcript publishes neither `start` nor `end`,
  because `end` falls back to `begin`, which is `None`.
- **A run may still publish `end` without `start`, and that case must survive.** Revision 1 attributed
  it to `sub['last']`, which was wrong and the round-1 review corrected it (F-7): `add_agent` sets
  `first` and `last` together under one `if stamp(o):` (`exporters/derive.py:304–308`), so a transcript
  with a last timestamp always has a first, and `sub['last']` can never outlive `sub['first']`. The real
  path is `fin['at']` (`exporters/derive.py:483–485`): no Agent tool-use launch record for the tool-use
  id (`state['launched']` misses, so `begin = sub['first'] = None`) **and** an agent transcript with no
  timestamped line at all, but a finish notification that carries an `at`. Then
  `end = (fin or {}).get('at')` is a real time while `start` is `None`. The page treats such a run as
  unplaced (§4.4), because a bar needs a left edge. §6.2's fixture is built on this path — a finish
  notification plus an undated transcript — not on a transcript with a last timestamp and no first,
  which cannot exist.
- `end` is a string in the exporter's existing time form, which is why `local/records.py` types run
  times as `'str'` and not `'datetime'` (`local/records.py:22–24`).

### 3.2 `runs.manual` rows still carry neither — nothing is invented

`place_manual()` is **not** changed. A manual row's internal `start`/`end` are its anchor's end time,
chosen so the row sorts into the swimlane after the run it followed; publishing it would put a bar on
the clock at a time nobody observed, and would make a zero-length bar indistinguishable from a real
one-second run. Manual rows stay off the axis and are listed as unplaced (§4.4) with the reason "no
recorded start".

`CLAUDE.md:38`'s sentence "`runs.manual` rows carry neither" becomes wrong once `end` exists
(it would now be "carry none of the three"). See open question **Q-1**: `CLAUDE.md` is outside
PBI-020's `allowed_areas` (`docs/backlog/pbi/PBI-020-timeline.md:7`), and the parent spec's permission to update
it is **conditioned on a declared `docs` touch** (`docs/backlog/specs/dispatch-board.md:216–217`) which
PBI-020's own row does not declare (`:256`, against PBI-017 `:219` and PBI-018 `:220`, which list
`CLAUDE.md` explicitly). So the grant does not self-execute here, and the build leaves the file alone.

### 3.3 Refusal times, so FR-123 is not vacuous

In `usage_doc()` (`exporters/derive.py:371–381`), each window already accumulates its refusals; carry
their times:

- while grouping (line 377–378), append `r['at']` to the window's list when it is truthy;
- emit `'at': sorted(...)` on each published limit entry beside `firstAt`, `refused`, `type` and
  `resetsAt`. The list holds one time per refusal that had one; a refusal with no readable time
  contributes nothing, so `len(at) <= refused` always.

**The invariant, stated correctly (F-1).** Revision 1 claimed `at[0] == firstAt` whenever the list is
non-empty. That is **false**, and the round-1 review was right to catch it. `usage_doc()` sorts the
refusals on `x['at'] or ''` (`exporters/derive.py:372`), so a refusal whose `at` is `None` — `reject()`
writes `'at': stamp(o)`, which is `None` for an untimed record (`:287–291`) — sorts first, and the
window it creates takes `'firstAt': r['at']`, i.e. `None` (`:377`). Later timed refusals in the same
`resetsAt` window then fill `at` while `firstAt` stays `None`. So:

- `len(at) <= refused`, always;
- when `firstAt` is truthy and `at` is non-empty, **`at[0] >= firstAt`**, with equality whenever the
  window's first refusal had a readable time — which is the ordinary case;
- when the window's *first* refusal had no readable time, `firstAt` is `None` and `at` may still be
  non-empty. `firstAt` is **not** repaired to `at[0]`: this PBI carries the times, it does not change
  what `firstAt` means, and rewriting it would alter a field PBI-013 and the usage tab already read.
  The page handles the null case instead (§4.8).

`test_usage_doc_lists_a_refusal_window_whose_first_refusal_has_no_time` (§6.1) pins exactly this
ordering, so the corrected invariant is tested rather than asserted.

In `aggregate_usage()` (`exporters/derive.py:579–582`), when merging into an existing `resetsAt`
window, merge the lists too: `m['at'] = sorted(set(m.get('at') or []) | set(l.get('at') or []))`.
Deduplication matters because a project's sessions can record the same account-wide refusal.

This is the minimum that makes FR-123 mean what it says. The alternative — mark only `firstAt` and
write "+4 more" — was rejected: it would satisfy the words of FR-123 while showing one mark for five
refusals, which is exactly the vacuous reading the spec gate should refuse.

`usage` is typed `'object'` on the session shape (`local/records.py:30`) and **`'object|null'`** on the
project shape (`local/records.py:53`) — revision 1 cited `:54` and the wrong type; corrected per F-6.
Neither type inspects the object's contents, so the added key needs no record-shape change and cannot
fail `local/tests/test_conformance.py`. PBI-013's forecast reads `usage.limits[].resetsAt` and is
unaffected by an added sibling key.

### 3.4 Where the derivation lives, and what it does not disturb

The parent spec's rule — "All derivations live in one shared module under `exporters/`; the collector
imports it, never re-implements it" (`docs/backlog/specs/dispatch-board.md:87`) — is satisfied by
construction: both changes are inside `exporters/derive.py`, which
`exporters/export_sessions.py:52–56` re-exports and the collector imports. There is **no new derived
document**:

- no new collection, so `refresh.py`'s `MANAGED` tuple (`exporters/refresh.py:44`) is unchanged and the
  mass-delete guard sees exactly the documents it sees today;
- no new `projectTabs` document, so the two-writer split (`CLAUDE.md:41`) is untouched and **nothing in
  this PBI computes an owned-set at all** — `records.TAB_NAMES` is not read, imported or copied;
- run documents gain one optional field and session/project usage blocks gain one optional list, so the
  refresher's diff pushes the same documents it pushes today, with slightly larger bodies.

**Operational note, recorded from the round-1 review (not a finding).** Because every subagent run
document gains a key, **the first refresh after this merges rewrites every run document**: the
refresher's diff sees each one as changed and pushes all of them in one much larger batch than a normal
tick (it splits past 50 writes, per the Refresh procedure in `CLAUDE.md`). That is a one-off; the tick
after it is back to its usual size. It is not a mass delete, so no guard is involved, and nothing about
the procedure changes — the owner should simply expect one big push.

The timeline's geometry (axis, packing, gaps) is **page state, not derived data**: it depends on the
selected project and session and on the chosen window, all of which live in the page. Putting it in
`derive.py` would mean publishing a document per view. Nothing else in the page works that way — the
swimlane computes its geometry at render time — and a stored geometry would be stale the moment the
viewer changed the session filter.

### 3.5 The record shapes already allow this — no `local/**` edit, no follow-up PBI

`local/records.py:40–43` already lists `'start': 'str'` **and `'end': 'str'`** under the run record's
`optional` fields (`'start': 'str'` at `:41`, `'end': 'str'` at `:42`), exactly as the parent spec
promised ("the run record's start and end fields (FR-101), which PBI-020 fills",
`docs/backlog/specs/dispatch-board.md:227`). `validate()` also allows unlisted fields at every level
("Fields a SPEC does not list are allowed, and kept, at every level", `local/records.py:21`), so the
`usage.limits[].at` list validates
regardless. **No document designed here fails `local/records.py`, so no follow-up PBI is needed and
no edit under `local/**` is proposed.** `local/tests/test_conformance.py` drives the real exporters and
will see the new fields; it should stay green untouched, and §6.4 makes that an explicit check rather
than an assumption.

---

## 4. The page half

### 4.1 Where the timeline goes

**A panel on the Dispatch tab, directly above the Swimlane panel — not a new tab.** Reasons:

- The tab bar holds ten tabs today (`site/index.html:230–239`, counted: overview, spec, assumptions,
  decisions, backlog, git, findings, dispatch, catalogue, usage). FR-125–FR-128 and AC-84 govern its
  width at 1050 px; an eleventh tab reopens a requirement this PBI has no business touching.
- The timeline answers the same question as the swimlane — what the agents did, in what order — over
  the same scope. `renderDispatch()` already has `sorted()`, `laneList()`, `toneOf`, `agentRuns()` and
  `scopeName()` in hand, so the timeline needs no new scope plumbing.
- `tests/page.test.mjs:21` derives `tabNames` from the HTML, so a new tab would silently join the
  adapter equivalence check with no fixture behind it; a panel inside Dispatch joins a panel that
  already has one (§5).

The panel is `<div class="panel">` with a `.ph` header ("Timeline"), the existing legend idiom, a
`.pb.scroll` holding the SVG, and a `.pb.faint` footnote explaining what the axis is — the same
structure as the Swimlane panel (`site/index.html:612–614`). The Dispatch tile row is unchanged.

### 4.2 Scope: which runs are "the selected runs" (FR-122)

Exactly the runs the Dispatch tab already shows: `sorted()`, which is the project- and session-filtered
run list. Selecting a session narrows the timeline with everything else. Usage-limit marks (§4.8) come
from the session documents in the same scope, so a project view shows its sessions' refusals and a
single-session view shows only that session's.

### 4.3 Placing one run (FR-122)

For each run in scope, in this order — the first rule that applies wins:

| # | Condition | Bar |
|---|---|---|
| 1 | `start` and `end` both readable, `end >= start` | `[start, end]` |
| 2 | `start` readable, `end` missing or unreadable or `< start`, `min > 0` | `[start, start + min minutes]`, drawn with a dashed right edge |
| 3 | `start` readable, no usable `end`, `min == 0` | an **instant marker** at `start`: a bar of the minimum width, drawn with a dashed right edge |
| 4 | no readable `start` | **not placed** — see §4.4 |

Rule 2 uses `min`, which is the run's own reported duration (`exporters/derive.py:240–245`), not a
guess. A time is "readable" when `Date.parse` gives a finite number; a malformed string is treated as
missing, never as `0` (epoch 1970 would throw the axis across 56 years).

**A run still in flight** (`kind === 'running'`) is placed by rule 1 from `start` to `end`, where `end`
is its last observed activity, and is drawn **open-ended**: no right cap, a dashed right edge, and the
existing `runglow` class. The bar is *not* stretched to the viewer's clock or to `meta/lastRefresh`.
The board only knows when the agent was last heard from; drawing a bar to "now" would assert activity
that was never observed. The open edge and the legend entry ("still running — the bar ends at its last
recorded activity") say exactly that, and the footnote repeats it.

### 4.4 Runs with no `start` — the decision

**A run with no readable `start` is never placed on the axis, never given a synthesized start, and
never silently dropped.** It appears in an **"Off the axis"** list immediately below the chart, inside
the same panel: one row per run with its lane, label, outcome tag, minutes and the reason
("no recorded start time"). The panel header carries the count as
`N of M runs have no recorded start time` whenever `N > 0`, and shows nothing when `N == 0`.

This is the only honest placement. The two real sources of a missing start are an agent whose
transcript carries no timestamp at all (`tests/test_export_sessions.py:772–780`) and a `runs.manual`
row, whose only candidate time is its anchor's end (§3.2). Both would be fabrications on a clock axis,
and both are real rows the owner should still see — a manual row is in-line orchestrator work that
genuinely happened.

The equivalent rule for the right edge is rule 3 of §4.3: a run with a start but no duration is an
instant, drawn as one, not widened to look like work.

### 4.5 The axis, and the three scales

**Domain.** Let `placed` be the runs of §4.3 rules 1–3. `spanStart = min(bar start)`,
`spanEnd = max(bar end)`.

**Window.** A `<select>` in the panel header offers *Last 6 hours*, *Last 24 hours*, *Last 7 days*,
*Everything*, always in that order so the markup is stable. It is **anchored at `spanEnd`, not at the
viewer's clock**, so the same data renders identically in both adapters and in a test. The default is
the first option whose length covers `spanEnd - spanStart`, and *Everything* when none does — so a
half-day project needs no interaction to show everything, and a three-week project opens on its last
7 days rather than as a hairline. The choice is page state, re-applied on every re-render by the
mechanism §4.12 names — **not** "like the session filter", which revision 1 said and which is wrong: the
session and project selects live in the header and are bound once at load (`site/index.html:1177`,
`:1185`), while this one is inside the markup `renderDispatch()` replaces. The choice is reset when the
project or session selection changes.

`domain = [max(spanStart, spanEnd - window), spanEnd]`, then padded by 2% at each end, and widened
symmetrically to a **minimum of 10 minutes** so a single instant run does not produce a zero-width
scale. Runs entirely left of the domain are counted in the footnote ("N runs before this window").

**Clipping at the domain's left edge (F-3).** A run that *straddles* the left edge — it began before the
window and was still running inside it — is neither entirely left nor wholly inside, and revision 1 left
it unspecified; with §4.6's "the bar's x is always the true start" it would be given a negative x and
drawn outside the `viewBox`. The rule: **every bar is clipped to the domain.** The drawn geometry is
`x = max(x(barStart), x(domainStart))` and `right = min(x(barEnd), x(domainEnd))`, so no bar coordinate
is ever left of the axis origin or right of its end. A bar clipped at the left is **marked as clipped**:
a square (un-rounded) left cap instead of the 4 px radius, a 2 px `var(--ink-3)` tick at the clip, and
its `<title>` opens "started before this window — ". §4.6's "true start" rule is therefore narrowed to
its real meaning: the *minimum-width* widening of a short bar may only extend it right, never move its
left edge left; clipping to the domain is a separate and stated exception. A clipped run is **not** also
counted in "N runs before this window" — it is drawn, and counting it as hidden would double-report it.
Pinned by the "straddling the left edge" case in §6.3 and by AC-T15.

**Ticks.** The step is the smallest of `1, 2, 5, 10, 15, 30 minutes; 1, 2, 3, 6, 12 hours; 1, 2, 7 days`
that yields at most 10 intervals across the domain. Ticks are placed at whole multiples of the step.
Labels use the page's existing time formatter (`when()`, as the header's "data as of" does,
`site/index.html:389`) so the timeline agrees with the rest of the board; a date label is added at each
day boundary. Labels are the page sans with tabular figures — **no monospace anywhere in this view**,
per the design rules (`CLAUDE.md:135`).

**The three scales, answered:**

- **One run.** Domain is that run's bar padded to at least 10 minutes; the step lands at 1 or 2 minutes;
  one lane band; the bar is drawn at its true width. No special case, no empty state.
- **A thousand runs.** Two bounds, both stated on the page rather than silently applied. First, at most
  **600 bars** are drawn, the most recent by start; the rest are counted in the footnote. Second, within
  each lane band bars are packed greedily into at most **10 sub-rows** (§4.6); a run that does not fit is
  counted in the same footnote line ("N runs did not fit this window — narrow the window"). Height is
  therefore bounded at 10 lanes × 10 sub-rows regardless of input, and no run is ever both undrawn and
  uncounted.
- **A run in flight.** §4.3: open-ended bar, `runglow`, legend and footnote.

**What the axis never does:** it is strictly linear real clock. No axis break, no log scale, no
compression of idle stretches. AC-83 is a statement about the clock, and an elided axis would make
"overlapping between 10:05 and 10:20" a claim about pixels instead of time. Idle stretches are shaded
(FR-124), which is the PRD's own answer to long gaps.

### 4.6 Lane bands and overlap (AC-83)

One horizontal band per lane, in `laneList()` order, reusing the swimlane's band idiom
(`site/index.html:571–576`): alternating `--raised`/transparent fills, the `human` lane in the violet
treatment, the lane name and its caption at the left of the band rather than above it.

Within a band, bars are laid into sub-rows by first fit, ordered by start: a bar goes into the first
sub-row whose last bar ends at least 4 px before this bar begins. **Two runs that overlap in time are
therefore always in different sub-rows and both fully visible** — which is what AC-83 requires; a
single-row lane would hide one bar behind the other and satisfy the criterion only by accident.

Bar geometry: height 14, radius 4, fill `var(--raised)` for `done` and `var(--surface)` otherwise,
stroke `toneOf[kind]` (`site/index.html:288`) at 1.5 — the swimlane's own mapping, so a verdict has the
same colour in both views. Minimum drawn width **3 px** so a one-minute run at day scale is still
visible and hoverable; the bar's x is always the true start, so a widened bar can only ever extend
right, and the footnote says so. Each bar carries an SVG `<title>` with the label, outcome, start, end
and minutes, and the run's id as `data-run` for PBI-014's detail view to hang off later.

### 4.7 Idle gaps (FR-124)

The active set is **every placed run in the domain, whether or not its bar was drawn** — a run that did
not fit a sub-row is still a run that was active, and shading over it would be a lie. Take the union of
their intervals, subtract it from the domain, and shade each remaining maximal interval **strictly
longer than `windowMinutes`** (§2.4).

Shading is a full-height rect in `color-mix(in srgb, var(--ink-3) 8%, transparent)` with the lane bands
showing through, plus a centred label when the gap is at least 60 px wide, and an SVG `<title>` with the
same text at any width. A gap exactly equal to the window is not shaded; "longer than" is read strictly.
Instant runs (§4.3 rule 3) cover zero time, so two instants an hour apart do produce an idle gap between
them — correct, and pinned by a test.

**What "idle" is allowed to mean (F-2).** The active set is built from *placed* runs, so an interval in
which only **unplaced** work happened — an undated subagent, or any `runs.manual` row of in-line
orchestrator work (`exporters/derive.py:720`; `tests/test_export_sessions.py:782–789`) — is shaded as
idle even though work was done. FR-124 permits this ("no **shown** run active"), but the page must not
imply the stronger claim. So the word "idle" never stands alone:

- the visible label reads **"idle 3 h 12 m — no run on this axis"** (and "— no run on this axis" is
  dropped only when the gap is too narrow for the label at all, where the `<title>` still carries it);
- each shaded gap's `<title>` reads "no run on this axis was active for 3 h 12 m";
- the `aria-label` (§4.10) says "N idle gaps, where no run on this axis was active";
- the footnote states it once in full, and, whenever the view has at least one unplaced run, names the
  consequence: **"Idle shading means no run on this axis was active. N runs are off the axis (they have
  no recorded start time) and their time is not represented here."**

This is a labelling requirement, not a geometry change: the shading is still computed from placed runs,
which is the only set whose extent is known. AC-T5 carries the wording assertion.

### 4.8 Usage-limit refusals (FR-123)

From the session documents in scope, take every `usage.limits[]` entry and every time in its new `at`
list (§3.3). Each time inside the domain is drawn as a **1 px vertical rule in `var(--nogo)` across the
full chart height, with a small solid triangle at the axis**, carrying an SVG `<title>`:
"usage limit refused at <time> — <type>, resets <time>". Refusals falling outside the domain are
counted in the footnote ("N refusals outside this window"). Times are deduplicated across sessions of
one project, because an account-wide refusal can appear in two transcripts.

**Backward compatibility with a store that has not been re-exported:** a limit entry with no `at` list
falls back to a single mark at `firstAt`, whose `<title>` reads "first refusal in this limit window
(N refused)". This is what the live artifact will show between the code landing and the next refresher
push, and it must not be mistaken for the finished behaviour — the test for AC-T8 uses a fixture with
`at`, and a separate test covers the fallback.

**The fallback is named in the footnote, not only in a `<title>` (F-8).** §4.10 insists that counts be
real text somewhere other than a tooltip, and a mark that stands for five refusals is exactly such a
count. Whenever any drawn mark came from the fallback, the footnote carries:
**"N limit windows show only their first refusal (M refusals in total); this store has not been
re-exported since the timeline landed."** When no entry falls back, the sentence is absent — the page
never explains a state it is not in.

**A limit entry whose `firstAt` is null.** §3.3 shows this is reachable: a window whose first refusal had
no readable time keeps `firstAt: None`. Such an entry draws marks from its `at` list as usual, and draws
**no fallback mark at all** when `at` is absent or empty — `Date.parse(null)` is not finite, so the
"readable time" rule of §4.3 applies unchanged and no mark is placed at epoch or at the domain's edge.
Its refusals are counted in the footnote's "refusals outside this window" line, with the reason "no
recorded time". Pinned by the "limit entry with a null firstAt" case in §6.3.

When no refusal is recorded anywhere in scope, no marks are drawn and the legend omits the entry. The
panel does not claim "no limits hit"; that statement belongs to PBI-013's forecast (AC-80).

### 4.9 Empty and degenerate states

| Case | What the panel shows |
|---|---|
| No runs in scope at all | `renderDispatch()`'s existing early return at `site/index.html:564` already replaces the whole panel; the timeline is never reached. Unchanged. |
| Runs in scope, none with a readable start | No SVG. `<div class="empty">No run in this view has a recorded start time.</div>` plus the full "Off the axis" list, so every run is still visible. |
| Exactly one placed run | §4.5, one run. Drawn normally. |
| All placed runs at the identical instant | Domain widened to the 10-minute minimum around that instant; bars stack into sub-rows; no division by zero anywhere — the scale function guards a zero-width domain before dividing. |

### 4.10 Design rules, and what moves

Against `CLAUDE.md:131–139`:

- **Professional dashboard.** A panel in the established `.panel` / `.ph` / `.pb` idiom, under the
  Dispatch tile row. No hero, no display type, no new heading scale.
- **Status-tile language.** No new tiles are added; the Dispatch row already counts runs, running,
  verdicts, cut off and tokens, and a timeline tile would restate them.
- **No wide monospace.** Every string in the view — tick labels, durations, lane names, run labels —
  is the page sans with tabular figures. Run ids appear only in `data-run` attributes and `<title>`
  text, never as displayed monospace.
- **Colours only through tokens, dark-first.** `toneOf` for verdicts, `--nogo` for limit marks,
  `--ink-3` mixed for idle shading, `--raised`/`--surface` for fills, `--rule` for the axis. No literal
  colour is introduced.
- **Motion only when it is true.** The only animated element in the timeline is a run whose `kind` is
  `running`, which gets the existing `.runglow` class (`site/index.html:200`) — already defined inside
  `@media (prefers-reduced-motion: no-preference)` (line 196), so reduced motion silences it with no
  new CSS. **Nothing else moves**: no bar grow-in, no axis transition, no scrolling animation, no
  pulsing on idle gaps or limit marks. A timeline that animates on every re-render would animate every
  10 minutes for data that did not change.
- **Accessibility.** `role="img"` with an `aria-label` in the swimlane's sentence style (line 570),
  naming the run count, the window, the number of idle gaps — qualified as "where no run on this axis
  was active" (§4.7) — and the number of limit marks, so a screen reader gets the summary the picture
  carries. The "Off the axis" list and **every footnote count** are real text, not only `<title>`
  tooltips: that includes the idle qualification (§4.7), the `firstAt` fallback and its total (§4.8),
  the runs before the window, the undrawn runs and the refusals outside the window.

### 4.11 Escaping

Every value from the store passes through `esc()` before entering the SVG string: run labels, verdicts,
lane names, `<title>` text, `data-run` values, and the formatted times. `md()` is **not used anywhere
in this view and is not widened** — run labels and verdicts are agent-written text, and the code-span
and bold allowance exists for repo-authored text. All generated attributes are quoted with double
quotes, since `esc()` escapes `"` but not `'` (`site/index.html:270`). Numeric geometry is computed
from `Number(...)` values and never interpolated from store strings.

### 4.12 The window control: the mechanism that survives a re-render (F-4)

The window `<select>` is the view's only interactive control, and `renderDispatch()` assigns
`p.innerHTML = ...` over the whole Dispatch panel (`site/index.html:604`) on **every** store change, so
a listener attached to the old markup and a choice held in the old element are both destroyed each
render. Revision 1 asserted the choice was "re-applied on re-render" without naming how. It is:

1. **The choice is module state, not DOM state.** A variable beside the page's other view state
   (`view`, `sel`) holds the chosen window key; it is the only place the choice lives. It is reset to
   the computed default (§4.5) when the project or session selection changes, and is otherwise
   untouched by a re-render.
2. **The markup carries the choice.** The emitted `<option>` for the held key carries `selected`, so the
   freshly written markup is already correct before any script runs. Immediately after the `innerHTML`
   assignment the page also sets `$('tl-window').value` from the same variable, because a re-used
   element keeps a `value` property that the new markup does not overwrite — and the test harness's
   element stub is exactly such a re-used element (`tests/page.test.mjs:47–52`, memoised by id).
3. **The listener is attached once per element, guarded by a flag on the element.** After each render
   the page attaches its `change` listener to `$('tl-window')` only if the element does not already
   carry the marker (a `dataset` flag it sets at the same time). In the browser each render produces a
   fresh element, so the flag is absent and the listener attaches exactly once; in the harness the stub
   persists, the flag is present from the first render, and the listener is **not** stacked —
   `addEventListener` on that stub appends without de-duplicating (`tests/page.test.mjs:50`), so an
   unguarded re-attach would fire the handler once per render and re-enter `renderDispatch()`. The
   handler itself is therefore also written to be re-entrant-safe: it sets the variable and calls
   `renderDispatch()` once, with no further state.
4. **It is exercised by a test, not just described.** The harness fires a real `change` event through
   `change('tl-window', …)` (`tests/page.test.mjs:83`), which is why the control needs a stable `id`
   rather than a class or a delegated listener on the panel — the helper invokes the listeners
   registered on that id's element and does not bubble.

AC-T16 pins both halves: the redraw, and the survival of the choice across a re-render driven by a
`change` event.

---

## 5. Both adapters (PBI-006's ten-panel check)

`tests/page.test.mjs:1461–1473` compares the whole rendered board between the store adapter and the
local API adapter, and asserts `emptyPanels(...)` is `[]` on both sides, so **no panel is compared
empty to empty**. `rendered()` (line 1432) covers `panel-dispatch`, so the timeline's markup enters the
comparison automatically — which is necessary but not sufficient: an equivalence check over a fixture
with no run times would compare one empty state to another and prove nothing.

Three additions keep it meaningful:

1. The `EQ_RUNS` fixture gains **start and end times on at least three runs**, including one pair that
   overlaps and one run whose `kind` is `running`, so the compared board actually draws bars.
2. One `EQ_SESSIONS` usage block gains a `limits` entry with an `at` list inside the fixture's span, so
   a limit mark is drawn on both sides.
3. The "the compared board shows X" list (`tests/page.test.mjs:1467–1469`) gains two rows —
   `['a timeline bar', /class="tl-bar"/]` and `['a usage-limit mark', /class="tl-limit"/]` — so a future
   change that stops drawing the timeline fails the equivalence check loudly instead of passing on two
   identically empty panels.

Nothing about adapter selection changes: both adapters deliver the same run and session documents, and
the timeline reads only those documents.

---

## 6. Test plan

Both Python suites are stdlib-only and the page suite is node built-ins only (`CLAUDE.md:106–110`).
Tests are written first, per owner decision D-9.

### 6.1 `tests/test_derive.py` (added cases; existing cases unchanged)

- `test_run_doc_publishes_start_and_end_for_a_subagent_row` — a row with both times publishes both.
  Extends the existing `run_doc` case at `tests/test_derive.py:238–244`.
- `test_run_doc_publishes_neither_for_a_manual_row` — the manual row of that same fixture publishes no
  `start`, no `end`, no `agentType`. Asserts `place_manual`'s internal times stay internal.
- `test_run_doc_omits_end_when_it_is_empty` — a row whose `end` is `None` publishes `start` only.
- `test_usage_doc_lists_every_refusal_time` — two refusals sharing a `resetsAt` and one without:
  the grouped entry carries `refused == 2` and `at == [t1, t2]`, `at[0] == firstAt`; the ungrouped
  entry carries its own single time.
- `test_usage_doc_lists_a_refusal_window_whose_first_refusal_has_no_time` (**new in revision 2, F-1**) —
  a window whose first refusal has no readable `at` (no `timestamp`, so `reject()` records `'at': None`)
  and two later timed refusals sharing its `resetsAt`. Asserts `firstAt is None`, `refused == 3`,
  `at == [t1, t2]`, and therefore that `at[0] == firstAt` does **not** hold while `len(at) < refused`
  does. This is the fixture the false invariant of revision 1 would have failed.
- `test_usage_doc_refusal_without_a_time_is_counted_not_listed` — `refused` counts it, `at` does not,
  so `len(at) < refused`.
- `test_aggregate_usage_merges_refusal_times_without_duplicates` — the same account-wide refusal in two
  sessions merges to one entry with one time.

### 6.2 `tests/test_export_sessions.py` (added cases; existing cases unchanged)

- `test_subagent_runs_carry_start_and_end` — end to end through the real exporter against a synthetic
  transcript tree; sits beside `test_subagent_runs_carry_agent_type_and_start` (line 756).
- `test_no_start_and_no_end_when_the_launch_time_is_unknown` — the undated-agent fixture of line 772
  publishes neither.
- `test_end_without_start_when_only_the_finish_notification_has_a_time` (**rebuilt in revision 2, F-7**)
  — the fixture is the real path of §3.1: an agent transcript with no timestamped line at all and no
  Agent tool-use launch record, plus a finish notification carrying an `at`. The run document publishes
  `end` and no `start`. It is **not** built as "a last timestamp with no first", which
  `exporters/derive.py:304–308` makes impossible.
- `test_manual_rows_carry_none_of_the_three` — extends line 782's case with `end`.

### 6.3 `tests/page.test.mjs` (added block, "timeline")

Cases, each a distinct fixture fed through the store adapter unless stated:

| Case | Fixture | Assertion |
|---|---|---|
| **AC-83 overlap** | runs at 10:00–10:20 and 10:05–10:30 | both bars exist; their x-ranges intersect, and the intersection maps back to 10:05–10:20 within one pixel; they are in different sub-rows |
| **Empty** | runs in scope, none with `start` | the timeline shows the "no recorded start time" empty state, the Off-the-axis list holds every run, and the swimlane below is unaffected |
| **Single run** | one run, 3 minutes | one bar, a domain of at least 10 minutes, at least two ticks, no error logged |
| **No runs at all** | empty run list | the existing Dispatch empty state (line 564); no timeline markup |
| **Unplaced** | one placed run, one undated subagent run, one manual row | exactly one bar; the header says "2 of 3 runs have no recorded start time"; both unplaced runs are listed by label |
| **In flight** | a `running` run with `start` and a last-activity `end` | the bar carries `runglow`, has a dashed right edge, and its right edge is at `end` — **not** at the test's clock |
| **End missing, min present** | `start`, no `end`, `min: 7` | the bar is 7 minutes wide with a dashed right edge |
| **Zero duration** | `start`, no `end`, `min: 0` | an instant marker at the minimum width, not a full-lane bar |
| **Idle gap (FR-124)** | two runs 90 minutes apart, `windowMinutes: 10` | exactly one shaded gap, labelled "idle 1 h 20 m", spanning the true gap |
| **Gap at the threshold** | two runs exactly 10 minutes apart, `windowMinutes: 10` | no shaded gap ("longer than", read strictly) |
| **Idle respects undrawn runs** | a run that did not fit a sub-row sits inside what would otherwise be a gap | no shading over it |
| **Limit marks (FR-123)** | a session whose `usage.limits[0].at` holds three times, two inside the domain | two marks drawn, each `<title>` naming its time and reset; the footnote counts the third |
| **Limit fallback** | a limit entry with `firstAt` and no `at` | one mark, `<title>` says "first refusal in this limit window"; **and the footnote names the fallback and the total refused, as real text outside any `<title>`** (F-8) |
| **Null `firstAt`** *(new, F-1/F-8)* | a limit entry with `firstAt: null` and no `at`, beside one ordinary entry | the ordinary entry's marks are drawn; the null entry places **no** mark (none at the domain edge, none at epoch), its refusals are counted in the footnote, and no `console.error` is logged |
| **Straddling the left edge** *(new, F-3)* | one run starting 2 hours before the domain and ending inside it, window *Last 6 hours* | exactly one bar; its left edge is **at the domain's left edge**, no coordinate in the emitted markup is negative or outside the `viewBox`, the bar carries the clipped-edge marking, its `<title>` opens "started before this window", and it is **not** counted in "N runs before this window" |
| **Window select: redraw** *(new, F-4)* | runs spanning 9 days (default *Last 7 days*), then `change('tl-window', '6h')` | the redrawn timeline's domain is 6 hours anchored at `spanEnd`, the bar count drops accordingly, and the footnote's "before this window" count rises to match — the two accounting for every run in scope |
| **Window select: survives a re-render** *(new, F-4)* | as above, then a store change that re-runs `renderDispatch()` | the `<select>` still shows *Last 6 hours* (the `selected` option **and** the element's value), the domain is still 6 hours, and firing `change` again a second time redraws once — asserted by the handler's effect, so a stacked listener that re-entered `renderDispatch()` would fail |
| **Idle wording** *(new, F-2)* | two runs 90 minutes apart with `windowMinutes: 10`, plus one `runs.manual` row in scope | the shaded gap's label and `<title>` both qualify idle as "no run on this axis", the `aria-label` says the same, and the footnote names the off-the-axis count and that its time is not represented |
| **Scale** | runs spanning 9 days | the default window is *Last 7 days*, the select shows all four options, and the footnote counts the runs before the window |
| **Volume** | 1200 synthetic runs in one lane | at most 600 bars in the markup, at most 10 sub-rows in that lane, the footnote states both counts, and the counts plus the drawn bars account for all 1200 |
| **Escaping** | a run whose label is `<img src=x onerror=alert(1)>` and a verdict with backticks and `**bold**` | no raw `<img` in the panel; the backticks and asterisks appear literally, proving `md()` was not applied |
| **Reduced motion** | a `running` run | the only animated class in the timeline markup is `runglow`; assert no other `class="flow"` or animated class appears in the timeline's markup |
| **Scope** | a project with two sessions, then one session selected | the timeline's bar count and limit marks narrow with the session filter, matching the swimlane's run count |

The suite fails on any unexpected `console.error` (`CLAUDE.md:109`), so a renderer that throws on a
malformed time fails rather than silently emptying the panel. One case feeds a run whose `start` is the
string `"not a time"` and asserts it is listed as unplaced with no error logged.

### 6.4 Suites that must stay green unchanged

- `python -m unittest discover -s tests` — all of it.
- `node tests/page.test.mjs` — including the adapter equivalence block with §5's additions.
- `python -m unittest discover -s local/tests` — **not edited by this PBI** (outside its areas).
  `local/tests/test_conformance.py` drives the real exporters against `local/records.py`'s shapes; it
  must pass with the new `end` field and the new `at` list, which §3.5 argues it will. The worker runs
  it as a check; **if it fails, that is a stop, not a licence to edit `local/**`** — it would mean the
  premise of §3.5 is wrong and the owner must be asked (Q-2).

---

## 7. Acceptance criteria

Inherited from the PRD:

- **AC-83** Two runs that ran 10:00–10:20 and 10:05–10:30 draw bars overlapping between 10:05 and
  10:20. *(FR-122; `tests/page.test.mjs`, the AC-83 overlap case in §6.3.)*

This spec's own, all pinned by a named test in §6:

- **AC-T1** *(FR-101)* A subagent run document whose launch and finish times are both known carries
  `start` **and** `end`; the same run's document carries neither when its launch time is unknown, and a
  `runs.manual` row carries neither in any case. *(§6.1, §6.2.)*
- **AC-T2** *(FR-122)* For a run with `start` and `end`, the drawn bar's left and right edges map back
  to those two times on the axis within one pixel — the bar is not the token-width bar of the swimlane.
  *(§6.3 overlap and single-run cases.)*
- **AC-T3** Where runs in scope have no readable `start`, the panel names the count
  ("N of M runs have no recorded start time") and lists each such run with its label and outcome; no
  such run is placed on the axis, and no start time is synthesized for it. A fixture of three runs of
  which two are unplaced is the minimum that can satisfy this. *(§6.3 unplaced case.)*
- **AC-T4** A run whose `kind` is `running` is drawn from its `start` to its recorded last activity with
  an open right edge, and its right edge does not move when the test's clock is advanced. *(§6.3
  in-flight case.)*
- **AC-T5** *(FR-124)* Given two runs separated by 90 minutes with `windowMinutes` 10, exactly one idle
  gap is shaded, over the true 80-minute interval between them; given two runs separated by exactly 10
  minutes, none is. **The shading is labelled for what it actually means**: the gap's visible label and
  its `<title>` both qualify idle as "no run **on this axis**", the chart's `aria-label` says the same,
  and where the view holds at least one unplaced run the footnote states in real text that those runs
  are off the axis and their time is not represented. *(§4.7, §6.3 idle cases and the idle-wording
  case.)*
- **AC-T6** An interval containing a run that was counted but not drawn is not shaded as idle. *(§6.3
  idle-respects-undrawn case.)*
- **AC-T7** *(FR-123)* Each published refusal time in the domain is drawn as its own mark, so a limit
  window whose `at` list holds three times inside the domain produces three marks, not one. *(§6.3
  limit-marks case.)*
- **AC-T8** *(FR-123, data)* A limit entry published by the exporter carries one `at` entry per refusal
  that had a readable time, so `len(at) <= refused` always. Where `firstAt` is truthy and `at` is
  non-empty, **`at[0] >= firstAt`**, and the two are equal whenever the window's first refusal had a
  readable time. Where the window's first refusal had **no** readable time, `firstAt` stays `null` while
  `at` still lists the later timed refusals — asserted on a fixture built that way, and `firstAt` is not
  rewritten. Merging two sessions' copies of one account-wide refusal yields one time, not two. *(§3.3,
  §6.1, including `test_usage_doc_lists_a_refusal_window_whose_first_refusal_has_no_time`.)*
- **AC-T9** With 1200 runs in scope, the markup holds at most 600 bars and at most 10 sub-rows per lane,
  and the footnote states counts which, added to the drawn bars, account for every run in scope.
  *(§6.3 volume case.)*
- **AC-T10** With runs spanning 9 days the default window is *Last 7 days* and the window select offers
  all four options; with runs spanning 3 hours the default is *Last 6 hours*. The default is computed
  from the data's own span, so it is identical in both adapters. *(§6.3 scale case.)*
- **AC-T11** A run label containing `<img src=x onerror=alert(1)>` and a verdict containing backticks
  and `**bold**` render as literal text: no raw tag in the panel, and no `<code>` or `<b>` produced from
  the verdict. *(§6.3 escaping case.)*
- **AC-T12** The only animated element the timeline emits is the `runglow` on a running run; with no
  running run in scope the timeline's markup contains no animated class at all. *(§6.3 reduced-motion
  case.)*
- **AC-T13** *(FR-97, PBI-006)* The adapter equivalence check compares a board on which the timeline
  draws at least one bar and at least one usage-limit mark on both sides, asserted by name, and the two
  sides remain deep-equal. *(§5; `tests/page.test.mjs:1461–1473`.)*
- **AC-T14** Worker close-out: both suites green on the head commit
  (`python -m unittest discover -s tests`, `node tests/page.test.mjs`), `local/tests` green unedited,
  and the code-review gate passed (`review-agents:code-reviewer` GO).
- **AC-T15** *(new in revision 2, F-3)* A run that began before the drawn domain and ended inside it is
  drawn clipped to the domain: its left edge is the domain's left edge, the emitted markup contains no
  negative coordinate and none outside the `viewBox`, the clipped edge is marked (square cap plus tick)
  and its `<title>` says the run started before this window. Such a run is drawn, so it is not also
  counted among "N runs before this window". *(§4.5; §6.3 straddling case.)*
- **AC-T16** *(new in revision 2, F-4)* The window `<select>` works and keeps working across re-renders:
  firing a `change` event to *Last 6 hours* redraws the timeline to a 6-hour domain anchored at
  `spanEnd`, with the bar count and the "before this window" count together accounting for every run in
  scope; after a subsequent store change re-runs `renderDispatch()`, the control still shows *Last 6
  hours* and the domain is still 6 hours; and a second `change` event redraws exactly once. *(§4.12;
  §6.3 window-select cases; harness `tests/page.test.mjs:83`.)*
- **AC-T17** *(new in revision 2, F-5 — the criterion with a human actor)* **NFR-22, verified by a named
  actor at close-out, not by the build.** The parent spec makes the design rules mandatory for every
  page PBI (`docs/backlog/specs/dispatch-board.md:216`), and no regex can judge "professional
  dashboard", legibility at 1050 px, or dark and light. Before the PR is marked ready, the worker must
  record **one** of these two, naming the actor in the PBI's Evidence section:
  - **the owner** looked at the rendered timeline and confirmed it against `CLAUDE.md:131–139`; or
  - the worker produced a **rendered-screenshot evidence artefact** under
    `docs/backlog/evidence/<date>-pbi-020-timeline/` — the precedent is
    `docs/backlog/evidence/2026-09-11-page-checks/` — showing the panel at 1050 px in **both** dark and
    light, with a written check against each of the five design rules of `CLAUDE.md:131–139`
    (professional dashboard, status-tile language, no wide monospace, tokens only, motion only when
    true), and the owner's confirmation is then outstanding rather than assumed.

  A close-out with neither is an incomplete close-out. This criterion is deliberately **not** phrased as
  build output: nothing in `tests/page.test.mjs` can assert it, and a test that pretended to would be
  the vacuous kind this spec refuses.

  *One note on the second option, recorded rather than glossed:* `docs/backlog/evidence/**` is not in
  PBI-020's `allowed_areas` either (`docs/backlog/pbi/PBI-020-timeline.md:7`). Writing the artefact is treated as
  **close-out bookkeeping on the delivery rails** — the same class as the PBI file's own Evidence
  section and its gate-tracking table, which every PBI writes at close-out and no PBI lists as an area —
  and not as a product edit. If the owner reads it more strictly, the first option (the owner's own
  look) closes AC-T17 with no file written at all, so the criterion is satisfiable under either reading.

None of AC-T1 to AC-T13, AC-T15 or AC-T16 can be met by a panel that renders nothing: each names a
fixture with the awkward case in it and an output that only a working renderer produces. AC-T17 is the
one criterion a machine cannot close, which is why it names its actor.

---

## 8. Assumptions and open questions

| # | Question | Chosen default (what the build does absent an answer) | Needs the OWNER? | Impact if wrong |
|---|---|---|---|---|
| **Q-1** | Once `end` is published, `CLAUDE.md:38`'s store-path row is wrong ("`runs.manual` rows carry neither" becomes "none of the three"), and **the build has no permission to fix it**. This is *not* the PBI-005 defect of metadata that both grants and forbids a path: PBI-020's `blocked_areas` is empty (`docs/backlog/pbi/PBI-020-timeline.md:7–8`); the file is simply not granted. The parent spec's permission to update `CLAUDE.md` is conditioned on **"a declared `docs` touch"** (`docs/backlog/specs/dispatch-board.md:216–217`), and where the planner meant it, the per-PBI row lists `CLAUDE.md` explicitly (PBI-017 `:219`, PBI-018 `:220`); PBI-020's row does not (`:256`). So the grant does not self-execute, and the spec's default is correct — but it knowingly ships a documented contract that is wrong. **The owner's choice:** (a) add `CLAUDE.md` to PBI-020's `allowed_areas` before the build starts, so the one-row correction lands with the change that causes it; or (b) pre-register a `chore-work` sweep to correct the row straight after the merge. | **Ask before editing.** The build leaves `CLAUDE.md` alone, publishes `end`, and reports the stale sentence at close-out. | **YES** — the one row that needs the owner. Either grant the path or pre-register the sweep; the build will not decide it. | Low either way, but not nil: option (a) or (b) costs one line, and doing neither leaves `CLAUDE.md:38` wrong for however long it takes someone to notice. Editing it unasked would be a scope breach. |
| **Q-2** | Does adding `end` and `usage.limits[].at` really pass `local/tests/test_conformance.py` untouched? §3.5 argues yes from `local/records.py:21` and `:40–43`. | Run the suite; treat a failure as a stop and report, never edit `local/**`. | **No — contingent, and expected not to fire.** The round-1 reviewer independently re-verified §3.5 against the live shapes (`local/records.py:41–42` already list `start` and `end`; unlisted fields are allowed at every level; `to_row`/`from_row` round-trip the whole document) and concluded it will not fire. It stays on this list only as a **stop, not a licence**: if the suite does fail, the premise of §3.5 is wrong, the worker stops and asks the owner, and no `local/**` file is edited to make it pass. | Low if it passes as argued; a hard stop, escalated to the owner, if not. |
| **Q-3** | Is a panel on Dispatch the right home, rather than an eleventh tab? §4.1 argues for the panel (FR-125–128, AC-84, the equivalence fixture). | Panel on Dispatch, above the swimlane. | No — a design judgement inside this PBI's areas, reversible in one change if the owner prefers a tab. | Low. |
| **Q-4** | Should the exporter publish per-refusal times at all, or should FR-123 mark only `firstAt`? | Publish them (§3.3); marking one time per group would meet FR-123 only vacuously. | No — the PRD's own wording ("each recorded usage-limit refusal") settles it, and parent-spec row 11 says the PRD defaults stand (`docs/backlog/specs/dispatch-board.md:295`). | Low; a rejected alternative is recorded rather than lost. |
| **Q-5** | The 600-bar and 10-sub-row bounds, and the four window options, are this spec's numbers — the PRD sets none. | Use them, and state every count the bound hides on the page. | No — tunable in one line; the criterion (AC-T9) is that nothing is hidden silently, not that the number is 600. | Low. |
| **Q-6** | Bar minimum width of 3 px means a very short run reads slightly wider than it was. | Draw it, always extending right from the true start, and say so in the footnote. | No. | Low; the alternative is an invisible run, which is worse. |
| **Q-7** | Should the timeline offer click-through to a run's detail (PBI-014, FR-121)? | No. Bars carry `data-run` so PBI-014 can attach later; this PBI wires no click handler. | No — PBI-014 owns FR-121. | Low. |

**After round 1, exactly one row needs the owner: Q-1.** Q-2 is contingent on a failure the reviewer
independently expects not to happen, and is carried as a stop rather than as a question; Q-3 to Q-7 are
settled inside this PBI's areas by the PRD, the parent spec or the existing code, and the round-1 review
agreed. Note that **NFR-22 is no longer an open question but a criterion with a named actor** (AC-T17):
the owner is one of the two ways to close it, but the worker can close it with a screenshot evidence
artefact instead, so it does not block the build.

---

## 9. Out of scope

- **`local/**`** — nothing is edited there. The record shapes already carry `start` and `end`
  (`local/records.py:40–43`); §3.5 explains why no change is needed and Q-2 covers the case where that
  turns out to be wrong.
- **A new tab, and the tab-bar requirements** FR-125–FR-128 / AC-84.
- **Run detail on click** (FR-121, PBI-014) — a `data-run` hook only.
- **The usage-limit forecast** (FR-117, FR-118, PBI-013). The timeline marks refusals that happened; it
  makes no estimate and shows no "no forecast" text.
- **Switching Dispatch's token figure** to transcript-derived usage (`CLAUDE.md:142`) — an open item,
  not this PBI's.
- **`projectTabs`, `records.TAB_NAMES`, `refresh.py`'s `MANAGED`** — untouched, as §3.4 states.
- **Changing `place_manual()`** or any other derivation's behaviour. The only behavioural change in
  `exporters/` is the two added publications of §3.1 and §3.3.

---

## 10. Spec-gate record

| Round | Revision reviewed | Verdict | Review note |
|---|---|---|---|
| 1 | 1 | APPROVE-WITH-NOTES | `docs/backlog/reviews/PBI-020/spec-review-r1.md` |

Round 1 (2026-09-12): APPROVE-WITH-NOTES, 0 High, 5 Medium, 3 Low; **all eight applied in revision 2,
none deferred.** The reviewer found no citation drift beyond F-6, re-verified both of the spec's
load-bearing claims independently and upheld them, and those claims are unchanged here:

- **FR-123 is unmeetable on today's document.** `usage_doc()` groups refusals by `resetsAt` and
  publishes only `{firstAt, refused, type, resetsAt}`, so each refusal's own time is discarded
  (`exporters/derive.py:287–291`, `:377–381`). The reviewer also confirmed the shared-module claim is
  genuine rather than asserted, by tracing `local/collector.py:436` → `derive.run_doc` and
  `derive.session_result` / `derive.project_doc` → `usage_doc` / `aggregate_usage`, so both adapters
  gain the field together.
- **§3.5 is right: no `local/**` edit and no follow-up PBI.** `local/records.py:41–42` already list
  `start` and `end` as run optionals, and unlisted fields are allowed at every level (`:21`).

Nothing in this revision weakens either. Every change below adds a constraint, a label, a fixture or a
correction; none removes a refusal the spec had made.

| Finding | Sev | Disposition in revision 2 |
|---|---|---|
| F-1 | Med | **Applied.** The false invariant is gone. §3.3 now states it as `len(at) <= refused` always; `at[0] >= firstAt` where `firstAt` is truthy and `at` non-empty, equal in the ordinary case; and `firstAt` null with `at` non-empty where the window's *first* refusal had no readable time — with the mechanism cited (`exporters/derive.py:372` sorts on `x['at'] or ''`, `:377` seeds `firstAt` from that first refusal, `reject()` writes `'at': None` at `:287–291`). `firstAt` is **not** rewritten to `at[0]`, with the reason stated: this PBI carries the times and does not redefine a field PBI-013 and the usage tab already read. AC-T8 is reworded to the true invariant; §6.1 gains `test_usage_doc_lists_a_refusal_window_whose_first_refusal_has_no_time`, the untimed-first fixture that revision 1's claim would have failed; and §4.8 gains the page's handling of a null `firstAt` (no mark at epoch, no mark at the domain edge, counted in the footnote) with a §6.3 case behind it |
| F-2 | Med | **Applied as a labelling requirement, with the geometry left alone.** §4.7 now says plainly that unplaced work — undated subagents and every `runs.manual` row (`exporters/derive.py:720`; `tests/test_export_sessions.py:782–789`) — falls outside the active set, so an interval of in-line orchestrator work will be shaded. FR-124 permits it; the page no longer implies otherwise. The word "idle" never stands alone: the visible label reads "idle 3 h 12 m — no run on this axis", the gap's `<title>` and the chart's `aria-label` say the same, and where the view holds any unplaced run the footnote states in real text that those runs are off the axis and their time is not represented. AC-T5 carries the wording assertion and §6.3 gains an idle-wording case with a manual row in the fixture |
| F-3 | Med | **Applied.** §4.5 states the clip rule: every bar is clipped to the domain (`x = max(x(barStart), x(domainStart))`, `right = min(x(barEnd), x(domainEnd))`), so no coordinate is ever negative or outside the `viewBox`. A left-clipped bar is marked as clipped — square cap, a `var(--ink-3)` tick, and a `<title>` opening "started before this window" — and is **not** also counted in "N runs before this window", which would double-report a run that is drawn. §4.6's "the bar's x is always the true start" is narrowed to its real meaning (minimum-width widening may only extend right) with clipping named as the stated exception. New AC-T15 and a §6.3 straddling case |
| F-4 | Med | **Applied, mechanism named.** New §4.12 spells out how the only interactive control survives `p.innerHTML = …` on every store change (`site/index.html:604`): the choice lives in module state beside `view`/`sel`, the emitted `<option>` carries `selected` **and** the element's `value` is set after the write (because the harness's stub element is memoised by id and keeps its `value` property, `tests/page.test.mjs:47–52`), and the `change` listener is attached once per element under a `dataset` flag — unguarded re-attachment would stack handlers on the stub, whose `addEventListener` appends without de-duplicating (`:50`), and re-enter `renderDispatch()`. The control takes a stable `id` rather than a delegated listener, because the harness's `change()` helper invokes the listeners on that id's element and does not bubble (`tests/page.test.mjs:83`). Revision 1's "re-applied on re-render like the session filter" is corrected in §4.5: the session and project selects are in the header and bound once at load (`site/index.html:1177`, `:1185`), which is exactly why they are not a precedent. New AC-T16 and two §6.3 cases (redraw; choice survives a re-render, and a second `change` redraws once) |
| F-5 | Med | **Applied — the one item with a human actor.** New **AC-T17** makes NFR-22 a close-out step with a named verifier: either **the owner** confirms the rendered view against `CLAUDE.md:131–139`, or the worker produces a rendered-screenshot evidence artefact under `docs/backlog/evidence/<date>-pbi-020-timeline/` (precedent: `docs/backlog/evidence/2026-09-11-page-checks/`) at 1050 px in both dark and light, with a written check against each of the five design rules. It is phrased as a worker close-out step, explicitly **not** as build output, because no regex can judge it and a test pretending to would be the vacuous kind this spec refuses. §8 records that NFR-22 is now a criterion with an actor rather than an open question, so it does not block the build. One honesty note is recorded in AC-T17: `docs/backlog/evidence/**` is not in `allowed_areas` either, so writing the artefact is treated as close-out bookkeeping of the same class as the PBI's own Evidence section; under a stricter reading the owner-look option closes the criterion with no file written |
| F-6 | Low | **Applied.** §3.3's citation is corrected: session `usage` is `'object'` at `local/records.py:30`, project `usage` is **`'object\|null'` at `local/records.py:53`** (revision 1 said `:54` and `'object'` for both). Verified by reading the file and counting lines. The conclusion is unchanged — neither type inspects the object's contents, so the added `at` list needs no shape change |
| F-7 | Low | **Applied, and the fixture rebuilt on the real path.** §3.1's rationale no longer claims `sub['last']` can produce an `end` without a `start`: `add_agent` sets `first` and `last` together under one `if stamp(o):` (`exporters/derive.py:304–308`), so a transcript with a last timestamp always has a first. The real path is now stated — no Agent tool-use launch record **and** an undated agent transcript (`begin = sub['first'] = None`) **plus** a finish notification carrying an `at`, so `end = (fin or {}).get('at')` is real while `start` is `None` (`:483–485`). §6.2's case is renamed `test_end_without_start_when_only_the_finish_notification_has_a_time` and built from a finish notification plus an undated transcript, not from the impossible "last without first". The conclusion — such a run is unplaced (§4.4) — stands |
| F-8 | Low | **Applied.** §4.8 now requires the `firstAt` fallback to be named in the **footnote** as real text, not only inside an SVG `<title>`: "N limit windows show only their first refusal (M refusals in total); this store has not been re-exported since the timeline landed", present only while some mark actually falls back. §6.3's limit-fallback case asserts the footnote text outside any `<title>`, which is what §4.10's rule about counts being real text demands |

**Owner rows after revision 2: Q-1 alone.** It is restated accurately — not the PBI-005
both-grants-and-forbids defect (PBI-020's `blocked_areas` is empty), but a grant conditioned on a
declared `docs` touch that PBI-020's row does not declare — and put to the owner as a choice between
adding `CLAUDE.md` to `allowed_areas` before the build and pre-registering a `chore-work` sweep after
the merge. Q-2 is recorded as contingent and expected not to fire, kept as a stop rather than a licence.
Q-3 to Q-7 stay settled.

**Operational note carried from the review** (not a finding, recorded in §3.4): the first refresh after
this merges rewrites every run document, so the owner should expect one unusually large push, once.
