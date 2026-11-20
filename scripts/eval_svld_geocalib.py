#!/usr/bin/env python
"""Evaluate GeoCalib against SVLD-3D calibration GT.

Compares only quantities GeoCalib predicts: focal length ``f`` and pitch.
GeoCalib does not predict yaw or camera height, so those GT fields are not
scored.  Pitch signs differ (SVLD ``fi`` is positive down; GeoCalib reports
negative when looking down), so absolute magnitudes are compared.

Example:
  py scripts/eval_svld_geocalib.py --manifest out/svld_geocalib/manifest.csv \
      --single out/svld_geocalib/geocalib_single.json \
      --multi-dir out/svld_geocalib --out out/svld_geocalib
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
from collections import defaultdict
from pathlib import Path

F_TOL = 0.05
PITCH_TOL_DEG = 2.0


def key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    values = sorted(values)
    n = len(values)
    p90 = values[min(n - 1, round((n - 1) * 0.9))]
    return {
        "n": n,
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "p90": round(p90, 4),
        "max": round(values[-1], 4),
    }


def row_metrics(f_gt: float, f_geo: float, pitch_gt: float, pitch_geo: float) -> dict:
    df = abs(f_geo - f_gt) / f_gt
    dp = abs(abs(pitch_geo) - abs(pitch_gt))
    return {
        "f_gt": round(f_gt, 2),
        "f_geo": round(f_geo, 2),
        "df_over_f": round(df, 6),
        "pitch_gt_deg": round(abs(pitch_gt), 4),
        "pitch_geo_deg": round(abs(pitch_geo), 4),
        "d_pitch_deg": round(dp, 4),
        "pass": df < F_TOL and dp < PITCH_TOL_DEG,
    }


def summarise(rows: list[dict]) -> dict:
    df = [r["df_over_f"] for r in rows]
    dp = [r["d_pitch_deg"] for r in rows]
    passed = sum(bool(r["pass"]) for r in rows)
    return {
        "n": len(rows),
        "df_over_f": stats(df),
        "d_pitch_deg": stats(dp),
        "pass": passed,
        "pass_pct": round(100 * passed / len(rows), 2) if rows else 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--single", default="out/svld_geocalib/geocalib_single.json")
    ap.add_argument("--multi-dir", default="out/svld_geocalib")
    ap.add_argument("--out", default="out/svld_geocalib")
    args = ap.parse_args()

    manifest = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    single = {
        key(r["image"]): r
        for r in json.loads(Path(args.single).read_text(encoding="utf-8-sig"))
        if "error" not in r
    }

    rows = []
    missing = 0
    for item in manifest:
        geo = single.get(key(item["source"]))
        if geo is None:
            missing += 1
            continue
        metrics = row_metrics(
            float(item["f_px"]),
            float(geo["f_px"]),
            math.degrees(float(item["pitch_rad"])),
            float(geo["pitch_deg"]),
        )
        rows.append({
            "split": item["split"],
            "scene": item["scene"],
            "image": item["image"],
            "width": item["width"],
            "height": item["height"],
            **metrics,
        })

    if not rows:
        raise SystemExit("no GeoCalib rows matched the manifest")

    groups = defaultdict(list)
    for row in rows:
        groups[(row["split"], row["scene"])].append(row)
        groups[(row["split"], "*")].append(row)
        groups[("*", "*")].append(row)

    summary = {
        "single_frame": {
            f"{split}/{scene}": summarise(items)
            for (split, scene), items in sorted(groups.items())
        },
        "missing": missing,
        "gate": {"f_tol": F_TOL, "pitch_tol_deg": PITCH_TOL_DEG},
    }

    multi_rows = []
    for scene in sorted({r["scene"] for r in rows}):
        path = Path(args.multi_dir) / f"geocalib_multi_{scene}.json"
        if not path.exists():
            continue
        result = json.loads(path.read_text(encoding="utf-8-sig"))
        gt = next(r for r in rows if r["scene"] == scene)
        metrics = row_metrics(
            float(gt["f_gt"]),
            float(result["f_median"]),
            float(gt["pitch_gt_deg"]),
            float(result["pitch_deg_down_positive_median"]),
        )
        multi_rows.append({"scene": scene, **metrics})
    summary["multi_frame"] = {
        "rows": multi_rows,
        "overall": summarise(multi_rows),
    }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "eval_single.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    if multi_rows:
        with (out_dir / "eval_multi.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(multi_rows[0].keys()))
            writer.writeheader()
            writer.writerows(multi_rows)
    (out_dir / "eval_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(f"rows={len(rows)} missing={missing}")
    for group_key, s in sorted(summary["single_frame"].items()):
        split, scene = group_key.split("/")
        if split == "*" or scene == "*":
            continue
        print(
            f"{split:8s} {scene:18s} n={s['n']:3d} "
            f"df med={s['df_over_f']['median']*100:5.1f}% "
            f"p90={s['df_over_f']['p90']*100:5.1f}% "
            f"dpitch med={s['d_pitch_deg']['median']:4.2f} "
            f"p90={s['d_pitch_deg']['p90']:4.2f} "
            f"pass={s['pass']}/{s['n']}"
        )
    overall = summary["single_frame"]["*/*"]
    print(
        f"OVERALL single n={overall['n']} "
        f"df med={overall['df_over_f']['median']*100:.1f}% "
        f"p90={overall['df_over_f']['p90']*100:.1f}% "
        f"dpitch med={overall['d_pitch_deg']['median']:.2f} "
        f"p90={overall['d_pitch_deg']['p90']:.2f} "
        f"pass={overall['pass']}/{overall['n']}"
    )
    print("MULTI")
    for row in multi_rows:
        print(
            f"  {row['scene']:18s} f {row['f_gt']:.0f}->{row['f_geo']:.0f} "
            f"({row['df_over_f']*100:+.1f}%) pitch {row['pitch_gt_deg']:.2f}->"
            f"{row['pitch_geo_deg']:.2f} ({row['d_pitch_deg']:+.2f} deg) "
            f"{'PASS' if row['pass'] else 'FAIL'}"
        )
    print(f"wrote {out_dir / 'eval_single.csv'}")
    print(f"wrote {out_dir / 'eval_multi.csv'}")
    print(f"wrote {out_dir / 'eval_summary.json'}")


if __name__ == "__main__":
    main()
