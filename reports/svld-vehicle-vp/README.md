# SVLD: PerspectiveFields, Vehicle VP (deep_vp), dan 3D Box Calibration

**Tanggal:** 20 November 2026  
**Tujuan:** menguji apakah VP kendaraan atau model yang memprediksi FoV/f bisa menggantikan VP vertikal dan sumber f di SVLD.

---

## 0. Ringkasan

1. **PerspectiveFields (CVPR 2023) gagal di 4/5 scene SVLD.** Rasio f median 0,33 (0cam), 0,58-0,69 (session0/6); hanya 1cam yang mendekati (0,95; 11/20 lulus 5%). VP vertikal dari up-vector field meleset **51-83 deg**.
2. **Depth Pro (ICLR 2025)** juga tidak konsisten: rasio f 0,98 di session0_centre, 0,87 di 1cam, tetapi 0,55 di 0cam, 0,44 di session0_right, 0,65 di session6_right. Model f generik tetap tidak bisa menggantikan kalibrasi per-kamera.
3. **deep_vp (ICANN 2021) secara konsep paling tepat untuk traffic camera**: dua VP horizontal ortogonal dari crop kendaraan, lalu `f^2 = -(v1-c).(v2-c)`; tidak butuh garis vertikal atau Manhattan world.
4. **Tetapi model pretrained-nya tidak bisa diunduh** (OneDrive SharePoint meminta login). Repo hanya berisi kode TensorFlow/Keras, tanpa bobot.
5. **Geometri deep_vp diuji dengan sudut box SVLD**: VP dari 8 sudut box kecil (~50 px) masih noise. Median angular error 1,7-20 deg tergantung scene; f dari pasangan VP length-width jauh dari GT (0cam 437 vs 3744 px).
6. **Jalur yang jauh lebih kuat: 3D box PnP.** Dengan 8 sudut box 3D + dimensi box, satu kendaraan memberi f, pitch, yaw, dan h. Pada box GT SVLD, error f **0,00-0,05%** (joint per citra) dan **0,06-0,21%** (satu objek).
7. **Sensitivitas 3D box** (proxy detektor nyata): noise 2D 1 px -> 0,37%; dimensi 3% -> 1,27%; posisi 0,3 m + yaw 2 deg + noise 1 px + dimensi 3% -> **1,86%** (p90 4,3%). Ini masih lebih baik dari AnyCalib/GeoCalib/PerspectiveFields.
8. **Model `yolo3Dbbox` yang sudah ada belum cukup akurat** untuk self-calibration: median error dimensi H 20%, W 7%, L 15% (truk/bus lebih buruk); kurva f tidak punya minimum di f GT. Route 3D box butuh detektor 3D yang lebih baik.

**Kesimpulan:** otomatis penuh untuk f masih belum terbukti. Urutan yang paling realistis:

1. **3D box kendaraan yang akurat** -> PnP, satu kali per kamera (paling menjanjikan).
2. **Kontainer/objek berukuran pasti** (Cawang) atau **spesifikasi lensa/kamera** -> paling akurat untuk deployment.
3. **Anotasi manual 3-4 garis vertikal sekali per kamera + VP jalan** -> fallback yang terkontrol.
4. **deep_vp / VPTR / VPDETR** -> riset lanjutan; butuh bobot, GPU, dan domain adaptation.

---

## 1. PerspectiveFields (CVPR 2023)

Model: `Paramnet-360Cities-edina-centered`, 798 MB, inference CPU ~3,5 s/citra. Model memprediksi roll, pitch, vFoV, dan up-vector field per piksel.

### 1.1 Hasil f dan vFoV

| Scene | n | f GT (px) | vFoV GT | f pred median | rasio f | lulus 5% | VP vertikal median | VP <2 deg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0cam | 20 | 3743,8 | 11,0 deg | 1227 | **0,328** | 0/20 | 51,1 deg | 0/20 |
| 1cam | 20 | 1142,3 | 35,0 deg | 1087 | **0,952** | **11/20** | 83,2 deg | 0/20 |
| session0_centre | 20 | 2878,1 | 14,3 deg | 1989 | **0,691** | 0/20 | 76,2 deg | 0/20 |
| session0_right | 20 | 3994,2 | 10,3 deg | 2325 | **0,582** | 0/20 | 76,5 deg | 0/20 |
| session6_right | 20 | 3384,3 | 12,1 deg | 1950 | **0,576** | 0/20 | 59,1 deg | 0/20 |

