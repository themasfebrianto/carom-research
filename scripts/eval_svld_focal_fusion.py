#!/usr/bin/env python
"""Evaluate GeoCalib + AnyCalib focal-length fusion against SVLD GT.

Unlike ``eval_svld_fusion.py`` (VP + f combinations), this script scores only
focal length and asks whether blind fusion of the two learned estimators
generalises from Cawang to an independent ground truth.

Scoring:
  * per image: |f - f_gt| / f_gt, pass at 5% and 10%
  * per scene: the same, plus one static-camera estimate per model
  * scene-level leave-one-scene-out calibration, because all images of a scene
    share one GT and the five scenes are the effective independent samples.

Example:
  py scripts/eval_svld_focal_fusion.py --out out/svld_focal_fusion
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

F_TOL = 0.05
F_TOL_10 = 0.10


def pct(v: float, ref: float) -> float:
    return (v - ref) / ref * 100.0


def stats(values: list[float], refs: list[float]) -> dict:
    if not values:
        return {"n": 0}
    errs = [pct(v, r) for v, r in zip(values, refs)]
    abs_errs = [abs(e) for e in errs]
    return {
        "n": len(values),
        "bias_pct": round(statistics.fmean(errs), 4),
        "mae_pct": round(statistics.fmean(abs_errs), 4),
        "rmse_pct": round(math.sqrt(statistics.fmean(e * e for e in errs)), 4),
        "median_abs_pct": round(statistics.median(abs_errs), 4),
        "p90_abs_pct": round(sorted(abs_errs)[min(len(abs_errs) - 1,
                                                  round((len(abs_errs) - 1) * 0.9))], 4),
        "max_abs_pct": round(max(abs_errs), 4),
        "pass_5pct": int(sum(e <= F_TOL * 100 for e in abs_errs)),
        "pass_10pct": int(sum(e <= F_TOL_10 * 100 for e in abs_errs)),
    }


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append({
                "split": r["split"],
                "scene": r["scene"],
                "image": r["image"],
                "f_gt": float(r["f_gt"]),
                "f_geo": float(r["f_geo"]),
                "f_any": float(r["f_any"]),
            })
    if not rows:
        raise SystemExit(f"no rows in {path}")
    return rows


def fuse_rows(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        g, a, gt = r["f_geo"], r["f_any"], r["f_gt"]
        out.append({
            **r,
            "f_mean": (g + a) / 2.0,
            "f_geom": math.sqrt(g * a),
            "f_harm": 2.0 * g * a / (g + a),
            "f_w25_geo": 0.25 * g + 0.75 * a,
            "f_w40_geo": 0.40 * g + 0.60 * a,
            "f_w60_geo": 0.60 * g + 0.40 * a,
            "f_w75_geo": 0.75 * g + 0.25 * a,
        })
    return out


def method_values(rows: list[dict], name: str) -> list[float]:
    return [r[name] for r in rows]


def summarize(rows: list[dict], names: list[str]) -> dict:
    refs = [r["f_gt"] for r in rows]
    return {name: stats(method_values(rows, name), refs) for name in names}


def convex_weight(g: np.ndarray, a: np.ndarray, ref: np.ndarray) -> float:
    x = g - a
    y = ref - a
    denom = float(np.dot(x, x))
    return float(np.dot(x, y) / denom) if denom else 0.5


def loo_convex(rows: list[dict], key_g: str = "f_geo",
               key_a: str = "f_any") -> dict:
    g = np.array([r[key_g] for r in rows])
    a = np.array([r[key_a] for r in rows])
    ref = np.array([r["f_gt"] for r in rows])
    preds = []
    for i in range(len(rows)):
        mask = np.ones(len(rows), dtype=bool)
        mask[i] = False
        w = convex_weight(g[mask], a[mask], ref[mask])
        preds.append(w * g[i] + (1.0 - w) * a[i])
    w_full = convex_weight(g, a, ref)
    return {"w_full": w_full, "preds": preds}


def loo_scale(values: list[float], refs: list[float]) -> dict:
    ratios = [r / v for v, r in zip(values, refs)]
    preds = []
    for i, v in enumerate(values):
        others = [ratios[j] for j in range(len(ratios)) if j != i]
        preds.append(v * statistics.median(others))
    return {"k_full": statistics.median(ratios), "preds": preds}


def pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
    if not sx or not sy:
        return float("nan")
    cov = statistics.fmean((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / (sx * sy)


def diagnostics(rows: list[dict]) -> dict:
    """How much of the two models' error is shared, and how far apart they are."""
    rg = [r["f_geo"] / r["f_gt"] for r in rows]
    ra = [r["f_any"] / r["f_gt"] for r in rows]
    gap = [abs(x - y) / y * 100.0 for x, y in zip(rg, ra)]
    return {
        "mean_ratio_geo": round(statistics.fmean(rg), 4),
        "mean_ratio_any": round(statistics.fmean(ra), 4),
        "error_correlation": round(pearson(rg, ra), 4),
        "gap_median_pct": round(statistics.median(gap), 4),
        "gap_mean_pct": round(statistics.fmean(gap), 4),
        "gap_p90_pct": round(sorted(gap)[min(len(gap) - 1,
                                            round((len(gap) - 1) * 0.9))], 4),
    }


