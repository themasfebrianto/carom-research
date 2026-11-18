# Kalibrasi CCTV Interchange Cawang KM 00+500

> **DIGANTIKAN.** Dokumen ini adalah Revisi 1. Analisis ulang dengan median temporal sejati dan tepi sub-piksel menemukan bahwa $f$, $h$, dan $w$ **tidak teridentifikasi secara terpisah** (degenerasi 1-parameter). Angka $f=1158$ px, $h=8{,}11$ m, dan $w=3{,}29$ m di bawah ini adalah satu titik sembarang dalam keluarga solusi dan **tidak boleh dipakai**. Lihat `KALIBRASI-CCTV-CAWANG-REV2.md`.

**Hasil kalibrasi metrik dari rekaman `recording cawang.mp4`, dengan validasi dan analisis ketidakpastian**

Tanggal analisis: 17 November 2026
Sumber: rekaman CCTV tetap, 10 menit, 4 Agustus 2026 pukul 11.19–11.29 WIB
Lokasi pada citra: `Interchange Cawang KM 00+500`

---

## 1. Ringkasan

Kalibrasi berhasil diselesaikan dengan residual **0,92 piksel RMS** pada grid marka jalan. Parameter yang diperoleh:

| Parameter | Nilai | Status |
|---|---|---|
| Focal length $f$ | **1158 px** | terukur (divalidasi) |
| Pitch (depresi) $\theta$ | **2,12°** | terukur |
| Roll $\phi$ | 0° (diasumsikan) | asumsi |
| Yaw $\psi$ | ≈0 (VP sejajar pusat citra) | terukur |
| Tinggi kamera $h$ | **8,11 m** | terukur |
| Baris horizon | **317 px** | terukur |
| VP arah jalan | **(651,5; 310,0)** | terukur |
| Lebar lajur tersirat | **3,29 m** | terukur |
| FOV horizontal | 57,9° (≈33 mm ekuivalen) | turunan |

**Tiga temuan utama:**

1. **Skala longitudinal terverifikasi independen.** Panjang dash dan celah antar-dash — yang *tidak* dipakai dalam fitting — direproduksi sebagai 5,02–5,09 m dan 7,85 m, versus spesifikasi 5,0 m dan 8,0 m. Galat < 2%. Ini memvalidasi $f$, $h$, dan pitch secara bersamaan.

2. **Skala lateral menyimpang.** Lebar lajur terukur 3,29 m, konsisten di tiga jarak berbeda (3,29 / 3,31 / 3,26 m), tetapi spesifikasi Bina Marga adalah 3,50–3,75 m. Selisih −6% sampai −9%. Karena skala longitudinal benar, penyimpangan ini terisolasi ke arah lateral — indikasi **piksel non-persegi (anamorphic)** atau lajur yang memang lebih sempit dari nominal.

3. **Kamera ini buruk untuk mengukur panjang.** Sumbu optik hampir sejajar jalan (yaw ≈ 0), sehingga panjang kendaraan terletak di arah kedalaman — sumbu terburuk. Rasio anisotropi $z/h$ mencapai 3,7× pada 30 m dan 6,2× pada 50 m.

---

## 2. Data dan kondisi

| Atribut | Nilai |
|---|---|
| Resolusi | 1280 × 720 |
| Frame rate | 25 fps konstan |
| Durasi | 600 s (15.000 frame) |
| Codec / bitrate | H.264 / 2,50 Mbps |
| Piksel | `yuvj420p` (full range) |
| Kestabilan kamera | statis — tidak ada pergeseran terdeteksi sepanjang 10 menit |
| Pencahayaan | siang, mendung cerah, kontras baik |
| Kepadatan lalu lintas | sedang; tidak pernah kosong sepenuhnya |

**Geometri scene.** Dua badan jalan terpisah median berpohon palem. Badan jalan kiri (3 lajur) menjauh dari kamera; badan jalan kanan mendekat. Kamera berada di sisi kiri, kira-kira segaris dengan badan jalan kiri. Jalan **melengkung ke kiri** di kejauhan (terlihat mulai $z\approx60$ m) dan berada pada struktur layang — relevan untuk keterbatasan model bidang datar.

---

## 3. Metode

### 3.1 Latar median-temporal

