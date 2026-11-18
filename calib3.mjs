// Calibration v3: 6 clean dashes (2 lanes x 3 rows), sub-pixel edges, full model.
import fs from 'node:fs';

const buf = fs.readFileSync('frames/median2.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2], CX = W / 2, CY = H / 2;

const raw = JSON.parse(fs.readFileSync('frames/dashes2.json', 'utf8'));
// keep lanes 0 and 1, assign row index by descending vNear
const dashes = [];
for (const lane of [0, 1]) {
  const ds = raw.filter(d => d.lane === lane).sort((a, b) => b.yNear - a.yNear).slice(0, 3);
  ds.forEach((d, k) => dashes.push({ lane, row: k, yFar: d.yFar, yNear: d.yNear, u: d.u }));
}
console.log('dashes used:', dashes.length);
dashes.forEach(d => console.log(`  lane ${d.lane} row ${d.row}: vFar=${d.yFar.toFixed(2)} vNear=${d.yNear.toFixed(2)} u=${d.u.toFixed(1)}`));

function proj(p, X, Y) {
  const { f, th, psi, h, k1 } = p;
  const cp = Math.cos(th), sp = Math.sin(th), cw = Math.cos(psi), sw = Math.sin(psi);
  const fw = [cp * cw, cp * sw, -sp];
  const rw = [sw, -cw, 0];
  const dw = [fw[1] * rw[2] - fw[2] * rw[1], fw[2] * rw[0] - fw[0] * rw[2], fw[0] * rw[1] - fw[1] * rw[0]];
  const dx = X, dy = Y, dz = -h;
  const xc = rw[0] * dx + rw[1] * dy + rw[2] * dz;
  const yc = dw[0] * dx + dw[1] * dy + dw[2] * dz;
  const zc = fw[0] * dx + fw[1] * dy + fw[2] * dz;
  const xn = xc / zc, yn = yc / zc, r2 = xn * xn + yn * yn;
  const s = 1 + (k1 || 0) * r2;
  return { u: CX + f * xn * s, v: CY + f * yn * s, zc };
}

const PERIOD = 13.0, DASH = 5.0;
function residuals(p) {
  const r = [];
  for (const dz of dashes) {
    const Y = p.Y0 - dz.lane * p.w;
    const Xn = p.Xp + dz.row * PERIOD;        // near edge (smaller X)
    const Xf = Xn + DASH;                     // far edge (larger X)
    const Xm = Xn + DASH / 2;
    r.push(proj(p, Xf, Y).v - dz.yFar);
    r.push(proj(p, Xn, Y).v - dz.yNear);
    r.push(proj(p, Xm, Y).u - dz.u);
  }
  return r;
}
const cost = p => residuals(p).reduce((s, x) => s + x * x, 0);

function solve(p0, keys, iters = 500) {
  let p = { ...p0 }, lam = 1e-2;
  for (let it = 0; it < iters; it++) {
    const r = residuals(p);
    const J = r.map(() => keys.map(() => 0));
    for (let k = 0; k < keys.length; k++) {
      const dp = { ...p }, eps = Math.max(1e-7, Math.abs(p[keys[k]]) * 1e-6);
      dp[keys[k]] += eps;
      const r2 = residuals(dp);
      for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / eps;
    }
    const n = keys.length;
    const A = Array.from({ length: n }, () => Array(n).fill(0)), g = Array(n).fill(0);
    for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) {
      g[a] += J[i][a] * r[i];
      for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b];
    }
    for (let a = 0; a < n; a++) A[a][a] *= (1 + lam);
    const M = A.map((row, i) => [...row, -g[i]]);
    for (let c = 0; c < n; c++) {
      let pv = c; for (let t = c + 1; t < n; t++) if (Math.abs(M[t][c]) > Math.abs(M[pv][c])) pv = t;
      [M[c], M[pv]] = [M[pv], M[c]];
      const d0 = M[c][c]; if (Math.abs(d0) < 1e-14) continue;
      for (let j = c; j <= n; j++) M[c][j] /= d0;
      for (let t = 0; t < n; t++) { if (t === c) continue; const f0 = M[t][c]; for (let j = c; j <= n; j++) M[t][j] -= f0 * M[c][j]; }
    }
    const dx = M.map(row => row[n]);
    const pn = { ...p }; keys.forEach((k, i) => pn[k] += dx[i]);
    if (cost(pn) < cost(p)) { p = pn; lam = Math.max(lam * 0.3, 1e-10); } else lam *= 3;
  }
  return p;
}

