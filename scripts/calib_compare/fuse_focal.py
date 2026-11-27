#!/usr/bin/env python
"""Fuse GeoCalib and AnyCalib focal-length estimates on Cawang frames.

The dash fit is used only as an evaluation reference, never as an input to the
blind fusion rules.  Outputs a per-frame CSV and a method-summary JSON.

Example:
  py scripts/calib_compare/fuse_focal.py `
    --geo-dir out/calib-compare/fusion `
    --any out/calib-compare/fusion/anycalib_all.json `
    --any-gen out/calib-compare/fusion/anycalib_gen_all.json `
    --geo-multi out/calib-compare/fusion/geocalib_multi_all.json `
    --ref 1082.35 `
    --out-dir out/calib-compare/fusion
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from pathlib import Path

import numpy as np


def frame_key(name: str) -> str:
    """Normalize 'geocalib_tm050', 'tm050_001.png', 'median2' to one key."""
    s = Path(name).stem
    s = re.sub(r"^geocalib_", "", s)
    s = re.sub(r"_001$", "", s)
    return s


def load_geocalib_singles(folder: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted(folder.glob("geocalib_*.json")):
        if path.name.startswith("geocalib_multi"):
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        fx, fy = d.get("fx"), d.get("fy", d.get("fx"))
        if fx is None:
            continue
        out[frame_key(path.name)] = {
            "f": (fx + fy) / 2.0,
            "pitch_deg": d.get("pitch_deg_down_positive"),
            "roll_deg": d.get("roll_deg"),
            "unc_px": d.get("focal_uncertainty_px"),
            "source": str(path),
        }
    return out


def load_anycalib(path: Path) -> dict[str, dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for row in d.get("frames", []):
        intr = row.get("intrinsics", {})
        f = intr.get("f")
        if f is None:
            fx, fy = intr.get("fx"), intr.get("fy")
            if fx is None or fy is None:
                continue
            f = (fx + fy) / 2.0
        out[frame_key(row["frame"])] = {
            "f": f,
            "cx": intr.get("cx"),
            "cy": intr.get("cy"),
            "source": str(path),
        }
    return out


def pct(v: float, ref: float) -> float:
    return (v - ref) / ref * 100.0


def stats(values: list[float], ref: float) -> dict:
    errs = [pct(v, ref) for v in values]
    abs_errs = [abs(e) for e in errs]
    return {
        "n": int(len(values)),
        "bias_pct": float(statistics.fmean(errs)),
        "mae_pct": float(statistics.fmean(abs_errs)),
        "rmse_pct": float(math.sqrt(statistics.fmean(e * e for e in errs))),
        "max_abs_pct": float(max(abs_errs)),
        "pass_5pct": int(sum(bool(e <= 5.0) for e in abs_errs)),
        "pass_10pct": int(sum(bool(e <= 10.0) for e in abs_errs)),
        "median_pct": float(statistics.median(errs)),
    }


def loo_convex(g: np.ndarray, a: np.ndarray, ref: float) -> dict:
    """Fit f = w*g + (1-w)*a with least squares; return in-sample and LOO w."""
    y = ref - a
    x = g - a
    denom = float(np.dot(x, x))
    w_full = float(np.dot(x, y) / denom) if denom else 0.5

    preds = []
    for i in range(len(g)):
        mask = np.ones(len(g), dtype=bool)
        mask[i] = False
        xm, ym = x[mask], y[mask]
        dm = float(np.dot(xm, xm))
        w = float(np.dot(xm, ym) / dm) if dm else 0.5
        preds.append(w * g[i] + (1.0 - w) * a[i])
    return {
        "w_full": w_full,
        "f_full": w_full * float(g.mean()) + (1.0 - w_full) * float(a.mean()),
        "loo_pred": preds,
    }


def loo_scale(fused: np.ndarray, ref: float) -> dict:
    ratios = [ref / v for v in fused]
    preds = []
    for i in range(len(fused)):
        others = [ratios[j] for j in range(len(ratios)) if j != i]
        k = statistics.median(others)
        preds.append(fused[i] * k)
    return {"k_full": statistics.median(ratios), "loo_pred": preds}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo-dir", default="out/calib-compare/fusion")
    ap.add_argument("--any", default="out/calib-compare/fusion/anycalib_all.json")
    ap.add_argument("--any-gen", default="")
    ap.add_argument("--geo-multi", default="")
    ap.add_argument("--ref", type=float, default=1082.35,
                    help="dash-fit reference f in px")
    ap.add_argument("--out-dir", default="out/calib-compare/fusion")
    args = ap.parse_args()

    geo = load_geocalib_singles(Path(args.geo_dir))
    any_d = load_anycalib(Path(args.any))
    any_gen = load_anycalib(Path(args.any_gen)) if args.any_gen else {}

    keys = sorted(set(geo) & set(any_d), key=lambda k: (k == "median2", k))
    if not keys:
        raise SystemExit("no overlapping GeoCalib/AnyCalib frames")
    ref = args.ref

    rows = []
    for k in keys:
        g = geo[k]["f"]
        a = any_d[k]["f"]
        ag = any_gen.get(k, {}).get("f")
        rows.append({
            "frame": k,
            "f_geocalib": g,
            "f_anycalib": a,
            "f_mean": (g + a) / 2.0,
            "f_geom": math.sqrt(g * a),
            "f_harm": 2.0 * g * a / (g + a),
            "f_anycalib_gen": ag,
            "f_mean_gen": (g + ag) / 2.0 if ag is not None else None,
            "err_geocalib_pct": pct(g, ref),
            "err_anycalib_pct": pct(a, ref),
            "err_mean_pct": pct((g + a) / 2.0, ref),
            "err_geom_pct": pct(math.sqrt(g * a), ref),
            "err_harm_pct": pct(2.0 * g * a / (g + a), ref),
            "err_mean_gen_pct": pct((g + ag) / 2.0, ref) if ag is not None else None,
            "pitch_geocalib_deg": geo[k]["pitch_deg"],
            "roll_geocalib_deg": geo[k]["roll_deg"],
            "unc_geocalib_px": geo[k]["unc_px"],
        })

    g_arr = np.array([r["f_geocalib"] for r in rows])
    a_arr = np.array([r["f_anycalib"] for r in rows])
    mean_arr = (g_arr + a_arr) / 2.0
    gen_rows = [r for r in rows if r["f_mean_gen"] is not None]
    gen_mean_arr = np.array([r["f_mean_gen"] for r in gen_rows]) if gen_rows else None

    methods: dict[str, dict] = {}
    methods["geocalib"] = stats([r["f_geocalib"] for r in rows], ref)
    methods["anycalib"] = stats([r["f_anycalib"] for r in rows], ref)
    methods["mean"] = stats(mean_arr.tolist(), ref)
    methods["geom"] = stats([r["f_geom"] for r in rows], ref)
    methods["harmonic"] = stats([r["f_harm"] for r in rows], ref)
    if gen_mean_arr is not None:
        methods["mean_gen"] = stats(gen_mean_arr.tolist(), ref)
        methods["anycalib_gen"] = stats([r["f_anycalib_gen"] for r in gen_rows], ref)

    # Weighted mean w*Geo + (1-w)*Any, per-frame.
    for w in (0.25, 0.4, 0.5, 0.6, 0.75):
        vals = (w * g_arr + (1.0 - w) * a_arr).tolist()
        methods[f"w_geo_{w:.2f}"] = stats(vals, ref)

    # Aggregated static-camera estimates: median per model, then fuse.
    g_med = statistics.median(g_arr)
    a_med = statistics.median(a_arr)
    methods["median_geo"] = stats([g_med], ref)
    methods["median_any"] = stats([a_med], ref)
    methods["median_geo_any_mean"] = stats([(g_med + a_med) / 2.0], ref)
    if args.geo_multi:
        gm = json.loads(Path(args.geo_multi).read_text(encoding="utf-8"))
        g_multi = gm["f_median"]
        methods["geocalib_multi"] = stats([g_multi], ref)
        methods["geocalib_multi_any_median_mean"] = stats(
            [(g_multi + a_med) / 2.0], ref)

    # Calibrated fusion: one convex weight fitted on the same frames (in-sample)
    # and leave-one-out, to show whether the 50/50 rule is special.
    convex = loo_convex(g_arr, a_arr, ref)
    methods["convex_full"] = stats(
        [(convex["w_full"] * g + (1 - convex["w_full"]) * a)
         for g, a in zip(g_arr, a_arr)], ref)
    methods["convex_loo"] = stats(convex["loo_pred"], ref)

    # One scale correction on the 50/50 mean, in-sample and LOO.
    scale = loo_scale(mean_arr, ref)
    methods["mean_scaled_full"] = stats((mean_arr * scale["k_full"]).tolist(), ref)
    methods["mean_scaled_loo"] = stats(scale["loo_pred"], ref)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / "fusion_frames.csv"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v)
                             for k, v in r.items()})

    summary = {
        "reference_f_px": ref,
        "reference_note": "mean of dash fits median2/t350/t500 (1082.58/1082.43/1082.03); not independent GT",
        "n_frames": len(rows),
        "frames": keys,
        "convex_fit": {
            "w_geo_full": float(convex["w_full"]),
            "w_any_full": float(1.0 - convex["w_full"]),
        },
        "scale_fit": {"k_full": float(scale["k_full"])},
        "methods": methods,
    }
    json_path = out_dir / "fusion_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"reference f = {ref:.2f} px; {len(rows)} frames")
    print(f"{'method':<32} {'bias%':>8} {'MAE%':>7} {'RMSE%':>7} {'max%':>7} {'<=5%':>6} {'<=10%':>6}")
    for name, s in methods.items():
        print(f"{name:<32} {s['bias_pct']:8.2f} {s['mae_pct']:7.2f} "
              f"{s['rmse_pct']:7.2f} {s['max_abs_pct']:7.2f} "
              f"{s['pass_5pct']:>3}/{s['n']:<2} {s['pass_10pct']:>3}/{s['n']:<2}")
    print(f"convex weight w_geo = {convex['w_full']:.3f}")
    print(f"scale k = {scale['k_full']:.5f}")
    print(f"wrote {csv_path} and {json_path}")


if __name__ == "__main__":
    main()
