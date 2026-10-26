"""Word anchors (design §10): a phrase the instructor says resolves to the time of its first word.

Matching is fuzzy and case-insensitive, so English-mode transcripts of Telugu + English speech (romanised, imperfect) still match.
"""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path


def norm(w: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", w.lower())


class Transcript:
    def __init__(self, path: Path | None):
        self.words: list[tuple[str, float]] = []
        if path and Path(path).exists():
            for line in Path(path).read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                for w in r.get("words", []):
                    n = norm(w.get("w", ""))
                    if n:
                        self.words.append((n, float(w["s"])))
        self.words.sort(key=lambda x: x[1])

    def chunks(self, path: Path) -> list[dict]:
        return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]

    def find(self, phrase: str, after: float = 0.0, before: float = 1e9, occurrence: int = 1, threshold: float = 0.6) -> float | None:
        toks = [norm(t) for t in phrase.split() if norm(t)]
        if not toks or not self.words:
            return None
        target = " ".join(toks)
        n = len(toks)
        hits = []
        idx = [i for i, (_, t) in enumerate(self.words) if after - 0.01 <= t <= before]
        for i in idx:
            if SequenceMatcher(None, toks[0], self.words[i][0]).ratio() < 0.6:    # the phrase must start here
                continue
            best = 0.0
            for m in (n - 1, n, n + 1):
                if m < 1 or i + m > len(self.words):
                    continue
                cw = [w for w, _ in self.words[i:i + m]]
                score = 0.5 * SequenceMatcher(None, target, " ".join(cw)).ratio() + 0.5 * SequenceMatcher(None, toks, cw).ratio()
                best = max(best, score)
            if best >= threshold:
                if hits and self.words[i][1] - hits[-1][1] < 1.0:       # same spoken phrase, keep the better start
                    if best > hits[-1][2]:
                        hits[-1] = (i, self.words[i][1], best)
                    continue
                hits.append((i, self.words[i][1], best))
        if len(hits) < occurrence:
            return None
        return round(hits[occurrence - 1][1], 2)

    def near(self, t: float, span: float = 4.0) -> str:
        """The words around a time, for error messages and revision context."""
        return " ".join(f"{w}@{s:.1f}" for w, s in self.words if t - span <= s <= t + span)
