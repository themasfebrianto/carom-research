// Fit camera (f, pitch, height, phase, lane width) to the dash grid.
// Model (yaw=0, roll=0, level road):
//   z(X) = X cos t + h sin t
//   v(X) = cy + f(-X sin t + h cos t)/z
//   du(X) = f*w/z            (lateral spacing between adjacent lane centres)

const CY = 360, CX = 640;
const PERIOD = 13.0;   // 5 m dash + 8 m gap, PM 34/2014, VR>=60

// observations
const rows = [
  { v: (667.5 + 665.0) / 2, du: 407.4 - 265.9 },   // X1
  { v: (554.0 + 552.0) / 2, du: 484.6 - 388.3 },   // X1+13
  { v: (494.5 + 494.5) / 2, du: 522.2 - 450.9 },   // X1+26
];
const X = rows.map((_, i) => i * PERIOD);

function predict(p, i) {
  const { f, t, h, X1, w } = p;
  const Xi = X1 + X[i];
  const z = Xi * Math.cos(t) + h * Math.sin(t);
  return {
    v: CY + f * (-Xi * Math.sin(t) + h * Math.cos(t)) / z,
    du: f * w / z,
  };
}
function residuals(p) {
  const r = [];
  for (let i = 0; i < rows.length; i++) {
    const q = predict(p, i);
    r.push(q.v - rows[i].v);
    r.push((q.du - rows[i].du) * 2.0);   // weight lateral 2x (px-level noise similar, but du is a difference → less noisy)
  }
  return r;
}
const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);

// Levenberg-Marquardt with numeric Jacobian
let p = { f: 1200, t: 2 * Math.PI / 180, h: 8, X1: 25, w: 3.6 };
let lambda = 1e-2;
for (let it = 0; it < 400; it++) {
  const r = residuals(p);
  const keys = ['f', 't', 'h', 'X1', 'w'];
  const J = r.map(() => keys.map(() => 0));
  for (let k = 0; k < keys.length; k++) {
    const dp = { ...p };
    const eps = Math.max(1e-6, Math.abs(p[keys[k]]) * 1e-6) + 1e-9;
    dp[keys[k]] += eps;
    const r2 = residuals(dp);
    for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / eps;
  }
  // normal equations
  const n = keys.length;
  const A = Array.from({ length: n }, () => Array(n).fill(0)), g = Array(n).fill(0);
  for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) {
    g[a] += J[i][a] * r[i];
    for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b];
  }
  for (let a = 0; a < n; a++) A[a][a] *= (1 + lambda);
  // solve A dx = -g (Gaussian elimination)
  const M = A.map((row, i) => [...row, -g[i]]);
  for (let c = 0; c < n; c++) {
    let piv = c; for (let rr = c + 1; rr < n; rr++) if (Math.abs(M[rr][c]) > Math.abs(M[piv][c])) piv = rr;
    [M[c], M[piv]] = [M[piv], M[c]];
    const d0 = M[c][c];
    for (let j = c; j <= n; j++) M[c][j] /= d0;
    for (let rr = 0; rr < n; rr++) {
      if (rr === c) continue;
      const f0 = M[rr][c];
      for (let j = c; j <= n; j++) M[rr][j] -= f0 * M[c][j];
    }
  }
  const dx = M.map(row => row[n]);
  const pn = { ...p };
  keys.forEach((k, i) => pn[k] += dx[i]);
  if (cost(pn) < cost(p)) { p = pn; lambda = Math.max(lambda * 0.3, 1e-9); }
  else lambda *= 3;
}

