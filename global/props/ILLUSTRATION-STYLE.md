# House style for illustrations Claude draws (rule P1)

Used only when the library and the free sources (`fzv illus search <words> --online`) have nothing that fits. The goal is to sit
next to the imported sets (Lukasz Adam, illlustrations.co, Open Peeps) without looking different.

- **Flat vector, simple shapes.** Rounded rectangles and circles, a few paths. No gradients, no shadows except one flat ellipse
  under the object (#102A56 at 15% opacity), no textures, no text inside the picture (captions are separate).
- **Natural colours, like the imported sets** (2026-11-05: pictures are not all kit blue): navy outlines (#102A56), the object's
  own colours in soft flat tones (a red calendar top, an orange box, a green plant, a yellow bulb, a grey laptop), light fills
  #FFFFFF / #EEF2F8, and green / red only when the picture means correct or wrong. At most 3–4 colours per picture.
  Skin tones from the library's palette (#F1C7A3, #D9A37E, #A8714F, #6E4A33) when people appear.
- **Outline:** 6 px navy stroke, round caps and joins, on a 400 x 300 viewBox (or 300 x 300), drawing filling about 80% of it.
- **One idea per picture:** the object she is talking about (a bottle being filled, a locked box, a calendar page), large and
  centred, at most one small extra (a check, a question mark, an arrow).
- **No people's faces from life, no logos or brand marks**, nothing copied from a copyrighted picture.
- Save as `edit/pictures/<name>.svg`, add with `bin/fzv illus add edit/pictures/<name>.svg --id il-<name> --title "…" --tags "…"
  --source generated --licence "Fuzentrix (original)"`, then preview it at its size in the frame and fix anything that reads badly.
