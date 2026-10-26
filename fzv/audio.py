"""Audio (design §8.4, §9b): synthesised SFX from the recorded cues, optional music ducked under the voice, two-pass loudnorm."""
from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path

import numpy as np

from . import media
from .config import GLOBAL, load_yaml

SR = 48000
_rng = np.random.default_rng(11)


def _t(d): return np.arange(int(d * SR)) / SR


def _bandnoise(d, f0, f1, q=0.6):
    n = int(d * SR); x = _rng.standard_normal(n); out = np.zeros(n); blk = 1024; win = np.hanning(blk * 2)
    fr = np.fft.rfftfreq(blk * 2, 1 / SR)
    for s in range(0, n, blk):
        seg = x[s:s + blk * 2]
        seg = np.pad(seg, (0, blk * 2 - len(seg))) if len(seg) < blk * 2 else seg
        fc = f0 * (f1 / f0) ** min(1.0, s / max(1, n))
        y = np.fft.irfft(np.fft.rfft(seg * win) * np.exp(-0.5 * (np.log(np.maximum(fr, 1) / fc) / q) ** 2))
        e = min(n, s + blk * 2); out[s:e] += y[: e - s]
    return out / (np.max(np.abs(out)) + 1e-9)


def _env_shape(n, peak=0.55):
    pk = int(n * peak)
    return np.concatenate([np.linspace(0, 1, pk) ** 2, np.linspace(1, 0, n - pk) ** 1.6])


def whoosh(d=0.6, f0=300, f1=2600): x = _bandnoise(d, f0, f1, 0.55); return x * _env_shape(len(x))
def pop(f0=880, f1=520, d=0.09): t = _t(d); return np.sin(2 * np.pi * np.cumsum(f0 * (f1 / f0) ** (t / d)) / SR) * np.exp(-t * 38)
def blip(f=1500, d=0.07): t = _t(d); return np.sin(2 * np.pi * f * t) * np.exp(-t * 55)
def tick(d=0.012): t = _t(d); return (_rng.standard_normal(len(t)) * 0.6 + np.sin(2 * np.pi * 3200 * t)) * np.exp(-t * 420)
def click(): t = _t(0.03); return (np.sin(2 * np.pi * 1900 * t) * 0.7 + _rng.standard_normal(len(t)) * 0.4) * np.exp(-t * 260)


def ding(f=1320, d=0.7):
    t = _t(d)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.01 * t) + 0.15 * np.sin(2 * np.pi * f * 3.02 * t)
    e = np.ones(len(t)); e[:144] = np.linspace(0, 1, 144); e[-2400:] = np.minimum(e[-2400:], np.linspace(1, 0, 2400))
    return x * np.exp(-t * 7) * e


def thud(d=0.35):
    t = _t(d); f = 140 * (55 / 140) ** (t / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11) + _bandnoise(d, 900, 300, 0.8) * np.exp(-t * 30) * 0.5


def impact(d=1.2):
    t = _t(d); f = 95 * (38 / 95) ** (t / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6) + _bandnoise(d, 2400, 200, 0.9) * np.exp(-t * 4.5) * 0.55


def chime():
    out = np.zeros(int(2.2 * SR))
    for i, f in enumerate([1046.5, 1318.5, 1568.0, 2093.0]):
        x = ding(f, 1.6); s = int(i * 0.09 * SR); out[s:s + len(x)] += x * (0.9 - i * 0.12)
    return out


# kind -> (generator, level dB relative to a -22 LUFS voice, pan)
KINDS = {
    "whoosh": (lambda: whoosh(0.6), -25, -0.2), "swish": (lambda: whoosh(0.35, 600, 3200), -29, 0.25), "pop": (pop, -27, 0.0),
    "blip": (blip, -29, 0.0), "tick": (tick, -33, 0.0), "click": (click, -26, 0.0), "ding": (ding, -27, 0.0),
    "good": (lambda: ding(1568), -28, 0.1), "bad": (lambda: pop(520, 300, 0.12), -26, 0.0), "thud": (thud, -21, 0.0),
    "impact": (impact, -25, 0.0), "chime": (chime, -23, 0.0), "type": (lambda: tick(0.008), -38, 0.0),
}


IMPORTANT = {"ding", "good", "bad", "click", "impact", "chime", "thud", "type"}   # results, presses, typing: always kept
TRANSITION = {"whoosh"}                                                               # scene changes: spaced out
MINOR = {"pop", "swish", "blip", "tick"}                                              # element entrances: only when the moment is quiet


