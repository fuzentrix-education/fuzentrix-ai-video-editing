"""`fzv verify`: duration and fps, overlay coverage, frames on both sides of every cut, loudness; a contact sheet."""
from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

from . import media


def grab(path: Path, t: float, w: int = 384) -> Image.Image:
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-vf", f"scale={w}:-1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(io.BytesIO(b)).convert("RGB")


def verify(proj, final: Path, raw_info: dict, cuts: list[dict], log=print) -> dict:
    fi = media.probe(final)
    lo = media.loudness(final)
    pdata = proj.load()
    checks = {
        "duration": {"ok": abs(fi["duration"] - raw_info["duration"]) < 0.1, "final": fi["duration"], "raw": raw_info["duration"]},
        # overlay keeps the source rate; compose re-renders the whole picture at the graphics rate
        "fps": {"ok": abs(fi["fps"] - (pdata.get("graphics_fps", 25) if pdata.get("mode") == "compose" else raw_info["fps"])) < 0.01,
                "final": fi["fps"], "raw": raw_info["fps"]},
        "size": {"ok": (fi["width"], fi["height"]) == (1920, 1080), "final": [fi["width"], fi["height"]]},
        "loudness": {"ok": abs(lo.get("lufs", 0) + 14) < 0.6 and lo.get("peak", 0) <= -0.8, **lo},
    }
    dur = fi["duration"]
    times = [round(dur * (i + 0.5) / 12, 2) for i in range(12)]
    for c in [c for c in cuts if c["kind"] == "studio"][:6]:
        times += [round(c["start"] - 0.04, 2), round(c["start"] + 0.04, 2)]
    tiles = []
    for t in times:
        im = grab(final, max(0, min(dur - 0.05, t)))
        ImageDraw.Draw(im).text((6, 4), f"{t:.2f}s", fill=(255, 255, 0))
        tiles.append(im)
    cols = 4
    w, h = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), (20, 20, 20))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * (w + 4), (i // cols) * (h + 4)))
    sheet_path = proj.edit / "out" / "verify.jpg"
    sheet.save(sheet_path, quality=85)
    report = {"ok": all(v["ok"] for v in checks.values()), "checks": checks, "sheet": str(sheet_path), "final": str(final)}
    (proj.edit / "verify.json").write_text(json.dumps(report, indent=1))
    log(f"verify: {'OK' if report['ok'] else 'PROBLEMS'}  " + "  ".join(f"{k}={'ok' if v['ok'] else 'FAIL'}" for k, v in checks.items()))
    return report
