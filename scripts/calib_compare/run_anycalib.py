#!/usr/bin/env python
"""Run AnyCalib on one image and dump the intrinsics as JSON."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch
from PIL import Image


def names_for(cam_id: str) -> list[str]:
    base = cam_id.partition(":")[0]
    if base == "pinhole":
        return ["fx", "fy", "cx", "cy"]
    if base == "simple_pinhole":
        return ["f", "cx", "cy"]
    if base in {"radial", "simple_radial", "kb", "simple_kb", "division", "simple_division"}:
        n = int(cam_id.partition(":")[2] or 1)
        ff = ["fx", "fy"] if base in {"radial", "kb", "division"} else ["f"]
        return ff + ["cx", "cy"] + [f"k{i}" for i in range(1, n + 1)]
    if base in {"ucm", "simple_ucm", "eucm", "simple_eucm", "fov"}:
        ff = ["fx", "fy"] if base in {"ucm", "eucm", "fov"} else ["f"]
        return ff + ["cx", "cy", "extra"]
    return [f"p{i}" for i in range(len(cam_id))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--model-id", default="anycalib_pinhole",
                    choices=["anycalib_pinhole", "anycalib_gen", "anycalib_dist", "anycalib_edit"])
    ap.add_argument("--cam-id", default="simple_pinhole")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    torch.set_num_threads(max(1, min(8, torch.get_num_threads())))
    from anycalib import AnyCalib

    image = np.array(Image.open(args.image).convert("RGB"))
    image = torch.tensor(image, dtype=torch.float32).permute(2, 0, 1) / 255.0

    model = AnyCalib(model_id=args.model_id)
    model.eval()
    with torch.no_grad():
        pred = model.predict(image, cam_id=args.cam_id)

    intrinsics = pred["intrinsics"].detach().cpu().reshape(-1).tolist()
    names = names_for(args.cam_id)
    result = {
        "image": str(Path(args.image)),
        "model_id": args.model_id,
        "cam_id": args.cam_id,
        "image_width": int(image.shape[-1]),
        "image_height": int(image.shape[-2]),
        "intrinsics": intrinsics,
        "intrinsics_named": dict(zip(names, intrinsics)),
        "pred_size": [int(v) for v in pred["pred_size"]],
    }
    # simple derived values
    d = result["intrinsics_named"]
    if "f" in d:
        result["fx"] = result["fy"] = d["f"]
    else:
        result["fx"] = d.get("fx")
        result["fy"] = d.get("fy")
    result["cx"] = d.get("cx")
    result["cy"] = d.get("cy")
    if result["fx"]:
        result["hfov_deg"] = math.degrees(2 * math.atan(result["image_width"] / (2 * result["fx"])))
    if result["fy"]:
        result["vfov_deg"] = math.degrees(2 * math.atan(result["image_height"] / (2 * result["fy"])))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
