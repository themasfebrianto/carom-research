# SOP Kalibrasi CCTV dari Rekaman Video

**Prosedur operasional untuk mendapatkan parameter kamera terkalibrasi dari rekaman CCTV statis**

Versi 1.0 · Berlaku umum untuk kamera pemantau lalu lintas tetap

---

## 0. Ruang lingkup

### 0.1 Keluaran

Prosedur ini menghasilkan satu set parameter kamera yang siap dipakai untuk pengukuran metrik:

| Keluaran | Simbol | Satuan |
|---|---|---|
| Focal length | $f$ | piksel |
| Rotasi kamera | yaw $\psi$, pitch $\theta$, roll $\phi$ | rad |
| Tinggi kamera | $h$ | m |
| Titik utama | $c_x, c_y$ | piksel |
| Koefisien distorsi radial (opsional) | $k_1$ | — |
| Matriks intrinsik + ekstrinsik | $K, R, \mathbf t$ | — |
| Ketidakpastian tiap parameter | $\sigma$ | — |

### 0.2 Batas

Prosedur ini **tidak** menghasilkan:

- Sertifikasi metrologi legal atau ketertelusuran.
- Validasi untuk kamera bergerak (PTZ, pan-tilt, kendaraan).
- Kalibrasi pada jalan yang tidak datar tanpa titik kendali tanah.
- Jaminan akurasi tanpa anchoring (§6).

### 0.3 Perkakas

| Perkakas | Fungsi | Alternatif |
|---|---|---|
| `ffmpeg` / `ffprobe` | inspeksi, ekstraksi frame, median temporal | OpenCV + NumPy |
| Node.js atau Python | deteksi marka, fitting | MATLAB, Julia |
| Laser rangefinder | anchoring tinggi kamera | meteran, RTK |
| GNSS RTK (opsional) | anchoring presisi | — |

### 0.4 Konvensi

Dunia: sumbu $Z$ ke atas, titik asal pada proyeksi vertikal kamera ke permukaan jalan, sumbu $X$ sepanjang arah jalan.

Kamera: $x$ ke kanan, $y$ ke bawah, $z$ ke depan (konvensi pinhole standar).

Semua satuan metrik, kecuali parameter piksel yang dinyatakan eksplisit.

---

## 1. Audit rekaman

**Lakukan ini sebelum menyentuh apa pun.** Sebagian besar rekaman CCTV tidak layak untuk pengukuran, dan mengetahui itu di menit pertama menghemat berhari-hari.

### 1.1 Properti teknis

```bash
ffprobe -v error -show_entries \
  stream=codec_name,width,height,r_frame_rate,avg_frame_rate,duration,bit_rate,pix_fmt \
  -show_entries format=duration,size,bit_rate -of json input.mp4
```

| Atribut | Ambang layak | Catatan |
|---|---|---|
| Resolusi | ≥ 1920×1080 **asli** | waspada upscaling 720p→1080p |
| Frame rate | ≥ 15 fps, konstan | 25 fps lebih baik untuk fusi |
| Durasi | ≥ 3 menit | butuh cukup kendaraan lewat |
| Bitrate | ≥ 2 Mbps pada 1080p | bitrate rendah menggeser tepi 1–2 px |
| `pix_fmt` | `yuv420p` / `yuvj420p` | `yuvj` = full range |

**Deteksi upscaling.** Bandingkan lebar transisi tepi marka dengan lebar yang diharapkan. Jika tepi tajam melebar > 3 px dan muncul blok 8×8, kemungkinan besar rekaman adalah hasil penskalaan. Solusi: pakai main stream, bukan substream.

**Deteksi interlacing.** Ekstrak satu frame berisi kendaraan bergerak. Jika tepi objek bergerigi (comb) pada baris ganjil/genap, rekaman interlaced. Deinterlace sebelum diproses, atau abaikan setengah baris.

### 1.2 Uji kamera statis

