# SOP Pengukuran Dimensi Kendaraan dari CCTV

**Prosedur operasional untuk mengukur panjang, lebar, dan tinggi kendaraan dari kamera statis terkalibrasi**

Versi 1.0 · Berlaku umum untuk kamera pemantau lalu lintas tetap

---

## 0. Prasyarat

### 0.1 Kalibrasi wajib sudah selesai

Prosedur ini **tidak** melakukan kalibrasi. Sebelum memulai, isi tabel berikut dari `SOP-KALIBRASI-CCTV.md`:

| Parameter | Nilai | Status |
|---|---|---|
| $f$ | ______ px | harus ter-anchor |
| $\theta$ | ______ ° | |
| $\psi$ | ______ ° | |
| $h$ | ______ m | harus ter-anchor |
| $c_x, c_y$ | ______ px | |
| $k_1$ | ______ | opsional |
| RMS kalibrasi | ______ px | < 2 px |

**Aturan mutlak:** jika kalibrasi berstatus **DEGENERATE** (lihat §5 SOP kalibrasi), pengukuran dalam satuan meter **dilarang**. Yang tersedia hanya besaran relatif.

### 0.2 Perkakas

Detektor objek/segmentasi, pelacak multi-objek, dan rutin optimasi nonlinear. Tidak ada ketergantungan pada merek atau pustaka tertentu.

### 0.3 Konvensi

Sama dengan SOP kalibrasi: $Z$ ke atas, $X$ sepanjang jalan, kamera pinhole dengan $y$ ke bawah.

---

## 1. Definisi measurand

**Ini harus ditetapkan sebelum satu pun angka dihitung.** Kendaraan memiliki beberapa "lebar" yang berbeda, dan selisihnya lebih besar daripada seluruh anggaran galat.

### 1.1 Lebar

| Istilah | Definisi | Nilai khas mobil |
|---|---|---|
| Track width | jarak antar pusat kontak ban | 1,50–1,60 m |
| Body width | lebar bodi tanpa spion | 1,75–1,85 m |
| Overall width | termasuk spion | 2,00–2,15 m |

Spion menjulur 20–40 cm per sisi. Pada truk, spion dan aksesori bisa menambah lebih banyak lagi.

**Wajib diputuskan dan dicatat:** apakah spion termasuk. Regulasi dimensi umumnya mengecualikan spion; verifikasi dengan instansi berwenang untuk yurisdiksi Anda, karena kesalahan di sini menghasilkan galat puluhan sentimeter.

### 1.2 Tinggi

Tinggi total dari permukaan jalan sampai titik tertinggi kendaraan **termasuk muatan** — bukan tinggi atap kabin.

Untuk truk bermuatan, titik tertinggi bisa berupa terpal, tiang, atau barang yang menjulang. Definisi harus menyebut apakah benda fleksibel (terpal berkibar) dihitung pada simpangan maksimum atau rata-rata.

### 1.3 Panjang

Panjang total termasuk julur depan dan belakang, bukan jarak sumbu roda.

Untuk kendaraan gandeng, panjang rangkaian diukur dari ujung terdepan sampai ujung terbelakang, termasuk jarak kopling.

---

## 2. Zona ukur

### 2.1 Prinsip

Galat pengukuran sangat bergantung pada geometri. Menempatkan zona di tempat yang salah dapat membuat sistem tidak berguna, sekalipun kalibrasinya sempurna.

**Aturan inti:** dimensi yang sejajar dengan sinar pandang paling buruk teramati.

| Posisi kamera | Panjang $L$ | Lebar $W$ | Tinggi $H$ |
|---|---|---|---|
| Menghadap sejajar jalan (head-on) | **buruk** | baik | baik |
| Menghadap tegak lurus jalan | baik | **buruk** | baik |
| 45° terhadap sumbu jalan | **sedang** | **sedang** | baik |

Tinggi selalu baik pada kamera miring, karena dipetakan ke sumbu vertikal citra.

### 2.2 Invarian redistribusi

Untuk satu kamera dan satu pandangan:

$$\sigma_L^2(\beta)+\sigma_W^2(\beta)=\sigma_{\text{kedalaman}}^2+\sigma_{\text{lateral}}^2=\text{konstan}$$