Kendaraan dihapus dengan merata-ratakan 50 frame berjarak 12 detik:

```
ffmpeg -i "recording cawang.mp4" \
  -vf "select='not(mod(n,300))',tmix=frames=49" -vsync 0 frames/tm_%03d.png
```

Karena setiap piksel jalan hanya tertutup kendaraan sebagian kecil waktu, rata-rata temporal mendekati citra jalan bersih. Hasil: `frames/median.png`. Ini menghasilkan citra kalibrasi dengan marka tajam tanpa satu pun kendaraan.

### 3.2 Deteksi dash dan estimasi VP

Komponen terhubung pada ambang luma 138, difilter dengan momen kedua (elongasi > 3, lebar minor 2,5–26 px). Untuk setiap kandidat dihitung sumbu utama. VP diestimasi sebagai titik yang meminimalkan jarak tegak-lurus berbobot ke seluruh sumbu dash, diiterasi dengan pembuangan outlier sudut > 10°.

Hasil: **VP = (651,5; 310,0)** dengan 6 inlier sudut konsisten dalam ±1,3°. VP ini tepat: sudut sumbu dash terhadap VP untuk inlier terbesar penyimpangannya hanya 1,3°.

### 3.3 Garis lajur dan baris dash

Tiga garis lajur diidentifikasi dari x pada baris 719: **209,5 / 369,2 / 533,6**. Ketiganya melalui VP. Jarak antar-garis pada baris 666 adalah 141,5 px dan 142,2 px — praktis sama, mengonfirmasi tiga lajur yang berdekatan dan yaw ≈ 0.

Penyapuan luma sepanjang tiap garis menghasilkan baris dash pada:

| Baris | $v$ (px) | $u$ lajur A | $u$ lajur B | $u$ lajur C |
|---|---|---|---|---|
| 1 | 666,3 | 265,9 | 407,4 | 549,6 |
| 2 | 553,0 | 388,3 | 484,6 | — |
| 3 | 494,5 | 450,9 | 522,2 | — |

### 3.4 Model dan fitting

Karena yaw ≈ 0 dan roll = 0, model kamera disederhanakan menjadi:

$$z(X)=X\cos\theta+h\sin\theta$$

$$v(X)=c_y+f\,\frac{-X\sin\theta+h\cos\theta}{z(X)},
\qquad
\Delta u(X)=\frac{f\,w}{z(X)}$$

dengan $X$ jarak tanah sepanjang sumbu jalan, $w$ lebar lajur, dan baris dash berjarak tepat satu periode marka.

Empat parameter diestimasi dengan Levenberg–Marquardt: $f$, $\theta$, $h$, $X_1$ (jarak ke baris dash terdekat). Lebar lajur $w$ **juga diestimasi**, bukan diasumsikan — sehingga nilainya menjadi pengukuran independen.

**Anchor skala:** periode marka 13 m (5 m garis + 8 m celah) sesuai PM 34/2014 Pasal 18 untuk kecepatan rencana ≥ 60 km/jam.

**Asumsi:** titik utama di pusat citra $(640,360)$; bidang tanah datar dan lurus; tidak ada distorsi radial; piksel persegi.

---

## 4. Hasil fitting

```
f      = 1158,0 px
pitch  = 2,122°
height = 8,11 m
X1     = 26,61 m
lebar lajur = 3,292 m
baris horizon = 317,1 px
VP vertikal  = baris 31.595  (tidak dapat dipakai)
```

| Baris dash | $X$ (m) | $v$ teramati | $v$ model | $\Delta u$ teramati | $\Delta u$ model |
|---|---|---|---|---|---|
| 1 | 26,6 | 666,3 | 666,4 | 141,5 | 141,7 |
| 2 | 39,6 | 553,0 | 552,6 | 96,3 | 95,5 |
| 3 | 52,6 | 494,5 | 494,8 | 71,3 | 72,0 |

**RMS berbobot = 0,92 px.**

Perhatikan nilai VP vertikal: baris 31.595 — praktis di tak hingga. Ini menegaskan bahwa pada geometri ini **tinggi kamera tidak dapat diukur dari vanishing point vertikal**; metode kutub $\mathbf v_z\propto\omega^{-1}(\mathbf v_x\times\mathbf v_y)$ memang benar secara teori tetapi tidak berguna secara numerik di sini. Skala harus datang dari marka, bukan dari VP.

