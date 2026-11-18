// Annotate PPM (robust header parse).
import fs from 'node:fs';
const [inp, outp, specPath] = process.argv.slice(2);
const buf = fs.readFileSync(inp);
const head = buf.subarray(0, 64).toString('latin1');
const m = head.match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
if (!m) throw new Error('bad PPM header: ' + JSON.stringify(head));
const off = m[0].length, W = +m[1], H = +m[2];
console.log(`PPM ${W}x${H} off=${off} need=${off + W * H * 3} have=${buf.length}`);
const d = Buffer.from(buf.subarray(off, off + W * H * 3));

const set = (x, y, c, t = 1) => {
  for (let dy = -t; dy <= t; dy++) for (let dx = -t; dx <= t; dx++) {
    const xx = Math.round(x) + dx, yy = Math.round(y) + dy;
    if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue;
    const o = (yy * W + xx) * 3; d[o] = c[0]; d[o + 1] = c[1]; d[o + 2] = c[2];
  }
};
const line = (x0, y0, x1, y1, c, t = 1) => {
  const n = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0)) | 0 || 1;
  for (let k = 0; k <= n; k++) set(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n, c, t);
};
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
for (const l of spec.lines || []) line(l.a * 0 + l.b, 0, l.a * (H - 1) + l.b, H - 1, l.c || [255, 0, 0], l.t ?? 1);
for (const l of spec.segs || []) line(l.x0, l.y0, l.x1, l.y1, l.c || [255, 0, 0], l.t ?? 1);
for (const p of spec.points || []) set(p.x, p.y, p.c || [0, 255, 0], p.t ?? 4);
for (const b of spec.boxes || []) {
  line(b.x0, b.y0, b.x1, b.y0, b.c); line(b.x1, b.y0, b.x1, b.y1, b.c);
  line(b.x1, b.y1, b.x0, b.y1, b.c); line(b.x0, b.y1, b.x0, b.y0, b.c);
}
fs.writeFileSync(outp, Buffer.concat([Buffer.from(`P6\n${W} ${H}\n255\n`), d]));
console.log('wrote', outp);
