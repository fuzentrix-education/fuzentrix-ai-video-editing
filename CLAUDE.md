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

The editor approves **twice** before the slow render, in this order (2026-11-02): first the **storyboard** (one frame per beat, shown
directly as a grid), then the **preview** (the whole edit playing with the real sound). `fzv render` waits for both (rule R2). You still plan the beat sheet (it drives the storyboard frames and
rule V4), but you don't stop for its approval: the editor sees the plan as the storyboard. Only when the prompt says
`Review: beats, storyboard` does the editor approve the beat sheet first (`fzv build` waits for it, rule R1). `Review: off` turns both off.

1. Run `bin/fzv ingest "<folder>"`, then `bin/fzv plan "<folder>"`. Plan writes the brief and drafts `edit/beats.yaml`.
2. Read **only** `<folder>/edit/plan_brief.md` and look at `edit/out/footage.jpg` (the footage every 10 s). The brief has:
   - the prompt and the settings
   - the shots and the layout slots
   - the template catalogue and the props list
   - **concept moments**: where the transcript names something the screen should show, with the templates that show it (freshest
     first), from one collection for every course (`global/concepts.yaml`). Use the ones that fit the lesson; skip a match that
     means something else here, with a word in the beat's notes
   - the compact transcript

   Look up full template parameters in `global/templates/catalogue.json` when needed.