```bash
ffmpeg -ss 30  -i input.mp4 -frames:v 1 frames/chk_a.png
ffmpeg -ss 540 -i input.mp4 -frames:v 1 frames/chk_b.png
```

Bandingkan area statis (tiang, marka, bangunan). **Geser > 2 px selama 10 menit = kamera tidak statis.** Jika PTZ atau bergeser akibat angin, kalibrasi hanya berlaku selama pose tidak berubah; pasang pemantau pose (§4.6) atau hentikan.

### 1.3 Kelayakan geometri

| Parameter | Cara memperkirakan | Ambang |
|---|---|---|
| Tinggi kamera | dari panjang tiang, tinggi bangunan | 6–15 m |
| Sudut depresi $\theta$ | dari baris horizon terhadap pusat citra | 5–30° |
| Jarak zona ukur | dari ukuran kendaraan di citra | 15–45 m |
| Arah lintasan | sudut kendaraan terhadap sumbu optik | 30–60° ideal |
| Kontak ban–aspal | inspeksi visual | **harus terlihat** |
| Marka memanjang | inspeksi visual | ≥ 2 garis terlihat |

**Tabel keputusan.** Hentikan prosedur jika salah satu terpenuhi:

- Kamera > 15 m **dan** kendaraan > 60 m pada seluruh frame.
- Lensa sangat lebar (HFOV > 90°) pada zona > 20 m.
- Semua kendaraan bergerak head-on (tidak ada rentang aspek).
- Ban selalu terhalang kanstin, rumput, atau genangan.
- Tidak ada satu pun objek berukuran diketahui **dan** tidak mungkin survei.

---

## 2. Membangun citra kalibrasi

### 2.1 Mengapa perlu

Satu frame tunggal selalu mengandung kendaraan yang menutupi sebagian marka. Median temporal menghapus objek bergerak yang menempati sebuah piksel **kurang dari separuh waktu**, dan menyisakan latar statis — sehingga deteksi marka menjadi bersih dan tepi dash dapat diukur sub-piksel.

**Gunakan median, bukan rata-rata.** Rata-rata (`tmix`) menyisakan jejak kendaraan yang menggeser centroid marka dan mendelusi kontras. Median (`tmedian`) memilih nilai tengah, sehingga kendaraan yang menempati sebuah piksel kurang dari separuh waktu hilang sepenuhnya.

### 2.2 Memilih sebaran frame

Ambil $N \approx 40$–$60$ frame tersebar merata sepanjang rekaman. Semakin banyak, semakin bersih, tetapi biaya memori naik linear.

Bila rekaman memiliki $F$ frame total:

$$\Delta n = \left\lfloor \frac{F}{N} \right\rfloor$$

### 2.3 Perintah

```bash
# radius = floor((N-1)/2); untuk N=50 -> radius=24
ffmpeg -i input.mp4 \
  -vf "select='not(mod(n,300))',tmedian=radius=24" \
  -vsync 0 frames/tm_%03d.png
```

`tmedian` hanya mengeluarkan frame setelah buffer terisi, sehingga jumlah keluarannya jauh lebih sedikit daripada masukannya. Ambil keluaran terakhir:

```powershell
$f = Get-ChildItem frames/tm_*.png | Sort-Object Name | Select-Object -Last 1
ffmpeg -i $f.FullName frames/median.png
```

**Penting:** simpan sebagai PNG (lossless). Menyimpan sebagai JPEG menambahkan artefak kompresi yang merusak presisi tepi.

### 2.4 Verifikasi

Periksa `frames/median.png`:

- Tidak ada kendaraan, atau hanya bayangan samar yang tidak menyentuh marka.
- Marka tampak tajam dengan tepi bersih.
- Permukaan jalan seragam.

Jika masih ada ghost, perbesar $N$ atau pilih segmen rekaman dengan lalu lintas lebih sepi.

### 2.5 Alternatif bila `tmedian` tidak tersedia

