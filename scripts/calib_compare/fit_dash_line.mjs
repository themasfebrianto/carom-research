// Fit one or two dashed lane lines with known dash period/length and lane width.
// Optionally add a solid boundary one lane width away to make f identifiable.
// Usage:
//   node scripts/calib_compare/fit_dash_line.mjs --frame borr --dashes videos/frames/borr_sel.json --width 1024 --height 768 --period 13 --dash-length 5 --out videos/frames/borr_fit
//   node scripts/calib_compare/fit_dash_line.mjs --frame belmera_solid --dashes videos/frames/belmera_sel.json --width 1280 --height 720 --period 13 --dash-length 5 --lane-width 3.6 --solid videos/frames/belmera_solid_yellow.json --solid-offset -1 --out videos/frames/belmera_solid_fit --fixed-f 989.113 --scan-f 700:950:10
// --solid-offset is signed: -1 = one lane to the right of the dashed line,
// +1 = one lane to the left.  --scan-f fixes f over a range (a:b:step or a,b,c)
// and reports the re-optimised RMS; a flat curve means f is not identifiable.
import fs from 'node:fs';
import path from 'node:path';

const args = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const REPO = path.resolve(args.repo || process.cwd());
const FRAME = args.frame || 'frame';
const DASHES = path.resolve(REPO, args.dashes);
const OUT = path.resolve(REPO, args.out || `videos/frames/${FRAME}_fit`);
const W = Number(args.width || 1280);
const H = Number(args.height || 720);
const CX = W / 2, CY = H / 2;
const PERIOD = Number(args.period || 13);
const DASH = Number(args.dashLength ?? args['dash-length'] ?? 5);
const LANE_W = Number(args.laneWidth ?? args['lane-width'] ?? 3.6);
const N_LANES = Number(args.lanes || 1);
const SOLID = args.solid ? path.resolve(REPO, args.solid) : null;
// Signed offset of the solid line from the dashed line, in lane widths.
// -1 puts it one lane to the right of the dashed line (the usual edge line).
const SOLID_OFFSET = Number(args['solid-offset'] ?? args.solidOffset ?? -1);
const SOLID_WEIGHT = Number(args['solid-weight'] ?? 1);

const raw = JSON.parse(fs.readFileSync(DASHES, 'utf8'));
const dashes = raw
  .filter(d => Number(d.lane) < N_LANES)
  .map(d => ({
    lane: Number(d.lane), row: Number(d.row),
    yFar: Number(d.yFar), yNear: Number(d.yNear), u: Number(d.u),
  }))
  .sort((a, b) => a.lane - b.lane || a.row - b.row);
if (dashes.length < 3) {
  console.error(`need >=3 dashes, got ${dashes.length}`);
  process.exit(2);
}

const solid = SOLID
  ? JSON.parse(fs.readFileSync(SOLID, 'utf8')).map(p => ({ u: Number(p.u), v: Number(p.v) }))
  : [];

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
  for (const d of dashes) {
    const Y = p.Y0 - d.lane * LANE_W;
    const Xn = p.Xp + d.row * PERIOD;
    r.push(proj(p, Xn + DASH, Y).v - d.yFar);
    r.push(proj(p, Xn, Y).v - d.yNear);
    r.push(proj(p, Xn + DASH / 2, Y).u - d.u);
  }
  if (solid.length) {
    const Ys = p.Y0 + SOLID_OFFSET * LANE_W;
    // The solid line is infinite along X, so two points define its projection.
    const q1 = proj(p, 10, Ys);
    const q2 = proj(p, 100, Ys);
    if (q1.zc > 0 && q2.zc > 0) {
      let A = q2.v - q1.v, B = q1.u - q2.u;
      const C = -(A * q1.u + B * q1.v);
      const n = Math.hypot(A, B);
      if (n > 1e-9) {
        A /= n; B /= n;
        for (const s of solid) r.push(SOLID_WEIGHT * (A * s.u + B * s.v + C / n));
      }
    }
  }
  return r;
}
const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);
const rms = p => {
  const r = residuals(p);
  return Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
};

