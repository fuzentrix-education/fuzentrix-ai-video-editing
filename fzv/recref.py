"""Recording reference (design §4.2): a keyframe for every settled state of a screen recording, at raw-cut times.

The planner reads these to copy code exactly, to time each line's typing and the Run press, and to see the program's input and
output. With `Recording: reference` the recording itself is never shown; the edit rebuilds it from these keyframes.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import media

DET_W = 960            # detection width: a typed character is ~50 changed pixels here, a blinking caret ~15


def gray_frames(rec: Path, crop: list[int], fps: float) -> np.ndarray:
    x, y, cw, ch = crop
    h = max(2, round(DET_W * ch / cw) // 2 * 2)
    cmd = ["ffmpeg", "-v", "error", "-i", str(rec), "-vf", f"fps={fps},crop={cw}:{ch}:{x}:{y},scale={DET_W}:{h}:flags=area,format=gray",
           "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out, size = [], DET_W * h
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        out.append(np.frombuffer(b, np.uint8).reshape(h, DET_W))
    p.wait()
    return np.stack(out) if out else np.zeros((0, h, DET_W), np.uint8)


def changed(a: np.ndarray, b: np.ndarray) -> int:
    return int((np.abs(a.astype(np.int16) - b.astype(np.int16)) > 24).sum())


def settled_states(frames: np.ndarray, fps: float, settle_s: float = 1.0, still_px: int = 40, new_px: int = 70) -> list[tuple[int, int, int]]:
    """[(first, last, change_start)] frame indices of each settled state that differs from the previous kept state.
    Frames are compared one second apart, which cancels a blinking caret (it is in the same phase again)."""
    n = len(frames)
    if n == 0:
        return []
    lag = max(1, round(fps))
    still = [True] * min(lag, n) + [changed(frames[i], frames[i - lag]) < still_px for i in range(lag, n)]
    runs, i = [], 0
    while i < n:
        if still[i]:
            j = i
            while j + 1 < n and still[j + 1]:
                j += 1
            first = i - 1 if i > 0 else 0
            if (j - first + 1) / fps >= settle_s:
                runs.append((first, j))
            i = j + 1
        else:
            i += 1
    kept, last_end = [], 0
    for first, last in runs:
        mid = (first + last) // 2
        if not kept or changed(frames[mid], frames[(kept[-1][0] + kept[-1][1]) // 2]) >= new_px:
            kept.append((first, last, last_end))
        last_end = last
    return kept


def build(rec: Path, r: dict, out_dir: Path, fps: float = 2.0, max_frames: int = 80, log=print) -> dict:
    """Write keyframes (content-area PNGs), contact sheets and index.json for one aligned recording."""
    out_dir.mkdir(parents=True, exist_ok=True)
    crop, off = r["crop"], r.get("offset") or 0.0
    frames = gray_frames(rec, crop, fps)
    new_px = 70
    states = settled_states(frames, fps, new_px=new_px)
    while len(states) > max_frames:
        new_px = int(new_px * 1.6)
        states = settled_states(frames, fps, new_px=new_px)
    for f in out_dir.glob("k*.png"):
        f.unlink()
    x, y, cw, ch = crop
    keys = []
    for k, (first, last, change) in enumerate(states, 1):
        t_mid = (first + last) / 2 / fps
        name = f"k{k:02d}_{off + first / fps:07.1f}.png"
        media.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t_mid:.3f}", "-i", rec, "-frames:v", "1", "-vf", f"crop={cw}:{ch}:{x}:{y}", out_dir / name])
        keys.append({"k": k, "file": name, "t_raw": round(off + first / fps, 2), "until_raw": round(off + last / fps, 2),
                     "change_from_raw": round(off + change / fps, 2), "t_rec": round(first / fps, 2)})
    sheets = contact_sheets(out_dir, keys)
    idx = {"id": r["id"], "file": r["file"], "offset": off, "crop": crop, "keyframes": keys, "sheets": sheets,
           "note": "keyframe pixels are content-area pixels; recording pixel = (x + crop[0], y + crop[1])"}
    (out_dir / "index.json").write_text(json.dumps(idx, indent=1))
    log(f"recording {r['id']}: {len(keys)} keyframes -> {out_dir}")
    return idx


def contact_sheets(out_dir: Path, keys: list[dict], cols: int = 2, rows: int = 4, tile_w: int = 900) -> list[str]:
    names = []
    try:
        font = ImageFont.truetype(str(Path(__file__).resolve().parents[1] / "global/brand/_shared/fonts/jetbrains-mono-latin-700-normal.woff2"), 22)
    except OSError:
        font = ImageFont.load_default()
    per = cols * rows
    for s in range(0, len(keys), per):
        chunk = keys[s:s + per]
        ims = [Image.open(out_dir / k["file"]).convert("RGB") for k in chunk]
        th = round(tile_w * ims[0].height / ims[0].width)
        sheet = Image.new("RGB", (cols * tile_w + (cols + 1) * 12, rows * (th + 40) + 12), (24, 32, 44))
        d = ImageDraw.Draw(sheet)
        for i, (k, im) in enumerate(zip(chunk, ims)):
            cx, cy = 12 + (i % cols) * (tile_w + 12), 12 + (i // cols) * (th + 40)
            d.text((cx, cy + 4), f"k{k['k']:02d}  raw {k['t_raw']:.1f}s  (changing from {k['change_from_raw']:.1f}s)", fill=(230, 236, 245), font=font)
            sheet.paste(im.resize((tile_w, th), Image.LANCZOS), (cx, cy + 34))
        name = f"sheet_{s // per + 1:02d}.jpg"
        sheet.save(out_dir / name, quality=88)
        names.append(name)
    return names
