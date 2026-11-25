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

### 15. Anchor container Cawang

```powershell
py scripts\cawang_container_anchor.py --out out\timepass\anchor
```

Menggabungkan hasil 20 ft TEMA (SAM2) dan 40 ft SINKOR (GrabCut). Hasil: 20 ft **6,046 m (−0,2%)**; 40 ft GrabCut **12,45 m (+2,1% vs 40 ft)** tetapi W bias dan tipe 40/45 ft belum pasti. 20 ft memvalidasi skala 3,6 m **di Cawang**; lokasi lain tetap perlu ukur. Detail: `../reports/cawang-container-anchor/README.md`.

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

## GeoCalib vs GT SVLD

Sampling 10 citra per scene per split (test + trainval) dan evaluasi f/pitch terhadap XML:

```powershell
py scripts\svld_geocalib_sample.py --per-scene 10 --out out\svld_geocalib

$GEO = "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe"
$files = Import-Csv out\svld_geocalib\manifest.csv | ForEach-Object { $_.source }
& $GEO scripts\geocalib_batch.py @files --out out\svld_geocalib\geocalib_single.json

foreach ($s in '0cam','1cam','session0_centre','session0_right','session6_right') {
  & $GEO scripts\calib_compare\run_geocalib_multi.py `
    "out\svld_geocalib\frames_multi\$s" `
    --out "out\svld_geocalib\geocalib_multi_$s.json"
}

py scripts\eval_svld_geocalib.py `
  --manifest out\svld_geocalib\manifest.csv `
  --single out\svld_geocalib\geocalib_single.json `
  --multi-dir out\svld_geocalib --out out\svld_geocalib
```

Hasil: **20/100 citra lulus** (hanya `session0_centre`); median Δf 14,9%, Δpitch 3,03°; multi-frame 1/5. Yaw dan `h` tidak diuji karena GeoCalib tidak mengestimasi keduanya. Detail: `../reports/svld-geocalib/README.md`.

## VP dan lebar lajur SVLD

```powershell
# VP dengan f GT (batas atas) dan f GeoCalib (realistis)
py scripts\svld_vp_eval.py --source gt  --out out\svld_vp
py scripts\svld_vp_eval.py --source geo --out out\svld_vp

# Lebar lajur dari posisi lateral kendaraan 3D
py scripts\svld_lane_width.py --out out\svld_vp --min-width-m 2.5

# Median VP per scene (kamera statis)
py scripts\svld_vp_scene_median.py --out out\svld_vp
```

Hasil: VP + `f` GT **95/100** lulus pitch/yaw <2° (median 0,20°/0,05°); median VP per scene **5/5** dengan f GT; VP + `f` GeoCalib **47/100** (2,46°/1,12°); GeoCalib saja 20/100. VP memberi **yaw**; `f` tetap bottleneck. Lebar lajur data-driven **2,7–3,56 m**, jadi 3,6 m bukan universal. Detail: `../reports/svld-vp/README.md`.

## AnyCalib dan fusion f SVLD

```powershell
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

# Prototipe f/h dari geometri lajur + lebar lajur
py scripts\svld_lane_fit.py --scene session0_right --out out\svld_lane_fit_right
py scripts\svld_lane_fit.py --scene session6_right --out out\svld_lane_fit_s6

# Dua VP ortogonal: VP jalan + VP vertikal otomatis
py scripts\svld_vertical_vp.py --scene 0cam --out out\svld_vertical_vp_0cam
py scripts\svld_vertical_vp.py --scene 1cam --out out\svld_vertical_vp_1cam

# GlobustVP (cvxpy + SCS)
py scripts\svld_globustvp.py --scene 0cam --limit 3 --k-mode gt `
  --min-length 60 --max-lines 40 --line-filter all --solver SCS --eps 1e-3 `
  --out out\svld_globustvp_0cam_all

# PerspectiveFields (CVPR 2023)
py scripts\svld_perspective_fields.py --limit 100 --batch 4 --out out\svld_perspective_fields

# Cek VP dari box kendaraan SVLD
py scripts\svld_vehicle_vp_check.py --limit 0

# 3D box PnP dari box GT SVLD
py scripts\svld_box_calib.py --manifest out\svld_geocalib\manifest.csv --out out\svld_box_calib
D:\Kerjaan\yolo3Dbbox\.venv\Scripts\python.exe scripts\svld_yolo3d_dims.py --n 20

