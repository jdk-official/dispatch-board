# Demonstration evidence: AC-84, AC-85 and AC-92

- **Recorded:** 2026-09-11
- **Recorded for:** PBI-022 (AC-R3)
- **Source under test:** `site/index.html` as on branch `pbi/PBI-022-prd-rebaseline` (base: PR #1, commit `942842b`)

## How the demonstrations were run

The live page runs inside claude.ai's artifact frame, which cannot be driven from a script. Each demonstration therefore runs the page's own source in the in-app browser, on a local copy.

- **The copy:** `out/preview/harness.html`, which is gitignored.
- **The data:** the board's real exported data, meaning the `out/` documents pushed to the live store on 2026-09-11. The copy stubs only the store connection (`window.claude.use('db')`).
- **The checks:** each check reads the rendered DOM. The copy also records any page error or `console.error`, and every run below logged none.

**To rebuild the copy:**
1. Load every JSON document from `out/sessions/`, `out/runs/`, `out/projects/` and `out/projectTabs/`, plus `out/catalogue/index.json`, `out/meta/status.json` and `out/status/dispatch-board.json`, into one object.
2. Write a `<script>` that sets `window.claude = { use: async n => n === 'db' ? <a fake store> : null }`. The fake store answers `collection(name).orderBy().onSnapshot` and `doc(path).onSnapshot` from that object.
3. Put that script before the contents of `site/index.html`.

The copy is not committed, because it embeds session data.

## AC-84: the "Claude usage" tab label at 1050 px

> When the page is shown at a viewport width of 1050 px, the page shall show the "Claude usage" tab label in full or show a visible overflow cue.

- **Setup:** the viewport set to 1050 × 800, with the dispatch-board project selected.
- **Observed:**
  - the tab row wraps onto a second line (two rows of tabs), because `.tabs` uses `flex-wrap: wrap`;
  - "Claude usage" sits at the start of the second row, at x 28–136 px of the 1050 px viewport;
  - its text is not clipped (`scrollWidth` ≤ `clientWidth`);
  - the page body does not scroll sideways.
- **Recording:** these figures were measured from the rendered DOM. A screenshot was viewed during the run but not saved, so this note is the record.
- **Result:** met. The label shows in full, so no overflow cue is needed.

## AC-85: every tab for the dispatch-board project

> When the dispatch-board project is selected, the page shall show the Overview, Spec, Assumptions, Decisions, Backlog, GitHub, Dispatch, Agent catalogue and Claude usage tabs.
>
> (PRD revision 3 wording. Revision 2 listed eight tabs, without Agent catalogue.)

- **Setup:** the page loaded with the real data. The picker lists "dispatch-board · live", "platform-catalogue" and "Other sessions · last 7 days", and dispatch-board is selected by default.
- **Observed visible tabs:** Overview, Spec, Assumptions, Decisions & not worked out, Backlog & status, GitHub details, Dispatch, Agent catalogue, Claude usage.
- **Result:** met. All nine tabs the revision-3 criterion names are shown.

## AC-92: the session filter narrows Dispatch to one session

> When a project with two linked sessions is selected and the session filter names one of them, the page shall list in Dispatch only that session's runs.

- **Setup:** no project in the real config links two sessions yet; each links one. This demonstration therefore used a second local copy, `out/preview/harness-two-sessions.html`.
  - **Data:** the same real data, with these changes made in the copy only:
    - dispatch-board's `sessions` list became `[9562c312, 7f71729a]`;
    - platform-catalogue's `sessions` list was emptied;
    - session `7f71729a` (platform-catalogue's build session) and all 56 of its runs had their `project` field rewritten from `platform-catalogue` to `dispatch-board`.
  - **Why the move was needed:** the page scopes a project by each session's and run's `project` field, not by the list alone.
  - Nothing in `board.config.json` or the live store was changed.
- **Observed**, with dispatch-board selected:
  - the filter offered "All sessions · 2", "Dispatchboard · live" (`9562c312`) and "Agent catalog plugins setup" (`7f71729a`);
  - the Dispatch run log showed these rows:

    | Filter | Rows | Runs in that scope | Runs from the other session |
    |---|---|---|---|
    | All sessions | 79 | 79 | — |
    | `7f71729a` | 56 | 56 | none |
    | `9562c312` | 23 | 23 | none |

  - with a session selected, the Agent runs tile read "dispatched in this session";
  - the page logged no errors.
- **Automated cover:** `tests/page.test.mjs` also checks the filter ("session filter narrows Dispatch and usage to one session; project tabs stay"). Its fixture project has one session, so this demonstration is what covers the two-session case.
- **Result:** met.
