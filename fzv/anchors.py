"""Word anchors (design §10): a phrase the instructor says resolves to the time of its first word.

Matching is fuzzy and case-insensitive, so English-mode transcripts of Telugu + English speech (romanised, imperfect) still match.
Numbers are the exception: "8" never matches "80" or "18" (rule S2: a value lands on its own word), nor "value2" "value1". A number
Whisper split ("2026" heard as "20, 26") still matches the joined words; a number it misheard needs the transcript's spelling
(`fzv words`). Short phrases (1-3 words) match only when each of their words does.
"""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path


def norm(w: str) -> str:
    return re.sub(r"[^0-9a-z\u0C00-\u0C7F]+", "", w.lower())            # Latin letters, digits and Telugu script


class Transcript:
    def __init__(self, path: Path | None, telugu: bool = True):
        self.words: list[tuple[str, float]] = []
        self.te = None                                   # the Telugu-mode transcript beside it (anchors "@te:..."), when there is one
        if telugu and path and (Path(path).parent / "transcript_te.jsonl").exists():
            self.te = Transcript(Path(path).parent / "transcript_te.jsonl", telugu=False)
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

    def num_at(self, i: int, num: str) -> int:
        """How many transcript words starting at i spell the number `num` (1 = the word itself, 2-3 = a split number), else 0."""
        acc = ""
        for k in range(i, min(i + 3, len(self.words))):
            w = self.words[k][0]
            if not w.isdigit():
                return 0
            acc += w
            if acc == num:
                return k - i + 1
            if not num.startswith(acc):
                return 0
        return 0

    def find(self, phrase: str, after: float = 0.0, before: float = 1e9, occurrence: int = 1, threshold: float = 0.6) -> float | None:
        toks = [norm(t) for t in phrase.split() if norm(t)]
        if not toks or not self.words:
            return None
        target = " ".join(toks)
        n = len(toks)
        hits = []
        idx = [i for i, (_, t) in enumerate(self.words) if after - 0.01 <= t <= before]
        for i in idx:
            if toks[0].isdigit():                                               # numbers match exactly (rule S2)
                k = self.num_at(i, toks[0])
                if not k:
                    continue
                if n == 1:
                    best = 1.0
                else:                                                           # the rest of the phrase after the number
                    rest, j = toks[1:], i + k
                    cw = [w for w, _ in self.words[j:j + len(rest)]]
                    best = SequenceMatcher(None, " ".join(rest), " ".join(cw)).ratio()   # the words after the number must match too
                    if any(a.isdigit() and a != b for a, b in zip(rest, cw)):
                        continue
            else:
                if SequenceMatcher(None, toks[0], self.words[i][0]).ratio() < 0.6:    # the phrase must start here
                    continue
                best = 0.0
                for m in ((n - 1, n, n + 1) if n >= 4 else (n, n + 1)):     # short phrases match in full: "variable store" is not "variable."
                    if m < 1 or i + m > len(self.words):
                        continue
                    cw = [w for w, _ in self.words[i:i + m]]
                    if re.sub(r"\D", "", "".join(toks)) != re.sub(r"\D", "", "".join(cw)):
                        continue                                                # "range 1 to 10" is not "range 1 to 100", "value2" not "value1"
                    if n <= 3 and not all(any(x == w or (len(x) >= 3 and SequenceMatcher(None, x, w).ratio() >= 0.7) for w in cw) for x in toks):
                        continue                                                # every word of a short phrase: "the name is" is not "the data is"
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

    def mentions(self, tok: str, t0: float, t1: float) -> list[float]:
        """When the instructor says `tok` (normalised, see norm) between t0 and t1: numbers exactly (split numbers joined),
        words of 5+ letters closely (romanised transcripts), shorter words exactly."""
        import bisect
        if not hasattr(self, "_ts"):
            self._ts = [t for _, t in self.words]
        out = []
        for i in range(bisect.bisect_left(self._ts, t0 - 0.01), bisect.bisect_right(self._ts, t1)):
            w = self.words[i][0]
            if tok.isdigit():
                if self.num_at(i, tok):
                    out.append(self.words[i][1])
            elif w == tok or (len(tok) >= 5 and abs(len(w) - len(tok)) <= 2 and SequenceMatcher(None, tok, w).ratio() >= 0.85):
                out.append(self.words[i][1])
        return out

    def between(self, t0: float, t1: float) -> list[tuple[str, float]]:
        return [(w, t) for w, t in self.words if t0 <= t < t1]

    def near(self, t: float, span: float = 4.0) -> str:
        """The words around a time, for error messages and revision context."""
        return " ".join(f"{w}@{s:.1f}" for w, s in self.words if t - span <= s <= t + span)
