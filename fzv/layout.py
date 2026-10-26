"""Ingest analysis for overlay mode (an editor's rough cut): classify every frame, refine cuts to exact frames,
measure the instructor's safe zone per shot kind, and fit the layout slots around it.

Shot kinds:
  studio  - full-screen instructor on the studio background
  corner  - instructor small (bottom right) on the brand plate, the rest of the frame free for graphics
  plate   - instructor large on the plate (e.g. the intro)
  empty   - plate with no instructor (e.g. the editor's logo animation)
"""
from __future__ import annotations

import numpy as np

from . import media

W, H, FPS = 96, 54, 5


def otsu(values: np.ndarray) -> tuple[float, float]:
    """Threshold and separation score for a 1-D distribution."""
    hist, edges = np.histogram(values, bins=64)
    mids = (edges[:-1] + edges[1:]) / 2
    best, thr = 0.0, float(values.mean())
    total = hist.sum()
    for i in range(1, 64):
        w0, w1 = hist[:i].sum(), hist[i:].sum()
        if w0 == 0 or w1 == 0:
            continue
        m0, m1 = (hist[:i] * mids[:i]).sum() / w0, (hist[i:] * mids[i:]).sum() / w1
        var = w0 * w1 * (m0 - m1) ** 2 / total ** 2
        if var > best:
            best, thr = var, mids[i]
    return thr, best


def bbox(mask: np.ndarray):
    if mask.sum() < 12:
        return None
    ys, xs = np.nonzero(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def kind_of(f: np.ndarray, plate_ref: np.ndarray, thr: float, two: bool):
    """Kind and instructor box of one low-res frame."""
    if two and f[1:10, 1:20].mean() < thr:
        return "studio", None
    b = bbox(np.abs(f.astype(np.float32) - plate_ref).max(-1) > 40)
    if b is None:
        return "empty", None
    return ("corner" if b[0] > W * 0.55 and b[1] > H * 0.4 else "plate"), b


PLATE_FILE: str | None = None        # the brand plate image the editor composited onto (set by plate_reference)


def plate_reference(plate_frames: np.ndarray) -> np.ndarray:
    """The empty plate. Editors composite onto a brand plate image, so use it when it matches the footage; otherwise the
    per-pixel 95th percentile (the light plate shows through whenever the instructor moves)."""
    from PIL import Image
    from .config import BRANDS
    sub = plate_frames[::5].astype(np.float32)
    med = np.median(sub, 0)
    for f in sorted(BRANDS.glob("*/plate/*.png")) + sorted(BRANDS.glob("*/*plate*.png")):
        cand = np.asarray(Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS), np.float32)
        if np.median(np.abs(cand[: int(H * 0.4), : int(W * 0.6)] - med[: int(H * 0.4), : int(W * 0.6)]).max(-1)) < 8:
            global PLATE_FILE
            PLATE_FILE = str(f.relative_to(BRANDS))
            return cand
    # no brand plate: the brightest-frame estimate, except where it departs strongly from a smooth fitted background
    # (a static instructor never "shows through", so take the fitted background there)
    from .keyer import fit_poly
    p95 = np.percentile(sub, 95, axis=0)
    border = np.median(np.concatenate([med[0], med[-1], med[:, 0], med[:, -1]]), 0)
    keep = np.abs(med - border).max(-1) < 30
    if keep.mean() < 0.2:
        return p95
    fitted = fit_poly(med, keep, (H, W))
    dev = np.abs(p95 - fitted).max(-1) > 40
    return np.where(dev[..., None], fitted, p95)


