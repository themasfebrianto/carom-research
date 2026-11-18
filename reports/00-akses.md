# Fase 0 — Status Akses Dataset

Diperbarui: 18 November 2026

## I24-3D

- **Status:** akun sudah didaftarkan; **menunggu persetujuan administrator**. Halaman registrasi: `https://i24motion.org/user/register`.
- **Yang perlu dilakukan:** tunggu email persetujuan; setelah masuk, cari unduhan **I24-3D**.
- **Catatan teknis:** situs menolak `curl`/`webfetch` otomatis dengan WAF, tetapi berhasil dibuka melalui browser. Registrasi tidak bisa diwakilkan.
- **Lisensi:** non-komersial, pendidikan, riset. Akses komersial harus diminta ke `info@i24motion.org`.
- **Data yang dibutuhkan:** `sceneX_hg.json`, `sceneX_annotations.csv`, video 4K per kamera. Mulai dari 3 scene; frame 1080p cukup untuk kalibrasi.

## SVLD-3D

- **Status:** test set sudah diunduh dan diekstrak.
- **Lokasi:** `data/svld/TESTDATA2021/TESTDATA2021/`
- **Isi:** 2.237 citra test, 8.142 objek, 5 file kalibrasi.
- **Resolusi:** 1.280×720 (5.461 objek) dan 1.920×1.080 (2.681 objek).
- **Kelas:** **Car 7.396, Bus 745, Truck 1**.
- **Temuan penting:** kelas **Truck praktis tidak ada** di test set (hanya 1, dengan dimensi 6,52×1,70×1,34 m — kemungkinan salah label). Jangan pakai SVLD-3D untuk validasi truk. Gunakan **Bus** sebagai proxy kendaraan besar; untuk truk gunakan I24-3D (semi/truck) atau RoScenes.
- **Lisensi:** tidak ada lisensi eksplisit di repo; perlakukan sebagai riset.
- **Inventaris:** `out/svld/summary.json`, `out/svld/objects.csv`.
- **Kalibrasi:** `f` (px), `fi` = pitch (rad), `theta` = yaw (rad), `h` (mm). Jangan menukar `fi` dan `theta`; horizon dari `vanishPoints` mengonfirmasi `fi` sebagai pitch.
- **Contoh:** `0cam` f=3743.78 px, pitch=6.43°, h=7.35 m; citra 1280×720. `session0_centre` f=2878.13 px, pitch=10.24°, h=10.12 m; citra 1920×1080.
- **Verifikasi kalibrasi:** reproyeksi 8.142 objek dengan `svld_reproj_check.py` → median RMS **0,74 px**, maks **1,08 px**, 0 objek >2 px. Kalibrasi SVLD dapat dipercaya.
- **Uji GeoCalib:** hanya **1/5 scene** lulus f<5% dan pitch<2°. Jadi untuk SVLD, pakai kalibrasi XML; jangan pakai GeoCalib sebagai sumber f. Detail: `out/svld/geocalib_mini.md`.
- **Uji geometri 50 objek:** 26 Car + 24 Bus, MAPE $L/W/H$ **0,36%**, RMS reproyeksi **0,35 px**. Ini uji dengan sudut 2D GT, bukan detektor. Detail: `out/svld/fit_dims_report.md`.
- **Sensitivitas noise:** 3 px → MAPE 2,79%, 1,7% fitting gagal; 5 px → 63,2% gagal. Target keypoint **≤3 px**. Detail: `out/svld/sensitivity_report.md`.
- **Subset sudut:** 4 kontak tanah + 1 sudut atap (5 titik) → MAPE **0,48%**, 0 gagal; 8 titik → 0,36%. Detektor tidak perlu 8 sudut box. Detail: `out/svld/subsets_report.md`.
- **Keypoint zero-shot:** 20 citra, 72 objek; match 56,9%; 5/5 di antara semua GT **36,1%** (Car 44,1%, Bus **0%**). Model `vehicle-keypoints` tidak siap untuk bus. Detail: `out/keypoint/detectability_report.md`.
- **Mask-based (YOLO11n-seg):** 20 citra, 21 objek; MAPE 12,19%; **W 7,11%, H 7,55%, L 21,92%**; mask IoU 0,796. W/H layak screening; panjang belum. Detail: `out/keypoint/mask_fit_report.md`.

## SKoPe3D

- **Status:** belum diunduh.
- **Halaman:** `https://skope3d.github.io/` (data melalui tautan Google Docs).
- **Rencana:** unduh subset 5.000 citra lebih dulu; 25.000 citra penuh hanya jika fine-tuning menuntut.
- **Lisensi:** paper CC BY-NC-SA 4.0; data cek halaman proyek.

## Sumber pendukung

| Sumber | Status | Catatan |
|---|---|---|
| TRUDI/TITUS | dataset publik (CC BY-SA 4.0) | 11.109 container, 2.780 trailer; MMDetection; domain pelabuhan |
| naver/cctv | repo publik, belum dipasang | model pretrained tersedia; dataset CCTV mereka belum tentu dirilis |
| MoGe-2 | repo publik, belum dipasang | MIT; bobot di Hugging Face |
| RoScenes | opsional, belum diunduh | non-komersial; data via ModelScope |
| Rope3D | tidak dipakai | akses hanya wilayah Cina |

## Aturan

- Dataset non-komersial hanya untuk validasi dan pembuktian konsep.
- Jangan menyalin data ke repo; `data/` dan `out/` sudah masuk `.gitignore`.
- Jangan mengunggah ulang data ke layanan publik.
