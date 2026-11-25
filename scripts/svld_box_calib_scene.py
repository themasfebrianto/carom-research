#!/usr/bin/env python
"""How many noisy 3D vehicle boxes are needed for a stable focal length?

A fixed traffic camera sees many vehicles.  Each 3D box is noisy, but the
camera parameters are shared.  This script perturbs each box independently
with a realistic detector error model and solves one camera per scene.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path

import numpy as np

from svld_box_calib import parse_objects, solve
from svld_box_calib_sensitivity import perturb_box


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--ann-root", default=r"data\svld\TESTDATA2021\TESTDATA2021\Annotations")
    ap.add_argument("--per-scene", type=int, default=30)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--out", default="out/svld_box_calib")
    args = ap.parse_args()

    manifest = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    ann_root = Path(args.ann_root)
    by_scene: dict[str, list[tuple]] = {}
    for item in manifest:
        ann = ann_root / f"{Path(item['source']).stem}.xml"
        if not ann.exists():
            continue
        objects, width, height = parse_objects(ann)
        for obj in objects:
            by_scene.setdefault(item["scene"], []).append((item, obj, width, height))

    rows = []
    for scene, items in by_scene.items():
        # Largest boxes first: they carry the most reliable 3D information.
        items = sorted(
            items,
            key=lambda t: np.ptp(t[1]["v2"][:, 0]) * np.ptp(t[1]["v2"][:, 1]),
            reverse=True,
        )[: args.per_scene]
        if len(items) < 2:
            continue
        f_gt = float(items[0][0]["f_px"])
        print(f"\n{scene}: {len(items)} boxes, f_gt={f_gt:.1f}")
        for n in (1, 2, 5, 10, len(items)):
            if n > len(items):
                continue
            errs = []
            for trial in range(args.trials):
                rng = np.random.default_rng(2000 + trial)
                obs, world = [], []
                for item, obj, width, height in items[:n]:
                    v2 = obj["v2"] + rng.normal(0.0, 1.0, size=obj["v2"].shape)
                    v3 = perturb_box(
                        obj,
                        rng,
                        dim_sigma=0.03,
                        pos_sigma=0.3,
                        yaw_sigma=math.radians(2.0),
                    )
                    obs.append(v2)
                    world.append(v3)
                p, _ = solve(
                    obs,
                    world,
                    items[0][2] / 2.0,
                    items[0][3] / 2.0,
                    [
                        np.array([1000.0, 0.1, 0.0, 5.0]),
                        np.array([3000.0, 0.1, 0.0, 7.0]),
                    ],
                )
                errs.append(abs(float(p[0]) / f_gt - 1.0) * 100.0)
            row = {
                "scene": scene,
                "n_boxes": n,
                "median_err_pct": round(statistics.median(errs), 3),
                "max_err_pct": round(max(errs), 3),
            }
            rows.append(row)
            print(row, flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "scene_aggregation.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out / 'scene_aggregation.csv'}")


if __name__ == "__main__":
    main()
