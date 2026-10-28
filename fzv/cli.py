"""fzv command line. Every command takes a video folder (raw cuts + optional prompt.md); working files go to <folder>/edit/.

  fzv doctor                              machine check: workers, transcription backend, encoder
  fzv ingest   <folder>                   identify files, audio, shots + safe zones, recordings, transcript
  fzv plan     <folder> [--check]         write edit/plan_brief.md for Claude and draft edit/beats.yaml; --check validates edit/edit.yaml
  fzv beats    <folder> [--redraft]       check the beat sheet, write beat_sheet.md and the review page (drafts it if missing)
  fzv approve  <folder> beats|storyboard  record the editor's approval (build waits for the beat sheet, render for the storyboard)
  fzv build    <folder>                   resolve anchors, compile clips (edit/built/)
  fzv preview  <folder> <clip> <t,t,...>  contact sheet of a clip over the real footage
  fzv validate <folder>                   rule checks before rendering
  fzv storyboard <folder> [--all]         one frame per beat over the real footage, before rendering (only changed frames redone)
  fzv mix      <folder> off|on|<track> [--level low|normal|high]   background music for this video; re-mixes only
  fzv studio   <folder> [--stop]          the live preview: the whole edit in HyperFrames Studio (no rendering)
  fzv draft    <folder>                   the preview video: the whole edit at a low frame rate with the real sound, before the final render
  fzv review   <folder> [--open]          the review page: beat sheet -> storyboard + preview -> final, change requests (edit/review/index.html)
  fzv render   <folder> [--only ids]      render changed clips (parallel, cached)
  fzv finish   <folder>                   SFX + music + mix, composite, encode, final MP4 (+ .srt if subtitles)
  fzv verify   <folder>                   final checks and a verification sheet
  fzv edit     <folder> [--prompt TEXT]   all of the above in order; stops where Claude or the editor has to act
  fzv revise   <folder> "7:41 change…"    map timestamps to scenes and log the request
  fzv templates [--refresh]               template catalogue and cards
  fzv props list | add <svg> --id ID --kind character|prop --tags "…" [--recolor] --source URL --licence L
  fzv icons add <svg> --id ID --source URL --licence L
  fzv music list | add <file> --id ID --mood M --source URL --licence L
  fzv sfx list | add <file|folder> [--category C] --source URL --licence L
  fzv registry search <words> | add <name…> | list   HyperFrames registry animations (mount with the `hf` template)
  fzv brands                              list brand kits
  fzv look     <folder> raw|rec1 t0-t1    tile frames over a raw-cut time range (--fps, --box x,y,w,h)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

from . import media
from .config import GLOBAL, REPO, brand_ids, defaults
from .project import Project


def log(msg: str):
    print(msg, flush=True)


# ---------------------------------------------------------------- ingest
def pick_raw(proj: Project, files: list[Path], forced: str | None) -> tuple[Path, list[Path]]:
    if forced:
        raw = proj.folder / forced
        return raw, [f for f in files if f != raw]
    if len(files) == 1:
        return files[0], []
    hint = re.compile(r"screen|record|capture|rec\b|ide|code", re.I)
    named = [f for f in files if hint.search(f.stem)]
    rest = [f for f in files if f not in named]
    if len(rest) == 1:
        return rest[0], named
    from .align import speech_fraction
    scored = sorted(files, key=lambda f: -speech_fraction(f))
    log("ingest: picked the raw cut by speech coverage (set it with --raw if wrong)")
    return scored[0], scored[1:]


def cmd_ingest(a) -> int:
    proj = Project(a.folder)
    settings = proj.settings()
    files = proj.media_files()
    if not files:
        log(f"no video files in {proj.folder}"); return 1
    raw, recs = pick_raw(proj, files, a.raw)
    info = media.probe(raw)
    gfps = 25 if round(info["fps"]) % 25 == 0 else min(30, round(info["fps"]))
    log(f"ingest: raw cut '{raw.name}'  {info['duration']:.2f}s  {info['fps']} fps  {info['width']}x{info['height']};  recordings: {[r.name for r in recs] or 'none'}")
    A = proj.edit / "audio"
    a16, voice = A / "a16.wav", A / "voice.wav"
    if not a16.exists():
        media.extract_audio(raw, a16, 16000, True)
    if not voice.exists():
        media.extract_audio(raw, voice, 48000, False, codec="pcm_s24le")
    tx_proc = None
    tx = proj.p("transcript.jsonl")
    if not a.no_transcribe and (a.force or not transcript_complete(proj)):
        if transcription_running(proj) and not a.force:
            log("ingest: transcription already running")
        else:
            if a.force:
                tx.unlink(missing_ok=True)
            tx_proc = start_transcription(proj)
            log("ingest: transcription started in the background" + (" (resuming)" if tx.exists() else ""))
    from .layout import analyse
    res = analyse(raw, info, settings["layout"], log)
    proj.p("cuts.json").write_text(json.dumps(res["cuts"], indent=1))
    proj.p("zones.json").write_text(json.dumps(res["zones"], indent=1))
    mode = settings["mode"]
    if mode == "auto":
        from .layout import auto_mode
        mode = auto_mode(res["cuts"], res["counts"], info["duration"])
        log(f"ingest: mode {mode} ({len(res['cuts'])} shots, {res['counts']['corner'] + res['counts']['empty']:.0f}s laid out)")
    if mode == "compose":
        from .compose import ingest as compose_ingest
        comp = compose_ingest(proj, raw, info, log, rekey=getattr(a, "rekey", False), fps=gfps)
        res["cuts"] = [{"kind": "plate", "start": 0.0, "end": round(info["duration"], 3)}]
        proj.p("cuts.json").write_text(json.dumps(res["cuts"], indent=1))
        res["zones"] = {}
        res["layout"] = settings["layout"]
        proj.update(compose=comp)
    recordings = []
    if recs:
        from .align import recordings as align_recs
        recordings = align_recs(a16, recs, log, [res["plate_ref"]] if res.get("plate_ref") is not None else [])
        proj.p("recordings.json").write_text(json.dumps(recordings, indent=1))
        from . import recref
        for r in recordings:
            if not r["needs_offset"]:
                recref.build(proj.folder / r["file"], r, proj.edit / "recref" / r["id"], log=log)
    from .machine import probe
    proj.update(raw=raw.name, duration=round(info["duration"], 3), fps=info["fps"], graphics_fps=gfps, mode=mode, brand=settings["brand"], plate_file=res.get("plate_file"),
                layout=res["layout"], zones=res["zones"], recordings=recordings, machine=probe(settings))
    proj.stage_done("ingest", mode=mode)
    if not a.no_transcribe and not transcript_complete(proj):
        wait_transcript(proj, log)
        log(f"ingest: transcript {'done' if transcript_complete(proj) else 'FAILED (see edit/transcribe.log)'}")
    try:
        from .review import footage
        footage(proj, log=log)
    except Exception as e:                                       # the footage sheet is a convenience; never fail ingest on it
        log(f"ingest: footage sheet skipped ({e})")
    log(f"ingest: done; mode {mode}. Next: `fzv plan {proj.folder}`")
    return 0


def cmd__transcribe(a) -> int:
    proj = Project(a.folder)
    from .transcribe import transcribe
    transcribe(proj.edit / "audio" / "a16.wav", proj.p("transcript.jsonl"), proj.settings()["transcription"], log=log)
    proj.p("transcript.done").write_text(time.strftime("%Y-%m-%d %H:%M:%S\n"))
    return 0


def transcript_complete(proj: Project) -> bool:
    """A transcript is complete when fzv finished it (marker), or when it came from elsewhere (no fzv log)."""
    tx = proj.p("transcript.jsonl")
    return tx.exists() and (proj.p("transcript.done").exists() or not proj.p("transcribe.log").exists())


def transcription_running(proj: Project) -> bool:
    import os
    f = proj.p("transcribe.pid")
    try:
        os.kill(int(f.read_text()), 0)
        return True
    except (OSError, ValueError):
        return False


def start_transcription(proj: Project) -> subprocess.Popen:
    proj.p("transcript.done").unlink(missing_ok=True)
    p = subprocess.Popen([sys.executable, "-m", "fzv", "_transcribe", str(proj.folder)], cwd=REPO,
                         stdout=open(proj.p("transcribe.log"), "w"), stderr=subprocess.STDOUT)
    proj.p("transcribe.pid").write_text(str(p.pid))
    return p


def wait_transcript(proj: Project, log=print, poll: float = 10.0) -> None:
    """Block until the background transcription finishes (plan and build need the whole transcript); resume it if it stopped."""
    tx, done, logf = proj.p("transcript.jsonl"), proj.p("transcript.done"), proj.p("transcribe.log")
    if transcript_complete(proj) or not proj.p("audio/a16.wav").exists():
        return
    if not transcription_running(proj):
        log("transcript: transcription is not running; resuming it")
        logf.write_text("")
        start_transcription(proj)
    dur, last = proj.load().get("duration") or 0, -1.0
    while not done.exists():
        rows = [json.loads(l) for l in tx.read_text(encoding="utf-8").splitlines() if l.strip()] if tx.exists() else []
        at = rows[-1]["end"] if rows else 0.0
        if at != last:
            log(f"transcript: {at:.0f}s of {dur:.0f}s")
            last = at
        if "Traceback" in logf.read_text(encoding="utf-8", errors="replace"):
            raise SystemExit(f"transcription failed; see {logf}")
        time.sleep(poll)


# ---------------------------------------------------------------- plan / build
def load_all(proj: Project):
    from . import spec as S
    from .anchors import Transcript
    settings = proj.settings()
    pdata = proj.load()
    if not proj.spec_path.exists():
        raise SystemExit(f"no {proj.spec_path} yet: run `fzv plan {proj.folder}` and write the spec")
    sp = S.load(proj.spec_path)
    if sp.get("brand"):
        settings["brand"] = sp["brand"]
    for k in ("subtitles", "music"):
        if isinstance(sp.get(k), dict):
            settings[k].update(sp[k])
        elif sp.get(k) in ("on", True):
            settings[k]["enabled"] = True
        elif sp.get(k) in ("off", False):
            settings[k]["enabled"] = False
    settings["graphics_fps"] = pdata.get("graphics_fps", settings.get("graphics_fps", 25))
    cuts = json.loads(proj.p("cuts.json").read_text()) if proj.p("cuts.json").exists() else [{"kind": "plate", "start": 0, "end": pdata.get("duration", 0)}]
    tx = Transcript(proj.p("transcript.jsonl"))
    return settings, pdata, sp, cuts, tx


def cmd_plan(a) -> int:
    proj = Project(a.folder)
    if a.check:
        from . import spec as S
        settings, pdata, sp, cuts, tx = load_all(proj)
        res, errs = S.resolve(sp, tx, pdata["duration"])
        from .plan import catalogue
        cat = catalogue()
        for sec in res.get("sections", []):
            for s in sec.get("scenes", []):
                (n, _), = s.items()
                if n not in cat:
                    errs.append(f"{sec.get('id')}: unknown template '{n}'")
        for e in errs:
            log(f"  {e}")
        log(f"plan --check: {'OK' if not errs else str(len(errs)) + ' problem(s)'}")
        return 0 if not errs else 1
    from . import beats as B
    from .plan import brief
    wait_transcript(proj, log)
    f = brief(proj, proj.settings())
    log(f"plan: wrote {f}")
    if not proj.p("beats.yaml").exists() and not B.legacy(proj):
        n = draft_beats(proj)
        log(f"plan: drafted {proj.p('beats.yaml')} ({n} beats from pauses, shots and concept moments)")
    log(f"Next: fill edit/beats.yaml (idea, show, templates, sync), run `fzv beats {proj.folder}` and show the editor the review page; "
        f"once approved, write {proj.spec_path} from it")
    return 0


# ---------------------------------------------------------------- beat sheet, storyboard, review (design §9f)
def draft_beats(proj: Project) -> int:
    from . import beats as B
    from .concepts import moments
    pdata = proj.load()
    tx = proj.p("transcript.jsonl")
    cuts = json.loads(proj.p("cuts.json").read_text()) if proj.p("cuts.json").exists() else [{"kind": "plate", "start": 0, "end": pdata["duration"]}]
    rows = B.draft(tx, cuts, pdata["duration"], moments(tx))
    B.write(proj.p("beats.yaml"), {"title": proj.prompt_fields().get("title") or proj.folder.name, "beats": rows})
    return len(rows)


def check_beats(proj: Project, settings: dict):
    from . import beats as B
    from .anchors import Transcript
    from .concepts import moments
    from .plan import catalogue
    from .registry import manifest
    from .validate import TEXT_ONLY
    doc = B.load(proj.p("beats.yaml"))
    return B.check(doc, Transcript(proj.p("transcript.jsonl")), proj.load()["duration"], set(catalogue()), {x["name"] for x in manifest()},
                   moments(proj.p("transcript.jsonl")), TEXT_ONLY, settings.get("visuals", {}).get("max_text_only_s", 15))


BEAT_STATUS = {"missing": "no beat sheet", "draft": "draft (Claude is filling it)", "proposed": "waiting for the editor's approval",
               "approved": "approved", "changed": "changed after approval: needs the editor's approval again"}


def write_beat_sheet(proj: Project) -> None:
    from . import beats as B
    from .review import title_of
    st = B.beats_state(proj)
    a = B.approval(proj, "beats") if st == "approved" else None
    status = BEAT_STATUS[st] + (f" ({a['at']}{': ' + a['note'] if a.get('note') else ''})" if a else "")
    proj.p("beat_sheet.md").write_text(B.markdown(B.load(proj.p("beats.yaml")), title_of(proj), status), encoding="utf-8")


def cmd_beats(a) -> int:
    from . import beats as B
    from .review import page
    proj = Project(a.folder)
    f = proj.p("beats.yaml")
    if a.redraft and f.exists():
        shutil.move(str(f), str(proj.edit / "_prev" / f"beats ({time.strftime('%Y%m%d-%H%M%S')}).yaml"))
        log("beats: previous beat sheet moved to edit/_prev/")
    if not f.exists():
        wait_transcript(proj, log)
        log(f"beats: drafted {f} ({draft_beats(proj)} beats). Fill idea, show, templates and sync, then run `fzv beats` again")
        return 0
    errs, warns, _ = check_beats(proj, proj.settings())
    write_beat_sheet(proj)
    out = page(proj, log=log)
    doc = B.load(f)
    log(f"beats: {len(doc.get('beats') or [])} beats; {len(errs)} problem(s), {len(warns)} note(s); status: {BEAT_STATUS[B.beats_state(proj)]}")
    for e in errs:
        log(f"  [problem] {e}")
    for w in warns:
        log(f"  [note] {w}")
    log(f"beats: {proj.p('beat_sheet.md')}\nreview page: {out}")
    return 1 if errs else 0


def cmd_approve(a) -> int:
    from . import beats as B
    from .review import page
    proj = Project(a.folder)
    if a.what == "beats":
        if not proj.p("beats.yaml").exists():
            log("approve: there is no beat sheet yet"); return 1
        errs, _, _ = check_beats(proj, proj.settings())
        if errs:
            log(f"approve: the beat sheet has {len(errs)} problem(s); fix them first:")
            for e in errs:
                log(f"  {e}")
            return 1
        B.record_approval(proj, "beats", B.beats_fingerprint(B.load(proj.p("beats.yaml"))), a.note or "")
        write_beat_sheet(proj)
        log("approve: beat sheet approved. Next: write edit/edit.yaml from it, build, validate, `fzv storyboard`")
    else:
        st = B.storyboard_state(proj)
        if st in ("missing", "stale"):
            log("approve: make the storyboard of the current build first (`fzv storyboard`)"); return 1
        why = preview_missing(proj, proj.settings())
        if why:
            log(f"approve: {why}"); return 1
        B.record_approval(proj, "storyboard", B.build_signature(proj), a.note or "")
        log("approve: storyboard approved. Next: render, finish, verify")
    page(proj, log=log)
    return 0


def cmd_storyboard(a) -> int:
    from .machine import probe
    from .review import page, storyboard
    proj = Project(a.folder)
    if not proj.p("beats.yaml").exists():
        log("storyboard: needs a beat sheet (edit/beats.yaml)"); return 1
    if not (proj.edit / "built" / "clips.json").exists():
        log("storyboard: build the edit first (`fzv build`)"); return 1
    storyboard(proj, workers=max(1, min(3, probe(proj.settings())["render_workers"])), redo_all=a.all, log=log)
    log(f"review page: {page(proj, log=log)}")
    return 0


def preview_mode(settings: dict) -> str:
    """browser | video | off (`required`, the earlier name, means video)."""
    from . import beats as B
    m = B.gate_mode(settings, "preview")
    return "video" if m == "required" else m


def preview_missing(proj: Project, settings: dict) -> str | None:
    """Why the storyboard can't be approved yet for want of a preview of the current build (None when it can)."""
    mode = preview_mode(settings)
    if mode == "browser":
        from .studio import state
        return None if state(proj) == "ready" else "open the live preview of the current build first (`fzv studio`) so the editor can watch it"
    if mode == "video":
        from .draft import preview_state
        return None if preview_state(proj) == "ready" else "make the preview video of the current build first (`fzv draft`) so the editor can watch it"
    return None


