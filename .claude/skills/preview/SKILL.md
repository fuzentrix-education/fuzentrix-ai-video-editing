---
name: preview
description: Open the live preview of a video edit in HyperFrames Studio (the whole edit playing in the browser with its sound, no rendering), or close it. Use when an editor asks to preview, play, watch or open a video edit in Studio before (or after) rendering.
argument-hint: "<video folder> [stop]"
---

# Live preview in HyperFrames Studio

The editor is not technical: plain words only. Open the live preview only when they ask, or as the preview before the final render
(edit-video skill, step 3).

Request: `$ARGUMENTS`: a video folder, optionally `stop`.

1. The edit must be built (`edit/built/`). If it isn't, say the preview comes after the storyboard step, and offer to continue the edit.
2. Run `bin/fzv studio "<folder>"`. It writes the Studio project (only when the build changed) and opens HyperFrames Studio in their
   browser. Tell them in a few lines:
   - press play or scrub the timeline; every scene is a clip on the timeline;
   - the sound is the real mix; music is its own track (mute it with its eye/speaker in the timeline to hear the video without it);
   - it's view-only: to change something, write it on the review page (**Copy for Claude**) or tell you, with the time.
   - On a slow machine playback may stutter; offer the preview video instead (`bin/fzv draft "<folder>"`, a smooth file at a lower frame rate).
3. With `stop`, or once they are done: `bin/fzv studio "<folder>" --stop` (the preview holds memory).
