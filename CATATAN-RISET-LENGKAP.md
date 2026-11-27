# Catatan Riset Lengkap — CAROM Air untuk CCTV

Status: 18 November 2026
HEAD saat catatan dibuat: `1fadfc4`

Dokumen ini adalah **ringkasan master**. Detail ada di berkas yang ditautkan di §10.

---

## 1. Pertanyaan riset

1. Apakah metode CAROM Air (drone, keypoint + model bentuk) dapat diadaptasi untuk mengukur dimensi kendaraan dari CCTV statis?
2. Komponen mana yang transfer, mana yang tidak?
3. Akurasi apa yang realistis untuk panjang, lebar, dan tinggi?
4. Apakah standar kontainer bisa menjadi ground truth tanpa pengukuran lapangan?

## 2. Putusan saat ini

| Aspek | Status | Angka |
|---|---|---|
| Geometri/parameterisasi | **terbukti (self-consistency)** | MAPE 0,36% dengan 8 sudut GT; **`veh_size` preset**, bukan ukur fisik |
| Kalibrasi SVLD | **terverifikasi** | median reproyeksi 0,74 px |
| GeoCalib | **tidak reliabel di SVLD** | 1/5 scene; 20/100 citra; multi 1/5 |
| VP jalan | **kuat jika f benar** | 95/100 (f GT), 47/100 (f GeoCalib); yaw tersedia |
| AnyCalib | **tidak membantu f** | 6/100; median 18,2% |
| Fusi `f` Geo+Any (SVLD GT) | **gagal buta; berguna setelah anchor** | 17/100 vs GeoCalib 20/100; korelasi galat 0,93; anchor 1 frame/kamera → MAE 4,28%, 71/95 |
| Geolokasi CCTV Bina Marga | **provisional, bukan survei** | 258 kamera; 222 koordinat; Dalam Kota 26; offset vs OSM median 21,8 m, maks 133,4 m |
| Cakupan street view KartaView | **cakupan baik, matching gagal** | 26/26 usable 2020 `PLANE`; panorama Cawang 2023 210 m; ~25 SIFT/12 LoFTR |
| Dash + garis solid | **menjanjikan, bersyarat** | BELMERA `f=811,6` (w=3,6); fixed-f RMS 1,674 vs 0,320; `w` dan standar dash dominan |
| Lane fit f | **belum berhasil** | 0/45; lane extraction |
| Vertical VP otomatis | **belum layak** | 0cam 2/20; 1cam 4/18 |
| GlobustVP | **tidak turnkey** | vertikal 24–35°, 0 inlier |
| Lebar/tinggi (mask) | **layak screening** | W 7,1%, H 7,6% |
| Panjang (mask) | **belum layak** | L 21,9% |
| Keypoint zero-shot | **belum cukup** | Car 44,1%, Bus 0% |
| Container-only 20 ft | **tervalidasi** | 6,046 vs 6,058 m (−0,2%) |
| Container-only 40 ft | **ambigu** | 13,99 m; 40 ft +14,7%, 45 ft +2,0% |

**Klaim yang sah:**

> "Kerangka geometri CAROM Air dapat diadaptasi untuk mengukur lebar dan tinggi dari CCTV statis; dengan titik 2D yang akurat, geometri mencapai <1%, dan mask-based memberi ~7% untuk W/H. Panjang tidak dapat diandalkan dari satu pandangan head-on; dibutuhkan sisi kendaraan, multi-frame, atau multi-kamera."

**Klaim yang tidak sah:**

> "CAROM Air dapat mengukur L/W/H dari CCTV dengan akurasi 10%."

---

## 3. Temuan teori penting

### 3.1 Anisotropi galat

$$
\sigma_{\text{lateral}}=\sqrt2\,\frac{z}{f}\sigma_{px},
\qquad
\sigma_{\text{kedalaman}}=\sqrt2\,\frac{z^2}{fh}\sigma_{px}
$$

Rasio anisotropi:

$$
\frac{\sigma_{\text{kedalaman}}}{\sigma_{\text{lateral}}}=\frac{z}{h}
$$

Tidak bergantung pada focal length atau resolusi. Pada Cawang ($h=8{,}876$ m, $\sigma_{px}=1{,}5$):

| Jarak | Lateral | Longitudinal | Anisotropi |
|---:|---:|---:|---:|
| 20 m | 3,9 cm | 8,8 cm | 2,2× |
| 30 m | 5,9 cm | 19,8 cm | 3,4× |
| 40 m | 7,8 cm | 35,2 cm | 4,5× |
| 50 m | 9,8 cm | 55,0 cm | 5,6× |

### 3.2 Degenerasi kalibrasi

Dari marka jalan saja, transformasi

$$
(f,\theta,h,w,Y_0)\longmapsto
\left(\lambda f,\frac{\theta}{\lambda},\frac{h}{\lambda},\frac{w}{\lambda},\frac{Y_0}{\lambda}\right)
$$

tidak mengubah citra. Yang terukur hanya $f\theta$, $fh$, $fw$, dan $w/h$. Satu anchor metrik wajib.

### 3.3 Batas panjang

Panjang tidak teramati bila sumbu optik hampir sejajar jalan. Ini bukan soal algoritma; informasi geometrinya tidak ada. Solusi: sisi kendaraan terlihat (kamera miring), multi-frame, atau multi-kamera.

### 3.4 Lima titik cukup

Dengan 4 kontak tanah + 1 sudut atap, MAPE 0,48%; 8 sudut 0,36%. Detektor tidak perlu 8 sudut box.

### 3.5 Standar kontainer

