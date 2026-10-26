"""Render clips with HyperFrames: one small project per worker (sharing edit/comp/assets), parallel, cached by content hash."""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .config import REPO

HF_ENV = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1", HYPERFRAMES_SKIP_SKILLS="1", DO_NOT_TRACK="1")


def hf_bin() -> list[str]:
    local = REPO / "node_modules" / ".bin" / "hyperframes"
    return [str(local)] if local.exists() else ["npx", "--yes", "hyperframes@0.8.162"]


def worker_dir(proj, k: int) -> Path:
    """A HyperFrames project folder for worker k: config files + an `assets` symlink to the shared assets."""
    w = proj.edit / "comp" / f"w{k}"
    w.mkdir(parents=True, exist_ok=True)
    (w / "hyperframes.json").write_text(json.dumps({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}, "media": {"autoProxy": True}}, indent=1))
    (w / "meta.json").write_text(json.dumps({"id": f"fzv-w{k}", "name": f"fzv-w{k}", "createdAt": "2026-10-25T00:00:00.000Z"}))
    (w / "package.json").write_text(json.dumps({"name": f"fzv-w{k}", "private": True, "type": "module"}))
    link = w / "assets"
    if not link.exists():
        link.symlink_to(Path("..") / "assets")
    return w


def stage_clip(proj, w: Path, html: Path) -> None:
    """Copy a built clip in as the worker's index.html, with exactly the registry sub-compositions it mounts (they must really
    live inside the project: HyperFrames won't read them through the assets symlink, and unused ones confuse its entry check)."""
    import re
    from .build import link_or_copy
    from .config import GLOBAL
    shutil.copy2(html, w / "index.html")
    shutil.rmtree(w / "compositions", ignore_errors=True)
    for rel in set(re.findall(r'data-composition-src="compositions/registry/([^"]+)"', html.read_text(encoding="utf-8"))):
        link_or_copy(GLOBAL / "registry" / rel, w / "compositions" / "registry" / rel)


def render_one(proj, clip: dict, k: int, low_memory: bool) -> dict:
    w = worker_dir(proj, k)
    stage_clip(proj, w, proj.edit / "built" / clip["html"])
    ext = "mp4" if clip.get("opaque") else "webm"                 # compose clips are full frames; overlay clips keep alpha
    out = proj.edit / "out" / f"{clip['id']}.{ext}"
    log = proj.edit / "out" / f"{clip['id']}.log"
    cmd = hf_bin() + ["render", "--format", ext, "--quality", "delivery", "-o", str(out)]
    if low_memory:
        cmd.append("--low-memory-mode")
    t0 = time.time()
    for attempt in range(1, 4):                     # Chrome can drop a page under memory pressure; retry before failing
        with open(log, "w") as lf:
            p = subprocess.run(cmd, cwd=w, env=HF_ENV, stdout=lf, stderr=subprocess.STDOUT)
        if p.returncode == 0 and out.exists():
            break
        if attempt == 3:
            raise RuntimeError(f"render failed for {clip['id']} after 3 attempts (see {log})")
        time.sleep(3)
    (proj.edit / "out" / f"{clip['id']}.hash").write_text(clip["hash"])
    return {"id": clip["id"], "seconds": round(time.time() - t0, 1)}


def snapshot(proj, clip: dict, local_times: list[float], out_dir: Path, k: int = 99) -> Path:
    w = worker_dir(proj, k)
    stage_clip(proj, w, proj.edit / "built" / clip["html"])
    shutil.rmtree(out_dir, ignore_errors=True)
    cmd = hf_bin() + ["snapshot", "--at", ",".join(f"{t:.3f}" for t in local_times), "--no-end", "--describe", "false", "--keep", "-o", str(out_dir)]
    p = subprocess.run(cmd, cwd=w, env=HF_ENV, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"snapshot failed: {p.stderr[-1500:]}")
    return out_dir


def lint(proj, clip: dict, k: int = 98) -> str:
    w = worker_dir(proj, k)
    stage_clip(proj, w, proj.edit / "built" / clip["html"])
    p = subprocess.run(hf_bin() + ["lint"], cwd=w, env=HF_ENV, capture_output=True, text=True)
    return (p.stdout + p.stderr)[-3000:]


def stale(proj, clips: list[dict]) -> list[dict]:
    todo = []
    for c in clips:
        out, h = proj.edit / "out" / f"{c['id']}.{'mp4' if c.get('opaque') else 'webm'}", proj.edit / "out" / f"{c['id']}.hash"
        if not (out.exists() and h.exists() and h.read_text().strip() == c["hash"]):
            todo.append(c)
    return todo


def render(proj, clips: list[dict], workers: int, low_memory: bool, only: list[str] | None = None, log=print) -> list[dict]:
    todo = [c for c in stale(proj, clips) if not only or c["id"] in only]
    if not todo:
        log("render: everything up to date")
        return []
    todo.sort(key=lambda c: -c["frames"])          # longest first keeps workers busy
    log(f"render: {len(todo)} clip(s), {sum(c['frames'] for c in todo)} frames, {workers} worker(s)")
    done = []
    free = queue.Queue()
    for k in range(workers):
        free.put(k)

    def job(c):
        k = free.get()                              # each worker folder is used by one render at a time
        try:
            return render_one(proj, c, k, low_memory)
        finally:
            free.put(k)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(job, c): c for c in todo}
        for f in as_completed(futs):
            r = f.result()
            done.append(r)
            log(f"  rendered {r['id']} in {r['seconds']}s")
    return done
