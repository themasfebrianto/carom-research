// Fit one or two dashed lane lines with known dash period/length and lane width.
// Usage:
//   node scripts/calib_compare/fit_dash_line.mjs --frame borr --dashes videos/frames/borr_sel.json --width 1024 --height 768 --period 13 --dash-length 5 --out videos/frames/borr_fit
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
const DASH = Number(args.dashLength || 5);
const LANE_W = Number(args.laneWidth || 3.6);
const N_LANES = Number(args.lanes || 1);

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
const res = {
  frame: FRAME, dashes: dashes.length, image_width: W, image_height: H,
  anchor_w_m: LANE_W, period_m: PERIOD, dash_length_m: DASH,
  f: p.f, pitch_deg: deg(p.th), yaw_deg: deg(p.psi), h_m: p.h, Xp_m: p.Xp, Y0_m: p.Y0,
  rms_px: best.rms, f_th: p.f * p.th, f_h: p.f * p.h, f_w: p.f * LANE_W,
  hfov_deg: deg(2 * Math.atan(CX / p.f)),
  fixed_f: fixed,
  observations: dashes,
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(`${OUT}.json`, JSON.stringify(res, null, 2));
const cols = ['frame', 'dashes', 'f', 'pitch_deg', 'yaw_deg', 'h_m', 'rms_px', 'period_m', 'dash_length_m', 'anchor_w_m'];
fs.writeFileSync(`${OUT}.csv`, [cols.join(','), [FRAME, dashes.length, p.f.toFixed(3), deg(p.th).toFixed(4), deg(p.psi).toFixed(4), p.h.toFixed(4), best.rms.toFixed(4), PERIOD, DASH, LANE_W].join(',')].join('\n') + '\n');
console.log(`frame=${FRAME} dashes=${dashes.length} f=${p.f.toFixed(2)} pitch=${deg(p.th).toFixed(3)} yaw=${deg(p.psi).toFixed(3)} h=${p.h.toFixed(3)} RMS=${best.rms.toFixed(3)}`);
if (fixed) console.log(`  fixed f=${fixed.f.toFixed(2)} -> pitch=${fixed.pitch_deg.toFixed(3)} yaw=${fixed.yaw_deg.toFixed(3)} h=${fixed.h_m.toFixed(3)} RMS=${fixed.rms_px.toFixed(3)}`);
console.log(`wrote ${OUT}.csv and ${OUT}.json`);