| Situasi | Solusi |
|---|---|
| ffmpeg tanpa `tmedian` | simpan $N$ frame, hitung median per piksel dengan NumPy/PIL |
| Rekaman sangat sepi | satu frame bersih sudah cukup |
| Rekaman selalu padat | median dari $N$ besar, atau ambil hanya area marka dari banyak frame |

---

## 3. Ekstraksi geometri marka

### 3.1 Garis lajur dan vanishing point

**Garis solid.** Deteksi tepi (Canny/Hough) atau penyapuan profil tegak-lurus, lalu fitting garis dengan RANSAC. Toleransi inlier 1,5–2 px.

**Vanishing point arah jalan.** Dua cara, dalam urutan keandalan:

1. **Dari orientasi dash.** Hitung sumbu utama setiap dash (momen kedua). VP adalah titik yang meminimalkan jarak tegak-lurus ke seluruh sumbu tersebut. Ini paling andal karena memakai puluhan tepi sekaligus.
2. **Dari perpotongan garis lajur.** RANSAC atas pasangan garis. Lebih rapuh karena garis yang hampir sejajar menghasilkan perpotongan yang sangat sensitif.

Kualitas VP dapat dinilai dari sebaran sudut: untuk inlier, selisih sudut sumbu dash terhadap arah VP seharusnya < 2°.

**Jangan** memakai VP sebagai pengamatan terpisah dalam fitting akhir. VP adalah turunan dari model; memasukkannya sebagai data independen akan menyeret solusi ke arah derau estimasi VP.

### 3.2 Deteksi dash sub-piksel

Untuk setiap garis lajur (ditentukan oleh VP dan posisinya pada baris referensi):

1. Sapu sepanjang garis, ambil luma maksimum dalam jendela tegak-lurus ±5 px.
2. Haluskan profil dengan rata-rata 5 titik.
3. Tentukan ambang adaptif per lajur: $0{,}45$ dari rentang antara persentil-25 dan nilai maksimum.
4. Temukan run kontinu di atas ambang; gabungkan celah < 3 px.
5. Buang run yang menyentuh batas sapuan, atau panjangnya di luar 9–90 px.
6. Hitung kedua tepi dengan interpolasi linear pada lintasan ambang → **presisi sub-piksel**.
7. Hitung pusat lateral dash dari rata-rata posisi puncak per baris.

### 3.3 Penugasan grid

Setiap dash harus diberi indeks (lajur $j$, baris $k$).

- **Lajur** ditentukan oleh garis tempat dash berada.
- **Baris** diurutkan menurun berdasarkan posisi vertikal (baris 0 = terdekat).

**Asumsi fase:** dash pada lajur bersebelahan dipasang sefase (satu kali pengecatan), sehingga baris ke-$k$ berada pada jarak yang sama di semua lajur. Verifikasi: posisi vertikal dash baris $k$ di lajur berbeda harus berbeda < 5 px.

Jika fase tidak konsisten, perlakukan setiap lajur sebagai deret independen dengan fase sendiri.

### 3.4 Jebakan

| Gejala | Penyebab | Solusi |
|---|---|---|
| Dash terdeteksi ganda | beberapa maksimum lokal dalam satu dash | pakai deteksi run, bukan maksimum lokal |
| Dash sangat panjang | run menyatu dengan garis kuning/bayangan | batasi panjang maksimum, buang lajur |
| Deteksi acak pada lajur tepi | kontaminasi median/vegetasi | buang lajur tersebut |
| Tepi bergeser sistematis | ambang global pada gambar dengan gradien | ambang adaptif per lajur |

---

## 4. Fitting model kamera

### 4.1 Model

Untuk titik tanah $(X, Y, 0)$:

$$\mathbf d = (X,\;Y,\;-h)^\top,\qquad
x_c=\mathbf r_w\!\cdot\!\mathbf d,\quad
y_c=\mathbf d_w\!\cdot\!\mathbf d,\quad
z_c=\mathbf f_w\!\cdot\!\mathbf d$$

