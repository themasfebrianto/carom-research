# I24-3D: Uji Kelayakan Ground Truth Kalibrasi

**Tanggal:** 19 November 2026  
**Ruang lingkup:** dataset I24-3D lengkap (50,04 GB) sudah tersedia lokal; parser diperbaiki; 3 kamera × 3 scene × 3 frame diuji dengan GeoCalib.

---

## 1. Ringkasan

1. **I24-3D `sceneX_hg.json` bukan ground truth kalibrasi pinhole.** `P` dibangun dari homografi (`H_inv`) ditambah kolom vanishing point vertikal; toolkit resmi memberi skala `* 0.01` lalu `Homography.scale_Z()` menyesuaikannya dengan tinggi box. RQ(`P`) tidak menghasilkan `fx/fy/cx/cy` fisik untuk 63 dari 102 kalibrasi.
2. **Dua kalibrasi untuk kamera yang sama (EB dan WB) tidak konsisten.** `f` berbeda median **7,1%**, p90 **24,6%**, maksimum **30,6%**. Ini cukup untuk menolak `f` dari `hg` sebagai GT.
3. **GeoCalib gagal pada geometri I24-3D.** Ketinggian kamera median **34 m** (90% di **28–45 m**), menghadap ke bawah **17–75°** (p2c3 hampir nadir). `f` GeoCalib meleset **−52% s/d +26%** (multi-frame; single-frame sampai **−76%**); pitch meleset **9–65°**.
4. **Gerbang Fase 1 (GeoCalib vs `P`, Δf/f <5%, Δpitch <2°) tidak dapat dijalankan** dengan data ini. Bukan karena GeoCalib saja, tetapi karena GT-nya tidak sah.
5. **I24-3D tetap berguna** untuk: ground-plane localization (H), tracking, dan GT dimensi 3D (`L/W/H`, 876.948 box, 720 objek). **Tidak** untuk GT intrinsik/pose, dan **bukan** side-view.

---

## 2. Dataset yang diperiksa

| Scene | Kamera/video | Baris anotasi | Objek unik | `spl_obj` | `track` | Frame anotasi / video | Video |
|---|---:|---:|---:|---:|---:|---:|---:|
| scene1 | 18 | 291.055 | 324 | 323 | 317 | 0–3.412 / 9.000 | 26,00 GB |
| scene2 | 17 (tanpa p2c2) | 146.365 | 114 | 114 | 187 | 0–1.801 / 3.582 | 12,40 GB |
| scene3 | 16 (tanpa p2c2, p2c4) | 439.528 | 282 | 281 | 561 | 0–1.801 / 3.531 | 11,50 GB |
| **Total** | **51 video** | **876.948** | **720** | **718** | **1.065** | — | **49,90 GB** |

- Video **3840×2160**; scene1 30 fps/300 s, scene2–3 60 fps/~119 s.
- Anotasi hanya mencakup **38–51%** frame video.
- Satuan dunia **kaki**; konversi 0,3048. Median manual: `semi` 22,29 × 2,68 × 4,05 m; `truck` 8,17 × 2,52 × 3,52 m.
- Kelas: sedan 272.145, midsize 300.242, pickup 152.486, semi 86.508, truck 34.111, van 31.375, `cs` 81 (tidak terdokumentasi di README).
- Tidak ada file 0 byte; `cache/` kosong. Dua file lock LibreOffice di `data/obj` dan `data/ts` (sisa sesi, bukan bagian dataset).

### Geometri kamera

Dari `P` (skala z sudah dikalibrasi di rilis ini):

- Posisi memanjang membentuk tiga grup tiang: **x ≈ 210 m (p1), 367 m (p2), 520 m (p3)**; lateral **y ≈ −5 m**.
- Tinggi kamera **median 34 m**; 90% di **28–45 m** (tanda negatif karena sumbu-z dunia mengarah ke bawah). Nilai ekstrem 0,7 m dan 90,6 m berasal dari entri kalibrasi rusak.
- Sudut hadap ke bawah (dari horizon `H` + `f`): **p2c3 ≈ 71–75°** (hampir nadir), **p1c5 ≈ 44–47°**, **p3c6 ≈ 17–20°**.
- Ini **bukan** CCTV jalan raya khas Indonesia (6–12 m, oblique). Ini kamera tiang sangat tinggi / aerial.

---

## 3. Metode

