# SVLD: AnyCalib, Fusion f, dan Lane Fit

**Tanggal:** 20 November 2026; update fusi `f` 26 November 2026  
**Tujuan:** menguji apakah f bisa diperbaiki dengan AnyCalib, kombinasi VP + model, atau geometri lajur.

---

## 1. Ringkasan

1. **AnyCalib tidak memperbaiki f di SVLD**: **6/100** lulus Δf <5%, median **18,2%**; GeoCalib tetap lebih baik (**20/100**, median 14,9%).
2. **Kombinasi VP + AnyCalib**: **34/100** lulus pitch/yaw <2°; lebih buruk dari VP + GeoCalib (**47/100**) dan jauh di bawah VP + f GT (**95/100**).
3. **Fusion buta tidak membantu**: rata-rata GeoCalib+AnyCalib **17/100**, MAE 19,53% vs GeoCalib 19,35% (20/100). Galat kedua model berkorelasi `r = 0,93` dan sama-sama 17–19% terlalu rendah; lihat `fusion-gt-2026-11-26.md`. **Setelah skala per kamera di-anchor dengan satu frame ber-`f` diketahui**, fusi 50/50 memberi MAE **4,28%** dan **71/95** lulus; 3/5 kamera hampir sempurna, `0cam` dan `session6_right` tetap gagal karena drift antar-frame. Ini mengukur **stabilitas relatif**, bukan pencarian `f` absolut: untuk kamera statis, `f` anchor tetap jawabannya.
4. **f dari pitch GeoCalib + VP** juga gagal: median error f **21,6%**, 0/100 lulus.
5. **Lane fit (f/h dari 3 garis lajur + lebar lajur)**:
   - **Sintetis berhasil**: semua start konvergen ke f/h yang benar (RMS 0 px).
   - **SVLD nyata gagal**: **0/45** citra lulus (RMS ≤5 px); f median error **60–64%**, RMS 11–139 px. Bottleneck: ekstraksi/assignment garis lajur, bukan matematikanya.
6. **Vertical VP otomatis juga gagal**: `0cam` hanya **2/20** OK (13 tanpa VP, 5 F_BAD); `1cam` 18/20 OK tetapi Δf median **9,0%**, hanya **4/18** lulus. Sudut VP vertikal vs gravitasi GeoCalib **35–43°**, tanda garis yang terdeteksi bukan vertikal sejati.
7. **GlobustVP (CVPR 2025) tidak menyelamatkan VP vertikal.** `0cam`: 2/3 frame menemukan 3 VP, tetapi VP vertikal punya **0 inlier** (error 2,85° hanya hasil cross-product). `1cam`: 3/3 frame, error vertikal **31–36°**. `session0_right`: **NO_3VP**. Solver SCS/Clarabel lambat/`optimal_inaccurate`; tidak turnkey.
8. **Kesimpulan:** tidak ada model belajar atau VP otomatis yang bisa dijadikan sumber f tunggal. f harus dari **kamera diketahui, dash fit dengan anchor, dua VP ortogonal yang tervalidasi, atau anotasi garis manual**. VP tetap sumber yaw/pitch terbaik bila f benar.

---

## 2. AnyCalib

- Model: `anycalib_pinhole`, `cam_id=simple_pinhole`.
- 100 citra yang sama (10 test + 10 trainval per scene), resolusi asli.
- Dibandingkan dengan GeoCalib dan GT XML.

| Metode | n | Δf median | Δf p90 | Lulus Δf<5% |
|---|---:|---:|---:|---:|
| GeoCalib | 100 | **14,9%** | 47,3% | **20/100** |
| AnyCalib | 100 | 18,2% | 46,9% | **6/100** |
| Rata-rata Geo+Any | 100 | 17,0% | — | 17/100 |
| 75% Geo + 25% Any | 100 | 16,0% | — | 20/100 |

Per scene (AnyCalib vs GeoCalib, median Δf):

| Scene | AnyCalib test/trainval | GeoCalib test/trainval |
|---|---:|---:|
| 0cam | 45,7% / 48,3% | 47,2% / 50,7% |
| 1cam | **8,1% / 6,8%** | 10,6% / 13,4% |
| session0_centre | 7,3% / 9,7% | **1,5% / 0,7%** |
| session0_right | 20,9% / 19,5% | 15,2% / 15,3% |
| session6_right | 18,4% / 19,0% | 24,9% / 19,1% |

**Bacaan:** AnyCalib hanya lebih baik di `1cam` dan sebagian `session6_right`; tidak ada scene yang menjadi <5% secara konsisten. Fusion tidak mengalahkan GeoCalib.

