# Explainer (show the process)

**Availability:** Always, wherever the instructor explains how something works. **Used for:** data flowing and being stored,
values converting, sequences being generated, requests travelling and returning, searches through many records, systems and
their operations, apps being used, records filling in, pain points and benefits.

This family exists because a text card only *labels* an idea. When the instructor describes a process, the screen must *show it
happening*, step by step, on the instructor's words (rules V1–V3).

## The rules

- **Show, don't label (V1).** Every section longer than 30 s has at least one animated explanation. Headers, cards, chips and
  definitions frame the idea; an Explainer, Code, Diagram, Data or Props template shows it.
- **No long words-only stretches (V2).** At most 15 s of screen where only text templates are visible.
- **Sync every step (V3).** Each step of an animation has its own `at`, anchored to the word that names it (`"@type conversion"`).
  When the instructor says "the data goes into the database", the item flies in on "database", not on a timer.
- **Rhythm.** A new visual roughly every 8–12 s; one idea on screen at a time (clutter budget, L10).
- **Concept moments.** `fzv plan` lists the places where the transcript names a concept from `global/concepts.yaml`, with the
  templates that show it; cover each one, or say in `decisions` why not. `fzv validate` reports uncovered moments as advice.
- **Illustrative details** (sample rows, a receipt, a portal screen) make the idea concrete. Use the instructor's own examples
  first (Rahul · 101 · CSE · 85); anything not said goes under `confirm`.

## Concept → template

| The instructor says… | Show it with | What moves |
|---|---|---|
| "store / collect / save the data", "data organised" | `data-flow` (or `db-tables`) | each item flies into the database as it is named; the cylinder fills, the count rises |
| "process it", "arrange it", "information" | `process-flow` | raw items → gear spins → the meaningful sentence; optional `banner` equation |
| "type conversion", `int(input())` | `type-convert` | `"20"` (str) drops into `int()` and comes out `20` (int); optional `then: 20 + 1 = 21` |
| "1 to n", `range(1, n+1)`, "generate numbers" | `range-gen` | numbers emitted one by one into slots; `n+1` not included; `stop_value` turns red on `break` |
| each iteration / the condition per round | `trace` + `tiles` (Code family) | the variable box rolls, True/False per round, tiles change state |
| "request", "fetch", "the bridge", "back end" | `request-flow` | a Request packet travels user → system → database, the Result comes back; `blocked` shows "no direct access" |
| "search", "find", "how long will it take" | `icon-grid` with `scan` / `find` | a magnifier sweeps thousands of records; the found one lights up |
| "10,000 students", "thousands of records" | `icon-grid` (count) or `counter` | the grid fills while the number counts up |
| "create, retrieve, update, delete", what a system does | `hub` | the system badge, then each operation on its spoke as it is named |
| "log in", "open the portal", "click results" | `mockup` (browser / phone) | fields type, the button presses, a spinner, the results appear |
| "your name, age, branch…", a record or form | `form-card` | each value types into its field when said |
| "inside a database: students, faculty, library" | `db-tables` | each table appears with its rows |
| problems / benefits around the instructor | `callouts` / `checklist` | chips pop at free spots; rows tick off |
| the term itself, first time | `big-word`, then `definition` | the giant word letter by letter, then the one-line definition |
| a big moment (the hero reveal, a fun fact) | `scene: dark` (compose mode) + `hub` / a card | the background turns to the dark brand scene behind the instructor |

## Look

- Brand variables only; nodes and cards are white with the brand line, containers in `--fz-action`, accents in `--fz-accent`.
- Moving things (packets, flying chips, dots) use the brand action/accent colours; results use `--fz-success`, stops `--fz-danger`.
- Motion: quick, purposeful (0.35–0.9 s per step), eased; nothing loops idly for long.
- Sound: let the template record its cues; `fzv finish` keeps only the meaningful ones (rule A5).

Templates: see `global/templates/explainer/` (or `fzv templates`).

## Ready-made alternatives (Registry family)

Open-source HyperFrames items mounted with `hf` (`fzv registry list` for variables): `constellation-hub` / `radial-surround` (a
system and its parts, cue per part), `count-up` / `chart-story` / `mk-progress-stat` (numbers), `code-morph` / `code-diff` /
`code-highlight` / `code-terminal-run` (code changing, a line in focus, a command running), `hw-arrow` / `hw-callout-circle` /
`hw-box-label` / `hw-underline` / `marker-highlight` / `cursor-annotate` (pointing things out), `comparison-split` (before/after),
`state-chip-rail` (a process moving through states), `chat-message` / `notification-stack` / `browser-device-stage` (app moments).
Prefer the Explainer templates when the brand look matters most; registry items carry their own styling.
