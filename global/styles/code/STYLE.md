# Code & Execution

**Availability:** Always, for any code. **Used for:** code typed to dictation, line highlights, notes with wires, loop traces, tiles, variables, terminal, screen-recording window.

All colours, fonts and timings come from the brand kit (CSS variables `--fz-*`), so this family looks the same in every video and adapts to the brand.

## Look

- Dark editor cards: `--fz-code-bg1 → --fz-code-bg2`, macOS dots, a tab, a Run button in `--fz-action`.
- JetBrains Mono 700, ligatures off, 34–46 px; syntax colours from the house kit (keyword, function, number, string, comment).
- Highlights: rounded boxes in `--fz-highlight` (green for 'runs', red for 'stops/breaks').
- Explanations are `note` cards **outside** the code, joined by a highlight-coloured wire with dots at both ends.
- Recordings: the whole content area in a branded window, never cropped or zoomed; the step tracker sits in the title bar.
- Terminals print the program's **real** output through `exec` (the build runs the code): typed input in the warning colour where it is read, errors in red, scrolling like a real terminal.
- `Recording: reference`: the recording is never shown; its code and output are rebuilt with code cards and `exec` terminals, timed to its keyframes.

## Motion

- Typing follows the instructor's dictation (`parts`) or a steady 15–18 cps; the caret blinks only while typing.
- Highlight boxes pop in (back.out) when the instructor reads that token.
- Trace values roll in from below; True/False chips swap per iteration.
- Output lines follow the recording: a real program prints everything at once (`exec.pace` 0.05), or line by line as the instructor reads them (`exec.times`).

Templates: see `global/templates/code/`.
