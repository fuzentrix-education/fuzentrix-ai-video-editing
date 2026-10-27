import json

import numpy as np
import pytest

from fzv import align, captions, config, layout, revise, spec
from fzv.anchors import Transcript


def write_tx(tmp_path, words):
    f = tmp_path / "t.jsonl"
    f.write_text(json.dumps({"start": 0, "end": 99, "text": " ".join(w for w, _ in words), "words": [{"w": w, "s": s} for w, s in words]}) + "\n")
    return f


# ---------- brand kits ----------
@pytest.mark.parametrize("bid", config.brand_ids())
def test_brand_merges_house_and_makes_css(bid):
    b = config.load_brand(bid)
    assert b["fonts"]["display"]["family"] == "Outfit"            # from the shared house style
    v = config.css_vars(b)
    for k in ("text", "accent", "emph", "highlight", "code-bg1", "grad", "font-mono"):
        assert v[k]
    css = config.brand_css(b)
    assert "@font-face" in css and "--fz-text:" in css


def test_career_orbit_merged_palette():
    v = config.css_vars(config.load_brand("career-orbit"))
    assert v["text"].upper() == "#0D274C" and v["accent"].upper() == "#16BBC8" and v["action"].upper() == "#1B53A2"


# ---------- anchors ----------
def test_anchor_fuzzy_and_occurrence(tmp_path):
    tx = Transcript(write_tx(tmp_path, [("For", 1.0), ("i", 1.4), ("in", 1.6), ("range", 1.9), ("if", 5.0), ("i", 5.2), ("equal", 5.4), ("to", 5.6),
                                       ("if", 9.0), ("i", 9.2), ("equals", 9.4), ("to", 9.6)]))
    assert tx.find("for i in range") == 1.0
    assert tx.find("if i equal to") == 5.0
    assert tx.find("if i equal to", occurrence=2) == 9.0
    assert tx.find("while loop") is None


# ---------- spec ----------
def test_resolve_numbers_anchors_relative(tmp_path):
    tx = Transcript(write_tx(tmp_path, [("hello", 10.0), ("everyone", 10.4), ("break", 20.0), ("statement", 20.3)]))
    sp = {"sections": [{"id": "s1", "range": [9, 30], "scenes": [
        {"header": {"label": "x", "title": "y", "at": "@hello everyone", "until": "+5"}},
        {"code-card": {"lines": ["a"], "at": 12, "type": [{"line": 1, "at": "@break statement"}], "highlights": [{"line": 1, "at": "+1", "until": 25}]}}]}],
          "studio": [{"studio-tag": {"text": "t", "at": 31.0}}]}
    res, errs = spec.resolve(sp, tx, 60)
    assert not errs
    h = res["sections"][0]["scenes"][0]["header"]
    assert h["at"] == 10.0 and h["until"] == 15.0
    c = res["sections"][0]["scenes"][1]["code-card"]
    assert c["type"][0]["at"] == 20.0 and c["highlights"][0]["at"] == 13.0


def test_plan_clips_assigns_studio_scenes_and_bug():
    res = {"sections": [{"id": "s1", "range": [0.0, 10.0], "scenes": [{"header": {"at": 1, "title": "t"}}]}],
           "studio": [{"studio-tag": {"text": "k", "at": 12.1}}]}
    cuts = [{"kind": "corner", "start": 0, "end": 11.98}, {"kind": "studio", "start": 11.98, "end": 15.0}, {"kind": "corner", "start": 15.0, "end": 20}]
    clips = spec.plan_clips(res, cuts, 25, ["plate", "studio"])
    plate = [c for c in clips if c["layer"] == "plate"][0]
    studio = [c for c in clips if c["layer"] == "studio"][0]
    assert plate["scenes"][0]["template"] == "bug"
    assert studio["has_content"] and studio["start"] == 11.96 and studio["end"] == 15.0


def test_snap():
    assert spec.snap(279.1, 25) == 279.12 and spec.snap(18.78, 25, "floor") == 18.76


