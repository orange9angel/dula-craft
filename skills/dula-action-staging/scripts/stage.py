#!/usr/bin/env python3
"""Render a technique / action sequence (anime "special move" staging) from a JSON beat sheet.

  python stage.py move.json -o clip.mp4 [--frames-dir DIR] [--preview N]

Every beat holds ONE approved drawing and adds staging around it: camera push and pan, shake, flash,
bloom on glowing colours, radiating speed lines, a cosmic or flat-colour background swap behind a
transparent cel, an aura that follows the cel's silhouette, afterimages, and two-colour impact frames.
Drawings are never warped: only rigid placement, camera and overlays.

Beat sheet (JSON):
{
  "fps": 24, "size": [1536, 1024],
  "beats": [
    {"image": "k11.png", "frames": 36,                       # hold length (frames at fps)
     "push": [1.0, 1.08], "focus": [0.62, 0.38],           # zoom start/end, zoom centre (0-1)
     "pan": [[0, 0], [-20, 0]],                             # pixel offset start/end
     "bloom": {"color": [230, 40, 30], "tol": 70, "radius": 18, "gain": 1.6, "pulse": 0.25},
     "lines": {"center": [0.6, 0.4], "color": [255, 255, 255], "count": 90, "alpha": 0.5, "inner": 0.18},
     "background": {"kind": "cosmos" | "solid" | "image", "color": [10, 0, 20], "image": "bg.png"},
     "aura": {"color": [255, 60, 30], "width": 22, "alpha": 0.85},   # needs a transparent cel image
     "afterimage": {"count": 3, "offset": [-40, 0], "alpha": 0.35},  # trailing copies of the cel
     "impact": {"dark": [10, 0, 0], "light": [230, 20, 20], "threshold": 110},
     "shake": {"amp": 14, "decay": true}, "flash": {"frames": 3, "amount": 0.9},
     "fade_in": 0, "fade_out": 0}
  ]
}
"""
import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

RNG = np.random.default_rng(7)


def load(path, size):
    im = Image.open(path).convert("RGBA")
    if im.size != tuple(size) and im.getextrema()[3][0] == 255:  # opaque frame: fit to canvas
        im = im.resize(size, Image.LANCZOS)
    return im


