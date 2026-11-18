// Fit with w pinned to 3.60 m (Bina Marga), everything else free.
import fs from 'node:fs';
const CX = 640, CY = 360;
const obs = [
  { lane: 0, row: 0, yFar: 636.12, yNear: 698.92, u: 265.3 },
  { lane: 0, row: 1, yFar: 539.28, yNear: 568.67, u: 387.8 },
  { lane: 0, row: 2, yFar: 485.91, yNear: 503.44, u: 450.6 },
  { lane: 1, row: 0, yFar: 632.84, yNear: 696.99, u: 407.3 },
  { lane: 1, row: 1, yFar: 536.70, yNear: 567.03, u: 484.2 },
  { lane: 1, row: 2, yFar: 484.26, yNear: 501.60, u: 521.9 },
];
const W_FIX = 3.60, PERIOD = 13, DASH = 5;

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
function residuals(p) {
  const r = [];
  for (const o of obs) {
    const Y = p.Y0 - o.lane * W_FIX;
    const Xn = p.Xp + o.row * PERIOD;
    r.push(proj(p, Xn + DASH, Y).v - o.yFar);
    r.push(proj(p, Xn, Y).v - o.yNear);
    r.push(proj(p, Xn + DASH / 2, Y).u - o.u);
  }
  return r;
}
const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);
const keys = ['f', 'th', 'psi', 'h', 'Xp', 'Y0'];
let p = { f: 1083, th: 2.45 * Math.PI / 180, psi: 0.0044, h: 8.9, Xp: 24.7, Y0: 9.57 }, lam = 1e-2;
for (let it = 0; it < 800; it++) {
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
    let pv = c; for (let t = c + 1; t < n; t++) if (Math.abs(M[t][c]) > Math.abs(M[pv][c])) pv = t;
    [M[c], M[pv]] = [M[pv], M[c]];
    const d0 = M[c][c]; if (Math.abs(d0) < 1e-14) continue;
    for (let j = c; j <= n; j++) M[c][j] /= d0;
    for (let t = 0; t < n; t++) { if (t === c) continue; const f0 = M[t][c]; for (let j = c; j <= n; j++) M[t][j] -= f0 * M[c][j]; }
  }
  const dx = M.map(row => row[n]); const pn = { ...p }; keys.forEach((k, i) => pn[k] += dx[i]);
  if (cost(pn) < cost(p)) { p = pn; lam = Math.max(lam * 0.3, 1e-10); } else lam *= 3;
}
const r = residuals(p);
console.log('=== w pinned at 3.60 m ===');
for (const k of keys) console.log(`  ${k} = ${p[k].toFixed(5)}`);
console.log(`  pitch = ${(p.th * 180 / Math.PI).toFixed(3)} deg   yaw = ${(p.psi * 180 / Math.PI).toFixed(3)} deg`);
console.log(`  RMS = ${Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length).toFixed(3)} px   dof = ${r.length - keys.length}`);
console.log('\nper-dash residuals:');
for (const o of obs) {
  const Y = p.Y0 - o.lane * W_FIX, Xn = p.Xp + o.row * PERIOD;
  console.log(`  lane${o.lane} row${o.row}: dvFar=${(proj(p, Xn + 5, Y).v - o.yFar).toFixed(2).padStart(6)} dvNear=${(proj(p, Xn, Y).v - o.yNear).toFixed(2).padStart(6)} du=${(proj(p, Xn + 2.5, Y).u - o.u).toFixed(2).padStart(6)}`);
}
const XofV = v => { let lo = 1, hi = 400; for (let k = 0; k < 100; k++) { const m = (lo + hi) / 2; if (proj(p, m, 0).v > v) lo = m; else hi = m; } return (lo + hi) / 2; };
console.log('\nrow -> distance:');
for (const v of [719, 666, 553, 494, 430, 400, 380]) console.log(`  v=${v} -> ${XofV(v).toFixed(1)} m`);
console.log(`\nhorizon = ${(CY - p.f * Math.tan(p.th)).toFixed(1)} px ; HFOV = ${(2 * Math.atan(CX / p.f) * 180 / Math.PI).toFixed(1)} deg`);