# ---------- revise ----------
def test_revise_parse():
    items = revise.parse("7:41 make the note larger; 12:05 fix the code; 1:02:03.5 last")
    assert [round(t, 1) for t, _ in items] == [461.0, 725.0, 3723.5]
    assert items[0][1] == "make the note larger"


# ---------- captions ----------
def test_captions_limits(tmp_path):
    words = [(f"word{i}", i * 0.3) for i in range(60)]
    cues = captions.cues(write_tx(tmp_path, words), max_chars=42, max_lines=2)
    assert cues and all(len(c["text"].replace("\n", " ")) <= 84 and c["until"] - c["at"] <= 6.01 for c in cues)


# ---------- layout ----------
def synthetic_frames():
    W, H = layout.W, layout.H
    studio = np.full((H, W, 3), 190, np.uint8); studio[15:45, 40:60] = 30
    plate = np.full((H, W, 3), 248, np.uint8)
    corner = plate.copy(); corner[38:54, 70:92] = 30
    return np.stack([studio] * 20 + [corner] * 40 + [plate] * 5)


def test_layout_classify_and_zones():
    fr = synthetic_frames()
    kinds, boxes, pref, sref, thr, two, occ = layout.classify(fr)
    assert two and kinds[0] == "studio" and kinds[30] == "corner" and kinds[-1] == "empty"
    segs = layout.segments(kinds, 5)
    assert [s[0] for s in segs] == ["studio", "corner", "empty"]
    rects = layout.zone_rects(occ["corner"])
    assert rects and min(r[0] for r in rects) >= 1300 and min(r[1] for r in rects) >= 700


# ---------- recording content area ----------
def test_recording_content_area():
    from PIL import Image
    ui = np.full((270, 480, 3), 240, np.uint8)
    ui[::6] = 60
    ui[:, ::40] = 60
    assert align.crop_from_frame(ui, 1920, 1080) == [0, 0, 1920, 1080]                      # full-screen UI: keep it all
    assert align.crop_from_frame(np.full((270, 480, 3), 200, np.uint8), 1920, 1080) == [0, 0, 1920, 1080]
    bars = np.zeros_like(ui)
    bars[40:230, 60:420] = ui[40:230, 60:420]
    x, y, w, h = align.crop_from_frame(bars, 1920, 1080)                                     # window on a plain desktop
    assert abs(x - 240) <= 6 and abs(y - 160) <= 6 and abs(w - 1440) <= 12 and abs(h - 760) <= 12
    plate = next(config.BRANDS.glob("*/plate/*.png"))
    comp = np.asarray(Image.open(plate).convert("RGB").resize((480, 270)), np.uint8).copy()
    comp[76:234] = 243                                                                       # IDE band composited on the brand plate
    comp[100:104, 20:200] = 40
    x, y, w, h = align.crop_from_frame(comp, 1920, 1080)
    assert x == 0 and w == 1920 and abs(y - 304) <= 8 and abs(h - 632) <= 16


# ---------- exact program output (rule E7) ----------
def test_exec_python_exact_transcript(tmp_path):
    from fzv import execute
    r = execute.run("python", "name = input('Name: ')\nfor i in range(1, 4):\n    print(i)\nprint(1/0)\n", "Durga\n", tmp_path)
    assert r["lines"][0] == {"text": "Name: ", "input": "Durga"}                 # input echoed where it is read
    assert [l["text"] for l in r["lines"][1:4]] == ["1", "2", "3"]
    assert r["exit"] == 1 and r["lines"][-1] == {"err": True, "text": "ZeroDivisionError: division by zero"}
    assert list(tmp_path.glob("*.json"))                                          # cached


def test_exec_apply_fills_and_times_terminal(tmp_path):
    from fzv import execute
    spec = {"sections": [{"id": "s", "scenes": [
        {"code-card": {"id": "c", "lines": ["n = int(input())", "for i in range(1, n+1):", "    print(i)"]}},
        {"terminal": {"id": "t", "at": 10.0, "exec": {"code": "c", "stdin": ["3"], "times": [11.0, 15.0], "pace": 0.5, "tones": {3: "warn"}}}},
        {"terminal": {"id": "bad", "at": 20.0, "exec": {"code": "c"}, "lines": [{"text": "1", "at": 21}]}}]}]}
    errs = execute.apply(spec, tmp_path)
    lines = spec["sections"][0]["scenes"][1]["terminal"]["lines"]
    assert [(l["text"], l.get("input"), l["at"]) for l in lines] == [("", "3", 11.0), ("1", None, 15.0), ("2", None, 15.5), ("3", None, 16.0)]
    assert lines[3]["tone"] == "warn"
    assert len(errs) == 1 and "remove hand-written" in errs[0]