function solve(p0, keys = ['f', 'th', 'psi', 'h', 'Xp', 'Y0'], iters = 1200) {
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

function covariance(p, keys) {
  const r = residuals(p);
  const m = r.length, n = keys.length;
  if (m <= n) return null;
  const J = r.map(() => keys.map(() => 0));
  for (let k = 0; k < n; k++) {
    const dp = { ...p }, eps = Math.max(1e-7, Math.abs(p[keys[k]]) * 1e-6);
    dp[keys[k]] += eps;
    const r2 = residuals(dp);
    for (let i = 0; i < m; i++) J[i][k] = (r2[i] - r[i]) / eps;
  }
  const A = Array.from({ length: n }, () => Array(n).fill(0));
  for (let i = 0; i < m; i++) for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b];
  const M = A.map((row, i) => [...row, ...Array.from({ length: n }, (_, j) => i === j ? 1 : 0)]);
  for (let c = 0; c < n; c++) {
    let pv = c;
    for (let t = c + 1; t < n; t++) if (Math.abs(M[t][c]) > Math.abs(M[pv][c])) pv = t;
    if (Math.abs(M[pv][c]) < 1e-12) return null;
    [M[c], M[pv]] = [M[pv], M[c]];
    const d0 = M[c][c];
    for (let j = 0; j < 2 * n; j++) M[c][j] /= d0;
    for (let t = 0; t < n; t++) {
      if (t === c) continue;
      const f0 = M[t][c];
      for (let j = 0; j < 2 * n; j++) M[t][j] -= f0 * M[c][j];
    }
  }
  const inv = M.map(row => row.slice(n));
  const sigma2 = r.reduce((s, x) => s + x * x, 0) / (m - n);
  const std = {};
  keys.forEach((k, i) => { std[k] = Math.sqrt(Math.max(0, sigma2 * inv[i][i])); });
  return { sigma_px: Math.sqrt(sigma2), dof: m - n, std, cov: inv.map(row => row.map(v => sigma2 * v)) };
}

const starts = [];
for (const f0 of [W * 0.8, W * 1.2, W * 1.8, W * 2.5]) {
  for (const th0 of [0.03, 0.08, 0.15, 0.25]) {
    for (const h0 of [5, 8, 12]) {
      for (const Xp0 of [5, 15, 30]) {
        for (const Y0 of [0, 5, -5]) {
          starts.push({ f: f0, th: th0, psi: 0, h: h0, Xp: Xp0, Y0 });
        }
      }
    }
  }
}
let best = null;
for (const s of starts) {
  const p = solve(s, ['f', 'th', 'psi', 'h', 'Xp', 'Y0'], 500);
  const r = rms(p);
  if (!Number.isFinite(r)) continue;
  if (p.f < 100 || p.f > 30000 || p.h < 0.5 || p.h > 60 || Math.abs(p.th) > 1.45 || Math.abs(p.psi) > 1.45) continue;
  if (!best || r < best.rms) best = { p, rms: r };
}
if (!best) { console.error('no physical solution'); process.exit(2); }
const p = best.p;
const deg = x => x * 180 / Math.PI;
let fixed = null;
if (args['fixed-f']) {
  const fFix = Number(args['fixed-f']);
  const pFix = solve({ ...p, f: fFix }, ['th', 'psi', 'h', 'Xp', 'Y0'], 1200);
  fixed = {
    f: fFix,
    pitch_deg: deg(pFix.th), yaw_deg: deg(pFix.psi), h_m: pFix.h,
    rms_px: rms(pFix),
  };
}

