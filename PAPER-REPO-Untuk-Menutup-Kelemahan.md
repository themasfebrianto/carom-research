# Paper dan Repo untuk Menutup Kelemahan

Dokumen ini menjawab satu pertanyaan: dari kelemahan yang tercatat di `RISET-CAROM-Air-untuk-CCTV.md`, mana yang bisa ditutup dengan paper atau repo yang **sudah tersedia**, tanpa menunggu survei lapangan lebih dulu?

Kriterianya empat:

1. dapat diakses publik, bukan hanya abstrak;
2. relevan dengan **kamera statis pinggir jalan**, bukan dashcam;
3. memberi ground truth metrik atau komponen pipeline yang hilang;
4. lisensinya jelas.

Satu peringatan di depan: **tidak ada satu pun sumber di bawah yang menghapus degenerasi $f$–$h$–$w$ pada instalasi baru.** Yang bisa ditutup adalah ketiadaan ground truth, ketiadaan implementasi, dan ketergantungan pada anchor lapangan. Degenerasi, anisotropi, dan keterbatasan panjang dari satu kamera tetap menjadi batas fundamental.

---

## 1. Ringkasan

| Prioritas | Kelemahan | Sumber | Jenis | Yang diberi | Akses |
|---|---|---|---|---|---|
| 1 | Nol kendaraan terukur dengan ground truth | **I24-3D** | dataset + devkit | 877.000 box 3D, $L/W/H$ per kendaraan, $P$, $H$, dan VP per kamera | registrasi, non-komersial |
| 2 | Truk dan bus belum teruji | **SVLD-3D** | dataset | 16.829 citra; bus 745 objek, truk hanya 1 | Google Drive |
| 3 | Pipeline CAROM Air belum pernah dijalankan | **SKoPe3D + OpenPifPaf + GSNet** | dataset + kode | keypoint CCTV, detektor 24/66, 79 mesh + PCA | campuran |
| 4 | Anchor menuntut kerja lapangan | **naver/cctv** | kode + model | homografi dari lintasan box, tanpa marka | CC BY-NC-SA |
| 5 | Skala metrik hanya dari satu anchor | **MoGe-2** | kode + bobot | point map metrik dari satu citra | MIT |
| 6 | Ambiguitas 2 vs 3 lajur | **RoadTagger + OSM** | paper + data | jumlah lajur dari satelit/OSM | publik |

Urutan di atas adalah urutan **dampak**, bukan urutan kemudahan. I24-3D menutup dua kelemahan sekaligus: ketiadaan ground truth dan fakta bahwa gerbang GeoCalib baru diuji pada satu titik data.

---

## 2. I24-3D — ground truth yang paling dekat dengan kasus kita

**Paper.** Derek Gloudemans, Yanbing Wang, Gracie Gumm, William Barbour, Daniel B. Work, *The Interstate-24 3D Dataset: a new benchmark for 3D multi-camera vehicle tracking*, BMVC 2023.

- **Repo.** `https://github.com/I24-MOTION/I24-3D-dataset`
- **Data.** `https://i24motion.org` (registrasi)

### 2.1 Isi

Tiga scene, masing-masing direkam oleh **16–17 kamera 4K @ 30 fps** yang dipasang di tiga tiang pinggir jalan setinggi 110 kaki, mencakup sekitar 2.000 kaki Interstate 24 dekat Nashville. Total 877.000 box 3D untuk 720 kendaraan unik. Kelasnya: sedan, midsize, van, pickup, semi, truck.

Yang membuat dataset ini sangat relevan bukan jumlah box-nya, melainkan **ground truth kalibrasinya**. Setiap kamera punya:

```text
data/hg/sceneX_hg.json
  corr_pts    titik korespondensi di citra
  space_pts   titik yang sama di citra jalan (z = 0)
  P           matriks proyeksi space -> image, disimpan 4x3
  H           homografi image -> ground plane
  H_inv       homografi ground plane -> image
  vps         tiga pasang titik: longitudinal, lateral, vertikal
```

Untuk proyek ini, pertama kalinya kita punya **puluhan kamera nyata dengan $f$, pitch, dan vanishing point yang benar**, bukan satu rekaman yang diakui tidak layak.

Anotasi kendaraannya:

```text
sceneX_annotations.csv
frame,camera,id,x,y,l,w,h,direction,class,gen
0,p1c1,0,372.043,4.141,15.924,5.722,4.48,1,sedan,manual
0,p1c1,46,464.146,103.813,35.711,8.57,12.02,-1,truck,manual
```

Satuan `x,y,l,w,h` adalah **kaki**; kalikan 0,3048 untuk meter. Contoh truk di atas: panjang 10,88 m, lebar 2,61 m, tinggi 3,66 m. Posisi `x,y` adalah **bottom-center rear** kendaraan di bidang jalan, jadi kontak ban sudah menjadi titik acuan. Galat dimensi rata-rata yang dilaporkan penulis adalah **0,5 kaki ≈ 15 cm**. Itu ketidakpastian ground truth, bukan galat pipeline; artinya pipeline tidak bisa dibuktikan lebih baik dari sekitar ±15 cm pada dataset ini. Satuan dunia I24-3D adalah kaki; $f$ tetap dalam piksel, tetapi $h$ dan translasi harus dikonversi ke meter sebelum dibandingkan dengan pipeline.