- Model seolah punya prior vFoV sekitar 30-33 deg. Ini benar untuk 1cam (35 deg) tetapi salah 3x untuk 0cam (11 deg).
- **VP vertikal dari up-vector field tidak bisa dipakai**: sudutnya 51-83 deg terhadap VP vertikal GT. Ini bukan sekadar offset; arahnya salah.
- Model FoV generik tidak bisa menjadi sumber f untuk lensa telephoto traffic camera. Model hanya berguna kalau FOV kamera berada di distribusi training (~30-60 deg).

### 1.2 Catatan teknis

- `pred_gravity_original` berbentuk `(2,H,W)`; panah per piksel menuju VP vertikal. Kami fit perpotongan garis dengan IRLS.
- Principal point diasumsikan di tengah; SVLD tidak menyimpan cx/cy.
- Inference batch 4 pada CPU berjalan, tetapi model tetap gagal pada 0cam.

---

## 2. deep_vp (ICANN 2021)

Repo: <https://github.com/kocurvik/deep_vp>  
Paper: *Traffic Camera Calibration via Vehicle Vanishing Point Detection* (arXiv:2103.11438).

### 2.1 Metode

- Input: crop kendaraan (bukan seluruh frame).
- CNN stacked hourglass memprediksi heatmap dua VP ortogonal dalam **diamond space** (bisa merepresentasikan titik di luar gambar).
- Untuk setiap kendaraan: dua VP horizontal (arah panjang dan lebar kendaraan).
- f dari ortogonalitas:

```
f^2 = -(u1-cx)(u2-cx) - (v1-cy)(v2-cy)
```

- Kumpulkan pasangan VP dari banyak kendaraan; f dan horizon line diestimasi dengan median/Theil-Sen.
- Tidak butuh garis vertikal, tidak butuh Manhattan world, tidak butuh model kendaraan tertentu.

### 2.2 Status reproduksi

- Repo berisi kode TensorFlow/Keras, `preview_heatmap.py`, `train_heatmap.py`, dan evaluasi BrnoCompSpeed/BrnoCarPark.
- **Bobot pretrained ada di OneDrive SharePoint** dan link-nya meminta login Microsoft (`X-Forms_Based_Auth_Required`). Tidak ada mirror di GitHub Releases/Zenodo (Zenodo hanya berisi kode).
- Tanpa bobot, kami tidak bisa menjalankan model pada SVLD. Training dari nol membutuhkan BoxCars116k dan GPU; tidak realistis di mesin ini (CPU-only).
- Kode memakai TensorFlow Hub untuk detektor kendaraan; versi TF lama perlu disesuaikan.

### 2.3 Uji geometri dengan box SVLD

Kami menguji bagian geometrinya saja: dari 8 sudut box 3D yang dianotasi, fit tiga VP (panjang, lebar, tinggi), lalu bandingkan dengan VP GT dari sumbu box 3D + kalibrasi GT.

| Calib | n box | Median angular error | p90 |
|---|---:|---:|---:|
| 0cam | 10.482 | **1,82 deg** | 19,91 deg |
| 1cam | 5.901 | **1,69 deg** | 5,98 deg |
| session0_centre | 2.814 | 15,22 deg | 51,41 deg |
| session0_right | 3.399 | 20,36 deg | 88,74 deg |
| session6_right | 1.830 | 4,83 deg | 9,68 deg |

- Untuk 0cam/1cam, median VP cukup baik (~1,7 deg), tetapi ekor error besar (p90 6-20 deg).
- Untuk session0_centre/right, box kecil dan sudut pandang membuat VP dari sudut box tidak stabil.
- f dari pasangan VP panjang-lebar (bukan rata-rata tiga pasangan):

