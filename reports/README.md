# Artefak Validasi

Salinan kurasi dari folder kerja `out/`. Folder `out/` tetap di-`.gitignore` karena berisi gambar, mask, model, dan dataset; folder ini hanya memuat **laporan, ringkasan, dan tabel kecil** yang cukup untuk mengaudit angka di dokumen utama.

- Dikumpulkan: 19 November 2026
- HEAD saat dikumpulkan: `f4dd9c3` (plus hasil uji video LearnPinhole yang belum di-commit)
- Format: UTF-8; tidak ada citra, video, bobot model, atau dataset
- Jumlah: 69 berkas, ±231 KB

## Indeks

| Path | Isi |
|---|---|
| `00-akses.md` | Status akses dataset dan lisensi |
| `00-environment.md` | Mesin, environment, dan verifikasi |
| `external-setup.md` | Cara membuat environment dan mengunduh bobot |
| `i24/` | Uji parser I24-3D (sintetis, bukan data nyata) |
| `svld/` | Validasi SVLD-3D: kalibrasi, geometri, sensitivitas, subset sudut |
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

**Bukan validasi I24-3D.** Data I24-3D belum tersedia; berkas ini hanya membuktikan parser dan evaluator berjalan. Hasil nyata menunggu persetujuan akses.

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