### 2.2 Apa yang bisa langsung diuji

**Uji A — GeoCalib versus kalibrasi ground truth.**

Ambil $K$ dari $P$ dengan dekomposisi RQ pada blok 3×3:

$$
P_{3\times4}=K[R\mid t],\qquad
K=\begin{bmatrix} f_x & 0 & c_x\\ 0 & f_y & c_y\\ 0 & 0 & 1\end{bmatrix}
$$

Karena `P` disimpan dengan penulisan `[4,3]`, periksa bentuk array saat memuat. **Data nyata 19 Nov 2026 menunjukkan file berisi 3×4**, bukan 4×3. Konvensi proyeksi standar adalah **3×4** (3 baris, 4 kolom); parser menerima keduanya. Yang dipakai untuk RQ adalah blok 3×3 di kiri. Setelah $K$ dinormalisasi agar $K_{33}=1$, bandingkan:

Namun `P` di kode I24-3D **dibangun** dari `H_inv` ditambah kolom VP vertikal (`homography.py`), bukan dari kalibrasi lab.

> **Koreksi 19 November 2026 — jangan pakai RQ(`P`) sebagai GT.** Data lengkap sudah diperiksa:
>
> - `P[:,2]` diskalakan `* 0.01` lalu `scale_Z()`; tidak ada jaminan `P = K[R|t]` dengan K pinhole.
> - Hanya **39/102** kalibrasi yang K-nya plausibel.
> - `f` EB vs WB untuk kamera yang sama berbeda median **7,1%**, p90 **24,6%**.
> - Ground RMS `H_inv` → `corr_pts` median **3,89 px**; **0/102** <1 px.
> - Kamera 28–45 m (median 34 m), pitch 17–75°; GeoCalib `f` meleset −52% s/d +26%, pitch 9–65°.
> - **Gerbang Δf/f <5% dan Δθ <2° tidak dapat dijalankan dengan `P`.** Laporan: `reports/i24-3d-kalibrasi/README.md`. Gunakan SVLD-3D/pengukuran lapangan untuk GT kalibrasi; I24-3D untuk GT dimensi dan ground-plane.

$$
\frac{\Delta f}{f}=\frac{|f_{\text{GeoCalib}}-f_x|}{f_x},
\qquad
\Delta\theta=\bigl|\theta_{\text{GeoCalib}}-\theta_{\text{GT}}\bigr|
$$

Catatan resolusi: pastikan acuan `P`/`H`. Jika frame yang dipakai berbeda (misalnya 1080p versus 4K), skala $f$, $c_x$, dan $c_y$ dengan rasio lebar sebelum dibandingkan dengan GeoCalib.

dengan $\theta_{\text{GT}}$ dari vanishing point longitudinal pada segmen yang landai:

$$
\theta_{\text{GT}}=\arctan\!\left(\frac{c_y-v_{\parallel,y}}{f_x}\right)
$$

Dua asumsi: roll kecil dan jalan tanpa kelandaian. Jika roll tidak nol, gunakan garis horizon dari dua VP. Jika ada kelandaian, pitch GeoCalib (relatif gravitasi) dan pitch dari $P$ (relatif bidang jalan) memang berbeda; batasi uji pada segmen landai, atau koreksi dengan grade dari $P$. Tanpa itu, selisih 2° bisa berasal dari kelandaian, bukan dari kesalahan kalibrasi.

Gerbang yang sudah dipakai di SOP (§0.3.2) adalah $\Delta\theta<2^\circ$. Sebelumnya gerbang itu hanya diuji pada **satu** rekaman. Dengan I24-3D, ia diuji pada **16–17 kamera × 3 scene ≈ 50 pasangan**. Itu langsung mengubah status gerbang dari anekdot menjadi statistik.

**Uji B — pipeline dimensi versus $L/W/H$.**

Untuk setiap kendaraan, hitung

$$
\mathrm{MAPE}_{LWH}=
\frac{1}{3N}\sum_{i=1}^{N}
\left(
\frac{|\hat L_i-L_i|}{L_i}+
\frac{|\hat W_i-W_i|}{W_i}+
\frac{|\hat H_i-H_i|}{H_i}
\right)\times100\%
$$

dan laporkan **bias** secara terpisah:

$$
\mathrm{bias}_L=\frac{1}{N}\sum_{i=1}^{N}(\hat L_i-L_i)
$$

MAPE bisa menutupi offset sistematis; bias tidak. Untuk ODOL (*over dimension, over loading*), offset sistematis justru yang paling berbahaya.

**Uji C — anisotropi $\sigma_z/\sigma_y=z/h$.**

