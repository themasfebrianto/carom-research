# Artefak Validasi

Salinan kurasi dari folder kerja `out/`. Folder `out/` tetap di-`.gitignore` karena berisi gambar, mask, model, dan dataset; folder ini hanya memuat **laporan, ringkasan, dan tabel kecil** yang cukup untuk mengaudit angka di dokumen utama.

- Dikumpulkan: 19 November 2026
- HEAD saat dikumpulkan: `a29c5dd` (plus perubahan lokal anchor container Cawang)
- Format: UTF-8; tidak ada citra, video, bobot model, atau dataset
- Jumlah: 102 berkas (awal) + 17 berkas vehicle-ruler (27 November 2026)
- Tambahan 26 November 2026: laporan fusi `f` GeoCalib+AnyCalib untuk Cawang dan untuk GT SVLD, beserta tabel ringkasannya
- Tambahan 27 November 2026: laporan geolokasi CCTV Bina Marga + cakupan KartaView, laporan dash + garis solid untuk memutus degenerasi `f`, diagnosis kegagalan GeoCalib + garis VP per citra, dan tool + pilot vehicle-ruler L1/L2 di SVLD

## Indeks

| Path | Isi |
|---|---|
| `00-akses.md` | Status akses dataset dan lisensi |
| `00-environment.md` | Mesin, environment, dan verifikasi |
| `external-setup.md` | Cara membuat environment dan mengunduh bobot |
| `i24/` | Uji parser I24-3D (sintetis); validasi data nyata ada di `i24-3d-kalibrasi/` |
| `i24-3d-kalibrasi/` | **Data nyata I24-3D**: 102 kalibrasi, konsistensi EB/WB, uji GeoCalib, keputusan GT |
| `svld/` | Validasi SVLD-3D test: kalibrasi, geometri, sensitivitas, subset sudut |
| `svld-trainval/` | **SVLD-3D trainval**: 14.592 gambar, 700 Truck, 1.166 Bus; kalibrasi, fit truk/bus, peringatan `veh_size` preset |
| `svld-geocalib/` | **GeoCalib vs SVLD GT**: 100 citra, 5 scene; f dan pitch; 20/100 lulus; multi 1/5 |
| `svld-vp/` | **VP jalan vs SVLD GT**: 95/100 (f GT), median per scene 5/5; lebar lajur 2,7–3,56 m |
| `svld-vp-failure-2026-11-27/` | **Diagnosis 53 kegagalan GeoCalib+VP**: 48 `f`-out, 5 outlier VP; bias `f` per kamera; scale+median VP 95/100 |
| `svld-vehicle-anchor/` | **Kendaraan well-known sebagai anchor**: bus Higer 12,6 vs kelas 12 m; anotasi SVLD sirkular |
| `svld-vehicle-ruler-2026-11-27/` | **Vehicle-ruler L1/L2**: 24 kandidat; pipeline simulasi 24/24; bbox 14,8%, mask 7,1%, tangent hull 3,8% vs face; lane detector 3/22 <10%; clicker + evaluator |
| `svld-calib-fusion/` | **AnyCalib + fusion f + lane fit**: AnyCalib 6/100; VP+Any 34/100; lane fit 0/45; fusi buta 17/100 vs GeoCalib 20/100, anchor per kamera 4,28% |
| `svld-vehicle-vp/` | **PerspectiveFields + vehicle VP + 3D box PnP**: PF gagal 4/5 scene; deep_vp dicek; 3D box GT f 0,00-0,21% |
| `3d-detector-survey/` | **Survey 3D detector**: CenterLoc3D (SVLD, no weights), BEVHeight++/CoBEV (pretrained roadside), Pro3D, MonoDGP, 3D-MOOD |
| `keypoint/` | Detectability keypoint dan mask-based fitting pada SVLD |
| `timepass/` | Side-view Cawang dan fitting kontainer |
| `cawang-container-anchor/` | **Anchor fisik Cawang**: 20 ft TEMA −0,2%; 40 ft SINKOR ambigu 40/45 ft |
| `calib-compare/` | GeoCalib vs AnyCalib vs VP vs Cawang dengan anchor `w=3,60 m`; termasuk fusi `f` dan median VP + anchor per kamera |
| `learnpinhole-video/` | Uji combo pada video tes LearnPinhole (480×360) |
| `geocalib-anycalib/` | Pros/cons GeoCalib vs AnyCalib + persiapan I24-3D |
| `DATASET-KALIBRASI.md` | Perbandingan SVLD-3D, I24-3D, I24V, CUTC, RoScenes; parameter dan batasannya |
| `cctv-dashfit-screening-2026-11-26.md` | Screening dash fit di 5+ CCTV; hanya Cawang yang identifiabel; GeoCalib tidak konsisten |
| `cctv-geolocation-2026-11-27/` | **Geolokasi CCTV Bina Marga + KartaView**: 258 kamera, 26 Dalam Kota; semua punya citra 2020; matching Cawang 2023 lemah (~25 SIFT/12 LoFTR) |
| `cctv-solid-line-2026-11-27/` | **Dash + garis solid**: BELMERA `f=811,6` (w=3,6 m); fixed-f RMS 1,674 vs 0,320; BORR melengkung, tidak valid |

