#!/usr/bin/env python
"""Container-anchored scale check without field access.

Two standard containers are used:
  20 ft TEMA: verified SAM2 mask; L=6.046 m vs 6.058 m (-0.2%).
  40 ft SINKOR: GrabCut side mask; length only, because the side view biases W.
The 40 ft type is uncertain (40 vs 45 ft), so it is a cross-check, not a
second anchor.

Example:
  py scripts/cawang_container_anchor.py --out out/timepass/anchor
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np


def largest_component(mask: np.ndarray, min_area: int = 300) -> np.ndarray:
    mask = (mask > 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        return mask.astype(bool)
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    if stats[idx, cv2.CC_STAT_AREA] < min_area:
        return np.zeros_like(mask, dtype=bool)
    return labels == idx


def grabcut_blue(image: np.ndarray, crop: tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = crop
    roi = image[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    blue = ((h > 90) & (h < 140) & (s > 80) & (v > 35)).astype(np.uint8)
    init = np.full(blue.shape, cv2.GC_BGD, np.uint8)
    init[blue > 0] = cv2.GC_PR_FGD
    init[0:5, :] = cv2.GC_BGD
    init[-5:, :] = cv2.GC_BGD
    rect = (5, 5, blue.shape[1] - 10, blue.shape[0] - 10)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(roi, init, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    mask_crop = ((init == cv2.GC_FGD) | (init == cv2.GC_PR_FGD)).astype(np.uint8)
    mask_crop = largest_component(mask_crop)
    full = np.zeros(image.shape[:2], np.uint8)
    full[y1:y2, x1:x2] = mask_crop
    return full.astype(bool)


def fit_mask(image_path: str, mask: np.ndarray, crop: tuple[int, int, int, int],
             out_dir: Path) -> dict:
    mask_path = out_dir / "masks" / f"{Path(image_path).stem}_mask.npy"
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(mask_path, mask)
    fit_dir = out_dir / Path(image_path).stem
    cmd = [
        sys.executable, "scripts/cawang_container_fit.py",
        "--image", image_path,
        "--mask", str(mask_path),
        "--box", ",".join(str(v) for v in crop),
        "--height", "2.591",
        "--out", str(fit_dir),
        "--maxiter", "50",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    result = json.loads((fit_dir / "container_fit.json").read_text(encoding="utf-8"))
    result["mask"] = str(mask_path)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/timepass/anchor")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    verified = Path("out/timepass/container20/container_fit.json")
    if verified.exists():
        fit = json.loads(verified.read_text(encoding="utf-8"))
        rows.append({
            "object": "20ft_tema",
            "image": Path(fit["image"]).name,
            "L_m": fit["L_m"],
            "W_m": fit["W_m"],
            "IoU": fit["iou"],
            "standard_L_m": 6.058,
            "standard_W_m": 2.438,
            "eL_pct": round(abs(fit["L_m"] - 6.058) / 6.058 * 100, 2),
            "eW_pct": round(abs(fit["W_m"] - 2.438) / 2.438 * 100, 2),
            "note": "verified SAM2 mask; length+width anchor",
        })

    image_path = "out/timepass/truck86.jpg"
    crop = (75, 435, 385, 708)
    image = cv2.imread(image_path)
    if image is not None:
        mask = grabcut_blue(image, crop)
        if mask.sum() >= 300:
            fit = fit_mask(image_path, mask, crop, out_dir)
            rows.append({
                "object": "40ft_sinkor_grabcut",
                "image": Path(image_path).name,
                "L_m": fit["L_m"],
                "W_m": fit["W_m"],
                "IoU": fit["iou"],
                "standard_L_m": 12.192,
                "standard_W_m": 2.438,
                "eL_pct": round(abs(fit["L_m"] - 12.192) / 12.192 * 100, 2),
                "eW_pct": round(abs(fit["W_m"] - 2.438) / 2.438 * 100, 2),
                "note": "length only; W biased by side mask; type 40 vs 45 ft unknown",
            })

    if not rows:
        raise SystemExit("no container result; check the 20 ft JSON and truck86 image")

    with (out_dir / "container_anchor.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "container_anchor.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    for row in rows:
        print(
            f"{row['object']:20s} L={row['L_m']:.3f} "
            f"({row['eL_pct']:.2f}%) W={row['W_m']:.3f} "
            f"({row['eW_pct']:.2f}%) IoU={row['IoU']:.4f}"
        )
    print(f"wrote {out_dir / 'container_anchor.csv'}")


if __name__ == "__main__":
    main()
