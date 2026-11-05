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
| `size` | tile px (default 150) |
| `gap` | px (default size+24) |
| `cols` | wrap after n tiles |
| `appear` | [t per tile]: each tile enters on the word that names it (rule S2; default: all at `at`) |
| `states` | [{i: index | value: v, state, at}]: now | ok | bad | skip | dim | on (back to plain) | focus (amber outline; the focus moves: the last focused tile goes back), e.g. a focus each time she names a value (rule S3) | pick (solid blue: the one chosen, e.g. the index asked for) |
| `note` | {text, at, until} small text under the tiles |

_Generated from runtime/templates; edit the template's meta there._
