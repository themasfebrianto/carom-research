// Worked example for the report: full calibration + dimension recovery trace.
const D2R = Math.PI / 180;
const mm = (A, B) => A.map(r => B[0].map((_, j) => r.reduce((s, v, k) => s + v * B[k][j], 0)));
const mv = (A, v) => A.map(r => r.reduce((s, a, k) => s + a * v[k], 0));
const T = A => A[0].map((_, j) => A.map(r => r[j]));
const dot = (a, b) => a.reduce((s, v, i) => s + v * b[i], 0);
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = a => Math.hypot(...a);
const unit = a => { const n = norm(a); return a.map(v => v / n); };
const sub = (a, b) => a.map((v, i) => v - b[i]);
const add = (a, b) => a.map((v, i) => v + b[i]);
const scale = (a, s) => a.map(v => v * s);
function inv3(M) {
  const [a, b, c] = M[0], [d, e, f] = M[1], [g, h, i] = M[2];
  const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g;
  const det = a * A + b * B + c * C;
  return [[A / det, -(b * i - c * h) / det, (b * f - c * e) / det],
          [B / det, (a * i - c * g) / det, -(a * f - c * d) / det],
          [C / det, -(a * h - b * g) / det, (a * e - b * d) / det]];
}
function makeCam({ f, W, H, h, yaw, pitch, roll = 0 }) {
  const cy = yaw * D2R, cp = pitch * D2R, cr = roll * D2R;
  const fw = [Math.cos(cp) * Math.cos(cy), Math.cos(cp) * Math.sin(cy), -Math.sin(cp)];
  let rw = [Math.sin(cy), -Math.cos(cy), 0];
  let dw = cross(fw, rw);
  if (cr !== 0) {
    const r2 = add(scale(rw, Math.cos(cr)), scale(dw, Math.sin(cr)));
    const d2 = add(scale(dw, Math.cos(cr)), scale(rw, -Math.sin(cr)));
    rw = r2; dw = d2;
  }
  const R = [rw, dw, fw];
  const K = [[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]];
  const C = [0, 0, h];
  return { f, W, H, h, R, K, C, t: scale(mv(R, C), -1) };
}
const project = (cam, X) => { const q = add(mv(cam.R, X), cam.t); return [cam.f * q[0] / q[2] + cam.W / 2, cam.f * q[1] / q[2] + cam.H / 2]; };
const ray = (cam, p) => unit(mv(T(cam.R), [(p[0] - cam.W / 2) / cam.f, (p[1] - cam.H / 2) / cam.f, 1]));
const homography = cam => mm(cam.K, [0, 1, 2].map(i => [[cam.R[0][0], cam.R[1][0], cam.R[2][0]][i], [cam.R[0][1], cam.R[1][1], cam.R[2][1]][i], cam.t[i]]));
const backProject = (Hm, p) => { const v = mv(inv3(Hm), [p[0], p[1], 1]); return [v[0] / v[2], v[1] / v[2]]; };
const heightFromRay = (cam, pTop, B) => {
  const d = ray(cam, pTop), v = sub(B, cam.C);
  const dd = d[0] * d[0] + d[1] * d[1];
  const lam = (v[0] * d[0] + v[1] * d[1]) / dd;
  return add(cam.C, scale(d, lam))[2] - B[2];
};

const r3 = (x) => +x.toFixed(3), r1 = (x) => +x.toFixed(1);

console.log('=== WORKED EXAMPLE ===');
const cam = makeCam({ f: 1920, W: 1920, H: 1080, h: 10.0, yaw: 8, pitch: 12, roll: 0 });
console.log('K =', JSON.stringify(cam.K));
console.log('R (world->cam) rows =', JSON.stringify(cam.R.map(r => r.map(r3))));
console.log('C =', cam.C, ' t =', cam.t.map(r3));

