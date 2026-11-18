// Calibration with pixel-consistent residuals.
import fs from 'node:fs';
const t = JSON.parse(fs.readFileSync('f2/tracked.json'));
const YEL = t.YEL.filter(p => p[1] <= 266);
const RED = t.RED.filter(p => p[1] >= 275);
const W = 480, H = 360, CX = W / 2, CY = H / 2;
const DASH = [
  { row: 0, near: 345, far: 297, u: 102.4 },
  { row: 1, near: 185, far: 165, u: 359.0 },
];
const PERIOD = 13, LEN = 5;

function basis(p) {
  const cp = Math.cos(p.th), sp = Math.sin(p.th), cw = Math.cos(p.psi), sw = Math.sin(p.psi);
  const fw = [cp * cw, cp * sw, -sp], rw = [sw, -cw, 0];
  const dw = [-sp * cw, -sp * sw, -cp];
  return { fw, rw, dw };
}
function proj(p, X, Y) {
  const { fw, rw, dw } = basis(p);
  const d = [X, Y, -p.h];
  const xc = rw[0] * d[0] + rw[1] * d[1] + rw[2] * d[2];
  const yc = dw[0] * d[0] + dw[1] * d[1] + dw[2] * d[2];
  const zc = fw[0] * d[0] + fw[1] * d[1] + fw[2] * d[2];
  return { u: CX + p.f * xc / zc, v: CY + p.f * yc / zc, zc };
}
function backProject(p, u, v) {
  const { fw, rw, dw } = basis(p);
  const xn = (u - CX) / p.f, yn = (v - CY) / p.f;
  const d = [
    rw[0] * xn + dw[0] * yn + fw[0],
    rw[1] * xn + dw[1] * yn + fw[1],
    rw[2] * xn + dw[2] * yn + fw[2]
  ];
  if (Math.abs(d[2]) < 1e-9) return null;
  const s = -p.h / d[2];
  if (s <= 0) return null;
  return { X: d[0] * s, Y: d[1] * s, z: Math.hypot(d[0] * s, d[1] * s) };
}

function residuals(p) {
  const r = [];
  for (const [u, v] of YEL) {
    const q = backProject(p, u, v);
    if (q) r.push((q.Y - p.Yyel) * p.f / q.z);      // lateral metres -> pixels
  }
  for (const [u, v] of RED) {
    const q = backProject(p, u, v);
    if (q) r.push((q.Y - p.Yred) * p.f / q.z);
  }
  for (const d of DASH) {
    const Xn = p.Xp + d.row * PERIOD;
    r.push(proj(p, Xn + LEN, p.Ydash).v - d.far);
    r.push(proj(p, Xn, p.Ydash).v - d.near);
    r.push(proj(p, Xn + LEN / 2, p.Ydash).u - d.u);
  }
  return r;
}
const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);
const keys = ['f', 'th', 'psi', 'h', 'Yyel', 'Yred', 'Ydash', 'Xp'];

function solve(p0, iters = 2000) {
  let p = { ...p0 }, lam = 1e-2;
  for (let it = 0; it < iters; it++) {
    const r = residuals(p);
    const J = r.map(() => keys.map(() => 0));
    for (let k = 0; k < keys.length; k++) {
      const dp = { ...p }, eps = Math.max(1e-7, Math.abs(p[keys[k]]) * 1e-6); dp[keys[k]] += eps;
      const r2 = residuals(dp);
      for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / eps;
    }
    const n = keys.length, A = Array.from({ length: n }, () => Array(n).fill(0)), g = Array(n).fill(0);
    for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) { g[a] += J[i][a] * r[i]; for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b]; }
    for (let a = 0; a < n; a++) A[a][a] *= (1 + lam);
    const M = A.map((row, i) => [...row, -g[i]]);
    for (let c = 0; c < n; c++) {
      let pv = c; for (let q = c + 1; q < n; q++) if (Math.abs(M[q][c]) > Math.abs(M[pv][c])) pv = q;
      [M[c], M[pv]] = [M[pv], M[c]];
      const d0 = M[c][c]; if (Math.abs(d0) < 1e-14) continue;
      for (let j = c; j <= n; j++) M[c][j] /= d0;
      for (let q = 0; q < n; q++) { if (q === c) continue; const f0 = M[q][c]; for (let j = c; j <= n; j++) M[q][j] -= f0 * M[c][j]; }
    }
    const dx = M.map(row => row[n]); const pn = { ...p }; keys.forEach((k, i) => pn[k] += dx[i]);
    if (cost(pn) < cost(p)) { p = pn; lam = Math.max(lam * 0.3, 1e-10); } else lam *= 3;
  }
  return p;
}

const p0 = { f: 421, th: 15 * Math.PI / 180, psi: 35 * Math.PI / 180, h: 8, Yyel: -5, Yred: 2, Ydash: -1.5, Xp: 20 };
let p = solve(p0);
const r = residuals(p);
const rms = Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
console.log('obs=%d params=%d dof=%d rms=%.2f px', r.length, keys.length, r.length - keys.length, rms);
for (const k of keys) console.log('  %s = %s', k.padEnd(6), p[k].toFixed(3));
console.log('\npitch=%s deg  yaw=%s deg  HFOV=%s deg  horizon=%s px',
  (p.th * 180 / Math.PI).toFixed(2), (p.psi * 180 / Math.PI).toFixed(2),
  (2 * Math.atan(CX / p.f) * 180 / Math.PI).toFixed(1), (CY - p.f * Math.tan(p.th)).toFixed(1));
console.log('lebar lajur kiri %s m, kanan %s m, total %s m',
  Math.abs(p.Ydash - p.Yyel).toFixed(2), Math.abs(p.Yred - p.Ydash).toFixed(2), Math.abs(p.Yred - p.Yyel).toFixed(2));
fs.writeFileSync('f2/calib_480.json', JSON.stringify(p, null, 1));

// degeneracy check: pin h, see how the others move
console.log('\nuji degenerasi (h dipaku):');
for (const hh of [5, 7, 9, 11, 14]) {
  const q = solve({ ...p, h: hh });
  const rr = residuals(q);
  console.log('  h=%d -> f=%s yaw=%s w_total=%s rms=%s', hh, q.f.toFixed(0), (q.psi * 180 / Math.PI).toFixed(1),
    Math.abs(q.Yred - q.Yyel).toFixed(2), Math.sqrt(rr.reduce((s, x) => s + x * x, 0) / rr.length).toFixed(2));
}
