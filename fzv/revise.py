"""`fzv revise`: timestamped change requests after delivery. Maps each timestamp to its section and scenes, logs the request,
and prints the context the editor (Claude) needs to change edit.yaml. Rebuild/render/finish then redo only what changed."""
from __future__ import annotations

import re
import time

import yaml

from .anchors import Transcript

TS = re.compile(r"(?<![\d:])(\d{1,2}):(\d{2})(?::(\d{2}))?(?:\.(\d+))?")


def parse(request: str) -> list[tuple[float, str]]:
    """'7:41 make the note larger; 12:05 fix the code' -> [(461.0, 'make the note larger'), (725.0, 'fix the code')]"""
    out, ms = [], list(TS.finditer(request))
    for i, m in enumerate(ms):
        h, mm, ss = (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m.group(3) else (0, int(m.group(1)), int(m.group(2)))
        t = h * 3600 + mm * 60 + ss + (float("0." + m.group(4)) if m.group(4) else 0)
        end = ms[i + 1].start() if i + 1 < len(ms) else len(request)
        out.append((t, request[m.end():end].strip(" ;,.-")))
    return out


def context(spec_resolved: dict, t: float, tx: Transcript) -> dict:
    hits = []
    for sec in spec_resolved.get("sections") or []:
        a, b = sec["range"]
        if not (a <= t < b):
            continue
        for i, s in enumerate(sec.get("scenes") or []):
            (name, p), = s.items()
            at, until = p.get("at", a), p.get("until", b)
            if isinstance(at, (int, float)) and at - 1 <= t <= (until if isinstance(until, (int, float)) else b) + 1:
                hits.append({"section": sec.get("id"), "scene": i, "template": name, "at": at, "until": until})
    for i, s in enumerate(spec_resolved.get("studio") or []):
        (name, p), = s.items()
        if isinstance(p.get("at"), (int, float)) and p["at"] - 1 <= t <= (p.get("until") or p["at"] + 5) + 1:
            hits.append({"section": "studio", "scene": i, "template": name, "at": p["at"], "until": p.get("until")})
    return {"t": t, "scenes": hits, "speech": tx.near(t, 5)}


def log_request(proj, request: str, items: list[dict]):
    f = proj.edit / "revisions.md"
    head = "" if f.exists() else "# Revisions\n\nEvery timestamped change request and what changed.\n\n"
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(head + f"## {time.strftime('%Y-%m-%d %H:%M')}\n\n**Request:** {request}\n\n")
        for it in items:
            fh.write(f"- {int(it['t'] // 60)}:{it['t'] % 60:05.2f} → " + (", ".join(f"{s['section']} scene {s['scene']} ({s['template']})" for s in it["scenes"]) or "no scene (add one)") + "\n")
        fh.write("\n**Status:** pending\n\n")