// vehicle: 4.50 x 1.80 x 1.50, centre 50 m ahead 3 m right, broadside
const car = { X0: 50, Y0: 3, L: 4.5, Wv: 1.8, Hv: 1.5, yaw: 90 };
const spec = [[1, 1], [1, -1], [-1, -1], [-1, 1]];
const names = ['front-left', 'front-right', 'rear-right', 'rear-left'];
const a = car.yaw * D2R, ca = Math.cos(a), sa = Math.sin(a);
const W = {};
spec.forEach(([sl, sw], i) => {
  const lx = sl * car.L / 2, ly = sw * car.Wv / 2;
  const gx = car.X0 + ca * lx - sa * ly, gy = car.Y0 + sa * lx + ca * ly;
  W[`b${i}`] = [gx, gy, 0]; W[`t${i}`] = [gx, gy, car.Hv];
});
console.log('\nground corners (X,Y):');
for (let i = 0; i < 4; i++) console.log(` b${i} ${names[i].padEnd(12)} world (${W['b' + i][0].toFixed(2)}, ${W['b' + i][1].toFixed(2)})  pixel ${project(cam, W['b' + i]).map(r1)}   roof pixel ${project(cam, W['t' + i]).map(r1)}`);

const pix = {}; for (const k in W) pix[k] = project(cam, W[k]);
const Hm = homography(cam);
console.log('\nH =', JSON.stringify(Hm.map(r => r.map(r3))));
const P = [0, 1, 2, 3].map(i => backProject(Hm, pix[`b${i}`]));
console.log('back-projected ground corners:');
P.forEach((p, i) => console.log(` P${i} = (${p[0].toFixed(3)}, ${p[1].toFixed(3)})  true (${W['b' + i][0].toFixed(2)}, ${W['b' + i][1].toFixed(2)})`));
console.log(' W = |P0P1| =', norm(sub(P[0], P[1])).toFixed(4), '  L = |P1P2| =', norm(sub(P[1], P[2])).toFixed(4));
console.log(' H = ray/vertical-line =', heightFromRay(cam, pix.t0, [P[0][0], P[0][1], 0]).toFixed(4));

// VPs
const vp = d => { const q = mv(cam.K, mv(cam.R, d)); return [q[0] / q[2], q[1] / q[2]]; };
console.log('\nvanishing points  vX =', vp([1, 0, 0]).map(r1), ' vY =', vp([0, 1, 0]).map(r1), ' vZ =', vp([0, 0, 1]).map(r1));
console.log('f from vX,vY =', Math.sqrt(-((vp([1, 0, 0])[0] - 960) * (vp([0, 1, 0])[0] - 960) + (vp([1, 0, 0])[1] - 540) * (vp([0, 1, 0])[1] - 540))).toFixed(2));

// sensitivity table for this very configuration
console.log('\nper-1px sensitivity in this configuration:');
const d0 = { L: norm(sub(P[0], P[1])), Wd: norm(sub(P[1], P[2])), H: heightFromRay(cam, pix.t0, [P[0][0], P[0][1], 0]) };
for (const axis of [0, 1]) {
  let dl = [], dw = [], dh = [];
  for (const key of ['b0', 'b1', 'b2', 'b3']) {
    const p2 = { ...pix, [key]: [...pix[key]] }; p2[key][axis] += 1;
    const Q = [0, 1, 2, 3].map(i => backProject(Hm, p2[`b${i}`]));
    dl.push(norm(sub(Q[0], Q[1])) - d0.L); dw.push(norm(sub(Q[1], Q[2])) - d0.Wd);
  }
  const p2 = { ...pix, t0: [...pix.t0] }; p2.t0[axis] += 1;
  dh.push(heightFromRay(cam, p2.t0, [P[0][0], P[0][1], 0]) - d0.H);
  console.log(`  axis ${axis === 0 ? 'u' : 'v'}: dL/dpix = ${Math.hypot(...dl).toFixed(4)}, dW/dpix = ${Math.hypot(...dw).toFixed(4)}, dH/dpix = ${Math.hypot(...dh).toFixed(4)} m`);
}
