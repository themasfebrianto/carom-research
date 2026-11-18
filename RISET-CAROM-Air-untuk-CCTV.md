# Adaptasi CAROM Air untuk Pengukuran Dimensi Kendaraan 3D dari Kamera CCTV Statis

**Kajian teoretis, derivasi geometris, analisis kesalahan, dan penilaian kelayakan**

Versi: 1.0 · November 2026
Lingkup: video CCTV lalu lintas statis (bukan drone), pengukuran panjang (L), lebar (W), tinggi (H)

---

## Daftar Isi

1. [Ringkasan eksekutif dan putusan](#1-ringkasan-eksekutif-dan-putusan)
2. [Posisi penelitian: CAROM Air bukan "CCTV yang diterbangkan"](#2-posisi-penelitian)
3. [Formulasi matematis CAROM Air](#3-formulasi-matematis-carom-air)
4. [Mengapa CAROM Air akurat: rezim geometri nadir](#4-mengapa-carom-air-akurat)
5. [Perubahan rezim geometri dari drone ke CCTV](#5-perubahan-rezim-geometri)
6. [Parameter yang dibutuhkan](#6-parameter-yang-dibutuhkan)
7. [Derivasi formula dimensi 3D dari citra CCTV](#7-derivasi-formula)
8. [Contoh numerik lengkap](#8-contoh-numerik-lengkap)
9. [Analisis kesalahan dan sensitivitas](#9-analisis-kesalahan)
10. [Kalibrasi otomatis tanpa anotasi manual](#10-kalibrasi-otomatis)
11. [Putusan: apa yang dapat dan tidak dapat diadaptasi](#11-putusan)
12. [Arsitektur yang diusulkan](#12-arsitektur-yang-diusulkan)
13. [Keterbatasan kajian dan agenda riset](#13-keterbatasan-kajian)
14. [Referensi](#14-referensi)
15. [Lampiran A: notasi](#lampiran-a-notasi)
16. [Lampiran B: verifikasi numerik](#lampiran-b-verifikasi-numerik)

---

## 1. Ringkasan eksekutif dan putusan

### 1.1 Pertanyaan

Apakah metode CAROM Air — yang dirancang untuk video drone pada ketinggian 85–120 m dengan sumbu kamera mendekati nadir — dapat diadaptasi untuk mengukur dimensi kendaraan (L × W × H) dari kamera CCTV statis di tepi jalan?

### 1.2 Putusan

**Dapat diadaptasi sebagian, dan bukan dengan pipeline apa adanya.**

Yang **transfer** adalah inti geometrinya: model pinhole, kendala bidang tanah datar, fitting model 3D ke citra, regularisasi bentuk kendaraan, dan estimasi state temporal. Semua ini tidak bergantung pada drone.

Yang **tidak transfer** adalah dua hal yang justru menjadi sumber akurasi CAROM Air:

1. **Asumsi proyeksi lemah (weak perspective).** Pada nadir 120 m, skala citra hampir seragam di seluruh badan kendaraan sehingga masalah fitting mendekati linear [1]. Pada CCTV miring dengan depresi 10–20°, skala citra berubah drastis sepanjang badan kendaraan dan asumsi ini runtuh.
2. **Angka akurasinya.** CAROM Air melaporkan galat dimensi L/W/H = 0,075 / 0,044 / 0,099 m [1]. Angka itu dicapai pada 85 m nadir dengan penanda ArUco untuk rekalibrasi. Pada CCTV, galat **tidak** berskala seragam: satu arah memburuk secara kuadratik terhadap jarak dan berbanding balik dengan tinggi kamera (§9), sehingga rasio anisotropi mencapai 5–10×.

### 1.3 Tiga temuan kunci

**Temuan 1 — Anisotropi galat adalah hukum geometri, bukan keterbatasan algoritma.**
Untuk kamera setinggi $h$ mengamati titik tanah pada jarak $z$ di sepanjang sumbu optik:

$$\frac{\sigma_{\text{kedalaman}}}{\sigma_{\text{lateral}}}=\frac{z}{h}$$

Rasio ini **tidak bergantung pada focal length maupun resolusi**. Lensa lebih panjang dan sensor lebih besar memperbaiki kedua arah secara bersamaan, tetapi tidak pernah memperbaiki rasionya. Hanya tiga hal yang dapat memperbaikinya: kamera lebih tinggi, jarak lebih dekat, atau sudut pandang ganda.

**Temuan 2 — Untuk satu kamera, presisi L dan W tidak dapat dioptimalkan bersamaan.**

$$\sigma_L^2(\beta)+\sigma_W^2(\beta)=\sigma_{\text{kedalaman}}^2+\sigma_{\text{lateral}}^2=\text{konstan}$$

dengan $\beta$ sudut antara sumbu panjang kendaraan dan arah pandang. Mengubah posisi kamera hanya **membagikan ulang** ketidakpastian antara L dan W. Fusi multi-frame sepanjang lintasan kendaraan adalah satu-satunya cara memperoleh keduanya sekaligus (§7.7, §7.9).

**Temuan 3 — Prior bentuk mencemari hasil ukur.**
CAROM Air mengestimasi parameter bentuk $\mathbf b$ dengan regularisasi ke template kategori: $\lambda\|\mathbf b-\mathbf b_t\|$. Untuk CCTV, prior ini **wajib** karena satu pandangan miring tidak cukup mengamati L, W, dan H sekaligus. Konsekuensinya, angka yang keluar adalah campuran pengukuran dan prior, bukan pengukuran murni. Dengan $\sigma_{\text{prior}}=0{,}10$ m dan $\sigma_{\text{likelihood}}=0{,}05$ m, estimasi hanya bergerak 20% dari rata-rata kelas menuju nilai sebenarnya (§9.6). Untuk penegakan batas lebar 2,5 m, ini mendiskualifikasi pemakaian langsung.

### 1.4 Peta kelayakan

Kamera 1080p, $f=1920$ px, $h=10$ m, $\sigma_{\text{px}}=1$:

| Jarak | Dimensi **tegak lurus** sinar pandang | Dimensi **sejajar** sinar pandang | Kelayakan |
|---|---|---|---|
| 20 m | 1,5 cm | 3,4 cm | Baik untuk semua keperluan termasuk pengukuran teknis |
| 30 m | 2,2 cm | 7,1 cm | Baik untuk screening dan statistik; marginal untuk penegakan |
| 50 m | 3,7 cm | 18,4 cm | Cukup untuk screening dan klasifikasi; tidak untuk penegakan |
| 70 m | 5,2 cm | 35,2 cm | Hanya untuk deteksi anomali kasar |
| 100 m | 7,4 cm | 70,3 cm | Tidak layak untuk dimensi |

Pembacaan tabel: **H selalu berada di kolom pertama** (tinggi dipetakan ke sumbu vertikal citra, hampir tegak lurus sinar pandang). L dan W **bertukar kolom** bergantung orientasi kendaraan: kendaraan melintang menempatkan L di kolom pertama dan W di kolom kedua; kendaraan menuju kamera sebaliknya (§7.9). Jadi kolom kedua adalah batas terburuk, bukan kesalahan sistematis.

Angka di atas adalah galat acak dari derau piksel saja, sebelum galat skala dan ketidakrataan jalan. Anggaran galat lengkap ada di §9.3.

**Batas keras:** kendaraan yang bergerak langsung menuju/menjauh dari kamera **tidak memiliki informasi panjang** yang dapat diamati. Ini bukan soal algoritma; ini degenerasi geometris (§7.10).

---

## 2. Posisi penelitian

### 2.1 Dua karya, dua rezim

Penting untuk tidak mencampuradukkan dua makalah dari laboratorium yang sama:

**CAROM (2021) — kamera infrastruktur** [2]. Framework ini sudah mengerjakan persis apa yang diminta: melokalisasi kendaraan dari kamera monokular di tepi jalan. Pipeline-nya:

1. Mask R-CNN untuk deteksi dan segmentasi instans [19].
2. Optical flow sparse untuk pelacakan.
3. RANSAC pada vektor optical flow untuk menemukan vanishing point arah gerak → heading kendaraan.
4. Tiga vanishing point (x, y, z kendaraan) + metode garis tangen pada kontur segmentasi → kotak 3D [7].
5. Dimensi kotak 3D **dikoreksi dengan prior dimensi per tipe kendaraan**.
6. Kalman filter 6-DoF.

Hasilnya: galat lokasi 0,8 m pada 50 m dan 1,7 m pada 120 m; **galat longitudinal 1,52 m versus lateral 0,22 m** — rasio 6,9:1 [2]. Makalah itu juga menyatakan terus terang: *"At certain view angles, e.g., when the vehicle is driving directly towards the camera, the 3D bounding box is inaccurate."*

Perhatikan: CAROM 2021 **tidak melaporkan galat dimensi**. Yang dilaporkan hanya lokasi dan kecepatan. Ini bukan kebetulan.

**CAROM Air (2023) — drone** [1]. Mengganti kotak 3D + prior tipe dengan:

1. Keypoint R-CNN, 33 keypoint (19 terdeteksi) per kendaraan.
2. Model bentuk morphable dari PCA atas 200 model 3D.
3. Fitting nonlinear least-squares: pose + parameter bentuk.
4. EKF dengan model sepeda kinematik; dimensi sebagai state yang berubah lambat.

Hasil dimensi: L 0,075 m, W 0,044 m, H 0,099 m.

### 2.2 Implikasi metodologis

Adaptasi "CAROM Air → CCTV" sebenarnya adalah **kembali ke rezim CAROM 2021, tetapi dengan perangkat keypoint dan model bentuk yang lebih baik**. Jadi pertanyaannya bukan "apakah mungkin" — sudah pernah dikerjakan — melainkan **"apakah perangkat baru itu cukup mengatasi masalah geometri yang membuat CAROM 2021 hanya melaporkan lokasi, bukan dimensi?"**

Jawaban ringkas: perangkat baru itu membantu, tetapi tidak mengubah hukum geometrinya.

### 2.3 Pengakuan penulis sendiri

CAROM Air §VI-5 secara eksplisit membahas generalisasi ke perspektif non-udara:

> *"We can also apply our keypoint-based vehicle localization method to videos from non-aerial perspectives. ... However, the keypoint detector must be trained with data from the same perspective. If some keypoints are not observable, e.g., when a vehicle moves toward the camera or when it is partially occluded by another vehicle, more robust regularization is required for the model fitting step."* [1]

Itu adalah pernyataan bahwa pipeline ini **tidak** plug-and-play untuk CCTV, dan bahwa regularisasi tambahan diperlukan — yang persisnya berarti prior bentuk, yang membawa masalah pencemaran di §9.6.

---

## 3. Formulasi matematis CAROM Air

Bagian ini merangkum matematika yang benar-benar dipakai, dengan definisi setiap variabel.

### 3.1 Model kamera dan kalibrasi

Model lubang jarum tanpa distorsi, bidang tanah datar:

$$\lambda\,\tilde{\mathbf p} = K\,[\,R\mid\mathbf t\,]\,\tilde{\mathbf P}_w,
\qquad
K=\begin{bmatrix} f_x & s & c_x\\ 0 & f_y & c_y\\ 0 & 0 & 1\end{bmatrix}$$

| Simbol | Arti |
|---|---|
| $\tilde{\mathbf p}=(u,v,1)^\top$ | koordinat piksel homogen |
| $\tilde{\mathbf P}_w=(X,Y,Z,1)^\top$ | koordinat dunia homogen (m) |
| $K$ | matriks intrinsik |
| $f_x,f_y$ | focal length dalam piksel |
| $s$ | skew (≈0 untuk kamera modern) |
| $c_x,c_y$ | titik utama (principal point) |
| $R\in SO(3)$ | rotasi dunia→kamera |
| $\mathbf t$ | translasi dunia→kamera |
| $\lambda$ | faktor skala proyektif (kedalaman) |

**Kalibrasi CAROM Air.** Intrinsik dikalibrasi di laboratorium. Untuk setiap track video, 8–16 titik korespondensi dianotasi pada citra satelit dan citra aerial referensi. Koordinat 3D titik dihitung dari skala peta dengan asumsi titik berada di bidang tanah. Pose kamera diselesaikan dengan **PnP** (Perspective-n-Points) [3]. Karena pose drone dapat bergeser, pose dihitung ulang setiap frame: fitur sudut dideteksi pada tanah, dilacak sepanjang video, dan PnP dijalankan lagi [1].

**Catatan penting untuk CCTV.** Langkah rekalibrasi per-frame ini **tidak diperlukan** untuk kamera statis. Itu keuntungan, bukan kerugian: pose konstan berarti galat sistematis konstan dan dapat dikarakterisasi sekali, bukan berfluktuasi.

**Sumber skala.** Skala metrik CAROM Air berasal dari peta (Google Maps). Ini adalah titik lemah tersembunyi: seluruh akurasi absolut bergantung pada akurasi peta dan ketepatan anotasi titik. Untuk CCTV, sumber skala harus diganti (§6.5, §10).

### 3.2 Keypoint kendaraan

33 keypoint didefinisikan dalam 3D, 19 di antaranya dideteksi pada citra [1, Tabel I]:

| ID | Terdeteksi | Definisi |
|---|---|---|
| 0–3 | ya | sudut atap |
| 4–7 | ya | sudut kaca depan/belakang |
| 8–11 | ya | pusat lampu depan/belakang |
| 12–15 | tidak | sudut bumper depan/belakang |
| 16–19 | tidak | pusat roda |
| 20–23 | tidak | sudut permukaan bawah sasis |
| 24–25 | ya | sudut terluar spion |
| 26–27 | tidak | sudut kaca pintu depan |
| 28–31 | ya | titik kontak roda–tanah |
| 32 | ya | pusat logo merek |

### 3.3 Prior bentuk (PCA)

Untuk setiap model $i$, vektor bentuk $\mathbf s_i\in\mathbb R^{99}$ adalah konkatenasi koordinat $(x,y,z)$ dari 33 keypoint. PCA menghasilkan rata-rata $\mathbf s_m$, matriks basis $\Phi$ (kolom = $k$ vektor eigen teratas), dan parameter $\mathbf b_i$ sehingga

$$\hat{\mathbf s}_i = \Phi\mathbf b_i + \mathbf s_m \approx \mathbf s_i .$$

Bentuk sembarang dibangkitkan dengan $\hat{\mathbf s}^\ast = \Phi\mathbf b^\ast + \mathbf s_m$. Pasangan $(\Phi,\mathbf s_m)$ disebut **vehicle shape prior** [1]. Basis PCA di sini mengikuti tradisi Active Shape Models [14].

### 3.4 Fitting model

$$\min_{\mathbf b,\,R,\,\mathbf t}\;\sum_{j=1}^{N}\alpha^{(j)}\left\|\mathbf p^{(j)}-\Pi\!\left(R\left(\Phi^{(j)}\mathbf b+\mathbf s_m^{(j)}\right)+\mathbf t\right)\right\| \;+\;\lambda\left\|\mathbf b-\mathbf b_t\right\|$$

| Simbol | Arti |
|---|---|
| $N$ | jumlah keypoint terdeteksi (19) |
| $\alpha^{(j)}\in\{0,1\}$ | visibilitas keypoint ke-$j$ dari detektor |
| $\mathbf p^{(j)}$ | koordinat piksel keypoint ke-$j$ |
| $\Phi^{(j)},\mathbf s_m^{(j)}$ | komponen prior untuk keypoint ke-$j$ |
| $\Pi(\cdot)$ | fungsi proyeksi kamera |
| $\mathbf b_t$ | parameter template kategori (mis. rata-rata sedan) |
| $\lambda$ | bobot regularisasi |

Karena kendaraan diasumsikan selalu di bidang tanah $Z=0$, pose hanya punya **tiga** derajat kebebasan: $(x,y)$ pada $\mathbf t$ dan heading $\psi$ pada $R=R_z(\psi)$. Masalahnya menjadi nonlinear least-squares tak berkendala, diselesaikan dengan Levenberg–Marquardt [1].

**Inisialisasi:** posisi dari pusat bounding box; heading dari RANSAC atas pasangan keypoint yang menunjuk arah depan, misalnya $\{(0,2),(1,3),(4,6),(8,10)\}$ [1].

**Klaim konvergensi:** karena $\Pi(\cdot)$ mendekati proyeksi lemah untuk video aerial, masalahnya mendekati least-squares linear dan konvergen sub-milidetik [1]. **Klaim inilah yang gugur untuk CCTV** (§5).

### 3.5 Estimasi state (EKF)

Posisi $(x,y)$ dan heading $\psi$ dianggap teramati langsung; tiga state lain tersembunyi. EKF memakai model sepeda kinematik yang disederhanakan, dengan asumsi sudut kemudi dan kecepatan dipertahankan antar-frame. Parameter bentuk $\mathbf b$ dan **dimensi kendaraan** diestimasi iteratif dari hasil fitting, dengan asumsi **tidak berubah antar-citra** [1].

Asumsi dimensi konstan inilah yang, dalam adaptasi CCTV, harus dinaikkan statusnya dari detail implementasi menjadi **kepala estimator** (§7.7).

---

## 4. Mengapa CAROM Air akurat

### 4.1 Skala citra hampir seragam

Pada nadir, ground sample distance (GSD) adalah

$$\text{GSD}=\frac{h}{f}\quad[\text{m/piksel}]$$

Untuk UAV 20 MP komersial dengan $f\approx 3600$ px setara dan $h=85$ m:

$$\text{GSD}=\frac{85}{3600}=0{,}0236\ \text{m/piksel}$$

Maka galat yang dilaporkan dapat dikonversi ke piksel:

| Dimensi | Galat (m) | Setara piksel | Galat relatif |
|---|---|---|---|
| L = 4,5 m | 0,075 | 3,2 px | 1,7% |
| W = 1,8 m | 0,044 | 1,9 px | 2,4% |
| H = 1,5 m | 0,099 | 4,2 px | 6,6% |

### 4.2 Mengapa H justru paling buruk pada nadir

Ini tampak berlawanan dengan intuisi, dan merupakan petunjuk penting.

Pada kamera nadir, sebuah titik di tanah pada jarak lateral $s$ dari titik nadir terproyeksi pada radius

$$r_b=\frac{f\,s}{h}, \qquad \text{dan titik atasnya pada } r_t=\frac{f\,s}{h-H}.$$

Jarak radial antara alas dan atap:

$$\Delta r = f s\left(\frac{1}{h-H}-\frac{1}{h}\right)\approx \frac{f s H}{h^2}.$$

Maka sensitivitas tinggi terhadap piksel:

$$\boxed{\;\sigma_H \approx \frac{h^2}{f\,s}\,\sigma_{\text{px}}\;}$$

Untuk $h=85$ m, $f=3600$ px, $s=20$ m: $\sigma_H\approx 0{,}100$ m per piksel. **Angka ini hampir persis sama dengan galat H yang dilaporkan CAROM Air, 0,099 m** [1]. Mekanismenya konsisten: pada nadir, tinggi kendaraan hanya terbaca sebagai pergeseran radial orde kedua, dan makin dekat kendaraan ke titik nadir ($s\to 0$), makin tidak teramati.

Konsekuensi: untuk drone, tinggi adalah dimensi **paling sulit**, bukan paling mudah. Urutan galat relatif CAROM Air (1,7% < 2,4% < 6,6%) mencerminkan urutan ini.

### 4.3 Apa artinya untuk CCTV

Pada CCTV miring, urutan itu **terbalik**. Tinggi kendaraan dipetakan ke sumbu vertikal citra dengan sensitivitas orde pertama:

$$\sigma_H\approx \sqrt2\,\frac{z}{f}\,\sigma_{\text{px}}$$

yang setara dengan sensitivitas lateral, bukan kedalaman. Jadi H menjadi **mudah**, sementara L menjadi sulit ketika kendaraan bergerak sejajar sumbu optik.

Ini bukan kebetulan: kedua rezim adalah cermin satu sama lain. Dalam kedua kasus, dimensi yang sejajar dengan arah pandang adalah yang paling buruk. Pada nadir, tinggi sejajar arah pandang. Pada CCTV, panjang (untuk kendaraan yang datang/menjauh) sejajar arah pandang.

**Prinsip umum:** *dimensi yang sejajar dengan sinar pandang tidak teramati dengan baik dari satu pandangan.* Ini adalah pernyataan tentang kondisi matriks Jacobian, dan berlaku universal (§7.8).

---

## 5. Perubahan rezim geometri

### 5.1 Perbandingan kuantitatif

| Besaran | Drone (CAROM Air) | CCTV tepi jalan |
|---|---|---|
| Tinggi kamera $h$ | 85–120 m | 6–15 m |
| Sudut depresi $\theta$ | 80–90° | 5–30° |
| GSD lateral $z/f$ | 2,4–3,3 cm/px | 1,5–5 cm/px |
| Rasio anisotropi $z/h$ | ~0,3–1,4 | **4–15** |
| Rentang $L/z$ (kekuatan perspektif) | 0,04 | 0,10–0,25 |
| Drift pose | ya, per frame | tidak (statis) |
| Oklusi | jarang | sering |
| Sumber skala | peta/satelit | **harus disurvei** |
| Keypoint terlihat | 19 dari 33 | 8–14 dari 19 (perkiraan) |

### 5.2 Parameter yang menentukan: $z/h$

Ambil kamera pinhole dengan sumbu optik membentuk sudut $\theta$ terhadap horizontal, tinggi $h$ di atas bidang tanah. Untuk titik tanah pada jarak $X$ horizontal, koordinat kamera adalah

$$z_c = X\cos\theta + h\sin\theta, \qquad y_c = -X\sin\theta + h\cos\theta .$$

Bayangan vertikalnya $v = f\,y_c/z_c + c_y$. Diferensiasi terhadap $X$:

$$\frac{\partial v}{\partial X}=f\,\frac{-\sin\theta\,z_c-y_c\cos\theta}{z_c^{2}} = -\frac{f h}{z_c^{2}} .$$

Jadi

$$\frac{\partial X}{\partial v}=-\frac{z_c^{2}}{f h}.$$

Sementara arah lateral:

$$\frac{\partial Y}{\partial u}=\frac{z_c}{f}.$$

Rasio keduanya:

$$\frac{\partial X/\partial v}{\partial Y/\partial u}=\frac{z_c}{h}.$$

Untuk $z_c\approx z$ (sudut depresi moderat), diperoleh hukum $z/h$. **Rasio ini tidak memuat $f$ dan tidak memuat resolusi.** Ini adalah konsekuensi murni dari foreshortening bidang tanah.

### 5.3 Kekuatan perspektif

Rasio $L/z$ mengukur seberapa jauh proyeksi menyimpang dari affine. Untuk mobil 4,5 m:

- Drone pada 120 m: $L/z = 0{,}038$ → galat aproksimasi affine ≈ 4%.
- CCTV pada 40 m: $L/z = 0{,}113$ → galat ≈ 11%.

Dalam piksel, ini berarti perbedaan panjang bayangan sisi dekat dan sisi jauh mobil sekitar 11% pada CCTV versus 4% pada drone. Model bentuk harus menyerap perbedaan itu; jika model mengasumsikan proyeksi lemah, kesalahannya langsung masuk ke dimensi.

Inilah alasan teknis mengapa klaim "sangat dekat dengan least-squares linear" pada [1] tidak dapat dipindahkan ke CCTV.

---

## 6. Parameter yang dibutuhkan

Bagian ini menjawab fokus penelitian 1 dan 3.

### 6.1 Intrinsik

| Parameter | Simbol | Mengapa perlu | Catatan khusus CCTV |
|---|---|---|---|
| Focal length (px) | $f_x,f_y$ | Skala dasar; semua dimensi berskala $1/f$ | **Wajib dikalibrasi di lab** [6]. Lensa varifocal berubah jika zoom disentuh |
| Titik utama | $c_x,c_y$ | Pusat proyeksi; kesalahan → bias sistematis | Bergeser jika cropping/encoding mengubah resolusi |
| Skew | $s$ | Umumnya 0 | Abaikan |
| Distorsi radial | $k_1,k_2,k_3$ | **Kritis.** Lensa 2,8–6 mm punya distorsi 5–15% di tepi | CAROM Air mengasumsikan nol distorsi [1]; untuk CCTV asumsi ini **tidak boleh** dipakai |
| Distorsi tangensial | $p_1,p_2$ | Kesalahan pemasangan lensa | Kecil, tetapi murah untuk disertakan |
| Resolusi & sensor | — | Menentukan $f$ dalam piksel | 1080p minimum; 4K lebih baik untuk jarak jauh |
| Shutter | global/rolling | Rolling shutter menggeser objek bergerak | Pada 30 km/jam dan readout 10 ms, smear ≈ 8 cm |
| Interlacing | — | CCTV lawas PAL/NTSC | Field tearing pada objek bergerak; deinterlace atau buang |

### 6.2 Ekstrinsik

Rotasi diuraikan sebagai yaw–pitch–roll:

$$R = R_z(\psi)\,R_y(\theta)\,R_x(\phi)$$

| Parameter | Simbol | Rentang khas CCTV | Sensitivitas |
|---|---|---|---|
| Yaw | $\psi$ | 0–90° terhadap sumbu jalan | Menentukan arah anisotropi; **paling penting untuk perencanaan** |
| Pitch (depresi) | $\theta$ | 5–30° | Menentukan $z_c$ dan horizon; kesalahan kecil sebagian terserap sebagai rotasi kaku (§9.5) |
| Roll | $\phi$ | 0–3° (kesalahan pemasangan) | Mentilt horizon; <1° aman untuk metode berbasis VP |
| Tinggi kamera | $h$ | 6–15 m | **Langsung berskala linear ke semua dimensi** |
| Posisi horizontal | $C_x,C_y$ | — | Menentukan homografi; direseksi dari titik survei |

### 6.3 Vanishing point dan garis horizon

| Parameter | Simbol | Definisi | Kegunaan |
|---|---|---|---|
| VP arah memanjang jalan | $\mathbf v_x$ | Titik pertemuan garis-garis sejajar arah $X$ dunia | Arah kendaraan, rotasi |
| VP arah melintang | $\mathbf v_y$ | Titik pertemuan garis sejajar arah $Y$ | Ortogonalitas → $f$ |
| VP vertikal | $\mathbf v_z$ | Titik pertemuan garis-garis vertikal dunia | **Kunci pengukuran tinggi** |
| Garis horizon | $\mathbf l$ | $\mathbf l=\mathbf v_x\times\mathbf v_y$ | Bidang tanah di tak hingga |

Untuk kamera miring ke bawah, $\mathbf v_z$ berada **di bawah** citra (titik antipodal dari arah "atas"), pada baris $c_y+f\cot\theta$. Ini sering menimbulkan kesalahan implementasi: tanda komponen homogen harus dijaga.

### 6.4 Homografi bidang tanah

$$H = K\,[\,\mathbf r_1\;\mathbf r_2\;\mathbf t\,],\qquad
\lambda\begin{bmatrix}u\\v\\1\end{bmatrix}=H\begin{bmatrix}X\\Y\\1\end{bmatrix}$$

dengan $\mathbf r_1,\mathbf r_2$ kolom pertama dan kedua $R$. Matriks $H$ punya 8 derajat kebebasan; skalanya tidak ditentukan oleh $H$ sendiri.

**Ambiguitas skala.** Dari citra saja, rekonstruksi hanya tertentu hingga satu faktor skala. Ini adalah fakta fundamental proyeksi monokular. CAROM Air memecahkannya dengan peta; CCTV harus memecahkannya dengan referensi metrik (§6.5).

### 6.5 Referensi skala — parameter paling kritis

Karena semua dimensi berskala linear terhadap referensi, galat relatif referensi **langsung** menjadi galat relatif dimensi:

$$\frac{\sigma_L}{L}=\frac{\sigma_h}{h}=\frac{\sigma_{L_{\text{ref}}}}{L_{\text{ref}}}$$

| Sumber referensi | Ketidakpastian khas | Akibat pada L = 4,5 m | Akibat pada H = 1,5 m |
|---|---|---|---|
| Lebar lajur 3,50 m (asumsi) | ±0,15 m (4,3%) | ±19,3 cm | ±6,5 cm |
| Lebar lajur 3,50 m (diukur) | ±0,05 m (1,4%) | ±6,3 cm | ±2,1 cm |
| Survei RTK 4–8 titik | ±0,5% | ±2,3 cm | ±0,8 cm |
| Tinggi kamera dari survei | ±0,1 m pada 10 m (1%) | ±4,5 cm | ±1,5 cm |

**Kesimpulan operasional:** untuk pengukuran, survei RTK satu kali atas 4–8 titik di zona ukur adalah investasi dengan hasil terbesar. Ini bukan "anotasi manual per kendaraan"; ini kalibrasi satu kali.

### 6.6 Lingkungan

| Faktor | Pengaruh | Kuantifikasi |
|---|---|---|
| Ketidakrataan jalan | Setara galat tinggi lokal | $\Delta X=\Delta z/\tan\theta$. Pada $\theta=12°$, 5 cm tonjolan → 23,5 cm galat jarak |
| Kemiringan melintang (crown) | Bidang tanah tidak datar | 2% crown pada 10 m → 20 cm |
| Kemiringan memanjang | Sama seperti di atas | 1% grade pada 50 m → 50 cm ketinggian semu |
| Ketinggian trotoar | Oklusi alas kendaraan | 10–15 cm tinggi hilang jika ban tertutup |
| Getaran tiang | Perubahan pose | Monitor residu fitur statis |
| Hujan/kabut | Penurunan kontras, deteksi keypoint gagal | Buang frame dengan skor rendah |
| Malam/IR | Pergeseran fokus dan panjang fokus efektif | Kalibrasi terpisah untuk mode IR |
| Kotoran/air pada kubah | Refraksi lokal | Deteksi anomali kalibrasi |

### 6.7 Definisi objek ukur — sering terlewat

Sebelum menghitung apa pun, **measurand** harus didefinisikan. Untuk kendaraan ada tiga lebar yang berbeda:

| Istilah | Definisi | Nilai khas mobil |
|---|---|---|
| Track width | Jarak antar pusat kontak ban | 1,50–1,60 m |
| Body width | Lebar bodi tanpa spion | 1,75–1,85 m |
| Overall width | Termasuk spion | 2,00–2,15 m |

Regulasi Indonesia (PP 55/2012 Pasal 54) menetapkan batas lebar 2.500 mm [15] — yang dimaksud adalah lebar bodi, bukan track width. Jika pipeline mengestimasi dari titik kontak roda (seperti ground truth CAROM Air), hasilnya adalah track width, bukan body width. Selisihnya 25–35 cm, jauh melampaui seluruh anggaran galat.

Demikian pula tinggi: yang dimaksud regulasi adalah tinggi total termasuk muatan dan bak, bukan tinggi atap kabin.

---

## 7. Derivasi formula

### 7.1 Homografi tanah dan back-projection

Untuk titik di bidang tanah $Z=0$, $\tilde{\mathbf P}_w=(X,Y,0,1)^\top$:

$$\lambda\tilde{\mathbf p}=K[\mathbf r_1\;\mathbf r_2\;\mathbf t]\begin{bmatrix}X\\Y\\1\end{bmatrix}=H\begin{bmatrix}X\\Y\\1\end{bmatrix}$$

Maka untuk setiap piksel yang **diketahui berada di tanah**:

$$\begin{bmatrix}X\\Y\\1\end{bmatrix}\sim H^{-1}\tilde{\mathbf p}
\quad\Longrightarrow\quad
X=\frac{(H^{-1}\tilde{\mathbf p})_1}{(H^{-1}\tilde{\mathbf p})_3},\;\;
Y=\frac{(H^{-1}\tilde{\mathbf p})_2}{(H^{-1}\tilde{\mathbf p})_3}$$

Ini eksak, bukan aproksimasi. **Semua titik kontak ban berada di tanah, sehingga posisinya dapat direkonstruksi tanpa mengetahui tinggi kendaraan.**

### 7.2 Panjang dan lebar

Misalkan $P_0,P_1,P_2,P_3$ adalah empat sudut tapak kendaraan hasil back-projection, terurut mengelilingi persegi panjang. Maka

$$\boxed{\;L=\|P_1-P_2\|,\qquad W=\|P_0-P_1\|,\qquad
\|P_i-P_j\|=\sqrt{(X_i-X_j)^2+(Y_i-Y_j)^2}\;}$$

**Sifat penting:** L dan W hanya bergantung pada homografi dan empat titik tanah. Tidak ada ketergantungan pada $\mathbf v_z$, pada tinggi kendaraan, atau pada prior bentuk. Karena itu L dan W adalah dimensi yang **paling bersih** secara metodologis.

Yang tersisa hanyalah galat lokasi titik, yang mengikuti hukum anisotropi §5.2.

### 7.3 Tinggi — rumus 1: perpotongan sinar dengan garis vertikal

Ini adalah rumus yang paling langsung dan yang dipakai untuk verifikasi.

Diketahui:
- $B=(X_b,Y_b,0)$: titik alas, hasil back-projection titik kontak.
- $\mathbf p_t$: piksel atap yang berada **tepat di atas** $B$.
- $\mathbf C$: pusat kamera.

Sinar dari kamera melalui $\mathbf p_t$:

$$\mathbf d=\frac{R^\top K^{-1}\tilde{\mathbf p}_t}{\|R^\top K^{-1}\tilde{\mathbf p}_t\|}\quad(\text{arah dunia, satuan})$$

Titik atap terletak pada garis vertikal melalui $B$:

$$\mathbf P = \mathbf C + \lambda\mathbf d = B + \mu\,\mathbf e_z,\qquad \mathbf e_z=(0,0,1)^\top$$

Selesaikan dengan komponen horizontal:

$$\boxed{\;\lambda=\frac{(B-\mathbf C)\cdot \mathbf d_{xy}}{\|\mathbf d_{xy}\|^2},
\qquad
H=\left(\mathbf C+\lambda\mathbf d\right)_z-B_z\;}$$

dengan $\mathbf d_{xy}=(d_x,d_y,0)$.

**Contoh geometris:**

```
              atap T
                |
    C (kamera)  |        B = alas (di tanah)
      \         |       /
       \        |      /
        \       |     /
         \______|____/
                B
   sinar C->p_t  dan  garis vertikal melalui B
   berpotongan di T; H = T.z - B.z
```

**Degenerasi.** Jika kamera tepat di atas $B$, maka $\|\mathbf d_{xy}\|\to 0$ dan $\lambda$ meledak. Secara fisis: garis vertikal melalui $B$ terproyeksi menjadi satu titik, sehingga tinggi tidak teramati. Ini penjelasan formal mengapa nadir buruk untuk H (§4.2).

### 7.4 Tinggi — rumus 2: cross-ratio Criminisi (tanpa kalibrasi penuh)

Jika kalibrasi tidak tersedia tetapi vanishing point vertikal $\mathbf v_z$ dan garis horizon $\mathbf l$ dapat diestimasi, metrologi satu pandangan [4] memberikan:

$$\kappa(\mathbf b,\mathbf t)=\frac{\|\mathbf b\times\mathbf t\|}{(\mathbf l\cdot\mathbf b)\,\|\mathbf v_z\times\mathbf t\|}$$

dan tinggi objek:

$$\boxed{\;Z_x=Z_r\,\frac{\kappa(\mathbf b_x,\mathbf t_x)}{\kappa(\mathbf b_r,\mathbf t_r)}\;}$$

dengan $(\mathbf b_r,\mathbf t_r)$ segmen vertikal referensi yang tingginya $Z_r$ diketahui. Semua vektor dalam koordinat homogen.

**Syarat:** $\mathbf b_x,\mathbf t_x,\mathbf v_z$ harus segaris (ketiganya pada satu garis vertikal 3D). Ini terpenuhi jika titik alas dan titik atap berada pada rusuk vertikal yang sama dari kotak pembatas.

**Keunggulan:** tidak memerlukan $K$, $R$, maupun $h$. Hanya $\mathbf l$, $\mathbf v_z$, dan satu panjang referensi.
**Kelemahan:** sangat sensitif terhadap galat $\mathbf v_z$ dan $\mathbf l$, dan hanya memberikan satu skalar.

Verifikasi numerik: implementasi rumus ini pada citra sintetis dengan tiang referensi 3,00 m mereproduksi tinggi mobil 1,5000 m secara eksak (Lampiran B, uji 1b).

### 7.5 Tinggi — rumus 3: fitting kotak 3D 7-DoF

Rumusan paling umum dan paling sesuai untuk CCTV.

Parameter: $\boldsymbol\theta=(X,Y,\psi,L,W,H)$ — 6 skalar.
Delapan sudut kotak dalam kerangka kendaraan:

$$\mathbf P_k^{\text{veh}}=\left(\pm\frac{L}{2},\;\pm\frac{W}{2},\;\{0,H\}\right),\qquad k=1,\dots,8$$

Transformasi ke dunia:

$$\mathbf P_k = \mathbf C_v + R_z(\psi)\,\mathbf P_k^{\text{veh}},\qquad \mathbf C_v=(X,Y,0)^\top$$

Proyeksi dan residual:

$$\mathbf p_k=\Pi(\mathbf P_k),\qquad
E(\boldsymbol\theta)=\sum_{k\in\mathcal V}\rho\left(\left\|\mathbf p_k^{\text{obs}}-\mathbf p_k\right\|_{\Sigma_k}\right)$$

dengan $\mathcal V$ himpunan sudut yang terlihat, $\rho$ robust loss (Huber/Cauchy), dan $\Sigma_k$ kovarians lokasi keypoint.

**Varian morphable (CAROM Air).** Delapan sudut kotak dapat diganti dengan 33 keypoint model bentuk:

$$\mathbf P_k^{\text{veh}}=\Phi^{(k)}\mathbf b+\mathbf s_m^{(k)},\qquad
E=\sum_{k}\alpha_k\rho\left(\left\|\mathbf p_k^{\text{obs}}-\Pi(R_c\mathbf P_k+\mathbf t_c)\right\|_{\Sigma_k}\right)+\lambda_b\|\mathbf b-\mathbf b_t\|^2$$

Dalam hal ini $\boldsymbol\theta$ diperluas dengan $\mathbf b$, sedangkan $L,W,H$ **tidak** dioptimasi langsung — keduanya dihitung dari keypoint yang telah direkonstruksi:

$$L=\|\mathbf P_{\text{rear}}-\mathbf P_{\text{front}}\|,\quad
W=\|\mathbf P_{\text{right}}-\mathbf P_{\text{left}}\|,\quad
H=\max_k(\mathbf P_k)_z$$

Perbedaan ini penting: pada varian kotak, dimensi adalah **parameter bebas** yang diamati; pada varian morphable, dimensi adalah **fungsi dari state bentuk** dan karena itu terikat prior. Varian pertama lebih jujur untuk pengukuran; varian kedua lebih tahan terhadap oklusi.

Konstruksi kotak 3D dari tiga vanishing point dan garis tangen pada kontur kendaraan dijelaskan oleh Dubská dkk. [7]; varian yang hanya memakai bounding box 2D dan lebar kendaraan tetap dijelaskan oleh Zwemer dkk. [9].

**Hitungan derajat kebebasan.** Satu pandangan memperlihatkan maksimal 7 dari 8 sudut kotak (satu selalu tersembunyi) = 14 persamaan untuk 6 parameter. Secara nominal over-determined. Tetapi **jumlah persamaan bukan jaminan kondisi baik** — lihat §7.8.

### 7.6 Kalibrasi otomatis dari vanishing point

**Langkah 1 — focal length dari dua VP ortogonal.** Dengan $K=\mathrm{diag}(f,f,1)$ berpusat di $(c_x,c_y)$ dan tanpa skew, ortogonalitas arah memberi $\mathbf v_1^\top\omega\,\mathbf v_2=0$ dengan $\omega=K^{-\top}K^{-1}$ [5, 10]:

$$\boxed{\;f^{2}=-(u_1-c_x)(u_2-c_x)-(v_1-c_y)(v_2-c_y)\;}$$

Jika nilai di dalam akar negatif, konfigurasi VP tidak valid (fisis tidak mungkin).

**Langkah 2 — rotasi dari tiga VP.** Untuk arah dunia $\mathbf e_i$,

$$\mathbf v_i\sim K R\,\mathbf e_i\quad\Longrightarrow\quad \mathbf r_i=\frac{K^{-1}\mathbf v_i}{\|K^{-1}\mathbf v_i\|}$$

Kolom-kolom $R$ diperoleh langsung; ortogonalisasi Gram–Schmidt menyerap derau; $\mathbf r_3=\mathbf r_1\times\mathbf r_2$ menjamin $\det R=+1$. Tanda $\mathbf r_i$ dipilih agar titik tanah berada di bawah horizon.

**Langkah 3 — translasi.** Dengan titik asal dunia di proyeksi vertikal kamera ($\mathbf C=(0,0,h)$):

$$\mathbf t=-R\,\mathbf C=-h\,\mathbf r_3$$

sehingga

$$H=K\,[\,\mathbf r_1\;\;\mathbf r_2\;\;-h\,\mathbf r_3\,]$$

**Langkah 4 — posisi dan tinggi kamera dari titik survei.** Dengan $R$ dan $f$ diketahui, proyeksi titik tanah hanya bergantung pada tiga parameter $(C_x,C_y,h)$. Setiap titik tanah berkoordinat metrik memberi 2 persamaan (setelah perkalian silang, linear dalam ketiganya). Maka **dua titik survei** sudah cukup untuk menyelesaikan ketiganya secara tertutup. Dalam praktik gunakan 6–8 titik dan least-squares untuk meredam derau deteksi.

**Ringkasan resep:** 3 VP (dari marka jalan + arah vertikal) + 2 titik survei = kalibrasi metrik lengkap. Ini adalah inti dari §10.

### 7.7 Fusi multi-frame: benda kaku yang bergerak

Inilah modifikasi terpenting untuk CCTV.

Sebuah kendaraan adalah **benda kaku dengan dimensi konstan**. Ketika melintas, ia diamati dari banyak sudut aspek. Rumuskan sebagai bundle adjustment atas seluruh track:

$$\min_{\{L,W,H\},\,\{X_k,Y_k,\psi_k\}}\;\sum_{k=1}^{K}\sum_{j=1}^{8}\alpha_{kj}\,\rho\left(\left\|\mathbf p_{kj}^{\text{obs}}-\Pi\!\left(R_c\left[R_z(\psi_k)\mathbf P_j^{\text{veh}}(L,W,H)+\begin{pmatrix}X_k\\Y_k\\0\end{pmatrix}\right]+\mathbf t_c\right)\right\|_{\Sigma}\right)$$

dengan $K$ jumlah frame dalam track, $R_c,\mathbf t_c$ pose kamera (statis, sama untuk semua $k$), dan $\mathbf P_j^{\text{veh}}$ delapan sudut kotak dari §7.5. Perhatikan: $L,W,H$ **tidak** bersuperskrip $k$ — itulah kendalanya.

**Mengapa ini bekerja.** Informasi Fisher bertambah:

$$\frac{1}{\sigma_L^2}\approx\sum_{k}\frac{1}{\sigma_L^2(\beta_k)}$$

dengan $\beta_k$ sudut aspek pada frame $k$. Frame di mana $L$ tegak lurus arah pandang menyumbang presisi $\sigma_{\text{lateral}}$; frame di mana $L$ sejajar sumbu pandang hampir tidak menyumbang. Hasilnya

$$\sigma_L\approx\frac{\sigma_{\text{lateral}}}{\sqrt{N_{\text{eff}}}},\qquad N_{\text{eff}}=\#\{k:|\beta_k|>45°\}$$

Untuk lintasan 2 detik pada 25 fps dengan separuh frame beraspek baik, $N_{\text{eff}}\approx 25$ → perbaikan ≈5× dibanding satu frame lateral, dan ≈25× dibanding satu frame head-on.

**Batasnya.** Fusi tidak menghilangkan bias sistematis (skala, ketidakrataan jalan, prior). Ia hanya menghilangkan derau acak dan anisotropi geometris.

### 7.8 Analisis kondisi: mengapa dimensi sejajar sinar pandang buruk

Tuliskan Jacobian proyeksi terhadap parameter kotak. Untuk satu pandangan, arah paling lemah dari ruang parameter adalah kombinasi yang menggeser kotak **sepanjang** sinar pandang sambil menyesuaikan dimensinya agar siluet tetap sama.

Secara informal: jika kotak digeser sejauh $\delta$ menjauh dan dimensinya diperbesar dengan faktor $(1+\delta/z)$, siluetnya hampir tidak berubah. Kombinasi nol ini adalah

$$\delta L \approx L\,\frac{\delta z}{z}$$

yang berarti

$$\frac{\sigma_L}{L}\gtrsim \frac{\sigma_z}{z}.$$

Karena $\sigma_z$ sendiri tumbuh sebagai $z^2/(fh)$, galat relatif panjang tumbuh sebagai $z/(fh)\cdot L$ — konsisten dengan §5.2.

**Akibat praktis:** nilai singular terkecil dari Jacobian menentukan arah ketidakpastian, dan arah itu kira-kira sejajar sinar pandang. Tidak ada estimator yang dapat mengalahkan ini tanpa informasi tambahan (prior, frame lain, atau kamera lain).

Sebagai bukti pentingnya lokalisasi relatif terhadap prediksi bentuk: pada analisis ablasi MonoDLE untuk KITTI, mengganti prediksi dimensi 3D dengan nilai ground truth hanya menaikkan AP dari 11,12% menjadi 11,96%, sedangkan mengganti lokasi 3D menaikkannya menjadi 78,84% [11]. Artinya, pada monokular, **lokalisasi — bukan bentuk — yang mendominasi**; dan lokalisasi bergantung tepat pada geometri yang dianalisis di sini.

### 7.9 Invarian redistribusi L–W

Untuk dimensi horizontal yang membentuk sudut $\beta$ terhadap arah kedalaman:

$$\sigma^2(\beta)=\sigma_{\text{dep}}^2\cos^2\beta+\sigma_{\text{lat}}^2\sin^2\beta$$

Karena $L\perp W$, maka $\beta_W=\beta_L+90°$, sehingga

$$\sigma_L^2+\sigma_W^2=\sigma_{\text{dep}}^2+\sigma_{\text{lat}}^2=\text{konstan}$$

**Interpretasi:** memindahkan kamera atau mengubah yaw hanya **membagikan ulang** ketidakpastian antara panjang dan lebar. Tidak ada posisi kamera tunggal yang optimal untuk keduanya.

**Korolari — sudut kamera optimal untuk satu pandangan.** Karena jumlah kuadratnya tetap, galat **terburuk** diminimalkan ketika kedua dimensi mendapat porsi sama, yaitu pada $\gamma=45°$ terhadap sumbu jalan. Dengan $\rho=z/h$:

$$\sigma_L=\sigma_W=\sigma_{\text{lat}}\sqrt{\frac{\rho^{2}+1}{2}}$$

Untuk $\rho=5$: keduanya menjadi $3{,}6\,\sigma_{\text{lat}}$, versus konfigurasi tegak lurus di mana W mencapai $5\,\sigma_{\text{lat}}$ dan L hanya $1\,\sigma_{\text{lat}}$. Jadi kamera miring 40–50° terhadap sumbu jalan **bukan kompromi asal-asalan** — ia meminimalkan galat maksimum, yang relevan karena lebar adalah dimensi dengan toleransi hukum paling ketat (2,5 m).

Ini juga menjelaskan mengapa pengukuran L dan W saling bertukar presisi pada tabel §9.2: pada baris "melintang" $\sigma_L$ kecil dan $\sigma_W$ besar; pada baris "sejajar" sebaliknya; jumlah kuadratnya selalu sama.

### 7.10 Degenerasi head-on

Jika kendaraan bergerak lurus menuju kamera, sudut aspek $\beta$ konstan sepanjang lintasan. Maka:

- Semua frame memberi informasi yang sama.
- Siluet hanya membatasi kombinasi $L$ dan $W$ melalui lebar tampak.
- Panjang tidak teramati; yang teramati adalah "seberapa cepat kendaraan membesar", yang bergantung pada kecepatan, bukan panjang.

Secara formal, kolom Jacobian untuk $L$ menjadi (hampir) kombinasi linear kolom untuk posisi. Ini adalah degenerasi, bukan derau.

**Konsekuensi desain:** zona ukur harus ditempatkan agar kendaraan melintas **melintang**, bukan menuju kamera. Untuk jalan dengan dua arah, kamera di sisi jalan menghadap tegak lurus adalah konfigurasi terbaik untuk L; kamera di ujung jalan adalah yang terburuk.

---

## 8. Contoh numerik lengkap

Contoh ini dihitung penuh dan diverifikasi (Lampiran B).

### 8.1 Konfigurasi

| Komponen | Nilai |
|---|---|
| Kamera | 1920 × 1080, $f=1920$ px, $c=(960,540)$ |
| Posisi | $h=10{,}00$ m, tepat di atas titik asal |
| Orientasi | yaw 8°, pitch (depresi) 12°, roll 0° |
| Kendaraan | $L=4{,}50$ m, $W=1{,}80$ m, $H=1{,}50$ m |
| Posisi kendaraan | pusat (50,00; 3,00) m, heading 90° (melintang) |

Matriks:

$$K=\begin{bmatrix}1920&0&960\\0&1920&540\\0&0&1\end{bmatrix},\qquad
R=\begin{bmatrix}0{,}139&-0{,}990&0\\-0{,}206&-0{,}029&-0{,}978\\0{,}969&0{,}136&-0{,}208\end{bmatrix},\qquad
\mathbf t=\begin{bmatrix}0\\9{,}781\\2{,}079\end{bmatrix}$$

### 8.2 Pengamatan (piksel)

| Sudut tapak | Koordinat dunia (X, Y) | Piksel alas $(u,v)$ | Piksel atap $(u,v)$ |
|---|---|---|---|
| depan-kiri | (49,10; 5,25) | (1022,3; 521,7) | (1022,7; 465,3) |
| depan-kanan | (50,90; 5,25) | (1029,5; 508,7) | (1029,9; 454,1) |
| belakang-kanan | (50,90; 0,75) | (1196,5; 513,2) | (1197,9; 457,9) |
| belakang-kiri | (49,10; 0,75) | (1195,1; 526,5) | (1196,6; 469,4) |

Perhatikan: tinggi 1,50 m bersesuaian dengan pergeseran vertikal **55–57 piksel**. Ini adalah sinyal yang kuat — alasan mengapa H mudah pada CCTV miring.

### 8.3 Langkah 1 — vanishing point

$$\mathbf v_x=(1235{,}9;\;131{,}9),\qquad
\mathbf v_y=(-13006{,}7;\;131{,}9),\qquad
\mathbf v_z=(960{,}0;\;9572{,}9)$$

Keduanya berada pada baris 131,9 — konsisten dengan definisi: horizon adalah garis $v=131{,}9$.

### 8.4 Langkah 2 — focal length dari VP ortogonal

$$f^2=-\big[(1235{,}9-960)(-13006{,}7-960)\big]-(131{,}9-540)(131{,}9-540)$$

$$f^2=3\,686\,866{,}9\quad\Longrightarrow\quad f=1920{,}12\ \text{px}\quad\checkmark$$

(Nilai sebenarnya 1920,00 px. Selisih 0,006% murni berasal dari pembulatan koordinat VP ke satu desimal; pada perhitungan tanpa pembulatan, hasilnya eksak hingga presisi mesin — lihat Lampiran B.)

### 8.5 Langkah 3 — homografi

$$H=\begin{bmatrix}1197{,}096&-1770{,}628&1995{,}952\\ 127{,}754&17{,}955&19903{,}157\\ 0{,}969&0{,}136&2{,}079\end{bmatrix}$$

### 8.6 Langkah 4 — back-projection empat sudut tapak

| Sudut | Hasil rekonstruksi | Nilai sebenarnya |
|---|---|---|
| depan-kiri | (49,100; 5,250) | (49,10; 5,25) |
| depan-kanan | (50,900; 5,250) | (50,90; 5,25) |
| belakang-kanan | (50,900; 0,750) | (50,90; 0,75) |
| belakang-kiri | (49,100; 0,750) | (49,10; 0,75) |

Eksak hingga presisi mesin.

### 8.7 Langkah 5 — dimensi

$$W=\|P_0-P_1\|=\sqrt{(49{,}1-50{,}9)^2}=1{,}8000\ \text{m}\quad\checkmark$$

$$L=\|P_1-P_2\|=\sqrt{(50{,}9-50{,}9)^2+(5{,}25-0{,}75)^2}=4{,}5000\ \text{m}\quad\checkmark$$

Tinggi, dengan $\mathbf d$ dari piksel atap $(1022{,}7;465{,}3)$ dan $B=P_0$:

$$\lambda=\frac{(B-\mathbf C)\cdot\mathbf d_{xy}}{\|\mathbf d_{xy}\|^2},\qquad
H=(\mathbf C+\lambda\mathbf d)_z=1{,}5000\ \text{m}\quad\checkmark$$

### 8.8 Sensitivitas konfigurasi ini

| Arah derau | $dL/dp$ | $dW/dp$ | $dH/dp$ |
|---|---|---|---|
| horizontal ($u$) | 0,038 m/px | 0,005 m/px | 0,0002 m/px |
| vertikal ($v$) | 0,014 m/px | **0,192 m/px** | 0,026 m/px |

Bacaan:

- Kendaraan **melintang**, sehingga L tegak lurus arah pandang dan membentang 167 piksel → $dL\approx0{,}038$ m/px. Baik.
- W justru sejajar arah kedalaman dan hanya membentang 14,9 piksel → $dW\approx0{,}192$ m/px, **5× lebih buruk**. Buruk.
- H → $0{,}026$ m/px, praktis sebaik L.
- Rasio $0{,}192/0{,}038\approx5{,}0=z/h=50/10$ ✓

Ini adalah ilustrasi sempurna dari invarian §7.9: konfigurasi yang menguntungkan L **merugikan** W, dan sebaliknya. Jumlah kuadratnya tetap. Untuk mendapatkan keduanya sekaligus, diperlukan fusi multi-frame (§7.7).

---

## 9. Analisis kesalahan

### 9.1 Hukum skala galat

Dari §5.2, dengan $\sigma_{\text{px}}$ galat lokasi titik (1σ, per titik ujung):

$$\boxed{\sigma_{\text{kedalaman}}\approx\sqrt{2}\;\frac{z^{2}}{f\,h}\,\sigma_{\text{px}}}
\qquad
\boxed{\sigma_{\text{lateral}}\approx\sqrt{2}\;\frac{z}{f}\,\sigma_{\text{px}}}
\qquad
\boxed{\sigma_H\approx\sqrt{2}\;\frac{z}{f}\,\sigma_{\text{px}}}$$

Faktor $\sqrt2$ berasal dari dua titik ujung yang galatnya independen. Perhatikan bahwa $\sigma_H\approx\sigma_{\text{lateral}}$: **tinggi dan lebar sama-sama dimensi "lateral"** sejauh menyangkut kondisi geometri, berbeda dari panjang yang dapat jatuh ke arah kedalaman.

Sebagai dukungan empiris independen: pada dataset KITTI, galat prediksi dimensi monokular (Metode Geo-Dist, Tabel 1 [12]) adalah panjang 0,293 m, lebar 0,071 m, tinggi 0,078 m. Panjang **4× lebih buruk** daripada lebar dan tinggi, dan penulisnya mencatat bahwa galat panjang dipengaruhi sudut yaw akibat ambiguitas satu pandangan, sedangkan galat tinggi tidak. Pola ini persis yang diprediksi hukum anisotropi di atas, meskipun berasal dari metode dan geometri kamera yang sangat berbeda.

### 9.2 Verifikasi terhadap simulasi

Simulasi Monte Carlo-Jakobian pada kamera sintetis ($h=10$ m, pitch 12°, $\sigma=1$ px) memberikan:

**f = 1920 px (1080p, HFOV ≈ 53°)**

| z | Orientasi | $\sigma_L$ | $\sigma_W$ | $\sigma_H$ | Analitik L | Analitik W/H |
|---|---|---|---|---|---|---|
| 20 m | melintang | 0,017 | 0,033 | 0,015 | 0,029 | 0,015 |
| 20 m | sejajar | 0,034 | 0,017 | 0,017 | 0,029 | 0,015 |
| 30 m | melintang | 0,024 | 0,070 | 0,021 | 0,066 | 0,022 |
| 30 m | sejajar | 0,071 | 0,024 | 0,023 | 0,066 | 0,022 |
| 40 m | melintang | 0,031 | 0,120 | 0,028 | 0,118 | 0,029 |
| 40 m | sejajar | 0,121 | 0,031 | 0,030 | 0,118 | 0,029 |
| 50 m | melintang | 0,038 | 0,183 | 0,034 | 0,184 | 0,037 |
| 50 m | sejajar | 0,184 | 0,038 | 0,036 | 0,184 | 0,037 |
| 70 m | sejajar | 0,352 | 0,053 | 0,049 | 0,361 | 0,052 |
| 100 m | sejajar | 0,703 | 0,087 | 0,068 | 0,737 | 0,074 |

Kesesuaian dengan hukum analitik dalam 10% pada $z\ge 40$ m. Penyimpangan pada jarak dekat disebabkan oleh pendekatan $z_c\approx z$ dan korelasi antar titik ujung.

**f = 3200 px (lensa tele, HFOV ≈ 33°)**

| z | Orientasi | $\sigma_L$ | $\sigma_W$ | $\sigma_H$ |
|---|---|---|---|---|
| 30 m | sejajar | 0,042 | 0,015 | 0,014 |
| 40 m | sejajar | 0,073 | 0,019 | 0,018 |
| 50 m | sejajar | 0,111 | 0,023 | 0,022 |
| 70 m | sejajar | 0,211 | 0,032 | 0,029 |
| 100 m | sejajar | 0,422 | 0,047 | 0,041 |

**Pelajaran:** menggandakan focal length memotong galat menjadi separuh di kedua arah, tetapi **tidak** mengubah rasio anisotropi. Untuk 5 cm pada L di 50 m, dibutuhkan $f\approx 6800$ px — di luar jangkauan CCTV 1080p praktis.

### 9.3 Anggaran galat lengkap

Untuk kamera 1080p, $f=1920$, $h=10$ m, $z=40$ m, geometri 45° terhadap sumbu jalan (§7.9), satu kali kalibrasi RTK:

| Sumber | Mekanisme | $\sigma_L$ | $\sigma_W$ | $\sigma_H$ | Sifat |
|---|---|---|---|---|---|
| Derau piksel (1 px) | $\sqrt{(\sigma_{\text{dep}}^2+\sigma_{\text{lat}}^2)/2}$ | 8,8 cm | 8,8 cm | 3,0 cm | acak |
| Skala (RTK 0,5%) | linear | 2,3 cm | 0,9 cm | 0,8 cm | sistematis |
| Ketidakrataan jalan (2 cm) | $\Delta z/\tan\theta$, terbagi 45° | 6,6 cm | 6,6 cm | 2,0 cm | sistematis, lokal |
| Distorsi lensa residual | 1–2 px di tepi | ~5 cm | ~2 cm | ~2 cm | sistematis |
| Heading (1°) | pertukaran L–W | 4 cm | 1,6 cm | 0 | acak |
| Prior bentuk | penyusutan Bayes | 5–20 cm | 3–10 cm | 5–15 cm | sistematis |
| **Total (RSS, tanpa prior)** | | **≈13 cm** | **≈11 cm** | **≈4 cm** | |
| **Total (dengan prior)** | | **≈14 cm** | **≈12 cm** | **≈11 cm** | |

**Perbandingan konfigurasi.** Dengan geometri tegak lurus terhadap sumbu jalan, tabel yang sama memberi L ≈7,5 cm tetapi W ≈16 cm. Dengan geometri 45°, keduanya menjadi ≈13 dan ≈11 cm. Ini adalah perwujudan angka dari invarian §7.9: sudut 45° meminimalkan galat **maksimum**.

**Catatan penting:** galat ketidakrataan jalan (6,6 cm per dimensi) **tidak mengecil dengan jarak**. Ia menjadi lantai (floor) yang hanya dapat diturunkan dengan meratakan/mengukur permukaan atau memperbesar sudut depresi.

Jika RTK tidak tersedia dan skala diambil dari lebar lajur nominal (galat 1,4%), tambahkan 6,3 / 2,5 / 2,1 cm secara kuadratik pada kolom L / W / H.

Catatan: galat sistematis tidak boleh dijumlahkan secara RSS jika ingin interval kepercayaan yang benar. Untuk keperluan praktis, gunakan $u = k\sqrt{\sum u_i^2}$ dengan $k=2$ (95%) dan **tambahkan** bias yang diketahui secara linear, sesuai kerangka GUM [18].

### 9.4 Hierarki sumber galat

Berdasarkan besarnya pengaruh:

1. **Derau piksel pada arah kedalaman** — mendominasi L untuk $z>30$ m. Tidak dapat dikurangi tanpa mengubah geometri.
2. **Prior bentuk** — mendominasi H dan W secara sistematis; tidak dapat dirata-ratakan.
3. **Referensi skala** — dominan jika tidak disurvei (19 cm!) tetapi dapat dihilangkan hampir seluruhnya dengan RTK.
4. **Ketidakrataan jalan** — dominan pada sudut depresi kecil; 2 cm tonjolan → 9 cm galat.
5. **Distorsi lensa** — signifikan jika tidak dimodelkan; hilang jika dikalibrasi.
6. **Orientasi kamera** — mengejutkan, kecil (§9.5).

### 9.5 Kesalahan orientasi sebagian besar terserap

Simulasi dengan pitch yang salah, sementara seluruh geometri diturunkan secara konsisten dari pose yang salah itu:

| Galat pitch | $\Delta L$ | $\Delta W$ | $\Delta H$ |
|---|---|---|---|
| 0,05° | −2,0 cm | −1,5 cm | −0,6 cm |
| 0,10° | −3,9 cm | −3,0 cm | −1,2 cm |
| 0,25° | −9,6 cm | −7,5 cm | −3,0 cm |
| 0,50° | −18,8 cm | −14,4 cm | −5,8 cm |

**Mengapa kecil?** Kesalahan orientasi memutar seluruh rekonstruksi secara hampir kaku. Yang berubah adalah posisi titik-titik di dalam kerangka yang ikut berputar, bukan bentuk internalnya. Ini berbeda dengan estimasi naif yang menganggap galat pitch setara galat piksel.

**Implikasi:** kalibrasi orientasi tidak perlu presisi ekstrem (0,2° sudah cukup), **asalkan** homografi dan arah vertikal diturunkan dari model yang sama dan konsisten. Jika homografi diambil dari anotasi manual sementara arah vertikal dari sumber lain, sifat saling meniadakan ini hilang.

**Yang tidak terserap:** deviasi lokal bidang tanah. Itu bukan rotasi kaku, melainkan deformasi, dan langsung masuk ke hasil.

### 9.6 Pencemaran prior — masalah terbesar untuk penegakan

Estimasi Bayes linear-Gaussian:

$$\hat{\theta}=\frac{\sigma_{\text{lik}}^{-2}\,y+\sigma_{\text{prior}}^{-2}\,\mu}{\sigma_{\text{lik}}^{-2}+\sigma_{\text{prior}}^{-2}}$$

Faktor penyusutan ke rata-rata kelas:

$$s=\frac{\sigma_{\text{lik}}^{2}}{\sigma_{\text{lik}}^{2}+\sigma_{\text{prior}}^{2}}$$

| $\sigma_{\text{prior}}$ (kelas) | $\sigma_{\text{lik}}$ (pengukuran) | Faktor penyusutan $s$ | Kendaraan 2,60 m dilaporkan sebagai |
|---|---|---|---|
| 0,05 m | 0,05 m | 0,50 | 2,55 m |
| 0,10 m | 0,05 m | 0,20 | **2,52 m** |
| 0,15 m | 0,05 m | 0,10 | 2,51 m |

Dengan kata lain: jika prior kelas punya simpangan 10 cm, sebuah truk selebar 2,60 m akan dilaporkan 2,52 m — **di bawah ambang 2,50 m ditambah toleransi**. Sistem akan meloloskan pelanggaran.

Ini bukan cacat implementasi; ini perilaku matematis yang benar dari estimasi berprior. Pendekatan serupa dipakai luas di deteksi monokular: SMOKE memprediksi residual logaritmik terhadap dimensi rata-rata kategori, $h=\bar h\,e^{\delta_h}$ [13], sehingga estimasi tidak pernah jauh dari rata-rata kelas. Untuk keperluan pengukuran, prior harus:

- dilebarkan (kovarians besar) sehingga $s\to 1$,
- dipisahkan per sub-kelas yang sangat spesifik (merek–model–tahun), atau
- dilaporkan eksplisit bersama ketidakpastiannya, sehingga pengguna tahu bahwa angka itu bukan pengukuran murni.

Sochor dkk. [8] menemukan masalah analog dari sisi kalibrasi: metode berbasis kotak pembatas dengan dimensi rata-rata kendaraan menghasilkan **bias sistematis yang bergantung sudut pandang**. Mereka menggantinya dengan pencocokan model 3D kendaraan spesifik dan menurunkan galat jarak dari 1,23 m menjadi 0,26 m.

### 9.7 Sumber galat lain yang sering diabaikan

| Sumber | Besar | Catatan |
|---|---|---|
| Bayangan | 0,3–2 m | Harus dihilangkan sebelum estimasi alas [7] |
| Oklusi parsial | tak terbatas | CAROM membuang kotak jika oklusi terdeteksi [2] |
| Kendaraan tidak boxy | 5–15 cm | Bus, truk bak, kendaraan modifikasi |
| Muatan di atap | tak terbatas | Prior akan "menarik" tinggi ke bawah |
| Rolling shutter | ~8 cm @30 km/jam | Bergantung sensor |
| Kompresi H.264 | 0,5–1 px | Bitrate rendah memperburuk keypoint |
| Embun/air di kubah | 1–5 px lokal | Deteksi via residu fitur statis |
| Perubahan fokus (autofocus) | mengubah $f$ | Matikan autofocus |
| Suhu (ekspansi tiang) | ~0,01 mm/K·m | 10 m tiang, 30 K → 3,6 mm; dapat diabaikan |

### 9.8 Ketidakpastian harus dilaporkan per kendaraan

Karena galat sangat bergantung pada posisi dan orientasi kendaraan, satu angka tunggal untuk seluruh sistem menyesatkan. Keluaran yang benar adalah

$$\big(\hat L,\;\hat W,\;\hat H,\;\Sigma\big)$$

dengan $\Sigma$ dari Jacobian pada solusi optimal:

$$\Sigma_\theta=\left(J^\top\Sigma_{\text{pix}}^{-1}J\right)^{-1}$$

Ini juga berfungsi sebagai **gerbang kualitas**: tolak pengukuran jika $\sigma_L>0{,}15$ m, atau jika kendaraan berada pada sudut aspek buruk.

---

## 10. Kalibrasi otomatis

Persyaratan "tanpa anotasi manual" perlu ditafsirkan dengan tepat. Ada dua hal berbeda:

| Jenis | Biaya | Dapat diotomatiskan? |
|---|---|---|
| Anotasi **per kendaraan** | besar, berulang | **Ya** — ini yang diminta |
| Kalibrasi **per lokasi** | kecil, sekali | Sebagian; lebih baik disurvei |

Rekomendasi: kalibrasi satu kali per lokasi (survei), lalu nol anotasi per kendaraan. Ini memenuhi semangat persyaratan dan memberikan akurasi terbaik.

### 10.1 Metode A — vanishing point dari marka jalan

**Cara kerja.** Deteksi batas lajur (Hough, atau jaringan segmentasi). Kelompokkan garis sejajar, RANSAC untuk VP. Dua arah jalan yang berbeda (mis. jalan utama dan jalan simpang) memberi dua VP ortogonal; garis vertikal bangunan/tiang memberi VP ketiga.

**Kelebihan:** sepenuhnya otomatis, tidak butuh data kendaraan.
**Kelemahan:** butuh marka yang jelas dan lurus; jalan menikung merusak asumsi.
**Akurasi khas:** galat pengukuran jarak pada bidang jalan orde 2% (rata-rata 1,9%, terburuk 5,6% pada 163 pengukuran) [7].

### 10.2 Metode B — vanishing point dari lintasan kendaraan

**Cara kerja.** Seperti CAROM 2021: optical flow pada badan kendaraan, RANSAC untuk mencari titik pertemuan vektor-vektor yang konsisten, sepanjang garis horizon [2]. Untuk kendaraan yang bergerak lurus, arah gerak = arah lajur.

**Kelebihan:** tidak butuh marka; bekerja di jalan tanpa marka.
**Kelemahan:** butuh volume kendaraan; kendaraan berbelok mengotori data.
**Catatan:** CAROM 2021 melaporkan kegagalan ketika kendaraan berhenti, terlalu jauh, atau RANSAC gagal [2].

### 10.3 Metode C — deteksi VP dengan CNN

**Cara kerja.** Jaringan menghasilkan heatmap VP dalam parameterisasi diamond space, sehingga VP di luar citra (termasuk di tak hingga) tetap dapat direpresentasikan [10]. Pasangan VP per kendaraan memberi kendala ortogonalitas → $f$ dan orientasi bidang jalan.

**Kelebihan:** menangani VP jauh di luar citra — kasus umum pada lensa tele.
**Kelemahan:** butuh pelatihan; generalisasi antar-lokasi perlu diuji.

### 10.4 Metode D — dimensi statistik kendaraan

**Cara kerja.** Kumpulkan histogram dimensi kotak 3D dari ribuan kendaraan; cocokkan median dengan median dimensi kendaraan yang diketahui; skala = rasio [7].

**Kelebihan:** benar-benar otomatis.
**Kelemahan serius:** kotak pembatas **tidak pernah rapat** karena kendaraan tidak kotak dan sudut membulat. Derajat kepadatan bergantung sudut pandang → **bias sistematis yang bergantung posisi kamera** [8]. Dubská dkk. melaporkan galat jarak 1,9% (terburuk 5,6%) [7], tetapi Sochor dkk. menunjukkan bahwa metode ini kalah jauh dari pencocokan model: 1,23 m versus 0,26 m galat rata-rata [8].

**Putusan:** dapat dipakai untuk bootstrap awal, **tidak** untuk kalibrasi final.

### 10.5 Metode E — pencocokan model 3D kendaraan spesifik

**Cara kerja.** Klasifikasi merek–model–varian–tahun (VGG/CNN), render model 3D yang sesuai, cocokkan bounding box dengan IoU, skala dari panjang model yang diketahui [8].

**Kelebihan:** galat terbaik di kelasnya untuk kalibrasi otomatis (0,26 m rata-rata, 2,33%; 0,10 m dengan skala manual).
**Kelemahan:** butuh dataset dan model 3D; bergantung kualitas klasifikasi (akurasi 0,97 dilaporkan [8]).

### 10.6 Metode F — survei RTK satu kali (rekomendasi)

**Cara kerja.** Ukur 4–8 titik di zona ukur dengan RTK GNSS (±1–2 cm). Titik dapat berupa: sudut marka, tiang, lubang got, batas perkerasan. Kalibrasi diselesaikan dengan resection + least-squares.

**Kelebihan:** akurasi terbaik (0,5% atau lebih baik); sekali kerja untuk bertahun-tahun; menjadi **acuan kebenaran** untuk memantau drift.
**Kelemahan:** butuh kunjungan lapangan dan izin.

### 10.7 Resep gabungan yang diusulkan

```
Tahap 0  (sekali, offline, otomatis)
  ├─ deteksi marka & garis vertikal  → v_x, v_y, v_z
  ├─ f dari persamaan ortogonalitas (7.6)
  ├─ R dari tiga VP (7.6)
  └─ cek konsistensi: reproyeksi garis marka < 0,5 px

Tahap 1  (sekali, survei)
  ├─ 6 titik RTK pada bidang tanah
  ├─ selesaikan h dan (C_x, C_y) dengan least-squares
  └─ simpan K, R, t, kovarians

Tahap 2  (otomatis, berjalan terus)
  ├─ monitor pose: reproyeksi fitur statis (tiang, marka) [17]
  │   jika RMS > 0,3 px → alarm drift/PTZ
  ├─ deteksi & lacak kendaraan
  ├─ estimasi keypoint + kotak 3D (7.5)
  ├─ fusi multi-frame (7.7)
  └─ keluarkan (L, W, H, Σ) + skor kualitas
```

Tahap 0 dan 1 adalah biaya satu kali. Tahap 2 tidak memerlukan anotasi apa pun per kendaraan.

### 10.8 Kalibrasi mandiri tanpa survei sama sekali

Jika survei mustahil, urutan fallback:

1. **Lebar lajur dari citra** — jika marka terdeteksi, lebar lajur dapat diukur relatif; tetap butuh satu angka nominal (3,0–3,6 m menurut kelas jalan). Ketidakpastian ±5–15 cm → galat 1,4–4,3%.
2. **Dimensi kendaraan yang lolos uji tipe** — kendaraan baru di Indonesia memiliki data dimensi pada dokumen uji tipe. Jika pelat nomor terbaca dan database diakses, dimensi dapat diambil. Ini mengubah masalah menjadi identifikasi, bukan pengukuran — berguna untuk validasi, tidak untuk penegakan.
3. **Jarak antar-marka putus-putus** — jika sesuai standar, dapat menjadi referensi.
4. **Tinggi kamera dari DEM/peta topografi** — akurasi biasanya buruk (>1 m).

Semua fallback ini memberi akurasi 2–5%, cukup untuk screening, tidak untuk metrologi.

---

## 11. Putusan

### 11.1 Kompatibilitas komponen CAROM Air

| Komponen CAROM Air | Status untuk CCTV | Tindakan |
|---|---|---|
| Model pinhole $K[R\vert\mathbf t]$ | **Pertahankan** | Tambahkan model distorsi |
| Asumsi bidang tanah datar | **Pertahankan, perkuat** | Model tanah per-segmen (makalah sudah menyinggung "piecewise flat ground" [1]) |
| PnP dengan titik peta 8–16 | **Ganti** | Kalibrasi otomatis VP + survei (§10) |
| Rekalibrasi per frame (drift) | **Buang** | Kamera statis; ganti dengan monitor pose |
| Keypoint R-CNN 33 titik | **Latih ulang** | Distribusi sudut pandang berbeda; 8–14 titik terlihat |
| Prior bentuk PCA | **Pertahankan, lebarkan** | Kovarians per kelas; laporkan posterior |
| Fitting 3-DoF di bidang tanah | **Pertahankan** | Tetap 3-DoF, tetapi solver nonlinear penuh |
| Solver mendekati linear (weak perspective) | **Buang** | LM penuh dengan Jacobian analitik |
| EKF sepeda + dimensi konstan | **Pertahankan, tingkatkan** | Jadikan fusi multi-frame sebagai estimator utama (§7.7) |
| Skala dari peta | **Ganti** | Survei RTK atau referensi metrik lokal |
| Evaluasi pada mobil terparkir @85 m | **Tidak berlaku** | Perlu evaluasi pada lalu lintas nyata, berbagai sudut |

### 11.2 Yang benar-benar dapat diadaptasi

**Ya, dengan batas berikut:**

1. **Kerangka geometrinya utuh.** Homografi tanah, back-projection, perpotongan sinar–garis vertikal, cross-ratio, fitting kotak 3D — semuanya berlaku untuk kamera apa pun. Tidak ada yang khusus drone.
2. **L dan W dapat diukur dengan baik**, asalkan geometrinya diperhatikan: 1,5–2,4 cm untuk dimensi tegak lurus arah pandang dan 3,4–7,1 cm untuk yang sejajar, pada 20–30 m dengan kalibrasi tersurvei. Karena keduanya bertukar peran (§7.9), geometri 45° memberi ≈3–5 cm untuk keduanya.
3. **H dapat diukur dengan baik** pada CCTV miring — justru lebih baik daripada pada drone: 1,5–4 cm pada 20–50 m.
4. **Kalibrasi otomatis layak** untuk komponen rotasi dan focal length; komponen skala paling baik disurvei sekali.

### 11.3 Yang tidak dapat diadaptasi

1. **Angka akurasi CAROM Air tidak berpindah.** 7,5 cm untuk L hanya mungkin pada GSD 2,4 cm/px dengan pandangan nadir. Pada CCTV 50 m, L yang sejajar arah pandang 2,5× lebih buruk.
2. **Kendaraan head-on tidak terukur panjangnya.** Degenerasi geometris, bukan keterbatasan algoritma.
3. **Metrologi legal (±2–3 cm) tidak tercapai** dengan satu CCTV tak tersurvei pada jarak jauh. Diperlukan stereo, gerbang ukur khusus, atau prosedur tersertifikasi.
4. **Prior bentuk tidak dapat dihilangkan** jika hanya ada satu pandangan miring — dan prior berarti hasil bukan pengukuran murni.

### 11.4 Matriks kelayakan per keperluan

| Keperluan | Akurasi perlu | Tercapai dengan 1 CCTV? | Konfigurasi |
|---|---|---|---|
| Statistik dimensi kendaraan | ±20 cm | **Ya** | Kamera apa pun, kalibrasi otomatis |
| Klasifikasi golongan kendaraan | ±15 cm | **Ya** | Seperti di atas |
| Deteksi kandidat ODOL (screening) | ±15 cm | **Ya** | $h\ge8$ m, $z\le40$ m, survei |
| Deteksi kandidat ODOL (presisi lebih tinggi) | ±10 cm | **Marginal** | $z\le30$ m, 45°, RTK, multi-frame |
| Pra-seleksi jembatan timbang | ±5–10 cm | **Marginal** | Tele, $z\le25$ m, RTK, multi-frame |
| Penegakan batas 2,5 m / 4,2 m | ±2–3 cm | **Tidak** | Perlu gerbang ukur (light curtain/LiDAR) atau stereo terkalibrasi |
| Bukti hukum | tertelusur (GUM) | **Tidak** | Prosedur tersertifikasi + redundansi sensor |

### 11.5 Konteks regulasi Indonesia

PP 55/2012 Pasal 54 menetapkan batas [15]:

| Parameter | Batas |
|---|---|
| Panjang kendaraan tunggal (bukan bus) | 12.000 mm |
| Panjang bus tunggal | 13.500 mm |
| Panjang rangkaian dengan gandengan/tempelan | 18.000 mm |
| Lebar | 2.500 mm |
| Tinggi | 4.200 mm **dan** tidak lebih dari 1,7 × lebar |
| Julur belakang | maks 62,5% jarak sumbu |
| Julur depan | maks 47,5% jarak sumbu |

Perhatikan klausul tinggi: batas efektif adalah $\min(4{,}2\ \text{m},\;1{,}7\,W)$. Ini berarti galat pada W **merambat** ke batas tinggi. Untuk truk selebar 2,3 m, batas tinggi efektif adalah 3,91 m — dan galat W sebesar 5 cm menggeser ambang itu sebesar 8,5 cm.

Pengawasan di lapangan dilakukan di Unit Pelaksana Penimbangan Kendaraan Bermotor (UPPKB) berdasarkan Permenhub 134/2015 [16]. Peraturan itu menetapkan toleransi kelebihan **muatan** (5% tidak dinyatakan pelanggaran) tetapi **tidak** menetapkan toleransi kelebihan dimensi. Ketiadaan toleransi dimensi berarti ambang keputusan harus datang dari ketidakpastian pengukuran alat, bukan dari regulasi.

Untuk lebar 2,5 m, sistem dengan $\sigma_W=4$–$11$ cm (Tabel §9.3, tergantung geometri) memiliki batas keputusan 95% pada $\pm8$–$\pm22$ cm. Artinya kendaraan selebar 2,58–2,72 m masih dapat terbaca sebagai 2,50 m. Sebagai alat **screening** untuk mengarahkan ke alat ukur presisi, ini memadai — asalkan ambangnya diset lebih rendah (mis. flag pada 2,40 m) untuk mengompensasi. Sebagai dasar **tilang**, ini tidak memadai.

### 11.6 Modifikasi yang diperlukan — daftar konkret

1. **Model distorsi.** Ganti asumsi nol distorsi dengan model Brown–Conrady ($k_1,k_2,p_1,p_2,k_3$), dikalibrasi per kamera.
2. **Kalibrasi otomatis.** Ganti PnP-dengan-peta dengan resep VP + survei (§10.7).
3. **Detektor keypoint baru.** Latih ulang pada sudut pandang CCTV; turunkan ke 12–16 keypoint yang benar-benar terlihat; tambahkan head visibilitas dan ketidakpastian per keypoint.
4. **Solver nonlinear penuh.** Buang aproksimasi weak-perspective; gunakan LM dengan Jacobian analitik dan robust loss.
5. **Fusi multi-frame dengan dimensi konstan.** Ini yang mengubah sistem dari "pengukuran per frame" menjadi "pengukuran per kendaraan" (§7.7).
6. **Prior yang jujur.** Kovarians per kelas yang lebar; laporkan posterior; sediakan mode "tanpa prior" untuk penegakan (dengan konsekuensi galat lebih besar tetapi tidak bias).
7. **Keluaran ketidakpastian.** Setiap pengukuran disertai $\Sigma$ dan skor kualitas; tolak otomatis jika di luar ambang.
8. **Monitor pose.** Deteksi drift/PTZ/getaran via reproyeksi fitur statis.
9. **Penanganan oklusi eksplisit.** Masker visibilitas; tolak jika titik alas tidak terlihat.
10. **Definisi measurand.** Tetapkan apakah W adalah lebar bodi, lebar total, atau track width; kalibrasi konsisten dengan definisi itu.

---

## 12. Arsitektur yang diusulkan

### 12.1 Tiga tingkat

**Tingkat A — Screening (akurasi ±15–25 cm)**
Kamera eksisting, kalibrasi otomatis VP, tanpa survei. Keluaran: flag kandidat anomali dimensi. Berguna untuk prioritisasi.

**Tingkat B — Measurement (±5–10 cm)**
Kamera tetap $h\ge8$ m, lensa 6–12 mm ($f\ge2000$ px), zona ukur 20–40 m, RTK 6 titik, fusi multi-frame. Keluaran: estimasi dimensi dengan ketidakpastian. Cukup untuk statistik, klasifikasi, dan pra-seleksi.

**Tingkat C — Enforcement (±2–3 cm)**
Diperlukan redundansi: stereo terkalibrasi, atau gerbang ukur (light curtain / LiDAR 1D / sensor profil), atau kamera tunggal tersurvei dengan zona ukur 10–20 m dan prosedur tersertifikasi. CV berperan sebagai pemicu dan verifikasi, bukan alat ukur tunggal.

### 12.2 Spesifikasi minimum Tingkat B

| Komponen | Spesifikasi | Alasan |
|---|---|---|
| Resolusi | ≥ 1920×1080, disarankan 2560×1440 | $f$ efektif menentukan $\sigma$ |
| Focal length | $f\ge2000$ px (HFOV ≈ 50°) | Galat ∝ $1/f$ |
| Lensa | prime (bukan varifocal), fokus tetap | Stabilitas $f$ |
| Shutter | global (diutamakan) | Rolling shutter → skew |
| Frame rate | ≥ 25 fps | $N_{\text{eff}}$ untuk fusi |
| Bitrate | ≥ 4 Mbps per stream | Presisi keypoint |
| Tinggi pemasangan | 8–15 m | Rasio $z/h$ |
| Depresi | 12–25° | Kompromi H vs oklusi |
| Zona ukur | 20–45 m | $\sigma_L$ kuadratik |
| Geometri | kamera 40–50° terhadap sumbu jalan (minimax §7.9); tegak lurus hanya jika L diprioritaskan | Redistribusi galat L–W |
| Permukaan jalan | datar ±2 cm dalam zona | $\Delta z/\tan\theta$ |
| Kalibrasi | 6 titik RTK, residu < 0,5 px | Skala |
| Pencahayaan | hindari backlight ekstrem | Keypoint |

### 12.3 Yang tidak boleh dilakukan

- Menempatkan kamera di ujung jalan menghadap lalu lintas datang, lalu berharap mengukur panjang.
- Memakai lensa wide (2,8 mm) untuk zona jauh.
- Menggunakan autofokus atau varifocal yang dapat bergeser.
- Mengandalkan lebar lajur nominal sebagai satu-satunya referensi skala.
- Melaporkan satu angka dimensi tanpa ketidakpastian.
- Memakai hasil berprior untuk keputusan hukum.

---

## 13. Keterbatasan kajian

1. **Tidak ada eksperimen lapangan.** Seluruh angka galat berasal dari (a) hukum propagasi analitik yang diturunkan di sini, (b) verifikasi numerik pada kamera sintetis (Lampiran B), dan (c) angka yang dilaporkan literatur. Validasi pada CCTV nyata di Indonesia diperlukan sebelum adopsi.
2. **Angka CAROM Air berasal dari satu eksperimen.** Evaluasi dimensi dilakukan pada satu mobil terparkir, drone 85 m, enam track, 20 menit [1]. Generalisasi ke lalu lintas padat belum diuji oleh penulisnya.
3. **Model kotak mengasumsikan kendaraan kaku dan boxy.** Bus, truk bak terbuka, kendaraan dengan muatan tinggi, dan kendaraan modifikasi menyimpang jauh.
4. **Analisis mengasumsikan bidang tanah datar.** Model tanah per-segmen dapat memperbaiki, tetapi menambah parameter yang harus dikalibrasi.
5. **Referensi yang diakses terbatas.** Beberapa makalah (mis. IEEE Xplore) hanya tersedia abstraknya; angka diambil dari versi arXiv atau halaman penerbit.
6. **Tidak membahas aspek hukum pembuktian.** Persyaratan metrologi legal (ketertelusuran, sertifikasi alat) berada di luar lingkup dan memerlukan kajian tersendiri.

---

## 14. Referensi

[1] D. Lu, E. Eaton, M. Weg, W. Wang, S. Como, J. Wishart, H. Yu, Y. Yang, "CAROM Air — Vehicle Localization and Traffic Scene Reconstruction from Aerial Videos," *IEEE ICRA*, 2023. arXiv:2306.00075. https://arxiv.org/abs/2306.00075

[2] D. Lu, V. C. Jammula, S. Como, J. Wishart, Y. Chen, Y. Yang, "CAROM — Vehicle Localization and Traffic Scene Reconstruction from Monocular Cameras on Road Infrastructures," *IEEE ICRA*, 2021, pp. 11725–11731. arXiv:2104.00893. https://arxiv.org/abs/2104.00893

[3] R. Hartley, A. Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed., Cambridge University Press, 2003.

[4] A. Criminisi, I. Reid, A. Zisserman, "Single View Metrology," *International Journal of Computer Vision*, vol. 40, no. 2, pp. 123–148, 2000.

[5] B. Caprile, V. Torre, "Using Vanishing Points for Camera Calibration," *International Journal of Computer Vision*, vol. 4, no. 2, pp. 127–139, 1990.

[6] Z. Zhang, "A Flexible New Technique for Camera Calibration," *IEEE Trans. Pattern Analysis and Machine Intelligence*, vol. 22, no. 11, pp. 1330–1334, 2000.

[7] M. Dubská, A. Herout, J. Sochor, "Automatic Camera Calibration for Traffic Understanding," *British Machine Vision Conference (BMVC)*, 2014. https://bmva-archive.org.uk/bmvc/2014/papers/paper013/index.html

[8] J. Sochor, R. Juránek, A. Herout, "Traffic Surveillance Camera Calibration by 3D Model Bounding Box Alignment for Accurate Vehicle Speed Measurement," *Computer Vision and Image Understanding*, vol. 161, pp. 87–98, 2017. arXiv:1702.06451.

[9] M. H. Zwemer, D. Scholte, R. G. J. Wijnhoven, P. H. N. de With, "3D Detection of Vehicles from 2D Images in Traffic Surveillance," *VISAPP*, 2022. https://www.scitepress.org/Papers/2022/107836/107836.pdf

[10] V. Kocur, M. Ftáčnik, "Traffic Camera Calibration via Vehicle Vanishing Point Detection," *ICANN*, 2021. arXiv:2103.11438. https://arxiv.org/abs/2103.11438

[11] X. Ma, Y. Zhang, D. Xu, D. Zhou, S. Yi, H. Li, W. Ouyang, "Delving into Localization Errors for Monocular 3D Object Detection," *CVPR*, 2021. arXiv:2103.16237.

[12] X. Shi, Q. Ye, X. Chen, C. Chen, Z. Chen, T.-K. Kim, "Geometry-based Distance Decomposition for Monocular 3D Object Detection," *ICCV*, 2021. arXiv:2104.03775.

[13] Z. Liu, Z. Wu, R. Tóth, "SMOKE: Single-Stage Monocular 3D Object Detection via Keypoint Estimation," *CVPR Workshops*, 2020. arXiv:2002.10111.

[14] T. F. Cootes, C. J. Taylor, D. H. Cooper, J. Graham, "Active Shape Models — Their Training and Application," *Computer Vision and Image Understanding*, vol. 61, no. 1, pp. 38–59, 1995.

[15] Republik Indonesia, *Peraturan Pemerintah Nomor 55 Tahun 2012 tentang Kendaraan*, Pasal 54.

[16] Kementerian Perhubungan RI, *Peraturan Menteri Perhubungan Nomor 134 Tahun 2015 tentang Penimbangan Kendaraan Bermotor di Jalan*.

[17] D. G. Lowe, "Distinctive Image Features from Scale-Invariant Keypoints," *International Journal of Computer Vision*, vol. 60, no. 2, pp. 91–110, 2004.

[18] ISO/IEC Guide 98-3:2008, *Uncertainty of Measurement — Part 3: Guide to the Expression of Uncertainty in Measurement (GUM)*.

[19] K. He, G. Gkioxari, P. Dollár, R. Girshick, "Mask R-CNN," *ICCV*, 2017, pp. 2961–2970.

---

## Lampiran A: notasi

| Simbol | Arti | Satuan |
|---|---|---|
| $L, W, H$ | panjang, lebar, tinggi kendaraan | m |
| $K$ | matriks intrinsik | — |
| $f_x, f_y$ | focal length dalam piksel | px |
| $c_x, c_y$ | titik utama | px |
| $R$ | rotasi dunia→kamera | — |
| $\mathbf t$ | translasi dunia→kamera | m |
| $\mathbf C$ | pusat kamera di dunia | m |
| $h$ | tinggi kamera di atas tanah | m |
| $\theta$ | sudut depresi (pitch) | rad |
| $\psi$ | yaw kamera | rad |
| $\phi$ | roll kamera | rad |
| $z$ | jarak sepanjang sumbu optik | m |
| $X, Y$ | koordinat tanah | m |
| $H$ (matriks) | homografi | — |
| $\mathbf v_i$ | vanishing point arah $i$ | px |
| $\mathbf l$ | garis horizon | — |
| $\omega$ | conic absolut $\omega=K^{-\top}K^{-1}$ | — |
| $\mathbf b$ | parameter bentuk PCA | — |
| $\Phi$ (matriks) | basis PCA | — |
| $\mathbf s_m$ | bentuk rata-rata | m |
| $\alpha_j$ | visibilitas keypoint | {0,1} |
| $\beta$ | sudut aspek kendaraan terhadap arah pandang | rad |
| $\sigma$ | simpangan baku (1σ) | m atau px |
| $\lambda$ | pengali Lagrange / skala proyektif | — |
| GSD | ground sample distance | m/px |

---

## Lampiran B: verifikasi numerik

Seluruh formula dalam laporan ini diverifikasi dengan implementasi JavaScript mandiri tanpa dependensi — `verify_geometry.mjs` (proyeksi, kalibrasi VP, rekonstruksi, Jacobian), `worked_example.mjs` (contoh §8), dan `sensitivity_check.mjs` (sensitivitas per sumbu) — yang membangun kamera sintetis, memproyeksikan kotak 3D, lalu merekonstruksi dimensinya dari citra.

### Uji 1 — rekonstruksi eksak

| Konfigurasi | $f$ terestimasi | galat maks $R$ | L | W | H |
|---|---|---|---|---|---|
| CCTV wide, $f=1200$, $h=10$, pitch 15°, roll 1,5° | 1200,0 | $1{,}1\times10^{-16}$ | 4,5000 | 1,8000 | 1,5000 |
| CCTV tele, $f=3200$, $h=10$, pitch 15°, roll 1,5° | 3200,0 | $1{,}1\times10^{-16}$ | 4,5000 | 1,8000 | 1,5000 |
| Drone nadir, $f=3600$, $h=85$ | tidak dihitung¹ | $1{,}1\times10^{-16}$ | 4,5000 | 1,8000 | 1,5000 |

¹ Pada konfigurasi nadir ($\theta\to90°$), arah dunia $X$ dan $Y$ sejajar bidang citra, sehingga kedua VP horizontal berada di tak hingga dan kendala ortogonalitas menjadi trivial: $f$ **tidak teramati** dari keduanya dan harus diberikan dari kalibrasi laboratorium. Untuk $\theta=89{,}9°$ nilainya masih dapat dihitung tetapi berkondisi sangat buruk. Untuk CCTV dengan pitch 10–30°, degenerasi ini tidak terjadi: $\mathbf v_z$ berada pada baris $c_y+f\cot\theta$, berhingga dan teramati.

### Uji 1b — cross-ratio Criminisi

Dengan tiang referensi 3,00 m di tempat lain dalam scene:

$$\hat H_{\text{mobil}}=1{,}5000\ \text{m}\quad(\text{benar }1{,}5\ \text{m})$$

Eksak.

### Uji 2 — Jacobian numerik vs analitik

Tabel §9.2. Kesesuaian dalam 10% untuk $z\ge40$ m. Ini memvalidasi hukum $\sigma\propto z^2/(fh)$ dan $\sigma\propto z/f$.

### Uji 3 — sensitivitas tinggi pada nadir

$h=85$ m, $f=3600$ px:

| $s$ (offset dari nadir) | $\sigma_H$ numerik | $\sigma_H$ analitik $h^2/(fs)$ |
|---|---|---|
| 2 m | 0,448 | 1,003 |
| 5 m | 0,266 | 0,401 |
| 10 m | 0,158 | 0,201 |
| 20 m | 0,087 | 0,100 |
| 45 m | 0,041 | 0,045 |

Konvergensi ke hukum analitik pada $s$ besar. Pada $s=20$ m, nilainya **0,087 m/px — sangat dekat dengan galat H CAROM Air sebesar 0,099 m** [1]. Ini mendukung penjelasan di §4.2.

### Uji 4 — galat skala

| Referensi | Galat relatif | $\sigma_L$ pada 4,5 m | $\sigma_H$ pada 1,5 m |
|---|---|---|---|
| Lebar lajur ±0,15 m | 4,3% | 19,3 cm | 6,5 cm |
| Lebar lajur ±0,05 m | 1,4% | 6,3 cm | 2,1 cm |
| RTK | 0,5% | 2,3 cm | 0,8 cm |

### Uji 5 — galat pitch

Tabel §9.5. Menunjukkan bahwa galat orientasi sebagian besar terserap, berbeda dengan intuisi umum.

### Batasan verifikasi

Verifikasi ini menggunakan proyeksi ideal tanpa distorsi, tanpa derau non-Gaussian, dan tanpa oklusi. Ia memvalidasi **aljabar dan propagasi galat**, bukan performa pada data nyata.

---

*Dokumen ini disusun dari sumber primer (makalah ICRA, BMVC, CVIU, arXiv) dan verifikasi numerik mandiri. Angka galat bersifat prediktif dan harus divalidasi pada instalasi CCTV aktual sebelum digunakan untuk keputusan operasional.*