### 2.1 Cek fusi terhadap GT (26 November 2026)

Evaluasi khusus fusi `f` pada 100 citra yang sama, dengan GT XML dan tanpa memakai GT sebagai input. Detail lengkap: `fusion-gt-2026-11-26.md`.

| Metode | MAE | Median `|Δf|` | Lulus <5% | Lulus <10% |
|---|---:|---:|---:|---:|
| GeoCalib | **19,35%** | **14,91%** | **20/100** | 25/100 |
| AnyCalib | 20,18% | 18,17% | 6/100 | **34/100** |
| 50/50 Geo+Any | 19,53% | 16,97% | 17/100 | 31/100 |
| 50/50 + anchor 1 frame/kamera (relatif) | **4,28%** | — | **71,3/95** | — |

- Rasio estimasi/GT: GeoCalib `0,807`, AnyCalib `0,830`; korelasi galat **0,929**; jarak antar-model hanya **7,05%**. Kedua model bias ke arah yang sama, jadi 50/50 tidak menghapus apa pun — berbeda dari Cawang yang biasnya berlawanan.
- Fusi 50/50 lebih buruk daripada model terbaik di **setiap** scene. Oracle pemilih per citra pun hanya 22/100 dan MAE 16,85%: masalahnya bias bersama, bukan pemilihan model.
- Anchor skala per kamera (satu frame ber-`f` diketahui, Monte Carlo 2.000 undian) menurunkan MAE ke **4,28%** (p10–p90 3,64–5,29%), **71,3/95** lulus. Per scene: `session0_right` 1,07%, `session0_centre` 1,69%, `1cam` 1,89%, `session6_right` 6,81%, `0cam` 9,96%.
- Sisa galat mengikuti CV ensemble dalam scene: 0,9–1,6% untuk tiga kamera yang berhasil, 5,8–8,6% untuk `0cam`/`session6_right`. Satu anchor tidak cukup bila estimasi bergeser antar-frame. Untuk kamera statis, `f` anchor tetap jawabannya; ensemble hanya cek konsistensi/deteksi drift.

---

## 3. Kombinasi VP + f

| Metode | Lulus pitch/yaw <2° | Δpitch median | Δyaw median |
|---|---:|---:|---:|
| VP + f GT | **95/100** | 0,20° | 0,05° |
| VP + f GeoCalib | 47/100 | 2,46° | 1,12° |
| VP + f AnyCalib | 34/100 | 2,25° | 1,09° |
| VP v + pitch GeoCalib → f | 0/100 | — | — |

Per scene VP + AnyCalib vs VP + GeoCalib vs VP + GT:

| Scene | VP+GT | VP+Geo | VP+Any |
|---|---:|---:|---:|
| 0cam | 19/20 | 0/20 | 0/20 |
| 1cam | 16/20 | 2/20 | **12/20** |
| session0_centre | 20/20 | 20/20 | 20/20 |
| session0_right | 20/20 | 20/20 | 1/20 |
| session6_right | 20/20 | 5/20 | 1/20 |

**Bacaan:** VP sendirian bukan masalah; f yang salah merusak pose. AnyCalib hanya membantu 1cam, tetapi tidak cukup untuk gate 80%.

---

## 4. Lane fit: f/h dari geometri lajur

### 4.1 Uji sintetis

- 3 garis lajur, lebar 3,5 m, f/h/pose diketahui.
- Fit f, pitch, yaw, h, x0 dari titik 2D + lebar lajur.
- Tiga start berbeda semuanya konvergen ke **f=1500, h=8,00 m, pitch=10°, yaw=4°** dengan RMS 0 px.

**Artinya:** secara matematis, f dan h bisa dipisahkan dari garis lajur paralel + lebar lajur; tidak ada degenerasi yang menghalangi.

### 4.2 Uji nyata SVLD

Prototipe: `detect_lane_vp` → cluster segmen → 3 lajur berurutan → robust least squares.

| Scene | n | Lulus (RMS ≤5 px) | FIT_BAD | FIT_FAILED | Δf median | Δf min–max | RMS median |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0cam | 5 | **0** | 4 | 1 | 60,3% | 39,1–87,7% | 70,6 px |
| session0_right | 20 | **0** | 19 | 1 | 64,5% | 10,5–86,7% | 30,7 px |
| session6_right | 20 | **0** | 11 | 9 | 60,3% | 0,6–77,3% | 59,7 px |

- Satu citra `session6_right` memberi f=3404 vs GT 3384 (0,6%), tetapi RMS 5,35 px — masih gagal gate.
- RMS 11–139 px menunjukkan model tidak cocok dengan segmen yang terdeteksi, bukan sekadar noise.

