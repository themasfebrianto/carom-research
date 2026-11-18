// RANSAC line finder with ROI + luma threshold, for the clean median frame.
import fs from 'node:fs';
const path = process.argv[2] || 'frames/median.ppm';
const THR = +(process.argv[3] || 165);
const X0 = +(process.argv[4] || 0), X1 = +(process.argv[5] || 1279);
const Y0 = +(process.argv[6] || 420), Y1 = +(process.argv[7] || 719);

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
const lum = (x, y) => { const o = (y * W + x) * 3; return 0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2]; };

const pts = [];
for (let y = Y0; y <= Math.min(Y1, H - 1); y++) {
  let inr = false, st = 0;
  for (let x = X0; x <= Math.min(X1, W - 1) + 1; x++) {
    const on = x <= Math.min(X1, W - 1) && lum(x, y) > THR;
    if (on) { if (!inr) { inr = true; st = x; } }
    else if (inr) {
      const w = x - st;
      if (w >= 2 && w <= 30) pts.push([st + (w - 1) / 2, y]);
      inr = false;
    }
  }
}
console.log(`ROI x[${X0},${X1}] y[${Y0},${Y1}] thr ${THR} -> ${pts.length} run-centres`);

function ransac(tol, iters, minIn) {
  const out = [];
  for (let t = 0; t < iters; t++) {
    const p1 = pts[(Math.random() * pts.length) | 0], p2 = pts[(Math.random() * pts.length) | 0];
    if (Math.abs(p1[1] - p2[1]) < 80) continue;
    const a = (p1[0] - p2[0]) / (p1[1] - p2[1]);
    const b = p1[0] - a * p1[1];
    const inl = pts.filter(q => Math.abs(q[0] - (a * q[1] + b)) < tol);
    if (inl.length >= minIn) out.push({ a, b, n: inl.length, inl });
  }
  return out;
}
let L = ransac(1.8, 3000, 40).sort((p, q) => q.n - p.n);
const keep = [];
for (const l of L) {
  if (keep.every(k => Math.abs(k.a - l.a) > 0.05 || Math.abs(k.b - l.b) > 10)) keep.push(l);
  if (keep.length >= 8) break;
}
console.log('\n #   x@y=700 x@y=650 x@y=550 x@y=450     a         b    inl  yspan   length');
keep.forEach((l, k) => {
  const ys = l.inl.map(p => p[1]);
  console.log(`${String(k).padStart(2)} ${(l.a * 700 + l.b).toFixed(1).padStart(8)} ${(l.a * 650 + l.b).toFixed(1).padStart(7)} ${(l.a * 550 + l.b).toFixed(1).padStart(7)} ${(l.a * 450 + l.b).toFixed(1).padStart(7)} ${l.a.toFixed(4).padStart(7)} ${l.b.toFixed(1).padStart(8)} ${String(l.n).padStart(4)} ${Math.min(...ys)}-${Math.max(...ys)}`);
});
// VP of the dominant family: intersect line0 and line1
if (keep.length >= 2) {
  const [p, q] = keep;
  if (Math.abs(p.a - q.a) > 1e-6) {
    const yv = (q.b - p.b) / (p.a - q.a), xv = p.a * yv + p.b;
    console.log(`\nVP(0,1) = (${xv.toFixed(1)}, ${yv.toFixed(1)})`);
  }
}
fs.writeFileSync('frames/lines2.json', JSON.stringify(keep.map(l => ({ a: l.a, b: l.b, n: l.n })), null, 1));
