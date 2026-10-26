# Technical Diagram

**Availability:** Content-driven. **Used for:** architecture, client-server, database tables and ER links, memory and stack models, request flow.

All colours, fonts and timings come from the brand kit (CSS variables `--fz-*`), so this family looks the same in every video and adapts to the brand.

## Look

- A light blueprint grid (40 px, `--fz-line`, 55% opacity) on white; never a dark blueprint (the plate is white).
- Blocks are white cards with an icon and a short label; arrows in `--fz-accent` with arrowheads; labels in mono.
- Tables: tinted header row, mono uppercase column names, key columns in `--fz-emph`.

## Motion

- Blocks pop in as named; arrows draw on (0.5 s) when the relationship is said.
- Rows enter one by one; highlights tint cells.

Templates: see `global/templates/diagram/`.
