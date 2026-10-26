# Editing a video with fzv, end to end

This is the day-to-day procedure: from an editor's files to a delivered, verified video, and changes after delivery.
Details of every command and setting are in the [README](../README.md); the reasoning and the rules are in
[SYSTEM_DESIGN.md](SYSTEM_DESIGN.md).

```
 editor's files ─► video folder ─► fzv edit (ingest + plan) ─► Claude writes edit.yaml ─► build · validate · preview
        ─► render · finish · verify ─► review the final + "to confirm" ─► deliver ─► fzv revise "m:ss …" (as often as needed)
```

---

## 0. Once per machine

```bash
git clone <repo> fuzentrix-video-editing-automations && cd fuzentrix-video-editing-automations
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e ".[dev]"
uv pip install --python .venv/bin/python mlx-whisper          # Apple Silicon (elsewhere: faster-whisper)
npm install && npx hyperframes render --help >/dev/null       # renderer + its headless Chrome
bin/fzv doctor                                                # workers, transcription backend, encoder
.venv/bin/python -m pytest                                    # should pass
```

Before long runs, close heavy apps (VMs, many browser tabs): `fzv` slows down sharply when the machine is short of memory.

## 1. Once per team: shared assets

Everything in `global/` is shared by every video. Add to it whenever you like; each import records its source and licence.

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

1. Make a folder for the video, e.g. `videos/loop-control/`.
2. Put in the editor's **raw cut** (rough cut, or raw / green-screen footage) and any **screen recording** as a separate file.
3. Write `prompt.md` (or pass `--prompt` in step 3). A good prompt:

```markdown
# Loop Control Statements
Brand: career-orbit
Music: calm-piano, low            # optional; off unless asked
SFX: on                           # minimal | off | library only
Presenter box: on                 # bottom-right instructor in a rounded brand box (rough cuts and raw footage)
Recording: reference              # only if the screen recording isn't good enough to show
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
the instructor is, aligns recordings and saves their keyframes, then writes **`edit/plan_brief.md`** and stops.

Check the mode it detected (`ingest: mode overlay|compose`). An editor's rough cut is *overlay* (graphics go in the empty space),
raw or green-screen footage is *compose* (the instructor is keyed and placed). If it is wrong, add `Mode: overlay` or
`Mode: compose` to the prompt and run `bin/fzv ingest` again.

## 4. Claude writes the edit

Open the repo in **Claude Code** and ask:

> Edit the video in `videos/loop-control` (follow CLAUDE.md).

Claude reads only the plan brief, then:
1. **Plans the visuals first**: for every stretch where the instructor explains something, it picks an animation that *shows* it
   (data flying into a database, `"20"` converting to `20`, `range` emitting 1…n, a request travelling…), each step anchored to
   the word that names it. It covers the **concept moments** the brief lists.
2. Writes `edit/edit.yaml` (sections, scenes, timings, decisions, things to confirm).
3. Runs `bin/fzv build` and `bin/fzv validate`, and fixes everything validate reports (instructor overlap, clutter, text-only
   stretches, overflow, fake output…).
4. Previews tricky moments (`bin/fzv preview <folder> <clip> <t1,t2>`), looks at them and adjusts.

In compose mode it also checks the cut-out's edges and, if a desk or laptop travels with the instructor, adds `key:` options and
re-keys (`bin/fzv ingest <folder> --rekey`).

## 5. Render, finish, verify

```bash
bin/fzv edit "videos/loop-control"        # or: bin/fzv render … && bin/fzv finish … && bin/fzv verify …
```

- **render**: graphics clips, in parallel, cached (only changed clips re-render).
- **finish**: sound effects from the team's library, music if asked, mix to −14 LUFS, composite over the untouched footage,
  encode → **`videos/loop-control/Loop Control Statements - Edited.mp4`** (the previous final moves to `edit/_prev/`).
- **verify**: duration, frame rate, size and loudness, plus `edit/out/verify.jpg` (frames at every cut).

## 6. Review before delivery

Watch the final and read `edit/decisions.md`. Check:

- [ ] **To confirm:** code rebuilt from dictation, corrections made to a screen recording, names heard indistinctly, illustrative details.
- [ ] **Show the process:** every explanation is animated in sync; no long stretches of text alone.
- [ ] **Instructor:** never covered; in the box at the bottom right if the setting is on.
- [ ] **Clean screen:** one idea at a time; nothing overflowing.
- [ ] **Program output** matches what the program really prints (it is generated by running the code).
- [ ] **Sound:** effects on the visual events, no identical sound repeated back to back; music audible but under the voice.

## 7. Changes after delivery

```bash
bin/fzv revise "videos/loop-control" "7:41 make the break note larger; 10:05 show the output one line at a time"
```

`revise` maps each timestamp to the scenes on screen, prints what the instructor says there and logs the request in
`edit/revisions.md`. Then ask Claude Code:

> Apply the pending revisions in `videos/loop-control` (follow CLAUDE.md).

Claude edits only those scenes, re-runs build → validate → render → finish → verify (only changed clips and encode chunks are
redone; a one-scene change takes a few minutes) and marks each request done in `edit/revisions.md`.

## 8. What the folder holds afterwards

```
videos/loop-control/
  LOOP CONTROL ST ROUGH CUT .mp4        raw cut (untouched)
  screen recording .mp4                 recording (untouched)
  prompt.md                             the prompt
  Loop Control Statements - Edited.mp4  the final
  edit/                                 transcript, shots, plan brief, edit.yaml, decisions.md, revisions.md, renders, previews
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
