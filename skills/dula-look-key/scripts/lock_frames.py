"""Lock the still parts of same-camera frames to one base frame. Run from the film folder.

  python <skill>/scripts/lock_frames.py BASE VAR1 VAR2 ... [--thr 38] [--dry]

Every integrated frame is a fresh image-model painting, so brick, rust, posters and paving re-render between
frames of one camera and the background "boils" on every drawing swap: parts that should stay still move.
For each variant: register it to the base (SIFT similarity), find the regions that really changed (blurred colour
difference, speckles removed, holes filled, only large components), and composite the variant inside a feathered
mask over the base. Everything outside the mask becomes the base's exact pixels.

Originals are kept once in assets/keys/unlocked/. Masks for review go to build/lock/<var>.png. Names are frame names
in assets/keys (BASE may also be a plate name in assets/plates).
"""
import argparse
import shutil
from pathlib import Path

import cv2
import numpy as np

KEYS = Path("assets/keys")
KEEP = KEYS / "unlocked"
DEBUG = Path("build/lock")


def path_of(name):
    for p in (KEEP / f"{name}.png", KEYS / f"{name}.png", Path("assets/plates") / f"{name}.png"):
        if p.exists():
            return p
    raise SystemExit(f"not found: {name}")


def register(base, var):
    sift = cv2.SIFT_create(contrastThreshold=0.02)
    g1, g2 = (cv2.cvtColor(x, cv2.COLOR_BGR2GRAY) for x in (base, var))
    k1, d1 = sift.detectAndCompute(g1, None)
    k2, d2 = sift.detectAndCompute(g2, None)
    good = [m for m, n in cv2.BFMatcher().knnMatch(d2, d1, k=2) if m.distance < 0.72 * n.distance]
    if len(good) < 30:
        return None, 0
    p2 = np.float32([k2[m.queryIdx].pt for m in good])
    p1 = np.float32([k1[m.trainIdx].pt for m in good])
    M, inl = cv2.estimateAffinePartial2D(p2, p1, method=cv2.RANSAC, ransacReprojThreshold=2.0, maxIters=20000)
    if M is None:
        return None, 0
    s = float(np.hypot(M[0, 0], M[1, 0]))
    if not 0.9 < s < 1.1 or int(inl.sum()) < 40:
        return None, int(inl.sum())
    return M, int(inl.sum())


def change_mask(base, var, thr, min_area=0.0025):
    h, w = base.shape[:2]
    a = cv2.GaussianBlur(base, (0, 0), 2.5).astype(np.int16)
    b = cv2.GaussianBlur(var, (0, 0), 2.5).astype(np.int16)
    d = np.abs(a - b).max(axis=2)
    m = (d > thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > min_area * h * w:
            keep[lab == i] = 1
    # fill holes inside each kept region
    ff = keep.copy() * 255
    pad = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, pad, (0, 0), 128)
    keep[ff == 0] = 1
    # Thin features (a hair tuft, a strap, a tail tip) differ only a little after blurring and fall outside the
    # core; if they belong to the base's character they would survive as fragments (a stray
    # hair tuft of the standing pose once remained on a crouch). Near the core, any raw difference joins the mask.
    raw = np.abs(base.astype(np.int16) - var.astype(np.int16)).max(axis=2) > 18
    near = cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81))).astype(bool)
    halo = (raw & near).astype(np.uint8)
    halo = cv2.morphologyEx(halo, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    keep = np.maximum(keep, halo)
    keep = cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    alpha = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 3.0)
    return np.clip(alpha, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("vars", nargs="+")
    ap.add_argument("--thr", type=int, default=38)
    ap.add_argument("--roi", default="", help="x0,y0,x1,y1 in source px: changes outside are always discarded")
    ap.add_argument("--min-area", type=float, default=0.0025, help="smallest kept change, fraction of the frame")
    ap.add_argument("--dry", action="store_true", help="write masks and previews only")
    a = ap.parse_args()
    KEEP.mkdir(parents=True, exist_ok=True)
    DEBUG.mkdir(parents=True, exist_ok=True)
    base = cv2.imread(str(path_of(a.base)))
    h, w = base.shape[:2]
    for vn in a.vars:
        src = KEYS / f"{vn}.png"
        if not (KEEP / f"{vn}.png").exists():
            shutil.copy2(src, KEEP / f"{vn}.png")
        var = cv2.imread(str(KEEP / f"{vn}.png"))
        if var.shape[:2] != (h, w):
            var = cv2.resize(var, (w, h), interpolation=cv2.INTER_LANCZOS4)
        # Registration is measured but NOT applied: mouth patches were cut from the unwarped frame, so the
        # character's pixels must stay exactly where they are. Measured shifts are 0-2 px.
        M, inl = register(base, var)
        alpha = change_mask(base, var, a.thr, a.min_area)
        if a.roi:
            x0, y0, x1, y1 = (int(v) for v in a.roi.split(","))
            r = np.zeros_like(alpha); r[y0:y1, x0:x1] = 1
            alpha = alpha * cv2.GaussianBlur(r, (0, 0), 6)
        out = (var.astype(np.float32) * alpha[..., None] + base.astype(np.float32) * (1 - alpha[..., None])).round().astype(np.uint8)
        vis = base.copy()
        vis[alpha > 0.5] = (0.45 * vis[alpha > 0.5] + 0.55 * np.array([255, 0, 255])).astype(np.uint8)
        cv2.imwrite(str(DEBUG / f"{vn}.jpg"), np.hstack([cv2.resize(out, (w // 3, h // 3)), cv2.resize(vis, (w // 3, h // 3))]))
        reg = f"measured shift ({M[0,2]:+.1f},{M[1,2]:+.1f}), not applied" if M is not None else f"no registration (inliers {inl})"
        print(f"{a.base} <- {vn}: {reg}, kept from variant {float((alpha > 0.5).mean()):.0%}")
        if not a.dry:
            cv2.imwrite(str(src), out)


if __name__ == "__main__":
    main()
