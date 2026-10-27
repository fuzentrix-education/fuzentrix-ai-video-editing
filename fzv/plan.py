"""`fzv plan`: everything Claude needs to write edit/edit.yaml, in one compact brief (edit/plan_brief.md),
plus the template catalogue generated from the runtime itself (global/templates/catalogue.json)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

from .anchors import Transcript
from .config import GLOBAL, REPO, RUNTIME, brand_ids, load_yaml


def catalogue(refresh: bool = False) -> dict:
    f = GLOBAL / "templates" / "catalogue.json"
    newest = max(p.stat().st_mtime for p in (RUNTIME / "templates").glob("*.js"))
    if refresh or not f.exists() or f.stat().st_mtime < newest:
        p = subprocess.run(["node", str(REPO / "node" / "sample.mjs"), "catalogue", str(RUNTIME)], capture_output=True, text=True, cwd=REPO)
        if p.returncode != 0:
            raise RuntimeError(p.stderr[-1500:])
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(json.loads(p.stdout), indent=1))
        write_cards(json.loads(p.stdout))
    return json.loads(f.read_text())


def write_cards(cat: dict):
    """One markdown card per template under global/templates/<family>/ (generated; edit the JS meta instead)."""
    for name, m in cat.items():
        d = GLOBAL / "templates" / m.get("family", "misc")
        d.mkdir(parents=True, exist_ok=True)
        rows = "\n".join(f"| `{k}` | {v} |" for k, v in (m.get("params") or {}).items())
        (d / f"{name}.md").write_text(f"# {name}\n\n**Family:** {m.get('family')} · **Layers:** {', '.join(m.get('layers', []))}\n\n{m.get('doc', '')}\n\n"
                                      f"| Parameter | Meaning |\n|---|---|\n{rows}\n\n_Generated from runtime/templates; edit the template's meta there._\n", encoding="utf-8")


def compact_transcript(path: Path) -> str:
    lines = []
    for l in path.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            lines.append(f"[{r['start']:7.1f}] {r['text']}")
    return "\n".join(lines)


def registry_items() -> list[dict]:
    from .registry import manifest
    return manifest()


def concept_notes(proj) -> list[str]:
    from .concepts import moments
    ms = moments(proj.p("transcript.jsonl"))
    out = ["## Show the process (rules V1–V3)",
           "Every explanation is SHOWN, in step with the words: a new visual roughly every 8–12 s, each step on the word that names it, "
           f"never more than {proj.settings().get('visuals', {}).get('max_text_only_s', 15)} s of words-only screen. Text cards label; animations explain. "
           "Concept → template guide: CLAUDE.md and global/styles/explainer/STYLE.md."]
    if ms:
        out.append("**Concept moments found in the transcript** (cover each with one of the templates, or say in `decisions` why not):")
        out.append("\n".join(f"- {m['t']:7.1f}s  “{m['phrase']}” → {', '.join(m['templates'])}: {m['show']}" for m in ms))
    return out


def recording_notes(proj, pdata: dict, settings: dict) -> list[str]:
    recs = pdata.get("recordings") or []
    if not recs:
        return []
    use = settings.get("recordings", {}).get("use", "show")
    out = ["## Screen recordings", f"**Use: {use}** (prompt field `Recording:`; default show)."]
    if use == "show":
        out.append("Show each recording whole with `recording-window` in the free area of its plate/corner shots; highlight boxes are in "
                   "recording pixels (keyframe pixel + crop offset). Explanations go outside the window, wired with `note`.")
    else:
        out.append(("""The recording is **reference only: never show it** (rule E8). Rebuild what it shows as animation, in step with what the instructor says:
- **Code:** a `code-card` per program, from the last keyframe of that program. Corrections mode **{corr}**: with `tidy`, fix the
  recording's typos, spacing/formatting and false starts, and put the code exactly as typed in `recorded:` so the build lists every change
  and checks the output is unchanged (rule E9; a fix that changes the output needs `logic_fix: <why>` and goes to 'to confirm').
  With `exact`, copy it exactly as typed. Type each line when it appears in the recording (keyframe times below; `fzv look <folder> recN t0-t1` for finer steps),
  or on the word the instructor says it with if that reads better. Press `run` when they click Run.
- **Output:** a `terminal` with `exec: {code: <card id>, stdin: [what the instructor typed into the program]}`. The build runs the code and prints its real
  output, input echoed where it is read (rule E7); time it with `exec.times` / `exec.pace` to match the recording. Never type output by hand.
  Check the result in edit/edit.resolved.yaml against the recording's output keyframe; IDE banners such as "=== Code Execution Successful ===" are not program output.
