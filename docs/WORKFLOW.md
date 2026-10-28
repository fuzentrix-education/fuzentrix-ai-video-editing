# Editing a video with fzv, end to end

This is the day-to-day procedure: from an editor's files to a delivered, verified video, and changes after delivery.
**Editors** only need the one-page [editor guide](EDITOR-GUIDE.md): they chat with Claude Code and Claude runs every step below.
Details of every command and setting are in the [README](../README.md); the reasoning and the rules are in
[SYSTEM_DESIGN.md](SYSTEM_DESIGN.md).

```
 editor's files ─► video folder ─► ingest + plan ─► Claude fills the BEAT SHEET ─► editor approves (review page)
        ─► Claude writes edit.yaml ─► build · validate ─► STORYBOARD ─► editor approves ─► render · finish · verify
        ─► final + "to confirm" on the review page ─► changes by beat or time (as often as needed)
```

| Editor types in Claude Code | Claude does |
|---|---|
| `/edit-video <folder or file> [notes]` | §2–§6 below, stopping twice for the editor's approval |
| `/review <folder>` | refreshes and opens the review page, says what is waiting |
| `/change <folder> beat 7: …; 7:41: …` | §7 below |
| `/approve <folder> beats\|storyboard` | records the approval and carries on |

The skills live in `.claude/skills/`; the safe steps are pre-approved in `.claude/settings.json`, so Claude Code doesn't ask
"Allow?" at every step.

---

## 0. Once per machine

```bash
git clone <repo> fuzentrix-ai-video-editing && cd fuzentrix-ai-video-editing
brew install ffmpeg node uv        # if missing
bin/setup                          # everything else: Python env, renderer + browser, transcription model, library check, tests
```

Then install VS Code and the Claude Code extension and open **this folder itself** (File → Open Folder), so the project skills
and pre-approved steps load. Before long runs, close heavy apps (VMs, many browser
tabs): `fzv` slows down sharply when the machine is short of memory.

## 1. Shared assets (already included)

Everything a video needs ships in `global/`: 57 templates, 31 registry animations, 114 icons, 120 props and characters, 2 music
tracks, 97 sound effects and the brand kits. Nothing is fetched per video. Adding more is optional; each import records its source
and licence. To review the sound effects once: `bin/fzv sfx audition`, listen, then `bin/fzv sfx remove <category:number>…`.

| Asset | How to add | Notes |
|---|---|---|
| **SFX library** | `bin/fzv sfx add <folder> --source "<url>" --licence "<licence>"` | categories guessed from file names (whoosh, pop, click, ding, success, error, typing…) or `--category`; `bin/fzv sfx list` |
| **Music** | `bin/fzv music add track.mp3 --id calm-focus --mood calm --source … --licence …` | used only when a prompt asks |
| **Props / characters** | `bin/fzv props add file.svg --id … --recolor --source … --licence …` | recoloured to the brand |
| **Icons** | `bin/fzv icons add icon.svg --id … --source … --licence …` | 24-grid line icons (Tabler, Lucide) |
| **Animations from the HyperFrames registry** | `bin/fzv registry search <words>` then `bin/fzv registry add <name…>` | 448 open-source items; 31 are installed; mount with the `hf` template |
| **Concept phrases** | edit `global/concepts.yaml` | phrases that should trigger an animation (rule V3) |
| **House settings** | edit `global/defaults.yaml` | box around the instructor, SFX density, music level, clutter budget… |

Licences: only CC0, MIT, ISC, Apache-2.0, public domain or paid licences (the videos carry no credits roll). `fzv` refuses
non-commercial and no-derivatives licences.

## 2. Per video: the folder and the prompt

1. Make a folder for the video, e.g. `videos/loop-control/` (`videos/` is git-ignored except its README; `/edit-video` makes it for you).
2. Put in the editor's **raw cut** (rough cut, or raw / green-screen footage) and any **screen recording** as a separate file.
3. Write `prompt.md` (or pass `--prompt` in step 3). A good prompt:

```markdown
# Loop Control Statements
Brand: career-orbit
Music: calm-piano, low            # optional; off unless asked
SFX: on                           # minimal | off | library only
Presenter box: on                 # bottom-right instructor in a rounded brand box (rough cuts and raw footage)
Recording: reference              # only if the screen recording isn't good enough to show
Review: on                        # default: the editor approves the beat sheet and the storyboard; off | beats | storyboard
- Make the three example programs the highlight.
- Show data going into the database when she talks about storing data.
- A car and a traffic police officer for the traffic analogy.
```

