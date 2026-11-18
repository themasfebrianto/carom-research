// Numerical verification of the CCTV vehicle-dimension geometry used in the report.
// World: Z-up, origin at the vertical projection of the camera on the road.
// Camera: x_c right, y_c down, z_c forward.  p ~ K R (X - C)

const D2R = Math.PI / 180;

/* ---------- tiny linear algebra ---------- */
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

/* ---------- camera ---------- */
function makeCam({ f, W, H, h, yaw, pitch, roll = 0 }) {
  const cy = yaw * D2R, cp = pitch * D2R, cr = roll * D2R;
  const fw = [Math.cos(cp) * Math.cos(cy), Math.cos(cp) * Math.sin(cy), -Math.sin(cp)];
  // right-handed camera frame (x right, y down, z forward): right = up x forward
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
  const t = scale(mv(R, C), -1);
  return { f, W, H, h, R, K, C, t };
}
const project = (cam, X) => { const q = add(mv(cam.R, X), cam.t); return [cam.f * q[0] / q[2] + cam.W / 2, cam.f * q[1] / q[2] + cam.H / 2]; };
const camCentre = cam => cam.C;
// ray direction in world for pixel p
const ray = (cam, p) => unit(mv(T(cam.R), [(p[0] - cam.W / 2) / cam.f, (p[1] - cam.H / 2) / cam.f, 1]));

/* ---------- vehicle box: corners ordered around the footprint ---------- */
function boxCorners({ X0, Y0, L, Wv, Hv, yaw }) {
  const a = yaw * D2R, ca = Math.cos(a), sa = Math.sin(a);
  const spec = [[1, 1], [1, -1], [-1, -1], [-1, 1]];   // FL, FR, RR, RL in vehicle frame
  const out = {};
  spec.forEach(([sl, sw], i) => {
    const lx = sl * L / 2, ly = sw * Wv / 2;
    const gx = X0 + ca * lx - sa * ly, gy = Y0 + sa * lx + ca * ly;
    out[`b${i}`] = [gx, gy, 0];
    out[`t${i}`] = [gx, gy, Hv];
  });
  return out;
}

/* ---------- (1) focal length from two orthogonal VPs ---------- */
const focalFromVPs = (v1, v2, cx, cy) => Math.sqrt(-((v1[0] - cx) * (v2[0] - cx) + (v1[1] - cy) * (v2[1] - cy)));

/* ---------- (2) rotation from three orthogonal VPs ---------- */
function vpOf(cam, d) { const q = mv(cam.K, mv(cam.R, d)); return [q[0], q[1], q[2]]; } // homogeneous, NO divide
function rotFromVPs(cam, hs) {
  const Ki = inv3(cam.K);
  let c1 = unit(Ki.map(r => dot(r, hs[0])));
  let c2 = unit(Ki.map(r => dot(r, hs[1])));
  if (c1[2] < 0) c1 = scale(c1, -1);
  if (c2[2] < 0) c2 = scale(c2, -1);
  const c3 = unit(cross(c1, c2));
  return [0, 1, 2].map(i => [c1[i], c2[i], c3[i]]);
}

/* ---------- (3) ground homography ---------- */
function homography(cam) {
  const R = cam.R;
  const r1 = [R[0][0], R[1][0], R[2][0]], r2 = [R[0][1], R[1][1], R[2][1]];
  return mm(cam.K, [0, 1, 2].map(i => [r1[i], r2[i], cam.t[i]]));
}
function backProjectGround(Hm, p) {
  const v = mv(inv3(Hm), [p[0], p[1], 1]);
  return [v[0] / v[2], v[1] / v[2]];
}

/* ---------- (4) height: intersect viewing ray with vertical line through B ---------- */
function heightFromRay(cam, pTop, B) {
  const d = ray(cam, pTop);              // unit world direction
  const v = sub(B, cam.C);               // C -> B
  const dd = d[0] * d[0] + d[1] * d[1];  // horizontal part of d
  const lambda = (v[0] * d[0] + v[1] * d[1]) / dd;
  const P = add(cam.C, scale(d, lambda));
  return P[2] - B[2];                    // height above the base point
}

