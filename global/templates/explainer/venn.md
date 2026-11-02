# venn

**Family:** explainer · **Layers:** plate

Two sets as circles that draw on; each value pops into its region as it is said; an operation fills its region (union, intersection, difference, symmetric difference) in the brand blue; amber rings point at values, red strikes skip them; an optional result row.

| Parameter | Meaning |
|---|---|
| `a` | {label, at} |
| `b` | {label, at} |
| `items` | [{v, in: a | b | both, at}] |
| `op` | {kind: union | intersection | a-b | b-a | symmetric, at, label} |
| `rings` | [{v, at, until}] |
| `strike` | [{v, at}] |
| `result` | {text, at}: a mono row under the circles, e.g. result = {10, 20} |
| `at` |  |
| `until` |  |
| `box` | default: main slot |

_Generated from runtime/templates; edit the template's meta there._
