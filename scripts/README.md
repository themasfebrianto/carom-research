# Skrip Validasi

Semua skrip di folder ini adalah alat Fase 1–2, bukan pipeline produksi.

## Environment

| Kebutuhan | Env |
|---|---|
| GeoCalib, torch CPU | `C:\Users\omega\AppData\Local\Temp\opencode\geoenv` |
| parsing, metrik, plot, fitting | `C:\Users\omega\AppData\Local\Temp\opencode\cctv-eval` |
| YOLO-seg / YOLO-pose | `C:\Users\omega\AppData\Local\Temp\opencode\vehicle-kp` |
| Grounding DINO + SAM 2 | `C:\Users\omega\AppData\Local\Temp\opencode\grounded-sam2` |
| ffmpeg | sistem |

Cara membuat ulang environment dan mengunduh bobot: `reports/external-setup.md`.

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
py scripts\i24_parse.py `
  --hg I24-3D\data\hg\scene1_hg.json `
  --out out\i24\calib_gt_scene1.json
```

Struktur nyata file adalah `{"EB": {kamera: ...}, "WB": {kamera: ...}}`; parser menangani bentuk itu dan bentuk flat. Keluaran default berisi `ground_rms_px`, `ground_max_px`, `horizon_line`, `curve`, `vps`, dan `P_z_scale` per arah/kamera.

**Penting:** `P[:,2]` adalah kolom VP vertikal dengan skala arbitrer (`* 0.01`) yang disesuaikan `scale_Z()`. RQ(`P`) **bukan** intrinsik fisik; karena itu `fx/fy/...` tidak ditulis secara default. Untuk diagnostik lama, tambah `--legacy-rq` (hasilnya diberi `rq_warning`). Detail: `../reports/i24-3d-kalibrasi/README.md`.

### 3. Ekstrak frame

```powershell
py scripts\i24_frames.py I24-3D\video\scene1 `
  --out out\i24\frames\scene1 --times 10 30 50 `
  --scale 1920:1080
```

Nama file mengikuti prefix folder; kamera `p1c1` akan terbaca oleh evaluator. Gunakan `--scale 1920:1080` agar `f` GeoCalib sebanding dengan `P`/`H` I24-3D yang ber-referensi 1080p; tanpa `--scale`, frame keluar 4K dan `f` harus dikali 2.

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
  --direction EB `
  --out out\i24\calib_eval_scene1.csv
```

Keluaran: CSV per frame + ringkasan median/p90/max dan status gerbang. Karena `hg` tidak memberi `f` fisik, semua baris akan berstatus **`NO_F_GT`**; `--legacy-rq` hanya menaruh blok diagnostik di `legacy_rq`, bukan `fx` top-level. Jangan menafsirkan `NO_F_GT` sebagai lulus/gagal; itu berarti GT `f` tidak tersedia.

Untuk uji pilot I24-3D yang sudah dijalankan (GT pitch dari horizon `H`, GeoCalib single + multi-frame):

```powershell
py scripts\i24_pilot_summary.py --out out\i24\i24_pilot_summary.csv
```

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
# test set: Car/Bus
py scripts\svld_fit_dims.py `
  --root data\svld\TESTDATA2021\TESTDATA2021 `
  --out out\svld --n 50 --seed 42

# trainval: truk dan bus
py scripts\svld_fit_dims.py `
  --root "SVLD-3D-TRAINVAL-SCENE-A-C\DATA2021" `
  --out out\svld_trainval\fit_truck120 --n 120 --classes Truck --seed 42
py scripts\svld_fit_dims.py `
  --root "SVLD-3D-TRAINVAL-SCENE-D\DATA2021" `
  --out out\svld_trainval\fit_bus_d120 --n 120 --classes Bus --seed 42
```

Keluaran: `fit_dims.csv`, `fit_dims_summary.json`.
Input: 8 sudut 2D GT (`vertex2d`) + kalibrasi XML; fit 6 parameter (X, Y, yaw, L, W, H).
`--classes` membatasi/menambah kelas (default semua yang ada: Car, Bus, Truck); stratifikasi jarak memakai bin 0–35, 35–65, 65–2000 m.