3. **Plan the visuals in the beat sheet** (rules V1–V3, `global/styles/explainer/STYLE.md`). Fill every row of `edit/beats.yaml`:
   `idea` (one sentence), `show` (plain words an editor understands), `templates`, `sync` (the words each step lands on). When the
   English-mode transcript garbles Telugu speech, rewrite `says` as a clean English gist of what is really said (editors read it). Merge or
   split rows freely; they must stay contiguous. For every stretch where the instructor explains how something works, pick the
   template that **shows** it happening, not a card that names it:
   - data being stored / collected → `data-flow`; processed into information → `process-flow`; `int(input())` → `type-convert`;
     "1 to n" / `range` → `range-gen`; each iteration → `trace` + `tiles`; request / fetch / back end → `request-flow`;
     searching many records → `icon-grid` with `scan`; a system's operations → `hub`; logging in / using an app → `mockup`;
     a record or form → `form-card`; tables in a database → `db-tables`; problems / benefits → `callouts` / `checklist`;
     sets, union / intersection / difference → `venn`; checking each character (`isalpha`, `isdigit`…) → `char-scan`.
   - Give **every step its own anchor** on the word that names it (the chip flies into the database on "database").
   - **Never repetitive (V5):** no animation twice in a row, none in more than 20% of the video's animations. When a concept comes
     back, show it another way (the next template in its list, a diagram, props, a chart). `fzv beats` flags repeats.
   - Aim for a new visual every 8–12 s; never more than 15 s of words-only screen. Cover every concept moment from the brief, or
     say in `notes` why not. Use the instructor's own examples; illustrative extras go in `notes` (and later `confirm`).
   - **Never change the whole background** (rule L11): the brand plate stays for the entire video. No dark `scene` and no full-frame
     `cutaway` backdrop unless the prompt asks. Make a big moment big with the graphics themselves: `big-word`, `term-reveal`, a `hub`,
     a larger card or diagram, a presenter move.
   - **Registry animations** (brief: "Registry animations"; in beats `hf:<item>`): mount open-source HyperFrames items with
     `- hf: {item, at, until, box: {x, y, w, h}, vars: {...}, cues: ["@word", …]}` (e.g. `marker-highlight` / `cursor-annotate`
     to point things out, `code-morph` / `code-diff` for code changing, `chart-story` / `count-up` for numbers). One mount per item per
     clip; components fill their box, blocks scale into it.
   - **One kit, colour only for meaning:** every video uses the one Career Orbit kit (`global/brand/brand.yaml`): navy text, one brand
     blue; green = correct / output, red = error / False, amber = look here, and only when the moment means it. Never a colour per
     topic (tone: success/danger/warn are meanings, not decoration). The dotted backdrop stays all video.
   - **Brand colours first:** registry items draw in their own colours, which don't always follow the brand (`constellation-hub`
     rendered violet in Career Orbit, 2026-10-28). Use a brand template whenever one does the job (`hub` for a system and its parts,
     `agenda`, `flowchart`, `checklist`…), keep registry items for what only they can do, and check their colours in the storyboard;
     anything off-brand gets swapped before the editor sees it.
   - **3D** (`db3d`, `network3d`, `loop3d`; three.js, flat shading in the theme's colours): **only when the video's prompt asks for 3D**
     (rule S1; the brief marks the family off otherwise, and beats/validate reject it). Then at most one or two hero moments, where depth
     helps (data going into a database, a request travelling user → DBMS → database, loop values passing a condition); 2D elsewhere.
4. Run `bin/fzv beats "<folder>"` until it reports no problems, and act on its notes. Then go straight on to step 5: no stop for the
   editor. Only with `Review: beats, storyboard` in the prompt: `bin/fzv review "<folder>" --open`, show the editor a compact table (beat,
   time, what we show, on which words) and **wait for their approval**; changes go into the rows (their words in `feedback`); when they
   clearly approve, `bin/fzv approve "<folder>" beats --note "<their words>"`. Never approve on their behalf.
5. Write `<folder>/edit/edit.yaml` from the beat sheet, beat by beat (format: design §10; a worked example is in `examples/`).
   - **`sections`:** one per topic stretch, with contiguous ranges covering every plate and corner shot. Break sections inside studio shots.
   - **`chapter:`** on every section after the intro: a short name (2–3 words, e.g. "Indexing"); neighbouring sections share one. The
     build adds the chapter pill (top left: number, chapter · lesson title) to every clip; don't add it yourself.
   - **`studio`:** at least one `studio-tag` (or another studio-layer scene) for **every** studio shot. Never leave a plain-instructor stretch (rule L4).
   - **Times:** use word anchors (`at: "@phrase the instructor says"`, `"@phrase#2"` for the second occurrence) or seconds read from the transcript; `+0.5` is relative to the scene's `at`.
   - **`decisions:`** a few lines on the styles you chose and why. **`confirm:`** anything shown that wasn't said outright. **`overrides:`** any rule the prompt overrides. **`props_to_add:`** props the prompt asks for that aren't in the library.
6. Run `bin/fzv plan "<folder>" --check`, then `bin/fzv build`, then `bin/fzv validate`. Fix every problem it reports (V4: every beat is
   built with the templates it was approved with; L12: no block covers another, so place the next card below the previous one's real
   height), and act on the V3 and V5 advice.
7. Preview tricky sections with `bin/fzv preview "<folder>" <clip> <t1,t2,…>` when needed.
   - **Compose mode:** zoom into the instructor's edges in a preview snapshot. If a desk, laptop or plant travels with the instructor, add
     `key: {exclude: [[x, y, w, h]], exclude_poly: [[[x, y], …]], cut_below: y}` (find coordinates with `fzv look "<folder>" raw t-t`),
     run `fzv ingest "<folder>" --rekey`, and rebuild. Keep graphics clear of the instructor's poses (validate checks the real silhouette, rule L2).
8. **Storyboard first.** Run `bin/fzv storyboard "<folder>"` and look at `edit/out/storyboard.jpg` yourself; fix wrong visuals, overlaps
   and empty or cluttered frames first. The grid is also saved in the video's folder as `<Title> - Storyboard.jpg`. Then
   `bin/fzv review "<folder>" --open` and show the editor the storyboard directly (no preview yet). **Wait.** On approval:
   `bin/fzv approve "<folder>" storyboard --note "<their words>"`; changes go back through the build and a new storyboard.
9. **Then the preview, before rendering** (`review.preview`): `browser` (default) → `bin/fzv studio "<folder>"` opens the **live preview**
   in HyperFrames Studio (no rendering, real sound; view-only); `video` → `bin/fzv draft "<folder>"` makes a quick low-frame-rate draft
   video. Refresh the page and ask the editor to watch it and approve. **Wait.** On approval: `bin/fzv approve "<folder>" preview --note
   "<their words>"` (it refuses before the storyboard is approved or while the preview of the current build is missing). Open the live
   preview **only** here or when the editor asks for it (`/preview`), and close it (`bin/fzv studio "<folder>" --stop`) when they're done.
10. Run `bin/fzv render`, `bin/fzv finish` and `bin/fzv verify` (or `bin/fzv edit`, which stops at any step still waiting). Verify refreshes
   the review page and runs the **listening check** (measures the final mix: effects buried or too loud, clipping, noise, music
   balance; `edit/out/listen.json`). Fix what it reports (usually `bin/fzv mix` levels, or a cue moved off a word), then tell the editor where
   the final is and list the "to confirm" items in plain words.

## House rules that matter most

The full set is `global/RULES.md`, the master prompt every edit follows (the team's master prompt v5 adapted to this workflow); it is
in every video's brief. The ones that matter most:

- **Content comes from the video's own audio only.** Never from a script or PDF.
- **Never move, blur or circle the instructor in a rough cut.** Graphics go only in the empty space (layout slots).
  The bottom-right instructor is boxed automatically in both modes (`presenter.corner_box`; prompt `Presenter box: off`); keep graphics clear of the box.
- **Show the process, in sync** (V1–V3): text labels, animation explains. Every explained process moves on screen, step by step on its words.
- **The background never changes** (L11): the brand plate stays all video; no dark scenes or full-frame cutaways unless the prompt asks.
- **Always something on screen; never clutter.** At most 4 blocks, 40 words and 12 code lines at once. One idea at a time.
- **Explanations sit outside code cards and terminals,** joined by `note` wires. Recordings are shown whole (`recording-window`).
- **Output is real:** every terminal uses `exec: {code: <card id>, stdin: [...]}`; the build runs the code and prints its exact output. Never type output by hand.
- **`Recording: reference`:** never show the recording. Rebuild each program from the keyframes in `edit/recref/` (type lines at the keyframe times; Run when the instructor clicks Run) and check the `exec` output in `edit.resolved.yaml` against the recording's output keyframe.
  - **Corrections (default `tidy`):** fix the recording's typos, spacing and false starts in `lines`, and put the code exactly as typed in `recorded:`. The build logs every change and runs both versions; never change what the program prints without `logic_fix: <why>`. With `Recording: reference, exact`, copy it as typed.
- **Off unless the prompt asks:** subtitles, music, the sketch style and outros.
- **Sound:** templates record their cues; `fzv finish` keeps only the meaningful ones and uses the team's library in `global/sfx/` first (A5). Don't add extra sound cues.
  Her voice is cleaned (denoise, EQ, levelling, de-ess; prompt `Voice: untouched` turns it off) and never lowered; effects sit 18–26 dB
  under it and dip while she speaks.
- **Styles:**
  - **Base on every video:** Core and Code.
  - **Wherever a process is explained:** Explainer (data-flow, process-flow, type-convert, range-gen, request-flow, icon-grid, hub, mockup, form-card, db-tables, callouts, checklist, big-word).
  - **Only when the prompt asks for 3D:** 3D (db3d, network3d, loop3d), for one or two hero moments.
  - **Where the content calls for them:** Kinetic for key terms (12 words max), Diagram for structure, Data for numbers.
  - **Props:** from `global/props/` only.

## Revising after delivery

Requests name a time (`7:41 …`) or a beat (`beat 7: …`); the review page's **Copy for Claude** produces both.
1. Run `bin/fzv revise "<folder>" "<the request>"`. It prints the affected scenes and the speech around each time or beat, and logs the request in `edit/revisions.md`.
2. Edit only those scenes in `edit.yaml`. When what a beat shows changes, update its row in `edit/beats.yaml` too and add the editor's words to
   `feedback`. With the beat-sheet gate on (`Review: beats, storyboard`), their request approves the rows it touches:
   `bin/fzv approve "<folder>" beats --note "change request: <their words>"`.
3. Run build, validate and `bin/fzv storyboard` (only changed frames are redone; see `edit/out/storyboard_changed.jpg`) and show the
   editor the changed frames; on approval `bin/fzv approve "<folder>" storyboard --note "<their words>"`. Then the preview (`bin/fzv studio`,
   or `bin/fzv draft` in video mode: only changed clips are re-drafted); on approval `bin/fzv approve "<folder>" preview --note "<their words>"`.
   If their request already said to go ahead and render, record both approvals with their words.
4. Run render, finish and verify; only changed clips and chunks are redone. Update the request's **Status** in `edit/revisions.md` to say what changed.
- **Music requests** ("music: off", "music: keep calm-piano, level high", "music: add focus-piano, level low", from the review page's music
  switch): `bin/fzv mix "<folder>" off|on|<track> [--level low|normal|high]`. It updates prompt.md and re-mixes only (no graphics re-render).

## Changing the system itself

- **Templates:** `runtime/templates/*.js`. Each `FZ.register(meta, fn)` carries its own documentation. Run `bin/fzv templates --refresh` after changes.
- **Brand values:** `global/brand/brand.yaml` (the one kit; `bin/fzv brands --sheet` renders `brand_sheet.png`). **Defaults:** `global/defaults.yaml`. **Rules:** `global/rules.yaml` plus `fzv/validate.py`.
- **Checks:** run `.venv/bin/python -m pytest` before handing back.