Kelompokkan kendaraan per kedalaman $z$, lalu fit \(\sigma_z/\sigma_y\) terhadap \(z/h\). Jika hukum ini benar, kemiringannya ≈ 1. Hukum ini sudah diturunkan dan diverifikasi numerik, tetapi belum pernah diuji pada data nyata dengan ground truth. I24-3D memberi kesempatan itu.

### 2.3 Batas

- Jalan tol Amerika, bukan jalan Indonesia. Kelas kendaraan dan perilakunya berbeda.
- Hanya 720 kendaraan unik; cukup untuk validasi, tidak untuk pelatihan besar.
- Dimensi tiap kendaraan **tetap sepanjang lintasan** (satu nilai $L/W/H$ per ID). Itu bagus untuk konsistensi, tetapi tidak menangkap variasi muatan.
- Lisensi: non-komersial, pendidikan, dan riset. Akses komersial harus diminta ke `info@i24motion.org`.

---

## 3. SVLD-3D — truk dan bus di kamera pinggir jalan

**Paper.** Xinyao Tang, Huansheng Song, Wei Wang, Chunhui Zhao, *CenterLoc3D: Monocular 3D Vehicle Localization Network for Roadside Surveillance Cameras*, Complex & Intelligent Systems, 2023 (arXiv:2203.14550).

- **Repo.** `https://github.com/stjuliet/SVLD-3D-DATASET`
- **Data.** Google Drive, tautan publik di README repo.

### 3.1 Isi

Lima scene, 14.592 citra train/val dan 2.237 citra test, resolusi 1.920×1.080 dan 1.280×720. Kelas yang tersedia: **Car, Bus, Truck**. Namun distribusi test set sangat timpang: **Car 7.396, Bus 745, Truck 1**. Setiap anotasi memuat:

```text
bbox2d       kotak 2D (x, y, w, h)
vertex2d     delapan sudut box 3D di citra
vertex3d     delapan sudut box 3D di dunia, dalam milimeter
veh_size     dimensi (l, w, h) dalam meter
base_point   titik kontak tanah
```

Kalibrasi per scene tersedia di `Calib/{scene_id}.xml` dengan `f` (px), `fi` = φ = **pitch** (rad), `theta` = **yaw** (rad), dan `h` (mm). Contoh Scene A: $f=2878{,}13$ px, $\phi=0{,}17874$ rad, $\theta=0{,}26604$ rad, $h\approx10{,}12$ m. Jangan menukar `fi` dan `theta`: `fi` adalah pitch yang harus dibandingkan dengan GeoCalib; `theta` adalah yaw.

### 3.2 Angka pembanding

CenterLoc3D melaporkan **presisi dimensi rata-rata 85%** dan $AP_{3D}$ 51,30%. Perhatikan definisi metriknya:

$$
P_{\text{dim}}=\left(1-\sum_{k\in\{l,w,h\}}\frac{|k_{\text{pred}}-k_{\text{gt}}|}{k_{\text{gt}}}\right)\times100\%
$$

Jadi presisi 85% berarti **jumlah** galat relatif ketiga sumbu ≈ 15%, bukan 15% per sumbu. Secara rata-rata per sumbu itu ≈ 5%, dengan panjang sebagai sumbu terburuk. Angka ini cukup untuk menunjukkan bahwa tugasnya mungkin, tetapi belum menjawab apakah bias absolutnya cukup kecil untuk ODOL.

Yang penting: **kode model CenterLoc3D tidak tersedia di repo dataset.** Yang tersedia adalah dataset dan devkit. Jadi SVLD-3D bukan solusi siap pakai; ia adalah **benchmark** untuk mengukur pipeline kita sendiri.

**Peringatan dari uji mini.** Kalibrasi SVLD terverifikasi lewat reproyeksi 8.142 objek: median RMS 0,74 px, maksimum 1,08 px. Tetapi GeoCalib hanya lulus **1 dari 5** scene (f<5%, pitch<2°): f meleset 10-51% dan pitch 0,8-5,0°. Uji lanjutan 100 citra (10 test + 10 trainval per scene) mengonfirmasi: **20/100 lulus**, Δf median 14,9%, Δpitch 3,03°, multi-frame 1/5; hanya `session0_centre` yang layak.

**VP jalan** pada 100 citra yang sama: dengan `f` GT **95/100** lulus pitch/yaw <2° (median 0,20°/0,05°); dengan `f` GeoCalib **47/100** (median 2,46°/1,12°). VP memberi **yaw** yang tidak dimiliki GeoCalib; `f` tetap bottleneck. Urutan yang masuk akal: `f` dari dash fit/known camera/anchor → VP untuk yaw/pitch. **Lebar lajur bukan 3,6 m universal**: data SVLD memberi 2,7–3,56 m; ukur per lokasi. Untuk SVLD, pakai kalibrasi XML; jangan pakai GeoCalib sebagai sumber $f$. Ini justru bukti bahwa gerbang §0.3.2 SOP bekerja. Detail: `reports/svld-geocalib/README.md` dan `reports/svld-vp/README.md`.

