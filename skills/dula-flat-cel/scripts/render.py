#!/usr/bin/env python3
"""Render the film from build/sheet.json. Run from the film folder.

  python render.py                         full film -> output/film.mp4
  python render.py --range 0,20 -o a.mp4   only this stretch, for a pilot
  python render.py --stills 1.0,2.5        just these seconds -> build/stills/*.png

Holds are real: one drawing and one position per hold, so motion stays on 2s and 3s like
hand-drawn TV animation. Every displayed drawing is logged to build/displayed.json, which
check_mouths.py reads. It audits what was shown, not what was planned.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _bootstrap  # noqa: E402

_bootstrap.ensure("PIL")
from PIL import Image  # noqa: E402

OPEN_WIDE = 0.5
OPEN_HALF = 0.14


def lerp(a, b, u):
    return a + (b - a) * u


def seeded(n):
    x = math.sin(n * 127.1) * 43758.5453
    return x - math.floor(x)


class Layers:
    def __init__(self, sheet):
        self.plates = sheet["plates"]
        self.originals = {}
        self.scaled = {}

    def original(self, key, is_plate):
        slot = (key, is_plate)
        if slot not in self.originals:
            path = Path(self.plates[key]) if is_plate else Path(f"assets/flat/{key}.png")
            if not path.exists():
                sys.exit(f"[ERROR] Image not found: {path}")
            self.originals[slot] = Image.open(path).convert("RGBA")
        return self.originals[slot]

    def get(self, key, height, flip=False, tint=None, is_plate=False):
        slot = (key, is_plate, round(height, 1), flip, tuple(tint) if tint else None)
        if slot not in self.scaled:
            im = self.original(key, is_plate)
            size = (max(1, round(im.width * height / im.height)), max(1, round(height)))
            im = im.resize(size, Image.LANCZOS)
            if flip:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            if tint:
                r, g, b, a = im.split()
                r, g, b = (c.point(lambda v, k=k: min(255, int(v * k))) for c, k in zip((r, g, b), tint))
                im = Image.merge("RGBA", (r, g, b, a))
            self.scaled[slot] = im
        return self.scaled[slot]


class Canvas:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.image = Image.new("RGBA", (width, height), (0, 0, 0, 255))

    def place(self, image, cx, bottom):
        """x is the centre of the drawing's canvas and y its bottom edge, in output pixels."""
        left, top = round(cx - image.width / 2), round(bottom - image.height)
        x0, y0 = max(left, 0), max(top, 0)
        x1, y1 = min(left + image.width, self.width), min(top + image.height, self.height)
        if x1 > x0 and y1 > y0:
            self.image.alpha_composite(image.crop((x0 - left, y0 - top, x1 - left, y1 - top)), (x0, y0))


def mouth_key(actor, key, sheet, t, hold, fps):
    states = actor["talk"].get(key)
    if not states:
        return key
    for lid in actor["talk_lines"]:
        envelope = sheet["env"][lid]
        local = t - sheet["lines"][lid]
        if local < 0 or local >= len(envelope) / fps:
            continue
        index = int(local * fps / hold) * hold
        value = envelope[index] if index < len(envelope) else 0
        # A two-state mouth needs a higher threshold, or it stays open through speech.
        if states[1] == states[2]:
            return states[2] if value > OPEN_WIDE else states[0]
        return states[2 if value > OPEN_WIDE else 1 if value > OPEN_HALF else 0]
    return states[0]


def draw(sheet, layers, frame_index):
    fps = sheet["fps"]
    t = frame_index / fps
    shot = next((s for s in sheet["shots"] if s["t0"] <= t < s["t1"]), sheet["shots"][-1])
    local = t - shot["t0"]
    hold = shot.get("hold", 3)
    held = int(round(local * fps) / hold)
    span = shot["t1"] - shot["t0"]
    progress = min(1, local / span) if span else 0

    canvas = Canvas(sheet["width"], sheet["height"])
    plate = shot["plate"]
    canvas.place(layers.get(plate["key"], plate["height"], tint=plate.get("tint"), is_plate=True),
                 lerp(*plate["x"], progress), lerp(*plate["y"], progress))
    shown = []
    for actor in shot["actors"]:
        if "show" in actor and not actor["show"][0] <= local < actor["show"][1]:
            continue
        u = 0
        if actor.get("t0") is not None:
            u = min(1, max(0, (local - actor["t0"]) / (actor["t1"] - actor["t0"])))
        step = math.floor(u * actor["steps"]) / actor["steps"] if actor.get("steps") else u
        key = actor["cels"][held % len(actor["cels"])]
        if "talk" in actor:
            key = mouth_key(actor, key, sheet, t, hold, fps)
        if any(b <= local < b + 0.13 for b in actor.get("blink", [])):
            key = actor["blink_cel"]
        shake_x = shake_y = 0
        if actor.get("shake"):
            shake_x = (seeded(held) - 0.5) * actor["shake"]
            shake_y = (seeded(held + 99) - 0.5) * actor["shake"] * 0.5
        bob = actor["bob"] if actor.get("bob") and held % 2 else 0
        off = actor.get("offs", {}).get(key, [0, 0])
        image = layers.get(key, actor["h"], flip=actor.get("flip", False), tint=actor.get("tint"))
        canvas.place(image, lerp(*actor["x"], step) + shake_x + off[0], lerp(*actor["y"], step) + shake_y - bob + off[1])
        shown.append({"who": actor.get("who"), "cel": key})
    return canvas.image.convert("RGB"), {"shot": shot["id"], "shown": shown}


def main():
    _bootstrap.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default="output/film.mp4")
    ap.add_argument("--range", help="start,end in seconds, e.g. 0,20")
    ap.add_argument("--stills", help="comma-separated seconds")
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()

    if not Path("build/sheet.json").exists():
        sys.exit("[ERROR] Run build_film.py first")
    sheet = json.loads(Path("build/sheet.json").read_text(encoding="utf-8"))
    layers = Layers(sheet)
    fps = sheet["fps"]

    if args.stills:
        folder = Path("build/stills")
        folder.mkdir(parents=True, exist_ok=True)
        for value in args.stills.split(","):
            image, state = draw(sheet, layers, round(float(value) * fps))
            path = folder / f"t{float(value):07.2f}.png"
            image.save(path)
            print(f"{path}  shot {state['shot']}  {[s['cel'] for s in state['shown']]}")
        return 0

    start, end = 0.0, sheet["dur"]
    if args.range:
        start, end = (float(v) for v in args.range.split(","))
        end = min(end, sheet["dur"])
    first, last = round(start * fps), round(end * fps)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{sheet['width']}x{sheet['height']}", "-r", str(fps), "-i", "-"]
    audio = Path("build/mix.wav")
    if audio.exists() and not args.no_audio:
        cmd += ["-ss", str(start), "-t", str(end - start), "-i", str(audio), "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out)]
    encoder = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    states = []
    for index in range(first, last):
        image, state = draw(sheet, layers, index)
        states.append({"frame": index, **state})
        encoder.stdin.write(image.tobytes())
        if (index - first) % (fps * 5) == 0:
            print(f"{index / fps:.0f}/{end:.0f} s", flush=True)
    encoder.stdin.close()
    if encoder.wait():
        sys.exit("[ERROR] ffmpeg encoding failed")
    if not args.range:
        Path("build/displayed.json").write_text(json.dumps(states, ensure_ascii=False), encoding="utf-8")
    print(f"Done: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