### `i24/`

| Berkas | Isi |
|---|---|
| `calib_smoke.csv` | Uji parser `P` 3×4/4×3; `f_geo` sama dengan `f_gt` karena masukan sintetis |
| `gt_smoke.json` | Ground truth sintetis untuk uji parser |
| `geo_smoke.json` | Keluaran GeoCalib pada dua citra uji |
| `geocalib_smoke.json` | Ringkasan GeoCalib pada dua citra uji |

**Bukan validasi I24-3D.** Berkas di `i24/` adalah uji smoke sintetis. Data nyata sudah tersedia dan hasilnya ada di `i24-3d-kalibrasi/`.

### `i24-3d-kalibrasi/`

| Berkas | Isi |
|---|---|
| `README.md` | Laporan lengkap: struktur dataset, 102 kalibrasi, EB vs WB, GeoCalib single/multi-frame, keputusan |
| `summary.csv` | 9 baris pilot: GT f/pitch vs GeoCalib untuk p2c3, p1c5, p3c6 × 3 scene |
| `ground_rms.csv` | 102 baris ground RMS `H_inv` → `corr_pts` per scene/arah/kamera |

Hasil pokok: `f` EB vs WB berbeda median 7,1% (p90 24,6%); `P` bukan matriks kamera terkalibrasi; GeoCalib f meleset −52% s/d +26% dan pitch 9–65°. Gerbang kalibrasi Fase 1 dibatalkan; I24-3D dipakai untuk GT dimensi/ground-plane, bukan f/pose.

### `svld/`

| Berkas | Isi |
|---|---|
| `summary.json` | Inventaris test set: 2.237 citra, 8.142 objek; 7.396 Car, 745 Bus, 1 Truck; statistik dimensi dan kalibrasi per kelas |
| `reproj_summary.json` | Verifikasi kalibrasi: median RMS 0,74 px, p90 0,85 px, maks 1,08 px, 0 objek >2 px |
| `geocalib_5.json` | GeoCalib vs kalibrasi GT pada 5 scene |
| `geocalib_mini.md` | Sintesis uji GeoCalib: hanya 1/5 scene lulus |
| `fit_dims.csv` | 50 objek (26 Car, 24 Bus): GT, hasil fit, galat per sumbu, RMS |
| `fit_dims_report.md` | Metode dan tabel hasil uji geometri |
| `fit_dims_summary.json` | Ringkasan MAPE dan RMS |
| `sensitivity_report.md` | Sensitivitas noise 0–5 px |
| `sensitivity_summary.json` | Ringkasan per level noise: MAPE, jumlah gagal |
| `subsets.csv` | Hasil per objek untuk subset 8/6/5/4 sudut |
| `subsets_report.md` | Metode dan tabel subset sudut |
| `subsets_summary.json` | Ringkasan MAPE per subset |

Tiga CSV mentah berukuran besar **tidak disertakan** (lihat §Lisensi):