1. Parser `scripts/i24_parse.py` diperbaiki untuk struktur nyata `{"EB": {...}, "WB": {...}}`; `P` 3×4; output default hanya metrik ground-plane.
2. Tiga kamera dipilih berdasarkan **px per kaki** dari correspondence: **p2c3** (≈11,6 px/ft, paling “dekat”/nadir), **p1c5** (≈6,4), **p3c6** (≈3,5, paling jauh/oblique). Ketiganya ada di semua scene.
3. Frame 1080p diekstrak pada **5, 15, 25 s** (di dalam rentang anotasi semua scene).
4. GeoCalib dijalankan single-frame (27 citra) dan multi-frame shared-intrinsics (3 citra per kamera).
5. GT `f` diambil dari RQ(`P`) dan **ditandai tidak sah** bila K tidak plausibel (aspect ≥5%, principal point di luar 40% tengah, atau f <300 px).
6. GT pitch dihitung dari garis horizon `H` (baris ketiga) dan `f`: `pitch = atan((540 − y_horizon)/f)`; positif = menunduk. Untuk p2c3/p1c5/p3c6, nilai ini konsisten dengan horizon visual di luar atas frame.

Perintah lengkap ada di §8.

---

## 4. Hasil kalibrasi

### 4.1 Konsistensi ground-plane

Round-trip `H_inv(space_pts)` → `corr_pts`:

| Scene | Kalibrasi | RMS median | RMS maks | <1 px | <5 px |
|---|---:|---:|---:|---:|---:|
| scene1 | 36 | 3,76 px | 9,36 px | 0 | 26 |
| scene2 | 34 | 4,17 px | 8,41 px | 0 | 20 |
| scene3 | 32 | 3,84 px | 7,27 px | 0 | 21 |
| **Total** | **102** | **3,89 px** | **9,36 px** | **0** | **67** |

Tidak ada satu pun yang memenuhi target <1 px di `PAPER-REPO-Untuk-Menutup-Kelemahan.md`. Ini bukan sekadar noise: `H` adalah hasil `cv2.findHomography` pada titik klik, dan `space_pts` berada di frame jalan yang diluruskan (koreksi `curve` diterapkan setelah H). Jadi `H` memang **model tracking**, bukan homografi fotogrametri.

### 4.2 RQ(P) tidak fisik

- Hanya **39/102** kalibrasi yang K-nya plausibel (fx≈fy, principal point di 40% tengah).
- Contoh rusak: scene1 `p3c6` EB `fx=162`, `fy=452`, `cy=7.054`; kamera lain `cx` mencapai 1.870 pada frame 1920.
- `|P[2,2]|` bervariasi ~0,0003–0,03; artinya skala z sudah disesuaikan per kamera, tetapi K tetap tidak dijamin pinhole.
- Sumber resmi: `I24-3D-dataset/homography.py` menulis `P[:,2] = [vps[2][0], vps[2][1], 1] * 0.01`, lalu `scale_Z()` mencari skala terbaik memakai tinggi box. Tidak ada jaminan `P` terdekomposisi menjadi `K[R|t]` dengan K pinhole.

### 4.3 EB vs WB untuk kamera yang sama

`f` dari dua kalibrasi independen (frame dunia EB dan WB) harus sama karena intrinsik tidak bergantung arah:

| Statistik | Nilai |
|---|---:|
| Median \|Δf\|/f | **7,1%** |
| p90 | **24,6%** |
| Maksimum | **30,6%** |

Contoh: scene1 `p2c3` EB 1.715 vs WB 1.342 (24,4%); scene2 `p3c6` 2.461 vs 2.039 (18,8%); scene3 `p3c6` 2.456 vs 2.012 (19,9%). Sebagian kamera konsisten (scene2/3 `p2c3` ≈0,2%/0,0%; scene3 `p1c5` 0,7%), tetapi mayoritas tidak.

**Kesimpulan:** `f` dari `hg` tidak bisa dipakai sebagai GT tunggal. Yang bisa dipakai adalah **rentang** EB–WB, dan hanya untuk kamera yang kedua arahnya konsisten.

---

## 5. Hasil GeoCalib

### 5.1 Stabilitas single-frame

Untuk kamera dan scene yang sama, `f` GeoCalib bergantung pada frame:

| Scene | Kamera | f frame 5/15/25 s | Rentang |
|---|---|---:|---:|
| scene2 | p2c3 | 1.970 / 1.313 / 1.339 | 657 px |
| scene2 | p3c6 | 1.206 / 532 / 1.524 | 992 px |
| scene3 | p2c3 | 1.722 / 1.803 / 958 | 845 px |
| scene3 | p1c5 | 1.390 / 1.305 / 1.220 | 170 px |

Pitch juga liar: scene2 `p1c5` +14,0°/+14,3°/+4,8° (magnitudo 4,8–14,3°, tetapi arahnya “mendongak”, padahal kamera menunduk); roll 22,6°/43,5°/19,3°.

### 5.2 Multi-frame vs GT

Multi-frame memaksa satu `f` per kamera. Perbandingan dengan GT yang **kedua arahnya konsisten**:

