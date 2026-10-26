# range-gen

**Family:** explainer · **Layers:** plate

A range generator emits its numbers one by one into slots (first ones paced, the rest quickly), optionally stopping at a break value. For range(), loops generating values.

| Parameter | Meaning |
|---|---|
| `call` | e.g. range(1, n+1) |
| `n` | optional 'n = 20' tag |
| `start` | first value (default 1) |
| `end` | last value generated (inclusive) |
| `max_slots` | slots shown (default 10; longer ranges show … and the last) |
| `at` |  |
| `emit_at` | first number |
| `pace` | s per number (default 0.45) |
| `times` | [time per number] instead of pace |
| `stop_value` | value where `break` stops the loop |
| `stop_at` | time it stops |
| `note` | {text, at} (e.g. 'n+1 is not included') |
| `until` |  |
| `box` | x, y, w (default main slot) |
| `size` | slot px (default 78) |

_Generated from runtime/templates; edit the template's meta there._