**Penyebab:** clustering/assignment garis lajur dari LSD/Hough tidak cukup. Segmen dapat berupa tepi jalan, median, atau potongan marka yang tidak berurutan; asumsi 3 lajur bersebelahan dengan lebar sama sering dilanggar.

**Bukan kesimpulan:** "geometri lajur tidak bisa." Yang gagal adalah **lane extraction**, bukan identifiabilitas.

---

## 5. Vertical VP / gravity (E3)

### 5.1 Matematika

Dengan principal point di tengah, dua VP ortogonal memberi:

```
f^2 = -(u_road-cx)(u_vert-cx) - (v_road-cy)(v_vert-cy)
```

- **VP sejati dari GT**: f pulih **exact 0%** untuk kelima scene.
- **`vanishPoints` tersimpan**: f error **+2,5% s/d +26%**; `0cam` tidak menghasilkan solusi.
- **Gravitasi GeoCalib + VP**: f linear dari vektor gravitasi; **20/100** lulus, Δf median 20,2%; hanya `session0_centre` **20/20** (0,8%). Scene lain 21–39%.

### 5.2 Garis vertikal otomatis

Deteksi LSD untuk garis near-vertical (tiang/gedung), RANSAC VP vertikal, lalu f dari VP jalan + VP vertikal.

| Scene | n | Tanpa VP vertikal | F_BAD | OK | Δf median | Lulus Δf<5% | Sudut vs gravitasi |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0cam | 20 | 13 | 5 | 2 | 77,6% | **0/2** | 43,5° |
| 1cam | 20 | 0 | 2 | 18 | 9,0% | **4/18** | 35,7° |

- `1cam` paling baik, tetapi median 9% dan hanya 4/18 <5%.
- Sudut VP vertikal vs gravitasi 35–43° menunjukkan garis yang terdeteksi **bukan vertikal sejati** (pohon, tepi bangunan miring, bayangan).
- `0cam` gagal total: 13/20 tidak menemukan VP vertikal.

**Kesimpulan:** dua VP otomatis **belum layak** untuk SVLD dengan LSD klasik. VP vertikal butuh anotasi manual garis vertikal, detektor Manhattan-world/NeurVPS, atau prior gravitasi yang jauh lebih akurat.

### 5.3 GlobustVP (CVPR 2025)

GlobustVP diuji pada 7 frame (0cam 3, 1cam 3, session0_right 1), LSD semua garis, maksimum 40 garis, SCS `eps=1e-3`, 300 attempt.

| Scene | n | Menemukan 3 VP | Error vertikal median | Inlier vertikal | Catatan |
|---|---:|---:|---:|---:|---|
| 0cam | 3 | 2 | 24,35° | **0** | error 2,85° dari cross-product, bukan garis |
| 1cam | 3 | 3 | 35,19° | 0–6 | vertikal salah |
| session0_right | 1 | 0 | — | — | `NO_3VP` |

- SCS sering `optimal_inaccurate`; Clarabel tidak menerima opsi SCS. Tanpa MOSEK, solver lambat/tidak stabil.
- Solver memaksa 3 VP ortogonal; bila bukti garis hanya 2 arah, VP ketiga adalah cross-product tanpa inlier.
- **Bukan solusi turnkey** untuk SVLD. Perlu MOSEK/GPU, filter garis Manhattan yang lebih baik, atau pendekatan vehicle-VP.

## 6. Implikasi

1. **Jangan memakai GeoCalib/AnyCalib sebagai satu-satunya f.** Keduanya gagal di 4/5 scene.
2. **VP tetap unggul untuk yaw/pitch** jika f benar; fusi model tidak mengalahkan VP + f GT.
3. **f harus dari sumber geometri/known**:
   - kamera diketahui/spesifikasi,
   - dash fit dengan lebar lajur + periode dash standar (Cawang),
   - dua VP ortogonal (jalan + vertikal/lateral),
   - anotasi manual garis lajur yang bersih.
4. **Untuk SVLD**, GT f/pitch/yaw/h sudah tersedia; tidak perlu anchor untuk evaluasi. Untuk deployment, E2 memerlukan lane detector yang lebih baik.
5. **Scale** tetap dari kontainer 20 ft / lebar lajur per lokasi; bukan dari model.

---

## 7. Langkah berikutnya

