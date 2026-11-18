#!/usr/bin/env python
"""Compare GeoCalib output with I24-3D ground-truth calibration.

GeoCalib uses negative pitch for looking down; the I24-3D parser returns a
positive magnitude. This script compares absolute pitch magnitudes.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from pathlib import Path


def camera_from_name(name: str) -> str:
    m = re.search(r"(p\d+c\d+)", Path(name).stem)
    return m.group(1) if m else Path(name).stem


def pct(values, q):
    if not values:
        return float("nan")
    values = sorted(values)
    idx = min(len(values) - 1, max(0, int(round((len(values) - 1) * q))))
    return values[idx]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--geo", required=True, help="GeoCalib JSON (list)")
    ap.add_argument("--gt", required=True, help="parsed GT JSON (camera -> dict)")
    ap.add_argument("--out", required=True, help="output CSV")
    ap.add_argument("--f-tol", type=float, default=0.05)
    ap.add_argument("--pitch-tol", type=float, default=2.0)
    args = ap.parse_args()

    geo = json.loads(Path(args.geo).read_text(encoding="utf-8-sig"))
    gt = json.loads(Path(args.gt).read_text(encoding="utf-8-sig"))

    rows = []
    for r in geo:
        if "error" in r:
            rows.append({"image": r["image"], "camera": "", "status": "ERROR",
                         "note": r["error"]})
            continue
        cam = camera_from_name(r["image"])
        if cam not in gt:
            rows.append({"image": r["image"], "camera": cam, "status": "NO_GT",
                         "note": "camera not in GT JSON"})
            continue

        f_geo = float(r["f_px"])
        f_gt = float(gt[cam]["fx"])
        p_geo = abs(float(r["pitch_deg"]))
        p_gt = abs(float(gt[cam]["pitch_deg"]))
        df = abs(f_geo - f_gt) / f_gt
        dp = abs(p_geo - p_gt)
        ok = df < args.f_tol and dp < args.pitch_tol
        rows.append({
            "image": r["image"],
            "camera": cam,
            "f_geo": round(f_geo, 3),
            "f_gt": round(f_gt, 3),
            "df_over_f": round(df, 6),
            "pitch_geo": round(p_geo, 4),
            "pitch_gt": round(p_gt, 4),
            "d_pitch_deg": round(dp, 4),
            "status": "PASS" if ok else "FAIL",
            "note": "",
        })

    valid = [r for r in rows if r["status"] in ("PASS", "FAIL")]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["image", "camera", "f_geo", "f_gt", "df_over_f",
              "pitch_geo", "pitch_gt", "d_pitch_deg", "status", "note"]
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {out} ({len(rows)} rows, {len(valid)} with GT)")
    if not valid:
        return
    for key in ("df_over_f", "d_pitch_deg"):
        vals = [r[key] for r in valid]
        print(f"{key:12s} median={statistics.median(vals):.4f} "
              f"p90={pct(vals, 0.9):.4f} max={max(vals):.4f}")
    passed = sum(r["status"] == "PASS" for r in valid)
    print(f"pass: {passed}/{len(valid)} = {100*passed/len(valid):.1f}%")
    print(f"gate: {'LULUS' if passed/len(valid) >= 0.8 else 'GAGAL'} "
          f"(median f<{args.f_tol:.0%}, median pitch<{args.pitch_tol:g} deg, >=80%)")


if __name__ == "__main__":
    main()
