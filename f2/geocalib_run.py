import sys, json, math
import torch
from geocalib import GeoCalib

model = GeoCalib()

def probe(p):
    img = model.load_image(p)
    res = model.calibrate(img)
    cam, grav = res["camera"], res["gravity"]
    f = float(cam.f.reshape(-1)[0].item())
    pitch = float(grav.pitch.reshape(-1)[0].item())
    roll = float(grav.roll.reshape(-1)[0].item())
    try:
        v = grav.vec3d.reshape(-1).tolist()
        vec = [round(float(x), 4) for x in v]
    except Exception:
        vec = None
    return {
        "image": p,
        "f_px": round(f, 1),
        "hfov_deg": round(2 * math.degrees(math.atan(240.0 / f)), 2),
        "pitch_deg": round(math.degrees(pitch), 2),
        "roll_deg": round(math.degrees(roll), 2),
        "horizon_row": round(180.0 - f * math.tan(pitch), 1),
        "f_tan_pitch": round(f * math.tan(pitch), 1),
        "gravity_vec": vec,
    }

out = [probe(p) for p in sys.argv[1:]]
for d in out:
    print(json.dumps(d), flush=True)
json.dump(out, open("f2/geocalib.json", "w"), indent=1)
print("\nringkasan:")
fs = [d["f_px"] for d in out]
ps = [d["pitch_deg"] for d in out]
print(f"  f   : min {min(fs):.1f}  max {max(fs):.1f}  mean {sum(fs)/len(fs):.1f} px")
print(f"  pitch: min {min(ps):.2f}  max {max(ps):.2f}  mean {sum(ps)/len(ps):.2f} deg")
print(f"  horizon row (mean): {sum(d['horizon_row'] for d in out)/len(out):.1f}")
