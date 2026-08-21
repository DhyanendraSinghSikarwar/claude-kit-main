#!/usr/bin/env python3
"""
Flatten PBR / photo texture packs into tint-ready, seamless UI textures.

For each input pack (a zip or a folder of maps), produces:
  <name>_tile_gray.png     neutral grayscale seamless tile  -> tint via CSS blend
  <name>_overlay_alpha.png white RGB + alpha (detail in transparency) -> drop over any fill

Pipeline (the learnings this encodes):
  1. Pick base map: displacement/height (evenly lit, pure structure) if it has
     enough contrast, else desaturated diffuse/color. Diffuse carries baked
     lighting + its own colour, so it's the fallback, not the default.
  2. High-pass: subtract a heavy Gaussian blur to remove low-frequency lighting
     gradients. This is what makes a texture tint uniformly AND tile better.
     Smaller radius = flatter (use for directional/banded textures).
  3. Normalize: percentile clip (robust to outliers) -> full 0..255 range.
  4. Recenter mean to 128 so overlay/soft-light blends tint neutrally.
  5. make_seamless: offset so edges meet at a center cross, heal the cross with
     the original's smooth center (smoothstep mask). Output edges become the
     original's continuous center -> guaranteed edge continuity.

Caveat this encodes: strongly directional textures (regular horizontal/vertical
grain) resist clean tiling on the cross-axis; the eye catches any break in a
regular pattern. Flag them; recommend repeat-x / repeat-y or single-panel use.

Usage:
  python process_textures.py INPUT [INPUT ...] --out OUTDIR
         [--size 1024] [--montage montage.png]
         [--hp-radius-div N] [--flatten NAME=DIV ...]

  INPUT        a .zip or a folder containing one texture's maps
  --size       output px (default 1024; right size for a repeating tile)
  --montage    write a 2x2-tiled contact sheet for visual seam inspection
  --hp-radius-div  default high-pass divisor: radius = size // N (default 8)
  --flatten    per-pack override, e.g. --flatten running_track=64 (more flattening)
"""
import argparse, os, sys, tempfile, zipfile, glob
import numpy as np
from PIL import Image, ImageFilter

# map-type detection by filename keyword (first match wins)
BASE_KEYS = ["displacement", "height", "_disp", "_disp_"]
DIFF_KEYS = ["diffuse", "albedo", "_color", "color", "basecolor", "_diff", "_diff_"]
CONTRAST_MIN = 18.0   # below this, displacement is too flat -> use diffuse


def find_map(files, keys):
    for f in files:
        low = os.path.basename(f).lower()
        if any(k in low for k in keys):
            return f
    return None


def load_gray(path, size):
    return np.asarray(
        Image.open(path).convert("L").resize((size, size), Image.LANCZOS), float)


def normalize(a, lo=1, hi=99):
    plo, phi = np.percentile(a, lo), np.percentile(a, hi)
    if phi - plo < 1e-6:
        return a
    return np.clip((a - plo) / (phi - plo) * 255, 0, 255)


def highpass(a, radius):
    blur = np.asarray(Image.fromarray(a.astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius=radius)), float)
    return a - blur + 128


