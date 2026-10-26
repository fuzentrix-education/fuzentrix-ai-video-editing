# data-flow

**Family:** explainer · **Layers:** plate

Items (chips with icons) fly into a container (database, table, folder, server, cloud) as they are named; the container fills and counts. For collecting / storing / saving data.

| Parameter | Meaning |
|---|---|
| `target` | {kind: database|table|folder|server|cloud, label, x, y, size} (box coords; default right side) |
| `items` | [{text, icon, at, x, y}] flying in at `at` (sources default to a column on the left) |
| `count` | {to, label} the container counts up as items arrive (optional) |
| `at` |  |
| `until` |  |
| `box` | default: main slot |

_Generated from runtime/templates; edit the template's meta there._
