// Robust calibration of the 480x360 clip.
// Residuals all in PIXELS. Bounded LM with multi-start. Reports covariance.
import fs from 'node:fs';
const t = JSON.parse(fs.readFileSync('f2/tracked.json'));
const YEL = t.YEL.filter(p => p[1] <= 266);
const RED = t.RED.filter(p => p[1] >= 275);
const W = 480, H = 360, CX = W / 2, CY = H / 2;
const DASH = [
  { row: 0, near: 345.0, far: 297.0, u: 102.4 },
  { row: 1, near: 185.0, far: 165.0, u: 359.0 },
];
const PERIOD = 13, LEN = 5;
const VP_OBS = { u: 549.0, v: 67.0 };

const KEYS = ['f', 'th', 'psi', 'h', 'Yyel', 'Yred', 'Ydash', 'Xp'];
const BOUND = {
  f: [250, 2500], th: [0.02, 0.8], psi: [0.05, 1.3], h: [3, 30],
  Yyel: [-40, 40], Yred: [-40, 40], Ydash: [-40, 40], Xp: [5, 90]
};

function basis(p) {
  const cp = Math.cos(p.th), sp = Math.sin(p.th), cw = Math.cos(p.psi), sw = Math.sin(p.psi);
  return { fw: [cp * cw, cp * sw, -sp], rw: [sw, -cw, 0], dw: [-sp * cw, -sp * sw, -cp] };
}
function proj(p, X, Y) {
  const { fw, rw, dw } = basis(p);
  const d = [X, Y, -p.h];
  const xc = rw[0] * d[0] + rw[1] * d[1] + rw[2] * d[2];
  const yc = dw[0] * d[0] + dw[1] * d[1] + dw[2] * d[2];
  const zc = fw[0] * d[0] + fw[1] * d[1] + fw[2] * d[2];
  return { u: CX + p.f * xc / zc, v: CY + p.f * yc / zc };
}
function back(p, u, v) {
  const { fw, rw, dw } = basis(p);
  const xn = (u - CX) / p.f, yn = (v - CY) / p.f;
  const dx = rw[0] * xn + dw[0] * yn + fw[0];
  const dy = rw[1] * xn + dw[1] * yn + fw[1];
  const dz = rw[2] * xn + dw[2] * yn + fw[2];
  if (dz > -1e-6) return null;
  const s = -p.h / dz;
  const X = dx * s, Y = dy * s;
  const z = Math.hypot(X, Y);
  if (!isFinite(z) || z < 3 || z > 400) return null;
  return { X, Y, z };
}
function residuals(p) {
  const r = [];
  for (const [u, v] of YEL) { const q = back(p, u, v); if (q) r.push((q.Y - p.Yyel) * p.f / q.z); }
  for (const [u, v] of RED) { const q = back(p, u, v); if (q) r.push((q.Y - p.Yred) * p.f / q.z); }
  for (const d of DASH) {
    const Xn = p.Xp + d.row * PERIOD;
    r.push(proj(p, Xn + LEN, p.Ydash).v - d.far);
    r.push(proj(p, Xn, p.Ydash).v - d.near);
    r.push(proj(p, Xn + LEN / 2, p.Ydash).u - d.u);
  }
  // VP constraints (weight 2: the VP is well determined by 3 lines)
  r.push(2 * ((CY - p.f * Math.tan(p.th)) - VP_OBS.v));
  r.push(2 * ((CX + p.f * Math.tan(p.psi) / Math.cos(p.th)) - VP_OBS.u));
  return r;
}
const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);
const clamp = p => { for (const k of KEYS) p[k] = Math.min(BOUND[k][1], Math.max(BOUND[k][0], p[k])); return p; };

