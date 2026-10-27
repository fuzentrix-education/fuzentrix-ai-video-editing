"""What the editor sees (design §9f): the footage sheet, the storyboard and one review page per video.

  edit/out/footage.jpg          the raw cut every 10 s and at every shot change, with times (for Claude and the editor)
  edit/review/storyboard/*.jpg  one frame per beat, graphics over the real footage, taken after `fzv build` and before rendering
  edit/out/storyboard.jpg       the storyboard as one labelled sheet (only changed frames: storyboard_changed.jpg)
  edit/review/index.html        beat sheet -> storyboard -> final, the "to confirm" list, and change requests the editor copies
                                into Claude Code (a local page: nothing is uploaded)
"""
from __future__ import annotations

import html
import json
import queue
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont

from . import beats as B
from .anchors import Transcript
from .config import REPO


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                                  # Pillow without FreeType sizes
        return ImageFont.load_default()


def grab(src: Path, t: float, out: Path, w: int) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", str(src), "-frames:v", "1", "-vf", f"scale={w}:-2",
                    "-q:v", "4", str(out)], capture_output=True)
    return out


def sheet(tiles: list[tuple[Path, str]], out: Path, cols: int, w: int, pad: int = 6) -> Path | None:
    """A labelled contact sheet: tiles of width `w` with a caption band under each."""
    ims = [(Image.open(f).convert("RGB"), cap) for f, cap in tiles if f.exists()]
    if not ims:
        return None
    th, band = w * 9 // 16, 30 if w < 500 else 40
    rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * w + (cols - 1) * pad, rows * (th + band) + (rows - 1) * pad), (20, 22, 28))
    d, F = ImageDraw.Draw(S), font(17 if w < 500 else 22)
    for i, (im, cap) in enumerate(ims):
        x, y = (i % cols) * (w + pad), (i // cols) * (th + band + pad)
        S.paste(im.resize((w, th)), (x, y))
        d.text((x + 8, y + th + 6), cap[: int(w / (9 if w < 500 else 11))], fill=(235, 238, 245), font=F)
    out.parent.mkdir(parents=True, exist_ok=True)
    S.save(out, quality=86)
    return out


def segments(proj) -> list[dict]:
    f = proj.p("transcript.jsonl")
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def line_at(segs: list[dict], t: float) -> str:
    best = None
    for s in segs:
        if s["start"] <= t + 0.5:
            best = s
        else:
            break
    return (best or {}).get("text", "") if best and t <= best["end"] + 3 else ""


# ---------------------------------------------------------------- footage sheet
def footage(proj, every: float = 10.0, w: int = 320, log=print) -> list[dict]:
    pdata = proj.load()
    raw, dur = proj.folder / pdata["raw"], float(pdata["duration"])
    cuts = json.loads(proj.p("cuts.json").read_text()) if proj.p("cuts.json").exists() else []
    times = sorted({round(min(dur - 0.1, i * every + every / 2), 1) for i in range(int(dur // every) + 1)} |
                   {round(min(dur - 0.1, c["start"] + 0.5), 1) for c in cuts})
    D = proj.edit / "review" / "footage"
    todo = [t for t in times if not (D / f"t{int(t * 10):06d}.jpg").exists()]
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda t: grab(raw, t, D / f"t{int(t * 10):06d}.jpg", w), todo))
    segs = segments(proj)
    rows = [{"t": t, "file": f"footage/t{int(t * 10):06d}.jpg", "shot": B.kind_at(cuts, t), "text": line_at(segs, t)} for t in times]
    if todo or not (proj.edit / "out" / "footage.jpg").exists():
        sheet([(D / Path(r["file"]).name, f"{B.mmss(r['t'])} {r['shot']}") for r in rows], proj.edit / "out" / "footage.jpg", 6, w)
        log(f"footage: {len(times)} frames -> edit/out/footage.jpg")
    return rows


# ---------------------------------------------------------------- storyboard
def key_times(proj) -> dict[str, float]:
    doc = B.load(proj.p("beats.yaml"))
    tx = Transcript(proj.p("transcript.jsonl"))
    out = {}
    for b in doc.get("beats") or []:
        if isinstance(b.get("start"), (int, float)) and isinstance(b.get("end"), (int, float)):
            out[str(b["id"])] = B.key_time(b, [B.resolve_time(v, b, tx) for v in b.get("sync") or []], tx)
    return out


def storyboard(proj, workers: int = 3, redo_all: bool = False, log=print) -> dict:
    """One frame per beat at its key moment, graphics over the raw-cut frame. Frames whose clip and time are unchanged are kept,
    so after a revision only the changed beats are snapshotted again."""
    from .preview import raw_frame
    from .render import snapshot
    doc = B.load(proj.p("beats.yaml"))
    keys = key_times(proj)
    man = json.loads((proj.edit / "built" / "clips.json").read_text())
    raw = proj.folder / proj.load()["raw"]
    R = proj.edit / "review"
    D = R / "storyboard"
    D.mkdir(parents=True, exist_ok=True)
    meta_f = R / "storyboard.json"
    old = json.loads(meta_f.read_text()).get("frames", {}) if meta_f.exists() and not redo_all else {}
    cuts = json.loads(proj.p("cuts.json").read_text()) if proj.p("cuts.json").exists() else []
    frames, jobs = {}, {}
    for b in doc.get("beats") or []:
        bid, t = str(b["id"]), keys.get(str(b["id"]))
        if t is None:
            continue
        layer = "studio" if B.kind_at(cuts, t) == "studio" else "plate"      # what the final shows at that moment
        clip = next((m for m in man if m["start"] <= t < m["end"] and m["layer"] == layer), None)
        sig = f"{clip['id']}:{clip['hash']}:{t:.2f}" if clip else f"none:{t:.2f}"
        frames[bid] = {"t": t, "clip": clip["id"] if clip else None, "sig": sig, "file": f"storyboard/{bid}.jpg"}
        if old.get(bid, {}).get("sig") == sig and (D / f"{bid}.jpg").exists():
            continue
        jobs.setdefault(clip["id"] if clip else None, []).append(bid)

    free = queue.Queue()                                          # worker folders, one snapshot at a time each
    for k in range(max(1, min(workers, len(jobs) or 1))):
        free.put(120 + k)

    def run(cid: str | None, bids: list[str]):
        k = free.get()
        try:
            shoot(cid, bids, k)
        finally:
            free.put(k)

    def shoot(cid: str | None, bids: list[str], k: int):
        ts = [frames[b]["t"] for b in bids]
        if cid is None:                                           # no graphics at this moment: the footage alone
            for b, t in zip(bids, ts):
                raw_frame(raw, t).convert("RGB").resize((1280, 720)).save(D / f"{b}.jpg", quality=88)
            return
        clip = next(m for m in man if m["id"] == cid)
        local = [round(max(0.0, t - clip["start"]), 3) for t in ts]
        snap = snapshot(proj, clip, local, proj.edit / "out" / f"story_{cid}", k=k)
        for b, t, lt in zip(bids, ts, local):
            ov = Image.open(snap / f"at-{('%.3f' % lt).rstrip('0').rstrip('.')}s.png").convert("RGBA")
            base = raw_frame(raw, t).resize(ov.size) if not clip.get("opaque") else Image.new("RGBA", ov.size, (0, 0, 0, 255))
            Image.alpha_composite(base, ov).convert("RGB").resize((1280, 720)).save(D / f"{b}.jpg", quality=88)

    t0 = time.time()
    if jobs:
        log(f"storyboard: {sum(len(v) for v in jobs.values())} frame(s) from {len(jobs)} clip(s)")
        with ThreadPoolExecutor(max(1, min(workers, len(jobs)))) as ex:
            for f in [ex.submit(run, cid, bids) for cid, bids in jobs.items()]:
                f.result()
    changed = [b for bids in jobs.values() for b in bids]
    meta = {"build": B.build_signature(proj), "at": time.strftime("%Y-%m-%d %H:%M:%S"), "frames": frames, "changed": changed}
    meta_f.write_text(json.dumps(meta, indent=1))
    order = [str(b["id"]) for b in doc.get("beats") or [] if str(b["id"]) in frames]
    shows = {str(b["id"]): str(b.get("show") or "") for b in doc.get("beats") or []}
    cap = lambda i, b: f"#{i} {B.mmss(frames[b]['t'])}  {shows[b]}"
    out = sheet([(D / f"{b}.jpg", cap(i, b)) for i, b in enumerate(order, 1)], proj.edit / "out" / "storyboard.jpg", 3, 640)
    part = proj.edit / "out" / "storyboard_changed.jpg"
    if changed and len(changed) < len(order):
        sheet([(D / f"{b}.jpg", cap(order.index(b) + 1, b)) for b in order if b in changed], part, min(3, len(changed)), 640)
    elif part.exists():
        part.unlink()
    log(f"storyboard: {len(order)} beat(s), {len(changed)} new frame(s) in {time.time() - t0:.0f}s -> {out}")
    return meta


# ---------------------------------------------------------------- review page
def folder_ref(proj) -> str:
    try:
        ref = str(proj.folder.relative_to(REPO.resolve()))
    except ValueError:
        ref = str(proj.folder)
    return f'"{ref}"' if " " in ref else ref


def title_of(proj) -> str:
    sp = B.load(proj.spec_path) if proj.spec_path.exists() else {}
    return sp.get("title") or proj.prompt_fields().get("title") or proj.folder.name


def section(md: str, head: str) -> list[str]:
    out, on = [], False
    for ln in md.splitlines():
        if ln.startswith("## "):
            on = ln[3:].strip().lower() == head.lower()
            continue
        if on and ln.strip().startswith("- "):
            out.append(ln.strip()[2:])
    return out


def next_step(st: dict, has_final: bool, legacy: bool) -> tuple[str, str | None]:
    """(what the editor should do now, the approval to copy or None)."""
    if legacy:
        return "This edit was made before beat sheets. Watch the final video and ask for changes at any time.", None
    b, s = st["beats"], st["storyboard"]
    if b in ("missing", "draft"):
        return "Claude is preparing the beat sheet.", None
    if b == "proposed":
        return "Read the beat sheet: one row per idea, with what we show and on which words. Write changes under any beat, or approve it.", "beats"
    if b == "changed":
        return "The beat sheet changed after you approved it. Check the changes, then approve it again.", "beats"
    if s in ("missing", "stale"):
        return "Beat sheet approved. Claude is building the storyboard (one frame per beat).", None
    if s == "ready":
        return "Check the storyboard: one frame per beat over the real footage. Write changes under any beat, or approve it to render the final video.", "storyboard"
    if not has_final:
        return "Storyboard approved. The final video is rendering.", None
    return "The final video is ready. Watch it, check the list to confirm, and ask for changes at any time.", None


def page(proj, settings: dict | None = None, log=print) -> Path:
    settings = settings or proj.settings()
    pdata = proj.load()
    R = proj.edit / "review"
    R.mkdir(parents=True, exist_ok=True)
    rows = footage(proj, log=log) if pdata.get("raw") else []
    raw = proj.folder / pdata["raw"] if pdata.get("raw") else None
    doc = B.load(proj.p("beats.yaml"))
    keys = key_times(proj) if doc else {}
    tx = Transcript(proj.p("transcript.jsonl"))
    title = title_of(proj)
    final = proj.output_path(title)
    has_final = final.exists()
    stamp = lambda f: int(f.stat().st_mtime) if f.exists() else 0
    # footage and final frames at each beat's key moment (re-grabbed when the time or the final changes)
    cache_f = R / "frames.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    jobs = []
    for bid, t in keys.items():
        for kind, src in (("raw", raw), ("final", final if has_final else None)):
            if not src:
                continue
            f = R / kind / f"{bid}.jpg"
            sig = f"{t:.2f}:{stamp(src)}"
            if cache.get(f"{kind}/{bid}") != sig or not f.exists():
                jobs.append((src, t, f))
                cache[f"{kind}/{bid}"] = sig
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda j: grab(j[0], j[1], j[2], 640), jobs))
    cache_f.write_text(json.dumps(cache))
    st = {"beats": B.beats_state(proj), "storyboard": B.storyboard_state(proj)}
    legacy = B.legacy(proj)
    msg, approve = next_step(st, has_final, legacy)
    sb = json.loads((R / "storyboard.json").read_text()).get("frames", {}) if (R / "storyboard.json").exists() else {}
    beats = []
    for i, b in enumerate(doc.get("beats") or [], 1):
        bid = str(b.get("id"))
        sync = []
        for v in b.get("sync") or []:
            t = B.resolve_time(v, b, tx) if isinstance(b.get("start"), (int, float)) else None
            sync.append({"w": "" if isinstance(v, (int, float)) else str(v).lstrip("@"), "t": t})
        fr = {}
        for kind, rel in (("footage", f"raw/{bid}.jpg"), ("storyboard", f"storyboard/{bid}.jpg"), ("final", f"final/{bid}.jpg")):
            f = R / rel
            if f.exists() and (kind != "storyboard" or bid in sb) and (kind != "final" or has_final):
                fr[kind] = f"{rel}?v={stamp(f)}"
        beats.append({"id": bid, "n": i, "start": b.get("start"), "end": b.get("end"), "shot": b.get("shot", ""), "says": b.get("says", ""),
                      "idea": b.get("idea", ""), "show": b.get("show", ""), "templates": [str(t) for t in b.get("templates") or []],
                      "sync": sync, "concepts": b.get("concepts") or [], "notes": b.get("notes", ""), "feedback": b.get("feedback", ""),
                      "key": keys.get(bid), "frames": fr})
    dec = proj.p("decisions.md").read_text(encoding="utf-8") if proj.p("decisions.md").exists() else ""
    ver = json.loads(proj.p("verify.json").read_text()) if proj.p("verify.json").exists() and has_final else None
    data = {
        "title": title, "folder": folder_ref(proj), "mode": pdata.get("mode"), "duration": pdata.get("duration"),
        "generated": time.strftime("%Y-%m-%d %H:%M"), "state": st, "legacy": legacy, "next": msg, "approve": approve,
        "approvals": pdata.get("approvals") or {},
        "final": {"src": "../../" + quote(final.name), "name": final.name, "v": stamp(final),
                  "checks": {k: v.get("ok") for k, v in (ver or {}).get("checks", {}).items()}} if has_final else None,
        "confirm": section(dec, "To confirm"),
        "beats": beats,
        "footage": [dict(r, file=f"{r['file']}?v={stamp(R / r['file'])}") for r in rows],
        "revisions": proj.p("revisions.md").read_text(encoding="utf-8") if proj.p("revisions.md").exists() else "",
    }
    out = R / "index.html"
    out.write_text(PAGE.replace("__TITLE__", html.escape(title)).replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")),
                   encoding="utf-8")
    return out


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review: __TITLE__</title>
<style>
:root{--bg:#f6f7fb;--card:#fff;--ink:#1d2330;--mute:#5d6678;--line:#e2e6ef;--accent:#2f6fed;--accent-ink:#fff;--ok:#1f9d55;--warn:#c27c0e;--wait:#7a5cf0;--chip:#eef2fb}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#11141b;--card:#1a1f29;--ink:#e8ebf2;--mute:#9aa3b5;--line:#2a3140;--accent:#5b8dff;--accent-ink:#0b1020;--ok:#3ccf7a;--warn:#f0a63a;--wait:#a28bff;--chip:#232a38}}
:root[data-theme=dark]{--bg:#11141b;--card:#1a1f29;--ink:#e8ebf2;--mute:#9aa3b5;--line:#2a3140;--accent:#5b8dff;--accent-ink:#0b1020;--ok:#3ccf7a;--warn:#f0a63a;--wait:#a28bff;--chip:#232a38}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:20px 16px 110px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:28px 0 10px}.sub{color:var(--mute);font-size:13px}
.steps{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.step{display:flex;align-items:center;gap:8px;padding:6px 12px;border-radius:999px;background:var(--card);border:1px solid var(--line);font-size:13px}
.dot{width:9px;height:9px;border-radius:50%;background:var(--mute)}.ok .dot{background:var(--ok)}.wait .dot{background:var(--wait)}.warn .dot{background:var(--warn)}
.next{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;padding:14px 16px;display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.next p{margin:0;flex:1 1 320px}
button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:7px 14px;cursor:pointer}
button.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:600}
.player{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
video{width:100%;border-radius:8px;background:#000;display:block}
.here{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}.here input{flex:1 1 260px}
input,textarea{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:7px 10px;width:100%}
textarea{min-height:42px;resize:vertical}
.checks{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.chip{background:var(--chip);border-radius:6px;padding:2px 8px;font-size:12px}
.chip.bad{color:#fff;background:#d64545}
ul.confirm{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px 12px 34px;margin:0}
.beat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin:0 0 14px}
.beat header{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.num{font-weight:700;background:var(--accent);color:var(--accent-ink);border-radius:7px;padding:1px 9px}
a.time{color:var(--accent);cursor:pointer;font-weight:600;text-decoration:none}
.frames{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-bottom:10px}
figure{margin:0}figure img{width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:8px;border:1px solid var(--line);display:block;background:var(--bg)}
figcaption{font-size:12px;color:var(--mute);margin-top:3px}
dl{display:grid;grid-template-columns:150px 1fr;gap:4px 14px;margin:0 0 10px}dt{color:var(--mute);font-size:13px}dd{margin:0}
.says{color:var(--mute);font-style:italic}
.req{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:10px 16px;display:none}
.req .in{max-width:1180px;margin:0 auto;display:flex;gap:10px;align-items:center;flex-wrap:wrap}.req .in span{flex:1 1 200px}
.toast{position:fixed;left:50%;transform:translateX(-50%);bottom:78px;background:var(--ink);color:var(--bg);padding:8px 14px;border-radius:8px;display:none}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin-top:12px}summary{cursor:pointer;font-weight:600}
.foot{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;margin-top:10px}.foot div{font-size:12px;color:var(--mute)}
pre{white-space:pre-wrap;font-size:13px}
@media (max-width:640px){dl{grid-template-columns:1fr}dt{margin-top:6px}}
</style></head><body><main id="app"></main>
<div class="req" id="req"><div class="in"><span id="reqn"></span><button id="clear">Clear</button><button class="primary" id="copy">Copy for Claude</button></div></div>
<div class="toast" id="toast"></div>
<script>
const D = __DATA__;
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const mmss = t => t == null ? "" : `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;
const KEY = "fzv-review:" + D.folder;
let store = {beats: {}, times: []};
try { store = Object.assign(store, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) {} updateBar(); };
const label = {missing: "not started", draft: "being written", proposed: "waiting for you", changed: "changed, approve again", approved: "approved",
               stale: "being updated", ready: "waiting for you"};
const cls = s => s === "approved" ? "ok" : (s === "proposed" || s === "ready" || s === "changed") ? "wait" : "";
function steps() {
  if (D.legacy) return "";
  const f = D.final ? (Object.values(D.final.checks).every(Boolean) ? "ok" : "warn") : "";
  return `<div class="steps"><span class="step ${cls(D.state.beats)}"><i class="dot"></i>1 · Beat sheet: ${label[D.state.beats]}</span>
    <span class="step ${cls(D.state.storyboard)}"><i class="dot"></i>2 · Storyboard: ${D.state.beats === "approved" ? label[D.state.storyboard] : "after the beat sheet"}</span>
    <span class="step ${f}"><i class="dot"></i>3 · Final video: ${D.final ? "ready" : "not rendered yet"}</span></div>`;
}
function beatCard(b) {
  const fig = (k, cap) => b.frames[k] ? `<figure><a href="${b.frames[k].split("?")[0]}" target="_blank"><img loading="lazy" src="${b.frames[k]}" alt="${cap} at ${mmss(b.key)}"></a><figcaption>${cap}</figcaption></figure>` : "";
  const frames = fig("footage", "Footage") + fig("storyboard", "Storyboard (before render)") + fig("final", "Final video");
  const sync = b.sync.map(s => s.t == null ? `${esc(s.w)} (not found)` : `${esc(s.w)} <a class="time" data-t="${s.t}">${mmss(s.t)}</a>`.trim()).join(" · ");
  const row = (k, v) => v ? `<dt>${k}</dt><dd>${v}</dd>` : "";
  return `<article class="beat" id="${esc(b.id)}"><header><span class="num">${b.n}</span>
      <a class="time" data-t="${b.start}">${mmss(b.start)}–${mmss(b.end)}</a><span class="sub">${esc(b.shot)}</span></header>
    ${frames ? `<div class="frames">${frames}</div>` : ""}
    <dl>${row("Instructor says", `<span class="says">“${esc(b.says)}”</span>`)}${row("The idea", esc(b.idea) || "<i>(being written)</i>")}
      ${row("What we show", esc(b.show) || "<i>(being written)</i>")}${row("On the words", sync)}
      ${row("Templates", b.templates.map(t => `<span class="chip">${esc(t)}</span>`).join(" "))}
      ${row("Concept moments", esc(b.concepts.join("; ")))}${row("Notes", esc(b.notes))}${row("Your earlier requests", esc(b.feedback))}</dl>
    <textarea data-beat="${b.n}" data-t="${b.start}" placeholder="Anything to change in beat ${b.n}? Write it in plain words.">${esc(store.beats[b.n] || "")}</textarea></article>`;
}
function render() {
  const app = $("#app");
  let h = `<h1>${esc(D.title)}</h1><div class="sub">${esc(D.folder)} · ${esc(D.mode || "")} · ${mmss(D.duration)} · page made ${esc(D.generated)}</div>`;
  h += steps();
  h += `<div class="next"><p>${esc(D.next)}</p>${D.approve ? `<button class="primary" id="approve">Copy approval for Claude</button>` : ""}</div>`;
  if (D.final) {
    const bad = Object.entries(D.final.checks).filter(([, ok]) => !ok).map(([k]) => k);
    h += `<h2>Final video</h2><div class="player"><video id="video" controls preload="metadata" src="${D.final.src}?v=${D.final.v}"></video>
      <div class="checks">${Object.entries(D.final.checks).map(([k, ok]) => `<span class="chip ${ok ? "" : "bad"}">${esc(k)} ${ok ? "ok" : "check"}</span>`).join("")}</div>
      <div class="here"><input id="hereText" placeholder="Pause the video where something should change, write it here…"><button id="hereAdd">Add at <span id="hereT">0:00</span></button></div></div>`;
  }
  if (D.confirm.length) h += `<h2>To confirm</h2><ul class="confirm">${D.confirm.map(c => `<li>${esc(c)}</li>`).join("")}</ul>`;
  if (D.beats.length) h += `<h2>Beats (${D.beats.length})</h2>` + D.beats.map(beatCard).join("");
  if (store.times.length) h += `<h2>Requests at a time</h2><ul class="confirm" id="times">${store.times.map((r, i) => `<li>${mmss(r.t)} ${esc(r.text)} <a class="time" data-del="${i}">remove</a></li>`).join("")}</ul>`;
  if (D.footage.length) h += `<details><summary>Footage every 10 seconds (${D.footage.length} frames)</summary><div class="foot">${D.footage.map(f =>
      `<div><img loading="lazy" src="${f.file}" style="width:100%;border-radius:6px"><b>${mmss(f.t)}</b> ${esc(f.shot)} · ${esc(f.text).slice(0, 90)}</div>`).join("")}</div></details>`;
  if (D.revisions) h += `<details><summary>Change requests so far</summary><pre>${esc(D.revisions)}</pre></details>`;
  app.innerHTML = h;
  updateBar();
}
function requests() {
  const out = [];
  for (const b of D.beats) { const v = (store.beats[b.n] || "").trim(); if (v) out.push(`beat ${b.n} (${mmss(b.start)}): ${v.replace(/\s*\n\s*/g, " ")}`); }
  for (const r of store.times) out.push(`${mmss(r.t)}: ${r.text}`);
  return out;
}
function updateBar() {
  const n = requests().length;
  $("#req").style.display = n ? "block" : "none";
  $("#reqn").textContent = `${n} change request${n === 1 ? "" : "s"} written. Copy them and paste into Claude Code.`;
}
function toast(t) { const el = $("#toast"); el.textContent = t; el.style.display = "block"; setTimeout(() => el.style.display = "none", 3500); }
async function copy(text) {
  try { await navigator.clipboard.writeText(text); }
  catch (e) { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove(); }
  toast("Copied. Paste it into Claude Code and press Enter.");
}
document.addEventListener("input", e => { if (e.target.dataset.beat) { store.beats[e.target.dataset.beat] = e.target.value; save(); } });
document.addEventListener("click", e => {
  const t = e.target.closest("[data-t]"), del = e.target.closest("[data-del]");
  if (del) { store.times.splice(+del.dataset.del, 1); save(); render(); return; }
  if (t && t.tagName === "A") { const v = $("#video"); if (v) { v.currentTime = +t.dataset.t; v.play(); v.scrollIntoView({behavior: "smooth", block: "center"}); } }
  if (e.target.id === "approve") copy(`/approve ${D.folder} ${D.approve}`);
  if (e.target.closest("#hereAdd")) { const v = $("#video"), x = $("#hereText"); if (x.value.trim()) { store.times.push({t: v.currentTime, text: x.value.trim()}); x.value = ""; save(); render(); } }
});
$("#copy").onclick = () => copy(`/change ${D.folder} ${requests().join("; ")}`);
$("#clear").onclick = () => { if (confirm("Clear the requests written on this page?")) { store = {beats: {}, times: []}; save(); render(); } };
render();
setInterval(() => { const v = $("#video"), s = $("#hereT"); if (v && s) s.textContent = mmss(v.currentTime); }, 300);
</script></body></html>
"""
