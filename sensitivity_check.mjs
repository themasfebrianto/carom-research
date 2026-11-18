// Corrected per-axis sensitivity for the worked example.
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
  return { f, W, H, h, R, K, C: [0, 0, h], t: scale(mv(R, [0, 0, h]), -1) };
}
const project = (c, X) => { const q = add(mv(c.R, X), c.t); return [c.f * q[0] / q[2] + c.W / 2, c.f * q[1] / q[2] + c.H / 2]; };
const cam = makeCam({ f: 1920, W: 1920, H: 1080, h: 10, yaw: 8, pitch: 12, roll: 0 });
const homography = c => mm(c.K, [0, 1, 2].map(i => [[c.R[0][0], c.R[1][0], c.R[2][0]][i], [c.R[0][1], c.R[1][1], c.R[2][1]][i], c.t[i]]));
const Hm = homography(cam);
const back = p => { const v = mv(inv3(Hm), [p[0], p[1], 1]); return [v[0] / v[2], v[1] / v[2]]; };

const car = { X0: 50, Y0: 3, L: 4.5, Wv: 1.8, Hv: 1.5, yaw: 90 };
const a = car.yaw * D2R, ca = Math.cos(a), sa = Math.sin(a);
const spec = [[1, 1], [1, -1], [-1, -1], [-1, 1]];
const pix = {}, Wd = {};
spec.forEach(([sl, sw], i) => {
  const lx = sl * car.L / 2, ly = sw * car.Wv / 2;
  const p = [car.X0 + ca * lx - sa * ly, car.Y0 + sa * lx + ca * ly, 0];
  Wd[`b${i}`] = p; pix[`b${i}`] = project(cam, p);
});
const P0 = [0, 1, 2, 3].map(i => back(pix[`b${i}`]));
const L0 = norm(sub(P0[1], P0[2]));   // edges P1->P2
const W0 = norm(sub(P0[0], P0[1]));   // edges P0->P1
console.log('baseline L,W =', L0.toFixed(4), W0.toFixed(4));
console.log('edge spans px: W edge', Math.hypot(pix.b0[0] - pix.b1[0], pix.b0[1] - pix.b1[1]).toFixed(1),
            ' L edge', Math.hypot(pix.b1[0] - pix.b2[0], pix.b1[1] - pix.b2[1]).toFixed(1));

for (const axis of [0, 1]) {
  const dL = [], dW = [];
  for (const key of ['b0', 'b1', 'b2', 'b3']) {
    const p2 = { ...pix, [key]: [...pix[key]] }; p2[key][axis] += 0.25;
    const Q = [0, 1, 2, 3].map(i => back(p2[`b${i}`]));
    dL.push((norm(sub(Q[1], Q[2])) - L0) / 0.25);
    dW.push((norm(sub(Q[0], Q[1])) - W0) / 0.25);
  }
  console.log(`axis ${axis ? 'v' : 'u'}: |dL/dp| = ${Math.hypot(...dL).toFixed(4)}  |dW/dp| = ${Math.hypot(...dW).toFixed(4)} m/px`);
}
