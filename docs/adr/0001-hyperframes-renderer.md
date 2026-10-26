# 0001: HyperFrames renders the graphics

**Status:** accepted (2026-10-21). **Scope:** this repo only.

**Context.** The content kit's ADR 0006 chose Revideo for animation templates. Every video edited so far (DBMS trail, Durga trail, Loop Control) was rendered with HyperFrames (HTML + GSAP), including transparent overlays composited over an editor's rough cut.

**Decision.**
- **Renderer:** HyperFrames, pinned at 0.8.162, renders all graphics in this repo.
- **Format:** templates are plain JS registered into a small runtime (`runtime/lib.js`).
- **Output:** clips render as transparent VP9 WebM at 25 fps and are composited with ffmpeg at the source frame rate.

**Consequences.**
- One stack for templates, previews (snapshots) and DOM-based rule checks: the same page is sampled by headless Chrome.
- The content kit keeps ADR 0006. If it moves to HyperFrames later, these templates can be shared.
