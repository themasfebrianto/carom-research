#!/usr/bin/env python
"""Compare yolo3Dbbox dimension predictions with SVLD GT dimensions.

Run with the yolo3Dbbox virtualenv:
  D:\Kerjaan\yolo3Dbbox\.venv\Scripts\python.exe scripts\svld_yolo3d_dims.py --n 20
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np
import torch
from torchvision import transforms
from torchvision.models import vgg

REPO = Path(r"D:\Kerjaan\yolo3Dbbox")
sys.path.insert(0, str(REPO))

from torch_lib import Model  # noqa: E402
from torch_lib.ClassAverages import ClassAverages  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--ann-root", default=r"data\svld\TESTDATA2021\TESTDATA2021\Annotations")
    ap.add_argument("--n", type=int, default=20)
    args = ap.parse_args()

    model = Model.Model(features=vgg.vgg19_bn(weights=None).features, bins=2)
    ckpt = torch.load(
        REPO / "weights" / "epoch_10.pkl", map_location="cpu", weights_only=False
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    averages = ClassAverages()
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    )
    to_tensor = transforms.Compose([transforms.ToTensor(), normalize])

    rows = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    errs = {"H": [], "W": [], "L": []}
    for item in rows:
        if len(errs["H"]) >= args.n:
            break
        ann = Path(args.ann_root) / f"{Path(item['source']).stem}.xml"
        if not ann.exists():
            continue
        root = ET.parse(ann).getroot()
        obj = root.find("object")
        if obj is None:
            continue
        bbox = [float(x) for x in (obj.findtext("bbox2d") or "").split()]
        dims = [float(x) for x in (obj.findtext("veh_size") or "").split()]
        if len(bbox) != 4 or len(dims) != 3:
            continue
        x, y, w, h = bbox
        img = cv2.imread(item["source"])
        crop = img[int(y) : int(y + h) + 1, int(x) : int(x + w) + 1]
        if crop.size == 0:
            continue
        crop = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_CUBIC)
        with torch.no_grad():
            _, _, dim = model(to_tensor(crop).unsqueeze(0))
        pred_hwl = dim.cpu().numpy()[0] + averages.get_item("car")
        gt_hwl = np.array([dims[2], dims[1], dims[0]])  # L,W,H -> H,W,L
        for k, idx in zip(("H", "W", "L"), range(3)):
            errs[k].append(abs(pred_hwl[idx] / gt_hwl[idx] - 1.0) * 100.0)
        print(
            f"{item['scene']:18s} {Path(item['source']).stem:30s} "
            f"GT(HWL)={np.round(gt_hwl,2)} pred={np.round(pred_hwl,2)}"
        )

    print("\nmedian absolute dimension error")
    for k in ("H", "W", "L"):
        print(
            f"  {k}: {statistics.median(errs[k]):5.1f}% "
            f"(p90 {np.percentile(errs[k], 90):5.1f}%, n={len(errs[k])})"
        )


if __name__ == "__main__":
    main()
