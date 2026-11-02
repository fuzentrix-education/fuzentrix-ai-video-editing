// Build the Fuzentrix logo variants from the original vector (no redrawing): stacked, icon, horizontal lockup, + white on-dark versions.
import { createRequire } from "module"; import fs from "fs"; const require = createRequire(import.meta.url);
const puppeteer = require(process.env.PPTR);
const [,, src, outDir] = process.argv;
const svg = fs.readFileSync(src, "utf8");
const b = await puppeteer.launch({ executablePath: process.env.CHROME, headless: "shell" });
const p = await b.newPage(); await p.setContent(`<body>${svg}</body>`);
const files = await p.evaluate(() => {
  const NS = "http://www.w3.org/2000/svg";
  const root = document.querySelector("svg");
  const shapes = [...root.querySelectorAll("path, polygon")];
  const WORD = shapes.slice(0, 12), ICON = shapes.slice(12);          // 0 = FUZENTRIX, 1-11 = EDUCATION + rules, 12-29 = icon
  const defs = root.querySelector("defs").cloneNode(true);
  const bbox = (els) => { let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; els.forEach((e) => { const r = e.getBBox(); x0 = Math.min(x0, r.x); y0 = Math.min(y0, r.y); x1 = Math.max(x1, r.x + r.width); y1 = Math.max(y1, r.y + r.height); }); return { x0, y0, x1, y1, w: x1 - x0, h: y1 - y0 }; };
  const make = (vb, parts, title) => {
    const s = document.createElementNS(NS, "svg");
    s.setAttribute("xmlns", NS); s.setAttribute("viewBox", vb.map((v) => +v.toFixed(2)).join(" "));
    s.setAttribute("width", Math.round(vb[2] * 2)); s.setAttribute("height", Math.round(vb[3] * 2));
    const t = document.createElementNS(NS, "title"); t.textContent = title; s.appendChild(t);
    s.appendChild(defs.cloneNode(true));
    parts.forEach(([els, tf]) => { const g = document.createElementNS(NS, "g"); if (tf) g.setAttribute("transform", tf); els.forEach((e) => g.appendChild(e.cloneNode(true))); s.appendChild(g); });
    return s;
  };
  const white = (s) => {   // monochrome white for dark backgrounds
    const c = s.cloneNode(true);
    c.querySelectorAll("stop").forEach((st) => st.setAttribute("stop-color", "#FFFFFF"));
    c.querySelectorAll("style").forEach((st) => st.textContent = st.textContent.replace(/fill:\s*#[0-9a-fA-F]{3,6}/g, "fill: #FFFFFF"));
    c.querySelectorAll("path, polygon").forEach((e) => { const f = e.getAttribute("fill"); if (f && !f.startsWith("url")) e.setAttribute("fill", "#FFFFFF"); });
    c.querySelector("title").textContent += " (on dark)";
    return c;
  };
  const pad = 24;
  const all = bbox(shapes), ic = bbox(ICON), wd = bbox(WORD);
  const stacked = make([all.x0 - pad, all.y0 - pad, all.w + 2 * pad, all.h + 2 * pad], [[WORD], [ICON]], "Fuzentrix Education");
  const icon = make([ic.x0 - pad, ic.y0 - pad, ic.w + 2 * pad, ic.h + 2 * pad], [[ICON]], "Fuzentrix Education icon");
  // horizontal lockup: icon at 1.6x the wordmark block height, 0.25 icon-width gap, wordmark centred vertically
  const iconH = wd.h * 1.6, s = iconH / ic.h, iconW = ic.w * s, gap = iconW * 0.25;
  const W = iconW + gap + wd.w, H = iconH;
  const tIcon = `translate(${pad - ic.x0 * s} ${pad - ic.y0 * s}) scale(${s})`;
  const tWord = `translate(${pad + iconW + gap - wd.x0} ${pad + (H - wd.h) / 2 - wd.y0})`;
  const horiz = make([0, 0, W + 2 * pad, H + 2 * pad], [[ICON, tIcon], [WORD, tWord]], "Fuzentrix Education (horizontal)");
  const ser = (n) => '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(n);
  return {
    "fuzentrix_logo.svg": ser(stacked), "fuzentrix_logo_on-dark.svg": ser(white(stacked)),
    "fuzentrix_icon.svg": ser(icon), "fuzentrix_icon_on-dark.svg": ser(white(icon)),
    "fuzentrix_logo_horizontal.svg": ser(horiz), "fuzentrix_logo_horizontal_on-dark.svg": ser(white(horiz)),
  };
});
for (const [f, c] of Object.entries(files)) { fs.writeFileSync(`${outDir}/${f}`, c); console.log(f, c.length); }
await b.close();
