---
name: edit-video
description: Edit a teaching video end to end for a video editor, from the rough cut or raw footage in a folder to the finished, checked video, with the editor approving the storyboard and then its preview before the final render. Use when someone asks to edit, make or finish a video in videos/<name>, or hands over video files to edit.
argument-hint: "<video folder or files> [notes for this video]"
---

# Edit a video for an editor

The person asking is a video editor, not a programmer. Talk in plain words: what you are doing, what they need to look at, what
they need to decide. Never paste commands, YAML, file contents or logs into the chat. You run every command yourself; the
`bin/fzv` steps are pre-approved. Long steps (transcription, rendering) run in the background: say roughly how long they take.

Request: `$ARGUMENTS`: the video folder (for example `videos/dbms-trail`), optionally followed by notes for this video.

## 0. The folder and the prompt
- Files or a folder outside `videos/`: make `videos/<short-name>/` (lowercase, hyphens, no spaces) and copy the rough cut / raw
  footage and any screen recording into it. Never move or change the editor's originals.
- No `prompt.md` yet: write it from their notes (format: docs/WORKFLOW.md §2). Ask once, in one short message, only what you
  can't tell: whether to show the screen recording or rebuild it, music (off unless they want it), anything to
  highlight. "Use the defaults" is a fine answer.

## 1. Ingest and plan
Run `bin/fzv edit "<folder>"`. It transcribes (several minutes), finds the shots and drafts the beat sheet, then stops. Tell the
editor in one line what it detected: a *rough cut* (graphics go around the instructor) or *raw footage* (the instructor is
placed on a brand background).

## 2. Plan the beat sheet (no stop for the editor)
1. Follow CLAUDE.md "Editing a video" steps 2–3: read `edit/plan_brief.md`, look at `edit/out/footage.jpg`, and fill every row of
   `edit/beats.yaml`: `idea`, `show` (plain words an editor understands: "chips with Name, Branch and Year fly into a database"),
   `templates`, `sync` (the words each step lands on). Merge or split rows when an idea is shorter or longer.
2. Run `bin/fzv beats "<folder>"` until it reports no problems; act on its notes (text-only stretches, concept moments, missing
   sync words) or say in `notes` why not.
3. Go straight on to step 3: the editor judges the plan as the storyboard (their first approval). Tell them in one line that the plan
   is ready and the storyboard is being built.
4. Only if the prompt says `Review: beats, storyboard`: run `bin/fzv review "<folder>" --open`, post a compact table (beat number,
   time, what we show, on which words) and **stop and wait**. Changes go into the rows (their words in `feedback`); approval only when
   they clearly approve: `bin/fzv approve "<folder>" beats --note "<their words>"`. Never approve on their behalf.

## 3. Build, storyboard, then the editor's approval
1. Write `edit/edit.yaml` from the beat sheet, beat by beat (CLAUDE.md steps 4–6). Run `bin/fzv build`, `bin/fzv validate`
   and fix everything it reports (V4: every beat built with the templates the beat sheet names).
2. Run `bin/fzv storyboard "<folder>"` (about a minute; one frame per beat over the real footage). Look at
   `edit/out/storyboard.jpg` yourself first and fix wrong visuals, overlaps, empty or cluttered frames before the editor sees it.
3. **Show the storyboard directly.** Run `bin/fzv review "<folder>" --open`; the grid is also saved in the video's folder as
   `<Title> - Storyboard.jpg`. Tell them it's ready, point out anything to look at closely (illustrative details, rebuilt code), and
   ask them to approve the frames or request changes. **Stop and wait.** Approval: `bin/fzv approve "<folder>" storyboard --note "<their words>"`.
4. **Then the preview, before rendering.** Default (`review.preview: browser`): `bin/fzv studio "<folder>"` opens the **live preview** in
   HyperFrames Studio in their browser (no rendering, the real sound; music is its own track they can mute). If the prompt says
   `Review: on, preview video`, run `bin/fzv draft "<folder>"` instead (a quick low-frame-rate video). Refresh the page and ask them to
   watch it and approve, or request changes. **Stop and wait.** Approval: `bin/fzv approve "<folder>" preview --note "<their words>"`; then
   close the live preview (`bin/fzv studio "<folder>" --stop`).
5. Changes at either step: use the `change` skill's "after approval" steps.

## 4. Render and hand over
Run `bin/fzv edit "<folder>"` in the background (renders, mixes, checks; 10–40 minutes depending on length). Then run
`bin/fzv review "<folder>" --open` and tell them, in a few lines: where the final video is, whether the checks passed, and the
"to confirm" items in plain words. Changes later: they ask in the chat or use the review page (the `change` skill).

## If something goes wrong
Fix it yourself when you can (validate problems, a transcript still running, a clip that failed to render). If it needs the
editor (a missing file, a decision only they can make), ask one clear question. Never leave them with an error message.
