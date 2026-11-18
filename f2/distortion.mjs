// Is the right edge curved, or is it radial distortion?
// Joint test: find k1 that straightens BOTH the yellow line and the right edge.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const d = buf.subarray(off);
const px = (x, y) => { const o = (y * W + x) * 3; return [d[o], d[o + 1], d[o + 2]]; };
const isYellow = ([r, g, b]) => r > 140 && g > 110 && b < 110 && r - b > 55;
const isWhite = ([r, g, b]) => Math.min(r, g, b) > 140 && Math.max(r, g, b) - Math.min(r, g, b) < 40;

function centres(y, pred, x0, x1, maxW) {
  const out = []; let st = null;
  for (let x = x0; x <= x1 + 1; x++) {
    const on = x <= x1 && pred(px(x, y));
    if (on) { if (st === null) st = x; }
    else if (st !== null) { const w = x - st; if (w >= 1 && w <= maxW) out.push(st + (w - 1) / 2); st = null; }
  }
  return out;
}

// yellow: leftmost yellow run per row
const YEL = [];
for (let y = 150; y <= 268; y++) {
  const c = centres(y, isYellow, 0, 340, 8);
  if (c.length) YEL.push([c[0], y]);
}
// right edge: leftmost white run in x 320..470
const RED = [];
for (let y = 150; y <= 350; y++) {
  const c = centres(y, isWhite, 320, 470, 14);
  if (c.length) RED.push([c[0], y]);
}
console.log(`yellow pts ${YEL.length}, right-edge pts ${RED.length}`);

const CX = W / 2, CY = H / 2;
function undistort(p, k1) {
  const dx = p[0] - CX, dy = p[1] - CY, r2 = dx * dx + dy * dy;
  const s = 1 + k1 * r2;
  return [CX + dx * s, CY + dy * s];
}
function lineRms(pts, k1) {
  const P = pts.map(p => undistort(p, k1));
  const n = P.length; let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (const [x, y] of P) { sx += x; sy += y; sxy += x * y; sxx += y * y; }
  const a = (n * sxy - sx * sy) / (n * sxx - sy * sy);
  const b = (sx - a * sy) / n;
  let ss = 0;
  for (const [x, y] of P) { const r = x - (a * y + b); ss += r * r; }
  return Math.sqrt(ss / n);
}

console.log('\n   k1        RMS kuning   RMS tepi kanan   jumlah');
let best = null;
for (let k1 = -2.0e-6; k1 <= 2.01e-6; k1 += 0.2e-6) {
  const ry = lineRms(YEL, k1), rr = lineRms(RED, k1);
  const tot = ry + rr;
  if (!best || tot < best.tot) best = { k1, ry, rr, tot };
  console.log(`${(k1 * 1e6).toFixed(1).padStart(6)}e-6   ${ry.toFixed(2).padStart(9)}   ${rr.toFixed(2).padStart(13)}   ${tot.toFixed(2).padStart(7)}`);
}
console.log(`\nk1 terbaik = ${(best.k1 * 1e6).toFixed(2)}e-6 : kuning ${best.ry.toFixed(2)} px, tepi ${best.rr.toFixed(2)} px`);

// residual profile of the right edge at k1=0 and at the best k1
console.log('\nsisaan tepi kanan per baris (k1=0 vs k1 terbaik):');
for (const k1 of [0, best.k1]) {
  const P = RED.map(p => undistort(p, k1));
  const n = P.length; let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (const [x, y] of P) { sx += x; sy += y; sxy += x * y; sxx += y * y; }
  const a = (n * sxy - sx * sy) / (n * sxx - sy * sy), b = (sx - a * sy) / n;
  const r = P.map(([x, y]) => x - (a * y + b));
  const head = r.slice(0, 6).reduce((s, v) => s + v, 0) / 6;
  const tail = r.slice(-6).reduce((s, v) => s + v, 0) / 6;
  console.log(`  k1=${(k1 * 1e6).toFixed(1)}e-6 : tren hujung-ke-hujung = ${(tail - head).toFixed(2)} px`);
}
