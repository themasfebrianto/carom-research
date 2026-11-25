#!/usr/bin/env python
"""Evaluate AnyCalib focal length on the SVLD sample, next to GeoCalib.

AnyCalib estimates f (and distortion for other camera models); it does not
estimate yaw, pitch, or height.  Therefore only Delta f is scored.

Example:
  py scripts/eval_svld_anycalib.py --out out/svld_anycalib
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
from collections import defaultdict
from pathlib import Path

F_TOL = 0.05


def key(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    values = sorted(values)
    n = len(values)
    return {
        "n": n,
        "mean": round(statistics.mean(values), 4),
        "median": round(statistics.median(values), 4),
        "p90": round(values[min(n - 1, round((n - 1) * 0.9))], 4),
        "max": round(values[-1], 4),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--any-dir", default="out/svld_anycalib")
    ap.add_argument("--geo", default="out/svld_geocalib/geocalib_single.json")
    ap.add_argument("--out", default="out/svld_anycalib")
    args = ap.parse_args()

    manifest = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    geocalib = {}
    geo_path = Path(args.geo)
    if geo_path.exists():
        geocalib = {
            key(row["image"]): row
            for row in json.loads(geo_path.read_text(encoding="utf-8-sig"))
            if "error" not in row
        }

    anycalib = {}
    for path in Path(args.any_dir).glob("*_*.json"):
        if path.name in ("eval_summary.json",):
            continue
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        folder = Path(doc.get("folder", ""))
        parts = list(folder.parts)
        if "frames" not in parts:
            continue
        idx = parts.index("frames")
        split, scene = parts[idx + 1], parts[idx + 2]
        for row in doc.get("frames", []):
            values = row.get("intrinsics", {})
            f = values.get("f")
            if f is None:
                fx, fy = values.get("fx"), values.get("fy")
                f = (fx + fy) / 2 if fx and fy else None
            if f is not None:
                anycalib[(split, scene, row["frame"])] = float(f)

    rows = []
    for item in manifest:
        f_any = anycalib.get((item["split"], item["scene"], item["image"]))
        if f_any is None:
            continue
        f_gt = float(item["f_px"])
        row = {
            "split": item["split"],
            "scene": item["scene"],
            "image": item["image"],
            "f_gt": round(f_gt, 2),
            "f_any": round(f_any, 2),
            "df_any": round(abs(f_any - f_gt) / f_gt, 6),
            "pass_any": abs(f_any - f_gt) / f_gt < F_TOL,
        }
        geo = geocalib.get(key(item["source"]))
        if geo is not None:
            f_geo = float(geo["f_px"])
            row.update({
                "f_geo": round(f_geo, 2),
                "df_geo": round(abs(f_geo - f_gt) / f_gt, 6),
                "pass_geo": abs(f_geo - f_gt) / f_gt < F_TOL,
                "geo_minus_any_pct": round(100 * (f_geo - f_any) / f_any, 2),
            })
        rows.append(row)

    groups = defaultdict(list)
    for row in rows:
        groups[(row["split"], row["scene"])].append(row)
        groups[(row["split"], "*")].append(row)
        groups[("*", "*")].append(row)
    summary = {}
    for (split, scene), items in sorted(groups.items()):
        summary[f"{split}/{scene}"] = {
            "n": len(items),
            "f_any": stats([r["df_any"] for r in items]),
            "f_geo": stats([r["df_geo"] for r in items if "df_geo" in r]),
            "pass_any": sum(bool(r["pass_any"]) for r in items),
            "pass_geo": sum(bool(r.get("pass_geo")) for r in items),
        }

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "eval_anycalib.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "eval_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(f"rows={len(rows)}")
    for group, s in summary.items():
        print(
            f"{group:24s} n={s['n']:3d} "
            f"AnyCalib dF med={s['f_any'].get('median', float('nan'))*100:5.1f}% "
            f"pass={s['pass_any']}/{s['n']}  "
            f"GeoCalib med={s['f_geo'].get('median', float('nan'))*100:5.1f}% "
            f"pass={s['pass_geo']}/{s['n']}"
        )
    print(f"wrote {out_dir / 'eval_anycalib.csv'}")
    print(f"wrote {out_dir / 'eval_summary.json'}")


if __name__ == "__main__":
    main()
