#!/usr/bin/env python3
"""Light flat cels for a scene, in flat language: ambient colour, a hard-edged rim on the side
facing the key light, and a flat cast shadow on the floor. Run from the film folder.

  light_cels.py --rigs config/lights.json --rig bureau_lamp --cels zl_reach,zl_reach_m1,...
  light_cels.py --rigs config/lights.json --all-used config/film.json      every (cel, rig) pair film.json asks for

Writes assets/flat/<cel>@<rig>.png next to the original, same canvas size, so film.json uses
"zl_reach@bureau_lamp" and the renderer scales it exactly like the original. Every mouth/blink
state of a drawing gets the identical treatment (the rim and shadow come from the silhouette, which
the states share), so swapping states never flickers the light.

Rig (config/lights.json):
  {"bureau_lamp": {
     "ambient": [0.86, 0.82, 0.95],            multiply on the drawing (scene light colour/level)
     "rim": {"to_light": [-0.5, -1.0],          direction from the figure towards the light (x right, y down);
                                                may be a LIST of rims for several lights (e.g. two moons)
             "color": [255, 214, 150], "width": 0.010, "opacity": 0.85, "inset": 0.004},
     "shadow": {"color": [40, 30, 55], "opacity": 0.35, "length": 0.35, "shear": -0.8,
                "contact": 0.45}}}
  width/inset/length are fractions of the figure height. Lines (dark pixels) are never painted over.
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

LINE_LUMA = 70  # outline pixels stay black


def figure_box(a):
    ys, xs = np.where(a > 40)
    return (ys.min(), ys.max(), xs.min(), xs.max()) if len(ys) else None


def rim_mask(a, to_light, width, inset):
    """Pixels inside the figure whose neighbour towards the light is outside: a hard band."""
    inside = a > 128
    if inset > 0:
        inside = ndimage.binary_erosion(inside, iterations=max(1, int(inset)))
    v = np.array(to_light, float)
    v /= np.linalg.norm(v) or 1
    band = np.zeros_like(inside)
    steps = max(1, int(width))
    for k in range(1, steps + 1):
        dx, dy = int(round(v[0] * k)), int(round(v[1] * k))
        shifted = np.zeros_like(inside)
        h, w = inside.shape
        ys0, ys1 = max(0, -dy), min(h, h - dy)
        xs0, xs1 = max(0, -dx), min(w, w - dx)
        shifted[ys0:ys1, xs0:xs1] = inside[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
        band |= inside & ~shifted
    # keep it a clean flat shape: drop specks
    band = ndimage.binary_opening(band, iterations=1)
    return band


def cast_shadow(a, box, sh):
    """Silhouette flattened onto the floor from the feet, sheared, plus a contact ellipse."""
    h, w = a.shape
    y0, y1, x0, x1 = box
    fig_h = y1 - y0
    sil = (a > 128).astype(np.uint8)
    length = sh.get("length", 0.35)
    shear = sh.get("shear", -0.8)
    out = np.zeros((h, w), bool)
    ys, xs = np.nonzero(sil[y0:y1 + 1])
    if len(ys):
        up = (y1 - y0) - ys  # height above the feet
        ny = (y1 - up * length).astype(int)            # lies on the floor, going back (up the image)
        nx = (xs + x0 + up * length * shear).astype(int)
        ok = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
        out[ny[ok], nx[ok]] = True
        out = ndimage.binary_closing(out, iterations=3)
        out = ndimage.binary_fill_holes(out)
    c = sh.get("contact", 0.45)
    if c:
        feet = np.nonzero(sil[max(y1 - int(fig_h * 0.04), 0):y1 + 1].any(axis=0))[0]
        if len(feet):
            cx, rx = (feet.min() + feet.max()) / 2, (feet.max() - feet.min()) / 2 * (1 + c * 0.3) + 4
            ry = max(4, fig_h * 0.018)
            yy, xx = np.ogrid[:h, :w]
            out |= ((xx - cx) / rx) ** 2 + ((yy - y1) / ry) ** 2 <= 1
    return out & (a <= 128)


def light(path, rig, out):
    im = Image.open(path).convert("RGBA")
    arr = np.array(im).astype(np.float32)
    a = arr[..., 3]
    box = figure_box(a)
    if box is None:
        im.save(out)
        return
    fig_h = box[1] - box[0]
    rgb = arr[..., :3]
    luma = rgb @ [0.299, 0.587, 0.114]
    amb = np.array(rig.get("ambient", [1, 1, 1]), np.float32)
    rgb = np.clip(rgb * amb, 0, 255)
    rims = rig.get("rim")
    rims = rims if isinstance(rims, list) else ([rims] if rims else [])   # a list = several key lights
    for rim in rims:
        band = rim_mask(a, rim["to_light"], rim.get("width", 0.01) * fig_h, rim.get("inset", 0.004) * fig_h)
        band &= luma > LINE_LUMA
        col = np.array(rim["color"], np.float32)
        op = rim.get("opacity", 0.85)
        rgb[band] = rgb[band] * (1 - op) + col * op
    res = np.dstack([rgb, a])
    sh = rig.get("shadow")
    if sh:
        m = cast_shadow(a, box, sh)
        col = np.array(sh["color"], np.float32)
        res[m, :3] = col
        res[m, 3] = 255 * sh.get("opacity", 0.35)
    Image.fromarray(res.clip(0, 255).astype(np.uint8)).save(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rigs", required=True)
    ap.add_argument("--rig")
    ap.add_argument("--cels", default="")
    ap.add_argument("--all-used", help="film.json: light every name@rig it references")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    rigs = json.loads(Path(a.rigs).read_text(encoding="utf-8"))
    jobs = []
    if a.all_used:
        text = Path(a.all_used).read_text(encoding="utf-8")
        for name, rig in sorted(set(re.findall(r'"([A-Za-z0-9_]+)@([A-Za-z0-9_]+)"', text))):
            base = Path("assets/flat") / f"{name}.png"
            # every state of the drawing gets the same light
            for p in sorted(Path("assets/flat").glob(f"{name}*.png")):
                if "@" not in p.stem and (p.stem == name or re.fullmatch(rf"{name}_(m\d|blink|closed)", p.stem)):
                    jobs.append((p, rig))
            if not base.exists():
                print("missing", base)
    else:
        for name in filter(None, a.cels.split(",")):
            jobs.append((Path("assets/flat") / f"{name}.png", a.rig))
    for src, rig in jobs:
        out = src.with_name(f"{src.stem}@{rig}.png")
        if out.exists() and not a.force and out.stat().st_mtime > src.stat().st_mtime:
            continue
        light(src, rigs[rig], out)
        print("lit", out.name)


if __name__ == "__main__":
    main()