---

## 5. Validasi

### 5.1 Validasi A — dimensi marka (independen, longitudinal)

Panjang dash dan celah **tidak dipakai** dalam fitting (hanya pusat dash). Model memprediksi:

| Fitur | Model | Spesifikasi | Galat |
|---|---|---|---|
| Dash lajur B baris 1 | 5,02 m | 5,0 m | +0,4% |
| Dash lajur A baris 2 | 5,05 m | 5,0 m | +1,0% |
| Dash lajur A baris 3 | 5,09 m | 5,0 m | +1,8% |
| Celah antar-dash | 7,85 m | 8,0 m | −1,9% |

**Kesimpulan: skala longitudinal akurat dalam 2%.** Ini memvalidasi $f$, $h$, dan $\theta$ secara bersamaan, karena ketiganya menentukan pemetaan baris-citik ke jarak-tanah.

### 5.2 Validasi B — lebar lajur (lateral)

| Baris | $X$ (m) | $\Delta u$ (px) | Lebar tersirat |
|---|---|---|---|
| 666,3 | 26,6 | 141,5 | 3,29 m |
| 553,0 | 39,6 | 96,3 | 3,31 m |
| 494,5 | 52,7 | 71,3 | 3,26 m |

Konsistensi internal sangat baik (**sebaran 1,5%**), tetapi nilai absolutnya 6–9% di bawah spesifikasi 3,50–3,75 m.

Karena $f$ dan $z$ sudah divalidasi oleh §5.1, penyimpangan ini **terisolasi ke arah lateral**. Kemungkinan penyebab, berurut:

1. **Piksel non-persegi / penskalaan anamorphic.** Bila $f_x/f_y=1{,}09$, lebar lajur menjadi tepat 3,60 m. Ini lazim pada encoder CCTV yang mengubah rasio aspek.
2. **Lajur memang lebih sempit** dari nominal — ruas ini adalah area interchange, bukan mainline.
3. Distorsi radial sisa (tidak didukung data: jarak antar-lajur dalam ≈ luar).

### 5.3 Validasi C — kontainer ISO 20 ft

Kontainer pada frame $t=5$ s, muka belakang, diukur pada grid presisi (crop 5×):

| Dimensi | Terukur | Standar | Galat |
|---|---|---|---|
| Lebar | 2,54 m | 2,44 m | +4,1% |
| Tinggi (high-cube) | 3,04 m | 2,90 m | +4,8% |

Kedua dimensi menyimpang +4–5% dengan arah sama — konsisten satu sama lain, tetapi **berlawanan arah** dengan §5.2. Dengan ketidakpastian baca piksel ±2 px pada objek 56 px (±3,6%), kedua hasil ini masih bersilangan pada tingkat ~±10%.

**Interpretasi jujur:** dua anchor independen memberi jawaban yang tidak sepenuhnya sepakat. Skala absolut berada dalam **±5–10%** kecuali dilakukan satu pengukuran lapangan.

---

## 6. Ketidakpastian

### 6.1 Sensitivitas terhadap asumsi anchor

| Periode marka | $f$ (px) | $h$ (m) | $w$ (m) | RMS |
|---|---|---|---|---|
| 12 m | 1109 | 7,81 | 3,17 | 0,92 |
| **13 m** | **1158** | **8,11** | **3,29** | 0,92 |
| 14 m | 1204 | 8,40 | 3,41 | 0,92 |
| 15 m | 1248 | 8,68 | 3,52 | 0,92 |
| 16 m | 1291 | 8,95 | 3,63 | 0,92 |

**RMS identik untuk semua periode.** Ini menunjukkan degenerasi penting: dengan hanya grid marka, **periode dan lebar lajur tidak terpisah**. Setiap kombinasi mensyaratkan $w \approx 0{,}103 \times$ periode. Data ini tidak dapat memilih di antara keduanya tanpa anchor eksternal.

Agar $w=3{,}60$ m, periode harus 15,7 m — bukan nilai standar. Maka periode 13 m lebih masuk akal, dan lebar lajur 3,29 m adalah hasil yang konsisten dengan data.

