"""Gambar overlay box 3D GT (hijau) vs prediksi checkpoint (merah).

Contoh:
  py scripts/overlay_centerloc3d_ckpt.py --line out/centerloc3d/DATA2021_scene_val.txt --index 0 --out out/centerloc3d_test/overlay_ac.jpg
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as F

EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
]


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=r"C:\Users\omega\AppData\Local\Temp\opencode\CenterLoc3D_fresh")
    ap.add_argument("--ckpt", default=r"D:\Kerjaan\riset-carom\checkpoint_best.pth")
    ap.add_argument("--line", required=True)
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--peak-thresh", type=float, default=0.25)
    return ap.parse_args()


def feat_to_raw(v, W, H):
    """v: (8,2) feature -> raw pixel (lihat konversi di utils/loss.py)."""
    v = np.asarray(v, dtype=np.float64).copy()
    v[:, 0] = v[:, 0] * W / 128.0
    v[:, 1] = v[:, 1] * W / 128.0 - abs(W - H) / 2.0
    return v


def draw_box(img, pts, color, thick=2, radius=3):
    pts = np.round(pts).astype(int)
    for a, b in EDGES:
        cv2.line(img, tuple(pts[a]), tuple(pts[b]), color, thick, cv2.LINE_AA)
    for p in pts:
        cv2.circle(img, tuple(p), radius, color, -1, cv2.LINE_AA)


def main():
    args = parse_args()
    repo = Path(args.repo).resolve()
    line_path = Path(args.line).resolve()
    out_path = Path(args.out).resolve()
    sys.path.insert(0, str(repo))
    os.chdir(repo / "train")
    np.float = float

    from dataset.dataloader import Bbox3dDatasets, bbox3d_dataset_collate
    from nets.fpn import KeyPointDetection

    lines = [ln for ln in line_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    line = lines[args.index]
    ds = Bbox3dDatasets([line], (512, 512, 3), 3, False)
    batch = bbox3d_dataset_collate([ds[0]])
    imgs = torch.from_numpy(batch[0]).float()
    raw_w, raw_h = int(batch[9][0]), int(batch[10][0])

    model = KeyPointDetection("resnet", 2, 3, pretrained_weights=False)
    ck = torch.load(args.ckpt, map_location="cpu", weights_only=False)
    model.load_state_dict(ck["state_dict"])
    model.eval()

    with torch.no_grad():
        pred_hm, pred_center, pred_vertex, pred_size = model(imgs)
    pv = pred_vertex[0].permute(1, 2, 0).numpy()  # (128,128,16)
    hm = pred_hm[0].max(0).values
    pooled = F.max_pool2d(hm[None, None], 3, 1, 1)[0, 0]
    peaks = torch.nonzero((hm == pooled) & (hm > args.peak_thresh))
    print("peaks:", len(peaks))

    img = cv2.imread(line.split(" ")[0])
    H, W = img.shape[:2]
    assert (W, H) == (raw_w, raw_h), (W, H, raw_w, raw_h)

    # GT boxes (hijau)
    box_info = np.array([list(map(float, b.split(","))) for b in line.split(" ")[2:]])
    for box in box_info:
        gt_v = box[7:23].reshape(8, 2)
        draw_box(img, feat_to_raw(gt_v, W, H), (0, 200, 0), 3, 2)
        base = (int(box[27]), int(box[28]))
        cv2.circle(img, base, 5, (0, 200, 0), -1, cv2.LINE_AA)

    # Prediksi (merah) di setiap peak
    for y, x in peaks.tolist():
        pred_v = pv[y, x].reshape(8, 2)
        draw_box(img, feat_to_raw(pred_v, W, H), (0, 0, 255), 1, 2)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img)
    print("tulis", out_path)


if __name__ == "__main__":
    main()