def thin_cues(cues: list, cfg: dict) -> list:
    """Fewer, better SFX (rule A5): minor cues only with room around them, whooshes spaced, a cap per minute."""
    if cfg.get("enabled") is False:
        return []
    minor_gap, whoosh_gap, per_min = cfg.get("minor_gap_s", 0.35), cfg.get("whoosh_gap_s", 1.5), cfg.get("max_per_min", 0)
    minor_ok = cfg.get("minor", True)
    kept = []
    for kind, t in sorted(cues, key=lambda c: c[1]):
        if kind in MINOR and (not minor_ok or any(abs(t - k[1]) < minor_gap for k in kept)
                              or any(c[0] not in MINOR and 0 < c[1] - t < minor_gap for c in cues)):   # an important sound is coming
            continue
        if kind in TRANSITION and any(k[0] in TRANSITION and t - k[1] < whoosh_gap for k in kept):
            continue
        if kind == "type" and any(k[0] == "type" and t - k[1] < 1.0 for k in kept):
            continue
        if any(k[0] == kind and abs(t - k[1]) < 0.25 for k in kept):
            continue
        kept.append((kind, t))
    rank = lambda k: 0 if k[0] in MINOR else 1 if k[0] in TRANSITION else 2
    changed = bool(per_min)
    while changed:                                       # optional cap: at most per_min cues in any 60 s window, dropping minor ones first
        changed = False
        for i, (_, t0) in enumerate(kept):
            win = [k for k in kept if t0 <= k[1] < t0 + 60]
            if len(win) > per_min:
                kept.remove(min(win, key=lambda k: (rank(k), -k[1])))
                changed = True
                break
    return kept


def sfx_library() -> dict[str, list[dict]]:
    """category -> sounds from global/sfx/manifest.yaml (the team's SFX library)."""
    f = GLOBAL / "sfx" / "manifest.yaml"
    lib = {}
    for s in (load_yaml(f).get("sounds") or []) if f.exists() else []:
        if (GLOBAL / "sfx" / s["file"]).exists():
            lib.setdefault(s["category"], []).append(s)
    return lib


_decoded: dict[str, np.ndarray] = {}


