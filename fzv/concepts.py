"""Concept moments (rule V3): where the instructor names something the screen should show, from global/concepts.yaml."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .config import GLOBAL, load_yaml

_norm = lambda w: re.sub(r"[^a-z0-9,+]", "", w.lower())


def lexicon() -> list[dict]:
    f = GLOBAL / "concepts.yaml"
    return load_yaml(f).get("concepts") or [] if f.exists() else []


def moments(transcript: Path, gap_s: float = 12.0) -> list[dict]:
    """[{id, t, phrase, templates, show}] in time order; one per concept per `gap_s`."""
    if not transcript.exists():
        return []
    words = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        if line.strip():
            for w in json.loads(line).get("words") or []:
                for part in re.split(r"[\s-]+", w["w"]):
                    if _norm(part):
                        words.append((_norm(part), w["s"]))
    toks = [w for w, _ in words]
    out, last = [], {}
    for c in lexicon():
        for ph in c.get("phrases") or []:
            pt = [_norm(x) for x in re.split(r"[\s-]+", ph.strip()) if _norm(x)]
            if not pt:
                continue
            for i in range(len(toks) - len(pt) + 1):
                if toks[i:i + len(pt)] == pt:
                    t = words[i][1]
                    if t - last.get(c["id"], -1e9) >= gap_s:
                        out.append({"id": c["id"], "t": round(t, 2), "phrase": ph.strip(), "templates": c.get("templates") or [], "show": c.get("show", "")})
                        last[c["id"]] = t
    return sorted(out, key=lambda m: m["t"])


def covered(m: dict, spec: dict, before: float = 3.0, after: float = 10.0) -> bool:
    """A matching template is on screen around the moment."""
    for sec in spec.get("sections") or []:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            if name in m["templates"] and isinstance(p, dict) and isinstance(p.get("at"), (int, float)):
                end = p["until"] if isinstance(p.get("until"), (int, float)) else sec["range"][1]
                if p["at"] <= m["t"] + after and end >= m["t"] - before:
                    return True
    return False
