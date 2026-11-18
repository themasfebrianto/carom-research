// Extract white road-marking blobs from a PPM frame.
// Usage: node marks.mjs frame.ppm
import fs from 'node:fs';

const path = process.argv[2] || 'frames/f005.ppm';
const buf = fs.readFileSync(path);

// parse P6 header
let i = 0, fields = [];
while (fields.length < 4) {
  while (i < buf.length && /\s/.test(String.fromCharCode(buf[i]))) i++;
  if (buf[i] === 35) { while (buf[i] !== 10) i++; continue; }
  let s = '';
  while (i < buf.length && !/\s/.test(String.fromCharCode(buf[i]))) s += String.fromCharCode(buf[i++]);
  fields.push(s);
}
while (i < buf.length && /\s/.test(String.fromCharCode(buf[i]))) i++;
const W = +fields[1], H = +fields[2];
const data = buf.subarray(i);
console.log(`PPM ${W}x${H}  data bytes ${data.length}  expected ${W * H * 3}`);

const at = (x, y) => { const o = (y * W + x) * 3; return [data[o], data[o + 1], data[o + 2]]; };

// white-ish mask
const mask = new Uint8Array(W * H);
const YMIN = 40;           // skip the text overlay
for (let y = YMIN; y < H; y++) {
  for (let x = 0; x < W; x++) {
    const [r, g, b] = at(x, y);
    const mn = Math.min(r, g, b), mx = Math.max(r, g, b);
    if (mn > 150 && mx - mn < 45) mask[y * W + x] = 1;
  }
}

// connected components (4-neighbour, iterative)
const lab = new Int32Array(W * H).fill(-1);
const comps = [];
const stack = new Int32Array(W * H);
for (let p0 = 0; p0 < W * H; p0++) {
  if (!mask[p0] || lab[p0] !== -1) continue;
  const id = comps.length;
  let sp = 0; stack[sp++] = p0; lab[p0] = id;
  let n = 0, sx = 0, sy = 0, x0 = 1e9, x1 = -1, y0 = 1e9, y1 = -1;
  while (sp) {
    const p = stack[--sp];
    const x = p % W, y = (p - x) / W;
    n++; sx += x; sy += y;
    if (x < x0) x0 = x; if (x > x1) x1 = x;
    if (y < y0) y0 = y; if (y > y1) y1 = y;
    const nb = [p - 1, p + 1, p - W, p + W];
    for (const q of nb) {
      if (q < 0 || q >= W * H || lab[q] !== -1 || !mask[q]) continue;
      const qx = q % W;
      if (Math.abs(qx - x) > 1) continue;
      lab[q] = id; stack[sp++] = q;
    }
  }
  comps.push({ n, cx: sx / n, cy: sy / n, x0, x1, y0, y1, w: x1 - x0 + 1, h: y1 - y0 + 1 });
}

// candidate lane markings: elongated, thin, modest area
const cand = comps.filter(c =>
  c.n >= 40 && c.w >= 3 && c.w <= 40 && c.h >= 8 &&
  c.h / c.w >= 1.8 && c.n / (c.w * c.h) > 0.45 && c.cy > 380
).sort((a, b) => b.cy - a.cy);

console.log(`\ntotal components ${comps.length}, candidates ${cand.length}`);
console.log('   cx      cy     w    h    n   fill  aspect');
for (const c of cand.slice(0, 60)) {
  console.log(`${c.cx.toFixed(1).padStart(7)} ${c.cy.toFixed(1).padStart(7)} ${String(c.w).padStart(4)} ${String(c.h).padStart(4)} ${String(c.n).padStart(5)}  ${(c.n / (c.w * c.h)).toFixed(2)}  ${(c.h / c.w).toFixed(2)}`);
}
