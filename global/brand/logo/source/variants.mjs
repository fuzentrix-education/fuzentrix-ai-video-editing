// Career Orbit logo variants from careerorbit_logo.svg (icon = raster colour map clipped to #co-icon; wordmark = 2 paths).
// Writes: horizontal lockup, on-dark (white CAREER, teal ORBIT, icon tone-lifted so its navy reads on dark) and all-white versions of logo, icon and horizontal.
import { createRequire } from "module"; import fs from "fs"; const require = createRequire(import.meta.url);
const puppeteer = require(process.env.PPTR);
const dir = process.argv[2];
const svg = fs.readFileSync(`${dir}/careerorbit_logo.svg`, "utf8");
const b = await puppeteer.launch({ executablePath: process.env.CHROME, headless: "shell" });
const p = await b.newPage(); await p.setContent(`<body>${svg}</body>`);
const out = await p.evaluate(() => {
  const NS = "http://www.w3.org/2000/svg";
  const root = document.querySelector("svg");
  const clip = root.querySelector("#co-icon path"), image = root.querySelector("#icon"), word = root.querySelector("#wordmark");
  const tmp = clip.cloneNode(true); root.appendChild(tmp); const ib = tmp.getBBox(); tmp.remove();
  const wb = word.getBBox();
  const TEAL = "#16BBC8", WHITE = "#FFFFFF";
  // build an svg from parts: icon (colour image or white fill), wordmark with given colours, optional transforms
  const make = (vb, { icon = "colour", words = ["#1C2F58", "#30809F"], tIcon = "", tWord = "", withWord = true, withIcon = true }, title) => {
    const s = document.createElementNS(NS, "svg");
    s.setAttribute("xmlns", NS); s.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
    s.setAttribute("viewBox", vb.map((v) => +v.toFixed(2)).join(" "));
    s.setAttribute("width", Math.round(vb[2] * 4)); s.setAttribute("height", Math.round(vb[3] * 4));
    const t = document.createElementNS(NS, "title"); t.textContent = title; s.appendChild(t);
    const defs = document.createElementNS(NS, "defs"); defs.appendChild(root.querySelector("#co-icon").cloneNode(true)); s.appendChild(defs);
    if (icon === "lifted") defs.insertAdjacentHTML("beforeend", '<filter id="lift" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncR type="gamma" exponent="0.55"/><feFuncG type="gamma" exponent="0.55"/><feFuncB type="gamma" exponent="0.55"/></feComponentTransfer></filter>');
    if (withIcon) {
      const g = document.createElementNS(NS, "g"); if (tIcon) g.setAttribute("transform", tIcon);
      if (icon === "colour" || icon === "lifted") { const im = image.cloneNode(true); if (icon === "lifted") im.setAttribute("filter", "url(#lift)"); g.appendChild(im); }
      else { const r = document.createElementNS(NS, "rect"); r.setAttribute("x", ib.x - 2); r.setAttribute("y", ib.y - 2); r.setAttribute("width", ib.width + 4); r.setAttribute("height", ib.height + 4); r.setAttribute("fill", icon); r.setAttribute("clip-path", "url(#co-icon)"); g.appendChild(r); }
      s.appendChild(g);
    }
    if (withWord) {
      const g = word.cloneNode(true); if (tWord) g.setAttribute("transform", tWord);
      [...g.querySelectorAll("path")].forEach((pa, i) => pa.setAttribute("fill", words[i]));
      s.appendChild(g);
    }
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(s);
  };
  const pad = 8;
  const x0 = Math.min(ib.x, wb.x), y0 = Math.min(ib.y, wb.y), x1 = Math.max(ib.x + ib.width, wb.x + wb.width), y1 = Math.max(ib.y + ib.height, wb.y + wb.height);
  const vbStack = [x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad];
  const vbIcon = [ib.x - pad, ib.y - pad, ib.width + 2 * pad, ib.height + 2 * pad];
  // horizontal: icon height = 2.2x the wordmark height, gap = 0.18 icon width, wordmark centred vertically
  const iconH = wb.height * 2.2, sc = iconH / ib.height, iconW = ib.width * sc, gap = iconW * 0.18;
  const W = iconW + gap + wb.width, H = iconH;
  const tIcon = `translate(${pad - ib.x * sc} ${pad - ib.y * sc}) scale(${sc})`;
  const tWord = `translate(${pad + iconW + gap - wb.x} ${pad + (H - wb.height) / 2 - wb.y})`;
  const vbH = [0, 0, W + 2 * pad, H + 2 * pad];
  const H_ = { tIcon, tWord };
  return {
    "careerorbit_logo_on-dark.svg": make(vbStack, { icon: "lifted", words: [WHITE, TEAL] }, "Career Orbit (on dark)"),
    "careerorbit_logo_white.svg": make(vbStack, { icon: WHITE, words: [WHITE, WHITE] }, "Career Orbit (white)"),
    "careerorbit_icon_on-dark.svg": make(vbIcon, { icon: "lifted", withWord: false }, "Career Orbit icon (on dark)"),
    "careerorbit_icon_white.svg": make(vbIcon, { icon: WHITE, withWord: false }, "Career Orbit icon (white)"),
    "careerorbit_logo_horizontal.svg": make(vbH, { ...H_ }, "Career Orbit (horizontal)"),
    "careerorbit_logo_horizontal_on-dark.svg": make(vbH, { ...H_, icon: "lifted", words: [WHITE, TEAL] }, "Career Orbit (horizontal, on dark)"),
    "careerorbit_logo_horizontal_white.svg": make(vbH, { ...H_, icon: WHITE, words: [WHITE, WHITE] }, "Career Orbit (horizontal, white)"),
  };
});
for (const [f, c] of Object.entries(out)) { fs.writeFileSync(`${dir}/${f}`, c); console.log(f, c.length); }
await b.close();
