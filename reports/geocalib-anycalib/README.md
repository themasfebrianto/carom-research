# Laporan Hari Ini: GeoCalib vs AnyCalib, dan Persiapan I24-3D

**Tanggal:** 19 November 2026  
**Ruang lingkup hari ini:** hanya **GeoCalib** dan **AnyCalib**; VP dan anchor belum diuji sebagai pipeline penuh. I24-3D baru tahap persiapan, belum download 50 GB.

---

## 1. Kesimpulan singkat

**GeoCalib dan AnyCalib bukan pengganti kalibrasi metrik.** Keduanya memberi sebagian dari yang dibutuhkan:

| Kebutuhan | GeoCalib | AnyCalib | VP | Anchor |
|---|---|---|---|---|
| `f` / intrinsik | **ya** | **ya** | tidak | tidak |
| pitch/roll | **ya** (gravity) | tidak | pitch dari jalan | tidak |
| yaw | tidak | tidak | **ya** | tidak |
| skala metrik | tidak | tidak | tidak | **ya** |

Jadi untuk laporan hari ini, posisinya:

> **GeoCalib/AnyCalib = estimator intrinsik/pose awal. VP = arah jalan. Anchor = skala. Tanpa VP + anchor, hasilnya belum kalibrasi metrik.**

---

## 2. Bukti dari uji yang sudah ada

### Cawang (720p, anchor `w=3,60 m`)

| Metode | f (px) | Δf vs Cawang | RMS fixed pose |
|---|---:|---:|---:|
| Cawang dash fit | 1082,58 | 0% | **1,101** |
| GeoCalib single | 943,28–980,50 | **−9% s/d −13%** | 3,1–4,4 |
| GeoCalib multi | 969,55 | −10,4% | 3,49 |
| AnyCalib simple | 1100–1207 | **+1,6% s/d +11,5%** | 1,2–2,8 |
| AnyCalib radial:1 | 1252,85 | +15,7% | 3,87 |
| VP-only (`f=1082,6`) | 1082,58 | 0% | 1,33 |

**Bacaan:** GeoCalib sistematis terlalu rendah; AnyCalib lebih dekat tetapi tidak stabil antar frame. Tidak ada yang menyamai dash fit Cawang.

### Video tes LearnPinhole (480×360)

| Metode | f (px) | pitch | yaw | RMS/posisi |
|---|---:|---:|---:|---|
| Baseline | ≈502 | 4,86° | −1,75° | h=6,26 m |
| GeoCalib multi | **501,80** | 3,08°* | — | f cocok |
| AnyCalib simple | 528,22 | — | — | +5,2%, range 510–598 |
| VP lajur | 501,80 | **4,913°** | **−1,659°** | cocok baseline |

\* Pitch GeoCalib = gravity, bukan pitch jalan.

**Bacaan:** pada video ini, GeoCalib + VP cukup untuk `f` dan pose. Anchor lebar jalan tidak stabil karena jalan melengkung/batas kanan keluar frame; anchor Avanza tetap lebih tepat.

---

## 3. GeoCalib: pros and cons

### Pro

- **Tidak butuh garis dash**; bisa jalan di satu citra.
- Memberi **`f` + arah gravitasi** (pitch/roll).
- Ada **multi-frame shared-intrinsics**, berguna untuk kamera statis.
- Ada **uncertainty** (walau perlu dicek).
- Relatif robust di scene umum; tidak perlu training lokal.

### Con

- **Pinhole-centric**: satu focal length, principal point diasumsikan di tengah.
- Di Cawang, `f` **9–13% terlalu rendah**.
- **Pitch = gravity, bukan bidang jalan**; beda 0,5–1,8° pada data kita.
- Uncertainty single-image besar (187–229 px di Cawang); multi-frame justru terlalu optimistis (0,01 px).
- Tidak memberi **yaw** dan **skala**.

**Cocok untuk:** prior `f`/roll, inisialisasi, cross-check.  
**Tidak cocok untuk:** satu-satunya sumber kalibrasi ODOL.

---

## 4. AnyCalib: pros and cons

### Pro

- **Model-agnostik**: pinhole, radial, KB, UCM, EUCM, division.
- Bisa mengestimasi **fx/fy, cx/cy, distorsi**; berguna untuk lensa CCTV yang tidak diketahui.
- Tahan crop/stretch; tidak butuh gravity.
- Bisa sangat dekat pada frame yang “baik” (Cawang TEMA: 1100 px, +1,6%).

### Con