def scene_medians(rows: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["scene"]].append(r)
    out = []
    for scene, rs in sorted(groups.items()):
        g = statistics.median(r["f_geo"] for r in rs)
        a = statistics.median(r["f_any"] for r in rs)
        out.append({
            "scene": scene,
            "n": len(rs),
            "f_gt": statistics.fmean(r["f_gt"] for r in rs),
            "f_geo": g,
            "f_any": a,
            "f_mean": (g + a) / 2.0,
            "f_geom": math.sqrt(g * a),
            "f_harm": 2.0 * g * a / (g + a),
            "f_w25_geo": 0.25 * g + 0.75 * a,
            "f_w40_geo": 0.40 * g + 0.60 * a,
            "f_w60_geo": 0.60 * g + 0.40 * a,
            "f_w75_geo": 0.75 * g + 0.25 * a,
        })
    return out


def scene_loo_convex(medians: list[dict]) -> dict:
    """Fit one convex weight on four scene medians, predict the fifth."""
    preds, weights = [], []
    for i, held in enumerate(medians):
        train = [m for j, m in enumerate(medians) if j != i]
        g = np.array([m["f_geo"] for m in train])
        a = np.array([m["f_any"] for m in train])
        ref = np.array([m["f_gt"] for m in train])
        w = convex_weight(g, a, ref)
        weights.append(w)
        preds.append(w * held["f_geo"] + (1.0 - w) * held["f_any"])
    refs = [m["f_gt"] for m in medians]
    return {"weights": weights, "preds": preds, "stats": stats(preds, refs)}


def scene_loo_model_scale(medians: list[dict]) -> dict:
    """Per-model scale fitted on four scenes, applied to the held-out scene."""
    preds, k_geo, k_any = [], [], []
    for i, held in enumerate(medians):
        train = [m for j, m in enumerate(medians) if j != i]
        kg = statistics.median(m["f_gt"] / m["f_geo"] for m in train)
        ka = statistics.median(m["f_gt"] / m["f_any"] for m in train)
        k_geo.append(kg)
        k_any.append(ka)
        preds.append(0.5 * (kg * held["f_geo"] + ka * held["f_any"]))
    refs = [m["f_gt"] for m in medians]
    return {
        "k_geo": k_geo, "k_any": k_any, "preds": preds,
        "stats": stats(preds, refs),
    }


def scene_loo_fused_scale(medians: list[dict]) -> dict:
    """One scale on the 50/50 scene median, fitted on four scenes."""
    preds, ks = [], []
    for i, held in enumerate(medians):
        train = [m for j, m in enumerate(medians) if j != i]
        k = statistics.median(m["f_gt"] / m["f_mean"] for m in train)
        ks.append(k)
        preds.append(k * held["f_mean"])
    refs = [m["f_gt"] for m in medians]
    return {"k": ks, "preds": preds, "stats": stats(preds, refs)}


