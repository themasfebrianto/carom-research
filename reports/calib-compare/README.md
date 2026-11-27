# Uji Banding Kalibrasi: GeoCalib vs AnyCalib vs VP vs Cawang

**Tanggal:** 19 November 2026  
**Tujuan:** membandingkan `f`, pitch, yaw, dan tinggi kamera dari GeoCalib, AnyCalib, dan vanishing point (VP) terhadap kalibrasi Cawang yang sudah ada, dengan **anchor lebar lajur `w = 3,60 m`** yang sama untuk semua metode.

> **Batas penting:** Cawang bukan ground truth independen. Angka Cawang adalah hasil fitting 18 tepi dash yang sudah di-anchor ke `w = 3,60 m`. Uji ini mengukur **konsistensi metode**, bukan akurasi absolut. Untuk akurasi absolut tetap diperlukan `h` laser/RTK, `w` meteran, atau ground truth kendaraan.

---

## 1. Data dan metode

**Input:**

- `frames/median2.png` — median temporal 49 frame, 1280×720.
- `frames/dashes2.json` — 6 dash bersih (2 lajur × 3 baris) × 3 observasi = **18 residual**.
- `frames/vp.json` — VP dari `vpfit.mjs`: `(651,54, 309,96)`.
- Frame tambahan: `frame_sinkor_86.png` (t≈86 s) dan `frame_tema_247.png` (t≈247 s), diekstrak dari klip bukti.

**Model:** sama dengan `anchor.mjs`:

```text
proj(p, X, Y) dengan p = { f, pitch, yaw, h }
w = 3,60 m (dipaku)
periode dash 13 m, panjang dash 5 m
```

**Dua mode fitting untuk tiap metode:**

1. **Fixed pose** — `f`, pitch, yaw dari metode dipegang; fit `h`, `Xp`, `Y0`; lihat RMS.
2. **Fixed f** — hanya `f` dari metode yang dipegang; fit pitch, yaw, `h`, `Xp`, `Y0`; lihat apakah f saja kompatibel dengan geometri dash.

Metode yang diuji:

- **Cawang** — `anchor.mjs`, baseline.
- **GeoCalib** — `f` + gravity pitch; yaw dari VP. Diuji single-image, multi-frame shared-intrinsics, dan varian distorted.
- **AnyCalib** — `f` dari `simple_pinhole`, `pinhole`, dan `radial:1`; pitch/yaw dari VP.
- **VP-only** — pitch/yaw dari VP, `f` tetap 1082,58 px.
- **Free fit** — semua parameter bebas dengan `w = 3,60 m` (kontrol).

---

## 2. Hasil utama

| Metode | f (px) | Δf vs Cawang | pitch | yaw | h (m) | RMS fixed pose | RMS fixed f |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Cawang dash fit** | 1082,58 | 0,0% | 2,432° | 0,271° | 8,876 | **1,101** | **1,101** |
| GeoCalib pinhole median2 | 943,28 | −12,9% | 1,995° | 0,700° | 9,234 | 3,963 | 2,168 |
| GeoCalib multi shared | 969,55 | −10,4% | 1,905° | 0,681° | 8,989 | 3,487 | 1,852 |
| AnyCalib simple median2 | 1183,10 | +9,3% | 2,422° | 0,559° | 8,521 | 2,310 | 1,615 |
| AnyCalib pinhole median2 | 1181,63 | +9,1% | 2,425° | 0,559° | 8,529 | 2,279 | 1,604 |
| AnyCalib radial:1 median2 | 1252,85 | +15,7% | 2,287° | 0,528° | 8,157 | 3,867 | 2,216 |
| AnyCalib simple TEMA 247 | 1100,00 | +1,6% | 2,605° | 0,601° | 9,027 | 1,215 | 1,122 |
| AnyCalib gen simple median2 | 1244,78 | +15,0% | 2,302° | 0,531° | 8,196 | 3,682 | 2,144 |
| VP-only (f=1082,6) | 1082,58 | 0,0% | 2,646° | 0,610° | 9,145 | 1,333 | 1,101 |
| Free fit (w=3,60) | 1082,03 | −0,05% | 2,429° | 0,269° | 8,875 | **1,101** | — |

**Bacaan:** semakin kecil RMS, semakin cocok dengan 18 tepi dash. Cawang dan free fit berada di **1,101 px**. Tidak ada metode eksternal yang menyamai itu.

---

## 3. Temuan

### 3.1 Cawang tetap yang paling konsisten