ISO 668: 20 ft = 6,058 m; 40 ft = 12,192 m; 45 ft = 13,716 m; lebar 2,438 m; tinggi 2,591 m (standar) / 2,896 m (high cube). Ini GT sah **untuk kontainer**, bukan truk total.

---

## 4. Temuan eksperimen

### 4.1 Kalibrasi Cawang REV2

| Parameter | Nilai |
|---|---:|
| $f$ | 1082,6 px |
| pitch | 2,432° |
| yaw | 0,271° |
| $h$ | 8,876 m |
| $w$ (anchor) | 3,60 m (asumsi; divalidasi 20 ft Cawang −0,2%) |
| RMS | 1,097 px |

> **Catatan 20 November 2026:** `w=3,60 m` adalah **asumsi**, bukan pengukuran. Hasil Cawang ini hanya valid relatif terhadap anchor tersebut. **Kontainer 20 ft TEMA (6,046 vs 6,058 m, −0,2%) memvalidasi skala 3,6 m di Cawang**; secara linear memberi `w_est ≈ 3,60 m`; 40 ft SINKOR tetap ambigu 40/45 ft. Data SVLD memberi lebar lajur **2,7–3,56 m**; 3,6 m tidak universal. Untuk lokasi lain, ukur lebar lajur aktual sebelum memakai `h`/skala absolut. Detail: `reports/cawang-container-anchor/README.md`.

Empat set parameter (A–D) memfit citra hampir sama; perbedaan proyeksi maksimum 1,37 px. Kalibrasi geometrik berhasil, identifikasi parameter tidak.

### 4.2 GeoCalib

- Rekaman 480×360: $f=616\pm30$ px, pitch 12,1°; VP 11,0° → selisih 1,1°.
- SVLD 5 scene: hanya **1/5** lulus f<5% dan pitch<2°; f meleset 2,1-51,0%, pitch 0,81-4,99°. Uji 100 citra (10 test + 10 trainval/scene): **20/100 lulus**, median Δf **14,9%**, Δpitch **3,03°**; multi 1/5. Detail: `reports/svld-geocalib/README.md`.
- Cawang 720p (median2): f=943,3 px, pitch 1,995°; multi-frame shared f=969,6. Terhadap dash fit (f=1082,6; RMS 1,097 px), GeoCalib 9–13% terlalu rendah; RMS fixed-pose 3,1–4,4 px. Varian distorted+radial f=890,3. **Bukan pengganti f atau pitch dash.**
- AnyCalib (Cawang): f bergantung frame, 1100–1207 px; frame TEMA 1100 px (+1,6%, RMS 1,215 px), median2 1183 px (+9,3%). Berguna sebagai cek independen per frame, bukan kalibrasi tunggal. Detail: `reports/calib-compare/README.md`.
- **VP jalan** 100 citra: dengan `f` GT **95/100** lulus pitch/yaw <2° (median 0,20°/0,05°); dengan `f` GeoCalib **47/100** (median 2,46°/1,12°). Median VP per scene: **5/5** dengan f GT (maks 0,43°/0,14°), 2/5 dengan f GeoCalib. VP memberi **yaw** yang tidak dimiliki GeoCalib; `f` adalah bottleneck. `1cam` 4/20 outlier per frame. Detail: `reports/svld-vp/README.md`.
- **AnyCalib** 100 citra: **6/100** lulus Δf<5% (median 18,2%); VP + AnyCalib **34/100**. `f` dari pitch GeoCalib + VP juga gagal (median 21,6%). Detail: `reports/svld-calib-fusion/README.md`.
- **Fusi `f` GeoCalib+AnyCalib vs GT SVLD (26 Nov):** 50/50 memberi MAE **19,53%**, **17/100** lulus 5% — lebih buruk dari GeoCalib (19,35%, 20/100). Rasio estimasi/GT 0,807 (Geo) dan 0,830 (Any), korelasi galat **0,929**, jarak antar-model hanya 7,05%: kedua model bias ke arah yang sama, berbeda dari Cawang. Setelah **skala per kamera di-anchor dengan satu frame ber-`f`**, 50/50 memberi MAE **4,28%** dan **71/95** lulus sebagai ukuran **stabilitas relatif** (bukan `f` absolut); per scene `session0_right` 1,07%, `session0_centre` 1,69%, `1cam` 1,89%, `session6_right` 6,81%, `0cam` 9,96%. Detail: `reports/svld-calib-fusion/fusion-gt-2026-11-26.md`.
- **Lane fit** (3 garis + lebar lajur): identifiabel di sintetis (f/h pulih sempurna), tetapi **0/45** citra SVLD lulus; RMS 11–139 px. Bottleneck lane extraction/assignment, bukan matematika.
- **Vertical VP / gravitasi**: VP sejati dari GT memberi f exact; `vanishPoints` tersimpan error 2,5–26%; gravitasi GeoCalib + VP hanya `session0_centre` (20/20, 0,8%), overall 20/100. Garis vertikal otomatis LSD: 0cam 2/20 OK, 1cam 18/20 tapi hanya 4/18 lulus; sudut vs gravitasi 35–43°. **GlobustVP**: 0cam 2/3, 1cam 3/3, tetapi vertikal 24–35° dan 0 inlier; SCS tanpa MOSEK lambat/tidak stabil. Belum layak; perlu manual/deep VP.
- **PerspectiveFields (CVPR 2023)**: f rasio 0,328 (0cam), 0,952 (1cam), 0,691/0,582/0,576 (session); VP vertikal 51-83 deg; hanya 1cam 11/20 lulus 5%. Model punya prior vFoV ~30-33 deg, gagal untuk lensa tele 10-14 deg.
- **Vehicle VP / deep_vp**: konsep dua VP horizontal ortogonal dari kendaraan tepat, tetapi bobot pretrained OneDrive login dan tidak ada mirror. VP dari box 50 px SVLD noise (median 1,7-20 deg); f dari pasangan VP panjang-lebar jauh dari GT.
- **3D box PnP**: 8 sudut box + dimensi memberi f 0,00-0,05% (joint per citra) dan 0,06-0,21% (satu objek) pada box GT; sensitivitas 1 px/3% dimensi/0,3 m/2 deg -> 1,86%. Butuh detektor 3D akurat; `yolo3Dbbox` lama meleset median H 20%, W 7%, L 15% (truk/bus lebih buruk). Catatan: hanya dimensi + 8 sudut 2D (tanpa posisi world) ambigu; 1cam/session0 bisa salah minimum. Detail: `reports/svld-vehicle-vp/README.md`.
- **Depth Pro (ICLR 2025)**: f rasio 0,979 (session0_centre), 0,870 (1cam), 0,652 (session6_right), 0,546 (0cam), 0,441 (session0_right); hanya 1 scene <5%; CPU 3-5 menit/citra.
- **Survey 3D detector**: CenterLoc3D (khusus SVLD-3D, MIT, tanpa pretrained weight), BEVHeight++/CoBEV (pretrained roadside, GPU), Pro3D (SOTA 2026, code/ckpt belum), MonoDGP/MonoDETR (KITTI, domain beda), 3D-MOOD (open-set, bisa CPU via LibreYOLO). Detail: `reports/3d-detector-survey/README.md`. Model f generik tetap tidak bisa menggantikan kalibrasi per-kamera.
- **Lebar lajur SVLD tidak universal 3,6 m**: estimasi kendaraan 2,7–3,25 m; marka 3,0–3,56 m. Untuk skala absolut, ukur per lokasi; jangan pakai 3,6 m buta.
- Kesimpulan: GeoCalib/AnyCalib berguna sebagai pembanding, tetapi **wajib divalidasi per scene**. Jangan jadikan satu-satunya sumber $f$. f harus dari geometri/known camera/anchor.

