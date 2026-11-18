import csv, json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
fits = json.loads((REPO / "out/calib-compare/fits.json").read_text(encoding="utf-8"))
base = fits["baseline"]
base_f = base["f"]
methods = {m["name"]: m for m in fits["methods"]}

rows = [
    ("Cawang dash fit", "cawang_baseline", "baseline: 6 dash x 3 edge, w=3.60"),
    ("GeoCalib pinhole median2", "geocalib_pitch", "single image, f+pitch; yaw from VP"),
    ("GeoCalib multi shared", "geocalib_multi_sinkor", "8 frames, shared f; f=969.55"),
    ("AnyCalib simple median2", "anycalib_simple", "simple_pinhole; yaw/pitch from VP"),
    ("AnyCalib pinhole median2", "anycalib_pinhole", "full pinhole; f avg of fx/fy"),
    ("AnyCalib radial:1 median2", "anycalib_radial", "radial:1, k1=-0.0289"),
    ("AnyCalib simple TEMA 247", "anycalib_simple_tema", "frame t=247; f=1100.0"),
    ("AnyCalib gen simple median2", "anycalib_gen_simple_median2", "model variant anycalib_gen"),
    ("VP only (f=1082.6)", "vp_only", "vpfit VP; f fixed"),
    ("Free fit (w=3.60)", "free_fit", "all params free; f=1082.03"),
]

def fmt(x, n=3):
    return f"{x:.{n}f}"

out_rows = []
for label, key, note in rows:
    m = methods[key]
    s = m["fixed_pose"]
    sf = m.get("fixed_f")
    out_rows.append({
        "method": label,
        "f_px": round(s["f"], 2),
        "delta_f_pct": round((s["f"] - base_f) / base_f * 100, 2),
        "pitch_deg": round(s["th_deg"], 3),
        "yaw_deg": round(s["psi_deg"], 3),
        "h_m": round(s["h"], 3),
        "rms_fixed_pose_px": round(s["rms_px"], 3),
        "rms_fixed_f_px": round(sf["rms_px"], 3) if sf else None,
        "dof_fixed_pose": s["dof"],
        "note": note,
    })

out_dir = REPO / "reports/calib-compare"
out_dir.mkdir(parents=True, exist_ok=True)
with (out_dir / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
    w.writeheader(); w.writerows(out_rows)

print("| Metode | f (px) | delta f vs Cawang | pitch | yaw | h (m) | RMS fixed pose | RMS fixed f |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
for r in out_rows:
    rms_ff = "-" if r["rms_fixed_f_px"] is None else f"{r['rms_fixed_f_px']:.3f}"
    print(f"| {r['method']} | {r['f_px']:.2f} | {r['delta_f_pct']:+.1f}% | {r['pitch_deg']:.3f} deg | {r['yaw_deg']:.3f} deg | {r['h_m']:.3f} | {r['rms_fixed_pose_px']:.3f} | {rms_ff} |")
print("\nCSV:", out_dir / "summary.csv")