Any rule or default can be overridden in the prompt for that video; overrides are logged in `edit/decisions.md`.

## 3. Ingest and plan

```bash
bin/fzv edit "videos/loop-control"
```

This picks the raw cut and recordings, extracts audio, transcribes (Telugu + English), finds every shot change, measures where
the instructor is, aligns recordings and saves their keyframes, saves the **footage sheet** (`edit/out/footage.jpg`: a frame every
10 s and at every shot change), writes **`edit/plan_brief.md`**, drafts **`edit/beats.yaml`** and stops.

Check the mode it detected (`ingest: mode overlay|compose`). An editor's rough cut is *overlay* (graphics go in the empty space),
raw or green-screen footage is *compose* (the instructor is keyed and placed). If it is wrong, add `Mode: overlay` or
`Mode: compose` to the prompt and run `bin/fzv ingest` again.

## 4. The beat sheet (plan), approved by the editor

A **beat** is one idea the instructor explains, usually 8–20 s. The draft has one row per beat, cut at pauses, shot changes and
concept moments, with what the instructor says. Claude fills each row (following CLAUDE.md):

| Field | Example |
|---|---|
| `idea` | Data is collected and stored in a database |
| `show` | Chips with Name, Branch and Year fly into a database cylinder; the count rolls up to 10,000 |
| `templates` | `data-flow`, `hf:count-up` |
| `sync` | `"@database"`, `"@records"` (each step lands on its word) |

`bin/fzv beats <folder>` checks the sheet (contiguous rows, known templates, sync words found in the beat) and gives notes:
words-only stretches, concept moments without a matching animation, steps without sync words. It writes `edit/beat_sheet.md`
and refreshes the **review page** (`edit/review/index.html`; `bin/fzv review <folder> --open`).

The editor reads the page (footage frame, what is said, what we show, on which words) and either approves or writes changes
under any beat → **Copy for Claude** → pastes into the chat. Claude edits the rows (their words go into `feedback`) and asks again.
On approval, Claude runs `bin/fzv approve <folder> beats --note "<their words>"` (logged in `edit/approvals.md`).
**`fzv build` refuses to run until the current beat sheet is approved** (rule R1); any later change needs a new approval.

## 5. Claude writes the edit; the storyboard, approved by the editor

1. Claude writes `edit/edit.yaml` from the approved beat sheet, beat by beat, then runs `bin/fzv build` and `bin/fzv validate`
   and fixes everything validate reports (instructor overlap, clutter, text-only stretches, overflow, fake output, **V4**: a beat
   not built with the templates it was approved with…).
2. `bin/fzv storyboard <folder>` takes one frame per beat at its key moment (just after its last sync word), graphics over the real
   footage, in about a minute: `edit/review/storyboard/` and the sheet `edit/out/storyboard.jpg`. Claude checks it first.
3. The **preview** of the whole edit, per `review.preview`:
   - `browser` (default): `bin/fzv studio <folder>` writes `edit/studio/` (the whole edit as one HyperFrames project: the footage, each
     built clip as a sub-composition at its time, the sound as two tracks) and opens it in **HyperFrames Studio**: live playback, no
     rendering, view-only. Made only here or when the editor asks (`/preview`); `--stop` closes it.
   - `video`: `bin/fzv draft <folder>` makes the **preview video** (`edit/review/preview.mp4`): every clip rendered at `review.preview_fps` (10 fps)
   in draft quality, composited over the footage at 960x540 with the real mix (voice, music, SFX). Timing and sound are the final's;
   only the motion is choppier. It takes a fraction of the final render (about 4 minutes for DBMS, 20–25 for the 15-minute Loop Control
   on an 8 GB Mac), and a revision re-drafts only the clips it changed.
