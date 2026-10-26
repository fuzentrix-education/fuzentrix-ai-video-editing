# prop-scene

**Family:** props · **Layers:** plate

A small staged scene: a ground line (road or desk) with several props, each with its own entrance and moves.

| Parameter | Meaning |
|---|---|
| `ground` | road | desk | none |
| `box` | scene area x, y, w, h (ground sits at the bottom) |
| `at` |  |
| `until` |  |
| `props` | [{asset, x, y, w, h (relative to box), at, flip, moves: [{to: [x, y], at}], react: [{kind, at}]}] |

_Generated from runtime/templates; edit the template's meta there._
