#!/usr/bin/env python
"""Pilot: Dubska/Sochor tangent-hull width on the SVLD vehicle-ruler candidates.

The implementation lives in ``D:\\Kerjaan\\CCTV-ODOL\\cctv\\tangent_hull.py``.
It measures width from the mask contour's outer bottom corner and inner tangent
pivot, instead of the full silhouette width.  That is the method the user asked
about; this script checks whether it removes the bbox/mask bias on SVLD.

Important: the tangent construction assumes a nearly level camera (lateral and
vertical vanishing points at infinity) and a vehicle yaw below about 1.5 deg.
SVLD has 6-15 deg camera pitch and candidates up to 10 deg yaw, so the method is
expected to work only on the near-frontal group and to degrade (or return a
deadzone) on the oblique group.  The pilot measures that rather than assuming it.

Run with the backend virtualenv (it has ultralytics):

  D:\\Kerjaan\\LearnPinhole\\backend\\.venv\\Scripts\\python.exe ^
      scripts\\svld_tangent_hull_pilot.py --limit 24
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, r"D:\Kerjaan\CCTV-ODOL")

from cctv.groundplane import GroundPlane  # noqa: E402
from cctv.tangent_hull import (  # noqa: E402
    OUTER_CORNER_BODY,
    OUTER_CORNER_FOOTPRINT,
    fit,
)
from svld_vehicle_ruler import (  # noqa: E402
    CANDIDATES,
    backproject_ground,
    intersect_y,
    load_case,
    visible_face,
)

OUT = REPO / "out/svld_vehicle_ruler/tangent_hull"
MODEL_PATH = REPO / "out/keypoint/yolo11n-seg.pt"


def iou_box(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    return inter / (area_a + area_b - inter + 1e-9)


def make_gp(cam: dict) -> GroundPlane:
    """SVLD model -> CCTV-ODOL GroundPlane.

    SVLD: R = Rx(phi + pi/2) Rz(theta), camera at (0, 0, h).
    CCTV-ODOL: pitch positive downward, yaw from +Y.  The SVLD theta sign is
    opposite to the CCTV-ODOL yaw convention; verified by projecting the GT
    vertices (RMS 0.48 px on the 0cam bus).
    """
    return GroundPlane.from_pose(
        cam["f"], cam["cx"], cam["cy"],
        math.degrees(cam["phi"]), -math.degrees(cam["theta"]),
        0.0, cam["h"],
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--conf", type=float, default=0.15)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    from ultralytics import YOLO

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    overlays = out_dir / "overlays"
    overlays.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(MODEL_PATH))

    specs = CANDIDATES[: args.limit] if args.limit else CANDIDATES
    rows = []
    for spec in specs:
        case = load_case(spec)
        cam = case["cam"]
        gp = make_gp(cam)
        img = cv2.imread(str(case["image_path"]))
        H, W = img.shape[:2]
        x, y, bw, bh = case["bbox"]
        gt = [x, y, x + bw, y + bh]

        # Image-based face width from the SVLD 2D face edges; reference only.
        bl, br, contact = visible_face(case["obj"], at_contact=True)
        ground = backproject_ground(float(contact[0]), float(contact[1]), cam)
        if ground is None:
            continue
        y_contact = float(ground[1])
        pl = intersect_y(float(bl[0]), float(bl[1]), y_contact, cam)
        pr = intersect_y(float(br[0]), float(br[1]), y_contact, cam)
        W_face = float(np.linalg.norm(pl - pr))

        det = model.predict(source=img, imgsz=args.imgsz, conf=args.conf,
                            verbose=False, retina_masks=True)[0]
        if det.masks is None or len(det.boxes) == 0:
            print(f"{spec['id']}: no mask")
            continue
        boxes = det.boxes.xyxy.cpu().numpy()
        ious = [iou_box(gt, b) for b in boxes]
        k = int(np.argmax(ious))
        mask_iou = float(ious[k])
        if mask_iou < 0.25:
            print(f"{spec['id']}: mask IoU {mask_iou:.2f}")
            continue
        mask = det.masks.data[k].cpu().numpy()
        mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST) > 0.5
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        contour = max(contours, key=cv2.contourArea).reshape(-1, 2).astype(float)

        got = {}
        for oc in (OUTER_CORNER_BODY, OUTER_CORNER_FOOTPRINT):
            res = fit(contour, gp, image_size=(W, H), shrink_px=0.94,
                      outer_corner=oc)
            got[oc] = res

        body = got[OUTER_CORNER_BODY]
        foot = got[OUTER_CORNER_FOOTPRINT]
        row = {
            "id": spec["id"], "scene": spec["scene"], "class": spec["cls"],
            "role": spec["role"], "angle_deg": round(case["angle_deg"], 3),
            "dist_m": round(case["dist_m"], 3),
            "W_preset": round(case["W_preset"], 4), "W_face": round(W_face, 4),
            "mask_iou": round(mask_iou, 3),
            "body_width": round(body.width_m, 4) if body else float("nan"),
            "body_error_pct": round(abs(body.width_m - case["W_preset"]) / case["W_preset"] * 100, 3)
            if body else float("nan"),
            "body_side_ratio": round(body.side_ratio, 4) if body else float("nan"),
            "body_iou": round(body.hull_iou, 4) if body else float("nan"),
            "body_deadzone": bool(body.is_deadzone) if body else True,
            "body_reason": body.reason if body and body.reason else "",
            "body_depth_m": round(body.depth_m, 3) if body else float("nan"),
            "body_length_m": round(body.length_m, 3) if body else float("nan"),
            "foot_width": round(foot.width_m, 4) if foot else float("nan"),
            "foot_error_pct": round(abs(foot.width_m - case["W_preset"]) / case["W_preset"] * 100, 3)
            if foot else float("nan"),
            "foot_deadzone": bool(foot.is_deadzone) if foot else True,
            "foot_side_ratio": round(foot.side_ratio, 4) if foot else float("nan"),
        }
        rows.append(row)
        print(f"{spec['id']:24s} angle={row['angle_deg']:5.1f} "
              f"preset={row['W_preset']:.2f} body={row['body_width']:5.2f} "
              f"({row['body_error_pct']:5.1f}%) foot={row['foot_width']:5.2f} "
              f"({row['foot_error_pct']:5.1f}%) dead={row['body_deadzone']}")

        canvas = img.copy()
        cv2.drawContours(canvas, [contour.astype(np.int32)], -1, (255, 0, 0), 2)
        if body is not None and not body.is_deadzone:
            for a, b in ((0, 1), (1, 3), (3, 2), (2, 0), (4, 5), (5, 7),
                         (7, 6), (6, 4), (0, 4), (1, 5), (2, 6), (3, 7)):
                pa, pb = body.corners_uv[a], body.corners_uv[b]
                if np.isfinite(pa).all() and np.isfinite(pb).all():
                    cv2.line(canvas, tuple(np.round(pa).astype(int)),
                             tuple(np.round(pb).astype(int)), (0, 255, 0), 2)
        txt = (f"{spec['id']} body={row['body_width']:.2f}m "
               f"({row['body_error_pct']:.1f}%) side={row['body_side_ratio']:.3f} "
               f"dead={row['body_deadzone']}")
        cv2.putText(canvas, txt, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(canvas, txt, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(str(overlays / f"{spec['id']}.jpg"), canvas,
                    [cv2.IMWRITE_JPEG_QUALITY, 88])

    with (out_dir / "tangent_hull_results.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    def stats(key: str, subset=None) -> dict:
        vals = [r[key] for r in (subset or rows)
                if isinstance(r[key], (int, float)) and math.isfinite(float(r[key]))]
        if not vals:
            return {"n": 0}
        return {
            "n": len(vals),
            "median": round(float(np.median(vals)), 3),
            "p90": round(float(np.percentile(vals, 90)), 3),
            "max": round(float(np.max(vals)), 3),
        }

    def by_angle(lo, hi):
        return [r for r in rows if lo <= r["angle_deg"] < hi]

    summary = {
        "n": len(rows),
        "body_error_pct": stats("body_error_pct"),
        "body_error_pct_valid": stats("body_error_pct",
                                      [r for r in rows if not r["body_deadzone"]]),
        "foot_error_pct": stats("foot_error_pct"),
        "body_deadzones": sum(1 for r in rows if r["body_deadzone"]),
        "foot_deadzones": sum(1 for r in rows if r["foot_deadzone"]),
        "by_angle": {},
        "by_class": {},
    }
    for lo, hi in ((0, 3), (3, 6), (6, 10), (10, 15)):
        sub = by_angle(lo, hi)
        summary["by_angle"][f"{lo}-{hi}"] = {
            "n": len(sub),
            "body_error_pct": stats("body_error_pct", sub),
            "body_deadzones": sum(1 for r in sub if r["body_deadzone"]),
        }
    for cls in sorted({r["class"] for r in rows}):
        sub = [r for r in rows if r["class"] == cls]
        summary["by_class"][cls] = {
            "n": len(sub),
            "body_error_pct": stats("body_error_pct", sub),
        }
    (out_dir / "tangent_hull_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
