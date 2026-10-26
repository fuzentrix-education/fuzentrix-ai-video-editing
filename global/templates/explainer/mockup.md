# mockup

**Family:** explainer · **Layers:** plate

A browser window or phone with app screens that change as they are described: typing into fields, pressing buttons, a loading spinner, results. For 'open the portal, log in, click results…', an app.

| Parameter | Meaning |
|---|---|
| `kind` | browser | phone |
| `url` | browser address / phone app title |
| `screens` | [{at, elements: [{title} | {subtitle} | {field, value, at} | {button, press_at} | {row, value} | {spinner, at, until} | {stat, value} | {badge}]}] |
| `cursor` | [{x, y, at, click}] in frame coords |
| `at` |  |
| `until` |  |
| `box` | x, y, w, h (default main slot) |

_Generated from runtime/templates; edit the template's meta there._