def cosmos(size, t, color=(8, 4, 24)):
    w, h = size
    base = np.zeros((h, w, 3), np.float32) + np.array(color, np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    for i, (cx, cy, r, c) in enumerate([(0.3, 0.4, 0.5, (80, 20, 120)), (0.7, 0.6, 0.45, (20, 40, 140)),
                                        (0.5, 0.2, 0.35, (140, 30, 60))]):
        d = np.hypot(xx / w - cx - 0.02 * math.sin(t + i), yy / h - cy)
        base += np.clip(1 - d / r, 0, 1)[..., None] ** 2 * np.array(c, np.float32) * 0.8
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    stars = np.random.default_rng(3).random((420, 3))
    for x, y, s in stars:
        tw = 0.5 + 0.5 * math.sin(t * 4 + s * 20)
        v = int(150 + 105 * tw)
        r = 1 if s < 0.85 else 2
        d.ellipse([x * w - r, y * h - r, x * w + r, y * h + r], fill=(v, v, 255))
    return img.convert("RGBA")


def speed_lines(size, center, color, count, alpha, inner, seed):
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = center[0] * w, center[1] * h
    rng = np.random.default_rng(seed)
    far = math.hypot(w, h)
    for _ in range(count):
        a = rng.random() * 2 * math.pi
        width = rng.uniform(0.004, 0.02)
        r0 = far * rng.uniform(inner, inner + 0.25)
        p = [(cx + math.cos(a) * r0, cy + math.sin(a) * r0),
             (cx + math.cos(a - width) * far, cy + math.sin(a - width) * far),
             (cx + math.cos(a + width) * far, cy + math.sin(a + width) * far)]
        d.polygon(p, fill=(*color, int(255 * alpha * rng.uniform(0.5, 1))))
    return layer


def bloom(img, color, tol, radius, gain):
    a = np.asarray(img.convert("RGB"), np.float32)
    dist = np.abs(a - np.array(color, np.float32)).max(axis=2)
    mask = np.clip(1 - dist / tol, 0, 1)
    glow = Image.fromarray((a * mask[..., None]).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    g = np.asarray(glow, np.float32) * gain
    out = np.clip(a + g, 0, 255).astype(np.uint8)
    return Image.fromarray(out).convert("RGBA")


def aura(cel, color, width, alpha, t):
    m = cel.getchannel("A")
    grown = m.filter(ImageFilter.MaxFilter(width | 1)).filter(ImageFilter.GaussianBlur(width / 2))
    ring = ImageChops.subtract(grown, m)
    a = np.asarray(ring, np.float32) / 255
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    flicker = 0.75 + 0.25 * np.sin(yy / 23 - t * 9 + np.sin(xx / 41 + t * 3) * 2)
    layer = np.zeros((h, w, 4), np.uint8)
    layer[..., :3] = color
    layer[..., 3] = np.clip(a * flicker * alpha * 255 * 1.6, 0, 255).astype(np.uint8)
    return Image.fromarray(layer)


def impact(img, dark, light, threshold):
    g = np.asarray(img.convert("L").filter(ImageFilter.MedianFilter(5)), np.float32)
    m = (g > threshold)[..., None]
    out = np.where(m, np.array(light, np.uint8), np.array(dark, np.uint8)).astype(np.uint8)
    return Image.fromarray(out).convert("RGBA")


def rain(size, R, seed):
    """Screen-space rain streaks, redrawn on twos."""
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = np.random.default_rng(seed)
    ang = math.radians(R.get("angle", 8))
    col = tuple(R.get("color", (190, 210, 255)))
    for _ in range(R.get("count", 260)):
        x, y = rng.random() * w * 1.1 - w * 0.05, rng.random() * h
        ln = R.get("length", 36) * rng.uniform(0.6, 1.4)
        d.line([(x, y), (x + math.sin(ang) * ln, y + math.cos(ang) * ln)],
               fill=(*col, int(255 * R.get("alpha", 0.3) * rng.uniform(0.4, 1))), width=1 + int(rng.random() < 0.2))
    return layer


def title(size, T, u):
    """Centred title lines; fades in over the first third of the beat."""
    from PIL import ImageFont
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = min(1.0, u * 3)
    y = size[1] * T.get("y", 0.42)
    for line, px, col in zip(T["lines"], T.get("sizes", [120, 54]), T.get("colors", [[235, 30, 25], [230, 230, 230]])):
        font = ImageFont.truetype(T.get("font", "C:/Windows/Fonts/msyhbd.ttc"), px)
        bw = d.textlength(line, font=font)
        d.text(((size[0] - bw) / 2, y), line, font=font, fill=(*col, int(255 * a)),
               stroke_width=T.get("stroke", 2), stroke_fill=(0, 0, 0, int(255 * a)))
        y += px * 1.45
    return layer


def camera(img, size, zoom, focus, offset):
    w, h = size
    cw, ch = w / zoom, h / zoom
    fx, fy = focus[0] * w, focus[1] * h
    x0 = min(max(fx - cw * focus[0], 0), w - cw) - offset[0] / zoom
    y0 = min(max(fy - ch * focus[1], 0), h - ch) - offset[1] / zoom
    return img.transform(size, Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC)


def lerp(a, b, u):
    return a + (b - a) * u


def render_beat(beat, size, base_dir, start_index, out_dir, global_t):
    n = int(beat["frames"])
    src = load(base_dir / beat["image"], size) if beat.get("image") else None
    transparent = src is not None and src.getextrema()[3][0] < 255
    zoom0, zoom1 = beat.get("push", [1.0, 1.0])
    pan0, pan1 = beat.get("pan", [[0, 0], [0, 0]])
    focus = beat.get("focus", [0.5, 0.5])
    shake = beat.get("shake")
    flash = beat.get("flash")
    for i in range(n):
        u = i / max(n - 1, 1)
        t = global_t + i / 24
        bg = beat.get("background")
        if bg and bg["kind"] == "cosmos":
            frame = cosmos(size, t, tuple(bg.get("color", (8, 4, 24))))
        elif bg and bg["kind"] == "image":
            frame = load(base_dir / bg["image"], size)
        else:
            frame = Image.new("RGBA", size, (*bg.get("color", (0, 0, 0)), 255) if bg else (0, 0, 0, 255))
        cel = src
        def add_lines(fr):
            L = beat["lines"]
            fr.alpha_composite(speed_lines(size, L.get("center", [0.5, 0.5]), tuple(L.get("color", (255, 255, 255))),
                                           L.get("count", 80), L.get("alpha", 0.5), L.get("inner", 0.2),
                                           seed=start_index + i // 2))  # lines change on twos
            return fr
        if beat.get("lines") and transparent:
            frame = add_lines(frame)  # behind a transparent cel
        if transparent:
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            pos = ((size[0] - cel.width) // 2, (size[1] - cel.height) // 2)
            if beat.get("afterimage"):
                A = beat["afterimage"]
                for k in range(A.get("count", 3), 0, -1):
                    ghost = cel.copy()
                    ghost.putalpha(cel.getchannel("A").point(lambda v, k=k: int(v * A.get("alpha", 0.35) / k)))
                    canvas.alpha_composite(ghost, (pos[0] + A["offset"][0] * k, pos[1] + A["offset"][1] * k))
            layer = Image.new("RGBA", size, (0, 0, 0, 0))
            layer.alpha_composite(cel, pos)
            if beat.get("aura"):
                Au = beat["aura"]
                canvas.alpha_composite(aura(layer, tuple(Au["color"]), Au.get("width", 20), Au.get("alpha", 0.8), t))
            canvas.alpha_composite(layer)
            frame.alpha_composite(canvas)
        elif cel is not None:
            frame = cel.copy() if not bg else frame
            if bg:
                frame.alpha_composite(cel)
        if beat.get("bloom"):
            B = beat["bloom"]
            g = B.get("gain", 1.5) * (1 + B.get("pulse", 0) * math.sin(t * 6))
            frame = bloom(frame, B["color"], B.get("tol", 70), B.get("radius", 16), g)
        if beat.get("impact"):
            I = beat["impact"]
            frame = impact(frame, I["dark"], I["light"], I.get("threshold", 110))
        if beat.get("lines") and not transparent:
            frame = add_lines(frame)  # over an opaque frame, after the impact recolour
        off = [lerp(pan0[0], pan1[0], u), lerp(pan0[1], pan1[1], u)]
        if shake:
            amp = shake["amp"] * ((1 - u) if shake.get("decay") else 1)
            off[0] += RNG.uniform(-amp, amp)
            off[1] += RNG.uniform(-amp, amp)
        frame = camera(frame, size, lerp(zoom0, zoom1, u * u * (3 - 2 * u)), focus, off)
        if beat.get("rain"):
            frame.alpha_composite(rain(size, beat["rain"], start_index + i // 2))
        if beat.get("title"):
            frame.alpha_composite(title(size, beat["title"], u))
        if flash and i < flash.get("frames", 2):
            amt = flash.get("amount", 0.9) * (1 - i / flash.get("frames", 2))
            frame = Image.blend(frame, Image.new("RGBA", size, (255, 255, 255, 255)), amt)
        fi, fo = beat.get("fade_in", 0), beat.get("fade_out", 0)
        k = 1.0
        if fi and i < fi:
            k = i / fi
        if fo and i >= n - fo:
            k = min(k, (n - 1 - i) / fo)
        if k < 1:
            frame = Image.blend(Image.new("RGBA", size, (0, 0, 0, 255)), frame, k)
        frame.convert("RGB").save(out_dir / f"f{start_index + i:05d}.png")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--frames-dir")
    a = ap.parse_args()
    spec_path = Path(a.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    size, fps = tuple(spec.get("size", (1536, 1024))), spec.get("fps", 24)
    frames = Path(a.frames_dir) if a.frames_dir else Path(tempfile.mkdtemp(prefix="stage_"))
    frames.mkdir(parents=True, exist_ok=True)
    idx = 0
    for beat in spec["beats"]:
        idx += render_beat(beat, size, spec_path.parent, idx, frames, idx / fps)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(frames / "f%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", a.out], check=True)
    print(f"wrote {a.out}: {idx} frames, {idx / fps:.2f} s; frames in {frames}")


if __name__ == "__main__":
    sys.exit(main())