| Scene | Kamera | GT f EB/WB | GT pitch | Geo f | Δf | Geo pitch | Δpitch |
|---|---|---|---:|---:|---:|---:|---:|
| scene2 | p2c3 | 1.540/1.537 | 72,6° | 1.489 | −3,2% | 7,2° | **−65,4°** |
| scene3 | p2c3 | 1.633/1.633 | 70,7° | 1.732 | +6,1% | 19,1° | **−51,6°** |
| scene2 | p1c5 | 1.362/1.397 | 46,9° | 1.082 | −21,6% | 13,7°* | **−33,2°** |
| scene3 | p1c5 | 1.326/1.317 | 47,4° | 1.310 | −0,9% | 37,6° | **−9,8°** |
| scene2 | p3c6 | 2.462/2.039† | 17,5–20,5° | 1.075 | **−52,4%** | 32,4° | +12,9° |
| scene3 | p3c6 | 2.456/2.012† | 17,4–20,3° | 1.251 | **−44,0%** | 31,3° | +12,3° |

\* Arah pitch GeoCalib berlawanan (mendongak) untuk kamera yang menunduk; dipakai magnitudo.  
† EB/WB berbeda ~19%; GT `f` tidak tunggal.

Catatan: “konsisten” di sini berarti **Δf EB–WB <3%**; bukan jaminan principal point K sepenuhnya plausibel (lihat kolom `gt_eb_plausible`/`gt_wb_plausible` di `summary.csv`). Scene1 `p3c6` dikecualikan karena `f_EB=162`, `f_WB=146` (K tidak plausibel); GT pitch dari nilai itu (78–79°) tidak bermakna.

### 5.3 Pola

- **`f` tidak punya bias sistematis**: kamera yang sama bisa −22% di satu scene dan −1% di scene lain (multi-frame); single-frame lebih liar, sampai −76% (scene2 `p3c6`: 532 px vs GT ~2.250 px). Ini gejala input out-of-distribution, bukan offset yang bisa dikoreksi.
- **Pitch selalu salah untuk kamera nadir/steep.** p2c3: GT ~71°, GeoCalib 7–19°. Selisih 52–65°.
- Untuk kamera paling oblique (p3c6), GeoCalib **melebihkan** pitch ~12–13°, dan `f` terlalu rendah ~44–52%.
- Satu kasus `f` hampir benar (p1c5 scene3, −0,9%) tetapi pitch tetap meleset ~10°. Artinya `f` yang kebetulan cocok tidak menyelamatkan pose.

---

## 6. Mengapa GeoCalib gagal

1. **Domain gap geometri.** GeoCalib dilatih untuk perspektif jalan/kamera ground-level dengan horizon di dalam frame. I24-3D memakai tiang 28–45 m; untuk p2c3 horizon berada **ribuan piksel di atas frame** (y ≈ −4.400). Tidak ada isyarat horizon yang bisa dipakai.
2. **P bukan matriks kamera terkalibrasi.** Kolom z berasal dari VP vertikal dengan skala arbitrer; `scale_Z` hanya mencocokkan tinggi box. RQ(`P`) tidak menghasilkan K pinhole yang konsisten.
3. **`vps` tidak bisa dipakai sebagai GT per kamera.** Ketiga VP identik untuk seluruh 102 kalibrasi, dan garis melalui VP longitudinal–lateral tidak cocok dengan horizon `H` (selisih sudut **0,1–14,8°**, median **2,1°**). Nilainya kemungkinan scene-level/salinan.
4. **Frame jalan diluruskan.** `space_to_im` menambahkan koreksi `curve` setelah H; `H`/`P` adalah model koordinat jalan, bukan proyeksi Euclidean global.

---

## 7. Implikasi dan keputusan

### Yang harus diubah

- **Gerbang Fase 1 dibatalkan sebagaimana dirancang.** Metrik Δf/f dan Δpitch terhadap `P` tidak sah. Fase 2 (dimensi) tetap boleh, tetapi **jangan** memakai asumsi GT `f`/pose.
- **Jangan memakai `fx` dari `P` sebagai GT** di dokumen mana pun. Jika perlu, gunakan rentang EB–WB dan tandai sebagai proxy.
- **I24-3D bukan side-view.** Ini kamera tinggi/nadir. Untuk validasi panjang dari siluet samping, tetap gunakan SVLD-3D bus atau pengukuran lapangan.

### Yang masih bisa dikerjakan dengan I24-3D

1. **GT dimensi 3D**: 876.948 box, 720 objek, `L/W/H` per kendaraan (termasuk semi/truck). Cocok untuk menguji pipeline dimensi dari box, bukan dari siluet.
2. **Ground-plane localization**: H memetakan kaki kendaraan ke koordinat jalan; bisa dipakai untuk menguji reproyeksi ground point (RMS 3,9 px).
3. **Tracking multi-kamera**: `tracklets`/`spl_obj` menyediakan lintasan; relevan untuk evaluasi tracking, bukan kalibrasi.
4. **Distribusi kelas dan ukuran** untuk prior dimensi kendaraan besar (semi/truck) di jalan bebas hambatan.

