// Verify: (a) per-dash residuals at the anchored calibration, (b) where the visible road bend actually is.
const CX = 640, CY = 360;
// anchored solution: w = 3.60 (Bina Marga) -> family member
const f = 1082, h = 8.91, th = 2.45 * Math.PI / 180;
const Xp = 24.8, w = 3.60, Y0 = 9.66;
const s = Math.sin(th), c = Math.cos(th);

function proj(X, Y) {
  const zc = X * c + h * s, yc = -X * s + h * c, xc = -Y;
  return { u: CX + f * xc / zc, v: CY + f * yc / zc };
}
function XofV(v) {
  let lo = 1, hi = 400;
  for (let k = 0; k < 100; k++) { const m = (lo + hi) / 2; if (proj(m, 0).v > v) lo = m; else hi = m; }
  return (lo + hi) / 2;
}

const obs = [
  { lane: 0, row: 0, yFar: 636.12, yNear: 698.92, u: 265.3 },
  { lane: 0, row: 1, yFar: 539.28, yNear: 568.67, u: 387.8 },
  { lane: 0, row: 2, yFar: 485.91, yNear: 503.44, u: 450.6 },
  { lane: 1, row: 0, yFar: 632.84, yNear: 696.99, u: 407.3 },
  { lane: 1, row: 1, yFar: 536.70, yNear: 567.03, u: 484.2 },
  { lane: 1, row: 2, yFar: 484.26, yNear: 501.60, u: 521.9 },
];
console.log('anchored calibration: f=%d px, h=%s m, w=%s m', f, h, w);
console.log('\nper-dash residuals (model - observed), px');
let ss = 0, n = 0;
for (const o of obs) {
  const Y = Y0 - o.lane * w;
  const Xn = Xp + o.row * 13, Xf = Xn + 5, Xm = Xn + 2.5;
  const a = proj(Xf, Y), b = proj(Xn, Y), m = proj(Xm, Y);
  const dvF = a.v - o.yFar, dvN = b.v - o.yNear, du = m.u - o.u;
  ss += dvF * dvF + dvN * dvN + du * du; n += 3;
  console.log(`  lane${o.lane} row${o.row}: dvFar=${dvF.toFixed(2).padStart(7)} dvNear=${dvN.toFixed(2).padStart(7)} du=${du.toFixed(2).padStart(6)}`);
}
console.log(`  RMS = ${Math.sqrt(ss / n).toFixed(2)} px over ${n} residuals`);

console.log('\nwhere things are in the image:');
for (const v of [719, 666, 600, 553, 520, 494, 460, 430, 400, 380, 370]) {
  console.log(`  v=${v} -> X=${XofV(v).toFixed(1)} m`);
}