function solve(p0, iters = 800) {
  let p = clamp({ ...p0 }), lam = 1e-3;
  for (let it = 0; it < iters; it++) {
    const r = residuals(p);
    const J = r.map(() => KEYS.map(() => 0));
    for (let k = 0; k < KEYS.length; k++) {
      const dp = { ...p }, eps = Math.max(1e-7, Math.abs(p[KEYS[k]]) * 1e-6); dp[KEYS[k]] += eps;
      const r2 = residuals(dp);
      const sign = (dp[KEYS[k]] === p[KEYS[k]]) ? 1 : 1;  // clamped same value is fine
      for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / eps;
    }
    const n = KEYS.length, A = Array.from({ length: n }, () => Array(n).fill(0)), g = Array(n).fill(0);
    for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) { g[a] += J[i][a] * r[i]; for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b]; }
    for (let a = 0; a < n; a++) A[a][a] *= (1 + lam);
    const M = A.map((row, i) => [...row, -g[i]]);
    let ok = true;
    for (let c = 0; c < n; c++) {
      let pv = c; for (let q = c + 1; q < n; q++) if (Math.abs(M[q][c]) > Math.abs(M[pv][c])) pv = q;
      if (Math.abs(M[pv][c]) < 1e-12) { ok = false; break; }
      [M[c], M[pv]] = [M[pv], M[c]];
      const d0 = M[c][c];
      for (let j = c; j <= n; j++) M[c][j] /= d0;
      for (let q = 0; q < n; q++) { if (q === c) continue; const f0 = M[q][c]; for (let j = c; j <= n; j++) M[q][j] -= f0 * M[c][j]; }
    }
    if (!ok) { lam *= 10; continue; }
    const dx = M.map(row => row[n]);
    const pn = { ...p };
    KEYS.forEach((k, i) => pn[k] += dx[i]);
    clamp(pn);
    if (cost(pn) < cost(p)) { p = pn; lam = Math.max(lam * 0.3, 1e-10); } else lam *= 3;
  }
  return p;
}

// multi-start over f and h
let best = null;
for (const f0 of [300, 400, 500, 700, 900, 1200]) {
  for (const h0 of [5, 8, 12, 18]) {
    const th0 = Math.atan((CY - VP_OBS.v) / f0);
    const psi0 = Math.atan((VP_OBS.u - CX) * Math.cos(th0) / f0);
    const p = solve({ f: f0, th: th0, psi: psi0, h: h0, Yyel: -6, Yred: 1, Ydash: -2.5, Xp: 18 });
    const c = cost(p);
    if (!best || c < best.c) best = { p, c };
  }
}
const p = best.p;
const r = residuals(p);
const rms = Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
console.log('=== HASIL ===');
console.log('obs=%d params=%d dof=%d  rms=%.2f px  cost=%.1f', r.length, KEYS.length, r.length - KEYS.length, rms, best.c);
for (const k of KEYS) console.log('  %s = %s', k.padEnd(6), p[k].toFixed(4));
console.log('\npitch %s deg | yaw %s deg | HFOV %s deg | horizon %s px',
  (p.th * 180 / Math.PI).toFixed(2), (p.psi * 180 / Math.PI).toFixed(2),
  (2 * Math.atan(CX / p.f) * 180 / Math.PI).toFixed(1), (CY - p.f * Math.tan(p.th)).toFixed(1));
console.log('lajur kiri %s m | kanan %s m | total %s m',
  Math.abs(p.Ydash - p.Yyel).toFixed(2), Math.abs(p.Yred - p.Ydash).toFixed(2), Math.abs(p.Yred - p.Yyel).toFixed(2));

// covariance
const J = r.map(() => KEYS.map(() => 0));
for (let k = 0; k < KEYS.length; k++) {
  const dp = { ...p }, eps = Math.max(1e-7, Math.abs(p[KEYS[k]]) * 1e-6); dp[KEYS[k]] += eps;
  const r2 = residuals(clamp({ ...dp }));
  for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / eps;
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
console.log('\nketidakpastian (1 sigma):');
KEYS.forEach((k, i) => console.log('  %s = %s +- %s', k.padEnd(6), p[k].toFixed(3), Math.sqrt(Math.max(M[i][n + i], 0) * s2).toFixed(3)));
fs.writeFileSync('f2/calib_480.json', JSON.stringify(p, null, 1));
