# Fase 0 — Environment

Diperbarui: 18 November 2026

## Mesin

| Item | Nilai |
|---|---|
| OS | Windows (win32) |
| GPU | **tidak tersedia** (`nvidia-smi` tidak ada; torch CUDA false) |
| CPU PyTorch | 2.15.0+cpu |
| ffmpeg | 8.1.1-full_build |
| 7-Zip | 26.06 (dipasang untuk ekstrak RAR SVLD-3D) |
| Node.js | v26.13.0 |
| Python | 3.11.9 (`py`) |
| uv | 0.12.3 |
| Disk C | 17,1 GB bebas (dipakai untuk venv) |
| Disk D | 229,9 GB bebas (dipakai untuk data/out) |

## Environment

| Env | Path | Isi | Status |
|---|---|---|---|
| `geoenv` | `C:\Users\omega\AppData\Local\Temp\opencode\geoenv` | torch CPU, torchvision, geocalib (editable), opencv, kornia | **OK** |
| `cctv-eval` | `C:\Users\omega\AppData\Local\Temp\opencode\cctv-eval` | numpy, scipy, pandas, opencv, matplotlib, gdown | **OK** |
| `openpifpaf` | belum dibuat | OpenPifPaf (AGPL, riset) | pending |
| `moge` | belum dibuat | MoGe (MIT) | pending |

## Konsekuensi GPU

- GeoCalib pada ~150 frame CPU masih layak (inferensi per citra orde detik).
- OpenPifPaf, Keypoint R-CNN, dan GSNet fitting akan lambat di CPU.
- MoGe-2 pada CPU hanya untuk 2–4 citra, bukan batch besar.
- Fase 4 (keypoint) memerlukan subset kecil atau cloud GPU sekali pakai.

## Verifikasi

```powershell
$GEO="C:\Users\omega\AppData\Local\Temp\opencode\geoenv"
& "$GEO\Scripts\python.exe" -c "import torch, geocalib; print(torch.__version__)"

$EVAL="C:\Users\omega\AppData\Local\Temp\opencode\cctv-eval"
& "$EVAL\Scripts\python.exe" scripts\i24_parse.py --self-test
```

Hasil self-test parser:

```text
3x4: OK  f=1000.000  pitch=10.000  h=8.000
4x3: OK  f=1000.000  pitch=10.000  h=8.000
```

## Data yang sudah siap

| Data | Lokasi | Ukuran | Status |
|---|---|---|---|
| SVLD-3D test | `data/svld/TESTDATA2021/TESTDATA2021` | 2,56 GB (7,18 GB termasuk arsip) | 2.237 citra, 8.142 objek |
| I24-3D | belum | — | akun terdaftar, menunggu persetujuan |

Inventaris SVLD: `out/svld/summary.json`, `out/svld/objects.csv`.

## Update 18 November 2026 (sore)

Setelah uji keypoint dan container-only, environment bertambah:

| Env | Path | Isi | Status |
|---|---|---|---|
| `vehicle-kp` | `C:\Users\omega\AppData\Local\Temp\opencode\vehicle-kp` | ultralytics 8.4.215, torch 2.15.0+cpu, opencv 5.1.0 | **OK** |
| `grounded-sam2` | `C:\Users\omega\AppData\Local\Temp\opencode\grounded-sam2` | transformers 5.23.0, torch 2.15.0+cpu, opencv 5.1.0 | **OK** |
| `openpifpaf` | — | gagal build di Windows (MSVC, torch 1.13.1) | **gagal** |
| `moge` | — | belum dipasang | pending |

- OpenPifPaf diganti `vehicle-keypoints` (YOLO26-pose, MIT).
- Bobot model tidak disertakan di repo; cara mengunduh ada di `external-setup.md`.
- Grounded SAM 2 memakai `IDEA-Research/grounding-dino-tiny` + `facebook/sam2.1-hiera-tiny`.

## Catatan

- `P` I24-3D ditulis `[4,3]` di README; parser menerima 3×4 dan 4×3.
- Satuan I24-3D adalah kaki; konversi 0,3048 ke meter.
- Jika frame 1080p dipakai, skala $f,c_x,c_y$ dengan rasio lebar terhadap resolusi acuan `P`.
