#!/usr/bin/env python
"""Camera calibration from one 3D box (8 corners + 3D points).

This is the reusable version of the SVLD experiment.  It accepts either

  * 8 world points + 8 image points, or
  * a box centre, dimensions (L, W, H) and yaw, plus 8 image points.

The camera model is the one used by SVLD/CenterLoc3D:

    R = Rx(phi + pi/2) Rz(theta)
    Pc = R (P - [0, 0, h])
    u = f Xc / Zc + cx
    v = f Yc / Zc + cy

Example:
  py scripts/box_pnp_calib.py --input box.json --width 1280 --height 720
  py scripts/box_pnp_calib.py --input box.json --overlay out/box_overlay.jpg
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np

from svld_box_calib import project, solve


def box_corners(center, dims_lwh, yaw_deg: float) -> np.ndarray:
    """Eight corners in the same order as SVLD: bottom 4, then top 4."""
    L, W, H = dims_lwh
    X, Y, Z = center
    local = np.array(
        [[W / 2, -L / 2], [-W / 2, -L / 2], [-W / 2, L / 2], [W / 2, L / 2]]
    )
    c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    xy = local @ np.array([[c, s], [-s, c]])
    xy[:, 0] += X
    xy[:, 1] += Y
    bottom = np.column_stack([xy, np.full(4, Z)])
    top = np.column_stack([xy, np.full(4, Z + H)])
    return np.vstack([bottom, top])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON with points2d and points3d or center/dims/yaw")
    ap.add_argument("--width", type=int, default=0, help="image width; else from JSON")
    ap.add_argument("--height", type=int, default=0)
    ap.add_argument("--cx", type=float, default=0.0, help="principal point x; default width/2")
    ap.add_argument("--cy", type=float, default=0.0)
    ap.add_argument("--overlay", default=None, help="optional output image with the fitted box")
    ap.add_argument("--out", default=None, help="optional JSON result path")
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    p2 = np.array(data["points2d"], float)
    if p2.shape != (8, 2):
        raise SystemExit("points2d must be 8x2")

    if "points3d" in data:
        p3 = np.array(data["points3d"], float)
        if p3.shape != (8, 3):
            raise SystemExit("points3d must be 8x3")
    else:
        center = data["center"]
        dims = data["dims"]
        yaw = float(data.get("yaw_deg", 0.0))
        p3 = box_corners(center, dims, yaw)

    width = args.width or int(data.get("image_size", [1280, 720])[0])
    height = args.height or int(data.get("image_size", [1280, 720])[1])
    cx = args.cx or width / 2.0
    cy = args.cy or height / 2.0

    starts = [
        np.array([max(width, height) * 1.2, 0.1, 0.0, 5.0]),
        np.array([1000.0, 0.1, 0.0, 5.0]),
        np.array([3000.0, 0.1, 0.0, 7.0]),
    ]
    params, rms = solve([p2], [p3], cx, cy, starts)
    f, phi, theta, h = params

    result = {
        "f_px": round(float(f), 3),
        "pitch_deg": round(math.degrees(float(phi)), 4),
        "yaw_deg": round(math.degrees(float(theta)), 4),
        "camera_height_m": round(float(h), 4),
        "rms_px": round(float(rms), 4),
        "cx": cx,
        "cy": cy,
        "image_size": [width, height],
        "n_points": 8,
        "points2d_reproj": project(p3, params, cx, cy).round(2).tolist(),
    }
    print(json.dumps(result, indent=2))

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.overlay:
        image_path = data.get("image")
        if not image_path:
            raise SystemExit("--overlay needs an image path in the JSON")
        img = cv2.imread(image_path)
        if img is None:
            raise SystemExit(f"cannot read {image_path}")
        uv = project(p3, params, cx, cy)
        for i in range(8):
            cv2.circle(img, (int(uv[i, 0]), int(uv[i, 1])), 5, (0, 0, 255), -1)
            cv2.putText(img, str(i), (int(uv[i, 0]) + 6, int(uv[i, 1]) - 6),
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
