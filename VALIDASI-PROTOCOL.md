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
| I24-3D | ground-plane + dimensi 3D; **bukan GT f/pose** | 3 scene, 16–18 kamera; 876.948 box, 720 objek | non-komersial, registrasi |
| SVLD-3D | kalibrasi + geometri bus/truk; **`veh_size` preset** | test 2.237 citra; trainval 14.592 citra (700 Truck, 1.166 Bus) | riset; lisensi tidak dinyatakan |
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

- Test: 200 citra (70 car, 130 bus). Trainval: 14.592 citra, 700 Truck + 1.166 Bus; gunakan untuk stress-test kelas besar/panjang, bukan accuracy claim.
- Sebar jarak dan sudut pandang; catat oklusi.
- Jangan memilih hanya kendaraan yang mudah.
- **Truck test hanya 1 objek**, tetapi trainval punya 700 Truck. **`veh_size` adalah preset**, bukan pengukuran per kendaraan; jangan klaim akurasi fisik dari fit 8 sudut. Truk tetap perlu pengukuran lapangan/I24/RoScenes untuk GT fisik.
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
| Kalibrasi I24-3D | **tidak berlaku** — `hg` bukan GT f/pose | gunakan SVLD/pengukuran lapangan |
| Round-trip formula | <1% | perbaiki konvensi/urutan sudut |
| Dimensi I24-3D | $W/H$ <10% pada 20–30 m | batasi klaim; jangan lanjut ke ODOL |
| SVLD-3D | kalibrasi <2 px; dimensi **self-consistency**, bukan accuracy | dokumentasikan; jangan klaim fisik |
| Keypoint + shape | PCK >80%, RMS ≤3 px, $L/W/H$ <10% | hasil negatif; klaim adaptasi tidak terbukti |
| Anchor naver/cctv | pergeseran <5% untuk prior ±5% | hanya inisialisasi, bukan anchor |
| MoGe-2 | $h$ <10% dari anchor | 10–20% peringatan; >20% buang |

## 6. Aturan pelaporan

- Setiap laporan menyebut jumlah sampel, jumlah yang gagal diproses, dan alasan.
- Jangan membuang outlier tanpa menyebutkannya; laporkan dengan dan tanpa outlier.
- Jangan mengklaim akurasi lebih baik dari ketidakpastian ground truth (I24-3D ±15 cm). **`veh_size` SVLD adalah preset**, jadi tidak bisa dipakai sebagai ketidakpastian fisik.
- Setiap angka harus bisa dihasilkan ulang dari skrip yang disimpan.
- Dataset non-komersial hanya dipakai untuk validasi; bukan untuk melatih model produksi.
