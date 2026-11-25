#!/usr/bin/env python
"""Two-orthogonal-VP focal length on SVLD: road VP + vertical VP.

The road VP comes from lane markings (`lane_vp`).  The vertical VP is detected
from near-vertical image lines (poles, buildings, signposts), excluding lines
that pass through the road VP (lane markings).  With principal point centered,
two orthogonal VPs give:

    f^2 = -(u_r-cx)(u_v-cx) - (v_r-cy)(v_v-cy)

A GeoCalib gravity check is recorded but not required for the fit.

Example:
  py scripts/svld_vertical_vp.py --scene 0cam --out out/svld_vertical_vp
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

BACKEND = Path(r"D:\Kerjaan\LearnPinhole\backend")


def line_eq(x1, y1, x2, y2):
    a = y1 - y2
    b = x2 - x1
    c = x1 * y2 - x2 * y1
    n = math.hypot(a, b)
    if n < 1e-9:
        return None
    return a / n, b / n, c / n


def intersect(l1, l2):
    a1, b1, c1 = l1
    a2, b2, c2 = l2
    det = a1 * b2 - a2 * b1
    if abs(det) < 1e-9:
        return None
    u = (b1 * c2 - b2 * c1) / det
    v = (c1 * a2 - c2 * a1) / det
    if not (math.isfinite(u) and math.isfinite(v)):
        return None
    return u, v


def dist_line(eq, u, v):
    return abs(eq[0] * u + eq[1] * v + eq[2])


def detect_vertical_lines(image):
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
    found = lsd.detect(gray)[0]
    segs = []
    if found is None:
        return segs
    for row in np.asarray(found).reshape(-1, 4):
        x1, y1, x2, y2 = (float(v) for v in row)
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < max(24.0, 0.055 * h):
            continue
        if abs(dx) > 0.35 * abs(dy):
            continue
        eq = line_eq(x1, y1, x2, y2)
        if eq is None:
            continue
        segs.append((x1, y1, x2, y2, length, eq))
    segs.sort(key=lambda s: s[4], reverse=True)
    return segs[:80]


def refine(segs, u, v):
    for _ in range(4):
        a = np.array([s[5][0] for s in segs])
        b = np.array([s[5][1] for s in segs])
        c = np.array([s[5][2] for s in segs])
        weight = np.array([s[4] for s in segs])
        m00 = float((weight * a * a).sum())
        m01 = float((weight * a * b).sum())
        m11 = float((weight * b * b).sum())
        r0 = float(-(weight * a * c).sum())
        r1 = float(-(weight * b * c).sum())
        det = m00 * m11 - m01 * m01
        if abs(det) < 1e-9:
            break
        u = (r0 * m11 - r1 * m01) / det
        v = (m00 * r1 - m01 * r0) / det
    return u, v


def ransac_vertical(segs, w, h, road_u, road_v, tol=3.0):
    # remove lane markings: their line passes through the road VP
    cand = [s for s in segs if dist_line(s[5], road_u, road_v) > 5.0]
    if len(cand) < 3:
        return None
    pairs = []
    top = cand[:40]
    for i in range(len(top)):
        for j in range(i + 1, len(top)):
            pairs.append((top[i], top[j]))
    rng = np.random.default_rng(13)
    for _ in range(600):
        i, j = rng.choice(len(cand), 2, replace=False)
        pairs.append((cand[int(i)], cand[int(j)]))

    best = None
    limit = 8.0 * max(w, h)
    for s1, s2 in pairs:
        p = intersect(s1[5], s2[5])
        if p is None:
            continue
        u, v = p
        if not (-limit <= u <= limit and -limit <= v <= limit):
            continue
        # vertical VP from a downward camera is below the image; allow above for others
        inliers = [s for s in cand if dist_line(s[5], u, v) < tol]
        if len(inliers) < 4:
            continue
        score = sum(s[4] for s in inliers)
        if best is None or score > best[0]:
            best = (score, u, v, inliers)
    if best is None:
        return None
    _, u, v, inliers = best
    u, v = refine(inliers, u, v)
    inliers = [s for s in cand if dist_line(s[5], u, v) < tol]
    if len(inliers) < 4:
        return None
    rms = float(np.sqrt(np.mean([dist_line(s[5], u, v) ** 2 for s in inliers])))
    return {
        "u": float(u),
        "v": float(v),
        "inliers": len(inliers),
        "total": len(cand),
        "rms": rms,
        "length": float(sum(s[4] for s in inliers)),
    }


def gravity_vector(pitch_deg, roll_deg):
    # R = Rroll * Rpitch * Ryaw (vp_pose convention), gravity = R @ [0,0,-1]
    p = math.radians(pitch_deg)
    r = math.radians(roll_deg)
    cp, sp = math.cos(p), math.sin(p)
    cr, sr = math.cos(r), math.sin(r)
    # R rows for yaw=0
    gx = sr * cp
    gy = -cr * cp
    gz = sp
    return gx, gy, gz


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="out/svld_geocalib/manifest.csv")
    ap.add_argument("--geo", default="out/svld_geocalib/geocalib_single.json")
    ap.add_argument("--backend", default=str(BACKEND))
    ap.add_argument("--scene", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default="out/svld_vertical_vp")
    args = ap.parse_args()

    sys.path.insert(0, args.backend)
    from app.lane_vp import detect_lane_vp

    manifest = list(csv.DictReader(Path(args.manifest).open(encoding="utf-8")))
    if args.scene:
        manifest = [r for r in manifest if r["scene"] == args.scene]
    if args.limit:
        manifest = manifest[: args.limit]
    geo = {}
    if Path(args.geo).exists():
        geo = {
            Path(r["image"]).name: r
            for r in json.loads(Path(args.geo).read_text(encoding="utf-8-sig"))
            if "error" not in r
        }

    rows = []
    for item in manifest:
        image = cv2.imread(item["source"])
        if image is None:
            continue
        h, w = image.shape[:2]
        road = detect_lane_vp(image, prior_focal=1.2 * w)
        row = {
            "split": item["split"],
            "scene": item["scene"],
            "image": item["image"],
            "lane_w": "",
        }
        if not road.ok:
            row.update({"status": "NO_ROAD_VP", "reason": road.reason})
            rows.append(row)
            continue
        vp = ransac_vertical(
            detect_vertical_lines(image), w, h, road.u, road.v
        )
        if vp is None:
            row.update({"status": "NO_VERTICAL_VP"})
            rows.append(row)
            continue
        cx, cy = w / 2, h / 2
        f2 = -(road.u - cx) * (vp["u"] - cx) - (road.v - cy) * (vp["v"] - cy)
        if f2 <= 0 or not math.isfinite(f2):
            row.update({"status": "F_BAD", "vert_u": vp["u"], "vert_v": vp["v"],
                        "inliers": vp["inliers"], "rms": vp["rms"]})
            rows.append(row)
            continue
        f_est = math.sqrt(f2)
        f_gt = float(item["f_px"])
        df = abs(f_est - f_gt) / f_gt
        angle = ""
        g = geo.get(item["image"])
        if g:
            gx, gy, gz = gravity_vector(-float(g["pitch_deg"]), float(g["roll_deg"]))
            # vertical direction from VP: K^-1 [u,v,1]
            dv = np.array([(vp["u"] - cx) / f_est, (vp["v"] - cy) / f_est, 1.0])
            dv /= np.linalg.norm(dv)
            gv = np.array([gx, gy, gz])
            gv /= np.linalg.norm(gv)
            angle = round(math.degrees(math.acos(min(1.0, abs(float(dv @ gv))))), 2)
        row.update({
            "status": "OK" if (vp["rms"] <= 3.0 and vp["inliers"] >= 4) else "VP_WEAK",
            "road_u": road.u, "road_v": road.v,
            "vert_u": round(vp["u"], 2), "vert_v": round(vp["v"], 2),
            "inliers": vp["inliers"], "rms": round(vp["rms"], 3),
            "f_est": round(f_est, 2), "f_gt": f_gt,
            "df_pct": round(df * 100, 3),
            "gravity_angle_deg": angle,
        })
        rows.append(row)
        print(
            f"{item['split']:8s} {item['scene']:18s} {item['image']:28s} "
            f"f {f_gt:.0f}->{f_est:.0f} ({df*100:5.1f}%) "
            f"vVP=({vp['u']:.0f},{vp['v']:.0f}) in={vp['inliers']} "
            f"rms={vp['rms']:.2f} grav={angle}"
        )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for row in rows for k in row})
    with (out / "vertical_vp.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    groups = defaultdict(list)
    for row in rows:
        if row["status"] == "OK":
            groups[(row["split"], row["scene"])].append(row)
            groups[(row["split"], "*")].append(row)
            groups[("*", "*")].append(row)
    summary = {}
    for group, items in sorted(groups.items()):
        vals = sorted(r["df_pct"] for r in items)
        summary[f"{group[0]}/{group[1]}"] = {
            "n_ok": len(vals),
            "median_pct": round(statistics.median(vals), 2),
            "p90_pct": round(vals[min(len(vals) - 1, round((len(vals) - 1) * 0.9))], 2),
            "pass_5pct": sum(v < 5 for v in vals),
        }
    (out / "vertical_vp_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"\nwrote {out / 'vertical_vp.csv'}")
    for group, s in summary.items():
        print(f"  {group:24s} n_ok={s['n_ok']:3d} median={s['median_pct']:5.1f}% pass5={s['pass_5pct']}/{s['n_ok']}")


if __name__ == "__main__":
    main()
