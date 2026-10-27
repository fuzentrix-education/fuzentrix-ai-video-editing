---
name: approve
description: Record a video editor's approval of a video's beat sheet or storyboard and continue the edit (write and build the edit after the beat sheet, render after the storyboard).
argument-hint: "<video folder> beats|storyboard"
disable-model-invocation: true
---

# Record the editor's approval

The editor typed this (or pasted it from the review page's **Copy approval for Claude** button), so it is their approval.

Request: `$ARGUMENTS`: the video folder, then `beats` or `storyboard`.

1. Run `bin/fzv approve "<folder>" <beats|storyboard> --note "approved by the editor"`. If it reports problems (a beat sheet with
   unfilled rows, a storyboard older than the latest build), fix them, show the editor what changed and ask again; don't approve
   something they haven't seen.
2. Continue the edit-video skill:
   - after **beats**: write `edit/edit.yaml` from the approved beat sheet, build, validate, make the storyboard and show it (step 3);
   - after **storyboard**: render with `bin/fzv edit "<folder>"` in the background and hand over the final (step 4).
3. Tell the editor in one line what happens next and roughly how long it takes.
