// Scan along known lane lines (through VP) and find dash intervals.
import fs from 'node:fs';
const path = process.argv[2];
const buf = fs.readFileSync(path);
const head = buf.subarray(0, 64).toString('latin1');
const mm = head.match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mm[0].length, W = +mm[1], H = +mm[2];
const d = buf.subarray(off);
const lum = (x, y) => { const o = ((y | 0) * W + (x | 0)) * 3; return 0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2]; };

const V = { x: 651.54, y: 309.96 };
const YREF = 719;
const lanes = [209.5, 369.2, 533.6];
const YTOP = 400, YBOT = 718;

console.log('lane  y0    y1     peak  length  cx      cy');
const found = [];
for (const xb of lanes) {
  // profile
  const prof = [];
  for (let y = YBOT; y >= YTOP; y--) {
    const k = (y - V.y) / (YREF - V.y);
    const x = V.x + (xb - V.x) * k;
    let best = 0, bx = x;
    for (let dx = -2; dx <= 2; dx++) {
      const l = lum(x + dx, y);
      if (l > best) { best = l; bx = x + dx; }
    }
    prof.push({ y, x: bx, l: best });
  }
  // adaptive threshold: road ~90-110, dashes >140
  let runs = [], inr = false, st = null;
  for (const p of prof) {
    const on = p.l > 135;
    if (on && !inr) { inr = true; st = p; }
    else if (!on && inr) {
      const seg = prof.filter(q => q.y <= st.y && q.y >= (prof.find(z => z === p)?.y ?? p.y));
      inr = false;
    }
    if (on && inr) continue;
  }
  // simpler: collect contiguous runs by index
  runs = [];
  let i0 = null;
  for (let i = 0; i < prof.length; i++) {
    if (prof[i].l > 135) { if (i0 === null) i0 = i; }
    else if (i0 !== null) { runs.push([i0, i - 1]); i0 = null; }
  }
  if (i0 !== null) runs.push([i0, prof.length - 1]);

  for (const [a, b] of runs) {
    if (b - a + 1 < 6) continue;                     // too short
    const seg = prof.slice(a, b + 1);
    const cy = seg.reduce((s, q) => s + q.y, 0) / seg.length;
    const cx = seg.reduce((s, q) => s + q.x, 0) / seg.length;
    const peak = Math.max(...seg.map(q => q.l));
    // require the run to be isolated (gap above and below)
    found.push({ xb, y0: seg[0].y, y1: seg[seg.length - 1].y, cx, cy, peak, len: b - a + 1 });
    console.log(`${xb.toFixed(0)}  ${seg[0].y}  ${seg[seg.length - 1].y}  ${peak.toFixed(0).padStart(4)}  ${String(b - a + 1).padStart(5)}  ${cx.toFixed(1).padStart(6)} ${cy.toFixed(1).padStart(7)}`);
  }
}
fs.writeFileSync('frames/lanedashes.json', JSON.stringify(found, null, 1));
