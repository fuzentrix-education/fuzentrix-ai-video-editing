/* Presenter (compose mode only): the keyed instructor on the brand plate, with named poses (rule L5: focus in the intro,
   then one fixed position, at most 2 moves). build_compose adds this scene to every clip and emits the static <video>. */
(function () {
  FZ.register({ name: "presenter", family: "presenter", layers: ["plate"], static: true,
    doc: "Keyed instructor with poses: studio (her whole studio shot, laptop and desk, life-size and centred: the intro), wide, close, side-right, side-left, corner (bottom right, boxed). Added automatically in compose mode from the spec's `presenter.poses`.",
    params: { poses: "[{name, at, x, y, scale (optional custom)}]", crop: "[x, y, w, h] of the cut-out in source pixels (set by ingest)",
              box: "{w, h, margin, radius}: the bottom-right pose sits in a rounded box (setting presenter.corner_box)",
              studio: "[{t0, t1, el, crop}]: the keyed studio shots this clip shows (set by build)", max_scale: "largest face enlargement (default 1.1: never soft)" } }, (a, p) => {
    const host = a.byId("fz-presenter"); if (!host) throw new Error("presenter markup missing");
    host.setAttribute("data-fz", "presenter");      // validate reads its live box: the instructor's safe zone in compose mode (rule L2)
    const [pcx, pcy, w, h] = p.crop, CAP = p.max_scale || 1.1;      // her face is never enlarged more than 1.1x (it would soften)
    const cap = (s) => Math.min(s, CAP);
    const POSE = {
      studio:       () => ({ scale: 1, x: pcx, y: pcy }),               // where she is in the camera frame: life-size, centred
      wide:         () => { const s = cap(940 / h); return { scale: s, x: (1920 - w * s) / 2 + 140, y: 1080 - h * s + 30 }; },
      close:        () => { const s = cap(1350 / h); return { scale: s, x: (1920 - w * s) / 2, y: 1080 - h * s + 260 * s / (1350 / h) }; },
      "side-right": () => { const s = cap(860 / h); return { scale: s, x: 1920 - w * s - 30, y: 1080 - h * s + 30 }; },
      "side-left":  () => { const s = cap(860 / h); return { scale: s, x: 30, y: 1080 - h * s + 30 }; },
      corner:       () => {
        if (p.box && p.free) {                   // the studio keying in a roomy box: from just above her head to the desk, centred on her
          const B = p.box, F = p.free, bx = 1920 - B.margin - B.w, by = 1080 - B.margin - B.h, s = cap(B.h / (F.desk_y - F.head_y));
          return { scale: s, x: bx + B.w / 2 - (F.focus_x - pcx) * s, y: by - (F.head_y - pcy) * s };
        }
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
        border: "4px solid #FFFFFF", boxShadow: "0 30px 70px -24px rgba(16,42,86,.45), 0 0 0 1px var(--fz-line)" }, host.parentNode);
      host.parentNode.insertBefore(frame, host);
      frame.setAttribute("data-fz", "presenter-frame");
      clipOf = (q) => { const t = poseOf(q), s = t.scale; return `inset(${(by + 4 - t.y) / s}px ${(t.x + w * s - (bx + B.w - 4)) / s}px ${(t.y + h * s - (by + B.h - 4)) / s}px ${(bx + 4 - t.x) / s}px round ${(B.radius - 4) / s}px)`; };
    }
    const OPEN = "inset(-2000px -2000px -2000px -2000px round 0px)";
    const poseOf = (q) => Object.assign(POSE[q.name] ? POSE[q.name]() : POSE.wide(), q.x != null ? { x: q.x } : {}, q.y != null ? { y: q.y } : {}, q.scale != null ? { scale: q.scale } : {});
    const poses = (p.poses || [{ name: "wide", at: 0 }]).slice().sort((x, y) => x.at - y.at);
    // a move that starts exactly where a section starts belongs to that section (it animates there instead of cutting)
    const atStart = poses.filter((q) => q.at < a.OFF - 0.01).pop() || poses[0];
    gsap.set(host, Object.assign({ transformOrigin: "0 0" }, poseOf(atStart)));
    const boxed = (q) => frame && q.name === "corner";
    // studio shots: the keyed studio video (her with laptop and desk), aligned with the cut-out's pose so the two match exactly
    const ST = (p.studio || []).map((s) => Object.assign({}, s, { node: a.byId(s.el) })).filter((s) => s.node);
    const layerOf = (q) => ST.find((s) => Math.abs(s.t0 - q.at) < 0.05);
    const alignOf = (s, q) => { const t = poseOf(q); return { x: t.x + t.scale * (s.crop[0] - pcx), y: t.y + t.scale * (s.crop[1] - pcy), scale: t.scale }; };
    const clipStudio = (s, q) => {               // the studio frame clipped to the corner box, in its own (unscaled) pixels
      const B = p.box, bx = 1920 - B.margin - B.w, by = 1080 - B.margin - B.h, t = alignOf(s, q), sw = s.crop[2], sh = s.crop[3], k = t.scale;
      return `inset(${(by + 4 - t.y) / k}px ${(t.x + sw * k - (bx + B.w - 4)) / k}px ${(t.y + sh * k - (by + B.h - 4)) / k}px ${(bx + 4 - t.x) / k}px round ${(B.radius - 4) / k}px)`;
    };
    ST.forEach((s) => gsap.set(s.node, { transformOrigin: "0 0", x: s.crop[0], y: s.crop[1], clipPath: OPEN }));
    const D = 0.8, EASE = (a.M.move || [0.5, "power2.inOut"])[1];
    // in a studio shot the cut-out stays under the studio video at the same place (validate reads her position from it, rule L2)
    if (atStart.name === "studio" && layerOf(atStart)) { gsap.set(layerOf(atStart).node, { autoAlpha: 1 }); gsap.set(host, { autoAlpha: 0 }); }   // one picture of her, no double edges
    if (frame) { gsap.set(host, { clipPath: boxed(atStart) ? clipOf(atStart) : OPEN }); if (boxed(atStart)) gsap.set(frame, { autoAlpha: 1 }); }
    let cur = atStart;
    poses.filter((q) => q !== atStart && q.at >= a.OFF - 0.01 && q.at < a.END).forEach((q) => {
      const from = cur.name === "studio" && layerOf(cur), into = q.name === "studio" && layerOf(q);
      if (from) {                                // out of the studio shot: the whole frame shrinks to where she lands, then the cut-out takes over
        a.set(host, q.at, { autoAlpha: 0 });
        a.set(host, q.at + 0.02, Object.assign(poseOf(q), boxed(q) ? { clipPath: clipOf(q) } : {}));
        a.tl.fromTo(from.node, { x: from.crop[0], y: from.crop[1], scale: 1, clipPath: OPEN },
          Object.assign(alignOf(from, q), { clipPath: boxed(q) ? clipStudio(from, q) : OPEN, duration: D, ease: EASE, immediateRender: false }), a.T(q.at));
        if (boxed(q)) a.inn(frame, q.at + D - 0.35, { scale: 0.96 }, 0.35);
        a.set(host, q.at + D, { autoAlpha: 1 });                 // the hand-over only once the frame has landed exactly on her
        a.to(from.node, q.at + D, { autoAlpha: 0, duration: 0.25, ease: "none" });
      } else if (into) {                         // into a studio shot: the frame grows from where she is to the whole studio
        a.set(into.node, q.at, Object.assign(alignOf(into, cur), { clipPath: boxed(cur) ? clipStudio(into, cur) : OPEN }));
        a.to(into.node, q.at, { autoAlpha: 1, duration: 0.25, ease: "none" });
        a.tl.to(into.node, { x: into.crop[0], y: into.crop[1], scale: 1, clipPath: OPEN, duration: D, ease: EASE }, a.T(q.at + 0.2));
        a.set(host, q.at + 0.25, { autoAlpha: 0 });
        a.set(host, q.at + 0.2 + D, Object.assign({}, poseOf(q), { clipPath: OPEN }));   // stays hidden under the studio video
        if (boxed(cur)) a.out(frame, q.at + 0.25, {}, 0.3);
      } else if (p.free) {                       // studio keying: the whole frame and the box's clip move together (one picture, no hand-over)
        const c0 = boxed(cur) ? clipOf(cur) : OPEN, c1 = boxed(q) ? clipOf(q) : OPEN;
        a.tl.fromTo(host, Object.assign(poseOf(cur), { clipPath: c0 }), Object.assign(poseOf(q), { clipPath: c1, duration: D, ease: EASE, immediateRender: false }), a.T(q.at));
        if (boxed(q)) a.inn(frame, q.at + D - 0.35, { scale: 0.96 }, 0.35);
        if (boxed(cur) && !boxed(q)) a.out(frame, q.at, {}, 0.3);
      } else {
        if (boxed(cur) && !boxed(q)) { a.set(host, q.at, { clipPath: OPEN }); a.out(frame, q.at, {}, 0.3); }
        a.tl.fromTo(host, poseOf(cur), Object.assign(poseOf(q), { duration: D, ease: EASE, immediateRender: false }), a.T(q.at));
        if (boxed(q)) {   // the box appears as she lands, then closes around her
          a.inn(frame, q.at + D - 0.35, { scale: 0.96 }, 0.35);
          a.tl.fromTo(host, { clipPath: OPEN }, { clipPath: clipOf(q), duration: 0.01, immediateRender: false }, a.T(q.at + D));
        }
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
    const frame = a.el("", "abs hide", { left: x, top: y, width: w, height: h, borderRadius: r, border: "4px solid #FFFFFF", boxShadow: "0 24px 60px -20px rgba(16,42,86,.45), 0 0 0 1px var(--fz-line)" }, a.root, "presenter-frame");
    (p.intervals || []).forEach(([s, e]) => {
      els.forEach((el) => { a.set(el, s, { autoAlpha: 1 }); a.set(el, e, { autoAlpha: 0 }); });
      a.inn(frame, s, { scale: 0.97 }, 0.35); a.set(frame, e, { autoAlpha: 0 });
    });
  });
})();