let scan = null;
if (args['scan-f']) {
  const spec = args['scan-f'];
  const list = [];
  if (spec.includes(':')) {
    const [a, b, st] = spec.split(':').map(Number);
    for (let f = a; f <= b + 1e-9; f += st) list.push(Number(f.toFixed(3)));
  } else {
    list.push(...spec.split(',').map(Number));
  }
  // Solve outward from the free-fit f so each fixed-f solve starts nearby.
  list.sort((a, b) => Math.abs(a - p.f) - Math.abs(b - p.f));
  const solved = new Map([[p.f, p]]);
  scan = [];
  for (const fFix of list) {
    let start = p, bestd = Infinity;
    for (const [fk, pk] of solved) {
      const d = Math.abs(fk - fFix);
      if (d < bestd) { bestd = d; start = pk; }
    }
    const pFix = solve({ ...start, f: fFix }, ['th', 'psi', 'h', 'Xp', 'Y0'], 1200);
    solved.set(fFix, pFix);
    scan.push({ f: fFix, rms_px: rms(pFix), pitch_deg: deg(pFix.th), yaw_deg: deg(pFix.psi), h_m: pFix.h });
  }
  scan.sort((a, b) => a.f - b.f);
}
const cov = covariance(p, ['f', 'th', 'psi', 'h', 'Xp', 'Y0']);

const res = {
  frame: FRAME, dashes: dashes.length, image_width: W, image_height: H,
  anchor_w_m: LANE_W, period_m: PERIOD, dash_length_m: DASH,
  f: p.f, pitch_deg: deg(p.th), yaw_deg: deg(p.psi), h_m: p.h, Xp_m: p.Xp, Y0_m: p.Y0,
  rms_px: best.rms, f_th: p.f * p.th, f_h: p.f * p.h, f_w: p.f * LANE_W,
  hfov_deg: deg(2 * Math.atan(CX / p.f)),
  solid_points: solid.length, solid_offset_lanes: SOLID_OFFSET,
  fixed_f: fixed,
  scan_f: scan,
  covariance: cov,
  observations: dashes,
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(`${OUT}.json`, JSON.stringify(res, null, 2));
const cols = ['frame', 'dashes', 'solid_points', 'f', 'pitch_deg', 'yaw_deg', 'h_m', 'rms_px', 'period_m', 'dash_length_m', 'anchor_w_m', 'f_sigma'];
const fSigma = cov ? cov.std.f : NaN;
fs.writeFileSync(`${OUT}.csv`, [cols.join(','), [FRAME, dashes.length, solid.length, p.f.toFixed(3), deg(p.th).toFixed(4), deg(p.psi).toFixed(4), p.h.toFixed(4), best.rms.toFixed(4), PERIOD, DASH, LANE_W, Number.isFinite(fSigma) ? fSigma.toFixed(3) : ''].join(',')].join('\n') + '\n');
if (scan) {
  const scols = ['f', 'rms_px', 'pitch_deg', 'yaw_deg', 'h_m'];
  fs.writeFileSync(`${OUT}_scan.csv`, [scols.join(','), ...scan.map(s => [s.f, s.rms_px.toFixed(4), s.pitch_deg.toFixed(4), s.yaw_deg.toFixed(4), s.h_m.toFixed(4)].join(','))].join('\n') + '\n');
}
console.log(`frame=${FRAME} dashes=${dashes.length} solid=${solid.length} f=${p.f.toFixed(2)} pitch=${deg(p.th).toFixed(3)} yaw=${deg(p.psi).toFixed(3)} h=${p.h.toFixed(3)} RMS=${best.rms.toFixed(3)}`);
if (cov) console.log(`  sigma f=${cov.std.f.toFixed(2)} (${(100 * cov.std.f / p.f).toFixed(2)}%) pitch=${(cov.std.th * 180 / Math.PI).toFixed(3)} deg h=${cov.std.h.toFixed(3)} m`);
if (fixed) console.log(`  fixed f=${fixed.f.toFixed(2)} -> pitch=${fixed.pitch_deg.toFixed(3)} yaw=${fixed.yaw_deg.toFixed(3)} h=${fixed.h_m.toFixed(3)} RMS=${fixed.rms_px.toFixed(3)}`);
if (scan) {
  const base = scan.reduce((a, b) => b.rms_px < a.rms_px ? b : a);
  console.log(`  scan f: best f=${base.f.toFixed(2)} RMS=${base.rms_px.toFixed(3)}; range ${scan[0].f}..${scan[scan.length - 1].f}`);
}
console.log(`wrote ${OUT}.csv and ${OUT}.json`);
