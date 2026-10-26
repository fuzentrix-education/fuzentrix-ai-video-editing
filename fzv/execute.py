"""Program output on screen is the program's real output (rule E7).

A `terminal` scene with `exec: {code: <code-card id>, stdin: [...]}` runs that card's code at build time and prints exactly what
a terminal shows: the program's output with the typed input echoed where it was read, errors included. Runs are cached by
content hash in edit/runs/.

Python runs with a small shim that echoes input() at the right place, so the transcript is exact and deterministic.
C, C++, Java and JavaScript run on a pseudo-terminal; each stdin line is sent once the program goes quiet (waiting for input).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VERSION = 1
ECHO, ERR = "\x1eIN\x1e", "\x1eERR\x1e"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")
LANG = {"py": "python", "python": "python", "python3": "python", "js": "javascript", "mjs": "javascript", "javascript": "javascript",
        "node": "javascript", "c": "c", "cpp": "cpp", "cc": "cpp", "c++": "cpp", "java": "java"}
MAX_LINES, TIMEOUT = 400, 10.0

PY_SHIM = r'''
import builtins, sys, traceback
ECHO, ERR = "\x1eIN\x1e", "\x1eERR\x1e"
class _Err:
    def write(self, s):
        sys.stdout.write("".join(ERR + p if p.strip() else p for p in s.splitlines(True)))
        return len(s)
    def flush(self):
        sys.stdout.flush()
sys.stderr = _Err()
def _input(prompt=""):
    sys.stdout.write(str(prompt))
    v = sys.stdin.readline()
    if not v:
        raise EOFError("EOF when reading a line")
    v = v.rstrip("\n")
    sys.stdout.write(ECHO + v + "\n")
    return v
builtins.input = _input
try:
    exec(compile(open("main.py", encoding="utf-8").read(), "main.py", "exec"), {"__name__": "__main__"})
except SystemExit:
    raise
except BaseException:
    t, v, tb = sys.exc_info()
    traceback.print_exception(t, v, tb.tb_next)
    sys.exit(1)
'''


def lang_of(name: str | None, title: str | None = None) -> str:
    if name:
        return LANG.get(str(name).lower(), str(name).lower())
    ext = (title or "main.py").rsplit(".", 1)[-1].lower()
    return LANG.get(ext, "python")


def parse(raw: str) -> list[dict]:
    """Terminal text with markers -> [{text, input?, err?}]."""
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    out = []
    for ln in lines:
        d = {}
        if ERR in ln:
            d["err"] = True
            ln = ln.replace(ERR, "")
        if ECHO in ln:
            ln, d["input"] = ln.split(ECHO, 1)
        d["text"] = ln if "input" in d else ln.rstrip()      # keep a prompt's trailing space before the typed input
        out.append(d)
    return out


def _run_py(src: str, stdin: str, tmp: Path) -> tuple[str, int, bool]:
    (tmp / "main.py").write_text(src, encoding="utf-8")
    (tmp / "_fzshim.py").write_text(PY_SHIM, encoding="utf-8")
    try:
        r = subprocess.run([sys.executable, "-u", "-I", "_fzshim.py"], cwd=tmp, input=stdin, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired as e:
        return (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""), -1, True
    return r.stdout + "".join(ERR + l for l in r.stderr.splitlines(True)), r.returncode, False


def _run_pty(cmd: list[str], stdin: str, tmp: Path) -> tuple[str, int, bool]:
    """Run on a pseudo-terminal with echo off; feed each stdin line when the program is quiet, inserting a marked echo."""
    import pty
    import termios
    master, slave = pty.openpty()
    attrs = termios.tcgetattr(slave)
    attrs[3] &= ~termios.ECHO
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    env = dict(os.environ, TERM="dumb", NO_COLOR="1", FORCE_COLOR="0")
    p = subprocess.Popen(cmd, cwd=tmp, stdin=slave, stdout=slave, stderr=slave, close_fds=True, env=env)
    os.close(slave)
    feed = [l + "\n" for l in stdin.splitlines()]
    out, quiet_since, start, timed_out = [], time.time(), time.time(), False
    heard = False          # output since the last feed: a prompt is likely waiting, so feed sooner
    echo = None            # some runtimes (Node readline) echo input themselves; drop that copy
    while True:
        r, _, _ = select.select([master], [], [], 0.05)
        if r:
            try:
                b = os.read(master, 65536)
            except OSError:
                b = b""
            if not b:
                break
            txt = ANSI.sub("", b.decode("utf-8", "replace")).replace("\r\n", "\n").replace("\r", "")
            while echo and txt and txt[0] == echo[0]:     # may arrive split across reads
                txt, echo = txt[1:], echo[1:]
            if txt:
                echo = None
            out.append(txt)
            quiet_since, heard = time.time(), True
        elif p.poll() is not None:
            break
        elif feed and time.time() - quiet_since > (0.3 if heard else 1.5):
            line = feed.pop(0)
            out.append(ECHO + line)
            os.write(master, line.encode())
            quiet_since, heard, echo = time.time(), False, line
        if time.time() - start > TIMEOUT:
            p.kill(); timed_out = True
            break
    os.close(master)
    code = p.wait()
    return "".join(out), code, timed_out


def _compile(cmd: list[str], tmp: Path) -> str | None:
    if not shutil.which(cmd[0]):
        return f"{cmd[0]} is not installed on this machine"
    r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=60)
    return None if r.returncode == 0 else (r.stderr or r.stdout)


def run(lang: str, src: str, stdin: str = "", cache: Path | None = None) -> dict:
    key = hashlib.sha256(json.dumps([VERSION, lang, src, stdin]).encode()).hexdigest()[:16]
    if cache:
        f = cache / f"{key}.json"
        if f.exists():
            return json.loads(f.read_text())
    with tempfile.TemporaryDirectory(prefix="fzrun_") as d:
        tmp = Path(d)
        err = None
        if lang == "python":
            raw, code, to = _run_py(src, stdin, tmp)
        elif lang == "javascript":
            (tmp / "main.js").write_text(src); raw, code, to = _run_pty(["node", "main.js"], stdin, tmp)
        elif lang in ("c", "cpp"):
            fn = "main.c" if lang == "c" else "main.cpp"
            (tmp / fn).write_text(src)
            err = _compile(["cc" if lang == "c" else "c++", fn, "-o", "main", "-lm"], tmp)
            raw, code, to = (ERR + err.replace("\n", "\n" + ERR), 1, False) if err else _run_pty(["./main"], stdin, tmp)
        elif lang == "java":
            m = re.search(r"public\s+(?:final\s+)?class\s+(\w+)", src)
            cls = m.group(1) if m else "Main"
            (tmp / f"{cls}.java").write_text(src)
            err = _compile(["javac", f"{cls}.java"], tmp)
            raw, code, to = (ERR + err.replace("\n", "\n" + ERR), 1, False) if err else _run_pty(["java", cls], stdin, tmp)
        else:
            raw, code, to = ERR + f"no runner for language '{lang}'", 1, False
    lines = parse(raw)
    res = {"lang": lang, "code": src, "stdin": stdin, "exit": code, "timed_out": to, "truncated": len(lines) > MAX_LINES, "lines": lines[:MAX_LINES]}
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f"{key}.json").write_text(json.dumps(res, indent=1))
    return res


def code_cards(spec: dict) -> dict:
    cards = {}
    for sec in spec.get("sections") or []:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            if name == "code-card" and isinstance(p, dict) and p.get("id"):
                cards[p["id"]] = p
    return cards


def line_changes(recorded: list[str], shown: list[str]) -> list[str]:
    import difflib
    out = []
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, recorded, shown, autojunk=False).get_opcodes():
        if op == "replace":
            for k in range(max(a1 - a0, b1 - b0)):
                old = recorded[a0 + k] if a0 + k < a1 else None
                new = shown[b0 + k] if b0 + k < b1 else None
                out.append(f"line {b0 + k + 1}: `{old}` → `{new}`" if old is not None and new is not None else
                           (f"line {b0 + k + 1}: added `{new}`" if new is not None else f"removed `{old}`"))
        elif op == "insert":
            out += [f"line {b0 + k + 1}: added `{shown[b0 + k]}`" for k in range(b1 - b0)]
        elif op == "delete":
            out += [f"removed `{recorded[a0 + k]}`" for k in range(a1 - a0)]
    return out


def corrections(spec: dict, cache: Path) -> None:
    """Code cards that correct the recording (`recorded:` = the lines as typed there): list the changes and, when a terminal runs
    the card, run the recorded code too so a correction that changes the program's output is caught (rule E9)."""
    cards = code_cards(spec)
    runs = {}
    for sec in spec.get("sections") or []:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            if name == "terminal" and isinstance(p, dict) and (p.get("exec") or {}).get("code"):
                runs.setdefault(p["exec"]["code"], []).append(p["exec"])
    for cid, card in cards.items():
        rec = card.get("recorded")
        if not rec:
            continue
        res = {"changes": line_changes(list(rec), list(card.get("lines") or []))}
        lang = lang_of(card.get("lang"), card.get("title"))
        for ex in runs.get(cid, []):
            stdin = ex.get("stdin") or []
            stdin = "".join(str(x) + "\n" for x in (stdin if isinstance(stdin, list) else [stdin]))
            show = lambda r: [l["text"] + (l.get("input") or "") for l in r["lines"]]
            a = show(run(lang, "\n".join(rec) + "\n", stdin, cache))
            b = show(run(lang, "\n".join(card.get("lines") or []) + "\n", stdin, cache))
            if a != b:
                res.update(output_same=False, recorded_output=a[:12], output=b[:12])
                break
            res["output_same"] = True
        card["corrections_result"] = res