Free fit dengan `w = 3,60 m` mengembalikan:

```text
f = 1082,03 px
pitch = 2,429°
yaw = 0,269°
h = 8,875 m
RMS = 1,101 px (12 DoF)
```

Ini praktis sama dengan `anchor.mjs` (`f=1082,58`, `h=8,876`, RMS 1,097–1,101). Artinya, dengan anchor yang sama, data dash memang memilih keluarga solusi Cawang.

### 3.2 GeoCalib: `f` sistematis terlalu rendah

- Single-image pinhole: `f = 943,28` (median2), `960,33` (median), `967,91` (sinkor), `980,50` (tema).
- Selisih terhadap Cawang: **−9,4% sampai −12,9%**.
- Multi-frame shared-intrinsics (8 frame): `f = 969,55`; tidak memperbaiki.
- Varian distorted + `simple_radial`: `f = 890,34`, `k1 ≈ −0,063`; justru lebih jauh.
- Ketidakpastian f yang dilaporkan single-image: **187–229 px** (≈20–24% relatif) — model sendiri menandai f tidak stabil.
- RMS fixed pose: **3,15–4,37 px**; bahkan setelah pose di-fit (fixed f), RMS masih **1,73–2,17 px**.

**Kesimpulan:** pada citra CCTV low-pitch ini, GeoCalib tidak cukup akurat untuk `f`. Ia juga tidak bisa menggantikan pose dash: dengan `f` dipaku ke 1082,58, pitch GeoCalib (1,88°/1,70°) memberi RMS **2,44/2,89 px**, lebih buruk dari pitch dash (2,43°, RMS 1,10). Jadi GeoCalib **bukan** sumber pitch yang lebih baik untuk Cawang.

### 3.3 AnyCalib: lebih baik dari GeoCalib, tetapi tidak stabil antar frame

- `simple_pinhole` median2: `f = 1183,10` (+9,3%); RMS fixed pose 2,310; fixed f 1,615.
- `pinhole` median2: `fx = 1184,90`, `fy = 1178,36` (beda 0,55%), `cx = 640,09`, `cy = 361,66`; `f` rata-rata 1181,63.
- `radial:1` median2: `f = 1252,85`, `k1 = −0,0289`; RMS fixed pose 3,867; fixed f 2,216. Model distorsi tidak membantu di citra ini.
- **Frame TEMA t=247:** `f = 1100,00` (+1,6%); RMS fixed pose **1,215**, fixed f **1,122** — hampir menyamai Cawang.
- Frame sinkor t=86: `f = 1206,90` (+11,5%); RMS fixed pose 2,826.
- Varian `anycalib_gen` + `simple_pinhole`: median2 1244,78; tema 1155,83. Selisih model mencapai ~5%.

**Kesimpulan:** AnyCalib bisa sangat dekat pada frame yang “baik” (TEMA: +1,6%, RMS 1,215), tetapi meleset 9–12% pada frame lain. Ia belum bisa menjadi pengganti kalibrasi dash; lebih tepat sebagai **independent check/prior per frame** dengan gerbang.

### 3.4 VP-only: bagus sebagai inisialisasi, bukan hasil akhir

- Dengan `f = 1082,58`, VP `vpfit` memberi pitch **2,646°**, yaw **0,610°**.
- Fixed pose RMS **1,333 px**; fixed f (pose di-fit) kembali ke **2,433°/0,273°/1,101 px**.
- Artinya VP dari `vpfit` hanya **0,21° pitch dan 0,34° yaw** dari solusi dash; cukup untuk inisialisasi, tetapi tidak cukup untuk menggantikan fitting 18 tepi.

### 3.5 Invarian menjelaskan mengapa RMS memburuk

Dengan `w = 3,60 m` dipaku, data dash menghendaki:

```text
f·h ≈ 9609 px·m
f·w ≈ 3897 px·m
```

- GeoCalib `f = 943` dengan `h` hasil fit 8,38 → `f·h ≈ 7906`, jauh di luar keluarga.
- AnyCalib `f = 1183` dengan `h` 9,29 → `f·h ≈ 10983`, juga jauh.
- AnyCalib TEMA `f = 1100` dengan `h` 8,945 → `f·h ≈ 9839`, dekat; karena itu RMS-nya bagus.

Ini bukan soal optimizer, melainkan **f yang tidak cocok dengan kombinasi f·h/f·w yang diukur marka**.

---

## 4. Rekomendasi

