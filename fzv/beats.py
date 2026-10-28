"""Beat sheet (design §9f): the edit planned one idea at a time and approved by the editor before edit.yaml is written.

  edit/beats.yaml      one row per beat (an idea the instructor explains, usually 8–20 s). `fzv plan` drafts the rows from the
                       transcript's pauses, the shot changes and the concept moments; Claude fills `idea`, `show`, `templates` and
                       `sync`; the editor changes rows in plain words and approves (`fzv approve <folder> beats`).
  edit/beat_sheet.md   the same as a readable table (rewritten by every `fzv beats`)

Approvals (beat sheet, storyboard) are kept in project.yaml with a fingerprint of what was approved, so any later change needs a new
approval. `fzv build` waits for an approved beat sheet and `fzv render` for an approved storyboard (settings `review.*`).
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

import yaml

from .anchors import Transcript

HEADER = """\
# Beat sheet: one row per idea the instructor explains. Planned before edit.yaml and approved by the editor (fzv approve).
#   start, end  seconds of the raw cut; beats follow each other with no gaps and cover the whole video
#   shot        the shot kinds in this stretch (plate, corner, studio)
#   says        what the instructor says: the transcript; Claude rewrites it as a clean English gist when it is garbled
#   concepts    concept moments in this stretch: time, phrase -> templates that show it
#   idea        the idea in one plain sentence                                    <- Claude fills
#   show        what appears on screen, in plain words for the editor            <- Claude fills
#   templates   the templates that build it (catalogue names; hf:<item> for registry animations)
#   sync        the words each step lands on, in order: "@phrase" anchors (or seconds)
#   key         optional: when the storyboard frame is taken ("@phrase" or seconds; default just after the last sync word)
#   notes       anything to confirm (illustrative details, names heard indistinctly)
#   feedback    the editor's requests for this beat, in their words, and what was done
"""


def mmss(t: float) -> str:
    t = max(0.0, float(t))
    return f"{int(t // 60)}:{int(t % 60):02d}"


def span(b: dict) -> str:
    return f"{mmss(b['start'])}–{mmss(b['end'])}"


def kind_at(cuts: list[dict], t: float) -> str:
    for c in cuts:
        if c["start"] <= t < c["end"]:
            return c["kind"]
    return cuts[-1]["kind"] if cuts else "plate"


# ---------------------------------------------------------------- draft
def units(transcript: Path, cuts: list[dict]) -> list[dict]:
    """Transcript segments (split at pauses by the transcriber), cut in two where a shot change falls inside one."""
    bounds = [c["start"] for c in cuts[1:]]
    out = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        ws = [w for w in r.get("words") or [] if str(w.get("w", "")).strip()]
        if not ws:
            continue
        cur = []
        for w in ws:
            if cur and any(cur[-1]["s"] < b <= w["s"] for b in bounds):
                out.append(cur)
                cur = []
            cur.append(w)
        out.append(cur)
    res = []
    for i, u in enumerate(out):
        nxt = out[i + 1][0]["s"] if i + 1 < len(out) else u[-1]["s"] + 0.6
        res.append({"start": float(u[0]["s"]), "end": float(min(nxt, u[-1]["s"] + 0.6)), "text": " ".join(str(w["w"]).strip() for w in u)})
    return res


def draft(transcript: Path, cuts: list[dict], duration: float, moments: list[dict],
          min_s: float = 8.0, target_s: float = 14.0, max_s: float = 20.0, min_shot_s: float = 4.0) -> list[dict]:
    """Rows of a new beat sheet. A beat closes at a pause once it is `target_s` long, before a concept moment once it is `min_s`
    long, and never runs past `max_s` when it can close earlier. Shot changes always start a new beat unless a side is tiny."""
    us = units(transcript, cuts) if transcript.exists() else []
    hard = [c["start"] for i, c in enumerate(cuts) if i and c["end"] - c["start"] >= min_shot_s and cuts[i - 1]["end"] - cuts[i - 1]["start"] >= min_shot_s]
    groups, cur = [], []
    for u in us:
        if cur:
            length = u["start"] - cur[0]["start"]
            crosses = any(cur[-1]["start"] < b <= u["start"] + 1e-6 for b in hard)
            concept = any(u["start"] - 0.5 <= m["t"] < u["end"] for m in moments)
            if crosses or length >= target_s or (length >= min_s and (concept or u["end"] - cur[0]["start"] > max_s)):
                groups.append(cur)
                cur = []
        cur.append(u)
    if cur:
        groups.append(cur)
    apart = lambda g1, g2: any(g1[-1]["start"] < b <= g2[0]["start"] + 1e-6 for b in hard)
    i = 0
    while i < len(groups) and len(groups) > 1:                 # a tiny beat ("So,") joins a neighbour in the same shot
        nxt = groups[i + 1][0]["start"] if i + 1 < len(groups) else duration
        if nxt - groups[i][0]["start"] < min_s / 2:
            if i > 0 and not apart(groups[i - 1], groups[i]):
                groups[i - 1] += groups.pop(i)
                continue
            if i + 1 < len(groups) and not apart(groups[i], groups[i + 1]):
                groups[i] += groups.pop(i + 1)
                continue
        i += 1
    if not groups:
        return [row(1, 0.0, duration, cuts, "", moments)]
    starts = [0.0]
    for prev, g in zip(groups, groups[1:]):
        cut = next((b for b in hard if prev[-1]["start"] < b <= g[0]["start"] + 1e-6), None)
        gap = max(0.0, g[0]["start"] - prev[-1]["end"])
        starts.append(round(cut if cut is not None else g[0]["start"] - min(0.3, gap / 2), 2))
    ends = starts[1:] + [round(duration, 2)]
    return [row(i + 1, s, e, cuts, " ".join(u["text"] for u in g), moments) for i, (s, e, g) in enumerate(zip(starts, ends, groups))]


def row(n: int, start: float, end: float, cuts: list[dict], says: str, moments: list[dict]) -> dict:
    kinds = []
    for c in cuts:
        if c["end"] > start and c["start"] < end and c["kind"] not in kinds:
            kinds.append(c["kind"])
    return {"id": f"b{n:02d}", "start": round(start, 2), "end": round(end, 2), "shot": ", ".join(kinds) or "plate",
            "says": re.sub(r"\s+", " ", says).strip(),
            "concepts": [f"{mmss(m['t'])} “{m['phrase']}” -> {' / '.join(m['templates'])}" for m in moments if start <= m["t"] < end],
            "idea": "", "show": "", "templates": [], "sync": [], "notes": ""}


def write(path: Path, doc: dict) -> None:
    body = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=130)
    path.write_text(HEADER + "\n" + body, encoding="utf-8")


def load(path: Path) -> dict:
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}


# ---------------------------------------------------------------- check
def resolve_time(v, b: dict, tx: Transcript, lo_pad: float = 1.5, hi_pad: float = 1.5):
    """A sync / key value inside its beat: seconds, or "@phrase" / "@phrase#2" (2nd time it is said in this beat)."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s.startswith("@"):
        return None
    phrase, occ = s[1:], 1
    m = re.match(r"^(.*)#(\d+)$", phrase)
    if m:
        phrase, occ = m.group(1), int(m.group(2))
    return tx.find(phrase, after=b["start"] - lo_pad, before=b["end"] + hi_pad, occurrence=occ)


