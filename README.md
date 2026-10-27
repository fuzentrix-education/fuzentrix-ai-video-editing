# Fuzentrix video editing automations (`fzv`)

`fzv` turns an instructor's video into a finished, on-brand teaching video with motion graphics: titles, code cards that type
along with the instructor, the program's real output, diagrams, props and characters, sound effects and (if asked) music.

- **Global files** define what every video gets: brand kits, rules, style families, templates, icons, props, characters and music.
- **A prompt per video** steers or overrides any of those defaults for that video.
- **Editors chat, Claude edits.** Video editors work in Claude Code in VS Code (`/edit-video`, `/change`, `/review`, `/approve`);
  Claude runs every `fzv` step. They approve a **beat sheet** (what each idea shows, on which words) and a **storyboard** (one frame
  per beat over the real footage) on a local review page before the slow render.
- **Fixes after delivery** are made by beat or time ("beat 7: use a car", "7:41 make the note larger"); only the changed parts are redone.
- **Claude writes the edit.** `fzv` prepares a plan brief and a draft beat sheet from the video; Claude (following [CLAUDE.md](CLAUDE.md))
  fills the beat sheet and writes the edit spec from it; `fzv` checks it against the rules, renders it and delivers the final MP4.

**Editors start here: [docs/EDITOR-GUIDE.md](docs/EDITOR-GUIDE.md)** (one page, no commands).
**Everyone else: [docs/WORKFLOW.md](docs/WORKFLOW.md), the end-to-end procedure** (setup, shared assets, a video from folder to
delivery, review checklist, revisions). The full design (decisions, rules, styles, spec format) is in [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md). The latest end-to-end
test on real videos (an overlay rough cut and a green-screen take) is in [docs/test-reports/](docs/test-reports/2026-10-26-workflow-test.md).

---

## Contents