def cmd_studio(a) -> int:
    """The live preview: the whole edit in HyperFrames Studio (no rendering). Made when the editor asks, or before the final render."""
    from . import studio as St
    from .review import page
    proj = Project(a.folder)
    S = proj.edit / "studio"
    if a.stop:
        St.serve(S, stop=True, log=log); page(proj, log=log); return 0
    if not (proj.edit / "built" / "clips.json").exists():
        log("studio: build the edit first (`fzv build`)"); return 1
    if St.state(proj) != "ready":
        settings, *_ = load_all(proj)
        St.build(proj, settings, log=log)
    if not a.build_only:
        St.serve(S, port=a.port, open_browser=not a.no_open, log=log)
    log(f"review page: {page(proj, log=log)}")
    return 0


def cmd_draft(a) -> int:
    from .draft import draft
    from .machine import probe
    from .review import page
    proj = Project(a.folder)
    if not (proj.edit / "built" / "clips.json").exists():
        log("draft: build the edit first (`fzv build`)"); return 1
    if not (proj.edit / "audio" / "cues.json").exists():
        log("draft: validate the edit first (`fzv validate`): it records the sound-effect cues"); return 1
    settings, *_ = load_all(proj)
    m = probe(proj.settings())
    draft(proj, settings, workers=m["render_workers"], low_memory=m["low_memory"], log=log)
    log(f"review page: {page(proj, log=log)}")
    return 0


