// Calibration v3: yellow line + dashed line only (right edge excluded).
// Dashes detected precisely, then 7-parameter fit with VP constraint + covariance.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const d = buf.subarray(off);
const lum = (x, y) => { const o = (y * W + x) * 3; return 0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2]; };

// --- precise dash blobs
const dNear = { u: 102.4, y0: 297, y1: 345 };
const dFar = { u: 359.0, y0: 165, y1: 185 };
console.log('dash dekat: u=%s v=%s  y %d..%d', dNear.u, (dNear.y0 + dNear.y1) / 2, dNear.y0, dNear.y1);
console.log('dash jauh : u=%s v=%s  y %d..%d', dFar.u, (dFar.y0 + dFar.y1) / 2, dFar.y0, dFar.y1);

const YEL = JSON.parse(fs.readFileSync('f2/tracked.json')).YEL.filter(p => p[1] <= 266);
const CX = W / 2, CY = H / 2;
const DASH = [
  { row: 0, near: dNear.y1, far: dNear.y0, u: dNear.u },
  { row: 1, near: dFar.y1, far: dFar.y0, u: dFar.u },
];
const PERIOD = 13, LEN = 5, VPOBS = { u: 562.5, v: 60.0 };

const KEYS = ['f', 'th', 'psi', 'h', 'Yyel', 'Ydash', 'Xp'];
const B = { f: [200, 3000], th: [0.02, 0.9], psi: [0.05, 1.4], h: [3, 30], Yyel: [-40, 40], Ydash: [-40, 40], Xp: [2, 120] };
const clamp = p => { for (const k of KEYS) p[k] = Math.min(B[k][1], Math.max(B[k][0], p[k])); return p; };

function basis(p) {
  const cp = Math.cos(p.th), sp = Math.sin(p.th), cw = Math.cos(p.psi), sw = Math.sin(p.psi);
  return { fw: [cp * cw, cp * sw, -sp], rw: [sw, -cw, 0], dw: [-sp * cw, -sp * sw, -cp] };
}
function proj(p, X, Y) {
  const { fw, rw, dw } = basis(p); const v = [X, Y, -p.h];
  const xc = rw[0] * v[0] + rw[1] * v[1] + rw[2] * v[2];
  const yc = dw[0] * v[0] + dw[1] * v[1] + dw[2] * v[2];
  const zc = fw[0] * v[0] + fw[1] * v[1] + fw[2] * v[2];
  return { u: CX + p.f * xc / zc, v: CY + p.f * yc / zc };
}
function back(p, u, v) {
  const { fw, rw, dw } = basis(p);
  const xn = (u - CX) / p.f, yn = (v - CY) / p.f;
  const dx = rw[0] * xn + dw[0] * yn + fw[0], dy = rw[1] * xn + dw[1] * yn + fw[1], dz = rw[2] * xn + dw[2] * yn + fw[2];
  if (dz > -1e-6) return null;
  const s = -p.h / dz, X = dx * s, Y = dy * s, z = Math.hypot(X, Y);
  return (z < 3 || z > 400) ? null : { X, Y, z };
}
function residuals(p) {
  const r = [];
  for (const [u, v] of YEL) { const q = back(p, u, v); if (q) r.push((q.Y - p.Yyel) * p.f / q.z); }
  for (const q of DASH) {
    const Xn = p.Xp + q.row * PERIOD;
    r.push(proj(p, Xn + LEN, p.Ydash).v - q.far);
    r.push(proj(p, Xn, p.Ydash).v - q.near);
    r.push(proj(p, Xn + LEN / 2, p.Ydash).u - q.u);
  }
  r.push(2 * ((CY - p.f * Math.tan(p.th)) - VPOBS.v));
  r.push(2 * ((CX + p.f * Math.tan(p.psi) / Math.cos(p.th)) - VPOBS.u));
  return r;
}
const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);

function solve(p0, iters = 1200) {
  let p = clamp({ ...p0 }), lam = 1e-3;
  for (let it = 0; it < iters; it++) {
    const r = residuals(p); const J = r.map(() => KEYS.map(() => 0));
    for (let k = 0; k < KEYS.length; k++) {
      const dp = { ...p }, e = Math.max(1e-7, Math.abs(p[KEYS[k]]) * 1e-6); dp[KEYS[k]] += e;
      const r2 = residuals(dp);
      for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / e;
    }
    const n = KEYS.length, A = Array.from({ length: n }, () => Array(n).fill(0)), g = Array(n).fill(0);
    for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) { g[a] += J[i][a] * r[i]; for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b]; }
    for (let a = 0; a < n; a++) A[a][a] *= (1 + lam);
    const M = A.map((row, i) => [...row, -g[i]]);
    for (let c = 0; c < n; c++) {
      let pv = c; for (let q = c + 1; q < n; q++) if (Math.abs(M[q][c]) > Math.abs(M[pv][c])) pv = q;
      if (Math.abs(M[pv][c]) < 1e-12) { lam *= 10; continue; }
      [M[c], M[pv]] = [M[pv], M[c]];
      const d0 = M[c][c];
      for (let j = c; j <= n; j++) M[c][j] /= d0;
      for (let q = 0; q < n; q++) { if (q === c) continue; const f0 = M[q][c]; for (let j = c; j <= n; j++) M[q][j] -= f0 * M[c][j]; }
    }
    const dx = M.map(row => row[n]); const pn = { ...p }; KEYS.forEach((k, i) => pn[k] += dx[i]); clamp(pn);
    if (cost(pn) < cost(p)) { p = pn; lam = Math.max(lam * 0.3, 1e-10); } else lam *= 3;
  }
  return p;
}

