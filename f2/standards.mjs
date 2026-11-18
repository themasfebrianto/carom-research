// Try different marking standards (dash length / gap) and report fit quality.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const YEL = JSON.parse(fs.readFileSync('f2/tracked.json')).YEL.filter(p => p[1] <= 266);
const CX = W / 2, CY = H / 2;
const DASH = [
  { u: 102.4, near: 345, far: 297 },
  { u: 359.0, near: 185, far: 165 },
];
const VPOBS = { u: 562.5, v: 60.0 };
const KEYS = ['f', 'th', 'psi', 'h', 'Yyel', 'Ydash', 'Xp'];
const B = { f: [150, 4000], th: [0.02, 0.9], psi: [0.05, 1.4], h: [2, 40], Yyel: [-40, 40], Ydash: [-40, 40], Xp: [-20, 120] };
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
function residuals(p, PERIOD, LEN) {
  const r = [];
  for (const [u, v] of YEL) { const q = back(p, u, v); if (q) r.push((q.Y - p.Yyel) * p.f / q.z); }
  for (let i = 0; i < 2; i++) {
    const d = DASH[i], Xn = p.Xp + i * PERIOD;
    r.push(proj(p, Xn + LEN, p.Ydash).v - d.far);
    r.push(proj(p, Xn, p.Ydash).v - d.near);
    r.push(proj(p, Xn + LEN / 2, p.Ydash).u - d.u);
  }
  r.push(2 * ((CY - p.f * Math.tan(p.th)) - VPOBS.v));
  r.push(2 * ((CX + p.f * Math.tan(p.psi) / Math.cos(p.th)) - VPOBS.u));
  return r;
}
function solve(p0, PERIOD, LEN) {
  const cost = p => residuals(p, PERIOD, LEN).reduce((s, x) => s + x * x, 0);
  let p = clamp({ ...p0 }), lam = 1e-3;
  for (let it = 0; it < 900; it++) {
    const r = residuals(p, PERIOD, LEN); const J = r.map(() => KEYS.map(() => 0));
    for (let k = 0; k < KEYS.length; k++) {
      const dp = { ...p }, e = Math.max(1e-7, Math.abs(p[KEYS[k]]) * 1e-6); dp[KEYS[k]] += e;
      const r2 = residuals(dp, PERIOD, LEN);
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
  return { p, c: cost(p) };
}

const opts = [[13, 5, '5 m garis + 8 m celah (>=60 km/j)'], [8, 3, '3 m garis + 5 m celah (<60 km/j)'],
[12, 4, '4 + 8'], [10, 4, '4 + 6'], [9, 4, '4 + 5'], [11, 5, '5 + 6'], [14, 6, '6 + 8']];
console.log('periode/panjang | rms (px) | dash rms | f | h | w | pitch | yaw');
for (const [P, L, label] of opts) {
  let best = null;
  for (const f0 of [250, 400, 600, 900]) for (const h0 of [4, 7, 11, 16]) {
    const th0 = Math.atan((CY - VPOBS.v) / f0), psi0 = Math.atan((VPOBS.u - CX) * Math.cos(th0) / f0);
    const s = solve({ f: f0, th: th0, psi: psi0, h: h0, Yyel: -8, Ydash: -4, Xp: 8 }, P, L);
    if (!best || s.c < best.c) best = s;
  }
  const r = residuals(best.p, P, L);
  const rms = Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
  const dR = r.slice(YEL.length, YEL.length + 6);
  const drms = Math.sqrt(dR.reduce((s, x) => s + x * x, 0) / dR.length);
  console.log(`${P}/${L} ${label.padEnd(30)} rms=${rms.toFixed(2)}  dash=${drms.toFixed(1)}  f=${best.p.f.toFixed(0)}  h=${best.p.h.toFixed(1)}  w=${Math.abs(best.p.Ydash - best.p.Yyel).toFixed(2)}  pitch=${(best.p.th * 180 / Math.PI).toFixed(1)}  yaw=${(best.p.psi * 180 / Math.PI).toFixed(1)}`);
}
