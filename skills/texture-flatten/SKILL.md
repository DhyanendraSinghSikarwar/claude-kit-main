---
name: texture-flatten
description: >
  Flatten PBR or photo texture packs (paper, leather, fabric, metal, wood, stone,
  rubber, etc.) into neutral, seamless, tint-ready textures for UI/graphic use.
  ALWAYS use this skill whenever the user wants to make textures "colourless",
  "neutral", "grayscale", "tintable", or usable with "any accent colour"; whenever
  they upload texture packs / PBR zips (ambientCG, Poly Haven, TextureCan, cc0-textures)
  and want them tiled or recoloured; or whenever they ask for seamless background
  tiles or texture overlays for CSS/web/UI. Trigger even if they don't say "flatten" —
  e.g. "make these tile and work with any colour", "turn this pack into a UI texture".
---

# Texture Flatten

Turn raw texture packs into **neutral, seamless, tint-with-any-accent** assets for UI.

Each input pack (a zip or a folder of maps) produces two files:

| Output | What it is | How the user applies it |
|--------|-----------|--------------------------|
| `NAME_tile_gray.png` | Neutral grayscale seamless tile | Tint via a CSS **blend mode** (recommended) |
| `NAME_overlay_alpha.png` | White RGB + alpha (detail in transparency) | Drop over any solid fill, control with `opacity` |

## When to reach for which output
- **Grayscale tile + blend mode** is the default: one file works with *any* accent, retintable anytime in CSS. Primary downside: `multiply` only darkens, so dark accents may need `screen`.
- **Alpha overlay** when they want a texture layer independent of the background colour (e.g. a `::after` layer over a gradient).

## Run it

The whole pipeline is in `scripts/process_textures.py`. Do NOT rewrite the image
math inline — call the script.

```bash
pip install pillow numpy --break-system-packages -q
python scripts/process_textures.py INPUT [INPUT ...] --out OUTDIR --montage montage.png
```

- `INPUT` — a `.zip` or a folder, **one texture per input**. Accepts multiple.
- `--size` — output px (default `1024`; the right size for a repeating tile — 4K source is wasteful for a UI layer, and tiles stay crisp when downscaled).
- `--montage` — writes a 2×2-tiled contact sheet. **Always generate this and view it.**
- `--flatten NAME=DIV` — per-pack flattening override (see tuning below).

## The pipeline (why each step exists)

1. **Pick the base map.** Prefer `displacement`/`height` (evenly lit, pure surface structure). Fall back to **desaturated diffuse/color** only when displacement is too flat (std < 18). Diffuse carries baked lighting *and its own colour*, which fight uniform tinting — so it's the fallback, not the default. (In practice many packs have low-contrast displacement, so diffuse-desat is common and fine.)
2. **High-pass** (subtract a heavy Gaussian blur). Removes low-frequency lighting gradients. This is the single most important step: it's what makes a texture tint *uniformly* and also tightens seams.
3. **Normalize** via percentile clip (robust to outliers) → full 0–255 range.
4. **Recenter mean to 128** so `overlay`/`soft-light` blends tint neutrally.
5. **make_seamless** — offset so edges meet at a center cross, then heal the cross with the original's smooth center (smoothstep mask). The output edges become the original's continuous interior → guaranteed edge continuity.

## Verify visually, not numerically

Per-pixel edge-difference numbers are **misleading for grainy textures** (paper, fabric, stone): high-frequency noise makes edge diffs look large even when the tile is perceptually seamless. Always open the `--montage` and look for a hard line at tile boundaries. Trust your eyes.

## Tuning for stubborn textures

**Directional textures** (regular horizontal/vertical grain — e.g. a running track, brushed metal, plank wood) are the hard case: the eye catches any break in a *regular* pattern that it would ignore in a stochastic one.

- First remedy: flatten harder with a smaller blur radius, e.g. `--flatten running_track=64` (radius = size // 64). This kills intrinsic bright/dark bands that otherwise land on the tile edge.
- If a faint seam remains on the grain's cross-axis, that's a property of the source, not a bug. Don't burn iterations on it. Ship it and tell the user to tile it on one axis only (`background-repeat: repeat-x` for horizontal grain) or use it as a single non-repeating panel.

Contrast this with stochastic textures, which almost always go fully seamless with defaults.

## CSS the user gets

Grayscale tile + blend (recommended):
```css
.textured {
  background-color: #1B4D3E;                 /* any accent */
  background-image: url("paper_tile_gray.png");
  background-size: 160px;                     /* scale to taste */
  background-blend-mode: multiply;           /* screen on dark bg; overlay/soft-light = subtle */
}
```

Alpha overlay:
```css
.wrap { position: relative; background: #1B4D3E; }
.wrap::after {
  content: ""; position: absolute; inset: 0;
  background: url("paper_overlay_alpha.png"); background-size: 160px;
  opacity: .5; mix-blend-mode: multiply; pointer-events: none;
}
```

## Deliver
Save both PNGs per texture to the output dir. If a `present_files`-style tool is
available, also offer a short self-contained `preview.html` with an accent colour
picker + blend-mode dropdown so the user can test any colour live (embed the tiles
as base64 so it works standalone). Include a brief README noting which textures
tile on both axes vs one axis.
