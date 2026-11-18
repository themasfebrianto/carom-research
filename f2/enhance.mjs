// Does sharpening / upscaling / sub-pixel centroiding improve line extraction?
// Reports band slopes (geometry) and RMS (precision) in ORIGINAL pixel units.
import fs from 'node:fs';

const file = process.argv[2] || 'f2/median.ppm';
const SC = +(process.argv[3] || 1);         // image scale relative to original
const MODE = process.argv[4] || 'centroid'; // 'threshold' | 'centroid'

const buf = fs.readFileSync(file);
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const d = buf.subarray(off);
const lum = (x, y) => {
  if (x < 0 || y < 0 || x >= W || y >= H) return 0;
  const o = (y * W + x) * 3;
  return 0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2];
};

// sub-pixel centre of a bright band inside [x0,x1]
function centroid(y, x0, x1) {
  let bg = 1e9;
  for (let x = x0; x <= x1; x++) bg = Math.min(bg, lum(x, y));
  let sw = 0, swx = 0;
  for (let x = x0; x <= x1; x++) {
    const w = Math.max(0, lum(x, y) - bg - 6);
    sw += w; swx += w * x;
  }
  return sw > 20 ? swx / sw : null;
}
function thrCenter(y, x0, x1) {
  let bg = 1e9, mx = 0;
  for (let x = x0; x <= x1; x++) { const l = lum(x, y); bg = Math.min(bg, l); mx = Math.max(mx, l); }
  const thr = bg + 0.45 * (mx - bg);
  let a = null, b = null;
  for (let x = x0; x <= x1; x++) if (lum(x, y) > thr) { if (a === null) a = x; b = x; }
  return a === null ? null : (a + b) / 2;
}
const centre = (y, x0, x1) => MODE === 'centroid' ? centroid(y, x0, x1) : thrCenter(y, x0, x1);

function track(y0, x0s, step, yTop, win) {
  const pts = [];
  let x = x0s * SC, s = step;
  for (let y = Math.round(y0 * SC); y >= Math.round(yTop * SC); y--) {
    x += s;
    const c = centre(y, Math.round(x - win), Math.round(x + win));
    if (c === null) continue;
    pts.push([c, y]);
    if (pts.length > 6) {
      const p = pts[pts.length - 6];
      s = 0.7 * s + 0.3 * ((c - p[0]) / (y - p[1]));
    }
    x = c;
  }
  return pts.map(([xx, yy]) => [xx / SC, yy / SC]);   // back to original units
}

const win = 6 * SC;
const YEL = track(266, 7, 2.7, 150, win);   // step in scaled px per row
const RED = track(352, 331, 0.62, 150, win);
console.log(`${file}  mode=${MODE}  scale=${SC}`);
console.log(`  yellow ${YEL.length} pts, right ${RED.length} pts`);

const fit = P => {
  const n = P.length; let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (const [x, y] of P) { sx += x; sy += y; sxy += x * y; sxx += y * y; }
  const a = (n * sxy - sx * sy) / (n * sxx - sy * sy), b = (sx - a * sy) / n;
  let ss = 0; for (const [x, y] of P) { const r = x - (a * y + b); ss += r * r; }
  return { a, b, rms: Math.sqrt(ss / n) };
};
const bands = (P, edges) => edges.map(([lo, hi]) => {
  const q = P.filter(p => p[1] >= lo && p[1] <= hi);
  return q.length >= 8 ? fit(q).a : null;
});
const E = [[150, 200], [200, 250], [250, 300], [300, 360]];
const by = bands(YEL, E), br = bands(RED, E);
const sp = a => { const v = a.filter(v => v !== null); return v.length ? Math.max(...v) - Math.min(...v) : NaN; };
const fy = fit(YEL), fr = fit(RED);
console.log(`  yellow  a=${fy.a.toFixed(4)} rms=${fy.rms.toFixed(2)}  bands ${by.map(v => v === null ? ' - ' : v.toFixed(3)).join(' ')}  spread=${sp(by).toFixed(3)}`);
console.log(`  right   a=${fr.a.toFixed(4)} rms=${fr.rms.toFixed(2)}  bands ${br.map(v => v === null ? ' - ' : v.toFixed(3)).join(' ')}  spread=${sp(br).toFixed(3)}`);
