#!/usr/bin/env python3
"""Turn raw drawings into stable flat cels. Run from the film folder.

  python prep_cels.py [--palette config/palette.json]

1. Every drawing in assets/cels is pressed into true flat fills in assets/flat.
2. Every mouth or eye variant is locked onto its base, so only the edit differs.
3. Outside the edit a variant takes the base's exact flat pixels, so fills do not
   flicker when mouths swap.
4. build/check_alpha.png shows everything on magenta. Look at it: bad cutouts show at once.

Palette file: {"skin": [250, 220, 190], ...}. Only colours near an entry snap to it.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _bootstrap  # noqa: E402

_bootstrap.ensure("cv2", "numpy", "PIL")
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

CHANGE = 40      # how different a pixel must be to count as part of the edit
SNAP = 15.0      # wider than this and props get dyed the wrong colour
CLUSTERS = 28
MERGE = 7.0
EDGE = 14.0


def rgba(path):
    return np.array(Image.open(path).convert("RGBA"))


def save(array, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array.astype(np.uint8)).save(path)


def flatten(src, palette):
    """Cluster colours across the whole drawing, pixel by pixel. Regions bounded by ink lines are
    deliberately not used: one gap in a line merges two neighbouring fills and repaints them."""
    rgb, alpha = src[..., :3], src[..., 3]
    fg = alpha > 128
    if not fg.any():
        return src.copy()
    smooth = cv2.bilateralFilter(rgb, 7, 22, 5)
    lab = cv2.cvtColor((smooth / 255).astype(np.float32), cv2.COLOR_RGB2LAB)
    pixels = lab[fg]
    rng = np.random.default_rng(7)
    sample = pixels[rng.choice(len(pixels), min(60000, len(pixels)), replace=False)]
    cv2.setRNGSeed(7)
    k = min(CLUSTERS, len(sample))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 25, 0.2)
    _, _, centres = cv2.kmeans(sample, k, None, criteria, 2, cv2.KMEANS_PP_CENTERS)
    keep = []
    for i in range(len(centres)):
        if all(np.linalg.norm(centres[i] - centres[j]) >= MERGE for j in keep):
            keep.append(i)
    centres = centres[keep]
    nearest = np.linalg.norm(lab[..., None, :] - centres[None, None], axis=-1).argmin(-1)
    colours = cv2.cvtColor(centres[None].astype(np.float32), cv2.COLOR_LAB2RGB)[0] * 255
    if palette is not None:
        palette_lab = cv2.cvtColor((palette / 255)[None], cv2.COLOR_RGB2LAB)[0]
        for i, centre in enumerate(centres):
            distance = np.linalg.norm(palette_lab - centre, axis=1)
            j = int(distance.argmin())
            # Black and grey stay as drawn: hair and props must not pick up a colour.
            if distance[j] < SNAP and centre[0] > 25 and np.hypot(centre[1], centre[2]) > 12:
                colours[i] = palette[j]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gradient = np.hypot(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)) / 4
    flat = (gradient < EDGE) & fg
    out = rgb.copy()
    out[flat] = colours[nearest[flat]].round().astype(np.uint8)
    return np.dstack([out, alpha])


def on_gray(image):
    a = image[..., 3:4] / 255.0
    return cv2.cvtColor((image[..., :3] * a + 128 * (1 - a)).astype(np.uint8), cv2.COLOR_RGB2GRAY)


def lock(base, variant, window):
    """The generator redraws the whole canvas with faint noise and may shift it. Register it, find
    the largest dense blob of strong change, and take only that from the variant."""
    if variant.shape != base.shape:
        size = (base.shape[1], base.shape[0])
        variant = np.array(Image.fromarray(variant).resize(size, Image.LANCZOS))
    gb, gv = on_gray(base), on_gray(variant)
    (dx, dy), _ = cv2.phaseCorrelate(gb.astype(np.float32), gv.astype(np.float32))
    matrix = np.float32([[1, 0, -dx], [0, 1, -dy]])
    variant = cv2.warpAffine(variant, matrix, (variant.shape[1], variant.shape[0]), flags=cv2.INTER_LINEAR)
    gv = on_gray(variant)
    diff = (np.abs(gb.astype(int) - gv) > 45).astype(np.uint8)
    if window:
        x, y, w, h = window
        keep = np.zeros_like(diff)
        keep[y:y + h, x:x + w] = 1
        diff *= keep
    diff = cv2.morphologyEx(diff, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    diff = cv2.dilate(diff, np.ones((25, 25), np.uint8))
    count, _, stats, _ = cv2.connectedComponentsWithStats(diff)
    if count < 2:
        return None, None
    best = 1 + int(np.argmax(stats[1:, 4]))
    x, y, w, h, _ = stats[best]
    margin = 12
    mask = np.zeros(base.shape[:2], np.float32)
    mask[max(y - margin, 0):y + h + margin, max(x - margin, 0):x + w + margin] = 1
    mask = cv2.GaussianBlur(mask, (0, 0), 5)[..., None]
    return base * (1 - mask) + variant * mask, (int(x), int(y), int(w), int(h))


def relock(locked, cel, flat_base, flat_variant):
    """The lock window is wider than the mouth and holds repainted pixels. Only strong change counts
    as the edit, or a patch of clothing shifts colour on every mouth swap."""
    changed = (np.abs(locked.astype(int) - cel.astype(int)).max(2) > CHANGE).astype(np.uint8)
    changed = cv2.morphologyEx(changed, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    changed = cv2.dilate(changed, np.ones((9, 9), np.uint8))
    same = changed == 0
    flat_variant = flat_variant.copy()
    flat_variant[same] = flat_base[same]
    return flat_variant, float((~same).mean() * 100)


def contact_sheet(paths, out, height=420, per_row=8):
    tiles = []
    for path in paths:
        im = Image.open(path).convert("RGBA")
        im = im.resize((max(1, im.width * height // im.height), height), Image.LANCZOS)
        back = Image.new("RGBA", im.size, (255, 0, 255, 255))
        back.alpha_composite(im)
        tiles.append(back.convert("RGB"))
    if not tiles:
        return
    groups = [tiles[i:i + per_row] for i in range(0, len(tiles), per_row)]
    sheet = Image.new("RGB", (max(sum(t.width for t in g) for g in groups), height * len(groups)))
    for r, group in enumerate(groups):
        x = 0
        for tile in group:
            sheet.paste(tile, (x, r * height))
            x += tile.width
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def main():
    _bootstrap.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--palette", default="config/palette.json")
    ap.add_argument("--variants", default="config/variants.tsv")
    args = ap.parse_args()

    palette = None
    if Path(args.palette).exists():
        palette = np.array(list(json.loads(Path(args.palette).read_text(encoding="utf-8")).values()), np.float32)

    flat_dir = Path("assets/flat")
    variants = []
    if Path(args.variants).exists():
        for line in Path(args.variants).read_text(encoding="utf-8").splitlines():
            if line.strip():
                variants.append(line.split("\t"))
    names = {row[0] for row in variants}

    for path in sorted(Path("assets/cels").glob("*.png")):
        if path.stem in names:
            continue
        out = flat_dir / path.name
        if not out.exists() or out.stat().st_mtime < path.stat().st_mtime:
            save(flatten(rgba(path), palette), out)
            print(f"Flattened {path.stem}")

    problems = 0
    for row in variants:
        name, base = row[:2]
        raw = Path(f"assets/cels/raw/{name}.png")
        if not raw.exists():
            print(f"[MISSING] Variant not painted yet: {raw}")
            problems += 1
            continue
        window = tuple(int(v) for v in row[3].split(",")) if len(row) > 3 and row[3].strip() else None
        base_cel = rgba(f"assets/cels/{base}.png")
        locked, rect = lock(base_cel, rgba(raw), window)
        if locked is None:
            print(f"[WARNING] {name} is almost identical to its base, so the edit did not happen. Repaint it.")
            problems += 1
            continue
        locked = locked.astype(np.uint8)
        save(locked, Path(f"assets/cels/locked/{name}.png"))
        flat_variant, own = relock(locked, base_cel, rgba(flat_dir / f"{base}.png"), flatten(locked, palette))
        save(flat_variant, flat_dir / f"{name}.png")
        print(f"Locked {name}: edit at x={rect[0]} y={rect[1]} w={rect[2]} h={rect[3]}, own pixels {own:.2f}%")
        if own > 15:
            print(f"[WARNING] {name} changed a large area. Check it edited the mouth or eyes, not the body. If needed, add a window x,y,w,h as column 4 of variants.tsv.")

    contact_sheet(sorted(flat_dir.glob("*.png")), Path("build/check_alpha.png"))
    print("Review sheet: build/check_alpha.png. Look at it yourself.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