/* ---------- (5) Criminisi cross-ratio height (reference-based) ---------- */
function criminisi(cam, b, t, refB, refT, Zref) {
  // vertical vanishing point (world +Z seen by the camera)
  const hz = vpOf(cam, [0, 0, 1]);
  const vZ = [hz[0] / hz[2], hz[1] / hz[2], 1];
  // horizon line l = K^-T n, n = R e_z  (ground normal expressed in camera coords)
  const nC = mv(cam.R, [0, 0, 1]);
  const l = mv(T(inv3(cam.K)), nC);
  const h3 = x => [x[0], x[1], 1];
  const k = (bb, tt) => norm(cross(h3(bb), h3(tt))) / (Math.abs(dot(l, h3(bb))) * norm(cross(vZ, h3(tt))));
  return Zref * k(b, t) / k(refB, refT);
}

/* ---------- (6) full recovery from pixels ---------- */
function recover(cam, pix) {
  const Hm = homography(cam);
  const P = [0, 1, 2, 3].map(i => backProjectGround(Hm, pix[`b${i}`]));
  const Wm = norm(sub(P[0], P[1]));        // FL-FR
  const Lm = norm(sub(P[1], P[2]));        // FR-RR
  const Hm2 = heightFromRay(cam, pix.t0, [P[0][0], P[0][1], 0]);
  return { L: Lm, W: Wm, H: Hm2 };
}

const fx = v => typeof v === 'number' ? +v.toFixed(4) : v;
const show = o => JSON.stringify(o, (k, v) => fx(v));

/* ================= TEST 1: exact recovery ================= */
console.log('=== TEST 1  exact recovery (noise free) ===');
for (const cfg of [
  { name: 'CCTV wide   f=1200 h=10 pitch=15 yaw=15', f: 1200, W: 1920, H: 1080, h: 10, yaw: 15, pitch: 15, roll: 1.5 },
  { name: 'CCTV tele   f=3200 h=10 pitch=15 yaw=15', f: 3200, W: 1920, H: 1080, h: 10, yaw: 15, pitch: 15, roll: 1.5 },
  { name: 'Nadir drone f=3600 h=85  pitch=89.9    ', f: 3600, W: 5472, H: 3648, h: 85, yaw: 0, pitch: 89.9, roll: 0 },
]) {
  const cam = makeCam(cfg);
  const car = { X0: 42, Y0: 14, L: 4.5, Wv: 1.8, Hv: 1.5, yaw: 70 };
  const corners = boxCorners(car);
  const pix = {}; for (const k in corners) pix[k] = project(cam, corners[k]);

  const vX = vpOf(cam, [1, 0, 0]), vY = vpOf(cam, [0, 1, 0]), vZ = vpOf(cam, [0, 0, 1]);
  const nrm = h => [h[0] / h[2], h[1] / h[2]];
  const fEst = cfg.name.includes('Nadir') ? NaN : focalFromVPs(nrm(vX), nrm(vY), cam.W / 2, cam.H / 2);
  const Rest = rotFromVPs(cam, [vX, vY, vZ]);
  const rErr = Math.max(...[0, 1, 2].flatMap(i => [0, 1, 2].map(j => Math.abs(Rest[i][j] - cam.R[i][j]))));

  const d = recover(cam, pix);
  const dC = criminisi(cam, pix.b0, pix.t0, pix.b1, pix.t1, 1.0); // ref = a 1.0 m vertical
  console.log(`\n${cfg.name}`);
  console.log('  pixels b0..t0 :', show(pix.b0), show(pix.t0), ' inside FOV:', pix.b0[0] > 0 && pix.b0[0] < cam.W && pix.b0[1] > 0 && pix.b0[1] < cam.H);
  console.log('  f est         :', fEst.toFixed(1), ' R maxerr:', rErr.toExponential(2));
  console.log('  L,W,H  true   : 4.5, 1.8, 1.5');
  console.log('  L,W,H  recovered:', show(d), '  Criminisi H (via 1 m ref):', dC.toFixed(4));
}