1. **Pertahankan dash fit + anchor `w` sebagai kalibrasi utama Cawang.** Tidak ada metode eksternal yang lebih baik pada data ini.
2. **GeoCalib jangan dipakai sebagai sumber `f` atau pitch utama** untuk Cawang. Jika dipakai, hanya sebagai sinyal gravitasi/roll dengan prior `f` yang kuat, dan harus divalidasi terhadap VP/dash.
3. **AnyCalib pakai sebagai cek independen per frame**, bukan pengganti:
   - jika `|Δf|/f < 5%` dan `|Δpitch| < 0,5°` terhadap dash fit → terima sebagai konfirmasi;
   - jika di luar itu → tandai frame/kamera, jangan paksa.
   - Frame TEMA lulus; median2/sinkor tidak.
4. **VP tetap dipakai untuk inisialisasi yaw/pitch**, tetapi pose akhir harus dari fitting dash (atau fitting gabungan).
5. **Jangan menambah `k1` hanya karena tersedia.** Pada uji ini `radial:1` dan GeoCalib distorted tidak memperbaiki RMS; model distorsi malah menyerap skala.
6. **Langkah berikutnya:** uji pada 20–50 kamera I24-3D/SVLD-3D, dan ukur `h`/`w` Cawang dengan laser/meteran untuk mendapatkan ground truth independen.

---

## 5. Keterbatasan

- Cawang bukan ground truth independen; `w = 3,60 m` adalah asumsi standar.
- Hanya 18 observasi dari 6 dash; tidak ada roll dalam model fitting.
- GeoCalib/AnyCalib adalah model general-purpose, dilatih pada OpenPano; domain CCTV low-pitch mungkin out-of-distribution.
- Uji CPU, single-image; AnyCalib tidak punya mode shared-intrinsics seperti GeoCalib.
- Belum ada uji downstream kontainer 20 ft karena `out/timepass` (gambar + mask) tidak disertakan di repo.

---

## 6. Artefak

- `summary.csv` — tabel hasil di atas.
- `fits.json` — hasil fitting lengkap (parameter, RMS, DoF, invarian).
- `geocalib_median2.json`, `geocalib_median.json`, `geocalib_sinkor_86.json`, `geocalib_tema_247.json`, `geocalib_multi_sinkor.json`, `geocalib_distorted_simple_radial_median2.json`.
- `anycalib_simple_pinhole.json`, `anycalib_pinhole.json`, `anycalib_radial1.json`, `anycalib_simple_sinkor_86.json`, `anycalib_simple_tema_247.json`, `anycalib_gen_simple_median2.json`, `anycalib_gen_simple_tema_247.json`.
- Skrip reproduksi: `scripts/calib_compare/` (`run_geocalib.py`, `run_anycalib.py`, `run_geocalib_multi.py`, `fit_compare.mjs`, `make_summary.py`, `run_all.ps1`).

**Reproduksi:**

```powershell
# environment: lihat scripts/calib_compare/README.md
pwsh scripts\calib_compare\run_all.ps1

# atau manual setelah environment aktif:
$py = "C:\Users\omega\AppData\Local\Temp\opencode\carom-calib\env\Scripts\python.exe"
& $py scripts\calib_compare\run_geocalib.py frames\median2.png --out out\calib-compare\geocalib_median2.json
& $py scripts\calib_compare\run_anycalib.py frames\median2.png --cam-id simple_pinhole --out out\calib-compare\anycalib_simple_pinhole.json
node scripts\calib_compare\fit_compare.mjs
& $py scripts\calib_compare\make_summary.py
```

---

## 7. Apakah combo GeoCalib + AnyCalib + VP + anchor `w` cukup?

**Cukup sebagai bahan, belum cukup sebagai hasil akhir.** Kombinasi ini sudah membentuk semua komponen homografi metrik, tetapi kualitasnya bergantung pada cara menggabungkannya.

| Komponen | Status pada uji Cawang |
|---|---|
| `f` GeoCalib | 943–980 px, 9–13% terlalu rendah |
| `f` AnyCalib | 1100–1207 px, bergantung frame; TEMA +1,6%, median2 +9,3% |
| VP garis | beda 0,21° pitch / 0,34° yaw dari dash fit; RMS fixed pose 1,333 px |
| anchor `w=3,60` | asumsi; error skala ±4% → ±9 cm pada 30 m |
| roll | GeoCalib −0,54°; model dash mengabaikan roll |
| joint fit | belum ada; ini yang membuat error `f`/VP/anchor bertumpuk |

**Agar cukup:**