### 4.2.1 Combo GeoCalib + AnyCalib + VP + anchor lebar jalan

Komponen ini cukup untuk membentuk homografi metrik, tetapi **belum cukup jika hanya ditempel** (f model + VP mentah + w=3,60 + langsung hitung H).

- `f` GeoCalib di Cawang 943–980 px (9–13% terlalu rendah); AnyCalib 1100–1207 px tergantung frame.
- **Fusi `f` 50/50 GeoCalib+AnyCalib (8 median temporal Cawang, 26 Nov):** MAE **1,58%**, maks **3,92%**, **8/8** lulus gerbang 5%; bobot optimal `0,470 Geo / 0,530 Any`, koreksi skala `1,006`, LOO MAE `1,80%`. Ini terjadi karena bias GeoCalib `−13,1%` dan AnyCalib `+11,4%` hampir sama besar dan berlawanan arah — **spesifik Cawang**, bukan sifat umum. Di GT SVLD fusi buta hanya **17/100** vs GeoCalib 20/100; rasio 0,807/0,830 dan korelasi galat 0,929 (bias searah). Setelah skala per kamera di-anchor, ensemble hanya mengukur **stabilitas relatif**: MAE **4,28%**, **71/95** lulus; `f` absolut tetap dari anchor. Detail: `reports/calib-compare/fusion-2026-11-26.md` dan `reports/svld-calib-fusion/fusion-gt-2026-11-26.md`.
- VP dari garis (`vpfit`) beda 0,21° pitch dan 0,34° yaw dari dash fit; RMS fixed pose 1,333 px vs 1,101 px.
- `w=3,60 m` masih asumsi; error skala ±4% menjadi sekitar ±9 cm pada 30 m. **Cawang 20 ft TEMA 6,046 (−0,2%) mendukung 3,6 m di lokasi ini**; 40 ft SINKOR ambigu 40/45 ft. Data SVLD: lebar lajur **2,7–3,56 m**; untuk lokasi lain, ukur per lokasi.
- GeoCalib melihat roll −0,54°; model dash Cawang mengabaikan roll. Bisa jadi superelevasi nyata, bukan sekadar error model.

Syarat agar combo ini cukup:

1. pilih `f` dengan gerbang/median 5–10 frame; jangan percaya satu frame;
2. VP dari garis sejajar/tepi jalan/vehicle VP yang bersih, robust terhadap bayangan dan lengkung;
3. anchor `w` atau `h` diukur, bukan diasumsikan;
4. joint fit `f, pitch, yaw, roll, h` dengan prior, bukan plug-and-play;
5. validasi reproyeksi ≤1–2 px dan cek `h` independen;
6. ground truth lokal sebagai gerbang akhir.

**Putusan:** cukup untuk screening/kalibrasi awal; belum untuk penegakan ODOL. Untuk Cawang, dash fit + anchor `w` tetap yang utama. Detail: `reports/calib-compare/README.md`.

**Uji video LearnPinhole (480x360):** GeoCalib multi f=501,8 cocok baseline 502; VP pitch/yaw 4,91/-1,66 cocok baseline 4,86/-1,75; AnyCalib median 528,2 (+5,2%, range 510-598); anchor lebar jalan tidak stabil karena jalan melengkung dan batas kanan keluar frame, sehingga anchor Avanza tetap lebih tepat. Detail: `reports/learnpinhole-video/README.md`.

### 4.2.2 Dataset kalibrasi yang tersedia

