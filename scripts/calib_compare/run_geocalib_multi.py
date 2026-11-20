#!/usr/bin/env python
"""Run GeoCalib multi-image shared-intrinsics calibration on a folder of frames."""
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

import torch


def flatten(x):
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().reshape(-1).tolist()
    return x


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out", required=True)
    ap.add_argument("--weights", default="pinhole", choices=["pinhole", "distorted"])
    args = ap.parse_args()

    torch.set_num_threads(max(1, min(8, torch.get_num_threads())))
    from geocalib import GeoCalib

    model = GeoCalib(weights=args.weights)
    paths = sorted(
        p for p in Path(args.folder).iterdir()
        if p.suffix.lower() in (".png", ".jpg", ".jpeg")
    )
    if not paths:
        raise SystemExit(f"no images under {args.folder}")
    images = [model.load_image(p) for p in paths]
    batch = torch.stack(images)
    out = model.calibrate(batch, shared_intrinsics=True)
    camera, gravity = out["camera"], out["gravity"]
    fs = flatten(camera.f)
    cs = flatten(camera.c)
    pitches = flatten(gravity.pitch)
    rolls = flatten(gravity.roll)
    uncs = flatten(out.get("focal_uncertainty")) if out.get("focal_uncertainty") is not None else None

    result = {
        "folder": str(Path(args.folder)),
        "n_images": len(paths),
        "weights": args.weights,
        "f_each": fs,
        "f_median": statistics.median(fs),
        "cx_each": cs[0::2],
        "cy_each": cs[1::2],
        "pitch_deg_raw_each": [math.degrees(x) for x in pitches],
        "pitch_deg_down_positive_median": -math.degrees(statistics.median(pitches)),
        "roll_deg_each": [math.degrees(x) for x in rolls],
        "roll_deg_median": math.degrees(statistics.median(rolls)),
        "focal_uncertainty_each": uncs,
        "focal_uncertainty_median": statistics.median(uncs) if uncs else None,
        "hfov_deg_median": math.degrees(2 * math.atan(camera.size[0, 0].item() / (2 * statistics.median(fs)))),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
