#!/usr/bin/env python
"""Inventory parser for the SVLD-3D test set.

Outputs one CSV row per annotated object plus a JSON summary.

Units:
  veh_size  : metres (as documented)
  vertex3d  : millimetres (values like 121105 and 1360 for a 1.36 m car)
  calib h   : millimetres
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


def parse_calib(path: Path) -> dict:
    root = ET.parse(path).getroot()
    raw = {child.tag: (child.text or "").strip() for child in root}
    return {
        "f_px": float(raw["f"]),
        "pitch_rad": float(raw["fi"]),
        "yaw_rad": float(raw["theta"]),
        "h_m": float(raw["h"]) / 1000.0,
        "vanish_points": raw.get("vanishPoints", ""),
    }


def parse_annotation(path: Path, calib_dir: Path) -> list[dict]:
    root = ET.parse(path).getroot()
    size = root.find("size")
    width = int(size.findtext("width"))
    height = int(size.findtext("height"))

    calib_rel = (root.findtext("calibfile") or "").replace("\\", "/")
    calib_name = Path(calib_rel).name
    calib_path = calib_dir / calib_name
    calib = parse_calib(calib_path) if calib_path.exists() else {}

    rows = []
    for obj in root.findall("object"):
        bbox = [float(x) for x in (obj.findtext("bbox2d") or "").split()]
        dims = [float(x) for x in (obj.findtext("veh_size") or "").split()]
        if len(bbox) != 4 or len(dims) != 3:
            continue
        rows.append({
            "image": path.stem,
            "width": width,
            "height": height,
            "calib": calib_name,
            "f_px": calib.get("f_px", ""),
            "h_m": calib.get("h_m", ""),
            "pitch_rad": calib.get("pitch_rad", ""),
            "yaw_rad": calib.get("yaw_rad", ""),
            "class": (obj.findtext("type") or "").strip(),
            "bbox_x": bbox[0],
            "bbox_y": bbox[1],
            "bbox_w": bbox[2],
            "bbox_h": bbox[3],
            "L_m": dims[0],
            "W_m": dims[1],
            "H_m": dims[2],
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"data\svld\TESTDATA2021\TESTDATA2021")
    ap.add_argument("--out", default=r"out\svld")
    args = ap.parse_args()

    root = Path(args.root)
    ann_dir = root / "Annotations"
    calib_dir = root / "Calib"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    anns = sorted(ann_dir.glob("*.xml"))
    if not anns:
        raise SystemExit(f"no annotations under {ann_dir}")

    rows = []
    for i, ann in enumerate(anns, 1):
        rows.extend(parse_annotation(ann, calib_dir))
        if i % 500 == 0:
            print(f"  {i}/{len(anns)} annotations...", flush=True)

    fields = ["image", "width", "height", "calib", "f_px", "h_m", "pitch_rad", "yaw_rad",
              "class", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
              "L_m", "W_m", "H_m"]
    csv_path = out_dir / "objects.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    by_class = defaultdict(list)
    for r in rows:
        by_class[r["class"]].append(r)

    def stats(values):
        if not values:
            return None
        return {
            "n": len(values),
            "mean": round(statistics.mean(values), 4),
            "std": round(statistics.pstdev(values), 4) if len(values) > 1 else 0.0,
            "min": round(min(values), 4),
            "max": round(max(values), 4),
        }

    summary = {
        "annotations": len(anns),
        "objects": len(rows),
        "images_with_objects": len({r["image"] for r in rows}),
        "resolutions": dict(Counter(f"{r['width']}x{r['height']}" for r in rows)),
        "calib_files": sorted({r["calib"] for r in rows}),
        "classes": dict(Counter(r["class"] for r in rows)),
        "class_stats": {
            cls: {
                "objects": len(items),
                "L_m": stats([r["L_m"] for r in items]),
                "W_m": stats([r["W_m"] for r in items]),
                "H_m": stats([r["H_m"] for r in items]),
                "calib_f_px": stats([float(r["f_px"]) for r in items if r["f_px"] != ""]),
                "calib_h_m": stats([float(r["h_m"]) for r in items if r["h_m"] != ""]),
                "calib_pitch_deg": stats([math.degrees(float(r["pitch_rad"]))
                                          for r in items if r["pitch_rad"] != ""]),
                "calib_yaw_deg": stats([math.degrees(float(r["yaw_rad"]))
                                        for r in items if r["yaw_rad"] != ""]),
            }
            for cls, items in sorted(by_class.items())
        },
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\nwrote {csv_path} ({len(rows)} objects, {len(anns)} images)")
    print(json.dumps({k: summary[k] for k in
                      ("annotations", "objects", "images_with_objects",
                       "resolutions", "classes")}, indent=2))


if __name__ == "__main__":
    main()
