// Test the suspected (f, theta, h, w, Y0) scale degeneracy.
const CX = 640, CY = 360;

function proj(p, X, Y) {
  const { f, th, h, psi = 0 } = p;
  const cp = Math.cos(th), sp = Math.sin(th), cw = Math.cos(psi), sw = Math.sin(psi);
  const fw = [cp * cw, cp * sw, -sp];
  const rw = [sw, -cw, 0];
  const dw = [fw[1] * rw[2] - fw[2] * rw[1], fw[2] * rw[0] - fw[0] * rw[2], fw[0] * rw[1] - fw[1] * rw[0]];
  const dx = X, dy = Y, dz = -h;
  const xc = rw[0] * dx + rw[1] * dy + rw[2] * dz;
  const yc = dw[0] * dx + dw[1] * dy + dw[2] * dz;
  const zc = fw[0] * dx + fw[1] * dy + fw[2] * dz;
  return { u: CX + f * xc / zc, v: CY + f * yc / zc };
}

// two members of the fitted family (from the Y0 sweep)
const P = {
  A: { f: 1205, th: 2.20 * Math.PI / 180, h: 8.001, w: 3.238, Y0: 8.69, Xp: 24.76 },
  B: { f: 1312, th: 2.04 * Math.PI / 180, h: 7.367, w: 2.978, Y0: 8.00, Xp: 24.85 },
  C: { f: 1099, th: 2.40 * Math.PI / 180, h: 8.745, w: 3.545, Y0: 9.50, Xp: 24.65 },
  D: { f: 1758, th: 1.54 * Math.PI / 180, h: 5.528, w: 2.228, Y0: 6.00, Xp: 25.06 },
};

const feats = [];
for (let lane = 0; lane < 2; lane++) for (let row = 0; row < 3; row++) {
  feats.push({ lane, row, kind: 'near' }, { lane, row, kind: 'far' }, { lane, row, kind: 'mid' });
}
console.log('feature predictions for each family member:');
console.log('  lane row kind      A(u,v)            B(u,v)            C(u,v)            D(u,v)');
let maxdiff = 0;
for (const ft of feats) {
  const out = {};
  for (const [k, p] of Object.entries(P)) {
    const Y = p.Y0 - ft.lane * p.w;
    const Xn = p.Xp + ft.row * 13;
    const X = ft.kind === 'near' ? Xn : ft.kind === 'far' ? Xn + 5 : Xn + 2.5;
    out[k] = proj(p, X, Y);
  }
  const du = Math.max(...Object.values(out).map(q => q.u)) - Math.min(...Object.values(out).map(q => q.u));
  const dv = Math.max(...Object.values(out).map(q => q.v)) - Math.min(...Object.values(out).map(q => q.v));
  maxdiff = Math.max(maxdiff, du, dv);
  const s = Object.entries(out).map(([k, q]) => `${k}(${q.u.toFixed(1)},${q.v.toFixed(1)})`).join(' ');
  console.log(`  ${ft.lane}    ${ft.row}   ${ft.kind.padEnd(5)}  ${s}`);
}
console.log(`\nmax spread across family members: ${maxdiff.toFixed(2)} px`);
console.log('(if small, the four parameter sets are indistinguishable in the image)');

// invariant combinations
console.log('\n--- invariant combinations ---');
for (const [k, p] of Object.entries(P)) {
  console.log(`${k}: f*th=${(p.f * p.th * 180 / Math.PI).toFixed(1)}  f*h=${(p.f * p.h).toFixed(0)}  f*w=${(p.f * p.w).toFixed(0)}  w/h=${(p.w / p.h).toFixed(4)}  horizon=${(CY - p.f * Math.tan(p.th)).toFixed(1)}`);
}