**Uji geometri 50 objek.** Dengan 8 sudut 2D GT + kalibrasi XML, fitting 3D box memberi MAPE $L/W/H$ **0,36%** dan RMS reproyeksi **0,35 px** (26 Car, 24 Bus). Artinya kalibrasi dan fitting sudah benar; yang belum diuji adalah keypoint/detektor. Detail: `out/svld/fit_dims_report.md`.

### 3.3 Apa yang bisa diuji

- Jalankan pipeline $L/W/H$ pada 2.237 citra test, per kelas. Bandingkan dengan 85%.
- Gunakan scene 720p untuk meniru kondisi substream.
- **Fokus ke Bus**, bukan Truck: test set hanya punya 1 Truck. Bus memberi 745 objek kendaraan besar dengan $L$ 9,46–12,60 m, $W$ 2,57–2,76 m, $H$ 2,80–2,92 m.
- Untuk truk, gunakan I24-3D (kelas semi/truck) atau RoScenes. Jangan mengklaim validasi truk dari SVLD-3D.
- Uji apakah galat bus jauh lebih besar dari mobil. Hipotesis dari proyek ini: ya, karena panjang kendaraan besar lebih sulit diamati.

### 3.4 Catatan RoScenes

Jika butuh data truk/bus yang jauh lebih banyak, **RoScenes** (ECCV 2024) berisi 14 scene jalan tol, 6–12 kamera, dan 21,13 juta anotasi 3D dengan kelas car/van/truck/bus. Devkit tersedia via `pip install roscenes`, data via ModelScope. Tetapi lisensinya **melarang penggunaan komersial secara tegas**, dan lokasinya di jalan tol Chengdu. Untuk validasi riset, ini sumber yang sangat kuat; untuk produksi, tidak.

---

## 4. SKoPe3D + OpenPifPaf + GSNet — mengisi pipeline yang hilang

Kelemahan proyek ini bukan hanya data, tetapi juga **komponen**: CAROM Air adalah pipeline keypoint → model bentuk → fitting, dan belum ada satu pun bagian yang dijalankan pada CCTV. Tiga sumber berikut menutup bagian yang berbeda.

Catatan: repo `duolu/CAROM` hanya berisi paper dan tautan dataset. Tautan kode IAM (`Institute-of-Automated-Mobility/tracking_3d`) mengembalikan **404** saat diperiksa, jadi pipeline tetap harus dirakit dari komponen di bawah.

### 4.1 SKoPe3D — keypoint dari sudut kamera CCTV

**Paper.** Himanshu Pahadia, Duo Lu, Bharatesh Chakravarthi, Yezhou Yang, *SKoPe3D: A Synthetic Dataset for Vehicle Keypoint Perception in 3D from Traffic Monitoring Cameras*, IEEE ITSC 2023.

- **Proyek.** `https://skope3d.github.io/` dan `https://duolu.github.io/skope3d.html`

Isinya 25.000 citra dari 28 scene CARLA, 150.000 instance kendaraan, 4,9 juta keypoint, 33 keypoint per kendaraan, resolusi 1.920×1.080, dengan hujan, malam, dan fajar. Yang membedakannya dari ApolloCar3D: **sudut pandangnya kamera pinggir jalan**, bukan dashcam.

Ini menjawab keberatan utama terhadap ApolloCar3D: model keypoint yang dilatih dari sudut frontal akan melihat kendaraan dari sudut yang salah di CCTV. SKoPe3D memberi pre-training yang sesuai sudut, lalu fine-tuning pada frame CCTV nyata.

Batasnya jujur: sintetis, dan papernya sendiri menyatakan sim-to-real gap masih terasa. Pada scene sulit, keypoint gagal karena oklusi dan resolusi jauh. Karena itu ia dipakai untuk **pre-train**, bukan sebagai model final.

### 4.2 OpenPifPaf — detektor keypoint siap pakai

**Repo.** `https://github.com/openpifpaf/openpifpaf`

- **Plugin mobil.** `https://openpifpaf.github.io/plugins_apollocar3d.html`

Model `shufflenetv2k16-apollo-24` memberi 24 keypoint dengan AP 76,1% pada ApolloCar3D, dan bobotnya diunduh otomatis. Ini adalah jalur tercepat untuk mendapatkan keypoint kendaraan tanpa melatih dari nol.

Dua batas:

- dilatih pada **ApolloCar3D**, yang frontal dan street-level, sehingga domain gap ke CCTV tetap ada;
- lisensi **AGPL-3.0**. Untuk produk yang didistribusikan atau dijalankan sebagai layanan jaringan, AGPL menuntut sumber dibuka. EPFL menyediakan lisensi komersial terpisah.

### 4.3 GSNet — model bentuk yang bisa dipakai

**Paper.** Lei Ke, Shichao Li, Yanan Sun, Yu-Wing Tai, Chi-Keung Tang, *GSNet: Joint Vehicle Pose and Shape Reconstruction with Geometrical and Scene-aware Supervision*, ECCV 2020.

- **Repo.** `https://github.com/lkeab/gsnet`

