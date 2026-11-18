#!/usr/bin/env python
"""Detectability of the 5 target points on SVLD-3D using vehicle-keypoints.

Target points:
  4 wheels      : keypoints 0-3
  1 roof corner : best of keypoints 9-12

A GT vehicle is matched to the detection with the highest IoU. A keypoint is
counted if its confidence >= 0.3 and it lies inside the image.

This is a detectability test, not a dimension fit.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from svld_fit_dims import parse_annotation, select_objects, stats

WHEELS = [0, 1, 2, 3]
TOPS = [9, 10, 11, 12]
KP_NAMES = [
    "right_front_wheel", "left_front_wheel", "right_back_wheel", "left_back_wheel",
    "right_front_headlight", "left_front_headlight", "right_back_headlight",
    "left_back_headlight", "exhaust", "right_front_top", "left_front_top",
    "right_back_top", "left_back_top", "center",
]


def iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    return inter / (area_a + area_b - inter)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"data\svld\TESTDATA2021\TESTDATA2021")
    ap.add_argument("--weights", default=r"out\keypoint\hf\weights.pt")
    ap.add_argument("--out", default=r"out\keypoint")
    ap.add_argument("--car-images", type=int, default=10)
    ap.add_argument("--bus-images", type=int, default=10)
    ap.add_argument("--conf", type=float, default=0.01)
    ap.add_argument("--imgsz", type=int, default=1920)
    ap.add_argument("--iou-thr", type=float, default=0.3)
    ap.add_argument("--kp-conf", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.root)
    anns = sorted((root / "Annotations").glob("*.xml"))
    objects = []
    for i, ann in enumerate(anns, 1):
        parsed = parse_annotation(ann, root / "Calib")
        if parsed:
            objects.extend(parsed)
        if i % 500 == 0:
            print(f"  parse {i}/{len(anns)}...", flush=True)

    selected = select_objects(objects, 50, args.seed)
    by_cls = defaultdict(list)
    seen = set()
    for obj in selected:
        if obj["image"] in seen:
            continue
        seen.add(obj["image"])
        by_cls[obj["class"]].append(obj["image"])
    images = by_cls["Car"][:args.car_images] + by_cls["Bus"][:args.bus_images]
    print(f"images: {len(images)} ({sum(i in by_cls['Car'] for i in images)} Car, "
          f"{sum(i in by_cls['Bus'] for i in images)} Bus)")

    all_by_image = defaultdict(list)
    for obj in objects:
        if obj["image"] in images:
            all_by_image[obj["image"]].append(obj)

    model = YOLO(args.weights)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir = out_dir / "overlays"
    overlay_dir.mkdir(exist_ok=True)

    rows = []
    for idx, image in enumerate(images, 1):
        img_path = root / "JPEGImages" / f"{image}.jpg"
        image_bgr = cv2.imread(str(img_path))
        h, w = image_bgr.shape[:2]
        result = model.predict(source=str(img_path), conf=args.conf,
                               imgsz=args.imgsz, verbose=False)[0]
        det_boxes = result.boxes.xyxy.cpu().numpy() if len(result.boxes) else np.zeros((0, 4))
        det_conf = result.boxes.conf.cpu().numpy() if len(result.boxes) else np.zeros(0)
        kpts = result.keypoints.data.cpu().numpy() if result.keypoints is not None else np.zeros((0, 14, 3))

        gt_objs = all_by_image.get(image, [])
        print(f"  {idx}/{len(images)} {image}: {len(gt_objs)} GT, {len(det_boxes)} det", flush=True)

        vis = image_bgr.copy()
        for gt in gt_objs:
            x, y, bw, bh = gt["bbox2d"]
            gt_box = (x, y, x + bw, y + bh)
            best_iou, best_j = 0.0, -1
            for j, db in enumerate(det_boxes):
                v = iou(gt_box, db)
                if v > best_iou:
                    best_iou, best_j = v, j

            cv2.rectangle(vis, (int(x), int(y)), (int(x + bw), int(y + bh)), (0, 255, 0), 2)
            row = {
                "image": image,
                "class": gt["class"],
                "distance_m": round(float(gt["distance_m"]), 2),
                "iou": round(float(best_iou), 3),
                "det_conf": "",
                "wheels": 0,
                "roof": 0,
                "five": 0,
                "status": "NOT_DETECTED",
            }
            if best_j >= 0 and best_iou >= args.iou_thr:
                db = det_boxes[best_j]
                kp = kpts[best_j]
                cv2.rectangle(vis, (int(db[0]), int(db[1])), (int(db[2]), int(db[3])),
                              (255, 0, 0), 2)
                wheels = []
                for k in WHEELS:
                    kx, ky, kc = kp[k]
                    ok = kc >= args.kp_conf and 0 <= kx < w and 0 <= ky < h
                    wheels.append(ok)
                    if ok:
                        cv2.circle(vis, (int(kx), int(ky)), 4, (0, 0, 255), -1)
                roof_ok = False
                for k in TOPS:
                    kx, ky, kc = kp[k]
                    if kc >= args.kp_conf and 0 <= kx < w and 0 <= ky < h:
                        roof_ok = True
                        cv2.circle(vis, (int(kx), int(ky)), 4, (0, 255, 255), -1)
                row.update({
                    "det_conf": round(float(det_conf[best_j]), 3),                    "wheels": int(sum(wheels)),
                    "roof": int(roof_ok),
                    "five": int(sum(wheels) == 4 and roof_ok),
                    "status": "MATCHED",
                })
            rows.append(row)
        cv2.imwrite(str(overlay_dir / f"{image}.jpg"), vis)

    fields = ["image", "class", "distance_m", "iou", "det_conf",
              "wheels", "roof", "five", "status"]
    csv_path = out_dir / "detectability.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = {"images": len(images), "gt_objects": len(rows)}
    for cls in ("Car", "Bus"):
        sub = [r for r in rows if r["class"] == cls]
        matched = [r for r in sub if r["status"] == "MATCHED"]
        summary[cls] = {
            "gt": len(sub),
            "matched": len(matched),
            "match_rate_pct": round(100 * len(matched) / len(sub), 1) if sub else 0.0,
            "five_pct_matched": round(100 * sum(r["five"] for r in matched) / len(matched), 1) if matched else 0.0,
            "wheels_mean": float(statistics.mean([r["wheels"] for r in matched])) if matched else None,
            "roof_pct_matched": round(100 * sum(r["roof"] for r in matched) / len(matched), 1) if matched else 0.0,
            "iou_mean": float(statistics.mean([r["iou"] for r in matched])) if matched else None,
        }
    (out_dir / "detectability_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n" + json.dumps(summary, indent=2))
    print(f"\nwrote {csv_path}")
    print(f"overlays: {overlay_dir}")


if __name__ == "__main__":
    main()