def per_scene_scale(rows: list[dict], n_anchor: int) -> dict:
    """Rescale the 50/50 mean per camera from the first ``n_anchor`` frames.

    ``n_anchor=0`` fits the scale on every frame of the scene (oracle); a
    positive value simulates a short labelled calibration clip per camera.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["scene"]].append(r)
    preds, refs, scenes, ks = [], [], [], []
    by_scene = {}
    for scene, rs in sorted(groups.items()):
        rs = sorted(rs, key=lambda r: r["image"])
        n = n_anchor if n_anchor > 0 else len(rs)
        anchors, held = rs[:n], rs[n:]
        k = statistics.median(r["f_gt"] / r["f_mean"] for r in anchors)
        scene_preds = [k * r["f_mean"] for r in held]
        scene_refs = [r["f_gt"] for r in held]
        ks.append(k)
        by_scene[scene] = {
            "k": round(k, 4),
            "n_anchor": len(anchors),
            "n": len(held),
            **stats(scene_preds, scene_refs),
        }
        for r, p in zip(held, scene_preds):
            preds.append(p)
            refs.append(r["f_gt"])
            scenes.append(scene)
    return {
        "scenes": scenes, "k": ks, "preds": preds,
        "stats": stats(preds, refs), "by_scene": by_scene,
    }


def per_scene_scale_insample(rows: list[dict]) -> dict:
    """Optimistic bound: one scale per scene fitted and scored on all frames."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["scene"]].append(r)
    preds, refs, ks, by_scene = [], [], [], {}
    for scene, rs in sorted(groups.items()):
        k = statistics.median(r["f_gt"] / r["f_mean"] for r in rs)
        scene_preds = [k * r["f_mean"] for r in rs]
        scene_refs = [r["f_gt"] for r in rs]
        ks.append(k)
        by_scene[scene] = {"k": round(k, 4), "n": len(rs),
                           **stats(scene_preds, scene_refs)}
        preds.extend(scene_preds)
        refs.extend(scene_refs)
    return {"k": ks, "stats": stats(preds, refs), "by_scene": by_scene}


