"""Global configuration: repo paths, defaults, rules and the brand kit.

There is one brand kit, global/brand/brand.yaml (Career Orbit). It becomes CSS variables (brand.css) for the runtime, a
rendered backdrop image, plus a small JSON object (motion, bug, name card) passed to FZ.create.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
GLOBAL = REPO / "global"
RUNTIME = REPO / "runtime"
BRANDS = GLOBAL / "brand"            # the brand kit folder (one kit; the name is kept for older callers)


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
    return [load_yaml(BRANDS / "brand.yaml").get("id", "career-orbit")]


def load_brand(brand_id: str | None = None) -> dict:
    """The brand kit. There is only one, so `brand_id` (from older specs and prompts) is ignored."""
    b = load_yaml(BRANDS / "brand.yaml")
    b["_dir"] = str(BRANDS)
    b["_shared"] = str(BRANDS)
    return b


def editor_plates() -> list[Path]:
    """The editors' slide backgrounds: rough cuts made on one are recognised and keyed against it."""
    return sorted((BRANDS / "plates").glob("*.png"))


def resolve_plate(rel: str) -> Path:
    """A plate path stored by an earlier ingest (relative to global/brand), found again after the kit was reorganised."""
    p = BRANDS / rel
    return p if p.is_file() else BRANDS / "plates" / Path(rel).name


def color(brand: dict, name: str | None, fallback: str = "#000000") -> str:
    """Resolve a role value: a colour name in `colors`, a `semantic` name, or a literal hex."""
    if not name:
        return fallback
    name = str(name)
    if name.startswith("#") or name.startswith("rgb"):
        return name
    for table in ("colors", "semantic"):
        v = (brand.get(table) or {}).get(name)
        if isinstance(v, str):
            return v
    return fallback