def apply(spec: dict, cache: Path) -> list[str]:
    """Fill every exec terminal's `lines` with the program's real output, timed from `exec`. Returns problems."""
    cards, errors = code_cards(spec), []
    for sec in spec.get("sections") or []:
        for s in sec.get("scenes") or []:
            (name, p), = s.items()
            if name != "terminal" or not isinstance(p, dict) or not p.get("exec"):
                continue
            ex, where = p["exec"], f"{sec.get('id')}.terminal{'#' + p['id'] if p.get('id') else ''}"
            if p.get("lines") or p.get("chips") or p.get("input"):
                errors.append(f"{where}: `exec` prints the real output; remove hand-written lines/chips/input")
                continue
            card = cards.get(ex.get("code")) if ex.get("code") else None
            if ex.get("code") and not card:
                errors.append(f"{where}: exec.code '{ex.get('code')}' is not a code-card id"); continue
            src = ex.get("source") or "\n".join(card.get("lines") or []) + "\n"
            lang = lang_of(ex.get("lang") or (card or {}).get("lang"), (card or {}).get("title"))
            stdin = ex.get("stdin") or []
            stdin = "".join(str(x) + "\n" for x in (stdin if isinstance(stdin, list) else [stdin]))
            r = run(lang, src, stdin, cache)
            if r["timed_out"]:
                errors.append(f"{where}: program did not finish in {TIMEOUT:.0f}s (waiting for more stdin, or an endless loop?)")
            elif r["exit"] != 0 and not ex.get("expect_error"):
                last = next((l["text"] for l in reversed(r["lines"]) if l["text"]), "")
                errors.append(f"{where}: program exited with {r['exit']}: {last} (set exec.expect_error: true if the error is the point)")
            if r["truncated"]:
                errors.append(f"{where}: output longer than {MAX_LINES} lines")
            times = list(ex.get("times") or [])
            t = ex.get("at", (p.get("at") or 0) + 0.5)
            pace, after_in = ex.get("pace", 0.08), ex.get("after_input", 0.6)
            lines, prev_input = [], False
            for i, l in enumerate(r["lines"]):
                if i < len(times) and times[i] is not None:
                    t = times[i]
                elif i:
                    t += after_in if prev_input else pace
                d = {"text": l["text"], "at": round(t, 3)}
                if "input" in l:
                    d["input"] = l["input"]
                tones = {int(k): v for k, v in (ex.get("tones") or {}).items()}
                if l.get("err"):
                    d["tone"] = "bad"
                elif i in tones:
                    d["tone"] = tones[i]
                elif ex.get("tone") and "input" not in l:
                    d["tone"] = ex["tone"]
                lines.append(d)
                prev_input = "input" in l
            p["lines"] = lines
            p["exec_result"] = {"lang": lang, "exit": r["exit"], "lines": len(lines)}
    corrections(spec, cache)
    return errors