def test_prompt_recording_field(tmp_path):
    from fzv.project import Project
    for line, use in [("Recording: reference only", "reference"), ("Screen recording: don't use it", "reference"), ("Recording: show", "show"), ("", "show")]:
        (tmp_path / "prompt.md").write_text(f"# T\n{line}\n")
        assert Project(tmp_path).settings()["recordings"]["use"] == use


def test_recref_settled_states_ignore_caret():
    from fzv import recref
    base = np.full((60, 200), 240, np.uint8)
    frames = []
    for i in range(24):                                  # 12 s at 2 fps: a line is typed at 4-5 s, another at 8-9 s; the caret blinks throughout
        f = base.copy()
        if i >= 8:
            f[10:20, 10:60] = 30
        if i >= 9:
            f[10:20, 60:110] = 30
        if i >= 16:
            f[30:40, 10:90] = 30
        if i % 2:
            f[10:30, 150:152] = 0
        frames.append(f)
    states = recref.settled_states(np.stack(frames), 2.0)
    assert len(states) == 3 and states[1][0] in (9, 10) and states[2][0] in (16, 17)


# ---------- third-party assets ----------
def test_recolor_and_licences():
    from fzv import assets
    svg, m = assets.recolor('<svg viewBox="0 0 10 10"><path fill="#1E5AA8"/><path fill="#F7F7F7"/><path fill="black"/><path style="fill:#E5A882"/><path fill="#F92F60"/></svg>')
    assert m["#1E5AA8"] == "var(--fz-action)" and m["#F7F7F7"] == "#FFFFFF" and m["#000000"] == "#2B2F3A"
    assert m["#E5A882"] in assets.SKIN and m["#F92F60"] == "var(--fz-danger)"
    assert assets.clean_svg('<?xml version="1.0"?><svg width="32" height="16"><g/></svg>') == '<svg viewBox="0 0 32 16"><g/></svg>'
    assert assets.licence_problem("CC BY-NC 4.0") and assets.licence_problem("free for personal use") and assets.licence_problem("")
    assert not assets.licence_problem("MIT") and not assets.licence_problem("CC0") and not assets.licence_problem("Pixabay Content License")
    assert assets.attribution_warning("CC BY 4.0") and not assets.attribution_warning("CC0 1.0")


def test_corrections_listed_and_output_checked(tmp_path):
    from fzv import execute
    rec = ["n = int(input())", "for i in range(1,n+1):", "    if i == 11:", "        break", "    print(i)"]
    tidy = ["n = int(input())", "for i in range(1, n+1):", "    if i == 11:", "        break", "    print(i)"]
    logic = ["n = int(input())", "for i in range(1, n+1):", "    if i == 5:", "        break", "    print(i)"]
    for lines, same in ((tidy, True), (logic, False)):
        spec = {"sections": [{"id": "s", "scenes": [{"code-card": {"id": "c", "lines": lines, "recorded": rec}},
                                                    {"terminal": {"at": 1.0, "exec": {"code": "c", "stdin": ["20"]}}}]}]}
        assert execute.apply(spec, tmp_path) == []
        cr = spec["sections"][0]["scenes"][0]["code-card"]["corrections_result"]
        assert cr["output_same"] is same and cr["changes"][0].startswith("line 2: `for i in range(1,n+1):` → `for i in range(1, n+1):`")