dengan basis kamera

$$\mathbf f_w=(\cos\theta\cos\psi,\;\cos\theta\sin\psi,\;-\sin\theta)$$
$$\mathbf r_w=(\sin\psi,\;-\cos\psi,\;0)$$
$$\mathbf d_w=\mathbf f_w\times\mathbf r_w$$

dan proyeksi

$$u=c_x+f\,\frac{x_c}{z_c}\bigl(1+k_1r^2\bigr),\qquad
v=c_y+f\,\frac{y_c}{z_c}\bigl(1+k_1r^2\bigr),\qquad
r^2=\Bigl(\frac{x_c}{z_c}\Bigr)^2+\Bigl(\frac{y_c}{z_c}\Bigr)^2$$

| Simbol | Arti |
|---|---|
| $f$ | focal length (piksel) |
| $\theta$ | pitch, positif menunduk |
| $\psi$ | yaw, 0 = sumbu optik sejajar jalan |
| $h$ | tinggi kamera di atas bidang jalan |
| $k_1$ | distorsi radial orde pertama (opsional) |

### 4.2 Observasi

Untuk setiap dash: tepi jauh, tepi dekat, dan pusat lateral. Tiga observasi per dash.

Koordinat dunia dash ditentukan oleh pola marka:

$$X_{\text{dekat},k}=X_p+13k,\qquad
X_{\text{jauh},k}=X_{\text{dekat},k}+5$$

dengan $X_p$ fase (parameter bebas), 13 m periode dan 5 m panjang garis.

> **Perhatikan arah.** Tepi **dekat** berada pada $X$ **lebih kecil** (baris citra lebih besar). Menukar keduanya adalah kesalahan paling umum dan membuat solver divergen.

### 4.3 Inisialisasi

| Parameter | Nilai awal | Sumber |
|---|---|---|
| $f$ | $c_x/\tan(\text{HFOV}/2)$ | datasheet lensa |
| $\theta$ | dari baris horizon: $\theta=\arctan((c_y-v_h)/f)$ | VP jalan |
| $h$ | perkiraan dari tiang/bangunan | visual |
| $X_p$ | jarak ke dash terdekat | perkiraan dari ukuran kendaraan |
| $w$ | 3,5 m | standar, sementara |
| $Y_0$ | dari $u$ lajur pertama | hitung balik |

Hitung RMS residual pada nilai awal. Jika > 20 px, inisialisasi salah — perbaiki dulu, jangan langsung optimasi.

### 4.4 Optimasi

Levenberg–Marquardt dengan Jacobian numerik. Parameter: $f,\theta,\psi,h,X_p,w$ (dan $Y_0$ bila lajur ≥ 2).

### 4.5 Kovarians

$$\Sigma=\sigma^2\,(J^\top J)^{-1},\qquad
\sigma^2=\frac{\mathbf r^\top\mathbf r}{n-p}$$

dengan $n$ jumlah observasi dan $p$ jumlah parameter.

### 4.6 Kriteria keberterimaan

| Kriteria | Ambang |
|---|---|
| RMS residual | < 2 px |
| Residual per fitur | < 3 px |
| Tren residual terhadap jarak | tidak ada |
| DoF | ≥ 8 |
| Derajat kebebasan per parameter | ≥ 1,5 |

Jika terdapat tren sistematis (residual membesar monoton terhadap jarak), model kurang: tambahkan $k_1$, atau batasi zona, atau periksa kelurusan jalan.

### 4.7 Pemantau pose

Setelah kalibrasi, pilih 6–10 fitur statis (baut pembatas, sudut marka, tiang). Reproyeksikan setiap beberapa menit. Jika RMS > 0,3 px, kamera telah bergeser — kalibrasi batal. Ini pengganti rekalibrasi per frame yang tidak diperlukan pada kamera statis.

