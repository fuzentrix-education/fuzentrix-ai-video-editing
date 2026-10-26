# terminal

**Family:** code · **Layers:** plate

Output panel. With `exec` it runs the code card's program and prints its exact output (input echoed where it is read, errors in red), scrolling like a real terminal. Registers `id` for notes.

| Parameter | Meaning |
|---|---|
| `id` |  |
| `title` | default Output |
| `at` |  |
| `until` |  |
| `box` | default: bottom-left |
| `exec` | {code: code-card id, stdin: [lines typed into the program], at, pace, times: [t per line], after_input, tone, tones: {line index: tone}, expect_error} runs the code at build time and prints its real output (rule E7) |
| `input` | {text, at} shown as 'input > text' (manual mode) |
| `lines` | [{text, input, at, tone: ok|warn|bad|dim}] (filled by exec; by hand needs `manual`) |
| `chips` | [{text, at}] instead of lines (needs `manual`) |
| `manual` | reason the output is written by hand (rule E7) |
| `lh` | line height (default 44) |

_Generated from runtime/templates; edit the template's meta there._