def test_auto_mode():
    from fzv.layout import auto_mode
    seg = lambda k, a, b: {"kind": k, "start": a, "end": b}
    rough = [seg("plate", 0, 12), seg("corner", 12, 500), seg("studio", 500, 520), seg("corner", 520, 899)]
    assert auto_mode(rough, {"corner": 867, "studio": 20, "plate": 12, "empty": 0}, 899) == "overlay"
    assert auto_mode([seg("plate", 0, 237)], {"corner": 0, "studio": 0, "plate": 237, "empty": 0}, 237) == "compose"   # green screen
    assert auto_mode([seg("studio", 0, 300)], {"corner": 0, "studio": 300, "plate": 0, "empty": 0}, 300) == "compose"  # raw studio take


def test_transcript_repeat_cleanup():
    from fzv.transcribe import collapse_repeats, tidy_text
    assert tidy_text("write colon colon colon colon colon Yes.") == "write colon colon Yes."
    assert tidy_text("1-n-n-n-n-n Thank you.") == "1-n-n Thank you."
    assert tidy_text("I can see the one I can see.") == "I can see the one I can see."
    assert [w["w"] for w in collapse_repeats([{"w": x, "s": i} for i, x in enumerate("a colon colon colon colon b".split())])] == ["a", "colon", "colon", "b"]


def test_clip_hash_tracks_used_templates_and_media(tmp_path):
    import os
    from fzv.build import clip_hash
    A = tmp_path / "assets"
    (A / "runtime" / "templates").mkdir(parents=True)
    (A / "runtime" / "lib.js").write_text("lib")
    (A / "runtime" / "templates" / "code.js").write_text('R({ name: "code-card" })')
    (A / "runtime" / "templates" / "sketch.js").write_text('R({ name: "sketch-board" })')
    (A / "presenter").mkdir()
    (A / "presenter" / "p.webm").write_bytes(b"x" * 10)
    html = tmp_path / "c.html"
    html.write_text('<video src="assets/presenter/p.webm"></video>')
    clip = {"scenes": [{"template": "code-card", "params": {}}]}
    h0 = clip_hash(html, A, clip)
    (A / "runtime" / "templates" / "sketch.js").write_text('R({ name: "sketch-board" }) // changed')
    assert clip_hash(html, A, clip) == h0                      # an unused template changed: still cached
    (A / "runtime" / "templates" / "code.js").write_text('R({ name: "code-card" }) // changed')
    h1 = clip_hash(html, A, clip)
    assert h1 != h0                                            # a used template changed
    (A / "presenter" / "p.webm").write_bytes(b"y" * 12)          # re-keyed presenter
    assert clip_hash(html, A, clip) != h1


def test_mix_with_music(tmp_path):
    import subprocess
    from fzv import audio
    from fzv.project import Project
    proj = Project(tmp_path)
    (proj.edit / "audio").mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=6", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le",
                    str(proj.edit / "audio" / "voice.wav")], check=True)
    settings = proj.settings()
    settings["music"].update(enabled=True, track="calm-piano", level_db=-28)
    out = audio.mix(proj, tmp_path / "none.mp4", 6.0, settings, log=lambda *_: None)
    assert out.exists() and out.stat().st_size > 100_000


# ---------- SFX (rule A5) ----------
def test_thin_cues_spacing_and_cap():
    from fzv.audio import thin_cues
    cues = [["pop", 1.0], ["pop", 1.5], ["ding", 2.0], ["whoosh", 5.0], ["whoosh", 9.0], ["swish", 20.0]] + [["click", 100 + i] for i in range(12)]
    strict = {"minor_gap_s": 3.0, "whoosh_gap_s": 12.0, "max_per_min": 8}
    kept = [tuple(k) for k in thin_cues(cues, strict)]
    kinds = [k for k, _ in kept]
    assert ("pop", 1.0) not in kept and ("ding", 2.0) in kept             # minor pop too close to the ding
    assert kinds.count("whoosh") == 1                                      # whooshes 12 s apart
    assert max(sum(1 for _, t in kept if t0 <= t < t0 + 60) for _, t0 in kept) <= 8
    assert len(thin_cues(cues, {})) >= len(cues) - 2                       # defaults keep nearly every cue (only stacked duplicates go)
    assert thin_cues(cues, {"enabled": False}) == []
    assert all(k not in ("pop", "swish") for k, _ in thin_cues(cues, {"minor": False}))


