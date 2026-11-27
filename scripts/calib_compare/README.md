# Uji Banding Kalibrasi: GeoCalib / AnyCalib / VP

Skrip ini menghasilkan perbandingan `f`, pitch, yaw, dan tinggi kamera untuk
Cawang dengan anchor lebar lajur `w = 3,60 m`. Hasil lengkap ada di
`reports/calib-compare/`.

## Environment

Buat satu environment CPU di temp, lalu clone kedua repo:

```powershell
$work = "C:\Users\omega\AppData\Local\Temp\opencode\carom-calib"
New-Item -ItemType Directory -Force $work | Out-Null
Set-Location $work
git clone --depth 1 https://github.com/cvg/GeoCalib.git
git clone --depth 1 https://github.com/javrtg/AnyCalib.git

$envDir = "$work\env"
uv venv $envDir --python 3.11
uv pip install --python "$envDir\Scripts\python.exe" `
  torch torchvision --index-url https://download.pytorch.org/whl/cpu
uv pip install --python "$envDir\Scripts\python.exe" opencv-python kornia matplotlib
uv pip install --python "$envDir\Scripts\python.exe" -e C:\Users\omega\AppData\Local\Temp\opencode\carom-calib\GeoCalib --no-deps
uv pip install --python "$envDir\Scripts\python.exe" -e C:\Users\omega\AppData\Local\Temp\opencode\carom-calib\AnyCalib --no-deps
```

Bobot GeoCalib/AnyCalib diunduh otomatis saat pertama kali dijalankan.

## Urutan pakai

Untuk mereproduksi seluruh tabel (semua frame, GeoCalib multi-frame, AnyCalib
beberapa model, fitting, dan summary), dari root repo:

```powershell
pwsh scripts\calib_compare\run_all.ps1
```

Atau jalankan manual:

```powershell
$py = "C:\Users\omega\AppData\Local\Temp\opencode\carom-calib\env\Scripts\python.exe"

& $py scripts\calib_compare\run_geocalib.py `
  frames\median2.png --out out\calib-compare\geocalib_median2.json

& $py scripts\calib_compare\run_anycalib.py `
  frames\median2.png --model-id anycalib_pinhole --cam-id simple_pinhole `
  --out out\calib-compare\anycalib_simple_pinhole.json

node scripts\calib_compare\fit_compare.mjs
& $py scripts\calib_compare\make_summary.py
```

`fit_compare.mjs` membaca `frames/dashes2.json`, `frames/vp.json`, dan semua
JSON metode di `out/calib-compare/`, lalu menulis `out/calib-compare/fits.json`.

### Video LearnPinhole

Untuk klip `D:\Kerjaan\LearnPinhole\frontend\public\videos\clip-test-pengukuran.mp4`
(480×360), ekstrak 8 frame lalu jalankan:

```powershell
& $py scripts\calib_compare\run_lane_vp.py `
  out\learnpinhole-video\frames `
  --backend D:\Kerjaan\LearnPinhole\backend `
  --out out\learnpinhole-video\lane_vp.json

& $py scripts\calib_compare\run_geocalib_multi.py `
  out\learnpinhole-video\frames `
  --out out\learnpinhole-video\geocalib_multi.json

& $py scripts\calib_compare\run_anycalib_batch.py `
  out\learnpinhole-video\frames --cam-id simple_pinhole `
  --out out\learnpinhole-video\anycalib_simple.json
```

Hasil dan analisis ada di `reports/learnpinhole-video/README.md`.

## Frame baru / satu frame

`fit_compare_frame.mjs` membandingkan satu frame Cawang tanpa mengubah baseline
`frames/dashes2.json` dan `frames/vp.json`. Skrip memilih 3 dash per lajur
berdasarkan posisi `yNear` yang diharapkan, lalu menghitung dash fit, VP-only,
GeoCalib, dan GeoCalib+VP.

```powershell
node scripts\calib_compare\fit_compare_frame.mjs `
  --frame t350 `
  --dashes out\calib-compare\newframe\dashes_median_t350.json `
  --vp out\calib-compare\newframe\vp_median2_backup.json `
  --geo out\calib-compare\newframe\geocalib_median_t350.json `
  --out out\calib-compare\newframe\fits_median_t350_globalvp
```

