"""`fzv doctor`: probe the machine and choose worker counts, transcription backend and encoder (design §5.1)."""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess

from . import media
from .config import REPO
from .transcribe import backend


def ram_gb() -> float:
    try:
        if platform.system() == "Darwin":
            return int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout) / 2**30
        with open("/proc/meminfo") as f:
            return int(f.readline().split()[1]) / 2**20
    except Exception:
        return 8.0


def probe(settings: dict) -> dict:
    cores = os.cpu_count() or 4
    ram = ram_gb()
    r = settings.get("render", {})
    workers = r.get("workers", "auto")
    if workers == "auto":
        workers = max(1, min(cores // 2, int((ram - r.get("reserve_gb", 2.0)) // max(0.5, r.get("ram_per_worker_gb", 1.0))), 6))
        if ram <= 8.5:
            workers = 1                                           # HyperFrames low-memory mode territory
    enc = media.encoders()
    hw = next((e for e in ("h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_vaapi") if e in enc), None)
    info = {
        "platform": f"{platform.system()} {platform.machine()}", "cores": cores, "ram_gb": round(ram, 1),
        "render_workers": int(workers), "low_memory": ram <= 8.5, "transcription": backend(), "hw_encoder": hw,
        "node": shutil.which("node") is not None, "ffmpeg": shutil.which("ffmpeg") is not None,
        "hyperframes": (REPO / "node_modules" / ".bin" / "hyperframes").exists(),
    }
    return info


def library() -> dict:
    """What the shared library holds (it ships with the repo; bin/setup checks it is complete)."""
    import re
    import yaml
    from .config import GLOBAL, RUNTIME
    y = lambda f, k: len((yaml.safe_load((GLOBAL / f).read_text()) or {}).get(k) or []) if (GLOBAL / f).exists() else 0
    cat = GLOBAL / "templates" / "catalogue.json"
    return {"templates": len(json.loads(cat.read_text())) if cat.exists() else 0,
            "registry animations": y("registry/manifest.yaml", "items"),
            "icons": len(re.findall(r"<symbol ", (RUNTIME / "icons.svg").read_text())),
            "props & characters": y("props/manifest.yaml", "assets"),
            "music tracks": y("music/manifest.yaml", "tracks"),
            "sound effects": y("sfx/manifest.yaml", "sounds"),
            "brand kits": len([d for d in (GLOBAL / "brand").iterdir() if (d / "brand.yaml").exists()])}


def report(info: dict) -> str:
    return json.dumps(info, indent=1)