4. The review page shows the preview video, then the storyboard as a **grid** (one frame per beat, its time and what it shows; click a frame to see it
   large and write a change for that beat; after rendering the same grid switches to the final video's frames). The editor approves
   or asks for changes the same way as for the beat sheet. Changed scenes are rebuilt and
   only their frames are taken again (`edit/out/storyboard_changed.jpg`). On approval: `bin/fzv approve <folder> storyboard`.
   **`fzv render` refuses to run until the storyboard of the current build is approved** (rule R2), and the approval waits for the
   preview video of that build (`review.preview`; prompt `Review: on, no preview` skips it).

In compose mode Claude also checks the cut-out's edges and, if a desk or laptop travels with the instructor, adds `key:` options and
re-keys (`bin/fzv ingest <folder> --rekey`).

## 6. Render, finish, verify

```bash
bin/fzv edit "videos/loop-control"        # or: bin/fzv render … && bin/fzv finish … && bin/fzv verify …
```

`fzv edit` runs every step that is ready and stops at the first one still waiting for Claude or the editor.

- **render**: graphics clips, in parallel, cached (only changed clips re-render).
- **finish**: sound effects from the team's library, music if asked, mix to −14 LUFS, composite over the untouched footage,
  encode → **`videos/loop-control/Loop Control Statements - Edited.mp4`** (the previous final moves to `edit/_prev/`).
- **verify**: duration, frame rate, size and loudness, plus `edit/out/verify.jpg` (frames at every cut). It refreshes the review
  page, which now plays the final and shows a frame of it per beat beside the storyboard frame.

Before delivery, Claude (and the editor, on the review page) check:

- [ ] **To confirm:** code rebuilt from dictation, corrections made to a screen recording, names heard indistinctly, illustrative details.
- [ ] **Show the process:** every explanation is animated in sync; no long stretches of text alone.
- [ ] **Instructor:** never covered; in the box at the bottom right if the setting is on.
- [ ] **Clean screen:** one idea at a time; nothing overflowing.
- [ ] **Program output** matches what the program really prints (it is generated by running the code).
- [ ] **Sound:** effects on the visual events, no identical sound repeated back to back; music audible but under the voice.

## 7. Changes (before or after delivery)

On the review page the editor writes a change under a beat, or pauses the final video and adds a change at that time, then
**Copy for Claude** → paste. Typed by hand it looks like:

```
/change videos/loop-control beat 7 (1:23): use a car; 7:41: make the break note larger
```

Claude runs `bin/fzv revise <folder> "<requests>"` (beat numbers become the beat's time; each time is mapped to the scenes on
screen, with what the instructor says there; logged in `edit/revisions.md`), edits only those scenes (and the beat's row; the
request approves it), rebuilds, takes the changed storyboard frames, asks "render?" (unless the editor already said so), then
renders, finishes and verifies. Only changed clips and encode chunks are redone; a one-scene change takes a few minutes. Each
request's **Status** in `edit/revisions.md` says what changed.

Edits made before beat sheets existed (no `edit/beats.yaml`) keep working without the approval steps.

## 8. What the folder holds afterwards

```
videos/loop-control/
  LOOP CONTROL ST ROUGH CUT .mp4        raw cut (untouched)
  screen recording .mp4                 recording (untouched)
  prompt.md                             the prompt
  Loop Control Statements - Edited.mp4  the final
  edit/                                 transcript, shots, plan brief, beats.yaml + beat_sheet.md, edit.yaml, decisions.md,
                                        approvals.md, revisions.md, renders, previews
  edit/review/index.html                the review page (local; open it in any browser)
```

Keep the whole folder: re-runs and revisions reuse its caches.

## 9. Settings you will touch most

| Want | Where |
|---|---|
| No box around the instructor for one video | prompt `Presenter box: off` (house default: `presenter.corner_box` in `global/defaults.yaml`) |
| Fewer entrance sounds | prompt `SFX: minimal`; only the team's library: `SFX: library only` |
| Music level | prompt `Music: <track>, low` / `high`; house default `music.rel_lufs` |
| Show the screen recording / rebuild it | prompt `Recording: show` (default) / `Recording: reference` (`, exact` = no corrections) |
| Stricter or looser "show the process" | `visuals.max_text_only_s` in `global/defaults.yaml` |
| More concept triggers | `global/concepts.yaml` |
| Skip the approvals for one video (tests) | prompt `Review: off` (`beats` / `storyboard` keeps one; `on, no preview` skips only the preview video); house default `review.*` in `global/defaults.yaml` |
| Live preview in Studio, or a preview video | prompt `Review: on, preview video` for the draft video; house default `review.preview` (`browser`) |
| Smoother or faster preview video | `review.preview_fps` in `global/defaults.yaml` (default 10) |
| Music on or off after the fact | review page music switch → **Keep this for the final**, or `bin/fzv mix <folder> off\|on\|<track> --level …` (re-mixes only) |
