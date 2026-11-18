// Compare external calibrations against the 18 Cawang dash-edge observations.
// Anchor: lane width w = 3.60 m. Model and observations follow anchor.mjs.
import fs from 'node:fs';
import path from 'node:path';

const REPO = path.resolve(process.argv[2] || process.cwd());
const OUT = path.join(REPO, 'out/calib-compare');
const CX = 640, CY = 360;
const W_FIX = 3.60, PERIOD = 13, DASH = 5;

const raw = JSON.parse(fs.readFileSync(path.join(REPO, 'frames/dashes2.json'), 'utf8'));
const vp = JSON.parse(fs.readFileSync(path.join(REPO, 'frames/vp.json'), 'utf8')).VP;
const dashes = [];
for (const lane of [0, 1]) {
  const ds = raw.filter(d => d.lane === lane).sort((a, b) => b.yNear - a.yNear).slice(0, 3);
  ds.forEach((d, k) => dashes.push({ lane, row: k, yFar: d.yFar, yNear: d.yNear, u: d.u }));
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
const rms = p => Math.sqrt(residuals(p).reduce((s, x) => s + x * x, 0) / residuals(p).length);

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
const vpPitch = f => Math.atan2(CY - vp.y, f);
const vpYaw = (f, th) => Math.atan2((vp.x - CX) * Math.cos(th), f);

function summarize(label, p, mode, extra = {}) {
  const r = residuals(p);
  const dof = r.length - (mode === 'free' ? 6 : mode === 'fixed_f' ? 5 : 3);
  return {
    label, mode,
    f: p.f, th_rad: p.th, th_deg: deg(p.th), psi_rad: p.psi, psi_deg: deg(p.psi),
    h: p.h, Xp: p.Xp, Y0: p.Y0,
    rms_px: Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length),
    dof, n_obs: r.length,
    f_th: p.f * p.th, f_h: p.f * p.h, f_w: p.f * W_FIX, w_h: W_FIX / p.h,
    vp_model_u: CX + p.f * Math.tan(p.psi) / Math.cos(p.th),
    vp_model_v: CY - p.f * Math.tan(p.th),
    horizon_px: CY - p.f * Math.tan(p.th),
    hfov_deg: deg(2 * Math.atan(CX / p.f)),
    ...extra,
  };
}

const base = { f: 1082.58269, th: 0.04245, psi: 0.00473, h: 8.87587, Xp: 24.63092, Y0: 9.64234 };
const geo = JSON.parse(fs.readFileSync(path.join(OUT, 'geocalib_median2.json'), 'utf8'));
const geoMedian = JSON.parse(fs.readFileSync(path.join(OUT, 'geocalib_median.json'), 'utf8'));
const geoSinkor = JSON.parse(fs.readFileSync(path.join(OUT, 'geocalib_sinkor_86.json'), 'utf8'));
const geoTema = JSON.parse(fs.readFileSync(path.join(OUT, 'geocalib_tema_247.json'), 'utf8'));
const geoMulti = JSON.parse(fs.readFileSync(path.join(OUT, 'geocalib_multi_sinkor.json'), 'utf8'));
const geoPriorMedian2 = JSON.parse(fs.readFileSync(path.join(OUT, 'geocalib_median2_prior_f1082.json'), 'utf8'));
const geoPriorSinkor = JSON.parse(fs.readFileSync(path.join(OUT, 'geocalib_sinkor_prior_f1082.json'), 'utf8'));
const anySimple = JSON.parse(fs.readFileSync(path.join(OUT, 'anycalib_simple_pinhole.json'), 'utf8'));
const anySimpleSinkor = JSON.parse(fs.readFileSync(path.join(OUT, 'anycalib_simple_sinkor_86.json'), 'utf8'));
const anySimpleTema = JSON.parse(fs.readFileSync(path.join(OUT, 'anycalib_simple_tema_247.json'), 'utf8'));
const anyGenSimple = JSON.parse(fs.readFileSync(path.join(OUT, 'anycalib_gen_simple_median2.json'), 'utf8'));
const anyGenSimpleTema = JSON.parse(fs.readFileSync(path.join(OUT, 'anycalib_gen_simple_tema_247.json'), 'utf8'));
const anyPin = JSON.parse(fs.readFileSync(path.join(OUT, 'anycalib_pinhole.json'), 'utf8'));
const anyRad = JSON.parse(fs.readFileSync(path.join(OUT, 'anycalib_radial1.json'), 'utf8'));

