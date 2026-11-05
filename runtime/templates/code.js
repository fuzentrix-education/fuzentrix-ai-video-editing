/* Code & Execution family: used for any code. Explanations always sit outside code and terminals (rule L6). */
(function () {
  const R = FZ.register;
  // tile states as kit colours [background, border, text]; resolved here because colour tweens need real values, not var()
  const STATE = { ok: ["success-soft", "success", "success"], bad: ["danger-soft", "danger", "danger"], skip: ["highlight-soft", "highlight", "highlight-text"],
                  dim: ["dim", "line", "mist"], now: ["tint", "accent", "text"],
                  focus: ["highlight-soft", "highlight", "text"], pick: ["accent", "accent", "card"], on: ["card", "line", "text"] };
  // focus: the item she is talking about gets the warm amber outline (Rani's look, 2026-11-05: "too much blue"); pick: the one chosen
  // (an index asked for, the selected date) is solid blue
  const cssv = (n, d) => getComputedStyle(document.documentElement).getPropertyValue("--fz-" + n).trim() || d;
  const tileColors = (kind) => STATE[kind] && STATE[kind].map((n) => cssv(n, "#102A56"));
  const tileState = (a, el, g, kind) => { const c = tileColors(kind);
    if (c) a.to(el, g, { backgroundColor: c[0], borderColor: c[1], color: c[2], boxShadow: kind === "focus" ? `0 0 0 3px ${c[1]}` : "0 0 0 0px rgba(0,0,0,0)", duration: 0.22 }); };

  R({ name: "code-card", family: "code", layers: ["plate"],
      doc: "Dark editor card. Lines type in spoken chunks or at a steady speed; highlights, active-line bar, Run press. Registers `id` so notes can point at its lines.",
      params: { id: "name for notes and traces", lines: "[code lines]", title: "tab title (default main.py)", lang: "python | c | cpp | java | javascript (default: from the title's extension)", recorded: "reference mode: the lines exactly as typed in the recording, when `lines` corrects them (rule E9)", logic_fix: "why a correction changes the output (goes to 'to confirm')", at: "", until: "", box: "default: main slot (left)",
                fs: "font px (default: the kit's code size, 52, fitted to the box; never below 40)", type: "[{line, at, cps} | {line, parts: [[lastCharIndex, at], ...]}] (parts: each segment on its word, 45 ms/char + 40 ms, max 0.55 s)", reveal: "[{lines: [n...], at}] show whole lines",
                highlights: "[{line, cols: [c0, c1], at, until, tone: ''|green|red}]", active: "[{line, at}]", active_off: "time", caret_off: "time", run: "time the Run button is pressed",
                focus: "[{keep: [lines], at, until}] dim the other lines" } }, (a, p) => {
    const lines = p.lines || [], bx = a.box(p, "main"), BAR = 56, TOP = BAR + 20;
    // the kit's code size (52 px), shrunk only as far as the box needs: the longest line must fit its width, all lines ~60% of its height
    const maxLen = Math.max(1, ...lines.map((l) => l.length)), hMax = p.box && p.box.h ? bx.h : bx.h * 0.62;
    const fs = p.fs || Math.max(a.TY.codeMin, Math.min(a.TY.code, Math.floor((bx.w - 140) / (0.6 * (maxLen + 2))), Math.floor((hMax - 96) / (1.55 * Math.max(1, lines.length)))));
    const lh = Math.round(fs * 1.55), chw = fs * 0.6, X0 = 34 + 2 * chw + 26;
    const w = p.box && p.box.w ? bx.w : Math.min(bx.w, Math.max(560, X0 + Math.max(...lines.map((l) => l.length)) * chw + 80));
    const h = BAR + 40 + lines.length * lh;
    const card = a.el(`<div class="bar"><div class="dot"></div><div class="dot"></div><div class="dot"></div>
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
    a.show(card, p.at, a.until(p), { y: 30 }, 0.6); a.sfx("pop", p.at);
    (p.type || []).forEach((ty) => {
      const li = ty.line - 1, cs = chars[li] || [];
      a.set(caret, (ty.at != null ? ty.at : ty.parts[0][1]) - 0.01, { autoAlpha: 1 });
      a.set(act, (ty.at != null ? ty.at : ty.parts[0][1]) - 0.01, { autoAlpha: 1, top: TOP + li * lh });
      if (ty.parts) {
        let from = 0;
        // each segment types on its word and is done quickly: 45 ms a character + 40 ms, at most 0.55 s (the kit's rule, 2026-11-05)
        ty.parts.forEach(([end, g]) => { const n = Math.max(1, Math.min(end, cs.length - 1) - from + 1), step = Math.min(0.55, 0.045 * n + 0.04) / n;
          for (let k = from; k <= end && k < cs.length; k++) { const t = g + (k - from) * step; a.set(cs[k], t, { opacity: 1 }); caretAt(li, k, t); } from = end + 1; a.sfx("type", g); });
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
      a.inn(b, hl.at, { scale: 1.15 }, 0.35, a.M.pop[1]); a.out(b, hl.until != null ? hl.until : a.until(p), {}, 0.25);
      a.sfx(hl.tone === "red" ? "bad" : "blip", hl.at);
    });
    (p.focus || []).forEach((f) => lines.forEach((_, li) => { if (!f.keep.includes(li + 1)) { a.to(chars[li], f.at, { opacity: 0.6, duration: 0.3 }); if (f.until != null) a.to(chars[li], f.until, { opacity: 1, duration: 0.3 }); } }));   // the rest stays readable
    if (p.run != null) { a.pulse(card.querySelector(".run"), p.run, 1.08); a.sfx("click", p.run); }
    a.refs[p.id || "code"] = { kind: "code", box: { x: bx.x, y: bx.y, w, h },
      cy: (line) => bx.y + TOP + (line - 1) * lh + lh / 2, cx: (c) => bx.x + X0 + c * chw,
      lineEnd: (line) => bx.x + X0 + (lines[line - 1] || "").length * chw + 14, run: () => [bx.x + w - 18, bx.y + 32] };
  });

  R({ name: "note", family: "code", layers: ["plate"],
      doc: "An explanation card outside the code, joined to its target by a wire (rule L6). Target a code line, a terminal line, a recording highlight or a point.",
      params: { nt: "optional mono pill (markdown/code)", text: "explanation (markdown, 16 words max)", at: "", until: "", box: "x, y, w (default: side slot)",
                target: "{code: id, line} | {code: id, run: true} | {term: id, line} | {rec: id, hl: name} | {point: [x, y]}", elbow_x: "ignored: the wire is routed around the other graphics automatically" } }, (a, p) => {
    const bx = a.box(p, "side");
    const n = a.el(`${p.nt ? `<div class="nt lt">${p.nt_code ? a.hlCode(p.nt) : a.md(p.nt)}</div>` : ""}<div class="nd">${a.md(p.text || "")}</div>`, "fz-card fz-note hide", { left: bx.x, top: bx.y, width: bx.w }, a.root, "note");
    a.show(n, p.at, a.until(p), { x: 30 }, 0.5, a.M.pop[1]); a.sfx("pop", p.at);
    const t = p.target; if (!t) return;
    let p0 = null;
    if (t.code && a.refs[t.code]) { const r = a.refs[t.code]; p0 = t.run ? r.run() : [r.lineEnd(t.line) + 8, r.cy(t.line)]; }   // clear of the last character
    else if (t.term && a.refs[t.term]) { const r = a.refs[t.term]; p0 = r.lineAnchor(t.line); }
    else if (t.rec && a.refs[t.rec]) { const r = a.refs[t.rec]; p0 = r.hlAnchor(t.hl); }
    else if (t.point) p0 = t.point;
    if (!p0) return;
    a.pointer(p0, n, p.at + 0.15, a.until(p) - 0.1, p.nt ? 47 : 40);       // routed once every scene is laid out
  });

  R({ name: "terminal", family: "code", layers: ["plate"], doc: "Output panel. With `exec` it runs the code card's program and prints its exact output (input echoed where it is read, errors in red), scrolling like a real terminal. Registers `id` for notes.",
      params: { id: "", title: "default Output", at: "", until: "", box: "default: bottom-left", exec: "{code: code-card id, stdin: [lines typed into the program], at, pace, times: [t per line], after_input, tone, tones: {line index: tone}, expect_error} runs the code at build time and prints its real output (rule E7)",
                input: "{text, at} shown as 'input > text' (manual mode)", lines: "[{text, input, at, tone: ok|warn|bad|dim}] (filled by exec; by hand needs `manual`)", chips: "[{text, at}] instead of lines (needs `manual`)",
                manual: "reason the output is written by hand (rule E7)", lh: "line height (default: 1.45 x the kit's terminal size)" } }, (a, p) => {
    const bx = a.box(p, "bottom"), L0 = p.lines || [];
    // the kit's terminal size, shrunk only when a line (a real error message) would not fit the panel
    const longest = Math.max(1, ...L0.map((l) => String(l.text || "").length + String(l.input || "").length), p.input ? String(p.input.text).length + 8 : 1);
    const tfs = Math.max(24, Math.min(a.TY.terminal, Math.floor((bx.w - 56) / (0.6 * longest)))), lh = p.lh || Math.round(tfs * 1.45);
    const t = a.el(`<div class="tbar"><div class="fz-label" style="color:var(--fz-on-dark-soft)">${a.esc(p.title || "Output")}</div><div style="width:10px;height:10px;border-radius:50%;background:var(--fz-dark-success)"></div></div>`,
      "fz-term hide", { left: bx.x, top: bx.y, width: bx.w, height: bx.h }, a.root, "term");
    a.show(t, p.at, a.until(p), { y: 30 }, 0.55); a.sfx("pop", p.at);
    let n = 0; const ys = [];
    const tone = { ok: "var(--fz-dark-success)", warn: "var(--fz-dark-highlight)", bad: "var(--fz-dark-danger)", dim: "rgba(225,235,255,.5)" };
    if (p.input) { const l = a.el(`<span style="color:rgba(220,231,244,.5)">input &gt;</span> <span style="color:var(--fz-warning)">${a.esc(p.input.text)}</span>`, "tl hide", { top: 66 }, t); a.inn(l, p.input.at, { x: -12 }, 0.25); a.sfx("blip", p.input.at); n = 1; ys.push(66); }
    if (p.chips) {
      const row = a.el("", "abs", { left: 26, top: 66 + n * lh + 6, display: "flex", gap: 12, flexWrap: "wrap", width: bx.w - 52 }, t);
      p.chips.forEach((c) => { const e = a.el(a.esc(c.text), "hide", { minWidth: 64, height: 64, padding: "0 14px", borderRadius: 14, background: "rgba(134,239,172,.12)", border: "2px solid rgba(134,239,172,.45)", display: "grid", placeItems: "center", font: "700 30px/1 var(--fz-font-mono)", color: c.tone ? tone[c.tone] : "var(--fz-dark-success)" }, row); a.inn(e, c.at, { scale: 0.5 }, 0.25, a.M.pop[1]); a.sfx("pop", c.at); });
    }
    const L = p.lines || [];
    if (L.length) {   // lines print one by one and scroll like a real terminal once the panel is full
      const top0 = 66 + n * lh, cap = Math.max(1, Math.floor((bx.h - top0 - 10) / lh));
      const clip = a.el("", "abs", { left: 0, top: top0 - 8, width: bx.w, height: bx.h - top0 - 2, overflow: "hidden" }, t);
      const scr = a.el("", "abs", { left: 0, top: 8, width: bx.w, height: 1 }, clip);
      let lastSfx = -9;
      L.forEach((ln, i) => {
        const inp = ln.input != null ? `<span style="color:var(--fz-warning)">${a.esc(ln.input)}</span>` : "";
        const l = a.el(a.esc(ln.text || "") + inp, "tl hide", { top: i * lh, fontSize: tfs, color: ln.tone ? tone[ln.tone] : undefined }, scr);
        a.inn(l, ln.at, { x: -12 }, 0.22, "power2.out");
        if (ln.input != null) a.sfx("blip", ln.at);
        else if ((ln.text || "").trim() && ln.at - lastSfx > 0.4) {
          a.sfx(ln.tone === "bad" ? "bad" : lastSfx < -1 ? "good" : "tick", ln.at); lastSfx = ln.at;
        }
        if (i >= cap) a.to(scr, ln.at, { y: -(i - cap + 1) * lh, duration: 0.18, ease: "power2.out" });
        ys.push(top0 + Math.min(i, cap - 1) * lh);
      });
    }
    a.refs[p.id || "term"] = { kind: "term", box: bx, lineAnchor: (i) => [bx.x + bx.w - 18, bx.y + (ys[i] != null ? ys[i] : 66) + 15] };
  });

  R({ name: "tiles", family: "code", layers: ["plate"], doc: "A row or grid of value tiles that change state (now / ok / bad / skip / dim), e.g. loop values or rounds.",
      params: { id: "", values: "[...]", label: "optional label above (markdown)", at: "", until: "", box: "x, y (default main slot)", size: "tile px (default 150)", gap: "px (default size+24)", cols: "wrap after n tiles",
                appear: "[t per tile]: each tile enters on the word that names it (rule S2; default: all at `at`)",
                states: "[{i: index | value: v, state, at}]: now | ok | bad | skip | dim | on (back to plain) | focus (amber outline; the focus moves: the last focused tile goes back), e.g. a focus each time she names a value (rule S3) | pick (solid blue: the one chosen, e.g. the index asked for)",
                note: "{text, at, until} small text under the tiles" } }, (a, p) => {
    const bx = a.box(p, "main"), sz = p.size || 150, gap = p.gap || sz + 24, cols = p.cols || 99;
    if (p.label) { const l = a.el(a.md(p.label), "abs hide", { left: bx.x, top: bx.y - 44, font: "700 26px/1 var(--fz-font-body)" }, a.root, "text"); a.show(l, p.at - 0.1, a.until(p), { y: 10 }, 0.4); }
    const fit = (v) => Math.round(Math.min(sz * 0.45, (sz * 0.84) / (0.62 * Math.max(1, String(v).length))));   // long values shrink to fit the tile
    const fsz = Math.min(...(p.values || [""]).map(fit));    // one text size for the whole row: "day", "month", "year" match
    const T = (p.values || []).map((v, i) => a.el(a.esc(v), "fz-tile hide", { left: bx.x + (i % cols) * gap, top: bx.y + Math.floor(i / cols) * gap, width: sz, height: sz, fontSize: fsz, borderRadius: Math.round(sz * 0.22) }, a.root, "block"));
    const app = p.appear || [];
    if (app.length) T.forEach((t, i) => { const g = app[i] != null ? app[i] : p.at; a.inn(t, g, { y: 20, scale: 0.8 }, 0.35, a.M.pop[1]); a.sfx(i ? "blip" : "pop", g); });
    else { a.inn(T, p.at, { y: 20, scale: 0.8 }, 0.35, a.M.pop[1], { stagger: 0.04 }); a.sfx("pop", p.at); }
    a.out(T, a.until(p), { y: -12, stagger: 0.01 });
    a.group(T, Math.min(p.at, ...app.filter((g) => g != null)), a.until(p));
    const idx = (s) => (s.i != null ? s.i : (p.values || []).findIndex((v) => String(v) === String(s.value)));
    const base = T.map(() => "on"); let cur = -1;
    [...(p.states || [])].sort((x, y) => x.at - y.at).forEach((s) => {
      const i = idx(s); if (!T[i]) return;
      if (s.state === "focus") { if (cur >= 0 && cur !== i) tileState(a, T[cur], s.at, base[cur]); tileState(a, T[i], s.at, "focus"); cur = i; a.sfx("tick", s.at); return; }
      if (cur === i) cur = -1;
      base[i] = s.state; tileState(a, T[i], s.at, s.state);
      if (s.state === "bad") a.sfx("bad", s.at); else if (s.state === "ok") a.sfx("decision", s.at);
    });
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
    a.show(panel, p.at, U, { x: 30 }, 0.5); a.sfx("pop", p.at);
    const code = p.code && a.refs[p.code], tiles = p.tiles && a.refs[p.tiles], IT = p.iterations || [];
    const ibox = panel.querySelector(".ibox"), cbox = panel.querySelector(".cbox");
    IT.forEach((it, k) => {
      const next = IT[k + 1] ? IT[k + 1].val : U, isT = !!it.result;
      const val = a.el(a.esc(it.v), "abs hide", { left: 0, top: 0, width: 140, height: 96, display: "grid", placeItems: "center", font: "800 58px/1 var(--fz-font-mono)", color: isT ? "var(--fz-danger)" : "var(--fz-success)" }, ibox);
      a.inn(val, it.val, { y: 60 }, 0.35); if (IT[k + 1]) a.out(val, next, { y: -60 }, 0.3);
      a.sfx("tick", it.val);
      if (tiles && tiles.tiles[k]) tileState(a, tiles.tiles[k], it.val, "now");
      if (it.res != null) {
        const c = a.el(`<span style="font:700 34px/1 var(--fz-font-mono)">${a.hlCode(`${it.v} ${p.cond || ""}`)}</span><span style="color:var(--fz-text2);font-size:30px">${a.icon("arrow")}</span>
          <span style="padding:6px 16px;border-radius:12px;font:800 28px/1 var(--fz-font-body);background:${isT ? "var(--fz-danger-soft)" : "var(--fz-dim)"};color:${isT ? "var(--fz-danger)" : "var(--fz-text2)"}">${isT ? "True" : "False"}</span>`,
          "abs hide", { left: 0, top: 0, display: "flex", alignItems: "center", gap: 14, whiteSpace: "nowrap" }, cbox);
        a.inn(c, it.res, { x: -16 }, 0.35); if (IT[k + 1]) a.out(c, next - 0.2, {}, 0.2);
        if (isT) a.sfx("stop", it.res);
      }
      if (isT && tiles && tiles.tiles[k]) { tileState(a, tiles.tiles[k], it.res, "bad"); tiles.tiles.slice(k + 1).forEach((tt, j) => tileState(a, tt, (it.hit || it.res) + 0.6 + j * 0.06, "dim")); }
      if (!isT && it.out != null) { if (tiles && tiles.tiles[k]) tileState(a, tiles.tiles[k], it.out, "ok"); a.sfx("pop", it.out); }
    });
  });

  R({ name: "problem", family: "code", layers: ["plate"], doc: "Problem statement card; phrases colour as they are read out.",
      params: { label: "default Problem", text: "markdown", highlights: "[{text, at, tone: emph|danger|warning|success}]", at: "", until: "", box: "default: main slot (top)", size: "font px (default 38)" } }, (a, p) => {
    const bx = a.box(p, "main"); let html = a.md(p.text || "");
    (p.highlights || []).forEach((h, i) => { html = html.replace(a.esc(h.text), `<span class="fz-ph" data-i="${i}">${a.esc(h.text)}</span>`); });
    const c = a.el(`<div class="fz-label" style="margin-bottom:12px">${a.esc(p.label || "Problem")}</div>${html}`, "fz-card hide", { left: bx.x, top: bx.y, width: bx.w, padding: "28px 36px", font: `600 ${p.size || 38}px/1.32 var(--fz-font-body)` }, a.root, "block");
    a.show(c, p.at, a.until(p), { y: 26 }, 0.6); a.sfx("pop", p.at);
    (p.highlights || []).forEach((h, i) => {
      const s = c.querySelector(`.fz-ph[data-i="${i}"]`); if (!s) return;
      if (h.tone) a.to(s, h.at, { color: `var(--fz-${h.tone})`, duration: 0.3 });
      else { s.classList.add("fz-mark"); s.style.backgroundSize = "0% .36em";      // the marker sweeps under the phrase she reads
        a.tl.fromTo(s, { backgroundSize: "0% .36em" }, { backgroundSize: "100% .36em", duration: 0.45, ease: "power2.out", immediateRender: false }, a.T(h.at)); }
      a.sfx("blip", h.at);
    });
  });

  R({ name: "variables", family: "code", layers: ["plate"], doc: "Variable boxes that update as the code runs (name = value).",
      params: { label: "card label (default Variables), e.g. Accessing values", vars: "[{name, value, at}]", updates: "[{name, value, at}]", at: "", until: "", box: "default: side slot" } }, (a, p) => {
    const bx = a.box(p, "side"), rows = {};
    const c = a.el(`<div class="fz-label">${a.esc(p.label || "Variables")}</div>`, "fz-card fz-pad hide", { left: bx.x, top: bx.y, width: bx.w }, a.root, "block");
    a.show(c, p.at, a.until(p), { x: 30 }, 0.5);
    // the value pill fits the longest value this variable ever shows (values sit absolutely inside it, so it can't grow by itself)
    const longest = {};
    [...(p.vars || []), ...(p.updates || [])].forEach((v) => { longest[v.name] = Math.max(longest[v.name] || 0, String(v.value ?? "").length); });
    (p.vars || []).forEach((v) => {
      const pw = Math.max(150, Math.ceil((longest[v.name] || 0) * 38 * 0.62) + 40);       // mono ~0.6 em per character, plus padding
      const r = a.el(`<div style="font:800 40px/1 var(--fz-font-mono);min-width:90px">${a.esc(v.name)}</div><div style="font:700 34px/1 var(--fz-font-mono);color:var(--fz-text2)">=</div><div class="val" style="position:relative;min-width:${pw}px;height:72px;border-radius:16px;background:linear-gradient(160deg,var(--fz-code-bg1),var(--fz-code-bg2));overflow:hidden"></div>`,
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
    const win = a.byId("rec-" + p.id); if (!win) throw new Error(`static markup for recording "${p.id}" missing`);
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
      a.to(e, st.at, { backgroundColor: a.cv("accent"), color: "#ffffff", duration: 0.3 }); a.to(e.querySelector(".sn"), st.at, { backgroundColor: "#ffffff", color: a.cv("accent"), duration: 0.3 });
      if (i > 0) { const prev = steps.children[i - 1]; a.to(prev, st.at, { backgroundColor: a.cv("success-soft"), color: a.cv("success"), duration: 0.3 }); a.to(prev.querySelector(".sn"), st.at, { backgroundColor: a.cv("success"), color: "#ffffff", duration: 0.3 }); }
    });
    const H = {};
    (p.highlights || []).forEach((h) => {
      const [x, y, w, hh] = h.box, e = a.el("", "fz-hl hide", { left: x, top: y, width: w, height: hh }, cam);   // cam is in recording pixels (already shifted by the crop)
      a.tl.fromTo(e, { autoAlpha: 0, scale: 1.3 }, { autoAlpha: 1, scale: 1, duration: 0.35, ease: a.M.pop[1], immediateRender: false }, a.T(h.at)); a.out(e, h.until, {}, 0.3); a.sfx("blip", h.at);
      H[h.name] = [bx.x + (x - rec.crop[0] + w / 2) * S, bx.y + 52 + (y - rec.crop[1] + hh) * S + 4];
    });
    a.refs[p.id] = { kind: "rec", box: { x: bx.x, y: bx.y, w: bx.w, h: 52 + viewH }, hlAnchor: (name) => H[name] };
  });

  R({ name: "char-scan", family: "code", layers: ["plate"],
      doc: "A string split into character cells; a pointer walks along and stamps ✓ or ✗ for a test (Python's isalpha, isdigit, isalnum, isupper, islower, isspace); the result pops as True / False.",
      params: { text: "the string", test: "alpha | digit | alnum | upper | lower | space", marks: "optional marks per character instead of a test: ✓ ✗ –",
                label: "caption above, e.g. `\"Hi5\".isalpha()`", at: "", until: "", step: "s per character (default 0.4)", times: "[time per character] (overrides step)",
                stop_on_fail: "stop at the first ✗, as Python does (default false: check every character)", result: "{at}: the True / False pill",
                indexes: "show indexes under the cells (default false)", box: "x, y (default main slot)", size: "cell px (default 84)" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p), sz = p.size || 84, gap = sz + 12, chars = [...String(p.text || "")];
    const isL = (c) => /\p{L}/u.test(c), isN = (c) => /\p{N}/u.test(c);
    const test = { alpha: (c) => isL(c), digit: (c) => /\p{Nd}/u.test(c), alnum: (c) => isL(c) || isN(c), space: (c) => /\s/.test(c),
                   upper: (c) => (c.toLowerCase() === c.toUpperCase() ? null : c === c.toUpperCase()), lower: (c) => (c.toLowerCase() === c.toUpperCase() ? null : c === c.toLowerCase()) }[p.test || "alpha"];
    const marks = chars.map((c, k) => p.marks ? ({ "✓": true, "✗": false }[[...p.marks][k]] ?? null) : test ? test(c) : null);
    const cased = p.test === "upper" || p.test === "lower";
    const value = chars.length > 0 && (cased ? marks.some((m) => m === true) && !marks.some((m) => m === false) : marks.every((m) => m !== false));
    let stopAt = chars.length; if (p.stop_on_fail) { const f = marks.findIndex((m) => m === false); if (f >= 0) stopAt = f + 1; }
    const top = bx.y + (p.label ? 60 : 0);
    if (p.label) { const l = a.el(a.hlCode(p.label), "abs hide lt", { left: bx.x, top: bx.y, font: "700 34px/1 var(--fz-font-mono)", color: "var(--fz-text)" }, a.root, "text"); a.show(l, p.at, U, { y: 10 }, 0.4); }
    const cells = chars.map((c, k) => a.el(a.esc(c === " " ? "␣" : c), "fz-tile hide", { left: bx.x + k * gap, top: top + 34, width: sz, height: sz, fontSize: Math.round(sz * 0.5),
      fontFamily: "var(--fz-font-mono)", borderRadius: Math.round(sz * 0.2), color: "var(--fz-text)" }, a.root, "block"));
    a.inn(cells, p.at, { y: 18, scale: 0.85 }, 0.35, a.M.pop[1], { stagger: 0.04 }); a.out(cells, U, { y: -10, stagger: 0.01 }); a.sfx("pop", p.at);
    if (p.indexes) chars.forEach((_, k) => { const n = a.el(String(k), "abs hide", { left: bx.x + k * gap, top: top + 34 + sz + 64, width: sz, textAlign: "center", font: "600 22px/1 var(--fz-font-mono)", color: "var(--fz-mist)" }, a.root, "part"); a.show(n, p.at + 0.2, U, { y: 6 }, 0.3); });
    const ptr = a.el(`<svg width="28" height="20" viewBox="0 0 28 20"><path d="M2 2 L26 2 L14 18 Z" style="fill:var(--fz-accent)"/></svg>`, "abs hide", { left: bx.x + sz / 2 - 14, top: top + 6 }, a.root, "part");
    const t0 = p.at + 0.6 + chars.length * 0.04, times = chars.map((_, k) => (p.times && p.times[k] != null ? p.times[k] : t0 + k * (p.step || 0.4)));
    if (chars.length) a.set(ptr, times[0] - 0.05, { autoAlpha: 1, x: 0 });
    chars.slice(0, stopAt).forEach((_, k) => {
      const g = times[k];
      if (k > 0) a.to(ptr, g - 0.15, { x: k * gap, duration: 0.15, ease: "power1.out" });
      const m = marks[k], tone = m === true ? ["success-soft", "success"] : m === false ? ["danger-soft", "danger"] : ["dim", "line"];
      a.to(cells[k], g, { backgroundColor: a.cv(tone[0]), borderColor: a.cv(tone[1]), duration: 0.2 });
      const stamp = a.el(m === true ? "✓" : m === false ? "✗" : "–", "abs hide", { left: bx.x + k * gap + sz / 2 - 18, top: top + 34 + sz + 12, width: 36, height: 36, borderRadius: 18,
        display: "grid", placeItems: "center", font: "800 22px/1 var(--fz-font-body)", color: "#fff", background: m === true ? "var(--fz-success)" : m === false ? "var(--fz-danger)" : "var(--fz-mist)" }, a.root, "part");
      a.pop(stamp, g + 0.05); a.out(stamp, U);
      a.sfx(m === false ? "bad" : "tick", g);
    });
    if (chars.length) a.out(ptr, (times[stopAt - 1] || p.at) + 0.6);
    if (p.result) {
      const rx = bx.x + Math.min(stopAt, chars.length) * gap + 24;
      const pill = a.el(value ? "True" : "False", "abs hide", { left: Math.min(rx, bx.x + chars.length * gap + 24), top: top + 34 + sz / 2 - 30, height: 60, padding: "0 24px", borderRadius: 30,
        display: "grid", placeItems: "center", font: "800 32px/1 var(--fz-font-mono)", color: "#fff", background: value ? "var(--fz-success)" : "var(--fz-danger)" }, a.root, "part");
      a.pop(pill, p.result.at); a.out(pill, U); a.sfx(value ? "good" : "bad", p.result.at);
    }
  });
})();
