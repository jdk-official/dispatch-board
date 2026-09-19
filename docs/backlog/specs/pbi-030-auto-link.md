---
id: PBI-030
title: "Sessions link to a project automatically from the files they edit"
pbi: PBI-030
status: approved at spec-gate round 2 (APPROVE-WITH-NOTES; notes applied in revision 3 as a text pass)
revision: 3
parent_spec: docs/backlog/specs/dispatch-board.md
parent_revision: 5
date: 2026-09-19
grounded_at: 8bd2621
reviews: docs/backlog/reviews/PBI-030/spec-review-r1.md (round 1, revision 1, CHANGES-REQUIRED); docs/backlog/reviews/PBI-030/spec-review-r2.md (round 2, revision 2, APPROVE-WITH-NOTES). Dispositions for both rounds are in §11
---

# PBI-030: Sessions link to a project automatically from the files they edit (per-PBI spec)

**Citations note.** Every `path:line` below is grounded at `8bd2621` (`main`, 2026-09-19). The code paths this
spec cites (`exporters/`, `local/`, `tests/`, `site/`, `board.config.json`) had no uncommitted changes when
it was grounded. PBI-010 is building in parallel and edits `exporters/derive.py`, including `project_doc`.
PBI-030 builds only after PBI-010 merges (PBI file, Notes), so **the builder must re-ground every line
number against its own base.**

## 1. Intent

