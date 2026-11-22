#!/usr/bin/env python3
"""Contact tile + section timeline for a director pass.

  python review_tile.py film.mp4 [--every 2] [--sections sections.json] [--out tile.png]

sections.json (optional): {"sections": [{"t0": 0.0, "t1": 8.5, "part": "intro"}, ...]}

Writes a labelled tile (one frame every N seconds, time stamp + section name) so monotony, dead stretches and rhythm
problems are visible at a glance. Needs ffmpeg and Pillow.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--every", type=float, default=2.0)
    ap.add_argument("--sections", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--cols", type=int, default=10)
    a = ap.parse_args()
    v = Path(a.video)
    secs = []
    if a.sections and Path(a.sections).exists():
        secs = json.load(open(a.sections, encoding="utf-8")).get("sections", [])
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)],
                               capture_output=True, text=True).stdout.strip())
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-vf", f"fps=1/{a.every},scale=320:180",
                        str(Path(td) / "f_%04d.png")], check=True)
        fs = sorted(Path(td).glob("f_*.png"))
        rows = (len(fs) + a.cols - 1) // a.cols
        tile = Image.new("RGB", (320 * a.cols, 196 * rows), "black")
        d = ImageDraw.Draw(tile)
        for i, f in enumerate(fs):
            t = i * a.every
            x, y = (i % a.cols) * 320, (i // a.cols) * 196
            tile.paste(Image.open(f), (x, y))
            part = next((s.get("part", "") for s in secs if s["t0"] <= t < s["t1"]), "")
            d.text((x + 4, y + 182), f"{t:5.1f}s {part}"[:44], fill="white")
    out = Path(a.out) if a.out else v.with_name(v.stem + "_tile.png")
    tile.save(out)
    print(f"wrote {out} ({len(fs)} frames, {dur:.1f} s)")


if __name__ == "__main__":
    main()
