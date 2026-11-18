// Map markings row by row: white and yellow runs.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const d = buf.subarray(off);
const px = (x, y) => { const o = (y * W + x) * 3; return [d[o], d[o + 1], d[o + 2]]; };

const isWhite = ([r, g, b]) => Math.min(r, g, b) > 135 && Math.max(r, g, b) - Math.min(r, g, b) < 45;
const isYellow = ([r, g, b]) => r > 140 && g > 110 && b < 110 && r - b > 60;

function runsAt(y, pred) {
  const out = [];
  let st = null;
  for (let x = 0; x < W; x++) {
    if (pred(px(x, y))) { if (st === null) st = x; }
    else if (st !== null) { out.push([st, x - 1]); st = null; }
  }
  if (st !== null) out.push([st, W - 1]);
  return out.filter(([a, b]) => b - a + 1 <= 40 && b - a + 1 >= 1);
}
console.log('row | white runs                    | yellow runs');
for (let y = 340; y >= 150; y -= 10) {
  const w = runsAt(y, isWhite).map(([a, b]) => `${a}-${b}`).join(' ');
  const yl = runsAt(y, isYellow).map(([a, b]) => `${a}-${b}`).join(' ');
  console.log(`${String(y).padStart(3)} | ${w.padEnd(30)} | ${yl}`);
}