def key_time(b: dict, sync_times: list[float], tx: Transcript) -> float:
    """When the storyboard frame of a beat is taken: its `key`, else 1.5 s after the last sync word, kept inside the beat."""
    lo, hi = b["start"] + 0.5, max(b["start"] + 0.5, b["end"] - 0.3)
    if b.get("key") is not None:
        k = resolve_time(b["key"], b, tx)
        if k is not None:
            return round(min(hi, max(lo, k)), 2)
    ts = [t for t in sync_times if t is not None]
    t = (max(ts) + 1.5) if ts else (b["start"] + b["end"]) / 2
    return round(min(hi, max(lo, t)), 2)


def filled(b: dict) -> bool:
    return all(str(b.get(k) or "").strip() for k in ("idea", "show"))


def check(doc: dict, tx: Transcript, duration: float, templates: set[str], registry: set[str], moments: list[dict],
          text_only: set[str], max_text_only_s: float = 15.0) -> tuple[list[str], list[str], dict]:
    """(errors, warnings, {beat id: {"sync": [t…], "key": t}})."""
    errs, warns, res = [], [], {}
    beats = doc.get("beats") or []
    if not beats:
        return ["the beat sheet has no beats"], [], {}
    ids = [str(b.get("id")) for b in beats]
    for d in sorted({i for i in ids if ids.count(i) > 1}):
        errs.append(f"beat id {d} is used twice")
    for b in beats:
        if not isinstance(b.get("start"), (int, float)) or not isinstance(b.get("end"), (int, float)) or b["end"] <= b["start"]:
            errs.append(f"{b.get('id')}: start and end must be seconds with end after start")
    if errs:
        return errs, warns, res
    beats = sorted(beats, key=lambda b: b["start"])
    if beats[0]["start"] > 0.6:
        errs.append(f"nothing covers 0:00–{mmss(beats[0]['start'])}: start the first beat at 0")
    if beats[-1]["end"] < duration - 0.6:
        errs.append(f"nothing covers {mmss(beats[-1]['end'])}–{mmss(duration)}: end the last beat at {duration:.2f}")
    for a, b in zip(beats, beats[1:]):
        if abs(b["start"] - a["end"]) > 0.6:
            errs.append(f"{a['id']} ends at {a['end']} but {b['id']} starts at {b['start']}: beats must follow each other (no gaps or overlaps)")
    for b in beats:
        bid, n = b["id"], len(b.get("templates") or [])
        if not filled(b):
            errs.append(f"{bid} ({span(b)}): fill `idea` and `show`")
        names = []
        for t in b.get("templates") or []:
            t = str(t).strip()
            if t.startswith("hf:"):
                if t[3:] not in registry:
                    errs.append(f"{bid}: no registry animation '{t[3:]}' installed (fzv registry list / add)")
                names.append("hf")
            elif t == "hf":
                errs.append(f"{bid}: say which registry animation, as hf:<item>")
            elif t not in templates:
                errs.append(f"{bid}: unknown template '{t}'")
            else:
                names.append(t)
        times = []
        for v in b.get("sync") or []:
            t = resolve_time(v, b, tx)
            if t is None:
                errs.append(f"{bid}: sync word {v!r} not found between {mmss(b['start'] - 1.5)} and {mmss(b['end'] + 1.5)}")
            times.append(t)
        if b.get("key") is not None and resolve_time(b["key"], b, tx) is None:
            errs.append(f"{bid}: key {b['key']!r} not found in the beat")
        res[bid] = {"sync": times, "key": key_time(b, times, tx)}
        if filled(b) and not n:
            warns.append(f"{bid}: no templates; say what stays on screen (never a plain-instructor stretch, rule L4)")
        if filled(b) and n and not set(names) - text_only and b["end"] - b["start"] > max_text_only_s:
            warns.append(f"{bid} ({b['end'] - b['start']:.0f}s): words only; animate what is explained (rules V1/V2)")
        if filled(b) and n and not b.get("sync"):
            warns.append(f"{bid}: no sync words; anchor each step on the word that names it")
        if b["end"] - b["start"] > 25:
            warns.append(f"{bid} is {b['end'] - b['start']:.0f}s long; split it if it holds more than one idea")
        for m in moments if filled(b) else []:
            if b["start"] <= m["t"] < b["end"] and not set(m["templates"]) & set(names):
                warns.append(f"{bid}: “{m['phrase']}” at {mmss(m['t'])} is a concept moment; {' / '.join(m['templates'])} would show it (or say why not in notes)")
    return errs, warns, res


