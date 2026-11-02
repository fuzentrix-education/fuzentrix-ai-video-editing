"""Listening check (part of `fzv verify`): measure the final mix the way a viewer would hear it and say what sounds wrong, in plain words.

- Each placed effect against her voice at the same moment: buried (more than 32 dB under it while she speaks) or too loud (less than
  12 dB under her usual speaking level).
- Clipping (runs of samples at full scale) and a peak too close to the limit, on the final video's own sound.
- Background noise under her voice, and the music's level against her voice while she speaks.
Advisory: the notes appear on the review page and in verify.json; they don't fail the video. No models: plain measurements, a few
seconds per video. (Earshot was tried for this on 2026-11-02 and left out: under continuous speech it can't tell an effect from a
syllable, and these measurements caught what it missed.)
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from . import media

SR = 16000


def _pcm(path: Path, sr: int = SR) -> np.ndarray:
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.float32).astype(np.float64)


def _frames_db(x: np.ndarray, hop: float = 0.05) -> np.ndarray:
    h = int(SR * hop)
    n = len(x) // h
    return 20 * np.log10(np.sqrt(np.mean(x[: n * h].reshape(n, h) ** 2, 1)) + 1e-9) if n else np.zeros(0)


def clipping(path: Path) -> dict:
    """Runs of 3+ samples at full scale in the final's sound (decoded at 48 kHz stereo, interleaved)."""
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "2", "-ar", "48000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.abs(np.frombuffer(b, np.float32))
    hot = x >= 0.999
    if not hot.any():
        return {"runs": 0, "times": []}
    edges = np.flatnonzero(np.diff(np.concatenate([[0], hot.astype(np.int8), [0]])))
    starts, ends = edges[::2], edges[1::2]
    long_runs = starts[(ends - starts) >= 3]
    return {"runs": int(len(long_runs)), "times": [round(float(s) / (48000 * 2), 2) for s in long_runs[:5]]}


def effect_levels(voice: np.ndarray, sfx: np.ndarray, used: list) -> list[dict]:
    """Each placed effect's loudest 100 ms against her voice at that same moment (`local_db`, for masking) and against her usual
    speaking level (`overall_db`, for loudness). Both tracks are taken before the final loudness step, which scales them alike."""
    w = int(0.1 * SR)
    def peak(x, a, b):
        seg = x[a:b]
        return 10 * np.log10(np.convolve(seg ** 2, np.ones(w) / w, "valid").max() + 1e-12) if len(seg) >= w else -120.0
    fr = _frames_db(voice)
    speech = float(np.median(fr[fr > np.percentile(fr, 90) - 20])) if len(fr) else -20.0
    out = []
    for kind, t in used:
        a, b = int(t * SR), int((t + 0.35) * SR)
        e, v = peak(sfx, a, b), peak(voice, a, b)
        out.append({"kind": kind, "t": float(t), "local_db": round(float(e - v), 1), "overall_db": round(float(e - speech), 1), "speaking": bool(v > speech - 10)})
    return out


def measure(proj, settings: dict, final: Path | None = None) -> dict:
    """Clipping and peak of the final, background noise under the voice, each effect against the voice, and the music against
    the voice while she speaks."""
    A = proj.edit / "audio"
    out = {}
    if final is not None and Path(final).exists():
        out["clipping"] = clipping(final)
        out["true_peak_dbtp"] = media.loudness(final).get("peak")
    voice = A / "voice_clean.wav" if (A / "voice_clean.wav").exists() else A / "voice.wav"
    if voice.exists():
        vx = _pcm(voice)
        v = _frames_db(vx)
        if len(v):
            out["voice_to_noise_db"] = round(float(np.percentile(v, 90) - np.percentile(v, 10)), 1)
        if (A / "sfx.wav").exists() and (A / "sfx_used.json").exists():
            fx = effect_levels(vx, _pcm(A / "sfx.wav"), json.loads((A / "sfx_used.json").read_text()))
            out["effects"] = len(fx)
            out["buried"] = [f for f in fx if f["speaking"] and f["local_db"] < -32]
            out["too_loud"] = [f for f in fx if f["overall_db"] > -12]
    vs, mu = A / "stem_voice_sfx.wav", A / "stem_music.wav"
    if (settings.get("music") or {}).get("enabled") and vs.exists() and mu.exists() and voice.exists():
        v, s, m = _frames_db(_pcm(voice)), _frames_db(_pcm(vs)), _frames_db(_pcm(mu))
        n = min(len(v), len(s), len(m))
        if n:
            speech = v[:n] > np.percentile(v[:n], 90) - 20                         # frames where she is speaking
            if speech.any():
                out["music_under_voice_db"] = round(float(np.median(s[:n][speech] - m[:n][speech])), 1)
    return out


def notes_from(m: dict) -> list[str]:
    """Plain-language notes for the editor (empty: it sounds right)."""
    notes = []
    at = lambda ts: ", ".join(f"{int(t // 60)}:{t % 60:04.1f}" for t in ts[:5])   # noqa: E731
    cl = m.get("clipping") or {}
    if cl.get("runs"):
        notes.append(f"The sound clips (distorts) in {cl['runs']} place(s), e.g. at {at(cl['times'])}.")
    if m.get("true_peak_dbtp") is not None and m["true_peak_dbtp"] > -0.5:
        notes.append(f"The loudest peak is {m['true_peak_dbtp']:.1f} dBTP: too close to the limit; it can distort on some players.")
    if m.get("effects") and len(m.get("buried") or []) / m["effects"] > 0.15:
        notes.append(f"{len(m['buried'])} of {m['effects']} sound effects are buried under her voice (more than 32 dB under it), "
                     f"e.g. at {at([f['t'] for f in m['buried']])}.")
    if m.get("too_loud"):
        notes.append(f"{len(m['too_loud'])} sound effect(s) are too loud (less than 12 dB under her voice), e.g. at {at([f['t'] for f in m['too_loud']])}.")
    if m.get("voice_to_noise_db") is not None and m["voice_to_noise_db"] < 25:
        notes.append(f"Background noise is high: her voice is only {m['voice_to_noise_db']:.0f} dB above it.")
    mu = m.get("music_under_voice_db")
    if mu is not None and mu < 12:
        notes.append(f"The music is too close to her voice ({mu:.0f} dB under it while she speaks); turn it down.")
    if mu is not None and mu > 30:
        notes.append(f"The music is barely audible ({mu:.0f} dB under her voice); turn it up or switch it off.")
    return notes


def listen(proj, final: Path, settings: dict, log=print) -> dict:
    """The `sound` check of verify.json: {ok, notes, measures}."""
    if (settings.get("listen") or {}).get("enabled") is False:
        return {"ok": True, "skipped": "listening check off (setting listen.enabled)"}
    m = measure(proj, settings, final)
    notes = notes_from(m)
    if m.get("effects"):
        m["effects_buried"] = f"{len(m.get('buried') or [])}/{m['effects']}"
    rep = {"ok": not notes, "notes": notes, "measures": m}
    (proj.edit / "out" / "listen.json").write_text(json.dumps(rep, indent=1, default=str))
    log("listen: " + ("sounds right" if not notes else "; ".join(notes)))
    return rep
