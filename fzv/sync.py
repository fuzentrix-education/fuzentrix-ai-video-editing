"""Narration-to-picture sync checks (rules S2–S4), run by `fzv validate`:

- S2: nothing appears before she says it (more than `early_s`, 0.15 s, before its word), and no faded previews.
- S5: nothing lands late: a value or word shown more than `late_s` (0.3 s) after she says it. Both use exact first-seen times
  (sample.mjs searches inside each 0.5 s step), as in the Career Orbit kit's sync audit (2026-11-05).
- S4: while she explains, something on screen reacts at least every `max_hold_s` seconds.
- S3 (advice): a value she says again while it is on screen gets a reaction (a highlight, a focus, a pulse).

S2 and S3 read what the viewer can see: the DOM samples carry each element's visible text, matched to her words in the
transcript (numbers exactly). S4 reads the resolved spec: every time something enters, changes or leaves.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from .anchors import Transcript, norm
from .spec import TIME_KEYS, TIME_LISTS

# templates whose text is not a "said" thing: section titles and chrome, the instructor, typed code and program output
EXEMPT = {"chapter", "progress", "bug", "name-card", "studio-tag", "captions", "presenter", "scene",
          "code-card", "terminal", "recording-window", "syntax-pill"}      # titles count since 2026-11-05: they must match what she says
TITLES = {"header", "title-hero", "big-word", "term-reveal"}
STOP = {"with", "that", "this", "from", "into", "your", "have", "will", "what", "when", "then", "than", "they", "them", "each",
        "only", "also", "here", "there", "just", "like", "more", "most", "some", "such", "very", "over", "about", "after",
        "before", "where", "which", "while", "does", "done", "make", "made", "used", "uses", "same", "other", "every", "both",
        "the", "and", "for", "are", "you", "can", "was", "not", "but", "all", "its", "has", "had", "our", "out", "use", "may",
        "any", "get", "see", "let", "now", "new", "way", "say", "too", "also", "into", "onto", "per", "via"}


def tokens(txt: str) -> list[str]:
    """The words of on-screen text worth matching to speech: numbers, and words of 4+ letters that carry meaning."""
    out = []
    for w in re.findall(r"[0-9]+(?:\.[0-9]+)?|[A-Za-z]+", txt or ""):
        n = norm(w)
        if n and (n.isdigit() or (len(n) >= 3 and n not in STOP)):
            out.append(n)
    return list(dict.fromkeys(out))


def collect(store: dict, clip_id: str, layer: str, t: float, items: list[dict]):
    """Remember, per element, when it was first and last visible and when each of its words first became readable."""
    for i in items:
        if "id" not in i or i.get("tpl") in EXEMPT or i["role"] not in ("block", "note", "text", "part", "title"):
            continue
        r = store.setdefault((clip_id, i["id"]), {"tpl": i.get("tpl", ""), "role": i["role"], "layer": layer, "first": t, "last": t, "toks": {}, "txt": ""})
        r["last"] = t
        if i.get("txt"):
            r["txt"] = r["txt"] or i["txt"]
            for k in tokens(i["txt"]):
                r["toks"].setdefault(k, t)


def refine(store: dict, clip_id: str, start: float, ref: dict):
    """Replace the sampled first-seen times (0.5 s steps) with the exact ones the sampler found: the element's text, each word."""
    for eid, r in ref.items():
        e = store.get((clip_id, eid))
        if not e:
            continue
        if "@" in r:
            e["first"] = min(e["first"], round(start + r["@"], 3))
        for k in e["toks"]:
            if k in r:
                e["toks"][k] = round(start + r[k], 3)


def event_times(params, out: list[float]):
    """Every time in a resolved scene's params: entrances, exits, state changes, typing steps, highlights."""
    if isinstance(params, dict):
        for k, v in params.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and (k == "at" or k in TIME_KEYS or (isinstance(k, str) and k.endswith("_at"))):
                out.append(float(v))
            elif k in TIME_LISTS and isinstance(v, list):
                out += [float(x) for x in v if isinstance(x, (int, float))]
            elif k == "parts" and isinstance(v, list):
                out += [float(p[1]) for p in v if isinstance(p, (list, tuple)) and len(p) > 1 and isinstance(p[1], (int, float))]
            elif k == "type" and isinstance(v, list):                       # typing without parts runs at a steady speed: it moves
                lines = params.get("lines") or []
                for ty in v:
                    if isinstance(ty, dict) and isinstance(ty.get("at"), (int, float)) and not ty.get("parts"):
                        n = len(lines[ty["line"] - 1]) if 0 < ty.get("line", 0) <= len(lines) else 0
                        out += [ty["at"] + s for s in range(0, int(n / (ty.get("cps") or 16)) + 1)]
                event_times(v, out)
            elif isinstance(v, (dict, list)):
                event_times(v, out)
    elif isinstance(params, list):
        for x in params:
            event_times(x, out)
    return out


