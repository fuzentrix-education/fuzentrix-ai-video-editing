# presenter

**Family:** presenter · **Layers:** plate

Keyed instructor with poses: wide, close, side-right, side-left, corner (bottom right). Added automatically in compose mode from the spec's `presenter.poses`.

| Parameter | Meaning |
|---|---|
| `poses` | [{name, at, x, y, scale (optional custom)}] |
| `crop` | [x, y, w, h] of the cut-out in source pixels (set by ingest) |
| `box` | {w, h, margin, radius}: the bottom-right pose sits in a rounded box (setting presenter.corner_box) |

_Generated from runtime/templates; edit the template's meta there._
