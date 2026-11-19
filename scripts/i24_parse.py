#!/usr/bin/env python
"""Parse I24-3D ``sceneX_hg.json`` calibration files.

The released file is keyed by direction::

    {"EB": {"p1c1": {...}, ...}, "WB": {...}}

Each camera entry contains ``H``, ``H_inv``, ``P``, ``vps``, ``corr_pts``,
``space_pts`` and ``curve``.  ``P`` is **not** a calibrated camera matrix:
the official toolkit (``I24-3D-dataset/homography.py``) builds it as::

    P[:, 0] = H_inv[:, 0]
    P[:, 1] = H_inv[:, 1]
    P[:, 3] = H_inv[:, 2]
    P[:, 2] = [vps[2][0], vps[2][1], 1] * 0.01   # arbitrary scale

``Homography.scale_Z()`` is needed before ``P`` carries metric height.  As a
result, RQ-decomposing ``P`` does **not** recover physical ``fx/fy/cx/cy`` or
camera height.  The default output therefore reports only quantities that are
defined by the released data:

* ``ground_rms_px`` / ``ground_max_px`` -- ``H_inv(space_pts)`` vs ``corr_pts``
* ``horizon_line`` -- third row of ``H``, the image of the space plane's line
  at infinity (a projective invariant of ``H``)

Use ``--legacy-rq`` to also emit the old ``fx/fy/...`` block for diagnostics;
those values are not ground truth.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.linalg import rq

IMAGE_REFERENCE = (1920, 1080)
WORLD_UNIT = "feet"


def as_3x4(P) -> np.ndarray:
    P = np.asarray(P, dtype=float)
    if P.shape == (4, 3):
        P = P.T
    if P.shape != (3, 4):
        raise ValueError(f"P must be 3x4 or 4x3, got {P.shape}")
    return P


def decompose(P) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return K, R, t with P = K [R | t] (diagnostic only for I24-3D)."""
    P = as_3x4(P)
    M = P[:, :3]
    K, R = rq(M)

    signs = np.sign(np.diag(K))
    signs[signs == 0] = 1.0
    D = np.diag(signs)
    K = K @ D
    R = D @ R
    if abs(K[2, 2]) < 1e-12:
        raise ValueError("degenerate K: K[2,2] is zero")
    K = K / K[2, 2]

    if K[0, 0] < 0:
        K[:, 0] *= -1
        R[0, :] *= -1
    if K[1, 1] < 0:
        K[:, 1] *= -1
        R[1, :] *= -1

    t = np.linalg.solve(M, P[:, 3])
    return K, R, t


def camera_center(P) -> np.ndarray:
    P = as_3x4(P)
    return -np.linalg.solve(P[:, :3], P[:, 3])


def project(P, X) -> np.ndarray:
    """Project Nx3 world points (Z=0 allowed) to Nx2 pixels."""
    P = as_3x4(P)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[None, :]
    Xh = np.hstack([X, np.ones((X.shape[0], 1))])
    p = Xh @ P.T
    if np.any(np.abs(p[:, 2]) < 1e-12):
        raise ValueError("point projects to infinity")
    return p[:, :2] / p[:, 2:3]


def pose_from_R(R: np.ndarray) -> dict:
    """Pitch/roll/yaw in degrees from a world->camera rotation."""
    forward_world = R[2, :]
    right_world = R[0, :]
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, -forward_world[2]))))
    roll = math.degrees(math.asin(max(-1.0, min(1.0, right_world[2]))))
    yaw = math.degrees(math.atan2(forward_world[1], forward_world[0]))
    return {"pitch_deg": pitch, "roll_deg": roll, "yaw_deg": yaw}


def is_camera_entry(value) -> bool:
    return isinstance(value, dict) and "P" in value


def iter_calibrations(hg: dict):
    """Yield ``(direction, camera, entry)`` for flat and EB/WB files."""
    if not hg:
        raise ValueError("empty calibration file")
    if all(is_camera_entry(v) for v in hg.values()):
        for cam, entry in hg.items():
            yield None, cam, entry
        return
    for direction, cameras in hg.items():
        if not isinstance(cameras, dict):
            raise ValueError(f"unexpected top-level value for {direction!r}")
        for cam, entry in cameras.items():
            if not is_camera_entry(entry):
                raise ValueError(
                    f"unexpected entry {direction!r}/{cam!r}: missing 'P'"
                )
            yield direction, cam, entry


def ground_metrics(entry: dict) -> dict:
    """Metrics of the released ground-plane mapping (H_inv)."""
    H = np.asarray(entry["H"], dtype=float)
    H_inv = np.asarray(entry["H_inv"], dtype=float)
    if H.shape != (3, 3) or H_inv.shape != (3, 3):
        raise ValueError(f"H/H_inv must be 3x3, got {H.shape}/{H_inv.shape}")

    P = as_3x4(entry["P"])
    space = np.asarray(entry["space_pts"], dtype=float)
    corr = np.asarray(entry["corr_pts"], dtype=float)
    if space.shape[1] == 2:
        space_xyz = np.hstack([space, np.zeros((space.shape[0], 1))])
    else:
        space_xyz = space
    pred = project(P, space_xyz)
    err = np.linalg.norm(pred - corr, axis=1)

    # Third row of H is the image of the space plane's line at infinity.
    line = H[2, :]
    norm = math.hypot(float(line[0]), float(line[1]))
    horizon = (line / norm).tolist() if norm > 0 else line.tolist()

    return {
        "n_corr": int(corr.shape[0]),
        "ground_rms_px": round(float(np.sqrt(np.mean(err**2))), 4),
        "ground_max_px": round(float(np.max(err)), 4),
        "horizon_line": [round(float(x), 8) for x in horizon],
        "curve": [float(x) for x in entry.get("curve", [])],
        "vps": [[float(x) for x in vp] for vp in entry.get("vps", [])],
        "P_z_column": [round(float(x), 8) for x in P[:, 2]],
    }


