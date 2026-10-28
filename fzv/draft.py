"""`fzv draft` (design §9f): a preview video of the whole edit before the final render.

The editor watches it on the review page together with the storyboard and approves once: the motion, the timing on the words and
the sound (voice, music, SFX) are those of the final; only the frame rate (`review.preview_fps`, default 10) and the picture quality
are lower, so it renders in a fraction of the time. Clips are rendered at the low rate into edit/draft/ (cached by content hash, so a
revision re-renders only the clips it changed), composited over the footage at 960x540 and muxed with the real mix:

  edit/review/preview.mp4    the preview        edit/review/preview.json   {build, fps, at}: which build it shows
"""
from __future__ import annotations

import json
import queue
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import beats as B
from . import media
from .finish import enable_expr
from .render import HF_ENV, hf_bin, stage_clip, worker_dir

W, H = 960, 540


def draft_path(proj, clip: dict) -> Path:
    return proj.edit / "draft" / f"{clip['id']}.{'mp4' if clip.get('opaque') else 'webm'}"


def render_clip(proj, clip: dict, fps: int, k: int, low_memory: bool) -> float:
    w = worker_dir(proj, k)
    stage_clip(proj, w, proj.edit / "built" / clip["html"])
    out = draft_path(proj, clip)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = hf_bin() + ["render", "--format", out.suffix[1:], "--quality", "draft", "--fps", str(fps), "-o", str(out)]
    if out.suffix == ".webm":
        cmd += ["--vp9-cpu-used", "8"]
    if low_memory:
        cmd.append("--low-memory-mode")
    t0 = time.time()
    for attempt in range(1, 4):
        with open(out.with_suffix(".log"), "w") as lf:
            p = subprocess.run(cmd, cwd=w, env=HF_ENV, stdout=lf, stderr=subprocess.STDOUT)
        if p.returncode == 0 and out.exists():
            break
        if attempt == 3:
            raise RuntimeError(f"draft render failed for {clip['id']} (see {out.with_suffix('.log')})")
        time.sleep(3)
    out.with_suffix(".hash").write_text(f"{clip['hash']}@{fps}")
    return round(time.time() - t0, 1)


def stale(proj, man: list[dict], fps: int) -> list[dict]:
    todo = []
    for c in man:
        out = draft_path(proj, c)
        h = out.with_suffix(".hash")
        if not (out.exists() and h.exists() and h.read_text().strip() == f"{c['hash']}@{fps}"):
            todo.append(c)
    return todo


def composite(proj, raw: Path, info: dict, man: list[dict], clips: list[dict], cuts: list[dict], compose: bool, out: Path) -> Path:
    """The preview picture, 960x540 at the draft rate x2.5 (the footage stays fluid; graphics hold between their draft frames)."""
    rate = 25
    if compose:                                                    # opaque section clips: just join them
        lst = proj.edit / "draft" / "list.txt"
        lst.write_text("".join(f"file '{draft_path(proj, c).name}'\n" for c in sorted(man, key=lambda c: c["start"])))
        media.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", f"scale={W}:{H},fps={rate}",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-pix_fmt", "yuv420p", "-an", out])
        return out
    by = {c["id"]: c for c in clips}
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", raw]
    fc, last = [f"[0:v]fps={rate},scale={W}:{H}[b]"], "[b]"
    for k, m in enumerate(sorted(man, key=lambda c: c["start"])):
        c = dict(by.get(m["id"], {}), **m)
        cmd += ["-c:v", "libvpx-vp9", "-i", draft_path(proj, m)]
        fc.append(f"[{k + 1}:v]setpts=PTS-STARTPTS+{m['start']:.3f}/TB,scale={W}:{H},fps={rate}[o{k}]")
        fc.append(f"{last}[o{k}]overlay=0:0:eof_action=pass:repeatlast=0:enable='{enable_expr(c, 0.0, info['duration'], cuts)}'[v{k}]")
        last = f"[v{k}]"
    cmd += ["-filter_complex", ";".join(fc), "-map", last, "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-pix_fmt", "yuv420p",
            "-an", "-t", f"{info['duration']:.3f}", out]
    media.run(cmd)
    return out


def preview_state(proj) -> str:
    """missing | stale (built again since) | ready."""
    f = proj.edit / "review" / "preview.json"
    sig = B.build_signature(proj)
    if not f.exists() or not sig or not (proj.edit / "review" / "preview.mp4").exists():
        return "missing"
    return "ready" if json.loads(f.read_text()).get("build") == sig else "stale"


def draft(proj, settings: dict, workers: int = 1, low_memory: bool = True, log=print) -> Path:
    from .audio import mix
    pdata = proj.load()
    raw = proj.folder / pdata["raw"]
    info = media.probe(raw)
    man = json.loads((proj.edit / "built" / "clips.json").read_text())
    clips = json.loads(proj.p("clips.json").read_text())
    cuts = json.loads(proj.p("cuts.json").read_text()) if proj.p("cuts.json").exists() else [{"kind": "plate", "start": 0, "end": info["duration"]}]
    fps = int((settings.get("review") or {}).get("preview_fps", 10))
    compose = (pdata.get("mode") == "compose")
    t0 = time.time()
    todo = sorted(stale(proj, man, fps), key=lambda c: -(c["end"] - c["start"]))
    if todo:
        log(f"draft: rendering {len(todo)} clip(s) at {fps} fps, {workers} worker(s)")
        free = queue.Queue()
        for k in range(workers):
            free.put(140 + k)

        def job(c):
            k = free.get()
            try:
                return c["id"], render_clip(proj, c, fps, k, low_memory)
            finally:
                free.put(k)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for f in as_completed([ex.submit(job, c) for c in todo]):
                cid, s = f.result()
                log(f"  draft {cid} in {s}s")
    else:
        log("draft: every clip is up to date")
    R = proj.edit / "review"
    R.mkdir(parents=True, exist_ok=True)
    video = proj.edit / "draft" / "video.mp4"
    composite(proj, raw, info, man, clips, cuts, compose, video)
    mix_wav = mix(proj, raw, info["duration"], settings, log)
    out = R / "preview.mp4"
    media.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", mix_wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
               "-t", f"{info['duration']:.3f}", "-movflags", "+faststart", out])
    from .audio import export_stems
    export_stems(proj, R)
    (R / "preview.json").write_text(json.dumps({"build": B.build_signature(proj), "fps": fps, "at": time.strftime("%Y-%m-%d %H:%M:%S")}))
    log(f"draft: preview video in {time.time() - t0:.0f}s -> {out}")
    return out
