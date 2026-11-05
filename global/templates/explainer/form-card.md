# form-card

**Family:** explainer · **Layers:** plate

A record / form / receipt card whose field values type in as they are said. For 'your name, age, branch…', a student record, a filled form.

| Parameter | Meaning |
|---|---|
| `title` |  |
| `icon` |  |
| `fields` | [{label, value, at, label_at}]: label_at = when she names the field (the row pops in then; default with the card), at = when the value types in |
| `stamp` | {text, at, tone: ok|bad|accent} |
| `focus` | [{field: 1-based number or label, at}]: the field she is talking about gets the amber outline; it moves with her (rule S3) |
| `at` |  |
| `until` |  |
| `box` | x, y, w (default side slot) |

_Generated from runtime/templates; edit the template's meta there._
