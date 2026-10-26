/* Registry family (design §7.4): HyperFrames registry items vendored into global/registry/ (fzv registry add) and mounted by
   HyperFrames into a static host built by fzv. This side only times the host's visibility and gives it a validation role. */
(function () {
  const R = FZ.register;
  R({ name: "hf", family: "registry", layers: ["plate", "studio"],
      doc: "Mount an installed HyperFrames registry item (fzv registry list) in a box: its variables set the content, `cues` (word anchors) time its steps.",
      params: { item: "registry item name", at: "", until: "", box: "x, y, w, h", vars: "{variable: value} (see fzv registry list)", cues: "[times] for items with a `cues` variable (one per step)" } }, (a, p) => {
    const h = document.getElementById(p._host);
    if (!h) throw new Error(`registry host for "${p.item}" missing (rebuild)`);
    h.setAttribute("data-fz", "block");
    a.set(h, p.at, { autoAlpha: 1 }); a.set(h, a.until(p), { autoAlpha: 0 });
  });
})();
