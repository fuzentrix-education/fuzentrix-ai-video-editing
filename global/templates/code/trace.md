# trace

**Family:** code · **Layers:** plate

Loop trace panel: the variable box, the condition check with its True/False result, per iteration. Optionally drives a code card's highlights, a tiles row and a terminal.

| Parameter | Meaning |
|---|---|
| `var` | variable name (default i) |
| `cond` | condition text after the value, e.g. '== 6' |
| `at` |  |
| `until` |  |
| `box` | default: side slot |
| `iterations` | [{v, val: time value appears, chk: time check starts, res: time result shows, result: true|false, pr: time print runs, out: time output appears, out_text}] |
| `code` | code-card id (optional) |
| `check_line` | line of the if |
| `print_line` | line of the print |
| `hit_line` | line that runs when true (e.g. break) |
| `tiles` | tiles id (optional) |
| `term` | terminal id (optional; prints out_text) |

_Generated from runtime/templates; edit the template's meta there._
