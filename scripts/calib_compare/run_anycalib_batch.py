#!/usr/bin/env python
"""Run AnyCalib on a folder of frames and dump per-frame intrinsics."""
from __future__ import annotations

import argparse
import json
import statistics
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
    return [f"p{i}" for i in range(8)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--model-id", default="anycalib_pinhole")
    ap.add_argument("--cam-id", default="simple_pinhole")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    torch.set_num_threads(max(1, min(8, torch.get_num_threads())))
    from anycalib import AnyCalib

    paths = sorted(Path(args.folder).glob("*.png"))
    images = []
    for p in paths:
        arr = np.array(Image.open(p).convert("RGB"))
        images.append(torch.tensor(arr, dtype=torch.float32).permute(2, 0, 1) / 255.0)
    batch = torch.stack(images)
    model = AnyCalib(model_id=args.model_id)
    model.eval()
    with torch.no_grad():
        pred = model.predict(batch, cam_id=args.cam_id)

    names = names_for(args.cam_id)
    rows = []
    for p, intrins in zip(paths, pred["intrinsics"]):
        vals = intrins.detach().cpu().reshape(-1).tolist()
        d = dict(zip(names, vals))
        if "f" in d:
            d["fx"] = d["fy"] = d["f"]
        rows.append({"frame": p.name, "intrinsics": d, "raw": vals})

    fx = [r["intrinsics"].get("fx") for r in rows if r["intrinsics"].get("fx") is not None]
    fy = [r["intrinsics"].get("fy") for r in rows if r["intrinsics"].get("fy") is not None]
    summary = {
        "folder": str(Path(args.folder)),
        "model_id": args.model_id,
        "cam_id": args.cam_id,
        "n_frames": len(rows),
        "fx_median": statistics.median(fx) if fx else None,
        "fy_median": statistics.median(fy) if fy else None,
        "f_median": statistics.median((a + b) / 2 for a, b in zip(fx, fy)) if fx and fy else None,
        "fx_min": min(fx) if fx else None,
        "fx_max": max(fx) if fx else None,
        "frames": rows,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "frames"}, indent=2))
    for r in rows:
        d = r["intrinsics"]
        print(r["frame"], {k: round(v, 3) for k, v in d.items()})


if __name__ == "__main__":
    main()