function report(p, keys, label) {
  const r = residuals(p);
  const rms = Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
  const dof = r.length - keys.length;
  const J = r.map(() => keys.map(() => 0));
  for (let k = 0; k < keys.length; k++) {
    const dp = { ...p }, eps = Math.max(1e-7, Math.abs(p[keys[k]]) * 1e-6); dp[keys[k]] += eps;
    const r2 = residuals(dp);
    for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / eps;
  }
  const n = keys.length, A = Array.from({ length: n }, () => Array(n).fill(0));
  for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b];
  const M = A.map((row, i) => [...row, ...Array.from({ length: n }, (_, j) => i === j ? 1 : 0)]);
  for (let c = 0; c < n; c++) {
    let pv = c; for (let t = c + 1; t < n; t++) if (Math.abs(M[t][c]) > Math.abs(M[pv][c])) pv = t;
    [M[c], M[pv]] = [M[pv], M[c]];
    const d0 = M[c][c];
    for (let j = 0; j < 2 * n; j++) M[c][j] /= d0;
    for (let t = 0; t < n; t++) { if (t === c) continue; const f0 = M[t][c]; for (let j = 0; j < 2 * n; j++) M[t][j] -= f0 * M[c][j]; }
  }
  const s2 = dof > 0 ? r.reduce((s, x) => s + x * x, 0) / dof : NaN;
  console.log(`\n=== ${label} ===`);
  console.log(`obs=${r.length} params=${keys.length} dof=${dof} rms=${rms.toFixed(3)} px`);
  keys.forEach((k, i) => console.log(`  ${k.padEnd(4)} = ${p[k].toFixed(6).padStart(13)}  ± ${Math.sqrt(Math.max(M[i][n + i], 0) * s2).toFixed(6)}`));
  return p;
}

const deg = x => x * 180 / Math.PI;
const p0 = { f: 1158, th: 2.12 * Math.PI / 180, psi: 0.006, h: 8.11, Xp: 24.3, w: 3.29, Y0: 8.69 };
{
  const c0 = residuals(p0);
  console.log('initial rms =', Math.sqrt(c0.reduce((s, x) => s + x * x, 0) / c0.length).toFixed(2), 'px');
}

console.log('\n--- fits ---');
const P6 = solve(p0, ['f', 'th', 'psi', 'h', 'Xp', 'w', 'Y0']);
report(P6, ['f', 'th', 'psi', 'h', 'Xp', 'w', 'Y0'], 'A: 7 params (psi free)');

const P5 = solve(p0, ['f', 'th', 'psi', 'h', 'Xp', 'w'], undefined);
report(P5, ['f', 'th', 'psi', 'h', 'Xp', 'w'], 'B: Y0 fixed-free check (6 params)');

console.log('\n--- final parameters (A) ---');
console.log(`  f        = ${P6.f.toFixed(2)} px`);
console.log(`  pitch    = ${deg(P6.th).toFixed(3)} deg`);
console.log(`  yaw      = ${deg(P6.psi).toFixed(3)} deg`);
console.log(`  height   = ${P6.h.toFixed(3)} m`);
console.log(`  phase Xp = ${P6.Xp.toFixed(2)} m`);
console.log(`  lane w   = ${P6.w.toFixed(4)} m`);
console.log(`  Y0       = ${P6.Y0.toFixed(3)} m`);
console.log(`  horizon  = ${(CY - P6.f * Math.tan(P6.th)).toFixed(1)} px`);
console.log(`  HFOV     = ${(2 * Math.atan(CX / P6.f) * 180 / Math.PI).toFixed(1)} deg`);
console.log(`  road VP  = u=${(CX + P6.f * Math.tan(P6.psi)).toFixed(1)}, v=${(CY - P6.f * Math.tan(P6.th) / Math.cos(P6.psi)).toFixed(1)}`);

console.log('\n--- residuals per dash ---');
for (const dz of dashes) {
  const Y = P6.Y0 - dz.lane * P6.w;
  const Xf = P6.Xp + dz.row * PERIOD, Xn = Xf + DASH, Xm = Xf + DASH / 2;
  const a = proj(P6, Xf, Y), b = proj(P6, Xn, Y), c = proj(P6, Xm, Y);
  console.log(`  lane${dz.lane} row${dz.row}: dvFar=${(a.v - dz.yFar).toFixed(2)} dvNear=${(b.v - dz.yNear).toFixed(2)} du=${(c.u - dz.u).toFixed(2)}`);
}

// derived validation: dash length and gap implied by the model
console.log('\n--- model-implied dash geometry ---');
const XofV = (v, Y) => {
  let lo = 1, hi = 400;
  for (let k = 0; k < 100; k++) {
    const mid = (lo + hi) / 2;
    const pv = proj(P6, mid, Y).v;
    if (pv > v) lo = mid; else hi = mid;
  }
  return (lo + hi) / 2;
};
for (const dz of dashes.filter(d => d.row === 0 && d.lane === 0)) {
  const Y = P6.Y0;
  const x1 = XofV(dz.yNear, Y), x2 = XofV(dz.yFar, Y);
  console.log(`  lane0 row0: dash length = ${Math.abs(x1 - x2).toFixed(3)} m (spec 5.000)`);
}

// --- Y0 sensitivity: is the fixed nuisance parameter safe?
console.log('\n--- sensitivity to the fixed Y0 (6-param model) ---');
for (const Y0 of [6.0, 7.0, 8.0, 8.69, 9.5, 10.5]) {
  const q = solve({ ...p0, Y0 }, ['f', 'th', 'psi', 'h', 'Xp', 'w'], 800);
  const rr = residuals(q);
  const rms = Math.sqrt(rr.reduce((s, x) => s + x * x, 0) / rr.length);
  console.log(`  Y0=${Y0.toFixed(2)} -> f=${q.f.toFixed(0)} th=${deg(q.th).toFixed(2)} psi=${deg(q.psi).toFixed(2)} h=${q.h.toFixed(3)} w=${q.w.toFixed(3)} Xp=${q.Xp.toFixed(2)} rms=${rms.toFixed(2)}`);
}
fs.writeFileSync('frames/final.json', JSON.stringify(P6, null, 1));
