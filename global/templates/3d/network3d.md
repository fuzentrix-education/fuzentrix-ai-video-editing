# network3d

**Family:** 3d · **Layers:** plate

3D: devices on a floor (person, laptop/client, server, database) joined by arcs; request and response packets travel along them on their words. For client/server, user -> DBMS -> database, APIs. One hero moment per video.

| Parameter | Meaning |
|---|---|
| `nodes` | [{id, kind: person|laptop|server|database, text, x, z, at}] x -5..5, z -3..3 (floor units) |
| `links` | [{from, to, at}] arcs draw on at `at` |
| `packets` | [{from, to, label, at, dur, kind: req|res}] |
| `at` |  |
| `until` |  |
| `box` | x, y, w, h (default main slot) |

_Generated from runtime/templates; edit the template's meta there._
