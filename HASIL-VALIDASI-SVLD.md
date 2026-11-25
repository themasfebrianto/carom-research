# Hasil Validasi SVLD-3D

Ringkasan seluruh uji pada SVLD-3D: kalibrasi, geometri, sensitivitas, subset sudut, keypoint zero-shot, dan mask-based. Dokumen ini menjawab pertanyaan: **sejauh mana adaptasi CAROM Air ke kamera CCTV terbukti?**

## 1. Ringkasan eksekutif

| Komponen | Hasil | Status |
|---|---|---|
| Kalibrasi SVLD | reproyeksi 8.142 objek, median 0,74 px | **terverifikasi** |
| GeoCalib pada 5 scene SVLD | 1/5 scene; **20/100 citra** lulus f<5% dan pitch<2°; multi 1/5 | **tidak reliabel** |
| VP + f GT | 95/100 lulus pitch/yaw <2°; median 0,20°/0,05° | **kuat untuk pose** |
| VP + f GeoCalib | 47/100; median 2,46°/1,12° | **f tetap bottleneck** |
| VP + f AnyCalib | 34/100; median 2,25°/1,09° | lebih buruk dari GeoCalib |
| AnyCalib f | 6/100 lulus Δf<5%; median 18,2% | **tidak membantu** |
| Lane fit f | 0/45 RMS≤5 px; f median 60% | **lane extraction gagal** |
| Vertical VP otomatis | 0cam 2/20 OK; 1cam 4/18 lulus | **belum layak** |
| GlobustVP (CVPR 2025) | 0cam 2/3, 1cam 3/3, tetapi vertikal 24–35° / 0 inlier | **tidak turnkey** |
| PerspectiveFields (CVPR 2023) | f rasio 0,33-0,95; VP vertikal 51-83 deg | **tidak layak** |
| 3D box PnP (box GT SVLD) | f 0,00-0,05% joint; 0,06-0,21% satu objek; noise 1,9% | **batas atas, butuh box akurat** |
| Depth Pro (ICLR 2025) | f 0,98 (s0c), 0,87 (1cam), 0,65 (s6r), 0,55 (0cam), 0,44 (s0r) | **tidak konsisten** |
| Lebar lajur SVLD | 2,7–3,56 m tergantung metode | **3,6 m tidak universal** |
| Geometri 50 objek (8 sudut GT) | MAPE 0,36%, RMS 0,35 px | **self-consistency** (label preset; lihat §4) |
| Sensitivitas noise 3 px | MAPE 2,79%, 1,7% gagal | **target keypoint ≤3 px** |
| Subset 5 titik | MAPE 0,48% | **cukup** |
| Keypoint zero-shot (20 citra) | 5/5 36,1% semua GT; Car 44,1%, Bus 0% | **belum cukup** |
| Mask-based (21 objek) | W 7,1%, H 7,6%, **L 21,9%** | **W/H layak, L tidak** |

**Putusan:** geometri dan kalibrasi terbukti; persepsi untuk lebar/tinggi mendekati berguna; **panjang belum layak dari satu kamera**. Klaim "CAROM Air bisa diadaptasi" harus dibatasi pada W/H, atau menunggu multi-frame/multi-kamera.

## 2. Kalibrasi

SVLD menyediakan `f`, `fi` (pitch), `theta` (yaw), dan `h` per scene. Verifikasi dilakukan dengan memproyeksikan 8.142 box 3D GT ke citra dan membandingkannya dengan 8 sudut 2D anotasi:

- median RMS **0,74 px**
- persentil 90 **0,85 px**
- maksimum **1,08 px**
- 0 objek >2 px

Kalibrasi SVLD konsisten dan sah untuk geometri. **Dimensi `veh_size` adalah preset**, bukan pengukuran per kendaraan; lihat §4 dan `reports/svld-trainval/README.md`.

## 3. GeoCalib

Diuji pada satu citra per scene (5 scene). Hasil:

