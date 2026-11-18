// Calibration v2: true-median frame, sub-pixel dash edges, coupled model fit.
import fs from 'node:fs';

const path = process.argv[2] || 'frames/median2.ppm';
const buf = fs.readFileSync(path);
const head = buf.subarray(0, 64).toString('latin1');
const mh = head.match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2], CX = W / 2, CY = H / 2;
const d = buf.subarray(off);
const lum = (x, y) => {
  x = Math.round(x); y = Math.round(y);
  if (x < 0 || y < 0 || x >= W || y >= H) return 0;
  const o = (y * W + x) * 3;
  return 0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2];
};

/* ---------- 1. profile + sub-pixel dash edges ---------- */
const VPx = 651.54, VPy = 309.96, YREF = 719;
const LANES = [209.5, 369.2, 533.6];
const YTOP = 430, YBOT = 718;

function profileFor(xb) {
  const arr = [];
  for (let y = YBOT; y >= YTOP; y--) {
    const k = (y - VPy) / (YREF - VPy);
    const x0 = VPx + (xb - VPx) * k;
    // 5-sample perpendicular profile, keep max and its position (parabolic)
    let best = -1, bi = 0, vals = [];
    for (let dx = -4; dx <= 4; dx++) { const l = lum(x0 + dx, y); vals.push(l); if (l > best) { best = l; bi = dx; } }
    let sub = bi;
    const l0 = vals[bi - 1 + 4], l1 = vals[bi + 4], l2 = vals[bi + 1 + 4];
    if (l0 !== undefined && l2 !== undefined) {
      const den = (l0 - 2 * l1 + l2);
      if (Math.abs(den) > 1e-6) sub = bi + 0.5 * (l0 - l2) / den;
    }
    arr.push({ y, x: x0 + sub, l: best });
  }
  return arr;
}

// smooth
const smooth = a => a.map((p, i) => {
  const q = [a[i - 1], a[i], a[i + 1]].filter(Boolean);
  return { ...p, l: q.reduce((s, z) => s + z.l, 0) / q.length };
});

function findDashes(prof) {
  const out = [];
  for (let i = 2; i < prof.length - 2; i++) {
    if (!(prof[i].l > 128 && prof[i].l >= prof[i - 1].l && prof[i].l > prof[i + 1].l)) continue;
    // local base
    let base = 1e9;
    for (let j = Math.max(0, i - 55); j < Math.min(prof.length, i + 55); j++) base = Math.min(base, prof[j].l);
    const thr = (prof[i].l + base) / 2;
    // walk left (towards larger y = nearer)
    let a = i; while (a + 1 < prof.length && prof[a + 1].l > thr) a++;
    let b = i; while (b - 1 >= 0 && prof[b - 1].l > thr) b--;
    // sub-pixel crossing, linear interpolation
    const interp = (p1, p2, t) => p1.y + (p2.y - p1.y) * (t - p1.l) / (p2.l - p1.l);
    const yNear = (a + 1 < prof.length) ? interp(prof[a], prof[a + 1], thr) : prof[a].y;
    const yFar = (b - 1 >= 0) ? interp(prof[b], prof[b - 1], thr) : prof[b].y;
    const len = Math.abs(yNear - yFar);
    if (len < 7) continue;
    // lateral sub-pixel centre: average x over the dash core
    let sx = 0, n = 0;
    for (let j = Math.min(a, b) + 1; j <= Math.max(a, b) - 1; j++) { sx += prof[j].x; n++; }
    const xc = n ? sx / n : prof[i].x;
    out.push({ yNear, yFar, xc, peak: prof[i].l, len });
    i = a + 3;
  }
  return out;
}

console.log('=== 1. dash detection (sub-pixel) ===');
const dashes = [];
LANES.forEach((xb, j) => {
  const prof = smooth(profileFor(xb));
  const ds = findDashes(prof);
  ds.sort((p, q) => q.yNear - p.yNear);
  ds.slice(0, 4).forEach((dz, k) => {
    dashes.push({ lane: j, row: k, yFar: dz.yFar, yNear: dz.yNear, u: dz.xc, len: dz.len });
    console.log(`lane ${j} row ${k}: vFar=${dz.yFar.toFixed(2)} vNear=${dz.yNear.toFixed(2)} u=${dz.xc.toFixed(1)} len=${dz.len.toFixed(1)}px peak=${dz.peak.toFixed(0)}`);
  });
});

/* ---------- 2. camera model ---------- */
function proj(p, X, Y) {
  const { f, th, psi, h, k1 } = p;
  const cp = Math.cos(th), sp = Math.sin(th), cyw = Math.cos(psi), syw = Math.sin(psi);
  const fw = [cp * cyw, cp * syw, -sp];
  const rw = [syw, -cyw, 0];
  const dw = [fw[1] * rw[2] - fw[2] * rw[1], fw[2] * rw[0] - fw[0] * rw[2], fw[0] * rw[1] - fw[1] * rw[0]];
  const dx = X, dy = Y, dzz = -h;
  const xc = rw[0] * dx + rw[1] * dy + rw[2] * dzz;
  const yc = dw[0] * dx + dw[1] * dy + dw[2] * dzz;
  const zc = fw[0] * dx + fw[1] * dy + fw[2] * dzz;
  const xn = xc / zc, yn = yc / zc, r2 = xn * xn + yn * yn;
  const s = 1 + k1 * r2;
  return { u: CX + f * xn * s, v: CY + f * yn * s };
}

