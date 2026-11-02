# loop3d

**Family:** 3d · **Layers:** plate

3D: loop values ride a conveyor one per iteration through a gate that checks the condition; passing values drop into an output tray, the break value turns the gate red and the belt stops. For for-loops, range(), break.

| Parameter | Meaning |
|---|---|
| `values` | [values] in loop order |
| `times` | [time per value] when each value reaches the gate |
| `cond` | condition label on the gate, e.g. 'i == 6' |
| `stop_value` | value where break stops the loop (optional) |
| `label` | caption above the belt (markdown) |
| `at` |  |
| `until` |  |
| `box` | x, y, w, h (default main slot) |

_Generated from runtime/templates; edit the template's meta there._