| Scene | Δf/f | Δpitch | Status |
|---|---:|---:|---|
| 0cam | 51,0% | 3,41° | gagal |
| 1cam | 10,4% | 4,94° | gagal |
| session0_centre | 2,1% | 1,46° | lulus |
| session0_right | 16,2% | 0,81° | gagal (f) |
| session6_right | 28,5% | 4,99° | gagal |

Hanya **1/5** lulus. Kalibrasi XML SVLD benar, jadi ini domain gap GeoCalib pada scene jalan dengan vegetasi dan kamera miring. Gerbang validasi silang SOP §0.3.2 bekerja; jangan memakai GeoCalib tanpa cek per scene.

**Uji lanjutan 100 citra** (10 test + 10 trainval per scene) mengonfirmasi pola ini: **20/100 lulus (20%)**, hanya `session0_centre`; median Δf **14,9%**, Δpitch **3,03°**; multi-frame **1/5**. Hasil test dan trainval hampir sama (20% di keduanya), jadi bukan kebetulan satu frame. Detail: `reports/svld-geocalib/README.md`.

### 3.1 VP jalan (tambahan)

VP arah jalan diuji pada 100 citra yang sama, dengan dua sumber `f`:

| Sumber `f` | Lulus pitch/yaw <2° | Δpitch median | Δyaw median |
|---|---:|---:|---:|
| VP + `f` GT | **95/100** | **0,20°** | **0,05°** |
| VP + `f` GeoCalib | 47/100 | 2,46° | 1,12° |
| GeoCalib saja | 20/100 | 3,03° | tidak ada |

**Bacaan:** VP memberi **yaw** yang tidak dimiliki GeoCalib, dan pitch yang sangat akurat bila `f` benar. Dengan `f` GeoCalib, VP masih lebih baik dari GeoCalib saja (47 vs 20), tetapi **f yang salah tetap merusak pose**. Urutan yang masuk akal: `f` dari dash fit/kamera diketahui/anchor → VP untuk yaw/pitch.

`1cam` adalah outlier utama: 4/20 frame memilih persilangan garis yang salah; VP benar scene itu `(u≈464, v≈−42)`. **Median VP per scene** (kamera statis): dengan `f` GT **5/5 lulus**, maksimum Δpitch 0,43°/Δyaw 0,14°; dengan `f` GeoCalib **2/5**. Median temporal menghilangkan outlier 1cam, tetapi tidak memperbaiki `f`.

### 3.2 Lebar lajur dan anchor

- Marka: median per scene **3,0–3,56 m**, tetapi IQR lebar dan sebagian bimodal.
- Posisi lateral box 3D: puncak lajur memberi **2,7–3,25 m** (0cam 3,0; 1cam 2,7; session0_centre 3,2; session0_right 3,2; session6_right 3,25).
- **3,6 m bukan lebar universal.** Untuk skala absolut, ukur lebar lajur per lokasi; gunakan estimasi kendaraan sebagai prior dan marka sebagai cross-check. Untuk Cawang, jangan pakai `w=3,60` sebagai GT; container 20 ft tetap cek skala independen.
- Detail: `reports/svld-vp/README.md`.

### 3.3 AnyCalib dan fusion f

AnyCalib (`anycalib_pinhole`, `simple_pinhole`) pada 100 citra yang sama:

| Metode | Δf median | Lulus Δf<5% |
|---|---:|---:|
| GeoCalib | **14,9%** | **20/100** |
| AnyCalib | 18,2% | **6/100** |
| Rata-rata Geo+Any | 17,0% | 17/100 |
| 75% Geo + 25% Any | 16,0% | 20/100 |

AnyCalib hanya lebih baik di `1cam` (6,8–8,1% vs 10,6–13,4%); di `session0_centre` justru lebih buruk (7,3–9,7% vs 0,7–1,5%). **Fusion tidak mengalahkan GeoCalib.** VP + AnyCalib **34/100**, kalah dari VP + GeoCalib **47/100**.

### 3.4 f dari geometri lajur

Prototipe: 3 garis lajur + lebar lajur → fit f/pitch/yaw/h/x0.

