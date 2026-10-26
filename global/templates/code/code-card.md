# code-card

**Family:** code · **Layers:** plate

Dark editor card. Lines type in spoken chunks or at a steady speed; highlights, active-line bar, Run press. Registers `id` so notes can point at its lines.

| Parameter | Meaning |
|---|---|
| `id` | name for notes and traces |
| `lines` | [code lines] |
| `title` | tab title (default main.py) |
| `lang` | python | c | cpp | java | javascript (default: from the title's extension) |
| `recorded` | reference mode: the lines exactly as typed in the recording, when `lines` corrects them (rule E9) |
| `logic_fix` | why a correction changes the output (goes to 'to confirm') |
| `at` |  |
| `until` |  |
| `box` | default: main slot (left) |
| `fs` | font px (default 38) |
| `type` | [{line, at, cps} | {line, parts: [[lastCharIndex, at], ...]}] |
| `reveal` | [{lines: [n...], at}] show whole lines |
| `highlights` | [{line, cols: [c0, c1], at, until, tone: ''|green|red}] |
| `active` | [{line, at}] |
| `active_off` | time |
| `caret_off` | time |
| `run` | time the Run button is pressed |
| `focus` | [{keep: [lines], at, until}] dim the other lines |

_Generated from runtime/templates; edit the template's meta there._
