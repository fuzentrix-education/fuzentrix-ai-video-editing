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

    // ---------- layout ----------
    // slot: main | side | bottom | full | studio | header; a spec may pass an explicit box {x, y, w, h}
    const box = (p, slot) => Object.assign({}, LAY[slot] || LAY.main || { x: 96, y: 210, w: 1220, h: 790 }, p.box || {});

    // ---------- python syntax colouring ----------
    const KW = ["for", "in", "if", "elif", "else", "while", "break", "continue", "pass", "def", "return", "and", "or", "not", "True", "False", "None", "is", "import", "from", "class", "try", "except", "finally", "with", "as", "lambda", "yield", "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE", "CREATE", "TABLE", "JOIN", "ON", "GROUP", "BY", "ORDER", "AND", "OR", "NOT", "NULL", "PRIMARY", "KEY"];
    const FN = ["print", "range", "input", "int", "len", "str", "float", "list", "dict", "set", "tuple", "sum", "min", "max", "sorted", "open", "type", "COUNT", "AVG", "SUM", "MIN", "MAX"];
    function classify(txt) {
      const cls = new Array(txt.length).fill("");
      let ci = -1, q = null;
      for (let i = 0; i < txt.length; i++) { const c = txt[i]; if (q) { if (c === q) q = null; } else if (c === "'" || c === '"') q = c; else if (c === "#" || (c === "-" && txt[i + 1] === "-")) { ci = i; break; } }
      const re = /'[^']*'?|"[^"]*"?|[A-Za-z_][A-Za-z_0-9]*|\d+(\.\d+)?|./g; let m;
      while ((m = re.exec(txt))) {
        if (ci >= 0 && m.index >= ci) break;
        const w = m[0];
        const c = /^['"]/.test(w) ? "str" : KW.includes(w) ? "kw" : FN.includes(w) ? "fn" : /^\d/.test(w) ? "num" : /^[A-Za-z_]/.test(w) || w === " " ? "" : "op";
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
      tl, T, OFF, END, B, LAY, M, root, $, byId, NS, el, px, esc, md, icon, box, inn, out, pop, set, to, show, pulse, sfx,
      classify, hlCode, wire, route, edge, group, refs: {},
      // default exit for a scene: its own `until`, else the end of the clip
      until: (p) => (p.until != null ? p.until : END - 0.1),
      // run scenes in spec order: [{template, params}]
      run(scenes) {
        scenes.forEach((s, i) => {
          const fn = FZ.templates[s.template];
          if (!fn) { window.__fz_errors.push(`scene ${i}: unknown template "${s.template}"`); return; }
          try { fn(api, s.params || {}); } catch (e) { window.__fz_errors.push(`scene ${i} (${s.template}): ${e.message}`); }
        });
      },
    };
    return api;
  };
})();
