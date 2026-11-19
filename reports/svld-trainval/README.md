# SVLD-3D TRAINVAL: Inventaris, Kalibrasi, dan Uji Dimensi Truk/Bus

**Tanggal:** 19 November 2026  
**Data:** `SVLD-3D-TRAINVAL-SCENE-A-C`, `-SCENE-D`, `-SCENE-E` (13,47 GB, 14.592 gambar)  
**Status:** kalibrasi terverifikasi; dimensi **bukan** pengukuran per kendaraan (lihat §4).

---

## 1. Ringkasan

1. **14.592 gambar, 39.477 objek**: Car 37.611, Bus 1.166, **Truck 700**. Ini mengisi kekosongan truk di test set (hanya 1 Truck).
2. **Kalibrasi 5 scene konsisten**: reproyeksi 39.477 box 3D, median **0,73–0,84 px** per scene, maksimum **1,11 px**, **0 objek >2 px**.
3. **Peringatan penting:** `veh_size` SVLD adalah **preset ukuran**, bukan hasil pengukuran per kendaraan. Contoh: **1.164 dari 1.166 Bus** memiliki `L=12,60 m`; 184 Truck memiliki `L=20,00 m`; test set memakai Bus `12,00/9,46 m`. Uji fit dimensi karena itu adalah **self-consistency geometri**, bukan akurasi dunia nyata.
4. **Pilot fit 294 objek** (120 Truck, 80 Bus-D, 94 Bus-E): semua konvergen, RMS median **0,34–0,39 px**, MAPE LWH median **0,20–0,32%**. Galat **panjang** tumbuh dengan jarak: median 0,15% (<35 m) → **4,39%** (>150 m), maksimum **17,96%**. Lebar/tinggi tetap <0,5%.
5. **Kesimpulan:** trainval sangat berguna untuk stress-test pipeline pada truk panjang dan bus, dan untuk cek kalibrasi; **tidak** untuk mengklaim akurasi L/W/H dunia nyata.

---

## 2. Isi dataset

| Root | Gambar | Objek | Car | Bus | Truck | Ukuran | Resolusi | Calib |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| A-C | 7.043 | 22.229 | 21.528 | 1 | **700** | 3,41 GB | 1920×1080 | 3 |
| D | 3.848 | 11.890 | 10.913 | 977 | 0 | 5,06 GB | 1280×720 | 1 |
| E | 3.701 | 5.358 | 5.170 | 188 | 0 | 5,00 GB | 1280×720 | 1 |
| **Total** | **14.592** | **39.477** | **37.611** | **1.166** | **700** | **13,47 GB** | — | **5** |

- Truk hanya ada di scene A-C (`session0_centre`, `session0_right`, `session6_right`); D/E hanya Car dan Bus.
- `ImageSets/Main`: `trainval.txt` 14.592 baris, `val.txt` 1.621, `test.txt` 2.237. `train.txt` juga 14.592 (sama dengan trainval), jadi **gunakan `val.txt`** untuk validasi, bukan `train.txt`.
- File mentah ada di root repo (`SVLD-3D-TRAINVAL-*`), bukan di `data/svld/`; sudah di-`.gitignore`.

---

## 3. Kalibrasi

Reproyeksi 8 sudut 3D → 2D untuk seluruh objek:

| Root | Calib | Objek | Median | p90 | Maks | >2 px |
|---|---|---|---:|---:|---:|---:|
| A-C | `session0_centre` | 10.751 | 0,746 | 0,857 | 1,047 | 0 |
| A-C | `session0_right` | 8.664 | 0,742 | 0,863 | 1,016 | 0 |
| A-C | `session6_right` | 2.814 | 0,767 | 0,858 | 1,115 | 0 |
| D | `0cam` | 11.890 | 0,730 | 0,800 | 1,009 | 0 |
| E | `1cam` | 5.358 | 0,836 | 0,836 | 1,014 | 0 |

**Bacaan:** model kamera CenterLoc3D dan kalibrasi XML konsisten di semua scene, sama seperti test set (0,74 px). Tidak ada scene yang perlu dibuang.

---

## 4. Peringatan: `veh_size` adalah preset