const PERIOD = 13.0, DASH = 5.0;

function residuals(p, useK1) {
  const r = [];
  const w = p.w, Y0 = p.Y0;
  for (const dz of dashes) {
    const Y = Y0 - dz.lane * w;
    const Xf = p.Xp + dz.row * PERIOD;          // far (start of dash)
    const Xn = Xf + DASH;                        // near (end of dash)
    const Xm = Xf + DASH / 2;
    const pf = proj(p, Xf, Y), pn = proj(p, Xn, Y), pm = proj(p, Xm, Y);
    r.push(pf.v - dz.yFar);
    r.push(pn.v - dz.yNear);
    r.push(pm.u - dz.u);
  }
  return r;
}
const cost = (p, k) => residuals(p, k).reduce((s, x) => s + x * x, 0);

function solve(p0, keys, useK1, iters = 300) {
  let p = { ...p0 }, lam = 1e-2;
  for (let it = 0; it < iters; it++) {
    const r = residuals(p, useK1);
    const J = r.map(() => keys.map(() => 0));
    for (let k = 0; k < keys.length; k++) {
      const dp = { ...p }, eps = Math.max(1e-7, Math.abs(p[keys[k]]) * 1e-6);
      dp[keys[k]] += eps;
      const r2 = residuals(dp, useK1);
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
    if (cost(pn, useK1) < cost(p, useK1)) { p = pn; lam = Math.max(lam * 0.3, 1e-10); }
    else lam *= 3;
  }
  return p;
}

function report(p, keys, useK1, label) {
  const r = residuals(p, useK1);
  const rms = Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length);
  const dof = r.length - keys.length;
  // covariance: sigma^2 (J^T J)^-1 with sigma estimated
  const J = r.map(() => keys.map(() => 0));
  for (let k = 0; k < keys.length; k++) {
    const dp = { ...p }, eps = Math.max(1e-7, Math.abs(p[keys[k]]) * 1e-6); dp[keys[k]] += eps;
    const r2 = residuals(dp, useK1);
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
  const s2 = dof > 0 ? (r.reduce((s, x) => s + x * x, 0)) / dof : NaN;
  console.log(`\n=== ${label} ===`);
  console.log(`observations=${r.length}  parameters=${keys.length}  dof=${dof}  rms=${rms.toFixed(3)} px`);
  keys.forEach((k, i) => {
    const sd = Math.sqrt(Math.max(M[i][n + i], 0) * s2);
    console.log(`  ${k.padEnd(5)} = ${p[k].toFixed(5).padStart(12)}   ± ${sd.toFixed(5)}`);
  });
  if (useK1) console.log(`  horizon row = ${(CY - p.f * Math.tan(p.th)).toFixed(1)}`);
  return { rms, dof, cov: M, s2 };
}

const p0 = { f: 1158, th: 2.12 * Math.PI / 180, psi: 0, h: 8.11, Xp: 26.6, w: 3.29, Y0: 8.69, k1: 0 };

console.log('\n=== 2. fits ===');
const A = solve(p0, ['f', 'th', 'h', 'Xp', 'w', 'Y0'], false);
report(A, ['f', 'th', 'h', 'Xp', 'w', 'Y0'], false, 'Model A: k1=0, psi=0');

const B = solve(p0, ['f', 'th', 'h', 'Xp', 'w', 'Y0', 'k1'], true);
report(B, ['f', 'th', 'h', 'Xp', 'w', 'Y0', 'k1'], true, 'Model B: k1 free, psi=0');

const Cc = solve(p0, ['f', 'th', 'psi', 'h', 'Xp', 'w', 'Y0'], false);
report(Cc, ['f', 'th', 'psi', 'h', 'Xp', 'w', 'Y0'], false, 'Model C: psi free, k1=0');

/* ---------- 3. derived quantities ---------- */
console.log('\n=== 3. derived ===');
for (const [nm, p] of [['A', A], ['B', B], ['C', Cc]]) {
  const deg = x => x * 180 / Math.PI;
  const hfov = 2 * Math.atan(CX / p.f) * 180 / Math.PI;
  console.log(`${nm}: f=${p.f.toFixed(1)} th=${deg(p.th).toFixed(3)}deg psi=${deg(p.psi).toFixed(3)}deg h=${p.h.toFixed(3)} w=${p.w.toFixed(4)} Xp=${p.Xp.toFixed(2)} horizon=${(CY - p.f * Math.tan(p.th)).toFixed(1)} HFOV=${hfov.toFixed(1)}deg`);
}
fs.writeFileSync('frames/calib2.json', JSON.stringify({ A, B, C: Cc }, null, 1));
