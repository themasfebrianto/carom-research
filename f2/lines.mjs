// RANSAC line detection for the 480x360 frame.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const d = buf.subarray(off);
const lum = (x, y) => { const o = (y * W + x) * 3; return 0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2]; };

const X0 = 0, X1 = W - 1, Y0 = 145, Y1 = H - 4;
const pts = [];
for (let y = Y0; y <= Y1; y++) {
  let st = null;
  for (let x = X0; x <= X1 + 1; x++) {
    const on = x <= X1 && lum(x, y) > 138;
    if (on) { if (st === null) st = x; }
    else if (st !== null) {
      const w = x - st;
      if (w >= 2 && w <= 14) pts.push([st + (w - 1) / 2, y]);
      st = null;
    }
  }
}
console.log('run centres:', pts.length);

function ransac(tol, iters, minIn) {
  const out = [];
  for (let t = 0; t < iters; t++) {
    const p1 = pts[(Math.random() * pts.length) | 0], p2 = pts[(Math.random() * pts.length) | 0];
    if (Math.abs(p1[1] - p2[1]) < 40) continue;
    const a = (p1[0] - p2[0]) / (p1[1] - p2[1]);
    const b = p1[0] - a * p1[1];
    const inl = pts.filter(q => Math.abs(q[0] - (a * q[1] + b)) < tol);
    if (inl.length >= minIn) out.push({ a, b, n: inl.length, inl });
  }
  return out;
}
const L = ransac(1.5, 6000, 45).sort((p, q) => q.n - p.n);
const keep = [];
for (const l of L) {
  if (keep.every(k => Math.abs(k.a - l.a) > 0.04 || Math.abs(k.b - l.b) > 8)) keep.push(l);
  if (keep.length >= 8) break;
}
console.log('\n #   x@y=340 x@y=250 x@y=160     a        b    inl  yspan');
keep.forEach((l, k) => {
  const ys = l.inl.map(p => p[1]);
  console.log(`${String(k).padStart(2)} ${(l.a * 340 + l.b).toFixed(1).padStart(8)} ${(l.a * 250 + l.b).toFixed(1).padStart(8)} ${(l.a * 160 + l.b).toFixed(1).padStart(8)} ${l.a.toFixed(4).padStart(8)} ${l.b.toFixed(1).padStart(8)} ${String(l.n).padStart(4)} ${Math.min(...ys)}-${Math.max(...ys)}`);
});
fs.writeFileSync('f2/lines.json', JSON.stringify(keep.map(l => ({ a: l.a, b: l.b, n: l.n })), null, 1));