- `objects.csv` (1,4 MB) — satu baris per objek, memuat anotasi dan dimensi GT;
- `reproj_objects.csv` (1,5 MB) — satu baris per objek, memuat GT dan galat reproyeksi;
- `sensitivity.csv` (495 KB) — satu baris per objek per level noise.

Angka yang dipakai di dokumen utama semuanya ada di `summary.json`, `*_summary.json`, dan laporan MD. CSV tersebut dapat diregenerasi dengan perintah di bawah.

**Penting:** `veh_size` SVLD adalah preset ukuran, bukan pengukuran per kendaraan. MAPE 0,36% adalah self-consistency geometri; lihat `../reports/svld-trainval/README.md` §4.

### `svld-trainval/`

| Berkas | Isi |
|---|---|
| `README.md` | Inventaris trainval, verifikasi kalibrasi, uji fit truk/bus, peringatan preset |
| `inventory.csv` | 14.592 gambar, 39.477 objek (37.611 Car, 1.166 Bus, 700 Truck), 13,47 GB |
| `calib_reproj.csv` | 5 scene: median 0,73–0,84 px, maks 1,11 px, 0 objek >2 px |
| `fit_summary.csv` | 120 Truck, 80 Bus-D, 94 Bus-E: MAPE, eL/eW/eH, RMS |
| `fit_distance.csv` | Galat panjang per jarak: 0,15% (<35 m) → 4,39% (>150 m) |

Hasil pokok: kalibrasi trainval konsisten; box 20 m dan bus 12,6 m dapat direkonstruksi; **panjang memburuk dengan jarak**, W/H stabil. Label dimensi adalah preset, jadi bukan accuracy claim.

### `svld-geocalib/`

| Berkas | Isi |
|---|---|
| `README.md` | Uji akurasi GeoCalib vs GT SVLD: 100 citra, 5 scene, single + multi-frame |
| `summary.csv` | Ringkasan per scene/split: Δf, Δpitch, jumlah lulus |
| `single.csv` | 100 baris single-frame: GT, GeoCalib, galat, status |
| `multi.csv` | 5 baris multi-frame per scene |

Hasil pokok: **20/100 citra lulus** (hanya `session0_centre`); Δf median 14,9%, Δpitch median 3,03°; multi-frame 1/5. Yaw dan tinggi kamera tidak diuji karena GeoCalib tidak mengestimasi keduanya.

### `svld-vp/`

| Berkas | Isi |
|---|---|
| `README.md` | Uji VP jalan, perbandingan f GT vs f GeoCalib, dan pengukuran lebar lajur |
| `summary.csv` | Ringkasan VP per scene/split/sumber f: Δpitch, Δyaw, lulus |
| `lane_width.csv` | Lebar lajur dari marka vs posisi lateral box 3D per scene |
| `vp_scene_median.csv` | Median VP per scene: 5/5 lulus dengan f GT; 2/5 dengan f GeoCalib |
| `vp_gt.csv`, `vp_geo.csv` | 100 baris hasil VP dengan f GT dan f GeoCalib |
| `lane_width_frames.csv` | Lebar lajur per frame dari marka |

Hasil pokok: VP + `f` GT **95/100** lulus pitch/yaw <2° (median 0,20°/0,05°); median VP per scene **5/5** <0,5°. VP + `f` GeoCalib **47/100** (2,46°/1,12°); GeoCalib saja 20/100. VP memberi yaw; `f` tetap bottleneck. Lebar lajur **2,7–3,56 m**; 3,6 m tidak universal.

### `svld-vp-failure-2026-11-27/`

| Berkas | Isi |
|---|---|
| `README.md` | Laporan diagnosis: dekomposisi error, window `f` per citra, outlier VP, mitigasi |
| `diagnosis.csv` | 100 baris: `f` Geo/GT, window, komponen error, `cause`, `detail` |
| `failure_table.md` | 53 baris kegagalan dengan alasan per citra |
| `diagnosis_summary.json` | Ringkasan per scene, mitigasi, single anchor, outlier VP |

