"""Subtitles (design §9a): off by default; when a prompt switches them on, segment the transcript into caption cues."""
from __future__ import annotations

import json
from pathlib import Path


def cues(transcript: Path, max_chars: int = 42, max_lines: int = 2, min_s: float = 1.0, max_s: float = 6.0) -> list[dict]:
    words = []
    for l in transcript.read_text(encoding="utf-8").splitlines():
        if l.strip():
            words += [(w["w"], float(w["s"])) for w in json.loads(l).get("words", []) if w.get("w")]
    out, cur, start = [], [], None
    limit = max_chars * max_lines
    for i, (w, s) in enumerate(words):
        if start is None:
            start = s
        nxt = words[i + 1][1] if i + 1 < len(words) else s + 0.6
        cur.append(w)
        text = " ".join(cur)
        if len(text) >= limit - 8 or nxt - s > 0.8 or nxt - start > max_s or w.endswith((".", "?", "!")):
            end = min(nxt, start + max_s, s + 0.9)
            out.append({"text": wrap(text, max_chars), "at": round(start, 2), "until": round(max(end, start + min_s), 2)})
            cur, start = [], None
    return out


def wrap(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    cut = text.rfind(" ", 0, len(text) // 2 + 6)
    return text[:cut] + "\n" + text[cut + 1:] if cut > 0 else text
