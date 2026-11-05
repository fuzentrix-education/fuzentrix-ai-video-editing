# presenter

**Family:** presenter · **Layers:** plate

Keyed instructor with poses: studio (her whole studio shot, laptop and desk, life-size and centred: the intro), wide, close, side-right, side-left, corner (bottom right, boxed). Added automatically in compose mode from the spec's `presenter.poses`.

| Parameter | Meaning |
|---|---|
| `poses` | [{name, at, x, y, scale (optional custom)}] |
| `crop` | [x, y, w, h] of the cut-out in source pixels (set by ingest) |
| `box` | {w, h, margin, radius}: the bottom-right pose sits in a rounded box (setting presenter.corner_box) |
| `studio` | [{t0, t1, el, crop}]: the keyed studio shots this clip shows (set by build) |
| `max_scale` | largest face enlargement (default 1.1: never soft) |

_Generated from runtime/templates; edit the template's meta there._
