#!/usr/bin/env python
"""Fit a 3D box to a YOLO-seg vehicle mask on SVLD-3D.

For each GT vehicle:
  1. run YOLO-seg once per image;
  2. match the detection with the highest bbox IoU;
  3. crop the mask and fit X, Y, yaw, L, W, H by maximising silhouette IoU.

The mask is the visible vehicle body; the box bottom is the ground. The fit is
therefore evaluated as a perception experiment, not as an oracle geometry test.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import differential_evolution
from ultralytics import YOLO

from svld_fit_dims import (
    parse_annotation,
    select_objects,
    box_corners,
    project,
    backproject_ground,
)

PRIORS = {
    "Car": (4.5, 1.8, 1.5),
    "Bus": (11.0, 2.7, 2.9),
    "Truck": (7.0, 2.3, 2.8),
}
BOUNDS = {
    "Car": [(2.5, 6.5), (1.3, 2.3), (1.0, 2.2)],
    "Bus": [(7.0, 15.0), (2.2, 3.3), (2.3, 4.0)],
    "Truck": [(4.0, 12.0), (1.8, 3.0), (1.8, 4.0)],
}


def iou_box(a, b) -> float:
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


def make_crop(bbox, width, height, margin=0.25, size=256):
    x, y, w, h = bbox
    cx, cy = x + w / 2, y + h / 2
    side = max(w, h) * (1 + 2 * margin)
    x1, y1 = cx - side / 2, cy - side / 2
    x2, y2 = cx + side / 2, cy + side / 2
    # keep the crop inside the image where possible
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(width, x2), min(height, y2)
    return x1, y1, x2, y2


def to_crop(points, crop, size):
    x1, y1, x2, y2 = crop
    sx = size / (x2 - x1)
    sy = size / (y2 - y1)
    out = np.empty_like(points, dtype=float)
    out[:, 0] = (points[:, 0] - x1) * sx
    out[:, 1] = (points[:, 1] - y1) * sy
    return out


def fit_mask(mask_crop, calib, width, height, gt_bbox, cls, size=256, maxiter=25):
    x, y, w, h = gt_bbox
    ground = backproject_ground(x + w / 2, y + h, calib, width, height)
    if ground is None:
        return None
    L0, W0, H0 = PRIORS.get(cls, (5.0, 2.0, 2.0))
    Lb, Wb, Hb = BOUNDS.get(cls, BOUNDS["Car"])
    crop = make_crop(gt_bbox, width, height, 0.25, size)

    obs = mask_crop > 0.5

    def objective(p):
        pts = project(box_corners(p), calib, width, height)
        pts = to_crop(pts, crop, size)
        poly = cv2.convexHull(pts.astype(np.float32)).astype(np.int32)
        pred = np.zeros((size, size), dtype=np.uint8)
        cv2.fillPoly(pred, [poly], 1)
        pred = pred > 0
        inter = np.logical_and(pred, obs).sum()
        union = np.logical_or(pred, obs).sum()
        return 1.0 - (inter / union if union else 0.0)

    bounds = [
        (ground[0] - 20, ground[0] + 20),
        (ground[1] - 20, ground[1] + 20),
        (-math.pi / 2, math.pi / 2),
        Lb, Wb, Hb,
    ]
    result = differential_evolution(
        objective, bounds, seed=0, maxiter=maxiter, popsize=6,
        tol=1e-3, polish=True, workers=1,
    )
    return result, crop


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"data\svld\TESTDATA2021\TESTDATA2021")
    ap.add_argument("--weights", default=r"out\keypoint\yolo11n-seg.pt")
    ap.add_argument("--out", default=r"out\keypoint")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--iou-thr", type=float, default=0.3)
    ap.add_argument("--maxiter", type=int, default=25)
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

    selected = select_objects(objects, max(args.n, 50), args.seed)
    by_image = defaultdict(list)
    for obj in selected:
        by_image[obj["image"]].append(obj)
    images = list(by_image)[:args.n]
    print(f"images: {len(images)}")

    model = YOLO(args.weights)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir = out_dir / "mask_fit"
    overlay_dir.mkdir(exist_ok=True)

    rows = []
    for idx, image in enumerate(images, 1):
        img_path = root / "JPEGImages" / f"{image}.jpg"
        image_bgr = cv2.imread(str(img_path))
        H, W = image_bgr.shape[:2]
        result = model.predict(source=str(img_path), conf=args.conf,
                               imgsz=args.imgsz, verbose=False)[0]
        det_boxes = result.boxes.xyxy.cpu().numpy() if len(result.boxes) else np.zeros((0, 4))
        det_confs = result.boxes.conf.cpu().numpy() if len(result.boxes) else np.zeros(0)
        det_masks = result.masks.data.cpu().numpy() if result.masks is not None else np.zeros((0, 1, 1))

        print(f"  {idx}/{len(images)} {image}: {len(by_image[image])} GT, {len(det_boxes)} det", flush=True)
        for gt in by_image[image]:
            x, y, w, h = gt["bbox2d"]
            gt_box = (x, y, x + w, y + h)
            best_iou, best_j = 0.0, -1
            for j, db in enumerate(det_boxes):
                v = iou_box(gt_box, db)
                if v > best_iou:
                    best_iou, best_j = v, j
            row = {
                "image": image, "class": gt["class"],
                "distance_m": round(float(gt["distance_m"]), 2),
                "det_iou": round(float(best_iou), 3),
                "mask_iou": "", "L_gt": gt["L_gt"], "W_gt": gt["W_gt"], "H_gt": gt["H_gt"],
                "L_fit": "", "W_fit": "", "H_fit": "",
                "eL_pct": "", "eW_pct": "", "eH_pct": "",
                "status": "NOT_DETECTED",
            }
            if best_j >= 0 and best_iou >= args.iou_thr:
                full_mask = cv2.resize(det_masks[best_j], (W, H),
                                       interpolation=cv2.INTER_LINEAR)
                crop = make_crop(gt["bbox2d"], W, H, 0.25, 256)
                x1, y1, x2, y2 = crop
                mask_crop = full_mask[int(y1):int(y2), int(x1):int(x2)]
                mask_crop = cv2.resize(mask_crop, (256, 256),
                                       interpolation=cv2.INTER_LINEAR)
                fit = fit_mask(mask_crop, gt["calib_data"], W, H,
                               gt["bbox2d"], gt["class"], 256, args.maxiter)
                if fit is None:
                    rows.append(row)
                    continue
                result_fit, _ = fit
                L, Wf, Hf = result_fit.x[3], result_fit.x[4], result_fit.x[5]
                row.update({
                    "mask_iou": round(float(1 - result_fit.fun), 3),
                    "L_fit": round(float(L), 3),
                    "W_fit": round(float(Wf), 3),
                    "H_fit": round(float(Hf), 3),
                    "eL_pct": round(abs(L - gt["L_gt"]) / gt["L_gt"] * 100, 2),
                    "eW_pct": round(abs(Wf - gt["W_gt"]) / gt["W_gt"] * 100, 2),
                    "eH_pct": round(abs(Hf - gt["H_gt"]) / gt["H_gt"] * 100, 2),
                    "status": "FIT",
                })
                # overlay
                vis = image_bgr.copy()
                cv2.rectangle(vis, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2)
                pts = project(box_corners(result_fit.x), gt["calib_data"], W, H)
                hull = cv2.convexHull(pts.astype(np.float32)).astype(np.int32)
                cv2.polylines(vis, [hull], True, (255, 0, 0), 2)
                cv2.imwrite(str(overlay_dir / f"{image}_{gt['class']}_{row['distance_m']}.jpg"), vis)
            rows.append(row)

    fields = ["image", "class", "distance_m", "det_iou", "mask_iou",
              "L_gt", "W_gt", "H_gt", "L_fit", "W_fit", "H_fit",
              "eL_pct", "eW_pct", "eH_pct", "status"]
    csv_path = out_dir / "mask_fit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    ok = [r for r in rows if r["status"] == "FIT"]
    summary = {"gt": len(rows), "fit": len(ok)}
    if ok:
        summary["mape_pct"] = {
            "mean": round(statistics.mean([(r["eL_pct"] + r["eW_pct"] + r["eH_pct"]) / 3 for r in ok]), 2),
            "median": round(statistics.median([(r["eL_pct"] + r["eW_pct"] + r["eH_pct"]) / 3 for r in ok]), 2),
        }
        summary["eL_pct"] = round(statistics.mean([r["eL_pct"] for r in ok]), 2)
        summary["eW_pct"] = round(statistics.mean([r["eW_pct"] for r in ok]), 2)
        summary["eH_pct"] = round(statistics.mean([r["eH_pct"] for r in ok]), 2)
        summary["mask_iou_mean"] = round(statistics.mean([r["mask_iou"] for r in ok]), 3)
        for cls in ("Car", "Bus"):
            sub = [r for r in ok if r["class"] == cls]
            if sub:
                summary[f"{cls}_mape_pct"] = round(statistics.mean(
                    [(r["eL_pct"] + r["eW_pct"] + r["eH_pct"]) / 3 for r in sub]), 2)
    (out_dir / "mask_fit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n" + json.dumps(summary, indent=2))
    print(f"\nwrote {csv_path}")


if __name__ == "__main__":
    main()
