// Are the yellow line, the dashed line and the NEAR portion of the right edge concurrent?
import fs from 'node:fs';
const t = JSON.parse(fs.readFileSync('f2/tracked.json'));
const YEL = t.YEL, RED = t.RED;

const fit = P => {
  const n = P.length; let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (const [x, y] of P) { sx += x; sy += y; sxy += x * y; sxx += y * y; }
  const a = (n * sxy - sx * sy) / (n * sxx - sy * sy), b = (sx - a * sy) / n;
  let ss = 0; for (const [x, y] of P) { const r = x - (a * y + b); ss += r * r; }
  return { a, b, rms: Math.sqrt(ss / n), n };
};

const yel = fit(YEL);
const redNear = fit(RED.filter(p => p[1] >= 275));
const redFar = fit(RED.filter(p => p[1] <= 250));
console.log('yellow      a=%s b=%s rms=%s n=%d', yel.a.toFixed(4), yel.b.toFixed(1), yel.rms.toFixed(2), yel.n);
console.log('right near  a=%s b=%s rms=%s n=%d  (y>=275)', redNear.a.toFixed(4), redNear.b.toFixed(1), redNear.rms.toFixed(2), redNear.n);
console.log('right far   a=%s b=%s rms=%s n=%d  (y<=250)', redFar.a.toFixed(4), redFar.b.toFixed(1), redFar.rms.toFixed(2), redFar.n);

const dashNear = [102.4, 320], dashFar = [359.0, 175];
const dashSlope = (dashFar[0] - dashNear[0]) / (dashFar[1] - dashNear[1]);
const dashB = dashNear[0] - dashSlope * dashNear[1];
console.log('dashed      a=%s b=%s  (2 clusters)', dashSlope.toFixed(4), dashB.toFixed(1));

const inter = (L1, L2) => {
  const y = (L2.b - L1.b) / (L1.a - L2.a);
  return { x: L1.a * y + L1.b, y };
};
const A = { a: yel.a, b: yel.b }, B = { a: redNear.a, b: redNear.b }, C = { a: dashSlope, b: dashB };
const vAB = inter(A, B), vAC = inter(A, C), vBC = inter(B, C);
console.log('\nVP yellow x right-near  = (%.0f, %.0f)', vAB.x, vAB.y);
console.log('VP yellow x dashed      = (%.0f, %.0f)', vAC.x, vAC.y);
console.log('VP right-near x dashed  = (%.0f, %.0f)', vBC.x, vBC.y);
const cx = (vAB.x + vAC.x + vBC.x) / 3, cy = (vAB.y + vAC.y + vBC.y) / 3;
console.log('rata-rata = (%.0f, %.0f)', cx, cy);
console.log('sebaran maks = %.0f px', Math.max(
  Math.hypot(vAB.x - cx, vAB.y - cy), Math.hypot(vAC.x - cx, vAC.y - cy), Math.hypot(vBC.x - cx, vBC.y - cy)));

// residual of each line at the mean VP (perpendicular distance)
const perp = (L, V) => Math.abs(L.a * V.y + L.b - V.x) / Math.hypot(L.a, 1);
console.log('\njarak tegak-lurus ke VP rata-rata:');
console.log('  yellow     %.2f px', perp(A, { x: cx, y: cy }));
console.log('  right near %.2f px', perp(B, { x: cx, y: cy }));
console.log('  dashed     %.2f px', perp(C, { x: cx, y: cy }));

// what if the far part of the right edge is used?
const vFar = inter(A, { a: redFar.a, b: redFar.b });
console.log('\nVP yellow x right-FAR   = (%.0f, %.0f)  <-- menyimpang %.0f px', vFar.x, vFar.y, Math.hypot(vFar.x - cx, vFar.y - cy));
