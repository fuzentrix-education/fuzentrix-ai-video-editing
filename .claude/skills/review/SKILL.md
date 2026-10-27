---
name: review
description: Show a video editor where a video edit stands and open its review page (beat sheet, storyboard, final video, things to confirm). Use when an editor asks to see, check or review a video edit, or asks what state a video is in.
argument-hint: "[video folder]"
---

# Show the review page

The editor is not technical: plain words only, no commands or logs in the chat.

Request: `$ARGUMENTS`: a video folder. With no folder, run `bin/fzv review "<folder>"` for each folder in `videos/` that has an
`edit/` folder, and list them in one line each: name, stage, what happens next.

With a folder:
1. Run `bin/fzv review "<folder>" --open`. It refreshes `edit/review/index.html` (beats, storyboard frames, final-video frames)
   and opens it in the browser.
2. Tell the editor in a few lines:
   - the stage: beat sheet waiting for them / storyboard waiting for them / rendering / final ready;
   - what to do now: approve, or write changes under a beat or at a time in the video and press **Copy for Claude**, then paste
     the copied text into the chat;
   - the "to confirm" items, in plain words, when the final is ready.
