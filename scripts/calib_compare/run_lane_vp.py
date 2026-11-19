#!/usr/bin/env python
"""Run LearnPinhole lane_vp.detect_lane_vp on a folder of frames."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--backend", default=r"D:\Kerjaan\LearnPinhole\backend",
                    help="Path to LearnPinhole/backend")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.path.insert(0, args.backend)
    from app.lane_vp import detect_lane_vp
    rows = []
    for path in sorted(Path(args.folder).glob("*.png")):
        frame = cv2.imread(str(path))
        h, w = frame.shape[:2]
        result = detect_lane_vp(frame, prior_focal=0.703125 * w)
        rows.append({
            "frame": path.name,
            "ok": bool(result.ok),
            "u": float(result.u),
            "v": float(result.v),
            "inliers": int(result.inliers),
            "total": int(result.total),
            "rms": float(result.rms),
            "reason": result.reason,
            "segments": [
                {"x1": s.x1, "y1": s.y1, "x2": s.x2, "y2": s.y2,
                 "length": s.length, "white": s.white}
                for s in result.segments
            ],
        })
    ok = [r for r in rows if r["ok"] and r["inliers"] >= 4 and r["rms"] <= 3.0]
    summary = {
        "n_frames": len(rows),
        "n_ok": len(ok),
        "median_u": float(np.median([r["u"] for r in ok])) if ok else None,
        "median_v": float(np.median([r["v"] for r in ok])) if ok else None,
        "median_inliers": float(np.median([r["inliers"] for r in ok])) if ok else None,
        "median_rms": float(np.median([r["rms"] for r in ok])) if ok else None,
        "frames": rows,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "frames"}, indent=2))
    for r in rows:
        print(r["frame"], "ok" if r["ok"] else "FAIL", f"u={r['u']:.1f}", f"v={r['v']:.1f}", f"in={r['inliers']}", f"rms={r['rms']:.2f}", r["reason"])


if __name__ == "__main__":
    main()
