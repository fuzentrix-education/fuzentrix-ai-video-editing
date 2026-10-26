// export.mjs <dir> : transparent PNGs of each SVG at the listed widths
import { createRequire } from "module"; import fs from "fs"; const require = createRequire(import.meta.url);
const puppeteer = require(process.env.PPTR);
const dir = process.argv[2];
const JOBS = {
  "fuzentrix_logo.svg": [1000, 2000, 4000], "fuzentrix_logo_on-dark.svg": [2000],
  "fuzentrix_icon.svg": [1024], "fuzentrix_icon_on-dark.svg": [1024],
  "fuzentrix_logo_horizontal.svg": [1000, 2000], "fuzentrix_logo_horizontal_on-dark.svg": [2000],
};
const b = await puppeteer.launch({ executablePath: process.env.CHROME, headless: "shell", args: ["--allow-file-access-from-files"] });
for (const [f, widths] of Object.entries(JOBS)) {
  const vb = fs.readFileSync(`${dir}/${f}`, "utf8").match(/viewBox="([^"]+)"/)[1].split(" ").map(Number);
  for (const w of widths) {
    const h = Math.round(w * vb[3] / vb[2]);
    const p = await b.newPage(); await p.setViewport({ width: w, height: h });
    fs.writeFileSync(`${dir}/_tmp.html`, `<body style="margin:0;background:transparent"><img src="${f}" style="display:block;width:${w}px;height:${h}px"></body>`);
    await p.goto(`file://${dir}/_tmp.html`, { waitUntil: "load" });
    const out = `${dir}/${f.replace(".svg", "")}_${w}w.png`;
    await p.screenshot({ path: out, omitBackground: true }); await p.close();
    console.log(out.split("/").pop(), w, "x", h);
  }
}
fs.unlinkSync(`${dir}/_tmp.html`); await b.close();
