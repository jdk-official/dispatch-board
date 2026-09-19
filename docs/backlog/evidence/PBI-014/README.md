# PBI-014 — rendered-screenshot evidence (AC-82, NFR-22)

Captured 2026-09-19 by the orchestrator for the owner, who is the named verifier and approves or rejects these.

**How:** the page `site/index.html` at main `47f8c13` (PBI-014 merged as `4bbbad8`), served by the local server (`local/server.py`, local API adapter) over a scratch database from one `local/collector.py --once` pass (201 runs). Headless Edge via CDP, 1400 px wide: open the Dispatch tab, click the run, wait for web fonts, isolate the Run detail panel, capture. Dark = `prefers-color-scheme: dark` (bare `:root` tokens); light = `prefers-color-scheme: light`.

| File | Run | Shows |
|---|---|---|
| `run-detail-code-reviewer-dark.png` / `-light.png` | `a7f2ff8c431f28b3c` "Review PBI-013 forecast change" | Outcome Approved / GO-WITH-CONDITIONS, duration 11 min, 131,126 tokens, 5 findings (id, severity, what's wrong, `file:line`, remediation), files its findings name |
| `run-detail-code-writer-dark.png` / `-light.png` | `aed41112a65c82b5a` "Build PBI-013 usage-limit forecast" | Outcome Done / DONE-WITH-CONDITIONS, 9 min, 136,383 tokens, no findings, files it edited |

**Second light path:** `[data-theme="light"]` set under a dark system preference resolves `--go`, `--changes`, `--nogo` and `--human` to exactly the values `prefers-color-scheme: light` gives (`#1D8752|#9A6200|#C23A2E|#7A3CC4`), and both differ from dark.

**Known and not PBI-014 defects:**
- Builder files show as `…/page.test.mjs`: this capture is from the local database, which has the PBI-027 gap (collector omits the repo). The published board places main-checkout paths relative to the repo; worktree edits are `…/name` on both.
- `&gt;` / `&lt;` in CR-PBI013-01 and -04: the reviewer agent wrote those entities itself (present verbatim in `agent-a7f2ff8c431f28b3c.jsonl`); the page escapes them correctly and shows the source text.
- A visible gap before commas and colons ("Sep 11 , 04:26"): the DOM text has no space (`Sep 11, 04:26 PM`); it is how the Schibsted Grotesk web font renders punctuation, page-wide, in both headless Edge and the in-app Chromium, and predates PBI-014.

**Owner disposition:** _pending_
