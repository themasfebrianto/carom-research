# Protokol Validasi Eksternal

Dokumen ini mengunci definisi dan ambang sebelum data dilihat. Tujuannya mencegah "menyesuaikan metode setelah tahu hasil".

## 1. Satuan dan konvensi

- Semua panjang dalam **meter**. I24-3D memberi anotasi dalam kaki; konversi \(1\text{ ft}=0{,}3048\text{ m}\).
- Sudut dalam **derajat** untuk laporan; perhitungan internal boleh radian.
- Dunia: sumbu \(Z\) ke atas, \(X\) sepanjang jalan, \(Y\) melintang.
- Kamera: \(x\) ke kanan, \(y\) ke bawah, \(z\) ke depan.
- $L/W/H$ adalah panjang, lebar, tinggi box kendaraan; untuk I24-3D titik acuan adalah **bottom-center rear**.

## 2. Sumber data

| Sumber | Peran | Jumlah yang dipakai | Lisensi |
|---|---|---|---|
| I24-3D | ground truth kalibrasi + dimensi | 3 scene, 16–17 kamera, 3 frame/kamera; 100 kendaraan round-trip; 50 kendaraan persepsi | non-komersial, registrasi |
| SVLD-3D | ground truth bus/kendaraan besar | 200 citra test: 70 car, 130 bus | riset; lisensi tidak dinyatakan |
| SKoPe3D | pre-train keypoint sudut CCTV | subset 5.000–25.000 citra | paper CC BY-NC-SA |
| Cawang/ATP | uji domain nyata | 50 frame, 100 frame fine-tune | milik proyek |

## 3. Pemilihan frame dan kendaraan

### I24-3D

- Tiga frame per kamera: 10 s, 30 s, 50 s.
- Frame harus tajam, tidak terpotong, dan memuat jalan.
- Untuk dimensi: 50 kendaraan, stratifikasi:
  - jarak: 20–40 m, 40–70 m, 70–100 m;
  - kelas: sedan, pickup/van, semi/truck.
- Kendaraan harus terlihat utuh (tidak terpotong tepi citra) dan tidak teroklusi berat.

### SVLD-3D

- 200 citra test: 70 car, 130 bus.
- Sebar jarak dan sudut pandang; catat oklusi.
- Jangan memilih hanya kendaraan yang mudah.
- **Truck hanya 1 objek di test set.** Jangan memakai SVLD-3D untuk klaim truk. Truk diuji di I24-3D atau RoScenes; bus dipakai sebagai proxy kendaraan besar.
- **Kalibrasi:** `f` (px), `fi` = pitch (rad), `theta` = yaw (rad), `h` (mm). Jangan menukar `fi` dan `theta`.

## 4. Metrik

### Kalibrasi

$$
\frac{\Delta f}{f}=\frac{|f_{\text{GeoCalib}}-f_{\text{GT}}|}{f_{\text{GT}}},
\qquad
\Delta\theta=|\theta_{\text{GeoCalib}}-\theta_{\text{GT}}|
$$

- Laporkan median, persentil 90, dan maksimum.
- Lulus: median $\Delta f/f<5\%$, median $|\Delta\theta|<2^\circ$, ≥80% kamera lulus.

### Dimensi

$$
\mathrm{MAPE}_{LWH}=
\frac{1}{3N}\sum_{i=1}^{N}
\left(
\frac{|\hat L_i-L_i|}{L_i}+
\frac{|\hat W_i-W_i|}{W_i}+
\frac{|\hat H_i-H_i|}{H_i}
\right)\times100\%
$$

$$
\mathrm{bias}_k=\frac{1}{N}\sum_{i=1}^{N}(\hat k_i-k_i),\qquad k\in\{L,W,H\}
$$

- Laporkan MAPE dan bias per sumbu, per kelas, per bin jarak.
- Jangan hanya melaporkan MAPE gabungan; bias sistematis adalah yang paling berbahaya untuk ODOL.

### Keypoint

- PCK@0.1: keypoint dianggap benar jika jarak <10% diagonal box 2D.
- RMS reproyeksi sudut box 3D dalam piksel.
- Laporkan per kelas dan per jarak.

## 5. Ambang keputusan

| Tahap | Lulus | Gagal → tindakan |
|---|---|---|
| Kalibrasi I24-3D | median $\Delta f/f<5\%$, median $\Delta\theta<2^\circ$, ≥80% kamera | stop; revisi kalibrasi |
| Round-trip formula | <1% | perbaiki konvensi/urutan sudut |
| Dimensi I24-3D | $W/H$ <10% pada 20–30 m | batasi klaim; jangan lanjut ke ODOL |
| SVLD-3D | truk/bus <15% | dokumentasikan; turunkan klaim |
| Keypoint + shape | PCK >80%, RMS ≤3 px, $L/W/H$ <10% | hasil negatif; klaim adaptasi tidak terbukti |
| Anchor naver/cctv | pergeseran <5% untuk prior ±5% | hanya inisialisasi, bukan anchor |
| MoGe-2 | $h$ <10% dari anchor | 10–20% peringatan; >20% buang |

## 6. Aturan pelaporan

- Setiap laporan menyebut jumlah sampel, jumlah yang gagal diproses, dan alasan.
- Jangan membuang outlier tanpa menyebutkannya; laporkan dengan dan tanpa outlier.
- Jangan mengklaim akurasi lebih baik dari ketidakpastian ground truth (I24-3D ±15 cm).
- Setiap angka harus bisa dihasilkan ulang dari skrip yang disimpan.
- Dataset non-komersial hanya dipakai untuk validasi; bukan untuk melatih model produksi.