const methods = [];
const add = (name, f, th, psi, source, extra = {}) => {
  const p0 = { ...base, f, th, psi };
  const fixedPose = solve(p0, ['h', 'Xp', 'Y0']);
  const fixedF = solve(p0, ['th', 'psi', 'h', 'Xp', 'Y0']);
  methods.push({
    name, source,
    input: { f, th_deg: deg(th), psi_deg: deg(psi), ...extra },
    fixed_pose: summarize(`${name} | fixed pose`, fixedPose, 'fixed_pose'),
    fixed_f: summarize(`${name} | fixed f`, fixedF, 'fixed_f'),
  });
};

add('cawang_baseline', base.f, base.th, base.psi, 'anchor.mjs');
add('geocalib_pitch', geo.fx, geo.pitch_deg_down_positive * Math.PI / 180, vpYaw(geo.fx, vpPitch(geo.fx)), 'GeoCalib pinhole', { geo_pitch_down_deg: geo.pitch_deg_down_positive, geo_roll_deg: geo.roll_deg, geo_unc_px: geo.focal_uncertainty_px });
add('geocalib_vp_pitch', geo.fx, vpPitch(geo.fx), vpYaw(geo.fx, vpPitch(geo.fx)), 'GeoCalib f + VP pitch/yaw');
add('anycalib_simple', anySimple.fx, vpPitch(anySimple.fx), vpYaw(anySimple.fx, vpPitch(anySimple.fx)), 'AnyCalib simple_pinhole f + VP');
add('anycalib_pinhole', (anyPin.fx + anyPin.fy) / 2, vpPitch((anyPin.fx + anyPin.fy) / 2), vpYaw((anyPin.fx + anyPin.fy) / 2, vpPitch((anyPin.fx + anyPin.fy) / 2)), 'AnyCalib pinhole f avg + VP', { fx: anyPin.fx, fy: anyPin.fy, cx: anyPin.cx, cy: anyPin.cy });
add('anycalib_radial', (anyRad.fx + anyRad.fy) / 2, vpPitch((anyRad.fx + anyRad.fy) / 2), vpYaw((anyRad.fx + anyRad.fy) / 2, vpPitch((anyRad.fx + anyRad.fy) / 2)), 'AnyCalib radial:1 f avg + VP', { fx: anyRad.fx, fy: anyRad.fy, k1: anyRad.k1 });
add('geocalib_median', geoMedian.fx, geoMedian.pitch_deg_down_positive * Math.PI / 180, vpYaw(geoMedian.fx, vpPitch(geoMedian.fx)), 'GeoCalib median.png', { geo_pitch_down_deg: geoMedian.pitch_deg_down_positive, geo_roll_deg: geoMedian.roll_deg, geo_unc_px: geoMedian.focal_uncertainty_px });
add('geocalib_sinkor', geoSinkor.fx, geoSinkor.pitch_deg_down_positive * Math.PI / 180, vpYaw(geoSinkor.fx, vpPitch(geoSinkor.fx)), 'GeoCalib frame sinkor', { geo_pitch_down_deg: geoSinkor.pitch_deg_down_positive, geo_roll_deg: geoSinkor.roll_deg, geo_unc_px: geoSinkor.focal_uncertainty_px });
add('geocalib_tema', geoTema.fx, geoTema.pitch_deg_down_positive * Math.PI / 180, vpYaw(geoTema.fx, vpPitch(geoTema.fx)), 'GeoCalib frame tema', { geo_pitch_down_deg: geoTema.pitch_deg_down_positive, geo_roll_deg: geoTema.roll_deg, geo_unc_px: geoTema.focal_uncertainty_px });
add('geocalib_multi_sinkor', geoMulti.f_median, geoMulti.pitch_deg_down_positive_median * Math.PI / 180, vpYaw(geoMulti.f_median, vpPitch(geoMulti.f_median)), 'GeoCalib multi shared f', { geo_pitch_down_deg: geoMulti.pitch_deg_down_positive_median, geo_roll_deg: geoMulti.roll_deg_median, geo_unc_px: geoMulti.focal_uncertainty_median });
add('geocalib_prior_f_median2', geoPriorMedian2.fx, geoPriorMedian2.pitch_deg_down_positive * Math.PI / 180, vpYaw(geoPriorMedian2.fx, vpPitch(geoPriorMedian2.fx)), 'GeoCalib prior f=1082.58 median2', { geo_pitch_down_deg: geoPriorMedian2.pitch_deg_down_positive, geo_roll_deg: geoPriorMedian2.roll_deg });
add('geocalib_prior_f_sinkor', geoPriorSinkor.fx, geoPriorSinkor.pitch_deg_down_positive * Math.PI / 180, vpYaw(geoPriorSinkor.fx, vpPitch(geoPriorSinkor.fx)), 'GeoCalib prior f=1082.58 sinkor', { geo_pitch_down_deg: geoPriorSinkor.pitch_deg_down_positive, geo_roll_deg: geoPriorSinkor.roll_deg });
add('anycalib_simple_sinkor', anySimpleSinkor.fx, vpPitch(anySimpleSinkor.fx), vpYaw(anySimpleSinkor.fx, vpPitch(anySimpleSinkor.fx)), 'AnyCalib frame sinkor + VP');
add('anycalib_simple_tema', anySimpleTema.fx, vpPitch(anySimpleTema.fx), vpYaw(anySimpleTema.fx, vpPitch(anySimpleTema.fx)), 'AnyCalib frame tema + VP');
add('anycalib_gen_simple_median2', anyGenSimple.fx, vpPitch(anyGenSimple.fx), vpYaw(anyGenSimple.fx, vpPitch(anyGenSimple.fx)), 'AnyCalib gen simple median2 + VP');
add('anycalib_gen_simple_tema', anyGenSimpleTema.fx, vpPitch(anyGenSimpleTema.fx), vpYaw(anyGenSimpleTema.fx, vpPitch(anyGenSimpleTema.fx)), 'AnyCalib gen simple tema + VP');
add('vp_only', base.f, vpPitch(base.f), vpYaw(base.f, vpPitch(base.f)), 'VP only with f=1082.6');