let best = null;
for (const f0 of [250, 350, 450, 600, 800, 1100, 1500]) for (const h0 of [4, 7, 10, 14]) {
  const th0 = Math.atan((CY - VPOBS.v) / f0), psi0 = Math.atan((VPOBS.u - CX) * Math.cos(th0) / f0);
  const p = solve({ f: f0, th: th0, psi: psi0, h: h0, Yyel: -8, Ydash: -4, Xp: 12 });
  const c = cost(p);
  if (!best || c < best.c) best = { p, c };
}
const p = best.p, r = residuals(p);
const rms = Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
console.log('\n=== FIT (kuning + putus-putus saja) ===');
console.log(`obs=${r.length} params=${KEYS.length} dof=${r.length - KEYS.length} rms=${rms.toFixed(2)} px`);
{
  const rmsOf = a => Math.sqrt(a.reduce((s, x) => s + x * x, 0) / a.length).toFixed(2);
  const yR = r.slice(0, YEL.length);
  const dR = r.slice(YEL.length, YEL.length + 6);
  const vpR = r.slice(-2);
  console.log(`  kuning rms=${rmsOf(yR)}  dash rms=${rmsOf(dR)}  VP rms=${rmsOf(vpR)}`);
  console.log(`  dash residuals: ${dR.map(x => x.toFixed(1)).join(' ')}`);
  console.log(`  VP residuals  : ${vpR.map(x => x.toFixed(1)).join(' ')}`);
}
for (const k of KEYS) console.log('  %s = %s', k.padEnd(6), p[k].toFixed(3));
console.log('\npitch %s deg | yaw %s deg | HFOV %s deg', (p.th * 180 / Math.PI).toFixed(2), (p.psi * 180 / Math.PI).toFixed(2), (2 * Math.atan(CX / p.f) * 180 / Math.PI).toFixed(1));
console.log('lebar lajur (kuning -> putus-putus) = %s m', Math.abs(p.Ydash - p.Yyel).toFixed(2));

// covariance
const J = r.map(() => KEYS.map(() => 0));
for (let k = 0; k < KEYS.length; k++) {
  const dp = { ...p }, e = Math.max(1e-7, Math.abs(p[KEYS[k]]) * 1e-6); dp[KEYS[k]] += e;
  const r2 = residuals(dp);
  for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / e;
}
const n = KEYS.length, A = Array.from({ length: n }, () => Array(n).fill(0));
for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b];
const M = A.map((row, i) => [...row, ...Array.from({ length: n }, (_, j) => i === j ? 1 : 0)]);
for (let c = 0; c < n; c++) {
  let pv = c; for (let q = c + 1; q < n; q++) if (Math.abs(M[q][c]) > Math.abs(M[pv][c])) pv = q;
  [M[c], M[pv]] = [M[pv], M[c]];
  const d0 = M[c][c];
  for (let j = 0; j < 2 * n; j++) M[c][j] /= d0;
  for (let q = 0; q < n; q++) { if (q === c) continue; const f0 = M[q][c]; for (let j = 0; j < 2 * n; j++) M[q][j] -= f0 * M[c][j]; }
}
const s2 = r.reduce((s, x) => s + x * x, 0) / (r.length - KEYS.length);
console.log('\n1 sigma:');
KEYS.forEach((k, i) => console.log('  %s = %s +- %s', k.padEnd(6), p[k].toFixed(2), Math.sqrt(Math.max(M[i][n + i], 0) * s2).toFixed(2)));

console.log('\nuji degenerasi (h dipaku):');
for (const hh of [5, 7, 9, 12, 16]) {
  const q = solve({ ...p, h: hh });
  const rr = residuals(q);
  console.log('  h=%2d -> f=%s  w=%s m  rms=%s', hh, q.f.toFixed(0), Math.abs(q.Ydash - q.Yyel).toFixed(2),
    Math.sqrt(rr.reduce((s, x) => s + x * x, 0) / rr.length).toFixed(2));
}