/* ================= TEST 1b: Criminisi absolute scale with a distinct reference ================= */
console.log('\n\n=== TEST 1b  Criminisi height with a real 3.00 m reference pole elsewhere in the scene ===');
{
  const cam = makeCam({ f: 1920, W: 1920, H: 1080, h: 10, yaw: 15, pitch: 15, roll: 0 });
  const car = { X0: 42, Y0: 14, L: 4.5, Wv: 1.8, Hv: 1.5, yaw: 70 };
  const c = boxCorners(car);
  const pb = project(cam, c.b0), pt = project(cam, c.t0);
  const poleBase = [30, -4, 0], poleTop = [30, -4, 3.0];
  const hb = project(cam, poleBase), ht = project(cam, poleTop);
  console.log('  car H  via 3.00 m reference :', criminisi(cam, pb, pt, hb, ht, 3.0).toFixed(4), ' (true 1.5000)');
  console.log('  car H  via 1.50 m reference :', criminisi(cam, pb, pt, pb, pt, 1.5).toFixed(4), ' (true 1.5000)');
}

/* ================= TEST 3b: nadir height conditioning, numeric ================= */
console.log('\n\n=== TEST 3b  nadir: sigma_H per 1 px, numeric (h=85 m, f=3600) ===');
for (const s of [2, 5, 10, 20, 45]) {
  const cam = makeCam({ f: 3600, W: 5472, H: 3648, h: 85, yaw: 0, pitch: 89.5 });
  const car = { X0: s, Y0: 0, L: 4.5, Wv: 1.8, Hv: 1.5, yaw: 0 };
  const c = boxCorners(car);
  const pix = {}; for (const k in c) pix[k] = project(cam, c[k]);
  const d0 = recover(cam, pix);
  // perturb in both image axes, take RSS (height is sensitive along the radial direction)
  let acc = 0;
  for (const ax of [0, 1]) {
    const p2 = { ...pix, t0: [...pix.t0] }; p2.t0[ax] += 1;
    const d1 = recover(cam, p2);
    acc += Math.pow(d1.H - d0.H, 2);
  }
  console.log(`  s=${String(s).padStart(2)} m  sigma_H= ${Math.sqrt(acc).toFixed(3)} m/px   analytic ${(85 * 85 / (3600 * s)).toFixed(3)}   H0=${d0.H.toFixed(3)}`);
}

/* ================= TEST 5: pitch mis-calibration ================= */
console.log('\n\n=== TEST 5  pitch error: bias in L, W, H (true pitch 12 deg) ===');
console.log(' sigma_pix = 0, so any error here is pure model bias');
for (const epsDeg of [0.05, 0.1, 0.25, 0.5]) {
  const camTrue = makeCam({ f: 1920, W: 1920, H: 1080, h: 10, yaw: 0, pitch: 12, roll: 0 });
  const car = { X0: 49, Y0: 0, L: 4.5, Wv: 1.8, Hv: 1.5, yaw: 90 }; // broadside at 50 m
  const c = boxCorners(car);
  const pix = {}; for (const k in c) pix[k] = project(camTrue, c[k]);
  const camBad = makeCam({ f: 1920, W: 1920, H: 1080, h: 10, yaw: 0, pitch: 12 + epsDeg, roll: 0 });
  const d = recover(camBad, pix);
  console.log(`  pitch err ${epsDeg.toFixed(2)} deg -> L ${(d.L - 4.5).toFixed(3)} m, W ${(d.W - 1.8).toFixed(3)} m, H ${(d.H - 1.5).toFixed(3)} m`);
}

