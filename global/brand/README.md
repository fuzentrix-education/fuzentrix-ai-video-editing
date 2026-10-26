# Fuzentrix brand kits

These are the global brand files that every Fuzentrix video, slide deck and graphic reads from. The video workflow in this repo (`docs/SYSTEM_DESIGN.md`) loads them at render time. Change them here and every future render follows.

```
brand/
  _shared/                 house style used by every brand
    house.yaml             fonts, type scale, shapes, shared colours, code colours, motion, audio, layout
    fonts/                 Outfit, Inter, JetBrains Mono, Montserrat (SIL Open Font Licence, woff2)
    plate/                 slide_background.png: the white plate with blue arcs that editors use
    brand-sheet.html       one-page brand sheet (?brand=<id>), rendered by render-sheet.mjs
  career-orbit/            Career Orbit (the Fuzentrix LMS): the main brand. Logo set, brand.yaml, brand sheet
  fuzentrix/               Fuzentrix Education (parent brand): logo set from the original vector, brand.yaml, brand sheet
```

**How the kits fit together**
- Each `brand.yaml` **extends** `_shared/house.yaml` and adds only its logo files, colour roles, corner-logo setup and name-card label.
- Typography, shapes, motion and sound are identical across brands, so a Fuzentrix video and a Career Orbit video feel like one family. Only the logo and colours change.
- **Pick the brand per video:** Career Orbit by default; a video's prompt can choose `fuzentrix`.
- **To add a brand:** create a new folder with a logo set, a `brand.yaml` that extends `../_shared/house.yaml`, and a README. Then add its colours to `brand-sheet.html` and render the sheet.

| Brand | Folder | Status |
|---|---|---|
| Career Orbit (LMS, main brand) | `career-orbit/` | Complete: stacked, horizontal and icon logos in colour, on-dark and white. Colours merge the LMS app's navy ramp with the logo's teal. The logo was rebuilt from footage (no original exists). |
| Fuzentrix Education (parent) | `fuzentrix/` | Complete: stacked, horizontal and icon logos, each in colour and on-dark, as SVG and PNG. |
