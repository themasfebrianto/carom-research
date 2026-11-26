// Compare GeoCalib / VP / GeoCalib+VP against a dash fit on one Cawang frame.
// Anchor: lane width w = 3.60 m. Observations: 18 dash edges (2 lanes x 3 rows).
//
// Usage:
//   node scripts/calib_compare/fit_compare_frame.mjs ^
//     --frame t350 --dashes out/calib-compare/newframe/dashes_t350.json ^
//     --vp out/calib-compare/newframe/vp_t350.json ^
//     --geo out/calib-compare/newframe/geocalib_t350.json ^
//     --out out/calib-compare/newframe/fits_t350
//
// Without --geo it still fits the dash reference and VP-only.
import fs from 'node:fs';
import path from 'node:path';

const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
  const k = process.argv[i].replace(/^--/, '');
  args[k] = process.argv[i + 1];
}
const REPO = path.resolve(args.repo || process.cwd());
const FRAME = args.frame || 'frame';
const DASHES = path.resolve(REPO, args.dashes || 'frames/dashes2.json');
const VP_PATH = path.resolve(REPO, args.vp || 'frames/vp.json');
const GEO_PATH = args.geo ? path.resolve(REPO, args.geo) : null;
const OUT = path.resolve(REPO, args.out || `out/calib-compare/newframe/fits_${FRAME}`);
const CX = 640, CY = 360;
const W_FIX = 3.60, PERIOD = 13, DASH = 5;

// Expected near-edge rows from the validated median2 calibration.  A single
// frame can contain extra fragments (occlusion, shadows); choose the run
// closest to each expected row instead of blindly taking the top three.
const ROW_TEMPLATE = {
  0: [698.92, 568.67, 503.44],
  1: [696.99, 567.03, 501.60],
};
const ROW_TOL = 20;

const raw = JSON.parse(fs.readFileSync(DASHES, 'utf8'));
const vp = JSON.parse(fs.readFileSync(VP_PATH, 'utf8')).VP;

const dashes = [];
const rejected = [];
for (const lane of [0, 1]) {
  const laneRuns = raw.filter(d => d.lane === lane);
  ROW_TEMPLATE[lane].forEach((expected, row) => {
    const candidates = laneRuns
      .map(d => ({ ...d, dist: Math.abs(d.yNear - expected) }))
      .filter(d => d.dist <= ROW_TOL)
      .sort((a, b) => a.dist - b.dist);
    if (!candidates.length) {
      rejected.push({ lane, row, reason: 'no run near expected row' });
      return;
    }
    const d = candidates[0];
    dashes.push({ lane, row, yFar: d.yFar, yNear: d.yNear, u: d.u, source_yNear: d.yNear });
  });
}
if (dashes.length < 4) {
  console.error(`only ${dashes.length} dashes selected; need >=4. Rejected:`, rejected);
  process.exit(2);
}

function proj(p, X, Y) {
  const { f, th, psi, h } = p;
  const cp = Math.cos(th), sp = Math.sin(th), cw = Math.cos(psi), sw = Math.sin(psi);
  const fw = [cp * cw, cp * sw, -sp];
  const rw = [sw, -cw, 0];
  const dw = [fw[1] * rw[2] - fw[2] * rw[1], fw[2] * rw[0] - fw[0] * rw[2], fw[0] * rw[1] - fw[1] * rw[0]];
  const dx = X, dy = Y, dz = -h;
  const xc = rw[0] * dx + rw[1] * dy + rw[2] * dz;
  const yc = dw[0] * dx + dw[1] * dy + dw[2] * dz;
  const zc = fw[0] * dx + fw[1] * dy + fw[2] * dz;
  return { u: CX + f * xc / zc, v: CY + f * yc / zc, zc };
}

function residuals(p) {
  const r = [];
  for (const dz of dashes) {
    const Y = p.Y0 - dz.lane * W_FIX;
    const Xn = p.Xp + dz.row * PERIOD;
    r.push(proj(p, Xn + DASH, Y).v - dz.yFar);
    r.push(proj(p, Xn, Y).v - dz.yNear);
    r.push(proj(p, Xn + DASH / 2, Y).u - dz.u);
  }
  return r;
}
const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);
const rms = p => {
  const r = residuals(p);
  return Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
};