const free = solve({ ...base }, ['f', 'th', 'psi', 'h', 'Xp', 'Y0']);
methods.push({ name: 'free_fit', source: 'all 18 observations, w=3.60', input: {}, fixed_pose: summarize('free_fit', free, 'free'), fixed_f: null });

const result = {
  generated: new Date().toISOString(),
  anchor_w_m: W_FIX,
  vp,
  vp_pitch_deg_at_1082: deg(vpPitch(base.f)),
  vp_yaw_deg_at_1082: deg(vpYaw(base.f, vpPitch(base.f))),
  n_dashes: dashes.length,
  dashes,
  baseline: base,
  methods,
};
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(path.join(OUT, 'fits.json'), JSON.stringify(result, null, 2));

console.log('anchor w =', W_FIX, ' VP =', vp, ' n_dash =', dashes.length);
console.log('VP pitch/yaw at f=1082.6:', deg(vpPitch(base.f)).toFixed(3), deg(vpYaw(base.f, vpPitch(base.f))).toFixed(3));
for (const m of methods) {
  console.log('\n===', m.name, '|', m.source, '===');
  for (const mode of ['fixed_pose', 'fixed_f']) {
    const s = m[mode]; if (!s) continue;
    console.log(`${mode.padEnd(10)} f=${s.f.toFixed(2)} th=${s.th_deg.toFixed(3)} psi=${s.psi_deg.toFixed(3)} h=${s.h.toFixed(3)} RMS=${s.rms_px.toFixed(3)} dof=${s.dof}`);
  }
}
console.log('\nwrote', path.join(OUT, 'fits.json'));
