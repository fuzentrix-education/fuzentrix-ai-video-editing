"""ffmpeg / ffprobe helpers."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


def run(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run([str(c) for c in cmd], capture_output=capture, text=False)
    if check and p.returncode != 0:
        err = (p.stderr or b"").decode(errors="replace")[-2000:]
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str, cmd[:6]))} …\n{err}")
    return p


def probe(path: Path) -> dict:
    """Duration, fps, size and whether there is audio."""
    p = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,r_frame_rate,duration:format=duration", "-of", "json", path])
    d = json.loads(p.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    a = any(s.get("codec_type") == "audio" for s in d.get("streams", []))
    num, den = (v.get("r_frame_rate") or "25/1").split("/")
    return {"duration": float(d.get("format", {}).get("duration") or v.get("duration") or 0), "fps": round(float(num) / float(den or 1), 3),
            "width": int(v.get("width", 0)), "height": int(v.get("height", 0)), "audio": a}


def extract_audio(src: Path, dst: Path, rate: int, mono: bool, start: float | None = None, dur: float | None = None, codec: str = "pcm_s16le") -> Path:
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", src]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-vn", "-ar", str(rate)] + (["-ac", "1"] if mono else ["-ac", "2"]) + ["-c:a", codec, dst]
    run(cmd)
    return dst


def read_wav_mono(path: Path) -> tuple[np.ndarray, int]:
    import wave
    with wave.open(str(path)) as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype=np.int16 if sw == 2 else np.int32).astype(np.float32)
    x /= 32768.0 if sw == 2 else 2147483648.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    return x, sr


def frames(src: Path, fps: float, w: int, h: int, start: float | None = None, dur: float | None = None):
    """Yield low-res RGB frames (h, w, 3) uint8."""
    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", f"{max(0, start):.3f}"]
    cmd += ["-i", str(src)]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-vf", f"fps={fps},scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


def frame_png(src: Path, t: float, dst: Path, width: int | None = None) -> Path:
    vf = ["-vf", f"scale={width}:-1"] if width else []
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1", *vf, dst])
    return dst


def encoders() -> set[str]:
    p = run(["ffmpeg", "-hide_banner", "-encoders"], check=False)
    out = (p.stdout or b"").decode(errors="replace")
    return {ln.split()[1] for ln in out.splitlines() if len(ln.split()) > 1 and ln.strip()[:1] == "V"}


def loudness(path: Path) -> dict:
    p = run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], check=False)
    txt = (p.stderr or b"").decode(errors="replace")
    out = {}
    for ln in txt.splitlines()[::-1]:
        s = ln.strip()
        if s.startswith("I:") and "lufs" not in out:
            out["lufs"] = float(s.split()[1])
        if s.startswith("Peak:") and "peak" not in out:
            out["peak"] = float(s.split()[1])
        if len(out) == 2:
            break
    return out
