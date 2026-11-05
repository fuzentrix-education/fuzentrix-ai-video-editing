# freeform

**Family:** core · **Layers:** plate, studio

Free composition for a moment no template shows well: your own markup (the kit's classes and --fz-* colours, sizes from the type scale) and its animation steps, each on her word. Checked like any scene (sync, sizes, overlaps).

| Parameter | Meaning |
|---|---|
| `html` | markup inside the box; give parts classes or ids to animate (start hidden ones with class `hide`) |
| `box` | x, y, w, h |
| `at` |  |
| `until` |  |
| `steps` | [{sel: CSS selector inside, at, from: {y, x, scale, opacity…} (enter from), to: {…} (change to), dur, ease, out: time, sfx: kind}] |

_Generated from runtime/templates; edit the template's meta there._
