// Fit with f FIXED from GeoCalib. Does the dash geometry become consistent?
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const YEL = JSON.parse(fs.readFileSync('f2/tracked.json')).YEL.filter(p => p[1] <= 266);
const CX = W / 2, CY = H / 2;
const geo = JSON.parse(fs.readFileSync('f2/geocalib.json'));
const F_GEO = geo.reduce((s, d) => s + d.f_px, 0) / geo.length;

const DASH = [{ u: 102.4, near: 345, far: 297 }, { u: 359.0, near: 185, far: 165 }];
const KEYS = ['th', 'psi', 'h', 'Yyel', 'Ydash', 'Xp'];
const B = { th: [0.02, 0.9], psi: [0.05, 1.4], h: [1, 40], Yyel: [-40, 40], Ydash: [-40, 40], Xp: [-10, 120] };
const clamp = p => { for (const k of KEYS) p[k] = Math.min(B[k][1], Math.max(B[k][0], p[k])); return p; };
const basis = p => {
  const cp = Math.cos(p.th), sp = Math.sin(p.th), cw = Math.cos(p.psi), sw = Math.sin(p.psi);
  return { fw: [cp * cw, cp * sw, -sp], rw: [sw, -cw, 0], dw: [-sp * cw, -sp * sw, -cp] };
};
const proj = (p, X, Y) => {
  const { fw, rw, dw } = basis(p); const v = [X, Y, -p.h];
  const xc = rw[0] * v[0] + rw[1] * v[1] + rw[2] * v[2];
  const yc = dw[0] * v[0] + dw[1] * v[1] + dw[2] * v[2];
  const zc = fw[0] * v[0] + fw[1] * v[1] + fw[2] * v[2];
  return { u: CX + p.f * xc / zc, v: CY + p.f * yc / zc };
};
const back = (p, u, v) => {
  const { fw, rw, dw } = basis(p);
  const xn = (u - CX) / p.f, yn = (v - CY) / p.f;
  const dx = rw[0] * xn + dw[0] * yn + fw[0], dy = rw[1] * xn + dw[1] * yn + fw[1], dz = rw[2] * xn + dw[2] * yn + fw[2];
  if (dz > -1e-6) return null;
  const s = -p.h / dz, X = dx * s, Y = dy * s, z = Math.hypot(X, Y);
  return (z < 2 || z > 500) ? null : { X, Y, z };
};

function makeResiduals(PERIOD, LEN) {
  return p => {
    const r = [];
    for (const [u, v] of YEL) { const q = back(p, u, v); if (q) r.push((q.Y - p.Yyel) * p.f / q.z); }
    for (let i = 0; i < 2; i++) {
      const d = DASH[i], Xn = p.Xp + i * PERIOD;
      r.push(proj(p, Xn + LEN, p.Ydash).v - d.far);
      r.push(proj(p, Xn, p.Ydash).v - d.near);
      r.push(proj(p, Xn + LEN / 2, p.Ydash).u - d.u);
    }
    return r;
  };
}
function solve(p0, residuals, iters = 2000) {
  const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);
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
    if (cost(pn) < cost(p)) { p = pn; lam = Math.max(lam * 0.3, 1e-11); } else lam *= 3;
  }
  return p;
}

console.log(`f GeoCalib (rata-rata 4 citra) = ${F_GEO.toFixed(1)} px  (HFOV ${(2 * Math.atan(CX / F_GEO) * 180 / Math.PI).toFixed(1)} deg)\n`);
for (const [P, L, label] of [[13, 5, '5 m + 8 m'], [8, 3, '3 m + 5 m'], [12, 4, '4 + 8']]) {
  const res = makeResiduals(P, L);
  let best = null;
  for (const th0 of [0.10, 0.18, 0.25, 0.35]) for (const h0 of [4, 7, 11]) {
    const psi0 = Math.atan((562.5 - CX) * Math.cos(th0) / F_GEO);
    const p = solve({ f: F_GEO, th: th0, psi: psi0, h: h0, Yyel: -8, Ydash: -4, Xp: 6 }, res);
    const c = res(p).reduce((s, x) => s + x * x, 0);
    if (!best || c < best.c) best = { p, c };
  }
  const r = res(best.p);
  const rms = Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
  const rmsOf = a => Math.sqrt(a.reduce((s, x) => s + x * x, 0) / a.length);
  const p = best.p;
  console.log(`${label}  rms=${rms.toFixed(2)} px   kuning=${rmsOf(r.slice(0, YEL.length)).toFixed(2)}  dash=${rmsOf(r.slice(YEL.length)).toFixed(2)}`);
  console.log(`   pitch=${(p.th * 180 / Math.PI).toFixed(2)} deg  yaw=${(p.psi * 180 / Math.PI).toFixed(1)}  h=${p.h.toFixed(2)} m  lajur=${Math.abs(p.Ydash - p.Yyel).toFixed(2)} m  Xp=${p.Xp.toFixed(1)}`);
  console.log(`   horizon=${(CY - p.f * Math.tan(p.th)).toFixed(0)} px   dash residuals: ${r.slice(YEL.length).map(x => x.toFixed(0)).join(' ')}`);
}
