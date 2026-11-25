#!/usr/bin/env python
"""Check vehicle-box vanishing points from SVLD 2D/3D corners.

deep_vp (ICANN 2021) predicts two orthogonal VPs from a vehicle crop.  This
script tests the same geometry with SVLD annotations: fit the three VP
directions from the 8 projected box corners and compare them with the GT VPs
obtained from the 3D box axes and the GT calibration.
"""

from __future__ import annotations

import argparse
import math
import statistics
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import numpy as np


def numbers(text: str) -> list[float]:
    return [
        float(x)
        for x in text.replace("(", "").replace(")", "").replace(",", " ").split()
    ]


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


def angle(a, b) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    a = a / (np.linalg.norm(a) + 1e-12)
    b = b / (np.linalg.norm(b) + 1e-12)
    return math.degrees(math.acos(min(1.0, abs(float(a @ b)))))


def fit_vps(v2: np.ndarray) -> list[np.ndarray]:
    edge_sets = [
        [(0, 1), (2, 3), (4, 5), (6, 7)],
        [(0, 3), (1, 2), (4, 7), (5, 6)],
        [(0, 4), (1, 5), (2, 6), (3, 7)],
    ]
    vps = []
    for edges in edge_sets:
        A, b = [], []
        for i, j in edges:
            x1, y1 = v2[i]
            x2, y2 = v2[j]
            A.append([y1 - y2, x2 - x1])
            b.append(-(x1 * y2 - x2 * y1))
        sol, *_ = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)
        vps.append(np.array([sol[0], sol[1], 1.0]))
    return vps


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"data\svld\TESTDATA2021\TESTDATA2021")
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()

    root = Path(args.root)
    by_calib: dict[str, list[float]] = defaultdict(list)
    for i, ann in enumerate(sorted((root / "Annotations").glob("*.xml"))):
        if args.limit and i >= args.limit:
            break
        tree = ET.parse(ann).getroot()
        calib_name = Path(tree.findtext("calibfile").replace("\\", "/")).name
        calib_path = root / "Calib" / calib_name
        if not calib_path.exists():
            continue
        calib = ET.parse(calib_path).getroot()
        f = float(calib.findtext("f"))
        phi = float(calib.findtext("fi"))
        theta = float(calib.findtext("theta"))
        R = rotation(phi, theta)
        K = np.array([[f, 0, 640.0], [0, f, 360.0], [0, 0, 1.0]])

        for obj in tree.findall("object"):
            v2 = np.array(numbers(obj.findtext("vertex2d") or "")).reshape(8, 2)
            v3 = np.array(numbers(obj.findtext("vertex3d") or "")).reshape(8, 3) / 1000.0
            est = fit_vps(v2)
            axes = [v3[1] - v3[0], v3[3] - v3[0], v3[4] - v3[0]]
            for k, axis in enumerate(axes):
                d = R @ (axis / np.linalg.norm(axis))
                gt = K @ d
                gt = gt / gt[2]
                by_calib[calib_name].append(angle(est[k], gt))

    for calib, errors in by_calib.items():
        print(
            f"{calib:38s} n={len(errors):5d} "
            f"median={statistics.median(errors):6.2f}deg "
            f"p90={np.percentile(errors, 90):6.2f}deg"
        )


if __name__ == "__main__":
    main()