- **SVLD-3D**: `f`, `h`, pitch, yaw; **tanpa roll** dan distorsi; test set publik 2.237 gambar. Cocok untuk uji cepat `f/pitch/yaw/h`.
- **I24-3D**: `P`, `H`, `H_inv`, `vps`, `corr_pts`, `space_pts`, `curve`; `f/h/yaw/pitch/roll` diturunkan dari `P`. **Data lengkap 50,04 GB sudah diperiksa 19 Nov 2026**: RQ(`P`) **bukan** GT fisik (kolom-Z ad hoc; `f` EB vs WB beda median 7,1%); kamera 28–45 m dan bukan side-view. Lihat `reports/i24-3d-kalibrasi/README.md`.
- **I24V**: 234 kamera 1080p, 234 jam; `H`/`P` static/dynamic; fokus tracking, bukan pengganti I24-3D; lebih besar.
- **CUTC**: checkerboard/ChArUco, GT paling bersih; **RoScenes**: multi-kamera roadside.
- Repo `I24-MOTION/I24-3D-dataset` adalah **toolkit** (`homography.py`, `scene.py`, `export_dataset.py`), bukan dataset. Detail dan link: `reports/DATASET-KALIBRASI.md`.

### 4.2.3 Geolokasi CCTV Bina Marga dan cakupan street view (27 Nov)

- **258 kamera** Bina Marga di 16 ruas: **222** berkoordinat, **206** punya KM, **166** memakai koordinat existing, **56** diinterpolasi dari KM + centerline OSM, **20** di-clamp.
- **Tol Dalam Kota (Cawang–Pluit): 26 kamera**, semuanya berkoordinat. **21** `provisional_stationing` (KM + A/B), **5** `interpolated_km`; **17 KM unik**. Offset koordinat existing terhadap centerline OSM **median 21,8 m, maks 133,4 m**.
- **KartaView 26/26 kamera** punya citra usable dalam radius 300 m; jarak **median 2,1 m, maks 6,5 m**; semua **2020-05/06, proyeksi `PLANE`** (perspektif, bukan equirect).
- **Panorama Cawang 2023** (ID `1838190345`, 5760×2880 equirect) berada **210,05 m** dari koordinat sementara KM 00+400. Matching ke frame CCTV hanya **~25 inlier SIFT** (FOV 100°, pitch −20°, yaw 0°) dan **~12 inlier LoFTR** (FOV 120°, conf 0,2).
- Angka **115/158 inlier** sebelumnya **tidak valid**: thumbnail 1280×720 adalah pandangan perspektif (HFOV ≈120°), bukan equirect. Korelasi thumbnail dengan crop panorama yaw 0/FOV 120 adalah 0,886, jadi thumbnail itu crop dari panorama.
- **Putusan:** street view berguna untuk verifikasi kasar ruas/arah, jumlah lajur, dan prior VP; **bukan** sumber `f`/pose atau anchor metrik. Jarak 210 m + perubahan scene 2023→2026 terlalu besar untuk matching yang reprodusibel.
- Detail: `reports/cctv-geolocation-2026-11-27/README.md`.

### 4.2.4 Dash + garis solid: memutus degenerasi `f` (27 Nov)

- **Dash-only BELMERA tetap degenerate.** Free fit `f=1101,09`, RMS `0,320 px`; memaku `f=989,11` memberi RMS `0,320 px` juga. Pola dash hanya menentukan rasio, bukan skala absolut.
- **Garis solid satu lebar lajur memutus degenerasi.** BELMERA (garis kuning median, `w=3,6 m`, period 13 m/dash 5 m): `f=811,55`, pitch `15,551°`, yaw `−0,106°`, `h=10,438 m`, RMS `0,439 px`.
- **Fixed-f RMS:** `f=989,11` → `1,674 px`; `f=1101,09` → `2,469 px`. Scan `f` minimum di ~810. Kovarians statistik `8,76 px` (`1,08%`), tetapi ini hanya noise piksel.
- **Lebar lajur dominan:** `w=3,0 → f=985,3`; `3,3 → 890,8`; `3,6 → 811,6`; `3,9 → 744,1`. Perubahan ±0,3 m menggeser `f` ~8–10%.
- **Standar dash juga dominan:** period 13,333 m/dash 5 m → `f=826,3` (RMS 0,488); period 8 m/dash 3 m → `f=462,2` (RMS 0,488). Keduanya rasio 0,375; citra tidak bisa membedakan tanpa konteks situs. Tol → 5 m; jalan kota → 3 m.
- **Stabilitas:** near-only 809,3 vs far-only 819,0 (beda 1,2%); sisi salah memberi RMS 42,9. Garis putih tepi kiri dengan offset +2 memberi `f=412,9`, pitch 33°, `h=21 m` — tidak konsisten; jangan pakai batas yang jumlah lajurnya tidak pasti.
- **BORR tidak valid:** solid memutus degenerasi secara prinsip (`f=987,16`; fixed `f=1663,67` RMS 3,500 vs 1,436), tetapi `u` dash naik 324→494 terhadap jarak — jalan melengkung. Model garis lurus tidak berlaku.
- **Putusan:** garis solid adalah tambahan yang berguna untuk situs lurus dengan satu dash + satu solid, tetapi `f` hanya identifiabel **bersyarat** pada `w` dan standar dash. Belum ada klaim akurasi absolut; perlu uji terhadap GT SVLD dan pengukuran `w` per situs.
- Detail: `reports/cctv-solid-line-2026-11-27/README.md`.

### 4.3 SVLD-3D