| Scene | f GT | f median dari VP box | Rasio |
|---|---:|---:|---:|
| 0cam | 3743,8 | 436,9 | 0,12 |
| 1cam | 1142,3 | 1070,0 | 0,94 |
| session0_centre | 2878,1 | 1668,3 | 0,58 |
| session0_right | 3994,2 | 1236,9 | 0,31 |
| session6_right | 3384,3 | 3710,1 | 1,10 |

**Bacaan:** geometri dua VP benar, tetapi **estimasi VP dari box 50 px terlalu sensitif**. deep_vp menggantinya dengan CNN yang belajar dari penampilan kendaraan; itu bisa lebih baik, tetapi domain gap SVLD (kendaraan kecil, blur, lensa tele) tetap risiko besar. Model ini dilatih pada crop BoxCars/BrnoCarPark yang kendaraannya jauh lebih besar.

---

## 3. 3D box PnP: jalur yang paling akurat

### 3.1 Matematika

SVLD menyimpan 8 sudut 3D (`vertex3d`, mm) dan 8 sudut 2D (`vertex2d`) per kendaraan. Model kamera:

```
R = Rx(phi + pi/2) Rz(theta)
Pc = R (P - [0, 0, h])
u = f Xc / Zc + cx
v = f Yc / Zc + cy
```

Unknown: `f, phi, theta, h`; `cx, cy` di tengah gambar. Satu box memberi 16 persamaan; cukup untuk 4 unknown. Solver `scipy.optimize.least_squares` dengan robust loss.

### 3.2 Hasil dengan box GT

100 citra yang sama (20 per scene). Joint solve semua box per citra:

| Scene | n citra | f GT | Median error f | p90 | Lulus 1% | Lulus 5% |
|---|---:|---:|---:|---:|---:|---:|
| 0cam | 10 | 3743,8 | **0,02%** | 0,04% | 10/10 | 10/10 |
| 1cam | 10 | 1142,3 | **0,05%** | 0,10% | 10/10 | 10/10 |
| session0_centre | 10 | 2878,1 | **0,00%** | 0,01% | 10/10 | 10/10 |
| session0_right | 10 | 3994,2 | **0,01%** | 0,01% | 10/10 | 10/10 |
| session6_right | 10 | 3384,3 | **0,02%** | 0,03% | 10/10 | 10/10 |

Satu objek saja (224 objek):

| Scene | n objek | Median error f | p90 | Lulus 5% |
|---|---:|---:|---:|---:|
| 0cam | 36 | 0,17% | 0,31% | 36/36 |
| 1cam | 24 | 0,16% | 0,40% | 24/24 |
| session0_centre | 54 | 0,21% | 0,54% | 54/54 |
| session0_right | 56 | 0,13% | 0,34% | 56/56 |
| session6_right | 54 | 0,06% | 0,16% | 54/54 |

**Penting:** ini batas atas, karena box 3D dan sudut 2D SVLD konsisten by construction (sudut 2D adalah proyeksi box 3D dengan kalibrasi GT). Ini membuktikan geometri dan model kamera benar, bukan membuktikan detektor nyata bisa.

### 3.3 Sensitivitas terhadap error detektor

Satu objek terbesar per citra, 3 trial per kasus, error diukur terhadap f GT.

| Kasus | Median error f | p90 | Lulus 5% |
|---|---:|---:|---:|
| GT (tanpa noise) | 0,08% | 0,31% | 49/50 |
| Noise 2D 0,5 px | 0,19% | 0,58% | 147/150 |
| Noise 2D 1 px | 0,37% | 0,91% | 147/150 |
| Noise 2D 2 px | 0,70% | 1,62% | 148/150 |
| Dimensi 1% | 0,44% | 1,08% | 147/150 |
| Dimensi 3% | 1,27% | 3,30% | 145/150 |
| Dimensi 5% | 2,22% | 5,86% | 129/150 |
| Posisi 0,25 m | 0,43% | 1,10% | 149/150 |
| Posisi 0,5 m | 0,88% | 2,24% | 146/150 |
| Posisi 1 m | 1,80% | 5,45% | 134/150 |
| Yaw 1 deg | 0,29% | 1,28% | 147/150 |
| Yaw 3 deg | 0,80% | 3,00% | 144/150 |
| Yaw 5 deg | 1,21% | 4,97% | 135/150 |
| **Kombinasi** (1 px + 3% dim + 0,3 m + 2 deg) | **1,86%** | 4,30% | 140/150 |

