# recording-window

**Family:** code · **Layers:** plate

The whole screen recording in a branded window, never cropped or zoomed (rule L7); step tracker in the title bar; highlight boxes in recording coordinates. Registers `id` for notes. Needs a recording listed in the spec's recordings.

| Parameter | Meaning |
|---|---|
| `id` | recording id (from recordings) |
| `title` | window title |
| `at` |  |
| `until` |  |
| `box` | x, y, w[, h] (fits inside; aspect kept) |
| `steps` | [{label, at}] |
| `highlights` | [{name, box: [x, y, w, h] in recording pixels, at, until}] |
| `hide` | [{at, until}] periods to hide the window (e.g. concept scenes) |

_Generated from runtime/templates; edit the template's meta there._
