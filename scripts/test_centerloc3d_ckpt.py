"""Uji checkpoint CenterLoc3D tanpa training: val loss + akurasi box 3D.

Dipakai untuk menjawab "checkpoint ini bagus atau tidak" tanpa GPU:
  1. muat state_dict ke arsitektur resnet-50 (strict=True),
  2. hitung val loss dengan rumus yang sama seperti trainer,
  3. ukur error vertex/size/center pada sel GT (piksel mentah & meter),
  4. ukur recall deteksi 2D (IoU vs GT box) dari heatmap.

Contoh:
    py scripts/test_centerloc3d_ckpt.py ^
        --ckpt checkpoint_best.pth ^
        --val-txt out/centerloc3d/DATA2021_scene_val.txt ^
        --n 120 --batch 8 --out out/centerloc3d_test
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F


def parse_args():
    ap = argparse.ArgumentParser("Uji checkpoint CenterLoc3D")
    ap.add_argument("--repo", default=r"C:\Users\omega\AppData\Local\Temp\opencode\CenterLoc3D_fresh")
    ap.add_argument("--ckpt", default="checkpoint_best.pth")
    ap.add_argument("--val-txt", default="out/centerloc3d/DATA2021_scene_val.txt")
    ap.add_argument("--n", type=int, default=120, help="jumlah gambar val yang diuji (0 = semua)")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--out", default="out/centerloc3d_test")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--peak-thresh", type=float, default=0.25)
    ap.add_argument("--peak-radius", type=float, default=4.0, help="jarak maksimum peak ke GT (sel 128x128)")
    return ap.parse_args()


def feat_to_raw(x, y, raw_w, raw_h, input_size=512.0, feat_size=128.0):
    """Koordinat feature-map (128) -> piksel gambar mentah."""
    scale = min(input_size / raw_w, input_size / raw_h)
    new_w = int(raw_w * scale)
    new_h = int(raw_h * scale)
    dx = (input_size - new_w) // 2
    dy = (input_size - new_h) // 2
    x_raw = (x * (input_size / feat_size) - dx) / scale
    y_raw = (y * (input_size / feat_size) - dy) / scale
    return x_raw, y_raw


def nms_peaks(hm, thresh, kernel=3):
    """Peak lokal 3x3 pada heatmap (1,128,128)."""
    pooled = F.max_pool2d(hm[None, None], kernel, stride=1, padding=kernel // 2)[0, 0]
    keep = (pooled == hm) & (hm > thresh)
    ys, xs = torch.nonzero(keep, as_tuple=True)
    return xs, ys, hm[ys, xs]


def main():
    args = parse_args()
    repo = Path(args.repo).resolve()
    ckpt_path = Path(args.ckpt).resolve()
    val_txt = Path(args.val_txt).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(repo))
    import os

    os.chdir(repo / "train")
    np.float = float  # CenterLoc3D lama memakai np.float (dihapus di NumPy 2)

    from dataset.dataloader import Bbox3dDatasets, bbox3d_dataset_collate
    import dataset.dataloader as _dlmod

    _dlmod.shuffle = lambda *a, **k: None  # jangan acak urutan; nama gambar harus cocok
    from nets.fpn import KeyPointDetection
    from utils.loss import (
        focal_loss,
        reg_iou_loss_diff as reg_iou_loss,
        reg_l1_loss,
        reproject_l1_loss,
    )

    device = torch.device(args.device)
    input_shape = (512, 512, 3)
    output_shape = (128, 128)

    print(f"checkpoint : {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    print(f"epoch={ckpt.get('epoch')} best={ckpt.get('best')} run_tag={ckpt.get('run_tag')!r}")
    state = ckpt["state_dict"]
    bad = [k for k, v in state.items() if torch.is_tensor(v) and not torch.isfinite(v).all()]
    print(f"tensor tidak hingga: {len(bad)}")
    if bad:
        print("  contoh:", bad[:5])

    model = KeyPointDetection("resnet", 2, num_classes=3, pretrained_weights=False).to(device)
    model.load_state_dict(state, strict=True)
    model.eval()
    print("state_dict cocok (strict=True)")

    lines = [ln for ln in val_txt.read_text(encoding="utf-8").splitlines() if ln.strip()]
    missing = [ln for ln in lines if not Path(ln.split(" ")[0]).exists()]
    if missing:
        print(f"lewati {len(missing)} baris yang gambarnya tidak ada")
        lines = [ln for ln in lines if Path(ln.split(" ")[0]).exists()]
    if args.n and args.n < len(lines):
        rng = np.random.default_rng(args.seed)
        idx = rng.choice(len(lines), size=args.n, replace=False)
        lines = [lines[i] for i in sorted(idx)]
    print(f"val images : {len(lines)}")

    np.random.seed(args.seed)
    ds = Bbox3dDatasets(lines, input_shape, 3, False)
    dl = torch.utils.data.DataLoader(
        ds, batch_size=args.batch, shuffle=False, num_workers=0,
        collate_fn=bbox3d_dataset_collate,
    )

    totals = dict(loss=0.0, cls=0.0, center=0.0, vertex=0.0, size=0.0, reproj=0.0, iou=0.0)
    n_batches = 0
    skipped = 0
    rows = []

    v_err_raw, s_err_m, c_err_raw = [], [], []
    det_total = det_hit = det_peaks = det_fp = 0
    ious = []

    t0 = time.time()
    with torch.no_grad():
        for it, batch in enumerate(dl):
            batch = [torch.from_numpy(b).float() if isinstance(b, np.ndarray) else b.float() for b in batch]
            (
                imgs, calibs, hms, centers, vertices, sizes,
                masks, perspectives, base_points, raw_ws, raw_hs,
            ) = batch
            imgs = imgs.to(device)
            calibs = calibs.to(device)
            hms = hms.to(device)
            centers = centers.to(device)
            vertices = vertices.to(device)
            sizes = sizes.to(device)
            masks = masks.to(device)
            perspectives = perspectives.to(device)
            base_points = base_points.to(device)
            raw_ws = raw_ws.to(device)
            raw_hs = raw_hs.to(device)

            pred_hm, pred_center, pred_vertex, pred_size = model(imgs)

            def terms(sl):
                """Loss per potongan batch (sl = slice), sama seperti trainer."""
                cls_l = focal_loss(pred_hm[sl], hms[sl])
                ctr_l = reg_l1_loss(pred_center[sl], centers[sl], masks[sl], index=2)
                vtx_l = 0.1 * reg_l1_loss(pred_vertex[sl], vertices[sl], masks[sl], index=16)
                siz_l = 0.1 * reg_l1_loss(pred_size[sl], sizes[sl], masks[sl], index=3)
                rpj_l = 0.1 * reproject_l1_loss(
                    pred_vertex[sl], calibs[sl], pred_size[sl], masks[sl], base_points[sl],
                    16, perspectives[sl], output_shape, input_shape, raw_hs[sl], raw_ws[sl],
                )
                iou_l = reg_iou_loss(
                    "ciou", pred_vertex[sl], vertices[sl], masks[sl], perspectives[sl],
                    output_shape, input_shape, raw_hs[sl], raw_ws[sl],
                )
                if iou_l > 1.0:
                    iou_l = torch.log(iou_l)
                return cls_l, ctr_l, vtx_l, siz_l, rpj_l, iou_l

            cls_loss, center_loss, vertex_loss, size_loss, reproj_loss, iou_loss = terms(slice(None))
            loss = cls_loss + center_loss + vertex_loss + size_loss + reproj_loss + iou_loss
            if not torch.isfinite(loss):
                skipped += 1
                continue

            for k, v in (
                ("loss", loss), ("cls", cls_loss), ("center", center_loss),
                ("vertex", vertex_loss), ("size", size_loss),
                ("reproj", reproj_loss), ("iou", iou_loss),
            ):
                totals[k] += float(v)
            n_batches += 1

            # loss per gambar (untuk melihat outlier)
            B = imgs.shape[0]
            for b in range(B):
                t = terms(slice(b, b + 1))
                rows.append({
                    "batch": it,
                    "image": lines[it * args.batch + b].split(" ")[0].split("\\")[-1],
                    "loss": round(float(t[0] + t[1] + t[2] + t[3] + t[4] + t[5]), 4),
                    "cls": round(float(t[0]), 4),
                    "center": round(float(t[1]), 4),
                    "vertex": round(float(t[2]), 4),
                    "size": round(float(t[3]), 4),
                    "reproj": round(float(t[4]), 4),
                    "iou": round(float(t[5]), 4),
                    "objects": int(masks[b].sum()),
                })

            # --- akurasi box 3D pada sel GT ---
            pv = pred_vertex.permute(0, 2, 3, 1)  # B,128,128,16
            ps = pred_size.permute(0, 2, 3, 1)    # B,128,128,3
            pc = pred_center.permute(0, 2, 3, 1)  # B,128,128,2
            B = imgs.shape[0]
            for b in range(B):
                m = masks[b] > 0.5
                if not m.any():
                    continue
                ys, xs = torch.nonzero(m, as_tuple=True)
                rw = float(raw_ws[b])
                rh = float(raw_hs[b])

                # vertex: prediksi vs GT, keduanya di ruang feature
                pv_b = pv[b][ys, xs]  # N,16
                gv_b = vertices[b][ys, xs]
                px, py = feat_to_raw(pv_b[:, 0::2], pv_b[:, 1::2], rw, rh)
                gx, gy = feat_to_raw(gv_b[:, 0::2], gv_b[:, 1::2], rw, rh)
                v_err_raw.append(float(torch.sqrt(((px - gx) ** 2 + (py - gy) ** 2).mean(dim=1)).mean()))
                s_err_m.append(float((ps[b][ys, xs] - sizes[b][ys, xs]).abs().mean()))
                pcx, pcy = feat_to_raw(pc[b][ys, xs, 0], pc[b][ys, xs, 1], rw, rh)
                gcx, gcy = feat_to_raw(centers[b][ys, xs, 0], centers[b][ys, xs, 1], rw, rh)
                c_err_raw.append(float(torch.sqrt((pcx - gcx) ** 2 + (pcy - gcy) ** 2).mean()))

                # --- deteksi 2D dari heatmap ---
                hm = pred_hm[b].max(dim=0).values
                pxs, pys, pscores = nms_peaks(hm, args.peak_thresh)
                matched = set()
                for j in range(len(ys)):
                    cx, cy = float(xs[j]), float(ys[j])
                    if len(pxs) == 0:
                        det_total += 1
                        continue
                    d2 = (pxs.float() - cx) ** 2 + (pys.float() - cy) ** 2
                    k = int(torch.argmin(d2))
                    det_total += 1
                    if float(d2[k]) > args.peak_radius ** 2:
                        continue
                    det_hit += 1
                    matched.add(k)
                    # IoU box 2D: prediksi dari vertex sel peak, GT dari vertex sel GT
                    pvk = pv[b][pys[k], pxs[k]]
                    gvk = gv_b[j]
                    px1 = float(pvk[0::2].min()); px2 = float(pvk[0::2].max())
                    py1 = float(pvk[1::2].min()); py2 = float(pvk[1::2].max())
                    gx1 = float(gvk[0::2].min()); gx2 = float(gvk[0::2].max())
                    gy1 = float(gvk[1::2].min()); gy2 = float(gvk[1::2].max())
                    iw = max(0.0, min(px2, gx2) - max(px1, gx1))
                    ih = max(0.0, min(py2, gy2) - max(py1, gy1))
                    inter = iw * ih
                    union = (px2 - px1) * (py2 - py1) + (gx2 - gx1) * (gy2 - gy1) - inter
                    if union > 0:
                        ious.append(inter / union)
                det_peaks += len(pxs)
                det_fp += len(pxs) - len(matched)

            print(
                f"  batch {it+1}: loss={float(loss):.4f} cls={float(cls_loss):.3f} "
                f"center={float(center_loss):.3f} vertex={float(vertex_loss):.3f} "
                f"size={float(size_loss):.3f} reproj={float(reproj_loss):.3f} "
                f"iou={float(iou_loss):.3f}",
                flush=True,
            )

    elapsed = time.time() - t0
    n = max(n_batches, 1)
    summary = {k: v / n for k, v in totals.items()}
    summary["batches"] = n_batches
    summary["skipped_batches"] = skipped
    summary["seconds"] = round(elapsed, 1)
    summary["seconds_per_image"] = round(elapsed / max(len(lines), 1), 3)
    summary["vertex_err_px"] = round(float(np.mean(v_err_raw)), 2) if v_err_raw else None
    summary["size_err_m"] = round(float(np.mean(s_err_m)), 3) if s_err_m else None
    summary["center_err_px"] = round(float(np.mean(c_err_raw)), 2) if c_err_raw else None
    summary["det_objects"] = det_total
    summary["det_hit"] = det_hit
    summary["det_recall"] = round(det_hit / det_total, 4) if det_total else None
    summary["det_iou_mean"] = round(float(np.mean(ious)), 4) if ious else None
    summary["det_iou_50"] = round(float(np.mean([i >= 0.5 for i in ious])), 4) if ious else None
    summary["det_peaks"] = det_peaks
    summary["det_false_pos"] = det_fp
    summary["det_precision"] = round((det_peaks - det_fp) / det_peaks, 4) if det_peaks else None
    summary["epoch"] = ckpt.get("epoch")
    summary["best"] = ckpt.get("best")
    summary["run_tag"] = ckpt.get("run_tag")
    summary["n_images"] = len(lines)

    losses = sorted(r["loss"] for r in rows)
    if losses:
        summary["loss_median"] = losses[len(losses) // 2]
        summary["loss_p90"] = losses[int(len(losses) * 0.9)]
        summary["loss_max"] = losses[-1]

    (out / "report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    cols = ("batch", "image", "loss", "cls", "center", "vertex", "size", "reproj", "iou", "objects")
    with (out / "images.csv").open("w", encoding="utf-8") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join(str(r[k]) for k in cols) + "\n")

    print("\n=== ringkasan ===")
    for k, v in summary.items():
        print(f"{k:20s} {v}")
    worst = sorted(rows, key=lambda r: -r["loss"])[:5]
    print("\n5 gambar dengan loss terbesar:")
    for r in worst:
        print(f"  {r['image']}: loss={r['loss']} reproj={r['reproj']} vertex={r['vertex']} obj={r['objects']}")
    print(f"\nlaporan: {out/'report.json'}")


if __name__ == "__main__":
    main()
