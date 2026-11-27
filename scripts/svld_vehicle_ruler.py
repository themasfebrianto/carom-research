#!/usr/bin/env python
"""Vehicle-ruler L1/L2 validation on SVLD-3D.

The goal is to test whether a vehicle of known width can provide a lane-width
anchor:

    w_lane = W_spec * L_px / V_px

where W_spec is the manufacturer body width (without mirrors), V_px is the
body width in pixels, and L_px is the lane width in pixels at the same ground
contact row.  The formula uses only image measurements and the published
width; SVLD calibration is used only to score the result.

Subcommands
-----------
candidates
    Build the candidate CSV and annotated crops (grid in original pixels).
simulate
    Generate face-edge/contact points from SVLD vertex2d and lane points from
    the scene lane-width prior.  This is a *pipeline check*, not an
    independent measurement; the vertex2d points come from the preset 3D box.
annotate
    OpenCV clicker for the real, independent L1/L2 annotations.  Click order:
    body_left, body_right, lane_left, lane_right, contact.
eval
    Evaluate an annotations CSV (manual or simulated), write results,
    summary and overlays.

Example
-------
  py scripts/svld_vehicle_ruler.py candidates
  py scripts/svld_vehicle_ruler.py simulate
  py scripts/svld_vehicle_ruler.py eval --ann out/svld_vehicle_ruler/annotations_sim.csv
  py scripts/svld_vehicle_ruler.py annotate --ids 0cam_bus_000667,1cam_bus_002664
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from pathlib import Path

import cv2
import numpy as np
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "out/svld_vehicle_ruler"
TEST_ROOT = REPO / "data/svld/TESTDATA2021/TESTDATA2021"
TRAINVAL_ROOTS = {
    "0cam": REPO / "SVLD-3D-TRAINVAL-SCENE-D/DATA2021",
    "1cam": REPO / "SVLD-3D-TRAINVAL-SCENE-E/DATA2021",
    "session0_centre": REPO / "SVLD-3D-TRAINVAL-SCENE-A-C/DATA2021",
    "session0_right": REPO / "SVLD-3D-TRAINVAL-SCENE-A-C/DATA2021",
    "session6_right": REPO / "SVLD-3D-TRAINVAL-SCENE-A-C/DATA2021",
}

# Lane-width priors from the lateral peaks of the SVLD 3D boxes.  These are
# priors, not independent ground truth; they are only used by `simulate`.
LANE_W = {
    "0cam": 3.00,
    "1cam": 2.70,
    "session0_centre": 3.20,
    "session0_right": 3.20,
    "session6_right": 3.25,
}

# The 20 primary vehicles (all <=10 deg relative yaw) plus 4 oblique cases.
# bw/bh are the expected bbox2d sizes used to pick the right object.
CANDIDATES = [
    dict(id="0cam_bus_000667", scene="0cam", cls="Bus", stem="real_scene_cam0_000667", bw=339, bh=404, role="primary"),
    dict(id="0cam_car_005254", scene="0cam", cls="Car", stem="real_scene_cam0_005254", bw=251, bh=214, role="primary"),
    dict(id="0cam_car_004778", scene="0cam", cls="Car", stem="real_scene_cam0_004778", bw=182, bh=171, role="primary"),
    dict(id="0cam_car_014640", scene="0cam", cls="Car", stem="real_scene_cam0_014640", bw=160, bh=150, role="primary"),
    dict(id="1cam_bus_002664", scene="1cam", cls="Bus", stem="real_scene_cam1_002664", bw=263, bh=449, role="primary"),
    dict(id="1cam_car_012704", scene="1cam", cls="Car", stem="real_scene_cam1_012704", bw=125, bh=208, role="primary"),
    dict(id="1cam_car_005176", scene="1cam", cls="Car", stem="real_scene_cam1_005176", bw=120, bh=147, role="primary"),
    dict(id="1cam_car_004098", scene="1cam", cls="Car", stem="real_scene_cam1_004098", bw=88, bh=96, role="primary"),
    dict(id="s0c_truck_000617", scene="session0_centre", cls="Truck", stem="session0_center_000617", bw=336, bh=362, role="primary"),
    dict(id="s0c_car_002850", scene="session0_centre", cls="Car", stem="session0_center_002850", bw=141, bh=128, role="primary"),
    dict(id="s0c_car_007499", scene="session0_centre", cls="Car", stem="session0_center_007499", bw=118, bh=111, role="primary"),
    dict(id="s0c_car_004110", scene="session0_centre", cls="Car", stem="session0_center_004110", bw=121, bh=107, role="primary"),
    dict(id="s0r_car_008012", scene="session0_right", cls="Car", stem="session0_right_008012", bw=266, bh=240, role="primary"),
    dict(id="s0r_car_006781", scene="session0_right", cls="Car", stem="session0_right_006781", bw=198, bh=211, role="primary"),
    dict(id="s0r_car_007989", scene="session0_right", cls="Car", stem="session0_right_007989", bw=198, bh=196, role="primary"),
    dict(id="s0r_car_006690", scene="session0_right", cls="Car", stem="session0_right_006690", bw=177, bh=172, role="primary"),
    dict(id="s6r_truck_000462", scene="session6_right", cls="Truck", stem="session6_right_000462", bw=387, bh=322, role="primary"),
    dict(id="s6r_car_000674", scene="session6_right", cls="Car", stem="session6_right_000674", bw=326, bh=359, role="primary"),
    dict(id="s6r_car_000224", scene="session6_right", cls="Car", stem="session6_right_000224", bw=259, bh=243, role="primary"),
    dict(id="s6r_car_008281", scene="session6_right", cls="Car", stem="session6_right_008281", bw=292, bh=252, role="primary"),
    dict(id="s0c_truck_000630", scene="session0_centre", cls="Truck", stem="session0_center_000630", bw=525, bh=516, role="oblique"),
    dict(id="s6r_truck_000815", scene="session6_right", cls="Truck", stem="session6_right_000815", bw=475, bh=505, role="oblique"),
    dict(id="s0r_car_006645", scene="session0_right", cls="Car", stem="session0_right_006645", bw=187, bh=156, role="oblique"),
    dict(id="s6r_car_008293", scene="session6_right", cls="Car", stem="session6_right_008293", bw=340, bh=301, role="oblique"),
]

ANN_FIELDS = [
    "id", "scene", "image", "class", "model", "W_spec", "spec_source",
    "spec_confidence", "source",
    "body_left_u", "body_left_v", "body_right_u", "body_right_v",
    "lane_left_u", "lane_left_v", "lane_right_u", "lane_right_v",
    "contact_u", "contact_v", "notes",
]


# --------------------------------------------------------------------------
# annotations and camera
# --------------------------------------------------------------------------

def numbers(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text or "")]


def find_asset(scene: str, stem: str) -> tuple[Path, Path, Path]:
    """Return (image_path, annotation_path, root) for a scene image."""
    test_img = TEST_ROOT / "JPEGImages" / f"{stem}.jpg"
    if test_img.exists():
        root = TEST_ROOT
    else:
        root = TRAINVAL_ROOTS[scene]
        test_img = root / "JPEGImages" / f"{stem}.jpg"
        if not test_img.exists():
            raise FileNotFoundError(f"image not found: {stem} ({scene})")
    ann = root / "Annotations" / f"{stem}.xml"
    if not ann.exists():
        raise FileNotFoundError(f"annotation not found: {ann}")
    return test_img, ann, root


def parse_calib(root: Path, ann_root: ET.Element) -> dict:
    calib_name = Path((ann_root.findtext("calibfile") or "").replace("\\", "/")).name
    calib_path = root / "Calib" / calib_name
    if not calib_path.exists():
        # test-set calib can be in the test Calib directory even for a trainval
        # image copied from the same scene; fall back to a recursive search.
        matches = list(REPO.glob(f"**/Calib/{calib_name}"))
        if not matches:
            raise FileNotFoundError(f"calib not found: {calib_name}")
        calib_path = matches[0]
    xr = ET.parse(calib_path).getroot()
    raw = {child.tag: (child.text or "").strip() for child in xr}
    size = ann_root.find("size")
    width = int(size.findtext("width"))
    height = int(size.findtext("height"))
    return {
        "f": float(raw["f"]),
        "phi": float(raw["fi"]),
        "theta": float(raw["theta"]),
        "h": float(raw["h"]) / 1000.0,
        "width": width,
        "height": height,
        "cx": width / 2.0,
        "cy": height / 2.0,
        "calib_path": str(calib_path),
    }


def parse_objects(ann_path: Path) -> list[dict]:
    xr = ET.parse(ann_path).getroot()
    out = []
    for obj in xr.findall("object"):
        typ = (obj.findtext("type") or "").strip()
        bbox = numbers(obj.findtext("bbox2d") or "")
        v2 = numbers(obj.findtext("vertex2d") or "")
        v3 = numbers(obj.findtext("vertex3d") or "")
        dims = numbers(obj.findtext("veh_size") or "")
        if len(bbox) != 4 or len(v2) != 16 or len(v3) != 24 or len(dims) != 3:
            continue
        out.append({
            "class": typ,
            "bbox": bbox,
            "v2": np.array(v2, dtype=float).reshape(8, 2),
            "v3": np.array(v3, dtype=float).reshape(8, 3) / 1000.0,
            "dims": dims,
        })
    return out


def select_object(objects: list[dict], cls: str, bw: float, bh: float) -> dict:
    pool = [o for o in objects if o["class"] == cls]
    if not pool:
        raise ValueError(f"no {cls} object")
    def score(o):
        return abs(o["bbox"][2] - bw) + abs(o["bbox"][3] - bh)
    best = min(pool, key=score)
    if score(best) > 30:
        best = max(pool, key=lambda o: o["bbox"][2] * o["bbox"][3])
    return best


def load_case(spec: dict) -> dict:
    image_path, ann_path, root = find_asset(spec["scene"], spec["stem"])
    xr = ET.parse(ann_path).getroot()
    cam = parse_calib(root, xr)
    obj = select_object(parse_objects(ann_path), spec["cls"], spec["bw"], spec["bh"])
    x, y, w, h = obj["bbox"]
    bottom = obj["v3"][:4]
    cx = float(bottom[:, 0].mean())
    cy = float(bottom[:, 1].mean())
    lx = float(bottom[3, 0] - bottom[0, 0])
    ly = float(bottom[3, 1] - bottom[0, 1])
    ln = math.hypot(lx, ly)
    rn = math.hypot(cx, cy)
    cosang = abs((lx * cx + ly * cy) / (ln * rn)) if ln > 1e-9 and rn > 1e-9 else 0.0
    angle = math.degrees(math.acos(max(-1.0, min(1.0, cosang))))
    return {
        "spec": spec,
        "image_path": image_path,
        "ann_path": ann_path,
        "root": root,
        "cam": cam,
        "obj": obj,
        "bbox": obj["bbox"],
        "dist_m": rn,
        "angle_deg": angle,
        "W_preset": float(obj["dims"][1]),
    }


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def rotation(phi: float, theta: float) -> np.ndarray:
    return np.array([
        [math.cos(theta), -math.sin(theta), 0.0],
        [-math.sin(phi) * math.sin(theta), -math.sin(phi) * math.cos(theta), -math.cos(phi)],
        [math.cos(phi) * math.sin(theta), math.cos(phi) * math.cos(theta), -math.sin(phi)],
    ])


def project(points: np.ndarray, cam: dict) -> np.ndarray:
    R = rotation(cam["phi"], cam["theta"])
    Pc = (R @ (points - np.array([0.0, 0.0, cam["h"]])).T).T
    return np.stack([
        cam["f"] * Pc[:, 0] / Pc[:, 2] + cam["cx"],
        cam["f"] * Pc[:, 1] / Pc[:, 2] + cam["cy"],
    ], axis=1)


def ray_world(u: float, v: float, cam: dict) -> np.ndarray:
    R = rotation(cam["phi"], cam["theta"])
    d_c = np.array([(u - cam["cx"]) / cam["f"], (v - cam["cy"]) / cam["f"], 1.0])
    return R.T @ d_c


def backproject_ground(u: float, v: float, cam: dict) -> np.ndarray | None:
    d = ray_world(u, v, cam)
    if abs(d[2]) < 1e-9:
        return None
    t = -cam["h"] / d[2]
    if t <= 0:
        return None
    return np.array([0.0, 0.0, cam["h"]]) + t * d


def intersect_y(u: float, v: float, y_plane: float, cam: dict) -> np.ndarray | None:
    d = ray_world(u, v, cam)
    if abs(d[1]) < 1e-9:
        return None
    t = (y_plane - 0.0) / d[1]
    if t <= 0:
        return None
    return np.array([0.0, 0.0, cam["h"]]) + t * d


def visible_face(obj: dict, at_contact: bool = True) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (body_left, body_right, contact) in pixels for the visible end face.

    The 3D box order is bottom 0-3, top 4-7.  The two end faces are
    (0,1,4,5) and (2,3,6,7); the visible one is the one closer to the camera
    (smaller mean Y).

    at_contact=True uses the bottom edge (same row as the tire contact), which
    is what the formula needs.  at_contact=False uses the mid-height of the
    face, which is the fair comparison against a bbox/mask silhouette.
    """
    faces = [(0, 1, 4, 5), (2, 3, 6, 7)]
    face = min(faces, key=lambda f: float(obj["v3"][list(f), 1].mean()))
    pts = obj["v2"][list(face)]
    if at_contact:
        bottom = pts[np.argsort(pts[:, 1])[2:]]
        if bottom[0, 0] <= bottom[1, 0]:
            body_left, body_right = bottom[0], bottom[1]
        else:
            body_left, body_right = bottom[1], bottom[0]
    else:
        order = np.argsort(pts[:, 0])
        left = pts[order[:2]]
        right = pts[order[2:]]
        body_left = left.mean(axis=0)
        body_right = right.mean(axis=0)
    contact = (body_left + body_right) / 2.0
    return body_left, body_right, contact


