# request-flow

**Family:** explainer · **Layers:** plate

Nodes with big icons; packets travel along curved links when they are sent (request -> processing -> result back). Optional blocked direct path. For client/server, user -> DBMS -> database, API calls.

| Parameter | Meaning |
|---|---|
| `nodes` | [{id, text, icon, x, y, at}] (box coords) |
| `links` | [{from, to, at}] |
| `packets` | [{from, to, label, at, dur, kind: req|res}] |
| `blocked` | {from, to, label, at} dashed red arc with a cross |
| `results` | [{text, at, x, y}] small cards that appear (e.g. the returned record) |
| `at` |  |
| `until` |  |
| `box` | default: main slot |

_Generated from runtime/templates; edit the template's meta there._
