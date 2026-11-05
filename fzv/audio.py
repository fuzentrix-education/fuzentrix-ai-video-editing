"""Audio (design §8.4, §9b): the voice cleaned (rumble filter, speech denoiser, EQ, gentle levelling, de-esser), SFX from the
recorded cues 18-26 dB under the voice and dipping while she speaks, optional music ducked under the voice, two-pass loudnorm.
The voice itself is never ducked, cut or lowered."""
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
    # the editors' sound names (2026-11-04); synthesised only if their files are missing
    "decision": (lambda: pop(1200, 700, 0.06), -26, 0.0), "ticks": (tick, -33, 0.0), "stop": (lambda: blip(600, 0.12), -26, 0.0),
    "page": (lambda: whoosh(0.45, 900, 4200), -27, 0.0), "boing": (lambda: pop(300, 900, 0.3), -26, 0.0),
}


# kind -> dB under the voice's loudness, measured on the sound's loudest 100 ms (master prompt: 18-26 dB under the narration)
UNDER = {"ding": 18, "good": 18, "bad": 19, "chime": 18, "impact": 18, "thud": 19, "click": 21, "whoosh": 22, "swish": 23,
         "pop": 23, "blip": 24, "tick": 25, "type": 26, "decision": 21, "ticks": 25, "stop": 20, "page": 22, "boing": 20}
SPEECH_DIP = 0.7                     # SFX x0.7 (-3 dB) while she speaks, +-0.05 s, so an effect never masks a word

IMPORTANT = {"ding", "good", "bad", "click", "impact", "chime", "thud", "type"}   # results, presses, typing: always kept
TRANSITION = {"whoosh", "page"}                                                       # chapter changes and new topics: spaced out
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
        if kind == "type" and any(k[0] == "type" and t - k[1] < 2.5 for k in kept):     # one key press per typing burst, not per chunk
            continue
        if any(k[0] == kind and abs(t - k[1]) < 0.25 for k in kept):
            continue
        kept.append((kind, t))
    # over the cap, drop in this order: typing, small blips and ticks, then pops (the editors' main sound), then transitions; results never
    rank = lambda k: 0 if k[0] == "type" else 1 if k[0] in MINOR - {"pop"} else 2 if k[0] == "pop" else 3 if k[0] in TRANSITION else 4
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


def _norm(x: np.ndarray) -> np.ndarray:
    """Scale so the loudest 100 ms sits at -20 dBFS RMS: every sound, short click or long whoosh, then lands at its UNDER level."""
    w = int(0.1 * SR)
    if len(x) == 0:
        return x
    e = np.convolve(x ** 2, np.ones(min(w, len(x))) / min(w, len(x)), "valid") if len(x) >= 2 else x ** 2
    return x * (0.1 / max(np.sqrt(e.max()), 1e-6))