def per_scene_model_scale(rows: list[dict], n_anchor: int) -> dict:
    """Scale each model per camera, then average, from ``n_anchor`` frames."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["scene"]].append(r)
    preds, refs, by_scene = [], [], {}
    for scene, rs in sorted(groups.items()):
        rs = sorted(rs, key=lambda r: r["image"])
        n = n_anchor if n_anchor > 0 else len(rs)
        anchors, held = rs[:n], rs[n:]
        kg = statistics.median(r["f_gt"] / r["f_geo"] for r in anchors)
        ka = statistics.median(r["f_gt"] / r["f_any"] for r in anchors)
        scene_preds = [0.5 * (kg * r["f_geo"] + ka * r["f_any"]) for r in held]
        scene_refs = [r["f_gt"] for r in held]
        by_scene[scene] = {
            "k_geo": round(kg, 4), "k_any": round(ka, 4),
            "n_anchor": len(anchors), "n": len(held),
            **stats(scene_preds, scene_refs),
        }
        preds.extend(scene_preds)
        refs.extend(scene_refs)
    return {
        "preds": preds, "stats": stats(preds, refs), "by_scene": by_scene,
    }


def mc_anchor(rows: list[dict], n_anchor: int, trials: int = 2000,
              seed: int = 42) -> dict:
    """Random-anchor simulation of the per-camera scale recipe.

    Each trial draws ``n_anchor`` labelled frames per scene, fits one scale for
    that camera, and scores the remaining frames.  Averaging over draws removes
    the luck of a particular anchor frame.
    """
    rng = random.Random(seed)
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["scene"]].append(r)
    scenes = sorted(groups.items())
    trial_mae, trial_pass, trial_max = [], [], []
    scene_mae: dict[str, list[float]] = {s: [] for s, _ in scenes}
    scene_pass: dict[str, list[int]] = {s: [] for s, _ in scenes}
    for _ in range(trials):
        errs, passes, worst = [], 0, 0.0
        for scene, rs in scenes:
            order = list(range(len(rs)))
            rng.shuffle(order)
            anchors = [rs[i] for i in order[:n_anchor]]
            held = [rs[i] for i in order[n_anchor:]]
            k = statistics.median(r["f_gt"] / r["f_mean"] for r in anchors)
            se = [abs(pct(k * r["f_mean"], r["f_gt"])) for r in held]
            sp = sum(e <= F_TOL * 100 for e in se)
            errs.extend(se)
            passes += sp
            worst = max(worst, max(se))
            scene_mae[scene].append(statistics.fmean(se))
            scene_pass[scene].append(sp)
        trial_mae.append(statistics.fmean(errs))
        trial_pass.append(passes)
        trial_max.append(worst)

    def q(vals: list[float], p: float) -> float:
        sv = sorted(vals)
        return sv[min(len(sv) - 1, round((len(sv) - 1) * p))]

    n_held = len(rows) - n_anchor * len(scenes)
    return {
        "n_anchor": n_anchor,
        "trials": trials,
        "n_held": n_held,
        "mae_pct_mean": round(statistics.fmean(trial_mae), 4),
        "mae_pct_p10": round(q(trial_mae, 0.1), 4),
        "mae_pct_p90": round(q(trial_mae, 0.9), 4),
        "pass_5pct_mean": round(statistics.fmean(trial_pass), 2),
        "max_abs_pct_mean": round(statistics.fmean(trial_max), 4),
        "by_scene": {
            scene: {
                "mae_pct_mean": round(statistics.fmean(scene_mae[scene]), 4),
                "pass_5pct_mean": round(statistics.fmean(scene_pass[scene]), 2),
                "n_held": len(groups[scene]) - n_anchor,
            }
            for scene, _ in scenes
        },
    }


def load_multi_f(multi_dir: Path, scene: str) -> float | None:
    path = multi_dir / f"geocalib_multi_{scene}.json"
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    return d.get("f_median")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default="out/svld_anycalib/eval_anycalib.csv")
    ap.add_argument("--multi-dir", default="out/svld_geocalib")
    ap.add_argument("--out", default="out/svld_focal_fusion")
    args = ap.parse_args()

    rows = fuse_rows(load_rows(Path(args.eval)))
    names = ["f_geo", "f_any", "f_mean", "f_geom", "f_harm",
             "f_w25_geo", "f_w40_geo", "f_w60_geo", "f_w75_geo"]

    overall = summarize(rows, names)
    diag = diagnostics(rows)
    by_scene: dict[str, dict] = {}
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["scene"]].append(r)
    for scene, rs in sorted(groups.items()):
        by_scene[scene] = summarize(rs, names)

    # Image-level LOO (scene-leaky, shown only for comparison with Cawang).
    img_loo = loo_convex(rows)
    img_loo_stats = stats(img_loo["preds"], [r["f_gt"] for r in rows])
    scale_loo = loo_scale([r["f_mean"] for r in rows], [r["f_gt"] for r in rows])
    scale_loo_stats = stats(scale_loo["preds"], [r["f_gt"] for r in rows])

    # Static-camera scene medians and honest leave-one-scene-out calibration.
    medians = scene_medians(rows)
    median_stats = summarize(medians, names)
    scene_loo = scene_loo_convex(medians)
    scene_scale_models = scene_loo_model_scale(medians)
    scene_scale_fused = scene_loo_fused_scale(medians)
    scale_anchor = {str(n): per_scene_scale(rows, n) for n in (1, 10)}
    scale_oracle = per_scene_scale_insample(rows)
    model_scale_anchor = {str(n): per_scene_model_scale(rows, n) for n in (1, 10)}
    mc = {str(n): mc_anchor(rows, n) for n in (1, 5)}

    # Static-camera check with GeoCalib's shared multi-frame f.
    multi_rows = []
    for m in medians:
        f_multi = load_multi_f(Path(args.multi_dir), m["scene"])
        if f_multi is not None:
            multi_rows.append({
                "scene": m["scene"],
                "f_gt": m["f_gt"],
                "f_multi": f_multi,
                "f_multi_any": 0.5 * (f_multi + m["f_any"]),
            })
    multi_stats = summarize(multi_rows, ["f_multi", "f_multi_any"]) if multi_rows else {}

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    frame_fields = ["split", "scene", "image", "f_gt", "f_geo", "f_any",
                    "f_mean", "f_geom", "f_harm"]
    frame_fields += [n for n in names if n not in frame_fields]
    frame_fields += [f"err_{n[2:]}_pct" for n in names]
    frame_fields += [f"pass_{n[2:]}" for n in names]
    with (out_dir / "fusion_frames.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=frame_fields)
        w.writeheader()
        for r in rows:
            row = {k: r[k] for k in frame_fields if k in r}
            for n in names:
                row[f"err_{n[2:]}_pct"] = round(pct(r[n], r["f_gt"]), 4)
                row[f"pass_{n[2:]}"] = abs(pct(r[n], r["f_gt"])) <= F_TOL * 100
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v)
                        for k, v in row.items()})

    method_rows = []
    for name in names:
        s = overall[name]
        method_rows.append({
            "method": name,
            "n": s["n"],
            "bias_pct": s["bias_pct"],
            "mae_pct": s["mae_pct"],
            "rmse_pct": s["rmse_pct"],
            "median_abs_pct": s["median_abs_pct"],
            "p90_abs_pct": s["p90_abs_pct"],
            "max_abs_pct": s["max_abs_pct"],
            "pass_5pct": s["pass_5pct"],
            "pass_10pct": s["pass_10pct"],
        })
    with (out_dir / "fusion_methods.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(method_rows[0].keys()))
        w.writeheader()
        w.writerows(method_rows)

    scene_rows = []
    for scene, s_by_name in by_scene.items():
        for name, s in s_by_name.items():
            scene_rows.append({"scene": scene, "method": name, **s})
    with (out_dir / "fusion_scenes.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(scene_rows[0].keys()))
        w.writeheader()
        w.writerows(scene_rows)

    median_rows = []
    for m in medians:
        for name in names:
            median_rows.append({
                "scene": m["scene"], "n": m["n"], "method": name,
                "f_gt": round(m["f_gt"], 4),
                "f_est": round(m[name], 4),
                "err_pct": round(pct(m[name], m["f_gt"]), 4),
            })
    with (out_dir / "fusion_scene_medians.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(median_rows[0].keys()))
        w.writeheader()
        w.writerows(median_rows)

    mc_rows = []
    for n, res in mc.items():
        for scene, v in res["by_scene"].items():
            mc_rows.append({
                "n_anchor": n, "scene": scene, "trials": res["trials"],
                "n_held": v["n_held"],
                "mae_pct_mean": v["mae_pct_mean"],
                "pass_5pct_mean": v["pass_5pct_mean"],
            })
        mc_rows.append({
            "n_anchor": n, "scene": "ALL", "trials": res["trials"],
            "n_held": res["n_held"], "mae_pct_mean": res["mae_pct_mean"],
            "pass_5pct_mean": res["pass_5pct_mean"],
        })
    with (out_dir / "anchor_mc.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(mc_rows[0].keys()))
        w.writeheader()
        w.writerows(mc_rows)

    summary = {
        "input": str(args.eval),
        "n_images": len(rows),
        "n_scenes": len(by_scene),
        "note": ("All images of a scene share one GT focal length; the five "
                 "scenes, not the 100 images, are the independent samples."),
        "overall": overall,
        "diagnostics": diag,
        "by_scene": by_scene,
        "image_loo_convex": {
            "w_geo_full": img_loo["w_full"],
            "stats": img_loo_stats,
        },
        "image_loo_mean_scale": {
            "k_full": scale_loo["k_full"],
            "stats": scale_loo_stats,
        },
        "scene_medians": {
            "values": medians,
            "stats": median_stats,
        },
        "scene_loo_convex": scene_loo,
        "scene_loo_model_scale": scene_scale_models,
        "scene_loo_fused_scale": scene_scale_fused,
        "per_scene_scale_anchor": scale_anchor,
        "per_scene_scale_oracle": scale_oracle,
        "per_scene_model_scale_anchor": model_scale_anchor,
        "anchor_monte_carlo": mc,
        "multi_frame": {"values": multi_rows, "stats": multi_stats},
    }
    (out_dir / "fusion_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")

    print(f"{len(rows)} images / {len(by_scene)} scenes")
    print(f"{'method':<12} {'bias%':>8} {'MAE%':>7} {'med%':>7} {'max%':>7} "
          f"{'<=5%':>7} {'<=10%':>7}")
    for name in names:
        s = overall[name]
        print(f"{name:<12} {s['bias_pct']:8.2f} {s['mae_pct']:7.2f} "
              f"{s['median_abs_pct']:7.2f} {s['max_abs_pct']:7.2f} "
              f"{s['pass_5pct']:>4}/{s['n']:<2} {s['pass_10pct']:>4}/{s['n']:<2}")
    print("\nper scene, median |err| %")
    print(f"{'scene':<18} " + " ".join(f"{n[2:]:>8}" for n in names))
    for scene, s_by_name in by_scene.items():
        print(f"{scene:<18} " + " ".join(
            f"{s_by_name[n]['median_abs_pct']:8.2f}" for n in names))
    print(f"\nrelative error correlation r={diag['error_correlation']:.3f}; "
          f"mean ratio geo={diag['mean_ratio_geo']:.3f} any={diag['mean_ratio_any']:.3f}; "
          f"model gap median={diag['gap_median_pct']:.2f}%")
    print(f"image LOO convex w_geo={img_loo['w_full']:.3f} "
          f"MAE={img_loo_stats['mae_pct']:.2f}% "
          f"pass={img_loo_stats['pass_5pct']}/{img_loo_stats['n']}")
    print(f"scene LOO convex w_geo={scene_loo['weights']} "
          f"MAE={scene_loo['stats']['mae_pct']:.2f}%")
    print(f"scene LOO model scale MAE={scene_scale_models['stats']['mae_pct']:.2f}% "
          f"k_geo={[round(k, 3) for k in scene_scale_models['k_geo']]} "
          f"k_any={[round(k, 3) for k in scene_scale_models['k_any']]}")
    for n, res in scale_anchor.items():
        print(f"per-scene 50/50 scale from {n} anchor frame(s): "
              f"MAE={res['stats']['mae_pct']:.2f}% "
              f"pass={res['stats']['pass_5pct']}/{res['stats']['n']} "
              f"max={res['stats']['max_abs_pct']:.2f}% "
              f"k={[round(k, 3) for k in res['k']]}")
    for n, res in model_scale_anchor.items():
        print(f"per-scene per-model scale from {n} anchor frame(s): "
              f"MAE={res['stats']['mae_pct']:.2f}% "
              f"pass={res['stats']['pass_5pct']}/{res['stats']['n']} "
              f"max={res['stats']['max_abs_pct']:.2f}%")
    print(f"per-scene 50/50 scale, oracle: "
          f"MAE={scale_oracle['stats']['mae_pct']:.2f}% "
          f"pass={scale_oracle['stats']['pass_5pct']}/{scale_oracle['stats']['n']}")
    for n, res in mc.items():
        print(f"anchor MC {n} frame(s)/camera: MAE mean={res['mae_pct_mean']:.2f}% "
              f"(p10-p90 {res['mae_pct_p10']:.2f}-{res['mae_pct_p90']:.2f}%) "
              f"pass={res['pass_5pct_mean']:.1f}/{res['n_held']} "
              f"max={res['max_abs_pct_mean']:.2f}%")
    if multi_stats:
        print(f"GeoCalib multi + Any median: "
              f"MAE={multi_stats['f_multi_any']['mae_pct']:.2f}% "
              f"pass={multi_stats['f_multi_any']['pass_5pct']}/{multi_stats['f_multi_any']['n']}")
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
