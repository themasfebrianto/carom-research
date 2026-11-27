# Cawang: Median VP + Anchor `f` — Seberapa Akurat?

**Tanggal:** 27 November 2026  
**Tujuan:** menguji pipeline **median VP + koreksi skala `f` per kamera** di Cawang, lalu membandingkan `f`, pitch, yaw, dan RMS dengan referensi dash fit Cawang.  
**Data:** 8 median temporal Cawang (7 lokal + `median2`), 1280×720.

> **Batasan ground truth.** Cawang **tidak punya ground truth independen**. Referensi yang dipakai adalah **dash fit dengan `w = 3,60 m`** (`f≈1082,35 px`, pitch `2,466°`, yaw `0,287°`). Anchor 20 ft TEMA memvalidasi skala 3,6 m di Cawang dalam ~0,2%, tetapi itu tetap validasi skala, bukan kalibrasi XML independen. Jadi angka di bawah adalah **konsistensi terhadap referensi dash fit**, bukan akurasi absolut terhadap kebenaran fisik.

---

## 1. Ringkasan

1. **VP Cawang sangat stabil.** 8 frame memberi `u=650,1–653,2`, `v=307,3–313,6`; median **`(651,48, 312,41)`**. Tidak ada outlier seperti di 1cam SVLD.
2. **Median VP + `f` referensi** memberi pose **pitch `2,518°`, yaw `0,607°`** vs dash fit **`2,466°`, `0,287°`** → **Δpitch `+0,052°`, Δyaw `+0,320°`**. Pitch sangat dekat; yaw punya bias sistematis +0,32°.
3. **Median VP + anchor dash** (oracle): `f` error median **0,88%**, maks **3,05%**; pose error median **0,052° pitch / 0,320° yaw**; **8/8** lulus f<5% dan pose<2°.
4. **Median VP + anchor buta** (50/50 fusion dari frame lain): `f` error median **1,44%**, maks **4,02%**; pose **0,077°/0,326°**; **8/8** lulus.
5. **Satu frame anchor buta** (LOO 56 pasangan): `f` error median **1,50%**, maks **5,50%**, **55/56** lulus f<5%; pose **56/56** lulus. Satu pasangan agak melewati 5%; gunakan beberapa frame/median scale.
6. **RMS fixed pose** pada 3 frame yang punya anotasi dash:
   - Anchor dash: **1,374 / 1,443 / 1,398 px** vs referensi **1,101 / 1,131 / 1,174 px** — **3/3** lulus gate RMS <1,5 px.
   - Anchor buta: **1,489 / 1,569 / 1,456 px** — **2/3** lulus; t350 sedikit di atas 1,5 px.
7. **Penting:** `f` GeoCalib mentah error **12,9%**, tetapi pose-nya hanya meleset **0,43° pitch / 0,41° yaw** dan **lulus 8/8 gate pose 2°**. Di Cawang yang pitch-nya hanya 2,4°, gate pose 2° **tidak cukup** untuk mendeteksi `f` yang salah. Yang menangkap error `f` adalah **gate f<5%** dan **RMS fixed pose** (4,3–4,7 px vs 1,1–1,2 px).
8. **Kesimpulan:** median VP + anchor **akurat relatif terhadap dash fit Cawang** untuk `f` (~1%) dan pitch (~0,05–0,1°), tetapi **yaw masih bias +0,32°**. Bias ini berasal dari geometri VP/marka, bukan dari `f`. RMS fixed pose ~1,4 px, hanya ~0,25 px di atas dash fit.

---

## 2. Metode

### 2.1 Frame dan `f`

Delapan median temporal dari `reports/calib-compare/fusion_frames.csv`:

| Frame | `f` GeoCalib | `f` AnyCalib | `f` 50/50 |
|---|---:|---:|---:|
| tm050 | 950,01 | 1211,26 | 1080,64 |
| tm150 | 913,82 | 1191,84 | 1052,83 |
| tm250 | 929,09 | 1150,79 | 1039,94 |
| tm350 | 933,45 | 1235,89 | 1084,67 |
| tm450 | 945,25 | 1198,02 | 1071,64 |
| tm500 | 946,51 | 1243,00 | 1094,75 |
| tm550 | 967,24 | 1230,71 | 1098,98 |
| median2 | 939,86 | 1183,10 | 1061,48 |

Referensi: `f=1082,35`, pitch `2,466°`, yaw `0,287°` (rata-rata dash fit median2/t350/t500).

### 2.2 VP

`detect_lane_vp` dari `LearnPinhole/backend` dijalankan pada 8 frame dengan `prior_focal=1082,35`. Hasilnya stabil; median `u,v` dipakai untuk semua frame (kamera statis).

### 2.3 Anchor dan skala

Tiga varian anchor:

