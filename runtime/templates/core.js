/* Core Explainer family: the base of every video. */
(function () {
  const R = FZ.register;
  const tones = { red: "red", green: "green", amber: "amber", dark: "dark", purple: "purple" };

  R({ name: "bug", family: "core", layers: ["plate", "studio"], doc: "Brand logo, top right, in a white pill. Stays until the clip ends.",
      params: { at: "appear time (default: clip start)" } }, (a, p) => {
    const b = a.B.bug || {}, L = a.LAY.bug || { right: 56, top: 26 };
    const e = a.el(`<img src="assets/brand/${b.logo}" style="height:${b.height || 40}px">`, "fz-bug hide", { right: L.right, top: L.top }, a.root, "chrome");
    if (p.at == null || p.at <= a.OFF + 0.01) a.set(e, a.OFF, { autoAlpha: 1 }); else { a.inn(e, p.at, { y: -20 }, 0.6); a.sfx("swish", p.at); }
  });

  R({ name: "header", family: "core", layers: ["plate"], doc: "Section label and title, top left (the header band).",
      params: { label: "small mono label", title: "title; *word* = emphasis", at: "", until: "" } }, (a, p) => {
    const l = a.el(a.esc(p.label || ""), "fz-label abs fz-hdr-lbl hide", {}, a.root, "chrome");
    const t = a.el(a.md(p.title || ""), "fz-h1 abs fz-hdr-t hide", {}, a.root, "title");
    a.show(l, p.at, p.until, { y: 12 }, 0.45);
    a.show(t, p.at + 0.12, p.until, { y: 22 }, 0.6);
    a.sfx("whoosh", p.at);
  });

  R({ name: "title-hero", family: "core", layers: ["plate"], doc: "Opening title over the intro shot: label, two-line title (second line in the brand gradient), optional focus chip.",
      params: { label: "", title: "two lines separated by \\n", focus: "optional chip text (markdown)", at: "", until: "", box: "default: hero slot" } }, (a, p) => {
    const bx = a.box(p, "hero"), [l1, l2] = String(p.title || "").split("\n");
    const lbl = a.el(a.esc(p.label || ""), "fz-label abs hide", { left: bx.x + 4, top: bx.y }, a.root, "chrome");
    const t = a.el(`${a.esc(l1 || "")}${l2 ? `<br/><span class="grad">${a.esc(l2)}</span>` : ""}`, "abs hide", { left: bx.x, top: bx.y + 40, font: "900 92px/1.02 var(--fz-font-display)", color: "var(--fz-text)", letterSpacing: "-.015em" }, a.root, "block");
    const g = t.querySelector(".grad"); if (g) g.style.cssText = "background:var(--fz-grad);-webkit-background-clip:text;background-clip:text;color:transparent";
    a.show(lbl, p.at - 0.15, p.until, { y: 12 }, 0.45);
    a.tl.fromTo(t, { autoAlpha: 0, clipPath: "inset(0% 100% 0% 0%)" }, { autoAlpha: 1, clipPath: "inset(0% 0% 0% 0%)", duration: 0.9, ease: "power3.out", immediateRender: false }, a.T(p.at));
    a.out(t, p.until, {}, 0.25);
    a.sfx("whoosh", p.at - 0.1);
    if (p.focus) { const c = a.el(`<div class="fz-ic red">${a.icon(p.focus_icon || "stop")}</div><span>${a.md(p.focus)}</span>`, "fz-chip hide", { left: bx.x + 4, top: bx.y + 270 }, a.root, "block"); a.pop(c, p.focus_at || p.at + 1.2); a.out(c, p.until, {}, 0.2); a.sfx("pop", p.focus_at || p.at + 1.2); }
  });

  R({ name: "name-card", family: "core", layers: ["plate", "studio"], doc: "Instructor name card. Only when the instructor introduces themself (rule E5).",
      params: { name: "as said in the audio", role: "default: brand name-card title", at: "", until: "", box: "default: namecard slot" } }, (a, p) => {
    const bx = a.box(p, "namecard");
    const e = a.el(`<div style="font:800 40px/1 var(--fz-font-display);color:#fff">${a.esc(p.name)}</div><div style="font:500 21px/1.2 var(--fz-font-body);color:var(--fz-on-dark-soft);margin-top:8px">${a.esc(p.role || (a.B.nameCard || "Instructor"))}</div>`,
      "abs hide", { left: bx.x, top: bx.y, padding: "20px 34px 20px 26px", borderRadius: 22, background: "var(--fz-text)", boxShadow: "0 20px 50px -16px rgba(13,39,76,.45)" }, a.root, "block");
    a.tl.fromTo(e, { autoAlpha: 0, clipPath: "inset(0% 100% 0% 0% round 22px)" }, { autoAlpha: 1, clipPath: "inset(0% 0% 0% 0% round 22px)", duration: 0.7, ease: "power3.out", immediateRender: false }, a.T(p.at));
    if (p.until != null) a.tl.to(e, { clipPath: "inset(0% 100% 0% 0% round 22px)", duration: 0.45, ease: "power3.in" }, a.T(p.until));
    a.sfx("swish", p.at);
  });

  R({ name: "agenda", family: "core", layers: ["plate"], doc: "Numbered list of cards, each entering when said (agenda, plan, steps).",
      params: { label: "optional label above", items: "[{text, icon, tone, at}]", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), items = p.items || [], h = p.row_h || 96, gap = p.gap || 22;
    if (p.label) { const l = a.el(a.esc(p.label), "fz-label abs hide", { left: bx.x, top: bx.y - 46 }, a.root, "chrome"); a.show(l, items[0].at - 0.1, a.until(p), { y: 12 }, 0.4); }
    const parts = items.map((it, i) => {
      const c = a.el(`<div class="fz-ic ${tones[it.tone] || ""}" style="width:64px;height:64px;font-size:34px">${a.icon(it.icon || "check")}</div>
        <div style="font:800 40px/1.1 var(--fz-font-display)">${a.md(it.text)}</div><div style="margin-left:auto;font:700 22px/1 var(--fz-font-mono);color:#9AAEC7">${String(i + 1).padStart(2, "0")}</div>`,
        "fz-card hide", { left: bx.x, top: bx.y + i * (h + gap), width: Math.min(bx.w, p.width || 820), height: h, display: "flex", alignItems: "center", gap: 24, padding: "0 30px 0 18px" }, a.root, "block");
      a.show(c, it.at, a.until(p), { x: -40 }, 0.5, "back.out(1.3)"); a.sfx("swish", it.at);
      return c;
    });
    a.group(parts, items.length ? items[0].at : p.at, a.until(p));
  });

  R({ name: "definition", family: "core", layers: ["plate"], doc: "One-sentence definition in a card; phrases underline as they are said.",
      params: { text: "the sentence (markdown)", highlights: "[{text: exact phrase in text, at}]", at: "", until: "", box: "default: main slot (top)", size: "font px (default 46)" } }, (a, p) => {
    const bx = a.box(p, "main"); let html = a.md(p.text || "");
    (p.highlights || []).forEach((h, i) => { html = html.replace(a.esc(h.text), `<span class="fz-dh" data-i="${i}" style="position:relative">${a.esc(h.text)}</span>`); });
    const c = a.el(html, "fz-card hide", { left: bx.x, top: bx.y, width: bx.w, padding: "34px 40px", font: `700 ${p.size || 46}px/1.3 var(--fz-font-display)` }, a.root, "block");
    a.show(c, p.at, a.until(p), { y: 26 }, 0.6); a.sfx("swish", p.at);
    (p.highlights || []).forEach((h, i) => {
      const s = c.querySelector(`.fz-dh[data-i="${i}"]`); if (!s) return;
      a.to(s, h.at, { color: getComputedStyle(document.documentElement).getPropertyValue("--fz-emph").trim() || "#30809F", duration: 0.3 });
      const u = a.el("", "abs hide", { left: 0, bottom: -4, width: "100%", height: 6, borderRadius: 3, background: "var(--fz-accent)", transformOrigin: "0 50%" }, s);
      a.inn(u, h.at, { scaleX: 0 }, 0.8, "power2.inOut"); a.sfx("blip", h.at);
    });
  });

  R({ name: "type-cards", family: "core", layers: ["plate"], doc: "2-4 concept cards side by side (e.g. break / continue / pass).",
      params: { cards: "[{keyword, icon, tone, text, at, emphasis_at}]", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), n = (p.cards || []).length, gap = 32, w = Math.min(400, (bx.w - gap * (n - 1)) / n);
    const parts = p.cards.map((cd, i) => {
      const c = a.el(`<div class="fz-ic ${tones[cd.tone] || ""}" style="width:84px;height:84px;font-size:46px">${a.icon(cd.icon || "sparkle")}</div>
        <div style="font:700 46px/1 var(--fz-font-mono);margin-top:22px;color:var(--fz-text)">${a.esc(cd.keyword)}</div>
        <div class="fz-body" style="margin-top:14px;font-size:29px">${a.md(cd.text || "")}</div>`,
        "fz-card hide", { left: bx.x + i * (w + gap), top: bx.y, width: w, minHeight: 360, padding: "34px 32px" }, a.root, "block");
      a.show(c, cd.at, a.until(p), { y: 40 }, 0.55, "back.out(1.4)"); a.sfx("pop", cd.at);
      if (cd.emphasis_at != null) { a.pulse(c, cd.emphasis_at, 1.06); a.sfx("tick", cd.emphasis_at); }
      return c;
    });
    a.group(parts, p.cards[0].at, a.until(p));
  });

  R({ name: "chips", family: "core", layers: ["plate", "studio"], doc: "A row of short keyword or question chips.",
      params: { items: "[{text, icon, tone, at}]", until: "", box: "default: main slot", gap: "px between chips (default 24)" } }, (a, p) => {
    const bx = a.box(p, "main"); let x = bx.x;
    const row = a.el("", "abs", { left: bx.x, top: bx.y, display: "flex", gap: p.gap || 24, flexWrap: "wrap", width: bx.w });
    const parts = (p.items || []).map((it) => {
      const c = a.el(`<div class="fz-ic ${tones[it.tone] || ""}">${a.icon(it.icon || "sparkle")}</div><span>${a.md(it.text)}</span>`, "fz-chip hide", { position: "relative" }, row, "block");
      a.pop(c, it.at); a.out(c, a.until(p)); a.sfx("pop", it.at);
      return c;
    });
    a.group(parts, (p.items || [{ at: p.at }])[0].at, a.until(p));
  });

  R({ name: "card", family: "core", layers: ["plate", "studio"], doc: "A single text card with an optional icon and label: a takeaway, a fact, a question.",
      params: { label: "", icon: "", tone: "", text: "markdown", at: "", until: "", box: "default: main slot", size: "font px (default 32)" } }, (a, p) => {
    const bx = a.box(p, "main");
    const c = a.el(`${p.label ? `<div class="fz-label" style="margin-bottom:12px">${a.esc(p.label)}</div>` : ""}<div style="display:flex;align-items:center;gap:20px">${p.icon ? `<div class="fz-ic ${tones[p.tone] || ""}">${a.icon(p.icon)}</div>` : ""}<div class="fz-body" style="font-size:${p.size || 32}px">${a.md(p.text || "")}</div></div>`,
      "fz-card hide", { left: bx.x, top: bx.y, width: p.box && p.box.w ? bx.w : "auto", maxWidth: bx.w, padding: "24px 30px" }, a.root, "block");
    a.show(c, p.at, a.until(p), { y: 26 }, 0.55, "back.out(1.3)"); a.sfx("swish", p.at);
  });

  R({ name: "summary", family: "core", layers: ["plate"], doc: "Recap rows with optional keyword chips at the end of a row.",
      params: { rows: "[{icon, tone, text, at, chips: [{text, tone, at}]}]", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main");
    const parts = (p.rows || []).map((r, i) => {
      const row = a.el(`<div class="fz-ic ${tones[r.tone] || ""}">${a.icon(r.icon || "check")}</div><div>${a.md(r.text)}</div><div class="chips" style="margin-left:auto;display:flex;gap:12px"></div>`,
        "fz-card hide fz-body", { left: bx.x, top: bx.y + i * 128, width: bx.w, height: 104, display: "flex", alignItems: "center", gap: 22, padding: "0 24px 0 22px", fontSize: 34 }, a.root, "block");
      a.show(row, r.at, a.until(p), { x: -40 }, 0.5, "back.out(1.3)"); a.sfx("swish", r.at);
      (r.chips || []).forEach((c) => { const ch = a.el(`<code style="font-size:28px;color:var(--fz-${c.tone || "emph"})">${a.esc(c.text)}</code>`, "fz-chip hide", { position: "relative", padding: "10px 18px" }, row.querySelector(".chips")); a.pop(ch, c.at); a.sfx("pop", c.at); });
      return row;
    });
    a.group(parts, (p.rows || [{ at: p.at }])[0].at, a.until(p));
  });

  R({ name: "flowchart", family: "core", layers: ["plate"], doc: "Nodes and arrows, with an optional marker that walks the path. Node coordinates are relative to the box.",
      params: { nodes: "[{id, x, y, w, h, text, kind: box|term|dec|ok, at}]", edges: "[{from, to, label, tone: hot|green|red, at, path: optional svg path in box coords}]", walk: "[{node, at}]", until: "", box: "default: main slot" } }, (a, p) => {
    const bx = a.box(p, "main"), N = {}, U = a.until(p);
    (p.nodes || []).forEach((n) => {
      const cls = n.kind === "term" ? "term" : n.kind === "dec" ? "dec" : "";
      const e = a.el(`<span>${a.md(n.text)}</span>`, `fz-node hide ${cls}`, { left: bx.x + n.x, top: bx.y + n.y, width: n.w || 280, height: n.h || 72 }, a.root, "block");
      if (n.kind === "ok") Object.assign(e.style, { background: "var(--fz-success)", color: "#fff", borderColor: "var(--fz-success)", borderRadius: "999px" });
      if (n.kind === "stop") e.style.borderColor = "#F8B4B6";
      N[n.id] = { e, x: bx.x + n.x, y: bx.y + n.y, w: n.w || 280, h: n.h || 72 };
      a.show(e, n.at, U, { scale: 0.8 }, 0.45, "back.out(1.6)"); a.sfx("pop", n.at);
    });
    a.group(Object.values(N).map((n) => n.e), Math.min(...(p.nodes || []).map((n) => n.at)), U);
    (p.edges || []).forEach((ed) => {
      const A = N[ed.from], Bn = N[ed.to]; if (!A || !Bn) return;
      let d = ed.path ? ed.path.replace(/(-?\d+(\.\d+)?)\s+(-?\d+(\.\d+)?)/g, (m, x, _, y) => `${+x + bx.x} ${+y + bx.y}`) : null;
      if (!d) {
        const ax = A.x + A.w / 2, bxc = Bn.x + Bn.w / 2;
        if (Math.abs(ax - bxc) < 2) d = Bn.y > A.y ? `M ${ax} ${A.y + A.h} L ${ax} ${Bn.y - 6}` : `M ${ax} ${A.y} L ${ax} ${Bn.y + Bn.h + 6}`;
        else d = Bn.x > A.x ? `M ${A.x + A.w} ${A.y + A.h / 2} L ${Bn.x - 6} ${Bn.y + Bn.h / 2}` : `M ${A.x} ${A.y + A.h / 2} L ${Bn.x + Bn.w + 6} ${Bn.y + Bn.h / 2}`;
      }
      const path = a.edge(d, ed.at, U, ed.tone || "");
      if (ed.label) { const pt = path.getPointAtLength(path.getTotalLength() / 2); const l = a.el(a.esc(ed.label), "fz-flab hide", { left: pt.x + 12, top: pt.y - 14 }, a.root, "text"); if (ed.tone === "green") l.style.color = "var(--fz-success)"; if (ed.tone === "red") l.style.color = "var(--fz-danger)"; a.show(l, ed.at + 0.1, U, { scale: 0.7 }, 0.3); }
    });
    if (p.walk && p.walk.length) {
      const dot = a.el("", "abs hide", { left: 0, top: 0, width: 26, height: 26, borderRadius: 13, background: "var(--fz-highlight-strong)", boxShadow: "0 0 0 8px color-mix(in srgb, var(--fz-highlight-strong) 25%, transparent)" });
      const at = (n) => ({ x: n.x - 40, y: n.y + n.h / 2 - 13 });          // the marker rides just left of the nodes
      p.walk.forEach((w, i) => { const n = N[w.node]; if (!n) return; if (i === 0) a.set(dot, w.at, Object.assign({ autoAlpha: 1 }, at(n))); else { a.to(dot, w.at, Object.assign({ duration: 0.8, ease: "power2.inOut" }, at(n))); a.sfx("swish", w.at); } });
      a.out(dot, U, {}, 0.2);
    }
  });

  R({ name: "cutaway", family: "core", layers: ["plate"], doc: "Full-frame backdrop for a short full-screen moment (rule L3: at most 12 s each, 10% of runtime). Put the scenes that belong to it after it, with box set inside the full frame.",
      params: { at: "", until: "required", tone: "light (plate image) | deep (dark brand gradient)" } }, (a, p) => {
    const deep = p.tone === "deep";
    const e = a.el(deep ? "" : `<div style="position:absolute;inset:0;background:url('assets/brand/plate.png') center/cover;opacity:.95"></div>`, "abs hide",
      { left: 0, top: 0, width: 1920, height: 1080, background: deep ? "var(--fz-deep-grad)" : "var(--fz-page)" }, a.root, "cutaway");
    a.tl.fromTo(e, { autoAlpha: 0, clipPath: "circle(0% at 50% 50%)" }, { autoAlpha: 1, clipPath: "circle(75% at 50% 50%)", duration: 0.6, ease: "power3.inOut", immediateRender: false }, a.T(p.at));
    a.tl.to(e, { clipPath: "circle(0% at 50% 50%)", duration: 0.5, ease: "power3.inOut" }, a.T(p.until - 0.5));
    a.sfx("whoosh", p.at); a.sfx("whoosh", p.until - 0.5);
  });

  R({ name: "studio-tag", family: "core", layers: ["studio"], doc: "Light graphic for the instructor's studio shots (rule L4): a keyword, the step in progress or a short takeaway, in the studio frame's free area. 12 words at most.",
      params: { label: "optional small label", text: "markdown, 12 words at most", icon: "", at: "", until: "" } }, (a, p) => {
    const bx = a.box(p, "studio");
    const c = a.el(`${p.label ? `<div class="fz-label" style="margin-bottom:10px">${a.esc(p.label)}</div>` : ""}<div style="display:flex;align-items:center;gap:18px">${p.icon ? `<div class="fz-ic">${a.icon(p.icon)}</div>` : ""}<div style="font:800 38px/1.15 var(--fz-font-display);color:var(--fz-text)">${a.md(p.text || "")}</div></div>`,
      "fz-card hide", { left: bx.x, top: bx.y, maxWidth: bx.w, padding: "22px 28px", background: "rgba(255,255,255,.92)" }, a.root, "block");
    a.show(c, p.at, a.until(p), { x: -30 }, 0.55, "back.out(1.3)"); a.sfx("swish", p.at);
  });

  R({ name: "captions", family: "core", layers: ["plate", "studio"], doc: "Subtitles. Only when the video prompt switches them on (rule E3).",
      params: { cues: "[{text, at, until}]", y: "top of the caption bar (default 960)" } }, (a, p) => {
    (p.cues || []).forEach((c) => {
      const e = a.el(a.esc(c.text), "fz-cap hide", { top: p.y || 960 }, a.root, "caption");
      a.set(e, c.at, { autoAlpha: 1 }); a.set(e, c.until, { autoAlpha: 0 });
    });
  });

  R({ name: "image", family: "core", layers: ["plate", "studio"], doc: "Place an image file from the video's assets (e.g. a screenshot or diagram).",
      params: { src: "path under assets/", at: "", until: "", box: "required", radius: "corner radius (default brand)" } }, (a, p) => {
    const bx = a.box(p, "main");
    const e = a.el(`<img src="assets/${p.src}" style="width:100%;height:100%;object-fit:contain;display:block">`, "abs hide", { left: bx.x, top: bx.y, width: bx.w, height: bx.h, borderRadius: p.radius != null ? p.radius : "var(--fz-radius)", overflow: "hidden" }, a.root, "block");
    a.show(e, p.at, a.until(p), { scale: 0.96 }, 0.55); a.sfx("swish", p.at);
  });
})();