---

## 5. Uji degenerasi — WAJIB

**Jangan lewati langkah ini.** Fitting yang konvergen dengan residual kecil tidak berarti parameternya teridentifikasi.

### 5.1 Mengapa

Untuk sudut kecil dan $X \gg h$:

$$v \approx c_y - f\theta + \frac{fh}{X},
\qquad
u \approx c_x - \frac{fY}{X}$$

Baris citra hanya memuat $f\theta$ dan $fh$; kolom memuat $fY$. Tidak ada observasi yang memisahkan $f$ dari $\theta$, $h$, dan $w$ secara individual.

Transformasi

$$(f,\theta,h,w,Y_0)\longmapsto
\Bigl(\lambda f,\;\tfrac{\theta}{\lambda},\;\tfrac{h}{\lambda},\;\tfrac{w}{\lambda},\;\tfrac{Y_0}{\lambda}\Bigr)$$

**tidak mengubah citra sama sekali**, untuk setiap $\lambda>0$.

### 5.2 Uji empiris

1. Jalankan fitting penuh, catat RMS.
2. Ulangi dengan salah satu parameter dipatok pada beberapa nilai berbeda (misalnya $Y_0$ atau $w$), biarkan sisanya bebas.
3. Plot RMS terhadap nilai yang dipatok.

| Pola RMS | Kesimpulan |
|---|---|
| Naik tajam | parameter teridentifikasi |
| **Datar (< 0,1 px sepanjang rentang lebar)** | **degenerate** |

### 5.3 Invarian yang tetap terukur

| Kombinasi | Arti |
|---|---|
| $f\theta$ | posisi horizon |
| $fh$ | skala kedalaman |
| $fw$ | skala lateral |
| $w/h$ | rasio lebar lajur terhadap tinggi kamera |

Parameter individual **tidak boleh dilaporkan** tanpa anchoring.

### 5.4 Kapan degenerasi lemah

Degenerasi menguat ketika $\theta$ kecil, karena titik hilang vertikal berada di

$$v_z=c_y+\frac{f}{\tan\theta}$$

Makin kecil $\theta$, makin jauh $v_z$ dan makin sedikit informasi perspektif vertikal.

| Pitch | $v_z$ pada $f=1000$, citra 720p | Kondisi |
|---|---|---|
| 2° | baris ≈ 28.600 | degenerasi praktis penuh |
| 10° | baris ≈ 6.000 | lemah |
| 20° | baris ≈ 3.100 | cukup |
| 30° | baris ≈ 2.100 | baik |

Kamera dengan pitch di bawah ~5° **praktis selalu** memerlukan anchoring; pada pitch sekecil itu, pemisahan $f$ dari $h$ terlalu lemah untuk diandalkan.

---

## 6. Anchoring

### 6.1 Prinsip

Karena $w/h$ dan $fh$ terukur, satu nilai nyata mengunci seluruh sistem.

**Jika tinggi kamera $h$ diketahui:**

$$f=\frac{fh}{h},\qquad
\theta=\frac{f\theta}{f},\qquad
w=\frac{fw}{f}$$

**Jika lebar lajur $w$ diketahui:**

$$h=w\,\frac{fh}{fw},\qquad
f=\frac{fh}{h},\qquad
\theta=\frac{f\theta}{f}$$

### 6.2 Pilihan anchor

| Anchor | Usaha | Ketidakpastian khas | Dampak |
|---|---|---|---|
| Laser ke lensa | 30 detik | ±1–2% | terbaik |
| Rekaman pemasangan / tinggi tiang | gratis | ±5–10% | cukup |
| RTK pada 4–6 titik tanah | 1 jam | ±0,5% | terbaik, termahal |
| Lebar lajur standar | otomatis | ±4% | minimal |
| Objek standar (kontainer, gapura) | 5 menit | ±2–5% | baik |

