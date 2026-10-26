"""Global configuration: repo paths, defaults, rules and brand kits.

A brand kit is global/brand/<id>/brand.yaml, which `extends` global/brand/_shared/house.yaml. The merged kit becomes CSS
variables (brand.css) for the runtime, plus a small JSON object (motion, bug, name card) passed to FZ.create.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
GLOBAL = REPO / "global"
RUNTIME = REPO / "runtime"
BRANDS = GLOBAL / "brand"


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def defaults() -> dict:
    return load_yaml(GLOBAL / "defaults.yaml")


def rules() -> dict:
    return load_yaml(GLOBAL / "rules.yaml").get("rules", {})


def brand_ids() -> list[str]:
    return sorted(p.name for p in BRANDS.iterdir() if (p / "brand.yaml").exists())


def load_brand(brand_id: str) -> dict:
    """Merged brand kit: house style + brand.yaml (+ the brand's folder path under `_dir`)."""
    folder = BRANDS / brand_id
    if not (folder / "brand.yaml").exists():
        raise SystemExit(f"brand '{brand_id}' not found; available: {', '.join(brand_ids())}")
    b = load_yaml(folder / "brand.yaml")
    house = load_yaml((folder / b["extends"]).resolve()) if b.get("extends") else {}
    merged = deep_merge(house, b)
    merged["_dir"] = str(folder)
    merged["_shared"] = str((folder / b["extends"]).resolve().parent) if b.get("extends") else str(BRANDS / "_shared")
    return merged


def color(brand: dict, name: str | None, fallback: str = "#000000") -> str:
    """Resolve a role value: a colour name in `colors`, a house `semantic` name, or a literal hex."""
    if not name:
        return fallback
    name = str(name)
    if name.startswith("#"):
        return name
    for table in ("colors", "semantic"):
        v = (brand.get(table) or {}).get(name)
        if isinstance(v, str):
            return v
    return fallback


def css_vars(brand: dict) -> dict[str, str]:
    """The CSS variables every template uses, resolved from the brand's roles."""
    r, c, code, sem = brand.get("roles", {}), brand.get("colors", {}), brand.get("code", {}), brand.get("semantic", {})
    text = color(brand, r.get("text"), "#0D274C")
    highlight = color(brand, r.get("highlight"), sem.get("warning", "#F6AD55"))
    grad = None
    for gname in ("orbit", "logo"):
        if gname in brand.get("gradients", {}):
            grad = brand["gradients"][gname]
            break
    grad = grad or [text, color(brand, r.get("accent"), "#1790B4")]
    deep = brand.get("gradients", {}).get("deep") or [text, "#081830"]
    shape = brand.get("shape", {})
    fonts = brand.get("fonts", {})
    v = {
        "text": text,
        "text2": color(brand, r.get("text-secondary"), "#52657D"),
        "emph": color(brand, r.get("title-emphasis"), "#30809F"),
        "emph2": color(brand, r.get("small-emphasis"), "#1B53A2"),
        "label": color(brand, r.get("title-emphasis"), "#30809F"),
        "icon": color(brand, r.get("small-emphasis"), "#1B53A2"),
        "accent": color(brand, r.get("accent"), "#1790B4"),
        "action": color(brand, r.get("action") or r.get("cta"), color(brand, r.get("accent"), "#1B53A2")),
        "highlight": highlight,
        "highlight-strong": "#F59E0B" if highlight.upper() == "#F6AD55" else highlight,
        "card": color(brand, r.get("card"), c.get("surface", "#FFFFFF") if str(c.get("surface", "")).upper() == "#FFFFFF" else "#FFFFFF"),
        "line": color(brand, r.get("card-border"), "#DCE7F4"),
        "tint": color(brand, r.get("pill"), "#EAF4FA"),
        "page": color(brand, r.get("page"), c.get("surface", "#F3F7FD")),
        "on-dark-accent": color(brand, r.get("on-dark-accent"), "#16BBC8"),
        "on-dark-soft": "#A9D6E5",
        "success": sem.get("success", "#12A150"),
        "danger": sem.get("danger", "#E5484D"),
        "warning": sem.get("warning", "#F6AD55"),
        "purple": sem.get("info-purple", "#7C5CD6"),
        "code-bg1": (code.get("bg") or ["#13274A", "#0B1730"])[0],
        "code-bg2": (code.get("bg") or ["#13274A", "#0B1730"])[1],
        "kw": code.get("keyword", "#7DD3FC"), "fn": code.get("function", "#FBBF24"), "num": code.get("number", "#6EE7B7"),
        "str": code.get("string", "#F9A8D4"), "op": code.get("operator", "#CBD5E1"), "cm": code.get("comment", "#7B8BA5"),
        "lkw": code.get("on-light", {}).get("keyword", "#0E7490"), "lfn": code.get("on-light", {}).get("function", "#B45309"),
        "lnum": code.get("on-light", {}).get("number", "#047857"), "lstr": code.get("on-light", {}).get("string", "#BE185D"),
        "grad": f"linear-gradient(90deg, {', '.join(color(brand, g, g) for g in grad)})",
        "deep-grad": f"linear-gradient(160deg, {', '.join(color(brand, g, g) for g in deep)})",
        "radius": f"{shape.get('card-radius', 26)}px",
        "shadow": shape.get("card-shadow", "0 30px 60px -22px rgba(13,39,76,.28)"),
        "font-display": f'"{fonts.get("display", {}).get("family", "Outfit")}", sans-serif',
        "font-body": f'"{fonts.get("body", {}).get("family", "Inter")}", sans-serif',
        "font-mono": f'"{fonts.get("mono", {}).get("family", "JetBrains Mono")}", monospace',
        "font-hand": f'"{fonts.get("hand", {}).get("family", "Caveat")}", cursive',
    }
    return v


def brand_css(brand: dict, font_url_prefix: str = "fonts/") -> str:
    """@font-face rules for every bundled font file of the brand's families, then the :root variables."""
    shared = Path(brand["_shared"])
    faces = []
    for key in ("display", "body", "mono", "hand", "wordmark"):
        fam = brand.get("fonts", {}).get(key, {}).get("family")
        if not fam:
            continue
        slug = fam.lower().replace(" ", "-")
        for f in sorted((shared / "fonts").glob(f"{slug}-latin-*-normal.woff2")):
            weight = f.stem.split("-")[-2]
            faces.append(f'@font-face {{ font-family: "{fam}"; src: url("{font_url_prefix}{f.name}") format("woff2"); font-weight: {weight}; }}')
    root = "\n".join(f"  --fz-{k}: {v};" for k, v in css_vars(brand).items())
    return "\n".join(faces) + "\n:root {\n" + root + "\n}\n"


def brand_js(brand: dict) -> dict:
    """The small part of the brand the runtime needs as data."""
    m = brand.get("motion", {})
    motion = {}
    for k in ("enter", "exit", "pop"):
        if isinstance(m.get(k), dict):
            motion[k] = [m[k].get("duration", 0.5), m[k].get("ease", "power3.out")]
    if "stagger" in m:
        motion["stagger"] = m["stagger"]
    if "wire-draw" in m:
        motion["wire"] = m["wire-draw"]
    bug = brand.get("bug", {})
    return {"id": brand.get("id"), "name": brand.get("name"), "motion": motion,
            "bug": {"logo": Path(bug.get("logo", "")).name, "height": bug.get("height", 40)},
            "nameCard": brand.get("name-card", {}).get("title", "Instructor")}


def dump_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
