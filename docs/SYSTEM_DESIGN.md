# Fuzentrix Video Workflow: System Design

**Status:** building. **Updated:** 2026-10-25. **Owner:** Fuzentrix content team.
**Repository:** `Automations/fuzentrix-video-editing-automations/` (this document is `docs/SYSTEM_DESIGN.md`).
**Reference implementations:** `Automations/video-edits/` (`dbms-trail`, `durga-trail`, `loop-control`).

This document describes `fzv`, a standalone tool that turns an instructor's video into a finished, on-brand teaching video with motion graphics.
- Every video reads the same **global** rules, styles and templates. When several brand kits exist, the video's prompt names the one to use (Career Orbit by default).
- Each video can carry its own **prompt** that steers or overrides those defaults.
- After delivery, a video can be fixed at specific timestamps with further prompts.

The document also records the decisions behind the design and the lessons from the first three edits.

---

## 1. Goals

1. **Consistency by default.** One brand kit (colours, fonts, logo, motion, sound) and one template library for every video, with no per-video styling unless a prompt asks for it.
2. **Variety where the content needs it.** A fixed set of style families (§7). The planner picks the families that suit each video; a prompt can pick for it.
3. **Prompt-driven.** Each video can have its own custom prompt, and timestamped change requests after delivery.
4. **Everything in the video's folder.** Raw cuts in, edited video and all working files out, side by side.
5. **Runs on any machine.** No stage assumes particular hardware. The tool detects the machine and sizes parallel work, transcription and encoding to fit it (§5.1); faster machines simply finish sooner.
6. **Cheap revisions.** A change at one timestamp re-renders and re-encodes only the section it falls in.

**Not goals:** cutting or re-ordering the instructor's footage, outros, and showing content that was not said in the video. Subtitles and music are **off by default**; a video's prompt can switch them on (§3.3).

## 2. Decisions

| # | Decision | Why |
|---|---|---|
| D1 | **Standalone tool**, git repo `Automations/fuzentrix-video-editing-automations/`, CLI `fzv`. Not a content-kit skill. | Faster to iterate. It can be packaged as a skill later (§15, phase 6). |
| D2 | **HyperFrames** (HTML + GSAP), version pinned at **0.8.162**. | Proven on all three videos, including transparent overlays. Content-kit ADR 0006 (Revideo) still governs the content kit; this tool deliberately differs. |
| D3 | **Brand look:** one shared house style (typography, shapes, motion, sound), with colours and logo per brand. Career Orbit (the LMS, main brand) merges the LMS app's navy ramp with its logo's teal; Fuzentrix Education (the parent) uses its logo and website colours (§6). | Every video feels like one family; only logo and colours change between brands. |
| D4 | **Audio only.** Content and timing come from the video's own Telugu + English audio. No script, Master Script or PDF. | The user's instruction; the video must match what was actually said. |
| D5 | **Rough cuts stay as the editor made them.** The instructor's positions and cuts are never changed; graphics are a transparent overlay. | The user's feedback on Loop Control. |
| D6 | **Graphics render at 25 fps; delivery keeps the source frame rate** (50 fps for current footage). | Halves render time; the instructor's footage keeps full motion. |
| D7 | **One folder per video** holds the raw cuts, the prompt, the final video and an `edit/` folder with every working file (§3.2). | The user's folder model. |
| D8 | **Global files define the defaults:** brand kit, rules, styles, templates, defaults (§3.1). | One place to change the look of every future video. |
| D9 | **A video's prompt can override anything** for that video, including global rules. Every override is logged in `edit/decisions.md`. | The user's choice; the log keeps overrides visible. |
| D10 | **No outros or end cards.** The editors' intro animation already brands every video. | The user's instruction. |
| D11 | **Style families** (§7): a fixed base on every video, content-driven families picked per video, and Sketch only on request. | Variety per video without losing the house look. |
| D12 | **The instructor stays visible most of the time.** Short full-screen cutaways are allowed when a moment needs one (§8.2, L3). | The user's choice. |
| D13 | **Device-agnostic.** Worker counts, transcription backend and encoder are chosen from the machine at run time; nothing is tuned to one computer (§5.1). | The user's instruction: build the workflow, not for a device. |
| D14 | **Brand per video, chosen by the prompt.** With several kits in `global/brand/`, the prompt names one; otherwise `defaults.yaml` (Career Orbit). | The user's instruction. |
| D15 | **Subtitles and music are opt-in.** Off by default; the prompt can switch either on, with options (§3.3, §9a, §9b). | The user's instruction. |
| D16 | **Screen recordings are separate files.** Raw cuts never contain them; the tool aligns each recording to the raw cut and positions it on screen (§4.1). | The user's instruction. |
| D17 | **Never a plain-instructor stretch.** There is always something to look at: during studio shots a light studio-layer graphic sits in the free part of the frame, and plate stretches never sit empty (rule L4). | The user's instruction. |
| D18 | **A clutter budget.** At any moment the screen carries a limited amount of information (rule L10). | The user's instruction. |
| D19 | **Characters and props come from a shared library** of brand-styled assets, used through templates (§9c). | Consistent look; no one-off drawings per video. |
| D20 | **A recording can be kept as reference only.** With `Recording: reference` in the prompt the recording is never shown; its code and output are rebuilt as animations, timed from the recording's keyframes and the instructor's words (§4.2). | The user's instruction: some recordings are not good enough to show. |
| D22 | **Reference rebuilds may correct the recording.** Typos, spacing and false starts are fixed by default (`tidy`); every change is logged, and a change that alters the program's output must be explained and confirmed (rule E9). `Recording: reference, exact` copies the code as typed. | The user's instruction: mistakes in recordings can be corrected when the video doesn't show them. |
| D23 | **Free starter library.** Icons from Tabler (MIT), props and characters from Fluent Emoji (MIT, recoloured to the brand), music from public-domain / CC0 recordings; every asset records its source and licence (§9d). | The user chose free sources; the videos carry no credits roll. |
| D24 | **Show the process, in sync.** When the instructor explains how something works, the screen shows it happening (data flowing in, a value converting, numbers being generated, a request travelling), each step on the word that names it. Text cards label; animations explain (rules V1–V3, Explainer family). | The user's feedback on the first test edits: "only text popups… not interacted and synced to explanations". |
| D25 | **SFX come from the team's library, varied.** `global/sfx/` (added with `fzv sfx add`) is used first, files rotating per category; synthesised sounds fill missing categories with a different take each time. Every visual event keeps its sound; only sounds stacked on top of each other are dropped (rule A5). | The user: sounds were *repeated*, not too many; "we provide sfx libraries, should use them". |
| D26 | **Bottom-right instructor in a box, in both modes.** Raw footage: the cut-out is clipped to a rounded brand box. Rough cuts: the same frame is drawn around the instructor's corner area and the strips outside it are covered with the exact plate image the editor used, so the instructor looks cut by the box. A setting (`presenter.corner_box`, prompt `Presenter box: off`). | The user's rule, "can modify anytime"; the earlier DBMS edit they preferred framed the instructor this way. |
| D27 | **Music is audible.** When the prompt asks for music, the bed sits a fixed loudness below the voice (−18 LU; "low" −22, "high" −14), measured per track, with gentle ducking. | The first music test was effectively silent (−28 dB plus hard ducking). |
| D28 | **Animations from the HyperFrames registry.** 448 open-source (Apache-2.0) blocks and components; `fzv registry add` vendors them into `global/registry/` and the `hf` template mounts them in a box with their variables and word-anchored cues (§7.4). | The user: "get the animation templates also, or take from web". |
| D21 | **Output on screen is the program's real output.** The build runs the code shown on screen and prints exactly what a terminal shows (rule E7). | The user's instruction: outputs printed exactly how the code outputs them. |

## 3. Organisation: global files and video folders

### 3.1 Global files (shared by every video)

Everything global lives in the repo:

