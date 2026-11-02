/* fzv runtime core: loaded by every composition, before the templates.
 *
 * - Every time in a spec is a GLOBAL second of the raw cut. api.T(g) converts it to the clip's local time.
 * - Templates register with FZ.register(meta, fn) and are run in spec order by api.run(scenes).
 * - Elements carry data-fz roles ("block", "code", "term", "note", "text", "chrome") so `fzv validate`
 *   can check the safe zone, the clutter budget and the "never empty" rule from DOM boxes.
 * - sfx(kind, t) only records cues (window.__fz_sfx); `fzv finish` turns them into sound.
 * - GSAP writes into vars objects, so presets are always copied before use.
 */
(function () {
  const FZ = (window.FZ = window.FZ || {});
  FZ.templates = FZ.templates || {};
  FZ.meta = FZ.meta || {};
  FZ.register = (meta, fn) => { FZ.templates[meta.name] = fn; FZ.meta[meta.name] = meta; };
  window.__fz_sfx = window.__fz_sfx || [];
  window.__fz_errors = window.__fz_errors || [];

  FZ.create = function (cfg) {
    gsap.defaults({ lazy: false });                       // jump-seeks need correct start values
    const tl = gsap.timeline({ paused: true });
    // the clip's own root: `cfg.root` (a selector) when the clip is mounted with others (the Studio preview), else the page's #root
    const root = (cfg.root && document.querySelector(cfg.root)) || document.getElementById("root");
    const OFF = cfg.offset, END = cfg.offset + cfg.duration;
    const B = cfg.brand || {}, LAY = cfg.layout || {};
    const M = Object.assign({ enter: [0.55, "power3.out"], exit: [0.35, "power2.in"], pop: [0.5, "back.out(1.8)"], stagger: 0.04, wire: 0.45 }, B.motion || {});
    const T = (g) => Math.max(0, +(g - OFF).toFixed(3));
    const $ = (s) => (typeof s === "string" ? root.querySelector(s) || document.querySelector(s) : s);
    const byId = (id) => root.querySelector("#" + CSS.escape(id)) || document.getElementById(id);   // this clip's element first
    const NS = "http://www.w3.org/2000/svg";
    const REST = { x: 0, y: 0, scale: 1, rotation: 0, xPercent: 0, yPercent: 0, scaleX: 1, scaleY: 1 };
    const UNITLESS = ["opacity", "zIndex", "fontWeight", "lineHeight", "flex", "flexGrow", "flexShrink", "order", "scale"];
    let uid = 0;

    // ---------- timeline helpers ----------
    function inn(sel, g, from = {}, d = M.enter[0], ease = M.enter[1], to = {}) {
      const tt = { autoAlpha: 1, duration: d, ease, immediateRender: false };
      for (const k in from) if (k in REST) tt[k] = REST[k];
      tl.fromTo(sel, Object.assign({ autoAlpha: 0 }, from), Object.assign(tt, to), T(g));
    }
    const out = (sel, g, to = {}, d = M.exit[0], ease = M.exit[1]) => { if (g == null) return; tl.to(sel, Object.assign({ autoAlpha: 0, duration: d, ease }, to), T(g)); };
    const pop = (sel, g, to = {}) => inn(sel, g, { scale: 0.6, y: 18 }, M.pop[0], M.pop[1], to);
    const set = (sel, g, vars) => tl.set(sel, Object.assign({}, vars), T(g));
    const to = (sel, g, vars) => tl.to(sel, Object.assign({}, vars), T(g));
    const show = (sel, g0, g1, from = { y: 24 }, d, ease) => {
      inn(sel, g0, from, d, ease);
      if (g1 != null) out(sel, g1, from.x ? { x: from.x / 2 } : { y: -14 });
    };
    const pulse = (sel, g, s = 1.08) => tl.fromTo(sel, { scale: 1 }, { keyframes: [{ scale: s }, { scale: 1 }], duration: 0.45, immediateRender: false }, T(g));
    const sfx = (kind, g) => { if (g != null) window.__fz_sfx.push([kind, +(+g).toFixed(3)]); };

    // ---------- DOM ----------
    const px = (o) => { const s = {}; for (const k in o) s[k] = typeof o[k] === "number" && !UNITLESS.includes(k) ? o[k] + "px" : o[k]; return s; };
    function el(html, cls = "", style = {}, parent = root, role = null) {
      const e = document.createElement("div");
      if (cls) e.className = cls;
      e.innerHTML = html;
      Object.assign(e.style, px(style));
      if (role) e.setAttribute("data-fz", role);
      $(parent).appendChild(e);
      e.id = e.id || "fz" + ++uid;
      return e;
    }
    const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    // *word* → emphasis span, **word** → strong; everything else escaped
    const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\*(.+?)\*/g, "<em>$1</em>").replace(/`(.+?)`/g, "<code>$1</code>");
    const icon = (name) => `<svg class="i"><use href="#i-${name}"/></svg>`;
    // a kit colour by name (`--fz-<name>`), resolved for GSAP tweens, which can't animate to var(...)
    const cv = (name, fallback) => getComputedStyle(root || document.documentElement).getPropertyValue("--fz-" + name).trim() || fallback || "#102A56";

    // ---------- layout ----------
    // slot: main | side | bottom | full | studio | header; a spec may pass an explicit box {x, y, w, h}
    const box = (p, slot) => Object.assign({}, LAY[slot] || LAY.main || { x: 96, y: 210, w: 1220, h: 790 }, p.box || {});

    // ---------- python syntax colouring ----------
    const KW = ["for", "in", "if", "elif", "else", "while", "break", "continue", "pass", "def", "return", "and", "or", "not", "True", "False", "None", "is", "import", "from", "class", "try", "except", "finally", "with", "as", "lambda", "yield", "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE", "CREATE", "TABLE", "JOIN", "ON", "GROUP", "BY", "ORDER", "AND", "OR", "NOT", "NULL", "PRIMARY", "KEY"];
    // the LMS code editor's rules: these builtins colour as keywords; any other name followed by "(" is a call; Capitalised names are types
    const KW_BUILTIN = ["print", "len", "range", "str", "int", "dict", "list", "set"];
    const SQL_LINE = /\b(SELECT|INSERT|UPDATE|DELETE|CREATE|FROM|WHERE)\b/;
    function classify(txt) {
      const cls = new Array(txt.length).fill("");
      let ci = -1, q = null;
      for (let i = 0; i < txt.length; i++) { const c = txt[i]; if (q) { if (c === q) q = null; } else if (c === "'" || c === '"') q = c; else if (c === "#" || (c === "-" && txt[i + 1] === "-")) { ci = i; break; } }
      const re = /'[^']*'?|"[^"]*"?|[A-Za-z_][A-Za-z_0-9]*|\d+(\.\d+)?|./g; let m;
      while ((m = re.exec(txt))) {
        if (ci >= 0 && m.index >= ci) break;
        const w = m[0];
        const name = /^[A-Za-z_]/.test(w), call = name && /^\s*\(/.test(txt.slice(m.index + w.length));
        const c = /^['"]/.test(w) ? "str" : KW.includes(w) || KW_BUILTIN.includes(w) ? "kw" : /^\d/.test(w) ? "num"
          : name ? (call ? "fn" : /^[A-Z]/.test(w) && !SQL_LINE.test(txt) ? "ty" : "") : w === " " ? "" : "op";
        for (let k = 0; k < w.length; k++) cls[m.index + k] = c;
      }
      if (ci >= 0) for (let k = ci; k < txt.length; k++) cls[k] = "cm";
      return cls;
    }
    function hlCode(txt) {
      const cls = classify(txt); let h = "", cur = null, buf = "";
      const flush = () => { if (buf) h += cur ? `<span class="${cur}">${esc(buf)}</span>` : esc(buf); buf = ""; };
      [...txt].forEach((c, i) => { if (cls[i] !== cur) { flush(); cur = cls[i]; } buf += c; });
      flush(); return h;
    }

    // ---------- pointer wires (explanations outside code) ----------
    let wires = null;
    function wire(pts, g0, g1) {
      if (!wires) { wires = document.createElementNS(NS, "svg"); wires.setAttribute("class", "fz-wires"); wires.setAttribute("width", "1920"); wires.setAttribute("height", "1080"); root.appendChild(wires); }
      const gEl = document.createElementNS(NS, "g"); gEl.style.opacity = "0"; gEl.style.visibility = "hidden";
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", "M " + pts.map((q) => q.map((v) => +v.toFixed(1)).join(" ")).join(" L "));
      let len = 0; for (let k = 1; k < pts.length; k++) len += Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]);
      p.style.strokeDasharray = len + " " + (len + 20); p.style.strokeDashoffset = len;
      gEl.appendChild(p);
      const dot = (q, r) => { const c = document.createElementNS(NS, "circle"); c.setAttribute("cx", q[0]); c.setAttribute("cy", q[1]); c.setAttribute("r", r); gEl.appendChild(c); return c; };
      dot(pts[0], 6); const end = dot(pts[pts.length - 1], 5); end.style.opacity = "0";
      wires.appendChild(gEl);
      set(gEl, g0, { autoAlpha: 1 });
      tl.fromTo(p, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: M.wire, ease: "power2.inOut", immediateRender: false }, T(g0));
      tl.fromTo(end, { opacity: 0 }, { opacity: 1, duration: 0.12, immediateRender: false }, T(g0 + M.wire - 0.05));
      out(gEl, g1, {}, 0.25);
      return gEl;
    }
    // straight or elbow route from a point to a box edge
    function route(p0, boxR, elbowX) {
      if (p0[0] >= boxR.x + 20 && p0[0] <= boxR.x + boxR.w - 20 && boxR.y > p0[1] + 10) return [p0, [p0[0], boxR.y]];   // note right below: drop straight
      if (p0[0] >= boxR.x + 20 && p0[0] <= boxR.x + boxR.w - 20 && boxR.y + (boxR.h || 120) < p0[1] - 10) return [p0, [p0[0], boxR.y + (boxR.h || 120)]];
      const ay = boxR.y + (boxR.ay != null ? boxR.ay : 47);
      const ax = p0[0] < boxR.x ? boxR.x : boxR.x + boxR.w;
      if (Math.abs(p0[1] - ay) < 1) return [p0, [ax, ay]];
      const ex = elbowX != null ? elbowX : (p0[0] + ax) / 2;
      return [p0, [ex, p0[1]], [ex, ay], [ax, ay]];
    }

    // ---------- pointers: a note joined to what it explains, routed around everything else ----------
    // Laid out after every scene is built: the timeline is sought to the moment the note shows, the boxes that are visible then become
    // obstacles, and the wire takes the cleanest right-angled path: out of its target the short way, never along a line of text or
    // through another card, tile or the instructor; rounded corners, a ringed dot on the target.
    const pointers = [];
    function pointer(p0, note, g0, g1, ay) { pointers.push({ p0, note, g0, g1, ay }); }
    // visibility from each element's own setting (the timeline's autoAlpha, or the `hide` class): the renderer keeps the page hidden
    // while scripts run, so computed visibility (inherited) would call everything hidden
    const visOf = (el) => { let o = 1; for (let e = el; e && e !== root; e = e.parentElement) {
      const cs = getComputedStyle(e); if (cs.display === "none") return 0;
      const v = e.style.visibility; if (v === "hidden" || (!v && e.classList.contains("hide"))) return 0;
      o *= parseFloat(cs.opacity); } return o; };
    const rectOf = (el) => { const r = el.getBoundingClientRect(), o = root.getBoundingClientRect(); return { x0: r.left - o.left, y0: r.top - o.top, x1: r.right - o.left, y1: r.bottom - o.top }; };
    function layoutPointers() {
      if (!pointers.length) return;
      const keep = tl.time();
      pointers.forEach((w) => {
        // everything that shows at any moment while the wire is up is an obstacle (sampled every 1.5 s)
        const times = [w.g0 + 0.7]; for (let t = w.g0 + 2.2; t < w.g1 - 0.2 && times.length < 12; t += 1.5) times.push(t);
        let N = null; const obs = [];
        times.forEach((t, k) => {
          tl.seek(T(t), false);
          if (k === 0) N = rectOf(w.note);
          [...root.querySelectorAll("[data-fz], .fz-tile")].filter((e) => e !== w.note && !w.note.contains(e) && !e.closest(".fz-wires, .fz-edges") && visOf(e) > 0.3)
            .map(rectOf).filter((r) => r.x1 - r.x0 > 4 && r.y1 - r.y0 > 4 && (r.x1 - r.x0) * (r.y1 - r.y0) < 1920 * 1080 * 0.6)
            .forEach((r) => { if (!obs.some((q) => Math.abs(q.x0 - r.x0) < 2 && Math.abs(q.y0 - r.y0) < 2 && Math.abs(q.x1 - r.x1) < 2 && Math.abs(q.y1 - r.y1) < 2)) obs.push(r); });
        });
        const [px, py] = w.p0, inside = (r) => px >= r.x0 - 2 && px <= r.x1 + 2 && py >= r.y0 - 2 && py <= r.y1 + 2;
        const own = obs.filter(inside).sort((a, b) => (a.x1 - a.x0) * (a.y1 - a.y0) - (b.x1 - b.x0) * (b.y1 - b.y0));
        const tgt = own[0] || { x0: px - 1, y0: py - 1, x1: px + 1, y1: py + 1 };
        const others = obs.filter((r) => !inside(r));
        const ay = N.y0 + Math.min(w.ay != null ? w.ay : 40, (N.y1 - N.y0) / 2);
        const cxN = Math.min(N.x0 + 70, (N.x0 + N.x1) / 2);
        const ends = [[N.x0, ay, "h", "L"], [N.x1, ay, "h", "R"], [cxN, N.y0, "v", "T"], [cxN, N.y1, "v", "B"]];
        const mids = (vals) => { const v = [...new Set(vals.map(Math.round))].sort((a, b) => a - b); return v.slice(1).map((x, k) => (x + v[k]) / 2).filter((m, k) => v[k + 1] - v[k] >= 16); };
        const boxes = others.concat([tgt, N]);
        const lanesX = [px, tgt.x0 - 26, tgt.x1 + 26, N.x0 - 30, N.x1 + 30, ...others.flatMap((r) => [r.x0 - 24, r.x1 + 24]), ...mids(boxes.flatMap((r) => [r.x0, r.x1]))];
        const lanesY = [py, tgt.y0 - 26, tgt.y1 + 26, N.y0 - 30, N.y1 + 30, ...others.flatMap((r) => [r.y0 - 24, r.y1 + 24]), ...mids(boxes.flatMap((r) => [r.y0, r.y1]))];
        const cands = [];
        ends.forEach(([ax, by, dir, side]) => {
          const LX = lanesX.concat([ax]), LY = lanesY.concat([by]);
          const push = (c) => { c.side = side; cands.push(c); };
          if (dir === "h") {
            LX.forEach((ex) => push([[px, py], [ex, py], [ex, by], [ax, by]]));
            LY.forEach((ey) => LX.forEach((ex) => push([[px, py], [px, ey], [ex, ey], [ex, by], [ax, by]])));
          } else {
            LY.forEach((ey) => push([[px, py], [px, ey], [ax, ey], [ax, by]]));
            LX.forEach((ex) => LY.forEach((ey) => push([[px, py], [ex, py], [ex, ey], [ax, ey], [ax, by]])));
          }
        });
        const segHits = (a, b, r, pad) => { const x0 = Math.min(a[0], b[0]), x1 = Math.max(a[0], b[0]), y0 = Math.min(a[1], b[1]), y1 = Math.max(a[1], b[1]);
          return x0 < r.x1 - pad && x1 > r.x0 + pad && y0 < r.y1 - pad && y1 > r.y0 + pad; };
        const insideLen = (a, b, r) => { const x0 = Math.max(Math.min(a[0], b[0]), r.x0), x1 = Math.min(Math.max(a[0], b[0]), r.x1), y0 = Math.max(Math.min(a[1], b[1]), r.y0), y1 = Math.min(Math.max(a[1], b[1]), r.y1);
          return x1 < x0 || y1 < y0 ? 0 : Math.max(x1 - x0, y1 - y0); };
        let best = null, bestScore = Infinity;
        cands.forEach((c0) => {
          const c = [];                                                           // drop repeated and collinear points
          c0.forEach((q) => { if (c.length && Math.hypot(q[0] - c[c.length - 1][0], q[1] - c[c.length - 1][1]) < 0.5) return;
            if (c.length > 1) { const a1 = c[c.length - 2], b1 = c[c.length - 1];
              if ((a1[0] === b1[0] && b1[0] === q[0]) || (a1[1] === b1[1] && b1[1] === q[1])) c.pop(); }
            c.push(q); });
          if (c.length < 2) return;
          let score = 0, len = 0;
          for (let k = 1; k < c.length; k++) {
            const a = c[k - 1], b = c[k];
            if (a[0] !== b[0] && a[1] !== b[1]) { score += 1e6; break; }
            const L = Math.hypot(b[0] - a[0], b[1] - a[1]); len += L;
            if (k > 1 && L < 14) score += 400;                                    // no tiny jogs
            others.forEach((r) => { if (segHits(a, b, r, 3)) score += 1000;
              else { const gap = Math.max(r.x0 - Math.max(a[0], b[0]), Math.min(a[0], b[0]) - r.x1, r.y0 - Math.max(a[1], b[1]), Math.min(a[1], b[1]) - r.y1);
                     if (gap < 12) score += (12 - gap) * 6; } });                // keep a little air around other graphics
            score += insideLen(a, b, tgt) * 6;                                    // leave the target the short way
            if (Math.min(a[0], b[0]) < 24 || Math.max(a[0], b[0]) > 1896 || Math.min(a[1], b[1]) < 24 || Math.max(a[1], b[1]) > 1056) score += 2000;
            if (k > 1 && segHits(a, b, N, 2)) score += 1000;                      // never runs through its own note
          }
          const last = c[c.length - 1], prev = c[c.length - 2];
          if (Math.hypot(last[0] - prev[0], last[1] - prev[1]) < 18) score += 300;   // a clear lead-in to the note
          const fromOutside = { L: prev[1] === last[1] && prev[0] < last[0], R: prev[1] === last[1] && prev[0] > last[0],
                                T: prev[0] === last[0] && prev[1] < last[1], B: prev[0] === last[0] && prev[1] > last[1] }[c0.side];
          if (!fromOutside) score += 1e6;                                         // meets the note head-on, from outside
          score += len + (c.length - 2) * 70;
          if (score < bestScore) { bestScore = score; best = c; }
        });
        if (best && own[0] && tgt.x1 - tgt.x0 <= 240 && tgt.y1 - tgt.y0 <= 240) {   // a small target (a tile): start at its edge, not on its text
          const [q0, q1] = best, dx = Math.sign(q1[0] - q0[0]), dy = Math.sign(q1[1] - q0[1]);
          const e = dx > 0 ? [tgt.x1 + 4, q0[1]] : dx < 0 ? [tgt.x0 - 4, q0[1]] : dy > 0 ? [q0[0], tgt.y1 + 4] : [q0[0], tgt.y0 - 4];
          best = Math.hypot(q1[0] - e[0], q1[1] - e[1]) > 6 ? [e].concat(best.slice(1)) : [e].concat(best.slice(2));
        }
        if (best) drawPointer(best, w.g0, w.g1);
      });
      tl.seek(keep, false);
    }
    function drawPointer(pts, g0, g1) {
      if (!wires) { wires = document.createElementNS(NS, "svg"); wires.setAttribute("class", "fz-wires"); wires.setAttribute("width", "1920"); wires.setAttribute("height", "1080"); root.appendChild(wires); }
      const gEl = document.createElementNS(NS, "g"); gEl.style.opacity = "0"; gEl.style.visibility = "hidden";
      let d = `M ${pts[0][0]} ${pts[0][1]}`;
      for (let k = 1; k < pts.length - 1; k++) {                              // rounded corners
        const a = pts[k - 1], c = pts[k], b = pts[k + 1];
        const r = Math.min(14, Math.hypot(c[0] - a[0], c[1] - a[1]) / 2, Math.hypot(b[0] - c[0], b[1] - c[1]) / 2);
        const u = [(c[0] - a[0]) / (Math.hypot(c[0] - a[0], c[1] - a[1]) || 1), (c[1] - a[1]) / (Math.hypot(c[0] - a[0], c[1] - a[1]) || 1)];
        const v = [(b[0] - c[0]) / (Math.hypot(b[0] - c[0], b[1] - c[1]) || 1), (b[1] - c[1]) / (Math.hypot(b[0] - c[0], b[1] - c[1]) || 1)];
        d += ` L ${c[0] - u[0] * r} ${c[1] - u[1] * r} Q ${c[0]} ${c[1]} ${c[0] + v[0] * r} ${c[1] + v[1] * r}`;
      }
      d += ` L ${pts[pts.length - 1][0]} ${pts[pts.length - 1][1]}`;
      const p = document.createElementNS(NS, "path"); p.setAttribute("d", d); gEl.appendChild(p);
      wires.appendChild(gEl);
      const len = p.getTotalLength ? p.getTotalLength() : 1000;
      p.style.strokeDasharray = len + " " + (len + 20); p.style.strokeDashoffset = len;
      const dot = (q, r, cls) => { const c = document.createElementNS(NS, "circle"); c.setAttribute("cx", q[0]); c.setAttribute("cy", q[1]); c.setAttribute("r", r); c.setAttribute("class", cls); gEl.appendChild(c); return c; };
      dot(pts[0], 6.5, "t"); const end = dot(pts[pts.length - 1], 4, "e"); end.style.opacity = "0";
      set(gEl, g0, { autoAlpha: 1 });
      tl.fromTo(p, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: M.wire, ease: "power2.inOut", immediateRender: false }, T(g0));
      tl.fromTo(end, { opacity: 0 }, { opacity: 1, duration: 0.12, immediateRender: false }, T(g0 + M.wire - 0.05));
      out(gEl, g1, {}, 0.25);
    }

    // ---------- svg edges (flowcharts, diagrams) ----------
    let edgeSvg = null;
    function edge(d, g0, g1, cls = "", dur = 0.5) {
      if (!edgeSvg) {
        edgeSvg = document.createElementNS(NS, "svg"); edgeSvg.setAttribute("class", "fz-edges"); edgeSvg.setAttribute("width", "1920"); edgeSvg.setAttribute("height", "1080");
        edgeSvg.innerHTML = `<defs>${[["a", "var(--fz-text2)"], ["ah", "var(--fz-accent)"], ["ar", "var(--fz-danger)"], ["ag", "var(--fz-success)"]].map(([id, c]) =>
          `<marker id="fz-${id}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" style="fill:${c}" stroke="none"/></marker>`).join("")}</defs>`;
        // under the graphics but above static layers (compose mode: plate, background, presenter live inside #root)
        const anchor = root.querySelector("#fz-presenter");
        if (anchor) anchor.after(edgeSvg); else root.insertBefore(edgeSvg, root.firstChild);
      }
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", d); if (cls) p.setAttribute("class", cls);
      p.setAttribute("marker-end", `url(#fz-${cls === "hot" ? "ah" : cls === "red" ? "ar" : cls === "green" ? "ag" : "a"})`);
      edgeSvg.appendChild(p);
      const len = p.getTotalLength();
      p.style.strokeDasharray = len + " " + (len + 40); p.style.strokeDashoffset = len; p.style.opacity = "0";
      set(p, g0, { opacity: 1 });
      tl.fromTo(p, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: dur, ease: "power2.inOut", immediateRender: false }, T(g0));
      out(p, g1, {}, 0.25);
      return p;
    }

    // several elements that form ONE idea on screen (a tile row, a list, a flowchart): the items become "part"s and an
    // invisible bounding element carries the "block" role, so the clutter budget counts them once (rule L10)
    function group(els, g0, g1) {
      els = els.filter(Boolean);
      if (!els.length) return null;
      els.forEach((e) => e.setAttribute("data-fz", "part"));
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      els.forEach((e) => { const r = e.getBoundingClientRect(); x0 = Math.min(x0, r.left); y0 = Math.min(y0, r.top); x1 = Math.max(x1, r.right); y1 = Math.max(y1, r.bottom); });
      const gEl = el("", "abs hide", { left: x0, top: y0, width: x1 - x0, height: y1 - y0, pointerEvents: "none" }, root, "block");
      set(gEl, g0, { autoAlpha: 1 }); if (g1 != null) set(gEl, g1 + 0.3, { autoAlpha: 0 });
      return gEl;
    }

    const api = {
      tl, T, OFF, END, B, LAY, M, root, $, byId, NS, el, px, esc, md, icon, cv, box, inn, out, pop, set, to, show, pulse, sfx,
      classify, hlCode, wire, route, pointer, edge, group, refs: {},
      // default exit for a scene: its own `until`, else the end of the clip
      until: (p) => (p.until != null ? p.until : END - 0.1),
      // run scenes in spec order: [{template, params}]
      run(scenes) {
        scenes.forEach((s, i) => {
          const fn = FZ.templates[s.template];
          if (!fn) { window.__fz_errors.push(`scene ${i}: unknown template "${s.template}"`); return; }
          try { fn(api, s.params || {}); } catch (e) { window.__fz_errors.push(`scene ${i} (${s.template}): ${e.message}`); }
        });
        try { layoutPointers(); } catch (e) { window.__fz_errors.push(`pointers: ${e.message}`); }
      },
    };
    return api;
  };
})();
