#!/usr/bin/env python
"""Evaluate Apple Depth Pro focal-length prediction on SVLD frames.

Depth Pro predicts a horizontal field of view from a single image and converts
it to a focal length in pixels.  It resizes the input to 1536x1536 internally,
so we report both the raw value and the value rescaled to the original width.

Run with the depth-pro virtualenv:
  D:\tmp\depthpro-env\Scripts\python.exe scripts\svld_depthpro.py --per-scene 1
"""

from __future__ import annotations

import argparse
import csv
import statistics
import time
from pathlib import Path

import torch

from depth_pro import create_model_and_transforms, load_rgb
from depth_pro.depth_pro import DEFAULT_MONODEPTH_CONFIG_DICT, DepthProConfig

CKPT = Path(r"D:\tmp\depthpro-weights\depth_pro.pt")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--per-scene", type=int, default=1)
    ap.add_argument("--scene", default=None)
    ap.add_argument("--out", default="out/svld_depthpro")
    args = ap.parse_args()

    rows = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    by_scene: dict[str, list[dict]] = {}
    for r in rows:
        if args.scene and r["scene"] != args.scene:
            continue
        by_scene.setdefault(r["scene"], []).append(r)
    selected = []
    for scene, items in by_scene.items():
        selected.extend(items[: args.per_scene])

    cfg = DepthProConfig(
        patch_encoder_preset=DEFAULT_MONODEPTH_CONFIG_DICT.patch_encoder_preset,
        image_encoder_preset=DEFAULT_MONODEPTH_CONFIG_DICT.image_encoder_preset,
        decoder_features=DEFAULT_MONODEPTH_CONFIG_DICT.decoder_features,
        checkpoint_uri=str(CKPT),
        use_fov_head=True,
        fov_encoder_preset=DEFAULT_MONODEPTH_CONFIG_DICT.fov_encoder_preset,
    )
    model, transform = create_model_and_transforms(
        config=cfg, device=torch.device("cpu"), precision=torch.float32
    )
    model.eval()

    out_rows = []
    for item in selected:
        image, _, f_exif = load_rgb(item["source"])
        h, w = image.shape[:2]
        t0 = time.time()
        with torch.no_grad():
            pred = model.infer(transform(image), f_px=None)
        elapsed = time.time() - t0
        f = pred["focallength_px"]
        f = float(f.item()) if hasattr(f, "item") else float(f)
        f_gt = float(item["f_px"])
        row = {
            "scene": item["scene"],
            "image": item["image"],
            "width": w,
            "height": h,
            "f_gt": round(f_gt, 3),
            "f_pred": round(f, 3),
            "f_ratio": round(f / f_gt, 4),
            "f_pred_square": round(f * 1536.0 / w, 3),
            "f_ratio_square": round((f * 1536.0 / w) / f_gt, 4),
            "elapsed_s": round(elapsed, 1),
            "f_exif": f_exif if f_exif else "",
        }
        out_rows.append(row)
        print(row, flush=True)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "depthpro.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)
    print("\nsummary")
    for scene in sorted({r["scene"] for r in out_rows}):
        rs = [r for r in out_rows if r["scene"] == scene]
        print(
            scene,
            "f_ratio med",
            round(statistics.median(r["f_ratio"] for r in rs), 3),
            "square med",
            round(statistics.median(r["f_ratio_square"] for r in rs), 3),
        )
    print(f"wrote {out / 'depthpro.csv'}")


if __name__ == "__main__":
    main()
