#!/usr/bin/env python
"""Which corner subsets still constrain L/W/H?

For each object, fit the 3D box using only a subset of the 8 annotated corners.
Dimensions are initialised from class priors, not from GT, so an unobserved
dimension stays at its prior and shows up as an error.

This is an information-content test, not a detector benchmark.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from svld_fit_dims import (
    parse_annotation,
    select_objects,
    fit_object,
    box_corners,
    project,
    stats,
)
from svld_sensitivity import canonical_order, LO, HI

PRIORS = {
    "Car": (4.5, 1.8, 1.5),
    "Bus": (11.0, 2.7, 2.9),
    "Truck": (7.0, 2.3, 2.8),
}

SUBSETS = {
    "all8": list(range(8)),
    "bottom4_top2": [0, 1, 2, 3, 4, 5],
    "bottom4_top1": [0, 1, 2, 3, 4],
    "bottom4": [0, 1, 2, 3],
    "top4": [4, 5, 6, 7],
    "bottom2_top2": [0, 1, 4, 5],
}


def fit_subset(obs, idx, calib, width, height, p0):
    def res(p):
        pred = project(box_corners(p), calib, width, height)
        return (pred[idx] - obs[idx]).ravel()

    return least_squares(
        res, np.clip(p0, LO + 1e-6, HI - 1e-6),
        bounds=(LO, HI), loss="linear", max_nfev=300, x_scale="jac",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"data\svld\TESTDATA2021\TESTDATA2021")
    ap.add_argument("--out", default=r"out\svld")
    ap.add_argument("--n", type=int, default=50)
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

    rows = []
    for i, obj in enumerate(selected, 1):
        best = fit_object(obj["vertex2d"], obj["calib_data"],
                          obj["width"], obj["height"], obj["class"])
        if best is None:
            continue
        obs = canonical_order(obj["vertex2d"], best.rev, best.shift)
        L0, W0, H0 = PRIORS.get(obj["class"], (5.0, 2.0, 2.0))
        p0 = np.array([best.x[0], best.x[1], best.x[2], L0, W0, H0])

        for name, idx in SUBSETS.items():
            result = fit_subset(obs, idx, obj["calib_data"],
                                obj["width"], obj["height"], p0)
            L, W, H = result.x[3], result.x[4], result.x[5]
            pred = project(box_corners(result.x), obj["calib_data"],
                           obj["width"], obj["height"])
            rms = float(np.sqrt(np.mean(np.sum((pred[idx] - obs[idx]) ** 2, axis=1))))
            at_bound = any(abs(result.x[j] - LO[j]) < 1e-3 or
                           abs(result.x[j] - HI[j]) < 1e-3 for j in (3, 4, 5))
            rows.append({
                "image": obj["image"],
                "class": obj["class"],
                "distance_m": round(obj["distance_m"], 2),
                "subset": name,
                "n_corners": len(idx),
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
        if i % 10 == 0:
            print(f"  {i}/{len(selected)}...", flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "subsets.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {}
    for name in SUBSETS:
        sub = [r for r in rows if r["subset"] == name]
        ok = [r for r in sub if not r["failed"]]
        summary[name] = {
            "n": len(sub),
            "ok": len(ok),
            "failed": len(sub) - len(ok),
            "mape_pct": stats([(r["eL_pct"] + r["eW_pct"] + r["eH_pct"]) / 3 for r in ok]),
            "eL_pct": stats([r["eL_pct"] for r in ok]),
            "eW_pct": stats([r["eW_pct"] for r in ok]),
            "eH_pct": stats([r["eH_pct"] for r in ok]),
        }
    (out / "subsets_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n| Subset | n corner | fail | MAPE | L | W | H |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for name, s in summary.items():
        m = s["mape_pct"]
        print(f"| {name} | {next(r['n_corners'] for r in rows if r['subset']==name)} | "
              f"{s['failed']} | {m['mean']:.2f}% | {s['eL_pct']['mean']:.2f}% | "
              f"{s['eW_pct']['mean']:.2f}% | {s['eH_pct']['mean']:.2f}% |")
    print(f"\nwrote {csv_path}")


if __name__ == "__main__":
    main()
