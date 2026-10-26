"""HyperFrames registry (design §7.4): vendor open-source animated blocks and components into global/registry/ and mount them
in clips with the `hf` template. Items are Apache-2.0 (github.com/heygen-com/hyperframes); each keeps its source and licence.

    fzv registry search <words>        what the registry has (448 items: code animations, diagrams, charts, cursors, annotations…)
    fzv registry add <name> [...]      vendor items (and their fonts/assets) into global/registry/
    fzv registry list                  installed items with their variables
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

from .config import GLOBAL, REPO

REG = GLOBAL / "registry"
ENV = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1", HYPERFRAMES_SKIP_SKILLS="1", DO_NOT_TRACK="1")
SOURCE = "https://github.com/heygen-com/hyperframes/tree/main/registry"
LICENCE = "Apache-2.0 (HyperFrames registry)"


def _hf(*args, cwd=None, timeout=180) -> subprocess.CompletedProcess:
    return subprocess.run([str(REPO / "node_modules" / ".bin" / "hyperframes"), *args], cwd=cwd, env=ENV, capture_output=True, text=True, timeout=timeout)


def catalog(refresh: bool = False) -> list[dict]:
    cache = REG / "catalog.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text())
    p = _hf("catalog", "--json")
    if p.returncode != 0:
        raise SystemExit(f"registry: catalog failed: {p.stderr[-500:]}")
    data = json.loads(p.stdout[p.stdout.index("["):])
    REG.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data, indent=1))
    return data


def search(words: str) -> list[dict]:
    ws = [w.lower() for w in words.split()]
    return [x for x in catalog() if all(w in (x["name"] + " " + x["description"] + " " + " ".join(x.get("tags", []))).lower() for w in ws)]


def manifest() -> list[dict]:
    f = REG / "manifest.yaml"
    return (yaml.safe_load(f.read_text()) or {}).get("items") or [] if f.exists() else []


def variables(html: str) -> list[dict]:
    m = re.search(r"data-composition-variables='(\[.*?\])'", html, re.S)
    if not m:
        return []
    try:
        return [{k: v for k, v in d.items() if k in ("id", "type", "default", "description", "options")} for d in json.loads(m.group(1))]
    except json.JSONDecodeError:
        return []


def comp_id(html: str, name: str) -> str:
    """The composition id the item's root registers its timeline under (mounts must use it)."""
    m = re.search(r'<template>\s*<div[^>]*data-composition-id="([^"]+)"', html) or re.search(r'id="root"[^>]*data-composition-id="([^"]+)"', html)
    return m.group(1) if m else name


def vendor_scripts(html: str, log=print) -> str:
    """CDN scripts (gsap, lottie-web…) are downloaded once into global/registry/_assets/vendor/ so renders never need the network."""
    import urllib.request
    def fetch(m):
        url = m.group(1)
        rel = Path("vendor") / re.sub(r"^https?://[^/]+/(npm/)?", "", url).replace("/dist/", "/").replace("/build/player/", "/")
        dst = REG / "_assets" / rel
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "fzv-registry/1.0"}), timeout=60) as r:
                dst.write_bytes(r.read())
            log(f"registry: vendored {url}")
        return f'<script src="assets/{rel.as_posix()}"></script>'
    return re.sub(r'<script src="(https?://cdn\.jsdelivr\.net/[^"]+)"></script>', fetch, html)


def open_ended(html: str) -> str:
    """Components hold their final frame; lift their declared length so the mount's own window (`at`..`until`) decides."""
    html = re.sub(r'data-composition-duration="[0-9.]+"', 'data-composition-duration="3600"', html, count=1)
    html = re.sub(r'(<template>\s*<div[^>]*?data-duration=")[0-9.]+(")', r"\g<1>3600\2", html, count=1)
    # the component's wrapper clip (starts at 0) is timed too: give it the same open end
    return re.sub(r'<[a-z]+\b[^>]*\bdata-start="0"[^>]*>', lambda m: re.sub(r'data-duration="[0-9.]+"', 'data-duration="3600"', m.group(0)), html)


