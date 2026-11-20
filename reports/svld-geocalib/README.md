# GeoCalib vs SVLD-3D: Uji Akurasi 100 Citra

**Tanggal:** 19 November 2026  
**Ruang lingkup:** 5 scene × (10 citra test + 10 citra trainval) = **100 citra**; GeoCalib single-frame dan multi-frame; GT dari `Calib/{scene}.xml`.

---

## 1. Ringkasan

1. **Hanya 1 dari 5 scene lulus**: `session0_centre` (Δf ~1%, Δpitch ~1,7°).
2. **Total 20/100 citra lulus (20%)**; multi-frame juga **1/5 scene**.
3. Scene lain gagal konsisten:
   - `0cam`: Δf **47–51%**, Δpitch **3,9–5,1°**
   - `1cam`: Δf **10–13%**, Δpitch **4,2–4,8°**
   - `session0_right`: Δf **15%**, Δpitch **0,8°** (pitch bagus, f gagal)
   - `session6_right`: Δf **19–25%**, Δpitch **3,2–4,2°**
4. Hasil **test dan trainval hampir sama** (20% lulus di keduanya), jadi ini bukan kebetulan satu frame.
5. **Yaw dan tinggi kamera tidak bisa diuji**: GeoCalib tidak mengestimasi keduanya. Roll tidak punya GT eksplisit di SVLD. Uji ini hanya untuk **f dan pitch**.
6. Kalibrasi SVLD tetap sah: reproyeksi 39.477 box trainval, median 0,73–0,84 px, 0 objek >2 px. Kegagalan ada di GeoCalib, bukan di GT.

---

## 2. Metode

- Sampel: 10 citra per scene per split, dipilih merata dari daftar nama file (bukan acak), total 100.
- Resolusi asli: 1920×1080 untuk `session0_*`; 1280×720 untuk `0cam`/`1cam`.
- Single-frame: GeoCalib per citra.
- Multi-frame: satu model shared-intrinsics per scene, 20 citra (test+trainval).
- GT: `f` (px), `fi` (pitch, rad), `theta` (yaw, rad), `h` (mm) dari XML.
- Pitch dibandingkan sebagai magnitudo (SVLD `fi` positif menunduk; GeoCalib `pitch_deg` negatif menunduk).
- Lulus jika **Δf/f <5% dan Δpitch <2°**.
- Tidak dinilai: yaw, `h`, roll (lihat §6).

Perintah ada di §8.

---

## 3. Hasil single-frame

| Scene | Split | n | f GT (px) | Δf median | Δf p90 | Δpitch median | Δpitch p90 | Lulus |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 0cam | test | 10 | 3.743,8 | 47,2% | 54,0% | 5,12° | 8,97° | 0/10 |
| 0cam | trainval | 10 | 3.743,8 | 50,7% | 56,0% | 3,88° | 4,25° | 0/10 |
| 1cam | test | 10 | 1.142,3 | 10,6% | 14,0% | 4,81° | 4,96° | 0/10 |
| 1cam | trainval | 10 | 1.142,3 | 13,4% | 14,8% | 4,21° | 4,57° | 0/10 |
| session0_centre | test | 10 | 2.878,1 | **1,5%** | 2,1% | **1,61°** | 1,75° | **10/10** |
| session0_centre | trainval | 10 | 2.878,1 | **0,7%** | 2,0% | **1,73°** | 1,81° | **10/10** |
| session0_right | test | 10 | 3.994,2 | 15,2% | 15,7% | **0,79°** | 0,84° | 0/10 |
| session0_right | trainval | 10 | 3.994,2 | 15,3% | 16,2% | **0,80°** | 0,95° | 0/10 |
| session6_right | test | 10 | 3.384,3 | 24,9% | 29,8% | 4,18° | 4,93° | 0/10 |
| session6_right | trainval | 10 | 3.384,3 | 19,1% | 28,8% | 3,24° | 4,82° | 0/10 |

**Overall:**

| Kelompok | n | Δf median | Δf p90 | Δpitch median | Δpitch p90 | Lulus |
|---|---:|---:|---:|---:|---:|---:|
| Test | 50 | 15,1% | 47,2% | 3,48° | 5,14° | 10 (20%) |
| Trainval | 50 | 14,8% | 49,7% | 2,47° | 4,45° | 10 (20%) |
| **Semua** | **100** | **14,9%** | **47,3%** | **3,03°** | **4,96°** | **20 (20%)** |

---

## 4. Hasil multi-frame

Satu model per scene, 20 citra (test+trainval):

| Scene | f GT | f Geo | Δf | Pitch GT | Pitch Geo | Δpitch | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| 0cam | 3.743,8 | 1.949 | **47,9%** | 6,43° | 10,88° | 4,45° | GAGAL |
| 1cam | 1.142,3 | 1.004 | **12,1%** | 19,12° | 14,64° | 4,48° | GAGAL |
| session0_centre | 2.878,1 | 2.846 | **1,1%** | 10,24° | 8,57° | 1,67° | **LULUS** |
| session0_right | 3.994,2 | 3.385 | **15,2%** | 9,01° | 9,82° | 0,81° | GAGAL (f) |
| session6_right | 3.384,3 | 2.610 | **22,9%** | 15,07° | 19,03° | 3,97° | GAGAL |

