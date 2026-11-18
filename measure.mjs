// Measure the container truck with the fitted camera model.
const CY = 360, CX = 640, f = 1158, h = 8.11;
const th = 2.12 * Math.PI / 180;
const s = Math.sin(th), c = Math.cos(th);

// ground distance X for image row v
function XofV(v) {
  let lo = 1, hi = 400;
  for (let k = 0; k < 100; k++) {
    const m = (lo + hi) / 2, z = m * c + h * s;
    const vv = CY + f * (-m * s + h * c) / z;
    if (vv > v) lo = m; else hi = m;
  }
  return (lo + hi) / 2;
}
function zOf(X) { return X * c + h * s; }

// height Z of a pixel on the vertical plane at distance X
function ZofPixel(v, X) {
  let lo = -2, hi = 8;
  for (let k = 0; k < 100; k++) {
    const Z = (lo + hi) / 2;
    const zc = X * c + (h - Z) * s;
    const yc = -X * s + (h - Z) * c;
    const vv = CY + f * yc / zc;
    if (vv > v) lo = Z; else hi = Z;   // larger Z -> row goes up (smaller v)
  }
  return (lo + hi) / 2;
}

const vGround = 496;                 // rear wheel contact row
const Xr = XofV(vGround), zr = zOf(Xr);
console.log(`truck rear plane: X=${Xr.toFixed(1)} m  z=${zr.toFixed(1)} m`);

const uL = 336, uR = 392;            // rear-face left / right edges
const W = (uR - uL) * zr / f;
console.log(`W = ${(uR - uL)} px * ${zr.toFixed(1)} / ${f} = ${W.toFixed(2)} m   (ISO 20ft = 2.44 m)`);

const vTop = 409, vBot = 476;
const zTop = ZofPixel(vTop, Xr), zBot = ZofPixel(vBot, Xr);
console.log(`rear face: bottom Z=${zBot.toFixed(2)} m, top Z=${zTop.toFixed(2)} m, H_container=${(zTop - zBot).toFixed(2)} m  (ISO 20ft = 2.59 m)`);

// ---- theoretical uncertainty for this camera
console.log('\n--- theoretical 1-sigma for this camera (f=%d, h=%.1f) ---', f, h);
for (const z of [30, 40, 50, 60]) {
  const sLat = Math.SQRT2 * z / f, sDep = Math.SQRT2 * z * z / (f * h);
  console.log(`  z=${z} m : lateral ${(sLat * 1000).toFixed(1)} mm/px, depth ${(sDep * 1000).toFixed(1)} mm/px, anisotropy ${(z / h).toFixed(1)}x`);
}
// lane width check at the three rows
console.log('\n--- implied lane width from the fit ---');
for (const [v, du] of [[666.25, 141.5], [553.0, 96.3], [494.5, 71.3]]) {
  const X = XofV(v), z = zOf(X);
  console.log(`  v=${v}: X=${X.toFixed(1)} m, du=${du} px -> w=${(du * z / f).toFixed(2)} m`);
}