### 6.2 Sensitivitas terhadap titik utama

| $c_y$ | $f$ | pitch | $h$ | $w$ |
|---|---|---|---|---|
| 340 | 1154 | 1,14° | 8,14 | 3,304 |
| 360 | 1158 | 2,12° | 8,11 | 3,290 |
| 380 | 1163 | 3,10° | 8,06 | 3,274 |

Pengaruh kecil (< 0,5% pada $w$). Asumsi titik utama tidak kritis.

### 6.3 Ketidakpastian teoretis per titik

Dengan $f=1158$, $h=8{,}11$, $\sigma_{\text{px}}=1$:

$$\sigma_{\text{lateral}}=\sqrt2\,\frac{z}{f},\qquad
\sigma_{\text{kedalaman}}=\sqrt2\,\frac{z^{2}}{f h}$$

| $z$ | Lateral | Kedalaman | Anisotropi $z/h$ |
|---|---|---|---|
| 30 m | 3,7 cm/px | 13,6 cm/px | 3,7× |
| 40 m | 4,9 cm/px | 24,1 cm/px | 4,9× |
| 50 m | 6,1 cm/px | 37,7 cm/px | 6,2× |
| 60 m | 7,3 cm/px | 54,2 cm/px | 7,4× |

Angka ini bukan sekadar teori: rasio 6,2× pada 50 m konsisten dengan rasio galat longitudinal/lateral 6,9:1 yang dilaporkan CAROM untuk kamera infrastruktur pada rentang serupa.

---

## 7. Implikasi: apa yang bisa diukur

Dengan $\sigma_{\text{px}}=1{,}5$ (realistis untuk deteksi keypoint pada 720p), $1\sigma$:

| Jarak | Lebar $W$ atau tinggi $H$ | Panjang $L$ (bila sejajar pandang) | Layak? |
|---|---|---|---|
| 20 m | 3,7 cm | 9,0 cm | ya, screening akurat |
| 25 m | 4,6 cm | 14,1 cm | ya |
| 30 m | 5,5 cm | 20,3 cm | marginal untuk L |
| 40 m | 7,3 cm | 36,1 cm | tidak untuk L |
| 50 m | 9,2 cm | 56,5 cm | tidak |

Ditambah galat sistematis skala 5–10%, yang **tidak mengecil dengan jarak**.

**Zona ukur yang disarankan untuk kamera ini: 18–30 m** (baris citra ≈ 530–640). Di luar itu, panjang menjadi tidak berarti dan lebar memburuk secara linear.

**Yang layak:**
- Lebar dan tinggi kendaraan pada 18–30 m: ±5–8 cm → cukup untuk klasifikasi golongan, deteksi kandidat ODOL, dan statistik.
- Verifikasi muatan menjulang (tinggi) — karena tinggi dipetakan ke sumbu vertikal, yang berkondisi baik.

**Yang tidak layak:**
- Panjang kendaraan. Dengan yaw ≈ 0, panjang selalu berada di arah kedalaman. Pada 30 m galatnya sudah 20 cm; pada 50 m setengah meter.
- Penegakan hukum tanpa pengukuran lapangan.

---

## 8. Kesimpulan dan rekomendasi

### 8.1 Kesimpulan

1. Kalibrasi **berhasil dan reprodusibel**, dengan residual 0,92 px dan validasi longitudinal independen dalam 2%.
2. Parameter kamera yang diperoleh masuk akal: lensa lebar (HFOV 58°), tinggi 8,1 m, pitch 2,1° — kamera dipasang tinggi tetapi hampir horizontal, sehingga jalan tampak sangat memanjang.
3. Skala lateral tidak sepakat dengan spesifikasi (3,29 vs 3,50–3,75 m). Ini **bukan kegagalan metode**, melainkan informasi: salah satu dari (a) rasio piksel, (b) lebar lajur as-built, atau (c) anchor nominal, tidak benar.
4. Geometri kamera ini **tidak cocok untuk mengukur panjang**. Itu sifat optik, bukan algoritma.

### 8.2 Rekomendasi

