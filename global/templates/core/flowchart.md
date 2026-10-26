# flowchart

**Family:** core · **Layers:** plate

Nodes and arrows, with an optional marker that walks the path. Node coordinates are relative to the box.

| Parameter | Meaning |
|---|---|
| `nodes` | [{id, x, y, w, h, text, kind: box|term|dec|ok, at}] |
| `edges` | [{from, to, label, tone: hot|green|red, at, path: optional svg path in box coords}] |
| `walk` | [{node, at}] |
| `until` |  |
| `box` | default: main slot |

_Generated from runtime/templates; edit the template's meta there._
