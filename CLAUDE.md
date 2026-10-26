# Working in this repo (for Claude)

This repo is `fzv`, the Fuzentrix video editing pipeline. Your job in a session is usually one of two things:
- **Edit a video:** write its `edit/edit.yaml`.
- **Revise a delivered video:** change only the scenes a timestamped request touches.

The design is `docs/SYSTEM_DESIGN.md`. Its rules (§8) are defaults that a video's prompt may override.

## Editing a video

1. Run `bin/fzv ingest "<folder>"`, then `bin/fzv plan "<folder>"`.
2. Read **only** `<folder>/edit/plan_brief.md`. It has:
   - the prompt and the settings
   - the shots and the layout slots
   - the template catalogue and the props list
   - **concept moments**: where the transcript names something the screen should show, with the templates that show it
   - the compact transcript

   Look up full template parameters in `global/templates/catalogue.json` when needed.
3. **Plan the visuals first** (rules V1–V3, `global/styles/explainer/STYLE.md`). Go through the transcript and, for every stretch
   where the instructor explains how something works, pick the template that **shows** it happening, not a card that names it:
   - data being stored / collected → `data-flow`; processed into information → `process-flow`; `int(input())` → `type-convert`;
     "1 to n" / `range` → `range-gen`; each iteration → `trace` + `tiles`; request / fetch / back end → `request-flow`;
     searching many records → `icon-grid` with `scan`; a system's operations → `hub`; logging in / using an app → `mockup`;
     a record or form → `form-card`; tables in a database → `db-tables`; problems / benefits → `callouts` / `checklist`.
   - Give **every step its own anchor** on the word that names it (the chip flies into the database on "database").
   - Aim for a new visual every 8–12 s; never more than 15 s of words-only screen. Cover every concept moment from the brief, or
     say in `decisions` why not. Use the instructor's own examples; illustrative extras go under `confirm`.
   - Compose mode: one or two big moments may use `scene: {kind: dark}` behind the instructor (a hero reveal, a fun fact).
   - **Registry animations** (brief: "Registry animations"): mount open-source HyperFrames items with
     `- hf: {item, at, until, box: {x, y, w, h}, vars: {...}, cues: ["@word", …]}` (e.g. `constellation-hub` for a system and its
     parts, `hw-arrow` / `hw-callout-circle` / `marker-highlight` / `cursor-annotate` to point things out, `code-morph` / `code-diff`
     for code changing, `chart-story` / `count-up` for numbers). One mount per item per clip; components fill their box, blocks scale into it.
4. Write `<folder>/edit/edit.yaml` (format: design §10; a worked example is in `examples/`).
   - **`sections`:** one per topic stretch, with contiguous ranges covering every plate and corner shot. Break sections inside studio shots.
   - **`studio`:** at least one `studio-tag` (or another studio-layer scene) for **every** studio shot. Never leave a plain-instructor stretch (rule L4).
   - **Times:** use word anchors (`at: "@phrase the instructor says"`, `"@phrase#2"` for the second occurrence) or seconds read from the transcript; `+0.5` is relative to the scene's `at`.
   - **`decisions:`** a few lines on the styles you chose and why. **`confirm:`** anything shown that wasn't said outright. **`overrides:`** any rule the prompt overrides. **`props_to_add:`** props the prompt asks for that aren't in the library.
5. Run `bin/fzv plan "<folder>" --check`, then `bin/fzv build`, then `bin/fzv validate`. Fix every problem it reports, and act on the V3 advice (uncovered concept moments).
6. Preview tricky sections with `bin/fzv preview "<folder>" <clip> <t1,t2,…>` and look at the sheet before rendering.
   - **Compose mode:** zoom into the instructor's edges in a preview snapshot. If a desk, laptop or plant travels with the instructor, add
     `key: {exclude: [[x, y, w, h]], exclude_poly: [[[x, y], …]], cut_below: y}` (find coordinates with `fzv look "<folder>" raw t-t`),
     run `fzv ingest "<folder>" --rekey`, and rebuild. Keep graphics clear of the instructor's poses (validate checks the real silhouette, rule L2).
7. Run `bin/fzv render`, `bin/fzv finish` and `bin/fzv verify`. Show the user `edit/out/verify.jpg`, and list the "to confirm" items.

## House rules that matter most

- **Content comes from the video's own audio only.** Never from a script or PDF.
- **Never move, blur or circle the instructor in a rough cut.** Graphics go only in the empty space (layout slots).
  The bottom-right instructor is boxed automatically in both modes (`presenter.corner_box`; prompt `Presenter box: off`); keep graphics clear of the box.
- **Show the process, in sync** (V1–V3): text labels, animation explains. Every explained process moves on screen, step by step on its words.
- **Always something on screen; never clutter.** At most 4 blocks, 40 words and 12 code lines at once. One idea at a time.
- **Explanations sit outside code cards and terminals,** joined by `note` wires. Recordings are shown whole (`recording-window`).
- **Output is real:** every terminal uses `exec: {code: <card id>, stdin: [...]}`; the build runs the code and prints its exact output. Never type output by hand.
- **`Recording: reference`:** never show the recording. Rebuild each program from the keyframes in `edit/recref/` (type lines at the keyframe times; Run when the instructor clicks Run) and check the `exec` output in `edit.resolved.yaml` against the recording's output keyframe.
  - **Corrections (default `tidy`):** fix the recording's typos, spacing and false starts in `lines`, and put the code exactly as typed in `recorded:`. The build logs every change and runs both versions; never change what the program prints without `logic_fix: <why>`. With `Recording: reference, exact`, copy it as typed.
- **Off unless the prompt asks:** subtitles, music, the sketch style and outros.
- **Sound:** templates record their cues; `fzv finish` keeps only the meaningful ones and uses the team's library in `global/sfx/` first (A5). Don't add extra sound cues.
- **Styles:**
  - **Base on every video:** Core and Code.
  - **Wherever a process is explained:** Explainer (data-flow, process-flow, type-convert, range-gen, request-flow, icon-grid, hub, mockup, form-card, db-tables, callouts, checklist, big-word, scene).
  - **Where the content calls for them:** Kinetic for key terms (12 words max), Diagram for structure, Data for numbers.
  - **Props:** from `global/props/` only.

## Revising after delivery

1. Run `bin/fzv revise "<folder>" "<the user's request with timestamps>"`. It prints the affected scenes and the speech around each timestamp, and logs the request in `edit/revisions.md`.
2. Edit only those scenes in `edit.yaml`. Then run build, validate, render, finish and verify; only changed clips and chunks are redone.
3. Update the request's **Status** in `edit/revisions.md` to say what changed.

## Changing the system itself

- **Templates:** `runtime/templates/*.js`. Each `FZ.register(meta, fn)` carries its own documentation. Run `bin/fzv templates --refresh` after changes.
- **Brand values:** `global/brand/`. **Defaults:** `global/defaults.yaml`. **Rules:** `global/rules.yaml` plus `fzv/validate.py`.
- **Checks:** run `.venv/bin/python -m pytest` before handing back.