def add(names: list[str], log=print) -> list[dict]:
    items = {x["name"]: x for x in manifest()}
    cat = {x["name"]: x for x in catalog()}
    with tempfile.TemporaryDirectory(prefix="fzreg_") as d:
        proj = Path(d).resolve()
        (proj / "hyperframes.json").write_text(json.dumps({"registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
                                                           "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}}))
        (proj / "index.html").write_text("<!doctype html><html><body><div id='root' data-composition-id='root' data-width='1920' data-height='1080'></div></body></html>")
        for n in names:
            if n in items:
                log(f"registry: {n} already installed"); continue
            p = _hf("add", n, "--dir", str(proj), "--no-clipboard", "--json", cwd=proj)
            if p.returncode != 0:
                log(f"registry: {n} failed: {(p.stderr or p.stdout)[-300:]}"); continue
            out = json.loads(p.stdout[p.stdout.index("{"):])
            files = [Path(f).resolve() for f in (out.get("files") or out.get("written") or [])]
            main = next((f for f in files if f.suffix == ".html"), None)
            if not main:
                log(f"registry: {n}: no composition file"); continue
            dst = REG / n
            dst.mkdir(parents=True, exist_ok=True)
            for f in files:
                rel = f.relative_to(proj)
                if rel.parts[0] == "assets":                     # fonts/images referenced as assets/… from the document root
                    t = REG / "_assets" / Path(*rel.parts[1:])
                else:
                    t = dst / f.name
                t.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, t)
            html = vendor_scripts((dst / main.name).read_text(encoding="utf-8"), log)
            for ref in set(re.findall(r'assets/([A-Za-z0-9_./-]+\.(?:json|png|jpg|svg|webp|woff2|mp3|wav))', html)):   # document-relative assets
                t, here = REG / "_assets" / ref, dst / Path(ref).name
                if not t.exists() and here.exists():
                    t.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(here), t)
            if cat.get(n, {}).get("type", "component") == "component":
                html = open_ended(html)
            (dst / main.name).write_text(html, encoding="utf-8")
            c = cat.get(n, {})
            items[n] = {"name": n, "type": c.get("type", "component"), "file": f"{n}/{main.name}", "comp_id": comp_id(html, n), "title": c.get("title", n),
                        "description": c.get("description", ""), "tags": c.get("tags", []), "duration": c.get("duration"),
                        "size": c.get("dimensions"), "variables": variables(html), "source": f"{SOURCE}/{n}", "licence": LICENCE}
            log(f"registry: {n} added ({items[n]['type']}, {len(items[n]['variables'])} variables)")
    (REG / "manifest.yaml").write_text("# Vendored HyperFrames registry items (fzv registry add). Mount with the `hf` template.\n" +
                                       yaml.safe_dump({"items": sorted(items.values(), key=lambda x: x["name"])}, sort_keys=False, allow_unicode=True, width=200), encoding="utf-8")
    return list(items.values())


def host_markup(scene_id: str, item: dict, local_at: float, dur: float, box: dict, vars_: dict) -> str:
    """Static host element for one mount (HyperFrames mounts the sub-composition into it). Components are elastic and fill the box;
    blocks are fixed-size scenes (usually 1920x1080) scaled into it. The host carries the item's own composition id, because items
    register their timeline under it (so one mount per item per clip)."""
    size = item.get("size") or {}
    if item.get("type") == "block" and size.get("width"):
        k = min(box["w"] / size["width"], box["h"] / size["height"])
        geo = f"left:{box['x']}px;top:{box['y']}px;width:{size['width']}px;height:{size['height']}px;transform:scale({k:.4f});transform-origin:0 0;"
    else:
        geo = f"left:{box['x']}px;top:{box['y']}px;width:{box['w']}px;height:{box['h']}px;"
    style = ("position:absolute;" + geo +
             "--fg:var(--fz-text);--bg:transparent;--accent:var(--fz-accent);--accent-2:var(--fz-action);--brand:var(--fz-action);"
             "--surface:var(--fz-card);--radius:var(--fz-radius);--font-display:var(--fz-font-display);--font-body:var(--fz-font-body);--font-mono:var(--fz-font-mono)")
    vv = json.dumps({k: (",".join(map(str, v)) if isinstance(v, list) else v) for k, v in vars_.items()}).replace("'", "&#39;")
    cid = item.get("comp_id") or item["name"]
    return (f'<div id="{scene_id}" class="fz-hf hide" data-composition-id="{cid}" data-composition-src="compositions/registry/{item["file"]}" '
            f'data-start="{local_at:.3f}" data-duration="{dur:.3f}" data-variable-values=\'{vv}\' style="{style}"></div>')
