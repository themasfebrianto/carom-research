#!/usr/bin/env python
"""Calibrate an SVLD camera from annotated 3D vehicle boxes.

The SVLD annotations contain the eight 2D projections and the eight world
coordinates of every vehicle box.  A single cuboid of known size gives enough
constraints to solve focal length, pitch, yaw and camera height:

    R = Rx(phi + pi/2) Rz(theta)
    Pc = R (P - [0, 0, h])
    u = f Xc / Zc + cx
    v = f Yc / Zc + cy

This script solves that model per object and jointly per image.  It is a
geometry test: the 3D boxes are GT annotations.  A production system would
replace them with boxes from a monocular 3D detector.

Example:
  py scripts/svld_box_calib.py --manifest out/svld_geocalib/manifest.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares


def numbers(text: str) -> list[float]:
    return [
        float(x)
        for x in text.replace("(", "").replace(")", "").replace(",", " ").split()
    ]


def parse_calib(path: Path) -> dict:
    root = ET.parse(path).getroot()
    raw = {child.tag: (child.text or "").strip() for child in root}
    return {
        "f_px": float(raw["f"]),
        "phi_rad": float(raw["fi"]),
        "theta_rad": float(raw["theta"]),
        "h_m": float(raw["h"]) / 1000.0,
    }


def rotation(phi: float, theta: float) -> np.ndarray:
    return np.array(
        [
            [math.cos(theta), -math.sin(theta), 0.0],
            [
                -math.sin(phi) * math.sin(theta),
                -math.sin(phi) * math.cos(theta),
                -math.cos(phi),
            ],
            [
                math.cos(phi) * math.sin(theta),
                math.cos(phi) * math.cos(theta),
                -math.sin(phi),
            ],
        ]
    )


def project(points_m: np.ndarray, params: np.ndarray, cx: float, cy: float) -> np.ndarray:
    f, phi, theta, h = params
    R = rotation(phi, theta)
    Pc = (R @ (points_m - np.array([0.0, 0.0, h])).T).T
    return np.stack(
        [
            f * Pc[:, 0] / Pc[:, 2] + cx,
            f * Pc[:, 1] / Pc[:, 2] + cy,
        ],
        axis=1,
    )


def parse_objects(ann_path: Path) -> tuple[list[dict], int, int]:
    root = ET.parse(ann_path).getroot()
    size = root.find("size")
    width = int(size.findtext("width"))
    height = int(size.findtext("height"))
    objects = []
    for obj in root.findall("object"):
        v3 = numbers(obj.findtext("vertex3d") or "")
        v2 = numbers(obj.findtext("vertex2d") or "")
        if len(v3) != 24 or len(v2) != 16:
            continue
        objects.append(
            {
                "class": (obj.findtext("type") or "").strip(),
                "dims": [float(x) for x in (obj.findtext("veh_size") or "").split()],
                "v3": np.array(v3).reshape(8, 3) / 1000.0,
                "v2": np.array(v2).reshape(8, 2),
            }
        )
    return objects, width, height


def solve(
    observations: list[np.ndarray],
    world_points: list[np.ndarray],
    cx: float,
    cy: float,
    starts: list[np.ndarray],
) -> tuple[np.ndarray, float]:
    def residual(p):
        return np.concatenate(
            [project(P, p, cx, cy).ravel() - obs.ravel()
             for P, obs in zip(world_points, observations)]
        )

    best = None
    for x0 in starts:
        try:
            res = least_squares(
                residual,
                x0,
                bounds=([50.0, -1.45, -1.45, 0.3], [30000.0, 1.45, 1.45, 60.0]),
                loss="soft_l1",
                f_scale=1.5,
                max_nfev=5000,
            )
        except Exception:
            continue
        rms = float(np.sqrt(np.mean(res.fun ** 2)))
        if best is None or res.cost < best[1]:
            best = (res.x, res.cost, rms)
    if best is None:
        return np.full(4, np.nan), float("nan")
    return best[0], best[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--ann-root", default=r"data\svld\TESTDATA2021\TESTDATA2021\Annotations")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--scene", default=None)
    ap.add_argument("--out", default="out/svld_box_calib")
    args = ap.parse_args()

    manifest = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    if args.scene:
        manifest = [r for r in manifest if r["scene"] == args.scene]
    if args.limit:
        manifest = manifest[: args.limit]
    ann_root = Path(args.ann_root)

    object_rows = []
    image_rows = []
    for item in manifest:
        ann = ann_root / f"{Path(item['source']).stem}.xml"
        if not ann.exists():
            ann = ann_root / f"{item['image'].rsplit('.', 1)[0]}.xml"
        if not ann.exists():
            continue
        objects, width, height = parse_objects(ann)
        if not objects:
            continue
        cx, cy = width / 2.0, height / 2.0
        f_gt = float(item["f_px"])
        starts = [
            np.array([1000.0, 0.1, 0.0, 5.0]),
            np.array([3000.0, 0.1, 0.0, 7.0]),
            np.array([max(width, height) * 1.2, 0.1, 0.0, 10.0]),
        ]

        for obj in objects:
            p, rms = solve([obj["v2"]], [obj["v3"]], cx, cy, starts)
            object_rows.append(
                {
                    "scene": item["scene"],
                    "image": item["image"],
                    "class": obj["class"],
                    "f_gt": round(f_gt, 3),
                    "f_est": round(float(p[0]), 3),
                    "f_ratio": round(float(p[0] / f_gt), 5),
                    "phi_est": round(float(p[1]), 5),
                    "theta_est": round(float(p[2]), 5),
                    "h_est": round(float(p[3]), 4),
                    "rms_px": round(rms, 3),
                }
            )

        p, rms = solve(
            [o["v2"] for o in objects],
            [o["v3"] for o in objects],
            cx,
            cy,
            starts,
        )
        image_rows.append(
            {
                "scene": item["scene"],
                "image": item["image"],
                "n_obj": len(objects),
                "f_gt": round(f_gt, 3),
                "f_est": round(float(p[0]), 3),
                "f_ratio": round(float(p[0] / f_gt), 5),
                "phi_est": round(float(p[1]), 5),
                "theta_est": round(float(p[2]), 5),
                "h_est": round(float(p[3]), 4),
                "rms_px": round(rms, 3),
            }
        )
        print(
            f"{item['scene']:18s} {item['image']:30s} n={len(objects):2d} "
            f"f={p[0]:8.1f}/{f_gt:8.1f} ({p[0]/f_gt:5.3f}) "
            f"phi={p[1]:+.4f} theta={p[2]:+.4f} h={p[3]:.2f} rms={rms:.2f}",
            flush=True,
        )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("objects.csv", object_rows), ("images.csv", image_rows)):
        fields = sorted({k for r in rows for k in r})
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    print("\nsummary by scene (joint per image)")
    for scene in sorted({r["scene"] for r in image_rows}):
        rs = [r for r in image_rows if r["scene"] == scene]
        ratios = [r["f_ratio"] for r in rs]
        err = [abs(x - 1) * 100 for x in ratios]
        print(
            f"  {scene:18s} n={len(rs):2d} "
            f"median_err={statistics.median(err):6.2f}% "
            f"p90={np.percentile(err, 90):6.2f}% "
            f"pass1%={sum(e < 1 for e in err):2d}/{len(rs)} "
            f"pass5%={sum(e < 5 for e in err):2d}/{len(rs)}"
        )

    print("\nsummary by scene (single object)")
    for scene in sorted({r["scene"] for r in object_rows}):
        rs = [r for r in object_rows if r["scene"] == scene]
        err = [abs(r["f_ratio"] - 1) * 100 for r in rs]
        print(
            f"  {scene:18s} n={len(rs):3d} "
            f"median_err={statistics.median(err):6.2f}% "
            f"p90={np.percentile(err, 90):6.2f}% "
            f"pass5%={sum(e < 5 for e in err):3d}/{len(rs)}"
        )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
