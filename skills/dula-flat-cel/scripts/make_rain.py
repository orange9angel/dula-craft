#!/usr/bin/env python3
"""Draw three rain layers to cycle as an overlay. Run from the film folder.

  python make_rain.py [--amount 170] [--slant 0.22] [--names rain_a,rain_b,rain_c]

Use them in film.json as: {"overlay": true, "cels": ["rain_a", "rain_b", "rain_c"]}
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _bootstrap  # noqa: E402

_bootstrap.ensure("PIL")
from PIL import Image, ImageDraw  # noqa: E402

SMOOTH = 2  # drawn larger, then scaled down, so the streaks have soft edges


def main():
    _bootstrap.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--amount", type=int, default=170, help="streaks per layer")
    ap.add_argument("--slant", type=float, default=0.22, help="sideways lean of each streak")
    ap.add_argument("--names", default="rain_a,rain_b,rain_c")
    args = ap.parse_args()

    width, height = 1440, 1080
    film = Path("config/film.json")
    if film.exists():
        data = json.loads(film.read_text(encoding="utf-8"))
        width, height = data.get("width", width), data.get("height", height)
    folder = Path("assets/flat")
    folder.mkdir(parents=True, exist_ok=True)
    for seed, name in enumerate(args.names.split(","), 1):
        rng = random.Random(seed)
        image = Image.new("RGBA", (width * SMOOTH, height * SMOOTH), (226, 240, 255, 0))
        draw = ImageDraw.Draw(image)
        for _ in range(args.amount):
            x, y = rng.randint(-60, width) * SMOOTH, rng.randint(-60, height) * SMOOTH
            length = rng.randint(36, 84) * SMOOTH
            draw.line([(x, y), (x - length * args.slant, y + length)],
                      fill=(226, 240, 255, rng.randint(95, 165)), width=rng.choice((2, 2, 3)) * SMOOTH)
        image.resize((width, height), Image.LANCZOS).save(folder / f"{name}.png")
        print(f"Done: {folder / (name + '.png')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