```
fuzentrix-video-editing-automations/       git repo
  README.md                                setup and everyday commands
  docs/SYSTEM_DESIGN.md  docs/adr/         this document and later decisions
  fzv                                      CLI entry point (wraps `python -m fzv`)
  fzv/                                     pipeline code (Python 3.11+): ingest, plan, build, preview, validate, render, finish, verify, revise
  runtime/                                 browser runtime: lib.js (timeline + helpers), templates/<family>/*.js, gsap.min.js
  node/                                    headless-Chrome helpers: SFX cue collection, DOM sampling for validate, stills
  global/
    defaults.yaml                          defaults: brand, style mix, cutaway limits, clutter budget, subtitles off, music off, output naming
    rules.yaml  RULES.md                   the rules (§8): machine-checkable defaults
    brand/                                 brand kits (see global/brand/README.md)
      _shared/     house.yaml (fonts, type, shapes, motion, code colours, audio, layout) + fonts/ + plate/ + brand sheet
      career-orbit/  brand.yaml (extends _shared/house.yaml) + logo set + brand sheet
      fuzentrix/     brand.yaml (extends _shared/house.yaml) + logo set + brand sheet
    styles/<family>/STYLE.md               the fixed look of each style family (§7)
    templates/<family>/<template>.md       template cards: parameters, footprint, rules (§9)
    props/                                 characters and props library + manifest.yaml (§9c)
    music/                                 licensed music tracks + manifest.yaml (§9b; empty until tracks are added)
  examples/                                reference edit specs (loop-control)
  tests/
```

Changing a global file changes the defaults for every **future** render. Delivered videos are not re-rendered automatically.

### 3.2 A video's folder

```
<video folder>/                            e.g. "durga trail videos/"
  LOOP CONTROL ST ROUGH CUT .mp4           raw cut(s) exactly as delivered: never modified, never moved
  screen recording .mp4                    separate screen recordings, if any
  prompt.md                                this video's custom prompt (optional)
  Loop Control Statements - Edited.mp4     the final video
  edit/                                    everything the tool makes
    project.yaml                           which file is the main cut, recordings, mode, brand, fps, output name, stage status
    cuts.json  zones.json  recordings.json  transcript.jsonl
    edit.yaml  edit.resolved.yaml          the scene spec (§10), with anchors and with resolved times
    decisions.md                           styles chosen and why; every prompt override of a global rule; items to confirm
    revisions.md                           every timestamped change request and what changed
    sections/  built/  comp/  out/  audio/
    _prev/                                 earlier versions of the final video (never deleted)
    README.md                              content map and how to re-render
```

**Identifying the files:**
- The **raw cut** is the file with speech across most of its length.
- A **screen recording** is a separate file: little or no speech, or audio that matches a stretch of the raw cut. Raw cuts never contain recordings (D16).
- If it's ambiguous, the tool asks.

### 3.3 The video prompt (`prompt.md`)

The prompt is free text. It may also be passed on the command line, and is then saved to `prompt.md`. The planner reads it alongside the global defaults.

```markdown
# Loop Control Statements
Brand: career-orbit                  # which kit in global/brand/ (default: defaults.yaml → career-orbit)
Style: default                       # e.g. "sketch edit", "minimal", "more diagrams"
Subtitles: off                       # default off. "on" (English), or "on, Telugu + English", with a position
Music: off                           # default off. e.g. "calm-focus, low" (a track id or mood from global/music)
Recording: show                      # default show. "reference": never show it; rebuild code and output as animation, fixing typos (§4.2). "reference, exact": no fixes
- Focus on break; make the three example programs the highlight.
- Use a short cutaway for the theatre analogy, with a car and a police officer character.
- No name card.
```

**Precedence:** the video prompt beats `global/defaults.yaml` and `global/rules.yaml`, for that video only (D9). Each override is written to `edit/decisions.md`, so a reviewer can see where a video departs from house style.

**Asking for characters and props:** name them in plain words ("a car drives past", "a student at a laptop"). The planner maps them to library assets (§9c). Anything not in the library is listed in `decisions.md` as "props to add" instead of being improvised.

## 4. Inputs and modes

| Mode | When | What happens to the instructor | Example |
|---|---|---|---|
| **overlay** | An editor's rough cut, layout done: full-screen studio shots plus plate shots with the instructor in a corner. Screen recordings, if any, arrive as separate files. | Nothing (D5). Plate-layer graphics fill the empty space; light studio-layer graphics accompany studio shots (L4). | `loop-control` (899 s) |
| **compose** | Raw instructor footage (green screen or grey studio), plus optional screen recordings. | Keyed out, placed on the brand plate, positioned by rule L4. | `durga-trail`, `dbms-trail` |

The mode is detected at ingest and recorded in `project.yaml`; a prompt can force it.

### 4.1 Screen recordings (separate files)

When a video comes with a raw cut **and** a screen recording, the tool edits them together.
1. **Align.** Cross-correlate the recording's audio with the raw cut's audio to find its offset. If the recording has no audio, use the offset given in the prompt, or ask.
2. **Measure.** Find the recording's content area: the IDE or browser panel, without its margins. A margin is only cut when it matches a known background: the raw cut's plate, a brand plate image, or a uniform colour (desktop, black bars); logos and plate swooshes are tolerated. Anything else keeps the full frame. Highlight boxes are given in recording pixels.
3. **Position.** Place the whole recording, never cropped (L7), in a branded window in the free area of the plate shots, sized as large as the instructor's safe zone allows (the window fits the slot's width **and** height, aspect kept). During the instructor's studio shots the recording window is hidden; the studio layer carries a light graphic instead (L4).
4. **Point.** Highlight boxes, step tracker and notes with wires work in recording coordinates (template X06).
5. **Keyframes.** Ingest also saves a keyframe of every settled screen state (a line finished, output printed) with its raw-cut time, plus contact sheets, in `edit/recref/<id>/`. Frames are compared one second apart, which cancels a blinking caret. `fzv look <folder> recN t0-t1` tiles finer steps.

The Durga trail and Loop Control Example 2 used exactly this path.

### 4.2 Recording as reference only (`Recording: reference`)

When a recording is not good enough to show, the prompt says so and the recording becomes a reference (D20). It is never shown (rule E8); the edit rebuilds it:
- **Code:** a `code-card` per program, from the recording's last keyframe for that program. Each line types when it appears in the recording (keyframe times), or on the word the instructor says it with. Run is pressed when the instructor clicks Run.
- **Corrections (D22):** with the default `tidy`, the card fixes the recording's typos, spacing/formatting and false starts, and keeps the code as typed in `recorded:`. The build diffs the two, logs every change in `decisions.md` ("Corrections from the recording"), and runs both versions: if the output differs, validation fails (E9) unless `logic_fix:` explains the change, which then goes to "to confirm" with both outputs. `Recording: reference, exact` copies the code as typed.
- **Output:** a `terminal` with `exec: {code, stdin}`. The build runs the program with what the instructor typed into it and prints exactly what a terminal shows (rule E7), timed with `exec.times` / `exec.pace` to the recording. IDE banners such as "=== Code Execution Successful ===" are not program output.
- **Explanations:** notes outside the code card and terminal, as always (L6).

**Runners:** Python runs with a shim that echoes `input()` where it is read (deterministic). C, C++, Java and JavaScript run on a pseudo-terminal; each stdin line is sent once the program goes quiet. Runs time out after 10 s and are cached in `edit/runs/`. A program that exits with an error fails the build unless `exec.expect_error: true` (for videos about errors).

Verified on Loop Control Example 2: rebuilt from the recording's 16 keyframes, the card types `range(1,n+1)` exactly as in the recording (the hand-made card had added a space), and the terminal prints `20` at 643.0 s and the real output 1–10 at 654.5 s.

## 5. Architecture and stages

```
 video folder ──►  1 ingest ─► 2 plan ─► 3 build ─► 4 preview ─► 5 validate ─► 6 render ─► 7 finish ─► 8 verify ─► final MP4
 (raw cuts,           │       (Claude)      ▲                                              │
  prompt.md)          │          ▲          └──────────────── revise <time> "<change>" ◄───┘
                      ▼          │
                 global files: brand kit · rules · defaults · style families · templates
```

Only **plan** and **revise** are creative work, done by Claude. Every other stage is deterministic code: repeatable and cheap in tokens.

`fzv edit "<video folder>" [--prompt "…"]` runs stages 1–8 in order. Each stage also has its own command.