Hasil pokok: **47/100 pass**. **48/53 gagal murni karena `f`** di luar window; **5/53** adalah VP outlier + `f` di luar window; **0 kegagalan murni VP**. VP identik di 99/100 citra; dengan `f` GT, 95/100 pass. Bias `f` GeoCalib per kamera: GT/Geo **1,92×** (0cam), **1,14×** (1cam), **1,01×** (session0_centre), **1,18×** (session0_right), **1,31×** (session6_right). Window `f`: 0cam −24/+45%, 1cam −8,8/+14,2%, session0_centre −11,7/+17,4%, session0_right −18,2/+29,4%, session6 −13,5/+14,4%. Mitigasi: scale per kamera + median VP **95/100**; affine + median VP **100/100** (oracle). 4 outlier VP 1cam (`v` +237..+342 vs normal −42) dan 1 outlier 0cam (6 inlier) ditolak oleh gate `v < cy` / `inliers ≥ 8`. Detail: `svld-vp-failure-2026-11-27/README.md`.

### `svld-vehicle-anchor/`

| Berkas | Isi |
|---|---|
| `README.md` | Uji kelayakan kendaraan well-known sebagai anchor; contoh bus Higer KLQ6129; mengapa anotasi SVLD sirkular |

Hasil pokok: `veh_size` SVLD preset; bus Higer kelas 12 m diberi 12,6 × 2,75 × 2,8 m. Anchor kendaraan hanya sah dengan datasheet model/year + anotasi manual 8 sudut/5 titik, 3–5 instance; perkiraan 3–5%, tidak sebaik container 20 ft Cawang (0,2%).

### `svld-calib-fusion/`

| Berkas | Isi |
|---|---|
| `README.md` | AnyCalib 100 citra, fusion f, VP+Any/Geo/GT, lane fit sintetis vs nyata |
| `anycalib_summary.csv` | AnyCalib vs GeoCalib per scene/split |
| `fusion_summary.csv` | VP + f GT/Geo/Any dan f dari pitch GeoCalib |
| `lane_fit_summary.csv` | Lane fit: 0/45 OK; RMS dan Δf per scene |
| `vertical_vp_summary.csv` | Vertical VP otomatis: 0cam 2/20; 1cam 18/20 tapi 4/18 lulus |
| `globustvp_summary.csv` | GlobustVP: 0cam 2/3, 1cam 3/3, tapi vertikal 24–35° dan 0 inlier |
| `fusion-gt-2026-11-26.md` | **Fusi f vs GT SVLD**: 50/50 17/100 vs GeoCalib 20/100; korelasi galat 0,93; anchor per kamera 4,28% |
| `fusion_gt_methods.csv` | Ringkasan metode fusi terhadap GT |
| `fusion_gt_scenes.csv` | Ringkasan fusi per scene |
| `fusion_gt_anchor.csv` | Monte Carlo anchor skala per kamera |

Hasil pokok: AnyCalib **6/100** (median 18,2%), GeoCalib 20/100; VP+Any **34/100**, VP+Geo 47/100, VP+GT 95/100. **Fusi buta 50/50 17/100**, MAE 19,53% vs GeoCalib 19,35%: kedua model bias ke arah yang sama (rasio 0,807/0,830, korelasi galat 0,929). Setelah skala per kamera di-anchor dengan satu frame ber-`f` diketahui, ensemble memberi MAE **4,28%** dan **71/95** lulus sebagai ukuran **stabilitas relatif** (3/5 kamera hampir sempurna; `0cam` dan `session6_right` tetap gagal); `f` anchor tetap jawabannya. Lane fit identifiabel di sintetis, tetapi **0/45** nyata karena lane extraction. Vertical VP otomatis belum layak (0cam 2/20; 1cam 4/18). GlobustVP tidak turnkey (vertikal 24–35°, 0 inlier).

### `keypoint/`

| Berkas | Isi |
|---|---|
| `detectability.csv` | Hasil per objek: GT, deteksi, keypoint yang cocok |
| `detectability_report.md` | Metode dan hasil: match 56,9%; 5/5 Car 44,1%, Bus 0% |
| `detectability_summary.json` | Ringkasan per kelas |
| `mask_fit.csv` | Hasil per objek untuk YOLO11n-seg |
| `mask_fit_report.md` | Metode dan hasil: MAPE 12,19%; W 7,11%, H 7,55%, L 21,92% |
| `mask_fit_summary.json` | Ringkasan per kelas dan sumbu |