- **Explanations:** `note` cards outside the code card and terminal, wired to lines.""").replace("{corr}", settings.get("recordings", {}).get("corrections", "tidy")))
    for r in recs:
        idx = proj.edit / "recref" / r["id"] / "index.json"
        if not idx.exists():
            continue
        ix = json.loads(idx.read_text())
        out.append(f"**{r['id']}** `{r['file']}` offset {r['offset']}s, content crop {r['crop']}. Keyframes (settled screen states; raw-cut times) in "
                   f"`edit/recref/{r['id']}/`; overview sheets: {', '.join(ix['sheets'])}. Open single keyframes to read code exactly.")
        out.append("\n".join(f"- k{k['k']:02d} `{k['file']}` settled {k['t_raw']:.1f}s (changing from {k['change_from_raw']:.1f}s, holds until {k['until_raw']:.1f}s)"
                             for k in ix["keyframes"]))
    return out


def brief(proj, settings: dict) -> Path:
    pdata = proj.load()
    cat = catalogue()
    cuts = json.loads(proj.p("cuts.json").read_text()) if proj.p("cuts.json").exists() else []
    tx = proj.p("transcript.jsonl")
    props = load_yaml(GLOBAL / "props" / "manifest.yaml").get("assets", [])
    fam = {}
    for n, m in cat.items():
        fam.setdefault(m.get("family"), []).append(n)
    parts = [
        f"# Plan brief: {proj.folder.name}",
        "Write `edit/edit.yaml` for this video. Read docs/SYSTEM_DESIGN.md §7–§10 for the style families, rules and spec format.",
        "## The video's prompt", proj.prompt().strip() or "(none: use the global defaults)",
        "## Settings (global defaults + prompt)",
        "```yaml\n" + yaml.safe_dump({k: settings[k] for k in ("brand", "mode", "styles", "subtitles", "music", "name_card", "cutaways", "clutter", "empty")}, sort_keys=False) + "```",
        f"Brand kits available: {', '.join(brand_ids())}",
        "## Source",
        f"raw cut: `{pdata.get('raw')}`  duration {pdata.get('duration')}s  fps {pdata.get('fps')}  mode {pdata.get('mode')}",
        "recordings: " + (json.dumps(pdata.get("recordings")) if pdata.get("recordings") else "none"),
        *recording_notes(proj, pdata, settings),
        "## Layout slots (instructor safe zones already removed)", "```json\n" + json.dumps(pdata.get("layout"), indent=1) + "\n```",
        "safe zones: " + json.dumps(pdata.get("zones")),
        "## Shots (cuts.json)",
        "\n".join(f"- {c['kind']:7s} {c['start']:8.2f} – {c['end']:8.2f}  ({c['end'] - c['start']:.1f}s)" for c in cuts),
        "Every studio shot needs a `studio` scene (rule L4). Plate/corner shots must never sit empty for more than "
        f"{settings['empty']['max_gap_s']}s. Clutter budget: {settings['clutter']}.",
        *concept_notes(proj),
        "## Beat sheet first (edit/beats.yaml, rule R1)",
        "`fzv plan` drafted one row per beat (an idea the instructor explains, 8–20 s) from the pauses, shot changes and concept moments. "
        "Before writing edit.yaml, fill every row: `idea` (one plain sentence), `show` (what appears, in plain words for a non-technical editor), "
        "`templates` and `sync` (the words each step lands on). Merge or split rows freely; they must stay contiguous. Then run `fzv beats` and show "
        "the editor the review page; edit.yaml is written only from the approved sheet, scene by scene (rule V4). "
        "The footage every 10 s and at each shot change: `edit/out/footage.jpg`.",
        "## Templates by family", "\n".join(f"- **{f}**: {', '.join(sorted(ns))}" for f, ns in sorted(fam.items())),
        "Full parameters: global/templates/catalogue.json (or the cards in global/templates/<family>/).",
        "## Props library (template `prop`, `prop-move`, `prop-scene`; asset ids)",
        "**characters:** " + ", ".join(a["id"] for a in props if a["kind"] == "character"),
        "**props:** " + ", ".join(a["id"] for a in props if a["kind"] != "character"),
        "## Icons (`icon: <name>` in agenda, chips, cards…)", ", ".join(re.findall(r'symbol id="i-([a-z0-9-]+)"', (RUNTIME / "icons.svg").read_text(encoding="utf-8"))),
        "## Registry animations (template `hf`: `- hf: {item, at, until, box: {x, y, w, h}, vars: {...}, cues: [word anchors]}`)",
        "\n".join(f"- `{x['name']}` ({x['type']}): {x['description'][:110]}" + (f" · vars: {', '.join(v['id'] for v in x.get('variables', []))}" if x.get("variables") else "")
                  for x in registry_items()) or "none installed (fzv registry search / add)",
        "## Music tracks (only when the prompt asks)", ", ".join(f"{t['id']} ({t.get('mood', '')}, {t.get('duration', '?')}s)" for t in
                                                                   (load_yaml(GLOBAL / "music" / "manifest.yaml").get("tracks") or [])) or "none",
        "## Transcript (timing only; English-mode, may be romanised Telugu)",
        "Anchors: write `at: \"@phrase the instructor says\"` (fuzzy match), `\"@phrase#2\"` for the 2nd occurrence, or seconds.",
        "```\n" + (compact_transcript(tx) if tx.exists() else "(not transcribed yet)") + "\n```",
    ]
    out = proj.p("plan_brief.md")
    out.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    return out