# --------------------------------------------------------------------------
# candidates
# --------------------------------------------------------------------------

def draw_grid(img: np.ndarray, x0: int, y0: int, scale: float,
              step: int, label_step: int) -> None:
    h, w = img.shape[:2]
    color = (0, 180, 255)
    for gx in range(0, 10000, step):
        u = int(round((gx - x0) * scale))
        if 0 <= u < w:
            cv2.line(img, (u, 0), (u, h - 1), color, 1)
            if gx % label_step == 0:
                cv2.putText(img, str(gx), (u + 2, 14), cv2.FONT_HERSHEY_SIMPLEX,
                            0.38, (0, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(img, str(gx), (u + 2, 14), cv2.FONT_HERSHEY_SIMPLEX,
                            0.38, (255, 255, 255), 1, cv2.LINE_AA)
    for gy in range(0, 10000, step):
        v = int(round((gy - y0) * scale))
        if 0 <= v < h:
            cv2.line(img, (0, v), (w - 1, v), color, 1)
            if gy % label_step == 0:
                cv2.putText(img, str(gy), (2, v - 2 if v > 12 else v + 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(img, str(gy), (2, v - 2 if v > 12 else v + 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)


def save_crop(img: np.ndarray, bbox: tuple[float, float, float, float],
              out_path: Path, margin_x: float, margin_top: float,
              margin_bottom: float, max_side: int, step: int,
              label_step: int, draw_box: bool = True) -> None:
    x, y, w, h = bbox
    x1 = max(0, int(round(x - margin_x * w)))
    x2 = min(img.shape[1], int(round(x + w + margin_x * w)))
    y1 = max(0, int(round(y - margin_top * h)))
    y2 = min(img.shape[0], int(round(y + h + margin_bottom * h)))
    crop = img[y1:y2, x1:x2].copy()
    scale = min(1.0, max_side / max(crop.shape[:2]))
    if scale < 1.0:
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    if draw_box:
        bx1 = int(round((x - x1) * scale)); bx2 = int(round((x + w - x1) * scale))
        by1 = int(round((y - y1) * scale)); by2 = int(round((y + h - y1) * scale))
        cv2.rectangle(crop, (bx1, by1), (bx2, by2), (0, 255, 0), 2)
    draw_grid(crop, x1, y1, scale, step, label_step)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])


def cmd_candidates(args) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for spec in CANDIDATES:
        case = load_case(spec)
        x, y, w, h = case["bbox"]
        rows.append({
            "id": spec["id"],
            "scene": spec["scene"],
            "role": spec["role"],
            "class": spec["cls"],
            "stem": spec["stem"],
            "image": str(case["image_path"]),
            "annotation": str(case["ann_path"]),
            "calib": case["cam"]["calib_path"],
            "bbox_x": x, "bbox_y": y, "bbox_w": w, "bbox_h": h,
            "dist_m": round(case["dist_m"], 3),
            "angle_deg": round(case["angle_deg"], 3),
            "W_preset": round(case["W_preset"], 4),
            "width_px": case["cam"]["width"],
            "height_px": case["cam"]["height"],
            "f_px": case["cam"]["f"],
            "model": "",
            "W_spec": "",
            "spec_source": "",
            "spec_confidence": "",
        })
        img = cv2.imread(str(case["image_path"]))
        save_crop(img, case["bbox"], OUT / "crops" / f"{spec['id']}_tight.jpg",
                  0.15, 0.15, 0.15, 800, 25, 50)
        save_crop(img, case["bbox"], OUT / "crops" / f"{spec['id']}_context.jpg",
                  0.60, 0.40, 0.80, 1000, 50, 100)
        save_crop(img, case["bbox"], OUT / "crops" / f"{spec['id']}_full.jpg",
                  0.02, 0.02, 0.02, 1400, 100, 200)
        print(f"{spec['id']:24s} {spec['cls']:5s} d={case['dist_m']:5.1f}m "
              f"angle={case['angle_deg']:4.1f} W_preset={case['W_preset']:.2f}")

    path = OUT / "candidates.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {path} ({len(rows)} rows)")


# --------------------------------------------------------------------------
# simulate and eval
# --------------------------------------------------------------------------

def write_annotation_row(row: dict, path: Path) -> None:
    existing = []
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            existing = [r for r in csv.DictReader(fh) if r.get("id") != row["id"]]
    existing.append(row)
    existing.sort(key=lambda r: r["id"])
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ANN_FIELDS)
        writer.writeheader()
        for r in existing:
            writer.writerow({k: r.get(k, "") for k in ANN_FIELDS})


def cmd_simulate(args) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / ("annotations_sim.csv" if not args.out else args.out)
    if path.exists():
        path.unlink()
    rows = []
    for spec in CANDIDATES:
        case = load_case(spec)
        cam = case["cam"]
        body_left, body_right, contact = visible_face(case["obj"])
        ground = backproject_ground(float(contact[0]), float(contact[1]), cam)
        if ground is None:
            print(f"skip {spec['id']}: contact does not hit ground")
            continue
        xc, yc = float(ground[0]), float(ground[1])
        w = LANE_W[spec["scene"]]
        lane_world = np.array([[xc - w / 2.0, yc, 0.0],
                               [xc + w / 2.0, yc, 0.0]])
        lane_px = project(lane_world, cam)
        row = {
            "id": spec["id"],
            "scene": spec["scene"],
            "image": str(case["image_path"]),
            "class": spec["cls"],
            "model": "",
            "W_spec": f"{case['W_preset']:.4f}",
            "spec_source": "preset",
            "spec_confidence": "",
            "source": "sim_face",
            "body_left_u": f"{body_left[0]:.2f}", "body_left_v": f"{body_left[1]:.2f}",
            "body_right_u": f"{body_right[0]:.2f}", "body_right_v": f"{body_right[1]:.2f}",
            "lane_left_u": f"{lane_px[0, 0]:.2f}", "lane_left_v": f"{lane_px[0, 1]:.2f}",
            "lane_right_u": f"{lane_px[1, 0]:.2f}", "lane_right_v": f"{lane_px[1, 1]:.2f}",
            "contact_u": f"{contact[0]:.2f}", "contact_v": f"{contact[1]:.2f}",
            "notes": "simulated from SVLD vertex2d; not independent",
        }
        rows.append(row)
        print(f"{spec['id']:24s} face={np.linalg.norm(body_right-body_left):6.1f}px "
              f"lane={np.linalg.norm(lane_px[1]-lane_px[0]):6.1f}px")
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ANN_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in ANN_FIELDS})
    print(f"\nwrote {path} ({len(rows)} rows)")


