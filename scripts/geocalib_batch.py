#!/usr/bin/env python
"""Batch GeoCalib inference with per-image error handling.

Run with the GeoCalib environment, for example:
  & "$GEO\\Scripts\\python.exe" scripts\\geocalib_batch.py IMAGES... --out out/i24/geocalib.json
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch
from geocalib import GeoCalib


def probe(model, path: str) -> dict:
    img = model.load_image(path)
    res = model.calibrate(img)
    cam, grav = res["camera"], res["gravity"]
    f = float(cam.f.reshape(-1)[0].item())
    pitch = float(grav.pitch.reshape(-1)[0].item())
    roll = float(grav.roll.reshape(-1)[0].item())
    height, width = int(img.shape[-2]), int(img.shape[-1])
    return {
        "image": path,
        "width": width,
        "height": height,
        "f_px": round(f, 3),
        "hfov_deg": round(2.0 * math.degrees(math.atan((width / 2.0) / f)), 3),
        "vfov_deg": round(2.0 * math.degrees(math.atan((height / 2.0) / f)), 3),
        "pitch_deg": round(math.degrees(pitch), 4),
        "roll_deg": round(math.degrees(roll), 4),
        "horizon_row": round(height / 2.0 - f * math.tan(pitch), 3),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    model = GeoCalib().to(args.device)
    results = []
    for path in args.images:
        try:
            row = probe(model, path)
            results.append(row)
            print(json.dumps(row), flush=True)
        except Exception as exc:  # keep the batch alive
            row = {"image": path, "error": f"{type(exc).__name__}: {exc}"}
            results.append(row)
            print(json.dumps(row), flush=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))

    ok = [r for r in results if "error" not in r]
    print(f"\n{len(ok)}/{len(results)} ok -> {out}")
    if ok:
        fs = [r["f_px"] for r in ok]
        ps = [r["pitch_deg"] for r in ok]
        print(f"f: min {min(fs):.1f} max {max(fs):.1f} mean {sum(fs)/len(fs):.1f} px")
        print(f"pitch: min {min(ps):.2f} max {max(ps):.2f} mean {sum(ps)/len(ps):.2f} deg")


if __name__ == "__main__":
    main()
