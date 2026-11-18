# Skrip Validasi

Semua skrip di folder ini adalah alat Fase 1–2, bukan pipeline produksi.

## Environment

| Kebutuhan | Env |
|---|---|
| GeoCalib, torch CPU | `C:\Users\omega\AppData\Local\Temp\opencode\geoenv` |
| parsing, metrik, plot | `C:\Users\omega\AppData\Local\Temp\opencode\cctv-eval` |
| ffmpeg | sistem |

## Urutan pakai

### 1. Verifikasi parser tanpa data

```powershell
& "C:\Users\omega\AppData\Local\Temp\opencode\cctv-eval\Scripts\python.exe" `
  scripts\i24_parse.py --self-test
```

Harus keluar:

```text
3x4: OK  f=1000.000  pitch=10.000  h=8.000
4x3: OK  f=1000.000  pitch=10.000  h=8.000
```

### 2. Parse kalibrasi I24-3D

```powershell
& "C:\Users\omega\AppData\Local\Temp\opencode\cctv-eval\Scripts\python.exe" `
  scripts\i24_parse.py `
  --hg data\i24\hg\scene1_hg.json `
  --out out\i24\calib_gt_scene1.json
```

Keluaran berisi `fx`, `fy`, `cx`, `cy`, `height_m`, `pitch_deg`, `roll_deg`, `yaw_deg`, dan `roundtrip_rms_px` jika `space_pts`/`corr_pts` ada.

### 3. Ekstrak frame

```powershell
py scripts\i24_frames.py data\i24\video\scene1 `
  --out out\i24\frames\scene1 --times 10 30 50
```

Nama file mengikuti prefix folder; kamera `p1c1` akan terbaca oleh evaluator.

### 4. Jalankan GeoCalib

```powershell
$GEO="C:\Users\omega\AppData\Local\Temp\opencode\geoenv"
& "$GEO\Scripts\python.exe" scripts\geocalib_batch.py `
  out\i24\frames\scene1\*.png `
  --out out\i24\geocalib_scene1.json
```

Untuk batch besar, berikan daftar file eksplisit; wildcard PowerShell bisa terlalu panjang.

### 5. Bandingkan dengan ground truth

```powershell
py scripts\eval_i24_calib.py `
  --geo out\i24\geocalib_scene1.json `
  --gt out\i24\calib_gt_scene1.json `
  --out out\i24\calib_eval_scene1.csv
```

Keluaran: CSV per frame + ringkasan median/p90/max dan status gerbang.

### 6. Inventaris SVLD-3D

```powershell
py scripts\parse_svld.py `
  --root data\svld\TESTDATA2021\TESTDATA2021 `
  --out out\svld
```

Keluaran: `objects.csv` (satu baris per objek) + `summary.json`.
Test set: 2.237 citra, 8.142 objek, 7.396 Car / 745 Bus / **1 Truck**. Jangan pakai SVLD-3D untuk klaim truk; gunakan I24-3D atau RoScenes.

Kalibrasi SVLD: `f` (px), `fi` = pitch (rad), `theta` = yaw (rad), `h` (mm). Jangan menukar `fi` dan `theta`.

### 7. Verifikasi kalibrasi SVLD

```powershell
py scripts\svld_reproj_check.py `
  --root data\svld\TESTDATA2021\TESTDATA2021 `
  --out out\svld
```

Keluaran: `reproj_objects.csv`, `reproj_summary.json`.
Hasil: 8.142 objek, median RMS 0,74 px, maksimum 1,08 px, 0 objek >2 px.
Kalibrasi SVLD konsisten; GeoCalib hanya lulus 1/5 scene, jadi jangan pakai GeoCalib untuk SVLD.

### 8. Fit dimensi SVLD

```powershell
py scripts\svld_fit_dims.py `
  --root data\svld\TESTDATA2021\TESTDATA2021 `
  --out out\svld --n 50 --seed 42
```

Keluaran: `fit_dims.csv`, `fit_dims_summary.json`.
Input: 8 sudut 2D GT (`vertex2d`) + kalibrasi XML; fit 6 parameter (X, Y, yaw, L, W, H).
Hasil 50 objek: MAPE 0,36%, RMS 0,35 px. Ini uji geometri, bukan detektor.

### 9. Analisis sensitivitas noise

```powershell
py scripts\svld_sensitivity.py `
  --root data\svld\TESTDATA2021\TESTDATA2021 `
  --out out\svld --n 50 --reps 20 --sigmas 0 0.5 1 2 3 5
```

Keluaran: `sensitivity.csv`, `sensitivity_summary.json`.
Hasil: 3 px → MAPE 2,79%, 1,7% gagal; 5 px → 63,2% gagal. Target keypoint ≤3 px.

### 10. Subset sudut

```powershell
py scripts\svld_subsets.py `
  --root data\svld\TESTDATA2021\TESTDATA2021 `
  --out out\svld --n 50 --seed 42
```

Keluaran: `subsets.csv`, `subsets_summary.json`.
Hasil: 4 kontak tanah + 1 atap (5 titik) → MAPE 0,48%, 0 gagal; 8 titik → 0,36%.

### 11. Detectability keypoint SVLD

```powershell
& "C:\Users\omega\AppData\Local\Temp\opencode\vehicle-kp\Scripts\python.exe" `
  scripts\svld_kp_detectability.py `
  --root data\svld\TESTDATA2021\TESTDATA2021 `
  --weights out\keypoint\hf\weights.pt --out out\keypoint
```

Hasil 20 citra: match 56,9%; 5/5 di antara semua GT 36,1% (Car 44,1%, Bus 0%).
Model `vehicle-keypoints` tidak siap untuk bus; zero-shot tidak cukup.

### 12. Mask-based fitting

```powershell
& "C:\Users\omega\AppData\Local\Temp\opencode\vehicle-kp\Scripts\python.exe" `
  scripts\svld_mask_fit.py `
  --root data\svld\TESTDATA2021\TESTDATA2021 `
  --weights out\keypoint\yolo11n-seg.pt --out out\keypoint --n 20 --imgsz 1280
```

Hasil 21 objek: MAPE 12,19%; W 7,11%, H 7,55%, L 21,92%; mask IoU 0,796.
W/H layak screening; panjang belum. Mask body tidak memuat kontak ban.

## Catatan teknis

- `P` I24-3D ditulis `[4,3]`; parser menerima 3×4 dan 4×3.
- `P` dibangun dari `H_inv` + VP vertikal, bukan kalibrasi lab. Uji round-trip `P` → `corr_pts`; jika RMS >1 px, jangan pakai RQ. Gunakan `vps`/`H` sebagai fallback.
- Satuan I24-3D adalah kaki; konversi 0,3048 ke meter.
- Jika frame 1080p dipakai, skala `f`, `cx`, `cy` dengan rasio lebar terhadap resolusi acuan `P`.
- GeoCalib memakai pitch negatif untuk menunduk; evaluator membandingkan magnitudo absolut.
- File JSON dari PowerShell bisa ber-BOM; skrip membaca dengan `utf-8-sig`.
- Jangan menjalankan GeoCalib dan parser dari env yang sama jika dependensi bentrok; keduanya dipisah.
