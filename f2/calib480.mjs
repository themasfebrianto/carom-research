// Full calibration using the near-field geometry:
//   - two straight ground lines (yellow, right edge) at unknown constant Y
//   - two dashes on a third line (longitudinal metric anchor: 13 m)
import fs from 'node:fs';
const t = JSON.parse(fs.readFileSync('f2/tracked.json'));
const YEL = t.YEL.filter(p => p[1] <= 266);
const RED = t.RED.filter(p => p[1] >= 275);

const W = 480, H = 360, CX = W / 2, CY = H / 2;
// dashes (measured from the median)
const DASH = [
  { row: 0, near: 345, far: 297, u: 102.4 },
  { row: 1, near: 185, far: 165, u: 359.0 },
];
const PERIOD = 13, LEN = 5;

function proj(p, X, Y) {
  const { f, th, psi, h } = p;
  const cp = Math.cos(th), sp = Math.sin(th), cw = Math.cos(psi), sw = Math.sin(psi);
  const fw = [cp * cw, cp * sw, -sp], rw = [sw, -cw, 0];
  const dw = [fw[1] * rw[2] - fw[2] * rw[1], fw[2] * rw[0] - fw[0] * rw[2], fw[0] * rw[1] - fw[1] * rw[0]];
  const dx = X, dy = Y, dz = -h;
  const xc = rw[0] * dx + rw[1] * dy + rw[2] * dz;
  const yc = dw[0] * dx + dw[1] * dy + dw[2] * dz;
  const zc = fw[0] * dx + fw[1] * dy + fw[2] * dz;
  return { u: CX + f * xc / zc, v: CY + f * yc / zc };
}
// back-project a pixel to the ground plane, return Y
function groundY(p, u, v) {
  const { f, th, psi, h } = p;
  const cp = Math.cos(th), sp = Math.sin(th), cw = Math.cos(psi), sw = Math.sin(psi);
  const fw = [cp * cw, cp * sw, -sp], rw = [sw, -cw, 0];
  const dw = [fw[1] * rw[2] - fw[2] * rw[1], fw[2] * rw[0] - fw[0] * rw[2], fw[0] * rw[1] - fw[1] * rw[0]];
  const xn = (u - CX) / f, yn = (v - CY) / f;
  // camera ray (xn, yn, 1) -> world via R^T
  const dc = [xn, yn, 1];
  const dx = rw[0] * dc[0] + dw[0] * dc[1] + fw[0] * dc[2];
  const dy = rw[1] * dc[0] + dw[1] * dc[1] + fw[1] * dc[2];
  const dz = rw[2] * dc[0] + dw[2] * dc[1] + fw[2] * dc[2];
  if (Math.abs(dz) < 1e-9) return null;
  const s = -h / dz;
  if (s <= 0) return null;
  return dy * s;
}

function residuals(p) {
  const r = [];
  for (const [u, v] of YEL) { const Y = groundY(p, u, v); if (Y !== null) r.push((Y - p.Yyel) * 8); }
  for (const [u, v] of RED) { const Y = groundY(p, u, v); if (Y !== null) r.push((Y - p.Yred) * 8); }
  for (const d of DASH) {
    const Xn = p.Xp + d.row * PERIOD, Xf = Xn + LEN;
    r.push(proj(p, Xf, p.Ydash).v - d.far);
    r.push(proj(p, Xn, p.Ydash).v - d.near);
    r.push(proj(p, Xn + LEN / 2, p.Ydash).u - d.u);
  }
  return r;
}
const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);
const keys = ['f', 'th', 'psi', 'h', 'Yyel', 'Yred', 'Ydash', 'Xp'];
let p = { f: 420, th: 14 * Math.PI / 180, psi: 30 * Math.PI / 180, h: 8, Yyel: -6, Yred: 2, Ydash: -2, Xp: 20 };
let lam = 1e-2;
for (let it = 0; it < 1500; it++) {
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
const r = residuals(p);
const rms = Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
console.log('obs=%d params=%d dof=%d  rms=%.3f', r.length, keys.length, r.length - keys.length, rms);
for (const k of keys) console.log('  %s = %s', k.padEnd(6), p[k].toFixed(4));
console.log('\npitch=%s deg  yaw=%s deg  HFOV=%s deg  horizon=%s px',
  (p.th * 180 / Math.PI).toFixed(2), (p.psi * 180 / Math.PI).toFixed(2),
  (2 * Math.atan(CX / p.f) * 180 / Math.PI).toFixed(1),
  (CY - p.f * Math.tan(p.th)).toFixed(1));
console.log('Y: kuning %s, dash %s, tepi %s  (lebar lajur kiri %s m, kanan %s m)',
  p.Yyel.toFixed(2), p.Ydash.toFixed(2), p.Yred.toFixed(2),
  Math.abs(p.Ydash - p.Yyel).toFixed(2), Math.abs(p.Yred - p.Ydash).toFixed(2));
fs.writeFileSync('f2/calib_480.json', JSON.stringify(p, null, 1));