def markdown(doc: dict, title: str, status: str) -> str:
    esc = lambda s: str(s or "").replace("|", "\\|").replace("\n", " ").strip()
    cut = lambda s, n: s if len(s) <= n else s[: n - 1].rstrip() + "…"
    lines = [f"# Beat sheet: {title}", "", f"**Status:** {status}", "",
             "| # | Time | Shot | Instructor says | The idea | What we show | On the words | Notes |", "|---|---|---|---|---|---|---|---|"]
    for i, b in enumerate(doc.get("beats") or [], 1):
        sync = ", ".join(str(s).lstrip("@") for s in b.get("sync") or [])
        notes = "; ".join(x for x in (esc(b.get("notes")), esc(b.get("feedback"))) if x)
        lines.append(f"| {i} | {span(b)} | {esc(b.get('shot'))} | {cut(esc(b.get('says')), 180)} | {esc(b.get('idea'))} | {esc(b.get('show'))} | {esc(sync)} | {notes} |")
    return "\n".join(lines) + "\n"


def expand_refs(request: str, doc: dict) -> str:
    """'beat 7: use a car' / 'b07 use a car' -> '1:23 use a car' (the beat's start), so `fzv revise` can map it to scenes."""
    beats = doc.get("beats") or []
    by_id = {str(b.get("id")): b for b in beats}

    def sub(m):
        n = int(m.group(1) or m.group(2))
        b = by_id.get(f"b{n:02d}") or (beats[n - 1] if 0 < n <= len(beats) else None)
        if not b:
            return m.group(0)
        t = b["start"] + 0.5
        return f"{int(t // 60)}:{t % 60:04.1f} "
    return re.sub(r"\bbeat\s*#?(\d{1,3})\b\s*:?\s*|\bb(\d{2,3})\b\s*:?\s*", sub, request, flags=re.I)


