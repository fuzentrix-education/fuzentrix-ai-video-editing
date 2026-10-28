---
name: change
description: Apply a video editor's change requests to a video edit, by beat number ("beat 7, use a car") or by time in the video ("7:41 make the text bigger"), before or after rendering. Use when an editor asks to change, fix, move or adjust something in a video edit, or pastes requests copied from the review page.
argument-hint: "<video folder> beat N: <change>; m:ss: <change>; …"
---

# Apply an editor's change requests

The editor is not technical: answer in plain words, never paste commands, YAML or logs. The `bin/fzv` steps are pre-approved.

Request: `$ARGUMENTS`: the video folder first, then one or more requests separated by `;`. Requests name a beat
(`beat 7 (1:23): …`) or a time in the video (`7:41: …`). If the folder is missing and there is only one video in `videos/`, use it;
otherwise ask which video.

## 1. Where does the edit stand?
Run `bin/fzv review "<folder>"`; it prints the beat sheet, storyboard and final state.

## 2. Beat sheet not approved yet (still planning)
Change those rows in `edit/beats.yaml` and add the editor's words to each row's `feedback`. Run `bin/fzv beats "<folder>"`,
refresh the page (`bin/fzv review "<folder>" --open`), show only the changed rows in the chat and ask for approval
(edit-video skill, step 2).

## 3. After the beat sheet was approved (storyboard or final video exists)
1. Run `bin/fzv revise "<folder>" "<the requests>"`: it maps each beat or time to the scenes on screen, prints what the instructor
   says there and logs the request in `edit/revisions.md`.
2. Change only those scenes in `edit/edit.yaml` (CLAUDE.md "Revising after delivery"). When what a beat shows changes, update its row
   in `edit/beats.yaml` too (`show`, `templates`, `sync`) and add the editor's words to `feedback`. Their request is their approval
   of the rows it touches: `bin/fzv approve "<folder>" beats --note "change request: <their words>"`.
3. Run `bin/fzv build`, `bin/fzv validate` (fix everything), then `bin/fzv storyboard "<folder>"` (only changed frames are redone) and,
   if they want to see it move, the live preview (`bin/fzv studio "<folder>"`). Look at `edit/out/storyboard_changed.jpg` yourself and fix anything wrong.
4. Refresh the page (`bin/fzv review "<folder>" --open`), say what changed (the preview video shows it in motion), and ask "Render the new version?" If their message already
   said to go ahead and render, don't ask: approve with their words as the note.
5. Once approved: `bin/fzv approve "<folder>" storyboard --note "<their words>"`, then `bin/fzv edit "<folder>"` in the background (only
   changed clips and encode chunks are redone: minutes, not the whole video). Set each request's **Status** in `edit/revisions.md`
   to what changed, refresh the page and tell them it's ready.

## Music requests
"music: off", "music: keep <track>, level high", "music: add <track>, level low" (from the review page's music switch, or in their words):
run `bin/fzv mix "<folder>" off|on|<track> --level low|normal|high`. Only the sound is re-mixed (a minute or two); no approval is needed
for it. Tell them when the new version is ready.

## When a request can't be done as asked
Say so plainly and offer the closest option (for example, a prop that isn't in the library: offer one that is, and add it to
`props_to_add`). Requests that contradict a house rule (covering the instructor, burning in subtitles) are possible when the editor
insists: record the rule in `overrides:` with their reason.
