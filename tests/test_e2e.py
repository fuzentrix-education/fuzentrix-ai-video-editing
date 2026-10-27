"""End-to-end on a synthetic 8 s rough cut (studio shot, then the plate with the instructor in the corner).
Slow (renders with HyperFrames): run with FZV_E2E=1."""
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(not os.environ.get("FZV_E2E"), reason="set FZV_E2E=1 to run the end-to-end render test")


def fzv(*args):
    p = subprocess.run([str(REPO / "bin" / "fzv"), *map(str, args)], capture_output=True, text=True, cwd=REPO)
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout


def test_end_to_end(tmp_path):
    v = tmp_path / "video"; v.mkdir()
    raw = v / "rough cut.mp4"
    src = ("color=c=#BEBEBE:s=1920x1080:d=3:r=50[st];[st]drawbox=x=800:y=300:w=320:h=600:color=#202830:t=fill[a];"
           "color=c=#F8F8F8:s=1920x1080:d=5:r=50[pl];[pl]drawbox=x=1500:y=760:w=380:h=320:color=#202830:t=fill[b];[a][b]concat=n=2:v=1:a=0[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-filter_complex", src, "-f", "lavfi", "-i", "sine=f=220:d=8", "-map", "[v]", "-map", "0:a",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", raw], check=True)
    (v / "prompt.md").write_text("# E2E\nReview: off\n")        # no editor here to approve; the gates are tested in test_core
    fzv("ingest", v, "--no-transcribe")
    cuts = json.loads((v / "edit" / "cuts.json").read_text())
    assert [c["kind"] for c in cuts] == ["studio", "corner"]
    (v / "edit" / "edit.yaml").write_text("""title: E2E
sections:
  - id: s1
    range: [3.0, 8.0]
    scenes:
      - header: { label: Test, title: "End to *end*", at: 3.2, until: 7.8 }
      - card: { text: "A **card** in the main slot", at: 3.6, until: 7.8 }
studio:
  - studio-tag: { text: "Studio *tag*", at: 0.4, until: 2.8 }
""")
    fzv("plan", v, "--check")
    fzv("build", v)
    out = fzv("validate", v)
    assert "OK" in out, out
    (v / "edit" / "beats.yaml").write_text("""beats:
  - {id: b01, start: 0, end: 3.0, shot: studio, idea: Intro, show: A studio tag, templates: [studio-tag], sync: [0.4]}
  - {id: b02, start: 3.0, end: 8.0, shot: corner, idea: The topic, show: A header and a card, templates: [header, card], sync: [3.2, 3.6]}
""")
    fzv("storyboard", v)
    assert (v / "edit" / "review" / "storyboard" / "b02.jpg").exists() and (v / "edit" / "out" / "storyboard.jpg").exists()
    fzv("render", v)
    fzv("finish", v)
    out = fzv("verify", v)
    assert (v / "E2E - Edited.mp4").exists() and "OK" in out
    page = (v / "edit" / "review" / "index.html").read_text()
    assert "E2E - Edited.mp4" in page and (v / "edit" / "review" / "final" / "b02.jpg").exists()
