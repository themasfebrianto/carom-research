#!/usr/bin/env python
"""Scene-level VP pose for a static camera (median u,v across frames).

Per-frame VP can pick a wrong line intersection (one 1cam outlier).  For a
static roadside camera the VP is constant, so the median across frames is a
robust scene-level estimate.  f is taken as the median f of the same run.

Example:
  py scripts/svld_vp_scene_median.py --out out/svld_vp
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--vp-dir", default="out/svld_vp")
    ap.add_argument("--backend", default=r"D:\Kerjaan\LearnPinhole\backend")
    ap.add_argument("--out", default="out/svld_vp")
    args = ap.parse_args()

    sys.path.insert(0, args.backend)
    from app.vp_pose import pose_from_vp

    manifest = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    gt = {row["scene"]: row for row in manifest}
    rows = []
    for source in ("gt", "geo"):
        path = Path(args.vp_dir) / f"vp_{source}.csv"
        if not path.exists():
            continue
        by_scene = defaultdict(list)
        for row in csv.DictReader(path.open(encoding="utf-8")):
            if row["accepted"] == "True":
                by_scene[row["scene"]].append(row)
        for scene, items in sorted(by_scene.items()):
            u = statistics.median(float(r["u"]) for r in items)
            v = statistics.median(float(r["v"]) for r in items)
            f = statistics.median(float(r["f_px"]) for r in items)
            item = gt[scene]
            width, height = int(item["width"]), int(item["height"])
            pitch, yaw = pose_from_vp(u, v, f, width / 2, height / 2, 0.0)
            gt_pitch = math.degrees(float(item["pitch_rad"]))
            gt_yaw = math.degrees(float(item["yaw_rad"]))
            rows.append({
                "source_f": source,
                "scene": scene,
                "n": len(items),
                "u": round(u, 2),
                "v": round(v, 2),
                "f_px": round(f, 2),
                "vp_pitch_deg": round(pitch, 4),
                "vp_yaw_deg": round(yaw, 4),
                "gt_pitch_deg": round(gt_pitch, 4),
                "gt_yaw_deg": round(gt_yaw, 4),
                "d_pitch_deg": round(abs(pitch - gt_pitch), 4),
                "d_yaw_deg": round(abs(yaw - gt_yaw), 4),
                "pass": abs(pitch - gt_pitch) < 2.0 and abs(yaw - gt_yaw) < 2.0,
            })

    out = Path(args.out) / "vp_scene_median.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out}")
    for row in rows:
        print(
            f"{row['source_f']:3s} {row['scene']:18s} "
            f"dP={row['d_pitch_deg']:5.2f} dY={row['d_yaw_deg']:5.2f} "
            f"{'PASS' if row['pass'] else 'FAIL'}"
        )


if __name__ == "__main__":
    main()
