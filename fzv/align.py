"""Screen recordings (design §4.1): separate files aligned to the raw cut by audio, with their content area measured."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
from scipy.signal import fftconvolve

from . import media


def envelope(x: np.ndarray, sr: int, rate: int = 100) -> np.ndarray:
    hop = sr // rate
    n = len(x) // hop
    e = np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1))
    return (e - e.mean()) / (e.std() + 1e-9)


def speech_fraction(path: Path) -> float:
    """Share of 50 ms windows with speech-level energy; used to tell the raw cut from recordings."""
    info = media.probe(path)
    if not info["audio"]:
        return 0.0
    with tempfile.TemporaryDirectory() as d:
        wav = media.extract_audio(path, Path(d) / "a.wav", 8000, True, dur=min(info["duration"], 600))
        x, sr = media.read_wav_mono(wav)
    hop = sr // 20
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    return float((db > np.percentile(db, 20) + 12).mean())


def offset(raw_wav: Path, rec: Path) -> tuple[float | None, float]:
    """Raw-cut time at which the recording's t=0 plays, and a confidence score (correlation peak, ~0.8+ = same take)."""
    info = media.probe(rec)
    if not info["audio"]:
        return None, 0.0
    with tempfile.TemporaryDirectory() as d:
        rw = media.extract_audio(rec, Path(d) / "r.wav", 8000, True)
        xr, sr = media.read_wav_mono(rw)
    x, sr2 = media.read_wav_mono(raw_wav)
    if sr2 != sr:
        from scipy.signal import resample_poly
        x = resample_poly(x, sr, sr2)
    er, ex = envelope(xr, sr), envelope(x, sr)
    seg = er[: min(len(er), 100 * 40)]                       # first 40 s of the recording
    if len(seg) < 200 or len(ex) < len(seg):
        return None, 0.0
    c = fftconvolve(ex, seg[::-1], mode="valid") / len(seg)
    k = int(np.argmax(c))
    return round(k / 100, 2), round(float(c[k]), 3)


def solid_block(med: np.ndarray, ref: np.ndarray):
    """Largest solid region that differs from `ref`, as (rows, cols) slices, if everything outside it matches `ref`."""
    from scipy import ndimage
    h, w = med.shape[:2]
    d = np.abs(med - ref).max(-1) > 6
    solid = ndimage.binary_opening(d, np.ones((7, 7), bool))   # drops thin arcs, text strokes and logo outlines
    lab, n = ndimage.label(solid)
    if n == 0:
        return None
    k = int(np.argmax(ndimage.sum(solid, lab, range(1, n + 1))))
    ys, xs = ndimage.find_objects(lab)[k]
    area = (ys.stop - ys.start) * (xs.stop - xs.start) / (h * w)
    outside = d.copy()
    outside[ys, xs] = False
    if 0.15 <= area <= 0.92 and outside.sum() / (h * w * (1 - area)) < 0.06:   # logos and plate swooshes are allowed
        return ys, xs
    return None


def crop_from_frame(med: np.ndarray, W: int, H: int, plates: list[np.ndarray] = ()) -> list[int]:
    """Content box of a (median) recording frame, in W x H pixels. The margins must match a known background: the raw cut's
    plate, a brand plate image, or a uniform border colour (desktop, bars). Full frame if none fits."""
    from PIL import Image
    from .config import BRANDS
    med = med.astype(np.float32)
    h, w = med.shape[:2]
    refs = [np.asarray(Image.fromarray(np.clip(p, 0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) for p in plates]
    refs += [np.asarray(Image.open(f).convert("RGB").resize((w, h), Image.LANCZOS), np.float32) for f in sorted(BRANDS.glob("*/plate/*.png"))]
    border = np.concatenate([med[0], med[-1], med[:, 0], med[:, -1]])
    refs.append(np.broadcast_to(np.median(border, 0), med.shape))
    for ref in refs:
        b = solid_block(med, ref)
        if b:
            ys, xs = b
            s, pad = W / w, 4
            x0, y0 = max(0, int(xs.start * s) - pad), max(0, int(ys.start * s) - pad)
            x1, y1 = min(W, int(xs.stop * s) + pad), min(H, int(ys.stop * s) + pad)
            return [x0 // 2 * 2, y0 // 2 * 2, (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2]
    return [0, 0, W, H]


def content_area(rec: Path, plates: list[np.ndarray] = ()) -> list[int]:
    """[x, y, w, h] of the recording's content (IDE/browser) without plain margins around it. Full frame if unsure."""
    info = media.probe(rec)
    W, H = info["width"], info["height"]
    fr = list(media.frames(rec, 0.2, 480, int(480 * H / W) // 2 * 2))
    if not fr:
        return [0, 0, W, H]
    return crop_from_frame(np.median(np.stack(fr[:30]), 0), W, H, plates)


def recordings(raw_wav: Path, files: list[Path], log=print, plates: list[np.ndarray] = ()) -> list[dict]:
    out = []
    for i, f in enumerate(files):
        off, conf = offset(raw_wav, f)
        info = media.probe(f)
        crop = content_area(f, plates)
        rid = f"rec{i + 1}"
        out.append({"id": rid, "file": f.name, "offset": off, "confidence": conf, "width": info["width"], "height": info["height"],
                    "duration": round(info["duration"], 2), "crop": crop, "needs_offset": off is None or conf < 0.6})
        log(f"recording {rid}: {f.name}  offset {off}s  confidence {conf}  content area {crop}")
    return out