Hasil 26 November 2026 (dua median temporal lokal baru): GeoCalib `f=928,50/944,10`
vs dash `1082,43/1082,03` (−14,2%/−12,8%); GeoCalib+VP RMS `4,674/4,285 px`;
VP-only RMS `1,323/1,374 px`. Detail: `reports/calib-compare/newframe-2026-11-26.md`.

## Dash fit dengan garis solid

`fit_dash_line.mjs` bisa menambahkan satu garis solid sebagai batas kedua. Ini
memutus degenerasi `f` pada kamera yang hanya punya satu garis putus-putus.
Garis solid diasumsikan sejajar garis dash dan berjarak `--solid-offset` kali
lebar lajur (`-1` = satu lajur di kanan garis dash).

Deteksi garis solid dari warna:

```powershell
$py = "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe"

& $py scripts\calib_compare\detect_solid_line.py `
  videos\frames\belmera_tm30_001.png `
  --color yellow --roi 450,250,640,720 --vmin 300 --vmax 715 `
  --out videos\frames\belmera_solid_yellow.json `
  --overlay videos\frames\belmera_solid_yellow_overlay.png
```

Fit dash + solid, dengan cek identifiabilitas:

```powershell
node scripts\calib_compare\fit_dash_line.mjs `
  --frame belmera_solid `
  --dashes videos\frames\belmera_sel.json `
  --width 1280 --height 720 `
  --period 13 --dash-length 5 --lane-width 3.6 `
  --solid videos\frames\belmera_solid_yellow.json --solid-offset -1 `
  --out videos\frames\belmera_solid_fit `
  --fixed-f 989.113 --scan-f 700:950:10
```

Keluaran: `*.csv`, `*.json`, dan `*_scan.csv`. JSON memuat `covariance`
(sigma parameter dari Jacobian), `fixed_f`, dan `scan_f`.

Hasil 27 November 2026:

- BELMERA dash-only: `f=1101,09`, RMS `0,320 px`; fixed `f=989,11` tetap
  `0,320 px` — **degenerate**.
- BELMERA dash + solid (`w=3,6 m`, period 13 m/dash 5 m): `f=811,55`,
  pitch `15,551°`, yaw `−0,106°`, `h=10,438 m`, RMS `0,439 px`;
  fixed `f=989,11` → RMS `1,674 px`; fixed `f=1101,09` → RMS `2,469 px`.
- Scan minimum ~810. Sigma statistik `8,76 px` (`1,08%`), tetapi `w=3,0→985,3`,
  `3,3→890,8`, `3,6→811,6`, `3,9→744,1`; error `w` jauh lebih besar.
- BORR: solid memutus degenerasi secara prinsip, tetapi jalan melengkung
  (`u` dash 324→494); model garis lurus tidak valid.

Detail: `reports/cctv-solid-line-2026-11-27/README.md`.

## Median VP + anchor `f` Cawang

`cawang_median_vp_anchor.py` mendeteksi VP pada 8 median temporal Cawang,
mengambil median VP, mengoreksi `f` GeoCalib dengan scale per kamera, lalu
membandingkan `f`/pose dengan dash fit. Anchor bisa dash (oracle) atau 50/50
(buta).

```powershell
$py = "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe"
& $py scripts\calib_compare\cawang_median_vp_anchor.py --out out\calib-compare\fusion
```

RMS fixed pose untuk frame ber-anotasi dash (median2/t350/t500):

```powershell
node scripts\calib_compare\fit_compare_frame.mjs `
  --frame median2_dash `
  --dashes frames\dashes2.json `
  --vp out\calib-compare\fusion\cawang_median_vp.json `
  --geo out\calib-compare\fusion\anchor_dash_median2.json `
  --out out\calib-compare\fusion\fits_anchor_dash_median2
```