function solve(p0, keys, iters = 900) {
  let p = { ...p0 }, lam = 1e-2;
  for (let it = 0; it < iters; it++) {
    const r = residuals(p);
    const J = r.map(() => keys.map(() => 0));
    for (let k = 0; k < keys.length; k++) {
      const dp = { ...p }, eps = Math.max(1e-7, Math.abs(p[keys[k]]) * 1e-6);
      dp[keys[k]] += eps;
      const r2 = residuals(dp);
      for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / eps;
    }
    const n = keys.length;
    const A = Array.from({ length: n }, () => Array(n).fill(0)), g = Array(n).fill(0);
    for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) {
      g[a] += J[i][a] * r[i];
      for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b];
    }
    for (let a = 0; a < n; a++) A[a][a] *= (1 + lam);
    const M = A.map((row, i) => [...row, -g[i]]);
    for (let c = 0; c < n; c++) {
      let pv = c; for (let t = c + 1; t < n; t++) if (Math.abs(M[t][c]) > Math.abs(M[pv][c])) pv = t;
      [M[c], M[pv]] = [M[pv], M[c]];
      const d0 = M[c][c]; if (Math.abs(d0) < 1e-14) continue;
      for (let j = c; j <= n; j++) M[c][j] /= d0;
      for (let t = 0; t < n; t++) { if (t === c) continue; const f0 = M[t][c]; for (let j = c; j <= n; j++) M[t][j] -= f0 * M[c][j]; }
    }
    const dx = M.map(row => row[n]);
    const pn = { ...p }; keys.forEach((k, i) => pn[k] += dx[i]);
    if (cost(pn) < cost(p)) { p = pn; lam = Math.max(lam * 0.3, 1e-10); } else lam *= 3;
  }
  return p;
}

const deg = x => x * 180 / Math.PI;
const rad = x => x * Math.PI / 180;
const wrap = x => { while (x > 180) x -= 360; while (x < -180) x += 360; return x; };
const vpPitch = f => Math.atan2(CY - vp.y, f);
const vpYaw = (f, th) => Math.atan2((vp.x - CX) * Math.cos(th), f);

function report(p, keys) {
  const r = residuals(p);
  const n = keys.length;
  const J = r.map(() => keys.map(() => 0));
  for (let k = 0; k < keys.length; k++) {
    const dp = { ...p }, eps = Math.max(1e-7, Math.abs(p[keys[k]]) * 1e-6); dp[keys[k]] += eps;
    const r2 = residuals(dp);
    for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / eps;
  }
  const A = Array.from({ length: n }, () => Array(n).fill(0));
  for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b];
  const M = A.map((row, i) => [...row, ...Array.from({ length: n }, (_, j) => i === j ? 1 : 0)]);
  for (let c = 0; c < n; c++) {
    let pv = c; for (let t = c + 1; t < n; t++) if (Math.abs(M[t][c]) > Math.abs(M[pv][c])) pv = t;
    [M[c], M[pv]] = [M[pv], M[c]];
    const d0 = M[c][c];
    for (let j = 0; j < 2 * n; j++) M[c][j] /= d0;
    for (let t = 0; t < n; t++) { if (t === c) continue; const f0 = M[t][c]; for (let j = 0; j < 2 * n; j++) M[t][j] -= f0 * M[c][j]; }
  }
  const dof = r.length - n;
  const s2 = dof > 0 ? r.reduce((s, x) => s + x * x, 0) / dof : NaN;
  const out = {
    n_obs: r.length, n_params: n, dof, rms_px: Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length),
    f: p.f, pitch_deg: deg(p.th), yaw_deg: deg(p.psi), h_m: p.h, Xp_m: p.Xp, Y0_m: p.Y0,
    f_th: p.f * p.th, f_h: p.f * p.h, f_w: p.f * W_FIX, w_h: W_FIX / p.h,
    hfov_deg: deg(2 * Math.atan(CX / p.f)),
    vp_model_u: CX + p.f * Math.tan(p.psi) / Math.cos(p.th),
    vp_model_v: CY - p.f * Math.tan(p.th),
    horizon_px: CY - p.f * Math.tan(p.th),
    std: Object.fromEntries(keys.map((k, i) => [k, Math.sqrt(Math.max(M[i][n + i], 0) * s2)])),
  };
  return out;
}

const base = { f: 1082.58269, th: 0.04245, psi: 0.00473, h: 8.87587, Xp: 24.63092, Y0: 9.64234 };
const ref = solve({ ...base }, ['f', 'th', 'psi', 'h', 'Xp', 'Y0']);
const refSummary = report(ref, ['f', 'th', 'psi', 'h', 'Xp', 'Y0']);

const methods = [];
const add = (name, source, f, th, psi, extra = {}) => {
  const p0 = { ...ref, f, th, psi };
  const fixedPose = solve(p0, ['h', 'Xp', 'Y0']);
  const fixedF = solve(p0, ['th', 'psi', 'h', 'Xp', 'Y0']);
  methods.push({
    name, source,
    input: { f, pitch_deg: deg(th), yaw_deg: deg(psi), ...extra },
    fixed_pose: report(fixedPose, ['h', 'Xp', 'Y0']),
    fixed_f: report(fixedF, ['th', 'psi', 'h', 'Xp', 'Y0']),
  });
};

