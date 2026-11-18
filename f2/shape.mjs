// Compare bow of the yellow line vs the right edge, and test whether a single
// radial-distortion coefficient explains both.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const d = buf.subarray(off);
const px = (x, y) => { const o = (y * W + x) * 3; return [d[o], d[o + 1], d[o + 2]]; };
const isYellow = ([r, g, b]) => r > 140 && g > 110 && b < 110 && r - b > 55;
const isWhite = ([r, g, b]) => Math.min(r, g, b) > 138 && Math.max(r, g, b) - Math.min(r, g, b) < 42;
const runs = (y, pred, x0, x1, maxW) => {
  const out = []; let st = null;
  for (let x = x0; x <= x1 + 1; x++) {
    const on = x <= x1 && pred(px(x, y));
    if (on) { if (st === null) st = x; }
    else if (st !== null) { const w = x - st; if (w >= 1 && w <= maxW) out.push(st + (w - 1) / 2); st = null; }
  }
  return out;
};

// --- yellow, tracked from the bottom
const YEL = [];
let pred = runs(268, isYellow, 0, 40, 10)[0];
for (let y = 268; y >= 150; y--) {
  const c = runs(y, isYellow, Math.max(0, pred - 12), pred + 12, 10);
  if (!c.length) continue;
  const b = c.reduce((a, q) => Math.abs(a - pred) <= Math.abs(q - pred) ? a : q);
  YEL.push([b, y]);
  pred = b + (y > 151 ? -2.7 : 0);
}
// --- right edge, tracked
const RED = [];
let seed = runs(352, isWhite, 300, 420, 16)[0];
pred = seed;
for (let y = 352; y >= 150; y--) {
  const c = runs(y, isWhite, pred - 14, pred + 14, 16);
  if (!c.length) continue;
  const b = c.reduce((a, q) => Math.abs(a - pred) <= Math.abs(q - pred) ? a : q);
  RED.push([b, y]);
  pred = b - 0.62;
}
console.log('yellow pts %d, right pts %d', YEL.length, RED.length);

const CX = W / 2, CY = H / 2;
const und = ([x, y], k1) => {
  const dx = x - CX, dy = y - CY, r2 = dx * dx + dy * dy, s = 1 + k1 * r2;
  return [CX + dx * s, CY + dy * s];
};
function stats(P) {
  const n = P.length; let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (const [x, y] of P) { sx += x; sy += y; sxy += x * y; sxx += y * y; }
  const a = (n * sxy - sx * sy) / (n * sxx - sy * sy), b = (sx - a * sy) / n;
  let ss = 0; for (const [x, y] of P) { const r = x - (a * y + b); ss += r * r; }
  return { a, b, rms: Math.sqrt(ss / n) };
}
function bandSlopes(P) {
  const out = [];
  for (const [lo, hi] of [[150, 200], [200, 250], [250, 300], [300, 355]]) {
    const q = P.filter(p => p[1] >= lo && p[1] <= hi);
    if (q.length < 5) { out.push(null); continue; }
    out.push(stats(q).a);
  }
  return out;
}
console.log('\nkemiringan per pita:');
console.log('  kuning     :', bandSlopes(YEL).map(v => v === null ? '  -  ' : v.toFixed(3)).join('  '));
console.log('  tepi kanan :', bandSlopes(RED).map(v => v === null ? '  -  ' : v.toFixed(3)).join('  '));

console.log('\nuji distorsi radial (k1):');
let best = null;
for (let k1 = -1.5e-6; k1 <= 1.51e-6; k1 += 0.1e-6) {
  const sy = stats(YEL.map(p => und(p, k1)));
  const sr = stats(RED.map(p => und(p, k1)));
  const tot = sy.rms + sr.rms;
  if (!best || tot < best.tot) best = { k1, sy, sr, tot };
}
for (const k1 of [0, -0.5e-6, -1.0e-6, best.k1]) {
  const sy = stats(YEL.map(p => und(p, k1)));
  const sr = stats(RED.map(p => und(p, k1)));
  const by = bandSlopes(YEL.map(p => und(p, k1)));
  const br = bandSlopes(RED.map(p => und(p, k1)));
  console.log(`  k1=${(k1 * 1e6).toFixed(1)}e-6  rms kuning ${sy.rms.toFixed(2)}  rms tepi ${sr.rms.toFixed(2)}`);
  console.log(`               pita kuning ${by.map(v => v === null ? '-' : v.toFixed(3)).join(' ')}`);
  console.log(`               pita tepi   ${br.map(v => v === null ? '-' : v.toFixed(3)).join(' ')}`);
}
const spread = a => { const v = a.filter(x => x !== null); return Math.max(...v) - Math.min(...v); };
console.log('\nsebaran kemiringan antar pita (indikator lengkung):');
console.log('  kuning     : %s', spread(bandSlopes(YEL)).toFixed(3));
console.log('  tepi kanan : %s', spread(bandSlopes(RED)).toFixed(3));