- Satu outlier 98% muncul pada box degenerat/kecil; median dan joint solve mengatasinya.
- **Target detektor 3D:** dimensi <=3%, posisi <=0,3 m, yaw <=2 deg, sudut 2D <=1 px -> f error ~1,9% (median), cukup untuk pengukuran kecepatan/dimensi kasar, belum cukup untuk metrologi +/-1%.

### 3.4 Agregasi banyak box

Kamera tetap, jadi banyak kendaraan bisa di-joint. Namun error dimensi yang sistematis tidak hilang hanya dengan menambah box. Simulasi combined noise (1 px, 3% dim, 0,3 m, 2 deg):

| Scene | 1 box | 5 box | 10 box | 30 box |
|---|---:|---:|---:|---:|
| 0cam | 3,57% | 1,22% | 2,57% | 1,67% |
| 1cam | 3,36% | 3,66% | 4,17% | 4,70% |
| session0_centre | 2,60% | 1,64% | 2,40% | **0,37%** |
| session0_right | 1,83% | 1,10% | 0,99% | **0,57%** |
| session6_right | 2,21% | 3,10% | 4,63% | 1,60% |

**Bacaan:** agregasi membantu kalau error antar-kendaraan tidak bias (session0), tetapi tidak menyelamatkan bias dimensi (1cam/session6). Kualitas box per kendaraan tetap faktor utama.

### 3.5 Batas penting: box world-space vs box lokal

- `svld_box_calib.py` memakai **8 titik 3D world-space** (posisi + orientasi box sudah diketahui). Ini yang memberi f 0,00-0,21%.
- `box_pnp_known_dims.py` hanya memakai **dimensi + 8 sudut 2D**, lalu menyelesaikan pose box sekaligus. Satu cuboid dengan pose bebas **ambigu**: box bisa dibalik/digeser dan f bisa trade-off dengan depth. Uji 50 objek SVLD: session6 0,74% dan 0cam 1,61%, tetapi 1cam/session0_centre/session0_right median 88-651% karena salah minimum. **Jangan dipakai sebagai pengganti box world-space.**
- Artinya detektor 3D harus memberi **box world-space** (posisi, dimensi, orientasi), bukan hanya crop + dimensi. Alternatif: joint solve banyak box dengan constraint kamera/ground.

---

## 4. Uji `yolo3Dbbox` yang sudah ada

Repo: `D:\Kerjaan\yolo3Dbbox` (PyTorch, model KITTI, weights `epoch_10.pkl` 369 MB, CPU OK).

Model memprediksi dimensi dan orientasi dari crop 224x224, lalu `calc_location` memakai K untuk translasi. Kami uji self-calibration: sapu f, hitung ulang lokasi, proyeksikan box 3D, bandingkan dengan 8 sudut GT.

Contoh 0cam, mobil GT 4,50 x 1,79 x 1,36 m:

- Prediksi model (H,W,L) = **1,57 x 1,62 x 3,68 m** -> H +15%, W -9%, L -18%.
- 20 objek (didominasi mobil, beberapa truk/bus): median error **H 20,4%, W 7,2%, L 14,8%** (p90 35-59%). Model KITTI menganggap truk/bus sebagai mobil; dimensi box tidak bisa dipakai untuk PnP.
- Kurva error vs f **datar/tidak punya minimum di f GT 3744**:
  - objek 0: error 13,7 px (f=300) -> 6,3 px (f=8000), best di batas atas.
  - objek 1: 22,2 px -> 18,1 px, best di 8000.
  - objek 2: minimum 6,3 px di f=735, bukan 3744.

