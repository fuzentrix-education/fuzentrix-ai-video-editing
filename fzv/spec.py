"""The edit spec (edit/edit.yaml): load, resolve times, plan clips.

Times in a spec are global seconds of the raw cut, written as
  - a number: 279.6
  - an anchor: "@For i in range" or "@if i equal to#2" (second occurrence), resolved from the transcript
  - a relative time: "+0.5" (from the scene's `at`)
Plate scenes live in `sections`; studio-layer scenes (rule L4) in `studio`; both render as transparent clips.
"""
from __future__ import annotations

import copy
import math
import re

import yaml

from .anchors import Transcript

TIME_KEYS = {"at", "until", "run", "caret_off", "active_off", "vs_at", "emphasis_at", "focus_at", "val", "chk", "res", "pr", "out", "hit"}
TIME_LISTS = {"times", "row_at", "cues"}
REL = re.compile(r"^[+-]\d+(\.\d+)?$")


class SpecError(Exception):
    pass


def load(path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def scene_items(scenes):
    """Scenes are written as one-key mappings {template: params}; yield (template, params)."""
    for s in scenes or []:
        if not isinstance(s, dict) or len(s) != 1:
            raise SpecError(f"a scene must be a one-key mapping {{template: params}}, got: {str(s)[:80]}")
        (name, params), = s.items()
        yield name, (params or {})


class Resolver:
    def __init__(self, transcript: Transcript):
        self.tx = transcript
        self.errors: list[str] = []
        self.anchors: list[tuple[str, float]] = []

    def time(self, v, base: float | None, lo: float, hi: float, where: str):
        if v is None or isinstance(v, (int, float)):
            return v
        s = str(v).strip()
        if REL.match(s):
            if base is None:
                self.errors.append(f"{where}: relative time {s} without an `at`")
                return None
            return round(base + float(s), 3)
        if s.startswith("@"):
            phrase, occ = s[1:], 1
            m = re.match(r"^(.*)#(\d+)$", phrase)
            if m:
                phrase, occ = m.group(1), int(m.group(2))
            t = self.tx.find(phrase, after=lo, before=hi, occurrence=occ)
            if t is None:
                self.errors.append(f"{where}: anchor '{phrase}' not found between {lo:.1f}s and {hi:.1f}s")
                return None
            self.anchors.append((s, t))
            return t
        try:
            return float(s)
        except ValueError:
            return v

    def walk(self, obj, base, lo, hi, where):
        if isinstance(obj, dict):
            out = {}
            # resolve `at` first so relative times inside can use it
            if "at" in obj:
                out["at"] = self.time(obj["at"], base, lo, hi, where + ".at")
                base = out["at"] if isinstance(out["at"], (int, float)) else base
            for k, v in obj.items():
                if k == "at":
                    continue
                if isinstance(k, str) and (k in TIME_KEYS or k.endswith("_at")):
                    out[k] = self.time(v, base, max(lo, (base or lo) - 3), hi, f"{where}.{k}")
                elif k in TIME_LISTS and isinstance(v, list):
                    out[k] = [self.time(x, base, max(lo, (base or lo) - 3), hi, f"{where}.{k}") for x in v]
                elif k == "parts" and isinstance(v, list):
                    out[k] = [[p[0], self.time(p[1], base, max(lo, (base or lo) - 3), hi, f"{where}.parts")] for p in v]
                else:
                    out[k] = self.walk(v, base, lo, hi, f"{where}.{k}")
            return out
        if isinstance(obj, list):
            return [self.walk(x, base, lo, hi, f"{where}[{i}]") for i, x in enumerate(obj)]
        return obj


def snap(t: float, fps: int, mode: str = "round") -> float:
    f = {"round": round, "floor": math.floor, "ceil": math.ceil}[mode](t * fps + (1e-6 if mode == "floor" else -1e-6 if mode == "ceil" else 0))
    return f / fps


def resolve(spec: dict, transcript: Transcript, duration: float) -> tuple[dict, list[str]]:
    """Return the spec with every time resolved to seconds, plus a list of problems."""
    r = Resolver(transcript)
    out = copy.deepcopy(spec)
    secs = []
    for i, sec in enumerate(spec.get("sections") or []):
        lo, hi = sec["range"]
        scenes = []
        for name, params in scene_items(sec.get("scenes")):
            rp = r.walk(params, None, lo - 1, hi + 1, f"{sec.get('id', i)}.{name}")
            if isinstance(rp.get("at"), (int, float)):
                lo_next = rp["at"]
            scenes.append({name: rp})
        secs.append(dict(sec, scenes=scenes))
    out["sections"] = secs
    studio = []
    for name, params in scene_items(spec.get("studio")):
        studio.append({name: r.walk(params, None, 0, duration, f"studio.{name}")})
    out["studio"] = studio
    return out, r.errors


def plan_clips(spec: dict, cuts: list[dict], fps: int, bug_layers: list[str]) -> list[dict]:
    """Plate clips = sections; studio clips = studio shots (cuts.json) with the studio scenes that start inside them."""
    clips = []
    for sec in spec.get("sections") or []:
        a, b = snap(sec["range"][0], fps), snap(sec["range"][1], fps)
        scenes = [{"template": n, "params": p} for n, p in scene_items(sec["scenes"])]
        if "plate" in bug_layers and sec.get("bug", True) and not any(s["template"] == "bug" for s in scenes):
            scenes.insert(0, {"template": "bug", "params": {"at": sec.get("bug_at")}})
        clips.append({"id": sec.get("id", f"s{len(clips):02d}"), "layer": "plate", "start": a, "end": b, "scenes": scenes})
    studio_scenes = [{"template": n, "params": p} for n, p in scene_items(spec.get("studio"))]
    k = 0
    for c in cuts:
        if c["kind"] != "studio":
            continue
        a, b = snap(c["start"], fps, "floor"), snap(c["end"], fps, "ceil")
        inside = [s for s in studio_scenes if isinstance(s["params"].get("at"), (int, float)) and c["start"] - 0.5 <= s["params"]["at"] < c["end"]]
        scenes = ([{"template": "bug", "params": {}}] if "studio" in bug_layers else []) + inside
        clips.append({"id": f"st{k:02d}", "layer": "studio", "start": a, "end": b, "scenes": scenes, "cut": [c["start"], c["end"]], "has_content": bool(inside)})
        k += 1
    return clips
