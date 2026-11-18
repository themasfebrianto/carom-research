#!/usr/bin/env python
"""Sensitivity of SVLD 3D-box fitting to 2D corner noise.

For each selected object:
  1. fit the noise-free corners to get the true order and solution;
  2. add independent Gaussian noise (sigma px) to the 8 corners;
  3. refit with the same order, starting from the noise-free solution;
  4. compare L/W/H with veh_size.

This is a local error-budget test, not a detector benchmark. Correlated detector
errors and wrong corner ordering are separate failure modes.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from svld_fit_dims import (
    parse_annotation,
    select_objects,
    fit_object,
    box_corners,
    project,
    residuals,
    stats,
)

LO = np.array([-500.0, -500.0, -math.pi, 2.0, 1.0, 1.0])
HI = np.array([500.0, 500.0, math.pi, 20.0, 3.5, 4.5])


def canonical_order(obs: np.ndarray, rev: bool, shift: int) -> np.ndarray:
    base = np.vstack([obs[:4][::-1], obs[4:][::-1]]) if rev else obs
    idx = [(i + shift) % 4 for i in range(4)]
    return np.vstack([base[idx], base[[i + 4 for i in idx]]])


def fit_fixed(obs: np.ndarray, calib: dict, width: int, height: int, p0: np.ndarray):
    p0 = np.clip(p0, LO + 1e-6, HI - 1e-6)
    return least_squares(
        residuals, p0, args=(obs, calib, width, height),
        bounds=(LO, HI), loss="linear", max_nfev=300, x_scale="jac",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"data\svld\TESTDATA2021\TESTDATA2021")
    ap.add_argument("--out", default=r"out\svld")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--sigmas", nargs="+", type=float, default=[0.0, 0.5, 1.0, 2.0, 3.0, 5.0])
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.root)
    anns = sorted((root / "Annotations").glob("*.xml"))
    objects = []
    for i, ann in enumerate(anns, 1):
        parsed = parse_annotation(ann, root / "Calib")
        if parsed:
            objects.extend(parsed)
        if i % 500 == 0:
            print(f"  parse {i}/{len(anns)}...", flush=True)

    selected = select_objects(objects, args.n, args.seed)
    print(f"selected {len(selected)} objects")

    # Noise-free fit: establish the true order and solution.
    prepared = []
    for i, obj in enumerate(selected, 1):
        best = fit_object(obj["vertex2d"], obj["calib_data"],
                          obj["width"], obj["height"], obj["class"])
        if best is None:
            continue
        obs_canon = canonical_order(obj["vertex2d"], best.rev, best.shift)
        pred = project(box_corners(best.x), obj["calib_data"],
                       obj["width"], obj["height"])
        rms = float(np.sqrt(np.mean(np.sum((pred - obs_canon) ** 2, axis=1))))
        prepared.append((obj, best.x, obs_canon, rms))
        print(f"  prep {i}/{len(selected)} {obj['image']} rms={rms:.2f}px", flush=True)

    rng = random.Random(args.seed)
    rows = []
    for sigma in args.sigmas:
        for rep in range(args.reps if sigma > 0 else 1):
            for obj, p_true, obs_canon, rms0 in prepared:
                if sigma > 0:
                    noise = np.array([[rng.gauss(0, sigma), rng.gauss(0, sigma)]
                                      for _ in range(8)])
                    obs = obs_canon + noise
                else:
                    obs = obs_canon.copy()

                result = fit_fixed(obs, obj["calib_data"], obj["width"],
                                   obj["height"], p_true)
                L, W, H = result.x[3], result.x[4], result.x[5]
                pred = project(box_corners(result.x), obj["calib_data"],
                               obj["width"], obj["height"])
                rms = float(np.sqrt(np.mean(np.sum((pred - obs) ** 2, axis=1))))
                at_bound = any(abs(result.x[i] - LO[i]) < 1e-3 or
                               abs(result.x[i] - HI[i]) < 1e-3 for i in (3, 4, 5))
                rows.append({
                    "sigma_px": sigma,
                    "rep": rep,
                    "image": obj["image"],
                    "class": obj["class"],
                    "distance_m": round(obj["distance_m"], 2),
                    "L_gt": obj["L_gt"], "W_gt": obj["W_gt"], "H_gt": obj["H_gt"],
                    "L_fit": round(float(L), 3),
                    "W_fit": round(float(W), 3),
                    "H_fit": round(float(H), 3),
                    "eL_pct": round(abs(L - obj["L_gt"]) / obj["L_gt"] * 100, 3),
                    "eW_pct": round(abs(W - obj["W_gt"]) / obj["W_gt"] * 100, 3),
                    "eH_pct": round(abs(H - obj["H_gt"]) / obj["H_gt"] * 100, 3),
                    "rms_px": round(rms, 3),
                    "failed": int(rms > 5.0 or at_bound),
                })
        print(f"  sigma {sigma:g} px done", flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    csv_path = out / "sensitivity.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    summary = {}
    for sigma in args.sigmas:
        sub = [r for r in rows if r["sigma_px"] == sigma]
        ok = [r for r in sub if not r["failed"]]
        summary[str(sigma)] = {
            "n": len(sub),
            "ok": len(ok),
            "failed": len(sub) - len(ok),
            "mape_pct": stats([(r["eL_pct"] + r["eW_pct"] + r["eH_pct"]) / 3 for r in ok]),
            "eL_pct": stats([r["eL_pct"] for r in ok]),
            "eW_pct": stats([r["eW_pct"] for r in ok]),
            "eH_pct": stats([r["eH_pct"] for r in ok]),
            "rms_px": stats([r["rms_px"] for r in ok]),
        }
    (out / "sensitivity_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n| sigma | n | fail | MAPE mean | MAPE p90 | L mean | W mean | H mean |")
    print("|---:|---:|---:|---:|---:|---:|---:|---:|")
    for sigma in args.sigmas:
        s = summary[str(sigma)]
        m = s["mape_pct"]
        print(f"| {sigma:g} | {s['n']} | {s['failed']} | "
              f"{m['mean']:.2f}% | {m['p90']:.2f}% | "
              f"{s['eL_pct']['mean']:.2f}% | {s['eW_pct']['mean']:.2f}% | "
              f"{s['eH_pct']['mean']:.2f}% |")
    print(f"\nwrote {csv_path}")


if __name__ == "__main__":
    main()
