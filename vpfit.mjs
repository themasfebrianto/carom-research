// Iterative VP estimation from dash major-axis orientations.
import fs from 'node:fs';
const path = process.argv[2];
const THR = +(process.argv[3] || 140);
const [X0, X1, Y0, Y1] = process.argv.slice(4, 8).map(Number);

const buf = fs.readFileSync(path);
const head = buf.subarray(0, 64).toString('latin1');
const m = head.match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = m[0].length, W = +m[1], H = +m[2];
const d = buf.subarray(off);
const lum = (x, y) => { const o = (y * W + x) * 3; return 0.299 * d[o] + 0.587 * d[o + 1] + 0.114 * d[o + 2]; };

const mask = new Uint8Array(W * H);
for (let y = Y0; y <= Y1; y++) for (let x = X0; x <= X1; x++) if (lum(x, y) > THR) mask[y * W + x] = 1;

const lab = new Int32Array(W * H).fill(-1), st = new Int32Array(W * H), comps = [];
for (let y = Y0; y <= Y1; y++) for (let x = X0; x <= X1; x++) {
  const p0 = y * W + x;
  if (!mask[p0] || lab[p0] !== -1) continue;
  const id = comps.length; let sp = 0; st[sp++] = p0; lab[p0] = id;
  let n = 0, sx = 0, sy = 0, b0 = 1e9, b1 = -1, b2 = 1e9, b3 = -1;
  const px = [];
  while (sp) {
    const q = st[--sp], qx = q % W, qy = (q - qx) / W;
    n++; sx += qx; sy += qy; px.push(qx, qy);
    if (qx < b0) b0 = qx; if (qx > b1) b1 = qx; if (qy < b2) b2 = qy; if (qy > b3) b3 = qy;
    for (const r of [q - 1, q + 1, q - W, q + W]) {
      if (r < 0 || r >= W * H || lab[r] !== -1 || !mask[r]) continue;
      const rx = r % W, ry = (r - rx) / W;
      if (Math.abs(rx - qx) > 1 || ry < Y0 || ry > Y1) continue;
      lab[r] = id; st[sp++] = r;
    }
  }
  const cx = sx / n, cy = sy / n;
  let sxx = 0, syy = 0, sxy = 0;
  for (let k = 0; k < px.length; k += 2) { const dx = px[k] - cx, dy = px[k + 1] - cy; sxx += dx * dx; syy += dy * dy; sxy += dx * dy; }
  sxx /= n; syy /= n; sxy /= n;
  const tr = (sxx + syy) / 2, df = Math.sqrt(((sxx - syy) / 2) ** 2 + sxy * sxy);
  const l1 = tr + df, l2 = Math.max(tr - df, 1e-6);
  comps.push({ n, cx, cy, L: Math.sqrt(12 * l1), Wd: Math.sqrt(12 * l2), ang: 0.5 * Math.atan2(2 * sxy, sxx - syy), x0: b0, x1: b1, y0: b2, y1: b3 });
}
let cand = comps.filter(c => c.n >= 80 && c.L >= 20 && c.L <= 300 && c.Wd >= 2.5 && c.Wd <= 26 && c.L / c.Wd >= 3);
console.log(`comps ${comps.length} -> elongated ${cand.length}`);

// init VP guess
let V = { x: 715, y: 313 };
for (let it = 0; it < 8; it++) {
  // keep dashes whose axis points at V (within 10 deg)
  const keep = cand.filter(c => {
    const ex = Math.atan2(V.y - c.cy, V.x - c.cx);
    let da = ((c.ang - ex) * 180 / Math.PI) % 180; if (da > 90) da -= 180; if (da < -90) da += 180;
    return Math.abs(da) < 10 && c.cy > V.y + 60;
  });
  if (keep.length < 4) { console.log('too few'); break; }
  // weighted LS: minimise sum w_i * (n_i . (V - p_i))^2   with n_i = normal to dash axis
  let A11 = 0, A12 = 0, A22 = 0, b1 = 0, b2 = 0;
  for (const c of keep) {
    const nx = -Math.sin(c.ang), ny = Math.cos(c.ang);
    const w = c.n * Math.min(1, c.L / 40);
    A11 += w * nx * nx; A12 += w * nx * ny; A22 += w * ny * ny;
    const rhs = nx * c.cx + ny * c.cy;
    b1 += w * nx * rhs; b2 += w * ny * rhs;
  }
  const det = A11 * A22 - A12 * A12;
  V = { x: (b1 * A22 - b2 * A12) / det, y: (A11 * b2 - A12 * b1) / det };
  if (it === 7 || it === 0) console.log(`iter ${it}: kept ${keep.length}  VP=(${V.x.toFixed(1)}, ${V.y.toFixed(1)})`);
}
console.log(`\nFINAL VP = (${V.x.toFixed(2)}, ${V.y.toFixed(2)})`);
// residuals
const keep = cand.filter(c => {
  const ex = Math.atan2(V.y - c.cy, V.x - c.cx);
  let da = ((c.ang - ex) * 180 / Math.PI) % 180; if (da > 90) da -= 180; if (da < -90) da += 180;
  return Math.abs(da) < 10;
});
const res = keep.map(c => {
  const nx = -Math.sin(c.ang), ny = Math.cos(c.ang);
  return Math.abs(nx * (c.cx - V.x) + ny * (c.cy - V.y));
}).sort((a, b) => a - b);
console.log(`kept ${keep.length}, perpendicular residual median ${res[(res.length / 2) | 0].toFixed(2)} px, p90 ${res[(res.length * 0.9) | 0].toFixed(2)} px`);
console.log('\n dash list (kept):');
keep.sort((a, b) => b.cy - a.cy).forEach((c, k) => console.log(
  `${String(k).padStart(3)} (${c.cx.toFixed(1).padStart(6)}, ${c.cy.toFixed(1).padStart(6)})  L=${c.L.toFixed(1).padStart(5)} W=${c.Wd.toFixed(1).padStart(4)} ang=${(c.ang * 180 / Math.PI).toFixed(1).padStart(6)} n=${c.n}`));
fs.writeFileSync('frames/vp.json', JSON.stringify({ VP: V, dashes: keep.map(c => ({ cx: c.cx, cy: c.cy, L: c.L, Wd: c.Wd, ang: c.ang, n: c.n })) }, null, 1));
