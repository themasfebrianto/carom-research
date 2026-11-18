#!/usr/bin/env python
"""Verify SVLD-3D calibration by reprojecting annotated 3D boxes.

Camera model follows CenterLoc3D (Eq. 2):
  world: origin at camera projection on the road, z up
  camera: x_c parallel to x, z_c along the optical axis, y_c completes
  R = Rx(phi + pi/2) Rz(theta)
  P_c = R (P - [0, 0, h])
  u = f x_c / z_c + c_x,  v = f y_c / z_c + c_y

Units:
  vertex3d : millimetres -> metres
  h        : millimetres -> metres
  f        : pixels
  phi, theta: radians
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


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


def process(ann_path: Path, calib_dir: Path) -> tuple[list[dict], list[dict]]:
    root = ET.parse(ann_path).getroot()
    size = root.find("size")
    width = int(size.findtext("width"))
    height = int(size.findtext("height"))

    calib_rel = (root.findtext("calibfile") or "").replace("\\", "/")
    calib_name = Path(calib_rel).name
    calib_path = calib_dir / calib_name
    if not calib_path.exists():
        return [], [{"image": ann_path.stem, "status": "NO_CALIB", "calib": calib_name}]
    calib = parse_calib(calib_path)

    objects = []
    errors = []
    for obj in root.findall("object"):
        p3 = np.array(numbers(obj.findtext("vertex3d") or "")).reshape(-1, 3) / 1000.0
        p2 = np.array(numbers(obj.findtext("vertex2d") or "")).reshape(-1, 2)
        dims = [float(x) for x in (obj.findtext("veh_size") or "").split()]
        if p3.shape != (8, 3) or p2.shape != (8, 2) or len(dims) != 3:
            continue
        pred = project(p3, calib, width, height)
        err = np.linalg.norm(pred - p2, axis=1)
        objects.append({
            "image": ann_path.stem,
            "calib": calib_name,
            "class": (obj.findtext("type") or "").strip(),
            "rms_px": float(np.sqrt(np.mean(err**2))),
            "max_px": float(np.max(err)),
            "L_m": dims[0],
            "W_m": dims[1],
            "H_m": dims[2],
            "width": width,
            "height": height,
            "f_px": calib["f_px"],
            "phi_deg": math.degrees(calib["phi_rad"]),
            "theta_deg": math.degrees(calib["theta_rad"]),
            "h_m": calib["h_m"],
        })
    errors.append({"image": ann_path.stem, "status": "OK", "objects": len(objects)})
    return objects, errors


def stats(values):
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    return {
        "n": n,
        "median": round(statistics.median(values), 4),
        "p90": round(values[min(n - 1, int(round((n - 1) * 0.9)))], 4),
        "max": round(values[-1], 4),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"data\svld\TESTDATA2021\TESTDATA2021")
    ap.add_argument("--out", default=r"out\svld")
    args = ap.parse_args()

    root = Path(args.root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_objects = []
    all_errors = []
    anns = sorted((root / "Annotations").glob("*.xml"))
    for i, ann in enumerate(anns, 1):
        objs, errs = process(ann, root / "Calib")
        all_objects.extend(objs)
        all_errors.extend(errs)
        if i % 500 == 0:
            print(f"  {i}/{len(anns)} annotations...", flush=True)

    fields = ["image", "calib", "class", "rms_px", "max_px",
              "L_m", "W_m", "H_m", "width", "height",
              "f_px", "phi_deg", "theta_deg", "h_m"]
    csv_path = out_dir / "reproj_objects.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(all_objects)

    by_calib = {}
    for obj in all_objects:
        by_calib.setdefault(obj["calib"], []).append(obj["rms_px"])

    summary = {
        "annotations": len(anns),
        "objects": len(all_objects),
        "images_ok": sum(1 for e in all_errors if e["status"] == "OK"),
        "images_no_calib": sum(1 for e in all_errors if e["status"] == "NO_CALIB"),
        "overall_rms_px": stats([o["rms_px"] for o in all_objects]),
        "objects_over_2px": sum(1 for o in all_objects if o["rms_px"] > 2.0),
        "by_calib": {k: stats(v) for k, v in sorted(by_calib.items())},
    }
    (out_dir / "reproj_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\nwrote {csv_path} ({len(all_objects)} objects)")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