### 6.3 Cara mengukur tinggi kamera yang benar

> **Referensi harus permukaan jalan di zona ukur**, bukan tanah di kaki tiang.

Pada jalan layang, jembatan, atau kamera yang dipasang di bangunan seberang, kedua permukaan itu bisa berbeda puluhan sentimeter. Karena galat tinggi merambat 1:1 ke semua dimensi, kesalahan 30 cm pada $h=9$ m menjadi galat 3,3% pada setiap lebar kendaraan.

Prosedur:

1. Tandai titik di permukaan jalan pada zona ukur (bukan di bahu, bukan di bawah tiang).
2. Ukur jarak vertikal dari titik itu ke pusat lensa.
3. Jika tidak bisa vertikal, ukur jarak miring dan sudut, lalu hitung komponen vertikal.
4. Catat tanggal dan metode.

### 6.4 Verifikasi silang

Setelah anchoring, periksa hasilnya terhadap kenyataan:

| Besaran | Harus masuk akal |
|---|---|
| $w$ | 3,0–4,0 m untuk lajur normal |
| $h$ | 6–15 m, konsisten dengan visual |
| $f$ | sesuai datasheet lensa dalam ±20% |
| HFOV | sesuai spesifikasi kamera |

Jika salah satu keluar jauh dari rentang, anchor-nya salah — bukan modelnya.

---

## 7. Validasi

### 7.1 Konsistensi internal

Reproyeksikan seluruh fitur dan periksa residual per fitur. Tidak boleh ada tren terhadap jarak atau terhadap posisi lateral.

### 7.2 Objek berukuran standar

Pilih objek dengan dimensi yang diketahui dan **tegak lurus sumbu pandang**:

| Objek | Dimensi acuan |
|---|---|
| Kontainer ISO 20 ft | 2,44 × 2,59 m (atau 2,90 m high-cube) |
| Kendaraan uji tipe | dari dokumen pabrikan |
| Gapura/gerbang tol | dari gambar teknik |
| Marka putus-putus | 5 m garis + 8 m celah |

Ukur pada beberapa frame. Jika menyimpang > 5% secara sistematis, periksa anchor.

**Perhatian:** jika lebar dan tinggi objek menyimpang dengan **persentase yang hampir sama**, penyebabnya galat kedalaman, bukan rasio aspek piksel. Jika hanya satu arah yang menyimpang, baru curigai $f_x\neq f_y$.

### 7.3 Konsistensi multi-frame

Lacak 20–30 kendaraan yang melintas dari dekat ke jauh. Dimensi terukur harus **konstan** terhadap baris citra. Plot dimensi terhadap $v$; kurva yang miring sistematis menunjukkan galat pada $\theta$, $f$, atau $k_1$.

Ini validasi paling kuat yang tidak memerlukan ground truth.

---

## 8. Template pelaporan

```markdown
## Kalibrasi [lokasi] — [tanggal]

### Data
- Rekaman: [nama], [resolusi], [fps], [durasi]
- Metode median: N=[..], radius=[..]
- Kamera statis: terverifikasi / tidak

### Hasil
| Parameter | Nilai | ± | Status |
|---|---|---|---|
| f | | | terukur / ter-anchor |
| pitch | | | |
| yaw | | | |
| h | | | |
| w | | | |
| RMS | | | |

### Invarian
| f·θ | f·h | f·w | w/h |

### Anchoring
- Metode: [laser / RTK / standar]
- Nilai acuan: [..] m
- Tanggal & pelaksana: [..]

### Validasi
- Residual per fitur: [maks .. px]
- Objek standar: [..] vs [..] → [..]%
- Konsistensi multi-frame: [lolos / tidak]

### Status
[TERKALIBRASI / DEGENERATE — JANGAN DIPAKAI]
```

---

## Lampiran A — Perintah siap tempel