- **Sintetis**: tiga start berbeda semuanya konvergen ke f/h yang benar (RMS 0 px). Secara matematis identifiabel.
- **Nyata SVLD**: **0/45** citra lulus (RMS ≤5 px); f median error **60–64%**, RMS 11–139 px. Bottleneck: clustering/assignment garis dari LSD/Hough, bukan matematikanya.
- Satu citra `session6_right` memberi f error 0,6%, tetapi RMS 5,35 px; belum cukup.

**Kesimpulan:** lane fit butuh lane detector/assignment yang lebih baik (UFLD/CLRNet atau anotasi manual), atau dash fit dengan periode/standar marka.

### 3.5 Vertical VP otomatis

- **VP sejati dari GT**: f exact 0% untuk 5 scene; `vanishPoints` tersimpan memberi error +2,5–26% (0cam invalid).
- **Gravitasi GeoCalib + VP jalan**: f linear, tetapi hanya `session0_centre` yang lulus (20/20, 0,8%); overall 20/100, median 20,2%.
- **Garis vertikal otomatis (LSD + RANSAC)**:
  - `0cam`: 13/20 tidak menemukan VP vertikal, 5 F_BAD, hanya **2/20 OK**; Δf median 77,6%.
  - `1cam`: 18/20 OK, tetapi Δf median **9,0%**, hanya **4/18** lulus.
  - Sudut VP vertikal vs gravitasi **35–43°** → garis yang terdeteksi bukan vertikal sejati.
- **Kesimpulan:** dua VP otomatis belum layak di SVLD. Perlu anotasi manual garis vertikal atau detektor Manhattan-world/NeurVPS; gravitasi GeoCalib hanya bisa jadi prior/consistency check.

**GlobustVP (CVPR 2025):** 7 frame (0cam 3, 1cam 3, session0_right 1), SCS `eps=1e-3`, 300 attempt. `0cam` 2/3 menemukan 3 VP tetapi VP vertikal **0 inlier** (error 2,85° dari cross-product); `1cam` 3/3 tetapi error vertikal **31–36°**; `session0_right` **NO_3VP**. SCS sering `optimal_inaccurate`; tanpa MOSEK solver lambat/tidak stabil. **Bukan solusi turnkey.**

### 3.6 PerspectiveFields dan vehicle VP (deep_vp)

**PerspectiveFields (CVPR 2023)** memprediksi roll, pitch, vFoV, dan up-vector field. Pada 100 citra SVLD: f rasio median **0,328** (0cam), **0,952** (1cam), **0,691** (session0_centre), **0,582** (session0_right), **0,576** (session6_right); hanya 1cam yang lulus 5% (11/20). VP vertikal dari up-vector field meleset **51-83 deg**. Model punya prior vFoV ~30-33 deg, sehingga gagal pada lensa tele 10-14 deg.

**deep_vp (ICANN 2021)** adalah pendekatan traffic camera yang tepat secara konsep: CNN memprediksi dua VP horizontal ortogonal dari crop kendaraan, lalu `f^2 = -(v1-c).(v2-c)`; tidak butuh garis vertikal. Namun bobot pretrained ada di OneDrive SharePoint yang meminta login, dan tidak ada mirror. Geometri yang sama diuji dari 8 sudut box SVLD: median angular error VP 1,7-20 deg tergantung scene; f dari pasangan VP panjang-lebar masih jauh dari GT (0cam 437 vs 3744 px). Kendaraan SVLD hanya ~50 px, jauh lebih kecil dari crop BoxCars/BrnoCarPark.

