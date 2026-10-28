"""`fzv studio` (design §9g): the whole edit as one HyperFrames project, played live in HyperFrames Studio (`hyperframes preview`).

Made only when the editor asks for it or as the preview before the final render. No rendering: Studio plays the scenes in the
browser over the footage, with the sound as two tracks (voice + SFX, and music, which can be muted in Studio's timeline).

  edit/studio/index.html                 root composition: footage (rough cuts) + one host per built clip at its time + audio tracks
  edit/studio/compositions/<clip>.html    each built clip as a sub-composition (<template>, its own composition id and timeline)
  edit/studio/assets -> ../comp/assets    the clips' shared assets; media/ holds the footage and the audio tracks

View-only: changes made in Studio's panels are not carried back into edit.yaml (the review page and the chat stay the way to change it).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from . import beats as B
from . import media
from .config import REPO
from .render import HF_ENV, hf_bin

# Studio keeps a registry of running previews under XDG_STATE_HOME; keep it inside the repo (git-ignored .hyperframes/), so it works
# on locked-down machines too
STUDIO_ENV = dict(HF_ENV, XDG_STATE_HOME=str(REPO / ".hyperframes" / "state"))


ICONS = re.compile(r'<svg width="0" height="0" style="position:absolute"><defs>.*?</defs></svg>', re.S)


HF_HOST = re.compile(r'<div id="(hf\d+-[^"]+)" class="fz-hf hide"([^>]*?) data-start="([\d.]+)"([^>]*)></div>')


def hoist_registry(body: str, cid: str, start: float) -> tuple[str, list[str]]:
    """Registry animations mounted inside a clip -> hosts in the root composition at their global time (Studio does not pass
    variables to sub-compositions nested two levels deep). Ids get the clip's prefix, here and in the clip's scene data."""
    hosts = []
    def take(m):
        hid = f"{cid}-{m.group(1)}"
        hosts.append(f'<div id="{hid}" class="fz-hf hide"{m.group(2)} data-start="{start + float(m.group(3)):.3f}"{m.group(4)}></div>')
        return ""
    body = HF_HOST.sub(take, body)
    body = re.sub(r'"_host": ?"(hf\d+-[^"]+)"', lambda m: f'"_host":"{cid}-{m.group(1)}"', body)
    return body, hosts


def subcomposition(html: str, cid: str, start: float = 0.0) -> tuple[str, list[str]]:
    """A built clip page -> the sub-composition contract: everything inside <template>, a root carrying the clip's own composition
    id, the runtime pointed at that root, and the timeline registered under the clip's id. Returns it with the registry hosts
    hoisted to the root composition."""
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    body = re.search(r"<body>(.*)</body>", html, re.S).group(1)
    body = ICONS.sub("", body, count=1)                     # the icon sprite lives once in the root document (Studio mounts only the root)
    body = body.replace('id="fz-presenter-video"', f'id="fz-presenter-video-{cid}"').replace('id="rec-video-', f'id="rec-video-{cid}-')  # media ids must be unique
    assets = "".join(re.findall(r"<script src=\"[^\"]+\"></script>|<link rel=\"stylesheet\"[^>]*>", head))
    body = body.replace('<div id="root" data-composition-id="main"', f'<div id="root" data-composition-id="{cid}" data-fz-root="{cid}"', 1)
    body = body.replace("FZ.create({ offset", f"FZ.create({{ root: '[data-fz-root=\"{cid}\"]', offset", 1)
    body = body.replace('window.__timelines["main"]', f'window.__timelines["{cid}"]', 1)
    body, hosts = hoist_registry(body, cid, start)
    return (f'<!doctype html>\n<html lang="en" data-composition-id="{cid}"><head><meta charset="UTF-8" /></head>\n<body>\n<template>\n'
            f"{assets}\n{body}\n</template>\n</body></html>\n"), hosts


ROOT = """<!doctype html>
<html lang="en"><head><meta charset="UTF-8" /><meta name="viewport" content="width=1920, height=1080" />
<script src="assets/runtime/vendor/gsap.min.js"></script>
<style>html, body {{ margin: 0; background: #000; }} #root {{ position: relative; width: 1920px; height: 1080px; overflow: hidden; background: #fff; }}
.fz-host, #footage {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; }} .fz-host {{ isolation: isolate; }}</style></head>
<body>
{icons}
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="1920" data-height="1080" data-fps="{fps}">
{footage}{hosts}{audio}</div>
<script>
(function () {{
  const tl = gsap.timeline({{ paused: true }});
  // plate graphics are hidden while the editor's studio shot is on screen (as in the final)
  {hides}
  tl.set({{}}, {{}}, {dur});
  window.__timelines = window.__timelines || {{}};
  window.__timelines["main"] = tl;
}})();
</script>
</body></html>
"""


def project_files(S: Path) -> None:
    S.mkdir(parents=True, exist_ok=True)
    (S / "hyperframes.json").write_text(json.dumps({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}, "media": {"autoProxy": True}}, indent=1))
    (S / "meta.json").write_text(json.dumps({"id": "fzv-studio", "name": "fzv studio preview", "createdAt": "2026-10-27T00:00:00.000Z"}))
    (S / "package.json").write_text(json.dumps({"name": "fzv-studio", "private": True, "type": "module"}))
    link = S / "assets"
    if not link.exists():
        link.symlink_to(Path("..") / "comp" / "assets")


def link(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def build(proj, settings: dict, log=print) -> Path:
    """Write edit/studio/ for the current build. Returns the project folder."""
    from .audio import export_stems
    pdata = proj.load()
    raw = proj.folder / pdata["raw"]
    info = media.probe(raw)
    dur = round(info["duration"], 3)
    man = json.loads((proj.edit / "built" / "clips.json").read_text())
    clips = {c["id"]: c for c in json.loads(proj.p("clips.json").read_text())}
    cuts = json.loads(proj.p("cuts.json").read_text()) if proj.p("cuts.json").exists() else []
    compose = pdata.get("mode") == "compose"
    S = proj.edit / "studio"
    if (S / "compositions").exists():
        shutil.rmtree(S / "compositions")
    (S / "compositions" / "registry").mkdir(parents=True, exist_ok=True)
    (S / "media").mkdir(parents=True, exist_ok=True)
    project_files(S)
    reg_src = proj.edit / "comp" / "assets" / "registry"
    hosts, hides, icons = [], [], ""
    for m in sorted(man, key=lambda c: c["start"]):
        cid = f"fz-{m['id']}"
        html = (proj.edit / "built" / m["html"]).read_text(encoding="utf-8")
        icons = icons or (ICONS.search(html).group(0) if ICONS.search(html) else "")
        sub, reg_hosts = subcomposition(html, cid, m["start"])
        (S / "compositions" / f"{m['id']}.html").write_text(sub, encoding="utf-8")
        for item in set(re.findall(r'data-composition-src="compositions/registry/([^/"]+)/', html)):   # registry items it mounts
            if (reg_src / item).exists() and not (S / "compositions" / "registry" / item).exists():
                shutil.copytree(reg_src / item, S / "compositions" / "registry" / item, copy_function=os.link)
        hosts.append(f'<div id="h-{m["id"]}" class="fz-host" data-composition-id="{cid}" data-composition-src="compositions/{m["id"]}.html" '
                     f'data-start="{m["start"]:.3f}" data-duration="{m["end"] - m["start"]:.3f}"></div>')
        hosts += reg_hosts
        if m["layer"] == "plate" and not compose:
            for c in cuts:
                if c["kind"] == "studio" and c["end"] > m["start"] and c["start"] < m["end"]:
                    hides.append(f'tl.set("#h-{m["id"]}", {{ autoAlpha: 0 }}, {max(m["start"], c["start"]):.3f}); '
                                 f'tl.set("#h-{m["id"]}", {{ autoAlpha: 1 }}, {min(m["end"], c["end"]):.3f});')
    footage = ""
    if not compose:
        link(raw, S / "media" / f"footage{raw.suffix.lower()}")
        footage = (f'<video id="footage" src="media/footage{raw.suffix.lower()}" data-start="0" data-duration="{dur}" muted playsinline></video>\n')
    st = export_stems(proj, proj.edit / "review")
    tracks = []
    if st.get("voice_sfx") and st.get("music"):
        for key, label in (("voice_sfx", "voice"), ("music", "music")):
            link(proj.edit / "review" / st[key], S / "media" / st[key])
            tracks.append(f'<audio id="{label}" src="media/{st[key]}" data-start="0" data-duration="{dur}"></audio>')
    else:
        mix = proj.edit / "audio" / "mix.wav"
        if mix.exists():
            media.run(["ffmpeg", "-v", "error", "-y", "-i", mix, "-c:a", "aac", "-b:a", "128k", S / "media" / "mix.m4a"])
            tracks.append(f'<audio id="mix" src="media/mix.m4a" data-start="0" data-duration="{dur}"></audio>')
    fps = settings.get("graphics_fps", 25)
    (S / "index.html").write_text(ROOT.format(dur=dur, fps=fps, footage=footage, icons=icons, hosts="\n".join(hosts) + "\n", audio="\n".join(tracks) + "\n",
                                              hides="\n  ".join(hides)), encoding="utf-8")
    (S / "studio.json").write_text(json.dumps({"build": B.build_signature(proj)}))
    log(f"studio: {len(man)} scene(s){', footage' if footage else ''}, {len(tracks)} audio track(s) -> {S}")
    return S


def state(proj) -> str:
    """missing | stale | ready: whether edit/studio/ shows the current build."""
    f = proj.edit / "studio" / "studio.json"
    if not f.exists():
        return "missing"
    return "ready" if json.loads(f.read_text()).get("build") == B.build_signature(proj) else "stale"


def serve(S: Path, port: int | None = None, stop: bool = False, open_browser: bool = True, log=print) -> str | None:
    """Start (or stop) HyperFrames Studio for the project in the background; returns its URL."""
    if stop:
        subprocess.run(hf_bin() + ["preview", str(S), "--stop"], env=STUDIO_ENV, capture_output=True, text=True)
        f = S / "studio.json"
        if f.exists():
            d = json.loads(f.read_text()); d.pop("url", None); f.write_text(json.dumps(d))
        log("studio: stopped")
        return None
    cmd = hf_bin() + ["preview", str(S), "--background", "--no-open"] + (["--port", str(port)] if port else [])
    p = subprocess.run(cmd, env=STUDIO_ENV, capture_output=True, text=True)
    txt = re.sub(r"\x1b\[[0-9;]*m", "", p.stdout + p.stderr)
    m = re.search(r"https?://(?:localhost|127\.0\.0\.1):\d+[^\s]*", txt)
    if not m:
        raise SystemExit(f"studio: could not start HyperFrames Studio:\n{txt[-1500:]}")
    url = m.group(0)
    f = S / "studio.json"
    d = json.loads(f.read_text()) if f.exists() else {}
    f.write_text(json.dumps(dict(d, url=url)))                   # the review page links to the running preview
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    log(f"studio: {url}")
    return url
