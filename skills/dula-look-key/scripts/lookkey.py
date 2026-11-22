#!/usr/bin/env python3
"""Look-key tools. Run from the film folder.

  lookkey.py key    OUT --plate PLATE --anchor A [--anchor B ...] --staging "who does what, contacts"
  lookkey.py erase  OUT --key KEY [--remove "the boy on the sofa and the woman with the broom"]
  lookkey.py closer OUT --key KEY --view "medium view of the sofa from the front at sitting eye level"
  lookkey.py cel    OUT --anchor A --key KEY --pose "pose, expression, facing"
  lookkey.py check  config/film.json --key KEY [--max-zoom 2.0]

Image generation uses the image route of the neighbouring dula-flat-cel skill (scripts/paint.py).
check prints plate zoom per shot and style statistics against the key; it measures drift,
it does not judge fusion or physical contact.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PAINT = HERE.parents[2] / "dula-flat-cel" / "scripts"

ALPHA = "FULLY TRANSPARENT background (real PNG alpha), no backdrop, no ground, no shadow, no text."


def codex(out, prompt, refs, size=None):
    sys.path.insert(0, str(PAINT))
    from paint import codex_image  # noqa: E402
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    codex_image(out, prompt, [str(r) for r in refs], size)
    receipt = out.with_suffix(".json")
    receipt.write_text(json.dumps({"prompt": prompt, "refs": [str(r) for r in refs], "size": size},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out)


def cmd_key(a):
    names = ", ".join(f"image {i + 2}" for i in range(len(a.anchor)))
    prompt = (f"Image 1 is the background: keep this exact room, layout, camera, colours and flat low-detail cartoon "
              f"painting style. {names} are the characters: keep their exact designs, faces, proportions, line weight "
              f"and flat colours. Draw ONE finished animation frame of the characters physically inside this place: "
              f"{a.staging} Bodies take real weight: seats and cushions dent under a sitter, feet rest on the floor, "
              f"each figure has a soft flat contact shadow where it meets a surface, nearer furniture overlaps what is "
              f"behind it. Characters and place share the same thin dark outline and flat colour style. No text. "
              f"Landscape 3:2.")
    codex(a.out, prompt, [a.plate, *a.anchor])


def cmd_erase(a):
    who = a.remove or "every character"
    prompt = (f"Edit the attached animation frame: remove {who} completely, including their contact shadows and "
              f"anything they hold. Repaint what was hidden so the place is empty and undisturbed (cushions undented, "
              f"floor continuous). Keep every other pixel exactly the same: layout, camera, colours, line weight and "
              f"flat low-detail painting style. No people. Landscape 3:2.")
    codex(a.out, prompt, [a.key])


def cmd_closer(a):
    prompt = (f"The attached frame shows this place. Paint the SAME place, empty of people, from a nearer camera: "
              f"{a.view}. Keep the same objects, colours, outline weight and flat low-detail painting style; the "
              f"closer view shows the same level of detail as the original, not more. No people, no text. Landscape 3:2.")
    codex(a.out, prompt, [a.key])


def cmd_cel(a):
    prompt = (f"Image 1 is the locked character model sheet: keep the exact head, face, proportions, colours and "
              f"clothes. Image 2 is an approved frame of this film: match its outline weight, outline colour, flat "
              f"palette and level of detail. New pose of this character alone, full body: {a.pose} {ALPHA}")
    codex(a.out, prompt, [a.anchor[0], a.key], "1024x1536")


def stats(path):
    import cv2
    import numpy as np
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 4:
        mask = im[..., 3] > 40
        im = im[..., :3]
    else:
        mask = np.ones(im.shape[:2], bool)
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 140) > 0
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
    flat = (~cv2.dilate(edges.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)) & mask
    return {"edge_density": round(float(edges[mask].mean()), 4),
            "saturation": round(float(hsv[..., 1][mask].mean()) / 255, 3),
            "flat_texture": round(float(lap[flat].mean()), 2)}


def cmd_check(a):
    film = json.loads(Path(a.film).read_text(encoding="utf-8"))
    wide = film.get("height", 1080)
    print("== plate zoom (plate height / frame height) ==")
    over = 0
    for s in film["shots"]:
        z = s["plate"].get("height", wide) / wide
        flag = "  OVER" if z > a.max_zoom + 1e-6 else ""
        over += bool(flag)
        print(f"{s['id']:6s} {s['plate']['key']:22s} {z:4.2f}x{flag}")
    print(f"{over} shot(s) above {a.max_zoom}x")
    print("== style against key ==")
    ref = stats(a.key)
    print("key", ref)
    for key, path in film["plates"].items():
        if Path(path).exists():
            st = stats(path)
            print(f"{key:22s}", {k: round(v / ref[k], 2) if ref[k] else None for k, v in st.items()})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("key"); p.add_argument("out"); p.add_argument("--plate", required=True)
    p.add_argument("--anchor", action="append", required=True); p.add_argument("--staging", required=True)
    p = sub.add_parser("erase"); p.add_argument("out"); p.add_argument("--key", required=True); p.add_argument("--remove")
    p = sub.add_parser("closer"); p.add_argument("out"); p.add_argument("--key", required=True); p.add_argument("--view", required=True)
    p = sub.add_parser("cel"); p.add_argument("out"); p.add_argument("--anchor", action="append", required=True)
    p.add_argument("--key", required=True); p.add_argument("--pose", required=True)
    p = sub.add_parser("check"); p.add_argument("film"); p.add_argument("--key", required=True)
    p.add_argument("--max-zoom", type=float, default=2.0)
    a = ap.parse_args()
    {"key": cmd_key, "erase": cmd_erase, "closer": cmd_closer, "cel": cmd_cel, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
