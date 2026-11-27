#!/usr/bin/env python
"""Cawang: median road VP + per-camera focal anchor.

The Cawang reference is the dash fit with ``w = 3.60 m`` (not an independent
ground truth).  This script tests the mitigation proposed for SVLD:

  1. detect the road VP on the 8 temporal-median Cawang frames,
  2. take the temporal median VP,
  3. correct the focal length with a per-camera scale ``s = f_anchor/f_geo``,
  4. compare f, pitch, and yaw with the Cawang dash-fit reference.

Three anchors are compared:
  * ``dash``  — the dash-fit f (oracle, uses the reference),
  * ``blind`` — the median of ``f_50/50 / f_geocalib`` (no dash reference),
  * ``single``— one other frame's 50/50 fusion as the anchor (leave-one-out).

Example:
  py scripts/calib_compare/cawang_median_vp_anchor.py \
      --out out/calib-compare/fusion
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(r"D:\Kerjaan\LearnPinhole\backend")

# Cawang dash-fit reference: mean of median2 / t350 / t500.
F_REF = 1082.35
PITCH_REF = 2.466
YAW_REF = 0.287
CX, CY = 640.0, 360.0


def pose(u: float, v: float, f: float) -> tuple[float, float]:
    """Pitch/yaw in the Cawang/dash convention (positive down/right)."""
    pitch = math.degrees(math.atan2(CY - v, f))
    yaw = math.degrees(math.atan2((u - CX) * math.cos(math.radians(pitch)), f))
    return pitch, yaw


def detect_vp(image_path: Path) -> dict:
    sys.path.insert(0, str(BACKEND))
    from app.lane_vp import detect_lane_vp

    image = cv2.imread(str(image_path))
    if image is None:
        raise RuntimeError(f"cannot read {image_path}")
    result = detect_lane_vp(image, prior_focal=F_REF)
    if not result.ok:
        raise RuntimeError(f"VP failed on {image_path.name}: {result.reason}")
    return {
        "u": float(result.u),
        "v": float(result.v),
        "inliers": int(result.inliers),
        "total": int(result.total),
        "rms": float(result.rms),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frames-csv", default="reports/calib-compare/fusion_frames.csv")
    ap.add_argument("--frames-dir", default="out/calib-compare/fusion/frames_all8")
    ap.add_argument("--out", default="out/calib-compare/fusion")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((ROOT / args.frames_csv).open(encoding="utf-8")))
    frames_dir = ROOT / args.frames_dir

    vp = {}
    for row in rows:
        frame = row["frame"]
        matches = sorted(frames_dir.glob(f"{frame}*.png"))
        if not matches:
            raise FileNotFoundError(f"no image for frame {frame} in {frames_dir}")
        vp[frame] = detect_vp(matches[0])
        print(f"{frame:8s} VP=({vp[frame]['u']:8.2f}, {vp[frame]['v']:8.2f}) "
              f"inliers={vp[frame]['inliers']:2d} rms={vp[frame]['rms']:.2f}")

    u_med = statistics.median(v["u"] for v in vp.values())
    v_med = statistics.median(v["v"] for v in vp.values())
    print(f"median VP=({u_med:.2f}, {v_med:.2f})")
    (out_dir / "cawang_vp8.json").write_text(
        json.dumps({"vp": vp, "median": {"u": u_med, "v": v_med}}, indent=2),
        encoding="utf-8",
    )

    geo = {r["frame"]: float(r["f_geocalib"]) for r in rows}
    anyc = {r["frame"]: float(r["f_anycalib"]) for r in rows}
    mean = {r["frame"]: float(r["f_mean"]) for r in rows}

    scale_dash = F_REF / statistics.median(geo.values())
    scale_blind = statistics.median(
        mean[f] / geo[f] for f in geo
    )

    variants = {
        "geo_raw": {f: geo[f] for f in geo},
        "mean_raw": {f: mean[f] for f in geo},
        "geo_dash_scale": {f: geo[f] * scale_dash for f in geo},
        "mean_dash_scale": {f: mean[f] * (F_REF / statistics.median(mean.values())) for f in geo},
        "geo_blind_scale": {f: geo[f] * scale_blind for f in geo},
    }

    def stats(fs: dict[str, float]) -> dict:
        ferr = [abs(fs[f] - F_REF) / F_REF * 100 for f in fs]
        poses = {f: pose(u_med, v_med, fs[f]) for f in fs}
        dp = [abs(poses[f][0] - PITCH_REF) for f in fs]
        dy = [abs(poses[f][1] - YAW_REF) for f in fs]
        return {
            "n": len(fs),
            "f_median": statistics.median(fs.values()),
            "df_pct_median": statistics.median(ferr),
            "df_pct_max": max(ferr),
            "pass_f_5pct": sum(e < 5 for e in ferr),
            "dpitch_median": statistics.median(dp),
            "dpitch_max": max(dp),
            "dyaw_median": statistics.median(dy),
            "dyaw_max": max(dy),
            "pass_pose_2deg": sum(p < 2 and y < 2 for p, y in zip(dp, dy)),
        }

    summary = {
        "reference": {"f": F_REF, "pitch_deg": PITCH_REF, "yaw_deg": YAW_REF,
                      "note": "dash fit w=3.60 m; not independent GT"},
        "median_vp": {"u": u_med, "v": v_med},
        "pose_at_reference_f": pose(u_med, v_med, F_REF),
        "scale_dash": scale_dash,
        "scale_blind": scale_blind,
        "variants": {name: stats(fs) for name, fs in variants.items()},
    }

    # Leave-one-out single anchor: use another frame's 50/50 f as the anchor.
    loo = []
    for i, frame in enumerate(geo):
        for j, anchor in enumerate(geo):
            if i == j:
                continue
            f_corr = geo[frame] * (mean[anchor] / geo[anchor])
            loo.append(f_corr)
    loo_err = [abs(f - F_REF) / F_REF * 100 for f in loo]
    loo_poses = [pose(u_med, v_med, f) for f in loo]
    summary["single_anchor_loo"] = {
        "n": len(loo),
        "df_pct_median": statistics.median(loo_err),
        "df_pct_max": max(loo_err),
        "pass_f_5pct": sum(e < 5 for e in loo_err),
        "dpitch_max": max(abs(p - PITCH_REF) for p, y in loo_poses),
        "dyaw_max": max(abs(y - YAW_REF) for p, y in loo_poses),
        "pass_pose_2deg": sum(
            abs(p - PITCH_REF) < 2 and abs(y - YAW_REF) < 2 for p, y in loo_poses
        ),
    }

    with (out_dir / "median_vp_anchor_frames.csv").open("w", newline="", encoding="utf-8") as fh:
        fields = ["frame", "f_geo", "f_anycalib", "f_mean", "f_dash_scale",
                  "f_blind_scale", "df_geo_pct", "df_mean_pct", "df_dash_scale_pct",
                  "df_blind_scale_pct", "pitch_geo", "yaw_geo", "pitch_mean", "yaw_mean",
                  "pitch_dash_scale", "yaw_dash_scale", "pitch_blind_scale", "yaw_blind_scale"]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for frame in geo:
            p_geo = pose(u_med, v_med, geo[frame])
            p_mean = pose(u_med, v_med, mean[frame])
            p_dash = pose(u_med, v_med, geo[frame] * scale_dash)
            p_blind = pose(u_med, v_med, geo[frame] * scale_blind)
            writer.writerow({
                "frame": frame,
                "f_geo": round(geo[frame], 2),
                "f_anycalib": round(anyc[frame], 2),
                "f_mean": round(mean[frame], 2),
                "f_dash_scale": round(geo[frame] * scale_dash, 2),
                "f_blind_scale": round(geo[frame] * scale_blind, 2),
                "df_geo_pct": round(100 * (geo[frame] - F_REF) / F_REF, 2),
                "df_mean_pct": round(100 * (mean[frame] - F_REF) / F_REF, 2),
                "df_dash_scale_pct": round(100 * (geo[frame] * scale_dash - F_REF) / F_REF, 2),
                "df_blind_scale_pct": round(100 * (geo[frame] * scale_blind - F_REF) / F_REF, 2),
                "pitch_geo": round(p_geo[0], 4), "yaw_geo": round(p_geo[1], 4),
                "pitch_mean": round(p_mean[0], 4), "yaw_mean": round(p_mean[1], 4),
                "pitch_dash_scale": round(p_dash[0], 4), "yaw_dash_scale": round(p_dash[1], 4),
                "pitch_blind_scale": round(p_blind[0], 4), "yaw_blind_scale": round(p_blind[1], 4),
            })

    (out_dir / "median_vp_anchor_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print("\nreference:", summary["reference"])
    print("pose at f_ref:", tuple(round(x, 4) for x in summary["pose_at_reference_f"]))
    for name, s in summary["variants"].items():
        print(f"{name:18s} f={s['f_median']:7.1f} |df| med={s['df_pct_median']:4.2f}% "
              f"max={s['df_pct_max']:4.2f}% passF={s['pass_f_5pct']}/{s['n']} "
              f"|dp| med={s['dpitch_median']:.3f} max={s['dpitch_max']:.3f} "
              f"|dy| med={s['dyaw_median']:.3f} max={s['dyaw_max']:.3f} "
              f"passPose={s['pass_pose_2deg']}/{s['n']}")
    s = summary["single_anchor_loo"]
    print(f"single_anchor_loo  |df| med={s['df_pct_median']:.2f}% max={s['df_pct_max']:.2f}% "
          f"passF={s['pass_f_5pct']}/{s['n']} passPose={s['pass_pose_2deg']}/{s['n']}")
    print(f"wrote {out_dir / 'median_vp_anchor_frames.csv'}")
    print(f"wrote {out_dir / 'median_vp_anchor_summary.json'}")


if __name__ == "__main__":
    main()
