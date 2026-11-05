/* 3D family (three.js r158, MIT): simple 3D explainers for one or two hero moments per video.
 *
 * Seekable like everything else: each scene is a pure function renderAt(t) of the global time, driven by one tween on the
 * paused GSAP timeline (no requestAnimationFrame, no clock, no randomness). Colours come from the theme's CSS variables
 * (ink, accent, success, danger, card), flat toon shading, no tone mapping, so 3D matches the 2D graphics in any theme.
 * Labels are HTML that follows the projected 3D positions: sharp text in the house fonts.
 * The page loads three.js only when a clip uses one of these templates (fzv build).
 */
(function () {
  const R = FZ.register;
  const css = (n, d) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || d;
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const smooth = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };
  const lerp = (a, b, u) => a + (b - a) * u;

  /* A 3D stage in the scene's box: renderer, camera, lights, theme colours, HTML labels, and the timeline driver. */
  function stage(a, p, opts) {
    const bx = a.box(p, "main"), U = a.until(p);
    const wrap = a.el("", "abs hide", { left: bx.x, top: bx.y, width: bx.w, height: bx.h }, a.root, "block");
    const cv = document.createElement("canvas");
    cv.width = bx.w; cv.height = bx.h; cv.style.cssText = `position:absolute;left:0;top:0;width:${bx.w}px;height:${bx.h}px`;
    wrap.appendChild(cv);
    const S = { a, p, bx, U, wrap, ok: false, labels: [] };
    S.color = (v, d) => new THREE.Color(css(v, d));
    S.mat = (v, d, extra) => new THREE.MeshToonMaterial(Object.assign({ color: S.color(v, d) }, extra || {}));
    S.label = (html, cls, style) => {
      const el = document.createElement("div");
      el.className = "fz-3dlabel " + (cls || "");
      el.innerHTML = html;
      el.style.cssText = "position:absolute;left:0;top:0;transform:translate(-50%,-50%);white-space:nowrap;pointer-events:none;" + (style || "");
      wrap.appendChild(el); S.labels.push(el);
      return el;
    };
    S.place = (el, v, dy, show) => {                       // put an HTML label at a 3D point (projected), or hide it
      if (!S.ok) return;
      const q = v.clone().project(S.cam);
      el.style.left = ((q.x + 1) / 2 * bx.w).toFixed(1) + "px";
      el.style.top = ((1 - q.y) / 2 * bx.h + (dy || 0)).toFixed(1) + "px";
      el.style.opacity = show === false ? 0 : 1;
    };
    try {
      S.r = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true, preserveDrawingBuffer: true });
      S.r.setPixelRatio(1); S.r.setSize(bx.w, bx.h, false); S.r.setClearColor(0x000000, 0);
      S.r.toneMapping = THREE.NoToneMapping; S.r.outputColorSpace = THREE.SRGBColorSpace;
      S.scene = new THREE.Scene();
      S.cam = new THREE.PerspectiveCamera(opts.fov || 30, bx.w / bx.h, 0.1, 200);
      S.cam.position.set(...(opts.cam || [0, 5, 11])); S.cam.lookAt(...(opts.look || [0, 0.6, 0]));
      S.scene.add(new THREE.HemisphereLight(0xffffff, 0xd8dde3, 1.1));
      const d = new THREE.DirectionalLight(0xffffff, 1.25); d.position.set(4, 9, 6); S.scene.add(d);
      S.ok = true;
    } catch (e) {
      window.__fz_errors.push(`${opts.name}: WebGL unavailable (${e.message}); the 3D scene is left blank`);
    }
    S.shadow = (x, z, rx, rz) => {                           // soft contact shadow: grounds objects without real shadows
      const m = new THREE.Mesh(new THREE.CircleGeometry(1, 48), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.09, depthWrite: false }));
      m.rotation.x = -Math.PI / 2; m.scale.set(rx, rz, 1); m.position.set(x, 0.005, z); S.scene.add(m); return m;
    };
    S.drive = (renderAt) => {                                // one tween over the scene's life; every seek re-renders
      const prox = { t: p.at };
      const draw = (t) => { if (S.ok) { renderAt(t); S.r.render(S.scene, S.cam); } };
      a.tl.to(prox, { t: U, duration: Math.max(0.04, U - p.at), ease: "none", immediateRender: false, onUpdate: () => draw(prox.t) }, a.T(p.at));
      draw(p.at);
      a.inn(wrap, p.at, { y: 16 }); a.out(wrap, U);
    };
    return S;
  }

  /* database: stacked discs with accent rings */
  function database(S, x, z, r) {
    const g = new THREE.Group(), body = S.mat("--fz-text", "#1F2328"), ring = S.mat("--fz-accent", "#E3A008");
    for (let i = 0; i < 3; i++) {
      const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, r * 0.55, 64), body); m.position.y = r * 0.3 + i * r * 0.64; g.add(m);
      const t = new THREE.Mesh(new THREE.TorusGeometry(r, r * 0.035, 8, 64), ring); t.rotation.x = Math.PI / 2; t.position.y = m.position.y + r * 0.275; g.add(t);
    }
    g.position.set(x, 0, z); S.scene.add(g); S.shadow(x, z, r * 1.25, r * 0.7);
    g.userData.top = new THREE.Vector3(x, r * 0.3 + 2 * r * 0.64 + r * 0.3, z);
    return g;
  }
  function laptop(S, x, z) {
    const g = new THREE.Group(), ink = S.mat("--fz-text", "#1F2328"), screen = S.mat("--fz-accent", "#E3A008");
    const base = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.1, 1.1), ink); base.position.y = 0.05; g.add(base);
    const lid = new THREE.Group(); lid.position.set(0, 0.1, -0.55);
    const back = new THREE.Mesh(new THREE.BoxGeometry(1.7, 1.05, 0.06), ink); back.position.set(0, 0.52, 0); lid.add(back);
    const glass = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 0.85), screen); glass.position.set(0, 0.52, 0.035); lid.add(glass);
    lid.rotation.x = -0.18; g.add(lid);
    g.position.set(x, 0, z); S.scene.add(g); S.shadow(x, z, 1.15, 0.8);
    g.userData.top = new THREE.Vector3(x, 1.25, z);
    return g;
  }
  function server(S, x, z) {
    const g = new THREE.Group(), ink = S.mat("--fz-text", "#1F2328"), led = S.mat("--fz-success", "#12A150");
    for (let i = 0; i < 3; i++) {
      const u = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.48, 1.0), ink); u.position.y = 0.26 + i * 0.52; g.add(u);
      const l = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.07, 0.02), led); l.position.set(0.42, 0.26 + i * 0.52, 0.51); g.add(l);
    }
    g.position.set(x, 0, z); S.scene.add(g); S.shadow(x, z, 1.0, 0.75);
    g.userData.top = new THREE.Vector3(x, 1.75, z);
    return g;
  }
  function person(S, x, z) {
    const g = new THREE.Group(), ink = S.mat("--fz-text", "#1F2328");
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.55, 1.0, 32), ink); body.position.y = 0.5; g.add(body);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.32, 32, 16), ink); head.position.y = 1.35; g.add(head);
    g.position.set(x, 0, z); S.scene.add(g); S.shadow(x, z, 0.75, 0.55);
    g.userData.top = new THREE.Vector3(x, 1.8, z);
    return g;
  }
  const db1 = (S, x, z) => database(S, x, z, 1.0);
  const KINDS = { database: db1, laptop, client: laptop, server, person, user: person };

  // ---------- db3d: records fly into a 3D database ----------
  R({ name: "db3d", family: "3d", layers: ["plate"],
      doc: "3D: records (labelled cards) fly one by one into a database cylinder that turns slowly; it pulses as each lands and a count rises. For collecting / storing data in a database. One hero moment per video.",
      params: { items: "[{text, at}] each card flies in at `at`", label: "label under the database (default Database)", count: "{to, label} count shown under the database (optional)",
                at: "", until: "", box: "x, y, w, h (default main slot)" } }, (a, p) => {
    const S = stage(a, p, { name: "db3d", cam: [0, 4.6, 11.5], look: [0.6, 1.0, 0] });
    if (!S.ok) { S.drive(() => {}); return; }
    const db = database(S, 2.4, 0, 1.45);
    const items = (p.items || []).map((it) => {
      const card = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.62, 0.08), S.mat("--fz-card", "#FFFFFF"));
      const edge = new THREE.Mesh(new THREE.BoxGeometry(1.56, 0.68, 0.06), S.mat("--fz-accent", "#E3A008")); edge.position.z = -0.02; card.add(edge);
      S.scene.add(card);
      const lab = S.label(a.esc(it.text), "", "font:700 26px/1 var(--fz-font-body);color:var(--fz-text)");
      a.sfx("whoosh", it.at);
      return { it, card, lab };
    });
    const nameEl = S.label(a.esc(p.label || "Database"), "", "font:600 24px/1 var(--fz-font-mono);letter-spacing:.16em;text-transform:uppercase;color:var(--fz-text2)");
    const cnt = p.count ? S.label("", "", "font:800 54px/1 var(--fz-font-display);color:var(--fz-text)") : null;
    const top = db.userData.top;
    S.drive((t) => {
      db.rotation.y = (t - p.at) * 0.35;
      let landed = 0, pulse = 0;
      items.forEach(({ it, card, lab }, k) => {
        const u = (t - it.at) / 0.9, e = smooth(u);
        const sx = -3.3, sy = 3.0 - (k % 3) * 0.95, sz = 0.6;
        card.position.set(lerp(sx, top.x, e), lerp(sy, top.y, e) + Math.sin(e * Math.PI) * 0.9, lerp(sz, top.z, e));
        card.rotation.set(0, lerp(0.25, 0, e), lerp(0, -0.2, e));
        card.scale.setScalar(lerp(1, 0.25, e));
        card.visible = u > -0.6 && u < 1;
        if (u >= 1) { landed++; pulse = Math.max(pulse, 1 - clamp01((u - 1) * 2.2)); }
        S.place(lab, card.position, 0, card.visible && e < 0.75);
        lab.style.opacity = card.visible ? (1 - smooth((e - 0.45) / 0.3)) * smooth((u + 0.6) / 0.4) : 0;
      });
      db.scale.set(1 + 0.05 * pulse, 1 + 0.08 * pulse, 1 + 0.05 * pulse);
      S.place(nameEl, new THREE.Vector3(top.x, 0, 0), 64);
      if (cnt) {
        const n = p.count.to != null ? Math.round(p.count.to * (items.length ? landed / items.length : 1)) : landed;
        cnt.innerHTML = `${n.toLocaleString("en-IN")} <span style="font:600 24px var(--fz-font-body);color:var(--fz-text2)">${a.esc(p.count.label || "")}</span>`;
        S.place(cnt, new THREE.Vector3(top.x, 0, 0), 122);
      }
    });
  });

  // ---------- network3d: nodes in 3D, packets travel between them ----------
  R({ name: "network3d", family: "3d", layers: ["plate"],
      doc: "3D: devices on a floor (person, laptop/client, server, database) joined by arcs; request and response packets travel along them on their words. For client/server, user -> DBMS -> database, APIs. One hero moment per video.",
      params: { nodes: "[{id, kind: person|laptop|server|database, text, x, z, at}] x -5..5, z -3..3 (floor units)",
                links: "[{from, to, at}] arcs draw on at `at`", packets: "[{from, to, label, at, dur, kind: req|res}]",
                at: "", until: "", box: "x, y, w, h (default main slot)" } }, (a, p) => {
    const S = stage(a, p, { name: "network3d", cam: [0, 7.5, 12], look: [0, 0.6, 0], fov: 32 });
    if (!S.ok) { S.drive(() => {}); return; }
    const N = {};
    (p.nodes || []).forEach((n) => {
      const g = (KINDS[n.kind] || server)(S, n.x || 0, n.z || 0);
      N[n.id] = { n, g, lab: S.label(a.esc(n.text || ""), "", "font:700 24px/1 var(--fz-font-body);color:var(--fz-text)") };
      a.sfx("pop", n.at != null ? n.at : p.at);
    });
    const curve = (A, B) => {
      const s = A.g.userData.top.clone(), e = B.g.userData.top.clone();
      const mid = s.clone().add(e).multiplyScalar(0.5); mid.y += 1.4 + s.distanceTo(e) * 0.12;
      return new THREE.QuadraticBezierCurve3(s, mid, e);
    };
    const links = (p.links || []).filter((l) => N[l.from] && N[l.to]).map((l) => {
      const c = curve(N[l.from], N[l.to]);
      const geo = new THREE.TubeGeometry(c, 64, 0.035, 8, false);
      const m = new THREE.Mesh(geo, S.mat("--fz-text2", "#59636E")); S.scene.add(m);
      return { l, m, total: geo.index.count };
    });
    const packets = (p.packets || []).filter((k) => N[k.from] && N[k.to]).map((k) => {
      const c = curve(N[k.from], N[k.to]);
      const col = k.kind === "res" ? "--fz-success" : "--fz-accent";
      const ball = new THREE.Mesh(new THREE.SphereGeometry(0.22, 24, 16), S.mat(col, k.kind === "res" ? "#12A150" : "#E3A008"));
      S.scene.add(ball);
      const lab = k.label ? S.label(a.esc(k.label), "", "font:600 22px/1 var(--fz-font-mono);padding:6px 12px;border-radius:999px;background:var(--fz-card);border:1px solid var(--fz-line);color:var(--fz-text)") : null;
      a.sfx("whoosh", k.at);
      return { k, c, ball, lab };
    });
    S.drive((t) => {
      const yaw = Math.sin((t - p.at) * 0.25) * 0.12;          // a slow, gentle camera sway
      S.cam.position.set(Math.sin(yaw) * 12, 7.5, Math.cos(yaw) * 12); S.cam.lookAt(0, 0.6, 0);
      Object.values(N).forEach(({ n, g, lab }) => {
        const u = smooth((t - (n.at != null ? n.at : p.at)) / 0.5);
        g.scale.setScalar(Math.max(0.001, u)); g.visible = u > 0;
        S.place(lab, new THREE.Vector3(g.position.x, 0, g.position.z), 36, u > 0.5);
      });
      links.forEach(({ l, m, total }) => {
        const u = smooth((t - (l.at != null ? l.at : p.at)) / 0.7);
        m.geometry.setDrawRange(0, Math.floor(total * u / 6) * 6); m.visible = u > 0;
      });
      packets.forEach(({ k, c, ball, lab }) => {
        const u = (t - k.at) / (k.dur || 1.2);
        ball.visible = u >= 0 && u <= 1;
        if (ball.visible) ball.position.copy(c.getPoint(smooth(u)));
        if (lab) S.place(lab, ball.position, -38, ball.visible);
      });
    });
  });

  // ---------- loop3d: a conveyor of loop values through a condition gate ----------
  R({ name: "loop3d", family: "3d", layers: ["plate"],
      doc: "3D: loop values ride a conveyor one per iteration through a gate that checks the condition; passing values drop into an output tray, the break value turns the gate red and the belt stops. For for-loops, range(), break.",
      params: { values: "[values] in loop order", times: "[time per value] when each value reaches the gate", cond: "condition label on the gate, e.g. 'i == 6'",
                stop_value: "value where break stops the loop (optional)", label: "caption above the belt (markdown)", at: "", until: "", box: "x, y, w, h (default main slot)" } }, (a, p) => {
    const S = stage(a, p, { name: "loop3d", cam: [0, 6.2, 11.5], look: [0, 0.4, 0], fov: 30 });
    if (!S.ok) { S.drive(() => {}); return; }
    const ink = S.mat("--fz-text", "#1F2328"), card = S.mat("--fz-card", "#FFFFFF");
    const belt = new THREE.Mesh(new THREE.BoxGeometry(11, 0.18, 1.5), S.mat("--fz-text2", "#59636E")); belt.position.y = 0.4; S.scene.add(belt);
    [-5.3, 5.3].forEach((x) => { const r = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 1.6, 24), ink); r.rotation.x = Math.PI / 2; r.position.set(x, 0.4, 0); S.scene.add(r); });
    S.shadow(0, 0, 6, 1.2);
    const gate = new THREE.Group();
    const postL = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.2, 0.2), ink); postL.position.set(0, 1.2, -1.0); gate.add(postL);
    const postR = postL.clone(); postR.position.z = 1.0; gate.add(postR);
    const barMat = S.mat("--fz-text", "#1F2328");
    const bar = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.22, 2.2), barMat); bar.position.set(0, 2.3, 0); gate.add(bar);
    gate.position.x = 0.8; S.scene.add(gate);
    const condEl = p.cond ? S.label(a.esc(p.cond), "", "font:700 26px/1 var(--fz-font-mono);padding:8px 16px;border-radius:12px;background:var(--fz-card);border:2px solid var(--fz-line);color:var(--fz-text)") : null;
    const cap = p.label ? S.label(a.md(p.label), "", "font:600 30px/1.2 var(--fz-font-body);color:var(--fz-text2);transform:none;left:8px;top:8px") : null;
    const ok = S.color("--fz-success", "#12A150"), bad = S.color("--fz-danger", "#E5484D"), plain = S.color("--fz-text", "#1F2328");
    const vals = (p.values || []), times = p.times || vals.map((_, i) => p.at + 0.8 + i * 0.9);
    const stopIdx = p.stop_value != null ? vals.findIndex((v) => v === p.stop_value) : -1;
    const blocks = vals.map((v, i) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.8, 0.8), card);
      const e = new THREE.Mesh(new THREE.BoxGeometry(0.84, 0.84, 0.84), new THREE.MeshToonMaterial({ color: plain.clone(), transparent: true, opacity: 0.18 })); m.add(e);
      S.scene.add(m);
      const lab = S.label(a.esc(v), "", "font:800 34px/1 var(--fz-font-body);color:var(--fz-text)");
      if (i <= (stopIdx >= 0 ? stopIdx : vals.length - 1)) a.sfx(i === stopIdx ? "bad" : "tick", times[i]);
      return { v, i, m, e, lab };
    });
    S.drive((t) => {
      const stopT = stopIdx >= 0 ? times[stopIdx] : Infinity;
      const tt = Math.min(t, stopT + 0.15);                     // the belt stops just after the break value reaches the gate
      blocks.forEach(({ i, m, e, lab }) => {
        if (stopIdx >= 0 && i > stopIdx) { m.visible = false; lab.style.opacity = 0; return; }   // never reached
        const arrive = times[i], u = (tt - arrive);            // seconds relative to reaching the gate
        let x = gate.position.x + u * 2.8, y = 0.9, z = 0;
        const passed = u > 0.3 && i !== stopIdx;
        if (passed) {                                          // passed values settle in rows in the output tray, front right
          const k = blocks.slice(0, i).filter((b) => b.i !== stopIdx).length, f = smooth((u - 0.3) / 0.6);
          x = lerp(gate.position.x + 0.84, 2.0 + (k % 4) * 0.86, f); y = lerp(0.9, 0.45, f); z = lerp(0, 1.8 + Math.floor(k / 4) * 0.9, f);
        }
        m.visible = u > -2.0; m.position.set(x, y, z);         // values come into view at the left end of the belt
        const flash = Math.abs(u) < 0.3;
        e.material.color.copy(i === stopIdx && u > -0.1 ? bad : (flash || passed) ? ok : plain);
        e.material.opacity = i === stopIdx && u > -0.1 ? 0.55 : flash ? 0.45 : passed ? 0.3 : 0.18;
        S.place(lab, m.position, 0, m.visible);
      });
      const hit = stopIdx >= 0 && t >= stopT;
      barMat.color.copy(hit ? bad : blocks.some(({ i }) => Math.abs(t - times[i]) < 0.3) ? ok : plain);
      bar.rotation.x = hit ? 0 : 0;
      if (condEl) S.place(condEl, new THREE.Vector3(gate.position.x, 3.1, 0), 0);
    });
  });
})();