def _load_sound(path: Path) -> np.ndarray:
    """Decode to mono float at SR, normalised on its loudest 100 ms (-20 dBFS RMS)."""
    k = str(path)
    if k not in _decoded:
        b = subprocess.run(["ffmpeg", "-v", "error", "-i", k, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
        _decoded[k] = _norm(np.frombuffer(b, np.float32).astype(np.float64))
    return _decoded[k]


def speech_gain(voice: Path, duration: float, lufs: float) -> np.ndarray:
    """Per-sample gain for the SFX bus: SPEECH_DIP where she speaks (frames within 20 dB of her loudness, +-0.05 s), 1 elsewhere,
    with 30 ms ramps."""
    b = subprocess.run(["ffmpeg", "-v", "error", "-i", str(voice), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(b, np.float32).astype(np.float64)
    n, hop = int(duration * SR) + SR, int(0.02 * SR)
    frames = len(x) // hop
    rms = np.sqrt(np.mean(x[: frames * hop].reshape(frames, hop) ** 2, 1)) if frames else np.zeros(0)
    on = 20 * np.log10(np.maximum(rms, 1e-9)) > lufs - 20
    pad = 3                                                    # +-0.06 s around speech
    on = np.convolve(on.astype(float), np.ones(2 * pad + 1), "same") > 0
    g = np.ones(n)
    idx = np.repeat(on, hop)[:n]
    g[: len(idx)] = np.where(idx, SPEECH_DIP, 1.0)
    r = int(0.03 * SR)
    return np.convolve(np.pad(g, (r, r), mode="edge"), np.ones(2 * r + 1) / (2 * r + 1), "valid")[:n]


def synth_sfx(cues: list, duration: float, out: Path, voice_lufs: float = -14.0, min_gap: float = 0.06, cfg: dict | None = None,
              dip: np.ndarray | None = None) -> Path:
    """Each cue at its UNDER level below the voice (plus `level_db` from the settings), dipping under speech (`dip`)."""
    cfg = cfg or {}
    cues = thin_cues(cues, cfg)
    lib = sfx_library()
    fallback = cfg.get("fallback", "synth")
    offset_db = voice_lufs + 20 + cfg.get("level_db", 0.0)         # sound normalised to -20 dBFS -> voice level, then UNDER below it
    L = np.zeros(int(duration * SR) + SR); Rch = np.zeros_like(L)
    last, rotation, used = {}, {}, []
    for kind, t in sorted(cues, key=lambda c: c[1]):
        if kind not in KINDS or t < 0 or t >= duration:
            continue
        if t - last.get(kind, -9) < min_gap:                 # never stack identical cues
            continue
        last[kind] = t
        gen, _, pan = KINDS[kind]
        db = -UNDER.get(kind, 22)
        extra = cfg.get("minor_db", 0.0) if kind in MINOR else 0.0
        rng = np.random.default_rng(abs(hash((kind, int(round(t * 100))))) % (2 ** 32))
        if lib.get(kind):                                    # the team's library first
            files = lib[kind]
            k = rotation.get(kind, -1) + 1
            rotation[kind] = k
            prim = [f for f in files if f.get("role") == "primary"]
            if prim:                                         # the editors' house sound; its alt partner every third cue, for variety
                alts = [f for f in files if f.get("role") == "alt"]
                s = alts[(k // 3) % len(alts)] if alts and k % 3 == 2 else prim[k % len(prim)]
            else:                                            # no house sound: files rotate, never the same one twice in a row
                s = files[k % len(files)]
            x = _load_sound(GLOBAL / "sfx" / s["file"]) * 10 ** ((db + offset_db + extra + s.get("gain_db", 0.0)) / 20)
        elif fallback == "synth":                            # synthesised: every cue a slightly different take (pitch, level)
            base = _norm(gen())
            f = rng.uniform(0.88, 1.12)
            x = np.interp(np.arange(0, len(base) - 1, f), np.arange(len(base)), base) * 10 ** ((db + offset_db + extra + rng.uniform(-1.5, 1.5)) / 20)
        else:
            continue
        used.append((kind, round(t, 3)))
        s = int(t * SR); e = min(len(L), s + len(x)); x = x[: e - s]
        L[s:e] += x * np.sqrt((1 - pan) / 2) * 1.414; Rch[s:e] += x * np.sqrt((1 + pan) / 2) * 1.414
    out.with_name("sfx_used.json").write_text(json.dumps(used))   # the effects really placed: the listening check listens for these
    if dip is not None:                                      # effects dip while she speaks; the voice is never touched
        L[: len(dip)] *= dip[: len(L)]; Rch[: len(dip)] *= dip[: len(Rch)]
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


VOICE_CHAIN = ("highpass=f=80,arnndn=m={model}:mix=0.9,equalizer=f=250:t=q:w=1:g=-1.5,equalizer=f=3200:t=q:w=1:g=2,"
               "acompressor=threshold=-20dB:ratio=2:attack=10:release=150,deesser=i=0.3")
# rumble and desk thumps out; RNNoise speech denoiser keeping 10% of the dry signal so her tone stays natural; less boxiness; a
# little presence; gentle levelling for a steady volume; softer "s" sounds. Model: global/audio/sh.rnnn (rnnoise-models, speech
# in recording noise; not subject to copyright).


def clean_voice(voice: Path, out: Path, cfg: dict, log=print) -> Path:
    """The cleaned voice (cached by the chain), or the original with only a 70 Hz high-pass when `voice.cleanup` is off."""
    chain = VOICE_CHAIN.format(model=str(GLOBAL / "audio" / "sh.rnnn")) if cfg.get("cleanup", True) else "highpass=f=70"
    key = out.with_suffix(".key")
    if out.exists() and key.exists() and key.read_text() == chain and out.stat().st_mtime >= voice.stat().st_mtime:
        return out
    media.run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-af", chain, "-c:a", "pcm_s24le", out])
    key.write_text(chain)
    log("audio: voice cleaned (denoise, EQ, levelling, de-ess)" if cfg.get("cleanup", True) else "audio: voice untouched (70 Hz high-pass only)")
    return out


def mix(proj, raw: Path, duration: float, settings: dict, log=print) -> Path:
    """cleaned voice + SFX (dipping under speech) (+ ducked music) -> two-pass loudnorm -> edit/audio/mix.wav"""
    A = proj.edit / "audio"
    raw_voice = A / "voice.wav"
    if not raw_voice.exists():
        media.extract_audio(raw, raw_voice, SR, mono=False, codec="pcm_s24le")
    voice = clean_voice(raw_voice, A / "voice_clean.wav", settings.get("voice") or {}, log)
    lvl = media.loudness(voice).get("lufs", -22.0)
    cues = json.loads((A / "cues.json").read_text()) if (A / "cues.json").exists() else []
    dip = speech_gain(voice, duration, lvl)
    sfx = synth_sfx(cues, duration, A / "sfx.wav", voice_lufs=lvl, cfg=settings.get("sfx") or {}, dip=dip)
    music = music_track(settings)
    inputs = ["-i", voice, "-i", sfx]
    fmt = "aformat=sample_rates=48000:channel_layouts=stereo"
    # the voice feeds both the mix and (with music) the ducking sidechain; a filter label can be used once, so split it
    fc = f"[0:a]apad=whole_dur={duration},{fmt}" + (",asplit=3[v][vk][vn];[1:a]asplit=2[s][sn];" if music else "[v];")
    if music:
        m = settings["music"]
        inputs += ["-stream_loop", "-1", "-i", music]
        mlufs = music_loudness(music)
        gain = (lvl + m.get("rel_lufs", -18)) - mlufs          # the bed sits rel_lufs below the voice, whatever the track's own level
        fc += (f"[2:a]{fmt},atrim=0:{duration},volume={gain:.1f}dB,afade=t=in:d={m.get('fade_s', 2)},afade=t=out:st={max(0, duration - m.get('fade_s', 2))}:d={m.get('fade_s', 2)}[mu];"
               f"[mu][vk]sidechaincompress=threshold=0.06:ratio=3:attack=40:release=700:makeup=1,asplit=2[duck][dm];"
               f"[v][s][duck]amix=inputs=3:normalize=0:duration=first[m];"
               f"[vn][sn]amix=inputs=2:normalize=0:duration=first[nm]")
    else:
        fc += "[v][1:a]amix=inputs=2:normalize=0:duration=first[m]"
    raw_mix = A / "raw_mix.wav"
    stems = [(A / "stem_voice_sfx.raw.wav", "[nm]"), (A / "stem_music.raw.wav", "[dm]")] if music else []
    media.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[m]", "-t", f"{duration:.3f}", "-c:a", "pcm_s24le", raw_mix,
               *[x for f, lab in stems for x in ("-map", lab, "-t", f"{duration:.3f}", "-c:a", "pcm_s24le", f)]])
    p = media.run(["ffmpeg", "-hide_banner", "-i", raw_mix, "-af", "loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json", "-f", "null", "-"], check=False)
    txt = (p.stderr or b"").decode(errors="replace")
    j = json.loads(txt[txt.rindex("{"):txt.rindex("}") + 1])
    out = A / "mix.wav"
    media.run(["ffmpeg", "-v", "error", "-y", "-i", raw_mix, "-af",
               f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,aresample={SR}",
               "-c:a", "pcm_s16le", out])
    # stems at the final mix's gain (loudnorm runs in linear mode: one constant gain), so voice+SFX + music == the mix; the review page
    # plays the video without music from them, and the Studio preview carries them as two tracks
    for old in A.glob("stem_*.wav"):
        if not old.name.endswith(".raw.wav"):
            old.unlink()
    if stems:
        gain = media.loudness(out).get("lufs", -14.0) - media.loudness(raw_mix).get("lufs", -14.0)
        for f, _ in stems:
            media.run(["ffmpeg", "-v", "error", "-y", "-i", f, "-af", f"volume={gain:.2f}dB,aresample={SR}", "-c:a", "pcm_s16le", f.with_name(f.name.replace(".raw", ""))])
            f.unlink()
    log(f"audio: voice {lvl:.1f} LUFS, {len(cues)} SFX cues{', music ' + music.name if music else ''} -> {media.loudness(out)}")
    return out


def export_stems(proj, dest: Path) -> dict:
    """AAC copies of the stems next to the review page: {"voice_sfx": name, "music": name} (empty without music)."""
    A, out = proj.edit / "audio", {}
    for key in ("voice_sfx", "music"):
        src = A / f"stem_{key}.wav"
        f = dest / f"{key}.m4a"
        if src.exists():
            if not f.exists() or f.stat().st_mtime < src.stat().st_mtime:
                media.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-c:a", "aac", "-b:a", "128k", f])
            out[key] = f.name
        elif f.exists():
            f.unlink()
    return out
