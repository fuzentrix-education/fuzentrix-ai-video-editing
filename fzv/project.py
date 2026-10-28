"""The video folder model (design §3.2): raw cuts and recordings in, `edit/` and the final video out, side by side."""
from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

import yaml

from . import media
from .config import deep_merge, defaults, load_yaml

FINAL_RE = re.compile(r" - Edited( v\d+)?\.mp4$", re.I)


class Project:
    def __init__(self, folder: str | Path):
        self.folder = Path(folder).expanduser().resolve()
        if not self.folder.is_dir():
            raise SystemExit(f"not a folder: {self.folder}")
        self.edit = self.folder / "edit"
        for sub in ("built", "comp", "out", "audio", "_prev", "sections"):
            (self.edit / sub).mkdir(parents=True, exist_ok=True)

    # ---------- paths ----------
    def p(self, name: str) -> Path:
        return self.edit / name

    @property
    def project_yaml(self) -> Path: return self.p("project.yaml")
    @property
    def spec_path(self) -> Path: return self.p("edit.yaml")

    # ---------- project.yaml ----------
    def load(self) -> dict:
        return load_yaml(self.project_yaml) if self.project_yaml.exists() else {}

    def save(self, data: dict):
        with open(self.project_yaml, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    def update(self, **kw):
        d = self.load()
        d.update(kw)
        self.save(d)
        return d

    def stage_done(self, stage: str, **info):
        d = self.load()
        d.setdefault("stages", {})[stage] = dict(info, at=time.strftime("%Y-%m-%d %H:%M:%S"))
        self.save(d)

    # ---------- inputs ----------
    def media_files(self) -> list[Path]:
        return sorted(f for f in self.folder.iterdir() if f.suffix.lower() in media.VIDEO_EXT and not FINAL_RE.search(f.name) and not f.name.startswith("."))

    def prompt(self) -> str:
        f = self.folder / "prompt.md"
        return f.read_text(encoding="utf-8") if f.exists() else ""

    def prompt_fields(self) -> dict:
        """Simple `Key: value` lines from prompt.md (Brand, Style, Subtitles, Music, Mode, Recording, Title)."""
        out = {}
        for ln in self.prompt().splitlines():
            m = re.match(r"^\s*(?:screen[\s-]+)?(brand|style|subtitles|music|sfx|mode|title|recordings?|presenter box|instructor box|review)\s*:\s*(.+?)\s*(#.*)?$", ln, re.I)
            if m:
                out[m.group(1).lower().rstrip("s") if m.group(1).lower().startswith("record") else m.group(1).lower()] = m.group(2).strip()
        t = re.search(r"^#\s+(.+)$", self.prompt(), re.M)
        if t and "title" not in out:
            out["title"] = t.group(1).strip()
        return out

    def settings(self) -> dict:
        """Global defaults with this video's prompt fields applied (the prompt wins, design D9)."""
        d = defaults()
        f = self.prompt_fields()
        over = {}
        if "brand" in f:
            over["brand"] = f["brand"].split()[0].lower()
        if "mode" in f:
            over["mode"] = f["mode"].split()[0].lower()
        if "subtitles" in f:
            v = f["subtitles"].lower()
            over["subtitles"] = {"enabled": v.startswith("on") or v.startswith("yes")}
            if "telugu" in v:
                over["subtitles"]["language"] = "te+en"
        if "music" in f:
            v = f["music"].lower()
            over["music"] = {"enabled": not (v.startswith("off") or v.startswith("no"))}
            if over["music"]["enabled"]:
                over["music"]["track"] = re.split(r"[,\s]", v)[0]
                if "low" in v or "soft" in v:
                    over["music"]["rel_lufs"] = -22
                elif "high" in v or "loud" in v:
                    over["music"]["rel_lufs"] = -14
        if "sfx" in f:
            v = f["sfx"].lower()
            over["sfx"] = {"enabled": not v.startswith(("off", "no", "none"))}
            if "minimal" in v or "less" in v or "few" in v:
                over["sfx"]["minor"] = False
            if "library" in v and "only" in v:
                over["sfx"]["fallback"] = "none"
        pb = f.get("presenter box") or f.get("instructor box")
        if pb:
            over["presenter"] = {"corner_box": not any(w in pb.lower() for w in ("off", "no", "none", "false"))}
        if "review" in f:                                       # Review: on | off | beats (beat sheet only) | storyboard (storyboard only)
            v = f["review"].lower()
            if "no preview" in v or "preview off" in v:                 # e.g. "Review: on, no preview"
                over["review"] = {"preview": "off"}
            elif "preview video" in v or "video preview" in v:          # e.g. "Review: on, preview video"
                over["review"] = {"preview": "video"}
            elif v.startswith(("off", "no", "none", "skip")):
                over["review"] = {"beats": "off", "storyboard": "off", "preview": "off"}
            elif "beat" in v and "storyboard" not in v:
                over["review"] = {"beats": "required", "storyboard": "off", "preview": "off"}
            elif "storyboard" in v and "beat" not in v:
                over["review"] = {"beats": "off", "storyboard": "required", "preview": "browser"}
            else:
                over["review"] = {"beats": "required", "storyboard": "required", "preview": "browser"}
        rec = f.get("recording") or f.get("recordings")
        if rec:
            v = rec.lower()
            hide = any(w in v for w in ("reference", "off", "hide", "don't", "dont", "do not", "not ", "no ")) or v.strip() == "no"
            over["recordings"] = {"use": "reference" if hide else "show"}
            if "exact" in v or "as typed" in v:
                over["recordings"]["corrections"] = "exact"
        return deep_merge(d, over)

    # ---------- output ----------
    def output_path(self, title: str) -> Path:
        name = defaults()["output"]["name"].format(title=title.strip() or self.folder.name)
        return self.folder / name

    def archive_previous(self, out: Path):
        """Move an existing final into edit/_prev/ with a timestamp; never delete it."""
        if out.exists():
            stamp = time.strftime("%Y%m%d-%H%M%S")
            shutil.move(str(out), str(self.edit / "_prev" / f"{out.stem} ({stamp}){out.suffix}"))