Hasil 27 November 2026: median VP `(651,48, 312,41)`; pose `2,518°/0,607°` vs
dash `2,466°/0,287°` (Δ `+0,052°/+0,320°`). `f` error median **0,88%** (anchor
dash) dan **1,44%** (anchor 50/50 buta); 8/8 lulus f<5%. RMS fixed pose
**1,374/1,443/1,398 px** vs dash **1,101/1,131/1,174 px**. GeoCalib mentah
error `f` 12,9% tetapi masih lulus gate pose 2° karena pitch Cawang rendah;
gunakan gate `f` dan RMS, bukan pose saja. Detail:
`../reports/calib-compare/median-vp-anchor-2026-11-27.md`.

## Fusi `f` GeoCalib + AnyCalib

`fuse_focal.py` menggabungkan `f` dari GeoCalib dan AnyCalib, memakai dash fit
hanya sebagai referensi evaluasi. Skrip menghitung rata-rata 50/50, geometrik,
harmonik, bobot konveks (in-sample + leave-one-out), koreksi skala, dan agregat
kamera statis.

Environment yang dipakai untuk uji 26 November 2026:
`C:\Users\omega\AppData\Local\Temp\opencode\geoenv` (GeoCalib + AnyCalib di
env yang sama). AnyCalib dipasang dengan:

```powershell
$py = "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe"
uv pip install --python $py -e C:\Users\omega\AppData\Local\Temp\opencode\AnyCalib --no-deps
uv pip install --python $py scipy pandas tqdm
```

Urutan:

```powershell
$py = "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe"

& $py scripts\calib_compare\run_anycalib_batch.py `
  out\calib-compare\fusion\frames_all8 `
  --model-id anycalib_pinhole --cam-id simple_pinhole `
  --out out\calib-compare\fusion\anycalib_all8.json

& $py scripts\calib_compare\run_geocalib_multi.py `
  out\calib-compare\fusion\frames_all8 `
  --out out\calib-compare\fusion\geocalib_multi_all8.json

& $py scripts\calib_compare\fuse_focal.py `
  --geo-dir out\calib-compare\fusion `
  --any out\calib-compare\fusion\anycalib_all8.json `
  --any-gen out\calib-compare\fusion\anycalib_gen_all8.json `
  --geo-multi out\calib-compare\fusion\geocalib_multi_all8.json `
  --ref 1082.35 `
  --out-dir out\calib-compare\fusion\all8
```

Hasil: GeoCalib `−13,1%`, AnyCalib `+11,4%`, rata-rata 50/50 **MAE 1,58%**,
maks 3,92%, **8/8 lulus 5%**. Detail dan batas: `reports/calib-compare/fusion-2026-11-26.md`.

## Hasil pokok

Dengan `w = 3,60 m`:

- Cawang dash fit: `f=1082,58`, `h=8,876`, RMS `1,101 px`.
- GeoCalib: `f=943–981` (run lama), `928–944` (run 26 Nov); 9–14% terlalu rendah, RMS fixed pose `3,1–4,7 px`.
- AnyCalib: `f=1100–1207` tergantung frame; frame TEMA mendekati Cawang
  (+1,6%, RMS 1,215), median2 +9,3%.
- VP-only: pitch/yaw `2,646°/0,610°`; fixed pose RMS `1,333 px`, cukup untuk
  inisialisasi tetapi bukan pengganti fitting dash.
- Fusi 50/50 GeoCalib+AnyCalib (8 median temporal, 26 Nov): `MAE 1,58%`,
  maks `3,92%`, `8/8` lulus 5%; bobot optimal `0,470/0,530`, LOO `1,80%`.
  Ini spesifik Cawang; lihat `reports/calib-compare/fusion-2026-11-26.md`.

Lihat `reports/calib-compare/README.md` untuk tabel lengkap dan batasan.
