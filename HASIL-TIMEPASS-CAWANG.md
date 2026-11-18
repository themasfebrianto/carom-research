# Hasil Time-of-Passage / Side-View — Cawang

## Tujuan

Menguji apakah panjang kendaraan bisa diukur dari **satu kamera, pure pixel, tanpa plat**, memakai sisi kendaraan yang terlihat saat melintas.

## Metode

1. Deteksi/segmentasi kendaraan dengan YOLO11n-seg (COCO).
2. Track kendaraan antar frame dengan IoU.
3. Ambil kontur mask; tentukan arah memanjang jalan dari vanishing point ($VP=(651{,}5,\;310{,}0)$).
4. Cari dua ujung kontur sepanjang arah VP; di tiap ujung, ambil titik kontak tanah (titik kontur terbawah).
5. Back-project kedua titik ke bidang jalan dengan kalibrasi Cawang:
   - $f=1082{,}6$ px, $h=8{,}876$ m, pitch $=2{,}432^\circ$, $c=(640,360)$.
   - $X$ dari baris $v$; $Y=(u-c_x)z/f$; $z=X\cos\theta+h\sin\theta$.
6. Panjang = jarak Euclidean kedua titik ground. Kecepatan = perubahan $X$ titik tengah ground.

Ini bukan time-of-passage murni; ia mengukur panjang dari dua kontak tanah di sisi kendaraan. Secara geometri setara, dan lebih sederhana karena tidak perlu mendeteksi waktu crossing secara eksplisit.

## Hasil

### Truk kontainer SINKOR (40 ft), t=86,0–86,4 s

| t (s) | Panjang (m) | $X_m$ (m) | Area mask |
|---:|---:|---:|---:|
| 86,0 | 15,23 | 31,7 | 57.216 |
| 86,2 | 15,90 | 32,9 | 52.688 |
| 86,4 | 16,53 | 39,6 | 34.440 |

- Median panjang **15,90 m**; mean 15,89 m.
- Kecepatan dari titik tengah ground: **19,75 m/s = 71,1 km/jam**.
- Pembanding: kontainer 40 ft = 12,19 m; kabin + sasis ≈ 4 m; total ≈ 16,2 m. Galat ≈ **2%**.
- Pada 86,6–86,8 s, mask mengecil (<30k px) dan panjang melonjak 31/27 m; frame ini dibuang.

### Mobil near-lane (model salah kelas sebagai bus), t=86,0–86,2 s

| t (s) | Panjang (m) | $X_m$ (m) | Area mask |
|---:|---:|---:|---:|
| 86,0 | 4,17 | 41,8 | 4.482 |
| 86,2 | 5,03 | 41,1 | 4.734 |

- Median **4,60 m**; masuk rentang mobil (4,4–4,8 m).
- Kecepatan dari dua frame: −3,5 m/s (mendekat); baseline terlalu pendek untuk angka yang stabil.

## Interpretasi

1. **Metode ini bekerja saat sisi kendaraan terlihat dan mask bersih.** Truk 40 ft memberi 15,9 m, hampir sama dengan 16,2 m yang diharapkan.
2. **Kecepatan truk masuk akal** (71 km/jam), yang mendukung bahwa back-projection ground tidak meleset jauh.
3. **Kualitas turun saat kendaraan menjauh.** Mask mengecil, ujung kontur bergeser, panjang melonjak. Filter area mask minimum 30k px untuk truk ini membuang frame yang rusak.
4. **Kelas YOLO tidak reliabel.** Mobil terdeteksi sebagai bus. Kelas tidak dipakai untuk perhitungan; hanya untuk filter kasar.
5. **Ini bukan pengukuran tervalidasi.** Tidak ada GT; pembanding hanya standar kontainer. Diperlukan 10–20 kendaraan dengan dimensi diketahui.

## Batas

- Hanya dua kendaraan.
- Kamera Cawang melihat sisi kendaraan karena posisinya di tepi jalan; kamera yang tepat di belakang lajur tidak akan memberi sisi.
- Kalibrasi Cawang anchored pada lebar lajur 3,60 m; jalan melengkung; galat sistematis belum diukur.
- Endpoint kontur adalah aproksimasi kontak tanah; roda/bayangan tidak selalu masuk mask.
- Kecepatan mobil dari dua frame tidak stabil.

## Langkah berikutnya

1. **10–20 truk kontainer/bus** dengan standar panjang diketahui (20 ft, 40 ft, bus 12 m); bangun distribusi galat.
2. **Time-of-passage murni**: definisikan garis melintang pada $X_0$; catat waktu tepi depan/belakang melintas; bandingkan $L=v\,\Delta t$ dengan hasil side-view.
3. **I24-3D satu kamera** (GT) untuk validasi akurasi, setelah akses disetujui.
4. **Perbaiki endpoint** dengan deteksi roda/kontak tanah, bukan kontur mentah.

## Berkas

- `scripts/cawang_timepass.py`
- `out/timepass/timepass_bus.csv`
- `out/timepass/truck86_endpoints.jpg`
- `out/timepass/truck86.jpg`