def pct(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    return float(np.percentile(np.asarray(values, dtype=float), q))


def cmd_eval(args) -> None:
    ann_path = Path(args.ann)
    rows = list(csv.DictReader(ann_path.open(encoding="utf-8")))
    specs = {s["id"]: s for s in CANDIDATES}
    results = []
    overlays = OUT / "overlays"
    overlays.mkdir(parents=True, exist_ok=True)
    for row in rows:
        spec = specs.get(row["id"])
        if spec is None:
            print(f"unknown id: {row['id']}")
            continue
        try:
            case = load_case(spec)
            cam = case["cam"]
            bl = np.array([float(row["body_left_u"]), float(row["body_left_v"])])
            br = np.array([float(row["body_right_u"]), float(row["body_right_v"])])
            ll = np.array([float(row["lane_left_u"]), float(row["lane_left_v"])])
            lr = np.array([float(row["lane_right_u"]), float(row["lane_right_v"])])
            ct = np.array([float(row["contact_u"]), float(row["contact_v"])])
        except (ValueError, KeyError):
            print(f"bad row: {row['id']}")
            continue
        ground = backproject_ground(float(ct[0]), float(ct[1]), cam)
        if ground is None:
            print(f"contact misses ground: {row['id']}")
            continue
        y_plane = float(ground[1])
        p_left = intersect_y(float(bl[0]), float(bl[1]), y_plane, cam)
        p_right = intersect_y(float(br[0]), float(br[1]), y_plane, cam)
        if p_left is None or p_right is None:
            print(f"body edge misses plane: {row['id']}")
            continue
        W_meas = float(np.linalg.norm(p_left - p_right))
        V_px = float(np.linalg.norm(br - bl))
        L_px = float(np.linalg.norm(lr - ll))
        W_spec = float(row["W_spec"]) if row.get("W_spec") else case["W_preset"]
        w_formula = W_spec * L_px / V_px if V_px > 1e-9 else float("nan")
        gl = backproject_ground(float(ll[0]), float(ll[1]), cam)
        gr = backproject_ground(float(lr[0]), float(lr[1]), cam)
        w_ref = float(np.linalg.norm(gl - gr)) if gl is not None and gr is not None else float("nan")
        eW = abs(W_meas - W_spec) / W_spec * 100 if W_spec > 0 else float("nan")
        ew = abs(w_formula - w_ref) / w_ref * 100 if w_ref > 0 else float("nan")
        results.append({
            "id": row["id"], "scene": spec["scene"], "class": spec["cls"],
            "role": spec["role"], "source": row.get("source", ""),
            "spec_source": row.get("spec_source", ""),
            "dist_m": round(case["dist_m"], 3), "angle_deg": round(case["angle_deg"], 3),
            "W_preset": round(case["W_preset"], 4), "W_spec": round(W_spec, 4),
            "W_meas": round(W_meas, 4), "V_px": round(V_px, 2),
            "L_px": round(L_px, 2), "w_formula": round(w_formula, 4),
            "w_ref": round(w_ref, 4),
            "eW_pct": round(eW, 3), "ew_pct": round(ew, 3),
        })
        # overlay
        img = cv2.imread(str(case["image_path"]))
        for p, color, label in [
            (bl, (0, 255, 0), "body-L"), (br, (0, 255, 0), "body-R"),
            (ll, (255, 0, 0), "lane-L"), (lr, (255, 0, 0), "lane-R"),
            (ct, (0, 255, 255), "contact"),
        ]:
            cv2.circle(img, (int(round(p[0])), int(round(p[1]))), 4, color, -1)
            cv2.putText(img, label, (int(p[0]) + 5, int(p[1]) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
        cv2.line(img, tuple(np.round(bl).astype(int)), tuple(np.round(br).astype(int)), (0, 255, 0), 2)
        cv2.line(img, tuple(np.round(ll).astype(int)), tuple(np.round(lr).astype(int)), (255, 0, 0), 2)
        text = f"{row['id']}  eW={eW:.1f}%  ew={ew:.1f}%"
        cv2.putText(img, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imwrite(str(overlays / f"{row['id']}_{row.get('source','ann')}.jpg"), img,
                    [cv2.IMWRITE_JPEG_QUALITY, 90])

    if not results:
        print("no results")
        return
    out_csv = OUT / "results.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    groups = {}
    for r in results:
        for key in [("all", r["source"]), (r["scene"], r["source"]),
                    (r["class"], r["source"]), (r["role"], r["source"])]:
            groups.setdefault(key, []).append(r)
    summary = {}
    for key, vals in sorted(groups.items()):
        eW = [v["eW_pct"] for v in vals]
        ew = [v["ew_pct"] for v in vals]
        summary[f"{key[0]}/{key[1]}"] = {
            "n": len(vals),
            "eW_median_pct": round(statistics.median(eW), 3),
            "eW_p90_pct": round(pct(eW, 90), 3),
            "eW_pass3": sum(x < 3 for x in eW),
            "ew_median_pct": round(statistics.median(ew), 3),
            "ew_p90_pct": round(pct(ew, 90), 3),
            "ew_pass5": sum(x < 5 for x in ew),
        }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nwrote {out_csv} ({len(results)} rows)")
    for key in ("all/sim_face", "all/manual"):
        if key in summary:
            print(key, summary[key])
    print(f"wrote {OUT / 'summary.json'}")


# --------------------------------------------------------------------------
# manual clicker
# --------------------------------------------------------------------------

CLICK_LABELS = ["body-L", "body-R", "lane-L", "lane-R", "contact"]


def cmd_annotate(args) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    specs = {s["id"]: s for s in CANDIDATES}
    ids = args.ids.split(",") if args.ids else [s["id"] for s in CANDIDATES]
    ann_path = OUT / "annotations_manual.csv"
    existing = {}
    if ann_path.exists():
        with ann_path.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                existing[r["id"]] = r
    for cid in ids:
        cid = cid.strip()
        if cid not in specs:
            print(f"unknown id: {cid}")
            continue
        case = load_case(specs[cid])
        img = cv2.imread(str(case["image_path"]))
        scale = min(1.0, args.max_width / img.shape[1])
        view = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        points: list[tuple[float, float]] = []
        if cid in existing:
            r = existing[cid]
            mapping = {
                "body-L": ("body_left_u", "body_left_v"),
                "body-R": ("body_right_u", "body_right_v"),
                "lane-L": ("lane_left_u", "lane_left_v"),
                "lane-R": ("lane_right_u", "lane_right_v"),
                "contact": ("contact_u", "contact_v"),
            }
            for label in CLICK_LABELS:
                ku, kv = mapping[label]
                try:
                    points.append((float(r[ku]), float(r[kv])))
                except (KeyError, ValueError):
                    points = []
                    break
        state = {"points": points}

        def redraw():
            canvas = view.copy()
            for i, (u, v) in enumerate(state["points"]):
                p = (int(round(u * scale)), int(round(v * scale)))
                color = (0, 255, 0) if i < 2 else (255, 0, 0) if i < 4 else (0, 255, 255)
                cv2.circle(canvas, p, 5, color, -1)
                cv2.putText(canvas, CLICK_LABELS[i], (p[0] + 6, p[1] - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
            if len(state["points"]) >= 2:
                p = [(int(round(u * scale)), int(round(v * scale))) for u, v in state["points"][:2]]
                cv2.line(canvas, p[0], p[1], (0, 255, 0), 2)
            if len(state["points"]) >= 4:
                p = [(int(round(u * scale)), int(round(v * scale))) for u, v in state["points"][2:4]]
                cv2.line(canvas, p[0], p[1], (255, 0, 0), 2)
            cv2.putText(canvas, f"{cid}  clicks={len(state['points'])}/5  "
                                f"(u=undo, s=save, n=next, q=quit)",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(canvas, f"{cid}  clicks={len(state['points'])}/5  "
                                f"(u=undo, s=save, n=next, q=quit)",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(canvas, "body-L/R: contact row, no mirrors | lane-L/R: same row",
                        (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(canvas, "body-L/R: contact row, no mirrors | lane-L/R: same row",
                        (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow("vehicle-ruler", canvas)

        def on_mouse(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(state["points"]) < 5:
                state["points"].append((x / scale, y / scale))
                redraw()

        cv2.namedWindow("vehicle-ruler", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("vehicle-ruler", on_mouse)
        redraw()
        while True:
            key = cv2.waitKey(20) & 0xFF
            if key == ord("q"):
                cv2.destroyAllWindows()
                return
            if key == ord("u") and state["points"]:
                state["points"].pop()
                redraw()
            if key == ord("s") or key == ord("n"):
                if len(state["points"]) != 5:
                    print(f"{cid}: need 5 clicks, have {len(state['points'])}")
                    continue
                pts = state["points"]
                model = input(f"{cid} model (blank if unknown): ").strip()
                wspec = input(f"{cid} W_spec m (blank if unknown): ").strip()
                conf = input(f"{cid} confidence high/medium/low: ").strip()
                src = input(f"{cid} spec source/URL: ").strip()
                row = {
                    "id": cid, "scene": specs[cid]["scene"], "image": str(case["image_path"]),
                    "class": specs[cid]["cls"], "model": model, "W_spec": wspec,
                    "spec_source": src, "spec_confidence": conf, "source": "manual",
                    "body_left_u": f"{pts[0][0]:.2f}", "body_left_v": f"{pts[0][1]:.2f}",
                    "body_right_u": f"{pts[1][0]:.2f}", "body_right_v": f"{pts[1][1]:.2f}",
                    "lane_left_u": f"{pts[2][0]:.2f}", "lane_left_v": f"{pts[2][1]:.2f}",
                    "lane_right_u": f"{pts[3][0]:.2f}", "lane_right_v": f"{pts[3][1]:.2f}",
                    "contact_u": f"{pts[4][0]:.2f}", "contact_v": f"{pts[4][1]:.2f}",
                    "notes": "manual",
                }
                write_annotation_row(row, ann_path)
                print(f"saved {cid} -> {ann_path}")
                if key == ord("n"):
                    break
                redraw()
        cv2.destroyAllWindows()


# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("candidates")
    p.set_defaults(func=cmd_candidates)

    p = sub.add_parser("simulate")
    p.add_argument("--out", default="")
    p.set_defaults(func=cmd_simulate)

    p = sub.add_parser("eval")
    p.add_argument("--ann", default=str(OUT / "annotations_sim.csv"))
    p.set_defaults(func=cmd_eval)

    p = sub.add_parser("annotate")
    p.add_argument("--ids", default="")
    p.add_argument("--max-width", type=int, default=1400)
    p.set_defaults(func=cmd_annotate)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