- **Tidak memberi gravity/pose**; yaw/pitch tetap harus dari VP.
- **Tidak stabil antar frame**: Cawang 1100–1207; LearnPinhole 510–598.
- Tidak ada mode **shared-intrinsics** seperti GeoCalib.
- Tidak menonjolkan uncertainty.
- Model distorsi bisa menyerap skala; `radial:1` Cawang justru lebih buruk (1252 px).

**Cocok untuk:** cek `f`/distorsi per frame, inisialisasi, cross-check.  
**Tidak cocok untuk:** kalibrasi tunggal tanpa VP/anchor.

---

## 5. Mengapa VP dan anchor masih wajib

- **VP** memberi **yaw** dan **pitch jalan**; GeoCalib/AnyCalib tidak memberi yaw.
- **Anchor** memberi **skala metrik**; tanpa itu `f` dan `h` hanya saling menyerap.
- Satu anchor cukup secara teori, tetapi harus **diukur** (lebar lajur/tinggi kamera), bukan diasumsikan.
- Tanpa VP + anchor, GeoCalib/AnyCalib hanya memberi “bentuk” kamera, bukan ukuran.

**Status untuk laporan hari ini:**

```text
GeoCalib/AnyCalib = komponen
VP + anchor       = syarat wajib
```

---

## 6. Persiapan test I24-3D (BMVC 2023)

50 GB terlalu besar untuk hari ini. Jangan download seluruh dataset.

### Yang perlu diunduh sekarang (kecil)

- `scene1_hg.json` — kalibrasi semua kamera.
- `scene1_annotations.csv` — box 3D/dimensi.
- `scene1_splobj.json` / `scene1_ts.csv` — opsional.

Ini cukup untuk:

- memvalidasi parser `P`/`H`/`vps`,
- cek satuan kaki → meter,
- uji round-trip `P` → `corr_pts`,
- menyiapkan tabel GT.

### Video: satu kamera dulu

- Pilih satu kamera dekat (`p1c1` atau yang tersedia).
- Download **satu video** saja; ekstrak 10 frame.
- Kalau file per kamera tidak tersedia dan hanya ZIP scene 50 GB, tunda video; metadata dulu.

### Perintah persiapan

```powershell
# parser tanpa data
py scripts\i24_parse.py --self-test

# parse GT kalibrasi
py scripts\i24_parse.py `
  --hg data\i24\hg\scene1_hg.json `
  --out out\i24\calib_gt_scene1.json

# ekstrak 3 frame dari satu kamera
py scripts\i24_frames.py `
  data\i24\video\scene1\p1c1.mp4 `
  --out out\i24\frames\scene1 --times 10 30 50
```

### Yang harus dicek

1. `P` 3×4 atau 4×3; parser sudah menerima keduanya.
2. `height_m`: kalau ~110, itu **kaki**; kalikan 0,3048.
3. Round-trip `P` → `corr_pts`; target <1 px.
4. Resolusi video vs `P`; skala `fx,fy,cx,cy` jika memakai 1080p.
5. `vps` untuk cek pitch/yaw.
6. Label: **reference calibration (H_inv + VP + box-scale)**, bukan checkerboard GT.

### Matriks uji minimum

| Faktor | Target hari ini | Target lanjutan |
|---|---|---|
| Kamera | 1 | 3 |
| Frame | 10 | 30 |
| Metode | GeoCalib, AnyCalib, VP | + kombinasi, anchor |
| Metrik | Δf, Δpitch, Δyaw, Δh | + reproyeksi, dimensi |

Perbandingan lengkap SVLD/I24-3D/I24V/CUTC/RoScenes ada di `reports/DATASET-KALIBRASI.md`.

---

## 7. Rencana laporan hari ini

1. **Tulis pros/cons GeoCalib vs AnyCalib** (dokumen ini).
2. **Tegaskan VP + anchor wajib**; jangan klaim kalibrasi metrik dari model saja.
3. **Siapkan I24**: metadata + satu video; parser self-test sudah lulus.
4. **Belum download 50 GB**; tunda sampai scope jelas.
5. Besok/lanjutan: parse `scene1_hg.json`, jalankan GeoCalib/AnyCalib pada 10 frame, bandingkan dengan `P`/`vps`.

---

## 8. Batas

- Uji Cawang dan LearnPinhole bukan ground truth independen.
- I24 `P` adalah kalibrasi turunan, bukan checkerboard.
- Belum ada video I24 yang diuji hari ini.
- Pros/cons di atas berlaku untuk data dan model yang diuji; generalisasi perlu 3–5 kamera.
