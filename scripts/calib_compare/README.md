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

## Hasil pokok

Dengan `w = 3,60 m`:

- Cawang dash fit: `f=1082,58`, `h=8,876`, RMS `1,101 px`.
- GeoCalib: `f=943–981` (9–13% terlalu rendah), RMS fixed pose `3,1–4,4 px`.
- AnyCalib: `f=1100–1207` tergantung frame; frame TEMA mendekati Cawang
  (+1,6%, RMS 1,215), median2 +9,3%.
- VP-only: pitch/yaw `2,646°/0,610°`; fixed pose RMS `1,333 px`, cukup untuk
  inisialisasi tetapi bukan pengganti fitting dash.

Lihat `reports/calib-compare/README.md` untuk tabel lengkap dan batasan.
