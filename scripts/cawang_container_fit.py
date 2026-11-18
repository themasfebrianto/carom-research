#!/usr/bin/env python
"""Fit a 3D box to a container-only mask in the Cawang camera.

The mask should contain the container side, not the cab. The container height
is fixed to an ISO standard (2.591 m standard, 2.896 m high cube).

Example:
  py scripts\cawang_container_fit.py ^
    --image out\timepass\t247.jpg ^
    --mask out\timepass\gsam2_20ft\container_mask_0.npy ^
    --box 230,450,430,680 --height 2.591
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import differential_evolution

CX, CY, F, H = 640.0, 360.0, 1082.6, 8.876
TH = math.radians(2.432)
S, C = math.sin(TH), math.cos(TH)


def project(p, hc: float, crop, size: int):
    X, Y, Z0, yaw, L, W = p
    x1, y1, x2, y2 = crop
    local = np.array([[-L / 2, -W / 2], [L / 2, -W / 2],
                      [L / 2, W / 2], [-L / 2, W / 2]])
    c, s = math.cos(yaw), math.sin(yaw)
    xy = local @ np.array([[c, s], [-s, c]])
    xy[:, 0] += X
    xy[:, 1] += Y
    out = []
    for z in (Z0, Z0 + hc):
        for xw, yw in xy:
            zc = xw * C + (H - z) * S
            yc = -xw * S + (H - z) * C
            out.append((CX + F * yw / zc, CY + F * yc / zc))
    out = np.array(out)
    out[:, 0] = (out[:, 0] - x1) * size / (x2 - x1)
    out[:, 1] = (out[:, 1] - y1) * size / (y2 - y1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--mask", required=True, help=".npy or .png container mask")
    ap.add_argument("--box", required=True, help="crop x1,y1,x2,y2")
    ap.add_argument("--height", type=float, default=2.591)
    ap.add_argument("--out", default=r"out\timepass")
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--maxiter", type=int, default=60)
    args = ap.parse_args()

    if args.mask.endswith(".npy"):
        mask = np.load(args.mask).astype(bool)
    else:
        mask = cv2.imread(args.mask, cv2.IMREAD_GRAYSCALE) > 127

    x1, y1, x2, y2 = [int(v) for v in args.box.split(",")]
    crop = (x1, y1, x2, y2)
    obs = mask[y1:y2, x1:x2]
    obs = cv2.resize(obs.astype(np.uint8), (args.size, args.size),
                     interpolation=cv2.INTER_NEAREST) > 0

    def objective(p):
        pts = project(p, args.height, crop, args.size)
        poly = cv2.convexHull(pts.astype(np.float32)).astype(np.int32)
        pred = np.zeros((args.size, args.size), np.uint8)
        cv2.fillPoly(pred, [poly], 1)
        pred = pred > 0
        inter = np.logical_and(pred, obs).sum()
        union = np.logical_or(pred, obs).sum()
        return 1.0 - (inter / union if union else 0.0)

    bounds = [
        (10.0, 50.0), (-20.0, -3.0), (0.5, 1.8), (-0.3, 0.3),
        (4.0, 15.0), (2.1, 2.8),
    ]
    result = differential_evolution(
        objective, bounds, seed=0, maxiter=args.maxiter, popsize=10,
        tol=1e-3, polish=True, workers=1,
    )
    X, Y, Z0, yaw, L, W = result.x
    out = {
        "image": args.image,
        "mask": args.mask,
        "height_m": args.height,
        "L_m": round(float(L), 3),
        "W_m": round(float(W), 3),
        "Z0_m": round(float(Z0), 3),
        "yaw_deg": round(math.degrees(float(yaw)), 2),
        "X_m": round(float(X), 2),
        "Y_m": round(float(Y), 2),
        "iou": round(float(1 - result.fun), 4),
    }
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "container_fit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))

    # overlay fitted box
    image = cv2.imread(args.image)
    pts = project(result.x, args.height, crop, args.size)
    pts[:, 0] = pts[:, 0] * (x2 - x1) / args.size + x1
    pts[:, 1] = pts[:, 1] * (y2 - y1) / args.size + y1
    hull = cv2.convexHull(pts.astype(np.float32)).astype(np.int32)
    cv2.polylines(image, [hull], True, (255, 0, 0), 3)
    cv2.imwrite(str(out_dir / "container_fit_overlay.jpg"), image)
    print(f"wrote {out_dir / 'container_fit.json'}")


if __name__ == "__main__":
    main()