dengan $\beta$ sudut antara sumbu panjang kendaraan dan arah kedalaman. Mengubah posisi kamera hanya **membagikan ulang** ketidakpastian antara panjang dan lebar.

Konsekuensi desain: jika kedua dimensi sama pentingnya, sudut 45° meminimalkan galat **maksimum**:

$$\sigma_L=\sigma_W=\sigma_{\text{lateral}}\sqrt{\frac{\rho^2+1}{2}},
\qquad \rho=\frac{z}{h}$$

### 2.3 Pemilihan jarak

| Jarak | Kelayakan |
|---|---|
| < 15 m | baik, tetapi kendaraan cepat keluar frame dan oklusi tinggi |
| 15–30 m | **zona terbaik** untuk sebagian besar kamera |
| 30–45 m | hanya untuk lebar/tinggi pada kamera beresolusi tinggi |
| > 45 m | tidak layak untuk dimensi |

Kendaraan harus membentang **≥ 100 piksel** pada arah ukur. Di bawah itu galat meledak.

### 2.4 Syarat permukaan

- Datar dalam ±2 cm sepanjang zona.
- Bebas genangan, rumput, atau kanstin yang menutupi kontak ban.
- Tidak berada di tikungan tajam atau tanjakan curam.

Deviasi tinggi permukaan $\Delta z$ menjadi galat jarak:

$$\Delta X=\frac{\Delta z}{\tan\theta}$$

Pada $\theta=12°$, tonjolan 2 cm menjadi galat jarak 9,4 cm. Ini **tidak mengecil dengan bertambahnya jarak** — ia menjadi lantai galat.

---

## 3. Deteksi dan segmentasi

### 3.1 Segmentasi

Gunakan segmentasi instans (bukan hanya bounding box). Kontur diperlukan untuk:

- Menentukan titik kontak tanah.
- Memisahkan bayangan.
- Menemukan tepi atap.

### 3.2 Bayangan

Bayangan di bawah sasis dan di sisi kendaraan harus dipotong dari masker. Jika tidak, garis alas bergeser mengikuti batas bayangan dan lebar bisa melebih-lebihkan 0,3–1,5 m.

Metode: model segmentasi yang dilatih khusus dengan kelas kendaraan tanpa bayangan, atau penghapusan bayangan berbasis warna (bayangan mempertahankan hue aspal tetapi menurunkan luma).

### 3.3 Oklusi

Buang kendaraan dari pengukuran jika:

- Masker menyentuh tepi frame.
- Terhalang kendaraan lain pada bagian alas atau atap.
- Titik kontak ban tidak terlihat.

Jangan mencoba menaksir dimensi dari siluet terpotong — hasilnya bias tak terkendali.

### 3.4 Kendaraan gandeng

Truk dengan trailer harus dipisahkan menjadi dua instans. Asumsi benda kaku hanya berlaku per bagian.

Untuk panjang rangkaian, jumlahkan proyeksi tiap bagian ditambah jarak kopling; jangan memaksakan satu kotak pada kendaraan yang berbelok.

### 3.5 Malam dan inframerah

Mode IR mengubah respons spektral dan kadang menggeser fokus efektif. Kalibrasi terpisah diperlukan. Jika hanya ada kalibrasi siang, tandai hasil malam sebagai tidak tervalidasi.

---

## 4. Pelacakan

### 4.1 Syarat lintasan

| Kriteria | Ambang |
|---|---|
| Jumlah frame | ≥ 10 |
| Rentang sudut aspek $\beta$ | ≥ 20° |
| Oklusi | tidak ada pada frame yang dipakai |
| Perubahan skala | cukup untuk mengikat kedalaman |

### 4.2 Mengapa rentang aspek penting

Kendaraan adalah benda kaku dengan dimensi konstan. Ketika melintas, ia diamati dari banyak sudut. Itu informasi tambahan yang tidak dimiliki satu frame.

Jika kendaraan bergerak lurus menuju kamera, sudut aspeknya konstan sepanjang lintasan — **tidak ada informasi panjang yang bisa dipanen**. Ini degenerasi, bukan derau.

