# Kalibrasi CCTV Interchange Cawang — Revisi 2

**Analisis ulang dengan median temporal sejati, tepi sub-piksel, dan DoF memadai — serta koreksi terhadap kesimpulan Revisi 1**

Tanggal: 17 November 2026
Menggantikan: `KALIBRASI-CCTV-CAWANG.md` (Revisi 1)

---

## 1. Ringkasan perubahan

Revisi 1 menyimpulkan kalibrasi "berhasil" dengan $f = 1158$ px, $h = 8{,}11$ m, dan lebar lajur 3,29 m, dengan residual 0,92 px. Tiga perbaikan metodologis mengubah kesimpulan itu secara mendasar.

| Aspek | Revisi 1 | Revisi 2 |
|---|---|---|
| Latar | `tmix` (rata-rata; saya salah sebut median) | `tmedian` (median sejati) |
| Titik observasi | 6 pusat dash | 18 tepi sub-piksel |
| Derajat kebebasan | ~1 | **12** |
| Residual | 0,92 px | 1,09 px |
| Parameter $f, h, w$ | dilaporkan sebagai "terukur" | **tidak teridentifikasi** — degenerasi 1-parameter |

**Temuan utama Revisi 2: kalibrasi ini tidak menentukan $f$, $h$, dan $w$ secara terpisah.** Yang ditentukan hanyalah kombinasi $f\theta$, $fh$, $fw$, dan $w/h$. Ini bukan soal presisi; ini soal identifiabilitas.

---

## 2. Metode Revisi 2

### 2.1 Median temporal sejati

```bash
ffmpeg -i "recording cawang.mp4" \
  -vf "select='not(mod(n,300))',tmedian=radius=24" -vsync 0 frames/tm2_%03d.png
```

`tmedian` memilih piksel median dari 49 frame berjarak 12 detik. Dibandingkan rata-rata (`tmix`), marka lebih tajam dan jalan lebih seragam; puncak luma marka 245–251 terhadap dasar aspal 117–125, tanpa jejak kendaraan yang menggeser centroid.

### 2.2 Tepi dash sub-piksel

Untuk setiap garis lajur, profil luma disampel tegak lurus (±6 px) sepanjang citra. Ambang adaptif per lajur: $0{,}45$ dari rentang antara persentil-25 dan nilai maksimum. Setiap run diterjemahkan menjadi dua tepi dengan interpolasi linear pada lintasan ambang, memberi presisi sub-piksel.

Hasil deteksi (lajur 0 dan 1 bersih; lajur 2 terkontaminasi garis kuning median sehingga dibuang):

| Lajur | Baris | $v$ tepi jauh | $v$ tepi dekat | panjang (px) |
|---|---|---|---|---|
| 0 | 0 | 636,12 | 698,92 | 62,8 |
| 0 | 1 | 539,28 | 568,67 | 29,4 |
| 0 | 2 | 485,91 | 503,44 | 17,5 |
| 1 | 0 | 632,84 | 696,99 | 64,2 |
| 1 | 1 | 536,70 | 567,03 | 30,3 |
| 1 | 2 | 484,26 | 501,60 | 17,3 |

Enam dash × 3 observasi (tepi jauh, tepi dekat, posisi lateral) = **18 observasi**.

### 2.3 Model

Model kamera penuh dengan yaw, pitch, dan tinggi:

$$u=c_x+f\,\frac{x_c}{z_c}\bigl(1+k_1r^2\bigr),\qquad
v=c_y+f\,\frac{y_c}{z_c}\bigl(1+k_1r^2\bigr)$$

dengan $(x_c,y_c,z_c)$ koordinat kamera dari titik tanah $(X,Y,0)$, dan $X$ ditentukan oleh pola marka: tepi dekat dash ke-$k$ berada di $X_p + 13k$, tepi jauh di $X_p + 13k + 5$.

Fitting Levenberg–Marquardt, parameter $f,\theta,\psi,h,X_p,w$ (dan $Y_0$ pada varian 7-parameter), kovarians dari $(J^\top J)^{-1}$ diskalakan dengan varians residual.

---

## 3. Hasil: degenerasi teridentifikasi

Fitting 6 parameter memberi residual **1,09 px RMS dengan 12 derajat kebebasan** — nilai yang wajar untuk tepi sub-piksel. Tetapi solusinya tidak unik.

### 3.1 Uji degenerasi

Empat set parameter yang sangat berbeda, semuanya memfit data dengan kualitas hampir sama:

| Set | $f$ (px) | pitch | $h$ (m) | $w$ (m) | RMS (px) |
|---|---|---|---|---|---|
| A | 1205 | 2,20° | 8,00 | 3,24 | 1,09 |
| B | 1312 | 2,04° | 7,37 | 2,98 | 1,08 |
| C | 1099 | 2,40° | 8,75 | 3,55 | 1,10 |
| D | 1758 | 1,54° | 5,53 | 2,23 | 1,07 |

Diproyeksikan ulang ke seluruh fitur dash, keempatnya menghasilkan posisi citra yang berbeda **maksimum 1,37 px** — di bawah derau. Artinya: **citra tidak dapat membedakan keempatnya.**

