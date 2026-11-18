// Evaluate the analytic two-dash solution and see if the yellow line agrees.
import fs from 'node:fs';
const buf = fs.readFileSync('f2/median.ppm');
const mh = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+(\d+)\s/);
const off = mh[0].length, W = +mh[1], H = +mh[2];
const YEL = JSON.parse(fs.readFileSync('f2/tracked.json')).YEL.filter(p => p[1] <= 266);
const CX = W / 2, CY = H / 2;

const basis = p => {
  const cp = Math.cos(p.th), sp = Math.sin(p.th), cw = Math.cos(p.psi), sw = Math.sin(p.psi);
  return { fw: [cp * cw, cp * sw, -sp], rw: [sw, -cw, 0], dw: [-sp * cw, -sp * sw, -cp] };
};
const proj = (p, X, Y) => {
  const { fw, rw, dw } = basis(p); const v = [X, Y, -p.h];
  const xc = rw[0] * v[0] + rw[1] * v[1] + rw[2] * v[2];
  const yc = dw[0] * v[0] + dw[1] * v[1] + dw[2] * v[2];
  const zc = fw[0] * v[0] + fw[1] * v[1] + fw[2] * v[2];
  return { u: CX + p.f * xc / zc, v: CY + p.f * yc / zc };
};
const back = (p, u, v) => {
  const { fw, rw, dw } = basis(p);
  const xn = (u - CX) / p.f, yn = (v - CY) / p.f;
  const dx = rw[0] * xn + dw[0] * yn + fw[0], dy = rw[1] * xn + dw[1] * yn + fw[1], dz = rw[2] * xn + dw[2] * yn + fw[2];
  if (dz > -1e-6) return null;
  const s = -p.h / dz;
  return { X: dx * s, Y: dy * s, z: Math.hypot(dx * s, dy * s) };
};

for (const thd of [22, 25, 27.5, 30, 34]) {
  const th = thd * Math.PI / 180;
  const f = 120 / Math.tan(th);           // from VP row = 60
  const h = 22.27 * Math.sin(th) * Math.cos(th);
  const Xp = 10.24 - h * Math.tan(th);
  const psi = Math.atan((562.5 - CX) * Math.cos(th) / f);
  const p = { f, th, psi, h };
  // dash check
  const vfar = proj(p, Xp + 13 + 5, 0).v;
  const vnear = proj(p, Xp, 0).v;
  // yellow Y spread
  const ys = YEL.map(([u, v]) => { const q = back(p, u, v); return q ? q.Y : NaN; }).filter(Number.isFinite);
  const mean = ys.reduce((s, x) => s + x, 0) / ys.length;
  const sd = Math.sqrt(ys.reduce((s, x) => s + (x - mean) ** 2, 0) / ys.length);
  const pxErr = sd * p.f / 30;
  console.log(`th=${thd}  f=${f.toFixed(0)}  h=${h.toFixed(2)}  Xp=${Xp.toFixed(2)}  psi=${(psi * 180 / Math.PI).toFixed(1)}  |  yellow Y mean=${mean.toFixed(2)} sd=${sd.toFixed(3)} m (~${pxErr.toFixed(1)} px)`);
}
