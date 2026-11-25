#!/usr/bin/env python
"""Evaluate single-box calibration with known dimensions on SVLD.

Uses only the eight 2D corners and the GT box dimensions (L, W, H); the box
position and yaw are solved jointly with f/pitch/yaw/height.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from box_pnp_known_dims import solve_cuboid
from svld_box_calib import parse_objects


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--ann-root", default=r"data\svld\TESTDATA2021\TESTDATA2021\Annotations")
    ap.add_argument("--per-scene", type=int, default=10)
    ap.add_argument("--out", default="out/svld_box_known_dims")
    args = ap.parse_args()

    rows = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    ann_root = Path(args.ann_root)
    by_scene: dict[str, list] = {}
    for item in rows:
        ann = ann_root / f"{Path(item['source']).stem}.xml"
        if not ann.exists():
            continue
        objects, width, height = parse_objects(ann)
        if not objects:
            continue
        obj = max(objects, key=lambda o: np.ptp(o["v2"][:, 0]) * np.ptp(o["v2"][:, 1]))
        by_scene.setdefault(item["scene"], []).append((item, obj, width, height))

    out_rows = []
    for scene, items in by_scene.items():
        for item, obj, width, height in items[: args.per_scene]:
            dims = obj["dims"]
            if len(dims) != 3:
                continue
            best = solve_cuboid(obj["v2"], dims, width / 2.0, height / 2.0, width, height)
            if best is None:
                continue
            p, _, rms = best
            f_gt = float(item["f_px"])
            row = {
                "scene": scene,
                "image": item["image"],
                "n_obj": 1,
                "f_gt": round(f_gt, 3),
                "f_est": round(float(p[0]), 3),
                "f_ratio": round(float(p[0] / f_gt), 5),
                "rms_px": round(rms, 3),
            }
            out_rows.append(row)
            print(row, flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "known_dims.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)

    print("\nsummary")
    for scene in sorted({r["scene"] for r in out_rows}):
        rs = [r for r in out_rows if r["scene"] == scene]
        err = [abs(r["f_ratio"] - 1) * 100 for r in rs]
        print(
            f"  {scene:18s} n={len(rs):2d} median={statistics.median(err):5.2f}% "
            f"p90={np.percentile(err, 90):5.2f}% "
            f"pass5={sum(e < 5 for e in err):2d}/{len(rs)}"
        )


if __name__ == "__main__":
    main()
