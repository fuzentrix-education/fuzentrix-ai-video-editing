"""`fzv finish` (overlay mode): composite the transparent clips onto the untouched raw cut, chunk by chunk, then concat and mux the mix.

- Plate clips show only during plate/corner shots, studio clips only during their studio shot: frame-exact `enable` windows.
- Chunks are cached by content hash, so a timestamped revision re-encodes only the chunks it touches.
- The encoder is chosen from the machine (VideoToolbox, NVENC, Quick Sync, VAAPI, else libx264).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import media


def encoder_args(available: set[str], prefer_hw: bool = True) -> list[str]:
    if prefer_hw and "h264_videotoolbox" in available:
        return ["-c:v", "h264_videotoolbox", "-b:v", "14M", "-maxrate", "20M", "-bufsize", "28M", "-profile:v", "high", "-allow_sw", "1"]
    if prefer_hw and "h264_nvenc" in available:
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19", "-b:v", "0", "-profile:v", "high"]
    if prefer_hw and "h264_qsv" in available:
        return ["-c:v", "h264_qsv", "-global_quality", "20", "-profile:v", "high"]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", "17", "-profile:v", "high"]


def chunk_bounds(duration: float, clips: list[dict], fps: int, max_len: float = 240.0) -> list[tuple[float, float]]:
    pts = {0.0, round(duration, 3)}
    for c in clips:
        if c["layer"] == "plate":
            pts.update({c["start"], c["end"]})
    pts = sorted(p for p in pts if 0 <= p <= duration)
    out = []
    for a, b in zip(pts, pts[1:]):
        if b - a < 0.2:
            continue
        n = max(1, int((b - a) // max_len) + (1 if (b - a) % max_len > 1 else 0))
        step = round((b - a) / n * fps) / fps
        cur = a
        for i in range(n):
            nxt = b if i == n - 1 else round(cur + step, 3)
            out.append((round(cur, 3), round(nxt, 3)))
            cur = nxt
    return out


def enable_expr(clip: dict, a: float, b: float, cuts: list[dict]) -> str:
    if clip["layer"] == "studio":
        s, e = clip["cut"]
        return f"between(t\\,{max(0, s - a):.3f}\\,{min(b, e) - a - 0.0005:.3f})"
    studio = [(max(a, c["start"]) - a, min(b, c["end"]) - a) for c in cuts if c["kind"] == "studio" and c["end"] > a and c["start"] < b]
    within = f"between(t\\,{max(0, clip['start'] - a):.3f}\\,{min(b, clip['end']) - a - 0.0005:.3f})"
    if not studio:
        return within
    return within + "*not(" + "+".join(f"between(t\\,{s:.3f}\\,{e - 0.0005:.3f})" for s, e in studio) + ")"


def encode_chunk(proj, raw: Path, a: float, b: float, members: list[dict], cuts: list[dict], src_fps: float, enc: list[str], idx: int, log=print) -> Path:
    key = json.dumps([str(raw), raw.stat().st_mtime, a, b, src_fps, enc, [(m["id"], m["hash"], m["start"], m["end"]) for m in members],
                      [(c["kind"], c["start"], c["end"]) for c in cuts if c["end"] > a and c["start"] < b]])
    h = hashlib.sha256(key.encode()).hexdigest()[:12]
    D = proj.edit / "out" / "chunks"
    D.mkdir(parents=True, exist_ok=True)
    out = D / f"{idx:03d}_{h}.mp4"
    if out.exists():
        log(f"  chunk {idx:03d} {a:8.2f}-{b:8.2f}s  cached")
        return out
    for old in D.glob(f"{idx:03d}_*.mp4"):
        old.unlink()
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", raw]
    fc, last = [], "[0:v]"
    for k, m in enumerate(members):
        seek = max(0.0, a - m["start"])
        cmd += ["-ss", f"{seek:.3f}", "-c:v", "libvpx-vp9", "-i", proj.edit / "out" / f"{m['id']}.webm"]
        delay = max(0.0, m["start"] - a)
        fc.append(f"[{k + 1}:v]setpts=PTS-STARTPTS+{delay:.3f}/TB,fps={src_fps}[o{k}]")
        fc.append(f"{last}[o{k}]overlay=0:0:eof_action=pass:repeatlast=0:enable='{enable_expr(m, a, b, cuts)}'[v{k}]")
        last = f"[v{k}]"
    if members:
        cmd += ["-filter_complex", ";".join(fc), "-map", last]
    else:
        cmd += ["-map", "0:v"]
    cmd += [*enc, "-pix_fmt", "yuv420p", "-r", f"{src_fps}", "-g", str(int(src_fps * 2)), "-an", "-t", f"{b - a:.3f}", out]
    media.run(cmd)
    log(f"  chunk {idx:03d} {a:8.2f}-{b:8.2f}s  encoding ({len(members)} overlay clip(s))")
    return out


def finish(proj, raw: Path, info: dict, clips: list[dict], cuts: list[dict], mix_wav: Path, out_path: Path, settings: dict, log=print) -> Path:
    fps = settings.get("graphics_fps", 25)
    enc = encoder_args(media.encoders(), settings.get("render", {}).get("hw_encode", True))
    log(f"finish: encoder {enc[1]}")
    bounds = chunk_bounds(info["duration"], clips, fps)
    parts = []
    for i, (a, b) in enumerate(bounds):
        members = [c for c in clips if c["start"] < b and c["end"] > a and (proj.edit / "out" / f"{c['id']}.webm").exists()]
        parts.append(encode_chunk(proj, raw, a, b, members, cuts, info["fps"], enc, i, log))
    lst = proj.edit / "out" / "chunks" / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    video = proj.edit / "out" / "video.mp4"
    media.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video])
    proj.archive_previous(out_path)
    a_cfg = settings["output"]["audio"]
    media.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", mix_wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", a_cfg["codec"], "-b:a", a_cfg["bitrate"],
               "-ar", str(a_cfg["rate"]), "-t", f"{info['duration']:.3f}", "-map_metadata", "-1", "-movflags", "+faststart", out_path])
    log(f"finish: wrote {out_path}")
    return out_path


def write_srt(cues: list[dict], path: Path):
    def ts(t):
        h, r = divmod(t, 3600); m, s = divmod(r, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"
    path.write_text("".join(f"{i + 1}\n{ts(c['at'])} --> {ts(c['until'])}\n{c['text']}\n\n" for i, c in enumerate(cues)), encoding="utf-8")
