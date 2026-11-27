# SVLD: Diagnosis Kegagalan `f` GeoCalib + Garis VP

**Tanggal:** 27 November 2026  
**Tujuan:** menjelaskan, per citra, mengapa pose dari `f` GeoCalib + garis VP gagal di sekitar 50% citra SVLD, lalu menguji mitigasinya.  
**Data:** 100 citra yang sama dengan uji VP sebelumnya (10 test + 10 trainval per scene, 5 scene).

---

## 1. Ringkasan

1. **Baseline: 47/100 lulus** gate pitch/yaw <2°. **53 gagal.**
2. **VP bukan bottleneck.** Dari 100 citra, **99** memberi VP yang identik (atau hampir identik) saat `f` GT dan `f` GeoCalib dipakai. Dengan `f` GT, **95/100** lulus. Jadi 5 kegagalan yang tersisa adalah outlier VP, bukan masalah `f`.
3. **48 dari 53 kegagalan murni karena `f`.** VP bagus (VP-induced error <2°), tetapi `f` GeoCalib berada di luar **window `f`** yang masih memberi pose <2°. **5 kegagalan sisanya** adalah `BOTH`: VP outlier + `f` juga di luar window. **Tidak ada kegagalan murni VP.**
4. **Bias `f` GeoCalib bersifat per-kamera, bukan noise acak.** Rasio GT/GeoCalib: **0cam 1,92×**, **1cam 1,14×**, **session0_centre 1,01×**, **session0_right 1,18×**, **session6_right 1,31×**. Bias ini konsisten antar frame di scene yang sama.
5. **Window `f` per citra** menjelaskan kenapa error yang sama bisa lulus di satu scene dan gagal di scene lain:

   | Scene | `f` Geo/GT | Window `f` (median) | Pitch GT | Pass |
   |---|---:|---:|---:|---:|
   | 0cam | 0,52× | −24,1% .. +45,1% | 6,43° | 0/20 |
   | 1cam | 0,87× | −8,8% .. +14,2% | 19,12° | 2/20 |
   | session0_centre | 0,99× | −11,7% .. +17,4% | 10,24° | 20/20 |
   | session0_right | 0,85× | −18,2% .. +29,4% | 9,01° | 20/20 |
   | session6_right | 0,76× | −13,5% .. +14,4% | 15,07° | 5/20 |

6. **Mitigasi**:

   | Metode | Pass |
   |---|---:|
   | Per-image VP + `f` GeoCalib (baseline) | **47/100** |
   | Per-image VP + `f` GT | 95/100 |
   | Per-image VP + median `f` per scene (LOO) | 40/100 |
   | Per-image VP + scale per kamera (LOO) | **91/100** |
   | Median VP + `f` GeoCalib | 48/100 |
   | Median VP + scale per kamera (LOO) | **95/100** |
   | Median VP + `f` GT | 100/100 |
   | Per-image VP + affine per kamera (LOO) | 95/100 |
   | Median VP + affine per kamera (LOO) | 100/100 |

7. **5 outlier VP**:
   - **4 di 1cam**: `v` = +237, +292, +337, +342, padahal VP normal ≈ −42; VP error 13–18°.
   - **1 di 0cam**: `v` = −220, inlier hanya 6; VP error 2,37°.
   - Penyebab: detektor garis memilih tepi jalan/curb yang melengkung ketika marka putus-putus samar atau tertutup kendaraan. Gate sederhana `v < cy` menolak 4 outlier 1cam; `inliers ≥ 8` menolak outlier 0cam.
8. **Rekomendasi:** untuk CCTV statis, kalibrasi `f` per kamera sekali (1–10 frame anchor), gunakan median VP temporal, dan pasang reliability gate berbasis window `f`. Jika belum ada anchor, pakai geometri marka (dash+solid/lebar lajur) atau objek known-width. **GeoCalib sendiri tidak cukup.**

---

## 2. Metode diagnosis

### 2.1 Data

- `out/svld_vp/vp_geo.csv` — 100 baris: `f` GeoCalib, VP, pose.
- `out/svld_vp/vp_gt.csv` — 100 baris: `f` GT, VP, pose.
- `out/svld_geocalib/manifest.csv` — GT `f`, pitch, yaw, width, height.

VPGeo dan VPGT sama di **99/100** citra. Satu-satunya perbedaan: `real_scene_cam1_005176.jpg` (`u` 600,87 vs 600,61; `v` 342,27 vs 342,05) — perbedaan sub-piksel, tidak mengubah diagnosis.

### 2.2 Dekomposisi error

Untuk setiap citra:

