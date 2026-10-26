# House rules (one-page version)

These are the defaults for every video. A video's prompt may override any of them for that video; every override is logged in `edit/decisions.md`. The full table with check types is in `docs/SYSTEM_DESIGN.md` §8, and the machine-checked list is in `rules.yaml`.

**Content**
- Content and timing come from the video's own audio only. Never from a script.
- Never cut or extend the instructor's footage. No outros.
- Subtitles off unless the prompt asks.
- Show the name card only when the instructor introduces themself.
- Anything shown that wasn't said outright goes under "to confirm".
- **Program output is real:** terminals print through `exec`, which runs the code shown. Never type output by hand.
- **`Recording: reference`:** the recording is never shown; code and output are rebuilt as animation from its keyframes.
- **Corrections:** a rebuilt card may fix the recording's typos, spacing and false starts (logged); a fix that changes the output must be explained and confirmed.

**Layout**
- **Rough cuts:** the instructor is untouched. No halo, circle or blur. Graphics go only in the empty space. The one exception is the
  rounded brand box at the bottom right (setting `presenter.corner_box`, on by default; prompt `Presenter box: off`).
- **Never a plain-instructor stretch:**
  - plate shots never sit empty for more than 2 s
  - every studio shot carries a light studio-layer graphic
- **Cutaways:** short, only when needed. 12 s each at most, 10% of the runtime in total.
- **Raw footage (compose mode):** focus on the instructor in the intro, then one fixed spot (bottom right), framed in a rounded brand box. Two moves at most.
- **Code:** explanations sit outside code cards and terminals.
- **Recordings:** shown whole, never cropped or zoomed.
- **Clutter:** at most 4 blocks, 40 words and 12 code lines on screen at once. One idea at a time.

**Show the process**
- When the instructor explains how something works, **show it happening**: data flies into the database, `"20"` converts to `20`,
  `range` emits 1…n, a request travels and the result comes back. Text cards label; animations explain.
- Every step lands on the word that names it. A new visual roughly every 8–12 s; never more than 15 s of words-only screen.
- Cover the concept moments `fzv plan` lists (`global/concepts.yaml`), or say why not. Guide: `global/styles/explainer/STYLE.md`.

**Type and motion**
- Brand fonts and sizes only. Text no smaller than 26 px; code no smaller than 30 px. Code ligatures off.
- Motion timings come from the brand kit; animate only transform and opacity.
- Every change lands on a spoken word (±0.3 s).

**Audio and delivery**
- Voice untouched apart from a 70 Hz high-pass.
- **Sounds on the visual events, never repeated:** the team's SFX library first (`fzv sfx add`), files rotating per category; synthesised fallback varies every take.
- Music only if the prompt asks; audible but well under the voice.
- −14 LUFS, −1 dBTP.
- 1920×1080 at the source fps, H.264, AAC 320k.
- Earlier finals move to `edit/_prev/` and are never deleted.
