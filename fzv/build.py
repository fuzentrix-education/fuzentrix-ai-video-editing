"""Compile planned clips into standalone HyperFrames compositions (edit/built/<clip>.html) with shared assets in edit/comp/assets."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import yaml

from . import media
from .config import GLOBAL, RUNTIME, brand_css, brand_js, dump_json, load_brand, load_yaml

TEMPLATE_FILES = ["core.js", "code.js", "content.js", "explainer.js", "registry.js", "props.js", "sketch.js", "presenter.js"]

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width=1920, height=1080" />
<script src="assets/runtime/vendor/gsap.min.js"></script><script src="assets/runtime/lib.js"></script>
{template_tags}
<link rel="stylesheet" href="assets/runtime/base.css" /><link rel="stylesheet" href="assets/brand.css" /></head>
<body>
{icons}
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="1920" data-height="1080" data-fps="{fps}">{static}</div>
<script>
window.FZ_PROPS = {props};
window.FZ_RECORDINGS = {recs};
(function () {{
  const api = FZ.create({{ offset: {off}, duration: {dur}, brand: {brand}, layout: {layout} }});
  api.run({scenes});
  window.__timelines = window.__timelines || {{}};
  window.__timelines["main"] = api.tl;
}})();
</script>
</body></html>
"""

REC_MARKUP = """<div id="rec-{id}" class="fz-rec hide"><div class="bar"><div class="dot" style="background:#FF6058"></div><div class="dot" style="background:#FFBD2E"></div><div class="dot" style="background:#28CA42"></div>
<div class="ttl" style="margin-left:16px;font:500 18px/1 var(--fz-font-mono);color:var(--fz-text2)"></div><div class="fz-steps"></div>
<div style="margin-left:28px;display:flex;align-items:center;gap:8px;font:700 15px/1 var(--fz-font-mono);letter-spacing:.14em;color:var(--fz-danger)"><span style="width:10px;height:10px;border-radius:50%;background:var(--fz-danger);display:block"></span>SCREEN</div></div>
<div class="view"><div class="cam" style="width:{w}px;height:{h}px"><video id="rec-video-{id}" src="assets/rec/{file}" muted playsinline data-start="{start}" data-duration="{dur}" data-track-index="1" style="width:{w}px;height:{h}px"></video></div></div></div>"""


def link_or_copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if dst.stat().st_size == src.stat().st_size:
            return
        dst.unlink()
    try:
        dst.hardlink_to(src)
    except OSError:
        shutil.copy2(src, dst)


def prepare_assets(proj, brand: dict) -> Path:
    """edit/comp/assets: runtime, brand.css + fonts, brand logo and plate. Idempotent."""
    A = proj.edit / "comp" / "assets"
    for f in ["lib.js", "base.css"] + [f"templates/{t}" for t in TEMPLATE_FILES] + ["vendor/gsap.min.js"]:
        link_or_copy(RUNTIME / f, A / "runtime" / f)
        if (A / "runtime" / f).stat().st_mtime < (RUNTIME / f).stat().st_mtime:     # runtime edited: refresh the copy
            (A / "runtime" / f).unlink(); shutil.copy2(RUNTIME / f, A / "runtime" / f)
    shared = Path(brand["_shared"])
    for f in (shared / "fonts").glob("*.woff2"):
        link_or_copy(f, A / "fonts" / f.name)
    bug = Path(brand["_dir"]) / brand.get("bug", {}).get("logo", "")
    if bug.is_file():
        link_or_copy(bug, A / "brand" / bug.name)
    plate = (Path(brand["_dir"]) / brand.get("plate", "")) if brand.get("plate") else None
    plate = plate if plate and plate.is_file() else shared / "plate" / "slide_background.png"
    link_or_copy(plate, A / "brand" / "plate.png")
    (A / "brand.css").write_text(brand_css(brand, "fonts/"), encoding="utf-8")
    reg = GLOBAL / "registry"                                # vendored HyperFrames registry items (the `hf` template)
    for f in reg.rglob("*"):
        if f.is_file() and f.suffix in (".html", ".woff2", ".woff", ".ttf", ".png", ".svg", ".json", ".jpg", ".webp", ".js", ".css", ".mp3", ".wav"):
            rel = f.relative_to(reg)
            link_or_copy(f, A / Path(*rel.parts[1:]) if rel.parts[0] == "_assets" else A / "registry" / rel)
    link = proj.edit / "built" / "assets"                   # built pages load directly (sampler, previews)
    if not link.exists():
        link.symlink_to(Path("..") / "comp" / "assets")
    return A


def props_used(clip: dict) -> set[str]:
    ids = set()
    for s in clip["scenes"]:
        p = s["params"]
        if s["template"] in ("prop", "prop-move", "sketch-draw") and p.get("asset"):
            ids.add(p["asset"])
        if s["template"] == "prop-scene":
            ids.update(pr["asset"] for pr in p.get("props", []) if pr.get("asset"))
    return ids


def props_js(ids: set[str]) -> dict:
    lib = GLOBAL / "props" / "svg"
    out = {}
    for i in sorted(ids):
        f = lib / f"{i}.svg"
        if f.exists():
            out[i] = f.read_text(encoding="utf-8").strip()
    return out


