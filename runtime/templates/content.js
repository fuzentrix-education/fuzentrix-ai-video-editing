/* Content-driven families: Kinetic Typography, Technical Diagram, Data Storytelling.
   The planner adds these only where the content calls for them (design §7.2). */
(function () {
  const R = FZ.register;

  // ---------- Kinetic Typography: key terms and takeaways only, never running speech ----------
  R({ name: "term-reveal", family: "kinetic", layers: ["plate", "studio"], doc: "The key term or a takeaway built word by word (12 words at most). Words in *stars* get the brand gradient.",
      params: { text: "markdown, 12 words max", times: "optional [time per word]; default staggered from at", at: "", until: "", box: "default: main slot", size: "px (default 88)" } }, (a, p) => {
    const bx = a.box(p, "main"), words = String(p.text || "").split(/\s+/).filter(Boolean);
    if (words.length > 12) window.__fz_errors.push(`term-reveal: ${words.length} words (max 12)`);
    const wrap = a.el("", "abs", { left: bx.x, top: bx.y, width: bx.w, font: `900 ${p.size || 88}px/1.05 var(--fz-font-display)`, color: "var(--fz-text)", letterSpacing: "-.015em" }, a.root, "block");
    words.forEach((w, i) => {
      const grad = /^\*.*\*[.,!?:]?$/.test(w), clean = w.replace(/\*/g, "");
      const s = a.el(a.esc(clean), "hide", { display: "inline-block", marginRight: "0.25em" }, wrap);
      if (grad) s.style.cssText += ";background:var(--fz-grad-text, var(--fz-grad));-webkit-background-clip:text;background-clip:text;color:transparent";
      const t = p.times && p.times[i] != null ? p.times[i] : p.at + i * 0.12;
      a.inn(s, t, { yPercent: 60 }, 0.55, "power4.out"); a.out(s, a.until(p), { yPercent: -30 }, 0.3);
    });
    a.sfx("whoosh", p.at);
  });

  R({ name: "rule-stack", family: "kinetic", layers: ["plate", "studio"], doc: "Two or three short lines that stack into a rule or takeaway; the last line is emphasised.",
      params: { lines: "[{text, at}]", until: "", box: "default: main slot", size: "px (default 64)" } }, (a, p) => {
    const bx = a.box(p, "main"), L = p.lines || [], fs = p.size || 64;
    const parts = L.map((ln, i) => {
      const last = i === L.length - 1;
      const e = a.el(a.md(ln.text), "abs hide", { left: bx.x, top: bx.y + i * fs * 1.25, font: `${last ? 900 : 800} ${fs}px/1.1 var(--fz-font-display)`, color: last ? "var(--fz-emph)" : "var(--fz-text)" }, a.root, "block");
      a.tl.fromTo(e, { autoAlpha: 0, clipPath: "inset(0% 100% 0% 0%)" }, { autoAlpha: 1, clipPath: "inset(0% 0% 0% 0%)", duration: 0.6, ease: "power3.out", immediateRender: false }, a.T(ln.at));
      a.out(e, a.until(p)); a.sfx(last ? "ding" : "swish", ln.at);
      return e;
    });
    a.group(parts, L.length ? L[0].at : p.at, a.until(p));
  });

  R({ name: "contrast", family: "kinetic", layers: ["plate"], doc: "'X vs Y' split: two titles with a short line each and a 'vs' between.",
      params: { left: "{title, text, at, tone}", right: "{title, text, at, tone}", vs_at: "", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), w = (bx.w - 140) / 2;
    const parts = [["left", 0], ["right", w + 140]].map(([k, dx]) => {
      const s = p[k]; if (!s) return null;
      const tfs = Math.min(64, Math.floor((w - 72) / (0.62 * Math.max(4, String(s.title).replace(/[*_`]/g, "").length))));   // long titles shrink to fit
      const e = a.el(`<div style="font:900 ${tfs}px/1 var(--fz-font-display);color:var(--fz-${s.tone || "text"})">${a.md(s.title)}</div><div class="fz-body" style="margin-top:16px">${a.md(s.text || "")}</div>`, "fz-card fz-pad hide", { left: bx.x + dx, top: bx.y, width: w }, a.root, "block");
      a.show(e, s.at, a.until(p), { x: k === "left" ? -40 : 40 }, 0.55, "back.out(1.3)"); a.sfx("swish", s.at);
      return e;
    });
    a.group(parts, p.left ? p.left.at : p.at, a.until(p));
    const vs = a.el("vs", "abs hide", { left: bx.x + w + 30, top: bx.y + 60, width: 80, textAlign: "center", font: "900 44px/1 var(--fz-font-display)", color: "var(--fz-accent)" }, a.root, "text");
    a.pop(vs, p.vs_at != null ? p.vs_at : p.right.at); a.out(vs, a.until(p));
  });

  // ---------- Technical Diagram: blueprint grid on white, blocks and arrows ----------
  R({ name: "blocks", family: "diagram", layers: ["plate"], doc: "Labelled blocks with icons and arrows on a light blueprint grid (architecture, client-server, request flow). Coordinates relative to the box.",
      params: { nodes: "[{id, x, y, w, h, text, icon, at}]", links: "[{from, to, label, at, tone: hot|green|red}]", grid: "true to draw the blueprint grid (default true)", at: "", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), N = {};
    if (p.grid !== false) { const g = a.el("", "abs hide", { left: bx.x, top: bx.y, width: bx.w, height: bx.h, borderRadius: 20, backgroundImage: "linear-gradient(var(--fz-line) 1px, transparent 1px), linear-gradient(90deg, var(--fz-line) 1px, transparent 1px)", backgroundSize: "40px 40px", opacity: 0.55 }, a.root, "deco"); a.show(g, p.at, U, { scale: 0.98 }, 0.5); }
    (p.nodes || []).forEach((n) => {
      const e = a.el(`${n.icon ? `<div class="fz-ic" style="width:64px;height:64px;font-size:36px">${a.icon(n.icon)}</div>` : ""}<div style="font:800 28px/1.15 var(--fz-font-display);margin-top:${n.icon ? 12 : 0}px">${a.md(n.text)}</div>`,
        "fz-card hide", { left: bx.x + n.x, top: bx.y + n.y, width: n.w || 220, height: n.h || 150, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: 16 }, a.root, "block");
      N[n.id] = { x: bx.x + n.x, y: bx.y + n.y, w: n.w || 220, h: n.h || 150, e };
      a.show(e, n.at, U, { scale: 0.8 }, 0.45, "back.out(1.6)"); a.sfx("pop", n.at);
    });
    a.group(Object.values(N).map((n) => n.e), Math.min(...(p.nodes || []).map((n) => n.at)), U);
    (p.links || []).forEach((l) => {
      const A = N[l.from], B = N[l.to]; if (!A || !B) return;
      const acx = A.x + A.w / 2, acy = A.y + A.h / 2, bcx = B.x + B.w / 2, bcy = B.y + B.h / 2;
      const horiz = Math.abs(bcx - acx) >= Math.abs(bcy - acy);
      const d = horiz ? `M ${bcx > acx ? A.x + A.w : A.x} ${acy} L ${bcx > acx ? B.x - 8 : B.x + B.w + 8} ${bcy}` : `M ${acx} ${bcy > acy ? A.y + A.h : A.y} L ${bcx} ${bcy > acy ? B.y - 8 : B.y + B.h + 8}`;
      const path = a.edge(d, l.at, U, l.tone || "hot");
      if (l.label) { const pt = path.getPointAtLength(path.getTotalLength() / 2); const t = a.el(a.esc(l.label), "fz-flab hide", { left: pt.x - 40, top: pt.y - 40 }, a.root, "text"); a.show(t, l.at + 0.1, U, { scale: 0.7 }, 0.3); }
    });
  });

  R({ name: "table", family: "diagram", layers: ["plate"], doc: "A data table (database rows, comparisons). Rows enter when said; cells or rows can be highlighted.",
      params: { title: "optional", columns: "[header...]", rows: "[[cell...]...]", row_at: "[time per row] (default all at `at`)", highlights: "[{row, col (optional), at, until, tone: emph|success|danger}]", at: "", until: "", box: "default: main slot", key_cols: "[indices shown as key columns]" } }, (a, p) => {
    const bx = a.box(p, "main"), cols = p.columns || [], U = a.until(p);
    const tbl = a.el(`${p.title ? `<div class="fz-label" style="margin:0 0 14px 4px">${a.md(p.title)}</div>` : ""}<div class="tw" style="border-radius:18px;overflow:hidden;border:1px solid var(--fz-line);background:var(--fz-card);box-shadow:var(--fz-shadow)"></div>`,
      "abs hide", { left: bx.x, top: bx.y, width: bx.w }, a.root, "block");
    const tw = tbl.querySelector(".tw"), grid = `display:grid;grid-template-columns:repeat(${cols.length},1fr)`;
    a.el(cols.map((c, i) => `<div style="padding:16px 20px;font:700 22px/1 var(--fz-font-mono);letter-spacing:.06em;text-transform:uppercase;color:${(p.key_cols || []).includes(i) ? "var(--fz-emph)" : "var(--fz-text2)"}">${a.esc(c)}</div>`).join(""), "", { cssText: grid + ";background:var(--fz-tint)" }, tw);
    a.show(tbl, p.at, U, { y: 24 }, 0.55); a.sfx("swish", p.at);
    const R_ = (p.rows || []).map((r, i) => {
      const row = a.el(r.map((c) => `<div class="c" style="padding:14px 20px;font:600 28px/1.2 var(--fz-font-body);border-top:1px solid var(--fz-line)">${a.esc(c)}</div>`).join(""), "hide", { cssText: grid }, tw);
      a.inn(row, p.row_at && p.row_at[i] != null ? p.row_at[i] : p.at + 0.2 + i * 0.08, { x: -16 }, 0.3);
      return row;
    });
    (p.highlights || []).forEach((h) => { const r = R_[h.row]; if (!r) return; const tgt = h.col != null ? r.children[h.col] : r; a.to(tgt, h.at, { backgroundColor: h.tone === "danger" ? "#FDECEC" : h.tone === "success" ? "#E3F5EA" : "#E6F6FA", duration: 0.25 }); if (h.until != null) a.to(tgt, h.until, { backgroundColor: "rgba(0,0,0,0)", duration: 0.25 }); a.sfx("blip", h.at); });
  });

  // ---------- Data Storytelling ----------
  R({ name: "bars", family: "data", layers: ["plate"], doc: "Bar chart that builds as values are said.",
      params: { title: "optional", items: "[{label, value, at, tone: accent|success|danger|warning}]", max: "scale max (default largest value)", unit: "suffix", at: "", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), it = p.items || [], max = p.max || Math.max(...it.map((i) => i.value)), U = a.until(p);
    const bw = Math.min(160, (bx.w - 40) / it.length - 40), chartH = bx.h - 120;
    if (p.title) { const t = a.el(a.md(p.title), "fz-h2 abs hide", { left: bx.x, top: bx.y }, a.root, "text"); a.show(t, p.at, U, { y: 14 }, 0.45); }
    const parts = [];
    it.forEach((b, i) => {
      const x = bx.x + 20 + i * (bw + 40), h = Math.max(6, (b.value / max) * chartH), base = bx.y + 80 + chartH;
      const bar = a.el("", "abs hide", { left: x, top: base - h, width: bw, height: h, borderRadius: "14px 14px 4px 4px", background: `var(--fz-${b.tone || "accent"})`, transformOrigin: "50% 100%" }, a.root, "block");
      const val = a.el(`${a.esc(b.value)}${a.esc(p.unit || "")}`, "abs hide", { left: x, top: base - h - 44, width: bw, textAlign: "center", font: "800 32px/1 var(--fz-font-display)" }, a.root, "text");
      const lab = a.el(a.esc(b.label), "abs hide", { left: x - 20, top: base + 14, width: bw + 40, textAlign: "center", font: "600 24px/1.2 var(--fz-font-body)", color: "var(--fz-text2)" }, a.root, "text");
      a.inn(bar, b.at, { scaleY: 0 }, 0.6, "power3.out"); a.inn(val, b.at + 0.4, { y: 10 }, 0.3); a.inn(lab, b.at, { y: 10 }, 0.3);
      a.out([bar, val, lab], U); a.sfx("pop", b.at);
      parts.push(bar, val, lab);
    });
    a.group(parts, it.length ? it[0].at : p.at, U);
  });

  R({ name: "counter", family: "data", layers: ["plate", "studio"], doc: "A number that counts up to its value, with a label.",
      params: { value: "number", from: "start (default 0)", prefix: "", suffix: "", locale: "digit grouping (default en-IN: 10,000 · 1,00,000; `plain` for years: 1966)", label: "markdown", at: "", until: "", dur: "count duration (default 1.2)", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main");
    const c = a.el(`<div class="n" style="font:900 120px/1 var(--fz-font-display);color:var(--fz-emph)">${a.esc(p.prefix || "")}${p.from || 0}${a.esc(p.suffix || "")}</div><div class="fz-body" style="margin-top:12px">${a.md(p.label || "")}</div>`, "abs hide", { left: bx.x, top: bx.y }, a.root, "block");
    a.show(c, p.at, a.until(p), { y: 20 }, 0.5);
    const o = { v: p.from || 0 }, n = c.querySelector(".n");
    a.tl.to(o, { v: p.value, duration: p.dur || 1.2, ease: "power2.out", onUpdate: () => { n.textContent = `${p.prefix || ""}${p.locale === "plain" ? String(Math.round(o.v)) : Math.round(o.v).toLocaleString(p.locale || "en-IN")}${p.suffix || ""}`; } }, a.T(p.at + 0.2));
    a.sfx("tick", p.at + 0.2);
  });

  R({ name: "curve", family: "data", layers: ["plate"], doc: "Line chart that draws itself (growth, Big-O). Points are in data units.",
      params: { series: "[{label, points: [[x, y]...], tone, at}]", x_label: "", y_label: "", xmax: "", ymax: "", at: "", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), S = p.series || [];
    const xmax = p.xmax || Math.max(...S.flatMap((s) => s.points.map((q) => q[0]))), ymax = p.ymax || Math.max(...S.flatMap((s) => s.points.map((q) => q[1])));
    const X = (x) => bx.x + 80 + (x / xmax) * (bx.w - 120), Y = (y) => bx.y + bx.h - 60 - (y / ymax) * (bx.h - 100);
    a.edge(`M ${bx.x + 80} ${bx.y + 20} L ${bx.x + 80} ${bx.y + bx.h - 60} L ${bx.x + bx.w - 20} ${bx.y + bx.h - 60}`, p.at, U, "", 0.6);
    if (p.x_label) { const t = a.el(a.esc(p.x_label), "fz-small abs hide", { left: bx.x + bx.w - 260, top: bx.y + bx.h - 40, width: 240, textAlign: "right" }, a.root, "text"); a.show(t, p.at, U, { y: 8 }, 0.3); }
    if (p.y_label) { const t = a.el(a.esc(p.y_label), "fz-small abs hide", { left: bx.x, top: bx.y }, a.root, "text"); a.show(t, p.at, U, { y: 8 }, 0.3); }
    S.forEach((s) => {
      const d = "M " + s.points.map((q) => `${X(q[0]).toFixed(1)} ${Y(q[1]).toFixed(1)}`).join(" L ");
      const path = a.edge(d, s.at, U, s.tone === "red" ? "red" : s.tone === "green" ? "green" : "hot", 1.2);
      path.removeAttribute("marker-end");
      const last = s.points[s.points.length - 1];
      if (s.label) { const t = a.el(a.md(s.label), "abs hide", { left: X(last[0]) - 200, top: Y(last[1]) - 44, width: 190, textAlign: "right", font: "700 26px/1.1 var(--fz-font-display)" }, a.root, "text"); a.show(t, s.at + 1.0, U, { y: 8 }, 0.3); }
      a.sfx("swish", s.at);
    });
  });
})();
