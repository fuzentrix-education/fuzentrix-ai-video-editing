"""Compose mode (design §4, §12.2): raw instructor footage, no editor's layout.

ingest  - pick a background model, find the instructor's crop, key the whole video to edit/comp/assets/presenter.webm
build   - every section becomes a full opaque clip: brand plate + presenter (poses from the spec, rule L5) + graphics
finish  - render clips as MP4, concat, mux the mix
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from . import media
from .build import TEMPLATE_FILES, build as build_clips, link_or_copy, prepare_assets

PRESENTER_MARKUP = """<div class="abs" style="left:0;top:0;width:1920px;height:1080px;background:url('assets/brand/plate.png') center/cover"></div>
<div id="fz-bg" class="abs" style="left:0;top:0;width:1920px;height:1080px"></div>
<div id="fz-presenter" class="abs" style="left:0;top:0;width:{w}px;height:{h}px"><video id="fz-presenter-video" src="assets/presenter/{file}" muted playsinline data-start="0" data-playback-start="{offset}" data-duration="{dur}" data-track-index="0" style="width:{w}px;height:{h}px;filter:drop-shadow(0 18px 34px rgba(13,39,76,.28))"></video></div>"""


def key_options(proj) -> dict:
    """Keyer options from edit.yaml `key:` (or project.yaml): {exclude: [[x, y, w, h]...], cut_below: y}."""
    if proj.spec_path.exists():
        k = (yaml.safe_load(proj.spec_path.read_text()) or {}).get("key")
        if k:
            return k
    return proj.load().get("key") or {}


def ingest(proj, raw: Path, info: dict, log=print, rekey: bool = False, fps: int = 25) -> dict:
    from .keyer import background, crop_box, key_video
    opts = key_options(proj)
    mode, plate = background(raw, info, log)
    crop = crop_box(raw, info, plate, mode, opts)
    out = proj.edit / "comp" / "assets" / "presenter" / "presenter.webm"
    out.parent.mkdir(parents=True, exist_ok=True)
    if rekey:
        for f in out.parent.glob("presenter*.webm"):
            f.unlink()
    if ((proj.settings().get("presenter") or {}).get("source", "studio")) == "studio":
        # the roomy box keying (her hands and the laptop stay); studio shots are keyed at build, only for their stretches
        key_box(proj, raw, fps, log)
    elif not out.exists():
        key_video(raw, out, info, plate, mode, crop, fps, log, opts)      # the render rate: no judder from 25 -> 30 fps
    return {"key_mode": mode, "crop": crop, "file": out.name, "key": opts, "fps": fps}


def presenter_source(proj, settings: dict | None = None) -> tuple[str, list[int]]:
    """(file, crop) of the keyed video the presenter plays. With `presenter.source: studio`: the whole studio keying if it exists, else
    the box keying (her and the laptop's near end, the whole video; studio shots then come from short studio keyings); else the cut-out."""
    settings = settings or proj.settings()
    pdata = proj.load()
    P = proj.edit / "comp" / "assets" / "presenter"
    if (settings.get("presenter") or {}).get("source", "studio") == "studio":
        name = f"studio_0.00_{float(pdata['duration']):.2f}.webm"
        if (P / name).exists():
            return name, STUDIO_CROP
        if (P / "presenter_box.webm").exists():
            return "presenter_box.webm", BOX_CROP
    return "presenter.webm", pdata["compose"]["crop"]


def key_box(proj, raw: Path, fps: int, log=print) -> str:
    """Key what the roomy box shows (BOX_CROP, nothing cut away: her hands and the laptop stay) for the whole video."""
    from .keyer import background, key_video
    out = proj.edit / "comp" / "assets" / "presenter" / "presenter_box.webm"
    if not out.exists():
        info = media.probe(raw)
        mode, plate = background(raw, info, log)
        key_video(raw, out, info, plate, mode, BOX_CROP, fps, log, {})
    return out.name


def occupancy(proj, cell: int = 40, settings: dict | None = None) -> list[list[int]]:
    """Cells [x0, y0, x1, y1] (keyed-video pixels) where the instructor (and, in the studio keying, her laptop and desk) ever
    appears: the union of the alpha over the video. Cached in edit/comp; validate maps it through the live pose (rule L2)."""
    import numpy as np
    file, crop = presenter_source(proj, settings)
    cache = proj.edit / "comp" / f"occupancy_{Path(file).stem}.json"
    src = proj.edit / "comp" / "assets" / "presenter" / file
    if cache.exists() and src.exists() and cache.stat().st_mtime >= src.stat().st_mtime:
        return json.loads(cache.read_text())
    _, _, w, h = crop
    gw, gh = max(1, w // cell), max(1, h // cell)
    out = subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(src), "-vf", f"fps=1,alphaextract,scale={gw}:{gh}:flags=area",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    fr = np.frombuffer(out, np.uint8)[: len(out) // (gw * gh) * gw * gh].reshape(-1, gh, gw)
    occ = (fr > 40).any(0) if len(fr) else np.zeros((gh, gw), bool)
    cells = [[int(x * w / gw), int(y * h / gh), int((x + 1) * w / gw), int((y + 1) * h / gh)] for y, x in zip(*np.nonzero(occ))]
    cache.write_text(json.dumps(cells))
    return cells


STUDIO_CROP = [160, 260, 1600, 820]        # the studio shot: her, the laptop and the desk (source pixels); edges fade into the backdrop
BOX_CROP = [600, 260, 920, 780]             # what the roomy corner box shows: her and the near end of the laptop (keyed for the whole video)
STUDIO_MARKUP = """<div id="fz-studio-{k}" class="abs" style="left:0;top:0;width:{w}px;height:{h}px;opacity:0;visibility:hidden;-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 9%,#000 91%,transparent 100%);mask-image:linear-gradient(90deg,transparent 0,#000 9%,#000 91%,transparent 100%)"><video id="fz-studio-video-{k}" src="assets/presenter/{file}" muted playsinline data-start="{start}" data-playback-start="{offset}" data-duration="{dur}" data-track-index="{track}" style="width:{w}px;height:{h}px"></video></div>"""


def studio_spans(poses: list[dict], duration: float) -> list[tuple[float, float]]:
    """Stretches in the `studio` pose (the intro, a chapter opener), each with 1.2 s more for the move out of it."""
    ps = sorted(poses, key=lambda q: q["at"])
    return [(q["at"], min(duration, (ps[i + 1]["at"] if i + 1 < len(ps) else duration) + 1.2)) for i, q in enumerate(ps) if q.get("name") == "studio"]


def key_studio(proj, raw: Path, span: tuple[float, float], fps: int, log=print) -> str:
    """Key one studio stretch with the laptop and desk kept (no exclude areas): her studio shot, on the kit's backdrop (rule L11)."""
    from .keyer import background, key_video
    name = f"studio_{span[0]:.2f}_{span[1]:.2f}.webm"
    out = proj.edit / "comp" / "assets" / "presenter" / name
    if not out.exists():
        info = media.probe(raw)
        mode, plate = background(raw, info, log)
        key_video(raw, out, info, plate, mode, STUDIO_CROP, fps, log, {}, span=span)
    return name


def trimmed_presenter(proj, clip: dict) -> str:
    src = proj.edit / "comp" / "assets" / "presenter" / "presenter.webm"
    name = f"presenter_{clip['id']}_{clip['start']:.2f}_{clip['end'] - clip['start']:.2f}.webm"
    dst = src.parent / name
    if not dst.exists():
        media.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{clip['start']:.3f}", "-c:v", "libvpx-vp9", "-i", src, "-t", f"{clip['end'] - clip['start']:.3f}",
                   "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-crf", "22", "-b:v", "0", "-row-mt", "1", "-deadline", "good", "-cpu-used", "5", dst])
    return name


def build_compose(proj, settings, pdata, sp, cuts, tx, log) -> int:
    from . import spec as S
    comp = pdata.get("compose")
    if not comp:
        raise SystemExit("compose mode: run `fzv ingest` first (it keys the instructor)")
    res, errs = S.resolve(sp, tx, pdata["duration"])
    if not errs:
        from .execute import apply as run_programs
        errs = run_programs(res, proj.p("runs"))
    if errs:
        for e in errs:
            log(f"  {e}")
        return 1
    with open(proj.p("edit.resolved.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(res, f, sort_keys=False, allow_unicode=True)
    clips = S.plan_clips(res, [{"kind": "plate", "start": 0, "end": pdata["duration"]}], settings["graphics_fps"],
                         [l for l in ("plate",) if l in (settings.get("bug") or {}).get("layers", [])], settings.get("chrome"), pdata["duration"])
    poses = (res.get("presenter") or {}).get("poses") or [{"name": "wide", "at": 0}]
    pset = dict(settings.get("presenter") or {})
    pset.update({k: v for k, v in (res.get("presenter") or {}).items() if k != "poses"})   # the spec may override per video
    box = pset.get("box") if pset.get("corner_box", True) else None
    raw = proj.folder / pdata["raw"]
    pfile, pcrop = presenter_source(proj, settings)
    studio_src = pfile.startswith("studio_")              # one keying of the whole studio: every pose (and the box) comes from it
    roomy = pfile != "presenter.webm"                      # the box shows her freely, with the laptop (studio or box keying)
    spans = [] if studio_src else [(s, key_studio(proj, raw, s, comp.get("fps", 25), log)) for s in studio_spans(poses, pdata["duration"])]
    for c in clips:
        studio, extra = [], ""
        for k, ((t0, t1), file) in enumerate(spans):
            a0, a1 = max(t0, c["start"]), min(t1, c["end"])
            if a1 - a0 > 0.05:                             # this clip shows (part of) a studio stretch: its own keyed video
                studio.append({"t0": t0, "t1": t1, "el": f"fz-studio-{k}", "crop": STUDIO_CROP})
                extra += STUDIO_MARKUP.format(k=k, w=STUDIO_CROP[2], h=STUDIO_CROP[3], file=file, start=round(a0 - c["start"], 3),
                                              offset=round(a0 - t0, 3), dur=round(a1 - a0, 3), track=1 + k)
        c["scenes"].insert(0, {"template": "presenter", "params": {"poses": poses, "crop": pcrop, "box": box, "studio": studio,
                                                                   **({"free": pset.get("free")} if roomy else {})}})
        # every section plays the one keyed video from its own start (data-playback-start): no per-section re-encode
        mk = PRESENTER_MARKUP.format(w=pcrop[2], h=pcrop[3], file=pfile, offset=round(c["start"], 3), dur=round(c["end"] - c["start"], 3))
        if roomy:                                          # no shadowed cut-out edge; a studio keying's desk fades out at its ends
            mk = mk.replace(";filter:drop-shadow(0 18px 34px rgba(13,39,76,.28))", "").replace(
                'id="fz-presenter" class="abs" style="', 'id="fz-presenter" class="abs" style="-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 9%,#000 91%,transparent 100%);mask-image:linear-gradient(90deg,transparent 0,#000 9%,#000 91%,transparent 100%);')
        c["static"] = mk + extra
        c["opaque"] = True
    man = build_clips(proj, res, clips, settings)
    proj.p("clips.json").write_text(json.dumps(clips, indent=1))
    from .cli import write_decisions
    write_decisions(proj, sp, settings, res)
    proj.stage_done("build", clips=len(man), mode="compose")
    log(f"build (compose): {len(man)} clip(s)")
    return 0


def finish_compose(proj, info: dict, clips: list[dict], mix_wav: Path, out_path: Path, settings: dict, log=print) -> Path:
    parts = [proj.edit / "out" / f"{c['id']}.mp4" for c in sorted(clips, key=lambda c: c["start"])]
    missing = [p.name for p in parts if not p.exists()]
    if missing:
        raise SystemExit(f"finish (compose): render these clips first: {missing}")
    lst = proj.edit / "out" / "compose_list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    video = proj.edit / "out" / "video.mp4"
    media.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video])
    proj.archive_previous(out_path)
    a = settings["output"]["audio"]
    media.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", mix_wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", a["codec"], "-b:a", a["bitrate"],
               "-ar", str(a["rate"]), "-t", f"{info['duration']:.3f}", "-map_metadata", "-1", "-movflags", "+faststart", out_path])
    log(f"finish (compose): wrote {out_path}")
    return out_path