def make_seamless(a, frac=0.15):
    h, w = a.shape
    off = np.roll(a, (h // 2, w // 2), (0, 1))   # off's edges = a's smooth center
    fy, fx = int(h * frac), int(w * frac)
    yy = np.abs(np.arange(h) - h // 2)
    xx = np.abs(np.arange(w) - w // 2)
    my = np.clip(1 - yy / fy, 0, 1); my = my * my * (3 - 2 * my)  # smoothstep
    mx = np.clip(1 - xx / fx, 0, 1); mx = mx * mx * (3 - 2 * mx)
    mask = np.maximum(my[:, None], mx[None, :])   # 1 along center seam-cross
    return off * (1 - mask) + a * mask


def collect_maps(path, tmp):
    """Return (name, [jpg/png files]) for a zip or folder input."""
    if path.lower().endswith(".zip"):
        name = os.path.splitext(os.path.basename(path))[0]
        dest = os.path.join(tmp, name)
        with zipfile.ZipFile(path) as z:
            z.extractall(dest)
        root = dest
    else:
        name = os.path.basename(path.rstrip("/"))
        root = path
    files = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        files += glob.glob(os.path.join(root, "**", ext), recursive=True)
    # drop obvious preview thumbnails
    files = [f for f in files if "preview" not in os.path.basename(f).lower()]
    return name, sorted(files)


def clean_name(name):
    # strip resolution / format suffixes for tidy output filenames
    for junk in ("-4K", "_4K", "-4k", "_4k", "-JPG", "_JPG", "-PNG", "_PNG"):
        name = name.replace(junk, "")
    return name.strip("-_").lower() or "texture"


def process(path, out, size, default_div, overrides, montage_tiles):
    name_raw, files = collect_maps(path, TMP)
    name = clean_name(name_raw)
    if not files:
        return (name, "no image maps found", None)

    disp_p = find_map(files, BASE_KEYS)
    diff_p = find_map(files, DIFF_KEYS)

    base, src = None, None
    if disp_p:
        d = load_gray(disp_p, size)
        if float(d.std()) >= CONTRAST_MIN:
            base, src = d, "displacement"
    if base is None:
        pick = diff_p or disp_p or files[0]
        base = load_gray(pick, size)
        src = "diffuse(desat)" if pick == diff_p else f"fallback:{os.path.basename(pick)}"

    div = overrides.get(name, overrides.get(name_raw, default_div))
    base = normalize(highpass(base, max(1, size // div)))
    base = make_seamless(base)

    tile = np.clip(base + (128 - base.mean()), 0, 255).astype(np.uint8)
    Image.fromarray(tile, "L").save(os.path.join(out, f"{name}_tile_gray.png"), optimize=True)

    alpha = (255 - normalize(base)).astype(np.uint8)
    rgba = np.zeros((size, size, 4), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = alpha
    Image.fromarray(rgba, "RGBA").save(os.path.join(out, f"{name}_overlay_alpha.png"), optimize=True)

    if montage_tiles is not None:
        montage_tiles.append((name, tile))
    return (name, src, f"size//{div}")


def build_montage(tiles, path, th=256):
    if not tiles:
        return
    sheet = Image.new("L", (th * 2 * len(tiles) + 20 * len(tiles), th * 2), 255)
    x = 0
    for _, tile in tiles:
        t = Image.fromarray(tile).resize((th, th))
        for i in (0, 1):
            for j in (0, 1):
                sheet.paste(t, (x + i * th, j * th))
        x += th * 2 + 20
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser(description="Flatten texture packs into tint-ready seamless tiles.")
    ap.add_argument("inputs", nargs="+", help="zip(s) or folder(s), one texture each")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--montage")
    ap.add_argument("--hp-radius-div", type=int, default=8)
    ap.add_argument("--flatten", nargs="*", default=[],
                    help="per-pack overrides NAME=DIV (higher DIV = flatter)")
    args = ap.parse_args()

    overrides = {}
    for kv in args.flatten:
        k, _, v = kv.partition("=")
        overrides[clean_name(k)] = int(v)
        overrides[k] = int(v)

    os.makedirs(args.out, exist_ok=True)
    global TMP
    TMP = tempfile.mkdtemp()
    montage_tiles = [] if args.montage else None

    rows = []
    for p in args.inputs:
        rows.append(process(p, args.out, args.size, args.hp_radius_div, overrides, montage_tiles))

    if args.montage:
        build_montage(montage_tiles, args.montage)

    w = max((len(r[0]) for r in rows), default=8) + 2
    print(f"{'pack':<{w}}{'base map':<20}{'flatten'}")
    for n, s, f in rows:
        print(f"{n:<{w}}{s:<20}{f or ''}")
    if args.montage:
        print(f"\nMontage: {args.montage}  (inspect visually — per-pixel seam numbers "
              "lie for grainy textures)")


if __name__ == "__main__":
    main()
