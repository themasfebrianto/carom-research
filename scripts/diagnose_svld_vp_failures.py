#!/usr/bin/env python
"""Diagnose why GeoCalib focal + lane-VP pose fails on SVLD-3D.

The evaluation in ``svld_vp_eval.py`` reports a pass/fail per image, but not
*why* it failed.  This script decomposes the pose error into

  * the part caused by the focal length (VP fixed, f = GeoCalib vs GT), and
  * the part caused by the vanishing point (GT f, detected VP vs GT pose),

and computes, for each image, the focal-length interval that would keep both
pitch and yaw inside a 2 degree gate.  An image is then labelled F_OUT when
GeoCalib's f lies outside that interval while the VP is good, or BOTH when the
VP itself is an outlier.

It also evaluates simple mitigations on the same 100 images:

  * scene-median VP (static camera) instead of the per-image VP,
  * a per-camera focal scale correction (leave-one-out),
  * a per-camera affine focal correction (leave-one-out),
  * the combination of both.

Outputs ``diagnosis.csv`` (one row per image) and ``diagnosis_summary.json``.

Example:
  py scripts/diagnose_svld_vp_failures.py --out out/svld_vp
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


def pose_from_vp(u: float, v: float, f: float, cx: float, cy: float) -> tuple[float, float]:
    """Pitch/yaw from a road VP at zero roll (same as app.vp_pose)."""
    xn = (u - cx) / f
    yn = (v - cy) / f
    pitch = math.degrees(math.atan(-yn))
    yaw = math.degrees(math.atan(-xn * math.cos(math.radians(pitch))))
    return pitch, yaw


def pose_error(
    u: float, v: float, f: float, cx: float, cy: float,
    gt_pitch: float, gt_yaw: float,
) -> tuple[float, float, float]:
    pitch, yaw = pose_from_vp(u, v, f, cx, cy)
    dp = abs(pitch - gt_pitch)
    dy = abs(yaw - gt_yaw)
    return max(dp, dy), dp, dy


def tolerance_window(
    u: float, v: float, f_gt: float, cx: float, cy: float,
    gt_pitch: float, gt_yaw: float, gate: float,
) -> tuple[float, float, bool, float, float, float]:
    """Focal interval [f_lo, f_hi] that keeps max(dpitch, dyaw) < gate.

    Returns (f_lo, f_hi, empty, error_at_f_gt, dpitch_at_f_gt, dyaw_at_f_gt).
    The pose error is monotonic in f on each side of f_gt, so the interval is
    contiguous.  If the VP itself is bad, the interval is empty.
    """
    e0, dp0, dy0 = pose_error(u, v, f_gt, cx, cy, gt_pitch, gt_yaw)
    if e0 >= gate:
        return f_gt, f_gt, True, e0, dp0, dy0

    def boundary(direction: int) -> float:
        previous = f_gt
        current = f_gt
        for _ in range(1200):
            current *= 1.0 + direction * 0.01
            if current <= 1.0 or current > 1e7:
                return current
            if pose_error(u, v, current, cx, cy, gt_pitch, gt_yaw)[0] >= gate:
                lo, hi = previous, current
                for _ in range(60):
                    mid = 0.5 * (lo + hi)
                    if pose_error(u, v, mid, cx, cy, gt_pitch, gt_yaw)[0] >= gate:
                        hi = mid
                    else:
                        lo = mid
                return 0.5 * (lo + hi)
            previous = current
        return current

    return boundary(-1), boundary(+1), False, e0, dp0, dy0


def pass_pose(
    u: float, v: float, f: float, cx: float, cy: float,
    gt_pitch: float, gt_yaw: float, gate: float,
) -> bool:
    return pose_error(u, v, f, cx, cy, gt_pitch, gt_yaw)[0] < gate


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vp-geo", default="out/svld_vp/vp_geo.csv")
    ap.add_argument("--vp-gt", default="out/svld_vp/vp_gt.csv")
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--out", default="out/svld_vp")
    ap.add_argument("--gate", type=float, default=2.0)
    args = ap.parse_args()

    root = Path.cwd()
    geo = list(csv.DictReader((root / args.vp_geo).open(encoding="utf-8")))
    gt_rows = list(csv.DictReader((root / args.vp_gt).open(encoding="utf-8")))
    gt = {r["image"]: r for r in gt_rows}
    manifest = list(csv.DictReader((root / args.manifest).open(encoding="utf-8")))
    dims = {r["image"]: (int(r["width"]), int(r["height"])) for r in manifest}

    rows = []
    for r in geo:
        g = gt[r["image"]]
        w_img, h_img = dims[r["image"]]
        cx, cy = w_img / 2.0, h_img / 2.0
        u, v = float(r["u"]), float(r["v"])
        f_geo = float(r["f_px"])
        f_gt = float(g["f_px"])
        gt_pitch = float(r["gt_pitch_deg"])
        gt_yaw = float(r["gt_yaw_deg"])

        p_geo, y_geo = pose_from_vp(u, v, f_geo, cx, cy)
        p_gtf, y_gtf = pose_from_vp(u, v, f_gt, cx, cy)
        f_lo, f_hi, empty, e0, dp0, dy0 = tolerance_window(
            u, v, f_gt, cx, cy, gt_pitch, gt_yaw, args.gate
        )
        in_window = (not empty) and (f_lo <= f_geo <= f_hi)
        total_err = max(abs(p_geo - gt_pitch), abs(y_geo - gt_yaw))
        vp_err = max(abs(p_gtf - gt_pitch), abs(y_gtf - gt_yaw))
        passed = total_err < args.gate

        if passed:
            cause = "PASS"
        elif empty or vp_err >= args.gate:
            cause = "BOTH" if not in_window else "VP"
        elif not in_window:
            cause = "F_OUT"
        else:
            cause = "OTHER"

        f_err_pct = 100.0 * (f_geo - f_gt) / f_gt
        f_lo_pct = 100.0 * (f_lo - f_gt) / f_gt
        f_hi_pct = 100.0 * (f_hi - f_gt) / f_gt
        if passed:
            detail = f"f in window; VP err {vp_err:.2f} deg"
        elif cause == "F_OUT":
            detail = (f"f_geo {f_err_pct:+.1f}% outside window "
                      f"[{f_lo_pct:+.1f}%, {f_hi_pct:+.1f}%]; VP err {vp_err:.2f} deg")
        elif cause == "BOTH":
            detail = (f"VP outlier (v={v:.1f}, VP err {vp_err:.2f} deg); "
                      f"f also outside window ({f_err_pct:+.1f}%)")
        elif cause == "VP":
            detail = f"VP outlier (VP err {vp_err:.2f} deg); f in window"
        else:
            detail = f"error just over gate; f in window; VP err {vp_err:.2f} deg"

        rows.append({
            "split": r["split"],
            "scene": r["scene"],
            "image": r["image"],
            "f_geo": round(f_geo, 2),
            "f_gt": round(f_gt, 2),
            "f_err_pct": round(f_err_pct, 3),
            "cx": cx,
            "cy": cy,
            "u": round(u, 2),
            "v": round(v, 2),
            "inliers": int(r["inliers"]),
            "rms": round(float(r["rms"]), 3),
            "gt_pitch_deg": round(gt_pitch, 4),
            "gt_yaw_deg": round(gt_yaw, 4),
            "pitch_geo_deg": round(p_geo, 4),
            "yaw_geo_deg": round(y_geo, 4),
            "pitch_gtf_deg": round(p_gtf, 4),
            "yaw_gtf_deg": round(y_gtf, 4),
            "d_pitch_total": round(abs(p_geo - gt_pitch), 4),
            "d_yaw_total": round(abs(y_geo - gt_yaw), 4),
            "d_pitch_f": round(abs(p_geo - p_gtf), 4),
            "d_yaw_f": round(abs(y_geo - y_gtf), 4),
            "d_pitch_vp": round(abs(p_gtf - gt_pitch), 4),
            "d_yaw_vp": round(abs(y_gtf - gt_yaw), 4),
            "f_lo": round(f_lo, 2),
            "f_hi": round(f_hi, 2),
            "f_lo_pct": round(f_lo_pct, 3),
            "f_hi_pct": round(f_hi_pct, 3),
            "window_empty": bool(empty),
            "f_in_window": bool(in_window),
            "vp_err_at_gt_deg": round(vp_err, 4),
            "pass": bool(passed),
            "cause": cause,
            "detail": detail,
        })

    scenes = sorted({r["scene"] for r in rows})
    by_scene = {s: [r for r in rows if r["scene"] == s] for s in scenes}

    # --- Mitigations -----------------------------------------------------
    def scene_medians(sub: list[dict], exclude: str | None = None):
        others = [r for r in sub if r["image"] != exclude]
        u_med = statistics.median(r["u"] for r in others)
        v_med = statistics.median(r["v"] for r in others)
        f_med = statistics.median(r["f_geo"] for r in others)
        ratio = statistics.median(r["f_gt"] / r["f_geo"] for r in others)
        return u_med, v_med, f_med, ratio

    def affine_correction(sub: list[dict], r: dict) -> float:
        others = [x for x in sub if x["image"] != r["image"]]
        x = np.array([x["f_geo"] for x in others], dtype=float)
        y = np.array([x["f_gt"] for x in others], dtype=float)
        if len(x) < 3 or np.ptp(x) < 1e-6:
            _, _, _, ratio = scene_medians(sub, r["image"])
            return r["f_geo"] * ratio
        a, b = np.polyfit(x, y, 1)
        return float(a * r["f_geo"] + b)

    methods = {
        "per_image_vp_geo_f": 0,
        "per_image_vp_gt_f": 0,
        "per_image_vp_loo_scale": 0,
        "per_image_vp_loo_median_f": 0,
        "loo_median_vp_geo_f": 0,
        "loo_median_vp_loo_scale": 0,
        "loo_median_vp_gt_f": 0,
        "per_image_vp_loo_affine": 0,
        "loo_median_vp_loo_affine": 0,
    }
    scene_methods = {s: Counter() for s in scenes}
    for s, sub in by_scene.items():
        for r in sub:
            u, v = r["u"], r["v"]
            u_med, v_med, f_med, ratio = scene_medians(sub, r["image"])
            f_aff = affine_correction(sub, r)
            cases = {
                "per_image_vp_geo_f": (u, v, r["f_geo"]),
                "per_image_vp_gt_f": (u, v, r["f_gt"]),
                "per_image_vp_loo_scale": (u, v, r["f_geo"] * ratio),
                "per_image_vp_loo_median_f": (u, v, f_med),
                "loo_median_vp_geo_f": (u_med, v_med, r["f_geo"]),
                "loo_median_vp_loo_scale": (u_med, v_med, r["f_geo"] * ratio),
                "loo_median_vp_gt_f": (u_med, v_med, r["f_gt"]),
                "per_image_vp_loo_affine": (u, v, f_aff),
                "loo_median_vp_loo_affine": (u_med, v_med, f_aff),
            }
            for name, (uu, vv, ff) in cases.items():
                good = pass_pose(
                    uu, vv, ff, r["cx"], r["cy"],
                    r["gt_pitch_deg"], r["gt_yaw_deg"], args.gate,
                )
                methods[name] += int(good)
                scene_methods[s][name] += int(good)

    # How sensitive is a one-frame per-camera scale anchor?
    single_anchor = {}
    for s, sub in by_scene.items():
        passes = []
        for anchor in sub:
            ratio = anchor["f_gt"] / anchor["f_geo"]
            others = [x for x in sub if x["image"] != anchor["image"]]
            u_med = statistics.median(x["u"] for x in others)
            v_med = statistics.median(x["v"] for x in others)
            for use_median_vp in (False, True):
                n = 0
                for r in others:
                    uu, vv = (u_med, v_med) if use_median_vp else (r["u"], r["v"])
                    if pass_pose(uu, vv, r["f_geo"] * ratio, r["cx"], r["cy"],
                                 r["gt_pitch_deg"], r["gt_yaw_deg"], args.gate):
                        n += 1
                passes.append((use_median_vp, n))
        single_anchor[s] = {
            "per_image_vp": {
                "min": min(n for med, n in passes if not med),
                "median": statistics.median(n for med, n in passes if not med),
                "max": max(n for med, n in passes if not med),
            },
            "median_vp": {
                "min": min(n for med, n in passes if med),
                "median": statistics.median(n for med, n in passes if med),
                "max": max(n for med, n in passes if med),
            },
            "n_other_frames": len(sub) - 1,
        }

    summary = {
        "n": len(rows),
        "gate_deg": args.gate,
        "causes": dict(Counter(r["cause"] for r in rows)),
        "scenes": {
            s: {
                "n": len(sub),
                "pass": sum(r["pass"] for r in sub),
                "causes": dict(Counter(r["cause"] for r in sub)),
                "f_in_window": sum(r["f_in_window"] for r in sub),
                "window_low_pct_median": round(statistics.median(
                    max(-99.0, r["f_lo_pct"]) for r in sub), 2),
                "window_high_pct_median": round(statistics.median(
                    min(99.0, r["f_hi_pct"]) for r in sub), 2),
                "median_f_ratio_gt_over_geo": round(statistics.median(
                    r["f_gt"] / r["f_geo"] for r in sub), 4),
            }
            for s, sub in by_scene.items()
        },
        "mitigations": methods,
        "mitigations_by_scene": {s: dict(c) for s, c in scene_methods.items()},
        "single_anchor_scale": single_anchor,
        "vp_outliers": [
            {
                "scene": r["scene"], "image": r["image"],
                "u": r["u"], "v": r["v"], "inliers": r["inliers"],
                "vp_err_at_gt_deg": r["vp_err_at_gt_deg"],
                "cause": r["cause"],
            }
            for r in rows if r["vp_err_at_gt_deg"] >= args.gate
        ],
    }

    out = root / args.out
    out.mkdir(parents=True, exist_ok=True)
    with (out / "diagnosis.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (out / "diagnosis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"n={len(rows)} pass={sum(r['pass'] for r in rows)} "
          f"causes={summary['causes']}")
    for s, info in summary["scenes"].items():
        print(f"  {s:18s} pass={info['pass']:2d}/{info['n']:2d} "
              f"causes={info['causes']} "
              f"window={info['window_low_pct_median']:+.1f}%..{info['window_high_pct_median']:+.1f}%")
    print("mitigations:")
    for name, n in methods.items():
        print(f"  {name:32s} {n:3d}/100")
    print("single-anchor scale (median pass over other frames):")
    for s, info in single_anchor.items():
        print(f"  {s:18s} per-image VP {info['per_image_vp']}  median VP {info['median_vp']}")
    print(f"wrote {out / 'diagnosis.csv'} and diagnosis_summary.json")


if __name__ == "__main__":
    main()
