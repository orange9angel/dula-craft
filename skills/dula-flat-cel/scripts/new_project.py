#!/usr/bin/env python3
"""Create an empty film folder: python new_project.py my_film"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _bootstrap  # noqa: E402

STYLE = (
    "STYLE LOCK: classic TV cartoon cel. Thin clean uniform black ink outline with slight hand-drawn "
    "weight variation. Completely flat solid colour fills: no gradients, no airbrush, no soft shading, "
    "no texture, no rim light, no 3D look, no painterly rendering. At most one hard-edged flat shadow "
    "tone. Simple rounded shapes, very few lines, large plain colour areas. Expressive squash and "
    "stretch in faces and poses. An original character, not resembling any existing franchise.\n"
)
PLATE_STYLE = (
    "BACKGROUND STYLE: soft hand-painted watercolour background for a TV cartoon, gentle washes, "
    "simple readable shapes, no characters, no text, no logos, no people.\n"
)
FILM = {
    "width": 1440,
    "height": 1080,
    "fps": 24,
    "plates": {"room": "assets/plates/room.png"},
    "ambience": {},
    "bgm": None,
    "voices": {"hero": {"desc": "Describe the voice here: age, tone, breath, pace"}},
    "lines": [
        {"id": "l01", "who": "hero", "text": "Write the line here."},
    ],
    "shots": [
        {
            "id": "S1",
            "plate": {"key": "room", "height": 1080, "x": 720, "y": 1080},
            "hold": 3,
            "lines": ["l01"],
            "actors": [{"who": "hero", "cels": ["hero_stand"], "cx": 720, "ground": 1000, "height": 760}],
        }
    ],
}
FOLDERS = [
    "assets/anchors", "assets/cels/raw", "assets/cels/locked", "assets/flat", "assets/plates",
    "audio/voice", "audio/sfx", "audio/music", "config", "build", "output",
]


def main():
    _bootstrap.utf8_console()
    if len(sys.argv) != 2:
        sys.exit("Usage: python new_project.py <folder>")
    root = Path(sys.argv[1])
    if (root / "config" / "film.json").exists():
        sys.exit(f"{root} is already a project. Nothing was overwritten.")
    for folder in FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / "story.md").write_text("# Story\n\nOne-sentence summary:\n\n## Beats\n", encoding="utf-8")
    (root / "config/style.txt").write_text(STYLE, encoding="utf-8")
    (root / "config/plate_style.txt").write_text(PLATE_STYLE, encoding="utf-8")
    (root / "config/film.json").write_text(json.dumps(FILM, ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ("anchors", "cels", "variants", "plates"):
        (root / f"config/{name}.tsv").write_text("", encoding="utf-8")
    print(f"Project created: {root}")


if __name__ == "__main__":
    main()