def recording_assets(proj, clip: dict, recordings: dict, A: Path, fps: int) -> tuple[str, dict]:
    """Trim each recording a clip uses to the clip's window (25 fps, H.264) and emit its static markup."""
    markup, recs = [], {}
    for s in clip["scenes"]:
        if s["template"] != "recording-window":
            continue
        rid = s["params"]["id"]
        r = recordings.get(rid)
        if not r:
            raise SystemExit(f"clip {clip['id']}: recording '{rid}' is not listed in the spec's recordings")
        src = (proj.folder / r["file"]).resolve()
        info = media.probe(src)
        in_rec = max(0.0, clip["start"] - r["offset"])
        local = max(0.0, r["offset"] - clip["start"])
        dur = max(0.04, min(info["duration"] - in_rec, clip["end"] - clip["start"] - local))
        name = f"{rid}_{clip['id']}_{in_rec:.2f}_{dur:.2f}.mp4"
        dst = A / "rec" / name
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            media.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{in_rec:.3f}", "-i", src, "-t", f"{dur:.3f}", "-an", "-r", str(fps), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", dst])
        crop = r.get("crop") or [0, 0, info["width"], info["height"]]
        markup.append(REC_MARKUP.format(id=rid, w=info["width"], h=info["height"], file=name, start=f"{local:.2f}", dur=f"{dur:.2f}"))
        recs[rid] = {"w": crop[2], "h": crop[3], "crop": crop}
    return "\n".join(markup), recs


def registry_hosts(clip: dict) -> str:
    """Static hosts for `hf` scenes: HyperFrames mounts each registry item into its box at its time."""
    from .registry import host_markup, manifest
    items = {x["name"]: x for x in manifest()}
    out = []
    for k, s in enumerate(clip["scenes"]):
        if s["template"] != "hf":
            continue
        p = s["params"]
        it = items.get(p.get("item"))
        if not it:
            raise SystemExit(f"clip {clip['id']}: registry item '{p.get('item')}' is not installed (fzv registry add {p.get('item')})")
        at = float(p["at"]); end = float(p["until"]) if p.get("until") is not None else clip["end"] - 0.1
        vars_ = dict(p.get("vars") or {})
        if any(v["id"] == "accent" for v in it.get("variables", [])):
            vars_.setdefault("accent", "blue")               # closest registry accent to the brand blues
        if p.get("cues"):                                    # word-anchored cue times -> seconds from the mount's start
            vars_["cues"] = ",".join(f"{max(0.0, float(t) - at):.2f}" for t in p["cues"])
        box = dict({"x": 96, "y": 230, "w": 1000, "h": 560}, **(p.get("box") or {}))
        hid = f"hf{k}-{p['item']}"
        p["_host"] = hid
        out.append(host_markup(hid, it, at - clip["start"], max(0.2, end - at), box, vars_, p.get("css")))
    return "\n".join(out)


def build_clip(proj, clip: dict, brand: dict, layout: dict, recordings: dict, fps: int, A: Path) -> Path:
    static, recs = recording_assets(proj, clip, recordings, A, fps)
    static = clip.get("static", "") + static + registry_hosts(clip)
    html = PAGE.format(
        template_tags="".join(f'<script src="assets/runtime/templates/{t}"></script>' for t in TEMPLATE_FILES),
        icons=(RUNTIME / "icons.svg").read_text(encoding="utf-8"), static=static,
        dur=round(clip["end"] - clip["start"], 3), fps=fps, off=clip["start"],
        props=dump_json(props_js(props_used(clip))), recs=dump_json(recs),
        brand=dump_json(brand_js(brand)), layout=dump_json(layout), scenes=dump_json(clip["scenes"]),
    )
    out = proj.edit / "built" / f"{clip['id']}.html"
    out.write_text(html, encoding="utf-8")
    return out


def template_files(A: Path) -> dict[str, Path]:
    """Template name -> the runtime file that registers it."""
    out = {}
    for f in sorted((A / "runtime" / "templates").glob("*.js")):
        for name in re.findall(r'name:\s*"([a-z0-9-]+)"', f.read_text(encoding="utf-8")):
            out.setdefault(name, f)
    return out


def clip_hash(html_path: Path, A: Path, clip: dict | None = None) -> str:
    """Content hash of a clip: its HTML, the runtime core and brand CSS, the template files that define the templates it uses,
    and every media file it plays (size + mtime, so a re-keyed presenter or a replaced recording re-renders)."""
    html = html_path.read_bytes()
    h = hashlib.sha256(html)
    used = {s["template"] for s in (clip or {}).get("scenes", [])}
    tf = template_files(A)
    files = [A / "runtime" / "lib.js", A / "runtime" / "base.css", A / "runtime" / "icons.svg", A / "brand.css"]
    files += sorted({tf[t] for t in used if t in tf}) if clip else sorted((A / "runtime" / "templates").glob("*.js"))
    for f in files:
        if f.is_file():
            h.update(f.name.encode()); h.update(f.read_bytes())
    for ref in sorted(set(re.findall(rb'src="assets/([^"]+)"', html))):
        f = A / ref.decode()
        if f.is_file():
            st = f.stat()
            h.update(ref); h.update(f"{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()[:16]


def build(proj, spec_resolved: dict, clips: list[dict], settings: dict) -> list[dict]:
    brand = load_brand(spec_resolved.get("brand") or settings["brand"])
    A = prepare_assets(proj, brand)
    pdata = proj.load()
    layout = pdata.get("layout") or settings["layout"]
    fps = settings.get("graphics_fps", 25)
    recordings = {r["id"]: r for r in (spec_resolved.get("recordings") or [])}
    for r in (pdata.get("recordings") or []):
        recordings.setdefault(r["id"], r)
    manifest = []
    for c in clips:
        html = build_clip(proj, c, brand, layout, recordings, fps, A)
        manifest.append({k: c[k] for k in ("id", "layer", "start", "end")} | {"html": html.name, "hash": clip_hash(html, A, c), "frames": round((c["end"] - c["start"]) * fps), "opaque": bool(c.get("opaque"))})
    with open(proj.edit / "built" / "clips.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    return manifest
