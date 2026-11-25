#!/usr/bin/env python
"""Estimate f/pitch/yaw/height from SVLD lane lines + known lane width.

The camera model is the SVLD/CenterLoc3D model:
  R = Rx(phi + pi/2) Rz(theta), camera at (0, 0, h), principal point centered.
Lane boundaries are parallel at x = x0 + s*i*w, with w known.  This is the
classical parallel-lines calibration: the lane width fixes scale, the lane
line geometry fixes f/h and pose.  No GeoCalib/AnyCalib focal is used.

Example:
  py scripts/svld_lane_fit.py --per-scene 10 --out out/svld_lane_fit
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import least_squares

BACKEND = Path(r"D:\Kerjaan\LearnPinhole\backend")

# Lane-width priors from the lateral vehicle peaks (meters).
LANE_W = {
    "0cam": 3.00,
    "1cam": 2.70,
    "session0_centre": 3.20,
    "session0_right": 3.20,
    "session6_right": 3.25,
}


def rotation(phi: float, theta: float) -> np.ndarray:
    return np.array([
        [math.cos(theta), -math.sin(theta), 0.0],
        [-math.sin(phi) * math.sin(theta), -math.sin(phi) * math.cos(theta), -math.cos(phi)],
        [math.cos(phi) * math.sin(theta), math.cos(phi) * math.cos(theta), -math.sin(phi)],
    ])


def project(points, f, phi, theta, h, cx, cy):
    R = rotation(phi, theta)
    Pc = (R @ (points - np.array([0.0, 0.0, h])).T).T
    return np.stack([f * Pc[:, 0] / Pc[:, 2] + cx,
                     f * Pc[:, 1] / Pc[:, 2] + cy], axis=1)


def predicted_line(x, f, phi, theta, h, cx, cy):
    pts = project(np.array([[x, 5.0, 0.0], [x, 200.0, 0.0]]),
                  f, phi, theta, h, cx, cy)
    (u1, v1), (u2, v2) = pts
    a = v1 - v2
    b = u2 - u1
    c = u1 * v2 - u2 * v1
    n = math.hypot(a, b)
    return a / n, b / n, c / n


def cluster_segments(segments, v_ref: float, width: int, height: int):
    entries = []
    for seg in segments:
        a, b, c = seg.eq
        if abs(a) < 1e-6:
            continue
        u_ref = -(b * v_ref + c) / a
        if not (-0.5 * width < u_ref < 1.5 * width):
            continue
        entries.append((u_ref, seg))
    entries.sort(key=lambda item: item[0])
    if not entries:
        return []
    gap = 0.035 * width
    clusters = [[entries[0]]]
    for item in entries[1:]:
        if item[0] - clusters[-1][-1][0] <= gap:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    out = []
    for cluster in clusters:
        segs = [item[1] for item in cluster]
        if sum(s.length for s in segs) < 0.08 * height:
            continue
        out.append(segs)
    return out


def fit_image(segments, w: float, width: int, height: int, vp_u: float, vp_v: float):
    cx, cy = width / 2.0, height / 2.0
    v_ref = 0.82 * height
    clusters = cluster_segments(segments, v_ref, width, height)
    if len(clusters) < 3:
        return None
    # Keep at most 5 strongest clusters, sorted left to right.
    clusters = sorted(clusters, key=lambda c: sum(s.length for s in c), reverse=True)[:5]
    clusters.sort(key=lambda c: statistics.median(
        -(s.eq[1] * v_ref + s.eq[2]) / s.eq[0] for s in c
    ))

    f0s = [0.7 * width, 1.2 * width, 1.8 * width, 2.4 * width]
    best = None
    # Try consecutive triplets; one bad cluster (median/guardrail) then does not
    # poison the whole fit.
    for start in range(max(1, len(clusters) - 2)):
        subset = clusters[start:start + 3]
        if len(subset) < 3:
            continue
        points = []
        for cluster in subset:
            pts = []
            for seg in cluster:
                pts.append((seg.x1, seg.y1))
                pts.append((seg.x2, seg.y2))
            points.append(np.asarray(pts, dtype=float))

        def residuals(p):
            f, phi, theta, h, x0, sign = p
            out = []
            for i, pts in enumerate(points):
                x = x0 + sign * i * w
                a, b, c = predicted_line(x, f, phi, theta, h, cx, cy)
                out.extend(a * pts[:, 0] + b * pts[:, 1] + c)
            return np.asarray(out)

        for sign in (1.0, -1.0):
            for f0 in f0s:
                pitch0 = math.atan2(cy - vp_v, f0)
                yaw0 = math.atan2(-(vp_u - cx) * math.cos(pitch0), f0)
                p0 = np.array([
                    f0,
                    min(max(pitch0, math.radians(1)), math.radians(30)),
                    min(max(yaw0, math.radians(-30)), math.radians(30)),
                    8.0, -5.0, sign,
                ])
                try:
                    result = least_squares(
                        residuals, p0,
                        bounds=([300, math.radians(1), math.radians(-30), 2.0, -50, -1],
                                [6000, math.radians(40), math.radians(30), 20.0, 50, 1]),
                        loss="soft_l1", f_scale=2.0, max_nfev=1500, x_scale="jac",
                    )
                except Exception:
                    continue
                if best is None or result.cost < best.cost:
                    best = result
    if best is None:
        return None
    f, phi, theta, h, x0, sign = best.x
    rms = float(np.sqrt(np.mean(best.fun ** 2)))
    return {
        "f_est": float(f),
        "pitch_deg": math.degrees(float(phi)),
        "yaw_deg": math.degrees(float(theta)),
        "height_m": float(h),
        "x0_m": float(x0),
        "sign": int(sign),
        "rms_px": rms,
        "n_lanes": 3,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--backend", default=str(BACKEND))
    ap.add_argument("--out", default="out/svld_lane_fit")
    ap.add_argument("--limit", type=int, default=0,
                    help="debug: process only the first N manifest rows")
    ap.add_argument("--scene", default=None,
                    help="debug: only this scene (e.g. session0_right)")
    args = ap.parse_args()

    sys.path.insert(0, args.backend)
    from app.lane_vp import detect_lane_vp

    manifest = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    if args.scene:
        manifest = [row for row in manifest if row["scene"] == args.scene]
    if args.limit:
        manifest = manifest[: args.limit]
    rows = []
    for item in manifest:
        scene = item["scene"]
        w = LANE_W.get(scene)
        if w is None:
            continue
        image = cv2.imread(item["source"])
        if image is None:
            continue
        h_img, w_img = image.shape[:2]
        vp = detect_lane_vp(image, prior_focal=1.2 * w_img)
        if not vp.ok:
            rows.append({
                "split": item["split"], "scene": scene, "image": item["image"],
                "status": "NO_VP", "reason": vp.reason, "lane_w_m": w,
            })
            continue
        fit = fit_image(vp.segments, w, w_img, h_img, vp.u, vp.v)
        if fit is None:
            rows.append({
                "split": item["split"], "scene": scene, "image": item["image"],
                "status": "FIT_FAILED", "reason": "fewer than 3 lane clusters",
                "lane_w_m": w,
            })
            continue
        f_gt = float(item["f_px"])
        status = "OK" if fit["rms_px"] <= 5.0 else "FIT_BAD"
        rows.append({
            "split": item["split"], "scene": scene, "image": item["image"],
            "status": status, **fit, "lane_w_m": w, "f_gt": f_gt,
            "df_pct": round(abs(fit["f_est"] - f_gt) / f_gt * 100, 3),
        })
        print(
            f"{item['split']:8s} {scene:18s} {item['image']:28s} "
            f"{status:8s} f {f_gt:.0f}->{fit['f_est']:.0f} "
            f"({rows[-1]['df_pct']:.1f}%) rms={fit['rms_px']:.2f}"
        )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for row in rows for k in row})
    with (out_dir / "lane_fit.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    groups = defaultdict(list)
    for row in rows:
        if row.get("status") == "OK":
            groups[(row["split"], row["scene"])].append(row["df_pct"])
            groups[(row["split"], "*")].append(row["df_pct"])
            groups[("*", "*")].append(row["df_pct"])
    summary = {}
    for group, vals in sorted(groups.items()):
        vals = sorted(vals)
        summary[f"{group[0]}/{group[1]}"] = {
            "n": len(vals),
            "median_pct": round(statistics.median(vals), 3),
            "p90_pct": round(vals[min(len(vals) - 1, round((len(vals) - 1) * 0.9))], 3),
            "max_pct": round(vals[-1], 3),
            "pass_5pct": sum(v < 5 for v in vals),
        }
    (out_dir / "lane_fit_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {out_dir / 'lane_fit.csv'}")
    for group, s in summary.items():
        print(f"  {group:24s} n={s['n']:3d} median={s['median_pct']:5.1f}% pass5={s['pass_5pct']}/{s['n']}")


if __name__ == "__main__":
    main()