def set_prompt_field(proj: Project, key: str, value: str) -> None:
    """Replace (or add) a `Key: value` line in the video's prompt.md."""
    f = proj.folder / "prompt.md"
    lines = f.read_text(encoding="utf-8").splitlines() if f.exists() else [f"# {proj.folder.name}"]
    pat = re.compile(rf"^\s*{re.escape(key)}\s*:", re.I)
    for i, ln in enumerate(lines):
        if pat.match(ln):
            lines[i] = f"{key}: {value}"
            break
    else:
        lines.insert(1, f"{key}: {value}")
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")


def cmd_mix(a) -> int:
    """Music on/off, track and level for one video: updates prompt.md and re-mixes only (no graphics are rendered again)."""
    proj = Project(a.folder)
    cur = proj.settings()["music"]
    if a.music == "off":
        value = "off"
    else:
        track = a.music if a.music not in ("on", None) else (cur.get("track") or "calm-piano")
        value = track + ({"low": ", low", "high": ", high"}.get(a.level or "", ""))
        from .config import load_yaml
        known = [t["id"] for t in load_yaml(GLOBAL / "music" / "manifest.yaml").get("tracks") or []]
        if track not in known:
            log(f"mix: no music track '{track}' (tracks: {', '.join(known)})"); return 1
    set_prompt_field(proj, "Music", value)
    sp = proj.spec_path
    if sp.exists() and "music" in (yaml.safe_load(sp.read_text()) or {}):
        log("mix: note: edit.yaml has its own `music:`, which wins over the prompt; remove it to use this setting")
    log(f"mix: music {value}")
    title = (yaml.safe_load(sp.read_text()) or {}).get("title") if sp.exists() else None
    title = title or proj.prompt_fields().get("title") or proj.folder.name
    if proj.output_path(title).exists():
        if cmd_finish(argparse.Namespace(folder=a.folder)):
            return 1
        return cmd_verify(argparse.Namespace(folder=a.folder))
    from .draft import preview_state
    if preview_state(proj) == "ready":
        return cmd_draft(argparse.Namespace(folder=a.folder))
    log("mix: saved; it is used when the preview or the final is made")
    return 0


