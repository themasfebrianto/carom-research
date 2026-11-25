#!/usr/bin/env python
"""Test self-calibration with the existing yolo3Dbbox model.

The model predicts vehicle dimensions and local orientation from a 224x224
crop.  Given a candidate focal length it solves the 3D location from the 2D
box.  We sweep f, project the predicted 3D box and compare its corners with
the annotated SVLD 3D box.  A clear minimum at the GT f would mean the
existing 3D detector can calibrate the camera without a known K.

Run with the yolo3Dbbox virtualenv:
  D:\Kerjaan\yolo3Dbbox\.venv\Scripts\python.exe ^
    scripts\svld_yolo3d_selfcal.py --scene 0cam --limit 3
"""

from __future__ import annotations

import argparse
import math
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

from library.Math import calc_location, create_corners, rotation_matrix  # noqa: E402
from torch_lib import Model  # noqa: E402
from torch_lib.ClassAverages import ClassAverages  # noqa: E402


def numbers(text: str) -> list[float]:
    return [
        float(x)
        for x in text.replace("(", "").replace(")", "").replace(",", " ").split()
    ]


def theta_ray(img: np.ndarray, box_2d, f: float) -> float:
    width = img.shape[1]
    fovx = 2 * math.atan(width / (2 * f))
    center = (box_2d[1][0] + box_2d[0][0]) / 2.0
    dx = center - width / 2.0
    mult = -1.0 if dx < 0 else 1.0
    angle = math.atan((2 * abs(dx) * math.tan(fovx / 2)) / width)
    return angle * mult


def project(corners: np.ndarray, f: float, cx: float, cy: float) -> np.ndarray:
    corners = np.asarray(corners, float)
    return np.stack(
        [f * corners[:, 0] / corners[:, 2] + cx, f * corners[:, 1] / corners[:, 2] + cy],
        axis=1,
    )


def corner_error(pred: np.ndarray, gt: np.ndarray) -> float:
    d = np.linalg.norm(pred[:, None, :] - gt[None, :, :], axis=2)
    return float(d.min(axis=0).mean())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="0cam")
    ap.add_argument("--limit", type=int, default=2)
    ap.add_argument("--fmin", type=float, default=300.0)
    ap.add_argument("--fmax", type=float, default=8000.0)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--ann-root", default=r"data\svld\TESTDATA2021\TESTDATA2021\Annotations")
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    args = ap.parse_args()

    import csv

    manifest = [
        r
        for r in csv.DictReader(Path(args.manifest).open(encoding="utf-8"))
        if r["scene"] == args.scene
    ][: args.limit]

    model = Model.Model(features=vgg.vgg19_bn(weights=None).features, bins=2)
    ckpt = torch.load(
        REPO / "weights" / "epoch_10.pkl", map_location="cpu", weights_only=False
    )
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    averages = ClassAverages()
    angle_bins = np.arange(2) * np.pi + np.pi / 2

    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
    )
    to_tensor = transforms.Compose([transforms.ToTensor(), normalize])

    for item in manifest:
        ann = Path(args.ann_root) / f"{Path(item['source']).stem}.xml"
        root = ET.parse(ann).getroot()
        img = cv2.imread(item["source"])
        h, w = img.shape[:2]
        cx, cy = w / 2.0, h / 2.0
        f_gt = float(item["f_px"])
        for oi, obj in enumerate(root.findall("object")):
            bbox = [float(x) for x in (obj.findtext("bbox2d") or "").split()]
            v2 = np.array(numbers(obj.findtext("vertex2d") or "")).reshape(8, 2)
            if len(bbox) != 4:
                continue
            x, y, bw, bh = bbox
            box_2d = [(int(x), int(y)), (int(x + bw), int(y + bh))]
            crop = img[box_2d[0][1] : box_2d[1][1] + 1, box_2d[0][0] : box_2d[1][0] + 1]
            if crop.size == 0:
                continue
            crop = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_CUBIC)
            inp = to_tensor(crop).unsqueeze(0)
            with torch.no_grad():
                orient, conf, dim = model(inp)
            dim = dim.cpu().numpy()[0] + averages.get_item("car")
            orient = orient.cpu().numpy()[0]
            conf = conf.cpu().numpy()[0]
            k = int(np.argmax(conf))
            alpha = math.atan2(orient[k, 1], orient[k, 0]) + angle_bins[k] - math.pi

            fs = np.geomspace(args.fmin, args.fmax, args.steps)
            errs = []
            for f in fs:
                tr = theta_ray(img, box_2d, f)
                P = np.array([[f, 0, cx, 0], [0, f, cy, 0], [0, 0, 1, 0]], float)
                loc, _ = calc_location(dim, P, box_2d, alpha, tr)
                corners = create_corners(dim, loc, rotation_matrix(alpha + tr))
                pred = project(np.array(corners), f, cx, cy)
                errs.append(corner_error(pred, v2))
            errs = np.array(errs)
            best = int(np.argmin(errs))
            f_best = float(fs[best])
            f_at_gt = float(np.interp(f_gt, fs, errs))
            print(
                f"{args.scene} {Path(item['source']).stem} obj{oi} "
                f"dims(hwl)={np.round(dim, 2)} alpha={math.degrees(alpha):6.1f} "
                f"f_gt={f_gt:7.1f} f_best={f_best:7.1f} "
                f"err@best={errs[best]:6.2f}px err@gt={f_at_gt:6.2f}px "
                f"ratio={f_best/f_gt:5.2f}"
            )
            for f, e in zip(fs[:: max(1, args.steps // 12)], errs[:: max(1, args.steps // 12)]):
                print(f"    f={f:8.1f} err={e:7.2f}px")


if __name__ == "__main__":
    main()