- Test set: 2.237 citra, 8.142 objek; **7.396 Car, 745 Bus, 1 Truck**.
- Trainval (baru): 14.592 citra, 39.477 objek; **37.611 Car, 1.166 Bus, 700 Truck**; 5 scene, kalibrasi median **0,73–0,84 px**, maks 1,11, 0 objek >2 px.
- Kalibrasi: `f`, `fi` = pitch, `theta` = yaw, `h` mm.
- Reproyeksi test 8.142 objek: median **0,74 px**, p90 0,85, maks 1,08, 0 objek >2 px.
- **`veh_size` adalah preset, bukan pengukuran**: 1.164/1.166 Bus trainval `L=12,60 m`; test Bus `12,00/9,46 m`; 184 Truck `L=20,00 m`. MAPE fit adalah self-consistency, bukan akurasi fisik. Detail: `reports/svld-trainval/README.md`.
- Kamera SVLD menghadap jalan (sudut 4–29°), **bukan side-view**; tidak bisa memvalidasi panjang.

### 4.4 Geometri 50 objek (self-consistency)

26 Car + 24 Bus, jarak 13,5–122,9 m, input 8 sudut 2D GT. **Bukan akurasi fisik**: `veh_size` adalah preset, dan 2D/3D box dibangun dari dimensi yang sama.

| Metrik | Mean | Median | p90 | Max |
|---|---:|---:|---:|---:|
| MAPE LWH | **0,36%** | 0,23% | 0,81% | 1,18% |
| L | 0,65% | 0,36% | 1,59% | 3,16% |
| W | 0,15% | 0,12% | 0,33% | 0,44% |
| H | 0,30% | 0,23% | 0,53% | 1,25% |
| RMS | 0,35 px | 0,35 px | 0,41 px | 0,46 px |

**Kendaraan well-known bukan anchor independen.** `veh_size` SVLD adalah preset dan `vertex2d` adalah proyeksi box preset. Contoh: bus Higer KLQ6129 (kelas 12 m) di `real_scene_cam0_003368` diberi 12,6 × 2,75 × 2,8 m; kelas 12 m biasanya ≈12,0 × 2,55 × 3,2 m. Uji anchor yang sah butuh datasheet model/year + anotasi manual 8 sudut/5 titik, 3–5 instance; perkiraan 3–5%, tidak sebaik container 20 ft Cawang (0,2%). Detail: `reports/svld-vehicle-anchor/README.md`.

### 4.5 Sensitivitas noise

| $\sigma$ | MAPE | Gagal |
|---:|---:|---:|
| 0 | 0,36% | 0% |
| 1 px | 1,05% | 0% |
| 2 px | 1,91% | 0% |
| 3 px | 2,79% | 1,7% |
| 5 px | 4,57%* | 63,2% |

\* hanya 37% berhasil.

**Target keypoint: ≤3 px.**

### 4.6 Subset sudut

| Subset | MAPE | Gagal |
|---|---:|---:|
| 8 sudut | 0,36% | 0 |
| 6 sudut | 0,46% | 0 |
| **5 sudut** | **0,48%** | **0** |
| 4 kontak tanah | 2,39% | 1 |
| 4 sudut atap | 3,04% | 0 |
| 2 tanah + 2 atap | 4,27% | 0 |

### 4.7 Keypoint zero-shot

Model `vehicle-keypoints` (YOLO26-pose, 14 keypoint, MIT), 20 citra SVLD, 72 objek GT.

| Kelompok | GT | Cocok | 5/5 di antara cocok | 5/5 dari semua GT |
|---|---:|---:|---:|---:|
| Semua | 72 | 41 (56,9%) | 63,4% | 36,1% |
| Car | 59 | 33 (55,9%) | 78,8% | 44,1% |
| Bus | 13 | 8 (61,5%) | 0% | 0% |

### 4.8 Mask-based

YOLO11n-seg, 21 objek.

| Kelompok | n | MAPE | L | W | H | IoU |
|---|---:|---:|---:|---:|---:|---:|
| Semua | 21 | 12,19% | 21,92% | 7,11% | 7,55% | 0,796 |
| Car | 12 | 12,86% | 22,20% | 8,07% | 8,32% | 0,780 |
| Bus | 9 | 11,30% | 21,56% | 5,83% | 6,51% | 0,820 |

### 4.9 Cawang side-view / time-of-passage

Lower envelope mask + VP direction + back-projection ground.

| t (s) | Lane | Median L | Tafsiran |
|---:|---|---:|---|
| 32 | far | 11,56 m | 20 ft / box truck |
| 86 | far | 14,63 m | 40 ft container + kabin |
| 247 | near | 6,44 m | box truck kecil |
| 431 | far | 16,74 m | truk panjang |
| 567 | far | 17,37 m | truk panjang |
| 578 | near | 14,69 m | 40 ft container |

Truk SINKOR 40 ft: 14,04 m median (13,71–15,22); kecepatan 61,2 km/jam. Kontur mentah memberi 15,9 m — terlalu panjang.

Kecepatan batch 7–119 km/jam: **tidak stabil**, baseline 0,8 s terlalu pendek.

### 4.10 Grounded SAM 2 container-only

Grounding DINO tiny + SAM 2.1 tiny.

- Prompt teks `"shipping container."` → box mencakup kabin; mask whole-truck.
- Box prompt kontainer `[255,475,405,645]` → mask container-only 21.907 px; 0 piksel hijau (kabin); 75,2% piksel merah (kontainer).
- Fit 3D box dengan H=2,591:

| Kontainer | Standar | Fit | Galat | IoU |
|---|---:|---:|---:|---:|
| 20 ft TEMA | 6,058 m | **6,046 m** | **−0,2%** | 0,972 |
| 40 ft SINKOR | 12,192 m | 13,990 m | +14,7% | 0,741 |
| 40 ft SINKOR (jika 45 ft) | 13,716 m | 13,990 m | +2,0% | 0,741 |

