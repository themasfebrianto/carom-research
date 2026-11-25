#!/usr/bin/env python
"""Single-image calibration from one cuboid of known dimensions.

EXPERIMENTAL.  Only the eight 2D corners and the box dimensions (L, W, H) are
used.  The solver recovers the focal length, camera pitch/yaw/height, and the
box position and yaw jointly:

    unknowns: f, phi, theta, h, X, Y, yaw       (7)
    equations: 8 corners x 2                    (16)

A single cuboid with unknown world pose is ambiguous: the box can be flipped or
moved and still project close to the same corners, and f trades against depth.
On SVLD this produced wrong minima on 1cam/session0 scenes.  Prefer
`box_pnp_calib.py` with world-space 3D points, or solve several boxes jointly.

Example:
  py scripts/box_pnp_known_dims.py --input box.json --out result.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares

from svld_box_calib import project


def box_corners(center, dims_lwh, yaw: float) -> np.ndarray:
    L, W, H = dims_lwh
    X, Y, _ = center
    local = np.array(
        [[W / 2, -L / 2], [-W / 2, -L / 2], [-W / 2, L / 2], [W / 2, L / 2]]
    )
    c, s = math.cos(yaw), math.sin(yaw)
    xy = local @ np.array([[c, s], [-s, c]])
    xy[:, 0] += X
    xy[:, 1] += Y
    bottom = np.column_stack([xy, np.zeros(4)])
    top = np.column_stack([xy, np.full(4, H)])
    return np.vstack([bottom, top])


def solve_cuboid(p2, dims, cx, cy, width, height):
    def residual(p):
        f, phi, theta, h, X, Y, yaw = p
        corners = box_corners((X, Y, 0.0), dims, yaw)
        return (project(corners, np.array([f, phi, theta, h]), cx, cy) - p2).ravel()

    starts = []
    for f0 in (max(width, height) * 1.2, 1000.0, 3000.0):
        for y0 in (10.0, 25.0, 50.0):
            starts.append(np.array([f0, 0.1, 0.0, 6.0, 0.0, y0, 0.0]))

    best = None
    for x0 in starts:
        try:
            res = least_squares(
                residual,
                x0,
                bounds=(
                    [50.0, -1.45, -1.45, 0.3, -500.0, 1.0, -math.pi],
                    [30000.0, 1.45, 1.45, 60.0, 500.0, 500.0, math.pi],
                ),
                loss="soft_l1",
                f_scale=1.5,
                max_nfev=10000,
            )
        except Exception:
            continue
        rms = float(np.sqrt(np.mean(res.fun ** 2)))
        if best is None or res.cost < best[1]:
            best = (res.x, res.cost, rms)
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--overlay", default=None)
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    p2 = np.array(data["points2d"], float)
    if p2.shape != (8, 2):
        raise SystemExit("points2d must be 8x2")
    dims = [float(x) for x in data["dims"]]
    if len(dims) != 3:
        raise SystemExit("dims must be [L, W, H]")
    width, height = [int(x) for x in data.get("image_size", [1280, 720])]
    cx, cy = width / 2.0, height / 2.0

    best = solve_cuboid(p2, dims, cx, cy, width, height)
    if best is None:
        raise SystemExit("no solution")
    p, _, rms = best
    f, phi, theta, h, X, Y, yaw = p
    result = {
        "f_px": round(float(f), 3),
        "pitch_deg": round(math.degrees(float(phi)), 4),
        "yaw_deg": round(math.degrees(float(theta)), 4),
        "camera_height_m": round(float(h), 4),
        "box_X_m": round(float(X), 4),
        "box_Y_m": round(float(Y), 4),
        "box_yaw_deg": round(math.degrees(float(yaw)), 4),
        "dims_LWH_m": [round(float(x), 4) for x in dims],
        "rms_px": round(float(rms), 4),
        "image_size": [width, height],
        "cx": cx,
        "cy": cy,
    }
    print(json.dumps(result, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.overlay and data.get("image"):
        img = cv2.imread(data["image"])
        corners = box_corners((X, Y, 0.0), dims, yaw)
        uv = project(corners, np.array([f, phi, theta, h]), cx, cy)
        for i in range(8):
            cv2.circle(img, (int(uv[i, 0]), int(uv[i, 1])), 6, (0, 0, 255), -1)
            cv2.putText(img, str(i), (int(uv[i, 0]) + 7, int(uv[i, 1]) - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        edges = [(0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7), (7, 6), (6, 4),
                 (0, 4), (1, 5), (2, 6), (3, 7)]
        for a, b in edges:
            cv2.line(img, (int(uv[a, 0]), int(uv[a, 1])),
                     (int(uv[b, 0]), int(uv[b, 1])), (0, 255, 0), 2)
        cv2.imwrite(args.overlay, img)
        print(f"wrote {args.overlay}")


if __name__ == "__main__":
    main()
