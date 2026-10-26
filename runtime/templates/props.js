/* Props family: characters and objects from global/props (design §9c). build.py inlines only the SVGs a clip uses
   into window.FZ_PROPS, so props recolour with the brand's CSS variables. Fixed motion vocabulary: enter, idle, move, react, exit. */
(function () {
  const R = FZ.register;
  const make = (a, id, bx, role = "block") => {
    const svg = (window.FZ_PROPS || {})[id];
    if (!svg) throw new Error(`prop "${id}" is not in global/props (add it with fzv props add)`);
    const e = a.el(svg, "fz-prop hide", { left: bx.x, top: bx.y, width: bx.w, height: bx.h }, a.root, role);
    return e;
  };
  const enter = (a, e, kind, g) => {
    if (kind === "slide") a.inn(e, g, { x: -80 }, 0.6);
    else if (kind === "fade") a.inn(e, g, {}, 0.5, "power1.out");
    else a.inn(e, g, { scale: 0.6, y: 20 }, 0.55, "back.out(1.8)");
  };
  const idle = (a, e, kind, g, until) => {
    if (kind !== "bob" || until == null) return;
    const reps = Math.max(1, Math.floor((until - g - 0.8) / 1.2));
    a.tl.fromTo(e, { y: 0 }, { y: -6, duration: 0.6, yoyo: true, repeat: reps * 2 - 1, ease: "sine.inOut", immediateRender: false }, a.T(g + 0.6));
  };
  const react = (a, e, kind, g) => {
    if (kind === "shake") a.tl.fromTo(e, { x: 0 }, { keyframes: [{ x: -8 }, { x: 8 }, { x: -5 }, { x: 0 }], duration: 0.4, immediateRender: false }, a.T(g));
    else if (kind === "pulse") a.pulse(e, g, 1.1);
    else if (kind === "tick" || kind === "cross") {
      const m = a.el(a.icon(kind === "tick" ? "check" : "x"), "abs hide", { left: e.offsetLeft + e.offsetWidth - 20, top: e.offsetTop - 20, fontSize: 48, color: kind === "tick" ? "var(--fz-success)" : "var(--fz-danger)" }, a.root, "deco");
      a.pop(m, g); a.sfx(kind === "tick" ? "good" : "bad", g); return m;
    }
  };

  R({ name: "prop", family: "props", layers: ["plate", "studio"], doc: "Place a character or prop from the library; optional idle motion and reactions.",
      params: { asset: "library id (global/props/manifest.yaml)", box: "x, y, w, h", at: "", until: "", enter: "pop | slide | fade", idle: "bob | none", flip: "mirror horizontally",
                react: "[{kind: shake|pulse|tick|cross, at}]", label: "{text, at} caption under the prop" } }, (a, p) => {
    const bx = a.box(p, "main"), e = make(a, p.asset, bx);
    if (p.flip) e.querySelector("svg").style.transform = "scaleX(-1)";
    enter(a, e, p.enter, p.at); idle(a, e, p.idle, p.at, a.until(p)); a.out(e, a.until(p)); a.sfx("pop", p.at);
    const extra = (p.react || []).map((r) => react(a, e, r.kind, r.at)).filter(Boolean); extra.forEach((m) => a.out(m, a.until(p)));
    if (p.label) { const l = a.el(a.md(p.label.text), "fz-small abs hide", { left: bx.x - 40, top: bx.y + bx.h + 10, width: bx.w + 80, textAlign: "center", color: "var(--fz-text)" }, a.root, "text"); a.show(l, p.label.at != null ? p.label.at : p.at, a.until(p), { y: 8 }, 0.3); }
    a.refs[p.id || p.asset] = { kind: "prop", el: e };
  });

  R({ name: "prop-move", family: "props", layers: ["plate"], doc: "Move a prop along a path (a car driving past, a ball rolling), with easing and optional speed lines.",
      params: { asset: "", box: "start x, y and size w, h", path: "[[x, y]...] later positions (absolute px)", times: "[arrival time per point]", at: "appear", until: "",
                enter: "pop | slide | fade", flip: "", speed_lines: "true for motion streaks" } }, (a, p) => {
    const bx = a.box(p, "main"), e = make(a, p.asset, bx);
    if (p.flip) e.querySelector("svg").style.transform = "scaleX(-1)";
    enter(a, e, p.enter || "slide", p.at); a.sfx("swish", p.at);
    let prev = p.at, px0 = bx.x, py0 = bx.y;
    (p.path || []).forEach((pt, i) => {
      const t = (p.times || [])[i]; if (t == null) return;
      const dur = Math.max(0.3, Math.min(2.5, (t - prev) * 0.9));
      a.tl.to(e, { x: pt[0] - bx.x, y: pt[1] - bx.y, duration: dur, ease: "power2.inOut" }, a.T(t - dur));
      if (p.speed_lines) {
        const dir = pt[0] >= px0 ? -1 : 1;
        const sl = a.el([0, 1, 2].map((k) => `<div style="position:absolute;left:0;top:${k * 18}px;width:${80 - k * 20}px;height:5px;border-radius:3px;background:var(--fz-line)"></div>`).join(""), "abs hide", { left: 0, top: 0, width: 80, height: 50 }, a.root, "deco");
        a.tl.fromTo(sl, { autoAlpha: 0, x: px0 + (dir < 0 ? -60 : bx.w + 10), y: py0 + bx.h * 0.4 }, { autoAlpha: 0.9, x: pt[0] + (dir < 0 ? -60 : bx.w + 10), y: pt[1] + bx.h * 0.4, duration: dur, ease: "power2.inOut", immediateRender: false }, a.T(t - dur));
        a.out(sl, t + 0.05, {}, 0.2);
      }
      a.sfx("whoosh", t - dur); prev = t; px0 = pt[0]; py0 = pt[1];
    });
    a.out(e, a.until(p));
    a.refs[p.id || p.asset] = { kind: "prop", el: e };
  });

  R({ name: "prop-scene", family: "props", layers: ["plate"], doc: "A small staged scene: a ground line (road or desk) with several props, each with its own entrance and moves.",
      params: { ground: "road | desk | none", box: "scene area x, y, w, h (ground sits at the bottom)", at: "", until: "",
                props: "[{asset, x, y, w, h (relative to box), at, flip, moves: [{to: [x, y], at}], react: [{kind, at}]}]" } }, (a, p) => {
    const bx = a.box(p, "main"), U = a.until(p);
    if (p.ground === "road") {
      const g = a.el(`<div style="position:absolute;left:0;right:0;top:41px;height:6px;background:repeating-linear-gradient(90deg,#fff 0 42px,transparent 42px 78px);opacity:.75"></div>`, "abs hide",
        { left: bx.x, top: bx.y + bx.h - 92, width: bx.w, height: 92, borderRadius: 20, background: "linear-gradient(180deg,#53627A,#3E4B60)", boxShadow: "0 24px 50px -24px rgba(13,39,76,.6)" }, a.root, "deco");
      a.show(g, p.at, U, { scaleX: 0.6 }, 0.7);
    } else if (p.ground === "desk") {
      const g = a.el("", "abs hide", { left: bx.x, top: bx.y + bx.h - 26, width: bx.w, height: 26, borderRadius: 13, background: "linear-gradient(180deg,#B9825B,#9A6844)" }, a.root, "deco");
      a.show(g, p.at, U, { scaleX: 0.6 }, 0.6);
    }
    const parts = [];
    (p.props || []).forEach((pr, i) => {
      const b = { x: bx.x + pr.x, y: bx.y + pr.y, w: pr.w || 160, h: pr.h || 120 }, e = make(a, pr.asset, b);
      if (pr.flip) e.querySelector("svg").style.transform = "scaleX(-1)";
      enter(a, e, pr.enter, pr.at != null ? pr.at : p.at + i * 0.15); a.sfx("pop", pr.at);
      (pr.moves || []).forEach((m) => { a.tl.to(e, { x: m.to[0] - pr.x, y: m.to[1] - pr.y, duration: m.dur || 1.1, ease: "power2.inOut" }, a.T(m.at)); a.sfx("whoosh", m.at); });
      const extra = (pr.react || []).map((r) => react(a, e, r.kind, r.at)).filter(Boolean); extra.forEach((m) => a.out(m, pr.until != null ? pr.until : U));
      a.out(e, pr.until != null ? pr.until : U);
      if (pr.id) a.refs[pr.id] = { kind: "prop", el: e };
      parts.push(e);
    });
    a.group(parts, p.at, U);
  });
})();