20 ft TEMA adalah **validasi GT pertama yang bersih**. 40 ft SINKOR ambigu tipe.

---

## 5. Kesalahan dan koreksi

| # | Kesalahan | Dampak | Koreksi | Status |
|---:|---|---|---|---|
| 1 | REV1 mengklaim $f,h,w$ terukur | kalibrasi tidak sahih | REV2: degenerasi 1-parameter | selesai |
| 2 | Memakai `16-15-44.mp4` 480×360 @115 kbps | tidak layak ukur | audit; rekomendasi main stream | selesai |
| 3 | Menganggap CenterLoc3D 85% = 15% per sumbu | salah tafsir akurasi | 85% = jumlah 3 sumbu ≈15%, rata-rata ≈5% | selesai |
| 4 | Menganggap `theta` SVLD = pitch | kalibrasi tertukar | `fi` = pitch, `theta` = yaw | selesai |
| 5 | Endpoint kontur mentah | 40 ft jadi 15,9 m | lower envelope → 14,0–14,3 m | selesai |
| 6 | Container-only pakai mask warna | 13,81 m vs 12,19 (+13,3%) | SAM2 box prompt container-only | selesai |
| 7 | YOLO26-seg dianggap lebih baik | 17,5 m vs 14,04 m | tetap YOLO11/lower envelope | selesai |
| 8 | Prompt teks SAM2 mencakup kabin | mask whole-truck | box prompt kontainer-only | selesai |
| 9 | Kecepatan dari baseline 0,8 s | 7–119 km/jam | jangan pakai kecepatan; panjang lebih stabil | terbuka |
| 10 | `P` I24-3D dianggap 4×3 | potensi transpose salah | data nyata 3×4; parser menerima keduanya; ground RMS median 3,89 px | selesai |
| 11 | GeoCalib dipercaya tanpa cek | f salah di 4/5 SVLD | gerbang pitch vs VP | selesai |
| 12 | OpenPifPaf dianggap bisa langsung | build gagal (MSVC/torch 1.13.1) | ganti `vehicle-keypoints` | selesai |
| 13 | GSNet dianggap punya bobot | bobot pretrained dihapus | fitting manual; data ApolloCar3D NC | terbuka |
| 14 | SVLD dianggap punya truk | test hanya 1 Truck | trainval 700 Truck (dimensi preset); I24-3D/RoScenes | selesai |
| 15 | SVLD dianggap bisa uji panjang | kamera 4–29° (rear/front) | butuh data side-view | selesai |
| 16 | 40 ft SINKOR dianggap 40 ft | bisa 45 ft | perlu identifikasi tipe | terbuka |
| 17 | Ambiguitas 2 vs 3 lajur ATP | skala bisa 1,4× | belum diselesaikan | terbuka |
| 18 | Truk ATP 2,1 m vs harapan 2,6–2,9 m | galat 25–30% | hipotesis lajur/segmentasi | terbuka |

---

## 6. Kendala

| Kendala | Dampak | Status / workaround |
|---|---|---|
| Tanpa multi-kamera | panjang sulit | side-view 1 kamera, multi-frame, atau kamera miring |
| Tanpa plat | tidak bisa lookup dimensi | pure pixel; standar kontainer |
| Tanpa GPU | training/fine-tune lambat | CPU inference; model siap pakai |
| I24-3D bukan GT f/pose | gerbang kalibrasi tidak bisa dijalankan | pakai SVLD/pengukuran lapangan; I24 untuk GT dimensi/ground-plane |
| Situs I24-3D menolak `curl` (WAF) | otomasi gagal | data 50,04 GB sudah diunduh via browser; tidak perlu curl |
| Tanpa GT lokal Indonesia | klaim akurasi terbatas | SVLD/Cawang proksi; field test |
| Cawang pitch 2,43° | degenerasi terburuk | ukur anchor lebar lajur; 3,60 m hanya asumsi |
| Jalan Cawang melengkung | galat sistematis | batasi segmen lurus |
| Kalibrasi Cawang tanpa GT | hanya konsistensi | standar kontainer 20 ft |
| Anchor 3,6 m diasumsikan | skala bisa salah 5%+ | Cawang 20 ft valid −0,2%; lokasi lain ukur lajur; SVLD 2,7-3,56 m |
| Geolokasi CCTV hanya provisional | posisi kamera bisa meleset puluhan meter | KM + OSM + arah A/B; verifikasi street view; bukan survei |
| Street view jauh dari kamera | matching lemah, pose tidak stabil | Cawang 2023 210 m; ~25 SIFT/12 LoFTR; jangan pakai untuk `f` |
| Lebar lajur tidak diukur | `f` dash+solid bergeser ~8–10% per ±0,3 m | ukur per situs; satu kendaraan/landmark; jangan pakai 3,6 m buta |
| Standar dash 3 m vs 5 m ambigu | `f` bisa berbeda ~1,8× | konteks situs (tol vs kota); ukur marka; butuh model skala absolut |
| Garis solid hanya untuk segmen lurus | jalan melengkung (BORR) gagal | batasi segmen lurus; model lengkung atau homografi lokal |
| Mask body tanpa ban | panjang bias | lower envelope; SAM2 container-only |
| Kecepatan tidak stabil | time-of-passage mentah | track lebih panjang; garis crossing |
| Lisensi non-komersial | tidak untuk produk | validasi riset; data sendiri |
| SVLD test hanya 1 Truck | truk tak teruji | trainval 700 Truck (tapi `veh_size` preset); I24-3D/RoScenes |
| 40 ft ambigu 40/45 | GT tidak pasti | identifikasi tipe/kode kontainer |
| Kontainer di atas sasis | back-projection ground salah | tinggi standar + 3D fit |
| Kamera SVLD bukan side-view | tak bisa validasi panjang | side-view Cawang/pengukuran lapangan; **I24-3D juga aerial/nadir**, bukan side-view |