### 4.3 Tukar ID

Pelacak dapat bertukar identitas antar kendaraan serupa. Jika terjadi, kendala "dimensi konstan" akan mencampur dua kendaraan dan menghasilkan nilai yang salah. Periksa konsistensi visual antar frame sebelum menggabungkan.

---

## 5. Formula pengukuran

### 5.1 Panjang dan lebar

Untuk titik yang **berada di bidang tanah** (kontak ban, sudut tapak):

$$\lambda\tilde{\mathbf p}=H\begin{bmatrix}X\\Y\\1\end{bmatrix},
\qquad H=K\,[\,\mathbf r_1\;\mathbf r_2\;\mathbf t\,]$$

Back-projection:

$$X=\frac{(H^{-1}\tilde{\mathbf p})_1}{(H^{-1}\tilde{\mathbf p})_3},
\qquad
Y=\frac{(H^{-1}\tilde{\mathbf p})_2}{(H^{-1}\tilde{\mathbf p})_3}$$

Dengan empat sudut tapak $P_0,P_1,P_2,P_3$ terurut mengelilingi persegi panjang:

$$L=\|P_1-P_2\|,\qquad W=\|P_0-P_1\|$$

**Sifat:** $L$ dan $W$ hanya bergantung pada homografi dan titik tanah. Tidak bergantung pada tinggi kendaraan maupun model bentuk. Ini dimensi yang paling bersih secara metodologis.

### 5.2 Tinggi

Diketahui $B=(X_b,Y_b,0)$ dari back-projection titik kontak, dan $\mathbf p_t$ piksel atap yang berada tepat di atas $B$.

Sinar dari pusat kamera $\mathbf C$:

$$\mathbf d=\frac{R^\top K^{-1}\tilde{\mathbf p}_t}{\|R^\top K^{-1}\tilde{\mathbf p}_t\|}$$

Titik atap berada pada garis vertikal melalui $B$:

$$\mathbf P=\mathbf C+\lambda\mathbf d=B+\mu\,\mathbf e_z$$

Solusi:

$$\lambda=\frac{(B-\mathbf C)\cdot\mathbf d_{xy}}{\|\mathbf d_{xy}\|^2},
\qquad
H=(\mathbf C+\lambda\mathbf d)_z-B_z$$

dengan $\mathbf d_{xy}=(d_x,d_y,0)$.

**Degenerasi:** jika kamera tepat di atas $B$, $\|\mathbf d_{xy}\|\to 0$ dan tinggi tidak teramati. Ini sebabnya pandangan nadir buruk untuk tinggi, sedangkan pandangan miring baik.

### 5.3 Tinggi tanpa kalibrasi penuh (cross-ratio)

Jika hanya tersedia garis horizon $\mathbf l$ dan titik hilang vertikal $\mathbf v_z$:

$$\kappa(\mathbf b,\mathbf t)=\frac{\|\mathbf b\times\mathbf t\|}{(\mathbf l\cdot\mathbf b)\,\|\mathbf v_z\times\mathbf t\|},
\qquad
Z_x=Z_r\,\frac{\kappa(\mathbf b_x,\mathbf t_x)}{\kappa(\mathbf b_r,\mathbf t_r)}$$

dengan $(\mathbf b_r,\mathbf t_r)$ segmen vertikal referensi yang tingginya $Z_r$ diketahui.

Syarat: $\mathbf b_x,\mathbf t_x,\mathbf v_z$ segaris. Berguna bila kalibrasi penuh tidak tersedia, tetapi sensitif terhadap galat $\mathbf v_z$.

### 5.4 Fitting kotak 3D

Rumusan paling umum. Parameter:

$$\boldsymbol\theta=(X,\;Y,\;\psi,\;L,\;W,\;H)$$

Delapan sudut kotak:

$$\mathbf P_k^{\text{veh}}=\Bigl(\pm\tfrac{L}{2},\;\pm\tfrac{W}{2},\;\{0,H\}\Bigr),
\qquad
\mathbf P_k=\mathbf C_v+R_z(\psi)\,\mathbf P_k^{\text{veh}}$$

