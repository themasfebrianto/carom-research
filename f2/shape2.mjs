// Track both lines, then test whether the bow is distortion or road curvature.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const d = buf.subarray(off);
const px = (x, y) => { const o = (y * W + x) * 3; return [d[o], d[o + 1], d[o + 2]]; };
const isY = ([r, g, b]) => r > 140 && g > 105 && b < 115 && r - b > 50;
const isW = ([r, g, b]) => Math.min(r, g, b) > 136 && Math.max(r, g, b) - Math.min(r, g, b) < 45;

function runsAt(y, pred, x0, x1) {
  const out = []; let st = null;
  for (let x = x0; x <= x1; x++) {
    const on = pred(px(x, y));
    if (on) { if (st === null) st = x; }
    else if (st !== null) { const w = x - st; if (w >= 1 && w <= 16) out.push(st + (w - 1) / 2); st = null; }
  }
  return out;
}
// generic tracker: start at (y0,x0), walk up, step computed from dx/dy sign
function track(pred, y0, x0, step, yTop) {
  const pts = [[x0, y0]];
  let x = x0, s = step;
  for (let y = y0 - 1; y >= yTop; y--) {
    x += s;
    const c = runsAt(y, pred, Math.max(0, Math.round(x) - 14), Math.min(W - 1, Math.round(x) + 14));
    if (!c.length) continue;
    const b = c.reduce((a, q) => Math.abs(a - x) <= Math.abs(q - x) ? a : q);
    pts.push([b, y]);
    if (pts.length > 6) {
      const p = pts[pts.length - 6];
      const inst = (b - p[0]) / (y - p[1]);
      s = 0.7 * s + 0.3 * inst;
    }
    x = b;
  }
  return pts;
}

// yellow: at y=268 near x≈7; step +2.7 (x grows as y shrinks)
const yStart = 266;
const y0c = runsAt(yStart, isY, 0, 45);
const YEL = y0c.length ? track(isY, yStart, y0c[0], 2.7, 150) : [];
// right edge: at y=352 x≈331; step +0.62
const r0c = runsAt(352, isW, 300, 420);
const RED = r0c.length ? track(isW, 352, r0c[0], 0.62, 150) : [];
console.log('yellow pts', YEL.length, YEL.length ? `y ${YEL.at(-1)[1]}..${YEL[0][1]}` : '');
console.log('right  pts', RED.length, RED.length ? `y ${RED.at(-1)[1]}..${RED[0][1]}` : '');
if (!YEL.length || !RED.length) process.exit(1);

const CX = W / 2, CY = H / 2;
const und = ([x, y], k1) => {
  const dx = x - CX, dy = y - CY, s = 1 + k1 * (dx * dx + dy * dy);
  return [CX + dx * s, CY + dy * s];
};
const fitLine = P => {
  const n = P.length; let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (const [x, y] of P) { sx += x; sy += y; sxy += x * y; sxx += y * y; }
  const a = (n * sxy - sx * sy) / (n * sxx - sy * sy), b = (sx - a * sy) / n;
  let ss = 0; for (const [x, y] of P) { const r = x - (a * y + b); ss += r * r; }
  return { a, b, rms: Math.sqrt(ss / n) };
};
const bands = P => [[150, 200], [200, 250], [250, 300], [300, 360]].map(([lo, hi]) => {
  const q = P.filter(p => p[1] >= lo && p[1] <= hi);
  return q.length >= 8 ? fitLine(q).a : null;
});

console.log('\nkemiringan per pita (dx/dy):');
console.log('  kuning      ', bands(YEL).map(v => v === null ? '  -   ' : v.toFixed(3)).join('  '));
console.log('  tepi kanan  ', bands(RED).map(v => v === null ? '  -   ' : v.toFixed(3)).join('  '));

const spread = a => { const v = a.filter(x => x !== null); return v.length ? Math.max(...v) - Math.min(...v) : NaN; };
console.log('  sebaran kuning     %s', spread(bands(YEL)).toFixed(3));
console.log('  sebaran tepi kanan %s', spread(bands(RED)).toFixed(3));

console.log('\nuji k1 (distorsi radial) — RMS tiap garis:');
let best = null;
for (let k1 = -1.6e-6; k1 <= 1.61e-6; k1 += 0.1e-6) {
  const a = fitLine(YEL.map(p => und(p, k1))), b = fitLine(RED.map(p => und(p, k1)));
  const t = a.rms + b.rms;
  if (!best || t < best.t) best = { k1, a, b, t };
}
for (const k1 of [0, -0.4e-6, -0.8e-6, best.k1]) {
  const a = fitLine(YEL.map(p => und(p, k1))), b = fitLine(RED.map(p => und(p, k1)));
  console.log(`  k1=${(k1 * 1e6).toFixed(1)}e-6  kuning ${a.rms.toFixed(2)}  tepi ${b.rms.toFixed(2)}  | sebaran ${spread(bands(YEL.map(p => und(p, k1)))).toFixed(3)} / ${spread(bands(RED.map(p => und(p, k1)))).toFixed(3)}`);
}
console.log('\nk1 terbaik = %se-6 (RMS gabungan %s)', (best.k1 * 1e6).toFixed(1), best.t.toFixed(2));
fs.writeFileSync('f2/tracked.json', JSON.stringify({ YEL, RED }));
