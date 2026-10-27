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
             "name-card", "studio-tag", "captions", "contrast", "big-word", "callouts", "checklist", "bug", "scene", "presenter"}


def text_only_stretches(sec: dict, end_default: float) -> list[tuple[float, float]]:
    """Stretches of a section where only text templates are on screen."""
    lo, hi = sec["range"]
    vis = []
    for s in sec.get("scenes") or []:
        (name, p), = s.items()
        if name in TEXT_ONLY or not isinstance(p, dict) or not isinstance(p.get("at"), (int, float)):
            continue
        vis.append((max(lo, p["at"]), min(hi, p["until"] if isinstance(p.get("until"), (int, float)) else hi)))
    gaps, t = [], lo
    for a, b in sorted(vis):
        if a > t:
            gaps.append((t, a))
        t = max(t, b)
    if t < hi:
        gaps.append((t, hi))
    return gaps
CONTENT = BLOCKS | {"text", "cutaway", "part"}


def scene_in(spec: dict, want: str, lo: float, hi: float) -> bool:
    """A scene of template `want` (or `hf:<item>`) is on screen at some point between lo and hi (1 s tolerance)."""
    item = want[3:] if want.startswith("hf:") else None
    name = "hf" if item else want
    groups = [(s, sec["range"][1]) for sec in spec.get("sections") or [] for s in sec.get("scenes") or []]
    groups += [(s, None) for s in spec.get("studio") or []]
    for s, end in groups:
        (n, p), = s.items()
        if n != name or not isinstance(p, dict) or not isinstance(p.get("at"), (int, float)) or (item and p.get("item") != item):
            continue
        until = p["until"] if isinstance(p.get("until"), (int, float)) else (end if end is not None else p["at"] + 5)
        if p["at"] <= hi + 1 and until >= lo - 1:
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
    key = f"{m['id']}_{m.get('hash', 'nohash')}_{len(local_times)}_{local_times[0] if local_times else 0:.2f}.json"
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


def inter(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def box(it):
    return [it["x"], it["y"], it["x"] + it["w"], it["y"] + it["h"]]


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
        occ_cells, crop_wh = occupancy(proj), tuple(proj.load()["compose"]["crop"][2:4])
    by_id = {c["id"]: c for c in clips}
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
        for fr in res["frames"]:
            t = round(m["start"] + fr["t"], 2)
            kind = kind_at(cuts, t)
            if m["layer"] == "plate" and kind == "studio":
                last_content = None                         # plate layer is hidden during studio shots; gaps restart after
                continue
            items = fr["items"]
            cut_away = any(i["role"] == "cutaway" for i in items)
            blocks = [i for i in items if i["role"] in BLOCKS]
            content = [i for i in items if i["role"] in CONTENT]
            # L2: safe zone
            z = zones.get(kind)
            rects = (z.get("cells") or [z.get("bbox")]) if isinstance(z, dict) else ([z] if z else [])
            rects = rects + [box(i) for i in items if i["role"] == "presenter-frame"]
            # compose mode: where the keyed instructor really is, mapped through her live pose (box of #fz-presenter)
            for pb in (box(i) for i in items if i["role"] == "presenter"):
                sx, sy = (pb[2] - pb[0]) / crop_wh[0], (pb[3] - pb[1]) / crop_wh[1]
                rects = rects + [[round(pb[0] + c[0] * sx), round(pb[1] + c[1] * sy), round(pb[0] + c[2] * sx), round(pb[1] + c[3] * sy)] for c in occ_cells]
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
            # L8: edges
            for i in blocks:
                bx = box(i)
                if bx[0] < 40 or bx[1] < 40 or bx[2] > 1880 or bx[3] > 1040:
                    flag("L8", t, f"{i['role']} at {bx} is within 40 px of the frame edge"); break
            # L10: clutter budget
            maxb, maxw = (clutter["studio_max_blocks"], clutter["studio_max_words"]) if m["layer"] == "studio" else (clutter["max_blocks"], clutter["max_words"])
            if len(blocks) > maxb:
                flag("L10", t, f"{len(blocks)} content blocks on screen (max {maxb})")
            words = sum(i.get("words", 0) for i in items if i["role"] in ("block", "note", "text", "part"))
            if words > maxw:
                flag("L10", t, f"{words} words of text on screen (max {maxw})")
            lines = sum(i.get("lines", 0) for i in items if i["role"] == "code")
            if lines > clutter["max_code_lines"]:
                flag("L10", t, f"{lines} code lines on screen (max {clutter['max_code_lines']})")
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
        for a, b in text_only_stretches(sec, hi):
            if b - a > max_text and not any(q0 <= a and b <= q1 + 0.5 for q0, q1 in quiet):
                flag("V2", a, f"{b - a:.0f}s of text-only screen in section {sec.get('id')} ({a:.1f}–{b:.1f}s, max {max_text:.0f}s): animate the process being explained")
    # V3 (advice): concept moments without a matching animation
    from .concepts import covered, moments
    advice = [{"rule": "V3", "t": m["t"], "msg": f"“{m['phrase']}” is said here; show it with {' / '.join(m['templates'])} ({m['show']})"}
              for m in moments(proj.p("transcript.jsonl")) if not covered(m, spec)]
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
    report = {"ok": not out, "problems": out, "advice": advice, "sfx_cues": len(sfx)}
    (proj.edit / "validate.json").write_text(json.dumps(report, indent=1))
    (proj.edit / "audio").mkdir(exist_ok=True)
    (proj.edit / "audio" / "cues.json").write_text(json.dumps(sorted(sfx, key=lambda x: x[1])))
    log(f"validate: {'OK' if not out else str(len(out)) + ' problem(s)'}; {len(sfx)} SFX cues")
    for p in out[:40]:
        log(f"  [{p['rule']}] {p['t']:.2f}s  {p['msg']}")
    if advice:
        log(f"validate: {len(advice)} concept moment(s) without a matching animation (advice, rule V3):")
        for p in advice[:20]:
            log(f"  [V3] {p['t']:.2f}s  {p['msg']}")
    return report