- `pose(VP, f)` = pitch/yaw dari VP dan `f` (roll = 0, sama dengan `app.vp_pose`).
- **Komponen `f`**: `|pose(VP, f_geo) − pose(VP, f_gt)|`.
- **Komponen VP**: `|pose(VP, f_gt) − GT pose|`.
- **Total**: `|pose(VP, f_geo) − GT pose|`.

### 2.3 Window `f`

Untuk setiap citra dicari interval `f` di sekitar `f_gt` yang masih memberi `max(|Δpitch|, |Δyaw|) < 2°`. Error pose monoton terhadap `f` di kedua sisi `f_gt`, jadi intervalnya kontigu; pencarian memakai scan log + bisection. Jika error di `f_gt` sudah ≥2°, window kosong (VP-limited).

### 2.4 Klasifikasi

| Label | Arti |
|---|---|
| `PASS` | Total error <2° |
| `F_OUT` | Total ≥2°, VP error <2°, `f_geo` di luar window |
| `BOTH` | Total ≥2°, VP error ≥2°, `f_geo` juga di luar window |
| `VP` | Total ≥2°, VP error ≥2°, `f_geo` di dalam window (tidak terjadi) |
| `OTHER` | Sisa (tidak terjadi) |

### 2.5 Mitigasi yang diuji

Semua memakai 100 citra yang sama:

- `per_image_vp_geo_f` — baseline.
- `per_image_vp_gt_f` — ceiling dengan VP per citra.
- `per_image_vp_loo_scale` — `f_geo × median(f_gt/f_geo)` dari 19 frame lain di scene yang sama (leave-one-out).
- `loo_median_vp_geo_f` — VP median 19 frame lain, `f_geo`.
- `loo_median_vp_loo_scale` — median VP + scale LOO.
- `loo_median_vp_gt_f` — median VP + `f` GT.
- `per_image_vp_loo_affine` — affine `f_gt = a·f_geo + b`, fit pada 19 frame lain.
- `loo_median_vp_loo_affine` — median VP + affine.
- **Single anchor** — satu frame jadi anchor, `ratio = f_gt_anchor / f_geo_anchor`, diterapkan ke 19 frame lain; diulang untuk setiap anchor.

Implementasi: `scripts/diagnose_svld_vp_failures.py`.

---

## 3. Hasil

### 3.1 Sebab per scene

| Scene | n | Pass | `F_OUT` | `BOTH` | `f` Geo/GT | Window `f` (median) | Pitch GT |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0cam | 20 | 0 | 19 | 1 | 0,52× | −24,1% .. +45,1% | 6,43° |
| 1cam | 20 | 2 | 14 | 4 | 0,87× | −8,8% .. +14,2% | 19,12° |
| session0_centre | 20 | 20 | 0 | 0 | 0,99× | −11,7% .. +17,4% | 10,24° |
| session0_right | 20 | 20 | 0 | 0 | 0,85× | −18,2% .. +29,4% | 9,01° |
| session6_right | 20 | 5 | 15 | 0 | 0,76× | −13,5% .. +14,4% | 15,07° |

Pola test vs trainval konsisten: 0cam 0/10 + 0/10, 1cam 2/10 + 0/10, session0_centre 10/10 + 10/10, session0_right 10/10 + 10/10, session6 1/10 + 4/10.

### 3.2 Kenapa error `f` berdampak berbeda di tiap scene

Sensitivitas pitch terhadap `f` (roll = 0):

$$
\frac{d\,\text{pitch}}{d\ln f} = -\tfrac12 \sin(2\,\text{pitch})
$$

Semakin besar pitch, semakin sempit window `f`:

- **1cam** pitch 19° → sensitivitas ≈17,4°/ln `f`; error 12,5% (ln ≈ −0,134) memberi ≈2,3° pitch error — tepat di batas.
- **session6_right** pitch 15° → ≈14,3°/ln `f`; error 23,6% memberi ≈3,8° — gagal.
- **session0_right** pitch 9° → ≈8,9°/ln `f`; error 15,2% memberi ≈1,35° — lulus.
- **0cam** pitch 6,4° → ≈6,4°/ln `f`; error 52% memberi ≈4,7° — gagal meski window lebar.

Jadi kegagalan adalah **bias `f` per kamera × sensitivitas pose terhadap `f`**, bukan VP. Window `f` adalah cara praktis menghitung batas toleransi per citra tanpa perlu GT.

### 3.3 Outlier VP

