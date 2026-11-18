#!/usr/bin/env python
"""Parse I24-3D sceneX_hg.json into camera intrinsics/extrinsics.

The dataset README writes P as [4,3], while the standard projection matrix is
3x4. This script accepts either shape and normalises it. Run --self-test first
to verify the conventions without the real dataset.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.linalg import rq


def as_3x4(P) -> np.ndarray:
    P = np.asarray(P, dtype=float)
    if P.shape == (4, 3):
        P = P.T
    if P.shape != (3, 4):
        raise ValueError(f"P must be 3x4 or 4x3, got {P.shape}")
    return P


def decompose(P) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return K, R, t with P = K [R | t]."""
    P = as_3x4(P)
    M = P[:, :3]
    K, R = rq(M)

    # Make the diagonal of K positive, then normalise K[2, 2] = 1.
    signs = np.sign(np.diag(K))
    signs[signs == 0] = 1.0
    D = np.diag(signs)
    K = K @ D
    R = D @ R
    if abs(K[2, 2]) < 1e-12:
        raise ValueError("degenerate K: K[2,2] is zero")
    K = K / K[2, 2]

    # A valid pinhole camera has positive focal lengths.
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


def parse_camera(entry: dict) -> dict:
    P = as_3x4(entry["P"])
    K, R, t = decompose(P)
    C = camera_center(P)
    pose = pose_from_R(R)

    out = {
        "fx": float(K[0, 0]),
        "fy": float(K[1, 1]),
        "cx": float(K[0, 2]),
        "cy": float(K[1, 2]),
        "height_m": float(C[2]),
        "camera_center": [float(x) for x in C],
        **pose,
    }

    # Optional round-trip check against the labelled correspondences.
    if "space_pts" in entry and "corr_pts" in entry:
        space = np.asarray(entry["space_pts"], dtype=float)
        corr = np.asarray(entry["corr_pts"], dtype=float)
        if space.shape[1] == 2:
            space = np.hstack([space, np.zeros((space.shape[0], 1))])
        pred = project(P, space)
        err = np.linalg.norm(pred - corr, axis=1)
        out["roundtrip_rms_px"] = float(np.sqrt(np.mean(err**2)))
        out["roundtrip_max_px"] = float(np.max(err))

    return out


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

    # Points on the road plane, in front of the camera.
    X = np.array([
        [10.0, -3.0, 0.0],
        [20.0, 0.0, 0.0],
        [30.0, 3.0, 0.0],
        [40.0, -1.0, 0.0],
    ])
    uv = project(P, X)

    for shape_name, P_in in (("3x4", P), ("4x3", P.T)):
        parsed = parse_camera({"P": P_in.tolist(),
                               "space_pts": X[:, :2].tolist(),
                               "corr_pts": uv.tolist()})
        assert abs(parsed["fx"] - f) < 1e-6, (shape_name, parsed)
        assert abs(parsed["fy"] - f) < 1e-6, (shape_name, parsed)
        assert abs(parsed["cx"] - cx) < 1e-6, (shape_name, parsed)
        assert abs(parsed["cy"] - cy) < 1e-6, (shape_name, parsed)
        assert abs(parsed["height_m"] - height) < 1e-6, (shape_name, parsed)
        assert abs(parsed["pitch_deg"] - 10.0) < 1e-6, (shape_name, parsed)
        assert abs(parsed["yaw_deg"] - 20.0) < 1e-6, (shape_name, parsed)
        assert parsed["roundtrip_rms_px"] < 1e-9, (shape_name, parsed)
        print(f"{shape_name}: OK  f={parsed['fx']:.3f}  "
              f"pitch={parsed['pitch_deg']:.3f}  h={parsed['height_m']:.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hg", help="path to sceneX_hg.json")
    ap.add_argument("--out", help="output JSON")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return
    if not args.hg:
        ap.error("--hg or --self-test is required")

    hg = json.loads(Path(args.hg).read_text(encoding="utf-8-sig"))
    parsed = {cam: parse_camera(entry) for cam, entry in hg.items()}
    text = json.dumps(parsed, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out} ({len(parsed)} cameras)")
    else:
        print(text)


if __name__ == "__main__":
    main()