### `timepass/`

| Path | Isi |
|---|---|
| `timepass_bus.csv` | Sampel side-view mentah |
| `cand_*/`, `cand2_*/` | Kandidat kendaraan per waktu, dua kriteria seleksi |
| `lower/timepass_bus.csv` | Batch lower-envelope: 6 kendaraan, 6,44–17,37 m |
| `yolo26/timepass_bus.csv` | Batch YOLO26-seg pembanding |
| `container_fit_report.md` | **Hasil negatif** fitting kontainer dengan mask warna: 13,81 m (+13,3%) |
| `container20/container_fit.json` | **Hasil bersih** 20 ft TEMA: 6,046 m vs 6,058 m (−0,2%), IoU 0,972 |

Catatan: `container_fit_report.md` adalah percobaan lama dengan threshold warna HSV. Hasil yang berlaku adalah `container20/container_fit.json` dan bagian "Validasi 20 ft" di `../HASIL-TIMEPASS-CAWANG.md`; mask-nya berasal dari Grounded SAM 2 dengan box prompt container-only.

### `cawang-container-anchor/`

| Berkas | Isi |
|---|---|
| `README.md` | Anchor fisik Cawang: 20 ft TEMA vs standar, 40 ft SINKOR ambigu, implikasi 3,6 m |
| `container_anchor.csv` | Ringkasan 20 ft dan 40 ft GrabCut |
| `container_anchor.json` | Versi JSON tabel |
| `20ft_tema_fit.json` | Fit 20 ft terverifikasi: L 6,046 m (−0,2%), W 2,437 m |
| `40ft_sinkor_grabcut_fit.json` | Fit 40 ft GrabCut: L 12,45 m; W bias side-view |

Hasil pokok: 20 ft TEMA memvalidasi skala Cawang (3,6 m) dalam ~0,2%; 40 ft SINKOR tetap ambigu 40/45 ft (SAM2 13,99 m vs GrabCut 12,45 m). Tanpa lapangan, 20 ft adalah physical anchor terbaik.

### `calib-compare/`

| Berkas | Isi |
|---|---|
| `README.md` | Laporan uji banding GeoCalib, AnyCalib, VP, dan Cawang dengan anchor `w=3,60 m` |
| `summary.csv` | Tabel f, pitch, yaw, h, RMS fixed pose/fixed f |
| `fits.json` | Hasil fitting lengkap 18 tepi dash, invarian, dan parameter |
| `geocalib_*.json` | Keluaran GeoCalib single/multi-frame, termasuk varian distorted |
| `anycalib_*.json` | Keluaran AnyCalib `simple_pinhole`, `pinhole`, `radial:1`, dan varian model |
| `fusion-2026-11-26.md` | **Fusi f GeoCalib + AnyCalib**: 8 median temporal Cawang, 50/50 vs bobot terkalibrasi, LOO, varian model |
| `median-vp-anchor-2026-11-27.md` | **Median VP + anchor f di Cawang**: f error 0,88% (dash anchor) / 1,44% (blind), pose Δ +0,05°/+0,32°, RMS 1,37–1,44 px |
| `median_vp_anchor_frames.csv` | 8 frame: f Geo/Any/50-50, f dash scale, f blind scale, error, pitch/yaw |
| `median_vp_anchor_rms.csv` | 6 baris: RMS fixed pose anchor dash/buta pada median2/t350/t500 |
| `median_vp_anchor_summary.json` | Ringkasan varian, median VP, scale, single anchor LOO |
| `cawang_vp8.json` | VP per frame + median |
| `fusion_frames.csv` | Tabel per frame: f GeoCalib, AnyCalib, rata-rata, galat |
| `fusion_summary.csv` | Ringkasan metode fusi (bias, MAE, RMSE, maks, lulus 5%) |
| `fusion_distorted_summary.csv` | Ringkasan varian GeoCalib distorted |