- **Dash** (oracle): `s = f_ref / median(f_geo)`; ini memakai referensi dash.
- **Blind** (realistis): `s = median(f_50/50 / f_geo)` dari 8 frame; tidak memakai referensi dash.
- **Single anchor** (LOO): `s = f_50/50(anchor) / f_geo(anchor)` dari satu frame lain; diulang untuk 56 pasangan.

`f_corr = s · f_geo`. Untuk varian 50/50, `f_50/50` juga diskalakan dengan `s` yang sesuai.

### 2.4 Metrik

- Error `f` terhadap 1082,35 px.
- Pose dari median VP: `pitch = atan2(cy−v, f)`, `yaw = atan2((u−cx)·cos(pitch), f)` (konvensi Cawang: positif bawah/kanan).
- Error pose terhadap dash fit 2,466°/0,287°.
- RMS fixed pose: dash model dengan `f,pitch,yaw` dipegang, `h,Xp,Y0` di-fit; dijalankan untuk 3 frame yang punya anotasi dash (median2, t350, t500) memakai `fit_compare_frame.mjs`.

---

## 3. Hasil

### 3.1 Stabilitas VP

| Frame | u | v | Inlier | RMS |
|---|---:|---:|---:|---:|
| tm050 | 650,08 | 307,28 | 17 | 1,15 |
| tm150 | 651,17 | 313,33 | 16 | 2,17 |
| tm250 | 650,95 | 310,33 | 15 | 1,43 |
| tm350 | 651,79 | 313,61 | 17 | 1,88 |
| tm450 | 651,12 | 311,49 | 12 | 1,48 |
| tm500 | 652,93 | 312,73 | 13 | 1,78 |
| tm550 | 653,17 | 312,82 | 14 | 1,96 |
| median2 | 652,64 | 312,08 | 16 | 1,95 |
| **Median** | **651,48** | **312,41** | — | — |

Tidak ada outlier VP; rentang `u` hanya 3,1 px dan `v` 6,3 px. Ini berbeda dari 1cam SVLD yang punya 4 outlier.

### 3.2 `f` dan pose (8 frame)

| Varian | `f` median | `|Δf|` median | `|Δf|` maks | Lulus f<5% | `|Δpitch|` median | `|Δyaw|` median | Lulus pose<2° |
|---|---:|---:|---:|---:|---:|---:|---:|
| GeoCalib mentah | 942,6 | **12,92%** | 15,57% | 0/8 | 0,425° | 0,410° | **8/8** |
| 50/50 mentah | 1076,1 | 1,34% | 3,92% | 8/8 | 0,066° | 0,324° | 8/8 |
| Geo + dash scale | 1082,3 | **0,88%** | 3,05% | 8/8 | **0,052°** | 0,320° | 8/8 |
| Geo + blind scale | 1071,5 | 1,44% | 4,02% | 8/8 | 0,077° | 0,326° | 8/8 |
| 50/50 + dash scale | 1082,3 | 1,55% | 3,36% | 8/8 | 0,052° | 0,320° | 8/8 |
| Single anchor LOO | — | 1,50% | 5,50% | **55/56** | — | — | **56/56** |

Bacaan:

- **Anchor dash** memberi `f` paling dekat (0,88% median) karena memang memakai referensi.
- **Anchor buta** (50/50) tetap memberi 1,44% median; ini menunjukkan bias `f` per kamera cukup stabil untuk dikoreksi tanpa referensi dash.
- **Satu anchor** bisa mencapai 5,50% (satu pasangan); gunakan median beberapa frame.
- **Pose** selalu <2° bahkan untuk GeoCalib mentah, karena pitch Cawang rendah. Jadi gate pose bukan uji `f` yang baik di sini.

### 3.3 RMS fixed pose (3 frame ber-anotasi dash)

| Frame | Referensi dash `f/pitch/yaw` | RMS dash | RMS anchor dash | RMS anchor buta |
|---|---|---|---:|---:|---:|
| median2 | 1082,03 / 2,429° / 0,269° | 1,101 | **1,374** | 1,489 |
| t350 | 1082,43 / 2,482° / 0,300° | 1,131 | **1,443** | 1,569 |
| t500 | 1082,03 / 2,485° / 0,289° | 1,174 | **1,398** | 1,456 |

Catatan: angka referensi di tabel ini berasal dari `fit_compare_frame.mjs` (3 dash per lajur), sedikit berbeda dari dash fit 18 tepi (`1082,35/2,466/0,287`). Perbedaan ini adalah variasi pemilihan dash, bukan error metode.

- Anchor dash: **3/3** di bawah gate RMS 1,5 px.
- Anchor buta: **2/3** di bawah 1,5 px; t350 1,569 px.
- Kenaikan RMS ~0,25–0,30 px sebagian besar berasal dari **bias yaw +0,31–0,34°**, bukan dari `f`.

