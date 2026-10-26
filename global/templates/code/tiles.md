# tiles

**Family:** code · **Layers:** plate

A row or grid of value tiles that change state (now / ok / bad / skip / dim), e.g. loop values or rounds.

| Parameter | Meaning |
|---|---|
| `id` |  |
| `values` | [...] |
| `label` | optional label above (markdown) |
| `at` |  |
| `until` |  |
| `box` | x, y (default main slot) |
| `size` | tile px (default 100) |
| `gap` | px (default size+16) |
| `cols` | wrap after n tiles |
| `states` | [{i: index | value: v, state, at}] |
| `note` | {text, at, until} small text under the tiles |

_Generated from runtime/templates; edit the template's meta there._
