#!/usr/bin/env python
"""Sample SVLD-3D images per scene and write a GeoCalib evaluation manifest.

The manifest carries the scene calibration GT from ``Calib/{scene}.xml``:
``f`` (px), ``fi`` (pitch, rad), ``theta`` (yaw, rad) and ``h`` (mm).

Example:
  py scripts/svld_geocalib_sample.py --per-scene 10
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


SPLITS = {
    "test": [Path("data/svld/TESTDATA2021/TESTDATA2021")],
    "trainval": [
        Path("SVLD-3D-TRAINVAL-SCENE-A-C/DATA2021"),
        Path("SVLD-3D-TRAINVAL-SCENE-D/DATA2021"),
        Path("SVLD-3D-TRAINVAL-SCENE-E/DATA2021"),
    ],
}


def scene_from_calib(name: str) -> str:
    stem = Path(name).stem
    for suffix in ("_calibParams", "_ManualCamCalibResult"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem


def parse_calib(path: Path) -> dict:
    root = ET.parse(path).getroot()
    raw = {child.tag: (child.text or "").strip() for child in root}
    return {
        "f_px": float(raw["f"]),
        "pitch_rad": float(raw["fi"]),
        "yaw_rad": float(raw["theta"]),
        "h_m": float(raw["h"]) / 1000.0,
    }


def find_image(images_dir: Path, name: str) -> Path | None:
    for suffix in (".jpg", ".png", ".jpeg"):
        candidate = images_dir / f"{name}{suffix}"
        if candidate.exists():
            return candidate
    return None


def even_indices(n: int, k: int) -> list[int]:
    if n <= k:
        return list(range(n))
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-scene", type=int, default=10,
                    help="images per scene per split")
    ap.add_argument("--out", default="out/svld_geocalib")
    args = ap.parse_args()

    out_dir = Path(args.out)
    frames_dir = out_dir / "frames"
    multi_dir = out_dir / "frames_multi"
    manifest = []

    for split, roots in SPLITS.items():
        grouped: dict[str, list[tuple[Path, Path, dict]]] = defaultdict(list)
        for root in roots:
            calib_dir = root / "Calib"
            images_dir = root / "JPEGImages"
            calib_paths = {p.name: p for p in calib_dir.glob("*.xml")}
            calibs = {
                scene_from_calib(name): parse_calib(path)
                for name, path in calib_paths.items()
            }
            for annotation in sorted((root / "Annotations").glob("*.xml")):
                root_xml = ET.parse(annotation).getroot()
                calib_name = Path(
                    (root_xml.findtext("calibfile") or "").replace("\\", "/")
                ).name
                if calib_name not in calib_paths:
                    continue
                scene = scene_from_calib(calib_name)
                if scene not in calibs:
                    continue
                name = Path(
                    (root_xml.findtext("filename") or "").replace("\\", "/")
                ).stem
                image = find_image(images_dir, name)
                if image is None:
                    continue
                size = root_xml.find("size")
                grouped[scene].append((
                    image,
                    calibs[scene],
                    calib_name,
                    int(size.findtext("width")),
                    int(size.findtext("height")),
                ))

        for scene, items in sorted(grouped.items()):
            items.sort(key=lambda item: item[0].name)
            chosen = [items[i] for i in even_indices(len(items), args.per_scene)]
            scene_dir = frames_dir / split / scene
            scene_dir.mkdir(parents=True, exist_ok=True)
            multi_scene_dir = multi_dir / scene
            multi_scene_dir.mkdir(parents=True, exist_ok=True)

            for image, calib, calib_name, width, height in chosen:
                dst = scene_dir / image.name
                shutil.copy2(image, dst)
                multi_dst = multi_scene_dir / f"{split}_{image.name}"
                shutil.copy2(image, multi_dst)
                manifest.append({
                    "split": split,
                    "scene": scene,
                    "image": image.name,
                    "source": str(dst.resolve()),
                    "calib": calib_name,
                    "f_px": calib["f_px"],
                    "width": width,
                    "height": height,
                    "pitch_rad": calib["pitch_rad"],
                    "yaw_rad": calib["yaw_rad"],
                    "h_m": calib["h_m"],
                })
            print(f"{split:8s} {scene:18s} {len(chosen):3d}/{len(items):5d} images")

    if not manifest:
        raise SystemExit("no images sampled; check the dataset paths")
    manifest.sort(key=lambda row: (row["split"], row["scene"], row["image"]))
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(manifest[0].keys()))
        writer.writeheader()
        writer.writerows(manifest)

    summary = defaultdict(int)
    for row in manifest:
        summary[f"{row['split']}/{row['scene']}"] += 1
    (out_dir / "sample_summary.json").write_text(
        json.dumps({"n": len(manifest), "by_scene": dict(summary)}, indent=2),
        encoding="utf-8",
    )
    print(f"\nwrote {out_dir / 'manifest.csv'} ({len(manifest)} images)")


if __name__ == "__main__":
    main()
