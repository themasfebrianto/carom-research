# SVLD-3D: Uji VP dan Pengukuran Lebar Lajur

**Tanggal:** 20 November 2026  
**Ruang lingkup:** 100 citra yang sama dengan uji GeoCalib (10 test + 10 trainval per scene); VP jalan untuk pitch/yaw; lebar lajur dari marka dan dari posisi lateral kendaraan.

---

## 1. Ringkasan

1. **VP + `f` GT sangat akurat**: **95/100** lulus gate pitch/yaw <2°, median Δpitch **0,20°**, Δyaw **0,05°**. Empat dari lima scene 100% lulus; **median VP per scene: 5/5 <0,5°**.
2. **VP + `f` GeoCalib**: **47/100** lulus, median Δpitch **2,46°**, Δyaw **1,12°**. Lebih baik dari GeoCalib saja (**20/100**), tetapi **f GeoCalib tetap bottleneck**.
3. **VP memberi yaw**, yang tidak dimiliki GeoCalib. Dengan `f` yang benar, VP hampir menyelesaikan masalah pose.
4. **Lebar lajur bukan 3,6 m secara universal.** Posisi lateral kendaraan memberi **2,7–3,25 m**; marka memberi **3,0–3,56 m**; kedua metode berbeda hingga **0,6 m**. Untuk skala absolut, ukur lebar lajur per lokasi; jangan pakai 3,6 m buta.
5. `1cam` adalah scene tersulit: 4/20 frame memilih VP yang salah (outlier lokal), meskipun VP yang benar untuk scene ini adalah `(u≈464, v≈−42)`.

---

## 2. Metode

- Sampel: 100 citra yang sama dengan `reports/svld-geocalib/` (10 test + 10 trainval per scene).
- Deteksi: `LearnPinhole/backend/app/lane_vp.detect_lane_vp` pada marka putih/kuning; `prior_focal` = `f` GT atau `f` GeoCalib.
- Pose: `vp_pose.pose_from_vp(u, v, f, cx, cy, roll=0)`. Konvensi ini cocok dengan model SVLD `R = Rx(fi + π/2) Rz(theta)`; sudut dibandingkan langsung.
- Lulus: **Δpitch <2° dan Δyaw <2°**, dengan VP diterima jika `ok`, inliers ≥4, RMS ≤3 px.
- Lebar lajur:
  - **Marka**: segmen marka inlier VP di-back-project ke bidang jalan dengan kalibrasi GT; cluster offset lateral; jarak antar cluster = lebar.
  - **Kendaraan**: pusat lateral box 3D dari 39.477 anotasi trainval; histogram 0,1 m; puncak = pusat lajur; jarak puncak = lebar.

---

## 3. Hasil VP

### 3.1 VP + `f` GT

| Scene | Split | n | Δpitch median | Δpitch p90 | Δyaw median | Δyaw p90 | Lulus |
|---|---|---:|---:|---:|---:|---:|---:|
| 0cam | test | 10 | 0,08° | 0,62° | 0,03° | 0,51° | 9/10 |
| 0cam | trainval | 10 | 0,03° | 0,06° | 0,02° | 0,02° | 10/10 |
| 1cam | test | 10 | 0,29° | 15,75° | 0,04° | 5,46° | 8/10 |
| 1cam | trainval | 10 | 0,31° | 12,98° | 0,06° | 4,48° | 8/10 |
| session0_centre | test | 10 | 0,37° | 0,45° | 0,24° | 0,55° | 10/10 |
| session0_centre | trainval | 10 | 0,47° | 0,53° | 0,08° | 0,36° | 10/10 |
| session0_right | test | 10 | 0,03° | 0,07° | 0,06° | 0,07° | 10/10 |
| session0_right | trainval | 10 | 0,04° | 0,09° | 0,05° | 0,07° | 10/10 |
| session6_right | test | 10 | 0,20° | 1,58° | 0,04° | 0,15° | 10/10 |
| session6_right | trainval | 10 | 0,23° | 0,42° | 0,03° | 0,07° | 10/10 |