add('dash_fit', 'free fit with w=3.60', ref.f, ref.th, ref.psi);
add('vp_only', 'VP + dash f', ref.f, vpPitch(ref.f), vpYaw(ref.f, vpPitch(ref.f)));

if (GEO_PATH) {
  const geo = JSON.parse(fs.readFileSync(GEO_PATH, 'utf8'));
  const fGeo = (geo.fx + (geo.fy ?? geo.fx)) / 2;
  const pitchGeo = rad(geo.pitch_deg_down_positive ?? geo.pitch_deg_down);
  add('geocalib', 'GeoCalib f + GeoCalib pitch + VP yaw', fGeo, pitchGeo, vpYaw(fGeo, pitchGeo), {
    roll_deg: geo.roll_deg, focal_uncertainty_px: geo.focal_uncertainty_px,
  });
  add('geocalib_vp', 'GeoCalib f + VP pitch/yaw', fGeo, vpPitch(fGeo), vpYaw(fGeo, vpPitch(fGeo)), {
    roll_deg: geo.roll_deg, focal_uncertainty_px: geo.focal_uncertainty_px,
  });
}

const result = {
  generated: new Date().toISOString(),
  frame: FRAME,
  dashes_path: DASHES, vp_path: VP_PATH, geo_path: GEO_PATH,
  anchor_w_m: W_FIX, vp,
  vp_pitch_deg_at_ref: deg(vpPitch(ref.f)),
  vp_yaw_deg_at_ref: deg(vpYaw(ref.f, vpPitch(ref.f))),
  n_dashes: dashes.length,
  dashes, rejected,
  reference: refSummary,
  methods,
};

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(`${OUT}.json`, JSON.stringify(result, null, 2));
const cols = ['frame', 'method', 'source', 'mode', 'f', 'df_pct', 'pitch_deg', 'dpitch_deg', 'yaw_deg', 'dyaw_deg', 'h_m', 'rms_px', 'n_obs', 'dof', 'pass_f', 'pass_pose', 'pass_rms'];
const lines = [cols.join(',')];
for (const m of methods) {
  for (const [mode, s] of [['fixed_pose', m.fixed_pose], ['fixed_f', m.fixed_f]]) {
    const df = (s.f - refSummary.f) / refSummary.f * 100;
    const dp = s.pitch_deg - refSummary.pitch_deg;
    const dy = wrap(s.yaw_deg - refSummary.yaw_deg);
    const passF = Math.abs(df) < 5;
    const passPose = Math.abs(dp) < 0.5 && Math.abs(dy) < 2;
    const passRms = s.rms_px < 1.5;
    lines.push([FRAME, m.name, m.source, mode, s.f.toFixed(3), df.toFixed(3), s.pitch_deg.toFixed(4), dp.toFixed(4), s.yaw_deg.toFixed(4), dy.toFixed(4), s.h_m.toFixed(4), s.rms_px.toFixed(4), s.n_obs, s.dof, passF, passPose, passRms].join(','));
  }
}
fs.writeFileSync(`${OUT}.csv`, lines.join('\n') + '\n');

console.log(`frame=${FRAME} dashes=${dashes.length} VP=(${vp.x.toFixed(2)}, ${vp.y.toFixed(2)})`);
console.log(`dash ref: f=${refSummary.f.toFixed(2)} pitch=${refSummary.pitch_deg.toFixed(3)} yaw=${refSummary.yaw_deg.toFixed(3)} h=${refSummary.h_m.toFixed(3)} RMS=${refSummary.rms_px.toFixed(3)}`);
for (const m of methods) {
  for (const [mode, s] of [['fixed_pose', m.fixed_pose], ['fixed_f', m.fixed_f]]) {
    const df = (s.f - refSummary.f) / refSummary.f * 100;
    const dp = s.pitch_deg - refSummary.pitch_deg;
    const dy = wrap(s.yaw_deg - refSummary.yaw_deg);
    console.log(`${m.name.padEnd(13)} ${mode.padEnd(10)} f=${s.f.toFixed(1)} (${df >= 0 ? '+' : ''}${df.toFixed(2)}%) pitch=${s.pitch_deg.toFixed(3)} (${dp >= 0 ? '+' : ''}${dp.toFixed(3)}) yaw=${s.yaw_deg.toFixed(3)} (${dy >= 0 ? '+' : ''}${dy.toFixed(3)}) RMS=${s.rms_px.toFixed(3)}`);
  }
}
console.log(`wrote ${OUT}.csv and ${OUT}.json`);
