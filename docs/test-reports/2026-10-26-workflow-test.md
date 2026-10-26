# Workflow test, 2026-10-26

Two real videos were taken from raw files to a verified final MP4 through the documented flow (`fzv edit` → plan brief → spec →
build → validate → preview → render → finish → verify → revise), on the 8 GB M1 that the team uses. The machine was heavily
swapped during the test (about 44 GB of app memory against 8 GB of RAM), so the times below are pessimistic.

## The two videos

| | Loop Control Statements | DBMS Trail |
|---|---|---|
| **Input** | 899 s editor's rough cut, 50 fps, plus a separate 130 s screen recording | 237.5 s green-screen take, 59.94 fps |
| **Prompt** | `Recording: reference`; make the three example programs the highlight | `Music: calm-piano, low`; instructor in focus first, then bottom right; key terms easy to remember |
| **Mode** | overlay (detected) | compose (detected) |
| **Spec** | from the plan brief, starting from `examples/loop-control` (same video) | written from the plan brief from scratch: 10 sections |
| **Final** | `workflow-test/loop-control/Loop Control Statements - Edited.mp4` | `workflow-test/dbms-trail/DBMS Trail - Edited.mp4` |
| **Verify** | OK: 899.32 s, 50 fps, −14.0 LUFS, −1.0 dBTP | OK: 237.54 s, 30 fps, −14.0 LUFS, −1.0 dBTP |

## What each stage did

**Loop Control**
- **Ingest:** all 28 shots found to the frame; recording aligned at 531.82 s (confidence 0.913), IDE measured at y 304–932,
  16 keyframes saved; 95 transcript chunks.
- **Spec and build:** Example 2 rebuilt from the recording (never shown, rule E8). The card types each line when it was typed in the
  recording; the terminal runs the program with the `20` she typed and prints the real output `20 / 1 … 10` (rule E7). Correction
  logged: `range(1,n+1)` → `range(1, n+1)`, output unchanged (rule E9).
- **Validate:** OK, 183 SFX cues. **Render:** 22 clips, 25,207 frames, one worker. **Build → verify:** 49 min 52 s.
- **Revision 1** ("14:56 add a short Thank-you card"): logged by `fzv revise`, applied, verified. The whole video re-rendered once
  (40 min) because templates had changed during the test.
- **Revision 2** ("14:44 header should read 'Today we covered'"): one clip re-rendered (18 s) and one encode chunk re-encoded; render +
  finish 2 min 20 s. Both requests are marked done in `edit/revisions.md`.

**DBMS**
- **Ingest:** compose mode; green screen keyed with `key: {exclude, exclude_poly, cut_below}` so only the instructor travels (no laptop,
  no desk): an 858×746 cut-out instead of 1920×796. Keying ≈ 15–20 min per pass.
- **Spec and build:** name card (she introduces herself), Data / Information / Database / DBMS terms, student table, CRUD chips,
  request-flow blocks, recap, Apollo fact with a prop; one presenter move (wide intro, then bottom right). Build 0.3 s.
- **Validate:** caught the intro graphics touching her hair in the wide pose and the title "Information" overflowing its card;
  both fixed before rendering.
- **Render:** 10 clips, 7,126 frames, ≈ 11–13 min. **Finish:** 53 s with music ducked under the voice. **Sync:** presenter within one
  frame of the audio (hand-motion check).

## Problems found and fixed

| Area | Problem | Fix |
|---|---|---|
| Ingest | `plan`/`edit` didn't wait for the background transcript | `plan` waits; progress shown |
| Ingest | A half-written transcript counted as complete; a stopped transcription never restarted | `transcript.done` marker, `transcribe.pid`, resume from the last chunk |
| Ingest | Green-screen footage was detected as an editor's rough cut | `auto_mode`: overlay needs an edited layout (shots + corner/empty plate) |
| Transcript | Whisper repetition loops ("colon colon colon…") | temperature fallback 0 → 0.2 → 0.4, repeat clean-up |
| Keyer | Keyed the full frame, then cropped (slow) | crop in the decoder first (~3× less work) |
| Keyer | An interrupted run left a "finished" `presenter.webm` | write `.part`, rename when complete |
| Keyer | Laptop edge beside the arm; green fringe on the jacket | `exclude_poly` polygons; green-limit despill |
| Keyer | Keyed at 25 fps but rendered at 30 (judder) | key at the graphics rate; verify expects it in compose mode |
| Build | Re-encoded the presenter for every section (~12 min) | `data-playback-start` on one keyed WebM (0.3 s) |
| Validate | No safe-zone check in compose mode | live presenter box × the instructor's alpha occupancy (rule L2) |
| Validate | Missed a single word wider than its card | leaf overflow check (T3) |
| Templates | Long tile values and contrast titles overflowed | text shrinks to fit |
| Templates | Counter showed `10000` | Indian digit grouping (`10,000`) |
| Cache | Any template change re-rendered every clip; a re-keyed presenter could reuse stale renders | cache key = used template files + media size/mtime |
| Revise | Validation re-sampled every clip | samples cached per clip hash (22 s cold, 0.5 s warm) |
| Finish | Music path failed (voice label used twice in the mix) | `asplit` for the ducking sidechain; test added |

## Still open

- **Memory:** close the VM and heavy apps before long runs; transcription and rendering slow down sharply when swapping.
- **Transcripts** are English-mode on Telugu + English speech: good for timing, approximate for content (by design, §12.3).
- **To confirm** (in each `decisions.md`): Example 3's code rebuilt from dictation; the name "Swara" as heard; "CSE" where the
  transcript has "CSC"; the illustrative second row of the DBMS student table.
