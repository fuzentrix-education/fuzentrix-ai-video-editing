# House rules: the master prompt every edit follows

Every video gets these rules; Claude reads them in each video's brief (`edit/plan_brief.md`). They adapt the team's master prompt
("Professional LMS video editing", v5) to this workflow: content comes from the instructor's audio (no PPT), the look is the one
Career Orbit kit, and most rules are checked automatically (`rules.yaml`, `fzv validate`). A video's prompt may override a rule for that
video; every override is logged in `edit/decisions.md`. The full table with check types is in `docs/SYSTEM_DESIGN.md` §8.

**Goal:** a modern, professional, student-friendly lesson: the instructor teaching naturally, clean graphics that explain on her exact
words, subtle sound that adds depth, and her voice never interrupted.

## 1. Content and sync
- Understand the whole lesson first (the beat sheet), then sync every graphic, highlight, code line and output to the word that names it
  (±0.3 s). Nothing appears before she says it; nothing stays after the point ends.
- Content and timing come from the video's own audio only (Telugu and English). Never from a script, PDF or PPT.
- Never cut or extend her footage. No subtitles and no outros unless the prompt asks.
- Program output is real: terminals print through `exec`, which runs the code shown. Never type output by hand.
- Anything shown that she didn't say outright goes under "to confirm". The name card appears only when she introduces herself.

## 2. Show the process (motion graphics)
- When she explains how something works, **show it happening**: data flies into the database, `"20"` converts to `20`, `range` emits
  1…n, a pointer scans a string, values drop into a Venn diagram. Text cards label; animations explain.
- Every step lands on the word that names it. A new visual roughly every 8–12 s; never more than 15 s of words-only screen.
- Cover the concept moments `fzv plan` lists (`global/concepts.yaml`) that fit the lesson, or say why not.
- **Never repetitive (V5):** no animation twice in a row, none in more than 20% of a video's animations.
- Clean, minimal, soft motion: no spins, wipes or flips; animate only position, scale and opacity. 3D only when the prompt asks (S1).
- **Clutter:** at most 4 blocks, 40 words and 12 code lines on screen at once. One idea at a time.
- **Never a plain-instructor stretch (L4):** plate shots never sit empty for more than 2 s; every studio shot carries a light
  studio-layer graphic.
- **Cutaways:** short and only when the prompt allows them: 12 s each at most, 10% of the runtime in total.

## 3. The instructor
- **Rough cuts:** she is untouched: no halo, circle, blur or cut-out. Graphics go only in the empty space and never cover her (L2).
- The bottom-right instructor sits in a rounded box (setting `presenter.corner_box`; prompt `Presenter box: off`).
- **Raw footage (compose mode):** focus on her in the intro, then one fixed spot (bottom right) in the box. Two moves at most.
- Her face stays natural: no smoothing or beauty filters, true skin tone.
- (Next build, not active yet: the master prompt's single framed box that resizes as a whole, with a gentle face lift.)

## 4. Code and screen recordings
- Code is shown in the dark editor with the LMS code editor's colours, typed in step with her dictation; Run flashes when she runs it.
- Explanations sit outside code cards and terminals, joined by thin blue pointer lines routed around other graphics.
- Recordings are shown whole and in order, never cropped, zoomed, cut or rearranged. Only a messy recording is rebuilt, when the prompt
  says `Recording: reference`; every correction is logged and confirmed.

## 5. The look (one brand kit, `global/brand/brand.yaml`)
- Navy text and one brand blue. Green = correct / True / output, red = error / False, amber = look here, and only when the moment
  means it. No colour per topic; teal only inside the logo.
- The dotted backdrop stays for the whole video (L11): no dark scenes or full-frame cutaways unless the prompt asks.
- Highlights: the words turn blue and a blue underline draws under them.
- The chapter pill top left on every frame (chapter number, chapter name · lesson). Give every section after the intro a short
  `chapter:` name. No logo in the video: the team adds the Career Orbit logo after the final render (prompt `Logo: on` burns it in
  top right); keep the top-right corner clear.
- Brand fonts and sizes only: text no smaller than 26 px, code no smaller than 30 px, ligatures off.
- **Blocks never cover each other** (L12): place the next card below the previous one's real height.

## 6. Sound
- **Her voice is the priority:** never cut, muted, faded or lowered for anything. It is cleaned, keeping her natural tone: rumble filter,
  speech denoiser, slight EQ for clarity, gentle levelling for a steady volume, softer "s" sounds (prompt `Voice: untouched` turns
  this off).
- **Sound effects** on visual events only, never on every element: pop (things appear), swish / slide (cards move in), click / tick
  (highlights, steps, Run), whoosh (scene changes), ding / chime (correct result), soft error (wrong case), typing.
- They sit 18–26 dB under her voice by kind and dip 3 dB more while she speaks, so they never mask a word. Only the effects are ducked,
  never the voice. The team's library first; never the same file twice in a row.
- Music only if the prompt asks: audible but well under the voice, ducked while she speaks.
- Final mix: −14 LUFS, −1 dBTP.

## 7. Plan, approve, check
- Plan per idea in the beat sheet (`edit/beats.yaml`): what each beat shows and on which words.
- Before showing anything, the build is checked automatically: sync, clutter, overlap, text overflow, the instructor's safe zone,
  repetition, background changes.
- Two approvals before the render, in order: first the storyboard (one frame per beat, shown directly; saved in the video's folder as
  `<Title> - Storyboard.jpg`), then the preview (the whole edit playing live with real sound). The beat sheet too only with
  `Review: beats, storyboard`. Render only after an explicit "render" or "approved". Any later
  change needs a new approval, and only the changed parts are rendered again.
- After the render, verify: length, frame rate, size and loudness, a frame sheet, and the listening check (measures the final mix:
  effects buried under her voice or too loud, clipping, background noise, music too loud or too quiet).

## 8. Delivery
- 1920×1080, H.264, AAC 320k. Overlay edits keep the source frame rate; compose edits render at 30 fps.
- Earlier finals move to `edit/_prev/` and are never deleted.

## Non-negotiables
- Content from her audio only, synced to her words.
- Her voice never interrupted, lowered or masked.
- Show the process, never just a card that names it.
- One kit: navy and blue, colour only for meaning, the dotted backdrop all video.
- Never clutter, never overlap, never cover her.
- No render before the editor approves the storyboard and then the preview.
