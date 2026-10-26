/* Presenter (compose mode only): the keyed instructor on the brand plate, with named poses (rule L5: focus in the intro,
   then one fixed position, at most 2 moves). build_compose adds this scene to every clip and emits the static <video>. */
(function () {
  FZ.register({ name: "presenter", family: "presenter", layers: ["plate"], static: true,
    doc: "Keyed instructor with poses: wide, close, side-right, side-left, corner (bottom right). Added automatically in compose mode from the spec's `presenter.poses`.",
    params: { poses: "[{name, at, x, y, scale (optional custom)}]", crop: "[x, y, w, h] of the cut-out in source pixels (set by ingest)",
              box: "{w, h, margin, radius}: the bottom-right pose sits in a rounded box (setting presenter.corner_box)" } }, (a, p) => {
    const host = document.getElementById("fz-presenter"); if (!host) throw new Error("presenter markup missing");
    host.setAttribute("data-fz", "presenter");      // validate reads its live box: the instructor's safe zone in compose mode (rule L2)
    const [, , w, h] = p.crop;
    const POSE = {
      wide:         () => { const s = 940 / h; return { scale: s, x: (1920 - w * s) / 2 + 140, y: 1080 - h * s + 30 }; },
      close:        () => { const s = 1350 / h; return { scale: s, x: (1920 - w * s) / 2, y: 1080 - h * s + 260 }; },
      "side-right": () => { const s = 860 / h; return { scale: s, x: 1920 - w * s - 30, y: 1080 - h * s + 30 }; },
      "side-left":  () => { const s = 860 / h; return { scale: s, x: 30, y: 1080 - h * s + 30 }; },
      corner:       () => {
        if (!p.box) { const s = 470 / h; return { scale: s, x: 1920 - w * s - 40, y: 1080 - h * s + 20 }; }
        // boxed: head and shoulders fill the box; the cut-out's top margin (~40 px) sits just above the box edge
        const B = p.box, s = Math.min((B.h * 1.08) / (h - 40), (B.w * 1.15) / w), bx = 1920 - B.margin - B.w, by = 1080 - B.margin - B.h;
        return { scale: s, x: bx + (B.w - w * s) / 2, y: by + 14 - 40 * s };
      },
    };
    // the box: a rounded brand frame behind her, and a clip so nothing of her shows outside it
    let frame = null, clipOf = null;
    if (p.box) {
      const B = p.box, bx = 1920 - B.margin - B.w, by = 1080 - B.margin - B.h;
      frame = a.el("", "abs hide", { left: bx, top: by, width: B.w, height: B.h, borderRadius: B.radius, background: "linear-gradient(165deg, #FFFFFF 0%, var(--fz-tint) 100%)",
        border: "4px solid #FFFFFF", boxShadow: "0 30px 70px -24px rgba(13,39,76,.45), 0 0 0 1px var(--fz-line)" }, host.parentNode);
      host.parentNode.insertBefore(frame, host);
      frame.setAttribute("data-fz", "presenter-frame");
      clipOf = (q) => { const t = poseOf(q), s = t.scale; return `inset(${(by + 4 - t.y) / s}px ${(t.x + w * s - (bx + B.w - 4)) / s}px ${(t.y + h * s - (by + B.h - 4)) / s}px ${(bx + 4 - t.x) / s}px round ${(B.radius - 4) / s}px)`; };
    }
    const OPEN = "inset(-2000px -2000px -2000px -2000px round 0px)";
    const poseOf = (q) => Object.assign(POSE[q.name] ? POSE[q.name]() : POSE.wide(), q.x != null ? { x: q.x } : {}, q.y != null ? { y: q.y } : {}, q.scale != null ? { scale: q.scale } : {});
    const poses = (p.poses || [{ name: "wide", at: 0 }]).slice().sort((x, y) => x.at - y.at);
    const atStart = poses.filter((q) => q.at <= a.OFF + 0.01).pop() || poses[0];
    gsap.set(host, Object.assign({ transformOrigin: "0 0" }, poseOf(atStart)));
    const boxed = (q) => frame && q.name === "corner";
    if (frame) { gsap.set(host, { clipPath: boxed(atStart) ? clipOf(atStart) : OPEN }); if (boxed(atStart)) gsap.set(frame, { autoAlpha: 1 }); }
    let cur = atStart;
    poses.filter((q) => q.at > a.OFF + 0.01 && q.at < a.END).forEach((q) => {
      if (boxed(cur) && !boxed(q)) { a.set(host, q.at, { clipPath: OPEN }); a.out(frame, q.at, {}, 0.3); }
      a.tl.fromTo(host, poseOf(cur), Object.assign(poseOf(q), { duration: 0.9, ease: "expo.inOut", immediateRender: false }), a.T(q.at));
      if (boxed(q)) {   // the box appears as she lands, then closes around her
        a.inn(frame, q.at + 0.55, { scale: 0.92 }, 0.45, "back.out(1.4)");
        a.tl.fromTo(host, { clipPath: OPEN }, { clipPath: clipOf(q), duration: 0.01, immediateRender: false }, a.T(q.at + 0.9));
      }
      a.sfx("whoosh", q.at); cur = q;
    });
  });
})();

/* Corner box for rough cuts (setting presenter.corner_box, rule L5): the editor's footage already holds the instructor, so the box
   is drawn around her bottom-right area and the strips outside it are covered with the same plate image the editor used,
   which makes her look cut by the box. Visible only during her corner shots (`intervals`). */
(function () {
  FZ.register({ name: "corner-box", family: "presenter", layers: ["plate"], static: true,
    doc: "Rough cuts: frame the instructor's bottom-right area in the brand box during corner shots (added automatically by build).",
    params: { box: "[x, y, w, h]", radius: "corner radius", plate: "plate image the editor used", intervals: "[[start, end]] corner shots" } }, (a, p) => {
    const [x, y, w, h] = p.box, r = p.radius || 28, bg = (l, t) => `url(${p.plate}) ${-l}px ${-t}px / 1920px 1080px no-repeat`;
    const els = [];
    const patch = (l, t, pw, ph, extra = {}) => { const e = a.el("", "abs hide", Object.assign({ left: l, top: t, width: pw, height: ph, background: bg(l, t) }, extra), a.root, "deco"); els.push(e); return e; };
    patch(x + w, y, 1920 - x - w, 1080 - y);                                  // right of the box
    patch(x, y + h, w, 1080 - y - h);                                         // below the box
    [[x, y, "100% 100%"], [x + w - r, y, "0 100%"], [x, y + h - r, "100% 0"], [x + w - r, y + h - r, "0 0"]].forEach(([l, t, at]) =>
      patch(l, t, r, r, { WebkitMaskImage: `radial-gradient(circle at ${at}, transparent ${r - 0.5}px, #000 ${r}px)`, maskImage: `radial-gradient(circle at ${at}, transparent ${r - 0.5}px, #000 ${r}px)` }));
    const frame = a.el("", "abs hide", { left: x, top: y, width: w, height: h, borderRadius: r, border: "4px solid #FFFFFF", boxShadow: "0 24px 60px -20px rgba(13,39,76,.45), 0 0 0 1px var(--fz-line)" }, a.root, "presenter-frame");
    (p.intervals || []).forEach(([s, e]) => {
      els.forEach((el) => { a.set(el, s, { autoAlpha: 1 }); a.set(el, e, { autoAlpha: 0 }); });
      a.inn(frame, s, { scale: 0.97 }, 0.35); a.set(frame, e, { autoAlpha: 0 });
    });
  });
})();
