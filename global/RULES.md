# House rules: the master prompt every edit follows

Every video gets these rules; Claude reads them in each video's brief (`edit/plan_brief.md`). They adapt the team's master prompt
("Professional LMS video editing", v5) to this workflow: content comes from the instructor's audio (no PPT), the look is the one
Career Orbit kit, and most rules are checked automatically (`rules.yaml`, `fzv validate`). A video's prompt may override a rule for that
video; every override is logged in `edit/decisions.md`. The full table with check types is in `docs/SYSTEM_DESIGN.md` §8.

**Goal:** a modern, professional, student-friendly lesson: the instructor teaching naturally, clean graphics that explain on her exact
words, subtle sound that adds depth, and her voice never interrupted.

**Limits and freedom (2026-11-05):** the checked rules are the limits: on her words (S2–S4), readable (L13), clean and aligned (L10,
L12, L14), never covering her (L2), the kit's colours, free licences, her voice untouched. Everything else is a starting point, not a
formula: which template, which layout, which examples and pictures, how a screen builds. Look at each moment fresh, consider two ideas,
pick the one that teaches best, and don't repeat a pattern just because it worked before. When no template shows it well, compose it
yourself (`freeform`: your own markup in the kit's style, animated on her words).

## 1. Content and sync
- Understand the whole lesson first (the beat sheet), then sync every graphic, highlight, code line and output to the word that names it
  (±0.3 s). Nothing appears before she says it; nothing stays after the point ends.
- **Times are her words, not seconds.** Write every `at` as an anchor on the word (`"@2026"`, `"@immutable"`, `"@15#2"` for the
  second time she says it), and give each item of a group its own word: tiles `appear: ["@15", "@8", "@2026"]`, agenda items, chips,
  card fields. Numbers match exactly; `fzv words <folder> <from>-<to>` prints the exact words and times.
- **Nothing early, no previews (S2, checked):** a value, label or picture is never on screen more than 0.15 s before she says it
  (a title: 1 s). No faded "coming next" tiles or grey placeholders: an item appears when it is named.
- **Nothing late (S5, checked):** and never more than 0.3 s after it: anchor the value on its own word, not the start of her
  phrase. Both are timed to the frame (2026-11-05, from the Career Orbit kit's sync audit). Where her Telugu was misheard, anchor
  on the Telugu transcript (`"@te:…"`, `fzv words <folder> --te`); those times are trusted. The Telugu transcript is made at ingest
  (in the background), and `fzv validate` lists the anchors where the two transcripts disagree by more than 0.5 s (S6, advice):
  check each one; in Telugu speech the Telugu one is usually right.
- **Follow her (S3):** when she repeats a value that is on screen ("day is 15, month 8…"), it reacts on her word: tiles `focus`,
  form-card `focus`, a code `highlights` entry. The item she is talking about gets the warm amber outline (Rani's look); the one chosen (the index asked for) is solid blue.
- **Never frozen (S4, checked):** while she explains, something on screen changes at least every 8 s: the next step, a highlight,
  a focus on what she is talking about.
- Content and timing come from the video's own audio only (Telugu and English). Never from a script, PDF or PPT.
- Never cut or extend her footage. No subtitles and no outros unless the prompt asks.
- Program output is real: terminals print through `exec`, which runs the code shown. Never type output by hand.
- Anything shown that she didn't say outright goes under "to confirm". The name card appears only when she introduces herself.

## 2. Show the process (motion graphics)
- When she explains how something works, **show it happening**: data flies into the database, `"20"` converts to `20`, `range` emits
  1…n, a pointer scans a string, values drop into a Venn diagram. Text cards label; animations explain.
- Every step lands on the word that names it. A new visual roughly every 8–12 s; never more than 15 s of words-only screen.
- Cover the concept moments `fzv plan` lists (`global/concepts.yaml`) that fit the lesson, or say why not.
- **Never repetitive (V5):** no animation twice in a row, none in more than 20% of a video's animations.
- Clean, minimal, soft motion: no spins, wipes or flips; animate only position, scale and opacity. 3D only when the prompt asks (S1).
- **Clutter:** at most 4 blocks, 40 words and 12 code lines on screen at once. One idea at a time.
- **Make it better than the words alone (P2):** add what a good editor would, listed under "to confirm": a question opener when she
  starts a new idea ("Why & where do we use tuples?", a big title while she stays in the box), more real-world examples of what she says (fixed values
  -> calendar dates, map coordinates, RGB colours), an "accessing values" list as she names indexes (date[0] -> 15), a key-property
  title. Never against what she says, never cluttered.
- **Pictures (P1):** when she uses an analogy or a real-world example (a calendar, a water bottle, a map, colours), a picture shows it
  on her word, with a short caption bubble (`picture`). Only at key points, one at a time, never crowding a diagram. The library first,
  then free illustrations from the web (`fzv illus search … --online`: CC0 / MIT / no-credit licences only, checked on the source's
  page, in their own natural colours), and if nothing fits, an illustration drawn in the house style (global/props/ILLUSTRATION-STYLE.md).
  Never logos, brands, photos of real people, or anything that needs a credit.
- **Never a plain-instructor stretch (L4):** plate shots never sit empty for more than 2 s; every studio shot carries a light
  studio-layer graphic.
- **Cutaways:** short and only when the prompt allows them: 12 s each at most, 10% of the runtime in total.

## 3. The instructor
- **Rough cuts:** she is untouched: no halo, circle, blur or cut-out. Graphics go only in the empty space and never cover her (L2).
- The bottom-right instructor sits in a rounded box (setting `presenter.corner_box`; prompt `Presenter box: off`).
- **Raw footage (compose mode):** the intro is her **studio shot**: life-size and centred with the laptop and desk (pose `studio`,
  keyed onto the kit's backdrop, never the old slide behind her), like the manual edit. When the intro ends the whole studio frame
  shrinks into the bottom-right box and she stays there (pose `corner`), like Harshith's layout. No other moves unless the prompt asks
  (user 2026-11-05: "I didn't ask to move the tutor"). Graphics land after a move has settled (about 1 s after it starts).
- The corner box is roomy (520 x 480): her whole upper body, her hands and the near end of the laptop, never cut tight at the head
  or hands (user 2026-11-05: "keep it freely").
- Her face is never enlarged beyond 1.1x (it would soften); natural, no smoothing or beauty filters, true skin tone.
- Sections join softly: graphics fade out before a section ends and the next ones fade in; the backdrop and the tutor never cut.

## 4. Code and screen recordings
- Code is shown in the dark editor with the LMS code editor's colours, typed in step with her dictation; Run flashes when she runs it.
- Explanations sit outside code cards and terminals, joined by thin blue pointer lines routed around other graphics.
- Recordings are shown whole and in order, never cropped, zoomed, cut or rearranged. Only a messy recording is rebuilt, when the prompt
  says `Recording: reference`; every correction is logged and confirmed.

## 5. The look (one brand kit, `global/brand/brand.yaml`)
- Navy text and one brand blue, with Rani's highlighting (2026-11-05): blue section kickers with a dot ("• EXAMPLE 1"), and an amber
  highlighter marker under the key word of a title and under each phrase as she says it (definitions, problem statements). Green
  = correct / True / output, red = error / False, amber rings = look here. No colour per topic.
- **Not everything blue (user, 2026-11-05: "images and other properties should have natural colors"):** text and UI may be blue;
  pictures keep their own natural colours (never recoloured), the item she talks about gets the warm amber outline (solid blue only
  for the one chosen), labels in a row of parts use Rani's blue / green / amber, captions sit on white cards. A date is Rani's
  `calendar` (navy month bar, the day lighting up, Day / Month / Year rows beside it).
- The light dotted backdrop (faint dots, like Rani's) stays for the whole video (L11): no dark scenes or full-frame cutaways unless
  the prompt asks.
- Highlights: the amber marker sweeps under the words on her word; code highlights are amber boxes; the item she talks about in a row
  of values gets the amber outline (`pick`: solid blue for the one chosen).
- The chapter pill top left on every frame (chapter number, chapter name · lesson). Give every section after the intro a short
  `chapter:` name. No logo in the video: the team adds the Career Orbit logo after the final render (prompt `Logo: on` burns it in
  top right); keep the top-right corner clear.
- **One type scale** (`brand.yaml` type-scale, the templates read it): titles 64 px, body 32, captions 26, labels 22 and never
  anything smaller (L13); code 52 px, shrinking only to fit, never below 40. Sharp, few sizes, generous line spacing. Ligatures off.
- **Two fonts with clear jobs (user, 2026-11-05):** Bricolage Grotesque only for headings, titles and big statements (40 px and up);
  Inter for everything else: body text, agenda rows, cards, chips, labels, tiles and values (the heading font inside small cards
  "is not looking good"); JetBrains Mono for code and output.
- **Titles on one line (L15, 2026-11-05):** headings and hero titles never wrap ("Career Orbit", "Previous session"); the templates
  shrink them to fit their box (hero to 64 px, headers to 46) and report one that still doesn't fit: shorten it or widen the box.
- **One grid** (L14): every block starts at the left margin (96 px) or lines up with the block above or beside it; content sits in
  the column left of the tutor box, top-aligned under the header. Empty space is fine; misaligned space is not.
- **One motion:** things fade in with a soft 24 px rise, values and pictures settle gently, exits fade with a small lift. No wipes,
  spins, flips or bounces (`brand.yaml` motion; templates use it).
- **Blocks never cover each other** (L12): place the next card below the previous one's real height.

## 6. Sound
- **Her voice is the priority:** never cut, muted, faded or lowered for anything. It is cleaned, keeping her natural tone: rumble filter,
  speech denoiser, slight EQ for clarity, gentle levelling for a steady volume, softer "s" sounds (prompt `Voice: untouched` turns
  this off).
- **Sound effects** on meaningful visual events only, never on every element, at most 10 a minute. The editors' house set
  (`global/sfx`, picked by ear 2026-11-04): Soft Pop when a card or picture appears (Alternative UI Tone every third time), Digital Blip
  for a value or chip, UI Click for Run and selections, Decision Click when a highlight picks an option, Soft Tick for a step or a
  focus move, Soft Ticks while counting, Short Digital Stop when a loop breaks, Quick Whoosh for chapter changes and presenter moves,
  Page Flip for a new topic, Gentle Error Buzz for errors, Positive Notification for correct output, Success Chime for the final
  answer, a key press for typing, Cartoon Boing only for a playful "no". Transitions (dissolves) stay silent. A moment no template
  covers gets its sound with the `sound` scene. Not limited to this set: when a moment needs another sound, add a free CC0 one.
- They sit 18–26 dB under her voice by kind and dip 3 dB more while she speaks, so they never mask a word. Only the effects are ducked,
  never the voice. The team's library first; never the same file twice in a row.
- Music only if the prompt asks: audible but well under the voice, ducked while she speaks.
- Final mix: −14 LUFS, −1 dBTP.

## 7. Plan, approve, check
- Plan per idea in the beat sheet (`edit/beats.yaml`): what each beat shows and on which words.
- Before showing anything, the build is checked automatically: sync, clutter, overlap, text overflow, the instructor's safe zone,
  repetition, background changes.
- Two approvals before the render, in order: first the storyboard (one frame per beat, shown directly; saved in the video's folder as
  `<Title> - Storyboard.jpg`), then the preview (the whole edit playing live with real sound). The beat sheet too only with
  `Review: beats, storyboard`. Render only after an explicit "render" or "approved". Any later
  change needs a new approval, and only the changed parts are rendered again.
- After the render, verify: length, frame rate, size and loudness, a frame sheet, and the listening check (measures the final mix:
  effects buried under her voice or too loud, clipping, background noise, music too loud or too quiet).

## 8. Delivery
- 1920×1080, H.264, AAC 320k. Overlay edits keep the source frame rate; compose edits render at 30 fps.
- Earlier finals move to `edit/_prev/` and are never deleted.

## Non-negotiables
- Content from her audio only, synced to her words.
- Her voice never interrupted, lowered or masked.
- Show the process, never just a card that names it.
- One kit: navy and blue, colour only for meaning, the dotted backdrop all video.
- Never clutter, never overlap, never cover her.
- No render before the editor approves the storyboard and then the preview.
