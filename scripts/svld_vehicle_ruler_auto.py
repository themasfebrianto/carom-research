#!/usr/bin/env python
"""Automated pilot for the SVLD vehicle-ruler experiment.

This is intentionally *not* the final L1/L2 measurement:

* the face edges are still simulated from SVLD ``vertex2d`` (preset box), so
  they are a geometry check, not an independent annotation;
* the lane boundaries come from ``detect_lane_vp`` at the contact row, which
  is noisy and sometimes picks the wrong line.

What it does provide:

1. A direct comparison of three body-width sources: the visible face
   (``face``), the 2D bbox (``bbox``), and a YOLO-seg mask (``mask``).
   This quantifies how much the silhouette overestimates the face width for
   oblique vehicles, which is exactly why the manual protocol clicks the face
   edges.
2. A real-image check of the pixel-ratio formula using the detected lane
   points: ``w_formula`` vs ``w_ref`` from the same points.  It isolates the
   formula/depth assumptions from lane-line detection quality.
3. A comparison of the detected lane width against the scene prior, which
   shows how often the lane detector picked the correct boundaries.

Run with the backend virtualenv because it has ultralytics:

  D:\\Kerjaan\\LearnPinhole\\backend\\.venv\\Scripts\\python.exe ^
      scripts\\svld_vehicle_ruler_auto.py --limit 24
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

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, r"D:\Kerjaan\LearnPinhole\backend")

from app.lane_vp import detect_lane_vp  # noqa: E402
from svld_vehicle_ruler import (  # noqa: E402
    CANDIDATES,
    LANE_W,
    OUT,
    backproject_ground,
    intersect_y,
    load_case,
    visible_face,
)

MODEL_PATH = Path(__file__).resolve().parents[1] / "out/keypoint/yolo11n-seg.pt"


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


def mask_span(mask: np.ndarray, row: int, half: int = 2) -> tuple[int, int] | None:
    h, w = mask.shape[:2]
    r0 = max(0, row - half)
    r1 = min(h, row + half + 1)
    xs = np.where(mask[r0:r1].any(axis=0))[0]
    if len(xs) == 0:
        return None
    return int(xs.min()), int(xs.max())


def detected_lane_span(img, cam, v_contact: float, u_veh: float):
    """Return (x_left, x_right, vp_info) from the lane detector at one row."""
    vp = detect_lane_vp(img, prior_focal=cam["f"])
    if not vp.segments:
        return None, None, {"ok": vp.ok, "reason": vp.reason, "inliers": vp.inliers}
    xs = []
    for seg in vp.segments:
        a, b, c = seg.eq
        if abs(a) < 1e-9:
            continue
        x = -(b * v_contact + c) / a
        if -0.2 * cam["width"] <= x <= 1.2 * cam["width"]:
            xs.append(x)
    if not xs:
        return None, None, {"ok": vp.ok, "reason": "no_row_intersections",
                            "inliers": vp.inliers}
    xs.sort()
    clusters: list[list[float]] = []
    for x in xs:
        if clusters and x - clusters[-1][-1] <= 0.03 * cam["width"]:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    centers = [statistics.median(c) for c in clusters]
    left = [x for x in centers if x < u_veh - 4]
    right = [x for x in centers if x > u_veh + 4]
    info = {
        "ok": vp.ok, "reason": vp.reason, "inliers": vp.inliers,
        "clusters": len(centers),
    }
    if not left or not right:
        return None, None, info
    return max(left), min(right), info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--conf", type=float, default=0.15)
    ap.add_argument("--out", default=str(OUT / "auto"))
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
        img = cv2.imread(str(case["image_path"]))
        H, W = img.shape[:2]
        body_left, body_right, contact = visible_face(case["obj"], at_contact=True)
        body_left_mid, body_right_mid, _ = visible_face(case["obj"], at_contact=False)
        u_veh = float((body_left[0] + body_right[0]) / 2.0)
        v_row = float(contact[1])
        v_mid = float((body_left_mid[1] + body_right_mid[1]) / 2.0)
        ground = backproject_ground(float(contact[0]), v_row, cam)
        if ground is None:
            print(f"{spec['id']}: contact misses ground")
            continue
        y_contact = float(ground[1])
        # Contact-row face width: this is the width used by the formula.
        V_face = abs(float(body_right[0] - body_left[0]))
        V_face_mid = abs(float(body_right_mid[0] - body_left_mid[0]))
        p_face_l = intersect_y(float(body_left[0]), v_row, y_contact, cam)
        p_face_r = intersect_y(float(body_right[0]), v_row, y_contact, cam)
        W_face = float(np.linalg.norm(p_face_l - p_face_r))

        # bbox and mask widths at the face mid-height; this is the fair
        # silhouette-vs-face comparison (both include the side face/mirrors).
        x, y, bw, bh = case["bbox"]
        V_bbox = float(bw)
        p_bbox_l = intersect_y(float(x), v_mid, y_contact, cam)
        p_bbox_r = intersect_y(float(x + bw), v_mid, y_contact, cam)
        W_bbox = float(np.linalg.norm(p_bbox_l - p_bbox_r)) if p_bbox_l is not None and p_bbox_r is not None else float("nan")

        # YOLO mask
        V_mask = float("nan")
        W_mask = float("nan")
        mask_iou = float("nan")
        det = model.predict(source=img, imgsz=args.imgsz, conf=args.conf,
                            verbose=False, retina_masks=True)[0]
        if det.masks is not None and len(det.boxes):
            boxes = det.boxes.xyxy.cpu().numpy()
            gt = [x, y, x + bw, y + bh]
            ious = [iou_box(gt, b) for b in boxes]
            k = int(np.argmax(ious))
            mask_iou = float(ious[k])
            if mask_iou >= 0.25:
                mask = det.masks.data[k].cpu().numpy()
                mask = cv2.resize(mask, (W, H), interpolation=cv2.INTER_NEAREST) > 0.5
                span = mask_span(mask, int(round(v_mid)), 2)
                if span is not None:
                    mx1, mx2 = span
                    V_mask = float(mx2 - mx1 + 1)
                    p_l = intersect_y(float(mx1), v_mid, y_contact, cam)
                    p_r = intersect_y(float(mx2), v_mid, y_contact, cam)
                    if p_l is not None and p_r is not None:
                        W_mask = float(np.linalg.norm(p_l - p_r))

        # lane boundaries from the classical detector
        lane_l, lane_r, lane_info = detected_lane_span(img, cam, v_row, u_veh)
        L_px = float("nan")
        w_formula = float("nan")
        w_ref = float("nan")
        w_prior = LANE_W[spec["scene"]]
        if lane_l is not None and lane_r is not None:
            L_px = float(lane_r - lane_l)
            w_formula = case["W_preset"] * L_px / V_face
            gl = backproject_ground(float(lane_l), float(contact[1]), cam)
            gr = backproject_ground(float(lane_r), float(contact[1]), cam)
            if gl is not None and gr is not None:
                w_ref = float(np.linalg.norm(gl - gr))

        row = {
            "id": spec["id"], "scene": spec["scene"], "class": spec["cls"],
            "role": spec["role"], "dist_m": round(case["dist_m"], 3),
            "angle_deg": round(case["angle_deg"], 3),
            "W_preset": round(case["W_preset"], 4),
            "V_face": round(V_face, 2), "V_face_mid": round(V_face_mid, 2),
            "W_face": round(W_face, 4),
            "V_bbox": round(V_bbox, 2), "W_bbox": round(W_bbox, 4),
            "V_mask": round(V_mask, 2), "W_mask": round(W_mask, 4),
            "mask_iou": round(mask_iou, 3),
            "ratio_bbox": round(V_bbox / V_face_mid, 4) if V_face_mid > 0 else float("nan"),
            "ratio_mask": round(V_mask / V_face_mid, 4) if V_face_mid > 0 and not math.isnan(V_mask) else float("nan"),
            "e_face_pct": round(abs(W_face - case["W_preset"]) / case["W_preset"] * 100, 3),
            "e_bbox_pct": round(abs(W_bbox - case["W_preset"]) / case["W_preset"] * 100, 3)
            if math.isfinite(W_bbox) else float("nan"),
            "e_mask_pct": round(abs(W_mask - case["W_preset"]) / case["W_preset"] * 100, 3)
            if math.isfinite(W_mask) else float("nan"),
            "lane_ok": bool(lane_l is not None and lane_r is not None),
            "lane_inliers": lane_info.get("inliers"),
            "lane_clusters": lane_info.get("clusters", 0),
            "L_px": round(L_px, 2), "w_formula": round(w_formula, 4),
            "w_ref": round(w_ref, 4), "w_prior": w_prior,
            "e_formula_pct": round(abs(w_formula - w_ref) / w_ref * 100, 3)
            if not math.isnan(w_formula) and not math.isnan(w_ref) and w_ref > 0 else float("nan"),
            "e_prior_pct": round(abs(w_ref - w_prior) / w_prior * 100, 3)
            if not math.isnan(w_ref) else float("nan"),
        }
        rows.append(row)
        print(f"{spec['id']:24s} face={V_face:6.1f} bbox={V_bbox:6.1f} "
              f"mask={V_mask:6.1f} lane={L_px:6.1f} "
              f"ef={row['e_formula_pct']:6.1f}% ep={row['e_prior_pct']:6.1f}%")

        # overlay
        canvas = img.copy()
        cv2.rectangle(canvas, (int(x), int(y)), (int(x + bw), int(y + bh)), (0, 255, 0), 2)
        cv2.line(canvas, tuple(np.round(body_left).astype(int)),
                 tuple(np.round(body_right).astype(int)), (0, 255, 255), 2)
        cv2.circle(canvas, tuple(np.round(contact).astype(int)), 5, (0, 0, 255), -1)
        if lane_l is not None:
            cv2.circle(canvas, (int(round(lane_l)), int(round(contact[1]))), 5, (255, 0, 0), -1)
            cv2.circle(canvas, (int(round(lane_r)), int(round(contact[1]))), 5, (255, 0, 0), -1)
        txt = (f"{spec['id']}  face={V_face:.0f} bbox={V_bbox:.0f} "
               f"mask={V_mask:.0f}  wf={w_formula:.2f} wr={w_ref:.2f}")
        cv2.putText(canvas, txt, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(canvas, txt, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(str(overlays / f"{spec['id']}.jpg"), canvas,
                    [cv2.IMWRITE_JPEG_QUALITY, 88])

    with (out_dir / "auto_results.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    def stats(key: str) -> dict:
        vals = [r[key] for r in rows if isinstance(r[key], (int, float))
                and math.isfinite(float(r[key]))]
        if not vals:
            return {"n": 0}
        return {
            "n": len(vals),
            "median": round(float(np.median(vals)), 3),
            "p90": round(float(np.percentile(vals, 90)), 3),
            "max": round(float(np.max(vals)), 3),
        }

    lane_rows = [r for r in rows if r["lane_ok"]]
    summary = {
        "n": len(rows),
        "e_face_pct": stats("e_face_pct"),
        "e_bbox_pct": stats("e_bbox_pct"),
        "e_mask_pct": stats("e_mask_pct"),
        "ratio_bbox": stats("ratio_bbox"),
        "ratio_mask": stats("ratio_mask"),
        "e_formula_pct": stats("e_formula_pct"),
        "e_prior_pct": stats("e_prior_pct"),
        "lane_ok": len(lane_rows),
        "lane_pass_formula_5pct": sum(
            isinstance(r["e_formula_pct"], float) and math.isfinite(r["e_formula_pct"])
            and r["e_formula_pct"] < 5 for r in lane_rows),
        "lane_pass_prior_10pct": sum(
            isinstance(r["e_prior_pct"], float) and math.isfinite(r["e_prior_pct"])
            and r["e_prior_pct"] < 10 for r in lane_rows),
    }
    (out_dir / "auto_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