### 3.2 Mengapa

Untuk sudut kecil, pemetaan baris-citik ke jarak-tanah adalah

$$v \approx c_y - f\theta + \frac{f h}{X}$$

yang hanya memuat dua kombinasi: $f\theta$ dan $fh$. Skala lateral

$$u \approx c_x - \frac{f w}{z}$$

menambah kombinasi ketiga, $fw$. Tidak ada observasi yang memisahkan $f$ dari $\theta$, $h$, atau $w$ secara individual.

Transformasi

$$(f,\;\theta,\;h,\;w,\;Y_0)\;\longmapsto\;\Bigl(\lambda f,\;\tfrac{\theta}{\lambda},\;\tfrac{h}{\lambda},\;\tfrac{w}{\lambda},\;\tfrac{Y_0}{\lambda}\Bigr)$$

**meninggalkan citra tidak berubah sama sekali** untuk setiap $\lambda>0$.

### 3.3 Besaran yang benar-benar terukur

| Kombinasi | Nilai | Ketidakpastian |
|---|---|---|
| $f\theta$ | 2651 px·deg | ±2% |
| $fh$ | 9641 px·m | ±1% |
| $fw$ | 3902 px·m | ±1% |
| $w/h$ | **0,4044** | ±0,5% |
| $X_p$ | 24,8 m | ±0,6 m |
| Baris horizon | 313,5 px | ±1 px |
| Yaw $\psi$ | 0,25° | ±0,2° |

**Rasio $w/h = 0,404$ adalah hasil paling kokoh**: lebar lajur adalah 40,4% dari tinggi kamera, terlepas dari focal length.

---

## 4. Koreksi terhadap Revisi 1

### 4.1 "Lebar lajur 3,29 m" tidak sahih

Angka itu adalah salah satu titik dalam keluarga degenerasi, dipilih oleh nilai awal solver dan parameter yang dipatok (yaw = 0). Dengan $f = 1758$ (set D), lebarnya 2,23 m; dengan $f = 1099$ (set C), 3,55 m. Ketiganya cocok dengan citra.

### 4.2 "Validasi panjang dash 5,02–5,09 m" tidak sekuat klaim semula

Pada Revisi 1, panjang dash adalah pemeriksaan independen yang sah — tetapi ia hanya memvalidasi kombinasi $f\theta$ dan $fh$, bukan $f$ atau $h$ sendiri. Kesimpulan "skala longitudinal akurat 2%" tetap benar; kesimpulan implisit bahwa $h$ dan $f$ terukur tidak.

### 4.3 Hipotesis piksel anamorfik: dicabut

Kontainer menyimpang +4,1% (lebar) dan +4,8% (tinggi) — hampir sama. Galat yang sama pada arah horizontal dan vertikal berasal dari **kedalaman**, bukan rasio aspek. Hipotesis $f_x\neq f_y$ di Revisi 1 tidak didukung dan dicabut.

### 4.4 Distorsi radial: tidak signifikan

Garis lajur terfit lurus dalam ~1,8 px sepanjang 270 baris. Distorsi yang cukup kuat untuk menjelaskan penyimpangan lateral akan membusurkan garis ~8–10 px. Tidak ada.

---

## 5. Kalibrasi titik tetap: satu angka menyelesaikan semuanya

Karena $w/h$ dan $fh$ diketahui, menentukan **salah satu** dari $h$ atau $w$ mengunci seluruh sistem.

### 5.1 Jika lebar lajur diketahui (mis. 3,60 m per Bina Marga)

Memaku $w=3{,}60$ m dan membebaskan sisanya memberi solusi:

| Parameter | Nilai |
|---|---|
| $f$ | **1082,6 px** (HFOV 61,2°) |
| pitch | **2,432°** |
| yaw | 0,271° |
| $h$ | **8,876 m** |
| $w$ | 3,60 m (input) |
| $X_p$ | 24,63 m |
| Baris horizon | 314,0 |
| **RMS** | **1,097 px (12 DoF)** |

**Penting:** RMS 1,097 px identik dengan fitting bebas (1,09 px). Artinya memaku $w$ **tidak sedikit pun memperburuk** kesesuaian — konfirmasi bahwa solusi ber-anchor ini memang anggota keluarga degenerasi, bukan kompromi. Residual per dash tersebar dalam ±1,8 px tanpa tren sistematis.

Nilai invarian bergeser tipis dari §3.3 ($fh$: 9641 → 9608; $fw$: 3902 → 3897; $w/h$: 0,4044 → 0,4056) — pergeseran 0,1–0,3%, konsisten dengan klaim bahwa degenerasi nyaris eksak.

### 5.2 Jika tinggi kamera diukur langsung (lebih baik)

Ukur dengan laser dari permukaan jalan ke lensa. Hubungannya:

| $h$ terukur | $f$ (px) | $w$ (m) | Status lebar lajur |
|---|---|---|---|
| 7,0 m | 1373 | 2,84 | tidak realistis |
| 8,0 m | 1201 | 3,24 | di bawah spesifikasi |
| **8,88 m** | **1082** | **3,60** | **sesuai Bina Marga** |
| 9,5 m | 1011 | 3,85 | di atas spesifikasi |
| 12,0 m | 801 | 4,87 | tidak realistis |

