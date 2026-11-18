// Re-track the RIGHT EDGE but always take the LEFTMOST candidate run
// (the painted line is left of the railing). Compare straightness.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const d = buf.subarray(off);
const px = (x, y) => { const o = (y * W + x) * 3; return [d[o], d[o + 1], d[o + 2]]; };
const isW = ([r, g, b]) => Math.min(r, g, b) > 136 && Math.max(r, g, b) - Math.min(r, g, b) < 45;

function runsAt(y, x0, x1) {
  const out = []; let st = null;
  for (let x = x0; x <= x1; x++) {
    const on = isW(px(x, y));
    if (on) { if (st === null) st = x; }
    else if (st !== null) { const w = x - st; if (w >= 1 && w <= 16) out.push(st + (w - 1) / 2); st = null; }
  }
  return out;
}
function track(y0, x0, step, yTop, win, pick) {
  const pts = [[x0, y0]];
  let x = x0, s = step;
  for (let y = y0 - 1; y >= yTop; y--) {
    x += s;
    const c = runsAt(y, Math.max(0, Math.round(x) - win), Math.min(W - 1, Math.round(x) + win));
    if (!c.length) continue;
    const b = pick === 'left' ? Math.min(...c)
      : pick === 'right' ? Math.max(...c)
        : c.reduce((a, q) => Math.abs(a - x) <= Math.abs(q - x) ? a : q);
    pts.push([b, y]);
    if (pts.length > 6) { const p = pts[pts.length - 6]; s = 0.7 * s + 0.3 * ((b - p[0]) / (y - p[1])); }
    x = b;
  }
  return pts;
}
const fit = P => {
  const n = P.length; let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (const [x, y] of P) { sx += x; sy += y; sxy += x * y; sxx += y * y; }
  const a = (n * sxy - sx * sy) / (n * sxx - sy * sy), b = (sx - a * sy) / n;
  let ss = 0; for (const [x, y] of P) { const r = x - (a * y + b); ss += r * r; }
  return { a, b, rms: Math.sqrt(ss / n), n };
};
const bands = (P) => [[150, 200], [200, 250], [250, 300], [300, 360]].map(([lo, hi]) => {
  const q = P.filter(p => p[1] >= lo && p[1] <= hi);
  return q.length >= 8 ? fit(q).a : null;
});

const seed = runsAt(352, 300, 420)[0];
for (const pick of ['nearest', 'left']) {
  const P = track(352, seed, 0.62, 150, 14, pick);
  const f = fit(P), b = bands(P);
  const v = b.filter(v => v !== null);
  console.log('pick=%-8s n=%d  a=%s  rms=%s  bands %s  spread=%s',
    pick, P.length, f.a.toFixed(4), f.rms.toFixed(2), b.map(v => v === null ? ' - ' : v.toFixed(3)).join(' '),
    (Math.max(...v) - Math.min(...v)).toFixed(3));
  fs.writeFileSync(`f2/red_${pick}.json`, JSON.stringify(P));
}

// where do the two picks diverge?
const near = JSON.parse(fs.readFileSync('f2/red_nearest.json'));
const left = JSON.parse(fs.readFileSync('f2/red_left.json'));
console.log('\nsampel perbandingan (y, nearest, left, selisih):');
for (const y of [340, 300, 260, 220, 190, 160, 150]) {
  const a = near.find(p => p[1] === y), b = left.find(p => p[1] === y);
  if (a && b) console.log(`  y=${y}  ${a[0].toFixed(1)}  ${b[0].toFixed(1)}  ${(b[0] - a[0]).toFixed(1)}`);
}
