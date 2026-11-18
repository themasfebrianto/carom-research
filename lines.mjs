// Detect straight lines (lane markings) from narrow bright horizontal runs.
// Usage: node lines.mjs frame.ppm [yTop] [yBot]
import fs from 'node:fs';

const path = process.argv[2] || 'frames/f005.ppm';
const yTop = +(process.argv[3] || 430);
const yBot = +(process.argv[4] || 719);

const buf = fs.readFileSync(path);
let i = 0; const f = [];
while (f.length < 4) {
  while (/\s/.test(String.fromCharCode(buf[i]))) i++;
  if (buf[i] === 35) { while (buf[i] !== 10) i++; continue; }
  let s = '';
  while (!/\s/.test(String.fromCharCode(buf[i]))) s += String.fromCharCode(buf[i++]);
  f.push(s);
}
while (/\s/.test(String.fromCharCode(buf[i]))) i++;
const W = +f[1], H = +f[2];
const d = buf.subarray(i);
const at = (x, y) => { const o = (y * W + x) * 3; return [d[o], d[o + 1], d[o + 2]]; };

// collect narrow bright runs
const pts = [];
for (let y = yTop; y <= yBot; y++) {
  let inr = false, st = 0, peak = 0;
  for (let x = 0; x <= W; x++) {
    const mn = x < W ? Math.min(...at(x, y)) : 0;
    if (x < W && mn > 165) {
      if (!inr) { inr = true; st = x; peak = 0; }
      peak = Math.max(peak, mn);
    } else if (inr) {
      const w = x - st;
      if (w >= 2 && w <= 26) pts.push([st + (x - 1 - st) / 2, y, peak, w]);
      inr = false;
    }
  }
}
console.log(`points ${pts.length}`);

// RANSAC on (x, y): line as x = a*y + b
function ransac(pts, tol, iters, minIn) {
  const found = [];
  for (let t = 0; t < iters; t++) {
    const p1 = pts[(Math.random() * pts.length) | 0], p2 = pts[(Math.random() * pts.length) | 0];
    if (Math.abs(p1[1] - p2[1]) < 60) continue;
    const a = (p1[0] - p2[0]) / (p1[1] - p2[1]);
    const b = p1[0] - a * p1[1];
    const inl = pts.filter(q => Math.abs(q[0] - (a * q[1] + b)) < tol);
    if (inl.length >= minIn) found.push({ a, b, n: inl.length, inl });
  }
  return found;
}
let L = ransac(pts, 2.0, 4000, 55);
// de-duplicate by (a,b) proximity
L.sort((p, q) => q.n - p.n);
const keep = [];
for (const l of L) {
  if (keep.every(k => Math.abs(k.a - l.a) > 0.06 || Math.abs(k.b - l.b) > 12)) keep.push(l);
  if (keep.length >= 12) break;
}
console.log('\n  #   x@y=700  x@y=600  x@y=450     a        b     inliers  yspan');
keep.forEach((l, k) => {
  const ys = l.inl.map(p => p[1]);
  console.log(`${String(k).padStart(3)} ${(l.a * 700 + l.b).toFixed(1).padStart(9)} ${(l.a * 600 + l.b).toFixed(1).padStart(9)} ${(l.a * 450 + l.b).toFixed(1).padStart(9)} ${l.a.toFixed(3).padStart(8)} ${l.b.toFixed(1).padStart(9)} ${String(l.n).padStart(7)}  ${Math.min(...ys)}-${Math.max(...ys)}`);
});
fs.writeFileSync('frames/lines.json', JSON.stringify(keep.map(l => ({ a: l.a, b: l.b, n: l.n })), null, 1));
