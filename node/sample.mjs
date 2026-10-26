// fzv headless-Chrome helper.
//   node node/sample.mjs catalogue <repo>/runtime            -> JSON: every template's meta
//   node node/sample.mjs sample <clip.html> <t1,t2,...>      -> JSON: visible fz elements per local time, sfx cues, script errors
//   node node/sample.mjs still <page.html> <out.png> [w h]   -> PNG screenshot (brand sheets, docs)
import { createRequire } from "module";
import fs from "fs";
import os from "os";
import path from "path";
const require = createRequire(import.meta.url);
const puppeteer = require("puppeteer-core");

function chrome() {
  if (process.env.FZV_CHROME && fs.existsSync(process.env.FZV_CHROME)) return process.env.FZV_CHROME;
  const home = os.homedir(), found = [];
  const walk = (dir, name, depth = 0) => {
    if (depth > 4 || !fs.existsSync(dir)) return;
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) walk(p, name, depth + 1);
      else if (e.name === name) found.push(p);
    }
  };
  walk(path.join(home, ".cache/puppeteer/chrome-headless-shell"), "chrome-headless-shell");
  walk(path.join(home, ".cache/hyperframes/chrome"), "chrome-headless-shell");
  walk(path.join(home, ".cache/puppeteer/chrome"), "Google Chrome for Testing");
  for (const p of ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "C:/Program Files/Google/Chrome/Application/chrome.exe"]) if (fs.existsSync(p)) found.push(p);
  if (!found.length) throw new Error("no Chrome found: set FZV_CHROME, or run `npx hyperframes render` once to download one");
  return found[0];
}

async function browser() {
  return puppeteer.launch({ executablePath: chrome(), headless: "shell", args: ["--allow-file-access-from-files", "--autoplay-policy=no-user-gesture-required"] });
}

const [, , cmd, a1, a2, a3, a4] = process.argv;

if (cmd === "catalogue") {
  const b = await browser(); const p = await b.newPage();
  const files = ["vendor/gsap.min.js", "lib.js", ...fs.readdirSync(path.join(a1, "templates")).filter((f) => f.endsWith(".js")).map((f) => "templates/" + f)];
  await p.setContent("<div id='root'></div>");
  for (const f of files) await p.addScriptTag({ content: fs.readFileSync(path.join(a1, f), "utf8") });
  console.log(JSON.stringify(await p.evaluate(() => window.FZ.meta)));
  await b.close();
} else if (cmd === "sample") {
  const times = a2.split(",").map(Number);
  const b = await browser(); const p = await b.newPage();
  await p.setViewport({ width: 1920, height: 1080 });
  await p.goto("file://" + path.resolve(a1), { waitUntil: "load" });
  await p.evaluate(() => document.fonts.ready);
  const res = await p.evaluate((times) => {
    const tl = window.__timelines && window.__timelines.main;
    const vis = (el) => { let o = 1; for (let e = el; e && e !== document.body; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.visibility === "hidden" || cs.display === "none") return 0; o *= parseFloat(cs.opacity); } return o; };
    const words = (el) => (el.innerText || "").trim().split(/\s+/).filter(Boolean).length;
    const frames = [];
    for (const t of times) {
      if (tl) tl.seek(t, false);
      const items = [];
      document.querySelectorAll("[data-fz]").forEach((el) => {
        const o = vis(el); if (o < 0.05) return;
        const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return;
        const role = el.getAttribute("data-fz");
        const it = { role, x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), o: +o.toFixed(2) };
        if (["block", "note", "text", "caption", "part"].includes(role)) it.words = words(el);
        if (role === "code") it.lines = el.querySelectorAll(".fz-cl").length;
        const ov = [el, ...el.querySelectorAll(".fz-body,.nd,.fz-h2")].some((e) => e.scrollWidth > e.clientWidth + 3 && getComputedStyle(e).overflow !== "visible" ? true : e.scrollWidth > e.clientWidth + 3 && e.clientWidth > 0 && getComputedStyle(e).whiteSpace === "nowrap");
        const leafWide = [el, ...el.querySelectorAll("*")].some((e) => e.children.length === 0 && (e.textContent || "").trim() && e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 3);
        if (ov || leafWide) it.overflow = true;
        items.push(it);
      });
      frames.push({ t, items });
    }
    return { frames, sfx: window.__fz_sfx || [], errors: window.__fz_errors || [] };
  }, times);
  console.log(JSON.stringify(res));
  await b.close();
} else if (cmd === "still") {
  const b = await browser(); const p = await b.newPage();
  await p.setViewport({ width: +(a3 || 1920), height: +(a4 || 1080) });
  await p.goto(a1.startsWith("file://") ? a1 : "file://" + path.resolve(a1), { waitUntil: "load" });
  await p.evaluate(() => document.fonts.ready); await new Promise((r) => setTimeout(r, 300));
  await p.screenshot({ path: a2, fullPage: true }); await b.close();
} else {
  console.error("usage: sample.mjs catalogue <runtime> | sample <html> <times> | still <html> <png> [w h]");
  process.exit(2);
}