---

## 7. Pertanyaan terbuka

1. **2 vs 3 lajur ATP** — apakah jalan itu 2 atau 3 lajur? Skala bisa berubah 1,4×.
2. **40 ft SINKOR** — 40 ft atau 45 ft? Perlu identifikasi tipe.
3. **Generalisasi 20 ft** — apakah 3–5 kontainer 20 ft lain juga memberi 6,0–6,2 m?
4. **Detektor 5 titik** — apakah ada model yang mencapai ≤3 px pada mobil dan bus?
5. **Time-of-passage murni** — apakah $L=v\Delta t$ lebih stabil daripada side-view?
6. **Multi-frame 1 kamera** — apakah sudut pandang berubah cukup untuk panjang?
7. **Truk/bus side-view GT** — side-view Cawang atau field test; I24-3D bukan side-view (aerial/nadir), tetapi memberi GT dimensi 3D.
8. **Validasi Indonesia** — satu kendaraan diukur dengan meteran.
9. **Metrologi legal** — sertifikasi alat, ketertelusuran.
10. **Lisensi model** — OpenPifPaf AGPL, data NC; jalur produksi belum jelas.
11. **Akurasi `f` dash + solid terhadap GT SVLD** — apakah metode ini bisa <5% pada citra SVLD yang punya satu dash + satu solid?
12. **Lebar lajur aktual per CCTV** — bisakah diukur tanpa survei (kendaraan known-width, marka lain, atau container)?
13. **Distorsi radial CCTV** — seberapa besar `k1`, dan apakah near/far konsisten di kamera selain BELMERA?
14. **Batas street view** — apakah ada citra street-level dalam 10–20 m dari kamera Cawang, atau perlu survei manual?

---

## 8. Riset dan sumber penting

| Sumber | Kontribusi | Catatan |
|---|---|---|
| CAROM Air (Lu dkk., ICRA 2023) | keypoint + model bentuk, EKF, drone | weak perspective; tidak transfer langsung ke CCTV |
| CAROM (Lu dkk., ICRA 2021) | infrastruktur, mask + tangent hull | pendahulu untuk CCTV |
| GeoCalib (Veicht dkk., ECCV 2024) | f, pitch, roll dari 1 citra | 1/5 scene; 20/100 citra; wajib cek VP |
| SVLD-3D / CenterLoc3D (Tang dkk.) | 2.237 citra, GT L/W/H, kalibrasi | truk hanya 1; kamera rear/front |
| I24-3D (Gloudemans dkk., BMVC 2023) | 16–18 kamera, 877k box, P/H/VP | data tersedia; **bukan GT f/pose** (P z-scale ad hoc); aerial 28–45 m, bukan side-view |
| SKoPe3D (Pahadia dkk., ITSC 2023) | 25k CARLA, 33 keypoint, side CCTV | tidak ada bobot pretrained |
| GSNet (Ke dkk., ECCV 2020) | 79 mesh + PCA | bobot dihapus; data NC |
| OpenPifPaf | 24/66 keypoint | build gagal di Windows; AGPL |
| vehicle-keypoints | YOLO26-pose 14 keypoint | zero-shot Car 44,1%, Bus 0% |
| Grounding DINO + SAM 2 | container-only via box prompt | 20 ft −0,2%; 40 ft ambigu |
| TRUDI/TITUS (BMVC 2025) | 11.109 container, 2.780 trailer | CC BY-SA; MMDetection |
| naver/cctv (ICCV 2021) | kalibrasi dari track box | skala dari prior; sirkular untuk ODOL |
| MoGe-2 (NeurIPS 2025) | metric point map | wildcard; belum diuji |
| RoadTagger (AAAI 2020) | lane count dari satelit | 77%; untuk banyak ruas |
| ISO 668 | standar kontainer | 20/40/45 ft |

---

## 9. Peta berkas

| Berkas | Isi |
|---|---|
| `RISET-CAROM-Air-untuk-CCTV.md` | laporan riset utama |
| `SOP-KALIBRASI-CCTV.md` | SOP kalibrasi (GeoCalib §0.3, degenerasi §5) |
| `SOP-PENGUKURAN-DIMENSI-KENDARAAN.md` | SOP pengukuran L/W/H |
| `KALIBRASI-CCTV-CAWANG-REV2.md` | kalibrasi Cawang yang berlaku |
| `AUDIT-16-15-44.md` | studi kasus rekaman tidak layak |
| `PAPER-REPO-Untuk-Menutup-Kelemahan.md` | peta paper/repo |
| `PLAN-PENUTUPAN-KELEMAHAN.md` | rencana penutupan kelemahan per fase |
| `VALIDASI-PROTOCOL.md` | protokol dan ambang |
| `HASIL-VALIDASI-SVLD.md` | sintesis SVLD |
| `HASIL-TIMEPASS-CAWANG.md` | side-view, 20 ft, 40 ft |
| `CATATAN-RISET-LENGKAP.md` | dokumen ini |
| `reports/` | artefak validasi (lihat `reports/README.md`) |
| `reports/external-setup.md` | environment GeoCalib, YOLO, Grounded SAM 2 |
| `clips/` | klip bukti video tanpa re-encode (lihat `clips/README.md`) |
| `scripts/` | 14 skrip validasi (lihat `scripts/README.md`) |

Skrip penting:

