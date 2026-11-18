#!/usr/bin/env python
"""Prototype: side-view length from a tracked vehicle in Cawang.

Uses the anchored Cawang calibration (f=1082.6, h=8.876, pitch=2.432 deg).
For each tracked mask, the two extreme contour points along the principal axis
are back-projected to the ground plane; their distance is the length estimate.
Also reports the ground speed of the mask centre.

This is a prototype, not a validated measurement.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

# Anchored Cawang calibration, 1280x720
CX, CY = 640.0, 360.0
F = 1082.6
H = 8.876
TH = math.radians(2.432)
S, C = math.sin(TH), math.cos(TH)
VPX, VPY = 651.5, 310.0  # longitudinal vanishing point from vp.json


def x_of_v(v: float) -> float:
    lo, hi = 1.0, 400.0
    for _ in range(80):
        m = (lo + hi) / 2
        z = m * C + H * S
        vv = CY + F * (-m * S + H * C) / z
        if vv > v:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def ground_point(u: float, v: float):
    X = x_of_v(v)
    z = X * C + H * S
    Y = (u - CX) * z / F
    return X, Y


def mask_endpoints(mask: np.ndarray):
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return None
    cnt = max(cnts, key=cv2.contourArea).reshape(-1, 2).astype(float)
    if len(cnt) < 10:
        return None
    mean = cnt.mean(axis=0)
    axis = np.array([VPX - mean[0], VPY - mean[1]], dtype=float)
    n = np.linalg.norm(axis)
    if n < 1e-6:
        cov = np.cov((cnt - mean).T)
        vals, vecs = np.linalg.eigh(cov)
        axis = vecs[:, np.argmax(vals)]
    else:
        axis /= n
    proj = (cnt - mean) @ axis
    i_min, i_max = int(np.argmin(proj)), int(np.argmax(proj))
    p_min, p_max = cnt[i_min], cnt[i_max]
    span = abs(proj[i_max] - proj[i_min])

    # ground contact: lowest (max y) contour point near each end
    def contact(p):
        d = np.abs((cnt - p) @ axis)
        near = cnt[d < max(2.0, 0.12 * span)]
        if len(near) == 0:
            return p
        return near[np.argmax(near[:, 1])]

    return contact(p_min), contact(p_max), cnt


def iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    aa = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    bb = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    return inter / (aa + bb - inter)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="recording cawang.mp4")
    ap.add_argument("--weights", default=r"out\keypoint\yolo11n-seg.pt")
    ap.add_argument("--start", type=float, default=202.0)
    ap.add_argument("--duration", type=float, default=2.5)
    ap.add_argument("--fps", type=float, default=5.0)
    ap.add_argument("--out", default=r"out\timepass")
    ap.add_argument("--init-bbox", default="", help="x1,y1,x2,y2")
    ap.add_argument("--conf", type=float, default=0.15)
    ap.add_argument("--lane", choices=["near", "far", "any"], default="any",
                    help="near: image x>=600; far: x<600")
    ap.add_argument("--min-area", type=int, default=30000,
                    help="ignore masks smaller than this for the summary")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(args.video)
    src_fps = cap.get(cv2.CAP_PROP_FPS)
    start_frame = int(args.start * src_fps)
    step = max(1, int(round(src_fps / args.fps)))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    model = YOLO(args.weights)
    target = None
    if args.init_bbox:
        target = tuple(float(x) for x in args.init_bbox.split(","))

    rows = []
    n = int(args.duration * args.fps)
    for k in range(n):
        ok, frame = cap.read()
        if not ok:
            break
        if k > 0:
            for _ in range(step - 1):
                cap.grab()
        t = args.start + k / args.fps
        result = model.predict(source=frame, conf=args.conf, imgsz=1280, verbose=False)[0]
        dets = []
        for j, b in enumerate(result.boxes.xyxy.cpu().numpy()):
            name = model.names[int(result.boxes.cls[j])]
            if name not in ("bus", "truck"):
                continue
            x1, y1, x2, y2 = b
            cx = (x1 + x2) / 2
            if args.lane == "near" and cx < 600:
                continue
            if args.lane == "far" and cx >= 600:
                continue
            dets.append((j, b, name, float(result.boxes.conf[j])))

        if not dets:
            print(f"{t:.2f}s: no near-lane bus/truck")
            continue

        if target is None:
            j, b, name, conf = max(dets, key=lambda d: (d[1][2] - d[1][0]) * (d[1][3] - d[1][1]))
            target = tuple(float(x) for x in b)
            print(f"{t:.2f}s: init {name} conf={conf:.2f} bbox={[round(float(x),1) for x in b]}")
        else:
            j, b, name, conf = max(dets, key=lambda d: iou(target, d[1]))
            if iou(target, b) < 0.2:
                print(f"{t:.2f}s: target lost (best IoU {iou(target,b):.2f})")
                break
            target = tuple(float(x) for x in b)

        mask = cv2.resize(result.masks.data[j].cpu().numpy(),
                          (frame.shape[1], frame.shape[0]),
                          interpolation=cv2.INTER_LINEAR) > 0.5
        ends = mask_endpoints(mask)
        if ends is None:
            continue
        p1, p2, cnt = ends
        X1, Y1 = ground_point(float(p1[0]), float(p1[1]))
        X2, Y2 = ground_point(float(p2[0]), float(p2[1]))
        length = math.hypot(X2 - X1, Y2 - Y1)
        Xm, Ym = (X1 + X2) / 2, (Y1 + Y2) / 2
        rows.append({
            "t": round(t, 2),
            "class": name,
            "conf": round(conf, 3),
            "x1": round(float(target[0]), 1),
            "y1": round(float(target[1]), 1),
            "x2": round(float(target[2]), 1),
            "y2": round(float(target[3]), 1),
            "length_m": round(length, 2),
            "X1": round(X1, 1), "Y1": round(Y1, 1),
            "X2": round(X2, 1), "Y2": round(Y2, 1),
            "Xm": round(Xm, 1), "Ym": round(Ym, 1),
            "mask_area": int(mask.sum()),
        })
        print(f"{t:.2f}s {name} conf={conf:.2f} L={length:.2f}m "
              f"Xm={Xm:.1f} Ym={Ym:.1f} area={int(mask.sum())}")

    cap.release()
    csv_path = out_dir / "timepass_bus.csv"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        stable = [r for r in rows if r["mask_area"] >= args.min_area]
        use = stable if len(stable) >= 2 else rows
        lengths = [r["length_m"] for r in use]
        print(f"\nstable frames (area>={args.min_area}): {len(use)}/{len(rows)}")
        print(f"length: median {statistics.median(lengths):.2f} m, "
              f"mean {statistics.mean(lengths):.2f} m, "
              f"min {min(lengths):.2f}, max {max(lengths):.2f}")
        if len(use) >= 2:
            dt = use[-1]["t"] - use[0]["t"]
            dx = use[-1]["Xm"] - use[0]["Xm"]
            if dt > 0:
                print(f"speed (ground midpoint): {dx/dt:.2f} m/s = {dx/dt*3.6:.1f} km/h")
        print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