1. **Lane detector yang lebih baik** — UFLD/CLRNet atau segmentasi marka; ulangi E2. Target RMS <3 px dan f <5%.
2. **Anotasi manual 3–4 garis lajur** pada 10 citra untuk menguji batas atas E2 (apakah assignment adalah satu-satunya masalah).
3. **Dua VP ortogonal** — jalan + vertikal; otomatis LSD gagal (0cam 2/20, 1cam 4/18). GlobustVP juga gagal (0 inlier vertikal, error 31–36°). Perlu anotasi manual garis vertikal, MOSEK/GPU, atau detektor Manhattan-world/NeurVPS.
4. **Dash fit Cawang-style** — bawa metode f/h dari Cawang (periode/dash standar + lebar lajur) ke SVLD jika standar marka diketahui.
5. **Joint fit** — f, pitch, yaw, h, k1 dengan constraint garis, VP, anchor container; robust loss + bootstrap.

---

## 8. Reproduksi

```powershell
# AnyCalib 100 citra (geoenv + AnyCalib)
$GEO = "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe"
foreach ($split in 'test','trainval') {
  foreach ($scene in '0cam','1cam','session0_centre','session0_right','session6_right') {
    & $GEO scripts\calib_compare\run_anycalib_batch.py `
      "out\svld_geocalib\frames\$split\$scene" `
      --model-id anycalib_pinhole --cam-id simple_pinhole `
      --out "out\svld_anycalib\${split}_${scene}.json"
  }
}
py scripts\eval_svld_anycalib.py --out out\svld_anycalib
py scripts\eval_svld_fusion.py --out out\svld_fusion
py scripts\eval_svld_focal_fusion.py --out out\svld_focal_fusion

# Lane fit (prototipe)
py scripts\svld_lane_fit.py --scene session0_right --out out\svld_lane_fit_right
py scripts\svld_lane_fit.py --scene session6_right --out out\svld_lane_fit_s6

# Vertical VP otomatis
py scripts\svld_vertical_vp.py --scene 0cam --out out\svld_vertical_vp_0cam
py scripts\svld_vertical_vp.py --scene 1cam --out out\svld_vertical_vp_1cam

# GlobustVP (cvxpy + SCS)
py scripts\svld_globustvp.py --scene 0cam --limit 3 --k-mode gt `
  --min-length 60 --max-lines 40 --line-filter all --solver SCS --eps 1e-3 `
  --out out\svld_globustvp_0cam_all
```

Artefak:

- `out/svld_anycalib/*.json` — 10 batch AnyCalib.
- `out/svld_anycalib/eval_anycalib.csv` — 100 baris.
- `out/svld_fusion/fusion_summary.csv` — kombinasi VP + f.
- `out/svld_focal_fusion/` — fusi `f` vs GT: per frame, metode, scene, dan Monte Carlo anchor.
- `out/svld_lane_fit*/lane_fit.csv` — prototipe lane fit.
- `out/svld_vertical_vp_*` — VP vertikal otomatis 0cam/1cam.
- `out/svld_globustvp_*` — hasil GlobustVP.
- `reports/svld-calib-fusion/anycalib_summary.csv` — ringkasan AnyCalib.
- `reports/svld-calib-fusion/fusion_summary.csv` — ringkasan kombinasi.
- `reports/svld-calib-fusion/lane_fit_summary.csv` — ringkasan lane fit.
- `reports/svld-calib-fusion/vertical_vp_summary.csv` — ringkasan vertical VP.
- `reports/svld-calib-fusion/globustvp_summary.csv` — ringkasan GlobustVP.
- `reports/svld-calib-fusion/fusion-gt-2026-11-26.md` — laporan fusi `f` terhadap GT SVLD.
- `reports/svld-calib-fusion/fusion_gt_methods.csv` — ringkasan metode fusi.
- `reports/svld-calib-fusion/fusion_gt_scenes.csv` — ringkasan fusi per scene.
- `reports/svld-calib-fusion/fusion_gt_anchor.csv` — Monte Carlo anchor per kamera.

---

## 9. Batas

- AnyCalib hanya diuji `pinhole/simple_pinhole`; model radial/KB belum.
- Lane fit memakai lebar lajur dari estimasi kendaraan (2,7–3,25 m), bukan pengukuran lapangan.
- Lane fit prototipe hanya 45 citra (0cam 5, right 20, session6 20), bukan 100.
- Segmentasi marka klasik (LSD/Hough) menjadi bottleneck; hasil bukan batas atas metode.
- Vertical VP otomatis hanya diuji 0cam/1cam; scene highway belum. GlobustVP hanya 7 frame, SCS tanpa MOSEK; NeurVPS/VPDETR belum diuji.
- SVLD `veh_size` preset; tidak dipakai di sini.
- GeoCalib/AnyCalib tidak memberi yaw/tinggi; hanya f/pitch/roll yang relevan.