Model ini belum bisa dipakai untuk self-calibration pada kendaraan kecil SVLD. Error dimensi 15-20% mendominasi, bukan geometrinya.

Jika produksi memakai detektor 3D yang lebih baik (atau box 3D yang diverifikasi), route PnP di Bagian 3 langsung bisa dipakai.

---

## 5. Model / paper lain yang dicek

| Metode | Tahun | Status | Catatan |
|---|---|---|---|
| **PerspectiveFields** | CVPR 2023 | diuji | Gagal telephoto; lihat Bagian 1 |
| **GeoCalib** | ECCV 2024 | sudah diuji | 20/100, hanya session0_centre |
| **AnyCalib** | ICCV 2025 | sudah diuji | 6/100 |
| **GlobustVP** | CVPR 2025 | sudah diuji | VP vertikal 0 inlier / 31-36 deg |
| **deep_vp** | ICANN 2021 | dicek, tidak bisa run | Bobot OneDrive login; konsep vehicle VP |
| **VPTR** | AAAI 2024 | belum diuji | Transformer, pretrained SU3 di Google Drive; deformable attention butuh CUDA |
| **VPDETR** | AAAI 2024 | belum diuji | Set prediction, SU3/ScanNet; tidak ada repo resmi yang jelas |
| **NeurVPS** | NeurIPS 2019 | belum diuji | Conic convolution CUDA; lama |
| **RVPD** | WACV 2025 | belum diuji | C++/OpenCV 3.4 + Boost; unsupervised recurrence; potensial untuk garis lemah |
| **Depth Pro** | ICLR 2025 | diuji 5 scene | f 0,98 (s0c), 0,87 (1cam), 0,65 (s6r), 0,55 (0cam), 0,44 (s0r); CPU 3-5 menit/citra |
| **TLCalib** | Sensors 2023 | riset | Transformer 3 VP untuk roadside; tidak ada kode publik |
| **DeepCalib highway** | Sensors 2025 | riset | Synthetic CARLA + triplet attention; tidak ada kode publik |
| **Adaptive structure tensor** | Electronics 2026 | riset | Struktur tensor + hierarchical VP; tidak ada kode publik |

### 5.1 Depth Pro (ICLR 2025)

Model 1,77 GB, inference 1536x1536 pada CPU ~3-5 menit/citra. Depth Pro memprediksi horizontal FoV langsung dari citra; `f_px` dihitung dengan lebar asli.

| Scene | Resolusi | f GT | f pred | Rasio | Catatan |
|---|---:|---:|---:|---:|---|
| 0cam | 1280x720 | 3743,8 | 2045,1 | **0,546** | gagal |
| 1cam | 1280x720 | 1142,3 | 993,2 | **0,870** | borderline; square-scaled 1,043 |
| session0_centre | 1920x1080 | 2878,1 | 2816,2 | **0,979** | bagus |
| session0_right | 1920x1080 | 3994,2 | 1762,1 | **0,441** | gagal |
| session6_right | 1920x1080 | 3384,3 | 2207,8 | **0,652** | gagal |

- Depth Pro adalah model f terbaik sejauh ini untuk `session0_centre` (2,2%) dan `1cam` (4,3% dengan koreksi square), tetapi tetap gagal di 0cam/session0_right.
- Konversi f dari citra non-square tidak konsisten: model melihat 1536x1536, sedangkan kode memakai lebar asli. Untuk 1cam, koreksi ke 1536 justru lebih dekat; untuk session0_centre, nilai mentah lebih dekat. Model belum robust terhadap aspect ratio/resolusi.
- Inference CPU sangat berat; bukan kandidat produksi real-time tanpa GPU.

---

## 6. Implikasi untuk pipeline