| Scene | Image | u | v | Inlier | VP error | Cause |
|---|---|---:|---:|---:|---:|---|
| 1cam | `real_scene_cam1_004010.jpg` | 584,4 | **292,8** | 9 | 15,75° | BOTH |
| 1cam | `real_scene_cam1_005176.jpg` | 600,9 | **342,3** | 10 | 18,23° | BOTH |
| 1cam | `real_scene_cam1_001644.jpg` | 564,4 | **237,1** | 9 | 12,98° | BOTH |
| 1cam | `real_scene_cam1_002467.jpg` | 599,9 | **337,0** | 10 | 17,97° | BOTH |
| 0cam | `real_scene_cam0_007941.jpg` | 927,9 | **−220,0** | 6 | 2,37° | BOTH |

Empat outlier 1cam punya `v` **di bawah pusat gambar** (cy = 360), padahal VP jalan yang benar ≈ −42. Detektor memilih tepi kanan/curb yang melengkung ketika marka putus-putus di foreground samar; inlier 9–10 dan RMS ~1,0–1,6 px membuatnya tampak “percaya diri”. Contoh pembanding: `real_scene_cam1_004535.jpg` punya `u=463,8, v=−39,5` dan lolos dengan `f` GT.

Outlier 0cam punya `v=−220` (di atas pusat) dan hanya **6 inlier**; normalnya 8–15. Ini outlier yang lebih halus, tetapi tetap terdeteksi oleh jumlah inlier. Catatan: error outlier 0cam bisa ditekan ke 0,75° jika `f` dinaikkan 23% ke 4601 px, tetapi itu mengompensasi VP yang salah — bukan solusi yang benar. Median VP + `f` yang benar lebih baik.

**Gate single-frame yang bekerja di data ini:**

- `v < cy` → menolak 4 outlier 1cam; tidak ada citra normal yang punya `v ≥ cy`.
- `inliers ≥ 8` → menolak outlier 0cam (6 inlier). Tiga citra normal dengan 7 inlier juga ikut ditolak, tetapi ketiganya sudah `F_OUT`, jadi tidak ada pass yang hilang.

**Median VP temporal** lebih kuat: 19 frame lain untuk setiap citra. Dengan `f` GT, median VP memberi **100/100**; dengan scale per kamera, **95/100**.

### 3.4 Hasil mitigasi

| Metode | Pass |
|---|---:|
| Per-image VP + `f` GeoCalib | **47/100** |
| Per-image VP + `f` GT | 95/100 |
| Per-image VP + median `f` per scene (LOO) | 40/100 |
| Per-image VP + scale per kamera (LOO) | **91/100** |
| Median VP + `f` GeoCalib | 48/100 |
| Median VP + scale per kamera (LOO) | **95/100** |
| Median VP + `f` GT | 100/100 |
| Per-image VP + affine per kamera (LOO) | 95/100 |
| Median VP + affine per kamera (LOO) | 100/100 |

Bacaan:

- **Median VP saja tidak menyembuhkan `f`** (48/100). Ia hanya memperbaiki outlier VP.
- **Scale per kamera menyembuhkan sebagian besar bias `f`** (91/100 dengan VP per citra; 95/100 dengan median VP).
- **Affine per kamera + median VP** mencapai 100/100, tetapi ini oracle: affine di-fit dari GT `f` 19 frame lain. Ini menunjukkan batas atas, bukan metode buta.
- **Jangan pakai median `f` per scene**: hasilnya 40/100, lebih buruk dari baseline. Variasi `f` antar frame masih informatif; yang perlu dikoreksi adalah skala/bias, bukan variasi tersebut.

### 3.5 Robustness satu anchor

Satu frame dipakai sebagai anchor, ratio `f_gt/f_geo` diterapkan ke 19 frame lain:

| Scene | Per-image VP, median (min–max) | Median VP, median (min–max) |
|---|---|---:|
| 0cam | 17,5 (7–19) | 17,0 (7–19) |
| 1cam | 15,0 (14–16) | **19,0 (19–19)** |
| session0_centre | 19,0 (19–19) | 19,0 (19–19) |
| session0_right | 19,0 (19–19) | 19,0 (19–19) |
| session6_right | 11,0 (8–16) | 12,0 (8–17) |

Satu anchor cukup untuk 4/5 scene, tetapi **session6 butuh beberapa frame** (atau affine) karena variasi `f` GeoCalib-nya lebih lebar (rasio GT/Geo p10–p90 1,12–1,42). 0cam bisa apes jika frame anchor kebetulan outlier (min 7/19); gunakan 5–10 frame dan median ratio, bukan satu frame.

---

## 4. Alasan per citra

