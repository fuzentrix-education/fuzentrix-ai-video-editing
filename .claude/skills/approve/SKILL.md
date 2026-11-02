---
name: approve
description: Record a video editor's approval of a video's storyboard (first), its preview (second, then the render), or its beat sheet (only when the prompt asks for that review too), and continue the edit.
argument-hint: "<video folder> storyboard|preview|beats"
disable-model-invocation: true
---

# Record the editor's approval

The editor typed this (or pasted it from the review page's **Copy approval for Claude** button), so it is their approval.

Request: `$ARGUMENTS`: the video folder, then `storyboard` (first), `preview` (second) or `beats` (only for videos whose prompt says
`Review: beats, storyboard`).

1. Run `bin/fzv approve "<folder>" <storyboard|preview|beats> --note "approved by the editor"`. If it reports problems (a beat sheet with
   unfilled rows, a storyboard older than the latest build, a preview before the storyboard), fix them, show the editor what changed
   and ask again; don't approve something they haven't seen.
2. Continue the edit-video skill:
   - after **beats** (only with the beat-sheet review on): write `edit/edit.yaml` from the beat sheet, build, validate, make the storyboard and show it (step 3);
   - after **storyboard**: make the preview and show it (step 3.4); no render yet;
   - after **preview**: close the live preview, render with `bin/fzv edit "<folder>"` in the background and hand over the final (step 4).
3. Tell the editor in one line what happens next and roughly how long it takes.