# ---------------------------------------------------------------- approvals
def beats_fingerprint(doc: dict) -> str:
    return hashlib.sha1(json.dumps(doc.get("beats") or [], sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:12]


def build_signature(proj) -> str | None:
    f = proj.edit / "built" / "clips.json"
    if not f.exists():
        return None
    man = json.loads(f.read_text())
    return hashlib.sha1("|".join(sorted(f"{m['id']}:{m.get('hash', '')}" for m in man)).encode()).hexdigest()[:12]


def approval(proj, what: str) -> dict | None:
    return (proj.load().get("approvals") or {}).get(what)


def record_approval(proj, what: str, fingerprint: str, note: str = "") -> dict:
    d = proj.load()
    a = {"fingerprint": fingerprint, "at": time.strftime("%Y-%m-%d %H:%M:%S"), "note": note}
    d.setdefault("approvals", {})[what] = a
    proj.save(d)
    f = proj.edit / "approvals.md"
    head = "" if f.exists() else "# Approvals\n\nEvery beat-sheet and storyboard approval, with the editor's words.\n\n"
    with open(f, "a", encoding="utf-8") as fh:
        fh.write(head + f"- {a['at']}  **{what}** approved ({fingerprint})" + (f": {note}" if note else "") + "\n")
    return a


def beats_state(proj) -> str:
    """missing | draft (rows not filled) | proposed (filled, waiting for the editor) | approved | changed (edited after approval)."""
    f = proj.p("beats.yaml")
    if not f.exists():
        return "missing"
    doc = load(f)
    if not doc.get("beats") or not all(filled(b) for b in doc["beats"]):
        return "draft"
    a = approval(proj, "beats")
    if not a:
        return "proposed"
    return "approved" if a["fingerprint"] == beats_fingerprint(doc) else "changed"


def storyboard_state(proj) -> str:
    """missing | stale (built again since) | ready (waiting for the editor) | approved."""
    f = proj.edit / "review" / "storyboard.json"
    sig = build_signature(proj)
    if not f.exists() or not sig:
        return "missing"
    if json.loads(f.read_text()).get("build") != sig:
        return "stale"
    a = approval(proj, "storyboard")
    return "approved" if a and a["fingerprint"] == sig else "ready"


def gate_mode(settings: dict, what: str) -> str:
    return str((settings.get("review") or {}).get(what, "required")).lower()


def legacy(proj) -> bool:
    """Edits built before beat sheets existed (no beats.yaml) keep working without the review gates."""
    return not proj.p("beats.yaml").exists() and (proj.edit / "built" / "clips.json").exists()


def gate_build(proj, settings: dict) -> str | None:
    """None when building may go ahead, else the reason (plain words, for the editor)."""
    if gate_mode(settings, "beats") == "off" or legacy(proj):
        return None
    st = beats_state(proj)
    if st == "approved":
        return None
    return {"missing": "there is no beat sheet yet: run `fzv plan` (it drafts edit/beats.yaml), fill it and show it to the editor",
            "draft": "the beat sheet isn't filled in yet (every beat needs `idea` and `show`); then show it to the editor",
            "proposed": "the editor hasn't approved the beat sheet yet; show the review page and run `fzv approve <folder> beats` once they do",
            "changed": "the beat sheet changed after it was approved; show the editor what changed and approve it again"}[st]


def gate_render(proj, settings: dict) -> str | None:
    if not proj.p("beats.yaml").exists():
        return None
    why = gate_build(proj, settings)                           # never render a build whose beat sheet changed since approval
    if why or gate_mode(settings, "storyboard") == "off":
        return why
    st = storyboard_state(proj)
    if st == "approved":
        return None
    return {"missing": "there is no storyboard yet: run `fzv storyboard` and show it to the editor",
            "stale": "the edit was built again after the storyboard: run `fzv storyboard` (only changed frames are redone) and show the editor",
            "ready": "the editor hasn't approved the storyboard yet; show it and run `fzv approve <folder> storyboard` once they do"}[st]
