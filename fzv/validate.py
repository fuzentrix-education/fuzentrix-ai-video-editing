"""`fzv validate`: rule checks (design §8, global/rules.yaml) on DOM boxes sampled from every built clip, before rendering.

A video's prompt may override any rule; overrides are listed in the spec under `overrides: {RULE: reason}` and logged in decisions.md.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .config import REPO, rules as load_rules

BLOCKS = {"block", "code", "term", "note"}
# rule V1/V2: templates that SHOW a process (things move, transform, flow) vs templates that only put words on screen
TEXT_ONLY = {"header", "title-hero", "card", "definition", "chips", "term-reveal", "rule-stack", "summary", "agenda", "problem", "note",
             "name-card", "studio-tag", "captions", "contrast", "big-word", "callouts", "checklist", "bug", "scene", "presenter",
             "progress", "chapter", "sound"}


def text_only_stretches(sec: dict, end_default: float, hidden: list[tuple[float, float]] = ()) -> list[tuple[float, float]]:
    """Stretches of a section's plate time where only text templates are on screen. `hidden` (studio shots, where plate graphics
    are not shown, and deliberate quiet stretches) is cut out of them."""
    from .spec import scene_span
    lo, hi = sec["range"]
    vis = []
    for s in sec.get("scenes") or []:
        (name, p), = s.items()
        a, b = scene_span(p, hi)
        if name in TEXT_ONLY or a is None:
            continue
        vis.append((max(lo, a), min(hi, b)))
    gaps, t = [], lo
    for a, b in sorted(vis):
        if a > t:
            gaps.append((t, a))
        t = max(t, b)
    if t < hi:
        gaps.append((t, hi))
    out = []
    for a, b in gaps:                                   # cut the hidden intervals out of each gap
        pieces = [(a, b)]
        for h0, h1 in hidden:
            pieces = [q for p0, p1 in pieces for q in ((p0, min(p1, h0)), (max(p0, h1), p1)) if q[1] - q[0] > 0.05]
        out += pieces
    return out
CONTENT = BLOCKS | {"text", "cutaway", "part"}
TYPE_EXEMPT = {"hf", "db3d", "network3d", "loop3d", "sketch-board", "sketch-draw", "sketch-text", "sketch-list", "sketch-flow", "sketch-mark", "mockup"}   # L13: they draw their own text
ALIGN_EXEMPT = {"header", "title-hero", "chapter", "progress", "bug", "name-card", "studio-tag", "captions", "presenter", "note", "hf",
                "prop-move", "prop-scene", "picture", "prop", "cutaway", "scene", "big-word", "contrast"}   # L14: chrome, wired notes, pictures and free-moving props


def scene_in(spec: dict, want: str, lo: float, hi: float) -> bool:
    """A scene of template `want` (or `hf:<item>`) is on screen at some point between lo and hi (1 s tolerance)."""
    item = want[3:] if want.startswith("hf:") else None
    name = "hf" if item else want
    groups = [(s, sec["range"][1]) for sec in spec.get("sections") or [] for s in sec.get("scenes") or []]
    groups += [(s, None) for s in spec.get("studio") or []]
    from .spec import scene_span
    for s, end in groups:
        (n, p), = s.items()
        if n != name or (item and isinstance(p, dict) and p.get("item") != item):
            continue
        at, until = scene_span(p, end)
        if at is None:
            continue
        if until is None:
            until = at + 5
        if at <= hi + 1 and until >= lo - 1:
            return True
    return False


def sample(html: Path, local_times: list[float]) -> dict:
    p = subprocess.run(["node", str(REPO / "node" / "sample.mjs"), "sample", str(html), ",".join(f"{t:.2f}" for t in local_times)],
                       capture_output=True, text=True, cwd=REPO)
    if p.returncode != 0:
        raise RuntimeError(f"sampler failed for {html.name}: {p.stderr[-1500:]}")
    return json.loads(p.stdout)


def sample_cached(proj, m: dict, local_times: list[float]) -> dict:
    """DOM samples of a clip, cached by its content hash (a revision re-samples only the clips that changed)."""
    key = f"{m['id']}_{m.get('hash', 'nohash')}_{len(local_times)}_{local_times[0] if local_times else 0:.2f}_s10.json"   # s10: + painted boxes of titles (L12); exact first-seen times (refine); data-nowords left out
    D = proj.edit / "validate_cache"
    f = D / key
    if m.get("hash") and f.exists():
        return json.loads(f.read_text())
    res = sample(proj.edit / "built" / m["html"], local_times)
    D.mkdir(exist_ok=True)
    for old in D.glob(f"{m['id']}_*.json"):
        old.unlink()
    f.write_text(json.dumps(res))
    return res


def kind_at(cuts: list[dict], t: float) -> str:
    for c in cuts:
        if c["start"] <= t < c["end"]:
            return c["kind"]
    return cuts[-1]["kind"] if cuts else "plate"


def overlap_share(a, b) -> float:
    """Intersection area as a share of the smaller box ([x0, y0, x1, y1])."""
    w, h = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    return w * h / max(1, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


def contains(a, b, pad: int = 4) -> bool:
    return a[0] - pad <= b[0] and a[1] - pad <= b[1] and a[2] + pad >= b[2] and a[3] + pad >= b[3]


def inter(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def box(it):
    return [it["x"], it["y"], it["x"] + it["w"], it["y"] + it["h"]]


def background_changes(spec: dict) -> list[tuple[float, str]]:
    """(time, template) of every scene that replaces the whole background: a dark `scene` or a full-frame `cutaway` (rule L11)."""
    out = []
    for sec in spec.get("sections") or []:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            if name in ("scene", "cutaway"):
                out.append((p.get("at") if isinstance(p.get("at"), (int, float)) else (sec.get("range") or [0])[0], name))
    return out


def validate(proj, spec: dict, clips: list[dict], manifest: list[dict], cuts: list[dict], zones: dict, settings: dict, step: float = 0.5, log=print) -> dict:
    R = load_rules()
    over = set((spec.get("overrides") or {}).keys())
    clutter, empty = settings["clutter"], settings["empty"]
    problems, sfx, errors = [], [], []

    quiet = [(q[0], q[1]) for q in (spec.get("quiet") or [])]       # deliberate clean stretches, e.g. the editor's logo animation

    def flag(rule, t, msg):
        if rule == "L4" and any(a <= t <= b + empty["max_gap_s"] for a, b in quiet):
            return
        if rule not in over:
            problems.append({"rule": rule, "t": round(t, 2), "msg": msg})

    occ_cells, crop_wh = [], (1, 1)
    if (proj.load().get("compose") or {}).get("crop"):
        from .compose import occupancy
        from .compose import presenter_source
        occ_cells, crop_wh = occupancy(proj, settings=settings), tuple(presenter_source(proj, settings)[1][2:4])
    by_id = {c["id"]: c for c in clips}
    from .config import load_brand
    kit = load_brand()
    ts, margin = kit.get("type-scale", {}), (kit.get("layout") or {}).get("margin-left", 96)
    floor, code_min = ts.get("label", 22), ts.get("code-min", 40)
    looked = set()                                        # rules L13/L14: each element is reported once
    from . import sync as S
    seen_el = {}                                          # rules S2/S3: what each element shows, and when (see fzv/sync.py)
    refined = []                                          # per clip: the exact first-seen times (sample.mjs refine)
    for m in manifest:
        c = by_id[m["id"]]
        times = [round(m["start"] + i * step, 2) for i in range(int((m["end"] - m["start"]) / step))]
        res = sample_cached(proj, m, [t - m["start"] for t in times])
        if m["layer"] == "plate":                          # hidden plate graphics stay silent during studio shots
            sfx += [q for q in res["sfx"] if kind_at(cuts, q[1]) != "studio" and m["start"] <= q[1] < m["end"]]
        else:
            sfx += [q for q in res["sfx"] if c["cut"][0] <= q[1] < c["cut"][1]]
        errors += [f"{m['id']}: {e}" for e in res["errors"]]
        last_content = None
        refined.append((m["id"], m["start"], res.get("refine") or {}))
        for fr in res["frames"]:
            t = round(m["start"] + fr["t"], 2)
            kind = kind_at(cuts, t)
            if m["layer"] == "plate" and kind == "studio":
                last_content = None                         # plate layer is hidden during studio shots; gaps restart after
                continue
            items = fr["items"]
            S.collect(seen_el, m["id"], m["layer"], t, items)
            cut_away = any(i["role"] == "cutaway" for i in items)
            blocks = [i for i in items if i["role"] in BLOCKS]
            content = [i for i in items if i["role"] in CONTENT]
            # L2: safe zone
            z = zones.get(kind)
            rects = (z.get("cells") or [z.get("bbox")]) if isinstance(z, dict) else ([z] if z else [])
            rects = rects + [box(i) for i in items if i["role"] == "presenter-frame"]
            # compose mode: where the keyed instructor really is, mapped through her live pose (box of #fz-presenter)
            frames_ = [box(i) for i in items if i["role"] == "presenter-frame"]
            for pb in (box(i) for i in items if i["role"] == "presenter"):
                sx, sy = (pb[2] - pb[0]) / crop_wh[0], (pb[3] - pb[1]) / crop_wh[1]
                cells = [[round(pb[0] + c[0] * sx), round(pb[1] + c[1] * sy), round(pb[0] + c[2] * sx), round(pb[1] + c[3] * sy)] for c in occ_cells]
                if frames_:                                   # boxed: only what the box shows of her counts
                    f0 = frames_[0]
                    cells = [[max(c[0], f0[0]), max(c[1], f0[1]), min(c[2], f0[2]), min(c[3], f0[3])] for c in cells if inter(c, f0)]
                rects = rects + cells
            if rects and not cut_away:
                for i in blocks + [i for i in items if i["role"] in ("text", "part")]:
                    hit = next((r for r in rects if r and inter(box(i), r)), None)
                    if hit:
                        flag("L2", t, f"{i['role']} at {box(i)} overlaps the instructor ({kind} zone {hit})"); break
            # L6: notes outside code and terminals
            codes = [box(i) for i in items if i["role"] in ("code", "term")]
            for n in (i for i in items if i["role"] == "note"):
                if any(inter(box(n), cb) for cb in codes):
                    flag("L6", t, f"note at {box(n)} overlaps a code card or terminal"); break
            # L12: one block never covers another (text that wraps longer than planned pushes a card into its neighbour)
            solid = [i["pb"] for i in items if i["role"] in ("block", "code", "term") and i.get("o", 1) > 0.6 and i.get("pb")]   # pb: what it paints
            for k, b1 in enumerate(solid):
                hit = next((b2 for b2 in solid[k + 1:] if overlap_share(b1, b2) > 0.04 and not contains(b1, b2) and not contains(b2, b1)), None)
                if hit:
                    flag("L12", t, f"block at {b1} overlaps the block at {hit}"); break
            # L12 for titles too: a header under a hero title or a card (the 6:27 title-over-header slipped through, 2026-11-05)
            heads = [i["pb"] for i in items if i["role"] == "title" and i.get("o", 1) > 0.6 and i.get("pb")]
            for k, h1 in enumerate(heads):
                hit = next((b2 for b2 in heads[k + 1:] + solid if overlap_share(h1, b2) > 0.04 and not contains(b2, h1)), None)
                if hit:
                    flag("L12", t, f"title at {h1} overlaps {hit}: one title at a time, clear of the cards"); break
            # L8: edges
            for i in blocks:
                bx = box(i)
                if bx[0] < 40 or bx[1] < 40 or bx[2] > 1880 or bx[3] > 1040:
                    flag("L8", t, f"{i['role']} at {bx} is within 40 px of the frame edge"); break
            # L10: clutter budget
            maxb, maxw = (clutter["studio_max_blocks"], clutter["studio_max_words"]) if m["layer"] == "studio" else (clutter["max_blocks"], clutter["max_words"])
            if len(blocks) > maxb:
                flag("L10", t, f"{len(blocks)} content blocks on screen (max {maxb})")
            words = sum(i.get("words", 0) for i in items if i["role"] in ("block", "note", "text", "part") and not i.get("nest"))
            if words > maxw:
                flag("L10", t, f"{words} words of text on screen (max {maxw})")
            lines = sum(i.get("lines", 0) for i in items if i["role"] == "code")
            if lines > clutter["max_code_lines"]:
                flag("L10", t, f"{lines} code lines on screen (max {clutter['max_code_lines']})")
            # L13: one type scale; nothing on screen smaller than the kit's label size, code not below code-min (registry items, 3D and
            # sketch draw their own text)
            for i in items:
                if i.get("fs") is None or i.get("tpl") in TYPE_EXEMPT or (m["id"], i["id"], "L13") in looked:
                    continue
                checks = [(i["fs"], floor, "text")] + ([(i["cfs"], code_min if i["role"] == "code" else 30, "code")] if i.get("cfs") else [])
                for size, low, what in checks:
                    if size < low:
                        looked.add((m["id"], i["id"], "L13"))
                        flag("L13", t, f"{i.get('tpl') or i['role']} {what} is {size} px (min {low}): use the kit's type scale (--fz-fs-*)")
                        break
            # L14: one left edge: every block starts at the margin, lines up with another block's left edge, or sits in a row with one
            al = [i for i in items if i["role"] in ("block", "code", "term", "text") and i.get("tpl") not in ALIGN_EXEMPT and i.get("o", 1) > 0.6]
            refs = al + [i for i in items if i.get("tpl") in ("picture", "prop", "note") and i["role"] in ("block", "note") and i.get("o", 1) > 0.6]
            for i in al:
                if (m["id"], i["id"], "L14") in looked:
                    continue
                others = [o for o in refs if o is not i]
                ok = (abs(i["x"] - margin) <= 6 or any(abs(i["x"] - o["x"]) <= 6 or abs(i["y"] - o["y"]) <= 12 or contains(box(o), box(i)) for o in others))
                if not ok:
                    looked.add((m["id"], i["id"], "L14"))
                    flag("L14", t, f"{i.get('tpl') or i['role']} at x {i['x']} lines up with nothing: start it at the left margin ({margin}) or align it with the block above or beside it")
            # T3: overflow
            if any(i.get("overflow") for i in items):
                flag("T3", t, "text overflows its card")
            # E3: captions only when subtitles are on
            if not settings["subtitles"]["enabled"] and any(i["role"] == "caption" for i in items):
                flag("E3", t, "captions shown but subtitles are off")
            # L4: plate shots never empty for long
            if m["layer"] == "plate":
                if content or any(i["role"] == "title" for i in items):     # a section title counts as something to see
                    last_content = t
                elif last_content is None:
                    last_content = t
                elif t - last_content > empty["max_gap_s"]:
                    flag("L4", t, f"nothing on screen for {t - last_content:.1f}s"); last_content = t
    # L4: every studio shot carries a studio-layer graphic; plate/corner time not covered by any section
    for c in clips:
        if c["layer"] == "studio" and not c.get("has_content"):
            flag("L4", c["start"], f"studio shot {c['cut'][0]:.2f}-{c['cut'][1]:.2f}s has no studio-layer graphic")
    covered = sorted((c["start"], c["end"]) for c in clips if c["layer"] == "plate")
    for cut in cuts:
        if cut["kind"] in ("corner", "plate") and cut["end"] - cut["start"] > empty["max_gap_s"]:
            inside = sum(max(0, min(b, cut["end"]) - max(a, cut["start"])) for a, b in covered)
            if inside < (cut["end"] - cut["start"]) * 0.9:
                flag("L4", cut["start"], f"{cut['kind']} shot {cut['start']:.2f}-{cut['end']:.2f}s is not covered by a section")
    # L3: cutaways
    cut_lens = []
    for sec in spec.get("sections") or []:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            if name == "cutaway" and isinstance(p.get("at"), (int, float)) and isinstance(p.get("until"), (int, float)):
                cut_lens.append((p["at"], p["until"] - p["at"]))
    lim = settings["cutaways"]
    for at, d in cut_lens:
        if d > lim["max_each_s"]:
            flag("L3", at, f"cutaway of {d:.1f}s (max {lim['max_each_s']}s)")
    total_dur = cuts[-1]["end"] if cuts else 1
    if sum(d for _, d in cut_lens) > total_dur * lim["max_total_pct"] / 100:
        flag("L3", 0, f"cutaways total {sum(d for _, d in cut_lens):.1f}s (max {lim['max_total_pct']}% of runtime)")
    # L11: the background stays the brand plate: no dark scenes or full-frame backdrops unless the prompt asks (overrides: {L11: why})
    for t, name in background_changes(spec):
        flag("L11", t, f"`{name}` changes the whole background; keep the brand plate and make the moment big with the graphics instead")
    # L1: nothing that touches the instructor in overlay mode
    if spec.get("mode", "overlay") == "overlay":
        for c in clips:
            for s in c["scenes"]:
                if s["template"] in R.get("L1", {}).get("forbidden_in_overlay", []):
                    flag("L1", c["start"], f"template {s['template']} is not allowed in overlay mode")
    # E7: output on screen is the program's real output; E8: a recording kept as reference is never shown
    use = spec.get("recording_use") or settings.get("recordings", {}).get("use", "show")
    for sec in spec.get("sections") or []:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            if not isinstance(p, dict):
                continue
            if name == "terminal" and not p.get("exec") and not p.get("manual") and (p.get("lines") or p.get("chips") or p.get("input")):
                flag("E7", p.get("at") or 0, f"terminal {p.get('id', '')} output is written by hand; use `exec` so it is the program's real output (or give `manual: <reason>`)")
            cr = p.get("corrections_result") if name == "code-card" else None
            if cr and cr.get("changes"):
                if settings.get("recordings", {}).get("corrections") == "exact":
                    flag("E9", p.get("at") or 0, f"code card {p.get('id')} differs from the recording but the prompt asks for the code exactly as recorded")
                elif cr.get("output_same") is False and not p.get("logic_fix"):
                    flag("E9", p.get("at") or 0, f"code card {p.get('id')}: the correction changes the program's output; say why in `logic_fix:` (it goes to 'to confirm') or keep the recorded code")
            if name == "recording-window" and use == "reference":
                flag("E8", p.get("at") or 0, "the prompt keeps the recording as reference only; rebuild it with code-card + terminal exec instead of recording-window")
    # V1 / V2: show the process, not only words (design §7.3)
    vis_cfg = settings.get("visuals", {})
    max_text = vis_cfg.get("max_text_only_s", 15.0)
    for sec in spec.get("sections") or []:
        lo, hi = sec["range"]
        names = {next(iter(s)) for s in sec.get("scenes") or []}
        if hi - lo >= vis_cfg.get("min_section_s", 30.0) and not names - TEXT_ONLY:
            flag("V1", lo, f"section {sec.get('id')} ({hi - lo:.0f}s) has no animated explanation: show what is described (data-flow, process-flow, code, diagram, props…)")
        hidden = [(c["start"], c["end"]) for c in cuts if c["kind"] == "studio"] + list(quiet)
        for a, b in text_only_stretches(sec, hi, hidden):
            if b - a > max_text:
                flag("V2", a, f"{b - a:.0f}s of text-only screen in section {sec.get('id')} ({a:.1f}–{b:.1f}s, max {max_text:.0f}s): animate the process being explained")
    # V3 (advice): concept moments without a matching animation
    from .concepts import blocked_templates, covered, is_animation, repeats, video_moments
    blocked = blocked_templates(settings)
    advice = [{"rule": "V3", "t": m["t"], "msg": f"“{m['phrase']}” is said here; show it with {' / '.join(m['templates'])} ({m['show']})"}
              for m in video_moments(proj, settings) if m["templates"] and not covered(m, spec)]
    # V5 (advice): variety; the same animation twice in a row, or one animation carrying too much of the video
    from .plan import catalogue
    from .spec import scene_span
    fam = {n: m.get("family") for n, m in catalogue().items()}
    seq = []
    for sec in spec.get("sections") or []:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            key = f"hf:{p.get('item')}" if name == "hf" and isinstance(p, dict) else name
            at, _ = scene_span(p, sec["range"][1])
            if at is not None and is_animation(key, fam):
                seq.append((at, key, f"{at:.1f}s"))
    advice += [{"rule": "V5", "t": t, "msg": msg} for t, msg in repeats(sorted(seq), vis_cfg.get("max_repeat_share", 0.2))]
    # S1: on-request styles (3D, sketch) only when the prompt asks for them
    for sec in (spec.get("sections") or []) + [{"scenes": spec.get("studio") or []}]:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            if name in blocked:
                flag("S1", p.get("at") if isinstance(p, dict) and isinstance(p.get("at"), (int, float)) else 0,
                     f"{name} is used only when the prompt asks for its style (3D, sketch); swap it for a 2D template or add the request to the prompt")
    # V4: every beat of the beat sheet is built as approved (design §9f)
    if proj.p("beats.yaml").exists():
        from . import beats as B
        for b in B.load(proj.p("beats.yaml")).get("beats") or []:
            if not B.filled(b) or not isinstance(b.get("start"), (int, float)):
                continue
            for want in [str(t) for t in b.get("templates") or []]:
                if not scene_in(spec, want, b["start"], b["end"]):
                    flag("V4", b["start"], f"beat {b['id']} ({B.span(b)}) was approved with {want}, but edit.yaml has no {want} there")
    # L5: compose mode, instructor moves at most twice
    if spec.get("mode") == "compose":
        poses = (spec.get("presenter") or {}).get("poses") or []
        if len(poses) - 1 > 2:
            flag("L5", 0, f"{len(poses) - 1} presenter moves (max 2: intro focus, then one fixed position)")
    for (clip_id, start, ref) in refined:
        S.refine(seen_el, clip_id, start, ref)
    # S2-S5: in step with her words (fzv/sync.py)
    from .anchors import Transcript
    tx_all = Transcript(proj.p("transcript.jsonl"))
    s_prob, s_adv, s_sum = S.check(seen_el, spec, tx_all, cuts, quiet, settings.get("sync", {}))
    s_adv += S.disagreements((spec.get("_anchoring") or {}).get("anchors") or [], tx_all)   # S6: the two transcripts disagree
    for p in s_prob:
        flag(p["rule"], p["t"], p["msg"])
    advice += s_adv
    for e in errors:
        problems.append({"rule": "script", "t": 0, "msg": e})
    # collapse repeats of the same rule within 2 s
    out, seen = [], {}
    for p in sorted(problems, key=lambda p: (p["rule"], p["t"])):
        k = (p["rule"], p["msg"].split(" at ")[0][:40])
        if k in seen and p["t"] - seen[k] < 2:
            continue
        seen[k] = p["t"]
        out.append(p)
    report = {"ok": not out, "problems": out, "advice": advice, "sfx_cues": len(sfx), "sync": s_sum}
    (proj.edit / "validate.json").write_text(json.dumps(report, indent=1))
    (proj.edit / "audio").mkdir(exist_ok=True)
    (proj.edit / "audio" / "cues.json").write_text(json.dumps(sorted(sfx, key=lambda x: x[1])))
    log(f"validate: {'OK' if not out else str(len(out)) + ' problem(s)'}; {len(sfx)} SFX cues")
    for p in out[:40]:
        log(f"  [{p['rule']}] {p['t']:.2f}s  {p['msg']}")
    log(f"validate: sync: {s_sum['early']} early, {s_sum['late']} late, {s_sum['holds']} hold(s) (longest {s_sum['longest_hold_s']}s), "
        f"{s_sum['repeats_without_reaction']} repeat(s) with no reaction; {s_sum['times_on_words']} times on her words, {s_sum['times_typed']} typed in seconds")
    for rule, what in (("V3", "concept moment(s) without a matching animation"), ("V5", "variety note(s): an animation repeated"),
                       ("S3", "repeat(s) with nothing reacting"), ("S6", "time(s) where the English and Telugu transcripts disagree")):
        adv = [p for p in advice if p["rule"] == rule]
        if adv:
            log(f"validate: {len(adv)} {what} (advice, rule {rule}):")
            for p in adv[:20]:
                log(f"  [{rule}] {p['t']:.2f}s  {p['msg']}")
    return report