def test_synth_sfx_varies_repeated_cues(tmp_path):
    import wave
    from fzv import audio
    out = audio.synth_sfx([["pop", 0.5], ["pop", 1.5]], 2.5, tmp_path / "s.wav", cfg={"fallback": "synth"})
    with wave.open(str(out)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2)[:, 0].astype(float)
    a, b = x[int(0.5 * 48000):int(0.6 * 48000)], x[int(1.5 * 48000):int(1.6 * 48000)]
    assert np.abs(a).max() > 0 and not np.allclose(a, b)                   # two pops, two different takes


def test_sfx_library_used_first(tmp_path, monkeypatch):
    import subprocess
    from fzv import audio
    g = tmp_path / "global"
    (g / "sfx" / "ding").mkdir(parents=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=440:d=0.3", str(g / "sfx" / "ding" / "d1.wav")], check=True)
    (g / "sfx" / "manifest.yaml").write_text("sounds:\n- {id: ding-d1, category: ding, file: ding/d1.wav, gain_db: 0}\n")
    monkeypatch.setattr(audio, "GLOBAL", g)
    assert list(audio.sfx_library()) == ["ding"]
    out = audio.synth_sfx([["ding", 0.5], ["pop", 2.0]], 4.0, tmp_path / "s.wav", cfg={"fallback": "none"})
    import wave
    with wave.open(str(out)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2)[:, 0]
    assert np.abs(x[int(0.5 * 48000):int(0.8 * 48000)]).max() > 20           # library ding plays
    assert np.abs(x[int(2.0 * 48000):int(2.5 * 48000)]).max() == 0          # no pop: not in the library, fallback none


def test_prompt_music_sfx_presenter_fields(tmp_path):
    from fzv.project import Project
    (tmp_path / "prompt.md").write_text("# T\nMusic: calm-piano, low\nSFX: minimal\nPresenter box: off\n")
    s = Project(tmp_path).settings()
    assert s["music"]["enabled"] and s["music"]["rel_lufs"] == -22 and s["sfx"]["minor"] is False and s["presenter"]["corner_box"] is False


# ---------- beat sheet, approvals, review gates (design §9f) ----------
def seg_tx(tmp_path, segs):
    """Transcript with one segment per (start, words…); words 0.4 s apart."""
    f = tmp_path / "transcript.jsonl"
    rows = []
    for start, text in segs:
        ws = text.split()
        rows.append(json.dumps({"start": start, "end": start + 0.4 * len(ws), "text": text, "words": [{"w": w, "s": round(start + 0.4 * i, 2)} for i, w in enumerate(ws)]}))
    f.write_text("\n".join(rows) + "\n")
    return f


def test_beats_draft_contiguous_shots_and_no_tiny_beats(tmp_path):
    from fzv import beats as B
    segs = [(t, "we talk about loops and how they repeat work") for t in range(0, 60, 5)] + [(60.5, "So,")] + [(63, "the studio part starts here now")]
    tx = seg_tx(tmp_path, segs)
    cuts = [{"kind": "corner", "start": 0, "end": 62.0}, {"kind": "studio", "start": 62.0, "end": 70.0}]
    moments = [{"t": 30.0, "phrase": "database", "templates": ["data-flow"], "show": ""}]
    rows = B.draft(tx, cuts, 70.0, moments)
    assert rows[0]["start"] == 0 and rows[-1]["end"] == 70.0
    assert all(abs(a["end"] - b["start"]) < 1e-6 for a, b in zip(rows, rows[1:]))
    assert all(r["end"] - r["start"] >= 4 for r in rows)                      # "So," joined a neighbour
    assert any(r["start"] == 62.0 for r in rows) and rows[-1]["shot"] == "studio"   # the studio shot starts its own beat
    assert any(r["start"] <= 30 < r["end"] and r["concepts"] for r in rows)
    assert all(r["end"] - r["start"] <= 25 for r in rows)


def test_beats_check_states_and_gates(tmp_path):
    import yaml
    from fzv import beats as B
    from fzv.project import Project
    tx_f = seg_tx(tmp_path, [(0, "data goes into the database here"), (10, "and the records are stored safely now")])
    proj = Project(tmp_path)
    proj.save({"raw": "r.mp4", "duration": 20.0})
    (proj.edit / "transcript.jsonl").write_text(tx_f.read_text())
    doc = {"beats": [{"id": "b01", "start": 0, "end": 10, "idea": "", "show": "", "templates": [], "sync": []},
                     {"id": "b02", "start": 10, "end": 20, "idea": "stored", "show": "rows land", "templates": ["data-flow", "nope"], "sync": ["@zebra"]}]}
    B.write(proj.p("beats.yaml"), doc)
    tx = Transcript(proj.p("transcript.jsonl"))
    errs, _, _ = B.check(doc, tx, 20.0, {"data-flow", "card"}, set(), [], set())
    assert any("fill" in e for e in errs) and any("'nope'" in e for e in errs) and any("zebra" in e for e in errs)
    assert B.beats_state(proj) == "draft" and B.gate_build(proj, proj.settings())
    doc["beats"][0].update(idea="data is stored", show="chips fly into a database", templates=["data-flow"], sync=["@database"])
    doc["beats"][1].update(templates=["data-flow"], sync=["@records"])
    B.write(proj.p("beats.yaml"), doc)
    errs, warns, res = B.check(doc, tx, 20.0, {"data-flow", "card"}, set(), [], set())
    assert not errs and res["b01"]["sync"] == [1.6] and 0.5 <= res["b01"]["key"] <= 9.7
    assert B.beats_state(proj) == "proposed"
    B.record_approval(proj, "beats", B.beats_fingerprint(B.load(proj.p("beats.yaml"))), "looks good")
    assert B.beats_state(proj) == "approved" and B.gate_build(proj, proj.settings()) is None
    assert "looks good" in proj.p("approvals.md").read_text()
    doc["beats"][1]["show"] = "rows land one by one"
    B.write(proj.p("beats.yaml"), doc)
    assert B.beats_state(proj) == "changed" and "changed" in B.gate_build(proj, proj.settings())
    assert B.gate_render(proj, proj.settings())                                # no storyboard yet
    (tmp_path / "prompt.md").write_text("# T\nReview: off\n")
    assert B.gate_build(proj, proj.settings()) is None and B.gate_render(proj, proj.settings()) is None


def test_legacy_edit_without_beats_skips_gates(tmp_path):
    from fzv import beats as B
    from fzv.project import Project
    proj = Project(tmp_path)
    assert B.gate_build(proj, proj.settings())                                # a new edit needs its beat sheet
    (proj.edit / "built" / "clips.json").write_text("[]")
    assert B.legacy(proj) and B.gate_build(proj, proj.settings()) is None and B.gate_render(proj, proj.settings()) is None


def test_beat_refs_become_times():
    from fzv import beats as B
    doc = {"beats": [{"id": "b01", "start": 0, "end": 10}, {"id": "b02", "start": 83.0, "end": 98}]}
    out = B.expand_refs("beat 2: use a car; b01 bigger text; 7:41 slower", doc)
    assert [round(t, 1) for t, _ in revise.parse(out)] == [83.5, 0.5, 461.0]
    assert revise.parse(out)[0][1] == "use a car"


def test_prompt_review_field(tmp_path):
    from fzv.project import Project
    assert Project(tmp_path).settings()["review"] == {"beats": "required", "storyboard": "required"}
    (tmp_path / "prompt.md").write_text("# T\nReview: beats only\n")
    assert Project(tmp_path).settings()["review"] == {"beats": "required", "storyboard": "off"}


def test_v4_scene_in():
    from fzv.validate import scene_in
    sp = {"sections": [{"range": [0, 30], "scenes": [{"data-flow": {"at": 5.0, "until": 12.0}}, {"hf": {"item": "count-up", "at": 20.0}}]}],
          "studio": [{"studio-tag": {"at": 40.0, "until": 44.0}}]}
    assert scene_in(sp, "data-flow", 10, 20) and not scene_in(sp, "data-flow", 14, 20)
    assert scene_in(sp, "hf:count-up", 25, 29) and not scene_in(sp, "hf:chart-story", 0, 30)
    assert scene_in(sp, "studio-tag", 41, 43)
