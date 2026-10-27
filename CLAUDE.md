# Working in this repo (for Claude)

This repo is `fzv`, the Fuzentrix video editing pipeline. Your job in a session is usually one of two things:
- **Edit a video:** plan its beat sheet with the editor, then write its `edit/edit.yaml`.
- **Revise a delivered video:** change only the scenes a timestamped request touches.

The design is `docs/SYSTEM_DESIGN.md`. Its rules (§8) are defaults that a video's prompt may override.

## Who you talk to

Often a **video editor, not a programmer**, through the project skills in `.claude/skills/` (`/edit-video`, `/change`, `/review`,
`/approve`). Speak plainly to them: what you are doing, what they should look at, what they decide. Never paste commands, YAML or
logs into the chat. The `bin/fzv` steps are pre-approved in `.claude/settings.json`.

## Editing a video

The editor approves twice before the slow render: the **beat sheet** (plan) and the **storyboard** (one frame per beat).
`fzv build` waits for the first and `fzv render` for the second (rules R1/R2; prompt `Review: off` turns them off).

1. Run `bin/fzv ingest "<folder>"`, then `bin/fzv plan "<folder>"`. Plan writes the brief and drafts `edit/beats.yaml`.
2. Read **only** `<folder>/edit/plan_brief.md` and look at `edit/out/footage.jpg` (the footage every 10 s). The brief has:
   - the prompt and the settings
   - the shots and the layout slots
   - the template catalogue and the props list
   - **concept moments**: where the transcript names something the screen should show, with the templates that show it
   - the compact transcript

   Look up full template parameters in `global/templates/catalogue.json` when needed.
3. **Plan the visuals in the beat sheet** (rules V1–V3, `global/styles/explainer/STYLE.md`). Fill every row of `edit/beats.yaml`:
   `idea` (one sentence), `show` (plain words an editor understands), `templates`, `sync` (the words each step lands on). Merge or
   split rows freely; they must stay contiguous. For every stretch where the instructor explains how something works, pick the
   template that **shows** it happening, not a card that names it:
   - data being stored / collected → `data-flow`; processed into information → `process-flow`; `int(input())` → `type-convert`;
     "1 to n" / `range` → `range-gen`; each iteration → `trace` + `tiles`; request / fetch / back end → `request-flow`;
     searching many records → `icon-grid` with `scan`; a system's operations → `hub`; logging in / using an app → `mockup`;
     a record or form → `form-card`; tables in a database → `db-tables`; problems / benefits → `callouts` / `checklist`.
   - Give **every step its own anchor** on the word that names it (the chip flies into the database on "database").
   - Aim for a new visual every 8–12 s; never more than 15 s of words-only screen. Cover every concept moment from the brief, or
     say in `notes` why not. Use the instructor's own examples; illustrative extras go in `notes` (and later `confirm`).
   - Compose mode: one or two big moments may use `scene: {kind: dark}` behind the instructor (a hero reveal, a fun fact).
   - **Registry animations** (brief: "Registry animations"; in beats `hf:<item>`): mount open-source HyperFrames items with
     `- hf: {item, at, until, box: {x, y, w, h}, vars: {...}, cues: ["@word", …]}` (e.g. `constellation-hub` for a system and its
     parts, `hw-arrow` / `hw-callout-circle` / `marker-highlight` / `cursor-annotate` to point things out, `code-morph` / `code-diff`
     for code changing, `chart-story` / `count-up` for numbers). One mount per item per clip; components fill their box, blocks scale into it.
4. Run `bin/fzv beats "<folder>"` until it reports no problems, and act on its notes. Then `bin/fzv review "<folder>" --open` and
   show the editor a compact table (beat, time, what we show, on which words). **Wait for their approval.** Changes go into the rows
   (their words in `feedback`). When they clearly approve: `bin/fzv approve "<folder>" beats --note "<their words>"`. Never approve on
   their behalf.
5. Write `<folder>/edit/edit.yaml` from the approved beat sheet, beat by beat (format: design §10; a worked example is in `examples/`).
   - **`sections`:** one per topic stretch, with contiguous ranges covering every plate and corner shot. Break sections inside studio shots.
   - **`studio`:** at least one `studio-tag` (or another studio-layer scene) for **every** studio shot. Never leave a plain-instructor stretch (rule L4).
   - **Times:** use word anchors (`at: "@phrase the instructor says"`, `"@phrase#2"` for the second occurrence) or seconds read from the transcript; `+0.5` is relative to the scene's `at`.
   - **`decisions:`** a few lines on the styles you chose and why. **`confirm:`** anything shown that wasn't said outright. **`overrides:`** any rule the prompt overrides. **`props_to_add:`** props the prompt asks for that aren't in the library.
6. Run `bin/fzv plan "<folder>" --check`, then `bin/fzv build`, then `bin/fzv validate`. Fix every problem it reports (V4: every beat is
   built with the templates it was approved with), and act on the V3 advice.
7. Preview tricky sections with `bin/fzv preview "<folder>" <clip> <t1,t2,…>` when needed.
   - **Compose mode:** zoom into the instructor's edges in a preview snapshot. If a desk, laptop or plant travels with the instructor, add
     `key: {exclude: [[x, y, w, h]], exclude_poly: [[[x, y], …]], cut_below: y}` (find coordinates with `fzv look "<folder>" raw t-t`),
     run `fzv ingest "<folder>" --rekey`, and rebuild. Keep graphics clear of the instructor's poses (validate checks the real silhouette, rule L2).
8. Run `bin/fzv storyboard "<folder>"` and look at `edit/out/storyboard.jpg` yourself; fix wrong visuals, overlaps and empty or cluttered
   frames first. Then `bin/fzv review "<folder>" --open` and ask the editor to approve. **Wait.** On approval:
   `bin/fzv approve "<folder>" storyboard --note "<their words>"`.
9. Run `bin/fzv render`, `bin/fzv finish` and `bin/fzv verify` (or `bin/fzv edit`, which stops at any step still waiting). Verify refreshes
   the review page. Tell the editor where the final is and list the "to confirm" items in plain words.

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

Requests name a time (`7:41 …`) or a beat (`beat 7: …`); the review page's **Copy for Claude** produces both.
1. Run `bin/fzv revise "<folder>" "<the request>"`. It prints the affected scenes and the speech around each time or beat, and logs the request in `edit/revisions.md`.
2. Edit only those scenes in `edit.yaml`. When what a beat shows changes, update its row in `edit/beats.yaml` too and add the editor's words to
   `feedback`; their request approves the rows it touches: `bin/fzv approve "<folder>" beats --note "change request: <their words>"`.
3. Run build, validate and `bin/fzv storyboard` (only changed frames are redone; see `edit/out/storyboard_changed.jpg`). Show the editor and ask
   before rendering, unless their request already said to go ahead; then `bin/fzv approve "<folder>" storyboard --note "<their words>"`.
4. Run render, finish and verify; only changed clips and chunks are redone. Update the request's **Status** in `edit/revisions.md` to say what changed.

## Changing the system itself

- **Templates:** `runtime/templates/*.js`. Each `FZ.register(meta, fn)` carries its own documentation. Run `bin/fzv templates --refresh` after changes.
- **Brand values:** `global/brand/`. **Defaults:** `global/defaults.yaml`. **Rules:** `global/rules.yaml` plus `fzv/validate.py`.
- **Checks:** run `.venv/bin/python -m pytest` before handing back.