Repo ini menyediakan **79 mesh mobil dengan topologi sama** (1.352 vertex, 2.700 face), mean shape, dan empat model PCA. Itu persis komponen "morphable model" yang dipakai CAROM Air: parameter bentuk $\mathbf{b}$ yang dioptimasi bersama pose.

Dua catatan penting:

- **Bobot pretrained sudah dihapus** (issue #21). Yang tersedia adalah mesh, basis PCA, dan kode; model harus dilatih atau di-fit sendiri.
- Kode berlisensi MIT, tetapi data ApolloCar3D yang dipakai untuk melatihnya **non-komersial**.

### 4.4 Yang perlu dirakit

Urutan yang masuk akal:

1. pre-train keypoint di SKoPe3D;
2. fine-tune pada 100–200 frame CCTV yang dianotasi manual (Cawang atau ATP);
3. untuk mobil, fit mesh GSNet ke keypoint dengan proyeksi perspektif penuh;
4. untuk truk dan bus, jangan paksakan mesh mobil. Gunakan box 3D dengan prior dimensi per kelas dari I24-3D/SVLD-3D, lalu ukur $L/W/H$ dari box itu.

Uji SVLD menunjukkan **4 kontak tanah + 1 sudut atap** (5 titik) sudah cukup: MAPE 0,48%, nol kegagalan. Delapan sudut memberi 0,36%, tetapi detektor tidak perlu menemukan semuanya. Fokuskan keypoint pada roda dan atap, bukan seluruh sudut box.

**Hasil zero-shot keypoint.** Model `vehicle-keypoints` (YOLO26-pose, 14 keypoint) diuji pada 20 citra SVLD: 5/5 hanya **44,1%** dari semua mobil GT dan **0%** bus. Di antara deteksi yang cocok, 78,8% mobil mencapai 5/5. Zero-shot tidak cukup; perlu fine-tuning pada sudut CCTV atau pendekatan mask-based.

**Hasil mask-based.** YOLO11n-seg + fitting siluet pada 21 objek SVLD: **W 7,1%, H 7,6%, L 21,9%**; mask IoU 0,796. Lebar dan tinggi layak untuk screening; panjang tidak. Mask body tidak memuat kontak ban, sehingga skala panjang ambigu. Arsitektur yang masuk akal: mask untuk $W/H$ + keypoint kontak tanah untuk $L$, atau fusi multi-frame.

Langkah 3 adalah tempat klaim "CAROM Air bisa diadaptasi" benar-benar diuji. CAROM Air memakai **weak perspective** karena kamera drone hampir nadir. CCTV tidak. Fitting-nya harus memakai proyeksi perspektif penuh, dan justru di situ asumsi CAROM Air tidak transfer.

### 4.5 Kriteria lulus (usulan)

- PCK@0.1 keypoint > 80% pada frame CCTV uji, minimal untuk **5 titik: 4 kontak tanah + 1 atap**.
- RMS reproyeksi sudut box **≤3 px** pada jarak 20–30 m. Pada SVLD, noise 5 px membuat 63% fitting gagal; 3 px hanya 1,7%.
- Galat $L/W/H$ pada kendaraan uji < 10%, dengan bias < 5 cm.

Angka-angka ini usulan, bukan ambang yang berasal dari paper. Jika tidak tercapai, klaim adaptasi harus diturunkan dari "bisa" menjadi "bisa dengan batasan".

---

## 5. naver/cctv — kalibrasi dari arus lalu lintas

**Paper.** Jérôme Revaud, Martin Humenberger, *Robust Automatic Monocular Vehicle Speed Estimation for Traffic Surveillance*, ICCV 2021.

- **Repo.** `https://github.com/naver/cctv`

### 5.1 Apa yang dilakukan

Metode ini hanya membutuhkan **lintasan box 2D** dari detektor off-the-shelf. Dari lintasan itu ia mengestimasi homografi jalan, termasuk focal length, tanpa marka jalan dan tanpa kalibrasi manual. Idenya: mobil punya bentuk 3D yang mirip dan dimensi yang sudah diketahui secara umum; lintasan box yang bergerak di jalan memberi cukup kendala untuk memulihkan geometri.

Dua batas teknis yang perlu dicatat: modelnya dilatih pada **mobil** (sekitar 10 model kendaraan penumpang), sehingga scene yang didominasi truk berat mungkin tidak cocok dengan prior-nya; dan model kameranya disederhanakan — roll dianggap nol dan satu vanishing point dianggap di tak hingga. Untuk Cawang dan ATP, roll ≈ 0,24°, jadi asumsi itu masih wajar, tetapi harus diverifikasi pada instalasi lain.

Pada BrnoCompSpeed dan dataset CCTV mereka, metode ini mengalahkan kalibrasi manual untuk estimasi kecepatan. Kodenya tersedia, plus model pretrained.

### 5.2 Kenapa ini relevan

Ini menjawab langsung keberatan "setiap instalasi butuh kerja lapangan". Untuk Cawang dan ATP, yang gagal justru karena marka tidak konsisten, metode ini bisa memberi $H$, $f$, dan orientasi tanpa marka. Bahkan ia bisa menjadi **inisialisasi** yang lebih baik daripada fitting marka.

### 5.3 Jebakan melingkar — wajib dibaca

Metode ini menetapkan skala dari **asumsi dimensi kendaraan**. Jika hasilnya kemudian dipakai untuk mengukur dimensi kendaraan, hasilnya akan mengembalikan asumsi itu.

Secara formal, misalkan prior dimensi $\bar d$ dan skala yang dipilih $s$, sehingga hasil ukur $\hat d_i=s\,p_i$ dengan $p_i$ ukuran proyeksi. Jika dimensi sebenarnya adalah $\alpha\bar d$ untuk suatu faktor global $\alpha$, maka citra yang sama juga konsisten dengan skala $s/\alpha$ dan prior $\bar d$. Pasangan $(s,\bar d)$ dan $(s/\alpha,\alpha\bar d)$ menghasilkan citra yang identik.

**Artinya $\alpha$ tidak teridentifikasi.** Faktor skala global diserap ke dalam kalibrasi, bukan diukur. Jika seluruh armada truk 10% lebih besar dari prior, faktor 10% itu hilang ke dalam $s$; yang tersisa hanya perbedaan **relatif** antar kendaraan. Untuk ODOL, justru bias global itulah yang menentukan.

Konsekuensinya:

| Boleh | Tidak boleh |
|---|---|
| kalibrasi kamera ($f$, pitch, homografi) | menetapkan ambang ODOL |
| estimasi kecepatan dan lintasan | mengklaim akurasi absolut $L/W/H$ |
| inisialisasi sebelum anchoring | menggantikan anchor yang diukur |

Untuk penegakan ODOL, tetap diperlukan **satu panjang yang diukur**, bukan diasumsikan. Boleh lebar lajur, boleh satu kendaraan yang diukur dengan meteran. Setelah itu, naver/cctv dipakai untuk menyebarkan skala ke seluruh scene, bukan untuk menciptakan skala.

### 5.4 Eksperimen

1. Jalankan pada Cawang dan ATP; bandingkan $f$ dan pitch dengan GeoCalib/REV2.
2. Jalankan pada BrnoCompSpeed; reproduksi galat kecepatan.
3. Ukur berapa besar skala bergeser jika prior dimensi diubah 5%. Jika pergeseran > 5%, metode ini tidak boleh dipakai sebagai anchor.

---

## 6. MoGe-2 — cek skala independen

**Paper.** Ruicheng Wang et al., *MoGe-2: Accurate Monocular Geometry with Metric Scale and Sharp Details*, NeurIPS 2025 (arXiv:2507.02546).

- **Repo.** `https://github.com/microsoft/MoGe` (MIT; DINOv2 di dalamnya Apache 2.0)

MoGe-2 memprediksi **point map metrik** dan intrinsik dari satu citra. Untuk kasus kita, kegunaannya bukan menggantikan kalibrasi, melainkan memberi **pendapat kedua** tentang skala:

1. jalankan MoGe-2 pada frame jalan;
2. ambil titik-titik di permukaan jalan;
3. fit bidang $\mathbf{n}^\top\mathbf{P}+d=0$;
4. karena pusat kamera di titik asal, tinggi kamera adalah

$$
h=\frac{|d|}{\|\mathbf{n}\|}
$$

5. bandingkan dengan anchor yang sudah diukur (Cawang: 8,876 m).

Jika $h$ dari MoGe-2 berada dalam 10% dari anchor, ia berguna sebagai pemeriksaan cepat pada instalasi baru. Jika 10–20%, perlakukan sebagai peringatan: cukup untuk menandai kecurigaan, tidak cukup untuk mengoreksi anchor. Di atas 20%, jangan dipakai. Papernya sendiri mengakui bahwa skala metrik bisa menyimpang pada domain di luar distribusi, dan CCTV jalan tol Indonesia termasuk di luar distribusi itu.

MoGe-2 bukan pengganti anchor. Ia hanya mengurangi biaya **verifikasi**.

---

## 7. Ambiguitas 2 vs 3 lajur

Ini bukan kelemahan metodologis yang besar, tetapi pertanyaan terbuka yang mahal jika dibiarkan. Untuk satu lokasi, tidak perlu model:

1. baca tag `lanes` di OpenStreetMap untuk ruas tersebut;
2. ukur lebar perkerasan di citra satelit (Google Earth atau Esri);
3. hitung

$$
N_{\text{lajur}}\approx\frac{W_{\text{perkerasan}}}{w_{\text{lajur}}}
$$

dengan $w_{\text{lajur}}$ 3,0–3,75 m. Jika lebar perkerasan sekitar 7,5 m, itu 2 lajur; jika sekitar 11 m, itu 3 lajur.

Jika ingin metode yang bisa diskalakan, **RoadTagger** (He et al., AAAI 2020) memprediksi jumlah lajur dari citra satelit + OSM dengan akurasi 77%. Untuk satu ruas, akurasi itu tidak sepadan dengan biaya; untuk ratusan ruas, baru masuk akal.

Yang perlu diingat: lebar lajur di Indonesia tidak selalu 3,5 m. Pada jalan tol, lajur bisa 3,6–3,75 m; pada jalan arteri, bisa 3,0–3,25 m. Karena itu pengukuran satelit lebih baik daripada asumsi standar.

---

## 8. Yang tetap tidak bisa ditutup

Supaya tidak ada harapan palsu:

| Kelemahan | Bisa ditutup paper/repo? | Alasan |
|---|---|---|
| Degenerasi $f$–$h$–$w$ tanpa anchor | **tidak** | informasi metrik memang tidak ada di citra |
| Anisotropi $\sigma_z/\sigma_y=z/h$ | **tidak** | konsekuensi geometri, bukan kekurangan algoritma |
| Panjang tidak teramati pada pandangan head-on | **tidak** | sisi panjang tidak terlihat |
| Domain gap Indonesia | **tidak** | semua dataset di atas berasal dari AS, Cina, atau Eropa |
| Ground truth lokal | **tidak sepenuhnya** | I24-3D/SVLD-3D adalah proksi, bukan pengganti satu kendaraan yang diukur di Indonesia |
| Ambang ODOL yang sah secara hukum | **tidak** | itu domain regulasi, bukan visi komputer |

I24-3D dan SVLD-3D memberi **bukti bahwa pipeline bisa bekerja**, bukan **izin bahwa hasilnya sah untuk penindakan**. Untuk penegakan, satu kendaraan yang diukur dengan meteran di lokasi yang sama tetap tidak bisa digantikan.

---

## 9. Urutan eksekusi yang disarankan

Dua minggu, tanpa menunggu survei besar. Hari 0: ajukan akses I24-3D (registrasi). I24-3D berisi video 4K, jadi siapkan ruang disk yang cukup; SVLD-3D dan SKoPe3D jauh lebih ringan.

| Hari | Kegiatan | Keluaran |
|---|---|---|
| 1–2 | unduh I24-3D; parse `sceneX_hg.json`; pilih 3 kamera (dekat, menengah, jauh) | `VALIDASI-I24-3D.md` |
| 3–4 | GeoCalib versus $P$ pada semua kamera; hitung $\Delta f/f$ dan $\Delta\theta$ | tabel 50 pasangan |
| 5–7 | jalankan pipeline $L/W/H$ pada 50 kendaraan I24-3D; hitung MAPE dan bias | tabel per kelas dan per jarak |
| 8 | unduh SVLD-3D; evaluasi pada 2.237 citra test | pembanding presisi 85% (≈5% per sumbu) |
| 9–10 | pre-train keypoint SKoPe3D; fine-tune pada 100 frame CCTV | PCK@0.1 |
| 11 | naver/cctv pada Cawang dan ATP; bandingkan $H$, $f$ | catatan jebakan melingkar |
| 12 | MoGe-2 pada 4 frame; bandingkan $h$ dengan anchor | tabel selisih |
| 13–14 | tulis kesimpulan: mana yang lulus, mana yang tidak | keputusan go/no-go |

Urutan ini sengaja menaruh **I24-3D lebih dulu**. Jika GeoCalib gagal pada 50 kamera nyata, seluruh anggaran galat di laporan riset perlu direvisi, dan tidak ada gunanya melanjutkan ke keypoint atau MoGe-2.

---

## 10. Lisensi

| Sumber | Kode | Data/bobot | Boleh untuk produk komersial? |
|---|---|---|---|
| I24-3D | tidak dinyatakan | non-komersial, riset/pendidikan | tidak; minta izin |
| SVLD-3D | tidak ada lisensi eksplisit | Google Drive | belum jelas; perlakukan riset |
| SKoPe3D | — | paper CC BY-NC-SA 4.0; data cek halaman proyek | tidak |
| OpenPifPaf | AGPL-3.0 | bobot Apollo | tidak, kecuali lisensi komersial EPFL |
| GSNet | MIT | ApolloCar3D non-komersial | kode boleh; data tidak |
| naver/cctv | CC BY-NC-SA 3.0 | model pretrained | tidak |
| MoGe-2 | MIT | bobot Hugging Face | ya, cek lisensi bobot |
| RoScenes | — | non-komersial tegas | tidak |
| Rope3D | Apache-2.0 (tools) | hanya wilayah Cina | tidak dapat diakses |

Untuk sistem yang benar-benar dipakai menindak ODOL, **jangan latih model produksi dengan dataset non-komersial tanpa izin**. Dataset-dataset di atas dipakai untuk validasi dan pembuktian konsep. Model produksi harus dilatih dari data sendiri, atau dari sumber yang lisensinya mengizinkan.

---

## 11. Kandidat eksperimental (belum direkomendasikan)

Dua sumber berikut menarik, tetapi belum cukup bukti untuk dimasukkan ke jalur utama.

- **MonoGuard** (You dkk., *Expert Systems with Applications*, 2026). Framework deteksi kendaraan *oversized* dari kamera surveillance monokular. Ia melaporkan akurasi tinggi untuk estimasi tinggi mobil dan truk, tetapi evaluasinya pada 36 skenario simulasi UAV, bukan CCTV nyata, dan tidak ditemukan kode publik. Berguna sebagai pembanding klaim, bukan sebagai alat.
- **UrbanOmniDetect** (Turkcan dkk., CVPR 2026 DriveX). Satu model keypoint yang mengklaim 3D detection tanpa intrinsik, depth, atau ground-plane prior, dan mengklaim generalisasi lintas ego-vehicle, infrastruktur, dan drone. Repo tersedia di `https://github.com/mkturkcan/urbanomnidetect` dengan lisensi AGPL-3.0. Jika klaimnya bertahan pada CCTV Indonesia, ini bisa menjadi jalan pintas yang besar; sampai diuji, perlakukan sebagai hipotesis.

---

## 12. Kesimpulan

Jika hanya satu sumber yang bisa dieksekusi: **I24-3D**. Ia menutup dua kelemahan sekaligus — ground truth dimensi dan gerbang GeoCalib yang baru diuji pada satu rekaman — dan bisa dikerjakan tanpa survei lapangan.

Jika tujuan berikutnya adalah truk dan bus: **SVLD-3D**, dengan angka pembanding presisi 85% (≈5% per sumbu).

Jika tujuan berikutnya adalah membuktikan klaim adaptasi: **SKoPe3D + OpenPifPaf + GSNet**, dengan syarat fitting memakai proyeksi perspektif penuh, bukan weak perspective.

Untuk anchor: **naver/cctv** berguna untuk kalibrasi dan kecepatan, tetapi tidak untuk menetapkan ODOL, karena skalanya berasal dari prior dimensi.

Yang tidak berubah: satu kendaraan yang diukur dengan meteran di lokasi nyata tetap diperlukan sebelum ada angka yang boleh disebut tervalidasi.

---

## 13. Referensi

1. D. Gloudemans, Y. Wang, G. Gumm, W. Barbour, D. B. Work. *The Interstate-24 3D Dataset: a new benchmark for 3D multi-camera vehicle tracking.* BMVC 2023. arXiv:2308.14833. Data: `https://i24motion.org`; kode: `https://github.com/I24-MOTION/I24-3D-dataset`
2. X. Tang, H. Song, W. Wang, C. Zhao. *CenterLoc3D: Monocular 3D Vehicle Localization Network for Roadside Surveillance Cameras.* Complex & Intelligent Systems, 2023. arXiv:2203.14550. Data: `https://github.com/stjuliet/SVLD-3D-DATASET`
3. H. Pahadia, D. Lu, B. Chakravarthi, Y. Yang. *SKoPe3D: A Synthetic Dataset for Vehicle Keypoint Perception in 3D from Traffic Monitoring Cameras.* IEEE ITSC 2023. arXiv:2309.01324. Proyek: `https://skope3d.github.io/`
4. S. Kreiss, L. Bertoni, A. Alahi. *OpenPifPaf: Composite Fields for Semantic Keypoint Detection and Spatio-Temporal Association.* 2021. Kode: `https://github.com/openpifpaf/openpifpaf`; plugin mobil: `https://openpifpaf.github.io/plugins_apollocar3d.html`
5. L. Ke, S. Li, Y. Sun, Y.-W. Tai, C.-K. Tang. *GSNet: Joint Vehicle Pose and Shape Reconstruction with Geometrical and Scene-aware Supervision.* ECCV 2020. arXiv:2007.13124. Kode: `https://github.com/lkeab/gsnet`
6. J. Revaud, M. Humenberger. *Robust Automatic Monocular Vehicle Speed Estimation for Traffic Surveillance.* ICCV 2021. Kode: `https://github.com/naver/cctv`
7. R. Wang et al. *MoGe-2: Accurate Monocular Geometry with Metric Scale and Sharp Details.* NeurIPS 2025. arXiv:2507.02546. Kode: `https://github.com/microsoft/MoGe`
8. S. He et al. *RoadTagger: Robust Road Attribute Inference with Graph Neural Networks.* AAAI 2020. arXiv:1912.12408.
9. X. Zhu et al. *RoScenes: A Large-scale Multi-view 3D Dataset for Roadside Perception.* ECCV 2024. arXiv:2405.09883. Kode: `https://github.com/roscenes/RoScenes`
10. X. Ye et al. *Rope3D: The Roadside Perception Dataset for Autonomous Driving and Monocular 3D Object Detection Task.* CVPR 2022. Tools: `https://github.com/liyingying0113/rope3d-dataset-tools`
11. Y. You, J. Gu, Z. Chen, G. Wu, K. Gao. *MonoGuard: towards infrastructure-aware oversized vehicle detection via dynamic 3D metrology with monocular surveillance cameras.* Expert Systems with Applications, 2026. Paper; tidak ditemukan kode publik.
12. M. K. Turkcan, D. Gumaste, Z. Kostic. *Calibration-Free View-Agnostic Monocular 3D Object Detection for Urban Scenes.* CVPR 2026 DriveX Workshop. Kode: `https://github.com/mkturkcan/urbanomnidetect` (AGPL-3.0).
