# Editor guide: editing a video with Claude

You edit by chatting with Claude inside VS Code. Claude does the technical work. You decide what the video shows, and you
approve it twice before the slow render: first the **storyboard** (one frame per beat), then the **preview** (the whole edit playing
with its sound).

## Once per computer

Someone technical sets this up once (about 15 minutes; [WORKFLOW.md §0](WORKFLOW.md#0-once-per-machine)):
1. Install VS Code and the **Claude Code** extension, and sign in with the team's Claude account.
2. Get the `fuzentrix-ai-video-editing` folder and run `bin/setup` in it once.
3. In VS Code, choose **File → Open Folder** and pick `fuzentrix-ai-video-editing` itself (not a folder above it), so
   Claude finds the team's shortcuts.

## Each video

1. **Start.** Open the Claude panel and type, for example:
   `/edit-video ~/Desktop/DBMS TRAIL.mp4  show the screen recording, highlight the three examples`
   Claude makes a folder for it in `videos/`, asks anything it needs (once), and starts. Transcription takes a few minutes.
2. **Claude plans the edit.** It writes the beat sheet (one row per idea the instructor explains: what we show and on which
   words) and goes straight on to the storyboard; you don't need to approve the plan. (If you want to see the plan first, start with
   "Review: beats, storyboard".)
3. **Approve the storyboard.** Claude shows the storyboard straight away: a grid of frames, one per beat, with the graphics over the
   real footage. It's on the review page, and saved in the video's folder as `<Title> - Storyboard.jpg`. Click a frame to see it large
   (arrow keys step through) and write a change for that beat right there ("use a car here", "skip this", "beat 7: make this the
   highlight"), click **Copy for Claude** and paste it into the chat. Happy with it: click **Approve the storyboard**, or just type "approved".
4. **Approve the preview.** Then Claude opens the **live preview** in HyperFrames Studio: the whole edit playing in your browser with
   its real sound, before anything is rendered (press play, scrub the timeline; the music is its own track you can mute). Write a
   change at a time, or click **Approve the preview** (or type "approved, render it"). You can also ask for the live preview at any
   time ("open the live preview" or `/preview <folder>`).
5. **Get the final video.** Claude renders (10–40 minutes) and opens the page again with the video, a frame per beat, and a
   short **To confirm** list (for example code rebuilt from what the instructor dictated). If the listening check heard a problem (an
   effect buried or too loud, noise, music too loud), it's listed under **Listening check**. The video is saved as
   `videos/<name>/<Title> - Edited.mp4`.
6. **Music on or off.** Under the video on the review page, switch **Background music** On / Off while it plays to hear the
   difference, pick a level, and press **Keep this for the final**, then **Copy for Claude**. Only the sound is redone (a minute or two).
7. **Ask for changes at any time.** On the page, pause the video where something should change, type the change, click
   **Add at m:ss**, then **Copy for Claude** and paste. Or type: `/change videos/dbms-trail 7:41 make the note bigger`.
   Only the changed parts are rendered again, so a small change takes minutes.

## Shortcuts

| Type in the Claude panel | What happens |
|---|---|
| `/edit-video <folder or video file> [notes]` | starts an edit, or continues one |
| `/review <folder>` | tells you where the video stands and opens its review page |
| `/change <folder> beat 7: … ; 7:41: …` | changes things, by beat number or by time in the video |
| `/approve <folder> storyboard` | approves the storyboard; then `/approve <folder> preview` approves the preview and starts the render (`beats` only when you asked to review the plan too) |
| `/preview <folder>` | opens the live preview in HyperFrames Studio (`/preview <folder> stop` closes it) |

Plain sentences work too: "where is the DBMS video?", "at 3:10 the text is too small".

## What to say when you start

- **Brand:** nothing to choose. Every video uses the one Career Orbit kit (LMS colours and fonts, dotted background).
- **Screen recording:** show it as it is, or "rebuild it" when it is messy. Claude then recreates the code and its output as
  clean animation, fixes typos and lists every fix for you to confirm.
- **Music:** off unless you ask, for example "calm piano, low".
- **3D:** off unless you ask. Write "use 3D animations" (or name the moment: "3D for the database part") and Claude adds 3D
  for one or two big moments.
- **Instructor box:** on by default (a bottom-right instructor sits in a rounded brand box). Say "box off" to leave them as they are.
- **Voice:** cleaned by default (background noise, rumble and harsh "s" sounds removed, volume kept steady). Say "voice untouched" to keep it exactly as recorded.
- **Chapters:** on by default (the chapter number and name top left). Say "chapters off" to hide it.
- **Logo:** not in the video; add the Career Orbit logo after the final render. Say "logo on" to have it put top right instead.
- **What to highlight:** "make the three example programs the highlight", "show data going into a database when they talk about storing data".
- **Review:** on by default: you approve the storyboard, then the preview. "Review: beats, storyboard" adds the plan (beat sheet) before them;
  "Review: off" skips approvals, for quick tests only.

## What Claude always does

- Uses only what the instructor says in the video (never a script or PDF), keeps the original timing, never covers the instructor.
- Animates every explanation in step with the words, one idea on screen at a time.
- Shows real program output: it runs the code.
- Adds no subtitles, outro or music unless you ask. Sound effects come from the team's library.

## If something looks wrong

Tell Claude in plain words. If VS Code asks "Allow this command?" for something unusual, ask a technical teammate before
saying yes.
