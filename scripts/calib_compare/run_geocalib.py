#!/usr/bin/env python
"""Run GeoCalib on one image and dump the calibration parameters as JSON."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch


def tensor_to_list(x):
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().reshape(-1).tolist()
    return x


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--weights", default="pinhole", choices=["pinhole", "distorted"])
    ap.add_argument("--camera-model", default="pinhole")
    ap.add_argument("--prior-focal", type=float, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    torch.set_num_threads(max(1, min(8, torch.get_num_threads())))
    from geocalib import GeoCalib

    model = GeoCalib(weights=args.weights)
    image = model.load_image(args.image)
    priors = None
    if args.prior_focal is not None:
        priors = {"focal": torch.tensor(args.prior_focal, dtype=torch.float32)}
    out = model.calibrate(image, camera_model=args.camera_model, priors=priors)

    camera = out["camera"]
    gravity = out["gravity"]
    f = tensor_to_list(camera.f)
    c = tensor_to_list(camera.c)
    hfov = tensor_to_list(camera.hfov)
    vfov = tensor_to_list(camera.vfov)
    pitch = tensor_to_list(gravity.pitch)
    roll = tensor_to_list(gravity.roll)
    vec = tensor_to_list(gravity.vec3d)
    unc = out.get("focal_uncertainty")
    unc = tensor_to_list(unc) if unc is not None else None
    dist = tensor_to_list(camera.dist) if hasattr(camera, "dist") else None

    result = {
        "image": str(Path(args.image)),
        "weights": args.weights,
        "camera_model": args.camera_model,
        "image_width": camera.size[0, 0].item(),
        "image_height": camera.size[0, 1].item(),
        "fx": f[0],
        "fy": f[1] if len(f) > 1 else f[0],
        "cx": c[0],
        "cy": c[1],
        "hfov_deg": math.degrees(hfov[0]),
        "vfov_deg": math.degrees(vfov[0]),
        "pitch_rad": pitch[0],
        "pitch_deg_raw": math.degrees(pitch[0]),
        "pitch_deg_down_positive": -math.degrees(pitch[0]),
        "roll_rad": roll[0],
        "roll_deg": math.degrees(roll[0]),
        "gravity_vec3d": vec,
        "distortion": dist,
        "focal_uncertainty_px": unc[0] if unc else None,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
