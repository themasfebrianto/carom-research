# Environment Eksternal

Dokumen ini mencatat cara membangun ulang environment yang dipakai untuk validasi. Environment, bobot model, dan dataset **tidak** disertakan di repo.

Contoh path memakai `$env:TEMP\opencode`. Ganti sesuai mesin. Semua perintah diuji di Windows dengan Python 3.11 dan CPU saja.

## Perangkat lunak dasar

| Kebutuhan | Versi yang dipakai |
|---|---|
| Windows | 10/11 |
| Python | 3.11.9 |
| `uv` | 0.12.3 |
| `ffmpeg` / `ffprobe` | 8.1.1-full_build |
| Node.js | 26.13.0 (untuk skrip `.mjs`) |
| GPU | tidak ada; semua inferensi CPU |

## Ringkasan environment

| Env | Dipakai untuk | Paket kunci |
|---|---|---|
| `geoenv` | GeoCalib | `torch 2.15.0+cpu`, `geocalib`, `opencv-python` |
| `cctv-eval` | parsing, metrik, fitting | `numpy`, `scipy`, `pandas`, `opencv-python`, `matplotlib`, `gdown` |
| `vehicle-kp` | YOLO-seg dan YOLO-pose | `ultralytics 8.4.215`, `torch 2.15.0+cpu` |
| `grounded-sam2` | Grounding DINO + SAM 2 | `transformers 5.23.0`, `torch 2.15.0+cpu` |
| `openpifpaf` | **tidak dipakai** | gagal build di Windows (MSVC + torch 1.13.1) |

## 1. GeoCalib

Sumber: <https://github.com/cvg/GeoCalib> (ECCV 2024).

```powershell
$GEO="$env:TEMP\opencode\geoenv"
uv venv $GEO --python 3.11
uv pip install --python "$GEO\Scripts\python.exe" torch torchvision --index-url https://download.pytorch.org/whl/cpu
uv pip install --python "$GEO\Scripts\python.exe" "git+https://github.com/cvg/GeoCalib.git#egg=geocalib"
```

Verifikasi:

```powershell
& "$GEO\Scripts\python.exe" -c "import torch, geocalib; print(torch.__version__)"
```

Bobot GeoCalib diunduh otomatis dari Hugging Face saat pertama dipakai. Cache ada di `%USERPROFILE%\.cache\huggingface`.

## 2. Environment evaluasi

```powershell
$EVAL="$env:TEMP\opencode\cctv-eval"
uv venv $EVAL --python 3.11
uv pip install --python "$EVAL\Scripts\python.exe" numpy scipy pandas opencv-python matplotlib gdown
```

Dipakai oleh `parse_svld.py`, `svld_*.py`, `i24_parse.py`, `eval_i24_calib.py`, dan `cawang_container_fit.py`.

## 3. Vehicle keypoints

Model: `kiselyovd/vehicle-keypoints` (YOLO26-pose, 14 keypoint, MIT).

```powershell
$KP="$env:TEMP\opencode\vehicle-kp"
uv venv $KP --python 3.11
uv pip install --python "$KP\Scripts\python.exe" torch torchvision --index-url https://download.pytorch.org/whl/cpu
uv pip install --python "$KP\Scripts\python.exe" ultralytics huggingface_hub
```

Unduh bobot:

```powershell
& "$KP\Scripts\python.exe" -c "from huggingface_hub import hf_hub_download; print(hf_hub_download('kiselyovd/vehicle-keypoints', 'weights.pt', local_dir=r'out\keypoint\hf'))"
```

Verifikasi:

```powershell
& "$KP\Scripts\python.exe" -c "import torch, ultralytics; print(torch.__version__, ultralytics.__version__)"
```

Catatan: OpenPifPaf tidak dipakai karena build gagal di Windows tanpa MSVC dan memaksa torch 1.13.1. `vehicle-keypoints` adalah penggantinya.

## 4. Grounded SAM 2

Model: `IDEA-Research/grounding-dino-tiny` + `facebook/sam2.1-hiera-tiny`.

```powershell
$GS="$env:TEMP\opencode\grounded-sam2"
uv venv $GS --python 3.11
uv pip install --python "$GS\Scripts\python.exe" torch torchvision --index-url https://download.pytorch.org/whl/cpu
uv pip install --python "$GS\Scripts\python.exe" transformers pillow opencv-python
```

Verifikasi:

```powershell
& "$GS\Scripts\python.exe" -c "import torch, transformers; print(torch.__version__, transformers.__version__)"
```

Bobot diunduh otomatis dari Hugging Face saat pertama dipakai.

### Jebakan API `transformers` 5.x

Skrip `scripts/grounded_sam2_container.py` sudah disesuaikan dengan API berikut:

- `post_process_grounded_object_detection(..., threshold=...)`, bukan `box_threshold=...`;
- `post_process_masks(pred_masks, original_sizes)`, tanpa `reshaped_input_sizes`;
- label teks diambil dari `text_labels` (kunci `labels` akan berisi ID integer).

Jika memakai `transformers` 4.x, tanda tangan fungsi berbeda; sesuaikan atau pin versi 5.x.

## 5. Data dan folder kerja

```text
data/
  svld/TESTDATA2021/TESTDATA2021/    # test set SVLD-3D (tidak disertakan)
  i24/                               # menunggu akses (tidak disertakan)
out/
  svld/                              # keluaran validasi
  keypoint/                          # bobot dan keluaran keypoint
  timepass/                          # frame dan mask Cawang
reports/                             # salinan kurasi laporan dan ringkasan
```

`data/` dan `out/` di-`.gitignore`. Video Cawang (`recording cawang.mp4`) juga tidak disertakan; ekstrak frame dengan:

```powershell
ffmpeg -hide_banner -loglevel error -ss 247 -i "recording cawang.mp4" -frames:v 1 -y "out\timepass\t247.jpg"
```

## 6. Verifikasi cepat

```powershell
# parser I24-3D (tanpa data)
& "$env:TEMP\opencode\cctv-eval\Scripts\python.exe" scripts\i24_parse.py --self-test
# harus: 3x4: OK ... dan 4x3: OK ...

# GeoCalib
& "$env:TEMP\opencode\geoenv\Scripts\python.exe" scripts\geocalib_batch.py out\timepass\t247.jpg --out out\timepass\geocalib.json

# container-only
& "$env:TEMP\opencode\grounded-sam2\Scripts\python.exe" scripts\grounded_sam2_container.py `
  --image out\timepass\t247.jpg --box "255,475,405,645" --out out\timepass\gsam2_20ft

# fit 3D box kontainer
& "$env:TEMP\opencode\cctv-eval\Scripts\python.exe" scripts\cawang_container_fit.py `
  --image out\timepass\t247.jpg --mask out\timepass\gsam2_20ft\container_mask_0.npy `
  --box "230,450,430,680" --height 2.591 --out out\timepass\container20
```

## 7. Lisensi

- GeoCalib: lihat repositori asal.
- `vehicle-keypoints`: MIT.
- Grounding DINO dan SAM 2: lisensi model masing-masing di Hugging Face; periksa sebelum penggunaan komersial.
- Dataset: I24-3D non-komersial; SVLD-3D tanpa lisensi eksplisit; SKoPe3D CC BY-NC-SA 4.0; RoScenes non-komersial.
- Bobot dan dataset tidak boleh diunggah ulang ke repo ini.