Today a session belongs to a project only when its id is listed in that project's `sessions` in
`board.config.json`. `settings()` builds `project_of` from those lists alone
(`exporters/export_sessions.py:92-95`), and a new session lands in "Other sessions" until the owner copies
its id into the config (`site/index.html:350-352` groups by the session document's `project`).

After this PBI, a session that no project lists is linked to a project when its own transcripts show it
**successfully editing a file** inside that project's `repoPath`, or inside one of that project's worktree
folders. The hand-kept list stays, and it wins.

**Sources.**

- **The PBI:** `docs/backlog/pbi/PBI-030-auto-link-sessions.md`. Allowed areas are at `:7`, the four
  decisions this spec must settle at `:27-31`, and criteria L-1 to L-6 at `:37-42`.
- **PRD** (`docs/prd/dispatch-board.md`):
  - the glossary's "Linked session" (`:54`);
  - FR-3 (`:242`), FR-38 (`:289`), FR-40 (`:294`), FR-87 (`:422`), FR-137 to FR-139 (`:366-368`) and
    FR-185 (`:429`);
  - AC-90 (`:724`), AC-120 and AC-121 (`:760-761`);
  - A-36 (`:803`).
- **Parent spec, revision 5:**
  - "All derivations live in one shared module under `exporters/`; the collector imports it, never
    re-implements it" (`docs/backlog/specs/dispatch-board.md:87` at revision 5, `git show 8bd2621:…`);
  - row 12, "the last 7 days plus linked sessions, pruned by age only" (`:296`);
  - D-9, code-writer under TDD then code-reviewer (`:89`).
  - These parent line numbers are revision 5's (`8bd2621`); the working copy carries a revision-6 draft
    whose numbering differs (revision 2, SG30-9).
  - Sections marked "(rev 6, draft)" are ignored.
- **Live code at `8bd2621`:**
  - `exporters/board_config.py`, `exporters/export_sessions.py` and `exporters/derive.py`;
  - `local/collector.py` and `local/tabs.py`;
  - `exporters/refresh.py` (read only, since it is blocked) and `site/index.html` (read only, since it
    is blocked).
- **Measurements on this machine, 2026-09-19:**
  - the real transcripts under `~/.claude/projects`, scanned by a throwaway script in the scratchpad that
    was not committed;
  - `git -C C:/Users/jdk/dispatch-board worktree list`;
  - the folder `C:/Users/jdk/dispatch-board-worktrees/`.
- **Format precedent:** `docs/backlog/specs/pbi-010-derived-status.md`.

**Four rules govern the design.**

1. **One derivation.** The link decision is a pure function in `exporters/derive.py`. The session exporter
   and the collector call it identically (parent `:87`; FR-87). Neither re-implements it.
2. **Evidence is parsed once, decided every time.** The edited paths are collected during the existing
   parse and cached with it. The link is decided when documents are written, from the cached evidence and
   the current config. So a config change applies without re-reading a transcript (FR-40's pattern), and
   nothing re-scans a large transcript.
3. **The config list is authoritative.** An auto-link only ever fills a gap the config leaves. It never
   moves a listed session, and it never widens FR-38's fatal rule.
4. **No new process, no new store document, no new persistent state.** The rule reads no git, so the
   collector gains no subprocess. No collection is added. Nothing is kept beyond the caches that exist
   today.

---

## 2. The evidence as it actually is

### 2.1 Edit paths are already extracted, for main and subagent transcripts

- `derive.EDIT_TOOLS` names the tools that write a file and the input key holding the path: `Edit`,
  `Write` and `MultiEdit` use `file_path`, and `NotebookEdit` uses `notebook_path`
  (`exporters/derive.py:22-23`).
- `derive.response()` records every such call's `(tool_use id, path)` on its response
  (`exporters/derive.py:325-333`).
- **Subagents.** `add_agent` notes failed calls (`:370`, `failed_edit` at `:336-344`), and `agent_summary`
  drops them (`:377-387`). So a run row's `files` holds only **successful** edits (`edited()` at
  `:650-658`, set on the row at `:677`).
- **Main transcript.** `add_record` calls `response()` too (`:585`), so the main transcript's edit paths are
  **already in `state['by']`**. But `new_session` has no `failed` set (`:520-524`), and `session_result`
  publishes no file list (`:697-714`). A refused edit in the main transcript is therefore not yet told
  apart from a real one, and main-transcript edits are not yet in the cached result.
- **Reads are not recorded.** `Read`, `Grep`, `Glob`, `Bash` and `PowerShell` are not in `EDIT_TOOLS`, and
  their inputs are never read for paths. L-4 therefore holds by construction, once the evidence is limited
  to `EDIT_TOOLS`.

### 2.2 Paths as the transcripts hold them

Scan of every session exported on 2026-09-19 (the 7-day window plus listed sessions): 2,736 successful edit
paths.

| Form | Count |
|---|---|
| Backslashes, drive `C:` (`C:\Users\jdk\...`) | 2,502 |
| Forward slashes, drive `C:` (`C:/Users/jdk/...`) | 234 |
| Relative, `~/`, drive-relative or POSIX `/c/...` | 0 |

- **Slash direction really is mixed**, so the rule must normalise it.
- **Case must be ignored.** Windows paths are case-insensitive. The board's existing repository test
  already compares normalised, lower-cased paths with a `/` boundary (`publishable_files`,
  `exporters/derive.py:938-944`), and this spec reuses that test.
- **The `/` boundary matters on this machine.** Sibling folders share prefixes: `C:/Users/jdk/import-duty`
  and `C:/Users/jdk/import-duty-work` were both edited in the window, and
  `C:/Users/jdk/dispatch-board-worktrees` begins with `C:/Users/jdk/dispatch-board`.

### 2.3 Worktrees on this machine

- **The folder.** dispatch-board's worktrees live in the sibling folder
  `C:/Users/jdk/dispatch-board-worktrees/<name>`. Each live worktree's `.git` file points at
  `C:/Users/jdk/dispatch-board/.git/worktrees/<name>`.
- **`git worktree list` (2026-09-19)** shows the main checkout plus five worktrees: `chore-cells-wrap`,
  `chore-pr-steward`, `PBI-007`, `PBI-012` and `PBI-029`.
- **The folder holds more than git knows.** It also holds `PBI-005`, `PBI-009` and `PBI-028`, with no
  `.git` file: git has pruned them.
- **Most edits went to worktrees git no longer lists.** In the window, sessions edited files in **26**
  distinct dispatch-board worktrees. 808 successful edits went to worktree paths. Only **101** of them are
  in a worktree `git worktree list` still shows; **707** are in worktrees since removed (PBI-001 to PBI-006,
  PBI-008, PBI-009, PBI-011, PBI-013, PBI-014 and others).
- **A second naming convention exists.** The backlog-delivery plugin's own helper creates sibling worktrees
  named `<repo>-pbi-<id>-<slug>`
  (`~/.claude/plugins/cache/agent-catalog/backlog-delivery/0.2.0/scripts/create-pbi-worktree.py:233`).
  This repo does not use it (`backlog-delivery.config:18`, `worktree_script` unset).
- platform-catalogue has no worktree and no remote.

### 2.4 What the proposed rule does to today's data

This is a throwaway check, not a test. It counts distinct successfully edited files per project, main and
subagent transcripts together, using §3's rule with the default worktree root, over every session exported
on 2026-09-19.

| Session | Listed today | Last written | Transcript | Distinct files by project | Rule's link if unlisted |
|---|---|---|---|---|---|
| `7e0c4f3c` | dispatch-board | 2026-09-19 | 28.5 MB | dispatch-board 180 | dispatch-board |
| `9562c312` | dispatch-board | 2026-09-11 | 21.4 MB | dispatch-board 94 | none: outside the 7-day window, so not exported (§3.5) |
| `7f71729a` | platform-catalogue | 2026-09-18 | 10.2 MB | platform-catalogue 80, **dispatch-board 5** | platform-catalogue |
| 7 other sessions | none | 2026-09-12 to 2026-09-19 | up to 56.2 MB | none (their edits are in other folders: UP4eva, PSDRoster, AppData and others) | none |

What this establishes:

- **The rule reproduces the hand-kept list** for every listed session inside the window, including the one
  session that edits two projects (`7f71729a`, majority platform-catalogue). No unlisted session in today's
  window would be linked. So the first refresh after merge changes nothing on the live board today; the
  value shows with the next build session nobody lists.
- **L-3 is real data.** `7f71729a` is listed under platform-catalogue and edited 5 dispatch-board files.
- **Stickiness is real data.** `9562c312` is dispatch-board's first build session. Were it only auto-linked,
  it would leave the board 7 days after its last activity (§3.5, row Q-1).

---

## 3. Decisions

### 3.1 The evidence rule

A session's **evidence** is the set of distinct files it successfully edited. Two sources count:

- **The main transcript:** its `EDIT_TOOLS` calls whose `tool_result` did not come back `is_error`. That
  rule is the same as for subagents, and needs the main-state `failed` set of §4.1.
- **Every subagent transcript of the session:** the union of its run rows' `files`, which already hold
  only successful edits (§2.1). A carried row (a skipped agent) counts with the files it carried.

Choices within the rule:

- **Which tools.** Exactly `derive.EDIT_TOOLS`: `Edit`, `Write`, `NotebookEdit`, and `MultiEdit`, which
  also writes a file. The PBI names the first three; including `MultiEdit` keeps one definition of "an edit"
  across the board. Row A-1.
- **Not evidence.** `Read`, `Grep`, `Glob`, `Bash`, `PowerShell`, and any other tool, even when its input
  or output names a file in the repository (L-4). A file written by a shell command is not evidence.
- **Why subagents count.** Build sessions run from `C:\Users\jdk` and hand most edits to subagents. In
  `7e0c4f3c`, 167 main-transcript edit calls against 804 subagent edit calls, counting every folder (§2.4
  scan). The runs are the session's
  runs, and they are published under its project already. Row A-2.
- **Distinct files.** A file edited 40 times is one file. Files are counted on the **lower-cased** normal form
  of §3.2, so `C:\X\a.py` and `c:/x/A.py` are one file (revision 2, SG30-5).
- **Worktree copies count separately.** A file edited in the repository and in a worktree copy of it counts
  as two files. Both count for the same project, so a link is unaffected. Only the size of a §3.3 majority
  grows, so the count is "distinct paths", not "distinct repository files".
- **Threshold: one file.** A single successful edit under a project links an unlisted session to it (L-1's
  wording). Row A-3.
- **Placeable paths only.** Only a path that is absolute after normalisation (`derive.ABSOLUTE`,
  `exporters/derive.py:24`) can be evidence. These are never evidence:
  - a relative path;
  - a path climbing out with `..` that stays relative;
  - a home-relative (`~/…`) or drive-relative (`C:foo`) path (`derive.UNPLACEABLE`, `:27`).
- **Excluded sessions** (`sessions.exclude`) are never read, so they are never linked
  (`exporters/export_sessions.py:233`; `local/collector.py:277`).

### 3.2 Mapping a file to a project: path prefixes, not `git worktree list`

**Normal form.** A path, and each root it is tested against, is normalised by the same steps as
`publishable_files` (`exporters/derive.py:938-944`):

1. `\` becomes `/`;
2. `posixpath.normpath` is applied;
3. trailing `/` is stripped;
4. the result is compared lower-cased on **path-component boundaries**. **The formula is normative
   (revision 3, SG30-r2-4):** `(path + "/").lower().startswith(root.lower() + "/")`.
   - It is true for `root/x`, and false for `root-other/x` and `root-worktrees-old/x`.
   - It is also true for `root` itself. That is harmless, because an edit input naming a folder fails and
     so is never evidence.

**What is shared (revision 3, SG30-r2-3, option a).** Only steps 1 to 4, the normalisation and the boundary
test, live in one helper that `publishable_files` and the link rule both use. The two can therefore never
disagree about "inside the repository". The no-root rule below is **not** in that helper: it lives only in
the link rule's root builder, so `publishable_files`' behaviour is unchanged for every `repoPath`.

**A root that matches everything is never a root (revision 2, SG30-3; revision 3, SG30-r2-3, SG30-r2-4).**
The link rule's root builder treats a root as **no root**, whatever its source, when its normal form:

- is empty, `/`, or a bare drive (`X:`);
- is a bare UNC server or share (`//host` or `//host/share`);
- ends in whitespace;
- or is not absolute (`derive.ABSOLUTE`).

Examples: `""`, `"/"`, `"\\"`, `"C:/"`, `"C:\"`, `"\\server\share"`, `"//server"`, `"C:/x "`, `"."`,
`" "`, `"~/x"` and `"relative/x"`. This is the only defence for a degenerate `repoPath`. `worktreeRoots` is
also refused outright at config time (below). An extended-length root such as `\\?\C:\`, which normalises to
`//?/C:`, is accepted. It is harmless: it matches only extended-length paths (row A-10).

**String-only by design (revision 2, SG30-4).** The rule compares strings, so it stays pure and
deterministic with no filesystem access.

- Symlinks, junctions, `subst` drives and 8.3 short names are **not** resolved. A repository reached through
  one of them does not link unless its root is also configured in that form.
- The extended-length prefix `\\?\C:\…`, which normalises to `//?/C:/…`, is not stripped. So it does not
  match a `C:/` root (row A-10).

**A project's roots.**

- **`repoPath`, normalised.**
  - **Type (revision 2, SG30-2; revision 3, SG30-r2-5).** In the `projects` shape, `board_config.projects()`
    raises `ValueError`, naming the project and `repoPath`, for a `repoPath` that is present and neither a
    string nor `null`. That is exit 2 in the exporters and a Refusal in the collector, rather than a
    `TypeError` traceback.
    - An absent or `null` `repoPath` is still read as `''`, as today (`exporters/board_config.py:130`).
      `false`, numbers and lists are refused.
    - **The legacy shape is not covered.** There, a non-string `build.repoPath` still fails inside
      `legacy()` (`:98`, `repo.replace`) with the `AttributeError` it raises today, before the loop's check
      runs. The exit-2 claim is limited to the `projects` shape: `legacy()` is not edited (SG30-11), and
      the legacy shape is read only for old configs.
  - An empty `repoPath` gives the project no `repoPath` root and no default worktree root. That is the
    legacy default `''` (`exporters/board_config.py:95`, `:130`).
  - **An explicit `worktreeRoots` still applies (revision 3, SG30-r2-6).** With `repoPath: ""` and
    `worktreeRoots: ["C:/wt"]`, edits under `C:/wt` link. The two rules govern different roots: the
    `repoPath` root, and the default, derive from `repoPath`, while an explicit list stands on its own
    validation.
  - A `repoPath` that is a filesystem or drive root, or not absolute, gives no root either, by the helper's
    rule above. It is **not** refused: `repoPath` has other readers (`exporters/export_board.py:244`), and
    tightening its validation is outside this PBI. Such a project simply links nothing (row A-10).
- **`worktreeRoots`, a new optional per-project key.** It is a list of folder paths. A file is under a
  worktree root by the same component-boundary test as `repoPath` (revision 2, SG30-12).
  - A file directly in the root and a file in any folder below it both count: `<root>/f` and
    `<root>/<name>/f`.
  - `<root>-old/<name>/f` does not count.
  - **Default, computed from the normal form (revision 2, SG30-2).** When `repoPath` gives a root `R`, the
    default is `[R + "-worktrees"]`, else `[]`. `R` is `repoPath`'s normal form, trailing separators
    stripped. So `C:/Users/jdk/dispatch-board`, `C:/Users/jdk/dispatch-board/` and
    `C:\Users\jdk\dispatch-board\` all default to `C:/Users/jdk/dispatch-board-worktrees`, and never to
    `…/dispatch-board/-worktrees`.
  - **An explicit list replaces the default.** `[]` turns worktree mapping off for that project.
  - **Validated strictly (revision 2, SG30-3).** `board_config.projects()` raises `ValueError`, naming the
    project, `worktreeRoots` and the bad entry, when the value is not a list, or when any entry:
    - is not a string;
    - is not absolute after normalisation (`derive.ABSOLUTE`): relative (`"relative/x"`, `"."`, `" "`) or
      home-relative (`"~/x"`). **`~` is refused, not expanded**, so a value never silently fails to match;
    - is a filesystem or drive root after normalisation: `""`, `"/"`, `"\\"`, `"C:/"`, `"C:\"` or `"C:"`;
    - is a bare UNC server or share: `"\\server\share"`, `"//server"` or `"//server/share"` (revision 3,
      SG30-r2-4);
    - ends in whitespace, such as `"C:/x "`. Windows drops a trailing space from a real path, so such an
      entry could never match (revision 3, SG30-r2-4).
  - **The loop sets it once (revision 2, SG30-11).** The key is set in `projects()`'s one loop
    (`exporters/board_config.py:113-132`). The legacy shape flows through that loop too, so `legacy()` is
    not edited.
  - **A bad value stops every reader (revision 2, SG30-10).** `board_config.projects()` is shared, so each
    reader stops with nothing written:
    - `exporters/export_sessions.py` exits 2 (`:201-205`);
    - `exporters/export_board.py` exits 2 (`:243`, `:266-268`), so the spec tabs stop too;
    - the collector refuses the pass (`local/collector.py:582-585`).

    That matches how an unusable `id` or `statusDoc` behaves today. `export_board.py`'s half is untested in
    this PBI, because `tests/test_export_board.py` is outside `allowed_areas`.
  - **Not published.** It never appears on any store document.
  - **`board.config.json` is not edited**, since it is outside the allowed areas; the default applies
    unchanged.

**Nested roots.** Each file belongs to the project owning the **longest** root it is under, whether a
`repoPath` or a worktree root. A project nested inside another project's folder therefore takes its own
files. Two projects declaring the same root cannot both take a file: the tie goes to config order.

**Why a prefix rule and not `git worktree list`.**

| Option | Why not |
|---|---|
| `git worktree list --porcelain` run from `repoPath` each export | **It forgets history.** 707 of the window's 808 worktree edits are in worktrees git no longer lists (§2.3). A session's link would vanish when its worktree is cleaned up after merge, which is exactly when the work is done. The decision would also depend on the machine's git state at the moment of export, not on the transcript, so a re-run could relink sessions with no transcript change. **It adds a subprocess** to `export_sessions.py` and the collector's pass: another console-window risk (`exporters/export_board.py:45-51`), and another launch site for `local/tests/test_deploy_inspection.py` to account for (`:41-42`, `:68`) |
| Read each edited path's worktree `.git` file (`gitdir: <repo>/.git/worktrees/<name>`) | The same history problem: `PBI-005`, `PBI-009` and `PBI-028` still exist as folders with no `.git` file, and removed worktrees have no folder at all (§2.3). It also means file reads outside `projectsRoot` on every export |
| A fixed `<repoPath>-worktrees` convention, with no config key | Matches this machine today, but the plugin's own helper uses `<repo>-pbi-<id>-<slug>` siblings (§2.3). Without a key, a change of convention would need a code change. The key costs one validation, and its default is exactly the fixed convention (row A-4) |
| Path prefix with a configurable root list (**chosen**) | Deterministic from the transcript and the config alone. It survives worktree removal. It needs no process. The exporter and the collector give the same answer on any machine state |

**Known limit.** A worktree created outside every root (for example with the plugin's helper while the key
is left at its default) does not link. The session then stays in "Other sessions" unless it also edited
`repoPath` itself or is listed. Adding the folder to `worktreeRoots` fixes it without a code change.

### 3.3 One session, two projects

When an unlisted session's evidence falls under more than one project:

1. **Most distinct files wins.**
2. **A tie goes to config order:** the project listed first in `projects`.

This rule is deterministic and needs no timestamps; subagent `files` carry none per file. On today's data
it agrees with the hand-kept list (`7f71729a`: 80 against 5, §2.4).

**Stability.** Transcripts are append-only, so evidence only accumulates, with one exception (revision 3,
SG30-r2-7). An edit counts from its `tool_use` until an `is_error` result marks it failed. So a pass that
sees the call before its error result counts the edit for that one pass. With a threshold of one file, a
session whose only repository edit was refused can show as linked for a single collector pass or export.

- It is transient and self-correcting.
- It is consistent with how run `files` behave today.

A link can move from one project to another only if a later majority overtakes the earlier one. It then
moves with all of the session's runs, usage and findings, and the session document's `linkedBy` stays
`edits`. Row A-5.

**Rejected alternatives:**

- "First project edited wins" is stable but mislabels a session that touched one file of project A before
  spending the day on project B.
- "Ambiguous means unlinked" leaves the session in "Other sessions", which is the problem this PBI exists to
  fix. It would also unlink `7f71729a`-like sessions were they not listed.

### 3.4 Precedence

In order, first match wins:

1. **Excluded** (`sessions.exclude`): never read, never exported. Unchanged.
2. **Listed** in some project's `sessions`: that project, and the first such project when a session is
   listed twice (`exporters/export_sessions.py:95`). Its edits are ignored (L-3).
3. **Auto-linked**: the project chosen by §3.3.
4. **Otherwise** `project: null`, shown under "Other sessions".

### 3.5 Stickiness and the window: an auto-linked session is an unlisted session with a project

**Decision (row Q-1, owner-confirmed 2026-09-19):** an auto-link grants **no** exemption from the session
window. The owner answered "No, 7-day window (Recommended)". So Q-1 is resolved, and it no longer stands in
the way of a self-merge (revision 3, SG30-r2-8; AL-23).

- Only **listed** sessions are exported whatever their age (FR-137, `exporters/export_sessions.py:100`,
  `:231`, `:268`).
- An auto-linked session is exported while its last activity is inside `sessions.days`, exactly like any
  unlisted session. It leaves the board, and with it its project's session list, runs, usage and findings,
  when it ages out.
- **Within the window the link is stable.** It is recomputed on every run from the whole transcript's
  evidence. That evidence only grows, except for an edit whose error result has not yet been written
  (§3.3, "Stability").
- **To keep a session with its project for good, the owner lists it**, as today.

**Why not sticky.** Keeping a link past the window needs the link decision to exist before the session is
read, because both exporters skip an out-of-window transcript before parsing it
(`exporters/export_sessions.py:231`; `local/collector.py:270-273`). The options all fail:

- **Read the cached parse.** Both caches are disposable: `out/.cache/sessions.json` keeps only sessions
  seen this run (`exporters/export_sessions.py:227`, `:271`), and the collector drops an aged session's
  state (`local/collector.py:270-273`, `:286`). A sticky link would silently vanish on a cache reset or a
  `PARSER_VERSION` bump. The two sides would also keep it for different lengths of time, breaking FR-87.
- **Parse every transcript ever written.** Some are 56 MB (§2.4), which breaks NFR-3's warm 0.2 s budget
  on every cold cache.
- **A persisted link table** (a new `out/` state file and a collector table). It is new persistent state,
  needs a schema change (`local/schema.py` is outside the allowed areas), and needs its own pruning and
  guard rules. The owner declined it (Q-1, 2026-09-19).

**What the default costs.** An auto-linked build session's runs stop counting toward its project 7 days
after its last activity. That includes PBI-010's derived work-item states, which read the project's linked
sessions. It is no worse than today, where such a session is in "Other sessions" for the same 7 days and
then gone. It is worse than listing it.

### 3.6 Age pruning in the collector (FR-185)

- An auto-linked session is pruned by age exactly as an unlisted one: its records are deleted once its last
  activity is older than the window, and **that deletion bypasses the mass-delete guard** (FR-185, A-47).
- **No collector change is needed for this.** Every window and pruning test reads `st['build']`, which
  stays the config-only set: `local/collector.py:270`, `:420`, `:464` and `:466`.
- Listed sessions keep their exemption (AC-121).
- A vanished transcript of an auto-linked session whose last activity is inside the window is a deletion
  "other than by age". It goes through FR-184's guard, exactly as for an unlisted session today
  (`local/collector.py:461-510`).

### 3.7 FR-38 and a missing transcript

- **FR-38 stays listed-only.** `st['build']`, the set checked for a missing transcript
  (`exporters/export_sessions.py:100`, `:214-219`; `local/collector.py:588-592`), stays the set of
  **listed** sessions and is never widened by an auto-link.
- **An auto-link cannot outlive its transcript.** It is decided only from a transcript that was found and
  parsed this run. If the transcript goes, the session is simply not exported, and nothing remains to link
  (L-5).
- **The same holds for the collector.** The stored records of a vanished auto-linked session are deleted
  under §3.6's rules, never refused as a missing linked transcript.

### 3.8 `linkedBy` on the session document

**Decision: record it.** Every session document whose `project` is non-null gains
`linkedBy: "config" | "edits"`. A session with `project: null` has no `linkedBy` key.

- **Why.** It tells the owner which sessions are held only by evidence, and so will age out (§3.5): those
  are the ones to list to keep. It makes L-3 and §3.3 directly assertable. And a later page PBI can show it
  without an exporter change.
- **Where not.** Runs carry their session's `project` already, and gain nothing. The project document gains
  nothing.
- **The page is not changed** (`site/**` is blocked), so `linkedBy` is data only in this PBI.
- **Record shapes.** The local `session` shape does not list `linkedBy`, and "Fields a SPEC does not list
  are allowed, and kept" (`local/records.py:23`). `local/records*` is outside the allowed areas and needs no
  change. Listing it as an optional enum is a follow-up (row A-9).

### 3.9 FR-3's `build` flag

- **`build` stays config-only.** `legacy_build` is built from the listed sessions
  (`exporters/export_sessions.py:103`) and is not widened.
- **Why.** Only copies of the page from before projects read `build`, and FR-3's own note says so
  (`docs/prd/dispatch-board.md:242`). Changing what an obsolete reader sees buys nothing.
- **Consequence.** An auto-linked platform-catalogue session has `build: false`. Row A-8.

---

## 4. Where it is computed

### 4.1 `exporters/derive.py`

1. **Main-transcript failures.**
   - `new_session` gains `'failed': set()`.
   - `add_record` calls `failed_edit(state['failed'], o)` (`:336-344`), as `add_agent` does (`:370`).
2. **Cached evidence.** `session_result` puts `edits` in the result's `doc`: the main transcript's
   successful edit paths, as written, first edit first, each once. It uses `edited()`'s rule over the
   responses' `files`, filtered by `state['failed']`.
   - `edits` is **cache-only**. `session_doc` pops it, exactly as it pops `firstPrompt` (`:720`), so it is
     never published.
   - Subagent evidence is already in `result['rows'][*]['files']`, so nothing else is cached.
3. **One path helper.** It gives the normal form and the boundary test of §3.2. `publishable_files` is
   refactored to use it, with no behaviour change: the no-root rule stays in the link rule's root builder
   (revision 3, SG30-r2-3, option a), so every current `publishable_files` result is unchanged. Its existing
   tests stay green unchanged: `Sessions.test_run_doc_*` (`tests/test_derive.py:303-340`).
4. **The link rule:** a new pure function, `derive.link_sessions(results, projects, listed)`, returning
   `(project_of, linked_by)` as two dicts keyed by every session id in `results`.
   - `projects` is `board_config.projects()`'s output, whose entries now carry `worktreeRoots`.
   - `listed` is `settings()`'s config-only `project_of`.
   - `project_of[sid]` is a project id or `None`. `linked_by[sid]` is `'config'` or `'edits'`, and absent
     when unlinked.
   - The function is pure: no I/O, no clock, no config reading.
   - **A result without `edits` is tolerated (revision 2, SG30-6).** `link_sessions` reads a missing
     `doc['edits']` as `[]`, and `session_doc` pops it with a default (`doc.pop('edits', None)`).
     - **Why it can happen.** When a re-parse raises, the exporter keeps the old cache entry
       (`exporters/export_sessions.py:255-261`). Just after the `PARSER_VERSION` bump, that entry is a
       pre-bump result with no `edits`. The session then links on its subagent evidence alone until it
       parses again.
     - **The collector differs.** It resets such an entry instead (`_session_ok`,
       `local/collector.py:157-161`) and leaves the session out. That divergence between the exporter and
       the collector over an unparseable session exists today and is not widened here.
5. **`session_doc`** reads `st['project_of']` as today (`:726`). It reads the reason as
   **`st.get('linked_by', {})`** to set `linkedBy` (§3.8).
   - Revision 3, SG30-r2-2: `.get` keeps `tests/test_derive.py:356` green unchanged, and any other
     hand-built `st` too. That test's `st` has no `linked_by`, and a plain index would raise `KeyError`.
   - With `.get`, a session whose project comes from a hand-built `st` with no `linked_by` gets no
     `linkedBy` key.
6. **`project_doc`** (`:986-994`) builds its `linked` list from `project_of`, not only `p['sessions']`:
   - first the listed sessions, in config order, exactly as today (`:989`);
   - then the auto-linked sessions (`project_of[sid] == p['id']` and not in `p['sessions']`), **sorted by
     session id**, so the exporter and the collector, which fill `results` in different orders, write the
     same list.
   - `runs`, `running`, `last` and `usage` then cover both.
   - Whatever PBI-010 adds to `project_doc` reads the same `linked` list, so auto-linked sessions feed the
     derived work-item states too.

### 4.2 `exporters/board_config.py`

- In its one loop (`:113-132`), `projects()` validates `repoPath`'s type and adds a validated
  `worktreeRoots` to each project dict (default and validation as in §3.2). The legacy shape's raw dict flows
  through the same loop, so `legacy()` (`:89-100`) is unchanged (revision 2, SG30-11).
- No existing test asserts the project dict by equality: `tests/test_export_board.py:879-887` checks fields
  one by one. So the extra key breaks nothing in that blocked-for-this-PBI test file.

### 4.3 `exporters/export_sessions.py`

- `settings()` is unchanged. Its `project_of` and `build` stay config-only.
- After the results loop (`:228-269`) and before any document is written (`:273`), `main` calls
  `derive.link_sessions(results, st['projects'], st['project_of'])`, then uses
  `st = dict(st, project_of=…, linked_by=…)` for everything after:
  - `run_doc`'s project and `repo_of` lookup (`:280-286`);
  - `session_doc` (`:288`);
  - `project_doc` (`:290-291`);
  - the findings ledger's filter (`:301`), so an auto-linked session's review rounds join that project's
    ledger.
- `PARSER_VERSION` is bumped (§5.1).
- The module docstring (`:6-12`, `:32-44`) is updated to state the rule.

### 4.4 `local/collector.py`

- `assemble()` (`:425-443`) makes the same call, with the same arguments, before its loop (revision 3,
  SG30-r2-1). It then rebinds `st = dict(st, project_of=…, linked_by=…)`, exactly as §4.3 does, so every
  document call in `assemble()` reads the auto-link map:
  - `run_doc`'s project and `repo_of` lookup (`:436-438`);
  - **`derive.session_doc(results[sid], sid, st, …)` (`:440`)**, which would otherwise write the config-only
    `project` and no `linkedBy`;
  - `project_doc` (`:442`).

  AL-2's equivalence test pins this.
- **Nothing else in the collector changes.** Discovery, `judge`, `reasons`, `guard` and the missing-
  transcript check keep reading config-only `st['build']` (§3.6, §3.7).

### 4.5 What is not edited, and why it still works

| File | Why it needs no edit |
|---|---|
| `exporters/refresh.py` (blocked) | A project's status "mine" set is taken from each document's own `project` field (`:171`), so auto-linked sessions and runs move their project's `updatedAt` with no change. No document is added to or removed from a managed collection, so the mass-delete clauses (`:132-159`) are untouched |
| `local/tabs.py` | `project_of(kind, id, doc)` reads the record's `project` (`:156-157`) for the collector's status rule |
| `site/**` (blocked) | The page groups sessions and runs by their `project` (`site/index.html:350-352`, `:362`, `:1364`). "Other sessions" is `unlinked()`, so it shrinks only because fewer sessions have `project: null` (L-6) |
| `local/records*`, `local/schema*` | Unlisted fields are allowed and kept (`local/records.py:23`); `linkedBy` is a string |
| `local/tests/test_deploy_inspection.py` | No process launch is added (§3.2), so its launch inventory (`:41-42`, `:68`) is unchanged and must stay green |
| `board.config.json` | The defaults apply; no key is required |

---

## 5. Caching, FR-40 and performance

### 5.1 `PARSER_VERSION` must be bumped

- **Why.** The cached parse gains `doc['edits']`, and the main-state layout gains `failed`. A result cached
  under the build base's version lacks both. Reused as it is, it would show no main-transcript edits, and
  a refused main edit could not be told apart. PBI-011's round-1 NO-GO is the precedent: a new cached field
  needs a bump (`tests/test_export_sessions.py:1081-1091`).
- **Required:** `PARSER_VERSION` is **greater than the build base's value**. It is 9 at `8bd2621`
  (`exporters/export_sessions.py:60`), and PBI-010 may move it, so no literal is pinned. The signature leads
  with it (`:179`), so every cached session is re-parsed once.
- **Collector.** `_session_ok` rejects a stored entry whose `parser` differs, or whose state key set differs
  from `derive.new_session`'s (`local/collector.py:157-161`). Each in-window session is re-read from byte 0
  once. **`STATE_VERSION` (`:40`) does not need a bump**: the key-set check already covers it.
- **One-time cost.** A single full read of every exported transcript, about 130 MB on 2026-09-19 (§2.4
  sizes). After that, reads are incremental again.

### 5.2 A config change applies without a transcript change (FR-40)

The link is decided when documents are written, from the cached evidence (rule 2). So a change to a
project's `repoPath`, `worktreeRoots` or `sessions`, or to the `projects` order, applies on the next run with
**no re-parse**:

- in the exporter, the cache still hits, because the signature holds no config (`:170-179`);
- in the collector, the stored result is reused (`local/collector.py:323-326`) and `assemble` re-decides.

No config value is added to the signature.

### 5.3 No re-scan of large transcripts

- **The exporter** parses a session only when its signature changes (`exporters/export_sessions.py:245`).
  The edit paths are collected in that same pass by the `response()` call that already runs (§2.1).
- **The collector** reads only appended bytes (FR-86, `read_new` at `local/collector.py:119-134`), feeding
  them into the persisted state. That state already holds the main transcript's responses and their
  `files`, and now also the `failed` set.
- **The link rule** does about 200 distinct paths against at most a handful of roots per session. That is
  microseconds, far inside NFR-3's 0.2 s warm budget (AC-56).
- **Cache growth** is one list of distinct main-transcript edited paths per session; the largest session
  today edited 180 distinct project files across main and subagent transcripts together.

---

## 6. PRD amendments (proposed text; the PRD is not edited by this spec or this PBI)

New ids are the next free numbers at `8bd2621`: FR-193, AC-129 and A-49. If revision 6 of the parent claims
them first, they are renumbered when the PRD is edited.

| Where | Current (abridged) | Proposed |
|---|---|---|
| Glossary, `:54` | "**Linked session**: a session listed in a project's `sessions`. **Unlinked session**: any other exported session." | "**Listed session**: a session listed in a project's `sessions`. **Auto-linked session**: an exported session that no project lists, linked to a project by the files it edited (FR-193). **Linked session**: a listed or auto-linked session. **Unlinked session**: any other exported session." |
| FR-3, `:242` | "…sessions linked to the project whose status document is `meta/status`…" | "…sessions **listed by** the project whose status document is `meta/status`…" (an auto-linked session's `build` is false; §3.9) |
| FR-38, `:289` | "If a linked session's main transcript cannot be found…" | "If a **listed** session's main transcript cannot be found…" |
| FR-40, `:294` | "When a project's `sessions` list, `sessions.showFirstPrompt` or `runs.runningWindowMinutes` changes…" | "When a project's `sessions` list, **`repoPath` or `worktreeRoots`**, `sessions.showFirstPrompt` or `runs.runningWindowMinutes` changes…" |
| FR-137, `:366` | "…shall export every linked session whether or not its last activity lies within the session window." | "…shall export every **listed** session whether or not its last activity lies within the session window. **An auto-linked session is exported only while its last activity lies within the window.**" |
| FR-138, `:367` | "…to the id of the project that lists the session, or to null when no project lists it." | "…to the id of the project that lists the session; when no project lists it, to the id of the project it is auto-linked to (FR-193); otherwise to null. **A session document with a project also carries `linkedBy`, `config` or `edits`.**" |
| FR-139, `:368` | "…the exported linked `sessions`…" | "…the exported linked `sessions` (**listed sessions in config order, then auto-linked sessions ordered by session id**)…" |
| FR-185, `:429` | "…only the records of sessions linked to no project whose last activity is older than the session window…" | "…only the records of sessions **listed by** no project whose last activity is older than the session window **(auto-linked sessions included)**…" |
| AC-90, `:724` | "When a linked session was last active 30 days ago…" | "When a **listed** session was last active 30 days ago…" |
| AC-120, `:760` (revision 2, SG30-8) | "When an unlinked session's last activity is 8 days old, the collector shall delete that session's records…" | "When a session **listed by no project** (unlinked or auto-linked) has a last activity 8 days old, the collector shall delete that session's records…" |
| AC-121, `:761` | "When a linked session's last activity is 30 days old…" | "When a **listed** session's last activity is 30 days old…" |
| A-36, `:803` (revision 2, SG30-8) | "The local database keeps the last 7 days plus linked sessions, pruned by age only (FR-185)…" | "The local database keeps the last 7 days plus **listed** sessions, pruned by age only (FR-185)…" |
| **Parent spec** row 12 (revision 5 `docs/backlog/specs/dispatch-board.md:296`; revision 2, SG30-8) | "The local database keeps the last 7 days plus linked sessions, pruned by age only." | "The local database keeps the last 7 days plus **listed** sessions, pruned by age only." A parent-spec text amendment, applied by the planner at the parent's next revision, not by this PBI |
| **New FR-193** | — | "Where an exported session is listed by no project, the session exporter and the collector shall link it to the project under whose `repoPath` or `worktreeRoots` it successfully edited (Edit, Write, MultiEdit or NotebookEdit, in its main or subagent transcripts) the most distinct files, ties going to the project listed first; a session that edited no such file stays unlinked. Reading, searching or shell commands are not edits." |
| **New AC-129** | — | "When a session in the window that no project lists has successfully edited one file under a project's `repoPath`, the session exporter shall set its `project` to that project's id and `linkedBy` to `edits`, and the project document's `sessions` shall include it." (FR-193, FR-138) |
| **New A-49** | — | "**Auto-linked sessions are not sticky.** Default: an auto-link grants no exemption from the session window or from age pruning; to keep a session, list it. Impact if wrong: auto-linked build sessions' runs leave their project's figures and derived states 7 days after their last activity." (PBI-030 spec row Q-1) |

---

## 7. Acceptance criteria

Each criterion names the PBI criterion it proves, and names both sides wherever both the exporter and the
collector are concerned. Unless stated otherwise, "exports" means `export_sessions.main` on a synthetic tree.

| # | Maps to | Criterion |
|---|---|---|
| **AL-1** | L-1 | When a session in the window that no project lists has one successful `Edit` of a file under project `p`'s `repoPath`, the exporter writes its session document with `project: "p"` and `linkedBy: "edits"`. Each of its run documents has `project: "p"`, and `projects/p.sessions` contains it after every listed session. The same holds with `Write`, `MultiEdit` or `NotebookEdit` as the only edit (one sub-case each). Its run documents' `files` publish an edit inside `repoPath` **relative to `repoPath`**, where before linking it was `…/<name>` (revision 2, SG30-14) |
| **AL-2** | L-1 | On the fixture of AL-1, one collector pass writes session, run and project records equal to the exporter's documents (the `test_one_pass_equals_the_exporter` style, `local/tests/test_collector_equivalence.py:84`) |
| **AL-3** | L-1 | The edit links whether its path uses `\`, `/` or both, and whatever the case of the drive and folders relative to `repoPath`. A path under `<repoPath>-other/` does **not** link to `p` (the component boundary) |
| **AL-4** | L-1 | A session whose only edit is inside a subagent transcript links (AL-1's outcome) |
| **AL-5** | L-2 | A session whose edits are all under `<repoPath>-worktrees/<any>/…` links to `p`, with no `worktreeRoots` key and no git repository on disk. With `worktreeRoots: ["<other>"]`, an edit under `<other>/<x>/…` links and an edit under `<repoPath>-worktrees/…` does not. With `worktreeRoots: []`, neither links. **Revision 2 (SG30-12):** a file directly in `<repoPath>-worktrees/` links, and an edit under `<repoPath>-worktrees-old/x/f` does not. **Revision 2 (SG30-2):** with `repoPath` written with a trailing `/`, and again with a trailing `\`, an edit under `<repo>-worktrees/<x>/f` links. **Revision 3 (SG30-r2-6):** with `repoPath: ""` and `worktreeRoots: ["C:/wt"]`, an edit under `C:/wt/x/f` links |
| **AL-6** | L-2 | No process is launched by the link rule. `local/tests/test_deploy_inspection.py` passes unchanged, and AL-5's exporter and `derive` tests pass with `subprocess.run` patched to fail the test if it is called. The patch is limited to those tests: a collector pass runs git through `tabs.build` (`local/collector.py:597`), so no collector test patches it (revision 2, SG30-7) |
| **AL-7** | L-3 | A session listed under `a` that edited only `b`'s files has `project: "a"` and `linkedBy: "config"`, in the exporter and the collector. It is in `projects/a.sessions` and not in `projects/b.sessions` |
| **AL-8** | L-1 | An unlisted session with 3 distinct files under `b` and 2 under `a` links to `b`; with 2 and 2 it links to whichever of `a` and `b` is first in `projects`. With `b.repoPath` nested inside `a.repoPath`, an edit under `b.repoPath` counts for `b` only. Editing one file 5 times counts once, and so do `C:\X\a.py` and `c:/x/A.py` (one file, revision 2, SG30-5) |
| **AL-9** | L-4 | A session whose only tool calls on files under `repoPath` are `Read`, `Grep`, `Glob`, `Bash` or `PowerShell` (including a Bash command whose text names a repo file, and a `Read` result quoting a path) has `project: null`, no `linkedBy`, and is not in any project's `sessions` |
| **AL-10** | L-4 | An `Edit` whose `tool_result` has `is_error: true` is not evidence, in the main transcript and in a subagent transcript. A session whose only edit failed has `project: null` |
| **AL-11** | L-1, L-4 | None of these links: a relative path, a `~/…` path, a drive-relative path (`C:foo`), a path whose `..` resolves outside every root, or any project whose `repoPath` is `""` |
| **AL-12** | L-5 | Exporter: a session auto-linked in run 1 whose transcript is deleted before run 2 makes run 2 exit 0. Its session and run documents are not written, and `projects/p.sessions` no longer lists it. `Projects.test_linked_session_without_a_transcript_fails` (`tests/test_export_sessions.py:978`) still passes: a **listed** session's missing transcript is exit 2 |
| **AL-13** | L-5 | Collector: the same sequence commits, and is not a Refusal naming a missing transcript. Its records are deleted by the rules for an unlisted session (guarded as "other" when inside the window). **Fixture (revision 2, SG30-7):** at least two other stored sessions with runs, so the one deletion stays within FR-184's half. A second case with no other sessions asserts that any Refusal names the mass-delete guard, never a missing transcript |
| **AL-14** | §3.5, §3.6 | An auto-linking session last active 8 days ago (window 7) is not exported by the exporter. A collector that stored its records while it was in the window deletes them as an **age** deletion: the pass commits even when that deletion is more than half of the stored runs and sessions (AC-120 extended). A **listed** session last active 30 days ago keeps AC-90 and AC-121 (`tests/test_export_sessions.py:983`; `local/tests/test_collector.py:536`) |
| **AL-15** | FR-40 | After a first export, a change to `p.repoPath`, to `p.worktreeRoots`, or adding the session to `a.sessions` changes the session's `project` and `linkedBy` on the next run **with no transcript change**. The exporter reports `0 re-read`, and the collector re-derives no session (`rederived == 0`) |
| **AL-16** | §5.1 | `PARSER_VERSION` is greater than the build base's value. A cache entry signed with the base version is re-parsed, and its session then carries main-transcript evidence. A collector entry stored under the base version is read again from 0 once |
| **AL-17** | §5.3 | Collector: after a first pass, appending one successful `Edit` of a file under `repoPath` to an unlisted session's main transcript links it on the next pass. That pass's `bytes` equals the appended byte count, not the file size |
| **AL-18** | §3.2 | Each of these makes the session exporter exit 2 with an error naming the project and the key, writing nothing, and makes a collector pass a Refusal (revision 2, SG30-2, SG30-3): `worktreeRoots` as `"x"`, `null`, `[1]` or `[""]`; `worktreeRoots` holding `"/"`, `"\\"`, `"C:/"`, `"C:\"`, `"C:"`, `"relative/x"`, `"."`, `" "` or `"~/x"`; and, in the `projects` shape, a `repoPath` that is present and neither a string nor `null` (`5`, `false`). **Revision 3 (SG30-r2-4, SG30-r2-5)** adds three refused `worktreeRoots` entries: `"\\server\share"`, `"//server"` and `"C:/x "`. It also adds two accepted values: `repoPath: null` exports as `repoPath: ""` and links nothing; `repoPath` of `"C:/"` or `"\\server\share"` is accepted and links nothing (row A-10). The legacy shape's non-string `build.repoPath` is out of this criterion |
| **AL-19** | §3.9 | An unlisted session auto-linked to the `meta/status` project has `build: false` |
| **AL-20** | §4.3 | An auto-linked session's finished code-review round naming `PBI-001` appears in `projectTabs/p.findings` |
| **AL-21** | privacy | No published session document has an `edits` key, and no published document has a `worktreeRoots` key |
| **AL-22** | L-6 | `git diff <base>...HEAD --stat -- site/ exporters/refresh.py local/server.py` is empty, and `node tests/page.test.mjs` passes unchanged. In a fixture with one listed session, one auto-linked session and one unlisted session that edited nothing under a root, only the last has `project: null`, which is what `unlinked()` shows as "Other sessions" |
| **AL-23** | close-out | The three configured suites are green on the head commit, with numbers quoted: `python -m unittest discover -s tests`, `node tests/page.test.mjs`, `python -m unittest discover -s local/tests`. The accounted code-review gate has passed. **Merge breaker (revision 2, SG30-1): met.** The owner answered Q-1 on 2026-09-19: "No, 7-day window (Recommended)". Nothing in this spec now stands in the way of a self-merge on GO (revision 3, SG30-r2-8) |
| **AL-24** | L-2 (revision 2, SG30-14) | Close-out evidence for L-2 records the reading used: "a worktree of the project's repository" means a worktree under one of the project's `worktreeRoots` (default `<repoPath>-worktrees`). A worktree created elsewhere does not link (§3.2 "Known limit") |
| **AL-25** | §4.1 (revision 2, SG30-6) | A cache entry whose result has no `doc['edits']` (a pre-bump result kept after a failed re-parse) exports without error. Its session document has no `edits` key, and its link is decided from its subagent `files` alone |

**Verification tier:** 4. `PARSER_VERSION` is a pinned cache contract, and `derive` is the shared vocabulary
both writers import. The full canonical run, all three suites, is required, plus AL-16's re-parse check.

---

## 8. Test plan

Every test builds synthetic transcripts in a temporary directory and passes its own config, as the suites do
today. Nothing reads `board.config.json`, the real `~/.claude` or `out/`. The build is TDD, per D-9: each AL
is written red first.

| File (allowed area) | Class (new or extended) | Covers |
|---|---|---|
| `tests/test_derive.py` | `LinkSessions` (new): pure tests of `link_sessions` and the path helper, with no files at all | AL-3, AL-8, AL-11. Revision 2 adds: a `repoPath` with a trailing `/`, and one with a trailing `\`, both map `<repo>-worktrees/<x>/f` (SG30-2); the worktree-root boundary, both `-worktrees-old` and a file directly in the root (SG30-12); a root normalising to `''`, `/` or `X:` is no root (SG30-3); case-and-slash variants count as one file (SG30-5); a result with no `edits` (SG30-6). Revision 3 adds: UNC server and share roots, and roots ending in whitespace, are no root (SG30-r2-4); `repoPath: ""` with an explicit `worktreeRoots` links under it (SG30-r2-6); a pending-then-failed edit links on the first read and unlinks on the second (SG30-r2-7); `session_doc` with an `st` that has no `linked_by` (SG30-r2-2). Also: listed wins (AL-7's rule); threshold 1; tie to config order; nested roots, longest wins; the empty `repoPath`; default and explicit `worktreeRoots` (AL-5's rule); determinism (same result for `results` in any insertion order) |
| `tests/test_derive.py` | `Sessions.test_run_doc_*` (existing, `:303-340`; revision 3, SG30-r2-3) and `Sessions.test_session_doc_keeps_the_prompt_out_unless_asked` (existing, `:356`) | unchanged and green: the refactor onto the shared path helper leaves every current `publishable_files` case identical, and `session_doc` tolerates an `st` without `linked_by` |
| `tests/test_derive.py` | `MainFailedEdits` (new) | `add_record` notes a failed main edit, and `session_result`'s `edits` excludes it (AL-10, main half) |
| `tests/test_export_sessions.py` | `AutoLink` (new, on `TreeCase`) | AL-1 (four tools), AL-4, AL-5 end to end, AL-7, AL-9, AL-10 (subagent half), AL-12, AL-14 (exporter half), AL-19, AL-20, AL-21, AL-25 (revision 2), and AL-1's repo-relative `files` (SG30-14) |
| `tests/test_export_sessions.py` | `Cache` (extended, `:648`) | AL-15 (three config changes, `0 re-read`); AL-16 (a cache signed `PARSER_VERSION - 1` is re-parsed, in the style of `:1081-1091`) |
| `tests/test_export_sessions.py` | `ConfigTypes` (extended, `:587`) | AL-18 for the exporter. `tests/test_export_board.py` is not in the allowed areas, so `board_config`'s new validation is tested through the session exporter here |
| `tests/test_export_sessions.py` | `Projects` (existing, `:878`) | unchanged and green: listed-session behaviour, FR-38 and AC-90 are not regressed |
| `local/tests/test_collector_equivalence.py` | `Equivalence` (extended) | AL-2: the fixture gains an auto-linked session, a worktree-only session and a two-project session; one pass equals the exporter, and so does writing a few lines at a time (`:100`) |
| `local/tests/test_collector.py` | `Pruning` (extended, `:529`) | AL-14, collector half: an auto-linked session pruned by age commits past the guard, and a listed one is kept |
| `local/tests/test_collector.py` | `Guard` or a new `AutoLink` class | AL-13; AL-17 (`bytes` equals the appended size); AL-18 (Refusal); AL-16, collector half (`State` style, `:282`) |
| `local/tests/test_conformance.py` (existing) | unchanged | the real exporters' documents with `linkedBy` validate and round-trip |
| `local/tests/test_deploy_inspection.py` (existing) | unchanged | AL-6: no new launch site |
| `tests/page.test.mjs` (blocked; run, not edited) | unchanged | AL-22 |

**Manual check at close-out, recorded in Evidence, not a test.** Run `python exporters/refresh.py` on the
real data and confirm, as §2.4 predicts:

- no session's `project` changes;
- `linkedBy: "config"` appears on the three listed sessions;
- the run prints no re-read beyond the one-time full parse.

---

## 9. Assumptions and open questions

| Row | Question | Status | Answer, or default, impact and rating |
|---|---|---|---|
| **Q-1** | Should an auto-linked session stay with its project after it leaves the 7-day window, and be exempt from age pruning like a listed one? | **RESOLVED** (owner, 2026-09-19) | **No.** The owner's answer, verbatim: "No, 7-day window (Recommended)". An auto-linked session is exported and kept only inside the window, like any unlisted session, and the owner lists a session to keep it (§3.5). **Consequence, accepted by the owner:** auto-linked build sessions' runs, usage, findings and derived work-item states (PBI-010) leave their project 7 days after their last activity. **Merge breaker (revision 2, SG30-1): met** (revision 3, SG30-r2-8) |
| A-1 | Does `MultiEdit` count, although the PBI names only Edit, Write and NotebookEdit? | ASSUMED | Default: yes. `derive.EDIT_TOOLS` (`exporters/derive.py:23`) is the board's one definition of an edit, and `MultiEdit` writes a file. Impact if wrong: low; no `MultiEdit` or `NotebookEdit` call appears in any transcript written since 2026-09-11 (2,297 `Edit` calls do) |
| A-2 | Do subagent edits count as the session's evidence? | ASSUMED | Default: yes (§3.1). Impact if wrong: low; on today's data main-transcript edit calls alone give the same link for all three sessions that edit project files. Counts are successful edit **calls** in the main transcript only, from the §2.4 scan (revision 2, SG30-13): `7e0c4f3c` 142 in dispatch-board; `9562c312` 273 in dispatch-board; `7f71729a` 19 in platform-catalogue against 5 in dispatch-board. §3.1's "167 against 804" is `7e0c4f3c`'s calls in all folders, main against subagent |
| A-3 | Threshold | ASSUMED | Default: one successfully edited file. Impact if wrong: low; a single stray edit links a session that mostly worked elsewhere, which `linkedBy` makes visible and a listing overrides |
| A-4 | Worktree mapping: a configurable prefix list, or a fixed convention | ASSUMED | Default: an optional per-project `worktreeRoots`, defaulting to `[repoPath + "-worktrees"]` (§3.2). Impact if wrong: low; one validated key, not written to `board.config.json` |
| A-5 | Multi-project tie-break | ASSUMED | Default: most distinct files, then config order (§3.3). Impact if wrong: low; one measured case, which agrees with the list |
| A-6 | Order of auto-linked sessions in `projects/<id>.sessions` | ASSUMED | Default: after the listed ones, by session id. Impact if wrong: low; the page does not read this list's order (`site/index.html:350-352`) |
| A-7 | Claude Code's own `EnterWorktree` worktrees | ASSUMED | Default: not verified where Claude Code places them. If they are under `repoPath`, they are covered; otherwise the owner adds the folder to `worktreeRoots`. Impact if wrong: low |
| A-8 | Does `build` (FR-3) follow auto-links? | ASSUMED | Default: no (§3.9). Impact if wrong: low; only pre-projects copies of the page read it |
| A-9 | Should the local `session` shape list `linkedBy`? | ASSUMED | Default: not in this PBI; unlisted fields are allowed and kept (`local/records.py:23`), and `local/records*` is outside the allowed areas. Follow-up: list it as an optional enum. Impact if wrong: low |
| A-10 | POSIX-style (`/c/Users/...`) and extended-length (`\\?\C:\…`, which normalises to `//?/C:/…`) paths, and root or home-folder `repoPath`s | ASSUMED | Revision 2, SG30-3 and SG30-4. Revision 3, SG30-r2-4: a UNC server or share root (`//host`, `//host/share`) or a root ending in whitespace is also no root for linking. A `worktreeRoots` entry of that form is refused. An extended-length root (`//?/C:`) is accepted and matches only extended-length paths. **Default:** `/c/...` and extended-length edit paths are not rewritten, so they do not match a `C:/` root; the prefix is not stripped. A `repoPath` that normalises to a filesystem or drive root gives **no** root, so that project links nothing (§3.2), rather than owning every file on the drive. A home-folder `repoPath` (`C:/Users/jdk`) is a valid root, and owns every file under it that no longer root claims; that is the config author's choice. Impact if wrong: low; 0 of 2,736 measured edit paths used these forms (§2.2) |
| A-11 | Run documents' `files` for worktree edits | ASSUMED | Default: unchanged. A worktree path is still published as `…/<name>` (`exporters/derive.py:924-952`); newly linked sessions' repo edits become repo-relative, as for listed sessions. That widening of what is published is intended, and acceptable because only the owner views the board (PRD D-12). AL-1 asserts it (revision 2, SG30-14). Re-basing worktree files onto the repository is a follow-up. Impact if wrong: low |
| A-12 | `CLAUDE.md` (data model: `project`, the Projects section, the Refresh procedure's "Add a session id… to link it") and the README describe linking as config-only, and neither file is in the allowed areas | ASSUMED | Default: a docs chore at finalize updates `CLAUDE.md` and applies §6's PRD amendments. The `CLAUDE.md` changes: the session row's `project` and `linkedBy`; `worktreeRoots` in Projects, with the caveat that the plugin helper's `<repo>-pbi-<id>-<slug>` worktrees need adding to it; "list it to keep it"; and the privacy bullet on `files`, since an auto-linked session's repo edits are now repo-relative (revision 2, SG30-14). If the owner grants `CLAUDE.md` to this build, the build makes these changes itself instead. This is recorded, not widened silently. Impact if wrong: low, but until done `CLAUDE.md` is stale on one field |
| R-1 | Are main-transcript edit paths already parsed? | RESOLVED | Yes: `response()` records them for the main transcript too (`exporters/derive.py:325-333`, called at `:585`). Only failure tracking is missing (`:520-524`) |
| R-2 | Is FR-38's set config-only? | RESOLVED | Yes: `st['build'] = set(project_of)` from the config lists (`exporters/export_sessions.py:92-100`), checked at `:214-219` and `local/collector.py:588-592` |
| R-3 | Does the page need a change? | RESOLVED | No: it groups by `project` (`site/index.html:350-352`, `:362`, `:1364`) |
| R-4 | Does `refresh.py` need a change? | RESOLVED | No: its status rule reads each document's `project` (`exporters/refresh.py:171`), and no managed collection gains or loses a document |
| R-5 | Is `git worktree list` safe as the mapping? | RESOLVED | No: it lists 5 worktrees, while 26 were edited in the window, and 707 of 808 worktree edits are in removed ones (§2.3, measured 2026-09-19). It would also add a launch site (`local/tests/test_deploy_inspection.py:41-42`, `:68`) |
| R-6 | Does the collector need a pruning change? | RESOLVED | No: pruning and the guard read config-only `st['build']` (`local/collector.py:270`, `:420`, `:464-466`) |
| R-7 | Will the collector re-read stale state after the change? | RESOLVED | Yes, once: `_session_ok` rejects a changed `parser` or state key set (`local/collector.py:157-161`) |
| R-8 | Does the board config test need an edit for the new key? | RESOLVED | No: `tests/test_export_board.py:879-887` checks fields one by one, not by dict equality |

**Needs the owner:** nothing. The owner answered Q-1 on 2026-09-19, asked whether an auto-linked session should stay with its project after it leaves the 7-day session window, verbatim: "No, 7-day window (Recommended)". The default (no stickiness) stands. So Q-1 blocks neither the build nor a self-merge on GO (AL-23; revision
3, SG30-r2-8).

---

## 10. Out of scope

- Any page change: showing `linkedBy`, or an "auto-linked" marker (`site/**` is blocked).
- Sticky links or a persisted link table (declined by the owner, Q-1).
- Re-basing worktree file paths on run documents (A-11).
- Editing `board.config.json`, `CLAUDE.md`, the README or the PRD (A-12; §6 is proposed text only).
- Linking by `cwd`, by Bash commands, or by reads.

---

## 11. Spec-gate record

| Round | Revision reviewed | Reviewer | Verdict | Review |
|---|---|---|---|---|
| 1 | 1 | `pbi-review`, same-vendor subagent, clean context | CHANGES-REQUIRED (Medium 3, Low 11) | `docs/backlog/reviews/PBI-030/spec-review-r1.md` |
| 2 | 2 | `pbi-review`, same-vendor subagent, clean context | **APPROVE-WITH-NOTES** (Low 9; all 14 round-1 findings resolved) | `docs/backlog/reviews/PBI-030/spec-review-r2.md` |

### Round-1 dispositions

Every finding is applied in revision 2 or deferred, with the reason. Applied: 14 of 14; one optional part of
SG30-4 is declined, with the reason.

| Finding | Severity | Disposition | Where / reason |
|---|---|---|---|
| SG30-1 | Medium | **Applied**, as the review's option (a) | §3.5, AL-23, the Q-1 row and "Needs the owner": Q-1 stays high impact and does not block the build, but **must be answered by the owner before the build merges**. The owner answered on 2026-09-19 ("No, 7-day window (Recommended)"), so the breaker is met (revision 3) |
| SG30-2 | Medium | **Applied** | §3.2: the default worktree root is computed from `repoPath`'s normal form with trailing separators stripped, then `-worktrees` is appended. A non-string `repoPath` raises `ValueError`, giving exit 2 or a Refusal. Tests: `LinkSessions` (trailing `/` and `\`), AL-5, AL-18 |
| SG30-3 | Medium | **Applied** | §3.2: `worktreeRoots` entries must be absolute after normalisation and not a filesystem or drive root. `~` and relative entries are refused, not expanded; a bad value exits 2. The shared helper treats any root normalising to `''`, `/` or `X:` as no root, whatever its source, so a drive-root `repoPath` links nothing (A-10). Matching is on path-component boundaries. AL-18 lists every rejected form |
| SG30-4 | Low | **Applied**, with the optional part **declined** | The A-10 label is corrected to extended-length (`//?/C:/…`), and §3.2 states the string-only limits (symlinks, junctions, `subst`, 8.3 names). Stripping `//?/` is declined because 0 of 2,736 measured paths use it. Revision 3 corrects the reason: that measurement is the reason. The second reason first given, "no behaviour change" to `publishable_files`, was inexact at revision 2 (SG30-r2-3). It holds from revision 3, which keeps the no-root rule out of the shared helper |
| SG30-5 | Low | **Applied** | §3.1: distinct files are counted on the lower-cased normal form, and worktree copies count separately (harmless: same project). AL-8 gains a case-and-slash variant |
| SG30-6 | Low | **Applied** | §4.1: a missing `edits` is read as `[]` and popped with a default. The exporter/collector divergence over an unparseable session is noted as pre-existing. New AL-25 |
| SG30-7 | Low | **Applied** | AL-13: the fixture has at least two other stored sessions with runs, plus a guard-refusal case that must never name a missing transcript. AL-6: the `subprocess.run` patch is limited to the exporter and `derive` tests |
| SG30-8 | Low | **Applied** | §6 adds AC-120, A-36, and the parent's row 12 (revision 5 `:296`, as a parent-spec amendment for the planner) |
| SG30-9 | Low | **Applied** | §1 re-cites the parent at revision 5: `:87`, `:89` and `:296` |
| SG30-10 | Low | **Applied** | §3.2 names `export_board.py` (`:243`, `:266-268`) as stopping on a bad value too. That half is untested here, because `tests/test_export_board.py` is outside `allowed_areas` |
| SG30-11 | Low | **Applied** | §3.2 and §4.2: `worktreeRoots` is set once, in `projects()`'s loop; `legacy()` is not edited |
| SG30-12 | Low | **Applied** | §3.2: a worktree root uses the same component-boundary test, and a file directly in the root counts. AL-5 adds `<repoPath>-worktrees-old/x/f` (no link) and a file directly in the root (links) |
| SG30-13 | Low | **Applied** | A-2 and §3.1 label their units (edit calls, main transcript or all folders) and name each session |
| SG30-14 | Low | **Applied** | New AL-24 records the L-2 reading at close-out. AL-1 asserts repo-relative `files` for a newly linked session; A-11 records it as intended (D-12). A-12's docs chore adds the `CLAUDE.md` `files` privacy bullet, `worktreeRoots` and the `-pbi-` convention caveat |

**Round 2 scope** (per the review): SG30-1 to SG30-3, and a check of the Lows' dispositions above.

### Round-2 dispositions

Revision 3 is a text pass, as the review allows ("None of them needs another spec round"). Applied: 9 of 9.
Nothing is deferred. The only part left open is SG30-r2-5's alternative, which is declined.

| Finding | Severity | Disposition | Where / reason |
|---|---|---|---|
| SG30-r2-1 | Low | **Applied** | §4.4: `assemble()` rebinds `st` with the auto-link map before its loop, so `run_doc` (`:436-438`), **`session_doc` (`:440`)** and `project_doc` (`:442`) all read it. AL-2 pins it |
| SG30-r2-2 | Low | **Applied** | §4.1 step 5: `session_doc` reads `st.get('linked_by', {})`, so `tests/test_derive.py:356`'s `st` (no `linked_by`) stays green unchanged. §8 names that test |
| SG30-r2-3 | Low | **Applied**, as option (a) | §3.2 and §4.1 step 3: only the normalisation and the boundary test are shared. The no-root rule lives in the link rule's root builder alone, so "no behaviour change" to `publishable_files` is exact. §8 names the real tests, `Sessions.test_run_doc_*` (`tests/test_derive.py:303-340`), and drops the non-existent `PublishableFiles`. §11's SG30-4 reason is corrected |
| SG30-r2-4 | Low | **Applied** | §3.2: the boundary formula is normative, and it also matches the root itself (harmless). A bare UNC server or share and an entry ending in whitespace are refused in `worktreeRoots` and are no root in the link rule. The extended-length root is accepted as harmless. Recorded in AL-18, A-10 and `LinkSessions` |
| SG30-r2-5 | Low | **Applied**; the alternative (editing `legacy()`) is **declined** | §3.2: an absent or `null` `repoPath` is still read as `''`; `false`, numbers and lists are refused. The exit-2 claim is limited to the `projects` shape. The legacy shape's pre-existing `AttributeError` stays, because `legacy()` is not edited (SG30-11) and only old configs use that shape. AL-18 says so |
| SG30-r2-6 | Low | **Applied** | §3.2: an explicit `worktreeRoots` applies even when `repoPath` is `""`. AL-5 and `LinkSessions` gain the case |
| SG30-r2-7 | Low | **Applied** | §3.3 "Stability" and §3.5 now say an edit counts until its error result arrives, which is transient and self-correcting, as run `files` are today. `LinkSessions` gains a pending-then-failed case. No design change |
| SG30-r2-8 | Low | **Applied** | Q-1 is RESOLVED, with the owner's verbatim answer and the date. AL-23's breaker reads "met" with no "sticky" branch. "Being asked now" is gone from §9 and §11, and §3.5 and §10 read the decision |
| SG30-r2-9 | Low | **Applied** | AL-5's revision-2 and revision-3 additions are folded into its one table row, so §7 renders as one table |
