#!/usr/bin/env python
"""Detect white dash-like components in a frame and dump candidate endpoints.

This is a generalisation of the Cawang `dash3.mjs` extractor.  It does not
assume a fixed VP or lane position; it only finds bright elongated blobs in a
road ROI, computes their principal axis endpoints, and writes a CSV/JSON that
can be inspected and fed to the dash fitter.

Example:
  py scripts/calib_compare/detect_dashes.py videos/frames/ciawi_tm30_001.png \
     --roi 0,180,704,575 --out videos/frames/ciawi_dashes_candidates.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import cv2
import numpy as np


def parse_roi(text: str) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = [int(v) for v in text.replace(",", " ").split()]
    return x0, y0, x1, y1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--roi", default="", help="x0,y0,x1,y1; default whole image")
    ap.add_argument("--thr", type=int, default=135, help="white brightness threshold")
    ap.add_argument("--sat-max", type=int, default=90, help="maximum saturation")
    ap.add_argument("--min-area", type=int, default=25)
    ap.add_argument("--max-area", type=int, default=8000)
    ap.add_argument("--min-length", type=float, default=8.0)
    ap.add_argument("--max-length", type=float, default=250.0)
    ap.add_argument("--min-width", type=float, default=1.5)
    ap.add_argument("--max-width", type=float, default=30.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        raise SystemExit(f"cannot read {args.image}")
    h, w = img.shape[:2]
    if args.roi:
        x0, y0, x1, y1 = parse_roi(args.roi)
    else:
        x0, y0, x1, y1 = 0, 0, w, h
    roi = img[y0:y1, x0:x1]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 2] >= args.thr) & (hsv[:, :, 1] <= args.sat_max)).astype(np.uint8) * 255
    # close small gaps inside a dash, then remove single-pixel noise
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    rows = []
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < args.min_area or area > args.max_area:
            continue
        ys, xs = np.where(labels == i)
        if len(xs) < 8:
            continue
        pts = np.column_stack([xs, ys]).astype(np.float32)
        mean = pts.mean(axis=0)
        cov = np.cov((pts - mean).T)
        evals, evecs = np.linalg.eigh(cov)
        major = evecs[:, int(np.argmax(evals))]
        ang = math.atan2(float(major[1]), float(major[0]))
        # project points onto major/minor axes for length/width
        proj = (pts - mean) @ major
        orth = (pts - mean) @ np.array([-major[1], major[0]])
        length = float(proj.max() - proj.min())
        width = float(orth.max() - orth.min())
        if length < args.min_length or length > args.max_length:
            continue
        if width < args.min_width or width > args.max_width:
            continue
        if length / max(width, 1e-6) < 2.5:
            continue
        # endpoints in ROI coordinates, then image coordinates
        p0 = mean + major * float(proj.min())
        p1 = mean + major * float(proj.max())
        p0 += np.array([x0, y0], dtype=np.float32)
        p1 += np.array([x0, y0], dtype=np.float32)
        if p0[1] < p1[1]:
            far, near = p0, p1
        else:
            far, near = p1, p0
        rows.append(
            {
                "id": len(rows),
                "cx": round(float(mean[0] + x0), 2),
                "cy": round(float(mean[1] + y0), 2),
                "length": round(length, 2),
                "width": round(width, 2),
                "angle_deg": round(math.degrees(ang), 2),
                "area": area,
                "x_far": round(float(far[0]), 2),
                "y_far": round(float(far[1]), 2),
                "x_near": round(float(near[0]), 2),
                "y_near": round(float(near[1]), 2),
                "u_mid": round(float((far[0] + near[0]) / 2), 2),
            }
        )

    rows.sort(key=lambda r: (-r["y_near"], r["cx"]))
    for i, r in enumerate(rows):
        r["id"] = i
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)
    out.with_suffix(".json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"detected {len(rows)} candidates -> {out}")
    for r in rows[:40]:
        print(
            f"  id={r['id']:2d} cx={r['cx']:7.1f} cy={r['cy']:7.1f} "
            f"L={r['length']:6.1f} W={r['width']:5.1f} ang={r['angle_deg']:6.1f} "
            f"near=({r['x_near']:6.1f},{r['y_near']:6.1f}) far=({r['x_far']:6.1f},{r['y_far']:6.1f})"
        )


if __name__ == "__main__":
    main()
