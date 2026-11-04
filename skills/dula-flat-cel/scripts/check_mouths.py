#!/usr/bin/env python3
"""After a full render: for every line, did the speaker's drawing actually change while they talked?
Run from the film folder. Exit code 1 if any visible speaker's mouth froze."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _bootstrap  # noqa: E402


def main():
    _bootstrap.utf8_console()
    if not Path("build/displayed.json").exists():
        sys.exit("[ERROR] Run a full render.py first (without --range)")
    sheet = json.loads(Path("build/sheet.json").read_text(encoding="utf-8"))
    states = json.loads(Path("build/displayed.json").read_text(encoding="utf-8"))
    fps = sheet["fps"]
    frozen = 0
    for lid, at in sorted(sheet["lines"].items(), key=lambda kv: kv[1]):
        who = sheet["who"].get(lid)
        length = len(sheet["env"][lid])
        if not any(sheet["env"][lid]):
            print(f"{lid} {who}: no audio, skipped")
            continue
        first = round(at * fps)
        # Only a change of mouth counts. A walk cycle swapping drawings is not a talking mouth.
        frames = [[item for item in frame["shown"] if item["who"] == who]
                  for frame in states[first:first + length]]
        seen = [tuple(item.get("mouth") for item in items) for items in frames if items]
        swaps = sum(a != b for a, b in zip(seen, seen[1:]))
        seconds = length / fps
        rate = swaps / seconds if seconds else 0
        note = ""
        if not any(seen):
            note = "speaker off screen (voice-over)"
        elif swaps == 0:
            note = "FROZEN MOUTH"
            frozen += 1
        elif rate < 1.5:
            note = "few mouth changes: quiet words may stay closed. See mouth_open_at in the film.json reference"
        print(f"{lid} {who}: {int(at // 60)}:{at % 60:04.1f} length {seconds:.1f}s, {swaps} swaps ({rate:.1f}/s) {note}")
    print(f"Frozen mouths: {frozen}")
    return 1 if frozen else 0


if __name__ == "__main__":
    sys.exit(main())
