#!/usr/bin/env python
"""Sensitivity of 3D-box camera calibration to box errors.

The 3D boxes in SVLD are GT, so solving the camera from them is exact by
construction.  This script perturbs the 2D corners, dimensions, position and
yaw to estimate what a real monocular 3D detector would need to achieve.

Example:
  py scripts/svld_box_calib_sensitivity.py --trials 20
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from svld_box_calib import parse_objects, solve


def perturb_box(obj: dict, rng: np.random.Generator, dim_sigma: float,
                pos_sigma: float, yaw_sigma: float) -> np.ndarray:
    v3 = obj["v3"].copy()
    center = v3.mean(axis=0)
    # Local axes from the GT box.
    ax = v3[1] - v3[0]
    ay = v3[3] - v3[0]
    az = v3[4] - v3[0]
    ax /= np.linalg.norm(ax)
    ay /= np.linalg.norm(ay)
    az /= np.linalg.norm(az)
    local = np.stack(
        [(v3 - center) @ ax, (v3 - center) @ ay, (v3 - center) @ az], axis=1
    )
    if dim_sigma:
        local *= (1.0 + rng.normal(0.0, dim_sigma, size=(1, 3)))
    if yaw_sigma:
        a = rng.normal(0.0, yaw_sigma)
        c, s = math.cos(a), math.sin(a)
        # Rotate around the vertical axis (az).
        x = local[:, 0] * c - local[:, 1] * s
        y = local[:, 0] * s + local[:, 1] * c
        local[:, 0], local[:, 1] = x, y
    v3 = center + local[:, 0:1] * ax + local[:, 1:2] * ay + local[:, 2:3] * az
    if pos_sigma:
        v3 += rng.normal(0.0, pos_sigma, size=(1, 3))
    return v3


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--ann-root", default=r"data\svld\TESTDATA2021\TESTDATA2021\Annotations")
    ap.add_argument("--trials", type=int, default=10)
    ap.add_argument("--out", default="out/svld_box_calib")
    args = ap.parse_args()

    manifest = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    ann_root = Path(args.ann_root)
    items = []
    for item in manifest:
        ann = ann_root / f"{Path(item['source']).stem}.xml"
        if not ann.exists():
            continue
        objects, width, height = parse_objects(ann)
        if not objects:
            continue
        # Use the largest vehicle in each image (best 3D box quality).
        obj = max(
            objects,
            key=lambda o: (
                np.ptp(o["v2"][:, 0]) * np.ptp(o["v2"][:, 1])
            ),
        )
        items.append((item, obj, width, height))

    cases = [
        ("gt", 0.0, 0.0, 0.0, 0.0),
        ("noise_0.5px", 0.5, 0.0, 0.0, 0.0),
        ("noise_1px", 1.0, 0.0, 0.0, 0.0),
        ("noise_2px", 2.0, 0.0, 0.0, 0.0),
        ("dim_1pct", 0.0, 0.01, 0.0, 0.0),
        ("dim_3pct", 0.0, 0.03, 0.0, 0.0),
        ("dim_5pct", 0.0, 0.05, 0.0, 0.0),
        ("pos_0.25m", 0.0, 0.0, 0.25, 0.0),
        ("pos_0.5m", 0.0, 0.0, 0.5, 0.0),
        ("pos_1m", 0.0, 0.0, 1.0, 0.0),
        ("yaw_1deg", 0.0, 0.0, 0.0, math.radians(1.0)),
        ("yaw_3deg", 0.0, 0.0, 0.0, math.radians(3.0)),
        ("yaw_5deg", 0.0, 0.0, 0.0, math.radians(5.0)),
        ("combined", 1.0, 0.03, 0.3, math.radians(2.0)),
    ]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, noise2d, dim_sigma, pos_sigma, yaw_sigma in cases:
        errs = []
        f_ratios = []
        for trial in range(args.trials if name != "gt" else 1):
            rng = np.random.default_rng(1000 + trial)
            for item, obj, width, height in items:
                v2 = obj["v2"].copy()
                if noise2d:
                    v2 += rng.normal(0.0, noise2d, size=v2.shape)
                v3 = perturb_box(obj, rng, dim_sigma, pos_sigma, yaw_sigma)
                p, _ = solve(
                    [v2],
                    [v3],
                    width / 2.0,
                    height / 2.0,
                    [
                        np.array([1000.0, 0.1, 0.0, 5.0]),
                        np.array([3000.0, 0.1, 0.0, 7.0]),
                    ],
                )
                f_gt = float(item["f_px"])
                ratio = float(p[0] / f_gt)
                if math.isfinite(ratio) and ratio > 0:
                    f_ratios.append(ratio)
                    errs.append(abs(ratio - 1.0) * 100.0)
        rows.append(
            {
                "case": name,
                "n": len(errs),
                "median_err_pct": round(statistics.median(errs), 3) if errs else "",
                "p90_err_pct": round(float(np.percentile(errs, 90)), 3) if errs else "",
                "max_err_pct": round(max(errs), 3) if errs else "",
                "pass1pct": sum(e < 1 for e in errs),
                "pass5pct": sum(e < 5 for e in errs),
            }
        )
        print(rows[-1], flush=True)

    with (out / "sensitivity.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out / 'sensitivity.csv'}")


if __name__ == "__main__":
    main()
