"""Concept moments (rule V3): where the instructor names something the screen should show, from global/concepts.yaml.

One collection for every course, technical and non-technical; Claude uses the moments that fit the lesson (design §7.3). Variety
(rule V5): the suggested templates rotate so the same concept or template is not shown the same way twice in a row, and `repeats`
flags an animation used back to back or too often.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from .config import GLOBAL, load_yaml

GAP_S = 45.0        # a concept is listed again only this long after its last moment (a concept's own `gap` overrides it)
SHOW_FAMILIES = {"explainer", "diagram", "data", "kinetic", "3d", "sketch", "props", "registry"}   # V5 counts these
FRAMES = {"sketch-board", "sketch-mark", "scene", "cutaway"}                                       # …but not these


def norm(w: str) -> str:
    """One word as the matcher sees it: lower case, letters and digits (+ and commas inside numbers kept), plurals folded
    (components → component, classes → class, queries → query), so a phrase matches either form."""
    w = re.sub(r"[^a-z0-9,+]", "", w.lower()).strip(",")
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith(("sses", "ches", "shes", "xes")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def tokens(text) -> list[str]:
    return [t for t in (norm(x) for x in re.split(r"[\s/-]+", str(text).strip())) if t]


def lexicon() -> list[dict]:
    f = GLOBAL / "concepts.yaml"
    return (load_yaml(f).get("concepts") or []) if f.exists() else []


def _words(transcript: Path | None) -> list[tuple[str, float]]:
    out = []
    if transcript and transcript.exists():
        for line in transcript.read_text(encoding="utf-8").splitlines():
            if line.strip():
                for w in json.loads(line).get("words") or []:
                    out += [(t, w["s"]) for t in tokens(w["w"])]
    return out


def _find(words: list[tuple[str, float]], concepts: list[dict]) -> list[tuple[int, int, dict, str]]:
    """(first word, end, concept, phrase) for every phrase occurrence; where phrases overlap the longest wins ("type conversion"
    over "conversion", "http request" over "request")."""
    toks, at = [w for w, _ in words], {}
    for i, w in enumerate(toks):
        at.setdefault(w, []).append(i)
    hits = []
    for c in concepts:
        for ph in c.get("phrases") or []:
            pt = tokens(ph)
            hits += [(i, i + len(pt), c, str(ph).strip()) for i in at.get(pt[0] if pt else "", []) if toks[i:i + len(pt)] == pt]
    taken, kept = set(), []
    for h in sorted(hits, key=lambda h: (h[0] - h[1], h[0])):
        span = set(range(h[0], h[1]))
        if not span & taken:
            taken |= span
            kept.append(h)
    return sorted(kept, key=lambda h: h[0])


def moments(transcript: Path, gap_s: float = GAP_S) -> list[dict]:
    """[{id, t, phrase, templates, show}] in time order; a concept comes back only after its `gap` (default GAP_S)."""
    words = _words(transcript)
    out, last = [], {}
    for i, _, c, ph in _find(words, lexicon()):
        t = words[i][1]
        if t - last.get(c["id"], -1e9) >= float(c.get("gap", gap_s)):
            out.append({"id": c["id"], "t": round(t, 2), "phrase": ph, "templates": list(c.get("templates") or []), "show": c.get("show", "")})
            last[c["id"]] = t
    return out


def video_moments(proj, settings: dict | None = None) -> list[dict]:
    """The video's concept moments, each with the templates its styles allow, in the order to try them (`vary`)."""
    s = settings or proj.settings()
    blocked = blocked_templates(s)
    ms = moments(proj.p("transcript.jsonl"))
    return vary([dict(m, templates=[t for t in m["templates"] if t not in blocked]) for m in ms])


def vary(ms: list[dict], recent: int = 3) -> list[dict]:
    """Rule V5 on the suggestions: the nth time a concept comes back it leads with its nth template, and a template suggested
    first for one of the last `recent` moments moves to the back of the list."""
    out, seen, lead = [], Counter(), []
    for m in ms:
        ts = list(m["templates"])
        if ts:
            k = seen[m["id"]] % len(ts)
            ts = ts[k:] + ts[:k]
            ts.sort(key=lambda t: t in lead[-recent:])
            lead.append(ts[0])
        seen[m["id"]] += 1
        out.append(dict(m, templates=ts))
    return out


def is_animation(name: str, family: dict) -> bool:
    """Counts for the variety check (V5): explainer, diagram, data, kinetic, props, 3D, sketch and registry animations. Code,
    core and presenter templates (code cards, headers, the corner box…) repeat by design."""
    base = "hf" if name.startswith("hf:") else name
    return base not in FRAMES and family.get(base) in SHOW_FAMILIES


def repeats(seq: list[tuple[float, str, str]], max_share: float = 0.2, min_count: int = 4) -> list[tuple[float, str]]:
    """Rule V5: [(t, message)] where an animation follows itself, or carries more than `max_share` of the video's animations
    (and at least `min_count`). `seq` = [(time, template or hf:<item>, where)] in time order; `where` names it in messages."""
    out = [(t1, f"{w1}: {b} again right after {w0}; show it another way (the concept's next template, a diagram, props)")
           for (_, a, w0), (t1, b, w1) in zip(seq, seq[1:]) if a == b]
    for name, k in Counter(n for _, n, _ in seq).items():
        if k >= min_count and k > max_share * len(seq):
            at = [(t, w) for t, n, w in seq if n == name]
            out.append((at[0][0], f"{name} is {k} of the {len(seq)} animations ({', '.join(w for _, w in at[:8])}); show some of them another way"))
    return sorted(out)


def covered(m: dict, spec: dict, before: float = 3.0, after: float = 10.0) -> bool:
    """A matching template (or hf:<item>) is on screen around the moment."""
    from .validate import scene_in
    return any(scene_in(spec, t, m["t"] - before, m["t"] + after) for t in m["templates"])


def lint() -> list[str]:
    """Problems in the collection: unknown templates, repeated ids, a phrase in two concepts, a concept with no 2D choice."""
    from .plan import catalogue
    from .registry import manifest
    cat, items = catalogue(), {x["name"] for x in manifest()}
    on_request = {n for n, m in cat.items() if m.get("family") in ("3d", "sketch")}
    out, ids, phrases = [], Counter(), {}
    for c in lexicon():
        cid, ts = c.get("id"), [str(t) for t in c.get("templates") or []]
        ids[cid] += 1
        if not c.get("phrases") or not c.get("show"):
            out.append(f"{cid}: needs phrases and show")
        for t in ts:
            if not (t[3:] in items if t.startswith("hf:") else t in cat) or t in ("scene", "cutaway", "hf"):
                out.append(f"{cid}: unknown or not allowed template '{t}'")
        if len([t for t in ts if t not in on_request]) < 2:
            out.append(f"{cid}: give at least two 2D templates, so a concept that comes back can be shown another way")
        for ph in c.get("phrases") or []:
            k = tuple(tokens(ph))
            if k in phrases:
                out.append(f"{cid}: phrase “{ph}” " + ("is listed twice (plurals and hyphens match anyway)" if phrases[k] == cid else f"is already in {phrases[k]}"))
            phrases.setdefault(k, cid)
    out += [f"concept id '{i}' is used {n} times" for i, n in ids.items() if n > 1]
    return out


def blocked_templates(settings: dict) -> set[str]:
    """Templates of on-request style families (sketch, 3d) that this video's prompt does not ask for: never used."""
    from .plan import catalogue
    st = settings.get("styles") or {}
    off = set(st.get("on_request") or []) - set(st.get("requested") or [])
    return {n for n, m in catalogue().items() if m.get("family") in off}
