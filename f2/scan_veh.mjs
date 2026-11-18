// Find frames containing vehicles: compare each sampled frame to the median.
import fs from 'node:fs';
import { execSync } from 'node:child_process';

const W = 240, H = 180;
// build median at this scale
execSync('ffmpeg -v error -i f2/median.png -vf scale=240:180,format=gray -y f2/med.pgm');
const readPGM = p => {
  const b = fs.readFileSync(p);
  let i = 0; const tok = [];
  while (tok.length < 4) {
    while (i < b.length && /\s/.test(String.fromCharCode(b[i]))) i++;
    if (b[i] === 35) { while (b[i] !== 10) i++; continue; }
    let s = '';
    while (i < b.length && !/\s/.test(String.fromCharCode(b[i]))) s += String.fromCharCode(b[i++]);
    tok.push(s);
  }
  while (/\s/.test(String.fromCharCode(b[i]))) i++;
  return { w: +tok[1], h: +tok[2], d: b.subarray(i) };
};

const med = readPGM('f2/med.pgm');
// road ROI in the 240x180 image: roughly x 20..239, y 90..179
const X0 = 20, X1 = 239, Y0 = 90, Y1 = 179;

const files = fs.readdirSync('f2').filter(f => /^g_\d+\.pgm$/.test(f)).sort();
console.log('frames:', files.length);
const hits = [];
for (const f of files) {
  const im = readPGM('f2/' + f);
  let n = 0;
  for (let y = Y0; y <= Y1; y++) for (let x = X0; x <= X1; x++) {
    const i = y * W + x;
    if (Math.abs(im.d[i] - med.d[i]) > 35) n++;
  }
  if (n > 60) hits.push({ f, n });
}
hits.sort((a, b) => b.n - a.n);
console.log('kandidat (selisih > 35 luma, > 60 piksel):');
hits.slice(0, 25).forEach(h => {
  const idx = +h.f.match(/(\d+)/)[1];
  const t = (idx - 1) * 2;
  console.log(`  ${h.f}  t=${t}s  n=${h.n}`);
});
