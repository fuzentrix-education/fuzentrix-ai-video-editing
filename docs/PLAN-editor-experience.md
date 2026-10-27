# Plan: better outputs and an editor-friendly workflow (proposal, 2026-10-26)

> **Status 2026-10-27:** stages 1 and 2 are built. Stage 1 = editors work by chatting in Claude Code (skills `/edit-video`,
> `/change`, `/review`, `/approve`; pre-approved steps; [EDITOR-GUIDE.md](EDITOR-GUIDE.md)). Stage 2 = footage sheet, beat sheet,
> approvals with gates, storyboard and one review page per video (design D29, D30, §9f). Studio (§3 below) and the re-edits
> (step 7) are not started.

Four requests, one plan:
1. **Sound library** suited to teaching videos (calm, 3Blue1Brown-like).
2. **Beat sheets and contact sheets** in the workflow, so the edit is planned and checked before rendering.
3. **HyperFrames Studio** (the app/UI) to check and change an edit before export.
4. **Editors without technical knowledge** must be able to run all of this.

---

## 1. Sound effects for teaching videos

**What "3Blue1Brown style" means for sound:** 3Blue1Brown uses very few effects: a calm voice, soft music, and the animation
does the explaining. The equivalent for us is a **small, soft, consistent palette**: a light tick when an item appears, a gentle
air-whoosh between scenes, a soft chime on an "aha" result, a quiet click on Run, soft typing. No cartoon boings, no loud
risers, never the same file twice in a row (rule A5 already rotates files).

**Sources checked (commercial use, no credit needed):**