| # | Command | What it does | Output (in `edit/`) | Scales with |
|---|---|---|---|---|
| 1 | `fzv ingest` | Identify the main cut and recordings. Probe; extract audio (16 kHz for speech recognition, 48 kHz for the mix). Classify every frame as studio, plate, corner or recording, and refine each cut to the exact frame. Measure the instructor's safe zone. Align recordings. Transcribe in the background from minute 0 (§12.3). | project, cuts, zones, recordings, transcript | audio length; transcription runs in the background |
| 2 | `fzv plan` | Claude reads the prompt, the compact transcript, the cut summary, defaults, rules, the style catalogue and the template catalogue. It writes `edit.yaml` and `decisions.md`. | edit.yaml, decisions.md | video length (Claude) |
| 3 | `fzv build [sections]` | Resolve word anchors, compile sections from templates, syntax-check. | built/*.html, edit.resolved.yaml | seconds |
| 4 | `fzv preview <section> <times>` | Snapshot the overlay and composite it onto the real footage frames. | out/preview_*.jpg | sections previewed |
| 5 | `fzv validate` | Run the rule checks (§8) on DOM boxes sampled every 0.5 s, with any prompt overrides applied. | validate.json (blocks the render on failure) | video length |
| 6 | `fzv render [sections]` | Transparent WebM per section: parallel workers, skips studio intervals, cached by content hash. | out/*.webm | frames ÷ workers (workers sized to the machine) |
| 7 | `fzv finish` | Collect SFX cues and synthesise them; mix with two-pass loudnorm; composite per section, hardware encode, concat. The previous final moves to `_prev/`. | the final MP4 | video length; hardware encoder if present |
| 8 | `fzv verify` | Duration, fps, frame counts, frames on both sides of every cut, loudness and peak; verification sheet. | out/verify.jpg, verify.json | video length |

**Timestamped changes after delivery:**

```
fzv revise "<video folder>" "7:41 make the break note larger; 12:05 the code should say i == 8"
```

1. Each timestamp is mapped to its section and scene.
2. Claude edits only those scenes in `edit.yaml`.
3. Only the affected sections are rebuilt, re-rendered and re-encoded.
4. The change is logged in `revisions.md` and the new final is verified.

Turnaround depends on one section's length, not the whole video.

### 5.1 Device-agnostic execution

`fzv doctor` runs at the start of every job (and on its own) and writes `edit/machine.json`. Nothing else in the tool assumes a particular computer.

| Choice | How it's made | Override |
|---|---|---|
| Render workers | `min(sections, cores ÷ 2, (free RAM − 2 GB) ÷ RAM per worker)`, where RAM per worker is measured on the first section. HyperFrames low-memory mode when only one worker fits. | `defaults.yaml` or the video prompt |
| Transcription backend | mlx-whisper on Apple Silicon; faster-whisper (CUDA or CPU) or whisper.cpp elsewhere. Same model family and settings (§12.3). | `defaults.yaml` |
| Encoder | Hardware if available (VideoToolbox, NVENC, Quick Sync, VAAPI), otherwise libx264. Same quality target either way. | `defaults.yaml` |
| Background jobs | Transcription overlaps planning prep; previews and validation run while renders queue. | always on |

**Platforms:** macOS, Linux and Windows (WSL), wherever Python 3.11, Node 20, ffmpeg and headless Chrome run. Stage times and worker counts are recorded in `verify.json`, so each machine's real numbers become visible over time.

## 6. Brand kit

The brand kits live in `global/brand/` (see its README). `_shared/house.yaml` holds everything that is the same for every brand: fonts, type scale, shapes, shared colours, code colours, motion, audio and layout. Each `<brand>/brand.yaml` extends it with its logo set, colour roles, corner-logo setup and name-card label. `base.css` and the SFX levels are generated from the merged result; no template hard-codes a colour, font or duration. Each kit ships a one-page brand sheet (`<brand>_brand_sheet.png`).

### 6.1 Career Orbit (the LMS; default brand)

The kit is complete in `global/brand/career-orbit/` (see its README and `career-orbit_brand_sheet.png`).

**Logo set:** stacked (the master, rebuilt from footage because no original exists), horizontal and icon. Each comes in colour, on-dark and white, as SVG and transparent PNGs.
- **On-dark:** white CAREER, teal ORBIT, and the icon with its dark tones lifted so the navy part of the ring stays visible.
- **In videos:** the horizontal logo is the corner logo, 40 px high in a white pill.

**Colours:** a merge of two sources, so logo, LMS app and videos look like one product.
- the LMS app's navy ramp (`fuzentrix_ui/src/styles/theme.css`) for text, surfaces and buttons
- the logo's teal as the accent

```yaml
colors:
  navy:        "#0D274C"   # LMS brand-900: headings and body text
  action:      "#1B53A2"   # LMS brand-600: buttons, links, small-text emphasis (7.4:1 on white)
  action-hover: "#174484"  # LMS brand-700
  teal:        "#16BBC8"   # logo: THE accent (icons, progress, active states, accents on dark). Never text on white
  orbit-text:  "#30809F"   # logo "ORBIT": title emphasis at heading sizes
  slate:       "#52657D"   line: "#DDE9F6"   tint: "#EFF5FB"   surface: "#FFFFFF"   surface-warm: "#FBFAF7"
  deep:        "#07152B" / "#081830"   # LMS brand-deep / brand-950: dark panels
gradients:
  orbit: ["#164673", "#145695", "#1790B4", "#16BBC8"]   # the logo's ring: hero titles, brand moments
  deep:  ["#0D274C", "#081830"]                          # the LMS sidebar: dark panels, cutaway backgrounds
roles: { text: navy, title-emphasis: orbit-text, small-emphasis: action, accent: teal, action: action, highlight: warning (amber) }
```

The wordmark keeps its own navy `#1C2F58` inside the logo artwork only. The LMS app's interface fonts (Avenir, Source Sans 3) are not used; videos use the house fonts.

### 6.2 Fuzentrix Education

The kit is complete in `global/brand/fuzentrix/` (see its README). Typography, shapes, motion and sound come from the house style; only these differ from Career Orbit.

**Logo set:** every file comes from the original vector (`MAIN LOGO.svg` from the landing site), re-cropped or recoloured but never redrawn.
- stacked (master), horizontal and icon
- each in colour and on-dark (white)
- SVG plus transparent PNGs

The horizontal lockup is the video corner logo, 40 px high in a white pill.

```yaml
colors:
  ink:        "#0D274C"   # logo gradient (bottom), website primary: text
  brand-blue: "#3381C2"   # logo gradient (top): accent, title emphasis (large text only)
  brand-mid:  "#205487"   # gradient midpoint: emphasis in small text (7.8:1 on white)
  coral:      "#CF501B"   # website accent: calls to action
  orange:     "#D9731D"   # website focus ring: code highlight boxes and wires
  cyan:       "#38BDF8"   # website accent: accents on dark
  slate:      "#5C6B80"   surface: "#F3F6FA"   tint: "#ECF6FB"   line: "#E1E7EF"
gradients:
  logo: ["#0D274C", "#3381C2"]   # bottom to top
```

The older slide values (navy `#062858`, blue `#0A59C8`, Aptos) are replaced by these. The kit is used when a video's prompt sets `Brand: fuzentrix`.

## 7. Style families

All families use the brand kit. A family fixes the **look and motion grammar**; the templates (§9) fix the **layout**. That is what keeps every video consistent while letting each video use a different mix.

### 7.1 Catalogue

| Family | Availability | Used for | Look and motion |
|---|---|---|---|
| **Core Explainer** | **Always** (the base) | titles, headers, agenda, definitions, concept and type cards, analogies, flowcharts, summaries | White cards on the plate, Swiss grid, Outfit and Inter, orbit-blue accents; slide and fade entrances, pops for chips |
| **Code & Execution** | **Always, for any code** | syntax, code typed to the instructor's dictation, line highlights, notes with wires, loop traces, variable boxes, output terminal, screen-recording window | Dark navy editor cards, JetBrains Mono with ligatures off, syntax palette; explanations always outside the code (rule L6) |
| **Explainer** | **Always, wherever a process is explained** | data flowing into a database, processing, type conversion, range generation, request/response, searching many records, a system and its operations, app screens, records filling in, pain points and benefits | Brand nodes and cards; things move (packets travel, chips fly in, values convert, numbers emit, a magnifier scans); each step on its word; dark brand scene for big moments in compose mode. See `global/styles/explainer/STYLE.md` |
| **Kinetic Typography** | Content-driven | the defined term, a rule, a key takeaway, "X vs Y" | Big Outfit 800–900, word-by-word or line-by-line reveal, orbit gradient on the keyword. **12 words at most and never running speech**, so it can't turn into subtitles |
| **Technical Diagram** (blueprint / isometric) | Content-driven | architecture, client–server, database tables and ER diagrams, memory and stack models, request flow | A light blueprint grid on white (stays with the plate); blocks, arrows and line icons in brand blues; isometric blocks for systems; parts assemble and arrows draw on |
| **Data Storytelling** | Content-driven | counts, comparisons, growth, Big-O, query results | Flat bars, lines and tables in brand colours; count-ups; values build as the instructor says them |
| **Sketch / Whiteboard** | **Only when the prompt asks** (for example "sketch edit") | analogies and stories, or a whole video in sketch style | Whiteboard marker: a clean white board, navy `#1C2F58` and teal `#16BBC8` / `#30809F` marker strokes, red and green for right and wrong, Caveat for labels; strokes draw themselves on with a slight hand wobble; people and objects from one fixed open-licence line-art set |

**Not in the library** (low fit for lessons; see Appendix A): 3D scenes, character animation, glitch or synthwave, pixel art, hype product-launch edits. A prompt that asks for one is flagged in `decisions.md` as needing new templates.

### 7.3 Show the process (rules V1–V3)

Text cards (header, card, definition, chips) only label an idea. Whenever the instructor explains how something works, the planner
shows it happening with an Explainer, Code, Diagram, Data or Props template, in step with the words:
- **Every step on its word.** Each moving part has its own `at`, anchored to the word that names it.
- **Rhythm:** a new visual roughly every 8–12 s; at most 15 s of words-only screen (V2); every section over 30 s has an animated explanation (V1).
- **Concept moments:** `global/concepts.yaml` maps spoken phrases to the templates that show them ("type conversion" → `type-convert`, "1 to n" → `range-gen`, "store the data" → `data-flow`, "log in" → `mockup`…). `fzv plan` lists the moments found in the transcript; `fzv validate` reports uncovered ones as advice (V3). The team extends the lexicon.
- **Concrete examples:** the instructor's own examples first; illustrative details (sample rows, a portal screen) are allowed and listed under "to confirm".
- **Reference:** the earlier hand-made DBMS edit (`video-edits/dbms-trail/`) is the bar: about one new visual every 9 s, each one moving.

### 7.4 Registry animations (D28)

- **Source:** the HyperFrames registry (github.com/heygen-com/hyperframes, Apache-2.0): 448 items, 210 blocks (complete scenes,
  usually 1920×1080) and 238 components (elastic, take variables). `fzv registry search` browses it; `fzv registry add` vendors an
  item into `global/registry/<name>/` with its fonts and scripts (CDN scripts are downloaded into `global/registry/_assets/vendor/`
  so renders never need the network) and records its variables in `manifest.yaml`.
- **Mounting:** `- hf: {item, at, until, box, vars, cues}`. Build writes a static host carrying the item's composition id (items
  register their timeline under it, so one mount per item per clip), the brand tokens (`--fg`, `--accent`, `--brand`,
  `--font-display`…) and the variables; `cues` (word anchors) become the item's `cues` variable in seconds from its start. Components
  are made open-ended on install (they hold their last frame until `until`); blocks keep their own length and are scaled into the box.
- **Rendering:** each worker gets hard-linked copies of exactly the items a clip mounts (HyperFrames won't read sub-compositions through
  a symlink, and unused ones confuse its entry check).
- **Starter set (31):** browser-device-stage, chart-story, chat-message, code-diff, code-highlight, code-morph, code-terminal-run,
  comparison-split, conic-progress-ring, constellation-hub, count-up, cursor-annotate, data-chart, flowchart, grid-card-assemble,
  hw-arrow, hw-box-label, hw-callout-circle, hw-pipeline, hw-underline, kinetic-type-swap, marker-highlight, mk-line-graph,
  mk-progress-stat, mk-specs-list, mk-usage-arc, notification-stack, offset-path-traveler, press-ripple, radial-surround, state-chip-rail.
  Paste-only snippets (no root composition id) and blocks that load their assets asynchronously (the Lottie walker) are not mountable.
- **Validation:** validate sees each mount's box (role `block`) but not its inner content; preview it.

### 7.2 How the planner chooses (the defaults)

**Every video uses:**
- the base families (Core Explainer, plus Code & Execution wherever there is code)
- the same brand kit, bug and type scale

**Content-driven families are added only when the content calls for them:**
- **Kinetic Typography:** at most one moment per section, for the term being defined or the takeaway the instructor stresses.
- **Technical Diagram:** when the instructor explains structure: how parts connect, or where data lives.
- **Data Storytelling:** when the instructor gives numbers, comparisons or growth.

**Guard rails:**
- At most **two non-base families per section**.
- A family keeps its look for the whole video.
- The choices and their reasons go in `decisions.md`.

**Typical mapping from lesson moment to style:**

| Moment | Default | With "sketch edit" in the prompt |
|---|---|---|
| Opening (after the editor's intro animation) | Core title + name card (if the instructor introduces themself) | Sketch title |
| Agenda | Core agenda | Sketch list |
| Definition | Core definition card; Kinetic for the key term | Sketch card |
| Real-world analogy | Core analogy kit, or a short cutaway if it needs the whole frame | Sketch scene drawn on |
| Types / kinds | Core type cards | Sketch cards |
| How it works | Core flowchart or Technical Diagram | Sketch flow |
| Example program | Code & Execution: problem and plan, code card, trace, terminal; recording window or embedded-recording highlights | Same: code stays in Code & Execution |
| Numbers, results, comparisons | Data Storytelling | Sketch chart |
| Summary | Core summary | Sketch summary |
| Ending | Nothing extra (no outro) | Nothing extra |

Code is never drawn in sketch style. Readability of code always wins.

## 8. Rules

These are the global defaults. A video's prompt may override any of them (D9); overrides are logged in `decisions.md`. Check types:
- **auto:** `fzv validate` enforces it and it blocks the render.
- **lint:** HyperFrames lint.
- **review:** shown in the plan or verify output for a person to confirm.

### 8.1 Editorial

| ID | Rule | Check |
|---|---|---|
| E1 | Content and timing come only from the video's own audio. Never compare against or correct from a script. | review |
| E2 | Keep the original timing: never cut, trim, re-order or extend the instructor's footage. No outro. | auto (output duration = source duration) |
| E3 | Subtitles are off by default; only the prompt switches them on (§9a). Otherwise on-screen text is titles, labels, code and short notes; a note is 16 words at most. | auto |
| E4 | The brand kit is the one the prompt names; without one, `defaults.yaml` (Career Orbit). | auto |
| E5 | The name card appears only when the instructor introduces themself in the audio, using the name they say. Never guess from file or folder names. | auto (anchor on the self-introduction) |
| E6 | Anything shown that wasn't said outright (code rebuilt from dictation, a name heard indistinctly) is listed under "to confirm" in `decisions.md` and in the delivery message. | auto |
| E7 | Program output on screen is the program's real output: a terminal prints through `exec`, which runs the code card's code at build time. Hand-written output needs `manual: <reason>`. | auto |
| E8 | With `Recording: reference` the recording is never shown (no `recording-window`); its code and output are rebuilt (§4.2). | auto |
| E9 | A rebuilt code card may correct the recording (typos, spacing, false starts), but a correction that changes the program's output needs `logic_fix:` and is confirmed; with `Recording: reference, exact` the card must match the recording. | auto (both versions are run) |

### 8.2 Layout

| ID | Rule | Check |
|---|---|---|
| L1 | **Overlay mode:** the instructor's footage is untouched. No halo, circle, frame or blur on or behind them; the one exception is the bottom-right brand box (D26, setting). | auto (those templates are rejected in overlay mode) |
| L2 | No graphic intersects the instructor's safe zone in `zones.json`, except during a cutaway (L3). | auto (DOM boxes every 0.5 s) |
| L3 | **Cutaways:** the instructor is visible most of the time. A full-screen cutaway is allowed only when a moment needs the whole frame: at most **12 s each**, **10% of runtime in total**, never over a studio highlight shot. The instructor returns exactly as in the rough cut. | auto (limits) + review (need) |
| L4 | **Never a plain-instructor stretch.** Plate-layer graphics fill the free area of plate shots and never leave it empty for more than 2 s (scene changes excepted). During studio shots, a light **studio-layer** graphic (a keyword, the step in progress, a short takeaway) sits in the studio frame's free area; plate-layer graphics are hidden there. Both layers switch frame-exactly at each cut. | auto (empty-stretch check, 1 s samples) |
| L5 | **Compose mode:** instructor focus in the intro, then one fixed position (bottom right) until the end. At most 2 position changes. The bottom-right pose sits in a rounded brand box (setting `presenter.corner_box`, D26); graphics keep clear of the box. | auto |
| L6 | Explanations sit outside code cards and terminals. Inside them, only highlights, the caret and the active-line bar. | auto |
| L7 | Screen recordings are shown whole, scaled to fit; never cropped or zoomed into a part. Point at things with highlight boxes, wires and notes. | auto |
| L8 | Content margins: 96 px left; header band at y 78–180; brand bug at the top right; nothing within 40 px of the edge. | auto |
| L9 | One idea on screen at a time. The previous scene leaves before or as the next one enters. | review |
| L10 | **Clutter budget** at any moment: at most 4 content blocks (for example a code card, its output and two supporting visuals; header and logo don't count; a list, tile row or diagram counts once), 40 words of non-code text, 12 code lines, and 1 animated focus point. Studio-layer graphics: 1 block, 12 words. | auto (sampled every 0.5 s) |

### 8.2a Visual explanation

| ID | Rule | Check |
|---|---|---|
| V1 | Every section of 30 s or more has at least one animated explanation (a template that shows a process, not only words). | auto |
| V2 | At most 15 s of plate time where only text templates are on screen (`visuals.max_text_only_s`). | auto |
| V3 | Every concept moment in the transcript (`global/concepts.yaml`) is shown with a matching template around its word, or `decisions` says why not. | advice |

### 8.3 Typography and motion

| ID | Rule | Check |
|---|---|---|
| T1 | Only brand fonts and type-scale sizes. Body ≥ 26 px; code in cards ≥ 30 px; recordings at ≥ 0.85 scale. | auto |
| T2 | Code font with ligatures off. | auto |
| T3 | No text overflow and no one-word last lines in cards. | auto |
| T4 | At most two emphasised phrases per card, in `orbit-text` or a semantic colour. | review |
| M1 | Durations and eases come from brand motion tokens only. | auto |
| M2 | Animate transform and opacity only, never `left`/`top`/`letter-spacing`. | lint |
| M3 | Every visual change is anchored to a spoken word and lands within ±0.3 s of it. | auto + review |
| M4 | No continuous motion on or around the instructor. | auto |

### 8.4 Audio and delivery

| ID | Rule | Check |
|---|---|---|
| A1 | The voice is untouched except a 70 Hz high-pass. | auto |
| A2 | Subtle SFX only, tied to visual events, peaks ≥ 20 dB below the voice. Music only when the prompt asks for it (§9b), audible but under the voice (D27). | auto |
| A5 | SFX from the team's library first (`global/sfx/`), files rotating per category; synthesised fallback varies every take (pitch, level); only sounds within 0.35 s of another are dropped; `SFX: minimal` drops entrance sounds, `SFX: off` drops all (§9e). | auto |
| A3 | Final mix at −14 LUFS integrated, −1 dBTP. | auto |
| D1 | 1920×1080 at the source fps; H.264 High, yuv420p; AAC 320k at 48 kHz; faststart; metadata stripped. | auto |
| D2 | The final goes in the video folder as `<Title> - Edited.mp4`. Earlier versions move to `edit/_prev/` and are never deleted. | auto |
| D3 | `edit/README.md`, `decisions.md` and the verification sheet ship with every final. | auto |

## 9. Template library

Each template is a parameterised component:
- **JS** builds the DOM and timeline tweens from brand tokens.
- **CSS** comes from the family's `style.css`.
- **A `.md` card** lists its parameters, footprint and the rules it satisfies.

The library lives in `runtime/templates/*.js`. Each template carries its own documentation (`FZ.register(meta, fn)`); `fzv templates --refresh` regenerates `global/templates/catalogue.json` and one card per template.

| Template | Family | Use |
|---|---|---|
| `agenda` | Core | Numbered list of cards, each entering when said (agenda, plan, steps) |
| `bug` | Core | Brand logo, top right, in a white pill |
| `captions` | Core | Subtitles |
| `card` | Core | A single text card with an optional icon and label: a takeaway, a fact, a question |
| `chips` | Core | A row of short keyword or question chips |
| `cutaway` | Core | Full-frame backdrop for a short full-screen moment (rule L3: at most 12 s each, 10% of runtime) |
| `definition` | Core | One-sentence definition in a card; phrases underline as they are said |
| `flowchart` | Core | Nodes and arrows, with an optional marker that walks the path |
| `header` | Core | Section label and title, top left (the header band) |
| `image` | Core | Place an image file from the video's assets (e.g |
| `name-card` | Core | Instructor name card |
| `studio-tag` | Core | Light graphic for the instructor's studio shots (rule L4): a keyword, the step in progress or a short takeaway, in the studio frame's free area |
| `summary` | Core | Recap rows with optional keyword chips at the end of a row |
| `title-hero` | Core | Opening title over the intro shot: label, two-line title (second line in the brand gradient), optional focus chip |
| `type-cards` | Core | 2-4 concept cards side by side (e.g |
| `code-card` | Code | Dark editor card |
| `note` | Code | An explanation card outside the code, joined to its target by a wire (rule L6) |
| `problem` | Code | Problem statement card; phrases colour as they are read out |
| `recording-window` | Code | The whole screen recording in a branded window, never cropped or zoomed (rule L7); step tracker in the title bar; highlight boxes in recording coordinates |
| `terminal` | Code | Output panel; `exec` runs the code card's program and prints its exact output (E7), scrolling like a real terminal |
| `tiles` | Code | A row or grid of value tiles that change state (now / ok / bad / skip / dim), e.g |
| `trace` | Code | Loop trace panel: the variable box, the condition check with its True/False result, per iteration |
| `variables` | Code | Variable boxes that update as the code runs (name = value) |
| `contrast` | Kinetic | 'X vs Y' split: two titles with a short line each and a 'vs' between |
| `rule-stack` | Kinetic | Two or three short lines that stack into a rule or takeaway; the last line is emphasised |
| `term-reveal` | Kinetic | The key term or a takeaway built word by word (12 words at most) |
| `blocks` | Diagram | Labelled blocks with icons and arrows on a light blueprint grid (architecture, client-server, request flow) |
| `table` | Diagram | A data table (database rows, comparisons) |
| `bars` | Data | Bar chart that builds as values are said |
| `counter` | Data | A number that counts up to its value, with a label |
| `curve` | Data | Line chart that draws itself (growth, Big-O) |
| `prop` | Props | Place a character or prop from the library; optional idle motion and reactions |
| `prop-move` | Props | Move a prop along a path (a car driving past, a ball rolling), with easing and optional speed lines |
| `big-word` | Explainer | One giant word letter by letter (the term being introduced: DBMS, DATABASE), with an optional expansion line. Once per term, when it is first named |
| `callouts` | Explainer | Short chips that pop up at free positions as each point is said, with a gentle float (pain points, benefits, reactions). Screen coordinates |
| `checklist` | Explainer | Rows that tick off one by one as they are said (benefits, requirements, a recap). The last row may be a highlighted conclusion |
| `data-flow` | Explainer | Items (chips with icons) fly into a container (database, table, folder, server, cloud) as they are named; the container fills and counts |
| `db-tables` | Explainer | A database frame with its tables appearing inside, each with rows |
| `form-card` | Explainer | A record / form / receipt card whose field values type in as they are said |
| `hub` | Explainer | A central badge (the system) with spokes to what it does, each appearing as named |
| `icon-grid` | Explainer | A grid of icons standing for many items (students, records, files) with a count; optional magnifier scanning row by row, a found cell, or a cross |
| `mockup` | Explainer | A browser window or phone with app screens that change as they are described: typing into fields, pressing buttons, a loading spinner, results |
| `process-flow` | Explainer | Inputs box -> process (spinning icon) -> output card: dots travel through when the process runs |
| `range-gen` | Explainer | A range generator emits its numbers one by one into slots (first ones paced, the rest quickly), optionally stopping at a break value |
| `request-flow` | Explainer | Nodes with big icons; packets travel along curved links when they are sent (request -> processing -> result back). Optional blocked direct path |
| `scene` | Explainer | Compose mode only: switch the background behind the instructor to a dark brand scene for a big moment (the hero reveal, a fun fact); text turns light for its duration |
| `type-convert` | Explainer | A value changes type: a quoted value with its type badge goes through the conversion function and comes out converted |
| `prop-scene` | Props | A small staged scene: a ground line (road or desk) with several props, each with its own entrance and moves |
| `sketch-board` | Sketch | A clean whiteboard panel for a sketch scene (inside the free area, or full frame inside a cutaway) |
| `sketch-draw` | Sketch | Draw a library prop or character as marker outlines, stroke by stroke; optional light colour fill afterwards and a handwritten label |
| `sketch-flow` | Sketch | Hand-drawn boxes and arrows (coordinates relative to the box); each part draws on when said |
| `sketch-list` | Sketch | Hand-lettered list; each item writes on with a drawn tick or bullet when said |
| `sketch-mark` | Sketch | A hand-drawn annotation over anything on screen: circle, underline, arrow, box, tick or cross |
| `sketch-text` | Sketch | Handwritten text that writes itself on (left-to-right wipe) |
| `presenter` | compose only | Keyed instructor with poses: wide, close, side-right, side-left, corner (bottom right) |

Mode is enforced per template: templates for the instructor area (`presenter`, halos, frames) cannot be used in overlay mode.

### 9a. Subtitles (opt-in)

- **Off by default.** The prompt switches them on: `Subtitles: on`, optionally with a language and position.
- **Source:** the transcript, segmented into lines of at most 42 characters and 2 lines, 1–6 s each, timed to word timestamps.
- **Telugu + English speech:** the English-mode transcript is romanised and imperfect, so subtitles always produce a `captions.srt` for review, listed under "to confirm" before burn-in.
- **Placement:** inside the brand's safe area, never over code or the instructor's face. Brand fonts, white on a translucent ink bar.
- **Sidecar:** a separate `.srt` is always written next to the final, so the LMS can show captions without burning them in.

### 9b. Music (opt-in)

- **Off by default.** The prompt switches it on with a track id or a mood (`Music: calm-focus, low`).
- **Library:** `global/music/` holds licensed tracks with a `manifest.yaml` (id, mood, bpm, licence, file). Only tracks listed there are used. It is empty until tracks are added.
- **Mix:** each track's loudness is measured once; the bed sits 18 LU under the voice (`Music: …, low` → 22, `high` → 14), gently ducked while the instructor speaks (ratio 3), with 2 s fades. The final loudness rule (A3) still applies.
- **Included:** `calm-piano` (Satie, Gymnopédie No. 1) and `focus-piano` (Bach–Siloti, Prelude in B minor), public domain / CC0.

### 9e. Sound effects (rule A5)

- **The team's library:** `global/sfx/<category>/` with `manifest.yaml`, added with `fzv sfx add <file|folder> --source … --licence …` (category guessed from file names, or `--category`). Categories: `whoosh` (scene change), `swish`, `pop`, `blip`, `tick` (entrances), `click` (button press), `ding`, `good`, `bad` (results), `thud`, `impact` (big reveal), `chime`, `type` (typing). Several files per category rotate; each file is RMS-normalised, then placed at the category level.
- **Fallback:** categories missing from the library use fzv's synthesised sounds (`sfx.fallback: synth`) or stay silent (`none`, prompt `SFX: library only`).
- **Variety:** templates record a cue for every event and every cue keeps its sound; library files rotate per category and synthesised fallbacks differ per take, so the same sound never repeats back to back. Optional density settings (`minor_gap_s`, `whoosh_gap_s`, `max_per_min`) stay available in `defaults.yaml`.

### 9c. Characters and props

Characters (people, a police officer, a student) and props (a car, an ambulance, a laptop, a server, a book) come from **one shared library**, `global/props/`, so every video draws them the same way.

**The library:**
- **Manifest:** `manifest.yaml` lists each asset: id, kind (character or prop), tags, style (`flat` for the Core family, `line` for Sketch), source and licence, and its anchor point.
- **Brand-ready:** assets are SVGs coloured only with brand variables (`--fz-ink`, `--fz-accent`, `--fz-tint`, skin and hair tones), so they recolour automatically per brand.
- **Starter set:** a starter set is drawn in-house (no licence questions).
- **Growing it:**
  - Open-licence sets (for example Open Peeps, CC0, for Sketch people) can be imported after their licence is checked and recorded.
  - Generated images are allowed only through a fixed style prompt and a review step, and recorded as such.

**Using it in a video:**
- The prompt names characters and props in plain words; the planner picks library ids and a template: `prop`, `prop-move` or `prop-scene`.
- **Motion vocabulary (fixed):** enter (pop, slide, draw-on), idle (gentle bob, blink), move (along a path, with easing and optional speed lines), react (shake, tick, cross) and exit.
- Nothing outside the library is improvised. Missing assets go to "props to add" in `decisions.md`, and `fzv props add` imports a new SVG after a style check (brand variables only, size and anchor set).

### 9d. Where assets come from

**Included (D23):** 114 icons (35 in-house + 79 Tabler 3.49.0, MIT), 90 props and 30 characters (14 in-house + 106 Fluent Emoji flat, MIT; people in the medium skin tone), all recoloured to brand variables; music `calm-piano` (Satie, Gymnopédie No. 1, Musopen, public domain) and `focus-piano` (Bach–Siloti, Prelude in B minor, CC0), both from Wikimedia Commons. `scripts/fetch_free_assets.py` holds the lists, pinned versions and sources; licence notices are in `global/licences/`. Recolouring keeps neutrals, dark hair and skin tones natural and maps every other colour to the nearest brand variable (CIE Lab distance).

The videos are commercial (the LMS) and carry **no credits roll**, so every third-party asset must allow commercial use and edits **without attribution**: CC0, MIT, ISC, Apache 2.0, or a paid licence. Avoid CC BY / BY-SA (credit required), anything NC or ND, and "free for personal use". Every import records its source URL and licence; `fzv` refuses NC/ND/personal licences and warns on attribution licences.

| Need | Free, no attribution | Paid (one subscription covers a lot) |
|---|---|---|
| **Icons** (line, 24-grid, like ours) | Tabler Icons (MIT), Lucide (ISC), Phosphor (MIT), Material Symbols (Apache 2.0); Devicon (MIT) for language/tool logos | IconScout, Envato Elements |
| **Props** (vehicles, objects, places) | Microsoft Fluent Emoji, flat style (MIT); Google Noto Emoji (Apache 2.0); SVG Repo (filter to CC0/MIT; licences vary per asset) | Envato Elements, Freepik Premium, Adobe Stock |
| **Characters** | Open Peeps (CC0; hand-drawn, right for Sketch); unDraw (free licence, no attribution; set the accent colour to the brand teal before downloading) | Envato Elements character kits, Blush, Storyset or Freepik with Premium (the free tier needs attribution) |
| **Animated characters** | LottieFiles free animations (Lottie Simple License) | LottieFiles / Envato Lottie packs. Needs a `lottie` template (not built yet) |
| **Music** | Pixabay Music (Pixabay Content License). YouTube Audio Library is meant for YouTube uploads; check its terms before using tracks on the LMS | Epidemic Sound (business plan), Artlist, Envato Elements, Musicbed |
| **SFX** | not needed: `fzv` synthesises its SFX (deterministic, no licence) | Epidemic Sound, Envato Elements |

A **brand mascot** (a Career Orbit character drawn once by an illustrator, in poses) would give every video the same recurring character; it goes into `global/props/` like any other asset.

**Importing:**
- `fzv props add <file.svg> --id police-car --kind prop --tags "vehicle police" --recolor --source <url> --licence MIT` cleans the SVG, maps every fixed colour to the nearest brand variable (neutrals and skin tones are kept natural), scales icon-grid art to prop size and records source and licence in `global/props/manifest.yaml`.
- `fzv icons add <file.svg> --id rocket --source <url> --licence MIT` adds a line icon to `runtime/icons.svg`, drawn in the text colour.
- `fzv music add <file.mp3> --id calm-focus --mood calm --source <url> --licence "Pixabay Content License"` copies the track into `global/music/` and lists it; a prompt then uses it with `Music: calm-focus, low`.

## 10. The edit spec (`edit/edit.yaml`)

`edit.yaml` is the per-video spec. Claude writes it in the plan stage and edits it in revise; a person may edit it too. Times are **word anchors** resolved against `transcript.jsonl` at build time, so nobody looks up seconds by hand.

```yaml
video: loop-control
title: Loop Control Statements
brand: career-orbit
mode: overlay
styles: [core, code, kinetic]                # chosen by the planner or the prompt; reasons in decisions.md
sections:
  - id: s05
    range: [279.10, 473.88]                  # from cuts.json; sections break inside studio shots
    scenes:
      - header: { label: Example 1, title: "Stop the loop when *i* reaches *6*", at: "For i in range" }
      - code-card:
          id: ex1
          lines: ["for i in range(1, 11):", "    if i == 6:", "        break", "    print(i)"]
          type: [{ line: 1, at: "For i in range" }, { line: 2, at: "if i equal to" }]
      - trace:
          code: ex1
          iterations:
            - { i: 1, val: "value store", check: "if i equal to@2", result: "not equal to 6", print: "print of i" }
            - { i: 6, val: "6 and A value", result: "Condition is true" }
      - note-wire: { target: ex1:3, nt: "`break`", nd: "runs → the loop **exits**", at: "Break statement is executed", until: "+6.5" }
```

**Quiet ranges:** `quiet: [[start, end, reason]]` marks deliberate clean stretches, for example the editor's own logo animation. Rule L4 is not applied there, and the reasons are listed in `decisions.md`.

**Anchor syntax:**
- `"phrase"`: the first match after the previous anchor.
- `"phrase@2"`: the second match.
- `279.6`: absolute seconds.
- `"+0.3"`: relative to the previous anchor.

**Matching** is fuzzy and case-insensitive, and tolerates Telugu romanised by the English-mode transcript (up to 30% character edits). An unresolved anchor fails the build and lists the nearest candidates.

## 11. Claude's role

| Stage | Claude does | Claude does not |
|---|---|---|
| plan | Reads the prompt, transcript and cut summary; splits the video into sections; picks style families and templates; writes on-screen text from what was said; sets anchors; writes `decisions.md` | Write coordinates, colours or animation code |
| revise | Turns timestamped requests into `edit.yaml` changes for the affected scenes only | Touch other sections or generated HTML |
| review | Reads preview and verification sheets and reports problems | Approve output without showing the sheets |

**Context hygiene** (the first run used about 24 M input tokens):
- One fresh session per video.
- Load only: the prompt, RULES.md, the style and template catalogues, the brand summary, a compact transcript and the cut summary.
- Preview sheets at 960 px per tile, at most 6 tiles.
- Target about 3–6 M input and about 60 k output tokens per 15-minute video. A revision should cost a small fraction of that.

## 12. Implementation notes

### 12.1 Overlay mode (from `loop-control`)
- **Frame classes:** classify at 5 fps from a 160×90 decode. Studio = top-left luminance ≤ 228. Plate vs corner = bounding box of the difference from the median plate. Recording = a large, high-detail, non-plate rectangle. Refine each switch at the source fps.
- **Safe zone:** the union of the instructor's bounding boxes over corner frames, plus a 16 px margin. Current footage: x ≥ 1524, y ≥ 732.
- **Composite, two layers:** each section renders a **plate layer** and a **studio layer** (transparent WebM, decoded with `-c:v libvpx-vp9` to keep alpha). Layers are concatenated per kind, resampled to the source fps and overlaid with `enable` expressions from `cuts.json`: the plate layer only during plate and corner shots, the studio layer only during studio shots. That keeps every switch frame-exact even though graphics render at 25 fps.
- **Recording alignment:** cross-correlate the audio envelopes at 100 Hz. A peak above 0.8 means the same take; the trail video matched rough cut 531.82 s at 0.895.

### 12.2 Compose mode (from `durga-trail`, `dbms-trail`)
- **Background model,** picked automatically (`fzv/keyer.py`):
  - **Brand plate:** used when the footage sits on one (the median difference on the frame border is below 8), with a difference matte against the exact plate.
  - **Green screen:** chroma key with despill.
  - **Plain wall:** a fitted degree-4 polynomial plate.
- **Matte clean-up:** fill holes, keep the instructor's component plus attached objects (the laptop), and unmix edges against the plate.
- **Keyer options** in the spec's `key:` block: `exclude: [[x, y, w, h], …]` boxes, `exclude_poly: [[[x, y], …], …]` polygons (e.g. along a laptop's slanted edge) and `cut_below: y` (a desk line) remove props that shouldn't travel with the instructor. `fzv ingest --rekey` applies changed options.
- **Despill (green screen):** green is limited to max(red, blue) on every pixel, so edges carry no green fringe.
- **Playback:** every section plays the one keyed WebM from its own start (`data-playback-start`), so builds never re-encode the presenter per section (the DBMS build went from ~12 min to 0.3 s).
- **Output:** a cropped VP9 + alpha WebM at the graphics rate (25 fps for 25/50 fps sources, 30 for 30/60), so the instructor moves without judder; compose videos are delivered at that rate because the whole picture is re-rendered (verify expects it). The `presenter` template poses it on the brand plate by rule L5; sections render as full opaque clips that are joined and muxed.
- **Speed:** frames are cropped to the instructor's box in the decoder before the matte (about 3× less work); the WebM is written to `presenter.part.webm` and renamed when complete, so an interrupted run is never taken as finished.
- **Detection:** `auto_mode` picks overlay only for an edited layout (two or more shots, the instructor in a corner or off an empty plate for over 20% of the runtime); one continuous take (green screen, plain wall, plate without layout) is compose.
- **Safe zone (L2):** the presenter element reports its live box; validate maps the instructor's alpha occupancy (union over the video, 40 px cells, `edit/comp/occupancy.json`) through it, so graphics are checked against where the instructor really is, through pose moves.
- **DBMS trail (workflow test):** the desk spans the frame and the laptop sits beside the instructor; `key: {exclude: [[0, 0, 720, 1080], [1500, 0, 420, 1080]], cut_below: 992}` keys only the instructor (858×746 cut-out instead of 1920×796), which gives a proper bottom-right corner pose.

### 12.3 Transcription
- **Settings:** Whisper large-v3-turbo (mlx-whisper on Apple Silicon, faster-whisper or whisper.cpp elsewhere; §5.1), **English mode**, temperature 0 with fallback to 0.2 / 0.4 when a chunk's text compresses too well (a repetition loop), chunks of at most 14 s split at pauses, word timestamps, appended per chunk to `transcript.jsonl`. About 1.3× real time.
- **Loops:** any run of one word repeated more than twice ("colon colon colon…") is collapsed in both the text and the words.
- **Background and resume:** ingest starts transcription in a background process (`transcribe.pid`) and finishes with `transcript.done`; a transcript without the marker is partial. Plan and ingest wait for it, and resume it from the last written chunk if the process stopped. A transcript that came from elsewhere (no `transcribe.log`) counts as complete.
- **Avoid Telugu-script mode:** about 0.3× real time and loops. Use it only for short windows.
- **Purpose:** timing and content only; never burned in.

### 12.4 Rendering and finish
- **One root composition:** HyperFrames needs exactly one root `index.html`, so each section is copied over it to render.
- **Video in the page source:** `<video>` must be in static HTML.
- **Timeline registration:** register `window.__timelines["main"]` in the page itself.
- **Parallel renders:** one project copy per worker; the number of workers comes from §5.1. Cache by section HTML + assets + version.
- **SFX cues:** recorded by loading each section in headless Chrome with a recording `sfx()`, then synthesised deterministically (whoosh, swish, pop, blip, tick, click, ding, good, bad, thud, impact, chime, type).
- **Encode** each section with `h264_videotoolbox`, then concat, so a revision re-encodes one section.

- **Cache key per clip:** the clip's HTML, the runtime core and brand CSS, only the template files that define templates the clip uses, and the size + mtime of every media file it plays. A changed unused template keeps the cache; a re-keyed presenter or a replaced recording re-renders.
- **Validate cache:** DOM samples are cached per clip content hash (`edit/validate_cache/`); after a revision only changed clips are sampled again (Loop Control: 22 s cold, 0.5 s warm).
- **Text fit:** tiles and contrast titles shrink long values to fit their card; validate (T3) flags any single word wider than its box, not only wrapped text.

### 12.5 Known pitfalls

| Pitfall | Guard |
|---|---|
| GSAP `set` writes `duration: 0` into shared vars objects | The runtime always passes copies |
| Jump-seeks render wrong start values | `gsap.defaults({lazy: false})`; `fromTo` with `immediateRender: false` |
| JetBrains Mono ligatures (`==` as one glyph) | Ligatures off in base.css |
| `px()` turned `opacity: 0` into `0px`, leaving an opaque layer | Unitless-property list (fixed) |
| A local helper named like a runtime helper blanked a section | `node --check` in build; reserved names |
| A section skipped in preview hid a bug until the final encode | `fzv validate` snapshots every section before render |
| Highlight boxes off by one character on recordings | Measure the recording's character grid once; store it in recordings.json |
| Sketch strokes look mechanical | Fixed wobble seed, pressure taper and draw-speed token per brand |

## 13. Quality gates

1. **Plan check (automatic):**
   - anchors resolve
   - rules pass, with overrides applied
   - `decisions.md` lists styles, overrides and items to confirm
2. **Preview sign-off (when asked for):** one sheet per section over the real footage.
3. **Final verification (automatic):**
   - duration and fps
   - overlay frames = section sum
   - frames on both sides of every studio cut
   - loudness and peak
   - verification sheet
4. **Delivery message:** where the file is, which styles were used, what to confirm.

## 14. Performance

Speed depends on the machine, so the design targets **how work scales** rather than fixed times:

| Stage | Scales with | Design target |
|---|---|---|
| ingest | audio length | transcription runs in the background and overlaps planning prep |
| plan | video length | Claude writes a compact spec, not code; one fresh session per video |
| build + preview + validate | sections | seconds to build; previews only for sections that changed |
| render | frames ÷ workers | studio intervals skipped; unchanged sections served from cache |
| finish + verify | video length | per-section encode; only changed sections re-encoded |
| a timestamped revision | one section | independent of the video's total length |

**Reference point:** the first, manual edit of the 15-minute Loop Control video took 1 h 53 m end to end, including about 45 minutes of avoidable work (a slow transcription attempt and a full re-encode for a 5 s fix). The pipeline removes both. Each run records its own stage times in `verify.json`.

## 15. Build plan and status (2026-10-26)

| Phase | Scope | Status |
|---|---|---|
| 0. Foundations | Repo; brand kits (house style, Career Orbit, Fuzentrix Education); `defaults.yaml`, `rules.yaml`; brand.css from the kits; `fzv doctor` | **done** |
| 1. Base families | Core + Code templates; word-anchor resolver; spec compiler | **done** (Example 1 rebuilt from the spec matches the delivered video) |
| 2. Pipeline | `fzv edit / ingest / plan / build / preview / validate / render / finish / verify / revise`; video-folder layout; parallel render with retry; content-hash cache; per-chunk encode; `decisions.md`, `revisions.md` | **done** (ingest detects all 28 Loop Control cuts frame-exactly; end-to-end verified) |
| 3. Content families | Kinetic, Diagram, Data templates | **done** (templates in place; first real use will tune them) |
| 4. Compose mode | Keyer (brand-plate difference, chroma, fitted wall), `presenter` poses (rule L5), full-frame clips | **done** (first version) |
| 5. Sketch family | Whiteboard board, draw-on props, handwriting, lists, flows, marks; Caveat font | **done** (first version) |
| 5b. Recordings | Content-area detection against known backgrounds; window fits its slot; keyframes; reference mode (§4.2) with corrections (E9); `exec` runners (Python, C, C++, Java, JavaScript) | **done** (Loop Control Example 2 shown and rebuilt) |
| 5c. Library | Free starter set (icons, props, characters, music) with licence records; `props add --recolor`, `icons add`, `music add` | **done** |
| 5f. Second feedback round | Rough-cut corner box (plate patches + frame), SFX variety instead of thinning, HyperFrames registry (31 items, `hf`), end-to-end guide (docs/WORKFLOW.md), stable ids on media elements | **done** |
| 5e. Feedback round | Explainer family (14 templates), rules V1–V3 + concept lexicon, SFX library + density (A5), audible music, boxed corner pose; compose-mode edge layer fixed | **done** (gallery checked; videos not re-edited yet, by request) |
| 5d. Workflow test | Loop Control (overlay, `Recording: reference`, two revisions) and DBMS (green screen, compose, music) from raw files to verified finals; 16 problems found and fixed ([report](test-reports/2026-10-26-workflow-test.md)) | **done** |
| 6. Packaging (optional) | Wrap `fzv` as a Claude skill or fold into the content kit | open |

**Regression set:** `loop-control` (overlay, 15 min), `durga-trail` (compose + recording), `dbms-trail` (green screen). Every release rebuilds all three and compares frames at fixed times.

## 16. Open questions

1. **Sketch icon set:** pick one open-licence line-art set for people and objects, so every sketch video looks the same. Candidates: Open Peeps (CC0) for people, Tabler or Lucide outlines for objects.

---

## Appendix A. Motion references (researched 2026-10-23)

- **promptmotion.com** is only a domain for sale.
- The real galleries are **promptmotion.org** (230 code-rendered motion films and about 1,250 prompts) and **promptmotion.art** (about 100 cases).
- They offer prompts and finished videos, **not downloadable templates**, and grant **no licence**: "Videos and prompts belong to their creators". Use them as inspiration only.
- Many of their films are built with Remotion or HyperFrames, the same approach as this tool.
- There are almost no code-editor or typing templates, which is the gap our Code & Execution family fills.

| Fit for lessons | Styles seen | Taken into this design as |
|---|---|---|
| **High** | Algorithm/concept simulation explainers; blueprint/technical diagrams; whiteboard/line-art; kinetic typography (slowed down); 3Blue1Brown-style maths visuals; data storytelling; terminal/code scenes; talking head + graphics (without their subtitles) | Core, Code, Diagram, Kinetic, Data, Sketch |
| **Medium** | Swiss/editorial/geometric grids; isometric architecture; timelines; transitions (zoom-through, split screen, chart grow); paper-cut/collage (can feel childish) | Swiss grid as the base layout; isometric inside Diagram; a small transition set |
| **Low** | 3D scenes, character films, glitch/synthwave/psychedelic, pixel art, hype product-launch edits | Not in the library |

**Open style libraries worth borrowing ideas from:**
- **Lemo-Opuscar** (github.com/lemomo-ai/lemo-opuscar; README badge says MIT and CC BY 4.0, so check before reuse): 59 styles, each documented in a `STYLE.md`. Relevant styles: Whiteboard Explainer, Blueprint, Data Storytelling, Isometric Infographic, Living Screencast, ASCII/CRT Terminal, Swiss Motion Graphics, Pictogram Motion.
- **15 Motion Design Styles** (github.com/Vincentwei1021/mg-styles-15).

**Techniques that carry over:**
- Every frame is a pure function of time.
- A cue sheet built from word timestamps.
- Graphics placed on the side away from the face.
- One still per beat for QA before the full render.
