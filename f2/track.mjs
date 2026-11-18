// Track the right edge line upward from the bottom, always picking the run
// closest to the prediction. Then test straightness.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const d = buf.subarray(off);
const px = (x, y) => { const o = (y * W + x) * 3; return [d[o], d[o + 1], d[o + 2]]; };
const isWhite = ([r, g, b]) => Math.min(r, g, b) > 138 && Math.max(r, g, b) - Math.min(r, g, b) < 42;

function runs(y) {
  const out = []; let st = null;
  for (let x = 0; x <= W; x++) {
    const on = x < W && isWhite(px(x, y));
    if (on) { if (st === null) st = x; }
    else if (st !== null) { const w = x - st; if (w >= 1 && w <= 16) out.push({ c: st + (w - 1) / 2, w }); st = null; }
  }
  return out;
}

// seed at the bottom row: the right edge is the first narrow run right of x=320
let y0 = 352, seed = null;
for (const r of runs(y0)) if (r.c > 320 && r.c < 420) { seed = r.c; break; }
console.log('seed at y=%d : x=%s', y0, seed?.toFixed(1));

const track = [{ y: y0, x: seed }];
let pred = seed, slope = -0.7;
for (let y = y0 - 1; y >= 150; y--) {
  pred -= slope;
  const cands = runs(y).filter(r => r.c > 300 && Math.abs(r.c - pred) < 16);
  if (!cands.length) continue;
  const best = cands.reduce((a, b) => Math.abs(a.c - pred) <= Math.abs(b.c - pred) ? a : b);
  track.push({ y, x: best.c });
  if (track.length > 8) {
    const p = track[track.length - 8];
    slope = 0.7 * slope + 0.3 * ((best.c - p.x) / (y - p.y));
  }
}
console.log('tracked %d rows, y range %d..%d', track.length, track[track.length - 1].y, track[0].y);

const n = track.length; let sx = 0, sy = 0, sxx = 0, sxy = 0;
for (const p of track) { sx += p.x; sy += p.y; sxy += p.x * p.y; sxx += p.y * p.y; }
const a = (n * sxy - sx * sy) / (n * sxx - sy * sy), b = (sx - a * sy) / n;
let ss = 0;
for (const p of track) { const r = p.x - (a * p.y + b); ss += r * r; }
console.log('\nfit garis lurus: x = %s y + %s   RMS = %s px', a.toFixed(4), b.toFixed(1), Math.sqrt(ss / n).toFixed(2));

// slope in three bands
const band = (lo, hi) => {
  const q = track.filter(p => p.y >= lo && p.y <= hi);
  if (q.length < 5) return null;
  const m = q.length; let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (const p of q) { sx += p.x; sy += p.y; sxy += p.x * p.y; sxx += p.y * p.y; }
  return (m * sxy - sx * sy) / (m * sxx - sy * sy);
};
console.log('\nkemiringan per pita:');
for (const [lo, hi] of [[150, 200], [200, 250], [250, 300], [300, 355]]) {
  const s = band(lo, hi);
  console.log(`  y ${lo}-${hi}: ${s === null ? '-' : s.toFixed(4)}`);
}
// residual trend
const res = track.map(p => ({ y: p.y, r: p.x - (a * p.y + b) })).sort((p, q) => q.y - p.y);
const head = res.slice(0, 10).reduce((s, p) => s + p.r, 0) / 10;
const tail = res.slice(-10).reduce((s, p) => s + p.r, 0) / 10;
console.log('\ntren residual (bawah -> atas) = %s px', (tail - head).toFixed(2));
console.log('(garis lurus sejati: |tren| < 2 px)');
