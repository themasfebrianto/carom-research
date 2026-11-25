#!/usr/bin/env python
"""Run GlobustVP on SVLD frames and compare its 3 VPs with GT directions.

GlobustVP assumes a known intrinsic matrix K.  Two modes:
  --k-mode gt       use the SVLD GT f (upper bound on VP detection)
  --k-mode generic  use f = 1.2 * max(width, height) (realistic, no GT)

The three estimated VPs are matched to the GT world X/Y/Z directions by the
best permutation; the Z match is the vertical VP.

Example:
  py scripts/svld_globustvp.py --scene 0cam --limit 1 --k-mode gt
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from globustvp.solver.core import globustvp
from globustvp.utils.geometry import (
    compute_backprojection_normals,
    compute_line_uncertainties,
    normalize_lines,
)
from globustvp.utils.io import load_image_and_gray
from globustvp.utils.line_processing import (
    detect_and_format_lines,
    filter_lines_by_length,
)

BACKEND = Path(r"D:\Kerjaan\LearnPinhole\backend")


def rotation(phi: float, theta: float) -> np.ndarray:
    return np.array([
        [math.cos(theta), -math.sin(theta), 0.0],
        [-math.sin(phi) * math.sin(theta), -math.sin(phi) * math.cos(theta), -math.cos(phi)],
        [math.cos(phi) * math.sin(theta), math.cos(phi) * math.cos(theta), -math.sin(phi)],
    ])


def angle_deg(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    return math.degrees(math.acos(min(1.0, abs(float(a @ b)))))


def match_vps(est, true):
    best = None
    for perm in itertools.permutations(range(3)):
        errs = [angle_deg(est[i], true[perm[i]]) for i in range(3)]
        score = sum(errs)
        if best is None or score < best[0]:
            best = (score, perm, errs)
    return best[1], best[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--scene", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--k-mode", choices=["gt", "generic"], default="gt")
    ap.add_argument("--min-length", type=int, default=30)
    ap.add_argument("--max-lines", type=int, default=20)
    ap.add_argument("--line-filter", choices=["all", "main"], default="all",
                    help="all = keep all LSD lines; main = GlobustVP KMeans filter")
    ap.add_argument("--solver", default="SCS")
    ap.add_argument("--eps", type=float, default=1e-4)
    ap.add_argument("--max-iters", type=int, default=20000)
    ap.add_argument("--out", default="out/svld_globustvp")
    args = ap.parse_args()

    manifest = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    if args.scene:
        manifest = [r for r in manifest if r["scene"] == args.scene]
    if args.limit:
        manifest = manifest[: args.limit]

    rows = []
    for item in manifest:
        image_path = item["source"]
        img, gray = load_image_and_gray(image_path)
        if img is None:
            continue
        h, w = gray.shape[:2]
        f_gt = float(item["f_px"])
        f_k = f_gt if args.k_mode == "gt" else 1.2 * max(w, h)
        K = np.array([[f_k, 0, w / 2], [0, f_k, h / 2], [0, 0, 1]], float)

        if args.line_filter == "all":
            lsd = cv2.createLineSegmentDetector()
            raw = lsd.detect(gray)[0]
            filtered = filter_lines_by_length(raw, min_length=args.min_length)
            if filtered.size == 0:
                rows.append({
                    "split": item["split"], "scene": item["scene"],
                    "image": item["image"], "k_mode": args.k_mode,
                    "status": "FEW_LINES", "n_lines": 0,
                })
                continue
            seg = filtered[:, 0, :]
            lines = np.ones((6, seg.shape[0]))
            lines[0:2, :] = seg[:, 0:2].T
            lines[3:5, :] = seg[:, 2:4].T
        else:
            lines = detect_and_format_lines(
                gray_image=gray, min_length=args.min_length
            )
        if args.max_lines and lines.shape[1] > args.max_lines:
            lengths = np.linalg.norm(lines[3:5, :] - lines[0:2, :], axis=0)
            keep = np.argsort(lengths)[-args.max_lines:]
            lines = lines[:, keep]
        n_lines = int(lines.shape[1])
        if n_lines < 8:
            rows.append({
                "split": item["split"], "scene": item["scene"],
                "image": item["image"], "k_mode": args.k_mode,
                "status": "FEW_LINES", "n_lines": n_lines,
            })
            continue

        normalized = normalize_lines(K, lines).T
        para = compute_backprojection_normals(normalized)
        unc = compute_line_uncertainties(normalized, K, use_uncertainty=True)
        param = {
            "line_num": n_lines,
            "vanishing_point_num": 3,
            "c": 0.03,
            "sample_line_num": 4,
            "is_fast_solver": True,
            "eigen_threshold": 1,
            "solver": args.solver,
            "K": K,
            "max_attempts": 300,
        }
        result = None
        last_error = None
        t0 = time.time()
        for eps in (args.eps, 1e-5, 1e-4):
            if args.solver.upper() == "CLARABEL":
                param["solver_opts"] = {
                    "tol_gap_abs": eps,
                    "tol_gap_rel": eps,
                    "max_iter": args.max_iters,
                }
            else:
                param["solver_opts"] = {
                    "eps_abs": eps, "eps_rel": eps, "max_iters": args.max_iters
                }
            np.random.seed(0)
            print(
                f"  solving {n_lines} lines with {args.solver} eps={eps}...",
                flush=True,
            )
            try:
                result = globustvp(normalized, para, unc, param)
                break
            except Exception as exc:
                last_error = exc
                if "optimal_inaccurate" not in str(exc).lower():
                    break
        elapsed = time.time() - t0
        if result is None:
            rows.append({
                "split": item["split"], "scene": item["scene"],
                "image": item["image"], "k_mode": args.k_mode,
                "status": "ERROR", "n_lines": n_lines,
                "note": f"{type(last_error).__name__}: {last_error}",
            })
            continue
        status, est_vps, est_corrs = result

        if not status or est_vps.shape[0] != 3:
            rows.append({
                "split": item["split"], "scene": item["scene"],
                "image": item["image"], "k_mode": args.k_mode,
                "status": "NO_3VP", "n_lines": n_lines,
                "elapsed_s": round(elapsed, 3),
            })
            continue

        phi = float(item["pitch_rad"])
        theta = float(item["yaw_rad"])
        R = rotation(phi, theta)
        true = [R @ np.array([1.0, 0, 0]), R @ np.array([0, 1.0, 0]), R @ np.array([0, 0, 1.0])]
        perm, errs = match_vps(est_vps, true)
        # perm[i] = true direction matched to est_vps[i]
        z_idx = perm.index(2)
        counts = est_corrs.sum(axis=1).tolist()
        rows.append({
            "split": item["split"], "scene": item["scene"],
            "image": item["image"], "k_mode": args.k_mode,
            "status": "OK", "n_lines": n_lines, "f_k": round(f_k, 2),
            "f_gt": f_gt, "elapsed_s": round(elapsed, 3),
            "err_x_deg": round(errs[perm.index(0)], 3),
            "err_y_deg": round(errs[perm.index(1)], 3),
            "err_z_deg": round(errs[perm.index(2)], 3),
            "count_x": int(counts[perm.index(0)]),
            "count_y": int(counts[perm.index(1)]),
            "count_z": int(counts[z_idx]),
            "est_vps": ";".join(
                ",".join(f"{v:.6f}" for v in row) for row in est_vps
            ),
        })
        print(
            f"{item['split']:8s} {item['scene']:18s} {item['image']:28s} "
            f"lines={n_lines} t={elapsed:.2f}s "
            f"errX={rows[-1]['err_x_deg']:.2f} errY={rows[-1]['err_y_deg']:.2f} "
            f"errZ={rows[-1]['err_z_deg']:.2f} counts={counts}"
        )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for row in rows for k in row})
    with (out / "globustvp.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {}
    for row in rows:
        if row.get("status") == "OK":
            key = f"{row['split']}/{row['scene']}"
            summary.setdefault(key, []).append(row)
    print("\nsummary")
    for key, items in summary.items():
        print(
            f"  {key:24s} n={len(items):3d} "
            f"z_err_med={statistics.median(r['err_z_deg'] for r in items):5.2f} "
            f"z_ok_2deg={sum(r['err_z_deg'] < 2 for r in items)}/{len(items)}"
        )
    print(f"wrote {out / 'globustvp.csv'}")


if __name__ == "__main__":
    main()
