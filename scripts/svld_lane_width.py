#!/usr/bin/env python
"""Estimate SVLD lane width from the lateral positions of 3D vehicle boxes.

The 3D boxes are in the SVLD world frame (x lateral, y longitudinal, mm).
Vehicles cluster around lane centres; a smoothed histogram of their lateral
centres gives lane peaks, and adjacent peak spacing is the lane width.  This
is an independent cross-check for the 3.6 m anchor assumption.

Example:
  py scripts/svld_lane_width.py --out out/svld_vp
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks


ROOTS = [
    Path("SVLD-3D-TRAINVAL-SCENE-A-C/DATA2021"),
    Path("SVLD-3D-TRAINVAL-SCENE-D/DATA2021"),
    Path("SVLD-3D-TRAINVAL-SCENE-E/DATA2021"),
]


def numbers(text: str) -> list[float]:
    return [
        float(x)
        for x in text.replace("(", "").replace(")", "").replace(",", " ").split()
    ]


def scene_from_calib(name: str) -> str:
    stem = Path(name).stem
    for suffix in ("_calibParams", "_ManualCamCalibResult"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/svld_vp")
    ap.add_argument("--bin-m", type=float, default=0.10)
    ap.add_argument("--min-gap-m", type=float, default=1.5)
    ap.add_argument("--min-width-m", type=float, default=2.8)
    ap.add_argument("--max-width-m", type=float, default=4.2)
    args = ap.parse_args()

    by_scene: dict[str, list[float]] = defaultdict(list)
    for root in ROOTS:
        if not root.exists():
            continue
        for ann in (root / "Annotations").glob("*.xml"):
            xml_root = ET.parse(ann).getroot()
            calib = Path(
                (xml_root.findtext("calibfile") or "").replace("\\", "/")
            ).name
            scene = scene_from_calib(calib)
            for obj in xml_root.findall("object"):
                pts = numbers(obj.findtext("vertex3d") or "")
                if len(pts) != 24:
                    continue
                arr = np.array(pts).reshape(-1, 3) / 1000.0
                by_scene[scene].append(float(arr[:, 0].mean()))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for scene, xs in sorted(by_scene.items()):
        xs = np.array(xs, dtype=float)
        lo = math.floor(xs.min())
        hi = math.ceil(xs.max())
        edges = np.arange(lo, hi + args.bin_m, args.bin_m)
        hist, edges = np.histogram(xs, bins=edges)
        smooth = gaussian_filter1d(hist.astype(float), sigma=2.0)
        min_distance = max(1, round(args.min_gap_m / args.bin_m))
        peaks, props = find_peaks(
            smooth,
            height=0.05 * smooth.max(),
            distance=min_distance,
        )
        centers = [float(edges[i] + args.bin_m / 2) for i in peaks]
        widths = [
            b - a
            for a, b in zip(centers, centers[1:])
            if args.min_width_m <= b - a <= args.max_width_m
        ]
        rows.append({
            "scene": scene,
            "objects": len(xs),
            "peaks_m": ";".join(f"{c:.2f}" for c in centers),
            "adjacent_widths_m": ";".join(f"{w:.2f}" for w in widths),
            "width_median_m": round(statistics.median(widths), 3) if widths else None,
            "width_n": len(widths),
        })

    with (out_dir / "vehicle_lane_width.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "vehicle_lane_width.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    print(f"wrote {out_dir / 'vehicle_lane_width.csv'}")
    for row in rows:
        print(
            f"{row['scene']:18s} peaks={row['peaks_m']} "
            f"widths={row['adjacent_widths_m']} median={row['width_median_m']}"
        )


if __name__ == "__main__":
    main()
