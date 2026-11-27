#!/usr/bin/env python
"""Check KartaView street-level coverage around provisional CCTV coordinates.

For each camera coordinate produced by ``cctv_geolocate.py``, query the public
KartaView API for nearby street-level photos.  The nearest photo is a practical
proxy for whether the site has enough street-level imagery for a
street-view-based 3D reconstruction and camera localization.

The KartaView public endpoint is keyless:
  https://api.kartaview.org/2.0/photo/?lat=..&lng=..&radius=..

Example:
  py scripts/cctv_streetview_check.py `
    --cameras out/cctv-geolocate/cameras_dalam_kota.csv `
    --out out/cctv-geolocate --radius 300 --download-thumbs
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

API = "https://api.kartaview.org/2.0/photo/"
UA = "Mozilla/5.0 (riset-carom calibration coverage check)"
EARTH_R_M = 6_371_008.8


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in metres between two WGS84 points."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2.0 * EARTH_R_M * math.asin(math.sqrt(a))


def _context() -> ssl.SSLContext:
    # The public KartaView endpoint presents a chain that Python's default
    # store rejects on this machine; coverage checking is read-only and public.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _get_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_context()) as r:
        return json.loads(r.read().decode("utf-8"))


def _download(url: str, path: Path, timeout: int = 60) -> bool:
    if not url:
        return False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=_context()) as r:
            path.write_bytes(r.read())
        return True
    except Exception:
        return False


def _probe(url: str, timeout: int = 20) -> bool:
    """Return True when the image URL actually serves bytes.

    KartaView still lists old 2019-2020 Jakarta photos whose files were
    purged from storage; the CDN then answers HTTP 500.  A listing hit is
    not the same as usable imagery, so probe before claiming coverage.
    """
    if not url:
        return False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=_context()) as r:
            return bool(r.read(64))
    except Exception:
        return False


def nearby(lat: float, lon: float, radius: int, page: int = 0) -> list[dict]:
    q = urllib.parse.urlencode({
        "lat": f"{lat:.7f}", "lng": f"{lon:.7f}",
        "radius": radius, "page": page,
    })
    data = _get_json(f"{API}?{q}")
    return data.get("result", {}).get("data", []) or []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cameras", default="out/cctv-geolocate/cameras_dalam_kota.csv")
    ap.add_argument("--out", default="out/cctv-geolocate")
    ap.add_argument("--radius", type=int, default=300)
    ap.add_argument("--max-pages", type=int, default=1)
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--download-thumbs", action="store_true")
    ap.add_argument("--thumb-limit", type=int, default=0,
                    help="0 = download every nearest thumb")
    ap.add_argument("--usable-tries", type=int, default=6,
                    help="probe up to N nearest photos until one image downloads")
    args = ap.parse_args()

    rows = list(csv.DictReader(Path(args.cameras).open(encoding="utf-8")))
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir = out_dir / "thumbs"
    if args.download_thumbs:
        thumb_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, r in enumerate(rows):
        lon = r.get("final_lon", "")
        lat = r.get("final_lat", "")
        base = {
            "id": r.get("id", ""),
            "name": r.get("name", ""),
            "highway_id": r.get("highway_id", ""),
            "km": r.get("km", ""),
            "side": r.get("side", ""),
            "lon": lon,
            "lat": lat,
            "coord_source": r.get("coord_source", ""),
        }
        if lon == "" or lat == "":
            results.append({**base, "n_photos": 0, "nearest_m": "",
                            "nearest_date": "", "nearest_sequence": "",
                            "nearest_image": "", "coverage": "no_coordinate"})
            continue

        photos: list[dict] = []
        try:
            for page in range(args.max_pages):
                batch = nearby(float(lat), float(lon), args.radius, page)
                photos.extend(batch)
                if len(batch) == 0:
                    break
                time.sleep(args.delay)
        except Exception as exc:  # noqa: BLE001 - report and continue
            results.append({**base, "n_photos": 0, "nearest_m": "",
                            "nearest_date": "", "nearest_sequence": "",
                            "nearest_image": "", "coverage": f"error:{type(exc).__name__}"})
            continue

        if not photos:
            results.append({**base, "n_photos": 0, "nearest_m": "",
                            "nearest_date": "", "nearest_sequence": "",
                            "nearest_image": "", "coverage": "none"})
            continue

        def dist(p: dict) -> float:
            # The public API's "distance" field is not the distance from the
            # query point (it is often 0 for the first photo), so compute the
            # great-circle distance from the photo's own coordinates instead.
            try:
                plat = float(p.get("lat"))
                plon = float(p.get("lng"))
            except (TypeError, ValueError):
                return float("inf")
            return haversine_m(float(lat), float(lon), plat, plon)

        ordered = sorted(photos, key=dist)
        best = ordered[0]
        nearest = dist(best)
        # The CDN wrapper (imageThUrl) is the URL that actually serves bytes;
        # the raw storage URL behind it is often unreachable from here.
        image = best.get("imageThUrl") or best.get("imageProcUrl") or ""

        usable = None
        usable_m = ""
        # Old 2019-2020 Jakarta uploads are purged from KartaView storage, so
        # the nearest photo is often unusable.  Probe the nearest few *and*
        # the most recent few, then keep the first that actually serves bytes.
        nearest_n = ordered[:max(1, args.usable_tries)]
        newest_n = sorted(photos, key=lambda p: (p.get("shotDate") or ""),
                          reverse=True)[:max(1, args.usable_tries)]
        seen: set = set()
        candidates = []
        for cand in nearest_n + newest_n:
            cid = cand.get("id")
            if cid in seen:
                continue
            seen.add(cid)
            candidates.append(cand)
        for cand in candidates:
            url = cand.get("imageThUrl") or cand.get("imageProcUrl") or ""
            if _probe(url):
                usable = cand
                usable_m = round(dist(cand), 1)
                break

        rec = {
            **base,
            "n_photos": len(photos),
            "nearest_m": round(nearest, 1),
            "nearest_date": (best.get("shotDate") or "")[:10],
            "nearest_sequence": best.get("sequenceId", ""),
            "nearest_image": image,
            "nearest_cdn": best.get("imageThUrl") or best.get("imageProcUrl") or "",
            "usable": "yes" if usable else "no",
            "usable_m": usable_m,
            "usable_date": (usable.get("shotDate") or "")[:10] if usable else "",
            "usable_id": usable.get("id", "") if usable else "",
            "usable_projection": usable.get("projection", "") if usable else "",
            "coverage": "yes" if usable else "listing_only",
        }
        results.append(rec)

        if args.download_thumbs and image:
            if args.thumb_limit and i >= args.thumb_limit:
                pass
            else:
                suffix = Path(urllib.parse.urlparse(image).path).suffix or ".jpg"
                safe = "".join(ch if ch.isalnum() or ch in "-_" else "_"
                               for ch in (r.get("id") or f"cam{i}"))
                _download(image, thumb_dir / f"{safe}{suffix}")

        time.sleep(args.delay)

    fields = ["id", "name", "highway_id", "km", "side", "lon", "lat",
              "coord_source", "n_photos", "nearest_m", "nearest_date",
              "nearest_sequence", "nearest_image", "nearest_cdn",
              "usable", "usable_m", "usable_date", "usable_id",
              "usable_projection", "coverage"]
    with (out_dir / "streetview_coverage.csv").open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    n = len(results)
    yes = sum(r["coverage"] == "yes" for r in results)
    listing = sum(r["coverage"] == "listing_only" for r in results)
    none = sum(r["coverage"] == "none" for r in results)
    err = sum(str(r["coverage"]).startswith("error") for r in results)
    with_cov = [r for r in results if r["coverage"] == "yes"]
    med = sorted(r["usable_m"] for r in with_cov)
    summary = {
        "n_cameras": n,
        "coverage_yes": yes,
        "coverage_listing_only": listing,
        "coverage_none": none,
        "coverage_error": err,
        "radius_m": args.radius,
        "usable_m_median": (round(med[len(med) // 2], 1) if med else None),
        "usable_m_max": (round(max(med), 1) if med else None),
    }
    (out_dir / "streetview_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{n} cameras; usable imagery {yes}, listing only {listing}, "
          f"none {none}, error {err}")
    if med:
        print(f"  usable photo: median {summary['usable_m_median']} m, "
              f"max {summary['usable_m_max']} m")
    print(f"wrote {out_dir / 'streetview_coverage.csv'}")


if __name__ == "__main__":
    main()
