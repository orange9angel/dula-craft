"""Turn locked frames into full-frame transparent layers over their base. Run from the film folder.

  python <skill>/scripts/make_layer.py BASE VAR1 VAR2 ...

A locked variant equals its base outside the changed region, so the layer is the variant where it differs from the
base (feathered), transparent elsewhere. Written to assets/flat/<VAR>_L.png with a box record covering the whole
frame, so a renderer can place it exactly on the plate and two layers alternate without any drift.
The four corner pixels are made opaque (copied from the base) so every layer has the same visible box.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np


def main():
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) > 1 else 2)
    base_n, vars_ = sys.argv[1], sys.argv[2:]
    base = cv2.imread(f"assets/keys/{base_n}.png")
    h, w = base.shape[:2]
    for vn in vars_:
        var = cv2.imread(f"assets/keys/{vn}.png")
        d = np.abs(var.astype(np.int16) - base.astype(np.int16)).max(axis=2) > 3
        m = cv2.dilate(d.astype(np.uint8), np.ones((3, 3), np.uint8))
        alpha = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2)
        alpha = np.clip(alpha * 1.4, 0, 1)
        rgba = np.dstack([var, (alpha * 255).astype(np.uint8)])
        for y, x in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
            rgba[y, x, :3] = base[y, x]
            rgba[y, x, 3] = 255
        out = Path(f"assets/flat/{vn}_L.png")
        cv2.imwrite(str(out), rgba)
        out.with_suffix(".json").write_text(json.dumps({"frame": f"assets/keys/{base_n}.png", "box": [0, 0, w, h]}), encoding="utf-8")
        print(f"{vn}_L: covers {float((alpha > 0.5).mean()):.1%} of the frame")


if __name__ == "__main__":
    main()
