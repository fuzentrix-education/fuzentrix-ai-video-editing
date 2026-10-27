"""Bring third-party assets into the global library with their source and licence recorded (design §9d).

- props: recolour a downloaded SVG to brand variables, so it recolours per brand like the in-house set
- icons: add a 24-grid line icon (Lucide, Tabler...) to the runtime sprite
- music: copy a licensed track into global/music/ and list it in the manifest
"""
from __future__ import annotations

import colorsys
import re
import shutil
import subprocess
from pathlib import Path

import yaml

from .config import GLOBAL, RUNTIME, css_vars, load_brand

# fixed colours allowed in props: white, dark (tyres, hair), metal grey, glass, lamps, and a range of skin tones
NEUTRALS = ["#FFFFFF", "#2B2F3A", "#D9DEE6", "#BFE3F2", "#FFE08A", "#FF8A80"]
SKIN = ["#F1C7A3", "#D9A37E", "#A8714F", "#6E4A33"]
ALLOWED = {c.upper() for c in NEUTRALS + SKIN}
BRAND_VARS = ["text", "text2", "accent", "action", "emph", "line", "tint", "highlight", "success", "danger", "purple"]
NAMED = {"black": "#000000", "white": "#FFFFFF", "red": "#FF0000", "green": "#008000", "blue": "#0000FF", "yellow": "#FFFF00",
         "orange": "#FFA500", "gray": "#808080", "grey": "#808080", "purple": "#800080", "pink": "#FFC0CB", "brown": "#A52A2A"}
COLOR = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)")
NAMED_ATTR = re.compile(r'((?:fill|stroke|stop-color|color)\s*[=:]\s*"?)(' + "|".join(NAMED) + r')\b', re.I)


def rgb(c: str) -> tuple[int, int, int]:
    c = c.strip()
    if c.startswith("rgb"):
        return tuple(int(x) for x in re.findall(r"\d+", c)[:3])
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def lab(c: tuple[int, int, int]) -> tuple[float, float, float]:
    def lin(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in c)
    x, y, z = (r * .4124 + g * .3576 + b * .1805) / .95047, r * .2126 + g * .7152 + b * .0722, (r * .0193 + g * .1192 + b * .9505) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def nearest(c: tuple[int, int, int], options: dict[str, str]) -> str:
    L = lab(c)
    return min(options, key=lambda k: sum((p - q) ** 2 for p, q in zip(L, lab(rgb(options[k])))))


def map_colour(c: str, brand_hex: dict[str, str]) -> str:
    r, g, b = rgb(c)
    if f"#{r:02X}{g:02X}{b:02X}" in ALLOWED:
        return f"#{r:02X}{g:02X}{b:02X}"
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if s < 0.12 or l > 0.95 or l < 0.12:                        # greys, near-white, near-black
        if l > 0.9:
            return "#FFFFFF"
        if l < 0.3:
            return "#2B2F3A"
        return "var(--fz-text2)" if l < 0.6 else "#D9DEE6"
    if l < 0.33 and s < 0.45 and (h <= 0.11 or h >= 0.92):          # dark browns (hair, shadows) -> natural dark
        return "#2B2F3A"
    if 0.02 <= h <= 0.11 and 0.2 <= s <= 0.8 and 0.25 <= l <= 0.88:   # skin and wood tones keep a natural skin tone
        return nearest((r, g, b), {k: k for k in SKIN})
    return f"var(--fz-{nearest((r, g, b), brand_hex)})"


def recolor(svg: str, brand_id: str = "career-orbit") -> tuple[str, dict[str, str]]:
    """Replace every fixed colour with the nearest brand variable (or an allowed neutral / skin tone)."""
    v = css_vars(load_brand(brand_id))
    brand_hex = {k: v[k] for k in BRAND_VARS if isinstance(v.get(k), str) and v[k].startswith("#")}
    svg = NAMED_ATTR.sub(lambda m: m.group(1) + NAMED[m.group(2).lower()], svg)
    mapping: dict[str, str] = {}

    def sub(m):
        src = m.group(0)
        mapping.setdefault(src, map_colour(src, brand_hex))
        return mapping[src]
    svg = COLOR.sub(sub, svg)
    return svg, mapping


