# The brand kit

Every Fuzentrix video uses **one** brand kit: Career Orbit, the Fuzentrix LMS. There are no per-brand kits and nothing to choose per
video. The video workflow loads it at build time, so a change here reaches every future render.

```
brand/
  brand.yaml          the kit: logo, colours, backdrop, fonts, type, shapes, code colours, motion, audio, layout
  brand_sheet.png     everything on one page (`fzv brands --sheet` renders it from brand.yaml)
  sheet.html          the sheet's page
  logo/               Career Orbit logo set (SVG and PNG; colour, on-dark, white) and its source files
  fonts/              Bricolage Grotesque, Manrope, JetBrains Mono, Caveat (SIL Open Font Licence, woff2)
  plates/             the editors' slide backgrounds, used only to recognise and key rough cuts made on them
  archive/            retired material, not loaded: the old Fuzentrix Education logo set, the first Career Orbit sheet
```

## Where the values come from

The **Career Orbit LMS design** (its default theme): navy and one blue, Manrope for text and Bricolage Grotesque for headings, white
cards with 22 px corners and soft navy shadows. The videos look like the product the students are using.

## The colour budget

Every frame stays calm. A video uses only:

| Group | Colours | Use |
|---|---|---|
| Neutrals | navy `#102A56`, slate `#3B5079`, mist `#8A9BBA`, line `#DCE7FA`, dim `#F1F4F9`, page `#F4F7FC`, white | Text, cards, borders, the backdrop |
| Brand | blue `#2563EB` (text-safe `#1D4ED8`), blue soft `#E3EDFF`, sky `#78B7FF` on dark | The only decorative colour: emphasis, icons, progress, active states |
| Meaning | green `#15803D`, red `#C42020`, amber `#F59E0B` (each with a soft fill) | Only when the moment means it: correct / True / output, error / False / stop, look here |
| Code | the LMS code editor's theme: editor `#0D1A3A`, text `#E1EBFF`, keywords `#A5B6FF`, strings `#7EE0B5`, numbers `#F7B267`, calls `#5CC8FF`, types `#FFD580`, comments `#7483AD` | The dark editor and terminal, so videos match what students type in |

**Don't:** a colour per topic, teal outside the logo artwork, violet / pink / orange / rose, coloured window dots, or changing the backdrop.

**How emphasis looks:** highlighted words turn blue and a blue underline draws under them as they are said (no highlighter-pen marks).
Pointer lines from a note to what it explains are thin blue lines with rounded corners, routed around every other graphic.
Templates read every colour from the kit (`--fz-*` variables); none hard-codes one.

## The backdrop

A pale page (`#F4F7FC`) with a navy dot grid (34 px) and two very soft blue light pools. It is rendered from `backdrop:` in brand.yaml
at build time and stays for the whole video (rule L11). The pools don't drift, so clips join seamlessly.

## Logo

| File | Use |
|---|---|
| `logo/careerorbit_logo.svg` | **Master.** The orbit icon above the CAREERORBIT wordmark. |
| `logo/careerorbit_logo_horizontal.svg` | Icon beside the wordmark: the corner logo the team adds to finished videos (top right, no box), navbars. Not burned in by the workflow unless the prompt says `Logo: on`. |
| `logo/careerorbit_icon.svg` | The icon alone: avatars, favicons, small marks. |
| `*_on-dark.svg` | Navy or dark backgrounds: white CAREER, teal ORBIT, the icon's dark tones lifted. |
| `*_white.svg` | Single-colour white: photos, busy or coloured backgrounds. |
| `*_1000w.png` … `*_4000w.png` | Transparent PNGs for video, PowerPoint and Canva. |

Leave clear space of at least the height of the "C" in CAREER. Minimum width: 160 px stacked, 200 px horizontal, 32 px icon.
Don't recolour, stretch, rotate or outline the logo.

## Fonts

| Role | Font | Use |
|---|---|---|
| Display | Bricolage Grotesque 600–800 | Titles, headings, big numbers |
| Body | Manrope 500–800 | Body text, chips, labels |
| Mono | JetBrains Mono 400–700 | Code, values, terminals (ligatures off) |
| Hand | Caveat | Sketch style only |

Registry animations that ask for Inter or Outfit by name get Manrope and Bricolage Grotesque (`fonts.aliases`).

## Changing the kit

Edit `brand.yaml`, run `bin/fzv brands --sheet` and look at `brand_sheet.png`, then rebuild a video to see it in place.
