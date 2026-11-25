#!/usr/bin/env python
"""Build CenterLoc3D annotation lines from SVLD-3D XML.

The official dataset/data2script.py assumes every image ID exists in the
current DATA2021 folder.  The public SVLD archives are split by scene, so this
script skips missing images and can filter to one scene.

  python make_centerloc3d_txt.py \
    --data-root /content/svld_ac/DATA2021 \
    --out-dir /content/CenterLoc3D/dataset \
    --scene session0_center \
    --out-name DATA2021_scene
"""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path


CLASSES = ["Car", "Truck", "Bus"]


def numbers(text: str) -> list[float]:
    return [
        float(x)
        for x in text.replace("(", " ").replace(")", " ").replace(",", " ").split()
    ]


def load_xml(path: Path):
    """Parse an annotation, returning None for empty/truncated files.

    A few files in the public archives are zero bytes (bad upload or a partial
    extraction).  They carry no objects, so skipping them loses nothing.
    """
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None


def calib_usable(path: Path, cache: dict[Path, bool]) -> bool:
    """A 0-byte calib file crashes read_calib_params, so never emit its line."""
    if path not in cache:
        try:
            cache[path] = path.stat().st_size > 100 and ET.parse(path) is not None
        except (ET.ParseError, OSError):
            cache[path] = False
    return cache[path]


def annotation_line(image: Path, calib: Path, root) -> str | None:
    parts = [str(image), str(calib)]
    found = 0
    for obj in root.findall("object"):
        try:
            cls = (obj.findtext("type") or "").strip()
            if cls not in CLASSES:
                continue
            bbox = [float(x) for x in (obj.findtext("bbox2d") or "").split()]
            dims = [float(x) for x in (obj.findtext("veh_size") or "").split()]
            center = [float(x) for x in (obj.findtext("veh_loc_2d") or "").split()]
            vertex = numbers(obj.findtext("vertex2d") or "")
            base = [float(x) for x in (obj.findtext("base_point") or "").split()]
        except ValueError:
            continue
        if len(bbox) != 4 or len(dims) != 3 or len(center) != 2:
            continue
        if len(vertex) != 16 or len(base) != 2:
            continue
        persp = 1 if (obj.findtext("perspective") or "").strip() == "right" else 0
        values = bbox + [CLASSES.index(cls)] + center + vertex + dims + [persp] + base
        parts.append(",".join(str(v) for v in values))
        found += 1
    if not found:
        return None
    return " ".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True, help=".../DATA2021")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--scene", default="", help="0cam, 1cam, session0_center, ...")
    ap.add_argument("--out-name", default="DATA2021_scene")
    ap.add_argument("--splits", default="train,val")
    args = ap.parse_args()

    data = Path(args.data_root)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scene_key = args.scene.replace("centre", "center")
    aliases = {
        "0cam": "real_scene_cam0",
        "1cam": "real_scene_cam1",
        "session0_center": "session0_center",
        "session0_right": "session0_right",
        "session6_right": "session6_right",
    }
    image_prefix = aliases.get(scene_key, scene_key)

    for split in args.splits.split(","):
        ids_path = data / "ImageSets" / "Main" / f"{split}.txt"
        if not ids_path.exists():
            print(f"skip {split}: no {ids_path}")
            continue
        ids = ids_path.read_text(encoding="utf-8").split()
        lines = []
        bad_xml = 0
        bad_calib = 0
        calib_cache: dict[Path, bool] = {}
        for image_id in ids:
            if image_prefix and image_prefix not in image_id:
                continue
            ann = data / "Annotations" / f"{image_id}.xml"
            image = data / "JPEGImages" / f"{image_id}.jpg"
            if not image.exists():
                image = data / "JPEGImages" / f"{image_id}.png"
            if not ann.exists() or not image.exists():
                continue
            tree = load_xml(ann)
            if tree is None:
                bad_xml += 1
                continue
            calib_name = Path((tree.findtext("calibfile") or "").replace("\\", "/")).name
            calib = data / "Calib" / calib_name
            if not calib_usable(calib, calib_cache):
                bad_calib += 1
                continue
            line = annotation_line(image, calib, tree)
            if line:
                lines.append(line)
        out_path = out / f"{args.out_name}_{split}.txt"
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        notes = []
        if bad_xml:
            notes.append(f"{bad_xml} xml kosong/rusak")
        if bad_calib:
            notes.append(f"{bad_calib} tanpa calib valid")
        note = f" ({', '.join(notes)} dilewati)" if notes else ""
        print(f"{split}: {len(lines)} lines -> {out_path}{note}")


if __name__ == "__main__":
    main()