Hasil pokok: Cawang dash fit tetap paling konsisten (RMS 1,101 px); GeoCalib `f` 9–13% terlalu rendah; AnyCalib +1,6% pada frame TEMA tetapi +9–12% pada frame lain; VP-only cukup untuk inisialisasi, bukan pengganti fitting. **Fusi 50/50 GeoCalib+AnyCalib** pada 8 frame memberi MAE 1,58%, maks 3,92%, 8/8 lulus 5% — karena bias kedua model berlawanan; ini spesifik Cawang, bukan sifat umum.

### `learnpinhole-video/`

| Berkas | Isi |
|---|---|
| `README.md` | Uji combo GeoCalib + AnyCalib + VP + anchor lebar jalan pada video tes LearnPinhole |
| `summary.csv` | Ringkasan f, pitch, yaw, h baseline dan hasil uji |
| `lane_vp.json` | VP per frame dari `lane_vp.detect_lane_vp` |
| `geocalib_*.json` | GeoCalib multi-frame dan single-frame |
| `anycalib_simple.json` | AnyCalib 8 frame |

Hasil pokok: GeoCalib multi `f=501,80` cocok dengan baseline `≈502`; VP pitch/yaw `4,91°/−1,66°` cocok dengan baseline `4,86°/−1,75°`; AnyCalib median `528,22` (+5,2%, range 510–598); anchor lebar jalan tidak stabil karena jalan melengkung dan batas kanan keluar frame.

### `geocalib-anycalib/`

| Berkas | Isi |
|---|---|
| `README.md` | Pros/cons GeoCalib vs AnyCalib, alasan VP + anchor tetap wajib, dan persiapan test I24-3D |

Ringkas: GeoCalib/AnyCalib hanya estimator intrinsik/pose awal; yaw tetap dari VP dan skala tetap dari anchor. I24-3D cukup dimulai dari `scene1_hg.json` + satu video kamera, bukan 50 GB.

### `cctv-geolocation-2026-11-27/`

| Berkas | Isi |
|---|---|
| `README.md` | Laporan lengkap: metode KM + OSM, cakupan KartaView, matching SIFT/LoFTR, batasan |
| `dalam_kota_cameras.csv` | 26 kamera Cawang–Pluit: KM, arah, koordinat, status, offset |
| `streetview_coverage.csv` | 26 baris cakupan KartaView: jarak, tanggal, proyeksi, ID |
| `geolocate_summary.json` | Ringkasan 258 kamera dan per-ruas |
| `streetview_summary.json` | Ringkasan cakupan 26 kamera |

Hasil pokok: 258 kamera, 222 berkoordinat, 56 interpolasi KM, 20 clamped. Dalam Kota: 26 kamera, 21 `provisional_stationing`, 5 `interpolated_km`; offset existing vs centerline OSM median 21,8 m, maks 133,4 m. KartaView 26/26 usable, median 2,1 m, maks 6,5 m, semua 2020 `PLANE`. Panorama Cawang 2023 berjarak 210 m; SIFT ~25 inlier, LoFTR ~12. **Street view tidak cukup untuk `f`/pose.** Angka 115/158 inlier sebelumnya tidak valid karena thumbnail perspektif diperlakukan sebagai equirect.

### `svld-vehicle-ruler-2026-11-27/`

| Berkas | Isi |
|---|---|
| `README.md` | Laporan lengkap: 24 kandidat, protokol 5 titik, validasi pipeline, ablasi bbox/mask, detektor lajur, batasan |
| `candidates.csv` | 24 kandidat: scene, kelas, bbox, jarak, sudut, `W_preset`, path citra/anotasi/kalibrasi |
| `auto_results.csv` | 24 baris pilot: `V_face`, `V_bbox`, `V_mask`, rasio, lane, `w_formula`, `w_ref`, error |
| `auto_summary.json` | Ringkasan ablasi body source, formula, dan lane detector |
| `sim_results.csv` | 24 baris validasi pipeline dengan titik simulasi + lane oracle |
| `sim_summary.json` | Ringkasan L1/L2 simulasi |
| `annotations_sim.csv` | Titik simulasi (bukan anotasi independen) |
| `tangent_hull_results.csv` | 24 baris tangent hull: `body`/`footprint` width, error, side ratio, hull IoU, deadzone |
| `tangent_hull_summary.json` | Ringkasan tangent hull per sudut/kelas |
| `overlays/` | Contoh overlay 4 anchor + 4 overlay tangent hull |