```bash
# 1. Inspeksi
ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration,pix_fmt \
        -of default=nw=1 input.mp4

# 2. Uji statis
ffmpeg -ss 30  -i input.mp4 -frames:v 1 chk_a.png
ffmpeg -ss 540 -i input.mp4 -frames:v 1 chk_b.png

# 3. Median temporal (N=50)
ffmpeg -i input.mp4 -vf "select='not(mod(n,300))',tmedian=radius=24" \
       -vsync 0 tm_%03d.png

# 4. Ambil keluaran terakhir
#    (PowerShell)  Get-ChildItem tm_*.png | Sort-Object Name | Select-Object -Last 1
#    (bash)        ls tm_*.png | tail -1

# 5. Konversi ke PPM untuk pemrosesan piksel
ffmpeg -i median.png -pix_fmt rgb24 median.ppm
```

## Lampiran B — Struktur folder

```
proyek/
├─ input.mp4
├─ frames/
│  ├─ chk_a.png          uji statis
│  ├─ chk_b.png
│  ├─ tm_*.png           keluaran median
│  ├─ median.png         citra kalibrasi
│  └─ median.ppm
├─ out/
│  ├─ dashes.json        deteksi dash
│  ├─ calib.json         parameter + kovarians
│  └─ overlay.png        validasi visual
└─ notes.md              catatan lapangan
```

## Lampiran C — Checklist

```
[ ] Properti rekaman diperiksa (resolusi asli, fps, durasi)
[ ] Kamera terverifikasi statis (geser < 2 px / 10 menit)
[ ] Interlacing / upscaling diperiksa
[ ] Geometri layak (depresi, jarak, kontak ban terlihat)
[ ] Median temporal dibuat dan diverifikasi bersih
[ ] Garis lajur terdeteksi dengan residual garis < 2 px
[ ] VP konsisten (sebaran sudut < 2°)
[ ] ≥ 6 dash terdeteksi dengan tepi sub-piksel
[ ] DoF ≥ 8, RMS < 2 px, tanpa tren
[ ] Uji degenerasi dijalankan
[ ] Anchor diukur (tinggi / lebar / RTK) dan dicatat
[ ] Verifikasi silang lolos (w, h, f, HFOV masuk akal)
[ ] Validasi objek standar / multi-frame
[ ] Laporan diisi dengan status eksplisit
```

## Lampiran D — Jebakan yang sudah terverifikasi

| # | Jebakan | Akibat | Pencegahan |
|---|---|---|---|
| 1 | Memakai rata-rata temporal, bukan median | centroid marka bergeser, kontras turun | `tmedian`, verifikasi visual |
| 2 | Menyimpan citra sebagai JPEG | artefak kompresi di tepi | selalu PNG/PPM |
| 3 | Menukar tepi dekat dan jauh dash | solver divergen, parameter tak bermakna | tepi dekat = $X$ lebih kecil |
| 4 | Memakai VP sebagai pengamatan independen | solusi tertarik derau VP | turunkan VP dari model |
| 5 | Melewatkan uji degenerasi | melaporkan $f$, $h$, $w$ yang illusioner | §5 wajib |
| 6 | Anchor diukur terhadap tanah kaki tiang | galat skala 2–4% | ukur terhadap jalan di zona |
| 7 | Menganggap jalan lurus tanpa verifikasi | bias pada baris terjauh | periksa residual per baris |
| 8 | Memakai lajur yang terkontaminasi marka kuning | deteksi palsu | buang lajur, atau deteksi warna terpisah |
| 9 | Pitch diasumsikan nol | horizon salah, tinggi salah | estimasi pitch dari VP |
| 10 | Kalibrasi dipakai setelah kamera bergeser | galat tak terdeteksi | pemantau pose §4.7 |

---

*Prosedur ini menghasilkan parameter kamera. Untuk menggunakannya mengukur kendaraan, lanjutkan ke `SOP-PENGUKURAN-DIMENSI-KENDARAAN.md`.*
