"""Fetch the free starter library (design §9d): Tabler icons, Fluent Emoji props and characters, public-domain music.

Every asset is commercial-use and needs no credit (MIT, CC0, public domain). Each import records its source URL and licence.
Re-runnable: assets that already exist are skipped.

    .venv/bin/python scripts/fetch_free_assets.py [--only icons|props|music]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fzv.assets import add_icon, add_music, add_prop  # noqa: E402
from fzv.config import GLOBAL, RUNTIME, load_yaml  # noqa: E402

UA = {"User-Agent": "fzv-asset-fetch/1.0 (Fuzentrix video tooling)"}
TABLER = "3.49.0"
TABLER_ICONS = """terminal-2 braces brackets variable math-function binary cpu device-desktop device-mobile cloud wifi network api sql filter
sort-ascending arrows-shuffle repeat refresh git-branch bug shield key mail message bell calendar hourglass target trophy rocket puzzle
school notebook pencil chart-line chart-pie chart-dots trash plus minus equal percentage hash list-numbers list-check folder file-code
link home building map-pin eye thumb-up alert-circle info-circle circle-check circle-x stack-2 sitemap hierarchy vector box lock-open
user-check brain microphone video photo player-pause arrows-exchange infinity calculator coin shopping-cart truck ticket movie
building-bank""".split()

# Fluent Emoji (Microsoft, MIT), flat style; people in the medium skin tone. Recoloured to brand variables on import.
FLUENT_PROPS = """Bus|Taxi|Bicycle|Motor scooter|Delivery truck|Locomotive|Airplane|Rocket|Police car|Fire engine|Construction|Stop sign|
Vertical traffic light|House|Office building|School|Hospital|Bank|Convenience store|Factory|Classical building|Stadium|Desktop computer|
Keyboard|Computer mouse|Floppy disk|Battery|Electric plug|Light bulb|Gear|Hammer and wrench|Magnifying glass tilted left|Locked|Key|
Money bag|Credit card|Shopping cart|Package|Envelope|Calendar|Alarm clock|Hourglass done|Stopwatch|Globe showing asia-australia|Cloud|
Robot|Books|Pencil|Graduation cap|Trophy|Bullseye|Ticket|Popcorn|Clapper board|Television|File folder|Open file folder|Clipboard|
Bar chart|Chart increasing|Chart decreasing|Abacus|Puzzle piece|Hot beverage|Red apple|Pizza|Bell|Megaphone|Microphone|Headphone|
Camera|Link|Shield|Fire|High voltage|Card index dividers|Bookmark tabs|Seat|Door|Brain"""
FLUENT_CHARACTERS = """Thinking face|Technologist|Man technologist|Woman technologist|Student|Man student|Woman student|Teacher|Man teacher|
Woman teacher|Police officer|Construction worker|Health worker|Office worker|Man office worker|Woman office worker|Scientist|Mechanic|
Cook|Person raising hand|Person tipping hand|Person shrugging|Detective|Judge|Pilot|Farmer"""

# Public-domain / CC0 piano recordings on Wikimedia Commons (no attribution required).
MUSIC = [
    {"id": "calm-piano", "mood": "calm", "title": "File:Erik Satie - gymnopedies - la 1 ere. lent et douloureux.ogg",
     "licence": "Public domain (Musopen recording, Robin Alciatore)"},
    {"id": "focus-piano", "mood": "focus", "title": "File:Bach-Siloti, Prelude in B minor (J. S. Bach, arranged Siloti), arrangement of Prelude in E minor BWV 855a.ogg",
     "licence": "CC0 1.0 (Felipe Sarro)"},
]


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def names(block: str) -> list[str]:
    return [n.strip() for n in block.replace("\n", "").split("|") if n.strip()]


def kebab(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")


def icons():
    have = (RUNTIME / "icons.svg").read_text(encoding="utf-8")
    added = 0
    for n in TABLER_ICONS:
        if f'id="i-{n}"' in have:
            continue
        url = f"https://cdn.jsdelivr.net/npm/@tabler/icons@{TABLER}/icons/outline/{n}.svg"
        try:
            svg = get(url).decode()
        except Exception as e:  # noqa: BLE001
            print(f"  icon {n}: {e}"); continue
        with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as f:
            f.write(svg)
        add_icon(Path(f.name), n, f"https://tabler.io/icons/icon/{n} (@tabler/icons {TABLER})", "MIT")
        added += 1
    print(f"icons: {added} added from Tabler {TABLER}")


def props():
    tree = json.loads(get("https://api.github.com/repos/microsoft/fluentui-emoji/git/trees/main?recursive=1"))
    sha = tree["sha"]
    paths, medium = {}, {}
    for t in tree["tree"]:
        p = t["path"]
        if p.endswith("_flat.svg") or p.endswith("_flat_default.svg"):
            paths.setdefault(p.split("/")[1], p)
        elif p.endswith("_flat_medium.svg"):                     # people: a realistic medium skin tone (the default is emoji yellow)
            medium[p.split("/")[1]] = p
    lib = load_yaml(GLOBAL / "props" / "manifest.yaml").get("assets") or []
    have = {x["id"] for x in lib}
    fetched = {str(x.get("source", "")).rsplit("/assets/", 1)[-1] for x in lib if "fluentui-emoji" in str(x.get("source", ""))}
    added = 0
    for kind, block in (("prop", FLUENT_PROPS), ("character", FLUENT_CHARACTERS)):
        for n in names(block):
            if urllib.parse.quote(n) in fetched:                 # already imported
                continue
            if n not in paths:
                print(f"  {n}: not in Fluent Emoji"); continue
            pid = kebab(n)
            if pid in have:                                      # clashes with an in-house asset of the same name
                pid += "-alt"
            base = f"https://raw.githubusercontent.com/microsoft/fluentui-emoji/{sha}/"
            svg = get(base + urllib.parse.quote(medium.get(n, paths[n]) if kind == "character" else paths[n])).decode()
            try:
                meta = json.loads(get(base + urllib.parse.quote(f"assets/{n}/metadata.json")))
                tags = " ".join(dict.fromkeys(w for k in meta.get("keywords", [])[:8] for w in k.lower().split()))
            except Exception:  # noqa: BLE001
                tags = n.lower()
            try:
                add_prop(svg, pid, kind, tags, f"https://github.com/microsoft/fluentui-emoji/tree/{sha[:10]}/assets/{urllib.parse.quote(n)}", "MIT",
                         recolour=True, log=lambda m: None)
                have.add(pid)
                added += 1
            except ValueError as e:
                print(f"  {n}: {e}")
    print(f"props: {added} added from Fluent Emoji @ {sha[:10]}")


def music():
    have = {t["id"] for t in load_yaml(GLOBAL / "music" / "manifest.yaml").get("tracks") or []}
    for m in MUSIC:
        if m["id"] in have:
            continue
        q = urllib.parse.urlencode({"action": "query", "format": "json", "titles": m["title"], "prop": "imageinfo", "iiprop": "url"})
        info = next(iter(json.loads(get("https://commons.wikimedia.org/w/api.php?" + q))["query"]["pages"].values()))["imageinfo"][0]
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d) / "in.ogg"
            raw.write_bytes(get(info["url"]))
            out = Path(d) / f"{m['id']}.m4a"                       # AAC, 48 kHz stereo, like the delivery mix
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-ac", "2", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", out], check=True)
            t = add_music(out, m["id"], m["mood"], None, info["descriptionurl"], m["licence"])
        print(f"music: {t['id']} ({t['duration']}s) from {info['descriptionurl']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["icons", "props", "music"])
    a = ap.parse_args()
    for step in (icons, props, music):
        if not a.only or a.only == step.__name__:
            step()
