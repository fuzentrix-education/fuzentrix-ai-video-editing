"""Keyer for compose mode (design §12.2): cut the instructor out of raw footage into a VP9-alpha WebM.

Background models, tried in order:
  plate   - the footage was composited onto a brand plate image: difference matte against that exact plate
  chroma  - green screen: chroma key with despill
  fitted  - plain studio wall: a smooth degree-4 polynomial background fitted per channel, then a difference matte
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

from . import media
from .config import BRANDS

T0, T1, TH = 10.0, 40.0, 28.0


def _sample(src: Path, info: dict, n: int = 40, w: int = 480) -> np.ndarray:
    fps = max(0.05, n / max(1.0, info["duration"]))
    h = int(w * info["height"] / info["width"])
    return np.stack(list(media.frames(src, fps, w, h))[:n]).astype(np.float32)


def fit_poly(img: np.ndarray, keep: np.ndarray, out_hw: tuple[int, int]) -> np.ndarray:
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w]
    sel = np.flatnonzero(keep.ravel())[::7]
    terms = lambda X, Y: np.stack([X ** i * Y ** j for i in range(5) for j in range(5 - i)], 1)
    A = terms(xs.ravel()[sel] / w, ys.ravel()[sel] / h)
    H, W = out_hw
    yy, xx = np.mgrid[0:H, 0:W]
    Af = terms(xx.ravel() / W, yy.ravel() / H)
    out = np.zeros((H, W, 3), np.float32)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A, img[..., c].ravel()[sel], rcond=None)
        out[..., c] = (Af @ coef).reshape(H, W)
    return np.clip(out, 0, 255)


def background(src: Path, info: dict, log=print) -> tuple[str, np.ndarray]:
    """(mode, full-resolution background plate as float32 HxWx3)."""
    fr = _sample(src, info)
    med = np.median(fr, 0)
    h, w = med.shape[:2]
    border = np.zeros((h, w), bool); border[: h // 5] = True; border[:, : w // 6] = True; border[:, -w // 6:] = True
    H, W = info["height"], info["width"]
    for f in sorted(BRANDS.glob("*/plate/*.png")):
        cand = np.asarray(Image.open(f).convert("RGB").resize((w, h), Image.LANCZOS), np.float32)
        if np.median(np.abs(cand - med).max(-1)[border]) < 8:          # median: robust to a burned-in logo or the instructor's edge
            log(f"keyer: footage sits on the brand plate ({f.name})")
            return "plate", np.asarray(Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS), np.float32)
    g = med[..., 1] - np.maximum(med[..., 0], med[..., 2])
    if g[border].mean() > 40:
        log("keyer: green screen")
        return "chroma", np.zeros((H, W, 3), np.float32)
    fg = np.abs(fr - med).max(-1).mean(0) > 12                     # where the instructor moves
    keep = ~ndi.binary_dilation(fg, iterations=6)
    keep[: h // 8] |= True
    log("keyer: plain background, fitting a smooth plate")
    return "fitted", fit_poly(med, keep, (H, W))


def region_mask(h: int, w: int, opts: dict | None) -> np.ndarray | None:
    """1 where the instructor may appear: everything except `exclude` boxes [x, y, w, h], `exclude_poly` polygons
    [[x, y], ...] (e.g. along a laptop's slanted edge) and the area below `cut_below` (a desk line)."""
    if not opts:
        return None
    m = np.ones((h, w), np.float32)
    for x, y, bw, bh in opts.get("exclude") or []:
        m[int(y):int(y + bh), int(x):int(x + bw)] = 0
    if opts.get("exclude_poly"):
        poly = Image.new("L", (w, h), 255)
        draw = ImageDraw.Draw(poly)
        for pts in opts["exclude_poly"]:
            draw.polygon([tuple(p) for p in pts], fill=0)
        m *= np.asarray(poly, np.float32) / 255
    if opts.get("cut_below"):
        m[int(opts["cut_below"]):] = 0
    return m


def matte(rgb: np.ndarray, plate: np.ndarray, mode: str, region: np.ndarray | None = None) -> np.ndarray:
    """rgb uint8 HxWx3 → RGBA uint8."""
    c = rgb.astype(np.float32)
    if mode == "chroma":
        g = c[..., 1] - np.maximum(c[..., 0], c[..., 2])
        a = np.clip(1 - (g - 20) / 60, 0, 1)
        f = c.copy(); f[..., 1] = np.minimum(c[..., 1], np.maximum(c[..., 0], c[..., 2]))   # green-limit despill: no green fringe on edges
        a = ndi.median_filter(a, 3)
        if region is not None:
            a *= region
    else:
        d = np.abs(c - plate).max(-1)
        a = np.clip((d - T0) / (T1 - T0), 0, 1)
        if region is not None:
            a *= region
            d = d * (region > 0)
        hard = ndi.binary_opening(d > TH, iterations=1)
        filled = ndi.binary_fill_holes(hard)
        a = np.maximum(a, (filled & ~hard).astype(np.float32))
        lab, n = ndi.label(a > 0.5)
        if n:
            sizes = ndi.sum(np.ones_like(a), lab, range(1, n + 1))
            big = int(np.argmax(sizes)) + 1
            keep = np.isin(lab, [big] + [i + 1 for i, s in enumerate(sizes) if s >= 1500 and i + 1 != big
                                         and ndi.binary_dilation(lab == big, iterations=12)[lab == i + 1].any()])
            a *= ndi.binary_dilation(keep, iterations=6)
        ac = a[..., None]
        f = np.where(ac > 0.04, (c - (1 - ac) * plate) / np.maximum(ac, 0.04), c)
    return np.dstack([np.clip(f, 0, 255), a[..., None] * 255]).astype(np.uint8)


def crop_box(src: Path, info: dict, plate: np.ndarray, mode: str, opts: dict | None = None) -> list[int]:
    W, H = info["width"], info["height"]
    region = region_mask(H, W, opts)
    x0, y0, x1, y1 = W, H, 0, 0
    for f in media.frames(src, max(0.05, 20 / max(1, info["duration"])), W, H):
        a = matte(f, plate, mode, region)[..., 3] > 128
        if a.sum() < 500:
            continue
        ys, xs = np.nonzero(a)
        x0, y0, x1, y1 = min(x0, xs.min()), min(y0, ys.min()), max(x1, xs.max()), max(y1, ys.max())
    if x1 <= x0:
        return [0, 0, W, H]
    x0, y0 = max(0, x0 - 40) // 2 * 2, max(0, y0 - 40) // 2 * 2
    x1, y1 = min(W, x1 + 40), min(H, y1 + 40)
    return [int(x0), int(y0), int((x1 - x0) // 2 * 2), int((y1 - y0) // 2 * 2)]


def key_video(src: Path, out: Path, info: dict, plate: np.ndarray, mode: str, crop: list[int], fps: int = 25, log=print, opts: dict | None = None) -> Path:
    W, H = info["width"], info["height"]
    x, y, w, h = crop
    region = region_mask(H, W, opts)
    region = region[y:y + h, x:x + w] if region is not None else None       # key only the instructor's box: ~3x less work per frame
    plate = plate[y:y + h, x:x + w]
    tmp = out.with_name(out.stem + ".part" + out.suffix)                    # an interrupted run never leaves a "finished" file
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-vf", f"fps={fps},crop={w}:{h}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-crf", "22", "-b:v", "0", "-row-mt", "1", "-deadline", "good", "-cpu-used", "4", str(tmp)], stdin=subprocess.PIPE)
    n, size = 0, w * h * 3
    while True:
        b = dec.stdout.read(size)
        if len(b) < size:
            break
        rgba = matte(np.frombuffer(b, np.uint8).reshape(h, w, 3), plate, mode, region)
        enc.stdin.write(rgba.tobytes())
        n += 1
        if n % 250 == 0:
            log(f"keyer: {n} frames")
    enc.stdin.close(); enc.wait(); dec.wait()
    if enc.returncode != 0 or n == 0:
        raise SystemExit(f"keyer: encoding failed after {n} frames")
    tmp.replace(out)
    log(f"keyer: {n} frames → {out.name}")
    return out