- **`diagnosis.csv`** — 100 baris, satu baris per citra, dengan kolom `cause`, `detail`, `f_geo`, `f_gt`, `f_err_pct`, `f_lo_pct`, `f_hi_pct`, `vp_err_at_gt_deg`, `d_pitch_f`, `d_yaw_f`, `d_pitch_vp`, `d_yaw_vp`, dll.
- **`failure_table.md`** — 53 baris kegagalan, siap dibaca.
- **`diagnosis_summary.json`** — ringkasan per scene, mitigasi, single anchor, outlier VP.

Contoh pembacaan:

| Image | `f` Geo/GT | Window | VP error | Cause | Arti |
|---|---|---:|---:|---|---|
| `real_scene_cam0_004450.jpg` | 1811 / 3744 (−51,6%) | −24,0% .. +45,5% | 0,00° | F_OUT | `f` terlalu rendah; VP sempurna. Scale 1,92× menyembuhkan. |
| `real_scene_cam1_005088.jpg` | 982 / 1142 (−14,0%) | −8,7% .. +14,6% | 0,32° | F_OUT | Sedikit di luar window; scale 1,14× menyembuhkan. |
| `real_scene_cam1_004010.jpg` | 1025 / 1142 (−10,3%) | kosong | 15,75° | BOTH | VP salah (v=293); median VP + scale menyembuhkan. |
| `session6_right_008...jpg` | 2406 / 3384 (−28,9%) | −13,5% .. +14,4% | 1,72° | F_OUT | `f` terlalu rendah; scale 1,31× menyembuhkan. |

Untuk daftar lengkap, buka `failure_table.md`.

---

## 5. Kenapa GeoCalib bisa bias

- Model kalibrasi single-image (GeoCalib, AnyCalib, PerspectiveFields, DeepCalib) memprediksi `f` dari isi citra **plus prior FOV** dari distribusi training. Prior ini tidak uniform.
- **0cam** punya hFOV 19,4° (tele), jauh di luar distribusi model; GeoCalib memprediksi hFOV ≈39° (`f` 1810 vs 3743). Ini konsisten dengan literatur prior mismatch (mis. FoundationGeo): model learned bukan self-calibration, mereka memakai prior.
- Bias per kamera stabil: rasio GT/Geo p10–p90 **1,48–2,27** (0cam), **1,10–1,17** (1cam), **0,995–1,021** (session0_centre), **1,17–1,19** (session0_right). Session6 lebih lebar (**1,12–1,42**), kemungkinan karena variasi isi scene.
- **VP jalan hanya memberi 2 constraint** (pitch, yaw) untuk 3 unknown (`f`, pitch, yaw). Untuk mendapatkan `f`, dibutuhkan cue kedua yang independen:
  1. **Lebar lajur** — garis sejajar + lebar known (Caprile & Torre 1990; Guiducci 2000; Fung 2003; Lu 2014). Lane fit lama 0/45 karena extraction; dengan VP sebagai hard constraint, pencarian garis bisa dipersempit.
  2. **VP kedua** — vertikal atau vehicle VP (Caprile & Torre; Kocur & Ftáčnik 2021). Vertical VP otomatis gagal; bobot deep_vp tidak tersedia.
  3. **Objek known-width / 3D box PnP** — f langsung dari dimensi known; SVLD box PnP <0,2% dengan box GT, 1,86% dengan noise realistis.
  4. **Dash + garis solid** — jalur aktif; f bersyarat pada lebar lajur dan standar dash.
- Diagnosis ini menunjukkan: **VP sudah baik; investasi berikutnya adalah cue kedua untuk `f`, bukan detektor VP yang lebih rumit.**

---

## 6. Mitigasi yang disarankan

### A. Kalibrasi `f` per kamera sekali (static camera)

- Ambil 5–10 frame per kamera.
- Estimasi `f` anchor dengan geometri (dash+solid, lebar lajur, objek known-width, 3D box).
- Fit `f_anchor = a·f_geo + b` (affine) atau minimal median `f_anchor/f_geo`.
- Terapkan ke semua frame.
- Ekspektasi: **91–95/100** dengan VP per citra; **95–100/100** dengan median VP.

### B. Median VP temporal

- 10–20 frame; median `u,v`; pakai untuk semua frame.
- Menghilangkan 4 outlier 1cam; dengan `f` GT mencapai 100/100.
- Single-frame gate: `v < cy`, `inliers ≥ 8`, `rms ≤ 3 px`; tandai frame yang gagal gate.

### C. Reliability gate berbasis window `f`

