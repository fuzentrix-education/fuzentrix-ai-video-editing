"""Illustrations for picture moments (rule P1): when she uses an analogy or a real-world example, a picture shows it.

1. The library first: SVGs in global/props with kind `illustration`, in their own natural colours (plus the props and characters).
2. Else the web: free sources whose licences allow commercial use with no credit (checked on their own pages, 2026-11-04):
   - lukasz-adam        lukaszadam.com/illustrations: "under the CC0 license (MIT license) … No attribution required"; flat, one accent
   - illlustrations-co  illlustrations.co: the original 100-illustration set, "License CC0"
   - commons            Wikimedia Commons SVGs whose licence is CC0 or public domain (read from each file's own licence field)
   - openverse          api.openverse.org images with license cc0 / pdm, SVG only (often down: tried twice, then skipped)
   Candidates come back with a contact sheet to look at; the chosen one is imported (cleaned, scripts stripped, cropped; its own
   natural colours kept, 2026-11-05) with its source and licence recorded, so the next video finds it in the library.
3. Nothing fits: Claude draws one in the house style (global/props/ILLUSTRATION-STYLE.md) and imports it as `generated`.
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from .config import GLOBAL, REPO

UA = "fzv-illustration-sourcing/1.0 (Fuzentrix video editing)"       # never an email address (see the memory of 2026-10-26)
CACHE = REPO / ".cache" / "illustrations"
LICENCES = {
    "lukasz-adam": ("CC0 1.0 (Lukasz Adam; the page also says MIT; no attribution required)", "https://lukaszadam.com/illustrations"),
    "illlustrations-co": ("CC0 1.0 (illlustrations.co, Vijay Verma: the original 100-illustration set)", "https://illlustrations.co/explore"),
}
STOP = {"a", "an", "the", "of", "and", "or", "to", "in", "on", "for", "with", "is", "it"}


def _get(url: str, timeout: int = 30, limit: int = 4_000_000) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"{url}: larger than {limit // 1_000_000} MB")
    return data


def _words(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP]


def _score(query: list[str], text: str) -> float:
    t = _words(text)
    if not t:
        return 0.0
    hit = sum(1 for q in query if any(w == q or (len(q) > 3 and (w.startswith(q) or q.startswith(w)) and min(len(w), len(q)) > 3) for w in t))
    return hit / len(query)


# ---------- the library ----------
def library() -> list[dict]:
    man = yaml.safe_load((GLOBAL / "props" / "manifest.yaml").read_text(encoding="utf-8")) or {}
    return man.get("assets") or []


def local(query: str, kinds=("illustration", "prop", "character")) -> list[dict]:
    q = _words(query)
    out = []
    for a in library():
        if a.get("kind") not in kinds:
            continue
        s = _score(q, " ".join(str(a.get(k, "")) for k in ("id", "title", "tags", "set")))
        if s > 0:
            out.append(dict(a, score=round(s + (0.1 if a.get("kind") == "illustration" else 0), 2)))
    return sorted(out, key=lambda a: -a["score"])


# ---------- the web ----------
def _cached_index(name: str, build, max_age_days: int = 14) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{name}.json"
    if f.exists() and time.time() - f.stat().st_mtime < max_age_days * 86400:
        return json.loads(f.read_text())
    rows = build()
    f.write_text(json.dumps(rows))
    return rows


def _lukasz() -> list[dict]:
    t = _get("https://lukaszadam.com/illustrations").decode("utf-8", "ignore")
    rows = []
    for title, src in re.findall(r'<h3[^>]*>([^<]+)</h3>\s*<img src="(/images/free-illustrations/[^"]+\.svg)"', t):
        rows.append({"source": "lukasz-adam", "title": html.unescape(title).strip(), "url": "https://lukaszadam.com" + src,
                     "page": LICENCES["lukasz-adam"][1], "licence": LICENCES["lukasz-adam"][0]})
    return rows


def _illlustrations() -> list[dict]:
    t = _get("https://illlustrations.co/explore").decode("utf-8", "ignore")
    titles = {}
    for n, title in re.findall(r"Day (\d+): ([^\\\"<]{2,60})", t):
        titles.setdefault(int(n), html.unescape(title).strip())
    base = "https://bnlhgpfxkkevipjjkzvn.supabase.co/storage/v1/object/public/illlustrations-v1/day-{}/illustration.svg"
    return [{"source": "illlustrations-co", "title": titles[n], "url": base.format(n), "page": LICENCES["illlustrations-co"][1],
             "licence": LICENCES["illlustrations-co"][0]} for n in sorted(titles) if 1 <= n <= 100]      # the CC0 set: days 1-100


def _commons(query: str, n: int = 20) -> list[dict]:
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filemime:image/svg+xml", "gsrnamespace": 6,
        "gsrlimit": n, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiextmetadatafilter": "LicenseShortName|Artist"})
    pages = (json.loads(_get(u)).get("query") or {}).get("pages") or {}
    out = []
    for pg in sorted(pages.values(), key=lambda p: p.get("index", 99)):
        ii = (pg.get("imageinfo") or [{}])[0]
        lic = ((ii.get("extmetadata") or {}).get("LicenseShortName") or {}).get("value", "")
        if not re.search(r"cc0|public domain|^pd\b|pd-", lic, re.I):           # CC0 / public domain only: no credit, no share-alike
            continue
        artist = re.sub(r"<[^>]+>", "", ((ii.get("extmetadata") or {}).get("Artist") or {}).get("value", ""))[:60]
        out.append({"source": "commons", "title": pg.get("title", "").removeprefix("File:").rsplit(".", 1)[0], "url": ii.get("url", "").split("?")[0],
                    "page": ii.get("descriptionurl", ""), "licence": f"{lic} ({artist or 'Wikimedia Commons'})"})
    brandish = re.compile(r"logo|flag|coat of arms|emblem|seal of|badge|wordmark|trademark|prim-config", re.I)   # no logos or official marks
    return [r for r in out if r["url"].endswith(".svg") and not brandish.search(r["title"])]


def _openverse(query: str, n: int = 8) -> list[dict]:
    u = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode({"q": query, "license": "cc0,pdm", "extension": "svg", "page_size": n}, safe=",")
    for attempt in range(2):
        try:
            d = json.loads(_get(u))
            break
        except Exception:
            if attempt:
                raise
            time.sleep(2)
    return [{"source": f"openverse/{r.get('source', '')}", "title": r.get("title", ""), "url": r["url"], "page": r.get("foreign_landing_url", ""),
             "licence": f"{(r.get('license') or '').upper()} ({r.get('creator') or 'unknown'}, via Openverse)"} for r in d.get("results", []) if r.get("url")]


def online(query: str, limit: int = 24, log=print) -> list[dict]:
    """Candidates from the free sources, best title matches first (Openverse adds its own relevance order)."""
    q = _words(query)
    rows = []
    for name, build in (("lukasz-adam", _lukasz), ("illlustrations-co", _illlustrations)):
        try:                                                         # titles plus file names ("Coder Illustration 1" is coder-2.svg)
            for r in _cached_index(name, build):                    # the curated flat sets come first: they match the house style
                sc = _score(q, r["title"] + " " + Path(urllib.parse.urlparse(r["url"]).path).stem.replace("_", " ").replace("-", " "))
                rows.append(dict(r, score=round(0.5 + 0.5 * sc, 2) if sc else 0))
        except Exception as e:                                       # a source being down never stops the search
            log(f"illus: {name} unavailable ({e})")
    rows = [r for r in rows if r["score"] > 0]
    for name, fn in (("commons", _commons), ("openverse", _openverse)):
        try:
            rows += [dict(r, score=round(0.45 - i * 0.01, 2)) for i, r in enumerate(fn(query))]
        except Exception as e:
            log(f"illus: {name} unavailable ({e})")
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: -r["score"]):
        if r["url"] not in seen:
            seen.add(r["url"]); out.append(r)
    return out[:limit]


def sheet(cands: list[dict], out: Path) -> Path:
    """A contact sheet of candidates (numbered), to look at before choosing: <out>.html and <out>.png."""
    import hashlib
    import subprocess
    pv = CACHE / "previews"
    pv.mkdir(parents=True, exist_ok=True)
    for c in cands:
        if c.get("url") and not c.get("file"):
            f = pv / (hashlib.sha1(c["url"].encode()).hexdigest()[:16] + ".svg")
            try:
                if not f.exists():
                    f.write_bytes(_get(c["url"], limit=3_000_000))
                c["file"] = str(f)
            except Exception:
                pass
    cells = "".join(f'<figure><div class="p"><img src="{html.escape("file://" + c["file"] if c.get("file") else c.get("url", ""))}"></div><figcaption><b>{i + 1}</b> {html.escape(c.get("title") or c.get("id", ""))}'
                    f'<br><span>{html.escape(c.get("source", c.get("set", "")))}</span></figcaption></figure>' for i, c in enumerate(cands))
    page = ("<html><body style='margin:0;padding:18px;background:#F4F7FC;font:14px system-ui'><style>.g{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}"
            ".p{background:#fff;border-radius:10px;height:150px;padding:8px;box-sizing:border-box;overflow:hidden}.p img{width:100%;height:100%;object-fit:contain;display:block}"
            "figure{margin:0}span{color:#5E6E8C;font-size:12px}</style><div class='g'>" + cells + "</div></body></html>")
    h = out.with_suffix(".html")
    h.write_text(page, encoding="utf-8")
    subprocess.run(["node", str(REPO / "node" / "sample.mjs"), "still", str(h), str(out.with_suffix(".png")), "1400", "800"], cwd=REPO, capture_output=True, timeout=120)
    return out.with_suffix(".png")


# ---------- import ----------
def sanitize(svg: str) -> str:
    """Web SVGs may carry scripts, event handlers, external images or embedded HTML: none of that goes into a video."""
    svg = re.sub(r"<script\b.*?</script>|<foreignObject\b.*?</foreignObject>", "", svg, flags=re.S | re.I)
    svg = re.sub(r'\son[a-z]+\s*=\s*"[^"]*"', "", svg, flags=re.I)
    svg = re.sub(r'<image\b[^>]*href\s*=\s*"https?:[^"]*"[^>]*/?>', "", svg, flags=re.I)
    return svg


def fit(svg: str) -> str:
    """Drop a full-canvas background and tiny credit marks at the edges, and crop the viewBox to the picture (headless Chrome)."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        i, o = Path(d) / "in.svg", Path(d) / "out.svg"
        i.write_text(svg, encoding="utf-8")
        subprocess.run(["node", str(REPO / "node" / "sample.mjs"), "svgfit", str(i), str(o)], cwd=REPO, capture_output=True, timeout=120)
        return o.read_text(encoding="utf-8") if o.exists() else svg


def add(src: str, ill_id: str, title: str, tags: str, source: str, licence: str, set_name: str = "", log=print, crop: bool = True,
        natural: bool = True) -> dict:
    """Download (or read) one SVG, clean and crop it (natural colours kept; `natural=False` recolours it to the kit), and register
    it in global/props as kind `illustration`."""
    from .assets import add_prop
    data = _get(src).decode("utf-8", "ignore") if re.match(r"https?://", src) else Path(src).read_text(encoding="utf-8")
    if "<svg" not in data:
        raise ValueError("not an SVG (only vector illustrations: they stay sharp at any size)")
    data = sanitize(data)
    if crop:
        data = fit(data)
    set_name = set_name or (urllib.parse.urlparse(source).netloc if source.startswith("http") else source)
    return add_prop(data, ill_id, "illustration", tags, source, licence, style="flat", recolour=True, log=log,
                    extra={"title": title, "set": set_name}, natural=natural)