Perhatikan bahwa spesifikasi lebar lajur (3,50–3,75 m) **membatasi tinggi kamera** ke 8,65–9,27 m. Ini konsisten dengan tampilan visual: kamera berada di atas kendaraan terbesar, pada struktur bangunan sisi jalan.

---

## 6. Implikasi untuk pengukuran dimensi

Dengan kalibrasi teranchored ($f=1082$, $h=8{,}88$), dan $\sigma_{\text{px}}=1{,}5$ pada 720p:

$$\sigma_{\text{lateral}}=\sqrt2\,\frac{z}{f}\sigma_{\text{px}},
\qquad
\sigma_{\text{kedalaman}}=\sqrt2\,\frac{z^2}{fh}\sigma_{\text{px}}$$

| Jarak | Lebar / tinggi | Panjang | Anisotropi $z/h$ |
|---|---|---|---|
| 20 m | 3,9 cm | 8,8 cm | 2,2× |
| 30 m | 5,9 cm | 19,8 cm | 3,4× |
| 40 m | 7,8 cm | 35,2 cm | 4,5× |
| 50 m | 9,8 cm | 55,0 cm | 5,6× |

Ditambah **galat skala**: jika $w$ diketahui dari spesifikasi (±4%), semua dimensi mewarisi ±4%. Untuk lebar mobil 1,8 m itu ±7 cm. Jika $w$ atau $h$ diukur langsung (±0,5%), galat skala menjadi ±1 cm.

**Total pada 30 m, dengan anchor spesifikasi:** $\sqrt{5{,}9^2+7^2}\approx9$ cm.
**Total pada 30 m, dengan anchor lapangan:** $\sqrt{5{,}9^2+1^2}\approx6$ cm.

---

## 7. Kesimpulan

1. **Kalibrasi geometrik berhasil**, tetapi **identifikasi parameter tidak**. Residual 1,09 px dengan 12 DoF menunjukkan model cocok; degenerasi 1-parameter menunjukkan solusinya tidak unik.

2. **Satu pengukuran lapangan — tinggi kamera atau lebar lajur — menyelesaikan seluruh sistem.** Bukan penyempurnaan 5–10%, melainkan pemutus degenerasi faktor ~1,6.

3. **Untuk kamera ini, lebar dan tinggi kendaraan layak diukur pada 18–30 m** dengan total ±6–9 cm setelah anchoring. Panjang tidak layak karena sumbu optik hampir sejajar jalan.

4. **Kamera dengan pitch besar lebih mudah dikalibrasi.** Degenerasi $f$–$h$ melemah ketika $\theta$ besar, karena $v_z$ menjadi teramati. Kamera ini memiliki pitch hanya 2,45° — kasus terburuk.

5. **Rekomendasi operasional:** ukur tinggi kamera dengan laser (30 detik), atau lebar lajur dengan meteran. Simpan sebagai konstanta situs. Jangan pernah mengestimasi $f$ dan $h$ sekaligus dari marka saja.

---

## 8. Batasan

1. Hanya lajur 0 dan 1 yang dipakai; lajur 2 terkontaminasi garis kuning median.
2. Baris 3 berada pada $z\approx53$ m. Model jalan lurus **memfit baris ini dengan residual di bawah 1,6 px tanpa tren**, sehingga lengkung belum terdeteksi pada rentang ukur. Lengkung yang terlihat di citra berada pada $z\approx110$–145 m (baris 400–380), jauh di luar zona.
3. Roll diasumsikan nol dan tidak diverifikasi.
4. Bidang tanah diasumsikan datar; superelevasi interchange tidak dimodelkan.
5. Analisis mengasumsikan periode marka 13 m (PM 34/2014, VR ≥ 60 km/jam).
6. Kontainer ISO dipakai sebagai pemeriksaan orde-besar, bukan standar acuan.

---

## Lampiran — artefak

| Berkas | Isi |
|---|---|
| `frames/median2.png` | median temporal sejati (49 frame) |
| `frames/dashes2.json` | 9 dash terdeteksi, tepi sub-piksel |
| `dash3.mjs` | ekstraksi run + tepi sub-piksel |
| `calib3.mjs` | fitting 18 observasi + kovarians |
| `degeneracy.mjs` | uji degenerasi 1-parameter |
| `calib2.mjs` | percobaan awal (tersimpan sebagai catatan) |

### Reproduksi

```bash
ffmpeg -i "recording cawang.mp4" -vf "select='not(mod(n,300))',tmedian=radius=24" \
  -vsync 0 frames/tm2_%03d.png
ffmpeg -i frames/tm2_002.png -pix_fmt rgb24 frames/median2.ppm
node dash3.mjs frames/median2.ppm
node calib3.mjs
node degeneracy.mjs
```

---

*Revisi 2 ini menggantikan Revisi 1. Angka $f$, $h$, dan $w$ pada Revisi 1 tidak boleh dipakai tanpa anchoring; yang berlaku adalah kombinasi pada §3.3.*