1. pilih `f` dengan gerbang/median 5–10 frame; jangan pakai satu frame;
2. VP dari garis sejajar/tepi jalan/vehicle VP yang bersih, robust;
3. ukur `w` atau `h`, jangan hanya mengasumsikan 3,60 m;
4. joint fit `f, pitch, yaw, roll, h` dengan prior, bukan plug-and-play;
5. validasi reproyeksi ≤1–2 px dan cek `h` independen;
6. ground truth lokal sebagai gerbang akhir.

**Putusan:** cukup untuk screening/kalibrasi awal; belum untuk penegakan ODOL. Untuk Cawang, dash fit + anchor `w` tetap yang utama.

---

## 8. Kesimpulan satu paragraf

Dengan anchor `w = 3,60 m` yang sama, kalibrasi Cawang dari 18 tepi dash tetap yang paling konsisten (RMS 1,101 px). GeoCalib memberi `f` 9–13% terlalu rendah dan pitch yang tidak cocok dengan geometri dash; multi-frame shared-intrinsics tidak memperbaikinya. AnyCalib lebih dekat, tetapi hasilnya bergantung frame: +1,6% pada frame TEMA (RMS 1,215) dan +9–12% pada frame lain. VP `vpfit` hanya selisih 0,21°/0,34° dari solusi dash, cukup untuk inisialisasi tetapi bukan pengganti fitting. Untuk carom, **dash fit + anchor `w` tetap menjadi kalibrasi utama**, sedangkan GeoCalib/AnyCalib dipakai sebagai **pemeriksaan independen dengan gerbang**, bukan sebagai sumber tunggal.

---

## 9. Replikasi frame baru (26 November 2026)

Dua median temporal lokal baru dari `recording cawang.mp4` (window 325–374 s dan 475–524 s) mengonfirmasi pola lama. Detail: [`newframe-2026-11-26.md`](newframe-2026-11-26.md).

| Frame | f dash | f GeoCalib | Δf | RMS GeoCalib+VP | RMS VP-only |
|---|---:|---:|---:|---:|---:|
| t350 | 1082,43 | 928,50 | −14,22% | 4,674 px | 1,323 px |
| t500 | 1082,03 | 944,10 | −12,75% | 4,285 px | 1,374 px |

- Dash fit baru tetap `1,13–1,17 px`, cocok dengan baseline `1,101 px`.
- GeoCalib f tetap 12,8–14,2% terlalu rendah; pitch 0,38–0,49° terlalu kecil.
- VP dengan f dash: Δpitch `+0,16°`, Δyaw `+0,31–0,32°`, RMS `1,32–1,37 px`.
- VP lokal t500 gagal (pitch `1,693°`, RMS `3,041 px`); gunakan VP median temporal/global, bukan satu frame.
- **Kesimpulan tidak berubah:** f dari dash/anchor → VP untuk pitch/yaw; GeoCalib hanya roll/sanity, bukan sumber f.

---

## 10. Fusi `f` GeoCalib + AnyCalib (26 November 2026)

Uji terpisah: delapan median temporal Cawang (7 lokal + `median2`), model default, referensi dash fit `f=1082,35 px`. Detail: [`fusion-2026-11-26.md`](fusion-2026-11-26.md).

| Metode | Bias | MAE | Maks | Lulus <5% |
|---|---:|---:|---:|---:|
| GeoCalib | −13,09% | 13,09% | 15,57% | 0/8 |
| AnyCalib | +11,38% | 11,38% | 14,84% | 0/8 |
| **Rata-rata 50/50** | **−0,85%** | **1,58%** | **3,92%** | **8/8** |
| Bobot 0,47 Geo / 0,53 Any (LOO) | −0,10% | 1,80% | 3,61% | 8/8 |
| Median Geo + median Any (agregat) | −0,81% | 0,81% | 0,81% | 1/1 |

**Bacaan:** pada Cawang, bias GeoCalib dan AnyCalib hampir sama besar dan berlawanan arah, sehingga rata-rata 50/50 memberi `f` dalam 1,6% MAE — jauh lebih baik daripada masing-masing model. Bobot optimal 0,470/0,530 dan koreksi skala 1,006 menunjukkan ini bukan tuning. Namun ini **spesifik Cawang**: di SVLD fusi yang sama hanya 17/100 (GeoCalib 20/100). Jangan generalisasi 50/50 tanpa kalibrasi bobot per kamera. Untuk kalibrasi metrik penuh, `f` hasil fusi tetap harus dipasangkan dengan VP + anchor.
