# Artefak Validasi

Salinan kurasi dari folder kerja `out/`. Folder `out/` tetap di-`.gitignore` karena berisi gambar, mask, model, dan dataset; folder ini hanya memuat **laporan, ringkasan, dan tabel kecil** yang cukup untuk mengaudit angka di dokumen utama.

- Dikumpulkan: 19 November 2026
- HEAD saat dikumpulkan: `9657fd1` (plus perubahan lokal parser & laporan I24-3D)
- Format: UTF-8; tidak ada citra, video, bobot model, atau dataset
- Jumlah: 88 berkas

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
| `keypoint/` | Detectability keypoint dan mask-based fitting pada SVLD |
| `timepass/` | Side-view Cawang dan fitting kontainer |
| `calib-compare/` | GeoCalib vs AnyCalib vs VP vs Cawang dengan anchor `w=3,60 m` |
| `learnpinhole-video/` | Uji combo pada video tes LearnPinhole (480×360) |
| `geocalib-anycalib/` | Pros/cons GeoCalib vs AnyCalib + persiapan I24-3D |
| `DATASET-KALIBRASI.md` | Perbandingan SVLD-3D, I24-3D, I24V, CUTC, RoScenes; parameter dan batasannya |

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

### `calib-compare/`

| Berkas | Isi |
|---|---|
| `README.md` | Laporan uji banding GeoCalib, AnyCalib, VP, dan Cawang dengan anchor `w=3,60 m` |
| `summary.csv` | Tabel f, pitch, yaw, h, RMS fixed pose/fixed f |
| `fits.json` | Hasil fitting lengkap 18 tepi dash, invarian, dan parameter |
| `geocalib_*.json` | Keluaran GeoCalib single/multi-frame, termasuk varian distorted |
| `anycalib_*.json` | Keluaran AnyCalib `simple_pinhole`, `pinhole`, `radial:1`, dan varian model |

Hasil pokok: Cawang dash fit tetap paling konsisten (RMS 1,101 px); GeoCalib `f` 9–13% terlalu rendah; AnyCalib +1,6% pada frame TEMA tetapi +9–12% pada frame lain; VP-only cukup untuk inisialisasi, bukan pengganti fitting.

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