Distribusi dimensi menunjukkan nilai yang berulang, bukan pengukuran kontinu:

| Kelas | Nilai yang dominan | Jumlah |
|---|---|---:|
| Bus trainval | `L=12,60 m` | **1.164 / 1.166** |
| Bus trainval | `W=2,75/2,76 m`; `H=2,80/2,92 m` | 688 + 476 |
| Bus test | `L=12,00 m` / `L=9,46 m` | 468 / 275 |
| Truck trainval | `L=5,20` / `20,00` / `4,80` / `7,43 m` | 204 / 184 / 156 / 89 |
| Truck trainval | `W=2,08` / `2,63` / `2,05 m` | 202 / 184 / 156 |
| Car trainval | 116 nilai `L` unik; 5 nilai teratas mencakup ~17.000 objek | — |

Artinya:

- `vertex3d`, `vertex2d`, dan `veh_size` saling konsisten **karena dibangun dari box yang sama**.
- Fit 8 sudut akan selalu mengembalikan `veh_size` hampir tepat; MAPE kecil adalah **bukti parameterisasi dan kalibrasi**, bukan bukti akurasi pengukuran.
- Klaim "MAPE 0,36%" pada test set sebelumnya harus dibaca sebagai **self-consistency**, bukan akurasi terhadap kendaraan nyata.
- Untuk truk, label 20,00 m adalah template kendaraan panjang; jangan menganggapnya hasil ukur 20 m aktual.

---

## 5. Hasil fit pilot

Input: 8 sudut 2D GT + kalibrasi XML; fit 6 parameter (X, Y, yaw, L, W, H). Ini uji geometri, bukan detektor.

| Run | Kelas | n | MAPE median | p90 | maks | eL median | eL maks | eW median | eH median | RMS median |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A-C | Truck | 120 | 0,20% | 1,22% | 6,31% | 0,35% | 17,96% | 0,09% | 0,14% | 0,34 px |
| D | Bus | 80 | 0,21% | 0,38% | 0,63% | 0,42% | 1,30% | 0,08% | 0,14% | 0,39 px |
| E | Bus | 94 | 0,32% | 0,87% | 1,25% | 0,52% | 2,91% | 0,12% | 0,27% | 0,37 px |

Stratifikasi jarak untuk panjang:

| Run | Jarak | n | eL median | eL maks | eW median | eH median |
|---|---|---:|---:|---:|---:|---:|
| Truck | <35 m | 40 | 0,15% | 0,59% | 0,05% | 0,08% |
| Truck | 35–65 m | 40 | 0,35% | 1,30% | 0,08% | 0,14% |
| Truck | 65–100 m | 13 | 0,78% | 2,91% | 0,16% | 0,16% |
| Truck | 100–150 m | 15 | 1,99% | 7,47% | 0,21% | 0,46% |
| Truck | **>150 m** | 12 | **4,39%** | **17,96%** | 0,30% | 0,46% |
| Bus D | 35–65 m | 40 | 0,22% | 0,86% | 0,06% | 0,14% |
| Bus D | 65–100 m | 32 | 0,80% | 1,30% | 0,12% | 0,12% |
| Bus D | 100–150 m | 8 | 0,58% | 1,30% | 0,04% | 0,21% |
| Bus E | <35 m | 40 | 0,33% | 0,75% | 0,07% | 0,15% |
| Bus E | 35–65 m | 40 | 0,82% | 2,11% | 0,16% | 0,38% |
| Bus E | 65–100 m | 14 | 1,60% | 2,91% | 0,39% | 0,71% |

**Bacaan:**

- Box panjang (Truck 20 m, Bus 12,6 m) berhasil direkonstruksi; bukan masalah parameterisasi.
- **Panjang** adalah sumbu yang paling sensitif terhadap jarak; di >150 m galat bisa 18%, meskipun RMS reproyeksi tetap ~0,34 px. Ini anisotropi proyeksi, bukan kesalahan kalibrasi.
- **Lebar dan tinggi** tetap <0,5% bahkan di objek jauh.
- Bus D/E konsisten; Bus E sedikit lebih buruk karena resolusi 1280×720 dan jarak.

---

## 6. Yang bisa dan tidak bisa diklaim

**Bisa:**

