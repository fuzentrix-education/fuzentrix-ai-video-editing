/* Sketch / Whiteboard family: ONLY when the video's prompt asks ("sketch edit"). Whiteboard-marker look: navy and teal strokes,
   red/green for wrong/right, Caveat labels. Strokes draw themselves on with one fixed-seed wobble, so every sketch video matches.
   Code never goes in sketch style (it stays in the Code & Execution family). */
(function () {
  const R = FZ.register;
  const NS = "http://www.w3.org/2000/svg";
  const TONE = { ink: "var(--fz-text)", accent: "var(--fz-accent)", emph: "var(--fz-emph)", red: "var(--fz-danger)", green: "var(--fz-success)" };

  function roughDefs(a) {
    if (document.getElementById("fz-rough")) return;
    const s = document.createElementNS(NS, "svg"); s.setAttribute("width", "0"); s.setAttribute("height", "0"); s.style.position = "absolute";
    s.innerHTML = `<defs><filter id="fz-rough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="7"/><feDisplacementMap in="SourceGraphic" scale="3.2"/></filter></defs>`;
    a.root.appendChild(s);
  }
  // draw every stroke of an svg element in sequence (dash animation), starting at g, over dur seconds
  function drawOn(a, svgEl, g, dur) {
    const shapes = [...svgEl.querySelectorAll("path, rect, circle, ellipse, line, polyline, polygon")];
    const lens = shapes.map((s) => { try { return s.getTotalLength(); } catch (e) { return 200; } });
    const total = lens.reduce((x, y) => x + y, 0) || 1;
    let t = g;
    shapes.forEach((s, i) => {
      const L = lens[i], d = Math.max(0.08, dur * L / total);
      s.style.strokeDasharray = `${L} ${L + 20}`; s.style.strokeDashoffset = L;
      a.tl.fromTo(s, { strokeDashoffset: L }, { strokeDashoffset: 0, duration: d, ease: "power1.inOut", immediateRender: false }, a.T(t));
      t += d * 0.85;
    });
    return t;
  }
  function outline(svgText, stroke) {
    const tmp = document.createElement("div"); tmp.innerHTML = svgText;
    const svg = tmp.querySelector("svg");
    svg.querySelectorAll("path, rect, circle, ellipse, line, polyline, polygon").forEach((s) => {
      s.setAttribute("data-fill", s.getAttribute("fill") || "none");
      s.setAttribute("fill", "none"); s.setAttribute("stroke", stroke); s.setAttribute("stroke-width", "4");
      s.setAttribute("stroke-linecap", "round"); s.setAttribute("stroke-linejoin", "round"); s.setAttribute("vector-effect", "non-scaling-stroke");
    });
    svg.setAttribute("filter", "url(#fz-rough)"); svg.style.overflow = "visible";
    return svg;
  }

  R({ name: "sketch-board", family: "sketch", layers: ["plate"], doc: "A clean whiteboard panel for a sketch scene (inside the free area, or full frame inside a cutaway).",
      params: { at: "", until: "", box: "default: main slot", label: "optional handwritten title" } }, (a, p) => {
    roughDefs(a);
    const bx = a.box(p, "main");
    const b = a.el(p.label ? `<div style="position:absolute;left:34px;top:18px;font:700 44px/1 var(--fz-font-hand);color:var(--fz-text)">${a.esc(p.label)}</div>` : "", "abs hide",
      { left: bx.x, top: bx.y, width: bx.w, height: bx.h, borderRadius: 18, background: "#FFFFFF", border: "2px solid var(--fz-line)", boxShadow: "0 30px 60px -30px rgba(13,39,76,.35)" }, a.root, "deco");
    a.show(b, p.at, a.until(p), { scale: 0.97 }, 0.5); a.sfx("swish", p.at);
  });

  R({ name: "sketch-draw", family: "sketch", layers: ["plate"], doc: "Draw a library prop or character as marker outlines, stroke by stroke; optional light colour fill afterwards and a handwritten label.",
      params: { asset: "props library id", box: "x, y, w, h", at: "", dur: "drawing time (default 1.6 s)", until: "", tone: "ink | accent | emph | red | green", fill: "true to tint fills after drawing", label: "{text, at}" } }, (a, p) => {
    roughDefs(a);
    const svgText = (window.FZ_PROPS || {})[p.asset]; if (!svgText) throw new Error(`prop "${p.asset}" is not in global/props`);
    const bx = a.box(p, "main");
    const wrap = a.el("", "abs", { left: bx.x, top: bx.y, width: bx.w, height: bx.h }, a.root, "block");
    const svg = outline(svgText, TONE[p.tone] || TONE.ink); svg.style.width = "100%"; svg.style.height = "100%"; wrap.appendChild(svg);
    a.set(wrap, p.at - 0.01, { autoAlpha: 1 });
    const end = drawOn(a, svg, p.at, p.dur || 1.6); a.sfx("swish", p.at);
    if (p.fill) svg.querySelectorAll("[data-fill]").forEach((s) => { const f = s.getAttribute("data-fill"); if (f && f !== "none") { s.setAttribute("fill", f); s.style.fillOpacity = 0; a.to(s, end, { fillOpacity: 0.28, duration: 0.5 }); } });
    a.out(wrap, a.until(p));
    if (p.label) { const l = a.el(a.esc(p.label.text), "abs hide", { left: bx.x - 40, top: bx.y + bx.h + 6, width: bx.w + 80, textAlign: "center", font: "700 38px/1.1 var(--fz-font-hand)", color: "var(--fz-text)" }, a.root, "text");
      a.tl.fromTo(l, { autoAlpha: 0, clipPath: "inset(0% 100% 0% 0%)" }, { autoAlpha: 1, clipPath: "inset(0% 0% 0% 0%)", duration: 0.6, immediateRender: false }, a.T(p.label.at != null ? p.label.at : end)); a.out(l, a.until(p)); }
  });

  R({ name: "sketch-text", family: "sketch", layers: ["plate", "studio"], doc: "Handwritten text that writes itself on (left-to-right wipe).",
      params: { text: "short text", box: "x, y, w", size: "px (default 52)", tone: "ink | accent | emph | red | green", at: "", until: "", dur: "write time (default ~0.06 s per char)" } }, (a, p) => {
    const bx = a.box(p, "main");
    const e = a.el(a.esc(p.text || ""), "abs hide", { left: bx.x, top: bx.y, maxWidth: bx.w, font: `700 ${p.size || 52}px/1.15 var(--fz-font-hand)`, color: TONE[p.tone] || TONE.ink }, a.root, "text");
    a.tl.fromTo(e, { autoAlpha: 0, clipPath: "inset(0% 100% 0% 0%)" }, { autoAlpha: 1, clipPath: "inset(0% 0% 0% 0%)", duration: p.dur || Math.min(2.4, 0.06 * (p.text || "").length + 0.3), ease: "none", immediateRender: false }, a.T(p.at));
    a.out(e, a.until(p)); a.sfx("swish", p.at);
  });

  R({ name: "sketch-list", family: "sketch", layers: ["plate"], doc: "Hand-lettered list; each item writes on with a drawn tick or bullet when said.",
      params: { items: "[{text, at, mark: tick|cross|dot}]", box: "x, y, w", size: "px (default 46)", until: "" } }, (a, p) => {
    roughDefs(a);
    const bx = a.box(p, "main"), fs = p.size || 46, parts = [];
    (p.items || []).forEach((it, i) => {
      const y = bx.y + i * fs * 1.6;
      const mk = document.createElementNS(NS, "svg"); mk.setAttribute("viewBox", "0 0 40 40"); mk.setAttribute("filter", "url(#fz-rough)");
      const col = it.mark === "cross" ? TONE.red : it.mark === "dot" ? TONE.accent : TONE.green;
      mk.innerHTML = it.mark === "cross" ? `<path d="M8 8 L32 32 M32 8 L8 32" stroke="${col}" stroke-width="5" fill="none" stroke-linecap="round"/>` : it.mark === "dot" ? `<circle cx="20" cy="20" r="8" stroke="${col}" stroke-width="5" fill="none"/>` : `<path d="M6 22 L16 32 L34 8" stroke="${col}" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>`;
      const holder = a.el("", "abs", { left: bx.x, top: y + 4, width: fs * 0.9, height: fs * 0.9 }, a.root, "part"); holder.appendChild(mk);
      a.set(holder, it.at - 0.01, { autoAlpha: 1 }); drawOn(a, mk, it.at, 0.35); a.out(holder, a.until(p));
      const t = a.el(a.esc(it.text), "abs hide", { left: bx.x + fs * 1.2, top: y, width: bx.w - fs * 1.2, font: `700 ${fs}px/1.15 var(--fz-font-hand)`, color: TONE.ink }, a.root, "part");
      a.tl.fromTo(t, { autoAlpha: 0, clipPath: "inset(0% 100% 0% 0%)" }, { autoAlpha: 1, clipPath: "inset(0% 0% 0% 0%)", duration: Math.min(1.8, 0.05 * it.text.length + 0.3), ease: "none", immediateRender: false }, a.T(it.at + 0.3));
      a.out(t, a.until(p)); a.sfx("swish", it.at); parts.push(holder, t);
    });
    a.group(parts, (p.items || [{ at: p.at }])[0].at, a.until(p));
  });

  R({ name: "sketch-flow", family: "sketch", layers: ["plate"], doc: "Hand-drawn boxes and arrows (coordinates relative to the box); each part draws on when said.",
      params: { nodes: "[{id, x, y, w, h, text, at, tone}]", edges: "[{from, to, at, label, tone}]", until: "", box: "default: main slot" } }, (a, p) => {
    roughDefs(a);
    const bx = a.box(p, "main"), U = a.until(p), N = {}, parts = [];
    const svg = document.createElementNS(NS, "svg"); svg.setAttribute("width", "1920"); svg.setAttribute("height", "1080"); svg.setAttribute("filter", "url(#fz-rough)");
    svg.style.cssText = "position:absolute;left:0;top:0;overflow:visible;pointer-events:none"; a.root.appendChild(svg);
    (p.nodes || []).forEach((n) => {
      const x = bx.x + n.x, y = bx.y + n.y, w = n.w || 260, h = n.h || 110;
      const g = document.createElementNS(NS, "g"); svg.appendChild(g);
      g.innerHTML = `<path d="M${x + 6} ${y + 2} L${x + w - 4} ${y + 6} L${x + w - 2} ${y + h - 4} L${x + 4} ${y + h - 2} Z" fill="none" stroke="${TONE[n.tone] || TONE.ink}" stroke-width="4" stroke-linejoin="round"/>`;
      g.style.opacity = 0; a.set(g, n.at - 0.01, { opacity: 1 }); drawOn(a, g, n.at, 0.6); a.out(g, U, {}, 0.3);
      const t = a.el(a.esc(n.text), "abs hide", { left: x, top: y, width: w, height: h, display: "grid", placeItems: "center", textAlign: "center", font: "700 40px/1.05 var(--fz-font-hand)", color: TONE.ink }, a.root, "part");
      a.inn(t, n.at + 0.5, {}, 0.4); a.out(t, U); a.sfx("swish", n.at);
      N[n.id] = { x, y, w, h }; parts.push(t);
    });
    (p.edges || []).forEach((e) => {
      const A = N[e.from], B = N[e.to]; if (!A || !B) return;
      const ax = A.x + A.w / 2, ay = A.y + A.h / 2, bxc = B.x + B.w / 2, by = B.y + B.h / 2, horiz = Math.abs(bxc - ax) > Math.abs(by - ay);
      const x1 = horiz ? (bxc > ax ? A.x + A.w + 8 : A.x - 8) : ax, y1 = horiz ? ay : (by > ay ? A.y + A.h + 8 : A.y - 8);
      const x2 = horiz ? (bxc > ax ? B.x - 14 : B.x + B.w + 14) : bxc, y2 = horiz ? by : (by > ay ? B.y - 14 : B.y + B.h + 14);
      const ang = Math.atan2(y2 - y1, x2 - x1), hx = (t) => x2 - 18 * Math.cos(ang + t), hy = (t) => y2 - 18 * Math.sin(ang + t);
      const g = document.createElementNS(NS, "g"); svg.appendChild(g);
      const col = TONE[e.tone] || TONE.accent;
      g.innerHTML = `<path d="M${x1} ${y1} Q${(x1 + x2) / 2 + 6} ${(y1 + y2) / 2 - 8} ${x2} ${y2}" fill="none" stroke="${col}" stroke-width="4" stroke-linecap="round"/><path d="M${hx(0.5)} ${hy(0.5)} L${x2} ${y2} L${hx(-0.5)} ${hy(-0.5)}" fill="none" stroke="${col}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`;
      g.style.opacity = 0; a.set(g, e.at - 0.01, { opacity: 1 }); drawOn(a, g, e.at, 0.5); a.out(g, U, {}, 0.3);
      if (e.label) { const l = a.el(a.esc(e.label), "abs hide", { left: (x1 + x2) / 2 + 10, top: (y1 + y2) / 2 - 44, font: "700 34px/1 var(--fz-font-hand)", color: col }, a.root, "text"); a.inn(l, e.at + 0.4, {}, 0.3); a.out(l, U); }
      a.sfx("swish", e.at);
    });
    a.group(parts, Math.min(...(p.nodes || [{ at: p.at }]).map((n) => n.at)), U);
  });

  R({ name: "sketch-mark", family: "sketch", layers: ["plate"], doc: "A hand-drawn annotation over anything on screen: circle, underline, arrow, box, tick or cross.",
      params: { shape: "circle | underline | arrow | box | tick | cross", box: "x, y, w, h (for arrow: from top-left to bottom-right)", tone: "accent | red | green | ink", at: "", until: "" } }, (a, p) => {
    roughDefs(a);
    const bx = a.box(p, "main"), col = TONE[p.tone] || TONE.accent, { x, y, w, h } = bx;
    const d = { circle: `M${x + w * 0.5} ${y - 4} C${x + w * 1.08} ${y - 2} ${x + w * 1.06} ${y + h + 6} ${x + w * 0.48} ${y + h + 4} C${x - w * 0.06} ${y + h + 2} ${x - w * 0.04} ${y - 8} ${x + w * 0.56} ${y + 6}`,
                underline: `M${x} ${y + h} Q${x + w / 2} ${y + h + 10} ${x + w} ${y + h - 2}`,
                arrow: `M${x} ${y} Q${x + w * 0.6} ${y + h * 0.1} ${x + w} ${y + h} M${x + w - 26} ${y + h - 6} L${x + w} ${y + h} L${x + w - 6} ${y + h - 28}`,
                box: `M${x - 6} ${y - 4} L${x + w + 4} ${y - 8} L${x + w + 8} ${y + h + 4} L${x - 4} ${y + h + 8} Z`,
                tick: `M${x} ${y + h * 0.55} L${x + w * 0.38} ${y + h} L${x + w} ${y}`, cross: `M${x} ${y} L${x + w} ${y + h} M${x + w} ${y} L${x} ${y + h}` }[p.shape || "circle"];
    const svg = document.createElementNS(NS, "svg"); svg.setAttribute("width", "1920"); svg.setAttribute("height", "1080"); svg.setAttribute("filter", "url(#fz-rough)");
    svg.style.cssText = "position:absolute;left:0;top:0;overflow:visible;pointer-events:none";
    svg.innerHTML = `<path d="${d}" fill="none" stroke="${col}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>`;
    a.root.appendChild(svg); svg.style.opacity = 0;
    a.set(svg, p.at - 0.01, { opacity: 1 }); drawOn(a, svg, p.at, 0.5); a.out(svg, a.until(p), {}, 0.3); a.sfx("swish", p.at);
  });
})();