def clean_svg(svg: str) -> str:
    svg = re.sub(r"<\?xml.*?\?>|<!DOCTYPE.*?>|<!--.*?-->|<metadata.*?</metadata>", "", svg, flags=re.S)
    root = re.search(r"<svg\b[^>]*>", svg)
    if root and "viewBox" not in root.group(0):
        w, h = re.search(r'width="([\d.]+)', root.group(0)), re.search(r'height="([\d.]+)', root.group(0))
        if w and h:
            svg = svg.replace(root.group(0), root.group(0)[:-1] + f' viewBox="0 0 {w.group(1)} {h.group(1)}">', 1)
    root = re.search(r"<svg\b[^>]*>", svg)
    if root:
        svg = svg.replace(root.group(0), re.sub(r'\s(width|height)="[^"]*"', "", root.group(0)), 1)
    return svg.strip()


def scope_ids(svg: str, prefix: str) -> str:
    """Prefix internal ids (gradients, clip paths) so several inlined SVGs never clash on one page."""
    ids = set(re.findall(r'\bid="([^"]+)"', svg))
    for i in sorted(ids, key=len, reverse=True):
        svg = svg.replace(f'id="{i}"', f'id="{prefix}-{i}"').replace(f"url(#{i})", f"url(#{prefix}-{i})").replace(f'href="#{i}"', f'href="#{prefix}-{i}"')
    return svg


def add_prop(svg: str, prop_id: str, kind: str, tags: str, source: str, licence: str, style: str = "flat", recolour: bool = True,
             log=print) -> dict:
    """Clean, recolour and register one prop SVG in global/props (manifest + svg/)."""
    man_f = GLOBAL / "props" / "manifest.yaml"
    man = yaml.safe_load(man_f.read_text(encoding="utf-8")) or {}
    if any(x["id"] == prop_id for x in man.get("assets") or []):
        raise ValueError(f"'{prop_id}' already exists")
    if source != "in-house":
        if p := licence_problem(licence):
            raise ValueError(p)
        if w := attribution_warning(licence):
            log(f"warning: {w}")
    svg = scope_ids(clean_svg(svg), prop_id)
    if recolour:
        svg, mapping = recolor(svg)
    bad = sorted({c.upper() for c in re.findall(r'(?:fill|stroke|stop-color)\s*[=:]\s*"?(#[0-9A-Fa-f]{3,6})', svg)} - ALLOWED)
    if bad or ("var(--fz-" not in svg and not recolour):
        raise ValueError(f"colour the SVG with brand variables (var(--fz-text), var(--fz-accent)…) or recolour it; fixed colours: {bad}")
    vb = re.search(r'viewBox="([^"]+)"', svg)
    if not vb:
        raise ValueError("the SVG needs a viewBox")
    w, h = (float(x) for x in vb.group(1).split()[2:])
    k = 200 / max(w, h) if max(w, h) < 120 else 1.0          # icon-grid SVGs (24/32 px) scale up to the library's prop size
    entry = {"id": prop_id, "kind": kind, "style": style, "tags": tags, "size": [round(w * k), round(h * k)], "anchor": "bottom-center",
             "source": source, "licence": licence}
    (GLOBAL / "props" / "svg" / f"{prop_id}.svg").write_text(svg, encoding="utf-8")
    with open(man_f, "a", encoding="utf-8") as f:
        f.write("  - " + yaml.safe_dump(entry, default_flow_style=True, sort_keys=False, width=400, allow_unicode=True).strip() + "\n")
    return entry


