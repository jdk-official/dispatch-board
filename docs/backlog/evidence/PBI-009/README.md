# PBI-009 — rendered-screenshot evidence (spec W-14, NFR-22)

Captured 2026-09-19 by the orchestrator for the owner, who is W-14's named verifier and approves or rejects these.

**How:** the page `site/index.html` at main `25156c9` (PBI-009 merged), served by `local/server.py` on port 8766 over a scratch database from one `local/collector.py --once` pass with the merged code. Headless Edge via CDP, 1400 px wide: project picker set to dispatch-board, Overview, web fonts loaded, the summary tile and the "Waiting on you" panel isolated and captured. Dark = `prefers-color-scheme: dark` (bare `:root`); light = `prefers-color-scheme: light`.

**The panel's contents are a fixture, clearly so.** On the real transcripts nothing was waiting at capture time, because every question and refusal had since been followed by a message the owner typed. An empty panel would not show the design. So one session record in the **scratch database only** was given a `waiting` value in the exporter's exact shape: one structured question (`source: ask`), one refusal of each kind (`automode-blocked`, `user-rejected`, `permission-rule`) and `more: 2`. The detection itself is evidenced separately: the page and derive tests, and the round-2 reviewer's read-only run over the owner's 24 real transcripts (all 15 refusals survive until a typed owner message).

| File | Shows |
|---|---|
| `waiting-on-you-dark.png` | Tile "Waiting on you 4", panel with "Asked you" and three "Refused" items, "+2 more waiting" |
| `waiting-on-you-light.png` | The same, light theme |

**Second light path:** `[data-theme="light"]` under a dark system preference resolves `--go`, `--changes`, `--nogo` and `--human` to exactly the light values (`#1D8752|#9A6200|#C23A2E|#7A3CC4`).

**Owner disposition:** approved 2026-09-19, verbatim: "W-14 OK".
