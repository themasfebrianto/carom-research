// Connected components of bright (luma) pixels in the road region.
import fs from 'node:fs';
const path = process.argv[2] || 'frames/f005.ppm';
const THR = +(process.argv[3] || 150);
const YMIN = +(process.argv[4] || 420);

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

const mask = new Uint8Array(W * H);
for (let y = YMIN; y < H; y++) {
  for (let x = 0; x < W; x++) {
    const o = (y * W + x) * 3;
    const L = 0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2];
    if (L > THR) mask[y * W + x] = 1;
  }
}
const lab = new Int32Array(W * H).fill(-1);
const stack = new Int32Array(W * H);
const comps = [];
for (let p0 = 0; p0 < W * H; p0++) {
  if (!mask[p0] || lab[p0] !== -1) continue;
  const id = comps.length;
  let sp = 0; stack[sp++] = p0; lab[p0] = id;
  let n = 0, sx = 0, sy = 0, x0 = 1e9, x1 = -1, y0 = 1e9, y1 = -1;
  while (sp) {
    const p = stack[--sp]; const x = p % W, y = (p - x) / W;
    n++; sx += x; sy += y;
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    for (const q of [p - 1, p + 1, p - W, p + W]) {
      if (q < 0 || q >= W * H || lab[q] !== -1 || !mask[q]) continue;
      if (Math.abs((q % W) - x) > 1) continue;
      lab[q] = id; stack[sp++] = q;
    }
  }
  comps.push({ n, cx: sx / n, cy: sy / n, x0, x1, y0, y1, w: x1 - x0 + 1, h: y1 - y0 + 1 });
}
const cand = comps.filter(c => c.n >= 45 && c.w >= 3 && c.w <= 60 && c.h >= 6 && c.h <= 260)
  .sort((a, b) => b.cy - a.cy);
console.log(`comps ${comps.length}  candidates ${cand.length}`);
console.log('   cx      cy     x0    y0    w    h     n   aspect fill');
for (const c of cand.slice(0, 90))
  console.log(`${c.cx.toFixed(1).padStart(7)} ${c.cy.toFixed(1).padStart(6)} ${String(c.x0).padStart(5)} ${String(c.y0).padStart(5)} ${String(c.w).padStart(4)} ${String(c.h).padStart(4)} ${String(c.n).padStart(5)}  ${(c.h / c.w).toFixed(2).padStart(5)} ${(c.n / (c.w * c.h)).toFixed(2)}`);