1. [Quick start](#1-quick-start)
2. [Setup](#2-setup-once-per-machine)
3. [Editing a video, step by step](#3-editing-a-video-step-by-step)
4. [The prompt](#4-the-prompt)
5. [Screen recordings](#5-screen-recordings)
6. [Code and program output](#6-code-and-program-output)
7. [House rules](#7-house-rules)
8. [Styles and templates](#8-styles-and-templates)
9. [Brand kits](#9-brand-kits)
10. [Icons, props, characters, music and SFX](#10-icons-props-characters-and-music)
11. [Revising a delivered video](#11-revising-a-delivered-video)
12. [Command reference](#12-command-reference)
13. [What ends up in a video&#39;s folder](#13-what-ends-up-in-a-videos-folder)
14. [Speed and machines](#14-speed-and-machines)
15. [Troubleshooting](#15-troubleshooting)
16. [Working on the system](#16-working-on-the-system)

---

## 1. Quick start

```bash
# once per machine (details in §2): installs everything, downloads the renderer's browser and the transcription model
bin/setup

# per video: a folder with the raw cut (and any screen recording)
bin/fzv edit "videos/loop-control" --prompt "# Loop Control Statements
Brand: career-orbit
- Make the three example programs the highlight."
# -> stops after writing edit/plan_brief.md and a draft edit/beats.yaml
# -> Claude fills the beat sheet; the editor approves it on edit/review/index.html  (bin/fzv approve … beats)
# -> Claude writes edit/edit.yaml; build, validate, storyboard; the editor approves  (bin/fzv approve … storyboard)
bin/fzv edit "videos/loop-control"
# -> videos/loop-control/Loop Control Statements - Edited.mp4, edit/out/verify.jpg and the review page
```

In Claude Code all of this is one request: `/edit-video videos/loop-control`.

## 2. Setup (once per machine)

**You need:** macOS or Linux with [Homebrew](https://brew.sh) (or equivalents) for `ffmpeg`, `node` (20+) and `uv`. Then, from the
repo folder:

```bash
brew install ffmpeg node uv        # if not installed yet
bin/setup
```

`bin/setup` is the whole one-time setup, safe to run again:
1. checks the tools (ffmpeg with VP9, Node 20+, uv);
2. creates the Python environment and installs fzv (mlx-whisper on Apple Silicon, faster-whisper elsewhere);
3. installs HyperFrames and downloads its headless Chrome;
4. downloads the transcription model once (about 1.6 GB);
5. checks the shared library that ships with the repo (templates, registry animations, icons, props, music, sound effects, brand kits);
6. runs `fzv doctor` (workers, transcription backend, encoder) and the tests.

**Nothing is downloaded per video.** Every template, animation, icon, prop, character, music track and sound effect lives in
`global/` inside the repo; adding more later is optional (§10).

- Chrome: `fzv` uses HyperFrames' headless Chrome, Puppeteer's, or a system Chrome. Set `FZV_CHROME=/path/to/chrome` to choose one.
- To run code shown in videos (§6): Python is built in; C/C++ need `cc`/`c++`, Java needs a JDK, JavaScript needs Node.

## 3. Editing a video, step by step

### 3.1 The video's folder

Every video has its own folder. You put in:

- the **raw cut** (the editor's rough cut, or raw footage / green screen),
- any **screen recording** as a separate file (raw cuts never contain recordings; `fzv` aligns them by audio),
- optionally a **`prompt.md`** (or pass `--prompt` once; it is saved there).

Everything `fzv` makes goes into `<folder>/edit/`; the final video lands next to the raw cut as `<Title> - Edited.mp4`.
A previous final is moved to `edit/_prev/` before it is replaced. The repo itself never holds per-video files.

```
videos/loop-control/
  LOOP CONTROL ST ROUGH CUT .mp4      raw cut (the largest video with speech)
  screen recording .mp4               recording (aligned to the raw cut by audio)
  prompt.md                           the video's prompt
  Loop Control Statements - Edited.mp4   final video
  edit/                               everything else (§13)
```

### 3.2 The stages

`fzv edit <folder>` runs all stages in order; each also runs on its own (§12).

| Stage              | What happens                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ingest**   | Picks the raw cut and recordings. Extracts audio. Transcribes (Telugu + English speech, English-mode Whisper with word timestamps). Finds every shot change to the exact frame and classifies shots (studio close-up / plate with instructor in the corner / plate). Measures the instructor's safe zones and the free layout slots. Aligns each recording by audio, measures its content area and saves keyframes.**Mode:** an editor's rough cut is *overlay* mode (graphics go only into the empty space, the instructor is never touched); raw or green-screen footage is *compose* mode (the instructor is keyed and placed on the brand background). |
| **plan**     | Writes`edit/plan_brief.md` (prompt, settings, shots, layout slots, recordings and keyframes, templates, icons, props, music, the timed transcript) and drafts `edit/beats.yaml`: one row per beat (8–20 s), cut at pauses, shot changes and concept moments. |
| **(Claude + editor)** | Claude fills the beat sheet (idea, what we show, templates, sync words); `fzv beats` checks it and refreshes the review page; the editor approves (`fzv approve <folder> beats`). Then Claude writes`edit/edit.yaml` from it, following [CLAUDE.md](CLAUDE.md). `build` waits for the approval (rule R1). |
| **build**    | Resolves word anchors (`at: "@phrase the instructor says"`), runs the programs shown on screen (§6), compiles clips into `edit/built/`, writes `edit/decisions.md`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **validate** | Samples every clip twice a second in headless Chrome and checks the house rules (§7), including V4 (every beat built as approved). Fix what it reports;`fzv edit --force` renders anyway. |
| **preview**  | (optional)`fzv preview <folder> <clip> <t1,t2>` — a contact sheet over the real footage, before spending time on rendering.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| **storyboard** | One frame per beat at its key moment over the real footage (`edit/out/storyboard.jpg`), about a minute; only changed frames are redone. The editor approves it (`fzv approve <folder> storyboard`); `render` waits for that (rule R2). |
| **render**   | Renders changed clips only, in parallel, with retries. Overlay clips are transparent WebM; compose clips are opaque MP4.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **finish**   | Synthesises the SFX, adds music if asked, mixes to −14 LUFS / −1 dBTP, composites over the untouched footage at its own frame rate, encodes in cached chunks, writes the final MP4 (+`.srt` if subtitles are on).                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **verify**   | Checks duration, frame rate, size and loudness, grabs frames at every cut into`edit/out/verify.jpg`, and refreshes the review page (final video, a frame per beat, to confirm). |

### 3.3 With Claude Code

Open **this folder** in VS Code with the Claude Code extension and type `/edit-video videos/loop-control` (or ask in plain words).
Claude runs ingest and plan, fills the beat sheet, opens the review page and waits for your approval; then writes the spec,
builds, validates, makes the storyboard and waits again; then renders, finishes, verifies, opens the page with the final video and
lists anything to confirm (code it rebuilt, corrections it made, names it heard indistinctly).

| Shortcut (`.claude/skills/`) | What it does |
|---|---|
| `/edit-video <folder or file> [notes]` | Start or continue an edit (makes `videos/<name>/` and `prompt.md` when given files) |
| `/review [folder]` | Where a video stands; opens its review page |
| `/change <folder> beat 7: …; 7:41: …` | Changes by beat number or time, before or after rendering |
| `/approve <folder> beats\|storyboard` | The editor's approval (typed or copied from the review page) |

`.claude/settings.json` pre-approves the safe steps (`bin/fzv`, `bin/setup`, tests, copies into and edits inside `videos/`), so
Claude Code doesn't ask "Allow?" at every step. Personal overrides go in `.claude/settings.local.json` (git-ignored).

## 4. The prompt

The prompt is free text with a few optional `Key: value` lines. Global defaults live in `global/defaults.yaml`; **the prompt can
override any of them for its video**, and every override is logged in `edit/decisions.md`.

```markdown
# Loop Control Statements
Brand: career-orbit
Style: default
Subtitles: off
Music: off
Recording: show
- Focus on break; make the three example programs the highlight.
- Use a short cutaway for the traffic analogy, with a police officer and a car.
- No name card.
```

| Field              | Default          | Values                                                                                                                                                                                              |
| ------------------ | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `# Title`        | folder name      | the final file is`<Title> - Edited.mp4`                                                                                                                                                           |
| `Brand:`         | `career-orbit` | any kit in`global/brand/` (`fzv brands`): `career-orbit`, `fuzentrix`                                                                                                                       |
| `Style:`         | best per video   | free words:`sketch edit` (whiteboard-marker look, only on request), `minimal`, `more diagrams`…                                                                                              |
| `Subtitles:`     | `off`          | `on`, `on, Telugu + English` (burned in, plus an `.srt`)                                                                                                                                      |
| `Music:`         | `off`          | a track id or mood from`fzv music list`, e.g. `calm-piano` (18 LU under the voice), `calm-piano, low` (22), `…, high` (14)                                                                 |
| `SFX:`           | `on`           | `minimal` (no entrance pops/swishes), `off`, `library only` (no synthesised fallback)                                                                                                         |
| `Presenter box:` | `on`           | the bottom-right instructor sits in a rounded brand box (rough cuts: a frame with the plate patched outside it; raw footage: the cut-out is clipped to it);`off` to leave the instructor unframed |
| `Recording:`     | `show`         | `reference` (never show it; rebuild it as animation, §5.2), `reference, exact` (rebuild without corrections)                                                                                   |
| `Review:`       | `on`           | the editor approves the beat sheet and the storyboard before build and render; `off` (quick tests), `beats` or `storyboard` (only that one) |
| `Mode:`          | detected         | `overlay` (editor's rough cut) or `compose` (raw / green-screen footage)                                                                                                                        |

**Free text** steers everything else: what to emphasise, characters and props by plain name ("a student at a laptop", "a car
drives past"), short cutaways, things to avoid. A prop the library doesn't have is listed under "props to add" in
`decisions.md` instead of being improvised.

## 5. Screen recordings

A recording is always a separate file next to the raw cut. Ingest aligns it to the raw cut by audio (confidence ≥ 0.6, or give
the offset in the prompt), finds its content area (the IDE or browser without plain margins, brand plate or bars), and saves a
keyframe for every settled screen state (a line finished, output printed) with its raw-cut time in `edit/recref/<id>/`
(`index.json`, PNGs, contact sheets). `fzv look <folder> rec1 640-656` tiles finer steps.

### 5.1 `Recording: show` (default)

The whole recording is shown, never cropped or zoomed, in a branded window in the free area (template `recording-window`), with a
step tracker in its title bar and highlight boxes on the recording. Explanations sit outside the window, joined by wires.

### 5.2 `Recording: reference`

For recordings that aren't good enough to show. The recording is **never shown** (rule E8); it becomes the reference for an
animated rebuild that follows the instructor:

- **Code** goes into a code card that types each line when it was typed in the recording (or on the word the instructor says).
- **Output** comes from actually running the code with the input the instructor typed (§6), timed to the recording.
- **Explanations** sit outside the code card and terminal.

### 5.3 Corrections (reference mode)

Because the code is rebuilt, mistakes in the recording can be corrected. **Default `tidy`:** typos, spacing/formatting and false
starts are fixed in the rebuilt code. The card keeps the code exactly as typed in `recorded:`; the build then

- lists every change in `edit/decisions.md` ("Corrections from the recording"),
- runs **both** versions and checks the output is the same. A correction that changes what the program prints fails validation
  (rule E9) unless the spec says why in `logic_fix:`, and then it is listed under "to confirm" with both outputs.

`Recording: reference, exact` copies the code exactly as typed instead.

Example: Loop Control's recording types `for i in range(1,n+1):`; the tidy card shows `for i in range(1, n+1):`, `decisions.md`
records the change, and both versions print the same `20 / 1 … 10`.

## 6. Code and program output

- **Code cards** (`code-card`): dark editor cards, JetBrains Mono, syntax colours from the brand kit, typing in spoken chunks,
  highlights, an active-line bar, a Run press. Languages: Python, C, C++, Java, JavaScript (from `lang:` or the tab title).
- **Program output is the real output** (rule E7). A terminal never has hand-typed output; it uses
  `exec: {code: <card id>, stdin: [...]}`. At build time `fzv` runs the card's code and prints exactly what a terminal shows:
  the output, typed input echoed where the program read it, errors and tracebacks in red. It scrolls like a real terminal.
  Timing: `exec.times` (a time per line, e.g. as the instructor reads them) and `exec.pace` (0.05 s ≈ a real program).
- Runs time out after 10 s and are cached in `edit/runs/`. A program that fails stops the build unless `exec.expect_error: true`
  (for videos about errors). Python input is echoed exactly; C/C++/Java/JavaScript run on a pseudo-terminal.
- **Explanations always sit outside** code cards and terminals, as notes joined by wires (rule L6).

## 7. House rules

The one-page list is [global/RULES.md](global/RULES.md); `fzv validate` checks every automatic rule (`global/rules.yaml`). The
prompt may override any rule for its video (logged in `decisions.md`). The ones that matter most:

- **Content and timing come from the video's own audio**, never from a script. Never cut or extend the footage. No outros.
- **Rough cuts: the instructor is untouched.** No halo, circle, blur or move; graphics only in the empty space (the bottom-right brand box is the one exception, a setting).
  **Raw footage:** focus on the instructor in the intro, then one fixed spot (bottom right).
- **Show the process, in sync** (V1–V3): when the instructor explains how something works, the screen *shows it happening*
  (data flies into the database, `"20"` converts to `20`, `range` emits 1…n, a request travels and returns), each step on the word
  that names it. Text cards label; animations explain. A new visual roughly every 8–12 s; at most 15 s of words-only screen.
- **Always something to see:** plate stretches are never empty for more than 2 s; every studio close-up carries a light graphic.
- **Never cluttered:** at most 4 blocks, 40 words and 12 code lines on screen at once (1 block / 12 words in studio shots).
- **Explanations outside code**; **recordings shown whole**; **output is real** (E7); **reference recordings never shown** (E8);
  **corrections never change the output silently** (E9).
- **Off unless the prompt asks:** subtitles, music, the sketch style.
- **Sounds on the visual events, never repeated** (A5): the team's SFX library first, files rotating per category; synthesised fallback varies every take.
- **Bottom-right instructor in a rounded brand box** in rough cuts and raw footage (setting `presenter.corner_box`; prompt `Presenter box: off`).
- Anything shown that wasn't said outright is listed under **"to confirm"**.

## 8. Styles and templates

| Family                     | When                                                                              | Examples                                                                                                                                                                                                                       |
| -------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Core**             | always                                                                            | titles, headers, agenda, definition, cards, chips, summary, flowchart, cutaway, studio tag, name card                                                                                                                          |
| **Code & Execution** | always, for any code                                                              | code-card, terminal (`exec`), note, tiles, trace, variables, problem, recording-window                                                                                                                                       |
| **Explainer**        | wherever a process is explained                                                   | data-flow, process-flow, type-convert, range-gen, request-flow, icon-grid, form-card, db-tables, hub, mockup, callouts, checklist, big-word, scene (dark, compose mode)                                                        |
| **Registry**         | ready-made animations from the HyperFrames registry (31 installed, 448 available) | `hf` mounts any installed item: constellation-hub, radial-surround, count-up, chart-story, code-morph, code-diff, hw-arrow, hw-callout-circle, marker-highlight, cursor-annotate, comparison-split… (`fzv registry list`) |
| **Kinetic**          | key terms (12 words max)                                                          | term-reveal, rule-stack, contrast                                                                                                                                                                                              |
| **Diagram**          | structure                                                                         | blocks, flowchart                                                                                                                                                                                                              |
| **Data**             | numbers                                                                           | table, bars, counter, curve                                                                                                                                                                                                    |
| **Props**            | analogies                                                                         | prop, prop-move, prop-scene                                                                                                                                                                                                    |
| **Sketch**           | only when the prompt asks                                                         | sketch-board, sketch-draw, sketch-text, sketch-list, sketch-flow, sketch-mark                                                                                                                                                  |
| **Presenter**        | compose mode                                                                      | the instructor's poses (at most two moves)                                                                                                                                                                                     |

Which template shows which explanation: [global/styles/explainer/STYLE.md](global/styles/explainer/STYLE.md). The phrases that should
trigger an animation live in [global/concepts.yaml](global/concepts.yaml) (the plan brief lists every moment found; validate reports
uncovered ones). `fzv templates` lists all 55 with their parameters (cards in `global/templates/<family>/`); style guides are in
`global/styles/<family>/STYLE.md`. A worked spec for a full 15-minute video is [examples/loop-control/edit.yaml](examples/loop-control/edit.yaml).

## 9. Brand kits

`global/brand/_shared/house.yaml` holds what every brand shares: fonts (Outfit, Inter, JetBrains Mono, Caveat for sketch), type
scale, shapes, motion timings, code colours, audio levels, layout. Each `global/brand/<id>/brand.yaml` adds its logos and colours;
`fzv build` turns the merged kit into CSS variables (`--fz-*`) that every template, icon and prop uses, so a video recolours by
changing one line in the prompt.

- **Career Orbit** (the LMS, default): the LMS app's navy ramp + the logo's teal.
- **Fuzentrix Education** (the parent brand).

Brand sheets and logo variants: [global/brand/README.md](global/brand/README.md).

## 10. Icons, props, characters and music

### 10.1 What's included (free, commercial use, no credit needed)

| Library                       | Count                                                                                                                                                                                                             | Source and licence                                                                    | Where                                               |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------- |
| **Icons**               | 114 (35 in-house + 79 Tabler)                                                                                                                                                                                     | [Tabler Icons](https://tabler.io/icons) 3.49.0, MIT                                    | `runtime/icons.svg`; use `icon: rocket`         |
| **Props**               | 90 (10 in-house + 80 Fluent Emoji)                                                                                                                                                                                | [Microsoft Fluent Emoji](https://github.com/microsoft/fluentui-emoji), flat style, MIT | `global/props/`                                   |
| **Characters**          | 30 (4 in-house + 26 Fluent Emoji, medium skin tone)                                                                                                                                                               | same                                                                                  | `global/props/` (`kind: character`)             |
| **Music**               | `calm-piano` (Satie, Gymnopédie No. 1, Musopen recording) · `focus-piano` (Bach–Siloti, Prelude in B minor)                                                                                                | Wikimedia Commons; public domain / CC0                                                | `global/music/`                                   |
| **Registry animations** | 31 (constellation hub, radial surround, counters, charts, code morph/diff/highlight, terminal run, flowchart, handwritten arrows/circles/boxes/underlines, marker highlight, cursor annotate, comparison split…) | [HyperFrames registry](https://github.com/heygen-com/hyperframes), Apache-2.0          | `global/registry/`; `fzv registry add` for more |
| **Sound effects** | 97: Kenney Interface Sounds + UI Audio (90: clicks, ticks, blips, pops, confirmations, errors, glass dings, swishes, soft key taps) and 7 soft whooshes from Freesound | CC0 | `global/sfx/`; `fzv sfx list`, `fzv sfx audition` |

Every imported prop is **recoloured to the brand variables** (neutrals and skin tones stay natural), so the whole library matches
the brand and recolours per brand. Licence notices: [global/licences/](global/licences/README.md). Catalogues: `fzv props list`,
`fzv music list`, and the icon names in the plan brief.

**Using them:** name them in the prompt ("a police officer stops a car", "add calm music"); the planner maps words to assets by
their tags. In the spec: `prop: {asset: police-car, ...}`, `prop-move`, `prop-scene` (several props with enter/move/react/exit),
`icon: rocket` in agenda rows, chips and cards; `Music: calm-piano, low` in the prompt (music sits ~24 dB under the voice, ducked
further while the instructor speaks, looped to the video's length).

### 10.2 Sound effects

The library ships with a calm, teaching-style set (97 CC0 sounds). **Listen and prune:** `bin/fzv sfx audition` writes one MP3 per category to `global/sfx/_audition/` (with a numbered list); drop any sound with `bin/fzv sfx remove swish:3 pop:7` (category:number) or by file. Add more with `fzv sfx add`: a single file or a whole folder. Categories are guessed from file names (`whoosh`,
`swoosh`, `pop`, `click`, `ding`, `success`, `error`, `typing`…) or set with `--category`:

```bash
bin/fzv sfx add ~/Downloads/ui-sounds/ --source "<pack url>" --licence "<licence>"     # whole folder, categories guessed
bin/fzv sfx add swoosh_03.wav --category whoosh --source "<url>" --licence "<licence>"  # one file
bin/fzv sfx list                                                                       # what each category has
```

Categories: `whoosh` (scene change), `swish`, `pop`, `blip`, `tick` (element entrances), `click` (button press), `ding`, `good`,
`bad` (results), `thud`, `impact` (big reveal), `chime`, `type` (typing). Several files per category rotate. Files are loudness-
normalised, then placed at the house level for their category. Categories you haven't filled use fzv's synthesised sounds
(`sfx.fallback: synth` in `global/defaults.yaml`) or stay silent (`fallback: none`, or `SFX: library only` in a prompt).

**Variety, not silence (rule A5):** every visual event keeps its sound; what changes is that no identical sound repeats back to
back. Library files rotate per category (bring several per category for the best result), and synthesised sounds for missing
categories are a slightly different take each time (pitch, level). Only sounds landing on top of each other (within 0.35 s) are
dropped. `SFX: minimal` turns entrance sounds off; density settings live in `global/defaults.yaml` → `sfx`.

### 10.3 Adding more

Fuzentrix videos are commercial and have **no credits roll**, so every asset must allow commercial use and edits without
attribution: **CC0, MIT, ISC, Apache 2.0, public domain, or a paid licence.** Avoid CC BY / BY-SA (credit required), anything
NC/ND, and "free for personal use". The import commands refuse NC/ND/personal licences and warn on attribution licences.

| Need              | Free, no credit                                                                                                            | Paid                                     |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| Icons             | Tabler (MIT), Lucide (ISC), Phosphor (MIT), Material Symbols (Apache 2.0), Devicon (MIT, tech logos)                       | IconScout, Envato Elements               |
| Props, characters | Fluent Emoji (MIT), Noto Emoji (Apache 2.0), Open Peeps (CC0, hand-drawn: good for sketch), unDraw (free licence)          | Envato Elements, Freepik Premium, Blush  |
| Music             | Wikimedia Commons public-domain / CC0 recordings (e.g. Musopen), Pixabay Music (Pixabay Content License; download by hand) | Epidemic Sound, Artlist, Envato Elements |

Not suitable: OpenMoji and Twemoji (credit required), Kevin MacLeod / incompetech (CC BY), YouTube Audio Library (meant for
YouTube uploads). Licence terms change: check the source's current terms when you download.

```bash
# a prop or character (SVG): cleaned, recoloured to the brand, scaled, registered with its source and licence
bin/fzv props add police-car.svg --id police-car --kind prop --tags "vehicle police emergency" --recolor \
    --source "https://github.com/microsoft/fluentui-emoji/tree/main/assets/Police%20car" --licence MIT
# a line icon (24-grid SVG, e.g. Tabler or Lucide); drawn in the text colour
bin/fzv icons add rocket.svg --id rocket --source "https://tabler.io/icons/icon/rocket" --licence MIT
# a music track
bin/fzv music add track.mp3 --id upbeat-tech --mood upbeat --source "<page url>" --licence "Pixabay Content License"
```

`scripts/fetch_free_assets.py` shows the whole starter set as code (lists, pinned versions, sources) and is safe to re-run.

## 11. Revising a delivered video

```bash
bin/fzv revise "videos/loop-control" "7:41 make the break note larger; beat 12: show the output one line at a time"
```

Editors write these on the review page (under a beat, or at a paused moment of the final) and paste them via **Copy for Claude**
(`/change …`). `revise` turns beat numbers into the beat's time, maps each time to the scenes on screen, prints the speech around
it and logs the request in `edit/revisions.md`. A changed beat row needs a new approval (the request is it), and the changed
storyboard frames are shown before rendering. Claude edits only those scenes in `edit.yaml`; `build → validate → render → finish → verify` then redo only
the clips and encode chunks that changed (content-hash caches), and the request's status in `revisions.md` is updated.

## 12. Command reference

| Command                                                                                   | What it does                                                                                                                                        |
| ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fzv doctor`                                                                            | Machine check: render workers, low-memory mode, transcription backend, hardware encoder                                                             |
| `fzv edit <folder> [--prompt TEXT] [--force]` | All stages in order; stops where Claude or the editor has to act (beat sheet, edit.yaml, approvals); `--force` renders despite validation problems |
| `fzv ingest <folder> [--raw FILE] [--no-transcribe] [--force] [--rekey]`                | Files, audio, transcript, shots, safe zones, recordings + keyframes; compose mode keys the instructor (`--rekey` after changing `key:` options) |
| `fzv plan <folder> [--check]` | Write`edit/plan_brief.md` (waits for the transcript) and draft `edit/beats.yaml` / check `edit.yaml` (anchors, templates) |
| `fzv beats <folder> [--redraft]` | Check the beat sheet (coverage, templates, sync words; notes for words-only stretches and concept moments), write `beat_sheet.md`, refresh the review page |
| `fzv approve <folder> beats\|storyboard [--note TEXT]` | Record the editor's approval (`edit/approvals.md`); a later change needs a new one |
| `fzv build <folder>`                                                                    | Resolve anchors, run programs, compile clips, write`decisions.md`                                                                                 |
| `fzv preview <folder> <clip> <t,t,…>`                                                  | Contact sheet of a clip over the real footage (`edit/out/preview_<clip>.jpg`)                                                                     |
| `fzv validate <folder>`                                                                 | House-rule checks (`edit/validate.json`)                                                                                                          |
| `fzv storyboard <folder> [--all]` | One frame per beat over the real footage (`edit/review/storyboard/`, `edit/out/storyboard.jpg`); only changed frames redone |
| `fzv review <folder> [--open]` | The review page `edit/review/index.html`: beats, storyboard, final, to confirm, change requests |
| `fzv render <folder> [--only ids] [--workers N]`                                        | Render changed clips (parallel, cached, retried)                                                                                                    |
| `fzv finish <folder>`                                                                   | SFX + music + mix, composite, encode, final MP4 (+`.srt`)                                                                                         |
| `fzv verify <folder>`                                                                   | Duration, fps, size, loudness;`edit/out/verify.jpg`                                                                                               |
| `fzv revise <folder> "<m:ss or beat N request>…"` | Map times and beat numbers to scenes; log in`edit/revisions.md` |
| `fzv look <folder> raw\|rec1 t0-t1 [--fps F] [--box x,y,w,h]`                            | Tile frames of the raw cut or a recording over a raw-cut time range                                                                                 |
| `fzv templates [--refresh]`                                                             | Template catalogue (`--refresh` after changing templates)                                                                                         |
| `fzv props list` · `fzv props add …`                                                | Props and characters library / import (§10.2)                                                                                                      |
| `fzv icons add …` · `fzv music list` · `fzv music add …`                        | Icon and music import, track list                                                                                                                   |
| `fzv sfx list` · `fzv sfx add <file\|folder> [--category C] --source URL --licence L` · `fzv sfx audition` · `fzv sfx remove <cat:n\|file>…` | The SFX library: list, add, listen, prune |
| `fzv registry search <words>` · `fzv registry add <name…>` · `fzv registry list` | HyperFrames registry animations (vendored into`global/registry/`, mounted with `hf`)                                                            |
| `fzv brands`                                                                            | Brand kits                                                                                                                                          |

## 13. What ends up in a video's folder

| Path in`<folder>/edit/`               | Contents                                                                                               |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `project.yaml`                        | Detected facts (raw cut, fps, mode, layout slots, safe zones, recordings) and stage history            |
| `transcript.jsonl`, `audio/`        | Timed transcript; extracted audio, SFX cues, mix                                                       |
| `cuts.json`, `zones.json`           | Shots to the exact frame; the instructor's safe zones                                                  |
| `recordings.json`, `recref/`        | Recording offsets, content areas; keyframes and contact sheets                                         |
| `plan_brief.md`                       | What Claude reads to write the spec                                                                    |
| `beats.yaml`, `beat_sheet.md`, `approvals.md` | The beat sheet (Claude fills it, the editor approves it), the same as a table, and every approval with the editor's words |
| `edit.yaml` → `edit.resolved.yaml` | The edit spec, and the same with every time in seconds and every terminal's real output                |
| `decisions.md`                        | Brand, styles, why, overrides, corrections,**to confirm**, props to add                          |
| `runs/`                               | Cached program runs                                                                                    |
| `built/`, `sections/`               | Compiled clips and their renders                                                                       |
| `validate.json`, `validate_cache/`  | Rule-check report; DOM samples per clip (by content hash), so re-validation only samples changed clips |
| `out/`                                | `verify.jpg`, `footage.jpg`, `storyboard.jpg`, previews, `look_*.jpg`, encode chunks |
| `review/` | The review page `index.html` with its frames: footage, storyboard, final per beat, and the footage every 10 s |
| `revisions.md`                        | Change requests after delivery and what was done                                                       |
| `_prev/`                              | The previous final video                                                                               |

## 14. Speed and machines

`fzv doctor` sizes everything to the machine: render workers = min(sections, cores ÷ 2, free RAM ÷ ~1 GB) with HyperFrames'
low-memory mode when only one fits; transcription uses mlx-whisper on Apple Silicon and faster-whisper or whisper.cpp elsewhere; the
encoder is VideoToolbox, NVENC, QSV or libx264. Graphics render at 25 or 30 fps; overlay delivery keeps the source frame rate
(graphics are composited over the untouched footage), compose delivery is at the graphics rate (the whole picture is rendered).
`fzv finish` lists each encode chunk as `cached` or `encoding`.

Rough times on an 8 GB M1 (one render worker): ingest of a 15-minute rough cut ≈ 13 min (transcription runs alongside shot
detection), rendering ≈ 5–7 graphics fps, finish ≈ a few minutes; keying a 4-minute green-screen take ≈ 15–25 min. Re-runs after a
revision only redo what changed. Everything slows sharply when the machine is swapping: keep free memory for the pipeline.

## 15. Troubleshooting

| Symptom                                                         | Fix                                                                                                                                                                                       |
| --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `no Chrome found`                                             | `npx hyperframes render --help` once, or set `FZV_CHROME`                                                                                                                             |
| Anchor not found / wrong word                                   | Use more words (`"@if i equal to"`), `"@phrase#2"` for a later occurrence, or seconds from the transcript                                                                             |
| `[L2] … overlaps the instructor`                             | Move or shrink the block into a layout slot from the plan brief                                                                                                                           |
| `[L10] … blocks / words`                                     | Fewer things at once: end the previous block (`until`) or group items                                                                                                                   |
| `[V1]` / `[V2]` text-only section or stretch                | Show the process: pick an Explainer / Code / Diagram template for what is being explained (STYLE guide,`global/styles/explainer/`)                                                      |
| `[V3]` advice: a concept moment isn't shown                   | Add the suggested template on that word, or say in`decisions` why not; extend `global/concepts.yaml` if a phrase misfires                                                             |
| Music too loud or too soft                                      | `Music: <track>, low` / `high` in the prompt, or `music.rel_lufs` in `global/defaults.yaml`                                                                                       |
| `[E7] output is written by hand`                              | Use`exec: {code: <card>, stdin: [...]}` on the terminal                                                                                                                                 |
| `[E9] the correction changes the program's output`            | Keep the recorded code, or explain in`logic_fix:` (goes to "to confirm")                                                                                                                |
| `program exited with 1` at build                              | The code card doesn't run as written: check it against the recording's keyframe (or set`expect_error: true`)                                                                            |
| Recording`needs_offset`                                       | Low audio match; give`offset:` for it under `recordings:` in `edit.yaml`                                                                                                            |
| Compose mode: desk, laptop or plant travels with the instructor | `key: {cut_below: <y>, exclude: [[x, y, w, h]], exclude_poly: [[[x, y], …]]}` in `edit.yaml` (`fzv look <folder> raw 100-100` helps find coordinates), then `fzv ingest --rekey` |
| Render crash ("detached Frame")                                 | Retried automatically; if it persists,`fzv render --workers 1`                                                                                                                          |
| Wrong mode detected                                             | Add`Mode: overlay` or `Mode: compose` to the prompt and run `fzv ingest` again                                                                                                      |
| Transcription or rendering crawls                               | The machine is short of memory (`memory_pressure`, `sysctl vm.swapusage`): close VMs, browsers and other heavy apps. An interrupted transcription resumes where it stopped            |
| A transcript chunk repeats one word ("colon colon colon…")     | Whisper loop: fixed automatically by the temperature fallback and repeat clean-up; anchor on nearby words                                                                                 |

## 16. Working on the system

```
docs/SYSTEM_DESIGN.md   the design: decisions, rules, styles, templates, spec format, build status
CLAUDE.md               how Claude edits and revises videos in this repo
fzv/                    pipeline (Python): ingest, layout, align, recref, transcribe, spec, execute, build, render,
                        validate, audio, finish, verify, revise, compose/keyer, assets, cli
runtime/                browser side: lib.js, templates/*.js (HTML/GSAP), base.css, icons.svg, vendor/gsap
node/sample.mjs         headless-Chrome helper: catalogue, DOM sampling for validate, stills
global/                 defaults.yaml, rules.yaml, RULES.md, brand/, styles/, templates/, props/, music/, licences/
scripts/                fetch_free_assets.py
examples/               reference edit specs (loop-control)
tests/                  pytest suite (tests/_work/ is scratch, not committed)
```

- **Templates:** `runtime/templates/*.js`; each `FZ.register(meta, fn)` documents its parameters. Run `bin/fzv templates --refresh`.
- **Brand values:** `global/brand/`. **Defaults:** `global/defaults.yaml`. **Rules:** `global/rules.yaml` + `fzv/validate.py`.
- **Tests:** `.venv/bin/python -m pytest` (`FZV_E2E=1` for the end-to-end render) before committing.