def legacy_rq(entry: dict) -> dict:
    """Old RQ(P) block, kept only for diagnostics."""
    P = as_3x4(entry["P"])
    K, R, t = decompose(P)
    C = camera_center(P)
    _ = t
    return {
        "fx": round(float(K[0, 0]), 4),
        "fy": round(float(K[1, 1]), 4),
        "cx": round(float(K[0, 2]), 4),
        "cy": round(float(K[1, 2]), 4),
        "camera_center_world": [round(float(x), 4) for x in C],
        **{k: round(v, 4) for k, v in pose_from_R(R).items()},
        "rq_warning": (
            "RQ(P) is not physical: P[:,2] is a vertical-VP column with an "
            "arbitrary 0.01 scale. Do not use as ground truth."
        ),
    }


def self_test() -> None:
    """Synthetic camera: Z up, yaw 20 deg, pitch 10 deg, f 1000 px, h 8 m."""
    f, cx, cy = 1000.0, 960.0, 540.0
    theta = math.radians(10.0)
    psi = math.radians(20.0)
    height = 8.0

    K = np.array([[f, 0.0, cx], [0.0, f, cy], [0.0, 0.0, 1.0]])
    forward = np.array([
        math.cos(theta) * math.cos(psi),
        math.cos(theta) * math.sin(psi),
        -math.sin(theta),
    ])
    right = np.array([math.sin(psi), -math.cos(psi), 0.0])
    down = np.cross(forward, right)
    R = np.vstack([right, down, forward])
    C = np.array([0.0, 0.0, height])
    t = -R @ C
    P = K @ np.hstack([R, t[:, None]])

    X = np.array([
        [10.0, -3.0, 0.0],
        [20.0, 0.0, 0.0],
        [30.0, 3.0, 0.0],
        [40.0, -1.0, 0.0],
    ])
    uv = project(P, X)

    for shape_name, P_in in (("3x4", P), ("4x3", P.T)):
        K_out, _, _ = decompose(P_in)
        assert abs(K_out[0, 0] - f) < 1e-6, (shape_name, K_out)
        assert abs(K_out[1, 1] - f) < 1e-6, (shape_name, K_out)
        assert abs(K_out[0, 2] - cx) < 1e-6, (shape_name, K_out)
        assert abs(K_out[1, 2] - cy) < 1e-6, (shape_name, K_out)
        print(f"{shape_name}: OK  f={K_out[0, 0]:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hg", help="path to sceneX_hg.json")
    ap.add_argument("--out", help="output JSON")
    ap.add_argument("--direction", choices=["EB", "WB"],
                    help="write only this direction")
    ap.add_argument("--legacy-rq", action="store_true",
                    help="also emit the non-physical RQ(P) block")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return
    if not args.hg:
        ap.error("--hg or --self-test is required")

    path = Path(args.hg)
    hg = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = list(iter_calibrations(hg))
    nested = any(direction is not None for direction, _, _ in rows)

    directions: dict[str, dict] = {}
    flat: dict[str, dict] = {}
    for direction, cam, entry in rows:
        if args.direction and direction != args.direction:
            continue
        item = ground_metrics(entry)
        if args.legacy_rq:
            item["legacy_rq"] = legacy_rq(entry)
        if nested:
            directions.setdefault(direction, {})[cam] = item
        else:
            flat[cam] = item

    if not directions and not flat:
        raise SystemExit(f"no calibration for direction {args.direction!r}")

    rms = [
        item["ground_rms_px"]
        for group in ([*directions.values()] if nested else [flat])
        for item in group.values()
    ]
    summary = {
        "n_calibrations": len(rms),
        "ground_rms_median_px": round(float(np.median(rms)), 4) if rms else None,
        "ground_rms_max_px": round(float(np.max(rms)), 4) if rms else None,
        "pass_1px": int(sum(v < 1.0 for v in rms)),
        "pass_5px": int(sum(v < 5.0 for v in rms)),
    }

    doc = {
        "source": str(path),
        "format": "direction" if nested else "flat",
        "units": {"world": WORLD_UNIT, "image_reference": IMAGE_REFERENCE},
        "notes": [
            "P[:,2] is a vertical-VP column scaled by an arbitrary 0.01; "
            "RQ(P) is not a physical calibration (see I24-3D homography.py).",
            "ground_rms_px is H_inv(space_pts) vs corr_pts in the released "
            "road-aligned space frame.",
            "I24-3D hg does not provide fx/fy/height ground truth.",
        ],
        "summary": summary,
    }
    if nested:
        doc["directions"] = directions
    else:
        doc["calibrations"] = flat

    text = json.dumps(doc, indent=2, ensure_ascii=False)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        counts = ", ".join(
            f"{d}={len(cams)}" for d, cams in directions.items()
        ) if nested else f"flat={len(flat)}"
        print(f"wrote {out} ({summary['n_calibrations']} calibrations: {counts})")
        print(
            "ground RMS px: median={ground_rms_median_px} "
            "max={ground_rms_max_px}; <1px {pass_1px}/{n_calibrations}, "
            "<5px {pass_5px}/{n_calibrations}".format(**summary)
        )
    else:
        print(text)


if __name__ == "__main__":
    main()
