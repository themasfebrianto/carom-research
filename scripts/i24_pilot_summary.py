#!/usr/bin/env python
"""Summarise the I24-3D calibration pilot (GT vs GeoCalib).

Ground-truth f comes from RQ(P) and is flagged when K is not physically
plausible.  Ground-truth pitch is derived from the horizon line of H (third
row) and the candidate f: ``pitch = atan((cy - y_horizon) / f)`` with
``cy = 1080/2``.  Positive means looking down.

Example:
  py scripts/i24_pilot_summary.py --out out/i24/i24_pilot_summary.csv
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

from i24_parse import as_3x4, decompose


CAMS = ("p2c3", "p1c5", "p3c6")
SCENES = ("scene1", "scene2", "scene3")
CX, CY = 960.0, 540.0


def camera_of(path: str) -> str:
    m = re.search(r"(p\d+c\d+)", Path(path).stem)
    return m.group(1) if m else Path(path).stem


def scene_of(path: str) -> str:
    m = re.search(r"(scene\d)", str(path))
    return m.group(1) if m else ""


def plausible(K: np.ndarray, f_min: float = 300.0) -> bool:
    fx, fy = float(K[0, 0]), float(K[1, 1])
    cx, cy = float(K[0, 2]), float(K[1, 2])
    aspect = abs(fx - fy) / ((fx + fy) / 2.0)
    return (
        fx > f_min
        and aspect < 0.05
        and 0.3 * 2 * CX < cx < 0.7 * 2 * CX
        and 0.3 * 2 * CY < cy < 0.7 * 2 * CY
    )


def horizon_row(H: np.ndarray) -> float:
    line = H[2, :]
    return float(-(line[0] * CX + line[2]) / line[1])


def pitch_from_horizon(y_horizon: float, f: float) -> float:
    return math.degrees(math.atan((CY - y_horizon) / f))


def summary_row(scene: str, cam: str, hg: dict, geo_single: list, geo_multi: dict) -> dict:
    out = {"scene": scene, "camera": cam}
    gt_vals = {}
    for direction in ("EB", "WB"):
        entry = hg[direction][cam]
        P = as_3x4(entry["P"])
        K, _, _ = decompose(P)
        H = np.asarray(entry["H"], dtype=float)
        yh = horizon_row(H)
        C = -np.linalg.solve(P[:, :3], P[:, 3]) * 0.3048
        gt_vals[direction] = {
            "f": float(K[0, 0]),
            "fy": float(K[1, 1]),
            "y_horizon": yh,
            "pitch": pitch_from_horizon(yh, float(K[0, 0])),
            "height_m": float(C[2]),
            "plausible": plausible(K),
        }

    eb, wb = gt_vals["EB"], gt_vals["WB"]
    out.update({
        "gt_f_eb": round(eb["f"], 1),
        "gt_f_wb": round(wb["f"], 1),
        "gt_df_pct": round(100 * abs(eb["f"] - wb["f"]) / ((eb["f"] + wb["f"]) / 2), 2),
        "gt_pitch_eb": round(eb["pitch"], 2),
        "gt_pitch_wb": round(wb["pitch"], 2),
        "gt_horizon_row": round(eb["y_horizon"], 1),
        "gt_height_m": round(eb["height_m"], 1),
        "gt_eb_plausible": eb["plausible"],
        "gt_wb_plausible": wb["plausible"],
    })

    rows = [r for r in geo_single
            if "error" not in r
            and scene_of(r["image"]) == scene
            and camera_of(r["image"]) == cam]
    if rows:
        fs = [float(r["f_px"]) for r in rows]
        out.update({
            "geo_f_min": round(min(fs), 1),
            "geo_f_median": round(statistics.median(fs), 1),
            "geo_f_max": round(max(fs), 1),
            "geo_pitch_down_positive": round(
                statistics.median([abs(float(r["pitch_deg"])) for r in rows]), 2),
            "geo_roll": round(statistics.median([float(r["roll_deg"]) for r in rows]), 2),
        })
    else:
        out.update({"geo_f_min": "", "geo_f_median": "", "geo_f_max": "",
                    "geo_pitch_down_positive": "", "geo_roll": ""})

    if geo_multi:
        out.update({
            "geo_multi_f": round(float(geo_multi["f_median"]), 1),
            "geo_multi_pitch_down_positive": round(
                float(geo_multi["pitch_deg_down_positive_median"]), 2),
            "geo_multi_roll": round(float(geo_multi["roll_deg_median"]), 2),
        })
    else:
        out.update({"geo_multi_f": "", "geo_multi_pitch_down_positive": "",
                    "geo_multi_roll": ""})

    notes = []
    if not eb["plausible"] or not wb["plausible"]:
        notes.append("GT K tidak plausibel")
    if out["gt_df_pct"] > 10:
        notes.append("EB/WB f berbeda >10%")
    if not rows:
        notes.append("tidak ada frame GeoCalib")
    out["note"] = "; ".join(notes)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hg-dir", default="I24-3D/data/hg")
    ap.add_argument("--frames-dir", default="out/i24")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    hg_dir = Path(args.hg_dir)
    frames_dir = Path(args.frames_dir)
    geo_single = json.loads(
        (frames_dir / "geocalib_all.json").read_text(encoding="utf-8-sig")
    )

    rows = []
    for scene in SCENES:
        hg = json.loads(
            (hg_dir / f"{scene}_hg.json").read_text(encoding="utf-8-sig")
        )
        for cam in CAMS:
            if cam not in hg["EB"]:
                continue
            multi_path = frames_dir / f"geocalib_multi_{scene}_{cam}.json"
            multi = (
                json.loads(multi_path.read_text(encoding="utf-8-sig"))
                if multi_path.exists() else {}
            )
            rows.append(summary_row(scene, cam, hg, geo_single, multi))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")
    for r in rows:
        print(
            f"{r['scene']} {r['camera']}: GT f {r['gt_f_eb']}/{r['gt_f_wb']} "
            f"({r['gt_df_pct']}%), GT pitch {r['gt_pitch_eb']}/{r['gt_pitch_wb']} deg; "
            f"Geo multi f={r['geo_multi_f']} pitch={r['geo_multi_pitch_down_positive']} deg"
        )


if __name__ == "__main__":
    main()