def classify(frames: np.ndarray):
    """Per-frame kind and instructor box (low-res coords), plus per-kind occupancy grids (3x3 low-res cells = 60 px).
    Returns (kinds, boxes, plate_ref, studio_ref, thr, two, occupancy)."""
    lum = frames[:, 1:10, 1:20].reshape(len(frames), -1, 3).mean((1, 2))
    thr, sep = otsu(lum)
    two = bool(sep > 40 and (lum < thr).mean() > 0.01 and (lum >= thr).mean() > 0.2)
    plate_mask = lum >= thr if two else np.ones(len(frames), bool)
    plate_ref = plate_reference(frames[plate_mask])
    studio_ref = np.median(frames[~plate_mask][::5].astype(np.float32), 0) if (~plate_mask).sum() > 5 else None
    kinds, boxes, occ = [], [], {}
    for f in frames:
        k, b = kind_of(f, plate_ref, thr, two)
        kinds.append(k); boxes.append(b)
        if k in ("corner", "plate"):
            m = np.abs(f.astype(np.float32) - plate_ref).max(-1) > 40
            cells = m.reshape(H // 3, 3, W // 3, 3).any((1, 3))
            cnt = occ.setdefault(k, [np.zeros(cells.shape, np.int32), 0])
            cnt[0] += cells; cnt[1] += 1
    occupancy = {k: (c / max(1, n)) >= 0.03 for k, (c, n) in occ.items()}
    return kinds, boxes, plate_ref, studio_ref, thr, two, occupancy


def segments(kinds: list[str], fps: float, min_len: float = 0.5) -> list[list]:
    seg = []
    for i, k in enumerate(kinds):
        t = i / fps
        if seg and seg[-1][0] == k:
            seg[-1][2] = t
        else:
            seg.append([k, t, t])
    clean = []
    for s in seg:
        if clean and (s[2] - s[1] < min_len or clean[-1][0] == s[0]):
            clean[-1][2] = s[2]
            continue
        clean.append(s)
    if len(clean) > 1 and clean[0][2] - clean[0][1] < min_len:     # a blip at the very start joins the next segment
        clean[1][1] = clean[0][1]
        clean.pop(0)
    return clean


def refine(src, segs, plate_ref, thr, two, src_fps, duration):
    """Move each boundary to the exact source frame where the new kind starts."""
    cuts = []
    for i, (k, a, b) in enumerate(segs):
        start = 0.0
        if i > 0:
            t0 = max(0.0, a - 0.3)
            ks = [kind_of(f, plate_ref, thr, two)[0] for f in media.frames(src, src_fps, W, H, start=t0, dur=0.6)]
            prev = segs[i - 1][0]
            if k == "studio" or prev == "studio":         # a studio cut is the first frame that flips studio <-> not studio
                j = next((n for n, kk in enumerate(ks) if (kk == "studio") == (k == "studio")), None)
            else:
                j = next((n for n, kk in enumerate(ks) if kk == k), None)
            start = round(t0 + j / src_fps, 3) if j is not None else round(a, 3)
            cuts[-1]["end"] = start
        cuts.append({"kind": k, "start": start, "end": None})
    if cuts:
        cuts[-1]["end"] = round(duration, 3)
    return cuts


def zone_of(boxes, kinds, kind, sx, sy, margin=16):
    bb = [b for b, k in zip(boxes, kinds) if k == kind and b]
    if not bb:
        return None
    x0 = min(b[0] for b in bb) * sx - margin
    y0 = min(b[1] for b in bb) * sy - margin
    x1 = (max(b[2] for b in bb) + 1) * sx + margin
    y1 = (max(b[3] for b in bb) + 1) * sy + margin
    return [int(max(0, x0)), int(max(0, y0)), int(min(1920, x1)), int(min(1080, y1))]


def zone_rects(grid: np.ndarray, margin: int = 16) -> list[list[int]]:
    """Occupied 60 px cells merged into row runs, in full-res pixels."""
    rects, cs = [], 60
    for r in range(grid.shape[0]):
        c = 0
        while c < grid.shape[1]:
            if grid[r, c]:
                c0 = c
                while c < grid.shape[1] and grid[r, c]:
                    c += 1
                rects.append([max(0, c0 * cs - margin), max(0, r * cs - margin), min(1920, c * cs + margin), min(1080, (r + 1) * cs + margin)])
            else:
                c += 1
    return rects


def studio_slot(studio_ref: np.ndarray | None, default: dict) -> dict | None:
    """Where studio-layer graphics go: the first candidate (default slot top-left, then top-centre, then top-right) that sits on calm wall."""
    if studio_ref is None:
        return None
    g = studio_ref.mean(-1)
    e = np.zeros_like(g)
    e[:-1, :] += np.abs(np.diff(g, axis=0)); e[:, :-1] += np.abs(np.diff(g, axis=1))
    base = float(np.percentile(e[: int(H * 0.65)], 20)) + 0.1
    sx, sy = 1920 / W, 1080 / H
    d = default
    cands = [d, {"x": (1920 - d["w"]) // 2, "y": 60, "w": d["w"], "h": min(d["h"], 240)}, {"x": 1920 - d["x"] - d["w"], "y": d["y"], "w": d["w"], "h": d["h"]}]
    for c in cands:
        reg = e[int(c["y"] / sy):int((c["y"] + c["h"]) / sy), int(c["x"] / sx):int((c["x"] + c["w"]) / sx)]
        if reg.size and reg.mean() < 3 * base:
            return dict(c)
    return None


def fit_layout(layout: dict, zones: dict, studio_slot: dict | None) -> dict:
    """Trim slots so they never touch the corner instructor; place the studio slot on the calm wall."""
    out = {k: dict(v) for k, v in layout.items()}
    z = zones.get("corner")
    if z:
        x0, y0 = z[0], z[1]
        for k in ("side", "recording"):
            s = out.get(k)
            if s and s["x"] + s["w"] > x0 - 24 and "h" in s:
                s["h"] = max(120, min(s["h"], y0 - 24 - s["y"]))
        for k in ("main", "bottom"):
            s = out.get(k)
            if s and s["y"] + s.get("h", 0) > y0 - 24:
                s["w"] = max(400, min(s["w"], x0 - 24 - s["x"]))
        nc = out.get("namecard")
        if nc and nc["x"] + 380 > x0 and nc["y"] + 110 > y0:
            nc["y"] = max(120, y0 - 140)
    if studio_slot:
        out["studio"] = studio_slot
    return out


def analyse(src, info: dict, layout_defaults: dict, log=print) -> dict:
    log(f"layout: scanning {info['duration']:.0f}s at {FPS} fps")
    frames = np.stack(list(media.frames(src, FPS, W, H)))
    kinds, boxes, plate_ref, studio_ref, thr, two, occ = classify(frames)
    segs = segments(kinds, FPS)
    cuts = refine(src, segs, plate_ref, thr, two, info["fps"], info["duration"])
    sx, sy = 1920 / W, 1080 / H
    zones = {}
    for k in ("corner", "plate"):
        bb = zone_of(boxes, kinds, k, sx, sy)
        if bb:
            zones[k] = {"bbox": bb, "cells": zone_rects(occ[k]) if k in occ else [bb]}
    slot = studio_slot(studio_ref, layout_defaults["studio"])
    layout = fit_layout(layout_defaults, {k: v["bbox"] for k, v in zones.items()}, slot)
    counts = {k: round(sum(c["end"] - c["start"] for c in cuts if c["kind"] == k), 1) for k in ("studio", "corner", "plate", "empty")}
    log(f"layout: {len(cuts)} segments; seconds by kind {counts}; studio slot {slot}")
    return {"cuts": cuts, "zones": zones, "layout": layout, "counts": counts, "plate_ref": plate_ref, "plate_file": PLATE_FILE}


def auto_mode(cuts: list[dict], counts: dict, duration: float) -> str:
    """overlay for an editor's rough cut (an edited layout: several shots, the instructor in a corner or off an empty plate for a
    real share of the video); compose for raw footage (one continuous take: green screen, plain wall, or a plate without layout)."""
    laid_out = counts.get("corner", 0) + counts.get("empty", 0)
    return "overlay" if len(cuts) >= 2 and laid_out > 0.2 * duration else "compose"