| Skrip | Fungsi |
|---|---|
| `svld_reproj_check.py` | verifikasi kalibrasi SVLD |
| `svld_fit_dims.py` | fit 3D box; test 50 objek, trainval 120 Truck + 174 Bus (`--classes`) |
| `svld_sensitivity.py` | sensitivitas noise |
| `svld_perspective_fields.py` | PerspectiveFields 100 citra; f/vFoV/VP vertikal |
| `svld_vehicle_vp_check.py` | VP dari 8 sudut box kendaraan SVLD |
| `svld_box_calib.py` | PnP kamera dari box 3D kendaraan (f/phi/theta/h) |
| `svld_box_calib_sensitivity.py` | sensitivitas noise 2D/dimensi/posisi/yaw |
| `svld_box_calib_scene.py` | agregasi banyak box per scene |
| `box_pnp_calib.py` | tool PnP reusable dari 8 titik 3D world-space |
| `box_pnp_known_dims.py` | eksperimen box lokal (dimensi + 8 sudut; ambigu) |
| `svld_box_known_dims_eval.py` | evaluasi box lokal pada 50 objek SVLD |
| `svld_yolo3d_selfcal.py` | uji self-cal `yolo3Dbbox` |
| `svld_yolo3d_dims.py` | bandingkan dimensi prediksi `yolo3Dbbox` vs GT |
| `svld_depthpro.py` | uji f Depth Pro (CPU) |
| `train_centerloc3d_colab.py` | training CenterLoc3D + AMP + checkpoint/resume |
| `make_centerloc3d_txt.py` | generate annotation lines SVLD, skip gambar hilang |
| `patch_centerloc3d.py` | patch NumPy 2/PyTorch 2 untuk CenterLoc3D |
| `make_colab_notebook.py` | generator notebook Colab |
| `svld_subsets.py` | subset sudut |
| `svld_kp_detectability.py` | keypoint zero-shot |
| `svld_mask_fit.py` | mask-based W/H/L |
| `cawang_timepass.py` | side-view/lower envelope |
| `grounded_sam2_container.py` | segmentasi container-only |
| `cawang_container_fit.py` | fit 3D box container-only |

---

## 10. Riwayat commit

| Commit | Isi |
|---|---|
| `a75c4ae` | riset CAROM Air, laporan, kalibrasi, SOP |
| `424dafe` | audit rekaman 16-15-44 |
| `a01e8bc` | kalibrasi ulang tanpa tepi kanan |
| `0e922fb` | uji GeoCalib |
| `65e4bf0` | GeoCalib sebagai alat utama di SOP |
| `e999229` | validasi eksternal SVLD |
| `8c0b344` | side-view Cawang 15,9 m |
| `d63d45f` | lower envelope, batch 6 kendaraan |
| `0bc9537` | container-only +13,3% |
| `b919ba0` | YOLO26-seg whole-truck |
| `f83c12b` | Grounded SAM 2 container-only |
| `1fadfc4` | validasi 20 ft −0,2% |

---

## 11. Rekomendasi berikutnya

**Prioritas 0 (baru, 27 Nov) — ukur lebar lajur dan uji dash + solid terhadap GT SVLD.** Jalur aktif adalah kalibrasi geometri marka, bukan street view. Langkah: (a) pilih frame SVLD yang punya satu dash + satu garis solid; (b) jalankan `fit_dash_line.mjs --solid`; (c) bandingkan `f` dengan XML GT; (d) ulangi untuk beberapa lebar lajur/standar dash. Ini satu-satunya cara mengukur akurasi absolut metode, karena dash fit Cawang bukan GT independen.

**Prioritas 1 — validasi 20 ft berulang.** Uji 3–5 kontainer 20 ft lain dengan box prompt container-only. Jika semuanya 6,0–6,2 m, klaim validasi 20 ft kuat.

**Prioritas 2 — identifikasi 40 vs 45 ft.** Uji kontainer 40 ft yang jelas, atau baca kode ISO 6346 (bukan plat kendaraan). Tanpa tipe, 13,99 m tidak bisa disebut galat.

**Prioritas 3 — I24-3D untuk GT dimensi, bukan side-view.** Kamera I24-3D aerial/nadir 28–45 m; tidak ada pandangan sisi. Gunakan `L/W/H` 3D dari anotasi sebagai GT dimensi. Untuk validasi panjang dari siluet samping, tetap pakai side-view Cawang atau pengukuran lapangan.

**Prioritas 4 — detektor 5 titik.** Fine-tune `vehicle-keypoints` atau SKoPe3D; target ≤3 px. Butuh GPU.

**Prioritas 5 — time-of-passage murni.** Garis melintang $X_0$; bandingkan $v\Delta t$ dengan side-view.

**Prioritas 6 — field test Indonesia.** Satu kendaraan diukur dengan meteran. Ini tetap penentu akhir.

---

## 12. Catatan penutup

Yang sudah benar-benar kuat:

- Hukum galat dan anisotropi.
- Degenerasi $f$–$h$–$w$.
- Geometri pengukuran (0,36%).
- Lima titik cukup.
- Kalibrasi SVLD.
- Container-only 20 ft (−0,2%).
- Dash + garis solid memutus degenerasi `f` (BELMERA, bersyarat).

Yang masih rapuh:

- Panjang dari satu pandangan.
- Detektor 5 titik.
- Kecepatan.
- Generalisasi ke Indonesia.
- 40 vs 45 ft.
- Ambiguitas lajur ATP.
- Geolokasi CCTV (provisional, bukan survei).
- Matching street view (210 m, ~25 SIFT/12 LoFTR).
- Lebar lajur aktual dan standar dash (sistematis, bukan noise).

Jangan menambah dokumen baru sebelum salah satu dari lima prioritas di atas dieksekusi.
