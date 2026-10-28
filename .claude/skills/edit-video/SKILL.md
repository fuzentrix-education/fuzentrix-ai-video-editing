---
name: edit-video
description: Edit a teaching video end to end for a video editor, from the rough cut or raw footage in a folder to the finished, checked video, with the editor approving the beat sheet and the storyboard on the way. Use when someone asks to edit, make or finish a video in videos/<name>, or hands over video files to edit.
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
  can't tell: which brand, whether to show the screen recording or rebuild it, music (off unless they want it), anything to
  highlight. "Use the defaults" is a fine answer.

## 1. Ingest and plan
Run `bin/fzv edit "<folder>"`. It transcribes (several minutes), finds the shots and drafts the beat sheet, then stops. Tell the
editor in one line what it detected: a *rough cut* (graphics go around the instructor) or *raw footage* (the instructor is
placed on a brand background).

## 2. Beat sheet, then the editor's approval
1. Follow CLAUDE.md "Editing a video" steps 2–3: read `edit/plan_brief.md`, look at `edit/out/footage.jpg`, and fill every row of
   `edit/beats.yaml`: `idea`, `show` (plain words an editor understands: "chips with Name, Branch and Year fly into a database"),
   `templates`, `sync` (the words each step lands on). Merge or split rows when an idea is shorter or longer.
2. Run `bin/fzv beats "<folder>"` until it reports no problems; act on its notes (text-only stretches, concept moments, missing
   sync words) or say in `notes` why not.
3. Run `bin/fzv review "<folder>" --open` (opens the review page in their browser). In the chat, post a compact table: beat number,
   time, what we show, on which words. Ask them to approve or to say what to change, by beat number or time. **Stop and wait.**
4. Changes: edit those rows, add their words to the row's `feedback`, run `bin/fzv beats` again, show only the changed rows, ask again.
5. Approval: only when the editor clearly approves ("approved", "looks good", "go ahead", or `/approve`). Then run
   `bin/fzv approve "<folder>" beats --note "<their words>"`. Never approve on their behalf.

## 3. Build, storyboard, then the editor's approval
1. Write `edit/edit.yaml` from the approved beat sheet, beat by beat (CLAUDE.md steps 4–6). Run `bin/fzv build`, `bin/fzv validate`
   and fix everything it reports (V4: every beat built with the templates it was approved with).
2. Run `bin/fzv storyboard "<folder>"` (about a minute; one frame per beat over the real footage). Look at
   `edit/out/storyboard.jpg` yourself first and fix wrong visuals, overlaps, empty or cluttered frames before the editor sees it.
3. Make the preview of the whole edit. Default (`review.preview: browser`): `bin/fzv studio "<folder>"` opens the **live preview** in
   HyperFrames Studio in their browser (no rendering, the real sound; music is its own track they can mute). If the prompt says
   `Review: on, preview video`, run `bin/fzv draft "<folder>"` instead (a quick low-frame-rate video). Then `bin/fzv review "<folder>" --open`.
   Tell them the preview and the storyboard grid are ready, point out anything to look at closely (illustrative details, rebuilt code), and
   ask them to approve or request changes. **Stop and wait.** When they approve, close the live preview (`bin/fzv studio "<folder>" --stop`).
4. Changes: use the `change` skill's "after approval" steps. Approval: `bin/fzv approve "<folder>" storyboard --note "<their words>"`.

## 4. Render and hand over
Run `bin/fzv edit "<folder>"` in the background (renders, mixes, checks; 10–40 minutes depending on length). Then run
`bin/fzv review "<folder>" --open` and tell them, in a few lines: where the final video is, whether the checks passed, and the
"to confirm" items in plain words. Changes later: they ask in the chat or use the review page (the `change` skill).

## If something goes wrong
Fix it yourself when you can (validate problems, a transcript still running, a clip that failed to render). If it needs the
editor (a missing file, a decision only they can make), ask one clear question. Never leave them with an error message.