console.log('\n\n=== TEST 2  sigma in metres for 1 px centroid noise on each endpoint ===');
console.log('camera h=10m, roll=0, pitch=12deg; vehicle heading set to the extreme cases');
const A = { f: 1920, W: 1920, H: 1080, h: 10, pitch: 12, roll: 0 };
function sigmaFor(f, dist, headingMode, pixNoise = 1.0) {
  // aim the camera at (dist,0): yaw so that optical axis passes through the target
  const yaw = 0;
  const cam = makeCam({ ...A, f, yaw, pitch: 12 });
  // put the vehicle on the optical-axis ground trace at slant distance `dist`
  const zc = dist;                                  // along the axis
  const X0 = zc * Math.cos(12 * D2R), Y0 = 0;
  const heading = headingMode === 'along' ? 0 : 90; // along the ray / broadside
  const car = { X0, Y0, L: 4.5, Wv: 1.8, Hv: 1.5, yaw: heading };
  const corners = boxCorners(car);
  const pix = {}; for (const k in corners) pix[k] = project(cam, corners[k]);
  const d0 = recover(cam, pix);

  const vars = { L: [], W: [], H: [] };
  for (const key of ['b0', 'b1', 'b2', 'b3', 't0']) {
    for (const ax of [0, 1]) {
      const p2 = { ...pix, [key]: [...pix[key]] }; p2[key][ax] += 0.5;
      const d1 = recover(cam, p2);
      for (const k of ['L', 'W', 'H']) vars[k].push((d1[k] - d0[k]) / 0.5 * pixNoise);
    }
  }
  const s = {}; for (const k of ['L', 'W', 'H']) s[k] = Math.hypot(...vars[k]);
  return { s, d0, zc };
}

console.log('\nf=1920 px  (1080p, HFOV ~53 deg)');
console.log(' dist | heading |  sigma_L   sigma_W   sigma_H |  analytic L   analytic W/H');
for (const dist of [20, 30, 40, 50, 70, 100]) {
  for (const mode of ['across', 'along']) {
    const { s } = sigmaFor(1920, dist, mode);
    const aLat = Math.SQRT2 * dist / 1920, aDep = Math.SQRT2 * dist * dist / (1920 * 10);
    console.log(` ${String(dist).padStart(4)} | ${mode.padEnd(6)} | ${s.L.toFixed(3).padStart(7)}  ${s.W.toFixed(3).padStart(7)}  ${s.H.toFixed(3).padStart(7)} |     ${aDep.toFixed(3)}        ${aLat.toFixed(3)}`);
  }
}

console.log('\nf=3200 px  (tele, HFOV ~33 deg)');
console.log(' dist | heading |  sigma_L   sigma_W   sigma_H |  analytic L   analytic W/H');
for (const dist of [20, 30, 40, 50, 70, 100]) {
  for (const mode of ['across', 'along']) {
    const { s } = sigmaFor(3200, dist, mode);
    const aLat = Math.SQRT2 * dist / 3200, aDep = Math.SQRT2 * dist * dist / (3200 * 10);
    console.log(` ${String(dist).padStart(4)} | ${mode.padEnd(6)} | ${s.L.toFixed(3).padStart(7)}  ${s.W.toFixed(3).padStart(7)}  ${s.H.toFixed(3).padStart(7)} |     ${aDep.toFixed(3)}        ${aLat.toFixed(3)}`);
  }
}

/* ================= TEST 3: nadir height conditioning ================= */
console.log('\n\n=== TEST 3  nadir (drone) height sensitivity: sigma_H per 1 px vs offset s from nadir ===');
console.log('h=85 m, f=3600 px.  analytic: sigma_H = h^2 * dpix / (f * s)');
for (const s of [3, 5, 10, 20, 30, 45]) {
  console.log(`  s=${String(s).padStart(2)} m  ->  sigma_H = ${(85 * 85 / (3600 * s)).toFixed(3)} m/px`);
}

/* ================= TEST 4: scale error propagation ================= */
console.log('\n\n=== TEST 4  effect of scale-reference error on dimensions ===');
for (const [refName, relErr] of [['lane width 3.50 ± 0.15 m (4.3%)', 0.043], ['lane width 3.50 ± 0.05 m (1.4%)', 0.014], ['RTK survey of 4 pts (0.5%)', 0.005]]) {
  console.log(`  ${refName.padEnd(34)} -> sigma_L on 4.5 m = ${(4.5 * relErr * 100).toFixed(1)} cm,  sigma_H on 1.5 m = ${(1.5 * relErr * 100).toFixed(1)} cm`);
}