def licence_problem(lic: str) -> str | None:
    """Refuse licences that don't allow commercial use or edits; warn on attribution (the videos carry no credits)."""
    l = f" {lic.lower()} "
    if not lic.strip() or "…" in lic:
        return "record the licence (e.g. 'MIT', 'CC0', 'Pixabay Content License', 'Envato Elements')"
    if re.search(r"\bnc\b|non-?commercial|personal use|\bnd\b|no ?deriv", l):
        return f"licence '{lic}' does not allow commercial use or edits; pick another asset"
    return None


def attribution_warning(lic: str) -> str | None:
    if re.search(r"cc[ -]?by(?![ -]?0)|attribution|\bby-sa\b", lic.lower()):
        return "this licence needs a credit; Fuzentrix videos have no credits roll, so prefer CC0/MIT/ISC/Apache or a paid licence"
    return None


def add_icon(src: Path, icon_id: str, source: str, licence: str) -> str:
    sprite = RUNTIME / "icons.svg"
    s = sprite.read_text(encoding="utf-8")
    if f'id="i-{icon_id}"' in s:
        raise SystemExit(f"icons add: i-{icon_id} already exists")
    svg = clean_svg(src.read_text(encoding="utf-8"))
    vb = re.search(r'viewBox="([^"]+)"', svg)
    inner = re.sub(r"^.*?<svg\b[^>]*>|</svg>\s*$", "", svg, flags=re.S)
    inner = re.sub(r'<path[^>]*d="M0 0h24v24H0z"[^>]*/>', "", inner)          # Tabler's invisible bounding box
    inner, _ = recolor(inner)
    inner = re.sub(r'(stroke|fill)="var\(--fz-[a-z0-9-]+\)"', r'\1="currentColor"', inner)   # icons take the text colour
    sym = f'<symbol id="i-{icon_id}" viewBox="{vb.group(1) if vb else "0 0 24 24"}" data-source="{source}" data-licence="{licence}">{inner.strip()}</symbol>\n'
    sprite.write_text(s.replace("</defs>", sym + "</defs>", 1), encoding="utf-8")
    return sym


SFX_CATEGORIES = ["whoosh", "swish", "pop", "blip", "tick", "click", "ding", "good", "bad", "thud", "impact", "chime", "type"]
SFX_GUESS = [("whoosh", "whoosh swoosh woosh transition swipe sweep"), ("swish", "swish slide"), ("pop", "pop bubble appear"), ("blip", "blip beep ui"),
             ("tick", "tick tock"), ("click", "click tap press mouse button"), ("ding", "ding bell notification"), ("good", "success correct right positive"),
             ("bad", "error wrong fail negative buzz"), ("thud", "thud drop hit"), ("impact", "impact boom hit-big riser reveal"), ("chime", "chime sparkle magic"),
             ("type", "type typing keyboard key")]


def guess_sfx_category(name: str) -> str | None:
    n = name.lower()
    for cat, words in SFX_GUESS:
        if any(w in n for w in words.split()):
            return cat
    return None


def add_sfx(src: Path, category: str | None, source: str, licence: str, gain_db: float = 0.0) -> list[dict]:
    """Copy one sound or a folder of sounds into global/sfx/<category>/ and list them in the manifest."""
    man_f = GLOBAL / "sfx" / "manifest.yaml"
    text = man_f.read_text(encoding="utf-8") if man_f.exists() else "# The team's SFX library (rule A5). fzv uses these before its synthesised sounds.\n"
    data = yaml.safe_load(text) or {}
    sounds = data.get("sounds") or []
    files = [src] if src.is_file() else sorted(f for f in src.rglob("*") if f.suffix.lower() in (".wav", ".mp3", ".ogg", ".m4a", ".aiff", ".flac"))
    added = []
    for f in files:
        cat = category or guess_sfx_category(f.stem)
        if cat not in SFX_CATEGORIES:
            continue
        dst = GLOBAL / "sfx" / cat / f.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if any(s["file"] == f"{cat}/{f.name}" for s in sounds):
            continue
        shutil.copy2(f, dst)
        e = {"id": f"{cat}-{f.stem}".lower().replace(" ", "-"), "category": cat, "file": f"{cat}/{f.name}", "gain_db": gain_db, "source": source, "licence": licence}
        sounds.append(e)
        added.append(e)
    header = "".join(l + "\n" for l in text.splitlines() if l.startswith("#"))
    man_f.write_text(header + yaml.safe_dump({"sounds": sounds}, sort_keys=False, allow_unicode=True, width=200), encoding="utf-8")
    return added