def css_vars(brand: dict) -> dict[str, str]:
    """The CSS variables every template uses, resolved from the kit's roles. Templates use only these, never a fixed colour."""
    r, code, sem = brand.get("roles", {}), brand.get("code", {}), brand.get("semantic", {})
    C = lambda name, fb: color(brand, name, fb)                                  # noqa: E731
    text = C(r.get("text"), "#102A56")
    grads = brand.get("gradients", {})
    grad = grads.get("brand") or [text, C(r.get("accent"), "#2563EB")]
    deep = grads.get("deep") or [text, "#0B1D37"]
    shape, fonts, dark = brand.get("shape", {}), brand.get("fonts", {}), sem.get("on-dark", {})
    accent = C(r.get("accent"), "#2563EB")
    v = {
        "text": text,
        "text2": C(r.get("text-secondary"), "#3B5079"),
        "mist": C("mist", "#8A9BBA"),
        "emph": C(r.get("title-emphasis"), "#1D4ED8"),
        "emph2": C(r.get("small-emphasis"), "#1D4ED8"),
        "label": C(r.get("title-emphasis"), "#1D4ED8"),
        "icon": C(r.get("small-emphasis"), "#1D4ED8"),
        "accent": accent,
        "action": C(r.get("action"), accent),
        "highlight": C(r.get("highlight"), "#F59E0B"),
        "highlight-strong": C(r.get("highlight"), "#F59E0B"),
        "highlight-soft": sem.get("highlight-soft", "#FEF3DC"),
        "highlight-text": sem.get("highlight-text", "#9A4A06"),
        "kicker": C(r.get("kicker", "blue-text"), "#1D4ED8"),        # section kickers ("• EXAMPLE 1"): the brand blue
        "marker": (brand.get("colors") or {}).get("marker", "rgba(251,191,36,.55)"),
        "card": C(r.get("card"), "#FFFFFF"),
        "line": C(r.get("card-border"), "#DCE7FA"),
        "tint": C(r.get("pill"), "#E3EDFF"),
        "dim": C("dim", "#F1F4F9"),
        "page": C(r.get("page"), "#F4F7FC"),
        "deep": C(r.get("dark-panel"), "#0B1D37"),
        "on-dark-accent": C(r.get("on-dark-accent"), "#78B7FF"),
        "on-dark-soft": C(r.get("on-dark-soft"), "#A4B6D6"),
        "success": sem.get("success", "#15803D"),
        "success-soft": sem.get("success-soft", "#E3F4EA"),
        "danger": sem.get("danger", "#C42020"),
        "danger-soft": sem.get("danger-soft", "#FDECEC"),
        "warning": sem.get("highlight", "#F59E0B"),
        "purple": accent,                                     # retired: one brand colour, no extra hues
        "dark-success": dark.get("success", "#86EFAC"),
        "dark-danger": dark.get("danger", "#FCA5A5"),
        "dark-highlight": dark.get("highlight", "#FBBF24"),
        "code-bg1": (code.get("bg") or ["#0D1A3A", "#0A1530"])[0],
        "code-bg2": (code.get("bg") or ["#0D1A3A", "#0A1530"])[1],
        "code-text": code.get("text", "#E1EBFF"),
        "kw": code.get("keyword", "#A5B6FF"), "fn": code.get("function", "#5CC8FF"), "num": code.get("number", "#F7B267"),
        "str": code.get("string", "#7EE0B5"), "ty": code.get("type", "#FFD580"), "op": code.get("operator", "#E1EBFF"), "cm": code.get("comment", "#7483AD"),
        "lkw": code.get("on-light", {}).get("keyword", "#3546B8"), "lfn": code.get("on-light", {}).get("function", "#0B6FBF"),
        "lnum": code.get("on-light", {}).get("number", "#B4530A"), "lstr": code.get("on-light", {}).get("string", "#0E7A50"),
        "lty": code.get("on-light", {}).get("type", "#8A5A00"), "lcm": code.get("on-light", {}).get("comment", "#6B7794"),
        "grad": f"linear-gradient(90deg, {', '.join(C(g, g) for g in grad)})",
        "deep-grad": f"linear-gradient(160deg, {', '.join(C(g, g) for g in deep)})",
        "radius": f"{shape.get('card-radius', 22)}px",
        "shadow": shape.get("card-shadow", "0 2px 4px rgba(16,42,86,.06), 0 26px 50px -18px rgba(16,42,86,.30)"),
        "font-display": f'"{fonts.get("display", {}).get("family", "Bricolage Grotesque")}", sans-serif',
        "font-body": f'"{fonts.get("body", {}).get("family", "Manrope")}", sans-serif',
        "font-mono": f'"{fonts.get("mono", {}).get("family", "JetBrains Mono")}", monospace',
        "font-hand": f'"{fonts.get("hand", {}).get("family", "Caveat")}", cursive',
    }
    ts = brand.get("type-scale", {})                        # one type scale (rule L13): --fz-fs-h1, --fz-fs-body …
    for k, d in (("hero", 92), ("h1", 64), ("h2", 46), ("body", 32), ("small", 26), ("label", 22), ("chip", 28), ("code", 52), ("code-min", 40), ("terminal", 40)):
        v[f"fs-{k}"] = f"{ts.get(k, d)}px"
    v["margin"] = f"{(brand.get('layout') or {}).get('margin-left', 96)}px"
    return v


def brand_css(brand: dict, font_url_prefix: str = "fonts/") -> str:
    """@font-face rules for every bundled font file of the kit's families (and their aliases), then the :root variables."""
    fonts_dir = Path(brand["_shared"]) / "fonts"
    fonts = brand.get("fonts", {})
    families = [(fonts[k]["family"], fonts[k]["family"]) for k in ("display", "body", "mono", "hand") if isinstance(fonts.get(k), dict)]
    families += [(alias, fonts[role]["family"]) for alias, role in (fonts.get("aliases") or {}).items() if isinstance(fonts.get(role), dict)]
    faces = []
    for name, fam in families:
        slug = fam.lower().replace(" ", "-")
        for f in sorted(fonts_dir.glob(f"{slug}-latin-*-normal.woff2")):
            weight = f.stem.split("-")[-2]
            faces.append(f'@font-face {{ font-family: "{name}"; src: url("{font_url_prefix}{f.name}") format("woff2"); font-weight: {weight}; }}')
    root = "\n".join(f"  --fz-{k}: {v};" for k, v in css_vars(brand).items())
    return "\n".join(faces) + "\n:root {\n" + root + "\n}\n"


