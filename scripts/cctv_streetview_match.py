#!/usr/bin/env python
"""Feasibility check: match a CCTV frame to KartaView street-level imagery.

This is the first step of the "street-level 3D localization" track.  It does not
reconstruct a 3D scene yet; it measures whether a fixed CCTV frame and the
nearby street-level photos share enough visual features to support a 2D-3D
match later.

Two things make KartaView awkward and are handled here:

* The public listing still exposes 2019-2020 Jakarta photos whose full-size
  files were purged from storage: ``imageProcUrl`` often answers HTTP 500 while
  ``imageLthUrl`` (large thumbnail) still works.  The script prefers the URL
  that actually serves bytes.
* Old flat photos carry no usable heading.  Spherical panoramas (``projection
  == SPHERE``) are reprojected to a perspective view and several headings are
  scanned, keeping the best match.

Example:
  py scripts/cctv_streetview_match.py ^
    --frame out/streetview-proto/frames/cawang_t60.png ^
    --lat -6.2466969 --lon 106.8786261 ^
    --radius 300 --pages 3 --max-images 8 --out out/streetview-proto
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

import cv2
import numpy as np

API = "https://api.kartaview.org/2.0/photo/"
UA = "Mozilla/5.0 (riset-carom streetview match)"
EARTH_R_M = 6371000.0


def _ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _get_json(url: str, timeout: int = 40):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
        return json.loads(r.read().decode("utf-8"))


def _download(url: str, path: Path, timeout: int = 90) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            path.write_bytes(r.read())
        return True
    except Exception:  # noqa: BLE001
        return False


def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2.0 * EARTH_R_M * math.asin(math.sqrt(a))


def list_photos(lat, lon, radius, pages):
    out = []
    for page in range(pages):
        q = urllib.parse.urlencode({"lat": f"{lat:.7f}", "lng": f"{lon:.7f}",
                                    "radius": radius, "page": page})
        try:
            d = _get_json(API + "?" + q)
        except Exception:  # noqa: BLE001
            break
        data = d.get("result", {}).get("data", [])
        if not data:
            break
        out.extend(data)
        time.sleep(0.3)
    return out


def pick_url(p):
    for key in ("imageLthUrl", "imageProcUrl", "imageThUrl"):
        if p.get(key):
            return p[key]
    return None


def reproject_equirect(pano, yaw_deg, fov_deg, out_w, out_h, pitch_deg=0.0):
    """Perspective crop from an equirectangular panorama.

    The panorama's own yaw reference is unknown, so callers scan headings.
    """
    h, w = pano.shape[:2]
    f = (out_w / 2.0) / math.tan(math.radians(fov_deg) / 2.0)
    xs, ys = np.meshgrid(np.arange(out_w), np.arange(out_h))
    # ray in camera frame (x right, y down, z forward)
    x = (xs - out_w / 2.0) / f
    y = (ys - out_h / 2.0) / f
    z = np.ones_like(x)
    # pitch about x axis
    cp, sp = math.cos(math.radians(pitch_deg)), math.sin(math.radians(pitch_deg))
    y2 = y * cp - z * sp
    z2 = y * sp + z * cp
    # yaw about y axis
    cy, sy = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    x3 = x * cy + z2 * sy
    z3 = -x * sy + z2 * cy
    lon = np.arctan2(x3, z3)
    lat = np.arctan2(-y2, np.sqrt(x3 ** 2 + z3 ** 2))
    u = ((lon / (2 * math.pi) + 0.5) * w).astype(np.int32) % w
    v = ((0.5 - lat / math.pi) * h).astype(np.int32).clip(0, h - 1)
    return pano[v, u]


def match_sift(frame, img, nfeatures=4000, ratio=0.75):
    sift = cv2.SIFT_create(nfeatures=nfeatures)
    kp1, des1 = sift.detectAndCompute(frame, None)
    kp2, des2 = sift.detectAndCompute(img, None)
    if des1 is None or des2 is None or len(kp1) < 8 or len(kp2) < 8:
        return dict(kp_frame=len(kp1 or []), kp_photo=len(kp2 or []),
                    good=0, inliers=0, kp1=kp1, kp2=kp2, good_list=[])
    bf = cv2.BFMatcher(cv2.NORM_L2)
    raw = bf.knnMatch(des1, des2, k=2)
    good = [m for m, n in (pair for pair in raw if len(pair) == 2) if m.distance < ratio * n.distance]
    inliers = 0
    if len(good) >= 4:
        src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        if mask is not None:
            inliers = int(mask.sum())
    return dict(kp_frame=len(kp1), kp_photo=len(kp2), good=len(good),
                inliers=inliers, kp1=kp1, kp2=kp2, good_list=good)


def match_loftr(frame, img):
    try:
        import torch
        from kornia.feature import LoFTR
    except Exception:  # noqa: BLE001
        return None
    def prep(im):
        h, w = im.shape[:2]
        s = 640.0 / max(h, w)
        im = cv2.resize(im, (int(round(w * s / 8)) * 8, int(round(h * s / 8)) * 8))
        t = torch.from_numpy(im.astype(np.float32) / 255.0)[None, None]
        return t
    matcher = LoFTR(pretrained="outdoor")
    t0, t1 = prep(frame), prep(img)
    with torch.no_grad():
        out = matcher({"image0": t0, "image1": t1})
    k0 = out["keypoints0"].numpy()
    k1 = out["keypoints1"].numpy()
    conf = out["confidence"].numpy()
    keep = conf > 0.5
    k0, k1 = k0[keep], k1[keep]
    inliers = 0
    if len(k0) >= 4:
        _, mask = cv2.findHomography(k0.reshape(-1, 1, 2), k1.reshape(-1, 1, 2),
                                     cv2.RANSAC, 5.0)
        if mask is not None:
            inliers = int(mask.sum())
    return dict(matches=int(len(k0)), inliers=inliers)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--radius", type=int, default=300)
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--max-images", type=int, default=8)
    ap.add_argument("--ids", default="", help="comma-separated KartaView photo ids to force")
    ap.add_argument("--matcher", choices=["sift", "loftr", "both"], default="sift")
    ap.add_argument("--headings", default="0,45,90,135,180,225,270,315")
    ap.add_argument("--fov", type=float, default=60.0)
    ap.add_argument("--out", default="out/streetview-proto")
    args = ap.parse_args()

    out = Path(args.out)
    img_dir = out / "kartaview"
    img_dir.mkdir(parents=True, exist_ok=True)

    frame = cv2.imread(args.frame, cv2.IMREAD_GRAYSCALE)
    if frame is None:
        raise SystemExit(f"cannot read frame {args.frame}")
    print(f"frame {frame.shape[1]}x{frame.shape[0]}")

    photos = list_photos(args.lat, args.lon, args.radius, args.pages)
    photos = [p for p in photos if pick_url(p)]
    if args.ids:
        wanted = {s.strip() for s in args.ids.split(",") if s.strip()}
        photos = [p for p in photos if str(p.get("id")) in wanted]
    photos.sort(key=lambda p: haversine_m(args.lat, args.lon,
                                          float(p.get("lat", "nan")),
                                          float(p.get("lng", "nan"))))
    photos = photos[: args.max_images]
    print(f"candidates {len(photos)}")

    headings = [float(h) for h in args.headings.split(",") if h.strip()]
    rows = []
    best = None
    for p in photos:
        pid = str(p.get("id", ""))
        dist = haversine_m(args.lat, args.lon, float(p.get("lat", "nan")),
                           float(p.get("lng", "nan")))
        proj = p.get("projection", "?")
        url = pick_url(p)
        suffix = Path(urllib.parse.urlparse(url).path).suffix or ".jpg"
        path = img_dir / f"{pid}{suffix}"
        if not path.exists() and not _download(url, path):
            rows.append(dict(id=pid, distance_m=round(dist, 1),
                             shot_date=(p.get("shotDate") or "")[:10],
                             projection=proj, heading="", inliers=0, good=0,
                             status="download_failed"))
            continue
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            rows.append(dict(id=pid, distance_m=round(dist, 1),
                             shot_date=(p.get("shotDate") or "")[:10],
                             projection=proj, heading="", inliers=0, good=0,
                             status="read_failed"))
            continue

        if proj == "SPHERE":
            candidates = [(f"yaw{h}", reproject_equirect(img, h, args.fov, 960, 540))
                          for h in headings]
        else:
            candidates = [("raw", img)]

        for label, cand in candidates:
            r = match_sift(frame, cand)
            if r["inliers"] > (best["inliers"] if best else -1):
                best = dict(id=pid, inliers=r["inliers"], label=label,
                            kp1=r["kp1"], kp2=r["kp2"], good=r["good_list"],
                            cand=cand, dist=dist, date=(p.get("shotDate") or "")[:10])
            rows.append(dict(id=pid, distance_m=round(dist, 1),
                             shot_date=(p.get("shotDate") or "")[:10],
                             projection=proj, heading=label,
                             inliers=r["inliers"], good=r["good"],
                             status="ok" if r["inliers"] >= 12 else
                                    ("weak" if r["inliers"] >= 4 else "fail")))
        time.sleep(0.2)

    rows.sort(key=lambda r: (-r["inliers"], r["distance_m"]))
    with (out / "match_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "distance_m", "shot_date",
                                           "projection", "heading", "good",
                                           "inliers", "status"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    summary = dict(frame=args.frame, query=dict(lat=args.lat, lon=args.lon,
                                                radius_m=args.radius),
                   n_candidates=len(rows), best_inliers=0, best_id=None,
                   best_heading=None, best_date=None, best_distance_m=None)
    if best:
        summary.update(best_inliers=best["inliers"], best_id=best["id"],
                       best_heading=best["label"], best_date=best["date"],
                       best_distance_m=round(best["dist"], 1))
        vis = cv2.drawMatches(frame, best["kp1"], best["cand"], best["kp2"],
                              best["good"][:80], None,
                              flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        cv2.imwrite(str(out / "best_match.png"), vis)
        cv2.imwrite(str(out / "best_candidate.png"), best["cand"])

    if args.matcher in ("loftr", "both") and best:
        lf = match_loftr(frame, best["cand"])
        summary["loftr"] = lf

    (out / "match_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
