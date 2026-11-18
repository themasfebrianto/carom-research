// Dash detector using second moments (elongation), robust for diagonal dashes.
import fs from 'node:fs';
const path = process.argv[2];
const THR = +(process.argv[3] || 150);
const [X0, X1, Y0, Y1] = process.argv.slice(4, 8).map(Number);

const buf = fs.readFileSync(path);
let i = 0; const f = [];
while (f.length < 4) {
  while (/\s/.test(String.fromCharCode(buf[i]))) i++;
  if (buf[i] === 35) { while (buf[i] !== 10) i++; continue; }
  let s = '';
  while (!/\s/.test(String.fromCharCode(buf[i]))) s += String.fromCharCode(buf[i++]);
  f.push(s);
}
while (/\s/.test(String.fromCharCode(buf[i]))) i++;
const W = +f[1], H = +f[2], d = buf.subarray(i);
const lum = (x, y) => { const o = (y * W + x) * 3; return 0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2]; };
const m = new Uint8Array(W * H);
for (let y = Y0; y <= Y1; y++) for (let x = X0; x <= X1; x++) if (lum(x, y) > THR) m[y * W + x] = 1;

const lab = new Int32Array(W * H).fill(-1), st = new Int32Array(W * H), out = [];
for (let y = Y0; y <= Y1; y++) for (let x = X0; x <= X1; x++) {
  const p0 = y * W + x;
  if (!m[p0] || lab[p0] !== -1) continue;
  const id = out.length; let sp = 0; st[sp++] = p0; lab[p0] = id;
  let n = 0, sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0, b0 = 1e9, b1 = -1, b2 = 1e9, b3 = -1;
  const px = [];
  while (sp) {
    const q = st[--sp], qx = q % W, qy = (q - qx) / W;
    n++; sx += qx; sy += qy; px.push(qx, qy);
    if (qx < b0) b0 = qx; if (qx > b1) b1 = qx; if (qy < b2) b2 = qy; if (qy > b3) b3 = qy;
    for (const r of [q - 1, q + 1, q - W, q + W]) {
      if (r < 0 || r >= W * H || lab[r] !== -1 || !m[r]) continue;
      const rx = r % W, ry = (r - rx) / W;
      if (Math.abs(rx - qx) > 1 || ry < Y0 || ry > Y1) continue;
      lab[r] = id; st[sp++] = r;
    }
  }
  const cx = sx / n, cy = sy / n;
  for (let k = 0; k < px.length; k += 2) { const dx = px[k] - cx, dy = px[k + 1] - cy; sxx += dx * dx; syy += dy * dy; sxy += dx * dy; }
  sxx /= n; syy /= n; sxy /= n;
  const tr = (sxx + syy) / 2, df = Math.sqrt(((sxx - syy) / 2) ** 2 + sxy * sxy);
  const l1 = tr + df, l2 = Math.max(tr - df, 1e-6);
  out.push({ n, cx, cy, L: Math.sqrt(12 * l1), Wd: Math.sqrt(12 * l2), ang: 0.5 * Math.atan2(2 * sxy, sxx - syy) * 180 / Math.PI, x0: b0, x1: b1, y0: b2, y1: b3 });
}
const dash = out.filter(c => c.n >= 100 && c.L >= 22 && c.L <= 260 && c.Wd >= 3 && c.Wd <= 24 && c.L / c.Wd >= 2.5)
  .sort((a, b) => b.cy - a.cy);
console.log(`comps ${out.length}  dashes ${dash.length}`);
console.log('  i    cx       cy      L      W    elong   ang     area');
dash.forEach((c, k) => console.log(
  `${String(k).padStart(3)} ${c.cx.toFixed(1).padStart(7)} ${c.cy.toFixed(1).padStart(7)} ${c.L.toFixed(1).padStart(6)} ${c.Wd.toFixed(1).padStart(5)} ${(c.L / c.Wd).toFixed(1).padStart(6)} ${c.ang.toFixed(1).padStart(7)} ${String(c.n).padStart(6)}`
));
fs.writeFileSync('frames/dashes.json', JSON.stringify(dash.map(c => ({ cx: c.cx, cy: c.cy, L: c.L, Wd: c.Wd, ang: c.ang, n: c.n })), null, 1));