def backdrop_key(brand: dict) -> str:
    return hashlib.sha256(json.dumps([brand.get("backdrop"), brand.get("colors")], sort_keys=True).encode()).hexdigest()[:12]


def render_backdrop(brand: dict, out: Path, size: tuple[int, int] = (1920, 1080)) -> Path:
    """The dotted backdrop (kit `backdrop`): pale base, a navy dot grid and two soft light pools. Drawn at 3x, then reduced."""
    import numpy as np
    from PIL import Image, ImageDraw
    bd = brand.get("backdrop", {})
    rgb = lambda h: tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))      # noqa: E731
    W, H = size
    img = np.ones((H, W, 3), np.float32) * np.array(rgb(color(brand, bd.get("base", "page"), "#F4F7FC")), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for g in bd.get("glows", []):
        d = np.sqrt(((xx - g["x"] * W) / W) ** 2 + ((yy - g["y"] * H) / W) ** 2) / g["radius"]
        a = (np.clip(1 - d, 0, 1) ** 2 * g.get("opacity", 0.1))[..., None]
        img = img * (1 - a) + np.array(rgb(color(brand, g["color"], "#2563EB")), np.float32) * a
    k, dots = 3, bd.get("dots", {})
    pitch, rad = dots.get("pitch", 34), dots.get("radius", 1.7)
    mask = Image.new("L", (W * k, H * k), 0)
    dr = ImageDraw.Draw(mask)
    ox, oy = (W % pitch) / 2 + pitch / 2, (H % pitch) / 2 + pitch / 2              # the grid centred on the frame
    y = oy
    while y < H:
        x = ox
        while x < W:
            dr.ellipse(((x - rad) * k, (y - rad) * k, (x + rad) * k, (y + rad) * k), fill=255)
            x += pitch
        y += pitch
    a = (np.asarray(mask.resize((W, H), Image.LANCZOS), np.float32) / 255 * dots.get("opacity", 0.12))[..., None]
    img = img * (1 - a) + np.array(rgb(color(brand, dots.get("color", "navy"), "#102A56")), np.float32) * a
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() or out.is_symlink():
        out.unlink()                                          # never write through a hard link to a shared file
    img += np.random.default_rng(7).uniform(-0.5, 0.5, img.shape).astype(np.float32)   # dither: no banding in the soft glows
    Image.fromarray(img.clip(0, 255).round().astype(np.uint8)).save(out)
    return out


def brand_js(brand: dict) -> dict:
    """The small part of the brand the runtime needs as data."""
    m = brand.get("motion", {})
    motion = {}
    for k in ("enter", "exit", "pop", "move"):
        if isinstance(m.get(k), dict):
            motion[k] = [m[k].get("duration", 0.5), m[k].get("ease", "power3.out")]
    if "stagger" in m:
        motion["stagger"] = m["stagger"]
    if "wire-draw" in m:
        motion["wire"] = m["wire-draw"]
    bug = brand.get("bug", {})
    ts = brand.get("type-scale", {})
    return {"id": brand.get("id"), "name": brand.get("name"), "motion": motion,
            "type": {"code": ts.get("code", 52), "codeMin": ts.get("code-min", 40), "terminal": ts.get("terminal", 40), "label": ts.get("label", 22)},
            "bug": {"logo": Path(bug.get("logo", "")).name, "dark": Path(bug.get("on-dark", "") or bug.get("logo", "")).name, "height": bug.get("height", 40)},
            "nameCard": brand.get("name-card", {}).get("title", "Instructor")}


def dump_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
