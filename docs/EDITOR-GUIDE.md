# Editor guide: editing a video with Claude

You edit by chatting with Claude inside VS Code. Claude does the technical work. You decide what the video shows, and you
approve it at two points before the slow render: the **beat sheet** (the plan) and the **storyboard** (a preview).

## Once per computer

Someone technical sets this up once (about 15 minutes; [WORKFLOW.md §0](WORKFLOW.md#0-once-per-machine)):
1. Install VS Code and the **Claude Code** extension, and sign in with the team's Claude account.
2. Get the `fuzentrix-video-editing-automations` folder and run `bin/setup` in it once.
3. In VS Code, choose **File → Open Folder** and pick `fuzentrix-video-editing-automations` itself (not a folder above it), so
   Claude finds the team's shortcuts.

## Each video

1. **Start.** Open the Claude panel and type, for example:
   `/edit-video ~/Desktop/DBMS TRAIL.mp4  Career Orbit, show the screen recording, highlight the three examples`
   Claude makes a folder for it in `videos/`, asks anything it needs (once), and starts. Transcription takes a few minutes.
2. **Approve the beat sheet.** Claude opens the **review page** in your browser: one card per beat (one idea the instructor
   explains), with what they say, what we will show, and on which words it appears.
   - Happy with it: click **Copy approval for Claude** and paste it into the chat, or just type "approved".
   - Want changes: write under any beat ("use a car here", "skip this", "make this the highlight"), click **Copy for Claude**
     and paste it into the chat. Or type it directly: "beat 7: use a car".
3. **Approve the storyboard.** The page now shows one frame per beat, with the graphics over the real footage, before anything
   is rendered. Approve it or ask for changes the same way.
4. **Get the final video.** Claude renders (10–40 minutes) and opens the page again with the video, a frame per beat, and a
   short **To confirm** list (for example code rebuilt from what the instructor dictated). The video is saved as
   `videos/<name>/<Title> - Edited.mp4`.
5. **Ask for changes at any time.** On the page, pause the video where something should change, type the change, click
   **Add at m:ss**, then **Copy for Claude** and paste. Or type: `/change videos/dbms-trail 7:41 make the note bigger`.
   Only the changed parts are rendered again, so a small change takes minutes.

## Shortcuts

| Type in the Claude panel | What happens |
|---|---|
| `/edit-video <folder or video file> [notes]` | starts an edit, or continues one |
| `/review <folder>` | tells you where the video stands and opens its review page |
| `/change <folder> beat 7: … ; 7:41: …` | changes things, by beat number or by time in the video |
| `/approve <folder> beats` or `storyboard` | approves the plan or the preview |

Plain sentences work too: "where is the DBMS video?", "at 3:10 the text is too small".

## What to say when you start

- **Brand:** Career Orbit or Fuzentrix.
- **Screen recording:** show it as it is, or "rebuild it" when it is messy. Claude then recreates the code and its output as
  clean animation, fixes typos and lists every fix for you to confirm.
- **Music:** off unless you ask, for example "calm piano, low".
- **Instructor box:** on by default (a bottom-right instructor sits in a rounded brand box). Say "box off" to leave them as they are.
- **What to highlight:** "make the three example programs the highlight", "show data going into a database when they talk about storing data".
- **Review:** on by default. "Review: off" skips both approvals; use it only for quick tests.

## What Claude always does

- Uses only what the instructor says in the video (never a script or PDF), keeps the original timing, never covers the instructor.
- Animates every explanation in step with the words, one idea on screen at a time.
- Shows real program output: it runs the code.
- Adds no subtitles, outro or music unless you ask. Sound effects come from the team's library.

## If something looks wrong

Tell Claude in plain words. If VS Code asks "Allow this command?" for something unusual, ask a technical teammate before
saying yes.
