import { createRequire } from "module"; const require = createRequire(import.meta.url);
const puppeteer = require(process.env.PPTR);
const [,, url, out] = process.argv;
const b = await puppeteer.launch({ executablePath: process.env.CHROME, headless: "shell", args: ["--allow-file-access-from-files"] });
const p = await b.newPage(); await p.setViewport({ width: 1920, height: 1000 });
await p.goto(url, { waitUntil: "load" }); await p.evaluate(() => document.fonts.ready); await new Promise(r => setTimeout(r, 400));
await p.screenshot({ path: out, fullPage: true }); await b.close();