Residual:

$$E(\boldsymbol\theta)=\sum_{k\in\mathcal V}\rho\Bigl(\bigl\|\mathbf p_k^{\text{obs}}-\Pi(\mathbf P_k)\bigr\|_{\Sigma_k}\Bigr)$$

dengan $\mathcal V$ sudut terlihat dan $\rho$ robust loss.

**Peringatan:** jumlah persamaan bukan jaminan kondisi baik. Satu pandangan memberi maksimal 14 persamaan untuk 6 parameter, tetapi arah paling lemah dari Jacobian tetap sejajar sinar pandang.

### 5.5 Definisi variabel

| Simbol | Arti |
|---|---|
| $\mathbf p$ | koordinat piksel homogen |
| $H$ | homografi bidang tanah (3×3) |
| $K$ | matriks intrinsik |
| $R,\mathbf t$ | rotasi dan translasi dunia→kamera |
| $\mathbf C$ | pusat kamera di dunia |
| $\Pi(\cdot)$ | fungsi proyeksi |
| $\beta$ | sudut aspek: sumbu panjang kendaraan vs arah kedalaman |
| $\rho$ | rasio $z/h$ |

---

## 6. Fusi multi-frame

### 6.1 Rumusan

$$\min_{\{L,W,H\},\{X_k,Y_k,\psi_k\}}\;
\sum_{k=1}^{K}\sum_{j}
\alpha_{kj}\,\rho\Bigl(\bigl\|\mathbf p_{kj}^{\text{obs}}-\Pi\bigl(R_c\,[R_z(\psi_k)\mathbf P_j(L,W,H)+\mathbf c_k]+\mathbf t_c\bigr)\bigr\|_\Sigma\Bigr)$$

Perhatikan: $L,W,H$ **tidak** berindeks $k$ — itulah kendalanya.

### 6.2 Perolehan

Informasi Fisher bertambah:

$$\frac{1}{\sigma_L^2}\approx\sum_k\frac{1}{\sigma_L^2(\beta_k)}
\qquad\Longrightarrow\qquad
\sigma_L\approx\frac{\sigma_{\text{lateral}}}{\sqrt{N_{\text{eff}}}}$$

dengan $N_{\text{eff}}$ jumlah frame dengan $|\beta_k|>45°$.

### 6.3 Batas

Fusi menghilangkan **derau acak dan anisotropi geometris**. Fusi **tidak** menghilangkan bias sistematis:

- galat skala,
- ketidakrataan jalan,
- bias prior bentuk,
- bias segmentasi.

Jangan mengharapkan fusi memperbaiki kesalahan kalibrasi.

---

## 7. Ketidakpastian dan gating

### 7.1 Hukum skala galat

$$\sigma_{\text{lateral}}=\sqrt2\,\frac{z}{f}\sigma_{\text{px}},
\qquad
\sigma_{\text{kedalaman}}=\sqrt2\,\frac{z^2}{fh}\sigma_{\text{px}},
\qquad
\sigma_H\approx\sigma_{\text{lateral}}$$

Rasio anisotropi:

$$\frac{\sigma_{\text{kedalaman}}}{\sigma_{\text{lateral}}}=\frac{z}{h}$$

**Rasio ini tidak memuat $f$ dan tidak memuat resolusi.** Lensa lebih panjang memperbaiki kedua arah sekaligus, tetapi tidak pernah memperbaiki rasionya.

### 7.2 Contoh anggaran galat

Kamera $f=2000$ px, $h=10$ m, $\sigma_{\text{px}}=1{,}5$, geometri 45°, skala 1%:

| Sumber | Mekanisme | $\sigma_L$ | $\sigma_W$ | $\sigma_H$ |
|---|---|---|---|---|
| Derau piksel | $\sqrt{(\sigma_d^2+\sigma_l^2)/2}$ | 12,4 cm | 12,4 cm | 4,2 cm |
| Skala (1%) | linear | 4,5 cm | 1,8 cm | 1,5 cm |
| Ketidakrataan 2 cm | $\Delta z/\tan\theta$, terbagi 45° | 6,6 cm | 6,6 cm | 2,0 cm |
| Distorsi sisa | 1–2 px di tepi | ~5 cm | ~2 cm | ~2 cm |
| Heading 1° | pertukaran L–W | 4 cm | 1,6 cm | 0 |
| **Total (RSS)** | | **≈16 cm** | **≈14 cm** | **≈5 cm** |