### Alternatif GT kalibrasi

- **SVLD-3D** sudah punya XML kalibrasi eksplisit dan reproyeksi 0,74 px; itu GT kalibrasi yang lebih layak untuk `f`.
- **Pengukuran lapangan** (lebar lajur, tinggi kamera) tetap diperlukan untuk CCTV Indonesia.
- Jika tetap ingin memakai I24-3D untuk pose, perlu **kalibrasi ulang** dengan 2D box GT (tidak tersedia di CSV ini) dan `scale_Z`, lalu uji ulang; itu pekerjaan terpisah, bukan validasi langsung.

---

## 8. Reproduksi

```powershell
# 1. Parser: 102 kalibrasi, metrik ground-plane
py scripts\i24_parse.py --hg I24-3D\data\hg\scene1_hg.json --out out\i24\calib_gt_scene1.json
py scripts\i24_parse.py --hg I24-3D\data\hg\scene2_hg.json --out out\i24\calib_gt_scene2.json
py scripts\i24_parse.py --hg I24-3D\data\hg\scene3_hg.json --out out\i24\calib_gt_scene3.json

# 2. Frame 1080p: 5/15/25 s, 3 kamera × 3 scene
foreach ($s in 'scene1','scene2','scene3') {
  foreach ($c in 'p2c3','p1c5','p3c6') {
    py scripts\i24_frames.py "I24-3D\video\$s\$c.mp4" `
      --out "out\i24\frames\$s" --times 5 15 25 `
      --prefix "${s}_$c" --scale 1920:1080
  }
}

# 3. GeoCalib single + multi-frame
$GEO = "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe"
$files = Get-ChildItem out\i24\frames -Recurse -Filter *.png | ForEach-Object FullName
& $GEO scripts\geocalib_batch.py @files --out out\i24\geocalib_all.json

foreach ($s in 'scene1','scene2','scene3') {
  foreach ($c in 'p2c3','p1c5','p3c6') {
    $d = "out\i24\frames_multi\${s}_$c"
    New-Item -ItemType Directory -Force $d | Out-Null
    Copy-Item "out\i24\frames\$s\*${c}_*.png" $d -Force
    & $GEO scripts\calib_compare\run_geocalib_multi.py $d `
      --out "out\i24\geocalib_multi_${s}_$c.json"
  }
}

# 4. Ringkasan
py scripts\i24_pilot_summary.py --out out\i24\i24_pilot_summary.csv
```

Artefak:

- `out/i24/calib_gt_scene{1,2,3}.json` — 102 kalibrasi, metrik ground-plane.
- `out/i24/geocalib_all.json` — 27 frame single.
- `out/i24/geocalib_multi_*.json` — 9 kamera multi-frame.
- `out/i24/i24_pilot_summary.csv` — tabel 9 baris.
- `reports/i24-3d-kalibrasi/summary.csv` — salinan tabel pilot.
- `reports/i24-3d-kalibrasi/ground_rms.csv` — 102 baris ground RMS.

---

## 9. Batas

- `f` GT adalah **proxy dari RQ(P)**, bukan kalibrasi resmi; sudah ditandai plausibilitasnya. Kesimpulan utama tidak bergantung pada nilai absolut `f` karena EB/WB saja sudah tidak konsisten.
- GT pitch memakai horizon `H`; untuk p2c3/p1c5/p3c6 nilai ini konsisten dengan horizon visual di luar frame, tetapi bukan pengukuran independen.
- Pilot ini 3 kamera × 3 scene × 3 frame, bukan benchmark 50 kamera. Namun kegagalannya sistematis dan besar (≥9° pitch, hingga 65°), bukan noise kecil.
- GeoCalib memakai bobot `pinhole` CPU; mode `distorted` dan AnyCalib belum diuji. Domain gap-nya sama, jadi hasilnya kemungkinan tidak berubah.
- I24-3D non-komersial; angka di laporan ini hanya untuk riset.

---

## 10. Rujukan

- D. Gloudemans, Y. Wang, G. Gumm, W. Barbour, D. B. Work. *The Interstate-24 3D Dataset*. BMVC 2023. arXiv:2308.14833.
- Toolkit: `https://github.com/I24-MOTION/I24-3D-dataset` (`homography.py`, `scale_Z`).
- `reports/DATASET-KALIBRASI.md` — perbandingan dataset.
- `PAPER-REPO-Untuk-Menutup-Kelemahan.md` §2 — rencana awal memakai `P` sebagai GT.
