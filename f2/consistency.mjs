// Quantify geometric consistency: fit lines over different ranges, compare VPs.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const d = buf.subarray(off);
const px = (x, y) => { const o = (y * W + x) * 3; return [d[o], d[o + 1], d[o + 2]]; };
const isYellow = ([r, g, b]) => r > 140 && g > 110 && b < 110 && r - b > 55;
const isWhite = ([r, g, b]) => Math.min(r, g, b) > 140 && Math.max(r, g, b) - Math.min(r, g, b) < 40;

function centres(y, pred, x0, x1, maxW = 14) {
  const out = []; let st = null;
  for (let x = x0; x <= x1 + 1; x++) {
    const on = x <= x1 && pred(px(x, y));
    if (on) { if (st === null) st = x; }
    else if (st !== null) { const w = x - st; if (w >= 1 && w <= maxW) out.push(st + (w - 1) / 2); st = null; }
  }
  return out;
}
function fit(pts) {
  const n = pts.length; let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (const [x, y] of pts) { sx += x; sy += y; sxy += x * y; sxx += y * y; }
  const a = (n * sxy - sx * sy) / (n * sxx - sy * sy);
  const b = (sx - a * sy) / n;
  let ss = 0;
  for (const [x, y] of pts) { const r = x - (a * y + b); ss += r * r; }
  return { a, b, n, rms: Math.sqrt(ss / n), pts };
}
function vp(L1, L2) {
  if (Math.abs(L1.a - L2.a) < 1e-9) return null;
  const y = (L2.b - L1.b) / (L1.a - L2.a);
  return { x: L1.a * y + L1.b, y };
}

const Y = [];
for (let y = 150; y <= 268; y++) for (const c of centres(y, isYellow, 0, 340, 8)) Y.push([c, y]);
const yellow = fit(Y);
// right edge: white, right side. avoid the barrier beyond x>430
const R1 = [], R2 = [];
for (let y = 250; y <= 350; y++) for (const c of centres(y, isWhite, 320, 420, 14)) { R1.push([c, y]); R2.push([c, y]); }
const R3 = [];
for (let y = 150; y <= 350; y++) for (const c of centres(y, isWhite, 330, 420, 14)) R3.push([c, y]);

const rNear = fit(R1), rFull = fit(R3);
console.log('yellow     : a=%s b=%s rms=%s n=%d', yellow.a.toFixed(3), yellow.b.toFixed(1), yellow.rms.toFixed(2), yellow.n);
console.log('right near : a=%s b=%s rms=%s n=%d  (y 250-350)', rNear.a.toFixed(3), rNear.b.toFixed(1), rNear.rms.toFixed(2), rNear.n);
console.log('right full : a=%s b=%s rms=%s n=%d  (y 150-350)', rFull.a.toFixed(3), rFull.b.toFixed(1), rFull.rms.toFixed(2), rFull.n);

const v1 = vp(yellow, rNear), v2 = vp(yellow, rFull);
console.log('\nVP yellow x right(near) = (%s, %s)', v1.x.toFixed(0), v1.y.toFixed(0));
console.log('VP yellow x right(full) = (%s, %s)', v2.x.toFixed(0), v2.y.toFixed(0));
console.log('selisih = %s px', Math.hypot(v1.x - v2.x, v1.y - v2.y).toFixed(0));

// residual of a single straight right-edge model over the full span
const resFull = R3.map(([x, y]) => x - (rFull.a * y + rFull.b));
const trend = (() => { const lo = resFull.slice(0, 20).reduce((s, v) => s + v, 0) / 20; const hi = resFull.slice(-20).reduce((s, v) => s + v, 0) / 20; return hi - lo; })();
console.log('\nresidual tepi kanan: RMS %s px, tren (bawah-atas) %s px', rFull.rms.toFixed(2), trend.toFixed(2));
console.log('=> tren > 3 px menandakan jalan melengkung, bukan garis lurus');