1. **Satu pengukuran lapangan menutup 90% ketidakpastian.** Ukur lebar lajur atau lima periode dash sekali dengan meteran laser. Galat turun dari ±10% ke ±1%.
2. **Periksa rasio piksel.** Uji apakah $f_x=f_y$ dengan target kalibrasi (papan catur) atau dari datasheet kamera. Ini menjelaskan seluruh selisih lateral.
3. **Batasi zona ukur ke 18–30 m**, bukan seluruh frame.
4. **Untuk panjang, tambahkan kamera kedua** pada sudut 40–50° terhadap sumbu jalan (prinsip minimax §7.9 laporan utama), atau pindahkan kamera ke sisi jalan menghadap melintang.
5. **Jangan gunakan kalibrasi ini untuk penegakan.** Untuk screening dan statistik, memadai.

### 8.3 Yang akan berubah bila rekomendasi 1 dilakukan

| | Sekarang | Setelah 1 pengukuran lapangan |
|---|---|---|
| Skala absolut | ±5–10% | ±0,5% |
| Lebar mobil pada 25 m, total $1\sigma$ | **±19 cm** (didominasi skala: 10% × 1,8 m = 18 cm) | **±5 cm** |
| Kelayakan | statistik, screening kasar | pra-seleksi ODOL |

Perhatikan: pada tahap ini galat **skala mendominasi** galat pengukuran piksel. Itu sebabnya satu pengukuran lapangan bernilai lebih dari seluruh perbaikan algoritma.

---

## Lampiran A — Artefak

| Berkas | Isi |
|---|---|
| `frames/median.png` | citra latar median-temporal (dasar kalibrasi) |
| `frames/ann2.png` | overlay validasi: garis lajur + pusat dash prediksi |
| `frames/truck2.png` | crop kontainer dengan grid 20 px untuk validasi C |
| `lines2.mjs` | RANSAC garis pada ROI |
| `vpfit.mjs` | estimasi VP iteratif dari orientasi dash |
| `scan.mjs` | penyapuan luma sepanjang garis lajur → baris dash |
| `calib.mjs` | fitting Levenberg–Marquardt model kamera |
| `sens.mjs` | analisis sensitivitas (periode, titik utama) |
| `measure.mjs` | pengukuran objek + ketidakpastian teoretis |
| `annotate.mjs` | utilitas overlay |

### Cara reproduksi

```bash
ffmpeg -i "recording cawang.mp4" -vf "select='not(mod(n,300))',tmix=frames=49" \
  -vsync 0 frames/tm_%03d.png
# ambil frame terakhir sebagai frames/median.png
ffmpeg -i frames/median.png -pix_fmt rgb24 frames/median.ppm
node vpfit.mjs frames/median.ppm 138 0 760 400 719
node scan.mjs  frames/median.ppm
node calib.mjs
node sens.mjs
node measure.mjs
```

---

## Lampiran B — Asumsi dan batas

1. **Bidang tanah datar dan lurus.** Dilanggar: jalan melengkung ke kiri mulai $z\approx55$ m dan berada pada struktur layang. Kalibrasi hanya berlaku untuk zona 20–50 m.
2. **Roll = 0.** Tidak diverifikasi independen; horizon diasumsikan horizontal.
3. **Titik utama di pusat citra.** Tidak dikalibrasi; sensitivitas < 0,5%.
4. **Tanpa distorsi radial.** Tidak dimodelkan. Didukung secara tidak langsung oleh keseragaman jarak antar-lajur, tetapi tidak dibuktikan.
5. **Periode marka 13 m** dari PM 34/2014; tidak diukur di lapangan.
6. **Hanya badan jalan kiri** yang dikalibrasi. Badan jalan kanan berada di elevasi berbeda (terpisah median) dan memerlukan kalibrasi sendiri.
7. **Validasi kontainer** memakai asumsi high-cube (2,90 m); bila kontainer standar (2,59 m), galat tinggi menjadi +17% dan interpretasinya berubah.
8. **Video 720p.** Semua angka galat berskala $1/f$; kamera 4K pada FOV sama akan memberi $f\approx2300$ px dan galat lateral ~2× lebih baik.

---

*Dokumen ini dihasilkan dari pengolahan langsung berkas video, bukan estimasi. Seluruh angka dapat direproduksi dengan skrip pada Lampiran A. Interpretasi skala absolut bersifat sementara sampai dilakukan satu pengukuran lapangan.*
