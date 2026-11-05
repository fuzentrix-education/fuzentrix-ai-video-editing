# calendar

**Family:** explainer · **Layers:** plate

A month calendar (Rani's 'Imagine a calendar'): the card comes in, the dates fill in row by row, one date turns solid blue; optional rows beside it (DAY / MONTH / YEAR) pop in on her words, their values come in as she says them, and an amber outline follows her. For dates, schedules, 'imagine a calendar'.

| Parameter | Meaning |
|---|---|
| `month` | e.g. August |
| `year` | e.g. 2026 |
| `fill_at` | when the dates fill in (default at + 0.4) |
| `select` | {day, at}: that date turns solid blue |
| `fields` | [{label, value, at, label_at}] rows beside the calendar (label colours: blue, green, amber) |
| `focus` | [{field: 1-based, at}] the amber outline on a row |
| `stamp` | {text, at, tone: ok|bad|accent|warn} |
| `at` |  |
| `until` |  |
| `box` | x, y, w (calendar width, default 520) |

_Generated from runtime/templates; edit the template's meta there._
