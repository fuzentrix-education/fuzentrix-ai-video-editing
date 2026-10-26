# type-convert

**Family:** explainer · **Layers:** plate

A value changes type: a quoted value with its type badge goes through the conversion function and comes out converted. For input() -> int(), str(), float().

| Parameter | Meaning |
|---|---|
| `value` | the value, e.g. 20 |
| `from_type` | default str |
| `to_type` | default int |
| `fn` | default int() |
| `label` | caption above (markdown) |
| `at` | input value appears |
| `convert_at` | it goes through the function |
| `then` | {text, at} a follow-up line, e.g. '20 + 1 = 21' (optional) |
| `until` |  |
| `box` | x, y, w (default side slot) |

_Generated from runtime/templates; edit the template's meta there._