**Overall:** 95/100 lulus; Δpitch median 0,20° (p90 0,88°), Δyaw median 0,05° (p90 0,38°); RMS VP median 1,75 px.

### 3.2 VP + `f` GeoCalib

| Scene | Δpitch test / trainval | Δyaw test / trainval | Lulus test / trainval |
|---|---|---:|---:|
| 0cam | 5,63° / 6,41° | 3,39° / 4,24° | 0/10 / 0/10 |
| 1cam | 2,76° / 3,22° | 1,02° / 1,24° | 2/10 / 0/10 |
| session0_centre | 0,21° / 0,40° | 0,47° / 0,19° | 10/10 / 10/10 |
| session0_right | 1,62° / 1,62° | 0,28° / 0,30° | 10/10 / 10/10 |
| session6_right | 3,28° / 3,39° | 3,93° / 2,90° | 1/10 / 4/10 |

**Overall:** 47/100 lulus; Δpitch median **2,46°**, Δyaw median **1,12°**. VP tetap menerima 100% frame; yang gagal adalah akurasi pose akibat `f` yang salah.

### 3.3 Perbandingan

| Metode | f | pitch | yaw | Lulus (pitch/yaw <2°) |
|---|---|---|---:|
| GeoCalib single | dari citra | ya | tidak | **20/100** |
| VP + f GT | GT | ya | **ya** | **95/100** |
| VP + f GeoCalib | GeoCalib | ya | **ya** | **47/100** |

**Bacaan:** VP adalah estimator yaw/pitch yang kuat **jika f diketahui**. GeoCalib bagus untuk f hanya di sebagian scene; begitu f salah, VP ikut salah. Jadi urutan yang masuk akal: **f dari dash fit/known camera/anchor → VP untuk yaw/pitch**, bukan GeoCalib sendirian.

### 3.4 Kegagalan

- `1cam` 4/20 frame: VP terkunci pada persilangan garis yang salah (`u≈584–600, v≈237–342`) alih-alih VP benar (`u≈464, v≈−42`). Solusi praktis: kamera statis → median VP antar frame, atau prior horizon/VP dari frame sebelumnya.
- `0cam` 1/10 frame test: `v=−220` (bukan `−62`), pitch error 2,37°.
- Selain itu, VP cocok dengan GT sampai <0,5°.

### 3.5 Median VP per scene (kamera statis)

Karena kamera SVLD statis, median `u,v` dari 20 frame per scene menolak outlier lokal:

| Scene | f GT: Δpitch / Δyaw | f GeoCalib: Δpitch / Δyaw |
|---|---:|---:|
| 0cam | 0,01° / 0,02° | 5,76° / 3,81° |
| 1cam | 0,25° / 0,03° | 2,77° / 1,04° |
| session0_centre | 0,43° / 0,14° | 0,31° / 0,32° |
| session0_right | 0,03° / 0,05° | 1,62° / 0,29° |
| session6_right | 0,20° / 0,03° | 4,10° / 3,71° |

**Dengan f GT: 5/5 scene lulus**, semua <0,5°. **Dengan f GeoCalib: 2/5** (hanya centre dan right). Jadi median temporal menghilangkan outlier 1cam, tetapi tidak memperbaiki f yang salah.

---

## 4. Lebar lajur

| Scene | Marka median (IQR) | Puncak kendaraan (m) | Lebar kendaraan | Kandidat |
|---|---|---|---:|---:|
| 0cam | 3,51 (2,91–4,08) | −10,05; −7,05; −4,45; −1,45 | 3,00; 2,60; 3,00 | **3,0 m** |
| 1cam | 2,99 (2,92–3,00) | −7,55; −1,85; 0,85 | 2,70 | **2,7–3,0 m** |
| session0_centre | 3,00 (2,47–3,39) | −0,05; 8,45; 11,65; 18,25; 20,55; 24,65 | 3,20; 4,10 | **3,2 m** (4,1 mungkin lajur lebar/bahu) |
| session0_right | 3,53 (3,34–3,64) | −8,25; −3,05; 0,15; 3,35; 10,95; 13,95 | 3,20; 3,20; 3,00 | **3,2 m** |
| session6_right | 3,56 (3,11–3,72) | −14,25; −9,65; −6,35; −3,15 | 3,30; 3,20 | **3,25 m** |

