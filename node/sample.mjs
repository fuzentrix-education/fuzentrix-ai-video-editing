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
  return puppeteer.launch({ executablePath: chrome(), headless: "shell", args: ["--allow-file-access-from-files", "--autoplay-policy=no-user-gesture-required",
    // software WebGL for the 3D templates: the sampler only reads DOM boxes, so SwiftShader is enough and works on any machine
    "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
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
    const count = (el) => (el.innerText || "").trim().split(/\s+/).filter(Boolean).length;
    // text marked data-nowords (a calendar's dates, a picture's labels) is a picture, not words to read
    const words = (el) => (el.hasAttribute("data-nowords") ? 0 : count(el) - [...el.querySelectorAll("[data-nowords]")].reduce((n, d) => n + count(d), 0));
    // the painted part of an element: its own box when it draws something (fill, border, shadow, image), else the union of what
    // its children paint and the real extent of its text; layout-only containers don't count (rule L12)
    const painted = (e) => { const cs = getComputedStyle(e);
      return (cs.backgroundColor !== "rgba(0, 0, 0, 0)" && cs.backgroundColor !== "transparent") || cs.backgroundImage !== "none" ||
        parseFloat(cs.borderTopWidth) + parseFloat(cs.borderLeftWidth) > 0 || cs.boxShadow !== "none" || /^(IMG|SVG|CANVAS|VIDEO|svg)$/.test(e.tagName); };
    const pbox = (e, depth = 0) => {
      if (vis(e) < 0.05) return null;
      const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return null;
      if (painted(e) || depth > 6) return [r.left, r.top, r.right, r.bottom];
      let u = null;
      const add = (q) => { if (q) u = u ? [Math.min(u[0], q[0]), Math.min(u[1], q[1]), Math.max(u[2], q[2]), Math.max(u[3], q[3])] : q; };
      for (const n of e.childNodes) {
        if (n.nodeType === 3 && n.textContent.trim()) { const g = document.createRange(); g.selectNodeContents(n); const t = g.getBoundingClientRect(); if (t.width > 0) add([t.left, t.top, t.right, t.bottom]); }
        else if (n.nodeType === 1) add(pbox(n, depth + 1));
      }
      return u;
    };
    const txtOf = (el) => { if (el.hasAttribute("data-nowords")) return ""; let s = ""; const walk = (n) => { for (const c of n.childNodes) { if (c.nodeType === 3) s += c.textContent; else if (c.nodeType === 1 && !/^(svg|style|script)$/i.test(c.tagName) && !c.hasAttribute("data-nowords") && vis(c) > 0.3) { s += " "; walk(c); s += " "; } } };
      walk(el); return s.replace(/\s+/g, " ").trim(); };
    const frames = [];
    for (const t of times) {
      if (tl) tl.seek(t, false);
      const items = [];
      document.querySelectorAll("[data-fz]").forEach((el) => {
        const o = vis(el); if (o < 0.05 && el.getAttribute("data-fz") !== "presenter") return;   // a hidden cut-out still marks where she is
        const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return;
        const role = el.getAttribute("data-fz");
        const it = { role, x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height), o: +o.toFixed(2) };
        if (["block", "note", "text", "caption", "part"].includes(role)) it.words = words(el);
        it.id = el.id; const tpl = el.getAttribute("data-tpl"); if (tpl) it.tpl = tpl;
        if (el.parentElement && el.parentElement.closest("[data-fz]")) it.nest = 1;   // inside another element (a row of a card)
        // the smallest text a viewer can read in it (rule L13); text inside pictures (SVG) doesn't count
        if (["block", "note", "text", "part", "title", "chrome", "code", "term"].includes(role)) {
          let m = 1e9; const walk = (n) => { for (const c of n.childNodes) { if (c.nodeType === 3 && c.textContent.trim()) { const pe = c.parentElement; if (!pe.closest("svg") && vis(pe) > 0.3) m = Math.min(m, parseFloat(getComputedStyle(pe).fontSize)); } else if (c.nodeType === 1) walk(c); } };
          walk(el); if (m < 1e9) it.fs = Math.round(m);
          if (role === "code" || role === "term") {        // the code itself (lines, output), not the tab title or Run button
            const ls = [...el.querySelectorAll(role === "code" ? ".fz-cl" : ".tl")].filter((e) => vis(e) > 0.3);
            if (ls.length) it.cfs = Math.round(Math.min(...ls.map((e) => parseFloat(getComputedStyle(e).fontSize))));
          }
        }
        // the text a viewer can read (characters still hidden by typing are left out): the sync checks match it to her words
        if (["block", "note", "text", "part", "title"].includes(role)) { const s = txtOf(el); if (s) it.txt = s.slice(0, 120); }
        if (role === "code") it.lines = el.querySelectorAll(".fz-cl").length;
        if (["block", "code", "term", "title"].includes(role)) { const q = pbox(el); if (q) it.pb = q.map(Math.round); }
        const ov = [el, ...el.querySelectorAll(".fz-body,.nd,.fz-h2")].some((e) => e.scrollWidth > e.clientWidth + 3 && getComputedStyle(e).overflow !== "visible" ? true : e.scrollWidth > e.clientWidth + 3 && e.clientWidth > 0 && getComputedStyle(e).whiteSpace === "nowrap");
        const leafWide = [el, ...el.querySelectorAll("*")].some((e) => e.children.length === 0 && (e.textContent || "").trim() && e.clientWidth > 0 && e.scrollWidth > e.clientWidth + 3);
        if (ov || leafWide) it.overflow = true;
        items.push(it);
      });
      frames.push({ t, items });
    }
    // exact first-seen times (rules S2, S5: 0.15 s early, 0.3 s late): the samples tell in which step an element's text, or one
    // of its words, first became readable; a binary search inside that step finds the moment (to 1/60 s)
    const wordsOf = (s) => (s.toLowerCase().match(/[0-9]+(?:\.[0-9]+)?|[a-z]+/g) || []).map((w) => w.replace(/[^0-9a-z]/g, "")).filter((w) => w.length >= 3 || /^\d+$/.test(w));
    const first = {};
    frames.forEach((fr, k) => fr.items.forEach((it) => {
      if (!it.txt) return;
      const f = first[it.id] = first[it.id] || { k, w: {} };
      for (const w of wordsOf(it.txt)) if (!(w in f.w)) f.w[w] = k;
    }));
    const search = (k, test) => {
      if (k === 0 || !tl) return times[k];
      let lo = times[k - 1], hi = times[k];
      for (let n = 0; n < 5; n++) { const mid = (lo + hi) / 2; tl.seek(mid, false); if (test()) hi = mid; else lo = mid; }
      return +hi.toFixed(3);
    };
    const refine = {};
    for (const id in first) {
      const el = document.getElementById(id); if (!el) continue;
      const f = first[id], r = { "@": search(f.k, () => vis(el) >= 0.05 && !!txtOf(el)) };
      for (const w in f.w) r[w] = f.w[w] === f.k ? r["@"] : search(f.w[w], () => vis(el) >= 0.05 && wordsOf(txtOf(el)).includes(w));
      refine[id] = r;
    }
    return { frames, refine, sfx: window.__fz_sfx || [], errors: window.__fz_errors || [] };
  }, times);
  console.log(JSON.stringify(res));
  await b.close();
} else if (cmd === "still") {
  const b = await browser(); const p = await b.newPage();
  await p.setViewport({ width: +(a3 || 1920), height: +(a4 || 1080) });
  await p.goto(a1.startsWith("file://") ? a1 : "file://" + path.resolve(a1), { waitUntil: "load" });
  await p.evaluate(() => document.fonts.ready); await new Promise((r) => setTimeout(r, 300));
  await p.screenshot({ path: a2, fullPage: true }); await b.close();
} else if (cmd === "svgfit") {
  // an illustration from the web: drop its full-canvas background and tiny credit marks near the edges, crop the viewBox to what's left
  const b = await browser(); const p = await b.newPage();
  const src = fs.readFileSync(a1, "utf8");
  await p.setContent(`<html><body style="margin:0">${src}</body></html>`);
  const out = await p.evaluate(() => {
    const svg = document.querySelector("svg"); if (!svg) return null;
    const vb = (svg.getAttribute("viewBox") || "").split(/[\s,]+/).map(Number);
    if (vb.length !== 4 || !(vb[2] > 0)) return null;
    svg.style.width = vb[2] + "px"; svg.style.height = vb[3] + "px"; svg.removeAttribute("width"); svg.removeAttribute("height");
    const R = svg.getBoundingClientRect(), A = vb[2] * vb[3];
    const leaves = [...svg.querySelectorAll("path,rect,circle,ellipse,polygon,polyline,line,text,image,use")].filter((e) => !e.closest("defs,clipPath,mask,pattern,symbol"));
    const box = (e) => { const r = e.getBoundingClientRect(); return { x0: r.left - R.left, y0: r.top - R.top, x1: r.right - R.left, y1: r.bottom - R.top, a: r.width * r.height }; };
    let removed = 0; const keep = [];
    leaves.forEach((e) => {
      const q = box(e); if (q.a <= 0) return;
      const full = q.a >= 0.95 * A && q.x0 <= 1 && q.y0 <= 1;
      const cx = (q.x0 + q.x1) / 2, cy = (q.y0 + q.y1) / 2, edge = cx < 0.15 * vb[2] || cx > 0.85 * vb[2] || cy < 0.15 * vb[3] || cy > 0.85 * vb[3];
      if (full || (q.a < 0.005 * A && edge)) { e.remove(); removed++; } else keep.push(q);
    });
    if (!keep.length) return null;
    const u = keep.reduce((m, q) => ({ x0: Math.min(m.x0, q.x0), y0: Math.min(m.y0, q.y0), x1: Math.max(m.x1, q.x1), y1: Math.max(m.y1, q.y1) }), { x0: 1e9, y0: 1e9, x1: -1e9, y1: -1e9 });
    const pad = 0.03 * Math.max(u.x1 - u.x0, u.y1 - u.y0);
    svg.setAttribute("viewBox", [vb[0] + u.x0 - pad, vb[1] + u.y0 - pad, u.x1 - u.x0 + 2 * pad, u.y1 - u.y0 + 2 * pad].map((v) => +v.toFixed(2)).join(" "));
    svg.removeAttribute("style");
    return { svg: new XMLSerializer().serializeToString(svg), removed };
  });
  if (out) fs.writeFileSync(a2, out.svg);
  console.log(JSON.stringify(out ? { removed: out.removed } : { error: "no svg or viewBox" }));
  await b.close();
} else {
  console.error("usage: sample.mjs catalogue <runtime> | sample <html> <times> | still <html> <png> [w h] | svgfit <in.svg> <out.svg>");
  process.exit(2);
}