Angka ini pada $z=40$ m. Pada 25 m kira-kira separuhnya untuk arah lateral, seperempatnya untuk arah kedalaman.

### 7.3 Ketidakpastian per kendaraan

Keluarkan $\Sigma$ dari Jacobian pada solusi optimal:

$$\Sigma_\theta=\sigma^2\,(J^\top\Sigma_{\text{pix}}^{-1}J)^{-1}$$

Jangan melaporkan satu angka $\sigma$ untuk seluruh sistem — galat bergantung pada posisi dan sudut aspek setiap kendaraan.

### 7.4 Gerbang kualitas

Tolak pengukuran jika salah satu terpenuhi:

| Kondisi | Tindakan |
|---|---|
| $\sigma_W$ atau $\sigma_H$ > ambang situs | tolak |
| Rentang aspek lintasan < 20° | tolak untuk panjang |
| Oklusi pada alas atau atap | tolak |
| Residual fitting > 5 px | tandai, periksa manual |
| Kendaraan di luar zona ukur | tolak |
| Kalibrasi DEGENERATE | tolak seluruh pengukuran metrik |

---

## 8. Keputusan ODOL

### 8.1 Batas regulasi (Indonesia)

PP 55/2012 Pasal 54:

| Parameter | Batas |
|---|---|
| Panjang kendaraan tunggal (bukan bus) | 12.000 mm |
| Panjang bus tunggal | 13.500 mm |
| Panjang rangkaian dengan gandengan | 18.000 mm |
| Lebar | 2.500 mm |
| Tinggi | 4.200 mm **dan** tidak lebih dari 1,7 × lebar |
| Julur belakang | maks 62,5% jarak sumbu |
| Julur depan | maks 47,5% jarak sumbu |

**Perhatikan klausul tinggi:** ambang efektif adalah $\min(4{,}2\ \text{m};\;1{,}7\,W)$. Galat pada $W$ merambat ke ambang tinggi sebesar $1{,}7\,\sigma_W$.

### 8.2 Aturan keputusan

**Untuk penegakan (minimalkan false positive):**

$$\text{flag jika}\quad \hat W-1{,}96\,\sigma_W>2{,}50\ \text{m}$$

Kendaraan hanya ditandai jika batas bawah selang kepercayaan 95% melewati ambang.

**Untuk screening (minimalkan false negative):**

$$\text{flag jika}\quad \hat W>2{,}40\ \text{m}$$

Ambang diturunkan untuk mengompensasi ketidakpastian, lalu kandidat diperiksa dengan alat ukur presisi.

### 8.3 Realitas akurasi

Dengan $\sigma_W=10$ cm, ambang 95% berada pada ±20 cm. Artinya kendaraan selebar 2,60 m masih bisa terbaca 2,50 m.

| Keperluan | $\sigma$ perlu | Layak? |
|---|---|---|
| Statistik dimensi | ±20 cm | ya |
| Klasifikasi golongan | ±15 cm | ya |
| Deteksi kandidat ODOL | ±10–15 cm | ya, dengan ambang diturunkan |
| Pra-seleksi timbangan | ±5–10 cm | marginal |
| Penegakan hukum | ±2–3 cm | **tidak** — perlu sensor redundan |

---

## 9. Template keluaran

```json
{
  "track_id": 1234,
  "timestamp": "2026-01-01T10:00:00Z",
  "measurand": "body_width_excl_mirrors",
  "L": { "value": 4.52, "sigma": 0.11, "unit": "m" },
  "W": { "value": 1.84, "sigma": 0.04, "unit": "m" },
  "H": { "value": 1.51, "sigma": 0.05, "unit": "m" },
  "frames_used": 38,
  "aspect_span_deg": 47,
  "rms_reprojection_px": 1.8,
  "quality": "valid",
  "flags": []
}
```

