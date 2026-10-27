# Third-party asset licences

Every asset in `global/` that Fuzentrix didn't make records its source URL and licence: props in `global/props/manifest.yaml`,
icons as `data-source` / `data-licence` on their `<symbol>` in `runtime/icons.svg`, music in `global/music/manifest.yaml`.
All of them allow commercial use and edits without a credit in the video (design §9d).

| Source | Used for | Licence | Notice |
|---|---|---|---|
| Tabler Icons 3.49.0 (tabler.io) | 79 line icons in `runtime/icons.svg` | MIT | [tabler-icons-MIT.txt](tabler-icons-MIT.txt) |
| Microsoft Fluent Emoji, flat (github.com/microsoft/fluentui-emoji) | 106 props and characters in `global/props/svg/`, recoloured to the brand | MIT | [fluentui-emoji-MIT.txt](fluentui-emoji-MIT.txt) |
| HyperFrames registry (github.com/heygen-com/hyperframes) | 31 animated components and blocks in `global/registry/` (mounted with the `hf` template) | Apache-2.0 | [hyperframes-registry-Apache-2.0.txt](hyperframes-registry-Apache-2.0.txt) |
| Kenney: Interface Sounds + UI Audio (kenney.nl) | 90 UI sounds in `global/sfx/` (click, tick, blip, pop, good, bad, ding, chime, swish, type) | CC0 1.0 | none required |
| Freesound via Openverse (ludvique, Kinoton, LloydEvans09, adh.dreaming, qubodup, Sclolex) | 7 soft whooshes in `global/sfx/whoosh/` | CC0 1.0 | none required |
| Wikimedia Commons: Satie, Gymnopédie No. 1 (Musopen, Robin Alciatore) | `global/music/calm-piano.m4a` | Public domain | none required |
| Wikimedia Commons: Bach–Siloti, Prelude in B minor (Felipe Sarro) | `global/music/focus-piano.m4a` | CC0 1.0 | none required |

The MIT and Apache-2.0 licences ask that their notice stays with copies of the files; keep this folder with the library. Re-fetch or audit the set
with `scripts/fetch_free_assets.py`.