Hasil pokok: pipeline simulasi 24/24, `eW` median 0,37%, `ew` median 0,34%. Pada citra nyata, bbox 2D 14,8% dan YOLO mask 7,1% lebih lebar dari muka kendaraan; tangent hull `body` median 3,8% (p90 12,1%), terbaik di 0–3° (2,6%) tetapi tidak universal. Formula konsisten 22/22 <5%, tetapi detektor lajur hanya 3/22 dalam 10% prior. **L1/L2 final menunggu anotasi manual.**

### `cctv-solid-line-2026-11-27/`

| Berkas | Isi |
|---|---|
| `README.md` | Laporan lengkap: model dash + solid, fixed-f RMS, scan `f`, sensitivitas, BORR |
| `solid_fit_cases.csv` | 14 kasus: dash-only, solid, sweep `w`, sweep period, near/far, wrong side, BORR |
| `belmera_dash_fit.csv/.json` | Baseline dash-only BELMERA |
| `belmera_solid_fit.csv/.json` | Fit dash + garis kuning median, `w=3,6 m`, period 13 m |
| `belmera_solid_fit_scan.csv` | Scan `f` 700–950 |
| `belmera_solid_yellow.json` | 20 titik garis kuning median |
| `borr_solid_fit.csv/.json` | Fit BORR (kontrol negatif) |
| `borr_solid_fit_scan.csv` | Scan `f` BORR |

Hasil pokok: dash-only BELMERA `f=1101,09`, RMS 0,320, **degenerate** (fixed `f=989,11` tetap 0,320). Dash + solid: `f=811,55`, pitch 15,551°, yaw −0,106°, `h=10,438 m`, RMS 0,439; fixed `f=989,11` → RMS 1,674; fixed `f=1101,09` → RMS 2,469. Scan minimum di ~810. Sensitivitas `w`: 3,0→985,3; 3,3→890,8; 3,6→811,6; 3,9→744,1. Near vs far 809,3 vs 819,0. BORR melengkung: `f=987,16`, fixed `f=1663,67` RMS 3,500; tidak valid untuk model garis lurus.

## Cara mereproduksi

Environment, bobot, dan urutan perintah ada di:

- `../scripts/README.md` — urutan pakai seluruh skrip;
- `external-setup.md` — cara membuat environment dan mengunduh bobot.

Perintah yang menghasilkan CSV yang tidak disertakan:

```powershell
# objects.csv + summary.json
py scripts\parse_svld.py --root data\svld\TESTDATA2021\TESTDATA2021 --out out\svld

# reproj_objects.csv + reproj_summary.json
py scripts\svld_reproj_check.py --root data\svld\TESTDATA2021\TESTDATA2021 --out out\svld

# sensitivity.csv + sensitivity_summary.json
py scripts\svld_sensitivity.py --root data\svld\TESTDATA2021\TESTDATA2021 --out out\svld --n 50 --reps 20 --sigmas 0 0.5 1 2 3 5
```

## Lisensi dan batasan

- **SVLD-3D**: tidak ada lisensi eksplisit di repositori. Karena itu hanya ringkasan agregat dan tabel 50 objek yang disertakan; dump anotasi per objek tidak disalin. Dataset aslinya tidak disertakan.
- **I24-3D**: non-komersial, pendidikan, riset; akses komersial harus diminta.
- **TRUDI/TITUS**: CC BY-SA 4.0; dataset tidak disertakan.
- **SKoPe3D**: CC BY-NC-SA 4.0; belum diunduh.
- **RoScenes**: non-komersial; belum diunduh.
- Hasil Cawang (`timepass/`) adalah milik penelitian ini; video sumber tidak disertakan karena berisi citra lalu lintas yang dapat diidentifikasi.

Berkas di folder ini adalah bukti angka, bukan pengganti dokumen utama. Untuk interpretasi dan keterbatasan, lihat `../CATATAN-RISET-LENGKAP.md` dan `../HASIL-TIMEPASS-CAWANG.md`.