def _load_sound(path: Path) -> np.ndarray:
    """Decode to mono float at SR, RMS-normalised to -20 dBFS so library files sit at the category's level."""
    k = str(path)
    if k not in _decoded:
        b = subprocess.run(["ffmpeg", "-v", "error", "-i", k, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
        x = np.frombuffer(b, np.float32).astype(np.float64)
        rms = np.sqrt(np.mean(x ** 2)) if len(x) else 1.0
        _decoded[k] = x * (0.1 / max(rms, 1e-6))
    return _decoded[k]


def synth_sfx(cues: list, duration: float, out: Path, offset_db: float = -8.0, min_gap: float = 0.06, cfg: dict | None = None) -> Path:
    cfg = cfg or {}
    cues = thin_cues(cues, cfg)
    lib = sfx_library()
    fallback = cfg.get("fallback", "synth")
    offset_db += cfg.get("level_db", 0.0)
    L = np.zeros(int(duration * SR) + SR); Rch = np.zeros_like(L)
    last, rotation = {}, {}
    for kind, t in sorted(cues, key=lambda c: c[1]):
        if kind not in KINDS or t < 0 or t >= duration:
            continue
        if t - last.get(kind, -9) < min_gap:                 # never stack identical cues
            continue
        last[kind] = t
        gen, db, pan = KINDS[kind]
        extra = cfg.get("minor_db", -4.0) if kind in MINOR else 0.0
        rng = np.random.default_rng(abs(hash((kind, int(round(t * 100))))) % (2 ** 32))
        if lib.get(kind):                                    # the team's library first: files rotate, never the same one twice in a row
            files = lib[kind]
            k = rotation.get(kind, -1) + 1
            rotation[kind] = k
            s = files[k % len(files)]
            x = _load_sound(GLOBAL / "sfx" / s["file"]) * 10 ** ((db + offset_db + extra + s.get("gain_db", 0.0)) / 20)
        elif fallback == "synth":                            # synthesised: every cue a slightly different take (pitch, level)
            base = gen()
            f = rng.uniform(0.88, 1.12)
            x = np.interp(np.arange(0, len(base) - 1, f), np.arange(len(base)), base) * 10 ** ((db + offset_db + extra + rng.uniform(-1.5, 1.5)) / 20)
        else:
            continue
        s = int(t * SR); e = min(len(L), s + len(x)); x = x[: e - s]
        L[s:e] += x * np.sqrt((1 - pan) / 2) * 1.414; Rch[s:e] += x * np.sqrt((1 + pan) / 2) * 1.414
    mix = np.stack([L, Rch], 1)[: int(duration * SR)]
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    return out


def music_track(settings: dict) -> Path | None:
    m = settings.get("music", {})
    if not m.get("enabled"):
        return None
    man = load_yaml(GLOBAL / "music" / "manifest.yaml").get("tracks", []) if (GLOBAL / "music" / "manifest.yaml").exists() else []
    want = (m.get("track") or "").lower()
    for t in man:
        if want in (str(t.get("id", "")).lower(), str(t.get("mood", "")).lower()) or (not want and t):
            f = GLOBAL / "music" / t["file"]
            if f.exists():
                return f
    raise SystemExit(f"music '{want}' requested but not found in global/music/manifest.yaml (add licensed tracks there)")


def music_loudness(track: Path) -> float:
    """Integrated loudness of a music track (cached next to it)."""
    c = track.with_suffix(track.suffix + ".lufs")
    if c.exists() and c.stat().st_mtime >= track.stat().st_mtime:
        return float(c.read_text())
    v = media.loudness(track).get("lufs", -18.0)
    c.write_text(str(v))
    return v


def mix(proj, raw: Path, duration: float, settings: dict, log=print) -> Path:
    """voice (70 Hz high-pass) + SFX (+ ducked music) -> two-pass loudnorm -> edit/audio/mix.wav"""
    A = proj.edit / "audio"
    voice = A / "voice.wav"
    if not voice.exists():
        media.extract_audio(raw, voice, SR, mono=False, codec="pcm_s24le")
    lvl = media.loudness(voice).get("lufs", -22.0)
    cues = json.loads((A / "cues.json").read_text()) if (A / "cues.json").exists() else []
    sfx = synth_sfx(cues, duration, A / "sfx.wav", offset_db=-8.0 + (lvl + 22.0), cfg=settings.get("sfx") or {})
    music = music_track(settings)
    inputs = ["-i", voice, "-i", sfx]
    fmt = "aformat=sample_rates=48000:channel_layouts=stereo"
    # the voice feeds both the mix and (with music) the ducking sidechain; a filter label can be used once, so split it
    fc = f"[0:a]highpass=f=70,apad=whole_dur={duration},{fmt}" + (",asplit=2[v][vk];" if music else "[v];")
    if music:
        m = settings["music"]
        inputs += ["-stream_loop", "-1", "-i", music]
        mlufs = music_loudness(music)
        gain = (lvl + m.get("rel_lufs", -18)) - mlufs          # the bed sits rel_lufs below the voice, whatever the track's own level
        fc += (f"[2:a]{fmt},atrim=0:{duration},volume={gain:.1f}dB,afade=t=in:d={m.get('fade_s', 2)},afade=t=out:st={max(0, duration - m.get('fade_s', 2))}:d={m.get('fade_s', 2)}[mu];"
               f"[mu][vk]sidechaincompress=threshold=0.06:ratio=3:attack=40:release=700:makeup=1[duck];"
               f"[v][1:a][duck]amix=inputs=3:normalize=0:duration=first[m]")
    else:
        fc += "[v][1:a]amix=inputs=2:normalize=0:duration=first[m]"
    raw_mix = A / "raw_mix.wav"
    media.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[m]", "-t", f"{duration:.3f}", "-c:a", "pcm_s24le", raw_mix])
    p = media.run(["ffmpeg", "-hide_banner", "-i", raw_mix, "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"], check=False)
    txt = (p.stderr or b"").decode(errors="replace")
    j = json.loads(txt[txt.rindex("{"):txt.rindex("}") + 1])
    out = A / "mix.wav"
    media.run(["ffmpeg", "-v", "error", "-y", "-i", raw_mix, "-af",
               f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,aresample={SR}",
               "-c:a", "pcm_s16le", out])
    log(f"audio: voice {lvl:.1f} LUFS, {len(cues)} SFX cues{', music ' + music.name if music else ''} -> {media.loudness(out)}")
    return out
