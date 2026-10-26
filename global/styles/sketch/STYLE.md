# Sketch / Whiteboard

**Availability:** Only when the prompt asks ("sketch edit"). **Used for:** analogies and stories, or a whole video in sketch style; code stays in Code & Execution.

All colours, fonts and timings come from the brand kit (CSS variables `--fz-*`), so this family looks the same in every video and adapts to the brand.

## Look

- Whiteboard marker: a clean white board, navy `--fz-text` and teal (`--fz-accent`, `--fz-emph`) strokes; red and green for wrong and right.
- Labels in Caveat 700; body text stays in the house fonts for readability.
- People and objects from one line-art set (see global/props, style: line).

## Motion

- Strokes draw themselves on at the brand's draw speed with a slight fixed-seed wobble and pressure taper.
- Fills appear after their outline, never before.

Templates: see `global/templates/sketch/`.
