#!/usr/bin/env python
"""Run PerspectiveFields (CVPR 2023) on SVLD frames.

PerspectiveFields predicts a per-pixel up-vector field and a latitude field.
From these it regresses roll, pitch and vertical FoV.  We evaluate:

  * f from the predicted vFoV against the SVLD GT f
  * the vertical vanishing point recovered from the up-vector field
    against the GT vertical direction

Example:
  py scripts/svld_perspective_fields.py --limit 100
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

import cv2
import numpy as np
import torch

from perspective2d import PerspectiveFields


def rotation(phi: float, theta: float) -> np.ndarray:
    return np.array(
        [
            [math.cos(theta), -math.sin(theta), 0.0],
            [-math.sin(phi) * math.sin(theta), -math.sin(phi) * math.cos(theta), -math.cos(phi)],
            [math.cos(phi) * math.sin(theta), math.cos(phi) * math.cos(theta), -math.sin(phi)],
        ]
    )


def angle_deg(a, b) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    a = a / (np.linalg.norm(a) + 1e-12)
    b = b / (np.linalg.norm(b) + 1e-12)
    return math.degrees(math.acos(min(1.0, abs(float(a @ b)))))


def vvp_from_up_field(up: np.ndarray, step: int = 16) -> tuple[float, float, int]:
    """Intersect the per-pixel up-vector lines.

    up has shape (2, H, W); up[0], up[1] are the x/y components of the
    direction that points towards the vertical vanishing point.
    """
    h, w = up.shape[1:]
    ys = np.arange(step // 2, h, step)
    xs = np.arange(step // 2, w, step)
    xx, yy = np.meshgrid(xs, ys)
    u = up[0][yy, xx].reshape(-1)
    v = up[1][yy, xx].reshape(-1)
    mag = np.hypot(u, v)
    keep = mag > 1e-6
    xx, yy, u, v = xx.reshape(-1)[keep], yy.reshape(-1)[keep], u[keep], v[keep]

    # A line through p with direction d has normal n=(-d_y, d_x).
    n = np.stack([-v, u], axis=1)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    p = np.stack([xx, yy], axis=1).astype(float)
    b = (n * p).sum(axis=1)

    # IRLS to reduce the influence of local up-vector errors.
    weights = np.ones(len(n))
    sol = np.array([np.nan, np.nan])
    for _ in range(8):
        aw = n * weights[:, None]
        bw = b * weights
        sol, *_ = np.linalg.lstsq(aw, bw, rcond=None)
        resid = np.abs(n @ sol - b)
        scale = np.median(resid) * 1.4826 + 1e-6
        weights = 1.0 / (1.0 + (resid / (2.5 * scale)) ** 2)
    return float(sol[0]), float(sol[1]), int(len(n))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--step", type=int, default=16)
    ap.add_argument(
        "--version", default="Paramnet-360Cities-edina-centered"
    )
    ap.add_argument("--out", default="out/svld_perspective_fields")
    args = ap.parse_args()

    rows = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    if args.limit:
        rows = rows[: args.limit]

    model = PerspectiveFields(args.version).eval()
    torch.set_grad_enabled(False)

    out_rows = []
    for start in range(0, len(rows), args.batch):
        chunk = rows[start : start + args.batch]
        images = [cv2.imread(r["source"]) for r in chunk]
        keep = [i for i, im in enumerate(images) if im is not None]
        if not keep:
            continue
        images = [images[i] for i in keep]
        chunk = [chunk[i] for i in keep]
        preds = model.inference_batch(img_bgr_list=images)

        for item, img, pred in zip(chunk, images, preds):
            h, w = img.shape[:2]
            vfov = float(pred["pred_general_vfov"])
            f_pred = (h / 2.0) / math.tan(math.radians(vfov) / 2.0)
            f_gt = float(item["f_px"])
            pitch_gt = float(item["pitch_rad"])
            yaw_gt = float(item["yaw_rad"])

            up = pred["pred_gravity_original"].cpu().numpy()
            vx, vy, n_lines = vvp_from_up_field(up, step=args.step)

            # GT vertical direction.  SVLD pitch is positive downwards.
            R = rotation(pitch_gt, yaw_gt)
            vert = R @ np.array([0.0, 1.0, 0.0])
            K = np.array(
                [[f_gt, 0, w / 2.0], [0, f_gt, h / 2.0], [0, 0, 1.0]]
            )
            vvp_ray = np.linalg.inv(K) @ np.array([vx, vy, 1.0])
            vvp_angle = angle_deg(vvp_ray, vert)

            # f implied by the VVP if GT pitch were known.
            denom = math.tan(pitch_gt)
            f_from_vvp = (
                abs((h / 2.0 - vy) / denom) if abs(denom) > 1e-4 else float("nan")
            )

            out_rows.append(
                {
                    "split": item["split"],
                    "scene": item["scene"],
                    "image": item["image"],
                    "f_gt": round(f_gt, 3),
                    "vfov_pred_deg": round(vfov, 4),
                    "f_pred": round(f_pred, 3),
                    "f_ratio": round(f_pred / f_gt, 4),
                    "pitch_pred_deg": round(float(pred["pred_pitch"]), 4),
                    "roll_pred_deg": round(float(pred["pred_roll"]), 4),
                    "pitch_gt_deg": round(math.degrees(pitch_gt), 4),
                    "vvp_x": round(vx, 1),
                    "vvp_y": round(vy, 1),
                    "vvp_n_lines": n_lines,
                    "vvp_angle_deg": round(vvp_angle, 3),
                    "f_from_vvp_gtpitch": (
                        round(f_from_vvp, 3) if math.isfinite(f_from_vvp) else ""
                    ),
                }
            )
            print(
                f"{item['scene']:18s} {item['image']:30s} "
                f"f={f_pred:7.1f}/{f_gt:7.1f} ({f_pred/f_gt:5.2f}) "
                f"vfov={vfov:5.1f} vvp=({vx:7.1f},{vy:8.1f}) "
                f"angle={vvp_angle:5.1f}",
                flush=True,
            )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for r in out_rows for k in r})
    with (out / "perspective_fields.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)
    (out / "summary.json").write_text(
        json.dumps(
            {
                "version": args.version,
                "n": len(out_rows),
                "manifest": args.manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nsummary by scene")
    for scene in sorted({r["scene"] for r in out_rows}):
        rs = [r for r in out_rows if r["scene"] == scene]
        ratios = [r["f_ratio"] for r in rs]
        angles = [r["vvp_angle_deg"] for r in rs]
        print(
            f"  {scene:18s} n={len(rs):2d} "
            f"f_ratio med={statistics.median(ratios):5.3f} "
            f"pass5%={sum(abs(x - 1) < 0.05 for x in ratios):2d}/{len(rs)} "
            f"vvp_med={statistics.median(angles):5.2f} "
            f"vvp<2deg={sum(a < 2 for a in angles):2d}/{len(rs)}"
        )
    print(f"wrote {out / 'perspective_fields.csv'}")


if __name__ == "__main__":
    main()