**3D box PnP** jauh lebih kuat. Dengan 8 sudut box 3D + dimensi box, satu kendaraan memberi f, pitch, yaw, dan h. Pada box GT SVLD, error f **0,00-0,05%** (joint per citra) dan **0,06-0,21%** (satu objek). Sensitivitas: noise 2D 1 px -> 0,37%; dimensi 3% -> 1,27%; kombinasi 1 px + 3% dimensi + 0,3 m posisi + 2 deg yaw -> **1,86%** (p90 4,3%). Ini batas atas karena box GT konsisten dengan kalibrasi; detektor 3D nyata harus akurat. **Penting:** hanya dimensi + 8 sudut 2D (tanpa posisi world) bersifat ambigu; uji 50 objek memberi error 0,7-1,6% di session6/0cam tetapi 88-651% di 1cam/session0 karena salah minimum. Detektor 3D harus memberi box world-space (posisi + dimensi + orientasi), atau beberapa box di-joint. Model `yolo3Dbbox` yang ada meleset median H 20%, W 7%, L 15% (truk/bus lebih buruk), sehingga self-calibration-nya belum berhasil.

**Depth Pro (ICLR 2025)** langsung memprediksi f: rasio 0,979 (session0_centre), 0,870 (1cam), 0,652 (session6_right), 0,546 (0cam), 0,441 (session0_right). Hanya session0_centre yang <5%; model tetap tidak konsisten untuk lensa tele dan inference CPU 3-5 menit/citra. Detail: `reports/svld-vehicle-vp/README.md`.

## 4. Geometri

50 objek (26 Car, 24 Bus), jarak 13,5–122,9 m. Input: 8 sudut 2D GT + kalibrasi XML. Fit 6 parameter (X, Y, yaw, L, W, H).

| Metrik | Mean | Median | p90 | Max |
|---|---:|---:|---:|---:|
| MAPE LWH | **0,36%** | 0,23% | 0,81% | 1,18% |
| L | 0,65% | 0,36% | 1,59% | 3,16% |
| W | 0,15% | 0,12% | 0,33% | 0,44% |
| H | 0,30% | 0,23% | 0,53% | 1,25% |
| RMS | 0,35 px | 0,35 px | 0,41 px | 0,46 px |

Geometri, satuan, dan model kamera benar. Ini uji dengan sudut GT, bukan detektor.

> **Penting — 19 November 2026.** `veh_size` SVLD adalah **preset ukuran**, bukan hasil pengukuran per kendaraan:
>
> - Trainval: **1.164 dari 1.166 Bus** memiliki `L=12,60 m`; 184 Truck memiliki `L=20,00 m`.
> - Test: Bus memakai `L=12,00 m` atau `9,46 m`.
> - Car juga memakai preset: hanya 116 nilai `L` unik untuk 37.611 objek; 5 nilai teratas mencakup ~17.000 objek.
>
> Karena `vertex2d`, `vertex3d`, dan `veh_size` dibangun dari box yang sama, fit 8 sudut akan selalu mengembalikan `veh_size` hampir tepat. **MAPE 0,36% adalah bukti kalibrasi/parameterisasi, bukan akurasi fisik.** Trainval (700 Truck, 1.166 Bus) cocok untuk stress-test, bukan klaim akurasi dunia nyata. Detail: `reports/svld-trainval/README.md`.

### 4.4 Kendaraan well-known sebagai anchor?

**Tidak bisa memakai anotasi SVLD.** `veh_size` adalah preset, dan `vertex2d` adalah proyeksi box preset itu. Contoh: bus Higer KLQ6129 (kelas 12 m) di `real_scene_cam0_003368` diberi `veh_size` **12,6 × 2,75 × 2,8 m**, sedangkan kelas 12 m biasanya **≈12,0 × 2,55 × 3,2 m** (L +5%, W +7,8%, H −12,5%). Memakai bus ini dari anotasi SVLD akan mewarisi galat preset.

Uji yang sah memerlukan **datasheet model/year + anotasi manual 8 sudut/5 titik** (bukan `vertex2d`), pada 3–5 instance. Perkiraan terbaik 3–5%, tidak sebaik kontainer 20 ft Cawang (0,2%). Untuk anchor fisik, tetap gunakan kontainer 20 ft; SVLD untuk kalibrasi/geometri. Detail: `reports/svld-vehicle-anchor/README.md`.

## 5. Sensitivitas dan subset

Noise Gaussian pada 8 sudut 2D:

| σ | MAPE | Gagal |
|---:|---:|---:|
| 0 | 0,36% | 0% |
| 1 px | 1,05% | 0% |
| 2 px | 1,91% | 0% |
| 3 px | 2,79% | 1,7% |
| 5 px | 4,57%* | 63,2% |

\* hanya 37% yang berhasil.

Subset sudut:

| Subset | MAPE | Gagal |
|---|---:|---:|
| 8 sudut | 0,36% | 0 |
| 6 sudut | 0,46% | 0 |
| **5 sudut** | **0,48%** | **0** |
| 4 kontak tanah | 2,39% | 1 |
| 4 sudut atap | 3,04% | 0 |

**Target keypoint: 5 titik (4 kontak tanah + 1 atap), akurasi ≤3 px.** Delapan sudut tidak diperlukan.

## 6. Keypoint zero-shot

Model `vehicle-keypoints` (YOLO26-pose, 14 keypoint, MIT) pada 20 citra (10 Car, 10 Bus), 72 objek GT.

| Kelompok | GT | Cocok | 5/5 di antara cocok | 5/5 dari semua GT |
|---|---:|---:|---:|---:|
| Semua | 72 | 41 (56,9%) | 63,4% | 36,1% |
| Car | 59 | 33 (55,9%) | 78,8% | 44,1% |
| Bus | 13 | 8 (61,5%) | 0% | 0% |

Model ini tidak siap untuk bus. Untuk mobil, sinyalnya ada tetapi match rate rendah. Zero-shot tidak cukup; perlu fine-tuning pada sudut CCTV atau pendekatan lain.

## 7. Mask-based

YOLO11n-seg (COCO) pada 20 citra, 21 objek. Fit 3D box ke mask body dengan differential evolution.

| Kelompok | n | MAPE | L | W | H | Mask IoU |
|---|---:|---:|---:|---:|---:|---:|
| Semua | 21 | 12,19% | 21,92% | 7,11% | 7,55% | 0,796 |
| Car | 12 | 12,86% | 22,20% | 8,07% | 8,32% | 0,780 |
| Bus | 9 | 11,30% | 21,56% | 5,83% | 6,51% | 0,820 |

Lebar dan tinggi layak untuk screening (<10%); panjang tidak. Mask body tidak memuat kontak ban; box yang lebih besar dan lebih jauh bisa memberi siluet yang mirip. Ini konsisten dengan hukum anisotropi proyek: galat longitudinal tumbuh dengan $z^2$, lateral dengan $z$.

## 8. Apa yang terbukti dan tidak

**Terbukti:**

- Kalibrasi SVLD dapat dipercaya (0,74 px).
- Parameterisasi box dan kalibrasi benar: dengan 2D sempurna, MAPE 0,36% (self-consistency, bukan akurasi fisik).
- Lima titik cukup; target akurasi ≤3 px.
- Mask-based memberi W/H ~7%, cukup untuk screening.
- GeoCalib tidak reliabel pada 4/5 scene SVLD; 100 citra mengonfirmasi hanya 20% lulus; gerbang SOP perlu.

**Belum terbukti:**

- Detektor 5 titik yang mencapai ≤3 px pada kendaraan nyata. Zero-shot gagal pada bus dan hanya 44,1% mobil.
- Panjang dari satu kamera. Mask-based 21,9%; ini batas fundamental, bukan sekadar detector.
- Estimator f yang mencapai <5% tanpa anchor: GeoCalib 20/100, AnyCalib 6/100, lane fit 0/45, vertical VP 0cam 2/20 / 1cam 4/18, PerspectiveFields 0/20 di 4 scene (hanya 1cam 11/20). 3D box PnP adalah batas atas dan butuh detektor 3D yang akurat.
- Adaptasi pada CCTV Indonesia. Semua data berasal dari AS/Cina/Eropa.

## 9. Implikasi untuk klaim riset

Klaim yang sah:

> "Kerangka geometri CAROM Air dapat diadaptasi untuk mengukur lebar dan tinggi kendaraan dari CCTV statis, dengan akurasi geometri <1% bila titik 2D tersedia, dan ~7% dengan mask-based. Panjang tidak dapat diandalkan dari satu kamera karena anisotropi."

