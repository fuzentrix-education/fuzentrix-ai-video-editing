# Fuzentrix Education brand kit

The brand kit for Fuzentrix Education videos, slides and web graphics. Typography, shapes, motion and sound come from the shared house style in `../_shared/house.yaml`, the same as Career Orbit. This kit adds the logo, the colours and a few labels. `brand.yaml` holds the same values in machine-readable form, and `fuzentrix_brand_sheet.png` shows everything on one page.

## Logo files

All versions come from the original vector logo, `source/MAIN LOGO (original).svg`, copied from `fuzentrix_landing_site/public`. Nothing was redrawn: the files only re-crop, re-arrange or recolour the original shapes.

| File | Use |
|---|---|
| `fuzentrix_logo.svg` | **Master.** Icon above the FUZENTRIX / EDUCATION wordmark, tightly cropped. |
| `fuzentrix_logo_horizontal.svg` | Icon beside the wordmark. Use it for the corner logo in videos and other wide, short spaces. |
| `fuzentrix_icon.svg` | The book, figure and cap without the wordmark. Use it for avatars, favicons and small marks. |
| `*_on-dark.svg` | All-white versions of the three files above, for navy or dark backgrounds. |
| `*_1000w.png`, `*_2000w.png`, `*_4000w.png`, `*_1024w.png` | Transparent PNGs. Use these in video, PowerPoint and Canva. |

**The horizontal lockup is new.** It was arranged from the original parts: the icon is 1.6× the height of the wordmark block, the gap is a quarter of the icon's width, and the wordmark is centred vertically. If a designer supplies an official horizontal version, use theirs.

**Using the logo**
- **Clear space:** leave at least the height of the "F" in FUZENTRIX on every side.
- **Minimum width:** 160 px for the stacked logo, 200 px for the horizontal one, 32 px for the icon.
- **Backgrounds:** on white or light backgrounds, use the full-colour logo. On navy or any dark background, use the on-dark version; the gradient logo disappears on navy.
- **Don't** recolour it except to the white version, stretch it, rotate it, add effects or outlines, or place the gradient version on a mid or dark blue.
- **In videos:** the horizontal logo sits top right, 40 px high, in a white pill. That's the same position as the Career Orbit corner logo.

## Colours

The navy and blue come from the logo's gradient. The accents and neutrals come from the Fuzentrix website (`fuzentrix_landing_site/app/globals.css`), so videos and the website match.

| Role | Hex | Source | Use |
|---|---|---|---|
| ink | `#0D274C` | logo gradient (bottom), website primary | headings and body text |
| brand-blue | `#3381C2` | logo gradient (top) | accent and title emphasis. Large text only: 4.1:1 on white |
| brand-mid | `#205487` | midpoint of the logo gradient | emphasis in small text: 7.8:1 on white |
| coral | `#CF501B` | website accent | calls to action, sparing emphasis |
| orange | `#D9731D` | website focus ring | code highlight boxes and pointer lines in videos (not for text) |
| cyan | `#38BDF8` | website accent | accents on dark backgrounds, such as code cards |
| slate | `#5C6B80` | website muted text | secondary text |
| surface | `#F3F6FA` | website muted background | page base |
| tint | `#ECF6FB` | website accent background | pills, icon backgrounds |
| line | `#E1E7EF` | website border | card borders |
| charcoal | `#1A1A1A` | "EDUCATION" in the logo | logo only |

- **Gradient:** `#0D274C` → `#3381C2`, bottom to top as in the logo. Use it for hero titles, wipes and progress bars.
- **Shared colours:** success `#12A150`, danger `#E5484D`, warning `#F6AD55` and the code-syntax colours are the same in every brand (see `../_shared/house.yaml`).

**Older values:** earlier Fuzentrix slides used navy `#062858` and blue `#0A59C8` with the Aptos font. This kit replaces them with the logo and website values above.

## Type

These are shared with Career Orbit; the files are in `../_shared/fonts`, all under the SIL Open Font Licence.
- **Outfit:** titles and headings.
- **Inter:** body text, chips and labels. 26 px is the smallest size on screen.
- **JetBrains Mono:** code and labels, with ligatures off so that `==` shows as two characters.

The website itself uses Geist for its interface; videos use the house fonts above.

## Rebuilding the files

`source/variants.mjs` builds the six SVGs from the original, and `source/export.mjs` exports the PNGs. Both run with headless Chrome via puppeteer-core. `../_shared/brand-sheet.html?brand=fuzentrix`, rendered by `../_shared/render-sheet.mjs`, makes the brand sheet.