**Overall multi:** 1/5 lulus (20%), Δf median 15,2%, Δpitch median 3,97°. Di semua scene, f GeoCalib **lebih rendah** dari GT.

Multi-frame **tidak memperbaiki bias per scene**. Ia hanya menstabilkan angka; kesalahan f tetap 12–48% dan pitch 0,8–4,5°.

---

## 5. Interpretasi

- **`session0_centre` adalah satu-satunya scene yang cocok untuk GeoCalib**; f dan pitch sama-sama masuk gerbang.
- **`session0_right`** menunjukkan kasus penting: pitch bagus (0,8°) tetapi f meleset 15%. Gerbang harus menilai f dan pitch terpisah; pitch yang benar tidak menyelamatkan f.
- **`0cam`** paling buruk: f GeoCalib hanya ~separuh GT. Ini bukan sedikit bias; model memilih focal length yang salah.
- **`session6_right`** juga konsisten gagal di test dan trainval.
- Hasil **test vs trainval** hampir identik, jadi bukan sampling noise atau satu frame kebetulan.
- Angka ini juga hampir sama dengan uji satu citra sebelumnya (`0cam` 51%, `1cam` 10%, `centre` 2%, `right` 16%, `session6` 29%), jadi hasil lama bukan kebetulan.
- Kegagalan bukan karena GT: kalibrasi SVLD diverifikasi pada 39.477 box dengan median 0,73–0,84 px.
- Sebagian selisih pitch bisa berasal dari perbedaan **pitch gravitasi vs pitch bidang jalan** (kelandaian), tetapi 4–5° terlalu besar untuk dijelaskan hanya oleh grade jalan.

---

## 6. Yang tidak bisa diuji

| Besaran | Alasan |
|---|---|
| **Yaw** | GeoCalib tidak mengestimasi yaw; hanya f, pitch, roll. |
| **Tinggi kamera `h`** | GeoCalib tidak punya skala metrik; `h` tidak bisa dipulihkan tanpa anchor. |
| **Roll** | SVLD tidak punya tag roll eksplisit. `vanishPoints` bisa menurunkan tilt horizon, tetapi itu **derived**, bukan GT resmi; model CenterLoc3D juga tidak memakai roll. |

Jadi klaim yang sah dari uji ini hanya: **akurasi f dan pitch**.

---

## 7. Implikasi

1. **Jangan pakai GeoCalib sebagai sumber kalibrasi SVLD.** Pakai XML.
2. **Jangan pakai satu citra per scene** untuk menyimpulkan GeoCalib bagus; 100 citra mengonfirmasi 1/5 scene.
3. Untuk CCTV Indonesia, GeoCalib harus digerbang per scene dengan VP/reproyeksi; hasil SVLD menunjukkan 4/5 scene bisa gagal.
4. Untuk roll, gunakan CUTC/checkerboard atau pengukuran lapangan, bukan SVLD.
5. Untuk `h`, tetap butuh anchor/tinggi kamera terukur.

---

## 8. Reproduksi

```powershell
# 1. Sampel 10 citra/scene/split + manifest GT
py scripts\svld_geocalib_sample.py --per-scene 10 --out out\svld_geocalib

# 2. GeoCalib single-frame (geoenv)
$GEO = "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe"
$files = Import-Csv out\svld_geocalib\manifest.csv | ForEach-Object { $_.source }
& $GEO scripts\geocalib_batch.py @files --out out\svld_geocalib\geocalib_single.json

# 3. GeoCalib multi-frame per scene (20 citra: test+trainval)
foreach ($s in '0cam','1cam','session0_centre','session0_right','session6_right') {
  & $GEO scripts\calib_compare\run_geocalib_multi.py `
    "out\svld_geocalib\frames_multi\$s" `
    --out "out\svld_geocalib\geocalib_multi_$s.json"
}

# 4. Evaluasi
py scripts\eval_svld_geocalib.py `
  --manifest out\svld_geocalib\manifest.csv `
  --single out\svld_geocalib\geocalib_single.json `
  --multi-dir out\svld_geocalib `
  --out out\svld_geocalib
```

Artefak:

- `out/svld_geocalib/manifest.csv` — 100 citra + GT.
- `out/svld_geocalib/geocalib_single.json` — 100 hasil single.
- `out/svld_geocalib/geocalib_multi_*.json` — 5 hasil multi.
- `out/svld_geocalib/eval_single.csv` — 100 baris.
- `out/svld_geocalib/eval_multi.csv` — 5 baris.
- `out/svld_geocalib/eval_summary.json` — ringkasan.
- `reports/svld-geocalib/summary.csv` — ringkasan per scene/split.
- `reports/svld-geocalib/single.csv`, `multi.csv` — salinan tabel.

---

## 9. Batas

- 10 citra per scene per split, bukan seluruh 16.829 citra.
- Sampel merata berdasarkan nama file, bukan stratifikasi visual/oklusi.
- GeoCalib pretrained, CPU, bobot `pinhole`.
- GT pitch per scene, tidak ada variasi per frame.
- Tidak menguji yaw, `h`, atau roll (lihat §6).
- `veh_size` SVLD yang preset tidak relevan untuk uji kalibrasi ini.
