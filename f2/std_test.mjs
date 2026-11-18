// Which marking standard is consistent with BOTH the dash centres (13 m or 8 m)
// AND the observed dash length (48 px)?
const CY = 180;
function v(p, X) {
  const { f, th, h } = p;
  return CY + f * (-X * Math.sin(th) + h * Math.cos(th)) / (X * Math.cos(th) + h * Math.sin(th));
}
function solveStd(P, L) {
  let p = { f: 230, th: 27 * Math.PI / 180, h: 9, X1: 6 }, lam = 1e-3;
  const res = q => [
    v(q, q.X1) - 321,
    v(q, q.X1 + P) - 175,
    (v(q, q.X1) - v(q, q.X1 + L)) - 48,
    (CY - q.f * Math.tan(q.th)) - 60
  ];
  const cost = q => res(q).reduce((s, x) => s + x * x, 0);
  const keys = ['f', 'th', 'h', 'X1'];
  for (let it = 0; it < 4000; it++) {
    const r = res(p); const J = r.map(() => keys.map(() => 0));
    for (let k = 0; k < keys.length; k++) {
      const dp = { ...p }, e = Math.max(1e-8, Math.abs(p[keys[k]]) * 1e-6); dp[keys[k]] += e;
      const r2 = res(dp);
      for (let i = 0; i < r.length; i++) J[i][k] = (r2[i] - r[i]) / e;
    }
    const n = 4, A = Array.from({ length: n }, () => Array(n).fill(0)), g = Array(n).fill(0);
    for (let i = 0; i < r.length; i++) for (let a = 0; a < n; a++) { g[a] += J[i][a] * r[i]; for (let b = 0; b < n; b++) A[a][b] += J[i][a] * J[i][b]; }
    for (let a = 0; a < n; a++) A[a][a] *= (1 + lam);
    const M = A.map((row, i) => [...row, -g[i]]);
    for (let c = 0; c < n; c++) {
      let pv = c; for (let q = c + 1; q < n; q++) if (Math.abs(M[q][c]) > Math.abs(M[pv][c])) pv = q;
      if (Math.abs(M[pv][c]) < 1e-14) { lam *= 10; continue; }
      [M[c], M[pv]] = [M[pv], M[c]];
      const d0 = M[c][c];
      for (let j = c; j <= n; j++) M[c][j] /= d0;
      for (let q = 0; q < n; q++) { if (q === c) continue; const f0 = M[q][c]; for (let j = c; j <= n; j++) M[q][j] -= f0 * M[c][j]; }
    }
    const dx = M.map(row => row[n]); const pn = { ...p }; keys.forEach((k, i) => pn[k] += dx[i]);
    if (cost(pn) < cost(p)) { p = pn; lam = Math.max(lam * 0.3, 1e-11); } else lam *= 3;
  }
  const r = res(p);
  return { p, rms: Math.sqrt(r.reduce((s, x) => s + x * x, 0) / r.length), r };
}
for (const [P, L, label] of [[13, 5, '5 m garis + 8 m celah'], [8, 3, '3 m garis + 5 m celah'], [12, 4, '4+8'], [9, 3, '3+6']]) {
  const s = solveStd(P, L);
  console.log(`${label.padEnd(24)} -> f=${s.p.f.toFixed(0)} px  pitch=${(s.p.th * 180 / Math.PI).toFixed(1)} deg  h=${s.p.h.toFixed(2)} m  X1=${s.p.X1.toFixed(2)} m  rms=${s.rms.toFixed(2)} px`);
  console.log(`   residual: v1=${s.r[0].toFixed(1)} v2=${s.r[1].toFixed(1)} length=${s.r[2].toFixed(1)} vp=${s.r[3].toFixed(1)}`);
}
