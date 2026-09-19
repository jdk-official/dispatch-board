---
id: SPEC-PBI-025
title: "Local tab and status records: the collector writes each project's five tabs and its status document into the local database"
pbi: PBI-025
parent: docs/backlog/specs/dispatch-board.md (revision 5, approved)
revision: 4
status: approved at spec-gate round 2 (APPROVE-WITH-NOTES; N-1 through N-4 applied in revision 3 as a text pass needing no re-review; N-5 not this spec's to fix). Revision 4 is a post-approval correction from the code review — §4.4 row 4's "Store nothing" was wrong and would have deleted a carried record on the third pass; the build had correctly deviated, and the spec is amended to match. No acceptance criterion changed.
date: 2026-09-12
reviews: docs/backlog/reviews/PBI-025/spec-review-r1.md (round 1, revision 1, CHANGES-REQUIRED); docs/backlog/reviews/PBI-025/spec-review-r2.md (round 2, revision 2, APPROVE-WITH-NOTES)
---

# PBI-025: Local tab and status records (per-PBI spec)

## 1. Intent

PBI-019 built the collector, the local-first app's only writer, and gave it `session`, `run`,
`project`, `catalogue` and `lastRefresh` records. It deliberately wrote no `tab` and no `status`
record (PBI-019 spec §2, row Q-2). PBI-005 built the local server, which already serves every kind in
`records.TABLES` and states that "`tab` and `status` arrive when PBI-025 lands, and the server needs no
change for that" (`docs/backlog/specs/pbi-005-local-server.md:77-80`).

This PBI closes that gap. After it, a collector pass writes, for every project in `board.config.json`:

- the five tab records `spec`, `assumptions`, `decisions`, `backlog` and `git` (store paths
  `projectTabs/<projectId>.<tab>`), equal to `export_board.py`'s documents for the same repository,
  config and data file, apart from `generatedAt` and `pulls` (§4.4, §6);
- the project's `status` record at its `statusDoc` path (`meta/status` or `status/<projectId>`),
  carrying `live` and `updatedAt` by `refresh.py`'s rule (§5).

**Sources**

- **PRD revision 3:** FR-100 (the `tab` and `status` records), FR-153 and FR-190 (keep-last and
  `carriedSince`), FR-184 and FR-185 (the mass-delete guard and age pruning), FR-96 / NFR-17
  ("never contacts a network host"), C-16 (no answers).
- **Parent spec** (revision 5, approved): the Key decision "All derivations live in one shared module
  under `exporters/`; the collector imports it, never re-implements it"
  (`docs/backlog/specs/dispatch-board.md:87`) and the derivation rule at line 270.
- **PBI-019 spec** (revision 3, approved), whose pass structure, guard, transaction and error handling
  this PBI extends rather than replaces.
- **PBI-005 spec** (revision 2, approved), §§3, 5.4 and 6.2: the snapshot enumerates kinds from
  `records.TABLES`, so no server change is needed.
- **The live code:** `exporters/export_board.py`, `exporters/derive.py`, `exporters/refresh.py`,
  `local/collector.py`, `local/db.py`, `local/records.py`.

**Three rules govern the design**, inherited from PBI-019 and kept word for word:

1. **Equivalence.** For the same repositories, config, data files and `now`, the database holds the
   documents `export_board.py` writes, and the status documents `refresh.py` plans. Where a cleaner
   design and matching the exporter disagree, this spec matches the exporter.
2. **Reuse, never re-implement.** Every derivation is imported. Where a derivation is not yet shared,
   this PBI moves its *pure* half into `exporters/derive.py` (§3).
3. **Never contact a network host.** `gh` is a network client, so `pulls` is not collected locally
   (§4.5). Local `git` subprocesses are not network contacts and are kept.
4. **Touch only the tab suffixes this pass owns.** `projectTabs` is a two-writer collection. This pass owns
   the five `export_board` suffixes and nothing else; a tab record with any other suffix is neither written,
   nor deleted, nor counted by the guard (§2, §6.2, §6.3). This rule was added in revision 2 and is the
   subject of finding F-2.

---

## 2. The blocked-areas question, settled

PBI-025 blocks `local/records*`, `local/schema*` and `local/records.shapes.json`. It is therefore only
buildable if the `tab` and `status` record shapes, ids, collections and tables already exist. **They
do.** Evidence, all from the live tree:

| Fact | Evidence |
|---|---|
| `tab` shape exists: required `generatedAt` (`str`), optional `source`; fields SHAPES does not list are allowed and kept at every level (`local/records.py:20-21`) | `local/records.py:57-60` |
| `status` shape exists: every field optional — `title`, `message`, `live`, `updatedAt`, `metrics` | `local/records.py:61-64` |
| Store collections: `tab` → `projectTabs`; `status` → `None`, because a status id already names its own collection | `local/records.py:88-89` |
| Tab names: `records.TAB_NAMES` is now the **six** `('spec', 'assumptions', 'decisions', 'backlog', 'git', 'findings')` since PBI-026 merged (`5baa922`); `export_board.TABS` is still exactly the five (`exporters/export_board.py:39`) | `local/records.py:91` |
| Id forms: `tab` is `<projectId>.<tabname>`; `status` is `(?:meta\|status)/[A-Za-z0-9_-]{1,100}`, with `meta/lastRefresh` refused | `local/records.py:103-104`, `local/records.py:206-208` |
| SQLite tables: `tab` → `project_tabs (id, project, tab, doc)`; `status` → `statuses (id, doc)`. `to_row` splits a tab id on the first `.` to fill `project` and `tab`, "because a tab document does not name itself" | `local/records.py:112-119`, `local/records.py:238` |
| The conformance suite already validates every `tab` and `status` document the v1 exporters write, including carried tabs | `local/tests/test_conformance.py:82`, `:269-270`, `:353`, `:415` |
| `db.upsert`, `db.delete` and `db.stored` are generic over `records.TABLES`, so they need no change | `local/db.py:157-172` |
| The server enumerates kinds from `records.TABLES` and never from `sqlite_master` | `docs/backlog/specs/pbi-005-local-server.md:77-80`, `:344-346`, `:384-385` |

**Verdict: PBI-025 is coherent as written.** No edit to `local/records*`, `local/schema*` or
`local/records.shapes.json` is required by anything this spec specifies, and none is specified. The
schema version stays at 1 and `local/schema.py` is untouched.

**One collision to record, which does not change that verdict — but which does change §6.2.**
`TAB_NAMES` **now includes** `findings`: PBI-026 merged (`5baa922`) and widened it to six names
(`local/records.py:91`). PBI-011 added a sixth project tab,
`projectTabs/<projectId>.findings`, and it is written by `exporters/export_sessions.py:290-308`, **not** by
`export_board.py` — `export_board.TABS` is still the five (`exporters/export_board.py:39`, and its module
docstring at lines 7-10 says a document outside `TABS` "is never touched here"). Consequences:

- **PBI-025 does not write a `findings` record.** `exporters/export_sessions.py` is outside its allowed
  areas, so it cannot. That is stated as out of scope (§10) and as open question Q-3.
- **There is therefore no hard dependency on PBI-026.** PBI-026 has landed and widened `TAB_NAMES` to
  accept `findings`; nothing in this spec needed that widening, and nothing here broke when it landed.
- **The two are parallel-safe despite sharing `conflict_group: local-app`.** PBI-026's allowed areas are
  `local/records*`, `local/records.shapes.json`, `local/tests/**`; PBI-025 blocks the first two and
  PBI-026 blocks `local/collector*` and `local/db*`. The only overlap is `local/tests/**`, and this
  spec puts its tests in new files (§7), so no file is edited by both.
- **Handoff.** Once PBI-026 has landed, a follow-up PBI holding `exporters/export_sessions.py` and
  `local/tabs*` can add the findings tab locally. Until then the local Findings view shows its
  "not exported yet" state, exactly as the Spec tab does today (Q-3).

### 2.1 `projectTabs` is a two-writer collection (revision 2, finding F-2)

This is the one place where PBI-026's landing genuinely reaches this PBI, and revision 1 got it wrong.
`projectTabs` has **two writers, each of which owns a disjoint set of tab suffixes and is forbidden to
touch the other's**:

| Writer | Owns | Stated where |
|---|---|---|
| `export_board.py` | `spec`, `assumptions`, `decisions`, `backlog`, `git` (`TABS`, `exporters/export_board.py:39`) | Module docstring, `exporters/export_board.py:7-10`: a document outside `TABS`, "such as export_sessions.py's `<projectId>.findings`, is outside TABS and is never touched here; that exporter owns its own document's whole lifecycle" |
| `export_sessions.py` | `findings` | `exporters/export_sessions.py:290-308`: "This exporter owns that document's whole lifecycle -- write and delete -- rather than relying on export_board.py's folder wipe" |

`export_board.main` enforces its half in code: its deletion sweep filters on the suffix before removing
anything — `name[:-len('.json')].rsplit('.', 1)[-1] in TABS`
(`exporters/export_board.py:277-285`, whose comment reads "the folder is shared, but each exporter manages
only its own tab suffix's lifecycle").

`refresh.py` records the same ownership split at the push layer: its `TABS` is the **six**
(`exporters/refresh.py:47`, including `findings`), and the two lines above it
(`exporters/refresh.py:45-46`) are a comment about the two writers sharing the collection. So the board
already treats `projectTabs` as jointly owned; only the local side, in revision 1, did not.

**Why this bites the local side once PBI-026 lands.** `_ID_FORMS['tab']` is built *from* `TAB_NAMES`
(`local/records.py:103`: `r'%s\.(?:%s)' % (_PROJECT_ID, '|'.join(TAB_NAMES))`). So the moment PBI-026
widens `TAB_NAMES`, `<pid>.findings` becomes a **valid local tab id** — storable, and therefore stored by
whichever later PBI adds the findings tab locally. A local tab pass that computed its intended set from
`records.TAB_NAMES` would then find a stored `findings` record that it did not build, conclude the record
is no longer intended, and **delete it on every pass — every 60 seconds — destroying exactly what PBI-011
publishes**. A project whose only stored tab was `findings` would additionally trip the guard's
emptied-tabs clause (§6.3) and stall the whole pass.

**The rule this spec therefore adopts.** `local/tabs.py` defines its own constant:

```
tabs.OWNED = ('spec', 'assumptions', 'decisions', 'backlog', 'git')
```

and **every intended set, carry set, deletion set and guard grouping in this spec is scoped to `OWNED`,
never to `records.TAB_NAMES`** (§4.4, §6.1, §6.2, §6.3). A stored tab record whose suffix is not in
`OWNED` is invisible to this pass: not built, not carried, not deleted, not grouped. `OWNED` is a local
constant rather than an import of `export_board.TABS` only so that the blocked-area question stays
closed; asserting `tabs.OWNED == export_board.TABS` is AC-TB13, so the two cannot drift.

This makes PBI-026 safe to land before, after or during this PBI: widening `TAB_NAMES` changes nothing
this pass reads.

---

## 3. Where the derivation lives (the parent spec's rule)

The parent's Key decision is that all derivations live in one shared module under `exporters/`, so the
board and the local app produce identical documents from one implementation
(`docs/backlog/specs/dispatch-board.md:87`, `:270`). Applying that here needs one distinction, because
`derive.py`'s own contract is stricter than "shared":

> "Nothing here reads a file, the config, git or the network, prints, or exits: callers pass parsed data
> … and get records back." — `exporters/derive.py:5-7`

So *derivation* moves into `derive`; *I/O* does not. Applied tab by tab:

### 3.1 The four spec-derived tabs — already shared, nothing moves

`derive.spec_docs(pid, paths, spec, prd, brief, design, adrs, rounds, data, now)`
(`exporters/derive.py:866-938`) already produces the whole `spec`, `assumptions`, `decisions` and
`backlog` documents from text. `export_board.spec_tabs` (`exporters/export_board.py:92-115`) is the
~20 lines of I/O around it: read the four documents named in `docs`, list and read the ADR folder, and
read the review-round notes. **Nothing moves.** `local/tabs.py` imports `export_board` and calls
`export_board.spec_tabs(p, export_board.load_data(DATA_DIR, p['id']), stamp)`.

Importing `export_board` from `local/` is new — PBI-019 §2 recorded that the collector does *not*
import it, so that "the `carried` name clash in the PBI-004 follow-up does not arise". That clash is
between `export_board.carried` (bytes of a kept tab file) and `derive.carried` (a kept agent row); it
arises only from a star-import. `local/tabs.py` imports the **module**, never its names, so both stay
reachable as `export_board.carried` and `derive.carried`. `export_board` does no I/O at import time
(its `CONFIG` read is inside `main`, `exporters/export_board.py:239-241`), and it is under
`exporters/`, which the collector already puts on `sys.path` (PBI-019 §2).

### 3.2 The git tab — its pure half moves into `derive`

`export_board.git_tab` (`exporters/export_board.py:127-146`) mixes ten `subprocess` calls with the
arithmetic that turns their output into the document (`byDir` counting, the commit split on `|`,
`public_remote` redaction, `tracked` length). Only the second half is a derivation.

**What moves.** Two new pure functions in `exporters/derive.py` (revision 2 adds the first of them, and
widens the second's remit, per finding F-5):

```
derive.git_default(master_out, main_out) -> 'master' | 'main' | ''
derive.git_doc(root, branch, default, log, files, status, remotes_raw, head, ahead_out, shortstat_out, now)
```

`git_default` is the `master`/`main`/`''` selection that today sits inline in `git_tab`
(`exporters/export_board.py:129`): given the stdout of `git rev-parse --verify --quiet master` and of the
same command for `main`, it returns `'master'` if the first is non-empty, else `'main'` if the second is,
else `''`.

`git_doc` takes the *already-captured* stdout of the git commands as strings and returns exactly the dict
`git_tab` returns today, including `'source': 'git, local repository'`, `repoPath` with backslashes
replaced, and the key order. **It also applies the emptiness rule itself**: `ahead` is `ahead_out` when
both `default` and `branch` are non-empty and `''` otherwise, and likewise `shortstat` from
`shortstat_out` (`exporters/export_board.py:141-142`). A caller may still skip the two subprocesses when
`default` or `branch` is empty — both `export_board.git_tab` and `local/tabs.py` do — but that is now a
pure optimisation: the skipped call would have been passed `''`, and `git_doc` returns `''` either way,
so the caller cannot diverge from the rule by getting the condition wrong.

**Why revision 1 was wrong here.** Its signature left both the default-branch selection and the emptiness
rule in the caller, so `local/tabs.py` would have had to re-implement two derivations — breaking rule 2 —
and §7.1 asked `git_doc` to be tested for an emptiness rule its own signature could not exercise. With
`git_default` added and the rule moved inside `git_doc`, the only thing `local/tabs.py` re-implements is
the *sequence of subprocess calls* (§3.3), which is I/O, not derivation.

`public_remote` and its `USERINFO` pattern move with them (`exporters/export_board.py:119-124`; they are
pure `re` work and belong beside the redaction `derive` already owns). `export_board.public_remote` stays
as a re-export, in the style of the existing `from derive import (...)` line at
`exporters/export_board.py:33-34`, so no caller or test breaks.

**What stays in `export_board`.** `git_tab` keeps the `subprocess` calls and becomes a thin caller of
`derive.git_default` and `derive.git_doc`. `git`, `is_repo`, `pulls`, `github_origin`, `github_repo`,
`PR_LIST`, `PR_TIMEOUT`, `tab_bytes`, `carried`, `load_data`, `spec_tabs`, `verdict`, `read` and the whole
of `main` — the `out/` writing, the `TABS`-only file deletion, the gh call, and the printed summary — all
stay exactly where they are.

**Behaviour is unchanged.** `git_tab`'s output is identical before and after for identical captured
command output, which is criterion T-6 and AC-TB11 (§7.2 states how that is demonstrated without an
unreproducible fixture).

### 3.3 What the local side re-implements, and why that is the minimum

`local/tabs.py` runs the same git commands as `export_board.git_tab` — about ten lines of
`subprocess.run` — and calls `derive.git_default` and then `derive.git_doc` with the results. It does not
import `export_board.git_tab` itself, because that function's contract is "run git in this repo and return
the document", and the collector needs the *commands* to run under its own timeout and warning discipline
(§4.6). After the F-5 correction above, **no derivation at all is duplicated**: the two rules that
revision 1 would have left in the caller now live in `derive`.

This is the same trade PBI-019 recorded in its row Q-12 for the assembly glue: a short, tested,
equivalence-checked duplication of I/O sequencing, with the derivation itself shared. AC-TB1 and the
equivalence suite (§7) catch any drift.

---

## 4. The tab pass

### 4.1 Module layout

| File | Contents | Area |
|---|---|---|
| `local/tabs.py` | **New.** The `OWNED` constant (§2.1), building the five tab documents and the status documents for one pass (§4.2-§4.7, §5) | `local/tabs*` |
| `local/collector.py` | Hooking the tab pass into `run_pass`, extending the stored/deletion/guard sets and the report line (§4.8, §6) | `local/collector*` |
| `exporters/derive.py` | New `git_default` and `git_doc`, and the moved `public_remote` / `USERINFO` (§3.2) | allowed |
| `exporters/export_board.py` | `git_tab` becomes a caller of `derive.git_default` and `derive.git_doc`; `public_remote` re-exported (§3.2) | allowed |
| `tests/test_derive.py`, `tests/test_export_board.py` | New cases for `derive.git_doc` and the unchanged-output check (§7) | allowed |
| `local/tests/test_tabs.py`, `local/tests/test_tabs_equivalence.py` | **New.** Tests (§7) | allowed |

`board.config.json` and `exporters/board_config.py` are in the PBI's areas for a cadence or `gh` key.
**This spec adds neither** (§4.9, Q-5), so both files are left untouched. Keeping an area unused is
allowed; specifying an edit outside one is not.

### 4.2 Signature and placement in the pass

```
tabs.build(projects, data_dir, stamp, run=None) -> {pid: {tab: doc}}, [warning, ...]
```

- `projects` is `board_config.projects(config)`'s output, which the pass already has through
  `export_sessions.settings` and which carries `id`, `repoPath`, `docs` and `statusDoc`
  (`exporters/board_config.py:130-132`).
- `data_dir` is `<repo root>/projects`, resolved against the repository root as `databasePath` is
  (PBI-019 §3.1), never the working folder.
- `stamp` is `datetime.fromtimestamp(t0, timezone.utc).isoformat(timespec='seconds')`, the same
  expression the catalogue read already uses (`local/collector.py:441`), so one pass stamps everything
  from one clock.
- `run` stands in for `subprocess.run` so the tests can drive git without a repository.

**`tabs.build` is called before `BEGIN IMMEDIATE`**, alongside `settings` and the transcript glob
(`local/collector.py:556-566`), not inside the transaction. It needs nothing from the database: the
carry decision (§4.4) is taken later, inside the transaction, from `db.stored(conn, 'tab')`. Reading
the repositories and running git outside the write lock keeps PBI-019 §3.5's lock scope from growing by
ten subprocess calls per project per pass, which matters because the local server's writes-wait
behaviour and a second collector's 10 s busy wait both depend on that scope.

#### 4.2.1 What a failure inside `tabs.build` costs (revision 2, finding F-6)

Revision 1 said simply that "a raise inside `tabs.build` is not caught". That is the wrong default
locally, and the reviewer is right that it was a real operational choice presented as a footnote.

**Why the blast radius is larger locally than on the board.** `export_board.py` is one of three exporters
run by a refresher tick a human is watching; a failure there costs that tick and is seen. The collector's
`_one` catches every exception, prints one line — `pass failed (%s: %s); nothing written` — and returns 1
(`local/collector.py:643-648`), after which **the interval loop in `main` goes straight on to the next
pass** (`local/collector.py:696-708`). So a single project's
unreadable ADR folder (`PermissionError`) or non-UTF-8 spec file (`UnicodeDecodeError`) would, under
revision 1, destroy *every* record of *every* pass — sessions, runs, projects, catalogue and
`meta/lastRefresh` (`local/collector.py:582-583`) — once every 60 seconds, indefinitely and silently, for
a fault in a part of the data the failing project does not even own. The local board would freeze at its
last good state and the header's "data as of" would go stale with no indication why.

**The rule.** Failures are confined to the project that caused them:

| Failure inside `tabs.build`, for one project | Effect |
|---|---|
| Any `OSError` (including `PermissionError`, `FileNotFoundError`) reading that project's spec, PRD, brief, design, ADR folder or review notes | Warning `collector: project <id>: cannot read its documents (<type>: <message>); keeping the last export`. **That project** builds no spec-derived tabs this pass; §4.4 carries its stored ones. Every other project is built and the pass commits normally |
| `UnicodeDecodeError` on any of the same files | Same |
| `subprocess.TimeoutExpired` or `OSError` from any git call | The git tab alone is not built for that project, with the warning of §4.6; §4.4 carries it |
| `ValueError` from `export_board.load_data` — a malformed `projects/<pid>.json` | **Raised. The whole pass fails and writes nothing.** |

**Why this must be scoped per call, not one block around all of §4.3.** `UnicodeDecodeError` is a
subclass of `ValueError`. A single `except ValueError` wrapped around the whole of §4.3 step 2 would
therefore also catch the `ValueError` `load_data` raises for a malformed `projects/<pid>.json` —
silently downgrading row 4 into row 2's per-project confinement and erasing the distinction this table
draws. The handlers for rows 1-3 must instead be scoped to the specific calls that can raise them (the
document reads and the git subprocesses), with the `load_data` call kept **outside** that confined
block so its `ValueError` propagates unconfined to `run_pass`, exactly as row 4 requires.

**Why `load_data`'s `ValueError` is the one exception, and is genuinely different.** The other three are
faults in a *source* the tab is derived from, and the carry rule (FR-153, FR-190) is precisely the
designed response to a source going missing: keep the last export, mark it, warn. A malformed
`projects/<pid>.json` is not a missing source — it is the file that holds the **hand-kept build state**
(CLAUDE.md, Projects), and reading it as "no build state" would silently reset every PBI of that project
to "not started" in the Backlog tab. There is no carried document that protects against that, because the
tab *would* be rebuilt, just wrongly. `export_board.main` makes the same trade for the same reason, in
code and in its own words: it catches `ValueError` and returns 2 with "nothing exported"
(`exporters/export_board.py:273-275`), and its module docstring says "A malformed one stops the export and
leaves out/ as it was, so a typo cannot reset every PBI to 'not started'"
(`exporters/export_board.py:22-25`). The equivalence rule (§1, rule 1) therefore mandates matching it.
It is also the one case a human fixes in seconds, and it is loud: the pass exits non-zero every time.

A raise that does reach `run_pass` fails the pass before any transaction opens, so nothing is written —
the same outcome as a `Refusal`. `run_pass` already has that path: the inner handler rolls back if a
transaction is open (`local/collector.py:585-588`) and the outer one clears the in-memory cache and
re-raises (`local/collector.py:589-591`).

### 4.3 Which tabs are built

Exactly `export_board.main`'s rule (`exporters/export_board.py:250-261`), in the same order:

1. A project whose `repoPath` is empty or is not a folder produces **no** documents, with the warning
   `collector: project <id>: repository <path> does not exist`.
2. Otherwise `export_board.spec_tabs(p, export_board.load_data(data_dir, p['id']), stamp)` gives the
   four spec-derived tabs, or `{}` when the project has no readable spec.
3. If `export_board.is_repo(p['repoPath'])`, the `git` tab is added from §4.6.
4. `pulls` is **not** collected (§4.5).

Only the five `OWNED` names (§2.1) are ever produced; `tabs.build`'s result for a project is keyed by a
subset of `OWNED`, and the build asserts that, so a sixth suffix cannot enter the pass by accident.

Steps 1-3 for one project run inside the per-project failure boundary of §4.2.1: an `OSError` or
`UnicodeDecodeError` reading that project's documents, or a git failure, costs that project's tabs for
this pass and nothing else.

A `ValueError` from `load_data` — a project data file that is not valid JSON or not in shape — is the one
failure that is **raised, not confined**, so the pass writes nothing, exactly as `export_board.main`
returns 2 and exports nothing (`exporters/export_board.py:273-275`). §4.2.1 gives the reason in full: it
is the hand-kept build state, and treating it as absent would silently reset every PBI of that project to
"not started" — a fault no carried document protects against.

### 4.4 Keep-last and `carriedSince` (FR-153, FR-190) — yes, the local side carries too

The board's persistent copy is the file under `out/projectTabs/`; the local app's persistent copy is the
stored record. The behaviour is the same, expressed over documents instead of bytes. Inside the
transaction, for each configured project and **each of the five names in `tabs.OWNED`** — never
`records.TAB_NAMES`, per §2.1:

| Case | Action |
|---|---|
| The tab was built this pass | Store it (§6). Any `carriedSince` in the stored record is gone, because the built document has none. |
| The tab was not built, and **no** record is stored | Nothing. The page shows its "not exported yet" state. |
| The tab was not built, a record is stored, and it has **no** `carriedSince` | Store `dict(stored, carriedSince=since)` — the first carry. |
| The tab was not built, a record is stored, and it **already has** `carriedSince` | **Keep it in the intended set, returned unchanged.** Its first `carriedSince` survives, and `_Pass.store`'s unchanged-check means `db.upsert` is still not called. *(Amended at revision 4 — see below.)* |

> **Amendment, revision 4 (2026-09-12), from the PBI-025 code review, finding on the `tabs.carry` deviation.**
> Row 4 previously read "**Store nothing.** The stored record is left exactly as it is…". That wording is wrong, and the build correctly deviated from it. Returning nothing for an already-marked record drops it from the **intended** set, and §6.2 computes the deletion set as *stored minus intended* — so the record becomes a deletion candidate and is **deleted on the third pass**, losing the very carry this rule exists to preserve. The code-review reviewer reproduced that outcome from the literal wording.
> The implementation keeps the record in the intended set and returns it unchanged, which satisfies §4.4's "left exactly as it is" and §6.2's deletion rule at the same time, because `_Pass.store` compares against what is stored and issues no `db.upsert` when nothing changed. The spec is corrected to match the code; no acceptance criterion changes, and the observable behaviour the criteria assert (the carry survives, no write is issued) is unchanged.

`since = datetime.fromisoformat(stamp).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')` — the
same expression as `exporters/export_board.py:244`, so a local `carriedSince` is the same UTC-with-`Z`
form as the board's.

**Differences from the exporter, both deliberate and both harmless:**

- The exporter keeps the file's *bytes* and warns about a kept file that is not a readable JSON object
  (`exporters/export_board.py:214-233`). Locally there is no such case: `db.stored` returns documents
  already parsed and validated by `records.from_row`, and a row that cannot be read raises inside the
  pass rather than reaching the carry logic. `export_board.carried` is therefore **not** reused, and the
  `carried` name clash of §3.1 stays theoretical.
- The exporter's `since` is computed per run; so is the local one, from the same `stamp`.

**One warning per project per pass**, as the exporter does
(`exporters/export_board.py:270-271`): `collector: project <id>: cannot rebuild <tabs>; keeping the last
export`.

### 4.5 `pulls` is not collected locally (FR-96, NFR-17, AC-70)

`export_board` lists pull requests with `gh` (`exporters/export_board.py:179-205`), which contacts
github.com. PBI-019 §5 states that the collector never contacts a network host, and PBI-007's
end-to-end check inspects exactly that (NFR-17, AC-70). Three options were on the table (PBI-025
"Why a spec is required"); this spec chooses the first:

- **Chosen: leave `pulls` out locally.** The local `git` tab is `export_board`'s document minus the
  `pulls` key. The page already renders that state: "it says they are not available when `pulls` is
  absent" (CLAUDE.md, store-path table), which is the same thing a board refresh shows when `gh` is
  missing.
- Rejected: `gh` on a slower cycle. It would make the collector a network client and force PBI-007's
  AC-70 to carve out an exception, for a panel that is a convenience.
- Rejected: another source. There is none that is not also a network call.

So **T-5 needs no exception clause**: this spec approves no `gh` call, and AC-TB9 asserts the absence
directly. No cadence, timeout or missing-`gh` behaviour has to be specified, because none is invoked.

### 4.6 The git tab locally

`local/tabs.py` runs the same git commands as `export_board.git_tab`, through the injected `run`, with
`cwd=repoPath`, `capture_output=True`, `text=True`, `encoding='utf-8'`, and feeds their stdout to
`derive.git_doc` (§3.2). Two additions over the exporter, both local-only and neither changing the
document:

- **A timeout.** Each git call gets `timeout=15` (the value `export_board.PR_TIMEOUT` already uses for
  the same reason: "the refresher runs on a loop, so a hung gh must not stall it",
  `exporters/export_board.py:156`). The collector's loop has the same need. A `TimeoutExpired` or
  `OSError` from any git call means the git tab is **not built** for that project this pass, with a
  warning; §4.4 then carries the stored one. The exporter has no timeout and would hang; that is a local
  hardening, not a divergence in the document.
- **`is_repo` first.** Already the exporter's order (`exporters/export_board.py:256`).

`git log` is run without a limit, as the exporter runs it, so the documents match.

### 4.7 Tab documents and the shapes

Every tab document produced by `derive.spec_docs` and `derive.git_doc` carries `generatedAt` (a string)
and `source`, which is the whole of `SHAPES['tab']` (`local/records.py:57-60`); extra fields are allowed
and kept. A carried document adds `carriedSince`, also an extra field. So every tab record this pass
writes validates, with **no change to the shapes** — criterion T-4, asserted directly in AC-TB10.

Ids are `'%s.%s' % (pid, tab)`. `board_config.projects` already refuses a project id that is not
`[A-Za-z0-9_-]{1,100}` (`exporters/board_config.py:118-119`), and project ids never contain a dot, so
`to_row`'s split on the first `.` (`local/records.py:238`) recovers the project and tab columns correctly.

**The two id checks are near-identical, not identical** (revision 2, finding F-8). `board_config.ID` is
`re.compile(r'^[A-Za-z0-9_-]{1,100}$')` applied with `.match`
(`exporters/board_config.py:17`, `:118`), while `records` applies `_PROJECT_ID` with `.fullmatch`
(`local/records.py:207`). Because `$` also matches before a trailing newline, a project id ending in one
would pass `board_config` and be refused by `records`. `local/records.py:93-94` already documents exactly
this: "re.match with '$' would also accept a trailing newline. That makes the project and status forms
stricter than board_config.ID and STATUS_DOC, but only for strings ending in one." The divergence is
therefore known, one-directional and safe — the stricter check is the one guarding the database — and
revision 1's claim that the two are "exactly" the same is corrected here rather than relied on.

### 4.8 The report line

`run_pass`'s report dict (`local/collector.py:593-595`) gains `tabs` (tab records produced this pass)
and `statuses` (status records written). `summary()` gains `, N tabs` after the projects count. Cosmetic;
no test outside `local/tests/` reads it.

### 4.9 Cadence

**The tab pass runs on every collector pass.** It is the simplest rule that keeps the equivalence
guarantee, and it matches the board, where `refresh.py` runs all three exporters
(`EXPORTERS`, `exporters/refresh.py:43`) unconditionally on every tick, before any diffing
(`exporters/refresh.py:223`). The cost is the ADR and spec file reads plus ten git subprocesses per
project — for the two configured projects, well inside a 60 s interval, and all of it outside the write
lock (§4.2). No config key is added. If it is ever measured to be too heavy, Q-5 names the fix.

---

## 5. The status record

### 5.1 What is written

For each configured project, at its `statusDoc` path, exactly `refresh.py`'s two fields
(`exporters/refresh.py:184`):

- **`live`**: true when any run of that project produced by this pass has `kind == 'running'`
  (`exporters/refresh.py:173`).
- **`updatedAt`**: `clock().isoformat(timespec='seconds')`, the same injected clock `lastRefresh`
  already uses (`local/collector.py:582-583`), so one pass stamps both from one source and the tests can
  fix it.

### 5.2 When `updatedAt` moves

`refresh.py`'s rule is that a project's `updatedAt` moves only when something that project shows has
changed, or its `live` flag flipped (`exporters/refresh.py:162-180`). Locally, "changed" is the set of
records this pass actually **wrote or deleted**, which is exactly what `_Pass.store` already computes:
it skips a record whose document is unchanged **ignoring `generatedAt`** (`local/collector.py:496-499`)
— the same field `refresh.digest` pops (`exporters/refresh.py:84`). So the two notions of "changed"
already agree, and a tab whose only difference is a new `generatedAt` moves no status on either side.

A project's status is rewritten when either holds:

1. this pass wrote or deleted any of: its `project` record, any of its five `tab` records, any `session`
   whose `project` is this project, or any `run` whose `project` is this project; or
2. the computed `live` differs from the `live` in the stored status record (absent counts as differing
   from both `true` and `false`, so the first pass always writes).

Clause 1's "wrote or deleted" covers `refresh.py`'s "a document that was this project's at the last push
still counts" (`exporters/refresh.py:178-179`): a deleted run of this project is in the deletion set, so
it moves `updatedAt` here as it does there.

**The `findings` tab is not in clause 1**, because this PBI writes none (§2). `refresh.py`'s `TABS`
includes it (`exporters/refresh.py:47`), so on the board a findings-only change moves that project's
`updatedAt` and locally it does not. That divergence is named here, is invisible until a later PBI adds
the findings tab locally, and is recorded as Q-3.

### 5.3 Merging, not replacing — `title`, `message` and `metrics`

On the board, a status document is written with `op: "update"` for `meta/status`, and for any status
document already pushed once (`exporters/refresh.py:185`). `update` **merges**, which is what keeps the
hand-written `title`, `message` and `metrics` alive while the refresher rewrites `live` and `updatedAt`.

`db.upsert` replaces the whole `doc` column (`local/db.py:157-162`). So the collector must do the merge
itself:

> the document written is `dict(stored_status_or_empty, live=live, updatedAt=updatedAt)`.

Any `title`, `message` or `metrics` already in the stored record is preserved untouched. On a first
write the record holds `live` and `updatedAt` alone, which is valid: every field of `SHAPES['status']`
is optional (`local/records.py:61-64`).

**Where do `title`, `message` and `metrics` come from locally? Nowhere, and this spec does not invent a
source.** They are written by hand into the artifact store by the building session (CLAUDE.md store-path
table; the only on-disk copy is the backup `snapshot/meta/status.json`). Nothing in `board.config.json`
or `projects/<pid>.json` holds them — verified against the live files. So the local status record has
`live` and `updatedAt`, and the local page's status tile shows no title or message until the owner
decides otherwise. That is open question **Q-1, which needs the owner**; `board.config.json` and
`exporters/board_config.py` are in this PBI's areas precisely so the owner's answer *could* be built
here, but this spec will not guess a config shape for hand-written prose.

T-3 asks the spec to "state the local source of `title`, `message` and `metrics`, each tested". It is
stated — there is none, and the record must not lose them if something else supplies them — and it is
tested: AC-TB7 asserts that a stored status record carrying all three keeps them byte for byte across a
pass that rewrites `live` and `updatedAt`.

### 5.4 Status records are never deleted

`refresh.py`'s `MANAGED` collections — "the collections refresh.py sets and deletes" — are `runs`,
`sessions`, `projects`, `projectTabs`, `catalogue` (`exporters/refresh.py:44`). **`status` is not among
them**, so the refresher never deletes a status document and no status deletion can reach its guard, whose
clauses all run over `MANAGED` (`exporters/refresh.py:146-152`). The collector mirrors that:

*(Revision 2 correction, F-9 sweep: revision 1 supported this with a quote from
`exporters/refresh.py:27-29`. That sentence is about `meta/lastRefresh` — it says lastRefresh "is not
project data: it moves no status document, is never deleted and never counts toward the mass-delete
guard" — so its subject is lastRefresh, not a status document. The quote was misattributed. The claim
itself is unaffected and now rests on `MANAGED` at `:44`, which is the operative evidence.)* **no pass ever deletes a `status` record**, not even for a project removed from the config, and no
status deletion reaches the guard. A stale status record for a removed project is a known, matching leak,
cleaned up by hand exactly as the board's is.

---

## 6. Diff, deletion and the guard

### 6.1 The stored and intended sets

`run_pass` reads `stored = {kind: db.stored(conn, kind) for kind in KINDS + ('catalogue',)}`
(`local/collector.py:572`). `'tab'` and `'status'` join that read. `docs['tab']` is the intended tab set
from §4.3 plus the carries of §4.4; `docs['status']` is computed after the record writes (§5.2) and is
diffed separately, because it depends on what was written.

**`stored['tab']` is filtered before it is diffed** (§2.1). The pass partitions the stored tab records by
the suffix after the first `.`:

- **owned** — suffix in `tabs.OWNED`: these take part in the carry rule, the diff, the deletion set and
  the guard, exactly as below;
- **foreign** — any other suffix, `findings` being the only one that exists today: these are removed from
  `stored['tab']` before step 4 and take part in **nothing**. They are not carried, not diffed, not
  deleted and not grouped by the guard.

A foreign record is therefore left byte for byte as it is by every pass, forever, which is what the
two-writer rule requires: its writer owns its whole lifecycle, including its deletion.

Order inside the transaction, extending `local/collector.py:566-584`:

1. `_Pass.discover` / `assemble` / `catalogue` — unchanged.
2. `stored` now includes `tab` and `status`; `stored['tab']` is partitioned and its foreign records set
   aside, as above.
3. `docs['tab']` is completed from the owned half of `stored['tab']` by the carry rule (§4.4).
4. `deletions = p.reasons(stored, docs)` — now also over `tab` (§6.2).
5. `p.guard(stored, deletions)` — extended (§6.3). Still **before any write**.
6. Upserts for `session`, `run`, `project`, `catalogue`, `tab`.
7. Deletions applied.
8. **Then** `docs['status']` from §5.2, using the write and deletion sets of steps 6 and 7, and its
   upserts.
9. State, `lastRefresh`, `COMMIT` — unchanged.

Each tab and status upsert goes through `_Pass.store`, so it inherits the unchanged-ignoring-`generatedAt`
skip and the per-record `SAVEPOINT` error handling of PBI-019 §4.9 unchanged
(`local/collector.py:490-507`): a tab document that somehow breaks the shapes is skipped with a warning,
its stored version kept, and the pass goes on.

### 6.2 Tab deletions and age pruning — tabs are not prunable

**A tab record is deleted only when it is one this pass owns and its project is no longer in
`board.config.json`.** Nothing else deletes one: a project whose repository moved, whose spec was renamed
or whose git is unavailable keeps its tabs through the carry rule (§4.4). That is `export_board`'s own
rule — "Fix the source; a project's tabs go only when it is removed from `projects`" (CLAUDE.md, refresh
procedure).

**Revision 1's second deletion trigger is removed (finding F-2).** It said a tab record is also deleted
"when its tab name is no longer one of the five", with the five read from `records.TAB_NAMES`. That is a
data-loss bug, and it is the most important change in this revision. `records.TAB_NAMES` is a **blocked
file's** constant that PBI-026 exists to widen, and `projectTabs` has two writers (§2.1). Once PBI-026
lands and a later PBI stores a `findings` record, the deleted-set computed that way would contain it on
every pass — deleting, every 60 seconds, exactly the document PBI-011 publishes and whose lifecycle
`export_sessions.py` owns.

The corrected rule, stated so it cannot drift:

> The intended set, the carry set and the deletion set are **all** scoped to `tabs.OWNED`, a constant
> local to `local/tabs.py` holding the five `export_board` suffixes. A stored tab record whose suffix is
> not in `tabs.OWNED` is never in the deletion set, whatever `records.TAB_NAMES` says, and
> `records.TAB_NAMES` is not read by the deletion logic at all.

A tab name genuinely leaving `tabs.OWNED` would be a change to this repository's own source, made by a
PBI that would delete the records deliberately; it is not a condition this pass discovers at run time.

AC-TB13 asserts both halves: that `tabs.OWNED == export_board.TABS`, and that a pass leaves a stored
`findings` record untouched — storable directly, no patch needed, since `records.TAB_NAMES` already
includes it now that PBI-026 has merged — reproducing the post-PBI-026 world without editing a blocked
file.

**Tab records are never age-pruned.** FR-185 and PBI-019 §4.7 prune *unlinked sessions* by last activity;
a tab document is not a session, has no `last`, and belongs to a project that is either configured or
gone. So every tab deletion carries reason **`other`** and none carries `age`. `_Pass.reasons`
(`local/collector.py:452-470`) already assigns `age` only through the `aged` set of session ids, and a
tab id is never a session id, so the existing code reaches the right answer once `'tab'` is added to the
kinds it iterates; the spec states the rule so it cannot drift.

**A removed project's tabs are cleaned up in the same pass that removes its `project` record** — but see
§6.3: that pass is refused by the guard unless it is run with `--allow-mass-delete`, which is the same
ceremony the board demands.

**Status records are outside all of this** (§5.4): never deleted, never a deletion reason, never in the
guard.

### 6.3 The mass-delete guard

`_Pass.guard` (`local/collector.py:472-488`) refuses on three conditions today: more than half the stored
runs and sessions deleted other than by age; any `project` deletion; the `catalogue` deletion. It gains
`refresh.py`'s fourth clause (`exporters/refresh.py:146-152`):

> **Refuse when the pass would delete every stored tab record of a project that still has stored tabs.**
> Message: `every tab of project <id> (check its repoPath and docs in board.config.json)`.

Computed as `refresh.py` does: group the stored tab ids by the part before the first `.`, and refuse for
any project all of whose stored tab ids are in the deletion set. The rationale is `refresh.py`'s own
comment — because the carry rule keeps a tab whose source went missing, a project losing *all* its tabs
can only mean it left the export.

**With one scoping the board does not need (finding F-2): only owned tab ids are grouped.** A foreign
record (`findings`) is excluded from the grouping entirely — it is neither a member of a project's group
nor evidence that the project still has stored tabs. Two consequences, both deliberate:

- A project whose only stored tab is `findings` has an **empty** owned group. An empty group cannot have
  "every one of its members deleted" in any meaningful sense, so the clause does not fire for it. Without
  this scoping, such a project would trip the guard on the first pass after a later PBI stores its
  findings tab, and would stall every pass indefinitely — the second half of F-2.
- A project losing all five owned tabs is still refused, even if its `findings` record remains. The
  clause protects the five this pass owns; another writer's surviving document is not a reason to permit
  the deletion.

`refresh.py` needs no such scoping because it owns all six `TABS` at the push layer
(`exporters/refresh.py:47`). The local pass owns five of them, so it must say which.

The runs-and-sessions ratio clause is **not** extended to tabs: it counts `session` and `run` records
only, on both sides, and this spec does not change the denominator. A project removed from the config
therefore trips the `project` clause first, and the emptied-tabs clause with it; both are listed in the
one refusal message the existing code assembles.

A refused pass still writes nothing at all — no record, no deletion, no state, no marker, no
last-refresh, and no status — because the refusal is raised before step 6 and the whole pass rolls back
(PBI-019 §4.7; the `ROLLBACK` is at `local/collector.py:585-588`, and `:589-591` then clears the
in-memory cache and re-raises). Tabs and statuses inherit that unchanged. §7.3 says how a test observes
that "wrote nothing" claim soundly, which revision 1 got wrong (finding F-4).

### 6.4 What PBI-019's other rules do to tabs

- **Incremental reads (FR-86, AC-63)** are about transcripts. Tab sources are repository files and git;
  they are read whole every pass, as `export_board` reads them whole every run. No cursor, no state
  table, no `collector_*` row is added.
- **The collector's state tables** are untouched; `STATE_VERSION` is not bumped; no `derive.new_session`
  or `new_agent` key changes, so no session state is reset by this PBI.
- **`data_version` / `db.Changes`** need nothing: a pass that writes a tab or status commits, which the
  server already sees (PBI-019 §3.6).
- **C-16, answers:** unchanged. This PBI adds `tab` and `status`; there is still no `answers` kind, table
  or writer.

---

## 7. Tests

Standard library `unittest` only; nothing touches the real `~/.claude`, `out/`, `board.config.json` or
database. New files only, so nothing PBI-026 edits is edited here (§2).

### 7.1 `tests/test_derive.py` (added cases, none changed)

- `derive.git_default` returns `'master'` when the master probe printed a sha; `'main'` when only the main
  probe did; `''` when neither did; and `'master'` when **both** did, which is the precedence
  `exporters/export_board.py:129` has today.
- `derive.git_doc` on captured git output returns the document `git_tab` returns: the `byDir` counts,
  the commit split on `|` including a subject containing `|`, `tracked` length, `dirty` with blank lines
  dropped, and `repoPath` with backslashes replaced.
- **The emptiness rule, now exercisable** (finding F-5). `git_doc` is called with non-empty `ahead_out`
  and `shortstat_out` and with `default=''`, then with `branch=''`, then with both empty; each time the
  returned `ahead` and `shortstat` are `''`. With both `branch` and `default` non-empty, both values are
  passed through unchanged. Revision 1 asked for this assertion against a signature that could not make
  it — the rule lived in the caller — so the case is only now real.
- `derive.public_remote` strips the userinfo of a URL remote and leaves an scp-form remote alone.
- `derive` still imports no `subprocess` and reads no file: assert `subprocess` is not an attribute of
  the module, guarding the docstring contract of `exporters/derive.py:5-7`.

### 7.2 `tests/test_export_board.py` (added cases, none changed)

**Revision 2 replaces revision 1's committed fixture (finding F-3).** Revision 1 asked for
`export_board.main`'s written bytes to equal "a fixture captured from the pre-move implementation…
generated once during the build, from the current code, and committed". That is unachievable twice over,
and the reviewer is right on both counts:

- The git tab is **not reproducible across runs**. `repoPath` is a fresh temporary directory
  (`exporters/export_board.py:143`), and `head` and every `commits[].sha` and `.date` come from a
  synthetic repository built anew by each test run (`:144`, `:131-133`). No committed byte sequence can
  match it.
- A fixture "generated from the current code" is captured *after* the move, so comparing the post-move
  implementation against it proves only that the code equals itself. It is not evidence about the
  pre-move behaviour at all.

T-6 is instead proved **in-run**, which is stronger because it compares the two implementations directly:

- **The git tab: a reference implementation in the test.** `tests/test_export_board.py` keeps a verbatim
  copy of the pre-move `git_tab` body as a module-level `_reference_git_tab(root, now)` — the exact code
  at `exporters/export_board.py:127-146` on this PBI's base commit, with a comment saying so and naming
  that commit. Both it and the live `git_tab` are driven through **one shared fake `git`** that returns
  fixed captured stdout per argv, so neither touches a real repository and both see identical inputs. The
  test asserts `git_tab(...) == _reference_git_tab(...)`, comparing keys, values **and key order**
  (`list(a) == list(b)`), over several input sets: a repository with a default branch and a current
  branch, one with neither, one whose commit subject contains `|`, and one whose remote carries userinfo.
- **The four spec tabs: byte-identical `main` output.** These *are* deterministic — they derive from
  fixed text files and the injected `now`, with no sha, path or clock in them. So on the suite's existing
  synthetic repositories the test runs `export_board.main` twice, once before and once after nothing
  changes, and asserts the written bytes of `<pid>.spec.json`, `.assumptions.json`, `.decisions.json` and
  `.backlog.json` are byte-identical to a committed fixture. `repoPath` does not appear in them; the
  assertion is checked by the test itself, which fails if any of the four contains the temporary root.
- **The move changes no public surface.** `export_board.public_remote` is still importable and is
  `derive.public_remote`; `export_board.git_tab` still takes `(root, now)` and returns a dict with the
  same key order.

This satisfies T-6's "byte-identical on the same inputs" for everything whose bytes *can* be pinned, and
replaces the rest with a direct old-versus-new comparison, which is what T-6 is actually asking for.

### 7.3 `local/tests/test_tabs.py`

- **Builds the five.** A synthetic project with a spec, PRD, brief, ADR folder, review notes and a git
  repository yields all five tab documents; one without a spec yields only `git`; one whose `repoPath`
  does not exist yields none, with the warning.
- **`carriedSince`, the full FR-190 cycle.** Pass 1 writes a tab; the source is removed; pass 2 keeps the
  record and adds `carriedSince` equal to the pass stamp in `…Z` form; pass 3, still missing, calls
  `db.upsert` zero times for that record (counted) and leaves `carriedSince` identical; pass 4, with the
  source back, writes a rebuilt document with no `carriedSince`.
- **Never exported, never written.** A tab whose source has never existed produces no record and no
  deletion.
- **No network.** With `subprocess.run` patched to record every argv, a full pass runs `git` and nothing
  else — no `gh`, no `curl`, no `claude` — and the stored `git` tab has no `pulls` key even when the
  project's origin is a github.com remote. **Non-vacuous by construction** (finding F-7): the fixture has
  at least one project whose `origin` remote is on github.com — so `export_board.github_origin` would
  return true and the exporter *would* call `gh` — and the recorded argv list is asserted **non-empty**
  with every entry's argv[0] equal to `git`. A pass that ran no subprocess at all fails this test.
- **Git timeout.** A `run` that raises `TimeoutExpired` for one git call leaves the git tab unbuilt, with
  a warning, and the previously stored one carried.
- **Shapes, unchanged — as containment, not equality** (finding F-1). Every tab and status record written
  validates under `records.validate`. The canary then asserts
  `set(records.TAB_NAMES) >= set(tabs.OWNED)` — containment, so PBI-026 widening `TAB_NAMES` to add
  `findings` leaves it green — together with **exact** equality for `records.SHAPES['tab']`,
  `records.SHAPES['status']`, `records.TABLES['tab']`, `records.TABLES['status']` and
  `schema.SCHEMA_VERSION`, none of which PBI-026 touches. Revision 1 pinned `TAB_NAMES` itself to its
  current value, which would have failed the `local/tests` suite — this spec's own close-out criterion —
  the moment both PBIs were on main.
- **Foreign suffixes are untouched** (finding F-2). A `findings` record is inserted directly into the
  database — storable as-is, since `records.TAB_NAMES` already includes it (PBI-026, merged at
  `5baa922`) — reproducing the post-PBI-026 world without editing a blocked file, and a full pass is
  run. Afterwards the record is present and its `doc` column is **unchanged byte for byte**,
  `db.delete` was called zero times for its id, and the pass's report shows the five owned tabs written as
  usual. A second case gives a project a `findings` record and **no** owned tabs at all, and asserts the
  pass is not refused and commits normally — the emptied-tabs clause must not fire on an empty owned
  group. Both cases fail loudly against revision 1's rule.
- **Status.** `live` follows a running run of that project; `updatedAt` moves on a project's own change
  and on a `live` flip and does **not** move on an unrelated project's change or on a pass where only
  `generatedAt` differs; a stored status holding `title`, `message` and `metrics` keeps all three across
  a rewrite; the first write creates the record with the two fields alone; `meta/status` and
  `status/<pid>` both round-trip; no pass ever deletes a status record, including for a project removed
  from the config. **Non-vacuous** (finding F-7): that last case starts from a database that actually
  holds a status record for the project being removed, and asserts the record is still readable
  afterwards with its `doc` unchanged — not merely that no deletion was counted.
- **Guard.** A pass that would delete every stored tab of a project is refused and writes nothing;
  `--allow-mass-delete --once` applies it; a pass deleting *some* tabs of a project is not refused.
  **How "wrote nothing" is observed** (finding F-4): revision 1 asserted `PRAGMA data_version` unchanged
  on the collector's own connection, which is vacuous — `data_version` does not move for changes made on
  the connection reading it, which is precisely the behaviour `db.Changes` exists to exploit and
  documents: "Tells a reader when another connection has committed"
  (`local/db.py:175-186`). Revision 2 asserts instead, in this order of strength:
  1. **directly on the tables**, from a second connection opened after the refused pass: the row count of
     `project_tabs`, `statuses`, `sessions`, `runs`, `projects`, `catalogue` and `last_refresh`, and the
     full `id, doc` text of every row, are identical to a snapshot taken before the pass;
  2. `db.upsert` and `db.delete` call counts of zero, through a counting wrapper;
  3. `PRAGMA data_version` read from that **second** connection, which does move on another connection's
     commit and so is a real signal — kept as a cheap cross-check, never as the only assertion.
- **Deletion reasons, on a real deletion** (finding F-7). A project is removed from the config and the
  pass is run with `--allow-mass-delete`, so the deletion set is **asserted non-empty** (at least the five
  owned tab ids) before the reasons are checked: every one of those deletions carries reason `other`, none
  carries `age`, and the report's `aged` count is unchanged from before the pass.
- **Per-project failure is confined** (finding F-6). Three cases, each over a two-project fixture where
  the *second* project is healthy: an ADR folder whose read raises `PermissionError`; a spec file whose
  read raises `UnicodeDecodeError`; and a git call raising `TimeoutExpired`. In each, the pass
  **commits**: the healthy project's five tabs are written, the failing project's stored tabs are carried
  (§4.4), `meta/lastRefresh`, the session, run, project and catalogue records are all written, a warning
  naming the failing project is emitted, and the exit code is 0. A fourth case gives `load_data` a
  malformed `projects/<pid>.json` and asserts the opposite: the pass raises, the database is unchanged
  (observed as in the guard case above), and nothing at all is written.
- **Per-record error.** With `records.to_row` patched to raise `ValueError` for one tab id, that tab is
  skipped with a warning naming it, its stored version is kept, and every other record of the pass is
  written.

### 7.4 `local/tests/test_tabs_equivalence.py`

The equivalence suite, built on `local/tests/test_conformance.py`'s `Fixture`, which already runs
`export_board.main` over synthetic repositories twice, renaming one project's repository in between
(`local/tests/test_conformance.py:228-235`).

**`Fixture` is imported and consumed exactly as it is; `local/tests/test_conformance.py` is not edited**
(finding F-8). This matters beyond tidiness: that file is under `local/tests/**`, the single area PBI-025
and PBI-026 share, and §2's parallel-safety claim rests on neither PBI editing a file the other touches.
If the build finds it cannot reuse `Fixture` unmodified, that is a **stop-and-report condition**, not a
licence to edit the file — the fallback is a new fixture in a new file under `local/tests/`.

The suite also skips cleanly where the existing one does: `test_conformance.py:21` sets
`HAS_GIT = shutil.which('git') is not None`, and every git-dependent case here carries the same guard, so
the suite passes on a machine without git rather than failing.

- **T-1.** Run `export_board.main(cfg, out, data_dir, NOW)`, then `collector.run_pass(conn, cfg, …)` with
  the same `now`. For every project and every one of the five tabs, the document read from
  `out/projectTabs/<pid>.<tab>.json` and the record read from the database are **equal after removing
  `generatedAt` and `pulls`**. Covered projects: one with a full spec and a git repository, one with a
  spec and no git repository, one with neither.
- **Carry equivalence.** The fixture's second `export_board` run, with a project's repository moved away
  (`local/tests/test_conformance.py:228-235`), is matched by a second collector pass: both sides now
  carry, and the `carriedSince` values are equal.
- **Ownership equivalence** (finding F-2). `export_sessions.main` is run over the same fixture so that
  `out/projectTabs/<pid>.findings.json` exists, and `export_board.main` is run again. The exporter leaves
  that file untouched (`exporters/export_board.py:277-285`). The collector pass, over a database holding
  the equivalent `findings` record, leaves that record untouched. The two sides agree on which suffixes
  each writer owns, which is the property F-2 is about.
- **Status equivalence.** `refresh.plan`'s status documents and the collector's status records agree on
  `live`, and agree on *whether* `updatedAt` moved between two passes, for: a first pass, a quiet pass, a
  pass where only one project's run changed, and a pass where a linked run was deleted.

### 7.5 Suites

All three configured suites stay green on the head commit:
`python -m unittest discover -s tests`, `node tests/page.test.mjs`,
`python -m unittest discover -s local/tests`.

---

## 8. Acceptance criteria

**From the PBI file**, restated so each is mechanically verifiable.

- [ ] **T-1 Tab records match the exporter.** After a collector pass, each project's `spec`,
      `assumptions`, `decisions`, `backlog` and `git` records equal `export_board.py`'s documents for the
      same repository, config, data file and `now`, ignoring `generatedAt` and `pulls`. *(§4.3, §7.4.)*
- [ ] **T-2 Keep-last and `carriedSince`.** A tab whose source goes missing after a pass wrote it is kept
      and marked with `carriedSince`; the value is unchanged on later passes while the source stays
      missing, and gone once the source returns. *(§4.4, §7.3.)*
- [ ] **T-3 Status records.** Each project's status record is written at its `statusDoc` path with `live`
      and `updatedAt` by `refresh.py`'s rule. **Its first clause — "the spec states the local source of
      `title`, `message` and `metrics`" — is a spec-authoring condition, satisfied at this gate, not a
      close-out check** (finding F-8): §5.3 states it (there is none) and Q-1 settles it. The
      close-out-verifiable half is AC-TB7's: a stored value of each is preserved across a rewrite.
      *(§5, §7.3, §7.4; row Q-1, settled.)*
- [ ] **T-4 Shapes.** Every tab and status record written validates against `local/records.py`'s shapes,
      with no change to `local/records.py`, `local/records.shapes.json` or `local/schema.py`. *(§2, §4.7,
      AC-TB10.)*
- [ ] **T-5 Network boundary.** A test with a patched `subprocess` proves the pass runs no network
      command. **This spec approves no `gh` exception**, so T-5's conditional second half does not apply.
      *(§4.5, AC-TB9.)*
- [ ] **T-6 Behaviour unchanged for v1.** `export_board.git_tab` returns the same document, key order
      included, as a verbatim pre-move reference implementation driven through the same fake `git`; and
      `export_board.main`'s written bytes for the four deterministic spec tabs are byte-identical to a
      committed fixture. No existing test case is changed. *(§3.2, §7.2, AC-TB11; the unreproducible
      whole-output fixture of revision 1 is replaced per finding F-3.)*

**Added by this spec.**

- [ ] **AC-TB1** With `export_board.main` and one collector pass run on the same synthetic repositories,
      config, data files and `now`, the `{id: doc}` maps of tab documents from `out/projectTabs/` and
      from the database are equal after removing `generatedAt` and `pulls`, for a project with a full
      spec and git, one with a spec and no git, and one with neither.
- [ ] **AC-TB2** A tab whose source has never existed has no record and produces no deletion. A project
      whose `repoPath` does not exist produces no tab documents this pass and a warning naming it.
- [ ] **AC-TB3** *(FR-153, FR-190.)* The four-pass carry cycle of §7.3 holds: first carry adds
      `carriedSince` in `%Y-%m-%dT%H:%M:%SZ` form; a later carrying pass calls `db.upsert` zero times for
      that record; a rebuilt tab has no `carriedSince`. The local `carriedSince` equals the exporter's for
      the same `now`.
- [ ] **AC-TB4** A tab record this pass owns is deleted only when its project leaves `board.config.json`.
      Verified on a **non-empty** deletion set (finding F-7): a project is removed from the config and the
      pass run with `--allow-mass-delete`, the deletion set is asserted to contain at least its five owned
      tab ids, and every one of those deletions carries reason `other`; none carries `age`, and the
      report's `aged` count is unchanged.
- [ ] **AC-TB5** *(FR-184, FR-49 equivalence.)* A pass that would delete every stored **owned** tab record
      of a project is refused with the message naming that project; the refusal is decided before any
      upsert (`db.upsert` and `db.delete` counted at zero) and leaves records, state, markers,
      last-refresh and status unchanged. **The "unchanged" assertion is made on the tables themselves —
      row counts and the full `id, doc` text of every row, compared against a pre-pass snapshot read from
      a second connection** (finding F-4); `PRAGMA data_version` may be read as a cross-check only from
      that second connection, never from the collector's own, where it does not move for the connection's
      own writes (`local/db.py:175-186`). `--allow-mass-delete --once` applies the deletions. A pass
      deleting only some of a project's owned tabs is not refused.
- [ ] **AC-TB6** Each project's status record is written at `board_config.projects(cfg)`'s `statusDoc`
      (both the `meta/status` and `status/<pid>` forms), with `live` true exactly when one of that
      project's runs has `kind == 'running'`, and `updatedAt` from the injected clock.
- [ ] **AC-TB7** `updatedAt` moves when that project's `project`, `tab`, linked `session` or linked `run`
      records were written or deleted this pass, or when `live` flipped; it does not move on an unrelated
      project's change, nor on a pass whose only difference is `generatedAt`. A stored status record
      holding `title`, `message` and `metrics` keeps all three unchanged across such a rewrite.
- [ ] **AC-TB8** No pass deletes a `status` record, including a pass that removes a project from the
      config, and no status deletion is ever passed to the guard. **Non-vacuous** (finding F-7): the
      database holds a status record for the removed project before the pass, and after it that record is
      still readable with its `doc` byte-unchanged.
- [ ] **AC-TB9** *(FR-96, NFR-17.)* With `subprocess.run` patched to record every argv, a full pass
      invokes `git` and nothing else — no `gh`, no `claude`, no network client — and the stored `git` tab
      has no `pulls` key. **Non-vacuous** (finding F-7): at least one fixture project has an `origin`
      remote on github.com, so `github_origin` is true and the exporter would call `gh`; the recorded argv
      list is asserted non-empty and every entry's argv[0] is `git`. A git call that times out or cannot
      be run leaves that tab unbuilt, with a warning, and the stored one carried.
- [ ] **AC-TB10** *(T-4 canary, re-expressed per finding F-1.)* Every tab and status record written passes
      `records.validate`; `set(records.TAB_NAMES) >= set(tabs.OWNED)` (**containment**, so PBI-026's
      widening keeps it green); and `records.SHAPES['tab']`, `records.SHAPES['status']`,
      `records.TABLES['tab']`, `records.TABLES['status']` and `schema.SCHEMA_VERSION` are each **exactly
      equal** to their values at the start of this PBI. `records.TAB_NAMES` is **not** pinned to a value.
- [ ] **AC-TB11** *(T-6, re-expressed per finding F-3.)* `export_board.git_tab` equals a verbatim pre-move
      `_reference_git_tab` kept in the test — same keys, same values, same key order — over at least four
      input sets driven through one shared fake `git`, with no real repository touched. `export_board.main`'s
      written bytes for the four deterministic spec tabs are byte-identical to a committed fixture, and the
      test asserts none of those four contains the temporary repository root. `derive` still has no
      `subprocess` attribute. No byte-identity is claimed for the git tab, whose `repoPath`, `head` and
      `commits[].sha`/`.date` are not reproducible across runs.
- [ ] **AC-TB12** A tab record that cannot be stored (`records.to_row` raising one of PBI-019's
      `RECORD_ERRORS`) is skipped with a warning naming its kind and id, its stored version is kept, and
      every other record of the pass is written.
- [ ] **AC-TB13** *(Finding F-2, the two-writer rule.)* `tabs.OWNED == export_board.TABS`, and the
      deletion logic reads `tabs.OWNED`, never `records.TAB_NAMES`. With a `findings` tab record stored
      directly — valid as-is, since `records.TAB_NAMES` already includes it now that PBI-026 has merged,
      reproducing the post-PBI-026 world without editing a blocked file — a full pass leaves that record
      present and its `doc` byte-unchanged, calls `db.delete` zero times for its id, and still writes the
      five owned tabs. A project whose only stored tab is `findings` does not trip the guard's
      emptied-tabs clause, and its pass commits normally.
- [ ] **AC-TB14** *(Finding F-6, per-project failure confinement.)* Over a two-project fixture whose
      second project is healthy, each of a `PermissionError` on the first project's ADR folder, a
      `UnicodeDecodeError` on its spec file, and a `TimeoutExpired` from one of its git calls leaves the
      pass **committing**: the healthy project's five tabs written, the failing project's stored tabs
      carried, `meta/lastRefresh`, sessions, runs, projects and catalogue all written, a warning naming
      the failing project, exit code 0. A malformed `projects/<pid>.json` instead fails the whole pass and
      writes nothing, observed on the tables as in AC-TB5.

**Out of scope**, restated from the PBI file and confirmed here: the page and its data adapter (PBI-006);
the local server (PBI-005, which needs no change, §1); log-on start (PBI-007); answers (C-16); the
`findings` tab locally (§2, Q-3); and **any change to `local/records*`, `local/records.shapes.json`,
`local/schema*`, `local/server*` or `site/**`** — none is specified, and AC-TB10 asserts it.

**Close-out.** The three configured suites are green on the head commit
(`python -m unittest discover -s tests`, `node tests/page.test.mjs`,
`python -m unittest discover -s local/tests`), and the code-review gate passed
(`review-agents:code-reviewer` GO).

**That is 21 criteria: 6 from the PBI file, 14 added (AC-TB13 and AC-TB14 new in revision 2), and the
close-out.**

---

## 9. Assumptions and open questions

**Owner** marks a row that genuinely needs the owner before building. The rest are settled here or at the
spec gate.

| # | Question | Default chosen | Impact if wrong | Needs |
|---|---|---|---|---|
| Q-1 | Where do a local status record's `title`, `message` and `metrics` come from? On the board they are hand-written into the artifact store; nothing on disk holds them (verified against `board.config.json`, `projects/*.json` and CLAUDE.md) | **Settled at this gate — no local source, build the default.** The collector writes only `live` and `updatedAt`, merged onto the stored record so any of the three that is present survives (§5.3). This is not a choice the spec is making: it is *exactly* what `refresh.py` does (`exporters/refresh.py:184-185` writes those two fields and merges with `op: update`), so §1's equivalence rule already mandates it. Revision 1 marked this OWNER while calling its own default "safe to build against and reversible", which was a contradiction. **Considered and rejected as a seed source: `snapshot/meta/status.json`** — it does hold `title`, `message` and `metrics` on disk, but it is a dated backup of the artifact store (2026-09-10, CLAUDE.md), covers only platform-catalogue, and is not a live source any pass could re-read; seeding from it would publish stale prose as if it were current. **Follow-up PBI:** a config-sourced `status` block per project | Local status tiles show `live` and a timestamp but no title or message until the follow-up lands. Nothing is lost: any hand-written value already in the record survives every pass | settled |
| Q-2 | Is excluding `pulls` locally acceptable, given T-1 allows it "for example"? | **Yes.** `gh` is a network client and FR-96 / NFR-17 / AC-70 forbid one; T-1 pre-authorises the exclusion ("any field the spec explicitly excludes locally, for example `pulls`"). The page already renders the `pulls`-absent state (§4.5). **The word "permanently" is dropped** (revision 2): this spec excludes `pulls` from *this* PBI, and takes no position on forever | The local GitHub tab shows repository facts but no pull requests. **FYI to the owner, not a gate blocker:** restoring them would need a separate process outside the collector, since no collector exception is available — that is a product-scope reduction worth seeing, and the owner may want a follow-up PBI for it | settled, **FYI to owner** |
| Q-3 | The `findings` tab (PBI-011) is written by `exporters/export_sessions.py`, which is outside this PBI's areas, and `records.TAB_NAMES` now accepts it (PBI-026 merged at `5baa922`, status `Done`, `docs/backlog/pbi/PBI-026-findings-tab.md:4`) | **Out of scope, and now explicitly protected.** PBI-025 writes the five `export_board` tabs only. No dependency on PBI-026 is created, and the two are parallel-safe (§2). Revision 2 adds the missing half: this pass must also never *delete* a findings record (§2.1, §6.2, AC-TB13) — without that, PBI-026 landing would have turned an out-of-scope tab into a destroyed one. **The follow-up PBI should be raised now**, rather than banked: PBI-026 has already landed (`5baa922`), so the gap is open now and the follow-up is ready to schedule immediately | The local Findings view stays "not exported yet", and a findings-only change does not move a project's local `updatedAt` where it moves the board's (§5.2). PBI-007's end-to-end claim of "a board that needs no Claude session" is complete for the five tabs and the status tiles, but not for Findings | **OWNER** (a backlog-curation call only: when to raise the follow-up. Non-blocking — the build proceeds on this default either way) |
| Q-4 | Does the pure half of `git_tab` belong in `derive`, given `derive`'s "reads no file, config, git or network" contract? | **Yes, split it — with revision 2's correction (F-5).** `derive.git_default` takes the two branch probes' stdout; `derive.git_doc` takes captured command output **and applies the `ahead`/`shortstat` emptiness rule itself**. The `subprocess` calls stay in `export_board.git_tab` and are repeated (about ten lines) in `local/tabs.py` (§3.2, §3.3). Revision 1's signature left both derivations in the caller, so `local/tabs.py` would have re-implemented them — breaking rule 2 — and §7.1 tested `git_doc` for a rule its signature could not reach | If the reviewer prefers no split, the alternative is `local/tabs.py` calling `export_board.git_tab` whole. That is fewer lines but puts git I/O behind an exporter function the collector cannot time out, and the parent's rule would then be met by import rather than by sharing the derivation | settled |
| Q-5 | Cadence: tab reads (repo files and ten git subprocesses per project) are heavier than transcript reads | **Every pass**, no config key (§4.9). The work is outside the write lock (§4.2), and `refresh.py` runs `export_board.py` on every tick | If measured too heavy on a large repository, add `local.tabIntervalSeconds` to the `local` block — `board.config.json` and `exporters/board_config.py` are already in this PBI's areas, so it is a contained follow-up | — |
| Q-6 | Is `carriedSince` carried locally at all, given the board implements it over `out/` files? | **Yes** (§4.4). The stored record is the local persistent copy, and FR-190 is about the behaviour, not the medium | Without it, a project whose repository moved would silently show stale tabs with no marker, which is exactly what FR-190 exists to prevent | — |
| Q-7 | Are tab records prunable by age (FR-185)? | **No** (§6.2). FR-185 prunes unlinked sessions; a tab is not a session and has no `last`. Every tab deletion is reason `other` | If tabs were prunable, a quiet project's tabs would vanish from the local board while the artifact board kept them, breaking T-1 | — |
| Q-8 | Are status records ever deleted or guarded? | **No** to both (§5.4), mirroring `refresh.py`, where `status` is outside `MANAGED` | A removed project leaves a stale status record, exactly as it does in the artifact store. Cleaned up by hand if it ever matters | — |
| Q-9 | Should the guard's runs-and-sessions ratio count tab records? | **No.** The denominator stays `sessions + runs`, as in `refresh.py`. Tabs get their own per-project clause (§6.3) | A project with many tabs would otherwise dilute the ratio and weaken the session guard | — |
| Q-10 | Where does the tab pass sit relative to `BEGIN IMMEDIATE`? | **Before it** (§4.2): the reads need nothing from the database, and holding the write lock across ten subprocess calls per project would stretch PBI-019 §3.5's lock scope | If a reviewer prefers everything inside one transaction (as the catalogue read already is, `local/collector.py:440-450`), the change is small but the lock is held longer, which the local server and a second collector both feel | — |
| Q-11 | A git call that hangs | **15 s timeout per call** (§4.6), the value `export_board.PR_TIMEOUT` already uses; on timeout the tab is not built and the stored one is carried. The exporter has no such timeout | A slow-but-healthy repository could carry its git tab for a pass. The next pass rebuilds it | — |
| Q-12 | Does `local/tabs.py` importing `export_board` reopen the `carried` name clash PBI-019 §2 avoided? | **No.** The module is imported, never its names, and `export_board.carried` is not used at all (§4.4 works on documents, not bytes) | A star-import in the build would reintroduce it; the reviewer should watch for one | — |
| Q-13 | `board.config.json` and `exporters/board_config.py` are in the PBI's areas "for any cadence or `gh` key the spec settles on" | **Neither is edited.** No cadence key (Q-5), no `gh` key (Q-2) | None. An unused allowed area is not a defect | — |
| Q-14 | T-6 says "no existing test is edited", but §7.1 and §7.2 add cases to `tests/test_derive.py` and `tests/test_export_board.py` | **Settled at this gate.** Read as **no existing test case is changed**; adding cases to an allowed file is how T-6 is proved. Both files are named in the PBI's `allowed_areas`; `tests/**` as a whole is not, so a new `tests/test_git_doc.py` would be **outside** them. The literal reading therefore makes T-6 unprovable, which means the reinterpretation is forced rather than convenient. Recorded in §11 as an explicit restatement of a PBI-file criterion, so the build reviewer sees it was decided and not assumed | None. The restatement narrows nothing: no existing case changes either way | settled at gate (§11) |

**One row is marked OWNER: Q-3, and it does not block the build.** It is a backlog-curation call about
*when* to raise a follow-up for a *later* PBI's scope; the build proceeds on its default either way.

**Q-1 is no longer an OWNER row** (revision 2). The reviewer's call is accepted: writing only `live` and
`updatedAt` and merging is what `refresh.py` does, so the equivalence rule mandates it rather than leaving
it open, and revision 1 contradicted itself by marking OWNER while calling the same default safe and
reversible. The default is built; a config-sourced status block is recorded as a follow-up PBI.

**One row carries an FYI to the owner: Q-2.** Not a gate blocker — the `pulls` exclusion is forced by
FR-96 / NFR-17 and pre-authorised by T-1 — but "restoring pull requests needs a separate process outside
the collector" is a product-scope reduction the owner should see rather than discover.

**Two follow-up PBIs are recommended by this spec**, neither in its scope: a config-sourced status block
(Q-1) and the local findings tab, gated on PBI-026 (Q-3). Q-2 may warrant a third if the owner wants pull
requests locally. Every other row is settled here.

---

## 10. Out of scope

- **The page and its data adapter** (PBI-006): rendering the five tabs and the status tiles from the
  local snapshot.
- **The local server** (PBI-005): it already serves `tab` and `status` from `records.TABLES` and needs no
  change (`docs/backlog/specs/pbi-005-local-server.md:77-80`).
- **Log-on start and the end-to-end checks** (PBI-007), including AC-70's inspection that the collector
  contacts no network host — this PBI keeps that true (§4.5) but does not test it end to end.
- **The `findings` tab locally** (§2, §2.1, Q-3): *writing* it needs `exporters/export_sessions.py`,
  outside these areas, and PBI-026's widened `TAB_NAMES`. **Not writing it is not the same as ignoring
  it:** this pass must actively leave a stored `findings` record alone — never deleted, never carried,
  never counted by the guard (§6.2, §6.3, AC-TB13). That protection *is* in scope, and is the fix for
  finding F-2.
- **`pulls` locally** (§4.5, Q-2).
- **Any change to record shapes or the schema** (§2): `local/records*`, `local/records.shapes.json`,
  `local/schema*` are blocked and untouched.
- **`local/server*` and `site/**`**: blocked.
- **The refresher's plan counts** (AC-34, AC-42, AC-44): `exporters/refresh.py` and
  `tests/test_refresh.py` are outside these areas, so those counts and tests are unchanged regressions on
  this PBI's head commit.
- **Answers, of any kind** (C-16, D-22).

---

## 11. Spec-gate record

| Round | Revision reviewed | Verdict | Review note |
|---|---|---|---|
| 1 | 1 | CHANGES-REQUIRED | `docs/backlog/reviews/PBI-025/spec-review-r1.md` |

Round 1 (2026-09-12): CHANGES-REQUIRED, 2 High, 4 Medium, 2 Low, 1 Info; **all nine applied in revision
2, none deferred** — see `docs/backlog/reviews/PBI-025/spec-review-r1.md`.

The reviewer re-verified the COHERENT AS WRITTEN claim of §2 independently and upheld it, going further
than the spec did: `local/schema.py:24-27` builds the DDL from `records.TABLES.values()`, so
`project_tabs` and `statuses` already exist at `SCHEMA_VERSION = 1` and `db.open_db`'s column check
(`local/db.py:145-147`) passes untouched. That verdict is unchanged in revision 2, and no part of the
design was weakened to accommodate a finding.

| Finding | Sev | Disposition in revision 2 |
|---|---|---|
| F-1 | **High** | **Applied.** AC-TB10 and §7.3's canary no longer pin `records.TAB_NAMES`. The assertion is now containment — `set(records.TAB_NAMES) >= set(tabs.OWNED)` — plus exact equality for `SHAPES['tab']`, `SHAPES['status']`, `TABLES['tab']`, `TABLES['status']` and `SCHEMA_VERSION`, none of which PBI-026 touches (its `allowed_areas` are `local/records*`, `local/records.shapes.json`, `local/tests/**`; `docs/backlog/pbi/PBI-026-findings-tab.md:7`). The canary that would have failed the `local/tests` suite — this spec's own close-out criterion — the moment both PBIs reached main is gone |
| F-2 | **High** | **Applied, and treated as the priority.** Revision 1's second deletion trigger ("when its tab name is no longer one of the five", computed from `records.TAB_NAMES`) is **removed**. New §2.1 states the two-writer ownership rule with its evidence: `export_board` owns the five (`exporters/export_board.py:7-10`, `:39`, and the suffix-filtered deletion sweep at `:277-285`), `export_sessions` owns `findings` and "owns that document's whole lifecycle -- write and delete" (`exporters/export_sessions.py:290-308`), and `refresh.py`'s own `TABS` is the six with a two-writer comment above it (`exporters/refresh.py:45-47`). The intended, carry, deletion and guard-grouping sets are all scoped to a **local** constant `tabs.OWNED`, never `records.TAB_NAMES` (§4.4, §6.1, §6.2, §6.3); a foreign suffix is not built, not carried, not deleted and not grouped. The mechanism is named exactly: `_ID_FORMS['tab']` is built *from* `TAB_NAMES` (`local/records.py:103`), so PBI-026 (landed at `5baa922`) makes `<pid>.findings` a storable local id, and revision 1 would have deleted that record every 60 s, plus stalled a findings-only project on the emptied-tabs clause. AC-TB13 is new and tests both halves by storing a `findings` record directly, rather than editing a blocked file; revision 3 drops the monkey-patch this disposition originally described, once `findings` was already valid without one (N-2, §11) |
| F-3 | Med | **Applied.** The unachievable committed fixture is gone from §7.2 and AC-TB11, with both reasons recorded: the git tab's `repoPath`, `head` and `commits[].sha`/`.date` come from a freshly built synthetic repository and are not reproducible (`exporters/export_board.py:143-146`), and a fixture captured after the move proves only that the code equals itself. Replaced by the reviewer's in-run equivalence: a verbatim pre-move `_reference_git_tab` kept in `tests/test_export_board.py`, both it and the live `git_tab` driven through one shared fake `git`, compared on keys, values and key order over four input sets — plus genuine byte-identity for the four deterministic spec tabs, which carry no sha, path or clock |
| F-4 | Med | **Applied.** The vacuous assertion is gone. §7.3 and AC-TB5 now observe "wrote nothing" on the tables directly — row counts and the full `id, doc` text of every row against a pre-pass snapshot — read from a **second** connection, with `db.upsert`/`db.delete` counts of zero. `PRAGMA data_version` survives only as a cross-check from that second connection, with the reason stated: it does not move for the reading connection's own writes, which is exactly what `db.Changes` exists to exploit and documents ("Tells a reader when another connection has committed", `local/db.py:175-186`) |
| F-5 | Med | **Applied.** `derive.git_default(master_out, main_out)` is added, and `git_doc` now takes the raw `ahead`/`shortstat` stdout plus `branch`/`default` and applies the emptiness rule itself (§3.2). No derivation is duplicated in `local/tabs.py` any more — only the subprocess sequence, which is I/O. A caller skipping the two subprocesses is now a pure optimisation that cannot diverge, since the skipped call would have passed `''` and `git_doc` returns `''` either way. §7.1 is fixed: the emptiness rule is tested through `git_doc`'s own signature, which revision 1's could not exercise, and `git_default`'s master-wins precedence (`exporters/export_board.py:129`) is tested too |
| F-6 | Med | **Applied.** New §4.2.1 replaces the footnote with a stated failure boundary. A per-project `OSError`, `PermissionError`, `UnicodeDecodeError` or git failure is confined to that project: warn, build no tabs, carry per §4.4, and the pass **commits** everything else. The blast radius is spelled out — `_one` catches every exception and logs one line (`local/collector.py:643-648`) and the interval loop continues (`:696-708`), so revision 1 would have destroyed every session, run, project, catalogue and `lastRefresh` record every 60 s indefinitely for one project's unreadable file. `load_data`'s `ValueError` stays a whole-pass failure, and §4.2.1 says explicitly why it is different: it is the hand-kept build state, no carried document protects against reading it as absent, and `export_board` makes the same trade for the same stated reason (`exporters/export_board.py:22-25`, `:273-275`). AC-TB14 is new |
| F-7 | Low | **Applied, not deferred.** Each vacuously satisfiable criterion gets a non-empty precondition: AC-TB4 asserts the deletion set contains at least five owned tab ids before checking reasons; AC-TB8 starts from a database that holds the removed project's status record and asserts it is still readable with `doc` unchanged; AC-TB9 requires a fixture project with a github.com `origin` (so `github_origin` is true and `gh` *would* be called) and asserts the recorded argv list is non-empty with every argv[0] equal to `git`. §7.3 carries the same wording |
| F-8 | Low | **Applied, all three parts.** T-3's first clause is marked a spec-authoring condition **satisfied at this gate**, with AC-TB7 named as its close-out-verifiable half. §4.7's "exactly `records._PROJECT_ID`" is corrected: `board_config.ID` is `^...$` with `.match` (`exporters/board_config.py:17`, `:118`) and `records` uses `.fullmatch` (`local/records.py:207`), so a trailing newline diverges — as `local/records.py:93-94` already documents; the divergence is one-directional and the stricter check guards the database. §7.4 states that `test_conformance.Fixture` is consumed **unmodified**, and that needing to edit it is a stop-and-report condition, not a licence — because that file is the single area PBI-025 and PBI-026 share and §2's parallel-safety claim rests on it |
| F-9 | Info | **Applied, with one correction to the finding.** Re-verified every cited line against the live tree at `3e3ec44`. **The two drifts F-9 reports do not reproduce:** `exporters/board_config.py:118-119` is exactly the project-id refusal and `:130-132` is exactly the project dict, confirmed by direct read. The sweep did find **three real errors of its own**, all now fixed: §5.4 attributed "is never deleted and never counts toward the mass-delete guard" to a status document, but `exporters/refresh.py:27-29` says that of **`meta/lastRefresh`** — the claim now rests on `MANAGED` at `:44`, which is the operative evidence; §4.9 cited `refresh.py:43` for "runs on every tick", which is only the `EXPORTERS` tuple — the unconditional run is at `:223`; and `derive.spec_docs` ends at `:938`, not `:944`. Also corrected: `local/collector.py:589-591` is the cache-invalidate-and-re-raise path, not the rollback, which is `:585-588`; the `export_board` deletion sweep runs to `:285` |

**Q-14, recorded here as the gate asked (F-8 / reviewer's owner table).** T-6's "no existing test is
edited" is restated as **"no existing test *case* is changed"**. This is an explicit restatement of a
PBI-file criterion, decided at this gate and not assumed by the author: `tests/test_derive.py` and
`tests/test_export_board.py` are named individually in `allowed_areas` while `tests/**` is not, so the
literal reading would force the new cases into a file outside the PBI's areas and make T-6 unprovable.
No existing case changes under either reading.

**Owner rows after revision 2:** Q-3 alone stays OWNER (backlog curation, non-blocking). Q-1 is settled
at this gate on the reviewer's call, with `snapshot/meta/status.json` named as a considered-and-rejected
seed source and a config-sourced status block recorded as a follow-up PBI. Q-2 and Q-14 are settled, Q-2
carrying an FYI to the owner about the product-scope reduction.

### Round 2

| Round | Revision reviewed | Verdict | Review note |
|---|---|---|---|
| 2 | 2 | APPROVE-WITH-NOTES | `docs/backlog/reviews/PBI-025/spec-review-r2.md` |

Round 2 (2026-09-12): APPROVE-WITH-NOTES — all nine round-1 findings independently re-verified as
genuinely resolved in the spec text; **N-1 through N-4 applied in revision 3 as a text pass, none
deferred; N-5 is not this spec's to fix**. Every note is a stale fact created by PBI-026 landing mid-gate
(`5baa922`); none changes a rule, and none could have produced a wrong build — see
`docs/backlog/reviews/PBI-025/spec-review-r2.md`.

**Round 1's F-9 adjudicated withdrawn.** The round-2 reviewer read both sites F-9 named directly:
`exporters/board_config.py:118` is exactly the project-id refusal (round 1 cited `:120` for the raise)
and `:130-132` is exactly the project dict (round 1 cited `:131-133`). **Neither drift reproduces, so
round 1's F-9 is withdrawn** — the likely cause was a `sed`-based line-offset read rather than a direct
one. In its place, the round-2 reviewer's own direct sweep found four citation errors, unrelated to
F-9's original claim, that were real; all four are recorded below (mostly as N-3) and are now fixed.

| Finding | Sev | Disposition in revision 3 |
|---|---|---|
| N-1 | Low | **Applied.** §2's evidence row and the "one collision to record" paragraph are refreshed to the merged reality: `records.TAB_NAMES` is now the six names `('spec', 'assumptions', 'decisions', 'backlog', 'git', 'findings')`, PBI-026 merged at `5baa922`, and `docs/backlog/pbi/PBI-026-findings-tab.md:4` reads `status: Done`. Q-3 and this gate's own F-2 disposition are updated to the past tense of a landed dependency. **§2.1's rules are left exactly as they were** — they were already scoped to `tabs.OWNED`, never to the stale fact, and the reviewer verified them line by line |
| N-2 | Low | **Applied.** §7.3, AC-TB13 and §6.2's restatement of it no longer monkey-patch `records.TAB_NAMES`: the `findings` record is stored directly, valid as-is now that `findings` is already in `TAB_NAMES` post-merge. The patch was always inert regardless — `_ID_FORMS['tab']` is compiled at import from `TAB_NAMES` (`local/records.py:103`), so rebinding the tuple at runtime validated nothing. The criterion itself, and its non-vacuous preconditions, are unchanged |
| N-3 | Info | **Applied.** §2's citation into `local/tests/test_conformance.py` is refreshed for that file's +73-line growth from the PBI-026 merge: `:342`, `:344-347` and `:401-413` become `:353` (the `('tab', 'alpha.findings')` entry) and `:415` (the kinds set). `:82` and `:269-270` were re-verified unchanged and left as they were |
| N-4 | Low | **Applied.** §4.2.1 now states plainly that the per-project handlers must be scoped to the specific calls that can raise them, with the `load_data` call kept outside that confined block: `UnicodeDecodeError` is a subclass of `ValueError`, so a single block-level `except ValueError` around §4.3 step 2 would silently catch the one exception §4.2.1 requires to fail the whole pass, undoing the row-2/row-4 distinction the table draws |
| N-5 | Info | **Not this spec's to fix — flagged to the owner as close-out bookkeeping on the PBI-019 and PBI-005 spec files.** It concerns those specs' own front matter, not this one, and this PBI's allowed areas do not include them; the orchestrator is handling it |
