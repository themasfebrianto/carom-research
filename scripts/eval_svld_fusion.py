#!/usr/bin/env python
"""Summarise VP + focal-source combinations on the SVLD sample.

Methods:
  VP + f GT       (upper bound)
  VP + f GeoCalib
  VP + f AnyCalib
  VP v + GeoCalib pitch -> f (no anchor)
Only f and pitch/yaw are scored; GeoCalib/AnyCalib do not give yaw or h.

Example:
  py scripts/eval_svld_fusion.py --out out/svld_fusion
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
    ap.add_argument("--vp", default="out/svld_vp/vp_gt.csv")
    ap.add_argument("--any", default="out/svld_anycalib/eval_anycalib.csv")
    ap.add_argument("--geo", default="out/svld_geocalib/geocalib_single.json")
    ap.add_argument("--backend", default=r"D:\Kerjaan\LearnPinhole\backend")
    ap.add_argument("--out", default="out/svld_fusion")
    args = ap.parse_args()

    sys.path.insert(0, args.backend)
    from app.vp_pose import pose_from_vp

    anycalib = {
        (r["split"], r["scene"], r["image"]): r
        for r in csv.DictReader(Path(args.any).open(encoding="utf-8"))
    }
    geo = {
        Path(r["image"]).name: r
        for r in json.loads(Path(args.geo).read_text(encoding="utf-8-sig"))
        if "error" not in r
    }

    rows = []
    for r in csv.DictReader(Path(args.vp).open(encoding="utf-8")):
        a = anycalib.get((r["split"], r["scene"], r["image"]))
        if not a:
            continue
        width = 1920 if r["scene"].startswith("session") else 1280
        height = 1080 if r["scene"].startswith("session") else 720
        cx, cy = width / 2.0, height / 2.0
        gt_pitch = float(r["gt_pitch_deg"])
        gt_yaw = float(r["gt_yaw_deg"])
        f_gt = float(r["f_px"])
        f_geo = float(a["f_geo"]) if a.get("f_geo") else None
        f_any = float(a["f_any"])

        def pose_pass(f):
            p, y = pose_from_vp(float(r["u"]), float(r["v"]), f, cx, cy, 0.0)
            return abs(p - gt_pitch) < 2.0 and abs(y - gt_yaw) < 2.0

        g = geo.get(r["image"])
        f_geo_pitch = None
        if g:
            pitch_down = -math.radians(float(g["pitch_deg"]))
            if abs(pitch_down) > 1e-3:
                f_geo_pitch = (cy - float(r["v"])) / math.tan(pitch_down)
        row = {
            "split": r["split"],
            "scene": r["scene"],
            "image": r["image"],
            "f_gt": f_gt,
            "f_geo": f_geo,
            "f_any": f_any,
            "pass_vp_gt": pose_pass(f_gt),
            "pass_vp_geo": pose_pass(f_geo) if f_geo else False,
            "pass_vp_any": pose_pass(f_any),
            "f_geo_pitch": round(f_geo_pitch, 2) if f_geo_pitch else "",
            "df_geo_pitch": round(abs(f_geo_pitch - f_gt) / f_gt, 6) if f_geo_pitch else "",
        }
        rows.append(row)

    groups = defaultdict(list)
    for row in rows:
        groups[(row["split"], row["scene"])].append(row)
        groups[(row["split"], "*")].append(row)
        groups[("*", "*")].append(row)
    summary = []
    for (split, scene), items in sorted(groups.items()):
        f_geo_pitch = [r["df_geo_pitch"] for r in items if r["df_geo_pitch"] != ""]
        summary.append({
            "split": "all" if split == "*" else split,
            "scene": "ALL" if scene == "*" else scene,
            "n": len(items),
            "pass_vp_gt": sum(r["pass_vp_gt"] for r in items),
            "pass_vp_geo": sum(r["pass_vp_geo"] for r in items),
            "pass_vp_any": sum(r["pass_vp_any"] for r in items),
            "f_geo_pitch_median_pct": round(100 * statistics.median(f_geo_pitch), 2)
            if f_geo_pitch else "",
        })

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "fusion_rows.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    with (out / "fusion_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)
    print(f"wrote {out / 'fusion_summary.csv'}")
    for row in summary:
        print(
            f"{row['split']:8s} {row['scene']:18s} n={row['n']:3d} "
            f"VP+GT={row['pass_vp_gt']:3d} VP+Geo={row['pass_vp_geo']:3d} "
            f"VP+Any={row['pass_vp_any']:3d} GeoPitchF={row['f_geo_pitch_median_pct']}"
        )


if __name__ == "__main__":
    main()