def remove_sfx(names: list[str]) -> list[str]:
    """Drop sounds from the library by file (e.g. swish/close_002.ogg) or by audition number (e.g. swish:2)."""
    man_f = GLOBAL / "sfx" / "manifest.yaml"
    text = man_f.read_text(encoding="utf-8")
    sounds = (yaml.safe_load(text) or {}).get("sounds") or []
    drop = set()
    for n in names:
        if ":" in n and n.split(":")[1].isdigit():
            cat, k = n.split(":")
            same = [s for s in sounds if s["category"] == cat]
            if 1 <= int(k) <= len(same):
                drop.add(same[int(k) - 1]["file"])
        else:
            drop.add(n)
    keep = [s for s in sounds if s["file"] not in drop]
    for s in sounds:
        if s["file"] in drop:
            (GLOBAL / "sfx" / s["file"]).unlink(missing_ok=True)
    header = "".join(l + "\n" for l in text.splitlines() if l.startswith("#"))
    man_f.write_text(header + yaml.safe_dump({"sounds": keep}, sort_keys=False, allow_unicode=True, width=200), encoding="utf-8")
    return sorted(drop)


def sfx_audition(log=print) -> Path:
    """One MP3 per category with every library sound in order (0.7 s apart) and a list, for the team to listen and prune."""
    from .audio import sfx_library
    out = GLOBAL / "sfx" / "_audition"
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    for cat, sounds in sorted(sfx_library().items()):
        lst = out / f"{cat}.txt"
        inputs, fc = [], []
        for i, s in enumerate(sounds):
            inputs += ["-i", str(GLOBAL / "sfx" / s["file"])]
            fc.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo,apad=pad_dur=0.7[a{i}]")
        fc.append("".join(f"[a{i}]" for i in range(len(sounds))) + f"concat=n={len(sounds)}:v=0:a=1[o]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", "[o]", "-c:a", "libmp3lame", "-q:a", "3", str(out / f"{cat}.mp3")], check=True)
        lst.write_text("\n".join(f"{i + 1:2d}. {s['file']}" for i, s in enumerate(sounds)) + "\n")
        lines.append(f"{cat}: {len(sounds)} sound(s) -> {out / (cat + '.mp3')}")
    for l in lines:
        log(l)
    return out


def add_music(src: Path, track_id: str, mood: str, bpm: int | None, source: str, licence: str) -> dict:
    from . import media
    man_f = GLOBAL / "music" / "manifest.yaml"
    text = man_f.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    tracks = data.get("tracks") or []
    if any(t.get("id") == track_id for t in tracks):
        raise SystemExit(f"music add: '{track_id}' already exists")
    dst = GLOBAL / "music" / f"{track_id}{src.suffix.lower()}"
    shutil.copy2(src, dst)
    info = media.probe(dst)
    t = {"id": track_id, "mood": mood, "file": dst.name, "duration": round(info["duration"], 1), "source": source, "licence": licence}
    if bpm:
        t["bpm"] = bpm
    tracks.append(t)
    header = "".join(l + "\n" for l in text.splitlines() if l.startswith("#") and not l.startswith("#  -"))
    man_f.write_text(header + yaml.safe_dump({"tracks": tracks}, sort_keys=False, allow_unicode=True, width=200), encoding="utf-8")
    return t