- Hitung sensitivitas `f` dari VP/pitch: `|dpitch/dln f| = 0,5|sin(2 pitch)|` (tambahkan komponen yaw).
- Bandingkan dengan ketidakpastian `f` dari kalibrasi per kamera.
- Jika ketidakpastian > window, tandai frame dan minta anchor/frame lain.
- Ini memberi alasan per citra secara online dan mencegah kegagalan senyap.

### D. Fallback geometri

- Satu frame per kamera dengan dash + garis solid dan lebar lajur terukur/standar.
- Atau objek known-width / container / 3D box PnP.
- Jadikan anchor untuk kalibrasi per kamera; setelah itu GeoCalib+VP menangani frame lain.

### E. Jangan pakai median `f` per scene

- 40/100, lebih buruk dari baseline. Variasi `f` antar frame informatif; koreksi yang benar adalah skala/bias per kamera, bukan mengganti semua `f` dengan median.

### F. Jangan percaya VP per citra tanpa gate

- 5/100 outlier, semuanya terdeteksi oleh `v < cy` atau `inliers ≥ 8`.
- Median VP temporal lebih kuat daripada gate single-frame.

### G. Algoritma ringkas yang diusulkan

**Offline, sekali per kamera:**

1. Ambil 5–10 frame.
2. Estimasi `f` anchor per frame dengan dash+solid, objek known-width, atau 3D box PnP.
3. Fit koreksi per kamera `f_anchor = a·f_geo + b` (atau median `f_anchor/f_geo`).
4. Hitung median VP `(u,v)` dari frame-frame tersebut.
5. Simpan `(a, b, u_med, v_med)` sebagai profil kamera.

**Online, per frame:**

1. Deteksi garis dan VP.
2. Gate VP: `v < cy`, `inliers ≥ 8`, `rms ≤ 3 px`; jika gagal, pakai median VP profil.
3. Hitung `f_corr = a·f_geo + b`.
4. Hitung pitch/yaw dari VP dan `f_corr`.
5. Hitung window/sensitivitas `f`; jika ketidakpastian `f` (dari residual kalibrasi) melebihi window, tandai frame dan minta anchor/frame lain.
6. Jika kamera belum punya profil, jalankan fallback geometri (dash+solid/lebar lajur/objek) pada frame itu, atau tandai **UNCALIBRATED** — jangan keluarkan pose dengan `f` GeoCalib mentah.

---

## 7. Keterbatasan

- Angka 91/95/100 memakai GT `f` untuk kalibrasi LOO/affine; ini **batas atas/oracle**, bukan metode buta.
- Simulasi single anchor memakai GT `f` satu frame; dalam praktik anchor harus diukur.
- Diagnosis hanya 5 kamera statis SVLD, 20 frame per kamera; bias per kamera bisa berubah karena cuaca/waktu. Rekalibrasi periodik perlu diuji.
- Threshold gate (`v < cy`, `inliers ≥ 8`) dituning pada sampel ini; validasi pada kamera lain.
- Gate 2° sama dengan evaluasi; gate yang lebih ketat akan mempersempit window dan menuntut `f` lebih akurat.
- Outlier VP 1cam terlihat jelas secara visual; outlier 0cam lebih halus dan hanya tertangkap oleh jumlah inlier.

---

## 8. Langkah berikutnya

1. **Uji end-to-end tanpa GT `f`**: pakai dash+solid atau 3D box PnP untuk memberi anchor `f` di 5 scene SVLD, lalu ukur pass rate.
2. **Kalibrasi per kamera pada 5–10 frame**, uji pada frame held-out (split waktu/cuaca).
3. **Implementasikan reliability gate online**; ukur false accept/reject.
4. **Perbaiki lane extraction dengan VP sebagai hard constraint**; uji lane-width `f`.
5. **Uji VP kedua** (vehicle/vertical) sebagai cue `f` independen.
6. **Ulangi diagnosis di Cawang dan CCTV lain**; cek stabilitas bias per kamera antar hari.

---

## 9. Berkas

| Berkas | Isi |
|---|---|
| `diagnosis.csv` | 100 baris: `f` Geo/GT, window, dekomposisi error, `cause`, `detail` |
| `failure_table.md` | 53 baris kegagalan, tabel Markdown |
| `diagnosis_summary.json` | Ringkasan per scene, mitigasi, single anchor, outlier VP |
| `../../scripts/diagnose_svld_vp_failures.py` | Skrip diagnosis dan mitigasi |
| `../svld-vp/README.md` | Uji VP dan lebar lajur sebelumnya |
| `../svld-geocalib/README.md` | Uji GeoCalib vs GT SVLD |
