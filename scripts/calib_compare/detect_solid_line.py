#!/usr/bin/env python
"""Detect a solid lane boundary and sample points along it.

The dash fit in ``fit_dash_line.mjs`` needs a second lane boundary to make the
focal length identifiable.  This script extracts that boundary from a frame:
threshold a colour (yellow median line or white edge line), keep the connected
component with the largest vertical extent inside the ROI, fit a robust line,
and sample the median column per row bin.

Example:
  py scripts/calib_compare/detect_solid_line.py videos/frames/belmera_tm30_001.png \
      --color yellow --roi 450,250,640,720 --vmin 300 --vmax 715 \
      --out videos/frames/belmera_solid_yellow.json

The output is a JSON array of ``{"u": ..., "v": ...}`` points, directly usable as
``--solid`` in ``fit_dash_line.mjs``.
"""

from __future__ import annotations

import argparse
import json

import cv2
import numpy as np


def detect(
    image: np.ndarray,
    color: str,
    roi: tuple[int, int, int, int],
    vmin: int,
    vmax: int,
    n_sample: int,
) -> tuple[list[dict[str, float]], dict]:
    h, w = image.shape[:2]
    x0, y0, x1, y1 = roi
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    sub = image[y0:y1, x0:x1]
    b, g, r = (sub[:, :, i].astype(int) for i in range(3))

    if color == "yellow":
        mask = (r > 170) & (g > 125) & (b < 200) & (r - b > 50) & (g - b > 20)
    elif color == "white":
        hi = np.maximum(np.maximum(r, g), b)
        lo = np.minimum(np.minimum(r, g), b)
        mask = (lo > 150) & (hi - lo < 45)
    else:
        raise SystemExit("--color must be yellow or white")

    mask = mask.astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    best = None
    for idx in range(1, n_labels):
        _, _, _, hh, area = stats[idx]
        if area < 80 or hh < 40:
            continue
        yy, xx = np.nonzero(labels == idx)
        vv, uu = yy + y0, xx + x0
        keep = (vv >= vmin) & (vv <= vmax)
        if keep.sum() < 30:
            continue
        span = int(vv[keep].max() - vv[keep].min())
        if best is None or span > best[0]:
            best = (span, uu[keep], vv[keep])
    if best is None:
        return [], {"status": "NO_COMPONENT"}

    _, uu, vv = best
    a, b = np.polyfit(vv.astype(float), uu.astype(float), 1)
    for _ in range(5):
        resid = np.abs(uu - (a * vv + b))
        keep = resid < max(2.5, 3.0 * np.median(resid))
        a, b = np.polyfit(vv[keep].astype(float), uu[keep].astype(float), 1)
    resid = np.abs(uu - (a * vv + b))
    keep = resid < max(2.5, 3.0 * np.median(resid))

    vs = np.linspace(vv[keep].min(), vv[keep].max(), n_sample)
    points = []
    for v in vs:
        sel = keep & (np.abs(vv - v) < 6)
        if sel.sum() >= 2:
            points.append({"u": float(np.median(uu[sel])), "v": float(np.median(vv[sel]))})

    info = {
        "status": "OK",
        "color": color,
        "roi": [x0, y0, x1, y1],
        "component_pixels": int(keep.sum()),
        "v_range": [int(vv[keep].min()), int(vv[keep].max())],
        "line_u_per_v": float(a),
        "line_u_at_v0": float(b),
        "line_rms_px": float(np.sqrt(np.mean((uu[keep] - (a * vv[keep] + b)) ** 2))),
        "points": len(points),
    }
    return points, info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--color", default="yellow", choices=["yellow", "white"])
    ap.add_argument("--roi", default="0,0,10000,10000",
                    help="x0,y0,x1,y1 in image pixels")
    ap.add_argument("--vmin", type=int, default=0)
    ap.add_argument("--vmax", type=int, default=10000)
    ap.add_argument("--n", type=int, default=16, help="number of sampled points")
    ap.add_argument("--out", required=True)
    ap.add_argument("--overlay", default=None,
                    help="optional path for a PNG with the detected line drawn")
    args = ap.parse_args()

    image = cv2.imread(args.image)
    if image is None:
        raise SystemExit(f"cannot read {args.image}")
    roi = tuple(int(x) for x in args.roi.split(","))
    points, info = detect(image, args.color, roi, args.vmin, args.vmax, args.n)

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(points, fh, indent=2)
    print(json.dumps(info, indent=2))

    if args.overlay and points:
        vis = image.copy()
        for p in points:
            cv2.circle(vis, (int(round(p["u"])), int(round(p["v"]))), 3, (0, 0, 255), -1)
        cv2.imwrite(args.overlay, vis)
        print(f"wrote {args.overlay}")


if __name__ == "__main__":
    main()
