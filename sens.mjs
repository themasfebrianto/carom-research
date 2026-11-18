// Sensitivity of the dash-grid fit to assumptions: principal point cy, dash period.
const CY0 = 360;
const rowsBase = [
  { v: (667.5 + 665.0) / 2, du: 407.4 - 265.9 },
  { v: (554.0 + 552.0) / 2, du: 484.6 - 388.3 },
  { v: (494.5 + 494.5) / 2, du: 522.2 - 450.9 },
];
function fit(cy, period, cxUnused = 640) {
  const X = [0, period, 2 * period];
  const pred = (p, i) => {
    const Xi = p.X1 + X[i], z = Xi * Math.cos(p.t) + p.h * Math.sin(p.t);
    return { v: cy + p.f * (-Xi * Math.sin(p.t) + p.h * Math.cos(p.t)) / z, du: p.f * p.w / z };
  };
  const res = p => { const r = []; for (let i = 0; i < 3; i++) { const q = pred(p, i); r.push(q.v - rowsBase[i].v); r.push((q.du - rowsBase[i].du) * 2); } return r; };
  let p = { f: 1157, t: 2.12 * Math.PI / 180, h: 8.1, X1: 26.6, w: 3.29 }, lam = 1e-2;
  const keys = ['f', 't', 'h', 'X1', 'w'];
  for (let it = 0; it < 500; it++) {
    const r = res(p); const J = r.map(() => keys.map(() => 0));
    for (let k = 0; k < keys.length; k++) {
      const dp = { ...p }, eps = Math.max(1e-6, Math.abs(p[keys[k]]) * 1e-6); dp[keys[k]] += eps;
      const r2 = res(dp); for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / eps;
    }
    const n = 5, A = Array.from({ length: n }, () => Array(n).fill(0)), g = Array(n).fill(0);
    for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) { g[a] += J[i][a] * r[i]; for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b]; }
    for (let a = 0; a < n; a++) A[a][a] *= (1 + lam);
    const M = A.map((row, i) => [...row, -g[i]]);
    for (let c = 0; c < n; c++) { let pv = c; for (let t2 = c + 1; t2 < n; t2++) if (Math.abs(M[t2][c]) > Math.abs(M[pv][c])) pv = t2;[M[c], M[pv]] = [M[pv], M[c]]; const d0 = M[c][c]; for (let j = c; j <= n; j++) M[c][j] /= d0; for (let t2 = 0; t2 < n; t2++) { if (t2 === c) continue; const f0 = M[t2][c]; for (let j = c; j <= n; j++) M[t2][j] -= f0 * M[c][j]; } }
    const dx = M.map(row => row[n]); const qn = { ...p }; keys.forEach((k, i) => qn[k] += dx[i]);
    const c1 = res(p).reduce((s, x) => s + x * x, 0), c2 = res(qn).reduce((s, x) => s + x * x, 0);
    if (c2 < c1) { p = qn; lam = Math.max(lam * 0.3, 1e-9); } else lam *= 3;
  }
  const cost = res(p).reduce((s, x) => s + x * x, 0);
  return { p, rms: Math.sqrt(cost / 6) };
}
console.log('cy   period   f(px)   pitch(deg)  h(m)   w(m)   rms(px)');
for (const cy of [340, 350, 360, 370, 380]) {
  for (const per of [13]) {
    const { p, rms } = fit(cy, per);
    console.log(`${cy}   ${per}      ${p.f.toFixed(0).padStart(5)}   ${(p.t * 180 / Math.PI).toFixed(2).padStart(8)}  ${p.h.toFixed(2).padStart(5)}  ${p.w.toFixed(3)}  ${rms.toFixed(2)}`);
  }
}
console.log('\n(assumed cy=360 elsewhere)');
for (const per of [12, 13, 14, 15, 16]) {
  const { p, rms } = fit(360, per);
  console.log(`cy=360 period ${per} -> f=${p.f.toFixed(0)} h=${p.h.toFixed(2)} w=${p.w.toFixed(3)} rms=${rms.toFixed(2)}`);
}
console.log('\nWhat period would make w = 3.60 ?');
let lo = 10, hi = 25;
for (let k = 0; k < 60; k++) { const mid = (lo + hi) / 2; const { p } = fit(360, mid); if (p.w < 3.60) lo = mid; else hi = mid; }
const { p: pf } = fit(360, (lo + hi) / 2);
console.log(` period=${((lo + hi) / 2).toFixed(2)} m -> w=${pf.w.toFixed(3)}  (f=${pf.f.toFixed(0)}, h=${pf.h.toFixed(2)})`);
