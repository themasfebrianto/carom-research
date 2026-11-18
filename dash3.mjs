// Run-based dash extraction with sub-pixel edges.
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

const VPx = 651.54, VPy = 309.96, YREF = 719;
const LANES = [209.5, 369.2, 533.6];
const YTOP = 432, YBOT = 714;

function profileFor(xb) {
  const arr = [];
  for (let y = YBOT; y >= YTOP; y--) {
    const k = (y - VPy) / (YREF - VPy);
    const x0 = VPx + (xb - VPx) * k;
    let best = -1, sub = 0;
    const v = [];
    for (let dx = -6; dx <= 6; dx++) v.push(lum(x0 + dx, y));
    let bi = 0; for (let i = 0; i < v.length; i++) if (v[i] > best) { best = v[i]; bi = i; }
    sub = bi - 6;
    if (bi > 0 && bi < v.length - 1) {
      const den = v[bi - 1] - 2 * v[bi] + v[bi + 1];
      if (Math.abs(den) > 1e-6) sub = bi - 6 + 0.5 * (v[bi - 1] - v[bi + 1]) / den;
    }
    arr.push({ y, x: x0 + sub, l: best });
  }
  return arr;
}
const smooth = a => a.map((p, i) => {
  const q = [a[i - 2], a[i - 1], a[i], a[i + 1], a[i + 2]].filter(Boolean);
  return { ...p, l: q.reduce((s, z) => s + z.l, 0) / q.length };
});

function findRuns(prof) {
  const ls = prof.map(p => p.l).slice().sort((a, b) => a - b);
  const base = ls[Math.floor(ls.length * 0.25)];
  const mx = ls[ls.length - 1];
  const thr = base + 0.45 * (mx - base);
  let runs = [], st = null;
  for (let i = 0; i < prof.length; i++) {
    if (prof[i].l > thr) { if (st === null) st = i; }
    else if (st !== null) { runs.push([st, i - 1]); st = null; }
  }
  if (st !== null) runs.push([st, prof.length - 1]);
  const mg = [];
  for (const r of runs) {
    if (mg.length && r[0] - mg[mg.length - 1][1] <= 3) mg[mg.length - 1][1] = r[1];
    else mg.push([...r]);
  }
  const interp = (p1, p2) => p1.y + (p2.y - p1.y) * (thr - p1.l) / (p2.l - p1.l);
  const out = [];
  for (const [a, b] of mg) {
    if (a <= 0 || b >= prof.length - 1) continue;          // touches scan edges
    const yFar = interp(prof[b], prof[b + 1]);             // smaller y = farther
    const yNear = interp(prof[a], prof[a - 1]);            // larger y = nearer
    const len = Math.abs(yNear - yFar);
    if (len < 9 || len > 90) continue;
    let sx = 0, n = 0;
    for (let i = a + 1; i < b; i++) { sx += prof[i].x; n++; }
    out.push({ yFar, yNear, u: sx / Math.max(n, 1), len, peak: Math.max(...prof.slice(a, b + 1).map(p => p.l)), thr });
  }
  return { out, thr, base };
}

console.log('=== dashes ===');
const all = [];
LANES.forEach((xb, j) => {
  const { out, thr, base } = findRuns(smooth(profileFor(xb)));
  console.log(`lane ${j} (x719=${xb}) thr=${thr.toFixed(0)} base=${base.toFixed(0)}: ${out.length} runs`);
  out.forEach(o => console.log(`   vFar=${o.yFar.toFixed(2)} vNear=${o.yNear.toFixed(2)} len=${o.len.toFixed(1)} u=${o.u.toFixed(1)} peak=${o.peak.toFixed(0)}`));
  out.forEach(o => all.push({ lane: j, ...o }));
});
fs.writeFileSync('frames/dashes2.json', JSON.stringify(all, null, 1));