**Kesimpulan anchor:**

- Tidak ada bukti bahwa lebar lajur SVLD seragam 3,6 m. Estimasi kendaraan memberi **2,7–3,25 m**; estimasi marka memberi **3,0–3,56 m**. Selisih antar metode sampai **0,6 m**.
- Untuk skala absolut, **ukur lebar lajur per lokasi** (meteran/laser/satelit). Gunakan estimasi kendaraan sebagai prior, marka sebagai cross-check, dan laporkan ketidakpastian ±0,3–0,5 m.
- Untuk Cawang: jangan pakai `w=3,60` sebagai GT. Ukur lebar lajur aktual; container 20 ft (lebar 2,438 m) tetap menjadi cek skala independen yang sudah terbukti (6,046 vs 6,058 m).

---

## 5. Implikasi

1. **VP lebih cocok untuk pose daripada GeoCalib** pada SVLD, asalkan `f` benar. Ini mengubah prioritas: cari `f` yang terverifikasi (dash fit, kamera diketahui, atau anchor), lalu pakai VP untuk yaw/pitch.
2. **GeoCalib tidak boleh menjadi satu-satunya sumber f.** Pada 4/5 scene SVLD, f meleset 10–51%.
3. **Anchor width harus per lokasi.** 3,6 m adalah asumsi, bukan pengukuran. Untuk ODOL, kesalahan anchor 5% langsung menjadi kesalahan skala 5%.
4. **Kamera statis**: median VP antar frame dapat menolak outlier `1cam`. Uji ini belum dijalankan; kandidat langkah berikutnya.
5. **Roll/h tetap tidak tersedia** dari VP. Jangan mengklaim keduanya.

---

## 6. Reproduksi

```powershell
# VP + f GT dan VP + f GeoCalib (100 citra)
py scripts\svld_vp_eval.py --source gt  --out out\svld_vp
py scripts\svld_vp_eval.py --source geo --out out\svld_vp

# Lebar lajur dari posisi lateral kendaraan 3D
py scripts\svld_lane_width.py --out out\svld_vp --min-width-m 2.5

# Median VP per scene (kamera statis)
py scripts\svld_vp_scene_median.py --out out\svld_vp
```

Artefak:

- `out/svld_vp/vp_gt.csv`, `vp_geo.csv` — 100 baris per sumber f.
- `out/svld_vp/vp_summary_gt.json`, `vp_summary_geo.json` — ringkasan per scene/split.
- `out/svld_vp/lane_width_frames.csv` — lebar per frame dari marka.
- `out/svld_vp/lane_width_summary.json` — ringkasan marka.
- `out/svld_vp/vehicle_lane_width.csv` — puncak lajur dari box 3D.
- `out/svld_vp/vp_scene_median.csv` — median VP per scene (f GT dan GeoCalib).
- `reports/svld-vp/summary.csv` — ringkasan VP.
- `reports/svld-vp/lane_width.csv` — perbandingan marka vs kendaraan.
- `reports/svld-vp/vp_scene_median.csv` — ringkasan median VP.
- `reports/svld-vp/vp_gt.csv`, `vp_geo.csv`, `lane_width_frames.csv` — salinan tabel.

---

## 7. Batas

- VP bergantung pada marka; scene tanpa marka jelas akan gagal.
- 1cam memiliki outlier VP lokal; belum diuji dengan temporal median.
- Gate 2° untuk yaw dan pitch sama seperti SOP; yaw bukan gate resmi SVLD.
- `f` GT dipakai untuk batas atas; `f` GeoCalib untuk skenario realistis.
- Lebar lajur dari marka dan kendaraan adalah proxy; bukan pengukuran lapangan.
- `veh_size` preset tidak dipakai di sini.