Tabel ringkas untuk laporan:

| ID | Waktu | L ± σ | W ± σ | H ± σ | Frame | Aspek | Status |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

---

## 10. Jebakan

| # | Jebakan | Akibat | Pencegahan |
|---|---|---|---|
| 1 | Definisi lebar tidak ditetapkan | selisih 25–35 cm | tetapkan sebelum mengukur |
| 2 | Spion ikut terukur | truk legal ter-flag | masker bagian spion |
| 3 | Bayangan tidak dipotong | lebar +0,3–1,5 m | segmentasi sadar bayangan |
| 4 | Kendaraan head-on dipaksa diukur panjangnya | galat > 50 cm | gerbang rentang aspek |
| 5 | Prior bentuk dipakai untuk penegakan | hasil menyusut ke rata-rata kelas | laporkan mode tanpa prior |
| 6 | Rata-rata lintasan untuk muatan berkibar | puncak hilang, under-estimasi | laporkan maksimum untuk tinggi |
| 7 | Fusi multi-frame diharapkan memperbaiki kalibrasi | bias sistematis tetap | validasi kalibrasi terpisah |
| 8 | Satu $\sigma$ untuk semua kendaraan | kepercayaan berlebih | $\Sigma$ per kendaraan |
| 9 | Jalan dianggap datar | galat 9 cm dari 2 cm tonjolan | ukur kerataan zona |
| 10 | Menukar track ID | dimensi tercampur | cek konsistensi visual |

---

## Lampiran A — Ringkasan derivasi

**Homografi bidang tanah.** Untuk $Z=0$:

$$\lambda\tilde{\mathbf p}=K[\mathbf r_1\;\mathbf r_2\;\mathbf t]\begin{bmatrix}X\\Y\\1\end{bmatrix}$$

**Tinggi.** Perpotongan sinar kamera dengan garis vertikal melalui titik alas.

**Anisotropi.** Dari $\partial v/\partial X=-fh/z_c^2$ dan $\partial u/\partial Y=f/z_c$, rasio galat jarak/lateral $=z_c/h$.

**Invarian L–W.** $\sigma_L^2+\sigma_W^2$ konstan terhadap sudut pandang; hanya distribusinya yang berubah.

**Degenerasi head-on.** Jika $\beta$ konstan sepanjang lintasan, kolom Jacobian untuk $L$ menjadi kombinasi linear kolom posisi — panjang tidak teramati.

## Lampiran B — Tabel akurasi

Kamera $f=2000$ px, $h=10$ m, $\sigma_{\text{px}}=1{,}5$:

| $z$ | $\sigma$ lateral | $\sigma$ kedalaman | Anisotropi |
|---|---|---|---|
| 20 m | 2,1 cm | 4,2 cm | 2,0× |
| 30 m | 3,2 cm | 9,5 cm | 3,0× |
| 40 m | 4,2 cm | 17,0 cm | 4,0× |
| 50 m | 5,3 cm | 26,5 cm | 5,0× |
| 60 m | 6,4 cm | 38,2 cm | 6,0× |

Untuk kamera lain, skalakan dengan $1/f$ dan $1/h$.

## Lampiran C — Checklist

```
[ ] Kalibrasi ter-anchor (bukan DEGENERATE)
[ ] Definisi measurand tertulis (lebar: body/overall/track; tinggi termasuk muatan)
[ ] Zona ukur 15–30 m, datar, kontak ban terlihat
[ ] Segmentasi sadar bayangan
[ ] Pelacakan ≥ 10 frame, rentang aspek ≥ 20°
[ ] Oklusi diperiksa per frame
[ ] Kendaraan gandeng dipisah
[ ] L, W dari back-projection titik tanah
[ ] H dari perpotongan sinar–garis vertikal
[ ] Fusi multi-frame dengan dimensi konstan
[ ] Sigma per kendaraan dilaporkan
[ ] Gerbang kualitas diterapkan
[ ] Aturan keputusan sesuai keperluan (screening vs penegakan)
```

---

*Prasyarat: `SOP-KALIBRASI-CCTV.md` harus selesai dan ter-anchor sebelum prosedur ini dijalankan.*
