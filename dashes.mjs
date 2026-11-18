// Dash blob picker with explicit ROI + shape filter.
import fs from 'node:fs';
const path = process.argv[2] || 'frames/median.ppm';
const THR = +(process.argv[3] || 150);
const [X0, X1, Y0, Y1] = process.argv.slice(4, 8).map(Number);

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

const mask = new Uint8Array(W * H);
for (let y = Y0; y <= Y1; y++) for (let x = X0; x <= X1; x++) if (lum(x, y) > THR) mask[y * W + x] = 1;

const lab = new Int32Array(W * H).fill(-1);
const st = new Int32Array(W * H);
const out = [];
for (let p0 = Y0 * W + X0; p0 < Y1 * W + X1; p0++) {
  if (!mask[p0] || lab[p0] !== -1) continue;
  const id = out.length; let sp = 0; st[sp++] = p0; lab[p0] = id;
  let n = 0, sx = 0, sy = 0, x0 = 1e9, x1 = -1, y0 = 1e9, y1 = -1;
  while (sp) {
    const p = st[--sp], x = p % W, y = (p - x) / W;
    n++; sx += x; sy += y;
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    for (const q of [p - 1, p + 1, p - W, p + W]) {
      if (q < 0 || q >= W * H || lab[q] !== -1 || !mask[q]) continue;
      const qx = q % W, qy = (q - qx) / W;
      if (Math.abs(qx - x) > 1 || qy < Y0 || qy > Y1) continue;
      lab[q] = id; st[sp++] = q;
    }
  }
  out.push({ n, cx: sx / n, cy: sy / n, x0, x1, y0, y1, w: x1 - x0 + 1, h: y1 - y0 + 1 });
}
// dash-like: slender, diagonal, area in range
const dashes = out.filter(c =>
  c.n >= 90 && c.n <= 3000 &&
  c.h >= 12 && c.h <= 190 &&
  c.h / c.w >= 1.2 &&
  c.n / (c.w * c.h) > 0.22
).sort((a, b) => b.cy - a.cy);

console.log(`comps ${out.length}  dashes ${dashes.length}`);
console.log('  idx   cx       cy      x0   y0    w    h    area  aspect  fill');
dashes.forEach((c, k) => console.log(
  `${String(k).padStart(4)} ${c.cx.toFixed(1).padStart(7)} ${c.cy.toFixed(1).padStart(7)} ${String(c.x0).padStart(5)} ${String(c.y0).padStart(4)} ${String(c.w).padStart(4)} ${String(c.h).padStart(4)} ${String(c.n).padStart(6)} ${(c.h / c.w).toFixed(2).padStart(6)} ${(c.n / (c.w * c.h)).toFixed(2)}`
));
fs.writeFileSync('frames/dashes.json', JSON.stringify(dashes.map(c => ({ cx: c.cx, cy: c.cy, w: c.w, h: c.h, n: c.n })), null, 1));
