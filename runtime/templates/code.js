/* Code & Execution family: used for any code. Explanations always sit outside code and terminals (rule L6). */
(function () {
  const R = FZ.register;
  const STATE = { ok: ["#E3F5EA", "#12A150", "#12A150"], bad: ["#FDECEC", "#E5484D", "#E5484D"], skip: ["#FEF3E2", "#F6AD55", "#C27803"],
                  now: ["#E6F6FA", "#1FA2BC", "#1B7F95"], dim: ["#F3F6FA", "#DCE7F4", "#C3CFDD"] };
  const tileState = (a, el, g, kind) => { const c = STATE[kind]; if (c) a.to(el, g, { backgroundColor: c[0], borderColor: c[1], color: c[2], duration: 0.22 }); };

  R({ name: "code-card", family: "code", layers: ["plate"],
      doc: "Dark editor card. Lines type in spoken chunks or at a steady speed; highlights, active-line bar, Run press. Registers `id` so notes can point at its lines.",
      params: { id: "name for notes and traces", lines: "[code lines]", title: "tab title (default main.py)", lang: "python | c | cpp | java | javascript (default: from the title's extension)", recorded: "reference mode: the lines exactly as typed in the recording, when `lines` corrects them (rule E9)", logic_fix: "why a correction changes the output (goes to 'to confirm')", at: "", until: "", box: "default: main slot (left)",
                fs: "font px (default 38)", type: "[{line, at, cps} | {line, parts: [[lastCharIndex, at], ...]}]", reveal: "[{lines: [n...], at}] show whole lines",
                highlights: "[{line, cols: [c0, c1], at, until, tone: ''|green|red}]", active: "[{line, at}]", active_off: "time", caret_off: "time", run: "time the Run button is pressed",
                focus: "[{keep: [lines], at, until}] dim the other lines" } }, (a, p) => {
    const lines = p.lines || [], fs = p.fs || 38, lh = Math.round(fs * 1.62), chw = fs * 0.6;
    const bx = a.box(p, "main"), BAR = 56, TOP = BAR + 20, X0 = 34 + 2 * chw + 26;
    const w = p.box && p.box.w ? bx.w : Math.min(bx.w, Math.max(560, X0 + Math.max(...lines.map((l) => l.length)) * chw + 80));
    const h = BAR + 40 + lines.length * lh;
    const card = a.el(`<div class="bar"><div class="dot" style="background:#FF6058"></div><div class="dot" style="background:#FFBD2E"></div><div class="dot" style="background:#28CA42"></div>
      <div class="tab">${a.esc(p.title || "main.py")}</div><div class="run">${a.icon("play")}Run</div></div>`, "fz-code hide", { left: bx.x, top: bx.y, width: w, height: h }, a.root, "code");
    const act = a.el("", "fz-act hide", { top: TOP, height: lh, width: w }, card);
    const chars = lines.map((ln, li) => {
      const row = a.el(`<span class="gut" style="left:24px;width:${2 * chw + 6}px">${li + 1}</span><span class="txt" style="left:${X0}px"></span>`, "fz-cl",
        { top: TOP + li * lh, height: lh, width: w, font: `700 ${fs}px/${lh}px var(--fz-font-mono)` }, card);
      const txt = row.querySelector(".txt"), cls = a.classify(ln);
      return [...ln].map((c, k) => { const s = document.createElement("span"); s.className = "ch " + cls[k]; s.textContent = c; txt.appendChild(s); return s; });
    });
    const caret = a.el("", "fz-caret hide", { height: Math.round(fs * 1.15), left: X0, top: TOP + (lh - fs * 1.15) / 2 }, card);
    const caretAt = (li, k, g) => a.set(caret, g, { left: X0 + (k + 1) * chw + 2, top: TOP + li * lh + (lh - fs * 1.15) / 2 });
    a.show(card, p.at, a.until(p), { y: 30 }, 0.6); a.sfx("swish", p.at);
    (p.type || []).forEach((ty) => {
      const li = ty.line - 1, cs = chars[li] || [];
      a.set(caret, (ty.at != null ? ty.at : ty.parts[0][1]) - 0.01, { autoAlpha: 1 });
      a.set(act, (ty.at != null ? ty.at : ty.parts[0][1]) - 0.01, { autoAlpha: 1, top: TOP + li * lh });
      if (ty.parts) {
        let from = 0;
        ty.parts.forEach(([end, g]) => { for (let k = from; k <= end && k < cs.length; k++) { const t = g + (k - from) / (ty.cps || 22); a.set(cs[k], t, { opacity: 1 }); caretAt(li, k, t); } from = end + 1; a.sfx("type", g); });
      } else {
        let t = ty.at; const cps = ty.cps || 16;
        cs.forEach((s, k) => { a.set(s, t, { opacity: 1 }); caretAt(li, k, t); t += lines[li][k] === " " && k < 8 ? 0.02 : 1 / cps; });
        a.sfx("type", ty.at);
      }
    });
    (p.reveal || []).forEach((r) => r.lines.forEach((ln, i) => a.tl.to(chars[ln - 1], { opacity: 1, duration: 0.25, ease: "none" }, a.T(r.at + i * 0.1))));
    if (p.caret_off != null) a.set(caret, p.caret_off, { autoAlpha: 0 });
    (p.active || []).forEach((ac) => { a.set(act, ac.at, { autoAlpha: 1 }); a.to(act, ac.at, { top: TOP + (ac.line - 1) * lh, duration: 0.3, ease: "power2.out" }); });
    if (p.active_off != null) a.out(act, p.active_off, {}, 0.2);
    (p.highlights || []).forEach((hl) => {
      const [c0, c1] = hl.cols || [0, (lines[hl.line - 1] || "").length - 1];
      const b = a.el("", "fz-chl hide " + (hl.tone || ""), { left: X0 + c0 * chw - 6, top: TOP + (hl.line - 1) * lh + 6, width: (c1 - c0 + 1) * chw + 12, height: lh - 12 }, card);
      a.inn(b, hl.at, { scale: 1.15 }, 0.35, "back.out(2)"); a.out(b, hl.until != null ? hl.until : a.until(p), {}, 0.25);
      a.sfx(hl.tone === "red" ? "bad" : "blip", hl.at);
    });
    (p.focus || []).forEach((f) => lines.forEach((_, li) => { if (!f.keep.includes(li + 1)) { a.to(chars[li], f.at, { opacity: 0.28, duration: 0.3 }); if (f.until != null) a.to(chars[li], f.until, { opacity: 1, duration: 0.3 }); } }));
    if (p.run != null) { a.pulse(card.querySelector(".run"), p.run, 1.08); a.sfx("click", p.run); }
    a.refs[p.id || "code"] = { kind: "code", box: { x: bx.x, y: bx.y, w, h },
      cy: (line) => bx.y + TOP + (line - 1) * lh + lh / 2, cx: (c) => bx.x + X0 + c * chw,
      lineEnd: (line) => bx.x + X0 + (lines[line - 1] || "").length * chw + 14, run: () => [bx.x + w - 18, bx.y + 32] };
  });

  R({ name: "note", family: "code", layers: ["plate"],
      doc: "An explanation card outside the code, joined to its target by a wire (rule L6). Target a code line, a terminal line, a recording highlight or a point.",
      params: { nt: "optional mono pill (markdown/code)", text: "explanation (markdown, 16 words max)", at: "", until: "", box: "x, y, w (default: side slot)",
                target: "{code: id, line} | {code: id, run: true} | {term: id, line} | {rec: id, hl: name} | {point: [x, y]}", elbow_x: "optional x for the wire's bend" } }, (a, p) => {
    const bx = a.box(p, "side");
    const n = a.el(`${p.nt ? `<div class="nt lt">${p.nt_code ? a.hlCode(p.nt) : a.md(p.nt)}</div>` : ""}<div class="nd">${a.md(p.text || "")}</div>`, "fz-card fz-note hide", { left: bx.x, top: bx.y, width: bx.w }, a.root, "note");
    a.show(n, p.at, a.until(p), { x: 30 }, 0.5, "back.out(1.3)"); a.sfx("swish", p.at);
    const t = p.target; if (!t) return;
    let p0 = null;
    if (t.code && a.refs[t.code]) { const r = a.refs[t.code]; p0 = t.run ? r.run() : [r.lineEnd(t.line), r.cy(t.line)]; }
    else if (t.term && a.refs[t.term]) { const r = a.refs[t.term]; p0 = r.lineAnchor(t.line); }
    else if (t.rec && a.refs[t.rec]) { const r = a.refs[t.rec]; p0 = r.hlAnchor(t.hl); }
    else if (t.point) p0 = t.point;
    if (!p0) return;
    const nb = { x: bx.x, y: bx.y, w: bx.w, h: n.getBoundingClientRect().height, ay: p.nt ? 47 : 40 };
    if (t.rec) { const below = bx.y > p0[1]; a.wire(below ? [p0, [p0[0], bx.y]] : a.route(p0, nb, p.elbow_x), p.at + 0.15, a.until(p) - 0.1); }
    else a.wire(a.route(p0, nb, p.elbow_x), p.at + 0.15, a.until(p) - 0.1);
  });

  R({ name: "terminal", family: "code", layers: ["plate"], doc: "Output panel. With `exec` it runs the code card's program and prints its exact output (input echoed where it is read, errors in red), scrolling like a real terminal. Registers `id` for notes.",
      params: { id: "", title: "default Output", at: "", until: "", box: "default: bottom-left", exec: "{code: code-card id, stdin: [lines typed into the program], at, pace, times: [t per line], after_input, tone, tones: {line index: tone}, expect_error} runs the code at build time and prints its real output (rule E7)",
                input: "{text, at} shown as 'input > text' (manual mode)", lines: "[{text, input, at, tone: ok|warn|bad|dim}] (filled by exec; by hand needs `manual`)", chips: "[{text, at}] instead of lines (needs `manual`)",
                manual: "reason the output is written by hand (rule E7)", lh: "line height (default 44)" } }, (a, p) => {
    const bx = a.box(p, "bottom"), lh = p.lh || 44;
    const t = a.el(`<div class="tbar"><div class="fz-label" style="color:var(--fz-on-dark-soft)">${a.esc(p.title || "Output")}</div><div style="width:10px;height:10px;border-radius:50%;background:#28CA42"></div></div>`,
      "fz-term hide", { left: bx.x, top: bx.y, width: bx.w, height: bx.h }, a.root, "term");
    a.show(t, p.at, a.until(p), { y: 30 }, 0.55); a.sfx("swish", p.at);
    let n = 0; const ys = [];
    const tone = { ok: "#6EE7B7", warn: "#FBBF24", bad: "#F87171", dim: "rgba(220,231,244,.5)" };
    if (p.input) { const l = a.el(`<span style="color:rgba(220,231,244,.5)">input &gt;</span> <span style="color:var(--fz-warning)">${a.esc(p.input.text)}</span>`, "tl hide", { top: 66 }, t); a.inn(l, p.input.at, { x: -12 }, 0.25); a.sfx("blip", p.input.at); n = 1; ys.push(66); }
    if (p.chips) {
      const row = a.el("", "abs", { left: 26, top: 66 + n * lh + 6, display: "flex", gap: 12, flexWrap: "wrap", width: bx.w - 52 }, t);
      p.chips.forEach((c) => { const e = a.el(a.esc(c.text), "hide", { minWidth: 64, height: 64, padding: "0 14px", borderRadius: 14, background: "rgba(110,231,183,.12)", border: "2px solid rgba(110,231,183,.45)", display: "grid", placeItems: "center", font: "700 30px/1 var(--fz-font-mono)", color: c.tone ? tone[c.tone] : "var(--fz-num)" }, row); a.inn(e, c.at, { scale: 0.5 }, 0.25, "back.out(2)"); a.sfx("pop", c.at); });
    }
    const L = p.lines || [];
    if (L.length) {   // lines print one by one and scroll like a real terminal once the panel is full
      const top0 = 66 + n * lh, cap = Math.max(1, Math.floor((bx.h - top0 - 10) / lh));
      const clip = a.el("", "abs", { left: 0, top: top0 - 8, width: bx.w, height: bx.h - top0 - 2, overflow: "hidden" }, t);
      const scr = a.el("", "abs", { left: 0, top: 8, width: bx.w, height: 1 }, clip);
      let lastSfx = -9;
      L.forEach((ln, i) => {
        const inp = ln.input != null ? `<span style="color:var(--fz-warning)">${a.esc(ln.input)}</span>` : "";
        const l = a.el(a.esc(ln.text || "") + inp, "tl hide", { top: i * lh, color: ln.tone ? tone[ln.tone] : undefined }, scr);
        a.inn(l, ln.at, { x: -12 }, 0.22, "power2.out");
        if (ln.input != null) a.sfx("blip", ln.at);
        else if ((ln.text || "").trim() && ln.at - lastSfx > 0.25) { a.sfx("pop", ln.at); lastSfx = ln.at; }
        if (i >= cap) a.to(scr, ln.at, { y: -(i - cap + 1) * lh, duration: 0.18, ease: "power2.out" });
        ys.push(top0 + Math.min(i, cap - 1) * lh);
      });
    }
    a.refs[p.id || "term"] = { kind: "term", box: bx, lineAnchor: (i) => [bx.x + bx.w - 18, bx.y + (ys[i] != null ? ys[i] : 66) + 15] };
  });

  R({ name: "tiles", family: "code", layers: ["plate"], doc: "A row or grid of value tiles that change state (now / ok / bad / skip / dim), e.g. loop values or rounds.",
      params: { id: "", values: "[...]", label: "optional label above (markdown)", at: "", until: "", box: "x, y (default main slot)", size: "tile px (default 100)", gap: "px (default size+16)", cols: "wrap after n tiles",
                states: "[{i: index | value: v, state, at}]", note: "{text, at, until} small text under the tiles" } }, (a, p) => {
    const bx = a.box(p, "main"), sz = p.size || 100, gap = p.gap || sz + 16, cols = p.cols || 99;
    if (p.label) { const l = a.el(a.md(p.label), "abs hide", { left: bx.x, top: bx.y - 44, font: "700 26px/1 var(--fz-font-display)" }, a.root, "text"); a.show(l, p.at - 0.1, a.until(p), { y: 10 }, 0.4); }
    const fit = (v) => Math.round(Math.min(sz * 0.45, (sz * 0.84) / (0.62 * Math.max(1, String(v).length))));   // long values shrink to fit the tile
    const T = (p.values || []).map((v, i) => a.el(a.esc(v), "fz-tile hide", { left: bx.x + (i % cols) * gap, top: bx.y + Math.floor(i / cols) * gap, width: sz, height: sz, fontSize: fit(v), borderRadius: Math.round(sz * 0.22) }, a.root, "block"));
    a.inn(T, p.at, { y: 20, scale: 0.8 }, 0.35, "back.out(1.6)", { stagger: 0.04 }); a.out(T, a.until(p), { y: -12, stagger: 0.01 }); a.sfx("swish", p.at);
    a.group(T, p.at, a.until(p));
    (p.states || []).forEach((s) => { const i = s.i != null ? s.i : (p.values || []).findIndex((v) => String(v) === String(s.value)); if (T[i]) { tileState(a, T[i], s.at, s.state); if (s.state === "bad") a.sfx("bad", s.at); } });
    if (p.note) { const rows = Math.ceil(T.length / cols); const n = a.el(a.md(p.note.text), "fz-small abs hide", { left: bx.x, top: bx.y + rows * gap + 10 }, a.root, "text"); a.show(n, p.note.at, p.note.until != null ? p.note.until : a.until(p), { y: 10 }, 0.35); }
    a.refs[p.id || "tiles"] = { kind: "tiles", tiles: T };
  });

  R({ name: "trace", family: "code", layers: ["plate"],
      doc: "Loop trace panel: the variable box, the condition check with its True/False result, per iteration. Optionally drives a code card's highlights, a tiles row and a terminal.",
      params: { var: "variable name (default i)", cond: "condition text after the value, e.g. '== 6'", at: "", until: "", box: "default: side slot",
                iterations: "[{v, val: time value appears, chk: time check starts, res: time result shows, result: true|false, pr: time print runs, out: time output appears, out_text}]",
                code: "code-card id (optional)", check_line: "line of the if", print_line: "line of the print", hit_line: "line that runs when true (e.g. break)",
                tiles: "tiles id (optional)", term: "terminal id (optional; prints out_text)" } }, (a, p) => {
    const bx = a.box(p, "side"), U = a.until(p), v = p.var || "i";
    const panel = a.el(`<div class="fz-label">Iteration</div>
      <div style="display:flex;align-items:center;gap:22px;margin-top:20px"><div style="font:800 64px/1 var(--fz-font-mono);color:var(--fz-text)">${a.esc(v)}</div><div style="font:700 48px/1 var(--fz-font-mono);color:var(--fz-text2)">=</div>
      <div class="ibox" style="position:relative;width:140px;height:96px;border-radius:20px;background:linear-gradient(160deg,var(--fz-code-bg1),var(--fz-code-bg2));overflow:hidden"></div></div>
      <div class="cbox lt" style="position:relative;height:60px;margin-top:22px"></div>`, "fz-card fz-pad hide", { left: bx.x, top: bx.y, width: bx.w, height: 290 }, a.root, "block");
    a.show(panel, p.at, U, { x: 30 }, 0.5); a.sfx("swish", p.at);
    const code = p.code && a.refs[p.code], tiles = p.tiles && a.refs[p.tiles], IT = p.iterations || [];
    const ibox = panel.querySelector(".ibox"), cbox = panel.querySelector(".cbox");
    IT.forEach((it, k) => {
      const next = IT[k + 1] ? IT[k + 1].val : U, isT = !!it.result;
      const val = a.el(a.esc(it.v), "abs hide", { left: 0, top: 0, width: 140, height: 96, display: "grid", placeItems: "center", font: "800 58px/1 var(--fz-font-mono)", color: isT ? "#F87171" : "#6EE7B7" }, ibox);
      a.inn(val, it.val, { y: 60 }, 0.35); if (IT[k + 1]) a.out(val, next, { y: -60 }, 0.3);
      a.sfx("tick", it.val);
      if (tiles && tiles.tiles[k]) tileState(a, tiles.tiles[k], it.val, "now");
      if (it.res != null) {
        const c = a.el(`<span style="font:700 34px/1 var(--fz-font-mono)">${a.hlCode(`${it.v} ${p.cond || ""}`)}</span><span style="color:var(--fz-text2);font-size:30px">${a.icon("arrow")}</span>
          <span style="padding:6px 16px;border-radius:12px;font:800 28px/1 var(--fz-font-display);background:${isT ? "#FDECEC" : "#F1F5FA"};color:${isT ? "var(--fz-danger)" : "var(--fz-text2)"}">${isT ? "True" : "False"}</span>`,
          "abs hide", { left: 0, top: 0, display: "flex", alignItems: "center", gap: 14, whiteSpace: "nowrap" }, cbox);
        a.inn(c, it.res, { x: -16 }, 0.35); if (IT[k + 1]) a.out(c, next - 0.2, {}, 0.2);
        a.sfx(isT ? "bad" : "pop", it.res);
      }
      if (isT && tiles && tiles.tiles[k]) { tileState(a, tiles.tiles[k], it.res, "bad"); tiles.tiles.slice(k + 1).forEach((tt, j) => tileState(a, tt, (it.hit || it.res) + 0.6 + j * 0.06, "dim")); }
      if (!isT && it.out != null) { if (tiles && tiles.tiles[k]) tileState(a, tiles.tiles[k], it.out, "ok"); a.sfx("pop", it.out); }
    });
  });

  R({ name: "problem", family: "code", layers: ["plate"], doc: "Problem statement card; phrases colour as they are read out.",
      params: { label: "default Problem", text: "markdown", highlights: "[{text, at, tone: emph|danger|warning|success}]", at: "", until: "", box: "default: main slot (top)", size: "font px (default 38)" } }, (a, p) => {
    const bx = a.box(p, "main"); let html = a.md(p.text || "");
    (p.highlights || []).forEach((h, i) => { html = html.replace(a.esc(h.text), `<span class="fz-ph" data-i="${i}">${a.esc(h.text)}</span>`); });
    const c = a.el(`<div class="fz-label" style="margin-bottom:12px">${a.esc(p.label || "Problem")}</div>${html}`, "fz-card hide", { left: bx.x, top: bx.y, width: bx.w, padding: "28px 36px", font: `700 ${p.size || 38}px/1.32 var(--fz-font-display)` }, a.root, "block");
    a.show(c, p.at, a.until(p), { y: 26 }, 0.6); a.sfx("swish", p.at);
    (p.highlights || []).forEach((h, i) => { const s = c.querySelector(`.fz-ph[data-i="${i}"]`); if (s) { a.to(s, h.at, { color: `var(--fz-${h.tone || "emph"})`, duration: 0.3 }); a.sfx("blip", h.at); } });
  });

  R({ name: "variables", family: "code", layers: ["plate"], doc: "Variable boxes that update as the code runs (name = value).",
      params: { vars: "[{name, value, at}]", updates: "[{name, value, at}]", at: "", until: "", box: "default: side slot" } }, (a, p) => {
    const bx = a.box(p, "side"), rows = {};
    const c = a.el(`<div class="fz-label">Variables</div>`, "fz-card fz-pad hide", { left: bx.x, top: bx.y, width: bx.w }, a.root, "block");
    a.show(c, p.at, a.until(p), { x: 30 }, 0.5);
    (p.vars || []).forEach((v) => {
      const r = a.el(`<div style="font:800 40px/1 var(--fz-font-mono);min-width:90px">${a.esc(v.name)}</div><div style="font:700 34px/1 var(--fz-font-mono);color:var(--fz-text2)">=</div><div class="val" style="position:relative;min-width:150px;height:72px;border-radius:16px;background:linear-gradient(160deg,var(--fz-code-bg1),var(--fz-code-bg2));overflow:hidden"></div>`,
        "hide", { display: "flex", alignItems: "center", gap: 18, marginTop: 18 }, c);
      a.inn(r, v.at, { x: 16 }, 0.35); rows[v.name] = { box: r.querySelector(".val"), cur: null };
    });
    const put = (name, value, g) => {
      const rw = rows[name]; if (!rw) return;
      const e = a.el(a.esc(value), "abs hide", { left: 0, top: 0, width: "100%", height: 72, display: "grid", placeItems: "center", font: "800 38px/1 var(--fz-font-mono)", color: "var(--fz-num)", padding: "0 14px" }, rw.box);
      a.inn(e, g, { y: 40 }, 0.3); if (rw.cur) a.out(rw.cur, g, { y: -40 }, 0.25); rw.cur = e; a.sfx("tick", g);
    };
    (p.vars || []).forEach((v) => { if (v.value != null) put(v.name, v.value, v.at + 0.2); });
    (p.updates || []).forEach((u) => put(u.name, u.value, u.at));
  });

  R({ name: "recording-window", family: "code", layers: ["plate"], static: true,
      doc: "The whole screen recording in a branded window, never cropped or zoomed (rule L7); step tracker in the title bar; highlight boxes in recording coordinates. Registers `id` for notes. Needs a recording listed in the spec's recordings.",
      params: { id: "recording id (from recordings)", title: "window title", at: "", until: "", box: "x, y, w[, h] (fits inside; aspect kept)", steps: "[{label, at}]",
                highlights: "[{name, box: [x, y, w, h] in recording pixels, at, until}]", hide: "[{at, until}] periods to hide the window (e.g. concept scenes)" } }, (a, p) => {
    const rec = (window.FZ_RECORDINGS || {})[p.id]; if (!rec) throw new Error(`recording "${p.id}" not listed`);
    const win = document.getElementById("rec-" + p.id); if (!win) throw new Error(`static markup for recording "${p.id}" missing`);
    const bx = a.box(p, "recording"), S = Math.min(bx.w / rec.w, bx.h ? (bx.h - 52) / rec.h : Infinity), viewH = Math.round(rec.h * S);
    bx.w = Math.round(rec.w * S);   // whole recording, scaled to fit the slot's width and height
    Object.assign(win.style, a.px({ left: bx.x, top: bx.y, width: bx.w, height: 52 + viewH }));
    Object.assign(win.querySelector(".view").style, a.px({ width: bx.w, height: viewH }));
    win.setAttribute("data-fz", "block");
    const cam = win.querySelector(".cam"); gsap.set(cam, { scale: S, x: -rec.crop[0] * S, y: -rec.crop[1] * S });
    win.querySelector(".ttl").textContent = p.title || "Code Playground";
    const shows = [[p.at, a.until(p)]]; (p.hide || []).forEach((h) => { const last = shows[shows.length - 1]; shows.splice(shows.length - 1, 1, [last[0], h.at], [h.until, last[1]]); });
    shows.forEach(([s, e]) => { a.inn(win, s + 0.15, { scale: 0.96, y: 30 }, 0.7); a.out(win, e, { scale: 0.97 }, 0.35); a.sfx("whoosh", s); });
    const steps = win.querySelector(".fz-steps");
    (p.steps || []).forEach((st, i) => {
      const e = a.el(`<div class="sn">${i + 1}</div>${a.esc(st.label)}`, "fz-st", {}, steps);
      a.to(e, st.at, { backgroundColor: "#1FA2BC", color: "#ffffff", duration: 0.3 }); a.to(e.querySelector(".sn"), st.at, { backgroundColor: "#ffffff", color: "#1FA2BC", duration: 0.3 });
      if (i > 0) { const prev = steps.children[i - 1]; a.to(prev, st.at, { backgroundColor: "#E3F5EA", color: "#12A150", duration: 0.3 }); a.to(prev.querySelector(".sn"), st.at, { backgroundColor: "#12A150", color: "#ffffff", duration: 0.3 }); }
    });
    const H = {};
    (p.highlights || []).forEach((h) => {
      const [x, y, w, hh] = h.box, e = a.el("", "fz-hl hide", { left: x, top: y, width: w, height: hh }, cam);   // cam is in recording pixels (already shifted by the crop)
      a.tl.fromTo(e, { autoAlpha: 0, scale: 1.3 }, { autoAlpha: 1, scale: 1, duration: 0.35, ease: "back.out(2)", immediateRender: false }, a.T(h.at)); a.out(e, h.until, {}, 0.3); a.sfx("blip", h.at);
      H[h.name] = [bx.x + (x - rec.crop[0] + w / 2) * S, bx.y + 52 + (y - rec.crop[1] + hh) * S + 4];
    });
    a.refs[p.id] = { kind: "rec", box: { x: bx.x, y: bx.y, w: bx.w, h: 52 + viewH }, hlAnchor: (name) => H[name] };
  });
})();