const deg = r => r * 180 / Math.PI;
console.log('=== FIT ===');
console.log(`f      = ${p.f.toFixed(1)} px`);
console.log(`pitch  = ${deg(p.t).toFixed(3)} deg`);
console.log(`height = ${p.h.toFixed(2)} m`);
console.log(`X1     = ${p.X1.toFixed(2)} m  (distance to the nearest dash row)`);
console.log(`lane w = ${p.w.toFixed(3)} m   <-- independent measurement (spec 3.50-3.75)`);
console.log(`horizon row = ${(CY - p.f * Math.tan(p.t)).toFixed(1)} px ; vertical VP row = ${(CY + p.f / Math.tan(p.t)).toFixed(0)}`);
console.log('\n residual (px)      observed   predicted');
for (let i = 0; i < rows.length; i++) {
  const q = predict(p, i);
  console.log(`  X=${(p.X1 + X[i]).toFixed(1).padStart(6)} m   v ${rows[i].v.toFixed(1).padStart(7)}  ${q.v.toFixed(1).padStart(8)}   du ${rows[i].du.toFixed(1).padStart(6)} ${q.du.toFixed(1).padStart(7)}`);
}
const rr = residuals(p);
console.log(`\nRMS weighted = ${Math.sqrt(cost(p) / rr.length).toFixed(2)}   cost=${cost(p).toExponential(2)}`);

// --- sensitivity: what if the period is 12 m or 14 m?
console.log('\n=== SENSITIVITY TO THE 13 m ASSUMPTION ===');
for (const per of [12, 13, 14]) {
  const rows2 = rows.map(r => ({ ...r })), X2 = [0, per, 2 * per];
  const pred = (pp, i) => {
    const Xi = pp.X1 + X2[i], z = Xi * Math.cos(pp.t) + pp.h * Math.sin(pp.t);
    return { v: CY + pp.f * (-Xi * Math.sin(pp.t) + pp.h * Math.cos(pp.t)) / z, du: pp.f * pp.w / z };
  };
  const res2 = pp => { const r = []; for (let i = 0; i < rows2.length; i++) { const q = pred(pp, i); r.push(q.v - rows2[i].v); r.push((q.du - rows2[i].du) * 2); } return r; };
  let q = { ...p }, lam = 1e-2;
  for (let it = 0; it < 400; it++) {
    const r = res2(q); const keys = ['f', 't', 'h', 'X1', 'w'];
    const J = r.map(() => keys.map(() => 0));
    for (let k = 0; k < keys.length; k++) {
      const dp = { ...q }; const eps = Math.max(1e-6, Math.abs(q[keys[k]]) * 1e-6);
      dp[keys[k]] += eps; const r2 = res2(dp);
      for (let i2 = 0; i2 < r.length; i2++) J[i2][k] = (r2[i2] - r[i2]) / eps;
    }
    const n = keys.length, A = Array.from({ length: n }, () => Array(n).fill(0)), g = Array(n).fill(0);
    for (let i2 = 0; i2 < r.length; i2++) for (let a = 0; a < n; a++) { g[a] += J[i2][a] * r[i2]; for (let b = 0; b < n; b++) A[a][b] += J[i2][a] * J[i2][b]; }
    for (let a = 0; a < n; a++) A[a][a] *= (1 + lam);
    const M = A.map((row, i2) => [...row, -g[i2]]);
    for (let c = 0; c < n; c++) { let piv = c; for (let t2 = c + 1; t2 < n; t2++) if (Math.abs(M[t2][c]) > Math.abs(M[piv][c])) piv = t2;[M[c], M[piv]] = [M[piv], M[c]]; const d0 = M[c][c]; for (let j = c; j <= n; j++) M[c][j] /= d0; for (let t2 = 0; t2 < n; t2++) { if (t2 === c) continue; const f0 = M[t2][c]; for (let j = c; j <= n; j++) M[t2][j] -= f0 * M[c][j]; } }
    const dx = M.map(row => row[n]); const qn = { ...q }; keys.forEach((k, i2) => qn[k] += dx[i2]);
    const c1 = res2(q).reduce((s, x) => s + x * x, 0), c2 = res2(qn).reduce((s, x) => s + x * x, 0);
    if (c2 < c1) { q = qn; lam = Math.max(lam * 0.3, 1e-9); } else lam *= 3;
  }
  console.log(` period ${per} m -> h=${q.h.toFixed(2)} m  f=${q.f.toFixed(0)} px  w=${q.w.toFixed(3)} m  pitch=${deg(q.t).toFixed(2)}`);
}