Hasil test 50 objek: MAPE 0,36%, RMS 0,35 px. Trainval pilot (120 Truck + 174 Bus): MAPE median 0,20–0,32%, RMS 0,34–0,39 px; panjang memburuk >100 m. **Peringatan:** `veh_size` SVLD adalah preset, jadi ini uji self-consistency geometri, bukan akurasi fisik. Detail: `../reports/svld-trainval/README.md`.

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

### 13. Segmentasi kontainer-only

Grounded SAM 2 dengan box prompt yang hanya mencakup kontainer. Prompt teks saja (`"shipping container."`) mendeteksi box yang ikut mencakup kabin; karena itu box prompt manual dipakai bila kabin harus dipisahkan.

```powershell
& "C:\Users\omega\AppData\Local\Temp\opencode\grounded-sam2\Scripts\python.exe" `
  scripts\grounded_sam2_container.py `
  --image out\timepass\t247.jpg --box "255,475,405,645" --out out\timepass\gsam2_20ft
```

Keluaran: `container_mask_0.npy`, `container_mask_0.png`, `grounded_sam2_container.jpg`.
Mask 20 ft TEMA: 21.907 px; 0 piksel hijau (kabin) di dalam mask.

### 14. Fit 3D box ke kontainer

Tinggi kontainer dipaku ke standar ISO: 2,591 m (standar) atau 2,896 m (high cube).

```powershell
& "C:\Users\omega\AppData\Local\Temp\opencode\cctv-eval\Scripts\python.exe" `
  scripts\cawang_container_fit.py `
  --image out\timepass\t247.jpg `
  --mask out\timepass\gsam2_20ft\container_mask_0.npy `
  --box "230,450,430,680" --height 2.591 --out out\timepass\container20
```

Keluaran: `container_fit.json` dan `container_fit_overlay.jpg`.
Hasil 20 ft TEMA: $L=6{,}046$ m vs 6,058 m (−0,2%), $W=2{,}437$ m, IoU 0,972.

## Uji banding kalibrasi

Skrip di `scripts/calib_compare/` membandingkan GeoCalib, AnyCalib, VP, dan Cawang dengan anchor `w = 3,60 m`. Hasil dan batasannya ada di `reports/calib-compare/README.md`.

```powershell
python scripts\calib_compare\run_geocalib.py `
  frames\median2.png --out out\calib-compare\geocalib_median2.json
python scripts\calib_compare\run_anycalib.py `
  frames\median2.png --cam-id simple_pinhole `
  --out out\calib-compare\anycalib_simple_pinhole.json
node scripts\calib_compare\fit_compare.mjs
python scripts\calib_compare\make_summary.py
```

## Catatan teknis

- **`P` I24-3D ditulis 3×4** di file (README dataset menulis `[4,3]`); parser menerima keduanya.
- `P` dibangun dari `H_inv` + VP vertikal, bukan kalibrasi lab. Kolom-Z-nya diskalakan `* 0.01` lalu `scale_Z()`. **RQ(`P`) bukan intrinsik fisik**; jangan pakai `fx`/`height`/`pitch` dari RQ sebagai GT. Hasil data nyata: `f` EB vs WB berbeda median 7,1%, p90 24,6%.
- Ground RMS `H_inv` → `corr_pts` median 3,89 px, maks 9,36 px; 0/102 <1 px. `H` adalah model tracking di frame jalan yang diluruskan (`curve`), bukan homografi fotogrametri.
- Satuan I24-3D adalah kaki; konversi 0,3048 ke meter.
- Kamera I24-3D berada di 28–45 m dan menghadap ke bawah 17–75°; **bukan side-view**. GeoCalib meleset 9–65° pada data ini.
- **`veh_size` SVLD adalah preset, bukan pengukuran**: trainval 1.164/1.166 Bus `L=12,60 m`, 184 Truck `L=20,00 m`; test Bus `12,00/9,46 m`. Fit 8 sudut adalah self-consistency geometri, bukan akurasi fisik. Detail: `../reports/svld-trainval/README.md`.
- Jika frame 1080p dipakai, skala `f`, `cx`, `cy` dengan rasio lebar terhadap resolusi acuan `P`.
- GeoCalib memakai pitch negatif untuk menunduk; evaluator membandingkan magnitudo absolut.
- File JSON dari PowerShell bisa ber-BOM; skrip membaca dengan `utf-8-sig`.
- Jangan menjalankan GeoCalib dan parser dari env yang sama jika dependensi bentrok; keduanya dipisah.
