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

## Hasil pokok

Dengan `w = 3,60 m`:

- Cawang dash fit: `f=1082,58`, `h=8,876`, RMS `1,101 px`.
- GeoCalib: `f=943–981` (run lama), `928–944` (run 26 Nov); 9–14% terlalu rendah, RMS fixed pose `3,1–4,7 px`.
- AnyCalib: `f=1100–1207` tergantung frame; frame TEMA mendekati Cawang
  (+1,6%, RMS 1,215), median2 +9,3%.
- VP-only: pitch/yaw `2,646°/0,610°`; fixed pose RMS `1,333 px`, cukup untuk
  inisialisasi tetapi bukan pengganti fitting dash.

Lihat `reports/calib-compare/README.md` untuk tabel lengkap dan batasan.
