# char-scan

**Family:** code · **Layers:** plate

A string split into character cells; a pointer walks along and stamps ✓ or ✗ for a test (Python's isalpha, isdigit, isalnum, isupper, islower, isspace); the result pops as True / False.

| Parameter | Meaning |
|---|---|
| `text` | the string |
| `test` | alpha | digit | alnum | upper | lower | space |
| `marks` | optional marks per character instead of a test: ✓ ✗ – |
| `label` | caption above, e.g. `"Hi5".isalpha()` |
| `at` |  |
| `until` |  |
| `step` | s per character (default 0.4) |
| `times` | [time per character] (overrides step) |
| `stop_on_fail` | stop at the first ✗, as Python does (default false: check every character) |
| `result` | {at}: the True / False pill |
| `indexes` | show indexes under the cells (default false) |
| `box` | x, y (default main slot) |
| `size` | cell px (default 84) |

_Generated from runtime/templates; edit the template's meta there._
