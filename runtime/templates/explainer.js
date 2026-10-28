/* Explainer family (design §7, rule V1): show the PROCESS the instructor describes, in step with her words.
   Data flowing into a database, values converting type, a range generating numbers, a request travelling and returning,
   a search scanning thousands of records, app screens being used. Every step has its own `at`, anchored to the word
   that names it. Coordinates are relative to `box` unless a param says otherwise. */
(function () {
  const R = FZ.register;
  const TONE = { ok: "var(--fz-success)", bad: "var(--fz-danger)", warn: "#C27803", accent: "var(--fz-accent)", action: "var(--fz-action)" };

  // move an element along a quadratic curve p0 -> p1 (bend = how far the control point lifts, px), shrinking to `endScale`
  function fly(a, e, p0, p1, g, dur = 0.8, bend = -120, endScale = 1) {
    const c = [(p0[0] + p1[0]) / 2, Math.min(p0[1], p1[1]) + bend];
    const o = { t: 0 };
    const place = (t) => {
      const u = 1 - t, x = u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0], y = u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1];
      e.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%) scale(${1 + (endScale - 1) * t})`;
    };
    place(0);
    a.tl.fromTo(o, { t: 0 }, { t: 1, duration: dur, ease: "power2.inOut", immediateRender: false, onUpdate: () => place(o.t) }, a.T(g));
  }
  // text that types in: one span per character, revealed in turn (deterministic under jump-seeks)
  function typed(a, parent, txt, g, cps = 16) {
    parent.innerHTML = [...String(txt)].map((ch) => `<span style="opacity:0">${a.esc(ch)}</span>`).join("");
    [...parent.children].forEach((c, k) => a.set(c, g + k / cps, { opacity: 1 }));
  }
  const dbSvg = (bands = 6) => `<svg viewBox="0 0 120 150" width="100%" height="100%" style="overflow:visible">
      <path d="M10 22v104c0 10 22 18 50 18s50-8 50-18V22" fill="var(--fz-action)"/>
      ${Array.from({ length: bands }, (_, i) => `<path class="band b${i}" d="M10 ${126 - i * 17}c0 10 22 18 50 18s50-8 50-18" fill="none" stroke="#fff" stroke-width="5" opacity="0"/>`).join("")}
      <ellipse cx="60" cy="22" rx="50" ry="18" fill="var(--fz-accent)"/></svg>`;
  const targetHtml = (kind, a) => kind === "database" ? dbSvg() :
    `<div style="width:100%;height:100%;border-radius:28px;background:var(--fz-action);color:#fff;display:grid;place-items:center;font-size:${kind === "table" ? 90 : 96}px">${a.icon({ table: "table", folder: "folder", server: "server", cloud: "cloud", box: "box" }[kind] || "database")}</div>`;

  // ---------- data-flow: items fly into a container ----------
  R({ name: "data-flow", family: "explainer", layers: ["plate"],
      doc: "Items (chips with icons) fly into a container (database, table, folder, server, cloud) as they are named; the container fills and counts. For collecting / storing / saving data.",
      params: { target: "{kind: database|table|folder|server|cloud, label, x, y, size} (box coords; default right side)", items: "[{text, icon, at, x, y}] flying in at `at` (sources default to a column on the left)",
                count: "{to, label} the container counts up as items arrive (optional)", at: "", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), t = p.target || {};
    const sz = t.size || 220, tx = bx.x + (t.x != null ? t.x : bx.w - sz - 20), ty = bx.y + (t.y != null ? t.y : 80);
    const tgt = a.el(targetHtml(t.kind || "database", a), "abs hide", { left: tx, top: ty, width: sz, height: sz * (t.kind === "database" || !t.kind ? 1.25 : 1) }, a.root, "part");
    a.pop(tgt, p.at); a.out(tgt, U);
    const parts = [tgt];
    if (t.label) { const l = a.el(a.md(t.label), "abs hide", { left: tx - 60, top: ty + sz * 1.3 + 14, width: sz + 120, textAlign: "center", font: "800 30px/1.1 var(--fz-font-display)" }, a.root, "part"); a.show(l, p.at + 0.2, U, { y: 10 }); parts.push(l); }
    let cnt = null;
    if (p.count) { cnt = a.el("0", "abs hide", { left: tx - 80, top: ty - 96, width: sz + 160, textAlign: "center", font: "900 46px/1 var(--fz-font-display)", color: "var(--fz-emph)", whiteSpace: "nowrap" }, a.root, "part"); a.show(cnt, p.at + 0.2, U, { y: 10 }); parts.push(cnt); }
    const items = p.items || [], n = Math.max(1, items.length);
    items.forEach((it, i) => {
      const sx = bx.x + (it.x != null ? it.x : 30), sy = bx.y + (it.y != null ? it.y : 60 + i * Math.min(110, (bx.h - 120) / n));
      const wrap = a.el("", "abs hide", { left: 0, top: 0 }, a.root, "part");
      const c = a.el(`${it.icon ? `<div class="fz-ic" style="width:46px;height:46px;font-size:24px">${a.icon(it.icon)}</div>` : ""}<span>${a.md(it.text)}</span>`, "fz-chip", { left: 0, top: 0, fontSize: 26 }, wrap);
      const appear = Math.max(p.at, it.at - 0.9);
      a.set(wrap, appear, { autoAlpha: 1 });
      a.tl.fromTo(c, { scale: 0.6 }, { scale: 1, duration: 0.35, ease: "back.out(2)", immediateRender: false }, a.T(appear));
      // wait at the source, then fly into the container's mouth (the wrapper carries the flight, the chip its own pop)
      fly(a, wrap, [sx, sy], [tx + sz / 2 - 60, ty + sz * 0.2], it.at, 0.85, -140, 0.3);
      wrap.style.transform = `translate(${sx}px, ${sy}px) translate(-50%, -50%)`;
      a.set(wrap, it.at + 0.85, { autoAlpha: 0 });
      a.pulse(tgt, it.at + 0.85, 1.06);
      const band = tgt.querySelector(`.b${i % 6}`); if (band) a.set(band, it.at + 0.85, { opacity: 0.55 });
      if (cnt) {
        const v0 = Math.round((i / n) * (p.count.to || n)), v1 = Math.round(((i + 1) / n) * (p.count.to || n)), o = { v: v0 };
        a.tl.fromTo(o, { v: v0 }, { v: v1, duration: 0.4, immediateRender: false, onUpdate: () => { cnt.textContent = `${Math.round(o.v).toLocaleString("en-IN")}${p.count.label ? " " + p.count.label : ""}`; } }, a.T(it.at + 0.85));
      }
      a.sfx("swish", it.at);
    });
    a.group(parts, p.at, U);
  });

  // ---------- process-flow: inputs -> process -> output ----------
  R({ name: "process-flow", family: "explainer", layers: ["plate"],
      doc: "Inputs box -> process (spinning icon) -> output card: dots travel through when the process runs. For data -> information, raw -> processed, input -> output.",
      params: { inputs: "{label, items: [text | {text, at}]}", process: "{label, icon (default gear), at}", output: "{label, text (markdown), at, note}", banner: "{text, at} equation under the flow (optional)",
                at: "", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), W = bx.w, H = Math.min(bx.h, 420);
    const iw = W * 0.27, pw = W * 0.2, ow = W * 0.33, gap = (W - iw - pw - ow) / 2;
    const inp = a.el(`<div class="fz-label" style="margin-bottom:18px">${a.esc((p.inputs || {}).label || "Data")}</div>`, "abs hide", { left: bx.x, top: bx.y, width: iw, height: H, borderRadius: 26, border: "3px dashed var(--fz-line)", background: "rgba(255,255,255,.6)", padding: "24px 26px" }, a.root, "part");
    a.show(inp, p.at, U, { x: -30 });
    const its = ((p.inputs || {}).items || []).map((x) => (typeof x === "string" ? { text: x } : x));
    its.forEach((it, i) => { const e = a.el(a.md(it.text), "abs hide", { left: 26 + (i % 2) * 18, top: 70 + i * Math.min(66, (H - 100) / Math.max(1, its.length)), font: "700 32px/1 var(--fz-font-mono)", color: "var(--fz-text2)" }, inp); a.inn(e, it.at || p.at + 0.3 + i * 0.25, { x: -12 }, 0.3); });
    const pr = p.process || {}, px0 = bx.x + iw + gap;
    const proc = a.el(`<div class="gear" style="font-size:110px;line-height:0;color:#fff">${a.icon(pr.icon || "gear")}</div><div class="fz-label" style="color:var(--fz-on-dark-soft);margin-top:20px">${a.esc(pr.label || "Process")}</div>`,
      "abs hide", { left: px0, top: bx.y + (H - pw * 1.05) / 2, width: pw, height: pw * 1.05, borderRadius: 30, background: "var(--fz-text)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", boxShadow: "0 30px 70px -20px rgba(13,39,76,.55)" }, a.root, "part");
    const run = pr.at != null ? pr.at : p.at + 1;
    a.pop(proc, Math.max(p.at, run - 0.8)); a.out(proc, U);
    a.tl.to(proc.querySelector(".gear"), { rotation: 360, duration: 1.6, ease: "power1.inOut", immediateRender: false }, a.T(run));
    const arrow = (x, g) => { const e = a.el(a.icon("arrow"), "abs hide", { left: x, top: bx.y + H / 2 - 40, fontSize: 80, color: "var(--fz-action)" }, a.root, "part"); a.inn(e, g, { x: -20 }, 0.35); a.out(e, U); return e; };
    const a1 = arrow(bx.x + iw + gap / 2 - 40, run - 0.4), a2 = arrow(px0 + pw + gap / 2 - 40, run + 0.9);
    for (let k = 0; k < 3; k++) { const d = a.el("", "abs hide", { left: 0, top: 0, width: 22, height: 22, borderRadius: 11, background: "var(--fz-accent)" }, a.root, "deco"); a.set(d, run + k * 0.18, { autoAlpha: 1 }); fly(a, d, [bx.x + iw * 0.6, bx.y + H * (0.35 + k * 0.15)], [px0 + pw / 2, bx.y + H / 2], run + k * 0.18, 0.6, -60, 0.4); a.set(d, run + k * 0.18 + 0.6, { autoAlpha: 0 }); }
    const o = p.output || {}, ox = px0 + pw + gap, oat = o.at != null ? o.at : run + 1.2;
    const outc = a.el(`<div class="fz-label" style="display:inline-block;background:var(--fz-action);color:#fff;padding:9px 14px;border-radius:10px">${a.esc(o.label || "Information")}</div>
      <div class="txt" style="font:700 46px/1.2 var(--fz-font-display);margin-top:26px">${a.md(o.text || "")}</div>${o.note ? `<div class="fz-small" style="margin-top:18px">${a.md(o.note)}</div>` : ""}`,
      "fz-card hide", { left: ox, top: bx.y + 20, width: ow, minHeight: H - 40, padding: "30px 34px" }, a.root, "part");
    a.show(outc, oat, U, { x: 30 }); a.sfx("ding", oat);
    const parts = [inp, proc, a1, a2, outc];
    if (p.banner) { const b = a.el(a.md(p.banner.text), "fz-dark abs hide", { left: bx.x, top: bx.y + H + 40, width: W, height: 110, borderRadius: 26, background: "var(--fz-text)", color: "#fff", display: "grid", placeItems: "center", font: "800 54px/1 var(--fz-font-display)" }, a.root, "part"); a.show(b, p.banner.at, U, { y: 30 }); parts.push(b); }
    a.group(parts, p.at, U);
  });

  // ---------- type-convert: "20" (str) -> int() -> 20 (int) ----------
  R({ name: "type-convert", family: "explainer", layers: ["plate"],
      doc: "A value changes type: a quoted value with its type badge goes through the conversion function and comes out converted. For input() -> int(), str(), float().",
      params: { value: "the value, e.g. 20", from_type: "default str", to_type: "default int", fn: "default int()", label: "caption above (markdown)", at: "input value appears", convert_at: "it goes through the function",
                then: "{text, at} a follow-up line, e.g. '20 + 1 = 21' (optional)", until: "", box: "x, y, w (default side slot)" } }, (a, p) => {
    const bx = a.box(p, "side"), U = a.until(p), W = Math.max(bx.w, 460), cv = p.convert_at != null ? p.convert_at : p.at + 2;
    const fromT = p.from_type || "str", toT = p.to_type || "int", fn = p.fn || "int()";
    const parts = [];
    if (p.label) { const l = a.el(a.md(p.label), "abs hide", { left: bx.x, top: bx.y, width: W, font: "700 28px/1.25 var(--fz-font-display)" }, a.root, "part"); a.show(l, p.at, U, { y: 10 }); parts.push(l); }
    const y0 = bx.y + (p.label ? 70 : 0);
    const chip = (txt, type, tone) => `<div style="font:800 52px/1 var(--fz-font-mono);color:var(--fz-text)">${a.esc(txt)}</div><div style="margin-top:12px;font:700 20px/1 var(--fz-font-mono);letter-spacing:.12em;padding:6px 12px;border-radius:8px;background:${tone};color:#fff;display:inline-block">${a.esc(type)}</div>`;
    const inC = a.el(chip(`"${p.value}"`, fromT, "#C27803"), "fz-card hide", { left: bx.x, top: y0, width: W * 0.36, padding: "22px 20px", textAlign: "center" }, a.root, "part");
    a.pop(inC, p.at); parts.push(inC);
    const mach = a.el(`<div style="font:800 40px/1 var(--fz-font-mono);color:#fff">${a.esc(fn)}</div>`, "abs hide",
      { left: bx.x + W * 0.39, top: y0 + 150, width: W * 0.24, height: 96, borderRadius: 22, background: "var(--fz-text)", display: "grid", placeItems: "center", boxShadow: "0 24px 50px -18px rgba(13,39,76,.55)" }, a.root, "part");
    a.pop(mach, Math.max(p.at + 0.3, cv - 0.7)); parts.push(mach);
    const outC = a.el(chip(String(p.value), toT, "var(--fz-success)"), "fz-card hide", { left: bx.x + W * 0.64, top: y0, width: W * 0.36, padding: "22px 20px", textAlign: "center", borderColor: "var(--fz-success)", borderWidth: "3px" }, a.root, "part");
    // the input drops into the machine, the machine pulses, the converted value pops out
    a.to(inC, cv, { y: 150, x: W * 0.04, scale: 0.55, autoAlpha: 0.25, duration: 0.5, ease: "power2.in" });
    a.pulse(mach, cv + 0.45, 1.12);
    a.inn(outC, cv + 0.7, { y: 150, x: -W * 0.08, scale: 0.55 }, 0.55, "back.out(1.6)"); a.sfx("ding", cv + 0.7);
    a.to(inC, cv + 1.3, { y: 0, x: 0, scale: 1, autoAlpha: 0.45, duration: 0.4 });
    parts.push(outC);
    a.out([inC, mach, outC], U);
    if (p.then) { const t = a.el(a.md(p.then.text), "fz-cchip hide", { left: bx.x + W * 0.64, top: y0 + 280, fontSize: 32 }, a.root, "part"); a.show(t, p.then.at, U, { y: 14 }); parts.push(t); }
    a.group(parts, p.at, U);
  });

  // ---------- range-gen: range() emits numbers one by one ----------
  R({ name: "range-gen", family: "explainer", layers: ["plate"],
      doc: "A range generator emits its numbers one by one into slots (first ones paced, the rest quickly), optionally stopping at a break value. For range(), loops generating values.",
      params: { call: "e.g. range(1, n+1)", n: "optional 'n = 20' tag", start: "first value (default 1)", end: "last value generated (inclusive)", max_slots: "slots shown (default 10; longer ranges show … and the last)",
                at: "", emit_at: "first number", pace: "s per number (default 0.45)", times: "[time per number] instead of pace", stop_value: "value where `break` stops the loop", stop_at: "time it stops",
                note: "{text, at} (e.g. 'n+1 is not included')", until: "", box: "x, y, w (default main slot)", size: "slot px (default 78)" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), sz = p.size || 78, gap = sz + 14;
    const start = p.start != null ? p.start : 1, end = p.end != null ? p.end : start + 9;
    const last = p.stop_value != null ? Math.min(end, p.stop_value) : end, maxS = p.max_slots || (p.stop_value != null ? 12 : 10);
    let vals = []; for (let v = start; v <= last; v++) vals.push(v);
    if (vals.length > maxS) vals = vals.slice(0, maxS - 2).concat(["…", last]);
    const gen = a.el(`<span style="color:var(--fz-on-dark-accent)">${a.esc(p.call || "range()")}</span>${p.n ? `<span style="margin-left:22px;font-size:26px;color:var(--fz-on-dark-soft)">${a.esc(p.n)}</span>` : ""}`,
      "fz-cchip hide", { left: bx.x, top: bx.y, fontSize: 38 }, a.root, "part");
    a.pop(gen, p.at);
    const parts = [gen], cols = Math.max(1, Math.floor(bx.w / gap));
    const emit = p.emit_at != null ? p.emit_at : p.at + 0.8, pace = p.pace || 0.45;
    vals.forEach((v, i) => {
      const x = bx.x + (i % cols) * gap, y = bx.y + 110 + Math.floor(i / cols) * gap;
      const slot = a.el("", "abs hide", { left: x, top: y, width: sz, height: sz, borderRadius: 18, border: "2px dashed var(--fz-line)" }, a.root, "part");
      a.inn(slot, p.at + 0.2 + i * 0.03, {}, 0.3); a.out(slot, U); parts.push(slot);
      const g = (p.times && p.times[i] != null) ? p.times[i] : emit + (i < 4 ? i * pace : 4 * pace + (i - 4) * pace * 0.5);
      const stopHere = p.stop_value != null && v === p.stop_value;
      const tile = a.el(a.esc(v), "fz-tile hide", { left: x, top: y, width: sz, height: sz, fontSize: Math.round(sz * (String(v).length > 2 ? 0.32 : 0.42)), borderRadius: 18 }, a.root, "part");
      a.set(tile, g, { autoAlpha: 1 });
      a.tl.fromTo(tile, { x: bx.x + 60 - x, y: bx.y + 10 - y, scale: 0.4 }, { x: 0, y: 0, scale: 1, duration: 0.45, ease: "back.out(1.6)", immediateRender: false }, a.T(g));
      if (stopHere) { a.to(tile, p.stop_at || g + 0.6, { backgroundColor: "#FDECEC", borderColor: "var(--fz-danger)", color: "var(--fz-danger)", duration: 0.3 }); a.sfx("bad", p.stop_at || g + 0.6); }
      else if (i < 6) a.sfx("tick", g);
      a.out(tile, U); parts.push(tile);
    });
    a.out(gen, U);
    if (p.note) { const nt = a.el(a.md(p.note.text), "fz-small abs hide", { left: bx.x, top: bx.y + 110 + Math.ceil(vals.length / cols) * gap + 10 }, a.root, "part"); a.show(nt, p.note.at, U, { y: 10 }); parts.push(nt); }
    a.group(parts, p.at, U);
  });

  // ---------- request-flow: packets travel between nodes ----------
  R({ name: "request-flow", family: "explainer", layers: ["plate"],
      doc: "Nodes with big icons; packets travel along curved links when they are sent (request -> processing -> result back). Optional blocked direct path. For client/server, user -> DBMS -> database, API calls.",
      params: { nodes: "[{id, text, icon, x, y, at}] (box coords)", links: "[{from, to, at}]", packets: "[{from, to, label, at, dur, kind: req|res}]", blocked: "{from, to, label, at} dashed red arc with a cross",
                results: "[{text, at, x, y}] small cards that appear (e.g. the returned record)", at: "", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), N = {}, NE = {}, parts = [];
    (p.nodes || []).forEach((n) => {
      const e = a.el(`<div style="font-size:84px;line-height:0;color:var(--fz-action)">${a.icon(n.icon || "box")}</div><div class="fz-label" style="margin-top:16px">${a.esc(n.text)}</div>`,
        "fz-card hide", { left: bx.x + n.x, top: bx.y + n.y, width: 210, height: 190, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }, a.root, "part");
      a.pop(e, n.at != null ? n.at : p.at); a.out(e, U); N[n.id] = [bx.x + n.x + 105, bx.y + n.y + 95]; NE[n.id] = e; parts.push(e);
    });
    const curve = (f, t, bend) => { const [x0, y0] = N[f], [x1, y1] = N[t], dir = x1 > x0 ? 1 : -1; return `M ${x0 + dir * 108} ${y0} Q ${(x0 + x1) / 2} ${Math.min(y0, y1) + bend} ${x1 - dir * 108} ${y1}`; };
    (p.links || []).forEach((l) => a.edge(curve(l.from, l.to, -70), l.at, U, "hot"));
    if (p.blocked) {
      const b = p.blocked, [x0, y0] = N[b.from], [x1, y1] = N[b.to];
      a.edge(`M ${x0} ${y0 - 100} Q ${(x0 + x1) / 2} ${Math.min(y0, y1) - 300} ${x1} ${y1 - 100}`, b.at, U, "red");
      const x = a.el(a.icon("x"), "abs hide", { left: (x0 + x1) / 2 - 32, top: Math.min(y0, y1) - 232, width: 64, height: 64, borderRadius: 32, background: "var(--fz-danger)", color: "#fff", display: "grid", placeItems: "center", fontSize: 36 }, a.root, "part");
      a.pop(x, b.at + 0.5); a.out(x, U); a.sfx("bad", b.at + 0.5); parts.push(x);
      if (b.label) { const t = a.el(a.esc(b.label), "abs hide", { left: (x0 + x1) / 2 - 200, top: Math.min(y0, y1) - 290, width: 400, textAlign: "center", font: "700 28px/1 var(--fz-font-body)", color: "var(--fz-danger)" }, a.root, "part"); a.show(t, b.at + 0.5, U, { y: 8 }); parts.push(t); }
    }
    (p.packets || []).forEach((k) => {
      const res = k.kind === "res";
      const e = a.el(`${a.icon(res ? "check" : "arrow")}<span>${a.esc(k.label || (res ? "Result" : "Request"))}</span>`, "abs hide",
        { left: 0, top: 0, display: "flex", alignItems: "center", gap: 10, padding: "10px 18px", borderRadius: 999, background: res ? "var(--fz-success)" : "var(--fz-action)", color: "#fff", font: "700 24px/1 var(--fz-font-body)", boxShadow: "0 14px 30px -10px rgba(13,39,76,.45)", whiteSpace: "nowrap" }, a.root, "deco");
      const [x0, y0] = N[k.from], [x1, y1] = N[k.to], d = k.dur || 1.2;
      a.set(e, k.at, { autoAlpha: 1 }); fly(a, e, [x0, y0 - 120], [x1, y1 - 120], k.at, d, -80); a.set(e, k.at + d + 0.15, { autoAlpha: 0 });
      if (NE[k.to]) a.pulse(NE[k.to], k.at + d, 1.06);
      a.sfx(res ? "good" : "swish", k.at);
    });
    (p.results || []).forEach((r) => { const e = a.el(a.md(r.text), "fz-card hide", { left: bx.x + (r.x || 0), top: bx.y + (r.y || 0), padding: "14px 22px", font: "700 26px/1 var(--fz-font-mono)", whiteSpace: "nowrap" }, a.root, "part"); a.show(e, r.at, U, { y: 14 }); parts.push(e); });
    a.group(parts, p.at, U);
  });

  // ---------- icon-grid: many items, a scanning search, found / crossed ----------
  R({ name: "icon-grid", family: "explainer", layers: ["plate"],
      doc: "A grid of icons standing for many items (students, records, files) with a count; optional magnifier scanning row by row, a found cell, or a cross. For 'thousands of records', manual search.",
      params: { icon: "user | file | database …", cols: "default 14", rows: "default 5", count: "number shown (counts up)", label: "under the number", at: "", until: "",
                scan: "{at, until} magnifier sweeps the rows", find: "{index, at} highlight one cell", cross: "{at, text} red slash + text", box: "default: main slot", cell: "px (default 44)" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), cols = p.cols || 14, rows = p.rows || 5, c = p.cell || 44, parts = [];
    let gy = bx.y;
    if (p.count != null) {
      const num = a.el("0", "abs hide", { left: bx.x - 6, top: bx.y, font: "900 120px/1 var(--fz-font-display)", color: "var(--fz-text)" }, a.root, "part"); a.show(num, p.at, U, { y: 14 });
      const o = { v: 0 }; a.tl.to(o, { v: p.count, duration: 1.3, ease: "power2.out", immediateRender: false, onUpdate: () => { num.textContent = Math.round(o.v).toLocaleString("en-IN"); } }, a.T(p.at + 0.1));
      parts.push(num); gy += 130;
      if (p.label) { const l = a.el(a.md(p.label), "abs hide", { left: bx.x, top: gy, font: "600 30px/1 var(--fz-font-body)", color: "var(--fz-text2)" }, a.root, "part"); a.show(l, p.at + 0.3, U, { y: 8 }); parts.push(l); gy += 60; }
    }
    const cells = [];
    for (let r = 0; r < rows; r++) for (let k = 0; k < cols; k++) {
      const e = a.el(a.icon(p.icon || "user"), "abs hide", { left: bx.x + k * (c + 8), top: gy + r * (c + 8), fontSize: c * 0.8, color: "var(--fz-text2)", opacity: 0 }, a.root, "deco");
      a.tl.fromTo(e, { autoAlpha: 0, y: 10 }, { autoAlpha: 0.75, y: 0, duration: 0.25, immediateRender: false }, a.T(p.at + 0.15 + (k + r) * 0.02)); a.out(e, U, {}, 0.2); cells.push(e);
    }
    const gb = a.el("", "abs hide", { left: bx.x, top: gy, width: cols * (c + 8), height: rows * (c + 8) }, a.root, "part"); a.set(gb, p.at, { autoAlpha: 1 }); a.out(gb, U); parts.push(gb);
    if (p.scan) {
      const m = a.el("", "abs hide", { left: 0, top: 0, width: 110, height: 110, borderRadius: 55, background: "rgba(255,255,255,.5)", border: "6px solid var(--fz-action)", boxShadow: "0 18px 36px -10px rgba(13,39,76,.4)" }, a.root, "deco");
      const d = Math.max(1, (p.scan.until || p.scan.at + 4) - p.scan.at), legs = Math.min(rows, 4);
      a.set(m, p.scan.at, { autoAlpha: 1, x: bx.x - 30, y: gy - 30 });
      for (let r = 0; r < legs; r++) {
        a.to(m, p.scan.at + (r * d) / legs, { x: r % 2 ? bx.x - 30 : bx.x + cols * (c + 8) - 80, y: gy - 30 + r * ((rows - 1) * (c + 8) / Math.max(1, legs - 1)), duration: d / legs, ease: "sine.inOut" });
      }
      a.out(m, p.scan.until || U); a.sfx("swish", p.scan.at);
    }
    if (p.find) { const e = cells[p.find.index || 0]; if (e) { a.to(e, p.find.at, { color: "var(--fz-success)", scale: 1.6, autoAlpha: 1, duration: 0.35, ease: "back.out(2)" }); a.sfx("good", p.find.at); } }
    if (p.cross) {
      const s = a.el("", "abs hide", { left: bx.x - 10, top: gy + rows * (c + 8) / 2 - 5, width: cols * (c + 8) + 20, height: 10, borderRadius: 5, background: "var(--fz-danger)", transform: "rotate(-6deg)", transformOrigin: "0 50%" }, a.root, "deco");
      a.tl.fromTo(s, { autoAlpha: 1, scaleX: 0 }, { scaleX: 1, duration: 0.4, ease: "power2.out", immediateRender: false }, a.T(p.cross.at)); a.out(s, U); a.sfx("bad", p.cross.at);
      if (p.cross.text) { const t = a.el(a.md(p.cross.text), "fz-chip hide", { left: bx.x, top: gy + rows * (c + 8) + 24 }, a.root, "part"); a.pop(t, p.cross.at + 0.3); a.out(t, U); parts.push(t); }
    }
    a.group(parts, p.at, U);
  });

  // ---------- form-card: a record whose fields fill in ----------
  R({ name: "form-card", family: "explainer", layers: ["plate"],
      doc: "A record / form / receipt card whose field values type in as they are said. For 'your name, age, branch…', a student record, a filled form.",
      params: { title: "", icon: "", fields: "[{label, value, at}]", stamp: "{text, at, tone: ok|bad|accent}", at: "", until: "", box: "x, y, w (default side slot)" } }, (a, p) => {
    const bx = a.box(p, "side"), U = a.until(p), fs = p.fields || [];
    const card = a.el(`<div style="display:flex;align-items:center;gap:14px;margin-bottom:18px">${p.icon ? `<div class="fz-ic">${a.icon(p.icon)}</div>` : ""}<div class="fz-label">${a.esc(p.title || "Record")}</div></div>`,
      "fz-card fz-pad hide", { left: bx.x, top: bx.y, width: bx.w }, a.root, "block");
    fs.forEach((f) => {
      const row = a.el(`<span style="color:var(--fz-text2)">${a.esc(f.label)}</span><span class="v" style="font:700 30px/1 var(--fz-font-mono);color:var(--fz-text)"></span>`, "", { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 0", borderTop: "1px solid var(--fz-line)", font: "600 26px/1 var(--fz-font-body)" }, card);
      const txt = String(f.value == null ? "" : f.value), g = f.at != null ? f.at : p.at + 0.5;
      typed(a, row.querySelector(".v"), txt, g, 20);
      if (txt) a.sfx("type", g);
    });
    a.show(card, p.at, U, { x: 30 });
    if (p.stamp) { const s = a.el(a.esc(p.stamp.text), "abs hide", { right: 24, top: 22, padding: "8px 14px", border: `3px solid ${TONE[p.stamp.tone] || TONE.ok}`, color: TONE[p.stamp.tone] || TONE.ok, borderRadius: 10, font: "800 22px/1 var(--fz-font-mono)", transform: "rotate(-8deg)" }, card); a.pop(s, p.stamp.at); }
  });

  // ---------- db-tables: a database with tables inside ----------
  R({ name: "db-tables", family: "explainer", layers: ["plate"],
      doc: "A database frame with its tables appearing inside, each with rows. For 'a database stores students, faculty, library records…'.",
      params: { label: "default 'Inside a database'", tables: "[{title, icon, rows: [text], at}]", ok: "{text, at} chip under the frame", at: "", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), ts = p.tables || [], cw = (bx.w - 70) / 2, parts = [];
    const head = a.el(`<div class="fz-ic dark">${a.icon("database")}</div><div class="fz-label">${a.esc(p.label || "Inside a database")}</div>`, "abs hide", { left: bx.x, top: bx.y, display: "flex", alignItems: "center", gap: 14 }, a.root, "part");
    a.show(head, p.at, U, { y: 10 }); parts.push(head);
    const rowsN = Math.ceil(ts.length / 2), th = 230;
    const fr = a.el("", "abs hide", { left: bx.x - 20, top: bx.y + 76, width: bx.w + 40, height: rowsN * (th + 24) + 30, borderRadius: 30, border: "3px dashed var(--fz-action)", background: "rgba(229,239,253,.35)" }, a.root, "part");
    a.inn(fr, p.at + 0.1, { scale: 0.97 }, 0.45); a.out(fr, U); parts.push(fr);
    ts.forEach((t, i) => {
      const e = a.el(`<div style="display:flex;align-items:center;gap:12px;font:800 28px/1 var(--fz-font-display);margin-bottom:12px">${t.icon ? `<div class="fz-ic" style="width:44px;height:44px;font-size:24px">${a.icon(t.icon)}</div>` : ""}${a.esc(t.title)}</div>` +
        (t.rows || []).map((r) => `<div style="font:600 22px/1 var(--fz-font-mono);color:var(--fz-text2);padding:10px 0;border-top:1px solid var(--fz-line)">${a.esc(r)}</div>`).join(""),
        "fz-card hide", { left: bx.x + (i % 2) * (cw + 30), top: bx.y + 96 + Math.floor(i / 2) * (th + 24), width: cw, height: th, padding: "20px 24px" }, a.root, "part");
      a.pop(e, t.at != null ? t.at : p.at + 0.4 + i * 0.4); a.out(e, U); a.sfx("pop", t.at); parts.push(e);
    });
    if (p.ok) { const c = a.el(`<div class="fz-ic green">${a.icon("check")}</div>${a.md(p.ok.text)}`, "fz-chip hide", { left: bx.x, top: bx.y + 96 + rowsN * (th + 24) + 30 }, a.root, "part"); a.pop(c, p.ok.at); a.out(c, U); parts.push(c); }
    a.group(parts, p.at, U);
  });

  // ---------- hub: a central node with spokes ----------
  R({ name: "hub", family: "explainer", layers: ["plate"],
      doc: "A central badge (the system) with spokes to what it does, each appearing as named. For DBMS -> create/retrieve/update/delete, a component and its jobs.",
      params: { title: "centre badge text", subtitle: "", label: "small label above", spokes: "[{text, icon, at}]", caption: "{text, at}", at: "", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), cx = bx.x + bx.w / 2, cy = bx.y + Math.min(bx.h, 600) / 2, parts = [];
    if (p.label) { const l = a.el(a.esc(p.label), "fz-label abs hide", { left: bx.x, top: bx.y - 10 }, a.root, "part"); a.show(l, p.at, U, { y: 10 }); parts.push(l); }
    const badge = a.el(`<div style="font:900 84px/1 var(--fz-font-display);color:#fff">${a.esc(p.title || "")}</div>${p.subtitle ? `<div style="font:600 22px/1.2 var(--fz-font-body);color:rgba(255,255,255,.8);margin-top:12px">${a.esc(p.subtitle)}</div>` : ""}`,
      "abs hide", { left: cx - 230, top: cy - 105, width: 460, height: 210, borderRadius: 40, background: "var(--fz-grad)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", boxShadow: "0 30px 90px -20px rgba(27,83,162,.6)" }, a.root, "part");
    a.pop(badge, p.at + 0.1); a.out(badge, U); a.sfx("impact", p.at + 0.1); parts.push(badge);
    const sp = p.spokes || [], rx = Math.min(bx.w / 2 - 130, 470), ry = Math.min(Math.min(bx.h, 600) / 2 - 40, 250);
    sp.forEach((s, i) => {
      const ang = -Math.PI / 2 + (i + 0.5) * (2 * Math.PI / sp.length) - Math.PI / sp.length, sx = cx + rx * Math.cos(ang), sy = cy + ry * Math.sin(ang);
      a.edge(`M ${cx} ${cy} L ${sx} ${sy}`, s.at, U, "", 0.35);
      const c = a.el(`${s.icon ? `<div class="fz-ic">${a.icon(s.icon)}</div>` : ""}<span>${a.md(s.text)}</span>`, "fz-chip hide", { left: sx, top: sy }, a.root, "part");
      gsap.set(c, { xPercent: -50, yPercent: -50 });
      a.tl.fromTo(c, { autoAlpha: 0, scale: 0.5 }, { autoAlpha: 1, scale: 1, duration: 0.4, ease: "back.out(2)", immediateRender: false }, a.T(s.at)); a.out(c, U); parts.push(c);
    });
    if (p.caption) { const t = a.el(a.md(p.caption.text), "abs hide", { left: bx.x, top: cy + ry + 80, width: bx.w, textAlign: "center", font: "600 30px/1.3 var(--fz-font-body)", color: "var(--fz-text2)" }, a.root, "part"); a.show(t, p.caption.at, U, { y: 10 }); parts.push(t); }
    a.group(parts, p.at, U);
  });

  // ---------- mockup: phone or browser screens being used ----------
  R({ name: "mockup", family: "explainer", layers: ["plate"],
      doc: "A browser window or phone with app screens that change as they are described: typing into fields, pressing buttons, a loading spinner, results. For 'open the portal, log in, click results…', an app.",
      params: { kind: "browser | phone", url: "browser address / phone app title", screens: "[{at, elements: [{title} | {subtitle} | {field, value, at} | {button, press_at} | {row, value} | {spinner, at, until} | {stat, value} | {badge}]}]",
                cursor: "[{x, y, at, click}] in frame coords", at: "", until: "", box: "x, y, w, h (default main slot)" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), phone = p.kind === "phone";
    const W = phone ? Math.min(bx.w, 380) : bx.w, H = phone ? W * 2 : Math.min(bx.h, W * 0.66);
    const frame = a.el(phone ? `<div style="height:44px;display:flex;align-items:center;justify-content:center;font:700 18px/1 var(--fz-font-body);color:var(--fz-text2)">${a.esc(p.url || "")}</div>`
      : `<div style="height:52px;display:flex;align-items:center;gap:10px;padding:0 20px;border-bottom:1px solid var(--fz-line)"><div style="width:13px;height:13px;border-radius:7px;background:#FF6058"></div><div style="width:13px;height:13px;border-radius:7px;background:#FFBD2E"></div><div style="width:13px;height:13px;border-radius:7px;background:#28CA42"></div><div style="margin-left:18px;padding:7px 18px;border-radius:10px;background:var(--fz-tint);font:500 18px/1 var(--fz-font-mono);color:var(--fz-text2)">${a.esc(p.url || "")}</div></div>`,
      "fz-card hide", { left: bx.x, top: bx.y, width: W, height: H, overflow: "hidden", borderRadius: phone ? 46 : 22, border: phone ? "10px solid var(--fz-text)" : undefined }, a.root, "block");
    a.show(frame, p.at, U, { y: 30 });
    const screens = p.screens || [];
    screens.forEach((s, i) => {
      const sc = a.el("", "abs hide", { left: 0, top: phone ? 44 : 52, width: W - (phone ? 20 : 0), height: H - 60, padding: phone ? "18px 22px" : "34px 44px", display: "flex", flexDirection: "column", gap: phone ? 14 : 18 }, frame);
      const g0 = s.at != null ? s.at : p.at, g1 = screens[i + 1] ? screens[i + 1].at : null;
      a.set(sc, g0, { autoAlpha: 1 }); if (g1 != null) a.set(sc, g1, { autoAlpha: 0 });
      (s.elements || []).forEach((e) => {
        const before = sc.children.length;
        if (e.title) a.el(a.md(e.title), "", { font: `800 ${phone ? 30 : 40}px/1.1 var(--fz-font-display)` }, sc);
        else if (e.subtitle) a.el(a.md(e.subtitle), "", { font: "500 20px/1.2 var(--fz-font-mono)", color: "var(--fz-text2)" }, sc);
        else if (e.field != null) {
          const f = a.el(`<div style="font:600 18px/1 var(--fz-font-body);color:var(--fz-text2);margin-bottom:8px">${a.esc(e.field)}</div><div class="v" style="height:52px;border:2px solid var(--fz-line);border-radius:12px;padding:0 16px;display:flex;align-items:center;font:600 24px/1 var(--fz-font-mono)"></div>`, "", {}, sc);
          const txt = String(e.value || ""), g = e.at != null ? e.at : g0 + 0.5;
          typed(a, f.querySelector(".v"), txt, g, 14);
          if (txt) a.sfx("type", g);
        } else if (e.button) {
          const b = a.el(a.esc(e.button), "", { alignSelf: "flex-start", padding: "14px 34px", borderRadius: 12, background: "var(--fz-action)", color: "#fff", font: "700 24px/1 var(--fz-font-body)" }, sc);
          if (e.press_at != null) { a.pulse(b, e.press_at, 0.92); a.sfx("click", e.press_at); }
        } else if (e.row != null) a.el(`<span>${a.md(e.row)}</span><b>${a.esc(e.value == null ? "" : e.value)}</b>`, "", { display: "flex", justifyContent: "space-between", padding: "12px 0", borderBottom: "1px solid var(--fz-line)", font: "600 24px/1 var(--fz-font-body)" }, sc);
        else if (e.spinner != null) {
          const r = a.el(`<div class="sp" style="width:46px;height:46px;border-radius:50%;border:6px solid var(--fz-tint);border-top-color:var(--fz-action)"></div><span>${a.esc(e.spinner)}</span>`, "hide", { display: "flex", alignItems: "center", gap: 18, font: "600 24px/1 var(--fz-font-body)", color: "var(--fz-text2)" }, sc);
          const g = e.at != null ? e.at : g0, gu = e.until != null ? e.until : g + 2;
          a.set(r, g, { autoAlpha: 1 }); a.set(r, gu, { autoAlpha: 0, display: "none" });
          a.tl.fromTo(r.querySelector(".sp"), { rotation: 0 }, { rotation: 360 * Math.max(1, Math.round(gu - g)), duration: Math.max(0.5, gu - g), ease: "none", immediateRender: false }, a.T(g));
        } else if (e.stat != null) a.el(`${a.esc(e.stat)} <span style="color:var(--fz-on-dark-accent)">${a.esc(e.value || "")}</span>`, "", { alignSelf: "flex-start", padding: "14px 22px", borderRadius: 14, background: "var(--fz-text)", color: "#fff", font: "800 30px/1 var(--fz-font-display)" }, sc);
        else if (e.badge) a.el(a.md(e.badge), "fz-pill", {}, sc);
        if (e.at != null && e.field == null && e.spinner == null && sc.children.length > before) { const n = sc.children[sc.children.length - 1]; a.set(n, g0, { autoAlpha: 0 }); a.inn(n, e.at, { y: 12 }, 0.35); }
      });
    });
    const pts = p.cursor || [];
    if (pts.length) {
      const cur = a.el(`<svg width="40" height="40" viewBox="0 0 24 24"><path d="M4 2l16 9-7 2-3 7z" fill="#0D274C" stroke="#fff" stroke-width="1.5"/></svg>`, "abs hide", { left: 0, top: 0 }, frame);
      a.set(cur, pts[0].at - 0.9, { autoAlpha: 1, x: pts[0].x - 140, y: pts[0].y + 90 });
      pts.forEach((c, i) => {
        const from = i ? pts[i - 1].at + 0.1 : pts[0].at - 0.85;
        a.to(cur, from, { x: c.x, y: c.y, duration: Math.max(0.25, c.at - from - 0.05), ease: "power2.inOut" });
        if (c.click) { const rp = a.el("", "abs hide", { left: c.x - 24, top: c.y - 24, width: 48, height: 48, borderRadius: 24, border: "4px solid var(--fz-action)" }, frame); a.tl.fromTo(rp, { autoAlpha: 1, scale: 0.3 }, { autoAlpha: 0, scale: 1.6, duration: 0.5, immediateRender: false }, a.T(c.at)); a.sfx("click", c.at); }
      });
      a.out(cur, U, {}, 0.2);
    }
  });

  // ---------- callouts: short chips around the free space ----------
  R({ name: "callouts", family: "explainer", layers: ["plate", "studio"],
      doc: "Short chips that pop up at free positions as each point is said, with a gentle float (pain points, benefits, reactions). Screen coordinates.",
      params: { items: "[{text, icon, tone: red|amber|green|'', x, y, at, until}]", until: "" } }, (a, p) => {
    const U = a.until(p), els = (p.items || []).map((it) => {
      const c = a.el(`${it.icon ? `<div class="fz-ic ${it.tone || ""}">${a.icon(it.icon)}</div>` : ""}<span>${a.md(it.text)}</span>`, "fz-chip hide", { left: it.x, top: it.y }, a.root, "part");
      a.pop(c, it.at); a.out(c, it.until != null ? it.until : U); a.sfx("pop", it.at);
      a.tl.fromTo(c, { y: 0 }, { y: -8, duration: 1.4, yoyo: true, repeat: 3, ease: "sine.inOut", immediateRender: false }, a.T(it.at + 0.5));
      return c;
    });
    a.group(els, Math.min(...(p.items || [{ at: 0 }]).map((i) => i.at)), U);
  });

  // ---------- checklist ----------
  R({ name: "checklist", family: "explainer", layers: ["plate"],
      doc: "Rows that tick off one by one as they are said (benefits, requirements, a recap). The last row may be a highlighted conclusion.",
      params: { title: "", items: "[{text, icon, at}]", conclusion: "{text, at} dark banner under the list", at: "", until: "", box: "x, y, w (default main slot)" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), parts = [];
    if (p.title) { const t = a.el(a.esc(p.title), "fz-label abs hide", { left: bx.x, top: bx.y }, a.root, "part"); a.show(t, p.at, U, { y: 8 }); parts.push(t); }
    (p.items || []).forEach((it, i) => {
      const r = a.el(`<div class="fz-ic">${a.icon(it.icon || "check")}</div><span style="flex:1">${a.md(it.text)}</span><div class="ck" style="width:40px;height:40px;border-radius:20px;background:var(--fz-success);color:#fff;display:grid;place-items:center;font-size:24px">${a.icon("check")}</div>`,
        "fz-card hide", { left: bx.x, top: bx.y + 44 + i * 92, width: bx.w, height: 78, display: "flex", alignItems: "center", gap: 18, padding: "0 20px", font: "600 28px/1 var(--fz-font-body)" }, a.root, "part");
      a.show(r, it.at, U, { x: 30 }); a.tl.fromTo(r.querySelector(".ck"), { scale: 0 }, { scale: 1, duration: 0.35, ease: "back.out(2.2)", immediateRender: false }, a.T(it.at + 0.4)); a.sfx("tick", it.at + 0.4); parts.push(r);
    });
    if (p.conclusion) { const c = a.el(a.md(p.conclusion.text), "fz-dark abs hide", { left: bx.x, top: bx.y + 60 + (p.items || []).length * 92, width: bx.w, padding: "26px 30px", borderRadius: 22, background: "var(--fz-text)", color: "#fff", font: "800 36px/1.2 var(--fz-font-display)" }, a.root, "part"); a.show(c, p.conclusion.at, U, { y: 20 }); a.sfx("ding", p.conclusion.at); parts.push(c); }
    a.group(parts, p.at, U);
  });

  // ---------- big-word: one giant kinetic word ----------
  R({ name: "big-word", family: "explainer", layers: ["plate"],
      doc: "One giant word letter by letter (the term being introduced: DBMS, DATABASE), with an optional expansion line. Once per term, when it is first named.",
      params: { text: "the word", sub: "expansion or tagline (markdown), e.g. '*D*atabase *M*anagement *S*ystem'", sub_at: "", at: "", until: "", box: "x, y, w (default hero slot)", size: "px (default 170)" } }, (a, p) => {
    const bx = a.box(p, "hero"), U = a.until(p), size = p.size || Math.min(170, Math.floor(bx.w / (0.66 * Math.max(3, String(p.text).length))));
    const w = a.el([...String(p.text)].map((ch) => `<span class="ch" style="display:inline-block">${a.esc(ch)}</span>`).join(""), "abs hide",
      { left: bx.x, top: bx.y, font: `900 ${size}px/1 var(--fz-font-display)`, letterSpacing: "-.02em", color: "var(--fz-bigword, var(--fz-action))", whiteSpace: "nowrap" }, a.root, "block");
    a.set(w, p.at, { autoAlpha: 1 });
    a.tl.fromTo(w.querySelectorAll(".ch"), { yPercent: 60, autoAlpha: 0 }, { yPercent: 0, autoAlpha: 1, duration: 0.5, ease: "back.out(1.6)", stagger: 0.06, immediateRender: false }, a.T(p.at));
    a.out(w, U); a.sfx("whoosh", p.at);
    if (p.sub) { const s = a.el(a.md(p.sub), "abs hide", { left: bx.x + 6, top: bx.y + size * 1.05, font: "700 40px/1.2 var(--fz-font-display)", color: "var(--fz-text)" }, a.root, "text"); a.show(s, p.sub_at || p.at + 0.8, U, { y: 14 }); }
  });

  // ---------- scene: a dark full-frame scene behind the instructor (compose mode) ----------
  R({ name: "scene", family: "explainer", layers: ["plate"], static: false,
      doc: "Compose mode only: switch the background behind the instructor to a dark brand scene for a big moment (the hero reveal, a fun fact); text turns light for its duration.",
      params: { kind: "dark", at: "", until: "" } }, (a, p) => {
    const bg = a.byId("fz-bg");
    if (!bg) throw new Error("scene needs compose mode (no background layer behind the instructor in a rough cut)");
    const U = a.until(p);
    const d = a.el(`<div style="position:absolute;inset:0;background:radial-gradient(circle at 70% 40%, rgba(22,187,200,.25), transparent 55%),repeating-conic-gradient(from 0deg at 70% 40%, rgba(255,255,255,.035) 0 6deg, transparent 6deg 14deg)"></div>`,
      "abs hide", { left: 0, top: 0, width: 1920, height: 1080, background: "linear-gradient(160deg, #0D274C 0%, #0B1730 100%)" }, bg, "deco");
    a.inn(d, p.at, {}, 0.6, "power2.out"); a.out(d, U, {}, 0.6);
    a.set(a.root, p.at + 0.25, { attr: { "data-scene": "dark" } });      // CSS flips text to light and cards to glass
    a.set(a.root, U + 0.2, { attr: { "data-scene": "" } });
  });
})();
