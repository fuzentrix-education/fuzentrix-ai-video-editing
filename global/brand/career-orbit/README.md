# Career Orbit brand kit

Career Orbit is the Fuzentrix LMS. This kit is the main brand for course videos, and it's the recommended brand for the LMS app itself. Typography, shapes, motion and sound come from the shared house style in `../_shared/house.yaml`. This kit adds the logo set, the colours and a few labels.
- **`brand.yaml`** holds every value in machine-readable form.
- **`career-orbit_brand_sheet.png`** shows everything on one page.

## Logo files

| File | Use |
|---|---|
| `careerorbit_logo.svg` | **Master.** The orbit icon above the CAREERORBIT wordmark. Scales to any size. |
| `careerorbit_logo_horizontal.svg` | Icon beside the wordmark. Use it for the corner logo in videos, LMS navbars and other wide, short spaces. |
| `careerorbit_icon.svg` | The orbit icon alone, for avatars, favicons and small marks. |
| `*_on-dark.svg` | For navy or dark backgrounds: CAREER in white, ORBIT in teal, and the icon with its dark tones lifted so the navy part of the ring stays visible. |
| `*_white.svg` | All white, single colour. For photos and busy or coloured backgrounds. |
| `*_1000w.png`, `*_2000w.png`, `*_4000w.png`, `*_1024w.png` | Transparent PNGs. Use them in video, PowerPoint and Canva, which may not show the SVG icon colours. |
| `source/careerorbit_cutout_584w.png` | The cut-out from the footage that the rebuild was traced from. |

**Using the logo**
- **Clear space:** leave at least the height of the "C" in CAREER on every side.
- **Minimum width:** 160 px for the stacked logo, 200 px for the horizontal one, 32 px for the icon.
- **Backgrounds:**
  - White or light: the full-colour logo. The navy CAREER disappears on dark backgrounds.
  - Navy or dark (for example the LMS sidebar or a dark video panel): the on-dark version.
  - Photos and single-colour use: the white version.
- **Don't** recolour the logo except to the supplied versions, stretch it, rotate it, add effects or outlines, or place the full-colour logo on mid or dark blue.
- **In videos:** the horizontal logo sits top right, 40 px high, in a white pill.

## Colours

Two sources are merged, so the logo, the LMS app and the videos look like one product:
- **Navy ramp, for text, surfaces and buttons:** taken from the LMS app's `fuzentrix_ui/src/styles/theme.css`.
- **Teal, as the accent:** taken from the logo.

| Role | Hex | Source | Use |
|---|---|---|---|
| navy | `#0D274C` | LMS brand-900 | headings and body text |
| action | `#1B53A2` | LMS brand-600 | buttons, links, emphasis in small text (7.4:1 on white) |
| action-hover | `#174484` | LMS brand-700 | hover and pressed states |
| teal | `#16BBC8` | logo, orbit top and dot | **the accent:** icons, progress, active states, highlights on dark (6.4:1 on navy). **Never text on white** (2.3:1). |
| orbit-text | `#30809F` | logo, "ORBIT" | title emphasis at heading sizes (4.4:1 on white) |
| slate | `#52657D` | house | secondary text |
| line | `#DDE9F6` | LMS brand-100 | card borders, dividers |
| tint | `#EFF5FB` | LMS brand-50 | pills, icon backgrounds, page base |
| surface | `#FFFFFF` | LMS | cards |
| surface-warm | `#FBFAF7` | LMS | navbar and app shell |
| deep | `#07152B` / `#081830` | LMS brand-deep / brand-950 | dark panels |

**The rest of the LMS ramp:** `#2D6CBD` (500), `#5B91D1` (400), `#8FB4E0` (300), `#C3D7EE` (200).

**Gradients**
- **Orbit** `#164673 → #145695 → #1790B4 → #16BBC8`, the logo's ring: hero titles, brand moments and progress.
- **Deep** `#0D274C → #081830`, the LMS sidebar and sign-in panel: dark panels and cutaway backgrounds.

**Shared colours:** success `#12A150`, danger `#E5484D`, warning/highlight amber `#F6AD55` and the code-syntax colours are the same in every brand (see `../_shared/house.yaml`).

**Inside the logo artwork only:** the wordmark keeps its own navy `#1C2F58` for CAREER. Everywhere else, text uses the LMS navy `#0D274C`.

## Type

Videos use the house fonts, chosen for how they look on screen. Files are in `../_shared/fonts`, all under the SIL Open Font Licence.
- **Outfit:** titles and headings.
- **Inter:** body text, chips and labels. 26 px is the smallest size on screen.
- **JetBrains Mono:** code and labels, with ligatures off so that `==` shows as two characters.

The LMS app's interface keeps its own fonts (Avenir and Source Sans 3); the kit doesn't depend on them.

## For the LMS app

The app's colours already match this kit. It currently shows the Fuzentrix Education logo (`public/main-logo.svg`). To brand it as Career Orbit, use:
- `careerorbit_logo_horizontal_on-dark.svg` in the dark sidebar and sign-in panel
- `careerorbit_logo_horizontal.svg` on the light navbar
- `careerorbit_icon.svg` for the favicon

## How the logo was rebuilt

No original design file exists. The logo was reconstructed on 2026-10-21 from the intro animation of the Loop Control rough cut. If the designer's original turns up, use that instead and regenerate the versions.
- **Icon outline:** traced from the cut-out and smoothed. The ring is an oval band and the dot is a circle.
- **Icon colour:** a smooth colour map taken from the original, cropped to the outline. It looks like a gradient but isn't an editable one, so changing the colours in Illustrator or Figma means replacing the fill.
- **Icon colours:** teal `#16BBC8` at the top, blue `#145695` at the bottom left, navy `#164673` at the bottom right.
- **Wordmark:** Montserrat, converted to outlines. CAREER is weight 750 in `#1C2F58`; ORBIT is weight 475 in `#30809F`.
- **Derived versions (2026-10-24):** made by `source/variants.mjs`; PNGs exported by `source/export.mjs`.
  - **Horizontal:** the icon is 2.2× the wordmark height, with a gap of 0.18× the icon width.
  - **On-dark:** white CAREER and teal ORBIT, with a gamma lift of 0.55 on the icon.
  - **White:** the icon filled white through its outline.

  If a designer supplies official versions, use theirs.