| Source | What | Licence | Fit |
|---|---|---|---|
| [Kenney: Interface Sounds](https://kenney.nl/assets/interface-sounds) | 100 sounds: clicks, confirmations, errors, glass, drop, scroll, toggles, open/close | CC0 | **Best free fit**: soft, organic UI sounds; direct zip download |
| [Kenney: UI Audio](https://kenney.nl/assets/ui-audio) | 50 sounds: buttons, switches, clicks | CC0 | Good for clicks and ticks |
| [Mixkit sound effects](https://mixkit.co/free-sound-effects/) | whooshes, transitions, notification chimes | Mixkit SFX licence: commercial, no attribution | Pick individually (whooshes, chimes) |
| [Pixabay sound effects](https://pixabay.com/sound-effects/) | 130,000+ | Pixabay licence: commercial, no attribution | Huge; pick by hand (soft whoosh, soft pop) |
| [Sonniss GDC bundle](https://sonniss.com/gdc-bundle-license/) | 7.5 GB a year, mostly cinematic / game | royalty-free, commercial, no attribution (no AI training) | Few teaching-style sounds; heavy download |
| [Sonniss Explainer Video Sound Kit](https://sonniss.com/sound-effects/explainer-video-sound-kit/) | 1,222 explainer sounds (whooshes, UI, pops, typing, bells, gestures) + 51 music tracks | paid, $86 once, royalty-free | **Best overall fit** if a one-time purchase is fine |

Not suitable: Zapsplat free tier (credit required), Freesound unless CC0, BBC Sound Effects (non-commercial), Material sound
resources (CC BY).

**Proposed steps:**
1. Download Kenney Interface Sounds + UI Audio (CC0) and import with `fzv sfx add` (categories mapped from file names:
   click → click, select/switch/toggle → blip, pluck → pop, tick → tick, confirmation → good/ding, error → bad, glass → chime,
   drop → thud, open/close/maximize/minimize/scroll → swish).
2. Build an **audition reel**: one short MP3 per category with every candidate and its file name, so the team can listen and
   keep only the soft ones (a `keep/drop` list in `global/sfx/manifest.yaml`).
3. Add 3–5 soft whooshes and chimes picked by hand from Mixkit/Pixabay. **Decision (2026-10-26): free sources only**, so no paid kit.
4. Lower the house SFX level a further 2–3 dB for the calm style; keep "SFX: minimal" for very calm videos.

---

## 2. Beat sheets and contact sheets

The edit improves most when it is **planned per idea** and **checked before rendering**. Three artefacts, each readable by a
non-technical editor:

### 2.1 Footage sheet (automatic, after ingest)
One thumbnail per shot and every 10 s, with the transcript line under it, plus the concept moments. Orients the editor and Claude.

### 2.2 Beat sheet (Claude writes it, the editor approves it, *before* the spec)
A table, one row per beat (one idea the instructor explains, usually 8–20 s):

| # | Time | Instructor says (gist) | The idea | What we show (animation) | Synced on the words | Notes |
|---|---|---|---|---|---|---|
| 7 | 1:23–1:38 | "Data organise chesi database ready…" | Data is stored in a database | Chips (Name, Branch, Year) fly into a database cylinder; count 10,000 | "database" (1:25), "records" (1:30) | |

- Generated from the transcript, pauses, shots and concept moments (`fzv beats <folder>` → `edit/beat_sheet.md` + a page view).
- The editor reads it in plain language and changes cells ("use a car here", "skip this", "make this the highlight").
- Claude writes `edit.yaml` **from the approved beat sheet**, beat by beat; validate checks every beat has its visual (rule V1–V3).
- With music, `hyperframes beats` finds the music's beats so scene changes can land on them.

### 2.3 Storyboard contact sheet (automatic, after build, *before* render)
One frame per beat at its key moment (graphics over the real footage) with the beat's line under it; motion-heavy beats get an
onion-skin strip (`hyperframes keyframes --shot --layout strip`). Rendering is the slow part; the storyboard costs a minute and
catches wrong visuals, overlaps and timing before the render.

### 2.4 Final sheet (exists today as `verify.jpg`, extended)
One frame per beat from the final render, side by side with the storyboard frame, plus the "to confirm" list.

All four live on **one review page per video** (`edit/review/index.html`): beat sheet → storyboard → final, with an
"approve / request change at m:ss" box for each beat.

---

## 3. HyperFrames Studio for checking and changing before export

**What Studio offers** ([docs](https://hyperframes.heygen.com/studio)): a browser editor (`hyperframes preview`) and a desktop app
with the live frame, a **timeline** (move, trim, split clips), a **canvas** (move, resize, rotate, crop), a **Design panel**
(text, style, colour, motion) and an **Export** button. Every change is saved straight into the project's HTML files; the desktop
app records changes (`hyperframes history`, `catch-up`).

**The catch:** fzv's source of truth is `edit.yaml`; the HTML is generated from it, and most graphics are drawn by script at
play time. If an editor changes the generated HTML in Studio, the next fzv build would overwrite it, and Studio can't grab
elements that only exist at play time. So Studio needs a **round-trip**:

### Where Studio sits in the flow (decided 2026-10-26: editors need a UI for adjustments)

```
beat sheet ─► build ─► OPEN IN STUDIO (live preview, adjust: no render needed) ─► render ─► finish ─► final
                              ▲                                                                   │
                              └──────────── open again after delivery, adjust, re-render only what changed ┘
```

- **Before rendering (main use):** Studio plays the edit live in the browser over the real footage, so adjustments are seen
  instantly and the slow render happens once, after the editor is happy.
- **After rendering:** the same project reopens for changes; only the changed scenes re-render (minutes, not the whole video).
- **What the UI handles:** timing (drag / trim a scene), position and size (canvas), text and colour (Design panel), hide or delete
  a scene. **What still goes through Claude** in the chat: new animations, different content, anything that needs re-planning.

### Phase A: Studio as the review screen (small)
`fzv studio <folder>` builds a Studio project of the whole edited video: the raw cut as the base track, each **scene** as a
named clip on the timeline (its own sub-composition, stable id, at its time), the final mix as audio. Editors scrub, play, compare
and leave notes; changes still go through `fzv revise` (or the review page). No risk of lost edits.

### Phase B: two-way edits for the common tweaks (medium)
Make each fzv scene a Studio-editable clip whose **timing, box and text** are real HTML attributes and variables:
- drag/trim a scene on the timeline → its `at`/`until` (and all its inner word-anchored times shift with it);
- move/resize it on the canvas → its `box`;
- change its text in the Design/variables panel → its text params.

`fzv studio pull <folder>` reads what changed (`hyperframes history` / `catch-up`, file diffs) and writes it back into
`edit.yaml`, logs it in `revisions.md`, and the normal build → render → finish → verify runs. Anything Studio changes that fzv
can't map (e.g. a new element drawn by hand) is listed for Claude to translate or is kept as an "override" layer.

### Phase C: export
Keep **export in fzv** (`finish`): it mixes the voice, SFX and music to −14 LUFS and composites over the untouched footage at its
own frame rate, which Studio's export doesn't do. Studio's Export button can be wired to call `fzv finish` later.

---

## 4. Will the commands be too complex for editors? (no: editors use Claude Code in VS Code)

**Decision (2026-10-26):** editors use the same setup as today: **Claude Code in VS Code**. They type plain requests ("Edit the
video in videos/dbms", "At 7:41 make the note bigger"); Claude runs every `fzv` command. The commands are Claude's tools
(reliable, repeatable steps with caching and checks), not something editors type. No separate app is needed.

To make that smooth for non-technical editors:

| Item | What | Size |
|---|---|---|
| Slash commands | `/edit-video <folder>`, `/change <folder> <beat or m:ss change>`, `/review <folder>`, `/approve <folder> beats\|storyboard` in `.claude/skills/` | **done** |
| Pre-approved permissions | `.claude/settings.json` allows the safe fzv / test commands, so Claude Code doesn't ask "Allow?" at every step | **done** |
| One-step setup | `bin/setup` installs everything on a new machine (run once by someone technical) | **done** |
| Editor guide | one page: open the folder, put the video files, ask, review, request changes | **done** ([EDITOR-GUIDE.md](EDITOR-GUIDE.md)) |

Each editor needs VS Code, the Claude Code extension, a Claude subscription and the repo; long renders keep running while VS Code
stays open. A browser dashboard (`fzv app`) stays an option for later, not a requirement.

## 5. Proposed order

| Step | What | Size | Gives |
|---|---|---|---|
| 1 | SFX: Kenney import, category mapping, audition reel; pick extras | small | **done** (97 CC0 sounds incl. 7 Freesound whooshes; `fzv sfx audition` / `remove`) |
| 2 | Footage sheet + beat sheet (`fzv beats`), spec written from the approved beat sheet | medium | **done** (approvals + gates R1/R2, V4) |
| 3 | Storyboard contact sheet + one review page per video | small–medium | **done** (`fzv storyboard`, `fzv review`) |
| 4 | Editor setup in Claude Code: slash commands, pre-approved permissions, `bin/setup`, editor guide | small | **done** (as project skills) |
| 5 | `fzv studio` Phase A (open the edit in Studio, live preview before rendering) | small | visual check without rendering |
| 6 | Studio Phase B (adjust timing / position / text in Studio, synced back into the edit) | medium–large | the editor's adjustment UI, before and after rendering |
| 7 | Re-edit Loop Control and DBMS with all of the above | medium | proof against the old DBMS edit |

**Decided:** free SFX only; editors use Claude Code in VS Code. **Still open:** whether review links may use HyperFrames
`publish` (private cloud links) or stay local; who on the team approves beat sheets.
