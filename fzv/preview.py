"""Preview: snapshot a clip at chosen global times and composite the overlay onto the matching raw-cut frames (a contact sheet)."""
from __future__ import annotations

import io
import subprocess
from pathlib import Path

from PIL import Image

from .render import snapshot


def raw_frame(src: Path, t: float) -> Image.Image:
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    return Image.open(io.BytesIO(b)).convert("RGBA")


def preview(proj, clip: dict, times: list[float], raw: Path | None, tile_w: int = 960) -> Path:
    local = [max(0.0, t - clip["start"]) for t in times]
    snap = snapshot(proj, clip, local, proj.edit / "out" / f"snap_{clip['id']}")
    tiles = []
    for t, lt in zip(times, local):
        f = snap / f"at-{('%.3f' % lt).rstrip('0').rstrip('.')}s.png"
        ov = Image.open(f).convert("RGBA")
        base = raw_frame(raw, t).resize(ov.size) if raw else Image.new("RGBA", ov.size, (243, 247, 253, 255))
        tiles.append(Image.alpha_composite(base, ov).convert("RGB").resize((tile_w, tile_w * 9 // 16)))
    cols = 2 if len(tiles) > 1 else 1
    rows = (len(tiles) + cols - 1) // cols
    th = tile_w * 9 // 16
    sheet = Image.new("RGB", (cols * tile_w + (cols - 1) * 6, rows * th + (rows - 1) * 6), (20, 20, 20))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * (tile_w + 6), (i // cols) * (th + 6)))
    out = proj.edit / "out" / f"preview_{clip['id']}.jpg"
    sheet.save(out, quality=88)
    return out
