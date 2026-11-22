#!/usr/bin/env python3
"""Render a dula-flat-cel film with per-shot atmosphere in flat language. Run from the film folder
after build_film.py. Same output and audit log as the public render.py; effects come from
config/fx.json keyed by shot id, drawn over the composed frame (or between plate and actors for
"under" layers).

  render_fx.py [-o out.mp4] [--range a,b] [--stills 1.0,2.5] [--no-fx]

Effect types (coordinates in output pixels; everything moves on twos like the drawings):
  shafts   {"polys": [[[x,y],...], ...], "color": [255,226,170], "opacity": 0.16, "breathe": 0.15}
           hard-edged light beams (window, door gap, lamp cone)
  dust     {"box": [x0,y0,x1,y1], "n": 40, "size": [2,5], "color": [255,236,200], "opacity": 0.8,
            "drift": [3,-6], "seed": 1}    flat motes drifting in light; px per second
  glow     {"at": [[x,y],...], "r": 90, "color": [255,214,150], "opacity": 0.35, "flicker": 0.06}
           the one soft element: lamp bulbs and the sun
  misprint {"box": [x0,y0,x1,y1], "shift": 7, "opacity": 0.55, "wobble": 2, "from": 0, "to": 99}
           example signature effect: cyan/magenta print-registration ghosts of the region
  layer    {"img": "assets/plates/fg.png", "h": 1080, "x": [a,b], "y": [a,b]}  foreground parallax
  vignette {"strength": 0.25}
  grade    {"mul": [1.0, 0.96, 0.9]}      whole-frame light colour (compare with the ungraded film
                                           before using it)
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RENDER = Path(__file__).resolve().parents[2] / "dula-flat-cel/scripts"
sys.path.insert(0, str(RENDER))
import render as R  # noqa: E402


def rnd(seed):
    return np.random.default_rng(seed)


class FX:
    def __init__(self, fx, size, fps):
        self.fx, self.size, self.fps = fx, size, fps
        self.cache = {}

    def layer_img(self, path, h):
        k = (path, h)
        if k not in self.cache:
            im = Image.open(path).convert("RGBA")
            self.cache[k] = im.resize((round(im.width * h / im.height), round(h)), Image.LANCZOS)
        return self.cache[k]

    def apply(self, frame, shot, local, progress, under=False):
        effects = [e for e in self.fx.get(shot["id"], []) if bool(e.get("under")) == under]
        if not effects:
            return frame
        W, H = self.size
        t2 = math.floor(local * self.fps / 2) * 2 / self.fps  # on twos
        img = frame.convert("RGBA")
        for e in effects:
            k = e["type"]
            if "from" in e and not e["from"] <= local < e.get("to", 1e9):
                continue
            if k == "shafts":
                ov = Image.new("RGBA", (W, H))
                d = ImageDraw.Draw(ov)
                op = e.get("opacity", 0.16) * (1 + e.get("breathe", 0.15) * math.sin(t2 * 1.3))
                for poly in e["polys"]:
                    d.polygon([tuple(p) for p in poly], fill=tuple(e.get("color", [255, 226, 170])) + (int(255 * op),))
                img = Image.alpha_composite(img, ov)
            elif k == "dust":
                g = rnd(e.get("seed", 1))
                x0, y0, x1, y1 = e["box"]
                n = e.get("n", 40)
                px, py = g.uniform(x0, x1, n), g.uniform(y0, y1, n)
                sz = g.uniform(*e.get("size", [2, 5]), n)
                ph = g.uniform(0, 6.28, n)
                dx, dy = e.get("drift", [3, -6])
                xs = x0 + (px - x0 + dx * t2 + 6 * np.sin(t2 * 0.7 + ph)) % (x1 - x0)
                ys = y0 + (py - y0 + dy * t2 + 4 * np.cos(t2 * 0.5 + ph)) % (y1 - y0)
                ov = Image.new("RGBA", (W, H))
                d = ImageDraw.Draw(ov)
                col = tuple(e.get("color", [255, 236, 200]))
                for x, y, s, p in zip(xs, ys, sz, ph):
                    a = int(255 * e.get("opacity", 0.8) * (0.55 + 0.45 * math.sin(t2 * 1.7 + p)))
                    d.ellipse((x - s / 2, y - s / 2, x + s / 2, y + s / 2), fill=col + (max(a, 0),))
                img = Image.alpha_composite(img, ov)
            elif k == "glow":
                r = e.get("r", 90)
                ov = Image.new("RGBA", (W, H))
                d = ImageDraw.Draw(ov)
                f = 1 + e.get("flicker", 0.06) * (rnd(int(t2 * 100)).random() - 0.5) * 2
                for x, y in e["at"]:
                    d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(e.get("color", [255, 214, 150])) + (int(255 * e.get("opacity", 0.35) * f),))
                ov = ov.filter(ImageFilter.GaussianBlur(r * 0.45))
                base = np.asarray(img).astype(np.float32)
                o = np.asarray(ov).astype(np.float32)
                al = o[..., 3:4] / 255
                base[..., :3] = 255 - (255 - base[..., :3]) * (1 - al * o[..., :3] / 255)  # screen
                img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
            elif k == "misprint":
                x0, y0, x1, y1 = e["box"]
                reg = img.crop((x0, y0, x1, y1)).convert("RGB")
                arr = np.asarray(reg).astype(np.float32)
                # only drawn lines ghost; a mid-tone wall must not tint (it turned a whole region purple)
                luma = arr @ np.array([0.299, 0.587, 0.114], np.float32)
                ink = np.clip((110 - luma) / 60, 0, 1)[..., None]
                s = e.get("shift", 7)
                w = e.get("wobble", 2) * math.sin(t2 * 2.1)
                base = np.asarray(img).astype(np.float32)
                for (sx, sy), col in (((s + w, -s * 0.4), (0, 174, 239)), ((-s - w, s * 0.4), (236, 0, 140))):
                    ghost = np.zeros_like(base[..., :3])
                    gx, gy = int(x0 + sx), int(y0 + sy)
                    hh, ww = ink.shape[:2]
                    gx0, gy0 = max(gx, 0), max(gy, 0)
                    gx1, gy1 = min(gx + ww, W), min(gy + hh, H)
                    if gx1 <= gx0 or gy1 <= gy0:
                        continue
                    a = ink[gy0 - gy:gy1 - gy, gx0 - gx:gx1 - gx] * e.get("opacity", 0.55)
                    tint = np.array(col, np.float32) / 255
                    seg = base[gy0:gy1, gx0:gx1, :3]
                    base[gy0:gy1, gx0:gx1, :3] = seg * (1 - a * (1 - tint))  # multiply a coloured ink
                img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
            elif k == "layer":
                im = self.layer_img(e["img"], e.get("h", H))
                x = R.lerp(*e.get("x", [W / 2, W / 2]), progress)
                y = R.lerp(*e.get("y", [H, H]), progress)
                img.alpha_composite(im, (round(x - im.width / 2), round(y - im.height)))
            elif k == "vignette":
                yy, xx = np.ogrid[:H, :W]
                rr = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
                m = 1 - e.get("strength", 0.25) * np.clip(rr - 0.35, 0, 1)
                base = np.asarray(img).astype(np.float32)
                base[..., :3] *= m[..., None]
                img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
            elif k == "grade":
                base = np.asarray(img).astype(np.float32)
                base[..., :3] *= np.array(e["mul"], np.float32)
                img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
        return img.convert("RGB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default="output/film.mp4")
    ap.add_argument("--range")
    ap.add_argument("--stills")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--no-fx", action="store_true")
    a = ap.parse_args()
    sheet = json.loads(Path("build/sheet.json").read_text(encoding="utf-8"))
    fxp = Path("config/fx.json")
    fx = FX({} if a.no_fx or not fxp.exists() else json.loads(fxp.read_text(encoding="utf-8")),
            (sheet["width"], sheet["height"]), sheet["fps"])
    layers = R.Layers(sheet)
    fps = sheet["fps"]

    # "under" effects (floor light pools, ground fog) go between the plate and the actors: the
    # renderer's canvas is wrapped so the first placement (the plate) gets them applied.
    current = {}
    Canvas0 = R.Canvas

    class Canvas(Canvas0):
        def __init__(self, w, h):
            super().__init__(w, h)
            self.placed = 0

        def place(self, image, cx, bottom):
            r = super().place(image, cx, bottom)
            self.placed += 1
            if self.placed == 1 and current:
                self.image = fx.apply(self.image.convert("RGB"), current["shot"], current["local"],
                                      current["progress"], under=True).convert("RGBA")
            return r

    R.Canvas = Canvas

    def frame(i):
        t = i / fps
        shot = next((s for s in sheet["shots"] if s["t0"] <= t < s["t1"]), sheet["shots"][-1])
        local = t - shot["t0"]
        span = shot["t1"] - shot["t0"]
        progress = min(1, local / span) if span else 0
        current.update(shot=shot, local=local, progress=progress)
        pl = shot["plate"]
        zoom = None
        if isinstance(pl.get("height"), list) or "height_anim" in pl:
            # Slow push as a CAMERA move: draw the whole frame (plate, actors, mouth patches) at the start
            # size, then scale the finished frame about the plate's anchor with sub-pixel precision.
            # Growing only the plate re-rounded its size and position every step (visible shake) and left
            # patches behind: viewers saw the mouth separate from the face and the push-in shake.
            pl.setdefault("height_anim", pl["height"])
            h0, h1 = pl["height_anim"]
            pl["height"] = h0
            u = local / span if span else 0
            zoom = R.lerp(h0, h1, min(1, u)) / h0
        img, state = R.draw(sheet, layers, i)
        if zoom and zoom != 1:
            ax, ay = pl["x"][0], pl["y"][0]          # plate anchor: bottom centre, as the old push grew
            img = img.transform(img.size, Image.AFFINE, (1 / zoom, 0, ax - ax / zoom, 0, 1 / zoom, ay - ay / zoom),
                                resample=Image.BICUBIC)
        return fx.apply(img, shot, local, progress), state

    if a.stills:
        folder = Path("build/stills")
        folder.mkdir(parents=True, exist_ok=True)
        for v in a.stills.split(","):
            img, state = frame(round(float(v) * fps))
            p = folder / f"t{float(v):07.2f}.png"
            img.save(p)
            print(p, state["shot"], [s["cel"] for s in state["shown"]])
        return
    start, end = 0.0, sheet["dur"]
    if a.range:
        start, end = (float(v) for v in a.range.split(","))
        end = min(end, sheet["dur"])
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{sheet['width']}x{sheet['height']}",
           "-r", str(fps), "-i", "-"]
    mix = Path("build/mix.wav")
    if mix.exists() and not a.no_audio:
        cmd += ["-ss", str(start), "-t", str(end - start), "-i", str(mix), "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out)]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    states = []
    for i in range(round(start * fps), round(end * fps)):
        img, state = frame(i)
        states.append({"frame": i, **state})
        enc.stdin.write(img.tobytes())
        if i % (fps * 5) == 0:
            print(f"{i / fps:.0f}/{end:.0f} s", flush=True)
    enc.stdin.close()
    if enc.wait():
        sys.exit("ffmpeg failed")
    if not a.range:
        Path("build/displayed.json").write_text(json.dumps(states, ensure_ascii=False), encoding="utf-8")
    print("Done:", out)


if __name__ == "__main__":
    main()
