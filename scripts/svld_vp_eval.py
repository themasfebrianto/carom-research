#!/usr/bin/env python
"""Evaluate lane-VP pose and measure lane width on SVLD-3D.

VP gives the road-direction vanishing point; with a known focal it yields
pitch and yaw.  The same lane segments are back-projected with the GT SVLD
calibration to measure the lateral spacing between lane boundaries, i.e. the
scene-specific anchor width instead of a fixed 3.6 m assumption.

Examples:
  py scripts/svld_vp_eval.py --source gt
  py scripts/svld_vp_eval.py --source geo
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

BACKEND = Path(r"D:\Kerjaan\LearnPinhole\backend")


def key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    values = sorted(values)
    n = len(values)
    p90 = values[min(n - 1, round((n - 1) * 0.9))]
    return {
        "n": n,
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "p90": round(p90, 4),
        "max": round(values[-1], 4),
    }


def cluster_offsets(offsets: list[float], gap: float = 0.7) -> list[float]:
    if not offsets:
        return []
    offsets = sorted(offsets)
    clusters = [[offsets[0]]]
    for value in offsets[1:]:
        if value - clusters[-1][-1] <= gap:
            clusters[-1].append(value)
        else:
            clusters.append([value])
    return [statistics.median(cluster) for cluster in clusters]


def lane_widths_from_segments(segments, calib: dict, width: int, height: int) -> list[float]:
    """Back-project lane segments and return adjacent lateral spacings (m)."""
    from svld_fit_dims import backproject_ground

    offsets = []
    for seg in segments:
        x1, y1, x2, y2 = seg.x1, seg.y1, seg.x2, seg.y2
        if seg.white < 0.5 or seg.length < 0.04 * height:
            continue
        xs = []
        ys = []
        for t in (0.15, 0.35, 0.5, 0.65, 0.85):
            u = x1 + (x2 - x1) * t
            v = y1 + (y2 - y1) * t
            ground = backproject_ground(u, v, calib, width, height)
            if ground is None:
                continue
            xs.append(float(ground[0]))
            ys.append(float(ground[1]))
        if len(xs) < 3:
            continue
        if statistics.pstdev(xs) > 0.7:
            continue
        y_med = statistics.median(ys)
        if not (5.0 <= y_med <= 100.0):
            continue
        offsets.append(statistics.median(xs))

    centers = cluster_offsets(offsets)
    widths = []
    for a, b in zip(centers, centers[1:]):
        width_m = abs(b - a)
        if 2.4 <= width_m <= 4.6:
            widths.append(width_m)
    return widths


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--single", default="out/svld_geocalib/geocalib_single.json")
    ap.add_argument("--backend", default=str(BACKEND))
    ap.add_argument("--source", choices=["gt", "geo"], default="gt",
                    help="focal used for VP gating and pose")
    ap.add_argument("--out", default="out/svld_vp")
    args = ap.parse_args()

    sys.path.insert(0, args.backend)
    from app.lane_vp import detect_lane_vp
    from app.vp_pose import pose_from_vp

    manifest = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    geo = {}
    if args.source == "geo":
        geo = {
            key(row["image"]): row
            for row in json.loads(Path(args.single).read_text(encoding="utf-8-sig"))
            if "error" not in row
        }

    rows = []
    lane_frames = []
    for item in manifest:
        image_path = item["source"]
        image = cv2.imread(image_path)
        if image is None:
            continue
        height, width = image.shape[:2]
        if args.source == "gt":
            f_px = float(item["f_px"])
        else:
            match = geo.get(key(image_path))
            if match is None:
                continue
            f_px = float(match["f_px"])

        gt_pitch = math.degrees(float(item["pitch_rad"]))
        gt_yaw = math.degrees(float(item["yaw_rad"]))
        result = detect_lane_vp(image, prior_focal=f_px)
        accepted = (
            result.ok
            and result.inliers >= 4
            and result.rms <= 3.0
        )
        row = {
            "split": item["split"],
            "scene": item["scene"],
            "image": item["image"],
            "source": image_path,
            "f_px": round(f_px, 2),
            "accepted": accepted,
            "reason": result.reason,
            "u": round(float(result.u), 2),
            "v": round(float(result.v), 2),
            "inliers": int(result.inliers),
            "total": int(result.total),
            "rms": round(float(result.rms), 3),
            "gt_pitch_deg": round(gt_pitch, 4),
            "gt_yaw_deg": round(gt_yaw, 4),
        }
        if result.ok:
            pitch, yaw = pose_from_vp(
                result.u, result.v, f_px, width / 2.0, height / 2.0, 0.0
            )
            row.update({
                "vp_pitch_deg": round(pitch, 4),
                "vp_yaw_deg": round(yaw, 4),
                "d_pitch_deg": round(abs(pitch - gt_pitch), 4),
                "d_yaw_deg": round(abs(yaw - gt_yaw), 4),
                "pass": accepted and abs(pitch - gt_pitch) < 2.0
                        and abs(yaw - gt_yaw) < 2.0,
            })
        else:
            row.update({
                "vp_pitch_deg": "",
                "vp_yaw_deg": "",
                "d_pitch_deg": "",
                "d_yaw_deg": "",
                "pass": False,
            })
        rows.append(row)

        calib = {
            "f_px": float(item["f_px"]),
            "phi_rad": float(item["pitch_rad"]),
            "theta_rad": float(item["yaw_rad"]),
            "h_m": float(item["h_m"]),
        }
        widths = lane_widths_from_segments(result.segments, calib, width, height)
        lane_frames.append({
            "split": item["split"],
            "scene": item["scene"],
            "image": item["image"],
            "n_widths": len(widths),
            "lane_widths": ";".join(f"{w:.3f}" for w in widths),
        })

    if not rows:
        raise SystemExit("no rows processed; check the manifest and GeoCalib JSON")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / f"vp_{args.source}.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with (out_dir / "lane_width_frames.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(lane_frames[0].keys()))
        writer.writeheader()
        writer.writerows(lane_frames)

    groups = defaultdict(list)
    for row in rows:
        groups[(row["split"], row["scene"])].append(row)
        groups[(row["split"], "*")].append(row)
        groups[("*", "*")].append(row)
    summary = {}
    for (split, scene), items in sorted(groups.items()):
        accepted = [r for r in items if r["accepted"]]
        summary[f"{split}/{scene}"] = {
            "n": len(items),
            "accepted": len(accepted),
            "accepted_pct": round(100 * len(accepted) / len(items), 2),
            "rms": stats([r["rms"] for r in accepted]),
            "inliers": stats([r["inliers"] for r in accepted]),
            "d_pitch_deg": stats([r["d_pitch_deg"] for r in accepted]),
            "d_yaw_deg": stats([r["d_yaw_deg"] for r in accepted]),
            "pass": sum(bool(r["pass"]) for r in items),
            "pass_pct": round(100 * sum(bool(r["pass"]) for r in items) / len(items), 2),
        }

    lane_groups = defaultdict(list)
    for row in lane_frames:
        for text in row["lane_widths"].split(";"):
            if text:
                lane_groups[(row["split"], row["scene"])].append(float(text))
                lane_groups[(row["split"], "*")].append(float(text))
                lane_groups[("*", "*")].append(float(text))
    lane_summary = {}
    for (split, scene), values in sorted(lane_groups.items()):
        values = sorted(values)
        lane_summary[f"{split}/{scene}"] = {
            "n": len(values),
            "median_m": round(statistics.median(values), 3) if values else None,
            "p25_m": round(values[int(0.25 * (len(values) - 1))], 3) if values else None,
            "p75_m": round(values[int(0.75 * (len(values) - 1))], 3) if values else None,
        }

    (out_dir / f"vp_summary_{args.source}.json").write_text(
        json.dumps({"source": args.source, "groups": summary}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "lane_width_summary.json").write_text(
        json.dumps(lane_summary, indent=2), encoding="utf-8"
    )

    print(f"source={args.source} images={len(rows)}")
    for group, s in summary.items():
        print(
            f"{group:24s} n={s['n']:3d} accepted={s['accepted']:3d} "
            f"dpitch med={s['d_pitch_deg'].get('median', float('nan')):5.2f} "
            f"dyaw med={s['d_yaw_deg'].get('median', float('nan')):5.2f} "
            f"pass={s['pass']}/{s['n']}"
        )
    print("lane width (m):")
    for group, s in lane_summary.items():
        print(f"  {group:24s} n={s['n']:4d} median={s['median_m']} IQR={s['p25_m']}..{s['p75_m']}")


if __name__ == "__main__":
    main()