def section_events(sec: dict) -> list[float]:
    out = [float(sec["range"][0]), float(sec["range"][1])]
    for s in sec.get("scenes") or []:
        (name, p), = s.items()
        if name != "sound":                                   # a sound alone is not something to see
            event_times(p, out)
    return sorted(t for t in out if sec["range"][0] - 0.01 <= t <= sec["range"][1] + 0.01)


def cut_out(a: float, b: float, hidden: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pieces = [(a, b)]
    for h0, h1 in hidden:
        pieces = [q for p0, p1 in pieces for q in ((p0, min(p1, h0)), (max(p0, h1), p1)) if q[1] - q[0] > 0.05]
    return pieces


# ---------- S6 (advice): the English and Telugu transcripts disagree about when she says an anchored word ----------
_C = dict(zip("కఖగఘఙచఛజఝఞటఠడఢణతథదధనపఫబభమయరఱలళవశషసహ", "kkggncsjjnttddnttddnpfbbmyrrllvsssh"))
_V = dict(zip("అఆఇఈఉఊఋఎఏఐఒఓఔ", ["a", "a", "i", "i", "u", "u", "r", "e", "e", "ai", "o", "o", "au"]))
_M = dict(zip("ాిీుూృెేైొోౌ", ["a", "i", "i", "u", "u", "r", "e", "e", "ai", "o", "o", "au"]))


def roman(w: str) -> str:
    """Telugu script to rough Latin letters ("పిక్సుడు" -> "piksudu"), enough to spot an English word she said in Telugu speech."""
    out = []
    for ch in w:
        if ch in _C:
            out.append(_C[ch] + "a")
        elif ch in _V:
            out.append(_V[ch])
        elif ch in _M or ch == "్":
            if out and out[-1].endswith("a"):
                out[-1] = out[-1][:-1]
            if ch in _M:
                out.append(_M[ch])
        elif ch == "ం":                                  # anusvara: "n" in the English words she uses (print, string, indexing)
            out.append("n")
        elif ch.isascii() and ch.isalnum():
            out.append(ch.lower())
    return "".join(out)


def skeleton(w: str) -> str:
    """Consonants only, with the sounds Telugu spelling and Whisper swap merged (f/p, b/p, d/t, g/k, c/k, w/v, z/j)."""
    w = w.lower().replace("ch", "C").replace("ph", "p").replace("th", "t").replace("sh", "s").replace("c", "k").replace("C", "c")
    w = w.translate(str.maketrans("wfxqzbdg", "vpkkjptk"))
    w = re.sub(r"[^a-z0-9]", "", w)
    return re.sub(r"[aeiouyh]", "", w) or w


def disagreements(anchors: list, tx: Transcript, gap: float = 0.5, limit: int = 40) -> list[dict]:
    """Anchors where the Telugu-mode transcript puts the same word more than `gap` s away from the English one (Tuples 2026-11-05:
    "add", "remove", "change" ~1 s early, "Student is equal" 3 s early in the English pass). Advice: check those moments by ear or
    with `fzv words --te`, and anchor on the Telugu word when that one is right."""
    te = tx.te
    if te is None or not te.words:
        return []
    cand = [(w, t, skeleton(roman(w))) for w, t in te.words]
    out, seen = [], set()
    for phrase, t in anchors:
        p = phrase.lstrip("@").split("#")[0]
        if p.startswith("te:"):
            continue
        tok = next((x for x in (norm(w) for w in p.split()) if x.isdigit() or len(x) >= 4), None)
        if not tok:
            continue
        en = tx.find(tok, after=t - 0.3, before=t + 4) or t            # when the English pass hears that word
        best = None
        for w, tt, sk in cand:
            if abs(tt - en) > 3.5:                                 # up to 3.5 s apart ("Student is equal": 2.9 s in Tuples)
                continue
            if tok.isdigit():
                ok = re.sub(r"\D", "", w) == tok
                score = 1.0 if ok else 0
            elif re.fullmatch(r"[0-9a-z]+", w):                                       # an English word in the Telugu transcript
                score = SequenceMatcher(None, tok, w).ratio()
            else:
                k = skeleton(tok)
                score = SequenceMatcher(None, k, sk).ratio() if len(k) >= 3 and len(sk) >= 3 and k[0] == sk[0] else 0   # same first sound
            if score >= 0.82 and (best is None or score - 0.15 * abs(tt - en) > best[0] - 0.15 * abs(best[2] - en)):
                best = (score, w, tt)
        other = [m for m in tx.mentions(tok, best[2] - 0.6, best[2] + 0.6) if abs(m - en) > 0.05] if best else []
        if best and abs(best[2] - en) > gap and not other and (tok, round(en, 1)) not in seen:
            seen.add((tok, round(en, 1)))                  # (a word she says twice: the Telugu hit is her other time, not a drift)
            out.append({"rule": "S6", "t": round(t, 2), "msg": f"“{phrase}” lands at {t:.1f}s, but the Telugu transcript hears “{best[1]}” at "
                        f"{best[2]:.1f}s ({best[2] - en:+.1f}s): check which is right (`fzv words --te`); if it's the Telugu one, anchor with "
                        f"\"@te:{best[1]}\""})
    return out[:limit]


def said_at(tx: Transcript, k: str, t0: float, t1: float, txt: str = "") -> list[float]:
    """When she says on-screen word `k` between t0 and t1. A negative number on screen ("-1") is said "minus 1": from "minus"."""
    if k.isdigit() and re.search(rf"[-−]\s*{k}\b", txt or ""):
        return [m for m in tx.mentions("minus", t0, t1) if tx.mentions(k, m, m + 1.2)]
    return tx.mentions(k, t0, t1)


def check(store: dict, spec: dict, tx: Transcript, cuts: list[dict], quiet: list, cfg: dict) -> tuple[list, list, dict]:
    """(problems, advice, summary) for rules S2–S4."""
    early_s, late_s, window = cfg.get("early_s", 0.15), cfg.get("late_s", 0.3), cfg.get("window_s", 30)
    max_hold, min_words, rep_gap = cfg.get("max_hold_s", 8), cfg.get("hold_min_words", 10), cfg.get("repeat_gap_s", 1.2)
    problems, advice = [], []
    secs = spec.get("sections") or []
    sec_at = lambda t: next((s for s in secs if s["range"][0] - 0.01 <= t < s["range"][1]), None)   # noqa: E731
    events = {id(s): section_events(s) for s in secs}
    te_times = (spec.get("_anchoring") or {}).get("te_times") or []
    on_te = lambda f: any(abs(f - x) <= 0.12 for x in te_times)                                     # noqa: E731
    # an `@te:` anchor lands on her Telugu word: the English transcript (which misheard it) can't judge that moment

    # S2: early. A single value or word (a tile, a field value) is checked on its own word; anything longer as a whole: it is
    # early only when she hasn't started on any of its words yet (a label "day · month · year", a definition she then reads).
    early = []
    allowed = []                                          # scenes with `early_ok: <reason>`: the planner chose the moment on purpose
    for sec in secs:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            if isinstance(p, dict) and p.get("early_ok") and isinstance(p.get("at"), (int, float)):
                allowed.append((name, p["at"] - 0.5, p.get("until") if isinstance(p.get("until"), (int, float)) else sec["range"][1]))
    for (clip, _), r in store.items():
        if not r["toks"] or any(r["tpl"] == n and a0 <= r["first"] <= a1 for n, a0, a1 in allowed):
            continue
        # timed from when its words become readable (a container can be on screen, empty, before its words come in)
        units = [([k], t) for k, t in r["toks"].items()] if len(r["toks"]) == 1 else [(list(r["toks"]), min(r["toks"].values()))]
        for toks, f in units:
            if on_te(f):
                continue
            sec = sec_at(f)
            back = max(sec["range"][0] - 2, f - 20) if sec else f - 20
            room = cfg.get("early_title_s", 1.0) if r["tpl"] in TITLES else early_s      # a title may lead her by a moment
            if any(said_at(tx, k, back, f + room, r["txt"]) for k in toks):
                continue
            nxt = [m for k in toks for m in said_at(tx, k, f + room, f + window, r["txt"])]
            if nxt:
                m = min(nxt)
                word = next(k for k in toks if m in said_at(tx, k, m - 0.01, m + 0.01, r["txt"]))
                early.append((f, m, r, word))
    for f, m, r, word in sorted(early, key=lambda e: e[0]):
        what = f"“{r['txt'][:40]}”" if r["txt"] else r["tpl"]
        problems.append({"rule": "S2", "t": round(f, 2), "msg": f"{r['tpl'] or r['role']} {what} is on screen {m - f:.1f}s before she says "
                         f"“{word}” ({m:.1f}s): put it on her word (an @anchor), not ahead of it"})

    # S5: late. A single value or word that comes in more than late_s after she says it (and not again on a later word)
    late = []
    for (clip, _), r in store.items():
        if len(r["toks"]) != 1 or r["tpl"] in TITLES or any(r["tpl"] == n and a0 <= r["first"] <= a1 for n, a0, a1 in allowed):
            continue
        (k, f), = r["toks"].items()
        if on_te(f) or said_at(tx, k, f - late_s, f + early_s, r["txt"]):
            continue
        before = said_at(tx, k, f - 2.0, f - late_s, r["txt"])
        if before:
            late.append((f, max(before), r, k))
    for f, m, r, k in sorted(late, key=lambda e: e[0]):
        problems.append({"rule": "S5", "t": round(f, 2), "msg": f"{r['tpl'] or r['role']} “{r['txt'][:40]}” comes in {f - m:.1f}s after she says "
                         f"“{k}” ({m:.1f}s): put it on her word (an @anchor on that word, not the phrase's start or a later one)"})

    # S2: faded previews (tiles that enter dimmed, shown before they are meant)
    for sec in secs:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            if name != "tiles" or not isinstance(p, dict) or not isinstance(p.get("at"), (int, float)):
                continue
            app = p.get("appear") or []
            for st in p.get("states") or []:
                i = st.get("i")
                t_in = app[i] if isinstance(i, int) and i < len(app) and isinstance(app[i], (int, float)) else p["at"]
                if st.get("state") == "dim" and isinstance(st.get("at"), (int, float)) and st["at"] <= t_in + 0.3:
                    problems.append({"rule": "S2", "t": round(t_in, 2), "msg": f"tiles {p.get('id', '')}: tile {i} enters faded (a preview); "
                                     "show each tile on the word that names it instead"})
                    break

    # S4: holds. Gaps between on-screen events while she explains (studio shots and quiet stretches excluded).
    hidden = [(c["start"], c["end"]) for c in cuts if c["kind"] == "studio"] + [tuple(q[:2]) for q in quiet]
    holds = []
    for sec in secs:
        ev = events[id(sec)]
        for a, b in zip(ev, ev[1:]):
            for a2, b2 in cut_out(a, b, hidden):
                if b2 - a2 <= max_hold:
                    continue
                said = tx.between(a2 + 0.5, b2 - 0.5)
                if len(said) >= min_words:
                    holds.append((a2, b2, said))
    for a, b, said in holds:
        snippet = " ".join(w for w, _ in said[:10])
        problems.append({"rule": "S4", "t": round(a, 2), "msg": f"nothing on screen changes for {b - a:.1f}s ({a:.1f}–{b:.1f}s) while she explains "
                         f"(“{snippet}…”): highlight what she is talking about, or bring the next step in"})

    # S3 (advice): a short on-screen value she says again, with nothing reacting
    reps = []
    for (clip, _), r in store.items():
        if not r["toks"] or len(r["toks"]) > 2 or r["tpl"] in TITLES:     # a title doesn't flash each time she says its word
            continue
        sec = sec_at(r["first"])
        ev = events[id(sec)] if sec else []
        for k, f in r["toks"].items():
            for m in tx.mentions(k, f + 1.5, r["last"] - 0.5):
                if not any(m - 1.0 <= e <= m + rep_gap for e in ev):          # "minus 2": landing on "minus" counts
                    reps.append((m, r, k))
    seen = set()
    for m, r, k in sorted(reps, key=lambda x: x[0]):
        key = (r["tpl"], k, round(m))
        if key in seen:
            continue
        seen.add(key)
        advice.append({"rule": "S3", "t": round(m, 2), "msg": f"she says “{k}” again while {r['tpl'] or r['role']} “{r['txt'][:30]}” is on screen and nothing "
                       "reacts: highlight it on her word (tiles `focus`, form-card `focus`, code `highlights`)"})
    anch = spec.get("_anchoring") or {}
    summary = {"early": len(early), "late": len(late), "holds": len(holds), "longest_hold_s": round(max((b - a for a, b, _ in holds), default=0), 1),
               "repeats_without_reaction": len(advice), "times_on_words": anch.get("anchored", 0), "times_typed": anch.get("typed", 0)}
    return problems, advice[:40], summary
