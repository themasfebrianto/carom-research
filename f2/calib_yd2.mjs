// Refine from the analytic starting point implied by the two dashes + VP.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const YEL = JSON.parse(fs.readFileSync('f2/tracked.json')).YEL.filter(p => p[1] <= 266);
const CX = W / 2, CY = H / 2;
const DASH = [{ u: 102.4, near: 345, far: 297 }, { u: 359.0, near: 185, far: 165 }];
const VPOBS = { u: 562.5, v: 60.0 };
const PERIOD = 13, LEN = 5;
const KEYS = ['f', 'th', 'psi', 'h', 'Yyel', 'Ydash', 'Xp'];
const B = { f: [120, 3000], th: [0.05, 1.2], psi: [0.05, 1.4], h: [2, 40], Yyel: [-40, 40], Ydash: [-40, 40], Xp: [2, 120] };
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
function residuals(p) {
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
const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);
function solve(p0, iters = 3000) {
  let p = clamp({ ...p0 }), lam = 1e-4;
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
// analytic-family start: sweep theta, solve h from the two-dash relation implicitly via fit
let best = null;
for (const thd of [22, 25, 27, 30, 34]) {
  for (const fv of [180, 220, 260, 320]) {
    const th = thd * Math.PI / 180;
    const psi = Math.atan((VPOBS.u - CX) * Math.cos(th) / fv);
    for (const hv of [10, 13, 16]) {
      const s = solve({ f: fv, th, psi, h: hv, Yyel: -8, Ydash: -4, Xp: 10 });
      const c = cost(s);
      if (!best || c < best.c) best = { p: s, c };
    }
  }
}
const p = best.p, r = residuals(p);
const rms = Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
const rmsOf = a => Math.sqrt(a.reduce((s, x) => s + x * x, 0) / a.length);
console.log(`obs=${r.length} dof=${r.length - KEYS.length} rms=${rms.toFixed(2)} px`);
console.log(`  kuning ${rmsOf(r.slice(0, YEL.length)).toFixed(2)}  dash ${rmsOf(r.slice(YEL.length, YEL.length + 6)).toFixed(2)}  VP ${rmsOf(r.slice(-2)).toFixed(2)}`);
console.log(`  dash residuals: ${r.slice(YEL.length, YEL.length + 6).map(x => x.toFixed(1)).join(' ')}`);
for (const k of KEYS) console.log(`  ${k} = ${p[k].toFixed(3)}`);
console.log(`pitch ${(p.th * 180 / Math.PI).toFixed(1)} deg | yaw ${(p.psi * 180 / Math.PI).toFixed(1)} deg | HFOV ${(2 * Math.atan(CX / p.f) * 180 / Math.PI).toFixed(0)} deg`);
console.log(`lebar lajur ${Math.abs(p.Ydash - p.Yyel).toFixed(2)} m`);
fs.writeFileSync('f2/calib_yd.json', JSON.stringify(p, null, 1));