def cmd_review(a) -> int:
    from . import beats as B
    from .review import page
    proj = Project(a.folder)
    if not proj.load().get("raw"):
        log("review: ingest the video first"); return 1
    out = page(proj, log=log)
    title = (B.load(proj.spec_path).get("title") if proj.spec_path.exists() else None) or proj.prompt_fields().get("title") or proj.folder.name
    log(f"review: beat sheet {B.beats_state(proj)} · storyboard {B.storyboard_state(proj)} · final {'yes' if proj.output_path(title).exists() else 'not yet'}")
    log(f"review: {out}")
    if a.open:
        import webbrowser
        webbrowser.open(out.as_uri())
    return 0


def write_decisions(proj: Project, sp: dict, settings: dict, res: dict | None = None):
    lines = ["# Decisions", "", f"- Brand: {settings['brand']}", f"- Styles: {', '.join(sp.get('styles') or ['core', 'code'])}",
             f"- Subtitles: {'on' if settings['subtitles']['enabled'] else 'off'}", f"- Music: {'on (' + str(settings['music'].get('track')) + ')' if settings['music']['enabled'] else 'off'}"]
    if sp.get("decisions"):
        lines += ["", "## Why", "", str(sp["decisions"]).strip()]
    if sp.get("overrides"):
        lines += ["", "## Overrides of global rules (from the prompt)", ""] + [f"- **{k}**: {v}" for k, v in sp["overrides"].items()]
    if sp.get("quiet"):
        lines += ["", "## Deliberately clean stretches (rule L4 not applied)", ""] + [f"- {q[0]}–{q[1]} s: {q[2] if len(q) > 2 else ''}" for q in sp["quiet"]]
    fixes, confirm = [], list(sp.get("confirm") or [])
    for sec in (res or {}).get("sections") or []:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            cr = p.get("corrections_result") if name == "code-card" and isinstance(p, dict) else None
            if cr and cr.get("changes"):
                same = {True: "output unchanged", False: "**output changes**", None: "not run"}[cr.get("output_same")]
                fixes.append(f"- `{p.get('id')}` ({same}): " + "; ".join(cr["changes"]))
                if cr.get("output_same") is False:
                    confirm.append(f"Code card `{p.get('id')}` corrects the recording and its output changes "
                                   f"(recorded: {' / '.join(cr['recorded_output'])}; shown: {' / '.join(cr['output'])}). {p.get('logic_fix', '')}")
    if fixes:
        lines += ["", "## Corrections from the recording", "", f"Mode: {settings.get('recordings', {}).get('corrections', 'tidy')}"] + fixes
    if confirm:
        lines += ["", "## To confirm", ""] + [f"- {c}" for c in confirm]
    if sp.get("props_to_add"):
        lines += ["", "## Props to add", ""] + [f"- {c}" for c in sp["props_to_add"]]
    proj.p("decisions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_corner_box(proj: Project, pdata: dict, settings: dict, res: dict, clips: list[dict], cuts: list[dict]) -> None:
    """Rough cuts (setting presenter.corner_box): frame the instructor's bottom-right area in the brand box during her corner
    shots; strips outside the box are covered with the matching plate, so she is cut by the box (rule L5)."""
    pset = dict(settings.get("presenter") or {})
    pset.update({k: v for k, v in (res.get("presenter") or {}).items() if k != "poses"})
    z = (pdata.get("zones") or {}).get("corner")
    if not pset.get("corner_box", True) or not z:
        return
    B = dict({"margin": 40, "radius": 28, "pad": 16}, **(pset.get("box") or {}))
    x0, y0 = max(0, z["bbox"][0] - B["pad"]), max(0, z["bbox"][1] - B["pad"])
    x1, y1 = 1920 - B["margin"], 1080 - B["margin"]
    if x1 - x0 < 200 or y1 - y0 < 150:
        return
    plate = pdata.get("plate_file")
    if plate:                                                   # the exact image the editor used, so patches are seamless
        from .build import link_or_copy
        from .config import BRANDS
        link_or_copy(BRANDS / plate, proj.edit / "comp" / "assets" / "brand" / "editor_plate.png")
    for c in clips:
        if c["layer"] != "plate":
            continue
        iv = [[max(c["start"], k["start"]), min(c["end"], k["end"])] for k in cuts if k["kind"] == "corner" and k["end"] > c["start"] and k["start"] < c["end"]]
        if iv:
            c["scenes"].insert(0, {"template": "corner-box", "params": {"box": [x0, y0, x1 - x0, y1 - y0], "radius": B["radius"], "intervals": iv,
                                                                        "plate": "assets/brand/" + ("editor_plate.png" if plate else "plate.png")}})


def cmd_build(a) -> int:
    from . import spec as S
    from .build import build
    from .beats import gate_build
    proj = Project(a.folder)
    settings, pdata, sp, cuts, tx = load_all(proj)
    why = gate_build(proj, settings)
    if why:
        log(f"build: waiting: {why}"); return 1
    if (sp.get("mode") or pdata.get("mode")) == "compose":
        from .compose import build_compose
        return build_compose(proj, settings, pdata, sp, cuts, tx, log)
    res, errs = S.resolve(sp, tx, pdata["duration"])
    if not errs:
        from .execute import apply as run_programs
        errs = run_programs(res, proj.p("runs"))
    if errs:
        for e in errs:
            log(f"  {e}")
        log(f"build: {len(errs)} problem(s); fix edit.yaml"); return 1
    with open(proj.p("edit.resolved.yaml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(res, f, sort_keys=False, allow_unicode=True)
    clips = S.plan_clips(res, cuts, settings["graphics_fps"], settings["bug"]["layers"])
    add_corner_box(proj, pdata, settings, res, clips, cuts)
    if settings["subtitles"]["enabled"] and proj.p("transcript.jsonl").exists():
        from .captions import cues
        cc = cues(proj.p("transcript.jsonl"), settings["subtitles"]["max_chars"], settings["subtitles"]["max_lines"])
        proj.p("captions.json").write_text(json.dumps(cc, indent=1))
        for c in clips:
            mine = [q for q in cc if c["start"] <= q["at"] < c["end"]]
            if mine:
                c["scenes"].append({"template": "captions", "params": {"cues": mine}})
    man = build(proj, res, clips, settings)
    proj.p("clips.json").write_text(json.dumps(clips, indent=1))
    write_decisions(proj, sp, settings, res)
    proj.stage_done("build", clips=len(man))
    log(f"build: {len(man)} clip(s) ({sum(1 for m in man if m['layer'] == 'plate')} plate, {sum(1 for m in man if m['layer'] == 'studio')} studio)")
    return 0


def built(proj: Project):
    man = json.loads((proj.edit / "built" / "clips.json").read_text())
    clips = json.loads(proj.p("clips.json").read_text())
    return man, clips


def cmd_preview(a) -> int:
    from .preview import preview
    proj = Project(a.folder)
    man, _ = built(proj)
    c = next((m for m in man if m["id"] == a.clip), None)
    if not c:
        log(f"no clip {a.clip}; clips: {', '.join(m['id'] for m in man)}"); return 1
    out = preview(proj, c, [float(t) for t in a.times.split(",")], proj.folder / proj.load()["raw"])
    log(f"preview: {out}")
    return 0


def cmd_validate(a) -> int:
    from .validate import validate
    proj = Project(a.folder)
    settings, pdata, sp, cuts, tx = load_all(proj)
    man, clips = built(proj)
    import yaml as _y
    res = _y.safe_load(proj.p("edit.resolved.yaml").read_text())
    rep = validate(proj, res, clips, man, cuts, pdata.get("zones", {}), settings, log=log)
    return 0 if rep["ok"] else 1


def cmd_render(a) -> int:
    from .beats import gate_render
    from .machine import probe
    from .render import render
    proj = Project(a.folder)
    why = gate_render(proj, proj.settings())
    if why:
        log(f"render: waiting: {why}"); return 1
    man, _ = built(proj)
    m = probe(proj.settings())
    workers = a.workers or m["render_workers"]
    t0 = time.time()
    render(proj, man, workers, m["low_memory"], a.only.split(",") if a.only else None, log)
    proj.stage_done("render", seconds=round(time.time() - t0), workers=workers)
    return 0


def cmd_finish(a) -> int:
    from .audio import mix
    from .finish import finish, write_srt
    proj = Project(a.folder)
    settings, pdata, sp, cuts, tx = load_all(proj)
    man, clips = built(proj)
    by = {m["id"]: m for m in man}
    for c in clips:
        c["hash"] = by[c["id"]]["hash"]
    raw = proj.folder / pdata["raw"]
    info = media.probe(raw)
    t0 = time.time()
    mix_wav = mix(proj, raw, info["duration"], settings, log)
    title = sp.get("title") or proj.prompt_fields().get("title") or proj.folder.name
    if (sp.get("mode") or pdata.get("mode")) == "compose":
        from .compose import finish_compose
        out = finish_compose(proj, info, clips, mix_wav, proj.output_path(title), settings, log)
    else:
        out = finish(proj, raw, info, clips, cuts, mix_wav, proj.output_path(title), settings, log)
    if settings["subtitles"]["enabled"] and proj.p("captions.json").exists():
        write_srt(json.loads(proj.p("captions.json").read_text()), out.with_suffix(".srt"))
    from .audio import export_stems
    (proj.edit / "review").mkdir(exist_ok=True)
    export_stems(proj, proj.edit / "review")                      # the review page's music on/off switch
    proj.stage_done("finish", output=out.name, seconds=round(time.time() - t0))
    return 0


def cmd_verify(a) -> int:
    from .verify import verify
    proj = Project(a.folder)
    settings, pdata, sp, cuts, tx = load_all(proj)
    title = sp.get("title") or proj.prompt_fields().get("title") or proj.folder.name
    rep = verify(proj, proj.output_path(title), media.probe(proj.folder / pdata["raw"]), cuts, log)
    log(f"verify: sheet {rep['sheet']}")
    from .review import page
    log(f"review page: {page(proj, settings, log=log)}")
    return 0 if rep["ok"] else 1


def cmd_edit(a) -> int:
    """Everything in order. Stops where someone has to act: Claude fills the beat sheet and writes edit.yaml, the editor approves
    the beat sheet and the storyboard (settings `review.*`)."""
    from . import beats as B
    proj = Project(a.folder)
    if a.prompt:
        (proj.folder / "prompt.md").write_text(a.prompt.strip() + "\n", encoding="utf-8")
    if not proj.load().get("stages", {}).get("ingest"):
        if cmd_ingest(argparse.Namespace(folder=a.folder, raw=None, no_transcribe=False, force=False, rekey=False)):
            return 1
    settings = proj.settings()
    if not proj.p("plan_brief.md").exists() or (not proj.p("beats.yaml").exists() and not B.legacy(proj)):
        cmd_plan(argparse.Namespace(folder=a.folder, check=False))
    why = B.gate_build(proj, settings)
    if why:
        log(f"edit: waiting: {why}"); return 0
    if not proj.spec_path.exists():
        log("edit: stopping here; write edit/edit.yaml " + ("from the approved beat sheet" if proj.p("beats.yaml").exists() else "from edit/plan_brief.md")
            + ", then run `fzv edit` again"); return 0
    for step in (cmd_build, cmd_validate):
        if step(argparse.Namespace(folder=a.folder)):
            if step is cmd_validate and not a.force:
                log("edit: validation found problems; fix edit.yaml or rerun with --force"); return 1
            elif step is cmd_build:
                return 1
    if B.gate_mode(settings, "storyboard") != "off" and proj.p("beats.yaml").exists():
        if cmd_storyboard(argparse.Namespace(folder=a.folder, all=False)):
            return 1
        if B.storyboard_state(proj) != "approved" and preview_missing(proj, settings):
            if preview_mode(settings) == "browser":
                if cmd_studio(argparse.Namespace(folder=a.folder, stop=False, port=None, no_open=False, build_only=False)):
                    return 1
            elif cmd_draft(argparse.Namespace(folder=a.folder)):
                return 1
        why = B.gate_render(proj, settings)
        if why:
            log(f"edit: waiting: {why}"); return 0
    if cmd_render(argparse.Namespace(folder=a.folder, workers=None, only=None)):
        return 1
    cmd_finish(argparse.Namespace(folder=a.folder))
    return cmd_verify(argparse.Namespace(folder=a.folder))


def cmd_revise(a) -> int:
    from . import revise as Rv
    from . import spec as S
    proj = Project(a.folder)
    settings, pdata, sp, cuts, tx = load_all(proj)
    res, _ = S.resolve(sp, tx, pdata["duration"])
    request = a.request
    if proj.p("beats.yaml").exists():                            # "beat 7: …" means the beat's time
        from .beats import expand_refs, load as load_beats
        request = expand_refs(request, load_beats(proj.p("beats.yaml")))
    items = []
    for t, what in Rv.parse(request):
        ctx = Rv.context(res, t, tx)
        ctx["request"] = what
        items.append(ctx)
        log(f"\n{int(t // 60)}:{t % 60:05.2f}  \"{what}\"")
        for s in ctx["scenes"]:
            log(f"  scene: {s['section']} #{s['scene']} {s['template']} ({s['at']}–{s['until']})")
        log(f"  speech: {ctx['speech'][:300]}")
    if not items:
        log("revise: no time or beat number found; write requests like \"7:41 make the note larger\" or \"beat 7: use a car\""); return 1
    Rv.log_request(proj, a.request, items)
    log("\nrevise: logged in edit/revisions.md. Change those scenes in edit.yaml, then run build, validate, render, finish, verify (only changed clips and chunks are redone).")
    return 0


def cmd_templates(a) -> int:
    from .plan import catalogue
    cat = catalogue(refresh=a.refresh)
    fam = {}
    for n, m in cat.items():
        fam.setdefault(m.get("family"), []).append(n)
    for f, ns in sorted(fam.items()):
        log(f"{f:8s} {', '.join(sorted(ns))}")
    log(f"{len(cat)} templates; cards in global/templates/<family>/")
    return 0


def cmd_props(a) -> int:
    from .config import load_yaml
    man_f = GLOBAL / "props" / "manifest.yaml"
    man = load_yaml(man_f)
    if a.action == "list":
        for x in man.get("assets", []):
            log(f"{x['id']:16s} {x['kind']:10s} {x.get('style', 'flat'):5s} {x.get('tags', '')}")
        return 0
    from .assets import add_prop
    if not a.svg or not a.id:
        log("props add: give the SVG file and --id"); return 1
    try:
        e = add_prop(Path(a.svg).read_text(encoding="utf-8"), a.id, a.kind, a.tags, a.source, a.licence, a.style, recolour=a.recolor, log=log)
    except ValueError as err:
        log(f"props add: {err}"); return 1
    log(f"props add: {e['id']} added ({e['kind']}, size {e['size']})")
    return 0


def cmd_icons(a) -> int:
    from .assets import add_icon, attribution_warning, licence_problem
    if p := licence_problem(a.licence):
        log(f"icons add: {p}"); return 1
    if w := attribution_warning(a.licence):
        log(f"icons add: warning: {w}")
    add_icon(Path(a.svg), a.id, a.source, a.licence)
    log(f"icons add: i-{a.id} added to runtime/icons.svg (use it as icon: {a.id})")
    return 0


def cmd_music(a) -> int:
    from .assets import add_music, attribution_warning, licence_problem
    from .config import load_yaml
    if a.action == "list":
        for t in load_yaml(GLOBAL / "music" / "manifest.yaml").get("tracks") or []:
            log(f"{t['id']:18s} {t.get('mood', ''):10s} {t.get('duration', '')}s  {t.get('licence', '')}  {t.get('source', '')}")
        return 0
    if not a.file or not a.id or not a.source:
        log("music add: give the file, --id, --source and --licence"); return 1
    if p := licence_problem(a.licence):
        log(f"music add: {p}"); return 1
    if w := attribution_warning(a.licence):
        log(f"music add: warning: {w}")
    t = add_music(Path(a.file), a.id, a.mood, a.bpm, a.source, a.licence)
    log(f"music add: {t['id']} ({t['duration']}s) -> global/music/{t['file']}; use it with `Music: {t['id']}, low`")
    return 0


def cmd_sfx(a) -> int:
    from .assets import SFX_CATEGORIES, add_sfx, attribution_warning, licence_problem
    from .audio import sfx_library
    if a.action == "remove":
        from .assets import remove_sfx
        log(f"sfx remove: {', '.join(remove_sfx([a.path] + (a.more or []))) or 'nothing matched'}")
        return 0
    if a.action == "audition":
        from .assets import sfx_audition
        sfx_audition(log=log)
        return 0
    if a.action == "list":
        lib = sfx_library()
        for cat in SFX_CATEGORIES:
            log(f"{cat:8s} {len(lib.get(cat, [])):3d}  {', '.join(s['file'] for s in lib.get(cat, [])[:4])}{' …' if len(lib.get(cat, [])) > 4 else ''}")
        return 0
    if not a.path or not a.source:
        log("sfx add: give a file or folder, --source and --licence"); return 1
    if p := licence_problem(a.licence):
        log(f"sfx add: {p}"); return 1
    if w := attribution_warning(a.licence):
        log(f"sfx add: warning: {w}")
    added = add_sfx(Path(a.path), a.category, a.source, a.licence, a.gain)
    log(f"sfx add: {len(added)} sound(s) added" + ("" if added else " (no recognised category: pass --category)"))
    for e in added[:20]:
        log(f"  {e['category']:8s} {e['file']}")
    return 0


def cmd_registry(a) -> int:
    from . import registry as Rg
    if a.action == "search":
        for x in Rg.search(" ".join(a.names))[:60]:
            d = x.get("dimensions") or {}
            log(f"{x['type'][:4]} {x['name']:30s} {d.get('width', '')}x{d.get('height', '')}  {x['description'][:110]}")
        return 0
    if a.action == "list":
        for x in Rg.manifest():
            log(f"{x['name']:28s} {x['type'][:4]}  vars: {', '.join(v['id'] for v in x.get('variables', [])) or '-'}")
        return 0
    if not a.names:
        log("registry add: give one or more item names (fzv registry search <words>)"); return 1
    Rg.add(a.names, log=log)
    return 0


def cmd_brands(a) -> int:
    for b in brand_ids():
        log(f"{b}{'  (default)' if b == defaults()['brand'] else ''}")
    return 0


def cmd_doctor(a) -> int:
    from .machine import library, probe, report
    log(report(probe(defaults())))
    log("library: " + ", ".join(f"{v} {k}" for k, v in library().items()))
    return 0


def cmd_look(a) -> int:
    """Tile frames of the raw cut or a recording over a raw-cut time range, labelled with raw-cut times."""
    from PIL import Image, ImageDraw
    proj = Project(a.folder)
    pdata = proj.load()
    t0, t1 = (float(x) for x in a.range.split("-"))
    if a.source == "raw":
        src, off = proj.folder / pdata["raw"], 0.0
    else:
        r = next((r for r in pdata.get("recordings") or [] if r["id"] == a.source), None)
        if not r:
            log(f"no recording {a.source}"); return 1
        src, off = proj.folder / r["file"], r.get("offset") or 0.0
    info = media.probe(src)
    bx = [int(v) for v in a.box.split(",")] if a.box else [0, 0, info["width"], info["height"]]
    n = max(1, int((t1 - t0) * a.fps) + 1)
    tw = 1800 // a.cols
    th = round(tw * bx[3] / bx[2])
    rows = (n + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (a.cols * tw, rows * (th + 26)), (24, 32, 44))
    d = ImageDraw.Draw(sheet)
    for i in range(n):
        t = t0 + i / a.fps
        b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t - off):.3f}", "-i", str(src), "-frames:v", "1", "-vf",
                            f"crop={bx[2]}:{bx[3]}:{bx[0]}:{bx[1]},scale={tw}:{th}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        if len(b) == tw * th * 3:
            x, y = (i % a.cols) * tw, (i // a.cols) * (th + 26)
            sheet.paste(Image.frombytes("RGB", (tw, th), b), (x, y + 26))
            d.text((x + 6, y + 6), f"{t:.1f}s", fill=(230, 236, 245))
    out = proj.edit / "out" / f"look_{a.source}_{t0:.0f}-{t1:.0f}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    log(f"look: {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fzv", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    def add(name, fn, folder=True, **kw):
        p = sub.add_parser(name, **kw); p.set_defaults(fn=fn)
        if folder:
            p.add_argument("folder")
        return p
    add("doctor", cmd_doctor, folder=False)
    p = add("ingest", cmd_ingest); p.add_argument("--raw"); p.add_argument("--no-transcribe", action="store_true"); p.add_argument("--force", action="store_true")
    p.add_argument("--rekey", action="store_true", help="compose mode: key the instructor again (e.g. after changing `key:` options)")
    add("_transcribe", cmd__transcribe)
    p = add("plan", cmd_plan); p.add_argument("--check", action="store_true")
    p = add("beats", cmd_beats); p.add_argument("--redraft", action="store_true", help="start a new draft (the old sheet goes to edit/_prev/)")
    p = add("approve", cmd_approve); p.add_argument("what", choices=["beats", "storyboard"]); p.add_argument("--note", help="the editor's words")
    p = add("storyboard", cmd_storyboard); p.add_argument("--all", action="store_true", help="redo every frame")
    p = add("mix", cmd_mix, help="music on/off, track and level; re-mixes the final (or the preview) without rendering graphics again")
    p.add_argument("music", help="off | on | <track id>"); p.add_argument("--level", choices=["low", "normal", "high"])
    p = add("studio", cmd_studio, help="the live preview: the whole edit in HyperFrames Studio, no rendering (--stop to close it)")
    p.add_argument("--stop", action="store_true"); p.add_argument("--port", type=int); p.add_argument("--no-open", action="store_true")
    p.add_argument("--build-only", action="store_true", help="write edit/studio/ without starting Studio")
    add("draft", cmd_draft, help="the preview video of the whole edit (low frame rate, real timing and sound) before the final render")
    p = add("review", cmd_review); p.add_argument("--open", action="store_true", help="open the page in the browser")
    add("build", cmd_build)
    p = add("preview", cmd_preview); p.add_argument("clip"); p.add_argument("times")
    add("validate", cmd_validate)
    p = add("render", cmd_render); p.add_argument("--only"); p.add_argument("--workers", type=int)
    add("finish", cmd_finish)
    add("verify", cmd_verify)
    p = add("edit", cmd_edit); p.add_argument("--prompt"); p.add_argument("--force", action="store_true")
    p = add("revise", cmd_revise); p.add_argument("request")
    p = add("templates", cmd_templates, folder=False); p.add_argument("--refresh", action="store_true")
    p = add("props", cmd_props, folder=False); p.add_argument("action", choices=["list", "add"]); p.add_argument("svg", nargs="?")
    p.add_argument("--id"); p.add_argument("--kind", default="prop"); p.add_argument("--style", default="flat"); p.add_argument("--tags", default="")
    p.add_argument("--source", default="in-house"); p.add_argument("--licence", default="Fuzentrix (original)")
    p.add_argument("--recolor", action="store_true", help="map the SVG's fixed colours to the nearest brand variables")
    p = add("icons", cmd_icons, folder=False); p.add_argument("action", choices=["add"]); p.add_argument("svg"); p.add_argument("--id", required=True)
    p.add_argument("--source", required=True); p.add_argument("--licence", required=True)
    p = add("sfx", cmd_sfx, folder=False); p.add_argument("action", choices=["list", "add", "audition", "remove"]); p.add_argument("path", nargs="?")
    p.add_argument("more", nargs="*", help="remove: more files or category:number from the audition list")
    p.add_argument("--category", help="whoosh, swish, pop, blip, tick, click, ding, good, bad, thud, impact, chime, type (guessed from file names if omitted)")
    p.add_argument("--source"); p.add_argument("--licence", default=""); p.add_argument("--gain", type=float, default=0.0)
    p = add("registry", cmd_registry, folder=False, help="HyperFrames registry items: search, add, list")
    p.add_argument("action", choices=["search", "add", "list"]); p.add_argument("names", nargs="*")
    p = add("music", cmd_music, folder=False); p.add_argument("action", choices=["list", "add"]); p.add_argument("file", nargs="?")
    p.add_argument("--id"); p.add_argument("--mood", default="calm"); p.add_argument("--bpm", type=int); p.add_argument("--source"); p.add_argument("--licence", default="")
    add("brands", cmd_brands, folder=False)
    p = add("look", cmd_look, help="tile frames of the raw cut or a recording over a raw-cut time range")
    p.add_argument("source", help="raw | rec1 | rec2 ..."); p.add_argument("range", help="t0-t1 in raw-cut seconds")
    p.add_argument("--fps", type=float, default=1.0); p.add_argument("--box", help="x,y,w,h crop in source pixels"); p.add_argument("--cols", type=int, default=4)
    a = ap.parse_args(argv)
    sys.exit(a.fn(a) or 0)
