"""Transcription (design §12.3): Whisper large-v3-turbo in English mode, short chunks split at pauses, appended per chunk
to edit/transcript.jsonl. The backend is chosen for the machine: mlx-whisper on Apple Silicon, faster-whisper elsewhere,
or the whisper.cpp CLI. The transcript is for timing and content only; it is never burned in unless subtitles are on."""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from . import media


def backend(pref: str | None = None) -> str | None:
    order = [pref] if pref else []
    order += ["mlx", "faster", "whispercpp"]
    for b in order:
        if b == "mlx" and platform.system() == "Darwin" and platform.machine() == "arm64":
            try:
                import mlx_whisper  # noqa: F401
                return "mlx"
            except ImportError:
                pass
        if b == "faster":
            try:
                import faster_whisper  # noqa: F401
                return "faster"
            except ImportError:
                pass
        if b == "whispercpp" and shutil.which("whisper-cli"):
            return "whispercpp"
    return None


def chunk_points(x: np.ndarray, sr: int, start: float, end: float, cmin: float, cmax: float) -> list[float]:
    """Cut points at the longest pause inside each [cmin, cmax] window."""
    hop = int(sr * 0.02)
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    db = np.convolve(db, np.ones(5) / 5, mode="same")
    quiet = db < np.percentile(db, 12) + 3
    cuts, t = [start], start
    while t < end - 0.5:
        lo, hi = int((t + cmin) / 0.02), int(min(end, t + cmax) / 0.02)
        if hi <= lo:
            cuts.append(end); break
        seg = quiet[lo:hi]
        best, bi, i = 0, None, 0
        while i < len(seg):
            if seg[i]:
                j = i
                while j < len(seg) and seg[j]:
                    j += 1
                if j - i > best:
                    best, bi = j - i, i + (j - i) // 2
                i = j
            else:
                i += 1
        t = (lo + bi) * 0.02 if bi is not None and best >= 8 else min(end, t + cmax)
        cuts.append(round(t, 2))
    return cuts


FALLBACK = (0.0, 0.2, 0.4)      # Whisper re-decodes a chunk at a higher temperature when its text compresses too well (a loop)


def collapse_repeats(words: list[dict], keep: int = 2) -> list[dict]:
    """Drop runs of the same word repeated more than `keep` times (a Whisper hallucination: "colon colon colon …")."""
    out, run = [], 0
    for w in words:
        same = out and w["w"].lower().strip(".,!?-") == out[-1]["w"].lower().strip(".,!?-")
        run = run + 1 if same else 1
        if run <= keep:
            out.append(w)
    return out


def tidy_text(text: str, keep: int = 2) -> str:
    import re
    text = re.sub(r"\b((\w+)[-\s]+)(?:\2[-\s]+){%d,}" % keep, lambda m: (m.group(1) * keep).rstrip("- ") + " ", text + " ").strip()
    return text


def transcribe(wav16: Path, out: Path, cfg: dict, start: float = 0.0, end: float | None = None, log=print, prefer: str | None = None) -> Path:
    be = backend(prefer)
    if not be:
        raise SystemExit("no transcription backend: install mlx-whisper (Apple Silicon) or faster-whisper, or put whisper-cli on PATH")
    x, sr = media.read_wav_mono(wav16)
    end = end or len(x) / sr
    cuts = chunk_points(x, sr, start, end, cfg.get("chunk_min_s", 5), cfg.get("chunk_max_s", 14))
    lang = cfg.get("language", "en")
    done_to = 0.0
    if out.exists():                                   # resume: chunk points are deterministic, skip the chunks already written
        rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
        done_to = rows[-1]["end"] if rows else 0.0
    todo = [(a, b) for a, b in zip(cuts, cuts[1:]) if b > done_to + 1e-6]
    log(f"transcribe: {be}, {len(cuts) - 1} chunks ({len(todo)} to do), {end - start:.0f}s of audio")
    model = None
    if be == "faster":
        from faster_whisper import WhisperModel
        model = WhisperModel("large-v3-turbo" if "turbo" in cfg.get("model", "") else cfg.get("model", "large-v3"), compute_type="auto")
    with open(out, "a", encoding="utf-8") as f:
        for a, b in todo:
            seg = x[int(a * sr):int(b * sr)]
            if be == "mlx":
                import mlx_whisper
                r = mlx_whisper.transcribe(seg, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language=lang,
                                           word_timestamps=True, condition_on_previous_text=False, temperature=FALLBACK,
                                           compression_ratio_threshold=2.4)
                words = [{"w": w["word"].strip(), "s": round(w["start"] + a, 2)} for s in r["segments"] for w in s.get("words", [])]
                text = r["text"].strip()
            elif be == "faster":
                segs, _ = model.transcribe(seg, language=lang, word_timestamps=True, condition_on_previous_text=False, temperature=list(FALLBACK),
                                           compression_ratio_threshold=2.4)
                segs = list(segs)
                words = [{"w": w.word.strip(), "s": round(w.start + a, 2)} for s in segs for w in (s.words or [])]
                text = " ".join(s.text.strip() for s in segs)
            else:
                with tempfile.TemporaryDirectory() as d:
                    cw = Path(d) / "c.wav"
                    media.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", wav16, cw])
                    subprocess.run(["whisper-cli", "-l", lang, "-ojf", "-of", str(Path(d) / "o"), str(cw)], capture_output=True)
                    j = json.loads((Path(d) / "o.json").read_text())
                words = [{"w": t["text"].strip(), "s": round(t["offsets"]["from"] / 1000 + a, 2)} for s in j.get("transcription", []) for t in s.get("tokens", []) if t["text"].strip()]
                text = " ".join(s["text"].strip() for s in j.get("transcription", []))
            words, text = collapse_repeats(words), tidy_text(text)
            f.write(json.dumps({"start": a, "end": b, "text": text, "words": words}, ensure_ascii=False) + "\n")
            f.flush()
    return out
