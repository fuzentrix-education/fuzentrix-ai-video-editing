# Core Explainer

**Availability:** Always. **Used for:** titles, headers, agenda, definitions, concept and type cards, chips, flowcharts, cutaways, studio tags, summaries.

All colours, fonts and timings come from the brand kit (CSS variables `--fz-*`), so this family looks the same in every video and adapts to the brand.

## Look

- White cards (`--fz-card`) with a 1 px `--fz-line` border, brand radius and the brand shadow, on the editors' white plate.
- Swiss grid: 96 px left margin, header band at y 78–180, content in the `main` slot, small items in the `side` slot.
- Outfit 800 for titles (60/44 px), Inter 600 for body (30 px), JetBrains Mono uppercase labels (20 px, 0.2 em tracking).
- Emphasis: `*word*` in `--fz-emph` (title sizes only); `**word**` in `--fz-emph2` (any size). At most two per card.
- Icons: line icons from runtime/icons.svg in a tinted circle (`.fz-ic`); tones red/green/amber/purple only for meaning.

## Motion

- Enter: slide 24–40 px + fade, 0.55 s power3.out; lists stagger as each item is said.
- Exit: fade + small lift, 0.35 s power2.in.
- Chips pop (back.out); cards never bounce more than once.

Templates: see `global/templates/core/`.
