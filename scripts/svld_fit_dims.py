#!/usr/bin/env python
"""Fit a 3D box to SVLD-3D 2D corners and compare dimensions with GT.

This is a geometry test, not a detector test: the 8 observed corners are the
annotated projections of the GT box. If the fit recovers veh_size, the camera
model and box parameterisation are correct. A real detector would replace the
observed corners with predicted ones.

Camera model follows CenterLoc3D Eq. 2:
  R = Rx(phi + pi/2) Rz(theta)
  P_c = R (P - [0, 0, h])
  u = f x_c / z_c + cx,  v = f y_c / z_c + cy
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import least_squares


def numbers(text: str) -> list[float]:
    return [float(x) for x in text.replace("(", "").replace(")", "").replace(",", " ").split()]


def parse_calib(path: Path) -> dict:
    root = ET.parse(path).getroot()
    raw = {child.tag: (child.text or "").strip() for child in root}
    return {
        "f_px": float(raw["f"]),
        "phi_rad": float(raw["fi"]),
        "theta_rad": float(raw["theta"]),
        "h_m": float(raw["h"]) / 1000.0,
    }


def rotation(phi: float, theta: float) -> np.ndarray:
    return np.array([
        [math.cos(theta), -math.sin(theta), 0.0],
        [-math.sin(phi) * math.sin(theta), -math.sin(phi) * math.cos(theta), -math.cos(phi)],
        [math.cos(phi) * math.sin(theta), math.cos(phi) * math.cos(theta), -math.sin(phi)],
    ])


def project(points_m: np.ndarray, calib: dict, width: int, height: int) -> np.ndarray:
    R = rotation(calib["phi_rad"], calib["theta_rad"])
    Pc = (R @ (points_m - np.array([0.0, 0.0, calib["h_m"]])).T).T
    cx, cy = width / 2.0, height / 2.0
    return np.stack([
        calib["f_px"] * Pc[:, 0] / Pc[:, 2] + cx,
        calib["f_px"] * Pc[:, 1] / Pc[:, 2] + cy,
    ], axis=1)


def backproject_ground(u: float, v: float, calib: dict, width: int, height: int):
    R = rotation(calib["phi_rad"], calib["theta_rad"])
    cx, cy = width / 2.0, height / 2.0
    d_c = np.array([(u - cx) / calib["f_px"], (v - cy) / calib["f_px"], 1.0])
    d_w = R.T @ d_c
    if abs(d_w[2]) < 1e-9:
        return None
    t = -calib["h_m"] / d_w[2]
    if t <= 0:
        return None
    return np.array([0.0, 0.0, calib["h_m"]]) + t * d_w


def box_corners(p: np.ndarray) -> np.ndarray:
    X, Y, yaw, L, W, H = p
    local = np.array([
        [W / 2, -L / 2],
        [-W / 2, -L / 2],
        [-W / 2, L / 2],
        [W / 2, L / 2],
    ])
    c, s = math.cos(yaw), math.sin(yaw)
    xy = local @ np.array([[c, s], [-s, c]])
    xy[:, 0] += X
    xy[:, 1] += Y
    bottom = np.column_stack([xy, np.zeros(4)])
    top = np.column_stack([xy, np.full(4, H)])
    return np.vstack([bottom, top])


def residuals(p, obs, calib, width, height):
    return (project(box_corners(p), calib, width, height) - obs).ravel()


def fit_object(obs: np.ndarray, calib: dict, width: int, height: int,
               cls: str, yaw_hint: float = 0.0):
    bottom_center = obs[:4].mean(axis=0)
    ground = backproject_ground(float(bottom_center[0]), float(bottom_center[1]),
                                calib, width, height)
    if ground is None:
        return None

    priors = {
        "Car": (4.5, 1.8, 1.5),
        "Bus": (11.0, 2.7, 2.9),
        "Truck": (7.0, 2.3, 2.8),
    }
    L0, W0, H0 = priors.get(cls, (5.0, 2.0, 2.0))
    lo = np.array([-500.0, -500.0, -math.pi, 2.0, 1.0, 1.0])
    hi = np.array([500.0, 500.0, math.pi, 25.0, 3.5, 4.5])

    best = None
    for rev in (False, True):
        base = np.vstack([obs[:4][::-1], obs[4:][::-1]]) if rev else obs
        for shift in range(4):
            idx = [(i + shift) % 4 for i in range(4)]
            obs_s = np.vstack([base[idx], base[[i + 4 for i in idx]]])
            for yaw0 in (yaw_hint, yaw_hint + math.pi, yaw_hint + 0.25, yaw_hint - 0.25):
                p0 = np.array([ground[0], ground[1], yaw0, L0, W0, H0], dtype=float)
                p0 = np.clip(p0, lo + 1e-6, hi - 1e-6)
                try:
                    result = least_squares(
                        residuals, p0, args=(obs_s, calib, width, height),
                        bounds=(lo, hi), loss="linear", max_nfev=500,
                        x_scale="jac",
                    )
                except Exception:
                    continue
                if best is None or result.cost < best.cost:
                    result.shift = shift
                    result.rev = rev
                    best = result
    return best


def parse_annotation(path: Path, calib_dir: Path):
    root = ET.parse(path).getroot()
    size = root.find("size")
    width = int(size.findtext("width"))
    height = int(size.findtext("height"))
    calib_name = Path((root.findtext("calibfile") or "").replace("\\", "/")).name
    calib_path = calib_dir / calib_name
    if not calib_path.exists():
        return None
    calib = parse_calib(calib_path)

    objects = []
    for obj in root.findall("object"):
        v3 = np.array(numbers(obj.findtext("vertex3d") or "")).reshape(-1, 3) / 1000.0
        v2 = np.array(numbers(obj.findtext("vertex2d") or "")).reshape(-1, 2)
        dims = [float(x) for x in (obj.findtext("veh_size") or "").split()]
        bbox = [float(x) for x in (obj.findtext("bbox2d") or "").split()]
        if v3.shape != (8, 3) or v2.shape != (8, 2) or len(dims) != 3 or len(bbox) != 4:
            continue
        center = v3.mean(axis=0)
        distance = float(np.linalg.norm(center - np.array([0.0, 0.0, calib["h_m"]])))
        objects.append({
            "image": path.stem,
            "calib": calib_name,
            "class": (obj.findtext("type") or "").strip(),
            "vertex2d": v2,
            "vertex3d": v3,
            "bbox2d": bbox,
            "L_gt": dims[0], "W_gt": dims[1], "H_gt": dims[2],
            "distance_m": distance,
            "width": width, "height": height,
            "calib_data": calib,
        })
    return objects


def select_objects(objects, n: int, seed: int, classes: list[str] | None = None):
    rng = random.Random(seed)
    bins = [("near", 0, 35), ("mid", 35, 65), ("far", 65, 2000)]
    available = [
        cls for cls in ("Car", "Bus", "Truck")
        if any(o["class"] == cls for o in objects)
    ]
    if classes:
        available = [cls for cls in available if cls in classes]
    if not available:
        raise SystemExit(f"no objects for classes={classes!r}")

    per_bin = max(1, math.ceil(n / (len(available) * len(bins))))
    selected = []
    for cls in available:
        pool = [o for o in objects if o["class"] == cls]
        for _, lo, hi in bins:
            cand = [o for o in pool if lo <= o["distance_m"] < hi]
            rng.shuffle(cand)
            selected.extend(cand[:per_bin])
    rng.shuffle(selected)
    return selected[:n]


def stats(values):
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    return {
        "n": n,
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "p90": round(values[min(n - 1, int(round((n - 1) * 0.9)))], 4),
        "max": round(values[-1], 4),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"data\svld\TESTDATA2021\TESTDATA2021")
    ap.add_argument("--out", default=r"out\svld")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--classes", default=None,
                    help="comma-separated subset, e.g. Truck or Bus,Truck")
    ap.add_argument("--limit-annotations", type=int, default=0)
    args = ap.parse_args()

    root = Path(args.root)
    anns = sorted((root / "Annotations").glob("*.xml"))
    if args.limit_annotations:
        anns = anns[:args.limit_annotations]

    objects = []
    for i, ann in enumerate(anns, 1):
        parsed = parse_annotation(ann, root / "Calib")
        if parsed:
            objects.extend(parsed)
        if i % 500 == 0:
            print(f"  {i}/{len(anns)} annotations...", flush=True)

    classes = [c.strip() for c in args.classes.split(",")] if args.classes else None
    selected = select_objects(objects, args.n, args.seed, classes)
    counts = Counter(o["class"] for o in selected)
    print(f"selected {len(selected)} objects "
          f"({', '.join(f'{cls} {n}' for cls, n in sorted(counts.items()))})")

    rows = []
    for i, obj in enumerate(selected, 1):
        best = fit_object(obj["vertex2d"], obj["calib_data"],
                          obj["width"], obj["height"], obj["class"])
        if best is None:
            rows.append({**{k: obj[k] for k in
                            ("image", "class", "distance_m", "L_gt", "W_gt", "H_gt")},
                         "status": "FIT_FAILED"})
            continue
        L, W, H = best.x[3], best.x[4], best.x[5]
        pred = project(box_corners(best.x), obj["calib_data"],
                       obj["width"], obj["height"])
        idx = [(i + best.shift) % 4 for i in range(4)]
        base = obj["vertex2d"]
        if best.rev:
            base = np.vstack([base[:4][::-1], base[4:][::-1]])
        obs_shift = np.vstack([base[idx], base[[i + 4 for i in idx]]])
        rms = float(np.sqrt(np.mean(np.sum((pred - obs_shift) ** 2, axis=1))))
        rows.append({
            "image": obj["image"],
            "class": obj["class"],
            "distance_m": round(obj["distance_m"], 2),
            "L_gt": obj["L_gt"], "W_gt": obj["W_gt"], "H_gt": obj["H_gt"],
            "L_fit": round(float(L), 3), "W_fit": round(float(W), 3), "H_fit": round(float(H), 3),
            "eL_pct": round(abs(L - obj["L_gt"]) / obj["L_gt"] * 100, 2),
            "eW_pct": round(abs(W - obj["W_gt"]) / obj["W_gt"] * 100, 2),
            "eH_pct": round(abs(H - obj["H_gt"]) / obj["H_gt"] * 100, 2),
            "rms_px": round(rms, 3),
            "status": "OK",
        })
        print(f"  {i}/{len(selected)} {obj['image']} {obj['class']} "
              f"d={obj['distance_m']:.1f}m rms={rms:.2f}px "
              f"L {obj['L_gt']:.2f}->{L:.2f} W {obj['W_gt']:.2f}->{W:.2f} "
              f"H {obj['H_gt']:.2f}->{H:.2f}", flush=True)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = ["image", "class", "distance_m", "L_gt", "W_gt", "H_gt",
              "L_fit", "W_fit", "H_fit", "eL_pct", "eW_pct", "eH_pct",
              "rms_px", "status"]
    csv_path = out_dir / "fit_dims.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    ok = [r for r in rows if r.get("status") == "OK"]
    summary = {"selected": len(selected), "ok": len(ok)}
    if ok:
        summary["mape_pct"] = stats([(r["eL_pct"] + r["eW_pct"] + r["eH_pct"]) / 3 for r in ok])
        summary["eL_pct"] = stats([r["eL_pct"] for r in ok])
        summary["eW_pct"] = stats([r["eW_pct"] for r in ok])
        summary["eH_pct"] = stats([r["eH_pct"] for r in ok])
        summary["rms_px"] = stats([r["rms_px"] for r in ok])
        for cls in sorted({r["class"] for r in ok}):
            sub = [r for r in ok if r["class"] == cls]
            if sub:
                summary[f"{cls}_mape_pct"] = stats(
                    [(r["eL_pct"] + r["eW_pct"] + r["eH_pct"]) / 3 for r in sub])
    (out_dir / "fit_dims_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n" + json.dumps(summary, indent=2))
    print(f"\nwrote {csv_path}")


if __name__ == "__main__":
    main()