### 3.4 Kenapa GeoCalib mentah lolos pose tetapi gagal `f`

Pitch Cawang hanya ~2,4°, sehingga sensitivitas pose terhadap `f` kecil:

\[
\frac{d\,\text{pitch}}{d\ln f} = -\tfrac12 \sin(2\,\text{pitch})
\approx -0,042 \text{ rad} \approx -2,4°/\ln f
\]

Error `f` 13% (ln ≈ −0,139) hanya menggeser pitch ~0,33°. Karena gate pose 2°, GeoCalib mentah tetap **8/8 lulus pose**. Tetapi:

- gate `f<5%`: **0/8**;
- RMS fixed pose: **4,3–4,7 px** vs dash **1,1–1,2 px**.

Jadi untuk Cawang, **jangan menilai `f` dari pose gate saja**. Gunakan gate `f` dan RMS fixed pose. Ini pelajaran yang sama dengan SVLD: pitch rendah → window `f` lebar → pose tidak sensitif terhadap `f`.

### 3.5 Bias yaw

Median VP `u=651,48`; dash fit yaw `0,287°` setara dengan `u≈645,4`. Selisih **~6,1 px** menghasilkan bias yaw **+0,32°**. Bias ini:

- konsisten di semua frame (0,31–0,34°);
- tidak berubah saat `f` dikoreksi;
- masih di bawah gate 2°, tetapi bukan nol.

Kemungkinan penyebab: marka yang tidak sejajar sempurna dengan sumbu jalan, lengkung halus, atau perbedaan konvensi yaw antara VP dan dash fit. Untuk aplikasi yang butuh yaw <0,1°, bias ini harus dikalibrasi per kamera atau diganti dengan yaw dari dash fit.

---

## 4. Interpretasi

1. **Median VP + anchor bekerja di Cawang** relatif terhadap dash fit: `f` ~1%, pitch ~0,05–0,1°, yaw ~0,32°.
2. **Anchor tidak harus dash fit.** Anchor buta dari 50/50 fusion memberi `f` 1,44% median. Ini karena bias `f` GeoCalib per kamera stabil (1,15× di Cawang), bukan noise acak.
3. **Satu anchor cukup untuk sebagian besar frame**, tetapi bisa melewati 5% pada satu pasangan. Untuk produksi, gunakan 5–10 frame anchor dan median scale.
4. **RMS fixed pose ~1,4 px** vs dash 1,1–1,2 px. Ini masih sangat baik untuk pose, tetapi bukan pengganti dash fit jika target RMS <1,2 px.
5. **Bias yaw +0,32°** adalah residual utama. Kalau target yaw ketat, perlu koreksi yaw per kamera.

---

## 5. Keterbatasan

- Cawang tidak punya GT independen; referensi dash fit `w=3,60 m` bergantung pada asumsi lebar lajur.
- Uji ini hanya satu kamera Cawang dan 8 median temporal; belum lintas kamera/situs.
- Anchor “buta” memakai 50/50 fusion yang khusus Cawang; di SVLD fusi ini gagal. Yang diuji adalah **mekanisme scale per kamera**, bukan keampuhan 50/50 secara umum.
- Anchor dash adalah oracle; angka 0,88% adalah batas atas, bukan hasil buta.
- RMS hanya dihitung pada 3 frame yang punya anotasi dash.
- Bias yaw +0,32° bisa berubah jika marka/jalan berubah; perlu diuji ulang.

---

## 6. Langkah berikutnya

1. **Ganti anchor 50/50 dengan anchor geometri** (dash+solid, 3D box PnP, objek known-width) dan ulangi tanpa referensi dash.
2. **Uji kamera Cawang kedua** atau situs lain untuk melihat apakah bias `f` dan bias yaw per kamera stabil.
3. **Kalibrasi yaw offset per kamera** atau gunakan yaw dash fit jika target yaw ketat.
4. **Implementasikan reliability gate**: hitung window `f` dari VP/pitch; jika ketidakpastian `f` melebihi window, tandai frame.
5. **Uji multi-frame anchor**: 5–10 frame, median scale, lalu evaluasi pada frame held-out.

---

## 7. Berkas

| Berkas | Isi |
|---|---|
| `median_vp_anchor_frames.csv` | 8 frame: `f` Geo/Any/50-50, `f` dash scale, `f` blind scale, error, pitch/yaw |
| `median_vp_anchor_rms.csv` | 6 baris: RMS fixed pose anchor dash/buta pada median2/t350/t500 |
| `median_vp_anchor_summary.json` | Ringkasan varian, median VP, scale, single anchor LOO |
| `cawang_vp8.json` | VP per frame + median |
| `../../scripts/calib_compare/cawang_median_vp_anchor.py` | Skrip VP median + anchor |
| `fusion-2026-11-26.md` | Fusi `f` GeoCalib + AnyCalib Cawang |
