#!/usr/bin/env python
"""Derive provisional CCTV coordinates from public Bina Marga metadata.

The public Bina Marga camera pages expose camera labels, KM stationing, and
A/B direction, but not surveyed coordinates.  This script joins that metadata
to an OpenStreetMap road centreline and interpolates a coordinate at the
recorded KM.  The result is a *provisional* location, accurate to tens of
metres -- enough to retrieve street-level panoramas, not a surveyed coordinate.

Inputs are the public camera JSON and highway GeoJSON maintained by the
CCTV-Jakarta project (https://github.com/SkyUnik/CCTV-Jakarta), which in turn
scrapes the public Bina Marga pages.  No hidden endpoints are used.

Example:
  py scripts/cctv_geolocate.py `
    --cameras out/cctv-geolocate/source/cameras.json `
    --highways out/cctv-geolocate/source/highways.geojson `
    --out out/cctv-geolocate
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

EARTH_R_M = 6_371_008.8


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance in metres between two (lon, lat) points."""
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    h = (math.sin(dlat / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return 2.0 * EARTH_R_M * math.asin(math.sqrt(h))


def cumulative_distances(coords: list[list[float]]) -> list[float]:
    cum = [0.0]
    for a, b in zip(coords, coords[1:]):
        cum.append(cum[-1] + haversine_m((a[0], a[1]), (b[0], b[1])))
    return cum


def point_at_distance(coords: list[list[float]], cum: list[float],
                      dist_m: float) -> tuple[float, float]:
    """Linear interpolation along a polyline at a given distance."""
    if dist_m <= 0:
        return coords[0][0], coords[0][1]
    if dist_m >= cum[-1]:
        return coords[-1][0], coords[-1][1]
    lo, hi = 0, len(cum) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if cum[mid] <= dist_m:
            lo = mid
        else:
            hi = mid
    seg = cum[hi] - cum[lo]
    t = 0.0 if seg == 0 else (dist_m - cum[lo]) / seg
    lon = coords[lo][0] + t * (coords[hi][0] - coords[lo][0])
    lat = coords[lo][1] + t * (coords[hi][1] - coords[lo][1])
    return lon, lat


def km_to_road_position(km: float, anchors: list[dict]) -> tuple[float, bool]:
    """Piecewise-linear KM -> road position, clamped at the anchor range."""
    pts = sorted((float(a["km"]), float(a["roadPositionM"])) for a in anchors)
    if not pts:
        return km * 1000.0, False
    if km <= pts[0][0]:
        k0, m0 = pts[0]
        k1, m1 = pts[1] if len(pts) > 1 else pts[0]
        slope = 0.0 if k1 == k0 else (m1 - m0) / (k1 - k0)
        return m0 + (km - k0) * slope, km < pts[0][0]
    if km >= pts[-1][0]:
        k0, m0 = pts[-2] if len(pts) > 1 else pts[-1]
        k1, m1 = pts[-1]
        slope = 0.0 if k1 == k0 else (m1 - m0) / (k1 - k0)
        return m1 + (km - k1) * slope, km > pts[-1][0]
    for (k0, m0), (k1, m1) in zip(pts, pts[1:]):
        if k0 <= km <= k1:
            t = 0.0 if k1 == k0 else (km - k0) / (k1 - k0)
            return m0 + t * (m1 - m0), False
    return km * 1000.0, True


def load_highways(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for feat in data.get("features", []):
        geom = feat.get("geometry", {})
        if geom.get("type") != "LineString":
            continue
        coords = geom["coordinates"]
        props = feat.get("properties", {})
        anchors = props.get("cameraStationing", {}).get("anchors", [])
        out[feat.get("id", "")] = {
            "name": props.get("name", ""),
            "coords": coords,
            "cum": cumulative_distances(coords),
            "anchors": anchors,
            "length_m": cumulative_distances(coords)[-1],
        }
    return out


def offset_from_line(point: tuple[float, float], coords: list[list[float]]) -> float:
    """Approximate nearest-vertex distance from a point to the centreline."""
    return min(haversine_m(point, (c[0], c[1])) for c in coords)


# A camera label carries a KM station, not a survey.  Use a generous radius
# when retrieving street-level panoramas around the interpolated point.
RETRIEVAL_RADIUS_M = 200


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cameras", default="out/cctv-geolocate/source/cameras.json")
    ap.add_argument("--highways",
                    default="out/cctv-geolocate/source/highways.geojson")
    ap.add_argument("--out", default="out/cctv-geolocate")
    ap.add_argument("--highway", default="",
                    help="only this highwayId (default: all)")
    ap.add_argument("--max-offset-m", type=float, default=150.0)
    ap.add_argument("--no-map", action="store_true")
    args = ap.parse_args()

    cameras = json.loads(Path(args.cameras).read_text(encoding="utf-8"))
    highways = load_highways(Path(args.highways))
    cams = cameras.get("cameras", [])

    rows: list[dict] = []
    for c in cams:
        hid = c.get("highwayId", "")
        if args.highway and hid != args.highway:
            continue
        name = c.get("name", "")
        km = c.get("km")
        side = c.get("side")
        existing = c.get("coordinates")
        hw = highways.get(hid)

        row = {
            "id": c.get("id", ""),
            "provider_camera_id": c.get("providerCameraId", ""),
            "highway_id": hid,
            "highway_name": hw["name"] if hw else "",
            "name": name,
            "km": km,
            "side": side or "",
            "stream_url": c.get("streamUrl", ""),
            "source_page": c.get("sourcePage", ""),
            "existing_lon": existing[0] if existing else "",
            "existing_lat": existing[1] if existing else "",
            "existing_status": c.get("curationStatus", ""),
            "interp_lon": "",
            "interp_lat": "",
            "road_position_m": "",
            "line_length_m": round(hw["length_m"], 1) if hw else "",
            "retrieval_radius_m": RETRIEVAL_RADIUS_M,
            "offset_existing_vs_interp_m": "",
            "offset_existing_vs_line_m": "",
            "status": "",
            "gmaps_url": "",
            "streetview_url": "",
            "mapillary_url": "",
        }

        if hw is None:
            row["status"] = "no_highway_geometry"
        elif km is None:
            row["status"] = "no_km"
        else:
            pos, clamped = km_to_road_position(float(km), hw["anchors"])
            lon, lat = point_at_distance(hw["coords"], hw["cum"], pos)
            row["interp_lon"] = round(lon, 7)
            row["interp_lat"] = round(lat, 7)
            row["road_position_m"] = round(pos, 1)
            row["status"] = "clamped_km" if clamped else "interpolated"
            if existing:
                d = haversine_m((existing[0], existing[1]), (lon, lat))
                row["offset_existing_vs_interp_m"] = round(d, 1)

        if existing and hw is not None and row["offset_existing_vs_line_m"] == "":
            row["offset_existing_vs_line_m"] = round(
                offset_from_line((existing[0], existing[1]), hw["coords"]), 1)

        # What to use downstream: an existing coordinate wins, else the
        # provisional interpolation.
        if existing:
            row["final_lon"], row["final_lat"] = existing
            row["coord_source"] = c.get("curationStatus", "existing")
        elif row["interp_lon"] != "":
            row["final_lon"], row["final_lat"] = row["interp_lon"], row["interp_lat"]
            row["coord_source"] = "interpolated_km"
        else:
            row["final_lon"], row["final_lat"] = "", ""
            row["coord_source"] = "none"

        if row["final_lon"] != "":
            lon, lat = float(row["final_lon"]), float(row["final_lat"])
            row["gmaps_url"] = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            row["streetview_url"] = (
                "https://www.google.com/maps/@?api=1&map_action=pano"
                f"&viewpoint={lat},{lon}")
            row["mapillary_url"] = (
                f"https://www.mapillary.com/app/?lat={lat}&lng={lon}&z=17")

        rows.append(row)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    fields = list(rows[0].keys()) if rows else []
    with (out_dir / "cameras_geolocated.csv").open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # A focused table for the Cawang-Pluit corridor, the current Cawang case.
    fokus = [r for r in rows if r["highway_id"] == "dalam-kota"]
    if fokus:
        with (out_dir / "cameras_dalam_kota.csv").open(
                "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(fokus)

    feats = []
    for r in rows:
        if r["final_lon"] == "":
            continue
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [float(r["final_lon"]),
                                         float(r["final_lat"])]},
            "properties": {k: v for k, v in r.items()
                           if k not in ("final_lon", "final_lat")},
        })
    geojson = {"type": "FeatureCollection", "features": feats}
    (out_dir / "cameras_geolocated.geojson").write_text(
        json.dumps(geojson, indent=1, ensure_ascii=False), encoding="utf-8")

    # Summary
    by_highway: dict[str, list[dict]] = {}
    for r in rows:
        by_highway.setdefault(r["highway_id"], []).append(r)

    summary = {
        "n_cameras": len(rows),
        "n_with_coordinate": sum(bool(r["final_lon"] != "") for r in rows),
        "n_with_km": sum(r["km"] is not None for r in rows),
        "n_interpolated": sum(r["coord_source"] == "interpolated_km" for r in rows),
        "n_existing": sum(r["coord_source"] not in ("interpolated_km", "none")
                          for r in rows),
        "n_no_km": sum(r["status"] == "no_km" for r in rows),
        "n_no_geometry": sum(r["status"] == "no_highway_geometry" for r in rows),
        "n_clamped": sum(r["status"] == "clamped_km" for r in rows),
        "by_highway": {},
    }
    for hid, rs in sorted(by_highway.items()):
        offs = [r["offset_existing_vs_interp_m"] for r in rs
                if r["offset_existing_vs_interp_m"] != ""]
        summary["by_highway"][hid] = {
            "n": len(rs),
            "n_with_coordinate": sum(bool(r["final_lon"] != "") for r in rs),
            "n_interpolated": sum(r["coord_source"] == "interpolated_km"
                                  for r in rs),
            "n_existing": sum(r["coord_source"] not in ("interpolated_km", "none")
                              for r in rs),
            "n_no_km": sum(r["status"] == "no_km" for r in rs),
            "offset_median_m": (round(statistics.median(offs), 1)
                                if offs else None),
            "offset_max_m": round(max(offs), 1) if offs else None,
        }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.no_map:
        write_map(out_dir / "cameras_map.html", rows)

    print(f"{len(rows)} cameras; {summary['n_with_coordinate']} with a coordinate")
    print(f"  interpolated: {summary['n_interpolated']}; "
          f"existing: {summary['n_existing']}; "
          f"no KM: {summary['n_no_km']}; no geometry: {summary['n_no_geometry']}")
    for hid, s in summary["by_highway"].items():
        if s["n"] == 0:
            continue
        print(f"  {hid:<45} n={s['n']:3d} "
              f"coord={s['n_with_coordinate']:3d} "
              f"interp={s['n_interpolated']:3d} "
              f"existing={s['n_existing']:3d} "
              f"noKM={s['n_no_km']:3d} "
              f"offset_med={s['offset_median_m']} m")
    print(f"wrote {out_dir}")


def write_map(path: Path, rows: list[dict]) -> None:
    """A small Leaflet page for visual inspection of provisional points."""
    pts = []
    for r in rows:
        if r["final_lon"] == "":
            continue
        pts.append({
            "lon": float(r["final_lon"]),
            "lat": float(r["final_lat"]),
            "name": r["name"],
            "highway": r["highway_name"] or r["highway_id"],
            "km": r["km"],
            "side": r["side"],
            "source": r["coord_source"],
            "status": r["status"],
            "stream": r["stream_url"],
        })
    payload = json.dumps(pts, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>CCTV Bina Marga - koordinat sementara</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  html,body,#map {{ height:100%; margin:0; }}
  .popup {{ font: 12px/1.4 system-ui, sans-serif; max-width: 280px; }}
  .popup b {{ font-size: 13px; }}
  .badge {{ display:inline-block; padding:1px 5px; border-radius:4px;
            background:#eee; margin-right:4px; }}
</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const pts = {payload};
const map = L.map('map').setView([-6.2, 106.82], 12);
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
  {{maxZoom: 19, attribution: '&copy; OpenStreetMap'}}).addTo(map);
const colors = {{interpolated_km:'#d97706', provisional_stationing:'#2563eb',
  provisional_landmark:'#7c3aed', needs_review:'#6b7280'}};
for (const p of pts) {{
  const c = colors[p.source] || '#111827';
  L.circleMarker([p.lat, p.lon], {{radius: 5, color: c, fillColor: c,
    fillOpacity: 0.75, weight: 1}}).addTo(map).bindPopup(
    `<div class="popup"><b>${{p.name}}</b><br>` +
    `${{p.highway}}<br>` +
    `<span class="badge">KM ${{p.km ?? '-'}}</span>` +
    `<span class="badge">${{p.side || 'A/B ?'}}</span>` +
    `<span class="badge">${{p.source}}</span><br>` +
    `<a href="${{p.stream}}" target="_blank" rel="noreferrer">stream</a></div>`);
}}
</script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