- Kalibrasi SVLD trainval valid (5 scene, 0 objek >2 px).
- Model kamera dan parameterisasi box benar untuk Car, Bus, dan Truck panjang.
- Trainval menyediakan **700 Truck + 1.166 Bus** untuk stress-test detektor/keypoint/mask, dan untuk menguji penanganan kendaraan panjang.
- `val.txt` (1.621 gambar) adalah split validasi yang masuk akal; `test.txt` (2.237) tetap test set.

**Tidak bisa:**

- Mengklaim akurasi L/W/H dunia nyata dari `veh_size`; nilainya preset.
- Memakai MAPE kecil sebagai bukti pipeline mengukur kendaraan nyata.
- Mengklaim truk 20 m "terukur" — itu template.
- Menggantikan pengukuran lapangan atau container 20 ft Cawang yang punya GT fisik.

---

## 7. Rekomendasi

1. **Pakai trainval untuk stress-test**, bukan accuracy claim: 700 Truck dan 1.166 Bus cukup untuk menguji keypoint/mask pada kelas besar dan panjang.
2. **Fokus jarak**: panjang memburuk >100 m; untuk ODOL, batasi klaim panjang pada <65 m atau gunakan multi-frame.
3. **Jalankan full set bila perlu**: pilot ini 120 Truck + 174 Bus; full 700 + 1.166 bisa dijalankan dengan `--n 700`/`--n 1166` (perkiraan 10–20 menit).
4. **Validasi fisik tetap wajib**: container 20 ft Cawang 6,046 m vs 6,058 m adalah GT fisik yang lebih kuat daripada `veh_size` SVLD.
5. **Perbarui klaim** di `HASIL-VALIDASI-SVLD.md`: MAPE 0,36% adalah self-consistency, bukan akurasi.

---

## 8. Reproduksi

```powershell
# 1. Inventaris + kalibrasi per root
py scripts\parse_svld.py --root "SVLD-3D-TRAINVAL-SCENE-A-C\DATA2021" --out out\svld_trainval\ac
py scripts\parse_svld.py --root "SVLD-3D-TRAINVAL-SCENE-D\DATA2021"    --out out\svld_trainval\d
py scripts\parse_svld.py --root "SVLD-3D-TRAINVAL-SCENE-E\DATA2021"    --out out\svld_trainval\e

py scripts\svld_reproj_check.py --root "SVLD-3D-TRAINVAL-SCENE-A-C\DATA2021" --out out\svld_trainval\ac
py scripts\svld_reproj_check.py --root "SVLD-3D-TRAINVAL-SCENE-D\DATA2021"    --out out\svld_trainval\d
py scripts\svld_reproj_check.py --root "SVLD-3D-TRAINVAL-SCENE-E\DATA2021"    --out out\svld_trainval\e

# 2. Fit pilot (8 sudut GT, bukan detektor)
py scripts\svld_fit_dims.py --root "SVLD-3D-TRAINVAL-SCENE-A-C\DATA2021" `
  --out out\svld_trainval\fit_truck120 --n 120 --classes Truck --seed 42
py scripts\svld_fit_dims.py --root "SVLD-3D-TRAINVAL-SCENE-D\DATA2021" `
  --out out\svld_trainval\fit_bus_d120 --n 120 --classes Bus --seed 42
py scripts\svld_fit_dims.py --root "SVLD-3D-TRAINVAL-SCENE-E\DATA2021" `
  --out out\svld_trainval\fit_bus_e120 --n 120 --classes Bus --seed 42
```

Tabel di laporan ini:

- `inventory.csv` — isi per root.
- `calib_reproj.csv` — reproyeksi per calib.
- `fit_summary.csv` — ringkasan 3 run.
- `fit_distance.csv` — stratifikasi jarak.

---

## 9. Batas

- Pilot 294 objek, bukan full 1.866 objek truk/bus.
- `veh_size` preset; tidak ada GT fisik per kendaraan di SVLD.
- Fit memakai 8 sudut GT, bukan detektor; hasil tidak berlaku langsung untuk pipeline CCTV.
- D/E 1280×720; A-C 1920×1080.
- Lisensi SVLD tidak eksplisit di repo; data mentah tidak disertakan.