1. **Jangan mengganti anchor kontainer dengan model f generik.** Untuk Cawang, kontainer 20 ft tetap sumber f paling akurat (error -0,2%).
2. **Jika kamera punya data spesifikasi lensa/sensor**, itu sumber f paling murah dan paling stabil. `CCTV-ODOL` sudah mendukung `--focal` (datasheet) dan focal dari kontainer.
3. **Jika ada detektor 3D kendaraan yang akurat**, kalibrasi dari box 3D adalah otomatis dan akurat. Ini bisa menjadi fitur baru di `CCTV-ODOL`: satu box 3D -> f/pitch/yaw/h, lalu verifikasi dengan reproyeksi box.
4. **Jika tidak ada 3D box dan tidak ada kontainer**, opsi yang tersisa:
   - anotasi manual 3-4 garis vertikal + VP jalan (sekali per kamera),
   - dua VP horizontal ortogonal dari marka/stop line (perlu segmentasi marka yang bagus),
   - spesifikasi kamera.
5. **deep_vp bukan turnkey**: bobot tidak tersedia, domain gap besar, dan bahkan geometri VP dari box kecil SVLD noise. Jangan jadikan jalur utama tanpa uji bobot asli.

---

## 7. Langkah berikutnya

1. **Uji akurasi box 3D produksi** (`CCTV-ODOL`/`yolo3Dbbox`/detektor baru) terhadap box GT SVLD: dimensi, posisi, yaw. Kalau error <=3% / 0,3 m / 2 deg, route PnP layak.
2. **Coba dapatkan bobot deep_vp** dari penulis atau mirror; kalau berhasil, uji 20 crop kendaraan SVLD dan bandingkan f.
3. **Latih ulang model 3D box** pada SVLD trainval (39k objek) atau fine-tune model KITTI; ini lebih menjanjikan daripada memaksakan deep_vp.
4. **Uji VPTR/VPDETR** hanya jika ada GPU; keduanya butuh deformable attention CUDA.
5. **Fallback**: tool anotasi 3-4 garis vertikal sekali per kamera + VP jalan; ukur batas atas f.

---

## 8. Reproduksi

```powershell
# PerspectiveFields 100 citra
py scripts\svld_perspective_fields.py --limit 100 --batch 4 --out out\svld_perspective_fields

# Cek VP dari box kendaraan SVLD
py scripts\svld_vehicle_vp_check.py --limit 0

# 3D box PnP (box GT)
py scripts\svld_box_calib.py --manifest out\svld_geocalib\manifest.csv --out out\svld_box_calib

# Sensitivitas box 3D
py scripts\svld_box_calib_sensitivity.py --trials 3 --out out\svld_box_calib

# Agregasi banyak box
py scripts\svld_box_calib_scene.py --per-scene 30 --trials 5 --out out\svld_box_calib

# yolo3Dbbox self-cal (pakai venv repo)
D:\Kerjaan\yolo3Dbbox\.venv\Scripts\python.exe scripts\svld_yolo3d_selfcal.py --scene 0cam --limit 1 --steps 12

# Depth Pro (venv terpisah)
D:\tmp\depthpro-env\Scripts\python.exe scripts\svld_depthpro.py --scene 1cam --per-scene 1
```

Artefak:

- `out/svld_perspective_fields/perspective_fields.csv`
- `out/svld_box_calib/objects.csv`, `images.csv`, `sensitivity.csv`, `scene_aggregation.csv`
- `out/svld_depthpro/` (jika selesai)
- `scripts/svld_perspective_fields.py`, `svld_vehicle_vp_check.py`, `svld_box_calib.py`, `svld_box_calib_sensitivity.py`, `svld_box_calib_scene.py`, `box_pnp_calib.py`, `box_pnp_known_dims.py`, `svld_box_known_dims_eval.py`, `svld_yolo3d_selfcal.py`, `svld_yolo3d_dims.py`, `svld_depthpro.py`

---

## 9. Batas

- Box 3D SVLD adalah GT dan konsisten dengan kalibrasi; hasil PnP adalah batas atas, bukan bukti detektor nyata.
- Sensitivitas memakai noise Gaussian independen; error detektor nyata bisa bias dan berkorelasi dengan K.
- deep_vp tidak dijalankan karena bobot tidak bisa diunduh.
- PerspectiveFields hanya diuji varian centered 360Cities/EDINA; varian GSV/uncropped belum.
- Depth Pro hanya diuji 5 scene; inference CPU 3-5 menit/citra.