# Tool reusable: 8 sudut 2D + 8 titik 3D world-space -> f/pitch/yaw/h
py scripts\box_pnp_calib.py --input box.json --width 1280 --height 720 --out box_result.json
py scripts\svld_box_calib_sensitivity.py --trials 3 --out out\svld_box_calib
py scripts\svld_box_calib_scene.py --per-scene 30 --trials 5 --out out\svld_box_calib
```

Hasil: AnyCalib **6/100** (median Δf 18,2%), GeoCalib 20/100; fusion tidak mengalahkan GeoCalib. VP + Any **34/100**, VP + Geo **47/100**, VP + GT **95/100**. Lane fit identifiabel di sintetis, tetapi **0/45** nyata karena lane extraction/assignment. Vertical VP otomatis: 0cam **2/20** OK, 1cam 18/20 OK tetapi hanya **4/18** lulus; gravitasi GeoCalib + VP hanya `session0_centre`. GlobustVP: 0cam 2/3, 1cam 3/3, tetapi vertikal 24–35° / 0 inlier; tidak turnkey. Detail: `../reports/svld-calib-fusion/README.md`.

## Catatan teknis

- **`P` I24-3D ditulis 3×4** di file (README dataset menulis `[4,3]`); parser menerima keduanya.
- `P` dibangun dari `H_inv` + VP vertikal, bukan kalibrasi lab. Kolom-Z-nya diskalakan `* 0.01` lalu `scale_Z()`. **RQ(`P`) bukan intrinsik fisik**; jangan pakai `fx`/`height`/`pitch` dari RQ sebagai GT. Hasil data nyata: `f` EB vs WB berbeda median 7,1%, p90 24,6%.
- Ground RMS `H_inv` → `corr_pts` median 3,89 px, maks 9,36 px; 0/102 <1 px. `H` adalah model tracking di frame jalan yang diluruskan (`curve`), bukan homografi fotogrametri.
- Satuan I24-3D adalah kaki; konversi 0,3048 ke meter.
- Kamera I24-3D berada di 28–45 m dan menghadap ke bawah 17–75°; **bukan side-view**. GeoCalib meleset 9–65° pada data ini.
- **`veh_size` SVLD adalah preset, bukan pengukuran**: trainval 1.164/1.166 Bus `L=12,60 m`, 184 Truck `L=20,00 m`; test Bus `12,00/9,46 m`. Fit 8 sudut adalah self-consistency geometri, bukan akurasi fisik. Detail: `../reports/svld-trainval/README.md`.
- Jika frame 1080p dipakai, skala `f`, `cx`, `cy` dengan rasio lebar terhadap resolusi acuan `P`.
- GeoCalib memakai pitch negatif untuk menunduk; evaluator membandingkan magnitudo absolut.
- GeoCalib hanya mengestimasi `f`, pitch, dan roll; **yaw dan tinggi kamera tidak tersedia**, jadi jangan membandingkannya dengan GT SVLD. Roll SVLD juga tidak eksplisit.
- `vp_pose.pose_from_vp` memakai konvensi yang sama dengan model SVLD (`R = Rx(fi + π/2) Rz(theta)`), jadi pitch/yaw VP bisa dibandingkan langsung. VP hanya memberi **road-direction VP**; `f` harus dari sumber lain.
- **GeoCalib/AnyCalib bukan sumber f yang cukup** di SVLD: 20/100 dan 6/100. f harus dari kamera diketahui, dash fit + anchor, dua VP ortogonal, atau anotasi garis manual.
- Lane fit klasik (LSD/Hough) baru **0/45**; matematikanya identifiabel di sintetis, tetapi lane extraction/assignment adalah bottleneck. Detector lajur yang lebih baik atau anotasi manual diperlukan.
- Vertical VP otomatis (LSD + RANSAC) baru **0cam 2/20**, **1cam 4/18** lulus; sudut vs gravitasi 35–43°. Gravitasi GeoCalib hanya prior/consistency check, bukan sumber f. Perlu anotasi vertikal manual atau detektor Manhattan-world/NeurVPS.
- **GlobustVP** butuh MOSEK/GPU untuk performa paper; SCS CPU sering `optimal_inaccurate` dan memaksa 3 VP. Di SVLD, VP ketiga sering cross-product tanpa inlier; vertikal 24–35°. Bukan turnkey.
- **PerspectiveFields (CVPR 2023)** gagal di 4/5 scene SVLD: f rasio 0,33-0,95, VP vertikal 51-83 deg. Model punya prior vFoV ~30-33 deg dan tidak cocok untuk lensa tele 10-14 deg.
- **deep_vp (ICANN 2021)** adalah konsep vehicle-VP yang tepat, tetapi bobot pretrained ada di OneDrive login dan tidak ada mirror. Geometri VP dari box 50 px SVLD masih noise (median 1,7-20 deg).
- **3D box PnP** memakai 8 sudut box + dimensi: f 0,00-0,21% dengan box GT; sensitivitas 1 px + 3% dimensi + 0,3 m + 2 deg -> 1,86%. Butuh detektor 3D yang akurat; `yolo3Dbbox` lama meleset median H 20%, W 7%, L 15% (truk/bus lebih buruk).
- **Box lokal vs world-space**: `box_pnp_calib.py` memakai 8 titik 3D world-space dan akurat; `box_pnp_known_dims.py` hanya memakai dimensi + 8 sudut 2D dan **ambigu** (1cam/session0 bisa salah minimum). Detektor 3D harus memberi posisi/orientasi world-space, bukan hanya dimensi.
- **CenterLoc3D Colab**: notebook `notebooks/train_centerloc3d_colab.ipynb`; script `train_centerloc3d_colab.py` (AMP/checkpoint/resume), `make_centerloc3d_txt.py` (generate line, skip gambar hilang), `patch_centerloc3d.py` (NumPy 2/PyTorch 2). Smoke test CPU 1 iterasi sudah lolos; training penuh butuh GPU Colab.
- Lebar lajur SVLD dari marka dan dari posisi kendaraan berbeda hingga ~0,6 m; **jangan pakai 3,6 m sebagai GT**. Untuk skala absolut, ukur per lokasi.
- File JSON dari PowerShell bisa ber-BOM; skrip membaca dengan `utf-8-sig`.
- Jangan menjalankan GeoCalib dan parser dari env yang sama jika dependensi bentrok; keduanya dipisah.