Klaim yang tidak sah:

> "CAROM Air dapat mengukur L/W/H kendaraan dari CCTV dengan akurasi 10%."

Untuk panjang, diperlukan multi-frame, multi-kamera, atau model bentuk yang lebih kuat. Untuk bus/truk, diperlukan detektor yang dilatih pada kelas tersebut; model mobil tidak cukup.

## 10. Langkah berikutnya

1. **Hybrid** — mask untuk W/H, keypoint kontak tanah untuk L; uji pada 50 objek.
2. **Multi-frame/multi-kamera** — I24-3D sudah tersedia, tetapi bukan GT f/pose dan bukan side-view; lihat `reports/i24-3d-kalibrasi/README.md`.
3. **Trainval SVLD** — 14.592 gambar, 700 Truck + 1.166 Bus; gunakan untuk stress-test panjang/kelas besar, bukan accuracy claim. Lihat `reports/svld-trainval/README.md`.
4. **Fine-tune keypoint** — butuh GPU; `vehicle-keypoints` atau SKoPe3D.
5. **f dari geometri** — lane detector lebih baik (UFLD/CLRNet/manual), dua VP ortogonal yang tervalidasi, atau **3D box kendaraan PnP**. Lane fit klasik 0/45, vertical VP otomatis 0cam 2/20, 1cam 4/18, GlobustVP gagal (0 inlier vertikal), PerspectiveFields gagal di 4/5 scene. 3D box GT memberi f 0,00-0,21%; butuh detektor 3D akurat. Lihat `reports/svld-calib-fusion/README.md` dan `reports/svld-vehicle-vp/README.md`.
6. **Validasi lapangan Indonesia** — satu kendaraan diukur dengan meteran; tetap diperlukan.

**Catatan Cawang.** Side-view/lower-envelope pada satu kamera sudah dicoba: truk kontainer 40 ft terukur **14,0–14,3 m** (pembanding standar ≈14,6 m) dan batch 6 kendaraan memberi **6,4–17,4 m** yang masuk akal untuk box truck, 20 ft, 40 ft, dan truk panjang. Kecepatan belum stabil. **Validasi 20 ft dengan mask container-only: 6,046 m vs 6,058 m (−0,2%)** — hasil GT pertama yang bersih. Lihat `HASIL-TIMEPASS-CAWANG.md`.

## 11. Berkas

- `out/svld/geocalib_mini.md`
- `out/svld/fit_dims_report.md`
- `out/svld/sensitivity_report.md`
- `out/svld/subsets_report.md`
- `out/keypoint/detectability_report.md`
- `out/keypoint/mask_fit_report.md`
- `reports/svld-trainval/README.md` + `inventory.csv` + `calib_reproj.csv` + `fit_summary.csv` + `fit_distance.csv`
- `reports/svld-geocalib/README.md` + `summary.csv` + `single.csv` + `multi.csv`
- `reports/svld-vp/README.md` + `summary.csv` + `lane_width.csv` + `vp_gt.csv` + `vp_geo.csv`
- `reports/svld-calib-fusion/README.md` + `anycalib_summary.csv` + `fusion_summary.csv` + `lane_fit_summary.csv` + `vertical_vp_summary.csv` + `globustvp_summary.csv`
- `reports/svld-vehicle-vp/README.md` + `out/svld_perspective_fields/perspective_fields.csv` + `out/svld_box_calib/*`
- `reports/3d-detector-survey/README.md` - survey CenterLoc3D, BEVHeight++, CoBEV, Pro3D, MonoDGP, 3D-MOOD
- `scripts/svld_reproj_check.py`, `svld_fit_dims.py`, `svld_sensitivity.py`, `svld_subsets.py`, `svld_kp_detectability.py`, `svld_mask_fit.py`, `svld_lane_fit.py`, `svld_vertical_vp.py`, `svld_globustvp.py`, `eval_svld_anycalib.py`, `eval_svld_fusion.py`
